"""Agent 2: StructureParser — parses procedural documents into structured chunks."""
from __future__ import annotations

import pathlib
import re
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from action_ir import ParsedChunk


class StructureParser:
    """Parses synthetic procedural documents into structured chunks.

    Preserves section path, block type, step number, table context,
    and evidence offsets. This reduces the risk that a flat chunker
    merges unrelated steps or loses procedural order.
    """

    def __init__(self):
        self.heading_pattern = re.compile(r"^(#{1,6})\s+(.*)$")
        self.numbered_step_pattern = re.compile(r"^(\d+)\.\s+(.*)$")
        self.bullet_pattern = re.compile(r"^[-*]\s+(.*)$")
        self.bold_label_pattern = re.compile(r"\*\*([^*]+)\*\*:\s*(.*)")
        self.table_row_pattern = re.compile(r"^\|.*\|$")

    def parse(self, text: str, doc_id: str = "") -> List[ParsedChunk]:
        """Parse a document into structured chunks."""
        lines = text.split("\n")
        chunks: List[ParsedChunk] = []
        section_stack: List[str] = []
        current_table: Optional[List[str]] = None
        offset = 0

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            start_offset = offset
            offset += len(line) + 1  # +1 for newline

            # Skip empty lines
            if not stripped:
                i += 1
                continue

            # Heading
            m = self.heading_pattern.match(stripped)
            if m:
                level = len(m.group(1))
                title = m.group(2).strip()
                # Update section stack
                section_stack = section_stack[:level - 1]
                section_stack.append(title)
                chunks.append(ParsedChunk(
                    chunk_id=f"{doc_id}_h{len(chunks)}",
                    chunk_type="heading",
                    text=title,
                    section_path=list(section_stack),
                    evidence_offset=(start_offset, offset - 1),
                ))
                i += 1
                continue

            # Numbered step
            m = self.numbered_step_pattern.match(stripped)
            if m:
                step_num = m.group(1)
                step_text = m.group(2).strip()
                # Absorb indented continuation lines
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    if next_line.strip() and not next_line.startswith(" ") and not next_line.startswith("\t"):
                        break
                    if next_line.strip():
                        step_text += " " + next_line.strip()
                        offset += len(next_line) + 1
                    else:
                        offset += 1
                    j += 1
                chunks.append(ParsedChunk(
                    chunk_id=f"{doc_id}_s{len(chunks)}",
                    chunk_type="numbered_step",
                    text=step_text,
                    section_path=list(section_stack),
                    step_number=step_num,
                    evidence_offset=(start_offset, offset - 1),
                ))
                i = j
                continue

            # Bullet
            m = self.bullet_pattern.match(stripped)
            if m:
                bullet_text = m.group(1).strip()
                chunks.append(ParsedChunk(
                    chunk_id=f"{doc_id}_b{len(chunks)}",
                    chunk_type="bullet",
                    text=bullet_text,
                    section_path=list(section_stack),
                    evidence_offset=(start_offset, offset - 1),
                ))
                i += 1
                continue

            # Table row
            if self.table_row_pattern.match(stripped):
                if current_table is None:
                    current_table = []
                current_table.append(stripped)
                i += 1
                continue
            elif current_table is not None:
                # Flush table
                chunks.append(ParsedChunk(
                    chunk_id=f"{doc_id}_t{len(chunks)}",
                    chunk_type="table",
                    text="\n".join(current_table),
                    section_path=list(section_stack),
                    table_context={"rows": len(current_table)},
                    evidence_offset=(start_offset - sum(len(r) + 1 for r in current_table), offset - 1),
                ))
                current_table = None
                continue

            # Bold label (e.g., **Precondition**: ...)
            m = self.bold_label_pattern.match(stripped)
            if m:
                label = m.group(1).strip()
                content = m.group(2).strip()
                chunk_type = "warning" if label.lower() in {"warning", "caution", "note"} else "paragraph"
                chunks.append(ParsedChunk(
                    chunk_id=f"{doc_id}_p{len(chunks)}",
                    chunk_type=chunk_type,
                    text=f"{label}: {content}",
                    section_path=list(section_stack),
                    evidence_offset=(start_offset, offset - 1),
                ))
                i += 1
                continue

            # Default: paragraph
            chunks.append(ParsedChunk(
                chunk_id=f"{doc_id}_p{len(chunks)}",
                chunk_type="paragraph",
                text=stripped,
                section_path=list(section_stack),
                evidence_offset=(start_offset, offset - 1),
            ))
            i += 1

        # Flush remaining table
        if current_table is not None:
            chunks.append(ParsedChunk(
                chunk_id=f"{doc_id}_t{len(chunks)}",
                chunk_type="table",
                text="\n".join(current_table),
                section_path=list(section_stack),
                table_context={"rows": len(current_table)},
                evidence_offset=(start_offset, offset - 1),
            ))

        return chunks


def main():
    import argparse
    import json
    from utils import read_jsonl, write_jsonl

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=pathlib.Path, required=True, help="synthetic_docs.jsonl")
    parser.add_argument("--output", type=pathlib.Path, required=True, help="parsed_chunks.jsonl")
    args = parser.parse_args()

    docs = read_jsonl(args.input)
    parser_obj = StructureParser()
    all_chunks = []

    for doc in docs:
        chunks = parser_obj.parse(doc["text"], doc_id=doc["doc_id"])
        all_chunks.append({
            "doc_id": doc["doc_id"],
            "chunks": [c.to_dict() for c in chunks],
        })

    write_jsonl(args.output, all_chunks)
    print(f"Parsed {len(docs)} documents into {sum(len(r['chunks']) for r in all_chunks)} chunks → {args.output}")


if __name__ == "__main__":
    main()
