#!/usr/bin/env python3
"""wp-8386-01 (task_type 01-asset-registration): register report 8386's source
asset (its markdown) and enumerate the attachments / artifacts it declares.

Registration only -- no claim extraction, no report-type classification, no
`verified` marks (contract objective: register_assets only).

Sub-commands (idempotent, stdlib only except `figure` which needs matplotlib):

    python3 scripts/kf_wp8386_01_register.py build      # write asset_manifest.json
    python3 scripts/kf_wp8386_01_register.py envelope   # wrap manifest -> kf_result.json
    python3 scripts/kf_wp8386_01_register.py verify     # acceptance checks -> verification.json
    python3 scripts/kf_wp8386_01_register.py figure     # inventory + locator map png
    python3 scripts/kf_wp8386_01_register.py all        # build+envelope+verify+figure

Design rules honoured (contract wp-8386-01):
  * every asset is located by a verbatim anchor string that must occur EXACTLY
    once in the markdown -- the quote is the raw slice md[start:end], never
    retyped, so "zero manual transcription" is structural, not a promise;
  * every declared resolution is backed by a machine probe (anchor search,
    worktree path existence, live HTTP probe) -- unresolvable stays
    referenced_unresolved instead of being invented;
  * the build aborts loudly (SystemExit) rather than emitting a half manifest.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "8386"
PACKAGE_ID = "wp-8386-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID

# contract-declared identity -- comparison targets only, never trusted blindly
CONTRACT_SOURCE_HASH = "sha256:4104143f4653a88fd9df9c12b93d3d05d42592aca5c835749a34f21ad85761af"
CONTRACT_CHARS = 20879
CONTRACT_TITLE = ("[m7061] FuelEU 柔性三件套：RFNBO 乘子 + 岸电 OPS 抵扣 + 存借跨年滚动"
                  "（判据 a–g 全 PASS）")
CONTRACT_SCENARIO = "fueleu_flexible_multiyear"

RUN_DIR = ROOT / "runs" / PACKAGE_ID
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID
FIG_DIR = OUT_DIR / "figures"
SOURCE_COPY = RUN_DIR / ("report_%s.md" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
PRODUCER = "kf-worker/m15621"

# ---------------------------------------------------------------- api helpers
def _api_base() -> str:
    base = os.environ.get("TENSOR_API_BASE")
    if not base:
        raise SystemExit("TENSOR_API_BASE not set")
    return base.rstrip("/")


def _login() -> str:
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(_api_base() + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        tok = json.load(r).get("access_token")
    if not tok:
        raise SystemExit("login returned no access_token")
    return tok


def _get(path: str, tok: str):
    req = urllib.request.Request(_api_base() + path,
                                 headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def fetch_record() -> dict:
    tok = _login()
    st, raw = _get("/tensor/reports/%s" % REPORT_ID, tok)
    if st != 200:
        raise SystemExit("GET /tensor/reports/%s -> %s %r" % (REPORT_ID, st, raw[:200]))
    return json.loads(raw)


def sha256_hex(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------- resolution probes
def probe_path(rel: str) -> dict:
    """Machine check: does the path exist inside THIS worktree?"""
    p = (ROOT / rel).resolve()
    exists = p.exists()
    return {"check": "worktree_path_exists:%s" % rel,
            "result": "present" if exists else "absent",
            "kind": "worktree_fs"}


def probe_http(path: str) -> dict:
    """Machine check: is the API route the report claims actually served?"""
    url = "http://127.0.0.1:8002/api/v1/" + path.lstrip("/")
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return {"check": "http_probe:%s" % url, "result": "resolved" if r.status < 400 else "unresolved",
                    "http_status": r.status, "kind": "http"}
    except urllib.error.HTTPError as e:
        return {"check": "http_probe:%s" % url, "result": "unresolved",
                "http_status": e.code, "kind": "http"}
    except Exception as e:  # connection refused / timeout
        return {"check": "http_probe:%s" % url, "result": "unresolved",
                "http_status": None, "error": type(e).__name__, "kind": "http"}


def probe_no_fieldmap(md: str) -> dict:
    """Machine check for a `declared_absent` asset: the report says it has no
    spatial field maps -- verify that no image reference names a contour/cloud map
    and that the absence sentence is the only occurrence of the word."""
    refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", md)
    fieldmap_like = [r for r in refs if re.search(r"(contour|field|cloud|yun|map)", r, re.I)]
    return {"check": "scan_image_references_for_fieldmap(md)",
            "result": "absent" if not fieldmap_like else "present",
            "image_refs": len(refs), "fieldmap_like": fieldmap_like,
            "absence_word_count": md.count("云图"), "kind": "content_scan"}


def probe_git(rev: str) -> dict:
    """Machine check: is the cited commit an object of THIS repository?"""
    p = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", rev + "^{commit}"],
                       capture_output=True)
    return {"check": "git_cat_file:%s" % rev,
            "result": "resolved" if p.returncode == 0 else "unresolved",
            "git_returncode": p.returncode, "kind": "git"}


# ------------------------------------------------------------ anchor table
# (asset_id, asset_class, label, report_section, anchor, resolution, note)
# anchor = verbatim substring of the markdown that occurs EXACTLY once.
ANCHORS = [
    ("A01", "document", "报告 8386 全篇 markdown（登记对象本体）", "全文",
     "# FuelEU Maritime 柔性机制三件套：RFNBO 双倍乘子 + 岸电 OPS 零排放抵扣 + 存借跨年滚动",
     "resolved_in_source", "locator.method=document：span=整篇 [0, len)，quote=首行标题（唯一）"),
    ("A02", "heading", "§1 案例介绍（章节锚）", "§1",
     "## 1  案例介绍", "resolved_in_source", "章节标题即可定位小节起点"),
    ("A03", "regulation_reference", "FuelEU Maritime 法规出处与计罚口径（2400 EUR/t VLSFO）", "§1.1",
     "FuelEU Maritime（Regulation (EU) 2023/1805）把船用能量（燃料 + 岸电）的 **Well-to-Wake",
     "resolved_in_source", "法规号以转录形式出现在原文，未与 EUR-Lex 核对（见 A29）"),
    ("A04", "parameter_table", "三船声明输入参数表（GT / MCR / 年度能量 / 燃料切换档 / 靠港电量）", "§1.2",
     "| 船 | 类型 | GT | MCR [kW] | 年度能量 [TJ] | 燃料切换档（份额） | 靠港电量 |",
     "resolved_in_source", "原文自注 declared（非实测），本工序只登记不评测"),
    ("A05", "parameter_set", "仿真窗口与结算单元数（2025–2035 / 33 单元）", "§1.2",
     "仿真窗口：2025–2035（11 年），结算粒度 = 船 × 年", "resolved_in_source", ""),
    ("A06", "clause_register", "条款证据登记表（6 条柔性条款 × 机制证据/条款核实/可绑定判定）", "§1.3",
     "| 条款 ID | 条款号（转录） | 表号 | 机制证据 | 条款核实 | 可进入可绑定判定 |",
     "resolved_in_source", "表内 6 条均 citation_verification=WITHHELD_EXTERNAL"),
    ("A07", "evidence_gate_statement", "严格模式（strict_legal）证据闸声明与 0 可绑定判定", "§1.3",
     "严格模式（`strict_legal=True`）把全部 WITHHELD 条款移出判定：乘子退回 1、OPS 按声明",
     "resolved_in_source", ""),
    ("A08", "formula_block", "能量流层代数定义（E_phys / E_eff / G_eff / GHGI）", "§2.1",
     "E_eff  = Σ_k w_k·E_k        （合规能量，w=2 对 RFNBO，w=1 其它）",
     "resolved_in_source", "公式块；本工序不校验其正确性（属工序 03/04）"),
    ("A09", "formula_block", "GHGI 闭式解与乘子导数（判据 a 的解析锚）", "§2.1",
     "GI(m)  = (m·s·g_r + o·g_o + q·g_q) / (m·s + o + q)", "resolved_in_source", ""),
    ("A10", "numeric_anchor", "罚金换算率 rate = 2400/3.73756e6 = 6.42e-04 EUR/gCO2e", "§2.2",
     "`rate = 2400/(3.73756e6) = 6.42e-04 EUR/gCO2e`", "resolved_in_source", ""),
    ("A11", "formula_block", "跨年账本闭合式（含 deficit 符号 +1）", "§2.3",
     "cb_t + bank_in_t + borrow_in_t − repay_out_t − bank_out_t − spill_t + deficit_t = 0",
     "resolved_in_source", "§5 注意点 1 记录了该符号误写过的历史坑"),
    ("A12", "formula_block", "纯 banking 解析解（不依赖 LP 的独立锚）", "§2.3",
     "deficit_t = m_(t−1) − m_t", "resolved_in_source", ""),
    ("A13", "solver_declaration", "求解器与其绑定路径（scipy.optimize.linprog HiGHS）", "§2.4",
     "（本环境无 `highspy` 包，走 SciPy 的 HiGHS 绑定）", "resolved_in_source",
     "同字符串裸写形式在 §头 与 §2.4 各出现一次，故锚点取较长唯一串"),
    ("A14", "verification_path", "顶点穷尽枚举独立复核路径（numpy 仅用 linalg）", "§2.5",
     "对小规模（3 船 × 3 年）用**顶点穷尽枚举**复核 LP", "resolved_in_source", ""),
    ("A15", "criteria_table", "机器可算判据总表（a–g，全部 PASS）", "§3.1",
     "| 判据 | 结果数字 | 阈值 | 结论 |", "resolved_in_source", ""),
    ("A16", "data_table", "逐年逐船合规余额表（33 行 × 10 列）", "§3.2",
     "| 船 | 年 | E_phys [MWh] | E_eff [MWh] | GHGI | GI_L | CB [1e9 gCO2e] | RFNBO 份额 | OPS 份额 | 单年罚金 [EUR] |",
     "resolved_in_source", "33 个结算单元逐行在场"),
    ("A17", "data_table", "严格模式对照表（判决恒为 WITHHELD）", "§3.2b",
     "| 船 | 年 | GHGI（严格模式） | CB [1e9 gCO2e] | 单年罚金 [EUR] | 判决 |",
     "resolved_in_source", ""),
    ("A18", "data_table", "机制阶梯表（no_flex → fleet_pool+bank+borrow）", "§3.3",
     "| 配置 | LP 状态 | 累计罚金 [EUR] | 相对无柔性降幅 | 变量数 | 等式数 | 生效条款 |",
     "resolved_in_source", ""),
    ("A19", "data_table", "灵敏度表（energy ±30% / GWP20 vs GWP100）", "§3.5",
     "| 扰动 | GWP | 能量缩放 | 无柔性罚金 [EUR] | 单船柔性罚金 [EUR] | 船队柔性罚金 [EUR] | 平均 GHGI |",
     "resolved_in_source", ""),
    ("A20", "data_table", "κ 灵敏度与硬模式负控表", "§3.6",
     "| κ | 硬模式状态 | 累计罚金 [EUR] |", "resolved_in_source", ""),
    ("A21", "figure_set", "6 张结果图（PNG，报告 §4 逐图引用）", "§4",
     "![fig_ghgie_trajectory.png](../../artifacts/fueleu_maritime_m7061/fig_ghgie_trajectory.png)",
     "referenced_unresolved", "PNG 落在上游仓 ship-performance-platform 的 artifacts/ 下，本工作树不含"),
    ("A22", "data_artifact_reference", "acceptance.json（判据数字与每图 sha256 的机器产物）", "§8",
     "`artifacts/fueleu_maritime_m7061/acceptance.json`（程序化生成",
     "referenced_unresolved", "上游仓产物，本工作树不含"),
    ("A23", "source_code_reference", "实现模块目录 backend/modules/fueleu_maritime/", "§8",
     "`backend/modules/fueleu_maritime/`（clauses / energy / compliance_balance /",
     "referenced_unresolved", "上游仓目录，本工作树不含"),
    ("A24", "test_reference", "模块测试集（74 项，覆盖判据 a–g）", "§8",
     "`backend/modules/fueleu_maritime/tests/`（74 项，覆盖判据 a–g）",
     "referenced_unresolved", "上游仓目录，本工作树不含"),
    ("A25", "api_surface", "HTTP 路由声明 /api/v1/fueleu-maritime/{...}", "§8",
     "`/api/v1/fueleu-maritime/{registry,case,compliance,portfolio}`",
     "referenced_unresolved", "实测探针见 manifest 的 resolution_check（http_status 非 2xx）"),
    ("A26", "vcs_reference", "上游基线提交 7017a623", "报告头",
     "**基线提交**：`7017a623`", "referenced_unresolved",
     "本仓（TensorKnowledge）对象库不含该提交，git cat-file 探针结果见 resolution_check"),
    ("A27", "repro_command_block", "复跑命令块（pytest 74 项 / run_case.py / gen_report.py）", "§7",
     "python3 artifacts/fueleu_maritime_m7061/run_case.py", "resolved_in_source",
     "命令块在场，但其执行依赖 A22/A23 所在上游仓（本工作树不可执行）"),
    ("A28", "limitation_set", "NOT_SUPPORTED 诚实清单（Art. 23(2) 加成 / 多期偿还）", "§7",
     "- Art. 23(2) 连续不合规罚金加成（NOT_SUPPORTED，累计罚金为下界）",
     "resolved_in_source", "原文自述不支持项，本工序原样登记不改判"),
    ("A29", "external_evidence_gap", "EUR-Lex 原文核对缺口（WITHHELD_EXTERNAL 行）", "§6",
     "| 法规限值台阶 / 罚金单价 vs EUR-Lex 原文 | WITHHELD_EXTERNAL | 离线无外网，无法核对原文 | 无基准（声明） |",
     "referenced_unresolved", "离线无外网通道，登记为不可解析，不编造核对结论"),
    ("A30", "figure_declaration_absent", "空间场量云图声明缺席（0 维法规账务模型）", "§4",
     "（本节点是 0 维法规账务模型，没有空间场量，故无云图", "declared_absent",
     "原文显式声明无云图；本工序不据此推断任何缺失"),
]

# non-anchor probes attached to specific assets
EXTRA_PROBES = {
    "A21": lambda md: probe_path("artifacts/fueleu_maritime_m7061/fig_ghgie_trajectory.png"),
    "A22": lambda md: probe_path("artifacts/fueleu_maritime_m7061/acceptance.json"),
    "A23": lambda md: probe_path("backend/modules/fueleu_maritime"),
    "A24": lambda md: probe_path("backend/modules/fueleu_maritime/tests"),
    "A25": lambda md: probe_http("fueleu-maritime/registry"),
    "A26": lambda md: probe_git("7017a623"),
    "A29": lambda md: probe_path("artifacts/fueleu_maritime_m7061/eurlex"),
    "A30": lambda md: probe_no_fieldmap(md),
}

RESULT_TO_STATUS = {"resolved": "resolved_in_source", "present": "resolved_in_source",
                    "unresolved": "referenced_unresolved", "absent": None}


def line_of(md: str, pos: int) -> int:
    return md.count("\n", 0, pos) + 1


def build_manifest(record: dict) -> dict:
    md = record["markdown"]
    digest = sha256_hex(md.encode("utf-8"))
    if digest != CONTRACT_SOURCE_HASH:
        raise SystemExit("FATAL: live markdown %s != contract %s" % (digest, CONTRACT_SOURCE_HASH))
    assets = []
    for aid, cls, label, section, anchor, resolution, note in ANCHORS:
        n = md.count(anchor)
        if n != 1:
            raise SystemExit("FATAL: anchor for %s occurs %d times (must be 1): %r"
                             % (aid, n, anchor[:60]))
        idx = md.index(anchor)
        end = idx + len(anchor)
        if aid == "A01":
            locator = {"method": "document", "start_char": 0, "end_char": len(md),
                       "start_line": 1, "end_line": line_of(md, max(len(md) - 1, 0)),
                       "quote": md[idx:end], "unique": n == 1}
            check = {"check": "document_sha256_span_covers_whole_markdown",
                     "result": "resolved"}
        else:
            locator = {"method": "char_span", "start_char": idx, "end_char": end,
                       "start_line": line_of(md, idx), "end_line": line_of(md, end - 1),
                       "quote": md[idx:end], "unique": n == 1}
            check = {"check": "unique_substring_anchor_in_markdown", "result": "resolved"}
        if aid in EXTRA_PROBES:
            probe = EXTRA_PROBES[aid](md)
            mapped = RESULT_TO_STATUS.get(probe["result"])
            if mapped is None:
                # probe says 'absent': either the report itself declares the asset
                # absent, or the asset is referenced but not present in this worktree
                if resolution not in ("declared_absent", "referenced_unresolved"):
                    raise SystemExit("FATAL: %s probed absent but declared %s"
                                     % (aid, resolution))
            elif mapped != resolution:
                raise SystemExit("FATAL: %s declared %s but probe says %s"
                                 % (aid, resolution, probe["result"]))
            check = probe
        elif resolution != "resolved_in_source":
            raise SystemExit("FATAL: %s declares %s without a machine probe" % (aid, resolution))
        assets.append({"asset_id": aid, "asset_class": cls, "label": label,
                       "in_report_section": section, "locator": locator,
                       "resolution": resolution, "resolution_check": check,
                       "note": note})
    ids = [a["asset_id"] for a in assets]
    if len(ids) != len(set(ids)):
        raise SystemExit("FATAL: duplicate asset_id")
    by_class: dict = {}
    by_res: dict = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    figures = record.get("figures") or []
    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest.split(":", 1)[1],
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "title": record.get("title"),
            "scenario_key": record.get("scenario_key"),
            "platform_figures": [f.get("name") for f in figures],
            "platform_tags": record.get("tags") or [],
            "title_matches_contract": record.get("title") == CONTRACT_TITLE,
            "scenario_matches_contract": record.get("scenario_key") == CONTRACT_SCENARIO,
            "chars_match_contract": len(md) == CONTRACT_CHARS,
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
        # registration-only: no claim extraction in this package
        "claims": [],
        "claims_note": ("objective.register_assets only; classify_report_type=false and no "
                        "extraction -- an empty claims[] is the complete, honest result, "
                        "not a missing one."),
        "integrity": {
            "quote_uniqueness": "each locator.quote anchored by a string occurring exactly once",
            "hash_recomputed_locally": True,
            "hash_matches_contract": digest == CONTRACT_SOURCE_HASH,
            "anchors_checked": len(assets),
        },
        "producer": PRODUCER,
    }
    return manifest


def cmd_build() -> int:
    rec = fetch_record()
    SOURCE_COPY.parent.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_text(rec["markdown"], encoding="utf-8")
    (RUN_DIR / ("report_%s.json" % REPORT_ID)).write_text(
        json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = build_manifest(rec)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(MANIFEST.relative_to(ROOT)),
                      "sha256": sha256_hex(MANIFEST.read_bytes()),
                      "counts": manifest["counts"]}, ensure_ascii=False, indent=2))
    return 0


def cmd_envelope() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": CONTRACT_SOURCE_HASH,
            "source_field": "markdown",
            "producer": PRODUCER,
            "emitted_at": utcnow(),
            "notes": ("hash recomputed from GET /api/v1/tensor/reports/%s at build time and "
                      "compared to the contract value; locators are raw markdown slices"
                      % REPORT_ID),
        },
        "outputs": {
            "asset_manifest.json": manifest,
        },
        "claims": [],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"envelope": str(ENVELOPE.relative_to(ROOT)),
                      "sha256": sha256_hex(ENVELOPE.read_bytes()),
                      "output_keys": list(env["outputs"])}, ensure_ascii=False, indent=2))
    return 0


# ------------------------------------------------------------------ checks
def check_locators(md: str, manifest: dict) -> list:
    """Re-resolve every locator against a freshly fetched markdown."""
    problems = []
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        if a["asset_id"] == "A01":
            if loc["method"] != "document" or loc["end_char"] != len(md):
                problems.append((a["asset_id"], "document_span_mismatch"))
            if sha256_hex(md.encode("utf-8")).split(":", 1)[1] != manifest["source"]["hash"]:
                problems.append((a["asset_id"], "hash_mismatch"))
            continue
        if md[loc["start_char"]:loc["end_char"]] != q:
            problems.append((a["asset_id"], "slice_mismatch"))
            continue
        if md.count(q) != 1:
            problems.append((a["asset_id"], "quote_not_unique"))
            continue
        if loc["start_line"] != md.count("\n", 0, loc["start_char"]) + 1:
            problems.append((a["asset_id"], "line_drift"))
    return problems


def check_duplicate_ids(manifest: dict) -> list:
    seen, dups = set(), []
    for a in manifest["assets"]:
        if a["asset_id"] in seen:
            dups.append(a["asset_id"])
        seen.add(a["asset_id"])
    return dups


def check_resolution_consistency(manifest: dict) -> list:
    """A declared resolution must be the one the recorded probe result justifies --
    this is what stops an unresolved asset being relabelled `resolved_in_source`."""
    problems = []
    for a in manifest["assets"]:
        probe = a["resolution_check"]["result"]
        declared = a["resolution"]
        if probe in ("resolved", "present"):
            ok = declared == "resolved_in_source"
        elif probe == "unresolved":
            ok = declared == "referenced_unresolved"
        else:  # 'absent'
            ok = declared in ("referenced_unresolved", "declared_absent")
        if not ok:
            problems.append({"asset_id": a["asset_id"], "declared": declared,
                             "probe_result": probe})
    return problems


def check_claims(manifest: dict) -> list:
    bad = []
    for c in manifest["claims"]:
        if not (c.get("evidence_locator") or c.get("evidence") or c.get("status")):
            bad.append(c.get("claim_id"))
    return bad


def check_forbidden_verified(manifest: dict) -> list:
    """No asset/claim may be marked verified -- the platform gate owns that word."""
    hits = []
    blob = json.dumps(manifest, ensure_ascii=False).lower()
    for tok in ('"verified": true', '"verification_status": "verified"', '"status": "verified"'):
        if tok in blob:
            hits.append(tok)
    return hits


def cmd_verify() -> int:
    import jsonschema  # local dependency, present in this env

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rec = fetch_record()  # fresh login + fresh fetch: do not trust the local copy
    md = rec["markdown"]
    schema_path = ROOT / "schemas" / "asset_manifest.v1.1.schema.json"
    results = {}

    results["valid_json"] = {"ok": isinstance(manifest, dict), "detail": "manifest parsed as JSON"}
    try:
        jsonschema.validate(manifest, json.loads(schema_path.read_text(encoding="utf-8")))
        results["schema_pass"] = {"ok": True, "detail": "schemas/asset_manifest.v1.1.schema.json"}
    except Exception as e:  # noqa: BLE001 - report the validator message verbatim
        results["schema_pass"] = {"ok": False, "detail": str(e)[:400]}

    probs = check_locators(md, manifest)
    results["source_locator_resolvable"] = {"ok": not probs, "detail": probs or
                                            "%d locators re-resolved on live markdown"
                                            % len(manifest["assets"])}

    live = sha256_hex(md.encode("utf-8"))
    results["source_hash_matches"] = {"ok": live == CONTRACT_SOURCE_HASH,
                                      "detail": {"live": live, "contract": CONTRACT_SOURCE_HASH}}

    dups = check_duplicate_ids(manifest)
    results["no_duplicate_ids"] = {"ok": not dups, "detail": dups or
                                   "%d unique asset ids" % len(manifest["assets"])}

    bad = check_claims(manifest)
    results["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": not bad,
        "detail": {"claims": len(manifest["claims"]), "violations": bad,
                   "note": "claims=[] per contract objective (registration only)"}}

    incons = check_resolution_consistency(manifest)
    results["resolution_matches_probe"] = {"ok": not incons, "detail": incons or
                                           "all %d resolutions justified by a probe"
                                           % len(manifest["assets"])}

    verified = check_forbidden_verified(manifest)
    results["no_verified_marks"] = {"ok": not verified, "detail": verified or "none found"}

    # resolution bookkeeping must add up
    counts = manifest["counts"]
    total = counts["resolved_in_source"] + counts["referenced_unresolved"] + counts["declared_absent"]
    results["counts_consistent"] = {"ok": total == counts["assets"] == len(manifest["assets"]),
                                    "detail": {"sum": total, "assets": counts["assets"]}}

    # every non-in-source asset must carry a machine probe (not a claim)
    missing = [a["asset_id"] for a in manifest["assets"]
               if a["locator"]["method"] != "document" and "check" not in a["resolution_check"]]
    results["non_source_assets_probed"] = {"ok": not missing, "detail": missing or "all probed"}

    overall = all(v["ok"] for v in results.values())
    out = {"package_id": PACKAGE_ID, "report_id": REPORT_ID,
           "manifest_sha256": sha256_hex(MANIFEST.read_bytes()),
           "checked_at": utcnow(), "checks": results,
           "overall": "PASS" if overall else "FAIL"}
    VERIFICATION.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if overall else 1


# ----------------------------------------------------------------- figures
def cmd_figure() -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    assets = manifest["assets"]

    # fig 1: asset_class x resolution inventory
    classes = sorted({a["asset_class"] for a in assets})
    res_kinds = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    left = [0] * len(classes)
    colors = {"resolved_in_source": "#2a7f62", "referenced_unresolved": "#c9861b",
              "declared_absent": "#8a8a8a"}
    for kind in res_kinds:
        vals = [sum(1 for a in assets if a["asset_class"] == c and a["resolution"] == kind)
                for c in classes]
        ax.barh(classes, vals, left=left, color=colors[kind], label=kind)
        left = [l + v for l, v in zip(left, vals)]
    ax.set_xlabel("assets")
    ax.set_title("report 8386 asset inventory (n=%d, classes=%d)" % (len(assets), len(classes)))
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig_asset_inventory.png", dpi=140)
    plt.close(fig)

    # fig 2: locator coverage map over the markdown
    md = SOURCE_COPY.read_text(encoding="utf-8")
    fig, ax = plt.subplots(figsize=(10, 6))
    for i, a in enumerate(assets):
        s, e = a["locator"]["start_char"], a["locator"]["end_char"]
        ax.barh(i, e - s, left=s, height=0.6,
                color=colors[a["resolution"]])
        ax.text(-200, i, "%s %s" % (a["asset_id"], a["asset_class"]), ha="right", va="center",
                fontsize=6)
    ax.set_xlim(0, len(md))
    ax.set_ylim(-1, len(assets))
    ax.set_xlabel("markdown char offset (0..%d)" % len(md))
    ax.set_title("locator coverage: verbatim anchor spans (report 8386, sha256 %s…)"
                 % manifest["source"]["hash"][:12])
    ax.set_yticks([])
    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[k]) for k in res_kinds]
    ax.legend(handles, res_kinds, fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig_locator_coverage.png", dpi=140)
    plt.close(fig)

    digests = {p.name: sha256_hex(p.read_bytes()) for p in sorted(FIG_DIR.glob("*.png"))}
    (FIG_DIR / "figures.sha256.json").write_text(json.dumps(digests, indent=2), encoding="utf-8")
    print(json.dumps(digests, indent=2))
    return 0


def main(argv: list) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    if cmd == "build":
        return cmd_build()
    if cmd == "envelope":
        return cmd_envelope()
    if cmd == "verify":
        return cmd_verify()
    if cmd == "figure":
        return cmd_figure()
    if cmd == "all":
        rc = cmd_build() or cmd_envelope() or cmd_verify()
        cmd_figure()
        return rc
    raise SystemExit("unknown sub-command %r" % cmd)


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv))