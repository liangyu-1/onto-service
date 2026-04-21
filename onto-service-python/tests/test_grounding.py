"""
Tests for grounding service
"""

import pytest
from onto_service.grounding.grounding_service import GroundingService


@pytest.fixture
def grounding_service():
    return GroundingService()


@pytest.mark.asyncio
async def test_ground_query(grounding_service):
    result = await grounding_service.ground(
        domain_name="PlantGraph",
        version="1.0.0",
        query="查 P1 过程里攻击窗口内 P1_B2004 的最近值"
    )
    
    assert result is not None
    assert result["domain_name"] == "PlantGraph"
    assert result["version"] == "1.0.0"
    assert result["original_query"] == "查 P1 过程里攻击窗口内 P1_B2004 的最近值"
    assert "entities" in result
    assert "intent" in result


@pytest.mark.asyncio
async def test_list_entities(grounding_service):
    entities = await grounding_service.list_entities("PlantGraph", "1.0.0")
    assert isinstance(entities, list)
    assert len(entities) > 0


@pytest.mark.asyncio
async def test_list_entities_with_filter(grounding_service):
    entities = await grounding_service.list_entities("PlantGraph", "1.0.0", entity_type="object_type")
    assert isinstance(entities, list)
    for e in entities:
        assert e.get("type") == "object_type"
