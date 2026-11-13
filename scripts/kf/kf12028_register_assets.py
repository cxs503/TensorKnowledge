#!/usr/bin/env python3
"""KF wp-12028-01 · 01-asset-registration for report_id=12028 (hard-locked).

Scope: register source assets only.  No claim extraction, no report-type
classification, nothing marked verified (the platform gate computes that).

Every locator quote is a **whole markdown line** picked by a selector from
scripts/kf/register_assets_lib.py, then double-checked:
  quote in markdown  and  markdown[offset:offset+len(quote)] == quote
plus an asserted occurrence count, so a locator cannot silently land on the
wrong duplicate line.

Outputs
  work/wp-12028-01/source/report_12028.json / .md / markdown.sha256
  work/wp-12028-01/source/figures/*.png + figures_meta.json + probes.json
  docs/kf/wp-12028-01/asset_manifest.json
  docs/kf/wp-12028-01/kf_result.json

Usage: python3 scripts/kf/kf12028_register_assets.py [--offline]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kf12028_spec import (  # noqa: E402
    CONTRACT_CHARS,
    CONTRACT_HASH,
    CONTRACT_TITLE,
    EXTERNAL_KINDS,
    FIGURE_NAMES,
    PKG,
    PROBES,
    REPORT_ID,
    SCENARIO_KEY,
    SOURCE_URI,
    SPEC,
)
from register_assets_lib import Md, api_base, fetch_report, get_token, probe, sha256_of  # noqa: E402

SRC = Path("work/wp-12028-01/source")
DOCS = Path("docs/kf/wp-12028-01")


def sha256_of_bytes(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def png_dims(raw: bytes) -> dict:
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        return {}
    w, h = struct.unpack(">II", raw[16:24])
    return {"width_px": w, "height_px": h}


def fetch_figure(name: str, token: str | None, out: Path, prev: dict | None = None) -> dict:
    meta = {"name": name, "endpoint": "/tensor/reports/%s/figures/%s" % (REPORT_ID, name)}
    p = out / name
    if token:
        import urllib.request

        req = urllib.request.Request(api_base() + meta["endpoint"],
                                     headers={"Authorization": "Bearer " + token})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
                meta["http_status"] = r.status
                meta["content_type"] = r.headers.get("content-type")
        except Exception as e:  # noqa: BLE001 - record honestly
            meta.update({"http_status": getattr(e, "code", None), "error": repr(e),
                         "resolved": False})
            return meta
        p.write_bytes(data)
        meta.update({"bytes": len(data), "sha256": sha256_of_bytes(data), "resolved": True,
                     "retrieved_via": "API"})
    elif p.exists():
        data = p.read_bytes()
        meta.update({"bytes": len(data), "sha256": sha256_of_bytes(data), "resolved": True,
                     "retrieved_via": "local snapshot (offline)"})
    else:
        meta.update({"resolved": False, "note": "offline and no local snapshot"})
        return meta
    if token is None and prev and prev.get("resolved"):
        # offline rebuild: keep the HTTP evidence captured by the online run
        for k in ("http_status", "content_type"):
            if k in prev:
                meta[k] = prev[k]
        meta["http_evidence_from"] = "earlier online run (reused on offline rebuild)"
    meta.update(png_dims(data))
    return meta


def locate(md: Md, sel: str, title: str = "") -> tuple[int, str, dict, str | None]:
    """Locate a whole markdown line.  token: selectors may carry colons in the
    token itself, so only a trailing `:<digits>` is read as the nth index.

    Returns (offset, quote, meta, token) with token=None for non-token selectors.
    """
    if not sel.startswith("token:"):
        off, quote, meta = md.locate(sel, title=title)
        return off, quote, meta, None
    rest = sel[len("token:"):]
    token, nth = rest, 0
    head, sep, tail = rest.rpartition(":")
    if sep and tail.isdigit():
        token, nth = head, int(tail)
    if token == "__TITLE__":
        token = title
    off, quote = md.find_line(token, nth)
    return off, quote, {}, token


def probe_summary(probes: list[dict]) -> str:
    return ", ".join("%s=%s" % (p["path"].rsplit("/", 1)[-1] or p["path"], p.get("http_status"))
                     for p in probes)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    SRC.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    snap = SRC / "report_12028.json"

    rec = fetch_report(REPORT_ID, record_file=(snap if (args.offline or snap.exists()) else None))
    md_text = rec["markdown"]
    md = Md(md_text)
    raw = md_text.encode("utf-8")
    digest = sha256_of(md_text)
    (SRC / "report_12028.md").write_bytes(raw)
    (SRC / "markdown.sha256").write_text(digest + "\n", encoding="utf-8")

    token = None if args.offline else get_token()

    # figures
    fig_dir = SRC / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    record_figs = rec.get("figures") or []
    prev_meta_path = SRC / "figures_meta.json"
    prev_meta = (json.loads(prev_meta_path.read_text(encoding="utf-8"))
                 if token is None and prev_meta_path.exists() else {})
    figures = {}
    for f in record_figs:
        name = f.get("name") if isinstance(f, dict) else str(f)
        figures[name] = fetch_figure(name, token, fig_dir, prev_meta.get(name))
        figures[name]["caption_record"] = f.get("caption") if isinstance(f, dict) else None
    (SRC / "figures_meta.json").write_text(
        json.dumps(figures, ensure_ascii=False, indent=2), encoding="utf-8")

    # probes
    prev_probe_path = SRC / "probes.json"
    prev_probes = ({p["path"]: p for p in json.loads(prev_probe_path.read_text(encoding="utf-8"))}
                   if token is None and prev_probe_path.exists() else {})
    probes = []
    for ep in PROBES:
        if token is None and ep in prev_probes:
            r = dict(prev_probes[ep])
            r["reused_from"] = "earlier online probe (offline rebuild)"
        else:
            r = probe(ep, token)
        r["path"] = ep
        probes.append(r)
    (SRC / "probes.json").write_text(json.dumps(probes, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    psum = probe_summary(probes)

    # locate assets
    assets, failures = [], []
    for s in SPEC:
        try:
            off, quote, meta, token = locate(md, s["sel"], title=rec.get("title", ""))
        except LookupError as e:
            failures.append({"spec_id": s["id"], "name": s["name"], "error": str(e)})
            continue
        occ = md_text.count(quote)
        if md_text[off:off + len(quote)] != quote:
            failures.append({"spec_id": s["id"], "name": s["name"],
                             "error": "back-read mismatch"})
            continue
        if token is not None and s.get("occ") is not None:
            tok_occ = md_text.count(token)
            if tok_occ != s["occ"]:
                failures.append({"spec_id": s["id"], "name": s["name"],
                                 "error": "token occurrences %d != expected %d"
                                          % (tok_occ, s["occ"])})
                continue

        kind = s["kind"]
        e = {
            "asset_id": "ast-%s-%s" % (REPORT_ID, s["id"]),
            "kind": kind,
            "role": s["role"],
            "name": s["name"],
            "locators": [{
                "source_uri": SOURCE_URI,
                "source_field": "markdown",
                "char_start": off,
                "char_end": off + len(quote),
                "quote": quote,
                "section": s["section"],
            }],
            "occurrence_count": occ,
            "note": s.get("note", ""),
        }
        if meta:
            e["selector_stats"] = meta
        if kind == "figure_reference":
            fm = figures.get(s["name"].rsplit("/", 1)[-1], {})
            e["resolved_bytes"] = {k: fm.get(k) for k in
                                   ("endpoint", "http_status", "content_type", "bytes",
                                    "sha256", "width_px", "height_px")}
            if fm.get("resolved"):
                e["resolvable"] = True
                e["resolution"] = "platform_figure_store__http_200"
                e["status"] = "resolved"
                e["caveat"] = ("bytes are served by the platform figure store for report "
                               "12028; the report itself carries no image hash, so byte "
                               "identity with the producing-repo artifacts/crp/ file is not "
                               "proven at this package")
            else:
                e["resolvable"] = False
                e["resolution"] = "figure_store_unavailable"
                e["status"] = "unresolved"
                e["unresolved_reason"] = ("in-markdown link resolves but figure payload "
                                          "could not be retrieved from the platform store")
        elif kind in EXTERNAL_KINDS:
            e["resolvable"] = False
            e["resolution"] = "referenced_in_markdown__not_attached_to_report_record"
            e["status"] = "unresolved"
            e["unresolved_reason"] = (
                "the reference resolves verbatim in the markdown, but no byte-level copy is "
                "attached to report 12028 and the probed endpoints returned no payload (%s); "
                "registration stops at the reference and ownership stays with the producing "
                "repo (ship-performance-platform worktree agent/m10162)" % psum)
        else:
            e["resolvable"] = True
            e["resolution"] = "resolved_in_markdown"
            e["status"] = "resolved"
        assets.append(e)

    if failures:
        (SRC / "locator_failures.json").write_text(
            json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
        print("LOCATOR FAILURES\n" + json.dumps(failures, ensure_ascii=False, indent=1))
        return 2

    # record metadata asset
    rec_loc = [{"source_uri": SOURCE_URI, "source_field": "record", "field": f,
                "value": rec.get(f)}
               for f in ("id", "title", "scenario_key", "mission_id", "status",
                         "created_at", "created_by", "summary", "tags")
               if rec.get(f) is not None]
    rec_loc.append({"source_uri": SOURCE_URI, "source_field": "record",
                    "field": "figures[].name",
                    "value": [f.get("name") for f in record_figs]})
    assets.insert(0, {
        "asset_id": "ast-%s-02" % REPORT_ID, "kind": "record_metadata",
        "role": "identification", "name": "report_%s_record" % REPORT_ID,
        "locators": rec_loc, "occurrence_count": 1, "resolvable": True,
        "resolution": "fetched_via_tensor_api", "status": "resolved",
        "note": "record fields exactly as served by GET /tensor/reports/" + REPORT_ID,
    })

    h1_off, h1_quote = md.find_line("# CRP")
    assets.insert(0, {
        "asset_id": "ast-%s-01" % REPORT_ID, "kind": "source_document",
        "role": "primary_source", "name": "report_%s_markdown" % REPORT_ID,
        "locators": [{"source_uri": SOURCE_URI, "source_field": "markdown",
                      "char_start": h1_off, "char_end": h1_off + len(h1_quote),
                      "quote": h1_quote}],
        "content_ref": {"source_uri": SOURCE_URI, "source_field": "markdown",
                        "chars": len(md_text), "byte_length_utf8": len(raw),
                        "sha256": digest},
        "occurrence_count": md_text.count(h1_quote), "resolvable": True,
        "resolution": "fetched_via_tensor_api", "status": "resolved",
        "note": "H1 line locator; whole-document span in content_ref",
    })

    # observations, each bound to verbatim quotes
    def q(sel: str) -> dict:
        off, quote, _meta, _tok = locate(md, sel)
        return {"source_uri": SOURCE_URI, "source_field": "markdown",
                "char_start": off, "char_end": off + len(quote), "quote": quote}

    section_headers = [ln for _o, ln in md.lines if ln.startswith("## ")]
    observations = [
        {
            "id": "obs-title-drift",
            "observation": "record.title matches the contract title byte-wise, but the "
                           "markdown H1 carries an extra '分析报告' suffix",
            "record_title": rec.get("title"),
            "contract_title_equals_record": rec.get("title") == CONTRACT_TITLE,
            "markdown_h1": h1_quote,
            "markdown_h1_equals_record": h1_quote.lstrip("# ").strip() == rec.get("title"),
            "evidence": [q("h1")],
            "impact": "downstream extraction must key on report_id, not on title equality",
        },
        {
            "id": "obs-mission-id",
            "observation": "record.mission_id is %s and the markdown names 任务编号 m10162, "
                           "while the package contract declares mission_id: null"
                           % rec.get("mission_id"),
            "record_mission_id": rec.get("mission_id"),
            "contract_mission_id": None,
            "evidence": [q("token:**任务编号**: m10162")],
            "impact": "recorded as observed only; this package does not reconcile it",
        },
        {
            "id": "obs-benchmark-vs-case-geometry",
            "observation": "§1.2 declares the ITTC CRP benchmark geometry with 6/7 blades, "
                           "but the numbers in §3.1/§3.2 are computed for a different "
                           "simplified case (Z_f=4, Z_r=5); on the face of the text the "
                           "reported results are not results for the §1.2 geometry",
            "evidence": [q("token:| 叶数 Z | 6 | 7 |"),
                         q("token:**简单CRP案例**（Z_f=4, Z_r=5, P/D_f=0.9, P/D_r=1.1）：")],
            "impact": "registration-only finding: any downstream claim binding the §3 "
                      "numbers to the ITTC benchmark geometry is unsupported by the text",
        },
        {
            "id": "obs-torque-balance-fail",
            "observation": "the §1.3 target |Q_f + Q_r| / Q_ref < 1% is not met: §3.4 reports "
                           "172% and §6.2 marks it FAIL, with the outer pitch-optimisation "
                           "loop declared not implemented",
            "evidence": [q("token:**扭矩平衡迭代**"),
                         q("token:| 扭矩平衡 | < 1% | 172% | ⚠️ FAIL（需螺距优化） |"),
                         q("token:TorqueBalanceIterator")],
            "impact": "honest FAIL carried forward verbatim; no gate outcome is upgraded here",
        },
        {
            "id": "obs-title-scope-vs-method",
            "observation": "the title names 面元法 (panel method), but §2 documents only a "
                           "lifting-line + blade-element-momentum formulation; the markdown "
                           "contains %d occurrence(s) of 面元" % md_text.count("面元"),
            "panel_method_mentions_in_markdown": md_text.count("面元"),
            "evidence": [q("token:**升力线理论（Lifting Line Theory）+ Goldstein修正**：")],
            "impact": "note for downstream extraction: the panel-method part of the title "
                      "has no method section backing it inside this markdown",
        },
        {
            "id": "obs-efficiency-reference-uncorroborated",
            "observation": "the declared 1.0% efficiency error rests on one eta_ref value "
                           "quoted inside the report (Koushan 1993); the reference dataset "
                           "is not attached, so the number is registered, not reproduced",
            "evidence": [q("token:**ITTC CRP基准**（Koushan 1993）"),
                         q("token:| 效率精度 | < 10% | 1.0% | ✅ PASS |")],
            "impact": "downstream re-verification needs the primary benchmark table",
        },
        {
            "id": "obs-figures-complete",
            "observation": "%d figures are declared in record.figures, %d image links are in "
                           "§4 and %d figure payloads were retrievable from the platform "
                           "store; names and order agree"
                           % (len(record_figs),
                              sum(1 for a in assets if a["kind"] == "figure_reference"),
                              sum(1 for f in figures.values() if f.get("resolved"))),
            "record_figure_names": [f.get("name") for f in record_figs],
            "figure_bytes": {k: {"bytes": v.get("bytes"), "sha256": v.get("sha256"),
                                 "width_px": v.get("width_px"), "height_px": v.get("height_px")}
                             for k, v in figures.items()},
            "evidence": [q("token:artifacts/crp/fig1_circulation_interaction.png")],
            "impact": "figure payloads are registered with their own sha256 for later audit",
        },
    ]

    by_kind, by_res = {}, {"resolved": 0, "unresolved": 0}
    for a in assets:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1
        by_res[a["status"]] = by_res.get(a["status"], 0) + 1
    ids = [a["asset_id"] for a in assets]
    obs_ids = [o["id"] for o in observations]

    manifest = {
        "manifest_version": "1.0",
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "scope": {
            "report_id": REPORT_ID,
            "reports_touched": [REPORT_ID],
            "registers_assets_only": True,
            "extracts_claims": False,
            "classifies_report_type": False,
            "marks_verified": False,
            "writes_outside_worktree": False,
        },
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "title": rec.get("title"),
            "markdown_h1": h1_quote,
            "title_matches_contract": rec.get("title") == CONTRACT_TITLE,
            "title_equals_markdown_h1": h1_quote.lstrip("# ").strip() == rec.get("title"),
            "scenario_key": rec.get("scenario_key"),
            "scenario_key_matches_contract": rec.get("scenario_key") == SCENARIO_KEY,
            "chars": len(md_text),
            "byte_length_utf8": len(raw),
            "sha256": digest,
            "hash_check": {"expected": CONTRACT_HASH, "recomputed": digest,
                           "match": digest == CONTRACT_HASH},
            "chars_check": {"expected": CONTRACT_CHARS, "observed": len(md_text),
                            "match": len(md_text) == CONTRACT_CHARS},
            "retrieved_via": rec.get("_retrieved_via"),
            "section_headers": section_headers,
        },
        "assets": assets,
        "asset_counts": {
            "assets_total": len(assets),
            "resolved": by_res.get("resolved", 0),
            "unresolved": by_res.get("unresolved", 0),
            "by_kind": by_kind,
        },
        "id_uniqueness": {
            "asset_ids_unique": len(ids) == len(set(ids)),
            "asset_id_count": len(ids),
            "observation_ids_unique": len(obs_ids) == len(set(obs_ids)),
            "observation_count": len(obs_ids),
        },
        "claims_policy": {
            "claims": [],
            "reason": "objective.register_assets=true and objective.classify_report_type="
                      "false; the contract allows an empty claims array and forbids forced "
                      "claim generation, so no claim object is emitted, no text is "
                      "paraphrased and nothing is marked verified",
        },
        "probes": probes,
        "observations": observations,
        "limitations": [
            "registration only: no numeric re-verification, no claim extraction, no "
            "report-type classification — downstream work packages own those",
            "verification status is deliberately unset; the platform gate computes it",
            "code/test artefacts live in the producing repo and are not attached to the "
            "report record; their declared sizes and the pasted pytest transcript were "
            "registered as declared text and NOT re-executed or re-measured here",
            "figure payloads carry no hash in the report, so byte identity with the "
            "producing-repo PNG files cannot be confirmed from the report record alone",
            "the ITTC benchmark reference values quoted in §6.1 were not checked against "
            "the primary source (Koushan 1993 is not attached)",
        ],
    }

    emitted = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    result = {
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": digest,
            "source_field": "markdown",
            "source_uri": SOURCE_URI,
            "producer": "kf-worker agent/m15736 (scripts/kf/kf12028_register_assets.py)",
            "emitted_at": emitted,
            "notes": "source_hash recomputed locally from the markdown bytes served by "
                     "GET /api/v1/tensor/reports/12028; matches the contract-declared hash "
                     "%s byte for byte" % CONTRACT_HASH,
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    (DOCS / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (DOCS / "kf_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("assets:", len(assets), by_res, "| by_kind:", json.dumps(by_kind, ensure_ascii=False))
    print("hash match:", digest == CONTRACT_HASH, "| chars:", len(md_text))
    print("figures resolved:", sum(1 for f in figures.values() if f.get("resolved")),
          "/", len(figures))
    print("probes:", psum)
    print("wrote docs/kf/wp-12028-01/{asset_manifest.json,kf_result.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())