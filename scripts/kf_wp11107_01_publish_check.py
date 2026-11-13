#!/usr/bin/env python3
"""Post-publish round-trip check for wp-11107-01.

Verifies that what the platform stored is what this worktree produced:
  * GET /tensor/reports/{result_id}.markdown == docs/kf_result_wp-11107-01.md (byte-identical)
  * the single ```json block parses to the kf_result envelope on disk
  * each figure is retrievable at GET /tensor/reports/{id}/figures/{name} with the local sha256
  * GET /tensor/reports/11107 (the SOURCE) still hashes to contract input.source_hash

    python3 scripts/kf_wp11107_01_publish_check.py 14784
Writes docs/kf/wp-11107-01/publish_check.json
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-11107-01"
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
CONTRACT_HASH = "sha256:799d7ffedf0f95500aca8aa289c2778f4e9d15795c29cd32a412c41aae57c982"


def _get(path: str, tok: str | None = None, raw: bool = False):
    req = urllib.request.Request(API + path)
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            body = r.read()
            return r.status, body if raw else json.loads(body.decode())
    except urllib.error.HTTPError as exc:
        return exc.code, None


def main(rid: str) -> int:
    data = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    tok = json.loads(urllib.request.urlopen(
        urllib.request.Request(API + "/auth/login", data=data,
                               headers={"Content-Type": "application/json"}), timeout=60).read())["access_token"]

    local_md = (ROOT / "docs" / "kf_result_wp-11107-01.md").read_text(encoding="utf-8")
    snap_path = PKG / "published.json"
    snap = json.loads(snap_path.read_text(encoding="utf-8")) if snap_path.exists() else {}
    st, rec = _get("/tensor/reports/" + rid, tok)
    checks = []
    remote_md = rec.get("markdown") or ""
    ok = st == 200 and remote_md == local_md
    checks.append({"id": "result_markdown_roundtrip", "pass": ok,
                   "evidence": "GET /tensor/reports/%s -> HTTP %s, stored chars %d vs local %d, "
                               "sha256 stored %s local %s"
                               % (rid, st, len(remote_md), len(local_md),
                                  hashlib.sha256(remote_md.encode()).hexdigest()[:16],
                                  hashlib.sha256(local_md.encode()).hexdigest()[:16])})
    local_sha = hashlib.sha256(local_md.encode("utf-8")).hexdigest()
    checks.append({"id": "worktree_copy_is_published_snapshot",
                   "pass": bool(snap) and local_sha == snap.get("markdown_sha256"),
                   "evidence": "docs/kf_result_wp-11107-01.md sha256 %s vs published.json %s "
                               "(regenerate? then re-publish)" % (local_sha, snap.get("markdown_sha256"))})

    block = local_md.split("```json", 1)[1].split("```", 1)[0]
    env_disk = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
    checks.append({"id": "json_block_equals_envelope", "pass": json.loads(block) == env_disk,
                   "evidence": "single ```json block (count=%d) parses equal to docs/kf/wp-11107-01/kf_result.json"
                               % local_md.count("```json")})

    figs = []
    for f in (PKG / "figures").glob("*.png"):
        st2, body = _get("/tensor/reports/%s/figures/%s" % (rid, f.name), tok, raw=True)
        local_sha = hashlib.sha256(f.read_bytes()).hexdigest()
        remote_sha = hashlib.sha256(body).hexdigest() if body else None
        figs.append({"name": f.name, "http_status": st2, "bytes": len(body or b""),
                     "sha256_local": local_sha, "sha256_remote": remote_sha,
                     "match": remote_sha == local_sha})
    checks.append({"id": "figures_roundtrip", "pass": all(x["match"] for x in figs),
                   "evidence": "GET /tensor/reports/%s/figures/<name> sha256 vs local: %s"
                               % (rid, {x["name"]: x["match"] for x in figs})})

    st3, src = _get("/tensor/reports/11107", tok)
    src_hash = "sha256:" + hashlib.sha256(src["markdown"].encode("utf-8")).hexdigest()
    checks.append({"id": "source_unchanged", "pass": src_hash == CONTRACT_HASH,
                   "evidence": "GET /tensor/reports/11107 -> %s (contract %s)" % (src_hash, CONTRACT_HASH)})

    out = {"package_id": "wp-11107-01", "result_report_id": rid,
           "checks": checks, "all_pass": all(c["pass"] for c in checks),
           "figures": figs,
           "note": "round-trip evidence for the publication step; not a verification verdict"}
    (PKG / "publish_check.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                                            encoding="utf-8")
    for c in checks:
        print("%-32s %s" % (c["id"], "PASS" if c["pass"] else "FAIL"))
    print("all_pass=%s" % out["all_pass"])
    return 0 if out["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "14784"))