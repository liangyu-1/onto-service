"""
Tests for LLM client
"""

import pytest
from onto_service.llm.llm_client import LLMClient


@pytest.fixture
def llm_client():
    return LLMClient()


@pytest.mark.asyncio
async def test_extract_entities(llm_client):
    entities = [
        {"name": "ICSProcess", "type": "object_type", "aliases": ["过程"]},
        {"name": "SCADAPoint", "type": "object_type", "aliases": ["点位"]},
    ]
    
    result = await llm_client.extract_entities("查 P1 过程的最近值", entities)
    
    assert isinstance(result, list)
    # Mock mode should return some entities
    assert len(result) > 0


@pytest.mark.asyncio
async def test_classify_intent(llm_client):
    intent = await llm_client.classify_intent("查 P1 的最近值")
    assert isinstance(intent, str)
    assert len(intent) > 0


@pytest.mark.asyncio
async def test_generate_explanation(llm_client):
    template = "{process_id} 当前为 {security_state}"
    context = {"process_id": "P1", "security_state": "Normal"}
    
    explanation = await llm_client.generate_explanation(template, context)
    
    assert "P1" in explanation
    assert "Normal" in explanation


@pytest.mark.asyncio
async def test_generate_explanation_missing_param(llm_client):
    template = "{process_id} 当前为 {security_state}"
    context = {"process_id": "P1"}  # missing security_state
    
    explanation = await llm_client.generate_explanation(template, context)
    
    assert "失败" in explanation or "missing" in explanation.lower()
