#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KF wp-9645-01 源资产快照工具（证据可复现层）。

工序 01（asset-registration）在 docs/kf/wp-9645-01/ 里钉住了源报告 9645 的
SHA-256（``source_asset.hash.value``），但原 PR 没有把被哈希的字节留进工作树，
于是「哈希自证」只能靠上游 API 复述，离线无法复核：任何 sections / locator_check /
sha256.txt 的哈希都变成不可再推导的常数。

本工具补掉这个缺口，只做一件事：

  * ``--fetch``  从平台读 report_id=9645 的 record；**先**用 manifest 里钉住的
    hash/chars 校验，**校验通过才**落盘
        docs/kf/wp-9645-01/source/report_9645.md   （源 markdown 逐字节快照）
        docs/kf/wp-9645-01/source/record_9645.json（record 元数据，去掉 markdown 载荷）
        docs/kf/wp-9645-01/source/snapshot.json    （快照自身的 provenance/自证）
    校验不通过一律返回非零，绝不覆盖旧快照（防止源头漂移被静默吸收）。
  * ``--verify`` 纯离线：对已提交的快照重算 hash/chars 并与 manifest 钉住值比对。

边界：只读 report_id=9645；不抽取、不标 verified、不改写工序 01 的既有产物。

用法：
  python3 scripts/kf/wp_9645_01_snapshot.py --fetch      # 需要 TENSOR_API_BASE 等
  python3 scripts/kf/wp_9645_01_snapshot.py --verify     # 离线
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

PACKAGE_ID = "wp-9645-01"
REPORT_ID = "9645"
SOURCE_URI = "tensor://reports/9645"
SOURCE_FIELD = "markdown"
TOOL = "scripts/kf/wp_9645_01_snapshot.py"

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PKG_DIR = os.path.join(ROOT, "docs", "kf", PACKAGE_ID)
SRC_DIR = os.path.join(PKG_DIR, "source")
SNAPSHOT_MD = os.path.join(SRC_DIR, "report_%s.md" % REPORT_ID)
SNAPSHOT_RECORD = os.path.join(SRC_DIR, "record_%s.json" % REPORT_ID)
SNAPSHOT_META = os.path.join(SRC_DIR, "snapshot.json")

# record 元数据字段（markdown 载荷单独存快照；png 载荷不属于 01 工序登记范围）
RECORD_META_FIELDS = (
    "id",
    "title",
    "summary",
    "scenario_key",
    "mission_id",
    "stage",
    "tags",
    "figures",
    "status",
    "created_by",
    "created_at",
)


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def load_manifest() -> dict:
    with open(os.path.join(PKG_DIR, "asset_manifest.json"), encoding="utf-8") as f:
        return json.load(f)


def pinned_targets(manifest: dict) -> dict:
    """从 manifest 读出被钉住的源哈希/字符数（零手抄）。"""
    src = manifest["source_asset"]
    return {
        "hash": src["hash"]["value"],
        "contract_expected": src["hash"].get("contract_expected", src["hash"]["value"]),
        "chars": src["size"]["chars"],
        "bytes_utf8": src["size"]["bytes_utf8"],
        "lines": src["size"]["lines"],
        "uri": src["uri"],
        "field": src["field"],
    }


def verify_snapshot(snapshot_bytes: bytes, targets: dict) -> dict:
    """把快照字节与钉住值比对，返回逐项检查结果。"""
    checks = []
    try:
        text = snapshot_bytes.decode("utf-8")
        decode_ok = True
        decode_error = None
    except UnicodeDecodeError as exc:  # pragma: no cover - 防御性
        text = ""
        decode_ok = False
        decode_error = str(exc)

    computed_hash = sha256_bytes(snapshot_bytes)
    checks.append(
        {
            "item": "sha256",
            "pinned": targets["hash"],
            "computed": computed_hash,
            "pass": decode_ok and computed_hash == targets["hash"],
        }
    )
    checks.append(
        {
            "item": "chars",
            "pinned": targets["chars"],
            "computed": len(text),
            "pass": decode_ok and len(text) == targets["chars"],
        }
    )
    checks.append(
        {
            "item": "bytes_utf8",
            "pinned": targets["bytes_utf8"],
            "computed": len(snapshot_bytes),
            "pass": decode_ok and len(snapshot_bytes) == targets["bytes_utf8"],
        }
    )
    checks.append(
        {
            "item": "lines",
            "pinned": targets["lines"],
            "computed": text.count("\n") + 1,
            "pass": decode_ok and text.count("\n") + 1 == targets["lines"],
        }
    )
    result = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "all_pass": all(c["pass"] for c in checks),
        "checks": checks,
    }
    if decode_error is not None:
        result["decode_error"] = decode_error
    return result


def record_payload(record: dict) -> dict:
    """record 去掉 markdown 载荷，改为哈希/长度指针（快照本身另存）。"""
    meta = {k: record.get(k) for k in RECORD_META_FIELDS if k in record}
    md = record.get("markdown") or ""
    meta["markdown_sha256"] = sha256_text(md)
    meta["markdown_chars"] = len(md)
    return meta


def api_get(path: str) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    payload = json.dumps(
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }
    ).encode()
    req = urllib.request.Request(
        base + "/auth/login", data=payload, headers={"Content-Type": "application/json"}
    )
    tok = json.load(urllib.request.urlopen(req, timeout=30))
    token = tok.get("access_token") or tok.get("token")
    req = urllib.request.Request(
        base + path, headers={"Authorization": "Bearer " + token}
    )
    return json.load(urllib.request.urlopen(req, timeout=60))


def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def do_fetch() -> int:
    if not os.environ.get("TENSOR_API_BASE"):
        print("ERROR: TENSOR_API_BASE 未设置", file=sys.stderr)
        return 2
    manifest = load_manifest()
    targets = pinned_targets(manifest)

    record = api_get("/tensor/reports/%s" % REPORT_ID)
    if str(record.get("id")) != REPORT_ID:
        print("ERROR: 返回的 report id 不符: %r" % record.get("id"), file=sys.stderr)
        return 2

    snapshot_text = record.get("markdown") or ""
    snapshot_bytes = snapshot_text.encode("utf-8")
    verdict = verify_snapshot(snapshot_bytes, targets)
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    if not verdict["all_pass"]:
        print(
            "ERROR: 平台返回的 markdown 与 manifest 钉住的哈希/长度不一致；拒绝覆盖快照",
            file=sys.stderr,
        )
        return 1

    os.makedirs(SRC_DIR, exist_ok=True)
    _write_text(SNAPSHOT_MD, snapshot_text)
    meta = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "tool": TOOL,
        "retrieved_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "source_uri": SOURCE_URI,
        "source_field": SOURCE_FIELD,
        "snapshot_file": "docs/kf/%s/source/report_%s.md" % (PACKAGE_ID, REPORT_ID),
        "record_file": "docs/kf/%s/source/record_%s.json" % (PACKAGE_ID, REPORT_ID),
        "snapshot": {
            "sha256": sha256_bytes(snapshot_bytes),
            "chars": len(snapshot_text),
            "bytes_utf8": len(snapshot_bytes),
            "lines": snapshot_text.count("\n") + 1,
        },
        "pinned": {
            "sha256": targets["hash"],
            "chars": targets["chars"],
            "bytes_utf8": targets["bytes_utf8"],
            "lines": targets["lines"],
            "origin": "docs/kf/%s/asset_manifest.json :: source_asset" % PACKAGE_ID,
        },
        "verify": verdict,
    }
    _write_text(SNAPSHOT_RECORD, json.dumps(record_payload(record), ensure_ascii=False, indent=2) + "\n")
    _write_text(SNAPSHOT_META, json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    print("WROTE %s" % os.path.relpath(SNAPSHOT_MD, ROOT))
    print("WROTE %s" % os.path.relpath(SNAPSHOT_RECORD, ROOT))
    print("WROTE %s" % os.path.relpath(SNAPSHOT_META, ROOT))
    return 0


def do_verify() -> int:
    manifest = load_manifest()
    targets = pinned_targets(manifest)
    if not os.path.exists(SNAPSHOT_MD):
        print("ERROR: 快照缺失: %s" % SNAPSHOT_MD, file=sys.stderr)
        return 1
    with open(SNAPSHOT_MD, "rb") as f:
        snapshot_bytes = f.read()
    verdict = verify_snapshot(snapshot_bytes, targets)
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0 if verdict["all_pass"] else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="wp-9645-01 源资产快照（fetch / 离线 verify）")
    ap.add_argument("--fetch", action="store_true", help="从平台抓取并校验后落盘快照")
    ap.add_argument("--verify", action="store_true", help="离线复核已提交快照")
    args = ap.parse_args(argv)
    if args.fetch and args.verify:
        print("ERROR: --fetch 与 --verify 互斥", file=sys.stderr)
        return 2
    if args.fetch:
        return do_fetch()
    if args.verify:
        return do_verify()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())