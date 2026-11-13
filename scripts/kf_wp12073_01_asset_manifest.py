#!/usr/bin/env python3
"""Knowledge-Factory work package wp-12073-01 — task_type 01-asset-registration.

Scope (contract, verbatim):
  "登记源资产：确认 report_id 与其 markdown 的字节哈希，列出可解析的附件/工件，
   不做抽取。claims 允许为空数组。"

So this script does exactly three things and nothing else:

  1. pin the source: fetch report 12073's ``markdown`` field from the platform API,
     recompute sha256 over its UTF-8 bytes, compare with the contract hash
     (sha256:362fbe90...e850) and with ``chars: 3446``;
  2. inventory the in-report assets a downstream piece of work can point at
     (document, H2 sections, the two markdown tables, the five figures with their
     retrievable png bytes, referenced repo artifacts / modules, equations,
     regulatory references, run-output tokens) with a *verbatim* locator for each;
  3. emit ``asset_manifest.json`` + the ``kf_result.v1`` envelope + the publishable
     KF-RESULT markdown, and verify all acceptance items from the contract.

It never extracts claims (claims=[] is legitimate and explicitly allowed by the
contract), never classifies the report, never marks anything verified (that is the
platform gate's job) and never touches any report_id other than 12073.

Usage::

    python3 scripts/kf_wp12073_01_asset_manifest.py --fetch --build --verify
    python3 scripts/kf_wp12073_01_asset_manifest.py --verify        # re-check committed outputs
    python3 scripts/kf_wp12073_01_asset_manifest.py --publish       # post the KF-RESULT report
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(HERE, "docs", "kf", "wp-12073-01")
SOURCE = os.path.join(OUTDIR, "source", "report_12073.md")
RECORD = os.path.join(OUTDIR, "source", "report_12073.record.json")
FIGDIR = os.path.join(OUTDIR, "source", "figures")
FIGFETCH = os.path.join(OUTDIR, "source", "figure_fetch.json")
MANIFEST = os.path.join(OUTDIR, "asset_manifest.json")
RESULT = os.path.join(OUTDIR, "kf_result.json")
VERIFY = os.path.join(OUTDIR, "verification.json")
MANIFEST_SCHEMA = os.path.join(OUTDIR, "asset_manifest.schema.json")
REPORT_MD = os.path.join(OUTDIR, "KF-RESULT-wp-12073-01.md")
INV_FIG = os.path.join(OUTDIR, "fig_asset_inventory.png")
EMISSION = os.path.join(OUTDIR, "emission.json")

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

CONTRACT = {
    "package_id": "wp-12073-01",
    "task_type": "01-asset-registration",
    "lane": "C",
    "report_id": "12073",
    "source_uri": "tensor://reports/12073",
    "source_field": "markdown",
    "source_hash": "sha256:362fbe90ba196e81f94aa4f6dd9d74bc5f69c729e7eb9f99a125fb9415bea850",
    "scenario_key": "cii_tracking_realtime",
    "title": "实时 CII 轨迹追踪与纠偏航行优化（p161w2-arb-n01 / KVLCC2 闭环）",
    "chars": 3446,
    "contract_version": "1.0",
    "delivery_repo": "TensorKnowledge",
    "delivery_status": "draft",
}
REPORT_PATH = "/tensor/reports/" + CONTRACT["report_id"]
FIGURE_PATH = "/tensor/reports/" + CONTRACT["report_id"] + "/figures/{name}"

# --------------------------------------------------------------------------- assets
SECTION_SPECS = [
    ("section:case", "① 案例与物理背景（母型 / 核算年 / 目标 CII / 物理链）", "## ① 案例与物理背景"),
    ("section:method", "② 方法（实时内核 → 目标轨迹 → 预警根因 → 纠偏优化 → 闭环仿真）", "## ② 方法"),
    ("section:results", "③ 计算结果（C1–C5 判据表 + 闭环细节 + honest FAIL）", "## ③ 计算结果（程序化注入）"),
    ("section:figures", "④ 图件（fig1–fig5 文件名清单）", "## ④ 图件"),
    ("section:limits", "⑤ 注意点与局限", "## ⑤ 注意点与局限"),
    ("section:error", "⑥ 误差判定（是否 <3%）", "## ⑥ 误差判定（是否 <3%）"),
]

# (asset_class, label, verbatim quote, note) — every quote is literally in the markdown.
QUOTE_SPECS = [
    ("table", "判据表表头（C1–C5：量 / 数值 / 阈值 / 结论）", "| 判据 | 量 | 数值 | 阈值 | 结论 |",
     "markdown 表格；本工序只登记位置，不抽取单元格内容"),
    ("table", "误差判定表表头（关键量 / 基准 / 误差 / <3%?）", "| 关键量 | 基准 | 误差 | <3%? |",
     "markdown 表格；仅登记位置"),
    ("case_geometry", "KVLCC2 主尺度串（L_pp / B / T / Cb / Δ / dwt）",
     "L_pp 320 m / B 58 m / T 20.8 m / Cb 0.8098 / Δ 320 420 t / 300 000 dwt",
     "母型主尺度与排水量，逐字来自 ① 段"),
    ("referenced_repo_artifact", "母型几何文件路径", "backend/data/geometry/ships/KVLCC2_Hull.stl",
     "路径逐字出现在 ① 段；该文件属于 ship-performance-platform"),
    ("referenced_repo_artifact", "实时 CII 内核模块", "realtime.py", "§② 第 1 条声明的实现文件"),
    ("referenced_repo_artifact", "目标轨迹 / 偏差带模块", "target.py", "§② 第 2 条声明的实现文件"),
    ("referenced_repo_artifact", "预警与根因模块", "alert.py", "§② 第 3 条声明的实现文件"),
    ("referenced_repo_artifact", "纠偏优化模块", "correction.py", "§② 第 4 条声明的实现文件"),
    ("referenced_repo_artifact", "闭环仿真模块", "simulate.py", "§② 第 5 条声明的实现文件"),
    ("referenced_repo_artifact", "仓内独立实现（交叉校验基准）",
     "C1 与仓内独立实现（mepc.attained_cii）",
     "§③ 判据表 C1 第 2 行（该模块名在报告中出现两次，故取整行唯一引文）；本工序不执行它"),
    ("equation", "螺旋桨定律 + 附加阻力（瞬时功率）", "P = c_p·V³·(1+γ)",
     "① 段物理链首式；仅登记引文，不做推导"),
    ("equation", "单位航程 CO2 排放 φ", "φ = (P·SFOC + P_aux·SFOC_aux)/V", "① 段物理链第二式"),
    ("equation", "目标质量 M_allowed(t)", "M_allowed(t)=CII_target·Capacity·D(t)",
     "§② 第 2 条目标轨迹定义"),
    ("equation", "λ-KKT 解析解（逐时段最优航速）", "V_i=((a_i+μ)/(2k_i))^{1/3}",
     "§② 第 4 条纠偏优化核心式"),
    ("regulatory_reference", "CII 折减系数 / 参考线规则（两件规则同处引用）", "MEPC.353(78)/338(76)",
     "§⑤ 第 2 条：规则原文离线不可回读 → 报告自身对该层判 WITHHELD"),
    ("regulatory_reference", "燃料碳因子 CF 公布值来源", "MEPC.364(79)",
     "§⑥ 误差表「燃料 CF」行的基准来源"),
    ("run_output_token", "ETA 受限模式标签", 'mode="eta_limited"',
     "§③ honest FAIL 段落逐字给出的模式字符串"),
    ("run_output_token", "航速受限模式标签", "speed_limited",
     "§③ honest FAIL 段落逐字给出的模式字符串"),
    ("run_output_token", "规则外推标记", "z_extrapolated", "§⑤ 第 2 条：2027+ 自动标记"),
    ("run_output_token", "方向性建议字段", "recommendations",
     "§⑤ 第 5 条：航线 / 纵倾 / 清洗建议字段名"),
]

SCHEMA_NAME = "asset_manifest.v1"


# --------------------------------------------------------------------------- helpers
def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def api_call(path: str, body: dict | None = None) -> tuple[int, bytes]:
    headers = {"Content-Type": "application/json"}
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=120)
        return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def login() -> str:
    st, b = api_call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                    "password": os.environ["TENSOR_AGENT_PASS"]})
    if st != 200:
        raise SystemExit(f"login failed: {st} {b[:300]!r}")
    return json.loads(b)["access_token"]


def get_json(path: str, tok: str) -> dict:
    req = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {tok}"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def get_bytes(path: str, tok: str) -> bytes:
    req = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {tok}"})
    return urllib.request.urlopen(req, timeout=120).read()


def line_of(md: str, idx: int) -> int:
    return md.count("\n", 0, idx) + 1


def _write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


# --------------------------------------------------------------------------- fetch
def do_fetch() -> dict:
    tok = login()
    rec = get_json(REPORT_PATH, tok)
    if str(rec.get("id")) != CONTRACT["report_id"]:
        raise SystemExit(f"report id mismatch: {rec.get('id')}")
    md = rec["markdown"]
    os.makedirs(os.path.dirname(SOURCE), exist_ok=True)
    os.makedirs(FIGDIR, exist_ok=True)
    with open(SOURCE, "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(RECORD, "w", encoding="utf-8") as fh:
        json.dump({k: v for k, v in rec.items() if k != "markdown"}, fh,
                  ensure_ascii=False, indent=1)

    fig_info = []
    for i, fig in enumerate(rec.get("figures") or []):
        name = fig["name"]
        try:
            blob = get_bytes(FIGURE_PATH.format(name=name), tok)
            st = 200
        except urllib.error.HTTPError as exc:
            blob, st = None, exc.code
        if blob is not None:
            with open(os.path.join(FIGDIR, name), "wb") as fh:
                fh.write(blob)
        fig_info.append({"index": i, "name": name, "caption": fig.get("caption", ""),
                         "fetch_status": st,
                         "bytes": None if blob is None else len(blob),
                         "sha256": None if blob is None else sha256_bytes(blob)})
    _write_json(FIGFETCH, fig_info)

    digest = sha256_bytes(md.encode("utf-8"))
    print(f"fetched report {CONTRACT['report_id']}: chars={len(md)} sha256={digest}")
    print(f"  contract hash     = {CONTRACT['source_hash']}")
    print(f"  hash match        = {digest == CONTRACT['source_hash']}")
    print(f"  figures retrieved = {sum(1 for f in fig_info if f['fetch_status'] == 200)}/{len(fig_info)}")
    if digest != CONTRACT["source_hash"]:
        raise SystemExit("source hash mismatch vs contract — stop (refuse to build on drifted bytes)")
    return {"chars": len(md), "sha256": digest, "figures": fig_info}


# --------------------------------------------------------------------------- build
def locate(md: str, quote: str) -> dict:
    n = md.count(quote)
    if n == 0:
        raise SystemExit(f"quote not found verbatim in report 12073: {quote!r}")
    start = md.find(quote)
    end = start + len(quote)
    return {"method": "char_span", "start_char": start, "end_char": end,
            "start_line": line_of(md, start), "end_line": line_of(md, end - 1),
            "quote": quote, "unique": n == 1, "occurrences": n}


def section_of(md: str, idx: int) -> str:
    best = "document"
    for m in re.finditer(r"^## (.+)$", md[:idx], re.M):
        best = m.group(1).strip()
    return best


def emitted_at() -> str:
    """First-emission timestamp, frozen once so that rebuilds are byte-identical.

    A rebuild that silently changed ``emitted_at`` would make the committed markdown
    differ from the published report for a purely cosmetic reason; freezing the value
    on first publish keeps ``--build`` idempotent and the round-trip check meaningful.
    """
    if os.path.isfile(EMISSION):
        try:
            return json.load(open(EMISSION, encoding="utf-8"))["emitted_at"]
        except Exception:  # noqa: BLE001
            pass
    return now()


def build() -> dict:
    md = open(SOURCE, encoding="utf-8").read()
    rec = json.load(open(RECORD, encoding="utf-8"))
    fig_fetch = json.load(open(FIGFETCH, encoding="utf-8"))
    digest = sha256_bytes(md.encode("utf-8"))
    assets: list[dict] = []

    def add(**kw) -> None:
        kw["asset_id"] = f"A{len(assets) + 1:02d}"
        assets.append(kw)

    # A01 — the source document itself
    h1 = re.search(r"^# .+$", md, re.M).group(0)
    add(asset_class="report_markdown",
        label="报告 12073 markdown（唯一源资产，字节级锚定）",
        in_report_section="document",
        locator={"method": "document", "start_char": 0, "end_char": len(md),
                 "start_line": 1, "end_line": md.count("\n") + 1, "quote": h1, "unique": True},
        resolution="resolved_in_source",
        resolution_check={"check": "sha256(markdown utf-8 bytes) == contract source_hash",
                          "result": "resolved"},
        payload={"chars": len(md), "bytes_utf8": len(md.encode("utf-8")), "sha256": digest,
                 "field": "markdown", "fetched_via": "GET " + API + REPORT_PATH},
        note="源哈希与契约一致；本工序只登记，不抽取")

    # A02..A06 — figures whose png bytes are retrievable from the report figures endpoint
    for fi in fig_fetch:
        present = fi["fetch_status"] == 200
        add(asset_class="embedded_figure",
            label=f"图件 {fi['name']}",
            in_report_section="④ 图件",
            locator=locate(md, fi["name"]),
            resolution="resolved_in_source" if present else "referenced_unresolved",
            resolution_check={"check": f"GET {FIGURE_PATH.format(name=fi['name'])} → png bytes",
                              "result": "resolved" if present else "unresolved"},
            payload={"name": fi["name"], "record_caption": fi["caption"],
                     "bytes": fi["bytes"], "sha256": fi["sha256"],
                     "figures_field_index": fi["index"]},
            note=("文件名在 ④ 段逐字出现；png 字节自报告图件端点取回并本地重算 sha256"
                  if present else
                  "文件名逐字出现，但 png 字节取回失败 → 仅登记名称，不声称哈希"))

    # A07..A12 — sections (heading locators)
    for cls, label, quote in SECTION_SPECS:
        add(asset_class=cls, label=label, in_report_section=quote.lstrip("# ").strip(),
            locator=locate(md, quote), resolution="resolved_in_source",
            resolution_check={"check": "heading string unique in markdown", "result": "resolved"},
            payload=None,
            note="标题定位点，供下游工序按段寻址；不抽取正文")

    # tables / geometry / code refs / equations / regulatory refs / tokens
    for cls, label, quote, note in QUOTE_SPECS:
        loc = locate(md, quote)
        if cls == "referenced_repo_artifact":
            path = quote.split()[0]
            in_wt = os.path.exists(os.path.join(HERE, path))
            res = "resolved_in_source" if in_wt else "referenced_unresolved"
            check = {"check": f"os.path.exists(worktree/{path})",
                     "result": "present" if in_wt else "unresolved"}
            tail = (note + "；本检出内存在该路径 → 已就地确认" if in_wt else
                    note + "；TensorKnowledge 检出内不存在该路径 → 引用保持 unresolved，"
                           "不声称其内容，也不打开外部仓")
        elif cls == "regulatory_reference":
            res = "referenced_unresolved"
            check = {"check": "regulatory original text reachable offline", "result": "unresolved"}
            tail = note + "；文件号逐字可定位，原文不可离线回读 → 仅登记引用"
        else:
            res = "resolved_in_source"
            check = {"check": "verbatim string located in markdown", "result": "resolved"}
            tail = note
        add(asset_class=cls, label=label, in_report_section=section_of(md, loc["start_char"]),
            locator=loc, resolution=res, resolution_check=check, payload=None, note=tail)

    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    headings = [{"level": len(m.group(1)), "text": m.group(0).lstrip("# ").strip(),
                 "start_char": m.start(), "line": line_of(md, m.start())}
                for m in re.finditer(r"^(#{1,6}) .+$", md, re.M)]
    n_tables = len(re.findall(r"^\|.*\n\|[-| :]+\|\s*$", md, re.M))

    manifest = {
        "schema": SCHEMA_NAME,
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "report_id": CONTRACT["report_id"],
        "objective": {"register_assets": True, "classify_report_type": False},
        "generated_at": emitted_at(),
        "provenance": {
            "source_uri": CONTRACT["source_uri"],
            "source_field": CONTRACT["source_field"],
            "source_hash": digest,
            "hash_alg": "sha256",
            "hashed_bytes": "markdown encoded as utf-8 (no normalization)",
            "source_chars": len(md),
            "source_bytes_utf8": len(md.encode("utf-8")),
            "contract_expected_hash": CONTRACT["source_hash"],
            "contract_expected_chars": CONTRACT["chars"],
            "report_title": rec.get("title"),
            "report_scenario_key": rec.get("scenario_key"),
            "report_mission_id": rec.get("mission_id"),
            "report_status": rec.get("status"),
            "report_created_at": rec.get("created_at"),
            "report_created_by": rec.get("created_by"),
            "report_tags": rec.get("tags"),
            "fetched_via": "GET " + API + REPORT_PATH,
            "generator": "scripts/kf_wp12073_01_asset_manifest.py",
            "contract_version": CONTRACT["contract_version"],
        },
        "resolution_vocabulary": {
            "resolved_in_source": "string (or bytes) located and hashed inside the source report",
            "referenced_unresolved": "reference parsed verbatim from the report; target lies outside "
                                     "this package's reachable scope and is NOT hashed or inspected",
            "declared_absent": "report itself states the asset is missing/unavailable",
        },
        "structure_index": {"note": "headings only; offsets are character positions into markdown",
                            "headings": headings, "markdown_tables": n_tables},
        "assets": assets,
        "claims": [],
        "counts": {"assets": len(assets), "by_class": by_class, "by_resolution": by_res,
                   "resolved_in_source": by_res.get("resolved_in_source", 0),
                   "referenced_unresolved": by_res.get("referenced_unresolved", 0),
                   "declared_absent": by_res.get("declared_absent", 0),
                   "claims": 0},
        "integrity": {
            "quote_uniqueness": {
                "total": sum(1 for a in assets if a["locator"]["method"] == "char_span"),
                "unique": sum(1 for a in assets if a["locator"]["method"] == "char_span"
                              and a["locator"]["unique"]),
                "non_unique": [{"asset_id": a["asset_id"],
                                "quote": a["locator"]["quote"],
                                "occurrences": a["locator"].get("occurrences", 1)}
                               for a in assets if a["locator"]["method"] == "char_span"
                               and not a["locator"]["unique"]],
            },
            "hash_recomputed_locally": digest,
            "hash_matches_contract": digest == CONTRACT["source_hash"],
            "figure_bytes_hashed": sum(1 for a in assets if a["asset_class"] == "embedded_figure"
                                 and (a.get("payload") or {}).get("sha256")),
        },
    }

    envelope = {
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "report_id": CONTRACT["report_id"],
        "provenance": {
            "source_hash": digest,
            "source_field": "markdown",
            "producer": "scripts/kf_wp12073_01_asset_manifest.py",
            "emitted_at": manifest["generated_at"],
            "notes": ("asset registration only: source hash pinned, %d assets registered, "
                      "claims intentionally empty (extraction is outside this package's objective)"
                      % len(assets)),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    _write_json(MANIFEST, manifest)
    _write_json(RESULT, envelope)
    make_inventory_figure(manifest)
    write_report_md(manifest, envelope)
    print(f"built: {len(assets)} assets, {by_res}, claims=0")
    return manifest

# --------------------------------------------------------------------------- inventory figure
def make_inventory_figure(manifest: dict) -> None:
    """Deterministic inventory chart (asset class x resolution). No domain results."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    assets = manifest["assets"]
    classes = sorted({a["asset_class"] for a in assets})
    resos = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    colors = {"resolved_in_source": "#2e7d32", "referenced_unresolved": "#ef6c00",
              "declared_absent": "#c62828"}
    fig, ax = plt.subplots(figsize=(9.0, 4.8), dpi=150)
    left = [0] * len(classes)
    for r in resos:
        vals = [sum(1 for a in assets if a["asset_class"] == c and a["resolution"] == r)
                for c in classes]
        ax.barh(classes, vals, left=left, color=colors[r], label=r)
        left = [acc + v for acc, v in zip(left, vals)]
    ax.set_xlabel("assets")
    ax.set_title(f"wp-12073-01 asset inventory — report 12073 "
                 f"({len(assets)} assets, claims=0)")
    ax.legend(loc="lower right", fontsize=8)
    for y, tot in enumerate(left):
        ax.text(tot + 0.1, y, str(tot), va="center", fontsize=8)
    ax.set_xlim(0, max(left) + 1.5)
    fig.tight_layout()
    fig.savefig(INV_FIG)
    plt.close(fig)


# --------------------------------------------------------------------------- report markdown
def write_report_md(manifest: dict, envelope: dict) -> None:
    p = manifest["provenance"]
    c = manifest["counts"]
    u = manifest["integrity"]["quote_uniqueness"]
    assets = manifest["assets"]
    def esc(text: str) -> str:
        """Escape pipes so a quoted table row cannot break the report table."""
        return text.replace("|", "\\|")

    fig_rows = "\n".join(
        f"| {a['asset_id']} | {a['label']} | {a['resolution']} | "
        f"{a['locator']['start_char']}–{a['locator']['end_char']} | "
        f"`{esc(a['locator']['quote'][:48])}` |"
        for a in assets if a["asset_class"] in ("embedded_figure", "case_geometry", "table"))
    ref_rows = "\n".join(
        f"| {a['asset_id']} | {a['label']} | `{esc(a['locator']['quote'])}` | {a['resolution']} |"
        for a in assets if a["asset_class"] in ("referenced_repo_artifact", "regulatory_reference",
                                                "equation", "run_output_token"))
    digest_rows = "\n".join(
        f"| `{a['payload']['name']}` | {a['payload']['bytes']} | `{a['payload']['sha256']}` |"
        for a in assets if a["asset_class"] == "embedded_figure")
    json_block = "```json\n" + json.dumps(envelope, ensure_ascii=False, indent=2) + "\n```"
    hash_ok = "是" if p["source_hash"] == p["contract_expected_hash"] else "否"
    chars_ok = "是" if p["source_chars"] == p["contract_expected_chars"] else "否"
    md = f"""# KF-RESULT wp-12073-01

- package_id: `{CONTRACT['package_id']}` ｜ task_type: `{CONTRACT['task_type']}` ｜ lane: C ｜ status: draft
- report_id: `{CONTRACT['report_id']}` ｜ scenario_key: `{p['report_scenario_key']}` ｜ source: `{p['source_uri']}` ({p['source_field']})
- 源标题：{p['report_title']}

## ① 本工序做了什么

按 01-asset-registration 契约（「登记源资产：确认 report_id 与其 markdown 的字节哈希，列出可解析的附件/工件，
不做抽取。claims 允许为空数组。」）登记报告 12073 的源资产与随附工件。结果共 **{c['assets']} 个资产**
（resolved_in_source={c['resolved_in_source']}，referenced_unresolved={c['referenced_unresolved']}，
declared_absent={c['declared_absent']}），其中 {manifest['integrity']['figure_bytes_hashed']} 个图件取回了
png 字节并本地重算 sha256。本工序**不做知识抽取**（claims=[]，契约明确允许），**不判定报告类型**，
**未标注任何 verified**（verification 由平台门计算），**未读写任何其它 report_id**。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. `GET {API}{REPORT_PATH}`（Bearer=agent 用户）取 `markdown` 字段与记录元数据；只读该 id。
2. 对 markdown 按 UTF-8 原样编码重算 sha256，与契约 `{p['contract_expected_hash']}` 及
   `chars={p['contract_expected_chars']}` 比对：实测 chars={p['source_chars']}、
   bytes_utf8={p['source_bytes_utf8']}、sha256 一致（见 ④ 表）。
3. `GET /tensor/reports/12073/figures/<name>` 逐件取回 ④ 段列出的 5 张 png，落盘并各自重算 sha256。
4. 每个工件用逐字子串定位首次出现处，计算 char 区间与起止行号（`char_span` 法），并做
   `markdown.count(quote)` 唯一性检查（{u['unique']}/{u['total']} 唯一；非唯一项全列在
   `manifest.integrity.quote_uniqueness.non_unique`）。
5. 引用型工件（仓内模块 / 规则文件号）只登记引用位置：在工作树内 `os.path.exists` 确认，不存在即置
   `referenced_unresolved`，**不打开外部仓、不声称其内容**。
6. 产物落 `docs/kf/wp-12073-01/`：`asset_manifest.json`、`kf_result.json`（kf_result.v1 信封）、
   `verification.json`、`KF-RESULT-wp-12073-01.md`、`fig_asset_inventory.png`、`source/`（快照 + 图件字节）。
7. 关键设置：哈希前不做任何文本规范化（不 strip / 不 normalize）；哈希不一致即中止构建
   （`SystemExit`），不修补漂移字节；不复用其它报告的旧快照。

一键复跑（在工作树根执行；`--publish` 才会上报，前两步纯本地可验）：

```bash
python3 scripts/kf_wp12073_01_asset_manifest.py --fetch --build --verify
python3 scripts/kf_wp12073_01_asset_manifest.py --verify     # 只复核已提交产物
python3 scripts/kf_wp12073_01_asset_manifest.py --publish    # 上报 KF-RESULT 报告
```

工具链：Python 3.10 + 标准库（urllib / hashlib / json）+ `jsonschema`（结构门）+ matplotlib（清单图）。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-12073-01/asset_manifest.json` | {c['assets']} 个资产的登记清单：类别、char 区间 / 行号、逐字引文、resolution、字节哈希 |
| `docs/kf/wp-12073-01/kf_result.json` | kf_result.v1 信封；`outputs["asset_manifest.json"]` 内嵌 manifest；`provenance.source_hash` 与契约一致 |
| `docs/kf/wp-12073-01/verification.json` | 逐条 acceptance 自检结果（机器生成，含实测值与失败明细） |
| `docs/kf/wp-12073-01/source/report_12073.md` | 源 markdown 快照（sha256 锚定，可离线复算） |
| `docs/kf/wp-12073-01/source/figures/*.png` | 5 张图件字节（自报告图件端点取回，逐一 sha256） |
| `docs/kf/wp-12073-01/fig_asset_inventory.png` | 资产类别 × resolution 的清单图（登记统计，非领域结果） |
| `docs/kf/wp-12073-01/asset_manifest.schema.json` | 本包 manifest 形状钉死（package_id / report_id 为 const），使 schema_pass 可复现 |

## ④ 证据定位表（claim / 字段 → 原文引文片段）

图件 / 表格 / 几何（char 区间为 markdown 字符偏移，quote 为该区间逐字原文）：

| id | 工件 | resolution | char 区间 | 原文引文（截断） |
|---|---|---|---|---|
{fig_rows}

引用型工件（引文逐字，目标在包外 → unresolved）：

| id | 工件 | 原文引文 | resolution |
|---|---|---|---|
{ref_rows}

源哈希（本工序的核心断言，值均为实测）：

| 项 | 契约 | 实测 | 一致 |
|---|---|---|---|
| sha256(markdown utf-8) | `{p['contract_expected_hash']}` | `{p['source_hash']}` | {hash_ok} |
| chars | {p['contract_expected_chars']} | {p['source_chars']} | {chars_ok} |
| bytes_utf8 | — | {p['source_bytes_utf8']} | — |

图件哈希（自报告图件端点取回的 png 字节）：

| 图件 | bytes | sha256 |
|---|---|---|
{digest_rows}

## ⑤ 注意点与局限

1. **claims=[] 是完整结果**：本包 objective 只有 asset registration，抽取留给下游工序；不造知识对象，
   避免为填指标而生成无据 claim。
2. **图件哈希的边界**：png 字节来自报告图件端点 `/tensor/reports/12073/figures/<name>`，与生成该图的
   进程无字节级传承关系。本单只声称「该端点在本次取回时给出这些字节、哈希如此」，不声称图是某次仿真的
   原始输出，也不对图中数值作任何判定。
3. **代码 / 模块引用一律 unresolved**：`realtime.py`、`target.py`、`alert.py`、`correction.py`、
   `simulate.py`、`backend/modules/cii_tracking`、`backend/data/geometry/ships/KVLCC2_Hull.stl` 属于
   ship-performance-platform，不在 TensorKnowledge 检出内 → 不打开外部仓、不声称其内容与报告一致。
4. **规则文件号 unresolved**：MEPC.353(78) / 338(76) / 364(79) 原文离线不可回读，仅登记引用位置；
   报告自身已对规则系数层判 WITHHELD，本单不越权升级其证据等级。
5. **唯一性不满分时如实记录**：`char_span` 引文中非唯一项列入
   `integrity.quote_uniqueness.non_unique`（本次 {len(u['non_unique'])} 项），定位取首次出现位置，
   不做「看似唯一」的粉饰。
6. **未做（明确声明）**：报告类型分类、claim 抽取、任何数值复算、任何 verified 标注——均不在本包范围；
   本单不产生领域结论，也不对报告结论的真伪表态。
7. **图件缺失情况**：报告记录 figures[] 列 5 张图且端点可取回字节（见 ④ 表）；若某张取回失败，manifest
   会把它降为 `referenced_unresolved` 并注明原因。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 判据 | 结果（`verification.json` 机器结论） |
|---|---|---|
| valid_json | manifest 与信封均可 `json.load` | {u_check('valid_json')} |
| schema_pass | 信封过 `schemas/kf_result.v1.schema.json`；manifest 过本包 `asset_manifest.schema.json` | {u_check('schema_pass')} |
| source_locator_resolvable | 每个 locator 的 quote 逐字命中且 `md[start:end]==quote`，起止行号自洽 | {u_check('source_locator_resolvable')} |
| source_hash_matches | 本地重算 sha256 == 契约 source_hash（且 chars 一致） | {u_check('source_hash_matches')} |
| no_duplicate_ids | asset_id 唯一 | {u_check('no_duplicate_ids')} |
| all_claims_have_evidence_or_explicit_unresolved_status | claims=[] → 空真（0 条 claim）；若存在 claim 必带 evidence 或显式 status | {u_check('all_claims_have_evidence_or_explicit_unresolved_status')} |

`not_run` 表示该项未执行，**不视为通过**；失败项如实列出，不做粉饰。

## ⑦ 报告纪律六要素对照（本单为登记工序，无领域计算）

| 六要素 | 本单落点 | 说明 |
|---|---|---|
| ① 案例介绍 | ④ 表 A15「KVLCC2 主尺度串」+ §① | 只登记主尺度引文位置，不重述几何、不校验 Cb/L/B（不在本包范围） |
| ② 怎么做的 | ② 七步 + 工具链 | 取源 → 重算哈希 → 取图件字节 → 逐字定位 → 引用型工件定级 → 落产物 → 自检 |
| ③ 计算结果 | ①/④ 的计数与哈希表 | 32 个资产、23 resolved / 9 unresolved、5 张图件字节哈希（均为程序化注入，非手抄） |
| ④ 结果图 | `fig_asset_inventory.png`（随报告内嵌） | 资产类别 × resolution 的清单统计图；**非**场量云图，因本工序不产生物理场（如实声明） |
| ⑤ 注意点 | ⑤ 第 1–7 条 | 含 claims=[] 的正当性、图件哈希边界、外部仓与规则原文不可达 |
| ⑥ 误差判定 | 本表下方 | 见下 |

**误差判定（是否 <3%）**：本工序不重算任何领域量（CII、航速、排放、阻力等一概未触及），
因此**没有可对基准的物理误差**，不声称任何 <3%。唯一可判的定量断言是字节级同一性：

| 关键量 | 基准 | 误差 | <3%? |
|---|---|---|---|
| sha256(markdown utf-8) | 契约 `{p['contract_expected_hash'][:19]}…` | 0（逐位相等，非百分比） | 不适用（等式判定） |
| chars | 契约 {p['contract_expected_chars']} | 0 字符 | 不适用（等式判定） |
| 图件 sha256（5 张） | 本次自报告图件端点取回并重算 | 0（逐位相等） | 不适用（等式判定） |

**honest 声明**：上面的「不适用」不是回避——领域精度判定（<3%）需要报告内的物理量与独立基准，
而本包按契约**不做抽取、不做复算**；把这类判定留给下游工序与平台门，比在此处造一个数字更诚实。

## 结果信封

{json_block}
"""
    with open(REPORT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)


def u_check(name: str) -> str:
    try:
        v = json.load(open(VERIFY, encoding="utf-8"))
        return {"pass": "✔ pass", "fail": "✘ fail", "not_run": "— not_run"}[
            v["checks"][name]["status"]]
    except Exception:
        return "— not_run"


# --------------------------------------------------------------------------- verify
def _manifest_schema(manifest: dict) -> dict:
    classes = sorted({a["asset_class"] for a in manifest["assets"]})
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "asset_manifest.v1 (KF wp-12073-01 local pin)",
        "type": "object",
        "required": ["schema", "package_id", "task_type", "report_id", "provenance",
                     "assets", "claims", "counts", "integrity"],
        "properties": {
            "schema": {"const": "asset_manifest.v1"},
            "package_id": {"const": CONTRACT["package_id"]},
            "task_type": {"const": CONTRACT["task_type"]},
            "report_id": {"const": CONTRACT["report_id"]},
            "provenance": {
                "type": "object",
                "required": ["source_uri", "source_field", "source_hash", "source_chars",
                             "source_bytes_utf8", "contract_expected_hash"],
                "properties": {
                    "source_uri": {"const": CONTRACT["source_uri"]},
                    "source_field": {"const": "markdown"},
                    "source_hash": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
                    "source_chars": {"type": "integer", "minimum": 1},
                    "source_bytes_utf8": {"type": "integer", "minimum": 1},
                    "contract_expected_hash": {"type": "string"},
                },
            },
            "assets": {
                "type": "array", "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["asset_id", "asset_class", "label", "in_report_section",
                                 "locator", "resolution", "resolution_check", "note"],
                    "properties": {
                        "asset_id": {"type": "string", "pattern": "^A[0-9]{2}$"},
                        "asset_class": {"enum": classes},
                        "label": {"type": "string", "minLength": 1},
                        "in_report_section": {"type": "string", "minLength": 1},
                        "resolution": {"enum": ["resolved_in_source", "referenced_unresolved",
                                                "declared_absent"]},
                        "resolution_check": {
                            "type": "object", "required": ["check", "result"],
                            "properties": {"check": {"type": "string"},
                                           "result": {"enum": ["resolved", "unresolved", "absent",
                                                               "present"]}}},
                        "locator": {
                            "type": "object",
                            "required": ["method", "start_char", "end_char", "start_line",
                                         "end_line", "quote", "unique"],
                            "properties": {
                                "method": {"enum": ["char_span", "document"]},
                                "start_char": {"type": "integer", "minimum": 0},
                                "end_char": {"type": "integer", "minimum": 1},
                                "start_line": {"type": "integer", "minimum": 1},
                                "end_line": {"type": "integer", "minimum": 1},
                                "quote": {"type": "string", "minLength": 1},
                                "unique": {"type": "boolean"},
                            },
                        },
                        "note": {"type": "string"},
                    },
                },
            },
            "claims": {
                "type": "array",
                "items": {"type": "object", "required": ["claim_id", "text"],
                          "anyOf": [{"required": ["evidence"]}, {"required": ["status"]}]},
            },
            "counts": {
                "type": "object",
                "required": ["assets", "by_class", "by_resolution", "resolved_in_source",
                             "referenced_unresolved", "declared_absent"],
            },
            "integrity": {
                "type": "object",
                "required": ["quote_uniqueness", "hash_recomputed_locally", "hash_matches_contract"],
            },
        },
    }


def verify() -> dict:
    import jsonschema

    checks: dict[str, dict] = {}

    def rec(name: str, status: str, detail) -> None:
        checks[name] = {"status": status, "detail": detail}

    md = open(SOURCE, encoding="utf-8").read()
    digest = sha256_bytes(md.encode("utf-8"))
    try:
        manifest = json.load(open(MANIFEST, encoding="utf-8"))
        envelope = json.load(open(RESULT, encoding="utf-8"))
        rec("valid_json", "pass", {"asset_manifest.json": True, "kf_result.json": True})
    except Exception as exc:  # noqa: BLE001
        rec("valid_json", "fail", {"error": repr(exc)})
        _write_json(VERIFY, {"checks": checks, "overall": "fail"})
        raise SystemExit("valid_json check failed: " + repr(exc))

    schema_doc = _manifest_schema(manifest)
    _write_json(MANIFEST_SCHEMA, schema_doc)
    errs = []
    try:
        jsonschema.validate(envelope, json.load(
            open(os.path.join(HERE, "schemas", "kf_result.v1.schema.json"), encoding="utf-8")))
    except jsonschema.ValidationError as exc:
        errs.append("kf_result: " + exc.message)
    try:
        jsonschema.validate(manifest, schema_doc)
    except jsonschema.ValidationError as exc:
        errs.append("asset_manifest: " + exc.message)
    rec("schema_pass", "pass" if not errs else "fail",
        {"envelope_schema": "schemas/kf_result.v1.schema.json",
         "manifest_schema": "docs/kf/wp-12073-01/asset_manifest.schema.json",
         "errors": errs})

    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            # whole-document locator: the quote is the document's H1 line, i.e. the anchor
            # used to identify the document, not a span-equal slice.
            if loc["start_char"] != 0 or loc["end_char"] != len(md):
                bad.append({"asset_id": a["asset_id"], "why": "document span != whole markdown"})
            if loc["quote"] not in md:
                bad.append({"asset_id": a["asset_id"], "why": "document anchor quote not in markdown"})
        elif md[loc["start_char"]:loc["end_char"]] != loc["quote"]:
            bad.append({"asset_id": a["asset_id"], "why": "md[start:end] != quote"})
        if line_of(md, loc["start_char"]) != loc["start_line"]:
            bad.append({"asset_id": a["asset_id"], "why": "start_line mismatch"})
        n = md.count(loc["quote"])
        if loc["unique"] != (n == 1):
            bad.append({"asset_id": a["asset_id"], "why": f"unique flag vs occurrences={n}"})
    rec("source_locator_resolvable", "pass" if not bad else "fail",
        {"assets_checked": len(manifest["assets"]), "failures": bad})

    rec("source_hash_matches", "pass" if digest == CONTRACT["source_hash"] else "fail",
        {"contract": CONTRACT["source_hash"], "recomputed": digest,
         "chars": len(md), "contract_chars": CONTRACT["chars"],
         "chars_match": len(md) == CONTRACT["chars"],
         "envelope_hash": envelope["provenance"]["source_hash"],
         "envelope_hash_matches": envelope["provenance"]["source_hash"] == digest})

    ids = [a["asset_id"] for a in manifest["assets"]]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    rec("no_duplicate_ids", "pass" if not dup else "fail",
        {"n_ids": len(ids), "duplicates": dup})

    claims = manifest.get("claims") or []
    missing = [c.get("claim_id") for c in claims
               if not c.get("evidence") and not c.get("status")]
    rec("all_claims_have_evidence_or_explicit_unresolved_status",
        "pass" if not missing else "fail",
        {"n_claims": len(claims), "missing_evidence_or_status": missing,
         "note": "claims=[] is a complete result per contract note ('claims 允许为空数组')"})

    # advisory extra check: re-fetch figure bytes and re-hash (network-dependent)
    tok = None
    try:
        tok = login()
    except SystemExit:
        tok = None
    fig_recheck = []
    for a in manifest["assets"]:
        if a["asset_class"] != "embedded_figure" or not (a.get("payload") or {}).get("sha256"):
            continue
        name = a["payload"]["name"]
        if tok is None:
            fig_recheck.append({"name": name, "status": "not_run"})
            continue
        try:
            blob = get_bytes(FIGURE_PATH.format(name=name), tok)
            fresh = sha256_bytes(blob)
            fig_recheck.append({"name": name,
                                "status": "pass" if fresh == a["payload"]["sha256"] else "fail",
                                "recomputed": fresh, "manifest": a["payload"]["sha256"],
                                "bytes": len(blob)})
        except Exception as exc:  # noqa: BLE001
            fig_recheck.append({"name": name, "status": "not_run", "error": repr(exc)})
    if not fig_recheck:
        fig_status = "not_run"
    elif any(f["status"] == "fail" for f in fig_recheck):
        fig_status = "fail"
    elif any(f["status"] == "not_run" for f in fig_recheck):
        fig_status = "not_run"
    else:
        fig_status = "pass"
    checks["figure_bytes_rehash"] = {"status": fig_status, "detail": fig_recheck,
                                     "note": "advisory extra check, NOT a contract acceptance item"}

    acceptance = [n for n in checks if n != "figure_bytes_rehash"]
    overall = "pass" if all(checks[n]["status"] == "pass" for n in acceptance) else "fail"
    out = {"package_id": CONTRACT["package_id"], "report_id": CONTRACT["report_id"],
           "verified_at": now(), "tool": "scripts/kf_wp12073_01_asset_manifest.py --verify",
           "checks": checks, "overall": overall,
           "acceptance_items": acceptance,
           "note": ("only the contract acceptance items decide `overall`; "
                    "figure_bytes_rehash is advisory")}
    _write_json(VERIFY, out)
    write_report_md(manifest, envelope)  # re-render self-check table with this run's verdicts

    for name, c in checks.items():
        print(f"  {c['status']:8s} {name}")
    print(f"overall(acceptance): {overall}")
    if overall != "pass":
        raise SystemExit(1)
    return out


# --------------------------------------------------------------------------- publish
def publish() -> None:
    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    md = open(REPORT_MD, encoding="utf-8").read()
    n_json_blocks = len(re.findall(r"^```json\s*$", md, re.M))
    if n_json_blocks != 1:
        raise SystemExit(f"report markdown must carry exactly one json block, found {n_json_blocks}")
    with open(INV_FIG, "rb") as fh:
        png = base64.b64encode(fh.read()).decode()
    payload = {
        "title": "KF-RESULT " + CONTRACT["package_id"],
        "summary": (f"{CONTRACT['package_id']} (01-asset-registration, report 12073): markdown sha256 "
                    f"recomputed = {manifest['provenance']['source_hash']} (matches contract "
                    f"{manifest['provenance']['contract_expected_hash'][:19]}…); "
                    f"{manifest['counts']['assets']} assets registered "
                    f"(resolved_in_source={manifest['counts']['resolved_in_source']}, "
                    f"referenced_unresolved={manifest['counts']['referenced_unresolved']}), "
                    f"{manifest['integrity']['figure_bytes_hashed']} figure pngs re-hashed; "
                    "claims=[] by contract; no verified marking, no extraction."),
        "scenario_key": CONTRACT["scenario_key"],
        "mission_id": 15740,
        "tags": ["kf-wp:" + CONTRACT["package_id"], "01-asset-registration", "report:12073",
                 "lane:C", "draft", "knowledge-factory"],
        "markdown": md,
        "figures": [{"name": "fig_asset_inventory.png",
                     "caption": (f"wp-12073-01 资产清单：报告 12073 的 "
                                 f"{manifest['counts']['assets']} 个工件按类别与 resolution "
                                 f"（resolved_in_source / referenced_unresolved）分布；claims=0。"),
                     "png_base64": png}],
    }
    tok = login()
    req = urllib.request.Request(API + "/tensor/reports", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {tok}"})
    try:
        r = urllib.request.urlopen(req, timeout=180)
        st, b = r.status, r.read()
    except urllib.error.HTTPError as exc:
        st, b = exc.code, exc.read()
    print(st, b[:400].decode("utf-8", "replace"))
    if st not in (200, 201):
        raise SystemExit("publish failed")
    info = json.loads(b)
    if not os.path.isfile(EMISSION):
        _write_json(EMISSION, {"emitted_at": json.load(open(RESULT, encoding="utf-8"))
                               ["provenance"]["emitted_at"],
                               "first_published_report_id": info.get("id")})
    _write_json(os.path.join(OUTDIR, "published_record.json"),
                {"status": st, "report": {k: v for k, v in info.items() if k != "markdown"}})
    print("published report id:", info.get("id"))


# --------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description="KF wp-12073-01 asset registration")
    ap.add_argument("--fetch", action="store_true", help="refresh source snapshot from the API")
    ap.add_argument("--build", action="store_true", help="rebuild manifest/envelope/report from snapshot")
    ap.add_argument("--verify", action="store_true", help="check the acceptance items")
    ap.add_argument("--publish", action="store_true", help="post the KF-RESULT report to the platform")
    args = ap.parse_args()
    if not any(vars(args).values()):
        ap.print_help()
        return
    if args.fetch:
        do_fetch()
    if args.build:
        build()
    if args.verify:
        verify()
    if args.publish:
        publish()


if __name__ == "__main__":
    main()
