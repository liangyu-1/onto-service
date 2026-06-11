"""
Query Understanding API Router
语义查询理解 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from onto_service.query_understanding.query_service import QueryUnderstandingService

router = APIRouter()
query_service = QueryUnderstandingService()


class QueryAnalyzeRequest(BaseModel):
    query: str
    ontology_entities: Optional[List[Dict[str, Any]]] = None


class QueryAnalyzeResponse(BaseModel):
    intent: str
    linked_entities: List[str]
    constraints: List[Dict[str, Any]]
    expanded_queries: List[str]
    keywords: List[str]
    confidence: float


@router.post("/analyze", response_model=QueryAnalyzeResponse)
async def analyze_query(request: QueryAnalyzeRequest):
    """分析查询意图、实体链接、结构约束"""
    try:
        result = await query_service.analyze(request.query, request.ontology_entities)
        return QueryAnalyzeResponse(
            intent=result["intent"],
            linked_entities=result["linked_entities"],
            constraints=result["constraints"],
            expanded_queries=result["expanded_queries"],
            keywords=result["keywords"],
            confidence=result["confidence"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/intent", response_model=Dict[str, Any])
async def classify_intent(request: QueryAnalyzeRequest):
    """仅识别查询意图"""
    try:
        intent = await query_service._recognize_intent(request.query)
        return {"intent": intent, "query": request.query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entities", response_model=Dict[str, Any])
async def link_entities(request: QueryAnalyzeRequest):
    """仅执行实体链接"""
    try:
        entities = await query_service._link_entities(request.query, request.ontology_entities or [])
        return {"linked_entities": entities, "query": request.query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
