"""
Embedding API Router
提供语义嵌入服务
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from onto_service.embedding.embedding_service import EmbeddingService

router = APIRouter()
embedding_service = EmbeddingService()


class EmbeddingRequest(BaseModel):
    texts: List[str]
    model: Optional[str] = "default"


class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dimension: int


class SimilarityRequest(BaseModel):
    query: str
    candidates: List[str]
    top_k: Optional[int] = 5


class SimilarityResponse(BaseModel):
    results: List[dict]


@router.post("/embed", response_model=EmbeddingResponse)
async def embed_texts(request: EmbeddingRequest):
    """将文本转换为嵌入向量"""
    try:
        embeddings = await embedding_service.embed(request.texts)
        return EmbeddingResponse(
            embeddings=embeddings,
            model=embedding_service.model_name,
            dimension=len(embeddings[0]) if embeddings else 0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/similarity", response_model=SimilarityResponse)
async def compute_similarity(request: SimilarityRequest):
    """计算查询与候选文本的相似度"""
    try:
        results = await embedding_service.find_similar(
            query=request.query,
            candidates=request.candidates,
            top_k=request.top_k
        )
        return SimilarityResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
