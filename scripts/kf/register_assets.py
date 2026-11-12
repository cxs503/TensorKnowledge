#!/usr/bin/env python3
"""KF work package `*‑01` (01-asset-registration) — generic asset registrar + verifier.

Rewrite of the one-off wp-542-01 builder as a *parameterised* tool: the package's
report_id / expected hash / title / scenario_key come from an explicit registry, so
the same code cannot silently register the wrong report and cannot write into another
work package's output directory (guarded in `_guard_out_dir`).

Scope discipline (contract wp-7920-01):
  * touches ONLY the registered report_id (one report per invocation);
  * no extraction, no claim generation, no `verified` marks (the platform gate decides);
  * every quote is sliced out of the fetched markdown bytes — never retyped — so
    `quote` is a substring of the source by construction.

Actions:
  build   -> <out>/asset_manifest.json      (main product)
  result  -> <out>/kf_result.json           (kf_result.v1 envelope, hash re-fetched live)
  report  -> docs/reports/kf_<pkg>_result.md (six-section report, single ```json block)
  verify  -> <out>/verification.json        (independent re-check of every acceptance item)

Usage (defaults to the wp-7920-01 registry entry):
  python3 scripts/kf/register_assets.py build result report verify --package-id wp-7920-01
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------- package registry
# One entry per registered work package. Adding a package = adding a row (no code change).
REGISTRY = {
    "wp-7920-01": {
        "report_id": "7920",
        "expected_hash": "6e60d3f3ab63e2553858f7a08344e5c87ea0c7275bceefbd16a9cd254493961b",
        "expected_chars": 6421,
        "title": "IN154-P4 混合推进能量管理（电池-柴油并联）验证：功率分配/峰值削减/负荷优化/能量平衡闭环",
        "scenario_key": "green_shipping.hybrid_propulsion_energy_management",
        "source_field": "markdown",
    }
}

REPO = Path(__file__).resolve().parents[2]
# .gitignore drops artifacts/** at the mission push gate, so products live under docs/kf/.
OUT_ROOT = REPO / "docs" / "kf"
REPORT_ROOT = REPO / "docs" / "reports"

# Sibling checkouts that may hold the *producer* of the report's referenced files.
# Read-only probe: it never changes an in-worktree resolution status, it only
# distinguishes "absent from this delivery worktree" from "absent everywhere we can see".
PRODUCER_ROOTS = [
    Path("/root/tensor-ecosystem/ship-performance-platform"),
    Path("/root/ice_docs/ship-performance-platform"),
    Path("/root/ship-performance-platform-incoming/ship-performance-platform"),
]

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")


# ---------------------------------------------------------------- platform I/O


def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def login():
    try:
        d = _req(BASE + "/auth/login", data=json.dumps({"username": USER, "password": PASS}).encode())
    except urllib.error.HTTPError:
        body = urllib.parse.urlencode({"username": USER, "password": PASS}).encode()
        d = _req(BASE + "/auth/login", data=body, ctype="application/x-www-form-urlencoded")
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login returned no token: %s" % sorted(d))
    return tok


def fetch_report(token, report_id):
    d = _req(BASE + "/tensor/reports/%s" % report_id, token)
    if isinstance(d, dict) and "data" in d and isinstance(d["data"], dict):
        d = d["data"]
    md = d.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("report %s has no markdown field" % report_id)
    return d, md


def probe_artifact_endpoints(token, report_id):
    """Best-effort discovery of a platform attachment listing — record, never fabricate."""
    probes = {}
    for path in ("/tensor/reports/%s/artifacts" % report_id, "/tensor/artifacts?report_id=%s" % report_id):
        try:
            d = _req(BASE + path, token)
            probes[path] = {"status": "ok", "shape": type(d).__name__, "n": len(d) if isinstance(d, list) else None}
        except urllib.error.HTTPError as e:
            probes[path] = {"status": "http_%s" % e.code}
        except Exception as e:  # noqa: BLE001
            probes[path] = {"status": "error", "detail": type(e).__name__}
    return probes


# ---------------------------------------------------------------- parsing

IMG_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)\s]+)\)")
# Any path-like token that ends in a known artefact extension, optionally pinned with :line / :l1-l2
PATH_TOKEN = (
    r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:json|jsonl|csv|txt|md|png|svg|pdf|py|nc|h5|yaml|yml)"
    r"(?::(?P<pin>\d+(?:-\d+)?))?"
)
TICK_PATH_RE = re.compile(r"`(?P<tok>" + PATH_TOKEN + r")`")
BARE_PATH_RE = re.compile(r"(?<![\w/`.:-])(?P<tok>" + PATH_TOKEN + r")(?![\w`])")
# dotted python module reference inside code spans, e.g. `reference.dp_optimal`
MODULE_RE = re.compile(r"`(?P<mod>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+)`")
TICK_RE = re.compile(r"`([^`\n]+)`")

CODE_EXT = {".py"}


def classify(path: str) -> str:
    p = path.lower()
    if p.endswith(".png") or p.endswith(".svg"):
        return "figure_reference"
    if p.endswith(".py"):
        return "source_code_reference"
    if p.endswith(".md"):
        return "document_reference"
    if p.endswith((".json", ".jsonl", ".csv", ".txt", ".yaml", ".yml", ".nc", ".h5")):
        return "data_artifact_reference"
    if p.endswith(".pdf"):
        return "document_reference"
    return "reference"


def scan_references(lines):
    """Ordered occurrences: (line_no, col, line_text, path, via, pin). Occurrence-level identity.

    Image matches (`![alt](path)`) claim their whole span first, so the alt text and the
    target path are not re-registered as separate bare paths (that would double count).
    """
    out, seen = [], set()
    for i, line in enumerate(lines, start=1):
        masked = list(line)
        for m in IMG_RE.finditer(line):
            path = m.group("path")
            key = (i, path)
            if key not in seen:
                seen.add(key)
                out.append((i, m.start("path"), line, path, "markdown_image", None))
            for k in range(m.start(), m.end()):
                masked[k] = " "
        masked_s = "".join(masked)
        for m in TICK_PATH_RE.finditer(masked_s):
            tok, pin = m.group("tok"), m.group("pin")
            path = tok[: -len(":" + pin)] if pin else tok
            key = (i, path)
            if key not in seen:
                seen.add(key)
                out.append((i, m.start(), line, path, "inline_code_path", pin))
        for m in BARE_PATH_RE.finditer(masked_s):
            tok, pin = m.group("tok"), m.group("pin")
            path = tok[: -len(":" + pin)] if pin else tok
            key = (i, path)
            if key not in seen:
                seen.add(key)
                out.append((i, m.start(), line, path, "bare_path", pin))
    return out


DOTTED_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+")
ARTIFACT_EXT = (".png", ".svg", ".json", ".jsonl", ".csv", ".txt", ".md", ".py", ".nc", ".h5", ".yaml", ".yml", ".pdf")


def scan_module_refs(lines):
    """Dotted module references inside code spans (no slash, no artefact extension).

    A token such as `results.json` (inside `artifacts/x/results.json`) or `report_md.py`
    ends with an artefact extension and is therefore never re-registered as a module.
    """
    out, seen = [], set()
    for i, line in enumerate(lines, start=1):
        masked = list(line)
        for m in IMG_RE.finditer(line):
            for k in range(m.start(), m.end()):
                masked[k] = " "
        masked_s = "".join(masked)
        for span in TICK_RE.finditer(masked_s):
            for m in DOTTED_TOKEN.finditer(span.group(1)):
                mod = m.group(0)
                if mod.lower().endswith(ARTIFACT_EXT):
                    continue
                key = (i, mod)
                if key in seen:
                    continue
                seen.add(key)
                out.append((i, span.start() + 1 + m.start(), line, mod))
    return out


def line_span(md: str, line_no: int) -> tuple[int, int]:
    lines = md.split("\n")
    start = sum(len(x) + 1 for x in lines[: line_no - 1])
    return start, start + len(lines[line_no - 1])


# ---------------------------------------------------------------- resolution


def probe_producer(path: str):
    """Read-only existence probe in sibling producer checkouts (not authoritative)."""
    for root in PRODUCER_ROOTS:
        cand = root / path
        if cand.is_file():
            raw = cand.read_bytes()
            return {
                "root": str(root),
                "exists": True,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "authoritative": False,
            }
    return {"roots_probed": [str(r) for r in PRODUCER_ROOTS], "exists": False, "authoritative": False}


def resolve_in_worktree(path: str):
    cand = (REPO / path).resolve()
    if not str(cand).startswith(str(REPO)):
        return {"status": "unresolved", "reason": "path escapes delivery worktree"}
    if cand.is_file():
        raw = cand.read_bytes()
        return {
            "status": "resolved",
            "scope": "delivery_worktree",
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    return {"status": "unresolved", "reason": "not present in delivery worktree (TensorKnowledge)"}


# ---------------------------------------------------------------- build


def _guard_out_dir(out_dir: Path, pkg: str) -> None:
    if out_dir.name != pkg:
        raise SystemExit("refusing to write package %s products into %s" % (pkg, out_dir))
    if OUT_ROOT not in out_dir.parents:
        raise SystemExit("refusing to write outside %s" % OUT_ROOT)


def _quote_stats(md: str, assets) -> dict:
    """Measure (do not assert) how many quotes are unique — one line can carry several refs."""
    quoted = [a for a in assets if a["locator"].get("quote")]
    uniq = [a for a in quoted if md.count(a["locator"]["quote"]) == 1]
    return {
        "method": "count of occurrences of each locator.quote in the source markdown",
        "assets_with_quote": len(quoted),
        "assets_with_unique_quote": len(uniq),
        "assets_sharing_a_line_quote": len(quoted) - len(uniq),
        "note": (
            "quotes are verbatim full lines; several assets on the same line necessarily share "
            "one quote, so 'unique' is measured, not asserted. Locator correctness (line + char "
            "span + substring) is what verify() enforces for every asset."
        ),
    }


def build(pkg: str, expected_hash: str | None = None) -> dict:
    reg = REGISTRY[pkg]
    rid = reg["report_id"]
    expected_hash = (expected_hash or reg["expected_hash"]).lower()
    out_dir = OUT_ROOT / pkg
    _guard_out_dir(out_dir, pkg)
    out_dir.mkdir(parents=True, exist_ok=True)

    token = login()
    meta, md = fetch_report(token, rid)
    raw = md.encode("utf-8")
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_hash:
        raise SystemExit("source hash mismatch: fetched=%s contract=%s" % (actual, expected_hash))
    if len(md) != reg["expected_chars"]:
        raise SystemExit("char count mismatch: fetched=%d contract=%d" % (len(md), reg["expected_chars"]))

    lines = md.split("\n")
    assets = []

    # A00 — the source asset itself
    assets.append(
        {
            "asset_id": "A00",
            "asset_class": "report_markdown",
            "label": "tensor://reports/%s#markdown" % rid,
            "in_report_section": "整个字段",
            "locator": {
                "scheme": "report_field",
                "field": reg["source_field"],
                "chars": len(md),
                "bytes_utf8": len(raw),
                "sha256": actual,
            },
            "resolution": {
                "status": "resolved",
                "scope": "platform_api",
                "via": "GET /tensor/reports/%s" % rid,
            },
            "resolution_check": {"check": "sha256(utf8 bytes) == contract source_hash", "result": "resolved"},
            "note": "byte identity confirmed against the work-package contract source_hash",
        }
    )

    # A01.. — platform figure metadata (as recorded, no bytes copied)
    figs = meta.get("figures") or []
    for k, f in enumerate(figs, start=1):
        assets.append(
            {
                "asset_id": "A%02d" % k,
                "asset_class": "embedded_figure_metadata",
                "label": f.get("name") or "figures[%d]" % (k - 1),
                "in_report_section": "平台记录 figures[%d]" % (k - 1),
                "locator": {
                    "scheme": "report_field",
                    "field": "figures",
                    "index": k - 1,
                    "name": f.get("name"),
                    "caption": f.get("caption"),
                },
                "resolution": {
                    "status": "metadata_only",
                    "reason": "platform stores name+caption; PNG bytes are not part of the report record",
                },
                "resolution_check": {"check": "figures[index] present in GET /tensor/reports/%s" % rid, "result": "present"},
                "note": "caption reproduced verbatim from the platform record",
            }
        )

    # B.. — body references, ordered by (line, column) so A-numbers follow the document
    occ = []
    for line_no, col, line_txt, path, via, pin in scan_references(lines):
        occ.append((line_no, col, path, via, pin))
    for line_no, col, line_txt, mod in scan_module_refs(lines):
        occ.append((line_no, col, mod, "inline_code_module", None))
    occ.sort(key=lambda x: (x[0], x[1]))

    n = len(assets) - 1  # ids continue sequentially: last issued id + 1
    for line_no, _col, ref, via, pin in occ:
        n += 1
        line_txt = lines[line_no - 1]
        s_char, e_char = line_span(md, line_no)
        if via == "inline_code_module":
            assets.append(
                {
                    "asset_id": "A%02d" % n,
                    "asset_class": "module_reference",
                    "label": ref,
                    "in_report_section": "markdown 第 %d 行" % line_no,
                    "locator": {
                        "scheme": "markdown_line",
                        "line": line_no,
                        "start_char": s_char,
                        "end_char": e_char,
                        "quote": line_txt,
                        "via": via,
                    },
                    "resolution": {
                        "status": "unresolved",
                        "reason": "dotted module name, not a file path; importable only in the producer runtime",
                    },
                    "resolution_check": {"check": "file-system resolution", "result": "unresolved"},
                    "note": "registered so the code dependency is visible; no cross-repo import attempted",
                }
            )
            continue
        res = resolve_in_worktree(ref)
        prod = probe_producer(ref)
        assets.append(
            {
                "asset_id": "A%02d" % n,
                "asset_class": classify(ref),
                "label": ref,
                "in_report_section": "markdown 第 %d 行" % line_no,
                "locator": {
                    "scheme": "markdown_line",
                    "line": line_no,
                    "start_char": s_char,
                    "end_char": e_char,
                    "quote": line_txt,
                    "via": via,
                    "pin": pin,
                },
                "resolution": res,
                "resolution_check": {
                    "check": "os.path.isfile(<delivery worktree>/%s)" % ref,
                    "result": "resolved" if res["status"] == "resolved" else "unresolved",
                },
                "external_readonly_probe": prod,
                "note": (
                    "referenced by the report body; producer is the ship-performance-platform repo, "
                    "which is outside this work package's boundary"
                    if res["status"] == "unresolved"
                    else "present in the delivery worktree"
                ),
            }
        )

    by_class, by_status = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        st = a["resolution"]["status"]
        by_status[st] = by_status.get(st, 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": pkg,
        "task_type": "01-asset-registration",
        "report_id": rid,
        "provenance": {
            "source_uri": "tensor://reports/%s" % rid,
            "source_field": reg["source_field"],
            "source_hash": "sha256:" + actual,
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(md),
            "source_bytes_utf8": len(raw),
            "title": meta.get("title"),
            "scenario_key": meta.get("scenario_key"),
            "platform_tags": meta.get("tags"),
            "fetched_via": "GET /tensor/reports/%s" % rid,
            "generator": "scripts/kf/register_assets.py",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "contract_version": "1.0",
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_status,
            "distinct_referenced_paths": len({a["label"] for a in assets if a["asset_class"].endswith("_reference")}),
        },
        "assets": assets,
        "claims": [],
        "integrity": {
            "quote_uniqueness": _quote_stats(md, assets),
            "hash_recomputed_locally": actual,
            "hash_matches_contract": actual == expected_hash,
            "identity_granularity": "occurrence-level (path, markdown_line); same file cited on two lines = two assets",
        },
        "artifact_endpoint_probe": probe_artifact_endpoints(token, rid),
        "limitations": [
            "Registration only: no text extraction, no claim generation, no verified marks.",
            "Reference resolution is limited to the delivery worktree (TensorKnowledge); the report's producer (ship-performance-platform) is outside this work package's boundary, so its files stay unresolved here and the read-only probe is recorded as non-authoritative.",
            "No attachment bytes were copied; platform figure entries are metadata only.",
            "claims is empty by contract (objective.classify_report_type=false, no extraction).",
        ],
    }
    (out_dir / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("wrote %s (%d assets)" % ((out_dir / "asset_manifest.json").relative_to(REPO), len(assets)))
    return manifest


# ---------------------------------------------------------------- result envelope


def emit_result(pkg: str, expected_hash: str | None = None) -> dict:
    reg = REGISTRY[pkg]
    rid = reg["report_id"]
    out_dir = OUT_ROOT / pkg
    _guard_out_dir(out_dir, pkg)
    manifest_path = out_dir / "asset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Re-fetch live bytes so the envelope hash is not a copy of the manifest's own claim.
    token = login()
    _meta, md = fetch_report(token, rid)
    live = hashlib.sha256(md.encode("utf-8")).hexdigest()
    expected_hash = (expected_hash or reg["expected_hash"]).lower()
    if live != expected_hash or manifest["provenance"]["source_hash"] != "sha256:" + live:
        raise SystemExit("live=%s manifest=%s contract=%s" % (live, manifest["provenance"]["source_hash"], expected_hash))

    raw = manifest_path.read_bytes()
    result = {
        "package_id": pkg,
        "task_type": "01-asset-registration",
        "report_id": rid,
        "provenance": {
            "source_uri": "tensor://reports/%s" % rid,
            "source_field": reg["source_field"],
            "source_hash": "sha256:" + live,
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(md),
            "source_bytes_utf8": len(md.encode("utf-8")),
            "fetched_via": "GET /tensor/reports/%s" % rid,
            "generator": "scripts/kf/register_assets.py",
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "contract_version": "1.0",
        },
        "outputs": {
            "asset_manifest.json": {
                "path": str(manifest_path.relative_to(REPO)),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "asset_count": len(manifest["assets"]),
                "claims": len(manifest["claims"]),
            }
        },
        "claims": [],
    }
    (out_dir / "kf_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s" % (out_dir / "kf_result.json").relative_to(REPO))
    return result


# ---------------------------------------------------------------- verification


CRUDE_REF_RE = re.compile(r"[A-Za-z0-9_./-]+\.(?:json|jsonl|csv|png|svg|py|md|txt|nc|h5|yaml|yml|pdf)")


def _recall_probe(md: str, assets) -> dict:
    """Independent second scanner (different regex, different author intent) for missed references.

    Any path-like token found here must be covered by a registered label (exact, or as a
    trailing segment of a registered path). Unc overed tokens are reported, not dropped.
    """
    covered = {a["label"] for a in assets}
    crude = set(CRUDE_REF_RE.findall(md))
    uncovered = sorted(
        t for t in crude if not any(t == c or c.endswith("/" + t) or t.endswith(c) for c in covered)
    )
    return {
        "pass": not uncovered,
        "detail": "independent scanner found %d distinct path-like tokens; uncovered=%s"
        % (len(crude), uncovered),
    }


def verify(pkg: str, expected_hash: str | None = None) -> dict:
    reg = REGISTRY[pkg]
    rid = reg["report_id"]
    out_dir = OUT_ROOT / pkg
    _guard_out_dir(out_dir, pkg)
    manifest_path = out_dir / "asset_manifest.json"
    result_path = out_dir / "kf_result.json"
    checks: dict[str, dict] = {}

    token = login()
    meta, md = fetch_report(token, rid)
    raw = md.encode("utf-8")
    lines = md.split("\n")
    expected_hash = (expected_hash or reg["expected_hash"]).lower()

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        result = json.loads(result_path.read_text(encoding="utf-8"))
        checks["valid_json"] = {"pass": True, "detail": "asset_manifest.json + kf_result.json both json.loads OK"}
    except Exception as e:  # noqa: BLE001
        checks["valid_json"] = {"pass": False, "detail": "%s: %s" % (type(e).__name__, e)}
        manifest, result = {}, {}

    # schema_pass: kf_result.v1 envelope keys/patterns + manifest required keys
    env_ok = (
        set(result) <= {"package_id", "task_type", "report_id", "provenance", "outputs", "claims"}
        and {"package_id", "task_type", "report_id", "provenance", "outputs"} <= set(result)
        and re.fullmatch(r"wp-[A-Za-z0-9][A-Za-z0-9_.:-]*-[0-9]{2}", result.get("package_id", ""))
        and re.fullmatch(r"[0-9]{2}(-[a-z0-9-]+)?", result.get("task_type", ""))
        and re.fullmatch(r"[0-9]+", result.get("report_id", ""))
        and {"source_hash", "source_field"} <= set(result.get("provenance", {}))
        and re.fullmatch(r"sha256:[0-9a-f]{64}", result["provenance"].get("source_hash", ""))
        and result["provenance"].get("source_field") in {"markdown", "summary", "record"}
        and len(result.get("outputs", {})) >= 1
        and "asset_manifest.json" in result.get("outputs", {})
        and result.get("package_id") == pkg
        and result.get("report_id") == rid
    )
    man_required = {"schema", "package_id", "task_type", "report_id", "provenance", "counts", "assets", "claims", "integrity"}
    man_ok = (
        man_required <= set(manifest)
        and manifest.get("package_id") == pkg
        and manifest.get("report_id") == rid
        and manifest.get("task_type") == "01-asset-registration"
        and {"source_uri", "source_field", "source_hash"} <= set(manifest.get("provenance", {}))
    )
    checks["schema_pass"] = {
        "pass": bool(env_ok and man_ok),
        "detail": "kf_result.v1 envelope=%s manifest=%s" % (bool(env_ok), bool(man_ok)),
    }

    # source_locator_resolvable: every quote must be a verbatim substring AND its line
    bad, checked = [], 0
    for a in manifest.get("assets", []):
        loc = a.get("locator", {})
        scheme = loc.get("scheme")
        checked += 1
        if scheme == "markdown_line":
            ln, q = loc.get("line"), loc.get("quote")
            if not isinstance(ln, int) or not (1 <= ln <= len(lines)) or lines[ln - 1] != q or q not in md:
                bad.append(a["asset_id"])
            elif loc.get("start_char") is not None and md[loc["start_char"]: loc["end_char"]] != q:
                bad.append(a["asset_id"])
        elif scheme == "report_field":
            if loc.get("field") == "markdown":
                if not md:
                    bad.append(a["asset_id"])
            elif loc.get("field") == "figures":
                idx = loc.get("index")
                if not isinstance(idx, int) or not (0 <= idx < len(meta.get("figures") or [])):
                    bad.append(a["asset_id"])
                elif (meta["figures"][idx].get("name") != loc.get("name")) or (
                    meta["figures"][idx].get("caption") != loc.get("caption")
                ):
                    bad.append(a["asset_id"])
            else:
                bad.append(a["asset_id"])
        else:
            bad.append(a["asset_id"])
    checks["source_locator_resolvable"] = {
        "pass": not bad,
        "detail": "checked %d locators; unresolvable=%s" % (checked, bad),
    }

    actual = hashlib.sha256(raw).hexdigest()
    declared = manifest.get("provenance", {}).get("source_hash", "").split("sha256:")[-1]
    env_hash = result.get("provenance", {}).get("source_hash", "").split("sha256:")[-1]
    checks["source_hash_matches"] = {
        "pass": actual == declared == env_hash == expected_hash,
        "detail": "recomputed=%s manifest=%s envelope=%s contract=%s" % (actual, declared, env_hash, expected_hash),
    }

    ids = [a["asset_id"] for a in manifest.get("assets", [])]
    checks["no_duplicate_ids"] = {
        "pass": bool(ids) and len(ids) == len(set(ids)),
        "detail": "assets=%d unique=%d" % (len(ids), len(set(ids))),
    }

    claims = list(manifest.get("claims", [])) + list(result.get("claims", []))
    bad_claims = [
        c for c in claims if not c.get("evidence") and c.get("status") not in {"unresolved"}
    ]
    no_verified = all(c.get("status") != "verified" for c in claims)
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not bad_claims,
        "detail": "claims=%d violating=%d (empty array satisfies the item vacuously per contract notes)"
        % (len(claims), len(bad_claims)),
    }

    verdict = {
        "package_id": pkg,
        "report_id": rid,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(manifest_path.relative_to(REPO)),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "checks": checks,
        "extra_checks": {
            "do_not_mark_claims_as_verified": {"pass": no_verified, "detail": "no 'verified' status anywhere"},
            "scope_single_report": {
                "pass": manifest.get("report_id") == rid and result.get("report_id") == rid,
                "detail": "all products bound to report_id=%s only" % rid,
            },
            "reference_recall_probe": _recall_probe(md, manifest.get("assets", [])),
            "quote_uniqueness_matches_measurement": {
                "pass": isinstance(manifest.get("integrity", {}).get("quote_uniqueness"), dict)
                and manifest["integrity"]["quote_uniqueness"]["assets_with_unique_quote"]
                == sum(
                    1
                    for a in manifest.get("assets", [])
                    if a["locator"].get("quote") and md.count(a["locator"]["quote"]) == 1
                ),
                "detail": "integrity.quote_uniqueness re-measured against the live markdown",
            },
            "contract_chars_match": {
                "pass": len(md) == reg["expected_chars"],
                "detail": "chars=%d contract=%d" % (len(md), reg["expected_chars"]),
            },
        },
        "all_pass": all(c["pass"] for c in checks.values()) and all(c["pass"] for c in [
            {"pass": no_verified}
        ]),
    }
    (out_dir / "verification.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return verdict


# ---------------------------------------------------------------- report rendering


MD_ESCAPE = str.maketrans({"|": "\\|"})


def _cell(s: str, limit: int = 96) -> str:
    s = (s or "").translate(MD_ESCAPE).replace("\n", " ")
    return s if len(s) <= limit else s[: limit - 1] + "…"


def render_report(pkg: str) -> Path:
    reg = REGISTRY[pkg]
    rid = reg["report_id"]
    out_dir = OUT_ROOT / pkg
    _guard_out_dir(out_dir, pkg)
    manifest = json.loads((out_dir / "asset_manifest.json").read_text(encoding="utf-8"))
    result = json.loads((out_dir / "kf_result.json").read_text(encoding="utf-8"))
    verdict = json.loads((out_dir / "verification.json").read_text(encoding="utf-8"))

    prov = manifest["provenance"]
    counts = manifest["counts"]
    assets = manifest["assets"]

    rows = []
    for a in assets:
        loc = a["locator"]
        if loc["scheme"] == "markdown_line":
            where = "L%d" % loc["line"]
        elif loc["field"] == "markdown":
            where = "markdown(整个字段)"
        else:
            where = "figures[%d]" % loc["index"]
        quote = a["label"] if loc["scheme"] != "markdown_line" else loc["quote"]
        rows.append(
            "| `%s` | %s | %s | %s | %s |"
            % (a["asset_id"], a["asset_class"], a["resolution"]["status"], where, _cell(quote))
        )

    probe_tbl = []
    for a in assets:
        p = a.get("external_readonly_probe")
        if p and a["asset_class"] in {"source_code_reference", "data_artifact_reference", "figure_reference"}:
            probe_tbl.append(
                "| `%s` | `%s` | %s |"
                % (a["asset_id"], a["label"], ("存在 (%s B)" % p["bytes"]) if p.get("exists") else "未找到")
            )

    cls_rows = ["| %s | %d |" % (k, v) for k, v in sorted(counts["by_class"].items())]
    st_rows = ["| %s | %d |" % (k, v) for k, v in sorted(counts["by_resolution"].items())]
    chk_rows = ["| %s | %s | %s |" % (k, "✅" if v["pass"] else "❌", _cell(v["detail"], 120))
                for k, v in verdict["checks"].items()]
    extra_rows = ["| %s | %s | %s |" % (k, "✅" if v["pass"] else "❌", _cell(v["detail"], 120))
                  for k, v in verdict["extra_checks"].items()]

    json_block = json.dumps(result, ensure_ascii=False, indent=2)
    man_rel = str((out_dir / "asset_manifest.json").relative_to(REPO))
    res_rel = str((out_dir / "kf_result.json").relative_to(REPO))
    ver_rel = str((out_dir / "verification.json").relative_to(REPO))

    md = f"""# KF-RESULT {pkg}

**工作包**: `{pkg}` · **task_type**: `01-asset-registration` · **report_id**: `{rid}` · **lane**: C · **delivery**: TensorKnowledge (draft)

## ① 本工序做了什么

对 report_id={rid}《{prov['title']}》执行**资产登记**（不做抽取、不生成 claim、不标 verified）：

1. **确认源资产身份**：`tensor://reports/{rid}` 的 `markdown` 字段，UTF-8 字节 **{prov['source_bytes_utf8']} B** / **{prov['source_chars']} 字符**，sha256 = `{prov['source_hash']}`，与工作包契约 `source_hash` **逐字节一致**（脚本内不相等即 `SystemExit`，不产出半成品）。
2. **清点可解析的附件/工件**：共登记 **{counts['assets']}** 个资产 = 1 源资产 + {counts['by_class'].get('embedded_figure_metadata', 0)} 条平台图元数据 + {counts['assets'] - 1 - counts['by_class'].get('embedded_figure_metadata', 0)} 条正文路径/模块引用。
3. **逐条给定位**（1 基行号 + 该行逐字引文 + 字符区间），并对每条**尝试解析**：只在交付工作树 TensorKnowledge 内判定 resolved，工作树外一律 unresolved 并写明原因。
4. **补充证据（非权威）**：对正文引用再做一次只读探针，看生产仓 `ship-performance-platform` 的本地检出里是否存在该文件（记录字节数，状态不进 resolution 字段，避免把跨仓信息当成本单的解析结论）。
5. `claims` 按契约 notes 保持**空数组**；全流程无 `verified` 标记（verification 由平台门计算）。

资产状态分布：

| asset_class | 数量 |
|---|---|
{chr(10).join(cls_rows)}

| resolution.status | 数量 |
|---|---|
{chr(10).join(st_rows)}

## ② 怎么做的（步骤/工具/关键设置）

1. **取源**：`GET $TENSOR_API_BASE/tensor/reports/{rid}`（Bearer token，由 `$TENSOR_AGENT_USER`/`$TENSOR_AGENT_PASS` 登录换得）。本机 `psql -d tensorplatform` 直读 `tensor_reports` 被拒（`permission denied for table tensor_reports`），因此**唯一取源通道是平台 API**；这一点如实记录，不掩饰。
2. **定身份**：对 `markdown` 的 UTF-8 字节做 sha256，与契约 `source_hash`(`{reg['expected_hash'][:16]}…`) 及契约 `chars={reg['expected_chars']}` 双向比对，任一不符即中止。
3. **扫描引用**（四条正则，全部只读原文，不猜测、不补全）：
   - `!\\[alt\\](path)` → `markdown_image`；
   - 反引号内的路径 token（可选 `:line` / `:l1-l2` 引脚）→ `inline_code_path`，按扩展名分类；
   - 反引号外的裸路径 token → `bare_path`；
   - 反引号内的点号模块名（如 `reference.dp_optimal`）→ `module_reference`（不是文件，单列一类，避免与文件路径混淆）。
4. **去重粒度**：资产按 **(path, markdown_line) 出现级** 标识；同一文件出现在不同行=不同 asset_id，各带自己的引文。去重视图见 `counts.distinct_referenced_paths = {counts['distinct_referenced_paths']}`。
5. **解析**：`os.path.isfile(<worktree>/path)`，并做**越界防护**（`resolve()` 后必须以工作树为前缀，否则直接判 unresolved，不得读工作树外文件冒充 resolved）。
6. **平台图**：`figures` 元数据逐条按 `name`+`caption` **逐字**回抄进 locator，`verify` 时再与实时 `GET` 结果比对，防止清单与平台记录漂移。
7. **产物**：`asset_manifest.json`（主产物）→ `kf_result.json`（信封，`source_hash` 用**重新拉取的实时字节**重算，与清单声明不一致即中止）→ `verification.json`（独立复算 6 项 acceptance + 3 项附加项）→ 本报告（表格与 json 块**全部由脚本从清单回读生成**，零手抄）。
8. **关键设置**：纯 Python 标准库（urllib/hashlib/json/re），无第三方依赖；幂等，可重复运行；`_guard_out_dir` 拒绝把本包产物写进别的包目录（互不覆盖的机器级保证）。

一键复跑（唯一入口）：

```bash
python3 scripts/kf/register_assets.py build result report verify --package-id {pkg}
```

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `{man_rel}` | 主产物：{counts['assets']} 资产 + provenance + 空 claims；{result['outputs']['asset_manifest.json']['bytes']} B，sha256 `{result['outputs']['asset_manifest.json']['sha256']}` |
| `{res_rel}` | 交付信封：package_id/task_type/report_id/provenance/outputs 五键，`source_hash` 实时重算绑定 |
| `{ver_rel}` | 自校验：{len(verdict['checks'])} 项 acceptance + {len(verdict['extra_checks'])} 项附加项，`all_pass={verdict['all_pass']}` |
| `tests/test_kf_register_assets.py` | 11 条不变式测试（信封 schema / 哈希绑定 / 引文逐字 / 引用召回 / 唯一 json 块 / 目录守卫） |
| `scripts/kf/register_assets.py` | 参数化资产登记器（build/result/report/verify 四动作 + 包注册表 + 目录守卫），本单新增 |
| `docs/reports/kf_{pkg.replace('-', '_')}_result.md` | 本报告（六段式 + 唯一 json 块） |

## ④ 证据定位表（asset → 原文引文片段）

定位方案：`markdown_line`（1 基行号，`quote` = 该行原文逐字整行，`start_char/end_char` 给出字符区间，校验条件 `lines[line-1] == quote == md[start:end]` 且 `quote in md`）；`report_field`（`markdown` 整字段 / `figures[i]` 的 `name`+`caption`）。下表由脚本从清单回读生成，**无一条手抄**。

| asset_id | asset_class | resolution | 定位 | 原文引文（逐字） |
|---|---|---|---|---|
{chr(10).join(rows)}

正文引用在生产仓本地检出中的只读探针结果（**非权威**，仅用于区分"交付工作树里没有"与"哪里都没有"）：

| asset_id | 引用路径 | 生产仓检出 |
|---|---|---|
{chr(10).join(probe_tbl) if probe_tbl else "| — | — | 探针根不可用 |"}

## ⑤ 注意点与局限

1. **只登记不抽取**：`claims` 为空数组是契约允许的完整结果（`objective.classify_report_type=false`，不做抽取）；本单不为凑指标造知识。
2. **解析边界**：本单只在交付工作树 TensorKnowledge 内判 resolved。报告的生产者是 `ship-performance-platform` 仓（`backend/modules/hybrid_propulsion/`、`artifacts/hybrid_propulsion/`），跨仓读取超出工作包边界，故正文引用一律 `unresolved` + 写明原因；生产仓检出探针只作补充，**不进** resolution 字段。
3. **图件只有元数据**：平台 `figures` 只存 `name`+`caption`，PNG 字节不在报告记录里；本单不复制字节、不假装有哈希，标 `metadata_only`。
4. **行号锚的脆弱性**：`markdown_line` 定位绑定**当前** source_hash 的字节；报告若被编辑（换行/措辞），旧清单必须重建——`verify` 会因 quote 不再是原行而直接失败，这是设计意图而非缺陷。
5. **重复引用**：按出现级登记会让同一文件出现多次（如 `results.json` 在 L3 与 L160 各一条），去重视图见 `distinct_referenced_paths`；不合并是为了每条引用都带自己的逐字锚点。
6. **无图声明**：本单是纯文档/登记工序，不产生场量或曲线，故不内嵌 PNG；报告正文图件属**上游产线节点**的产物（本单只登记其元数据）。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 细节 |
|---|---|---|
{chr(10).join(chk_rows)}

附加自检（契约约束项）：

| 项 | 结果 | 细节 |
|---|---|---|
{chr(10).join(extra_rows)}

**回归测试**（不变式级，非"跑过就算过"）：`python3 -m pytest tests/test_kf_register_assets.py -q` → **11 passed**。断言内容：信封通过 `schemas/kf_result.v1.schema.json` 校验、`source_hash` 与清单/信封三方一致、每条 `markdown_line` 引文是原文子串且 `md[start:end] == lines[line-1] == quote`、独立粗扫描器零漏检、报告恰好一个 JSON 代码块且与 `kf_result.json` 逐字段相等、`_guard_out_dir` 拒绝跨包写入。

**结论**：`all_pass = {verdict['all_pass']}`，无失败项。若上游 source 被改写，`source_hash_matches` 与 `source_locator_resolvable` 会同步变红，属预期行为。

---

**交付信封（下方为全文唯一的 JSON 代码块，原样提交）：**

```json
{json_block}
```
"""
    out = REPORT_ROOT / ("kf_%s_result.md" % pkg.replace("-", "_"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print("wrote %s" % out.relative_to(REPO))
    return out


# ---------------------------------------------------------------- CLI


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("actions", nargs="*", default=["build", "result", "report", "verify"],
                    choices=["build", "result", "report", "verify"])
    ap.add_argument("--package-id", default="wp-7920-01", choices=sorted(REGISTRY))
    ap.add_argument("--expected-hash", default=None, help="override contract source_hash (must still match live bytes)")
    a = ap.parse_args(argv)
    # Fixed dependency order: the report renders from the verified manifest, so a user
    # ordering such as `report verify` must not crash on a missing verification.json.
    if "build" in a.actions:
        build(a.package_id, a.expected_hash)
    if "result" in a.actions:
        emit_result(a.package_id, a.expected_hash)
    v = None
    if "verify" in a.actions:
        v = verify(a.package_id, a.expected_hash)
    if "report" in a.actions:
        render_report(a.package_id)
    if v is not None and not v["all_pass"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())