"""
Embedding Service
提供语义嵌入和相似度计算
"""

import numpy as np
from typing import List, Dict, Any, Optional


class EmbeddingService:
    """
    语义嵌入服务
    
    使用 sentence-transformers 或 OpenAI API 生成文本嵌入
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension = 384  # all-MiniLM-L6-v2 的维度

    def _get_model(self):
        """懒加载模型"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
            except ImportError:
                # 如果没有 sentence-transformers，使用 mock
                self._model = "mock"
        return self._model

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """生成文本嵌入"""
        model = self._get_model()
        if model == "mock":
            # Mock 实现：随机向量
            return [np.random.randn(self._dimension).tolist() for _ in texts]
        
        embeddings = model.encode(texts)
        return embeddings.tolist()

    async def find_similar(self, query: str, candidates: List[str],
                          top_k: int = 5) -> List[Dict[str, Any]]:
        """找到与查询最相似的候选"""
        all_texts = [query] + candidates
        embeddings = await self.embed(all_texts)
        
        query_embedding = np.array(embeddings[0])
        candidate_embeddings = np.array(embeddings[1:])
        
        # 计算余弦相似度
        similarities = self._cosine_similarity(query_embedding, candidate_embeddings)
        
        # 排序并返回 top_k
        indexed_similarities = [(i, float(sim)) for i, sim in enumerate(similarities)]
        indexed_similarities.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, score in indexed_similarities[:top_k]:
            results.append({
                "candidate": candidates[idx],
                "score": score,
                "rank": len(results) + 1
            })
        return results

    async def match_entities(self, query: str, entities: List[Dict[str, Any]],
                            threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        将查询与实体列表进行匹配
        
        返回置信度高于阈值的实体
        """
        candidate_texts = []
        for entity in entities:
            # 组合实体名称和别名作为候选文本
            texts = [entity.get("name", "")] + entity.get("aliases", [])
            candidate_texts.append(" ".join(texts))
        
        if not candidate_texts:
            return []
        
        similarities = await self.find_similar(query, candidate_texts, top_k=len(candidate_texts))
        
        matched = []
        for result in similarities:
            if result["score"] >= threshold:
                entity = entities[result["rank"] - 1].copy()
                entity["confidence"] = result["score"]
                entity["entity_type"] = entity.get("type", "unknown")
                entity["canonical_name"] = entity.get("name", "")
                matched.append(entity)
        
        return matched

    @staticmethod
    def _cosine_similarity(query: np.ndarray, candidates: np.ndarray) -> np.ndarray:
        """计算余弦相似度"""
        query_norm = query / (np.linalg.norm(query) + 1e-8)
        candidates_norm = candidates / (np.linalg.norm(candidates, axis=1, keepdims=True) + 1e-8)
        return np.dot(candidates_norm, query_norm)
