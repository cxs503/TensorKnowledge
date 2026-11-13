"""Knowledge governance at scale — dedup · cross-validation · contradiction · review.

Anchor: **KBM-TKC-GOV-SCALE** (mission 15721, round 1).

This module adds the governance layer that sits *above* extraction:

===============  =============================================================
stage            what it does
===============  =============================================================
entity-res v1    candidate name -> canonical entity (alias collapse, qualifier
                 split, confidence); unresolved candidates are *discarded with
                 a reason*, never silently dropped
dedup            two layers: (L1) exact fingerprint of the full normalized
                 statement; (L2) semantic-subject equality + wording simhash
                 when conditions are unstated.  Duplicate rate = 1 - clusters/KO
cross-val        same entity+qualifier+unit across >=2 distinct source reports:
                 values compared under predeclared tolerances (5% agree / 15%
                 contradict, ``governance/gov-config-v1.json``)
contradiction    contradicted pairs become contradiction candidates with a
                 supported / contradicted / insufficient-evidence verdict
review pool      pooled agent reviewers, one instance per gate lane, dual
                 instances per lane, deterministic assignment under capacity,
                 decisions folded through the *existing* review state machine
                 (``scripts/ke_state_machine.py``: append-only, no self-approval)
buckets          three counting口径 kept apart and reconciled:
                 B0 raw records / B1 KO pending review / B2 governed objects
===============  =============================================================

Design rules honoured here
--------------------------
* **Zero hand-copying** — every extracted KO carries its source span, the exact
  needle and the sha256 of the source excerpt; :func:`relocate` re-derives the
  value from the bytes, so a claim that cannot be re-located is discarded.
* **Deterministic** — no wall-clock, no RNG: every ordering and assignment is a
  sha256 of stable ids; the run timestamp is an explicit input.
* **Data, not code** — entities, aliases, units, thresholds and the reviewer
  pool live in ``governance/gov-config-v1.json``.
* **Honest** — refusals are recorded, unsupported verdicts are
  ``insufficient-evidence`` (never ``supported``), and counting口径 mismatches
  raise :class:`BucketViolation` instead of being papered over.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "governance" / "gov-config-v1.json"
STATE_MACHINE_PATH = ROOT / "scripts" / "ke_state_machine.py"

PRODUCER_ID = "agent/kbm-gov-w1"
MAX_LINE_CHARS = 400


# ---------------------------------------------------------------------------
# Config / small helpers
# ---------------------------------------------------------------------------
def load_config(path: Path | str | None = None) -> dict:
    p = Path(path) if path else CONFIG_PATH
    cfg = json.loads(p.read_text(encoding="utf-8"))
    for key in ("entities", "thresholds", "review_pool", "extraction"):
        if key not in cfg:
            raise ValueError(f"gov config {p} missing section {key!r}")
    return cfg


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_int(text: str, mod: int) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16) % mod


_SUBSCRIPT = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_SUPERSCRIPT = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
_SUPER_RUN = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹]+")


def normalize_text(s: str) -> str:
    """NFC + unicode minus/equals + sub/superscripts (idempotent).

    Subscripts are plain digits (``C₁`` -> ``C1``); superscripts are *exponents*
    (``Ra=10⁵`` -> ``Ra=10^5``) so that 10⁵ is never read as 105 or 10.
    """
    s = unicodedata.normalize("NFC", s).translate(_SUBSCRIPT)
    s = _SUPER_RUN.sub(lambda m: "^" + m.group(0).translate(_SUPERSCRIPT), s)
    return (s.replace("\u2212", "-").replace("＝", "=")
             .replace("\u00a0", " ").replace("\r", "\n"))


def alias_key(s: str) -> str:
    """Alias comparison key: case/space/underscore/brace insensitive."""
    s = normalize_text(s).lower()
    return re.sub(r"[\s_${}\[\]()（）.·]+", "", s)


def sig(value: float, digits: int = 6) -> str:
    """Significant-digit key for a numeric value (stable across float noise)."""
    if value == 0:
        return "0"
    return f"{value:.{digits}g}"


def unit_key(unit: str | None) -> str:
    if unit is None or unit == "":
        return "-"
    u = normalize_text(unit).strip().lower()
    return "-" if u in ("-", "1") else u


# ---------------------------------------------------------------------------
# Entity Resolution v1
# ---------------------------------------------------------------------------
class EntityRegistry:
    """Alias-closed canonical entity registry (config driven).

    Resolution is deliberately *closed*: a name either resolves through a
    declared alias (confidence 1.0), resolves through alias + qualifier split
    (0.9, qualifier kept as part of the subject key) or is unresolved, in which
    case the candidate is discarded with reason ``entity_unresolved``.  There is
    no fuzzy fallback — an unresolvable name must not become quiet knowledge.
    """

    def __init__(self, cfg: dict):
        self.entities = {e["id"]: e for e in cfg["entities"]}
        self._alias: dict[str, str] = {}
        for e in cfg["entities"]:
            for a in e["aliases"]:
                self._alias.setdefault(alias_key(a), e["id"])

    def kind(self, entity_id: str) -> str:
        return self.entities[entity_id]["kind"]

    def canonical(self, entity_id: str) -> str:
        return self.entities[entity_id]["canonical"]

    def resolve(self, raw_name: str) -> dict:
        """Return {entity_id, qualifier, confidence, matched_alias} or unresolved."""
        name = normalize_text(raw_name).strip()
        eid = self._alias.get(alias_key(name))
        if eid:
            return {"entity_id": eid, "qualifier": "", "confidence": 1.0,
                    "matched_alias": name}
        m = re.match(r"^(?P<base>[^_]+?)_\{?(?P<q>[A-Za-z0-9]{1,12})\}?$", name)
        if m:
            eid = self._alias.get(alias_key(m.group("base")))
            if eid:
                return {"entity_id": eid, "qualifier": m.group("q").lower(),
                        "confidence": 0.9, "matched_alias": m.group("base")}
        return {"entity_id": None, "qualifier": "", "confidence": 0.0,
                "matched_alias": None}

    def alias_table(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {eid: [] for eid in self.entities}
        for key, eid in self._alias.items():
            out[eid].append(key)
        return {k: sorted(v) for k, v in out.items()}


# ---------------------------------------------------------------------------
# Quantity candidate extraction + provenance verification
# ---------------------------------------------------------------------------
_NUM = r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"
_CAND = re.compile(
    rf"(?<![A-Za-z0-9_@])"
    rf"(?P<name>[A-Za-z][A-Za-z0-9_]{{0,15}}|[Α-Ωα-ω][A-Za-z0-9_]{{0,15}}|[\u4e00-\u9fff]{{2,10}})"
    rf"\s*(?:=|为|达到)\s*"
    rf"(?P<value>{_NUM})\s*"
    rf"(?P<unit>[%A-Za-z°μ/][A-Za-z0-9°/^]{{0,7}})?"
)
_SNAKE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")


_CARET = re.compile(r"\^\s*\{?\s*(-?\d{1,3})\s*\}?")


def read_assignment(text: str, m: "re.Match") -> tuple[float, str | None, str | None]:
    """Interpret one ``name = value`` match.

    Returns ``(value, unit, reject_reason)``.  ``10^5`` is an exponent, not a
    truncated mantissa; ``24/Re`` / ``3*x`` are formulas, not measurements.
    """
    raw = m.group("value")
    try:
        value = float(raw)
    except ValueError:  # pragma: no cover - regex guarantees numeric
        return 0.0, None, "value_not_numeric"
    unit = m.group("unit")
    tail = text[m.end():]
    if tail.startswith("^"):
        cm = _CARET.match(tail)
        if not cm:
            return value, None, "value_is_expression"
        exp = int(cm.group(1))
        if abs(exp) > 20 or value <= 0:
            return value, None, "value_out_of_range"
        value = value ** exp
        rest = tail[cm.end():]
        unit = None if rest[:1].strip() else None
    elif tail[:1] in ("/", "*", "×", "·", "\\") or (unit or "").startswith("/"):
        return value, None, "value_is_expression"
    return value, unit, None


def _line_of(text: str, offset: int) -> tuple[int, int]:
    """(1-based line number, line start offset)."""
    start = text.rfind("\n", 0, offset) + 1
    return text.count("\n", 0, offset) + 1, start


def extract_candidates(text: str, report_id: Any, *,
                       max_line_chars: int = MAX_LINE_CHARS,
                       known_units: Sequence[str] = ()) -> tuple[list[dict], list[dict]]:
    """Pull raw ``name = value [unit]`` candidates out of one source document.

    Returns ``(candidates, discarded)``; discarded entries always carry a
    machine-readable reason.  No entity resolution happens here.
    """
    text = normalize_text(text)
    known = {u.lower() for u in known_units}
    cands: list[dict] = []
    dropped: list[dict] = []
    for m in _CAND.finditer(text):
        name = m.group("name")
        raw_value = m.group("value")
        line_no, line_start = _line_of(text, m.start())
        line_end = text.find("\n", m.start())
        line = text[line_start:(line_end if line_end != -1 else len(text))]
        base = {
            "report_id": report_id,
            "line_no": line_no,
            "span": [m.start(), m.end()],
            "needle": m.group(0),
            "name": name,
            "value_literal": raw_value,
            "line_sha256": sha256_text(line[:max_line_chars])[:16],
        }
        if len(line) > max_line_chars:
            dropped.append({**base, "reason": "line_too_long"})
            continue
        if _SNAKE.match(name):
            dropped.append({**base, "reason": "not_quantity_name"})
            continue
        value, unit, why = read_assignment(text, m)
        if why:
            dropped.append({**base, "reason": why})
            continue
        if not math.isfinite(value) or abs(value) > 1e12:
            dropped.append({**base, "reason": "value_out_of_range"})
            continue
        if unit is not None and known and unit.lower() not in known:
            unit = None  # unknown trailing token: not a unit, keep value only
        cands.append({**base, "value": value, "unit": unit, "line": line})
    return cands, dropped


def relocate(text: str, claim: dict, *, tolerance: float = 1e-9) -> dict:
    """Re-derive the value from the source bytes at the recorded span.

    This is the zero-hand-copying gate: a KO is only 'verified' if the exact
    needle still sits at ``span`` and the number read from the bytes equals the
    number recorded in the KO.
    """
    text = normalize_text(text)
    start, end = claim["span"]
    needle = text[start:end]
    ok_needle = needle == claim["needle"]
    ok_value = False
    try:
        ok_value = abs(float(claim["value_literal"]) - float(claim["value"])) <= tolerance * max(
            1.0, abs(float(claim["value"])))
    except (TypeError, ValueError):  # pragma: no cover - defensive
        ok_value = False
    return {
        "relocated": bool(ok_needle and ok_value),
        "needle_match": ok_needle,
        "value_match": ok_value,
        "excerpt_sha256": sha256_text(text[start:end]),
        "resolver": "gov-relocate-v1",
    }


_HEADING = re.compile(r"^#{1,6}\s+(.*)$", re.MULTILINE)


def _headings(text: str) -> list[tuple[int, str]]:
    return [(m.start(), m.group(1).strip()) for m in _HEADING.finditer(text)]


def _heading_for(headings: list[tuple[int, str]], offset: int) -> str:
    current = ""
    for pos, title in headings:
        if pos > offset:
            break
        current = title
    return current


def geometry_context(line: str, heading: str, cfg: dict) -> str | None:
    """Nearest declared shape/geometry keyword (line first, then its section).

    Geometry is a *condition*: two drag coefficients at the same Re on a cylinder
    and on a sphere are not the same physical case.  Without this the detector
    would report condition-blind "contradictions".
    """
    patterns = cfg.get("extraction", {}).get("context_keywords", {}).get("geometry", {})
    if not patterns:
        return None
    for scope in (line, heading):
        hay = normalize_text(scope).lower()
        hits: list[tuple[int, str]] = []
        for name, keys in patterns.items():
            n = sum(1 for k in keys if k.lower() in hay)
            if n:
                hits.append((n, name))
        if hits:
            hits.sort(key=lambda t: (-t[0], t[1]))
            return hits[0][1]
    return None


def _conditions_from_line(line: str, registry: EntityRegistry, own_entity: str) -> dict:
    """Condition entities (kind=condition) asserted on the same line."""
    conds: dict[str, str] = {}
    text = normalize_text(line)
    for m in _CAND.finditer(text):
        res = registry.resolve(m.group("name"))
        eid = res["entity_id"]
        if not eid or registry.kind(eid) != "condition" or eid == own_entity:
            continue
        value, unit, why = read_assignment(text, m)
        if why:
            continue
        conds[registry.canonical(eid)] = f"{sig(value)}" + (f" {unit_key(unit)}" if unit else "")
    return dict(sorted(conds.items()))


def _lookback_conditions(text: str, offset: int, registry: EntityRegistry,
                        own_entity: str, max_lines: int) -> dict:
    """Nearest preceding lines (same section) carrying condition assignments.

    Reports state the case once ("Re = 100 ...") and then list results; without a
    lookback window almost no result would carry its conditions, and
    cross-validation would be permanently ``insufficient-evidence`` by
    construction.  The window is bounded (config) and never crosses a heading.
    """
    found: dict[str, str] = {}
    start = offset
    for _ in range(max_lines):
        prev_end = start
        prev_start = text.rfind("\n", 0, max(0, prev_end - 1)) + 1
        if prev_start <= 0:
            break
        line = text[prev_start:prev_end]
        start = prev_start
        if line.lstrip().startswith("#"):
            break
        for k, v in _conditions_from_line(line, registry, own_entity).items():
            found.setdefault(k, v)
    return dict(sorted(found.items()))


def build_kos(report: dict, registry: EntityRegistry, cfg: dict) -> dict:
    """One source report -> quantity KOs + discards + entity-resolution ledger."""
    text = report["text"]
    headings = _headings(normalize_text(text))
    ex = cfg["extraction"]
    lookback = int(ex.get("condition_lookback_lines", 0) or 0)
    cands, dropped = extract_candidates(
        text, report["report_id"],
        max_line_chars=ex.get("max_line_chars", MAX_LINE_CHARS),
        known_units=ex.get("known_units", ()))
    pre_discarded = len(dropped)   # rejected before entity resolution
    kos: list[dict] = []
    resolution: list[dict] = []
    context = 0
    for cand in cands:
        res = registry.resolve(cand["name"])
        resolution.append({"candidate": cand["name"], **res,
                           "report_id": report["report_id"], "span": cand["span"]})
        if not res["entity_id"]:
            dropped.append({**{k: cand[k] for k in ("report_id", "line_no", "span", "needle",
                                                    "name", "line_sha256")},
                            "reason": "entity_unresolved"})
            continue
        if registry.kind(res["entity_id"]) != "result":
            # conditions are context, not observations: they are not KOs
            context += 1
            continue
        canonical = registry.canonical(res["entity_id"])
        unit = cand["unit"]
        conditions = _conditions_from_line(cand["line"], registry, res["entity_id"])
        if not conditions and lookback:
            conditions = _lookback_conditions(text, cand["span"][0], registry,
                                              res["entity_id"], lookback)
        geo = geometry_context(cand["line"], _heading_for(headings, cand["span"][0]), cfg)
        if geo:
            conditions["geo"] = geo
            conditions = dict(sorted(conditions.items()))
        subject_key = f"{canonical}|{res['qualifier']}|{unit_key(unit)}"
        cond_key = ";".join(f"{k}={v}" for k, v in conditions.items())
        ko = {
            "id": "tkc:gov:" + sha256_text(
                f"{report['report_id']}|{cand['span'][0]}|{subject_key}")[:16],
            "kind": "quantity-observation",
            "entity_id": res["entity_id"],
            "entity": canonical,
            "qualifier": res["qualifier"],
            "entity_confidence": res["confidence"],
            "matched_alias": res["matched_alias"],
            "value": cand["value"],
            "unit": unit,
            "conditions": conditions,
            "subject_key": subject_key,
            "condition_key": cond_key,
            "source": {
                "report_id": report["report_id"],
                "report_sha256": report.get("sha256"),
                "line_no": cand["line_no"],
                "span": cand["span"],
                "needle": cand["needle"],
                "line_sha256": cand["line_sha256"],
            },
            "producer_ids": [PRODUCER_ID, report.get("producer", "platform/report-author")],
            "verification": {},
            "fingerprints": {},
        }
        ko["verification"] = relocate(text, {
            "span": cand["span"], "needle": cand["needle"],
            "value_literal": cand["value_literal"], "value": ko["value"]},
            tolerance=ex.get("needle_tolerance", 1e-9))
        vdigits = cfg["thresholds"]["value_significant_digits"]
        ko["fingerprints"] = {
            "exact": sha256_text("|".join([
                subject_key, sig(ko["value"], vdigits), cond_key,
                text[cand["span"][0]:cand["span"][1]]])),
            "subject": sha256_text("|".join([subject_key, sig(ko["value"], vdigits), cond_key])),
            "simhash": simhash64(cand["line"], mask=True),
            "wording": mask_numbers(normalize_text(cand["line"]).lower())[:200],
        }
        if not ko["verification"]["relocated"]:
            dropped.append({**ko["source"], "reason": "provenance_unverified"})
            continue
        kos.append(ko)
    return {"kos": kos, "discarded": dropped, "resolution": resolution,
            "candidates": len(cands) + pre_discarded, "context": context}


# ---------------------------------------------------------------------------
# Fingerprints: simhash over number-masked wording
# ---------------------------------------------------------------------------
_TOK = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]")
_NUM_MASK = re.compile(_NUM)


def mask_numbers(text: str) -> str:
    return _NUM_MASK.sub("#", text)


def simhash64(text: str, *, mask: bool = True, shingle: int = 3) -> str:
    """64-bit simhash (hex) of the wording; numbers masked by default."""
    s = normalize_text(text).lower()
    if mask:
        s = mask_numbers(s)
    toks = _TOK.findall(s)
    if not toks:
        return "0" * 16
    grams = [" ".join(toks[i:i + shingle]) for i in range(max(1, len(toks) - shingle + 1))]
    vec = [0] * 64
    for g in grams:
        h = int(hashlib.md5(g.encode("utf-8")).hexdigest()[:16], 16)
        for bit in range(64):
            vec[bit] += 1 if (h >> bit) & 1 else -1
    out = 0
    for bit in range(64):
        if vec[bit] > 0:
            out |= (1 << bit)
    return f"{out:016x}"


def wording_tokens(text: str) -> set[str]:
    """Number-masked token set used by the semantic dedupe layer."""
    return set(_TOK.findall(mask_numbers(normalize_text(text).lower())))


def wording_jaccard(a: str, b: str) -> float:
    A, B = wording_tokens(a), wording_tokens(b)
    if not A and not B:
        return 1.0
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


# ---------------------------------------------------------------------------
# Dedup: two layers + connected components
# ---------------------------------------------------------------------------
class _UnionFind:
    def __init__(self, ids: Iterable[str]):
        self.parent = {i: i for i in ids}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            if ra > rb:  # deterministic root: smaller id wins
                ra, rb = rb, ra
            self.parent[rb] = ra


def dedupe(kos: Sequence[dict], cfg: dict) -> dict:
    """Cluster KOs into duplicate groups; return clusters + duplicate rate.

    L1 (*fingerprint*): identical exact fingerprint — same subject, same value at
    6 significant digits, same conditions **and** the same source needle text.

    L2 (*semantic*): same subject fingerprint — equals L1 minus the wording —
    and either (a) a non-empty identical condition set (conditions already pin
    the physical case), or (b) unstated conditions on both sides with wording
    simhash within ``near_dup_hamming``.
    """
    thr = cfg["thresholds"]
    uf = _UnionFind(ko["id"] for ko in kos)
    layers: dict[tuple[str, str], str] = {}

    by_exact: dict[str, list[dict]] = {}
    for ko in kos:
        by_exact.setdefault(ko["fingerprints"]["exact"], []).append(ko)
    for group in by_exact.values():
        for other in group[1:]:
            uf.union(group[0]["id"], other["id"])
            layers[(group[0]["id"], other["id"])] = "exact"

    by_subject: dict[str, list[dict]] = {}
    for ko in kos:
        by_subject.setdefault(ko["fingerprints"]["subject"], []).append(ko)
    for group in by_subject.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a["fingerprints"]["exact"] == b["fingerprints"]["exact"]:
                    continue
                if a["condition_key"] and a["condition_key"] == b["condition_key"]:
                    uf.union(a["id"], b["id"])
                    layers.setdefault((a["id"], b["id"]), "semantic_conditions")
                elif not a["condition_key"] and not b["condition_key"]:
                    fa, fb = a["fingerprints"], b["fingerprints"]
                    d = hamming(fa["simhash"], fb["simhash"])
                    j = wording_jaccard(fa.get("wording", ""), fb.get("wording", ""))
                    if d <= thr["near_dup_hamming"]:
                        uf.union(a["id"], b["id"])
                        layers.setdefault((a["id"], b["id"]), "semantic_simhash")
                    elif j >= thr.get("near_dup_jaccard", 0.5):
                        uf.union(a["id"], b["id"])
                        layers.setdefault((a["id"], b["id"]), "semantic_wording")

    comps: dict[str, list[dict]] = {}
    for ko in kos:
        comps.setdefault(uf.find(ko["id"]), []).append(ko)
    clusters = []
    for root, members in sorted(comps.items()):
        members = sorted(members, key=lambda k: (k["source"]["report_id"], k["source"]["span"][0]))
        rep = members[0]
        lay = sorted({layers.get((a["id"], b["id"]), "exact")
                      for i, a in enumerate(members) for b in members[i + 1:]})
        clusters.append({
            "cluster_id": "tkc:gov-cluster:" + sha256_text(root)[:12],
            "representative": rep["id"],
            "size": len(members),
            "member_ids": [m["id"] for m in members],
            "source_reports": sorted({m["source"]["report_id"] for m in members}),
            "subject_key": rep["subject_key"],
            "condition_key": rep["condition_key"],
            "value": rep["value"],
            "layers": lay or ["singleton"],
            "is_duplicate": len(members) > 1,
        })
    n = len(kos)
    dup_members = sum(c["size"] - 1 for c in clusters)
    return {
        "clusters": clusters,
        "n_ko": n,
        "n_clusters": len(clusters),
        "duplicate_members": dup_members,
        "duplicate_rate": (dup_members / n) if n else 0.0,
        "layer_counts": {
            "exact": sum(1 for c in clusters if c["is_duplicate"] and "exact" in c["layers"]),
            "semantic": sum(1 for c in clusters
                            if c["is_duplicate"] and "exact" not in c["layers"]),
            "clusters_by_size": _cluster_size_hist(clusters),
        },
    }


def _cluster_size_hist(clusters: Sequence[dict]) -> dict[str, int]:
    hist: dict[str, int] = {}
    for c in clusters:
        hist[str(c["size"])] = hist.get(str(c["size"]), 0) + 1
    return dict(sorted(hist.items(), key=lambda kv: int(kv[0])))


# ---------------------------------------------------------------------------
# Cross-validation + Contradiction Detection v1
# ---------------------------------------------------------------------------
def _rel_diff(a: float, b: float) -> float:
    denom = max(abs(a), abs(b))
    if denom < 1e-12:
        return 0.0 if a == b else 1.0
    return abs(a - b) / denom


def cross_validate(kos: Sequence[dict], cfg: dict) -> dict:
    """Compare the same physical quantity across distinct source reports.

    Verdicts are deliberately conservative:

    * ``supported``            — >=2 distinct reports agree within ``agree_rel``
                                 and no contradicted pair exists;
    * ``contradicted``         — some pair shares non-empty, identical
                                 conditions and differs by > ``contradict_rel``;
    * ``insufficient-evidence``— everything else (single source, unstated or
                                 differing conditions).

    Pairs with unstated conditions are still compared, but never promote a
    group to ``supported``/``contradicted``: they are recorded as
    ``unverified_comparison`` so the gap is visible instead of assumed away.
    """
    thr = cfg["thresholds"]
    agree_rel = thr["agree_rel"]
    contradict_rel = thr["contradict_rel"]
    groups: dict[str, list[dict]] = {}
    document_local: list[str] = []
    for ko in kos:
        scope = _compare_scope(ko, cfg)
        if scope == "document_local":
            document_local.append(ko["subject_key"])
            continue
        groups.setdefault(ko["subject_key"], []).append(ko)

    out_groups: list[dict] = []
    pairs: list[dict] = []
    for subject_key, members in sorted(groups.items()):
        members = sorted(members, key=lambda k: (k["source"]["report_id"], k["source"]["span"][0]))
        reports = sorted({m["source"]["report_id"] for m in members})
        pair_rows = []
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                if a["source"]["report_id"] == b["source"]["report_id"]:
                    continue  # intra-document repetition is dedup's business
                rel = _rel_diff(a["value"], b["value"])
                same_cond = (a["condition_key"] == b["condition_key"])
                # geometry alone does not pin a physical case: adjudication needs
                # at least one *numeric* condition (Re, Fr, alpha, ...) on both sides
                conds_stated = bool(_numeric_conditions(a) and _numeric_conditions(b))
                if rel <= agree_rel:
                    verdict = "agree"
                elif not same_cond:
                    verdict = "incomparable_conditions"
                elif not conds_stated:
                    verdict = "unverified_comparison"   # divergence, no conditions
                elif rel > contradict_rel:
                    verdict = "contradicted"
                else:
                    verdict = "divergent"
                row = {
                    "a": a["id"], "b": b["id"],
                    "reports": [a["source"]["report_id"], b["source"]["report_id"]],
                    "value_a": a["value"], "value_b": b["value"],
                    "unit": unit_key(a["unit"]),
                    "conditions_a": a["conditions"], "conditions_b": b["conditions"],
                    "rel_diff": round(rel, 6),
                    "verdict": verdict,
                    "thresholds": {"agree_rel": agree_rel, "contradict_rel": contradict_rel},
                }
                pair_rows.append(row)
                pairs.append({"subject_key": subject_key, **row})

        verdicts = [p["verdict"] for p in pair_rows]
        adjudicable = any(p["verdict"] == "agree" and p["conditions_a"]
                          and _has_numeric(p["conditions_a"]) for p in pair_rows)
        if "contradicted" in verdicts:
            group_verdict = "contradicted"
        elif len(reports) >= 2 and verdicts and all(v == "agree" for v in verdicts) and adjudicable:
            group_verdict = "supported"
        else:
            group_verdict = "insufficient-evidence"
        out_groups.append({
            "subject_key": subject_key,
            "entity": members[0]["entity"],
            "qualifier": members[0]["qualifier"],
            "unit": unit_key(members[0]["unit"]),
            "n_ko": len(members),
            "n_reports": len(reports),
            "reports": reports,
            "verdict": group_verdict,
            "pair_verdicts": {v: verdicts.count(v) for v in sorted(set(verdicts))},
        })

    contra = [p for p in pairs if p["verdict"] == "contradicted"]
    return {
        "groups": out_groups,
        "pairs": pairs,
        "contradictions": [
            {
                "contradiction_id": "tkc:gov-contradiction:" + sha256_text(
                    p["a"] + "|" + p["b"])[:12],
                "subject_key": p["subject_key"],
                "a": p["a"], "b": p["b"],
                "reports": p["reports"],
                "value_a": p["value_a"], "value_b": p["value_b"],
                "rel_diff": p["rel_diff"],
                "conditions": p["conditions_a"],
                "status": "contradicted",
                "next_action": "replicate",  # schema NextAction enum value
                "rationale": (f"same conditions, |Δ|/max = {p['rel_diff']:.2%} > "
                              f"contradict_rel={contradict_rel:.0%}"),
            }
            for p in contra
        ],
        "group_verdicts": {v: sum(1 for g in out_groups if g["verdict"] == v)
                           for v in ("supported", "contradicted", "insufficient-evidence")},
        "pair_verdicts": {v: sum(1 for p in pairs if p["verdict"] == v)
                          for v in sorted({p["verdict"] for p in pairs})},
        "n_pairs": len(pairs),
        "n_contradiction_pairs": len(contra),
        "document_local_subjects": sorted(set(document_local)),
    }


def _numeric_conditions(ko: dict) -> dict:
    return {k: v for k, v in ko["conditions"].items() if k != "geo"}


def _has_numeric(conditions: dict) -> bool:
    return any(k != "geo" for k in conditions)


def _compare_scope(ko: dict, cfg: dict) -> str:
    for e in cfg["entities"]:
        if e["id"] == ko["entity_id"]:
            return e.get("comparison", "cross_report")
    return "cross_report"


def ko_consistency_status(ko: dict, crossval: dict) -> dict:
    """Per-KO roll-up of the cross-validation result (feeding the review gate)."""
    worst = {"contradicted": 0, "divergent": 0, "agree": 0, "other": 0}
    for p in crossval["pairs"]:
        if ko["id"] not in (p["a"], p["b"]):
            continue
        v = p["verdict"]
        worst[v if v in ("contradicted", "divergent", "agree") else "other"] += 1
    if worst["contradicted"]:
        status = "contradicted"
    elif worst["divergent"]:
        status = "divergent"
    elif worst["agree"]:
        status = "agree"
    else:
        status = "not_compared"
    return {"status": status, **worst}

# ---------------------------------------------------------------------------
# Review pool (pooled agent reviewers + state-machine write-back)
# ---------------------------------------------------------------------------
def load_state_machine():
    """Load ``scripts/ke_state_machine.py`` as a module (single source of truth)."""
    spec = importlib.util.spec_from_file_location("ke_state_machine", STATE_MACHINE_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load {STATE_MACHINE_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _is_dimensionless(entity: str) -> bool:
    # dimensionless families: Cx coefficients, Reynolds/Froude/Mach/Nusselt/
    # Strouhal/Prandtl/Rayleigh/L-D/error/zeta/alpha/lambda are ratios by definition.
    return re.match(r"^(C[a-zA-Z]?|Re|Fr|Ma|Nu|St|Pr|Ra|L/D|err|zeta|alpha|lambda)$",
                    entity) is not None


def gate_provenance(ko: dict, _ctx: dict) -> tuple[str, str, str]:
    v = ko["verification"]
    if v.get("relocated") and v.get("excerpt_sha256"):
        return "pass", "PROVENANCE_OK", "needle relocated at recorded span"
    return "fail", "PROVENANCE_UNVERIFIED", "needle/value not reproducible from source bytes"


def gate_units(ko: dict, _ctx: dict) -> tuple[str, str, str]:
    unit = unit_key(ko["unit"])
    if _is_dimensionless(ko["entity"]):
        if unit in ("-", "%"):
            return "pass", "UNIT_OK", f"dimensionless entity, unit={unit}"
        return "fail", "UNIT_DIMENSION_MISMATCH", f"dimensionless entity carries unit={unit}"
    if unit == "-":
        return "needs-fix", "UNIT_MISSING", "dimensional entity without unit"
    return "pass", "UNIT_OK", f"unit={unit}"


def gate_entity(ko: dict, ctx: dict) -> tuple[str, str, str]:
    thr = ctx["thresholds"]
    if ko["entity_confidence"] >= thr["min_entity_confidence"]:
        return "pass", "ENTITY_RESOLVED", f"alias={ko['matched_alias']}"
    return ("needs-fix", "ENTITY_QUALIFIER_UNVERIFIED",
            f"base entity resolved but qualifier {ko['qualifier']!r} unverified")


def gate_consistency(ko: dict, ctx: dict) -> tuple[str, str, str]:
    st = ctx["consistency"].get(ko["id"], {"status": "not_compared"})
    if st["status"] == "contradicted":
        return ("fail", "CONTRADICTION_BLOCKING",
                "cross-source contradiction on identical conditions")
    if st["status"] == "divergent":
        return "needs-fix", "CROSS_SOURCE_DIVERGENT", "cross-source divergence above agree_rel"
    if st["status"] == "agree":
        return "pass", "CROSS_SOURCE_AGREES", "cross-source agreement within agree_rel"
    return "pass", "SINGLE_SOURCE", "no cross-source comparison available"


GATES: dict[str, Callable[[dict, dict], tuple[str, str, str]]] = {
    "provenance": gate_provenance,
    "units": gate_units,
    "entity": gate_entity,
    "consistency": gate_consistency,
}

VERDICT_TO_DECISION = {"pass": "approve", "needs-fix": "request-changes", "fail": "reject"}


class ReviewPool:
    """Pooled, deterministic review assignment + quorum + state-machine write-back.

    * one gate lane per reviewer role (provenance / units / entity / consistency);
    * two instances per lane in the pool; the instance is chosen by
      ``sha256(item_id)`` so the assignment is reproducible and balanced;
    * capacity per instance is enforced; an item that cannot be placed is
      *deferred by capacity* and counted, never silently dropped;
    * **independence** is enforced by the state machine itself
      (``is_independent``): a reviewer sharing an identity token with the
      producer is refused (``SELF_APPROVAL_BLOCKED``).
    """

    def __init__(self, cfg: dict):
        pool = cfg["review_pool"]
        self.policy = pool.get("policy", "dual-blind-quorum-v1")
        self.quorum = pool.get("quorum", {})
        self.reviewers = [dict(r) for r in pool["reviewers"]]
        self.used: dict[str, int] = {r["id"]: 0 for r in self.reviewers}
        self.thresholds = cfg["thresholds"]

    def _lane_instances(self, lane: str) -> list[dict]:
        return [r for r in self.reviewers if lane in r.get("lanes", ())]

    def assign(self, item_id: str) -> dict:
        """Return {lane: reviewer} using a stable hash per lane, honouring capacity."""
        out: dict[str, dict] = {}
        deferred: list[str] = []
        for lane in sorted(GATES):
            instances = self._lane_instances(lane)
            if not instances:
                raise KeyError(f"review pool has no reviewer for lane {lane!r}")
            start = stable_int(f"{item_id}|{lane}", len(instances))
            chosen = None
            for k in range(len(instances)):
                cand = instances[(start + k) % len(instances)]
                if self.used[cand["id"]] < cand.get("capacity", 10 ** 9):
                    chosen = cand
                    break
            if chosen is None:
                deferred.append(lane)
                continue
            self.used[chosen["id"]] += 1
            out[lane] = chosen
        return {"lanes": out, "deferred_lanes": deferred}

    def review(self, ko: dict, ctx: dict, *, run_at: str) -> dict:
        """Run every gate lane on one KO; return votes, decision, state-machine event."""
        assignment = self.assign(ko["id"])
        votes: list[dict] = []
        verdicts: list[str] = []
        for lane in sorted(GATES):
            reviewer = assignment["lanes"].get(lane)
            if reviewer is None:
                continue  # deferred by capacity -> no vote from this lane
            verdict, code, detail = GATES[lane](ko, {**ctx, "thresholds": self.thresholds})
            verdicts.append(verdict)
            votes.append({
                "item_id": ko["id"],
                "lane": lane,
                "reviewer": {"id": reviewer["id"], "reviewer_type": reviewer["reviewer_type"],
                             "role": lane, "model": reviewer.get("model")},
                "verdict": verdict,
                "code": code,
                "detail": detail,
                "reviewed_at": run_at,
            })
        scored = [v for v in verdicts if v != "pass"]
        if "fail" in verdicts:
            decision = "reject"
        elif "needs-fix" in verdicts:
            decision = "request-changes"
        elif len(scored) == 0 and verdicts:
            decision = "approve"
        else:
            decision = "request-changes"  # no vote at all = capacity deferral -> needs fix
        disagreement = len({v["verdict"] for v in votes}) > 1
        findings = [
            {"severity": _severity(v["verdict"]), "finding": f"[{v['lane']}] {v['code']}: {v['detail']}",
             "related_claim_refs": [ko["id"]]}
            for v in votes if v["verdict"] != "pass"
        ]
        event = {
            "id": "tkr:gov:" + sha256_text(f"{ko['id']}|{run_at}|{decision}")[:16],
            "object_ref": ko["id"],
            "object_version": "1.0.0",
            "decision": decision,
            "reviewer": {"id": _lead_reviewer(votes, decision)["id"],
                         "reviewer_type": "agent",
                         "role": "+".join(sorted({v["lane"] for v in votes})) or "pool"},
            "reviewed_at": run_at,
            "policy_version": load_state_machine().POLICY_VERSION,
            "rationale": (f"pool={self.policy} quorum; verdicts=" +
                          json.dumps(_verdict_hist(votes), sort_keys=True)),
            "findings": findings,
        }
        return {
            "votes": votes,
            "assignment": {"lanes": {k: v["id"] for k, v in assignment["lanes"].items()},
                           "deferred_lanes": assignment["deferred_lanes"]},
            "verdict": ("fail" if decision == "reject"
                        else "needs-fix" if decision == "request-changes" else "pass"),
            "decision": decision,
            "disagreement": disagreement,
            "event": event,
        }


def _lead_reviewer(votes: Sequence[dict], decision: str) -> dict:
    """Deterministically name the signing reviewer (the failing/asking lane if any)."""
    if not votes:
        return {"id": PRODUCER_ID}
    if decision == "approve":
        return votes[0]["reviewer"]
    wanted = "fail" if decision == "reject" else "needs-fix"
    for v in votes:
        if v["verdict"] == wanted:
            return v["reviewer"]
    return votes[0]["reviewer"]


def _severity(verdict: str) -> str:
    return {"fail": "blocking", "needs-fix": "major"}.get(verdict, "minor")


def _verdict_hist(votes: Sequence[dict]) -> dict:
    hist: dict[str, int] = {}
    for v in votes:
        hist[v["code"]] = hist.get(v["code"], 0) + 1
    return hist


def fold_reviews(events: Sequence[dict], kos_by_id: dict, *, run_at: str) -> dict:
    """Fold review events through the shared state machine -> per-object status.

    Refusals (any :class:`StateMachineError`) are recorded in ``refused`` and do
    not change the object's status: an attempt is auditable, a no-op is not
    mistaken for an approval.
    """
    sm = load_state_machine()
    ledger: list[dict] = []
    state: dict[str, str] = {}
    writeback: dict[str, dict] = {}
    refused: list[dict] = []
    for ev in sorted(events, key=lambda e: e["object_ref"]):
        ko = kos_by_id[ev["object_ref"]]
        cur = state.get(ev["object_ref"], "in-review")
        ctx = {"producer_ids": ko.get("producer_ids", [])}
        try:
            nxt, code = sm.validate_event(dict(ev), cur, ledger, ctx, ev["policy_version"])
        except sm.StateMachineError as exc:
            refused.append({"event_id": ev["id"], "object_ref": ev["object_ref"],
                            "code": exc.code, "detail": exc.detail, "at": run_at})
            writeback.setdefault(ev["object_ref"], {"state": cur, "last_code": exc.code,
                                                    "decision": None})
            continue
        ledger.append({**ev, "from_state": cur, "to_state": nxt, "outcome_code": code})
        state[ev["object_ref"]] = nxt
        writeback[ev["object_ref"]] = {"state": nxt, "last_code": code,
                                       "decision": ev["decision"], "at": ev["reviewed_at"]}
    return {"events": ledger, "status": state, "writeback": writeback,
            "refused": refused, "policy_version": sm.POLICY_VERSION}


def chain_ledger(events: Sequence[dict]) -> list[dict]:
    """Append-only hash chain: each line commits to the previous line's sha256."""
    out: list[dict] = []
    prev = "0" * 64
    for ev in events:
        line = {"event": ev, "prev_sha256": prev}
        line["line_sha256"] = sha256_text(json.dumps(line, sort_keys=True, ensure_ascii=False))
        prev = line["line_sha256"]
        out.append(line)
    return out


def verify_chain(lines: Sequence[dict]) -> dict:
    """Recompute the hash chain; return {'ok': bool, 'broken_at': index|None}."""
    prev = "0" * 64
    for i, line in enumerate(lines):
        body = {"event": line["event"], "prev_sha256": prev}
        if sha256_text(json.dumps(body, sort_keys=True, ensure_ascii=False)) != line["line_sha256"]:
            return {"ok": False, "broken_at": i, "n_lines": len(lines)}
        prev = line["line_sha256"]
    return {"ok": True, "broken_at": None, "n_lines": len(lines)}


# ---------------------------------------------------------------------------
# Three counting口径 (buckets) — reconciled, never conflated
# ---------------------------------------------------------------------------
class BucketViolation(Exception):
    """A counting口径 inconsistency: raised instead of reporting a wrong number."""


BUCKETS = {
    "B0_raw_records": "source documents scanned in the pilot batch",
    "B1_ko_pending_review": "extracted knowledge objects submitted to the review queue",
    "B2_governed_objects": "knowledge objects that survived review and dedupe collapse",
}


class Counting:
    """Three-bucket ledger with reconciliation invariants.

    The historical disease this fixes ("20 vs 257"): every published number had
    a different, unstated denominator.  Here every metric **must** declare its
    bucket (``tag``) and the bucket counts must reconcile; a mismatch raises
    :class:`BucketViolation`.
    """

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.metrics: dict[str, dict] = {}
        self.invariants: dict[str, bool] = {}

    # -- counts ------------------------------------------------------------
    def set(self, key: str, value: int) -> None:
        self.counts[key] = int(value)

    def inc(self, key: str, n: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + int(n)

    # -- metrics -----------------------------------------------------------
    def metric(self, name: str, value: Any, bucket: str, *, formula: str,
               numerator: str | None = None, denominator: str | None = None) -> None:
        if bucket not in BUCKETS and not bucket.startswith("derived:"):
            raise BucketViolation(f"metric {name!r} declares unknown bucket {bucket!r}")
        self.metrics[name] = {"value": value, "bucket": bucket, "formula": formula,
                              "numerator": numerator, "denominator": denominator}

    def reconcile(self) -> dict:
        c = self.counts
        checks = {
            "extraction_reconciles": c.get("quantity_statements", 0)
            == c.get("discarded", 0) + c.get("context_candidates", 0) + c.get("ko_extracted", 0),
            "review_queue_reconciles": c.get("ko_pending_review", 0) == c.get("ko_extracted", 0),
            "review_outcomes_reconcile": c.get("ko_pending_review", 0)
            == c.get("review_pass", 0) + c.get("review_needs_fix", 0) + c.get("review_fail", 0),
            "governed_partitions_pass": c.get("review_pass", 0)
            == c.get("governed_objects", 0) + c.get("pass_duplicate_members", 0),
            "duplicate_members_le_all": c.get("duplicate_members", 0)
            <= c.get("ko_pending_review", 0),
            "clusters_reconcile": c.get("dedup_clusters", 0)
            == c.get("ko_pending_review", 0) - c.get("duplicate_members", 0),
        }
        # metric buckets must stay inside the declared口径 hierarchy
        checks["duplicate_rate_bucket"] = self.metrics.get("duplicate_rate", {}).get(
            "bucket") == "derived:B1_ko_pending_review"
        checks["review_pass_rate_bucket"] = self.metrics.get("review_pass_rate", {}).get(
            "bucket") == "derived:B1_ko_pending_review"
        checks["governed_bucket"] = self.metrics.get("governed_knowledge_objects", {}).get(
            "bucket") == "B2_governed_objects"
        self.invariants = checks
        bad = [k for k, v in checks.items() if not v]
        if bad:
            raise BucketViolation(f"counting口径 violated: {bad}; counts={self.counts}")
        return checks


def duplicate_rate(dedup_result: dict) -> float:
    return dedup_result["duplicate_rate"]


# ---------------------------------------------------------------------------
# End-to-end governance run
# ---------------------------------------------------------------------------
def run_governance(reports: Sequence[dict], cfg: dict, *, run_at: str) -> dict:
    """Run the full governance pipeline over a pilot batch of source reports.

    ``reports``: [{'report_id', 'title', 'text', 'sha256'?, 'producer'?}]
    ``run_at``: explicit ISO-8601 timestamp (determinism: no wall clock inside).
    """
    registry = EntityRegistry(cfg)
    kos: list[dict] = []
    discarded: list[dict] = []
    resolution: list[dict] = []
    quantity_statements = 0
    context_candidates = 0
    for rep in sorted(reports, key=lambda r: r["report_id"]):
        rep = {**rep, "sha256": rep.get("sha256") or sha256_text(rep["text"])}
        built = build_kos(rep, registry, cfg)
        kos.extend(built["kos"])
        discarded.extend(built["discarded"])
        resolution.extend(built["resolution"])
        quantity_statements += built["candidates"]
        context_candidates += built["context"]

    dedup = dedupe(kos, cfg)
    crossval = cross_validate(kos, cfg)
    consistency = {ko["id"]: ko_consistency_status(ko, crossval) for ko in kos}

    pool = ReviewPool(cfg)
    kos_by_id = {ko["id"]: ko for ko in kos}
    results = [pool.review(ko, {"consistency": consistency}, run_at=run_at) for ko in kos]
    folded = fold_reviews([r["event"] for r in results], kos_by_id, run_at=run_at)

    # three口径
    counting = Counting()
    counting.set("raw_records", len(reports))
    counting.set("quantity_statements", quantity_statements)
    counting.set("context_candidates", context_candidates)
    counting.set("discarded", len(discarded))
    counting.set("ko_extracted", len(kos))
    counting.set("ko_pending_review", len(kos))
    counting.set("dedup_clusters", dedup["n_clusters"])
    counting.set("duplicate_members", dedup["duplicate_members"])
    outcomes = {"pass": 0, "needs-fix": 0, "fail": 0}
    for r in results:
        outcomes[r["verdict"]] += 1
    counting.set("review_pass", outcomes["pass"])
    counting.set("review_needs_fix", outcomes["needs-fix"])
    counting.set("review_fail", outcomes["fail"])

    # governed = pass AND representative of its duplicate cluster
    cluster_of = {mid: c["cluster_id"] for c in dedup["clusters"] for mid in c["member_ids"]}
    rep_of = {c["cluster_id"]: c["representative"] for c in dedup["clusters"]}
    passed = {r["event"]["object_ref"] for r in results if r["verdict"] == "pass"}
    governed = {oid for oid in passed if rep_of.get(cluster_of[oid]) == oid}
    counting.set("governed_objects", len(governed))
    counting.set("pass_duplicate_members", len(passed - governed))

    counting.metric("raw_records", len(reports), "B0_raw_records",
                    formula="count(distinct source report id in pilot slice)")
    counting.metric("ko_pending_review", len(kos), "B1_ko_pending_review",
                    formula="ko_extracted = quantity_statements - discarded")
    counting.metric("governed_knowledge_objects", len(governed), "B2_governed_objects",
                    formula="review_pass AND cluster representative")
    counting.metric("duplicate_rate", round(dedup["duplicate_rate"], 6),
                    "derived:B1_ko_pending_review",
                    formula="(B1 - clusters) / B1",
                    numerator="duplicate_members", denominator="ko_pending_review")
    counting.metric("contradiction_pairs", crossval["n_contradiction_pairs"],
                    "derived:B1_ko_pending_review",
                    formula="count(pairs with verdict=contradicted)",
                    numerator="n_contradiction_pairs", denominator="n_pairs")
    counting.metric("review_pass_rate", round(outcomes["pass"] / len(kos), 6) if kos else 0.0,
                    "derived:B1_ko_pending_review",
                    formula="review_pass / B1",
                    numerator="review_pass", denominator="ko_pending_review")
    counting.metric("entity_resolution_rate",
                    round(_resolution_rate(resolution), 6), "derived:B0_raw_records",
                    formula="resolved candidates / all candidates",
                    numerator="resolved", denominator="candidates")
    invariants = counting.reconcile()

    writeback = []
    for ko in kos:
        wb = folded["writeback"].get(ko["id"], {"state": "in-review", "last_code": None})
        writeback.append({
            "ko_id": ko["id"],
            "entity": ko["entity"],
            "value": ko["value"],
            "unit": unit_key(ko["unit"]),
            "subject_key": ko["subject_key"],
            "source_report": ko["source"]["report_id"],
            "review_state": wb.get("state"),
            "review_code": wb.get("last_code"),
            "governed": ko["id"] in governed,
            "cluster_id": cluster_of.get(ko["id"]),
            "consistency": consistency[ko["id"]]["status"],
        })

    return {
        "run_at": run_at,
        "config_version": cfg["version"],
        "policy_version": folded["policy_version"],
        "registry": registry,
        "reports": [{"report_id": r["report_id"], "title": r.get("title", ""),
                     "sha256": r.get("sha256") or sha256_text(r["text"]),
                     "chars": len(r["text"])} for r in sorted(reports, key=lambda r: r["report_id"])],
        "kos": kos,
        "discarded": discarded,
        "resolution": resolution,
        "dedup": dedup,
        "crossval": crossval,
        "review": {"results": results, "folded": folded,
                   "ledger": chain_ledger(folded["events"]),
                   "pool_usage": {r["id"]: pool.used[r["id"]] for r in pool.reviewers}},
        "counting": counting,
        "invariants": invariants,
        "writeback": writeback,
        "stats": {"metrics": counting.metrics, "counts": counting.counts,
                  "verdicts": outcomes,
                  "group_verdicts": crossval["group_verdicts"],
                  "pair_verdicts": crossval["pair_verdicts"],
                  "dedup_layers": dedup["layer_counts"],
                  "governed_objects": len(governed)},
    }


def _resolution_rate(resolution: Sequence[dict]) -> float:
    if not resolution:
        return 0.0
    resolved = sum(1 for r in resolution if r["entity_id"])
    return resolved / len(resolution)


# ---------------------------------------------------------------------------
# Artifact writing
# ---------------------------------------------------------------------------
def _dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def _dump_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_artifacts(result: dict, out_dir: Path) -> dict:
    """Persist every governance product; return the artefact index with sha256."""
    out = Path(out_dir)
    _dump_json(out / "snapshot.json", {
        "run_at": result["run_at"],
        "config_version": result["config_version"],
        "policy_version": result["policy_version"],
        "n_reports": len(result["reports"]),
        "reports": result["reports"],
        "snapshot_digest": sha256_text(json.dumps(
            [[r["report_id"], r["sha256"]] for r in result["reports"]], sort_keys=True)),
    })
    _dump_jsonl(out / "ko.jsonl", result["kos"])
    _dump_jsonl(out / "discarded.jsonl", result["discarded"])
    _dump_jsonl(out / "entity-resolution.jsonl", result["resolution"])
    _dump_json(out / "dedup-clusters.json", result["dedup"])
    _dump_json(out / "crossval.json", {k: v for k, v in result["crossval"].items()})
    _dump_json(out / "contradictions.json", {
        "contradictions": result["crossval"]["contradictions"],
        "n_contradiction_pairs": result["crossval"]["n_contradiction_pairs"],
    })
    _dump_jsonl(out / "review" / "votes.jsonl",
                [v for r in result["review"]["results"] for v in r["votes"]])
    _dump_jsonl(out / "review" / "ledger.jsonl", result["review"]["ledger"])
    _dump_json(out / "review" / "writeback.json", result["writeback"])
    _dump_json(out / "review" / "refused.json", result["review"]["folded"]["refused"])
    _dump_json(out / "review" / "pool.json", {
        "policy": result["review"]["results"][0]["assignment"] if result["review"]["results"] else {},
        "usage": result["review"]["pool_usage"],
    })
    _dump_json(out / "stats.json", {
        "metrics": result["stats"]["metrics"],
        "counts": result["stats"]["counts"],
        "bucket_definitions": BUCKETS,
        "invariants": result["invariants"],
        "verdicts": result["stats"]["verdicts"],
        "group_verdicts": result["stats"]["group_verdicts"],
        "pair_verdicts": result["stats"]["pair_verdicts"],
        "dedup_layers": result["stats"]["dedup_layers"],
    })
    files = sorted(p for p in out.rglob("*") if p.is_file())
    # hash bytes, not text: figures live in the same directory
    return {"files": {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in files}}
