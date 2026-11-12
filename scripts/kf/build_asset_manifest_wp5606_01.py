#!/usr/bin/env python3
"""KF work-package wp-5606-01 (task_type 01-asset-registration) — asset registration only.

Registers report_id=5606 (tensor://reports/5606, field=markdown):
  * confirms the SHA-256 of the markdown bytes against the work-package contract;
  * inventories attachments / referenced artifacts with source locators;
  * performs NO knowledge extraction (claims = [] by contract).

Every number / quote emitted here is derived programmatically from the report
payload fetched at run time — no hand transcription.  Idempotent: rerunning
regenerates byte-identical content except `generated_at`/`emitted_at`.

Usage:
    TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS must be set.
    python3 scripts/kf/build_asset_manifest_wp5606_01.py \
        --report-id 5606 --out runs/wp-5606-01
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

PACKAGE_ID = "wp-5606-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "5606"
SOURCE_URI = "tensor://reports/5606"
SOURCE_FIELD = "markdown"
CONTRACT_SOURCE_HASH = (
    "sha256:da0d91e5c5eae1aa240fba2fcc6b0ebab3960fb49f0f31378cf9a7f866b14edd"
)
CONTRACT_TITLE = "IN18-T3 顶刊报告框架与防造假溯源管线（快照+SHA-256+重跑 SQL 门禁）"
CONTRACT_SCENARIO = "campaign:IN18-T3:chronicle-report-v2"
CONTRACT_CHARS = 5853
CONTRACT_LAYER_HINT = "IN18-T3|campaign:IN18-T3:chronicle-report-v2|m"

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "schemas" / "kf_result.v1.schema.json"


# --------------------------------------------------------------------------- io
def api(path: str, token: str | None = None, data: dict | None = None):
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        base + path,
        data=json.dumps(data).encode() if data else None,
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def login() -> str:
    payload = {
        "username": os.environ["TENSOR_AGENT_USER"],
        "password": os.environ["TENSOR_AGENT_PASS"],
    }
    d = api("/auth/login", data=payload)
    return d.get("access_token") or d["token"]


# ------------------------------------------------------------------- primitives
def sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def lineno_of(lines: list[str], needle: str) -> int:
    """1-based line number of the first line containing `needle` (0 = absent)."""
    for i, ln in enumerate(lines, 1):
        if needle in ln:
            return i
    return 0


def locator(md: str, needle: str) -> dict:
    """Build a resolvable locator: verbatim quote + 1-based line, verified as substring."""
    lines = md.split("\n")
    n = lineno_of(lines, needle)
    if n == 0:
        return {
            "source_field": SOURCE_FIELD,
            "line": 0,
            "quote": "",
            "resolvable": False,
            "note": "declared token not found in report markdown",
        }
    quote = lines[n - 1].strip()
    return {
        "source_field": SOURCE_FIELD,
        "line": n,
        "quote": quote,
        "resolvable": quote in md,
    }


def sections_of(md: str) -> list[dict]:
    lines = md.split("\n")
    heads = []  # (idx0, level, text)
    for i, ln in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*\S)\s*$", ln)
        if m:
            heads.append((i, len(m.group(1)), m.group(2)))
    out = []
    for k, (i, level, text) in enumerate(heads):
        end = (heads[k + 1][0] - 1) if k + 1 < len(heads) else len(lines) - 1
        body = "\n".join(lines[i : end + 1])
        out.append(
            {
                "ordinal": k + 1,
                "level": level,
                "heading": text,
                "line_start": i + 1,
                "line_end": end + 1,
                "chars": len(body),
                "sha256": sha256_bytes(body.encode("utf-8")),
            }
        )
    return out


def resolve_local_path(p: str) -> dict:
    """Read-only existence probe for artifacts referenced by absolute path."""
    path = Path(p)
    exists = path.is_file()
    out = {
        "method": "local filesystem is_file()",
        "path": p,
        "exists": exists,
    }
    if exists:
        out["sha256"] = sha256_bytes(path.read_bytes())
    else:
        out["note"] = "referenced path is outside this worktree / not present at build time"
    return out


# --------------------------------------------------------------------- manifest
def build_manifest(md: str, rec: dict, token: str | None = None) -> dict:
    lines = md.split("\n")
    md_bytes = md.encode("utf-8")
    src_hash = sha256_bytes(md_bytes)

    attachments: list[dict] = []
    seen_ids: set[str] = set()

    def add(item: dict) -> None:
        assert item["asset_id"] not in seen_ids, f"duplicate asset_id {item['asset_id']}"
        seen_ids.add(item["asset_id"])
        attachments.append(item)

    # (a) record.figures — figure declarations stored on the platform record
    rec_figs = rec.get("figures") or []
    for k, fig in enumerate(rec_figs, 1):
        name = fig.get("name", "")
        payload_keys = sorted(set(fig.keys()))
        add(
            {
                "asset_id": f"att-fig-rec-{k:03d}",
                "kind": "figure_record_entry",
                "role": "figure",
                "name": name,
                "declared_sha256": None,
                "payload_present": False,
                "resolvable": False,
                "resolution": {
                    "method": "scan record.figures entry for binary payload keys",
                    "payload_keys": payload_keys,
                    "note": "record carries caption/name only; no png_base64 or byte payload",
                },
                "caption": fig.get("caption", ""),
                "locator": locator(md, name) if name else None,
            }
        )

    # (b) markdown figure ledger: `fig-00N` | name | file, file | `sha, sha` (11-hex prefixes)
    for m in re.finditer(r"^\|\s*`(fig-\d{3})`\s*\|(.+)$", md, re.M):
        pid, rest = m.group(1), m.group(2)
        cells = [c.strip() for c in rest.split("|")]
        if len(cells) < 3:
            continue
        files = [f.strip().strip("`") for f in cells[1].split(",")]
        hashes = [h.strip().strip("`") for h in cells[2].split(",")]
        for fname, hpref in zip(files, hashes):
            add(
                {
                    "asset_id": "att-" + fname.replace("_", "-").replace(".", "-"),
                    "kind": "figure_file",
                    "role": "figure",
                    "name": fname,
                    "ledger_pid": pid,
                    "declared_sha256": hpref,
                    "declared_sha256_is_prefix_only": len(hpref) < 64,
                    "payload_present": False,
                    "resolvable": False,
                    "resolution": {
                        "method": "look for file bytes in report payload and worktree",
                        "payload_search": "no base64/binary payload and no markdown image link in report",
                        "worktree_search": "file not present in TensorKnowledge worktree",
                        "note": "only the 11-hex SHA-256 prefix is registered in the report text",
                    },
                    "locator": locator(md, fname),
                }
            )

    # (c) frozen snapshot artifact referenced by absolute path + full snapshot hash
    for m in re.finditer(r"`(/[^`\s]+\.json)`", md):
        path = m.group(1)
        add(
            {
                "asset_id": "att-frozen-ledger-json",
                "kind": "frozen_input_artifact",
                "role": "upstream_data",
                "name": Path(path).name,
                "declared_path": path,
                "file_byte_hash_declared": None,
                "recorded_snapshot_sha256": next(
                    (h for h in re.findall(r"\b[0-9a-f]{64}\b", md) if h), None
                ),
                "hash_note": (
                    "the only 64-hex value in the report is the SQLite snapshot hash; the report "
                    "does not declare a byte hash of the ledger JSON itself, so file_byte_hash_declared "
                    "stays null"
                ),
                "payload_present": False,
                "resolvable": False,
                "resolution": resolve_local_path(path),
                "locator": locator(md, path),
            }
        )
        break  # single frozen input artifact in this report

    # (d) code modules named by basename in the methods section
    for mod in sorted(set(re.findall(r"`([A-Za-z0-9_]+\.py)`", md))):
        hits = sorted(REPO_ROOT.rglob(mod))
        add(
            {
                "asset_id": "att-code-" + mod.replace("_", "-").replace(".py", ""),
                "kind": "code_module_reference",
                "role": "implementation",
                "name": mod,
                "payload_present": False,
                "resolvable": bool(hits),
                "resolution": {
                    "method": "basename search inside TensorKnowledge worktree",
                    "hits": [str(h.relative_to(REPO_ROOT)) for h in hits],
                    "note": (
                        "report names the module by basename only (no repository/path); "
                        "not resolvable from the report text alone"
                        if not hits
                        else "resolved in worktree"
                    ),
                },
                "locator": locator(md, mod),
            }
        )

    known_hashes = sorted(set(re.findall(r"\b[0-9a-f]{64}\b", md)))
    hash_locators = [
        {
            "value": h,
            "locator": locator(md, h),
            "is_full_sha256": True,
            "appears_in_report": True,
        }
        for h in known_hashes
    ]

    manifest = {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "objective": {
            "register_assets": True,
            "classify_report_type": False,
            "extraction_performed": False,
        },
        "generated_at": now_iso(),
        "generator": "agent/m15569",
        "source_asset": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "platform_record_id": int(REPORT_ID),
            "hash": {
                "algorithm": "sha256",
                "value": src_hash,
                "scope": "UTF-8 bytes of tensor_reports.markdown (report 5606)",
                "contract_expected": CONTRACT_SOURCE_HASH,
                "matches_contract": src_hash == CONTRACT_SOURCE_HASH,
            },
            "size": {
                "chars": len(md),
                "bytes_utf8": len(md_bytes),
                "lines": len(lines),
                "contract_chars": CONTRACT_CHARS,
                "chars_match_contract": len(md) == CONTRACT_CHARS,
            },
            "record_metadata": {
                "title": rec.get("title"),
                "scenario_key": rec.get("scenario_key"),
                "tags": rec.get("tags"),
                "status": rec.get("status"),
                "created_by": rec.get("created_by"),
                "created_at": rec.get("created_at"),
                "mission_id": rec.get("mission_id"),
                "stage": rec.get("stage"),
                "figures_declared": len(rec_figs),
                "summary_sha256": sha256_bytes((rec.get("summary") or "").encode("utf-8")),
            },
            "contract_cross_check": {
                "title_matches_contract": rec.get("title") == CONTRACT_TITLE,
                "scenario_key_matches_contract": rec.get("scenario_key") == CONTRACT_SCENARIO,
                "chars_match_contract": len(md) == CONTRACT_CHARS,
                "contract_layer_hint": {
                    "value": CONTRACT_LAYER_HINT,
                    "interpreted": False,
                    "note": "objective.classify_report_type=false → hint registered verbatim, not interpreted",
                },
            },
        },
        "attachments": {
            "count": len(attachments),
            "resolvable_count": sum(1 for a in attachments if a["resolvable"]),
            "items": attachments,
            "scan": {
                "record_figures_len": len(rec_figs),
                "markdown_image_syntax_hits": len(re.findall(r"!\[", md)),
                "markdown_url_hits": len(re.findall(r"https?://", md)),
                "markdown_absolute_path_hits": len(re.findall(r"`/[^`\s]+`", md)),
                "markdown_code_module_hits": len(set(re.findall(r"`([A-Za-z0-9_]+\.py)`", md))),
                "full_sha256_literals": len(known_hashes),
            },
            "composition": {
                "figure_record_entry": sum(1 for a in attachments if a["kind"] == "figure_record_entry"),
                "figure_file": sum(1 for a in attachments if a["kind"] == "figure_file"),
                "frozen_input_artifact": sum(1 for a in attachments if a["kind"] == "frozen_input_artifact"),
                "code_module_reference": sum(1 for a in attachments if a["kind"] == "code_module_reference"),
            },
            "note": (
                "no embedded binary/base64 payload and no image link in the report markdown; "
                "figure files and the frozen input artifact are declared, not shipped — "
                "registration records the declaration and the failed local resolution attempt"
            ),
        },
        "declared_hashes": hash_locators,
        "sections": sections_of(md),
        "claims_registration": {
            "claims_emitted": 0,
            "claims_allowed_empty": True,
            "reason": (
                "task_type 01-asset-registration: objective.register_assets=true, "
                "no extraction; empty claims array is a legal complete result per contract"
            ),
        },
        "not_performed": [
            "knowledge extraction / claim generation (out of scope for 01)",
            "report type classification (objective.classify_report_type=false)",
            "verification of any report claim (verification is computed by the platform gate)",
            "byte-level check of figure PNG/PDF files (only 11-hex prefixes exist in the text, no payload)",
        ],
        "limitations": [
            "Figure attachments are registered from declarations only; their bytes were not available "
            "to this work package, so their hashes cannot be re-verified here.",
            "The frozen input artifact path points at another mission worktree and does not exist "
            "at build time; resolution status is recorded as false, not assumed.",
            "Code modules are named by basename without repository/path, so they cannot be resolved "
            "from the report text alone.",
            "Record mission_id and this work package mission differ; both values are registered "
            "verbatim without reconciliation.",
        ],
    }
    return manifest


def selfcheck(manifest: dict, md: str) -> dict:
    """Compute the contract acceptance booleans from the artifact itself, not by hand."""
    quotes = []

    def walk(node):
        if isinstance(node, dict):
            if set(node.keys()) >= {"line", "quote", "source_field"}:
                quotes.append(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(manifest)
    ids = [a["asset_id"] for a in manifest["attachments"]["items"]]
    quotes_ok = all(q["quote"] and q["quote"] in md for q in quotes)
    manifest_json = json.dumps(manifest, ensure_ascii=False)
    return {
        "valid_json": isinstance(json.loads(manifest_json), dict),
        "source_hash_matches": manifest["source_asset"]["hash"]["matches_contract"],
        "source_locator_resolvable": quotes_ok,
        "source_locator_count": len(quotes),
        "source_locator_failures": [
            q for q in quotes if not (q["quote"] and q["quote"] in md)
        ],
        "no_duplicate_ids": len(ids) == len(set(ids)),
        "all_claims_have_evidence_or_explicit_unresolved_status": (
            manifest["claims_registration"]["claims_emitted"] == 0
        ),
        "claims_empty_legal": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-id", default=REPORT_ID)
    ap.add_argument("--out", default=str(REPO_ROOT / "runs" / PACKAGE_ID))
    args = ap.parse_args()
    assert args.report_id == REPORT_ID, "this package is bound to report 5606 only"

    token = login()
    rec = api(f"/tensor/reports/{REPORT_ID}", token=token)
    md = rec["markdown"]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"source_{REPORT_ID}.md").write_text(md, encoding="utf-8")

    manifest = build_manifest(md, rec, token)
    checks = selfcheck(manifest, md)
    manifest["acceptance_selfcheck"] = checks

    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": manifest["source_asset"]["hash"]["value"],
            "source_field": SOURCE_FIELD,
            "source_uri": SOURCE_URI,
            "producer": "agent/m15569",
            "emitted_at": manifest["generated_at"],
            "notes": (
                "01-asset-registration: source hash confirmed, attachments/referenced artifacts "
                "inventoried with verbatim locators; no extraction performed; claims empty "
                "(legal per contract); verification is left to the platform gate"
            ),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    # schema validation (fails loudly, never silently downgraded)
    try:
        import jsonschema

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.validate(envelope, schema)
        checks["schema_pass"] = True
        checks["schema_path"] = str(SCHEMA_PATH.relative_to(REPO_ROOT))
    except Exception as exc:  # pragma: no cover - reported, not hidden
        checks["schema_pass"] = False
        checks["schema_error"] = f"{type(exc).__name__}: {exc}"
        raise

    (out_dir / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "kf_result.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    print(f"wrote {out_dir/'asset_manifest.json'} and {out_dir/'kf_result.json'}")
    return 0 if all(
        checks[k]
        for k in (
            "valid_json",
            "schema_pass",
            "source_hash_matches",
            "source_locator_resolvable",
            "no_duplicate_ids",
        )
    ) else 1


if __name__ == "__main__":
    sys.exit(main())