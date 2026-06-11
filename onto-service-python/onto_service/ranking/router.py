"""
Ranking API Router
学习排序 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from onto_service.ranking.ranking_service import RankingService

router = APIRouter()
ranking_service = RankingService()


class TrainRequest(BaseModel):
    training_data: List[Dict[str, Any]]


class TrainResponse(BaseModel):
    status: str
    model_info: Dict[str, Any]


class PredictRequest(BaseModel):
    candidates: List[Dict[str, Any]]


class PredictResponse(BaseModel):
    scores: List[float]
    ranked_indices: List[int]


class ModelInfoResponse(BaseModel):
    status: str
    model_info: Dict[str, Any]


@router.post("/train", response_model=TrainResponse)
async def train_model(request: TrainRequest):
    """训练 LambdaMART 排序模型"""
    try:
        result = ranking_service.train(request.training_data)
        return TrainResponse(
            status=result["status"],
            model_info=result.get("model_info", {})
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict", response_model=PredictResponse)
async def predict_scores(request: PredictRequest):
    """预测候选文档排序分数"""
    try:
        scores = ranking_service.predict(request.candidates)
        # 返回排序后的索引
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return PredictResponse(scores=scores, ranked_indices=ranked)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-info", response_model=ModelInfoResponse)
async def get_model_info():
    """获取当前模型信息"""
    try:
        info = ranking_service.get_model_info()
        return ModelInfoResponse(
            status=info.get("status", "unknown"),
            model_info=info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
