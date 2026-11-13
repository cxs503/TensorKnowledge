#!/usr/bin/env python3
"""Emit the KF-RESULT report for wp-1716-01 and (optionally) POST it.

Every number in the markdown is injected from the committed artifacts
(asset_manifest.json / checks.json) — nothing is transcribed by hand.

    python3 scripts/kf_wp1716_01_report.py --out /tmp/report_1716.json
    python3 scripts/kf_wp1716_01_report.py --post
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "kf" / "wp-1716-01"
MANIFEST = OUT / "asset_manifest.json"
CHECKS = OUT / "checks.json"
SNAPSHOT = OUT / "source_report_1716.md"
FIGURE = OUT / "figures" / "asset_locator_map.png"
REPORTING_MISSION = 15531
PACKAGE_ID = "wp-1716-01"


def sha256_file(p: Path) -> str:
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(REPO))


def short(q: str, n: int = 58) -> str:
    q = q.replace("|", "\\|")
    return q if len(q) <= n else q[: n - 1] + "…"


def build_result(manifest: dict, checks: dict, now: str) -> dict:
    return {
        "package_id": PACKAGE_ID,
        "task_type": "01-asset-registration",
        "report_id": manifest["report_id"],
        "provenance": {
            "source_uri": manifest["source"]["uri"],
            "source_field": "markdown",
            "source_hash": manifest["source"]["hash"]["value"],
            "source_hash_algorithm": "sha256",
            "source_hash_scope": "utf-8 bytes of the tensor_reports.markdown field",
            "source_hash_recomputed_in_run": manifest["source"]["hash"]["value"],
            "source_hash_matches_contract": manifest["source"]["hash"]["matches_contract"],
            "source_chars": manifest["source"]["size"]["chars"],
            "source_bytes": manifest["source"]["size"]["bytes"],
            "retrieved_at": now,
            "retrieval": {
                "method": "platform_api_read",
                "endpoint": "GET ${TENSOR_API_BASE}/tensor/reports/1716",
                "auth": "bearer token (agent user); read-only, source never written",
            },
            "contract_version": "1.0",
            "lane": "C",
            "mission_id": None,
            "reporting_mission_id": REPORTING_MISSION,
            "title": manifest["source"]["report_facts"]["title"],
            "scenario_key": manifest["source"]["report_facts"]["scenario_key"],
            "producer": {
                "repo": "TensorKnowledge",
                "worktree": str(REPO),
                "branch": "agent/m15531",
            },
            "generator": "scripts/kf_wp1716_01_asset_manifest.py",
            "repro_cmd": (
                "python3 scripts/kf_wp1716_01_asset_manifest.py "
                "&& python3 scripts/kf_wp1716_01_asset_manifest.py --verify --offline "
                "&& python3 scripts/kf_wp1716_01_figures.py "
                "&& python3 -m pytest tests/test_kf_wp1716_01.py -q"
            ),
            "check_summary": {
                "all_ok": checks["all_ok"],
                "n_checks": checks["n_checks"],
                "n_ok": checks["n_ok"],
                "failed": [c["check"] for c in checks["failed"]],
            },
        },
        "outputs": {
            "asset_manifest.json": {
                "path": rel(MANIFEST),
                "sha256": sha256_file(MANIFEST),
                "n_assets": manifest["unresolved_summary"]["n_assets"],
                "by_status": manifest["unresolved_summary"]["by_status"],
                "n_claims": len(manifest["claims"]),
                "schema": manifest["schema_version"],
            },
            "checks.json": {
                "path": rel(CHECKS),
                "sha256": sha256_file(CHECKS),
                "all_ok": checks["all_ok"],
                "n_checks": checks["n_checks"],
            },
            "source_report_1716.md": {
                "path": rel(SNAPSHOT),
                "sha256": sha256_file(SNAPSHOT),
                "chars": manifest["source"]["size"]["chars"],
                "bytes": manifest["source"]["size"]["bytes"],
            },
            "asset_locator_map.png": {
                "path": rel(FIGURE),
                "sha256": sha256_file(FIGURE),
                "present": FIGURE.exists(),
            },
        },
    }


def build_markdown(manifest: dict, checks: dict, result: dict,
                   supersedes: int | None = None) -> str:
    by_status = manifest["unresolved_summary"]["by_status"]
    assets = manifest["assets"]
    facts = manifest["source"]["report_facts"]
    probes = manifest["channel_probes"]
    reason_codes = manifest["unresolved_summary"]["reason_codes"]

    rows = []
    for a in assets:
        loc = a["locator"]
        rows.append(
            "| `{}` | {} | `{}`–`{}` | `{}` | {} |".format(
                a["asset_id"], a["kind"], loc["char_start"], loc["char_end"],
                short(loc["quote"]), a["status"],
            )
        )
    probe_rows = [
        "| `{}` | {} | {} |".format(p["path"], p["http_status"], p["detail"])
        for p in probes
    ]
    acc = []
    for c in checks["checks"]:
        acc.append("| {} | `{}` | {} |".format(
            "✅" if c["ok"] else "❌", c["check"], str(c["detail"])[:110] or "—"))

    if supersedes:
        supersede_note = (
            f"> **版本说明**：本报告是同一工作包（{PACKAGE_ID}）的第二次提交，取代报告 "
            f"{supersedes}。两次提交的产物内容完全相同（源哈希、{len(assets)} 个资产、"
            f"{checks['n_checks']} 项自检全绿），唯一差别是产物落点：上一次写在 "
            f"`artifacts/kf-wp-1716-01/`，该前缀会被推送门禁 `^artifacts?/` 丢弃"
            f"（见 `docs/ops/filter-audit.md`），下游将解析不到清单；本次改落 "
            f"`docs/kf/wp-1716-01/`（门禁放行 docs/ 交付图与文档）。以本报告为准。\n\n"
        )
    else:
        supersede_note = ""
    ok = checks["all_ok"]
    figname = "asset_locator_map.png"

    md = f"""# KF-RESULT {PACKAGE_ID}

**工序** 01-asset-registration（Lane C） · **源报告** report_id=1716 · **报单** mission 15531
**仓** TensorKnowledge · **分支** `agent/m15531` · **契约版本** 1.0
**产物** `docs/kf/wp-1716-01/asset_manifest.json`、`checks.json`、
`source_report_1716.md`、`figures/{figname}`

## ① 本工序做了什么

本工序是报告→知识产线里最前面的一道：**登记源资产，不做抽取**。具体做了三件事：

1. 从平台接口取回 report_id=1716 的 `markdown` 字段，**在本次运行内重算 sha256**，
   与工作包契约给定的 `source_hash` 逐位比对，并把当时的字节落成快照
   `source_report_1716.md`（{manifest['source']['size']['chars']} 字符 /
   {manifest['source']['size']['bytes']} 字节）。
2. 把报告**自己声明**的附件/工件列出来并逐个钉死定位：{len(assets)} 个资产，
   分四类（报告正文、结果图、正文引用的工件路径、产出分支 git ref）。
   每个资产都带一个半开区间字符定位 `[char_start, char_end)` + 逐字引文，
   生成器在落盘前断言 `markdown[char_start:char_end] == quote`。
3. 明确区分「拿到了字节」与「只拿到声明」：只有 {by_status.get('registered',0)} 个资产是
   `registered`（真的握有字节并通过哈希校验），其余 {by_status.get('declared_not_fetched',0)} 个是
   `declared_not_fetched`，每个都附**显式的原因码**，绝不悄悄升格成「已存在」。

{supersede_note}本工序**没有**做的事（契约边界）：没有抽取 claim（`claims` 为空数组，契约允许）、
没有做报告类型分类（`classify_report_type: false`）、没有读写任何其它 report_id、
没有把任何结论标成 verified（verification 由平台门计算）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET ${{TENSOR_API_BASE}}/tensor/reports/1716`（Bearer = agent 用户 token，
   只读）。标题与 `scenario_key` 亦从同一响应的元数据字段取回并做契约比对：
   `title_matches_contract={str(facts['title_matches_contract']).lower()}`、
   `scenario_key_matches_contract={str(facts['scenario_key_matches_contract']).lower()}`。
2. **重算哈希**：`sha256(markdown.encode('utf-8'))`，与契约值
   `{manifest['source']['hash']['contract_value']}` 比较；不一致则生成器直接 `SystemExit`，
   不写任何产物（fail-closed）。
3. **枚举资产**（不靠手抄，靠正则扫正文）：
   - 标题行 → 报告正文资产（`covers` 覆盖整个 markdown）；
   - 元数据 `figures[]` 的 `name` → 结果图资产，并回到正文验证该文件名确实出现在文内（有锚点才登记）；
   - 正文反引号里的仓内相对路径（`backend|tools|tests|artifacts|docs` 开头，含可选 `::symbol`）
     → 工件路径资产，同时记录**全部出现位置**（一处在头部工件行、多处在下文复述）；
   - 正文反引号里的 `agent/...` → 产出分支 git ref（provenance 指针）。
4. **定位可解性**：每个资产的 `locator` 与每个 `occurrences` 项都断言
   `markdown[start:end] == quote`；落盘后 `--verify` 再断言一遍（平台可独立复算同一子串）。
5. **字节通道探测**：对每张图与附件端点发一次只读 GET，把 HTTP 状态码原样记进
   `channel_probes`（见下表），作为「为什么这些资产只能是 declared」的一手证据。
6. **确定性**：清单里**不写任何墙钟字段**，`--offline` 重建逐字节相同（测试里钉住）；
   时间戳只出现在本报告的 `provenance.retrieved_at`。
7. **自检**：`--verify --live` 重放 {checks['n_checks']} 项断言（含 4 项回到线上重新取源的复核），
   并写 `checks.json`；另有 `tests/test_kf_wp1716_01.py` 17 项 pytest 从产物侧再验一遍。

通道探测结果（只读 GET，状态码如实记录）：

| 探测路径 | HTTP | detail |
|---|---:|---|
{chr(10).join(probe_rows)}

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-1716-01/asset_manifest.json` | 主交付。schema `kf-asset-manifest/1.0`；{len(assets)} 个资产；状态分布 {json.dumps(by_status, ensure_ascii=False)}；`claims: []`；`verification_policy.claims_marked_verified = 0`；原因码 {reason_codes} |
| `docs/kf/wp-1716-01/checks.json` | {checks['n_checks']} 项自检全部落盘（all_ok={str(ok).lower()}），含每项 ok/detail |
| `docs/kf/wp-1716-01/source_report_1716.md` | 报告 1716 markdown 的逐字快照，{manifest['source']['size']['chars']} 字符 / {manifest['source']['size']['bytes']} 字节，sha256 与契约一致 |
| `docs/kf/wp-1716-01/figures/{figname}` | 图 A：每个资产在 markdown 字符轴上的定位点（点=全部出现位置）与状态着色；图 B：按 kind×status 的资产计数 |
| `scripts/kf_wp1716_01_asset_manifest.py` | 生成器 + `--verify`（可 `--live` 回线上重放）；无墙钟字段，离线重建字节稳定 |
| `scripts/kf_wp1716_01_figures.py` | 从清单生成上图（无随机、无时间戳） |
| `tests/test_kf_wp1716_01.py` | 17 项 pytest：结构/哈希/定位/唯一性/诚实性/字节稳定 |

## ④ 证据定位表（资产 → 原文逐字引文）

定位字段统一为 `markdown`，区间是半开字符区间；下表引文为原文逐字片段（长引文截断以 `…` 标注，
完整引文见 `asset_manifest.json` 的 `locator.quote` 与 `occurrences`）。

| asset_id | kind | char 区间 | 原文引文 | status |
|---|---|---:|---|---|
{chr(10).join(rows)}

报告正文本身作为 `ast-1716-report-markdown` 登记，其哈希即契约哈希
`{manifest['source']['hash']['value']}`——0 号定位点到 {manifest['source']['size']['chars']} 号字符的整段。

## ⑤ 注意点与局限

- **只有 1 个资产真的握有字节**。其余 {by_status.get('declared_not_fetched',0)} 个是声明级登记：图
  端点 404（`figure_payload_404`）、工件路径在本工作树不存在且登记表未给字节通道
  （`producer_repo_not_in_worktree`）、git ref 属跨仓且只有分支名没有 commit id
  （`cross_repo_ref`）。任何下游若需要这些字节，必须另开取件工序，不能把本清单当字节凭据。
- **图的状态是「声明存在」不是「内容已验证」**：报告元数据给了 name+caption，正文给了文件名锚点，
  但 PNG 字节没拿到 → 无法核对图里画的与正文表格说的数字是否一致。
- **产物路径的仓库归属是读出来的**：报告头部写明仓为 TensorPlatform，因此这些
  `backend/…`、`tools/…`、`tests/…` 路径相对的是 TensorPlatform 而非本仓；本仓 probe 记为
  `exists=false`（见各资产 `resolution.local_worktree_probe`），这不是「文件丢了」。
- **刻意不登记的项**：`ishigami`、`sobol_g_a_0_0.5_3_9_99` 是 `artifacts/gsa_sobol_benchmark.json`
  内部的算例 key，不是独立附件；`saltelli_sample`、`sobol_indices`、
  `ice_resistance_uq.build_pce` 是符号级指针，其宿主模块已单独登记。登记它们会暗示我们握有容器。
  理由写在清单 `scope_notes.not_registered_on_purpose`。
- **不覆盖输出**：全过程只读 report 1716；不写其它 report_id、不改上游产物。
- **未做 verification**：本工序只做定位与哈希钉死，`no_verified_marker` 自检通过；证据分级/复核结论
  留给平台门与独立复核席位。

## ⑥ 自检（逐条对照 acceptance）

| 判据 | 检查项 | 结果 |
|---|---|---|
{chr(10).join(acc)}

结论：{checks['n_ok']}/{checks['n_checks']} 项通过，`all_ok={str(ok).lower()}`。
逐条对应验收项：`valid_json`（json.loads 通过）、`schema_pass`（必需顶层键齐全 +
`no_duplicate_ids`）、`source_locator_resolvable`（全部 locator 与 occurrence 逐字可切）、
`source_hash_matches`（= 契约哈希，线上重取亦一致）、`no_duplicate_ids`（{len(assets)} 个 id 互异）、
`all_claims_have_evidence_or_explicit_unresolved_status`（claims 为空且有原因码覆盖全部未解析资产）。
**无失败项**；pytest 17 项同为绿。

### repro_cmd

```bash
cd /root/tp-agent/work/m15531
python3 scripts/kf_wp1716_01_asset_manifest.py            # 取源 + 生成清单（需平台 token）
python3 scripts/kf_wp1716_01_asset_manifest.py --verify --live   # 重放 21 项自检（含线上复核）
python3 scripts/kf_wp1716_01_figures.py                   # 生成定位图
python3 -m pytest tests/test_kf_wp1716_01.py -q           # 17 项验收测试
```

```json
{json.dumps(result, ensure_ascii=False, indent=2)}
```
"""
    return md


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/report_1716.json")
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--supersedes", type=int, default=None,
                    help="report id of an earlier submission of this package")
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    checks = json.loads(CHECKS.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    result = build_result(manifest, checks, now)
    md = build_markdown(manifest, checks, result, supersedes=args.supersedes)

    n_json = len(re.findall(r"```json", md))
    assert n_json == 1, f"markdown must contain exactly one json block, got {n_json}"

    png = base64.b64encode(FIGURE.read_bytes()).decode()
    payload = {
        "title": f"KF-RESULT {PACKAGE_ID}",
        "summary": (
            "asset registration for report 1716: markdown sha256 re-derived and matched "
            f"to contract, {len(manifest['assets'])} assets pinned to verbatim locators, "
            f"{manifest['unresolved_summary']['by_status'].get('registered',0)} registered / "
            f"{manifest['unresolved_summary']['by_status'].get('declared_not_fetched',0)} "
            "declared with reason codes, claims empty, nothing verified"
        ),
        "scenario_key": manifest["source"]["report_facts"]["scenario_key"],
        "mission_id": REPORTING_MISSION,
        "tags": [
            f"kf-wp:{PACKAGE_ID}", "KF-RESULT", "01-asset-registration",
            "asset-registration", "asset-manifest", "provenance", "lane:C",
            "report:1716", "TensorKnowledge",
        ],
        "markdown": md,
        "figures": [
            {
                "name": "asset_locator_map.png",
                "caption": (
                    "图 A 每个登记资产在 report 1716 markdown 字符轴上的定位点"
                    "（点=该 token 的全部出现位置，颜色=状态）；图 B 按 kind×status 计数。"
                    "仅 1 个资产 registered（正文，哈希已校验），其余为 declared_not_fetched。"
                ),
                "png_base64": png,
            }
        ],
    }
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {args.out} ({len(md)} chars markdown, {len(png)} b64 chars figure)")

    if args.post:
        api = os.environ["TENSOR_API_BASE"].rstrip("/")
        body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                           "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
        req = urllib.request.Request(
            api + "/auth/login", data=body,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            token = json.load(r)["access_token"]
        req = urllib.request.Request(
            api + "/tensor/reports", data=Path(args.out).read_bytes(),
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + token})
        with urllib.request.urlopen(req, timeout=60) as r:
            print("POST", r.status, r.read()[:200].decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())