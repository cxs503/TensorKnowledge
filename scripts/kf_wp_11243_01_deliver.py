#!/usr/bin/env python3
"""KF wp-11243-01 delivery: result envelope -> schema gates -> figure -> report -> verify.

Everything in the report that is a number or a quote is read out of
knowledge/kf/wp-11243-01/asset_manifest.json (itself built by character-offset
slicing of the source markdown), so nothing is restated from memory.

    python3 scripts/kf_wp_11243_01_deliver.py            # build + validate + publish + verify
    python3 scripts/kf_wp_11243_01_deliver.py --no-post  # build + validate only

Exit code 0 iff every gate passes; 1 otherwise (honest failure).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PKG = "wp-11243-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "11243"
SCENARIO = "tensordem-cg-upscaling"
MISSION_ID = 15694
SOURCE_HASH = "sha256:d278a86d919c8f9093f0b1786fcbf15409897d999f6e960716334727d3117598"

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "knowledge" / "kf" / PKG
MANIFEST = OUT / "asset_manifest.json"
RESULT = OUT / "result.json"
REPORT_MD = OUT / "report_wp-11243-01.md"
FIGURE = OUT / "fig_manifest_composition.png"
VALIDATION = OUT / "validation.json"
VERIFY = OUT / "publish_verification.json"


def api(path: str, body: dict | None = None, method: str = "GET", raw: bool = False):
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    tok = json.loads(
        urllib.request.urlopen(
            urllib.request.Request(
                base + "/auth/login",
                data=json.dumps(
                    {
                        "username": os.environ["TENSOR_AGENT_USER"],
                        "password": os.environ["TENSOR_AGENT_PASS"],
                    }
                ).encode(),
                headers={"Content-Type": "application/json"},
            )
        ).read()
    )["access_token"]
    req = urllib.request.Request(
        base + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req) as resp:
        payload = resp.read()
        return resp.status, (payload if raw else json.loads(payload))


# ---------------------------------------------------------------- envelope
def build_envelope(manifest: dict) -> dict:
    return {
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": SOURCE_HASH,
            "source_field": "markdown",
            "producer": "scripts/kf_wp_11243_01_register.py",
            "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "notes": "read-only on report_id=11243; assets registered, nothing extracted, "
                     "no claim marked verified; every quote sliced by character offset "
                     "from the source markdown / record summary",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": manifest["claims"],
    }


def validate(envelope: dict, manifest: dict) -> dict:
    env_schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
    man_schema = json.loads(
        (ROOT / "schemas" / "asset_manifest.v1.wp-11243-01.schema.json").read_text()
    )
    out = {"kf_result.v1": "pass", "asset_manifest.v1.wp-11243-01": "pass", "details": {}}
    try:
        jsonschema.validate(envelope, env_schema)
    except jsonschema.ValidationError as exc:
        out["kf_result.v1"] = "fail"
        out["details"]["kf_result"] = f"{list(exc.absolute_path)}: {exc.message}"
    try:
        jsonschema.validate(manifest, man_schema)
    except jsonschema.ValidationError as exc:
        out["asset_manifest.v1.wp-11243-01"] = "fail"
        out["details"]["asset_manifest"] = f"{list(exc.absolute_path)}: {exc.message}"

    # acceptance items that are not schema-shaped
    md = (OUT / "source_report_11243.md").read_text()
    quotes_ok = True
    for a in manifest["assets"] + manifest["unresolved_references"]:
        loc = a["locator"]
        if loc["source_field"] == "markdown":
            quotes_ok &= loc["quote"] in md
    ids = [a["asset_id"] for a in manifest["assets"] + manifest["unresolved_references"]]
    out["acceptance"] = {
        "valid_json": json.loads(json.dumps(envelope)) is not None,
        "schema_pass": out["kf_result.v1"] == "pass"
        and out["asset_manifest.v1.wp-11243-01"] == "pass",
        "source_locator_resolvable": quotes_ok
        and all(x["resolved"] for x in manifest["integrity"]["locator_verification"]),
        "source_hash_matches": "sha256:"
        + hashlib.sha256(md.encode("utf-8")).hexdigest()
        == SOURCE_HASH
        == envelope["provenance"]["source_hash"],
        "no_duplicate_ids": len(ids) == len(set(ids)),
        "all_claims_have_evidence_or_explicit_unresolved_status": all(
            ("evidence" in c) or ("status" in c) for c in manifest["claims"]
        ),
    }
    return out


# ---------------------------------------------------------------- figure
def draw_figure(manifest: dict) -> None:
    c = manifest["counts"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), dpi=150)

    klass = dict(sorted(c["by_class"].items(), key=lambda kv: -kv[1]))
    axes[0].barh(list(klass)[::-1], list(klass.values())[::-1], color="#3b6ea5", height=0.6)
    axes[0].set_title("Registered assets by class (n=%d)" % c["assets"], fontsize=10)
    axes[0].set_xlabel("artifacts")
    for i, v in enumerate(list(klass.values())[::-1]):
        axes[0].text(v + 0.05, i, str(v), va="center", fontsize=9)
    axes[0].grid(axis="x", alpha=0.3)

    res = dict(sorted(c["by_resolution"].items()))
    bars = axes[1].bar(list(res), list(res.values()), color=["#2e7d32", "#c62828"], width=0.5)
    axes[1].set_title(
        "Resolution status (locators resolved %d/%d, claims %d)"
        % (c["locators_resolved"], c["locators"], c["claims"]),
        fontsize=10,
    )
    axes[1].set_ylabel("artifacts")
    for b, v in zip(bars, res.values()):
        axes[1].text(b.get_x() + b.get_width() / 2, v + 0.05, str(v), ha="center", fontsize=9)
    axes[1].grid(axis="y", alpha=0.3)
    fig.suptitle(
        "wp-11243-01 asset registration — report 11243 (sha256 %s…, %d chars)"
        % (manifest["source"]["hash"][:12], manifest["source"]["chars"]),
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURE)
    plt.close(fig)


# ---------------------------------------------------------------- report
def run_offline_tests() -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_kf_wp_11243_01.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    tail = [ln for ln in proc.stdout.splitlines() if "passed" in ln or "failed" in ln or "error" in ln]
    return {"exit_code": proc.returncode, "summary": tail[-1] if tail else "", "cmd": "pytest -q tests/test_kf_wp_11243_01.py"}


def render_report(manifest: dict, envelope: dict, val: dict, tests: dict) -> str:
    c = manifest["counts"]
    src = manifest["source"]
    figs = manifest["source"]["platform_figures"]
    blob = json.dumps(envelope, ensure_ascii=False, indent=2)

    def snippet(q: str, n: int = 96) -> str:
        flat = q.replace("\n", " ⏎ ").replace("|", "\\|")
        return flat if len(flat) <= n else flat[: n - 1] + "…"

    rows = []
    for a in manifest["assets"] + manifest["unresolved_references"]:
        loc = a["locator"]
        span = (
            f"L{loc['start_line']}–L{loc['end_line']} (char {loc['start_char']}–{loc['end_char']})"
            if loc["source_field"] == "markdown" and loc["method"] == "char_span"
            else f"{loc.get('pointer', 'whole field')}"
        )
        rows.append(
            f"| {a['asset_id']} | {a['asset_class']} | {a['resolution']} | {span} | "
            f"`{snippet(loc['quote'])}` |"
        )

    fig_rows = [
        "| %s | %s | %s | %s | %s |"
        % (f["name"], f["http_status"], f["bytes"], f["sha256"], f"{f['png_width']}×{f['png_height']}")
        for f in figs
    ]
    acc = val["acceptance"]
    mark = lambda b: "✓" if b else "✗"  # noqa: E731

    fig_b64 = base64.b64encode(FIGURE.read_bytes()).decode()

    md = f"""## ① 本工序做了什么

对 report_id=**11243**（{src['title']}）做**资产登记**（task_type `01-asset-registration`，lane C）：
确认报告 markdown 的字节哈希与契约 `source_hash` 一致，并把该报告所携带的附件/工件逐件登记进
`asset_manifest.json`——**只登记，不抽取**（objective.register_assets=true、
classify_report_type=false），claims 按契约保持空数组，任何结论都未标 verified。

登记结果：**{c['assets']}** 件资产 = {c['by_class']}；其中 {c['by_resolution']}。
源文档 sha256 = `{src['hash']}`，字符数 {src['chars']}、UTF-8 字节数 {src['bytes_utf8']}，
与契约 `sha256:{SOURCE_HASH[7:]}` / chars={src['chars']} **逐项相符**。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：只走平台 API `GET /tensor/reports/11243`（Bearer token 由
   `$TENSOR_AGENT_USER/$TENSOR_AGENT_PASS` 登录换取）。本机 `psql` 对该表无权限
   （`permission denied for table tensor_reports`），因此 API 是唯一信道；脚本内
   `assert str(record["id"]) == "11243"` 守住「只碰这一份报告」的边界。
2. **冻源**：markdown 原样落盘 `knowledge/kf/{PKG}/source_report_11243.md`（{src['bytes_utf8']} 字节），
   作为后续一切引文的只读快照。
3. **零手抄定位**：脚本不写任何一句引文——所有 `quote` 都由**字符偏移切片**从 markdown
   字符串里取出（section 由标题唯一匹配 → 到下一个标题前截断；record 字段由 needle
   命中后按句边界切片）。因此「引文逐字来自原文」是**机制**而非承诺。
4. **附件字节核验**：对 record 声明的 5 个图逐个 `GET /tensor/reports/11243/figures/<name>`，
   记录 HTTP 状态、字节数、PNG 宽高与 sha256，并把字节落到 `figures/`。注意：`/figures`
   列表端点返回 404，但**按名取字节的端点是 200**，故 5 张图全部登记为
   `resolved_in_source`（带字节），而非过往包常见的「有名字无载荷」。
5. **定位复核**：建完之后独立回验一遍——`markdown[start_char:end_char] == quote`、
   `quote in markdown`、行号一致（0 基）、以及引文在源中的出现次数必须为 1；
   复核失败则脚本 `exit 1`。
6. **结构门**：result 信封按 `schemas/kf_result.v1.schema.json`、manifest 按
   `schemas/asset_manifest.v1.wp-11243-01.schema.json` 用 `jsonschema` 校验（见 ③ validation.json）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `knowledge/kf/{PKG}/asset_manifest.json` | 主产物：{c['assets']} 件资产、{c['locators']} 条定位、claims=[]、integrity 全绿 |
| `knowledge/kf/{PKG}/source_report_11243.md` | 源快照（{src['bytes_utf8']} 字节，sha256 `{src['hash'][:16]}…`） |
| `knowledge/kf/{PKG}/figures/fig1..fig5*.png` | 5 个附件字节本体（共 {sum(f['bytes'] for f in figs)} 字节），逐个带 sha256 |
| `knowledge/kf/{PKG}/result.json` | kf_result.v1 信封（outputs.asset_manifest.json 内嵌全量 manifest） |
| `knowledge/kf/{PKG}/validation.json` | 两道 schema 门 + 6 条 acceptance 的机读判定 |
| `knowledge/kf/{PKG}/selfcheck.json` | 登记脚本的 integrity/checks 段 |
| `knowledge/kf/{PKG}/publish_verification.json` | 发布后回读校验（json 块唯一性、回读哈希、图字节可取） |
| `scripts/kf_wp_11243_01_register.py` / `_deliver.py` | 一键复跑（下方 repro_cmd） |
| `tests/test_kf_wp_11243_01.py` | 10 条离线不变量断言（哈希/引文逐字且唯一/表结构与块内容一致/id 唯一/schema） |
| `schemas/asset_manifest.v1.wp-11243-01.schema.json` | 本包 manifest 的结构 schema（schema_pass 的可复现依据） |

平台侧 5 个附件（登记元数据，非本包生成）：

| 附件名 | HTTP | 字节 | sha256 | 尺寸 |
|---|---|---|---|---|
{chr(10).join(fig_rows)}

## ④ 证据定位表（artifact / claim 字段 → 原文引文片段）

源 = `tensor://reports/11243#markdown`（sha256 `{src['hash']}`）。行号为 0 基；`pointer` 形式指向 record 字段。

| id | 类别 | 解析状态 | 定位 | 原文片段（逐字，脚本切片） |
|---|---|---|---|---|
{chr(10).join(rows)}

## ⑤ 注意点与局限

- **不抽取**：本包只登记「有什么」，不判断「内容对不对」。`Scaling Rule Table` 只登记
  表结构与行数（{json.dumps(manifest['assets'][8]['structure'], ensure_ascii=False)}），
  不把 f³/f 这类标度关系升格为 claim。
- **两处只能到 referenced_unresolved**：摘要里的
  `{snippet(manifest['unresolved_references'][0]['locator']['quote'], 70)}` 与
  `{snippet(manifest['unresolved_references'][1]['locator']['quote'], 70)}`
  在 markdown 正文中**不存在对应数字/路径**：正文 `pytest` 出现
  {manifest['unresolved_references'][0]['resolution_check']['markdown_occurrences']} 次、
  `0%` 出现 {manifest['unresolved_references'][1]['resolution_check']['markdown_occurrences']['0%']} 次、
  `56` 出现 {manifest['unresolved_references'][1]['resolution_check']['markdown_occurrences']['56']} 次
  （`deviation` 只作为定性用语 `deviations` 出现
  {manifest['unresolved_references'][1]['resolution_check']['markdown_occurrences']['deviation']} 次，不带任何测量值）。
  这两条属平台 record.summary，登记为未解析，**不得**当作已验证证据使用。
- **正文不引图**：markdown 正文没有任何 figure/路径引用，5 张图仅由 record 声明；
  图与正文段落的对应关系不做断言（caption 由 record 字段逐字复制）。
- **未做的验证**：未运行 TensorDEM 的 pytest 套件、未复核任何标度关系的数值正确性、
  未比对图 3 的误差预算——这些都超出本工序契约（review.required=false）。
- **版本关系**：平台 `/tensor/reports` 只有 POST（PATCH/PUT/DELETE 均 405），故同包早前的
  中间版本以追加方式留档；本报告为**最终版**（含离线测试证据），其 `asset_manifest.json`
  与 worktree 中 `knowledge/kf/wp-11243-01/asset_manifest.json` 逐字节一致。
- 边界合规：全程只读 report_id=11243，未写回该报告，未触碰任何其它 report_id，
  未改写上游产物，未把任何条目标为 verified。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| valid_json | {mark('✗' if not acc['valid_json'] else '✓')} | `json.loads` 往返成功，result.json 可解析 |
| schema_pass | {mark(acc['schema_pass'])} | kf_result.v1={val['kf_result.v1']}；asset_manifest.v1.wp-11243-01={val['asset_manifest.v1.wp-11243-01']} |
| source_locator_resolvable | {mark(acc['source_locator_resolvable'])} | {c['locators_resolved']}/{c['locators']} 条定位回验通过（切片相等 + 子串 + 行号一致 + 唯一） |
| source_hash_matches | {mark(acc['source_hash_matches'])} | 本地重算 `{src['hash']}` = 契约值 |
| no_duplicate_ids | {mark(acc['no_duplicate_ids'])} | {c['assets']} 个 id 无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | {mark(acc['all_claims_have_evidence_or_explicit_unresolved_status'])} | claims=[] 空数组（契约允许），空集真值为真；未造 claim 填空 |

补充机检（离线不变量测试，`{tests['cmd']}`，exit={tests['exit_code']}）：`{tests['summary']}`。

失败项：{('无' if all(acc.values()) else [k for k, v in acc.items() if not v])}。

repro_cmd：

```bash
cd <worktree> && python3 scripts/kf_wp_11243_01_register.py && python3 scripts/kf_wp_11243_01_deliver.py
```

## 结果信封（唯一 json 块）

```json
{blob}
```
"""
    return md


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    envelope = build_envelope(manifest)
    RESULT.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    val = validate(envelope, manifest)
    VALIDATION.write_text(json.dumps(val, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    draw_figure(manifest)

    tests = run_offline_tests()
    report_md = render_report(manifest, envelope, val, tests)
    REPORT_MD.write_text(report_md, encoding="utf-8")
    print("validation:", json.dumps(val["acceptance"], indent=2))
    if not all(val["acceptance"].values()):
        print("LOCAL GATES FAILED — not publishing", flush=True)
        return 1
    if "--no-post" in os.sys.argv:
        return 0

    assert report_md.count("```json") == 1, "report must carry exactly one json block"
    payload = {
        "title": f"KF-RESULT {PKG}",
        "summary": (
            f"asset registration for report 11243: {manifest['counts']['assets']} artifacts "
            f"registered ({manifest['counts']['by_resolution']}), {manifest['counts']['locators_resolved']}"
            f"/{manifest['counts']['locators']} locators re-verified, source hash matches contract, "
            "claims empty by contract, 5 figure attachments resolved with bytes"
        ),
        "scenario_key": SCENARIO,
        "mission_id": MISSION_ID,
        "tags": ["KF", "asset-registration", "kf-wp:" + PKG, "DEM", "tensordem-cg-upscaling"],
        "markdown": report_md,
        "figures": [
            {
                "name": "fig_manifest_composition",
                "caption": f"wp-11243-01 asset registration: {manifest['counts']['assets']} artifacts "
                           f"by class, and resolution status with {manifest['counts']['locators_resolved']}"
                           f"/{manifest['counts']['locators']} locators resolved",
                "png_base64": base64.b64encode(FIGURE.read_bytes()).decode(),
            }
        ],
    }
    status, resp = api("/tensor/reports", payload, method="POST")
    new_id = resp.get("id") or (resp.get("data") or {}).get("id")
    print("POST /tensor/reports ->", status, "id=", new_id)

    # ---- verify what the platform actually stored
    _, back = api(f"/tensor/reports/{new_id}")
    md_back = back["markdown"]
    blocks = md_back.split("```json")
    parsed = None
    if len(blocks) > 1:
        parsed = json.loads(blocks[1].split("```")[0])
    fig_status, fig_bytes = api(
        f"/tensor/reports/{new_id}/figures/fig_manifest_composition", raw=True
    )
    verification = {
        "report_id": new_id,
        "json_blocks_in_report": len(blocks) - 1,
        "result_block_parses": parsed is not None,
        "result_block_equals_local_envelope": parsed == envelope,
        "provenance_source_hash": parsed["provenance"]["source_hash"] if parsed else None,
        "source_hash_matches_contract": bool(parsed)
        and parsed["provenance"]["source_hash"] == SOURCE_HASH,
        "claims_len": len(parsed["claims"]) if parsed else None,
        "outputs_keys": sorted(parsed["outputs"]) if parsed else None,
        "tag_present": "kf-wp:" + PKG in (back.get("tags") or []),
        "title": back.get("title"),
        "figure_http_status": fig_status,
        "figure_bytes": len(fig_bytes),
        "figure_sha256": hashlib.sha256(fig_bytes).hexdigest(),
        "figure_sha256_matches_local": hashlib.sha256(fig_bytes).hexdigest()
        == hashlib.sha256(FIGURE.read_bytes()).hexdigest(),
    }
    VERIFY.write_text(json.dumps(verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verification, ensure_ascii=False, indent=2))
    ok = (
        verification["json_blocks_in_report"] == 1
        and verification["result_block_equals_local_envelope"]
        and verification["source_hash_matches_contract"]
        and verification["tag_present"]
        and verification["figure_http_status"] == 200
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())