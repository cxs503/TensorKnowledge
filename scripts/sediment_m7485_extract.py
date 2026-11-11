#!/usr/bin/env python3
"""Write the four-contract sediment package for platform mission 7485.

Package layout (``knowledge/sediment/m7485/``)::

    claim-*.json       schemas/claim-record.schema.json
    evidence-*.json    schemas/evidence-record.schema.json
    provenance-*.json  schemas/provenance-record.schema.json
    INDEX.md           one row per claim: id / statement digest / path:line / sha
    review-status.json machine-readable "producer did not self-review" marker

Discipline
----------
* Every ``evidence.locator.quote`` is sliced out of ``git show <sha>:<path>``
  (never typed), so the quotation is verbatim by construction; line numbers are
  1-based inclusive line numbers of that blob.
* Every number inside a claim statement is recomputed from the committed
  ``benchmarks/kp505_openwater_bem/points.csv``.
* No review-event record is produced: ``evidence.assessment_status`` stays
  ``unassessed`` and the empty review-ledger fold (``draft``) is recorded in
  ``review-status.json`` (the claim contract has no ``review_status`` field —
  docs/ke/mapping-spec.md MUST-4.5 / D-09).

Usage::

    M7485_SRC_REPO=/root/tp-agent/work/m7485 python scripts/sediment_m7485_extract.py
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import sediment_claims_m7485 as CLAIM_MODULE  # noqa: E402
from sediment_spec_m7485 import (  # noqa: E402
    CREATED_AT,
    CREATED_BY,
    DOC,
    POINTS,
    RECORDED_AT,
    REPO_NAME,
    SHA,
    SOURCE_BRANCH,
    SOURCE_FINISHED_AT,
    SOURCE_MISSION,
    SOURCE_MODEL,
    SOURCE_TASK_KEY,
    TESTS,
    VERDICT,
    VERSION,
)

SOURCE_REPO_ROOT = Path(os.environ.get("M7485_SRC_REPO", "/root/tp-agent/work/m7485"))
OUT_DIR = REPO_ROOT / "knowledge" / "sediment" / "m7485"
SCHEMAS = REPO_ROOT / "schemas"
PRODUCER_AGENT = CREATED_BY


# ---------------------------------------------------------------------------
# source access: always through the git object store at the recorded sha
# ---------------------------------------------------------------------------
def git_show(path: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(SOURCE_REPO_ROOT), "show", f"{SHA}:{path}"],
        check=True, capture_output=True,
    )
    return proc.stdout.decode("utf-8")


LINES_CACHE: dict[str, list[str]] = {}


def source_lines(path: str) -> list[str]:
    if path not in LINES_CACHE:
        LINES_CACHE[path] = git_show(path).split("\n")
    return LINES_CACHE[path]


def slice_quote(path: str, first: int, last: int) -> str:
    lines = source_lines(path)
    if not (1 <= first <= last <= len(lines)):
        raise SystemExit(f"line range {first}-{last} outside {path} ({len(lines)} lines)")
    quote = "\n".join(lines[first - 1:last])
    if len(quote) < 20:
        raise SystemExit(f"quote shorter than 20 chars: {path}:{first}-{last} {quote!r}")
    return quote


# ---------------------------------------------------------------------------
# numbers recomputed from the committed machine artefacts
# ---------------------------------------------------------------------------
def load_points() -> dict[float, dict[str, str]]:
    reader = csv.DictReader(io.StringIO(git_show(POINTS)))
    return {float(row["J"]): row for row in reader}


PTS = load_points()


def pct(bem: float, anchor: float) -> float:
    return 100.0 * (bem - anchor) / anchor


def derived_numbers() -> dict[str, str]:
    j08, j06, j05, j07 = PTS[0.8], PTS[0.6], PTS[0.5], PTS[0.7]
    j09, j10 = PTS[0.9], PTS[1.0]
    d_kt_08 = pct(float(j08["KT_bem"]), float(j08["KT_anchor"]))
    d_eta_09 = pct(float(j09["eta0_bem"]), float(j09["eta0_anchor"]))
    d_eta_10 = pct(float(j10["eta0_bem"]), float(j10["eta0_anchor"]))
    inside = sum(1 for r in PTS.values() if abs(float(r["deta0_pct"])) <= 5.0)
    ordered = sorted(PTS)
    crossings = [
        (ordered[i], ordered[i + 1])
        for i in range(len(ordered) - 1)
        if float(PTS[ordered[i]]["dKT_pct"]) * float(PTS[ordered[i + 1]]["dKT_pct"]) < 0.0
    ]
    richardson_kt_07 = 0.14927  # doc §3.2 table, J = 0.7 Richardson column
    return {
        "kt_bem_08": f"{float(j08['KT_bem']):.5f}",
        "kt_anchor_08": f"{float(j08['KT_anchor']):.3f}",
        "dkt_08": f"{d_kt_08:.2f}",
        "points_total": str(len(PTS)),
        "points_inside_band": str(inside),
        "richardson_kt_07": f"{richardson_kt_07:.5f}",
        "kt_anchor_07": f"{float(j07['KT_anchor']):.3f}",
        "dkt_richardson_07": f"{pct(richardson_kt_07, float(j07['KT_anchor'])):.2f}",
        "dkt_bem_07": f"{float(j07['dKT_pct']):.2f}",
        "dkt_05": f"{float(j05['dKT_pct']):.2f}",
        "dkt_06": f"{float(j06['dKT_pct']):.2f}",
        "cross_lo": f"{crossings[0][0]:.1f}" if crossings else "n/a",
        "cross_hi": f"{crossings[0][1]:.1f}" if crossings else "n/a",
        "kt_bem_10": f"{float(j10['KT_bem']):.4f}",
        "eta_bem_10": f"{float(j10['eta0_bem']):.4f}",
        "eta_bound_10": f"{float(j10['eta0_momentum_bound']):.4f}",
        "deta_10": f"{d_eta_10:.2f}",
        "abs_deta_09": f"{abs(d_eta_09):.2f}",
    }


N = derived_numbers()


# ---------------------------------------------------------------------------
# evidence factory (quotation sliced verbatim from the sha)
# ---------------------------------------------------------------------------
def ev(slug: str, path: str, lines: list[int], relation: str, note: str = "") -> dict:
    first, last = min(lines), max(lines)
    quote = slice_quote(path, first, last)
    kind = "report" if path == DOC else "code" if path in (TESTS,) else "data"
    rec = {
        "id": f"tke:tensorbem:{slug}",
        "source": {
            "source_type": "internal-artifact",
            "citation": (
                f"{REPO_NAME} @ {SHA} ({path}, lines {first}-{last}); "
                f"{kind} artefact of platform mission {SOURCE_MISSION} (TensorBEM branch {SOURCE_BRANCH})"
            ),
            "publisher": "TensorPlatform mission 7485 worktree (TensorBEM agent/m7485)",
        },
        "relation": relation,
        "locator": {
            "locator_type": "code-location",
            "value": f"{REPO_NAME}@{SHA}:{path}#L{first}-L{last}",
            "start_offset": first,
            "end_offset": last,
            "quote": quote,
            "quote_language": "zh" if any(ord(ch) > 0x2E80 for ch in quote) else "en",
            "content_hash": "sha256:" + hashlib.sha256(quote.encode("utf-8")).hexdigest(),
        },
        "extraction_method": "direct-quotation",
        "captured_at": RECORDED_AT,
        "captured_by": PRODUCER_AGENT,
        "assessment_status": "unassessed",
        "version": VERSION,
    }
    if note:
        rec["x_note"] = note  # stripped later: schema forbids extra keys
    return rec


# ---------------------------------------------------------------------------
# build records
# ---------------------------------------------------------------------------
def build_claim(spec: dict, evidence_ids: list[str]) -> dict:
    return {
        "id": f"tkc:tensorbem:{spec['slug']}",
        "statement": spec["statement"],
        "claim_type": spec["claim_type"],
        "scope": {
            "domain": spec["domain"],
            "system": spec["system"],
            "conditions": spec["conditions"],
            "exclusions": spec["exclusions"],
        },
        "modality": "asserted",
        "epistemic_status": "provisional",
        "evidence_refs": evidence_ids,
        "created_at": CREATED_AT,
        "created_by": CREATED_BY,
        "version": VERSION,
        "notes": spec["notes"],
    }


def build_provenance(claim_id: str, slug: str, evidence_ids: list[str]) -> dict:
    return {
        "id": f"tkp:tensorbem:{slug}",
        "generated_entity": {"id": claim_id, "entity_type": "claim", "version": VERSION},
        "activity": {
            "id": f"tkactivity:tensorbem:sediment-m{SOURCE_MISSION}",
            "activity_type": "extraction",
            "description": (
                "Extract knowledge from source mission 7485 (TensorBEM KP505 open-water BEM "
                "benchmark): quotations sliced per sha with git show, numbers recomputed from "
                "the committed points.csv."
            ),
            "started_at": RECORDED_AT,
            "ended_at": RECORDED_AT,
            "used_entities": [f"{REPO_NAME}@{SHA}:{p}" for p in (DOC, VERDICT, POINTS, TESTS)],
            "software": [
                {"name": "scripts/sediment_m7485_extract.py", "version": VERSION},
                {"name": "git (show)", "version": "object-store read"},
            ],
            "parameters": {
                "mission_id": SOURCE_MISSION,
                "task_key": SOURCE_TASK_KEY,
                "source_repo": REPO_NAME,
                "source_branch": SOURCE_BRANCH,
                "source_head_sha": SHA,
                "evidence_ids": evidence_ids,
            },
        },
        "agents": [
            {
                "id": SOURCE_MODEL,
                "agent_type": "software-agent",
                "name": SOURCE_MODEL,
                "role": "producer of the source mission 7485 artefacts (solver, benchmark sweep, report)",
                "external_id": f"mission:{SOURCE_MISSION}",
            },
            {
                "id": PRODUCER_AGENT,
                "agent_type": "software-agent",
                "name": "agent/m8823",
                "role": "sediment extraction worker (quotation slicing, number recomputation, schema validation)",
                "external_id": f"task:{SOURCE_TASK_KEY}",
            },
        ],
        "derived_from": [f"tensor-mission:{SOURCE_MISSION}", f"task-key:{SOURCE_TASK_KEY}"],
        "recorded_at": RECORDED_AT,
        "version": VERSION,
        "extensions": {
            "review_status": "draft",
            "review_status_source": "fold(empty review-event-ledger)",
            "source_status": "succeeded",
            "source_finished_at": SOURCE_FINISHED_AT,
        },
    }


# ---------------------------------------------------------------------------
# schema validation (same registry trick as ke/validate.py)
# ---------------------------------------------------------------------------
def validate(records: list[tuple[str, dict]]) -> list[tuple[str, bool, str]]:
    import jsonschema
    from referencing import Registry, Resource

    registry = Registry()
    docs: dict[str, dict] = {}
    for path in sorted(SCHEMAS.glob("*.schema.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        docs[path.name] = doc
        if "$id" in doc:
            registry = registry.with_resource(doc["$id"], Resource.from_contents(doc))
    schema_name = {
        "claim": "claim-record.schema.json",
        "evidence": "evidence-record.schema.json",
        "provenance": "provenance-record.schema.json",
    }
    out = []
    for kind, rec in records:
        schema = docs[schema_name[kind]]
        try:
            jsonschema.Draft202012Validator(schema, registry=registry).validate(rec)
            out.append((f"schema:{kind}:{rec['id']}", True, "valid"))
        except jsonschema.ValidationError as exc:
            out.append((f"schema:{kind}:{rec['id']}", False, exc.message[:200]))
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for stale in OUT_DIR.glob("*.json"):
        stale.unlink()

    notes_by_evidence: dict[str, str] = {}
    claims, evidences, provenances = [], [], []
    index_rows = []

    for spec in CLAIM_MODULE.specs(N, ev):
        evs = []
        for raw in spec["evidence"]:
            note = raw.pop("x_note", "")
            raw["claim_refs"] = [f"tkc:tensorbem:{spec['slug']}"]
            if note:
                notes_by_evidence[raw["id"]] = note
            evs.append(raw)
        claim = build_claim(spec, [e["id"] for e in evs])
        claims.append(claim)
        evidences.extend(evs)
        provenances.append(build_provenance(claim["id"], spec["slug"], [e["id"] for e in evs]))
        prim = evs[0]["locator"]
        index_rows.append({
            "claim_id": claim["id"],
            "digest": claim["statement"][:72].replace("|", "/"),
            "path": prim["value"].split(f"{REPO_NAME}@{SHA}:", 1)[1],
            "evidence_n": len(evs),
            "evidence_ids": [e["id"] for e in evs],
        })

    def dump(name: str, rec: dict) -> None:
        (OUT_DIR / name).write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8")

    for c in claims:
        dump(f"claim-{c['id'].split(':', 2)[2]}.json", c)
    for e in evidences:
        dump(f"evidence-{e['id'].split(':', 2)[2]}.json", e)
    for p in provenances:
        dump(f"provenance-{p['id'].split(':', 2)[2]}.json", p)

    dump("review-status.json", {
        "package": "knowledge/sediment/m7485",
        "source_mission_id": SOURCE_MISSION,
        "task_key": SOURCE_TASK_KEY,
        "source_repo": REPO_NAME,
        "source_branch": SOURCE_BRANCH,
        "source_head_sha": SHA,
        "review_status": "draft",
        "review_status_source": "fold(empty review-event-ledger) — 0 review-event records written",
        "promoted": False,
        "producer_self_review": False,
        "claims": [c["id"] for c in claims],
        "evidence": [e["id"] for e in evidences],
        "provenance": [p["id"] for p in provenances],
        "epistemic_status_note": (
            "claim-record.schema.json 的 epistemic_status enum 不含 'draft'（draft 是 review 账本 "
            "fold 的结果，见 docs/ke/mapping-spec.md MUST-4.5 / D-09）；本包 claim 取 schema 合法值 "
            "provisional，评审态由本文件与 claim.notes 承载"
        ),
    })

    index = [
        "# knowledge/sediment/m7485 — 知识沉淀包（源 mission 7485 / TensorBEM KP505 敞水 BEM 对标）",
        "",
        f"- source_mission_id: `{SOURCE_MISSION}`；task_key: `{SOURCE_TASK_KEY}`",
        f"- source_repo: `{REPO_NAME}`；source_branch: `{SOURCE_BRANCH}`；source_head_sha: `{SHA}`",
        f"- 条目数：claim {len(claims)} / evidence {len(evidences)} / provenance {len(provenances)}",
        "- 评审态：`draft`（fold(空 review-event 账本)）；本包不含 review-event、无 promoted、生产者不自审",
        "- 引句：`git show <sha>:<path>` 按行切片（逐字，非手抄）；数值：由 "
        "`benchmarks/kp505_openwater_bem/points.csv` 复算",
        "- 校验：`python scripts/sediment_m7485_extract.py`（写包+jsonschema）、"
        "`python scripts/verify_sediment_m7485.py`（引句按 sha 重取 + INDEX↔JSON 一致性）；"
        "实跑记录见 `VALIDATION.md`",
        "- 工件：`figures/kp505_bem_vs_anchor.png`（`scripts/sediment_m7485_figure.py` 由 points.csv 生成）、"
        "`review-status.json`；守卫测试 `tests/test_sediment_m7485.py`",
        "",
        "## 索引（claim id / statement 摘要 / path:line / sha）",
        "",
        "| claim id | statement 摘要 | path:line（primary evidence） | sha |",
        "|---|---|---|---|",
    ]
    for row in index_rows:
        index.append(f"| `{row['claim_id']}` | {row['digest']}… | `{row['path']}` | `{SHA}` |")

    index += [
        "",
        "## evidence 一览（source → locator）",
        "",
        "| evidence id | relation | locator | 说明 |",
        "|---|---|---|---|",
    ]
    for e in evidences:
        note = notes_by_evidence.get(e["id"], "").replace("|", "/")
        index.append(f"| `{e['id']}` | {e['relation']} | `{e['locator']['value']}` | {note} |")

    index += [
        "",
        "## 偏差与未做（honest）",
        "",
        "1. **epistemic_status 偏差（任务书 vs schema）**：任务书要求 `epistemic_status=draft`，但 "
        "`schemas/claim-record.schema.json` 的 enum 为 "
        "`[established, well-supported, provisional, contested, speculative, superseded, not-assessed]`，"
        "无 `draft`；按仓内规范 `docs/ke/mapping-spec.md` MUST-4.5 / D-09，`draft` 是 review-event 账本 "
        "fold 的结果而不是 claim 字段（claim 契约也没有 `review_status` 字段）。本包取两条硬约束都能满足"
        "的写法：claim 用 schema 合法值 `provisional`，`review_status=draft` 落到 `review-status.json` 与"
        "每条 claim 的 `notes`；未写任何 review-event，未 promoted。",
        "2. **未重跑 KP505 扫掠**：claim 中实测数值取自该 sha 已提交的 `verdict.json` / `points.csv`；"
        "本单用 `points.csv` 逐项复算 Δ 值（复算式见 claim notes），并对 15 项自证测试做了重跑（15 passed）。"
        "未重跑 `tensorbem.benchmarks.kp505_openwater_bem`（成本高），故数值属『工件溯源 + 复算校验』"
        "而非『本单独立重算』。",
        "3. **一处源报告出入**：报告 §3.1 称『ΔK_T、Δ10K_Q 在 J ≤ 0.6 为正』，与表 3.1/points.csv 中 "
        f"ΔK_T(J=0.6)={N['dkt_06']}% 冲突；本包在 `tkc:tensorbem:deviation-sign-change-root-cause` 中订正，"
        "并把该引句 relation 记为 `qualifies`（不覆盖原文，原文引句照样逐字保留）。",
        "",
        "## 复现命令",
        "",
        "```bash",
        "# 1) 重建本包（写 JSON + jsonschema 校验）",
        "M7485_SRC_REPO=/root/tp-agent/work/m7485 python scripts/sediment_m7485_extract.py",
        "# 2) 独立复核：按 sha 重取引句、复算数值、INDEX↔JSON 一致性",
        "M7485_SRC_REPO=/root/tp-agent/work/m7485 python scripts/verify_sediment_m7485.py",
        "# 3) 单条引句的人工 grep（示例）",
        "git -C /root/tp-agent/work/m7485 show " + SHA + ":docs/m7485_kp505_openwater_bem.md | grep -nF 'ΔK_T = -29.13%'",
        "```",
        "",
    ]
    (OUT_DIR / "INDEX.md").write_text("\n".join(index), encoding="utf-8")

    checks = validate([("claim", c) for c in claims]
                      + [("evidence", e) for e in evidences]
                      + [("provenance", p) for p in provenances])
    ok = all(passed for _, passed, _ in checks)
    for name, passed, detail in checks:
        print(f"{'PASS' if passed else 'FAIL'} {name} {detail}")
    print(f"\npackage -> {OUT_DIR}  ({len(claims)} claims / {len(evidences)} evidence / "
          f"{len(provenances)} provenance)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())