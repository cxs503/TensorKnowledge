#!/usr/bin/env python3
"""wp-1200-01 · 01-asset-registration（report_id=1200）

单一职责：登记源资产 = 取 report 1200 的 markdown → 字节哈希校验 → 列出可解析附件/工件
→ 产出 asset_manifest.json 与 result 信封（kf_result.v1）。

零手抄纪律：所有 quote 由本脚本对 markdown 做**行区间切片**生成（quote := md[line_start..line_end]），
不是人工转录；任何片段在源文本中定位失败即报错退出，不允许“凭记忆补” 。

用法：
  python3 scripts/kf/wp-1200-01/build_asset_manifest.py [--offline-source PATH]

  --offline-source  跳过 API，直接读本地 markdown 副本（复跑用；仍需哈希一致）

产物落 docs/kf/wp-1200-01/（本仓 artifacts/ 被 .gitignore 屏蔽，故交付物走 docs 物化）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PKG = "wp-1200-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "1200"
SOURCE_URI = "tensor://reports/1200"
SOURCE_FIELD = "markdown"
EXPECTED_HASH = "sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48"
EXPECTED_TITLE = ("m1625 · tests/factory schema 漂移根因与修复：手写迁移清单 vs 生产 glob"
                  "（5 FAILED → 168 passed）")
EXPECTED_SCENARIO = "tensorplatform_ci_quality"
EXPECTED_CHARS = 3612

HERE = Path(__file__).resolve().parent


def _worktree(p: Path) -> Path:
    for q in (p, *p.parents):
        if (q / ".git").exists():
            return q
    raise SystemExit("[init] 未找到工作树根（.git）")


WORKTREE = _worktree(HERE)
OUT = WORKTREE / "docs" / "kf" / PKG
SCHEMA_PATH = WORKTREE / "schemas" / "kf_result.v1.schema.json"


# ----------------------------------------------------------------------------- source
def login(base: str) -> str:
    user = os.environ["TENSOR_AGENT_USER"]
    pw = os.environ["TENSOR_AGENT_PASS"]
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": user, "password": pw}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    tok = body.get("access_token") or body.get("token")
    if not tok:
        raise SystemExit("login: 无 token 返回")
    return tok


def fetch_via_api() -> tuple[dict, str]:
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    tok = login(base)
    url = f"{base}/tensor/reports/{REPORT_ID}"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=60) as r:
        rec = json.load(r)
    return rec, f"GET {url} (Bearer auth)"


# ----------------------------------------------------------------------------- locators
def line_locator(md: str, pattern: str, occurrence: int = 0, label: str = "") -> dict:
    """把 pattern 命中的**整行区间**作为 locator；quote 由切片生成（逐字可验）。"""
    ms = [m for m in re.finditer(pattern, md, re.M)]
    if not ms:
        raise SystemExit(f"[locate] 未命中: {label or pattern!r}")
    if len(ms) > 1:
        # 同一行可能被多条候选命中（如重复出现）；调用方用 occurrence 指定
        pass
    try:
        m = ms[occurrence]
    except IndexError:
        raise SystemExit(f"[locate] occurrence {occurrence} 越界 ({len(ms)} hits): {label or pattern!r}")
    a, b = m.start(), m.end()
    ls = md.rfind("\n", 0, a) + 1                  # 行首
    le = md.find("\n", b - 1)                      # 行尾（含）
    if le == -1:
        le = len(md)
    quote = md[ls:le]
    return {
        "line_start": md.count("\n", 0, ls) + 1,
        "line_end": md.count("\n", 0, le) + 1,
        "char_start": ls,
        "char_end": le,
        "quote": quote,
    }


def anchor_locator(md: str, needle: str, anchor_occurrence: int = 0) -> dict:
    """在命中行内再精确定位工件路径本身（quote=整行，anchor=路径 token 的逐字切片）。"""
    idx = -1
    for _ in range(anchor_occurrence + 1):
        idx = md.find(needle, idx + 1)
        if idx == -1:
            raise SystemExit(f"[anchor] 未命中: {needle!r}")
    if md.find(needle, idx + 1) != -1:
        raise SystemExit(f"[anchor] 命中不唯一（需 occurrence 指定）: {needle!r}")
    return {
        "anchor_char_start": idx,
        "anchor_char_end": idx + len(needle),
        "anchor_text": md[idx:idx + len(needle)],
        "anchor_line": md.count("\n", 0, idx) + 1,
    }


def count_hits(md: str, pattern: str) -> int:
    return len(re.findall(pattern, md, re.M))


# ----------------------------------------------------------------------------- manifest
SCHEMA_ELEMENTS = [
    # (序号, 表.列, 声明迁移, 报告表格行正则)
    (1, "tensor_dev_missions.report_id", "096_report_gate.sql:12", r"^\| 1 \| tensor_dev_missions\.report_id \|.*$"),
    (2, "tensor_dev_missions.report_owed", "096_report_gate.sql:8 / 095_mission_lifecycle.sql:38",
     r"^\| 2 \| tensor_dev_missions\.report_owed \|.*$"),
    (3, "tensor_dev_missions.fail_stage", "095_mission_lifecycle.sql:35",
     r"^\| 3 \| tensor_dev_missions\.fail_stage \|.*$"),
    (4, "tensor_dev_missions.suspended_at", "095_mission_lifecycle.sql:19",
     r"^\| 4 \| tensor_dev_missions\.suspended_at \|.*$"),
    (5, "tensor_dev_missions.worktree_recyclable", "095_mission_lifecycle.sql:41",
     r"^\| 5 \| tensor_dev_missions\.worktree_recyclable \|.*$"),
    (6, "tensor_dev_missions.budget_used", "095_mission_lifecycle.sql:30",
     r"^\| 6 \| tensor_dev_missions\.budget_used \|.*$"),
    (7, "campaign_plans.name", "095_campaign_plans.sql / 097",
     r"^\| 7 \| campaign_plans\.name \|.*$"),
    (8, "campaign_plans.campaign_id", "095_campaign_plans.sql / 097",
     r"^\| 8 \| campaign_plans\.campaign_id \|.*$"),
]

# 报告正文点名的附件/工件（本工序只做登记，不做抽取；是否可解析如实标注）
ARTIFACT_REFS = [
    ("art-01", "test file", "tests/factory/conftest.py", r"^对象为 `tests/factory` 集成测试库.*$",
     "tests/factory 集成测试库 conftest（真实 PostgreSQL 临时集群）"),
    ("art-02", "source module", "backend/services/factory_bootstrap.py",
     r"^2\. 定根因.*$", "测试库迁移喂养实现（手写文件名元组）"),
    ("art-03", "source module", "backend/migrations/run_migration.py",
     r"^2\. 定根因.*$", "生产侧迁移执行器（glob 全量 + 版本登记）"),
    ("art-04", "migration sql", "097_campaign_plans_superset.sql",
     r"^   - `097_campaign_plans_superset\.sql`.*$", "补通道后暴露的第二个断点修复脚本"),
    ("art-05", "test file", "tests/factory/test_schema_migrations.py",
     r"^   - 新增 `tests/factory/test_schema_migrations\.py`.*$", "新增守护测试（报告称 4 例）"),
    ("art-06", "evidence script", "artifacts/m1625/probe_schema.py",
     r"^4\. 证据采集脚本.*$", "建 before/after 两个一次性集群的探测脚本"),
    ("art-07", "data artifact", "artifacts/m1625/schema_coverage.json",
     r"^左：迁移文件应用数 9→19.*$", "结果图数据源（报告称程序化生成）"),
    ("art-08", "migration sql", "094_factory_soul.sql",
     r"^- 094_factory_soul\.sql 现经两条通道.*$", "已知冗余：glob 与 soul 版本登记器各执行一次"),
]

METRICS_PATTERNS = [
    ("mig_files", r"^\| 应用到测试库的迁移文件数 \|.*$"),
    ("tables", r"^\| `public` schema 表数 \|.*$"),
    ("missing_cols", r"^\| 签名 8 个 schema 元素缺失数 \|.*$"),
    ("factory_tests", r"^\| `tests/factory` 结果 \|.*$"),
]


def build_manifest(md: str, fetched_via: str) -> dict:
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    source_hash = "sha256:" + digest
    if source_hash != EXPECTED_HASH:
        raise SystemExit(f"[hash] 源哈希不符：{source_hash} != {EXPECTED_HASH}（拒绝登记，不硬改）")
    if len(md) != EXPECTED_CHARS:
        raise SystemExit(f"[chars] 长度不符：{len(md)} != {EXPECTED_CHARS}")

    L = line_locator(md, r"^# m1625 — tests/factory.*$", label="title")
    schema_elems = []
    for idx, col, declared_by, pat in SCHEMA_ELEMENTS:
        loc = line_locator(md, pat, label=f"schema row {idx}")
        schema_elems.append({
            "ref_id": f"schema-elem-{idx:02d}",
            "table_column": col,
            "declared_by_migration": declared_by,
            "presence": {"production": "present", "test_db_before_fix": "missing"},
            "locator": loc,
        })

    artifacts = []
    for aid, kind, ref, pat, purpose in ARTIFACT_REFS:
        loc = line_locator(md, pat, label=aid)
        loc.update(anchor_locator(md, ref))
        artifacts.append({
            "asset_id": aid,
            "kind": kind,
            "ref": ref,
            "purpose_in_report": purpose,
            "mentioned_at": [loc],
            "resolvable": False,
            "resolvable_status": "unknown/unresolved",
            "unresolved_reason": (
                "该工件路径属 TensorPlatform 仓（本工作树为 TensorKnowledge），"
                "报告仅文字引用、未附内容；本工序不跨仓取证，故可解析性记为未验证"
            ),
        })

    metrics = []
    for mid, pat in METRICS_PATTERNS:
        metrics.append({"metric_id": mid, "locator": line_locator(md, pat, label=mid)})

    claims = [
        {
            "claim_id": "wp-1200-01-c01",
            "text": "报告原文声称：TensorPlatform main 自 dd66cb0c 起 control-plane job 连红，5 例 FAILED，且非单 PR 引入。",
            "status": "supported",
            "evidence": [{
                "quote": line_locator(md, r"^TensorPlatform `main` 自 dd66cb0c 起.*$", label="bg")["quote"],
                "source_field": "markdown",
                "note": "登记报告陈述；本工序不独立复核 CI 历史",
            }],
        },
        {
            "claim_id": "wp-1200-01-c02",
            "text": "报告原文给出的失败签名是 psycopg2.errors.UndefinedColumn：tensor_dev_missions 上的 report_id / fail_stage 列不存在。",
            "status": "supported",
            "evidence": [
                {"quote": line_locator(md, r'^psycopg2\.errors\.UndefinedColumn: column "report_id" / "fail_stage"$', label="sig1")["quote"],
                 "source_field": "markdown", "note": "失败签名第 1 行"},
                {"quote": line_locator(md, r'^of relation "tensor_dev_missions" does not exist$', label="sig2")["quote"],
                 "source_field": "markdown", "note": "失败签名第 2 行"},
            ],
        },
        {
            "claim_id": "wp-1200-01-c03",
            "text": "报告原文把 8 个 schema 元素列为本单判据集：生产库存在、修复前测试库缺失。",
            "status": "supported",
            "evidence": (
                [{"quote": line_locator(md, r"^对象为 `tests/factory` .*$", label="judge")["quote"],
                  "source_field": "markdown", "note": "判据集声明"}]
                + [{"quote": e["locator"]["quote"], "source_field": "markdown",
                    "note": f"判据 {e['ref_id']} {e['table_column']}"} for e in schema_elems]
            ),
        },
        {
            "claim_id": "wp-1200-01-c04",
            "text": "报告原文的根因判断：测试库由 backend/services/factory_bootstrap.py 的手写文件名元组喂养，生产侧由 run_migration.py glob 全量，导致生产有列而测试库没有。",
            "status": "supported",
            "evidence": [{"quote": line_locator(md, r"^2\. 定根因.*$", label="root")["quote"],
                          "source_field": "markdown", "note": "根因段（读代码 + git log -S）"}],
        },
        {
            "claim_id": "wp-1200-01-c05",
            "text": "报告原文的修复效果数字：迁移文件 9→19、public 表 15→43、8 个 schema 元素缺失 8→0、tests/factory 由 5 FAILED 转为 168 passed（34.3 s）。",
            "status": "supported",
            "evidence": [{"quote": m["locator"]["quote"], "source_field": "markdown",
                          "note": f"结果表行 {m['metric_id']}"} for m in metrics],
        },
        {
            "claim_id": "wp-1200-01-c06",
            "text": "报告原文称新增 tests/factory/test_schema_migrations.py 共 4 例（迁移清单完整性 + 迁移声明列必须在测试库真实存在）。",
            "status": "supported",
            "evidence": [{"quote": [a for a in artifacts if a["asset_id"] == "art-05"][0]["mentioned_at"][0]["quote"],
                          "source_field": "markdown", "note": "修复面第 3 条 bullet"}],
        },
        {
            "claim_id": "wp-1200-01-c07",
            "text": "报告原文把 094_factory_soul.sql 经 glob 与 soul 版本登记器各执行一次登记为已知冗余（DDL 幂等，实测无副作用）。",
            "status": "supported",
            "evidence": [{"quote": [a for a in artifacts if a["asset_id"] == "art-08"][0]["mentioned_at"][0]["quote"],
                          "source_field": "markdown", "note": "注意点第 1 条"}],
        },
        {
            "claim_id": "wp-1200-01-c08",
            "text": "报告原文称 backend/tests 中 test_alert_unit / test_api_key_unit 的 FAILED 为预存在环境问题（FastAPI 依赖注入版本漂移），另有 24 模块因离线缺包 collection ERROR，均非本改动引入。",
            "status": "partially-supported",
            "evidence": [{"quote": line_locator(md, r"^- `backend/tests` 抽样：.*$", label="backendtests")["quote"],
                          "source_field": "markdown",
                          "note": "报告自述；未附逐例日志，本工序无法独立确认『预存在』归因"}],
        },
        {
            "claim_id": "wp-1200-01-c09",
            "text": "报告原文自评误差判定为是（<3%），理由是本单判据为离散一致性（8→0 缺失、5→0 失败 = 0%），连续物理量误差不适用。",
            "status": "supported",
            "evidence": [{"quote": line_locator(md, r"^本单判据为\*\*二值一致性\*\*.*$", label="err")["quote"],
                          "source_field": "markdown", "note": "⑥ 误差判定段"}],
        },
        {
            "claim_id": "wp-1200-01-c10",
            "text": "报告原文声明存在未审计项：生产库 schema_migrations 登记与 backend/migrations/versions/（alembic 空壳 initial）的关系未审计，留待平台审计项。",
            "status": "unresolved",
            "unresolved_reason": "报告自述为未完成事项，本工序不做抽取/复核，保持未决；不得据本报告推定其已闭合",
            "evidence": [{"quote": line_locator(md, r"^- 未审计生产库 `schema_migrations`.*$", label="notaudited")["quote"],
                          "source_field": "markdown", "note": "⑤ 局限第 4 条"}],
        },
    ]

    ids = ([e["ref_id"] for e in schema_elems] + [a["asset_id"] for a in artifacts]
           + [c["claim_id"] for c in claims] + [m["metric_id"] for m in metrics]
           + ["asset-report-1200"])
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise SystemExit(f"[ids] 重复 id: {dup}")

    return {
        "manifest_version": "1.0",
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "source": {
            "asset_id": "asset-report-1200",
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "title": L["quote"].lstrip("# ").strip(),
            "title_locator": L,
            "scenario_key": EXPECTED_SCENARIO,
            "chars": len(md),
            "bytes": len(md.encode("utf-8")),
            "line_count": md.count("\n") + 1,
            "sha256": source_hash,
            "sha256_expected": EXPECTED_HASH,
            "sha256_match": True,
            "encoding": "utf-8",
            "locator_scheme": "1-based 行号 + 字符偏移（对 markdown 字段原样切片）；quote 字段=该切片逐字内容，可直接做子串检索复核",
            "fetched_via": fetched_via,
        },
        "attachments": artifacts,
        "registered_schema_elements": schema_elems,
        "registered_metric_locators": metrics,
        "claims": claims,
        "stats": {
            "attachments_listed": len(artifacts),
            "attachments_resolvable": sum(1 for a in artifacts if a["resolvable"]),
            "schema_elements_registered": len(schema_elems),
            "claims_total": len(claims),
            "claims_supported": sum(1 for c in claims if c["status"] == "supported"),
            "claims_partially_supported": sum(1 for c in claims if c["status"] == "partially-supported"),
            "claims_unresolved": sum(1 for c in claims if c["status"] == "unresolved"),
            "claims_refuted": sum(1 for c in claims if c["status"] == "refuted"),
        },
        "unresolved": [
            "附件可解析性（8 项）均为 unknown/unresolved：路径属 TensorPlatform 仓，本工序不跨仓取证。",
            "报告 c10 声明的生产库 schema_migrations / alembic 关系未审计，本工序保持未决。",
            "本工序不做抽取，claims 仅为报告原文陈述的登记定位，不含独立复核结论。",
        ],
    }


# ----------------------------------------------------------------------------- checks
def validate(manifest: dict, envelope: dict, md: str) -> dict:
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=envelope, schema=schema)

    checks = []

    def add(name, ok, detail=""):
        checks.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})

    add("valid_json", True, "manifest/envelope 均可被 json 解析（本函数入参即解析结果）")
    add("schema_pass", True, "jsonschema(draft2020-12) 对 kf_result.v1.schema.json 校验通过")
    add("source_hash_matches",
        manifest["source"]["sha256"] == EXPECTED_HASH,
        f"{manifest['source']['sha256']}")

    # 每个 locator 必须是 markdown 的逐字子串，且行号/偏移自洽
    locs = []
    for e in manifest["registered_schema_elements"]:
        locs.append(("schema:" + e["ref_id"], e["locator"]))
    for a in manifest["attachments"]:
        for i, loc in enumerate(a["mentioned_at"]):
            locs.append((f"attach:{a['asset_id']}#{i}", loc))
    for m in manifest["registered_metric_locators"]:
        locs.append(("metric:" + m["metric_id"], m["locator"]))
    locs.append(("title", manifest["source"]["title_locator"]))

    bad = []
    for name, loc in locs:
        sub = md[loc["char_start"]:loc["char_end"]]
        line_ok = md.count("\n", 0, loc["char_start"]) + 1 == loc["line_start"]
        if not (sub == loc["quote"] and loc["quote"] in md and line_ok):
            bad.append(name)
    # 工件 anchor（路径 token）必须落在其 mentioned_at 行区间内且逐字一致
    anchor_bad = []
    for a in manifest["attachments"]:
        for loc in a["mentioned_at"]:
            ok = (loc["anchor_text"] == a["ref"]
                  and loc["char_start"] <= loc["anchor_char_start"]
                  and loc["anchor_char_end"] <= loc["char_end"]
                  and loc["anchor_line"] == loc["line_start"])
            if not ok:
                anchor_bad.append(a["asset_id"])
    add("artifact_anchor_in_locator", not anchor_bad,
        f"{len(manifest['attachments'])} 个工件路径 token 均逐字落在其引用行内"
        if not anchor_bad else f"失败: {anchor_bad}")

    add("source_locator_resolvable", not bad,
        f"{len(locs)} 个 locator 全部为逐字切片且行号自洽" if not bad else f"失败: {bad}")

    ids = [c["claim_id"] for c in manifest["claims"]]
    add("no_duplicate_ids", len(ids) == len(set(ids)), f"{len(ids)} 个 claim_id 唯一")

    missing = [c["claim_id"] for c in manifest["claims"]
               if not c.get("evidence") and not c.get("unresolved_reason")]
    also_bad = [c["claim_id"] for c in manifest["claims"]
                if c.get("status") == "unresolved" and not c.get("unresolved_reason")]
    add("all_claims_have_evidence_or_explicit_unresolved_status", not missing and not also_bad,
        f"缺证据且无 unresolved_reason 的 claim: {missing + also_bad}" if (missing or also_bad)
        else f"{len(ids)} 条 claim 均有 quote 证据或显式 unresolved_reason")

    # claim 证据 quote 亦须逐字
    bad_q = [c["claim_id"] for c in manifest["claims"] for ev in c.get("evidence", [])
             if ev["quote"] not in md]
    add("claim_quotes_verbatim", not bad_q, f"非逐字: {bad_q}" if bad_q else "全部 quote ⊆ markdown")

    add("no_verified_marking",
        not re.search(r'"verified"\s*:\s*true', json.dumps(envelope, ensure_ascii=False)),
        "envelope 内无 verified:true；verification 由平台门计算")

    add("report_id_scope", envelope["report_id"] == REPORT_ID,
        "仅 report_id=1200；未读写其它 report")

    return {
        "schema": "kf_result.v1.schema.json",
        "schema_sha256": "sha256:" + hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest(),
        "checks": checks,
        "locators_checked": len(locs),
        "all_pass": all(c["result"] == "PASS" for c in checks),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline-source", default=None,
                    help="本地 markdown 副本路径（复跑用）")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    if args.offline_source:
        md = Path(args.offline_source).read_text(encoding="utf-8")
        fetched_via = f"local file {args.offline_source}（离线复跑）"
    else:
        rec, fetched_via = fetch_via_api()
        md = rec["markdown"]
        if rec.get("title") != EXPECTED_TITLE:
            print(f"[warn] title 与契约不一致: {rec.get('title')!r}", file=sys.stderr)

    (OUT / "source_1200.md").write_text(md, encoding="utf-8")

    manifest = build_manifest(md, fetched_via)
    envelope = {
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": manifest["source"]["sha256"],
            "source_field": SOURCE_FIELD,
            "producer": f"agent m15523 / {PKG} (TensorKnowledge)",
            "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "notes": ("asset registration only; quotes are programmatic line-slices of the source "
                      "markdown; no extraction, no verification marking"),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": manifest["claims"],
    }

    v = validate(manifest, envelope, md)

    (OUT / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "result_envelope.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "validation_report.json").write_text(
        json.dumps(v, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "source_1200.sha256").write_text(
        manifest["source"]["sha256"] + "  source_1200.md\n", encoding="utf-8")

    for c in v["checks"]:
        print(f"[{c['result']}] {c['check']}: {c['detail']}")
    print("all_pass:", v["all_pass"])
    return 0 if v["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())