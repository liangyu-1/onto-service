"""Rule-based baseline for action extraction."""
from __future__ import annotations

import pathlib
import re
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from action_ir import ActionIR, EvidenceSpan, ParsedChunk, ProceduralUnit
from agents.structure_parser import StructureParser
from agents.unit_extractor import UnitExtractor
from agents.action_ir_builder import ActionIRBuilder
from agents.ontology_grounder import OntologyGrounder
from agents.graph_builder import GraphBuilder


class RuleBaseline:
    """End-to-end rule-based extraction pipeline.

    Uses only regex, keyword matching, and heuristics — no LLM.
    """

    def __init__(self, action_bank_path: pathlib.Path):
        self.parser = StructureParser()
        self.extractor = UnitExtractor(llm=None, use_llm=False)
        self.builder = ActionIRBuilder(llm=None, use_llm=False)
        self.grounder = OntologyGrounder(action_bank_path)
        self.graph_builder = GraphBuilder()

    def extract(self, doc_text: str, doc_id: str = "") -> Dict[str, Any]:
        """Run the full rule-based extraction pipeline on a document."""
        # Parse
        chunks = self.parser.parse(doc_text, doc_id=doc_id)

        # Extract units
        units = self.extractor.extract_all(chunks)

        # Build Action IR
        actions = self.builder.build(units)

        # Ground to ontology
        grounded = self.grounder.ground_all(actions)

        # Build graph
        graph = self.graph_builder.build(grounded, doc_text)

        return {
            "doc_id": doc_id,
            "actions": [a.to_dict() for a in grounded],
            "graph": graph.to_dict(),
            "doc_text": doc_text,
        }
