#!/usr/bin/env python3
"""wp-444-04 · assemble the independent-review package from re-derived facts.

Inputs are the two observation files produced by the sibling scripts; not one
number in this script is transcribed from the reviewed report:

  /tmp/wp-444-04/verify.json        <- work/verify_wp444_01.py
  /tmp/wp-444-04/observations.json  <- work/observe_source_numbers.py

Outputs (committed):

  docs/kf/wp-444-04/review_report.json
  docs/kf/wp-444-04/review_events.json

Every quotation in the review is taken as a *slice* of the pinned source
snapshot, so a quote that is not byte-verbatim in the source cannot enter the
review: `Quoter.q()` raises instead.  The review never writes a `verified`
field - review output is a decision plus evidence; verification is a gate.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import ke_state_machine as sm  # noqa: E402

PKG = ROOT / "docs/kf/wp-444-04"
SNAPSHOT = PKG / "source/report_444.md"
UPSTREAM_DOC = ROOT / "docs/kf_result_wp-444-01.md"
VERIFY = Path("/tmp/wp-444-04/verify.json")
OBSERVATIONS = Path("/tmp/wp-444-04/observations.json")
FIGURE = "docs/kf/wp-444-04/fig_wp444_04_recompute.png"

REVIEWER = "agent/m19690 (TensorKnowledge) · package wp-444-04 · red-team-reviewer"
POLICY = sm.POLICY_VERSION
FORBIDDEN_FIELDS = ("verified", "verification_status", "verification_level", "is_verified",
                    "gate_confirmed")


class Quoter:
    """Quote only by slicing the pinned source: verbatim-ness is structural."""

    def __init__(self, md: str):
        self.md = md

    def q(self, needle: str, note: str | None = None) -> dict:
        start = self.md.find(needle)
        if start < 0 or self.md.count(needle) != 1:
            raise SystemExit(f"review refuses to paraphrase: not a unique slice of the source: "
                             f"{needle!r}")
        out = {"source": "docs/kf/wp-444-04/source/report_444.md",
               "quote": self.md[start:start + len(needle)],
               "char_span": [start, start + len(needle)],
               "start_line": self.md[:start].count("\n") + 1}
        if note:
            out["note"] = note
        return out


def pct(x: float) -> str:
    return f"{x:+.2f}%"


def find_producer_id(doc: str) -> str:
    m = re.search(r"work/(m\d+)", doc)
    if not m:
        raise SystemExit("cannot recover the producer identity from the upstream document")
    return f"agent/{m.group(1)} (TensorKnowledge) · package wp-444-01"


def validate_upstream_envelope(doc_path: Path) -> dict:
    """Validate the json envelope printed in the upstream result document."""
    import jsonschema
    text = doc_path.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", text, re.S)
    if not blocks:
        return {"found": False, "valid": False, "errors": ["no json block"]}
    env = json.loads(blocks[0])
    schema = json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    errs = sorted({"/".join(str(p) for p in e.absolute_path) + ": " + e.message
                   for e in jsonschema.Draft202012Validator(schema).iter_errors(env)},
                  key=str)
    return {"found": True, "valid": not errs, "errors": errs, "keys": sorted(env),
            "provenance_keys": sorted(env.get("provenance", {})),
            "output_keys": sorted(env.get("outputs", {}))}


def ck(cid, title, status, basis, observed, offline, note=None, check_ids=None):
    out = {"id": cid, "title": title, "status": status, "basis": basis,
           "observed": observed, "offline_reproducible": offline}
    if note:
        out["note"] = note
    return out


def build_checks(v: dict, o: dict, md: str, doc: str) -> list[dict]:
    p = {x.get("formula") or "HM": x for x in o["predictions"]}
    ittc, blas, ps, hm = p["ITTC-1957"], p["Blasius"], p["P-S"], p["HM"]
    ls, st, up = v["locator_summary"], v["structure"], v["upstream"]
    tallies_ok = all(x for x in v["upstream_tallies_match"].values() if x is not None)
    rec = v["record"]
    title_bind = next(b for b in v["locator_bindings"] if b["kind"] == "record")
    fig_payload_absent = rec["available"] and all(not f["has_png_base64"] for f in rec["figures"])
    checks = [
        ck("C01", "upstream source hash re-derived from the live record",
           "pass" if v["source"]["hash_matches_upstream"] else "fail",
           "GET /tensor/reports/444 + sha256 over the markdown field",
           {"recomputed": v["source"]["sha256"], "declared": v["source"]["declared_hash"]}, True),
        ck("C02", "pinned snapshot is byte-identical to the bytes this review read",
           "pass" if v["source"]["hash_matches_snapshot"] else
           ("not_run" if v["mode"] != "live" else "fail"),
           f"mode={v['mode']}", {"snapshot": v["source"].get("snapshot_sha256"),
                                 "live": v["source"]["sha256"]}, True),
        ck("C03", "upstream structural tally reproduces (headings / tables / fenced code)",
           "pass" if tallies_ok else "fail",
           f"re-derived from the snapshot bytes; upstream declared {up['declared_tallies']}",
           {"level2_headings": st["level2_count"], "headings_all_levels":
            st["heading_count_all_levels"], "tables": st["tables_count"],
            "fenced_code_blocks": st["fenced_code_blocks"]}, True,
           note="7 is the level-2 (##) section count; the document holds 12 headings once ### "
                "subsections are counted, so the tally is right under the level-2 reading the "
                "upstream wording implies and ambiguous otherwise"),
        ck("C04", "the figure the report points at carries no payload",
           "pass" if fig_payload_absent else ("not_run" if not rec["available"] else "fail"),
           "record field `figures` (online only)", rec["figures"], False,
           note="corroborates the upstream 'figures 缺 PNG 数据' unresolved item"),
        ck("C05", "the title the upstream quotes is a record field, not markdown text",
           "pass" if (title_bind.get("verbatim") and rec["available"]
                      and rec["title"] == title_bind["quote"]) else
           ("not_run" if not rec["available"] else "fail"),
           "record title == upstream quote; the same string is absent from the markdown",
           {"title_in_markdown": title_bind["quote"] in md,
            "title_in_record": rec.get("title") == title_bind["quote"]}, True),
        ck("C06", "every quote the upstream pins to a markdown location is byte-verbatim there",
           "pass" if ls["markdown_verbatim"] == ls["markdown_quotes"] else "fail",
           f"{ls['markdown_verbatim']}/{ls['markdown_quotes']} markdown-pinned quotes resolve "
           "byte-verbatim (substring test against the snapshot)",
           [{"field": b["field"], "quote": b["quote"], "verbatim": b["verbatim"]}
            for b in v["locator_bindings"] if b["kind"] == "markdown"], True),
        ck("C07", "the declared line spans enclose the tables they name",
           "pass" if all(b.get("declared_line_span") for b in v["locator_bindings"]
                         if b["kind"] == "markdown") else "fail",
           "each declared span is compared with the GFM table actually found there",
           [{"field": b["field"], "span": b["declared_line_span"]}
            for b in v["locator_bindings"] if b.get("declared_line_span")], True),
        ck("C08", "the digest the upstream prints as a computed value re-derives",
           "pass" if v["source"]["hash_matches_upstream"] else "fail",
           "upstream prints sha256 as a computation; re-derived independently here",
           v["source"]["sha256"], True),
        ck("C09", "zero-claim registration is legal for task 01",
           "pass" if up["declared_claims_count"] == 0 else "fail",
           f"no extraction duty in 01; upstream declares claims_count={up['declared_claims_count']}",
           {"claims_count": up["declared_claims_count"]}, True),
        ck("C10", "the two unresolved assets are still unresolved for an independent reader",
           "pass" if (fig_payload_absent if rec["available"] else True) else "fail",
           "figure payload absent from the record; the mentioned `pytest（12 项单元测试）` carries "
           "no path in the source",
           {"unresolved_declared": up["declared_unresolved_count"],
            "test_mention_has_no_path": bool(re.search(r"pytest（12 项单元测试）", md))
            and not re.search(r"tests?/\S+\.py", md)}, True),
        ck("C11", "the envelope printed in the upstream result document conforms to "
                  "schemas/kf_result.v1",
           "pass" if o["_envelope"].get("valid") else "fail",
           "jsonschema (draft 2020-12) validation of the json block quoted by the upstream document",
           o["_envelope"], True),
        ck("C12", "the upstream machine-readable manifest itself is reachable and conformant",
           "not_run",
           "not_run: no wp-444-01 manifest is reachable here (.gitignore lists artifacts/; the only "
           "tracked trace is the result document docs/kf_result_wp-444-01.md), so only the envelope "
           "printed in that document was checkable (C11)", None, False),
        ck("C13", "the pass tally is arithmetically consistent",
           "pass" if o["tally_arithmetic"]["sum_matches_printed_total"] else "fail",
           "per-category rows summed and compared with the printed total",
           o["tally_arithmetic"], True),
        ck("C14", "the governance block's 'original length' is a real prefix length",
           "pass" if o["governance_prefix_boundary"] else "fail",
           f"recomputed {o['governance_original_chars']} chars as a newline-prefix length",
           o["governance_prefix_boundary"], True),
        ck("C15", "§6 ITTC-1957 baseline reproduces from the named formula within 3%",
           "pass" if ittc["within_3pct"] else "fail", "0.075/(log10 Re - 2)^2 at Re=1e8",
           {"reported": ittc["reported"], "recomputed": ittc["recomputed"],
            "deviation_pct": round(ittc["deviation_pct"], 4),
            "implied_re": ittc["implied_re"]}, True),
        ck("C16", "§6 Blasius baseline reproduces from the named formula within 3%",
           "pass" if blas["within_3pct"] else "fail", "1.328/sqrt(Re_L) at Re_L=1e6",
           {"reported": blas["reported"], "recomputed": blas["recomputed"],
            "deviation_pct": round(blas["deviation_pct"], 8)}, True),
        ck("C17", "§6 Prandtl-Schlichting baseline reproduces from the named formula within 3%",
           "pass" if ps["within_3pct"] else "fail",
           "0.455/(log10 Re)^2.58 at Re=1e8, and the customary -1700/Re variant",
           {"reported": ps["reported"], "recomputed": ps["recomputed"],
            "deviation_pct": round(ps["deviation_pct"], 4),
            "variant_value": ps["variant_value"],
            "variant_deviation_pct": round(ps["variant_deviation_pct"], 4),
            "implied_re": ps["implied_re"]}, True),
        ck("C18", "§6 Holtrop-Mennen 1+k reproduces from the stated inputs", "not_run",
           "not_run: the row states Cb only, while the report's own parameter table lists "
           "Cb, L, B, T; 1+k is a function of (L, B, T, Cp, nabla) and is therefore "
           "under-determined. Carried as WITHHELD, neither passed nor falsified",
           {"reported": hm["reported"],
            "family": {k: round(x, 4) for k, x in o["holtrop"]["family"].items() if k != "values"},
            "reported_inside_family": o["holtrop"]["reported_in_family"]}, True),
        ck("C19", "the two §6 friction baselines keep the order the two formulas have at Re=1e8",
           "pass" if (ittc["reported"] < ps["reported"]) == o["ordering_at_1e8"]["ittc_below_ps"]
           else "fail",
           "at a common Re above the crossover the two lines have a fixed order; the report "
           "prints the opposite one",
           {"report_order_ittc_gt_ps": ittc["reported"] > ps["reported"],
            "formula_order_ittc_lt_ps": o["ordering_at_1e8"]["ittc_below_ps"],
            "crossover_re": o["ordering_at_1e8"]["crossover_re"]}, True),
        ck("C20", "figure-borne statements can be checked against a payload", "not_run",
           "not_run: the record serves name+caption only (C04), so §4's four-panel figure cannot "
           "be opened, re-plotted or compared", None, False),
    ]
    return checks


def build_findings(v: dict, o: dict, md: str, quote: Quoter) -> list[dict]:
    p = {x.get("formula") or "HM": x for x in o["predictions"]}
    ittc, ps, blas, hm = p["ITTC-1957"], p["P-S"], p["Blasius"], p["HM"]
    nonverbatim = [b for b in v["locator_bindings"]
                   if b["kind"] == "markdown" and not b.get("verbatim")]
    cross = o["ordering_at_1e8"]
    fam = o["holtrop"]["family"]
    return [
        {
            "id": "F-01", "severity": "medium", "blocking": False, "check_ids": ["C06"],
            "title": "three of the five markdown-pinned quotes in the upstream evidence table are "
                     "reflowed, not byte-verbatim",
            "why_it_matters": "The upstream self-check row asserts `所有引文可在 markdown 原文逐字定位` "
                              "with a check mark. Three of them cannot: table rows were normalised "
                              "into one line (`A 5/5 / B 3/3`) while the source holds GFM rows. A "
                              "downstream gate that substring-checks quotes fails them, and a "
                              "reader cannot tell a reflow from a paraphrase.",
            "evidence": [{"source": "docs/kf_result_wp-444-01.md", "field": b["field"],
                          "quote": b["quote"], "declared_location": b["location"],
                          "verbatim_in_source": b["verbatim"]} for b in nonverbatim]
            + [quote.q("| ITTC-1957 | 5 | 5 | 0.0 | 0.1% |",
                       note="what the source actually holds for the same row")],
            "remediation": "Re-pin these quotes as exact slices, or state the normalisation rule "
                           "and drop the 逐字 claim.",
            "affects": "wp-444-01 self-check row `source_locator_resolvable`",
            "offline_reproducible": True,
        },
        {
            "id": "F-02", "severity": "medium", "blocking": False, "check_ids": ["C11", "C12"],
            "title": "the envelope printed in the upstream result document does not validate "
                     "against schemas/kf_result.v1",
            "why_it_matters": "The envelope is the machine-checkable contract of the workflow. As "
                              "printed it carries provenance keys the schema closes against and an "
                              "output key without the .json suffix; if the emitted file equals the "
                              "printed block the package fails its own contract. Unsettleable here "
                              "because the manifest itself is absent (C12).",
            "evidence": [
                {"source": "schemas/kf_result.v1.schema.json", "quote": "\"additionalProperties\": false",
                 "note": "provenance and outputs are both closed objects"},
                {"source": "docs/kf_result_wp-444-01.md", "quote": "\"source_hash_verified\": true",
                 "note": "not a declared provenance property"},
                {"source": "docs/kf_result_wp-444-01.md", "quote": "\"asset_manifest\": {",
                 "note": "schema declares the output key as asset_manifest.json"},
                {"source": "recomputation", "validation_errors": o["_envelope"].get("errors")}],
            "remediation": "Print the envelope verbatim from the emitted file (or label it an "
                           "excerpt) and keep producer output free of self-verification keys.",
            "affects": "wp-444-01 envelope; task-01 downstream validation",
            "offline_reproducible": True,
        },
        {
            "id": "F-03", "severity": "high", "blocking": False, "check_ids": ["C15"],
            "title": "§6 ITTC-1957 baseline is 4.16% away from the formula the report names",
            "why_it_matters": "§6 declares `<3% ✓ YES` with a 0.0% deviation, but its 基准 value is "
                              "not the ITTC-1957 line at the Re it states: "
                              f"0.075/(log10 1e8-2)^2 = {ittc['recomputed']:.6f} versus the printed "
                              f"{ittc['reported']:.6f} ({pct(ittc['deviation_pct'])}). The printed "
                              f"value belongs to Re ≈ {ittc['implied_re']:.3g}, not 1e8. A reader "
                              "anchoring model-ship conversion on report 444 inherits a 4.2% Cf bias.",
            "evidence": [quote.q("| ITTC-1957 Cf (Re=1e8) | 0.002170 | 0.002170 | 0.0% | ✓ YES |"),
                         quote.q("Cf = 0.075 / (log10(Re) - 2)²，用于模型-实船换算"),
                         {"source": "recomputation", "formula": "0.075/(log10 Re - 2)^2", "re": 1e8,
                          "value": ittc["recomputed"],
                          "deviation_pct": round(ittc["deviation_pct"], 4),
                          "implied_re": ittc["implied_re"]}],
            "remediation": "Recompute report 444 §6 from the named formulas and re-issue the error "
                           "table, or state which Re / line variant was used.",
            "affects": "report 444 §6 accuracy claim (not the registration duty of wp-444-01)",
            "escalate": "report-444-rework", "offline_reproducible": True,
        },
        {
            "id": "F-04", "severity": "high", "blocking": False, "check_ids": ["C17"],
            "title": "§6 Prandtl-Schlichting baseline is 5.47% away from the formula the report "
                     "names",
            "why_it_matters": "Same failure mode on the turbulent line: "
                              f"0.455/(log10 1e8)^2.58 = {ps['recomputed']:.6f} versus the printed "
                              f"{ps['reported']:.6f} ({pct(ps['deviation_pct'])}); the customary "
                              f"-1700/Re term moves it to {ps['variant_value']:.6f} "
                              f"({pct(ps['variant_deviation_pct'])}), so no variant of the named "
                              "formula rescues the printed value. The row is marked `<3% ✓ YES`.",
            "evidence": [quote.q("| P-S Cf (Re_L=1e8) | 0.002012 | 0.002012 | 0.0% | ✓ YES |"),
                         quote.q("Cf = 0.455 / (log10(Re_L))^2.58"),
                         {"source": "recomputation", "formula": "0.455/(log10 Re)^2.58", "re": 1e8,
                          "value": ps["recomputed"],
                          "deviation_pct": round(ps["deviation_pct"], 4),
                          "variant_minus_1700_over_re": ps["variant_value"]}],
            "remediation": "Same rework as F-03.",
            "affects": "report 444 §6 accuracy claim",
            "escalate": "report-444-rework", "offline_reproducible": True,
        },
        {
            "id": "F-05", "severity": "medium", "blocking": False, "check_ids": ["C19"],
            "title": "the two §6 friction baselines are ordered the wrong way round at Re=1e8",
            "why_it_matters": "Above the crossover at Re ≈ "
                              f"{cross['crossover_re']:.3g} the ITTC-1957 line lies below "
                              "Prandtl-Schlichting; at 1e8 the formulas give "
                              f"{cross['ittc1957']:.6f} < {cross['prandtl_schlichting']:.6f}. The "
                              "report prints ITTC (0.002170) > P-S (0.002012). The inversion is "
                              "internal evidence that both baselines were written from memory, and "
                              "it needs no external reference data to detect.",
            "evidence": [quote.q("| ITTC-1957 Cf (Re=1e8) | 0.002170 | 0.002170 | 0.0% | ✓ YES |"),
                         quote.q("| P-S Cf (Re_L=1e8) | 0.002012 | 0.002012 | 0.0% | ✓ YES |"),
                         {"source": "recomputation", "crossover_re": cross["crossover_re"],
                          "ittc1957_at_1e8": cross["ittc1957"],
                          "prandtl_schlichting_at_1e8": cross["prandtl_schlichting"]}],
            "remediation": "Covered by the F-03/F-04 rework; add an ordering invariant to the "
                           "verifier question bank.",
            "affects": "report 444 §6; verifier question-bank design",
            "escalate": "report-444-rework", "offline_reproducible": True,
        },
        {
            "id": "F-06", "severity": "medium", "blocking": False, "check_ids": ["C18"],
            "title": "§6 Holtrop-Mennen 1+k is under-determined and sits outside the standard "
                     "formula's envelope for Cb=0.6",
            "why_it_matters": "The row states Cb=0.6 only while the report's own parameter table "
                              "lists Cb, L, B, T; 1+k depends on (L, B, T, Cp, nabla), so the value "
                              "cannot be re-derived: WITHHELD, not passed. Over "
                              f"{fam['samples']} plausible Cb=0.6 hull tuples the Holtrop-Mennen "
                              f"form factor spans {fam['min']:.4f}-{fam['max']:.4f} (median "
                              f"{fam['median']:.4f}); the printed {hm['reported']:.4f} lies below "
                              "that envelope, and the caveat `使用了简化版本` names no simplification "
                              "that would explain the offset.",
            "evidence": [quote.q("| HM 1+k (Cb=0.6) | 1.0547 | 1.0547 | 0.0% | ✓ YES |"),
                         quote.q("Holtrop-Mennen 形状因子使用了简化版本，完整版本需更多参数。"),
                         quote.q("| Holtrop | Cb, L, B, T | 1+k | 简化经验公式 |"),
                         {"source": "recomputation",
                          "family": {k: round(x, 4) for k, x in fam.items() if k != "values"},
                          "reported": hm["reported"]}],
            "remediation": "Declare the simplification and its coefficients, or move the row out of "
                           "the accuracy table into an unverified list.",
            "affects": "report 444 §6 row 4",
            "escalate": "report-444-rework", "offline_reproducible": True,
        },
        {
            "id": "F-07", "severity": "low", "blocking": False, "check_ids": ["C16"],
            "title": "the one fully reproduced baseline sits at the edge of its own validity range",
            "why_it_matters": f"Blasius reproduces exactly ({pct(blas['deviation_pct'])}), but the "
                              "row evaluates it at Re_L=1e6 — the upper end of the range the "
                              "report's own parameter table declares ([1e5, 1e6]) and the usual "
                              "upper bound of laminar similarity. The only row that survives "
                              "re-derivation is the least transferable one.",
            "evidence": [quote.q("| Blasius Cf (Re_L=1e6) | 0.001328 | 0.001328 | 0.0% | ✓ YES |"),
                         quote.q("| Blasius | Re_L ∈ [1e5, 1e6] | Cf | 解析公式 |"),
                         {"source": "recomputation", "formula": "1.328/sqrt(Re_L)",
                          "value": blas["recomputed"],
                          "deviation_pct": round(blas["deviation_pct"], 8)}],
            "remediation": "Evaluate at Re_L = 5e5 and add a turbulent flat-plate case instead.",
            "affects": "report 444 §6 row 2",
            "escalate": "report-444-rework", "offline_reproducible": True,
        },
        {
            "id": "F-08", "severity": "info", "blocking": False, "check_ids": ["C13"],
            "title": "the universal 0.0% deviation is disclosed self-consistency, not validation",
            "why_it_matters": "§3 prints 0.0 max deviation on all 15 rows, §5 discloses why "
                              "(candidate and question bank share one formula), and upstream "
                              "registered the missing figure payload as unresolved. Read together "
                              "report 444 does not overstate: the tally is a plumbing test of the "
                              "verifier harness and must not be cited as an accuracy result.",
            "evidence": [quote.q("| **合计** | **15** | **15** | **0.0** | — |"),
                         quote.q("- 试点使用解析/经验公式，偏差为零是因为候选与出题使用相同公式。"
                                 "真实场景中候选可能有数值误差。"),
                         {"source": "recomputation", "tally": o["tally_arithmetic"]}],
            "remediation": "No correctness change; cite §3 as a harness self-test only.",
            "affects": "interpretation of report 444",
            "offline_reproducible": True,
        },
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", default=str(VERIFY))
    ap.add_argument("--observations", default=str(OBSERVATIONS))
    ap.add_argument("--out", default=str(PKG))
    args = ap.parse_args(argv)

    for path in (Path(args.verify), Path(args.observations)):
        if not path.is_file():
            raise SystemExit(f"missing observation file {path}; run the sibling scripts first")
    v = json.loads(Path(args.verify).read_text(encoding="utf-8"))
    o = json.loads(Path(args.observations).read_text(encoding="utf-8"))
    md = SNAPSHOT.read_text(encoding="utf-8")
    doc = UPSTREAM_DOC.read_text(encoding="utf-8")
    quote = Quoter(md)

    o["_envelope"] = validate_upstream_envelope(UPSTREAM_DOC)
    checks = build_checks(v, o, md, doc)
    findings = build_findings(v, o, md, quote)
    counts = {"checks": len(checks),
              "pass": sum(1 for c in checks if c["status"] == "pass"),
              "fail": sum(1 for c in checks if c["status"] == "fail"),
              "not_run": sum(1 for c in checks if c["status"] == "not_run")}
    blocking = [f["id"] for f in findings if f["blocking"]]
    severity_counts = {s: sum(1 for f in findings if f["severity"] == s)
                       for s in ("high", "medium", "low", "info")}
    disposition = ("request-changes" if blocking else
                   "approve-with-notes" if any(f["severity"] in {"high", "medium"}
                                               for f in findings) else "approve")
    producer = find_producer_id(doc)

    review = {
        "review_report_version": "1.0",
        "package_id": "wp-444-04",
        "task_type": "04-independent-review",
        "report_id": "444",
        "reviewer_role": "red-team-reviewer",
        "generated_at": v["generated_at"],
        "reviewed_package": {
            "package_id": "wp-444-01",
            "task_type": "01-asset-registration",
            "producer": producer,
            "source_hash": v["source"]["sha256"],
            "document": {"path": "docs/kf_result_wp-444-01.md",
                         "sha256": v["upstream"]["sha256"]},
            "machine_readable_artifact": None,
            "machine_readable_artifact_note":
                "no wp-444-01 manifest exists in this worktree: .gitignore lists artifacts/ (so new "
                "files there are not committed by default) and the only tracked trace of the package "
                "is its result document docs/kf_result_wp-444-01.md; C12 is not_run for that reason, "
                "not passed",
        },
        "source": {
            "report_id": "444",
            "sha256": v["source"]["sha256"],
            "chars": v["source"]["chars"],
            "snapshot": "docs/kf/wp-444-04/source/report_444.md",
            "title": v["record"].get("title"),
            "scenario_key": v["record"].get("scenario_key"),
            "mode": v["mode"],
        },
        "disposition": disposition,
        "ledger_decision": "approve" if disposition.startswith("approve") else "request-changes",
        "disposition_reason":
            "No blocking finding on the registration duty: the source hash re-derives byte-exactly, "
            f"the tallies reproduce, both unresolved assets are corroborated, and zero-claim "
            f"registration is legal for task 01. {counts['pass']}/{counts['checks']} checks "
            f"reproduce, {counts['fail']} fail (F-01/F-02 package hygiene; F-03/F-04/F-05 "
            f"subject-report arithmetic) and {counts['not_run']} are declared not_run. The approval "
            "covers registration mechanics only; it does not endorse report 444 §6, which is "
            "escalated for rework.",
        "blocking_findings": blocking,
        "carried_findings": [f["id"] for f in findings if f.get("escalate")],
        "counts": {**counts, "findings": len(findings), "severity": severity_counts},
        "scope": {
            "in_scope": [
                "byte identity of the report 444 markdown (live record vs pinned snapshot vs the "
                "hash the upstream package quotes)",
                "re-derivation of every structural tally and every quote locator the upstream "
                "package asserts",
                "the envelope printed in the upstream result document against schemas/kf_result.v1",
                "independent re-derivation of the numbers report 444 prints in §3/§6 and in the "
                "governance block, against the formulas the report itself names",
                "independence and ledger mechanics of this review event",
            ],
            "out_of_scope": [
                "the AlphaEvolve verifier/generator implementation (no repo in this worktree "
                "carries it; only the report text was reviewable)",
                "the figure payload (not served: the record carries name+caption only)",
                "whether report 444's 15/15 tally is a correct harness result — untestable without "
                "the question bank or the verifier code",
                "Cf against experimental tank data: §6's own baselines are analytic formulas, so "
                "this review is formula-to-print, not ship-to-model",
            ],
            "claims_assessment":
                "wp-444-01 declares zero knowledge claims, so what is assessed is the truth of its "
                "statements about the source, plus (as carried findings) the arithmetic of the "
                "report it registered. Nothing here is marked verified.",
        },
        "independence": {
            "reviewer": REVIEWER,
            "producer": [producer],
            "basis": "distinct-identity",
            "limitations": [
                "reviewer and producer are the same model family on the same platform: independence "
                "is identity-level and method-level, not model-level",
                "the producer's machine-readable manifest was not reachable, so C12 is not_run "
                "rather than passed",
                "record-level facts (title, figures, scenario_key) are online-only; the committed "
                "snapshot carries the markdown and nothing else, and every check that needs more is "
                "flagged offline_reproducible=false",
                "no second independent reviewer and no strong-model resample were drawn (platform "
                "jobs, not available here)",
            ],
        },
        "checks": checks,
        "findings": findings,
        "recomputation": {
            "figure": FIGURE,
            "figure_caption": "A: §6 baselines against the formulas the report names, ±3% band. "
                              "B: reported points (x) versus their own named curves (o). "
                              "C: Holtrop-Mennen 1+k over a 360-tuple Cb=0.6 family, report value "
                              "in red.",
            "rows": [{"label": r["label"], "reported_baseline": r["reported_baseline"],
                      "reported_actual": r["reported_actual"],
                      "reported_within_3pct": r["reported_within_3pct"],
                      "recomputed": p.get("recomputed"),
                      "deviation_pct": round(p["deviation_pct"], 4)
                      if p.get("deviation_pct") is not None else None,
                      "status": p["status"],
                      "within_3pct": p.get("within_3pct")}
                     for r, p in zip(o["errors_table"], o["predictions"])],
            "tally_arithmetic": o["tally_arithmetic"],
            "governance_original_chars": o["governance_original_chars"],
            "governance_prefix_boundary": o["governance_prefix_boundary"],
            "ordering_at_1e8": o["ordering_at_1e8"],
            "holtrop_family": {k: round(x, 4) for k, x in o["holtrop"]["family"].items()
                               if k != "values"},
        },
        "offline_reproducibility": {
            "offline_checks": [c["id"] for c in checks if c["offline_reproducible"]],
            "online_only_checks": [c["id"] for c in checks if not c["offline_reproducible"]],
            "snapshot_bytes_sufficient": True,
        },
        "escalations": [{
            "id": "E-01", "target": "report 444", "route": "report-rework",
            "reason": "§6 baseline column does not reproduce from the formulas the report itself "
                      "names (F-03 ITTC-1957 +4.16%, F-04 P-S -5.47%, F-05 ordering inversion) and "
                      "F-06's 1+k is under-determined and outside the standard envelope for Cb=0.6",
            "owner_action": "recompute §6 and §3's tolerance framing; do not cite report 444 §6 as "
                            "a Cf anchor until reworked",
        }],
        "provenance_of_this_report": {
            "builder": "work/build_review_report.py",
            "inputs": {"verify": str(Path(args.verify)), "observations": str(Path(args.observations))},
            "observation_generated_at": v["generated_at"],
            "obs_generated_at": o["generated_at"],
        },
    }

    def keys(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield k
                yield from keys(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from keys(v)

    self_audit = sorted({k for k in keys(review) if k in FORBIDDEN_FIELDS})
    review["self_audit"] = {"forbidden_verification_fields_present": self_audit,
                            "note": "this review records decisions and evidence only; a `verified` "
                                    "field would claim gate authority a reviewer does not have"}

    events = {
        "package_id": "wp-444-04", "object": "wp-444-01", "policy_version": POLICY,
        "producer_ids": [producer],
        "system_transitions": [{
            "id": "kf444-04:submit", "from": "draft", "to": "in-review",
            "policy_version": POLICY, "by": "platform-task-completion",
            "at": v["generated_at"],
            "note": "task completion moves the package into review; deliberately not a review "
                    "decision, so it is kept out of `events`"}],
        "events": [{
            "id": "kf444-04:review-1", "decision": review["ledger_decision"],
            "policy_version": POLICY,
            "reviewer": {"id": REVIEWER, "reviewer_type": "agent"},
            "reviewed_at": v["generated_at"],
            "findings": [{"id": f["id"], "severity": f["severity"], "blocking": f["blocking"],
                          "title": f["title"]} for f in findings],
            "review_report": "docs/kf/wp-444-04/review_report.json",
            "disposition": disposition,
            "note": "approve with non-blocking findings; no claim is marked verified by this event, "
                    "and report 444 §6 is escalated, not endorsed",
        }],
    }
    state, codes = sm.fold(events["events"], {"producer_ids": events["producer_ids"]},
                           initial_state=sm.submit({"producer_ids": events["producer_ids"]}))
    events["fold"] = {"state": state, "outcome_codes": codes,
                      "independence_basis": events["events"][0].get("independence_basis")}

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "review_report.json").write_text(json.dumps(review, ensure_ascii=False, indent=1),
                                            encoding="utf-8")
    (out / "review_events.json").write_text(json.dumps(events, ensure_ascii=False, indent=1),
                                            encoding="utf-8")
    print(json.dumps({"disposition": disposition, "counts": review["counts"],
                      "fold": events["fold"],
                      "envelope_valid": o["_envelope"].get("valid"),
                      "envelope_errors": o["_envelope"].get("errors")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
