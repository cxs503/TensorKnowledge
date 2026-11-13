#!/usr/bin/env python3
"""Independent verification for KF work package wp-8240-01 (report_id=8240).

Re-derives every acceptance item of the package contract from the source
markdown and the emitted artifacts instead of trusting the generator:

  valid_json            -> json.loads on manifest + envelope
  schema_pass           -> jsonschema against schemas/asset_manifest.v1.1.schema.json
                           and schemas/kf_result.v1.schema.json
  source_locator_resolvable -> every locator.quote is a substring of the markdown,
                           occurs exactly once, and (method=char_span) the char span
                           reproduces it and sits inside the declared line span
  source_hash_matches   -> sha256(markdown) == contract source_hash; optional second,
                           independent read through the platform API (TENSOR_TOKEN)
  no_duplicate_ids      -> unique asset ids, and envelope/manifest id consistency
  all_claims_have_evidence_or_explicit_unresolved_status
                        -> per-claim rule; count reported (0 == vacuously satisfied,
                           reported as such, not as "checked")

Also checks report_id isolation (no other report_id path touched) and that the
durable docs/ mirror is byte-identical to artifacts/ and runs/ outputs.

Usage: python3 scripts/kf_verify_8240.py            (offline, uses cached payload)
       TENSOR_TOKEN=... python3 scripts/kf_verify_8240.py   (adds API re-read)
Exit code 0 iff every check passes.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.request

import jsonschema

REPORT_ID = "8240"
PACKAGE_ID = "wp-8240-01"
SOURCE_HASH = "113b007338c90e984af4be66352aae382cd90f7e976725e819825a95bfa46e7d"
SOURCE_CHARS = 9689

RUN_DIR = pathlib.Path(f"runs/{PACKAGE_ID}")
ART = pathlib.Path(f"artifacts/{PACKAGE_ID}/asset_manifest.json")
DOC = pathlib.Path(f"docs/{PACKAGE_ID}/asset_manifest.json")
ENV_RUN = RUN_DIR / f"kf_result.{PACKAGE_ID}.json"
ENV_DOC = pathlib.Path(f"docs/{PACKAGE_ID}/kf_result.{PACKAGE_ID}.json")
MD = RUN_DIR / f"report_{REPORT_ID}.md"

results: dict[str, dict] = {}


def record(name: str, ok: bool, detail, blocking: bool = True) -> None:
    results[name] = dict(passed=bool(ok), detail=detail, blocking=blocking)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def main() -> int:
    md = MD.read_text()
    manifest = json.loads(ART.read_text())
    envelope = json.loads(ENV_RUN.read_text())

    # --- valid_json -------------------------------------------------------
    try:
        json.loads(ART.read_text()), json.loads(ENV_RUN.read_text())
        record("valid_json", True, f"{ART} and {ENV_RUN} parse as JSON")
    except Exception as exc:  # pragma: no cover
        record("valid_json", False, repr(exc))
        raise

    # --- schema_pass ------------------------------------------------------
    schema_errs = []
    try:
        jsonschema.validate(manifest, json.loads(
            pathlib.Path("schemas/asset_manifest.v1.1.schema.json").read_text()))
    except jsonschema.ValidationError as exc:
        schema_errs.append(f"asset_manifest: {exc.message} at {list(exc.absolute_path)}")
    try:
        jsonschema.validate(envelope, json.loads(
            pathlib.Path("schemas/kf_result.v1.schema.json").read_text()))
    except jsonschema.ValidationError as exc:
        schema_errs.append(f"kf_result: {exc.message} at {list(exc.absolute_path)}")
    record("schema_pass", not schema_errs,
           schema_errs or "manifest vs asset_manifest.v1.1, envelope vs kf_result.v1: valid")

    # --- source_hash_matches (local) --------------------------------------
    local_hash = sha256_text(md)
    record("source_hash_matches_local",
           local_hash == SOURCE_HASH and manifest["source"]["hash"] == SOURCE_HASH
           and envelope["provenance"]["source_hash"] == "sha256:" + SOURCE_HASH
           and len(md) == SOURCE_CHARS == manifest["source"]["chars"],
           dict(local_sha256=local_hash, contract=SOURCE_HASH, chars=len(md),
                expected_chars=SOURCE_CHARS))

    # --- source_hash_matches (independent API re-read) --------------------
    token = os.environ.get("TENSOR_TOKEN")
    if not token:
        record("source_hash_matches_api", False,
               "not_run: TENSOR_TOKEN not set, no independent API re-read", blocking=False)
    else:
        base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
        req = urllib.request.Request(f"{base}/tensor/reports/{REPORT_ID}",
                                     headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            api = json.loads(r.read().decode())
        api_md = api.get("markdown") or ""
        api_hash = sha256_text(api_md)
        record("source_hash_matches_api",
               api_hash == SOURCE_HASH and api_md == md
               and str(api.get("id")) == REPORT_ID,
               dict(api_sha256=api_hash, same_bytes_as_cached=api_md == md,
                    api_id=api.get("id"), api_title=api.get("title")))

    # --- source_locator_resolvable ---------------------------------------
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1

    def line_of(char: int) -> int:
        i = 0
        while i + 1 < len(offs) and offs[i + 1] <= char:
            i += 1
        return i

    loc_errs, checked = [], 0
    for a in manifest["assets"]:
        checked += 1
        loc, aid = a["locator"], a["asset_id"]
        q = loc["quote"]
        if not q:
            loc_errs.append(f"{aid}: empty quote")
            continue
        n = md.count(q)
        if n == 0:
            loc_errs.append(f"{aid}: quote not found in source markdown")
            continue
        if n != 1:
            loc_errs.append(f"{aid}: quote occurs {n} times (not unique)")
        if not loc["unique"]:
            loc_errs.append(f"{aid}: locator.unique=false")
        if not (0 <= loc["start_char"] < loc["end_char"] <= len(md)):
            loc_errs.append(f"{aid}: char span out of bounds")
            continue
        if loc["method"] == "char_span":
            if md[loc["start_char"]:loc["end_char"]] != q:
                loc_errs.append(f"{aid}: char span does not reproduce quote")
            s, e = line_of(loc["start_char"]), line_of(loc["end_char"] - 1)
            if (s, e) != (loc["start_line"], loc["end_line"]):
                loc_errs.append(f"{aid}: line span {loc['start_line']}..{loc['end_line']} "
                                f"!= offsets imply {s}..{e}")
        else:
            if (loc["start_char"], loc["end_char"]) != (0, len(md)):
                loc_errs.append(f"{aid}: document locator span != whole document")
    record("source_locator_resolvable", not loc_errs,
           loc_errs or f"{checked} locators resolved: verbatim + unique + span-consistent")

    # --- asset_coverage (non-blocking on the contract, blocking on honesty) ---
    covered = set()
    for a in manifest["assets"]:
        if a["locator"]["method"] == "document":
            continue
        covered.update(range(a["locator"]["start_line"], a["locator"]["end_line"] + 1))
    bare = [(i, lines[i]) for i in range(len(lines)) if i not in covered and lines[i].strip()]
    non_structural = [i for i, ln in bare
                      if not ln.lstrip().startswith("#") and ln.strip() != "```"]
    record("asset_coverage",
           not non_structural
           and manifest["structural_lines_not_registered"]["count"] == len(bare),
           dict(uncovered_non_empty=len(bare), uncovered_payload_lines=non_structural,
                declared_structural_lines=manifest["structural_lines_not_registered"]["count"],
                note="every payload line is inside some content asset; only headings/captions "
                     "and code-block fences are left unregistered"))

    # --- no_duplicate_ids -------------------------------------------------
    ids = [a["asset_id"] for a in manifest["assets"]]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    record("no_duplicate_ids",
           not dup and manifest["package_id"] == PACKAGE_ID
           and envelope["package_id"] == PACKAGE_ID
           and manifest["report_id"] == envelope["report_id"] == REPORT_ID
           and [int(i[1:]) for i in ids] == sorted(int(i[1:]) for i in ids),
           dict(duplicates=dup, n_ids=len(ids),
                ids_sorted_ascending=[int(i[1:]) for i in ids] == sorted(int(i[1:]) for i in ids),
                package_id=manifest["package_id"], report_id=manifest["report_id"]))

    # --- counts consistency ----------------------------------------------
    by_class, by_res = {}, {}
    for a in manifest["assets"]:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    c = manifest["counts"]
    record("counts_consistent",
           c["assets"] == len(manifest["assets"]) and c["by_class"] == by_class
           and c["by_resolution"] == by_res
           and c["resolved_in_source"] == by_res.get("resolved_in_source", 0)
           and c["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)
           and c["declared_absent"] == by_res.get("declared_absent", 0),
           dict(declared=c, recomputed_by_class=by_class, recomputed_by_resolution=by_res))

    # --- claims rule ------------------------------------------------------
    claims = manifest["claims"]
    bad = [cl.get("claim_id") for cl in claims
           if not (cl.get("evidence_locator") or cl.get("evidence") or cl.get("status"))]
    record("all_claims_have_evidence_or_explicit_unresolved_status", not bad,
           dict(n_claims=len(claims), violations=bad,
                note="0 claims by contract (no extraction in task_type=01); rule is "
                     "vacuously satisfied and is reported as such, not as checked content"))

    # --- output wiring ----------------------------------------------------
    out = envelope["outputs"].get("asset_manifest.json")
    record("outputs_wired",
           isinstance(out, dict) and out == manifest
           and envelope["task_type"] == "01-asset-registration"
           and envelope["provenance"]["source_field"] == "markdown",
           dict(output_keys=list(envelope["outputs"]), manifest_embedded=out == manifest,
                task_type=envelope["task_type"]))

    # --- durable mirrors --------------------------------------------------
    doc_blob = DOC.read_text()
    doc_env = ENV_DOC.read_text()
    record("durable_mirror_matches",
           doc_blob == ART.read_text() and doc_env == ENV_RUN.read_text()
           and sha256_text(doc_blob) == envelope["provenance"]["artifact_sha256"],
           dict(artifact_sha256=sha256_text(ART.read_text()),
                declared=envelope["provenance"]["artifact_sha256"],
                env_mirror_identical=doc_env == ENV_RUN.read_text()))

    # --- durable source snapshot ------------------------------------------
    doc_md = DOC / "asset_manifest.json" and pathlib.Path(f"docs/{PACKAGE_ID}/source_{REPORT_ID}.md")
    record("durable_source_snapshot",
           doc_md.exists() and doc_md.read_bytes() == MD.read_bytes()
           and sha256_text(doc_md.read_text()) == SOURCE_HASH,
           dict(durable_copy=str(doc_md), identical=doc_md.exists() and doc_md.read_bytes() == MD.read_bytes(),
                note="docs/ copy is the committed evidence base (runs/** is dropped by the push gate)"))

    # --- report_id isolation ---------------------------------------------
    try:
        status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                                capture_output=True, text=True, check=True).stdout
    except Exception as exc:  # pragma: no cover
        status = ""
        record("report_id_isolation", False, f"git status unavailable: {exc}", blocking=False)
    if status:
        paths = [ln[3:].strip() for ln in status.splitlines() if ln.strip()]
        other = [p for p in paths
                 if re.search(r"wp-(?!8240-01)\d+-", p) or re.search(r"reports?/(?!8240)\d{3,}", p)]
        record("report_id_isolation", not other,
               dict(changed_paths=paths, foreign_report_artifacts=other,
                    note="only wp-8240-01 artifacts, its scripts/schema, and the 8240 payload are touched"))

    # --- report -----------------------------------------------------------
    blocking_fail = [k for k, v in results.items() if v["blocking"] and not v["passed"]]
    verdict = dict(
        package_id=PACKAGE_ID, report_id=REPORT_ID,
        source_sha256=SOURCE_HASH, n_assets=len(manifest["assets"]),
        results=results,
        passed=not blocking_fail,
        failed=[k for k, v in results.items() if not v["passed"]],
        not_run=[k for k, v in results.items() if not v["passed"] and not v["blocking"]],
    )
    (RUN_DIR / f"verify_{REPORT_ID}.json").write_text(
        json.dumps(verdict, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0 if not blocking_fail else 1


if __name__ == "__main__":
    sys.exit(main())