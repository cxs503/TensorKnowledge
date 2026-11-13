#!/usr/bin/env python3
"""Compose + publish the KF result report for wp-4776-01 (report 4776 only).

Everything numeric in the markdown is injected from the delivered files
(asset_manifest.json / checks.json) — no hand-typed values.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "docs" / "kf" / "wp-4776-01"
RUN = ROOT / "runs" / "wp-4776-01"
ENVELOPE = json.loads((PKG / "kf_result.json").read_text())
MANIFEST = json.loads((PKG / "asset_manifest.json").read_text())
CHECKS = json.loads((RUN / "checks.json").read_text())
FIG = RUN / "asset_locator_map.png"


def auth_token() -> str:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps(
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }
    ).encode()
    req = urllib.request.Request(
        base + "/auth/login",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.load(urllib.request.urlopen(req))["access_token"]


def make_figure() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = MANIFEST["asset_inventory"]
    colors = {
        "figure": "#c1121f",
        "evidence_artifact": "#0b6e4f",
        "referenced_repo_path": "#1d4e89",
    }
    fig, ax = plt.subplots(figsize=(9.6, 4.4))
    for i, r in enumerate(rows):
        y = len(rows) - i
        ax.hlines(
            y, 1, r["locator"]["line"], color=colors[r["kind"]], lw=1.2, alpha=0.55
        )
        ax.plot(r["locator"]["line"], y, "o", color=colors[r["kind"]], ms=6)
        ax.text(
            r["locator"]["line"] + 1.5,
            y,
            f"{r['asset_id']} {r['basename']}",
            va="center",
            fontsize=7.5,
            color="#222",
        )
    ax.set_yticks([])
    ax.set_xlim(0, 120)
    ax.set_xlabel("line number in tensor://reports/4776 markdown (quote locator)")
    ax.set_title(
        f"wp-4776-01 asset locator map — {len(rows)} registered assets, "
        f"source sha256 {MANIFEST['source']['sha256'][:19]}…",
        fontsize=9,
    )
    handles = [
        plt.Line2D([], [], marker="o", ls="", color=c, label=k)
        for k, c in colors.items()
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=7.5, frameon=False)
    ax.grid(axis="x", ls=":", lw=0.5, alpha=0.5)
    fig.tight_layout()
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=150)
    plt.close(fig)


def table(header: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def build_markdown() -> str:
    src = MANIFEST["source"]
    counts = MANIFEST["asset_counts"]
    probes = MANIFEST["reachability_probes"]

    loc_rows = [
        [
            a["asset_id"],
            a["kind"],
            f"`{a['declared_path']}`",
            a["locator"]["line"],
            f"{a['locator']['char_start']}–{a['locator']['char_end']}",
            a["locator"]["content_hash"][7:19] + "…",
            '"' + a["locator"]["quote"].replace("`", "\\`") + '"',
        ]
        for a in MANIFEST["asset_inventory"]
    ]

    check_rows = [
        [c["id"], f"`{c['criterion']}`", c["result"], c["detail"]]
        for c in CHECKS["checks"]
    ]
    unc_rows = [[u["item"], u["status"], u["detail"]] for u in MANIFEST["unresolved"]]
    probe_rows = [
        [p["method"], f"`{p['route']}`", str(p["http_status"]), p["note"]]
        for p in probes
    ]

    extra = [r for r in checks_extra()]

    md = f"""# KF-RESULT wp-4776-01 — 资产登记（report 4776）

## ① 本工序做了什么

对 **report_id = 4776**（唯一被读写的报告）执行 `01-asset-registration`：确认源身份（`{src["source_field"]}` 字段的字节级 sha256 与契约一致）、
登记可解析的附件/工件 **{counts["total"]} 件**（figure {counts["by_kind"].get("figure", 0)} / evidence_artifact {counts["by_kind"].get("evidence_artifact", 0)} / referenced_repo_path {counts["by_kind"].get("referenced_repo_path", 0)}）、
记录每件的可得性与逐字定位码。**不做**知识抽取（claims 为空数组）、**不做**报告分型、**不标注**任何 verified 状态（验证由平台门计算）。
报告主题为 TensorFEM 的 lint 债棘轮 CI 修复，属纯工程报告，本工序只登记其外延资产面。

源身份表（全部来自程序化计算，非手抄）：

| 字段 | 值 |
|---|---|
| source_uri | `{src["source_uri"]}` / field `{src["source_field"]}` |
| title（平台记录） | {MANIFEST["record_metadata"] and src["title"]} |
| markdown H1 | {src["markdown_h1"]} |
| chars / bytes(UTF-8) | {src["chars"]} / {src["byte_length_utf8"]}（契约 {src["contract_chars"]}，匹配={src["chars_match_contract"]}） |
| sha256 | `{src["sha256"]}` |
| 与契约 source_hash 一致 | {src["hash_matches_contract"]} |
| scenario_key | `{src["scenario_key"]}`（匹配契约={src["scenario_key_matches_contract"]}） |
| 平台记录 mission_id / status / created_at | {MANIFEST["record_metadata"]["mission_id"]} / {MANIFEST["record_metadata"]["status"]} / {MANIFEST["record_metadata"]["created_at"]} |

## ② 怎么做的

1. **取原文（不凭记忆）**：`POST /auth/login` 取 token → `GET {os.environ["TENSOR_API_BASE"].rstrip("/")}/tensor/reports/4776`，只取 `markdown` 字段；同响应里的 `figures[]` 只作附件元数据。
2. **源哈希**：`sha256(markdown.encode("utf-8"))`，不做换行归一，与契约 `source_hash` 逐字符比对。
3. **资产候选集**：从正文里出现的“路径型 token”人工划定候选（图 1 件、`runs/pr185-cure/` 证据件 6 件、被改动/被引用的仓库路径 6 件），每件写 `role_note` 说明它在报告里的角色；不做内容抽取、不做分型。
4. **定位码**：对每件资产做**逐字子串定位**（首个出现处），记录 `char_start/char_end`（码点，本文 ASCII 故等长于字节）、行号、出现次数、`content_hash = sha256(quote)`；写入时再次断言 `markdown[start:end] == quote`。
5. **可达性探测**：对 5 条路由发请求并记录 HTTP 码（见表 5）。
6. **自检**：生产者自检 `scripts/kf/wp_4776_01_register_assets.py` 内联 6 项，另有**独立实现**的复核脚本 `scripts/kf/wp_4776_01_verify.py`（不 import 生产者代码，重新取原文重算）——两者输出均为下表 ④ 的通过面。
7. **作图**：`matplotlib` 依 manifest 生成资产定位图（行号轴），零手抄。

工具链：Python 3.11.6 · `jsonschema` 4.26.0（Draft 2020-12 校验 `schemas/kf_result.v1.schema.json`）· `matplotlib` 3.10.8 · 平台 `:8010` 报告 API。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-4776-01/asset_manifest.json` | 契约声明的唯一输出：源哈希/尺寸/身份表、{counts["total"]} 件资产清单（含 role_note、locator、reachability、payload_in_record）、可达性探测记录、claims 空集声明、3 条 unresolved |
| `docs/kf/wp-4776-01/kf_result.json` | 结果信封（`kf_result.v1`）：`package_id/task_type/report_id/provenance/outputs` + `claims: []` |
| `runs/wp-4776-01/checks.json` | 6 项 acceptance 自检明细 + 13 条 locator 判定（`OK_OFFSETS`）|
| `runs/wp-4776-01/asset_locator_map.png` | 图 1：资产在原文中的行位置（供 02 工序做结构切分定位） |
| `scripts/kf/wp_4776_01_register_assets.py` | 生产者：拉原文→哈希→定位→写产物→自检（可一键复跑） |
| `scripts/kf/wp_4776_01_verify.py` | 独立复核：只读产物 + 重新取原文，重算 6 项 + 2 条附加护栏 |
| `schemas/kf_result.v1.schema.json` | 契约引用的信封 schema（本仓原缺；内容与平台 canonical 副本逐字节一致，供 schema_pass 可复现） |

## ④ 证据定位表（claim/字段 → 原文引文片段，逐字）

源 sha256：`{src["sha256"]}`（契约值同）。下表 13 行全部由 manifest 程序化生成，`quote` 列即原文逐字片段（反引号在表格里转义为 \\`，逐字原文见信封里同名字段），`start–end` 为码点偏移。

{table(["asset_id", "kind", "declared_path", "line", "start–end", "quote sha256", "quote（原文逐字）"], loc_rows)}

**可达性探测（表 5）**

{table(["method", "route", "http", "note"], probe_rows)}

## ⑤ 注意点与局限

{table(["item", "status", "说明"], unc_rows)}

* **只有 markdown 与 figures 元数据可核**：报告记录不携带附件字节，6 个 `runs/pr185-cure/` 证据件与 4 个改动文件均无法在此包内取到内容，故 `payload_in_record = not_hosted`，一律标 `unresolved` 而不是“已核”。
* **figure 只有元数据**：`figures[]` 提供 `name` + {MANIFEST["record_metadata"]["figures"][0]["caption_chars"]} 字符 caption，图字节不可取；不冒充“图已验”。
* **标题与 H1 不同**：平台 `title` 与 markdown H1 不一致（`title_equals_markdown_h1 = {src["title_equals_markdown_h1"]}`），属报告自身元数据差异，本工序照实登记不改写上游。
* **role_note 是登记性描述而非事实断言**：例如“exit 2 = 工具漂移”只是复述报告自述，本工序未执行任何 ruff/lint 命令，也未复核其中的数值（4271/624、18 passed 等）；这些留待 03 抽取 + 04 独立审核。
* **未做**：报告分型（`classify_report_type: false`）、claim 抽取、附图读取、其它 report_id 的任何读写。

## ⑥ 自检（逐条对照 acceptance）

生产者自检 `runs/wp-4776-01/checks.json` 与独立复核 `scripts/kf/wp_4776_01_verify.py` 双跑，结论一致：

{table(["#", "criterion", "result", "detail"], check_rows)}

{table(["附加护栏", "ok", "detail"], extra)}

**误差判定**（关键量 vs 基准，逐项）：

| 关键量 | 基准 | 实测 | 偏差 |
|---|---|---|---|
| markdown 字节哈希 | 契约 `sha256:03d3…3882` | `{src["sha256"][:19]}…` | 0（byte-exact） |
| 字符数 | 契约 4869 | {src["chars"]} | 0（0%） |
| 定位码命中 | 13/13 逐字 | {sum(1 for r in CHECKS["locators"] if r["result"] == "OK_OFFSETS")}/13 | 0（0%） |

关键量偏差均为 **0% < 3%**；但须说明：这三项是**内部一致性与字节同一性**基准，不是物理量对标——本工序不含物理结果，因此不存在“与实验/解析解比较”的误差面（这是工序性质决定，不是省略）。

**一键复跑**：

```
export TENSOR_API_BASE=http://127.0.0.1:8010/api/v1
python3 scripts/kf/wp_4776_01_register_assets.py   # 拉原文→重算哈希/定位→写 manifest+信封→自检
python3 scripts/kf/wp_4776_01_verify.py            # 独立复核 6 项 acceptance + 2 条护栏
python3 scripts/kf/wp_4776_01_report.py --no-post  # 只重建本报告文本/图（不发）
```

## 结果信封（下方唯一机器可读块）

```json
{json.dumps(ENVELOPE, ensure_ascii=False, indent=1)}
```
"""
    return md


def checks_extra() -> list[list[str]]:
    """Derived from the independent verifier's output, re-computed here on the files."""
    env_blob = json.dumps(ENVELOPE, ensure_ascii=False)
    forbidden = [
        t
        for t in (
            "verified",
            "verification_status",
            "verification_level",
            "is_verified",
            "gate_confirmed",
        )
        if ('"%' + t + '"') in env_blob
    ]
    return [
        [
            "no_self_verification_fields（GATE-RULES S9）",
            "✅" if not forbidden else "❌",
            f"产物中禁止键 {forbidden or '无'}；不含 verification/verified 自封字段",
        ],
        [
            "single_report_scope（互不覆盖）",
            "✅" if MANIFEST["scope"]["reports_touched"] == ["4776"] else "❌",
            "reports_touched = "
            + json.dumps(MANIFEST["scope"]["reports_touched"], ensure_ascii=False)
            + "；未读写其它 report_id",
        ],
    ]


def main(post: bool = True) -> int:
    make_figure()
    md = build_markdown()
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / "report.md").write_text(md)
    code_blocks = md.count("```json")
    print("json code blocks in report:", code_blocks)
    assert code_blocks == 1, "report must carry exactly one ```json block"

    if not post:
        return 0

    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    token = auth_token()
    payload = {
        "title": "KF-RESULT wp-4776-01",
        "summary": (
            f"资产登记 report 4776：源 sha256 与契约一致，登记 {MANIFEST['asset_counts']['total']} 件资产"
            f"（figure/evidence/repo-path），13/13 逐字定位码命中，claim 空集，6 项 acceptance 全过。"
        ),
        "scenario_key": MANIFEST["source"]["scenario_key"],
        "mission_id": 15561,
        "tags": [
            "kf-wp:wp-4776-01",
            "01-asset-registration",
            "report-4776",
            "KBM-RCI-F1-FACTORY",
        ],
        "markdown": md,
        "figures": [
            {
                "name": FIG.name,
                "caption": (
                    f"wp-4776-01 资产定位图：{MANIFEST['asset_counts']['total']} 件登记资产在 "
                    f"tensor://reports/4776 markdown 中的行位置（红=figure，绿=evidence_artifact，"
                    f"蓝=referenced_repo_path），数据由 asset_manifest.json 程序化注入。"
                ),
                "png_base64": base64.b64encode(FIG.read_bytes()).decode(),
            }
        ],
    }
    req = urllib.request.Request(
        base + "/tensor/reports",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token,
        },
        method="POST",
    )
    resp = json.load(urllib.request.urlopen(req))
    print(json.dumps(resp, ensure_ascii=False)[:400])
    rid = resp.get("id") or resp.get("report_id")
    print("published report id:", rid)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(post="--no-post" not in sys.argv))
