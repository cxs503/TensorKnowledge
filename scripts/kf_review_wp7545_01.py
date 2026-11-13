#!/usr/bin/env python3
"""Independent review harness for wp-7545-01 (task_type 04-independent-review, lane C).

Reviewer context = source markdown (tensor://reports/7545) + upstream knowledge product
(asset_manifest.json, kf_result.json). The producer's prose explanation (REPORT.md /
README.md) is deliberately NOT read into the review; it is touched only by the
prompt-independence metric (V10), which reports a number and no content.

Checks
  V1  source hash / chars / bytes vs contract
  V2  every locator quote sits exactly at [start_char:end_char]; line numbers agree;
      quote uniqueness inside the source
  V3  declared_absent figures: independent byte probes of both endpoint spellings and
      of the on-disk figure root (the route returns FileResponse/404-on-missing)
  V4  counts consistency (assets / by_class / by_resolution / kf_result asset_count)
  V5  completeness: every backticked path-like token in the markdown is registered
  V6  declared product digest in kf_result matches the manifest bytes on disk
  V7  cross-product: platform figure metadata vs manifest captions
  V8  kf_result envelope validates against schemas/kf_result.v1.schema.json
  V9  schema reproducibility: the in-repo asset_manifest schema is const-pinned to
      another package, so this package's schema_pass cannot be re-run from the repo
  V10 prompt independence: 5-gram Jaccard(review instructions, producer REPORT.md) < 0.5
Exit code 0 = no reviewer check failed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "work", "kf_wp7545", "report_7545.md")
SNAPSHOT = os.path.join(ROOT, "work", "kf_wp7545", "upstream")
_PRODUCER = "/root/tp-agent/work/m15597/docs/kf/wp-7545-01"
UP = os.environ.get("UPSTREAM_PKG") or (SNAPSHOT if os.path.isdir(SNAPSHOT) else _PRODUCER)
OUT = os.path.join(ROOT, "work", "kf_wp7545", "review")
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010").rstrip("/")
FIGROOT = "/root/tensor-ecosystem/TensorPlatform/backend/uploads/tensor_reports"

CONTRACT_HASH = "84010e0091071d5971888931b9d6b73fc3bba4f217dcd17ab739979fc1c5ae60"

#: Reviewer instructions authored for this package (independent of the producer prompt).
REVIEW_INSTRUCTIONS = """Independently re-derive the asset registration of report 7545.
Recompute the source digest and the character/byte counts from the platform markdown.
For every registered asset, re-resolve the locator against the source text and reject
any locator whose declared span does not equal its verbatim quote.
Probe the figure endpoints and the figure storage root; a missing figure may only be
recorded as absent with no invented digest.
Verify that every path-like token in the report body is registered and that the
class/resolution counts add up.
Validate the result envelope against the repository schema and check that the declared
product digest matches the bytes on disk.
State whether the upstream product can be used as-is by the extraction stage."""


def http_status(url: str, token: str | None = None) -> dict:
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return {"url": url.replace(BASE, ""), "status": r.status, "bytes_read": len(r.read(64))}
    except urllib.error.HTTPError as e:
        return {"url": url.replace(BASE, ""), "status": e.code}
    except Exception as e:  # noqa: BLE001
        return {"url": url.replace(BASE, ""), "error": str(e)}


def login() -> str | None:
    body = {"username": os.environ.get("TENSOR_AGENT_USER", ""),
            "password": os.environ.get("TENSOR_AGENT_PASS", "")}
    try:
        req = urllib.request.Request(BASE + "/auth/login", data=json.dumps(body).encode(),
                                     method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())
        return d.get("access_token") or d.get("token")
    except Exception:  # noqa: BLE001
        return None


def ngrams(text: str, n: int = 5) -> set[str]:
    t = re.sub(r"\s+", "", text)
    return {t[i:i + n] for i in range(max(0, len(t) - n + 1))}


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    src = open(SRC, encoding="utf-8").read()
    man = json.load(open(os.path.join(UP, "asset_manifest.json"), encoding="utf-8"))
    kfr_path = os.path.join(UP, "kf_result.json")
    kfr = json.load(open(kfr_path, encoding="utf-8"))
    checks: dict[str, dict] = {}

    # ---- snapshot of the reviewed product (audit reproducibility) ----------
    os.makedirs(SNAPSHOT, exist_ok=True)
    sums = []
    for fname in ("asset_manifest.json", "kf_result.json"):
        b = open(os.path.join(UP, fname), "rb").read()
        dst = os.path.join(SNAPSHOT, fname)
        if not os.path.isfile(dst) or open(dst, "rb").read() != b:
            open(dst, "wb").write(b)
        sums.append(f"{hashlib.sha256(b).hexdigest()}  {fname}")
    open(os.path.join(SNAPSHOT, "SHA256SUMS"), "w").write("\n".join(sums) + "\n")

    # ---- V1 source identity -------------------------------------------------
    h = hashlib.sha256(src.encode("utf-8")).hexdigest()
    checks["V1_source_identity"] = {
        "sha256": "sha256:" + h, "matches_contract": h == CONTRACT_HASH,
        "chars": len(src), "chars_declared": man["source"]["chars"],
        "bytes_utf8": len(src.encode("utf-8")), "bytes_declared": man["source"]["bytes_utf8"],
        "pass": h == CONTRACT_HASH and len(src) == man["source"]["chars"]
        and len(src.encode("utf-8")) == man["source"]["bytes_utf8"],
    }

    # ---- V2 locators -------------------------------------------------------
    lines = src.splitlines(keepends=True)
    starts, acc = [], 0
    for ln in lines:
        starts.append(acc)
        acc += len(ln)

    def line_of(idx: int) -> int:
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= idx:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    per_asset, loc_fail, uniq_fail, line_fail, doc_method = [], [], [], [], 0
    for a in man["assets"]:
        loc = a.get("locator") or {}
        q, s, e = loc.get("quote"), loc.get("start_char"), loc.get("end_char")
        ok = q is not None and s is not None and e is not None and src[s:e] == q
        uniq = (src.count(q) == 1) if q else False
        rows = {"asset_id": a["asset_id"], "resolution": a["resolution"],
                "method": loc.get("method"), "span": [s, e], "quote_at_locator": ok,
                "quote_unique": uniq, "quote_len": len(q) if q else 0,
                "quote_starts_at_span_start": bool(q and s is not None and src.startswith(q, s))}
        if a["resolution"] == "referenced_unresolved" and ok and uniq:
            rows["quote_occurrences_in_source"] = src.count(q)
        if s is not None:
            rows["start_line_recomputed"] = line_of(s)
            rows["start_line_declared"] = loc.get("start_line")
            if loc.get("start_line") is not None and rows["start_line_recomputed"] != loc["start_line"]:
                line_fail.append(a["asset_id"])
            if e is not None:
                rows["end_line_recomputed"] = line_of(max(s, e - 1))
                if loc.get("end_line") is not None and rows["end_line_recomputed"] != loc["end_line"]:
                    line_fail.append(a["asset_id"] + ":end_line")
        if loc.get("method") == "document":
            doc_method += 1
        if not ok:
            loc_fail.append(a["asset_id"])
        if not uniq:
            uniq_fail.append(a["asset_id"])
        per_asset.append(rows)
    checks["V2_locators"] = {
        "assets": len(per_asset), "locator_mismatch": loc_fail, "non_unique": uniq_fail,
        "line_number_mismatch": line_fail, "document_method_assets": doc_method,
        "detail_document_method": [r for r in per_asset if r["method"] == "document"],
        "pass": not loc_fail and not uniq_fail and not line_fail,
    }

    # ---- V3 declared_absent figure probes ---------------------------------
    tok = login()
    figs = [a for a in man["assets"] if a["asset_class"] == "embedded_figure"]
    probes = []
    for a in figs:
        name = a["label"]
        if a["resolution"] == "declared_absent":
            probes.append({
                "asset_id": a["asset_id"], "name": name,
                "probe_tensor_path": http_status(f"{BASE}/tensor/reports/7545/figures/{name}", tok),
                "probe_api_v1_path": http_status(f"{BASE}/api/v1/tensor/reports/7545/figures/{name}", tok),
                "on_disk": os.path.isfile(os.path.join(FIGROOT, "7545", name)),
            })
    invented = [a["asset_id"] for a in man["assets"]
                if a["resolution"] != "resolved_in_source" and a.get("sha256")]
    absent_confirmed = all(p["probe_tensor_path"].get("status") == 404
                           and p["probe_api_v1_path"].get("status") == 404
                           and p["on_disk"] is False for p in probes)
    checks["V3_declared_absent"] = {
        "probes": probes, "figure_storage_root": FIGROOT,
        "route_semantics": "GET /tensor/reports/{id}/figures/{name} -> FileResponse(FIGURE_DIR/id/name.png)"
                           " else HTTPException 404 (backend/api/tensor_reports.py:217-229)",
        "figures_absent_confirmed": absent_confirmed, "invented_digests": invented,
        "pass": absent_confirmed and not invented,
    }

    # ---- V4 counts ---------------------------------------------------------
    by_class, by_res = {}, {}
    for a in man["assets"]:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    c = man["counts"]
    checks["V4_counts"] = {
        "assets_actual": len(man["assets"]), "assets_declared": c["assets"],
        "by_class_actual": by_class, "by_class_declared": c["by_class"],
        "by_resolution_actual": by_res, "by_resolution_declared": c["by_resolution"],
        "kf_result_asset_count": kfr["outputs"]["asset_manifest.json"]["asset_count"],
        "pass": len(man["assets"]) == c["assets"] == kfr["outputs"]["asset_manifest.json"]["asset_count"]
        and by_class == c["by_class"] and by_res == c["by_resolution"],
    }

    # ---- V5 completeness of path-like tokens ------------------------------
    ticked = re.findall(r"`([^`]+)`", src)
    pathish = [t for t in ticked if re.search(r"[/\\.]|\.json|\.py|pytest", t)]
    registered = {(a.get("label") or "").strip() for a in man["assets"]}
    missing = sorted({t for t in pathish if t.strip() not in registered})
    checks["V5_completeness"] = {
        "backticked_tokens": len(ticked), "pathish_tokens": len(pathish),
        "pathish_unique": sorted(set(pathish)),
        "non_path_tokens_ignored": sorted(t for t in ticked if t not in pathish),
        "unregistered_pathish": missing, "pass": not missing,
    }

    # ---- V6 product digest ------------------------------------------------
    raw = open(os.path.join(UP, "asset_manifest.json"), "rb").read()
    dg = hashlib.sha256(raw).hexdigest()
    dec = kfr["outputs"]["asset_manifest.json"]
    checks["V6_product_digest"] = {"actual_sha256": dg, "declared_sha256": dec["sha256"],
                                   "actual_bytes": len(raw), "declared_bytes": dec["bytes"],
                                   "pass": dg == dec["sha256"] and len(raw) == dec["bytes"]}

    # ---- V7 platform figure metadata --------------------------------------
    plat = {}
    try:
        req = urllib.request.Request(f"{BASE}/tensor/reports/7545", method="GET")
        if tok:
            req.add_header("Authorization", "Bearer " + tok)
        with urllib.request.urlopen(req, timeout=30) as r:
            plat = json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        plat = {"error": str(e)}
    pf = plat.get("figures") or []
    name_ok = len(pf) == len(figs) == 4 and [p.get("name") for p in pf] == [a["label"] for a in figs]
    checks["V7_figure_metadata"] = {
        "platform_figures": pf,
        "manifest_captions": [{"asset_id": a["asset_id"], "label": a["label"],
                               "caption": a.get("caption")} for a in figs],
        "names_match_in_order": name_ok,
        "note": "fig[i] <-> 图 N correspondence is positional only (markdown carries no "
                "file names); captions differ in wording between platform metadata and "
                "the markdown caption line",
        "pass": name_ok,
    }

    # ---- V8 envelope schema ------------------------------------------------
    import jsonschema
    schema = json.load(open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"), encoding="utf-8"))
    errs = []
    try:
        jsonschema.validate(kfr, schema)
    except jsonschema.ValidationError as e:  # pragma: no cover
        errs = [f"{list(e.path)}: {e.message}"]
    checks["V8_envelope_schema"] = {"errors": errs, "pass": not errs}

    # ---- V9 schema reproducibility of the upstream manifest ---------------
    am_schema_path = os.path.join(ROOT, "schemas", "asset_manifest.v1.schema.json")
    am = json.load(open(am_schema_path, encoding="utf-8"))
    pinned_pid = am["properties"]["package_id"].get("const")
    pinned_rid = am["properties"]["report_id"].get("const")
    rebound_shipped = [f for f in os.listdir(UP) if "schema" in f.lower()]
    checks["V9_manifest_schema_reproducibility"] = {
        "schema_file": "schemas/asset_manifest.v1.schema.json",
        "pinned_package_id": pinned_pid, "pinned_report_id": pinned_rid,
        "package_under_review": man["package_id"], "report_under_review": man["report_id"],
        "rebound_schema_shipped_in_package": rebound_shipped,
        "pass": pinned_pid == man["package_id"] and pinned_rid == man["report_id"],
    }

    # ---- V10 prompt independence (metric only, no content ingested) -------
    prod_report = os.path.join(_PRODUCER, "REPORT.md")  # corpus only, never kept in this tree
    ratio, corpus = None, None
    if os.path.isfile(prod_report):
        raw_txt = open(prod_report, encoding="utf-8").read()
        corpus = {"path": prod_report,
                  "sha256": "sha256:" + hashlib.sha256(raw_txt.encode("utf-8")).hexdigest(),
                  "bytes": len(raw_txt.encode("utf-8"))}
        a, b = ngrams(REVIEW_INSTRUCTIONS), ngrams(raw_txt)
        ratio = round(len(a & b) / max(1, len(a | b)), 3)
    checks["V10_prompt_independence"] = {
        "jaccard_5gram_review_instructions_vs_producer_report": ratio,
        "threshold": 0.5,
        "corpus": corpus,
        "status": "run" if ratio is not None else "not_run (producer delivery text absent)",
        "note": "producer prose is not part of the reviewer context and is not copied into this "
                "tree; it is touched only to compute this distance, and the distance is reported "
                "as a number",
        "pass": (ratio < 0.5) if ratio is not None else None,
    }

    failed = [k for k, v in checks.items() if v["pass"] is False]
    report = {"package_reviewed": "wp-7545-01", "report_id": "7545",
              "source_sha256": "sha256:" + h, "checks": checks, "per_asset": per_asset,
              "failed_checks": failed,
              "verdict": "pass" if not failed else "needs-fix"}
    with open(os.path.join(OUT, "upstream_review_checks.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(json.dumps({"failed_checks": failed,
                      "per_check": {k: v["pass"] for k, v in checks.items()},
                      "V9": checks["V9_manifest_schema_reproducibility"]["rebound_schema_shipped_in_package"],
                      "V10": ratio, "unregistered_pathish": missing}, ensure_ascii=False, indent=1))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())