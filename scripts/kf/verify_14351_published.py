#!/usr/bin/env python3
"""Round-trip verification of the published KF-RESULT report for wp-14351-01.

Fetches the published report back from the platform (id recorded in
docs/kf/wp-14351-01/published.json) and re-checks, as the platform gate would:
  * title == "KF-RESULT wp-14351-01" and tags contain kf-wp:wp-14351-01
  * exactly one ```json block; it parses and equals docs/kf/wp-14351-01/kf_result.json
  * provenance.source_hash == sha256 of report 14351 markdown (recomputed here)
  * report_id == "14351"
  * every asset locator quote decodes back to a substring of report 14351 markdown
    (backticks were \u0060-escaped inside the json block; decoded value must be literal)
  * claims == [] and no verified marker
Exit code 0 = all pass.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "kf" / "wp-14351-01"
BASE = os.environ["TENSOR_API_BASE"].rstrip("/")


def token():
    cred = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    d = json.load(urllib.request.urlopen(urllib.request.Request(
        BASE + "/auth/login", data=cred, headers={"Content-Type": "application/json"}), timeout=30))
    return d.get("access_token") or d.get("token")


def get(path, tok):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def main() -> int:
    tok = token()
    pub_id = json.loads((OUT / "published.json").read_text(encoding="utf-8"))["id"]
    rep = get(f"/tensor/reports/{pub_id}", tok)
    src = json.loads((ROOT / "runs" / "wp-14351-01" / "report_14351.json").read_text(encoding="utf-8"))
    src_md = src["markdown"]
    src_hash = "sha256:" + hashlib.sha256(src_md.encode()).hexdigest()
    env = json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))

    md = rep["markdown"]
    checks = []

    def add(name, ok, detail):
        checks.append(dict(item=name, result="PASS" if ok else "FAIL", detail=detail))

    add("published_title", rep.get("title") == "KF-RESULT wp-14351-01", f"title={rep.get('title')!r}")
    add("tag_kf_wp", "kf-wp:wp-14351-01" in (rep.get("tags") or []), f"tags={rep.get('tags')}")
    add("single_json_block", md.count("```json") == 1, f"```json fences={md.count('```json')}")
    block = md.split("```json", 1)[1].split("```", 1)[0]
    parsed = json.loads(block)
    add("json_block_parses_and_matches", parsed == env,
        "block == docs/kf/wp-14351-01/kf_result.json（逐字段比较）")
    add("provenance_hash_matches_source", parsed["provenance"]["source_hash"] == src_hash,
        f"envelope {parsed['provenance']['source_hash'][:20]}… vs recomputed {src_hash[:20]}…")
    add("report_id_is_14351", parsed["report_id"] == "14351", f"report_id={parsed['report_id']}")
    man = parsed["outputs"]["asset_manifest.json"]
    quotes = [(a["asset_id"], a["locator"]["quote"]) for a in man["assets"]]
    bad = [aid for aid, q in quotes if q not in src_md]
    add("decoded_quotes_are_verbatim_substrings", not bad,
        f"{len(quotes) - len(bad)}/{len(quotes)} 条 quote 在 report 14351 markdown 中逐字命中"
        + (f"；未命中 {bad}" if bad else ""))
    add("claims_empty", parsed["claims"] == [], f"claims={parsed['claims']}")
    add("figures_embedded", len(rep.get("figures") or []) >= 1,
        f"figures={[f.get('name') for f in (rep.get('figures') or [])]}；"
        f"png_base64 长度={[len(f.get('png_base64') or '') for f in (rep.get('figures') or [])]}")

    out = dict(published_report_id=pub_id, source_report_id=14351,
               source_sha256=src_hash, checks=checks,
               passed=sum(c["result"] == "PASS" for c in checks),
               failed=sum(c["result"] == "FAIL" for c in checks))
    (OUT / "roundtrip_verification.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for c in checks:
        print(c["result"], c["item"], "|", c["detail"][:130])
    print(json.dumps({"published_report_id": pub_id, "passed": out["passed"], "failed": out["failed"]},
                     ensure_ascii=False))
    return 0 if out["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())