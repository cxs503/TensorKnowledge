#!/usr/bin/env python3
"""wp-1538-01 · 01-asset-registration for report_id=1538.

只做资产登记：确认 report_id ↔ markdown 字节哈希的对应关系，列出可解析的附件/工件，
不做内容抽取（claims 允许为空数组，本包保持空）。

零手抄纪律：本脚本不手打任何来自报告的数字/引文。所有登记字段要么来自
  (a) 平台 API 返回的报告记录本身（title/scenario_key/figures/chars），
  (b) 契约常量（package_id / source_hash / scenario_key / chars，均为派单给定值），
  (c) 从 markdown 中**程序化**抽取（§7 工件表路径、定位引文、行号），
并对每条抽取出的引文断言 `quote in markdown`（字节级子串命中），否则 fail-fast。

只读约束：仅 GET report_id=1538；不写任何其它 report。

用法：
    TENSOR_API_BASE=... TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=... \
      python3 artifacts/wp-1538-01/build_asset_manifest.py
退出码 0 = 全部断言通过；非 0 = 有硬失败（详见 stderr 与 check_log）。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PACKAGE_ID = "wp-1538-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "1538"
SOURCE_URI = "tensor://reports/1538"
SOURCE_FIELD = "markdown"
# 契约给定值（派单 YAML），不是从报告里抄的
CONTRACT_SOURCE_HASH = "sha256:9d7f968e4c888872eba25bfc190c3e6415e5c7a8f0f4b2733e665181e0d17c85"
CONTRACT_CHARS = 9477
CONTRACT_TITLE = "m1829 · CII 要求值 C1/C2「静默默认」缺陷：定位取证与显式 regime 修复"
CONTRACT_SCENARIO_KEY = "green_navigation/cii_required_value"

HERE = Path(__file__).resolve().parent
WORKTREE_ROOT = HERE.parent.parent  # artifacts/wp-1538-01 -> repo root

# 登记时点可探查的检出根（只做存在性探查，不读内容、不改任何文件）
PROBE_ROOTS = {
    "ship_performance_platform_declared_context": Path(
        "/root/ship-performance-platform-incoming/ship-performance-platform"
    ),
    "this_worktree_TensorKnowledge_m15528": WORKTREE_ROOT,
}

CHECK: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    CHECK.append((name, bool(ok), detail))
    return bool(ok)


def api_get_token(base: str, user: str, password: str) -> str:
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": user, "password": password}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as fh:
        payload = json.load(fh)
    payload = payload.get("data") or payload
    tok = payload.get("access_token") or payload.get("token")
    if not tok:
        raise RuntimeError("login 未返回 token")
    return tok


def api_get_report(base: str, token: str, report_id: str) -> dict:
    req = urllib.request.Request(
        f"{base}/tensor/reports/{report_id}", headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req, timeout=60) as fh:
        payload = json.load(fh)
    return payload.get("data") or payload


def line_of(markdown: str, needle: str) -> int:
    """1-based 行号；needle 必须是 markdown 的子串（fail-fast 保证）。"""
    if needle not in markdown:
        raise AssertionError(f"引文不在原文中（零手抄检查失败）: {needle!r}")
    return markdown[: markdown.index(needle)].count("\n") + 1


def parse_artifact_table(markdown: str) -> list[dict]:
    """从 §7 工件清单表中程序化抽取 path/cell，不手打任何路径。"""
    sec = re.search(r"^## 7 .*$", markdown, re.MULTILINE)
    if not sec:
        raise AssertionError("未找到 §7 工件清单小节")
    tail = markdown[sec.end() :]
    rows = []
    for line in tail.splitlines():
        if line.startswith("## "):  # 下一小节
            break
        m = re.match(r"^\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|\s*$", line)
        if m:
            rows.append({"declared_path": m.group(1), "declared_content": m.group(2), "table_row": line})
    return rows


def main() -> int:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    user = os.environ["TENSOR_AGENT_USER"]
    password = os.environ["TENSOR_AGENT_PASS"]

    token = api_get_token(base, user, password)
    rec = api_get_report(base, token, REPORT_ID)
    md = rec.get("markdown") or ""
    md_bytes = md.encode("utf-8")
    observed_hash = hashlib.sha256(md_bytes).hexdigest()

    # ---- A. 身份/哈希/长度（契约 vs 观测） ----
    check("report_id_matches", str(rec.get("id")) == REPORT_ID, f"observed id={rec.get('id')}")
    check(
        "source_hash_matches",
        f"sha256:{observed_hash}" == CONTRACT_SOURCE_HASH,
        f"observed=sha256:{observed_hash}",
    )
    check("chars_matches", len(md) == CONTRACT_CHARS, f"observed chars={len(md)} (契约 {CONTRACT_CHARS})")
    check("bytes_sha256_over_utf8", hashlib.sha256(md_bytes).hexdigest() == observed_hash, "utf-8 编码后重算一致")
    check("title_matches_contract", rec.get("title") == CONTRACT_TITLE, f"observed title={rec.get('title')!r}")
    check(
        "scenario_key_matches_contract",
        rec.get("scenario_key") == CONTRACT_SCENARIO_KEY,
        f"observed scenario_key={rec.get('scenario_key')!r}",
    )

    # ---- B. 附件（报告记录自带的 figures 元数据；二进制未下载，状态=metadata_only） ----
    attachments = []
    for i, fig in enumerate(rec.get("figures") or [], start=1):
        cap = fig.get("caption") or ""
        attachments.append(
            {
                "attachment_id": f"1538-att-{i:02d}",
                "name": fig.get("name"),
                "kind": "figure/png",
                "caption": cap,
                "locator": {"record_field": "figures", "index": i - 1, "name": fig.get("name")},
                "caption_locator": {"field": "record.figures[].caption", "line": line_of(md, cap)}
                if cap and cap in md
                else None,
                "caption_in_markdown": bool(cap) and cap in md,
                "name_in_markdown": bool(fig.get("name")) and str(fig.get("name")) in md,
                "name_locator": (
                    {"field": "markdown", "line": line_of(md, str(fig.get("name")))}
                    if fig.get("name") and str(fig.get("name")) in md
                    else None
                ),
                "caption_markdown_note": (
                    "报告记录的 figures[].caption 与 markdown 正文措辞不同（记录版为短摘要）；"
                    "本包保留记录版原文并标注 caption_in_markdown 结果，不改写为正文措辞。"
                ),
                "binary_resolution": "metadata_only",
                "binary_resolution_note": (
                    "仅登记报告记录中的 figures 元数据；本包未下载 PNG 二进制，"
                    "故不对其字节做存在性/哈希断言。"
                ),
            }
        )
    check("attachments_registered", True, f"figures={len(attachments)}")

    # ---- C. 工件（§7 表，程序化抽取 + 环境存在性探查） ----
    rows = parse_artifact_table(md)
    check("artifact_table_parsed", len(rows) > 0, f"rows={len(rows)}")
    artifacts = []
    for i, row in enumerate(rows, start=1):
        path = row["declared_path"]
        # 零手抄：路径与描述必须是原文子串
        line = line_of(md, row["table_row"])
        lin = line_of(md, path)
        probes = {}
        for label, root in PROBE_ROOTS.items():
            cand = root / path
            probes[label] = {
                "root": str(root),
                "abs_path": str(cand),
                "exists": cand.exists(),
            }
        any_exists = any(p["exists"] for p in probes.values())
        artifacts.append(
            {
                "artifact_id": f"1538-art-{i:02d}",
                "declared_path": path,
                "declared_kind": (
                    "source_code"
                    if path.endswith(".py")
                    else "dataset"
                    if path.endswith(".csv")
                    else "machine_output"
                    if path.endswith(".json")
                    else "patch"
                    if path.endswith(".diff")
                    else "figure"
                    if path.endswith(".png")
                    else "log"
                    if path.endswith(".txt")
                    else "test"
                    if "/tests/" in path
                    else "unknown"
                ),
                "declared_content_summary": row["declared_content"],
                "locator": {
                    "section": "§7 工件清单",
                    "table_row_line": line,
                    "path_line": lin,
                    "quote": row["table_row"],
                },
                "resolution_probes": probes,
                "resolution_status": "resolved_in_environment" if any_exists else "not_resolved",
                "resolution_note": (
                    "存在性探查仅针对登记时点可访问的检出根；"
                    "「未解析」= 本包未在该根下找到，不等于该工件不存在于其生产仓。"
                ),
            }
        )
    check("artifact_locators_exact", True, f"{len(artifacts)} 条路径/描述均为原文逐字子串")
    check(
        "no_duplicate_ids",
        len({a["artifact_id"] for a in artifacts}) == len(artifacts)
        and len({a["attachment_id"] for a in attachments}) == len(attachments)
        and len({a["declared_path"] for a in artifacts}) == len(artifacts),
        "attachment/artifact id 与 declared_path 均唯一",
    )

    # ---- D. 报告中被点名、但不属于 §7 工件表的外部引用（登记为 external_references） ----
    ext_specs = [
        {
            "label": "tensorplatform_green_navigation_module",
            "quote_candidates": ["`backend/services/green_navigation.py`"],
            "abs_path": "/root/tensor-ecosystem/TensorPlatform/backend/services/green_navigation.py",
        },
    ]
    external_references = []
    for spec in ext_specs:
        quote = next((q for q in spec["quote_candidates"] if q in md), None)
        if quote is None:
            continue
        p = Path(spec["abs_path"])
        external_references.append(
            {
                "ref_id": "1538-ext-01",
                "label": spec["label"],
                "abs_path": spec["abs_path"],
                "locator": {"field": "markdown", "line": line_of(md, quote), "quote": quote},
                "exists_at_registration": p.exists(),
                "resolution_note": "仅登记存在性；本包不读取该文件内容、不修改它。",
            }
        )
    check("external_refs_registered", True, f"count={len(external_references)}")

    # ---- D2. 本地快照（只读复本；用于离线复算哈希，不改上游） ----
    snapshot_path = WORKTREE_ROOT / "runs" / PACKAGE_ID / "source_1538.md"
    snapshot = None
    if snapshot_path.exists():
        snap_sha = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
        snapshot = {
            "path": str(snapshot_path.relative_to(WORKTREE_ROOT)),
            "sha256": f"sha256:{snap_sha}",
            "byte_identical_to_api_markdown": snap_sha == observed_hash,
        }
        check("local_snapshot_byte_identical", snap_sha == observed_hash, snapshot["sha256"])
    else:
        check("local_snapshot_byte_identical", False, "快照缺失（honest: not_run）")

    # ---- E. 组 manifest ----
    manifest = {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "title": rec.get("title"),
            "scenario_key": rec.get("scenario_key"),
            "platform_mission_id": rec.get("mission_id"),
            "platform_status": rec.get("status"),
            "created_at": rec.get("created_at"),
            "chars_declared": CONTRACT_CHARS,
            "chars_observed": len(md),
            "bytes_utf8_observed": len(md_bytes),
            "line_count_observed": md.count("\n") + 1,
            "source_hash_declared": CONTRACT_SOURCE_HASH,
            "source_hash_observed": f"sha256:{observed_hash}",
            "hash_match": f"sha256:{observed_hash}" == CONTRACT_SOURCE_HASH,
            "hash_algorithm": "sha256 over markdown.encode('utf-8')",
            "locator": {
                "api": f"GET {base}/tensor/reports/{REPORT_ID} (Bearer, field=markdown)",
                "fallback": "psql -d tensorplatform -tA -c \"select markdown from tensor_reports where id=1538\"",
                "fallback_note": "本次登记中 psql 直连被拒（permission denied for table tensor_reports），仅用 API 路径。",
            },
        },
        "attachments": attachments,
        "artifacts": artifacts,
        "external_references": external_references,
        "source_snapshot": snapshot,
        "claims": [],
        "claims_note": (
            "本工序 task_type=01-asset-registration，契约 notes 明示「不做抽取。claims 允许为空数组」；"
            "故 claims=[]（不是漏登记，也不是把结论标成 verified）。"
        ),
        "uncertainties": [
            "附件的 PNG 二进制未下载，仅登记 figures 元数据（binary_resolution=metadata_only）。",
            "工件表路径相对于其生产仓（ship-performance-platform）根；本包未在该仓做权威解析，"
            "只记录登记时点两个检出根的存在性探查结果。",
            "报告内的证据等级（如 a/c/Z 转录值的 WITHHELD）与 verification 由平台门计算，本包不复制、不改写、不升级。",
        ],
        "provenance": {
            "generated_by": f"agent/m15528 · {PACKAGE_ID}",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "builder": "artifacts/wp-1538-01/build_asset_manifest.py",
            "repro_cmd": (
                "TENSOR_API_BASE=$TENSOR_API_BASE TENSOR_AGENT_USER=$TENSOR_AGENT_USER "
                "TENSOR_AGENT_PASS=$TENSOR_AGENT_PASS python3 "
                "artifacts/wp-1538-01/build_asset_manifest.py"
            ),
        },
    }

    out_manifest = HERE / "asset_manifest.json"
    out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    check("manifest_valid_json", isinstance(json.loads(out_manifest.read_text(encoding="utf-8")), dict), str(out_manifest))
    manifest_sha = hashlib.sha256(out_manifest.read_bytes()).hexdigest()

    # ---- F. 结果信封（kf_result.v1） ----
    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": f"sha256:{observed_hash}",
            "producer": f"agent/m15528 · {PACKAGE_ID}",
            "emitted_at": manifest["provenance"]["generated_at"],
            "notes": (
                "01-asset-registration 只登记资产，不做抽取；claims=[] 合法。"
                "verification 由平台门计算，本包不自标 verified。"
            ),
            "asset_manifest_sha256": manifest_sha,
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    out_env = HERE / "kf_result_wp-1538-01.json"
    out_env.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ---- G. 结构门自检（kf_result.v1 权威 schema；本分支树内缺失则用同仓兄弟检出，记录 sha256） ----
    schema_note = ""
    schema_candidates = [WORKTREE_ROOT / "schemas" / "kf_result.v1.schema.json"]
    if os.environ.get("KF_RESULT_SCHEMA"):
        schema_candidates.append(Path(os.environ["KF_RESULT_SCHEMA"]))
    sibling = sorted(Path("/root/tp-agent/work").glob("*/schemas/kf_result.v1.schema.json"))
    schema_candidates.extend(sibling)
    schema_path = next((c for c in schema_candidates if c.exists()), None)
    if schema_path is None:
        check("schema_pass", False, "未找到 kf_result.v1.schema.json（honest: not_run）")
        schema_note = "schema not found (not_run)"
    else:
        raw = schema_path.read_bytes()
        schema = json.loads(raw)
        schema_sha = hashlib.sha256(raw).hexdigest()
        schema_note = f"{schema_path} sha256={schema_sha}"
        try:
            import jsonschema  # type: ignore

            jsonschema.validate(envelope, schema)
            jsonschema.validate({"package_id": PACKAGE_ID}, schema)  # 反证：缺键必须被判失败
            check("schema_negative_control", False, "反证未触发——schema 可能过于宽松")
        except ImportError:
            check("schema_pass", False, "jsonschema 未安装（honest: not_run）")
            schema_note += " | jsonschema not installed (not_run)"
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).splitlines()[0]
            if "is a required property" in msg or "required" in msg:
                # 反证按预期失败；再用未削弱的 try 校验 envelope 本身
                import jsonschema  # type: ignore

                try:
                    jsonschema.validate(envelope, schema)
                except Exception as exc2:  # noqa: BLE001
                    check("schema_pass", False, str(exc2).splitlines()[0])
                    schema_note += " | envelope invalid"
                else:
                    check("schema_pass", True, f"envelope 通过 {schema_path.name}；反证（缺 package_id）被正确判失败")
            else:
                check("schema_pass", False, msg)
    # manifest 的必备键（outputs 声明的产物自检）
    req_manifest = {
        "package_id", "task_type", "report", "attachments", "artifacts",
        "external_references", "claims", "uncertainties", "provenance",
    }
    check(
        "manifest_schema_pass",
        req_manifest <= set(manifest) and manifest["report"]["hash_match"] is True,
        f"必备键齐全={req_manifest <= set(manifest)}; report.hash_match={manifest['report']['hash_match']}",
    )

    # ---- H. 写 check log ----
    log = {
        "package_id": PACKAGE_ID,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "checks": [{"name": n, "ok": o, "detail": d} for n, o, d in CHECK],
        "all_ok": all(o for _, o, _ in CHECK),
        "schema_note": schema_note,
        "asset_manifest_sha256": manifest_sha,
        "kf_result_sha256": hashlib.sha256(out_env.read_bytes()).hexdigest(),
    }
    (HERE / "check_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for n, o, d in CHECK:
        print(f"[{'OK ' if o else 'FAIL'}] {n}: {d}")
    print(f"\nmanifest: {out_manifest}\nenvelope: {out_env}\nall_ok={log['all_ok']}")
    return 0 if log["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())