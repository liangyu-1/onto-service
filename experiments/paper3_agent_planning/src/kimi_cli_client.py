"""Kimi CLI client - uses subprocess to call kimi CLI for LLM requests."""
from __future__ import annotations

import json
import subprocess
from typing import Any, Dict

from llm_client import LLMClient


class KimiCLIClient(LLMClient):
    """Client that uses Kimi CLI via subprocess.
    
    Uses `kimi --print --quiet` for non-interactive execution.
    This works around the 403 restriction on the HTTP API.
    """

    def __init__(self, model: str = "kimi-latest"):
        self.model = model

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        """Send a chat request via Kimi CLI."""
        # Combine system and user prompt
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        result = subprocess.run(
            ['kimi', '--print', '--quiet'],
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=300,
            cwd='/Users/yuliang/mygithub/onto-service/experiments/paper3_agent_planning'
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Kimi CLI failed (code={result.returncode}): {result.stderr[:500]}")
        
        # Parse output - remove session resume line
        output = result.stdout.strip()
        lines = output.split('\n')
        # Filter out the "To resume this session" line
        content_lines = [l for l in lines if not l.startswith('To resume this session')]
        return '\n'.join(content_lines).strip()
