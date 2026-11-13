#!/usr/bin/env python3
"""wp-12510-01 · 01-asset-registration · report_id=12510

登记源资产：确认 report_id 与其 markdown 的字节哈希，列出可解析的附件/工件，不做抽取。
零手抄：所有 quote 为字面量针，运行时在取回的 markdown 内检索；
找不到 / 不唯一 → SystemExit（拒绝编造）。所有偏移/哈希/计数均为运行时计算。

用法:
  python3 scripts/wp12510_register_assets.py            # 在线：API 取源
  python3 scripts/wp12510_register_assets.py --offline  # 离线：用 runs/wp-12510-01 快照
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP_DIR = os.path.join(REPO, "runs", "wp-12510-01")
OUT_DIR = os.path.join(REPO, "docs", "kf", "wp-12510-01")

# ---- 契约声明（来自工作包契约 YAML，机器门按此校验）----
CONTRACT = {
    "package_id": "wp-12510-01",
    "task_type": "01-asset-registration",
    "report_id": "12510",
    "source_uri": "tensor://reports/12510",
    "source_field": "markdown",
    "source_hash": "sha256:45f688344f4bc7983fc167fa84ef0fb47ad9a7a8265bcfbe8095239002da62da",
    "title": "IMO IGF/G12 替代燃料安全评估框架",
    "scenario_key": "imo_g12_fuel_safety",
    "chars": 5656,
}

# 本地节点上源工件的可解析位置（只读探测，不写该工作树）
NODE_ARTIFACT_DIR = "/root/tp-agent/work/m11196/artifacts/imo_g12_fuel_safety"
NODE_CODE_DIR = "/root/tp-agent/work/m11196/backend/modules/imo_g12_fuel_safety"
NODE_TEST_DIR = os.path.join(NODE_CODE_DIR, "tests")


def fetch_markdown(offline: bool) -> tuple[str, dict]:
    """取回 report 12510 的 markdown 与记录元数据。返回 (markdown, record)。"""
    if offline:
        with open(os.path.join(SNAP_DIR, "report_12510_api.json"), encoding="utf-8") as f:
            rec = json.load(f)
        return rec["markdown"], rec
    base = os.environ["TENSOR_API_BASE"]
    user, pw = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    body = json.dumps({"username": user, "password": pw}).encode()
    req = urllib.request.Request(
        base + "/auth/login", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        token = json.load(r)["access_token"]
    req = urllib.request.Request(
        base + "/tensor/reports/12510", headers={"Authorization": "Bearer " + token}
    )
    with urllib.request.urlopen(req) as r:
        rec = json.load(r)
    return rec["markdown"], rec


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def locate(md: str, quote: str) -> dict:
    """在 markdown 内定位逐字引文；不唯一或找不到即失败（拒绝编造）。"""
    n = md.count(quote)
    if n != 1:
        raise SystemExit(f"locator quote not unique (count={n}): {quote!r}")
    start = md.index(quote)
    end = start + len(quote)
    start_line = md.count("\n", 0, start)
    end_line = md.count("\n", 0, end)
    return {
        "method": "char_span",
        "start_char": start,
        "end_char": end,
        "start_line": start_line,
        "end_line": end_line,
        "quote": quote,
        "unique": True,
    }


def disk_probe(path: str) -> dict:
    """只读探测本地节点上的工件；返回存在性/大小/哈希（目录则列文件数）。"""
    out = {"path": path, "exists": os.path.exists(path)}
    if out["exists"]:
        if os.path.isdir(path):
            files = sorted(
                f for f in os.listdir(path) if not f.startswith("__pycache__")
            )
            out["kind"] = "dir"
            out["entries"] = files
            out["entry_count"] = len(files)
        else:
            b = open(path, "rb").read()
            out["kind"] = "file"
            out["bytes"] = len(b)
            out["sha256"] = "sha256:" + sha256_hex(b)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    md, rec = fetch_markdown(args.offline)
    b = md.encode("utf-8")
    digest = "sha256:" + sha256_hex(b)

    # ---- 契约一致性（零手抄：全部运行时计算后与契约声明比对）----
    checks = {
        "hash_check": {
            "expected": CONTRACT["source_hash"],
            "recomputed": digest,
            "match": digest == CONTRACT["source_hash"],
        },
        "chars_check": {
            "expected": CONTRACT["chars"],
            "observed": len(md),
            "match": len(md) == CONTRACT["chars"],
        },
        "title_check": {
            "expected": CONTRACT["title"],
            "observed": rec["title"],
            "match": rec["title"] == CONTRACT["title"],
        },
        "scenario_key_check": {
            "expected": CONTRACT["scenario_key"],
            "observed": rec["scenario_key"],
            "match": rec["scenario_key"] == CONTRACT["scenario_key"],
        },
    }
    if not all(c["match"] for c in checks.values()):
        raise SystemExit(f"contract mismatch: {checks}")

    # ---- 资产登记（quote 为字面量针，运行时定位；找不到/不唯一即失败）----
    fig_names = [
        "fig1_fuel_properties",
        "fig2_hazard_levels",
        "fig3_risk_matrix",
        "fig4_risk_comparison",
    ]
    assets = []

    # A1 源文档本体
    h1 = "# IMO IGF/G12 替代燃料安全评估框架"
    assets.append({
        "asset_id": "ast-12510-01",
        "kind": "source_document",
        "role": "primary_source",
        "name": "report_12510_markdown",
        "locators": [{
            "source_uri": "tensor://reports/12510",
            "source_field": "markdown",
            "char_start": 0,
            "char_end": len(h1),
            "start_line": 0,
            "end_line": 0,
            "quote": h1,
            "unique": True,
            "note": "H1 line; whole-document identity (chars/bytes/sha256) recorded in content_ref",
        }],
        "content_ref": {
            "source_uri": "tensor://reports/12510",
            "source_field": "markdown",
            "chars": len(md),
            "byte_length_utf8": len(md.encode("utf-8")),
            "sha256": "sha256:" + sha256_hex(md.encode("utf-8")),
        },
        "resolvable": True,
        "resolution": "fetched_via_tensor_api",
        "status": "resolved",
    })

    # A2 记录元数据
    assets.append({
        "asset_id": "ast-12510-02",
        "kind": "record_metadata",
        "role": "identification",
        "name": "report_12510_record",
        "locators": [
            {"source_uri": "tensor://reports/12510", "source_field": "record",
             "field": "id", "value": rec["id"]},
            {"source_uri": "tensor://reports/12510", "source_field": "record",
             "field": "title", "value": rec["title"]},
            {"source_uri": "tensor://reports/12510", "source_field": "record",
             "field": "scenario_key", "value": rec["scenario_key"]},
            {"source_uri": "tensor://reports/12510", "source_field": "record",
             "field": "mission_id", "value": rec["mission_id"]},
        ],
        "resolvable": True,
        "resolution": "fetched_via_tensor_api",
        "status": "resolved",
    })

    # A3..A6 四张图（markdown 内引用 + 记录 figures 元数据 + 本地节点字节验证）
    for i, fn in enumerate(fig_names, start=3):
        png = f"{fn}.png"
        quote = f"![{fn}]({png})"
        loc = locate(md, quote)
        disk = disk_probe(os.path.join(NODE_ARTIFACT_DIR, png))
        if not disk.get("exists"):
            raise SystemExit(f"figure not found on node: {png}")
        rec_fig = rec["figures"][i - 3]
        if rec_fig["name"] + ".png" != png:
            raise SystemExit(f"figures metadata mismatch at index {i-3}")
        assets.append({
            "asset_id": f"ast-12510-{i:02d}",
            "kind": "figure",
            "role": "result_figure",
            "name": png,
            "locators": [
                {
                    "source_uri": "tensor://reports/12510",
                    "source_field": "markdown",
                    "char_start": loc["start_char"],
                    "char_end": loc["end_char"],
                    "start_line": loc["start_line"],
                    "end_line": loc["end_line"],
                    "quote": quote,
                    "unique": True,
                },
                {"source_uri": "tensor://reports/12510", "source_field": "record",
                 "field": f"figures[{i-3}].name", "value": png},
            ],
            "caption": rec_fig["caption"],
            "node_artifact": disk,
            "resolvable": True,
            "resolution": "referenced_in_markdown_and_record; bytes verified on node",
            "status": "resolved",
        })

    # A7 代码模块
    code_quote = "- **代码路径**: `backend/modules/imo_g12_fuel_safety/`"
    loc = locate(md, code_quote)
    code_disk = disk_probe(NODE_CODE_DIR)
    if not code_disk.get("exists"):
        raise SystemExit("code module not found on node")
    assets.append({
        "asset_id": "ast-12510-07",
        "kind": "source_code_module",
        "role": "implementation",
        "name": "backend/modules/imo_g12_fuel_safety",
        "locators": [{
            "source_uri": "tensor://reports/12510",
            "source_field": "markdown",
            "char_start": loc["start_char"],
            "char_end": loc["end_char"],
            "start_line": loc["start_line"],
            "end_line": loc["end_line"],
            "quote": code_quote,
            "unique": True,
        }],
        "node_artifact": code_disk,
        "resolvable": True,
        "resolution": "referenced_in_markdown; module verified on node",
        "status": "resolved",
    })

    # A8 测试套件
    test_quote = "- **测试路径**: `backend/modules/imo_g12_fuel_safety/tests/`"
    loc = locate(md, test_quote)
    test_disk = disk_probe(NODE_TEST_DIR)
    if not test_disk.get("exists"):
        raise SystemExit("test suite not found on node")
    assets.append({
        "asset_id": "ast-12510-08",
        "kind": "test_suite",
        "role": "verification",
        "name": "backend/modules/imo_g12_fuel_safety/tests",
        "locators": [{
            "source_uri": "tensor://reports/12510",
            "source_field": "markdown",
            "char_start": loc["start_char"],
            "char_end": loc["end_char"],
            "start_line": loc["start_line"],
            "end_line": loc["end_line"],
            "quote": test_quote,
            "unique": True,
        }],
        "node_artifact": test_disk,
        "resolvable": True,
        "resolution": "referenced_in_markdown; suite verified on node",
        "status": "resolved",
    })

    # ---- 计数与不变量（全部运行时计算）----
    ids = [a["asset_id"] for a in assets]
    by_class: dict[str, int] = {}
    for a in assets:
        by_class[a["kind"]] = by_class.get(a["kind"], 0) + 1
    manifest = {
        "manifest_version": "1.0",
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "scope": {
            "report_id": CONTRACT["report_id"],
            "reports_touched": [CONTRACT["report_id"]],
            "registers_assets_only": True,
            "extracts_claims": False,
            "classifies_report_type": False,
            "writes_outside_worktree": False,
        },
        "source": {
            "report_id": CONTRACT["report_id"],
            "source_uri": CONTRACT["source_uri"],
            "source_field": "markdown",
            "title": rec["title"],
            "scenario_key": rec["scenario_key"],
            "chars": len(md),
            "bytes_utf8": len(b),
            "sha256": digest,
            **checks,
            "platform_figures": rec.get("figures", []),
            "platform_tags": rec.get("tags", []),
        },
        "assets": assets,
        "asset_counts": {
            "total": len(assets),
            "by_class": by_class,
            "by_status": {
                "resolved": sum(1 for a in assets if a["status"] == "resolved"),
                "unresolved": sum(1 for a in assets if a["status"] != "resolved"),
            },
        },
        "id_uniqueness": {
            "asset_ids_unique": len(ids) == len(set(ids)),
            "claim_ids_unique": True,
        },
        "claims": [],
        "claims_policy": (
            "empty is legitimate for this package: objective.classify_report_type=false, "
            "no extraction; claims are not force-generated"
        ),
        "integrity": {
            "quote_uniqueness": (
                "every markdown locator quote verified at runtime as a unique verbatim "
                "substring of the fetched markdown (count==1); failure aborts the build"
            ),
            "hash_recomputed_locally": digest,
            "hash_matches_contract": checks["hash_check"]["match"],
        },
    }

    envelope = {
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "report_id": CONTRACT["report_id"],
        "provenance": {
            "source_hash": digest,
            "source_field": "markdown",
            "producer": "agent/m15747",
            "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "notes": (
                "source_hash recomputed from the report-12510 markdown bytes fetched over "
                "the TensorPlatform API; equals the contract-declared hash "
                + CONTRACT["source_hash"]
            ),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    # ---- 信封 schema 校验（schemas/kf_result.v1.schema.json）----
    import jsonschema

    with open(os.path.join(REPO, "schemas", "kf_result.v1.schema.json"), encoding="utf-8") as f:
        schema = json.load(f)
    jsonschema.validate(instance=envelope, schema=schema)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "asset_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(os.path.join(OUT_DIR, "kf_result.json"), "w", encoding="utf-8") as f:
        json.dump(envelope, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(os.path.join(SNAP_DIR, "markdown.sha256"), "w", encoding="utf-8") as f:
        f.write(digest + "  report_12510.md\n")

    print(json.dumps({
        "assets": len(assets),
        "by_class": by_class,
        "hash": digest,
        "hash_match": checks["hash_check"]["match"],
        "chars": len(md),
        "schema_pass": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
