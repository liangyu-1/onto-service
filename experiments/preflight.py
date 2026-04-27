from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Dict, List, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.common import RESULTS_DIR, ensure_dir, http_json, snapshot_environment, unwrap_result, write_json


DEFAULT_API_BASE = "http://localhost:8080/api/v1"


def _expect_count(name: str, actual: int, expected_min: int, checks: List[Dict[str, Any]]) -> bool:
    ok = actual >= expected_min
    checks.append(
        {
            "check": name,
            "ok": ok,
            "actual": actual,
            "expected_min": expected_min,
            "message": "" if ok else f"{name} expected >= {expected_min}, got {actual}",
        }
    )
    return ok


def _fetch_list(api_base: str, path: str) -> Tuple[bool, List[Dict[str, Any]], str]:
    resp = http_json("GET", f"{api_base}{path}")
    if not resp["ok"]:
        return False, [], f"HTTP {resp['status']}: {resp['body']}"
    data = unwrap_result(resp["body"])
    if not isinstance(data, list):
        return False, [], f"Expected list from {path}, got {type(data).__name__}"
    return True, data, ""


def run_preflight(api_base: str = DEFAULT_API_BASE, env_lock_path: str = "") -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    ok_all = True

    domain_targets = [("TPCH", "1.0.0"), ("PlantGraph", "1.0.0")]
    for domain, version in domain_targets:
        ok_obj, object_types, msg_obj = _fetch_list(api_base, f"/semantic/{domain}/{version}/object-types")
        ok_rel, relations, msg_rel = _fetch_list(api_base, f"/semantic/{domain}/{version}/relationships")
        ok_map, mappings, msg_map = _fetch_list(api_base, f"/abox-mappings/{domain}/{version}")

        if not ok_obj:
            ok_all = False
            checks.append({"check": f"{domain}.object_types.http", "ok": False, "message": msg_obj})
            object_types = []
        if not ok_rel:
            ok_all = False
            checks.append({"check": f"{domain}.relations.http", "ok": False, "message": msg_rel})
            relations = []
        if not ok_map:
            ok_all = False
            checks.append({"check": f"{domain}.mappings.http", "ok": False, "message": msg_map})
            mappings = []

        ok_all &= _expect_count(f"{domain}.object_types", len(object_types), 1, checks)
        ok_all &= _expect_count(f"{domain}.relations", len(relations), 0, checks)
        ok_all &= _expect_count(f"{domain}.mappings", len(mappings), 1, checks)

    env = snapshot_environment()
    if env_lock_path:
        lock_file = pathlib.Path(env_lock_path)
        if lock_file.exists():
            env_lock = json.loads(lock_file.read_text(encoding="utf-8"))
            for key, actual_key in [
                ("java_version_contains", "java_version"),
                ("docker_version_contains", "docker_version"),
                ("docker_compose_version_contains", "docker_compose_version"),
            ]:
                expected = str(env_lock.get(key, "")).strip()
                if not expected:
                    continue
                actual_val = str(env.get(actual_key, ""))
                ok = expected in actual_val
                checks.append(
                    {
                        "check": f"env.{actual_key}",
                        "ok": ok,
                        "expected_contains": expected,
                        "actual": actual_val,
                        "message": "" if ok else f"{actual_key} does not contain '{expected}'",
                    }
                )
                ok_all &= ok

            required_containers = env_lock.get("required_containers", [])
            running_containers = str(env.get("containers", ""))
            for name in required_containers:
                ok = str(name) in running_containers
                checks.append(
                    {
                        "check": f"env.container.{name}",
                        "ok": ok,
                        "message": "" if ok else f"container not running: {name}",
                    }
                )
                ok_all &= ok

    report = {
        "ok": ok_all,
        "api_base": api_base,
        "env_lock_path": env_lock_path,
        "checks": checks,
        "environment": env,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Experiment preflight checks for TPCH/PlantGraph")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE, help="API base URL")
    parser.add_argument(
        "--env-lock",
        default=str(pathlib.Path(__file__).resolve().parent / "configs" / "environment.lock.json"),
        help="Expected environment lock config",
    )
    parser.add_argument("--out-dir", default="", help="Output directory under experiments/results")
    args = parser.parse_args()

    if args.out_dir:
        out_dir = ensure_dir(pathlib.Path(args.out_dir))
    else:
        out_dir = ensure_dir(RESULTS_DIR / "preflight")

    report = run_preflight(api_base=args.api_base, env_lock_path=args.env_lock)
    write_json(out_dir / "preflight_report.json", report)

    if report["ok"]:
        print("Preflight OK")
        return 0
    print("Preflight FAILED. See preflight_report.json")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

