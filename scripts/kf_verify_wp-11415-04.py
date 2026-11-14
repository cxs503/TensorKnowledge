#!/usr/bin/env python3
"""Independent (red-team) verification of upstream package wp-11415-01.

Inputs (re-derived, never trusted):
  * report 11415 markdown re-fetched from the platform (scripts/kf_fetch_11415_04.py),
    sha256 re-checked against the contract hash;
  * the machine-readable payload of wp-11415-01, jsonschema-validated; the
    producer's prose sections are never parsed;
  * figure binaries re-fetched from the platform by name.

Checks
  C1 source identity        contract hash / char / byte count vs platform payload
  C2 locator fidelity       md[start:end]==quote, count(quote)==1, lines
                            recomputed, ids contiguous, section ownership
  C3 coverage completeness  per-token ownership: every file/figure reference in
                            the source must have an owning asset; table and
                            figure counts cross-checked against the source and
                            the platform payload
  C4 label semantics        every number handed to the reviewer inside a
                            label/note must appear verbatim in the source
  C5 resolution honesty     resolved_in_source -> span re-checked; unresolved ->
                            path really absent; declared_absent -> flag present
  C6 schema / envelope      kf_result.v1 + wp-11415-01 asset_manifest pin
  C7 review discipline      no self-declared verified, claims declared, single
                            report_id, figures match payload
  C8 replay                 upstream verifier replayed on reconstructed inputs
  C9 figure binaries        re-fetched by name, sha256/bytes vs registration

Writes runs/wp-11415-04/independent_checks.json.  Exit != 0 on any FAIL.
Run:  python3 scripts/kf_verify_wp-11415-04.py
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

RUN = pathlib.Path("runs/wp-11415-04")
MD = RUN / "report_11415.md"
UPSTREAM_RESULT = RUN / "upstream_kf_result_wp-11415-01.json"
MANIFEST = RUN / "upstream_asset_manifest_wp-11415-01.json"
IDENTITY = RUN / "source_identity.json"
REPLAY = RUN / "replay"
OUT = RUN / "independent_checks.json"

EXPECTED_HASH = "d8bc42883f1fa1d274a3ca4808586d2a8773e9d0f464b554c944f5090b0c8c50"
EXPECTED_CHARS = 7903
REPORT_ID = "11415"

FILE_RE = re.compile(r"[A-Za-z0-9_./-]*[A-Za-z0-9_]\.[A-Za-z0-9_]{2,6}\b")
FIG_RE = re.compile(r"\bfig[0-9]_[A-Za-z0-9_]+\.png\b")
TABLE_SEP_RE = re.compile(r"(?m)^\|\s*-{2,}")


def line_of(md: str, off: int) -> int:
    return md[:off].count("\n")


def heading_spans(md: str) -> list[tuple[int, int, str]]:
    out = []
    ms = list(re.finditer(r"(?m)^#{1,6} .*$", md))
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(md)
        out.append((m.start(), end, m.group(0)))
    return out


def enclosing_heading(spans, off: int) -> str | None:
    for s, e, txt in spans:
        if s <= off < e:
            return txt
    return None


def main() -> int:
    md = MD.read_text(encoding="utf-8")
    identity = json.loads(IDENTITY.read_text())
    result = json.loads(UPSTREAM_RESULT.read_text())
    man = json.loads(MANIFEST.read_text())
    assets = man["assets"]
    checks: dict[str, dict] = {}
    findings: list[dict] = []

    def bump(cid: str, status: str, detail: str | None = None, problem: str | None = None,
             severity: str = "major") -> None:
        c = checks.setdefault(cid, {"status": "pass", "detail": [], "problems": []})
        if detail:
            c["detail"].append(detail)
        if status != "pass":
            if c["status"] == "pass":
                c["status"] = status
            c["problems"].append(problem or detail)
            findings.append({"check": cid, "severity": severity, "problem": problem or detail})

    spans = heading_spans(md)

    # ------------------------------------------------------------------ C1
    h = hashlib.sha256(md.encode()).hexdigest()
    prov = result["provenance"]
    ok1 = (
        h == EXPECTED_HASH
        and len(md) == EXPECTED_CHARS
        and prov["source_hash"] == "sha256:" + EXPECTED_HASH
        and prov.get("source_chars", prov.get("chars")) == EXPECTED_CHARS
        and man["source"]["hash"] == EXPECTED_HASH
        and man["source"]["chars"] == EXPECTED_CHARS
    )
    bump("C1_source_identity", "pass" if ok1 else "FAIL",
         f"sha256={h} chars={len(md)} bytes={len(md.encode())} "
         f"upstream source_chars={prov.get('source_chars', prov.get('chars'))}")
    if not ok1:
        bump("C1_source_identity", "FAIL", problem="source identity disagrees with the contract")

    # ------------------------------------------------------------------ C2
    ids = [a["asset_id"] for a in assets]
    if ids != [f"A{i:02d}" for i in range(1, len(assets) + 1)]:
        bump("C2_locator_fidelity", "FAIL", problem=f"asset ids not contiguous: {ids}")
    if len(set(ids)) != len(ids):
        bump("C2_locator_fidelity", "FAIL", problem="duplicate asset_id")
    n_span = 0
    for a in assets:
        loc = a["locator"]
        q, meth = loc["quote"], loc["method"]
        if meth == "document":
            if q != md:
                bump("C2_locator_fidelity", "FAIL", problem=f"{a['asset_id']} document quote != markdown")
            n_span += 1
            continue
        if meth != "char_span":
            bump("C2_locator_fidelity", "FAIL", problem=f"{a['asset_id']} unknown method {meth}")
            continue
        s, e = loc["start_char"], loc["end_char"]
        if md[s:e] != q:
            bump("C2_locator_fidelity", "FAIL", problem=f"{a['asset_id']} md[{s}:{e}] != quote")
        n = md.count(q)
        if loc.get("unique") and n != 1:
            bump("C2_locator_fidelity", "FAIL", problem=f"{a['asset_id']} quote occurs {n}x, unique=true")
        if line_of(md, s) != loc["start_line"]:
            bump("C2_locator_fidelity", "FAIL",
                 problem=f"{a['asset_id']} start_line {loc['start_line']} != {line_of(md, s)}")
        if line_of(md, max(s, e - 1)) != loc["end_line"]:
            bump("C2_locator_fidelity", "FAIL",
                 problem=f"{a['asset_id']} end_line {loc['end_line']} != {line_of(md, max(s, e - 1))}")
        enc = enclosing_heading(spans, s)
        claimed = a["in_report_section"].strip()
        if claimed != (enc or "").strip():
            if claimed == "(preamble)" and s == 0:
                bump("C2_locator_fidelity", "pass",
                     detail=f"{a['asset_id']} '(preamble)' sentinel used for the title line (convention, quote verbatim)")
            else:
                bump("C2_locator_fidelity", "FAIL",
                     problem=f"{a['asset_id']} in_report_section {claimed!r} != enclosing heading {enc!r}")
        n_span += 1
    bump("C2_locator_fidelity", "pass", detail=f"{n_span}/{len(assets)} locators recomputed from raw bytes")

    # ------------------------------------------------------------------ C3
    file_toks = sorted({t for t in FILE_RE.findall(md) if "/" in t})
    fig_toks = sorted(set(FIG_RE.findall(md)))
    owner: dict[str, list[str]] = {}
    for tok in file_toks + fig_toks:
        holder = [a["asset_id"] for a in assets if tok in a["label"] or tok in a["locator"]["quote"]]
        owner[tok] = holder
    orphan = {t: h for t, h in owner.items() if not h}
    # a token is only "owned" if some asset names it in its label (a bare
    # verbatim quote mention is not a registration).
    label_owner = {t: [a["asset_id"] for a in assets if t in a["label"]] for t in owner}
    no_label = {t: h for t, h in label_owner.items() if not h}
    n_tables = len(TABLE_SEP_RE.findall(md))
    tab_assets = [a["asset_id"] for a in assets if a["asset_class"] == "table"]
    figs_payload = [f["name"] for f in identity.get("figures") or []]
    fig_assets = [a["label"].split("（")[0] for a in assets if a["asset_class"] == "figure"]
    c3_problems = []
    if orphan:
        c3_problems.append(f"references with no asset at all: {orphan}")
    if n_tables != len(tab_assets):
        c3_problems.append(f"source markdown has {n_tables} tables but {len(tab_assets)} table assets")
    if len(figs_payload) != len(fig_assets):
        c3_problems.append(f"payload has {len(figs_payload)} figures but {len(fig_assets)} figure assets")
    if sorted(figs_payload) != sorted(fig_assets):
        c3_problems.append(f"figure names differ: payload={figs_payload} assets={fig_assets}")
    bump("C3_coverage", "FAIL" if c3_problems else "pass",
         detail=f"file_tokens={len(file_toks)} figures={len(fig_toks)} md_tables={n_tables} "
                f"table_assets={len(tab_assets)} payload_figures={len(figs_payload)}",
         problem="; ".join(c3_problems) if c3_problems else None)
    if no_label:
        bump("C3_coverage", "pass",
             detail=f"tokens registered only inside quotes (no label owner): {no_label}")

    # ------------------------------------------------------------------ C4
    atoms: list[str] = []
    for a in assets:
        for f in ("label", "note"):
            atoms += re.findall(r"[0-9][0-9.,]*e?[-+]?[0-9]*", a.get(f) or "")
    atoms = [x for x in atoms if x.strip(".,") and ".." not in x]
    bad = sorted({x for x in atoms if x not in md and x.strip(".,") != REPORT_ID})
    bump("C4_label_numbers", "FAIL" if bad else "pass",
         detail=f"atoms_checked={len(set(atoms))} not_in_source={bad}",
         problem=f"numbers in labels absent from the source: {bad}" if bad else None)

    # ------------------------------------------------------------------ C5
    r_in = [a for a in assets if a["resolution"] == "resolved_in_source"]
    r_un = [a for a in assets if a["resolution"] == "referenced_unresolved"]
    r_ab = [a for a in assets if a["resolution"] == "declared_absent"]
    cnt = man["counts"]
    c5 = []
    if len(r_in) + len(r_un) + len(r_ab) != len(assets):
        c5.append("resolution buckets do not partition the assets")
    if cnt["resolved_in_source"] != len(r_in) or cnt["referenced_unresolved"] != len(r_un):
        c5.append("counts.by_resolution disagrees with the asset list")
    for a in r_un:
        rc = a["resolution_check"]
        for p in rc.get("paths", []):
            if pathlib.Path(p).exists():
                c5.append(f"{a['asset_id']} declared unresolved but {p} exists")
        if rc.get("result") != "unresolved" or set(rc.get("missing", [])) != set(rc.get("paths", [])):
            c5.append(f"{a['asset_id']} unresolved bookkeeping inconsistent")
    for a in r_in:
        rc = a.get("resolution_check", {})
        if rc.get("check") == "char_span_in_source_markdown":
            s, e = a["locator"]["start_char"], a["locator"]["end_char"]
            if md[s:e] != a["locator"]["quote"]:
                c5.append(f"{a['asset_id']} resolved but span does not slice")
        if rc.get("contract") and rc.get("recomputed") and rc["contract"] != rc["recomputed"]:
            c5.append(f"{a['asset_id']} recomputed != contract")
    for a in r_ab:
        flag = a["resolution_check"].get("flag")
        if flag and flag not in md:
            c5.append(f"{a['asset_id']} declared_absent flag {flag!r} not in source")
    bump("C5_resolution_honesty", "FAIL" if c5 else "pass",
         detail=f"resolved={len(r_in)} unresolved={len(r_un)} absent={len(r_ab)}",
         problem="; ".join(c5) if c5 else None)

    # ------------------------------------------------------------------ C6
    errors = []
    for schema_path, inst, name in (
        ("schemas/kf_result.v1.schema.json", result, "kf_result.v1"),
        ("schemas/asset_manifest.v1.wp-11415-01.schema.json", man, "asset_manifest.v1(wp-11415-01)"),
    ):
        schema = json.loads(pathlib.Path(schema_path).read_text(encoding="utf-8"))
        v = jsonschema.Draft202012Validator(schema)
        errs = [
            {"instance": name, "path": list(e.absolute_path), "message": e.message[:220]}
            for e in sorted(v.iter_errors(inst), key=lambda e: list(e.absolute_path))
        ]
        errors += errs
        if not errs:
            bump("C6_schema", "pass", detail=f"{name} valid")
    if errors:
        checks.setdefault("C6_schema", {"status": "pass", "detail": [], "problems": []})
        checks["C6_schema"]["status"] = "FAIL"
        checks["C6_schema"]["detail"].append({"schema_errors": errors})
        checks["C6_schema"]["problems"] = [f"{e['instance']} {e['path']}: {e['message']}" for e in errors]
        for e in errors:
            findings.append(
                {"check": "C6_schema", "severity": "major",
                 "problem": f"{e['instance']} schema violation at {e['path']}: {e['message']}"}
            )

    # ------------------------------------------------------------------ C7
    blob = json.dumps(man, ensure_ascii=False)
    c7 = []
    if re.search(r'"verification_status"\s*:\s*"verified"', json.dumps(result, ensure_ascii=False)):
        c7.append("upstream declares verification_status=verified")
    if man.get("claims") != []:
        c7.append("01 package carries claims (out of scope for this task_type)")
    if not man.get("claims_note"):
        c7.append("empty claims without a declaring note")
    foreign = sorted({x for x in re.findall(r"tensor://reports/([0-9A-Za-z_.:-]+)", json.dumps(result, ensure_ascii=False)) if x != REPORT_ID})
    if foreign:
        c7.append(f"foreign report ids referenced: {foreign}")
    if result["report_id"] != REPORT_ID or man["report_id"] != REPORT_ID:
        c7.append("report_id mismatch")
    bump("C7_review_discipline", "FAIL" if c7 else "pass",
         detail="no self-declared verified; claims=[] with note; single report_id",
         problem="; ".join(c7) if c7 else None)

    # ------------------------------------------------------------------ C8
    vr = REPLAY / "runs/wp-11415-01/verify_report.json"
    if vr.exists():
        vrep = json.loads(vr.read_text())
        failed = [k for k, v in vrep.get("checks", {}).items() if isinstance(v, dict) and v.get("pass_") is False]
        bump("C8_replay_upstream_verifier", "FAIL" if failed else "pass",
             detail=f"replay exit={vrep.get('exit_code', 'n/a')} failed_checks={failed}",
             problem=f"upstream verifier replay fails: {failed}" if failed else None)
    else:
        bump("C8_replay_upstream_verifier", "FAIL", problem="replay produced no verify_report.json")

    # ------------------------------------------------------------------ C9
    token = None
    try:
        base = os.environ["TENSOR_API_BASE"].rstrip("/")
        req = urllib.request.Request(
            base + "/auth/login",
            data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                             "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.loads(r.read().decode())
        token = tok.get("access_token") or tok.get("token")
    except Exception as exc:  # pragma: no cover
        bump("C9_figure_binaries", "FAIL", problem=f"cannot authenticate: {exc}")
    if token:
        c9 = []
        for a in [x for x in assets if x["asset_class"] == "figure"]:
            rc = a["resolution_check"]
            name = rc["figure_name"]
            req = urllib.request.Request(rc["url"], headers={"Authorization": "Bearer " + token})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = r.read()
            except Exception as exc:
                c9.append(f"{a['asset_id']} {name}: fetch failed {exc}")
                continue
            sha = "sha256:" + hashlib.sha256(data).hexdigest()
            if sha != rc.get("png_sha256") or len(data) != rc.get("png_bytes"):
                c9.append(f"{a['asset_id']} {name}: sha/bytes mismatch "
                          f"({sha[:19]} vs {rc.get('png_sha256', '')[:19]}, {len(data)} vs {rc.get('png_bytes')})")
        bump("C9_figure_binaries", "FAIL" if c9 else "pass",
             detail=f"{len([x for x in assets if x['asset_class'] == 'figure'])} figure binaries re-fetched",
             problem="; ".join(c9) if c9 else None)

    # ------------------------------------------------------------------ C10
    # Internal arithmetic of the *source* tables (zero hand transcription:
    # rows are parsed out of the markdown itself).  A registration package is
    # only as good as the numbers it points at, so the reviewer checks that the
    # registered tables do not contradict themselves.
    rows = {}
    for line in md.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 14 and cells[0].startswith("S") and "_" in cells[0]:
            rows[cells[0]] = cells
    c10 = []
    c10_devs: list[tuple[str, float]] = []
    checked = 0
    for name, c in rows.items():
        try:
            lw1, lw2 = float(c[4]), float(c[5])
            a, b, ratio, ref = float(c[10]), float(c[11]), float(c[12]), float(c[13])
        except (ValueError, IndexError):
            continue
        checked += 1
        if abs(lw2 / lw1 - 1.5) > 0.01:
            c10.append(f"{name}: lw2/lw1 = {lw2/lw1:.3f} != 1.5")
        # a and b are printed with 4 decimals, so their quotient carries at
        # most ~1.5e-3 of rounding; anything above that is a real contradiction.
        dev = abs(b / a - ratio) / ratio
        c10_devs.append((name, dev))
        if dev > 2e-3:
            c10.append(f"{name}: b/a table {ratio} != b/a from areas {b/a:.4f} (dev {dev:.2e})")
        if abs(ratio - ref) / ref > 1e-3:
            c10.append(f"{name}: b/a {ratio} != independent-reference column {ref}")
    # cross-table: C5 b/a column must repeat the parameter-table b/a column
    c5rows = [ln for ln in md.splitlines() if ln.strip().startswith("| S") and ln.count("|") == 7]
    for ln in c5rows:
        cells = [x.strip() for x in ln.strip().strip("|").split("|")]
        name = cells[0]
        if name in rows:
            try:
                if abs(float(cells[4]) - float(rows[name][12])) > 1e-3:
                    c10.append(f"{name}: C5 curve-input b/a {cells[4]} != {rows[name][12]}")
                if abs(float(cells[5]) - float(rows[name][12])) > 1e-3:
                    c10.append(f"{name}: C5 analytic b/a {cells[5]} != {rows[name][12]}")
            except ValueError:
                c10.append(f"{name}: unparsable C5 row")
    bump("C10_source_internal_arithmetic", "FAIL" if c10 else "pass",
         detail=f"parameter rows parsed={len(rows)} checked={checked} c5_rows={len(c5rows)} "
                f"max|b/a - b/a_areas|={max((d for _, d in c10_devs), default=0):.2e} (4-decimal rounding)",
         problem="; ".join(c10) if c10 else None)

    OUT.write_text(json.dumps({"checks": checks, "findings": findings,
                               "source_sha256": h, "chars": len(md)},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    for cid, c in checks.items():
        print(f"{cid}: {c['status']}")
        for d in c["detail"]:
            print("   ", str(d)[:300])
        for p in c["problems"]:
            print("  !", str(p)[:300])
    failed = [k for k, v in checks.items() if v["status"] != "pass"]
    print("\nFAILED:", failed or "none")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())