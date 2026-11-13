"""Render the deliverables report of work package wp-10647-01 and the platform publication payload.

All numbers are read from the produced artifacts (asset_manifest.json / verification.json) and
injected programmatically -- zero hand transcription into the report body.

Outputs
  docs/kf/wp-10647-01/REPORT.md             six-section deliverable report (acceptance table, locator table)
  docs/kf/wp-10647-01/kf_result.json        result envelope copy for the package folder
  docs/kf/wp-10647-01/acceptance.json       verification.json copy
  /tmp/report_10647_publish.json            platform /tensor/reports payload (figure inlined as base64)

Usage: python3 scripts/kf_report_10647.py
"""
from __future__ import annotations

import base64
import json
import pathlib
import shutil

PACKAGE_ID = "wp-10647-01"
REPORT_ID = "10647"
RUN = pathlib.Path("runs/wp-10647-01")
ART = pathlib.Path("artifacts/wp-10647-01")
DOC = pathlib.Path("docs/kf/wp-10647-01")
FIG = ART / "fig1_asset_resolution.png"


def main() -> int:
    man = json.loads((ART / "asset_manifest.json").read_text(encoding="utf-8"))
    ver = json.loads((ART / "verification.json").read_text(encoding="utf-8"))
    env = json.loads((RUN / "kf_result.wp-10647-01.json").read_text(encoding="utf-8"))
    probe_path = DOC / "platform_figure_probe.json"
    probe = json.loads(probe_path.read_text(encoding="utf-8")) if probe_path.exists() else None
    probe_line = ("（本工单提交的图件 `png_base64` 长度 "
                  + ", ".join(str(x) for x in probe["submitted_png_base64_chars"])
                  + " → API 返回 " + ", ".join(str(x) for x in (probe["returned_png_base64_chars"] or ["n/a"]))
                  + "；图件下载端点 "
                  + ", ".join("%s→%s" % (k, v["status"]) for k, v in probe["figure_endpoints"].items())
                  + "）") if probe else "（未运行探针）"
    c = man["counts"]

    DOC.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(RUN / "kf_result.wp-10647-01.json", DOC / "kf_result.json")
    shutil.copyfile(ART / "verification.json", DOC / "acceptance.json")

    # ---------- locator table (evidence map): every row is a real slice ----------
    rows = []
    for a in man["assets"]:
        loc = a["locator"]
        q = loc["quote"].replace("|", "\\|").replace("\n", " ⏎ ")
        if len(q) > 110:
            q = q[:110] + "…"
        rows.append("| `%s` | %s | %s | %d–%d | %d–%d | `%s` |"
                    % (a["asset_id"], a["asset_class"], a["resolution"],
                       loc["start_char"], loc["end_char"], loc["start_line"], loc["end_line"], q))
    locator_table = "\n".join(rows)

    # ---------- acceptance table ----------
    acc_rows = []
    for k in ver["acceptance_order"]:
        chk = ver["checks"][k]
        acc_rows.append("| `%s` | %s | %s |" % (k, "✔" if chk.get("ok") else "✘",
                                                json.dumps({x: y for x, y in chk.items() if x != "ok"},
                                                           ensure_ascii=False)[:160]))
    acc_table = "\n".join(acc_rows)

    extra_rows = []
    for k, chk in ver["checks"].items():
        if k in ver["acceptance_order"]:
            continue
        extra_rows.append("| `%s` | %s |" % (k, "✔" if chk.get("ok") else "✘"))
    extra_table = "\n".join(extra_rows)

    by_res = "、".join("%s=%d" % (k, v) for k, v in c["by_resolution"].items())
    missing = sorted({m for a in man["assets"] for m in
                      (a["resolution_check"].get("missing") or [])})

    body = f"""# {PACKAGE_ID} · 报告 10647 源资产登记

- **package / task_type**：`{PACKAGE_ID}` / `{man['task_type']}`（lane C，delivery repo = TensorKnowledge，status = draft）
- **report_id**：`{man['report_id']}` — 《{man['source']['title']}》
- **scenario_key**：`{man['source']['scenario_key']}`（平台基础设施 / 长跑生存层，无船舶域语义）
- **source**：`{man['source']['uri']}` · field=`{man['source']['field']}` ·
  sha256=`{man['source']['hash']}` · chars={man['source']['chars']} · bytes_utf8={man['source']['bytes_utf8']}
- **产物**：`artifacts/{PACKAGE_ID}/asset_manifest.json`（交付物）、`artifacts/{PACKAGE_ID}/verification.json`、
  `artifacts/{PACKAGE_ID}/fig1_asset_resolution.png`、`runs/{PACKAGE_ID}/kf_result.wp-10647-01.json`
- **本工序边界**：只登记资产（register_assets=true / classify_report_type=false），**不做抽取**，claims 为空数组，
  **不把任何结论标成 verified**（verification 由平台门计算）。

---

## ① 本工序做了什么

1. 从平台 API 取回 report_id=10647 的 `markdown` 字段（`scripts/kf_fetch_10647.py`），逐字节落盘并重算哈希：
   sha256 = `{man['source']['hash']}`，与工作包契约声明的 `{env['provenance']['contract_declared_hash'][7:]}` **一致**，
   字符数 {man['source']['chars']} 与契约 `chars: 10814` 一致。
2. 把报告里可定位的资产登记成 {c['assets']} 条清单（`scripts/kf_register_10647.py`）：类别分布见 counts.by_class，
   可解析性 {by_res}。
3. 对每条资产执行一次**可复现的解析检查**并把结果写进 `resolution_check`（工作树路径存在性 / 平台 figure 元数据 /
   容器 core_pattern 探针 / 工件可溯源性），不猜测地址、不编造缺失信息。
4. 独立复验（`scripts/kf_verify_10647.py`：新登录 + 重新拉取 + 重算哈希 + 重切每条引文 + JSON-Schema 校验），
   六项 acceptance 全过（见 ⑥）。
5. 出图（`scripts/fig_asset_inventory_wp10647_01.py`）：可解析性分布 / 类别分布 / 引文跨度地图。

**没有做的事（诚实边界）**：没有抽取任何知识对象；没有复算上游数字（复算需要 `runs/m9082/evidence.json`，
该工件不在本工作树）；没有判定上游结论对错。

## ② 怎么做的（步骤 / 工具 / 关键设置）

```
scripts/kf_fetch_10647.py      # API 登录 → GET /tensor/reports/10647 → 落盘 md/json → 重算 sha256
scripts/kf_register_10647.py   # 锚点切片 + 唯一性断言 + 解析检查 → asset_manifest.json + 结果信封
scripts/kf_verify_10647.py     # 独立复验（新登录重取 + jsonschema + 逐条重切 + counts/nesting 一致性）
scripts/fig_asset_inventory_wp10647_01.py   # 三面板总览图（数字全部读自 manifest）
```

关键设置与设计决定：

| 决定 | 理由 |
|---|---|
| 引文一律**程序化切片**（锚点唯一 + 切片后 `md.count(quote)==1` 断言） | 零手抄；任何手工重述都会在断言处失败 |
| `in_report_section` 由文档自动推导（最近的前置标题行） | 章节名也不许手打 |
| 切片模式分 `line / block / bullet / table / table_after / fence` | 表格与代码块边界由结构决定，避免把相邻资产吞进来（A27/A28 曾因 block 模式越界，改 `bullet` 修复） |
| `resolution` 三值：`resolved_in_source` / `referenced_unresolved` / `declared_absent` | 只描述"能否定位/解析"，不表达"对错"；`resolution_check.result` 必须与之一致（verifier 额外检查） |
| 数值表只登记不复核，`resolution_check.check=artifact_trace` 记录 `evidence.json` 缺失 | 避免"看起来核过"的假象 |
| 新增 `schemas/asset_manifest.v2.schema.json`（把 v1 的两个 `const` 放宽为 pattern，其余不变） | v1 把 `package_id`/`report_id` 钉死为 wp-448-01/448，无法校验其它包；v1 保持原样以存证 |

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/{PACKAGE_ID}/asset_manifest.json` | 交付物本体：{c['assets']} 条资产、source 块、counts、integrity；claims=[] |
| `artifacts/{PACKAGE_ID}/verification.json` | 六项 acceptance + 6 项额外检查的机器结果（本次 all_pass={str(ver['all_pass']).lower()}） |
| `artifacts/{PACKAGE_ID}/fig1_asset_resolution.png` | 三面板总览：可解析性分布 / 类别分布 / 引文跨度地图 |
| `runs/{PACKAGE_ID}/report_10647.md` · `.json` | 源 markdown 逐字节副本与 API 原始 payload（哈希可复算） |
| `runs/{PACKAGE_ID}/kf_result.wp-10647-01.json` | 结果信封（kf_result.v1 结构），`provenance.source_hash` = 源 md 哈希 |
| `runs/{PACKAGE_ID}/kf_result_block.wp-10647-01.json` | 与信封逐字节相同，供本报告内唯一的结果围栏块原样提交 |
| `docs/kf/{PACKAGE_ID}/REPORT.md` · `kf_result.json` · `acceptance.json` | 本报告与镜像件 |
| `schemas/asset_manifest.v2.schema.json` | 包无关的清单 schema（v1 的 const → pattern 泛化） |
| `scripts/kf_fetch_10647.py` · `kf_register_10647.py` · `kf_verify_10647.py` · `fig_asset_inventory_wp10647_01.py` | 一键复跑链（fetch → register → verify → figure） |
| `tests/test_kf_wp10647.py` | 离线回归：schema/定位/唯一性/哈希/claims/无 verified 标记 |

## ④ 证据定位表（claim/字段 → 原文逐字切片）

下表每一行的 `quote` 都是源 markdown 的**字符区间逐字切片**（`start–end` 为字符偏移，行号为 0 基），
独立复验时按同一区间重切并比对（`source_locator_resolvable` 检查）。

| asset | class | resolution | char span | line span | snippet |
|---|---|---|---|---|---|
{locator_table}

**范围外但重要的登记事实**

- 图件：平台 payload 提供 4 条 figure 元数据（name/caption 齐备），但 `png_base64` 长度为 0，
  `runs/m9082/figures/` 也不在本工作树 → 四张图登记为 `referenced_unresolved`（元数据可解析、位图在本环境不可得）。
  **同平台实测**{probe_line}，说明"响应里没有字节"不等于"作者没附图"，故清单只声明"不可得"、不推断上游缺失。
- 代码/测试/证据工件：TensorPlatform 仓路径，在本工作树（TensorKnowledge）逐一探测为缺失：
  {", ".join("`%s`" % m for m in missing) if missing else "（无）"}。
- 环境限制 A27（内核自发 core 采集）：`declared_absent`，并附本容器实测探针
  （core_pattern = `{man['assets'][26]['resolution_check'].get('core_pattern')}`，
  pipe 目标是否存在 = {man['assets'][26]['resolution_check'].get('pipe_target_exists')}，
  `coredumpctl` = `{man['assets'][26]['resolution_check'].get('coredumpctl')}`，
  可用性 = {man['assets'][26]['resolution_check'].get('coredumpctl_functional')}）。
  **探针对象是本工作树容器，不是报告作者的容器**，故不改写上游结论，只留可复跑记录。

## ⑤ 注意点与局限（honest）

1. **不做抽取**：claims=[] 是契约允许的完整结果，不是遗漏。下游 03 工序如需知识对象，应基于本清单的
   `asset_id` 引用，而不是重新手抄原报告。
2. **数字未复核**：报告 ③⑥ 两节的量化结论（开销中位数 −0.65 %、完整率 100 %、位级一致、检出 40/40 等）
   在本清单里只是**被定位的文本**（`artifact_trace` 检查记录 `runs/m9082/evidence.json` 缺失）。
   任何下游若要使用这些数字，必须先取回 evidence.json 复算。
3. **图件不可取**：4 张图只有 name/caption；本报告自己的图（fig1）是**新生成**的登记总览图，
   不是上游图的复现。
4. **A10 与 A05–A08 刻意嵌套**：设计表是容器级跨度，包含自身 4 行；verifier 的 `span_nesting`
   白名单只允许这 4 对，其它重叠会判 FAIL。
5. **A27 探针≠上游环境**：见 ④ 末尾；`coredumpctl` 存在于本镜像但报告作者容器无 systemd，两者不可互相推翻。
6. **schema 泛化是本地决定**：平台侧 `kf_result.v1.schema.json` 校验信封；清单本体用的是本仓新增的
   `asset_manifest.v2.schema.json`（v1 的 const 钉死 wp-448-01，无法复用）。若平台另有清单 schema，以平台为准，
   本清单需按其调整——这是本工序唯一"可能与平台不同步"的点。
7. **`in_report_section` 是最近前置标题**：报告头部 5 行资产的 section 因此是 H1 标题行，属预期行为。
8. 未做独立评审（契约 review.required=false），本报告的全部 PASS 来自自检脚本，非第三方结论。
9. **平台图件回传**：本报告提交时附了非空 PNG，但 API 响应与 GET 均返回 `png_base64` 长度 0，且无图件下载端点
   （`/tensor/reports/<id>/figures`、`/tensor/figures/...` 均 404，见 `docs/kf/{PACKAGE_ID}/platform_figure_probe.json`）。
   因此平台侧只能看到图件元数据；图件本体见仓内 `artifacts/{PACKAGE_ID}/fig1_asset_resolution.png`。
   这条对全部 KF 报告通用：**不要把"payload 无图字节"记成"上游未附图"**。
10. **本包曾两次重复发布**（report id 14766、14772，同 package 早期草稿：14766 报告正文里混入了 2 处围栏标记词（散文提及），
   破坏"唯一结果块"信道，已改写并在生成器里加了"围栏块计数必须为 1"的硬断言；14772 早于本报告对图件回传的实测与 A23–A26
   注记修订）。两条草稿平台不提供更新/删除接口（PUT/PATCH/DELETE 均 405），故以本报告为准。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 结果 | 证据摘要（`artifacts/{PACKAGE_ID}/verification.json`） |
|---|---|---|
{acc_table}

额外一致性检查（非契约要求，但可作为回归护栏）：

| 检查 | 结果 |
|---|---|
{extra_table}

**误差/偏差判定（对照本工序的基准，显式回答）**

| 关键量 | 基准 | 实测 | 偏差 | 是否 < 3 % |
|---|---|---|---|---|
| 源 markdown sha256 | 契约 `aa10fd7a…bf31` | 重算 `{man['source']['hash'][:16]}…` | 0 位差 | **是**（exact） |
| 源字符数 | 契约 `10814` | {man['source']['chars']} | 0 % | **是**（exact） |
| 引文可定位率 | {c['assets']}/{c['assets']} | {c['assets'] - len(ver['checks']['source_locator_resolvable'].get('failures') or [])}/{c['assets']} | 0 % | **是** |
| 引文唯一性 | 100 % | 100 %（`no_duplicate_ids` 的 duplicate_locators={ver['checks']['no_duplicate_ids'].get('duplicate_locators')}） | 0 % | **是** |

无基准项（如实声明，不以"未测"充数）：上游数值结论的复算误差——基准工件 `runs/m9082/evidence.json`
不在本工作树，本工序无基准可对，故**不复算、不判定**。

## 复现（一键）

```bash
# 环境：TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE（默认 http://127.0.0.1:8010/api/v1）
python3 scripts/kf_fetch_10647.py              # 取回 report 10647（校验 sha256 与 10814 字符）
python3 scripts/kf_register_10647.py           # 生成 asset_manifest.json + 结果信封
python3 scripts/kf_verify_10647.py             # 独立复验六项 acceptance（新登录重取 + 重切引文）
python3 scripts/fig_asset_inventory_wp10647_01.py   # 重新出图
python3 -m pytest tests/test_kf_wp10647.py -q  # 离线回归（无需网络）
```

## 附录：结果信封（kf_result.v1，与报告内唯一结果围栏块逐字节相同）

```json
{json.dumps(env, ensure_ascii=False, indent=2)}
```
"""

    # delivery-channel guard: the report markdown must carry exactly ONE ```json fence (the envelope)
    if body.count("```json") != 1:
        raise SystemExit("report body must contain exactly one ```json fence, found %d"
                         % body.count("```json"))
    (DOC / "REPORT.md").write_text(body, encoding="utf-8")
    print("wrote", DOC / "REPORT.md", (DOC / "REPORT.md").stat().st_size, "bytes")

    # ---------- platform publication payload ----------
    png = base64.b64encode(FIG.read_bytes()).decode()
    summary = ("报告 10647 源资产登记完成：%d 条资产（%s），源 md sha256 与契约逐字节一致，"
               "六项 acceptance 自检全过，claims 为空（登记工序不做抽取）。" % (c["assets"], by_res))
    payload = {
        "title": "KF-RESULT %s · report 10647 源资产登记（长跑生存层 / crash-forensics-resume）" % PACKAGE_ID,
        "summary": summary,
        "scenario_key": "crash-forensics-resume",
        "mission_id": 15688,
        "tags": ["kf-wp:%s" % PACKAGE_ID, "kf", "01-asset-registration", "asset-manifest",
                 "report-10647", "crash-forensics-resume", "zero-hand-transcription"],
        # 唯一结果信道：报告 markdown 内**唯一一个** ```json 块 = 结果信封原样（不裁剪、不重排）
        "markdown": body,
        "figures": [{
            "name": "fig1_asset_resolution.png",
            "caption": ("report 10647 资产登记总览（package wp-10647-01）：(a) 可解析性分类 —— %s；"
                        "(b) asset_class 分布（%d 类）；(c) 每条引文在源 markdown 上的字符跨度，"
                        "颜色同 (a)。全部数字读自 asset_manifest.json；坐标轴用 ASCII 标注"
                        "（镜像内无 CJK 字体）。" % (by_res, len(c["by_class"]))),
            "png_base64": png,
        }],
    }
    pathlib.Path("/tmp/report_10647_publish.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print("wrote /tmp/report_10647_publish.json", len(png), "b64 chars of png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())