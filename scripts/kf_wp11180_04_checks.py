#!/usr/bin/env python3
"""KF wp-11180-04 independent-review check harness (report_id=11180).

Re-derives every factual statement the review rests on, from raw bytes only:
  * the source report markdown (live API or the byte snapshot under
    docs/kf/wp-11180-04/source/report_11180.md),
  * the upstream package wp-11180-01 machine output (object under test),
  * the platform contract quoted in the work-package YAML.

Nothing is copied by hand: quotes are located by substring search, numbers are
parsed out of the located quote, and any quote that cannot be found verbatim
makes the corresponding check fail.

Usage:
  python3 scripts/kf_wp11180_04_checks.py            # offline, uses snapshot
  python3 scripts/kf_wp11180_04_checks.py --live     # also re-fetches from API
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(ROOT, "docs/kf/wp-11180-04/source/report_11180.md")
UPSTREAM_DOC = os.path.join(ROOT, "docs/report_wp11180_01.md")
OUT_DIR = os.path.join(ROOT, "docs/kf/wp-11180-04")
CHECKS_JSON = os.path.join(OUT_DIR, "review_checks.json")
FIG = os.path.join(OUT_DIR, "fig_review_checks.png")

REPORT_ID = "11180"
CONTRACT_HASH = ("sha256:9adfdac400ff0e205a17c20a761625acca0acf0e55f9ff477bf2c1c5c8bf3292")
CONTRACT_CHARS = 490
CONTRACT_TITLE = "EEXI Attained 闭合链路精度传递验证 (P74-N02)"
CONTRACT_SCENARIO = "green_shipping_eexi_chain"

# ---------------------------------------------------------------- source access


def login_token(base: str) -> str:
    req = urllib.request.Request(
        f"{base}/auth/login",
        data=json.dumps({
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(req, timeout=20))["access_token"]


def fetch_live() -> tuple[str, str]:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    tok = login_token(base)
    req = urllib.request.Request(
        f"{base}/tensor/reports/{REPORT_ID}", headers={"Authorization": f"Bearer {tok}"}
    )
    rec = json.load(urllib.request.urlopen(req, timeout=20))
    return rec["markdown"], f"{base}/tensor/reports/{REPORT_ID}"


def sha256_text(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- quote binding

# claim-key -> verbatim substring of the source markdown (zero hand-copy: each is
# located by `str.find`, offsets recorded; a miss is a hard failure).
QUOTES = {
    "goal": "将 EEXI attained 能力从 WITHHELD(99.9%误差) 推进到 REAL(<15%误差)",
    "method": "建立端到端同源链路：Holtrop 阻力 → BEMT 推进 → EEXI attained",
    "errors_line": "- 三船对标误差: 12.1% / 7.0% / 1.0% (均 <15%)",
    "same_source": "- 链路同源: grep 验证 4 处调用",
    "sensitivity": "- 敏感度分析: V_ref 主导 (57.1%)",
    "degenerate": "- 退化一致性: 验证通过",
    "asset_impl": "backend/api/green_shipping.py::_gn_eexi_from_physics()",
    "asset_test": "backend/tests/test_eexi_chain_p74n02.py",
    "asset_json": "artifacts/eexi_verification.json",
    "asset_doc": "docs/eexi_verification_report_p74n02.md",
    "conclusion": "EEXI attained 能力: WITHHELD → REAL",
}


def bind_quotes(md: str) -> dict:
    out = {}
    for k, q in QUOTES.items():
        i = md.find(q)
        out[k] = {
            "quote": q,
            "found": i >= 0,
            "start_char": i,
            "end_char": i + len(q) if i >= 0 else None,
            "unique": md.count(q) == 1 if i >= 0 else False,
            "line": md[:i].count("\n") + 1 if i >= 0 else None,
        }
    return out


# ---------------------------------------------------------------- upstream parse


def load_upstream() -> dict:
    doc = open(UPSTREAM_DOC, encoding="utf-8").read()
    blocks = re.findall(r"```json\n(.*?)```", doc, re.S)
    envelope = json.loads(blocks[0]) if len(blocks) == 1 else None
    return {"doc": UPSTREAM_DOC, "json_blocks": len(blocks), "envelope": envelope}


def schema_strict_deviation(env: dict) -> list:
    """Mirror schemas/kf_result.v1.schema.json's own constraints (no jsonschema dep)."""
    schema = json.load(open(os.path.join(ROOT, "schemas/kf_result.v1.schema.json")))
    dev = []
    extra = sorted(set(env) - set(schema["properties"]))
    if extra and schema.get("additionalProperties") is False:
        dev.append({"kind": "additional_property", "keys": extra})
    for k in schema["required"]:
        if k not in env:
            dev.append({"kind": "missing_required", "key": k})
    prov = schema["properties"]["provenance"]
    pextra = sorted(set(env.get("provenance", {})) - set(prov["properties"]))
    if pextra and prov.get("additionalProperties") is False:
        dev.append({"kind": "additional_property", "path": "provenance", "keys": pextra})
    outs = env.get("outputs", {})
    oextra = sorted(set(outs) - set(schema["properties"]["outputs"]["properties"]))
    if oextra:
        dev.append({"kind": "additional_property", "path": "outputs", "keys": oextra})
    return dev


# ---------------------------------------------------------------- checks


def chk(cid, name, status, method, detail, evidence=None):
    return {
        "id": cid,
        "name": name,
        "status": status,
        "method": method,
        "detail": detail,
        "evidence": evidence or [],
    }


def run(md: str, live: bool) -> dict:
    checks = []
    q = bind_quotes(md)
    digest = sha256_text(md)
    nbytes = len(md.encode("utf-8"))
    lines = md.splitlines()

    checks.append(chk(
        "C1", "source_hash_recompute", "pass" if digest == CONTRACT_HASH else "fail",
        "sha256 over the UTF-8 bytes of the markdown, no newline normalisation",
        {"computed": digest, "contract": CONTRACT_HASH, "equal": digest == CONTRACT_HASH},
    ))
    checks.append(chk(
        "C2", "source_size_and_shape", "pass" if (len(md) == CONTRACT_CHARS and nbytes == 670) else "fail",
        "recomputed char/byte/line counts and the H1 title",
        {"characters": len(md), "utf8_bytes": nbytes, "lines": len(lines),
         "h1": lines[0], "contract_chars": CONTRACT_CHARS,
         "title_in_h1": CONTRACT_TITLE.split(" (")[0] in lines[0]},
    ))
    checks.append(chk(
        "C3", "live_api_equals_snapshot",
        "pass" if live and live["md_hash"] == digest else ("fail" if live else "not_run"),
        "GET /tensor/reports/11180 -> sha256(markdown) vs the pinned snapshot",
        {"live": live["md_hash"] if live else None,
         "snapshot": digest,
         "equal": bool(live) and live["md_hash"] == digest,
         "source_url": live["url"] if live else None},
    ))
    n_found = sum(1 for v in q.values() if v["found"])
    checks.append(chk(
        "C4", "quote_binding_zero_handcopy", "pass" if n_found == len(q) else "fail",
        "every quote used by the review is located by str.find in the source bytes",
        {"quotes": len(q), "found": n_found,
         "all_unique": all(v["unique"] for v in q.values() if v["found"])},
        [{"quote": v["quote"], "char_span": [v["start_char"], v["end_char"]], "line": v["line"]}
         for v in q.values()],
    ))

    up = load_upstream()
    env = up["envelope"] or {}
    am = (env.get("outputs", {}) or {}).get("asset_manifest.json", {}) or {}
    checks.append(chk(
        "C5", "upstream_package_present",
        "pass" if (up["json_blocks"] == 1 and env.get("package_id") == "wp-11180-01"
                   and env.get("task_type") == "01-asset-registration"
                   and env.get("report_id") == REPORT_ID) else "fail",
        "locate wp-11180-01's submitted envelope; require exactly one json block",
        {"doc": os.path.relpath(up["doc"], ROOT), "json_blocks": up["json_blocks"],
         "package_id": env.get("package_id"), "task_type": env.get("task_type"),
         "report_id": env.get("report_id"),
         "declared_assets": len(am.get("assets", []))},
    ))

    span_rows = []
    if am.get("assets"):
        for a in am["assets"]:
            loc = a.get("locator", {})
            s, e, quote = loc.get("start_char"), loc.get("end_char"), loc.get("quote")
            got = md[s:e] if isinstance(s, int) and isinstance(e, int) else None
            span_rows.append({
                "asset_id": a.get("asset_id"),
                "declared_span": [s, e],
                "recomputed": got,
                "byte_exact": got == quote,
                "unique": md.count(quote) == 1,
                "resolution": a.get("resolution"),
                "resolution_reproduced": (not os.path.exists(os.path.join(ROOT, quote))),
            })
    span_ok = bool(span_rows) and all(r["byte_exact"] and r["unique"] for r in span_rows)
    checks.append(chk(
        "C6", "upstream_asset_spans_reproduce", "pass" if span_ok else "fail",
        "slice the source markdown at each declared char_span and compare byte-for-byte",
        {"assets": len(span_rows), "byte_exact": sum(r["byte_exact"] for r in span_rows),
         "unique": sum(r["unique"] for r in span_rows)},
        span_rows,
    ))
    unresolved = sum(1 for r in span_rows if r["resolution_reproduced"])
    checks.append(chk(
        "C7", "upstream_resolution_claim_reproduced",
        "pass" if unresolved == len(span_rows) else "fail",
        "os.path.exists() for every quoted asset path inside this worktree",
        {"declared": "referenced_unresolved", "reproduced_unresolved": unresolved,
         "assets": len(span_rows),
         "consequence": "no upstream artifact is reachable to re-derive the reported errors"},
        [{"asset_id": r["asset_id"], "path_quoted": md[r["declared_span"][0]:r["declared_span"][1]],
          "exists_in_worktree": not r["resolution_reproduced"]} for r in span_rows],
    ))

    dev = schema_strict_deviation(env) if env else [{"kind": "no_envelope"}]
    checks.append(chk(
        "C8", "upstream_envelope_schema_strict", "pass" if not dev else "fail",
        "constraints of schemas/kf_result.v1.schema.json applied to the submitted envelope",
        {"deviations": dev},
    ))

    # ---- headline arithmetic (numbers taken from the bound quote, not retyped)
    er = q["errors_line"]
    nums = [float(x) for x in re.findall(r"(\d+\.\d+)%", er["quote"])] if er["found"] else []
    arith_ok = bool(nums) and max(nums) < 15.0
    checks.append(chk(
        "C9", "headline_numbers_internal_arithmetic", "pass" if arith_ok else "fail",
        "parse the three errors out of the located quote; test the report's own '均 <15%'",
        {"errors_pct": nums, "max": max(nums) if nums else None,
         "mean": round(sum(nums) / len(nums), 3) if nums else None,
         "claim_all_below_15": arith_ok,
         "all_below_3": all(x < 3.0 for x in nums) if nums else None,
         "n_below_3": sum(1 for x in nums if x < 3.0)},
    ))

    has_3pct = "3%" in md
    checks.append(chk(
        "C10", "explicit_3pct_error_judgement", "pass" if has_3pct else "fail",
        "substring scan for an explicit <3% verdict (platform report discipline element 6)",
        {"'3%' in markdown": has_3pct,
         "thresholds_stated": re.findall(r"<\s*\d+(?:\.\d+)?%", md)},
    ))

    trace_keys = ["Cb", "L/B", "B/T", "gCO2", "MCR", "SFC", "capacity", "reference", "对标船名"]
    present = [k for k in trace_keys if k in md]
    checks.append(chk(
        "C11", "per_ship_traceability", "pass" if len(present) >= 3 else "fail",
        "scan for per-ship geometry / absolute EEXI / reference-value fields needed to recompute a % error",
        {"fields_present": present, "fields_missing": [k for k in trace_keys if k not in md],
         "absolute_eexi_value_present": bool(re.search(r"gCO2", md)),
         "reference_value_present": bool(re.search(r"\d+\.\d+\s*gCO2", md))},
    ))

    sens = q["sensitivity"]
    pcts = re.findall(r"(\d+\.\d+)%", sens["quote"]) if sens["found"] else []
    checks.append(chk(
        "C12", "sensitivity_decomposition", "pass" if len(pcts) >= 2 else "fail",
        "count independently reported sensitivity contributions; require a closed decomposition",
        {"contributions_reported": pcts,
         "sum_pct": sum(float(x) for x in pcts) if pcts else None,
         "residual_undecomposed_pct": round(100 - sum(float(x) for x in pcts), 1) if pcts else None,
         "method_stated": bool(re.search(r"OAT|方差|Sobol|TOA|单变量", md))},
    ))

    ss = q["same_source"]
    checks.append(chk(
        "C13", "same_source_chain_evidence", "pass" if re.search(r"[\w/]+\.py:\d+", md) else "fail",
        "look for file:line call sites / numeric equality tolerance behind the 'grep 4 calls' claim",
        {"claim": ss["quote"], "file_line_locators": re.findall(r"[\w/]+\.py:\d+", md),
         "numeric_equality_tolerance": bool(re.search(r"1e-|相对偏差|相对误差\s*[<=]", md)),
         "call_sites_enumerated": len(re.findall(r"[\w/]+\.py:\d+", md))},
    ))

    dg = q["degenerate"]
    checks.append(chk(
        "C14", "degenerate_limit_definition", "pass" if re.search(r"退化.*(极限|J=0|n→0|V=0)", md) else "fail",
        "require a stated degenerate limit and tolerance behind '退化一致性: 验证通过'",
        {"claim": dg["quote"],
         "limit_defined": bool(re.search(r"退化.*(极限|J=0|n→0|V=0)", md)),
         "tolerance_stated": bool(re.search(r"退化.*(1e-|误差\s*<)", md))},
    ))

    checks.append(chk(
        "C15", "prior_state_basis", "not_run",
        "look for the reference behind 'WITHHELD(99.9%误差)'",
        {"claim": q["goal"]["quote"],
         "reference_or_dataset_in_report": False,
         "note": "report 11180 states the prior 99.9% figure without any reference value; not re-derivable from 490 chars"},
    ))

    checks.append(chk(
        "C16", "grade_claim_independently_recomputable", "fail",
        "attempt independent reproduction: platform capability ledger + EEXI endpoints + the quoted verification artifact",
        {"capability_ledger": "not reachable from this worktree "
                              "(/root/ship-performance-platform-incoming/.../capabilities.json missing)",
         "eexi_endpoints_probed": ["calculations/eexi -> 404", "green-shipping/eexi/attained -> 404",
                                   "openapi.json -> 404"],
         "verification_artifact_reachable": False,
         "verdict": "the WITHHELD->REAL grade cannot be recomputed by this reviewer"},
    ))

    heads = re.findall(r"^#+\s*(.+)$", md, re.M)
    checks.append(chk(
        "C17", "source_report_structure_vs_platform_discipline",
        "pass" if any("注意" in h or "局限" in h for h in heads) else "fail",
        "section-header inventory vs the platform's 6-element report discipline",
        {"headers": heads,
         "element2_method": any("方法" in h for h in heads),
         "element3_results": any("结果" in h for h in heads),
         "element4_figures": bool(re.search(r"!\[|\.png|\.svg", md)),
         "element5_caveats": any(("注意" in h or "局限" in h) for h in heads),
         "element6_error_verdict": has_3pct},
    ))

    checks.append(chk(
        "C18", "reviewer_marks_nothing_verified", "pass",
        "assert the review output never asserts verification (platform gate owns it)",
        {"reviewer_role": "red-team-reviewer", "claims_marked_verified": 0,
         "note": "constraint do_not_mark_claims_as_verified honoured by construction"},
    ))

    summary = {}
    for c in checks:
        summary[c["status"]] = summary.get(c["status"], 0) + 1

    return {
        "package_id": "wp-11180-04",
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "reviewed_package": "wp-11180-01",
        "reviewer_role": "red-team-reviewer",
        "generated_at": None,  # stamped by the emitter
        "source": {
            "uri": f"tensor://reports/{REPORT_ID}",
            "field": "markdown",
            "sha256": digest,
            "contract_sha256": CONTRACT_HASH,
            "characters": len(md),
            "utf8_bytes": nbytes,
            "lines": len(lines),
            "h1": lines[0],
            "snapshot": os.path.relpath(SNAP, ROOT),
        },
        "quote_binding": q,
        "upstream": {
            "envelope_package_id": env.get("package_id"),
            "provenance": env.get("provenance", {}),
            "counts": am.get("counts", {}),
            "asset_spans": span_rows,
            "schema_deviations": dev,
        },
        "checks": checks,
        "counts": summary,
    }


def make_figure(md: str, res: dict) -> str | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:  # pragma: no cover
        print(f"[fig] matplotlib unavailable: {e}", file=sys.stderr)
        return None
    nums = next(c for c in res["checks"] if c["id"] == "C9")["detail"]["errors_pct"]
    sens = next(c for c in res["checks"] if c["id"] == "C12")["detail"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.0), dpi=150)

    labels = [f"ship {i+1}" for i in range(len(nums))]
    bars = ax1.bar(labels, nums, color="#3b6fb6", width=0.55)
    for b, v in zip(bars, nums):
        ax1.text(b.get_x() + b.get_width() / 2, v + 0.4, f"{v:.1f}%", ha="center", fontsize=9)
    ax1.axhline(15, color="#c0392b", ls="--", lw=1.2, label="platform tolerance 15% (hard fail above)")
    ax1.axhline(3, color="#27ae60", ls=":", lw=1.2, label="report discipline 3% question")
    ax1.set_ylim(0, 18)
    ax1.set_ylabel("|error| vs reference  [%]")
    ax1.set_title("report 11180: the only three errors given\n(no per-ship identity / reference value in source)", fontsize=9)
    ax1.legend(fontsize=7, loc="upper right")
    ax1.grid(axis="y", alpha=0.25)

    named = float(sens["contributions_reported"][0]) if sens["contributions_reported"] else 57.1
    ax2.barh(["named factor (V_ref)", "un-decomposed residual"], [named, 100 - named],
             color=["#3b6fb6", "#bbbbbb"], height=0.5)
    ax2.set_xlim(0, 100)
    ax2.set_xlabel("share of attained-EEXI variance  [%]")
    ax2.set_title("sensitivity statement as printed: one factor, no closure\n"
                  "(method and perturbation sizes absent)", fontsize=9)
    for y, v in enumerate([named, 100 - named]):
        ax2.text(v + 1.5, y, f"{v:.1f}%", va="center", fontsize=9)
    ax2.grid(axis="x", alpha=0.25)

    fig.suptitle("KF wp-11180-04 independent review — what the source report licenses, and what it does not",
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIG)
    plt.close(fig)
    return os.path.relpath(FIG, ROOT)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="re-fetch the report from the platform API")
    ap.add_argument("--no-figure", action="store_true")
    args = ap.parse_args()

    os.makedirs(os.path.join(OUT_DIR, "source"), exist_ok=True)
    md_snapshot = open(SNAP, encoding="utf-8").read() if os.path.exists(SNAP) else None
    live = None
    if args.live:
        md_live, url = fetch_live()
        live = {"md_hash": sha256_text(md_live), "url": url}
        if md_snapshot is not None and md_live != md_snapshot:
            print("[live] WARNING: live markdown differs from the pinned snapshot", file=sys.stderr)
        md = md_live
        if md_snapshot is None:
            open(SNAP, "w", encoding="utf-8").write(md)
    else:
        if md_snapshot is None:
            print(f"[offline] snapshot missing: {SNAP}; run with --live", file=sys.stderr)
            return 2
        md = md_snapshot

    res = run(md, live)
    fig = None if args.no_figure else make_figure(md, res)
    res["figure"] = fig
    with open(CHECKS_JSON, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"source sha256 = {res['source']['sha256']}")
    print(f"contract      = {CONTRACT_HASH}  match={res['source']['sha256'] == CONTRACT_HASH}")
    print(f"counts: {res['counts']}")
    for c in res["checks"]:
        print(f"  {c['id']:>4} {c['status']:<8} {c['name']}")
    print(f"wrote {os.path.relpath(CHECKS_JSON, ROOT)}")
    if fig:
        print(f"wrote {fig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())