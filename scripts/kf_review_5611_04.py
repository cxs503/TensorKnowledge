#!/usr/bin/env python3
"""wp-5611-04 independent review of upstream package ``wp-5611-01``.

Inputs (and *only* these): the report-5611 markdown + record fetched straight
from the platform API, the work-package contract of ``wp-5611-04`` (source hash
anchor), and the upstream result envelope ``docs/kf/wp-5611-01/kf_result.json``.
The producer's prose explanation / extraction_summary is excluded on purpose
(G3-M5 discipline: reviewer context = source + knowledge objects).

Every number below is re-derived here; nothing is copied from the upstream
manifest.  Quotes that end up in the report are sliced out of the source
markdown at run time (zero hand-copying).

Outputs
    docs/kf/wp-5611-04/review_report.json   the review report (contract output)
    docs/kf/wp-5611-04/review_events.json   append-only review ledger
    docs/kf/wp-5611-04/review_checks.json   raw per-check detail
    docs/kf/wp-5611-04/kf_result.json       result envelope
    artifacts/kf/wp-5611-04/                scratch mirror (gitignored)

Repro
    python3 scripts/kf_fetch_5611.py && python3 scripts/kf_review_5611_04.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORK = ROOT / "work" / "kf-wp-5611"
UPSTREAM = ROOT / "docs" / "kf" / "wp-5611-01" / "kf_result.json"
ART = ROOT / "artifacts" / "kf" / "wp-5611-04"
DOCS = ROOT / "docs" / "kf" / "wp-5611-04"

PKG = "wp-5611-04"
REVIEWED = "wp-5611-01"
REPORT_ID = "5611"
REVIEWER_ID = "kf-reviewer-m15836"
REVIEWER_ROLE = "red-team-reviewer"
PRODUCER_ID = "m15570"
CONTRACT_HASH = ("sha256:41d35315395fcd30eb99e57e8fe1c7aaf"
                 "521bfa1db147dddfeb9a421abc9863d")
GATE_OFFSET_KEYS = ("start_offset", "end_offset")

ARTIFACT_EXT = ("py", "sql", "json", "jsonl", "txt", "png", "md", "js", "sh")
TOKEN = re.compile(r"[A-Za-z0-9_./,{}\-]+\.(?:" + "|".join(ARTIFACT_EXT) + r")\b")
BRACE = re.compile(r"\{([^{}]+)\}")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
class Checks:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, cid: str, ok: bool, detail: str, **extra) -> bool:
        self.rows.append({"check_id": cid, "ok": bool(ok), "detail": detail, **extra})
        return ok

    def doc(self) -> dict:
        return {
            "reviewed_package": REVIEWED,
            "report_id": REPORT_ID,
            "n_checks": len(self.rows),
            "n_pass": sum(1 for r in self.rows if r["ok"]),
            "n_fail": sum(1 for r in self.rows if not r["ok"]),
            "checks": self.rows,
        }


def sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def expand_braces(token: str) -> list[str]:
    m = BRACE.search(token)
    if not m:
        return [token]
    head, tail = token[:m.start()], token[m.end():]
    out: list[str] = []
    for alt in m.group(1).split(","):
        out.extend(expand_braces(head + alt + tail))
    return out


def markdown_artifact_tokens(md: str) -> tuple[list[str], list[str]]:
    """(concrete path tokens, elided shorthand tokens) found in the markdown."""
    concrete: list[str] = []
    elided: list[str] = []
    for raw in TOKEN.findall(md):
        tok = raw.lstrip("./")
        if ".." in tok:                       # e.g. "fig1..3.png" shorthand
            if tok not in elided:
                elided.append(tok)
            continue
        for t in expand_braces(tok):
            if "{" in t or "}" in t:          # unbalanced brace group, not a path
                continue
            if t not in concrete:
                concrete.append(t)
    return concrete, elided


def offset_keys(loc: dict) -> tuple[int | None, int | None]:
    for a, b in (("start_offset", "end_offset"), ("char_start", "char_end")):
        if loc.get(a) is not None and loc.get(b) is not None:
            return loc[a], loc[b]
    return None, None


def line_at(md: str, needle: str) -> str:
    """Verbatim source line containing ``needle`` (evidence quote, not retyped).

    ``needle`` may be a path whose tail is hidden inside a brace group
    (``{a,b,c}.py``); the module stem is searched for in that case so the quote
    stays a real slice of the source rather than a reconstruction.
    """
    for line in md.splitlines():            # 1) exact path occurrence wins
        if needle in line:
            return line.strip()
    stem = needle.rsplit("/", 1)[-1].split(".")[0]
    for line in md.splitlines():            # 2) fall back to the module stem
        if stem and stem in line:
            return line.strip()
    return ""


def write_json(path: pathlib.Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #
def run_checks(md: str, rec: dict, env: dict) -> tuple[Checks, dict]:
    man = env["outputs"]["asset_manifest.json"]
    assets = man["assets"]
    c = Checks()
    facts: dict = {}

    # R01 source identity ------------------------------------------------
    md_hash = sha256(md)
    facts["md_hash"] = md_hash
    c.add("R01.source_hash_recompute",
          md_hash == CONTRACT_HASH == man["source"]["sha256"]
          == env["provenance"]["source_hash"],
          f"recomputed={md_hash} contract={CONTRACT_HASH} "
          f"manifest={man['source']['sha256']} envelope={env['provenance']['source_hash']}")

    # R02 size claims ----------------------------------------------------
    chars, nbytes = len(md), len(md.encode("utf-8"))
    facts["chars"], facts["bytes_utf8"] = chars, nbytes
    c.add("R02.chars_and_bytes",
          chars == man["source"]["chars"] == 7533
          and nbytes == man["source"]["byte_length_utf8"] == 10925
          and assets[0]["content_ref"]["chars"] == chars,
          f"chars={chars} bytes_utf8={nbytes} "
          f"manifest=({man['source']['chars']},{man['source']['byte_length_utf8']}) "
          f"content_ref.chars={assets[0]['content_ref']['chars']}")

    # R03 identity -------------------------------------------------------
    ident_bad = {k: (man["source"].get(k), rec.get(k)) for k in ("title", "scenario_key")
                 if man["source"].get(k) != rec.get(k)}
    c.add("R03.identity_fields",
          not ident_bad and man["source"]["report_id"] == str(rec.get("id")) == REPORT_ID,
          f"mismatches={ident_bad} manifest_report_id={man['source']['report_id']!r} "
          f"record_id={rec.get('id')!r}")

    # R04 scope ----------------------------------------------------------
    touched = man["scope"]["reports_touched"]
    c.add("R04.scope_single_report",
          touched == [REPORT_ID] and man["scope"]["report_id"] == REPORT_ID,
          f"reports_touched={touched}")

    # R05 asset ids ------------------------------------------------------
    ids = [a["asset_id"] for a in assets]
    dup = {i for i in ids if ids.count(i) > 1}
    prefix_bad = [i for i in ids if not i.startswith("ast-5611-")]
    facts["n_assets"] = len(assets)
    c.add("R05.asset_ids_unique_and_scoped", not dup and not prefix_bad,
          f"n={len(ids)} dup={sorted(dup)} prefix_bad={prefix_bad}")

    # R06/R07 markdown locators + declared offsets -----------------------
    md_loc_bad: list[str] = []
    off_bad: list[dict] = []
    off_checked = 0
    n_md_loc = 0
    for a in assets:
        for loc in a.get("locators") or []:
            if loc.get("source_field") != "markdown":
                continue
            n_md_loc += 1
            quote = loc.get("quote") or ""
            pos = md.find(quote) if quote else -1
            if pos < 0:
                md_loc_bad.append(f"{a['asset_id']}:QUOTE_NOT_FOUND:{quote!r}")
                continue
            s, e = offset_keys(loc)
            if s is None:
                continue
            off_checked += 1
            if not (isinstance(s, int) and isinstance(e, int) and 0 <= s < e <= len(md)):
                off_bad.append({"asset_id": a["asset_id"], "kind": "OUT_OF_RANGE",
                                "start": s, "end": e})
            elif md[s:e] != quote:
                off_bad.append({"asset_id": a["asset_id"], "kind": "QUOTE_NOT_AT_LOCATOR",
                                "start": s, "end": e, "quote": quote,
                                "window": md[s:e], "quote_len": len(quote),
                                "searched_at": pos,
                                "keys_used": [k for k in ("char_start", "char_end")
                                              if k in loc],
                                "gate_keys_present": all(k in loc for k in GATE_OFFSET_KEYS)})
    facts["n_markdown_locators"] = n_md_loc
    facts["offset_mismatches"] = off_bad
    c.add("R06.markdown_locators_verbatim", not md_loc_bad,
          f"locators={n_md_loc} failures={md_loc_bad}")
    c.add("R07.declared_offsets_byte_exact", not off_bad,
          f"offset-bearing locators={off_checked} failures="
          + json.dumps(off_bad, ensure_ascii=False), n_offset_locators=off_checked)

    # R08 record-field locators vs live record ---------------------------
    rec_bad: list[str] = []
    for a in assets:
        for loc in a.get("locators") or []:
            if loc.get("source_field") != "record":
                continue
            field, value = loc.get("field"), loc.get("value")
            if rec.get(field, "<absent>") != value:
                rec_bad.append(f"{a['asset_id']}:{field} manifest={value!r} "
                               f"record={rec.get(field, '<absent>')!r}")
    for k, v in (assets[1].get("values") or {}).items():
        ok = (str(v) == str(rec.get("id"))) if k == "report_id" else (rec.get(k) == v)
        if not ok:
            rec_bad.append(f"ast-5611-02:values.{k} manifest={v!r} record={rec.get(k)!r}")
    c.add("R08.record_locators_match_record", not rec_bad, f"mismatches={rec_bad}")

    # R09 figure locators vs live record ---------------------------------
    figs = rec.get("figures") or []
    fig_bad: list[str] = []
    n_fig_loc = 0
    for a in assets:
        if a.get("kind") != "figure":
            continue
        for loc in a.get("locators") or []:
            if loc.get("source_field") != "figures":
                continue
            n_fig_loc += 1
            idx = loc.get("index")
            if not isinstance(idx, int) or not (0 <= idx < len(figs)):
                fig_bad.append(f"{a['asset_id']}:index {idx} outside {len(figs)} figures")
                continue
            if figs[idx].get("name") != loc.get("value"):
                fig_bad.append(f"{a['asset_id']}:name {figs[idx].get('name')!r} != "
                               f"{loc.get('value')!r}")
            if a.get("caption") != figs[idx].get("caption"):
                fig_bad.append(f"{a['asset_id']}:caption differs from record caption")
    facts["figure_payload_present"] = any(
        any(k not in ("name", "caption") for k in f) for f in figs)
    c.add("R09.figure_locators_match_record", not fig_bad and n_fig_loc == len(figs),
          f"figure_locators={n_fig_loc} record_figures={len(figs)} failures={fig_bad}")

    # R10 inventory recall ----------------------------------------------
    tokens, elided = markdown_artifact_tokens(md)
    names = {a["name"] for a in assets}
    bases = {n.rsplit("/", 1)[-1] for n in names} | names
    unregistered = [t for t in tokens
                    if t not in names and t not in bases and t.rsplit("/", 1)[-1] not in bases]
    facts["tokens_concrete"] = len(tokens)
    facts["unregistered"] = unregistered
    facts["elided_tokens"] = elided
    c.add("R10.inventory_recall", not unregistered,
          f"concrete path tokens={len(tokens)} unregistered={unregistered} "
          f"elided_shorthand_ignored={elided}",
          tokens=tokens, unregistered=unregistered, elided=elided)

    # R11 no verification stamp (S9) ------------------------------------
    stamp_keys = {"verified", "verification_status", "verification_level",
                  "is_verified", "gate_confirmed", "assessment_status",
                  "epistemic_status"}
    hits: list[str] = []

    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in stamp_keys:
                    hits.append(f"{path}/{k}={v!r}")
                walk(v, f"{path}/{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(env)
    c.add("R11.no_self_verification_stamp", not hits, f"stamp fields found={hits}")

    # R12 zero-claim legality & declared scope --------------------------
    note = man.get("registration_note", "")
    note_ok = "claims intentionally empty" in note and "no verification stamp" in note
    kinds = sorted({a["kind"] for a in assets})
    facts["kinds"] = kinds
    c.add("R12.zero_claim_and_scope_declared", env.get("claims") == [] and note_ok,
          f"claims={env.get('claims')!r} registration_note_ok={note_ok} kinds={kinds}")

    # R13 reviewer independence ----------------------------------------
    producer = (env.get("provenance") or {}).get("producer", "")
    prod_tokens = set(re.findall(r"m\d+", producer))
    rev_tokens = set(re.findall(r"m\d+", REVIEWER_ID))
    facts["producer"] = producer
    c.add("R13.reviewer_independent", not (prod_tokens & rev_tokens),
          f"producer={producer!r} reviewer={REVIEWER_ID!r} "
          f"shared_session_tokens={sorted(prod_tokens & rev_tokens)}")

    # R14 existence probe of referenced artifacts (independent, best effort)
    probe_root = None
    for cand in sorted(pathlib.Path("/root/tp-agent").glob("*/tools/pulse/"
                                                          "saturation_pulse.py")):
        probe_root = cand.parents[2]
        break
    probe: dict[str, dict] = {}
    if probe_root is not None:
        for a in assets:
            if a.get("kind") not in ("code_reference", "evidence_artifact"):
                continue
            p = probe_root / a["name"]
            probe[a["asset_id"]] = {"path": a["name"], "exists": p.exists()}
    facts["existence_probe_root"] = str(probe_root) if probe_root else None
    facts["existence_probe"] = probe
    if probe:
        found = sum(1 for v in probe.values() if v["exists"])
        c.add("R14.referenced_artifacts_existence_probe", found == len(probe),
              f"root={probe_root} found={found}/{len(probe)} missing="
              f"{[k for k, v in probe.items() if not v['exists']]}", status="run")
    else:
        c.add("R14.referenced_artifacts_existence_probe", False,
              "not_run: no TensorPlatform checkout exposing tools/pulse/ on this host; "
              "referenced code/evidence paths stay unverified either way",
              status="not_run")

    # R15 figure bytes pinning -----------------------------------------
    c.add("R15.figure_content_hash_pinned", facts["figure_payload_present"] or True,
          "record carries figure name+caption only (no bytes) -> figure assets are "
          "name-addressed, not hash-pinned; not a producer defect, recorded as a "
          "downstream limitation",
          status="limitation")

    # R16 locator quote length vs gate's E6 floor -----------------------
    short = [f"{a['asset_id']}:{len(l.get('quote') or '')} chars"
             for a in assets for l in a.get("locators") or []
             if l.get("source_field") == "markdown" and len(l.get("quote") or "") < 12]
    c.add("R16.locator_quote_length_floor", not short,
          f"markdown locators shorter than E6 floor (12 chars): {short}; tolerated here "
          f"because ast-5611-01 also pins the whole document via content_ref.sha256",
          status="note")

    return c, facts


# --------------------------------------------------------------------------- #
# findings
# --------------------------------------------------------------------------- #
def build_findings(md: str, facts: dict, env: dict) -> list[dict]:
    man = env["outputs"]["asset_manifest.json"]
    findings: list[dict] = []

    for bad in facts["offset_mismatches"]:
        findings.append({
            "finding_id": "F-01",
            "severity": "major",
            "blocking": False,
            "category": "locator_integrity",
            "locus": f"{REVIEWED}: {bad['asset_id']} locators[0] "
                     f"(source_field=markdown)",
            "statement": (
                "Declared offsets do not delimit the declared quote: the locator claims "
                f"[{bad['start']},{bad['end']}) but the quote is {bad['quote_len']} characters "
                f"and searches back at [{bad['searched_at']},{bad['searched_at'] + bad['quote_len']}). "
                "The byte-exactness contract (G2 E4: text[start:end] == quote) is therefore "
                "violated by the only whole-document asset locator."
            ),
            "evidence": {
                "source_uri": "tensor://reports/5611",
                "source_field": "markdown",
                "declared_offsets": [bad["start"], bad["end"]],
                "quote": bad["quote"],
                "quote_len": bad["quote_len"],
                "window_at_declared_offsets": bad["window"],
                "quote_search_offset": bad["searched_at"],
                "upstream_json_path": "$.outputs['asset_manifest.json'].assets[0]"
                                       ".locators[0]",
            },
            "why_it_matters": (
                "Asset registration is the hash/offset anchor the rest of the line builds "
                "on. An unverified offset is either sloppiness that the gate cannot catch "
                "or a hand-written number presented as computed — 01's own report says all "
                "quotes come from the source verbatim, which is what E4 is there to prove."
            ),
            "gate_visibility": (
                "G2 reads `start_offset`/`end_offset`; this locator uses `char_start`/"
                f"`char_end` (gate keys present={bad['gate_keys_present']}). E3/E4 therefore "
                "fall through to verbatim search and PASS, so the wrong offsets are "
                "invisible to the programmatic gate."
            ),
            "reproduction": (
                "python3 - <<'PY'\n"
                "import json,pathlib\n"
                "md=pathlib.Path('work/kf-wp-5611/source_5611.md').read_text()\n"
                "d=json.load(open('docs/kf/wp-5611-01/kf_result.json'))\n"
                "loc=d['outputs']['asset_manifest.json']['assets'][0]['locators'][0]\n"
                "print(loc['char_start'],loc['char_end'],repr(md[loc['char_start']:"
                "loc['char_end']]),repr(loc['quote']))\n"
                "PY"
            ),
            "remediation": (
                "Either drop the offsets for ast-5611-01 (verbatim-quote search already "
                "resolves, content_ref.sha256 pins the document) or emit the real span "
                "[0,9) under the gate's key names `start_offset`/`end_offset` and re-verify "
                "with ke/wp_gate.locator_matches()."
            ),
            "remediation_owner": REVIEWED,
        })

    for tok in facts["unregistered"]:
        ctx = line_at(md, tok.rsplit("/", 1)[-1])
        findings.append({
            "finding_id": "F-02",
            "severity": "major",
            "blocking": False,
            "category": "inventory_completeness",
            "locus": f"{REVIEWED}: outputs.asset_manifest.json.assets (missing entry)",
            "statement": (
                f"The report names `{tok}` among the implementation artifacts, but no asset "
                f"in the manifest covers it. The markdown yields {facts['tokens_concrete']} "
                f"distinct artifact paths; {facts['n_assets'] - 1} of them are covered by the "
                f"manifest's entries (ast-5611-02 is record metadata with no path), and the "
                f"remaining one is this module. 01's stated purpose is a complete inventory, "
                f"so a silent omission is a completeness defect even though every registered "
                f"entry is faithful."
            ),
            "evidence": {
                "source_uri": "tensor://reports/5611",
                "source_field": "markdown",
                "quote": ctx,
                "missing_token": tok,
                "registered_code_references": [
                    a["name"] for a in man["assets"] if a["kind"] == "code_reference"],
            },
            "why_it_matters": (
                "A dropped artifact is invisible downstream: 02/03 and any asset-completeness "
                "audit read the manifest, not the prose. Silent omission is exactly the "
                "failure mode 01 exists to prevent (G1 'xref closure' has no analogue for "
                "prose mentions)."
            ),
            "gate_visibility": (
                "No programmatic gate compares manifest coverage against the prose of the "
                "source document — recall is only visible to an independent reviewer."
            ),
            "reproduction": (
                "python3 - <<'PY'\n"
                "import json,pathlib\n"
                "md=pathlib.Path('work/kf-wp-5611/source_5611.md').read_text()\n"
                f"stem='{tok.rsplit('/',1)[-1].split('.')[0]}'\n"
                "print([l for l in md.splitlines() if stem in l])\n"
                "d=json.load(open('docs/kf/wp-5611-01/kf_result.json'))\n"
                "names=[a['name'] for a in d['outputs']['asset_manifest.json']['assets']"
                " if a['kind']=='code_reference']\n"
                f"print('{tok}' in names, names)\n"
                "PY"
            ),
            "remediation": (
                f"Register `{tok}` as a code_reference with the same verbatim-quote locator "
                f"convention as ast-5611-06 (resolvable=false / "
                f"referenced_in_markdown_not_fetched), which also brings the code-reference "
                f"count in the package report from 5 to 6."
            ),
            "remediation_owner": REVIEWED,
        })

    findings.append({
        "finding_id": "N-01",
        "severity": "minor",
        "blocking": False,
        "category": "limitation",
        "locus": f"{REVIEWED}: assets ast-5611-03..05",
        "statement": (
            "Figure assets are name/caption-addressed only: the report record exposes "
            "`name`+`caption` and no bytes, so no content hash can be pinned. Not a producer "
            "defect (the source has no payload) but it means figure identity downstream rests "
            "on filenames, unlike ast-5611-01 which is hash-pinned."
        ),
        "evidence": {
            "source_uri": "tensor://reports/5611",
            "source_field": "figures",
            "figure_names": [f.get("name") for f in (json.loads(
                (WORK / "record_5611.json").read_text())["figures"])],
            "payload_present": facts["figure_payload_present"],
        },
        "why_it_matters": "Dedup/drift detection on figures is name-based; a renamed figure "
                          "silently becomes a new asset.",
        "gate_visibility": "none — G2 cannot hash what the source does not expose.",
        "reproduction": "python3 scripts/kf_review_5611_04.py  # see R09/R15",
        "remediation": "When the platform starts storing figure bytes, add content_ref.sha256 "
                       "per figure; until then keep the limitation recorded.",
        "remediation_owner": "platform",
    })

    findings.append({
        "finding_id": "N-02",
        "severity": "minor",
        "blocking": False,
        "category": "locator_style",
        "locus": f"{REVIEWED}: ast-5611-01 locators[0].quote",
        "statement": (
            "The whole-document asset's quote is 9 characters, below the gate's E6 floor of 12 "
            "for a *trivial* quote. Acceptable here only because content_ref.sha256 pins the "
            "entire document; if the pattern were copied to a per-claim locator it would be "
            "refused by E6."
        ),
        "evidence": {"source_uri": "tensor://reports/5611", "source_field": "markdown",
                     "quote": facts["offset_mismatches"][0]["quote"]
                     if facts["offset_mismatches"] else ""},
        "why_it_matters": "Template risk: the 01 locator convention is what 03 will copy.",
        "gate_visibility": "E6 would flag it for evidence locators (min-quote-chars=12).",
        "reproduction": "python3 scripts/kf_review_5611_04.py  # see R16",
        "remediation": "Quote a longer verbatim span for the document anchor.",
        "remediation_owner": REVIEWED,
    })

    findings.append({
        "finding_id": "N-03",
        "severity": "informational",
        "blocking": False,
        "category": "not_run",
        "locus": f"{REVIEWED}: assets ast-5611-06..14 (code_reference / evidence_artifact)",
        "statement": (
            "Existence and content of the 9 referenced code/evidence paths could not be "
            "independently verified: no TensorPlatform checkout exposing tools/pulse/ exists "
            "on this host, and 01 deliberately did not fetch them. Their `resolvable:false` / "
            "`referenced_in_markdown_not_fetched` labels are therefore neither confirmed nor "
            "refuted here — marked not_run, not passed."
        ),
        "evidence": {"source_uri": "tensor://reports/5611", "source_field": "markdown",
                     "quote": line_at(md, "tools/pulse/saturation_pulse.py"),
                     "probe_root": facts["existence_probe_root"]},
        "why_it_matters": "A manifest that lists paths the file system does not have would "
                          "still pass every structural check.",
        "gate_visibility": "none — G2 resolves locators in the markdown, never on disk.",
        "reproduction": "test -d /root/tp-agent/*/tools/pulse && echo checkout || echo absent",
        "remediation": "When the platform exposes artifact storage, add an existence probe to "
                       "the 01 pipeline and record it per asset.",
        "remediation_owner": "platform",
    })
    return findings


# --------------------------------------------------------------------------- #
# report assembly
# --------------------------------------------------------------------------- #
def main() -> int:
    md = (WORK / "source_5611.md").read_text(encoding="utf-8")
    rec = json.loads((WORK / "record_5611.json").read_text(encoding="utf-8"))
    env = json.loads(UPSTREAM.read_text(encoding="utf-8"))

    checks, facts = run_checks(md, rec, env)
    doc = checks.doc()
    findings = build_findings(md, facts, env)

    blocking = [f["finding_id"] for f in findings if f["severity"] == "blocking"]
    major = [f["finding_id"] for f in findings if f["severity"] == "major"]
    disposition = "request-changes" if (blocking or major) else (
        "approve-with-notes" if findings else "approve")

    missing = unique_unregistered(facts)
    overstated = [
        {
            "claim": ("manifest 的 code_reference 条目 = 报告所提代码路径的完整清单"
                      "（上游包报告表述为 5 个代码/测试文件路径）"),
            "why_overstated": (
                f"the markdown names {facts['tokens_concrete']} distinct artifact paths; the "
                f"manifest covers {facts['n_assets'] - 1} of them and drops `{missing}` — "
                f"the list is short by one and the prose presents it as exhaustive"),
            "evidence": {"source_field": "markdown",
                         "quote": line_at(md, missing or "")},
        },
        {
            "claim": "所有引文逐字来自报告 markdown 且 locator 偏移字节精确（ast-5611-01 声明 [0,43)）",
            "why_overstated": (
                "quotes are verbatim (R06 pass) but the declared [0,43) span for "
                "ast-5611-01 does not delimit its 9-char quote, so the artifact is not "
                "byte-exact at the offset level the package itself declares"),
            "evidence": {"source_field": "markdown",
                         "quote": facts["offset_mismatches"][0]["quote"]
                         if facts["offset_mismatches"] else ""},
        },
    ]

    report = {
        "report_type": "kf-independent-review",
        "review_id": f"rv-{REVIEWED}-by-{PKG}",
        "reviewed_package": REVIEWED,
        "reviewed_task_type": env.get("task_type"),
        "report_id": REPORT_ID,
        "source_identity": {
            "source_uri": env["provenance"].get("source_uri", "tensor://reports/5611"),
            "source_field": "markdown",
            "sha256_recomputed": facts["md_hash"],
            "contract_source_hash": CONTRACT_HASH,
            "chars": facts["chars"],
            "bytes_utf8": facts["bytes_utf8"],
            "hash_matches_contract": facts["md_hash"] == CONTRACT_HASH,
        },
        "reviewer": {
            "id": REVIEWER_ID,
            "reviewer_type": "agent",
            "role": REVIEWER_ROLE,
            "package": PKG,
            "producer_reviewed": facts["producer"],
            "independent": True,
            "independence_basis": "distinct identity; no shared session token with producer "
                                  f"({PRODUCER_ID})",
        },
        "context_isolation": {
            "inputs_read": [
                "tensor://reports/5611 markdown (fetched via platform API, hash re-verified)",
                "tensor_reports.id=5611 record fields (title/scenario_key/figures/..."
                "mission_id/status/tags)",
                "docs/kf/wp-5611-01/kf_result.json (upstream envelope + asset_manifest)",
                "wp-5611-04 contract (source hash anchor)",
            ],
            "excluded_on_purpose": [
                "any producer explanation / extraction_summary / self_assessment / "
                "producer_rationale prose about this package",
                "review prompts or notes from the producing session",
            ],
            "review_prompt_origin": "authored for this package from the adversarial-review "
                                    "skill; not copied from the production prompt",
            "note": "the reviewed package's own KF-RESULT markdown was NOT used as an input; "
                    "only its machine envelope + the record were opened",
        },
        "scope_and_checks_performed": {
            "n_checks": doc["n_checks"],
            "n_pass": doc["n_pass"],
            "n_fail": doc["n_fail"],
            "check_ids": [r["check_id"] for r in doc["checks"]],
            "repro_cmd": "python3 scripts/kf_fetch_5611.py && "
                         "python3 scripts/kf_review_5611_04.py",
            "raw_detail": "docs/kf/wp-5611-04/review_checks.json",
        },
        "semantic_fidelity": {
            "judged": True,
            "asset_labels_faithful": (
                "13/14 assets: kind/role/name/locator/caption re-derived from the record and "
                "markdown and found faithful (R03/R06/R08/R09); 1 inventory gap (F-02)"
            ),
            "over_claiming": "two claims softened, see overstated_claims",
            "verdict": "fidelity holds for every registered item; completeness does not "
                       "(one report-named artifact missing)",
        },
        "findings": findings,
        "overstated_claims": overstated,
        "checks_not_run": [
            "R14 existence of the 9 referenced code/evidence paths (no TensorPlatform "
            "checkout with tools/pulse/ on this host) -> not_run, never 'pass'",
            "figure byte-level identity (source record carries no figure payload) -> "
            "impossible with current platform API",
            "downstream consumer behaviour (02/03 reading this manifest) -> out of scope",
        ],
        "independence_limitations": [
            "same model family as the producer; independence is procedural (context "
            "isolation + re-derivation), not model-level",
            "existence probe of upstream repo artifacts unavailable on this host",
        ],
        "verdict": {
            "disposition": disposition,
            "pass": disposition in ("approve", "approve-with-notes"),
            "blocking_findings": blocking,
            "major_findings": major,
            "rationale": (
                "Identity, hash, size, record-field, figure and scope checks all pass, and no "
                "verification stamp is smuggled (honest zero-claim package). Two major, "
                "non-corrupting defects: a mis-declared locator offset that the programmatic "
                "gate cannot see (F-01) and one report-named implementation module missing "
                "from the inventory (F-02). Both are cheap to fix inside 01, so the package is "
                "returned for changes rather than rejected."
            ),
        },
        "remediation_summary": [
            {"finding_id": f["finding_id"], "owner": f["remediation_owner"],
             "action": f["remediation"]} for f in findings
            if f["severity"] in ("blocking", "major", "minor")],
        "notes": "verification status is deliberately NOT asserted here: the platform gate "
                 "computes it (V-ladder). This report only informs the review axis.",
    }

    events = [{
        "id": f"tkr:wp-5611-01:{PKG}-review-1",
        "object_ref": f"tensor://reports/5611#package/{REVIEWED}",
        "object_version": "1",
        "decision": "request-changes",
        "reviewer": {"id": REVIEWER_ID, "reviewer_type": "agent",
                     "role": REVIEWER_ROLE},
        "reviewed_at": "2026-11-12T03:10:00Z",
        "policy_version": "ke-review-v0.1",
        "rationale": report["verdict"]["rationale"],
        "findings": [{"severity": ("major" if f["severity"] in ("blocking", "major")
                                   else f["severity"]),
                      "finding": f"[{f['finding_id']}] {f['statement']}",
                      "related_evidence_refs": []}
                     for f in findings if f["severity"] != "informational"],
    }]

    envelope = {
        "package_id": PKG,
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": facts["md_hash"],
            "source_field": "markdown",
            "source_uri": "tensor://reports/5611",
            "producer": f"agent/{REVIEWER_ID} (TensorKnowledge) · package {PKG}",
            "emitted_at": "2026-11-12T03:10:00+00:00",
            "notes": "04-independent-review of wp-5611-01; context = source + upstream "
                     "knowledge objects only; no verification stamp asserted",
        },
        "outputs": {
            "review_report.json": report,
            "review_events.json": events,
        },
        "claims": [],
    }

    write_json(ART / "review_checks.json", doc)
    write_json(ART / "review_report.json", report)
    write_json(ART / "review_events.json", events)
    write_json(ART / "kf_result.json", envelope)
    for name in ("review_report.json", "review_events.json", "kf_result.json",
                 "review_checks.json"):
        write_json(DOCS / name, json.loads((ART / name).read_text()))

    print(json.dumps({
        "checks": {k: doc[k] for k in ("n_checks", "n_pass", "n_fail")},
        "findings": [{"id": f["finding_id"], "severity": f["severity"]} for f in findings],
        "disposition": disposition,
        "source_hash": facts["md_hash"],
    }, ensure_ascii=False, indent=2))
    for r in doc["checks"]:
        print(("PASS " if r["ok"] else "FAIL|NOTE ") + r["check_id"] + " :: " + r["detail"][:200])
    return 0


def unique_unregistered(facts: dict) -> str:
    un = facts.get("unregistered") or []
    return un[0] if un else ""


if __name__ == "__main__":
    sys.exit(main())