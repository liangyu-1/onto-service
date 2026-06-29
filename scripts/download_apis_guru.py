#!/usr/bin/env python3
"""Download APIs.guru OpenAPI Directory specs.

Usage:
    python scripts/download_apis_guru.py [--max-apis N] [--output-dir DIR] [--copy-to-openapi]

Defaults download a curated subset suitable for Paper 1 function-layer benchmark
construction. The full directory has ~2500 APIs; this script is conservative to
avoid pulling enormous or broken specs.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

DEFAULT_OUTPUT_DIR = Path("dataset/function_layer_benchmarks/raw/apis_guru")
DEFAULT_OPENAPI_DIR = Path("dataset/function_layer_benchmarks/openapi")
LIST_URL = "https://api.apis.guru/v2/list.json"
BASE_SPEC_URL = "https://api.apis.guru/v2/specs"

# Services already downloaded in the existing pilot subset.
PILOT_PROVIDERS = {
    "stripe.com",
    "github.com",
    "slack.com",
    "twilio.com",
    "atlassian.com",
    "xero.com",
    "box.com",
    "docusign.com",
    "sendgrid.com",
}

# Prefer APIs from these categories when curating a diverse subset.
PREFERRED_CATEGORIES = {
    "developer_tools",
    "financial",
    "messaging",
    "payments",
    "storage",
    "social",
    "ecommerce",
    "analytics",
    "crm",
    "project_management",
}


def fetch_json(url: str, timeout: float = 60.0) -> Any:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def count_operations(spec: dict[str, Any]) -> int:
    paths = spec.get("paths") or {}
    count = 0
    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue
        for method in path_item:
            if method.lower() in {"get", "post", "put", "patch", "delete", "head", "options"}:
                count += 1
    return count


def spec_size_mb(spec: dict[str, Any]) -> float:
    return len(json.dumps(spec).encode("utf-8")) / (1024 * 1024)


def provider_name(api_key: str) -> str:
    return api_key.split(":")[0]


def safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)


def load_existing_list(output_dir: Path) -> dict[str, Any] | None:
    list_path = output_dir / "list.json"
    if list_path.exists():
        with list_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_list(output_dir: Path, data: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    list_path = output_dir / "list.json"
    with list_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def category_score(info: dict[str, Any]) -> int:
    cats = info.get("x-apisguru-categories") or []
    score = 0
    for cat in cats:
        if cat in PREFERRED_CATEGORIES:
            score += 2
        else:
            score += 1
    return score


def rank_apis(api_list: dict[str, Any], max_per_provider: int = 3) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    """Return (api_key, version_info, info) ranked by curation heuristics.

    Heuristics:
    - prefer APIs in PREFERRED_CATEGORIES;
    - prefer OpenAPI 3.x over Swagger 2.0;
    - keep at most max_per_provider specs from the same provider to ensure diversity.
    """
    ranked: list[tuple[str, dict[str, Any], dict[str, Any], int]] = []
    provider_counts: dict[str, int] = {}

    for api_key, meta in api_list.items():
        versions = meta.get("versions") or {}
        preferred = meta.get("preferred")
        if preferred and preferred in versions:
            version_key = preferred
        elif versions:
            version_key = sorted(versions.keys())[-1]
        else:
            continue
        version_info = versions[version_key]
        info = version_info.get("info") or {}

        prov = provider_name(api_key)
        if provider_counts.get(prov, 0) >= max_per_provider:
            continue

        score = category_score(info)

        # Prefer OpenAPI 3.x
        openapi_ver = str(version_info.get("openapiVer") or "")
        if openapi_ver.startswith("3."):
            score += 3
        elif openapi_ver.startswith("2."):
            score += 1

        # Mild bonus for APIs with explicit preferred version
        if preferred:
            score += 1

        # Prefer APIs with a reasonable title/description length
        title = info.get("title") or ""
        desc = info.get("description") or ""
        if len(title) >= 3 and len(desc) >= 20:
            score += 1

        provider_counts[prov] = provider_counts.get(prov, 0) + 1
        ranked.append((api_key, version_info, info, score))

    ranked.sort(key=lambda x: x[3], reverse=True)
    return [(k, v, i) for k, v, i, _ in ranked]


def download_spec(api_key: str, version_info: dict[str, Any], output_dir: Path, timeout: float) -> Path | None:
    specs_dir = output_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    # Prefer the official APIs.guru cached JSON link if present.
    link = version_info.get("link")
    swagger_url = version_info.get("swaggerUrl")
    url = link or swagger_url
    if not url:
        print(f"  [skip] no download URL for {api_key}")
        return None

    file_name = safe_filename(f"{api_key.replace(':', '_')}.openapi.json")
    out_path = specs_dir / file_name

    if out_path.exists():
        print(f"  [exists] {out_path}")
        return out_path

    try:
        print(f"  [download] {api_key} from {url}")
        spec = fetch_json(url, timeout=timeout)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)
        return out_path
    except Exception as e:
        print(f"  [error] {api_key}: {e}")
        return None


def update_manifest(output_dir: Path, downloaded: list[tuple[str, str, Path | None]]) -> None:
    manifest_path = output_dir.parent / "download_manifest.json"
    existing: dict[str, Any] = {"downloaded_at": "", "sources": []}
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8") as f:
            existing = json.load(f)

    spec_files = [
        str(p.relative_to(output_dir.parent)).replace("\\", "/")
        for _, _, p in downloaded
        if p
    ]

    # Update or append the APIs.guru source entry.
    sources = existing.get("sources", [])
    apis_guru_entry = next((s for s in sources if s.get("name") == "APIs.guru OpenAPI Directory"), None)
    entry = {
        "name": "APIs.guru OpenAPI Directory",
        "type": "openapi_directory_subset",
        "files": sorted(set(spec_files)),
        "notes": f"The full list has many API entries. The local OpenAPI subset contains {len(spec_files)} service specs.",
    }
    if apis_guru_entry:
        apis_guru_entry.update(entry)
    else:
        sources.append(entry)

    existing["downloaded_at"] = datetime.now(timezone.utc).isoformat()
    existing["sources"] = sources

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


def copy_to_openapi(downloaded: list[tuple[str, str, Path | None]], openapi_dir: Path, max_files: int | None) -> None:
    openapi_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for api_key, version_key, p in downloaded:
        if p is None:
            continue
        target = openapi_dir / f"{safe_filename(api_key.replace(':', '_'))}.json"
        if target.exists():
            continue
        shutil.copy2(p, target)
        copied += 1
        if max_files and copied >= max_files:
            break
    print(f"[copy] {copied} specs copied to {openapi_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download APIs.guru OpenAPI Directory specs.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-apis", type=int, default=50, help="Maximum number of APIs to download.")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--refresh-list", action="store_true", help="Re-fetch list.json even if it exists.")
    parser.add_argument("--copy-to-openapi", action="store_true", help="Copy downloaded specs to dataset/function_layer_benchmarks/openapi/")
    parser.add_argument("--max-openapi-files", type=int, default=None, help="Limit specs copied to openapi/")
    args = parser.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch or load list.json
    api_list = None
    if not args.refresh_list:
        api_list = load_existing_list(output_dir)
    if api_list is None:
        print(f"[fetch] {LIST_URL}")
        api_list = fetch_json(LIST_URL, timeout=args.timeout)
        save_list(output_dir, api_list)
        print(f"[saved] list.json with {len(api_list)} API entries")
    else:
        print(f"[load] existing list.json with {len(api_list)} API entries")

    ranked = rank_apis(api_list)
    print(f"[rank] {len(ranked)} APIs ranked for curation")

    downloaded: list[tuple[str, str, Path | None]] = []
    for idx, (api_key, version_info, info) in enumerate(ranked[: args.max_apis], 1):
        version_key = version_info.get("version", "unknown")
        print(f"[{idx}/{args.max_apis}] {api_key} (v{version_key}) - {info.get('title', '')}")
        p = download_spec(api_key, version_info, output_dir, args.timeout)
        downloaded.append((api_key, version_key, p))
        time.sleep(0.2)

    successful = [d for d in downloaded if d[2] is not None]
    print(f"[done] downloaded {len(successful)}/{len(downloaded)} specs to {output_dir / 'specs'}")

    update_manifest(output_dir, downloaded)
    print(f"[manifest] updated {output_dir.parent / 'download_manifest.json'}")

    if args.copy_to_openapi:
        copy_to_openapi(downloaded, DEFAULT_OPENAPI_DIR, args.max_openapi_files)

    return 0


if __name__ == "__main__":
    sys.exit(main())
