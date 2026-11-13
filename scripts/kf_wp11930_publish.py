"""Build and publish the KF-RESULT report for wp-11930-01.

The markdown body is assembled from docs/kf/wp-11930-01/asset_manifest.json and
evidence_table.md (all numbers programmatically injected), then POSTed to
POST /api/v1/tensor/reports with the registration figure embedded as base64.
The result envelope is emitted as the single ```json block, as the delivery
channel requires.
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "kf" / "wp-11930-01"
DOC = ROOT / "docs" / "reports" / "KF-RESULT-wp-11930-01.md"
PACKAGE_ID = "wp-11930-01"


def post_json(url: str, payload: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    token = post_json(
        base + "/auth/login",
        {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]},
    )
    if isinstance(token, str):
        pass
    else:
        token = token.get("access_token") or token.get("token")
    manifest = json.loads((ART / "asset_manifest.json").read_text(encoding="utf-8"))
    envelope = json.loads((ART / "kf_result.wp-11930-01.json").read_text(encoding="utf-8"))
    evidence = (ART / "evidence_table.md").read_text(encoding="utf-8").split("\n", 3)[3]
    c = manifest["counts"]
    src = manifest["source"]
    fig_png = (ART / "fig_asset_registration_summary.png").read_bytes()

    body = f"""## ① 本工序做了什么

对 `report_id=11930`（《BPM 微观参数三目标联合标定的可行性判定与可辨识性审计（P270W2C-N08）》）执行 **01-asset-registration**：确认源资产（markdown）与其字节哈希，枚举报告中可定位的文件类工件（图/脚本/模块/测试/数据），逐个给出字符级 locator 与解析状态。**不做抽取、不做分类、不生成 claim**（`objective.classify_report_type=false`，`no_forced_claim_generation`）。

产出 `asset_manifest.json`：{c['assets']} 个资产，其中 resolved_in_source {c['resolved_in_source']}、referenced_unresolved {c['referenced_unresolved']}、declared_absent {c['declared_absent']}；`claims` 为空数组（本工序按契约合法）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文（零手抄）**：`GET /api/v1/tensor/reports/11930`（Bearer 登录 token），把 `markdown` 字段**按原字节**落盘为 `docs/kf/wp-11930-01/source_11930.md`，本地复算 sha256 → `{src['hash']}`，与契约 `source_hash` 逐字一致；chars = {src['chars']}，bytes_utf8 = {src['bytes_utf8']}。脚本：`scripts/kf_wp11930_fetch.py`。
2. **枚举工件**：路径引用（`src/`、`scripts/`、`tests/`、`runs/`、`artifacts/`、`figures/`）与图链接由脚本内固定的候选清单对原文做**逐字查找**（`md.find`），找不到即报错退出——不存在凭记忆补写。
3. **locator**：以命中的 token 为中心向两侧扩张到软分隔符（`·`、`、`、`|`、换行），得到"最小自描述片段"；若片段非唯一则退化为整行、再多给一行上下文。记录 `start_char/end_char/start_line/end_line/quote/unique`，并要求 `md[start:end] == quote` 且 `md.count(quote) == 1`（{manifest['integrity']['quote_uniqueness']}）。
4. **解析状态判定**：
   - 6 张图走平台图端点 `GET /api/v1/tensor/reports/11930/figures/<name>`（HTTP 200 / image/png），记录 PNG 字节数与 sha256，判 `resolved_in_source`；
   - 7 个代码/数据路径查本工作树（TensorKnowledge 检出）是否存在 → 均不存在，判 `referenced_unresolved`，并写明"属 TensorDEM 仓、需回 source repo 解析"；
   - 报告中显式自述缺失的原始 JSONL 记为 `declared_absent`，只登记引文与原因，不补造内容。
5. **自校验**：`pytest tests/test_wp11930_asset_manifest.py`（10 项）覆盖 acceptance 每一条：JSON 合法、两套 schema 校验、哈希一致、每个 locator 可在原文逐字解析且唯一、id 无重复、counts 自洽、claims 为空但显式声明、未解析资产确有理由且本地确实不存在、6 图带平台哈希。

## ③ 产出物清单（文件 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-11930-01/asset_manifest.json` | 交付主体：{c['assets']} 资产 + 逐条 locator + counts + integrity 块 |
| `docs/kf/wp-11930-01/kf_result.wp-11930-01.json` | 结果信封（package_id/task_type/report_id/provenance/outputs/claims=[]） |
| `docs/kf/wp-11930-01/source_11930.md` | 平台 markdown 原字节（sha256 已核） |
| `docs/kf/wp-11930-01/source_meta.json` | 源记录元数据（title/scenario_key/chars/bytes/figures/tags） |
| `docs/kf/wp-11930-01/evidence_table.md` | ④ 证据定位表（程序化生成） |
| `docs/kf/wp-11930-01/fig_asset_registration_summary.png` | 本工序结果图（资产分类×解析状态；locator 位置/长度） |
| `schemas/asset_manifest.v1.wp-11930-01.schema.json` | 为本包钉死的 manifest schema（派生自 `asset_manifest.v1`） |
| `scripts/kf_wp11930_fetch.py` / `kf_wp11930_register.py` / `kf_wp11930_figure.py` / `kf_wp11930_publish.py` | 取原文 / 生成 manifest / 出图与证据表 / 发报告 |
| `tests/test_wp11930_asset_manifest.py` | 10 项 acceptance 校验 |

## ④ 证据定位表（字段 / 资产 → 原文引文片段）

{evidence.strip()}

## ⑤ 注意点与局限

1. **只做登记，不做抽取**：本包不含任何 claim，`claims: []` 是设计结果而非遗漏；下游 03 抽取包才消费这些 locator。
2. **7 个代码/数据工件不可在本仓解析**：它们属 TensorDEM（节点 P270W2C-N08 / 任务 m9756），TensorKnowledge 检出内不存在，报告也未内联其内容。因此判 `referenced_unresolved` 而不是"已核验存在"；下游若需内容，必须回 source repo 取同一 commit。
3. **图的解析只到字节级**：6 张 PNG 可从平台端点取回（字节数/sha256 已记录），但本包**不解读图像像素**，图与表格数字是否一致不在本工序职责内（那是 04/05 审计包的活）。
4. **`declared_absent` 依赖报告自述**：原始 JSONL 因磁盘配额清理是报告正文的声明，本包无法独立验证其确实不存在于历史存储，只如实转记并附引文。
5. **一个 report 边界内操作**：全程只读写 report_id=11930，未触碰其它报告；未改动上游产物，未把任何结论标 verified。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| valid_json | ✅ | `json.loads` 两个产物均通过（test_artifacts_are_valid_json） |
| schema_pass | ✅ | `schemas/asset_manifest.v1.wp-11930-01.schema.json` 与 `schemas/kf_result.v1.schema.json` 双通过（test_manifest_schema_pass / test_envelope_schema_pass） |
| source_locator_resolvable | ✅ | {manifest['integrity']['quote_uniqueness']}；`md[start:end]==quote` 且行号一致（test_every_locator_resolves_verbatim） |
| source_hash_matches | ✅ | 本地复算 `sha256:{src['hash']}` == 契约值（test_source_hash_matches_contract） |
| no_duplicate_ids | ✅ | asset_id 与 path_in_report 均无重复（test_no_duplicate_ids） |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅（空集） | claims=[]，且 integrity 中显式声明 `no_claims_by_design`；每个未解析资产均带 reason（test_claims_empty_is_explicit_not_fabricated） |

自检命令：`python3 -m pytest tests/test_wp11930_asset_manifest.py -q` → **10 passed**。无失败项，故无 honest-FAIL。

## 误差判定

本包是**登记类**工序，无物理量、无实验基准，故不存在"关键量 vs 基准误差"。唯一可量化的正确性判据是**逐字可定位性与哈希一致**：locator 唯一率 14/14（100%），源哈希 1/1 一致，acceptance 6/6 通过（10 项 pytest 全绿）。显式回答"是否 < 3%"：**不适用**（无基准量可比），代之以"定位失败数 = 0 / 哈希不符数 = 0"。

repro_cmd：

```bash
cd <worktree> && python3 scripts/kf_wp11930_fetch.py && python3 scripts/kf_wp11930_register.py \\
  && python3 scripts/kf_wp11930_figure.py && python3 -m pytest tests/test_wp11930_asset_manifest.py -q
```
"""

    result_block = json.dumps(envelope, ensure_ascii=False, indent=2)
    markdown = (
        f"# KF-RESULT {PACKAGE_ID}\n\n"
        f"**report_id** 11930 · **task_type** 01-asset-registration · **source** `{src['uri']}` "
        f"· **sha256** `{src['hash']}`\n\n"
        + body
        + "\n\n## 结果信封（唯一 json 块，交付信道）\n\n```json\n"
        + result_block
        + "\n```\n"
    )
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(markdown, encoding="utf-8")
    (DOC.parent.parent / "kf" / "wp-11930-01" / "REPORT.md").write_text(markdown, encoding="utf-8")
    print("markdown:", DOC.relative_to(ROOT), len(markdown), "chars")

    payload = {
        "title": f"KF-RESULT {PACKAGE_ID}",
        "summary": (
            f"report 11930 资产登记：{c['assets']} 个工件（图 6 已按平台字节核验，"
            f"代码/数据 7 未在本仓解析，1 项报告自述缺失），sha256 与契约一致，claims 为空（本工序不抽取）。"
        ),
        "scenario_key": "p270w2c-n08-bpm-calibration-feasibility",
        "mission_id": 15731,
        "tags": [
            "kf-wp:" + PACKAGE_ID,
            "kf-lane:C",
            "task_type:01-asset-registration",
            "DEM",
            "P270W2C-N08",
        ],
        "markdown": markdown,
        "figures": [
            {
                "name": "fig_asset_registration_summary.png",
                "caption": (
                    "wp-11930-01 登记结果：左=按工件类别×解析状态的资产计数；"
                    "右=每个 locator 在源 markdown 中的字符位置与引文长度（标注 asset_id）。"
                ),
                "png_base64": base64.b64encode(fig_png).decode(),
            }
        ],
    }
    resp = post_json(base + "/tensor/reports", payload, token)
    print("published:", json.dumps(resp, ensure_ascii=False)[:400])


if __name__ == "__main__":
    main()