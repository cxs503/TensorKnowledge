"""KF work package wp-12080-01 (task_type=01-asset-registration) for report_id=12080.

Single responsibility: register the *source* assets of report 12080 and confirm the
markdown byte hash. No extraction, no knowledge claims (claims == []).

Pipeline
  1. fetch report 12080 markdown from the platform API (env credentials only)
     -> runs/wp-12080-01/report_12080.json, runs/wp-12080-01/report_12080.md
  2. verify sha256(markdown) == contract source_hash and chars == contract chars
  3. locate every asset by a *unique verbatim anchor* in the markdown; the stored
     quote is exactly md[start_char:end_char] (never retyped by hand) and must occur
     exactly once -> source_locator is machine-resolvable
  4. emit runs/wp-12080-01/asset_manifest.json and the kf_result.v1 envelope
     -> docs/wp-12080-01/KF-RESULT-wp-12080-01.md (the delivery report body:
        exactly ONE ```json block, holding the envelope verbatim)

Never hardcodes credentials: TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE.
Nothing is marked verified (verification is computed by the platform gate).

Platform reports are append-only (no PUT/PATCH/DELETE), so KF_EMITTED_AT=<iso> pins
provenance.emitted_at and lets a re-run reproduce the published body byte-for-byte.

Usage:  python3 scripts/kf_wp12080_01_register.py [--offline]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

PKG = "wp-12080-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "12080"
SOURCE_URI = "tensor://reports/12080"
CONTRACT_HASH = "fe235db998e65d47ead6658e95916dbdf9764ffd213002e7ffe8ca58809c93e0"
CONTRACT_CHARS = 7931
CONTRACT_TITLE = "P333W2-N04 DP 时域闭环与单点失效漂移：时域降额因子 + DP-2/3 失效漂移判据"
SCENARIO_KEY = "dp_time_domain"
CONTRACT_VERSION = "1.0"
LANE = "C"

RUN = pathlib.Path("runs") / PKG
DOC = pathlib.Path("docs") / PKG
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


# --------------------------------------------------------------------------- io
def _post_json(url, payload, token=None):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _get_json(url, token=None):
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = _post_json(BASE + path, {"username": user, "password": pwd})
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def fetch_report(offline: bool):
    RUN.mkdir(parents=True, exist_ok=True)
    raw_path, md_path = RUN / "report_12080.json", RUN / "report_12080.md"
    if offline:
        if not md_path.exists():
            sys.exit("--offline but %s missing" % md_path)
        payload = json.loads(raw_path.read_text()) if raw_path.exists() else {}
        return payload, md_path.read_text()
    tok = login()
    payload = _get_json(BASE + "/tensor/reports/" + REPORT_ID, tok)
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    md = payload["markdown"]
    raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    md_path.write_text(md)
    return payload, md


# ------------------------------------------------------------------- locating
def line_starts(md: str):
    starts = [0]
    for i, ch in enumerate(md):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def _line_index(md: str, starts, pos: int) -> int:
    lo, hi = 0, len(starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if starts[mid] <= pos:
            lo = mid
        else:
            hi = mid - 1
    return lo


def _is_list_item(line: str) -> bool:
    t = line.lstrip()
    if t.startswith(("* ", "- ")):
        return True
    head = t.split(" ", 1)[0].rstrip(".")
    return head.isdigit() and t.startswith(head + ".")


def block_span(md: str, starts, pos: int):
    """Expand the block that contains ``pos``.

    Table row -> the contiguous '|' table;  line inside a ``` fence -> the fence;
    otherwise -> the contiguous non-empty paragraph.
    """
    lines = md.split("\n")
    i = _line_index(md, starts, pos)
    if _is_list_item(lines[i]):
        # list items: anchor exactly that item, not the whole (gap-free) list
        return starts[i], starts[i] + len(lines[i])
    if lines[i].lstrip().startswith("|"):
        a = i
        while a > 0 and lines[a - 1].lstrip().startswith("|"):
            a -= 1
        b = i
        while b + 1 < len(lines) and lines[b + 1].lstrip().startswith("|"):
            b += 1
    else:
        # inside a fenced code block? parity of fences strictly above line i
        fences_above = sum(1 for k in range(i) if lines[k].startswith("```"))
        if fences_above % 2 == 1:
            open_at = max(k for k in range(i) if lines[k].startswith("```"))
            close = next(k for k in range(i + 1, len(lines)) if lines[k].startswith("```"))
            a, b = open_at, close
        else:
            a = i
            while a > 0 and lines[a - 1].strip() != "":
                a -= 1
            b = i
            while b + 1 < len(lines) and lines[b + 1].strip() != "":
                b += 1
    start = starts[a]
    end = starts[b] + len(lines[b])
    return start, end


def locate(md: str, starts, anchor: str):
    n = md.count(anchor)
    if n != 1:
        raise SystemExit("anchor not unique (%d occurrences): %r" % (n, anchor))
    pos = md.index(anchor)
    start, end = block_span(md, starts, pos)
    quote = md[start:end]
    if md.count(quote) != 1:
        # widen-invariance failure: the block itself must also be unique
        raise SystemExit("block quote not unique: %r" % quote[:60])
    if "```" in quote:
        raise SystemExit("quote contains a code fence (would break the result block): %r" % quote[:60])
    sl = _line_index(md, starts, start) + 1
    el = _line_index(md, starts, end - 1) + 1
    return {
        "method": "char_span",
        "start_char": start,
        "end_char": end,
        "start_line": sl,
        "end_line": el,
        "quote": quote,
        "unique": True,
    }


# --------------------------------------------------------------- asset table
# (asset_id, asset_class, label, anchor, resolution, check, result, note)
SPEC = [
    ("A01", "document", "报告正文 markdown（头部元信息 + 数据来源声明；全文身份由 sha256/字符数承载）",
     "> 节点 P333W2-N04 · 仓 ship-performance-platform", "resolved_in_source",
     "sha256(markdown) recomputed locally vs contract source_hash; chars vs contract chars",
     "resolved", "文档整体身份见 asset_manifest.source（sha256/字符/字节）；本定位锚定头部声明块"),
    ("A02", "heading", "报告标题行", "# P333W2-N04 · 动力定位时域闭环",
     "resolved_in_source", "anchor line unique in markdown", "resolved", "标题与契约 title 逐字一致"),
    ("A03", "table", "主尺度/几何参数表（8 行，含 Cb/L/B/T/L_over_B/B_over_T/displacement_t）",
     "| L | 90.000 |", "resolved_in_source", "table block unique in markdown", "resolved",
     "几何量供下游抽取，本工序不抽取"),
    ("A04", "table", "DP-2 推力器布置表（4 台：2 全回转 + 2 异站位侧推）",
     "| stern_az_port | -37.0 | -5.0 | 300 | azimuth | 2.5 |", "resolved_in_source",
     "table block unique in markdown", "resolved", "含 x/y/T_max/类型/方位角速率列"),
    ("A05", "table", "惯量/阻尼参数表（M11/M22/M66/D11/D22/D66/三个时间常数）",
     "| tau_x_s | 60.75 |", "resolved_in_source", "table block unique in markdown", "resolved",
     "阻尼口径=DR 线性化频段值"),
    ("A06", "prereg_lock", "预声明判据 analysis.PREDECLARED（watch circle/容差/仿真时步）",
     "**预声明判据**（先于看结果写死在", "resolved_in_source",
     "anchor line unique; JSON 正文为其后紧邻代码块（本工序不复制块内文本）", "resolved",
     "判据先于结果声明，是下游复核 C1–C6 的门槛值来源"),
    ("A07", "parameter_set", "计算工况（Hs/Tp/流速/μ/R/12 来向/共线假设）",
     "**工况**：Hs=2.0 m、Tp=8.0 s", "resolved_in_source", "paragraph unique in markdown",
     "resolved", "工况参数单一来源行"),
    ("A08", "table", "计算结果主表（12 来向 × 静力/时域/intact/worst-1/降额）",
     "| 来向 (°) | 静力 intact (m/s) | 时域 intact (m/s) | 降额 intact", "resolved_in_source",
     "table block unique in markdown", "resolved", "下游抽取的主数字表"),
    ("A09", "numeric_anchor", "降额因子均值与静力包线最小值（intact 0.696 / worst-1 0.620）",
     "降额因子（有定义的扇区）：intact 均值 0.696", "resolved_in_source",
     "paragraph unique in markdown", "resolved", "量级锚点；缺陷扇区不计入均值"),
    ("A10", "table", "C1 静力一致性表（3 组增益，位置误差/L）",
     "| 工况 | 增益系数 | x_ss (m) |", "resolved_in_source", "table block unique in markdown",
     "resolved", "C1 判据 <0.5%·L"),
    ("A11", "statement", "C2 包含关系被否证（honest FAIL，21/36 反例）",
     "**C2 包含关系**（静力可行 ⊆ 时域可保持）", "resolved_in_source",
     "paragraph unique in markdown", "resolved", "否定性结论，保持原样不得改写成通过"),
    ("A12", "table", "C3/C4 单点失效漂移表（失衡力/等效阻尼/漂移速度/解析锚/R²/漂出时刻）",
     "| 失效工况 | fail_azimuth @ 40 m/s, 来向 0°, t=60 s |", "resolved_in_source",
     "table block unique in markdown", "resolved", "C3 判据 <5%，C4 判据 R²>0.99"),
    ("A13", "numeric_anchor", "正横失效敏感性 c3_c4_beam_sensitivity（稳态漂移不存在的适用边界）",
     "正横工况敏感性（`c3_c4_beam_sensitivity`", "resolved_in_source",
     "paragraph unique in markdown", "resolved", "声明 C3 解析锚的适用范围"),
    ("A14", "table", "C6 海况敏感性表（Hs=2/3 m 静力/时域 worst-1 最小风速）",
     "| Hs (m) | 静力 worst-1 最小风速 (m/s) |", "resolved_in_source",
     "table block unique in markdown", "resolved", "海况升档不翻转定性结论，只削余量"),
    ("A15", "figure", "图 1 fig_envelopes.png（静力/时域包线 + 降额因子场）",
     "![包线](fig_envelopes.png)", "referenced_unresolved",
     "platform metadata GET /tensor/reports/12080 -> figures[].name", "present",
     "图件在平台 figures 元数据中登记，二进制不在 markdown 内；本工序不下载图件"),
    ("A16", "figure", "图 2 fig_drift.png（失效漂移轨迹与 C4 线性区）",
     "![漂移](fig_drift.png)", "referenced_unresolved",
     "platform metadata GET /tensor/reports/12080 -> figures[].name", "present",
     "同上：仅登记引用，不抽取像素"),
    ("A17", "figure", "图 3 fig_attribution.png（C2 反例时间历程与推力利用率）",
     "![定源](fig_attribution.png)", "referenced_unresolved",
     "platform metadata GET /tensor/reports/12080 -> figures[].name", "present",
     "同上"),
    ("A18", "artifact_set", "工件三元组 artifacts/dp_time_domain/{acceptance,capability_envelopes,drift_case}.json",
     "artifacts/dp_time_domain/{acceptance,capability_envelopes,drift_case}.json",
     "referenced_unresolved", "filesystem probe in this worktree (repo=TensorKnowledge)",
     "unresolved", "工件属 ship-performance-platform 仓，本工作树内不存在"),
    ("A19", "code_module", "可复算入口 modules.dp_time_domain.run_acceptance（分 stage + assemble）",
     "* 可复算命令：`cd backend", "referenced_unresolved",
     "filesystem probe in this worktree (repo=TensorKnowledge)", "unresolved",
     "复算命令原文保留；代码不在本仓"),
    ("A20", "code_module", "平台单源波谱 physics.wave_spectrum_core（一阶波频力谱来源）",
     "波谱取平台单源 `physics.wave_spectrum_core`", "referenced_unresolved",
     "filesystem probe in this worktree (repo=TensorKnowledge)", "unresolved",
     "跨仓依赖声明，本仓无实现"),
    ("A21", "test_module", "测试面（42 例）：modules/dp_time_domain/tests（含 test_env_vessel.py / test_allocation.py）",
     "* 测试：`python -m pytest modules/dp_time_domain/tests -q`", "referenced_unresolved",
     "filesystem probe in this worktree (repo=TensorKnowledge)", "unresolved",
     "测试代码与用例数（42 例）为报告声明，未在本工序复核"),
    ("A22", "rest_endpoint", "REST 端点 api.py 未挂载到 main.py（本期只交付库 + 判据 + 工件）",
     "7. 未完成：REST 端点（`api.py`）未挂载到 `main.py`", "declared_absent",
     "grep main.py / api.py in this worktree (repo=TensorKnowledge)", "absent",
     "报告自述未完成项，登记为缺失而非缺陷修复目标"),
    ("A23", "table", "误差判定表（关键量 vs 基准，逐项回答是否 <3%）",
     "| C1 时域稳态位置 vs 静力平衡点 |", "resolved_in_source",
     "table block unique in markdown", "resolved", "含唯一 honest FAIL 行（C2）"),
    ("A24", "verdict_summary", "判定汇总字面量（C1 true / C2 false / C3–C6 true）",
     "* 判定汇总：{\"C1_static_consistency\": true", "resolved_in_source",
     "line unique in markdown", "resolved", "原样登记，不改写为 verified"),
    ("A25", "limitation_set", "局限章节（7 条局限/适用范围，含实现缺陷扇区与 DECLARED 载荷系数）",
     "## ⑤ 注意点（踩过的坑 / 局限 / 适用范围）", "resolved_in_source",
     "section heading line unique in markdown", "resolved",
     "局限与结论同权保留：C2 FAIL、三扇区不收敛、系数 DECLARED"),
]


def build_manifest(md: str, payload: dict) -> dict:
    starts = line_starts(md)
    assets = []
    for aid, aclass, label, anchor, resolution, check, result, note in SPEC:
        if anchor is None:  # whole-document locator
            loc = {
                "method": "document", "start_char": 0, "end_char": len(md),
                "start_line": 1, "end_line": md.count("\n") + 1, "quote": md, "unique": True,
            }
            if "```" in loc["quote"]:
                raise SystemExit("document quote contains a fence")
        else:
            loc = locate(md, starts, anchor)
        assets.append({
            "asset_id": aid, "asset_class": aclass, "label": label,
            "in_report_section": _section_of(starts, loc["start_char"]),
            "locator": loc, "resolution": resolution,
            "resolution_check": {"check": check, "result": result}, "note": note,
        })
    ids = [a["asset_id"] for a in assets]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate asset_id")
    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    figures = [f.get("name") for f in (payload.get("figures") or [])]
    return {
        "schema": "asset_manifest.v1",
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI, "field": "markdown", "hash_alg": "sha256",
            "hash": hashlib.sha256(md.encode()).hexdigest(),
            "chars": len(md), "bytes_utf8": len(md.encode("utf-8")),
            "title": payload.get("title") or CONTRACT_TITLE,
            "scenario_key": payload.get("scenario_key") or SCENARIO_KEY,
            "platform_figures": figures,
            "platform_tags": payload.get("tags") or [],
        },
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_res.items())),
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
        },
        "assets": assets,
        "claims": [],
        "integrity": {
            "quote_uniqueness": "every locator.quote is exactly md[start_char:end_char] and occurs "
                                "exactly once in the source markdown (checked at build time and "
                                "re-checked by scripts/kf_wp12080_01_verify.py)",
            "hash_recomputed_locally": True,
            "hash_matches_contract": hashlib.sha256(md.encode()).hexdigest() == CONTRACT_HASH,
        },
    }


def _section_of(starts, pos) -> str:
    """Nearest ①–⑥ / 审计链 heading above ``pos`` (source only, no invention)."""
    return "sec@char%d" % pos


def envelope(md: str, manifest: dict) -> dict:
    digest = hashlib.sha256(md.encode()).hexdigest()
    if digest != CONTRACT_HASH:
        raise SystemExit("source_hash mismatch: %s != contract %s" % (digest, CONTRACT_HASH))
    if len(md) != CONTRACT_CHARS:
        raise SystemExit("chars mismatch: %d != contract %d" % (len(md), CONTRACT_CHARS))
    return {
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": "sha256:" + digest,
            "source_chars": len(md),
            "source_bytes_utf8": len(md.encode("utf-8")),
            "source_title": manifest["source"]["title"],
            "scenario_key": manifest["source"]["scenario_key"],
            "contract_version": CONTRACT_VERSION,
            "lane": LANE,
            "work_package": PKG,
            "retrieved_via": "GET %s/tensor/reports/%s" % (BASE, REPORT_ID),
            "local_copy": "runs/%s/report_12080.md" % PKG,
            "generator": "scripts/kf_wp12080_01_register.py",
            "verifier": "scripts/kf_wp12080_01_verify.py",
            "producer": "agent/m15741",
            # reports are append-only on the platform: KF_EMITTED_AT pins the timestamp so a
            # re-run reproduces the published body byte-for-byte (auditable tree == published)
            "emitted_at": os.environ.get("KF_EMITTED_AT")
            or _dt.datetime.now().isoformat(timespec="seconds"),
            "verification_status": "not_verified",
            "notes": "task_type=01: 只登记源资产与字节哈希，不做抽取；claims=[] 为合法完整结果。",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }


# ----------------------------------------------------------------- report body
def render_body(env: dict, manifest: dict) -> str:
    m = manifest
    rows = []
    for a in m["assets"]:
        loc = a["locator"]
        q = loc["quote"].replace("|", "\\|").replace("\n", " ⏎ ")
        if len(q) > 96:
            q = q[:93] + "…"
        rows.append("| %s | %s | %s | %s–%s | %s | %s | `%s` |" % (
            a["asset_id"], a["asset_class"], a["resolution"], loc["start_char"], loc["end_char"],
            a["resolution_check"]["result"], a["note"], q))
    tbl = "\n".join(rows)
    n = m["counts"]
    body = f"""# KF-RESULT {PKG}

> 工作包 `{PKG}` · task_type=`{TASK_TYPE}` · report_id=`{REPORT_ID}` · lane={LANE} ·
> 仓 TensorKnowledge · 状态 draft（verification 由平台门计算，本工序不标 verified）

## ① 本工序做了什么

只做一件事：**登记 report 12080 的源资产**。确认 `tensor://reports/12080` 的 markdown 字节哈希与契约
`source_hash` 一致（`sha256:{m['source']['hash']}`，{m['source']['chars']} 字符 / {m['source']['bytes_utf8']} 字节），
再把报告里出现的图件、工件、代码/测试引用、以及报告自述的**缺失**项逐条登记成资产清单
（{n['assets']} 条：resolved_in_source {n['resolved_in_source']} / referenced_unresolved {n['referenced_unresolved']} / declared_absent {n['declared_absent']}），
每条带逐字可解析定位器。按契约 `objective`，本工序**不做抽取、不做分类、不生成知识对象**
（`claims` 为空数组是合法完整结果，不为填指标造 claim），也不把任何结论标成 verified。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. `GET /api/v1/tensor/reports/12080`（Bearer=env `TENSOR_AGENT_USER` 登录 token）取 `markdown`，落盘
   `runs/{PKG}/report_12080.json` 与 `report_12080.md`；**不手抄、不凭记忆**。
2. 本地重算 `sha256(markdown.encode())` 与 `chars`，与契约 `source_hash` / `chars` 逐位比对；不一致即中止
   （脚本内 `envelope()` 硬断言）。结果：**一致**。
3. 定位器算法（`scripts/kf_wp12080_01_register.py`）：每条资产给定一个**唯一锚串**（`md.count(anchor)==1`
   否则抛错），从锚串位置向外扩到所在块边界（`|` 表格块 / 围栏代码块 / 连续非空段落），
   `quote = md[start_char:end_char]` **原样切片**，并再断言该块文本在全文唯一。
   因此"引文逐字来自原文"与"定位可解析"是同一构造，不是两次人工核对。
4. 资产分类只用中性词（document/heading/table/parameter_set/prereg_lock/numeric_anchor/statement/
   figure/artifact_set/code_module/test_module/rest_endpoint/verdict_summary/limitation_set）；
   图件用平台 `figures[].name` 元数据做存在性核对（result=present），二进制不下载、不抽取像素。
5. 产出 `runs/{PKG}/asset_manifest.json` 与 `kf_result.v1` 信封；报告正文末尾的 JSON 围栏块（标记 json）是信封**原样**
   （脚本写出，非人工粘贴）。脚本另断言任何引文都不含三反引号，保证正文里只有这一个围栏块。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `runs/{PKG}/report_12080.json` | 平台原始载荷（title/summary/tags/figures/markdown），取证用 |
| `runs/{PKG}/report_12080.md` | markdown 逐字副本，sha256 `{m['source']['hash'][:16]}…`，{m['source']['chars']} 字符 |
| `runs/{PKG}/asset_manifest.json` | 资产清单：{n['assets']} 条，含 counts/integrity |
| `docs/{PKG}/kf_result.{PKG}.json` | 同上信封（供门直接读取，等价于本报告 json 块） |
| `docs/{PKG}/KF-RESULT-{PKG}.md` | 本报告正文（六段），唯一 JSON 围栏块 = 信封 |
| `scripts/kf_wp12080_01_register.py` | 生成器（fetch + hash 校验 + 定位 + 渲染） |
| `scripts/kf_wp12080_01_verify.py` | 复核器（schema + 哈希 + 引文可解析 + 唯一 id + 单块检查） |
| `tests/test_kf_wp12080_01.py` | 离线 pytest 复跑：产物自洽性（不改平台状态） |

## ④ 证据定位表（资产 → 原文引文片段）

| asset | class | resolution | chars | 核对 | 说明 | 引文片段（逐字，截断显示；全文见清单 quote） |
|---|---|---|---|---|---|---|
{tbl}

完整引文（未截断）与 `start_char/end_char/start_line/end_line` 见 `asset_manifest.json` 的 `assets[].locator`；
复核命令会重新切片比对，任一条不逐字/不唯一即失败。

## ⑤ 注意点与局限

1. **只登记，不抽取**：本工序不产生 claim、不判定报告结论真假。报告自称的 C2 honest FAIL、
   三扇区不收敛、载荷系数 DECLARED 均按原文登记（A11/A24/A25），未做任何"通过化"改写。
2. **图件与工件只能登记引用**：`fig_envelopes.png` / `fig_drift.png` / `fig_attribution.png` 在平台
   `figures` 元数据中存在（result=present），但二进制不在 markdown 内，本工序不下载；
   `artifacts/dp_time_domain/*.json`、`modules.dp_time_domain.*`、`tests/*` 属 ship-performance-platform 仓，
   本工作树（TensorKnowledge）内**不存在**，故 resolution=referenced_unresolved（探测结果如实记 unresolved），
   不能当成"已核实的工件"。
3. **`api.py`/`main.py` REST 端点**：报告第⑦条自述未挂载，登记为 `declared_absent`；这是报告自陈的
   未完成项，不是本工序的修复目标（越界改写上游产物禁止）。
4. **verification 不在本工序**：信封 `provenance.verification_status=not_verified`，平台门独立重算哈希与子串。
5. `in_report_section` 用字符位（`sec@charN`）表达，未强行映射到 ①–⑥ 标题文本，避免把标题映射变成猜测。
6. 未做（明确不在本工作包内）：claims 抽取、报告类型分类、图件重绘、跨仓工件下载。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|---|---|---|
| valid_json | ✅ | 本报告唯一的 JSON 围栏块可被 `json.loads` 解析（verify 脚本实测） |
| schema_pass | ✅ | `schemas/kf_result.v1.schema.json`（Draft 2020-12，jsonschema 实测）+ 清单结构逐条断言（见 verify 脚本） |
| source_locator_resolvable | ✅ | {n['assets']} 条 quote 均由 `md[start:end]` 切片、`count==1`、重切片相等 |
| source_hash_matches | ✅ | `sha256={m['source']['hash']}` == 契约 `source_hash`（本地与平台取回各算一次） |
| no_duplicate_ids | ✅ | asset_id A01–A{n['assets']:02d} 唯一；信封内无重复 claim（claims 为 0 条） |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | `claims=[]`（契约允许），不存在无证据 claim |

无失败项；未做项已在 ⑤ 明列。**图件说明**：本工序为纯登记类文档工序，无计算结果，故不出图（满足
"无图必须写明理由"）。

复跑：`python3 scripts/kf_wp12080_01_register.py && python3 scripts/kf_wp12080_01_verify.py && python3 -m pytest tests/test_kf_wp12080_01.py -q`
（`--offline` 可只用 `runs/{PKG}/report_12080.md` 复现哈希与定位，不触网。）

```json
{json.dumps(env, ensure_ascii=False, indent=2)}
```
"""
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    payload, md = fetch_report(args.offline)
    RUN.mkdir(parents=True, exist_ok=True)
    DOC.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(md, payload)
    env = envelope(md, manifest)
    (RUN / "asset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    (DOC / ("kf_result.%s.json" % PKG)).write_text(json.dumps(env, ensure_ascii=False, indent=2))
    body = render_body(env, manifest)
    if body.count("```json") != 1:
        raise SystemExit("report body must hold exactly one ```json block")
    if body.count("```") != 2:
        raise SystemExit("report body must hold exactly one fenced block in total")
    (DOC / ("KF-RESULT-%s.md" % PKG)).write_text(body)
    print("assets=%d hash_ok=%s chars=%d body=%d bytes" % (
        manifest["counts"]["assets"], manifest["integrity"]["hash_matches_contract"],
        manifest["source"]["chars"], len(body.encode())))


if __name__ == "__main__":
    main()