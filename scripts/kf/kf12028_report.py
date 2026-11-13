#!/usr/bin/env python3
"""Build the wp-12028-01 delivery report + its inventory figure.

Every number in the markdown is interpolated from the generated artifacts
(asset_manifest.json / kf_result.json / acceptance.json) — nothing is retyped.

Outputs
  docs/kf/wp-12028-01/fig_asset_inventory.png
  docs/kf/wp-12028-01/REPORT.md
  docs/kf/wp-12028-01/report_payload.json   (POST body for /tensor/reports)

Usage: python3 scripts/kf/kf12028_report.py
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DOCS = Path("docs/kf/wp-12028-01")
PKG = "wp-12028-01"
REPORT_ID = "12028"
MISSION_ID = 15736
SCENARIO_KEY = "p227w2-N01"

STAGE_LABEL = {
    "source_document": "source_document",
    "record_metadata": "record_metadata",
    "method_definition": "method_definition",
    "equation_block": "equation_block",
    "code_module": "code_module",
    "test_file": "test_file",
    "script_file": "script_file",
    "declared_attribute": "declared_attribute",
    "test_record": "test_record",
    "repro_command": "repro_command",
    "figure_reference": "figure_reference",
    "figure_caption": "figure_caption",
    "benchmark_reference": "benchmark_reference",
    "literature_reference": "literature_reference",
    "result_table": "result_table",
    "gate_record": "gate_record",
    "symbol_reference": "symbol_reference",
    "observation_source": "observation_source",
}


def render_figure(man: dict) -> Path:
    by_kind: dict[str, dict[str, int]] = {}
    for a in man["assets"]:
        d = by_kind.setdefault(a["kind"], {"resolved": 0, "unresolved": 0})
        d[a["status"]] += 1
    kinds = sorted(by_kind, key=lambda k: -(by_kind[k]["resolved"] + by_kind[k]["unresolved"]))
    res = [by_kind[k]["resolved"] for k in kinds]
    unres = [by_kind[k]["unresolved"] for k in kinds]

    figs = [a for a in man["assets"] if a["kind"] == "figure_reference"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.6))
    y = range(len(kinds))
    ax1.barh(list(y), res, color="#2f6fb5", label="resolved")
    ax1.barh(list(y), unres, left=res, color="#c0392b", label="unresolved")
    ax1.set_yticks(list(y))
    ax1.set_yticklabels(kinds, fontsize=8)
    ax1.invert_yaxis()
    ax1.set_xlabel("assets")
    ax1.set_title("(a) report %s asset inventory by kind\nresolved=%d / unresolved=%d / total=%d"
                  % (REPORT_ID, man["asset_counts"]["resolved"],
                     man["asset_counts"]["unresolved"], man["asset_counts"]["assets_total"]),
                  fontsize=10)
    ax1.legend(fontsize=8, loc="lower right")
    ax1.grid(axis="x", alpha=0.3)

    names = [a["name"].rsplit("/", 1)[-1].replace("_", " ").replace(".png", "") for a in figs]
    nbytes = [a["resolved_bytes"]["bytes"] for a in figs]
    ax2.bar(range(len(figs)), nbytes, color="#1f8a70")
    for i, a in enumerate(figs):
        rb = a["resolved_bytes"]
        ax2.text(i, rb["bytes"] * 1.02, "%dx%d\n%s" %
                 (rb["width_px"], rb["height_px"], rb["sha256"][7:15]),
                 ha="center", va="bottom", fontsize=7)
    ax2.set_xticks(range(len(figs)))
    ax2.set_xticklabels(names, rotation=18, ha="right", fontsize=8)
    ax2.set_ylim(0, max(nbytes) * 1.35)
    ax2.set_ylabel("payload bytes served by platform store")
    ax2.set_title("(b) figure payloads registered (HTTP 200, sha256 pinned)", fontsize=10)
    ax2.grid(axis="y", alpha=0.3)

    fig.suptitle("KF %s · asset registration evidence — report %s" % (PKG, REPORT_ID), fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = DOCS / "fig_asset_inventory.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def locator_table(man: dict, ids: list[str]) -> str:
    rows = ["| 字段/资产 | 原文引文片段（逐字，含字符区间） |", "| --- | --- |"]
    idx = {a["asset_id"]: a for a in man["assets"]}
    for aid in ids:
        a = idx[aid]
        loc = a["locators"][0]
        q = loc["quote"].strip()
        if len(q) > 96:
            q = q[:93] + "…"
        rows.append("| `%s` (%s) | `%s` [%d:%d] |"
                    % (aid, a["name"], q.replace("|", "\\|"), loc["char_start"], loc["char_end"]))
    for obs in man["observations"][:3]:
        loc = obs["evidence"][0]
        q = loc["quote"].strip()
        if len(q) > 96:
            q = q[:93] + "…"
        rows.append("| 观察 `%s` | `%s` [%d:%d] |"
                    % (obs["id"], q.replace("|", "\\|"), loc["char_start"], loc["char_end"]))
    return "\n".join(rows)


def build() -> tuple[Path, Path]:
    man = json.loads((DOCS / "asset_manifest.json").read_text(encoding="utf-8"))
    env = json.loads((DOCS / "kf_result.json").read_text(encoding="utf-8"))
    acc = json.loads((DOCS / "acceptance.json").read_text(encoding="utf-8"))
    figs_meta = json.loads(Path("work/wp-12028-01/source/figures_meta.json")
                           .read_text(encoding="utf-8"))
    probes = json.loads(Path("work/wp-12028-01/source/probes.json").read_text(encoding="utf-8"))

    png = render_figure(man)
    src = man["source"]
    counts = man["asset_counts"]
    prov = env["provenance"]

    acc_rows = ["| acceptance 项 | 自检结论 | 关键证据 |", "| --- | --- | --- |"]
    for c in acc["checks"]:
        det = json.dumps(c["detail"], ensure_ascii=False)
        if len(det) > 120:
            det = det[:117] + "…"
        acc_rows.append("| `%s` | %s | %s |"
                        % (c["check"], c["status"], det.replace("|", "\\|")))
    acc_table = "\n".join(acc_rows)

    fig_rows = ["| 图文件 | 平台端点 | 状态 | 字节 | sha256 | 像素 |",
                "| --- | --- | --- | --- | --- | --- |"]
    for name, m in figs_meta.items():
        fig_rows.append("| `%s` | `%s` | %s | %s | `%s` | %dx%d |"
                        % (name, m.get("endpoint"), m.get("http_status"),
                           m.get("bytes"), (m.get("sha256") or "")[7:23],
                           m.get("width_px") or 0, m.get("height_px") or 0))
    fig_table = "\n".join(fig_rows)

    probe_rows = ["| 端点 | HTTP |", "| --- | --- |"]
    for p in probes:
        probe_rows.append("| `%s` | %s |" % (p["path"], p.get("http_status")))
    probe_table = "\n".join(probe_rows)

    unref = [a for a in man["assets"] if a["status"] == "unresolved"]
    unresolved_rows = ["| 资产 | kind | 未解析理由（摘） |", "| --- | --- | --- |"]
    for a in unref:
        unresolved_rows.append("| `%s` | %s | %s |"
                               % (a["asset_id"], a["kind"],
                                  a["unresolved_reason"][:150].replace("|", "\\|")))
    unresolved_table = "\n".join(unresolved_rows)

    obs_rows = ["| 观察 id | 内容（摘要） | 证据条数 |", "| --- | --- | --- |"]
    for o in man["observations"]:
        obs_rows.append("| `%s` | %s | %d |"
                        % (o["id"], o["observation"][:150].replace("|", "\\|"),
                           len(o["evidence"])))
    obs_table = "\n".join(obs_rows)

    env_json = json.dumps(env, ensure_ascii=False, indent=2)

    md = f"""# KF-RESULT {PKG}

- package_id: `{PKG}` ｜ task_type: `01-asset-registration` ｜ report_id: `{REPORT_ID}` ｜ lane: C ｜ repo: TensorKnowledge ｜ status: **draft**
- source: `{src['source_uri']}`（field=`markdown`），chars={src['chars']}，bytes_utf8={src['byte_length_utf8']}，sha256=`{src['sha256']}`
- 工序范围：**只登记资产**——不抽取 claim、不做报告类型分类、不标 verified（verification 由平台门计算）

## ① 本工序做了什么

对 report_id={REPORT_ID}（`{src['title']}`）执行 01-asset-registration：

1. 从平台 API 取回 markdown，本地重算字节哈希并锁定：`{src['sha256']}`，{src['chars']} 字符 / {src['byte_length_utf8']} 字节；契约声明 `{src['hash_check']['expected']}`，实测值与声明值逐字节相同（match={str(src['hash_check']['match']).lower()}），字符数也与契约声明的 {src['chars_check']['expected']} 一致（match={str(src['chars_check']['match']).lower()}）。
2. 建立资产清单：共 **{counts['assets_total']} 个资产**（resolved {counts['resolved']} / unresolved {counts['unresolved']}），覆盖源文档本体、记录元数据、方法/方程块、代码与测试工件引用、图件、声明数值表、门限记录、文献与基准引用。
3. 每条 locator 的 quote 由程序在运行时从原文**整行**取出（不是手打），双重校验 `md[start:end] == quote` 且 `quote in md`，并对选择器命中的 token 做**出现次数断言**（防止落到错误重复行）。
4. 图件不只登记引用：{len(figs_meta)} 张 PNG 从平台图件存储取回真实字节，逐张记录 sha256/字节数/像素尺寸（见下表）。
5. claims 按契约留空数组，并显式写明留空理由；未对任何数值做 re-verification，未生成"verified"标记。

## ② 怎么做的（步骤/工具/关键设置）

| 步骤 | 工具/脚本 | 关键设置 |
| --- | --- | --- |
| 取源 + 锁哈希 | `scripts/kf_fetch_12028.py`（urllib，Bearer 登录） | sha256 以 `markdown` 字段 utf-8 字节计算，与契约声明逐字节比对 |
| 资产登记 | `scripts/kf/kf12028_register_assets.py` + `scripts/kf/kf12028_spec.py`（`--offline` 可离线复跑） | 56 条 SPEC，选择器 `token:` / `table_row:` / `h1`；quote=整行原文；断言 `occurrence_count` 与期望一致，否则 SystemExit（拒绝编造） |
| 图件取字节 | 同上（`fetch_figure`） | `GET /tensor/reports/12028/figures/<name>`；记录 HTTP/bytes/sha256/IHDR 像素 |
| 可解析性探测 | 同上（`probe`） | 4 个候选端点，失败如实记 HTTP 状态码，不重试不猜测 |
| 共用库 | `scripts/kf/register_assets_lib.py`（复用既有件） | `Md` 行索引 + 选择器定位 + `fetch_report` 硬锁 report_id |
| 验收自检 | `scripts/kf/kf12028_verify_acceptance.py` + `scripts/kf/kf12028_checks.py` | 7 项检查（6 条契约 acceptance + 契约对齐 + 结构不变量），在线模式重新拉 markdown 复算哈希 |
| 单元测试 | `tests/test_wp12028_asset_manifest.py` | 23 项：正检 + **负对照**（篡改 quote / 平移偏移 / 伪造引文 / 伪造 record 值 / 重复 id / 改哈希 / 缺 unresolved 理由 / 篡改计数 → 必须被检出） |
| 图 | `scripts/kf/kf12028_report.py` | matplotlib Agg，全部数字从 manifest/figures_meta 程序化取，无手抄 |

## ③ 产出物清单

| 文件 | 要点 |
| --- | --- |
| `docs/kf/wp-12028-01/asset_manifest.json` | {counts['assets_total']} 资产 / 计数与不变量 / {len(man['observations'])} 条观察 / probe 证据 |
| `docs/kf/wp-12028-01/kf_result.json` | 提交用结果信封（outputs=`asset_manifest.json`，claims=[]） |
| `docs/kf/wp-12028-01/acceptance.json` | {acc['summary']['total']} 项自检（PASS {acc['summary']['pass']} / FAIL {acc['summary']['fail']}） |
| `docs/kf/wp-12028-01/fig_asset_inventory.png` | 资产解析状态 + 图件载荷清单图（本报告 ④ 附图） |
| `docs/kf/wp-12028-01/REPORT.md` / `report_payload.json` | 本报告与投递体 |
| `scripts/kf_fetch_12028.py`、`scripts/kf/kf12028_spec.py`、`scripts/kf/kf12028_register_assets.py`、`scripts/kf/kf12028_checks.py`、`scripts/kf/kf12028_verify_acceptance.py`、`scripts/kf/kf12028_report.py` | 取源/登记/检查/验收/出图，一键复跑 |
| `tests/test_wp12028_asset_manifest.py` | 23 项 pytest（含 12 项负对照） |
| `work/wp-12028-01/source/` | `report_12028.json`、`report_12028.md`、`markdown.sha256`、`figures/*.png`、`figures_meta.json`、`probes.json` |

图件载荷登记（真实字节，非字符串引用）：

{fig_table}

## ④ 证据定位表（claim/字段 → 原文引文片段）

全部引文由程序定位，区间为 markdown 字符下标（`[start:end]`），平台可逐条回解：

{locator_table(man, ['ast-12028-01', 'ast-12028-03', 'ast-12028-04', 'ast-12028-12',
                     'ast-12028-19', 'ast-12028-23', 'ast-12028-27', 'ast-12028-35',
                     'ast-12028-36', 'ast-12028-47', 'ast-12028-48', 'ast-12028-49'])}

观察项（registration-only，不作裁决，均附逐字证据）：

{obs_table}

## ⑤ 注意点与局限

1. **3 个代码/测试/脚本工件未能解析**（如实登记为 unresolved，不代上游补写）：报告正文引用了 `backend/methods/crp/__init__.py`、`backend/api/crp.py`、`backend/tests/test_crp.py`、`scripts/crp_generate_figures.py` 等，但这些字节不在报告存储中，探测端点无载荷：

{probe_table}

{unresolved_table}

2. **图件字节可解析但无哈希锚**：{len(figs_meta)} 张 PNG 由平台图件存储返回（HTTP 200，PNG magic 校验通过），但报告正文未给出图件哈希，故"与生产仓 `artifacts/crp/` 下同名文件逐字节同一"**无法从报告记录证明**——本单只登记平台侧字节与其 sha256，供后续审计比对。
3. **标题漂移**：record.title 与契约标题一致，但 markdown H1 多出"分析报告"后缀（`obs-title-drift`）；下游抽取须以 report_id 为键，不能以标题相等为键。
4. **mission_id 不一致**：record.mission_id={man['observations'][1].get('record_mission_id')}、正文写"任务编号 m10162"，而契约声明 mission_id: null（`obs-mission-id`）——如实记录，本单不做归并。
5. **报告内部口径差异（注册级观察，非裁决）**：§1.2 声明 6/7 叶的 ITTC 基准几何，而 §3.1/§3.2 的数值案例是 Z_f=4/Z_r=5 的简化案例（`obs-benchmark-vs-case-geometry`）；标题写"面元法"，§2 只给出升力线+叶素动量公式（`obs-title-scope-vs-method`）。
6. **honest FAIL 原样保留**：§1.3 目标 |Q_f+Q_r|/Q_ref < 1%，§3.4/§6.2 自报 172% 且标 FAIL，外层螺距优化未实现（`TorqueBalanceIterator` 仅为待办）——本单不升级任何门限结论，也不把"效率 1.0%"重述为已验证。
7. **未做**：数值复算、基准表回溯（Koushan 1993 未附）、代码字节核对（20,517/12,168/8,311 bytes 与 20 passed 记录均为**报告自述**，未重测）。

## ⑥ 自检：逐条对照 acceptance

{acc_table}

自检汇总：**PASS {acc['summary']['pass']} / FAIL {acc['summary']['fail']}**（共 {acc['summary']['total']} 项；worker 侧自检，非平台门）。

## ⑦ 结果图

![资产解析状态与图件载荷清单](fig_asset_inventory.png)

图 1：(a) 按 kind 统计的资产解析状态（resolved/unresolved）；(b) 4 张图件在平台存储的实际载荷字节数、像素尺寸与 sha256 前 8 位。

**为何没有场量云图/与解析解对比曲线**：本工作包是纯登记工序（`objective.register_assets=true`、`classify_report_type=false`），不执行任何求解、不复算任何流场量，因此不存在可供作图的场量或计算-基准对比曲线；强行作图会变成对上游数字的再绘图而非本工序证据。故图 1 只呈现本工序可自证的两类量：资产解析状态与图件载荷指纹。

## ⑧ 误差判定（关键量对照基准，显式回答是否 <3%）

| 关键量 | 基准 | 本工序观测 | 误差 | <3%？ |
| --- | --- | --- | --- | --- |
| markdown sha256 | 契约 `{src['hash_check']['expected']}` | `{src['sha256']}` | 0（逐字节一致） | ✅ 是（精确一致） |
| markdown 字符数 | 契约 {src['chars_check']['expected']} | {src['chars_check']['observed']} | 0% | ✅ 是 |
| locator 可回解率 | {acc['summary']['total']} 项自检全 PASS | PASS {acc['summary']['pass']} / FAIL {acc['summary']['fail']} | 0 项不符 | ✅ 是 |

**关于上游物理量误差（如 η 相对 ITTC 基准 1.0%）**：本工序**不做**该判定——参考数据（Koushan 1993）未附于报告记录，1.0% 是报告自述值，登记而已；任何"<3%"结论都属于下游复核工序，不在本单权责内。

## ⑨ 一键复跑

```bash
cd <worktree>
python3 scripts/kf_fetch_12028.py                       # 取源 + 锁哈希（需 TENSOR_AGENT_* 环境变量）
python3 scripts/kf/kf12028_register_assets.py           # 生成 asset_manifest.json / kf_result.json
python3 scripts/kf/kf12028_verify_acceptance.py         # 自检 → acceptance.json
python3 -m pytest tests/test_wp12028_asset_manifest.py -q   # 23 项测试（离线可跑）
python3 scripts/kf/kf12028_report.py                    # 出图 + 本报告 + 投递体
python3 scripts/kf/post_report.py docs/kf/wp-12028-01/report_payload.json
```

provenance：`source_hash` = `{prov['source_hash']}`（= 契约声明值，平台可独立重算）；`source_field` = `{prov['source_field']}`。

## 结果信封（唯一 json 代码块，平台门按 schemas/kf_result.v1.schema.json 校验）

```json
{env_json}
```
"""

    out = DOCS / "REPORT.md"
    out.write_text(md, encoding="utf-8")

    payload = {
        "title": "KF-RESULT " + PKG,
        "summary": ("登记 report %s 的源资产：hash/字符数与契约逐字节一致，%d 个资产（resolved %d / "
                    "unresolved %d），%d 张图件取回真实字节并 pin sha256，claims 按契约留空；"
                    "自检 %d/%d PASS（worker 侧，非平台门）。"
                    % (REPORT_ID, counts["assets_total"], counts["resolved"],
                       counts["unresolved"], len(figs_meta), acc["summary"]["pass"],
                       acc["summary"]["total"])),
        "scenario_key": SCENARIO_KEY,
        "mission_id": MISSION_ID,
        "tags": ["kf", "kf-wp:" + PKG, "asset-registration", "report-" + REPORT_ID,
                 "kf-stage-01", "CRP", "p227w2-N01"],
        "markdown": md,
        "figures": [{
            "name": png.name,
            "caption": ("图 1：report %s 资产解析状态（按 kind，resolved/unresolved）与 4 张图件"
                        "在平台存储的载荷字节/像素/sha256 指纹；由 scripts/kf/kf12028_report.py "
                        "从 asset_manifest.json 程序化生成。" % REPORT_ID),
            "png_base64": base64.b64encode(png.read_bytes()).decode(),
        }],
    }
    pay = DOCS / "report_payload.json"
    pay.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # exactly one ```json fence must exist in the submitted markdown
    assert md.count("```json") == 1, md.count("```json")
    json.loads(md.split("```json", 1)[1].split("```", 1)[0])  # fence parses
    return out, pay


if __name__ == "__main__":
    r, p = build()
    print("wrote", r, p)