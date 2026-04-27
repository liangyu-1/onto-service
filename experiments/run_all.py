from __future__ import annotations

import pathlib
import subprocess
import sys
from typing import List, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.common import RESULTS_DIR, utc_ts
from experiments.paper_pack import build_paper_artifact_pack


def run_step(label: str, cmd: List[str]) -> int:
    print(f"[run] {label}: {' '.join(cmd)}")
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent
    steps: List[Tuple[str, List[str]]] = [
        ("exp1_exp2", ["python", str(root / "run_exp1_exp2.py")]),
        ("exp3_counterfactual", ["python", str(root / "run_exp3_counterfactual.py")]),
        ("exp4_generalization", ["python", str(root / "run_exp4_generalization.py")]),
        ("exp5_drift", ["python", str(root / "run_exp5_drift.py")]),
    ]
    for label, cmd in steps:
        code = run_step(label, cmd)
        if code != 0:
            print(f"[fail] {label} exit={code}")
            return code

    pack_dir = RESULTS_DIR / f"paper_artifact_pack_{utc_ts()}"
    pack = build_paper_artifact_pack(pack_dir)
    print(f"[done] artifact pack: {pack_dir} items={len(pack['index'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

