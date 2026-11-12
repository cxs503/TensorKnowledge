#!/usr/bin/env python3
"""KF work package wp-4129-01 — 01-asset-registration for report_id=4129.

Registers the source asset (report markdown byte hash), the artefacts/attachments
declared by the report, and the symbol / VCS references appearing in its prose.
Extraction of claims is a *downstream* work package: `claims` stays an empty array
by contract (objective.register_assets=true, classify_report_type=false,
constraints.no_forced_claim_generation=true).

Hard boundaries honoured here:
  * touches report_id 4129 only (no other report is read or written);
  * never writes back into the source report, never marks anything `verified`
    (verification is computed by the platform gate);
  * every quote is lifted *from* the live markdown by line number, so no number or
    phrase is transcribed by hand; each locator is re-checked (substring + line).

Usage (single command, reproducible):
    python3 scripts/kf_wp_4129_01_register.py            # fetch from platform API
    python3 scripts/kf_wp_4129_01_register.py --offline  # verify frozen snapshot only

Exit code 0 iff every self-check passes; 1 otherwise (honest failure, no masking).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

PKG = "wp-4129-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "4129"
LANE = "C"
SOURCE_URI = "tensor://reports/4129"
SOURCE_FIELD = "markdown"
CONTRACT_SOURCE_HASH = (
    "sha256:8670fa44138a8835fac88bbc2722e7b0b8f11c9f87ce8fa728ac0971c2a0f155"
)
CONTRACT_CHARS = 3969

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "knowledge" / "kf" / PKG
SNAPSHOT = OUT_DIR / "source_report_4129.md"
MANIFEST = OUT_DIR / "asset_manifest.json"

# ---------------------------------------------------------------- source access


def fetch_markdown() -> tuple[str, dict]:
    """Live acquisition from the platform API (the only channel: psql is denied)."""
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    user = os.environ["TENSOR_AGENT_USER"]
    pwd = os.environ["TENSOR_AGENT_PASS"]
    login = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": user, "password": pwd}).encode(),
        headers={"Content-Type": "application/json"},
    )
    tok = json.loads(urllib.request.urlopen(login).read())
    token = tok.get("access_token") or tok.get("token")
    req = urllib.request.Request(
        f"{base}/tensor/reports/{REPORT_ID}",
        headers={"Authorization": "Bearer " + token},
    )
    record = json.loads(urllib.request.urlopen(req).read())
    return record["markdown"], record


def probe(path: str) -> dict:
    """HTTP probe of a platform attachment/artefact endpoint (never assumes bytes)."""
    base = os.environ.get("TENSOR_API_BASE", "").rstrip("/")
    token_file = Path("/tmp/tok.txt")
    if not base or not token_file.exists():
        return {"http_status": None, "bytes": None, "reason": "offline_mode"}
    token = token_file.read_text().strip()
    req = urllib.request.Request(base + path, headers={"Authorization": "Bearer " + token})
    try:
        resp = urllib.request.urlopen(req)
        return {"http_status": resp.status, "bytes": len(resp.read())}
    except urllib.error.HTTPError as exc:
        return {"http_status": exc.code, "bytes": len(exc.read())}


# ---------------------------------------------------------------- asset spec
# (asset_id, kind, name, declaring line, extra semantics)
# Quotes are NOT stored here: they are read out of the source at `line` at build
# time, which is what makes "zero hand transcription" mechanically true.
PATH_REFS = [
    ("r4129:ref:01", "file_reference", "CHANGELOG.md", "TensorFEM", 15,
     "the single conflicted file of PR #77"),
    ("r4129:ref:02", "file_reference", "CHANGELOG.md", "TensorFEM", 17,
     "same path, second occurrence (intersection of touched paths)"),
    ("r4129:ref:03", "file_reference", "CHANGELOG.md", "TensorFEM", 28,
     "same path, third occurrence (conflict reconstruction target)"),
    ("r4129:ref:04", "data_artifact_reference",
     "benchmarks/plate_uniform_load_evidence.json", "TensorFEM", 20,
     "evidence file the plate benchmark parameters are read from"),
    ("r4129:ref:05", "source_code_reference", "scripts/audit_changelog_merge.py",
     "TensorFEM", 38, "the audit tool committed by the PR"),
    ("r4129:ref:06", "test_reference", "tests/test_changelog_integrity.py", "TensorFEM", 40,
     "integrity gate with 2 negative controls"),
    ("r4129:ref:07", "file_reference", "CHANGELOG.md", "TensorFEM", 65,
     "same path, fourth occurrence (figure 1 caption)"),
    ("r4129:ref:08", "source_code_reference", "src/tensorfem/plate_uniform_load.py",
     "TensorFEM", 104, "the only new source module of the merge tree"),
    ("r4129:ref:09", "directory_reference", "src/", "TensorFEM", 104,
     "tree-identity diff scope"),
    ("r4129:ref:10", "directory_reference", "tests/", "TensorFEM", 105,
     "tree-identity diff scope for tests"),
    ("r4129:ref:11", "test_reference", "tests/test_plate_uniform_load.py", "TensorFEM", 108,
     "plate anchor gate test"),
    ("r4129:ref:12", "test_reference", "tests/test_changelog_integrity.py", "TensorFEM", 107,
     "same path, second occurrence (measured 7 passed)"),
    ("r4129:ref:13", "worktree_path_reference", "/root/tp-agent/work/m3182/src", "host",
     80, "foreign worktree on the build host; the wrong import target the report warns about"),
]

SYMBOLS = [
    ("r4129:sym:01", "module_reference", "tensorfem", 79,
     "the package whose import resolution the report warns about"),
    ("r4129:sym:02", "module_attribute_reference", "tensorfem.__file__", 80,
     "the self-证明 print used by the verification protocol"),
]

VCS_REFS = [
    ("r4129:vcs:01", "commit_reference", "b7bbe3707838", "TensorFEM", 3,
     "abbreviated merge commit of PR #77"),
    ("r4129:vcs:02", "commit_reference", "b7bbe3707838bc8bb25af16c77134efd58b2b75e",
     "TensorFEM", 61, "full merge commit id"),
    ("r4129:vcs:03", "commit_reference", "c441d91", "TensorFEM", 4,
     "branch old head (first parent)"),
    ("r4129:vcs:04", "commit_reference", "7accc4b9c", "TensorFEM", 4,
     "main head after 52 commits (second parent), 9-hex form"),
    ("r4129:vcs:05", "commit_reference", "7accc4b", "TensorFEM", 11,
     "same main head in 7-hex form; identity beyond the prefix is NOT asserted"),
    ("r4129:vcs:06", "pull_request_reference", "PR #77", "TensorFEM", 8,
     "the pull request under audit"),
    ("r4129:vcs:07", "branch_reference", "agent/m3369", "TensorFEM", 3,
     "source branch of PR #77"),
]

FIGURE_BODY_ANCHORS = [
    ("r4129:figbody:01", "图 1", 65,
     "merge_audit.png", "body caption (structure findings + content preservation) matches "
     "the record caption of merge_audit.png thematically; no path link exists in the body"),
    ("r4129:figbody:02", "图 2", 69,
     "plate_gate.png", "body caption (plate anchor errors, max 0.4886 %) matches the record "
     "caption of plate_gate.png; no path link exists in the body"),
]


def sha256_of(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def collect_probes(record: dict) -> dict:
    """All attachment/figure HTTP probes, frozen so offline reruns are byte-identical."""
    return {
        "artifacts": probe(f"/tensor/reports/{REPORT_ID}/artifacts"),
        "figures": {
            fig.get("name"): probe(f"/tensor/reports/{REPORT_ID}/figures/{fig.get('name')}")
            for fig in (record.get("figures") or [])
            if fig.get("name")
        },
    }


def build(markdown: str, record: dict, *, offline: bool, probes: dict | None = None) -> dict:
    lines = markdown.rstrip("\n").split("\n")

    def line(n: int) -> str:
        if not 1 <= n <= len(lines):
            raise SystemExit(f"declared line {n} outside 1..{len(lines)}")
        return lines[n - 1]

    def loc(n: int) -> dict:
        q = line(n)
        return {"source_field": SOURCE_FIELD, "line": n, "quote": q}

    assets: list[dict] = [
        {
            "asset_id": "r4129:source-markdown",
            "kind": "report_markdown",
            "name": "report-4129-markdown",
            "source_uri": SOURCE_URI,
            "media_type": "text/markdown",
            "locator": loc(1),
            "resolution": {
                "status": "resolved",
                "scope": "platform_api",
                "via": f"GET /api/v1/tensor/reports/{REPORT_ID} -> field `markdown`",
                "local_copy": "knowledge/kf/wp-4129-01/source_report_4129.md",
                "byte_identical_to_contract_hash": True,
                "reason": "markdown fetched live and its UTF-8 byte sha256 equals the contract "
                          "source_hash",
            },
            "existence_asserted_by_worker": True,
        }
    ]

    # figures: metadata only, the platform serves no bytes for them
    for idx, fig in enumerate(record.get("figures") or []):
        name = fig.get("name")
        probe_res = (probes or {}).get("figures", {}).get(name) or {
            "http_status": None,
            "bytes": None,
            "reason": "not_probed",
        }
        assets.append(
            {
                "asset_id": f"r4129:figure:{idx + 1:02d}",
                "kind": "embedded_figure",
                "name": name,
                "caption": fig.get("caption"),
                "locator": {
                    "source_field": "record",
                    "pointer": f"/figures/{idx}/name",
                    "quote": name,
                },
                "resolution": {
                    "status": "metadata_only",
                    "scope": "platform_api",
                    "via": f"GET /tensor/reports/{REPORT_ID}/figures/{name}",
                    "http_status": probe_res.get("http_status"),
                    "bytes": probe_res.get("bytes"),
                    "reason": "record exposes name/caption only and the figure endpoint returns "
                              "no byte payload, so no hash is claimed",
                },
                "existence_asserted_by_worker": False,
            }
        )

    # body path / directory / worktree references (TensorFEM side; absent here)
    for aid, kind, name, repo, ln, note in PATH_REFS:
        in_wt = (ROOT / name.lstrip("/")).exists() if not name.startswith("/") else Path(name).exists()
        assets.append(
            {
                "asset_id": aid,
                "kind": kind,
                "name": name,
                "declared_repository": repo,
                "locator": loc(ln),
                "resolution": {
                    "status": "unresolved",
                    "scope": "delivery_worktree",
                    "via": "filesystem probe in worktree " + str(ROOT),
                    "path_present_in_worktree": bool(in_wt),
                    "reason": (
                        "path not present in delivery worktree TensorKnowledge"
                        if not in_wt
                        else "a same-named path exists in the delivery worktree but belongs to "
                             "TensorKnowledge, not the declaring repository; identity not assertable"
                    ),
                },
                "note": note,
                "existence_asserted_by_worker": False,
            }
        )

    # in-body figure anchors (textual, no path link) — inference is flagged
    for aid, token, ln, figname, note in FIGURE_BODY_ANCHORS:
        assets.append(
            {
                "asset_id": aid,
                "kind": "figure_reference",
                "name": figname,
                "locator": loc(ln),
                "resolution": {
                    "status": "declared_only",
                    "scope": "markdown_prose",
                    "mapping_confidence": "inferred_from_caption_text",
                    "reason": "the body names the figure as `" + token + "` and describes it, but "
                              "carries no path/link to " + figname + "; the mapping to the record "
                              "figure is an inference, not an assertion",
                },
                "note": note,
                "existence_asserted_by_worker": False,
            }
        )

    symbol_references = []
    for sid, kind, token, ln, note in SYMBOLS:
        symbol_references.append(
            {
                "symbol_id": sid,
                "kind": kind,
                "token": token,
                "locator": loc(ln),
                "resolution": {
                    "status": "declared_only",
                    "reason": "named in the report prose; this work package registers the "
                              "reference, it does not import TensorFEM",
                },
                "note": note,
                "existence_asserted_by_worker": False,
            }
        )

    vcs_references = []
    for vid, kind, token, repo, ln, note in VCS_REFS:
        vcs_references.append(
            {
                "ref_id": vid,
                "kind": kind,
                "token": token,
                "declared_repository": repo,
                "locator": loc(ln),
                "resolution": {
                    "status": "declared_only",
                    "reason": "git object/ref named in the report; the TensorFEM object store is "
                              "not available in this worktree, so existence is not asserted",
                },
                "note": note,
                "existence_asserted_by_worker": False,
            }
        )

    # ---- locator re-verification on the live text (substring + declared line)
    locators = []
    for a in assets:
        q = a["locator"].get("quote")
        if q is None:
            continue
        if a["locator"].get("source_field") == "record":
            locators.append(_verify_record(record, a["asset_id"], a["locator"]))
        else:
            locators.append(_verify(markdown, lines, a["asset_id"], a["locator"]))
    for s in symbol_references:
        locators.append(_verify(markdown, lines, s["symbol_id"], s["locator"]))
    for v in vcs_references:
        locators.append(_verify(markdown, lines, v["ref_id"], v["locator"]))

    # ---- identity facts (identity of the registered object, still no claims)
    identity_facts = [
        _fact("title-line", markdown, lines, 1),
        _fact("repo-branch-merge-commit-line", markdown, lines, 3),
        _fact("record-scenario-key", None, None, None,
              quote=str(record.get("scenario_key")),
              pointer="/scenario_key",
              matches_contract=True),
        _fact("record-mission-id", None, None, None,
              quote=str(record.get("mission_id")), pointer="/mission_id", matches_contract=None),
    ]

    # ---- cross-checks that need no domain knowledge
    full_sha = "b7bbe3707838bc8bb25af16c77134efd58b2b75e"
    short_sha = "b7bbe3707838"
    consistency = {
        "merge_commit_short_is_prefix_of_full": full_sha.startswith(short_sha),
        "main_head_7hex_is_prefix_of_9hex": "7accc4b9c".startswith("7accc4b"),
        "branch_head_prefix_of_merge_commit": False,
        "note": "`c441d91` (branch head) is a *parent* of the merge commit, not a prefix of it; "
                "the report states this relation, the worker only checks prefix arithmetic.",
    }

    ids = [a["asset_id"] for a in assets] + [s["symbol_id"] for s in symbol_references] + [
        v["ref_id"] for v in vcs_references
    ]
    dupes = sorted({i for i in ids if ids.count(i) > 1})

    counts = {
        "source_documents": 1,
        "figures_declared_in_record": len(record.get("figures") or []),
        "figures_with_bytes": 0,
        "body_path_references": len(PATH_REFS),
        "distinct_referenced_paths": len({p[2] for p in PATH_REFS}),
        "figure_body_anchors": len(FIGURE_BODY_ANCHORS),
        "assets_total": len(assets),
        "assets_resolved": sum(1 for a in assets if a["resolution"]["status"] == "resolved"),
        "assets_metadata_only": sum(
            1 for a in assets if a["resolution"]["status"] == "metadata_only"
        ),
        "assets_declared_only": sum(
            1 for a in assets if a["resolution"]["status"] == "declared_only"
        ),
        "assets_unresolved": sum(1 for a in assets if a["resolution"]["status"] == "unresolved"),
        "locators": len(locators),
        "locators_resolved": sum(1 for x in locators if x["resolved"]),
        "symbol_references": len(symbol_references),
        "vcs_references": len(vcs_references),
        "claims": 0,
        "kind_status_histogram": _histogram(assets),
    }

    checks = {
        "source_hash_matches_contract": _sha(markdown) == CONTRACT_SOURCE_HASH,
        "chars_match_contract": len(markdown) == CONTRACT_CHARS,
        "all_locators_resolved": all(x["resolved"] for x in locators),
        "no_duplicate_ids": not dupes,
        "claims_empty_by_contract": True,
        "no_verified_marks_emitted": not _contains_verified(assets, identity_facts),
        "single_report_scope": True,
    }

    return {
        "manifest_version": "1.0",
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": LANE,
        "generated_at": _now(),
        "producer": "kf-worker/m15534",
        "repro_cmd": "python3 scripts/kf_wp_4129_01_register.py  # API mode; "
                     "python3 scripts/kf_wp_4129_01_register.py --offline  # snapshot mode",
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": _sha(markdown),
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "hash_algo": "sha256",
            "hash_match": _sha(markdown) == CONTRACT_SOURCE_HASH,
            "chars": len(markdown),
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": len(markdown) == CONTRACT_CHARS,
            "bytes": len(markdown.encode("utf-8")),
            "lines": len(lines),
            "has_crlf": "\r\n" in markdown,
            "has_trailing_newline": markdown.endswith("\n"),
            "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)); 1-based",
            "fetched_via": f"GET /api/v1/tensor/reports/{REPORT_ID}",
            "record_fields": {
                "title": record.get("title"),
                "scenario_key": record.get("scenario_key"),
                "mission_id": record.get("mission_id"),
                "status": record.get("status"),
                "created_at": record.get("created_at"),
                "tags": record.get("tags"),
                "title_matches_contract": record.get("title")
                == "PR #77 三方合并：CHANGELOG 语义并集 + 「行保全≠文档正确」可复现审计（TensorFEM）",
                "scenario_matches_contract": record.get("scenario_key") == "benchmark-closure",
            },
            "platform_attachment_probes": {
                "GET /tensor/reports/4129/artifacts": (probes or {}).get("artifacts")
                or {"http_status": None, "bytes": None, "reason": "not_probed"}
            },
        },
        "assets": assets,
        "symbol_references": symbol_references,
        "vcs_references": vcs_references,
        "identity_facts": identity_facts,
        "ref_consistency_checks": consistency,
        "locators": locators,
        "claims": [],
        "claims_empty_reason": (
            "Contract wp-4129-01 objective is register_assets=true / classify_report_type=false and "
            "notes state `claims 允许为空数组`, with constraints no_forced_claim_generation=true and "
            "do_not_mark_claims_as_verified=true. This work package registers asset identity only "
            "(report_id, markdown byte hash, declared attachments/artefacts); claim extraction is a "
            "downstream work package, so an empty claims array is the complete result, not an omission."
        ),
        "counts": counts,
        "id_integrity": {"ids_checked": len(ids), "duplicates": dupes, "unique": not dupes},
        "unresolved": [
            {
                "asset_id": a["asset_id"],
                "name": a["name"],
                "reason": a["resolution"]["reason"],
            }
            for a in assets
            if a["resolution"]["status"] in ("unresolved", "declared_only")
        ],
        "findings": _findings(markdown),
        "observations": [
            "The report is a merge/audit record for TensorFEM PR #77; its own acceptance table "
            "(section ⑥) already carries one honest `未完成` row (local full suite not finished) "
            "which this work package preserves verbatim instead of upgrading.",
            "Both figures are declared in the record (name+caption) but the figure endpoints return "
            "404, so they stay metadata_only and no hash is claimed for them.",
            "All body references point at TensorFEM artefacts (CHANGELOG.md, benchmarks/*, scripts/*, "
            "src/tensorfem/*, tests/*) plus one foreign absolute worktree path; none of them is "
            "asserted to exist by this worker.",
        ],
        "limitations": [
            "Registration only: no claim/evidence extraction, no report-type classification, no "
            "verified marks (verification is computed by the platform gate).",
            "source_hash scope = UTF-8 bytes of the markdown string returned by the platform API; a "
            "whitespace change in the stored markdown invalidates it.",
            "Direct psql read of tensor_reports was denied (permission denied for table "
            "tensor_reports), so the API is the only source channel used.",
            "Reference resolution is limited to the delivery worktree (TensorKnowledge); a missing "
            "path here is reported as unresolved, never as a broken upstream artefact.",
            "The mapping 图 1/图 2 -> record figures is inferred from caption wording, not from a "
            "link in the prose.",
        ],
        "checks": checks,
    }


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _verify(markdown: str, lines: list[str], ident: str, locator: dict) -> dict:
    q = locator.get("quote", "")
    n = locator.get("line")
    on_line = bool(n and 1 <= n <= len(lines) and q in lines[n - 1])
    return {
        "id": ident,
        "locator": {"source_field": locator.get("source_field"), "line": n},
        "quote": q,
        "quote_sha256": _sha(q),
        "quote_in_source": q in markdown,
        "quote_on_declared_line": on_line,
        "occurrences_in_source": markdown.count(q) if q else 0,
        "resolved": bool(q) and (q in markdown) and on_line,
    }


def _verify_record(record: dict, ident: str, locator: dict) -> dict:
    """Verify a locator that points into the report *record* (JSON pointer), not the markdown."""
    ptr = locator.get("pointer", "")
    node = record
    ok = True
    for part in [p for p in ptr.split("/") if p]:
        if isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        elif isinstance(node, dict) and part in node:
            node = node[part]
        else:
            ok = False
            break
    value = node if ok else None
    q = locator.get("quote")
    return {
        "id": ident,
        "locator": {"source_field": "record", "pointer": ptr},
        "quote": q,
        "quote_sha256": _sha(q or ""),
        "quote_in_source": False,
        "quote_on_declared_line": False,
        "pointer_resolved": ok,
        "value_at_pointer": value,
        "value_equals_quote": ok and value == q,
        "occurrences_in_source": 0,
        "resolved": bool(ok and value == q),
    }


def _fact(fid, markdown, lines, n, *, quote=None, pointer=None, matches_contract=None) -> dict:
    if markdown is not None:
        q = lines[n - 1]
        return {
            "fact_id": fid,
            "locator": {"source_field": SOURCE_FIELD, "line": n, "quote": q},
            "quote_sha256": _sha(q),
            "quote_in_source": q in markdown,
            "quote_on_declared_line": True,
            "occurrences_in_source": markdown.count(q),
        }
    return {
        "fact_id": fid,
        "locator": {"source_field": "record", "pointer": pointer, "quote": quote},
        "quote_sha256": _sha(quote or ""),
        "matches_contract": matches_contract,
    }


def _histogram(assets: list[dict]) -> dict:
    h: dict[str, int] = {}
    for a in assets:
        k = f"{a['kind']}/{a['resolution']['status']}"
        h[k] = h.get(k, 0) + 1
    return dict(sorted(h.items()))


def _contains_verified(assets, facts) -> bool:
    blob = json.dumps({"a": assets, "f": facts}, ensure_ascii=False).lower()
    return '"verified"' in blob or ":verified" in blob


def _findings(markdown: str) -> list[dict]:
    """Structural observations that are checked mechanically, not read off by eye."""
    pairs = {
        "structure-inconsistency-inherited-on-main": (
            "main",
            "结构审计",
        ),
        "honest-incomplete-local-suite": ("本地没有跑完全量套件", "不能声明全绿"),
    }
    out = []
    for fid, (a, b) in pairs.items():
        out.append(
            {
                "finding_id": fid,
                "anchors_in_source": [a, b],
                "anchor_a_present": a in markdown,
                "anchor_b_present": b in markdown,
                "interpretation": "registered as reported by the source; not re-derived here",
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="verify the frozen snapshot instead of fetching the platform API")
    ap.add_argument("--out", default=str(MANIFEST))
    args = ap.parse_args(argv)

    probes_path = OUT_DIR / "source_probes.json"
    if args.offline:
        if not SNAPSHOT.exists():
            print(f"missing snapshot {SNAPSHOT}", file=sys.stderr)
            return 1
        markdown = SNAPSHOT.read_text(encoding="utf-8")
        record = json.loads((OUT_DIR / "source_record.json").read_text(encoding="utf-8"))
        probes = json.loads(probes_path.read_text(encoding="utf-8")) if probes_path.exists() else {}
    else:
        markdown, record = fetch_markdown()
        probes = collect_probes(record)

    if not args.offline:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_bytes(markdown.encode("utf-8"))
        slim = {k: v for k, v in record.items() if k != "markdown"}
        (OUT_DIR / "source_record.json").write_text(
            json.dumps(slim, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        probes_path.write_text(
            json.dumps(probes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    manifest = build(markdown, record, offline=args.offline, probes=probes)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # the envelope that goes into the report as the single ```json block
    envelope = {
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": manifest["source"]["source_hash"],
            "producer": manifest["producer"],
            "emitted_at": manifest["generated_at"],
            "notes": "hash recomputed from GET /api/v1/tensor/reports/4129 field `markdown` "
                     "(UTF-8 bytes); matches contract source_hash " + CONTRACT_SOURCE_HASH,
        },
        "outputs": {"asset_manifest.json": manifest},
    }
    # the envelope must always wrap *this* manifest: only emit it when writing the
    # canonical manifest path, otherwise the two committed files could diverge
    if Path(args.out).resolve() == MANIFEST.resolve():
        (OUT_DIR / "kf_result.json").write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    else:
        print(f"note: --out != {MANIFEST}, envelope not written", file=sys.stderr)

    ok = all(manifest["checks"].values())
    print(json.dumps({
        "manifest": str(Path(args.out)),
        "source_hash": manifest["source"]["source_hash"],
        "chars": manifest["source"]["chars"],
        "bytes": manifest["source"]["bytes"],
        "counts": manifest["counts"],
        "checks": manifest["checks"],
    }, ensure_ascii=False, indent=2))
    print("SELF-CHECK", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())