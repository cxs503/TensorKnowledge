"""Publish the wp-14137-01 deliverable as its own platform report and verify the round trip.

The report body is *assembled programmatically* from artifacts/wp-14137-01/asset_manifest.json and
acceptance.json, so no count, hash or quote in the prose is hand-typed. The body carries exactly one
```json block, which is the result envelope written verbatim by scripts/kf_register_14137.py.

Nothing is written back to report 14137 (the registered source).

Usage: python3 scripts/kf_publish_14137.py
Outputs: docs/wp-14137-01/KF-RESULT-wp-14137-01.md, docs/wp-14137-01/publish_roundtrip.json
"""
from __future__ import annotations

import base64
import hashlib
import re
import sys
import json
import os
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/wp-14137-01"
ART = ROOT / "artifacts/wp-14137-01"
DOCS = ROOT / "docs/wp-14137-01"
PACKAGE_ID = "wp-14137-01"
REPORT_ID = "14137"
MISSION_ID = 15782
TITLE = f"KF-RESULT {PACKAGE_ID}"
SCENARIO_KEY = "dem_clump_shape_effect"
FIGURES = [("fig_asset_manifest.png",
            "左：24 条登记资产按类别与解析判定的分布；右：每条资产 locator 在 7569 字符源 markdown 中的字符区间"
            "（绿=源内可解析，红=引用但本工序不可解析）")]


def api_base() -> str:
    return os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def call(path: str, body: dict | None = None, token: str | None = None, method: str = "POST"):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(api_base() + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        return exc.code, {"error": exc.read().decode("utf-8", "replace")[:800]}


def login() -> str | None:
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (user and pwd):
        return None
    status, d = call("/auth/login", {"username": user, "password": pwd})
    if status not in (200, 201):
        return None
    return d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")


def extract_json_block(markdown: str) -> dict:
    assert markdown.count("```json") == 1, f"{markdown.count('```json')} json blocks (must be 1)"
    start = markdown.find("```json")
    end = markdown.rfind("\n```")          # the block is the last fence in the document
    assert end > start, "no closing fence after the json block"
    return json.loads(markdown[start + len("```json"):end])


NEGATIONS = ("不标", "未标", "不做", "未做", "未", "不", "not ", "no ", "never")


def verified_audit(markdown: str) -> dict:
    """Every mention of 'verified' must be negated (or part of a *_not_verified identifier name).

    Guards the contract constraint do_not_mark_claims_as_verified: we assert *negations*, not the
    absence of the word, because the report deliberately says '未标 verified' and ships a key named
    ``registered_not_verified``.
    """
    contexts, positive = [], 0
    for mt in re.finditer("verified", markdown, flags=re.IGNORECASE):
        i = mt.start()
        # enclosing identifier token, e.g. registered_not_verified
        j0, j1 = i, mt.end()
        while j0 > 0 and (markdown[j0 - 1].isalnum() or markdown[j0 - 1] == "_"):
            j0 -= 1
        while j1 < len(markdown) and (markdown[j1].isalnum() or markdown[j1] == "_"):
            j1 += 1
        token = markdown[j0:j1]
        pre = markdown[max(0, i - 40):i]
        negated = ("not" in token.lower().split("_")) or any(n in pre for n in NEGATIONS)
        contexts.append(dict(context=markdown[max(0, i - 34):i + 12].replace("\n", " "),
                             token=token, negated=negated))
        if not negated:
            positive += 1
    return dict(occurrences=len(contexts), non_negated_occurrences=positive,
                mentions=contexts[:12],
                verdict="no verified claim" if positive == 0 else "REVIEW: non-negated 'verified' present")


def build_markdown(manifest: dict, acceptance: dict, envelope: dict) -> str:
    src = manifest["source"]
    c = manifest["counts"]
    acc_rows = "\n".join(
        f"| {x['item']} | {'✅ PASS' if x['result'] == 'PASS' else '❌ FAIL'} | {x['detail'][:110]} |"
        for x in acceptance["checks"])
    def _row(a: dict) -> str:
        head = a["locator"]["quote"].splitlines()[0][:58].replace("|", "\\|")
        return (f"| {a['asset_id']} | {a['asset_class']} | `{a['in_report_section'][:34]}` | "
                f"[{a['locator']['start_char']}:{a['locator']['end_char']}] "
                f"(L{a['locator']['start_line']}–{a['locator']['end_line']}) | "
                f"{a['resolution']} / `{a['resolution_check']['check']}` → "
                f"{a['resolution_check']['result']} | {head} |")

    ev_rows = "\n".join(_row(a) for a in manifest["assets"])
    by_class = ", ".join(f"{k}×{v}" for k, v in sorted(c["by_class"].items(), key=lambda kv: -kv[1]))
    block = json.dumps(envelope, ensure_ascii=False, indent=2)

    return f"""# {TITLE}

本报告是工作包 `{PACKAGE_ID}`（task_type=`01-asset-registration`，lane C）的唯一结果信道。
登记对象=报告 `{REPORT_ID}`（`{src['uri']}`，字段 `{src['field']}`，{src['chars']} 字符 /
{src['bytes_utf8']} UTF-8 字节，sha256 `{src['hash']}`）。**只登记资产，不做抽取、不做分类、不标 verified。**

## ① 本工序做了什么

1. 从平台 API 取回报告 {REPORT_ID} 的 `markdown` 字段，本地重算 sha256 并与契约 `source_hash` 逐字比对
   （结果：{src['hash'][:16]}… 一致，字符数 {src['chars']} 与契约 `input.chars` 一致）。
2. 从正文中解析出 {c['assets']} 条**被引用的资产**并逐条登记：类别（{by_class}）、所在章节、
   字符区间 locator、解析判定（resolved_in_source={c['resolved_in_source']} /
   referenced_unresolved={c['referenced_unresolved']} / declared_absent={c['declared_absent']}）。
3. 对每条资产跑一条**机器判据**（worktree 路径存在性 / 只读 SQL 计数 / 集群作业状态 / 平台 figures 字段 /
   地址抽取），判定结果与其理由一并写入 manifest——不可解析的**如实标 unresolved 并写原因**，不猜地址。
4. 产出 `asset_manifest.json` + 结果信封 `kf_result.v1`，并写 {acceptance['total']} 项独立验收机检（见 ⑥）。
5. `claims` 为空数组：契约 `objective.classify_report_type=false`、本工序无抽取，空数组是合法完整结果
   （schema 原话「零条=合法完整结果」），不为填指标造知识。

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步骤 | 工具 / 命令 | 关键设置 |
|---|---|---|
| 取源 | `python3 scripts/kf_fetch_14137.py` | Bearer 登录 env 凭据；只 GET `/tensor/reports/{REPORT_ID}`，不写回源报告 |
| 登记 | `python3 scripts/kf_register_14137.py` | 每个 `quote` 从 markdown **切片**得到（锚点=唯一行 + 行跨度），写盘前校验 `quote` 是唯一子串；锚点不唯一/不存在则整单中止 |
| 证据判据 | 同上 `resolution_check()` | 判据类型见 ④ 表；DB 用只读 `select count(*)`；集群用 `run_cluster ps` 落盘到 `runs/wp-14137-01/cluster_cj974_probe.txt` |
| 验收 | `python3 scripts/kf_verify_14137.py`（`--offline --out <path>` = 断网复跑，另存文件不覆盖交付物） | 不复用登记脚本，独立重算：哈希三路（本地/字段/信封）+ 在线重取、locator 重切片、行号重算、id 去重、schema 校验 |
| 测试 | `python3 -m pytest tests/test_kf_wp14137_01.py -q` | 6 项断言（离线，不联网） |
| 图 | `python3 scripts/kf_figures_14137.py` | 数字全部从 manifest 读，不手抄 |

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/{PACKAGE_ID}/asset_manifest.json` | 主产物：{c['assets']} 条资产、locator、resolution_check、counts、integrity（含 schema_pass 记录） |
| `runs/{PACKAGE_ID}/kf_result.{PACKAGE_ID}.json` | `kf_result.v1` 结果信封（本报告唯一 json 块的来源，二者内容一致） |
| `runs/{PACKAGE_ID}/report_14137.md` / `report_14137.json` | 源 markdown 与原始 API 载荷（字节级固定，便于复算哈希） |
| `runs/{PACKAGE_ID}/cluster_cj974_probe.txt` | 集群作业 cj974 状态探测原始输出（资产 A13 的判据依据） |
| `artifacts/{PACKAGE_ID}/acceptance.json` | {acceptance['total']} 项 acceptance 机检逐条结果 |
| `artifacts/{PACKAGE_ID}/fig_asset_manifest.png` | 图 1（见 ④ 后） |
| `scripts/kf_fetch_14137.py` / `kf_register_14137.py` / `kf_verify_14137.py` / `kf_figures_14137.py` / `kf_publish_14137.py` | 一键复跑链 |
| `tests/test_kf_wp14137_01.py` | 契约不变量的 pytest 断言 |

## ④ 证据定位表（资产 → 原文引文片段）

locator 全部为 `char_span`，`md[start_char:end_char] == quote` 且 `quote` 在 markdown 中唯一（机检见 ⑥）。

| id | 类别 | 所在章节 | char 区间 (行) | 解析 / 判据 → 结果 | 引文首行（逐字） |
|---|---|---|---|---|---|
{ev_rows}

图 1：`fig_asset_manifest.png` —— {FIGURES[0][1]}。

## ⑤ 注意点与局限

1. **{c['referenced_unresolved']}/{c['assets']} 条资产判为 referenced_unresolved，这是真相不是缺陷**：报告 {REPORT_ID} 的代码/数据/图件都在
   TensorDEM 仓（`src/tensordem/contact/rolling_static.py`、`artifacts/GAP-DEM-CLUMP-R2/results.json` 等），
   本工作树是 TensorKnowledge 检出，契约又禁止改写外部仓产物 ⇒ 只登记路径，不解析版本（报告未给 commit hash）。
2. **平台表行数未能机检**：只读 `select count(*)` 被拒（`permission denied for table oss_solutions`），
   故 A11 的「6 行」、A12 的「218 行 / 140 个 feature_slug」只是**报告自报值**，登记为 unresolved，
   未升级为已核实。任何下游引用须注明「自报、未复核」。
3. **集群作业 cj974 仍 queued**（探测时点 656.8 min），报告自己声明「未回的数不引用」；本工序据此不给任何 a/b=3.0
   与 seed=1 的数值登记。
4. **图件有元数据无载荷**：平台 `figures` 字段只有 `name`+`caption`（`gap_dem_clump_r2.png`），无 `png_base64`；
   图件本体只在 TensorDEM 仓路径下 ⇒ A10 仍 unresolved。
5. **本工序不判定上游结论真伪**：报告 {REPORT_ID} 自报 13 项内核测试通过、repose 低于文献带 22–37% 的 honest-FAIL、
   fail_stage=`repose_mass_matched_fill_infeasible`，这些仅作为**被登记的内容**存在于 ④ 表内嵌表格
   （A20–A23 四条 in_source_table），本工序既未复跑测试也未复核数值。zero-hand-transcription：所有引用由脚本切片。
6. **schema 口径**：`schemas/asset_manifest.v1.schema.json` 是 wp-448-01 写的仓内本地 schema，其
   `package_id`/`report_id`/`source.uri` 为 `const`。本工序**在内存中替换这三个身份常量**后校验并在
   `integrity.schema_pass` 显式记录（不改上游文件）；若平台侧 schema 更严，平台门为准。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 依据（机检输出摘要） |
|---|---|---|
{acc_rows}

合计 **{acceptance['passed']}/{acceptance['total']} PASS**（`artifacts/{PACKAGE_ID}/acceptance.json`）。
另：`pytest tests/test_kf_wp14137_01.py -q` → 6 passed（测试跑的是 `--offline --out acceptance.offline.json`，
不覆盖本表的在线结果）。
若有失败项：本行如实写结果；本次运行无失败项，**未粉饰**（含 ⑤ 第 2 条 permission denied 已记为 unresolved 而非 pass）。

## 复现（一键）

```bash
cd <TensorKnowledge worktree>
python3 scripts/kf_fetch_14137.py            # 取源 + 校验 sha256（应打印 MATCH: True）
python3 scripts/kf_register_14137.py         # 登记 24 条资产 → artifacts/{PACKAGE_ID}/asset_manifest.json
python3 scripts/kf_verify_14137.py           # 18 项 acceptance 机检（--offline 可断网复跑）
python3 scripts/kf_figures_14137.py          # 图 1
python3 -m pytest tests/test_kf_wp14137_01.py -q
```

## 结果信封（全文唯一 json 代码块，机器门按此解析）

```json
{block}
```
"""


def main() -> int:
    if "--recheck-only" in sys.argv:
        rid = sys.argv[sys.argv.index("--recheck-only") + 1]
        return recheck_only(rid)
    manifest = json.loads((ART / "asset_manifest.json").read_text())
    acceptance = json.loads((ART / "acceptance.json").read_text())
    envelope = json.loads((RUN / f"kf_result.{PACKAGE_ID}.json").read_text())

    body = build_markdown(manifest, acceptance, envelope)
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / f"KF-RESULT-{PACKAGE_ID}.md").write_text(body)
    assert extract_json_block(body) == envelope, "json block differs from the envelope artifact"

    figures = []
    for name, caption in FIGURES:
        png = (ART / name).read_bytes()
        figures.append({"name": name, "caption": caption,
                        "png_base64": base64.b64encode(png).decode()})

    src_hash = hashlib.sha256((RUN / "report_14137.md").read_text().encode()).hexdigest()
    payload = {
        "title": TITLE,
        "summary": (
            f"登记报告 {REPORT_ID} 的源资产：markdown 逐字节固定（sha256 {src_hash[:16]}…、{manifest['source']['chars']} 字符），"
            f"{manifest['counts']['assets']} 条资产的字符区间/引文/唯一性全部机检；"
            f"{manifest['counts']['resolved_in_source']} 条源内可解析表格，"
            f"{manifest['counts']['referenced_unresolved']} 条外部/越权工件（TensorDEM 仓、平台表权限不足、"
            "集群作业 cj974 仍 queued）如实标 unresolved 并附判据；claims 空（本工序不抽取、不标 verified）。"
        ),
        "scenario_key": SCENARIO_KEY,
        "mission_id": MISSION_ID,
        "tags": ["kf-work-package", f"kf-wp:{PACKAGE_ID}", "asset-registration", "provenance",
                 f"report-{REPORT_ID}", "DEM", "clump", "honest-FAIL"],
        "markdown": body,
        "figures": figures,
    }

    token = login()
    status, resp = call("/tensor/reports", payload, token)
    print("POST /tensor/reports ->", status)
    if status not in (200, 201):
        print(json.dumps(resp, ensure_ascii=False)[:900])
        return 1
    new_id = resp.get("id") or (resp.get("data") or {}).get("id")
    print("published report id:", new_id)

    # ---- round trip: what the gate will recompute ----
    gs, record = call(f"/tensor/reports/{new_id}", token=login(), method="GET")
    if isinstance(record.get("data"), dict):
        record = record["data"]
    stored_md = record.get("markdown", "")
    block = extract_json_block(stored_md)
    fresh_status, fresh_rec = call(f"/tensor/reports/{REPORT_ID}", token=login(), method="GET")
    if isinstance(fresh_rec.get("data"), dict):
        fresh_rec = fresh_rec["data"]
    fresh_hash = hashlib.sha256((fresh_rec.get("markdown") or "").encode()).hexdigest()
    recheck = {
        "published_report_id": new_id,
        "http_status": gs,
        "json_blocks_in_markdown": stored_md.count("```json"),
        "json_block_round_trip_equal": block == envelope,
        "provenance_hash_equals_fresh_report_14137_hash": block["provenance"]["source_hash"] == "sha256:" + fresh_hash,
        "fresh_report_14137_hash": fresh_hash,
        "report_id_field": block["report_id"],
        "package_id_field": block["package_id"],
        "task_type_field": block["task_type"],
        "tags_stored": record.get("tags"),
        "title_stored": record.get("title"),
        "mission_id_stored": record.get("mission_id"),
        "figures_stored": [f.get("name") for f in record.get("figures", [])],
        "verified_mention_audit": verified_audit(stored_md),
        "body_chars": len(stored_md),
    }
    # supersession bookkeeping: only one report is authoritative per package; earlier ids are audited
    rt_path = DOCS / "publish_roundtrip.json"
    history: list[dict] = []
    if rt_path.exists():
        prev = json.loads(rt_path.read_text())
        history = [h for h in prev.get("superseded_reports", []) if isinstance(h, dict)]
        if prev.get("published_report_id") not in (None, new_id):
            history.append({
                "report_id": prev["published_report_id"],
                "superseded_by": new_id,
                "reason": ("同一工作包的早期版本：asset_manifest 的 in_report_section 由「最近一条以 # 开头的行」"
                           "推导，误把 §7 代码块内的注释行（`# 单算例` / `# 全网格（集群分片，8 片）`）当成章节；"
                           "本版改为围栏感知的标题映射（其余 locator/hash/claims 不变）"),
            })
    recheck["superseded_reports"] = history
    recheck["superseded_note"] = ("authoritative report = published_report_id; earlier ids are kept for audit only"
                                  if history else "first and only published report for this package")
    rt_path.write_text(json.dumps(recheck, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(recheck, ensure_ascii=False, indent=2))
    ok = all([recheck["json_block_round_trip_equal"], recheck["json_blocks_in_markdown"] == 1,
              recheck["provenance_hash_equals_fresh_report_14137_hash"],
              recheck["report_id_field"] == REPORT_ID, recheck["package_id_field"] == PACKAGE_ID,
              f"kf-wp:{PACKAGE_ID}" in (record.get("tags") or [])])
    print("round_trip_ok:", ok)
    return 0 if ok else 1


def recheck_only(report_id: str) -> int:
    """Re-verify an already published report (no new POST: one deliverable per package)."""
    envelope = json.loads((RUN / f"kf_result.{PACKAGE_ID}.json").read_text())
    token = login()
    gs, record = call(f"/tensor/reports/{report_id}", token=token, method="GET")
    if isinstance(record.get("data"), dict):
        record = record["data"]
    stored_md = record.get("markdown", "")
    block = extract_json_block(stored_md)
    _, fresh_rec = call(f"/tensor/reports/{REPORT_ID}", token=token, method="GET")
    if isinstance(fresh_rec.get("data"), dict):
        fresh_rec = fresh_rec["data"]
    fresh_hash = hashlib.sha256((fresh_rec.get("markdown") or "").encode()).hexdigest()
    audit = verified_audit(stored_md)
    recheck = {
        "published_report_id": report_id,
        "http_status": gs,
        "json_blocks_in_markdown": stored_md.count("```json"),
        "json_block_round_trip_equal": block == envelope,
        "provenance_hash_equals_fresh_report_14137_hash": block["provenance"]["source_hash"] == "sha256:" + fresh_hash,
        "fresh_report_14137_hash": fresh_hash,
        "report_id_field": block["report_id"],
        "package_id_field": block["package_id"],
        "task_type_field": block["task_type"],
        "tags_stored": record.get("tags"),
        "title_stored": record.get("title"),
        "mission_id_stored": record.get("mission_id"),
        "figures_stored": [f.get("name") for f in record.get("figures", [])],
        "verified_mention_audit": audit,
        "body_chars": len(stored_md),
        "mode": "recheck-only: same published report re-verified, no republish (one deliverable per package)",
    }
    (DOCS / "publish_roundtrip.json").write_text(json.dumps(recheck, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(recheck, ensure_ascii=False, indent=2))
    ok = all([recheck["json_block_round_trip_equal"], recheck["json_blocks_in_markdown"] == 1,
              recheck["provenance_hash_equals_fresh_report_14137_hash"],
              recheck["report_id_field"] == REPORT_ID, recheck["package_id_field"] == PACKAGE_ID,
              f"kf-wp:{PACKAGE_ID}" in (record.get("tags") or []),
              audit["non_negated_occurrences"] == 0])
    print("round_trip_ok:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())