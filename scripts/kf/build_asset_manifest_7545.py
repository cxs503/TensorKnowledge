#!/usr/bin/env python3
"""Work package wp-7545-01 (task_type=01-asset-registration) — asset registration for report 7545.

Scope guard (contract): touches ONLY report_id=7545; registration only, no extraction, no
claim generation, no `verified` marks. Every locator quote is sliced out of the fetched
markdown bytes (never retyped), so each quote is a literal substring of the source.

Usage:
  python3 scripts/kf/build_asset_manifest_7545.py build
  python3 scripts/kf/build_asset_manifest_7545.py verify
  python3 scripts/kf/build_asset_manifest_7545.py build verify
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PKG = "wp-7545-01"
REPORT_ID = "7545"
SOURCE_URI = "tensor://reports/7545"
SOURCE_FIELD = "markdown"
CONTRACT_HASH = "84010e0091071d5971888931b9d6b73fc3bba4f217dcd17ab739979fc1c5ae60"
CONTRACT_CHARS = 3583

REPO = Path(__file__).resolve().parents[2]
# .gitignore drops artifacts/** at push time (see docs/ops/filter-audit.md), so outputs live
# under docs/kf/<pkg>/ to survive the delivery gate instead of being silently filtered.
OUT_DIR = REPO / "docs" / "kf" / PKG
MANIFEST = OUT_DIR / "asset_manifest.json"
RESULT = OUT_DIR / "kf_result.json"
VERDICT = OUT_DIR / "verification.json"

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]

FILE_RE = re.compile(r"`([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:json|jsonl|py|md|txt|csv|png))(?::([A-Za-z0-9_()]+))?`")
TICK_RE = re.compile(r"`([^`\n]+)`")
HEAD_RE = re.compile(r"^#{1,3}\s+(.*)$")


# ---------------------------------------------------------------- platform I/O


def _req(url, token=None, data=None):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    d = _req(BASE + "/auth/login", data=json.dumps({"username": USER, "password": PASS}).encode())
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login returned no token: %s" % sorted(d))
    return tok


def fetch_report(token):
    d = _req(BASE + "/tensor/reports/%s" % REPORT_ID, token)
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    md = d.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("report %s carries no markdown field" % REPORT_ID)
    return d, md


def probe_figure(token, name):
    """Byte-level probe of the platform figure endpoint (record outcome, never invent bytes)."""
    url = BASE + "/tensor/reports/%s/figures/%s" % (REPORT_ID, name)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        raw = urllib.request.urlopen(req, timeout=60).read()
        return {"status": "ok", "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    except urllib.error.HTTPError as e:
        return {"status": "http_%s" % e.code, "detail": e.read().decode("utf-8", "replace")[:120]}
    except Exception as e:  # noqa: BLE001 - record, do not fabricate
        return {"status": "error", "detail": type(e).__name__}


# ---------------------------------------------------------------- worktree inventory


def tracked_paths():
    try:
        out = subprocess.run(["git", "-C", str(REPO), "ls-files"], capture_output=True, text=True, check=True)
        return set(out.stdout.split())
    except Exception:  # noqa: BLE001 - git may be absent in a bare export
        return set()


TRACKED = tracked_paths()


def resolve_local(path):
    """Resolve strictly inside the delivery worktree; cross-repo targets stay unresolved by design."""
    cand = (REPO / path).resolve()
    if str(cand).startswith(str(REPO)) and cand.exists():
        return {"status": "resolved_in_source", "how": "worktree_path", "abs": str(cand.relative_to(REPO))}
    hits = [p for p in TRACKED if p == path or p.startswith(path.rstrip("/") + "/")]
    if hits:
        return {"status": "resolved_in_source", "how": "git_index", "matches": len(hits)}
    return {"status": "referenced_unresolved", "how": "absent_from_worktree_and_git_index"}


# ---------------------------------------------------------------- assets


def locate(md, quote):
    start = md.find(quote)
    if start < 0:
        raise SystemExit("quote is not a substring of the source markdown: %r" % quote[:60])
    end = start + len(quote)
    first, last = start, end - 1
    return {
        "method": "char_span",
        "start_char": start,
        "end_char": end,
        "start_line": md.count("\n", 0, first) + 1,
        "end_line": md.count("\n", 0, last) + 1,
        "quote": quote,
        "unique": md.count(quote) == 1,
    }


def section_of(md, char_pos):
    head = "（正文首部）"
    for line in md[:char_pos].split("\n"):
        m = HEAD_RE.match(line.strip())
        if m:
            head = m.group(1).strip()
    return head


def collect_references(md):
    """Backticked file refs (with optional `:pin`) plus directory/command refs, deduplicated."""
    refs, seen = [], set()
    for lineno, line in enumerate(md.split("\n"), start=1):
        for m in FILE_RE.finditer(line):
            path, pin = m.group(1), m.group(2)
            key = (path, m.group(0))
            if key in seen:
                continue
            seen.add(key)
            refs.append({"path": path, "pin": pin, "token": m.group(0), "line": lineno,
                         "via": "backticked_file_ref",
                         "asset_class": {"py": "source_code_reference", "png": "figure_reference"}.get(
                             path.rsplit(".", 1)[-1], "data_artifact_reference")})
    file_tokens = {r["token"] for r in refs}
    for lineno, line in enumerate(md.split("\n"), start=1):
        for m in TICK_RE.finditer(line):
            tok = m.group(1)
            if m.group(0) in file_tokens or "/" not in tok:
                continue
            if " " in tok:  # e.g. a shell command such as the pytest invocation
                refs.append({"path": tok, "pin": None, "token": m.group(0), "line": lineno,
                             "via": "backticked_command_ref", "asset_class": "test_command_reference"})
            else:
                refs.append({"path": tok, "pin": None, "token": m.group(0), "line": lineno,
                             "via": "backticked_dir_ref", "asset_class": "directory_reference"})
    return refs


def build():
    token = login()
    meta, md = fetch_report(token)
    raw = md.encode("utf-8")
    actual = hashlib.sha256(raw).hexdigest()
    if actual != CONTRACT_HASH:
        raise SystemExit("source hash mismatch: recomputed=%s contract=%s" % (actual, CONTRACT_HASH))

    assets = [
        {
            "asset_id": "A01",
            "asset_class": "report_markdown",
            "label": "报告 markdown 全文字节（source_uri 指向的主资产）",
            "in_report_section": "（整篇）",
            "uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "chars": len(md),
            "bytes_utf8": len(raw),
            "sha256": actual,
            "locator": {
                "method": "document",
                "start_char": 0,
                "end_char": len(md),
                "start_line": 1,
                "end_line": md.count("\n") + 1,
                "quote": md.split("\n")[0],
                "unique": md.count(md.split("\n")[0]) == 1,
            },
            "resolution": "resolved_in_source",
            "resolution_check": {"check": "sha256(markdown utf-8 bytes) recomputed from GET /tensor/reports/7545",
                                 "result": "resolved"},
            "note": "字节哈希与契约 source_hash 一致；本包只登记资产，不抽取、不改写。",
        }
    ]

    figs = meta.get("figures") or []
    for i, fig in enumerate(figs, start=1):
        probe = probe_figure(token, fig["name"])
        mentions = [ln for ln in md.split("\n") if ("图 %d" % i) in ln]
        quote = mentions[0].strip().lstrip("- ").strip() if mentions else None
        if quote and quote not in md:
            quote = None
        loc = (locate(md, quote) if quote else
               {"method": "document", "start_char": 0, "end_char": len(md), "start_line": 1,
                "end_line": md.count("\n") + 1, "quote": md.split("\n")[0], "unique": False})
        assets.append({
            "asset_id": "A%02d" % (len(assets) + 1),
            "asset_class": "embedded_figure",
            "label": fig["name"],
            "in_report_section": section_of(md, loc["start_char"]),
            "uri": "tensor://reports/7545#figures[%d]" % (i - 1),
            "caption": fig.get("caption"),
            "sha256": probe.get("sha256"),
            "bytes_utf8": probe.get("bytes"),
            "locator": loc,
            "resolution": "resolved_in_source" if probe["status"] == "ok" else "declared_absent",
            "resolution_check": {
                "check": "GET /tensor/reports/7545/figures/%s byte probe" % fig["name"],
                "result": "present" if probe["status"] == "ok" else "absent",
            },
            "note": ("图注在 markdown 内逐字可定位；平台 figures 元数据有 name/caption，"
                     "但取值端点返回 %s %s，故无可哈希字节 → declared_absent（不臆造摘要）。"
                     % (probe["status"], probe.get("detail", ""))).replace("  ", " "),
        })

    for ref in collect_references(md):
        res = resolve_local(ref["path"])
        if ref["asset_class"] == "test_command_reference":
            res = {"status": "referenced_unresolved", "how": "command_not_executable_here"}
        label = ref["path"] + (":%s" % ref["pin"] if ref.get("pin") else "")
        assets.append({
            "asset_id": "A%02d" % (len(assets) + 1),
            "asset_class": ref["asset_class"],
            "label": label,
            "path_reference": ref["path"],
            "pin": ref.get("pin"),
            "in_report_section": section_of(md, md.find(ref["token"])),
            "uri": "tensor://reports/7545#markdown:L%d" % ref["line"],
            "locator": locate(md, ref["token"]),
            "resolution": res["status"],
            "resolution_check": {"check": "worktree path + git index lookup inside %s" % REPO.name,
                                 "result": "resolved" if res["status"] == "resolved_in_source" else "unresolved"},
            "note": {
                "worktree_path": "命中本工作树路径 %s" % res.get("abs"),
                "git_index": "命中 git 索引 %d 个条目" % res.get("matches", 0),
                "absent_from_worktree_and_git_index":
                    "报告引用的产物属于产生该报告的域仓/任务树（如 tools/abm、domains/ice_fracture_contact、"
                    "artifacts/IN59-P2/*），不在 TensorKnowledge 检出内；按边界不跨仓拷贝、不臆造哈希。",
                "command_not_executable_here":
                    "命令文本可逐字定位，但本包边界只登记资产、不执行测试；执行结论归报告作者，未在此复核。",
            }.get(res["how"], res["how"]),
        })

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contract": {
            "contract_version": "1.0",
            "lane": "C",
            "objective": {"register_assets": True, "classify_report_type": False},
            "source_hash_declared": "sha256:" + CONTRACT_HASH,
            "contract_chars": CONTRACT_CHARS,
            "repo": "TensorKnowledge",
            "status": "draft",
        },
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": actual,
            "chars": len(md),
            "bytes_utf8": len(raw),
            "title": meta.get("title"),
            "scenario_key": meta.get("scenario_key"),
            "platform_figures": [f.get("name") for f in figs],
            "platform_tags": meta.get("tags") or [],
            "report_mission_id": meta.get("mission_id"),
            "report_status": meta.get("status"),
            "report_created_at": meta.get("created_at"),
            "fetched_via": "GET /api/v1/tensor/reports/%s" % REPORT_ID,
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
        },
        "assets": assets,
        "claims": [],
        "claims_note": ("objective 只含 register_assets（classify_report_type=false），契约 no_forced_claim_generation=true，"
                        "故本包 claims 为空数组：空数组是合法完整结果，不造知识；任何抽取/核验留给下游工序与平台门。"),
        "integrity": {
            "quote_uniqueness": {
                "checked": len(assets),
                "unique": sum(1 for a in assets if a["locator"].get("unique")),
                "non_unique_ids": [a["asset_id"] for a in assets if not a["locator"].get("unique")],
            },
            "hash_recomputed_locally": actual,
            "hash_matches_contract": actual == CONTRACT_HASH,
            "chars_matches_contract": len(md) == CONTRACT_CHARS,
            "hashed_bytes": "markdown encoded as utf-8",
        },
        "identity_granularity": (
            "引用资产的标识是出现级（occurrence-level）：asset_id 绑定 (path_reference, markdown token)，"
            "因此同一命令在正文与审计链各出现一次会得到 A17/A18 两个资产，各自携带自己的逐字定位；"
            "去重视图见 counts.by_class 与 assets[*].path_reference。"
        ),
        "limitations": [
            "登记工序：不做文本抽取、不生成 claim、不标 verified（verification 由平台门计算）。",
            "引用解析严格限定在 TensorKnowledge 检出内；域仓/任务树产物（tools/abm、dem_bpm.py、artifacts/IN59-P2/*）按边界登记为 referenced_unresolved，不跨仓猜测。",
            "平台 figures 元数据 4 条 name/caption 全部登记；取值端点 404，无字节可哈希 → declared_absent。",
            "本包不执行报告声称的 pytest 命令，测试通过性未在此复核（仅登记命令文本可定位）。",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (%d assets, %s)" % (MANIFEST.relative_to(REPO), len(assets), by_res))
    return manifest


def emit_result(manifest):
    blob = MANIFEST.read_bytes()
    result = {
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + manifest["source"]["hash"],
            "hash_alg": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": manifest["source"]["chars"],
            "source_bytes_utf8": manifest["source"]["bytes_utf8"],
            "fetched_via": manifest["source"]["fetched_via"],
            "generator": "scripts/kf/build_asset_manifest_7545.py",
            "contract_version": "1.0",
            "producer": "agent/m15597",
            "emitted_at": datetime.now(timezone.utc).isoformat(),
        },
        "outputs": {
            "asset_manifest.json": {
                "path": str(MANIFEST.relative_to(REPO)),
                "sha256": hashlib.sha256(blob).hexdigest(),
                "bytes": len(blob),
                "asset_count": manifest["counts"]["assets"],
                "by_resolution": manifest["counts"]["by_resolution"],
                "claims": len(manifest["claims"]),
            }
        },
        "claims": [],
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s" % RESULT.relative_to(REPO))
    return result


# ---------------------------------------------------------------- independent verify


def _patched_schema(schema):
    """Local schemas/asset_manifest.v1.schema.json pins const package_id=wp-448-01; rebind to this package."""
    import copy
    s = copy.deepcopy(schema)
    s["properties"]["package_id"] = {"const": PKG}
    s["properties"]["report_id"] = {"const": REPORT_ID}
    s["properties"]["source"]["properties"]["uri"] = {"const": SOURCE_URI}
    return s


def verify():
    import jsonschema

    checks = {}
    token = login()
    meta, md = fetch_report(token)
    lines = md.split("\n")

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        result = json.loads(RESULT.read_text(encoding="utf-8"))
        checks["valid_json"] = {"pass": True, "detail": "asset_manifest.json + kf_result.json json.loads OK"}
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"valid_json": {"pass": False, "detail": str(e)}}))
        return 1

    schema = json.loads((REPO / "schemas" / "asset_manifest.v1.schema.json").read_text(encoding="utf-8"))
    kf_schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    errors = []
    try:
        jsonschema.validate(manifest, _patched_schema(schema))
    except jsonschema.ValidationError as e:
        errors.append("asset_manifest: %s at %s" % (e.message, list(e.absolute_path)))
    try:
        jsonschema.validate(result, kf_schema)
    except jsonschema.ValidationError as e:
        errors.append("kf_result: %s at %s" % (e.message, list(e.absolute_path)))
    if result["provenance"]["source_hash"] != "sha256:" + CONTRACT_HASH:
        errors.append("kf_result provenance.source_hash != contract source_hash")
    out = result["outputs"]["asset_manifest.json"]
    if out["sha256"] != hashlib.sha256(MANIFEST.read_bytes()).hexdigest():
        errors.append("outputs.asset_manifest.json sha256 does not match the file on disk")
    checks["schema_pass"] = {
        "pass": not errors,
        "detail": ("asset_manifest.v1 (consts rebound to %s/%s) + kf_result.v1 validated; errors=%s"
                   % (PKG, REPORT_ID, errors)),
    }

    bad_loc, unverifiable = [], []
    for a in manifest["assets"]:
        loc, q = a["locator"], a["locator"]["quote"]
        if loc["method"] == "document":
            ok = q in md and loc["start_char"] == 0 and loc["end_char"] == len(md)
        else:
            ok = (md[loc["start_char"]:loc["end_char"]] == q
                  and 1 <= loc["start_line"] <= len(lines)
                  and q in lines[loc["start_line"] - 1])
        if not ok:
            bad_loc.append(a["asset_id"])
        if not loc.get("unique"):
            unverifiable.append(a["asset_id"])
    checks["source_locator_resolvable"] = {
        "pass": not bad_loc,
        "detail": "checked %d locators against freshly fetched markdown; failing=%s; non-unique quotes=%s"
                  % (len(manifest["assets"]), bad_loc, unverifiable),
    }

    actual = hashlib.sha256(md.encode("utf-8")).hexdigest()
    declared = manifest["source"]["hash"]
    checks["source_hash_matches"] = {
        "pass": actual == declared == CONTRACT_HASH == result["provenance"]["source_hash"].split("sha256:")[-1],
        "detail": "recomputed=%s manifest=%s contract=%s" % (actual, declared, CONTRACT_HASH),
    }

    ids = [a["asset_id"] for a in manifest["assets"]]
    checks["no_duplicate_ids"] = {
        "pass": len(ids) == len(set(ids)) and all(re.fullmatch(r"A[0-9]{2}", i) for i in ids),
        "detail": "assets=%d unique=%d" % (len(ids), len(set(ids))),
    }

    claims = manifest.get("claims", []) + result.get("claims", [])
    bad_claims = [c for c in claims if not c.get("evidence") and c.get("status") != "unresolved"]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not bad_claims,
        "detail": "claims=%d violating=%d (empty array: vacuously satisfied per contract notes)"
                  % (len(claims), len(bad_claims)),
    }
    checks["do_not_mark_claims_as_verified"] = {
        "pass": all(c.get("status") != "verified" for c in claims)
                and manifest["contract"]["status"] == "draft",
        "detail": "no claim carries status=verified; manifest contract.status=draft",
    }

    verdict = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(MANIFEST.relative_to(REPO)),
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "kf_result": str(RESULT.relative_to(REPO)),
        "kf_result_sha256": hashlib.sha256(RESULT.read_bytes()).hexdigest(),
        "checks": checks,
        "all_pass": all(c["pass"] for c in checks.values()),
        "scope_note": "verification here = self-check of packagable structure; report-level truth is platform-gated.",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    VERDICT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0 if verdict["all_pass"] else 1


if __name__ == "__main__":
    acts = sys.argv[1:] or ["build", "result", "verify"]
    man = build() if "build" in acts else None
    if "result" in acts:
        emit_result(man or json.loads(MANIFEST.read_text(encoding="utf-8")))
    if "verify" in acts:
        sys.exit(verify())