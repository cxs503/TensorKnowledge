#!/usr/bin/env python3
"""wp-5559-04 · independent review of upstream package wp-5559-01 (01-asset-registration).

Reviewer-side verifier. Written from the work-package contract + schemas only; the
producer's own scripts are NOT imported or read. Every number below is recomputed
from (a) the report markdown the reviewer fetched independently from
GET /api/v1/tensor/reports/5559 and (b) the upstream manifest JSON.

Usage:
    python3 work/wp-5559-04/verify_upstream_ko.py \
        --source work/wp-5559-04/source_5559.md \
        --manifest knowledge/kf/wp-5559-01/asset_manifest.json \
        --upstream-result knowledge/kf/wp-5559-01/kf_result.json \
        --out work/wp-5559-04/review_checks.json

Exit code 0 = no blocking finding, 1 = at least one blocking finding.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

CONTRACT_SOURCE_HASH = "sha256:3b04e96a056a9d8ba1b7861452dd5c2b3ce74777654154c7cc91e41f4e0b74ed"
CONTRACT_CHARS = 9257
CONTRACT_REPORT_ID = "5559"


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def check_source(source_path: Path, manifest: dict, prov: dict) -> dict:
    raw = source_path.read_bytes()
    text = raw.decode("utf-8")
    h = sha256_hex(raw)
    src = manifest.get("source", {})
    return {
        "check": "source_identity",
        "reviewer_recomputed_sha256": "sha256:" + h,
        "contract_source_hash": CONTRACT_SOURCE_HASH,
        "manifest_source_hash": src.get("source_hash"),
        "upstream_result_source_hash": prov.get("source_hash"),
        "hash_equals_contract": ("sha256:" + h) == CONTRACT_SOURCE_HASH,
        "manifest_hash_equals_contract": src.get("source_hash") == CONTRACT_SOURCE_HASH,
        "result_hash_equals_contract": prov.get("source_hash") == CONTRACT_SOURCE_HASH,
        "bytes": len(raw),
        "chars": len(text),
        "contract_chars": CONTRACT_CHARS,
        "chars_equal_contract": len(text) == CONTRACT_CHARS,
        "manifest_chars": src.get("chars"),
        "manifest_chars_match": src.get("chars") == len(text),
        "manifest_bytes_match": src.get("bytes") == len(raw),
        "manifest_lines_match": src.get("lines") == len(text.splitlines()),
        "has_crlf": "\r\n" in text,
        "manifest_has_crlf_flag": src.get("has_crlf"),
        "report_id_in_manifest": manifest.get("report_id"),
        "single_report_scope": manifest.get("report_id") == CONTRACT_REPORT_ID,
    }, text


def resolve_pointer(obj, pointer: str):
    """RFC6901-ish resolution of /a/0/b against a JSON object; None if absent."""
    cur = obj
    for tok in [t for t in pointer.split("/") if t != ""]:
        tok = tok.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, list):
            if not tok.isdigit() or int(tok) >= len(cur):
                return None
            cur = cur[int(tok)]
        elif isinstance(cur, dict):
            if tok not in cur:
                return None
            cur = cur[tok]
        else:
            return None
    return cur


def check_locators(text: str, manifest: dict, record: dict | None = None) -> dict:
    """Re-resolve every locator from scratch.

    Two locator classes exist: markdown char-span locators (quote is a string, must be
    a verbatim substring) and record JSON-pointer locators (quote may be a non-string
    scalar, must equal the value at the pointer). Both are checked independently here.
    """
    locs = manifest.get("locators", [])
    md = [l for l in locs if (l.get("locator") or {}).get("source_field") == "markdown"]
    rec = [l for l in locs if (l.get("locator") or {}).get("source_field") == "record"]
    other = [l for l in locs if l not in md and l not in rec]

    not_found, bad_sha, bad_occ, bad_slice, nfc_only = [], [], [], [], []
    norm = unicodedata.normalize("NFC", text)
    for l in md:
        q = l.get("quote")
        if not isinstance(q, str) or not q:
            not_found.append({"id": l.get("id"), "why": "quote_not_a_string"})
            continue
        if q not in text:
            why = "nfc_only" if q and unicodedata.normalize("NFC", q) in norm else "not_found"
            (nfc_only if why == "nfc_only" else not_found).append({"id": l.get("id"), "why": why})
            continue
        if ("sha256:" + sha256_hex(q.encode("utf-8"))) != l.get("quote_sha256"):
            bad_sha.append(l.get("id"))
        occ = text.count(q)
        if occ != l.get("occurrences_in_source"):
            bad_occ.append({"id": l.get("id"), "reviewer": occ, "manifest": l.get("occurrences_in_source")})
        loc = l.get("locator") or {}
        cs, ce = loc.get("char_start"), loc.get("char_end")
        if isinstance(cs, int) and isinstance(ce, int):
            if text[cs:ce] != q:
                bad_slice.append({"id": l.get("id"), "slice": text[cs:ce][:40], "quote": q[:40]})
            elif loc.get("line") is not None:
                line_no = text.count("\n", 0, cs) + 1
                if line_no != loc.get("line"):
                    bad_slice.append({"id": l.get("id"), "why": "line_mismatch",
                                      "reviewer_line": line_no, "manifest_line": loc.get("line")})
        else:
            bad_slice.append({"id": l.get("id"), "why": "missing_offsets"})

    bad_ptr, rec_unverifiable = [], []
    for l in rec:
        ptr = (l.get("locator") or {}).get("pointer")
        if record is None:
            rec_unverifiable.append(l.get("id"))
            continue
        val = resolve_pointer(record, ptr)
        if val is None:
            bad_ptr.append({"id": l.get("id"), "pointer": ptr, "why": "pointer_unresolved"})
            continue
        if val != l.get("quote"):
            bad_ptr.append({"id": l.get("id"), "pointer": ptr, "reviewer": val, "quote": l.get("quote")})
        q = l.get("quote")
        qb = q.encode("utf-8") if isinstance(q, str) else json.dumps(q).encode("utf-8")
        if ("sha256:" + sha256_hex(qb)) != l.get("quote_sha256"):
            bad_sha.append(l.get("id") + "(record)")

    return {
        "check": "locators_resolved_independently",
        "locators_total": len(locs),
        "markdown_locators": len(md),
        "record_locators": len(rec),
        "other_locators": len(other),
        "not_found_in_source": not_found + nfc_only,
        "quote_sha256_mismatch": bad_sha,
        "occurrence_count_mismatch": bad_occ,
        "char_slice_or_line_mismatch": bad_slice,
        "record_pointer_mismatch": bad_ptr,
        "record_locators_unverifiable_without_record": rec_unverifiable,
        "all_quotes_verbatim": not (not_found or nfc_only),
        "all_shas_match": not bad_sha,
        "all_occurrences_match": not bad_occ,
        "all_char_slices_match": not bad_slice,
        "all_record_pointers_match": not bad_ptr,
        "manifest_resolved_true": sum(1 for l in locs if l.get("resolved")),
    }


NUM_TOKEN = re.compile(r"(?<![0-9A-Za-z_.])([0-9]+(?:\.[0-9]+)?)(?:[eE]([+-]?[0-9]+))?(?![0-9A-Za-z_])")


def _numeric_closure(text: str) -> set[float]:
    """Every number that literally appears in the source, plus simple re-forms."""
    out: set[float] = set()
    for m in NUM_TOKEN.finditer(text):
        mant, exp = m.group(1), m.group(2)
        try:
            val = float(mant) * (10.0 ** int(exp)) if exp else float(mant)
        except (ValueError, OverflowError):
            continue
        out.add(val)
    return out


def check_assets(text: str, manifest: dict) -> dict:
    assets = manifest.get("assets", [])
    ids = [a.get("asset_id") for a in assets]
    kinds: dict[str, int] = {}
    status: dict[str, int] = {}
    for a in assets:
        kinds[a.get("kind")] = kinds.get(a.get("kind"), 0) + 1
        st = (a.get("resolution") or {}).get("status")
        status[st] = status.get(st, 0) + 1
    stated = manifest.get("counts", {})
    id_re = re.compile(r"^[A-Za-z0-9_.:\-]+$")
    bad_ids = [i for i in ids if not isinstance(i, str) or not id_re.match(i)]
    # every registered asset must point at this report and at a markdown locator
    wrong_uri = [a.get("asset_id") for a in assets if a.get("source_uri") != "tensor://reports/5559"]
    res_ok = [a.get("asset_id") for a in assets if (a.get("resolution") or {}).get("status") in {"resolved"}]
    return {
        "check": "assets_and_counts",
        "assets_total_manifest": stated.get("assets_total"),
        "assets_len_reviewer": len(assets),
        "assets_total_matches": stated.get("assets_total") == len(assets),
        "by_kind_recomputed": kinds,
        "by_kind_stated": stated.get("by_kind"),
        "by_kind_matches": kinds == stated.get("by_kind"),
        "by_status_recomputed": status,
        "by_status_stated": stated.get("by_status"),
        "by_status_matches": status == stated.get("by_status"),
        "kinds_sum": sum(kinds.values()),
        "status_sum": sum(status.values()),
        "duplicate_ids": len(ids) - len(set(ids)),
        "ids_manifest_duplicates": (manifest.get("id_integrity") or {}).get("duplicates"),
        "malformed_ids": bad_ids,
        "assets_with_wrong_source_uri": wrong_uri,
        "assets_with_resolved_status": len(res_ok),
        "declared_parameters_stated": stated.get("declared_parameters"),
        "declared_parameters_recomputed": kinds.get("declared_parameter"),
    }


def check_figures_and_digests(text: str, manifest: dict) -> dict:
    body_imgs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
    record_figs = ((manifest.get("source", {}).get("record_fields") or {}).get("tags") is not None)
    declared = manifest.get("counts", {})
    fig_numeric = manifest.get("ref_consistency_checks", [])
    setcheck = next((c for c in fig_numeric if c.get("check") == "body_vs_record_figure_sets"), {})
    return {
        "check": "figures",
        "body_figure_links_reviewer": [p.rsplit("/", 1)[-1] for p in body_imgs],
        "body_figure_count_reviewer": len(body_imgs),
        "manifest_figures_in_body": declared.get("figures_in_body"),
        "manifest_figures_in_record": declared.get("figures_in_record"),
        "manifest_figures_with_bytes": declared.get("figures_with_bytes"),
        "figures_in_body_matches": declared.get("figures_in_body") == len(body_imgs),
        "manifest_records_set_mismatch": setcheck.get("consistent") is False,
        "record_figs_declared": record_figs,
        "caption_present_for": sum(1 for n in [p.rsplit("/", 1)[-1] for p in body_imgs] if n in text),
    }


def check_digest_prose(text: str, manifest: dict) -> dict:
    """The prose/table show truncated digests; the fenced json shows the full one."""
    full = re.findall(r"\b[0-9a-f]{64}\b", text)
    trunc16 = re.findall(r"\b[0-9a-f]{16}\b", text)
    m = re.search(r"```json\n(.*?)\n```", text, re.S)
    embedded_parsed = None
    embedded_digest = None
    if m:
        try:
            embedded_parsed = json.loads(m.group(1))
            embedded_digest = embedded_parsed.get("digest")
        except json.JSONDecodeError:
            embedded_parsed = "PARSE_ERROR"
    # only the field digest is supposed to agree with the embedded json; artifact hashes
    # are file digests whose full values are not in the record at all
    ell = re.findall(r"`([0-9a-f]{8,64})…`", text)
    field_prefixes = [p for p in ell if embedded_digest and embedded_digest.startswith(p)]
    undeclared = [p for p in ell if not (embedded_digest and embedded_digest.startswith(p))]
    prefixes_ok = [{"prefix": p, "is_prefix_of_embedded": True} for p in sorted(set(field_prefixes))]
    return {
        "check": "embedded_json_and_digests",
        "embedded_json_blocks": len(re.findall(r"```json", text)),
        "embedded_json_parsed": embedded_parsed is not None and embedded_parsed != "PARSE_ERROR",
        "embedded_digest_full_hex": bool(embedded_digest and re.fullmatch(r"[0-9a-f]{64}", embedded_digest)),
        "full_hex64_occurrences": len(full),
        "field_digest_prefixes_ok": prefixes_ok,
        "truncated_prefixes_not_in_field_digest": sorted(set(undeclared)),
        "truncated_prefix_count": len(set(undeclared)),
        "all_field_prefixes_consistent": all(p["is_prefix_of_embedded"] for p in prefixes_ok),
        "artifact_digests_resolvable_from_record": False,
        "manifest_embedded_json_asset": any(a.get("kind") == "embedded_json_reference" for a in manifest.get("assets", [])),
    }


def check_verification_language(manifest: dict, upstream_result: dict) -> dict:
    blob = json.dumps([manifest, upstream_result], ensure_ascii=False)
    forbidden = ["\"verified\": true", "\"verified_by\"", "marked_verified", "\"status\": \"verified\""]
    hits = [f for f in forbidden if f in blob]
    claims = upstream_result.get("claims")
    verified_in_verdict = re.findall(r"\"verdict\":\s*\"([^\"]+)\"", blob)
    return {
        "check": "no_verified_marks",
        "forbidden_token_hits": hits,
        "claims_array": claims,
        "claims_len": 0 if claims is None else len(claims),
        "verdict_tokens": verified_in_verdict,
        "manifest_no_verified_marks_flag": (manifest.get("checks") or {}).get("no_verified_marks_emitted"),
    }


def check_result_envelope_equal(manifest_path: Path, upstream_result: dict) -> dict:
    out = upstream_result.get("outputs") or {}
    embedded = out.get("asset_manifest.json")
    on_disk = load_json(manifest_path)
    prov = upstream_result.get("provenance") or {}
    return {
        "check": "result_envelope",
        "outputs_keys": sorted(out.keys()),
        "embedded_equals_file_on_disk": embedded == on_disk,
        "package_id": upstream_result.get("package_id"),
        "task_type": upstream_result.get("task_type"),
        "report_id": upstream_result.get("report_id"),
        "source_field": prov.get("source_field"),
        "producer": prov.get("producer"),
        "outputs_contains_review_report": "review_report.json" in out,
    }


SCHEMA_REQUIRED = ["package_id", "task_type", "report_id", "provenance", "outputs"]
SCHEMA_ALLOWED = set(SCHEMA_REQUIRED) | {"claims"}


def check_result_schema(upstream_result: dict) -> dict:
    """Minimal structural check of schemas/kf_result.v1.schema.json constraints."""
    errs = []
    for k in SCHEMA_REQUIRED:
        if k not in upstream_result:
            errs.append(f"missing:{k}")
    extra = set(upstream_result) - SCHEMA_ALLOWED
    if extra:
        errs.append(f"additionalProperties:{sorted(extra)}")
    if not re.match(r"^wp-[A-Za-z0-9][A-Za-z0-9_.:-]*-[0-9]{2}$", str(upstream_result.get("package_id"))):
        errs.append("package_id_pattern")
    if not re.match(r"^[0-9]{2}(-[a-z0-9-]+)?$", str(upstream_result.get("task_type"))):
        errs.append("task_type_pattern")
    if not re.match(r"^[0-9]+$", str(upstream_result.get("report_id"))):
        errs.append("report_id_pattern")
    prov = upstream_result.get("provenance") or {}
    if not re.match(r"^sha256:[0-9a-f]{64}$", str(prov.get("source_hash"))):
        errs.append("source_hash_pattern")
    if prov.get("source_field") not in {"markdown", "summary", "record"}:
        errs.append("source_field_enum")
    outs = upstream_result.get("outputs") or {}
    if not outs:
        errs.append("outputs_empty")
    return {"check": "kf_result_schema", "errors": errs, "schema_pass": not errs}


def check_numeric_closure(text: str, manifest: dict) -> dict:
    """Every number the manifest re-states must be locatable in the source text."""
    nums = _numeric_closure(text)
    offenders = []

    def visit(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                visit(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                visit(v, f"{path}[{i}]")
        elif isinstance(node, float):
            exact = any(abs(node - x) <= 1e-12 * max(1.0, abs(node)) for x in nums)
            # a derived value is acceptable when it rounds to a number that is in the
            # source text at the precision the source displays it (e.g. 2.048 -> 2.05)
            rounded = any(round(x, nd) == round(node, nd) for x in nums for nd in range(0, 7))
            if not (exact or rounded):
                offenders.append({"path": path, "value": node})
            elif not exact:
                offenders.append({"path": path, "value": node, "kind": "derived_rounding_consistent"})

    for key in ("ref_consistency_checks", "counts"):
        visit(manifest.get(key, {}), key)
    # floats inside locator/asset notes are prose, not measurements -> skipped on purpose
    return {
        "check": "numeric_closure_of_restated_numbers",
        "scope": "manifest.ref_consistency_checks + manifest.counts",
        "offenders": offenders[:40],
        "offender_count": len(offenders),
        "unexplained": [o for o in offenders if o.get("kind") != "derived_rounding_consistent"],
        "closed": not [o for o in offenders if o.get("kind") != "derived_rounding_consistent"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="work/wp-5559-04/source_5559.md")
    ap.add_argument("--manifest", default="knowledge/kf/wp-5559-01/asset_manifest.json")
    ap.add_argument("--upstream-result", default="knowledge/kf/wp-5559-01/kf_result.json")
    ap.add_argument("--record", default="work/wp-5559-04/record_5559.json")
    ap.add_argument("--out", default="work/wp-5559-04/review_checks.json")
    a = ap.parse_args()

    src_path, man_path = Path(a.source), Path(a.manifest)
    text = src_path.read_text(encoding="utf-8")
    manifest = load_json(man_path)
    upstream = load_json(Path(a.upstream_result))
    record_path = Path(a.record)
    record = load_json(record_path) if record_path.exists() else None

    src_chk, text = check_source(src_path, manifest, upstream.get("provenance") or {})
    checks = [
        src_chk,
        check_locators(text, manifest, record),
        check_assets(text, manifest),
        check_figures_and_digests(text, manifest),
        check_digest_prose(text, manifest),
        check_verification_language(manifest, upstream),
        check_result_envelope_equal(man_path, upstream),
        check_result_schema(upstream),
        check_numeric_closure(text, manifest),
    ]

    blocking = []
    if not src_chk["hash_equals_contract"] or not src_chk["manifest_hash_equals_contract"]:
        blocking.append("source_hash_mismatch")
    if not src_chk["chars_equal_contract"]:
        blocking.append("chars_mismatch")
    lc = checks[1]
    if (lc["not_found_in_source"] or lc["char_slice_or_line_mismatch"] or lc["quote_sha256_mismatch"]
            or lc["record_pointer_mismatch"] or lc["occurrence_count_mismatch"]):
        blocking.append("locator_unresolvable")
    ac = checks[2]
    if not ac["by_kind_matches"] or not ac["by_status_matches"] or ac["duplicate_ids"]:
        blocking.append("count_inconsistency")
    env = checks[6]
    if not env["embedded_equals_file_on_disk"]:
        blocking.append("envelope_manifest_diverges_from_file")
    sch = checks[7]
    if not sch["schema_pass"]:
        blocking.append("schema_fail")
    vf = checks[5]
    if vf["forbidden_token_hits"]:
        blocking.append("verified_mark_emitted")

    payload = {
        "reviewer": "kf-worker/wp-5559-04",
        "reviewed_package": upstream.get("package_id"),
        "report_id": upstream.get("report_id"),
        "source_sha256_reviewer": src_chk["reviewer_recomputed_sha256"],
        "checks": checks,
        "blocking_findings": blocking,
        "verdict": "pass" if not blocking else "needs-fix",
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "checks"}, ensure_ascii=False, indent=2))
    for c in checks:
        print("--", c["check"], json.dumps({k: v for k, v in c.items() if k != "check"}, ensure_ascii=False)[:600])
    return 0 if not blocking else 1


if __name__ == "__main__":
    sys.exit(main())