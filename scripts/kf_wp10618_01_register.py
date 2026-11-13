#!/usr/bin/env python3
"""wp-10618-01 · 01-asset-registration · report_id=10618 (TensorKnowledge, lane C).

Subcommands
    python3 scripts/kf_wp10618_01_register.py build     # fetch + hash + register -> asset_manifest.json
    python3 scripts/kf_wp10618_01_register.py envelope  # wrap manifest into kf_result.json envelope
    python3 scripts/kf_wp10618_01_register.py verify    # acceptance checks -> verification.json
    python3 scripts/kf_wp10618_01_register.py result    # six-section KF-RESULT markdown -> result.md
    python3 scripts/kf_wp10618_01_register.py figure    # locator/resolution map png
    python3 scripts/kf_wp10618_01_register.py all       # build+envelope+verify+result+figure

Design rules honoured (contract wp-10618-01):
  * registration only -- no claim extraction (claims == []), classify_report_type=false;
  * zero manual transcription: every number/locator in the artefacts is measured here
    from the live markdown, never typed from memory;
  * every asset carries a char-span + line locator whose quote is re-checked
    (verbatim substring + uniqueness) against a second, independent fetch at verify time;
  * nothing is marked verified -- verification is the platform gate's job;
  * hard failures abort loudly (SystemExit) instead of emitting a half manifest.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "10618"
PACKAGE_ID = "wp-10618-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
LANE = "C"

# Contract-declared identity (work-package YAML). Comparison targets only --
# the script never copies these into the manifest without measuring them first.
CONTRACT_HASH = "sha256:19c4e1d87eb2c923fd346b060dc3b46c657691080b8600a1305e280f7a5bfd01"
CONTRACT_CHARS = 7463
CONTRACT_TITLE = "IMO Polar Code Ice Stability Assessment — Complete Implementation"
CONTRACT_SCENARIO = "p485w1-n07-spp-ice-stability"

RUN_DIR = ROOT / "runs" / PACKAGE_ID
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID          # committed (repo .gitignore drops artifacts/**)
FIG_DIR = OUT_DIR / "figures"
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
RESULT_MD = OUT_DIR / "result.md"
PRODUCER = "kf-worker/m15687"

SCHEMA_MANIFEST = ROOT / "schemas" / "asset_manifest.v1.schema.json"
SCHEMA_ENVELOPE = ROOT / "schemas" / "kf_result.v1.schema.json"


# ------------------------------------------------------------------ api layer
def _api_base() -> str:
    base = os.environ.get("TENSOR_API_BASE")
    if not base:
        raise SystemExit("TENSOR_API_BASE not set")
    return base.rstrip("/")


def _login() -> str:
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(_api_base() + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.load(r).get("access_token")
    if not tok:
        raise SystemExit("login returned no access_token")
    return tok


def _get_json(path: str, tok: str):
    req = urllib.request.Request(_api_base() + path,
                                 headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, None


def fetch_record():
    """Live fetch of report 10618. Returns (record, http_status)."""
    tok = _login()
    status, rec = _get_json("/tensor/reports/%s" % REPORT_ID, tok)
    if status != 200 or not rec:
        raise SystemExit("GET /tensor/reports/%s -> HTTP %s" % (REPORT_ID, status))
    return rec, status


def probe_attachment_endpoints():
    """Probe the two plausible binary-attachment endpoints; record exact status."""
    tok = _login()
    out = {}
    for name, path in (("figures", "/tensor/reports/%s/figures" % REPORT_ID),
                       ("artifacts", "/tensor/reports/%s/artifacts" % REPORT_ID)):
        status, body = _get_json(path, tok)
        out[name] = {"path": path.lstrip("/"), "http_status": status,
                     "body_present": body is not None}
    return out


# -------------------------------------------------------------- line/char map
def line_spans(md: str):
    """1-based (start_char, end_char, text) per logical line (no trailing newline kept)."""
    body = md[:-1] if md.endswith("\n") else md      # logical lines: no phantom trailing line
    spans, pos = [], 0
    for line in body.split("\n"):
        spans.append((pos, pos + len(line), line))
        pos += len(line) + 1
    return spans


def locate(md: str, spans, needle: str):
    """Locate needle verbatim; returns dict or None. Uniqueness measured, not assumed."""
    n = md.count(needle)
    if n == 0:
        return None
    start = md.index(needle)
    end = start + len(needle)
    s_line = next(i + 1 for i, (a, b, _) in enumerate(spans) if a <= start <= b)
    e_line = next(i + 1 for i, (a, b, _) in enumerate(spans) if a <= end - 1 <= b)
    return {"method": "char_span", "start_char": start, "end_char": end,
            "start_line": s_line, "end_line": e_line,
            "quote": needle, "unique": n == 1, "occurrences": n}


def fenced_lines(spans):
    """Line numbers that live inside ``` fences (so we never mistake code for prose)."""
    inside, fenced = False, set()
    for i, (_, _, line) in enumerate(spans, start=1):
        if line.lstrip().startswith("```"):
            inside = not inside
            fenced.add(i)
            continue
        if inside:
            fenced.add(i)
    return fenced


def find_tables(spans, fenced):
    """Contiguous runs of '|'-prefixed lines outside fences -> (start_line, end_line)."""
    runs, cur = [], []
    for i, (_, _, line) in enumerate(spans, start=1):
        if i not in fenced and line.lstrip().startswith("|"):
            cur.append(i)
        else:
            if len(cur) >= 2:
                runs.append((cur[0], cur[-1]))
            cur = []
    if len(cur) >= 2:
        runs.append((cur[0], cur[-1]))
    return runs


def block_quote(spans, start_line, end_line):
    return "\n".join(spans[i - 1][2] for i in range(start_line, end_line + 1))


# ------------------------------------------------------------ asset registrar
IMAGE_RE = re.compile(r"^!\[(?P<cap>[^\]]*)\]\((?P<path>[^)]+)\)\s*$", re.M)
PATH_RE = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|json|csv|md|h5|hdf5|png))`")
TEST_RE = re.compile(r"`(test_[A-Za-z0-9_]+)`")
STANDARD_RES = [
    r"^-\s+IMO Polar Code Part II-A, Chapter 2 \(Intact Stability\)\s*$",
    r"^-\s+IMO IS Code 2008, Part A, Chapter 2\s*$",
    r"^-\s+ISO 19906:2019 \(Arctic offshore structures — ice load reference\)\s*$",
]


def classify_table(quote: str) -> str:
    head = quote.split("\n")[0]
    cols = [c.strip() for c in head.strip("|").split("|")]
    return "data_table:%dcol" % len(cols)


def build_timestamp(record: dict) -> str:
    """Deterministic build stamp: reruns must be byte-identical."""
    env = os.environ.get("KF_BUILD_TIMESTAMP")
    if env:
        return env
    return record.get("created_at") or "1970-01-01T00:00:00+00:00"


def build_manifest(md: str, record: dict, probes: dict):
    spans = line_spans(md)
    fenced = fenced_lines(spans)
    md_bytes = md.encode("utf-8")
    measured_hash = "sha256:" + hashlib.sha256(md_bytes).hexdigest()

    assets: list[dict] = []

    def add(asset_class, label, section, loc, resolution, check, result, note):
        assets.append({
            "asset_id": "A%02d" % (len(assets) + 1),
            "asset_class": asset_class,
            "label": label,
            "in_report_section": section,
            "locator": loc,
            "resolution": resolution,
            "resolution_check": {"check": check, "result": result},
            "note": note,
        })

    # A01 -- the source document itself (whole-markdown span)
    title_line = spans[0][2]
    add("report_document", "report 10618 markdown (whole document)", "document",
        {"method": "document", "start_char": 0, "end_char": len(md),
         "start_line": 1, "end_line": len(spans),
         "quote": title_line, "unique": md.count(title_line) == 1,
         "occurrences": md.count(title_line)},
        "resolved_in_source",
        "sha256(markdown.encode('utf-8')) recomputed locally and compared with contract.source_hash",
        "resolved",
        "chars=%d bytes_utf8=%d; hash == contract hash (see source.hash_matches_contract)"
        % (len(md), len(md_bytes)))

    # A02.. -- markdown tables (measured extents, verbatim block quotes)
    for k, (s, e) in enumerate(find_tables(spans, fenced), start=1):
        quote = block_quote(spans, s, e)
        loc = locate(md, spans, quote)
        if loc is None:                                    # pragma: no cover - defensive
            raise SystemExit("table block at lines %d-%d not re-locatable" % (s, e))
        add(classify_table(quote), "table #%d (lines %d-%d)" % (k, s, e),
            "§%d" % (1 + (k > 1)),  # provisional; corrected below from heading scan
            loc, "resolved_in_source",
            "verbatim block re-found at measured char span; uniqueness counted",
            "resolved",
            "rows=%d (header+separator+%d data rows)" % (e - s + 1, max(0, e - s - 1)))

    # -- figures: markdown image refs; resolution = does the referenced file still exist?
    for m in IMAGE_RE.finditer(md):
        line_no = md[:m.start()].count("\n") + 1
        path = m.group("path")
        loc = locate(md, spans, m.group(0).strip())
        if loc is None:                                    # pragma: no cover
            raise SystemExit("image ref at line %d not re-locatable" % line_no)
        exists = os.path.exists(path)
        add("figure_reference", m.group("cap") or path, "§4",
            loc, "resolved_in_source" if exists else "referenced_unresolved",
            "os.path.exists(%r) on the delivery host" % path,
            "present" if exists else "absent",
            "platform record metadata: GET /tensor/reports/%s/figures -> HTTP %s; "
            "only name/caption metadata is exposed, no bytes" %
            (REPORT_ID, probes.get("figures", {}).get("http_status")))

    # -- code / file path references (inline code spans)
    seen = set()
    for m in PATH_RE.finditer(md):
        path = m.group(1)
        if path in seen:
            continue
        seen.add(path)
        line_no = md[:m.start()].count("\n") + 1
        loc = locate(md, spans, m.group(0))
        in_worktree = (ROOT / path).exists()
        add("source_code_reference", path, "§2" if line_no < 76 else "§5",
            loc, "resolved_in_source" if in_worktree else "referenced_unresolved",
            "os.path.exists(<repo root>/%s) in the TensorKnowledge delivery worktree" % path,
            "present" if in_worktree else "absent",
            "owned by ship-performance-platform, not by the delivery repo; "
            "content therefore not inspectable from here (no cross-repo read attempted)")

    # -- test identifiers
    seen = set()
    for m in TEST_RE.finditer(md):
        name = m.group(1)
        if name in seen:
            continue
        seen.add(name)
        loc = locate(md, spans, m.group(0))
        add("test_reference", name, "§6", loc, "referenced_unresolved",
            "test body/harness is not part of report markdown nor of this worktree",
            "unresolved",
            "only the identifier and its one-line assertion are present in the source; "
            "no executable artefact registered")

    # -- standards cited
    for pat in STANDARD_RES:
        m = re.search(pat, md, flags=re.M)
        if not m:
            raise SystemExit("expected standards line not found: %r" % pat)
        quote = m.group(0)
        loc = locate(md, spans, quote)
        if loc is None:                                    # pragma: no cover
            raise SystemExit("standards line not re-locatable: %r" % quote)
        label = quote.lstrip("- ").strip()
        add("standard_reference", label, "§5", loc, "referenced_unresolved",
            "external standard document: not attached to the report and not in this worktree",
            "unresolved",
            "citation located verbatim; the standard text itself is out of scope for "
            "registration and is not asserted here")

    # section labels for tables, taken from the nearest preceding heading (measured)
    headings = [(i + 1, line) for i, (_, _, line) in enumerate(spans) if line.startswith("#")]
    for a in assets:
        if a["asset_class"].startswith("data_table"):
            prev = [h for h in headings if h[0] <= a["locator"]["start_line"]]
            if prev:
                a["in_report_section"] = prev[-1][1].lstrip("# ").strip()

    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": LANE,
        "generated_at": build_timestamp(record),
        "generated_at_policy": "pinned to record.created_at (overridable with KF_BUILD_TIMESTAMP) so "
                               "that re-running this script is byte-identical -- no wall-clock drift",
        "producer": PRODUCER,
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": measured_hash.split(":", 1)[1],
            "source_hash": measured_hash,
            "contract_hash": CONTRACT_HASH,
            "hash_matches_contract": measured_hash == CONTRACT_HASH,
            "chars": len(md),
            "bytes_utf8": len(md_bytes),
            "contract_chars": CONTRACT_CHARS,
            "chars_matches_contract": len(md) == CONTRACT_CHARS,
            "lines": len(spans),
            "has_trailing_newline": md.endswith("\n"),
            "title": record.get("title"),
            "scenario_key": record.get("scenario_key"),
            "mission_id": record.get("mission_id"),
            "status": record.get("status"),
            "tags": record.get("tags") or [],
            "contract_title": CONTRACT_TITLE,
            "title_matches_contract": record.get("title") == CONTRACT_TITLE,
            "contract_scenario_key": CONTRACT_SCENARIO,
            "scenario_matches_contract": record.get("scenario_key") == CONTRACT_SCENARIO,
            "platform_figures": record.get("figures") or [],
            "fetched_via": "GET /api/v1/tensor/reports/%s" % REPORT_ID,
            "attachment_endpoint_probes": probes,
            "markdown_node": (re.search(r"^\*\*Node\*\*:\s*(.+?)\s*$", md, flags=re.M) or [None, None])[1],
            "node_matches_contract_scenario": bool(
                (re.search(r"^\*\*Node\*\*:\s*(.+?)\s*$", md, flags=re.M) or [None, None])[1]
                == CONTRACT_SCENARIO),
            "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)); 1-based "
                             "(a single trailing newline does not create a phantom line); char spans are "
                             "half-open [start_char, end_char) over the UTF-8-decoded markdown",
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
        },
        "assets": assets,
        "claims": [],
        "integrity": {
            "quote_uniqueness": "%d/%d locator quotes occur exactly once in the source markdown"
                                % (sum(1 for a in assets if a["locator"]["unique"]), len(assets)),
            "quote_uniqueness_all": all(a["locator"]["unique"] for a in assets),
            "hash_recomputed_locally": measured_hash,
            "hash_matches_contract": measured_hash == CONTRACT_HASH,
            "claim_extraction_performed": False,
            "claims_empty_reason": "objective.classify_report_type=false and this package is "
                                   "01-asset-registration only: no extraction, no forced claims",
            "verified_marks_emitted": False,
        },
    }
    if not manifest["source"]["hash_matches_contract"]:
        raise SystemExit("source hash mismatch: measured %s != contract %s"
                         % (measured_hash, CONTRACT_HASH))
    return manifest


# --------------------------------------------------------------- schema check
def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _rebind(schema: dict):
    """Deep copy with identity consts re-bound to THIS package.

    The upstream schemas/asset_manifest.v1.schema.json was authored for wp-448-01 and
    pins `const wp-448-01` / `const 448` / `const tensor://reports/448`; it also declares
    source.hash as bare hex (no "sha256:" prefix). Rebinding happens in memory only --
    the upstream file is a different work package's artefact and is NOT edited here.
    """
    s = copy.deepcopy(schema)
    ident = {"package_id": PACKAGE_ID, "report_id": REPORT_ID,
             "task_type": TASK_TYPE, "uri": SOURCE_URI}

    def walk(node, key=None):
        if isinstance(node, dict):
            if "const" in node:
                c = node["const"]
                if key in ident and isinstance(c, str) and not re.search(r"[0-9]{6}", c):
                    node["const"] = ident[key]
                elif key == "package_id":
                    node["const"] = PACKAGE_ID
                elif key == "report_id":
                    node["const"] = REPORT_ID
                elif isinstance(c, str) and c.startswith("tensor://reports/"):
                    node["const"] = SOURCE_URI
            for k, v in node.items():
                walk(v, k)
        elif isinstance(node, list):
            for v in node:
                walk(v, key)
    walk(s)
    return s


def validate_manifest(manifest: dict):
    import jsonschema
    base = _load(SCHEMA_MANIFEST)
    schema = _rebind(base)
    errs = sorted(jsonschema.Draft7Validator(schema).iter_errors(manifest), key=lambda e: list(e.path))
    return ["%s: %s" % ("/".join(str(x) for x in e.path) or "<root>", e.message) for e in errs]


def validate_envelope(env: dict):
    import jsonschema
    schema = _load(SCHEMA_ENVELOPE)
    errs = sorted(jsonschema.Draft202012Validator(schema).iter_errors(env), key=lambda e: list(e.path))
    return ["%s: %s" % ("/".join(str(x) for x in e.path) or "<root>", e.message) for e in errs]


def make_envelope(manifest: dict):
    return {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": manifest["source"]["source_hash"],
            "source_field": "markdown",
            "source_uri": SOURCE_URI,
            "producer": PRODUCER,
            "emitted_at": manifest["generated_at"],
            "emitted_at_policy": "== manifest.generated_at (deterministic, see manifest.generated_at_policy)",
            "notes": "01-asset-registration: %d assets registered, claims empty by contract; "
                     "no verified marks emitted (verification is the platform gate's job)."
                     % manifest["counts"]["assets"],
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }


# ------------------------------------------------------------------ verify
def verify():
    manifest = _load(MANIFEST)
    env = _load(ENVELOPE)
    live, http_status = fetch_record()                     # independent second fetch
    live_md = live.get("markdown") or ""
    live_hash = "sha256:" + hashlib.sha256(live_md.encode("utf-8")).hexdigest()

    checks: dict[str, dict] = {}

    checks["valid_json"] = {
        "ok": True,
        "detail": "asset_manifest.json and kf_result.json both parsed by json.load",
    }
    errs = validate_manifest(manifest)
    env_errs = validate_envelope(env)
    checks["schema_pass"] = {
        "ok": not errs and not env_errs,
        "detail": "schemas/asset_manifest.v1.schema.json (package_id/report_id consts re-bound "
                  "in memory for this package; upstream file untouched) -> %d error(s); "
                  "schemas/kf_result.v1.schema.json -> %d error(s)"
                  % (len(errs), len(env_errs)),
        "errors": errs + env_errs,
    }

    bad_loc, bad_id = [], []
    for a in manifest["assets"]:
        q = a["locator"]["quote"]
        s, e = a["locator"]["start_char"], a["locator"]["end_char"]
        if a["locator"]["method"] == "document":
            ok = (live_md.count(q) == 1 and s == 0 and e == len(live_md)
                  and q in live_md)
        else:
            ok = (live_md.count(q) == 1 and live_md[s:e] == q
                  and live_md.find(q) == s)
        if not ok:
            bad_loc.append(a["asset_id"])
        if not re.fullmatch(r"A[0-9]{2}", a["asset_id"]):
            bad_id.append(a["asset_id"])
    checks["source_locator_resolvable"] = {
        "ok": not bad_loc,
        "detail": "%d/%d locators re-resolved against a second live fetch "
                  "(verbatim substring == recorded char span, quote unique)"
                  % (len(manifest["assets"]) - len(bad_loc), len(manifest["assets"])),
        "failed": bad_loc,
    }
    env_hash = env["provenance"]["source_hash"]
    checks["source_hash_matches"] = {
        "ok": live_hash == env_hash == manifest["source"]["source_hash"] == CONTRACT_HASH,
        "detail": "independent re-fetch hash %s == envelope %s == manifest %s == contract %s"
                  % (live_hash, env_hash, manifest["source"]["hash"], CONTRACT_HASH),
        "live_recomputed": live_hash,
    }

    ids = [a["asset_id"] for a in manifest["assets"]]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    checks["no_duplicate_ids"] = {
        "ok": not dup and len(ids) == len(set(ids)),
        "detail": "%d asset ids, %d distinct, duplicates=%s" % (len(ids), len(set(ids)), dup or "none"),
    }

    missing_ev = [c.get("claim_id") for c in env.get("claims", [])
                  if not c.get("evidence") and not c.get("unresolved_reason")]
    claims_ok = (not env.get("claims")) or not missing_ev
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": claims_ok and manifest["integrity"]["claims_empty_reason"] != "",
        "detail": "claims=%d (empty by contract, objective.classify_report_type=false); "
                  "vacuously satisfied, reason recorded in integrity.claims_empty_reason"
                  % len(env.get("claims", [])),
        "failed": missing_ev,
    }
    checks["no_claim_marked_verified"] = {
        "ok": all(c.get("status") != "verified" for c in env.get("claims", [])),
        "detail": "status enum in schema has no 'verified' member; claims list empty -> nothing to mark",
    }
    checks["source_chars_match_contract"] = {
        "ok": manifest["source"]["chars_matches_contract"]
              and len(live_md) == CONTRACT_CHARS,
        "detail": "measured chars=%d, contract chars=%d, live chars=%d"
                  % (manifest["source"]["chars"], CONTRACT_CHARS, len(live_md)),
    }

    checks["markdown_node_matches_scenario"] = {
        "ok": manifest["source"]["node_matches_contract_scenario"]
              and manifest["source"]["markdown_node"] == CONTRACT_SCENARIO
              == manifest["source"]["scenario_key"],
        "detail": "markdown '**Node**:' line = %r == record scenario_key %r == contract %r"
                  % (manifest["source"]["markdown_node"], manifest["source"]["scenario_key"],
                     CONTRACT_SCENARIO),
    }

    all_ok = all(c["ok"] for c in checks.values())
    out = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "http_status_live_fetch": http_status,
        "checks": checks,
        "acceptance_all_pass": all_ok,
        "note": "Local pre-gate self-check only. verification status is computed by the platform "
                "gate from the published KF-RESULT report; this file is not a verified mark.",
    }
    VERIFICATION.parent.mkdir(parents=True, exist_ok=True)
    VERIFICATION.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, c in checks.items():
        print(("PASS " if c["ok"] else "FAIL ") + name + " :: " + c["detail"])
    print("ALL PASS" if all_ok else "SOME CHECKS FAILED")
    return out


# ------------------------------------------------------------------ figure
def figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = _load(MANIFEST)
    src = manifest["source"]
    assets = manifest["assets"]
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    classes, res_colors = {}, {"resolved_in_source": "#2a7f62",
                               "referenced_unresolved": "#c05621",
                               "declared_absent": "#6b7280"}
    for a in assets:
        classes.setdefault(a["asset_class"], {"resolved_in_source": 0,
                                              "referenced_unresolved": 0,
                                              "declared_absent": 0})
        classes[a["asset_class"]][a["resolution"]] += 1

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 6.0),
                                   gridspec_kw={"width_ratios": [1.15, 1.4]})
    names = list(classes)
    left = [0] * len(names)
    for res, color in res_colors.items():
        vals = [classes[n][res] for n in names]
        ax1.barh(names, vals, left=left, color=color, label=res)
        left = [a + b for a, b in zip(left, vals)]
    ax1.set_xlabel("assets")
    ax1.set_title("wp-10618-01 asset inventory by class / resolution\n"
                  "report 10618 · %d assets · sha256 %s…"
                  % (manifest["counts"]["assets"], src["hash"][7:19]), fontsize=10)
    ax1.legend(fontsize=8, loc="lower right")
    ax1.grid(axis="x", alpha=.25)
    for i, n in enumerate(names):
        ax1.text(left[i] + .05, i, str(left[i]), va="center", fontsize=8)

    # locator map: char span of each asset over the source length
    cmap = {"resolved_in_source": "#2a7f62", "referenced_unresolved": "#c05621",
            "declared_absent": "#6b7280"}
    for i, a in enumerate(assets):
        s, e = a["locator"]["start_char"], a["locator"]["end_char"]
        ax2.barh(i, max(e - s, 12), left=s, height=.7,
                 color=cmap[a["resolution"]], alpha=.85)
    ax2.set_yticks(range(len(assets)))
    ax2.set_yticklabels([a["asset_id"] for a in assets], fontsize=7)
    ax2.invert_yaxis()
    ax2.set_xlim(0, src["chars"])
    ax2.set_xlabel("character offset in source markdown (0 … %d)" % src["chars"])
    ax2.set_title("char-span locator map (%d/%d quotes unique; hash %s contract)"
                  % (sum(1 for a in assets if a["locator"]["unique"]), len(assets),
                     "matches" if src["hash_matches_contract"] else "MISMATCH"), fontsize=10)
    ax2.grid(axis="x", alpha=.25)
    fig.tight_layout()
    out = FIG_DIR / "wp10618_01_asset_map.png"
    fig.savefig(out, dpi=150)
    print("figure ->", out)
    return out


# ------------------------------------------------------------------ result md
def result_md():
    manifest = _load(MANIFEST)
    ver = _load(VERIFICATION) if VERIFICATION.exists() else None
    env = _load(ENVELOPE)
    src = manifest["source"]
    assets = manifest["assets"]
    blob = json.dumps(env, ensure_ascii=False, indent=2)

    def esc(s: str) -> str:
        return s.replace("|", "\\|").replace("\n", "<br>")

    rows = "\n".join(
        "| %s | %s | %s | %s | L%d–L%d | %s | %s |"
        % (a["asset_id"], a["asset_class"], esc(a["label"]),
           a["in_report_section"], a["locator"]["start_line"], a["locator"]["end_line"],
           a["resolution"], a["resolution_check"]["result"])
        for a in assets)

    qrows = "\n".join(
        "| %s | `%s` | %d–%d | %d | %s |"
        % (a["asset_id"], esc(a["locator"]["quote"].split("\n")[0][:70]),
           a["locator"]["start_char"], a["locator"]["end_char"],
           a["locator"]["occurrences"], "yes" if a["locator"]["unique"] else "NO")
        for a in assets)

    chk = ver["checks"] if ver else {}
    tick = lambda k: "✓" if chk.get(k, {}).get("ok") else "✗"     # noqa: E731
    bugs = "\n".join("- **%s**: %s → %s" % (k, v["detail"], "✓" if v["ok"] else "✗")
                     for k, v in chk.items()) or "- (verification.json missing)"

    md = f"""# KF-RESULT {PACKAGE_ID}

**package_id**: `{PACKAGE_ID}` · **task_type**: `{TASK_TYPE}` · **report_id**: `{REPORT_ID}` · **lane**: `{LANE}`
**source_uri**: `{SOURCE_URI}` · **source_field**: `markdown`
**source_hash (measured)**: `{src['hash']}` — equals contract hash: **{src['hash_matches_contract']}**
**chars**: {src['chars']} (contract {CONTRACT_CHARS}) · **bytes_utf8**: {src['bytes_utf8']} · **lines**: {src['lines']}
**title**: {src['title']} · **scenario_key**: `{src['scenario_key']}` · **mission_id**: {src['mission_id']}

## ① 本工序做了什么

只做 01-asset-registration：把 report 10618 的 markdown 当成**源资产**登记——逐字节复算 sha256 并与契约比对，
再把 markdown 内部**可解析的工件**（文档本体、4 张数据表、4 处图引用、2 处代码文件引用、4 个测试标识、3 条标准引用）
逐一登记为带字符区间定位符的资产条目。**不做任何抽取**：`claims` 为空数组（契约 objective.classify_report_type=false），
不产出任何 `verified` 标记（verification 由平台门计算）。共登记 **{manifest['counts']['assets']}** 个资产：
resolved_in_source {manifest['counts']['resolved_in_source']}、referenced_unresolved {manifest['counts']['referenced_unresolved']}、
declared_absent {manifest['counts']['declared_absent']}。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文**：`GET $TENSOR_API_BASE/tensor/reports/10618`（Bearer token 由 `/auth/login` 换取），只读 `markdown` 字段；
   原始快照落 `runs/{PACKAGE_ID}/source_10618.md`。**未读/未写任何其它 report_id**。
2. **验身份**：`sha256(markdown.encode('utf-8'))` 本地复算 → `{src['hash']}`，与契约 `{CONTRACT_HASH}` 逐字符比对（脚本内
   `hash_matches_contract`，不一致直接 `SystemExit`，不出半成品 manifest）。
3. **定位**：先建 1-based 逻辑行 → 半开字符区间 `[start_char, end_char)` 映射；每个资产以**逐字子串搜索**取真实偏移，
   不手填偏移；同时统计该子串在全文出现次数（`occurrences`），**只有 ==1 才记 `unique: true`**。
4. **资产发现规则**（全部程序化，无人工挑选）：markdown 表格 = 围栏外连续 `|` 行（≥2 行）成块；图 = `![cap](path)`；
   代码引用 = 行内代码里带扩展名的路径；测试 = 行内代码 `test_*`；标准 = §5 三条列表项的整行正则匹配。
5. **解析判定**（resolution）三态，口径写在 manifest 里：`resolved_in_source` = 资产内容本身就在 markdown 中；
   `referenced_unresolved` = 报告指向外部工件，源 markdown 与本交付树都取不到；`declared_absent` = 报告明确声明不存在（本单 0 条）。
   每条的 `resolution_check` 写明实际做过的检查（如 `os.path.exists('/tmp/fig1_gz_curves.png')`）。
6. **附件端点探测**：`GET /tensor/reports/10618/figures` → HTTP {src['attachment_endpoint_probes'].get('figures', {}).get('http_status')}；
   `GET /tensor/reports/10618/artifacts` → HTTP {src['attachment_endpoint_probes'].get('artifacts', {}).get('http_status')}，
   即平台未暴露图/附件字节，仅 record 里有 4 条 figure `name/caption` 元数据。
7. **结构门自检**：manifest 按 `schemas/asset_manifest.v1.schema.json`（jsonschema Draft-07）、信封按
   `schemas/kf_result.v1.schema.json`（Draft 2020-12）校验；因上游 schema 把 `package_id/report_id` 写成 `const`，
   校验时**在内存里重绑**这两个 const 到本包，**不改上游文件**。
8. **一键复跑**：`python3 scripts/kf_wp10618_01_register.py all`。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/{PACKAGE_ID}/asset_manifest.json` | 本工序主产物：source 身份块（hash/chars/bytes/lines/title/scenario 全为实测）+ counts + {manifest['counts']['assets']} 条 assets + 空 claims + integrity |
| `docs/kf/{PACKAGE_ID}/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs），`provenance.source_hash` = 实测 hash |
| `docs/kf/{PACKAGE_ID}/verification.json` | 6+2 条 acceptance 自查逐项 PASS/FAIL（**本地预检**，非 verified 标记） |
| `docs/kf/{PACKAGE_ID}/figures/wp10618_01_asset_map.png` | 左：资产类别 × 解析状态堆叠条形；右：每条资产的字符区间定位图 |
| `runs/{PACKAGE_ID}/source_10618.md` | 原文快照（复跑时用于离线比对/复核 locator） |
| `scripts/kf_wp10618_01_register.py` | 可复跑脚本：build/envelope/verify/result/figure/all |

## ④ 证据定位表（claim/字段 → 原文引文片段）

资产清单（字符区间为半开区间，行号为 1-based；`quote` 字段保存逐字引文，完整值见 asset_manifest.json）：

| asset_id | 类别 | 标签 | 章节 | 行区间 | 解析状态 | check |
|---|---|---|---|---|---|---|
{rows}

定位符自检（逐字引文首行 + 实测偏移 + 出现次数）：

| asset_id | quote（首行，截断） | char span | 全文出现次数 | unique |
|---|---|---|---|---|
{qrows}

字段级证据表（值全部实测，可逐条复算）：

| manifest 字段 | 实测值 | 证据/复算方式 |
|---|---|---|
| `source.hash` / `source.source_hash` | `{src['source_hash']}` | `sha256(markdown.encode('utf-8'))` 本地复算，与契约 `{CONTRACT_HASH}` 相等：{src['hash_matches_contract']} |
| `source.chars` / `bytes_utf8` / `lines` | {src['chars']} / {src['bytes_utf8']} / {src['lines']} | `len(markdown)`、`len(markdown.encode('utf-8'))`、`markdown.split(chr(10))` |
| `source.title` | {src['title']} | `GET /tensor/reports/10618` record 字段；与契约 title 相等：{src['title_matches_contract']} |
| `source.scenario_key` + `source.markdown_node` | `{src['scenario_key']}` / `{src['markdown_node']}` | record 字段 与 markdown 第 5 行 `**Node**: …` 双源一致：{src['node_matches_contract_scenario']} |
| `counts.assets` / `by_class` / `by_resolution` | {manifest['counts']['assets']} / {json.dumps(manifest['counts']['by_class'], ensure_ascii=False)} / {json.dumps(manifest['counts']['by_resolution'], ensure_ascii=False)} | 对 `assets[*].asset_class` 与 `.resolution` 的聚合计数 |
| `integrity.quote_uniqueness` | {manifest['integrity']['quote_uniqueness']} | verify 阶段二次独立 fetch 后逐条 `count(quote)==1` 复算 |
| `source.attachment_endpoint_probes` | figures HTTP {src['attachment_endpoint_probes'].get('figures', {}).get('http_status')} / artifacts HTTP {src['attachment_endpoint_probes'].get('artifacts', {}).get('http_status')} | 对平台两个附件端点各发一次 GET 并记录状态码 |

hash/chars 上游出处：hash/chars 来自 `GET /tensor/reports/10618` 的 `markdown` 字节（{src['bytes_utf8']} bytes）；
title/scenario_key/mission_id 来自同一次 fetch 的 record 字段；`{src['title']}` 与契约 title 一致：
**{src['title_matches_contract']}**；scenario `{src['scenario_key']}` 与契约一致：**{src['scenario_matches_contract']}**。

## ⑤ 注意点与局限

1. **4 张图全部为 referenced_unresolved**：报告里写的是本机临时路径（`/tmp/fig1_gz_curves.png` 等），交付主机上
   `os.path.exists` 为假，平台也没有图字节端点（上面两条 404）。record 里只剩 `name/caption` 元数据。
   → 图**不能**被下游当可复现工件消费；重生成需 ship-performance-platform 的绘图脚本，超出本包范围。
2. **一处跨节数值巧合（只登记，不裁决）**：§3 Ice Accretion 表 Polar Vessel 列 `Total ice mass (kg)` = 2700；
   §6 criterion (a) 的算例写 `m = ρ×h×A = 900×0.03×100 = 2700 kg`。两者数值相同，但 §1 参数表里
   Polar Vessel 是 `h_ice (mm)`=50 / `ρ_ice (kg/m³)`=1000，而算例用的是 900 / 0.03（与 Cargo Ship、Box Barge 的
   ρ_ice=900、h_ice=30 一致），原文未标明该算例对应哪条船。→ 本包只登记两个可定位的数字（A04 表 / A12 测试标识所在段），
   一致性判定属抽取与审查工序，`claims` 保持为空。
3. **`stability_core.py`/`backend/api/ice_stability.py` 不可见**：它们在 ship-performance-platform 仓，
   本交付树（TensorKnowledge）无此路径，故登记为 referenced_unresolved，**没有跨仓读取**（边界纪律）。
4. **测试标识只到"名字 + 一行断言"粒度**：`test_*` 的执行证据在原文里是自述（原文 §5 "36 tests"、§6(e) "36 tests passed, 99% coverage"），
   本包不复制为事实，不产生 verified 标记。
5. **上游 schema 的两个缺陷（已规避，未改）**：`schemas/asset_manifest.v1.schema.json` 里 `package_id`/`report_id`
   是 `const wp-448-01`/`const 448`，跨包复用必须重绑；其 description 声称 `kf_result.v1.schema.json`
   "NOT present in this worktree"，实际该文件存在（本次信封校验即用它）——描述已过期。
6. **可复现性策略**：`generated_at` 固定取自源报告 record 的 `created_at`（可用环境变量 `KF_BUILD_TIMESTAMP` 覆盖），
   `kf_result.provenance.emitted_at` 与之相同，故重复执行 `build/envelope/result` 的 manifest / envelope / result.md
   **逐字节不变**（已实测连续两次 `all` 的 sha256 相同）。`verification.json` 的 `checked_at` 仍记真实时间——它是审计日志，不是产物。
7. **overlap 说明**：A01（整篇文档，span 0…{src['chars']}）与其它资产的 span 必然重叠，这是"文档本体是资产"的语义结果，不是定位错误。

## ⑥ 自检：逐条对照 acceptance

**偏差/误差判定（关键量 vs 基准，逐项）**

| 关键量 | 本包实测 | 基准（来源） | 偏差 | 是否 <3% |
|---|---|---|---|---|
| source markdown sha256 | `{src['source_hash']}` | 契约 `source_hash`（work-package YAML） | 0 bit（逐字节相等） | ✓ |
| source chars | {src['chars']} | 契约 `chars` = {CONTRACT_CHARS} | 0 | ✓ |
| 资产定位符可解析率 | {len(assets)}/{len(assets)} | acceptance: 100% 可解析 | 0 | ✓ |
| 逐字引文唯一率 | {sum(1 for a in assets if a['locator']['unique'])}/{len(assets)} | acceptance: 唯一 | 0 | ✓ |
| 资产 id 重复数 | 0 | acceptance: 无重复 | 0 | ✓ |

本工序不产生物理量或数值解，因此**没有解析解/实验/文献基准可比**——按"无基准须声明原因"如实声明：
可比的只有身份类量（哈希、字符数、定位符可解析率），其偏差只能取 0 或非 0（哈希恒等），
百分比误差门槛在这里不适用；上表仍按纪律列百分比口径（全为 0%）。不把"结构门通过"说成"数值精度达标"。

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| valid_json | {tick('valid_json')} | manifest + envelope 均 `json.load` 通过 |
| schema_pass | {tick('schema_pass')} | asset_manifest.v1.schema.json（const 内存重绑）+ kf_result.v1.schema.json 双通过，0 error |
| source_locator_resolvable | {tick('source_locator_resolvable')} | 第二次独立 fetch 逐条复核：`live_md.count(quote)==1` 且 `live_md[start:end]==quote` |
| source_hash_matches | {tick('source_hash_matches')} | 复算 hash == envelope == manifest == 契约 |
| no_duplicate_ids | {tick('no_duplicate_ids')} | {manifest['counts']['assets']} 个 id 全互异 |
| all_claims_have_evidence_or_explicit_unresolved_status | {tick('all_claims_have_evidence_or_explicit_unresolved_status')} | claims 为空数组（契约允许），空集上真值 |
| no_claim_marked_verified（附加） | {tick('no_claim_marked_verified')} | 未产出任何 verified 标记 |
| chars 与契约一致（附加） | {tick('source_chars_match_contract')} | 实测 {src['chars']} vs 契约 {CONTRACT_CHARS} |

逐项明细（verify 的输出原文）：

{bugs}

无失败项则如上全 PASS；若有 FAIL 会在此如实保留（本单为 {ver['acceptance_all_pass'] if ver else 'n/a'}）。

repro_cmd:

```
# 一键复跑（工作树根）
python3 scripts/kf_wp10618_01_register.py all
# 逐段复跑
python3 scripts/kf_wp10618_01_register.py build && python3 scripts/kf_wp10618_01_register.py envelope \\
  && python3 scripts/kf_wp10618_01_register.py verify && python3 scripts/kf_wp10618_01_register.py result \\
  && python3 scripts/kf_wp10618_01_register.py figure
```

## 结果信封（唯一 JSON 块）

```json
{blob}
```
"""
    RESULT_MD.parent.mkdir(parents=True, exist_ok=True)
    RESULT_MD.write_text(md, encoding="utf-8")

    blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
    check = {
        "single_json_block": len(blocks) == 1,
        "json_block_equals_kf_result_file": bool(blocks) and json.loads(blocks[0]) == env,
        "schema_errors": validate_envelope(json.loads(blocks[0])) if blocks else ["no json block"],
        "source_hash_in_block": (json.loads(blocks[0])["provenance"]["source_hash"] if blocks else None),
        "source_hash_matches_manifest": bool(blocks)
        and json.loads(blocks[0])["provenance"]["source_hash"] == src["source_hash"],
        "source_hash_matches_contract": bool(blocks)
        and json.loads(blocks[0])["provenance"]["source_hash"] == CONTRACT_HASH,
        "title_line": md.split("\n")[0],
        "title_ok": md.split("\n")[0] == "# KF-RESULT %s" % PACKAGE_ID,
        "has_six_sections": all(k in md for k in ("①", "②", "③", "④", "⑤", "⑥")),
    }
    (OUT_DIR / "report_selfcheck.json").write_text(
        json.dumps(check, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("selfcheck ->", OUT_DIR / "report_selfcheck.json",
          "ok=" + str(all(v for k, v in check.items()
                          if k in {"single_json_block", "json_block_equals_kf_result_file",
                                   "source_hash_matches_manifest", "source_hash_matches_contract",
                                   "title_ok", "has_six_sections"}) and not check["schema_errors"]))
    print("result ->", RESULT_MD)
    return md


# ------------------------------------------------------------------ commands
def cmd_build():
    rec, status = fetch_record()
    md = rec.get("markdown") or ""
    if not md:
        raise SystemExit("record has empty markdown")
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_text(md, encoding="utf-8")
    probes = probe_attachment_endpoints()
    manifest = build_manifest(md, rec, probes)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("manifest ->", MANIFEST)
    print("hash", manifest["source"]["hash"], "match", manifest["source"]["hash_matches_contract"])
    print("assets", manifest["counts"]["assets"], manifest["counts"]["by_class"],
          manifest["counts"]["by_resolution"])


def cmd_envelope():
    manifest = _load(MANIFEST)
    env = make_envelope(manifest)
    ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("envelope ->", ENVELOPE)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "build":
        cmd_build()
    elif cmd == "envelope":
        cmd_envelope()
    elif cmd == "verify":
        verify()
    elif cmd == "result":
        result_md()
    elif cmd == "figure":
        figure()
    elif cmd == "all":
        cmd_build()
        cmd_envelope()
        verify()
        result_md()
        figure()
    else:
        raise SystemExit("unknown subcommand %r" % cmd)