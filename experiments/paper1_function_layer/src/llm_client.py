"""Minimal OpenAI-compatible chat client for experiment code."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class ChatClient:
    def __init__(self, base_url: str, model: str, api_key_env: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.api_key = os.environ.get(api_key_env, "")
        if not self.api_key:
            raise ValueError(f"Missing API key environment variable: {api_key_env}")

    def complete_json(self, messages: list[dict[str, str]]) -> Any:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc
        data = json.loads(raw)
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
