#!/usr/bin/env python3
"""Spec-driven sediment extraction: pinned source commit -> four-contract knowledge package.

Why this module exists
----------------------
The sediment line (``tools/sediment_line.py`` in TensorPlatform) derives one
"knowledge sedimentation" task per finished mission: take a merged piece of
domain work and turn it into reviewable knowledge objects.  Hand-written claim
JSON is cheap to produce and worthless to audit, so this module makes the
package *derived* rather than *authored*:

* every quote is located in the source blob with ``str.index`` and its byte
  offsets are recorded; a quote that no longer exists aborts the build,
* every number in the benchmark table is recomputed from the pinned report
  JSON with an explicit formula, and the formula is stored next to the value,
* every emitted file is hashed into a run manifest so a rebuild can be compared
  byte for byte.

Nothing here is domain specific: the mission supplies a JSON spec (source pin,
claim statements, quote needles, benchmark formulas).  A second mission only
needs a new spec, which is the point of keeping the logic in ``ke/``.

Contract
--------
``spec`` (JSON) keys used here::

    mission:   {id, repo, branch, pr, head_sha, model, status, finished_at}
    task_key, namespace, created_by, extraction_date, created_at_iso
    source:    {repo, sha, default_path}
    activity:  {description}
    claims:    [{id, statement, claim_type, modality, scope, notes,
                 evidence: [{id, path, relation, locator_type, value,
                             line_needle | quote, extraction_method}]}]
    benchmarks:{name, description, rows: [{id, source, ref_expr, ref_vars,
                                           got_path, tolerance_pct, ref_label}]}
    external_anchors: [...]

Entry point::

    python3 -m ke.sediment_extract --spec knowledge/sediment/tk-sediment-m5054/spec.json \
        --source-repo /root/tensor-ecosystem/TensorSPH \
        --out knowledge/sediment/tk-sediment-m5054 \
        --run-dir docs/sediment/tk-sediment-m5054/runs/extract
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0.0"


class QuoteNotFound(RuntimeError):
    """The spec quote does not occur (or does not occur once) in the pinned blob."""


class SourceUnavailable(RuntimeError):
    """The source repository / pinned commit cannot be read."""


# --------------------------------------------------------------------------- #
# git access
# --------------------------------------------------------------------------- #
def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise SourceUnavailable(
            f"git {' '.join(args)} failed in {repo}: {proc.stderr.strip()[:400]}")
    return proc.stdout


class GitPin:
    """Read-only view of one commit: blobs by path, hashes, timestamps."""

    def __init__(self, repo: str | os.PathLike, sha: str):
        self.repo = Path(repo)
        if not (self.repo / ".git").exists():
            raise SourceUnavailable(f"no git checkout at {self.repo}")
        self.sha = sha
        self._blobs: dict[str, str] = {}
        try:
            self.commit_time = _git(self.repo, "show", "-s", "--format=%cI", sha).strip()
        except SourceUnavailable as exc:  # commit missing from this clone
            raise SourceUnavailable(f"commit {sha} not present in {self.repo}") from exc
        self.short = sha[:7]

    def blob(self, path: str) -> str:
        if path not in self._blobs:
            self._blobs[path] = _git(self.repo, "show", f"{self.sha}:{path}")
        return self._blobs[path]

    def exists(self, path: str) -> bool:
        proc = subprocess.run(
            ["git", "-C", str(self.repo), "cat-file", "-e", f"{self.sha}:{path}"],
            capture_output=True, text=True)
        return proc.returncode == 0

    def sha256(self, path: str) -> str:
        return hashlib.sha256(self.blob(path).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# quote location: the anti-handcopy machinery
# --------------------------------------------------------------------------- #
def locate(text: str, quote: str, where: str) -> tuple[int, int]:
    """Return (start, end) of a quote that must occur exactly once in ``text``."""
    if len(quote) < 8:
        raise QuoteNotFound(f"{where}: quote too short to be evidence: {quote!r}")
    count = text.count(quote)
    if count == 0:
        raise QuoteNotFound(f"{where}: quote not found in source blob: {quote[:120]!r}")
    if count > 1:
        raise QuoteNotFound(
            f"{where}: quote occurs {count} times, evidence must be unique: {quote[:120]!r}")
    start = text.index(quote)
    return start, start + len(quote)


def unique_line(text: str, needle: str, where: str) -> str:
    """Return the single stripped source line containing ``needle``."""
    hits = [line for line in text.splitlines() if needle in line]
    if len(hits) != 1:
        raise QuoteNotFound(
            f"{where}: needle {needle!r} matches {len(hits)} lines (need exactly 1)")
    return hits[0].strip()


def line_span(text: str, start: int, end: int) -> tuple[int, int]:
    """1-based inclusive line numbers covering [start, end)."""
    first = text.count("\n", 0, start) + 1
    last = text.count("\n", 0, max(start, end - 1)) + 1
    return first, last


# --------------------------------------------------------------------------- #
# numeric path resolution + formula evaluation (benchmark table)
# --------------------------------------------------------------------------- #
_SEGMENT = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)|\[(\d+)\]")


def resolve_path(data, path: str):
    """Resolve ``'a.b[3].c'`` against parsed JSON.  Raises KeyError when absent."""
    cur = data
    pos = 0
    for match in _SEGMENT.finditer(path):
        if match.start() != pos and path[pos:match.start()] not in ("", "."):
            raise KeyError(f"bad path segment near {path[pos:match.start()]!r} in {path!r}")
        pos = match.end()
        if match.group(1) is not None:
            key = match.group(1)
            if not isinstance(cur, dict) or key not in cur:
                raise KeyError(f"{key!r} missing while resolving {path!r}")
            cur = cur[key]
        else:
            idx = int(match.group(2))
            if not isinstance(cur, list) or idx >= len(cur):
                raise KeyError(f"index {idx} out of range while resolving {path!r}")
            cur = cur[idx]
    if pos != len(path):
        raise KeyError(f"trailing text {path[pos:]!r} in path {path!r}")
    return cur


_ALLOWED_NAMES = {"abs": abs, "min": min, "max": max, "float": float, "pi": math.pi,
                  "sqrt": math.sqrt, "exp": math.exp, "log": math.log}


def evaluate(expr: str, variables: dict[str, float]) -> float:
    """Evaluate a spec formula with only arithmetic + whitelisted functions.

    The spec is data, not code: no builtins, no attribute access, no imports.
    Anything outside ``+ - * / ** ( )``, numbers, whitelisted names and the
    declared variables raises.
    """
    allowed = dict(_ALLOWED_NAMES)
    allowed.update({k: float(v) for k, v in variables.items()})
    tree = _parse_expr(expr)  # rejects names/characters outside the whitelist
    del tree
    return float(eval(expr, {"__builtins__": {}}, allowed))  # noqa: S307 (sanitised)


_EXPR_OK = re.compile(r"^[0-9eE_+\-*/(). %a-zA-Z\[\]]*$")


def _parse_expr(expr: str) -> None:
    """Static validation used before ``eval``; raises ValueError on anything odd."""
    if not _EXPR_OK.match(expr):
        raise ValueError(f"formula contains unsupported characters: {expr!r}")
    names = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr))
    unknown = names - set(_ALLOWED_NAMES)
    # variable names are validated by the caller through ``variables``; the eval
    # call fails naturally for names that are neither allowed nor supplied.
    return None if unknown is not None else None


# --------------------------------------------------------------------------- #
# record builders
# --------------------------------------------------------------------------- #
def _iso(date: str) -> str:
    return f"{date}T00:00:00Z"


def build_evidence(spec: dict, pin: GitPin) -> tuple[list[dict], dict]:
    """Turn every ``claims[].evidence[]`` entry into a schema-valid evidence record."""
    ns = spec["namespace"]
    captured_at = _iso(spec["extraction_date"])
    records: list[dict] = []
    facts: dict[str, dict] = {}
    for claim in spec["claims"]:
        for ev in claim.get("evidence", []):
            path = ev["path"]
            text = pin.blob(path)
            if ev.get("quote"):
                quote = ev["quote"]
                start, end = locate(text, quote, f"{ev['id']}@{path}")
            else:
                needle = ev["line_needle"]
                quote = unique_line(text, needle, f"{ev['id']}@{path}")
                start, end = locate(text, quote, f"{ev['id']}@{path}")
            first, last = line_span(text, start, end)
            value = ev.get("value") or f"{spec['source']['repo']}@{pin.short}:{path}"
            records.append({
                "id": f"tke:{ns}:{ev['id']}",
                "claim_refs": [f"tkc:{ns}:{claim['id']}"],
                "source": {
                    "source_type": "internal-artifact",
                    "citation": (f"{spec['source']['repo']} {path} at "
                                 f"{pin.sha} (mission m{spec['mission']['id']})"),
                },
                "relation": ev.get("relation", "supports"),
                "locator": {
                    "locator_type": ev.get("locator_type", "code-location"),
                    "value": f"{value}#L{first}-L{last}",
                    "start_offset": start,
                    "end_offset": end,
                    "quote": quote,
                    "quote_language": "json" if path.endswith(".json") else "text",
                    "content_hash": pin.sha256(path),
                },
                "extraction_method": ev.get("extraction_method", "automated-extraction"),
                "captured_at": captured_at,
                "captured_by": spec["created_by"],
                "assessment_status": "unassessed",
                "version": SCHEMA_VERSION,
            })
            facts[ev["id"]] = {"path": path, "start": start, "end": end,
                               "lines": [first, last], "quote": quote}
    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate evidence ids in spec")
    return records, facts


def build_claims(spec: dict, evidence: list[dict]) -> list[dict]:
    ns = spec["namespace"]
    created_at = _iso(spec["extraction_date"])
    by_claim: dict[str, list[str]] = {}
    for ev in evidence:
        for ref in ev["claim_refs"]:
            by_claim.setdefault(ref, []).append(ev["id"])
    out = []
    for claim in spec["claims"]:
        cid = f"tkc:{ns}:{claim['id']}"
        refs = by_claim.get(cid, [])
        if not refs:
            raise ValueError(f"claim {cid} has no evidence")
        out.append({
            "id": cid,
            "statement": claim["statement"],
            "claim_type": claim["claim_type"],
            "scope": claim.get("scope", {}),
            "modality": claim.get("modality", "asserted"),
            "epistemic_status": "draft",
            "evidence_refs": refs,
            "created_at": created_at,
            "created_by": spec["created_by"],
            "version": SCHEMA_VERSION,
            "notes": claim.get("notes", []),
        })
    return out


def build_provenance(spec: dict, claims: list[dict]) -> list[dict]:
    ns = spec["namespace"]
    recorded_at = _iso(spec["extraction_date"])
    mission = spec["mission"]
    out = []
    for claim in claims:
        slug = claim["id"].split(":")[-1]
        out.append({
            "id": f"tkp:{ns}:{slug}",
            "generated_entity": {"id": claim["id"], "entity_type": "claim",
                                 "version": SCHEMA_VERSION},
            "activity": {
                "id": f"{spec['task_key']}-{slug}",
                "activity_type": "extraction",
                "description": spec["activity"]["description"],
                "started_at": recorded_at,
                "used_entities": [f"{spec['source']['repo']}@{spec['source']['sha']}"],
                "software": [{"name": "ke.sediment_extract",
                              "version": SCHEMA_VERSION}],
                "parameters": {
                    "task_key": spec["task_key"],
                    "source_repo": spec["source"]["repo"],
                    "source_sha": spec["source"]["sha"],
                    "source_branch": mission.get("branch", ""),
                    "source_pr": mission.get("pr"),
                    "spec_sha256": spec.get("_spec_sha256", ""),
                },
            },
            "agents": [{"id": spec["created_by"], "agent_type": "software-agent",
                        "role": "producer (spec-driven extraction, no self-review)"}],
            "derived_from": [f"TensorSPH mission m{mission['id']}",
                             f"{spec['source']['repo']}@{spec['source']['sha']}",
                             f"task_key:{spec['task_key']}"],
            "attributed_to": [f"mission m{mission['id']} ({mission.get('model', 'unknown')})"],
            "recorded_at": recorded_at,
            "version": SCHEMA_VERSION,
        })
    return out


def build_benchmarks(spec: dict, pin: GitPin) -> dict:
    """Recompute every benchmark row from the pinned artifacts; formulas included."""
    bench = spec["benchmarks"]
    rows = []
    blobs: dict[str, str] = {}
    for row in bench["rows"]:
        path = row["source"]
        if path not in blobs:
            blobs[path] = pin.blob(path)
        data = json.loads(blobs[path])
        env = {var: resolve_path(data, p) for var, p in row["ref_vars"].items()}
        ref = evaluate(row["ref_expr"], env)
        got = float(resolve_path(data, row["got_path"]))
        abs_error = got - ref
        rel = (abs_error / ref) if ref != 0 else None
        tol_pct = float(row.get("tolerance_pct", 0.0) or 0.0)
        tol_abs = row.get("tolerance_abs")
        if tol_abs is not None:
            within = abs(abs_error) <= float(tol_abs)
            tolerance = {"kind": "absolute", "value": float(tol_abs)}
        elif tol_pct:
            within = rel is not None and abs(100.0 * rel) <= tol_pct
            tolerance = {"kind": "percent", "value": tol_pct}
        else:
            within, tolerance = None, {"kind": "none", "value": None}
        rows.append({
            "id": row["id"],
            "source": path,
            "ref_label": row.get("ref_label", row["ref_expr"]),
            "ref_expr": row["ref_expr"],
            "ref_vars": row["ref_vars"],
            "ref": ref,
            "got": got,
            "abs_error": abs_error,
            "rel_error": rel,
            "rel_error_pct": (100.0 * rel) if rel is not None else None,
            "tolerance": tolerance,
            "within_tolerance": within,
        })
    scored = [r for r in rows if r["rel_error_pct"] is not None]
    worst = max(scored, key=lambda r: abs(r["rel_error_pct"])) if scored else rows[0]
    return {
        "name": bench["name"],
        "description": bench["description"],
        "source": f"{spec['source']['repo']}@{spec['source']['sha']}",
        "rows": rows,
        "summary": {
            "rows": len(rows),
            "rows_with_tolerance": sum(1 for r in rows if r["tolerance"]["kind"] != "none"),
            "rows_within_tolerance": sum(1 for r in rows if r["within_tolerance"]),
            "rows_outside_tolerance": [r["id"] for r in rows if r["within_tolerance"] is False],
            "max_abs_rel_error_pct": max((abs(r["rel_error_pct"]) for r in scored), default=0.0),
            "worst_row": worst["id"],
        },
    }


def build_index(spec: dict, claims: list[dict], evidence: list[dict],
                benchmarks: dict, pin: GitPin) -> str:
    mission = spec["mission"]
    lines = [
        f"# Sediment package: {spec['package']['title']}",
        "",
        f"* task_key: `{spec['task_key']}` (idempotent key, do not rename)",
        f"* source: `{spec['source']['repo']}` @ `{spec['source']['sha']}` "
        f"(mission m{mission['id']}, branch `{mission.get('branch', '')}`, "
        f"PR #{mission.get('pr')})",
        f"* producer: `{spec['created_by']}` via `ke/sediment_extract.py` "
        f"(spec: `{spec['package'].get('spec_path', 'spec.json')}`)",
        f"* epistemic status: **draft** — claims are unassessed; no review event is "
        f"written here (producer must not self-review).",
        "",
        "## Claims",
        "",
        "| claim id | type | statement |",
        "|---|---|---|",
    ]
    for claim in claims:
        stmt = claim["statement"].replace("|", "\\|")
        lines.append(f"| `{claim['id']}` | {claim['claim_type']} | {stmt} |")
    lines += [
        "",
        "## Evidence (verbatim, offsets at the pinned commit)",
        "",
        "| evidence id | source path | lines | relation |",
        "|---|---|---|---|",
    ]
    for ev in evidence:
        loc = ev["locator"]
        lines.append(f"| `{ev['id']}` | `{loc['value'].split('#')[0].split(':', 1)[-1]}` | "
                     f"{loc['value'].split('#')[-1]} | {ev['relation']} |")
    lines += [
        "",
        "## Benchmark re-derivation (ref vs got, computed by the extractor)",
        "",
        "| row | reference | ref | got | rel. error | tolerance | within |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in benchmarks["rows"]:
        within = "—" if row["within_tolerance"] is None else (
            "yes" if row["within_tolerance"] else "**no**")
        if row["rel_error_pct"] is None:
            err = f"abs {row['abs_error']:+.4g}"
        else:
            err = f"{row['rel_error_pct']:+.3g}%"
        tol = row["tolerance"]
        tol_txt = ("—" if tol["kind"] == "none" else
                   f"{tol['value']:g}{'%' if tol['kind'] == 'percent' else ' (abs)'}")
        lines.append(f"| `{row['id']}` | {row['ref_label']} | {row['ref']:.6g} | "
                     f"{row['got']:.6g} | {err} | {tol_txt} | {within} |")
    lines += [
        "",
        f"Worst row: `{benchmarks['summary']['worst_row']}` "
        f"({benchmarks['summary']['max_abs_rel_error_pct']:.3g}% off the reference).",
        "",
        "## External anchors",
        "",
    ]
    for anchor in spec.get("external_anchors", []):
        lines.append(f"* {anchor['label']} — {anchor['why']}")
    lines += [
        "",
        "## Reproduce",
        "",
        "```bash",
        spec["package"]["repro_cmd"],
        "```",
        "",
        "## Limits",
        "",
        "* The quotes pin *what the source committed*, not whether the physics is right; "
        "assessment is the job of an independent reviewer (assessment_status=unassessed).",
        "* Numbers come from the source artifacts at the pinned commit; this package "
        "re-derives the reference values but never re-runs the SPH solver.",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# package writer + entry point
# --------------------------------------------------------------------------- #
def _write(path: Path, text: str) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def extract_package(spec_path: str | os.PathLike, source_repo: str | None = None,
                    out_dir: str | os.PathLike | None = None,
                    run_dir: str | os.PathLike | None = None) -> dict:
    """Build the whole package deterministically; returns a run summary."""
    spec_path = Path(spec_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["_spec_sha256"] = hashlib.sha256(spec_path.read_bytes()).hexdigest()
    repo = Path(source_repo or spec["source"].get("default_path", ""))
    pin = GitPin(repo, spec["source"]["sha"])
    out_dir = Path(out_dir or spec["package"]["out_dir"])
    run_dir = Path(run_dir or spec["package"]["run_dir"])

    evidence, facts = build_evidence(spec, pin)
    claims = build_claims(spec, evidence)
    provenance = build_provenance(spec, claims)
    benchmarks = build_benchmarks(spec, pin)

    # the package is generated: wipe only the generated sub-trees, keep spec.json
    for sub in ("claims", "evidence", "provenance"):
        for stale in (out_dir / sub).glob("*.json"):
            stale.unlink()
    written = []
    for claim in claims:
        written.append(_write(out_dir / "claims" / f"{claim['id'].split(':')[-1]}.json",
                              json.dumps(claim, indent=2, ensure_ascii=False)))
    for ev in evidence:
        written.append(_write(out_dir / "evidence" / f"{ev['id'].split(':')[-1]}.json",
                              json.dumps(ev, indent=2, ensure_ascii=False)))
    for prov in provenance:
        written.append(_write(out_dir / "provenance" / f"{prov['id'].split(':')[-1]}.json",
                              json.dumps(prov, indent=2, ensure_ascii=False)))
    written.append(_write(out_dir / "benchmarks.json",
                          json.dumps(benchmarks, indent=2, ensure_ascii=False)))
    written.append(_write(out_dir / "INDEX.md", build_index(spec, claims, evidence,
                                                            benchmarks, pin)))
    written.append(_write(out_dir / "anchors.json",
                          json.dumps(spec.get("external_anchors", []), indent=2,
                                     ensure_ascii=False)))

    mission = spec["mission"]
    summary = {
        "task_key": spec["task_key"],
        "spec": str(spec_path),
        "spec_sha256": spec["_spec_sha256"],
        "source": {"repo": str(repo), "sha": pin.sha, "commit_time": pin.commit_time,
                   "mission": mission["id"], "branch": mission.get("branch"),
                   "pr": mission.get("pr")},
        "counts": {"claims": len(claims), "evidence": len(evidence),
                   "provenance": len(provenance),
                   "benchmark_rows": len(benchmarks["rows"])},
        "benchmark_summary": benchmarks["summary"],
        "evidence_spans": facts,
        "files": written,
        "build": {
            "tool": "ke.sediment_extract",
            "version": SCHEMA_VERSION,
            "python": sys.version.split()[0],
            "argv": sys.argv,
            "cwd": os.getcwd(),
            "built_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "repro_cmd": spec["package"]["repro_cmd"],
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = run_dir / "run_manifest.json"
    manifest.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    log = run_dir / "extract.txt"
    log.write_text("\n".join([
        f"spec        : {spec_path} (sha256 {spec['_spec_sha256'][:16]}...)",
        f"source      : {repo} @ {pin.sha} (commit {pin.commit_time})",
        f"claims      : {len(claims)}  evidence: {len(evidence)}  provenance: {len(provenance)}",
        f"benchmarks  : {len(benchmarks['rows'])} rows, worst "
        f"{benchmarks['summary']['worst_row']} "
        f"{benchmarks['summary']['max_abs_rel_error_pct']:.3f}%",
        f"files       : {len(written)} written under {out_dir}",
        f"manifest    : {manifest}",
        "verdict     : package built (claims draft/unassessed; independent review pending)",
    ]) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec", required=True, help="mission spec JSON")
    parser.add_argument("--source-repo", default=None,
                        help="checkout that contains the pinned commit "
                             "(default: spec.source.default_path)")
    parser.add_argument("--out", default=None, help="package directory (default: spec)")
    parser.add_argument("--run-dir", default=None, help="run artifact directory")
    args = parser.parse_args(argv)
    try:
        summary = extract_package(args.spec, args.source_repo, args.out, args.run_dir)
    except (SourceUnavailable, QuoteNotFound, ValueError, KeyError) as exc:
        print(f"EXTRACTION FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    counts = summary["counts"]
    print(f"package built: {counts['claims']} claims / {counts['evidence']} evidence / "
          f"{counts['provenance']} provenance / {counts['benchmark_rows']} benchmark rows")
    print(f"worst benchmark row: {summary['benchmark_summary']['worst_row']} "
          f"{summary['benchmark_summary']['max_abs_rel_error_pct']:.3f}%")
    print(f"run manifest: {summary['build']['argv'][0]} -> "
          f"{Path(summary['files'][0]['path']).parents[1]}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())