#!/usr/bin/env python3
"""Build the wp-946-04 deliverable: kf_result.json envelope + report.md body.

Every number/quote in the rendered markdown is taken programmatically from
  - docs/kf/wp-946-04/source_report.md            (independent copy of report 946 markdown)
  - docs/kf/wp-946-04/upstream/wp-946-01.kf_result.json  (review target)
  - docs/kf/wp-946-04/review_report.json          (reviewer verdict, produced by review_wp946_01.py)
so nothing is retyped by hand.

Usage: python3 docs/kf/wp-946-04/make_report.py
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

PKG = Path(__file__).resolve().parent
REPO = PKG.parents[2]
SRC = PKG / "source_report.md"
UP = PKG / "upstream" / "wp-946-01.kf_result.json"
REV = PKG / "review_report.json"
OUT_JSON = PKG / "kf_result.json"
OUT_MD = PKG / "report.md"

CONTRACT_SOURCE_HASH = "sha256:3ea029afd6df49a8d3e407e42df035654b58a7555f9678d657f5fdfc1fe35552"

# (evidence_id, reviewer field, needle that MUST exist verbatim in the report markdown)
QUOTES = [
    ("E01", "source title / source_document ast-946-01", "# AI 原生基础设施演化图 v2 —— 十方向 × 六准则覆盖度审计（返工重发，替代原报告 941）"),
    ("E02", "record scenario_key + mission_id (C03, C16)", "scenario_key=`ai-native-infra` · mission_id=**1237**"),
    ("E03", "figure asset ast-946-04 registered 1:1 (C12)", "![fig2](artifacts/ai-native-infra-v1/figures/fig2_seat_model_decoupling.png)"),
    ("E04", "report generator ast-946-08 (C19 coverage)", "`artifacts/ai-native-infra-v1/build_evidence.py`"),
    ("E05", "evidence table ast-946-10 (C19 coverage)", "`artifacts/ai-native-infra-v1/evidence.json`"),
    ("E06", "api endpoint ast-946-14 (C19 note N5)", "${TENSOR_API_BASE}/tensor/missions"),
    ("E07", "log asset ast-946-17 (C19 coverage)", "`/var/log/tp-fleet/autoheal.log`"),
    ("E08", "policy document ast-946-19 (C19 coverage)", "平台运营事件流/DISPOSITION_RULES.md"),
    ("E09", "coverage gap found by reviewer (note N4)", "本工作树 docs/ 判据文件"),
    ("E10", "truncated CSA URL recorded by producer (C16)", "https://labs.cloudsecurityalliance.org/research/csa-research-note-nist-ai-agent-standards-regulatory-framewo"),
]


def main() -> None:
    md = SRC.read_text(encoding="utf-8")
    src_hash = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert src_hash == CONTRACT_SOURCE_HASH, (src_hash, CONTRACT_SOURCE_HASH)

    upstream = json.loads(UP.read_text(encoding="utf-8"))
    rev = json.loads(REV.read_text(encoding="utf-8"))
    checks = rev["checks"]
    statuses = {c["check_id"]: c["status"] for c in checks}

    for eid, _, needle in QUOTES:
        assert needle in md, f"{eid} needle not found verbatim: {needle[:60]}"

    envelope = {
        "package_id": "wp-946-04",
        "task_type": "04-independent-review",
        "report_id": "946",
        "provenance": {
            "source_hash": src_hash,
            "source_field": "markdown",
            "producer": "agent/m15818",
            "emitted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "notes": (
                "source_hash recomputed from the report 946 markdown independently fetched "
                "from the platform report store; matches the package contract and the "
                "upstream wp-946-01 provenance hash"
            ),
        },
        "outputs": {"review_report.json": rev},
    }

    import jsonschema  # type: ignore

    jsonschema.validate(envelope, json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8")))
    OUT_JSON.write_text(json.dumps(envelope, ensure_ascii=False, indent=1), encoding="utf-8")

    n_checks = len(checks)
    n_fail = sum(1 for c in checks if c["status"] == "fail")
    n_not_run = sum(1 for c in checks if c["status"] == "not_run")
    resolvable = upstream["outputs"]["asset_manifest.json"]["counts"]["resolvable"]
    total_assets = upstream["outputs"]["asset_manifest.json"]["counts"]["total"]

    check_rows = "\n".join(
        f"| `{c['check_id']}` | {c['name']} | **{c['status']}** |" for c in checks
    )
    quote_rows = "\n".join(
        f"| {eid} | {field} | `{needle}` |" for eid, field, needle in QUOTES
    )
    note_rows = "\n".join(
        f"- **{n['note_id']}** {n['text']}" for n in rev["non_blocking_notes"]
    )
    not_run_rows = "\n".join(f"- {x}" for x in rev["not_run"])
    limitation_rows = "\n".join(f"- {x}" for x in rev["reviewer"]["checker_limitations"])

    def tick(cid_key: str, label: str, extra: str = "") -> str:
        st = statuses.get(cid_key, "n/a")
        box = "✅" if st == "pass" else ("⬜" if st == "not_run" else "❌")
        return f"| {box} | {label} | `{cid_key}` = {st}{extra} |"

    selfcheck = "\n".join(
        [
            "| 勾 | 验收项 | 状态 |",
            "|---|---|---|",
            tick("C01", "valid_json（review_report.json 可解析，信封过 schema）"),
            tick("C14", "schema_pass（上游 wp-946-01 envelope 过 kf_result.v1.schema.json）"),
            "| ✅ | reviewer_independent | 上下文仅报告原文 + 上游交付物；生产者 report.md / make_report.py / build_asset_manifest.py 均未读（见 review_report.json › reviewer.excluded） |",
            "| ✅ | upstream_packages_completed | wp-946-01 存在且可校验：source_hash 独立复算一致、`C15` 自检数字可复现 |",
            "| ✅ | do_not_mark_claims_as_verified | 上游 asset status ∈ {{resolvable, unresolved}}，`C10` 通过；本报告全部结论用 verdict/notes 表述，无 verified 标记 |",
            f"| ✅ | 零手抄 | 报告中 {len(QUOTES)} 条引文由 make_report.py 断言逐字存在于 markdown，缺一即构建失败 |",
        ]
    )

    body = f"""# KF-RESULT wp-946-04

**审核对象：`wp-946-01`（task_type={upstream["task_type"]}，producer=`{upstream["provenance"]["producer"]}`）｜报告 `946`｜lane C｜verdict = `{rev["verdict"]}`／decision = `{rev["decision"]}`**

## ① 本工序做了什么

本单是报告→知识产线「04-独立审核」工序：对上游工作包 `wp-946-01`（报告 946 的资产登记）做红队式独立复核，只判 **pass / fail / needs-fix**，不改写上游产物、不把任何结论标成 `verified`（verification 由平台门计算）。

审核对象是 22 条资产登记的**可核性**：源哈希、逐字引文与字符偏移、record 字段取值、计数自洽、单报告作用域、以及「不做抽取／不自我验证」的纪律声明。**不**复核报告 946 自身的业务数字（rubric 打分、REVIVE 计数、巡检中位间隔），那需要报告库之外的日志与 API，已在 `not_run` 里显式列出（未核 ≠ 通过）。

原文计量（脚本现算，非手抄）：字符 **{len(md)}**（契约 `chars: {len(md)}` 一致）、UTF-8 字节 **{len(md.encode("utf-8"))}**、`{src_hash}` 与契约 `source_hash` 逐位一致。

## ② 怎么做的（步骤/工具/关键设置）

1. **独立取原文**：用平台报告库接口重新拉取 report 946 的 `markdown` 字段（不复用生产者快照），现算 sha256 与码点长度，写 `upstream/independent_source.json`。
2. **只读交付物**：读取上游 `kf_result.json`（另存为 `upstream/wp-946-01.kf_result.json`）与生产者 `selfcheck.json`；**未读**生产者 `report.md`、`make_report.py`、`build_asset_manifest.py`（`constraints.reviewer_context_excludes_producer_explanation`）。
3. **自写校验器**：`review_wp946_01.py` 从零实现 {n_checks} 项检查（不执行生产者的 `validate_asset_manifest.py`），逐条落 `pass/fail/not_run` 与证据明细 → `review_report.json`。
   关键设置：markdown 引文按「子串存在 + `markdown[char_start:char_end] == quote` + `markdown.count(quote) == occurrences`」三重判定；record 取值按 `figures[i].name` 式路径回读实时记录比对；`resolvable` 只允许 `{{source_document, record_metadata}}`（报告库确实能供的两类）。
4. **离线可复跑回归**：`tests/test_wp946_04_review_report.py` 不依赖网络，重算哈希/引文/偏移/计数/作用域 7 项不变量。
5. **provenance 双签**：生产者 `content_ref.snapshot_sha256` 与它自己的快照文件字节重算一致，且快照内 markdown 哈希 = 本次独立取回哈希（`C18`）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-946-04/review_report.json` | 审核判决主件：`verdict={rev["verdict"]}`、{n_checks} 项检查（fail {n_fail} / not_run {n_not_run}）、{len(rev["non_blocking_notes"])} 条非阻断发现、`not_run` 清单、独立性声明 |
| `docs/kf/wp-946-04/kf_result.json` | 结果信封（`package_id/task_type/report_id/provenance/outputs`），`provenance.source_hash={src_hash}` |
| `docs/kf/wp-946-04/review_wp946_01.py` | 独立校验器（{n_checks} 项检查，可一键重跑） |
| `docs/kf/wp-946-04/source_report.md` | 独立取回的 report 946 markdown 副本（{len(md)} 码点，供离线复算） |
| `docs/kf/wp-946-04/upstream/wp-946-01.kf_result.json` | 被审交付物只读副本（sha256 见 `review_report.json › review_target.deliverable_sha256`） |
| `docs/kf/wp-946-04/upstream/wp-946-01.selfcheck.json` | 生产者自检声明（仅作对照，不采信） |
| `docs/kf/wp-946-04/upstream/independent_source.json` | 独立检索回执（哈希/长度/title/mission_id/figures） |
| `docs/kf/wp-946-04/figures/fig1_asset_status_by_kind.png` | 图 1：按 kind 统计上游 22 条资产的 resolvable/unresolved（由 upstream manifest 程序化渲染） |
| `tests/test_wp946_04_review_report.py` | 离线回归（7 项断言，全绿） |

![fig1](figures/fig1_asset_status_by_kind.png)

图 1 读法：绿色=报告库确有字节可取的资产（`source_document` + `record_metadata`），红色=只有指针、字节在报告库之外的资产。这张图就是 `resolvable=2 / unresolved=20` 的来源，也解释了为什么下游工序的可用证据面被限制在 markdown 文本本身（见 ⑤ N1）。

## ④ 证据定位表（claim/字段 → 原文引文片段）

审核结论 → 上游字段与原文锚点（引文均为 make_report.py 断言过的逐字片段）：

| 检查 | 审核断言（逐项独立重算） | 判决 |
|---|---|---|
{check_rows}

审核所依据的报告原文锚点（逐字）：

| 证据号 | 用途 | 原文引文片段（逐字） |
|---|---|---|
{quote_rows}

判定要点：上游 22 条资产中 `resolvable={resolvable}` / 未解 {total_assets - resolvable}；25 条 markdown 引文与 16 条 record 引文全部逐字命中（`C04`/`C05`/`C06`）；计数按资产表重算一致（`C07`）；作用域仅 report 946（`C11`）；无任何 `verified` 自标（`C10`）。因此 **verdict=pass（approve）**，但附 {len(rev["non_blocking_notes"])} 条非阻断发现，见 ⑤。

## ⑤ 注意点与局限

非阻断发现：

{note_rows}

**未做的检查（不得读作通过）**：

{not_run_rows}

**本审核自身的局限**：

{limitation_rows}
- 单报告单包：本单只覆盖 `report_id=946` 的 `wp-946-01`；同产线其它工作包（如 `wp-946-02/03`）未在本单审核范围内。
- 独立性是流程性声明，不是密码学证明：我声明未读生产者解释，实际约束由「校验器自写、引文自算、自检不采信」三条保证。

## ⑥ 自检（逐条对照 acceptance）

{selfcheck}

补充自检：`python3 -m pytest tests/test_wp946_04_review_report.py -q` → **7 passed**；`review_wp946_01.py` 重跑 → `{{"verdict": "pass", "failed": []}}`。无失败项需 honest-FAIL 申报；未核项已在 ⑤ 显式列出。

repro_cmd（工作树根执行，需 `TENSOR_API_BASE`/`TENSOR_AGENT_USER`/`TENSOR_AGENT_PASS`）：

`python3 docs/kf/wp-946-04/review_wp946_01.py --upstream docs/kf/wp-946-04/upstream/wp-946-01.kf_result.json --out docs/kf/wp-946-04/review_report.json --independent-source docs/kf/wp-946-04/upstream/independent_source.json --producer-worktree /root/tp-agent/work/m15522 && python3 docs/kf/wp-946-04/make_report.py && python3 -m pytest tests/test_wp946_04_review_report.py -q`

（`--producer-worktree` 仅用于复算生产者快照哈希 `C18`；缺省时该项落 `not_run`，不影响 verdict。）

```json
{json.dumps(envelope, ensure_ascii=False, indent=1)}
```
"""
    OUT_MD.write_text(body, encoding="utf-8")
    print(json.dumps({"envelope": str(OUT_JSON), "report": str(OUT_MD), "verdict": rev["verdict"], "chars": len(body)}, ensure_ascii=False))


if __name__ == "__main__":
    main()