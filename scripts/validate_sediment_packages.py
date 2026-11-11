#!/usr/bin/env python3
"""Run every sediment package's own verifier (repository-side integration point).

A package declares its verifier in ``manifest.json`` (``entry.verifier``); this
runner discovers the packages under ``knowledge/sediment/`` and executes the
declared entry in a subprocess, so a package cannot silently opt out of
verification and a broken package cannot take the runner down.  The source
repository of a package is read-only and usually absent in CI; when it is, the
package's verifier reports ``source:available = FAIL`` and this runner treats the
package as **not run** (reported, never counted as passed).

This module is the integration point of the sediment pipeline into the repository
gate: ``scripts/validate_knowledge_assets.py`` imports it and calls
``run_package`` for every discovered package, folding a failure into its own error
list.

Exit codes: 0 all runnable packages pass (or none runnable), 1 a package failed,
2 no ``knowledge/sediment`` directory at all.

Usage::

    python3 scripts/validate_sediment_packages.py            # all packages
    python3 scripts/validate_sediment_packages.py --json runs/sediment_packages.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEDIMENT = ROOT / "knowledge" / "sediment"


def packages(root: Path) -> list[Path]:
    return sorted(p.parent for p in root.glob("*/manifest.json"))


def run_package(pkg: Path, timeout: int = 900) -> dict:
    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    entry = manifest.get("entry", {}).get("verifier")
    if not entry:
        return {"package": pkg.name, "status": "no_entry", "returncode": None, "stdout": ""}
    source = manifest.get("source", {})
    env = dict(os.environ)
    env.setdefault(source.get("root_env", "SEDIMENT_SRC_REPO"), source.get("default_root", ""))
    # ``--no-write``: a validator must not mutate the committed run artefacts
    proc = subprocess.run(
        [sys.executable, str(ROOT / entry), "--no-write"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=timeout, env=env,
    )
    out = proc.stdout
    if proc.returncode == 0:
        status = "pass"
    elif "source:available" in out and "FAIL" in out and "NOT run" in out:
        status = "skipped-source-unavailable"
    else:
        status = "fail"
    return {
        "package": pkg.name,
        "status": status,
        "returncode": proc.returncode,
        "entry": entry,
        "source_sha": source.get("sha"),
        "tail": "\n".join(out.strip().splitlines()[-3:]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(SEDIMENT))
    ap.add_argument("--json", default="")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"no sediment directory at {root}; nothing to validate")
        return 2
    results = [run_package(pkg, args.timeout) for pkg in packages(root)]
    for res in results:
        print(f"{res['status']:>26}  {res['package']}  rc={res['returncode']}")
        if res["status"] == "fail":
            print(res["tail"])
    payload = {"root": str(root.relative_to(ROOT)), "n_packages": len(results),
               "statuses": {r["package"]: r["status"] for r in results}, "results": results}
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 1 if any(r["status"] == "fail" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())