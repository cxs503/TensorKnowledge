#!/usr/bin/env python3
"""Independent red-team verification of wp-5687-01 (01-asset-registration) against report 5687.

Reviewer context = report markdown + the upstream machine product (kf_result.json /
asset_manifest.json / verification.json). The producer's narrative is NOT read.

Design rules
------------
* Every check is machine-decidable and prints the raw operands it compared.
* Locators are re-verified against the report bytes, not against the producer's claim.
* The decision rule is predeclared BEFORE running (DECISION_RULE below) so a failing
  check cannot be argued away after the fact.
* Nothing here marks anything "verified": the emitted verdict is an advisory review
  recommendation; platform gates compute verification.

Usage
-----
    python3 docs/kf/wp-5687-04/verify_wp5687_01.py            # fetch report via API
    python3 docs/kf/wp-5687-04/verify_wp5687_01.py --offline  # use snapshot markdown only

Outputs (inside this package dir): checks.json, review_report.json, kf_result.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PKG = "wp-5687-04"
REVIEWED = "wp-5687-01"
REPORT_ID = "5687"
CONTRACT_SOURCE_HASH = "a4eaa764c52e072a87f6629009b94e3a5ae97d4aab543fe851599a732fcfeb3d"
SOURCE_FIELD = "markdown"
REPO_ROOT = Path(__file__).resolve().parents[3]
PKG_DIR = Path(__file__).resolve().parent
SNAP = PKG_DIR / "upstream_snapshot"

# Predeclared decision rule: verdict=pass requires (a) every gate check green and
# (b) zero blocking findings. A finding is blocking iff it makes the package's core
# contract false or unfalsifiable:
#   B1 source hash unrecomputable or divergent;
#   B2 any locator quote not a contiguous verbatim substring at the stated line;
#   B3 a fabricated resolution (status says resolved while the bytes are absent/unhashable);
#   B4 a claim presented as verified, or an empty claims list hiding extracted claims;
#   B5 JSON/schema invalidity of the delivered envelope.
# Findings outside B1-B5 are recorded as non-blocking defects / suggestions.
DECISION_RULE = {
    "verdict_pass_requires": ["all gate checks pass", "zero blocking findings (B1-B5)"],
    "blocking_classes": {
        "B1": "source hash unrecomputable or divergent",
        "B2": "locator quote not contiguous verbatim substring at declared line",
        "B3": "fabricated resolution status",
        "B4": "claim presented as verified / extracted claims hidden by empty claims list",
        "B5": "JSON or schema invalidity of delivered envelope",
    },
    "declared_before_running": True,
}


# ---------------------------------------------------------------- helpers
def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def api_get(path: str):
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    user, pw = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]

    def _req(url, data=None, tok=None):
        h = {"Content-Type": "application/json"}
        if tok:
            h["Authorization"] = "Bearer " + tok
        r = urllib.request.Request(url, data=data, headers=h)
        return json.load(urllib.request.urlopen(r, timeout=30))

    tok = _req(base + "/auth/login",
               json.dumps({"username": user, "password": pw}).encode())["access_token"]
    rec = _req(base + path, tok=tok)
    return rec.get("report", rec), tok


def http_status(path: str, tok: str) -> int | str:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(base + path, headers={"Authorization": "Bearer " + tok})
    try:
        return urllib.request.urlopen(req, timeout=15).status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:  # noqa: BLE001
        return f"error:{type(e).__name__}"


class Checks:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, cid, name, ok, detail, blocking_class=None) -> bool:
        self.items.append({
            "id": cid, "check": name,
            "result": "pass" if ok is True else ("fail" if ok is False else "not_run"),
            "detail": detail, "blocking_class": blocking_class if ok is False else None,
        })
        return ok is True


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="skip API, use snapshot markdown/metadata")
    ap.add_argument("--write-dir", default=str(PKG_DIR),
                    help="where checks.json/review_report.json/kf_result.json land (default: this package dir)")
    args = ap.parse_args()

    ck = Checks()
    meta: dict = {}
    tok = ""
    if args.offline:
        md = (SNAP / "source_markdown_5687.md").read_text(encoding="utf-8")
        meta = json.loads((SNAP / "report_record_5687.json").read_text(encoding="utf-8"))
        api_ok = False
    else:
        meta, tok = api_get(f"/tensor/reports/{REPORT_ID}")
        md = meta["markdown"]
        (SNAP / "source_markdown_5687.md").write_text(md, encoding="utf-8")
        (SNAP / "report_record_5687.json").write_text(
            json.dumps({k: v for k, v in meta.items() if k != "markdown"},
                       ensure_ascii=False, indent=1), encoding="utf-8")
        api_ok = True

    lines = md.split("\n")
    man = json.loads((SNAP / "asset_manifest.json").read_text(encoding="utf-8"))
    env = json.loads((SNAP / "kf_result.json").read_text(encoding="utf-8"))
    uver = json.loads((SNAP / "verification.json").read_text(encoding="utf-8"))

    # -- C1/C2 JSON validity (B5)
    ck.add("C1", "asset_manifest.json parses as JSON", True,
           f"{len(man.get('assets', []))} assets parsed", "B5")
    ck.add("C2", "kf_result.json parses as JSON", True,
           f"top keys={sorted(env.keys())}", "B5")

    # -- C3 envelope vs repository schema
    schema_path = REPO_ROOT / "schemas" / "kf_result.v1.schema.json"
    try:
        import jsonschema
        if schema_path.exists():
            jsonschema.validate(env, json.loads(schema_path.read_text()))
            ck.add("C3", "kf_result.json conforms to schemas/kf_result.v1.schema.json", True,
                   f"validated against {schema_path.relative_to(REPO_ROOT)}", "B5")
        else:
            ck.add("C3", "kf_result.json conforms to schemas/kf_result.v1.schema.json", None,
                   "schema file absent in this checkout", "B5")
    except ImportError:
        ck.add("C3", "kf_result.json conforms to schemas/kf_result.v1.schema.json", None,
               "jsonschema not importable", "B5")

    # -- C4/C5 source hash & size (B1)
    actual_hash = sha256_text(md)
    declared_env = env["provenance"]["source_hash"].removeprefix("sha256:")
    declared_man = man["provenance"]["source_hash"].removeprefix("sha256:")
    src_asset = next(a for a in man["assets"] if a["asset_id"] == "r5687:source")
    ck.add("C4", "report markdown sha256 matches contract + manifest declarations",
           actual_hash == declared_env == declared_man == CONTRACT_SOURCE_HASH
           and src_asset["sha256"] == CONTRACT_SOURCE_HASH,
           f"actual={actual_hash} contract={CONTRACT_SOURCE_HASH} env={declared_env} manifest={declared_man}", "B1")
    ck.add("C5", "declared chars/bytes_utf8 match recomputed size",
           src_asset["chars"] == len(md) and src_asset["bytes_utf8"] == len(md.encode())
           and man["provenance"]["source_chars"] == len(md)
           and man["provenance"]["source_bytes_utf8"] == len(md.encode()),
           f"chars={len(md)} bytes_utf8={len(md.encode())} declared={src_asset['chars']}/"
           f"{src_asset['bytes_utf8']}", "B1")

    # -- C6 report metadata fidelity
    meta_ok = (man["provenance"]["report_title"] == meta["title"]
               and man["provenance"]["report_scenario_key"] == meta["scenario_key"]
               and man["provenance"]["report_mission_id"] == meta["mission_id"]
               and man["provenance"]["report_tags"] == meta["tags"]
               and man["provenance"].get("report_created_at") == meta["created_at"]
               and man["report_id"] == str(meta["id"]) == env["report_id"])
    ck.add("C6", "manifest provenance metadata equals platform report record", meta_ok,
           f"mission_id={meta['mission_id']} tags={len(meta['tags'])} "
           f"created_at={meta['created_at']} report_id={env['report_id']}")

    # -- C7 ids distinct
    ids = [a["asset_id"] for a in man["assets"]]
    ck.add("C7", "asset ids distinct", len(ids) == len(set(ids)),
           f"{len(ids)} ids, {len(set(ids))} distinct")

    # -- C8 count consistency
    by_kind_declared = man["summary"]["by_kind"]
    recomputed: dict[str, int] = {}
    for a in man["assets"]:
        k = f"{a['kind']}/{a['resolution']['status']}"
        recomputed[k] = recomputed.get(k, 0) + 1
    ck.add("C8", "summary.asset_count/by_kind equals recomputed tally",
           man["summary"]["asset_count"] == len(man["assets"]) == 11
           and by_kind_declared == recomputed
           and man["summary"]["claims"] == len(man["claims"]),
           f"asset_count={man['summary']['asset_count']} len(assets)={len(man['assets'])} "
           f"by_kind_recomputed={recomputed}")

    # -- C9 locators verbatim (B2)  <- the core fidelity check
    loc_rows, bad = [], []
    for a in man["assets"]:
        loc = a.get("locator", {})
        if loc.get("scheme") != "markdown_line":
            continue
        ln, q = loc["line"], loc["quote"]
        line_txt = lines[ln - 1] if 1 <= ln <= len(lines) else ""
        ok = bool(q) and q in md and q in line_txt
        loc_rows.append({"asset_id": a["asset_id"], "line": ln, "quote_chars": len(q),
                         "verbatim_at_line": ok, "quote": q})
        if not ok:
            bad.append(a["asset_id"])
    ck.add("C9", "every markdown_line locator quote is contiguous verbatim text at declared line",
           len(bad) == 0 and len(loc_rows) == 7,
           f"checked={len(loc_rows)} bad={bad}", "B2")

    # -- C10 figure metadata fidelity
    figs = meta.get("figures") or []
    fig_assets = [a for a in man["assets"] if a["kind"] == "embedded_figure"]
    fig_ok = (len(figs) == len(fig_assets)
              and all(fa["name"] == fg["name"] and fa["caption"] == fg["caption"]
                      for fa, fg in zip(fig_assets, figs))
              and all(fa["locator"].get("index") == i for i, fa in enumerate(fig_assets)))
    ck.add("C10", "embedded_figure assets equal platform figures[] name/caption/index", fig_ok,
           f"report figures={[f['name'] for f in figs]} manifest={[f['name'] for f in fig_assets]}")

    # -- C11 no fabricated resolution (B3)
    resolved = [a for a in man["assets"] if a["resolution"]["status"] == "resolved"]
    fab = []
    for a in resolved:
        if a["asset_id"] == "r5687:source":
            if a["sha256"] != actual_hash:
                fab.append(a["asset_id"])
        else:  # any non-source "resolved" claim must expose bytes+hash we can re-check
            p = REPO_ROOT / (a.get("path_reference") or "")
            if not p.exists() or sha256_file(p) != a.get("sha256"):
                fab.append(a["asset_id"])
    meta_only = [a for a in man["assets"] if a["resolution"]["status"] == "metadata_only"]
    meta_only_ok = all(a["sha256"] is None and a.get("bytes") is None and
                       a["resolution"].get("has_payload") is False for a in meta_only)
    ck.add("C11", "no fabricated resolution: resolved assets re-hash, metadata_only assets claim no bytes",
           not fab and meta_only_ok and len(resolved) == 1,
           f"resolved={[a['asset_id'] for a in resolved]} fabricated={fab} "
           f"metadata_only_without_payload={meta_only_ok}", "B3")

    # -- C12 claims honesty (B4)
    md_says_nothing_verified = "verified" not in md.lower()
    ck.add("C12", "claims list empty and no verified mark asserted", man["claims"] == []
           and env.get("claims", []) == [] and uver["all_pass"] is True
           and "verified" not in json.dumps(man).lower().replace("no verified marks", ""),
           f"manifest claims={len(man['claims'])} envelope claims={len(env.get('claims', []))} "
           f"'verified' in report markdown={not md_says_nothing_verified}", "B4")

    # -- C13 declared output identity
    out = env["outputs"]["asset_manifest.json"]
    ck.add("C13", "declared output sha256/bytes equal the delivered manifest bytes",
           out["sha256"] == sha256_file(SNAP / "asset_manifest.json")
           and out["bytes"] == (SNAP / "asset_manifest.json").stat().st_size
           and out["asset_count"] == len(man["assets"]),
           f"sha256={sha256_file(SNAP/'asset_manifest.json')} bytes="
           f"{(SNAP/'asset_manifest.json').stat().st_size}")

    # -- C14 reproduce the upstream verification.json claims independently
    repro = {
        "valid_json": True,
        "schema_pass": ck.items[1]["result"] == "pass" and ck.items[2]["result"] == "pass",
        "source_locator_resolvable": len(loc_rows) + len(fig_assets) + 1 == 11 and all(
            r["verbatim_at_line"] for r in loc_rows),
        "source_hash_matches": actual_hash == CONTRACT_SOURCE_HASH,
        "no_duplicate_ids": len(ids) == len(set(ids)),
        "all_claims_have_evidence_or_explicit_unresolved_status": man["claims"] == [],
    }
    mism = {k: (uver["checks"][k]["pass"], v) for k, v in repro.items()
            if uver["checks"].get(k, {}).get("pass") != v}
    ck.add("C14", "all 6 upstream verification.json assertions reproduce here", not mism,
           f"reproduced={repro} mismatches={mism}")

    # -- C15 endpoint probe reproducibility
    if api_ok:
        raw = {p: http_status(p, tok) for p in
               ("/tensor/reports/5687/artifacts", "/tensor/artifacts?report_id=5687")}
        # declared values are strings like "http_404"; compare the numeric status they encode
        norm_live = {k: f"http_{v}" if isinstance(v, int) else v for k, v in raw.items()}
        declared = {k: v["status"] for k, v in man["artifact_endpoint_probe"].items()}
        ck.add("C15", "artifact_endpoint_probe statuses reproduce (both 404)",
               norm_live == declared and set(norm_live.values()) == {"http_404"},
               f"live={raw} normalized={norm_live} declared={declared}")
    else:
        ck.add("C15", "artifact_endpoint_probe statuses reproduce (both 404)", None,
               "offline mode: endpoint probe not re-issued")

    # -- C16 coverage gap enumeration (non-blocking fidelity)
    registered_paths = {a.get("path_reference") for a in man["assets"] if a.get("path_reference")}
    path_like = sorted({t for t in re.findall(r"`([^`]+)`", md)
                        if ("/" in t or t.endswith((".py", ".md"))) and " " not in t})
    unregistered = [t for t in path_like
                    if t not in registered_paths
                    and not any(t.endswith(rp) or rp.endswith(t.rstrip("/")) for rp in registered_paths if rp)]
    directive_declared = re.findall(r"`([^`]*artifacts/chronicle/[^`]*)`", md)
    ck.add("C16", "no report-declared path silently absent from the asset inventory",
           len(unregistered) == 0,
           f"path_like_tokens={path_like} unregistered={unregistered} "
           f"declared_bundle_lines={directive_declared}")

    # -- C17 distinct-path normalization
    norm = {re.sub(r"^.*/", "", a["path_reference"]) for a in man["assets"] if a.get("path_reference")}
    ck.add("C17", "summary.distinct_referenced_paths is basename-normalized",
           man["summary"]["distinct_referenced_paths"] == len(norm),
           f"declared={man['summary']['distinct_referenced_paths']} raw_paths="
           f"{sorted(registered_paths)} basename_normalized={len(norm)} {sorted(norm)}")

    # -- C18 schema_note accuracy at HEAD
    kf_schemas = sorted(p.name for p in (REPO_ROOT / "schemas").glob("kf_*.json"))
    ck.add("C18", "manifest schema_note ('no kf_* schema shipped') holds at repository HEAD",
           not kf_schemas,
           f"schemas/kf_*.json at HEAD={kf_schemas}")

    # ------------------------------------------------------------ findings
    findings: list[dict] = []

    def find(fid, severity, blocking, claim, evidence, repro, remedy):
        findings.append({"id": fid, "severity": severity, "blocking": blocking,
                         "claim_under_review": claim, "evidence": evidence,
                         "reproduction": repro, "remedy": remedy})

    if not kf_schemas == []:
        find("F1", "low", False,
             "manifest schema_note asserts no kf_* JSON Schema is shipped in the repository",
             {"quote_manifest": man["schema_note"],
              "fact": f"schemas/{kf_schemas[0]} exists at HEAD (git log -1 -- schemas/kf_result.v1.schema.json)",
              "note": "producer checkout lacks it, so the note is true for that tree but stale for HEAD; "
                      "the envelope nevertheless validates against it (check C3)"},
             "python3 -c \"import json,jsonschema;jsonschema.validate(json.load(open('docs/kf/wp-5687-04/upstream_snapshot/kf_result.json')),json.load(open('schemas/kf_result.v1.schema.json')))\"",
             "drop the schema_note or pin it to the producing commit.")
    if any(not r["verbatim_at_line"] for r in loc_rows) is False and len(unregistered) > 0:
        find("F2", "low", False,
             "asset inventory covers every path-like reference declared in the report",
             {"report_quote": "工件 `artifacts/chronicle/`（GLOBAL_CHRONICLE.md + 5 指标 CSV + crosscheck + 3 图）。",
              "line": 40, "unregistered_tokens": unregistered,
              "registered": sorted(p for p in registered_paths if p)},
             "python3 docs/kf/wp-5687-04/verify_wp5687_01.py  (check C16)",
             "register the artifact directory as one unresolved directory-level asset, or state in "
             "limitations that bundle members without declared names are out of inventory scope.")
    find("F3", "low", False,
         "ref:05 path_reference identifies the declared file",
         {"manifest": {"asset_id": "r5687:ref:05", "path_reference": "GLOBAL_CHRONICLE.md"},
          "report_quote": "工件 `artifacts/chronicle/`（GLOBAL_CHRONICLE.md + 5 指标 CSV + crosscheck + 3 图）。",
          "line": 40,
          "why": "the report places the file under artifacts/chronicle/; the basename alone resolves "
                 "to a different (nonexistent) candidate path. Status is unresolved, so no false resolve."},
         "python3 docs/kf/wp-5687-04/verify_wp5687_01.py  (checks C9/C11)",
         "carry the containing directory: path_reference=artifacts/chronicle/GLOBAL_CHRONICLE.md.")
    if man["summary"]["distinct_referenced_paths"] != len(norm):
        find("F4", "low", False,
             "summary.distinct_referenced_paths=5 counts distinct referenced files",
             {"declared": man["summary"]["distinct_referenced_paths"], "basename_normalized": len(norm),
              "paths": sorted(p for p in registered_paths if p),
              "why": "tools/chronicle/metrics.py and metrics.py are the same file counted twice"},
             "python3 docs/kf/wp-5687-04/verify_wp5687_01.py  (check C17)",
             "normalize by basename or record the raw-string definition explicitly (it does document "
             "occurrence-level identity, so this is a metric-label nit).")
    find("F5", "medium", False,
         "upstream verification.json check 'source_locator_resolvable: pass (unresolvable=[])' reads as "
         "'all references resolved'",
         {"quote": json.dumps(uver["checks"]["source_locator_resolvable"], ensure_ascii=False),
          "fact": "7 of 11 assets carry resolution.status=unresolved; the check actually measures "
                  "locator well-formedness, not target resolution",
          "impact": "a downstream gate keyed on this name could record 7 unresolved references as resolved"},
         "python3 -c \"import json;m=json.load(open('docs/kf/wp-5687-04/upstream_snapshot/asset_manifest.json'));print(sum(a['resolution']['status']=='unresolved' for a in m['assets']))\"",
         "split into locator_wellformed (pass) and targets_resolved (7 unresolved) or rename.")
    find("F6", "low", False,
         "the report's data assets (4 tables / 6 parameter rows with SQL provenance) are neither "
         "registered nor declared out of scope",
         {"report_quote": "| missions 区间行 | 4642 | `-- src: select id, created_at, finished_at, status, "
                          "claimed_by, repo from tensor_dev_missions where created_at <= :t_end` |",
          "why": "kind vocabulary has no data/table kind and limitations do not say data assets are excluded"},
         "python3 docs/kf/wp-5687-04/verify_wp5687_01.py  (check C16)",
         "add 'data/table references are outside the 01 kind vocabulary' to limitations.")

    blocking = [f for f in findings if f["blocking"]]
    gate_checks = [c for c in ck.items if c["id"] in
                   ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "C13")]
    all_green = all(c["result"] == "pass" for c in gate_checks)
    verdict = "pass" if (all_green and not blocking) else "needs-fix"

    emitted_at = datetime.now(timezone.utc).isoformat()
    review = {
        "package_id": PKG,
        "task_type": "04-independent-review",
        "contract_version": "1.0",
        "reviewed_package": REVIEWED,
        "reviewed_task_type": man["task_type"],
        "report_id": REPORT_ID,
        "reviewer_role": "red-team-reviewer",
        "independence": {
            "context_inputs": ["report 5687 markdown (sha256-pinned)",
                               "upstream machine product: kf_result.json / asset_manifest.json / verification.json"],
            "excluded": ["producer narrative / report_body.md / producer worktree notes"],
            "producer_explanation_read": False,
            "shared_worktree_with_producer": False,
            "not_self_review": True,
            "limitation": "same model family as producer; independence is procedural (fresh recomputation "
                          "from report bytes), not organisational.",
        },
        "decision": {
            "verdict": verdict,
            "verdict_is_advisory": True,
            "not_a_verified_mark": True,
            "rule": DECISION_RULE,
            "gate_checks_green": f"{sum(c['result']=='pass' for c in gate_checks)}/{len(gate_checks)}",
            "blocking_findings": len(blocking),
            "non_blocking_findings": len(findings) - len(blocking),
            "rationale": "core contract (hash-pinned source, contiguous verbatim locators, no fabricated "
                         "resolution, no verified marks, schema-valid envelope) is independently reproduced; "
                         "remaining findings are inventory coverage and label-accuracy defects.",
        },
        "checks": ck.items,
        "locator_verification": loc_rows,
        "coverage_enumeration": {"path_like_tokens": path_like, "unregistered": unregistered,
                                 "registered_path_references": sorted(p for p in registered_paths if p)},
        "findings": findings,
        "checks_not_run": [
            "byte-level verification of the referenced source files (tools/chronicle/*.py) — outside this "
            "worktree, listed unresolved by the upstream package itself",
            "verification of the report's numeric claims (M1-M5, crosscheck) — those belong to the 03/05 "
            "line, not to 01-asset-registration",
            "platform-side gate recomputation (verification is platform-computed; not claimed here)",
            "producer-side write-boundary adherence across other report_ids — no access to the producer's "
            "write log; only report 5687 artefacts were inspected",
        ],
        "overstated_claims": [
            "upstream verification.json check name source_locator_resolvable (see F5)",
            "manifest schema_note about missing kf_* schema (see F1)",
        ],
        "provenance": {
            "source_uri": f"tensor://reports/{REPORT_ID}",
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + actual_hash,
            "reviewed_artifacts": {
                "kf_result.json": "sha256:" + sha256_file(SNAP / "kf_result.json"),
                "asset_manifest.json": "sha256:" + sha256_file(SNAP / "asset_manifest.json"),
                "verification.json": "sha256:" + sha256_file(SNAP / "verification.json"),
                "upstream_worktree_package_dir": "docs/kf/wp-5687-01",
            },
            "snapshot_dir": "docs/kf/wp-5687-04/upstream_snapshot",
            "emitted_at": emitted_at,
        },
    }

    envelope = {
        "package_id": PKG,
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + actual_hash,
            "source_field": SOURCE_FIELD,
            "producer": "agent/m15838 red-team reviewer",
            "emitted_at": emitted_at,
            "notes": "independent review of wp-5687-01; verdict advisory, no claim marked verified",
        },
        "outputs": {"review_report.json": review},
    }

    out_dir = Path(args.write_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "checks.json").write_text(json.dumps({"checks": ck.items, "locators": loc_rows,
                                                     "coverage": review["coverage_enumeration"]},
                                                    ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "review_report.json").write_text(json.dumps(review, ensure_ascii=False, indent=1),
                                                encoding="utf-8")
    (out_dir / "kf_result.json").write_text(json.dumps(envelope, ensure_ascii=False, indent=1),
                                            encoding="utf-8")

    print(f"report {REPORT_ID} sha256={actual_hash}")
    for c in ck.items:
        print(f"  [{c['result']:^7s}] {c['id']} {c['check']}")
        print(f"            {c['detail']}")
    print(f"FINDINGS: {len(findings)} (blocking={len(blocking)})")
    for f in findings:
        print(f"  {f['id']} [{f['severity']}] blocking={f['blocking']} :: {f['claim_under_review'][:110]}")
    print(f"VERDICT: {verdict}  gate_checks_green="
          f"{sum(c['result']=='pass' for c in gate_checks)}/{len(gate_checks)}")
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())