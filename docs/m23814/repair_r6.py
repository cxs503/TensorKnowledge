#!/usr/bin/env python3
"""R6-fix: repair the three R5 residuals of the PROD-RA review bundle (m23814).

Frozen criteria (m23157 R5 receipt + m23257 verify_status.py, unchanged):
  R5-1  every pure-path locator field in docs/m22059/**.json and
        docs/review_m22059_prod_ra/**.json must resolve on a cold extraction
        (tracked files only), or be an explicit platform-evidence pointer.
  R5-2  SHA256SUMS must be sound: every listed file present, every digest
        equal to the actual bytes. Regenerated here by computation, never
        hand-copied.
  R5-3  D6 evidence bundle: 5/5 items carry provenance.input_sha256, no
        absolute foreign input_refs, 5/5 source_ref resolve cold, item
        sha256 equals the actual source file digest, bundle self-digest
        matches under tensorbench.criteria.canonical_sha256.

Method: field-level (JSON-aware) rewrite of pure-path fields only; prose
quoting historical findings is left untouched. Every decision is logged to
docs/m23814/raw/repair_log.json. Nothing is written outside the repo tree.

Usage:
    python3 docs/m23814/repair_r6.py --repo .
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/root/tensor-ecosystem/TensorBench")
from tensorbench.criteria import canonical_sha256  # noqa: E402

REVIEW = "docs/review_m22059_prod_ra"
RUN = "docs/m22059"
# The 4 raw files filtered out of the m22508 merge by the size gate; the
# m22508 worktree still holds the original bytes.
RAW_RESTORE_SOURCE = Path("/root/tp-agent/work/m22508") / REVIEW / "raw"
# Declared digests from the committed SHA256SUMS (the contract the restore
# must satisfy byte-for-byte).
RAW_RESTORE_DECLARED = {
    "adjacent_unit_tests.log": "e6cee4f833d41e5a7cb3d9cced80013df921a465e8a2ccd9be02e458a2087c71",
    "evidence_schema_validation.log": "3f92deedd83eba530dd8a0ea5305d441a69bc226256fc8e1767ed3fa0de603d8",
    "pytest_collect_base.log": "5967a6b8955be506669b1df2731ddca2ed173756860a57f058402b97b45b9048",
    "pytest_collect_reviewed.log": "4c020fde24714cb137d0b00d3677344daca08f5aeae86c16c691399053ad2740",
}
# Manifest entry order preserved from the committed manifest.
MANIFEST_ORDER = [
    "raw/SHA256SUMS", "raw/adjacent_unit_tests.log", "raw/cea.err",
    "raw/cea_neg.json", "raw/cea_rerun.json", "raw/cit_neg.json",
    "raw/citation.err", "raw/citation_audit_rerun.json",
    "raw/cluster_job_cj4175_status.txt", "raw/evidence_schema_validation.log",
    "raw/pytest_collect_base.log", "raw/pytest_collect_reviewed.log",
    "recheck.py", "recheck_output.json", "REVIEW-RECEIPT.json",
    "review-report.md", "verdict_insert.sql",
    "figures/six-checks-and-triage.png",
]
ABS_WORKTREE = re.compile(r"^/root/tp-agent/work/([^/]+)(/.*)?$")
KB10K_DIGEST_CONVENTION = (
    "sha256 over UTF-8 'name:file_sha256\\n' lines sorted by name "
    "(m23814 R6 convention; the m22760 dir-digest convention is not "
    "reproducible from the repo, so it is not claimed here)"
)


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def is_pure_path(s: str) -> bool:
    core = s.split("#")[0]
    return bool(core) and not re.search(r"\s", core) and (
        core.startswith(("runs/", "docs/m22059/", "/root/tp-agent/")))


def dir_digest(d: Path) -> tuple[str, dict]:
    files = {p.name: sha256_file(p) for p in sorted(d.iterdir()) if p.is_file()}
    digest = hashlib.sha256(
        "".join(f"{n}:{v}\n" for n, v in sorted(files.items())).encode()
    ).hexdigest()
    return digest, files


def rewrite_pure_path(root: Path, s: str, log: list) -> str:
    """Rewrite one pure-path field value; return the new value (or original)."""
    core, _, frag = s.partition("#")
    m = ABS_WORKTREE.match(core)
    if m:
        mid, rest = m.group(1), (m.group(2) or "").lstrip("/")
        if not rest:
            new = f"platform-evidence://worktree/{mid}"
            log.append({"old": s, "new": new, "rule": "bare_worktree_root->platform_pointer"})
            return new
        if rest.startswith("runs/m22059/"):
            cand = "docs/m22059/" + rest[len("runs/m22059/"):]
        elif rest.startswith("docs/m22059/"):
            cand = rest
        else:
            cand = rest
        if (root / cand).exists():
            log.append({"old": s, "new": cand + (f"#{frag}" if frag else ""),
                        "rule": "absolute->in_repo"})
            return cand + (f"#{frag}" if frag else "")
        log.append({"old": s, "new": f"platform-evidence://worktree/{mid}",
                    "rule": "absolute_unresolvable->platform_pointer"})
        return f"platform-evidence://worktree/{mid}"
    if core.startswith("runs/m22059/"):
        cand = "docs/m22059/" + core[len("runs/m22059/"):]
        if (root / cand).exists():
            log.append({"old": s, "new": cand + (f"#{frag}" if frag else ""),
                        "rule": "legacy_runs_prefix->in_repo"})
            return cand + (f"#{frag}" if frag else "")
        log.append({"old": s, "new": s, "rule": "legacy_unresolvable_kept"})
        return s
    return s  # already in-repo (docs/m22059/...)


def rewrite_file(root: Path, f: Path, log: list) -> int:
    obj = json.loads(f.read_text(encoding="utf-8"))
    changed = 0

    def fix(o):
        nonlocal changed
        if isinstance(o, dict):
            for k, v in list(o.items()):
                if isinstance(v, str) and is_pure_path(v):
                    nv = rewrite_pure_path(root, v, log)
                    if nv != v:
                        o[k] = nv
                        changed += 1
                else:
                    fix(v)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                if isinstance(v, str) and is_pure_path(v):
                    nv = rewrite_pure_path(root, v, log)
                    if nv != v:
                        o[i] = nv
                        changed += 1
                else:
                    fix(v)

    fix(obj)
    if changed:
        f.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    return changed


def update_sha_fragments(root: Path, files: list[Path], log: list) -> int:
    """Pass 2: refresh '#sha256:<old>' fragments whose path part resolves."""
    n = 0
    for f in files:
        obj = json.loads(f.read_text(encoding="utf-8"))
        touched = False

        def fix(o):
            nonlocal touched, n
            if isinstance(o, dict):
                for k, v in list(o.items()):
                    if isinstance(v, str) and "#sha256:" in v:
                        core, _, frag = v.partition("#")
                        p = root / core
                        if p.is_file() and frag.startswith("sha256:"):
                            actual = sha256_file(p)
                            if frag != f"sha256:{actual}":
                                o[k] = f"{core}#sha256:{actual}"
                                touched = True
                                n += 1
                                log.append({"file": str(f), "field": k,
                                            "old": v, "new": o[k],
                                            "rule": "sha_fragment_refreshed"})
                    else:
                        fix(v)
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    if isinstance(v, str) and "#sha256:" in v:
                        core, _, frag = v.partition("#")
                        p = root / core
                        if p.is_file() and frag.startswith("sha256:"):
                            actual = sha256_file(p)
                            if frag != f"sha256:{actual}":
                                o[i] = f"{core}#sha256:{actual}"
                                touched = True
                                n += 1
                                log.append({"file": str(f), "field": f"[{i}]",
                                            "old": v, "new": o[i],
                                            "rule": "sha_fragment_refreshed"})
                    else:
                        fix(v)

        fix(obj)
        if touched:
            f.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--log-out", default="docs/m23814/raw/repair_log.json")
    a = ap.parse_args()
    root = Path(a.repo).resolve()
    log: list[dict] = []
    total_fields = 0

    # ---- R5-2a: restore the 4 missing raw files byte-for-byte -------------
    raw = root / REVIEW / "raw"
    for name, declared in RAW_RESTORE_DECLARED.items():
        src = RAW_RESTORE_SOURCE / name
        dst = raw / name
        if not src.is_file():
            log.append({"step": "raw_restore", "file": name,
                        "status": "SOURCE_ABSENT"})
            continue
        got = sha256_file(src)
        if got != declared:
            log.append({"step": "raw_restore", "file": name,
                        "status": "HASH_MISMATCH", "declared": declared,
                        "actual": got})
            continue
        shutil.copyfile(src, dst)
        log.append({"step": "raw_restore", "file": name, "status": "restored",
                     "sha256": got, "source": str(src)})

    # ---- R5-2b: the raw/SHA256SUMS mirror is declared empty (e3b0c442...) --
    (raw / "SHA256SUMS").write_bytes(b"")
    log.append({"step": "raw_mirror_truncated", "file": "raw/SHA256SUMS",
                 "declared_digest": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"})

    # ---- R5-1: field-level locator rewrite ---------------------------------
    files = sorted(p for p in (root / RUN).rglob("*.json"))
    files += sorted(p for p in (root / REVIEW).rglob("*.json"))
    for f in files:
        total_fields += rewrite_file(root, f, log)

    # ---- R5-3: D6 evidence bundle recomputation -----------------------------
    vr_path = root / RUN / "validation-report.json"
    report = json.loads(vr_path.read_text(encoding="utf-8"))
    bundle = report["evidence_bundle"]
    for it in bundle["evidence_items"]:
        src = root / str(it["source_ref"]).split("#")[0]
        it["sha256"] = sha256_file(src)
        if it["evidence_id"] == "ev-kb10k-incompatibility":
            cd, cfiles = dir_digest(root / "knowledge/kb10k/claims")
            ed, efiles = dir_digest(root / "knowledge/kb10k/evidence")
            it["provenance"]["input_sha256"] = {
                "claims_dir_digest": cd,
                "evidence_dir_digest": ed,
                "claims_files": cfiles,
                "evidence_files": efiles,
                "digest_convention": KB10K_DIGEST_CONVENTION,
            }
    bundle["items_sha256"] = [it["sha256"] for it in bundle["evidence_items"]]
    canon = {k: v for k, v in bundle.items() if k != "integrity"}
    bundle["integrity"]["bundle_sha256"] = canonical_sha256(canon)
    vr_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    log.append({"step": "d6_bundle_recomputed",
                 "items_sha256": bundle["items_sha256"],
                 "bundle_sha256": bundle["integrity"]["bundle_sha256"]})

    # ---- pass 2: refresh #sha256: fragments (after all content is final) ---
    frag_files = [f for f in files if b"#sha256:" in f.read_bytes()]
    nfrag = update_sha_fragments(root, frag_files, log)

    # ---- R5-2c: regenerate SHA256SUMS from actual bytes ---------------------
    lines = []
    for rel in MANIFEST_ORDER:
        p = root / REVIEW / rel
        if not p.is_file():
            log.append({"step": "manifest", "file": rel, "status": "MISSING"})
            continue
        lines.append(f"{sha256_file(p)}  {rel}")
    (root / REVIEW / "SHA256SUMS").write_text("\n".join(lines) + "\n",
                                               encoding="utf-8")
    log.append({"step": "manifest_regenerated", "entries": len(lines)})

    out = root / a.log_out
    out.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if out.is_file():
        try:
            history = json.loads(out.read_text(encoding="utf-8"))
        except Exception:
            history = []
    history.append({"run": len(history) + 1,
                    "head": subprocess.run(["git", "rev-parse", "HEAD"],
                                           cwd=root, capture_output=True,
                                           text=True).stdout.strip(),
                    "entries": log})
    out.write_text(json.dumps(history, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"locator_fields_changed={total_fields} sha_fragments_refreshed={nfrag} "
          f"manifest_entries={len(lines)}")
    print(f"bundle_sha256={bundle['integrity']['bundle_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
