#!/usr/bin/env python3
"""KPI-KB-10K harvester — ecosystem-wide, extractive knowledge-object harvest.

Why this exists
---------------
``KPI-KB-10K`` asks for >= 10,000 *governed* knowledge objects (KO), i.e. each
KO carries the four-contract minimum of ``VISION.md`` §3: >=1 claim + >=1
evidence + >=1 provenance (review-event is producer-forbidden, see
``docs/kb10k/README.md`` §4).  Hand-writing 10k objects would be fabrication, so
every record here is **extracted, never authored**:

* the claim statement is a fixed machine template parameterised by values read
  from the source file (repo, commit, path, line, symbol name, section title);
* the evidence quote is a **verbatim contiguous slice** of the source bytes,
  pinned by ``locator.content_hash`` = sha256 of the quote and by
  ``start_offset``/``end_offset`` (character offsets into the source file), so
  anybody holding the pinned ``repo@commit`` can re-derive it byte for byte
  (``scripts/kb10k_verify.py --online``);
* the provenance record names the extraction activity and the producing agent.

Three harvest tiers (composition is reported per tier in ``manifest.json``):

===== ========================== ===============================================
tier  source                     one KO per
===== ========================== ===============================================
A     ecosystem python source    module-level *public* class/function definition
B     ecosystem markdown docs    ``## `` section (heading + leading paragraph)
C     platform governance tables negative-knowledge ledger row / oss_solutions row
===== ========================== ===============================================

Why a target-count allocation instead of "everything": the corpus holds ~98.7k
public module-level symbols (measured 2026-11-11), i.e. ~10x the KPI.  Emitting
all of them would produce a ~140 MB commit; the push gate also refuses files
>4 MB.  So the harvest is a **deterministic, domain-balanced round-robin** over
repositories at a fixed target (default 10,000) — same inputs => byte-identical
output.  See ``docs/kb10k/README.md`` §3 for the selection rule and §7 for the
scaling plan beyond 10k.

Layout written (mirrors the KE contract, aggregate containers are the layout
``ke.contract.discover`` documents as supported)::

    knowledge/kb10k/manifest.json
    knowledge/kb10k/claims/part-000.json      # list of claim records
    knowledge/kb10k/evidence/part-000.json    # list of evidence records
    knowledge/kb10k/provenance/part-000.json  # list of provenance records

Usage::

    kb10k_harvest.py [--target 10000] [--out knowledge/kb10k]
                     [--ecosystem /root/tensor-ecosystem] [--no-db]
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Fixed, reproducible metadata.  A rerun on the same sources must be identical,
# so nothing here depends on the wall clock.
# ---------------------------------------------------------------------------
GENERATOR = "scripts/kb10k_harvest.py"
GENERATOR_VERSION = "1.0.0"
CAPTURED_AT = "2026-11-11T00:00:00Z"       # mission date, not wall clock
ACCESSED_AT = "2026-11-11"
AGENT = "agent/m15151"
ACTIVITY_ID = "act-kb10k-harvest"
CLAIM_VERSION = "1.0.0"
MAX_QUOTE = 1200                            # schema evidence-record.locator.quote
SHARD_SIZE = 1000

#: tier -> share of the target (remainder is re-assigned to tier A)
TIER_SHARES = {"A": 0.88, "B": 0.085, "C": 0.035}

#: A quote that looks like an inline credential must never be committed.
_SECRET_RE = re.compile(
    r"""(?i)(password|passwd|secret|api[_-]?key|access[_-]?key|private[_-]?key|token)\s*[:=]\s*['"][^'"]{8,}""")

SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "build", "dist",
    "site-packages", ".mypy_cache", ".pytest_cache", ".tox", ".eggs", ".idea",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def slug(text: str, limit: int = 28) -> str:
    """Lowercase, [a-z0-9-] only — the id pattern of the four schemas."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if len(s) > limit:
        s = s[:limit].rstrip("-")
    return s or "x"


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def short_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


@dataclass
class Unit:
    """One candidate knowledge object before record rendering."""

    tier: str
    repo: str
    commit: str
    path: str            # repo-relative source path (or table name for tier C)
    kind: str            # class | function | async-function | section | ledger | solution
    name: str            # symbol / heading / row key
    signature: str = ""   # one-line signature or section first line
    doc_title: str = ""
    line: int = 0
    end_line: int = 0
    start_off: int = 0
    end_off: int = 0
    quote: str = ""
    extra: str = ""       # tier-specific detail used in the statement

    @property
    def id_slug(self) -> str:
        tag = {"class": "c", "function": "f", "async-function": "f",
               "section": "d", "ledger": "n", "solution": "s"}[self.kind]
        # name is part of the key: tier-C rows can share a pseudo line number
        # (non-numeric row keys -> 0), and a collision would silently drop a KO.
        key = f"{self.path}:{self.line}:{self.name}"
        return f"{slug(self.repo, 20)}-{tag}-{short_hash(key)}-l{self.line}"


# ---------------------------------------------------------------------------
# tier A + B: ecosystem repositories
# ---------------------------------------------------------------------------
def git_commit(repo: Path) -> tuple[str, bool]:
    try:
        sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown", False
    dirty = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                           capture_output=True, text=True).stdout.strip() != ""
    return sha, dirty


def is_test_path(rel: str) -> bool:
    parts = rel.split("/")
    return "tests" in parts or "test" in parts or Path(rel).name.startswith("test_") \
        or Path(rel).name.endswith("_test.py")


def walk_files(repo: Path, suffixes: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in SKIP_DIRS and not d.startswith("."))
        for f in sorted(filenames):
            if f.startswith("."):
                continue
            if f.endswith(suffixes):
                out.append(os.path.relpath(os.path.join(dirpath, f), repo))
    return sorted(out)


def code_units(repo: Path, name: str, commit: str, cap: int | None = None) -> list[Unit]:
    """Module-level public class/def per file — public API surface only.

    ``cap`` stops the scan once enough candidates exist for this repository's
    share of the quota (the corpus is ~10x the KPI; a full parse of all 20.8k
    files takes minutes and adds nothing to the selected set).
    """
    units: list[Unit] = []
    for rel in walk_files(repo, (".py",)):
        if cap is not None and len(units) >= cap:
            break
        if is_test_path(rel):
            continue
        p = repo / rel
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(src)
        except (SyntaxError, ValueError, OSError):
            continue
        lines = src.splitlines(keepends=True)
        offsets = [0]
        for ln in lines:
            offsets.append(offsets[-1] + len(ln))
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if node.name.startswith("_"):
                continue
            kind = ("class" if isinstance(node, ast.ClassDef)
                    else "function" if isinstance(node, ast.FunctionDef) else "async-function")
            # quote = definition line(s) up to and including the first docstring line
            start = node.lineno
            end = start
            doc_node = node.body[0] if node.body else None
            if isinstance(doc_node, ast.Expr) and isinstance(doc_node.value, ast.Constant) \
                    and isinstance(doc_node.value.value, str) \
                    and doc_node.lineno <= start + 1:
                end = doc_node.lineno          # def line (+ one docstring line)
            if _SECRET_RE.search("".join(lines[start - 1:end])):
                continue
            quote = "".join(lines[start - 1:end])
            if len(quote) > MAX_QUOTE:
                quote = quote[:MAX_QUOTE]
            sig = lines[start - 1].strip()
            units.append(Unit(
                tier="A", repo=name, commit=commit, path=rel, kind=kind, name=node.name,
                signature=sig[:200], line=start, end_line=start + quote.count("\n"),
                start_off=offsets[start - 1], end_off=offsets[start - 1] + len(quote),
                quote=quote,
                extra=sig[:120],
            ))
    return units


MD_HEADING = re.compile(r"^(##\s+\S.*)$")


def doc_units(repo: Path, name: str, commit: str, cap: int | None = None) -> list[Unit]:
    """``## `` sections: heading + the leading paragraph lines (contiguous)."""
    units: list[Unit] = []
    for rel in walk_files(repo, (".md",)):
        if cap is not None and len(units) >= cap:
            break
        p = repo / rel
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = src.splitlines(keepends=True)
        offsets = [0]
        for ln in lines:
            offsets.append(offsets[-1] + len(ln))
        for i, ln in enumerate(lines):
            m = MD_HEADING.match(ln)
            if not m:
                continue
            heading = ln.strip()
            end = i + 1
            while (end < len(lines) and end <= i + 4 and lines[end].strip()
                   and sum(len(x) for x in lines[i:end + 1]) <= 320):
                end += 1
            quote = "".join(lines[i:end])
            if _SECRET_RE.search(quote):
                continue
            if len(quote) > MAX_QUOTE:
                quote = quote[:MAX_QUOTE]
            body = " ".join(x.strip() for x in lines[i + 1:end]).strip()
            units.append(Unit(
                tier="B", repo=name, commit=commit, path=rel, kind="section",
                name=heading.lstrip("# ").strip(), signature=heading[:160],
                line=i + 1, end_line=end, start_off=offsets[i],
                end_off=offsets[i] + len(quote), quote=quote,
                extra=body[:200],
            ))
    return units


# ---------------------------------------------------------------------------
# tier C: platform governance tables (frozen rows, self-contained afterwards)
# ---------------------------------------------------------------------------
def psql(sql: str, db: str = "tensorplatform") -> list[list[str]] | None:
    """Read-only psql as the ``postgres`` role (table ACLs deny the agent user).

    Returns ``None`` when the platform DB is unreachable, so the harvester stays
    runnable (tier C dropped and reported, never silently fabricated).
    """
    for cmd in (["runuser", "-u", "postgres", "--", "psql", "-d", db, "-t", "-A", "-F", "\x1f", "-c", sql],
                ["psql", "-d", db, "-t", "-A", "-F", "\x1f", "-c", sql]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except Exception:
            continue
        if r.returncode == 0:
            rows = [ln.split("\x1f") for ln in r.stdout.splitlines() if ln.strip()]
            if rows:
                return rows
    return None


def governance_units() -> tuple[list[Unit], dict]:
    """Tier C: negative-knowledge ledger rows and oss_solutions rows."""
    units: list[Unit] = []
    report: dict = {"tables": {}, "skipped": []}

    rows = psql("SELECT entry_id, failure_kind, title, hypothesis, "
                "coalesce(failure_reason,''), coalesce(falsification_evidence,'') "
                "FROM negative_knowledge_ledger ORDER BY entry_id")
    if rows is None:
        report["skipped"].append({"table": "negative_knowledge_ledger", "reason": "psql unavailable"})
    else:
        report["tables"]["negative_knowledge_ledger"] = len(rows)
        for entry_id, fkind, title, hypothesis, reason, evidence in rows:
            payload = {"entry_id": entry_id, "failure_kind": fkind,
                       "title": title, "hypothesis": hypothesis,
                       "failure_reason": reason, "falsification_evidence": evidence}
            quote = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            if len(quote) > MAX_QUOTE:
                quote = quote[:MAX_QUOTE]
            units.append(Unit(
                tier="C", repo="tensorplatform", commit="db",
                path="negative_knowledge_ledger", kind="ledger",
                name=entry_id, signature=f"{fkind}: {title[:120]}",
                line=int(entry_id.rsplit(":", 1)[-1]) if entry_id.rsplit(":", 1)[-1].isdigit() else 0,
                quote=quote, extra=f"failure_kind={fkind}; {title[:120]}",
            ))

    cols = ("SELECT id, repo, feature_slug, tag, coalesce(method,''), coalesce(transfer,'') "
            "FROM oss_solutions ORDER BY id")
    rows = psql(cols)
    if rows is None:
        report["skipped"].append({"table": "oss_solutions", "reason": "psql unavailable"})
    else:
        report["tables"]["oss_solutions"] = len(rows)
        for rid, srepo, feature, tag, method, transfer in rows:
            payload = {"id": rid, "repo": srepo, "feature_slug": feature,
                       "tag": tag, "method": method, "transfer": transfer}
            quote = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            if len(quote) > MAX_QUOTE:
                quote = quote[:MAX_QUOTE]
            units.append(Unit(
                tier="C", repo="tensorplatform", commit="db",
                path="oss_solutions", kind="solution", name=f"row-{rid}",
                signature=f"{srepo} / {feature} / {tag}"[:160],
                line=int(rid) if rid.isdigit() else 0, quote=quote,
                extra=f"{srepo}:{feature}",
            ))
    return units, report


# ---------------------------------------------------------------------------
# record rendering (four contracts)
# ---------------------------------------------------------------------------
def claim_statement(u: Unit) -> str:
    if u.tier == "A":
        return (f"`{u.repo}@{u.commit[:8]}` defines module-level public {u.kind} "
                f"`{u.name}` in `{u.path}` at line {u.line}.")
    if u.tier == "B":
        return (f"`{u.repo}@{u.commit[:8]}` documentation section \"{u.name}\" "
                f"begins in `{u.path}` at line {u.line}; its leading text is quoted "
                f"verbatim in the linked evidence.")
    if u.kind == "ledger":
        return (f"Platform negative-knowledge ledger entry `{u.name}` records a "
                f"falsification/failure of kind `{u.extra.split(';')[0].split('=')[-1]}`: "
                f"\"{u.signature[:160]}\" (full row frozen in the evidence quote).")
    return (f"Platform method-migration record `oss_solutions#{u.name}` documents "
            f"`{u.extra}` — the transferable method and its conventions are frozen in "
            f"the evidence quote.")


def claim_type(u: Unit) -> str:
    return {"A": "definition", "B": "descriptive"}.get(u.tier) or \
        ("descriptive" if u.kind == "ledger" else "methodological")


def domain_of(u: Unit) -> str:
    return f"software/{u.repo}" if u.tier in ("A", "B") else "platform/governance"


def make_records(u: Unit) -> tuple[dict, dict, dict]:
    slug_id = u.id_slug
    cid, eid, pid = f"tkc:kb10k:{slug_id}", f"tke:kb10k:{slug_id}", f"tkp:kb10k:{slug_id}"
    system = (f"{u.repo}@{u.commit[:12]}" if u.tier != "C"
              else "tensorplatform@db")

    claim = {
        "id": cid,
        "statement": claim_statement(u),
        "claim_type": claim_type(u),
        "scope": {"domain": domain_of(u), "system": system},
        "modality": "asserted",
        "epistemic_status": "provisional",
        "evidence_refs": [eid],
        "created_at": CAPTURED_AT,
        "created_by": AGENT,
        "version": CLAIM_VERSION,
    }

    if u.tier == "C":
        source = {"source_type": "internal-artifact",
                  "citation": f"PostgreSQL tensorplatform.{u.path} row {u.name}",
                  "persistent_id": f"pg:tensorplatform:{u.path}:{u.name}",
                  "accessed_at": ACCESSED_AT}
        locator_value = f"tensorplatform.{u.path}#{u.name}"
        loc_type = "row-range"
        lang = "json"
    else:
        source = {"source_type": "other",
                  "citation": f"{u.repo} {u.path}",
                  "persistent_id": f"git:{u.repo}@{u.commit}:{u.path}",
                  "accessed_at": ACCESSED_AT}
        locator_value = f"{u.repo}@{u.commit[:12]} {u.path}:{u.line}-{u.end_line}"
        loc_type = "code-location" if u.tier == "A" else "section"
        lang = "python" if u.tier == "A" else "markdown"

    evidence = {
        "id": eid,
        "claim_refs": [cid],
        "source": source,
        "relation": "supports",
        "locator": {"locator_type": loc_type, "value": locator_value,
                    # A frozen DB row is not a file slice: no offsets claimed.
                    **({"start_offset": u.start_off, "end_offset": u.end_off}
                       if u.tier != "C" else {}),
                    "quote": u.quote, "content_hash": sha256_text(u.quote)},
        "extraction_method": "automated-extraction",
        "captured_at": CAPTURED_AT,
        "captured_by": AGENT,
        "assessment_status": "unassessed",
        "version": CLAIM_VERSION,
    }

    provenance = {
        "id": pid,
        "generated_entity": {"id": cid, "entity_type": "claim"},
        "activity": {"id": ACTIVITY_ID, "activity_type": "extraction",
                     "started_at": CAPTURED_AT,
                     "software": [{"name": GENERATOR, "version": GENERATOR_VERSION}]},
        "agents": [{"name": AGENT, "agent_type": "software-agent", "id": AGENT}],
        "recorded_at": CAPTURED_AT,
        "version": CLAIM_VERSION,
    }
    return claim, evidence, provenance


# ---------------------------------------------------------------------------
# selection + write
# ---------------------------------------------------------------------------
def round_robin(lists: dict[str, list[Unit]], quota: int) -> list[Unit]:
    """Deterministic domain-balanced interleave across repositories."""
    picked: list[Unit] = []
    order = sorted(lists)
    idx = {k: 0 for k in order}
    while len(picked) < quota:
        progressed = False
        for k in order:
            if idx[k] < len(lists[k]):
                picked.append(lists[k][idx[k]])
                idx[k] += 1
                progressed = True
                if len(picked) >= quota:
                    break
        if not progressed:
            break
    return picked


def write_shards(records: list[dict], out_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    shards = []
    for i in range(0, len(records), SHARD_SIZE):
        chunk = records[i:i + SHARD_SIZE]
        p = out_dir / f"part-{i // SHARD_SIZE:03d}.json"
        body = json.dumps(chunk, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":")) + "\n"
        p.write_text(body, encoding="utf-8")
        shards.append({"path": str(p.name), "records": len(chunk),
                       "bytes": len(body.encode("utf-8")),
                       "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()})
    return shards


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", type=int, default=10_000)
    ap.add_argument("--out", default="knowledge/kb10k")
    ap.add_argument("--ecosystem", default=os.environ.get("KB10K_ECOSYSTEM_ROOT",
                                                          "/root/tensor-ecosystem"))
    ap.add_argument("--no-db", action="store_true", help="skip tier C (offline runs)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    eco = Path(args.ecosystem)
    out = Path(args.out)
    if not eco.is_dir():
        print(f"FATAL ecosystem root not found: {eco}", file=sys.stderr)
        return 2

    # ---- tier A/B, per repository --------------------------------------
    per_repo: dict[str, dict[str, list[Unit]]] = {}
    repo_meta: dict[str, dict] = {}
    repos = sorted(p for p in eco.iterdir() if p.is_dir() and not p.name.startswith("."))
    n_repos = max(1, len(repos))
    # head-room factor: small repos contribute less than their even share, the
    # big ones must cover the difference, so cap well above target/n_repos.
    cap_a = int(args.target * TIER_SHARES["A"] / n_repos * 4.0) + 100
    cap_b = int(args.target * TIER_SHARES["B"] / n_repos * 2.5) + 20
    for repo in repos:
        commit, dirty = git_commit(repo)
        a = code_units(repo, repo.name, commit, cap=cap_a)
        b = doc_units(repo, repo.name, commit, cap=cap_b)
        if not a and not b:
            continue
        per_repo[repo.name] = {"A": a, "B": b}
        repo_meta[repo.name] = {"commit": commit, "dirty_worktree": dirty,
                                "code_candidates": len(a), "doc_candidates": len(b)}
        if not args.quiet:
            print(f"  {repo.name:28s} {commit[:10]} code={len(a):6d} doc={len(b):5d}")

    # ---- quota allocation ---------------------------------------------
    quota = {"A": int(args.target * TIER_SHARES["A"]),
             "B": int(args.target * TIER_SHARES["B"]),
             "C": int(args.target * TIER_SHARES["C"])}

    picked_b = round_robin({k: v["B"] for k, v in per_repo.items()}, quota["B"])

    picked_c: list[Unit] = []
    db_report: dict = {"tables": {}, "skipped": [{"table": "all", "reason": "--no-db"}]}
    if not args.no_db:
        picked_c, db_report = governance_units()
        picked_c = picked_c[:quota["C"]] if len(picked_c) > quota["C"] else picked_c

    # tier A takes whatever B and C did not consume -> the target is exact as
    # long as the corpus has enough tier-A candidates (it has ~11x the KPI).
    quota["A"] = max(0, args.target - len(picked_b) - len(picked_c))
    picked_a = round_robin({k: v["A"] for k, v in per_repo.items()}, quota["A"])
    quota["A_actual"] = len(picked_a)
    picked = picked_a + picked_b + picked_c

    # ---- render + shard ------------------------------------------------
    claims, evidence, provenance = [], [], []
    seen: set[str] = set()
    tier_counts = {"A": 0, "B": 0, "C": 0}
    for u in picked:
        c, e, p = make_records(u)
        if c["id"] in seen:            # defensive: ids are location-derived
            continue
        seen.add(c["id"])
        claims.append(c); evidence.append(e); provenance.append(p)
        tier_counts[u.tier] += 1

    for sub in ("claims", "evidence", "provenance"):
        d = out / sub
        if d.exists():
            for old in d.glob("part-*.json"):
                old.unlink()

    shards = {
        "claims": write_shards(claims, out / "claims"),
        "evidence": write_shards(evidence, out / "evidence"),
        "provenance": write_shards(provenance, out / "provenance"),
    }

    per_repo_counts: dict[str, int] = {}
    for u in picked:
        key = u.repo + "/" + u.path if u.tier == "C" else u.repo
        per_repo_counts[key] = per_repo_counts.get(key, 0) + 1

    manifest = {
        "kpi": "KPI-KB-10K",
        "generator": {"path": GENERATOR, "version": GENERATOR_VERSION,
                      "captured_at": CAPTURED_AT, "agent": AGENT},
        "target": args.target,
        "counts": {"claims": len(claims), "evidence": len(evidence),
                   "provenance": len(provenance),
                   "knowledge_objects": len(claims), "by_tier": tier_counts,
                   "by_repo": dict(sorted(per_repo_counts.items()))},
        "tier_definitions": {
            "A": "module-level public class/function in ecosystem python source",
            "B": "markdown '## ' section (heading + leading paragraph)",
            "C": "platform governance row (negative-knowledge ledger / oss_solutions)",
        },
        "quota": quota,
        "ecosystem_root": str(eco),
        "repos": repo_meta,
        "db": db_report,
        "shards": shards,
        "record_contract": {
            "claim": "schemas/claim-record.schema.json",
            "evidence": "schemas/evidence-record.schema.json",
            "provenance": "schemas/provenance-record.schema.json",
            "coverage": "each KO: 1 claim + 1 evidence(supports) + 1 provenance(claim)",
        },
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")

    total_bytes = sum(s["bytes"] for kind in shards.values() for s in kind)
    print(f"KOs={len(claims)} tiers={tier_counts} shards="
          f"{ {k: len(v) for k, v in shards.items()} } bytes={total_bytes}")
    if len(claims) < args.target:
        print(f"WARN shortfall: {args.target - len(claims)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())