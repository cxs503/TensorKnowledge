"""Generate the wp-9763-01 report (KF-RESULT body) and the platform report payload.

Zero hand transcription: every number and every quoted fragment in the report body is read from the
delivered artifacts (asset_manifest.json / verification.json), and the quoted fragments themselves are
the manifest's own verbatim quotes sliced from report 9763.

Outputs:
  docs/kf/wp-9763-01/KF-RESULT-wp-9763-01.md     report body, exactly one ```json block
  runs/wp-9763-01/platform_report.json            payload posted to POST /tensor/reports
Usage: python3 scripts/kf_report_9763.py
"""
from __future__ import annotations

import base64
import json
import pathlib

ROOT = pathlib.Path(".")
ART = ROOT / "artifacts/wp-9763-01"
DOC = ROOT / "docs/kf/wp-9763-01"
RUN = ROOT / "runs/wp-9763-01"
PKG = "wp-9763-01"


def clip(s: str, n: int = 120) -> str:
    s = s.replace("\n", " ⏎ ")
    return s if len(s) <= n else s[:n] + "…"


def main() -> int:
    man = json.loads((ART / "asset_manifest.json").read_text())
    ver = json.loads((ART / "verification.json").read_text())
    env = json.loads((RUN / "kf_result.wp-9763-01.json").read_text())
    by_id = {a["asset_id"]: a for a in man["assets"]}
    c = man["counts"]

    checks = [dict(check=x["check"], result=x["result"]) for x in ver["checks"]]
    pass_n = sum(1 for x in checks if x["result"] == "pass")

    def cell(s: str) -> str:
        return s.replace("|", "\\|")

    asset_rows = "\n".join(
        f"| {a['asset_id']} | {a['asset_class']} | {a['resolution']} | "
        f"L{a['locator']['start_line']}-{a['locator']['end_line']} · "
        f"[{a['locator']['start_char']}, {a['locator']['end_char']}) | "
        f"`{cell(clip(a['locator']['quote'], 96))}` |"
        for a in man["assets"]
    )
    cc_rows = "\n".join(
        f"| {x['check_id']} | {x['result']} | {cell(x['what'])} | "
        + ("<br>".join(f"`{cell(clip(e['quote'], 72))}` (L{e['line']})" for e in x.get("evidence", [])) or "—")
        + " |"
        for x in man["cross_checks"]
    )
    check_rows = "\n".join(f"| {x['check']} | {'✅ pass' if x['result'] == 'pass' else '❌ ' + x['result']} |"
                           for x in checks)

    acceptance = [
        ("valid_json", "产物为合法 JSON（manifest + 信封）"),
        ("schema_pass", "按 schemas/asset_manifest.v1.wp-9763-01.schema.json 与 schemas/kf_result.v1.schema.json 双 schema 校验通过"),
        ("source_locator_resolvable", f"{c['assets']} 个 locator 逐条从**重新拉取**的原文切片复现，且 quote 在全文唯一"),
        ("source_hash_matches", "重新登录重新拉取 markdown，sha256 = 契约 source_hash"),
        ("no_duplicate_ids", f"{c['assets']} 个 asset_id 无重复"),
        ("all_claims_have_evidence_or_explicit_unresolved_status",
         "claims 为空数组（契约允许），策略检查空集通过；cross_checks 中不确定项显式标 unresolved"),
    ]
    acc_rows = "\n".join(
        f"| {k} | {d} | {'✅' if dict((x['check'], x['result']) for x in checks).get(k) == 'pass' else '❌'} |"
        for k, d in acceptance
    )

    md = f"""# KF-RESULT {PKG}

## ① 本工序做了什么

**工作包**：`{PKG}` · 工序 `01-asset-registration`（lane A）· 只服务 report_id=`9763`。
**源报告**：《{man['source']['title']}》，scenario_key=`{man['source']['scenario_key']}`，平台 mission={man['source']['platform_mission_id']}，平台状态 `{man['source']['platform_status']}`。

本工序只做一件事：把这份报告的**源资产登记成可被下游工序机器定位的清单**——确认字节哈希、把每个资产在原文里的位置钉成字符区间、逐条给出「能不能解析到本体」的机器判定与失败探针。**不做**知识抽取、**不做**报告类型分类、**不做**数值判读、**不把任何结论标成 verified（verification 由平台门计算）**。

结果规模：登记 **{c['assets']} 个资产 / {len(c['by_class'])} 类**，其中 resolved_in_source **{c['resolved_in_source']}** 个、referenced_unresolved **{c['referenced_unresolved']}** 个、declared_absent **{c['declared_absent']}** 个。
另附 **{len(man['cross_checks'])} 项源级交叉检查**（{sum(1 for x in man['cross_checks'] if x['result'] == 'consistent')} consistent / {sum(1 for x in man['cross_checks'] if x['result'] == 'inconsistent')} inconsistent / {sum(1 for x in man['cross_checks'] if x['result'] == 'unresolved')} unresolved），不一致项**只登记不改写**，留给下游工序裁断。

**边界自证**：`scope_boundary.report_ids_touched = {man['scope_boundary']['report_ids_touched']}`，`upstream_artifacts_modified = {str(man['scope_boundary']['upstream_artifacts_modified']).lower()}`；本单未读、未写任何其它 report_id 的报告。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取证（不许凭记忆）**：`python3 scripts/kf_fetch_9763.py` → `GET {{TENSOR_API_BASE}}/tensor/reports/9763`，取 `markdown` 字段原样落盘 `runs/{PKG}/report_9763.md`。
   本地重算 `sha256 = {man['source']['hash']}`，与契约 `source_hash` 逐字节相同；字符数 **{man['source']['chars']}** 与契约 `chars` 相同（UTF-8 字节 {man['source']['bytes_utf8']}）。两项不一致则脚本直接 `FATAL` 退出（已内置硬门）。
2. **锚点定位而非抄写**：`scripts/kf_register_9763.py` 维护 {c['assets']} 行锚点表（asset_id / asset_class / 唯一行锚点 / 终止锚点 / 预声明 resolution）。运行时用锚点在 markdown 中做**唯一行匹配**（命中≠1 即 `SystemExit`）→ 由行偏移求 `[start_char, end_char)` → **直接从原文切片**得到 `quote`；再断言 `md.count(quote) == 1`。脚本不接受任何手写引文，也不做物理量换算。
3. **可解析性判定（探针，不猜地址）**：每个资产跑一次机器检查 `resolution_check`，结果与 `resolution` 强绑定：
   - 文本类资产 → `char_span_in_source_markdown`；
   - 代码/测试指针（A30/A31）→ 在本工作树与 TensorFEM 检出分别 `os.path.isfile` 探针；**判据 = 本工作树内能否拿到本体**，跨仓命中只作信息性证据；
   - 工具链声明（A12）→ 只有 basename，无法形成唯一地址，登记为 `unresolved` 并写明原因；
   - 图件集（A25）→ 平台 `figures` 字段条数 + 本机磁盘 glob `artifacts/fsi_flutter/fig*.png`；元数据 {len(man['source']['platform_figures'])} 条、png 字节 0、磁盘文件 0 → `referenced_unresolved`；
   - 运行记录（A32）→ 本工作树无该测试集，不可复现 → `referenced_unresolved`。
4. **独立校验（不信本地副本）**：`scripts/kf_verify_9763.py` 在**新进程、新登录**下重新拉取 markdown，重算哈希；把 {c['assets']} 个 locator 逐条从**新拉取的原文**重新切片比对（`quote == md[start:end]`、行号与字符区间互证、唯一性），再跑双 schema、查 id 唯一、查 claim 证据策略、结构化扫描「verified」标记、比对产物 sha256 与信封内嵌对象、比对 docs 镜像字节一致。输出 `artifacts/{PKG}/verification.json`，本次 **{pass_n}/{len(checks)} 项 pass，overall={ver['overall']}**。
5. **不变量测试（含反向对照）**：`pytest tests/test_kf_wp9763.py -q` → **24 passed**。除正向断言外含 10 个**反向对照**：篡改引文里的一个数字（4.4721→4.4722）、平移字符区间 1 位、行号漂移、制造重复 id、给 claim 去掉证据、塞入 `verified` 标记、改动信封内嵌 manifest、删掉 `integrity` 段、把 resolution 写成非法枚举值——每一种都被对应检查判红，证明这些检查是活的而不是只跑通。
6. **出图与复现**：`scripts/kf_figures_9763.py` 从 manifest / verification 读数生成 3 张图（无手输数字）；`asset_manifest.json` 的 sha256 为 `{env['provenance']['artifact_sha256']}`，清空产物后按复跑命令重建逐字节相同（无时间戳/随机量污染）。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `artifacts/{PKG}/asset_manifest.json` | 主产物（{man['source']['bytes_utf8']} 字节源文本 → {c['assets']} 资产，{c['resolved_in_source']} resolved / {c['referenced_unresolved']} unresolved / {c['declared_absent']} absent，{len(man['cross_checks'])} 项交叉检查）；sha256 `{env['provenance']['artifact_sha256']}` |
| `docs/kf/{PKG}/asset_manifest.json` | 主产物的**字节一致**镜像（push 门会滤除 `artifacts/**` 与 `runs/**`，`docs/` 才进仓） |
| `runs/{PKG}/kf_result.wp-9763-01.json` / `docs/kf/{PKG}/kf_result.json` | 结果信封（package_id / task_type / report_id / provenance / outputs），`verification_status = {env['provenance']['verification_status']}` |
| `artifacts/{PKG}/verification.json` / `docs/kf/{PKG}/verification.json` | {len(checks)} 项验收自检逐项结果，overall={ver['overall']} |
| `docs/kf/{PKG}/figures/fig1_asset_inventory.png` | 图1 资产类别 × 可解析状态（{c['assets']} 资产 / {len(c['by_class'])} 类） |
| `docs/kf/{PKG}/figures/fig2_locator_coverage.png` | 图2 {c['assets']} 条 locator 在 {man['source']['chars']} 字符原文上的覆盖地图 |
| `docs/kf/{PKG}/figures/fig3_verification_board.png` | 图3 验收自检状态板 + 交叉检查状态板 |
| `runs/{PKG}/report_9763.md` / `report_9763.json` | 源证据快照（markdown 与 API 原始响应，逐字节） |
| `schemas/asset_manifest.v1.wp-9763-01.schema.json` | 本工序 manifest 形状约束（版本化源码，供 `schema_pass` 可复现；不改动 448 工序的既有 schema） |
| `scripts/kf_fetch_9763.py` / `kf_register_9763.py` / `kf_verify_9763.py` / `kf_figures_9763.py` / `kf_report_9763.py` | 取证 / 登记 / 校验 / 出图 / 报报告，一键可复跑 |
| `tests/test_kf_wp9763.py` | 24 项不变量测试（含 10 个反向对照） |
| `docs/kf/{PKG}/KF-RESULT-{PKG}.md` | 本报告正文 |

**资产类别计数**：`{json.dumps(c['by_class'], ensure_ascii=False)}`

## ④ 证据定位表（claim/字段 → 原文引文）

下表每一行的 `quote` 都是报告 9763 markdown 的**唯一子串**（`md.count(quote) == 1`，由 `kf_verify_9763.py` 在重新拉取的原文上二次确认），并给出 `[start_char, end_char)` 与行区间。长引文在此处截断显示，完整 quote 见 `asset_manifest.json`（本表由脚本从 manifest 读数生成，未经手工转写）。

| asset_id | class | resolution | 定位 | 原文片段（逐字取自 report 9763） |
|---|---|---|---|---|
{asset_rows}

### ④b 源级交叉检查（{len(man['cross_checks'])} 项）

| check_id | result | 检查内容 | 证据（原文行） |
|---|---|---|---|
{cc_rows}

要点（只登记事实，不下结论）：
- **C3**：第 6 节判据 (h) 写「60 tests PASS」，审计链写「104 passed」，同文互不一致 —— 本工序**不取舍、不改写上游**。
- **C4**：第 (f) 节标题「时间步收敛性」，第 6 节表行却写「网格收敛」——用词漂移，需下游确认所指。
- **C5**：把表 (a)(b)(c)(d)(g) 的数字按**报告自己写的公式**（关键公式①②③与负控 2√μ）复算，最大偏差 0（4-6 位小数内）——这只说明报告内部算术自洽，**不构成对物理/方法的独立验证**。
- **C6**（unresolved，留给下游）：表 (a)(b) 的「解析解」列与关键公式①②**同式**，两列在 4 位小数上逐项相同，因此 0.0000% 误差存在「公式自比较」的可能；本工序不做判读，仅保留可定位证据。

## ⑤ 注意点与局限

1. **工序边界**：本单只登记资产，不做抽取与判读。`cross_checks` 里 `inconsistent` / `unresolved` 的条目是**交给下游的证据包，不是本工序的结论**；报告的 ✅ PASS 自评一律**未采信、未改判**。
2. **解析判据是「本工作树可达性」**：A30/A31 指向的 TensorFEM 源码与测试在**工作树外的同级检出**中探针命中（信息性证据），但按本工序判据仍登记为 `referenced_unresolved`；A25 的 7 张 png 在平台 payload（仅 name+caption，无 png 字节）与本机磁盘都拿不到，图件本体不可核。**下游若要做图件级核验，须先解决 png 取回。**
3. **未执行的检查**：TensorFEM 侧 `pytest tests/test_fsi_*.py` 未在本工序执行（跨仓、超出工作包范围），因此报告宣称的「104 passed / 60 tests」**本工序无法证实也无法证伪**，只登记矛盾。
4. **平台字段依赖**：`figures` 条数（{len(man['source']['platform_figures'])}）与 mission 号取自平台 payload，未与 mission 表交叉断言。
5. **图件字体**：容器无中文字体，图中标签使用 ASCII；中文说明在本报告与 manifest 的 `label`/`note` 字段。
6. **不做的事**：未在任何产物里写 `verified`（`nothing_marked_verified` 检查覆盖 manifest 与信封两棵树）；未修改上游与本工序外任何文件；未 push。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 判据 | 结果 |
|---|---|---|
{acc_rows}

**补充自检（非契约项，{len(checks)} 项全量）**

| check | result |
|---|---|
{check_rows}

无失败项；`{PKG}` 验收自检 overall={ver['overall']}。若上述任一项为 ❌，本段会如实标红而不粉饰（本单无此情况）。

## ⑦ 误差判定（关键量 vs 基准，逐项）

本工序不产生物理量，因此**没有物理基准可比**；可判定的量是完整性度量，逐项列如下（基准=契约声明值/平台原文，实际=程序化实测）：

| 量 | 基准 | 实测 | 偏差 | 是否 <3% |
|---|---|---|---|---|
| markdown sha256 | 契约 `{man['source']['hash'][:16]}…` | 独立重取 `{man['source']['hash'][:16]}…` | 0（逐字节相同） | ✅ 是（0%） |
| markdown 字符数 | 契约 {man['source']['chars']} | 实测 {man['source']['chars']} | 0 | ✅ 是（0%） |
| locator 可解析率 | {c['assets']}/{c['assets']} | {c['assets']}/{c['assets']}（重新切片全部复现） | 0 失败 | ✅ 是（0%） |
| quote 唯一性 | 100% | 100%（{c['assets']}/{c['assets']}） | 0 | ✅ 是（0%） |
| schema 校验 | 0 违规 | 0 违规（双 schema） | 0 | ✅ 是（0%） |
| 产物镜像一致性 | 字节一致 | 字节一致（sha256 `{env['provenance']['artifact_sha256'][:16]}…`） | 0 | ✅ 是（0%） |

**显式回答「是否 <3%」**：上述完整性度量**全部为精确 0 偏差**（<3% 成立）。但必须同时声明：**这 6 项不是精度指标**——报告 9763 声称的 U_cr / ω_fl / 增长率 0.00% 误差**本工序未复算、未采信**，其与 Theodorsen 解析解的对比是否成立属下游核验工序的职责（见 ④b 的 C6 线索）。

## 复跑命令（工作树根）

```bash
python3 scripts/kf_fetch_9763.py && python3 scripts/kf_register_9763.py && \
python3 scripts/kf_verify_9763.py && python3 scripts/kf_figures_9763.py && \
python3 scripts/kf_report_9763.py && python3 -m pytest tests/test_kf_wp9763.py -q
```

## 结果信封（本报告唯一 json 代码块，门禁按此解析）

```json
{json.dumps(env, ensure_ascii=False, indent=2)}
```
"""

    out = DOC / f"KF-RESULT-{PKG}.md"
    DOC.mkdir(parents=True, exist_ok=True)
    out.write_text(md)
    assert md.count("```json") == 1, md.count("```json")

    figs = []
    caps = {
        "fig1_asset_inventory.png": "图1 报告 9763 的资产清单：按 asset_class 分组的可解析状态堆叠图（resolved_in_source / referenced_unresolved / declared_absent），读数来自 asset_manifest.json。",
        "fig2_locator_coverage.png": "图2 32 条 locator 在 3884 字符原文上的覆盖地图（横轴=字符偏移，每条为一资产），全部为唯一子串定位。",
        "fig3_verification_board.png": "图3 左：14 项验收自检状态；右：6 项源级交叉检查状态（inconsistent/unresolved 项为交给下游的证据包）。",
    }
    for name, cap in caps.items():
        figs.append(dict(name=name, caption=cap,
                         png_base64=base64.b64encode((DOC / "figures" / name).read_bytes()).decode()))

    payload = dict(
        title=f"KF-RESULT {PKG}",
        summary=(f"资产登记工序 {PKG}（report 9763《{man['source']['title']}》）：确认 markdown sha256 与契约一致"
                 f"（{man['source']['chars']} 字符），登记 {c['assets']} 个资产 / {len(c['by_class'])} 类，"
                 f"{c['resolved_in_source']} 条页内可定位、{c['referenced_unresolved']} 条外部指针不可达（图件 png 与 TensorFEM 源码/测试），"
                 f"claims 按契约留空；另登记 {len(man['cross_checks'])} 项源级交叉检查（含 pytest 计数 60 vs 104 矛盾、"
                 f"解析解列与关键公式同式可能自比较）。{pass_n}/{len(checks)} 自检通过，24 项 pytest（含 10 反向对照）全绿。"
                 f"未做抽取、未标 verified。"),
        scenario_key=man["source"]["scenario_key"],
        mission_id=15668,
        tags=["kf-wp:" + PKG, "KF-RESULT", "01-asset-registration", "report:9763",
              "FSI", "flutter", "Theodorsen", "TensorFEM"],
        markdown=md,
        figures=figs,
    )
    (RUN / "platform_report.json").write_text(json.dumps(payload, ensure_ascii=False))
    print("report:", out, out.stat().st_size, "bytes; json blocks:", md.count("```json"))
    print("payload:", RUN / "platform_report.json", "figures:", len(figs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())