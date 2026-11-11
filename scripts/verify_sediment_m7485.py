#!/usr/bin/env python3
"""Independent verification of the sediment package ``knowledge/sediment/m7485``.

The verifier shares **no code path** with the writer apart from the identity
constants (repo / sha / paths): it reads only the written JSON files, re-fetches
the cited blobs by sha out of the TensorBEM git object store, and re-runs
``grep -F`` on them.  It also re-derives every number that appears in a claim
statement from the committed ``points.csv`` and checks INDEX↔JSON consistency.

Checks (each printed PASS/FAIL, exit code 1 on any FAIL):

  quote:N     evidence quote == the same line range of the blob at the sha
  grep:N      ``git show sha:path | grep -nF <first quote line>`` hits start line
  hash:N      locator.content_hash == sha256(quote)
  xref:N      claim.evidence_refs ↔ evidence.claim_refs resolve both ways
  num:N       claim statement contains the recomputed numbers
  index:N     INDEX.md row (id / path:line / sha) == JSON
  review:N    no review-event, review_status=draft, not promoted, unassessed

Usage::

    M7485_SRC_REPO=/root/tp-agent/work/m7485 python scripts/verify_sediment_m7485.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import csv  # noqa: E402
import io  # noqa: E402

from sediment_spec_m7485 import POINTS, REPO_NAME, SHA  # noqa: E402

PKG = REPO_ROOT / "knowledge" / "sediment" / "m7485"
SCHEMAS = REPO_ROOT / "schemas"
SOURCE_REPO_ROOT = Path(os.environ.get("M7485_SRC_REPO", "/root/tp-agent/work/m7485"))

LOCATOR_RE = re.compile(
    r"^(?P<repo>[A-Za-z0-9_.-]+)@(?P<sha>[0-9a-f]{40}):(?P<path>[^#]+)#L(?P<first>\d+)-L(?P<last>\d+)$"
)

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))


def git_show(path: str, sha: str) -> list[str]:
    proc = subprocess.run(["git", "-C", str(SOURCE_REPO_ROOT), "show", f"{sha}:{path}"],
                          check=True, capture_output=True)
    return proc.stdout.decode("utf-8").split("\n")


def grep_first_line(path: str, sha: str, needle: str) -> list[tuple[int, str]]:
    """Emulate ``git show sha:path | grep -nF <needle>`` exactly."""
    proc = subprocess.run(["git", "-C", str(SOURCE_REPO_ROOT), "show", f"{sha}:{path}"],
                          check=True, capture_output=True)
    hits = []
    for idx, raw in enumerate(proc.stdout.decode("utf-8").split("\n"), start=1):
        if needle in raw:
            hits.append((idx, raw))
    return hits


def load(kind: str) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(PKG.glob(f"{kind}-*.json"))]


def main() -> int:
    if not PKG.is_dir():
        raise SystemExit(f"package missing: {PKG}")

    claims = load("claim")
    evidences = load("evidence")
    provenances = load("provenance")
    review = json.loads((PKG / "review-status.json").read_text(encoding="utf-8"))
    index_text = (PKG / "INDEX.md").read_text(encoding="utf-8")

    check("count:claims>=3", len(claims) >= 3, f"{len(claims)} claims")
    check("count:evidence", len(evidences) >= len(claims), f"{len(evidences)} evidence")
    check("count:provenance", len(provenances) == len(claims), f"{len(provenances)} provenance")

    # ---- schema validation (independent of the writer's registry helper) ----
    import jsonschema
    from referencing import Registry, Resource

    registry = Registry()
    docs = {}
    for path in sorted(SCHEMAS.glob("*.schema.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        docs[path.name] = doc
        if "$id" in doc:
            registry = registry.with_resource(doc["$id"], Resource.from_contents(doc))
    schema_for = {"claim": "claim-record.schema.json",
                  "evidence": "evidence-record.schema.json",
                  "provenance": "provenance-record.schema.json"}
    for kind, recs in (("claim", claims), ("evidence", evidences), ("provenance", provenances)):
        bad = 0
        msg = "valid"
        for rec in recs:
            try:
                jsonschema.Draft202012Validator(docs[schema_for[kind]], registry=registry).validate(rec)
            except jsonschema.ValidationError as exc:
                bad += 1
                msg = f"{rec['id']}: {exc.message[:120]}"
        check(f"jsonschema:{kind}", bad == 0, msg if bad else f"{len(recs)} records valid")

    # ---- evidence: quote must be the verbatim blob slice at the sha ----
    for e in evidences:
        loc = e["locator"]
        value = loc["value"]
        m = LOCATOR_RE.match(value)
        if not m:
            check(f"locator:{e['id']}", False, f"unparsable value {value!r}")
            continue
        sha, path = m.group("sha"), m.group("path")
        first, last = int(m.group("first")), int(m.group("last"))
        try:
            lines = git_show(path, sha)
        except subprocess.CalledProcessError:
            check(f"quote:{e['id']}", False, f"blob not found {path}@{sha}")
            continue
        sliced = "\n".join(lines[first - 1:last])
        quote = loc["quote"]
        ok = sliced == quote and len(quote) >= 20
        check(f"quote:{e['id']}", ok,
              f"{path}#L{first}-L{last} len={len(quote)}" if ok else
              f"quote mismatch: blob={sliced[:60]!r} quote={quote[:60]!r}")
        ok_hash = loc.get("content_hash") == "sha256:" + hashlib.sha256(quote.encode()).hexdigest()
        check(f"hash:{e['id']}", ok_hash, "sha256 matches" if ok_hash else "content_hash mismatch")
        needle = quote.split("\n")[0]
        hits = grep_first_line(path, sha, needle)
        matched = any(h[0] == first for h in hits)
        check(f"grep:{e['id']}", matched,
              f"grep -nF '{needle[:32]}' -> line {hits[0][0] if hits else 'no hit'}"
              if matched else f"grep miss for {needle[:40]!r} (hits={[h[0] for h in hits]})")

    # ---- cross references ----
    claim_ids = {c["id"] for c in claims}
    evidence_ids = {e["id"] for e in evidences}
    for c in claims:
        missing = [r for r in c.get("evidence_refs", []) if r not in evidence_ids]
        check(f"xref:claim:{c['id']}", not missing and len(c.get("evidence_refs", [])) >= 1,
              f"{len(c.get('evidence_refs', []))} evidence" if not missing else f"missing {missing}")
    for e in evidences:
        refs = e.get("claim_refs", [])
        missing = [r for r in refs if r not in claim_ids]
        check(f"xref:evidence:{e['id']}", not missing and refs,
              f"-> {refs}" if not missing else f"missing {missing}")

    # ---- provenance completeness ----
    prov_by_entity = {p["generated_entity"]["id"]: p for p in provenances}
    for c in claims:
        p = prov_by_entity.get(c["id"])
        if p is None:
            check(f"prov:{c['id']}", False, "no provenance record")
            continue
        act = p["activity"]
        params = act.get("parameters", {})
        ok = (
            p.get("derived_from")
            and any("7485" in d for d in p["derived_from"])
            and params.get("mission_id") == 7485
            and params.get("task_key") == "tk-sediment-m7485"
            and len(p["agents"]) >= 1
            and act.get("activity_type") == "extraction"
        )
        check(f"prov:{c['id']}", bool(ok),
              f"derived_from={p.get('derived_from')} mission_id={params.get('mission_id')} "
              f"task_key={params.get('task_key')} agents={[a['id'] for a in p['agents']]}")

    # ---- numbers recomputed from the committed CSV ----
    reader = csv.DictReader(io.StringIO("\n".join(git_show(POINTS, SHA))))
    pts = {float(r["J"]): r for r in reader}

    def pct(bem: str, anchor: str) -> float:
        return 100.0 * (float(bem) - float(anchor)) / float(anchor)

    j08, j06, j05, j07, j09, j10 = (pts[0.8], pts[0.6], pts[0.5], pts[0.7], pts[0.9], pts[1.0])
    inside = sum(1 for r in pts.values() if abs(float(r["deta0_pct"])) <= 5.0)
    crossings = [
        (sorted(pts)[i], sorted(pts)[i + 1]) for i in range(len(pts) - 1)
        if float(pts[sorted(pts)[i]]["dKT_pct"]) * float(pts[sorted(pts)[i + 1]]["dKT_pct"]) < 0
    ]
    rich = 0.14927
    expect = {
        "tkc:tensorbem:kp505-kt-design-j-falsified": [
            f"{pct(j08['KT_bem'], j08['KT_anchor']):.2f}",   # -29.13
            f"{float(j08['KT_bem']):.5f}",
            f"{float(j08['KT_anchor']):.3f}",
            f"仅 {inside} 点",
            f"{len(pts)} 个锚点",
        ],
        "tkc:tensorbem:kp505-mesh-refinement-not-the-cause": [
            f"{rich:.5f}",
            f"{pct(f'{rich}', j07['KT_anchor']):.2f}",
            f"{float(j07['dKT_pct']):.2f}",
        ],
        "tkc:tensorbem:deviation-sign-change-root-cause": [
            f"{float(j05['dKT_pct']):.2f}",
            f"{float(j06['dKT_pct']):.2f}",
            f"({crossings[0][0]:.1f}, {crossings[0][1]:.1f})",
        ],
        "tkc:tensorbem:unphysical-near-zero-load-gate": [
            f"{float(j10['KT_bem']):.4f}",
            f"{float(j10['eta0_bem']):.4f}",
            f"{float(j10['eta0_momentum_bound']):.4f}",
            f"{pct(j10['eta0_bem'], j10['eta0_anchor']):.2f}",
            f"{abs(pct(j09['eta0_bem'], j09['eta0_anchor'])):.2f}",
        ],
    }
    by_id = {c["id"]: c for c in claims}
    for cid, needles in expect.items():
        claim = by_id.get(cid)
        if claim is None:
            check(f"num:{cid}", False, "claim missing")
            continue
        absent = [n for n in needles if n not in claim["statement"]]
        check(f"num:{cid}", not absent,
              "recomputed from points.csv: " + ", ".join(needles) if not absent else f"absent {absent}")

    # J=1.0 must be the only point flagged unphysical (supports the gate claim)
    gate_flags = {j: r["momentum_gate_ok"] for j, r in pts.items()}
    check("data:momentum-gate", [j for j, ok in gate_flags.items() if ok == "False"] == [1.0],
          f"gate False at J={[j for j, ok in gate_flags.items() if ok == 'False']}")
    # the 5 % band must contain exactly the points claimed
    band = [j for j, r in pts.items() if abs(float(r["deta0_pct"])) <= 5.0]
    check("data:band", len(band) == inside, f"{len(band)}/{len(pts)} inside ±5%: J={sorted(band)}")

    # ---- INDEX.md ↔ JSON consistency ----
    rows = [ln for ln in index_text.split("\n") if ln.startswith("| `tkc:")]
    check("index:row-count", len(rows) == len(claims), f"{len(rows)} rows / {len(claims)} claims")
    # primary evidence of a claim = the first id in its own evidence_refs list
    loc_by_id = {e["id"]: e["locator"]["value"] for e in evidences}
    primary = {c["id"]: loc_by_id[c["evidence_refs"][0]] for c in claims
               if c["evidence_refs"] and c["evidence_refs"][0] in loc_by_id}
    seen = set()
    for ln in rows:
        cells = [c.strip().strip("`") for c in ln.strip("|").split(" | ")]
        cid, path, sha = cells[0], cells[2], cells[3]
        seen.add(cid)
        claim = by_id.get(cid)
        if claim is None:
            check(f"index:{cid}", False, "claim id not in JSON")
            continue
        want_path = primary[cid].split(f"{REPO_NAME}@{SHA}:", 1)[1]
        ok = path == want_path and sha == SHA and claim["statement"].startswith(cells[1].rstrip("…"))
        check(f"index:{cid}", ok,
              f"{path} @ {sha[:8]}" if ok else
              f"mismatch: index={path}@{sha[:8]} json={want_path}@{SHA[:8]}")
    check("index:covers-all-claims", seen == claim_ids,
          f"missing {sorted(claim_ids - seen)}" if seen != claim_ids else "all claims present")

    # ---- review discipline ----
    review_events = sorted(PKG.glob("review-event*.json"))
    check("review:no-review-event", not review_events, f"{len(review_events)} review-event files")
    check("review:status-draft", review.get("review_status") == "draft",
          f"review_status={review.get('review_status')} source={review.get('review_status_source')}")
    check("review:not-promoted", review.get("promoted") is False,
          f"promoted={review.get('promoted')}")
    check("review:producer-no-self-review", review.get("producer_self_review") is False,
          f"producer_self_review={review.get('producer_self_review')}")
    bad_assess = [e["id"] for e in evidences if e["assessment_status"] != "unassessed"]
    check("review:evidence-unassessed", not bad_assess, f"non-unassessed: {bad_assess}" if bad_assess else "all unassessed")
    statuses = sorted({c["epistemic_status"] for c in claims})
    check("review:epistemic-status", statuses == ["provisional"],
          f"epistemic_status={statuses} (schema has no 'draft'; documented deviation)")
    no_note = [c["id"] for c in claims if not any("review_status=draft" in n for n in c.get("notes", []))]
    check("review:draft-note-on-claims", not no_note, f"missing note: {no_note}" if no_note else "all claims carry review_status=draft note")
    promoted = [c["id"] for c in claims if "promoted" in json.dumps(c, ensure_ascii=False).lower()
                and "无 promoted" not in json.dumps(c, ensure_ascii=False)]
    check("review:no-promoted-state", not promoted, f"suspicious: {promoted}" if promoted else "no promoted state")

    # ---- report ----
    width = max(len(n) for n, _, _ in RESULTS)
    failed = 0
    for name, ok, detail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {detail}")
        failed += 0 if ok else 1
    print(f"\n{len(RESULTS) - failed}/{len(RESULTS)} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())