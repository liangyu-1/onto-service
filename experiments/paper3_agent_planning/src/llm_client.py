"""OpenAI-compatible LLM client used by the tau2 agent entrypoint."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict


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

    def __init__(self, model: str, base_url: str, api_key: str = "EMPTY", max_retries: int = 4):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.max_retries = max_retries

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
        body = self._post_chat_completion(url, payload)
        
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

    def _post_chat_completion(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        encoded = json.dumps(payload).encode("utf-8")
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            req = urllib.request.Request(
                url=url,
                data=encoded,
                method="POST",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in {408, 409, 425, 429, 500, 502, 503, 504} or attempt >= self.max_retries:
                    break
                retry_after = exc.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 16)
                time.sleep(delay)
            except urllib.error.URLError as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(2 ** attempt, 16))
        raise last_error or RuntimeError("LLM request failed")
