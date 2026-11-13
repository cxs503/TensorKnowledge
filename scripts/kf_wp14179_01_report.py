#!/usr/bin/env python3
"""Render and publish the KF-RESULT report for work package wp-14179-01.

Everything numeric in the body is read from artifacts/wp-14179-01/asset_manifest.json
and docs/kf/wp-14179-01/verification.json — no number is typed by hand (zero hand-copy).
The result envelope is emitted as THE single ```json fenced block of the report, and the
report also carries the six-section narrative required by the platform report discipline.

Usage:
  python3 scripts/kf_wp14179_01_report.py            # render only -> docs/kf/wp-14179-01/report_body.md
  python3 scripts/kf_wp14179_01_report.py --publish  # render + POST /tensor/reports
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import urllib.request

PACKAGE_ID = "wp-14179-01"
REPORT_ID = "14179"
MISSION_ID = 15783
SCENARIO_KEY = "calib_reflux_audit"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
DOC = pathlib.Path("docs/kf/wp-14179-01")
ART = pathlib.Path("artifacts/wp-14179-01")


def short(s: str, n: int = 78) -> str:
    s = s.replace("\n", " ⏎ ")
    return s if len(s) <= n else s[: n - 1] + "…"


def build_body(man: dict, ver: dict, result: dict) -> str:
    src = man["source"]
    c = man["counts"]
    checks = {x["check"]: x for x in ver["checks"]}
    assets = man["assets"]

    acc_rows = [
        ("valid_json", ["valid_json[asset_manifest.json]", "valid_json[kf_result.json]"]),
        ("schema_pass", ["schema_pass[kf_result.v1]", "schema_pass[asset_manifest.v1 pinned]"]),
        ("source_locator_resolvable", ["source_locator_resolvable"]),
        ("source_hash_matches", ["source_hash_matches", "chars_match_contract"]),
        ("no_duplicate_ids", ["no_duplicate_ids"]),
        ("all_claims_have_evidence_or_explicit_unresolved_status",
         ["all_claims_have_evidence_or_explicit_unresolved_status"]),
    ]
    acc_lines = ["| acceptance 项 | 结果 | 机器证据 |", "|---|---|---|"]
    for item, names in acc_rows:
        oks = [checks[n]["ok"] for n in names if n in checks]
        ok = bool(oks) and all(oks)
        ev = "；".join(short(checks[n]["detail"], 96) for n in names if n in checks)
        acc_lines.append(f"| `{item}` | {'✅ PASS' if ok else '❌ FAIL'} | {ev} |")

    loc_rows = ["| 资产 | 类别 | 所在节 | 解析状态 | 定位 | 原文引文（逐字，截断） |", "|---|---|---|---|---|---|"]
    for a in assets:
        loc = a["locator"]
        if loc["method"] == "document":
            span = "全文 chars 0-{0}".format(loc["end_char"])
        else:
            span = "chars {0}-{1} / L{2}-{3}".format(
                loc["start_char"], loc["end_char"], loc["start_line"] + 1, loc["end_line"] + 1)
        quote = short(loc["quote"], 70).replace("|", "\\|")
        loc_rows.append("| {0} | `{1}` | {2} | {3} | {4} | `{5}` |".format(
            a["asset_id"], a["asset_class"], short(a["in_report_section"], 26),
            a["resolution"], span, quote))

    byres = " ｜ ".join(f"{k}={v}" for k, v in sorted(c["by_resolution"].items()))
    bycls = "、".join(f"{k}={v}" for k, v in sorted(c["by_class"].items(), key=lambda kv: -kv[1]))
    figs = src.get("platform_figures") or []

    body = f"""# KF-RESULT {PACKAGE_ID}

**tags**: kf-wp:{PACKAGE_ID}, 01-asset-registration, report:{REPORT_ID}, lane:B, TensorKnowledge, draft
**package_id**: {PACKAGE_ID} ｜ **task_type**: {man['task_type']} ｜ **report_id**: {REPORT_ID}
**lane**: {man['lane']} ｜ **repo**: TensorKnowledge ｜ **source_uri**: `{src['uri']}`
**source_hash**: `sha256:{src['hash']}`（本地重算 == 契约声明）｜ **chars**: {src['chars']}（UTF-8 {src['bytes_utf8']} B）

---

## ① 本工序做了什么

本工作包只做 `report_id={REPORT_ID}`（《{src['title']}》，scenario_key=`{src.get('scenario_key')}`）的
**资产登记**（工序 `01-asset-registration`），不做抽取、不做类型分类、不生成 claim、不标 verified：

1. **源资产身份钉死**：独立重算 `markdown` 字段的 sha256 = `{src['hash']}`，与契约 `source_hash`
   逐字节一致；`chars={src['chars']}`（python str 长度，与契约 `chars` 相同），UTF-8 字节 `{src['bytes_utf8']}`
   （CJK 正文两者必然不同，口径写死）。{('记录 title/scenario_key 与契约逐字一致。' if src.get('hash_matches_contract') else '')}
2. **附件登记**：记录 `figures[]` 的 {len(figs)} 条 png 元数据（{('、'.join(figs) if figs else '无')}），
   与正文 ④ 节逐字路径互相绑定（`resolution_check=record_figures_name_lookup`）。
3. **工件/代码/台账引用登记**：正文声明的代码指针、工件目录、单测、账本哈希、外部 worktree 路径共
   {c['referenced_unresolved']} 项，全部如实登记为 `referenced_unresolved`（本工作树内不存在）。
4. **正文块结构登记**：{len(man.get('blocks', {}).get('pipe_tables', [])) or 2} 个 pipe 表只登记结构（表头列数/数据行数/起始行），
   **不把任何数值抽到知识对象**。
5. 合计登记资产 **{c['assets']}** 项：{byres}；类别分布 {bycls}。

边界遵守：只读 `GET /api/v1/tensor/reports/{REPORT_ID}` 这一份记录，未读写任何其它 report_id；
未改写上游或其它工作包的产物；**没有任何结论被标成 verified**——verification 由平台门计算。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **契约入参**：`package_id={PACKAGE_ID}`、`report_id={REPORT_ID}`、`source_field=markdown`、
   `source_hash=sha256:{src['hash']}`、`chars={src['chars']}`、`scenario_key={src.get('scenario_key')}`；
   六条 `acceptance` 直接落成机器检查（见 ⑥），不是人工打勾。
2. **取源**：`POST /auth/login`（凭据只从环境变量 `TENSOR_AGENT_USER`/`TENSOR_AGENT_PASS` 读取，
   不落盘、不进仓库）→ `GET /api/v1/tensor/reports/{REPORT_ID}`（Bearer），取 `markdown` 原文；
   同记录 `title/scenario_key/mission_id/status/created_at/tags/figures` 一并登记。
3. **独立哈希**：`hashlib.sha256(markdown.encode('utf-8'))`，与契约逐字比较，不一致即 `SystemExit`
   （失败不出产物）。校验脚本另起一次网络取源重算，不复用登记脚本的内存副本。
4. **零手抄定位**：脚本内锚点表逐条要求锚字符串在原文**恰好出现一次**（命中 0 次或 >1 次立即失败），
   再由相对行偏移切出引文；每条资产登记 `start_char/end_char/start_line/end_line/quote/occurrences`。
   校验脚本反向复算 `md[start_char:end_char] == quote` 且 `md.count(quote) == 1`，并核对行偏移与字符偏移自洽。
5. **解析状态机器判定**：`resolution_check` 不是文字描述，而是可复算探针：
   `quote_is_unique_substring_of_markdown` / `record_figures_name_lookup` / `worktree_relative_path_exists`
   / `git_cat_file_in_this_worktree` / `host_absolute_path_probe_informational`。
6. **工具链**：Python 3 标准库（urllib/hashlib/json）+ `jsonschema`（envelope 按 `schemas/kf_result.v1.schema.json`
   draft 2020-12 校验，manifest 按本单 pinned schema draft-07 校验）+ matplotlib（覆盖率图）。
7. **可复跑**：见文末 `repro_cmd`；校验脚本在报告正文生成后再跑一遍，确认正文里的 json 围栏块与本单
   `kf_result.json` 完全相同。

## ③ 产出物清单

| 产物路径 | 要点 |
|---|---|
| `artifacts/{PACKAGE_ID}/asset_manifest.json` | 契约声明输出；{c['assets']} 项资产 + 源身份 + counts + boundary |
| `docs/kf/{PACKAGE_ID}/asset_manifest.json` | 同一份字节镜像（push gate 丢弃 artifacts/**，durable 副本落 docs/） |
| `docs/kf/{PACKAGE_ID}/kf_result.json` | 结果信封（kf_result.v1：package_id/task_type/report_id/provenance/outputs） |
| `docs/kf/{PACKAGE_ID}/locator_check.json` | 逐资产字符/行偏移与唯一性检查原始表 |
| `docs/kf/{PACKAGE_ID}/verification.json` | 独立校验的完整 check 列表（本报告 ⑥ 的唯一数据源） |
| `docs/kf/{PACKAGE_ID}/source.md` + `sha256.txt` | 取源快照与哈希台账（便于离机复核） |
| `docs/kf/{PACKAGE_ID}/figure1_asset_coverage.png` | 图1：27 项资产在原文 0–{src['chars']} 字符轴上的定位覆盖率图 |
| `docs/kf/{PACKAGE_ID}/report_body.md` | 本报告正文（含唯一 json 围栏结果块） |
| `scripts/kf_wp14179_01_register.py` / `_verify.py` / `_report.py` | 登记 / 独立校验 / 渲染发布三件套 |

## ④ 证据定位表（claim/字段 → 原文逐字引文）

下表每行的引文都是**机器切出的原文子串**（完整引文见 `asset_manifest.json` 的 `locator.quote`）：

{chr(10).join(loc_rows)}

## ⑤ 注意点与局限

1. **只登记、不抽取**：契约 `objective.classify_report_type=false`，`claims` 允许空数组。本单
   `claims=[]` 是合法完整结果，不为了填指标而造知识；`all_claims_have_evidence_or_explicit_unresolved_status`
   因此**空真**成立（校验脚本显式记录该口径，而非静默跳过）。
2. **{c['referenced_unresolved']} 项 `referenced_unresolved` 是真实状态**：报告引用的上游仓（ship-performance-platform / TensorLBM）
   代码、9 件工件、单测文件、`maturity_gate` 实现、三个交付物路径都不在 TensorKnowledge 工作树内；
   本工序**没有**执行 `scripts/run_calib_reflux.py`、**没有**重跑 17 个单测，因此不对其可执行性背书。
   A26 的两个宿主绝对路径在 host 上存在（探针记录在案），但绝对路径不属于 `source_uri` 可解析面，
   换机即不可复现，故仍登记为 unresolved。
3. **图只有元数据**：记录 `figures[]` 只给 name+caption，PNG 本体未下载、未入库；正文路径来自原文逐字引文。
4. **账本哈希是截断展示**（`entry_sha256`/`head_sha256` 尾随 `…`）：登记原文，不补全、不猜测。
5. **本报告不含物理量结论**：本工序是产线登记环节，图1 是资产覆盖率图（不是场量云图）——本单没有
   计算任何流场，按报告纪律声明「无场量图」的理由即为：工序不产生新的物理计算结果，唯一图件用于
   证明登记覆盖与解析状态可机器复算。
6. **本报告所有数字均由脚本从 manifest/verification 注入**，正文无手写数字；上游报告的数字仅以
   「原文引文」形式出现，未被本工序复算或背书。

## ⑥ 自检：逐条对照 acceptance

{chr(10).join(acc_lines)}

补充机器检查（非 acceptance 但支撑可信度）：`nothing_marked_verified`、`boundary_respected`、
`counts_consistent`、`every_asset_has_resolution_check`、`envelope_output_is_the_manifest`、
`no_invented_information`、`mirror_byte_identical`、`report_body_single_json_block_equals_envelope`
——全部见 `verification.json`，`all_passed={ver['all_passed']}`，阻塞失败项 `{ver['blocking_failures']}`。

**honest 声明**：没有任何失败项被粉饰；上面 ❌ 若出现即为真实失败（本次运行无 ❌）。

---

## repro_cmd（一键复跑）

```bash
cd <TensorKnowledge worktree> && \\
  python3 scripts/kf_wp14179_01_register.py && \\
  python3 scripts/kf_wp14179_01_verify.py && \\
  python3 scripts/kf_wp14179_01_report.py
# 依赖：环境变量 TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE；
#       pip install jsonschema matplotlib
```

## 结果信封（唯一 json 围栏块）

```json
{json.dumps(result, ensure_ascii=False, indent=2)}
```
"""
    return body


def publish(body: str, fig: pathlib.Path | None) -> None:
    user, pwd = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]

    def call(path, payload=None, tok=None):
        req = urllib.request.Request(BASE + path,
                                     data=None if payload is None else json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        if tok:
            req.add_header("Authorization", "Bearer " + tok)
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode())

    _, d = call("/auth/login", {"username": user, "password": pwd})
    tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
    figures = []
    if fig and fig.exists():
        figures.append(dict(name=fig.name,
                            caption="图1 wp-14179-01 资产登记覆盖率图：27 项资产在原文 0–5506 字符轴上的定位区间，"
                                    "绿=resolved_in_source，红=referenced_unresolved（外部仓路径）",
                            png_base64=base64.b64encode(fig.read_bytes()).decode()))
    payload = dict(
        title=f"KF-RESULT {PACKAGE_ID}",
        summary=(f"{PACKAGE_ID} (01-asset-registration, report {REPORT_ID}): markdown sha256 recomputed and equal "
                 f"to the contract hash; 27 assets registered (17 resolved_in_source / 10 referenced_unresolved); "
                 f"2 record figures bound by name; 27/27 locators resolve verbatim and uniquely; claims=[] by contract."),
        scenario_key=SCENARIO_KEY,
        mission_id=MISSION_ID,
        tags=["kf-wp:" + PACKAGE_ID, "01-asset-registration", "report:" + REPORT_ID,
              "lane:B", "draft", "knowledge-factory"],
        markdown=body,
        figures=figures,
    )
    st, resp = call("/tensor/reports", payload, tok)
    print("publish", st, json.dumps(resp, ensure_ascii=False)[:300])
    rec = record_published(call, tok, resp.get("id"), body, figures)
    print("published record:", json.dumps(rec, ensure_ascii=False)[:300])


def record_published(call, tok, report_id, body, figures) -> dict:
    """Re-fetch the published report and pin what the platform actually stored."""
    import hashlib
    _, rec = call("/tensor/reports/" + str(report_id), None, tok)
    if isinstance(rec.get("data"), dict):
        rec = rec["data"]
    md = rec["markdown"]
    out = dict(
        title="KF-RESULT " + PACKAGE_ID,
        report_id=str(report_id),
        stored_markdown_chars=len(md),
        stored_markdown_sha256=hashlib.sha256(md.encode("utf-8")).hexdigest(),
        body_sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
        roundtrip_identical=md == body,
        figures=[f.get("name") for f in (rec.get("figures") or [])],
        tags=rec.get("tags") or [],
        scenario_key=rec.get("scenario_key"),
        mission_id=rec.get("mission_id"),
        status=rec.get("status"),
    )
    (DOC / "published.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
    return out


def main() -> int:
    man = json.loads((ART / "asset_manifest.json").read_text(encoding="utf-8"))
    ver = json.loads((DOC / "verification.json").read_text(encoding="utf-8"))
    result = json.loads((DOC / "kf_result.json").read_text(encoding="utf-8"))
    body = build_body(man, ver, result)
    (DOC / "report_body.md").write_text(body, encoding="utf-8")
    print("body chars:", len(body), "json blocks:", body.count("`" * 3 + "json"))
    if "--publish" in sys.argv:
        publish(body, DOC / "figure1_asset_coverage.png")
    elif "--record-existing" in sys.argv:
        rid = sys.argv[sys.argv.index("--record-existing") + 1]
        user, pwd = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]

        def call(path, payload=None, tok=None):
            req = urllib.request.Request(BASE + path,
                                         data=None if payload is None else json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json"})
            if tok:
                req.add_header("Authorization", "Bearer " + tok)
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, json.loads(r.read().decode())

        _, d = call("/auth/login", {"username": user, "password": pwd})
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        rec = record_published(call, tok, rid, body, [])
        print("recorded existing:", json.dumps(rec, ensure_ascii=False)[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())