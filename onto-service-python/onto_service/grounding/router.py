"""
Grounding API Router
提供自然语言到语义实体的映射服务
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from onto_service.grounding.grounding_service import GroundingService

router = APIRouter()
grounding_service = GroundingService()


class GroundingRequest(BaseModel):
    domain_name: str
    version: str
    query: str
    context: Optional[Dict[str, Any]] = None


class GroundedEntity(BaseModel):
    entity_type: str  # object_type / property / relationship / value / logic / action
    name: str
    canonical_name: str
    confidence: float
    aliases: List[str] = []
    metadata: Optional[Dict[str, Any]] = None


class GroundingResponse(BaseModel):
    domain_name: str
    version: str
    original_query: str
    entities: List[GroundedEntity]
    intent: str
    sql_hint: Optional[str] = None


@router.post("/ground", response_model=GroundingResponse)
async def ground_query(request: GroundingRequest):
    """
    将自然语言查询 Grounding 为语义实体
    
    示例:
        query: "查 P1 过程里攻击窗口内 P1_B2004 的最近值"
        -> P1 -> ICSProcess 实例
        -> P1_B2004 -> SCADAPoint 实例
        -> 攻击窗口 -> AttackWindow
        -> 最近值 -> PointSample.value
    """
    try:
        result = await grounding_service.ground(
            domain_name=request.domain_name,
            version=request.version,
            query=request.query,
            context=request.context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-ground")
async def batch_ground_queries(requests: List[GroundingRequest]):
    """批量 grounding"""
    results = []
    for req in requests:
        result = await ground_query(req)
        results.append(result)
    return results


@router.get("/entities/{domain_name}/{version}")
async def list_entities(domain_name: str, version: str, entity_type: Optional[str] = None):
    """获取域中的所有语义实体"""
    return await grounding_service.list_entities(domain_name, version, entity_type)
