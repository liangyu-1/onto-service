"""Agent 3: UnitExtractor — extracts procedural units from document chunks."""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from action_ir import EvidenceSpan, ParsedChunk, ProceduralUnit
from llm_client import LLMClient


UNIT_EXTRACTION_PROMPT = """You are a procedural-unit extractor. Given a chunk from a procedural document, identify all procedural units within it.

A procedural unit is one of:
- operation: an action to be performed (e.g., "check the pressure gauge", "cancel the order")
- condition: a prerequisite or conditional statement (e.g., "if the order is pending", "before starting the pump")
- constraint: a policy or safety constraint (e.g., "user must be authenticated", "can only be done once per order")
- exception: an exception-handling or error-recovery statement (e.g., "if the item is unavailable, transfer to human")
- equipment: mention of a tool, device, or system component
- quality: a quality check or verification requirement

For each unit, output:
- unit_type: one of [operation, condition, constraint, exception, equipment, quality]
- text: the exact text span of the unit
- start: character offset within the chunk text where the unit starts
- end: character offset where the unit ends

Output as JSON:
{
  "units": [
    {"unit_type": "operation", "text": "...", "start": 0, "end": 20},
    ...
  ]
}

Chunk text:
"""


class UnitExtractor:
    """Extracts procedural units from parsed chunks using LLM + rule-based fallback."""

    def __init__(self, llm: Optional[LLMClient] = None, use_llm: bool = True):
        self.llm = llm
        self.use_llm = use_llm and llm is not None

        # Rule-based patterns as fallback
        self.patterns = {
            "operation": re.compile(
                r"\b(find|get|look up|retrieve|cancel|modify|update|change|return|exchange|transfer|ask|calculate|list|check|verify|confirm|process)\b",
                re.IGNORECASE,
            ),
            "condition": re.compile(
                r"\b(if|when|before|after|once|unless|provided that|given that)\b",
                re.IGNORECASE,
            ),
            "constraint": re.compile(
                r"\b(must|should|required|only|cannot|must not|ensure|necessary|mandatory)\b",
                re.IGNORECASE,
            ),
            "exception": re.compile(
                r"\b(if not|otherwise|else|in case of|when .* fails|error|exception|unable to)\b",
                re.IGNORECASE,
            ),
            "equipment": re.compile(
                r"\b(system|device|tool|gauge|meter|sensor|pump|valve|machine|software|platform)\b",
                re.IGNORECASE,
            ),
            "quality": re.compile(
                r"\b(verify|check|inspect|test|validate|ensure quality|quality check|audit)\b",
                re.IGNORECASE,
            ),
        }

    def _rule_extract(self, chunk: ParsedChunk) -> List[ProceduralUnit]:
        """Rule-based extraction using keyword patterns."""
        text = chunk.text
        units = []
        seen_spans = set()

        for unit_type, pattern in self.patterns.items():
            for m in pattern.finditer(text):
                start = max(0, m.start() - 20)
                end = min(len(text), m.end() + 80)
                # Avoid overlapping spans
                span_key = (start, end)
                if any(start < e and end > s for s, e in seen_spans):
                    continue
                seen_spans.add(span_key)

                unit_text = text[start:end]
                units.append(ProceduralUnit(
                    unit_id=f"{chunk.chunk_id}_u{len(units)}",
                    unit_type=unit_type,
                    text=unit_text,
                    chunk_id=chunk.chunk_id,
                    section_path=chunk.section_path,
                    evidence=[EvidenceSpan(text=unit_text, start=start, end=end, chunk_id=chunk.chunk_id)],
                ))

        return units

    def _llm_extract(self, chunk: ParsedChunk) -> List[ProceduralUnit]:
        """LLM-based extraction."""
        if not self.llm:
            return self._rule_extract(chunk)

        prompt = UNIT_EXTRACTION_PROMPT + json.dumps(chunk.text, ensure_ascii=False)
        try:
            response = self.llm.chat_json(
                system_prompt="You are a precise procedural-unit extractor. Output only valid JSON.",
                user_prompt=prompt,
                temperature=0.0,
            )
            raw_units = response.get("units", [])
        except Exception as e:
            # Fallback to rule-based on LLM failure
            print(f"LLM extraction failed for chunk {chunk.chunk_id}: {e}")
            return self._rule_extract(chunk)

        units = []
        for i, u in enumerate(raw_units):
            start = u.get("start", 0)
            end = u.get("end", len(chunk.text))
            unit_text = chunk.text[start:end] if 0 <= start < end <= len(chunk.text) else u.get("text", "")
            units.append(ProceduralUnit(
                unit_id=f"{chunk.chunk_id}_u{i}",
                unit_type=u.get("unit_type", "operation"),
                text=unit_text,
                chunk_id=chunk.chunk_id,
                section_path=chunk.section_path,
                evidence=[EvidenceSpan(text=unit_text, start=start, end=end, chunk_id=chunk.chunk_id)],
            ))

        return units

    def extract(self, chunk: ParsedChunk) -> List[ProceduralUnit]:
        """Extract procedural units from a single chunk."""
        if self.use_llm:
            return self._llm_extract(chunk)
        return self._rule_extract(chunk)

    def extract_all(self, chunks: List[ParsedChunk]) -> List[ProceduralUnit]:
        """Extract procedural units from all chunks."""
        all_units = []
        for chunk in chunks:
            units = self.extract(chunk)
            all_units.extend(units)
        return all_units


def main():
    import argparse
    from utils import read_jsonl, write_jsonl
    from llm_client import OpenAIClient

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=pathlib.Path, required=True, help="parsed_chunks.jsonl")
    parser.add_argument("--output", type=pathlib.Path, required=True, help="procedural_units.jsonl")
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--model", default="kimi-latest")
    parser.add_argument("--base-url", default="http://localhost:9999/v1")
    args = parser.parse_args()

    llm = None
    if args.use_llm:
        llm = OpenAIClient(model=args.model, base_url=args.base_url)

    extractor = UnitExtractor(llm=llm, use_llm=args.use_llm)
    records = read_jsonl(args.input)

    all_results = []
    for rec in records:
        chunks = [ParsedChunk.from_dict(c) for c in rec["chunks"]]
        units = extractor.extract_all(chunks)
        all_results.append({
            "doc_id": rec["doc_id"],
            "units": [u.to_dict() for u in units],
        })

    write_jsonl(args.output, all_results)
    total_units = sum(len(r["units"]) for r in all_results)
    print(f"Extracted {total_units} units from {len(records)} docs → {args.output}")


if __name__ == "__main__":
    main()
