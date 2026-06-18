#!/usr/bin/env python3
"""Verify that paper variants expose only their declared Method components."""
from __future__ import annotations

import pathlib
import sys

BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))

from tau2_ontology_agent import (  # noqa: E402
    build_ontology_section,
    uses_admissibility_gate,
    uses_full_conditions,
    uses_ontology_prompt,
    uses_ontology_repair,
    uses_runtime_ontology_state,
)


EXPECTED = {
    "schema": (False, False, False, False, False),
    "ontology_prompt": (True, False, False, False, False),
    "state_only": (True, True, False, False, False),
    "typed_admissibility": (True, True, True, True, False),
    "ontology_full": (True, True, True, True, True),
}


def main() -> None:
    for agent_kind, expected in EXPECTED.items():
        actual = (
            uses_ontology_prompt(agent_kind),
            uses_runtime_ontology_state(agent_kind),
            uses_admissibility_gate(agent_kind),
            uses_full_conditions(agent_kind),
            uses_ontology_repair(agent_kind),
        )
        if actual != expected:
            raise AssertionError(f"{agent_kind}: expected {expected}, got {actual}")

        section = build_ontology_section(
            agent_kind,
            "ACTIONBANK_SENTINEL",
            "RUNTIME_STATE_SENTINEL",
        )
        if ("ACTIONBANK_SENTINEL" in section) != expected[0]:
            raise AssertionError(f"{agent_kind}: ActionBank prompt isolation failed")
        if ("RUNTIME_STATE_SENTINEL" in section) != expected[1]:
            raise AssertionError(f"{agent_kind}: runtime-state prompt isolation failed")

    schema_section = build_ontology_section(
        "schema",
        "ACTIONBANK_SENTINEL",
        "RUNTIME_STATE_SENTINEL",
    )
    if schema_section:
        raise AssertionError(f"Schema-Only must receive no ontology section: {schema_section!r}")

    print("agent variant isolation smoke tests passed")


if __name__ == "__main__":
    main()
