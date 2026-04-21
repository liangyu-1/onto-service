"""
Grounding Service
负责将自然语言查询映射到语义实体
"""

import re
from typing import List, Dict, Any, Optional

from onto_service.llm.llm_client import LLMClient
from onto_service.embedding.embedding_service import EmbeddingService


class GroundingService:
    """
    Grounding 服务
    
    核心能力:
    1. 实体识别与链接 (Entity Recognition & Linking)
    2. 别名/同义词映射
    3. 意图识别
    4. 歧义消解
    """

    def __init__(self):
        self.llm_client = LLMClient()
        self.embedding_service = EmbeddingService()
        self.entity_cache = {}  # 简单的内存缓存

    async def ground(self, domain_name: str, version: str, query: str,
                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行 grounding
        
        流程:
        1. 从 TBOX 加载语义实体
        2. 使用 LLM 识别查询中的实体
        3. 使用 Embedding 进行相似度匹配
        4. 返回标准化的语义实体
        """
        # 1. 加载域实体
        entities = await self._load_domain_entities(domain_name, version)
        
        # 2. LLM 实体识别
        llm_entities = await self.llm_client.extract_entities(query, entities)
        
        # 3. Embedding 相似度匹配 (补充/验证)
        embedding_matches = await self.embedding_service.match_entities(query, entities)
        
        # 4. 融合结果
        grounded_entities = self._merge_results(llm_entities, embedding_matches)
        
        # 5. 意图识别
        intent = await self.llm_client.classify_intent(query)
        
        return {
            "domain_name": domain_name,
            "version": version,
            "original_query": query,
            "entities": grounded_entities,
            "intent": intent,
            "sql_hint": self._generate_sql_hint(grounded_entities, intent)
        }

    async def _load_domain_entities(self, domain_name: str, version: str) -> List[Dict[str, Any]]:
        """从 TBOX 加载语义实体"""
        cache_key = f"{domain_name}:{version}"
        if cache_key in self.entity_cache:
            return self.entity_cache[cache_key]
        
        # TODO: 从 Java 服务或数据库加载实体
        # 这里使用 mock 数据
        entities = [
            {"type": "object_type", "name": "ICSProcess", "aliases": ["过程", "工艺过程"]},
            {"type": "object_type", "name": "SCADAPoint", "aliases": ["点位", "测点"]},
            {"type": "property", "name": "PointSample.value", "aliases": ["值", "最近值", "当前值"]},
            {"type": "relationship", "name": "HAS_POINT", "aliases": ["包含点位", "拥有测点"]},
            {"type": "object_type", "name": "AttackWindow", "aliases": ["攻击窗口", "攻击时段"]},
        ]
        self.entity_cache[cache_key] = entities
        return entities

    def _merge_results(self, llm_entities: List[Dict], embedding_matches: List[Dict]) -> List[Dict]:
        """融合 LLM 和 Embedding 的结果"""
        merged = {}
        for e in llm_entities:
            key = e.get("canonical_name", e.get("name"))
            merged[key] = e
        for e in embedding_matches:
            key = e.get("canonical_name", e.get("name"))
            if key in merged:
                # 取最高置信度
                merged[key]["confidence"] = max(merged[key].get("confidence", 0), e.get("confidence", 0))
            else:
                merged[key] = e
        return list(merged.values())

    def _generate_sql_hint(self, entities: List[Dict], intent: str) -> Optional[str]:
        """生成 SQL 提示"""
        # 根据实体和意图生成 SQL 片段提示
        object_types = [e for e in entities if e.get("entity_type") == "object_type"]
        properties = [e for e in entities if e.get("entity_type") == "property"]
        
        if not object_types:
            return None
        
        hint = f"-- Intent: {intent}\n"
        hint += f"-- Objects: {', '.join(e['name'] for e in object_types)}\n"
        if properties:
            hint += f"-- Properties: {', '.join(e['name'] for e in properties)}\n"
        return hint

    async def list_entities(self, domain_name: str, version: str,
                           entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出域中的所有实体"""
        entities = await self._load_domain_entities(domain_name, version)
        if entity_type:
            entities = [e for e in entities if e.get("type") == entity_type]
        return entities
