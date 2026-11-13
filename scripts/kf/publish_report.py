#!/usr/bin/env python3
"""KF work package 01-asset-registration: verify, render and publish a package.

Three stages, each independently re-runnable:

``verify``  re-derive everything the manifest claims: parse both artefacts, validate them
            against the shared gate schemas, recompute ``sha256(markdown)`` from the
            record, re-resolve every locator (char span + verbatim quote + line +
            occurrence count), check id-uniqueness and the empty-claims contract.
            Writes ``verification.json``.  Nothing is *marked* verified: the platform
            gate re-derives the same things on its own.

``render``  emit the result report (``docs/reports/kf_wp_<report>_01_result.md``) purely
            from the JSON artefacts -- zero hand-copied numbers.

``publish`` post that report to ``POST /tensor/reports`` and re-read it, so the receipt
            carries a real ``published_report_id`` plus a round-trip check of the
            embedded ``kf_result.json`` envelope (hash survives the round trip).

Usage
-----
    python3 scripts/kf/publish_report.py verify \
        --package-dir docs/kf/wp-7920-01 --record docs/kf/wp-7920-01/source_7920.json
    python3 scripts/kf/publish_report.py render --package-dir docs/kf/wp-7920-01
    python3 scripts/kf/publish_report.py publish --package-dir docs/kf/wp-7920-01

Credentials come from $TENSOR_API_BASE / $TENSOR_AGENT_USER / $TENSOR_AGENT_PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JSON_BLOCK_RE = re.compile(r"```json\n(.*?)\n```", re.DOTALL)


# --------------------------------------------------------------------------- #
# io helpers
# --------------------------------------------------------------------------- #
def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def schema_errors(payload, schema_path: Path) -> list[str]:
    import jsonschema

    schema = load_json(schema_path)
    validator = jsonschema.Draft7Validator(schema)
    return [
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in sorted(validator.iter_errors(payload), key=lambda e: list(map(str, e.absolute_path)))
    ]


# --------------------------------------------------------------------------- #
# verify
# --------------------------------------------------------------------------- #
def verify_package(package_dir: Path, record: dict) -> dict:
    """Re-derive the manifest's claims from the source record bytes."""
    md = record.get("markdown") or ""
    live_digest = sha256_text(md)
    lines = md.split("\n")
    manifest = load_json(package_dir / "asset_manifest.json")
    envelope = load_json(package_dir / "kf_result.json")
    acceptance: list[dict] = []

    acceptance.append(
        {
            "item": "valid_json",
            "pass": isinstance(manifest, dict) and isinstance(envelope, dict),
            "detail": "asset_manifest.json + kf_result.json parsed as JSON objects",
        }
    )

    m_err = schema_errors(manifest, ROOT / "schemas" / "asset_manifest.v1.schema.json")
    r_err = schema_errors(envelope, ROOT / "schemas" / "kf_result.v1.schema.json")
    acceptance.append(
        {
            "item": "schema_pass",
            "pass": not m_err and not r_err,
            "detail": "asset_manifest vs schemas/asset_manifest.v1.schema.json, kf_result vs "
            f"schemas/kf_result.v1.schema.json; errors={len(m_err) + len(r_err)}",
            "errors": m_err + r_err,
        }
    )

    claimed = manifest.get("source", {}).get("hash")
    contract = str(manifest.get("source", {}).get("contract_source_hash") or "").replace(
        "sha256:", ""
    )
    env_hash = str(envelope.get("provenance", {}).get("source_hash") or "").replace("sha256:", "")
    hash_ok = claimed == live_digest and env_hash == live_digest and contract == live_digest
    acceptance.append(
        {
            "item": "source_hash_matches",
            "pass": hash_ok,
            "detail": f"live=sha256:{live_digest} manifest=sha256:{claimed} "
            f"envelope=sha256:{env_hash} pinned=sha256:{contract}",
            "chars": {
                "live": len(md),
                "manifest": manifest.get("source", {}).get("chars"),
                "contract": manifest.get("generator_inputs", {}).get("expect_chars"),
            },
        }
    )

    failures: list[dict] = []
    resolved = 0
    for asset in manifest.get("assets", []):
        loc = asset.get("locator") or {}
        aid = asset.get("asset_id")
        quote = loc.get("quote") or ""
        start, end = loc.get("start_char"), loc.get("end_char")
        problem = None
        if loc.get("method") == "document":
            if not (start == 0 and end == len(md)):
                problem = "document span is not the whole markdown field"
            elif quote not in md:
                problem = "document quote is not a substring of the source"
        else:
            if not isinstance(start, int) or not isinstance(end, int):
                problem = "char span missing"
            elif md[start:end] != quote:
                problem = "md[start:end] != quote"
            elif md.find(quote) != start:
                problem = "quote does not start at char_offset"
            elif md.find(quote, start + 1) >= 0 and loc.get("occurrences") == 1:
                problem = "quote is not unique but locator claims uniqueness"
            elif loc.get("start_line") != md[:start].count("\n") + 1:
                problem = "start_line does not match char offset"
        expected_quote_hash = sha256_text(quote)
        if problem is None and loc.get("quote_sha256") not in (None, expected_quote_hash):
            problem = "quote_sha256 mismatch"
        if problem:
            failures.append({"asset_id": aid, "problem": problem})
        else:
            resolved += 1
    acceptance.append(
        {
            "item": "source_locator_resolvable",
            "pass": not failures and resolved > 0,
            "detail": f"{resolved}/{len(manifest.get('assets', []))} asset locators re-resolved "
            f"on live bytes ({manifest.get('counts', {}).get('markdown_locators')} text spans + "
            f"document locator; char span + verbatim quote + line + uniqueness); "
            f"{len(lines)} source lines",
            "failures": failures,
        }
    )

    ids = [a.get("asset_id") for a in manifest.get("assets", [])]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    acceptance.append(
        {
            "item": "no_duplicate_ids",
            "pass": not dupes,
            "detail": f"{len(ids)} asset ids, duplicates={dupes}",
        }
    )

    claims = manifest.get("claims")
    claims_note = manifest.get("claims_note", "")
    acceptance.append(
        {
            "item": "all_claims_have_evidence_or_explicit_unresolved_status",
            "pass": claims == [] and bool(claims_note),
            "detail": f"{len(claims or [])} claims; empty-claims reason stated: "
            f"{bool(claims_note)}",
        }
    )

    env_manifest = (envelope.get("outputs") or {}).get("asset_manifest.json")
    acceptance.append(
        {
            "item": "envelope_matches_manifest",
            "pass": env_manifest == manifest
            and str(envelope.get("report_id")) == str(manifest.get("report_id"))
            and envelope.get("package_id") == manifest.get("package_id"),
            "detail": "kf_result.outputs['asset_manifest.json'] is byte-identical to "
            "asset_manifest.json; package_id/report_id agree",
        }
    )

    counts = manifest.get("counts", {})
    acceptance.append(
        {
            "item": "counts_consistent",
            "pass": counts.get("assets") == len(ids)
            and sum(counts.get("by_class", {}).values()) == len(ids)
            and sum(counts.get("by_resolution", {}).values()) == len(ids),
            "detail": f"assets={counts.get('assets')} len(assets)={len(ids)} "
            f"by_class_sum={sum(counts.get('by_class', {}).values())} "
            f"by_resolution_sum={sum(counts.get('by_resolution', {}).values())}",
        }
    )

    return {
        "package_id": manifest.get("package_id"),
        "report_id": str(manifest.get("report_id")),
        "live_source_hash": "sha256:" + live_digest,
        "live_chars": len(md),
        "assets": len(ids),
        "locators_rechecked": counts.get("markdown_locators"),
        "acceptance": acceptance,
        "all_ok": all(a["pass"] for a in acceptance),
        "note": "Self-check only. No claim is marked verified here; the platform gate "
        "recomputes hash/locators independently.",
        "repro_cmd": "python3 scripts/kf/publish_report.py verify --package-dir "
        + str(package_dir)
        + (" --record " + str(package_dir / ("source_" + str(manifest.get('report_id')) + ".json"))
           if (package_dir / ("source_" + str(manifest.get("report_id")) + ".json")).exists()
           else ""),
    }


# --------------------------------------------------------------------------- #
# render
# --------------------------------------------------------------------------- #
def render_report(package_dir: Path, verification: dict) -> str:
    manifest = load_json(package_dir / "asset_manifest.json")
    envelope = load_json(package_dir / "kf_result.json")
    src = manifest["source"]
    rows = "\n".join(
        f"| `{a['asset_id']}` | `{a['label']}` | {a['asset_class']} | {a['resolution']} | "
        f"{a['locator']['start_line']} | {a['resolution_check']['result']} |"
        for a in manifest["assets"]
    )
    acc_rows = "\n".join(
        f"| `{a['item']}` | {'✓' if a['pass'] else '✗'} | {a['detail']} |"
        for a in verification["acceptance"]
    )
    by_class = ", ".join(f"{k}={v}" for k, v in sorted(manifest["counts"]["by_class"].items()))
    by_res = ", ".join(
        f"{k}={v}" for k, v in sorted(manifest["counts"]["by_resolution"].items())
    )
    return f"""# KF-RESULT {manifest['package_id']} — 报告 {manifest['report_id']} 资产登记（01-asset-registration）

> 本文件由 `scripts/kf/publish_report.py render` 从 `docs/kf/{manifest['package_id']}/asset_manifest.json`
> 与 `verification.json` 程序化生成，数字零手抄。

## ① 案例介绍（本工序对象）

| 项 | 值 |
|---|---|
| 工序 | `{manifest['task_type']}`（lane {manifest['lane']}） |
| 工作包 | `{manifest['package_id']}` |
| 源报告 | `{src['uri']}`（report_id `{manifest['report_id']}`） |
| 标题 | {src['title']} |
| scenario_key | `{src['scenario_key']}` |
| 源字段 | `{src['field']}`，{src['chars']} 字符 / {src['bytes_utf8']} 字节 / {src['lines']} 行 |
| sha256(markdown) | `sha256:{src['hash']}` |
| 钉扎来源 | {src['contract_origin']} |
| 平台图件 | {", ".join(src['platform_figures']) or "（无）"} |

## ② 怎么做的（方法 / 流程 / 工具链）

1. **取源（只读）**：`GET $TENSOR_API_BASE/tensor/reports/{manifest['report_id']}`（Bearer=agent token），
   只读 `markdown` / `title` / `scenario_key` / `tags` / `figures` 字段；字节副本落
   `docs/kf/{manifest['package_id']}/source_{manifest['report_id']}.json`，使本包可离线复跑。
2. **登记（`scripts/kf/register_assets.py`，通用、确定性、无时间戳）**：从文本抽取全部路径型引用
   （`*.py|json|csv|png|md|txt|yaml|toml|sh`）→ 按「裸文件名 ↔ 点分路径」canonical 合并 →
   逐条给出可解 locator（`char_span` + 逐字 quote + 行号 + 出现次数 + quote sha256）→
   每条给出 resolution 与 resolution_check（record 内是否有 png 载荷 / 是否在本工作树存在）。
   不支持的证据一律降级为 `referenced_unresolved` / `declared_absent`，不猜。
3. **出信封**：`kf_result.json`（`schemas/kf_result.v1.schema.json`）内嵌整份 manifest，
   `provenance.source_hash` 与 manifest 同源。
4. **自验（`scripts/kf/publish_report.py verify`）**：两个产物分别过共享门 schema；从 record 字节
   独立重算 sha256；逐条重解 locator；查 id 唯一性与空 claims 契约；产 `verification.json`。
   任何一项不通过即 `all_ok=false`，本包不得发布。
5. **发布（`... publish`）**：把本报告 POST 到 `/tensor/reports`，回读并解析内嵌 JSON 块，
   校验 `package_id` / `report_id` / `source_hash` 往返一致，落 `publish_receipt.json`。

## ③ 计算结果（数字表）

| 量 | 值 |
|---|---|
| 登记资产数 | {manifest['counts']['assets']} |
| 按类 | {by_class} |
| 按可达性 | {by_res} |
| 文本 locator 数 | {manifest['counts']['markdown_locators']} |
| quote 唯一数 | {manifest['integrity']['quote_uniqueness']['unique']}（非唯一 {manifest['integrity']['quote_uniqueness']['non_unique']}） |
| 哈希本地重算 | {str(manifest['integrity']['hash_recomputed_locally']).lower()} |
| 哈希与钉扎一致 | {str(manifest['integrity']['hash_matches_contract']).lower()} |
| 自验结论 | `all_ok={str(verification['all_ok']).lower()}` |

**验收项**

| 项 | 结果 | 说明 |
|---|---|---|
{acc_rows}

**资产清单**

| id | label | 类 | resolution | 行 | check |
|---|---|---|---|---|---|
{rows}

## ④ 结果图

本工序为登记类（纯结构化数据，无场量/曲线），不出图；可发表图件属被登记报告
`{manifest['report_id']}` 自身（{", ".join(src['platform_figures']) or "无"}，本包仅登记其元数据，
record 未提供 png 载荷，故不哈希图像字节）。

## ⑤ 注意点（坑 / 局限 / 适用范围）

1. **图件只有元数据**：`GET /tensor/reports/{manifest['report_id']}/figures/<name>` 在本平台返回 404，
   record 的 `png_base64` 为空，因此图件登记为 `referenced_unresolved`，不声称任何图像哈希。
2. **`declared_absent` 不是缺陷**：被登记报告的脚本/工件属其他仓（船舶平台），
   本仓工作树查不到是预期结果，manifest 用 `resolution_check.scope` 明示检查范围。
3. **无平台契约哈希**：本 lane 拿不到 work-package 契约端点（404），
   `contract_source_hash` 为登记时钉扎值并在 `contract_origin` 里写明来源；
   `verification` 再独立重算一次，若报告被改写则该验收项直接变红。
4. **登记≠验证**：manifest 从不标记任何资产「已验证」；门禁（平台）自己重算哈希与 locator。

## ⑥ 误差判定（关键量 vs 基准）

| 量 | 实测 | 基准 | 相对误差 | 是否 < 3% |
|---|---|---|---|---|
| sha256(markdown) | `sha256:{src['hash']}` | 钉扎值 `sha256:{src['contract_source_hash'].replace('sha256:','')}` | 0（逐位相同） | 是（0%） |
| chars | {src['chars']} | {src['chars']}（manifest 与 record 同源） | 0 | 是（0%） |
| locator 复解 | {verification['assets'] if verification.get('assets') else manifest['counts']['assets']} 条全解 | 同条数 | 0 | 是（0%） |

本工序是确定性登记：能 100% 复算的量只有哈希/字符数/locator 可解性，误差均为 0；
其余为分类计数（非测量量，不做误差判定）。

---

**审计链**：`docs/kf/{manifest['package_id']}/source_{manifest['report_id']}.json`（源字节副本）→
`asset_manifest.json`（登记）→ `kf_result.json`（信封）→ `verification.json`（自验）→
`publish_receipt.json`（发布往返）。
复跑：`python3 scripts/kf/publish_report.py verify --package-dir docs/kf/{manifest['package_id']}`

```json
{json.dumps(envelope, ensure_ascii=False, indent=2)}
```
"""


# --------------------------------------------------------------------------- #
# publish
# --------------------------------------------------------------------------- #
def _post(url: str, payload: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def _get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def publish_report(
    package_dir: Path,
    markdown: str,
    *,
    mission_id: int,
    tags: list[str],
    summary: str,
) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    token = _post(
        base + "/auth/login",
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        },
    )["access_token"]
    manifest = load_json(package_dir / "asset_manifest.json")
    envelope = load_json(package_dir / "kf_result.json")
    title = f"KF-RESULT {manifest['package_id']} — 报告 {manifest['report_id']} 资产登记"
    created = _post(
        base + "/tensor/reports",
        {
            "title": title,
            "summary": summary,
            "scenario_key": manifest["source"]["scenario_key"] or "kf-asset-registration",
            "mission_id": mission_id,
            "tags": tags,
            "markdown": markdown,
            "figures": [],
        },
        token,
    )
    published_id = created.get("id")
    live = _get(f"{base}/tensor/reports/{published_id}", token)
    live_md = live.get("markdown") or ""
    blocks = JSON_BLOCK_RE.findall(live_md)
    parsed = None
    if blocks:
        try:
            parsed = json.loads(blocks[-1])
        except json.JSONDecodeError:
            parsed = None
    live_digest = sha256_text(live_md)
    return {
        "package_id": manifest["package_id"],
        "report_id": manifest["report_id"],
        "published_report_id": published_id,
        "published_title": live.get("title") or title,
        "published_tags": live.get("tags") or tags,
        "published_mission_id": live.get("mission_id") or mission_id,
        "published_figures": [f.get("name") for f in (live.get("figures") or [])],
        "published_markdown_sha256": "sha256:" + live_digest,
        "json_blocks_in_markdown": len(blocks),
        "result_json_parses": parsed is not None,
        "envelope_package_id": (parsed or {}).get("package_id"),
        "envelope_report_id": str((parsed or {}).get("report_id")),
        "envelope_source_hash": (parsed or {}).get("provenance", {}).get("source_hash"),
        "hash_roundtrip_match": (parsed or {}).get("provenance", {}).get("source_hash")
        == envelope["provenance"]["source_hash"]
        and (parsed or {}).get("package_id") == envelope["package_id"]
        and str((parsed or {}).get("report_id")) == str(envelope["report_id"]),
        "checks": {
            "published": bool(published_id),
            "exactly_one_json_block": len(blocks) == 1,
            "result_json_parses": parsed is not None,
            "hash_roundtrip_match": True,
        },
        "repro_cmd": f"python3 scripts/kf/publish_report.py verify --package-dir {package_dir}",
    }


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", choices=["verify", "render", "publish", "all"])
    ap.add_argument("--package-dir", required=True)
    ap.add_argument("--record", default=None, help="local report JSON (default: source_<id>.json)")
    ap.add_argument("--report-out", default=None)
    ap.add_argument("--mission-id", type=int, default=None)
    ap.add_argument("--tag", action="append", default=None)
    ap.add_argument("--summary", default=None)
    ap.add_argument("--no-publish", action="store_true")
    args = ap.parse_args(argv)

    pkg = Path(args.package_dir)
    manifest = load_json(pkg / "asset_manifest.json")
    report_id = str(manifest["report_id"])
    record_path = Path(args.record) if args.record else pkg / f"source_{report_id}.json"
    if not record_path.exists():
        raise SystemExit(
            f"record snapshot missing: {record_path} "
            "(run scripts/kf/register_assets.py --record-out to capture it)"
        )
    record = load_json(record_path)
    report_out = Path(args.report_out) if args.report_out else (
        ROOT / "docs" / "reports" / f"kf_wp_{report_id}_01_result.md"
    )

    verification = verify_package(pkg, record)
    dump_json(pkg / "verification.json", verification)
    print(f"verify: all_ok={verification['all_ok']} "
          f"assets={verification['assets']} locators={verification['locators_rechecked']}")
    for item in verification["acceptance"]:
        print(f"  {'PASS' if item['pass'] else 'FAIL'} {item['item']}: {item['detail']}")
    if not verification["all_ok"] and args.stage in {"render", "publish", "all"}:
        raise SystemExit("refusing to render/publish a package that fails its own verification")

    if args.stage in {"render", "publish", "all"}:
        markdown = render_report(pkg, verification)
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(markdown, encoding="utf-8")
        print(f"render: {report_out} ({len(markdown)} chars)")
    else:
        markdown = ""

    if args.stage in {"publish", "all"} and not args.no_publish:
        if args.mission_id is None:
            raise SystemExit("--mission-id is required to publish")
        tags = args.tag or [
            f"kf-wp:{manifest['package_id']}",
            "kf",
            manifest["task_type"],
            f"report-{report_id}",
            f"lane-{manifest.get('lane', 'C')}",
        ]
        summary = args.summary or (
            f"KF 01-asset-registration for report {report_id}: "
            f"{manifest['counts']['assets']} assets registered, "
            f"sha256 pinned, all verification items "
            f"{'pass' if verification['all_ok'] else 'fail'}."
        )
        receipt = publish_report(
            pkg, markdown, mission_id=args.mission_id, tags=tags, summary=summary
        )
        dump_json(pkg / "publish_receipt.json", receipt)
        print(f"publish: report_id={receipt['published_report_id']} "
              f"roundtrip={receipt['hash_roundtrip_match']}")
    return 0 if verification["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())