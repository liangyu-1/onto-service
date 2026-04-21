"""
LLM Client
封装 LLM 调用，用于实体识别、意图分类等
"""

import os
import json
from typing import List, Dict, Any, Optional


class LLMClient:
    """
    LLM 客户端
    
    支持 OpenAI API 和本地模型
    """

    def __init__(self, provider: str = "openai"):
        self.provider = provider
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    async def extract_entities(self, query: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        使用 LLM 从查询中提取实体
        
        返回识别到的语义实体列表
        """
        # 构建 prompt
        entity_list = "\n".join([
            f"- {e['name']} ({e['type']}): {', '.join(e.get('aliases', []))}"
            for e in entities
        ])
        
        prompt = f"""你是一个工业领域语义理解助手。请将用户的自然语言查询映射到预定义的语义实体。

预定义语义实体:
{entity_list}

用户查询: {query}

请以 JSON 格式返回识别到的实体列表，每个实体包含:
- entity_type: 实体类型
- name: 实体名称
- canonical_name: 标准名称
- confidence: 置信度 (0-1)

如果查询中包含实体别名，请映射到标准名称。"""

        # 调用 LLM
        response = await self._call_llm(prompt)
        
        try:
            # 解析 JSON 响应
            result = json.loads(response)
            return result.get("entities", [])
        except json.JSONDecodeError:
            # 如果 LLM 没有返回有效 JSON，返回空列表
            return []

    async def classify_intent(self, query: str) -> str:
        """
        分类查询意图
        
        例如: select / aggregate / compare / trend / anomaly
        """
        prompt = f"""请分析以下查询的意图，从以下选项中选择最匹配的一个:
- select: 查询具体数值或状态
- aggregate: 聚合统计 (平均值、总和、计数等)
- compare: 比较不同对象或时间段
- trend: 趋势分析
- anomaly: 异常检测
- predict: 预测
- action: 执行某个动作

查询: {query}

只返回意图标签，不要解释。"""

        response = await self._call_llm(prompt)
        return response.strip().lower()

    async def generate_explanation(self, template: str, context: Dict[str, Any]) -> str:
        """
        基于模板和上下文生成自然语言解释
        
        模板示例:
        "{process_id} 当前为 {security_state}，因为攻击窗口数为 {attack_window_count_5m}"
        """
        try:
            explanation = template.format(**context)
            return explanation
        except KeyError as e:
            return f"解释生成失败: 缺少参数 {e}"

    async def _call_llm(self, prompt: str) -> str:
        """
        调用 LLM API
        
        如果没有配置 API Key，返回 mock 响应
        """
        if not self.api_key:
            # Mock 实现
            return self._mock_llm_response(prompt)
        
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个工业领域语义理解助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"LLM 调用失败: {str(e)}"

    def _mock_llm_response(self, prompt: str) -> str:
        """Mock LLM 响应，用于开发和测试"""
        if "extract_entities" in prompt or "语义实体" in prompt:
            return json.dumps({
                "entities": [
                    {"entity_type": "object_type", "name": "ICSProcess", "canonical_name": "ICSProcess", "confidence": 0.95},
                    {"entity_type": "object_type", "name": "SCADAPoint", "canonical_name": "SCADAPoint", "confidence": 0.88}
                ]
            })
        elif "intent" in prompt or "意图" in prompt:
            return "select"
        return "{}"
