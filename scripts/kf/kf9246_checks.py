"""wp-9246-02 自检：逐条对照契约 acceptance，失败项如实记 FAILED（honest-FAIL）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import kf9246_spec as S
from kf9246_build import sha256_text


def run_checks(result: dict, classification: dict, md: str, out_dir: Path) -> dict:
    from jsonschema import Draft202012Validator

    checks: list[dict] = []

    def add(name, ok, **ev):
        checks.append({"check": name, "status": "passed" if ok else "FAILED", "evidence": ev})

    # A1 valid_json —— 信封与 classification 都能 json 往返
    try:
        json.loads(json.dumps(result))
        json.loads(json.dumps(classification))
        add("A1.valid_json", True, artifacts=["kf_result.json", "classification.json"],
            roundtrip="json.dumps -> json.loads OK")
    except Exception as exc:  # pragma: no cover
        add("A1.valid_json", False, error=str(exc))

    # A2 schema_pass —— 对 schemas/kf_result.v1.schema.json（draft 2020-12）
    schema = json.loads(S.RESULT_SCHEMA.read_text())
    errs = sorted(e.message for e in Draft202012Validator(schema).iter_errors(result))
    add("A2.schema_pass", not errs, schema="schemas/kf_result.v1.schema.json",
        schema_sha256=sha256_text(S.RESULT_SCHEMA.read_text()), errors=errs)

    # A3 source_hash_matches —— 契约声明 / 现算 / 信封 三方一致
    recomputed = sha256_text(md)
    declared = result["provenance"]["source_hash"]
    add("A3.source_hash_matches", recomputed == declared == S.SOURCE_HASH,
        declared=declared, recomputed=recomputed,
        chars={"contract": S.SOURCE_CHARS, "actual": len(md)})

    # A4 source_locator_resolvable —— 逐条 quote 回切原文，重算 content_hash
    bad, spans = [], 0
    for ev in classification["evidence"]:
        loc = ev["locator"]
        spans += 1
        if md[loc["start_offset"]:loc["end_offset"]] != loc["quote"]:
            bad.append([ev["id"], "span_mismatch"])
        elif sha256_text(loc["quote"]) != loc["content_hash"]:
            bad.append([ev["id"], "content_hash_mismatch"])
        elif loc["chars"] < 12:
            bad.append([ev["id"], "quote_too_short"])
        elif md.find(loc["quote"]) != loc["start_offset"]:
            bad.append([ev["id"], "not_unique_in_source"])
    sec_bad = [s["index"] for s in classification["structure"]["sections"]
               if md[s["start_offset"]:s["end_offset"]] == ""]
    add("A4.source_locator_resolvable", not bad and not sec_bad,
        char_span_locators=spans, section_locators=len(classification["structure"]["sections"]),
        mismatches=bad, empty_sections=sec_bad)

    # A5 no_duplicate_ids
    ids = ([e["id"] for e in classification["evidence"]]
           + [d["id"] for d in classification["decision_basis"]]
           + [u["id"] for u in classification["unresolved"]])
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    add("A5.no_duplicate_ids", not dupes, ids=len(ids), duplicates=dupes)

    # A6 每条判断有证据或显式 unresolved
    unresolved_ids = {u["id"] for u in classification["unresolved"]}
    ev_ids = {e["id"] for e in classification["evidence"]}
    dangling, unbound = [], []
    for d in classification["decision_basis"]:
        if not d["evidence"]:
            unbound.append(d["id"])
        dangling += [f"{d['id']}->{r}" for r in d["evidence"] if r not in ev_ids]
    for t, rows in classification["signals"]["step_fit"].items():
        for r in rows["steps"]:
            ref = r["evidence"]
            if ref and ref not in ev_ids and ref not in unresolved_ids:
                dangling.append(f"stepfit:{t}:{r['step_id']}->{ref}")
    add("A6.all_claims_have_evidence_or_explicit_unresolved_status",
        not dangling and not unbound, decision_basis=len(classification["decision_basis"]),
        unbound_statements=unbound, dangling_refs=dangling, claims_emitted=0,
        note=("工序 02 不产 claims（objective.classify_report_type=true，notes: 不做抽取）；"
              "本包每条判断都绑定逐字证据或显式 unresolved"))

    # A7 不把任何东西标成 verified
    offending = []
    blob = json.dumps(classification, ensure_ascii=False)
    for field in ("verified", "verification_status", "assessment_status", "epistemic_status"):
        for val in re.findall(rf'"{field}"\s*:\s*"([^"]*)"', blob):
            if val not in ("draft", "unassessed"):
                offending.append({field: val})
    add("A7.no_claims_marked_verified", not offending, offending=offending)

    # A8 单一 report_id 锁
    add("A8.scope_lock_single_report_id",
        classification["scope_guard"]["report_ids_read"] == [S.REPORT_ID],
        guard=classification["scope_guard"])

    # A9 报告里唯一一个 json 代码块 == 信封原样
    rpt = out_dir / f"KF-RESULT-{S.PACKAGE_ID}.md"
    if rpt.exists():
        text = rpt.read_text()
        blocks = re.findall(r"```json\n(.*?)\n```", text, flags=re.S)
        fences = text.count("```")
        ok = len(blocks) == 1 and fences == 2
        same = False
        if ok:
            try:
                same = json.loads(blocks[0]) == result
            except Exception:
                same = False
        add("A9.single_json_block_matches_envelope", ok and same,
            json_blocks=len(blocks), fence_markers=fences, parses_equal=same)
    else:
        add("A9.single_json_block_matches_envelope", False, error="report markdown missing")

    return {"ok": all(c["status"] == "passed" for c in checks), "checks": checks}