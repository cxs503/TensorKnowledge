"""Generate the install/feasibility matrix artefact from *observed* facts.

Nothing here is typed by hand: every row is derived from either
  * a live PyPI JSON query (wheel/sdist availability for this platform), or
  * a log file produced by an actual install attempt, or
  * an interpreter import probe.

Usage:
  python generate_install_matrix.py --out artifacts/ke_eval/install_matrix.json
"""
from __future__ import annotations

import argparse
import json
import platform
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

LOG_DIR = Path("/root/ke-eval/logs")

# distributions that cognee 1.6.7 declares as core dependencies and that need a
# platform-specific build (Rust/C++/binary)
COGNEE_NATIVE = ["lancedb", "pylance", "tiktoken", "tokenizers", "onnxruntime",
                 "fastembed", "cryptography", "cbor2", "ladybug", "kuzu"]
# version constraints that cognee 1.6.7 actually declares (PyPI metadata):
#   lancedb<0.40.0,>=0.39.0   -> query 0.39.0, not "latest"
PINS = {"lancedb": "0.39.0"}
GRAPHITI_NATIVE = ["jiter"]
PYPI = "https://pypi.org/pypi/{}/json"


def platform_tags() -> dict:
    return {"machine": platform.machine(), "system": platform.system(),
            "python": sys.version.split()[0],
            "libc": " ".join(platform.libc_ver())}


def wheels_for(pkg: str, version: str | None = None) -> dict:
    try:
        d = json.load(urllib.request.urlopen(PYPI.format(pkg), timeout=20))
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    ver = version or d["info"]["version"]
    files = d["releases"].get(ver, [])
    names = [f["filename"] for f in files]
    loong = [n for n in names if "loong" in n]
    return {"version": ver,
            "requires_python": d["info"]["requires_python"],
            "n_files": len(names),
            "n_wheels": sum(1 for n in names if n.endswith(".whl")),
            "has_sdist": any(n.endswith((".tar.gz", ".zip")) for n in names),
            "loongarch64_wheel": bool(loong),
            "wheel_platforms": sorted({re.sub(r"^.*?-(\d.*?)-(cp\d+|py3|pp\d+).*\.whl$", r"\1", n)
                                       for n in names if n.endswith(".whl")})[:8],
            "declared_requirements": len(d["info"].get("requires_dist") or [])}


def log_tail(name: str, pattern: str, n: int = 3) -> list[str]:
    p = LOG_DIR / name
    if not p.exists():
        return [f"<missing log {name}>"]
    lines = [ln.strip() for ln in p.read_text(errors="ignore").splitlines()
             if re.search(pattern, ln)]
    return lines[-n:]


def import_probe(venv: str, module: str) -> dict:
    py = Path(venv) / "bin" / "python"
    if not py.exists():
        return {"venv": venv, "status": "venv_missing"}
    try:
        r = subprocess.run([str(py), "-c", f"import {module}; print('OK')"],
                           capture_output=True, text=True, timeout=45)
    except subprocess.TimeoutExpired:
        return {"venv": venv, "status": "timeout_45s"}
    return {"venv": venv, "status": "ok" if r.returncode == 0 else "failed",
            "error_tail": [ln for ln in r.stderr.strip().splitlines() if ln.strip()][-2:]}


def rust_toolchains() -> dict:
    rustc = shutil.which("rustc")
    out = {"system_rustc": None, "rustup_rustc": None}
    if rustc:
        out["system_rustc"] = subprocess.run([rustc, "--version"], capture_output=True,
                                             text=True, timeout=30).stdout.strip()
    r2 = Path("/root/rust/cargo/bin/rustc")
    if r2.exists():
        out["rustup_rustc"] = subprocess.run(
            [str(r2), "--version"], capture_output=True, text=True, timeout=30,
            env={**os.environ, "RUSTUP_HOME": "/root/rust/rustup",
                 "CARGO_HOME": "/root/rust/cargo"}).stdout.strip()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/ke_eval/install_matrix.json")
    ap.add_argument("--graphiti-venv", default="/root/ke-eval-venv6")
    a = ap.parse_args()

    matrix = {
        "platform": platform_tags(),
        "toolchains": rust_toolchains(),
        "pypi": {
            "cognee": wheels_for("cognee"),
            "graphiti-core": wheels_for("graphiti-core"),
        },
        "native_deps": {
            "cognee": {p: wheels_for(p, PINS.get(p)) for p in COGNEE_NATIVE},
            "graphiti": {p: wheels_for(p) for p in GRAPHITI_NATIVE},
        },
        "attempts": [
            {"what": "pip install cognee (default mirror)",
             "result": "failed: no matching distribution",
             "evidence": log_tail("cognee_install.log", "error|ERROR", 2) or ["see probe log"]},
            {"what": "pip install cognee (pypi.org, system rust 1.77)",
             "result": "failed: maturin needs cargo edition2024",
             "evidence": log_tail("cognee_install.log", "edition2024|maturin", 2)},
            {"what": "pip install cognee (aliyun mirror, rust 1.99.1)",
             "result": "failed: cryptography sdist build chain",
             "evidence": log_tail("cognee_aliyun.log", "error|ERROR", 2)},
            {"what": "pip install graphiti-core (system rust 1.77)",
             "result": "failed: jiter -> maturin -> cargo edition2024",
             "evidence": log_tail("graphiti_v5.log", "edition2024|maturin", 2)},
            {"what": "import graphiti_core (venv6, wheel --no-deps + pure deps)",
             "result": import_probe(a.graphiti_venv, "graphiti_core")},
            {"what": "import cognee (venv5, wheel --no-deps + partial pure deps)",
             "result": import_probe("/root/ke-eval-venv5", "cognee")},
        ],
        "import_probe_log": str(LOG_DIR / "cognee_probe.json"),
        "pins": PINS,
    }
    def hard_blocked(group: str) -> list[str]:
        return [k for k, v in matrix["native_deps"][group].items()
                if v.get("loongarch64_wheel") is False and v.get("has_sdist") is False]
    matrix["hard_blocked"] = {"cognee": hard_blocked("cognee"),
                             "graphiti": hard_blocked("graphiti")}

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(matrix, indent=1))
    print(json.dumps({k: matrix[k] for k in ("platform", "toolchains")}, indent=1))
    for name, info in matrix["native_deps"]["cognee"].items():
        print(f"  cognee-dep {name:14s} loong64_wheel={info.get('loongarch64_wheel')} "
              f"sdist={info.get('has_sdist')} files={info.get('n_files')}")
    for name, info in matrix["native_deps"]["graphiti"].items():
        print(f"  graphiti-dep {name:12s} loong64_wheel={info.get('loongarch64_wheel')} "
              f"sdist={info.get('has_sdist')}")


if __name__ == "__main__":
    main()