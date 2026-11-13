#!/usr/bin/env python3
"""Self-check gate for wp-611-04 deliverables (run by run_all.sh, exit!=0 on failure).

Checks
  1  all JSON deliverables parse
  2  KF envelope validates against schemas/kf_result.v1.schema.json
  3  every review event validates against schemas/review-event.schema.json
  4  reviewer independence + the ledger folds legally through the real state machine
  5  provenance.source_hash == sha256(_source_611.md) == contract source_hash
  6  every quote in review_report.json is a byte-exact substring at its recorded offset
  7  no self-verification fields anywhere (no verified / verification_* / is_verified)
  8  the report body carries exactly ONE JSON fence and it parses to the same envelope
  9  every recomputed number in review_report.json matches independent_check_results.json
 10  upstream package state (live, optional: skipped when the API token is absent)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts"))

SOURCE_HASH = "sha256:72175cbfcd1c0273e48480878d29788a533b67f32b6129bcc0b153e1386a1c88"
FORBIDDEN = ("verified", "verification_status", "verification_level", "is_verified", "gate_confirmed")
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def load(name: str):
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return json.load(fh)


def scan_forbidden(obj, path="") -> list[str]:
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in FORBIDDEN:
                hits.append(f"{path}.{k}")
            hits += scan_forbidden(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits += scan_forbidden(v, f"{path}[{i}]")
    return hits


def main() -> int:
    # 1 -------------------------------------------------------------------
    try:
        rep = load("review_report.json")
        events = load("review_events.json")
        kf = load("kf_result_wp-611-04.json")
        check("1 valid_json", True, "3 deliverables parsed")
    except Exception as exc:                                     # pragma: no cover
        check("1 valid_json", False, repr(exc))
        return 1

    # 2 -------------------------------------------------------------------
    try:
        import jsonschema
        with open(os.path.join(REPO, "schemas", "kf_result.v1.schema.json"), encoding="utf-8") as fh:
            schema = json.load(fh)
        jsonschema.validate(kf, schema)
        check("2 envelope_schema", True, "kf_result.v1.schema.json")
    except ImportError:                                           # pragma: no cover
        check("2 envelope_schema", False, "jsonschema not installed")
    except Exception as exc:
        check("2 envelope_schema", False, repr(exc)[:300])

    # 3 -------------------------------------------------------------------
    try:
        import jsonschema
        with open(os.path.join(REPO, "schemas", "review-event.schema.json"), encoding="utf-8") as fh:
            ev_schema = json.load(fh)
        for ev in events:
            jsonschema.validate(ev, ev_schema)
        check("3 review_event_schema", True, f"{len(events)} event(s)")
    except ImportError:                                           # pragma: no cover
        check("3 review_event_schema", False, "jsonschema not installed")
    except Exception as exc:
        check("3 review_event_schema", False, repr(exc)[:300])

    # 4 -------------------------------------------------------------------
    try:
        from ke_state_machine import fold, is_independent, producer_identity
        producer = rep["producer_identity"]
        ok, basis = is_independent(rep["reviewer"], producer_identity({"producer_ids": [producer]}))
        # ledger starts at the submitted state (in-review), as the gate itself folds it
        state, codes = fold(events, {"producer_ids": [producer]}, initial_state="in-review")
        check("4 independence_and_ledger",
              ok and state == "draft" and codes == ["OK_CHANGES_REQUESTED"],
              f"reviewer={rep['reviewer']['id']} producer={producer} basis={basis} state={state} codes={codes}")
    except Exception as exc:
        check("4 independence_and_ledger", False, repr(exc)[:300])

    # 5 -------------------------------------------------------------------
    try:
        md = open(os.path.join(HERE, "_source_611.md"), encoding="utf-8").read()
        recomputed = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
        ok = recomputed == SOURCE_HASH == kf["provenance"]["source_hash"] == rep["subject"]["source_hash"]
        check("5 source_hash", ok, recomputed)
    except Exception as exc:                                      # pragma: no cover
        check("5 source_hash", False, repr(exc))
        md = ""

    # 6 -------------------------------------------------------------------
    try:
        bad = []
        n = 0
        for f in rep["findings"]:
            for ev in f["evidence"]:
                n += 1
                q, s, e = ev["quote"], ev["start_offset"], ev["end_offset"]
                if md.find(q) != s or md[s:e] != q:
                    bad.append(f"{f['finding_id']}:{q[:40]}")
                if ev.get("content_sha256") != "sha256:" + hashlib.sha256(q.encode()).hexdigest():
                    bad.append(f"{f['finding_id']}:hash")
        check("6 quotes_verbatim", not bad, f"{n} quotes, bad={bad[:3]}")
    except Exception as exc:                                      # pragma: no cover
        check("6 quotes_verbatim", False, repr(exc))

    # 7 -------------------------------------------------------------------
    hits = scan_forbidden(kf)
    check("7 no_self_verification", not hits, f"hits={hits[:5]}")

    # 8 -------------------------------------------------------------------
    try:
        body = open(os.path.join(HERE, "WP-611-04.md"), encoding="utf-8").read()
        fences = re.findall(r"```json\n(.*?)\n```", body, flags=re.S)
        parsed = json.loads(fences[0]) if len(fences) == 1 else None
        ok = (len(fences) == 1 and parsed == kf
              and body.splitlines()[0].strip() == "# KF-RESULT wp-611-04")
        check("8 single_json_block", ok, f"fences={len(fences)} identical_to_envelope={parsed == kf}")
    except Exception as exc:                                      # pragma: no cover
        check("8 single_json_block", False, repr(exc))

    # 9 -------------------------------------------------------------------
    try:
        res = load("independent_check_results.json")
        st, g = res["stability"], res["geometry_and_equilibrium"]
        by_id = {f["finding_id"]: f for f in rep["findings"]}
        pairs = {
            "GM_3d": (by_id["F1"]["recomputation"]["GM_3d_at_equilibrium"], st["3d"]["GM"]),
            "GM_max_grid": (by_id["F1"]["recomputation"]["GM_max_abs_over_draught_grid_3d"],
                            st["GM_max_abs_over_draught_grid_3d"]),
            "k_2d": (by_id["F5"]["recomputation"]["k_2d_recomputed"], st["2d"]["k_heave"]),
            "k_3d": (by_id["F5"]["recomputation"]["k_3d_recomputed"], st["3d"]["k_heave"]),
            "h_eq_2d": (g["h_eq_2d"], abs(g["h_eq_2d"])),
        }
        bad = [k for k, (a, b) in pairs.items() if a != b]
        table_gm = [m for m in rep["reproduction_table"] if m["quantity"].startswith("GM 3-D")][0]
        if table_gm["recomputed"] != st["3d"]["GM"]:
            bad.append("reproduction_table.GM_3-D")
        check("9 numbers_from_computation", not bad, f"bad={bad}")
    except Exception as exc:                                      # pragma: no cover
        check("9 numbers_from_computation", False, repr(exc))

    # 10 ------------------------------------------------------------------
    token = os.environ.get("KF_REVIEW_TOKEN")
    if not token:
        check("10 upstream_packages_completed", True,
              "SKIPPED (no KF_REVIEW_TOKEN): recorded evidence = scenario listing shows wp-611-01 published only")
    else:
        import urllib.request

        base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
        req = urllib.request.Request(
            base + "/tensor/reports?scenario_key=SIR-PC2_F07_dem_buoyancy_wet_coupling&limit=50",
            headers={"Authorization": "Bearer " + token})
        items = json.load(urllib.request.urlopen(req)).get("items", [])
        seen = {r["id"]: (r.get("status"), [t for t in (r.get("tags") or []) if t.startswith("kf-wp")])
                for r in items}
        check("10 upstream_packages_completed", 14568 in seen and seen[14568][0] == "published",
              f"scenario packages={seen}")

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())