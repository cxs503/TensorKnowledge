#!/usr/bin/env python3
"""Run the source's own guard tests against the pinned commit (m5054 provenance probe).

The knowledge package may only claim "the delivery contract is broken at this
sha" if that is executed, not asserted.  This script materialises the guard test
and the three committed benchmark reports out of ``TensorSPH@<sha>`` with
``git archive`` (so the working tree of the source repo is untouched), runs
pytest there, and writes the raw result to ``docs/sediment/tk-sediment-m5054/runs/source_guard/``
(``docs/`` because the push gate drops top-level ``runs/`` as a record area: the
probe output has to travel with the reviewable package, not stay on one host).

    python3 scripts/sediment_m5054_source_guard.py
    python3 scripts/sediment_m5054_source_guard.py --source-repo /path/to/TensorSPH

Exit code mirrors pytest (0 = guard tests pass, 1 = they fail).  A failing pin is
exactly what the honesty check wants to record, so 1 is a successful *run*; the
run artifact, not the exit code, is the deliverable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA = "82b72a15c044259d1e7c8d638e9273705fa42e7b"
ARCHIVE_PATHS = [
    "tests/test_threed_artifacts.py",
    "benchmarks/threed_kernel/report.json",
    "benchmarks/threed_shear/report.json",
    "benchmarks/threed_hydrostatic/report.json",
]
MISSING_DOC = "docs/verification_threed.md"
OUT_DIR = ROOT / "docs" / "sediment" / "tk-sediment-m5054" / "runs" / "source_guard"


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, check=False) if not check else subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-repo",
                        default=os.environ.get("TENSORSPH_REPO",
                                               "/root/tensor-ecosystem/TensorSPH"))
    parser.add_argument("--sha", default=SHA)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args(argv)
    repo = Path(args.source_repo)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. the doc the README links: does it exist at the pin?
    doc = git(repo, "cat-file", "-e", f"{args.sha}:{MISSING_DOC}", check=False)

    # 2. materialise the guarded artifacts and run the guard tests there
    tmp = Path(tempfile.mkdtemp(prefix="m5054-guard-"))
    archive = subprocess.run(["git", "-C", str(repo), "archive", args.sha, *ARCHIVE_PATHS],
                             capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", str(tmp)], input=archive.stdout, check=True)
    pytest_cmd = [sys.executable, "-m", "pytest", "tests/test_threed_artifacts.py", "-v",
                  "--no-header", "-p", "no:cacheprovider", "--tb=no"]
    proc = subprocess.run(pytest_cmd, cwd=tmp, capture_output=True, text=True)

    tail = (proc.stdout + proc.stderr).strip().splitlines()
    summary = ""
    for line in reversed(tail):
        if re.search(r"\d+ (passed|failed|error)", line):
            summary = line.strip("= ").strip()
            break
    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", summary)) else 0
    failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", summary)) else 0
    cases = []
    for line in tail:
        m = re.match(r"^(tests/\S+::\S+)\s+(PASSED|FAILED|ERROR)", line)
        if m:
            cases.append({"test": m.group(1), "status": m.group(2)})
    if not cases:  # -q prints node ids with F/. markers; recover ids from the source file
        node_ids = re.findall(r"^def (test_\w+)\(", (tmp / "tests" / "test_threed_artifacts.py")
                              .read_text(encoding="utf-8"), re.M)
        cases = [{"test": f"tests/test_threed_artifacts.py::{n}", "status": "unknown"}
                 for n in node_ids]

    manifest = {
        "probe": "source guard tests at the pinned commit",
        "source": {"repo": str(repo), "sha": args.sha,
                   "commit_time": git(repo, "show", "-s", "--format=%cI", args.sha).stdout.strip()},
        "archive_paths": ARCHIVE_PATHS,
        "doc_link_check": {
            "path": MISSING_DOC,
            "command": f"git -C {repo} cat-file -e {args.sha}:{MISSING_DOC}",
            "returncode": doc.returncode,
            "exists": doc.returncode == 0,
        },
        "pytest": {
            "command": " ".join(pytest_cmd),
            "cwd": str(tmp),
            "returncode": proc.returncode,
            "summary": summary,
            "passed": passed,
            "failed": failed,
            "cases": cases,
        },
        "conclusion": ("guard tests cannot pass at this commit: committed reports say "
                       "verdict=fail while the guard asserts verdict=pass"
                       if failed else "guard tests pass at this commit"),
    }
    (out / "source_guard.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                          encoding="utf-8")
    (out / "pytest_output.txt").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    (out / "repro.sh").write_text(
        "#!/bin/sh\n"
        f"# reproduce the m5054 source-guard probe (sha256 of source_guard.json is in "
        f"the extract manifest)\n"
        f"python3 scripts/sediment_m5054_source_guard.py --source-repo {repo} --sha {args.sha}\n",
        encoding="utf-8")
    size = (out / "source_guard.json").stat().st_size
    print(f"source guard: {passed} passed / {failed} failed -> {out / 'source_guard.json'} "
          f"({size} B, sha256 {hashlib.sha256((out / 'source_guard.json').read_bytes()).hexdigest()[:16]}...)")
    print(f"doc link {MISSING_DOC}: exit {doc.returncode} (exists={doc.returncode == 0})")
    print(f"pytest summary: {summary}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())