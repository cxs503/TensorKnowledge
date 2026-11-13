#!/usr/bin/env python3
"""Self-check of the wp-7216-04 report: single json block, schema, verbatim quotes.

    python3 scripts/kf_wp721604_verify_report.py

Checks
  1. the markdown holds exactly one ```json fenced block and it parses;
  2. the envelope validates against schemas/kf_result.v1.schema.json and its
     provenance.source_hash equals the sha256 of the live report markdown copy;
  3. the block's package_id / task_type / report_id match this work package;
  4. every 「…」 quotation in the evidence table is a substring of the report
     markdown (zero hand-copying: quotes are looked up, not trusted);
  5. the figure exists, is a PNG and its sha256 is recorded in the report.
Exit code 0 only when every check passes.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MD = REPO / "docs/kf/wp-7216-04/KF-RESULT-wp-7216-04.md"
SRC = REPO / "runs/wp-7216-04/source_7216.md"
FIG = REPO / "figures/wp-7216-04/review_map.png"


def main() -> int:
    md = MD.read_text(encoding="utf-8")
    source = SRC.read_text(encoding="utf-8")
    rows = []

    def check(name: str, ok: bool, detail: str) -> None:
        rows.append({"check": name, "ok": bool(ok), "detail": detail})

    blocks = re.findall(r"```json\n(.*?)```", md, re.S)
    check("single_json_block", len(blocks) == 1, f"json blocks={len(blocks)}")
    env = json.loads(blocks[0]) if blocks else {}
    check("json_parses", bool(env), f"keys={sorted(env)}")

    import jsonschema
    schema = json.loads((REPO / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    errs = list(jsonschema.Draft202012Validator(schema).iter_errors(env))
    check("schema_pass", not errs, f"errors={[e.message for e in errs][:3]}")

    live = "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
    prov = env.get("provenance") or {}
    check("provenance_hash_matches_live", prov.get("source_hash") == live,
          f"declared={prov.get('source_hash')} live={live}")
    check("envelope_identity",
          env.get("package_id") == "wp-7216-04"
          and env.get("task_type") == "04-independent-review"
          and env.get("report_id") == "7216",
          f"{env.get('package_id')}/{env.get('task_type')}/{env.get('report_id')}")

    # quotations in the evidence table must be verbatim source substrings
    # only the evidence table quotes claim to be verbatim source; 「…」 elsewhere in
    # the prose mark paraphrase, so the scan is scoped to section 4.
    start = md.index("## ④")
    end = md.index("**非阻塞观察**", start)
    evidence = md[start:end]
    quotes = re.findall(r"「([^」]{8,})」", evidence)
    bad = [q for q in quotes if q not in source]
    check("quotes_verbatim_in_source", not bad,
          f"{len(quotes)} quotations checked, not found={[b[:40] for b in bad][:5]}")

    check("figure_present", FIG.is_file() and FIG.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n",
          f"path={FIG} bytes={FIG.stat().st_size if FIG.is_file() else 0}")
    rep = (env.get("outputs") or {}).get("review_report.json") or {}
    fig_hash = hashlib.sha256(FIG.read_bytes()).hexdigest() if FIG.is_file() else ""
    check("figure_hash_recorded_in_report", fig_hash in md,
          f"sha256:{fig_hash}")
    check("no_verified_claim",
          rep.get("verification_status") == "not_verified_by_reviewer"
          and '"verified": true' not in blocks[0].lower(),
          "verification_status=%s" % rep.get("verification_status"))

    failed = [r for r in rows if not r["ok"]]
    print(json.dumps({"checks": rows, "failed": [r["check"] for r in failed]},
                     ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())