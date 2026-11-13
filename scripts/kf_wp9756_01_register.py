#!/usr/bin/env python3
"""wp-9756-01 | 01-asset-registration for report_id=9756.

Read-only on the platform: fetches tensor://reports/9756 (markdown), recomputes the
sha256 of the markdown UTF-8 bytes against the contract value, resolves every
registered locator as a verbatim substring of that markdown (zero hand-copy
discipline), and emits

    docs/kf/wp-9756-01/asset_manifest.json   asset registry (no extraction)
    docs/kf/wp-9756-01/locator_check.json    locator -> offset/line resolution report
    docs/kf/wp-9756-01/kf_result.json        kf_result.v1 envelope (schema-validated)
    docs/kf/wp-9756-01/source.md             verbatim copy of the source markdown
    docs/kf/wp-9756-01/sha256.txt            recomputed digest
    docs/kf/wp-9756-01/figures/asset_manifest_coverage.png   coverage bar chart

No other report_id is read or written. No claim is marked verified: hash equality and
substring resolution are mechanical identity checks; verification status stays with the
platform gate.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PWD = os.environ["TENSOR_AGENT_PASS"]
REPORT_ID = "9756"
PKG = "wp-9756-01"
EXPECTED_HASH = "sha256:66c02e91e7ffcc3d81b24465112b94ac481ebc351584c13d01d978c16be4316b"
EXPECTED_CHARS = 8293
EXPECTED_TITLE = ("P78-N03 船舶 EEXI/CII 绿色合规机器判决门成熟化：Annex 2 逐项达到值 + "
                  "G4 A–E 评级 + 年度合规报告 + 两处合规误判缺陷修复")
EXPECTED_SCENARIO = "ship_performance/green_compliance"
OUT = f"docs/kf/{PKG}"  # must live under docs/: the push gate drops artifacts/**
SCHEMA = "schemas/kf_result.v1.schema.json"

# ---------------------------------------------------------------- reference table
# (asset_id, kind, name, section, quote taken verbatim from the markdown, resolution,
#  resolution evidence, note)
# resolution: resolved_in_source | metadata_only | referenced_unresolved
FIG_DIR = "artifacts/p78n03_green_compliance"
REFS = [
    ("r9756:code:green_compliance", "source_code_reference",
     "backend/services/green_compliance.py", "头部行（代码清单）",
     "backend/services/green_compliance.py",
     "referenced_unresolved",
     "path text only; file lives in the producing repo ship-performance-platform",
     "判决核心实现（EEXI/CII 达到值、评级、报告装配）"),
    ("r9756:code:green_shipping", "source_code_reference",
     "backend/api/green_shipping.py", "头部行（代码清单）",
     "backend/api/green_shipping.py",
     "referenced_unresolved",
     "path text only; file lives in the producing repo ship-performance-platform",
     "四个 green-shipping 端点薄壳"),
    ("r9756:artifact:dir", "artifact_directory_reference",
     FIG_DIR + "/", "头部行（产物）",
     "`artifacts/p78n03_green_compliance/`（results.json + 4 图，png sha256 入 results.json）",
     "referenced_unresolved",
     "directory only; binaries live in the producing repo, not in this report record",
     "产物目录：results.json + 4 图；裸路径串在正文出现 8 次，故登记引文取带内容的完整行以保证唯一定位"),
    ("r9756:test:green_compliance", "test_module_reference",
     "`backend/tests/test_green_compliance.py`（53 例，含 6 例端点）", "头部行（用例）",
     "`backend/tests/test_green_compliance.py`（53 例，含 6 例端点）",
     "referenced_unresolved",
     "path text only; 裸路径串在正文出现 2 次（头部行 + §6 注），"
     "故登记引文取头部行的完整表述以保证唯一定位",
     "本节点 53 例（含 6 例端点）"),
    ("r9756:test:green_shipping", "test_module_reference",
     "backend/tests/test_green_shipping.py", "§7 复现清单",
     "tests/test_green_shipping.py",
     "referenced_unresolved",
     "path text only (written relative to backend/ in the §7 command)",
     "原有用例不回归：18 passed"),
    ("r9756:code:main", "source_code_reference",
     "backend/main.py", "§7 未跑说明",
     "backend/main.py",
     "referenced_unresolved",
     "path text only; explicitly declared NOT run in §7",
     "全量装配未跑（本地缺 openpyxl，声明为既有环境缺口）"),
    ("r9756:code:cii_required_value", "code_symbol_reference",
     "services/cii_required_value.required_cii", "§2 步骤 3 / §5 D2",
     "`services/cii_required_value.required_cii` 的**显式 regime**",
     "referenced_unresolved",
     "module.symbol text only; 裸符号串在正文出现 2 次（§2 步骤 3 与 §5 D2），"
     "故登记引文取 §2 完整表述以保证唯一定位",
     "CII 要求值显式 regime 的被委托实现（<2023 抛错 / 2027+ 外推标记）"),
    ("r9756:code:holtrop1984", "code_symbol_reference",
     "api.holtrop1984", "§1 参数表（R_T 出处）",
     "`api.holtrop1984`",
     "referenced_unresolved",
     "module text only; path text quoted from the parameter table 出处 column",
     "KVLCC2 R_T=2,047.3 kN 的来源链"),
    ("r9756:artifact:gen_artifacts", "script_artifact_reference",
     FIG_DIR + "/gen_artifacts.py", "§7 复现块",
     "python3 artifacts/p78n03_green_compliance/gen_artifacts.py",
     "referenced_unresolved",
     "command text only; script lives in the producing repo",
     "生成 results.json + 4 图 + 报告正文（程序化，零手抄）"),
    ("r9756:artifact:results_json", "data_artifact_reference",
     FIG_DIR + "/results.json", "§7 复现块",
     "`artifacts/p78n03_green_compliance/results.json`（含 png sha256、全部中间量）",
     "referenced_unresolved",
     "path text only; JSON payload not carried by the report record",
     "中间量 + 4 图 png sha256 的落盘处"),
    ("r9756:artifact:figure1_path", "figure_reference",
     FIG_DIR + "/fig1_eexi_vs_dwt.png", "§4 结果图",
     "![fig1_eexi_vs_dwt.png](artifacts/p78n03_green_compliance/fig1_eexi_vs_dwt.png)",
     "referenced_unresolved",
     "markdown image link; PNG bytes not carried by the report record",
     "与 record.figures[0] 同名（fig1_eexi_vs_dwt.png）"),
    ("r9756:artifact:figure2_path", "figure_reference",
     FIG_DIR + "/fig2_cii_rating_bands.png", "§4 结果图",
     "![fig2_cii_rating_bands.png](artifacts/p78n03_green_compliance/fig2_cii_rating_bands.png)",
     "referenced_unresolved",
     "markdown image link; PNG bytes not carried by the report record",
     "与 record.figures[1] 同名（fig2_cii_rating_bands.png）"),
    ("r9756:artifact:figure3_path", "figure_reference",
     FIG_DIR + "/fig3_power_limit.png", "§4 结果图",
     "![fig3_power_limit.png](artifacts/p78n03_green_compliance/fig3_power_limit.png)",
     "referenced_unresolved",
     "markdown image link; PNG bytes not carried by the report record",
     "与 record.figures[2] 同名（fig3_power_limit.png）"),
    ("r9756:artifact:figure4_path", "figure_reference",
     FIG_DIR + "/fig4_grade_vs_year.png", "§4 结果图",
     "![fig4_grade_vs_year.png](artifacts/p78n03_green_compliance/fig4_grade_vs_year.png)",
     "referenced_unresolved",
     "markdown image link; PNG bytes not carried by the report record",
     "与 record.figures[3] 同名（fig4_grade_vs_year.png）"),
    ("r9756:endpoint:rating_boundaries", "api_endpoint_reference",
     "GET /api/v1/green-shipping/rating_boundaries", "§7 端点自检",
     "GET /api/v1/green-shipping/rating_boundaries",
     "referenced_unresolved",
     "endpoint text only; the platform under registration is ship-performance-platform, "
     "not this knowledge repo — no HTTP call is made by this package",
     "dd 向量分级边界查询"),
    ("r9756:endpoint:eexi_full", "api_endpoint_reference",
     "POST /api/v1/green-shipping/eexi_full", "§7 端点自检",
     "POST /api/v1/green-shipping/eexi_full",
     "referenced_unresolved",
     "endpoint text only; not called by this package",
     "Annex 2 逐项达到值（terms/denominator 可审计）"),
    ("r9756:endpoint:cii_rating", "api_endpoint_reference",
     "POST /api/v1/green-shipping/cii_rating", "§7 端点自检",
     "POST /api/v1/green-shipping/cii_rating",
     "referenced_unresolved",
     "endpoint text only; not called by this package",
     "A–E 评级 + dd 向量"),
    ("r9756:endpoint:compliance_report", "api_endpoint_reference",
     "POST /api/v1/green-shipping/compliance_report", "§7 端点自检",
     "POST /api/v1/green-shipping/compliance_report",
     "referenced_unresolved",
     "endpoint text only; not called by this package",
     "年度合规报告装配 + 32 字段完整性"),
    ("r9756:endpoint:legacy_eexi_eedi", "api_endpoint_reference",
     "/eexi 与 /eedi", "§5 D1",
     "`/eexi` 与 `/eedi`",
     "referenced_unresolved",
     "endpoint text only (short form as written in D1); not called by this package",
     "D1 量纲缺陷的影响面端点，正文以简称给出，未写全前缀路径"),
    ("r9756:repro:gen_artifacts", "repro_command",
     "python3 artifacts/p78n03_green_compliance/gen_artifacts.py", "§7 复现块",
     "python3 artifacts/p78n03_green_compliance/gen_artifacts.py     # 生成 results.json + 4 图 + 本文档",
     "referenced_unresolved",
     "command text only; runs in the producing repo",
     "产线复现命令 1/3（生成侧）"),
    ("r9756:repro:pytest_green_compliance", "repro_command",
     "cd backend && python -m pytest tests/test_green_compliance.py -q", "§7 复现块",
     "cd backend && python -m pytest tests/test_green_compliance.py -q   # 53 passed",
     "referenced_unresolved",
     "command text only; 53 passed is the upstream author's reported count, not re-run here",
     "产线复现命令 2/3（本节点用例；报告 §7 尾注又说「本节点 49 例」，见 observations）"),
    ("r9756:repro:pytest_green_shipping", "repro_command",
     "cd backend && python -m pytest tests/test_green_shipping.py -q", "§7 复现块",
     "cd backend && python -m pytest tests/test_green_shipping.py -q     # 18 passed（原有用例不回归）",
     "referenced_unresolved",
     "command text only; 18 passed is the upstream author's reported count, not re-run here",
     "产线复现命令 3/3（回归侧）"),
]

# section anchors that pin the report structure (registered as locators, not assets)
ANCHORS = [
    ("q01", "## 1. 案例介绍（物理背景 / 几何 / 参数表）", "报告有案例介绍节（几何/参数表）"),
    ("q02", "## 4. 结果图", "报告有结果图节（4 个 markdown 图片链接）"),
    ("q03", "## 5. 注意点（踩过的坑 / 局限 / 适用范围）", "报告自报局限节（D1/D2 + 诚实边界）"),
    ("q04", "## 6. 误差判定（逐项 vs 基准）", "报告有逐项误差判定节"),
    ("q05", "## 7. 审计链与复现", "报告有复现节（3 条命令）"),
    ("q06", "## 发布注记（诚实披露）", "报告有发布注记（共享 /tmp 路径冲突自述）"),
    ("q07", "**产物**：`artifacts/p78n03_green_compliance/`（results.json + 4 图，png sha256 入 results.json）",
     "产物目录与内容声明"),
    ("q08", "| C_F (HFO) | 3.114 gCO2/gFuel | MEPC.364(79)（与化学计量派生互证 <3%） |",
     "参数表把 C_F 标为声明输入（未回读规则 PDF）"),
    ("q09", "参考线 / 削减率 / Z 表 / dd 向量均为**离线转录**（WITHHELD），未回读规则 PDF；",
     "系数层证据等级自报为 WITHHELD"),
    ("q10", "> C2 要求值与高精度复算偏差 0.00e+00% ≪3%。",
     "C2 复算偏差声明（上游表述，本包未复核）"),
    ("q11", "但**对规则原文**的偏差不可评估（系数层 WITHHELD，无原文基准）——这一条如实声明为",
     "对规则原文偏差不可评估的显式声明（无基准）"),
    ("q12", "id 9750（ingress 探针）、9754（串稿占位）为此次共享路径冲突的副产物，",
     "正文提及兄弟 report_id 9750/9754：仅登记为交叉引用，本包不读不写它们"),
]


# (about, [verbatim quotes from the markdown], note) — each quote becomes a locator.
# Facts that do NOT live in the markdown (e.g. HTTP probe codes) are recorded elsewhere
# in the manifest (counts.figure_probe_http_status), never dressed up as a source quote.
OBSERVATIONS = [
    ("用例计数两处口径",
     ["cd backend && python -m pytest tests/test_green_compliance.py -q   # 53 passed",
      "已跑：本节点 49 例 + 原 green_shipping 18 例全绿。"],
     "§7 命令注记写 53 passed，同节尾注写「本节点 49 例」；两处均为上游作者计数，本包只登记不复核"),
    ("兄弟 report_id 交叉引用",
     ["id 9750（ingress 探针）、9754（串稿占位）为此次共享路径冲突的副产物，"],
     "正文提及 9750/9754 为共享 /tmp 路径冲突副产物；本包不读不写这些报告，仅登记该交叉引用"),
    ("附件字节不可得",
     ["**产物**：`artifacts/p78n03_green_compliance/`（results.json + 4 图，png sha256 入 results.json）"],
     "记录侧 figures 只有 name+caption（本包探测 figures 端点全部 404，见 counts.figure_probe_http_status），"
     "二进制保存在产出仓；故 4 图登记为 metadata_only、4 条文内图链接登记为 referenced_unresolved"),
]


def post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def get_json(url: str, token: str):
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    return json.loads(urllib.request.urlopen(req, timeout=120).read())


def login() -> str:
    last: Exception | None = None
    for path in ("/auth/login", "/auth/token"):
        try:
            payload = {"username": USER, "password": PWD}
            body = post_json(BASE + path, payload)
            tok = body.get("access_token") or body.get("token")
        except Exception as exc:  # noqa: BLE001
            last = exc
            continue
        if tok:
            return tok
    raise SystemExit(f"login failed: {last}")


def probe(token: str, path: str) -> int | str:
    req = urllib.request.Request(BASE + path)
    req.add_header("Authorization", f"Bearer {token}")
    try:
        return urllib.request.urlopen(req, timeout=30).status
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        return exc.code
    except Exception as exc:  # noqa: BLE001
        return f"error: {exc}"


def line_of(md: str, pos: int) -> int:
    return md.count("\n", 0, pos) + 1


def main() -> None:
    tok = login()
    rec = get_json(f"{BASE}/tensor/reports/{REPORT_ID}", tok)
    if isinstance(rec.get("report"), dict):
        rec = rec["report"]
    md: str = rec["markdown"]

    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    got_hash = f"sha256:{digest}"
    hash_ok = got_hash == EXPECTED_HASH
    chars_ok = len(md) == EXPECTED_CHARS
    title_ok = rec.get("title") == EXPECTED_TITLE
    scenario_ok = rec.get("scenario_key") == EXPECTED_SCENARIO

    # ---- locators (mechanical resolution, no hand counting) --------------------
    locators = []

    def add_locator(lid: str, quote: str, meaning: str, asset_id: str | None = None) -> dict:
        pos = md.find(quote)
        n = md.count(quote)
        item = {
            "locator_id": lid,
            "asset_id": asset_id,
            "meaning": meaning,
            "source_field": "markdown",
            "quote": quote,
            "resolvable": pos >= 0,
            "char_start": pos if pos >= 0 else None,
            "char_end": (pos + len(quote)) if pos >= 0 else None,
            "line": line_of(md, pos) if pos >= 0 else None,
            "occurrences": n,
            "unique": n == 1,
        }
        locators.append(item)
        return item

    for qid, quote, meaning in ANCHORS:
        add_locator(qid, quote, meaning)

    assets = []
    for aid, kind, name, section, quote, resolution, res_note, note in REFS:
        loc = add_locator(f"L{len(assets) + 101}", quote, f"{kind}: {name}", aid)
        assets.append({
            "asset_id": aid,
            "kind": kind,
            "name": name,
            "in_report_section": section,
            "locator": {
                "source_field": "markdown",
                "locator_id": loc["locator_id"],
                "char_start": loc["char_start"],
                "char_end": loc["char_end"],
                "line": loc["line"],
                "quote": loc["quote"],
                "occurrences": loc["occurrences"],
                "unique": loc["unique"],
            },
            "resolution": resolution,
            "resolution_note": res_note,
            "note": note,
        })

    # ---- figures carried by the report record (metadata only) ------------------
    figures = [f for f in (rec.get("figures") or []) if isinstance(f, dict) and f.get("name")]
    probe_codes = {}
    for i, fig in enumerate(figures, start=1):
        name = fig["name"]
        code = probe(tok, f"/tensor/reports/{REPORT_ID}/figures/{name}")
        probe_codes[name] = code
        assets.append({
            "asset_id": f"r9756:figure:{i:02d}",
            "kind": "embedded_figure_metadata",
            "name": name,
            "caption": fig.get("caption"),
            "in_report_section": "record.figures（对应 §4 结果图 markdown 链接）",
            "locator": {
                "source_field": "record",
                "pointer": f"/figures/{i - 1}",
                "quote": name,
                "unique": sum(1 for f2 in figures if f2.get("name") == name) == 1,
            },
            "resolution": "metadata_only",
            "resolution_note": (
                f"GET /tensor/reports/{REPORT_ID}/figures/{name} -> {code}; "
                "record exposes name+caption only, so no byte payload and no png hash is claimed"
            ),
            "note": "图注逐字取自报告记录（record.figures[i].caption），未下载/未校验图像内容",
        })

    # ---- source document asset ------------------------------------------------
    assets.insert(0, {
        "asset_id": "r9756:source-markdown",
        "kind": "report_markdown",
        "name": f"report-{REPORT_ID}-markdown",
        "in_report_section": "document",
        "locator": {
            "source_field": "markdown",
            "method": "document",
            "pointer": "tensor://reports/9756#markdown",
            "char_start": 0,
            "char_end": len(md),
            "line": 1,
            "quote": md.splitlines()[0] if md else "",
            "unique": True,
        },
        "resolution": "resolved_in_source",
        "resolution_note": f"GET /tensor/reports/{REPORT_ID} -> 200; markdown served verbatim",
        "notes": {
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "lines": len(md.splitlines()),
            "sha256": got_hash,
            "hash_scope": "sha256 over UTF-8 bytes of the markdown field as served by the API",
            "local_copy": f"{OUT}/source.md",
        },
        "note": "本包唯一 resolved 的资产：正文逐字节可复核；其余均为路径/图注引用",
    })

    ids = [a["asset_id"] for a in assets]
    dup_ids = sorted({i for i in ids if ids.count(i) > 1})
    unresolved_locators = [l["locator_id"] for l in locators if not l["resolvable"]]
    non_unique_locators = [l["locator_id"] for l in locators if l["occurrences"] > 1]

    by_kind: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    headings = [ln.strip() for ln in md.splitlines() if ln.startswith("#")]

    # ---- observations: every quote is machine-resolved (no unverified quotation) --
    observations = []
    for oi, (about, quotes, note) in enumerate(OBSERVATIONS, start=1):
        lids = []
        for qi, q in enumerate(quotes, start=1):
            lid = f"O{oi}q{qi}"
            loc = add_locator(lid, q, f"observation O{oi}: {about}")
            if not loc["resolvable"]:
                raise SystemExit(f"UNRESOLVED OBSERVATION QUOTE {lid}: {q!r}")
            lids.append({"locator_id": lid, "char_start": loc["char_start"],
                         "char_end": loc["char_end"], "line": loc["line"]})
        observations.append({"about": about, "quotes": quotes,
                             "locator_ids": lids, "note": note})

    manifest = {
        "manifest_version": "1.0",
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "lane": "A",
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "producer": "agent/m15666",
        "scope": "只登记 report_id=9756 的源资产（附件/工件/代码/端点/复现命令），不做抽取、不做分类",
        "source": {
            "uri": f"tensor://reports/{REPORT_ID}",
            "field": "markdown",
            "fetch": f"GET {BASE}/tensor/reports/{REPORT_ID}",
            "hash_alg": "sha256",
            "hash": got_hash,
            "hash_expected": EXPECTED_HASH,
            "hash_matches_contract": hash_ok,
            "chars": len(md),
            "chars_expected": EXPECTED_CHARS,
            "chars_matches_contract": chars_ok,
            "bytes_utf8": len(md.encode("utf-8")),
            "lines": len(md.splitlines()),
            "heading_count": len(headings),
            "headings": headings,
            "local_copy": f"{OUT}/source.md",
        },
        "identity_facts": {
            "report_id": rec.get("id"),
            "title": rec.get("title"),
            "title_matches_contract": title_ok,
            "scenario_key": rec.get("scenario_key"),
            "scenario_key_matches_contract": scenario_ok,
            "status": rec.get("status"),
            "stage": rec.get("stage"),
            "created_at": rec.get("created_at"),
            "created_by": rec.get("created_by"),
            "source_mission_id": rec.get("mission_id"),
            "tags": rec.get("tags") or [],
            "summary_chars": len(rec.get("summary") or ""),
            "summary_note": "summary 字段存在但本包不登记其内容为资产（只登记 markdown 正文）",
        },
        "assets": assets,
        "locators": locators,
        "counts": {
            "assets_total": len(assets),
            "by_kind": by_kind,
            "by_resolution": by_res,
            "locators_total": len(locators),
            "locators_resolved": len(locators) - len(unresolved_locators),
            "locators_unresolved": unresolved_locators,
            "locators_non_unique": non_unique_locators,
            "figures_declared_in_record": len(figures),
            "figures_with_bytes": 0,
            "figure_probe_http_status": probe_codes,
        },
        "id_integrity": {
            "duplicate_asset_ids": dup_ids,
            "duplicate_ids_ok": dup_ids == [],
            "outputs_keys": ["asset_manifest.json"],
            "reports_other_than_9756_touched": [],
        },
        "claims": [],
        "claims_empty_reason": (
            "契约 objective.classify_report_type=false、notes 明示「不做抽取」，且 "
            "constraints.no_forced_claim_generation=true —— 本包不产出知识对象，claims 为空即完整结果"
        ),
        "observations": observations,
        "limitations": [
            "本包不下载 PNG / results.json，不做图像或 JSON 内容校验；只登记路径文本与记录级图注",
            "本包不调用 ship-performance-platform 的任何端点，端点资产仅为正文文本登记",
            "本包不判断上游数值正确性（如 3.2755 / 2.0710 / 32/32 等），只保证它们可在原文逐字定位",
            "hash 相等只证明「该 report_id 的 markdown 与契约 source_hash 逐字节一致」，不等于内容正确",
        ],
    }

    # ---- reproducibility figure: asset coverage by resolution ------------------
    os.makedirs(os.path.join(OUT, "figures"), exist_ok=True)
    fig_path = os.path.join(OUT, "figures", "asset_manifest_coverage.png")
    fig_sha = None
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        order = ["resolved_in_source", "metadata_only", "referenced_unresolved"]
        vals = [by_res.get(k, 0) for k in order]
        fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=140)
        bars = ax.bar(order, vals, color=["#2e7d32", "#f9a825", "#c62828"])
        for b, v in zip(bars, vals):
            ax.annotate(str(v), (b.get_x() + b.get_width() / 2, v), ha="center", va="bottom")
        ax.set_ylabel("assets")
        ax.set_title(f"{PKG}: asset resolution status "
                     f"(total={len(assets)}, locators={len(locators)}/{len(locators)})")
        ax.set_ylim(0, max(vals) * 1.25 if max(vals) else 1)
        fig.tight_layout()
        fig.savefig(fig_path)
        plt.close(fig)
        fig_sha = hashlib.sha256(open(fig_path, "rb").read()).hexdigest()
    except Exception as exc:  # noqa: BLE001
        manifest["limitations"].append(f"图未生成：{exc}")

    # ---- locator check report --------------------------------------------------
    locator_report = {
        "report_id": REPORT_ID,
        "package_id": PKG,
        "source_hash": got_hash,
        "source_hash_matches_contract": hash_ok,
        "quotes_checked": len(locators),
        "quotes_resolvable": len(locators) - len(unresolved_locators),
        "unresolved": unresolved_locators,
        "non_unique": non_unique_locators,
        "checks": locators,
    }

    # ---- envelope --------------------------------------------------------------
    envelope = {
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": got_hash,
            "source_field": "markdown",
            "source_uri": f"tensor://reports/{REPORT_ID}",
            "source_hash_expected": EXPECTED_HASH,
            "source_hash_matches": hash_ok,
            "source_chars": len(md),
            "source_mission_id": rec.get("mission_id"),
            "producer": "agent/m15666",
            "emitted_at": manifest["generated_at"],
            "notes": (
                "source_hash 由 GET /tensor/reports/9756 返回的 markdown UTF-8 字节现场重算；"
                "所有引文由 markdown.find 机械定位（见 locator_check.json）；"
                "未对任何结论标 verified，verification 由平台门计算"
            ),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    # ---- schema validation -----------------------------------------------------
    import jsonschema

    schema = json.load(open(SCHEMA, encoding="utf-8"))
    jsonschema.validate(envelope, schema)
    manifest_schema = os.path.join(OUT, "asset_manifest.schema.json")
    if os.path.exists(manifest_schema):
        jsonschema.validate(manifest, json.load(open(manifest_schema, encoding="utf-8")))

    os.makedirs(OUT, exist_ok=True)
    for name, obj in (("asset_manifest.json", manifest), ("locator_check.json", locator_report),
                      ("kf_result.json", envelope)):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    with open(os.path.join(OUT, "source.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(os.path.join(OUT, "sha256.txt"), "w", encoding="utf-8") as fh:
        fh.write(f"source_markdown {got_hash}\n")
        fh.write(f"source_chars {len(md)}\n")
        fh.write(f"source_bytes_utf8 {len(md.encode('utf-8'))}\n")
        fh.write(f"contract_expected {EXPECTED_HASH} match={hash_ok}\n")
        if fig_sha:
            fh.write(f"asset_manifest_coverage_png sha256:{fig_sha}\n")

    print(f"report {REPORT_ID}: chars={len(md)} bytes={len(md.encode('utf-8'))} "
          f"hash_match={hash_ok} chars_match={chars_ok}")
    print(f"assets={len(assets)} by_resolution={by_res} locators={len(locators)}/"
          f"{len(locators) - len(unresolved_locators)} resolved")
    print(f"non-unique locators={non_unique_locators} dup_asset_ids={dup_ids}")
    print(f"figure probes={probe_codes}")
    if not hash_ok:
        raise SystemExit("SOURCE HASH MISMATCH vs contract")
    if not chars_ok:
        raise SystemExit("SOURCE CHARS MISMATCH vs contract")
    if unresolved_locators:
        raise SystemExit(f"UNRESOLVED LOCATORS: {unresolved_locators}")
    if dup_ids:
        raise SystemExit(f"DUPLICATE ASSET IDS: {dup_ids}")


if __name__ == "__main__":
    main()