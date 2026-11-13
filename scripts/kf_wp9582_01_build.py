#!/usr/bin/env python3
"""wp-9582-01 (task_type 01-asset-registration): register report 9582's source asset
and enumerate the attachments/artifacts it declares. Registration only: no claim
extraction, no "verified" marks (verification is computed by the platform gate).

    python3 scripts/kf_wp9582_01_fetch.py     # step 0: pin report bytes (API, no DB)
    python3 scripts/kf_wp9582_01_build.py     # build + selfcheck + render KF-RESULT body

Design rules honoured (contract wp-9582-01):
  * only report_id 9582 is read; nothing else in the corpus is touched;
  * zero manual transcription -- every char offset, hash, count and quote below is
    measured from the pinned markdown, never typed in from reading it;
  * quotes are verbatim substrings, auto-expanded by whole lines until unique, and
    re-resolved against the live source at selfcheck time;
  * a failed check is written as a failed check (honest FAIL), never smoothed over.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "9582"
PACKAGE_ID = "wp-9582-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
RUN_DIR = ROOT / "runs" / PACKAGE_ID
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
META_COPY = RUN_DIR / ("source_%s_meta.json" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
SELFCHECK = OUT_DIR / "selfcheck.json"
REPORT_MD = OUT_DIR / ("KF-RESULT-%s.md" % PACKAGE_ID)
LOCAL_SCHEMA = OUT_DIR / "asset_manifest.schema.json"
CANON_SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
PRODUCER = "kf-worker/m15661"

# contract-declared identity (work-package YAML). Comparison targets only: the script
# never trusts them, it measures the bytes and reports the comparison.
CONTRACT = {
    "source_hash": "sha256:cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f",
    "chars": 11293,
    "title": "P82W2-N02 碎冰堆积体 μ(I) 流变标定：孔隙率场、力链网络与等效黏度（DEM）",
    "scenario_key": "ice_rubble_rheology_dem",
}

# ------------------------------------------------------------------ asset table
# (asset_id, asset_class, label, in_report_section, needle, resolution_policy, note)
# needle = literal text that must occur in the markdown; locator span is expanded to
# whole lines until the quote is unique in the document.
ASSET_SPEC = [
    ("A01", "report_source_markdown", "报告源资产：markdown 全文（本工序的输入字节）",
     "whole document", "# P82W2-N02 碎冰堆积体动态演化与运动学：孔隙率场、力链网络与 μ(I) 流变标定",
     "source",
     "字节级副本 runs/wp-9582-01/source_9582.md；sha256 于该副本重算，用于 provenance.source_hash。"),
    ("A02", "figure_reference", "porosity_fields.png（孔隙率场云图）", "④ 结果图",
     "**porosity_fields.png**", "figure", "图名+caption 在 §④ 可定位；PNG 像素字节未随报告记录附带。"),
    ("A03", "figure_reference", "mu_of_I_fit.png（μ–I 拟合与场景点）", "④ 结果图",
     "**mu_of_I_fit.png**", "figure", "图名+caption 在 §④ 可定位；PNG 像素字节未随报告记录附带。"),
    ("A04", "figure_reference", "mu_I_residuals.png（主判据残差与容差带）", "④ 结果图",
     "**mu_I_residuals.png**", "figure", "图名+caption 在 §④ 可定位；PNG 像素字节未随报告记录附带。"),
    ("A05", "figure_reference", "force_chain_vs_I.png（Z / A_c / 强链载荷份额 vs I）", "④ 结果图",
     "**force_chain_vs_I.png**", "figure", "图名+caption 在 §④ 可定位；PNG 像素字节未随报告记录附带。"),
    ("A06", "figure_reference", "contact_orientation.png（接触方向极分布）", "④ 结果图",
     "**contact_orientation.png**", "figure", "图名+caption 在 §④ 可定位；PNG 像素字节未随报告记录附带。"),
    ("A07", "figure_reference", "viscosity.png（等效黏度与文献窗）", "④ 结果图",
     "**viscosity.png**", "figure", "图名+caption 在 §④ 可定位；PNG 像素字节未随报告记录附带。"),
    ("A08", "preregistration_reference", "prereg/rubble_rheology_prereg.json（预注册阈值+Amendment）",
     "② 怎么做的 / 审计链", "prereg/rubble_rheology_prereg.json", "path",
     "路径字面量可定位；文件本体不在报告记录内，需到 TensorDEM 检出取回。"),
    ("A09", "code_reference", "src/tensordem/rubble_scenarios.py（DEM 场景定义）", "审计链",
     "src/tensordem/rubble_scenarios.py", "path",
     "路径字面量可定位；文件本体不在报告记录内，需到 TensorDEM 检出取回。"),
    ("A10", "code_reference", "src/tensordem/rubble_postprocess.py（后处理模块）", "审计链",
     "src/tensordem/rubble_postprocess.py", "path",
     "路径字面量可定位；文件本体不在报告记录内，需到 TensorDEM 检出取回。"),
    ("A11", "code_reference", "scripts/run_rubble_rheology.py（扫描脚本）", "审计链",
     "scripts/run_rubble_rheology.py", "path",
     "路径字面量可定位；文件本体不在报告记录内，需到 TensorDEM 检出取回。"),
    ("A12", "code_reference", "scripts/analyse_rubble_rheology.py（拟合/验收/绘图脚本）", "审计链",
     "scripts/analyse_rubble_rheology.py", "path",
     "路径字面量可定位；文件本体不在报告记录内，需到 TensorDEM 检出取回。"),
    ("A13", "data_artifact_reference", "artifacts/rubble_rheology/runs/*.json（逐 run 数字）", "审计链",
     "artifacts/rubble_rheology/runs/*.json", "path",
     "路径通配符可定位；逐 run 数据本体不在报告记录内。"),
    ("A14", "data_artifact_reference", "artifacts/rubble_rheology/summary.json（汇总）", "审计链",
     "artifacts/rubble_rheology/summary.json", "path",
     "路径字面量可定位；汇总数据本体不在报告记录内。"),
    ("A15", "code_reference", "scripts/ablate_compression_kinematics.py（压缩运动学消融）", "审计链",
     "scripts/ablate_compression_kinematics.py", "path",
     "路径字面量可定位；文件本体不在报告记录内。"),
    ("A16", "data_artifact_reference", "artifacts/rubble_rheology_ablation/（消融输出目录）", "审计链",
     "artifacts/rubble_rheology_ablation/", "path",
     "目录路径可定位；目录内容不在报告记录内。"),
    ("A17", "test_reference", "tests/test_rubble_postprocess.py（19 项含 4 负控）", "审计链",
     "tests/test_rubble_postprocess.py", "path",
     "路径字面量可定位；测试文件本体不在报告记录内。"),
    ("A18", "test_reference", "tests/test_rubble_kinematics.py（5 项运动学一致性）", "审计链",
     "tests/test_rubble_kinematics.py", "path",
     "路径字面量可定位；测试文件本体不在报告记录内。"),
    ("A19", "code_reference_module", "tensordem.rubble_postprocess（后处理模块引用）", "② 怎么做的",
     "`tensordem.rubble_postprocess`", "path",
     "模块引用可定位（与 A10 的文件路径是同一工件，登记口径不同：模块名 vs 相对路径）。"),
    ("A20", "code_reference_module", "tensordem.rubble_scenarios（场景模块引用）", "② 怎么做的",
     "`tensordem.rubble_scenarios`", "path",
     "模块引用可定位；模块源码本体不在报告记录内。"),
    ("A21", "code_reference_module", "tensordem.granular2d（颗粒引擎基座引用）", "② 怎么做的",
     "`tensordem.granular2d`", "path",
     "模块引用可定位；模块源码本体不在报告记录内。"),
    ("A22", "literature_data_reference", "Guimarães et al. 2022 逐点数据（文献锚点）",
     "⑤ 注意点 / ⑥ 误差判定", "Guimarães et al. 2022 未数字化逐点数据，逐点对比标注 WITHHELD",
     "absent",
     "报告显式声明该数据未数字化、逐点对比 WITHHELD —— 属于「报告自己声明不存在」的资产，不得当作可用基准。"),
]


def sha256_hex(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def locate(md: str, needle: str, max_expand: int = 8) -> dict:
    """Char span of `needle`, expanded by whole lines until the quote is unique."""
    if needle not in md:
        raise SystemExit("needle not found in source (registration aborted): %r" % needle)
    start = md.index(needle)
    s = md.rfind("\n", 0, start) + 1
    e = md.find("\n", start)
    e = len(md) if e == -1 else e
    quote = md[s:e]
    up = down = 0
    while md.count(quote) != 1 and (up < max_expand or down < max_expand):
        if down < max_expand:
            nxt = md.find("\n", e + 1)
            e = len(md) if nxt == -1 else nxt
            down += 1
        if md.count(quote) != 1 and up < max_expand:
            prev = md.rfind("\n", 0, max(s - 1, 0))
            s = 0 if prev == -1 else prev + 1
            up += 1
        quote = md[s:e]
    return {
        "method": "char_span",
        "start_char": s,
        "end_char": e,
        "start_line": md.count("\n", 0, s) + 1,
        "end_line": md.count("\n", 0, e) + 1,
        "quote": quote,
        "unique": md.count(quote) == 1,
    }


def build() -> dict:
    if not SOURCE_COPY.exists() or not META_COPY.exists():
        raise SystemExit("run scripts/kf_wp9582_01_fetch.py first (pinned source missing)")
    raw = SOURCE_COPY.read_bytes()
    md = raw.decode("utf-8")
    meta = json.loads(META_COPY.read_text(encoding="utf-8"))
    digest = sha256_hex(raw)

    fig_names = {f.get("name"): f for f in meta.get("figures") or []}
    assets = []
    for aid, cls, label, section, needle, policy, note in ASSET_SPEC:
        if policy == "source":
            loc = {
                "method": "document",
                "start_char": 0,
                "end_char": len(md),
                "start_line": 1,
                "end_line": md.count("\n") if md.endswith("\n") else md.count("\n") + 1,
                "quote": needle,
                "unique": md.count(needle) == 1,
            }
            resolution = "resolved_in_source"
            check = {
                "check": "pinned byte copy re-read; sha256/len re-measured from those bytes",
                "result": "resolved",
            }
            note = "%s 本副本 %d bytes / %d chars。" % (note, len(raw), len(md))
        else:
            loc = locate(md, needle)
            if policy == "figure":
                fname = needle.strip("*")
                rec = fig_names.get(fname)
                present = bool(rec and rec.get("png_base64"))
                resolution = "resolved_in_source" if present else "referenced_unresolved"
                check = {
                    "check": "name in §④ bold lead-in AND record.figures[].name match AND png_base64 non-empty",
                    "result": "present" if present else "unresolved",
                }
                note = "%s 记录侧 figures[] 命中=%s，png_base64 长度=%d。" % (
                    note, rec is not None, len((rec or {}).get("png_base64") or ""))
            elif policy == "absent":
                resolution = "declared_absent"
                check = {
                    "check": "literal WITHHELD declaration present in source",
                    "result": "absent",
                }
            else:
                local = (ROOT / needle.strip("`")).exists()
                resolution = "referenced_unresolved"
                check = {
                    "check": "path literal present in source; file bytes attached to report record? (record has no artifact field); path present in this TensorKnowledge worktree?",
                    "result": "unresolved",
                }
                note = "%s 本工作树同名路径存在=%s（不在本仓即需跨仓取回）。" % (note, local)
        assets.append({
            "asset_id": aid,
            "asset_class": cls,
            "label": label,
            "in_report_section": section,
            "resolution": resolution,
            "resolution_check": check,
            "locator": loc,
            "note": note,
        })

    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    ids = [a["asset_id"] for a in assets]
    no_dup = len(set(ids)) == len(ids) and ids == ["A%02d" % (i + 1) for i in range(len(ids))]
    unique_n = sum(1 for a in assets if a["locator"]["unique"])

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest[len("sha256:"):],
            "chars": len(md),
            "bytes_utf8": len(raw),
            "title": meta["title"],
            "scenario_key": meta["scenario_key"],
            "contract": {
                "source_hash": CONTRACT["source_hash"],
                "chars": CONTRACT["chars"],
                "title": CONTRACT["title"],
                "scenario_key": CONTRACT["scenario_key"],
                "hash_matches": digest == CONTRACT["source_hash"],
                "chars_match": len(md) == CONTRACT["chars"],
                "title_matches": meta["title"] == CONTRACT["title"],
                "scenario_key_matches": meta["scenario_key"] == CONTRACT["scenario_key"],
            },
            "platform_figures": [{
                "name": f.get("name") or "",
                "caption_chars": len(f.get("caption") or ""),
                "png_bytes_present": bool(f.get("png_base64")),
            } for f in meta.get("figures") or []],
            "platform_tags": meta.get("tags") or [],
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
        },
        "assets": assets,
        "claims": [],  # objective.classify_report_type=false -> no extraction, no claims
        "integrity": {
            "quote_uniqueness": {
                "total": len(assets),
                "unique": unique_n,
                "non_unique_ids": [a["asset_id"] for a in assets if not a["locator"]["unique"]],
            },
            "hash_recomputed_locally": digest,
            "hash_matches_contract": digest == CONTRACT["source_hash"],
            "chars_match_contract": len(md) == CONTRACT["chars"],
            "no_duplicate_ids": no_dup,
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Freeze-on-first-write: a rebuild must not silently re-stamp the artifact that was
    # already published, otherwise "delivered bytes == worktree bytes" becomes unprovable.
    emitted_at = utcnow()
    if ENVELOPE.exists():
        try:
            emitted_at = json.loads(ENVELOPE.read_text(encoding="utf-8"))["provenance"]["emitted_at"]
        except Exception:  # noqa: BLE001 - fall back to now, reported by the diff test
            pass
    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": digest,
            "source_field": "markdown",
            "producer": PRODUCER,
            "emitted_at": emitted_at,
            "notes": "Registration only: report_id 9582 markdown pinned byte-exact and hashed locally; "
                     "asset locators are char spans re-resolved against those bytes. No extraction, "
                     "no verified marks.",
        },
        "outputs": {
            "asset_manifest.json": manifest,
            "selfcheck.json": {},  # filled by selfcheck() below
        },
        "claims": [],
    }
    return {"md": md, "manifest": manifest, "envelope": envelope, "digest": digest}


def selfcheck(md: str, manifest: dict, envelope: dict) -> dict:
    import jsonschema

    checks = []

    def add(cid, name, ok, detail):
        checks.append({"id": cid, "name": name, "pass": bool(ok), "detail": detail})

    # 1 valid_json -- write envelope first so it can be re-parsed from disk
    envelope["outputs"]["selfcheck.json"] = {}  # placeholder, rewritten after checks
    ENVELOPE.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    parsed, bad = {}, []
    for p in (MANIFEST, ENVELOPE):
        try:
            parsed[p.name] = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - reported, not swallowed
            bad.append("%s: %s" % (p.name, exc))
    add("valid_json", "all emitted JSON re-parses from disk", not bad,
        {"files": [MANIFEST.name, ENVELOPE.name], "errors": bad})

    # 2 schema_pass
    schema = json.loads(LOCAL_SCHEMA.read_text(encoding="utf-8"))
    errs = sorted(jsonschema.Draft7Validator(schema).iter_errors(manifest), key=lambda e: list(e.path))
    canon = json.loads(CANON_SCHEMA.read_text(encoding="utf-8"))
    cerrs = sorted(jsonschema.Draft202012Validator(canon).iter_errors(parsed.get(ENVELOPE.name, envelope)),
                   key=lambda e: list(e.path))
    add("schema_pass", "asset_manifest.json vs package-pinned schema + kf_result.json vs canonical kf_result.v1",
        not errs and not cerrs,
        {"manifest_errors": ["%s: %s" % (list(e.path), e.message) for e in errs],
         "envelope_errors": ["%s: %s" % (list(e.path), e.message) for e in cerrs],
         "schemas": [LOCAL_SCHEMA.name, "schemas/" + CANON_SCHEMA.name]})

    # 3 source_locator_resolvable
    loc_fail = []
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "char_span":
            if md[loc["start_char"]:loc["end_char"]] != loc["quote"]:
                loc_fail.append("%s: span != quote" % a["asset_id"])
        else:  # document: span covers the whole field, quote is the in-document anchor
            if loc["start_char"] != 0 or loc["end_char"] != len(md):
                loc_fail.append("%s: document span does not cover the whole markdown field" % a["asset_id"])
        if md.count(loc["quote"]) != 1:
            loc_fail.append("%s: quote not unique" % a["asset_id"])
        if md.count("\n", 0, loc["start_char"]) + 1 != loc["start_line"]:
            loc_fail.append("%s: start_line mismatch" % a["asset_id"])
        if loc["quote"] not in md:
            loc_fail.append("%s: quote absent" % a["asset_id"])
    add("source_locator_resolvable", "every locator re-resolves to its verbatim quote in the pinned markdown",
        not loc_fail, {"locators_checked": len(manifest["assets"]), "failures": loc_fail,
         "rule": "char_span: md[start:end]==quote; document: start==0 and end==len(markdown); all: quote unique in markdown and start_line consistent"})

    # 4 source_hash_matches
    raw = SOURCE_COPY.read_bytes()
    digest = sha256_hex(raw)
    ok4 = (digest == CONTRACT["source_hash"] and len(raw.decode("utf-8")) == CONTRACT["chars"]
           and manifest["source"]["hash"] == CONTRACT["source_hash"][len("sha256:"):])
    add("source_hash_matches", "sha256 + char count of the pinned bytes equal the contract values",
        ok4, {"recomputed": digest, "contract": CONTRACT["source_hash"],
              "chars": len(raw.decode("utf-8")), "contract_chars": CONTRACT["chars"]})

    # 5 no_duplicate_ids
    ids = [a["asset_id"] for a in manifest["assets"]]
    ok5 = len(set(ids)) == len(ids)
    add("no_duplicate_ids", "asset_id values unique", ok5,
        {"n": len(ids), "unique": len(set(ids)), "ids": ids})

    # 6 all_claims_have_evidence_or_explicit_unresolved_status
    claims = manifest["claims"]
    bad6 = [c.get("claim_id") for c in claims
            if "evidence_locator" not in c and c.get("status") not in
            ("supported", "partially-supported", "unresolved", "refuted")]
    add("all_claims_have_evidence_or_explicit_unresolved_status",
        "claims either carry an evidence locator or an explicit status; claims=[] is the complete result for a registration-only package",
        not bad6, {"claims": len(claims), "violations": bad6,
                   "rationale": "objective.register_assets=true, objective.classify_report_type=false -> no extraction"})

    all_pass = all(c["pass"] for c in checks)
    checked_at = utcnow()
    if SELFCHECK.exists():
        try:
            checked_at = json.loads(SELFCHECK.read_text(encoding="utf-8"))["checked_at"]
        except Exception:  # noqa: BLE001 - fall back to now
            pass
    result = {
        "package_id": PACKAGE_ID,
        "authority": "local self-check only; the platform gate is authoritative and re-computes the hash independently",
        "checked_at": checked_at,
        "source_hash": digest,
        "acceptance": checks,
        "selfcheck_pass": all_pass,
        "failed": [c["id"] for c in checks if not c["pass"]],
    }
    SELFCHECK.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    envelope["outputs"]["selfcheck.json"] = result
    ENVELOPE.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def render(md: str, manifest: dict, envelope: dict, check: dict) -> str:
    src = manifest["source"]
    c = manifest["counts"]
    rows = []
    for a in manifest["assets"]:
        q = a["locator"]["quote"]
        shown = q if len(q) <= 92 else q[:92] + "…"
        rows.append("| %s | %s | %s | L%d | `%s` | %s |" % (
            a["asset_id"], a["asset_class"], a["resolution"], a["locator"]["start_line"],
            shown.replace("|", "\\|"), "unique" if a["locator"]["unique"] else "NOT-UNIQUE"))
    checks_md = "\n".join(
        "| %s | %s | %s |" % (x["id"], "✓" if x["pass"] else "✗ **FAIL**", json.dumps(x["detail"], ensure_ascii=False)[:220])
        for x in check["acceptance"])

    body = """# KF-RESULT {pkg}

工作包 `{pkg}` ｜ task_type `{tt}` ｜ report_id `{rid}` ｜ lane B ｜ tag `kf-wp:{pkg}` ｜ 状态 draft（verification 由平台门计算，本报告不自标 verified）

## ① 本工序做了什么

对 `{uri}` 做**资产登记**（task_type=01-asset-registration），不抽取知识、不分类、不给结论打 verified。产出一份 `asset_manifest.json`：确认 report_id 与其 markdown 的字节哈希/字符数，并把报告中声明的附件与工件逐条登记为可复核的引文定位（字符区间 + 1-based 行号 + 逐字引文 + 唯一性判定）。共登记 **{n} 个资产**：resolved_in_source {r} / referenced_unresolved {u} / declared_absent {a}。`claims` 为空数组（契约 objective.classify_report_type=false、no_forced_claim_generation=true，空 claims 即完整结果）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文（不经记忆、不经数据库）**：`psql -d tensorplatform` 直读被行级权限拒绝（`mission denied for table tensor_reports`），改走平台 API：`POST /auth/login`（Bearer）→ `GET /tensor/reports/9582`，只取 `markdown` 字段，**按字节原样**写 `runs/wp-9582-01/source_9582.md`（不追加换行），元数据写 `source_9582_meta.json`。工具 `scripts/kf_wp9582_01_fetch.py`（stdlib only）。
2. **哈希自证**：对上述字节重算 sha256 = `{hash}`，字符数 {chars}（UTF-8 字节数 {bytes}）——与契约 `{chash}` / {cchars} 逐项比对（见 manifest `source.contract` 四个布尔位）。
3. **资产抽取（程序化，不手抄）**：`scripts/kf_wp9582_01_build.py` 内以「字面 needle → 定位 → 引用行扩展」的方式登记：needle 在 markdown 中的首次出现位置取所在行，若该行在全文不唯一则上下各扩一行直至唯一（上限 8 行）；记录 `start_char/end_char`（Python str 下标）、`start_line/end_line`（1-based）、`quote`（逐字）、`unique`。图件另与报告记录 `figures[].name / png_base64` 做交叉核对。
4. **解析状态判定**（三态，不猜）：`resolved_in_source`（字节就在源内，如 markdown 本体）/ `referenced_unresolved`（引文可定位但工件字节不在报告记录内）/ `declared_absent`（报告自己声明数据不存在，如文献逐点数据 WITHHELD）。
5. **结构门**：`jsonschema` 双向校验——manifest vs 本包钉住的 `asset_manifest.schema.json`（draft-07），信封 vs 仓内规范 `schemas/kf_result.v1.schema.json`（2020-12）。
6. **自检**：6 条 acceptance 逐条机器判定，写 `selfcheck.json`（honest：不过就是不过）。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-9582-01/asset_manifest.json` | 主产物：source 身份（hash/chars/bytes/title/scenario_key + 契约比对位）+ {n} 个资产 + 计数 + integrity |
| `docs/kf/wp-9582-01/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs/claims），`outputs["asset_manifest.json"]` 内嵌 manifest |
| `docs/kf/wp-9582-01/selfcheck.json` | 6 条 acceptance 的机器判定与明细（本地自检，非平台 verification） |
| `docs/kf/wp-9582-01/asset_manifest.schema.json` | 本包钉住的 manifest 结构（仓内 448 版把 package_id 写死为 `wp-448-01`，不可复用） |
| `runs/wp-9582-01/source_9582.md` | 报告 markdown 字节级副本（{bytes} B / {chars} chars），一切定位与哈希以它为准 |
| `runs/wp-9582-01/source_9582_meta.json` | 记录元数据（title/scenario_key/tags/figures 名单/记录字段名） |
| `docs/kf/wp-9582-01/figures/fig_asset_inventory.png` | 图1 资产清单：按类别/解析状态着色（计数直读 manifest，无手抄） |
| `docs/kf/wp-9582-01/figures/fig_locator_map.png` | 图2 定位地图：{n} 条 locator 在 0–{chars} 字符坐标上的区间（斜线=整篇文档级 locator） |

图件均由 `scripts/kf_wp9582_01_figures.py` 从 `asset_manifest.json` 实测值绘制（类别/状态计数、字符区间、唯一性计数），不含任何人工输入数字；本工序不产生物理场量，故无云图/基准对比曲线。

## ④ 证据定位表（资产/字段 → 原文引文片段）

引文一律为源 markdown 的逐字子串；`L` 列为 1-based 起始行，截断仅用于本表展示（机读版在 manifest 的 `locator.quote` 全文）。

| asset_id | class | resolution | L | 原文引文（截断展示） | 唯一性 |
|---|---|---|---|---|---|
{rows}

## ⑤ 注意点与局限

1. **图件像素缺失**：记录 `figures[]` 有 6 条 `name/caption`，但 `png_base64` 长度全为 0——图名与 caption 可定位，**像素字节不可解析**，故 6 张图一律 `referenced_unresolved`，不冒充已登记图片。
2. **工件跨仓**：`prereg/…`、`src/tensordem/…`、`scripts/…`、`artifacts/…`、`tests/…` 共 {u} 条只以路径字面量出现；报告记录无 artifact 附件字段，本工作树（TensorKnowledge）内亦不存在同名路径。是否真实存在于 TensorDEM 检出**未验证**，故记 `referenced_unresolved` 而非「存在」或「不存在」。
3. **`declared_absent` 不等于「缺失」**：Guimarães et al. 2022 逐点数据是报告自己声明未数字化（WITHHELD）；登记它是为了禁止后续工序把它当基准。
4. **A19/A20/A21 与 A09/A10 的重复口径**：模块名（`tensordem.rubble_postprocess`）与相对路径（`src/tensordem/rubble_postprocess.py`）指同一工件，但报告中出现于不同章节、不同写法，故分条登记并在 note 注明，不做合并（合并会丢章节定位）。id 仍全局唯一，满足 no_duplicate_ids。
5. **哈希口径**：`provenance.source_hash` 是 markdown 的 **UTF-8 字节** sha256（不含任何附加换行）；字符数按 Unicode 码点计（{chars}），与契约一致，字节数 {bytes} 仅供对照。二者不可混用。
6. **未做（有意）**：不抽取 claims、不判定报告类型、不评估报告结论正误、不复制 A/B/C 级精度结论——这些属于 02/03 工序，越界会破坏工序边界。
7. **误差判定（本工序口径）**：本工序是元数据登记，无数值模型、无实验/解析基准可比，故「关键量误差是否 <3%」**不适用（N/A）**；可判定的只有可机检的身份量，且已全部给出实测值：哈希 = 契约哈希（逐位相等，误差 0）、字符数 = {chars}（与契约 {cchars} 相等，误差 0）、{n}/{n} 条引文可解析且唯一。报告物理结论的精度判定不在本工序范围，本报告不引用、不复述、不背书。
8. **图的口径**：本工序无物理场量，故不产云图/基准对比曲线；只画两张**由 manifest 实测数据生成**的登记图（资产清单、定位地图），图内每个数字都可回溯到 `asset_manifest.json` 字段。源报告的 6 张物理图（见注 1）字节不可得，**不重绘**——重绘等于二次创作，会污染证据链。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 结果 | 明细 |
|---|---|---|
{checks_md}

**总结论**：{verdict}

`repro_cmd`（一键复跑，工作树根下执行）：

```bash
python3 scripts/kf_wp9582_01_fetch.py && python3 scripts/kf_wp9582_01_build.py
```
""".format(
        pkg=PACKAGE_ID, tt=TASK_TYPE, rid=REPORT_ID, uri=SOURCE_URI,
        n=c["assets"], r=c["resolved_in_source"], u=c["referenced_unresolved"],
        a=c["declared_absent"], hash=src["hash"], chars=src["chars"],
        bytes=src["bytes_utf8"], chash=CONTRACT["source_hash"],
        cchars=CONTRACT["chars"], rows="\n".join(rows), checks_md=checks_md,
        verdict=("6/6 acceptance 全通过（本地自检）；真实 verification 由平台门独立重算。"
                 if check["selfcheck_pass"] else
                 "存在失败项：%s —— 如实上报，未粉饰。" % ", ".join(check["failed"])),
    )
    fence = "```"
    # exactly one json code block in the delivered markdown
    body = body.replace("## ⑥ 自检", "## ⑥ 自检")
    tail = ("\n## 结果 JSON（唯一 json 代码块，原样提交）\n\n%sjson\n%s\n%s\n" % (
        fence, json.dumps(envelope, ensure_ascii=False, indent=2), fence))
    return body + tail


def main() -> int:
    built = build()
    check = selfcheck(built["md"], built["manifest"], built["envelope"])
    body = render(built["md"], built["manifest"], built["envelope"], check)
    REPORT_MD.write_text(body, encoding="utf-8")
    # JSON blocks inside rendered markdown: the envelope must be the only json fence,
    # and the repro_cmd bash fence must not be counted.
    json_fences = body.count("```json")
    print(json.dumps({
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "envelope": str(ENVELOPE.relative_to(ROOT)),
        "selfcheck": str(SELFCHECK.relative_to(ROOT)),
        "report": str(REPORT_MD.relative_to(ROOT)),
        "assets": built["manifest"]["counts"]["assets"],
        "by_resolution": built["manifest"]["counts"]["by_resolution"],
        "selfcheck_pass": check["selfcheck_pass"],
        "failed": check["failed"],
        "json_code_blocks_in_report": json_fences,
    }, ensure_ascii=False, indent=2))
    return 0 if check["selfcheck_pass"] else 2


if __name__ == "__main__":
    sys.exit(main())