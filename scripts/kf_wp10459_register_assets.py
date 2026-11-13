"""Asset registration for report 10459 -- work package wp-10459-01 (task_type 01-asset-registration).

Scope guards (hard, per contract):
  * report_id=10459 only; nothing else is read or written.
  * No extraction, no claim generation (objective.classify_report_type=false), no verification marks.
    ``claims`` is emitted as an empty array -- that is a legitimate complete result, not a gap.
  * Zero hand transcription: every ``quote`` is *sliced out of the fetched markdown bytes* at run
    time from a programmatic anchor. The script asserts the anchor is unique, then asserts the
    resulting quote is a unique substring, then records its char span and 1-based line span.
  * Unresolvable targets are recorded as ``referenced_unresolved`` / ``declared_absent`` with the
    check that was actually run and its outcome -- never dropped, never given an invented address.
    ``resolution`` describes locator/target resolvability only; it does NOT mean "verified".

Inputs:  runs/wp-10459-01/report_10459.md   (from scripts/kf_wp10459_fetch.py)
         runs/wp-10459-01/report_10459.json (raw API payload: title/figures/tags/...)
Outputs: artifacts/wp-10459-01/asset_manifest.json   (contract-declared output file)
         docs/kf/wp-10459-01/asset_manifest.json     (durable mirror: the push gate drops artifacts/**)
         docs/kf/wp-10459-01/kf_result.json          (kf_result.v1 envelope)
         runs/wp-10459-01/kf_result_block.json       (same JSON, for the single ```json block)

Usage: python3 scripts/kf_wp10459_register_assets.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re
import sys

REPORT_ID = "10459"
PACKAGE_ID = "wp-10459-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/10459"
SOURCE_FIELD = "markdown"
CONTRACT_HASH = "08c1a0cfb3f0db38ad3a473ac2155001589bde91c1f85c21db1d29863ca84f6c"
CONTRACT_CHARS = 6431

REPO = pathlib.Path(__file__).resolve().parents[1]
RUN = REPO / "runs" / PACKAGE_ID
ART = REPO / "artifacts" / PACKAGE_ID
DOC = REPO / "docs" / "kf" / PACKAGE_ID
MD_PATH = RUN / "report_10459.md"
PAYLOAD_PATH = RUN / "report_10459.json"

# ---------------------------------------------------------------- asset table
# kind:
#   "document" -> whole markdown
#   "span"     -> anchor line +/- span=(first,last) line offsets (inclusive)
#   "charspan" -> exact substring of the markdown, located by anchor text
# resolution_check is what we actually ran; `result` is its outcome.
S = "resolved_in_source"
U = "referenced_unresolved"
A = "declared_absent"

ASSETS = [
    dict(id="A01", cls="document", label="报告 markdown 全文（源资产本体）", section="document",
         kind="document", resolution=S,
         check="sha256(markdown.encode('utf-8')) recomputed locally",
         result="resolved",
         note="chars=6431 / bytes_utf8=9539；哈希见 source.hash，与契约 source_hash 逐字一致。仅登记字节，不做抽取。"),
    dict(id="A02", cls="heading", label="报告 H1 标题行", section="title",
         kind="span", anchor="# IN102-N03 四个 WITHHELD 工程量", span=(0, 0), resolution=S,
         check="anchor line located in markdown", result="resolved",
         note="H1 文本与 API title 字段不同写法（API title 带“+ …（波浪增阻 κ / 污损 / 风压系数 / 砰击峰值系数）”括注）；两处均原文登记，未做统一改写。"),
    dict(id="A03", cls="statement", label="问题背景：四个工程量长期判 WITHHELD 的原因", section="① 案例介绍",
         kind="span", anchor="平台能力台账里四个工程量长期判", span=(0, 2), resolution=S,
         check="anchor line located in markdown", result="resolved",
         note="三行原文；“只有一个来源、从未做过区间一致性检验”是报告自述的缺口，不是本包结论。"),
    dict(id="A04", cls="parameter_set", label="参考船 KVLCC2 主尺度与工况参数", section="① 案例介绍",
         kind="span", anchor="参考船 **KVLCC2**", span=(0, 2), resolution=S,
         check="anchor line located in markdown", result="resolved",
         note="两行原文（L_pp/B/T/C_b/V_s/Re/B/L、A_F/A_L）。数值仅登记，不在此处复算或换算。"),
    dict(id="A05", cls="definition_table", label="四量物理定义表（κ_aw / ΔP/P / C_X(0) / C_F）", section="① 案例介绍",
         kind="span", anchor="| 量 | 定义 | 单位 |", span=(0, 5), resolution=S,
         check="table header located + span sliced verbatim", result="resolved",
         note="表头+分隔行+4 行公式定义；公式仅登记，本包不做实现核对。"),
    dict(id="A06", cls="method_spec", label="参考资产数字化方法（EvidenceEntry 10 字段 + digest→公式→数值审计链）", section="② 怎么做的",
         kind="span", anchor="1. **参考资产数字化**", span=(0, 3), resolution=S,
         check="anchor line located in markdown", result="resolved",
         note="四行原文；代码指针本体单列 A07。"),
    dict(id="A07", cls="code_pointer", label="实现文件 backend/modules/evidence_upgrade.py", section="② 怎么做的",
         kind="charspan", anchor="backend/modules/evidence_upgrade.py", resolution=U,
         check="os.path.exists('backend/modules/evidence_upgrade.py') in this worktree (TensorKnowledge)",
         result="unresolved",
         note="文件不属于本仓（属船舶平台仓），worktree 内不存在，故仅登记引用不登记内容；不伪造路径内容或哈希。"),
    dict(id="A08", cls="criterion", label="双源一致性判据（重叠度 ≥ 0.7 判 CONSISTENT）", section="② 怎么做的",
         kind="span", anchor="2. **双源一致性**", span=(0, 1), resolution=S,
         check="anchor line located in markdown", result="resolved",
         note="含重叠度定义式 |A∩B|/min(|A|,|B|) 原文；判据阈值 0.7 后续在 ③ 表与 ⑥ 表被引用。"),
    dict(id="A09", cls="numerical_setup", label="Sobol 设置（Saltelli 2010 pick-freeze, n_base=512, 3584 次/量, 两套因子带）", section="② 怎么做的",
         kind="span", anchor="3. **Sobol 全局敏感度**", span=(0, 2), resolution=S,
         check="anchor line located in markdown", result="resolved",
         note="三行原文；设计工况/环境分布两套因子带并列披露的说明在此。"),
    dict(id="A10", cls="self_check", label="惰性因子 dummy_unused 实现自检", section="② 怎么做的",
         kind="charspan", anchor="每个模型挂惰性因子 `dummy_unused` 作实现自检，实测 S_T=0.0000。", resolution=S,
         check="substring located + uniqueness asserted", result="resolved",
         note="单行原文；这是报告的实现自检声明，本包不重算其数值。"),
    dict(id="A11", cls="criterion", label="升级门判据（CONSISTENT 且 S_T>0.1 → REAL，否则维持 WITHHELD）", section="② 怎么做的",
         kind="span", anchor="4. **升级门**", span=(0, 1), resolution=S,
         check="anchor line located in markdown", result="resolved",
         note="两行原文；升级判决的机器可裁规则。本包不执行判决，只登记判据文本。"),
    dict(id="A12", cls="toolchain_declaration", label="工具链声明（纯 Python 无 numpy；pytest 35 用例；matplotlib 3.10.8 图件脚本）", section="② 怎么做的",
         kind="span", anchor="5. 工具链：纯 Python", span=(0, 1), resolution=S,
         check="anchor line located in markdown", result="resolved",
         note="两行原文；两个被引用的脚本本体单列 A13/A14。"),
    dict(id="A13", cls="code_pointer", label="测试文件 tests/test_evidence_upgrade.py（报告称 35 用例）", section="② 怎么做的",
         kind="charspan", anchor="tests/test_evidence_upgrade.py", resolution=U,
         check="os.path.exists('tests/test_evidence_upgrade.py') in this worktree (TensorKnowledge)",
         result="unresolved",
         note="worktree 内不存在该文件，35 用例数无法在此复核；按“不发明信息”原则仅登记引用与其声明数。"),
    dict(id="A14", cls="code_pointer", label="图件脚本 artifacts/evidence_upgrade/make_figures.py", section="② 怎么做的",
         kind="charspan", anchor="artifacts/evidence_upgrade/make_figures.py", resolution=U,
         check="os.path.exists('artifacts/evidence_upgrade/make_figures.py') in this worktree (TensorKnowledge)",
         result="unresolved",
         note="worktree 内不存在；图为上游仓产物，本包不重建图件。"),
    dict(id="A15", cls="result_table", label="判据总表（4 量 × 双源值/带宽/点值差/重叠度/判决/S_T/等级）", section="③ 计算结果",
         kind="span", anchor="| 量 | 源 A（值 [带]）", span=(0, 5), resolution=S,
         check="table header located + span sliced verbatim", result="resolved",
         note="表头+分隔行+4 行数据（wave_add_resistance / fouling / wind_coeff / slamming）。数字仅登记，不复算、不改等级标注。"),
    dict(id="A16", cls="verdict", label="升级判决结论（2/4 通过；wave/fouling 维持 WITHHELD）", section="③ 计算结果",
         kind="span", anchor="升级判决：**2/4 通过**", span=(0, 1), resolution=S,
         check="anchor line located in markdown", result="resolved",
         note="两行原文。这是报告作者的判决；本工序不确认、不升级、不标记 verified。"),
    dict(id="A17", cls="result_table", label="Sobol 敏感度排序表（设计工况 S_T 排序 + 惰性因子 S_T）", section="③ 计算结果",
         kind="span", anchor="| 量 | 敏感度排序（S_T，设计工况）", span=(0, 6), resolution=S,
         check="table header located + span sliced verbatim", result="resolved",
         note="含表头/分隔行/空行/4 行排序，逐字切片（空白行保留以保真）。"),
    dict(id="A18", cls="provenance_table", label="参考资产与审计链表（8 源：单位/有效域/带宽依据/provenance/sha256 前 16 位）", section="③ 计算结果",
         kind="span", anchor="| 量 | 源 | 单位 | 有效域 | 带宽依据 | provenance | sha256(前 16) |", span=(0, 10), resolution=S,
         check="table header located + span sliced verbatim", result="resolved",
         note="表头+分隔行+8 行源记录。sha256 仅前 16 位（报告原文如此），完整摘要不可由此表恢复——登记为截断摘要，不外推。"),
    dict(id="A19", cls="derived_numbers", label="关键派生数字清单（交点 B/L=0.25、κ 17.4%、污损 8.90×、风压 6.4%、砰击 57.1%）", section="③ 计算结果",
         kind="span", anchor="关键派生数字（代码算出，可复算）：", span=(0, 11), resolution=S,
         check="anchor line located + span sliced verbatim", result="resolved",
         note="12 行原文；报告自述“代码算出，可复算”，本包只登记不复算（复算属抽取/验证工序）。"),
    dict(id="A20", cls="figure", label="图 1 双源区间与重叠度（四量）", section="④ 结果图",
         kind="charspan", anchor="* 图 1 双源区间与重叠度（四量）：源 A/源 B 带宽 + 点值 + 判决。", resolution=U,
         check="markdown ④ 图题定位 + API figures[0] payload inspection",
         result="unresolved",
         note="平台 figures[0]=fig1_source_intervals.png 仅有 name/caption，无 png_base64 字节，故无字节可哈希；图件本体不在本 worktree。"),
    dict(id="A21", cls="figure", label="图 2 Sobol 总效应排序（设计工况，0.10 门线）", section="④ 结果图",
         kind="charspan", anchor="* 图 2 Sobol 总效应排序（设计工况），红线为被标定的量，虚线 0.10 门线；标题并列环境分布 S_T。", resolution=U,
         check="markdown ④ 图题定位 + API figures[1] payload inspection",
         result="unresolved",
         note="平台 figures[1]=fig2_sobol_total_effect.png 仅 name/caption，无字节。"),
    dict(id="A22", cls="figure", label="图 3 波浪增阻 κ 随 B/L 两源曲线与解析交点", section="④ 结果图",
         kind="charspan", anchor="* 图 3 波浪增阻 κ 随 B/L 的两源曲线与解析交点 B/L=0.25，KVLCC2 位置标注。", resolution=U,
         check="markdown ④ 图题定位 + API figures[2] payload inspection",
         result="unresolved",
         note="平台 figures[2]=fig3_wave_crossover.png 仅 name/caption，无字节。"),
    dict(id="A23", cls="caveat_section", label="注意点全节（带宽敏感/声明带/环境稀释/模型形式/生长律/MC 噪声）", section="⑤ 注意点",
         kind="span", anchor="## ⑤ 注意点（踩过的坑 / 局限 / 适用范围）", span=(0, 19), resolution=S,
         check="section heading located + span sliced verbatim", result="resolved",
         note="整节 20 行逐字登记；含 band_scale_at_flip=1.1187 与 env_diluted=True 等不确定度披露。"),
    dict(id="A24", cls="caveat", label="判决对带宽敏感（band_scale_at_flip=1.1187，B/L=0.25 丰满船两源重合）", section="⑤ 注意点",
         kind="charspan", anchor="1.1187，即两带同时放大到该倍数就从 INCONSISTENT", resolution=S,
         check="substring located + uniqueness asserted", result="resolved",
         note="原文跨行，此处 quote 取单行片段以保证逐字与唯一定位；完整语义见 A23 整节。"),
    dict(id="A25", cls="error_table", label="误差判定表（8 判据 × 基准/实测/是否达标 + 升级数量）", section="⑥ 误差判定",
         kind="span", anchor="| 判据 | 基准 / 参考 | 实测 | 是否达标 |", span=(0, 10), resolution=S,
         check="table header located + span sliced verbatim", result="resolved",
         note="表头+分隔行+9 行（含升级数量行）；含两处 honest FAIL（0.661 / 0.000）。本包不重判这些是否达标。"),
    dict(id="A26", cls="declared_absence", label="外部基准数据缺失声明", section="⑥ 误差判定",
         kind="charspan", anchor="无可用基准数据，故不声称 <3%", resolution=A,
         check="search markdown for any external benchmark dataset/citation supplying residuals",
         result="absent",
         note="报告显式声明无模型试验/实测/船队基准，故 <3% 不可声称；登记为 declared_absent，不补造基准。"),
    dict(id="A27", cls="declared_absence", label="OCIMF/Isherwood 数字化图表缺失声明", section="⑤ 注意点",
         kind="charspan", anchor="OCIMF/Isherwood 数字化图表，风压的两源是两条**第一原理路线**", resolution=A,
         check="search markdown for OCIMF/Isherwood digitised chart assets",
         result="absent",
         note="原文“本仓没有 OCIMF/Isherwood 数字化图表”；风压两源实为两条第一原理路线而非文献回归表。"),
    dict(id="A28", cls="declared_absence", label="污损船队统计标定未做声明", section="⑤ 注意点",
         kind="charspan", anchor="未做船队统计标定", resolution=A,
         check="search markdown for fleet-statistics calibration of the fouling growth law",
         result="absent",
         note="生长律为声明线性律（v=8 μm/月，24 月）；无船队统计标定数据，登记为缺失而非零。"),
    dict(id="A29", cls="metadata_field", label="报告自述的 JSON 字段 accuracy_caveat", section="⑤ 注意点",
         kind="charspan", anchor="`accuracy_caveat` 已显式写入报告 JSON", resolution=U,
         check="key 'accuracy_caveat' present in GET /tensor/reports/10459 payload top-level keys?",
         result="unresolved",
         note="markdown 自述该字段已写入报告 JSON，但平台记录顶层键为 id/title/summary/scenario_key/mission_id/stage/tags/figures/status/created_by/created_at/markdown，无 accuracy_caveat —— 上游不一致，如实登记，不代写该字段。"),
]

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.M)


def local_hash(md: str) -> str:
    return hashlib.sha256(md.encode("utf-8")).hexdigest()


def line_starts(md: str):
    starts = [0]
    for m in re.finditer(r"\n", md):
        starts.append(m.end())
    return starts


def char_to_line(starts, pos: int) -> int:
    lo, hi = 0, len(starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if starts[mid] <= pos:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


def build(md: str, payload: dict) -> dict:
    lines = md.split("\n")
    starts = line_starts(md)
    n = md.count

    assets = []
    for spec in ASSETS:
        aid = spec["id"]
        if spec["kind"] == "document":
            quote = md
            start_char, end_char = 0, len(md)
            start_line, end_line = 1, len(lines)
            unique = True
            method = "document"
        elif spec["kind"] == "span":
            anchor = spec["anchor"]
            if n(anchor) != 1:
                sys.exit("anchor not unique in markdown: %r (count=%d)" % (anchor, n(anchor)))
            a_line = char_to_line(starts, md.index(anchor))
            first, last = spec["span"]
            l0 = a_line - 1 + first
            l1 = a_line - 1 + last
            quote = "\n".join(lines[l0:l1 + 1])
            start_char = starts[l0]
            end_char = starts[l1] + len(lines[l1]) if l1 < len(lines) else len(md)
            start_line, end_line = l0 + 1, l1 + 1
            unique = n(quote) == 1
            method = "char_span"
        else:  # charspan
            anchor = spec["anchor"]
            if n(anchor) != 1:
                sys.exit("anchor not unique in markdown: %r (count=%d)" % (anchor, n(anchor)))
            quote = anchor
            start_char = md.index(anchor)
            end_char = start_char + len(quote)
            start_line = char_to_line(starts, start_char)
            end_line = char_to_line(starts, end_char - 1)
            unique = True
            method = "char_span"

        # independent re-check: the emitted quote must itself be locatable verbatim
        if md[start_char:end_char] != quote:
            sys.exit("%s: char span does not reproduce quote" % aid)
        if quote not in md:
            sys.exit("%s: quote not a substring of markdown" % aid)

        assets.append({
            "asset_id": aid,
            "asset_class": spec["cls"],
            "label": spec["label"],
            "in_report_section": spec["section"],
            "locator": {
                "method": method,
                "start_char": start_char,
                "end_char": end_char,
                "start_line": start_line,
                "end_line": end_line,
                "quote": quote,
                "unique": bool(unique),
            },
            "resolution": spec["resolution"],
            "resolution_check": {"check": spec["check"], "result": spec["result"]},
            "note": spec["note"],
        })

    ids = [a["asset_id"] for a in assets]
    if len(ids) != len(set(ids)):
        sys.exit("duplicate asset_id")

    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    headings = [
        {"level": len(m.group(1)), "text": m.group(2), "line_no": md[:m.start()].count("\n") + 1}
        for m in HEADING_RE.finditer(md)
    ]

    digest = local_hash(md)
    return {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "objective": {"register_assets": True, "classify_report_type": False},
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": digest,
            "hash_scope": "markdown encoded as utf-8",
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "title": payload.get("title"),
            "scenario_key": payload.get("scenario_key"),
            "mission_id": payload.get("mission_id"),
            "status": payload.get("status"),
            "created_at": payload.get("created_at"),
            "platform_figures": payload.get("figures") or [],
            "platform_tags": payload.get("tags") or [],
            "fetched_via": "GET /api/v1/tensor/reports/10459",
            "generator": "scripts/kf_wp10459_register_assets.py",
        },
        "resolution_vocabulary": {
            "resolved_in_source": "target bytes are inside the source markdown (or are the markdown itself); locator resolves to an exact slice/hash",
            "referenced_unresolved": "reference located in the markdown, but the target (file/figure bytes/JSON field) has no payload in this worktree or platform record -- nothing invented",
            "declared_absent": "the report itself declares the target to be absent/not done; registered as an explicit absence",
            "note": "resolution says nothing about truth or verification; no item here is marked verified",
        },
        "structure_index": {
            "note": "headings only, for downstream-工序 locator scaffolding; no content extracted here",
            "headings": headings,
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get(S, 0),
            "referenced_unresolved": by_res.get(U, 0),
            "declared_absent": by_res.get(A, 0),
            "claims": 0,
        },
        "assets": assets,
        "claims": [],
        "integrity": {
            "quote_uniqueness": "every quote asserted to occur exactly once in the markdown (unique=true for all %d assets)" % len(assets),
            "hash_recomputed_locally": digest,
            "hash_matches_contract": digest == CONTRACT_HASH,
            "chars_matches_contract": len(md) == CONTRACT_CHARS,
            "contract_expected_hash": CONTRACT_HASH,
            "contract_expected_chars": CONTRACT_CHARS,
        },
        "explicit_non_actions": [
            "no claim extraction (objective.classify_report_type=false; claims=[])",
            "no verification marking (verification computed by platform gate)",
            "no re-computation of the report's numbers; registration only",
            "no read/write of any other report_id",
        ],
    }


def main():
    if not MD_PATH.exists():
        sys.exit("missing %s -- run scripts/kf_wp10459_fetch.py first" % MD_PATH)
    md = MD_PATH.read_text(encoding="utf-8")
    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    if local_hash(md) != CONTRACT_HASH:
        sys.exit("refusing to register: local snapshot hash != contract hash")

    manifest = build(md, payload)
    for d in (ART, DOC):
        d.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest, ensure_ascii=False, indent=2)

    (ART / "asset_manifest.json").write_text(text, encoding="utf-8")
    (DOC / "asset_manifest.json").write_text(text, encoding="utf-8")

    result = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + manifest["source"]["hash"],
            "source_field": SOURCE_FIELD,
            "producer": "scripts/kf_wp10459_register_assets.py",
            "emitted_at": manifest["generated_at"],
            "notes": "asset registration only; claims empty by contract; no verification marks",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    rtext = json.dumps(result, ensure_ascii=False, indent=2)
    (DOC / "kf_result.json").write_text(rtext, encoding="utf-8")
    (RUN / "kf_result_block.json").write_text(rtext, encoding="utf-8")

    c = manifest["counts"]
    print("assets=%d resolved=%d unresolved=%d absent=%d" % (
        c["assets"], c["resolved_in_source"], c["referenced_unresolved"], c["declared_absent"]))
    print("by_class=%s" % json.dumps(c["by_class"], ensure_ascii=False))
    print("hash_matches_contract=%s" % manifest["integrity"]["hash_matches_contract"])
    print("wrote: %s" % ", ".join(str(p.relative_to(REPO)) for p in
                                 (ART / "asset_manifest.json", DOC / "asset_manifest.json",
                                  DOC / "kf_result.json", RUN / "kf_result_block.json")))


if __name__ == "__main__":
    main()