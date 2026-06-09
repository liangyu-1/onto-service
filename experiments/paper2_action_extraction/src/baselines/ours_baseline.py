"""Ours (multi-agent) baseline: full pipeline with structure parsing, unit extraction, Action IR, grounding, validation."""
from __future__ import annotations

import pathlib
from typing import Any, Dict, List

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from action_ir import ActionIR
from llm_client import LLMClient
from agents.structure_parser import StructureParser
from agents.unit_extractor import UnitExtractor
from agents.action_ir_builder import ActionIRBuilder
from agents.ontology_grounder import OntologyGrounder
from agents.graph_builder import GraphBuilder


class OursBaseline:
    """Full multi-agent extraction pipeline.

    Stages:
    1. StructureParser — parse document into chunks
    2. UnitExtractor — LLM-based procedural unit extraction
    3. ActionIRBuilder — compile units into Action IR
    4. OntologyGrounder — ground to ontology ActionBank
    5. GraphBuilder — build procedure graph
    """

    def __init__(
        self,
        llm: LLMClient,
        action_bank_path: pathlib.Path,
        use_llm_units: bool = True,
        use_llm_ir: bool = True,
    ):
        self.parser = StructureParser()
        self.extractor = UnitExtractor(llm=llm, use_llm=use_llm_units)
        self.builder = ActionIRBuilder(llm=llm, use_llm=use_llm_ir)
        self.grounder = OntologyGrounder(action_bank_path)
        self.graph_builder = GraphBuilder()

    def extract(self, doc_text: str, doc_id: str = "") -> Dict[str, Any]:
        """Run the full multi-agent extraction pipeline."""
        # Stage 1: Parse
        chunks = self.parser.parse(doc_text, doc_id=doc_id)

        # Stage 2: Extract units
        units = self.extractor.extract_all(chunks)

        # Stage 3: Build Action IR
        actions = self.builder.build(units)

        # Stage 4: Ground to ontology
        grounded = self.grounder.ground_all(actions)

        # Stage 5: Build graph
        graph = self.graph_builder.build(grounded, doc_text)

        return {
            "doc_id": doc_id,
            "actions": [a.to_dict() for a in grounded],
            "graph": graph.to_dict(),
            "doc_text": doc_text,
        }
