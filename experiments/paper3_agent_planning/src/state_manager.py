"""State management for agent planning."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DialogueState:
    """Tracks the current state of a planning episode."""
    # Authentication
    user_id: Optional[str] = None
    user_authenticated: bool = False
    
    # Cached objects (avoid repeated DB lookups)
    cached_users: Dict[str, Any] = field(default_factory=dict)
    cached_orders: Dict[str, Any] = field(default_factory=dict)
    cached_products: Dict[str, Any] = field(default_factory=dict)
    cached_reservations: Dict[str, Any] = field(default_factory=dict)
    cached_flights: Dict[str, Any] = field(default_factory=dict)
    
    # Policy flags
    user_confirmed: bool = False  # Did user explicitly confirm the last action?
    action_taken_on_order: Dict[str, bool] = field(default_factory=dict)  # order_id -> was modified/returned/exchanged
    transfer_to_human: bool = False
    
    # Conversation history
    history: List[Dict[str, Any]] = field(default_factory=list)
    
    def record_action(self, action_name: str, arguments: Dict[str, Any], result: Any) -> None:
        self.history.append({
            "action": action_name,
            "arguments": arguments,
            "result": result,
        })
    
    def record_user_message(self, message: str) -> None:
        self.history.append({"role": "user", "content": message})
    
    def record_agent_message(self, message: str) -> None:
        self.history.append({"role": "agent", "content": message})
    
    def clone(self) -> "DialogueState":
        return DialogueState(
            user_id=self.user_id,
            user_authenticated=self.user_authenticated,
            cached_users=copy.deepcopy(self.cached_users),
            cached_orders=copy.deepcopy(self.cached_orders),
            cached_products=copy.deepcopy(self.cached_products),
            cached_reservations=copy.deepcopy(self.cached_reservations),
            cached_flights=copy.deepcopy(self.cached_flights),
            user_confirmed=self.user_confirmed,
            action_taken_on_order=copy.deepcopy(self.action_taken_on_order),
            transfer_to_human=self.transfer_to_human,
            history=copy.deepcopy(self.history),
        )
