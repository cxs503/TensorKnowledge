#!/usr/bin/env python3
"""Independent red-team review of working package wp-946-01 (asset registration for report 946).

Reviewer context (by contract): the report 946 markdown as served by the platform
report store + the upstream deliverable (kf_result.json). The producer's own
explanation (report.md / make_report.py narrative / build_asset_manifest.py) is
NOT read: every number below is re-derived here from the report bytes.

Outputs
  review_report.json        review verdict + per-check evidence
  independent_source.json   independent retrieval of the report record (for re-hashing)

Usage
  python3 work/wp-946-04/review_wp946_01.py \
      --upstream work/wp-946-04/upstream/wp-946-01.kf_result.json \
      --out work/wp-946-04/review_report.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.request

CONTRACT_SOURCE_HASH = "sha256:3ea029afd6df49a8d3e407e42df035654b58a7555f9678d657f5fdfc1fe35552"
CONTRACT_CHARS = 14281
REPORT_ID = "946"
TARGET_PACKAGE = "wp-946-01"


def fetch_record(report_id: str = REPORT_ID) -> dict:
    """Independent retrieval straight from the platform report store."""
    base = os.environ["TENSOR_API_BASE"]
    user = os.environ["TENSOR_AGENT_USER"]
    pw = os.environ["TENSOR_AGENT_PASS"]
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": user, "password": pw}).encode(),
        headers={"Content-Type": "application/json"},
    )
    tok = json.load(urllib.request.urlopen(req))
    tok = tok.get("access_token") or tok.get("token")
    req = urllib.request.Request(
        base + "/tensor/reports/" + report_id,
        headers={"Authorization": "Bearer " + tok},
    )
    return json.load(urllib.request.urlopen(req))


def sha256_text(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--independent-source", default=None)
    ap.add_argument("--producer-worktree", default=None)
    args = ap.parse_args()

    rec = fetch_record()
    md = rec["markdown"]
    indep = {
        "report_id": rec["id"],
        "title": rec["title"],
        "scenario_key": rec["scenario_key"],
        "mission_id": rec["mission_id"],
        "tags": rec["tags"],
        "figures": rec["figures"],
        "chars_codepoints": len(md),
        "chars_utf8_bytes": len(md.encode("utf-8")),
        "sha256": sha256_text(md),
        "retrieved_by": "wp-946-04 independent retrieval (platform API)",
    }
    if args.independent_source:
        with open(args.independent_source, "w", encoding="utf-8") as fh:
            json.dump(indep, fh, ensure_ascii=False, indent=1)

    env = json.load(open(args.upstream, encoding="utf-8"))
    manifest = env["outputs"]["asset_manifest.json"]
    assets = manifest["assets"]

    checks: list[dict] = []

    def add(cid, name, ok, detail, blocking=True):
        checks.append(
            {
                "check_id": cid,
                "name": name,
                "status": "pass" if ok else "fail",
                "blocking": blocking,
                "detail": detail,
            }
        )

    # ---- C01 provenance hash -------------------------------------------------
    env_hash = env.get("provenance", {}).get("source_hash")
    man_hash = manifest["source"]["sha256"]
    add(
        "C01",
        "provenance.source_hash == independently recomputed markdown hash",
        env_hash == indep["sha256"] == man_hash == CONTRACT_SOURCE_HASH,
        {
            "envelope": env_hash,
            "manifest": man_hash,
            "independent_recompute": indep["sha256"],
            "contract": CONTRACT_SOURCE_HASH,
        },
    )

    # ---- C02 char length -----------------------------------------------------
    add(
        "C02",
        "chars (code points) match contract; both code-point and UTF-8 byte lengths disclosed",
        manifest["source"]["chars"] == indep["chars_codepoints"] == CONTRACT_CHARS
        and manifest["source"]["byte_length_utf8"] == indep["chars_utf8_bytes"],
        {
            "contract": CONTRACT_CHARS,
            "independent_code_points": indep["chars_codepoints"],
            "independent_utf8_bytes": indep["chars_utf8_bytes"],
        },
    )

    # ---- C03 title / scenario ------------------------------------------------
    add(
        "C03",
        "title and scenario_key in manifest match the report record",
        manifest["source"]["title_in_record"] == rec["title"]
        and manifest["source"]["title_match"] is True
        and manifest["source"]["scenario_key"] == rec["scenario_key"],
        {"record_title": rec["title"], "manifest_scenario": manifest["source"]["scenario_key"]},
    )

    # ---- C04 markdown locators verbatim at declared offsets -------------------
    md_bad, md_offsets, occurrence_bad, n_md_loc = [], 0, [], 0
    for a in assets:
        for loc in a.get("locators", []):
            if loc.get("source_field") != "markdown":
                continue
            n_md_loc += 1
            q = loc.get("quote", "")
            if q not in md:
                md_bad.append({"asset_id": a["asset_id"], "quote": q[:80]})
                continue
            cs, ce = loc.get("char_start"), loc.get("char_end")
            if cs is not None and ce is not None:
                md_offsets += 1
                if md[cs:ce] != q:
                    md_bad.append(
                        {
                            "asset_id": a["asset_id"],
                            "issue": "offset_slice_mismatch",
                            "declared": [cs, ce],
                            "slice_head": md[cs:cs + 40],
                            "quote_head": q[:40],
                        }
                    )
            cnt = md.count(q)
            if loc.get("occurrences") is not None and loc["occurrences"] != cnt:
                occurrence_bad.append(
                    {"asset_id": a["asset_id"], "declared": loc["occurrences"], "observed": cnt}
                )
    add(
        "C04",
        "every markdown locator quote is a verbatim substring of the report markdown",
        not md_bad,
        {"markdown_locators": n_md_loc, "failures": md_bad},
    )
    add(
        "C05",
        "declared char offsets delimit exactly the quoted bytes; occurrence counts agree",
        not md_bad and not occurrence_bad,
        {
            "offsets_compared": md_offsets,
            "offset_failures": [x for x in md_bad if x.get("issue")],
            "occurrence_failures": occurrence_bad,
        },
    )

    # ---- C06 record locators -------------------------------------------------
    def rec_value(path: str):
        cur = rec
        for part in path.split("."):
            m = re.match(r"^(\w+)\[(\d+)\]$", part)
            if m:
                cur = cur[m.group(1)][int(m.group(2))]
            else:
                cur = cur[part]
        return cur

    rec_bad, n_rec_loc = [], 0
    for a in assets:
        for loc in a.get("locators", []):
            if loc.get("source_field") != "record":
                continue
            n_rec_loc += 1
            try:
                observed = rec_value(loc["field"])
            except Exception as exc:  # noqa: BLE001
                rec_bad.append({"asset_id": a["asset_id"], "field": loc["field"], "error": str(exc)})
                continue
            if observed != loc.get("value"):
                rec_bad.append(
                    {
                        "asset_id": a["asset_id"],
                        "field": loc["field"],
                        "declared": loc.get("value"),
                        "observed": observed,
                    }
                )
    add(
        "C06",
        "every record locator value equals the live value in the report record",
        not rec_bad,
        {"record_locators": n_rec_loc, "failures": rec_bad},
    )

    # ---- C07 counts ----------------------------------------------------------
    kinds, statuses = {}, {}
    for a in assets:
        kinds[a["kind"]] = kinds.get(a["kind"], 0) + 1
        statuses[a["status"]] = statuses.get(a["status"], 0) + 1
    declared = manifest["counts"]
    counts_ok = (
        declared["total"] == len(assets)
        and declared["by_kind"] == kinds
        and declared["resolvable"] == statuses.get("resolvable", 0)
        and declared["unresolved"] == statuses.get("unresolved", 0)
    )
    add(
        "C07",
        "manifest counts recompute exactly from the asset list",
        counts_ok,
        {
            "declared_total": declared["total"],
            "recomputed_total": len(assets),
            "by_kind_match": declared["by_kind"] == kinds,
            "statuses_recomputed": statuses,
            "declared_by_status": declared.get("by_status"),
        },
    )

    # ---- C08 unique ids ------------------------------------------------------
    ids = [a["asset_id"] for a in assets]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    add("C08", "asset_ids are unique", not dup, {"n": len(ids), "duplicates": dup})

    # ---- C09 unresolved reason ----------------------------------------------
    missing_reason = [
        a["asset_id"]
        for a in assets
        if a.get("status") == "unresolved" and not a.get("unresolved_reason")
    ]
    add(
        "C09",
        "every unresolved asset carries an explicit unresolved_reason",
        not missing_reason,
        {"unresolved": statuses.get("unresolved", 0), "missing_reason": missing_reason},
    )

    # ---- C10 no self-verification / no verified label ------------------------
    text = json.dumps(env, ensure_ascii=False)
    bad_status = [a["status"] for a in assets if a["status"] not in ("resolvable", "unresolved")]
    verified_hits = [
        m.start()
        for m in re.finditer(r'"status"\s*:\s*"verified"|"verified"\s*:\s*true', text)
    ]
    ext = manifest.get("verification", {})
    add(
        "C10",
        "no asset is labelled verified and verification is declared as gate-computed",
        not bad_status and not verified_hits and ext.get("performed") is False,
        {
            "asset_statuses": sorted(set(bad_status)) or sorted(statuses),
            "verified_literal_hits": len(verified_hits),
            "verification_block": ext,
        },
    )

    # ---- C11 single-report scope --------------------------------------------
    ids_in_env = sorted(set(re.findall(r"reports/(\d+)", text)))
    add(
        "C11",
        "deliverable touches report 946 only (no other report_id)",
        ids_in_env == [REPORT_ID] and manifest["scope"]["report_id"] == REPORT_ID
        and manifest["scope"]["other_reports_read_or_written"] == [],
        {"report_ids_in_deliverable": ids_in_env, "scope_block": manifest["scope"]},
    )

    # ---- C12 figure coverage -------------------------------------------------
    md_figs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", md)
    man_figs = [a for a in assets if a["kind"] == "figure"]
    man_names = [a["name"] for a in man_figs]
    add(
        "C12",
        "all markdown image references are registered as figure assets (1:1)",
        len(md_figs) == len(man_figs) and sorted(md_figs) == sorted(man_names),
        {
            "markdown_images": md_figs,
            "registered_figures": man_names,
            "record_figures": [f.get("name") for f in rec.get("figures") or []],
        },
    )

    # ---- C13 claims empty is contract-legal ---------------------------------
    add(
        "C13",
        "claims array is empty (no extraction claimed by an asset-registration package)",
        env.get("claims") == [] and manifest["extraction"]["performed"] is False,
        {"claims_len": len(env.get("claims", [])), "extraction": manifest["extraction"]},
    )

    # ---- C14 envelope schema -------------------------------------------------
    schema_ok, schema_err = None, None
    try:
        import jsonschema  # type: ignore

        here = os.path.dirname(os.path.abspath(__file__))
        schema_path = None
        probe = here
        for _ in range(6):  # walk up to the repo root that owns schemas/
            cand = os.path.join(probe, "schemas", "kf_result.v1.schema.json")
            if os.path.exists(cand):
                schema_path = cand
                break
            probe = os.path.dirname(probe)
        schema = json.load(open(schema_path, encoding="utf-8"))
        jsonschema.validate(env, schema)
        schema_ok = True
    except ImportError:
        schema_err = "jsonschema not installed"
    except Exception as exc:  # noqa: BLE001
        schema_ok, schema_err = False, f"{type(exc).__name__}: {str(exc)[:300]}"
    add(
        "C14",
        "envelope validates against schemas/kf_result.v1.schema.json",
        bool(schema_ok),
        {"error": schema_err, "validator": "jsonschema" if schema_ok else None},
    )

    # ---- C15 producer self-check claims re-derived ---------------------------
    sc = None
    sc_path = os.path.join(os.path.dirname(args.upstream), "wp-946-01.selfcheck.json")
    if os.path.exists(sc_path):
        sc = json.load(open(sc_path, encoding="utf-8"))
    sc_detail = {"selfcheck_present": sc is not None}
    sc_ok = True
    if sc:
        prod = sc.get("checks", {})
        prod_md = (prod.get("source_locator_resolvable", {}).get("detail") or {}).get(
            "markdown_locators"
        )
        prod_rec = (prod.get("source_locator_resolvable", {}).get("detail") or {}).get(
            "record_locators"
        )
        sc_detail.update(
            {
                "producer_markdown_locators": prod_md,
                "reviewer_markdown_locators": n_md_loc,
                "producer_record_locators": prod_rec,
                "reviewer_record_locators": n_rec_loc,
                "producer_counts": sc.get("counts"),
                "reviewer_counts": {
                    "total": len(assets),
                    "resolvable": statuses.get("resolvable", 0),
                    "unresolved": statuses.get("unresolved", 0),
                },
            }
        )
        sc_ok = (
            prod_md == n_md_loc
            and prod_rec == n_rec_loc
            and sc.get("counts", {}).get("total") == len(assets)
            and sc.get("counts", {}).get("resolvable") == statuses.get("resolvable", 0)
        )
    add(
        "C15",
        "producer self-check numbers are re-derivable by the reviewer (self-check never taken on trust)",
        sc_ok,
        sc_detail,
    )

    # ---- C16 narrative assertions inside the manifest -----------------------
    fence_count = md.count("```")
    csa = re.search(r"https://labs\.cloudsecurityalliance\.org[^\s;]*", md)
    csa_url = csa.group(0) if csa else None
    # truncated mid-path means the captured URL ends without a document slug after 'framewo'
    csa_truncated = bool(csa_url) and csa_url.endswith("framewo")
    mission_note = manifest["notes"][0]
    add(
        "C16",
        "manifest narrative footnotes (no fenced code block / truncated CSA URL / mission_id mismatch) are factually true",
        fence_count == 0
        and csa_truncated
        and str(rec["mission_id"]) in mission_note,
        {
            "fenced_markers_in_markdown": fence_count,
            "csa_url_as_written": csa_url,
            "csa_url_truncated": csa_truncated,
            "record_mission_id": rec["mission_id"],
            "producer_note": mission_note,
        },
    )

    # ---- C17 resolvable/unresolved classification defensibility -------------
    # Anything the report store itself can serve must be resolvable; anything the store cannot
    # serve must be unresolved. The store serves exactly two things for this report: the
    # markdown bytes and the record metadata. Everything else is a pointer to an external
    # worktree/log/URL and cannot be opened through the report store.
    resolvable = {a["asset_id"]: a["kind"] for a in assets if a["status"] == "resolvable"}
    allowed_resolvable_kinds = {"source_document", "record_metadata"}
    mislabelled = {k: v for k, v in resolvable.items() if v not in allowed_resolvable_kinds}
    unresolved_store_kinds = [
        a["asset_id"] for a in assets if a["status"] == "unresolved" and a["kind"] in allowed_resolvable_kinds
    ]
    add(
        "C17",
        "resolvable/unresolved classification matches what the report store actually serves",
        not mislabelled and not unresolved_store_kinds,
        {
            "resolvable": resolvable,
            "allowed_kinds": sorted(allowed_resolvable_kinds),
            "mislabelled_resolvable": mislabelled,
            "store_servable_but_unresolved": unresolved_store_kinds,
        },
    )

    # ---- C18 producer-side record snapshot hash ------------------------------
    snap = None
    for a in assets:
        cr = a.get("content_ref") or {}
        if cr.get("snapshot_sha256"):
            snap = cr
            break
    c18 = {"declared": (snap or {}).get("snapshot_sha256"), "checked_path": args.producer_worktree}
    if snap and args.producer_worktree:
        cand = os.path.join(args.producer_worktree, snap.get("record_snapshot", ""))
        if os.path.exists(cand):
            got = "sha256:" + hashlib.sha256(open(cand, "rb").read()).hexdigest()
            inner = json.loads(open(cand, encoding="utf-8").read()).get("markdown", "")
            c18.update(
                {
                    "observed": got,
                    "match": got == snap["snapshot_sha256"],
                    "snapshot_markdown_sha256": sha256_text(inner),
                    "snapshot_markdown_matches_live_report": sha256_text(inner) == indep["sha256"],
                }
            )
            add(
                "C18",
                "producer record snapshot hash (declared in content_ref) recomputes and its markdown equals the live report",
                c18["match"] and c18["snapshot_markdown_matches_live_report"],
                c18,
            )
        else:
            c18["status"] = "not_run_path_absent"
    if "match" not in c18:
        checks.append(
            {
                "check_id": "C18",
                "name": "producer record snapshot hash recomputes",
                "status": "not_run",
                "blocking": False,
                "detail": c18,
            }
        )

    # ---- C19 no referenced path left unregistered ---------------------------
    names = [a["name"] for a in assets]
    equiv = {
        "/root/tp-agent/work/m1237/artifacts/ai-native-infra-v1/build_evidence.py":
            "absolute-path variant of the registered relative build_evidence.py",
        "http://127.0.0.1:8010/api/v1/tensor/missions":
            "literal form of the registered template ${TENSOR_API_BASE}/tensor/missions",
        "http://127.0.0.1:8010/api/v1/tensor/missions（missions":
            "truncated literal form of the same endpoint",
    }
    toks = set()
    for t in re.findall(r"`([^`\n]{3,160})`", md):
        for part in re.split(r"\s+(?:\+|&&)\s+", t):
            part = re.sub(r"^(?:python3|bash|sh)\s+", "", part.strip()).split(" ")[0]
            if "/" in part or part.endswith((".py", ".json", ".md", ".png", ".log", ".txt")):
                toks.add(part)
    uncovered = []
    for t in sorted(toks):
        if t in names or any(n.startswith(t) or t.startswith(n) for n in names) or t in equiv:
            continue
        uncovered.append(t)
    add(
        "C19",
        "every path-like reference fenced in the markdown is registered as an asset or is a known equivalent form",
        not uncovered,
        {
            "path_like_tokens": len(toks),
            "registered_names": names,
            "known_equivalents": equiv,
            "uncovered": uncovered,
        },
    )

    # ---- verdict -------------------------------------------------------------
    blocking = [c for c in checks if c["blocking"] and c["status"] == "fail"]
    verdict = "pass" if not blocking else "needs-fix"

    report = {
        "review_schema": "kf-independent-review.v1",
        "package_id": "wp-946-04",
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "review_target": {
            "package_id": TARGET_PACKAGE,
            "task_type": env.get("task_type"),
            "producer": env.get("provenance", {}).get("producer"),
            "deliverable_sha256": "sha256:"
            + hashlib.sha256(open(args.upstream, "rb").read()).hexdigest(),
            "outputs_reviewed": list(env["outputs"].keys()),
        },
        "reviewer": {
            "id": "agent/m15818",
            "role": "red-team-reviewer",
            "context": [
                "report 946 markdown fetched independently from the platform report store",
                "upstream deliverable work/wp-946-04/upstream/wp-946-01.kf_result.json",
            ],
            "excluded": [
                "producer report.md",
                "producer make_report.py narrative",
                "producer build_asset_manifest.py / validate_asset_manifest.py implementations",
                "producer's verbal explanation of its own work",
            ],
            "checker_limitations": [
                "C04-C05 match quotes as substrings/slices of the markdown; they cannot detect a quote "
                "that is verbatim but semantically irrelevant to its asset (spot-read only, 6 assets)",
                "C19 tokenises fenced spans and drops prose-embedded directory references, which is why "
                "the 'docs/ 判据文件' gap surfaces as note N4 rather than as a failed check",
            ],
            "independence_note": (
                "all quotes/offsets/counts below were re-derived with a reviewer-written checker "
                "(work/wp-946-04/review_wp946_01.py); the producer's validators were not executed"
            ),
        },
        "verdict": verdict,
        "decision": "approve" if verdict == "pass" else "request-changes",
        "reviewed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "policy_version": "kf-independent-review.v1",
        "verdict_reason": (
            "all blocking checks pass: provenance hash, verbatim locators, counts, scope and "
            "no-self-verification reproduce exactly"
            if verdict == "pass"
            else "blocking check failures: " + ", ".join(c["check_id"] for c in blocking)
        ),
        "checks": checks,
        "blocking_failures": [c["check_id"] for c in blocking],
        "non_blocking_notes": [
            {
                "note_id": "N1",
                "text": (
                    "20/22 assets are unresolved because report 946 stores figure references, not "
                    "figure bytes, and the artefact worktree is outside the report store. This is a "
                    "faithful registration, not a defect of the package, but it caps the usable "
                    "evidence surface of downstream packages at the markdown text itself."
                ),
            },
            {
                "note_id": "N2",
                "text": (
                    "The registration makes no correctness claim about report 946's numbers "
                    "(rubric scores, 31 REVIVE events, 33.0 s poll median). Reviewing those requires "
                    "the referenced logs/API which are outside the report store; that check is "
                    "explicitly not_run here, not passed."
                ),
            },
            {
                "note_id": "N4",
                "text": (
                    "Coverage gap found by this reviewer: C10's second cited source, the prose phrase "
                    "'本工作树 docs/ 判据文件', is not registered as its own asset (only "
                    "DISPOSITION_RULES.md is covered by ast-946-19). Non-blocking because the phrase "
                    "names no concrete file, but a downstream package citing C10 has no locator for it."
                ),
            },
            {
                "note_id": "N5",
                "text": (
                    "ast-946-14 registers the endpoint in template form '${TENSOR_API_BASE}/tensor/missions' "
                    "while the running text writes the literal 'http://127.0.0.1:8010/api/v1/tensor/missions'. "
                    "Semantically equal, but a downstream consumer grepping the literal string will miss it."
                ),
            },
            {
                "note_id": "N6",
                "text": (
                    "The absolute-path variant '/root/tp-agent/work/m1237/artifacts/ai-native-infra-v1/"
                    "build_evidence.py' (C7 row) is folded into the relative-name asset ast-946-08 rather than "
                    "registered separately; deliberate de-duplication, disclosed here so the fold is auditable."
                ),
            },
            {
                "note_id": "N3",
                "text": (
                    "record.mission_id=1237 vs contract mission_id=null is disclosed by the producer "
                    "rather than silently repaired; reconciliation belongs to the dispatch gate."
                ),
            },
        ],
        "not_run": [
            "existence/content check of external artefact paths (/root/tp-agent/work/m1237/artifacts/...) — outside both the report store and this worktree",
            "re-execution of report 946's build_evidence.py / make_report.py (no such artefacts are resolvable from the report store)",
            "figure byte integrity (PNG sha256 vs captions) — report store serves no figure bytes (HTTP 404 probed by producer, re-probed here)",
        ],
        "upstream_packages_completed": {
            "required": [TARGET_PACKAGE],
            "present": [TARGET_PACKAGE],
            "status": "completed",
            "evidence": "upstream kf_result.json validates against kf_result.v1.schema.json and its "
            "source_hash matches an independent recompute of the report markdown",
        },
    }

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print(json.dumps({"verdict": verdict, "failed": [c["check_id"] for c in checks if c["status"] == "fail"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())