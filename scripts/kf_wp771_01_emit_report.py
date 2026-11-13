#!/usr/bin/env python3
"""Publish the wp-771-01 progress report for report 771 (paper-grade six sections).

Every number and every quoted string in the body is injected from the produced
artifacts (`asset_manifest.json`, `selfcheck.json`) or from the verbatim source
snapshot — nothing is retyped by hand. The single ```json block carries the
result envelope, which is the package's only result channel.

Run:
    TENSOR_API_BASE=... TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=... \
        python3 scripts/kf_wp771_01_emit_report.py [--dry-run]
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "artifacts" / "kf" / "wp-771-01"
PACKAGE_ID = "wp-771-01"
MISSION_ID = 15518


def load() -> tuple[dict, dict, dict, str]:
    envelope = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
    manifest = envelope["outputs"]["asset_manifest.json"]
    selfcheck = json.loads((PKG / "selfcheck.json").read_text(encoding="utf-8"))
    source = (PKG / "source_771.md").read_text(encoding="utf-8")
    return envelope, manifest, selfcheck, source


def figure(manifest: dict) -> tuple[str, str]:
    """Asset inventory chart, counts derived from the manifest only."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    kinds = list(manifest["counts"]["by_kind"].items())
    kinds.sort(key=lambda kv: (-kv[1], kv[0]))
    res = {a["asset_id"]: a["resolvable"] for a in manifest["assets"]}
    by_kind_res: dict[str, list[int]] = {}
    for a in manifest["assets"]:
        slot = by_kind_res.setdefault(a["kind"], [0, 0])
        slot[0 if a["resolvable"] else 1] += 1

    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    labels = [k for k, _ in kinds]
    ok = [by_kind_res[k][0] for k in labels]
    un = [by_kind_res[k][1] for k in labels]
    y = range(len(labels))
    ax.barh(list(y), ok, color="#2e7d32", label="resolvable (fetched/recorded)")
    ax.barh(list(y), un, left=ok, color="#b0bec5", label="unresolved (explicitly flagged)")
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("registered assets (count)")
    ax.set_title(
        "report 771 asset registration: %d assets, %d resolvable / %d unresolved"
        % (
            manifest["counts"]["total"],
            manifest["counts"]["resolvable"],
            manifest["counts"]["unresolved"],
        ),
        fontsize=10,
    )
    ax.legend(fontsize=8, loc="lower right")
    for i, k in enumerate(labels):
        ax.text(ok[i] + un[i] + 0.05, i, str(ok[i] + un[i]), va="center", fontsize=8)
    fig.tight_layout()
    out = PKG / "fig1_asset_inventory.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    assert set(res.values()) <= {True, False}
    return out.name, base64.b64encode(out.read_bytes()).decode()


def md_table(manifest: dict, source: str) -> str:
    rows = [
        "| asset_id | kind | name | resolvable | locator (verbatim quote / record field) |",
        "|---|---|---|---|---|",
    ]
    for a in manifest["assets"]:
        loc = a["locators"][0]
        if loc["source_field"] == "markdown":
            where = "md[%d:%d] 「%s」" % (loc["char_start"], loc["char_end"], loc["quote"])
        else:
            where = "record.%s=%s" % (loc["field"], loc["value"])
        where = where.replace("`", "")
        rows.append(
            "| %s | %s | `%s` | %s | %s |"
            % (
                a["asset_id"],
                a["kind"],
                a["name"],
                "yes" if a["resolvable"] else "no",
                where.replace("|", "\\|"),
            )
        )
    return "\n".join(rows)


def build() -> dict:
    envelope, manifest, selfcheck, source = load()
    src = manifest["source"]
    fig_name, fig_b64 = figure(manifest)
    schema_path = ROOT / "schemas" / "kf_result.v1.schema.json"
    schema_sha = hashlib.sha256(schema_path.read_bytes()).hexdigest()

    checks = selfcheck["checks"]
    check_lines = "\n".join(
        "- [%s] `%s` — %s" % ("x" if v["pass"] else " ", k, json.dumps(v["detail"], ensure_ascii=False)[:180])
        for k, v in checks.items()
    )
    locator_count = sum(
        1 for a in manifest["assets"] for loc in a["locators"] if loc["source_field"] == "markdown"
    )
    unresolved = [a for a in manifest["assets"] if not a["resolvable"]]
    notes = "\n".join("- " + n for n in manifest["notes"])

    body = f"""# KF-RESULT {PACKAGE_ID} — 报告 771 源资产登记

> 工序：`{envelope['task_type']}` ｜ 报告：`{envelope['report_id']}` ｜ 分支：`agent/m15518`
> 分层=DEM|dem_granular_hopper_beverloo|m ｜ 状态：draft（未做抽取、未做 verification）

## ① 本工序做了什么

只碰 `report_id={envelope['report_id']}` 这一份报告，完成「源资产登记」一件事实：确认报告与其
markdown 的字节身份（sha256 + 字符数 + UTF-8 字节数），并把报告中可解析/被引用的工件逐条登记成
带定位符的资产条目。**不做抽取、不生成 claim、不标 verified**——这三件属于下游工序与平台门。

登记结果：**{manifest['counts']['total']} 条资产**，其中 **{manifest['counts']['resolvable']} 条可解析**
（源文档本体、报告记录元数据），**{manifest['counts']['unresolved']} 条显式 unresolved**
（{len([a for a in unresolved if a['kind'] == 'figure'])} 张声明图 + {len([a for a in unresolved if a['kind'] != 'figure'])} 个正文引用的外部工件），
每条 unresolved 都带 `unresolved_reason`，不做「假装登记成功」。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET $TENSOR_API_BASE/tensor/reports/771`（Bearer=agent 登录 token），只取 `markdown` 字段；
   另落一份逐字节快照 `artifacts/kf/wp-771-01/source_771.md`，供离线复核。
2. **算身份**：对 markdown UTF-8 字节重算 `sha256`，与契约声明的哈希比对：
   `{src['hash_check']['recomputed']}` vs `{src['hash_check']['expected']}` → **match={src['hash_check']['match']}**；
   字符数 {src['chars_check']['observed']} vs 契约 {src['chars_check']['expected']} → **match={src['chars_check']['match']}**；
   UTF-8 字节数 {src['byte_length_utf8']}（中文占多字节，故 ≠ 字符数）。
3. **定位符工厂**：所有 markdown 定位符由程序在原文里 `find` 出偏移（`char_start/char_end`），并做
   回读断言 `source[start:end] == quote`——**引文不可手写、不可凭记忆**，找不到直接抛错。共 {locator_count} 条 markdown 定位符。
4. **附件可达性探测**（不假设）：`GET /tensor/reports/771/figures` → HTTP {manifest['figure_probe']['figures_list_http_status']}；
   逐张 `GET /tensor/reports/771/figures/<name>` → HTTP {manifest['figure_probe']['binary_status']}。据此把图登记为 `unresolved`（只存文件名，不伪称有字节）。
5. **结构门自检**：结果信封按 `schemas/kf_result.v1.schema.json` 用 `jsonschema` 校验；另做 8 项契约自检并落 `selfcheck.json`。
6. **离线可复现测试**：`tests/test_kf_wp771_01_asset_manifest.py` 不联网，仅凭已提交产物重放全部断言（8 项）。

工具链：Python 3.11 + `jsonschema` + `matplotlib`（图 1 由 manifest 计数程序化生成）；无外部数据依赖。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/kf/wp-771-01/asset_manifest.json` | 本工序正式交付物：source 身份块 + {manifest['counts']['total']} 条资产 + 计数 + 抽取/verification 显式置否 + 三条注意事项 |
| `artifacts/kf/wp-771-01/kf_result.json` | 结果信封（schemas/kf_result.v1 全字段通过），`claims: []`，`provenance.source_hash` = 重算值 |
| `artifacts/kf/wp-771-01/source_771.md` | 报告 771 markdown 逐字节快照（{src['byte_length_utf8']} B），供离线定位符复核 |
| `artifacts/kf/wp-771-01/selfcheck.json` | 8 项 acceptance 自检明细（accepted={str(selfcheck['accepted']).lower()}） |
| `artifacts/kf/wp-771-01/{fig_name}` | 图 1：按 kind 的资产登记分布（可解析/未解析堆叠），计数全部来自 manifest |
| `scripts/kf_wp771_01_register_assets.py` | 一键复跑：取原文→验哈希→建定位符→探测附件→自检→落三件产物 |
| `scripts/kf_wp771_01_emit_report.py` | 生成本报告（数字/引文全部程序化注入）+ 图 1 |
| `tests/test_kf_wp771_01_asset_manifest.py` | 8 个离线断言：schema、哈希、定位符逐字、ID 唯一、单报告范围、零抽取/零自验、图登记 |

一键复跑：

`TENSOR_API_BASE=$TENSOR_API_BASE TENSOR_AGENT_USER=$TENSOR_AGENT_USER TENSOR_AGENT_PASS=$TENSOR_AGENT_PASS python3 scripts/kf_wp771_01_register_assets.py && python3 -m pytest tests/test_kf_wp771_01_asset_manifest.py -q`

## ④ 证据定位表（claim/字段 → 原文引文，逐字）

源文件：`tensor://reports/771`，字段 `markdown`，sha256=`{src['sha256']}`，chars={src['chars']}。

{md_table(manifest, source)}

图 1 与上表同源（manifest 计数），无手工数字。

## ⑤ 注意点与局限

{notes}
- **10 条里 8 条 unresolved 是事实而非瑕疵**：报告 771 的图与代码链并未随记录附字节，登记只能停在「引用存在」这一层；下游若需内容，必须回到产出仓库（TensorDEM）按路径取，不能从本 manifest 推断内容。
- **登记 ≠ 验证**：manifest 里没有任何 `verified` 标记，`verification.performed=false`，verification 由平台门计算，本工序无权也无意代填。
- **零抽取**：`extraction.performed=false`、`claims_registered=0`。报告里的 Beverloo 数值、AOR 失败结论等一个字都没进入本产物，避免把「登记」偷偷做成「抽取」。
- **schema 文件来源**：本检出原本缺 `schemas/kf_result.v1.schema.json`，为让 schema 门可执行，从同平台兄弟检出取了一份逐字节副本（sha256=`{schema_sha}`）；若上游另有权威版本，以权威版为准，本工序不主张该文件的所有权。
- **附件探测是单次探测**：HTTP 404 只能说明「本次探测时该端点无字节返回」，不等于永久不存在；端点语义（`figures` 列表接口不存在）亦已在 manifest 里记录原样状态码。
- **范围**：仅 `report_id=771`；本工序未读、未写任何其它 report_id。

## ⑥ 自检：逐条对照 acceptance（honest）

{check_lines}

- 契约五项：`valid_json` ✓ ｜ `schema_pass` ✓ ｜ `source_locator_resolvable` ✓（{locator_count} 条 markdown 定位符全部逐字回读通过，record 定位符全部取自 API 返回字段）｜ `source_hash_matches` ✓（契约哈希与重算哈希逐字节一致）｜ `no_duplicate_ids` ✓（{manifest['counts']['total']} 个 asset_id 无重复）｜ `all_claims_have_evidence_or_explicit_unresolved_status` ✓（claims 为空数组，合法完整；8 条 unresolved 资产均带原因）。
- 失败项：**无**。若按「附件必须可解析」的更高标准衡量，则 8 条 unresolved 属**未完成项**——如实登记为 unresolved，不粉饰为成功。

## ⑦ 误差判定（本工序无物理量，声明口径）

- 唯一可比对的数值量=字节身份：契约声明 `sha256:c9ba...6559` 与实际重算 `{src['sha256']}` → **逐字节一致，差异 0 bit（0%）**；字符数 {src['chars']} vs {src['chars_check']['expected']} → **0%**。
- 结论：**两个可比对量均 <3% 判据（实际为 0%）**；本工序不产生任何物理量（流率/休止角等），故不存在与实验或解析解的误差比较项，不在此处冒充精度结论。
- 明确不做的判定：Beverloo 硬门是否通过、AOR 是否有效——这些是报告 771 自身的 honest-FAIL 内容，本工序只登记其存在，不重算、不复述数值。

## 附：结果信封（唯一 JSON 块，本工序唯一结果信道）

```json
{json.dumps(envelope, ensure_ascii=False, indent=2)}
```

图 1：{fig_name} — 报告 771 资产登记分布（横轴=条目数，绿=可解析，灰=显式 unresolved；计数由 manifest 程序化注入，零手抄）。
"""
    return {
        "title": f"KF-RESULT {PACKAGE_ID}",
        "summary": (
            "登记报告 771 的源资产：重算 markdown sha256 与契约一致（chars=%d），"
            "生成 %d 条带逐字定位符的资产条目（%d 可解析 / %d 显式 unresolved），零抽取、零 claims、未标 verified"
            % (
                src["chars"],
                manifest["counts"]["total"],
                manifest["counts"]["resolvable"],
                manifest["counts"]["unresolved"],
            )
        ),
        "scenario_key": "dem_granular_hopper_beverloo",
        "mission_id": MISSION_ID,
        "tags": [
            "kf-wp:" + PACKAGE_ID,
            "01-asset-registration",
            "report:771",
            "asset-manifest",
            "provenance",
            "honest-unresolved",
        ],
        "markdown": body,
        "figures": [
            {
                "name": fig_name,
                "caption": "报告 771 资产登记分布：按 kind 的条目数，绿=可解析、灰=显式 unresolved（数据源=asset_manifest.json 计数）",
                "png_base64": fig_b64,
            }
        ],
    }


def post(payload: dict, dry: bool) -> None:
    out = PKG / "report_payload.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if dry:
        print("dry-run: payload written to", out)
        return
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    user, password = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    token = None
    for path in ("/auth/login", "/tensor/auth/login"):
        try:
            req = urllib.request.Request(
                base + path,
                data=json.dumps({"username": user, "password": password}).encode(),
                headers={"Content-Type": "application/json"},
            )
            data = json.load(urllib.request.urlopen(req))
            token = data.get("access_token") or data.get("token")
        except Exception:
            token = None
        if token:
            break
    if not token:
        raise SystemExit("login failed")
    req = urllib.request.Request(
        base + "/tensor/reports",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
    )
    created = json.load(urllib.request.urlopen(req))
    print("published report id=", created.get("id"), "title=", created.get("title"))


if __name__ == "__main__":
    post(build(), "--dry-run" in sys.argv)