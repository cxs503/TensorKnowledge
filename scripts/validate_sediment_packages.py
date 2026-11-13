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

Per-package statuses (always printed as an index, so one bad asset cannot hide
behind a single opaque red line)::

    pass                        verifier exited 0
    skipped-source-unavailable  read-only source repo absent -> nothing was checked
    blocked-missing-dependency  a python module the verifier needs is not installed
                                (``entry.requires``); the asset itself was not judged
    error-verifier-crashed      verifier emitted no PASS/FAIL line at all
    fail                        verifier ran and at least one check failed

The runner never trades a real failure for a green gate: ``fail``,
``error-verifier-crashed`` and ``blocked-missing-dependency`` all keep the gate
red.  What they must not do is report the *same* line for three different
causes -- the failure index says which of the three happened, and for a missing
dependency names the module and the requirements file to install.

Exit codes: 0 all runnable packages pass (or none runnable, or only source
skips), 1 a package failed / crashed / is blocked, 2 no ``knowledge/sediment``
directory at all.

Usage::

    python3 scripts/validate_sediment_packages.py            # all packages
    python3 scripts/validate_sediment_packages.py --json runs/sediment_packages.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEDIMENT = ROOT / "knowledge" / "sediment"
REQUIREMENTS = ROOT / "requirements-validation.txt"

# statuses that keep the repository gate red
FAILING_STATUSES = ("fail", "error-verifier-crashed", "blocked-missing-dependency")
MODULE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
CHECK_LINE_RE = re.compile(r"^(PASS|FAIL)\s+\S", re.M)
MISSING_MODULE_RE = re.compile(r"No module named '([A-Za-z0-9_.]+)'")


def packages(root: Path) -> list[Path]:
    return sorted(p.parent for p in root.glob("*/manifest.json"))


def _last_error_line(text: str) -> str:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def _requirements_hint() -> str:
    rel = REQUIREMENTS.relative_to(ROOT)
    return f"python -m pip install -r {rel}"


def probe_requirements(modules: list[str], timeout: int = 120) -> dict[str, str]:
    """Return ``{module: error}`` for every declared module that fails to import.

    The probe is a plain ``import`` in the same interpreter that will run the
    verifier, so it catches both "not installed" and "installed but broken".
    """
    missing: dict[str, str] = {}
    for module in modules:
        if not isinstance(module, str) or not MODULE_RE.match(module):
            missing[str(module)] = "invalid module name in manifest entry.requires"
            continue
        proc = subprocess.run([sys.executable, "-c", f"import {module}"],
                              capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            missing[module] = _last_error_line(proc.stderr) or f"import {module} failed"
    return missing


def run_package(pkg: Path, timeout: int = 900) -> dict:
    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    entry_spec = manifest.get("entry", {})
    entry = entry_spec.get("verifier")
    if not entry:
        return {"package": pkg.name, "status": "no_entry", "returncode": None,
                "reason": "manifest declares no entry.verifier", "stdout": ""}
    source = manifest.get("source", {})
    requires = [m for m in entry_spec.get("requires", []) if isinstance(m, str)]

    result = {
        "package": pkg.name,
        "entry": entry,
        "source_sha": source.get("sha"),
        "requires": requires,
    }

    # ---- declared dependencies first: a missing module is not a bad asset ----
    missing = probe_requirements(requires)
    if missing:
        detail = "; ".join(f"missing python module '{m}' ({err})" for m, err in missing.items())
        return {**result, "status": "blocked-missing-dependency", "returncode": None,
                "missing_requirements": sorted(missing),
                "reason": f"{detail} -- run: {_requirements_hint()}", "stdout": ""}

    env = dict(os.environ)
    env.setdefault(source.get("root_env", "SEDIMENT_SRC_REPO"), source.get("default_root", ""))
    # ``--no-write``: a validator must not mutate the committed run artefacts
    proc = subprocess.run(
        [sys.executable, str(ROOT / entry), "--no-write"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=timeout, env=env,
    )
    out, err = proc.stdout, proc.stderr
    n_checks = len(CHECK_LINE_RE.findall(out))
    tail = "\n".join(out.strip().splitlines()[-3:])
    base = {**result, "returncode": proc.returncode, "n_checks": n_checks, "tail": tail}

    if proc.returncode == 0:
        return {**base, "status": "pass", "reason": f"{n_checks} checks pass"}

    # legacy / self-declared source skip: the verifier says it did not run
    if "source:available" in out and "NOT run" in out:
        return {**base, "status": "skipped-source-unavailable",
                "reason": "read-only source repository absent; quote/number checks NOT run"}

    # environment failure reported by the verifier itself (``env:dependency``)
    if "env:dependency" in out:
        detail = next((ln for ln in out.splitlines() if "env:dependency" in ln), "")
        return {**base, "status": "blocked-missing-dependency",
                "reason": f"{detail.strip()} -- run: {_requirements_hint()}"}

    # crash before any check line: dependency import error inside the verifier
    crash_module = MISSING_MODULE_RE.search(err) or MISSING_MODULE_RE.search(out)
    if crash_module and n_checks == 0:
        module = crash_module.group(1)
        return {**base, "status": "blocked-missing-dependency", "missing_requirements": [module],
                "reason": (f"verifier crashed importing '{module}' before any check ran "
                           f"({_last_error_line(err)}) -- run: {_requirements_hint()}")}

    if n_checks == 0:
        return {**base, "status": "error-verifier-crashed",
                "reason": f"verifier exited {proc.returncode} without a PASS/FAIL line: "
                          f"{_last_error_line(err) or _last_error_line(out) or 'no output'}"}

    n_pass = len(re.findall(r"^PASS\s", out, re.M))
    return {**base, "status": "fail",
            "reason": f"{n_checks - n_pass}/{n_checks} checks failed; last lines: {tail}"}


def summarise(results: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for res in results:
        counts[res["status"]] = counts.get(res["status"], 0) + 1
    failing = [r for r in results if r["status"] in FAILING_STATUSES]
    return {
        "n_packages": len(results),
        "counts": counts,
        "ok": not failing,
        "failure_index": [
            {"package": r["package"], "status": r["status"], "returncode": r.get("returncode"),
             "reason": r.get("reason", "")}
            for r in failing
        ],
    }


def render_index(results: list[dict]) -> str:
    """Human-readable index: one line per asset, then the failing-asset list."""
    width = max([len(r["status"]) for r in results] + [5])
    name_width = max([len(r["package"]) for r in results] + [7])
    out = [f"{r['status']:<{width}}  {r['package']:<{name_width}}  rc={r['returncode']}"
           for r in results]
    summary = summarise(results)
    counts = ", ".join(f"{k}={v}" for k, v in sorted(summary["counts"].items()))
    out.append(f"-- sediment assets: {summary['n_packages']} package(s) [{counts}]")
    if summary["failure_index"]:
        out.append(f"FAILED ASSETS ({len(summary['failure_index'])}):")
        for item in summary["failure_index"]:
            out.append(f"  - {item['package']}: {item['status']} rc={item['returncode']} :: {item['reason']}")
    return "\n".join(out)


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
    print(render_index(results))
    summary = summarise(results)
    try:  # a --root outside the repository is legitimate (tests, ad-hoc runs)
        root_label = str(root.resolve().relative_to(ROOT))
    except ValueError:
        root_label = str(root.resolve())
    payload = {"root": root_label, "summary": summary,
               "statuses": {r["package"]: r["status"] for r in results}, "results": results}
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())