"""
Query Understanding Service
语义查询理解：意图识别、实体链接、结构约束提取、查询扩展
"""

import json
import os
from typing import List, Dict, Any, Optional

from onto_service.llm.llm_client import LLMClient


class QueryUnderstandingService:
    """
    查询理解服务
    
    核心能力:
    1. 意图识别 (Intent Recognition): MEASURE_LOOKUP / PROPERTY_SEARCH / RELATIONSHIP_QUERY / DEFINITION / FUNCTION_QUERY / PATH_NAVIGATION
    2. 实体链接 (Entity Linking): 将查询中的实体映射到本体 objectPath
    3. 结构约束提取 (Structure Constraint Extraction): "...的指标" → TYPE_FILTER: MEASURE
    4. 查询扩展 (Query Expansion): 同义词、上下位词扩展
    """

    def __init__(self):
        self.llm_client = LLMClient()

    async def analyze(self, query: str, ontology_entities: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        全面分析查询
        
        Args:
            query: 用户自然语言查询
            ontology_entities: 可选的本体实体列表，用于实体链接
            
        Returns:
            {
                "intent": "MEASURE_LOOKUP",
                "linked_entities": ["equipment_domain.equipment"],
                "constraints": [
                    {"type": "TYPE_FILTER", "value": "MEASURE", "description": "查询目标为指标"}
                ],
                "expanded_queries": ["设备故障数", "设备 fault count"],
                "keywords": ["设备", "故障数"],
                "confidence": 0.92
            }
        """
        # 并行执行意图识别和实体链接
        intent_task = self._recognize_intent(query)
        entity_task = self._link_entities(query, ontology_entities or [])
        
        intent_result = await intent_task
        entity_result = await entity_task
        
        # 结构约束提取（基于规则和 LLM）
        constraints = self._extract_constraints(query, intent_result)
        
        # 查询扩展
        expanded = self._expand_query(query, entity_result)
        
        return {
            "intent": intent_result,
            "linked_entities": entity_result,
            "constraints": constraints,
            "expanded_queries": expanded,
            "keywords": self._extract_keywords(query),
            "confidence": 0.85  # TODO: 基于多任务一致性计算
        }

    async def _recognize_intent(self, query: str) -> str:
        """识别查询意图"""
        # 先尝试规则匹配（快速路径）
        rule_intent = self._rule_based_intent(query)
        if rule_intent:
            return rule_intent
            
        # 规则不匹配时，使用 LLM
        prompt = f"""分析以下工业领域查询的意图，从以下选项中选择最匹配的一个:
- MEASURE_LOOKUP: 查找指标/度量（如"故障数"、"产量统计"）
- PROPERTY_SEARCH: 查找属性/字段（如"设备名称"、"ID"）
- RELATIONSHIP_QUERY: 查找关系/关联（如"和故障相关的"）
- DEFINITION: 查询定义/概念（如"什么是设备"）
- FUNCTION_QUERY: 查找函数/计算逻辑（如"聚合函数"、"统计方法"）
- PATH_NAVIGATION: 路径导航/探索（如"从设备到故障的路径"）
- GENERAL: 通用查询

查询: {query}

只返回意图标签，不要解释。"""

        response = await self.llm_client._call_llm(prompt)
        intent = response.strip().upper()
        
        valid_intents = ["MEASURE_LOOKUP", "PROPERTY_SEARCH", "RELATIONSHIP_QUERY", 
                        "DEFINITION", "FUNCTION_QUERY", "PATH_NAVIGATION", "GENERAL"]
        return intent if intent in valid_intents else "GENERAL"

    def _rule_based_intent(self, query: str) -> Optional[str]:
        """基于关键词规则的意图识别（快速路径）"""
        lower = query.lower()
        
        if any(kw in lower for kw in ["指标", "度量", "measure", "统计", "多少", "数", "count", "sum", "avg"]):
            return "MEASURE_LOOKUP"
        if any(kw in lower for kw in ["属性", "字段", "列", "property", "field", "column", "有什么"]):
            return "PROPERTY_SEARCH"
        if any(kw in lower for kw in ["关系", "关联", "连接", "relationship", "related", "link"]):
            return "RELATIONSHIP_QUERY"
        if any(kw in lower for kw in ["是什么", "定义", "概念", "什么意思", "介绍", "what is"]):
            return "DEFINITION"
        if any(kw in lower for kw in ["函数", "计算", "聚合", "function", "agg", "calculate"]):
            return "FUNCTION_QUERY"
        if any(kw in lower for kw in ["路径", "怎么找", "从", "到", "经过", "path", "route"]):
            return "PATH_NAVIGATION"
        return None

    async def _link_entities(self, query: str, entities: List[Dict[str, Any]]) -> List[str]:
        """实体链接：将查询中的实体映射到本体 objectPath"""
        if not entities:
            return []
            
        prompt = f"""将用户查询中的实体映射到预定义的本体实体路径。

预定义本体实体:
{json.dumps([{"path": e.get("path", e.get("name", "")), "name": e.get("name", ""), "type": e.get("type", "")} for e in entities[:50]], ensure_ascii=False, indent=2)}

用户查询: {query}

请返回查询中提到的实体对应的路径列表（JSON 数组格式），如:
["equipment_domain.equipment", "equipment_domain.equipment.properties.equipment_id"]

如果查询中没有明确提到预定义实体，返回空数组 []。"""

        response = await self.llm_client._call_llm(prompt)
        try:
            result = json.loads(response)
            if isinstance(result, list):
                return [str(item) for item in result if isinstance(item, str)]
            elif isinstance(result, dict):
                return result.get("entities", [])
        except json.JSONDecodeError:
            pass
        return []

    def _extract_constraints(self, query: str, intent: str) -> List[Dict[str, Any]]:
        """提取结构约束"""
        constraints = []
        lower = query.lower()
        
        # 类型过滤约束
        if "的指标" in lower or "的度量" in lower or "的measure" in lower:
            constraints.append({"type": "TYPE_FILTER", "value": "MEASURE", "description": "查询目标为指标/度量"})
        elif "的属性" in lower or "的字段" in lower:
            constraints.append({"type": "TYPE_FILTER", "value": "PROPERTY", "description": "查询目标为属性"})
        elif "的关系" in lower or "的关联" in lower:
            constraints.append({"type": "TYPE_FILTER", "value": "RELATIONSHIP", "description": "查询目标为关系"})
        elif "的函数" in lower:
            constraints.append({"type": "TYPE_FILTER", "value": "FUNCTION", "description": "查询目标为函数"})
        
        # 意图驱动的类型约束
        intent_type_map = {
            "MEASURE_LOOKUP": "MEASURE",
            "PROPERTY_SEARCH": "PROPERTY",
            "RELATIONSHIP_QUERY": "RELATIONSHIP",
            "FUNCTION_QUERY": "FUNCTION"
        }
        if intent in intent_type_map:
            type_value = intent_type_map[intent]
            # 避免重复添加
            if not any(c.get("value") == type_value for c in constraints):
                constraints.append({"type": "TYPE_FILTER", "value": type_value, "description": f"意图驱动的类型约束: {type_value}"})
        
        # 跳数约束
        if any(kw in lower for kw in ["相关", "附近", "周边", "related", "nearby"]):
            constraints.append({"type": "HOP_DISTANCE", "value": "2", "description": "相关实体在 2 跳以内"})
        
        return constraints

    def _expand_query(self, query: str, linked_entities: List[str]) -> List[str]:
        """查询扩展：同义词和上下位词"""
        expanded = [query]
        
        # 同义词映射表（可扩展为调用外部词库）
        synonym_map = {
            "故障": ["错误", "异常", "损坏", "breakdown", "fault", "error"],
            "设备": ["机器", "装置", "硬件", "equipment", "machine", "device"],
            "统计": ["计算", "汇总", "聚合", "count", "sum", "aggregate"],
            "属性": ["字段", "列", "特征", "property", "field", "column"],
            "指标": ["度量", "测量", "measure", "metric", "kpi"],
        }
        
        for keyword, synonyms in synonym_map.items():
            if keyword in query:
                for syn in synonyms:
                    expanded.append(query.replace(keyword, syn))
        
        return list(set(expanded))

    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        import re
        tokens = re.split(r'[\s,，.。;；!！?？]+', query)
        return [t.strip() for t in tokens if t.strip() and len(t.strip()) > 1]
