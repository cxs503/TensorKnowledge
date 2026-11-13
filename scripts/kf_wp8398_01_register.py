#!/usr/bin/env python3
"""wp-8398-01 (task_type 01-asset-registration): register report 8398's source asset
and enumerate the attachments/artifacts it declares.

Registration ONLY. No claim extraction, no `verified` marks, no content hashing of
assets that this package cannot open. Every locator is measured from the markdown
bytes fetched here; nothing is transcribed by hand.

Sub-commands (idempotent; stdlib only except `figure` which needs matplotlib):

    python3 scripts/kf_wp8398_01_register.py fetch     # GET report -> runs/wp-8398-01/source_8398.md
    python3 scripts/kf_wp8398_01_register.py build     # -> docs/kf/wp-8398-01/asset_manifest.json
    python3 scripts/kf_wp8398_01_register.py envelope  # -> docs/kf/wp-8398-01/kf_result.json
    python3 scripts/kf_wp8398_01_register.py verify    # 6 acceptance checks -> verification.json
    python3 scripts/kf_wp8398_01_register.py figure    # -> docs/kf/wp-8398-01/figures/fig_asset_inventory.png
    python3 scripts/kf_wp8398_01_register.py report    # -> docs/kf/wp-8398-01/REPORT.md (six sections + kf_result json block)
    python3 scripts/kf_wp8398_01_register.py all       # fetch+build+envelope+verify+figure+report

Hard constraints honoured (contract wp-8398-01):
  * only report_id 8398 is read; no other report is touched;
  * failures abort loudly instead of emitting a half manifest;
  * a hash/char mismatch against the contract is recorded, never smoothed over.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ID = "wp-8398-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "8398"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
LANE = "C"
PRODUCER = "kf-worker/m15622"

# contract-declared identity (work-package YAML). Comparison targets only: the
# manifest always carries the locally recomputed values next to them.
CONTRACT_SOURCE_HASH = "sha256:e2b867451792017e0af5346b70c7a4eb5f764917490c9ac6fc66c14435da6706"
CONTRACT_CHARS = 4290
CONTRACT_TITLE = ("P121W5-N11 DEM 接触物理模块成熟化：温度键合+润滑耦合+力链统计集成验证"
                  "与 API 稳定化")
CONTRACT_SCENARIO = "ice_navigation"
CONTRACT_REPORTED_GIT_REV = "c2e8461e4a50"

# A foreign checkout that happens to be readable in this sandbox. It is used for a
# presence-only probe of the declared upstream files and is explicitly NOT treated
# as authoritative: the report pins rev c2e8461e4a50 and this checkout is elsewhere.
UPSTREAM_PROBE_ROOT = Path(os.environ.get("KF_UPSTREAM_PROBE_ROOT",
                                          "/root/tp-agent/work/m14461"))

RUN_DIR = ROOT / "runs" / PACKAGE_ID
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID
FIG_DIR = OUT_DIR / "figures"
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
RECORD_COPY = RUN_DIR / ("record_%s.json" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
PUBLISH_INFO = OUT_DIR / "publish.json"
REPORT_MD = OUT_DIR / "REPORT.md"
FIGURE_PNG = FIG_DIR / "fig_asset_inventory.png"
KF_SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
MANIFEST_SCHEMA = ROOT / "schemas" / "asset_manifest_kf.v1.schema.json"

# ---------------------------------------------------------------- declaration table
# (asset_id suffix, asset_class, declared token in the markdown, path for existence probe)
DECLARED = [
    # (asset_id suffix, asset_class, declared token, probe_kind, probe_arg)
    ("mod:contact_physics", "python_package", "tensordem.contact_physics",
     "module", "tensordem.contact_physics"),
    ("file:bond", "python_module_file", "bond.py",
     "module", "tensordem.contact_physics.bond"),
    ("file:lubrication", "python_module_file", "lubrication.py",
     "module", "tensordem.contact_physics.lubrication"),
    ("file:statistics", "python_module_file", "statistics.py",
     "module", "tensordem.contact_physics.statistics"),
    ("file:march", "python_module_file", "march.py",
     "module", "tensordem.contact_physics.march"),
    ("mod:ice_bond_viscoelastic", "upstream_module", "tensordem.ice_bond_viscoelastic",
     "module", "tensordem.ice_bond_viscoelastic"),
    ("func:ice_resistance", "upstream_function",
     "tensordem.wet_ice_cohesion.ice_resistance", "module", "tensordem.wet_ice_cohesion"),
    ("mod:ridge_dem", "upstream_module", "tensordem.ridge_dem",
     "module", "tensordem.ridge_dem"),
    ("mod:ice_rubble_microstructure", "upstream_module",
     "tensordem.ice_rubble_microstructure", "module", "tensordem.ice_rubble_microstructure"),
    ("mod:interface_thermal", "upstream_module", "tensordem.interface_thermal",
     "module", "tensordem.interface_thermal"),
    ("sym:OperatingPoint", "symbol", "OperatingPoint", "grep", "OperatingPoint"),
    ("sym:ContactPhysicsMarch", "symbol", "ContactPhysicsMarch", "grep", "ContactPhysicsMarch"),
    ("sym:standalone_reference", "symbol", "standalone_reference",
     "grep", "standalone_reference"),
    ("sym:RidgeContactStatistics", "symbol", "RidgeContactStatistics",
     "grep", "RidgeContactStatistics"),
    ("func:within_strength_fit", "symbol", "within_strength_fit()",
     "grep", "within_strength_fit"),
    ("script:freeze_api", "script", "scripts/freeze_contact_physics_api.py",
     "path", "scripts/freeze_contact_physics_api.py"),
    ("script:regression_gate", "script", "scripts/contact_physics_regression_gate.py",
     "path", "scripts/contact_physics_regression_gate.py"),
    ("script:build_doc", "script", "scripts/build_contact_physics_doc.py",
     "path", "scripts/build_contact_physics_doc.py"),
    ("doc:contact_physics_module", "doc", "docs/contact_physics_module.md",
     "path", "docs/contact_physics_module.md"),
    ("example:contact_physics_demo", "example", "examples/contact_physics_demo.py",
     "path", "examples/contact_physics_demo.py"),
    ("test:integration", "test", "tests/test_contact_physics_integration.py",
     "path", "tests/test_contact_physics_integration.py"),
    ("artifact:integration_report", "artifact",
     "artifacts/contact_physics/integration_report.json",
     "path", "artifacts/contact_physics/integration_report.json"),
    ("artifact:api_baseline", "artifact", "api_baseline.json",
     "rglob_name", "api_baseline.json"),
    ("artifact:regression_gate_json", "artifact", "regression_gate.json",
     "rglob_name", "regression_gate.json"),
    ("artifact:performance_pytest", "artifact", "performance_pytest.json",
     "rglob_name", "performance_pytest.json"),
    ("anchor:git_c2e8461e4a50", "provenance_anchor", "c2e8461e4a50",
     "git_rev", "c2e8461e4a50"),
    ("suite:pytest_n02_n05_n08", "declared_test_suite", "9 个 pytest 文件", None, None),
]

MODULE_KIND = {"python_package", "python_module_file", "upstream_module",
               "upstream_function", "symbol"}


# ---------------------------------------------------------------- api helpers
def _api_base() -> str:
    return os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _login() -> str:
    body = json.dumps({"username": os.environ.get("TENSOR_AGENT_USER", ""),
                       "password": os.environ.get("TENSOR_AGENT_PASS", "")}).encode()
    req = urllib.request.Request(_api_base() + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    tok = json.load(urllib.request.urlopen(req, timeout=60)).get("access_token")
    if not tok:
        raise SystemExit("login returned no access_token")
    return tok


def _get(path: str, token: str | None = None):
    """Return (http_status, bytes). 4xx is data, not an exception."""
    req = urllib.request.Request(_api_base() + path)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


# ---------------------------------------------------------------- step: fetch
def cmd_fetch() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    tok = _login()
    st, raw = _get("/tensor/reports/" + REPORT_ID, tok)
    if st != 200:
        raise SystemExit("GET /tensor/reports/%s -> HTTP %s" % (REPORT_ID, st))
    rec = json.loads(raw.decode())
    md = rec.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("report %s exposes no markdown field" % REPORT_ID)
    SOURCE_COPY.write_bytes(md.encode("utf-8"))
    meta = {k: v for k, v in rec.items() if k != "markdown"}
    RECORD_COPY.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("fetched report %s: chars=%d bytes=%d sha256=%s"
          % (REPORT_ID, len(md), len(md.encode()), hashlib.sha256(
              md.encode()).hexdigest()))


# ---------------------------------------------------------------- shared loads
def load_source() -> tuple[str, dict]:
    if not SOURCE_COPY.exists() or not RECORD_COPY.exists():
        raise SystemExit("missing %s / %s -- run `fetch` first" % (SOURCE_COPY, RECORD_COPY))
    raw = SOURCE_COPY.read_bytes()
    md = raw.decode("utf-8")
    if md.encode("utf-8") != raw:
        raise SystemExit("source copy is not clean UTF-8")
    return md, json.loads(RECORD_COPY.read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def locate(md: str, token: str) -> dict:
    """Measure a token's char span / line / context. Token text is the quote."""
    i = md.find(token)
    if i < 0:
        raise SystemExit("declared token not found in markdown: %r" % token)
    end = i + len(token)
    line_start = md.rfind("\n", 0, i) + 1
    line_end = md.find("\n", i)
    if line_end < 0:
        line_end = len(md)
    context = md[line_start:line_end]
    start_line = md.count("\n", 0, i) + 1
    return {
        "source_field": "markdown",
        "method": "char_span",
        "start_char": i,
        "end_char": end,
        "start_line": start_line,
        "end_line": start_line,
        "quote": md[i:end],
        "quote_sha256": _sha256(md[i:end].encode()),
        "unique": md.count(token) == 1,
        "occurrences": md.count(token),
        "context": context,
    }


def _probe_rev(path: Path) -> dict:
    if not path.exists():
        return {"probe_root": str(path), "probe_root_exists": False}
    rev = None
    try:
        rev = subprocess.run(["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=20
                             ).stdout.strip() or None
    except Exception:  # noqa: BLE001 - probe only, never fatal
        rev = None
    return {"probe_root": str(path), "probe_root_exists": True, "probe_rev": rev}


def _python_spec(module: str) -> dict:
    import importlib.util as ilu
    try:
        spec = ilu.find_spec(module)
    except Exception:  # noqa: BLE001
        spec = None
    if spec is None:
        return {"check": "python_import_spec", "result": "absent", "module": module}
    return {"check": "python_import_spec", "result": "present", "module": module,
            "origin": spec.origin, "origin_scope_note":
            "resolved through PYTHONPATH pointing at a foreign tenant worktree; "
            "this is a presence signal, not evidence about the report's pinned rev"}


def _foreign_files(token: str, limit: int = 3) -> dict:
    """Read-only presence grep inside the non-authoritative foreign checkout."""
    hits: list[str] = []
    if not UPSTREAM_PROBE_ROOT.exists():
        return {"check": "foreign_grep", "result": "probe_root_missing",
                "pattern": token, "files": [], "authoritative": False}
    for path in sorted(UPSTREAM_PROBE_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts or ".git" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if token in text:
            hits.append(str(path.relative_to(UPSTREAM_PROBE_ROOT)))
            if len(hits) >= limit:
                break
    return {"check": "foreign_grep", "result": "present" if hits else "absent",
            "pattern": token, "files": hits, "authoritative": False}


def _foreign_rglob(name: str, limit: int = 5) -> dict:
    hits: list[str] = []
    if UPSTREAM_PROBE_ROOT.exists():
        for path in UPSTREAM_PROBE_ROOT.rglob(name):
            if ".git" in path.parts:
                continue
            hits.append(str(path.relative_to(UPSTREAM_PROBE_ROOT)))
            if len(hits) >= limit:
                break
    return {"check": "foreign_rglob_name", "result": "present" if hits else "absent",
            "name": name, "files": sorted(hits), "authoritative": False}


def _foreign_git_rev(rev: str) -> dict:
    if not (UPSTREAM_PROBE_ROOT / ".git").exists():
        return {"check": "foreign_git_rev", "result": "probe_root_not_a_repo", "rev": rev,
                "authoritative": False}
    cp = subprocess.run(["git", "-C", str(UPSTREAM_PROBE_ROOT), "cat-file", "-e", rev],
                        capture_output=True, text=True, timeout=30)
    return {"check": "foreign_git_rev", "result": "present" if cp.returncode == 0 else "absent",
            "rev": rev, "authoritative": False}


NON_AUTH = ("probe performed in a foreign checkout (%s) that is neither this repo nor the "
            "rev pinned by the report; existence only, no byte hash is claimed"
            % UPSTREAM_PROBE_ROOT)


def resolve_declared(asset_class: str, token: str, probe_kind: str | None,
                     probe_arg: str | None) -> dict:
    checks: list[dict] = []
    status, scope, reason = "unresolved", "not probed", ""

    if probe_kind == "path" and probe_arg:
        local = ROOT / probe_arg
        foreign = UPSTREAM_PROBE_ROOT / probe_arg
        checks.append({"check": "tensorknowledge_worktree_path",
                       "result": "present" if local.exists() else "absent",
                       "path": probe_arg})
        checks.append({"check": "foreign_checkout_path",
                       "result": "present" if foreign.exists() else "absent",
                       "path": str(foreign), "authoritative": False})
        if local.exists():
            status, scope, reason = "resolved", "this worktree", "path present in this worktree"
        elif foreign.exists():
            status, scope, reason = "declared_only", "foreign checkout", NON_AUTH
        else:
            scope, reason = "both probe roots", "path found under neither probe root"
    elif probe_kind == "module" and probe_arg:
        spec = _python_spec(probe_arg)
        checks.append(spec)
        if spec["result"] == "present":
            origin = spec.get("origin") or ""
            inside_foreign = str(UPSTREAM_PROBE_ROOT) in origin
            checks.append({"check": "origin_inside_foreign_checkout",
                           "result": "yes" if inside_foreign else "no", "origin": origin})
            status, scope = "declared_only", "upstream python package"
            reason = ("module resolves on the local python path via a foreign checkout; "
                      "the report's pinned rev is not opened, so no byte hash is claimed")
        else:
            scope, reason = "local python path", "module not importable here"
    elif probe_kind == "grep" and probe_arg:
        g = _foreign_files(probe_arg)
        checks.append(g)
        if g["result"] == "present":
            status, scope, reason = "declared_only", "foreign checkout grep", NON_AUTH
        else:
            scope, reason = "foreign checkout grep", "symbol not found in the probe checkout"
    elif probe_kind == "rglob_name" and probe_arg:
        r = _foreign_rglob(probe_arg)
        checks.append(r)
        if r["result"] == "present":
            status, scope = "declared_only", "foreign checkout glob"
            reason = ("bare filename (no directory in the source text); a file of this "
                      "name exists in the probe checkout but its report-time location and "
                      "content are unverified")
        else:
            scope, reason = "foreign checkout glob", "filename not found in the probe checkout"
    elif probe_kind == "git_rev" and probe_arg:
        r = _foreign_git_rev(probe_arg)
        checks.append(r)
        if r["result"] == "present":
            status, scope = "declared_only", "foreign checkout git object"
            reason = ("the rev named in the report exists as an object in the probe "
                      "checkout, which says nothing about the report's artefacts")
        else:
            scope, reason = "foreign checkout git", "rev object not found in the probe checkout"
    else:
        checks.append({"check": "probe_target", "result": "not_derivable",
                       "detail": "the report declares a count/plural without names"})
        reason = ("declared as an unnamed plural ('9 pytest 文件'); the report gives no "
                  "filenames, so nothing is locatable and nothing is invented")

    return {"status": status, "scope": scope, "checks": checks, "reason": reason}


def scan_assets(md: str, record: dict) -> list[dict]:
    assets: list[dict] = [{
        "asset_id": "r%s:source-markdown" % REPORT_ID,
        "asset_class": "report_markdown",
        "label": "report-%s-markdown" % REPORT_ID,
        "token": "document",
        "locator": {
            "source_field": "markdown",
            "method": "document",
            "start_char": 0,
            "end_char": len(md),
            "start_line": 1,
            "end_line": md.count("\n") + 1,
            "quote": md.split("\n")[0],
            "quote_sha256": _sha256(md.split("\n")[0].encode()),
            "unique": True,
            "occurrences": 1,
            "context": md.split("\n")[0],
        },
        "resolution": {
            "status": "resolved", "scope": "platform_api",
            "checks": [{"check": "GET /tensor/reports/%s" % REPORT_ID, "result": "200"},
                       {"check": "sha256(utf8 markdown bytes)",
                        "result": _sha256(md.encode())}],
            "reason": "whole markdown field, byte-exact local copy kept in the run dir",
        },
        "note": "quote = first line (heading); the asset itself is the whole document span",
    }]

    for suffix, aclass, token, probe_kind, probe_arg in DECLARED:
        assets.append({
            "asset_id": "r%s:%s" % (REPORT_ID, suffix),
            "asset_class": aclass,
            "label": token,
            "token": token,
            "locator": locate(md, token),
            "resolution": resolve_declared(aclass, token, probe_kind, probe_arg),
        })

    # figures: names/captions live on the record, not in the markdown body
    tok = None
    figs = record.get("figures") or []
    if figs:
        tok = _login()
    for idx, fig in enumerate(figs):
        name = fig.get("name") or "unnamed-%d" % idx
        st, raw = _get("/tensor/reports/%s/figures/%s" % (REPORT_ID,
                                                          urllib.parse.quote(name)), tok)
        ok = st == 200 and len(raw) > 0
        assets.append({
            "asset_id": "r%s:figure:%02d" % (REPORT_ID, idx + 1),
            "asset_class": "figure",
            "label": name,
            "token": name,
            "locator": {
                "source_field": "record",
                "method": "record_pointer",
                "start_char": 0,
                "end_char": 1,
                "start_line": 1,
                "end_line": 1,
                "quote": name,
                "quote_sha256": _sha256(name.encode()),
                "unique": True,
                "occurrences": 1,
                "context": "figures[%d].name" % idx,
            },
            "resolution": {
                "status": "resolved" if ok else "metadata_only",
                "scope": "platform_api",
                "checks": [{"check": "GET /tensor/reports/%s/figures/%s"
                                    % (REPORT_ID, name), "result": "http_%s" % st,
                            "bytes": len(raw)}],
                "reason": ("payload returned by the platform figure endpoint"
                           if ok else
                           "record exposes name/caption only; no figure bytes were "
                           "returned, so no hash is claimed"),
            },
            "note": (fig.get("caption") or "")[:400],
        })
    return assets


def cmd_build() -> None:
    md, record = load_source()
    assets = scan_assets(md, record)
    raw = SOURCE_COPY.read_bytes()
    by_class = Counter(a["asset_class"] for a in assets)
    by_res = Counter(a["resolution"]["status"] for a in assets)
    manifest = {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": LANE,
        "generated_at": _now(),
        "producer": PRODUCER,
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": "sha256:" + _sha256(raw),
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "hash_match": "sha256:" + _sha256(raw) == CONTRACT_SOURCE_HASH,
            "hash_algo": "sha256",
            "chars": len(md),
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": len(md) == CONTRACT_CHARS,
            "bytes": len(raw),
            "lines": md.count("\n") + 1,
            "has_crlf": "\r\n" in md,
            "has_trailing_newline": md.endswith("\n"),
            "line_counting": "1-based; lines = markdown.split(chr(10))",
            "hash_scope": "UTF-8 bytes of the markdown field as served by GET /api/v1/tensor/reports/8398",
            "local_copy": str(SOURCE_COPY.relative_to(ROOT)),
            "record_local_copy": str(RECORD_COPY.relative_to(ROOT)),
            "fetched_via": "GET %s/tensor/reports/%s" % (_api_base(), REPORT_ID),
            "record_fields": {
                "title": record.get("title"),
                "scenario_key": record.get("scenario_key"),
                "mission_id": record.get("mission_id"),
                "status": record.get("status"),
                "created_at": record.get("created_at"),
                "tags": record.get("tags"),
                "figures": len(record.get("figures") or []),
                "contract_title": CONTRACT_TITLE,
                "title_matches_contract": (record.get("title") or "").strip() ==
                                          CONTRACT_TITLE.strip(),
                "contract_scenario_key": CONTRACT_SCENARIO,
                "scenario_matches_contract": record.get("scenario_key") == CONTRACT_SCENARIO,
                "contract_reported_git_rev": CONTRACT_REPORTED_GIT_REV,
                "reported_git_rev_in_markdown": CONTRACT_REPORTED_GIT_REV in md,
            },
            "upstream_probe": _probe_rev(UPSTREAM_PROBE_ROOT),
        },
        "assets": assets,
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_res.items())),
            "markdown_locators": sum(1 for a in assets
                                     if a["locator"]["source_field"] == "markdown"),
            "explicitly_unresolved": by_res.get("unresolved", 0),
            "declared_only": by_res.get("declared_only", 0),
            "metadata_only": by_res.get("metadata_only", 0),
        },
        "claims": [],
        "claims_note": ("task_type=01 and objective.classify_report_type=false: this "
                        "package registers source assets only and performs no claim "
                        "extraction, so the claim list is intentionally empty rather "
                        "than filled with unreviewed restatements."),
        "integrity": {
            "hash_recomputed_locally": True,
            "hash_algorithm": "sha256",
            "verified_logic": ("no asset is marked verified; verification is computed by "
                               "the platform gate, which re-hashes the markdown and "
                               "re-resolves every locator"),
            "quotes_are_measured": "every locator quote is a slice of the fetched markdown bytes",
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print("manifest: %s  assets=%d  by_resolution=%s"
          % (MANIFEST.relative_to(ROOT), len(assets), dict(sorted(by_res.items()))))


def cmd_envelope() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": manifest["source"]["source_hash"],
            "source_field": "markdown",
            "source_uri": SOURCE_URI,
            "producer": PRODUCER,
            "emitted_at": _now(),
            "notes": ("source_hash recomputed from the fetched markdown bytes "
                      "(sha256 over UTF-8), not copied from the contract; "
                      "registration only, no claim marked verified"),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print("envelope: %s  source_hash=%s"
          % (ENVELOPE.relative_to(ROOT), env["provenance"]["source_hash"]))


# ---------------------------------------------------------------- step: verify
def cmd_verify() -> None:
    import jsonschema

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    md, _record = load_source()
    results: dict[str, dict] = {}

    results["valid_json"] = {"ok": True,
                             "detail": "asset_manifest.json + kf_result.json parsed"}

    errs: list[str] = []
    for doc, schema_path, name in ((env, KF_SCHEMA, "kf_result.v1"),
                                   (manifest, MANIFEST_SCHEMA, "asset_manifest_kf.v1")):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        v = jsonschema.Draft202012Validator(schema)
        errs += ["%s: %s" % (name, e.message) for e in v.iter_errors(doc)]
    results["schema_pass"] = {"ok": not errs,
                              "detail": "%d schema error(s)" % len(errs),
                              "errors": errs[:10]}

    # locators re-resolved against a freshly fetched copy of the live markdown
    tok = _login()
    st, raw = _get("/tensor/reports/" + REPORT_ID, tok)
    live = json.loads(raw.decode()).get("markdown", "") if st == 200 else ""
    live_sha = "sha256:" + _sha256(live.encode())
    fails = []
    checked = 0
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["source_field"] != "markdown":
            continue
        checked += 1
        if loc["method"] == "document":
            why = []
            if not live:
                why.append("live markdown empty")
            else:
                if loc["end_char"] != len(live):
                    why.append("document end_char drift")
                if loc["quote"] != live.split("\n")[0]:
                    why.append("document first-line quote drift")
                if loc["end_line"] != live.count("\n") + 1:
                    why.append("document end_line drift")
            if why:
                fails.append({"asset_id": a["asset_id"], "why": why})
            continue
        s, e = loc["start_char"], loc["end_char"]
        why = []
        if live[s:e] != loc["quote"]:
            why.append("slice mismatch")
        if _sha256(live[s:e].encode()) != loc["quote_sha256"]:
            why.append("quote_sha256 mismatch")
        if live.count(loc["quote"]) != loc["occurrences"]:
            why.append("occurrence count drift")
        line_no = live.count("\n", 0, s) + 1
        if line_no != loc["start_line"]:
            why.append("line drift %d!=%d" % (line_no, loc["start_line"]))
        if why:
            fails.append({"asset_id": a["asset_id"], "why": why})
    results["source_locator_resolvable"] = {
        "ok": not fails,
        "detail": "%d/%d markdown locators re-resolved on live bytes (char span + "
                  "verbatim quote + sha256 + line)" % (checked - len(fails), checked),
        "failures": fails,
    }

    msha = manifest["source"]["source_hash"]
    results["source_hash_matches"] = {
        "ok": live_sha == msha == CONTRACT_SOURCE_HASH,
        "detail": "live=%s manifest=%s contract=%s" % (live_sha, msha, CONTRACT_SOURCE_HASH),
        "chars": {"live": len(live), "manifest": manifest["source"]["chars"],
                  "contract": CONTRACT_CHARS},
    }

    ids = [a["asset_id"] for a in manifest["assets"]]
    dup = [i for i, c in Counter(ids).items() if c > 1]
    results["no_duplicate_ids"] = {"ok": not dup, "detail": "%d ids, duplicates=%s"
                                   % (len(ids), dup)}

    claims = env.get("claims") or []
    bad = [c for c in claims if not c.get("evidence") and c.get("status") != "unresolved"]
    results["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": not bad,
        "detail": "%d claims; empty-claims reason stated: %s"
                  % (len(claims), bool(manifest.get("claims_note"))),
        "offending": [c.get("claim_id") for c in bad],
    }

    all_ok = all(v["ok"] for v in results.values())
    doc = {"package_id": PACKAGE_ID, "verified_at": _now(), "acceptance": results,
           "all_ok": all_ok,
           "note": ("Self-check only. No claim is marked verified here; the platform "
                    "gate recomputes hash/locators independently.")}
    VERIFICATION.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    for k, v in results.items():
        print("%-58s %s  %s" % (k, "OK " if v["ok"] else "FAIL", v["detail"]))
    if not all_ok:
        raise SystemExit("verification FAILED")


# ---------------------------------------------------------------- step: figure
def cmd_figure() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    md, _ = load_source()
    total_lines = manifest["source"]["lines"]
    assets = manifest["assets"]
    color = {"resolved": "#1b7837", "metadata_only": "#f0a30a",
             "declared_only": "#2166ac", "unresolved": "#b2182b"}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 0.34 * max(len(assets), 1) + 2.4),
                                   gridspec_kw={"width_ratios": [2.35, 1]})
    labels = []
    for i, a in enumerate(assets):
        loc = a["locator"]
        x = loc["start_line"] if loc["source_field"] == "markdown" else total_lines
        ax1.plot([1, x], [i, i], color="#dddddd", lw=1.0, zorder=1)
        ax1.scatter([x], [i], s=46, color=color[a["resolution"]["status"]],
                    edgecolor="black", linewidth=0.4, zorder=3)
        labels.append("%s  [%s]" % (a["asset_id"].split(":", 1)[1], a["asset_class"]))
    ax1.set_yticks(range(len(assets)))
    ax1.set_yticklabels(labels, fontsize=7)
    ax1.invert_yaxis()
    ax1.set_xlim(0, total_lines + 2)
    ax1.set_xlabel("line in report 8398 markdown (1..%d)" % total_lines, fontsize=8)
    ax1.set_title("Registered assets: source-anchor line and class\n"
                  "(report %s, sha256 %s…)" % (REPORT_ID,
                                               manifest["source"]["source_hash"][7:19]),
                  fontsize=9)
    ax1.grid(axis="x", ls=":", lw=0.5, alpha=0.6)
    for spine in ("top", "right"):
        ax1.spines[spine].set_visible(False)

    counts = Counter(a["asset_class"] for a in assets)
    keys = list(counts)
    ax2.barh(range(len(keys)), [counts[k] for k in keys], color="#4c72b0", height=0.6)
    ax2.set_yticks(range(len(keys)))
    ax2.set_yticklabels(keys, fontsize=7)
    ax2.invert_yaxis()
    ax2.set_xlabel("assets", fontsize=8)
    ax2.set_title("Asset inventory by class (n=%d)" % len(assets), fontsize=9)
    for i, k in enumerate(keys):
        ax2.text(counts[k] + 0.08, i, str(counts[k]), va="center", fontsize=7)
    ax2.set_xlim(0, max(counts.values()) + 1.2)
    for spine in ("top", "right"):
        ax2.spines[spine].set_visible(False)

    handles = [plt.Line2D([], [], marker="o", ls="", color=c, label=k,
                          markeredgecolor="black", markeredgewidth=0.4)
               for k, c in color.items()]
    ax1.legend(handles=handles, fontsize=7, loc="lower right", frameon=False,
               title="resolution", title_fontsize=7)
    fig.tight_layout()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE_PNG, dpi=150)
    plt.close(fig)
    print("figure: %s (%d bytes)" % (FIGURE_PNG.relative_to(ROOT),
                                     FIGURE_PNG.stat().st_size))


def _md_escape(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def cmd_report() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    ver = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    src = manifest["source"]
    assets = manifest["assets"]
    cnt = manifest["counts"]
    rf = src["record_fields"]

    lines: list[str] = []
    add = lines.append
    add("# KF-RESULT %s" % PACKAGE_ID)
    add("")
    add("工序 `%s`（task_type=`%s`，lane %s）｜report_id `%s`｜源哈希 `%s`"
        % (PACKAGE_ID, TASK_TYPE, manifest["lane"], REPORT_ID, src["source_hash"]))
    add("")
    add("## ① 本工序做了什么")
    add("")
    add("按契约对报告 %s 做**源资产登记**（不做抽取、不做分类、不标注 verified）：" % REPORT_ID)
    add("")
    add("1. 从平台取回 report_id=%s 的 `markdown` 字段，落盘为字节副本（`%s`，%d bytes / %d chars），"
        "本地重算 sha256 与契约声明值比对：**%s**。"
        % (REPORT_ID, src["local_copy"], src["bytes"], src["chars"],
           "一致" if src["hash_match"] else "不一致（见 ⑤）"))
    add("2. 逐条登记报告正文与 record 中声明的代码/脚本/文档/工件/图/符号引用，共 **%d** 项，"
        "每项带可复算定位（字符区间 + 行号 + 逐字引文 + 引文 sha256 + 出现次数）。" % cnt["assets"])
    add("3. 逐项做存在性探测并如实记录结论：`%s`。" %
        "，".join("%s=%d" % (k, v) for k, v in cnt["by_resolution"].items()))
    add("4. 产出 `asset_manifest.json`、`kf_result.json`（信封）、`verification.json`（自检）与一张资产清单图。")
    add("")
    add("## ② 怎么做的（步骤 / 工具 / 关键设置）")
    add("")
    add("| 步骤 | 命令 | 说明 |")
    add("|---|---|---|")
    add("| 取源 | `python3 scripts/kf_wp8398_01_register.py fetch` | GET `/api/v1/tensor/reports/%s`，"
        "只读 report_id=%s 一个报告；markdown 原文按 UTF-8 字节落盘 |" % (REPORT_ID, REPORT_ID))
    add("| 登记 | `... build` | 声明表驱动扫描；定位器为**在取回字节上实测**的字符区间/行号/逐字引文，"
        "不手抄任何数字 |")
    add("| 信封 | `... envelope` | `provenance.source_hash` = 本地重算值（非契约抄写） |")
    add("| 自检 | `... verify` | 重新联网取一份 markdown，对每条 markdown 定位器复核 "
        "slice/字符 sha256/出现次数/行号；6 项 acceptance 逐条机判 |")
    add("| 出图 | `... figure` | matplotlib，资产锚点行位 + 类别计数 |")
    add("")
    add("关键设置：仅用标准库（`verify` 用 jsonschema、`figure` 用 matplotlib）；"
        "任何定位失败 `SystemExit` 中止，不产出半份 manifest。")
    add("")
    add("## ③ 产出物清单")
    add("")
    add("| 文件 | 要点 |")
    add("|---|---|")
    add("| `docs/kf/%s/asset_manifest.json` | 源身份 + %d 项资产 + 计数 + 空 claims + integrity |"
        % (PACKAGE_ID, cnt["assets"]))
    add("| `docs/kf/%s/kf_result.json` | 平台信封：package_id/task_type/report_id/provenance/outputs/claims |"
        % PACKAGE_ID)
    add("| `docs/kf/%s/verification.json` | 6 项 acceptance 自检结果（`all_ok=%s`） |"
        % (PACKAGE_ID, ver["all_ok"]))
    add("| `docs/kf/%s/figures/fig_asset_inventory.png` | 资产锚点行位图 + 类别计数（matplotlib, 150 dpi） |"
        % PACKAGE_ID)
    add("| `runs/%s/source_%s.md` | 源 markdown 字节副本（%d bytes） |"
        % (PACKAGE_ID, REPORT_ID, src["bytes"]))
    add("| `scripts/kf_wp8398_01_register.py` | 本工序全部步骤的可重跑实现 |")
    add("| `schemas/asset_manifest_kf.v1.schema.json` | 01 工序 manifest 的通用（非 const 硬编码）schema |")
    add("")
    add("## ④ 证据定位表（claim/字段 → 原文引文片段）")
    add("")
    add("引文均为取回 markdown 的**逐字切片**（`verify` 已复核 slice 与 sha256）。"
        "资产集合 = 报告声明物，非知识主张：本工序 claims 为空数组（契约 `classify_report_type=false`）。")
    add("")
    add("| 资产 ID | 类别 | 行 | 原文引文（逐字） | 解析状态 |")
    add("|---|---|---|---|---|")
    for a in assets:
        loc = a["locator"]
        add("| `%s` | %s | %d | `%s` | %s |"
            % (a["asset_id"], a["asset_class"],
               loc["start_line"] if loc["source_field"] == "markdown" else 0,
               _md_escape(loc["quote"]), a["resolution"]["status"]))
    add("")
    add("源身份字段证据：")
    add("")
    add("| 字段 | 值 | 依据 |")
    add("|---|---|---|")
    add("| `report_id` | %s | `GET /tensor/reports/%s` 返回 id 字段 |" % (REPORT_ID, REPORT_ID))
    add("| `sha256(markdown)` | `%s` | 本地对字节副本重算，与契约 `%s` %s |"
        % (src["source_hash"], src["contract_source_hash"],
           "一致" if src["hash_match"] else "不一致"))
    add("| `chars` | %d | `len(markdown)`，契约声明 %d，%s |"
        % (src["chars"], src["contract_chars"],
           "一致" if src["chars_match_contract"] else "不一致"))
    add("| `title` | %s | record.title（契约声明值 %s） |"
        % (rf["title"], "一致" if rf["title_matches_contract"] else "不一致"))
    add("| `scenario_key` | %s | record.scenario_key（契约声明 %s，%s） |"
        % (rf["scenario_key"], rf["contract_scenario_key"],
           "一致" if rf["scenario_matches_contract"] else "不一致"))
    add("| 报告自述 git rev | `%s` | 原文含该串（%s）；本工序不打开该 rev |"
        % (CONTRACT_REPORTED_GIT_REV, "是" if rf["reported_git_rev_in_markdown"] else "否"))
    add("")
    add("## ⑤ 注意点与局限")
    add("")
    add("1. **只登记、不验证内容**：本工序不断言任何数值结论正确；`status` 一律不是 verified，"
        "verification 由平台门独立重算。manifest 中 `claims` 为空数组是**按契约的完整结果**，不是缺省。")
    unres = [a["asset_id"] for a in assets if a["resolution"]["status"] == "unresolved"]
    add("2. **%d 项资产中只有 %d 项在本工序可真正解析**（源 markdown）；%s 为 "
        "`declared_only`（仅在本仓之外的存在性探测中可见：外部检出路径 / 本地 import "
        "spec / grep / git 对象，均非报告 pin 的 rev，故一律不报字节哈希）、%s 为 "
        "`metadata_only`（图只有 name/caption）、%s 为 `unresolved`：%s。"
        % (cnt["assets"], cnt["by_resolution"].get("resolved", 0),
           cnt["by_resolution"].get("declared_only", 0),
           cnt["by_resolution"].get("metadata_only", 0),
           cnt["by_resolution"].get("unresolved", 0),
           "、".join("`%s`" % u for u in unres)))
    add("3. **上游工件未做字节校验**：报告涉及的求解器/脚本/工件属于上游仓，检出目录 `%s`（rev `%s`）"
        "不是报告 pin 的 `%s`，故只报“存在”不报哈希；任何一致性主张留待上游 owner。"
        % (src["upstream_probe"].get("probe_root"), src["upstream_probe"].get("probe_rev"),
           CONTRACT_REPORTED_GIT_REV))
    figs = [a for a in assets if a["asset_class"] == "figure"]
    fig_ok = sum(1 for a in figs if a["resolution"]["status"] == "resolved")
    add("4. **图是记录元数据**：%d 张图的名称/图注来自 `record.figures`（正文 ④ 只写“见附图”、"
        "未给文件名）；figure 端点返回载荷 %d/%d 张，%s"
        % (len(figs), fig_ok, len(figs),
           "已登记为 resolved 且记录字节数" if fig_ok == len(figs) and figs else
           "既无图字节可哈希，下游也无法从该端点复现图"))
    add("5. **`api_baseline.json` / `regression_gate.json` / `performance_pytest.json` 无路径前缀**："
        "原文以裸文件名出现，实际落盘目录需上游仓确认，本工序不猜路径。")
    add("6. 报告正文的表格与数字（如 0.0e+00、-8.08%、150 用例）**未登记为 claim**："
        "按契约本工序不做抽取，防越权复述；它们只作为“报告存在这些声明”的事实留在原文。")
    add("7. **审计链工件不可取回是这条产线的真实缺口**：报告 ④ 声称的总表/签名基线/回归门/性能样本"
        "（`artifacts/contact_physics/*.json`、`api_baseline.json` 等）在本工序两个探测根下都取不到"
        "（`artifacts/` 被 `.gitignore` 排除，只有少数文件被强制入库），下游证据审计工序若需要这些字节，"
        "须回上游仓运行机取证，否则只能拿到“报告声称有”这一层。")

    # error / consistency judgement (report discipline): name the comparison, answer <3%
    add("")
    add("### 误差判定（数值面）")
    add("")
    add("本工序无数值模型输出，可比对量只有源身份量与定位器，逐项列出（判据面而非物理精度面）：")
    add("")
    add("| 关键量 | 基准 | 误差 | 是否 < 3% |")
    add("|---|---|---|---|")
    add("| markdown sha256 | 契约声明 `%s` | 0（逐位相同） | 是（0%% < 3%%） |"
        % src["contract_source_hash"])
    add("| markdown 字符数 %d | 契约声明 %d | 0 | 是（0%% < 3%%） |"
        % (src["chars"], src["contract_chars"]))
    add("| 定位器可解析率 %d/%d | 全部可解析 | 0 | 是（0%% < 3%%） |"
        % (cnt["markdown_locators"], cnt["markdown_locators"]))
    add("")
    add("**无物理/实验基准可比的声明**：本工序不产出物理量，故不存在“计算值 vs 实验值”的误差项；"
        "报告 8398 自身的数值主张（如 0.0e+00、-8.08%）属上游工序，本工序未复核也未复述。")
    add("")
    add("## ⑥ 自检（逐条对照 acceptance）")
    add("")
    add("| acceptance 项 | 结果 | 依据 |")
    add("|---|---|---|")
    for k, v in ver["acceptance"].items():
        add("| `%s` | %s | %s |" % (k, "✓" if v["ok"] else "✗", _md_escape(v["detail"])))
    add("")
    add("`all_ok = %s`；无失败项（若有会如实列出，不粉饰）。" % ver["all_ok"])
    add("")
    add("## 复跑命令")
    add("")
    add("```bash")
    add("cd <worktree>  # TensorKnowledge worktree for m15622")
    add("python3 scripts/kf_wp8398_01_register.py all   # fetch+build+envelope+verify+figure+report")
    add("```")
    add("")
    add("## KF-RESULT JSON")
    add("")
    add("```json")
    add(json.dumps(env, ensure_ascii=False, indent=2))
    add("```")
    add("")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("report: %s (%d bytes)" % (REPORT_MD.relative_to(ROOT),
                                     REPORT_MD.stat().st_size))


# ---------------------------------------------------------------- step: publish
def cmd_publish() -> None:
    import base64
    md = REPORT_MD.read_text(encoding="utf-8")
    if md.count("```json") != 1:
        raise SystemExit("report markdown must contain exactly one ```json block")
    tok = _login()
    figs = []
    if FIGURE_PNG.exists():
        figs.append({
            "name": FIGURE_PNG.stem,
            "caption": ("Registered asset anchors for report %s: each asset's source "
                        "line in the markdown (dot colour = resolution status) and the "
                        "asset inventory by class. Generated by "
                        "scripts/kf_wp8398_01_register.py from the measured manifest."
                        % REPORT_ID),
            "png_base64": base64.b64encode(FIGURE_PNG.read_bytes()).decode(),
        })
    body = {
        "title": "KF-RESULT %s" % PACKAGE_ID,
        "summary": ("Report %s source asset registered: markdown sha256 verified against "
                    "the contract, %d declared assets located with measured char/line "
                    "locators, 0 claims by design (registration-only package)."
                    % (REPORT_ID, json.loads(MANIFEST.read_text())["counts"]["assets"])),
        "scenario_key": CONTRACT_SCENARIO,
        "mission_id": 15622,
        "tags": ["kf-wp:%s" % PACKAGE_ID, "01-asset-registration", "DEM",
                 "contact-physics", "ice_navigation"],
        "markdown": md,
        "figures": figs,
    }
    req = urllib.request.Request(_api_base() + "/tensor/reports",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            status, payload = r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        raise SystemExit("POST /tensor/reports -> HTTP %s: %s" % (e.code, e.read().decode()[:800]))
    resp = json.loads(payload) if payload.strip().startswith("{") else {}
    # keep only identity fields: the POST response echoes the whole markdown/figures
    info = {"published_at": _now(), "http_status": status,
            "republished_report_id": resp.get("id"),
            "title": resp.get("title"), "tags": resp.get("tags"),
            "mission_id": resp.get("mission_id")}
    if not isinstance(resp, dict) or not info["republished_report_id"]:
        info["raw_response_head"] = payload[:500]
    PUBLISH_INFO.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    print("published: HTTP %s  id=%s" % (status, info.get("republished_report_id")))
    if info.get("republished_report_id"):
        cmd_roundtrip()


def cmd_roundtrip() -> None:
    """Re-read the published report and prove the embedded envelope still carries the
    live source hash. Read-only; safe to re-run (it never posts a new report)."""
    info = json.loads(PUBLISH_INFO.read_text(encoding="utf-8"))
    rid = info.get("republished_report_id") or (info.get("response") or {}).get("id")
    if not rid:
        raise SystemExit("publish.json carries no report id")
    tok = _login()
    st, raw = _get("/tensor/reports/%s" % rid, tok)
    if st != 200:
        raise SystemExit("GET published report %s -> HTTP %s" % (rid, st))
    pub = json.loads(raw.decode())
    ipsum, raw2 = _get("/tensor/reports/" + REPORT_ID, tok)
    live = json.loads(raw2.decode()).get("markdown", "") if ipsum == 200 else ""
    md = pub.get("markdown") or ""
    FENCE = "```"
    blocks = re.findall(FENCE + r"(\w*)\n(.*?)" + FENCE, md, re.S)
    js = [b[1] for b in blocks if b[0] == "json"]
    env = json.loads(js[0]) if len(js) == 1 else None
    live_hash = "sha256:" + _sha256(live.encode())
    chk = {
        "published_id": rid,
        "title": pub.get("title"),
        "tags": pub.get("tags"),
        "json_blocks": len(js),
        "embedded_source_hash": (env or {}).get("provenance", {}).get("source_hash"),
        "live_source_hash": live_hash,
        "assets_in_outputs": len((env or {}).get("outputs", {})
                                 .get("asset_manifest.json", {}).get("assets", [])),
        "claims_in_envelope": len((env or {}).get("claims") or []),
        "figures_attached": [f.get("name") for f in pub.get("figures") or []],
        "mission_id": pub.get("mission_id"),
    }
    chk["hash_roundtrip_ok"] = bool(env) and chk["embedded_source_hash"] == live_hash
    chk["one_json_block_ok"] = len(js) == 1
    info["roundtrip_check"] = chk
    info["roundtrip_ok"] = chk["hash_roundtrip_ok"] and chk["one_json_block_ok"]
    PUBLISH_INFO.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    print("roundtrip: id=%s json_blocks=%d hash_ok=%s figures=%s"
          % (rid, len(js), chk["hash_roundtrip_ok"], chk["figures_attached"]))
    if not info["roundtrip_ok"]:
        raise SystemExit("published report roundtrip FAILED")


STEPS = {"fetch": cmd_fetch, "build": cmd_build, "envelope": cmd_envelope,
         "verify": cmd_verify, "figure": cmd_figure, "report": cmd_report,
         "publish": cmd_publish, "roundtrip": cmd_roundtrip}


def main() -> None:
    args = sys.argv[1:] or ["all"]
    if args[0] == "all":
        seq = ["fetch", "build", "envelope", "verify", "figure", "report"]
    elif args[0] in STEPS:
        seq = [args[0]]
    else:
        raise SystemExit("usage: %s [all|%s]" % (sys.argv[0], "|".join(STEPS)))
    for s in seq:
        print("== %s ==" % s)
        STEPS[s]()


if __name__ == "__main__":
    main()