from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


ACTIONS = ["no_op", "refresh_mv", "repartition", "reindex", "cache_plan"]


@dataclass
class PolicyContext:
    step_idx: int
    event: Dict[str, Any]
    candidates: List[str]
    scores: Dict[str, float]


class BasePolicy:
    name = "base"

    def choose_action(self, ctx: PolicyContext) -> str:
        raise NotImplementedError


class StaticPolicy(BasePolicy):
    name = "static"

    def choose_action(self, ctx: PolicyContext) -> str:
        return "no_op"


class AlwaysTriggerPolicy(BasePolicy):
    name = "always_trigger"

    def choose_action(self, ctx: PolicyContext) -> str:
        return "refresh_mv" if "refresh_mv" in ctx.candidates else ctx.candidates[0]


class EditThresholdPolicy(BasePolicy):
    name = "edit_threshold"

    def __init__(self, threshold: int = 5):
        self.threshold = threshold

    def choose_action(self, ctx: PolicyContext) -> str:
        edit_count = int(ctx.event.get("edit_count", 0))
        if edit_count >= self.threshold and "refresh_mv" in ctx.candidates:
            return "refresh_mv"
        return "no_op"


class WorkloadOnlyPolicy(BasePolicy):
    name = "workload_only"

    def __init__(self, latency_threshold_ms: float = 250.0):
        self.latency_threshold_ms = latency_threshold_ms

    def choose_action(self, ctx: PolicyContext) -> str:
        latency_ms = float(ctx.event.get("base_latency_ms", 0.0))
        if latency_ms >= self.latency_threshold_ms:
            return "repartition" if "repartition" in ctx.candidates else "refresh_mv"
        return "no_op"


class SignificanceOnlyPolicy(BasePolicy):
    name = "significance_only"

    def __init__(self, significance_threshold: float = 0.5):
        self.significance_threshold = significance_threshold

    def choose_action(self, ctx: PolicyContext) -> str:
        significance = float(ctx.event.get("semantic_significance", 0.0))
        if significance >= self.significance_threshold:
            return "reindex" if "reindex" in ctx.candidates else "refresh_mv"
        return "no_op"


class ProposedPolicy(BasePolicy):
    name = "proposed"

    def choose_action(self, ctx: PolicyContext) -> str:
        # Proposed policy: pick max estimated utility from common scorer.
        best_action = "no_op"
        best_score = float("-inf")
        for action in ctx.candidates:
            score = float(ctx.scores.get(action, float("-inf")))
            if score > best_score:
                best_action = action
                best_score = score
        return best_action


class OraclePolicy(BasePolicy):
    name = "oracle"

    def choose_action(self, ctx: PolicyContext) -> str:
        best_action = "no_op"
        best_score = float("-inf")
        true_effects = ctx.event.get("action_effects", {})
        for action in ctx.candidates:
            score = float(true_effects.get(action, -1e9))
            if score > best_score:
                best_action = action
                best_score = score
        return best_action


def build_policies() -> List[BasePolicy]:
    return [
        StaticPolicy(),
        AlwaysTriggerPolicy(),
        EditThresholdPolicy(),
        WorkloadOnlyPolicy(),
        SignificanceOnlyPolicy(),
        ProposedPolicy(),
    ]

