"""Progressive minimal-install probe for a graph/vector memory framework.

Purpose: on a loongarch64 container without loong64 wheels for several Rust
extensions, determine *exactly* which import in the framework's top-level
`import` chain is unreachable. Strategy: install the distribution with
`--no-deps`, then repeatedly try `import <pkg>`; on ModuleNotFoundError install
the missing distribution from a curated module->dist map, but refuse to install
distributions that are known to be unavailable on this platform (recorded as
hard blockers). Every step is logged to JSON as evidence.

Usage:
  python probe_minimal_install.py --venv /root/ke-eval-venv5 --pkg cognee \
      --dist /path/cognee-1.6.7-py3-none-any.whl --out logs/probe.json
"""
import argparse
import json
import subprocess
import sys

MIRROR = ["--index-url", "https://mirrors.aliyun.com/pypi/simple/",
          "--trusted-host", "mirrors.aliyun.com", "--timeout", "30", "--retries", "1"]

# module name -> (dist name, note). Only distributions that are pure-python or
# buildable with plain gcc on loongarch64 are listed.
OPTIONAL_PURE = {
    "structlog": ("structlog", "pure-python logging"),
    "fastapi": ("fastapi", "pure-python ASGI"),
    "starlette": ("starlette", "pure-python ASGI"),
    "pydantic_settings": ("pydantic-settings", "pure-python"),
    "aiofiles": ("aiofiles", "pure-python"),
    "aiohttp": ("aiohttp", "C-extension, gcc sdist"),
    "aiosqlite": ("aiosqlite", "pure-python"),
    "aiolimiter": ("aiolimiter", "pure-python"),
    "alembic": ("alembic", "pure-python"),
    "sqlalchemy": ("sqlalchemy", "C-extension optional, gcc sdist"),
    "jinja2": ("jinja2", "pure-python"),
    "dateparser": ("dateparser", "pure-python"),
    "filelock": ("filelock", "pure-python"),
    "filetype": ("filetype", "pure-python"),
    "langdetect": ("langdetect", "pure-python"),
    "limits": ("limits", "pure-python"),
    "nbformat": ("nbformat", "pure-python"),
    "pypdf": ("pypdf", "pure-python"),
    "dotenv": ("python-dotenv", "pure-python"),
    "rdflib": ("rdflib", "pure-python, PROV-O capable"),
    "tenacity": ("tenacity", "pure-python"),
    "pympler": ("Pympler", "pure-python"),
    "typing_extensions": ("typing-extensions", "pure-python"),
    "urllib3": ("urllib3", "pure-python"),
    "uvicorn": ("uvicorn", "pure-python"),
    "gunicorn": ("gunicorn", "pure-python"),
    "packaging": ("packaging", "pure-python"),
    "multipart": ("python-multipart", "pure-python"),
    "networkx": ("networkx", "pure-python graph engine"),
    "dateutil": ("python-dateutil", "pure-python"),
    "fastapi_users": ("fastapi-users", "pure-python auth"),
    "litellm": ("litellm", "pure-python LLM gateway"),
    "dlt": ("dlt", "pure-python ELT"),
    "fakeredis": ("fakeredis", "pure-python redis stub"),
    "huggingface_hub": ("huggingface-hub", "pure-python client"),
    "certifi": ("certifi", "pure-python CA bundle"),
    "aiohttp": ("aiohttp", "C-extension, gcc sdist"),
    "click": ("click", "pure-python"),
    "psutil": ("psutil", "C-extension, gcc sdist"),
    "yaml": ("PyYAML", "C-extension optional"),
    "tqdm": ("tqdm", "pure-python"),
    "rich": ("rich", "pure-python"),
    "httpx": ("httpx", "pure-python"),
    "jiter": ("jiter", "Rust; needs cargo edition2024+"),
}

# Distributions known to be unavailable/unbuildable here (evidence in report).
HARD_BLOCK = {
    "lancedb": "Rust vector store: PyPI ships only macos/manylinux aarch64+x86_64 wheels, no sdist",
    "pylance": "Rust lance core; no loong64 wheel",
    "fastembed": "requires onnxruntime binary",
    "onnxruntime": "binary only, no loong64 build",
    "tokenizers": "Rust/maturin; sdist build needs cargo edition2024",
    "tiktoken": "Rust/maturin",
    "kuzu": "C++ sdist (multi-hour), no loong64 wheel",
    "ladybug": "graph adapter with native component",
    "enola-cli": "proprietary CLI wheel, no loong64 build",
}


def probe(venv_py, pkg):
    r = subprocess.run([venv_py, "-c", f"import {pkg}; print('IMPORT_OK')"],
                       capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venv", required=True)
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--dist", required=True, help="wheel/sdist already installed with --no-deps")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-steps", type=int, default=40)
    a = ap.parse_args()
    py = f"{a.venv}/bin/python"
    pip = f"{a.venv}/bin/pip"

    subprocess.run([pip, "install", "-q", "--no-deps", *MIRROR, a.dist], check=False)
    steps = []
    for i in range(a.max_steps):
        ok, out = probe(py, a.pkg)
        if ok:
            steps.append({"step": i, "status": "import_ok"})
            break
        line = [ln for ln in out.strip().splitlines() if ln.strip()][-1]
        mod = None
        if "No module named '" in line:
            mod = line.split("No module named '")[1].split("'")[0].split(".")[0]
        entry = {"step": i, "import_error_tail": line, "module": mod}
        if mod is None:
            entry["status"] = "blocked_non_module_error"
            steps.append(entry)
            break
        if mod in HARD_BLOCK:
            entry["status"] = "blocked_unavailable_dist"
            entry["reason"] = HARD_BLOCK[mod]
            steps.append(entry)
            break
        if mod not in OPTIONAL_PURE:
            entry["status"] = "blocked_unmapped_module"
            steps.append(entry)
            break
        dist, note = OPTIONAL_PURE[mod]
        r = subprocess.run([pip, "install", "-q", *MIRROR, dist],
                           capture_output=True, text=True)
        entry.update({"installed": dist, "note": note, "install_rc": r.returncode})
        if r.returncode:
            entry["status"] = "install_failed"
            entry["install_tail"] = (r.stdout + r.stderr).strip().splitlines()[-3:]
            steps.append(entry)
            break
        steps.append(entry)

    json.dump({"python": sys.version, "package": a.pkg, "steps": steps},
              open(a.out, "w"), indent=1)
    print(json.dumps(steps[-5:], indent=1))


if __name__ == "__main__":
    main()