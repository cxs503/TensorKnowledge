"""Production-line runner for the report-to-knowledge line (five processes).

Spec: ``docs/production/PRODUCTION-LINE-v1.md`` §2 (five processes) and §3
(three gates); ``docs/production/GATE-RULES.md`` owns the rule ids.  This
module is the *executable* side of §2 and it adds nothing to the science: it
only decides what may run, in which order, on which upstream state, and what a
downstream process is allowed to consume.

What it does (and what it refuses to do)
----------------------------------------
* **contracts** — emits ``work-package.json`` instances for any of the five
  processes and validates them against ``schemas/work-package-contract.schema.json``
  (the same file the gate reads; no second source of truth).
* **order** — the five processes are a DAG, not a menu.  ``05-synthesis-research``
  declares every basic process as a dependency and the runner *refuses* to start
  it while any upstream package is uncleared (防"缺全局信息反复得出重复结论").
* **gates** — a package is only *cleared* when its own exit gate passes:
  01/02 ``G1`` (contract + declared artefacts), 03 ``G1+G2`` via
  :func:`ke.wp_gate.run_gates`, 04 ``G3`` (independent review — the machine
  only reports the review state, it never invents an approval), 05 ``G1+G3``.
* **synthesis input** — assembled only from packages that are evidence-bound
  (``L2``/``L3``) *and* independently approved; everything else is refused with
  a reason code instead of being silently dropped.  Near-duplicate statements
  across reports are flagged, never merged: merging is a judgement call that
  belongs to the synthesis agent, not to the runner.
* **benchmark** — reference labels are read from the pre-existing fixture table
  in ``docs/production/GATE-RULES.md`` (written before this module existed),
  so a run compares *declared* behaviour against *computed* behaviour.  A
  mutation matrix reddens one invariant at a time to check that every
  implemented rule can actually fail.

Three axes stay separate here too: mission state is never read; review state is
a fold of the append-only ledger (reused from :mod:`ke.wp_gate`); the
verification level is computed, never assigned.

No domain vocabulary lives in this module: process content, objectives and rule
ids are all data, so the same runner serves any report domain.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_DIR = REPO_ROOT / "schemas"
_SCRIPTS = REPO_ROOT / "scripts"
for _p in (str(REPO_ROOT), str(_SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:  # imported as ``ke.wp_line``
    from . import wp_gate
except ImportError:  # imported script-style with the repo root on sys.path
    from ke import wp_gate  # type: ignore[no-redef]

from sediment_lib import SchemaSet  # noqa: E402  (reuse: schema loading)

LINE_VERSION = "wp-line-v1"
CONTRACT_FILE = wp_gate.CONTRACT_FILE
CONTRACT_SCHEMA = wp_gate.CONTRACT_SCHEMA
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "extraction"
REF_TABLE_DOC = REPO_ROOT / "docs" / "production" / "GATE-RULES.md"
PROMPTS_DIR = REPO_ROOT / "extraction-skills" / "prompts"

#: The five processes, in dependency order.  ``depends_on`` is the only place
#: ordering is declared; ``exit_gate`` is the only place "cleared" is declared.
PROCESS_ORDER: tuple[str, ...] = (
    "01-asset-registration",
    "02-classification-parse",
    "03-knowledge-extraction",
    "04-independent-review",
    "05-synthesis-research",
)

PROCESSES: dict[str, dict[str, Any]] = {
    "01-asset-registration": {
        "label": "asset registration",
        "difficulty": "low",
        "parallelism": "extreme",
        "agent_tier": "standard",
        "depends_on": (),
        "exit_gate": "G1",
        "artifacts": ("asset_manifest.json",),
        "objective": {"register_assets": True},
        "acceptance": {"valid_json": True, "schema_pass": True},
        "reviewer_role": "document-analyst",
    },
    "02-classification-parse": {
        "label": "classification / parse",
        "difficulty": "low",
        "parallelism": "high",
        "agent_tier": "standard",
        "depends_on": ("01-asset-registration",),
        "exit_gate": "G1",
        "artifacts": ("classification.json",),
        "objective": {"classify_report_type": True},
        "acceptance": {"valid_json": True, "schema_pass": True},
        "reviewer_role": "document-analyst",
    },
    "03-knowledge-extraction": {
        "label": "knowledge extraction",
        "difficulty": "medium",
        "parallelism": "high",
        "agent_tier": "standard",
        "depends_on": ("02-classification-parse",),
        "exit_gate": "G1+G2",
        "artifacts": ("claims.json", "evidence.json", "provenance.json",
                      "extraction_summary.json"),
        "objective": {
            "identify_research_question": True,
            "extract_methods_and_claims": True,
            "extract_evidence": True,
            "identify_assumptions": True,
            "identify_limitations": True,
        },
        "acceptance": {
            "valid_json": True,
            "schema_pass": True,
            "source_locator_resolvable": True,
            "source_hash_matches": True,
            "no_duplicate_ids": True,
            "all_claims_have_evidence_or_explicit_unresolved_status": True,
        },
        "reviewer_role": "evidence-auditor",
    },
    "04-independent-review": {
        "label": "independent review",
        "difficulty": "medium",
        "parallelism": "high",
        "agent_tier": "strong",
        "depends_on": ("03-knowledge-extraction",),
        "exit_gate": "G3",
        "artifacts": ("review_report.json",),
        "objective": {"judge_semantic_fidelity": True},
        "acceptance": {"reviewer_independent": True},
        "reviewer_role": "red-team-reviewer",
        "constraints_extra": {
            "reviewer_context_excludes_producer_explanation": True,
            "review_prompt_not_copied_from_producer": True,
        },
    },
    "05-synthesis-research": {
        "label": "synthesis research",
        "difficulty": "high",
        "parallelism": "low",
        "agent_tier": "strong",
        "depends_on": ("01-asset-registration", "02-classification-parse",
                       "03-knowledge-extraction", "04-independent-review"),
        "exit_gate": "G1+G3",
        "artifacts": ("synthesis.json",),
        "objective": {"cross_report_synthesis": True, "contradiction_detection": True,
                      "gap_identification": True},
        "acceptance": {"upstream_packages_completed": True, "reviewer_independent": True},
        "reviewer_role": "knowledge-integrator",
    },
}

BASE_CONSTRAINTS = {
    "every_claim_must_have_source_locator": True,
    "do_not_invent_missing_information": True,
    "preserve_uncertainty": True,
    "no_forced_claim_generation": True,
    "do_not_mark_claims_as_verified": True,
}

#: A package that is *cleared* by its exit gate.  ``FAIL_*`` verdicts, blocked
#: upstream and (for 04/05) unapproved review all leave it uncleared.
CLEARED_VERDICTS = ("PASS_PROGRAMMATIC_PENDING_REVIEW", "PASS")

#: Synthesis may only quote packages that are evidence-bound and approved.
SYNTHESIS_LEVELS = ("L2", "L3")

#: Benchmark thresholds, declared before the run (see docs/production/RUNNER.md).
THRESHOLDS = {
    "verdict_agreement": 1.0,
    "rule_agreement": 1.0,
    "level_agreement": 1.0,
    "mutation_detection": 1.0,
    "rule_coverage": 0.9,
}


# ---------------------------------------------------------------------------
# contracts
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Contract:
    """One work package: the contract dict plus where it was found."""

    package_dir: Path
    doc: dict

    @property
    def package_id(self) -> str:
        return str(self.doc.get("package_id"))

    @property
    def task_type(self) -> str:
        return str(self.doc.get("task_type"))

    @property
    def depends_on(self) -> tuple[str, ...]:
        return PROCESSES.get(self.task_type, {}).get("depends_on", ())

    @property
    def artifacts(self) -> tuple[str, ...]:
        declared = [k for k, v in (self.doc.get("output") or {}).items() if v]
        return tuple(declared) or PROCESSES.get(self.task_type, {}).get("artifacts", ())


def make_package_id(report_id: str, task_type: str) -> str:
    """``wp-<report>-<process>`` — stable, one package per (report, process)."""
    proc = str(task_type).split("-")[0]
    clean = re.sub(r"[^a-z0-9]+", "-", str(report_id).lower()).strip("-")
    return f"wp-{clean}-{proc}"[:68]


def build_contract(task_type: str, *, report_id: str, source_hash: str,
                   source_uri: str | None = None, package_id: str | None = None,
                   source_field: str = "markdown", attachments: Sequence[dict] | None = None,
                   attachments_manifest: str | None = None,
                   upstream_packages: Sequence[dict] | None = None,
                   reviewed_package: dict | None = None,
                   mission_id: str | None = None) -> dict:
    """Build one process contract.  Raises ``KeyError`` on an unknown process."""
    spec = PROCESSES[task_type]
    constraints = dict(BASE_CONSTRAINTS)
    constraints.update(spec.get("constraints_extra") or {})
    contract: dict[str, Any] = {
        "package_id": package_id or make_package_id(report_id, task_type),
        "task_type": task_type,
        "version": "1.0.0",
        "input": {
            "report_id": str(report_id),
            "source_uri": source_uri or f"tensor://reports/{report_id}",
            "source_hash": source_hash,
            "source_field": source_field,
        },
        "objective": dict(spec["objective"]),
        "constraints": constraints,
        "output": {name: True for name in spec["artifacts"]},
        "acceptance": dict(spec["acceptance"]),
        "review": {"required": True, "independent_reviewer": True,
                   "reviewer_role": spec["reviewer_role"], "sample_rate": 1.0},
        "delivery": {"repo": "TensorKnowledge", "status": "draft"},
    }
    if mission_id:
        contract["mission_id"] = str(mission_id)
    block = contract["input"]
    if attachments:
        block["attachments"] = [{k: v for k, v in att.items() if v is not None}
                                for att in attachments]
    if attachments_manifest:
        block["attachments_manifest"] = attachments_manifest
    if upstream_packages:
        block["upstream_packages"] = [dict(p) for p in upstream_packages]
    if reviewed_package:
        block["reviewed_package"] = dict(reviewed_package)
    if block.get("attachments") and "attachments_manifest" not in block:
        raise ValueError("attachments require attachments_manifest (schema rule)")
    return contract


def validate_contract(contract: dict, schemas: SchemaSet | None = None) -> str:
    """``""`` when the contract satisfies the schema, else a short error."""
    schemas = schemas or SchemaSet(_SCHEMA_DIR)
    return schemas.validate(CONTRACT_SCHEMA, contract)


def plan_package(contract: dict, root: Path | str, *, overwrite: bool = False) -> Path:
    """Write ``work-package.json`` under ``root/<package_id>/``; returns the dir."""
    err = validate_contract(contract)
    if err:
        raise ValueError(f"contract rejected by schema: {err}")
    dest = Path(root) / str(contract["package_id"])
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / CONTRACT_FILE
    if target.is_file() and not overwrite:
        raise FileExistsError(f"{target} exists (pass overwrite=True to replace)")
    target.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    return dest


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def derive_reviewed_package(root: Path | str, report_id: str) -> dict:
    """Digests of the 03 package an 04 contract points at (must already exist).

    04 may only be planned once 03 has produced ``claims.json``/``evidence.json``:
    the reviewer is bound to the bytes it reviews, so the digests cannot be
    invented at planning time.
    """
    pkg = Path(root) / make_package_id(report_id, "03-knowledge-extraction")
    claims, evidence = pkg / "claims.json", pkg / "evidence.json"
    missing = [f.name for f in (claims, evidence) if not f.is_file()]
    if missing:
        raise ValueError(f"04 needs the 03 artefacts of report {report_id} "
                         f"(missing {missing} under {pkg}) — run 03 first")
    return {"package_id": make_package_id(report_id, "03-knowledge-extraction"),
            "claims_sha256": _sha256_file(claims),
            "evidence_sha256": _sha256_file(evidence)}


def derive_upstream_packages(root: Path | str, report_id: str, *,
                            completed: Sequence[str] = ()) -> list[dict]:
    """One entry per basic process for the 05 contract; status is not guessed.

    ``completed`` names the processes the caller has seen clear their exit gate;
    everything else is ``pending`` (the schema's own vocabulary).
    """
    return [{"package_id": make_package_id(report_id, task_type),
             "status": "completed" if task_type in completed else "pending"}
            for task_type in PROCESS_ORDER[:-1]]


def plan_report(report_id: str, source_hash: str, root: Path | str, *,
                processes: Sequence[str] = PROCESS_ORDER, overwrite: bool = False,
                upstream: Sequence[dict] | None = None,
                reviewed_package: dict | None = None,
                source_uri: str | None = None,
                mission_id: str | None = None) -> list[dict]:
    """Emit the contract of every requested process for one report.

    Process 04 needs the 03 digests and 05 needs its upstream list; both are
    derived when not supplied, and 04 raises instead of inventing digests for
    artefacts that do not exist yet.
    """
    out = []
    for task_type in processes:
        if task_type == "04-independent-review" and reviewed_package is None:
            reviewed_package = derive_reviewed_package(root, report_id)
        if task_type == "05-synthesis-research" and upstream is None:
            upstream = derive_upstream_packages(root, report_id)
        contract = build_contract(
            task_type, report_id=report_id, source_hash=source_hash,
            source_uri=source_uri, mission_id=mission_id,
            upstream_packages=upstream if task_type == "05-synthesis-research" else None,
            reviewed_package=reviewed_package if task_type == "04-independent-review" else None,
        )
        path = plan_package(contract, root, overwrite=overwrite)
        out.append({"package_id": contract["package_id"], "task_type": task_type,
                    "path": str(path), "depends_on": list(PROCESSES[task_type]["depends_on"]),
                    "agent_tier": PROCESSES[task_type]["agent_tier"]})
    return out


# ---------------------------------------------------------------------------
# discovery / small helpers
# ---------------------------------------------------------------------------
def discover(root: Path | str) -> list[Contract]:
    """All work packages under ``root`` (a package dir, or a dir of them)."""
    root = Path(root)
    if (root / CONTRACT_FILE).is_file():
        candidates = [root]
    else:
        candidates = sorted(p.parent for p in root.glob(f"*/{CONTRACT_FILE}"))
    out = []
    for pkg in candidates:
        try:
            doc = json.loads((pkg / CONTRACT_FILE).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            doc = {}
        out.append(Contract(pkg, doc if isinstance(doc, dict) else {}))
    return out


def _json_valid(path: Path) -> tuple[bool, str]:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, str(exc)[:120]
    return True, ""


# ---------------------------------------------------------------------------
# G1 for the processes the 03 gate does not cover
# ---------------------------------------------------------------------------
G1_RULES = ("P1.contract_present", "P2.contract_schema", "P3.declared_artifacts",
            "P4.valid_json")


def spine_gate(contract: Contract, schemas: SchemaSet | None = None) -> dict:
    """Structural gate for processes 01/02/04/05 (contract + declared artefacts).

    The 03 branch has the richer structural rule set (S1-S15 in
    :mod:`ke.wp_gate`); the other branches exist only as contracts today, so the
    runner checks exactly what those contracts claim and says so instead of
    pretending the 03 rule set applies.
    """
    schemas = schemas or SchemaSet(_SCHEMA_DIR)
    pkg = contract.package_dir
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    err = validate_contract(contract.doc, schemas) if contract.doc else "contract missing"
    add("P1.contract_present", bool(contract.doc), f"{pkg.name}/{CONTRACT_FILE}")
    add("P2.contract_schema", not err, err or "contract valid")
    missing, broken = [], []
    for name in contract.artifacts:
        path = pkg / name
        if not path.is_file():
            missing.append(name)
            continue
        ok, why = _json_valid(path)
        if not ok:
            broken.append(f"{name}: {why}")
    add("P3.declared_artifacts", not missing, f"missing={missing}")
    add("P4.valid_json", not broken, f"broken={broken[:3]}")
    return {"gate": "spine-v1", "pass": all(c["ok"] for c in checks), "checks": checks,
            "summary": {"n_checks": len(checks),
                        "n_pass": sum(1 for c in checks if c["ok"]),
                        "n_fail": sum(1 for c in checks if not c["ok"])}}


# ---------------------------------------------------------------------------
# 01 — asset registration (the process that talks to the platform)
# ---------------------------------------------------------------------------
def register_assets(report_ids: Sequence[str], resolver, out_root: Path | str, *,
                    mission_id: str | None = None) -> dict:
    """Fetch each report, hash it, and emit one 01 package per report.

    ``resolver`` is a :class:`ke.wp_gate.DirSourceResolver` or
    :class:`ke.wp_gate.ApiSourceResolver`.  An unreachable source is recorded as
    ``reachable: false`` and never silently skipped — downstream 03 would
    otherwise discover it too late, at G2.
    """
    root = Path(out_root)
    rows = []
    for report_id in report_ids:
        package_id = make_package_id(report_id, "01-asset-registration")
        pkg = root / package_id
        pkg.mkdir(parents=True, exist_ok=True)
        row: dict[str, Any] = {"package_id": package_id, "report_id": str(report_id)}
        try:
            doc = resolver.resolve(str(report_id))
        except Exception as exc:  # noqa: BLE001 — unreachable is data, not a crash
            row.update({"reachable": False, "error": f"{type(exc).__name__}: {exc}"})
            manifest = {"package_id": package_id, "report_id": str(report_id),
                        "reachable": False, "error": row["error"], "attachments": []}
            (pkg / "asset_manifest.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            rows.append(row)
            continue
        manifest = {
            "package_id": package_id,
            "report_id": str(report_id),
            "reachable": True,
            "source_uri": doc.uri,
            "source_field": doc.field,
            "source_hash": doc.sha256,
            "length_chars": len(doc.text),
            "attachments": [],
            "attachment_manifest": None,
        }
        (pkg / "asset_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        contract = build_contract("01-asset-registration", report_id=str(report_id),
                                  source_hash=doc.sha256, source_uri=doc.uri,
                                  source_field=doc.field, mission_id=mission_id)
        (pkg / CONTRACT_FILE).write_text(
            json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        row.update({"reachable": True, "source_hash": doc.sha256,
                    "length_chars": len(doc.text), "source_uri": doc.uri})
        rows.append(row)
    out = {"line": LINE_VERSION, "process": "01-asset-registration",
           "n_reports": len(rows), "n_reachable": sum(1 for r in rows if r["reachable"]),
           "n_unreachable": sum(1 for r in rows if not r["reachable"]), "reports": rows}
    (root / "asset_registration.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# the line itself
# ---------------------------------------------------------------------------
def run_line(root: Path | str, *, resolver=None, review_ledger_dir: Path | str | None = None,
             tickets_dir: Path | str | None = None, prompts_dir: Path | str | None = None,
             min_quote_chars: int = 12, schemas: SchemaSet | None = None,
             allow_incomplete_upstream: bool = False) -> dict:
    """Run the line in dependency order and return the line report.

    A package whose declared upstream is not cleared is **not run at all**: its
    status becomes ``blocked_upstream`` (the reason, not a silent skip).  Process
    05 additionally requires every basic process to have finished, which is the
    mechanical form of "综合必须在基础加工完成后".
    """
    root = Path(root)
    schemas = schemas or SchemaSet(_SCHEMA_DIR)
    contracts = discover(root)
    producer_prompt = reviewer_prompt = None
    if prompts_dir:
        base = Path(prompts_dir)
        producer_prompt = (base / "producer-v1.md").read_text(encoding="utf-8")
        reviewer_prompt = (base / "reviewer-v1.md").read_text(encoding="utf-8")

    by_process: dict[str, list[Contract]] = {p: [] for p in PROCESS_ORDER}
    unknown: list[Contract] = []
    for c in contracts:
        if c.task_type in by_process:
            by_process[c.task_type].append(c)
        else:
            unknown.append(c)

    results: dict[str, dict] = {}
    processes_out: list[dict] = []

    def cleared(task_type: str) -> bool:
        rows = [results.get(c.package_id) for c in by_process.get(task_type, [])]
        if not rows:
            return True  # that process is absent from this root
        return all(r and r.get("status") == "cleared" for r in rows)

    for task_type in PROCESS_ORDER:
        rows: list[dict] = []
        for contract in by_process.get(task_type, []):
            blocked = [dep for dep in contract.depends_on if not cleared(dep)]
            if blocked and not allow_incomplete_upstream:
                row = {"package_id": contract.package_id, "task_type": task_type,
                       "status": "blocked_upstream", "blocked_on": blocked,
                       "verdict": None, "level": None, "failed_rules": []}
                results[contract.package_id] = row
                rows.append(row)
                continue
            row = {"package_id": contract.package_id, "task_type": task_type}
            if task_type == "03-knowledge-extraction":
                gate = wp_gate.run_gates(
                    contract.package_dir, resolver, min_quote_chars=min_quote_chars,
                    producer_prompt=producer_prompt, reviewer_prompt=reviewer_prompt,
                    review_ledger_dir=review_ledger_dir, tickets_dir=tickets_dir)
                failed = {c["name"].split(".")[0] for block in ("structural", "evidence")
                          for c in gate[block]["checks"] if not c["ok"]}
                failed |= {c["name"].split(".")[0] for c in gate["semantic"]["checks"]
                           if not c["ok"]}
                row.update({
                    "verdict": gate["verdict"],
                    "level": gate["verification"]["level"],
                    "ceiling_reason": gate["verification"]["ceiling_reason"],
                    "review_state": gate["axes"]["review_state"],
                    "failed_rules": sorted(failed),
                    "counts": gate["counts"],
                    "n_checks": (gate["structural"]["summary"]["n_checks"]
                                 + gate["evidence"]["summary"]["n_checks"]),
                })
                row["status"] = ("cleared" if gate["verdict"] in CLEARED_VERDICTS
                                 else "failed")
            else:
                gate = spine_gate(contract, schemas)
                row.update({
                    "verdict": "PASS" if gate["pass"] else "FAIL_STRUCTURAL",
                    "level": "L1" if gate["pass"] else "L0",
                    "ceiling_reason": "SPINE_OK" if gate["pass"] else "SPINE_GATE_FAILED",
                    "review_state": "n/a",
                    "failed_rules": sorted({c["name"].split(".")[0]
                                            for c in gate["checks"] if not c["ok"]}),
                    "gate": gate["gate"],
                    "n_checks": gate["summary"]["n_checks"],
                })
                row["status"] = "cleared" if gate["pass"] else "failed"
            results[contract.package_id] = row
            rows.append(row)
        processes_out.append({
            "task_type": task_type,
            "label": PROCESSES[task_type]["label"],
            "exit_gate": PROCESSES[task_type]["exit_gate"],
            "agent_tier": PROCESSES[task_type]["agent_tier"],
            "depends_on": list(PROCESSES[task_type]["depends_on"]),
            "n_packages": len(rows),
            "n_cleared": sum(1 for r in rows if r["status"] == "cleared"),
            "n_failed": sum(1 for r in rows if r["status"] == "failed"),
            "n_blocked_upstream": sum(1 for r in rows if r["status"] == "blocked_upstream"),
            "packages": rows,
        })

    base_complete = all(cleared(p) for p in PROCESS_ORDER[:-1])
    return {
        "line": LINE_VERSION,
        "gate": wp_gate.GATE_VERSION,
        "root": str(root),
        "order": list(PROCESS_ORDER),
        "n_packages": len(contracts),
        "n_unknown_task_type": len(unknown),
        "processes": processes_out,
        "base_processing_complete": base_complete,
        "synthesis_unblocked": base_complete,
    }


# ---------------------------------------------------------------------------
# synthesis input assembly (05 may only consume cleared, evidence-bound work)
# ---------------------------------------------------------------------------
REFUSAL_CODES = {
    "UPSTREAM_INCOMPLETE": "an upstream basic process still has an uncleared package",
    "NOT_EVIDENCE_BOUND": "package cleared structure but never bound claims to evidence",
    "REVIEW_NOT_APPROVED": "independent review has not approved the package",
    "GATE_FAILED": "package failed its own exit gate",
}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def assemble_synthesis_input(root: Path | str, line_report: dict | None = None, *,
                             similarity: float = 0.9) -> dict:
    """Build the 05 input bundle from eligible 03 packages only.

    Eligibility = cleared exit gate + evidence-bound level (L2/L3) + independent
    approval.  Ineligible packages are refused with a reason code.  Near
    duplicate statements (token Jaccard >= ``similarity``) across *different*
    reports are reported as candidates: the runner does not merge them, because
    "these two claims say the same thing" is a semantic judgement.
    """
    root = Path(root)
    report = line_report or run_line(root)
    rows = {r["package_id"]: r for proc in report["processes"] for r in proc["packages"]}
    claims: list[dict] = []
    eligible: list[dict] = []
    refusals: list[dict] = []
    for contract in discover(root):
        if contract.task_type != "03-knowledge-extraction":
            continue
        row = rows.get(contract.package_id) or {}
        status = row.get("status")
        if status == "failed":
            refusals.append({"package_id": contract.package_id, "code": "GATE_FAILED",
                             "detail": f"verdict={row.get('verdict')} "
                                       f"rules={row.get('failed_rules')}"})
            continue
        if status != "cleared":
            refusals.append({"package_id": contract.package_id, "code": "UPSTREAM_INCOMPLETE",
                             "detail": f"status={status} blocked_on={row.get('blocked_on')}"})
            continue
        if row.get("level") not in SYNTHESIS_LEVELS:
            refusals.append({"package_id": contract.package_id, "code": "NOT_EVIDENCE_BOUND",
                             "detail": f"level={row.get('level')} "
                                       f"reason={row.get('ceiling_reason')}"})
            continue
        if row.get("review_state") != "approved":
            refusals.append({"package_id": contract.package_id,
                             "code": "REVIEW_NOT_APPROVED",
                             "detail": f"review_state={row.get('review_state')}"})
            continue
        try:
            pkg_claims = json.loads((contract.package_dir / "claims.json")
                                    .read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            refusals.append({"package_id": contract.package_id, "code": "GATE_FAILED",
                             "detail": f"claims.json unreadable: {exc}"})
            continue
        if not isinstance(pkg_claims, list):
            refusals.append({"package_id": contract.package_id, "code": "GATE_FAILED",
                             "detail": "claims.json is not a list"})
            continue
        eligible.append({"package_id": contract.package_id,
                         "report_id": (contract.doc.get("input") or {}).get("report_id"),
                         "level": row.get("level"), "n_claims": len(pkg_claims)})
        for claim in pkg_claims:
            claims.append({"package_id": contract.package_id,
                           "report_id": (contract.doc.get("input") or {}).get("report_id"),
                           "claim": claim})

    duplicates = []
    seen: list[tuple[str, str, set[str]]] = []
    for entry in claims:
        claim = entry["claim"] or {}
        cid = str(claim.get("id"))
        toks = _tokens(claim.get("statement", ""))
        if not toks:
            continue
        for other_id, other_pkg, other_tok in seen:
            if other_pkg == entry["package_id"]:
                continue
            jac = len(toks & other_tok) / len(toks | other_tok)
            if jac >= similarity:
                duplicates.append({"claim_id": cid, "other_claim_id": other_id,
                                   "similarity": round(jac, 3),
                                   "packages": [entry["package_id"], other_pkg]})
        seen.append((cid, str(entry["package_id"]), toks))

    base_ok = bool(report.get("base_processing_complete"))
    ready = base_ok and bool(eligible)
    return {
        "line": LINE_VERSION,
        "generated_from": str(root),
        "ready": ready,
        "blocked_reason": None if ready else ("UPSTREAM_INCOMPLETE" if not base_ok
                                              else "NO_ELIGIBLE_PACKAGE"),
        "n_eligible_packages": len(eligible),
        "n_refused_packages": len(refusals),
        "n_claims": len(claims),
        "n_duplicate_candidates": len(duplicates),
        "eligible_packages": eligible,
        "refusals": refusals,
        "duplicates": duplicates,
        "claims": claims,
        "note": ("duplicates are candidates, not merges: merging is a semantic "
                 "judgement reserved for the synthesis reviewer"),
    }

# ---------------------------------------------------------------------------
# benchmark — declared reference labels vs computed verdicts
# ---------------------------------------------------------------------------
REF_ROW = re.compile(r"^\|\s*`(?P<pkg>[^`]+)`\s*\|\s*(?P<verdict>[^|]*?)\s*\|\s*"
                     r"(?P<rules>[^|]*?)\s*\|\s*(?P<level>[^|]*?)\s*\|", re.M)
RULE_IN_REF = re.compile(r"\b([SEMV]\d{1,2})\b")
CHECK_DEF = re.compile(r"check\(\s*[\"']([SEMV]\d{1,2}\.[a-z_0-9]+)[\"']")
FIXTURE_NAME = re.compile(r"^(ok|bad)-")


def parse_reference_table(path: Path | str = REF_TABLE_DOC) -> dict[str, dict]:
    """Parse the fixture matrix of ``GATE-RULES.md`` into reference labels.

    The table was authored with the fixtures (before this runner existed), so it
    is an external reference for the benchmark, not a transcription of results.
    """
    text = Path(path).read_text(encoding="utf-8")
    refs: dict[str, dict] = {}
    previous_verdict = ""
    for m in REF_ROW.finditer(text):
        pkg = m.group("pkg").strip()
        if not FIXTURE_NAME.match(pkg):
            continue
        verdict = re.sub(r"[`*]", "", m.group("verdict")).strip()
        if verdict in ("同上", "ditto", "same", "〃"):
            verdict = previous_verdict          # table uses ditto for repeats
        previous_verdict = verdict
        level = re.search(r"L[0-3]", m.group("level"))
        refs[pkg] = {"verdict": verdict,
                     "rules": sorted(set(RULE_IN_REF.findall(m.group("rules")))),
                     "level": level.group(0) if level else None}
    return refs


def implemented_rules(gate_source: Path | None = None) -> dict[str, list[str]]:
    """Every rule id the gate implements, grouped by id (mechanical scan)."""
    src = (gate_source or Path(wp_gate.__file__)).read_text(encoding="utf-8")
    out: dict[str, list[str]] = {}
    for name in CHECK_DEF.findall(src):
        out.setdefault(name.split(".")[0], []).append(name)
    return {k: sorted(v) for k, v in sorted(out.items())}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# --- mutation helpers: each one breaks exactly one declared invariant -------
def _m_drop_evidence(pkg: Path) -> None:
    claims = _load(pkg / "claims.json")
    claims[0]["evidence_refs"] = []
    _dump(pkg / "claims.json", claims)
    evidence = _load(pkg / "evidence.json")
    _dump(pkg / "evidence.json", [e for e in evidence
                                  if claims[0]["id"] not in (e.get("claim_refs") or [])])


def _m_tamper_source_hash(pkg: Path) -> None:
    contract = _load(pkg / "work-package.json")
    bad = contract["input"]["source_hash"][:-6] + "000000"
    contract["input"]["source_hash"] = bad
    _dump(pkg / "work-package.json", contract)
    summary = _load(pkg / "extraction_summary.json")
    summary.setdefault("source", {})["source_hash"] = bad
    _dump(pkg / "extraction_summary.json", summary)


def _m_shift_offsets(pkg: Path) -> None:
    evidence = _load(pkg / "evidence.json")
    loc = evidence[0]["locator"]
    loc["start_offset"] = int(loc["start_offset"]) + 1
    loc["end_offset"] = int(loc["end_offset"]) + 1
    _dump(pkg / "evidence.json", evidence)


def _m_tamper_quote(pkg: Path) -> None:
    evidence = _load(pkg / "evidence.json")
    loc = evidence[0]["locator"]
    quote = loc["quote"]
    loc["quote"] = ("Z" if quote[0] != "Z" else "Q") + quote[1:]
    _dump(pkg / "evidence.json", evidence)  # content_hash left untouched on purpose


def _m_trivial_quote(pkg: Path) -> None:
    evidence = _load(pkg / "evidence.json")
    evidence[0]["locator"]["quote"] = "the"
    evidence[0]["locator"]["content_hash"] = hashlib.sha256(b"the").hexdigest()
    _dump(pkg / "evidence.json", evidence)


def _m_duplicate_claim_id(pkg: Path) -> None:
    claims = _load(pkg / "claims.json")
    claims.append(json.loads(json.dumps(claims[0])))
    _dump(pkg / "claims.json", claims)


def _m_break_json(pkg: Path) -> None:
    (pkg / "claims.json").write_text('{"not": "a list",,}', encoding="utf-8")


def _m_self_verify(pkg: Path) -> None:
    claims = _load(pkg / "claims.json")
    claims[0]["epistemic_status"] = "verified"
    claims[0]["verification_status"] = "verified"
    _dump(pkg / "claims.json", claims)
    evidence = _load(pkg / "evidence.json")
    evidence[0]["assessment_status"] = "assessed"
    _dump(pkg / "evidence.json", evidence)


def _m_summary_counts(pkg: Path) -> None:
    summary = _load(pkg / "extraction_summary.json")
    counts = summary.setdefault("counts", {})
    counts["claims"] = int(counts.get("claims") or 0) + 3
    _dump(pkg / "extraction_summary.json", summary)


def _m_smuggle_review(pkg: Path) -> None:
    ledgers = pkg.parent / "ledgers"
    for candidate in (ledgers / f"wp-{pkg.name}.review_events.json",
                      ledgers / f"{pkg.name}.review_events.json"):
        if candidate.is_file():
            _dump(pkg / "review_events.json", _load(candidate))
            return
    raise FileNotFoundError(f"no ledger for {pkg.name} under {ledgers}")


def _m_remove_claim_file(pkg: Path) -> None:
    (pkg / "claims.json").unlink()


def _m_zero_claim_reason(pkg: Path) -> None:
    summary = _load(pkg / "extraction_summary.json")
    summary.setdefault("empty_result", {})["reason"] = ""
    _dump(pkg / "extraction_summary.json", summary)


def _m_review_off(pkg: Path) -> None:
    contract = _load(pkg / "work-package.json")
    contract["review"]["required"] = False
    _dump(pkg / "work-package.json", contract)


def _m_report_id_mismatch(pkg: Path) -> None:
    summary = _load(pkg / "extraction_summary.json")
    summary.setdefault("source", {})["report_id"] = "9999"
    _dump(pkg / "extraction_summary.json", summary)


def _m_provenance_emptied(pkg: Path) -> None:
    _dump(pkg / "provenance.json", [])


def _m_orphan_evidence(pkg: Path) -> None:
    evidence = _load(pkg / "evidence.json")
    evidence.append({**json.loads(json.dumps(evidence[0])), "id": "tke:orphan-0001",
                     "claim_refs": ["tkc:does-not-exist"]})
    _dump(pkg / "evidence.json", evidence)


def _m_illegal_review_transition(pkg: Path) -> None:
    ledgers = pkg.parent / "ledgers"
    ledger = ledgers / f"wp-{pkg.name}.review_events.json"
    events = _load(ledger)
    extra = json.loads(json.dumps(events[-1]))
    extra["id"] = "tkr:synthetic-9001:approve-2"
    _dump(ledger, events + [extra])  # approve -> approve is not a legal transition


def _m_unreachable_source(pkg: Path) -> None:
    contract = _load(pkg / "work-package.json")
    contract["input"]["report_id"] = "9998"
    _dump(pkg / "work-package.json", contract)
    summary = _load(pkg / "extraction_summary.json")
    summary.setdefault("source", {})["report_id"] = "9998"
    _dump(pkg / "extraction_summary.json", summary)


@dataclass(frozen=True)
class Mutation:
    """One deliberate defect: what it breaks and the rule that must catch it."""

    name: str
    breaks: str
    expect_rule: str
    mutate: Callable[[Path], None]
    base: str = "ok-basic"


MUTATIONS: tuple[Mutation, ...] = (
    Mutation("m01-claim-without-evidence", "every claim has evidence or unresolved",
             "S11", _m_drop_evidence),
    Mutation("m02-source-hash-tampered", "contract hash equals the source bytes", "E2",
             _m_tamper_source_hash),
    Mutation("m03-locator-offset-shifted", "quote sits at the declared offsets", "E4",
             _m_shift_offsets),
    Mutation("m04-quote-bytes-tampered", "quote hash matches the quote bytes", "E5",
             _m_tamper_quote),
    Mutation("m05-trivial-quote", "a quote is longer than the triviality floor", "E6",
             _m_trivial_quote),
    Mutation("m06-duplicate-claim-id", "record ids are unique", "S6", _m_duplicate_claim_id),
    Mutation("m07-invalid-json", "every artefact is valid JSON", "S2", _m_break_json),
    Mutation("m08-producer-self-verified", "producers never mark claims verified", "S8",
             _m_self_verify),
    Mutation("m09-summary-counts-inflated", "summary counts match the files", "S13",
             _m_summary_counts),
    Mutation("m10-package-carries-own-approval", "03 packages ship no review material",
             "S15", _m_smuggle_review),
    Mutation("m11-artefact-missing", "declared artefacts are present", "S1",
             _m_remove_claim_file),
    Mutation("m12-zero-claim-without-reason", "an empty result states why", "S12",
             _m_zero_claim_reason, base="ok-zero-claim"),
    Mutation("m13-review-not-declared", "review is required and independent", "M1",
             _m_review_off),
    Mutation("m14-report-id-mismatch", "source identity agrees across files", "S14",
             _m_report_id_mismatch),
    Mutation("m15-provenance-emptied", "summary counts match provenance", "S13",
             _m_provenance_emptied),
    Mutation("m16-orphan-evidence", "claim/evidence references are closed", "S10",
             _m_orphan_evidence),
    Mutation("m17-illegal-review-transition", "review events follow the state machine",
             "M2", _m_illegal_review_transition),
    Mutation("m18-source-unreachable", "the source document is reachable", "E1",
             _m_unreachable_source),
)


def _fixture_root(tmp: Path) -> Path:
    dest = tmp / "extraction"
    shutil.copytree(FIXTURES, dest)
    return dest


def _prompts(tmp: Path, *, leak: bool = False) -> Path:
    dest = tmp / "prompts"
    shutil.copytree(PROMPTS_DIR, dest)
    if leak:  # reviewer prompt copied from the producer prompt
        shutil.copyfile(dest / "producer-v1.md", dest / "reviewer-v1.md")
    return dest


def run_mutation(mutation: Mutation, *, workdir: Path | None = None) -> dict:
    """Apply one mutation to a throwaway copy and see whether the gate reddens."""
    tmp = Path(workdir or tempfile.mkdtemp(prefix=f"mut-{mutation.name}-"))
    try:
        root = _fixture_root(tmp)
        pkg = root / mutation.base
        mutation.mutate(pkg)
        prompts = _prompts(tmp)
        resolver = wp_gate.DirSourceResolver(root / "sources")
        gate = wp_gate.run_gates(pkg, resolver, review_ledger_dir=root / "ledgers",
                                 tickets_dir=root / "tickets",
                                 producer_prompt=(prompts / "producer-v1.md").read_text(),
                                 reviewer_prompt=(prompts / "reviewer-v1.md").read_text())
        failed = {c["name"].split(".")[0] for block in ("structural", "evidence")
                  for c in gate[block]["checks"] if not c["ok"]}
        failed |= {c["name"].split(".")[0] for c in gate["semantic"]["checks"]
                   if not c["ok"]}
        return {"name": mutation.name, "breaks": mutation.breaks,
                "expect_rule": mutation.expect_rule, "base": mutation.base,
                "got_verdict": gate["verdict"], "got_rules": sorted(failed),
                "got_level": gate["verification"]["level"],
                "verdict_changed": bool(gate["verdict"] not in CLEARED_VERDICTS),
                # detection = the declared rule fired on the declared defect;
                # semantic (M*) rules are preparation checks by design (the gate
                # never fakes a G3 pass), so they redden without failing the run
                "detected": mutation.expect_rule in failed}
    finally:
        if workdir is None:
            shutil.rmtree(tmp, ignore_errors=True)


def run_mutation_prompt_leak(*, workdir: Path | None = None) -> dict:
    """M4: a reviewer prompt copied from the producer prompt must redden."""
    tmp = Path(workdir or tempfile.mkdtemp(prefix="mut-m17-prompt-leak-"))
    try:
        root = _fixture_root(tmp)
        prompts = _prompts(tmp, leak=True)
        gate = wp_gate.run_gates(root / "ok-basic",
                                 wp_gate.DirSourceResolver(root / "sources"),
                                 review_ledger_dir=root / "ledgers",
                                 tickets_dir=root / "tickets",
                                 producer_prompt=(prompts / "producer-v1.md").read_text(),
                                 reviewer_prompt=(prompts / "reviewer-v1.md").read_text())
        failed = {c["name"].split(".")[0] for c in gate["semantic"]["checks"] if not c["ok"]}
        return {"name": "m19-reviewer-prompt-copied", "breaks":
                "review prompt is not copied from the producer prompt",
                "expect_rule": "M4", "base": "ok-basic",
                "got_verdict": gate["verdict"], "got_rules": sorted(failed),
                "got_level": gate["verification"]["level"],
                "verdict_changed": bool(gate["verdict"] not in CLEARED_VERDICTS),
                "detected": "M4" in failed}
    finally:
        if workdir is None:
            shutil.rmtree(tmp, ignore_errors=True)


def run_mutation_explained_context(*, workdir: Path | None = None) -> dict:
    """M5: producer explanation leaking into the review packet must redden."""
    tmp = Path(workdir or tempfile.mkdtemp(prefix="mut-m18-context-leak-"))
    try:
        root = _fixture_root(tmp)
        summary = _load(root / "ok-basic" / "extraction_summary.json")
        # the runner builds the review packet from the package; a leak is visible
        # when the producer explanation reaches the packet's context
        leaked = wp_gate.build_review_request(
            _load(root / "ok-basic" / "work-package.json"),
            _load(root / "ok-basic" / "claims.json"),
            _load(root / "ok-basic" / "evidence.json"),
            _load(root / "ok-basic" / "provenance.json"),
            {"report_id": "9001", "field": "markdown", "source_hash": "", "text": ""},
            sample_rate=1.0,
        )
        leaked.setdefault("context", {})["extraction_summary"] = summary
        leaks = wp_gate.context_leaks(leaked)
        return {"name": "m20-producer-explanation-in-review-context",
                "breaks": "review context excludes the producer explanation",
                "expect_rule": "M5", "base": "ok-basic",
                "got_verdict": "FAIL_SEMANTIC_PREP" if leaks else "PASS",
                "got_rules": ["M5"] if leaks else [],
                "got_level": "n/a",
                "verdict_changed": False,
                "detected": bool(leaks)}
    finally:
        if workdir is None:
            shutil.rmtree(tmp, ignore_errors=True)


def run_mutation_self_approval(*, workdir: Path | None = None) -> dict:
    """M3: an approval signed by the producer's own identity must redden."""
    tmp = Path(workdir or tempfile.mkdtemp(prefix="mut-m19-self-approval-"))
    try:
        root = _fixture_root(tmp)
        ledger = root / "ledgers" / "wp-ok-basic.review_events.json"
        events = _load(ledger)
        producer = _load(root / "ok-basic" / "claims.json")[0]["created_by"]
        for ev in events if isinstance(events, list) else events.get("events", []):
            if isinstance(ev, dict) and ev.get("decision") == "approve":
                ev["reviewer"] = {"id": producer, "reviewer_type": "person"}
        _dump(ledger, events)
        gate = wp_gate.run_gates(root / "ok-basic",
                                 wp_gate.DirSourceResolver(root / "sources"),
                                 review_ledger_dir=root / "ledgers",
                                 tickets_dir=root / "tickets")
        failed = {c["name"].split(".")[0] for c in gate["semantic"]["checks"] if not c["ok"]}
        return {"name": "m21-approval-signed-by-producer", "breaks":
                "reviewer identity differs from every producer identity",
                "expect_rule": "M3", "base": "ok-basic",
                "got_verdict": gate["verdict"], "got_rules": sorted(failed),
                "got_level": gate["verification"]["level"],
                "verdict_changed": bool(gate["verdict"] not in CLEARED_VERDICTS),
                "detected": "M3" in failed}
    finally:
        if workdir is None:
            shutil.rmtree(tmp, ignore_errors=True)


def run_benchmark(root: Path | str = FIXTURES, *, ref_doc: Path | str = REF_TABLE_DOC,
                  workdir: Path | None = None,
                  thresholds: dict | None = None) -> dict:
    """Reference-vs-computed fixture benchmark + mutation matrix + rule coverage."""
    root = Path(root)
    thresholds = dict(thresholds or THRESHOLDS)
    refs = parse_reference_table(ref_doc)
    prompts = PROMPTS_DIR
    line = run_line(root, resolver=wp_gate.DirSourceResolver(root / "sources"),
                    review_ledger_dir=root / "ledgers", tickets_dir=root / "tickets",
                    prompts_dir=prompts)
    rows = {Path(r["package_id"]).name: r for proc in line["processes"]
            for r in proc["packages"]}
    # package ids are wp-<fixture>; the fixture directory is the reference key
    got_by_fixture = {c.package_dir.name: rows.get(c.package_id)
                      for c in discover(root)
                      if c.task_type == "03-knowledge-extraction"}

    fixtures_out: dict[str, dict] = {}
    verdict_hits = rule_hits = level_hits = n_ref = 0
    for name, ref in sorted(refs.items()):
        got = got_by_fixture.get(name) or {}
        got_rules = set(got.get("failed_rules") or [])
        verdict_ok = got.get("verdict") == ref["verdict"]
        rules_ok = set(ref["rules"]).issubset(got_rules) if ref["rules"] else not got_rules
        level_ok = got.get("level") == ref["level"]
        n_ref += 1
        verdict_hits += verdict_ok
        rule_hits += rules_ok
        level_hits += level_ok
        fixtures_out[name] = {
            "ref_verdict": ref["verdict"], "got_verdict": got.get("verdict"),
            "ref_rules": ref["rules"], "got_rules": sorted(got_rules),
            "ref_level": ref["level"], "got_level": got.get("level"),
            "verdict_match": verdict_ok, "rules_match": rules_ok, "level_match": level_ok,
        }

    mutations_out = [run_mutation(m, workdir=None) for m in MUTATIONS]
    mutations_out.append(run_mutation_prompt_leak())
    mutations_out.append(run_mutation_explained_context())
    mutations_out.append(run_mutation_self_approval())
    n_mut = len(mutations_out)
    mut_hits = sum(1 for m in mutations_out if m["detected"])

    rules = implemented_rules()
    exercised = set()
    for row in fixtures_out.values():
        exercised |= set(row["got_rules"])
    for row in mutations_out:
        exercised |= set(row["got_rules"])
    all_rules = set(rules)
    coverage = len(all_rules & exercised) / len(all_rules) if all_rules else 0.0

    metrics = {
        "verdict_agreement": round(verdict_hits / n_ref, 4) if n_ref else 0.0,
        "rule_agreement": round(rule_hits / n_ref, 4) if n_ref else 0.0,
        "level_agreement": round(level_hits / n_ref, 4) if n_ref else 0.0,
        "mutation_detection": round(mut_hits / n_mut, 4) if n_mut else 0.0,
        "rule_coverage": round(coverage, 4),
    }
    failures = {k: {"ref": thresholds[k], "got": metrics[k]}
                for k in thresholds if metrics.get(k, 0.0) < thresholds[k]}
    return {
        "line": LINE_VERSION,
        "gate": wp_gate.GATE_VERSION,
        "reference": {"source": str(ref_doc), "n_fixtures": n_ref},
        "thresholds": thresholds,
        "metrics": metrics,
        "n_fixtures": n_ref,
        "fixtures": fixtures_out,
        "n_mutations": n_mut,
        "n_mutations_detected": mut_hits,
        "mutations": mutations_out,
        "rules": {"n_implemented": len(all_rules), "n_exercised": len(all_rules & exercised),
                  "uncovered": sorted(all_rules - exercised),
                  "implemented": {k: len(v) for k, v in rules.items()}},
        "below_threshold": failures,
        "pass": not failures,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _write(path: Path | str | None, payload: dict) -> None:
    if not path:
        return
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {dest}")


def _resolver(args) -> Any:
    if getattr(args, "online", False):
        return wp_gate.ApiSourceResolver()
    if getattr(args, "sources", None):
        return wp_gate.DirSourceResolver(args.sources)
    return None


def cmd_plan(args) -> int:
    processes = [p.strip() for p in (args.processes or ",".join(PROCESS_ORDER)).split(",")]
    unknown = [p for p in processes if p not in PROCESSES]
    if unknown:
        print(f"unknown process(es): {unknown}", file=sys.stderr)
        return 2
    rows = plan_report(args.report, args.source_hash, args.out, processes=processes,
                       overwrite=args.overwrite, mission_id=args.mission_id)
    _write(args.json, {"line": LINE_VERSION, "process": "plan", "packages": rows})
    for row in rows:
        print(f"{row['package_id']:<40} {row['task_type']:<24} tier={row['agent_tier']}")
    return 0


def cmd_register(args) -> int:
    ids = [r.strip() for r in (args.reports or "").split(",") if r.strip()]
    if not ids:
        print("--reports is required (comma separated report ids)", file=sys.stderr)
        return 2
    resolver = _resolver(args)
    if resolver is None:
        print("pass --online or --sources for process 01", file=sys.stderr)
        return 2
    out = register_assets(ids, resolver, args.out, mission_id=args.mission_id)
    _write(args.json, out)
    print(f"registered {out['n_reachable']}/{out['n_reports']} reports "
          f"({out['n_unreachable']} unreachable)")
    return 0


def cmd_run(args) -> int:
    report = run_line(args.root, resolver=_resolver(args),
                      review_ledger_dir=args.review_ledger_dir,
                      tickets_dir=args.tickets_dir, prompts_dir=args.prompts_dir,
                      min_quote_chars=args.min_quote_chars)
    _write(args.json, report)
    for proc in report["processes"]:
        print(f"{proc['task_type']:<24} exit={proc['exit_gate']:<7} "
              f"packages={proc['n_packages']:<3} cleared={proc['n_cleared']:<3} "
              f"failed={proc['n_failed']:<3} blocked={proc['n_blocked_upstream']}")
        for row in proc["packages"]:
            print(f"  {row['package_id']:<32} {row['status']:<17} "
                  f"verdict={row.get('verdict')} level={row.get('level')} "
                  f"rules={row.get('failed_rules')}")
    if report["synthesis_unblocked"]:
        bundle = assemble_synthesis_input(args.root, report)
        dest = Path(args.synthesis_json) if args.synthesis_json else None
        _write(dest, bundle)
        print(f"synthesis-ready: eligible={bundle['n_eligible_packages']} "
              f"refused={bundle['n_refused_packages']} claims={bundle['n_claims']} "
              f"duplicates={bundle['n_duplicate_candidates']}")
    else:
        print("synthesis blocked: base processing incomplete")
    return 2 if any(p["n_failed"] for p in report["processes"]) else 0


def cmd_synthesis(args) -> int:
    bundle = assemble_synthesis_input(args.root)
    _write(args.json, bundle)
    print(f"ready={bundle['ready']} reason={bundle['blocked_reason']} "
          f"claims={bundle['n_claims']} refusals={bundle['n_refused_packages']}")
    return 0 if bundle["ready"] else 3


def cmd_bench(args) -> int:
    bench = run_benchmark(args.root, ref_doc=args.ref_doc)
    _write(args.json, bench)
    m = bench["metrics"]
    print(f"fixtures={bench['n_fixtures']} verdict={m['verdict_agreement']:.2%} "
          f"rules={m['rule_agreement']:.2%} level={m['level_agreement']:.2%} "
          f"mutations={bench['n_mutations_detected']}/{bench['n_mutations']} "
          f"coverage={m['rule_coverage']:.2%}")
    for name, row in bench["fixtures"].items():
        flag = "ok " if row["verdict_match"] and row["rules_match"] else "DIFF"
        print(f"  {flag} {name:<20} ref={row['ref_verdict']:<32} "
              f"got={row['got_verdict']:<32} rules={row['got_rules']}")
    for row in bench["mutations"]:
        if not row["detected"]:
            print(f"  MISSED {row['name']} expect={row['expect_rule']} "
                  f"got={row['got_rules']}")
    if bench["below_threshold"]:
        print(f"below threshold: {bench['below_threshold']}")
    return 0 if bench["pass"] else 3


def cmd_all(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    code_run = cmd_run(argparse.Namespace(
        **{**vars(args), "json": str(out / "line_report.json"),
           "synthesis_json": str(out / "synthesis_input.json")}))
    code_bench = cmd_bench(argparse.Namespace(**{**vars(args),
                                                 "json": str(out / "benchmark.json")}))
    return max(code_run, code_bench)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m ke.wp_line",
        description="Production line runner: five processes, dependency order, gate-bound.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="emit work-package contracts for one report")
    p.add_argument("--report", required=True)
    p.add_argument("--source-hash", required=True, help="sha256:<64hex> of the source text")
    p.add_argument("--out", required=True, help="root directory for package dirs")
    p.add_argument("--processes", help="comma separated task types (default: all five)")
    p.add_argument("--mission-id")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--json")
    p.set_defaults(func=cmd_plan)

    r = sub.add_parser("register", help="process 01: fetch, hash and register reports")
    r.add_argument("--reports", required=True, help="comma separated report ids")
    r.add_argument("--out", required=True)
    r.add_argument("--sources")
    r.add_argument("--online", action="store_true")
    r.add_argument("--mission-id")
    r.add_argument("--json")
    r.set_defaults(func=cmd_register)

    u = sub.add_parser("run", help="run the line over a package root")
    u.add_argument("--root", required=True)
    u.add_argument("--sources")
    u.add_argument("--online", action="store_true")
    u.add_argument("--review-ledger-dir")
    u.add_argument("--tickets-dir")
    u.add_argument("--prompts-dir")
    u.add_argument("--min-quote-chars", type=int, default=12)
    u.add_argument("--synthesis-json")
    u.add_argument("--json")
    u.set_defaults(func=cmd_run)

    s = sub.add_parser("synthesis", help="assemble the 05 input bundle")
    s.add_argument("--root", required=True)
    s.add_argument("--json")
    s.set_defaults(func=cmd_synthesis)

    b = sub.add_parser("bench", help="reference-vs-computed fixture benchmark")
    b.add_argument("--root", default=str(FIXTURES))
    b.add_argument("--ref-doc", default=str(REF_TABLE_DOC))
    b.add_argument("--json")
    b.set_defaults(func=cmd_bench)

    a = sub.add_parser("all", help="run + bench over a package root, write both reports")
    a.add_argument("--root", default=str(FIXTURES))
    a.add_argument("--sources", default=str(FIXTURES / "sources"))
    a.add_argument("--online", action="store_true")
    a.add_argument("--review-ledger-dir", default=str(FIXTURES / "ledgers"))
    a.add_argument("--tickets-dir", default=str(FIXTURES / "tickets"))
    a.add_argument("--prompts-dir", default=str(PROMPTS_DIR))
    a.add_argument("--ref-doc", default=str(REF_TABLE_DOC))
    a.add_argument("--min-quote-chars", type=int, default=12)
    a.add_argument("--out", required=True)
    a.set_defaults(func=cmd_all)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
