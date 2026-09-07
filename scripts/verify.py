"""Run both local labs without opening their holdouts; save reviewable evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
LABS = ("classification", "incident_duration")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", choices=(*LABS, "all"), default="all")
    parser.add_argument("--mode", choices=("tests", "demo", "all"), default="all")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "verification")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "LAB_MODULE": "solucion"}
    records = []
    selected = LABS if args.lab == "all" else (args.lab,)
    for lab in selected:
        tasks = []
        if args.mode in ("tests", "all"):
            tasks.append(("tests", ["-m", "unittest", "-v"]))
        if args.mode in ("demo", "all"):
            tasks.append(("development", ["solucion.py"]))
        for name, command in tasks:
            result = subprocess.run(
                [sys.executable, *command],
                cwd=ROOT / "labs" / lab,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            log = output / f"{lab}-{name}.log"
            log.write_text(result.stdout + result.stderr)
            record = {
                "lab": lab,
                "command": "python " + " ".join(command),
                "working_directory": f"labs/{lab}",
                "exit_code": result.returncode,
                "log": log.name,
                "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
            }
            if name == "development" and result.returncode == 0:
                payload, _ = json.JSONDecoder().raw_decode(result.stdout)
                closed = (
                    payload.get("holdout_opened") is False
                    if lab == "classification"
                    else payload.get("holdout_status") == "CLOSED"
                )
                if not closed or "holdout" in payload:
                    raise RuntimeError(f"Unexpected holdout output in {lab}")
                (output / f"{lab}-development.json").write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
                )
                record["holdout_closed"] = True
            records.append(record)
            print(f"{lab}: {name}: exit {result.returncode}", flush=True)
    report = {
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.system(),
        "machine": platform.machine(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("numpy", "pandas", "scikit-learn", "scipy", "joblib", "threadpoolctl", "python-dateutil", "six")
        },
        "runs": records,
        "scope": "Synthetic data; development and contract tests only. No holdout evaluation requested.",
    }
    (output / "run.json").write_text(json.dumps(report, indent=2) + "\n")
    if any(record["exit_code"] != 0 for record in records):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
