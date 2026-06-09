"""RAG baseline: Retrieve similar tasks from train set as examples."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from src.state_manager import DialogueState
from src.llm_client import LLMClient
from src.action_bank import ActionBank


class RAGPlanner:
    """RAG-style planner that retrieves similar task examples from training data."""

    def __init__(self, llm: LLMClient, action_bank: ActionBank, train_tasks: List[Any], top_k: int = 2):
        self.llm = llm
        self.action_bank = action_bank
        self.train_tasks = train_tasks
        self.top_k = top_k

    def _extract_task_info(self, task: Any) -> str:
        """Extract task description."""
        if isinstance(task, dict):
            task_description = task.get("instruction", "")
            user_scenario = task.get("user_scenario", {})
        else:
            task_description = getattr(task, 'instruction', '')
            user_scenario = getattr(task, 'user_scenario', {})
        
        if not task_description and isinstance(user_scenario, dict):
            task_description = user_scenario.get("instruction", "")
            if not task_description and "instructions" in user_scenario:
                ins = user_scenario["instructions"]
                if isinstance(ins, dict):
                    task_description = ins.get("reason_for_call", "")
        
        known_facts = []
        if isinstance(user_scenario, dict):
            known_info = user_scenario.get("instructions", {}).get("known_info", "")
            if known_info:
                known_facts.append(f"Known: {known_info}")
        
        parts = [f"Task: {task_description}"]
        if known_facts:
            parts.extend(known_facts)
        return "\n".join(parts)

    def _retrieve_similar_tasks(self, task_info: str) -> List[str]:
        """Simple keyword-based retrieval of similar training tasks."""
        task_lower = task_info.lower()
        scores = []
        
        for t in self.train_tasks:
            train_info = self._extract_task_info(t).lower()
            # Simple keyword overlap scoring
            keywords = ['cancel', 'exchange', 'return', 'modify', 'address', 'item']
            score = sum(1 for kw in keywords if kw in task_lower and kw in train_info)
            # Also check if same action type
            if t.gold_actions:
                gold_final = t.gold_actions[-1]['name']
                scores.append((score, t, gold_final))
        
        # Sort by score and return top_k
        scores.sort(key=lambda x: x[0], reverse=True)
        examples = []
        for _, t, final in scores[:self.top_k]:
            info = self._extract_task_info(t)
            gold_seq = " -> ".join(ga['name'] for ga in t.gold_actions)
            examples.append(f"Example task: {info}\nSolution: {gold_seq}")
        
        return examples

    def plan_next_action(self, task: Any, state: DialogueState, db: Dict[str, Any]) -> Dict[str, Any]:
        task_info = self._extract_task_info(task)
        action_bank_text = self.action_bank.to_prompt_text()
        
        # Retrieve similar examples
        examples = self._retrieve_similar_tasks(task_info)
        examples_text = "\n\n".join(examples) if examples else "No similar examples found."

        # Build history
        history_lines = []
        for h in state.history:
            if "action" in h:
                result = h.get("result", "")
                if isinstance(result, dict) and "error" in result:
                    history_lines.append(f"- {h['action']} -> Error: {result['error']}")
                else:
                    history_lines.append(f"- {h['action']} -> OK")
        history_text = "\n".join(history_lines[-10:]) if history_lines else "No actions yet."

        system_prompt = f"""You are a customer service agent. Here are similar solved tasks:

{examples_text}

Available actions:
{action_bank_text}

Rules:
1. Authenticate user first
2. Use exact values from task description
3. Do not repeat successful actions

Respond with JSON:
{{
  "thought": "reasoning",
  "action": "action_id",
  "arguments": {{"param": "value"}}
}}"""

        user_prompt = f"""{task_info}

History:
{history_text}

What is the next action?"""

        try:
            response = self.llm.chat_json(system_prompt, user_prompt)
            return {
                "thought": response.get("thought", ""),
                "action": response.get("action", ""),
                "arguments": response.get("arguments", {}),
            }
        except Exception as e:
            return {
                "thought": f"Error: {e}",
                "action": "transfer_to_human_agents",
                "arguments": {"summary": "Planning failed."},
            }
