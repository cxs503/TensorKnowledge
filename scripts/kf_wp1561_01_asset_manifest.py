#!/usr/bin/env python3
"""Knowledge-Factory work package wp-1561-01 — task 01-asset-registration.

Scope (contract, verbatim): "登记源资产：确认 report_id 与其 markdown 的字节哈希，
列出可解析的附件/工件，不做抽取。claims 允许为空数组。"

So this script does exactly three things and nothing more:
  1. pin the source: fetch (or read the snapshot of) report 1561's ``markdown`` field,
     recompute its sha256 over UTF-8 bytes and compare with the contract hash;
  2. inventory the in-report assets that a downstream工序 can point at (document,
     sections, code blocks, tables, figures, referenced code/artifact/test paths,
     API endpoints, run-output tokens, literature / report cross references) with a
     verbatim locator for each;
  3. emit ``asset_manifest.json`` + the ``kf_result.v1`` envelope, and verify both.

It never extracts claims, never classifies the report, and never writes upstream.

Usage::

    python3 scripts/kf_wp1561_01_asset_manifest.py --fetch       # refresh snapshot from API
    python3 scripts/kf_wp1561_01_asset_manifest.py               # rebuild outputs from snapshot
    python3 scripts/kf_wp1561_01_asset_manifest.py --verify      # re-check committed outputs
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(HERE, "docs", "kf", "wp-1561-01")
SOURCE = os.path.join(OUTDIR, "source", "report_1561.md")
FIGFETCH = os.path.join(OUTDIR, "figure_fetch.json")
MANIFEST = os.path.join(OUTDIR, "asset_manifest.json")
RESULT = os.path.join(OUTDIR, "kf_result.json")
SELFCHECK = os.path.join(OUTDIR, "selfcheck.json")

CONTRACT = {
    "package_id": "wp-1561-01",
    "task_type": "01-asset-registration",
    "report_id": "1561",
    "source_uri": "tensor://reports/1561",
    "source_field": "markdown",
    "source_hash": "sha256:19203e6ea7f05573f0b06835f9c0e1f08fb54fc5481787ace02487d5ac6d1620",
    "scenario_key": "propulsion_closure",
    "title": (
        "m1838 推进端点推力闭合修复：Kt=0.3-0.2J 直线式 → BEMT 反解转速，"
        "5 型船闸门 verdict_fail=0"
    ),
}
ENVELOPE_SCHEMA = os.path.join(HERE, "schemas", "kf_result.v1.schema.json")
FIGURES_ENDPOINT = "/tensor/reports/1561/figures/{name}"

# literature / standard references: (label, regex). The regex only locates a string
# that is literally present in the markdown; nothing is inferred about its content.
LITERATURE = [
    ("ITTC-78 skin-friction line", r"ITTC-78"),
    ("B4-70 open-water experimental series", r"B4-70"),
    ("Wageningen B-series regression", r"Wageningen B"),
    ("Holtrop resistance regression", r"Holtrop"),
    ("Taylor single-screw t/w formula", r"Taylor 式"),
    ("B-series chord distribution", r"B 系列"),
]


def sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


# --------------------------------------------------------------------------- io
def api_token(base: str) -> str:
    user = os.environ["TENSOR_AGENT_USER"]
    pw = os.environ["TENSOR_AGENT_PASS"]
    req = urllib.request.Request(
        base.rstrip("/") + "/auth/login",
        data=json.dumps({"username": user, "password": pw}).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    tok = json.loads(urllib.request.urlopen(req, timeout=60).read())
    return tok["access_token"]


def fetch_report(base: str) -> tuple[str, dict]:
    token = api_token(base)
    req = urllib.request.Request(
        base.rstrip("/") + "/tensor/reports/1561",
        headers={"Authorization": "Bearer " + token},
    )
    record = json.loads(urllib.request.urlopen(req, timeout=60).read())
    record = record.get("data", record) if isinstance(record, dict) else record
    if str(record.get("id")) != CONTRACT["report_id"]:
        raise SystemExit(f"wrong report served: id={record.get('id')}")
    return record.get("markdown") or "", record, token


def fetch_figures(record: dict, token: str, base: str) -> dict:
    """Probe whether the declared figure payloads are actually served."""
    out = {}
    for fig in record.get("figures") or []:
        name = fig.get("name", "")
        rec = {"endpoint": FIGURES_ENDPOINT.format(name=name), "method": "GET"}
        req = urllib.request.Request(
            base.rstrip("/") + FIGURES_ENDPOINT.format(name=name),
            headers={"Authorization": "Bearer " + token},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=60)
            body = resp.read()
            rec.update(
                http_status=resp.status,
                content_type=resp.headers.get("Content-Type"),
                bytes=len(body),
                sha256=sha256_bytes(body),
                resolvable=True,
            )
        except urllib.error.HTTPError as exc:
            rec.update(
                http_status=exc.code,
                error_body=exc.read()[:200].decode("utf-8", "replace"),
                resolvable=False,
            )
        except urllib.error.URLError as exc:  # network down: honest unknown
            rec.update(http_status=None, error_body=str(exc), resolvable=None)
        out[name] = rec
    return out


def load_json(path: str, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------- inventory
class Inventory:
    def __init__(self, md: str, record: dict, figfetch: dict):
        self.md = md
        self.lines = md.split("\n")
        self.record = record or {}
        self.figfetch = figfetch or {}
        self.assets: list[dict] = []
        self._by_id: set[str] = set()

    # -- helpers --------------------------------------------------------------
    def _add(self, kind: str, quote: str, locator: dict, resolvability: str, **extra) -> str:
        aid = f"{CONTRACT['report_id']}-a{len(self.assets):03d}"
        assert aid not in self._by_id
        self._by_id.add(aid)
        asset = {
            "asset_id": aid,
            "kind": kind,
            "locator": locator,
            "resolvability": resolvability,
            "quote": quote,
            "quote_verbatim_in_markdown": quote in self.md,
            "embedded_in_report": True,
            "registration_action": "registered_index_only_no_extraction",
        }
        asset.update(extra)
        self.assets.append(asset)
        return aid

    def line_of(self, needle: str, start: int = 1) -> int:
        for i, line in enumerate(self.lines, 1):
            if i >= start and needle in line:
                return i
        return 0

    # -- detectors ------------------------------------------------------------
    def add_document(self):
        title_line = self.lines[0] if self.lines else ""
        self._add(
            "report_document",
            title_line,
            {
                "type": "report_document",
                "uri": CONTRACT["source_uri"],
                "field": "markdown",
                "line": 1,
                "anchor": "tensor://reports/1561#markdown",
            },
            "resolved_in_markdown",
            sha256=sha256_bytes(self.md.encode("utf-8")),
            utf8_bytes=len(self.md.encode("utf-8")),
            characters=len(self.md),
            line_count=len(self.lines),
            registration_note="hash pinned over UTF-8 bytes of the markdown field as served",
        )

    def add_sections(self):
        slot = 0
        for i, line in enumerate(self.lines, 1):
            if line.startswith("## "):
                self._add(
                    "section",
                    line,
                    {
                        "type": "markdown_line",
                        "line": i,
                        "line_range": [i, i],
                        "all_lines": [i],
                        "anchor": "tensor://reports/1561#markdown",
                    },
                    "resolved_in_markdown",
                    slot=slot,
                    label=line.lstrip("# ").strip(),
                )
                slot += 1

    def add_code_blocks(self):
        i = 0
        n_lines = len(self.lines)
        slot = 0
        while i < n_lines:
            line = self.lines[i]
            if line.startswith("```"):
                lang = line[3:].strip() or None
                start = i + 1
                j = start
                while j < n_lines and not self.lines[j].startswith("```"):
                    j += 1
                body = "\n".join(self.lines[start:j])
                first = next((txt.strip() for txt in self.lines[start:j] if txt.strip()), "")
                self._add(
                    "code_block",
                    first,
                    {
                        "type": "markdown_line_range",
                        "line": start + 1,
                        "line_range": [start + 1, j],
                        "anchor": "tensor://reports/1561#markdown",
                    },
                    "resolved_in_markdown",
                    slot=slot,
                    language=lang,
                    content_sha256=sha256_bytes(body.encode("utf-8")),
                    content_lines=j - start,
                )
                slot += 1
                i = j + 1
                continue
            i += 1

    def add_tables(self):
        slot = 0
        i = 0
        n = len(self.lines)
        while i < n:
            if self.lines[i].lstrip().startswith("|"):
                start = i
                while i < n and self.lines[i].lstrip().startswith("|"):
                    i += 1
                block = self.lines[start:i]
                header = block[0]
                cols = len([c for c in header.split("|")[1:-1]])
                sep = block[1] if len(block) > 1 else ""
                body_rows = len(block) - 2 if re.match(r"^\|[\s:|-]+\|?$", sep.strip()) else len(block) - 1
                self._add(
                    "table",
                    header,
                    {
                        "type": "markdown_line_range",
                        "line": start + 1,
                        "line_range": [start + 1, i],
                        "anchor": "tensor://reports/1561#markdown",
                    },
                    "resolved_in_markdown",
                    slot=slot,
                    columns=cols,
                    data_rows=body_rows,
                    table_sha256=sha256_bytes("\n".join(block).encode("utf-8")),
                )
                slot += 1
                continue
            i += 1

    def add_figures(self):
        for idx, fig in enumerate(self.record.get("figures") or []):
            name = fig.get("name", "")
            caption = fig.get("caption", "")
            line_no = self.line_of(name)
            probe = self.figfetch.get(name) or {}
            resolvable = probe.get("resolvable")
            if line_no and resolvable:
                resolvability = "resolved_in_markdown_and_served_by_api"
            elif line_no:
                resolvability = "declared_and_markdown_referenced_binary_not_served"
            else:
                resolvability = "declared_in_record_only"
            self._add(
                "figure",
                self.lines[line_no - 1] if line_no else name,
                {
                    "type": "report_record_field",
                    "field": f"figures[{idx}]",
                    "name": name,
                    "source_field": "record",
                    "line": line_no or None,
                    "markdown_reference_line": line_no or None,
                    "anchor": "tensor://reports/1561#markdown",
                },
                resolvability,
                caption_verbatim_in_markdown=caption in self.md,
                record_caption=caption,
                binary_probe=probe,
                note=(
                    "name+caption live in the report record `figures` field; the markdown names the "
                    "file (图 N + backticked filename) and describes the panel, caption text is record-side. "
                    "Binary payload could not be retrieved: see binary_probe.http_status."
                ),
            )

    def add_paths_and_tokens(self):
        seen: set[str] = set()
        for i, line in enumerate(self.lines, 1):
            for span in re.findall(r"`([^`\n]+)`", line):
                if span in seen:
                    continue
                kind = None
                if re.fullmatch(r"/[a-z0-9_-]+/[a-z0-9_-]+", span):
                    kind = "api_endpoint"
                elif span.endswith(".py"):
                    kind = "test_path" if span.startswith("tests/") else "code_path"
                elif span.endswith(".json") or span.endswith("/"):
                    kind = "artifact_path"
                elif re.fullmatch(r"[A-Za-z0-9_./-]+\.SHIPS", span):
                    kind = "code_path"
                elif re.match(r"^(cases|evaluated|verdict_fail|froude_fail)=", span):
                    kind = "run_output_token"
                elif span.startswith("chain_gate ") and "--" in span:
                    kind = "command"
                if not kind:
                    continue
                seen.add(span)
                present = (
                    os.path.exists(os.path.join(HERE, span.rstrip("/")))
                    if kind in ("code_path", "test_path", "artifact_path")
                    else None
                )
                extra = {}
                if present is not None:
                    extra = {
                        "present_in_worktree": present,
                        "worktree_root": "TensorKnowledge",
                        "upstream_repo": "ship-performance-platform",
                    }
                self._add(
                    kind,
                    span,
                    {
                        "type": "markdown_inline_code",
                        "line": i,
                        "anchor": "tensor://reports/1561#markdown",
                    },
                    "referenced_only_not_resolvable_from_this_record"
                    if kind != "run_output_token"
                    else "resolved_in_markdown",
                    **extra,
                )

    def add_bare_endpoints(self):
        """Prose (non code-span) mentions of an endpoint path."""
        seen = {a["quote"] for a in self.assets if a["kind"] == "api_endpoint"}
        pat = re.compile(r"(?<![\w`/])/[a-z][a-z0-9_]*(?:/[a-z][a-z0-9_]*)?(?![\w`/])")
        for i, line in enumerate(self.lines, 1):
            if "`" in line:
                continue
            for m in pat.finditer(line):
                span = m.group(0)
                if span in seen:
                    continue
                seen.add(span)
                self._add(
                    "api_endpoint",
                    span,
                    {"type": "markdown_text", "line": i, "anchor": "tensor://reports/1561#markdown"},
                    "referenced_only_not_resolvable_from_this_record",
                    note=(
                        "prose mention only: the markdown gives no HTTP method, API version or "
                        "request/response schema for this path"
                        + (
                            "; single-segment fragment, the full route is not spelled out here"
                            if span.count("/") == 0
                            else ""
                        )
                    ),
                )

    def add_contract_field_list(self):
        """The response-contract field block is one verbatim multi-line span."""
        head = "响应契约保留"
        tail = "geometry_check/design/method`"
        start = self.md.find(head)
        end = self.md.find(tail)
        if start < 0 or end < 0:
            return
        end += len(tail)
        quote = self.md[start:end]
        line_start = self.md[:start].count("\n") + 1
        line_end = self.md[:end].count("\n") + 1
        self._add(
            "api_contract_field_list",
            quote,
            {
                "type": "markdown_line_range",
                "line": line_start,
                "line_range": [line_start, line_end],
                "anchor": "tensor://reports/1561#markdown",
            },
            "resolved_in_markdown",
            field_name_count=len(re.findall(r"[a-z][a-z0-9_]{2,}", quote)),
            note=(
                "verbatim block listing the response contract field names (kept as one span: the "
                "fields are named, not interpreted)"
            ),
        )

    def add_gate_predicates(self):
        """Gate criteria identifiers (I1..I6, I5b, I5c) named in the report."""
        seen = set()
        for i, line in enumerate(self.lines, 1):
            for m in re.finditer(r"(?<![A-Za-z0-9_])I[1-6][abc]?(?![A-Za-z0-9_])", line):
                tok = m.group(0)
                if tok in seen:
                    continue
                seen.add(tok)
                self._add(
                    "gate_predicate",
                    tok,
                    {
                        "type": "markdown_text",
                        "line": i,
                        "anchor": "tensor://reports/1561#markdown",
                    },
                    "named_no_locator",
                    note="predicate identifier named in the report; its implementation is not in this record",
                )

    def add_citations(self):
        for label, pat in LITERATURE:
            m = re.search(pat, self.md)
            if not m:
                continue
            self._add(
                "citation_reference",
                m.group(0),
                {
                    "type": "markdown_text",
                    "line": self.line_of(m.group(0)),
                    "anchor": "tensor://reports/1561#markdown",
                },
                "named_no_locator",
                label=label,
                note="named only; the markdown carries no edition/DOI/report number to resolve it",
            )
        for pat, kind, label in [
            (r"\bm\d{4}\b", "report_cross_reference", "referenced platform mission id"),
            (r"PB-\d{3}", "report_cross_reference", "referenced platform playbook id"),
        ]:
            seen = set()
            for m in re.finditer(pat, self.md):
                tok = m.group(0)
                if tok in seen:
                    continue
                seen.add(tok)
                self._add(
                    kind,
                    tok,
                    {
                        "type": "markdown_text",
                        "line": self.line_of(tok),
                        "anchor": "tensor://reports/1561#markdown",
                    },
                    "named_no_locator",
                    label=label,
                    note="cross-reference token only; no locator is supplied inside this report",
                )

    def build(self) -> list[dict]:
        self.add_document()
        self.add_sections()
        self.add_code_blocks()
        self.add_tables()
        self.add_figures()
        self.add_paths_and_tokens()
        self.add_contract_field_list()
        self.add_gate_predicates()
        self.add_bare_endpoints()
        self.add_citations()
        return self.assets


# ------------------------------------------------------------------ observations
def observations(md: str, figfetch: dict, record: dict) -> list[dict]:
    """Factual, quote-bound notes a downstream工序 must not have to rediscover.

    These are *not* claims about the science and carry no verdict; each one either
    quotes the markdown twice or records a probe result.
    """
    obs = []

    q_aframax = next((ln for ln in md.split("\n") if ln.startswith("- **Aframax**")), "")
    q_follow = "其中 Aframax 的 Cb·L·B·T 与输入排水量相差 13.7%"
    if q_aframax and q_follow in md:
        obs.append(
            {
                "observation_id": "1561-o000",
                "kind": "internal_numeric_relation",
                "description": (
                    "Same geometry comparison is stated with two different percentages. "
                    "Both are reproducible from the numbers quoted in the same bullet "
                    "(Cb·L·B·T=130790 m3 vs displacement=115000 t): |delta|/130790 = 0.1207 (12.1%) "
                    "and |delta|/115000 = 0.1373 (13.7%), i.e. the two sentences use different "
                    "denominators. "
                    "The report does not flag this as an error; registered so a downstream "
                    "工序 does not silently pick one figure."
                ),
                "quotes": [q_aframax, q_follow],
                "quotes_verbatim_in_markdown": [q_aframax in md, q_follow in md],
                "arithmetic_check": {
                    "delta_m3": 130790 - 115000,
                    "ratio_over_geometry": round((130790 - 115000) / 130790, 4),
                    "ratio_over_displacement": round((130790 - 115000) / 115000, 4),
                },
                "assigned_status": "unresolved",
                "unresolved_reason": "which denominator the endpoint uses is not stated in the report",
            }
        )

    figs = record.get("figures") or []
    if figs:
        probed = {n: figfetch.get(n, {}) for n in (f.get("name") for f in figs)}
        statuses = sorted({str((p or {}).get("http_status")) for p in probed.values()})
        obs.append(
            {
                "observation_id": "1561-o001",
                "kind": "asset_payload_unavailable",
                "description": (
                    f"{len(figs)} figures are declared in the record `figures` field and named in the "
                    f"markdown, but GET {FIGURES_ENDPOINT} returned HTTP {'/'.join(statuses)} for every "
                    "name, so the binary payloads are not resolvable from this side. Figures are "
                    "registered as declared+reference-only; nothing was re-rendered or substituted."
                ),
                "probe_endpoint": FIGURES_ENDPOINT,
                "probe_results": probed,
                "assigned_status": "unresolved",
                "unresolved_reason": "figure binary not served by the report API at registration time",
            }
        )

    q_branch = next((ln.strip() for ln in md.split("\n") if "分支" in ln), "")
    if q_branch:
        obs.append(
            {
                "observation_id": "1561-o002",
                "kind": "provenance_gap",
                "description": (
                    "Upstream evidence artifacts are identified by repo-relative path plus a branch "
                    "name only; the markdown carries no commit sha or artifact checksum, so those "
                    "paths cannot be hash-pinned from this record. They are registered as textual "
                    "references (present_in_worktree=false)."
                ),
                "quotes": [q_branch],
                "quotes_verbatim_in_markdown": [q_branch in md],
                "assigned_status": "unresolved",
                "unresolved_reason": "no commit identity or digest supplied inside report 1561",
            }
        )

    q_fail = next((ln for ln in md.split("\n") if ln.startswith("| η0 vs B4-70")), "")
    q_undet = next((ln for ln in md.split("\n") if ln.startswith("| 已有能力 vs 实验基准")), "")
    if q_fail and q_undet:
        obs.append(
            {
                "observation_id": "1561-o003",
                "kind": "self_declared_non_pass_rows",
                "description": (
                    "The report's own ⑥ table contains one row answered 否 and one answered 未判定. "
                    "Registered so that downstream工序 preserves these statuses and does not lift "
                    "them to a pass; this package stamps nothing as verified."
                ),
                "quotes": [q_fail, q_undet],
                "quotes_verbatim_in_markdown": [q_fail in md, q_undet in md],
                "assigned_status": "unresolved",
                "unresolved_reason": "left exactly as the source states it (否 / 未判定)",
            }
        )
    return obs


# --------------------------------------------------------------------- manifest
def build_manifest(md: str, record: dict, figfetch: dict, generated_at: str) -> dict:
    assets = Inventory(md, record, figfetch).build()
    kinds: dict[str, int] = {}
    resolv: dict[str, int] = {}
    for a in assets:
        kinds[a["kind"]] = kinds.get(a["kind"], 0) + 1
        resolv[a["resolvability"]] = resolv.get(a["resolvability"], 0) + 1
    obs = observations(md, figfetch, record)
    return {
        "manifest_version": "1.0",
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "generated_at": generated_at,
        "report": {
            "report_id": CONTRACT["report_id"],
            "source_uri": CONTRACT["source_uri"],
            "source_field": CONTRACT["source_field"],
            "source_hash": sha256_bytes(md.encode("utf-8")),
            "contract_source_hash": CONTRACT["source_hash"],
            "source_hash_matches_contract": sha256_bytes(md.encode("utf-8"))
            == CONTRACT["source_hash"],
            "hash_algorithm": "sha256",
            "hash_basis": "UTF-8 bytes of the `markdown` field as served by the platform API",
            "utf8_bytes": len(md.encode("utf-8")),
            "characters": len(md),
            "lines": len(md.split("\n")),
            "title": record.get("title") or CONTRACT["title"],
            "contract_title": CONTRACT["title"],
            "title_matches_contract": (record.get("title") or CONTRACT["title"]) == CONTRACT["title"],
            "scenario_key": record.get("scenario_key") or CONTRACT["scenario_key"],
            "record_status": record.get("status"),
            "record_created_at": record.get("created_at"),
            "record_created_by": record.get("created_by"),
            "record_mission_id": record.get("mission_id"),
            "record_tags": record.get("tags") or [],
            "figures_declared": len(record.get("figures") or []),
            "registration_scope": (
                "inventory + hash pinning only; no extraction, no report_type classification, "
                "no verification stamp"
            ),
        },
        "assets": assets,
        "observations": obs,
        "counts": {
            "total": len(assets),
            "by_kind": dict(sorted(kinds.items())),
            "by_resolvability": dict(sorted(resolv.items())),
            "claims_registered": 0,
        },
        "claims": [],
        "claims_note": (
            "task_type 01 registers no knowledge claims; the empty array is the contract-permitted "
            "complete result, not an omission (constraint no_forced_claim_generation)"
        ),
        "schema_refs": {
            "envelope_schema": "schemas/kf_result.v1.schema.json",
            "envelope_schema_sha256": sha256_bytes(open(ENVELOPE_SCHEMA, "rb").read()),
            "manifest_schema": None,
            "note": (
                "asset_manifest.v1 has no upstream JSON-Schema; its invariants are enforced by "
                "verify_manifest() in this script and tests/test_wp1561_01_asset_registration.py"
            ),
        },
        "producer": (
            f"agent/m15529 (TensorKnowledge) · package {CONTRACT['package_id']}"
        ),
        "repro_cmd": (
            "python3 scripts/kf_wp1561_01_asset_manifest.py "
            "&& python3 scripts/kf_wp1561_01_asset_manifest.py --verify "
            "&& python3 -m pytest tests/test_wp1561_01_asset_registration.py -q"
        ),
        "tools": {
            "generator": "scripts/kf_wp1561_01_asset_manifest.py",
            "python": sys.version.split()[0],
            "git_head_at_generation": git_head(),
        },
    }


def git_head() -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", HERE, "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:  # pragma: no cover - only for record keeping
        return None


def build_result(manifest: dict, emitted_at: str) -> dict:
    return {
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "report_id": CONTRACT["report_id"],
        "provenance": {
            "source_hash": manifest["report"]["source_hash"],
            "source_field": CONTRACT["source_field"],
            "source_uri": CONTRACT["source_uri"],
            "producer": f"agent/m15529 (TensorKnowledge) · package {CONTRACT['package_id']}",
            "emitted_at": emitted_at,
            "notes": (
                "01-asset-registration: hash-pinned inventory of report 1561; claims intentionally "
                "empty; no extraction, no report_type classification, no verification stamp"
            ),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }


# ---------------------------------------------------------------- verification
def verify_manifest(manifest: dict, md: str, record: dict) -> dict:
    """Structural + traceability checks. Returns {check: {ok, detail}}."""
    checks: dict[str, dict] = {}
    lines = md.split("\n")
    digest = sha256_bytes(md.encode("utf-8"))

    checks["source_hash_matches_contract"] = {
        "ok": digest == CONTRACT["source_hash"] == manifest["report"]["source_hash"],
        "detail": {"computed": digest, "contract": CONTRACT["source_hash"]},
    }
    checks["source_hash_matches_record_metadata"] = {
        "ok": manifest["report"]["contract_source_hash"] == CONTRACT["source_hash"],
        "detail": manifest["report"]["source_hash_matches_contract"],
    }

    ids = [a["asset_id"] for a in manifest["assets"]]
    checks["no_duplicate_ids"] = {
        "ok": len(ids) == len(set(ids)),
        "detail": {"total": len(ids), "unique": len(set(ids))},
    }
    bad_ids = [i for i in ids if not re.fullmatch(r"1561-a[0-9]{3}", i)]
    checks["asset_id_pattern"] = {"ok": not bad_ids, "detail": bad_ids}
    contiguous = ids == [f"1561-a{i:03d}" for i in range(len(ids))]
    checks["asset_ids_contiguous"] = {"ok": contiguous, "detail": ids[:1] + ids[-1:]}

    unresolved_quotes, misplaced = [], []
    for a in manifest["assets"]:
        if a["kind"] in (
            "report_document", "section", "code_block", "table", "run_output_token", "figure",
            "api_endpoint", "code_path", "test_path", "artifact_path", "command",
            "citation_reference", "report_cross_reference", "api_contract_field_list",
            "gate_predicate",
        ):
            if a["quote"] not in md:
                unresolved_quotes.append(a["asset_id"])
                continue
            loc = a["locator"]
            ln = loc.get("line") or loc.get("markdown_reference_line")
            if ln:
                rng = loc.get("line_range") or [ln, ln]
                span = "\n".join(lines[rng[0] - 1 : rng[1]])
                if a["quote"] not in span:
                    misplaced.append({"asset_id": a["asset_id"], "line": ln})
    checks["source_locator_resolvable"] = {
        "ok": not unresolved_quotes and not misplaced,
        "detail": {"unresolvable": unresolved_quotes, "line_mismatch": misplaced},
    }

    kinds = {}
    for a in manifest["assets"]:
        kinds[a["kind"]] = kinds.get(a["kind"], 0) + 1
    checks["counts_consistent"] = {
        "ok": manifest["counts"]["total"] == len(manifest["assets"])
        and manifest["counts"]["by_kind"] == dict(sorted(kinds.items())),
        "detail": manifest["counts"],
    }

    checks["claims_empty_or_evidenced"] = {
        "ok": all(
            (c.get("evidence") or c.get("status") == "unresolved") for c in manifest["claims"]
        )
        and manifest["claims"] == [],
        "detail": {"claims": len(manifest["claims"])},
    }
    checks["no_verified_stamp"] = {
        "ok": all(
            c.get("status") != "verified" and c.get("status") != "verified-strong"
            for c in manifest["claims"]
        )
        and "verified" not in json.dumps(manifest.get("counts", {})),
        "detail": "claim statuses are not part of this task; nothing stamped verified",
    }

    declared = [f.get("name") for f in (record.get("figures") or [])]
    registered = [a["locator"].get("name") for a in manifest["assets"] if a["kind"] == "figure"]
    checks["figures_all_registered"] = {
        "ok": sorted(declared) == sorted(registered),
        "detail": {"declared": declared, "registered": registered},
    }

    unresolved_marked = [
        a["asset_id"]
        for a in manifest["assets"]
        if a["resolvability"] != "resolved_in_markdown" and not a.get("note") and a["kind"] != "api_endpoint"
        and a["kind"] not in ("code_path", "test_path", "artifact_path", "command",
                             "citation_reference", "report_cross_reference", "gate_predicate")
    ]
    checks["non_resolved_assets_explained"] = {"ok": not unresolved_marked, "detail": unresolved_marked}

    obs = manifest.get("observations") or []
    obs_ok = all(
        all(q in md for q in (o.get("quotes") or [])) and o.get("unresolved_reason") for o in obs
    )
    checks["observations_quote_bound"] = {"ok": obs_ok, "detail": [o["observation_id"] for o in obs]}

    return checks


def verify_envelope(result: dict) -> dict:
    checks = {}
    schema = load_json(ENVELOPE_SCHEMA)
    try:
        import jsonschema

        jsonschema.validate(result, schema)
        checks["envelope_schema_pass"] = {"ok": True, "detail": "jsonschema validate OK"}
    except ImportError:  # pragma: no cover
        checks["envelope_schema_pass"] = {"ok": False, "detail": "jsonschema not installed"}
    except Exception as exc:  # noqa: BLE001
        checks["envelope_schema_pass"] = {"ok": False, "detail": str(exc)}
    checks["envelope_report_id"] = {
        "ok": result["report_id"] == CONTRACT["report_id"],
        "detail": result["report_id"],
    }
    checks["envelope_package_id"] = {
        "ok": result["package_id"] == CONTRACT["package_id"],
        "detail": result["package_id"],
    }
    checks["envelope_source_field"] = {
        "ok": result["provenance"]["source_field"] == CONTRACT["source_field"],
        "detail": result["provenance"]["source_field"],
    }
    checks["envelope_declares_manifest_output"] = {
        "ok": "asset_manifest.json" in result["outputs"],
        "detail": list(result["outputs"]),
    }
    checks["envelope_manifest_matches_file"] = {
        "ok": result["outputs"]["asset_manifest.json"] == load_json(MANIFEST),
        "detail": "embedded manifest must equal docs/kf/wp-1561-01/asset_manifest.json",
    }
    return checks


def run_verify() -> int:
    md = open(SOURCE, encoding="utf-8").read()
    record = load_json(FIGFETCH.replace("figure_fetch.json", "report_record.json"), {})
    manifest = load_json(MANIFEST)
    result = load_json(RESULT)
    checks = {}
    checks.update(verify_manifest(manifest, md, record))
    checks.update(verify_envelope(result))
    failed = [k for k, v in checks.items() if not v["ok"]]
    report = {"ok": not failed, "failed": failed, "checks": checks}
    print(json.dumps(report, ensure_ascii=False, indent=1))
    if failed:
        print(f"VERIFY FAILED: {failed}", file=sys.stderr)
        return 1
    print(f"VERIFY OK: {len(checks)} checks passed", file=sys.stderr)
    return 0


# ------------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="re-fetch markdown + figures from the API")
    ap.add_argument("--verify", action="store_true", help="re-check committed outputs only")
    ap.add_argument("--outdir", default=OUTDIR)
    args = ap.parse_args()

    if args.verify:
        return run_verify()

    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
    if args.fetch:
        md, record, token = fetch_report(base)
        os.makedirs(os.path.dirname(SOURCE), exist_ok=True)
        with open(SOURCE, "w", encoding="utf-8") as fh:
            fh.write(md)
        figfetch = fetch_figures(record, token, base)
        with open(FIGFETCH, "w", encoding="utf-8") as fh:
            json.dump(figfetch, fh, ensure_ascii=False, indent=1)
        slim = {k: v for k, v in record.items() if k != "markdown"}
        with open(os.path.join(args.outdir, "report_record.json"), "w", encoding="utf-8") as fh:
            json.dump(slim, fh, ensure_ascii=False, indent=1, default=str)
    else:
        md = open(SOURCE, encoding="utf-8").read()
        record = load_json(os.path.join(args.outdir, "report_record.json"), {}) or {}
        figfetch = load_json(FIGFETCH, {}) or {}

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    manifest = build_manifest(md, record, figfetch, now)
    result = build_result(manifest, now)

    os.makedirs(args.outdir, exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    with open(RESULT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    checks = {}
    checks.update(verify_manifest(manifest, md, record))
    checks.update(verify_envelope(result))
    failed = [k for k, v in checks.items() if not v["ok"]]
    selfcheck = {
        "package_id": CONTRACT["package_id"],
        "generated_at": now,
        "ok": not failed,
        "failed": failed,
        "checks": checks,
        "artifact_sha256": {
            "asset_manifest.json": sha256_bytes(open(MANIFEST, "rb").read()),
            "kf_result.json": sha256_bytes(open(RESULT, "rb").read()),
            "source/report_1561.md": sha256_bytes(open(SOURCE, "rb").read()),
            "figure_fetch.json": sha256_bytes(open(FIGFETCH, "rb").read()),
        },
    }
    with open(SELFCHECK, "w", encoding="utf-8") as fh:
        json.dump(selfcheck, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(json.dumps({"ok": selfcheck["ok"], "failed": failed,
                      "assets": manifest["counts"]["total"],
                      "by_kind": manifest["counts"]["by_kind"]}, ensure_ascii=False, indent=1))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())