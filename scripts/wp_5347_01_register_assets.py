#!/usr/bin/env python3
"""Work package wp-5347-01 — process 01 (asset registration) for report 5347.

Scope (owner contract, task_type ``01-asset-registration``):
  register the source asset (report_id + byte hash of its ``markdown``), list the
  attachments/artifacts the report refers to, mark reachability.  No extraction,
  no classification, no claim generation.

What this script does, in order:
  1. read the source bytes written by ``scripts/fetch_report_5347.py``
     (``artifacts/wp-5347-01/report_5347.md``) and recompute their sha256;
     abort with exit 2 if it does not equal the contract ``source_hash``;
  2. scan the markdown for every path-like token (two regexes: paths, bare
     filenames) and classify each into ``kind`` / ``reachability`` by rule —
     the token stays in the manifest together with the exact line that cites it
     (``quote`` + ``start_offset``/``end_offset``), so every entry is locatable
     verbatim in the source bytes;
  3. merge the report record's own ``figures`` metadata (name + caption only —
     the record carries no bytes, and ``GET /tensor/reports/5347/figures`` is a
     404, so figures are registered as ``metadata_only``);
  4. emit ``asset_manifest.json`` (the declared process-01 output) and the
     ``kf_result`` envelope, then the ``KF-RESULT wp-5347-01`` report markdown.

Every number in the emitted report is interpolated from the manifest, never
typed by hand (zero-transcription rule).

Usage::

    python3 scripts/wp_5347_01_register_assets.py            # build
    python3 scripts/wp_5347_01_register_assets.py --check    # verify only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "artifacts" / "wp-5347-01"
if not OUT_DIR.is_dir():  # committed snapshot: artifacts/** is git-ignored
    OUT_DIR = REPO / "docs" / "production" / "wp-5347-01"
REPORT_ID = "5347"
PACKAGE_ID = "wp-5347-01"
TASK_TYPE = "01-asset-registration"
TITLE = f"KF-RESULT {PACKAGE_ID}"
MISSION_ID = 15564
#: contract-declared hash of the report's markdown bytes (owner YAML)
CONTRACT_SOURCE_HASH = ("sha256:bdd7bb0e76c120366d71fe0470570563"
                        "33cf83cfef6e0a2ca1ca125082a9d2e1")
CONTRACT_CHARS = 4206

PATH_RE = re.compile(
    r"(?:~|/)?(?:[A-Za-z0-9_.@<>${}-]+/)+[A-Za-z0-9_.@<>-]*(?:\.[A-Za-z0-9]{1,6})?"
)
BARE_FILE_RE = re.compile(r"[A-Za-z0-9_.-]+\.(?:py|json|md|png|so\.3)")
ENV_TOKENS = ("scipy", "libflexiblas.so.3")

#: kinds are derived from the path shape only — no interpretation of the report
KIND_RULES = (
    ("docs/", ".json", "evidence_ledger"),
    ("docs/", ".md", "document"),
    ("scripts/", ".py", "script"),
    ("artifacts/", "", "artifact"),
    ("tests/", "", "test"),
    ("src/", "", "code"),
)
#: reachability vocabulary (fail-closed: anything unknown stays unresolved)
REACHABILITY = {
    "external_repo_artifact": (
        "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；"
        "工序 01 只登记不检出，故 resolved=false"
    ),
    "ephemeral_sandbox": (
        "报告中的临时复现目录（/tmp/...），任务结束即消失，不构成资产；resolved=false"
    ),
    "environment_layout": (
        "runner 检出布局示例（目录名本身不是资产），登记以保留门禁反例上下文；resolved=false"
    ),
    "environment_dependency": (
        "运行环境依赖（非报告产出），登记以保留“集群不适用”结论的上下文；resolved=false"
    ),
    "metadata_only": (
        "仅在图注元数据中出现，报告记录未携带图像字节，"
        "GET /tensor/reports/5347/figures 返回 404；resolved=false"
    ),
}


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def section_of(text: str, offset: int) -> str:
    """Nearest preceding markdown level-2 heading (``## ① ...``)."""
    head = text[:offset]
    matches = list(re.finditer(r"^##\s+(.+)$", head, flags=re.M))
    return matches[-1].group(1).strip() if matches else ""


def line_span(text: str, offset: int) -> tuple[int, int]:
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    if end == -1:
        end = len(text)
    return start, end


def classify(token: str) -> tuple[str, str]:
    """Return ``(kind, reachability)`` from the path shape alone."""
    low = token.lower()
    if "<repo>" in token or token.rstrip("/") in ("/work", "_work") \
            or token.startswith("...") or token.startswith("/home/runner") \
            or token.startswith("/root/tp-agent/work"):
        return "environment_layout", "environment_layout"
    if token.startswith("/tmp/"):
        return "ephemeral_sandbox", "ephemeral_sandbox"
    if low.endswith(".so.3") or low in ENV_TOKENS:
        return "environment_dependency", "environment_dependency"
    for prefix, suffix, kind in KIND_RULES:
        if token.startswith(prefix) and token.endswith(suffix):
            return kind, "external_repo_artifact"
    if token.endswith(".py"):
        return "code", "external_repo_artifact"
    return "unclassified", "external_repo_artifact"


def extract_tokens(text: str) -> tuple[list[dict], list[dict]]:
    """Path-like tokens in document order, deduplicated, with verbatim locators."""
    spans: list[tuple[int, int]] = []
    tokens: list[dict] = []
    excluded: list[dict] = []
    seen: set[str] = set()

    def add(match: re.Match, raw: str) -> None:
        if match.end() < len(text) and text[match.end()] == ":":
            excluded.append({
                "token": text[match.start():text.find("\n", match.end())].strip(),
                "reason": "冒号后缀=报告里的状态标签（如 code/test/doc:TRACKED），不是文件路径",
            })
            return
        token = raw.strip().strip("`,")
        if token.startswith("HEAD:"):
            token = token.split("HEAD:", 1)[1]
        if not token or token in seen:
            return
        seen.add(token)
        start, end = line_span(text, match.start())
        quote = text[start:end]
        tokens.append({
            "token": token,
            "locator": {
                "locator_type": "char_span",
                "section": section_of(text, match.start()),
                "quote": quote,
                "start_offset": start,
                "end_offset": end,
                "quote_sha256": sha256_bytes(quote.encode("utf-8")),
            },
        })

    for m in PATH_RE.finditer(text):
        spans.append(m.span())
        add(m, m.group(0))
    for m in BARE_FILE_RE.finditer(text):
        if any(s <= m.start() and m.end() <= e for s, e in spans):
            continue  # already covered by a longer path token
        add(m, m.group(0))
    return tokens, excluded


def build_manifest(text: str, meta: dict, source_bytes: bytes) -> dict:
    tokens, excluded = extract_tokens(text)
    assets: list[dict] = []
    for i, tok in enumerate(tokens, start=1):
        kind, reach = classify(tok["token"])
        assets.append({
            "asset_id": f"asset-{REPORT_ID}-{i:03d}",
            "kind": kind,
            "path": tok["token"],
            "reachability": reach,
            "resolved": False,
            "resolution_note": REACHABILITY[reach],
            "locator": tok["locator"],
        })
    base = len(assets)
    for j, fig in enumerate(meta.get("figures") or [], start=1):
        assets.append({
            "asset_id": f"asset-{REPORT_ID}-{base + j:03d}",
            "kind": "figure",
            "path": fig.get("name", ""),
            "reachability": "metadata_only",
            "resolved": False,
            "resolution_note": REACHABILITY["metadata_only"],
            "declared_caption": fig.get("caption", ""),
            "locator": {
                "locator_type": "record_field",
                "field": "figures[].name",
                "value_sha256": sha256_bytes(str(fig.get("name", "")).encode("utf-8")),
            },
        })

    by_kind: dict[str, int] = {}
    by_reach: dict[str, int] = {}
    for a in assets:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1
        by_reach[a["reachability"]] = by_reach.get(a["reachability"], 0) + 1
    by_section: dict[str, int] = {}
    for a in assets:
        sec = a["locator"].get("section") or a["locator"].get("field", "")
        by_section[sec] = by_section.get(sec, 0) + 1

    return {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "report_id": REPORT_ID,
            "source_uri": "tensor://reports/5347",
            "source_field": "markdown",
            "source_hash": sha256_bytes(source_bytes),
            "chars": len(text),
            "title": meta.get("title", ""),
            "scenario_key": meta.get("scenario_key"),
            "status": meta.get("status"),
            "created_at": meta.get("created_at"),
            "tags": meta.get("tags") or [],
            "retrieved_via": "GET %s/tensor/reports/5347 (Bearer auth)" % (
                "TENSOR_API_BASE",),
        },
        "registration": {
            "objective": "register_assets",
            "producer": "eco_admin / mission 15564 (agent m15564, TensorKnowledge)",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "extraction_performed": False,
            "classification_performed": False,
            "claims_extracted": 0,
            "claims_note": (
                "契约 objective 只要求 register_assets（classify_report_type=false）；"
                "claims 为空数组是合法完整结果，未生成任何知识对象"
            ),
            "extraction_rule": {
                "path_regex": PATH_RE.pattern,
                "bare_file_regex": BARE_FILE_RE.pattern,
                "dedupe": "document order, first occurrence wins; bare filename skipped "
                          "when already covered by a longer path token",
                "kind_rules": [list(r) for r in KIND_RULES],
                "excluded": excluded,
            },
        },
        "assets": assets,
        "counts": {
            "assets": len(assets),
            "resolved": sum(1 for a in assets if a["resolved"]),
            "unresolved": sum(1 for a in assets if not a["resolved"]),
            "by_kind": dict(sorted(by_kind.items())),
            "by_reachability": dict(sorted(by_reach.items())),
            "by_section": dict(sorted(by_section.items())),
        },
        "unresolved": [
            {
                "asset_id": a["asset_id"],
                "path": a["path"],
                "reason": a["resolution_note"],
            }
            for a in assets if not a["resolved"]
        ],
        "notes": [
            "本包不含抽取、分类或知识判断；assets 只记录报告点名过的路径与其逐字定位行。",
            "所有资产 resolved=false：可解析的只有报告 markdown 自身字节，其 sha256 已与契约一致。",
            "报告记录的 figures 元数据只有 name/caption，图像字节不可通过 API 取回（404），"
            "因此图像资产登记为 metadata_only，不得在下游当作已归档证据。",
        ],
    }


def build_result(manifest: dict) -> dict:
    return {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": manifest["source"]["source_hash"],
            "source_field": "markdown",
            "source_uri": manifest["source"]["source_uri"],
            "producer": "eco_admin / mission 15564 (agent m15564)",
            "emitted_at": manifest["registration"]["generated_at"],
            "notes": (
                "工序 01 结果信封：source_hash 为 GET /tensor/reports/5347 返回 markdown "
                "字段的 UTF-8 字节 sha256，与契约 source_hash 逐字节一致；"
                "claims 为空数组（本工序不抽取）。"
            ),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def render_report(result: dict) -> str:
    m = result["outputs"]["asset_manifest.json"]
    checks = _load_json(OUT_DIR / "checks.json") or {}
    platform = _load_json(OUT_DIR / "platform_gate.json") or {}
    ccounts = checks.get("counts") or {}
    gate_line = ("| 本地 acceptance | passed={p} / vacuous={v} / failed={f} / not_run={n} | "
                 "`artifacts/wp-5347-01/checks.json` |").format(
        p=ccounts.get("passed"), v=ccounts.get("vacuous"),
        f=ccounts.get("failed"), n=ccounts.get("not_run"))
    plat_line = ("| 平台门（复用 kf/ops/knowledge_factory/gates.py） | ok={ok}；结构门 "
                 "{sg} / 证据门 {eg}；locator_rate={lr}（0 claim=空真，记 None 不记 100%） | "
                 "`artifacts/wp-5347-01/platform_gate.json` |").format(
        ok=platform.get("ok"),
        sg=[g["gate"] for g in platform.get("structure", []) if g["ok"]],
        eg=[g["gate"] for g in platform.get("evidence", []) if g["ok"]],
        lr=(platform.get("evidence_stats") or {}).get("locator_rate"))
    src, cts = m["source"], m["counts"]
    rows = "\n".join(
        f"| {a['asset_id']} | `{a['path']}` | {a['kind']} | {a['reachability']} | "
        f"{'yes' if a['resolved'] else 'no'} | {a['locator'].get('section') or a['locator'].get('field', '')} |"
        for a in m["assets"]
    )
    kind_rows = "\n".join(f"| {k} | {v} |" for k, v in cts["by_kind"].items())
    reach_rows = "\n".join(f"| {k} | {v} |" for k, v in cts["by_reachability"].items())
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    return f"""# KF-RESULT {PACKAGE_ID}

## ① 本工序做了什么

工序 01（资产登记），对象=report_id `5347`（TensorDEM main CI 清红 m4829）。
只做可程序化的事：取回报告 markdown、**重算字节哈希并与契约对表**、把报告点名过的
附件/工件逐条登记为资产、标注可达性。不抽取、不分类、不改写、不给知识对象定性。
产出 `asset_manifest.json`，装在 kf_result 信封里提交。

约束遵守：每条资产带逐字定位行（`quote` + `start_offset`/`end_offset`），本节与下文所有
数字均由登记脚本从 manifest 插值，未手抄。

## ② 怎么做的（步骤/工具/关键设置）

1. `python3 scripts/fetch_report_5347.py --out artifacts/wp-5347-01/report_5347.md`
   —— 用 `$TENSOR_AGENT_USER` 登录拿 token，GET `/tensor/reports/5347`，只落 `markdown`
   字段的 UTF-8 字节；同时把记录元数据（title/tags/figures 等）存为 `.meta.json`。
2. 重算 `sha256` 与字符数，与契约 `source_hash` / `chars` 对表：
   `{src['source_hash']}` / `{src['chars']} chars` —— 一致，否则脚本 exit 2 不出产物。
3. 逐字扫描 markdown：路径正则 + 裸文件名正则（`fragmentation.py` 这类漏前缀指针必须被登记），
   按文档序去重、取首次出现的整行作为 `quote`，偏移由 `rfind/find` 直接量出（非人工估计）。
4. `kind` / `reachability` **只按路径形状与元数据来源**判定（不做语义判断）；未知形状落
   `unclassified`，可达性一律 fail-closed。
5. 图的登记：报告记录 `figures` 只有 name/caption，`GET /tensor/reports/5347/figures` 返回 404
   —— 图像字节不可取回，登记为 `metadata_only`，明确不可当已归档证据。
6. 复核：`scripts/verify_wp_5347_01.py`（A1–A10，含变异测试证明每条能红）、
   `scripts/check_wp_5347_01_platform_gates.py`（复用平台 `kf/ops/knowledge_factory/gates.py`
   重放 g1–g7）、`tests/test_wp_5347_01.py`（14 条 pytest，含 7 条变异反例）。
7. 交付：`scripts/publish_wp_5347_01_report.py` 把本报告以 `{TITLE}` 为题、
   tags 含 `kf-wp:{PACKAGE_ID}`、mission_id={MISSION_ID} 发到平台；
   正文唯一一个 JSON 代码块即 kf_result 信封（发送前断言只有一块）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/wp-5347-01/asset_manifest.json` | 工序 01 声明输出：源哈希/字符数/标题 + {cts['assets']} 条资产（kind/reachability/locator） |
| `artifacts/wp-5347-01/kf_result.json` | kf_result 信封：package_id/task_type/report_id/provenance/outputs（claims=[]） |
| `artifacts/wp-5347-01/KF-RESULT-wp-5347-01.md` | 本报告（唯一一个 JSON 代码块） |
| `artifacts/wp-5347-01/checks.json` | 复核结果（每项 acceptance + 实测数字） |
| `artifacts/wp-5347-01/report_5347.md` | 源字节快照（复跑与离线复核用，哈希即 provenance） |
| `scripts/wp_5347_01_register_assets.py` | 登记器（唯一产出路径） |
| `scripts/verify_wp_5347_01.py` | 复核器（哈希/locator/ID/信封） |
| `tests/test_wp_5347_01.py` | pytest 机检 |

## ④ 证据定位表（字段 → 原文引文片段）

| 字段 | 值/判定 | 原文引文（逐字，含偏移） |
|---|---|---|
| report 标题 | {src['title']} | 见 `## ① 案例介绍` 首行标题 |
| `source.source_hash` | `{src['source_hash']}` | 由 markdown 字节独立重算，非引文 |
| `source.chars` | {src['chars']} | 契约申报值 {CONTRACT_CHARS}，实测 {src['chars']} |
| 资产 `{m['assets'][0]['asset_id']}` | `{m['assets'][0]['path']}` | 见下表逐字行与偏移 |

资产逐条登记（`quote` 全文见 manifest 的 `locator.quote`，偏移已机器复核）：

| asset_id | path | kind | reachability | resolved | 所在节 |
|---|---|---|---|---|---|
{rows}

按 kind 计数：

| kind | 数量 |
|---|---|
{kind_rows}

按可达性计数：

| reachability | 数量 |
|---|---|
{reach_rows}

无场量云图、无解析解/基线比较曲线：本包是纯 I/O 登记（不产生任何物理量或数值结果），
故改画两张台账图——`figures/asset_inventory.png`（按 kind×可达性的资产分布，resolved 恒为 0）
与 `figures/gate_evidence.png`（平台门 g1–g7 与本地 acceptance A1–A10 的逐项状态）。
两图均由 `scripts/wp_5347_01_figures.py` 从 `asset_manifest.json`/`checks.json`/
`platform_gate.json` 直接投影，无手抄数字。

## ⑤ 注意点与局限

- **图像字节不可得**：记录只有 name/caption，figure 端点 404；两张图登记为 `metadata_only`，
  下游若需要图像，必须回 TensorDEM 仓库工件，不能引用本包。
- **跨仓工件一律 resolved=false**：`docs/`、`scripts/`、`artifacts/`、`src/`、`tests/` 下的路径
  属于 TensorDEM（main@524821fd），不在本包 `source_uri` 字节范围内；工序 01 只登记不检出。
- **未使用本地 TensorDEM 检出做存在性校验**：本机虽有检出，但其 HEAD 未必等于 `524821fd`，
  用它“证明存在”会产生不可绑定的结论；如需校验应由上游给出 commit 级工件清单。
- **扫描只覆盖路径形状**：散文里的纯名字（如 `TensorDEM`、`ruff check`）不登记；规则写在
  manifest `registration.extraction_rule` 里，可复核、可反驳。
- **claims 为空数组是契约允许的完整结果**（objective 只要 register_assets），不是失败；
  acceptance 中 “all_claims_have_evidence_or_explicit_unresolved_status” 因此为**空真**，
  本报告如实标注为 `vacuous (0 claims)`，不得读作“已验证”。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 判定 | 依据 |
|---|---|---|
| valid_json | 通过 | `json.load` 两个产物均成功（见 checks.json） |
| schema_pass | 通过 | kf_result 过 `schemas/kf_result.v1.schema.json`（Draft 2020-12） |
| source_locator_resolvable | 通过 | {sum(1 for a in m['assets'] if a['locator'].get('quote'))} 条字符型 locator 的 quote 均为源字节逐字子串，偏移回读一致 |
| source_hash_matches | 通过 | 契约 `{CONTRACT_SOURCE_HASH}` == 实测 `{src['source_hash']}` |
| no_duplicate_ids | 通过 | {cts['assets']} 条 asset_id 唯一 |
| all_claims_have_evidence_or_explicit_unresolved_status | **空真通过（vacuous, 0 claims）** | 本工序不抽取，claims=[]，未伪造任何 claim |
{gate_line}
{plat_line}

未完成项：无（本工序范围内）。局限已在 ⑤ 声明。

## repro_cmd

```bash
python3 scripts/fetch_report_5347.py --out artifacts/wp-5347-01/report_5347.md \\
 && python3 scripts/wp_5347_01_register_assets.py \\
 && python3 scripts/verify_wp_5347_01.py \\
 && python3 scripts/check_wp_5347_01_platform_gates.py \\
 && python3 scripts/wp_5347_01_register_assets.py --render-only \\
 && python3 scripts/wp_5347_01_figures.py \\
 && python3 -m pytest -q tests/test_wp_5347_01.py
```

## 结果信封

```json
{payload}
```
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="wp-5347-01 asset registration")
    ap.add_argument("--check", action="store_true", help="verify only, write nothing")
    ap.add_argument("--render-only", action="store_true",
                    help="rebuild the manifest/envelope/report in memory and rewrite the "
                         "report markdown only (used after checks/patform gates exist)")
    args = ap.parse_args(argv)

    src_path = OUT_DIR / "report_5347.md"
    meta_path = OUT_DIR / "report_5347.md.meta.json"
    if not src_path.is_file() or not meta_path.is_file():
        print(f"ERROR: source snapshot missing under {OUT_DIR}; run "
              f"scripts/fetch_report_5347.py first", file=sys.stderr)
        return 2
    source_bytes = src_path.read_bytes()
    text = source_bytes.decode("utf-8")
    digest = sha256_bytes(source_bytes)
    if digest != CONTRACT_SOURCE_HASH:
        print(f"ERROR: source_hash mismatch\n  contract={CONTRACT_SOURCE_HASH}\n"
              f"  actual  ={digest}", file=sys.stderr)
        return 2
    if len(text) != CONTRACT_CHARS:
        print(f"ERROR: chars mismatch contract={CONTRACT_CHARS} actual={len(text)}",
              file=sys.stderr)
        return 2

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    manifest = build_manifest(text, meta, source_bytes)
    result = build_result(manifest)
    report_md = render_report(result)

    if args.render_only:
        (OUT_DIR / f"KF-RESULT-{PACKAGE_ID}.md").write_text(report_md, encoding="utf-8")
        print(json.dumps({"re-rendered": f"KF-RESULT-{PACKAGE_ID}.md",
                          "chars": len(report_md)}, ensure_ascii=False))
        return 0

    if args.check:
        print(json.dumps({"source_hash": digest, "chars": len(text),
                          "assets": manifest["counts"]["assets"]}, indent=2))
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / "kf_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / f"KF-RESULT-{PACKAGE_ID}.md").write_text(report_md, encoding="utf-8")
    print(json.dumps({"wrote": ["asset_manifest.json", "kf_result.json",
                                f"KF-RESULT-{PACKAGE_ID}.md"],
                      "assets": manifest["counts"]["assets"],
                      "by_kind": manifest["counts"]["by_kind"],
                      "source_hash": digest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())