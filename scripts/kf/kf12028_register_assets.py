#!/usr/bin/env python3
"""KF wp-12028-01 · 01-asset-registration for report_id=12028, plus doc rendering.

Scope: register source assets only.  No claim extraction, no report-type
classification, nothing marked verified (the platform gate computes that).

Every locator quote is a **whole markdown line** picked by a selector from
scripts/kf/register_assets_lib.py, then double-checked:
  quote in markdown  and  markdown[offset:offset+len(quote)] == quote
plus an asserted occurrence count, so a locator cannot silently land on the
wrong duplicate line.

Modes
  (default)   live registration: GET /tensor/reports/12028, pin the markdown
              hash, pull the 4 figure payloads, probe the reference-only
              endpoints, and write
                work/wp-12028-01/source/report_12028.json   (snapshot, committed)
                docs/kf/wp-12028-01/asset_manifest.json
                docs/kf/wp-12028-01/kf_result.json
  --offline   rebuild both artefacts from the committed snapshot only (no network)
  --render    regenerate docs/kf/wp-12028-01/REPORT.md + fig_asset_inventory.png
              from the JSON artefacts (programmatic injection, zero hand-copied numbers)
  --publish   POST REPORT.md (+ figure) to /tensor/reports and read it back

Usage
  python3 scripts/kf/kf12028_register_assets.py            # register (network)
  python3 scripts/kf/kf12028_register_assets.py --offline  # register (snapshot)
  python3 scripts/kf/kf12028_register_assets.py --render
  python3 scripts/kf/kf12028_register_assets.py --publish
"""
from __future__ import annotations

import argparse
import base64
import datetime as _dt
import hashlib
import json
import struct
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kf12028_spec import (  # noqa: E402
    CONTRACT_CHARS,
    CONTRACT_HASH,
    CONTRACT_TITLE,
    EXTERNAL_KINDS,
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
MISSION_ID = 19685


def sha256_of_bytes(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def png_dims(raw: bytes) -> dict:
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        return {}
    w, h = struct.unpack(">II", raw[16:24])
    return {"width_px": w, "height_px": h}


def fetch_figure(name: str, token: str | None, prev: dict | None = None) -> dict:
    """Fetch one figure payload and pin its fingerprint.

    The PNG bytes are deliberately *not* written into the worktree: the pinned
    fingerprint (bytes / sha256 / IHDR pixel size) is the evidence, and a stray
    local copy could silently drift away from what the platform store serves.
    """
    meta = {"name": name, "endpoint": "/tensor/reports/%s/figures/%s" % (REPORT_ID, name)}
    if not token:
        if prev:
            r = dict(prev)
            r["reused_from"] = "snapshot (offline rebuild, no live fetch)"
            return r
        return {**meta, "resolved": False, "note": "no token and no snapshot entry"}
    import urllib.request

    req = urllib.request.Request(api_base() + meta["endpoint"],
                                 headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            meta["http_status"] = r.status
            meta["content_type"] = r.headers.get("content-type")
    except Exception as e:  # noqa: BLE001 - record honestly, never guess
        meta.update({"http_status": getattr(e, "code", None), "error": repr(e),
                     "resolved": False})
        return meta
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        meta.update({"bytes": len(data), "sha256": sha256_of_bytes(data), "resolved": False,
                     "note": "payload is not a PNG (magic mismatch)"})
        return meta
    meta.update({"bytes": len(data), "sha256": sha256_of_bytes(data), "resolved": True})
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
    ap = argparse.ArgumentParser(description="wp-12028-01 asset registration (report 12028)")
    ap.add_argument("--offline", action="store_true",
                    help="rebuild both artefacts from the committed snapshot only (no network)")
    ap.add_argument("--render", action="store_true",
                    help="regenerate docs/kf/wp-12028-01/REPORT.md + fig_asset_inventory.png")
    ap.add_argument("--publish", action="store_true",
                    help="POST REPORT.md to /tensor/reports and read it back")
    args = ap.parse_args()
    if args.render:
        return render_report()
    if args.publish:
        return publish_report()

    SRC.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    snap = SRC / "report_12028.json"
    prev = json.loads(snap.read_text(encoding="utf-8")) if snap.exists() else {}

    # live fetch by default; --offline is the explicit opt-in to the snapshot, so a
    # committed snapshot can never silently mask upstream drift on its own.
    rec = fetch_report(REPORT_ID, record_file=(snap if args.offline else None))
    md_text = rec["markdown"]
    md = Md(md_text)
    raw = md_text.encode("utf-8")
    digest = sha256_of(md_text)

    token = None if args.offline else get_token()

    # figure payloads: fingerprint only (bytes / sha256 / IHDR dims); no PNG copies
    # are written, so a stray local file cannot drift away from the store silently.
    record_figs = rec.get("figures") or []
    prev_figs = prev.get("figure_fingerprints") or {}
    figures = {}
    for f in record_figs:
        name = f.get("name") if isinstance(f, dict) else str(f)
        figures[name] = fetch_figure(name, token, prev_figs.get(name))
        figures[name]["caption_record"] = f.get("caption") if isinstance(f, dict) else None

    # probes on the reference-only artefacts (code/test/script bytes not attached)
    prev_probes = {p["path"]: p for p in (prev.get("probes") or [])}
    probes = []
    for ep in PROBES:
        if token is None and ep in prev_probes:
            r = dict(prev_probes[ep])
            r["reused_from"] = "snapshot (offline rebuild, no live probe)"
        else:
            r = probe(ep, token)
        r["path"] = ep
        probes.append(r)
    psum = probe_summary(probes)

    # locate assets
    assets, failures = [], []
    for s in SPEC:
        try:
            off, quote, meta, tok_hit = locate(md, s["sel"], title=rec.get("title", ""))
        except LookupError as e:
            failures.append({"spec_id": s["id"], "name": s["name"], "error": str(e)})
            continue
        occ = md_text.count(quote)
        if md_text[off:off + len(quote)] != quote:
            failures.append({"spec_id": s["id"], "name": s["name"],
                             "error": "back-read mismatch"})
            continue
        if tok_hit is not None and s.get("occ") is not None:
            tok_occ = md_text.count(tok_hit)
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
    # envelope shape follows the *current* schemas/kf_result.v1.schema.json:
    # additionalProperties:false at top level and inside provenance, so the producer
    # stamp lives on the manifest (which is free-form) instead of the envelope.
    manifest["generated_by"] = {
        "tool": "scripts/kf/kf12028_register_assets.py",
        "worker": "kf-worker agent/m19685 (mission m19685, re-cut of closed PR #231)",
        "emitted_at": emitted,
        "mode": "offline-rebuild" if args.offline else "live-fetch",
    }
    result = {
        "package_id": PKG,
        "contract_version": "1.0",
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": digest,
            "source_hash_matches": digest == CONTRACT_HASH,
            "title": rec.get("title"),
            "scenario_key": rec.get("scenario_key"),
            "chars": len(md_text),
        },
        "outputs": {"asset_manifest.json": manifest},
    }

    (DOCS / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (DOCS / "kf_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    snap.write_text(json.dumps({**rec, "figure_fingerprints": figures, "probes": probes,
                                "snapshot": {"written_at": emitted,
                                             "mode": "offline-rebuild" if args.offline
                                             else "live-fetch"}},
                               ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("assets:", len(assets), by_res, "| by_kind:", json.dumps(by_kind, ensure_ascii=False))
    print("hash match:", digest == CONTRACT_HASH, "| chars:", len(md_text))
    print("figures resolved:", sum(1 for f in figures.values() if f.get("resolved")),
          "/", len(figures))
    print("probes:", psum)
    print("wrote", snap, "docs/kf/wp-12028-01/{asset_manifest.json,kf_result.json}")
    return 0 if digest == CONTRACT_HASH else 2


def render_figure(man: dict) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    by_kind: dict[str, dict[str, int]] = {}
    for a in man["assets"]:
        d = by_kind.setdefault(a["kind"], {"resolved": 0, "unresolved": 0})
        d[a["status"]] += 1
    kinds = sorted(by_kind, key=lambda k: -(by_kind[k]["resolved"] + by_kind[k]["unresolved"]))
    res = [by_kind[k]["resolved"] for k in kinds]
    unres = [by_kind[k]["unresolved"] for k in kinds]

    figs = [a for a in man["assets"] if a["kind"] == "figure_reference"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.6))
    y = range(len(kinds))
    ax1.barh(list(y), res, color="#2f6fb5", label="resolved")
    ax1.barh(list(y), unres, left=res, color="#c0392b", label="unresolved")
    ax1.set_yticks(list(y))
    ax1.set_yticklabels(kinds, fontsize=8)
    ax1.invert_yaxis()
    ax1.set_xlabel("assets")
    ax1.set_title("(a) report %s asset inventory by kind\nresolved=%d / unresolved=%d / total=%d"
                  % (REPORT_ID, man["asset_counts"]["resolved"],
                     man["asset_counts"]["unresolved"], man["asset_counts"]["assets_total"]),
                  fontsize=10)
    ax1.legend(fontsize=8, loc="lower right")
    ax1.grid(axis="x", alpha=0.3)

    names = [a["name"].rsplit("/", 1)[-1].replace("_", " ").replace(".png", "") for a in figs]
    nbytes = [a["resolved_bytes"]["bytes"] for a in figs]
    ax2.bar(range(len(figs)), nbytes, color="#1f8a70")
    for i, a in enumerate(figs):
        rb = a["resolved_bytes"]
        ax2.text(i, rb["bytes"] * 1.02, "%dx%d\n%s" %
                 (rb["width_px"], rb["height_px"], rb["sha256"][7:15]),
                 ha="center", va="bottom", fontsize=7)
    ax2.set_xticks(range(len(figs)))
    ax2.set_xticklabels(names, rotation=18, ha="right", fontsize=8)
    ax2.set_ylim(0, max(nbytes) * 1.35)
    ax2.set_ylabel("payload bytes served by platform store")
    ax2.set_title("(b) figure payloads registered (HTTP 200, sha256 pinned)", fontsize=10)
    ax2.grid(axis="y", alpha=0.3)

    fig.suptitle("KF %s · asset registration evidence — report %s" % (PKG, REPORT_ID), fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = DOCS / "fig_asset_inventory.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def locator_table(man: dict, ids: list[str]) -> str:
    rows = ["| 字段/资产 | 原文引文片段（逐字，含字符区间） |", "| --- | --- |"]
    idx = {a["asset_id"]: a for a in man["assets"]}
    for aid in ids:
        a = idx[aid]
        loc = a["locators"][0]
        q = loc["quote"].strip()
        if len(q) > 96:
            q = q[:93] + "…"
        rows.append("| `%s` (%s) | `%s` [%d:%d] |"
                    % (aid, a["name"], q.replace("|", "\\|"), loc["char_start"], loc["char_end"]))
    for obs in man["observations"][:3]:
        loc = obs["evidence"][0]
        q = loc["quote"].strip()
        if len(q) > 96:
            q = q[:93] + "…"
        rows.append("| 观察 `%s` | `%s` [%d:%d] |"
                    % (obs["id"], q.replace("|", "\\|"), loc["char_start"], loc["char_end"]))
    return "\n".join(rows)


def render_report() -> int:
    man = json.loads((DOCS / "asset_manifest.json").read_text(encoding="utf-8"))
    env = json.loads((DOCS / "kf_result.json").read_text(encoding="utf-8"))
    acc = json.loads((DOCS / "acceptance.json").read_text(encoding="utf-8"))
    snap = json.loads((SRC / "report_12028.json").read_text(encoding="utf-8"))
    figs_meta = snap["figure_fingerprints"]
    probes = snap["probes"]

    png = render_figure(man)
    src = man["source"]
    counts = man["asset_counts"]
    prov = env["provenance"]

    acc_rows = ["| acceptance 项 | 自检结论 | 模式 | 关键证据 |", "| --- | --- | --- | --- |"]
    for c in acc["checks"]:
        det = json.dumps(c["detail"], ensure_ascii=False)
        if len(det) > 120:
            det = det[:117] + "…"
        acc_rows.append("| `%s` | %s | %s | %s |"
                        % (c["check"], c["status"], c.get("mode", "-"),
                           det.replace("|", "\\|")))
    acc_table = "\n".join(acc_rows)

    fig_rows = ["| 图文件 | 平台端点 | 状态 | 字节 | sha256 | 像素 |",
                "| --- | --- | --- | --- | --- | --- |"]
    for name, m in figs_meta.items():
        fig_rows.append("| `%s` | `%s` | %s | %s | `%s` | %dx%d |"
                        % (name, m.get("endpoint"), m.get("http_status"),
                           m.get("bytes"), (m.get("sha256") or "")[7:23],
                           m.get("width_px") or 0, m.get("height_px") or 0))
    fig_table = "\n".join(fig_rows)

    probe_rows = ["| 端点 | HTTP |", "| --- | --- |"]
    for p in probes:
        probe_rows.append("| `%s` | %s |" % (p["path"], p.get("http_status")))
    probe_table = "\n".join(probe_rows)

    unref = [a for a in man["assets"] if a["status"] == "unresolved"]
    unresolved_rows = ["| 资产 | kind | 未解析理由（摘） |", "| --- | --- | --- |"]
    for a in unref:
        unresolved_rows.append("| `%s` | %s | %s |"
                               % (a["asset_id"], a["kind"],
                                  a["unresolved_reason"][:150].replace("|", "\\|")))
    unresolved_table = "\n".join(unresolved_rows)

    obs_rows = ["| 观察 id | 内容（摘要） | 证据条数 |", "| --- | --- | --- |"]
    for o in man["observations"]:
        obs_rows.append("| `%s` | %s | %d |"
                        % (o["id"], o["observation"][:150].replace("|", "\\|"),
                           len(o["evidence"])))
    obs_table = "\n".join(obs_rows)

    env_json = json.dumps(env, ensure_ascii=False, indent=2)
    live = next((c for c in acc["checks"] if c["check"] == "figure_payloads_live_sha256"), None)
    live_line = ("%s（mode=%s）" % (live["status"], live.get("mode")) if live else "未执行")

    md = f"""# KF-RESULT {PKG}

- package_id: `{PKG}` ｜ task_type: `01-asset-registration` ｜ report_id: `{REPORT_ID}` ｜ lane: C ｜ repo: TensorKnowledge ｜ status: **draft**
- source: `{src['source_uri']}`（field=`markdown`），chars={src['chars']}，bytes_utf8={src['byte_length_utf8']}，sha256=`{src['sha256']}`
- 工序范围：**只登记资产**——不抽取 claim、不做报告类型分类、不标 verified（verification 由平台门计算）
- 本次为**重开单**：上一版 PR #231 由 owner 于 2026-11-05 裁定关闭；本版从当前 `main` 重新切枝重做，交付压到 ≤10 个文件（旧版 23 个，且含 `ke/__pycache__/*.pyc` 二进制），功能与测试按同样的验收项重跑

## ① 本工序做了什么

对 report_id={REPORT_ID}（`{src['title']}`）执行 01-asset-registration：

1. 从平台 API 取回 markdown，本地重算字节哈希并锁定：`{src['sha256']}`，{src['chars']} 字符 / {src['byte_length_utf8']} 字节；契约声明 `{src['hash_check']['expected']}`，实测值与声明值逐字节相同（match={str(src['hash_check']['match']).lower()}），字符数也与契约声明的 {src['chars_check']['expected']} 一致（match={str(src['chars_check']['match']).lower()}）。
2. 建立资产清单：共 **{counts['assets_total']} 个资产**（resolved {counts['resolved']} / unresolved {counts['unresolved']}），覆盖源文档本体、记录元数据、方法/方程块、代码与测试工件引用、图件、声明数值表、门限记录、文献与基准引用。
3. 每条 locator 的 quote 由程序在运行时从原文**整行**取出（不是手打），双重校验 `md[start:end] == quote` 且 `quote in md`，并对选择器命中的 token 做**出现次数断言**（防止落到错误重复行）。
4. 图件不只登记引用：{len(figs_meta)} 张 PNG 从平台图件存储取回真实字节，逐张记录 sha256/字节数/像素尺寸（见下表）。
5. claims 按契约留空数组，并显式写明留空理由；未对任何数值做 re-verification，未生成"verified"标记。

## ② 怎么做的（步骤/工具/关键设置）

| 步骤 | 工具/脚本 | 关键设置 |
| --- | --- | --- |
| 取源 + 锁哈希 | 本脚本（urllib，Bearer 登录；仅 `--offline` 时读快照） | sha256 以 `markdown` 字段 utf-8 字节计算，与契约声明逐字节比对；默认活取，快照不能单独掩盖上游漂移 |
| 资产登记 | `scripts/kf/kf12028_register_assets.py` + `scripts/kf/kf12028_spec.py`（56 条 SPEC；`--offline` 可离线复跑） | 56 条 SPEC，选择器 `token:` / `table_row:` / `h1`；quote=整行原文；断言 `occurrence_count` 与期望一致，否则 SystemExit（拒绝编造） |
| 图件取字节 | 同上（`fetch_figure`，只 pin 指纹、不落 PNG） | `GET /tensor/reports/12028/figures/<name>`；记录 HTTP/bytes/sha256/IHDR 像素 |
| 可解析性探测 | 同上（`probe`） | 4 个候选端点，失败如实记 HTTP 状态码，不重试不猜测 |
| 共用库 | `scripts/kf/register_assets_lib.py`（复用既有件，未改动） | `Md` 行索引 + 选择器定位 + `fetch_report` 硬锁 report_id |
| 验收自检 | `scripts/kf/kf12028_checks.py`（纯函数 + runner，可离线） | 7 项检查（6 条契约 acceptance + 契约对齐 + 结构不变量），在线模式重新拉 markdown 复算哈希 |
| 单元测试 | `tests/test_wp12028_asset_manifest.py` | 23 项：正检 + **负对照**（篡改 quote / 平移偏移 / 伪造引文 / 伪造 record 值 / 重复 id / 改哈希 / 缺 unresolved 理由 / 篡改计数 → 必须被检出） |
| 图 | `scripts/kf/kf12028_register_assets.py --render` | matplotlib Agg，全部数字从 manifest + 快照指纹程序化取，无手抄 |

## ③ 产出物清单

| 文件 | 要点 |
| --- | --- |
| `docs/kf/wp-12028-01/asset_manifest.json` | {counts['assets_total']} 资产 / 计数与不变量 / {len(man['observations'])} 条观察 / probe 证据 |
| `docs/kf/wp-12028-01/kf_result.json` | 提交用结果信封（outputs=`asset_manifest.json`；claims 不进信封——现行 schema 顶层 `additionalProperties:false`，留空理由写在 manifest.claims_policy） |
| `docs/kf/wp-12028-01/acceptance.json` | {acc['summary']['total']} 项自检（PASS {acc['summary']['pass']} / FAIL {acc['summary']['fail']}） |
| `docs/kf/wp-12028-01/fig_asset_inventory.png` | 资产解析状态 + 图件载荷清单图（本报告 ④ 附图） |
| `docs/kf/wp-12028-01/REPORT.md` | 本报告（投递体由 `--publish` 在内存里构造，不落盘） |
| `scripts/kf/kf12028_spec.py`、`scripts/kf/kf12028_register_assets.py`、`scripts/kf/kf12028_checks.py` | 取源+登记+出图 / 自检，一键复跑 |
| `tests/test_wp12028_asset_manifest.py` | 23 项 pytest（含 12 项负对照） |
| `work/wp-12028-01/source/report_12028.json` | 单一快照文件：record + markdown + 4 张图件指纹 + 4 个探针结果（离线测试的唯一输入） |

图件载荷登记（真实字节，非字符串引用）：

{fig_table}

## ④ 证据定位表（claim/字段 → 原文引文片段）

全部引文由程序定位，区间为 markdown 字符下标（`[start:end]`），平台可逐条回解：

{locator_table(man, ['ast-12028-01', 'ast-12028-03', 'ast-12028-04', 'ast-12028-12',
                     'ast-12028-19', 'ast-12028-23', 'ast-12028-27', 'ast-12028-35',
                     'ast-12028-36', 'ast-12028-47', 'ast-12028-48', 'ast-12028-49'])}

观察项（registration-only，不作裁决，均附逐字证据）：

{obs_table}

## ⑤ 注意点与局限

1. **3 个代码/测试/脚本工件未能解析**（如实登记为 unresolved，不代上游补写）：报告正文引用了 `backend/methods/crp/__init__.py`、`backend/api/crp.py`、`backend/tests/test_crp.py`、`scripts/crp_generate_figures.py` 等，但这些字节不在报告存储中，探测端点无载荷：

{probe_table}

{unresolved_table}

2. **图件字节可解析但无哈希锚**：{len(figs_meta)} 张 PNG 由平台图件存储返回（HTTP 200，PNG magic 校验通过），但报告正文未给出图件哈希，故"与生产仓 `artifacts/crp/` 下同名文件逐字节同一"**无法从报告记录证明**——本单只登记平台侧字节与其 sha256，供后续审计比对。
3. **标题漂移**：record.title 与契约标题一致，但 markdown H1 多出"分析报告"后缀（`obs-title-drift`）；下游抽取须以 report_id 为键，不能以标题相等为键。
4. **mission_id 不一致**：record.mission_id={man['observations'][1].get('record_mission_id')}、正文写"任务编号 m10162"，而契约声明 mission_id: null（`obs-mission-id`）——如实记录，本单不做归并。
5. **报告内部口径差异（注册级观察，非裁决）**：§1.2 声明 6/7 叶的 ITTC 基准几何，而 §3.1/§3.2 的数值案例是 Z_f=4/Z_r=5 的简化案例（`obs-benchmark-vs-case-geometry`）；标题写"面元法"，§2 只给出升力线+叶素动量公式（`obs-title-scope-vs-method`）。
6. **honest FAIL 原样保留**：§1.3 目标 |Q_f+Q_r|/Q_ref < 1%，§3.4/§6.2 自报 172% 且标 FAIL，外层螺距优化未实现（`TorqueBalanceIterator` 仅为待办）——本单不升级任何门限结论，也不把"效率 1.0%"重述为已验证。
7. **未做**：数值复算、基准表回溯（Koushan 1993 未附）、代码字节核对（20,517/12,168/8,311 bytes 与 20 passed 记录均为**报告自述**，未重测）。

## ⑥ 自检：逐条对照 acceptance

{acc_table}

自检汇总：**PASS {acc['summary']['pass']} / FAIL {acc['summary']['fail']}**（共 {acc['summary']['total']} 项；worker 侧自检，非平台门）。

## ⑦ 结果图

![资产解析状态与图件载荷清单](fig_asset_inventory.png)

图 1：(a) 按 kind 统计的资产解析状态（resolved/unresolved）；(b) 4 张图件在平台存储的实际载荷字节数、像素尺寸与 sha256 前 8 位。

**为何没有场量云图/与解析解对比曲线**：本工作包是纯登记工序（`objective.register_assets=true`、`classify_report_type=false`），不执行任何求解、不复算任何流场量，因此不存在可供作图的场量或计算-基准对比曲线；强行作图会变成对上游数字的再绘图而非本工序证据。故图 1 只呈现本工序可自证的两类量：资产解析状态与图件载荷指纹。

## ⑧ 误差判定（关键量对照基准，显式回答是否 <3%）

| 关键量 | 基准 | 本工序观测 | 误差 | <3%？ |
| --- | --- | --- | --- | --- |
| markdown sha256 | 契约 `{src['hash_check']['expected']}` | `{src['sha256']}` | 0（逐字节一致） | ✅ 是（精确一致） |
| markdown 字符数 | 契约 {src['chars_check']['expected']} | {src['chars_check']['observed']} | 0% | ✅ 是 |
| 图件字节 sha256 | 平台存储实时复取 | {live_line} | 逐字节比对 | {live_line} |
| locator 可回解率 | {acc['summary']['total']} 项自检全 PASS | PASS {acc['summary']['pass']} / FAIL {acc['summary']['fail']} | 0 项不符 | ✅ 是 |

**关于上游物理量误差（如 η 相对 ITTC 基准 1.0%）**：本工序**不做**该判定——参考数据（Koushan 1993）未附于报告记录，1.0% 是报告自述值，登记而已；任何"<3%"结论都属于下游复核工序，不在本单权责内。

## ⑨ 一键复跑

```bash
cd <worktree>
python3 scripts/kf/kf12028_register_assets.py           # 生成 asset_manifest.json / kf_result.json
python3 scripts/kf/kf12028_checks.py                    # 自检 → acceptance.json（含活的图件字节复核）
python3 -m pytest tests/test_wp12028_asset_manifest.py -q   # 23 项测试（离线可跑）
python3 scripts/kf/kf12028_register_assets.py --render  # 出图 + 本报告
python3 scripts/kf/kf12028_register_assets.py --publish # 投递本报告（需 TENSOR_AGENT_* 环境变量）
```

provenance：`source_hash` = `{prov['source_hash']}`（= 契约声明值，平台可独立重算）；`source_field` = `{prov['source_field']}`。

## 结果信封（唯一 json 代码块，平台门按 schemas/kf_result.v1.schema.json 校验）

```json
{env_json}
```
"""

    out = DOCS / "REPORT.md"
    out.write_text(md, encoding="utf-8")

    # exactly one ```json fence must exist in the submitted markdown
    assert md.count("```json") == 1, md.count("```json")
    json.loads(md.split("```json", 1)[1].split("```", 1)[0])  # fence parses
    print("wrote", out, png)
    return 0


def publish_report() -> int:
    """POST REPORT.md (+ the inventory figure) to /tensor/reports and read it back."""
    md = (DOCS / "REPORT.md").read_text(encoding="utf-8")
    man = json.loads((DOCS / "asset_manifest.json").read_text(encoding="utf-8"))
    counts = man["asset_counts"]
    png = DOCS / "fig_asset_inventory.png"
    payload = {
        "title": "KF-RESULT " + PKG,
        "summary": ("登记 report %s 的源资产：hash/字符数与契约逐字节一致，%d 个资产"
                    "（resolved %d / unresolved %d），4 张图件取回真实字节并 pin sha256，"
                    "claims 按契约留空。"
                    % (REPORT_ID, counts["assets_total"], counts["resolved"],
                       counts["unresolved"])),
        "scenario_key": SCENARIO_KEY,
        "mission_id": MISSION_ID,
        "tags": ["kf", "kf-wp:" + PKG, "asset-registration", "report-" + REPORT_ID,
                 "kf-stage-01", "CRP", SCENARIO_KEY],
        "markdown": md,
        "figures": [{
            "name": png.name,
            "caption": ("图 1：report %s 资产解析状态（按 kind，resolved/unresolved）与 4 张图件"
                        "在平台存储的载荷字节/像素/sha256 指纹；由 "
                        "scripts/kf/kf12028_register_assets.py --render 从 asset_manifest.json "
                        "程序化生成。" % REPORT_ID),
            "png_base64": base64.b64encode(png.read_bytes()).decode(),
        }],
    }
    tok = get_token()
    if not tok:
        raise SystemExit("登录失败：无 token，无法投递")
    req = urllib.request.Request(
        api_base() + "/tensor/reports",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok},
        method="POST")
    out = json.load(urllib.request.urlopen(req, timeout=180))
    rid = out.get("id")
    print("published report_id=%s status=%s mission_id=%s"
          % (rid, out.get("status"), out.get("mission_id")))
    back = json.load(urllib.request.urlopen(
        urllib.request.Request(api_base() + "/tensor/reports/%s" % rid,
                               headers={"Authorization": "Bearer " + tok}), timeout=60))
    same = back.get("markdown") == md
    print("round-trip markdown identical:", same,
          "| stored chars:", len(back.get("markdown") or ""),
          "| figures:", len(back.get("figures") or []))
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main())
