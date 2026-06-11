"""LLM client for agent planning."""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any, Dict, Optional


class LLMClient:
    """Base LLM client interface."""

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        raise NotImplementedError

    def chat_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> Dict[str, Any]:
        """Get JSON response from LLM."""
        response = self.chat(system_prompt, user_prompt, temperature, json_mode=True)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            # Fallback: find the first {...} object in the text
            m = re.search(r"\{.*?\}", response, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Could not parse JSON from response: {response[:200]}")


class OpenAIClient(LLMClient):
    """OpenAI-compatible API client (works with vLLM, etc.)."""

    def __init__(self, model: str, base_url: str, api_key: str = "EMPTY"):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.0, json_mode: bool = False) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": 8192,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        req = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        
        # Handle potential None content (e.g., when finish_reason="length")
        choice = body["choices"][0]
        msg = choice.get("message", {})
        content = msg.get("content")
        if content is None:
            # Try to get reasoning content as fallback
            reasoning = msg.get("reasoning", "")
            if reasoning:
                raise ValueError(f"LLM returned None content (finish_reason={choice.get('finish_reason')}). Reasoning: {reasoning[:200]}")
            raise ValueError(f"LLM returned None content (finish_reason={choice.get('finish_reason')}). Usage: {body.get('usage')}")
        return content


class DummyClient(LLMClient):
    """Dummy client for testing pipeline without real LLM."""

    def __init__(self, fallback_responses: Optional[Dict[str, str]] = None):
        self.fallback_responses = fallback_responses or {}
        self.call_count = 0

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        self.call_count += 1
        for keyword, response in self.fallback_responses.items():
            if keyword in user_prompt:
                return response
        return json.dumps({
            "thought": "I need to take an action.",
            "action": "transfer_to_human_agents",
            "arguments": {"summary": "Need human assistance."}
        })


class HeuristicClient(LLMClient):
    """Heuristic client that simulates a naive agent with configurable mistake rate."""

    def __init__(self, mistake_rate: float = 0.3):
        from baselines.heuristic_llm import HeuristicLLM
        self.heuristic = HeuristicLLM(mistake_rate=mistake_rate)

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        response = self.heuristic.chat_json(system_prompt, user_prompt, temperature)
        return json.dumps(response)


def create_llm_client(
    model: str = "GLM-5.1",
    base_url: str = "https://open.bigmodel.cn/api/coding/paas/v4",
    api_key: str = "EMPTY",
    use_kimi_cli: bool = False,
) -> LLMClient:
    """Factory: create OpenAI-compatible client."""
    if api_key == "EMPTY":
        api_key = os.getenv("OPENAI_API_KEY", "EMPTY")
    if use_kimi_cli:
        from kimi_cli_client import KimiCLIClient
        print("Using Kimi CLI client")
        return KimiCLIClient(model=model)
    
    try:
        client = OpenAIClient(model=model, base_url=base_url, api_key=api_key)
        # Quick test
        client.chat("You are a test assistant.", "Say 'ok'", temperature=0.0)
        print(f"LLM client connected: {model} @ {base_url}")
        return client
    except Exception as e:
        raise RuntimeError(
            f"Could not connect to LLM at {base_url}: {e}. "
            "Please check the endpoint, model name, and API key."
        ) from e
