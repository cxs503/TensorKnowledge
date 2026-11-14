#!/usr/bin/env python3
"""wp-9478-02 — build + independently verify the delivered KF result.

Independence: this script does not reuse the cached source file. It logs in to
the platform, fetches report 9478 again, recomputes sha256 itself, and resolves
every locator that is embedded in the result *from the freshly fetched bytes*.
If any of that disagrees with what the artefact declares, it exits non-zero.

Outputs: kf_result.json (the delivered payload), verify.json (the check log).
Run: python3 docs/kf/wp-9478-02/scripts/verify_result.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parents[2]

CONTRACT_SOURCE_HASH = "sha256:133dbe58a74bd7549b66b2b86e5dc2e517f603c3ea65af45947d4cb5c1599e28"


def fresh_source() -> tuple[str, dict]:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(base + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as fh:
        token = json.loads(fh.read())["access_token"]
    req = urllib.request.Request(base + "/tensor/reports/9478",
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as fh:
        record = json.loads(fh.read())
    return record["markdown"], record


def main() -> int:
    cls = json.loads((PKG / "classification.json").read_text(encoding="utf-8"))
    src = cls["source"]
    result = {
        "package_id": cls["package_id"],
        "task_type": cls["task_type"],
        "contract_version": cls["contract_version"],
        "report_id": cls["report_id"],
        "provenance": {
            "source_uri": src["source_uri"],
            "source_field": src["source_field"],
            "source_hash": CONTRACT_SOURCE_HASH,
            "source_hash_matches": None,      # filled below, never self-asserted
            "title": src["title_from_record"],
            "scenario_key": src["scenario_key"],
            "chars": src["chars"],
        },
        "outputs": {"classification.json": cls},
    }

    checks: list[dict] = []
    text, record = fresh_source()
    digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    result["provenance"]["source_hash_matches"] = (digest == CONTRACT_SOURCE_HASH)
    checks.append({"check": "fresh fetch source_hash == contract",
                   "pass": digest == CONTRACT_SOURCE_HASH, "detail": digest})
    checks.append({"check": "fresh fetch chars == contract/declared",
                   "pass": len(text) == src["chars"], "detail": f"chars={len(text)}"})

    embedded = result["outputs"]["classification.json"]
    bad = []
    for e in embedded["evidence"]:
        loc = e["locator"]
        s, t, q = loc["start_offset"], loc["end_offset"], loc["quote"]
        ok = (0 <= s < t <= len(text) and text[s:t] == q
              and loc["content_hash"] == "sha256:" + hashlib.sha256(q.encode()).hexdigest()
              and len(q) >= 12)
        byte_ok = (loc["byte_start_utf8"] == len(text[:s].encode("utf-8"))
                   and loc["byte_end_utf8"] == len(text[:t].encode("utf-8")))
        if not (ok and byte_ok):
            bad.append({"evidence": e["id"], "char_ok": ok, "byte_ok": byte_ok})
    checks.append({"check": "embedded locators resolve against freshly fetched bytes",
                   "pass": not bad,
                   "detail": f"{len(embedded['evidence']) - len(bad)}/"
                             f"{len(embedded['evidence'])} resolved; failing={bad[:3]}"})

    ids = ([c["id"] for c in embedded["claims"]] + [e["id"] for e in embedded["evidence"]]
           + [u["id"] for u in embedded["unresolved"]])
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    checks.append({"check": "no duplicate ids", "pass": not dupes, "detail": f"n={len(ids)}"})
    missing = [c["id"] for c in embedded["claims"] if not c["evidence_refs"]]
    checks.append({"check": "every claim has evidence", "pass": not missing,
                   "detail": f"claims={len(embedded['claims'])} unresolved={len(embedded['unresolved'])}"})

    schema_path = REPO / "schemas" / "kf_result.v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        import jsonschema
        jsonschema.validate(result, schema)
        checks.append({"check": "kf_result.v1.schema.json", "pass": True,
                       "detail": schema["$id"]})
    except Exception as exc:  # noqa: BLE001
        checks.append({"check": "kf_result.v1.schema.json", "pass": False, "detail": str(exc)})

    # cross-source checks: record metadata vs body markdown — two different sources,
    # so this is an independent consistency probe, not a re-read of the artefact.
    rec_figs = (record.get("figures") or [])
    body_caps = cls["structure"]["figure_refs"]
    checks.append({"check": "record figure assets vs body figure captions",
                   "pass": len(rec_figs) == len(body_caps),
                   "detail": f"record={len(rec_figs)} named, body={len(body_caps)} captions, "
                             f"named captions in body={sum(1 for f in body_caps if not f['label_empty'])}"})
    checks.append({"check": "record tags name a solver the body never names",
                   "pass": text.count("TensorFEM") == 0,
                   "detail": f"record tags={[t for t in (record.get('tags') or []) if 'Tensor' in str(t)]}, "
                             f"body TensorFEM={text.count('TensorFEM')}, "
                             f"body TensorLBM={text.count('TensorLBM')}"})

    ok = all(c["pass"] for c in checks)
    (PKG / "kf_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (PKG / "verify.json").write_text(json.dumps({
        "package_id": cls["package_id"], "report_id": cls["report_id"],
        "checks": checks, "all_pass": ok,
        "fresh_fetch": {"source_hash": digest, "chars": len(text),
                        "record_title": record.get("title"),
                        "record_mission_id": record.get("mission_id"),
                        "record_tags": record.get("tags"),
                        "record_figures_len": len(record.get("figures") or []),
                        "record_figure_names": [f.get("name") for f in (record.get("figures") or [])],
                        "body_fsi2_count": text.count("fsi2"),
                        "body_tensorfem_count": text.count("TensorFEM"),
                        "body_tensorlbm_count": text.count("TensorLBM")},
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({c["check"]: c["pass"] for c in checks}, ensure_ascii=False))
    print("kf_result bytes:", (PKG / "kf_result.json").stat().st_size)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())