#!/usr/bin/env python3
"""Independent verification + benchmark for ``knowledge/sediment/sloshing-impact-lbm``.

Runs without the source project's numerical stack: the source repository is used
only as a git object store, so every check is a *reading* of a pinned blob plus a
**re-derivation** by ``scripts/sloshing_reference.py``.  The verifier shares no
authority with the builder: it re-slices every quote itself, re-reads every
source number with its own regex plan (``number_checks.json`` is the plan, not a
result), and re-derives every number from the source artefacts.

Checks (each printed PASS/FAIL, exit code 1 on any failure):

  package:*        records present, JSON parseable, counts consistent
  schema:*         claim/evidence/provenance records vs ``schemas/*.schema.json``
  xref:*           claim.evidence_refs <-> evidence.claim_refs closure
  index:*          ``INDEX.md`` rows == the JSON records
  discipline:*     draft/unassessed, semver, no quote-less evidence
  quote:N          ``locator.quote`` == the blob slice at the locator's line range
  hash:N           ``locator.content_hash`` == sha256 of that slice
  grep:N           the claim's first quote line is found at the recorded line
  num:<id>         re-derived value vs source-recorded value within tolerance
  lit:<id>         every claim literal is a canonical rendering of ref/got
  bench:*          benchmark table complete (ref, got, relative error)

A missing python dependency (``jsonschema``) is reported as ``env:dependency =
FAIL`` with the install command instead of a traceback: it says nothing about the
package content, and the repository runner (``validate_sediment_packages.py``)
labels it ``blocked-missing-dependency`` rather than ``fail``.

Outputs (committed as run artefacts)::

    run/verification.json   all checks + environment + record hashes
    run/benchmark.json      ref-vs-got table with relative errors

Usage::

    SLOSHING_SRC_REPO=/root/tensor-ecosystem/TensorLBM \\
        python3 scripts/verify_sediment_sloshing.py
    # optional: --no-write to keep the committed artefacts untouched
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import sloshing_reference as REF  # noqa: E402
from sediment_lib import (  # noqa: E402
    Checks,
    DependencyError,
    GitSource,
    SchemaSet,
    canonical_renderings,
    check_discipline,
    check_index,
    check_xref,
    load_records,
    quote_of,
    quote_sha256,
    read_json,
    write_json,
)

PKG = ROOT / "knowledge" / "sediment" / "sloshing-impact-lbm"
SCHEMAS = ROOT / "schemas"
LOCATOR_RE = re.compile(
    r"^(?P<repo>[A-Za-z0-9_.-]+)@(?P<sha>[0-9a-f]{40}):(?P<path>[^#]+)#L(?P<first>\d+)-L(?P<last>\d+)$"
)


# ---------------------------------------------------------------------------
# argument / recipe resolution (verifier's own copy: no shared code path)
# ---------------------------------------------------------------------------
def resolve_args(args: dict, src: GitSource) -> dict:
    out = {}
    for key, value in args.items():
        if isinstance(value, dict) and "recipe" in value:
            out[key] = eval_recipe(value["recipe"], value["args"], src)
        elif isinstance(value, dict) and "series" in value:
            spec = value["series"]
            out[key] = src.json(spec["path"])[spec["key"]]
        elif isinstance(value, list):
            out[key] = tuple(value) if key == "band" else value
        else:
            out[key] = value
    return out


def eval_recipe(name: str, args: dict, src: GitSource) -> float:
    fn, _ = REF.RECIPES[name]
    return float(fn(**resolve_args(args, src)))


def source_value(item: dict, src: GitSource) -> float | None:
    spec = item.get("ref")
    if not spec:
        return None
    match = re.search(spec["regex"], src.blob(spec["path"]), re.S)
    if not match:
        raise ValueError(f"regex miss on {spec['path']}: {spec['regex']}")
    value = float(match.group(1))
    if spec.get("transform") == "percent_from_ratio":
        value = (value - 1.0) * 100.0
    return value


def rel_error(ref: float, got: float) -> float:
    if ref == 0.0:
        return 0.0 if got == 0.0 else float("inf")
    return (got - ref) / ref


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--package", default=str(PKG))
    ap.add_argument("--src-repo", default=None)
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    pkg = Path(args.package)
    manifest = read_json(pkg / "manifest.json")
    source = manifest["source"]
    src_root = Path(args.src_repo or os.environ.get(source["root_env"], source["default_root"]))
    sha = source["sha"]
    src = GitSource(src_root, sha)

    checks = Checks()
    checks.check("package:manifest", manifest.get("package") == "sloshing-impact-lbm",
                 f"{manifest.get('records')}")
    claims = load_records(pkg, "claim")
    evidences = load_records(pkg, "evidence")
    provenances = load_records(pkg, "provenance")
    checks.check("package:counts",
                 len(claims) == manifest["records"]["claims"]
                 and len(evidences) == manifest["records"]["evidence"]
                 and len(provenances) == manifest["records"]["provenance"],
                 f"{len(claims)}/{len(evidences)}/{len(provenances)}")

    # ---- schema / xref / index / discipline ------------------------------
    try:
        schemas = SchemaSet(SCHEMAS)
    except DependencyError as exc:
        # an environment problem is reported as such: it is *not* evidence that
        # the package content is wrong, and the repository runner classifies on
        # the ``env:dependency`` line rather than on the exit code alone
        checks.check("env:dependency", False, str(exc))
        return _finish(checks, pkg, args, {"benchmark": None}, src_root, sha, partial=True)
    for kind, records in (("claim", claims), ("evidence", evidences), ("provenance", provenances)):
        bad = [m for m in (schemas.validate(f"{kind}-record.schema.json", r) for r in records) if m]
        checks.check(f"schema:{kind}", not bad, bad[0] if bad else f"{len(records)} valid")
    check_xref(checks, claims, evidences)
    check_index(checks, pkg, claims, evidences)
    check_discipline(checks, claims, evidences)

    # ---- source availability -------------------------------------------
    if not src.available:
        checks.check("source:available", False,
                     f"{src_root} missing (set {source['root_env']}); quote/number checks NOT run")
        return _finish(checks, pkg, args, {"benchmark": None}, src_root, sha, partial=True)
    checks.check("source:available", True, str(src_root))

    # ---- quotes: verbatim slice + hash + grep line -----------------------
    quote_by_claim: dict[str, list[str]] = {}
    for ev in evidences:
        uri = ev["locator"]["value"]
        m = LOCATOR_RE.match(uri)
        if not m:
            checks.check(f"quote:{ev['id']}", False, f"bad locator {uri}")
            continue
        path, first, last = m.group("path"), int(m.group("first")), int(m.group("last"))
        lines = src.lines(path, m.group("sha"))
        slice_text = quote_of(lines, first, last)
        checks.check(f"quote:{ev['id']}", slice_text == ev["locator"]["quote"],
                     f"{path}#L{first}-L{last} ({len(slice_text)} chars)")
        checks.check(f"hash:{ev['id']}",
                     quote_sha256(slice_text) == ev["locator"]["content_hash"],
                     ev["locator"]["content_hash"][:16])
        needle = slice_text.split("\n")[0]
        hits = [ln for ln, _ in src.grep(path, needle, m.group("sha"))]
        checks.check(f"grep:{ev['id']}", first in hits, f"first line found at {hits[:3]}")
        for claim_id in ev.get("claim_refs", []):
            quote_by_claim.setdefault(claim_id, []).append(slice_text)

    # ---- number checks: re-derive and compare ---------------------------
    plan = read_json(pkg / "number_checks.json")
    statement_of = {c["id"]: c["statement"] for c in claims}
    bench_rows = []
    for item in plan["checks"]:
        try:
            ref_value = source_value(item, src)
            got_value = eval_recipe(item["recipe"], item["args"], src) if item["recipe"] else None
        except Exception as exc:  # a broken plan must fail loudly, not silently pass
            checks.check(f"num:{item['id']}", False, f"{type(exc).__name__}: {exc}")
            continue
        if got_value is not None and item.get("tol_rel") is not None:
            err = rel_error(ref_value, got_value)
            checks.check(f"num:{item['id']}", abs(err) <= item["tol_rel"],
                         f"ref={ref_value!r} got={got_value!r} rel={err:+.3e} tol={item['tol_rel']:.0e}")
        elif ref_value is None:
            checks.check(f"num:{item['id']}", got_value is not None,
                         f"derived-only got={got_value!r} (source reports no such value)")
        else:
            checks.check(f"num:{item['id']}", True,
                         f"reported-only ref={ref_value!r} (re-derivation not possible)")
        allowed = set()
        if ref_value is not None:
            allowed |= canonical_renderings(ref_value)
        if got_value is not None:
            allowed |= canonical_renderings(got_value)
        statement = statement_of.get(item["claim"], "")
        for literal in item["literals"]:
            checks.check(
                f"lit:{item['id']}:{literal}",
                literal in allowed and literal in statement,
                f"in-statement={literal in statement} rendering={literal in allowed}",
            )
        bench_rows.append(
            {
                "id": item["id"],
                "quantity": item["quantity"],
                "claim": item["claim"],
                "ref_source": item["ref"],
                "ref": ref_value,
                "got": got_value,
                "rel_error": (
                None if (got_value is None or ref_value is None)
                else rel_error(ref_value, got_value)
            ),
                "tol_rel": item.get("tol_rel"),
                "rederived": item["recipe"] is not None,
                "verdict": (
                    "derived-only" if ref_value is None
                    else "reported-only" if got_value is None
                    else "pass" if abs(rel_error(ref_value, got_value)) <= item["tol_rel"]
                    else "fail"
                ),
                "note": item.get("note", ""),
            }
        )

    rederived = [r for r in bench_rows if r["rederived"]]
    compared = [r for r in rederived if r["rel_error"] is not None]
    checks.check("bench:has-rederived", len(rederived) >= 10, f"{len(rederived)} items re-derived")
    checks.check("bench:has-numbers",
                 len(compared) >= 10 and all(r["got"] is not None for r in compared),
                 f"{len(bench_rows)} rows, {len(compared)} with ref and got")
    worst = max((abs(r["rel_error"]) for r in compared), default=0.0)
    checks.check("bench:worst-error", worst <= 5e-3, f"max |rel error| = {worst:.3e}")
    exact = [r for r in compared if abs(r["rel_error"]) <= 1e-9]
    checks.check("bench:exact-reproductions", len(exact) >= 10,
                 f"{len(exact)}/{len(rederived)} reproduce the source value to <=1e-9")

    benchmark = {
        "package": manifest["package"],
        "source": {"repo": source["repo"], "sha": sha},
        "n_items": len(bench_rows),
        "n_rederived": len(rederived),
        "n_compared": len(compared),
        "n_reported_only": len(bench_rows) - len(rederived),
        "worst_abs_rel_error": worst,
        "items": bench_rows,
    }
    return _finish(checks, pkg, args, {"benchmark": benchmark,
                                       "quotes": {k: len(v) for k, v in quote_by_claim.items()}},
                   src_root, sha, partial=False)


def _finish(checks: Checks, pkg: Path, args, extra: dict, src_root: Path, sha: str,
            partial: bool) -> int:
    print(checks.render())
    verification = {
        "package": "sloshing-impact-lbm",
        "source": {"sha": sha, "root": str(src_root)},
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.system(),
            "partial": partial,
        },
        "summary": checks.summary(),
        "checks": checks.items,
        "extra": extra,
    }
    if not args.no_write:
        write_json(Path(pkg) / "run" / "verification.json", verification)
        if extra.get("benchmark"):
            write_json(Path(pkg) / "run" / "benchmark.json", extra["benchmark"])
    return 0 if checks.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())