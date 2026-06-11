"""
FastAPI 应用入口
提供 LLM Grounding、Embedding、Query Understanding 和 Ranking 服务
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from onto_service.grounding import router as grounding_router
from onto_service.embedding import router as embedding_router
from onto_service.query_understanding import router as query_router
from onto_service.ranking import router as ranking_router

app = FastAPI(
    title="Ontology Service Python API",
    description="LLM Grounding, Embedding, Query Understanding and Ranking Service for Ontology Platform",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(grounding_router.router, prefix="/api/v1/grounding", tags=["grounding"])
app.include_router(embedding_router.router, prefix="/api/v1/embedding", tags=["embedding"])
app.include_router(query_router.router, prefix="/api/v1/query", tags=["query-understanding"])
app.include_router(ranking_router.router, prefix="/api/v1/ranking", tags=["ranking"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "onto-service-python", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
