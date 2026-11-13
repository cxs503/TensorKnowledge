#!/usr/bin/env python3
"""Reusable core for sediment packages under ``knowledge/sediment/``.

A sediment package is a directory of four-contract records (claim / evidence /
provenance) plus:

  ``INDEX.md``         one row per claim: id, statement digest, locator, sha
  ``number_checks.json`` declarative plan: which numbers of which claim are
                        re-derived by which recipe from which source blob
  ``manifest.json``    package identity + the verifier entry that owns it

This module holds the parts that are *not* package specific, so that writers and
independent verifiers of different packages share the same discipline without
sharing a code path for the numbers:

  GitSource   read blobs at a pinned sha (``git -C repo show sha:path``)
  quotes      slice a line range out of a blob; hash it; emulate ``grep -nF``
  schemas     validate records against ``schemas/*.schema.json``
  xref        claim.evidence_refs <-> evidence.claim_refs closure
  index       render / parse / compare ``INDEX.md``
  Checks      PASS/FAIL accumulator that also serialises to JSON

Nothing here imports the source project: the source is a *record*, not a
dependency.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

__all__ = [
    "DependencyError",
    "GitSource",
    "quote_sha256",
    "SchemaSet",
    "Checks",
    "load_records",
    "check_xref",
    "index_rows",
    "render_index",
    "parse_index",
    "check_index",
    "check_discipline",
    "read_json",
    "write_json",
]

LOCATOR_RE = re.compile(
    r"^(?P<repo>[A-Za-z0-9_.-]+)@(?P<sha>[0-9a-f]{40}):(?P<path>[^#]+)#L(?P<first>\d+)-L(?P<last>\d+)$"
)


# ---------------------------------------------------------------------------
# source access
# ---------------------------------------------------------------------------
class GitSource:
    """Read-only view of a git repository at pinned shas."""

    def __init__(self, repo: Path | str, sha: str):
        self.repo = Path(repo)
        self.sha = sha
        self._lines: dict[str, list[str]] = {}

    @property
    def available(self) -> bool:
        return (self.repo / ".git").exists() or (self.repo / "HEAD").exists()

    def require(self) -> None:
        if not self.available:
            raise FileNotFoundError(f"source repository not available: {self.repo}")

    def blob(self, path: str, sha: str | None = None) -> str:
        self.require()
        proc = subprocess.run(
            ["git", "-C", str(self.repo), "show", f"{sha or self.sha}:{path}"],
            check=True,
            capture_output=True,
        )
        return proc.stdout.decode("utf-8")

    def lines(self, path: str, sha: str | None = None) -> list[str]:
        key = f"{sha or self.sha}:{path}"
        if key not in self._lines:
            self._lines[key] = self.blob(path, sha).split("\n")
        return self._lines[key]

    def json(self, path: str, sha: str | None = None):
        return json.loads(self.blob(path, sha))

    def grep(self, path: str, needle: str, sha: str | None = None) -> list[tuple[int, str]]:
        """Emulate ``git show sha:path | grep -nF <needle>`` (1-based, inclusive)."""
        return [(i, ln) for i, ln in enumerate(self.lines(path, sha), start=1) if needle in ln]


def quote_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def quote_of(lines: Sequence[str], first: int, last: int) -> str:
    """Verbatim slice, 1-based inclusive line numbers over a blob's lines."""
    return "\n".join(lines[first - 1:last])


# ---------------------------------------------------------------------------
# schema validation
# ---------------------------------------------------------------------------
class DependencyError(RuntimeError):
    """A python package the verifier needs is not installed in this interpreter.

    Raised instead of a bare ``ModuleNotFoundError`` so a caller can *report* the
    missing module (and the pinned requirements file) as an environment problem
    rather than let it look like a failed knowledge asset.
    """

    def __init__(self, module: str, detail: str = ""):
        self.module = module
        self.detail = detail or f"No module named '{module}'"
        super().__init__(
            f"missing python module '{module}' ({self.detail}); "
            "install requirements-validation.txt: python -m pip install -r requirements-validation.txt"
        )


class SchemaSet:
    """``schemas/*.schema.json`` loaded into a registry keyed by ``$id``."""

    def __init__(self, schema_dir: Path):
        try:
            import jsonschema
            from referencing import Registry, Resource
        except ImportError as exc:  # environment, not asset content
            raise DependencyError(getattr(exc, "name", None) or "jsonschema", str(exc)) from exc

        self._jsonschema = jsonschema
        self.docs: dict[str, dict] = {}
        registry = Registry()
        for path in sorted(Path(schema_dir).glob("*.schema.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            self.docs[path.name] = doc
            if "$id" in doc:
                registry = registry.with_resource(doc["$id"], Resource.from_contents(doc))
        self.registry = registry

    def validate(self, schema_file: str, record: dict) -> str:
        """Return ``""`` when valid, else a short error message."""
        validator = self._jsonschema.Draft202012Validator(
            self.docs[schema_file], registry=self.registry
        )
        try:
            validator.validate(record)
        except self._jsonschema.ValidationError as exc:
            return f"{record.get('id', '?')}: {exc.message[:160]}"
        return ""


SCHEMA_FOR_KIND = {
    "claim": "claim-record.schema.json",
    "evidence": "evidence-record.schema.json",
    "provenance": "provenance-record.schema.json",
}


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------
@dataclass
class Checks:
    """PASS/FAIL accumulator; ``ok`` is False as soon as one check fails."""

    items: list[dict] = field(default_factory=list)

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        self.items.append({"name": name, "ok": bool(ok), "detail": detail})
        return bool(ok)

    @property
    def failures(self) -> list[dict]:
        return [c for c in self.items if not c["ok"]]

    @property
    def ok(self) -> bool:
        return not self.failures

    def summary(self) -> dict:
        return {
            "n_checks": len(self.items),
            "n_pass": sum(1 for c in self.items if c["ok"]),
            "n_fail": len(self.failures),
            "failures": self.failures,
        }

    def render(self) -> str:
        width = max((len(c["name"]) for c in self.items), default=10)
        out = [f"{'PASS' if c['ok'] else 'FAIL'}  {c['name']:<{width}}  {c['detail']}" for c in self.items]
        s = self.summary()
        out.append(f"-- {s['n_pass']}/{s['n_checks']} checks pass")
        return "\n".join(out)


# ---------------------------------------------------------------------------
# records / package helpers
# ---------------------------------------------------------------------------
def canonical_renderings(value: float) -> set[str]:
    """Decimal renderings a claim statement may legitimately show for ``value``.

    A literal is only accepted if it is one of these forms of the *computed* value,
    so a truncated/rounded/typed-by-hand number cannot slip into a statement: the
    verifier re-formats and compares.
    """
    out = {str(value), repr(value), f"{value:.12g}", f"{value:.6g}"}
    for digits in (0, 1, 2, 3, 4, 5, 6):
        out.add(f"{value:.{digits}f}")
    for digits in (1, 2, 3, 4):
        out.add(f"{value:.{digits}e}")
    return out


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_records(pkg: Path, kind: str) -> list[dict]:
    """Records of one kind, either flat (``claim-*.json``) or in a subdirectory."""
    root = Path(pkg)
    paths = sorted(root.glob(f"{kind}-*.json")) or sorted((root / kind).glob("*.json"))
    return [read_json(p) for p in paths]


def check_xref(checks: Checks, claims: Sequence[dict], evidences: Sequence[dict]) -> None:
    """evidence_refs <-> claim_refs closure, both directions, plus id uniqueness."""
    claim_ids = [c["id"] for c in claims]
    ev_ids = [e["id"] for e in evidences]
    checks.check("xref:unique-claim-ids", len(set(claim_ids)) == len(claim_ids),
                 f"{len(claim_ids)} claims")
    checks.check("xref:unique-evidence-ids", len(set(ev_ids)) == len(ev_ids),
                 f"{len(ev_ids)} evidence records")
    dangling_c = [r for c in claims for r in c.get("evidence_refs", []) if r not in ev_ids]
    checks.check("xref:claim->evidence", not dangling_c, f"dangling={dangling_c}")
    dangling_e = [r for e in evidences for r in e.get("claim_refs", []) if r not in claim_ids]
    checks.check("xref:evidence->claim", not dangling_e, f"dangling={dangling_e}")
    unref = [i for i in ev_ids if not any(i in c.get("evidence_refs", []) for c in claims)]
    checks.check("xref:every-evidence-referenced", not unref, f"unreferenced={unref}")
    unreferenced_claims = [c["id"] for c in claims if not c.get("evidence_refs")]
    checks.check("xref:every-claim-has-evidence", not unreferenced_claims,
                 f"without evidence={unreferenced_claims}")


def index_rows(claims: Sequence[dict], evidences: Sequence[dict]) -> list[dict]:
    """One row per claim: id, statement digest, first locator, sha, #evidence."""
    ev_by_id = {e["id"]: e for e in evidences}
    rows = []
    for claim in claims:
        refs = [ev_by_id[r] for r in claim.get("evidence_refs", []) if r in ev_by_id]
        locator = refs[0]["locator"].get("value", "") if refs else ""
        digest = hashlib.sha256(claim["statement"].encode("utf-8")).hexdigest()[:16]
        rows.append(
            {
                "id": claim["id"],
                "digest": digest,
                "locator": locator,
                "sha": refs[0]["locator"].get("content_hash", "")[:16] if refs else "",
                "n_evidence": len(refs),
                "claim_type": claim.get("claim_type", ""),
            }
        )
    return sorted(rows, key=lambda row: row["id"])


def render_index(title: str, rows: Sequence[dict], footer: str = "") -> str:
    head = [
        f"# {title}",
        "",
        "| claim | type | statement digest | first locator | quote sha256 | evidence |",
        "|---|---|---|---|---|---|",
    ]
    body = [
        f"| `{r['id']}` | {r['claim_type']} | `{r['digest']}` | `{r['locator']}` | "
        f"`{r['sha']}` | {r['n_evidence']} |"
        for r in rows
    ]
    tail = [""]
    if footer:
        tail += [footer, ""]
    return "\n".join(head + body + tail)


def parse_index(text: str) -> list[dict]:
    """Parse the rows written by :func:`render_index` (tolerates extra prose)."""
    rows = []
    for line in text.splitlines():
        if not line.startswith("| `"):
            continue
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) != 6:
            continue
        rows.append(
            {
                "id": cells[0],
                "claim_type": cells[1],
                "digest": cells[2],
                "locator": cells[3],
                "sha": cells[4],
                "n_evidence": int(cells[5]),
            }
        )
    return rows


def check_index(checks: Checks, pkg: Path, claims: Sequence[dict], evidences: Sequence[dict]) -> None:
    text = (Path(pkg) / "INDEX.md").read_text(encoding="utf-8")
    parsed = parse_index(text)
    expected = index_rows(claims, evidences)
    checks.check("index:row-count", len(parsed) == len(expected),
                 f"parsed={len(parsed)} expected={len(expected)}")
    mismatch = [
        (p["id"], k) for p, e in zip(parsed, expected) for k in expected[0]
        if p.get(k) != e.get(k)
    ]
    checks.check("index:rows-match-json", not mismatch, f"mismatch={mismatch[:3]}")


def check_discipline(checks: Checks, claims: Sequence[dict], evidences: Sequence[dict]) -> None:
    """Producer discipline: draft/unassessed, no self-review, versioned records."""
    bad_status = [c["id"] for c in claims if c.get("epistemic_status") != "draft"]
    checks.check("discipline:claims-draft", not bad_status, f"non-draft={bad_status}")
    bad_assess = [e["id"] for e in evidences if e.get("assessment_status") != "unassessed"]
    checks.check("discipline:evidence-unassessed", not bad_assess, f"assessed={bad_assess}")
    bad_version = [r["id"] for r in list(claims) + list(evidences)
                   if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", str(r.get("version", "")))]
    checks.check("discipline:semver", not bad_version, f"bad={bad_version}")
    no_quote = [e["id"] for e in evidences if not e.get("locator", {}).get("quote")]
    checks.check("discipline:evidence-has-quote", not no_quote, f"without quote={no_quote}")


def iter_packages(root: Path) -> Iterable[Path]:
    for manifest in sorted(Path(root).glob("*/manifest.json")):
        yield manifest.parent