#!/usr/bin/env python3
"""Publish the wp-7473-01 delivery report (six-section, paper-grade) to the platform.

The kf_result JSON block is read verbatim from docs/kf/wp-7473-01/kf_result.json, so the
single ```json block in the report body is byte-identical to the artifact on disk.
All quoted evidence is sliced out of the committed source snapshot by line number.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PKG_DIR = REPO / "docs" / "kf" / "wp-7473-01"
MANIFEST = PKG_DIR / "asset_manifest.json"
RESULT = PKG_DIR / "kf_result.json"
SNAPSHOT = PKG_DIR / "source_markdown.md"
VERDICT = PKG_DIR / "verification.json"
FIGURE = PKG_DIR / "fig_asset_resolution.png"
RECEIPT = PKG_DIR / "pub_receipt.json"

PKG = "wp-7473-01"
REPORT_ID = "7473"
EXPECTED_HASH = "c3b3d0954d289cf1f7849f83889e995c71c39bbc15122ddf9f823f5d698d0f6b"
MISSION_ID = 15596
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")

# Evidence lines picked by number from the source snapshot (quotes sliced, never retyped).
EVIDENCE_LINES = [3, 4, 6, 7, 41, 45, 59, 72, 106, 128, 129, 130, 131]


def _req(url, token=None, data=None):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    d = _req(BASE + "/auth/login", data=json.dumps({"username": USER, "password": PASS}).encode())
    return d.get("access_token") or d.get("token")


def cell(text: str) -> str:
    """One-line, pipe-free table cell (markdown table integrity)."""
    t = text.replace("|", "\\|").replace("\n", " ").strip()
    return t if len(t) <= 160 else t[:157] + "…"


def main() -> int:
    md_src = SNAPSHOT.read_text(encoding="utf-8")
    digest = hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()
    assert digest == EXPECTED_HASH, digest
    lines = md_src.split("\n")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    verdict = json.loads(VERDICT.read_text(encoding="utf-8"))
    result_block = RESULT.read_text(encoding="utf-8").strip()

    counts = manifest["counts"]
    want = "|".join(str(lines[n - 1]) for n in EVIDENCE_LINES)
    assert "```" not in want, "evidence lines must not contain code fences"

    ev_rows = "\n".join(
        "| L%d | `%s` |" % (n, cell(lines[n - 1])) for n in EVIDENCE_LINES
    )

    fig_b64 = base64.b64encode(FIGURE.read_bytes()).decode()
    checks_rows = "\n".join(
        "| `%s` | %s | %s |" % (k, "✅" if v["pass"] else "❌", cell(v["detail"]))
        for k, v in verdict["checks"].items()
    )

    body = f"""# KF-RESULT {PKG} — report {REPORT_ID} 资产登记

> 工序：`01-asset-registration`（lane C）。只登记、不抽取、不生成知识对象、不打 `verified`。
> 源：`tensor://reports/{REPORT_ID}` 字段 `markdown`，**sha256 本地重算 = 契约值**
> `sha256:{EXPECTED_HASH}`，{manifest['source']['chars']} chars / {manifest['source']['bytes_utf8']} bytes(utf-8) / {manifest['source']['lines']} 逻辑行。
> 产线纪律：零手抄——本报告所有引文按行号从快照切片，产物中每个 quote 都是源字节的逐字子串。

## ① 本工序做了什么

对 report_id=7473（TensorLBM 湍流槽道求解器验证欠账清偿 R1）做**源资产登记**：确认报告身份与 markdown 字节哈希、
把报告里可定位的代码/测试/工件/图/文献/表**逐一定位并分类**，给出每一条的解析状态（可解析 / 引用未解析 / 报告声明不存在），
不做文本抽取、不造 claim。产出 `asset_manifest.json`（{counts['assets']} 条资产，claims=0）与 `kf_result.json`（交付信封）。

关键登记结论：

* 源哈希与契约一致（{EXPECTED_HASH[:16]}…），字符数 {manifest['source']['chars']} 与契约 `chars: 5942` 一致，标题/`scenario_key` 与契约逐字一致。
* **平台只存图元数据、不存图字节**：报告 record 的 `figures` 有 2 条（name+caption），但
  `GET /tensor/reports/7473/figures/{{name}}` 两条都返回 **HTTP 404**，因此 2 张图的字节哈希**不可声明**（登记为 `referenced_unresolved`）。
* {counts['distinct_referenced_paths']} 个不同路径被引用；按出现位置展开为 {counts['assets']} 条资产（occurrence-level 身份 = (path, 行号)）。
* 报告自己声明的缺口被如实登记为 `declared_absent`：合入时无 pytest/无验证文档（L4）、Re_tau=180/395 壁面湍流验证未做（L106）；
  以及 `referenced_unresolved` 的开放缺陷：`wall_exchange` 聚合口径未修。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. 取源：`GET /api/v1/tensor/reports/{REPORT_ID}`（Bearer token），**只取 `markdown` 字段**，UTF-8 编码后算 sha256；与契约
   `source_hash` 逐字比对。同一份字节写成本地快照 `docs/kf/wp-7473-01/source_markdown.md`（离线可复算）。
2. 登记器 `scripts/kf/build_asset_manifest_7473.py`（build/verify/result 三动作）：
   * 文件引用：正则扫 markdown 里的**反引号路径**（`.py/.json/.png/.md/.txt/.csv`）与**仓库根目录路径**（`src/ tests/ benchmarks/ artifacts/` 等白名单前缀）。
     白名单是必须的：不加会把行内数学（`dU/dt = a`、`2u_max/Re_tau_twin`）误登记成 30 条假目录资产（首版就踩了，见 §⑤）。
   * 每条的 locator = `(行号, 整行逐字 quote, 字符区间, 该 quote 在全文是否唯一)`，quote 由切片得到而非手打。
   * 解析判定按**归属仓**：`src/ tests/ benchmarks/ artifacts/` 属 TensorLBM，不在本交付工作树内→`referenced_unresolved`；
     **绝不拿 TensorKnowledge 自己的 `tests/` 去"解析"它**（首版曾把 `tests/` 判成 resolved，已修并写成回归测试）。
   * 图资产单独探针：对 record `figures` 逐条 `GET .../figures/{{name}}`，记录 http_status/bytes/sha256；非 200 即不声明字节。
3. 校验器 `verify`（同一脚本）：用 JSON Schema + 逐条 locator 回解 + 哈希重算 + id 唯一性 + claim 纪律，输出 `verification.json`。
4. 离线回归 `tests/test_kf_wp_7473_01.py`（11 条）：不依赖平台，校验快照哈希、locator 可解析、引文逐字、词汇封闭、跨仓误解析回归、kf_result 与 manifest 一致。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-7473-01/asset_manifest.json` | {counts['assets']} 条资产；by_resolution {json.dumps(counts['by_resolution'], ensure_ascii=False)}；claims=0；sha256 `{result['outputs']['asset_manifest.json']['sha256'][:16]}…` |
| `docs/kf/wp-7473-01/kf_result.json` | 交付信封（package_id/task_type/report_id/provenance/outputs/claims），即本报告唯一 json 块 |
| `docs/kf/wp-7473-01/source_markdown.md` | 源字节快照，sha256 = `{EXPECTED_HASH}`（离线复算锚） |
| `docs/kf/wp-7473-01/verification.json` | 7 项 acceptance 自检结果 + manifest sha256 |
| `docs/kf/wp-7473-01/asset_manifest_7473.schema.json` | 本包 manifest 的本地 JSON Schema（平台 schema 优先） |
| `docs/kf/wp-7473-01/fig_asset_resolution.png` | 图 1：资产类×解析状态构成 |
| `scripts/kf/build_asset_manifest_7473.py` | 登记器 + 校验器（只碰 report 7473） |
| `scripts/kf/plot_7473_manifest.py` | 图 1 生成器（从 manifest 直读，无手抄） |
| `tests/test_kf_wp_7473_01.py` | 11 条离线/在线回归 |

## ④ 证据定位表（字段 → 原文引文片段，逐字，按行号切片）

| 源行 | 原文引文（逐字，来自 `source_markdown.md`） |
|---|---|
{ev_rows}

locator 语义：`markdown_line`（行号 + 整行 quote + 字符区间 + 唯一性），`markdown_document`（全文，0..{manifest['source']['chars']}），
`report_field`（record 的 `figures[i]`）。全量 {counts['assets']} 条 locator 见 manifest，逐条已在 `verify` 中回解。

图 1（`fig_asset_resolution.png`）由图注入，数值全部来自 manifest：合计 {counts['assets']} 条，
resolved_in_source {counts['by_resolution'].get('resolved_in_source',0)} / referenced_unresolved {counts['by_resolution'].get('referenced_unresolved',0)} / declared_absent {counts['by_resolution'].get('declared_absent',0)}。

## ⑤ 注意点与局限（含踩坑，不粉饰）

1. **跨仓误解析（已修）**：首版把 `tests/`、`tests/test_turbulent_channel3d.py` 判成 `resolved_in_source`，因为交付工作树里
   TensorKnowledge 自己也有 `tests/`。这会让下游误以为 TensorLBM 的测试文件已被核验。已改为按归属仓判定，并写回归
   `test_foreign_repo_paths_are_not_falsely_resolved`。
2. **行内数学被当成目录（已修）**：`dU/dt`、`h/`、`Re_tau/`、`2u_max/` 等被目录正则捕获，首版产出 30 条假资产（54→24 条真资产）。
   加仓库根前缀白名单后总资产 {counts['assets']} 条。
3. **图字节不可得**：两张 png 的平台端点为 404，caption 只是元数据。本工序不猜图内容、不复制字节，故 2 条图资产停在
   `referenced_unresolved`——这是**能力边界**而非失败。
4. **TensorLBM 侧一切路径（src/tests/artifacts/benchmarks）均未核验**：它们不在本交付工作树范围内，登记为
   `referenced_unresolved`。"未核验"≠"不存在"，下游若要落到文件级证据必须去 TensorLBM 仓复核。
5. **文献锚只有名字级**：Guo 1993 / Ladd / MKM DNS / Reichardt 在报告里没有 DOI/URL，登记为未解析，未做外部检索。
6. claims 为空是**契约允许**（`objective.classify_report_type=false`，无抽取指令），不是漏做；本工序拒绝为凑指标造 claim。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 细节 |
|---|---|---|
{checks_rows}

`all_pass = {verdict['all_pass']}`，自检失败项：{ '无' if verdict['all_pass'] else '见上表 ❌' }。

复跑（一键，含登记+校验+信封+离线测试）：

```bash
cd <worktree> && python3 scripts/kf/build_asset_manifest_7473.py build verify result \\
  && python3 -m pytest -q tests/test_kf_wp_7473_01.py
```

只读体检（不写文件）：`python3 -m pytest -q tests/test_kf_wp_7473_01.py`（无平台凭据时在线用例自动 skip）。

### 交付信封（kf_result，唯一 json 块）

```json
{result_block}
```
"""

    figs = [{
        "name": "fig_asset_resolution.png",
        "caption": "report %s 资产登记构成（%d 条资产）：按 asset_class × 解析状态，右图为解析状态汇总；数值直读 asset_manifest.json"
                   % (REPORT_ID, counts["assets"]),
        "png_base64": fig_b64,
    }]

    token = login()
    payload = {
        "title": "KF-RESULT %s" % PKG,
        "summary": (
            "wp-7473-01 资产登记：report 7473 markdown sha256 本地重算与契约一致（%d chars）；"
            "登记 %d 条资产（%d 个不同路径），claims=0；发现平台 figure 端点对两张图均 404（图字节不可声明），"
            "并修正两处假解析（跨仓 tests/、行内数学误判为目录）。"
            % (manifest["source"]["chars"], counts["assets"], counts["distinct_referenced_paths"])
        ),
        "scenario_key": "tensorlbm/turbulent-channel3d-verification-r1/wp-7473-01",
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:%s" % PKG, "asset-registration", "TensorKnowledge", "lane-C", "report-7473"],
        "markdown": body,
        "figures": figs,
    }
    d = _req(BASE + "/tensor/reports", token=token, data=json.dumps(payload).encode())
    receipt = {
        "published_at": datetime.now(timezone.utc).isoformat(),
        "endpoint": BASE + "/tensor/reports",
        "response": d,
        "title": payload["title"],
        "tags": payload["tags"],
        "markdown_sha256": hashlib.sha256(body.encode()).hexdigest(),
        "markdown_chars": len(body),
        "kf_result_sha256": hashlib.sha256(RESULT.read_bytes()).hexdigest(),
        "source_hash": "sha256:" + EXPECTED_HASH,
        "figure_sha256": hashlib.sha256(FIGURE.read_bytes()).hexdigest(),
    }
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False)[:600])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())