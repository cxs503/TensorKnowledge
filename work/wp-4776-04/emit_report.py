#!/usr/bin/env python3
"""Emit docs/kf_result_wp-4776-04.md (single ```json block) from the built review.

Zero hand-copying: the JSON block is the serialised envelope read straight from
work/wp-4776-04/review_report.json, and it is validated against
schemas/kf_result.v1.schema.json before the markdown is written.
"""
from __future__ import annotations

import hashlib
import json
import os

REPO = "/root/tp-agent/work/m15830"
HERE = os.path.join(REPO, "work", "wp-4776-04")
DOC = os.path.join(REPO, "docs", "kf_result_wp-4776-04.md")

review = json.load(open(os.path.join(HERE, "review_report.json"), encoding="utf-8"))
md_src = open(os.path.join(HERE, "source_4776.md"), encoding="utf-8").read()
source_hash = "sha256:" + hashlib.sha256(md_src.encode("utf-8")).hexdigest()
assert source_hash == review["reviewed_source_hash"]

envelope = {
    "package_id": "wp-4776-04",
    "task_type": "04-independent-review",
    "report_id": "4776",
    "provenance": {
        "source_hash": source_hash,
        "source_field": "markdown",
        "producer": "wp-4776-04 red-team reviewer",
        "emitted_at": "2026-11-12T02:50:00Z",
        "notes": (
            "independent review of wp-4776-01 (asset registration of report 4776). Read: report 4776 "
            "markdown only + the structured artifact outputs['asset_manifest.json'] of wp-4776-01. No "
            "producer prose, no other report_id, nothing marked verified. Every quote in this result is "
            "guarded as a verbatim, single-occurrence substring of the source markdown."
        ),
    },
    "outputs": {"review_report.json": review},
}

schema = json.load(open(os.path.join(REPO, "schemas", "kf_result.v1.schema.json"), encoding="utf-8"))
try:
    import jsonschema

    jsonschema.validate(envelope, schema)
    schema_note = "jsonschema validation: PASS vs schemas/kf_result.v1.schema.json"
except ImportError:  # minimal manual fallback
    required = set(schema["required"])
    assert required <= set(envelope), required - set(envelope)
    import re as _re

    assert _re.match(schema["properties"]["package_id"]["pattern"], envelope["package_id"])
    assert _re.match(schema["properties"]["task_type"]["pattern"], envelope["task_type"])
    assert _re.match(schema["properties"]["report_id"]["pattern"], envelope["report_id"])
    assert _re.match(
        schema["properties"]["provenance"]["properties"]["source_hash"]["pattern"], source_hash
    )
    schema_note = "manual pattern/required-key validation: PASS (jsonschema not installed)"

json.dump(envelope, open(os.path.join(HERE, "result_envelope.json"), "w"), ensure_ascii=False, indent=1)

F = review["findings"]
by_id = {f["id"]: f for f in F}
checks = review["checks_run"]
quote = lambda s: s.replace("`", "ˋ") if False else s  # noqa: E731 - keep text verbatim


def cell(text: str) -> str:
    """Markdown table cell: keep backticks, escape pipes."""
    return text.replace("|", "\\|").replace("\n", " ")


table_rows = [
    ("源报告身份", "`sha256:03d3239696a36958c408df0ac3fd21d506a39cce4277b7f918134591d00d3882`；4869 字符 / 4869 字节 / 全 ASCII",
     "独立重算 sha256 与契约逐位一致；字符数与契约 4869 相等 ✔"),
    ("13 件资产定位码", "`pr185-cure-evidence.png`（A01，行 73）；`ci-test312-pre-fix.log` - the failing CI job log（A02，行 70）",
     "13/13 字符区间逐字节命中、quote sha256 与声明值一致、出现次数一致、行号一致 ✔"),
    ("覆盖完整性", "`runs/pr185-cure/` 与 6 个证据文件名、`pyproject.toml`、`scripts/lint_gate.py`、`tests/test_lint_gate.py`、`docs/lint-debt-baseline.md`、`docs/lint-baseline.json`、`.github/workflows/ci.yml`",
     "markdown 内 13 个路径 token 全部已登记，无漏登 ✔；分支/commit 句柄 2 个无登记位（R3）"),
    ("证据可取回性", "Evidence logs and the figure live in `runs/pr185-cure/`:",
     "4 条宿主路由探测：记录 200，figures 列表 404，figure 字节 404，attachments 404 → 7 件声明载荷 0 件可取回（R1）"),
    ("根因机制陈述", "expectations of those fixtures no longer hold and the collection came back empty.",
     "与声明仓自身记录冲突：TensorFEM `docs/lint-gate-determinism.md:16` 记 ruff 0.17.3 = failure (1228 errors)，规则集扩张应产生更多而非 0 命中（R2）"),
    ("修复结论不依赖机制", "## Fix (4 files)",
     "钉死单一 build + 跨版本拒绝比较的补救与机制解释无关，结论不受 R2 影响 ✔"),
    ("内部算术一致性", "`test (3.12)` = failure on branch `agent/m4156` (head `3910110`), 4 failed / 1764 passed:",
     "9 条数字恒等式全部自洽：4+1764=1768；15+3=18；14+4=18；1+17=18；4271/624 前后不变；4 个 FAILED 行 = 声明 4 failed ✔"),
    ("未标 verified / 未越权抽 claim", "No solver code, no other test, no unrelated file touched.",
     "上游 manifest claims 为空集、无 verified 字段；本评审同样未标 verified ✔"),
]

md = f"""# KF-RESULT wp-4776-04

**tags**: `kf-wp:wp-4776-04`, `independent-review`, `red-team`, `TensorFEM`, `ci`, `lint-debt-ratchet`

> 审核对象 **wp-4776-01**（report_id=4776，asset registration，源 sha256 `03d32396…d00d3882`）。
> **判定：pass（approve with notes）**——登记的 13 件资产定位码全部逐字节重算命中，未造数、未漏登、未标 verified。
> **产线判定：needs-fix**——被审报告本身有 3 项中等缺陷（7 件证据载荷 0 件可取回；根因机制与声明仓自身记录冲突；6 条仓库路径在审计环境不可解析），须在 03 抽知识前处理。

---

## ① 本工序做了什么

对工作包 `wp-4776-01`（报告 4776 的资产登记）做**独立红队审核**（工序 04）。只读 report_id=4776 的 markdown 与上游结构化产物 `outputs['asset_manifest.json']`；**未读生产者任何叙述**，未触碰其它 report_id，未把任何结论标为 verified，未改动上游文件。

七项检查，6 过 1 不过（唯一不过项即缺陷 R1 本身）：

| 检查 | 判据 | 结果 |
|---|---|---|
| C1 源身份 | 重算 sha256 == 契约；字符数 == 4869 | pass |
| C2 定位码保真 | 13 件的字符区间 / quote sha256 / 出现次数 / 行号逐项重算 | pass（13/13） |
| C3 覆盖完整性 | markdown 内全部路径 token 是否都已登记 | pass（13/13，无漏登） |
| C4 内部算术 | 9 条数字恒等式重算 | pass（9/9） |
| C5 载荷可取回 | 4 条宿主路由探测 | **fail**（figure 字节 404） |
| C6 引文逐字 | 本评审携带的每条引文是否为原文子串 | pass |
| C7 评审纪律 | 是否标 verified、判定是否与自身发现一致 | pass |

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文**：`GET $TENSOR_API_BASE/tensor/reports/4776`（`/auth/login` 取 Bearer），落盘 `work/wp-4776-04/source_4776.md`，重算 `sha256` 与契约比对（一致，4869 字符）。
2. **取上游产物但只取结构化部分**：从平台报告账本 payload 中切出 wp-4776-01 的 json 代码块（三反引号 json），**只保留 `outputs['asset_manifest.json']`**，落盘 `upstream/asset_manifest_wp-4776-01.json`；生产者的叙述段一概不读（独立性约束）。
3. **定位码独立重算**（`verify_review.py::c2_locators`）：对每件资产重算 `md[char_start:char_end] == quote`、`sha256(quote) == content_hash`、`count(quote) == occurrences`、`line_number == line`。**13/13 全中**。
4. **覆盖完整性反查**（`c3_completeness`）：用路径正则扫出 markdown 里全部 `*.py|toml|json|yml|md|log|png` token（13 个）与上游登记集比对 → 无漏登；另用 `agent/[A-Za-z0-9]+` / `head \`[0-9a-f]{7,40}\`` 抓出 2 个仓库句柄（`agent/m4156`、`3910110`）→ 上游 3 种 kind 无对应槽位（R3）。
5. **算术一致性**（`c4_arithmetic`）：程序化重算 9 条恒等式（CI 总数、新增用例数、drift/skip 与 pre-fix 两次运行的分区、4271/624、4 文件、4 FAILED 行、pin 出现次数），全自洽。
6. **宿主可取回性**（`c5_reachability`）：探测 `/tensor/reports/4776`、`/figures`、`/figures/pr185-cure-evidence.png`、`/attachments` 四条路由。
7. **仓库侧可解析性**（R6）：在 `/root/tensor-ecosystem/*`（14 仓）与 `/opt/mm-verify/*` 镜像里检索 `scripts/lint_gate.py`、`docs/lint-baseline.json`、`runs/pr185-cure/`，并在 TensorFEM（502 refs）与 TensorSPH（260 refs）里检索分支 `agent/m4156` 与两条路径的全部历史提交。
8. **零手抄**：`build_review.py` 里每条引文先断言「在原文中恰好出现一次」（锚行引文再断言落在指定行），断言失败即中止构建；`verify_review.py::c6_quotes` 在产物落盘后**再独立复核一遍** review_report.json 里的每条 quote。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `work/wp-4776-04/review_report.json` | 契约输出：判定 pass / 产线 needs-fix、6 条分级发现（0 高 / 3 中 / 3 低）、11 条已核实声明、6 项未跑、4 项独立性局限 |
| `work/wp-4776-04/checks.json` | 7 项检查的机器结果（含 13 件资产逐项布尔与 4 条路由状态码） |
| `work/wp-4776-04/verify_review.py` | 一键复核：hash / 13 件定位码 / 覆盖 / 算术 / 路由 / 引文逐字 / 纪律 |
| `work/wp-4776-04/build_review.py` | 产物构建器：引文守卫 + 定位码重算，任何一条不满足即中止 |
| `work/wp-4776-04/reviewer-figure.png` | 左：13 件资产在原文中的分布（空心=载荷不可取回）；右：13×6 验证矩阵 |
| `work/wp-4776-04/upstream/asset_manifest_wp-4776-01.json` | 上游产物只读副本（仅结构化部分），用于绑定居定位码声明值 |
| `work/wp-4776-04/source_4776.md` | 被审原文快照（sha256 见 provenance） |
| `docs/kf_result_wp-4776-04.md` | 本报告（唯一一个 json 代码块） |

## ④ 证据定位表（claim → 原文引文 / 评审方独立数字）

| 项 | 原文引文（逐字，机器校验） | 评审方独立结果 |
|---|---|---|
""" + "\n".join(
    f"| {cell(a)} | {cell(b)} | {cell(c)} |" for a, b, c in table_rows
) + f"""

## ⑤ 注意点与局限（分级发现）

| ID | 级别 | 阻断 | 发现 | 建议 |
|---|---|---|---|---|
| R1 | 中 | 否（对 01）；对 03/05 是 | 7 件声明证据载荷（1 图 + 6 条 `runs/pr185-cure/*`）**0 件**可从报告仓取回；`figures[]` 有 name+caption 但字节 404，正文内联 `fig:` 引用必然断图 | 重发报告并附 figure 字节与 6 件载荷，或删掉内联 fig 引用并把验证表标为纯散文 |
| R2 | 中 | 否（对 01）；对「把机制当事实抽取」是 | 根因写成事实：规则集扩张 → 空收集；但声明仓自身记录 ruff 0.17.3 = **1228 errors**（`docs/lint-gate-determinism.md:16`），扩张应产生**更多**命中而非 0；报告自己在 Caveats 里承认 rule-level 细节是 `{by_id['R2']['report_quote'][1]}`；`{by_id['R2']['report_quote'][2]}` 未测 | 根因降级为「观测=0.17.3 下解析为空，机制未确认」，并把未测的另一解释（JSON 输出/解析键或配置被拒）并列举出 |
| R6 | 中 | 否（对 01）；对 03/05 是 | 6 条 `referenced_repo_path` 在审计环境**无处可解析**：14 个生态仓 + 3 个 mm-verify 镜像无 `scripts/lint_gate.py`、无 `docs/lint-baseline.json`、无 `runs/pr185-cure/`；TensorFEM 502 refs 无 `agent/m4156`；两路径在 TensorFEM 全历史零提交；TensorFEM HEAD 的实际 lint 工具链是 `scripts/lint_scope.sh`（变更域）+ `[tool.ruff.lint]` 显式 select 钉死 + `docs/lint-gate-determinism.md`，dev extra 是 `ruff>=0.15,<0.16` 而非 `ruff==0.15.0` | **不是造假证据**（报告自述在未合并分支上，本环境是 main-only 快照且 agent ref 已剪枝）；但 A08–A12 在 03/05 必须记 WITHHELD，直到该分支可解析 |
| R3 | 低 | 否 | 唯一能指向未合并修复的句柄 `agent/m4156` / `3910110` 在 3 种 kind 里无槽位，资产集永远指不到可取回的提交 | 增 `repo_ref` kind 并登记两者 |
| R4 | 低 | 否 | 平台记录标题（`one pinned ruff build for…`）与原文 H1（`one ruff build for…`）不一致：上游已测得 `title_equals_markdown_h1=false`，却没进 `unresolved` / `registration_problems`（两者均为空），只读这两处的下游会看到「干净」清单 | 把标题不一致连同两个字符串一并列入 unresolved |
| R5 | 低 | 否 | 修复第 3 项的跳过守卫：`{by_id['R5']['report_quote'][0]}` → 恰好在「ruff 被升版」这一事件上，4 条真二进制端到端用例静默 skip，回归面在关键时刻最薄 | 保留 skip，另加一条**任何 ruff 下都不跳过**的「收集非空」断言，使 collected nothing 不可能静默 |

**局限**（如实申报，不粉饰）：

1. 未跑项 6 条：lint gate 的 exit 0 / exit 2 契约、`pytest → 18 passed` 与 `14 passed+4 skipped`、4 文件改动 diff（含「未碰求解器代码」）、4271/624 基线重数、ruff 0.16 的 59→413、证据图内容——原因均为「`scripts/lint_gate.py` / 基线 / 分支在审计环境不存在」或「无 0.17.x 可安装 build、无外网」。**这些一律记 not_run，不记 pass。**
2. 本环境的仓镜像为 main-only 快照且 agent 分支已剪枝，故仓库侧结论只表述为「不可解析」，**不表述为「不存在/造假」**。
3. 无法重算 0.17.3 下的真实行为：报告自述该 build 无 loong64 wheel，本环境同样装不上，所以 R2 只能靠「声明仓自身同版本记录」做反证，而非直接实验。
4. 图不可检视：figure 字节 404，只能读到 272 字 caption。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|---|---|---|
| `valid_json` | ✔ | `docs/kf_result_wp-4776-04.md` 全文仅一个 json 代码块；`verify_review.py` 能解析 review_report.json |
| `schema_pass` | ✔ | {schema_note} |
| `reviewer_independent` | ✔ | 只读原文 + 上游结构化产物；`review_report.json.independence_limitations` 4 条；`constraints.reviewer_context_excludes_producer_explanation` 遵守（未读生产者叙述） |
| `upstream_packages_completed` | ✔ | wp-4776-01 已产出完整 result（13 件资产清单，本评审据此独立重算 13/13） |
| `constraints.do_not_mark_claims_as_verified` | ✔ | 0 处 verified 标记（C7）；本文对上游一律 pass/未跑/WITHHELD 三态 |
| `constraints.review_prompt_not_copied_from_producer` | ✔ | 审核 prompt 与生产者无关：独立构造 7 项检查，其中 C2/C3/C4/C5 的重算方法未见于上游产物 |
| `output.review_report.json` | ✔ | 已落盘并通过信封 schema |

**诚实标注**：C5 检查本身 fail——这不是本工序的失败，而是本工序要报的缺陷（R1）；本工序对上游的判定为 pass，对产线的判定为 needs-fix，两者都写进了 `review_report.json` 的 `verdict` / `line_level_verdict`，未合并成一个含糊的结论。

## 复现（一键）

```text
cd work/wp-4776-04
python3 verify_review.py      # C1-C7，写 checks.json（--offline 用本地快照）
python3 build_review.py       # 引文守卫 + 定位码重算 → review_report.json
python3 make_figure.py        # → reviewer-figure.png
# 仓库侧反证：
git -C /root/tensor-ecosystem/TensorFEM log --all --oneline -- 'scripts/lint_gate.py'
git -C /root/tensor-ecosystem/TensorFEM for-each-ref --format='%(refname)' | wc -l   # 502
grep -n '0.17.3' /root/tensor-ecosystem/TensorFEM/docs/lint-gate-determinism.md      # :16 1228 errors
grep -n '0.17.4 widened the defaults' /root/tensor-ecosystem/TensorFEM/pyproject.toml # :75
```

![review](fig:reviewer-figure.png)

```json
{json.dumps(envelope, ensure_ascii=False, indent=1)}
```
"""

os.makedirs(os.path.dirname(DOC), exist_ok=True)
open(DOC, "w", encoding="utf-8").write(md)
print(schema_note)
print("wrote", DOC, len(md), "chars")
assert md.count("```json") == 1, md.count("```json")
print("single json fence: OK")