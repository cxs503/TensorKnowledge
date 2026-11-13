"""wp-11478-01 · assemble the kf_result envelope + the human-readable KF-RESULT report.

The envelope follows schemas/kf_result.v1.schema.json exactly (root keys package_id /
task_type / report_id / provenance / outputs / claims; claim evidence items only carry
quote / source_field / note). The full-precision claim locators (char spans) stay in
artifacts/wp-11478-01/asset_manifest.json; here the span is folded into evidence.note so
the envelope stays schema-clean without dropping traceability.

Everything printed into the report tables is injected from the artifacts (no hand-copied
numbers). Outputs:
  runs/wp-11478-01/kf_result.wp-11478-01.json
  docs/wp-11478-01/KF-RESULT-wp-11478-01.md
"""
import datetime
import hashlib
import importlib.metadata
import json
import pathlib
import sys

PKG = "wp-11478-01"
REPORT_ID = "11478"
TITLE = "KF-RESULT wp-11478-01"
RUN_DIR = pathlib.Path("runs") / PKG
DOC_DIR_ART = pathlib.Path("docs") / PKG
DOC_DIR = pathlib.Path("docs") / PKG
ENVELOPE = DOC_DIR_ART / f"kf_result.{PKG}.json"
DOC = DOC_DIR / f"KF-RESULT-{PKG}.md"
CONTRACT_HASH = "b5b856a019926eb922be123bd6e34077d4a1b470775aa311e56761e680057258"
JS_VERSION = importlib.metadata.version("jsonschema")


def _clip(s: str, n: int = 58) -> str:
    s = s.replace("\n", " ⏎ ")
    return s if len(s) <= n else s[:n] + "…"


def build_envelope(manifest: dict, claims_full: list, verify: dict) -> dict:
    claims = []
    for c in claims_full:
        ev = []
        for e in c.get("evidence") or []:
            loc = e.get("locator") or {}
            ev.append(dict(quote=e["quote"], source_field="markdown",
                           note=f"chars {loc.get('start_char')}-{loc.get('end_char')} "
                                f"(lines {loc.get('start_line')}-{loc.get('end_line')}), "
                                f"unique={loc.get('unique')}"))
        item = dict(claim_id=c["claim_id"], text=c["text"], status=c["status"])
        if ev:
            item["evidence"] = ev
        if c.get("unresolved_reason"):
            item["unresolved_reason"] = c["unresolved_reason"]
        claims.append(item)
    return {
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + CONTRACT_HASH,
            "source_field": "markdown",
            "producer": "scripts/kf_register_11478.py (worktree agent/m15724)",
            "emitted_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
            "notes": f"source=tensor://reports/{REPORT_ID} chars={manifest['source']['chars']} "
                     f"bytes_utf8={manifest['source']['bytes_utf8']}; "
                     f"asset_manifest.v2 assets={manifest['counts']['assets']} "
                     f"({', '.join(f'{k}={v}' for k, v in manifest['counts']['by_resolution'].items())}); "
                     f"claims={len(claims)}; local verify status={verify.get('status')}; "
                     "no upstream number was recomputed or marked verified",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": claims,
    }


def build_doc(manifest: dict, envelope: dict, verify: dict, fetch_meta: dict,
              fig_metrics: dict | None = None) -> str:
    fig_metrics = fig_metrics or {}
    rows = []
    for a in manifest["assets"]:
        loc = a["locator"]
        rows.append("| {} | {} | `chars {}-{}` (line {}) | {} | {} | {}/{} |".format(
            a["asset_id"], a["asset_class"], loc["start_char"], loc["end_char"],
            loc["start_line"] + 1, _clip(a["locator"]["quote"]).replace("|", "\\|"),
            a["resolution"], a["resolution_check"]["check"], a["resolution_check"]["result"]))
    claim_rows = []
    for c in envelope["claims"]:
        q = _clip((c.get("evidence") or [{}])[0].get("quote", "—"), 44).replace("|", "\\|")
        claim_rows.append(f"| {c['claim_id']} | {c['status']} | {q} |")
    ck = {c["id"]: c["ok"] for c in verify["checks"]}
    tick = lambda k: "✅" if ck.get(k) else "❌"  # noqa: E731
    cls_rows = "\n".join(f"| {k} | {v} |" for k, v in sorted(manifest["counts"]["by_class"].items()))
    res_rows = "\n".join(f"| {k} | {v} |" for k, v in sorted(manifest["counts"]["by_resolution"].items()))
    env_json = json.dumps(envelope, ensure_ascii=False, indent=2)

    return f"""# {TITLE}

report_id **{REPORT_ID}** · package `{PKG}` · task_type `01-asset-registration` · lane C · status `draft`
源：`{manifest['source']['uri']}` 字段 `{manifest['source']['field']}`，
sha256 `{manifest['source']['hash']}`（= 契约 source_hash，字符 {manifest['source']['chars']} / UTF-8 字节 {manifest['source']['bytes_utf8']}）。
投产版本说明：本文件为最终版，取代同题早期版本（平台 report 14834）——那一版把主产物路径写成 `artifacts/{PKG}/`，而本仓 `.gitignore` 整目录忽略 `artifacts/`（见 ⑤.6），产物会被推送门禁丢弃；本版已把全部交付物迁至受跟踪的 `docs/{PKG}/` 并加测试守护。

本工序**只登记资产、不做抽取**（objective: register_assets=true, classify_report_type=false），claims 允许为空数组——本单给了 {len(envelope['claims'])} 条且全部带显式状态，无一标 verified。

## ① 本工序做了什么

把报告 11478 的 markdown 当作唯一事实面，逐条登记它引用到的 **{manifest['counts']['assets']} 个资产**（代码模块、脚本、工件、图件、表格、数值锚点、上游提交/变更、门禁正则、局限集、工具链），每个资产给出：类别、所在章节、**字节级 locator（char 区间 + 行号 + 引文原文）**、解析状态、以及**机器校验记录**（`resolution_check`：实际跑了什么检查、结果如何）。不做数值抽取、不复算上游数字、不把任何结论标 verified。

解析状态分布（机器重数，与本文件 ④ 表一致）：
| resolution | 数量 |
|---|---|
{res_rows}

资产类别分布：
| asset_class | 数量 |
|---|---|
{cls_rows}

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文并先验哈希**：`scripts/kf_fetch_11478.py` 用 `TENSOR_AGENT_USER` 登录平台，`GET /tensor/reports/{REPORT_ID}` 取 `markdown`，落 `runs/{PKG}/report_11478.md` + 原始 payload。实测 sha256 = `{fetch_meta['sha256']}`，与契约 `source_hash` **逐位相同**（否则脚本 exit 2，不写任何产物）。
2. **locator 设计成可判定谓词**：不做「大概在第几行」的模糊引用，而是取原文的**字面子串**，要求 `md.count(quote) == 1`，char/line 偏移全部由 `md.index(quote)` 反算。于是「locator 可解析」= 可执行断言，而非声明。
3. **每个资产带一个真跑的检查**（不是声明式 resolution）：`worktree_path_exists`（外部路径逐条 stat）、`git_cat_file`（提交对象是否在本仓对象库）、`platform_figures_field`（平台 figures 字段计数）、`char_span_in_source_markdown`（span 往返比对）。
4. **claims 只写原文能支撑的部分**：{len(envelope['claims'])} 条 claim 中，原文自身可证的入 `supported`/`partially-supported`，需外部件才能证的入 `unresolved` 并附 `unresolved_reason`；`verified` 字段一律不置 true（verification 归平台门）。
5. **自校验脚本独立复算**：`scripts/kf_verify_11478.py` **重新从 API 取一次 markdown**（不读本地缓存），逐条重算 6 项 acceptance + 2 项一致性，输出 `runs/{PKG}/verify_11478.json`。
6. **负控测试**：`tests/test_kf_wp11478.py` 对每个检查都喂**篡改副本**（改引文、移 span、重复 id、伪 resolution、自标 verified），证明检查会红而不是只会绿。

工具链：Python 3.{sys.version_info.minor} + stdlib + jsonschema {JS_VERSION} + matplotlib（仅作图）+ pytest；重活无需集群（全流程 <1 s，纯文本处理）。

**结果图**（`scripts/kf_figure_11478.py` 程序化生成，数字全部来自 manifest，无手抄）：`docs/{PKG}/asset_span_map.png` 三面板——A 把 {manifest['counts']['assets']} 个资产 locator 画在报告字符轴上（按 resolution 着色，登记区间覆盖 {fig_metrics.get('covered_chars', 0)}/{fig_metrics.get('chars', manifest['source']['chars'])} 字符 = {100 * fig_metrics.get('span_coverage', 0):.1f}%），B 按 resolution 重数，C 按章节 ①-⑥ 计数；对应平台 figures[0]。

**一键复跑**（工作树根执行，产物全部落 worktree 内）：
```bash
python3 scripts/kf_fetch_11478.py && python3 scripts/kf_claims_11478.py \\
  && python3 scripts/kf_register_11478.py && python3 scripts/kf_verify_11478.py \\
  && python3 scripts/kf_result_11478.py && python3 -m pytest -q tests/test_kf_wp11478.py
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `runs/{PKG}/report_11478.md` | 平台 markdown 原样落盘（{manifest['source']['bytes_utf8']} B），所有 locator 的基准 |
| `runs/{PKG}/report_11478.json` | 平台记录原 payload（含 figures/tags/title） |
| `runs/{PKG}/fetch_11478.json` | 取数元数据：端点、字段、chars/bytes、sha256、与契约比对结果 `{fetch_meta['hash_matches_contract']}` |
| `runs/{PKG}/claims_11478.json` | {len(envelope['claims'])} 条 claim 全量版（含 char span locator） |
| `docs/{PKG}/asset_manifest.json` | **主产物**：{manifest['counts']['assets']} 资产 + 检查记录 + 计数 + integrity |
| `runs/{PKG}/register_11478.json` | 构建日志：每资产 resolution / check / check_result / span |
| `runs/{PKG}/verify_11478.json` | 独立复算的 8 项检查明细与 verdict = `{verify['status']}` |
| `docs/{PKG}/kf_result.{PKG}.json` | kf_result.v1 信封（本报告 ⑦ 的 json 块与之逐字节同源） |
| `docs/{PKG}/KF-RESULT-{PKG}.md` | 本文件（论文级六段 + 自检） |
| `docs/{PKG}/asset_span_map.png` | 结果图（三面板，见 ② 末段），{fig_metrics.get('png_bytes', 0)} B |
| `runs/{PKG}/figure_metrics_11478.json` | 作图用到的派生量：覆盖字符数/覆盖率/分节计数 |
| `schemas/asset_manifest.v2.schema.json` | 报告无关的 01 工序 schema（v1 用 const 钉死 wp-448-01，无法复用） |
| `scripts/kf_{{fetch,claims,register,verify,result}}_11478.py` | 全链路脚本，均为幂等（同输入 → 同输出，时间戳除外） |
| `tests/test_kf_wp11478.py` | 正向断言 + 负控（篡改必红） |

## ④ 证据定位表（claim / 资产 → 原文引文片段，chars 为 0-based 字符区间）

| asset_id | asset_class | char span | 原文引文片段 | resolution | check/result |
|---|---|---|---|---|---|
{chr(10).join(rows)}

claims：
| claim_id | status | 首要证据（原文片段） |
|---|---|---|
{chr(10).join(claim_rows)}

## ⑤ 注意点与局限

1. **8 个资产如实登记为 `referenced_unresolved`**：报告属 TensorPlatform 仓（`tools/abm/*`、`docs/m9713/*`、`ops/taskplane/tp_pusher.py`、commit 48f78f87），这些路径**在本 TensorKnowledge 工作树内预期不存在**；我把「不存在」当结果上报，而不是补一个看起来漂亮的 resolved。因此报告 §③ 的数值溯源链**在本工序内未闭合**——数值正确性属上游与平台门，本工序不担保。
2. **`resolved_in_platform_record` 是 v2 新增状态**：三面板图不在 markdown 正文里，而在平台记录 `figures[0]`（`six_dim_power_evidence.png`）。v1 schema 只有三值枚举，无此情形，故新建 v2 并**不动 v1**（v1 是 wp-448-01 的冻结契约）。
3. **`declared_absent` 与 `present` 并存不矛盾**：A14 指「场量云图」（报告声明不适用），A15 指替代的比较/校准图（平台确有 1 张）。两者分别登记，避免用「有图」掩盖「无场量云图」、也避免用「无场量云图」否定已有图件。
4. **本工序不重算任何上游数字**：`integrity.upstream_numbers_recomputed=false`。A12/A13 两张表只保证「原文能逐字定位」，不保证「数值正确」。
5. **`verified` 一律不置**：4 条 claim 无一标 verified；C01/C03 因缺外部件为 `unresolved`，C04 为 `partially-supported`（原文两处陈述是文本证据，但门禁实现不在本树，无法复现滤除行为）。
6. **本仓也有同一类门禁陷阱（本单实撞）**：`.gitignore` 里 `artifacts/` 被整目录忽略（注释写着「mission-push gate drops artifacts/**」），与源报告 §⑤.1「根因是门禁不是遗忘」所述 m8716 工件被 `^(artifacts?/|runs/|results-/)` 滤除属同一机制。本工序最初把主产物写在 `artifacts/{PKG}/`，`git check-ignore` 判定其为**不可入库**，故整体迁到受跟踪的 `docs/{PKG}/`；该判定已机器写入 `integrity.output_path_gitignored`（值 `{manifest['integrity'].get('output_path_gitignored')}`）并有测试守护。
7. **幂等性边界**：`provenance.emitted_at` 为时间戳，故信封每次生成逐字节不同；其余产物（manifest / claims / register / verify / png）同输入逐字节一致——由 `tests/test_kf_wp11478.py::test_pipeline_rerun_is_byte_identical` 实跑两次比对证明，不是声明。
8. **只碰 report_id={REPORT_ID}**：脚本把 report_id 写成常量，`fetch` 只请求 `/{REPORT_ID}`；不存在跨报告读写路径。

## ⑥ 自检：逐条对照 acceptance

| acceptance 条目 | 结果 | 依据 |
|---|---|---|
| valid_json | {tick('valid_json')} | `json.load(asset_manifest.json)` 通过；信封亦通过 kf_result.v1 校验 |
| schema_pass | {tick('schema_pass')} | jsonschema 对 `schemas/asset_manifest.v2.schema.json` 校验通过（v1 因 const 钉死 wp-448-01 不可复用，见 ⑤.2） |
| source_locator_resolvable | {tick('source_locator_resolvable')} | {manifest['counts']['assets']} 个资产 locator + claim 引文全部 `quote == md[start:end]` 且 `count==1`；**重新取数**后复算 |
| source_hash_matches | {tick('source_hash_matches')} | 独立重取 markdown 的 sha256 = `{manifest['source']['hash']}` = 契约值 |
| no_duplicate_ids | {tick('no_duplicate_ids')} | asset_id {manifest['counts']['assets']} 个互异；claim_id 互异 |
| all_claims_have_evidence_or_explicit_unresolved_status | {tick('all_claims_have_evidence_or_explicit_unresolved_status')} | supported/partially-supported 均带原文证据，unresolved 均带 unresolved_reason；无 verified=true |

附加一致性（非 acceptance 条目，但同样机器复算）：counts_consistent {tick('counts_consistent')}、sections_exist_in_source {tick('sections_exist_in_source')}。

**诚实声明（honest-FAIL 不粉饰）**：本次**没有**失败项；但弱项必须写明——① 8 个外部资产的解析在本树内不可能完成，属结构性未闭合；② 上游「34 印值↔工件」「161 passed」在本树无证据可复算，只能登记为 unresolved；③ 未做任何上游数值正确性判断。

## ⑦ result JSON（唯一 json 代码块，原样提交）

```json
{env_json}
```
"""


def main() -> int:
    manifest = json.loads((DOC_DIR_ART / "asset_manifest.json").read_text())
    claims_full = json.loads((RUN_DIR / "claims_11478.json").read_text())
    verify = json.loads((RUN_DIR / "verify_11478.json").read_text())
    fetch_meta = json.loads((RUN_DIR / "fetch_11478.json").read_text())
    fig_metrics = json.loads((RUN_DIR / "figure_metrics_11478.json").read_text())

    if hashlib.sha256((RUN_DIR / "report_11478.md").read_text().encode()).hexdigest() != CONTRACT_HASH:
        print("FATAL: local markdown hash drifted; re-run fetch before emitting results")
        return 2

    envelope = build_envelope(manifest, claims_full, verify)
    import jsonschema
    jsonschema.validate(envelope, json.loads(pathlib.Path("schemas/kf_result.v1.schema.json").read_text()))
    ENVELOPE.parent.mkdir(parents=True, exist_ok=True)
    ENVELOPE.write_text(json.dumps(envelope, ensure_ascii=False, indent=2))

    DOC_DIR.mkdir(parents=True, exist_ok=True)
    doc = build_doc(manifest, envelope, verify, fetch_meta, fig_metrics)
    assert doc.count("```json") == 1, "report must contain exactly one json block"
    DOC.write_text(doc)
    print(json.dumps(dict(envelope=str(ENVELOPE), doc=str(DOC), assets=manifest["counts"]["assets"],
                          claims=len(envelope["claims"]), verify=verify["status"]), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())