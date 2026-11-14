"""wp-9632-02 验收自检：逐条对照工作包 acceptance，机器可复跑。

检查项：
  C1 valid_json                —— classification.json / kf_result 包装均可解析
  C2 schema_pass               —— 包装体过 schemas/kf_result.v1.schema.json
  C3 source_hash_matches       —— 独立重算报告 markdown 的 sha256 与契约/产物一致
  C4 source_locator_resolvable —— 每条证据用 ke.wp_gate.locator_matches 解析（偏移量字节精确）
  C5 quote_content_hash        —— 每条的 content_hash == sha256(quote)
  C6 no_duplicate_ids          —— 全部 id 唯一
  C7 claims_evidence_or_unresolved —— 每个信号要么有证据、要么显式 absent/unresolved
  C8 no_self_verification      —— 产物不含 verified 类自证字段（verdict 由平台门计算）
  C9 section_map_sane          —— 结构切分连续、首尾覆盖全文、标题逐字可定位
  C10 report_type_in_taxonomy  —— 分类结果取自 registry 的六分型

退出码 0=全通过；1=有失败项（如实打印 FAIL 项）。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent
REPO = PKG.parents[1]
sys.path.insert(0, str(REPO))

from ke.wp_gate import locator_matches  # noqa: E402

EXPECTED_HASH = "sha256:b2c5eb5dad0b6db25574338b37aa5be1c8fdf20bbc7d3c75640e1c1727756841"
BANNED = ("\"verified\"", "\"verification_status\"", "\"verification_level\"",
          "\"is_verified\"", "\"gate_confirmed\"")


def main() -> int:
    checks: list[dict] = []

    def check(cid: str, ok: bool, detail: str) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail})

    # ---- C1
    try:
        cls = json.loads((PKG / "classification.json").read_text(encoding="utf-8"))
        wrap = json.loads((PKG / "kf_result_wp-9632-02.json").read_text(encoding="utf-8"))
        check("C1.valid_json", True, "classification.json + kf_result 包装可解析")
    except json.JSONDecodeError as exc:
        check("C1.valid_json", False, f"{exc}")
        print(json.dumps({"checks": checks}, ensure_ascii=False, indent=2))
        return 1

    # ---- C2
    import jsonschema

    schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    try:
        jsonschema.validate(wrap, schema)
        check("C2.schema_pass", True, "kf_result.v1.schema.json 通过")
    except jsonschema.ValidationError as exc:
        check("C2.schema_pass", False, f"{exc.message} at {list(exc.absolute_path)}")

    # ---- C3
    text = (PKG / "source_9632.md").read_text(encoding="utf-8")
    recomputed = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    decl = [cls["provenance"]["source_hash"], wrap["provenance"]["source_hash"]]
    check("C3.source_hash_matches", all(d == recomputed for d in decl) and recomputed == EXPECTED_HASH,
          f"recomputed={recomputed} declared={sorted(set(decl))}")
    check("C3b.chars_match",
          cls["provenance"]["chars"] == len(text) == wrap["provenance"]["chars"],
          f"chars={len(text)}")

    # ---- C4 / C5
    bad, bad_hash = [], []
    for ev in cls["evidence"]:
        ok, code, detail = locator_matches(text, ev)
        if not ok:
            bad.append(f"{ev['id']}:{code}:{detail}")
        q = ev["quote"]
        if ev["content_hash"] != "sha256:" + hashlib.sha256(q.encode("utf-8")).hexdigest():
            bad_hash.append(ev["id"])
    check("C4.source_locator_resolvable", not bad, f"unresolvable={bad[:5]} n={len(cls['evidence'])}")
    check("C5.quote_content_hash", not bad_hash, f"mismatch={bad_hash[:5]}")

    # ---- C6
    id_groups = {
        "evidence": [e["id"] for e in cls["evidence"]],
        "signals": [s["id"] for s in cls["signals"]],
        "sections": [s["id"] for s in cls["structure"]["sections"]],
        "topics": [t["id"] for t in cls["topics"]],
        "preserved_uncertainty": [c["id"] for c in cls["preserved_uncertainty"]],
        "unresolved": [u["id"] for u in cls["unresolved"]],
    }
    all_ids = [i for g in id_groups.values() for i in g]
    dupes = sorted({i for i in all_ids if all_ids.count(i) > 1})
    check("C6.no_duplicate_ids", not dupes and "" not in all_ids,
          f"n={len(all_ids)} duplicates={dupes[:5]}")

    # ---- C7
    ev_ids = {e["id"] for e in cls["evidence"]}
    missing = [
        s["id"] for s in cls["signals"]
        if not (s["evidence_id"] in ev_ids or s["status"] == "explicitly_absent")
    ]
    dangling = sorted(
        {s[k] for s in cls["signals"] for k in ("evidence_id", "context_evidence_id")
         if s[k]} - ev_ids
    )
    covers = sorted({e["id"] for e in cls["evidence"] if not e["covers"]})
    check("C7.claims_evidence_or_unresolved",
          not missing and not dangling and not covers and cls["claims_produced"] == [],
          f"unbacked={missing[:5]} dangling={dangling[:5]} unreferenced_evidence={covers[:5]} "
          f"claims_produced={len(cls['claims_produced'])}")

    # ---- C8
    blob = (PKG / "classification.json").read_text(encoding="utf-8") + \
           (PKG / "kf_result_wp-9632-02.json").read_text(encoding="utf-8")
    hits = [b for b in BANNED if b in blob]
    check("C8.no_self_verification", not hits, f"markers={hits}")

    # ---- C9
    secs = cls["structure"]["sections"]
    contiguous = all(
        secs[i]["end_offset"] == secs[i + 1]["start_offset"] for i in range(len(secs) - 1)
    ) and secs[0]["start_offset"] == 0 and secs[-1]["end_offset"] == len(text)
    heading_ok = all(
        text[s["start_offset"]:s["end_offset"]].lstrip("#").strip().startswith(s["heading"])
        for s in secs
    )
    check("C9.section_map_sane", contiguous and heading_ok,
          f"n={len(secs)} contiguous={contiguous} headings_verbatim={heading_ok}")

    # ---- C10
    reg = json.loads((REPO / "extraction-skills" / "registry.json").read_text(encoding="utf-8"))
    types = set(reg["report_types"])
    matrix_types = {r["report_type"] for r in cls["candidate_matrix"]}
    check("C10.report_type_in_taxonomy",
          cls["report_type"] in types and matrix_types == types
          and cls["selected_skill"]["skill_id"] in {s["skill_id"] for s in reg["skills"]},
          f"report_type={cls['report_type']} candidates={len(matrix_types)}/{len(types)}")

    failed = [c for c in checks if not c["ok"]]
    out = {
        "package_id": cls["package_id"],
        "report_id": cls["report_id"],
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": len(failed),
    }
    (PKG / "verify_report.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["id"] + " — " + c["detail"].splitlines()[0][:120])
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())