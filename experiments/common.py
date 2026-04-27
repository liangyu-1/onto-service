from __future__ import annotations

import csv
import datetime as dt
import json
import os
import pathlib
import subprocess
import urllib.error
import urllib.request
from typing import Any, Dict, Iterable, List


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPERIMENTS_DIR = ROOT / "experiments"
RESULTS_DIR = EXPERIMENTS_DIR / "results"


def utc_ts() -> str:
    return dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def ensure_dir(path: pathlib.Path) -> pathlib.Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: pathlib.Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: pathlib.Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def write_jsonl(path: pathlib.Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: pathlib.Path, rows: List[Dict[str, Any]], columns: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in columns})


def run_cmd(command: str) -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            shell=True,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return {
            "command": command,
            "code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as e:  # pragma: no cover
        return {"command": command, "code": 999, "stdout": "", "stderr": str(e)}


def http_json(method: str, url: str, payload: Dict[str, Any] | None = None, timeout: int = 20) -> Dict[str, Any]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url=url, data=data, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = {"raw": raw}
            return {"ok": True, "status": resp.status, "body": body}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"raw": raw}
        return {"ok": False, "status": e.code, "body": body}
    except Exception as e:  # pragma: no cover
        return {"ok": False, "status": 0, "body": {"message": str(e)}}


def unwrap_result(body: Any) -> Any:
    if isinstance(body, dict) and "code" in body and "data" in body:
        return body.get("data")
    return body


def snapshot_environment() -> Dict[str, Any]:
    return {
        "timestamp_utc": dt.datetime.utcnow().isoformat() + "Z",
        "git_branch": run_cmd(f"cd {ROOT} && git branch --show-current").get("stdout"),
        "git_head": run_cmd(f"cd {ROOT} && git rev-parse HEAD").get("stdout"),
        "python_version": run_cmd("python --version").get("stdout"),
        "java_version": run_cmd("java -version").get("stderr"),
        "docker_version": run_cmd("docker --version").get("stdout"),
        "docker_compose_version": run_cmd("docker-compose --version").get("stdout"),
        "containers": run_cmd("docker ps --format '{{.Names}} {{.Status}}'").get("stdout"),
    }

