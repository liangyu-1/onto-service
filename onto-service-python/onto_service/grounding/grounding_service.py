"""
Grounding Service
负责将自然语言查询映射到语义实体
"""

import os
import re
from typing import List, Dict, Any, Optional

import httpx

from onto_service.llm.llm_client import LLMClient
from onto_service.embedding.embedding_service import EmbeddingService

# Python service can call Java API for real entity data
JAVA_SERVICE_URL = os.getenv("JAVA_SERVICE_URL", "http://localhost:8080")


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
        self._use_java_api = True  # Try Java API first

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
        """从 TBOX 加载语义实体 - 优先从 Java API 加载，fallback 到缓存/mock"""
        cache_key = f"{domain_name}:{version}"
        if cache_key in self.entity_cache:
            return self.entity_cache[cache_key]

        # Try to load from Java service API
        if self._use_java_api:
            try:
                entities = await self._fetch_entities_from_java(domain_name, version)
                if entities:
                    self.entity_cache[cache_key] = entities
                    return entities
            except Exception as e:
                print(f"Failed to load entities from Java API: {e}, using fallback")
                self._use_java_api = False

        # Fallback: return empty list (caller should handle gracefully)
        # In production, this should load from a local cache file or database
        return []

    async def _fetch_entities_from_java(self, domain_name: str, version: str) -> List[Dict[str, Any]]:
        """从 Java 服务获取实体数据"""
        entities = []

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Fetch object types
            try:
                resp = await client.get(
                    f"{JAVA_SERVICE_URL}/api/v1/semantic/{domain_name}/{version}/object-types"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == 200 and data.get("data"):
                        for obj in data["data"]:
                            entities.append({
                                "type": "object_type",
                                "name": obj.get("labelName", ""),
                                "display_name": obj.get("displayName", ""),
                                "aliases": self._extract_aliases(obj.get("aiContext", "")),
                                "description": obj.get("description", "")
                            })
            except Exception as e:
                print(f"Failed to fetch object types: {e}")

            # Fetch properties
            try:
                # We need to fetch properties per object type
                for entity in list(entities):
                    if entity["type"] == "object_type":
                        resp = await client.get(
                            f"{JAVA_SERVICE_URL}/api/v1/semantic/{domain_name}/{version}/object-types/{entity['name']}/properties"
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("code") == 200 and data.get("data"):
                                for prop in data["data"]:
                                    entities.append({
                                        "type": "property",
                                        "name": f"{entity['name']}.{prop.get('propertyName', '')}",
                                        "owner_label": entity["name"],
                                        "property_name": prop.get("propertyName", ""),
                                        "aliases": prop.get("semanticAliases", []) or self._extract_aliases(prop.get("aiContext", "")),
                                        "description": prop.get("description", "")
                                    })
            except Exception as e:
                print(f"Failed to fetch properties: {e}")

            # Fetch relationships
            try:
                resp = await client.get(
                    f"{JAVA_SERVICE_URL}/api/v1/semantic/{domain_name}/{version}/relationships"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == 200 and data.get("data"):
                        for rel in data["data"]:
                            entities.append({
                                "type": "relationship",
                                "name": rel.get("labelName", ""),
                                "source_label": rel.get("sourceLabel", ""),
                                "target_label": rel.get("targetLabel", ""),
                                "outgoing_name": rel.get("outgoingName", ""),
                                "incoming_name": rel.get("incomingName", ""),
                                "aliases": self._extract_aliases(rel.get("aiContext", "")),
                                "description": rel.get("description", "")
                            })
            except Exception as e:
                print(f"Failed to fetch relationships: {e}")

        return entities

    def _extract_aliases(self, ai_context: str) -> List[str]:
        """从 ai_context 中提取别名"""
        if not ai_context:
            return []
        # Simple extraction: look for comma-separated terms
        aliases = []
        for part in ai_context.split(","):
            part = part.strip()
            if part and len(part) < 50:  # Reasonable alias length
                aliases.append(part)
        return aliases[:5]  # Limit to 5 aliases

    def _merge_results(self, llm_entities: List[Dict], embedding_matches: List[Dict]) -> List[Dict]:
        """融合 LLM 和 Embedding 的结果"""
        merged = {}
        for e in llm_entities:
            key = e.get("canonical_name", e.get("name", ""))
            if key:
                merged[key] = e
        for e in embedding_matches:
            key = e.get("canonical_name", e.get("name", ""))
            if key:
                if key in merged:
                    merged[key]["confidence"] = max(
                        merged[key].get("confidence", 0),
                        e.get("confidence", 0)
                    )
                else:
                    merged[key] = e
        return list(merged.values())

    def _generate_sql_hint(self, entities: List[Dict], intent: str) -> Optional[str]:
        """生成 SQL 提示"""
        object_types = [e for e in entities if e.get("entity_type") == "object_type" or e.get("type") == "object_type"]
        properties = [e for e in entities if e.get("entity_type") == "property" or e.get("type") == "property"]

        if not object_types:
            return None

        hint = f"-- Intent: {intent}\n"
        hint += f"-- Objects: {', '.join(e.get('name', e.get('canonical_name', '')) for e in object_types)}\n"
        if properties:
            hint += f"-- Properties: {', '.join(e.get('name', e.get('canonical_name', '')) for e in properties)}\n"
        return hint

    async def list_entities(self, domain_name: str, version: str,
                           entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出域中的所有实体"""
        entities = await self._load_domain_entities(domain_name, version)
        if entity_type:
            entities = [e for e in entities if e.get("type") == entity_type]
        return entities
