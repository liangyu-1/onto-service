"""
Tests for embedding service
"""

import pytest
from onto_service.embedding.embedding_service import EmbeddingService


@pytest.fixture
def embedding_service():
    return EmbeddingService()


@pytest.mark.asyncio
async def test_embed_texts(embedding_service):
    texts = ["ICSProcess", "SCADAPoint", "attack window"]
    embeddings = await embedding_service.embed(texts)
    
    assert len(embeddings) == len(texts)
    assert len(embeddings[0]) == embedding_service._dimension


@pytest.mark.asyncio
async def test_find_similar(embedding_service):
    query = "process security state"
    candidates = [
        "ICSProcess security_state",
        "SCADAPoint latest_value",
        "AttackWindow detection"
    ]
    
    results = await embedding_service.find_similar(query, candidates, top_k=2)
    
    assert len(results) == 2
    assert all("score" in r for r in results)
    assert all("rank" in r for r in results)
    # Results should be sorted by score descending
    assert results[0]["score"] >= results[1]["score"]


@pytest.mark.asyncio
async def test_match_entities(embedding_service):
    query = "process"
    entities = [
        {"name": "ICSProcess", "type": "object_type", "aliases": ["过程", "工艺过程"]},
        {"name": "SCADAPoint", "type": "object_type", "aliases": ["点位"]},
    ]
    
    matched = await embedding_service.match_entities(query, entities, threshold=0.5)
    
    assert isinstance(matched, list)
    # Should match ICSProcess
    assert any(e["name"] == "ICSProcess" for e in matched)
