#!/usr/bin/env python3
"""Probe resolvability of every referenced asset for report 11204.

Two resolvers, both read-only:
  1. platform HTTP  – GET endpoints under /api/v1/tensor/... (Bearer token)
  2. local filesystem – bounded-depth existence probe inside this worktree

Nothing is written outside work/wp-11204-01/probes.json. No asset is promoted to
"resolved" here; the builder decides resolution status from these raw results.
"""
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(HERE, "work", "wp-11204-01")
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

HTTP_PATHS = [
    "/tensor/reports/11204/figures/fig1_ct_field_and_seb_cohesive",
    "/tensor/reports/11204/figures/fig1_ct_field_and_seb_cohesive.png",
    "/tensor/reports/11204/figures/fig2_mixed_mode_and_j2",
    "/tensor/reports/11204/figures/fig3_j_comparison_and_convergence",
    "/tensor/reports/11204/figures",
    "/tensor/reports/11204/attachments",
    "/tensor/reports/11204/artifacts",
    "/tensor/artifacts/m9422/verification.json",
    "/tensor/artifacts/m9422/acceptance.json",
]

# paths named verbatim in the report body; probed inside this worktree only
FS_PATHS = [
    "src/tensorphysics/fem_nonlinear/",
    "src/tensorphysics/fem_nonlinear/j2_plasticity.py",
    "src/tensorphysics/fem_nonlinear/cohesive3d.py",
    "src/tensorphysics/fem_nonlinear/plane_strain_fem.py",
    "src/tensorphysics/fem_nonlinear/anchors.py",
    "src/tensorphysics/fem_nonlinear/verification.py",
    "scripts/m9422_run_verification.py",
    "scripts/m9422_figures.py",
    "tests/test_fem_elastoplastic_cohesive3d.py",
    "artifacts/m9422/verification.json",
    "artifacts/m9422/acceptance.json",
    "figures/m9422/fig1_ct_field_and_seb_cohesive.png",
    "figures/m9422/fig2_mixed_mode_and_j2.png",
    "figures/m9422/fig3_j_comparison_and_convergence.png",
]


def login():
    user = os.environ.get("TENSOR_AGENT_USER", "")
    pw = os.environ.get("TENSOR_AGENT_PASS", "")
    req = urllib.request.Request(
        API + "/auth/login",
        data=json.dumps({"username": user, "password": pw}).encode(),
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    return d.get("access_token") or d.get("token")


def probe_http(token, path):
    req = urllib.request.Request(API + path, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            return {
                "resolver": "platform_http",
                "path": path,
                "http_status": r.status,
                "bytes": len(body),
                "content_type": r.headers.get("Content-Type"),
                "body_prefix": body[:180].decode("utf-8", "replace"),
            }
    except urllib.error.HTTPError as e:
        body = e.read()[:400]
        return {
            "resolver": "platform_http",
            "path": path,
            "http_status": e.code,
            "bytes": len(body),
            "content_type": e.headers.get("Content-Type") if e.headers else None,
            "body_prefix": body.decode("utf-8", "replace"),
        }
    except Exception as e:  # noqa: BLE001
        return {"resolver": "platform_http", "path": path, "http_status": None, "error": str(e)}


def probe_fs(rel):
    ap = os.path.join(HERE, rel)
    return {
        "resolver": "worktree_fs",
        "path": rel,
        "exists": os.path.exists(ap),
        "is_dir": os.path.isdir(ap),
        "bytes": os.path.getsize(ap) if os.path.isfile(ap) else None,
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    token = login()
    http = [probe_http(token, p) for p in HTTP_PATHS]
    fs = [probe_fs(p) for p in FS_PATHS]
    res = {
        "report_id": "11204",
        "http_base": API,
        "http_probes": http,
        "fs_probes": fs,
        "fs_root": HERE,
        "repo_of_record": "TensorPhysics",
        "note": (
            "All referenced implementation artefacts belong to the TensorPhysics repository; "
            "this worktree is a TensorKnowledge checkout, so a missing path here is NOT evidence "
            "that the asset does not exist — it only means it is outside this package's reach."
        ),
    }
    with open(os.path.join(OUT, "probes.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps({"http": [(p["path"], p.get("http_status")) for p in http],
                      "fs_present": [p["path"] for p in fs if p["exists"]]},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())