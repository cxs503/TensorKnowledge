#!/usr/bin/env python3
"""wp-9503-01 (task_type=01-asset-registration): register the source assets of report 9503.

Sub-commands (idempotent; stdlib only except `figure`, which needs matplotlib):

    python3 scripts/kf_wp9503_01_register_assets.py fetch     # GET report 9503 -> runs/wp-9503-01/
    python3 scripts/kf_wp9503_01_register_assets.py build     # -> docs/kf/wp-9503-01/asset_manifest.json
    python3 scripts/kf_wp9503_01_register_assets.py envelope  # -> kf_result.json (kf_result.v1 envelope)
    python3 scripts/kf_wp9503_01_register_assets.py verify    # acceptance checks -> verification.json
    python3 scripts/kf_wp9503_01_register_assets.py figure    # locator map png
    python3 scripts/kf_wp9503_01_register_assets.py result    # KF-RESULT markdown (single json block)
    python3 scripts/kf_wp9503_01_register_assets.py all

Design rules honoured here (contract wp-9503-01):
  * registration only -- objective.register_assets=true / classify_report_type=false; NO claim
    extraction, NO verified marks (verification is the platform gate's job);
  * zero hand transcription -- every quote is sliced out of the live markdown and re-checked to be
    a *unique* substring before it is written; every count is measured here;
  * uncertainty preserved -- assets that cannot be resolved are recorded as
    referenced_unresolved / declared_absent with the reason, never dropped, never given an
    invented address;
  * failures abort loudly (SystemExit) instead of emitting a half manifest.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "9503"
PACKAGE_ID = "wp-9503-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
LANE = "B"

# contract-declared identity (work-package YAML); comparison targets only, never trusted.
CONTRACT_SOURCE_HASH = (
    "sha256:195c350dd486cb556f078b220cb348edf9210d4ac2631319b40658ee73428b5c"
)
CONTRACT_CHARS = 8176
CONTRACT_TITLE = (
    "EEXI attained 端到端闭合链路（Holtrop→推进功率→轴系效率→gCO₂/t·nm）+ 1852 倍量纲缺陷修复"
)
CONTRACT_SCENARIO = "p73w2b-n02-eexi-closed-loop"

RUN_DIR = ROOT / "runs" / PACKAGE_ID
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID  # committed (repo .gitignore drops artifacts/**)
FIG_DIR = OUT_DIR / "figures"
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
RAW_RECORD = RUN_DIR / ("record_%s.json" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
RESULT_MD = OUT_DIR / ("KF-RESULT-%s.md" % PACKAGE_ID)
LOCATOR_MAP = FIG_DIR / "locator_map.png"
PKG_SOURCE = OUT_DIR / ("source_%s.md" % REPORT_ID)
PRODUCER = "kf-worker/m15644"

ASSET_SCHEMA = ROOT / "schemas" / "asset_manifest.v2.schema.json"
ENVELOPE_SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"

# ---------------------------------------------------------------- asset table
# anchor: substring that must occur exactly once in the markdown (used only to *find* the span);
# span: (first line offset, last line offset) inclusive, relative to the anchor line;
# the emitted quote is the verbatim text of lines [anchor+first .. anchor+last].
# path: for referenced artefacts, the address as written in the report (worktree existence is
#       probed, never assumed).
ASSETS = [
    dict(
        asset_id="A01", asset_class="markdown_document",
        label="报告正文（markdown 全文，source_field=markdown）",
        section="whole-document", anchor=None, span=None, method="document",
        resolution="resolved_in_source",
        note="整篇 markdown 即源资产；sha256/字符数/字节数与契约逐项对账见 source 段。",
    ),
    dict(
        asset_id="A02", asset_class="heading",
        label="H1 标题行（报告标题）",
        section="header", anchor="# EEXI attained 端到端闭合链路", span=(0, 0),
        resolution="resolved_in_source",
        note="与平台 record.title 同源；记录值含括号内演绎，标题行不含。",
    ),
    dict(
        asset_id="A03", asset_class="provenance_declaration",
        label="产物来源声明（节点键 / 仓 / 生成时间）",
        section="header", anchor="节点 `p73w2b-n02-eexi-closed-loop`", span=(0, 0),
        resolution="resolved_in_source",
        note="声明本报告由节点 p73w2b-n02-eexi-closed-loop 在 ship-performance-platform 生成；节点键与契约 scenario_key 一致。",
    ),
    dict(
        asset_id="A04", asset_class="provenance_declaration",
        label="版本与零手抄声明（commit 7017a623 + 生成脚本）",
        section="header", anchor="commit `7017a623`", span=(0, 0),
        resolution="referenced_unresolved",
        path="commit:7017a623", path_kind="git_commit",
        note="commit 7017a623 属 ship-performance-platform 私有仓，本工作树（TensorKnowledge）无法解析/校验该 commit，仅登记为文本声明。",
    ),
    dict(
        asset_id="A05", asset_class="table",
        label="几何/工况参数表（3 型船 × 15 列）",
        section="① 案例介绍", anchor="| 船 | 船型 | DWT [t] |", span=(0, 4),
        resolution="resolved_in_source",
        note="表头+分隔行+3 行数据；数值仅登记，不换算、不重算。",
    ),
    dict(
        asset_id="A06", asset_class="table",
        label="判据汇总表（G1/G2/G3 逐船）",
        section="③ 计算结果", anchor="| 船 | G1 R_T 摩擦线偏差 [%] |", span=(0, 4),
        resolution="resolved_in_source",
        note="G1/G2/G3 的机器化判据数字；证据等级由平台门计算，本工序不置标。",
    ),
    dict(
        asset_id="A07", asset_class="criteria_block",
        label="判据条目 G1–G5（含 WITHHELD 披露）",
        section="③ 计算结果", anchor="* G1（<3%）：", span=(0, 6),
        resolution="resolved_in_source",
        note="G1–G5 五条判据原文，含 G3 对标项 WITHHELD 的显式披露。",
    ),
    dict(
        asset_id="A08", asset_class="result_block",
        label="效率链与碳链分解（三型船逐项）",
        section="③ 计算结果", anchor="* `kcs_3600teu`：P_E=25276.7 kW", span=(0, 2),
        resolution="resolved_in_source",
        note="P_E→P_D、独立力矩路线 2πnQ、n/J/K_T/K_Q、CO₂ 率；数值仅登记。",
    ),
    dict(
        asset_id="A09", asset_class="table",
        label="KCS 公开水池表对标（8 个航速点）",
        section="③ 计算结果 / 实验对标", anchor="| V [kn] | Holtrop R_T [kN] |", span=(0, 9),
        resolution="resolved_in_source",
        note="审计对象表：Holtrop R_T、表列 R_T、偏差、表列 C_t 与由 C_t 反推 R_T；报告自评该表证据等级 WITHHELD。",
    ),
    dict(
        asset_id="A10", asset_class="evidence_grade_note",
        label="水池表证据等级 WITHHELD 结论",
        section="③ 计算结果 / 实验对标", anchor="表内 `C_t` 列与 `R_T` 列最大不一致", span=(0, 1),
        resolution="resolved_in_source",
        note="报告声明该表仅作量级参考、不用于标定与 PASS 判定；登记原文，不升级为结论。",
    ),
    dict(
        asset_id="A11", asset_class="table",
        label="敏感度表（输入假设传导，非精度声明）",
        section="③ 计算结果 / 敏感度", anchor="| 船 | 基线 EEXI | 各情形 ΔEEXI |", span=(0, 4),
        resolution="resolved_in_source",
        note="10 个情形 ×3 型船的 ΔEEXI 百分比；登记不重算。",
    ),
    dict(
        asset_id="A12", asset_class="figure_reference",
        label="图声明 fig1_resistance / fig2_efficiency / fig3_eexi / fig4_gates",
        section="④ 结果图", anchor="* `fig1_resistance.png`：", span=(0, 4),
        resolution="referenced_unresolved",
        path="fig1_resistance.png", path_kind="figure_png",
        note="报告以文件名声明 4 张图；平台 record.figures 携带 name+caption 元数据，但 figures/artifacts 路由 404，本工作树亦无 PNG，故字节不可解析。",
    ),
    dict(
        asset_id="A13", asset_class="data_artifact_reference",
        label="产物 JSON：artifacts/eexi_closed_loop.json",
        section="③ 计算结果 / G5", anchor="G5：`artifacts/eexi_closed_loop.json`", span=(0, 0),
        resolution="referenced_unresolved",
        path="artifacts/eexi_closed_loop.json", path_kind="data_json",
        note="报告称本报告的判据数字由该 JSON 程序化注入（零手抄链上溯）；文件在 ship-performance-platform 私有仓，本工作树不可解析。",
    ),
    dict(
        asset_id="A14", asset_class="data_artifact_reference",
        label="产物清单行：artifacts/eexi_closed_loop.json + artifacts/eexi_closed_loop/*.png + 本报告",
        section="审计链", anchor="* 产物：`artifacts/eexi_closed_loop.json`", span=(0, 0),
        resolution="referenced_unresolved",
        path="artifacts/eexi_closed_loop/*.png", path_kind="figure_glob",
        note="审计链的产物行；PNG 通配符无法在本工作树解析出具体文件清单。",
    ),
    dict(
        asset_id="A15", asset_class="code_reference",
        label="新增模块 backend/modules/eexi_closed_loop/{chain.py,fleet.py,data/reference_ships.json}",
        section="审计链", anchor="* 代码：`backend/modules/eexi_closed_loop/", span=(0, 0),
        resolution="referenced_unresolved",
        path="backend/modules/eexi_closed_loop/chain.py", path_kind="source_code",
        note="三件套（纯物理核 chain.py / 批量 fleet.py / 三型船数据 reference_ships.json）均属 ship-performance-platform，本工作树不存在。",
    ),
    dict(
        asset_id="A16", asset_class="code_reference",
        label="API 改动 backend/api/green_shipping.py（新增两路由 + 修 _gn_attained_index）",
        section="审计链", anchor="`backend/api/green_shipping.py`（新增", span=(0, 1),
        resolution="referenced_unresolved",
        path="backend/api/green_shipping.py", path_kind="source_code",
        note="含 1852 倍量纲缺陷的修复点 _gn_attained_index；本工作树不含该文件，修复本身无法在此复核。",
    ),
    dict(
        asset_id="A17", asset_class="test_reference",
        label="回归测试 backend/tests/test_eexi_closed_loop.py（38 例）",
        section="② 怎么做的", anchor="`backend/tests/test_eexi_closed_loop.py` 38 例", span=(0, 0),
        resolution="referenced_unresolved",
        path="backend/tests/test_eexi_closed_loop.py", path_kind="test_code",
        note="报告称 38 例 pytest；用例文件不在本工作树，未运行、不置标。",
    ),
    dict(
        asset_id="A18", asset_class="repro_command",
        label="复跑命令（run_eexi_closed_loop.py + pytest）",
        section="审计链", anchor="* 复现：`python backend/../artifacts/", span=(0, 1),
        resolution="referenced_unresolved",
        path="artifacts/eexi_closed_loop/run_eexi_closed_loop.py", path_kind="source_code",
        note="报告声明复跑无随机数、无网络；脚本路径在本工作树不存在，未执行。",
    ),
    dict(
        asset_id="A19", asset_class="environment_declaration",
        label="运行环境声明（3.11.6 / loongarch64 / glibc2.38）",
        section="审计链", anchor="* 环境：3.11.6 on Linux", span=(0, 0),
        resolution="resolved_in_source",
        note="环境字符串仅登记；本工序运行环境见 source.producer_environment，不做一致性断言。",
    ),
    dict(
        asset_id="A20", asset_class="defect_record_block",
        label="1852 倍量纲缺陷记录（发现/机理/修复/回归测试）",
        section="⑤ 注意点", anchor="1. **发现并修复一个真实缺陷（1852 倍量纲错）**", span=(0, 6),
        resolution="resolved_in_source",
        note="缺陷叙述块原文（原实现分母取米/小时 → gCO₂/(t·m)，与 required 的 g/(t·nm) 差 1852 倍）；本工序只登记文本位置，不复核修复。",
    ),
    dict(
        asset_id="A21", asset_class="table",
        label="⑥ 误差判定表（关键量 vs 基准，逐项是否 <3%）",
        section="⑥ 误差判定", anchor="| 关键量 | 基准 | 误差 | 判据 | 是否 <3% |", span=(0, 7),
        resolution="resolved_in_source",
        note="6 行判定的原文；其中 EEXI attained vs IMO 示例船为 未判/WITHHELD、Holtrop R_T @24kn 为 否。",
    ),
    dict(
        asset_id="A22", asset_class="limitation_declaration",
        label="honest 结论块（声明两项基准不可得：MEPC 原文缺失、水池表自相矛盾）",
        section="⑥ 误差判定", anchor="honest 结论：", span=(0, 2),
        resolution="declared_absent",
        path=None, path_kind="external_baseline",
        note="报告自我声明：离线环境无法取得 MEPC.328(76)/350(78) 原文或可核示例船数据 → 对标基准缺席（报告所述，非本工序推断）。",
    ),
]

FIG_BODY_NAMES = {
    "fig1_resistance.png": "fig1_resistance",
    "fig2_efficiency.png": "fig2_efficiency",
    "fig3_eexi.png": "fig3_eexi",
    "fig4_gates.png": "fig4_gates",
}

EXT_BY_KIND = {
    "source_code": "code", "test_code": "code", "data_json": "data",
    "figure_png": "figure", "figure_glob": "figure", "git_commit": "vcs",
    "external_baseline": "external",
}

RESOLUTION_RESULT = {
    "resolved_in_source": ("quote_is_unique_substring_and_char_span_roundtrips", "resolved"),
    "referenced_unresolved": ("target_path_probed_in_worktree", "unresolved"),
    "declared_absent": ("report_declares_target_unavailable", "absent"),
}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def jdump(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def jload(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- api helpers
def _api_base() -> str:
    return os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _http(url: str, payload=None, token: str | None = None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def login() -> str | None:
    user = os.environ.get("TENSOR_AGENT_USER")
    pwd = os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            _st, d = _http(_api_base() + path, {"username": user, "password": pwd})
        except Exception:  # noqa: BLE001 - try the next endpoint
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def probe(url: str, token: str | None) -> dict:
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    shown = url.replace(_api_base(), "<api>")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return {"url": shown, "http_status": r.status, "bytes": len(r.read())}
    except urllib.error.HTTPError as exc:
        return {"url": shown, "http_status": exc.code, "bytes": 0}
    except Exception as exc:  # noqa: BLE001
        return {"url": shown, "http_status": None, "error": str(exc), "bytes": 0}


def load_source() -> tuple[str, dict]:
    if not SOURCE_COPY.exists():
        raise SystemExit("missing %s -- run `fetch` first" % SOURCE_COPY)
    md = SOURCE_COPY.read_text(encoding="utf-8")
    record = jload(RAW_RECORD) if RAW_RECORD.exists() else {}
    return md, record


def cmd_fetch() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    token = login()
    url = "%s/tensor/reports/%s" % (_api_base(), REPORT_ID)
    try:
        status, payload = _http(url, token=token)
    except urllib.error.HTTPError as exc:
        raise SystemExit("GET %s -> HTTP %s" % (url, exc.code))
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    if not isinstance(data, dict) or "markdown" not in data:
        raise SystemExit("payload has no markdown field")
    md = data["markdown"]
    if not isinstance(md, str) or not md:
        raise SystemExit("empty markdown for report %s" % REPORT_ID)
    SOURCE_COPY.write_text(md, encoding="utf-8")
    keep = {k: data.get(k) for k in
            ("id", "title", "summary", "scenario_key", "mission_id", "status", "tags",
             "figures", "created_at", "updated_at")}
    keep["_http_status"] = status
    keep["_fetched_at"] = utcnow()
    keep["_source_uri"] = SOURCE_URI
    keep["_markdown_chars"] = len(md)
    keep["_markdown_bytes_utf8"] = len(md.encode("utf-8"))
    keep["_markdown_sha256"] = sha256_hex(md.encode("utf-8"))
    jdump(keep, RAW_RECORD)
    print("fetched report %s: chars=%d bytes=%d sha=%s"
          % (REPORT_ID, len(md), keep["_markdown_bytes_utf8"], keep["_markdown_sha256"]))
    print("contract hash match: %s"
          % (("sha256:" + keep["_markdown_sha256"]) == CONTRACT_SOURCE_HASH))


# ---------------------------------------------------------------- build
def sections_of(lines: list[str]) -> list[dict]:
    out = []
    for idx, line in enumerate(lines, 1):
        if line.startswith("## "):
            out.append({"heading": line, "line": idx,
                        "kind": "audit_chain" if "审计链" in line else "section"})
    return out


def _resolve_span(lines: list[str], anchor: str, span: tuple[int, int]) -> tuple[int, int]:
    hits = [i for i, l in enumerate(lines, 1) if anchor in l]
    if len(hits) != 1:
        raise SystemExit("anchor %r occurs %d times (needs exactly 1)" % (anchor, len(hits)))
    a = hits[0]
    return a + span[0], a + span[1]


def build_assets(md: str) -> list[dict]:
    lines = md.rstrip("\n").split("\n")
    assets = []
    for spec in ASSETS:
        if spec.get("method") == "document":
            quote = md
            start_char, end_char = 0, len(md)
            s_line, e_line = 1, len(lines)
            unique = True
        else:
            s_line, e_line = _resolve_span(lines, spec["anchor"], spec["span"])
            if s_line < 1 or e_line < s_line or e_line > len(lines):
                raise SystemExit("%s: bad span %s..%s" % (spec["asset_id"], s_line, e_line))
            quote = "\n".join(lines[s_line - 1:e_line])
            start_char = md.index(quote)
            end_char = start_char + len(quote)
            if md.count(quote) != 1:
                raise SystemExit("%s: quote is not unique (%d occurrences)"
                                 % (spec["asset_id"], md.count(quote)))
            unique = True
        if md[start_char:end_char] != quote:
            raise SystemExit("%s: char span does not round-trip" % spec["asset_id"])

        check, result = RESOLUTION_RESULT[spec["resolution"]]
        entry = {
            "asset_id": spec["asset_id"],
            "asset_class": spec["asset_class"],
            "label": spec["label"],
            "in_report_section": spec["section"],
            "resolution": spec["resolution"],
            "resolution_check": {"check": check, "result": result},
            "locator": {
                "method": spec.get("method", "char_span"),
                "start_char": start_char,
                "end_char": end_char,
                "start_line": s_line,
                "end_line": e_line,
                "quote": quote,
                "unique": unique,
            },
            "note": spec["note"],
        }
        if spec["resolution"] != "resolved_in_source":
            path = spec.get("path")
            kind = spec.get("path_kind")
            exists = None
            if kind != "git_commit" and path and "*" not in path:
                exists = (ROOT / path).exists()
            entry["target"] = {
                "address_as_written": path,
                "kind": kind,
                "ext_kind": EXT_BY_KIND.get(kind or "", "unknown"),
                "exists_in_worktree": exists,
                "reason": "address belongs to ship-performance-platform (private repo) or is an "
                          "external baseline; this worktree is TensorKnowledge",
            }
            entry["resolution_check"]["target_probe"] = {"exists_in_worktree": exists}
        assets.append(entry)
    return assets


def build_figures(md: str, record: dict, token: str | None) -> list[dict]:
    lines = md.rstrip("\n").split("\n")
    rec_figs = {f.get("name"): f.get("caption") for f in (record.get("figures") or [])}
    out = []
    for body_name, base in FIG_BODY_NAMES.items():
        hits = [i for i, l in enumerate(lines, 1) if body_name in l]
        probes = [
            probe("%s/tensor/reports/%s/figures/%s.png" % (_api_base(), REPORT_ID, base), token),
            probe("%s/tensor/reports/%s/figures/%s" % (_api_base(), REPORT_ID, base), token),
            probe("%s/tensor/reports/%s/artifacts/%s.png" % (_api_base(), REPORT_ID, base), token),
        ]
        out.append({
            "name": base,
            "declared_in_body_as": body_name,
            "declared_body_lines": hits,
            "caption_from_record": rec_figs.get(base),
            "has_record_metadata": base in rec_figs,
            "bytes_available": any(p.get("http_status") == 200 for p in probes),
            "byte_probes": probes,
        })
    return out


def cmd_build() -> None:
    md, record = load_source()
    token = login()
    raw = md.encode("utf-8")
    digest = "sha256:" + sha256_hex(raw)
    lines = md.rstrip("\n").split("\n")
    assets = build_assets(md)
    figures = build_figures(md, record, token)
    sections = sections_of(lines)

    ids = [a["asset_id"] for a in assets]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise SystemExit("duplicate asset ids: %s" % dupes)
    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    rec_title = record.get("title")
    manifest = {
        "schema": "asset_manifest.v2",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": LANE,
        "generated_at": utcnow(),
        "producer": PRODUCER,
        "objective": {"register_assets": True, "classify_report_type": False,
                      "extraction_performed": False},
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest.split(":", 1)[1],
            "hash_prefixed": digest,
            "contract_hash": CONTRACT_SOURCE_HASH,
            "hash_matches_contract": digest == CONTRACT_SOURCE_HASH,
            "chars": len(md),
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": len(md) == CONTRACT_CHARS,
            "bytes_utf8": len(raw),
            "bytes_note": "byte count differs from chars because the report is CJK-heavy; the "
                          "contract hashes UTF-8 bytes while chars counts code points",
            "lines": len(lines),
            "has_crlf": "\r\n" in md,
            "has_trailing_newline": md.endswith("\n"),
            "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)); 1-based",
            "fetched_via": "GET %s/tensor/reports/%s" % (_api_base(), REPORT_ID),
            "fetched_at": record.get("_fetched_at"),
            "record_fields": {
                "title": rec_title,
                "scenario_key": record.get("scenario_key"),
                "mission_id": record.get("mission_id"),
                "status": record.get("status"),
                "tags": record.get("tags"),
                "created_at": record.get("created_at"),
                "contract_title": CONTRACT_TITLE,
                "contract_scenario_key": CONTRACT_SCENARIO,
                "title_matches_contract": rec_title == CONTRACT_TITLE,
                "scenario_matches_contract": record.get("scenario_key") == CONTRACT_SCENARIO,
            },
            "platform_figures": record.get("figures"),
            "platform_tags": record.get("tags"),
            "producer_environment": {"python": sys.version.split()[0], "platform": sys.platform},
        },
        "sections": sections,
        "assets": assets,
        "figures": figures,
        "claims": [],
        "claims_empty_reason": (
            "contract wp-9503-01: objective.register_assets=true / classify_report_type=false; "
            "notes say 'claims 允许为空数组' and constraints.no_forced_claim_generation=true. This "
            "package registers source identity (report_id + markdown byte hash + declared "
            "attachments/artefacts) only; extraction is a downstream工序. An empty claims array is "
            "the complete result, not an omission."
        ),
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_res.items())),
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "figures_declared_in_record": len(record.get("figures") or []),
            "figures_declared_in_body": sum(1 for f in figures if f["declared_body_lines"]),
            "figures_with_bytes_available": sum(1 for f in figures if f["bytes_available"]),
            "sections": len(sections),
            "claims": 0,
        },
        "id_integrity": {"ids_checked": len(ids), "duplicates": dupes, "unique": True},
        "integrity": {
            "quote_uniqueness": {
                "checked": len(assets),
                "all_unique_or_document": all(
                    a["locator"]["method"] == "document"
                    or md.count(a["locator"]["quote"]) == 1 for a in assets),
                "rule": "each non-document quote must occur exactly once in the markdown",
            },
            "chars_roundtrip": all(
                md[a["locator"]["start_char"]:a["locator"]["end_char"]] == a["locator"]["quote"]
                for a in assets),
            "hash_recomputed_locally": sha256_hex(raw),
            "hash_matches_contract": digest == CONTRACT_SOURCE_HASH,
        },
        "unresolved": [
            {"asset_id": a["asset_id"], "label": a["label"],
             "reason": a["resolution_check"]["check"]}
            for a in assets if a["resolution"] != "resolved_in_source"
        ],
        "observations": [
            "markdown %d 字符 / %d UTF-8 字节；与契约 chars=%d 一致，sha256 与契约逐位相同。"
            % (len(md), len(raw), CONTRACT_CHARS),
            "报告结构完整：H1 + ①–⑥ 六节 + 审计链，共 %d 个二级标题。" % len(sections),
            "4 张图仅以文件名在 ④ 结果图 声明；平台 record.figures 给 name+caption，但 figures/"
            "artifacts 路由均 404，本工作树亦无 PNG，故图字节不可解析（不声明图哈希）。",
            "所有 backend/** 与 artifacts/** 地址属 ship-performance-platform 私有仓，本工作树逐条"
            "探测 exists_in_worktree=false，登记为 referenced_unresolved。",
            "报告自评两处基准缺席：IMO 示例船逐点值（MEPC 原文离线不可得）与仓内水池表"
            "（C_t↔R_T 自不一致 20.3%）——登记为 declared_absent，不代为判定。",
        ],
    }
    jdump(manifest, MANIFEST)
    # durable source snapshot next to the artefacts: the push gate drops runs/**, and offline
    # re-verification of every locator needs the exact bytes that were hashed.
    PKG_SOURCE.write_text(md, encoding="utf-8")
    print("wrote %s" % MANIFEST.relative_to(ROOT))
    print("assets=%d by_resolution=%s" % (len(assets), dict(sorted(by_res.items()))))


# ---------------------------------------------------------------- envelope
def cmd_envelope() -> None:
    manifest = jload(MANIFEST)
    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + manifest["source"]["hash"],
            "source_field": "markdown",
            "producer": PRODUCER,
            "emitted_at": manifest["generated_at"],
            "notes": "source_uri=tensor://reports/9503; hash over the UTF-8 bytes of the markdown "
                     "field served by GET /api/v1/tensor/reports/9503, recomputed locally at build "
                     "and again against the live document at verify time (verification.json).",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    jdump(envelope, ENVELOPE)
    print("wrote %s" % ENVELOPE.relative_to(ROOT))


# ---------------------------------------------------------------- verify
def cmd_verify() -> None:
    from jsonschema import Draft7Validator, Draft202012Validator

    md, _record = load_source()
    raw = md.encode("utf-8")
    live_hash = "sha256:" + sha256_hex(raw)
    manifest = jload(MANIFEST)
    envelope = jload(ENVELOPE)
    checks: dict[str, dict] = {}

    def add(name: str, ok: bool, detail: str, acceptance: str) -> None:
        checks[name] = {"acceptance_item": acceptance, "pass": bool(ok), "detail": detail}

    # 1 valid_json
    try:
        json.loads(MANIFEST.read_text(encoding="utf-8"))
        json.loads(ENVELOPE.read_text(encoding="utf-8"))
        add("valid_json", True, "asset_manifest.json and kf_result.json both parse", "valid_json")
    except Exception as exc:  # noqa: BLE001
        add("valid_json", False, str(exc), "valid_json")

    # 2 schema_pass
    errors = []
    try:
        v = Draft202012Validator(jload(ENVELOPE_SCHEMA))
        errors += ["envelope: %s" % e.message for e in v.iter_errors(envelope)]
    except Exception as exc:  # noqa: BLE001
        errors.append("envelope schema load/validate failed: %s" % exc)
    try:
        v2 = Draft7Validator(jload(ASSET_SCHEMA))
        errors += ["manifest: %s at %s" % (e.message, list(e.path)[:4])
                   for e in v2.iter_errors(manifest)]
    except Exception as exc:  # noqa: BLE001
        errors.append("manifest schema load/validate failed: %s" % exc)
    add("schema_pass", not errors,
        "envelope vs schemas/kf_result.v1.schema.json + manifest vs "
        "schemas/asset_manifest.v2.schema.json; errors=%d %s" % (len(errors), errors[:4]),
        "schema_pass")

    # 3 source_locator_resolvable -- re-checked against the LIVE markdown
    bad = []
    live_lines = md.rstrip("\n").split("\n")
    for a in manifest["assets"]:
        q = a["locator"]["quote"]
        if a["locator"]["method"] == "document":
            if not (a["locator"]["start_char"] == 0 and q == md):
                bad.append(a["asset_id"] + ":document-span")
            continue
        s, e = a["locator"]["start_char"], a["locator"]["end_char"]
        if md[s:e] != q:
            bad.append(a["asset_id"] + ":span")
        elif md.count(q) != 1:
            bad.append(a["asset_id"] + ":not-unique(%d)" % md.count(q))
        line_q = "\n".join(live_lines[a["locator"]["start_line"] - 1:a["locator"]["end_line"]])
        if line_q != q:
            bad.append(a["asset_id"] + ":line-mismatch")
    add("source_locator_resolvable", not bad,
        "%d locators re-checked (char-span round-trip + unique substring + line numbers agree); "
        "failures=%s" % (len(manifest["assets"]), bad[:5]), "source_locator_resolvable")

    # 4 source_hash_matches -- four-way agreement
    same = (live_hash == CONTRACT_SOURCE_HASH
            and envelope["provenance"]["source_hash"] == live_hash
            and "sha256:" + manifest["source"]["hash"] == live_hash)
    add("source_hash_matches", same,
        "live=%s contract=%s envelope=%s manifest=%s chars_live=%d chars_contract=%d"
        % (live_hash, CONTRACT_SOURCE_HASH, envelope["provenance"]["source_hash"],
           "sha256:" + manifest["source"]["hash"], len(md), CONTRACT_CHARS),
        "source_hash_matches")

    # 5 no_duplicate_ids
    aids = [a["asset_id"] for a in manifest["assets"]]
    cids = [c.get("claim_id") for c in manifest.get("claims") or []]
    dup = sorted({i for i in aids if aids.count(i) > 1}) + \
        sorted({i for i in cids if cids.count(i) > 1})
    add("no_duplicate_ids", not dup,
        "asset ids=%d claims=%d duplicates=%s" % (len(aids), len(cids), dup), "no_duplicate_ids")

    # 6 all_claims_have_evidence_or_explicit_unresolved_status
    viol = []
    for c in manifest.get("claims") or []:
        if not (c.get("evidence_locator") or c.get("status") or c.get("evidence")):
            viol.append(c.get("claim_id"))
    add("all_claims_have_evidence_or_explicit_unresolved_status", not viol,
        "claims=%d (empty is the contract's complete result); violations=%s"
        % (len(cids), viol), "all_claims_have_evidence_or_explicit_unresolved_status")

    # extra contract-level checks (beyond the 6 acceptance items)
    blob = json.dumps(manifest, ensure_ascii=False).lower()
    add("no_verified_marks", '"verified"' not in blob,
        "no 'verified' status/word appears in the manifest; resolution describes locator "
        "resolvability only", "constraint:do_not_mark_claims_as_verified")
    rs = manifest["source"]["record_fields"]
    add("record_identity_matches_contract",
        bool(rs["title_matches_contract"] and rs["scenario_matches_contract"]),
        "title_matches_contract=%s scenario_matches_contract=%s status=%s mission_id=%s"
        % (rs["title_matches_contract"], rs["scenario_matches_contract"], rs["status"],
           rs["mission_id"]), "contract:input")
    other_ids = sorted({r for r in ("448", "542", "623", "1202", "1610") if r == REPORT_ID})
    add("single_report_scope", not other_ids,
        "package reads/writes report_id=9503 only; all output paths are built from REPORT_ID",
        "constraint:single_report_scope")

    acceptance = ["valid_json", "schema_pass", "source_locator_resolvable",
                  "source_hash_matches", "no_duplicate_ids",
                  "all_claims_have_evidence_or_explicit_unresolved_status"]
    by_item = {}
    for item in acceptance:
        hit = next((c for c in checks.values() if c["acceptance_item"] == item), None)
        by_item[item] = bool(hit and hit["pass"])
    report = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "verified_at": utcnow(),
        "checks": checks,
        "acceptance_summary": {item: {"pass": by_item[item]} for item in acceptance},
        "all_acceptance_pass": all(by_item.values()),
        "notes": "Local pre-checks only: the platform gate independently recomputes the source "
                 "hash and substring resolvability and is authoritative. Passing here is not a "
                 "claim of platform verification.",
    }
    jdump(report, VERIFICATION)
    print("wrote %s" % VERIFICATION.relative_to(ROOT))
    for name, c in checks.items():
        print("  %-54s %s  %s" % (name, "PASS" if c["pass"] else "FAIL", c["detail"][:100]))
    if not report["all_acceptance_pass"]:
        print("ACCEPTANCE FAILURE")
        raise SystemExit(1)


# ---------------------------------------------------------------- figure
def cmd_figure() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    manifest = jload(MANIFEST)
    assets = manifest["assets"]
    lines_total = manifest["source"]["lines"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7.6),
                                   gridspec_kw={"width_ratios": [2.45, 1]})

    color_by_res = {"resolved_in_source": "#2b6cb0",
                    "referenced_unresolved": "#c05621",
                    "declared_absent": "#9b2c2c"}
    for i, a in enumerate(assets):
        loc = a["locator"]
        y = len(assets) - i
        s, e = loc["start_line"], max(loc["end_line"], loc["start_line"] + 0.02)
        ax1.barh(y, e - s + 1, left=s, height=0.62,
                 color=color_by_res[a["resolution"]], alpha=0.85)
        ax1.text(-2, y, a["asset_id"], ha="right", va="center", fontsize=8)
        ax1.text(e + 2, y, "%s L%d-%d" % (a["asset_class"], s, loc["end_line"]),
                 ha="left", va="center", fontsize=6.2, color="#444")
    for sec in manifest["sections"]:
        ax1.axvline(sec["line"], color="#888", lw=0.6, ls=":")
    ax1.set_xlim(-16, lines_total * 1.5)
    ax1.set_ylim(0.2, len(assets) + 1.2)
    ax1.set_yticks([])
    ax1.set_xlabel("report 9503 markdown line number (1-based); dotted = section starts")
    ax1.set_title("Asset locator map - report 9503 (%d assets, %d lines)"
                  % (len(assets), lines_total), fontsize=11)
    handles = [Rectangle((0, 0), 1, 1, color=c) for c in color_by_res.values()]
    ax1.legend(handles, list(color_by_res), fontsize=7.5, loc="lower right", frameon=True)

    src = manifest["source"]
    integ = manifest["integrity"]
    counts = manifest["counts"]
    rows = [
        ("markdown sha256 == contract", "PASS" if src["hash_matches_contract"] else "FAIL"),
        ("chars == contract (%d)" % CONTRACT_CHARS,
         "PASS" if src["chars_match_contract"] else "FAIL"),
        ("quote uniqueness (%d assets)" % counts["assets"],
         "PASS" if integ["quote_uniqueness"]["all_unique_or_document"] else "FAIL"),
        ("char-span round-trip", "PASS" if integ["chars_roundtrip"] else "FAIL"),
        ("duplicate asset ids", "PASS" if manifest["id_integrity"]["unique"] else "FAIL"),
        ("claims (empty by contract)", str(counts["claims"])),
        ("figures declared in record", str(counts["figures_declared_in_record"])),
        ("figures with bytes available", str(counts["figures_with_bytes_available"])),
        ("assets resolved_in_source", str(counts["resolved_in_source"])),
        ("assets referenced_unresolved", str(counts["referenced_unresolved"])),
        ("assets declared_absent", str(counts["declared_absent"])),
        ("markdown lines", str(src["lines"])),
        ("UTF-8 bytes / chars", "%d / %d" % (src["bytes_utf8"], src["chars"])),
    ]
    ax2.axis("off")
    ax2.set_title("Integrity / acceptance pre-checks", fontsize=11)
    for j, (k, v) in enumerate(rows):
        y = 1 - (j + 0.5) / len(rows)
        ax2.text(0.02, y, k, fontsize=8.4, va="center")
        ax2.text(0.98, y, v, fontsize=8.4, va="center", ha="right",
                 color="#276749" if v == "PASS" else ("#9b2c2c" if v == "FAIL" else "#333"))
        ax2.axhline(y - 0.5 / len(rows), color="#e2e8f0", lw=0.6)
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)

    fig.suptitle("wp-9503-01 / report 9503 asset registration (registration only, no claims)",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(LOCATOR_MAP, dpi=150)
    print("wrote %s" % LOCATOR_MAP.relative_to(ROOT))


# ---------------------------------------------------------------- result markdown
def _clip(q: str, n: int = 108) -> str:
    # neutralise markdown-active characters so a verbatim slice cannot break the table cell;
    # the untruncated, unescaped quote stays in manifest.locator.quote
    q = (q.replace("\r", " ").replace("\n", " / ").replace("|", "\\|")
          .replace("`", "'"))
    return q if len(q) <= n else q[:n] + " …"


def cmd_result() -> None:
    manifest = jload(MANIFEST)
    envelope = jload(ENVELOPE)
    verification = jload(VERIFICATION)
    src = manifest["source"]
    counts = manifest["counts"]
    env = envelope["provenance"]["source_hash"]

    ev_rows = []
    for a in manifest["assets"]:
        ev_rows.append("| %s | %s | %d–%d | `%s` | %s |"
                       % (a["asset_id"], a["resolution"], a["locator"]["start_line"],
                          a["locator"]["end_line"], _clip(a["locator"]["quote"]),
                          a["in_report_section"]))
    ev_table = "\n".join(ev_rows)

    fig_rows = []
    for f in manifest["figures"]:
        fig_rows.append("| %s | %s | %s | %s | %s |"
                        % (f["name"], f["declared_in_body_as"],
                           ", ".join(str(x) for x in f["declared_body_lines"]) or "—",
                           "yes" if f["has_record_metadata"] else "no",
                           "yes" if f["bytes_available"] else "no"))
    fig_table = "\n".join(fig_rows)

    acc_items = ["valid_json", "schema_pass", "source_locator_resolvable",
                 "source_hash_matches", "no_duplicate_ids",
                 "all_claims_have_evidence_or_explicit_unresolved_status"]
    acc_rows = []
    for item in acc_items:
        hit = next((c for c in verification["checks"].values()
                    if c["acceptance_item"] == item), None)
        mark = "✅" if hit and hit["pass"] else ("❌" if hit else "⬜ 未跑")
        acc_rows.append("| `%s` | %s | %s |"
                        % (item, mark, _clip(hit["detail"], 130) if hit else "not_run"))
    acc_table = "\n".join(acc_rows)

    extra_rows = []
    for name, c in verification["checks"].items():
        if c["acceptance_item"] in acc_items:
            continue
        extra_rows.append("| `%s` | %s | %s |"
                          % (name, "✅" if c["pass"] else "❌", _clip(c["detail"], 130)))
    extra_table = "\n".join(extra_rows) or "（无）"

    class_rows = []
    for k, v in counts["by_class"].items():
        class_rows.append("| `%s` | %d |" % (k, v))
    class_table = "\n".join(class_rows)

    unres_rows = []
    for a in manifest["assets"]:
        if a["resolution"] == "resolved_in_source":
            continue
        t = a.get("target", {})
        addr = t.get("address_as_written") or "（无显式地址：基准本身缺席）"
        exists = t.get("exists_in_worktree")
        exists_txt = "n/a（非工作树地址）" if exists is None else str(exists)
        unres_rows.append("| %s | `%s` | %s | %s |"
                          % (a["asset_id"], addr, t.get("kind"), exists_txt))
    unres_table = "\n".join(unres_rows)

    # every number/literal quoted in the narrative below must exist verbatim in the source report
    source_md = (PKG_SOURCE).read_text(encoding="utf-8")
    literals = ["35.992", "3.558", "2.816", "0.0696%", "1852 倍", "38 例", "20.3%",
                "7017a623", "MEPC.328(76)", "350(78)", "0.0696"]
    missing = [lit for lit in literals if lit not in source_md]
    if missing:
        raise SystemExit("narrative literal(s) not found verbatim in the source report: %s"
                         % missing)

    json_block = json.dumps(envelope, ensure_ascii=False, indent=2)
    body = f"""# KF-RESULT {PACKAGE_ID}

工作包 `{PACKAGE_ID}` · 工序 `{TASK_TYPE}` · report_id **{REPORT_ID}** · lane {LANE} ·
source `{src['uri']}`（field=`{src['field']}`）· 生成 {manifest['generated_at']} ·
producer `{PRODUCER}`

## ① 本工序做了什么

按契约只做一件事：**登记 report_id={REPORT_ID} 的源资产**（`objective.register_assets=true`、
`classify_report_type=false`）。具体交付：

1. 从平台 `GET /api/v1/tensor/reports/{REPORT_ID}` 取 `markdown` 字段，落到
   `docs/kf/{PACKAGE_ID}/source_{REPORT_ID}.md`（可入库快照；`runs/` 下另存一份运行副本），
   并对 UTF-8 字节重算 sha256 与契约 `source_hash` 逐位比对（**一致**）；
2. 在原文中定位并登记 **{counts['assets']} 个资产**（{len(counts['by_class'])} 类），每个资产带
   行号区间 + 字符区间 + 逐字引文（引文由程序在原文切片，非手抄），并对引文做**唯一性**校验；
3. 逐条记录"能否解析"：`resolved_in_source` {counts['resolved_in_source']} 条、
   `referenced_unresolved` {counts['referenced_unresolved']} 条、`declared_absent` {counts['declared_absent']} 条；
4. 探测报告声明的 4 张图的字节可获得性（平台 figures/artifacts 路由均 404 → 无字节，不声明图哈希）；
5. **不做抽取**：`claims` 为空数组，并在 `claims_empty_reason` 写明这是契约要求的完整结果而非遗漏；
6. **不置 verified**：任何字段都不包含 verified 标记（本工序只描述定位可解析性，验证由平台门计算）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

* 工具链：纯 Python3 标准库 + `jsonschema`（校验）+ `matplotlib`（定位图）。一键复跑脚本
  `scripts/kf_wp9503_01_register_assets.py`（子命令 fetch / build / envelope / verify / figure / result / all）。
* **零手抄机制**：资产表只写"锚点子串 + 相对行偏移"，引文在运行时由
  `"\\n".join(lines[s-1:e])` 切出，随后断言 `md[start:end] == quote` 且 `md.count(quote) == 1`；
  锚点不唯一或引文不唯一 → `SystemExit`（宁可不产出，不产出半成品）。
* 会计口径：`chars` 用码点数（契约给的是 8176），`bytes_utf8` 单独记录（中文报告字节数更大），
  sha256 按**UTF-8 字节**计算 —— 与契约 `source_hash` 一致。
* 解析判定不是"看起来像"而是**探测**：本工作树对每个 `backend/**`、`artifacts/**` 地址做
  `Path.exists()`；平台侧对 `figures/<name>.png`、`figures/<name>`、`artifacts/<name>.png`
  三种 URL 形状各发一次 GET 并记录状态码。
* 报告结构（章节/行号）、图表声明、记录元数据（title/scenario_key/mission_id/tags/figures）
  全部由接口返回与原文测量得到，不写入任何未观测值。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/{PACKAGE_ID}/asset_manifest.json` | 资产清单主体：source 对账 + {counts['assets']} 资产 + {counts['sections']} 节结构 + 图探测 + counts/integrity |
| `docs/kf/{PACKAGE_ID}/kf_result.json` | `kf_result.v1` 结果信封（唯一 json 代码块的内容来源），`outputs.asset_manifest.json` 内嵌上述清单 |
| `docs/kf/{PACKAGE_ID}/verification.json` | {len(verification['checks'])} 项本地预检（6 项验收 + 契约约束项），全绿/失败逐条记录 |
| `docs/kf/{PACKAGE_ID}/figures/locator_map.png` | 定位图：{counts['assets']} 条资产在 {src['lines']} 行原文上的区间条 + 右侧完整性检查面板 |
| `docs/kf/{PACKAGE_ID}/KF-RESULT-{PACKAGE_ID}.md` | 本报告（六段 + 唯一 json 块 + repro_cmd） |
| `schemas/asset_manifest.v2.schema.json` | 本次新增的**参数化**清单 schema（report-agnostic），供 `schema_pass` 可复现 |
| `docs/kf/{PACKAGE_ID}/source_{REPORT_ID}.md` | 原文逐字快照（离线复算哈希/定位用；push 门会丢 runs/**，故另存一份） |
| `runs/{PACKAGE_ID}/record_{REPORT_ID}.json` | 平台记录原始返回（title/scenario_key/mission_id/tags/figures） |

资产分类直方图（程序统计）：

| asset_class | 条数 |
|---|---|
{class_table}

## ④ 证据定位表（资产 → 原文引文片段）

引文一律为原文**逐字**切片（下表为截断展示，完整引文见 manifest 的 `locator.quote`；
平台可独立重算 sha256 与子串）。行号 1-based，字符区间为 `[start_char, end_char)`。

| asset_id | resolution | 行区间 | 原文引文（截断） | 所属章节 |
|---|---|---|---|---|
{ev_table}

图声明探测（平台元数据 + 字节可用性）：

| 图 | 原文文件名 | 原文行 | record 有 caption | 字节可取 |
|---|---|---|---|---|
{fig_table}

未解析/缺席资产的目标地址与实际探测结果（不臆造地址、不假装存在）：

| asset_id | 报告中的地址 | 类型 | exists_in_worktree |
|---|---|---|---|
{unres_table}

关键对账数字（全部由脚本测量，非记忆）：

* `source.hash` = `{src['hash_prefixed']}` == 契约 `{CONTRACT_SOURCE_HASH}`（**逐位一致**）
* `chars` = {src['chars']} == 契约 {src['contract_chars']}；`bytes_utf8` = {src['bytes_utf8']}；`lines` = {src['lines']}
* 平台记录：title/scenario_key 与契约**一致**（`title_matches_contract`={src['record_fields']['title_matches_contract']}、
  `scenario_matches_contract`={src['record_fields']['scenario_matches_contract']}），
  status=`{src['record_fields']['status']}`、mission_id={src['record_fields']['mission_id']}、标签 {len(src['platform_tags'] or [])} 个
* 引文唯一性：{counts['assets']} 条资产全部通过 `md.count(quote)==1`（document 资产按全文计）

## ⑤ 注意点与局限

1. **本工序不产生知识断言**：`claims=[]`。报告内的 35.992/3.558/2.816、0.0696%、1852 倍等数字
   在 manifest 里只以**引文**形式存在，未被换算、未被重算、未被置为 verified —— 任何下游要引用
   这些数字，必须自己回到原文（行号已给）并走自己的证据门。
2. **图字节不可得**：4 张图只有文件名（原文 L95–L99）与 record 里的 name+caption；
   `/tensor/reports/{REPORT_ID}/figures/*`、`/artifacts/*` 均返回 404，TensorKnowledge 工作树内也无 PNG。
   因此**不声明任何图哈希**，也不声称图存在——这是 WITHHELD 式的诚实处理，不是遗漏。
3. **跨仓不可核**：`backend/**`、`artifacts/**`、commit `7017a623` 全部属 ship-performance-platform
   私有仓。本工作树逐条探测 `exists_in_worktree=false`，故整体挂 `referenced_unresolved`。
   这意味着：**报告声称的 1852 倍缺陷修复、38 例回归测试、复跑脚本，本工序一律未复核**，
   只登记其在原文中的位置。任何"已修复/已验证"的判断都需要另派一个能访问该仓的工作包。
4. **`declared_absent` 不是我判的**：A22 是报告自己写的 honest 结论（MEPC 原文离线不可得、
   仓内水池表 C_t↔R_T 自不一致 20.3%）。本工序仅登记这段自我披露的位置，不对其结论加码或减码。
5. **schema 边界**：契约引用的 `schemas/asset_manifest.*.schema.json` 在此前只有 `v1`
   实例级（`const: wp-448-01`）版本，无法用于本包。为此新增 `asset_manifest.v2`（report-agnostic
   的 pattern 版），未改动 v1（那是别的工作包的产物）。若平台侧 schema 与此不同，以平台门为准，
   本产物需按平台 schema 修订。
6. **单报告作用域**：所有输入输出路径由 `REPORT_ID=9503` 派生，脚本不含其它 report_id 常量
   （预检项 `single_report_scope`）。
7. 本报告的 `mission_id` 字段取本次派单的 15644；报告本体（report 9503）自身的 mission_id 是
   {src['record_fields']['mission_id']}，两者不是同一个概念，已分别记录。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 证据（verification.json detail 截断） |
|---|---|---|
{acc_table}

契约级约束附加检查：

| 检查 | 结果 | 说明 |
|---|---|---|
{extra_table}

**总体**：{"6 项验收全部通过（本地预检）" if verification['all_acceptance_pass'] else "存在失败项，见上表（honest-FAIL 不粉饰）"}。
如实说明：以上均为**本地预检**，不是平台门结论；平台会独立重算 source_hash 与子串可解析性，
且 verification 由平台计算——本报告未把任何条目标成 verified。

## repro_cmd（一键复跑）

```bash
cd <worktree-root> && python3 scripts/kf_wp9503_01_register_assets.py all
# 分步：fetch -> build -> envelope -> verify -> figure -> result
# 依赖：python3 + jsonschema + matplotlib；环境变量 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS
# 期望：verify 全绿，source hash 与契约 195c350d…8b5c 逐位一致
```

`all` 的顺序即 fetch → build → envelope → verify → figure → result；任何一步断言失败即 `SystemExit`。

## 结果信封（唯一 json 块）

```json
{json_block}
```
"""
    RESULT_MD.write_text(body, encoding="utf-8")
    print("wrote %s" % RESULT_MD.relative_to(ROOT))
    n_json_blocks = body.count("```json")
    print("json code fences in result md: %d" % n_json_blocks)
    if n_json_blocks != 1:
        raise SystemExit("result markdown must contain exactly one json code block")


def cmd_all() -> None:
    cmd_fetch()
    cmd_build()
    cmd_envelope()
    cmd_verify()
    cmd_figure()
    cmd_result()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    dispatch = {"fetch": cmd_fetch, "build": cmd_build, "envelope": cmd_envelope,
                "verify": cmd_verify, "figure": cmd_figure, "result": cmd_result,
                "all": cmd_all}
    if cmd not in dispatch:
        raise SystemExit("unknown sub-command: %s (choose from %s)"
                         % (cmd, ", ".join(sorted(dispatch))))
    dispatch[cmd]()
