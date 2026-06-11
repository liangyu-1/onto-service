#!/usr/bin/env python3
"""Robust wrapper around `deepxiv search`.

The upstream CLI can return zero results for narrow ontology/IR queries in
hybrid mode even when BM25 has good hits. This wrapper retries across modes and
lightly normalized query variants before giving up.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from typing import Any


SEARCH_MODES = ("hybrid", "bm25", "vector")


def query_variants(query: str) -> list[str]:
    variants: list[str] = []

    def add(candidate: str) -> None:
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if candidate and candidate not in variants:
            variants.append(candidate)

    add(query)
    add(re.sub(r"[-_/]", " ", query))
    add(re.sub(r"[^0-9A-Za-z\s]", " ", query))

    words = re.findall(r"[0-9A-Za-z]+", query)
    if len(words) > 4:
        add(" ".join(words[:4]))
        add(" ".join(words[-4:]))

    return variants


def result_count(payload: dict[str, Any]) -> int:
    for key in ("total_count", "total"):
        value = payload.get(key)
        if isinstance(value, int):
            return value
    for key in ("result", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)
    return 0


def result_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("result", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def run_deepxiv(query: str, mode: str, limit: int) -> tuple[int, dict[str, Any] | None, str]:
    cmd = [
        "deepxiv",
        "search",
        query,
        "--limit",
        str(limit),
        "--mode",
        mode,
        "--format",
        "json",
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        return proc.returncode, None, proc.stderr.strip() or proc.stdout.strip()
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return 1, None, f"invalid JSON from deepxiv: {exc}"
    return 0, payload, ""


def truncate_payload(payload: dict[str, Any], limit: int) -> dict[str, Any]:
    payload = dict(payload)
    for key in ("result", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            payload[key] = value[:limit]
    return payload


def print_text(
    payload: dict[str, Any],
    used_query: str,
    used_mode: str,
    attempts: list[dict[str, Any]],
    limit: int,
) -> None:
    papers = result_list(truncate_payload(payload, limit))
    print(f"Found {result_count(payload)} papers")
    print(f"Used query: {used_query}")
    print(f"Used mode: {used_mode}")
    print(f"Attempts: {len(attempts)}")
    print()
    for index, paper in enumerate(papers, 1):
        title = paper.get("title", "No title")
        arxiv_id = paper.get("arxiv_id", "unknown")
        citations = paper.get("citation_count", paper.get("citation", "unknown"))
        url = paper.get("url", "")
        print(f"{index}. {title}")
        print(f"   arXiv: {arxiv_id} | Citations: {citations}")
        if url:
            print(f"   URL: {url}")
        tldr = paper.get("tldr") or paper.get("abstract", "")
        if tldr:
            print(f"   {tldr[:300]}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Robust deepxiv search wrapper")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Number of results")
    parser.add_argument("--format", "-f", choices=("text", "json"), default="text")
    parser.add_argument(
        "--modes",
        default=",".join(SEARCH_MODES),
        help="Comma-separated modes to try, default: hybrid,bm25,vector",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.5,
        help="Seconds to wait between fallback attempts, default: 0.5",
    )
    args = parser.parse_args()

    if not shutil.which("deepxiv"):
        print("deepxiv is not on PATH", file=sys.stderr)
        return 127

    modes = [mode.strip() for mode in args.modes.split(",") if mode.strip()]
    invalid_modes = [mode for mode in modes if mode not in SEARCH_MODES]
    if invalid_modes:
        print(f"invalid modes: {', '.join(invalid_modes)}", file=sys.stderr)
        return 2

    attempts: list[dict[str, Any]] = []
    last_error = ""

    first_attempt = True
    for candidate_query in query_variants(args.query):
        for mode in modes:
            if not first_attempt and args.sleep > 0:
                time.sleep(args.sleep)
            first_attempt = False
            code, payload, error = run_deepxiv(candidate_query, mode, args.limit)
            count = result_count(payload or {})
            attempts.append(
                {
                    "query": candidate_query,
                    "mode": mode,
                    "return_code": code,
                    "count": count,
                    "error": error,
                }
            )
            if error:
                last_error = error
                # Connection failures are upstream/service/network problems. Do not
                # fan out to every query variant and overload the API further.
                if "Failed to connect" in error or "Connection error" in error:
                    if args.format == "json":
                        print(
                            json.dumps(
                                {
                                    "used_query": None,
                                    "used_mode": None,
                                    "attempts": attempts,
                                    "error": last_error,
                                    "result": {"total_count": 0, "result": []},
                                },
                                ensure_ascii=False,
                                indent=2,
                            )
                        )
                    else:
                        print("deepxiv connection failed; not retrying expanded variants.")
                        print(f"Error: {last_error}", file=sys.stderr)
                    return 1
            if payload and count > 0:
                if args.format == "json":
                    print(
                        json.dumps(
                            {
                                "used_query": candidate_query,
                                "used_mode": mode,
                                "attempts": attempts,
                                "result": truncate_payload(payload, args.limit),
                            },
                            ensure_ascii=False,
                            indent=2,
                        )
                    )
                else:
                    print_text(payload, candidate_query, mode, attempts, args.limit)
                return 0

    if args.format == "json":
        print(
            json.dumps(
                {
                    "used_query": None,
                    "used_mode": None,
                    "attempts": attempts,
                    "error": last_error,
                    "result": {"total_count": 0, "result": []},
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print("Found 0 papers after fallback attempts.")
        if last_error:
            print(f"Last error: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
