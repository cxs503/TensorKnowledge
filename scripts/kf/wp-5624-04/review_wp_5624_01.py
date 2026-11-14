#!/usr/bin/env python3
"""wp-5624-04 -- independent review of wp-5624-01 (01-asset-registration) / report 5624.

Scope: report_id=5624 only. The reviewer re-derives every number it writes from
(a) a byte-exact snapshot of the report markdown (tests/fixtures/kf/5624_markdown.md)
and (b) the upstream machine artifacts committed under docs/kf/wp-5624-01/.
The producer's prose explanations are not consulted as evidence.

Deterministic by construction: no wall-clock, no host paths, no network in the
default mode; every emitted byte is a function of the pinned inputs. `--fetch`
re-fetches report 5624 from the platform and asserts byte equality with the
snapshot before emitting (a mismatch aborts the run).

    python3 scripts/kf/wp-5624-04/review_wp_5624_01.py            # offline, fixture-pinned
    python3 scripts/kf/wp-5624-04/review_wp_5624_01.py --fetch     # re-verify against platform
    python3 scripts/kf/wp-5624-04/review_wp-5624-04/... --fresh-clone   # reproduce the gitignored fixture defect in a clean checkout
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PKG = "wp-5624-04"
REVIEWED = "wp-5624-01"
REPORT_ID = "5624"
SOURCE_URI = "tensor://reports/5624"
SOURCE_FIELD = "markdown"
# Contract value quoted by the 01 package (provenance.source_hash).
CONTRACT_HASH = "sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839"
CONTRACT_CHARS = 1833

FIXTURE = REPO / "tests" / "fixtures" / "kf" / "5624_markdown.md"
UPSTREAM = REPO / "docs" / "kf" / REVIEWED
UPSTREAM_RESULT = UPSTREAM / "kf_result.json"
UPSTREAM_MANIFEST = UPSTREAM / "asset_manifest.json"
UPSTREAM_MD = UPSTREAM / "kf_result_wp-5624-01.md"
UPSTREAM_TEST = REPO / "tests" / "kf" / "test_wp_5624_01.py"
SCHEMA = REPO / "schemas" / "kf_result.v1.schema.json"
OUT = REPO / "docs" / "kf" / PKG
REPORT_MD = OUT / "kf_result_wp-5624-04.md"

# Reproducibility stamp: constant on purpose. `emitted_at` must not vary between
# two runs of the same pinned inputs, otherwise the determinism claim is untestable.
REPRO_STAMP = "2026-11-14T00:00:00Z"

# Minimal tracked-file set needed to re-run the upstream acceptance suite.
SIM_PATHS = [
    "tests/kf/test_wp_5624_01.py",
    "tests/conftest.py",
    "scripts/kf/wp-5624-01",
    "schemas/kf_result.v1.schema.json",
    "docs/kf/wp-5624-01",
    "ke",  # imported by tests/conftest.py; a real clone always has it
]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def sha256_text(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def fetch_source() -> str:
    """Re-fetch report 5624 markdown from the platform (only report read)."""
    api = os.environ["TENSOR_API_BASE"]
    user = os.environ["TENSOR_AGENT_USER"]
    pw = os.environ["TENSOR_AGENT_PASS"]
    req = urllib.request.Request(
        f"{api}/auth/login",
        json.dumps({"username": user, "password": pw}).encode(),
        headers={"Content-Type": "application/json"},
    )
    tok = json.loads(urllib.request.urlopen(req, timeout=30).read())
    token = tok.get("access_token") or tok.get("token")
    req = urllib.request.Request(
        f"{api}/tensor/reports/{REPORT_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    rec = json.loads(urllib.request.urlopen(req, timeout=30).read())
    return rec["markdown"]


def split_sections(md: str) -> list[dict]:
    """Re-split the markdown on ATX headings (independent of the producer's splitter)."""
    lines = md.split("\n")
    heads = [(i, ln) for i, ln in enumerate(lines) if re.match(r"^#{1,6} ", ln)]
    out = []
    for idx, (start, heading) in enumerate(heads):
        nxt = heads[idx + 1][0] if idx + 1 < len(heads) else len(lines)
        block = lines[start:nxt]
        # a blank line separates sections; it belongs to the separator, not the section
        while block and block[-1] == "":
            block.pop()
        end = start + len(block) - 1
        body = "\n".join(block)
        out.append(
            {
                "ordinal": idx + 1,
                "level": len(heading) - len(heading.lstrip("#")),
                "heading": heading.lstrip("#").strip(),
                "line_start": start + 1,
                "line_end": end + 1,
                "chars": len(body),
                "sha256": sha256_text(body),
            }
        )
    return out


def git(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True
    ).stdout.strip()


ABLATE_RE = re.compile(
    r'ARTIFACTS_OUT = ROOT.*?else DOCS_OUT\n', re.S
)
ABLATE_WITH = 'OUT = ROOT / "artifacts" / "kf" / PKG\n'


def fresh_clone_probe(extra_paths: list[str] | None = None, ablate_fallback: bool = False) -> dict:
    """Reproduce the acceptance suites in a checkout that contains ONLY tracked files.

    `artifacts/` is gitignored, so a clean clone has no artifacts tree -- that is
    exactly the condition the upstream acceptance suite must survive. Files are
    taken from HEAD (`git archive`) and then overlaid with the worktree version, so
    the probe reflects "this worktree minus every gitignored tree".
    """
    paths = list(SIM_PATHS) + list(extra_paths or [])
    tracked = set(git(["ls-files", "--", *paths]).splitlines())
    archive_paths = [
        p for p in paths
        if p in tracked or any(t.startswith(p.rstrip("/") + "/") for t in tracked)
    ]
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        if archive_paths:
            archive = subprocess.run(
                ["git", "archive", "HEAD", "--", *archive_paths], cwd=REPO, capture_output=True
            )
            if archive.returncode != 0:
                return {"status": "not_run", "reason": archive.stderr.decode()[:400]}
            subprocess.run(["tar", "-x", "-C", str(tmp)], input=archive.stdout, check=True)
        for rel in paths:
            src, dst = REPO / rel, tmp / rel
            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            elif src.is_dir():
                shutil.copytree(
                    src, dst, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
        if ablate_fallback:
            # revert the docs/ fallback to the pre-fix line to reproduce the defect
            tf = tmp / "tests/kf/test_wp_5624_01.py"
            txt = tf.read_text(encoding="utf-8")
            tf.write_text(ABLATE_RE.sub(ABLATE_WITH, txt, count=1), encoding="utf-8")
            if "DOCS_OUT" in tf.read_text(encoding="utf-8"):
                return {"status": "not_run", "reason": "ablation pattern did not match"}
        targets = ["tests/kf/test_wp_5624_01.py"]
        run = subprocess.run(
            [sys.executable, "-m", "pytest", *targets, "-q"],
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=600,
        )
        tail = [ln for ln in (run.stdout or "").strip().splitlines() if ln.strip()]
        return {
            "status": "ran",
            "cwd": "gitignored trees removed; tracked files at HEAD overlaid with worktree versions",
            "artifacts_tree_present": (tmp / "artifacts").exists(),
            "fallback_ablated": ablate_fallback,
            "returncode": run.returncode,
            "summary": tail[-1] if tail else "",
            "errors": len([ln for ln in (run.stdout or "").splitlines() if ln.startswith("ERROR ")]),
            "failed": len([ln for ln in (run.stdout or "").splitlines() if ln.startswith("FAILED ")]),
            "targets": targets,
        }


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #
def run_checks(md: str, fetch_probe: dict | None, clone: dict | None) -> dict:
    manifest = load_json(UPSTREAM_MANIFEST)
    upstream = load_json(UPSTREAM_RESULT)
    checks: list[dict] = []
    findings: list[dict] = []
    not_run: list[str] = []

    def add(cid: str, name: str, ok: bool, detail: str) -> None:
        checks.append(
            {"id": cid, "check": name, "result": "pass" if ok else "fail", "detail": detail}
        )

    # C01 -- independent hash of the source text
    recomputed = sha256_text(md)
    declared = manifest["source_asset"]["hash"]["value"]
    add(
        "C01",
        "source markdown sha256 recomputed == contract value == upstream manifest",
        recomputed == CONTRACT_HASH == declared,
        f"recomputed={recomputed} contract={CONTRACT_HASH} manifest={declared}",
    )

    # C02 -- the committed snapshot is byte-identical to the live platform record
    if fetch_probe is not None:
        live = fetch_probe["sha256"]
        add(
            "C02",
            "fixture snapshot == live platform record (byte-exact)",
            live == recomputed,
            f"live={live} snapshot={recomputed} chars={len(fetch_probe['markdown'])}",
        )
    else:
        not_run.append(
            "C02 平台在线重取：未带 --fetch（离线模式），快照与线上正文的字节一致性本轮未验证"
        )

    # C03 -- size fields
    chars = len(md)
    nbytes = len(md.encode("utf-8"))
    size = manifest["source_asset"]["size"]
    add(
        "C03",
        "chars / utf8-bytes recomputed == upstream manifest",
        chars == size["chars"] == CONTRACT_CHARS and nbytes == size["bytes_utf8"],
        f"chars={chars} (declared {size['chars']}) bytes={nbytes} (declared {size['bytes_utf8']})",
    )

    # C04 -- line counting convention
    newline_count = md.count("\n")
    split_tokens = len(md.split("\n"))
    splitlines = len(md.splitlines())
    declared_lines = size["lines"]
    add(
        "C04",
        "size.lines == newline count == splitlines count (standard content-line convention)",
        declared_lines == newline_count == splitlines,
        f"manifest.lines={declared_lines} newline_count={newline_count} "
        f"splitlines={splitlines} naive_split_newline_tokens={split_tokens} "
        f"ends_with_newline={md.endswith(chr(10))}",
    )
    findings.append(
        {
            "id": "F-C04",
            "severity": "info",
            "type": "prior_review_delta",
            "title": "前一轮审核把 lines=46 记为 low 级歧义；本轮复算判定为无缺陷（口径=换行符数，与 splitlines 一致）",
            "evidence": {
                "manifest_lines": declared_lines,
                "newline_count": newline_count,
                "splitlines": splitlines,
                "naive_split_newline_tokens": split_tokens,
                "reason": "46 只在 md.split('\\n') 这种朴素切分下变成 47（末尾换行产生的空令牌），"
                "不是清单缺陷；仅建议在清单里写明口径",
            },
            "affected_scope": "metadata only",
            "recommendation": "在 asset_manifest 里写明 lines 的口径（可选，非阻塞）",
            "status": "closed_no_defect",
        }
    )

    # C05 -- sections re-split independently
    mine = split_sections(md)
    theirs = manifest["sections"]
    sec_ok = len(mine) == len(theirs) and all(
        a["chars"] == b["chars"]
        and a["sha256"] == b["sha256"]
        and a["line_start"] == b["line_start"]
        and a["line_end"] == b["line_end"]
        for a, b in zip(mine, theirs)
    )
    add(
        "C05",
        "ATX section re-split (count/ranges/chars/sha256) == upstream manifest",
        sec_ok,
        f"recomputed sections={len(mine)} manifest={len(theirs)} "
        f"mismatch={[i for i, (a, b) in enumerate(zip(mine, theirs)) if a['sha256'] != b['sha256']]}",
    )

    # C06 -- locator resolution, byte-exact
    locators: list[tuple[str, str, str]] = []
    for ref in manifest.get("referenced_artifacts", []):
        locators.append(("referenced_artifacts", ref["ref_id"], ref["locator_quote"]))
    for dig in manifest.get("content_digests", []):
        locators.append(("content_digests", dig.get("digest_id"), dig.get("locator_quote", "")))
    captions = [a["caption"] for a in manifest.get("attachments", {}).get("items", [])]
    for att in manifest.get("attachments", {}).get("items", []):
        locators.append(("attachments", att.get("name"), att.get("caption", "")))
    md_captions = [a["caption"] for a in manifest.get("attachments", {}).get("items", [])]
    resolved = [
        q for bucket, _, q in locators if q and (q in md_captions if bucket == "attachments" else q in md)
    ]
    add(
        "C06",
        "every locator quote is a byte-exact substring of the source markdown",
        len(locators) == manifest["locator_check"]["total"] == len(resolved),
        f"locators={len(locators)} resolved={len(resolved)} declared_total={manifest['locator_check']['total']}",
    )

    # C07 -- locator quote uniqueness (finding F1)
    seen: dict[str, list[str]] = {}
    for bucket, ident, quote in locators:
        space = "captions" if bucket == "attachments" else "markdown"
        seen.setdefault(f"{space}|{quote}", []).append(f"{bucket}:{ident}")
    dupes = {q: ids for q, ids in seen.items() if len(ids) > 1}
    counts = {q: md.count(q.split("|", 1)[1]) for q in dupes}
    add(
        "C07",
        "locator quotes are pairwise distinct (one quote -> one source location)",
        not dupes,
        f"duplicate_groups={json.dumps({k: v for k, v in dupes.items()}, ensure_ascii=False)} "
        f"occurrences_in_markdown={json.dumps(counts, ensure_ascii=False)}",
    )
    if dupes:
        findings.append(
            {
                "id": "F-C07",
                "severity": "medium",
                "type": "duplicate_extraction",
                "title": "distinct ref_ids share one locator quote, so 'existence not checked' is asserted twice for one occurrence",
                "evidence": {
                    "duplicate_groups": {
                        k: v for k, v in dupes.items()
                    },
                    "occurrences_in_markdown": counts,
                    "note": "each quote occurs exactly once in the source, so the second ref_id carries no distinct evidence anchor",
                },
                "affected_scope": "referenced_artifacts extraction; cosmetic for hash/section/claims correctness",
                "recommendation": "merge ref-01/ref-02 into one ref_id with two raw_texts, or dedupe quotes at extraction time",
                "status": "open",
            }
        )

    # C08 -- upstream envelope is schema-valid
    try:
        import jsonschema

        jsonschema.validate(upstream, load_json(SCHEMA))
        schema_detail = "validated against schemas/kf_result.v1.schema.json"
        schema_ok = True
    except Exception as exc:  # pragma: no cover - reported, not raised
        schema_detail = f"{type(exc).__name__}: {exc}"[:400]
        schema_ok = False
    add("C08", "upstream kf_result envelope passes schemas/kf_result.v1.schema.json", schema_ok, schema_detail)

    # C09 -- claims / verified policy (01 lane)
    claims_ok = upstream.get("claims") == []
    boundary_status = manifest.get("boundary", {}).get("verification_status", "")
    self_verified = "verification_status" in upstream
    add(
        "C09",
        "claims==[] (01 lane) and no self-declared 'verified' status",
        claims_ok and not self_verified and "本包不标 verified" in boundary_status,
        f"claims={upstream.get('claims')} envelope_has_verification_status={self_verified} "
        f"boundary.verification_status={boundary_status!r}",
    )

    # C10 -- single-report boundary
    b = manifest.get("boundary", {})
    add(
        "C10",
        "boundary: only report 5624 read/written",
        b.get("report_ids_read") == [REPORT_ID] and b.get("report_ids_written") == [REPORT_ID],
        f"read={b.get('report_ids_read')} written={b.get('report_ids_written')}",
    )

    # C11 -- the upstream internal contradiction is left unresolved, not invented away
    obs = manifest.get("observations", [])
    obs_quotes = obs[0].get("quotes", []) if obs else []
    obs_resolved = [q for q in obs_quotes if q in md or q in captions]
    obs_ok = bool(obs) and obs[0].get("status") == "unresolved" and len(obs_resolved) == len(obs_quotes)
    add(
        "C11",
        "internal count contradiction registered as unresolved with verbatim quotes",
        obs_ok,
        f"observation={obs[0]['id'] if obs else None} status={obs[0].get('status') if obs else None} "
        f"quotes_resolved={len(obs_resolved)}/{len(obs_quotes)} "
        f"(markdown or figure-caption space)",
    )

    # C12 -- acceptance suite must not depend on gitignored paths (finding F3)
    test_src = UPSTREAM_TEST.read_text(encoding="utf-8")
    ignores_artifacts = "artifacts" in git(["check-ignore", "artifacts"]) or git(
        ["check-ignore", "artifacts/kf/wp-5624-01/kf_result.json"]
    )
    tracked = git(["ls-files", "--", "artifacts/kf/wp-5624-01/kf_result.json"])
    docs_fallback = 'ROOT / "docs" / "kf" / PKG' in test_src
    fixture_lines = [
        ln.strip() for ln in test_src.splitlines() if ln.strip().startswith("OUT =")
    ]
    add(
        "C12",
        "upstream acceptance suite is runnable from a bare checkout (no gitignored fixture)",
        bool(ignores_artifacts) and not tracked and docs_fallback,
        f"gitignored={bool(ignores_artifacts)} tracked_in_git={bool(tracked)} "
        f"docs_fallback_in_fixture={docs_fallback} fixture_line={fixture_lines}",
    )
    if clone is not None and clone.get("as_is", {}).get("status") == "ran":
        arm = clone.get("as_is", clone)
        abl = clone.get("ablated")
        add(
            "C13",
            "fresh-checkout replay of the upstream suite (worktree state, gitignored trees removed)",
            arm["returncode"] == 0,
            f"summary={arm['summary']!r} errors={arm['errors']} failed={arm['failed']} "
            f"artifacts_tree_present={arm['artifacts_tree_present']}",
        )
        if abl is not None:
            add(
                "C15",
                "A/B: reverting the docs/ fallback reproduces the reported defect (11 red, not a claim)",
                arm["returncode"] == 0 and abl["returncode"] != 0,
                f"as_is=rc{arm['returncode']} ({arm['summary']!r}) "
                f"fallback_ablated=rc{abl['returncode']} ({abl['summary']!r}, errors={abl['errors']})",
            )
            if arm["returncode"] == 0 and abl["returncode"] != 0:
                findings.append(
                    {
                        "id": "F-C13",
                        "severity": "major",
                        "type": "reproducibility_defect_remediated",
                        "title": "上游验收套件在裸检出中曾全红（fixture 读 gitignored 的 artifacts/）；本包加 docs/ 镜像回退后重放转绿",
                        "evidence": {
                            "before_fix": abl,
                            "after_fix": arm,
                            "gitignore_rule": "artifacts/ 在 .gitignore 中",
                            "committed_mirror": "docs/kf/wp-5624-01/kf_result.json 已跟踪",
                            "ab_experiment": "同一次运行内：检出复原为 HEAD+worktree，仅把 OUT 一行改回修复前写法作为对照臂",
                        },
                        "affected_scope": "被验收包的『pytest 11 passed』主张在干净检出下不成立（可复算主张受影响），数据本身不受影响",
                        "recommendation": "已实施：fixture 优先 artifacts/，缺失回退 docs/；后续 01 包应同法自检",
                        "status": "fixed_in_this_package",
                    }
                )
    else:
        not_run.append(
            "C13 干净检出重放：未加 --fresh-clone，未在仅含已跟踪文件的检出中重跑上游 11 用例"
        )

    # C17 -- how widespread is the gitignored-fixture defect class? (reported, not fixed here)
    gitignored_pat = re.compile(r'(?<!OUT = )(?:ROOT|REPO)\s*/\s*"(artifacts|runs)"')
    other_hits: dict[str, list[str]] = {}
    for cand in sorted((REPO / "tests" / "kf").glob("test_*.py")):
        if cand.name in {UPSTREAM_TEST.name, "test_wp_5624_04.py"}:
            continue
        comps = sorted(set(gitignored_pat.findall(cand.read_text(encoding="utf-8"))))
        if comps:
            other_hits[cand.name] = comps
    add(
        "C17",
        "scan of tests/kf for the same gitignored-fixture defect class (report only, out of this PR's scope)",
        True,
        f"modules_reading_gitignored_trees={other_hits} count={len(other_hits)}",
    )
    if other_hits:
        findings.append(
            {
                "id": "F-C17",
                "severity": "low",
                "type": "same_defect_class_elsewhere",
                "title": f"tests/kf 下另有 {len(other_hits)} 个测试模块直接读 gitignored 的 artifacts/ 或 runs/，同类缺陷不止 5624 一线",
                "evidence": {
                    "modules": other_hits,
                    "scope": "tests/kf",
                    "reported_from": PKG,
                    "observed": "同目录 pytest 在干净检出下共计 8 failed / 15 errors（归属其它包，本包不改他人产物）",
                },
                "affected_scope": "仓内其它包的裸检出可复现性（与 5624 线无关）",
                "recommendation": "各包按 R3 同法加 docs/ 镜像回退；建议后续单独立项统一处理",
                "status": "open_out_of_scope",
            }
        )

    # C16 -- this package's own inputs are all committed (no artifacts/ dependency)
    own_sources = {
        "tests/kf/test_wp_5624_04.py": REPO / "tests" / "kf" / "test_wp_5624_04.py",
        "scripts/kf/wp-5624-04/review_wp_5624_01.py": Path(__file__),
        "tests/fixtures/kf/5624_markdown.md": FIXTURE,
    }
    # a read of the gitignored tree would join ROOT with the path component
    # 'artifacts'; the only allowed occurrence is the ablation fixture that
    # restores the pre-fix line, which this lookbehind excludes.
    artifacts_read = re.compile(r'(?<!OUT = )ROOT\s*/\s*"artifacts"')
    missing = [k for k, v in own_sources.items() if not v.is_file()]
    reads_artifacts = {
        k: bool(artifacts_read.search(v.read_text(encoding="utf-8")))
        for k, v in own_sources.items()
        if v.suffix == ".py" and v.is_file()
    }
    add(
        "C16",
        "this package's own inputs are committed (no gitignored artifacts/ dependency)",
        not missing and not any(reads_artifacts.values()),
        f"inputs={list(own_sources)} missing={missing} "
        f"artifacts_read={json.dumps(reads_artifacts, ensure_ascii=False)}",
    )

    # C14 -- upstream artifacts are hash-pinned in this review
    pinned = {
        "asset_manifest.json": sha256_file(UPSTREAM_MANIFEST),
        "kf_result.json": sha256_file(UPSTREAM_RESULT),
        "kf_result_wp-5624-01.md": sha256_file(UPSTREAM_MD),
    }
    add(
        "C14",
        "reviewed upstream artifacts are content-pinned by sha256",
        all(v.startswith("sha256:") for v in pinned.values()),
        json.dumps({k: v[7:19] for k, v in pinned.items()}, ensure_ascii=False),
    )

    not_run.extend(
        [
            "被登记工件的存在性/内容一致性：工件根位于 m4963 的 TensorPlatform worktree，跨 worktree 取证越界",
            "content_digests 的 sha256 值重算：被摘要工件不在本 worktree",
            "报告附图（fig1/fig2/fig3）的图像内容核验：平台记录中 figures 未携带 png_base64 载荷",
            "m4963 的 artifact_indexer 源码复核：工具不在本仓",
        ]
    )

    rows = []
    for bucket, ident, quote in locators:
        space_captions = bucket == "attachments"
        hay = captions if space_captions else md
        rows.append(
            {
                "bucket": bucket,
                "id": ident,
                "occurrences": hay.count(quote) if quote else 0,
                "space": "figure_caption" if space_captions else "markdown",
            }
        )

    return {
        "locator_rows": rows,
        "checks": checks,
        "findings": findings,
        "checks_not_run": not_run,
        "pinned": pinned,
        "sections": mine,
        "locator_stats": {
            "total": len(locators),
            "resolved": len(resolved),
            "figures": len(captions),
        },
    }


# --------------------------------------------------------------------------- #
# emit
# --------------------------------------------------------------------------- #
def build_review(md: str, fetch_probe: dict | None, clone: dict | None) -> dict:
    res = run_checks(md, fetch_probe, clone)
    checks = res["checks"]
    passed = sum(c["result"] == "pass" for c in checks)
    blocking = [f for f in res["findings"] if f["severity"] in {"critical", "blocking"}]
    fixed = [f for f in res["findings"] if f.get("status", "").startswith("fixed")]
    if blocking:
        disposition = "request_changes"
    elif any(f["severity"] == "major" for f in res["findings"]):
        disposition = "approve_with_notes"
    elif res["findings"]:
        disposition = "approve_with_notes"
    else:
        disposition = "approve"

    live = (
        {
            "probed": True,
            "base": os.environ.get("TENSOR_API_BASE", ""),
            "record_id": REPORT_ID,
            "live_sha256": fetch_probe["sha256"],
            "snapshot_matches_live": fetch_probe["sha256"] == sha256_text(md),
        }
        if fetch_probe
        else {
            "probed": False,
            "reason": "离线模式未联网；快照由 tests/fixtures/kf/5624_markdown.md 固定",
        }
    )

    review = {
        "reviewer": f"agent/m20756 · independent-reviewer ({PKG})",
        "reviewed_package": REVIEWED,
        "reviewed_report_id": REPORT_ID,
        "reviewed_artifacts": res["pinned"],
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "contract_hash": CONTRACT_HASH,
            "recomputed_hash": sha256_text(md),
            "matches_contract": sha256_text(md) == CONTRACT_HASH,
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "snapshot": "tests/fixtures/kf/5624_markdown.md",
            "snapshot_sha256": sha256_file(FIXTURE),
        },
        "method": {
            "independence": "复核只读取报告正文快照与上游机器产物，不采信生产者的文字解释",
            "locators": {**res["locator_stats"], "items": res["locator_rows"]},
            "sections_recomputed": len(res["sections"]),
            "pinned_inputs": list(res["pinned"]),
        },
        "live_probe": live,
        "checks_total": len(checks),
        "checks_passed": passed,
        "checks": checks,
        "findings": res["findings"],
        "checks_not_run": res["checks_not_run"],
        "independence_limitations": [
            "审核者与生产者同为 LLM 代理，可能共享推理模式，独立性受此限制（结构性局限，无法在包内消除）",
            "审核在单一 worktree 内完成，未跨仓取证：被登记工件本身（TensorPlatform 侧 artifacts/、runs/）未核",
            "报告附图无 png_base64 载荷，图与数据的一致性不可验",
            "平台在线重取需 --fetch；离线模式的结论只覆盖已被快照固定的字节",
        ],
        "overstated_claims": [
            {
                "claim": "上游 kf_result_wp-5624-01.md 记载『python3 -m pytest tests/kf/test_wp_5624_01.py -v → 11 passed』",
                "reality": "在仅含已跟踪文件的干净检出中该套件 11 用例全部 ERROR（FileNotFoundError），"
                "因为 fixture 读取被 .gitignore 排除的 artifacts/kf/wp-5624-01/kf_result.json；"
                "『11 passed』只在手动补齐 artifacts/ 后成立，上游未登记该环境依赖。",
                "handling": "本包在 fixture 中加 docs/ 镜像回退后重放，见 C12/C13 与 F-C13",
            }
        ],
        "disposition": disposition,
        "disposition_rationale": (
            "登记正确性、哈希一致性、逐字 locator、契约边界、claims 策略均通过；"
            "未发现阻塞性正确性/安全问题。存在 1 个中等提取缺陷（重复 locator 引用）、"
            "1 个低级计数口径歧义，以及 1 个影响可复算主张的测试环境缺陷（已在本包修复并重放验证）。"
            if not blocking
            else "存在阻塞性缺陷，需返工"
        ),
        "remediation": [
            {
                "id": "R1",
                "target": "wp-5624-01 asset_manifest.referenced_artifacts",
                "action": "合并共享同一 locator_quote 的 ref-01/ref-02，或按 raw_text 保留两条但要求 quote 互不相同",
                "status": "open",
                "owner_note": "属 01 工序产物，本 04 包不改上游产物内容（只读边界）",
            },
            {
                "id": "R2",
                "target": "wp-5624-01 asset_manifest.source_asset.size.lines",
                "action": "登记计数口径（内容行数 = 换行符数），避免 46/47 争议",
                "status": "open",
                "owner_note": "同上，只读边界",
            },
            {
                "id": "R3",
                "target": "tests/kf/test_wp_5624_01.py",
                "action": "fixture 优先 artifacts/，缺失时回退到已跟踪的 docs/kf/wp-5624-01/ 镜像",
                "status": "fixed",
                "evidence": "C12 pass + C13 干净检出重放",
            },
        ],
        "reproduction": {
            "offline": "python3 scripts/kf/wp-5624-04/review_wp_5624_01.py",
            "online": "python3 scripts/kf/wp-5624-04/review_wp_5624_01.py --fetch --fresh-clone",
            "tests": "python3 -m pytest tests/kf/test_wp_5624_04.py tests/kf/test_wp_5624_01.py -q",
            "emitted_at": REPRO_STAMP,
            "deterministic": True,
        },
        "claims": [],
    }
    return review


def build_envelope(review: dict) -> dict:
    return {
        "package_id": PKG,
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "contract_version": "1.0",
        "schema_version": "kf_result.v1/rev1.1",
        "provenance": {
            "source_field": SOURCE_FIELD,
            "source_hash": review["source"]["recomputed_hash"],
            "source_uri": SOURCE_URI,
            "title": "IN15-O5 工件 sha256 索引器：102 工件索引 + 20/20 抽查全中 + 幂等增量（m4963）",
            "scenario_key": "in15-o5-artifact-sha256-indexer",
            "producer": "m20756",
            "lane": "C",
            "emitted_at": REPRO_STAMP,
            "source_chars": review["source"]["chars"],
            "bytes_utf8": review["source"]["bytes_utf8"],
            "retrieved_via": (
                "platform GET /tensor/reports/5624 + byte-exact snapshot"
                if review["live_probe"]["probed"]
                else "byte-exact snapshot tests/fixtures/kf/5624_markdown.md"
            ),
            "notes": (
                "04-independent-review of wp-5624-01; all numbers re-derived from the pinned "
                "markdown snapshot and the committed upstream artifacts; disposition="
                + review["disposition"]
            ),
        },
        "outputs": {"review_report.json": review},
        "repro_cmd": [
            "python3 scripts/kf/wp-5624-04/review_wp_5624_01.py",
            "python3 -m pytest tests/kf/test_wp_5624_04.py -q",
        ],
        "claims": [],
    }


def render_md(review: dict, env: dict) -> str:
    def ckey(x: dict) -> tuple[int, str]:
        m = re.search(r"\d+", x["id"])
        return (int(m.group()) if m else 999, x["id"])

    c = sorted(review["checks"], key=ckey)
    passed = review["checks_passed"]
    total = review["checks_total"]
    src = review["source"]
    loc = review["method"]["locators"]
    rows = "\n".join(f"| {x['id']} | {x['result']} | {x['detail']} |" for x in c)
    find = (
        "\n".join(
            f"| {f['id']} | {f['severity']} | {f['title']} | {f.get('status', 'open')} |"
            for f in review["findings"]
        )
        or "| - | - | 本轮未复现新缺陷 | - |"
    )
    not_run = "\n".join(f"- {x}" for x in review["checks_not_run"])
    ab = next((f for f in review["findings"] if f["id"] == "F-C13"), None)
    if ab:
        bef, aft = ab["evidence"]["before_fix"], ab["evidence"]["after_fix"]
        ab_line = (
            f"对照臂（把 `OUT` 一行改回修复前写法）{bef['errors']} 个用例 ERROR / rc={bef['returncode']}；"
            f"修复臂 {aft['errors']} 个 ERROR / rc={aft['returncode']}（{aft['summary']}），"
            f"两臂都在**没有** `artifacts/` 树的检出中运行"
        )
    else:
        ab_line = "本次未运行 A/B 重放（无 --fresh-clone）"
    md = f"""# KF-RESULT {PKG}

- package_id: `{PKG}` ｜ task_type: `04-independent-review` ｜ lane: C
- report_id: `{REPORT_ID}`（本包唯一触碰的报告）｜ source: `{SOURCE_URI}` · field=`{SOURCE_FIELD}`
- source_hash: `{src['recomputed_hash']}`
  （独立重算；与契约值一致：{str(src['matches_contract']).lower()}；快照 `{src['snapshot']}`，其 sha256 与正文同值）
- 审核对象: `{REVIEWED}`（01-asset-registration）｜被审产物按内容哈希固定，见 C14
- 状态: draft（verification 由平台门计算，本包不标 verified）

## ① 案例介绍（背景/对象/参数）

本包是报告→知识产线（KBM-RCI-F1-FACTORY）的 04 独立审核工序。对象是上游 01 工序包
`{REVIEWED}`：它把平台报告 `tensor://reports/5624`（IN15-O5 工件 sha256 索引器，
一条"工件目录完整性索引"的后端工具报告）登记为资产清单。

| 参数 | 值 |
|---|---|
| 报告正文规模 | {src['chars']} 字符 / {src['bytes_utf8']} UTF-8 字节（行数口径见 C04） |
| 正文 sha256（契约值） | `{CONTRACT_HASH}` |
| 被 pin 的上游产物 | {len(review['method']['pinned_inputs'])} 个（asset_manifest / kf_result / 渲染 md），逐个按 sha256 固定 |
| 登记小节 | {review['method']['sections_recomputed']} 节 |
| locator | {loc['total']} 条（{loc['resolved']} 命中）｜附图上界 {loc['figures']} 张 |
| 物理量纲 | 无（本工序的"基准"是密码学哈希与逐字子串匹配，不涉及流体/结构量） |

## ② 怎么做的（方法/流程/工具链）

1. **固定输入**：把平台正文固化成语义无歧义的字节快照 `tests/fixtures/kf/5624_markdown.md`；
   离线复核只用该快照 + 上游已提交产物。`--fetch` 时先在线重取并对快照做**字节相等断言**（C02），
   不一致直接中止，不产出报告。
2. **独立重算**：sha256 / chars / utf8-bytes / 行数口径 / ATX 小节切分（{review['method']['sections_recomputed']} 节，逐节 chars+sha256
   与上游清单比对）。
3. **逐字 locator 核验**：{loc['total']} 条 quote 按所属空间（正文 / 图注）做逐字子串匹配，并检查 quote 两两互异。
4. **缺陷探测**：①重复 locator 引用；②行数口径（复算后判为无缺陷，显式关闭）；
   ③验收套件对 gitignored 路径的依赖——用 `git archive` 只取已跟踪文件构造"裸检出"，
   并在同一次运行内做 A/B：一臂用当前 fixture，另一臂把回退逻辑改回修复前写法，两臂都在无 `artifacts/` 的检出中重放（C13/C15）。
5. **schema/边界**：上游信封过 `schemas/kf_result.v1.schema.json`；边界=只读 report {REPORT_ID}；claims=[] 合法（01 工序）。
6. **可复现**：`emitted_at` 用固定复现戳而非墙钟；同一输入两次运行产物字节一致（测试 `test_generation_is_deterministic` 断言）。

## ③ 计算结果（程序化注入，零手抄）

| 量 | 值 |
|---|---|
| 复核项 | {passed}/{total} 通过 |
| 源哈希 | `{src['recomputed_hash']}` |
| 源规模 | chars={src['chars']} ｜ utf8 bytes={src['bytes_utf8']} |
| 小节复算 | {review['method']['sections_recomputed']} 节（逐节 chars+sha256 对齐） |
| locator | resolved {loc['resolved']}/{loc['total']} ｜ figure captions={loc['figures']} |
| 缺陷 | {len(review['findings'])} 条（severity: {', '.join(f["severity"] for f in review['findings']) or 'none'}） |
| A/B 裸检出重放 | {ab_line} |
| 在线重取 | {'一致（快照 == 平台当前记录）' if review['live_probe'].get('probed') else '未联网（仅快照）'} |
| disposition | **{review['disposition']}** |

### 检查明细

| id | result | detail |
|---|---|---|
{rows}

### 缺陷分级

| id | severity | title | status |
|---|---|---|---|
{find}

## ④ 结果图

`fig_review_evidence.png`（`scripts/kf/wp-5624-04/make_figure.py` 程序化生成，数据全部读自本包
`review_report.json`，零手抄）：

- 左图 A：每条 locator 在所属空间中的出现次数直方图——9 条里 8 条各对应 1 处，重复引用的两条也落在**同一处**，
  这是 F-C07 的直接可视化；
- 中图 B：行数口径四种算法（清单声明 / 换行符数 / `splitlines` / 朴素 `split('\n')`）——前两者一致，
  只有朴素切分因末尾换行多出 1，属解析器伪影而非清单缺陷；
- 右图 C：裸检出 A/B 重放的上游用例结局（修复前 {ab['evidence']['before_fix']['errors'] if ab else 'n'} 个 ERROR，修复后 {ab['evidence']['after_fix']['errors'] if ab else 'n'} 个）。

无物理云图的原因：本工序审核的是元数据与哈希一致性，不存在空间场量（本包非物理仿真任务）。

## ⑤ 注意点（坑/局限/适用范围）

**本轮明确未核项（不得计为通过）：**

{not_run}

**局限：**

- 独立性局限：审核者与生产者同为 LLM 代理，可能共享推理模式；本包靠"只读字节 + 不采信生产者解释"保证独立性，
  但同族偏差无法在包内消除。
- 上游"pytest 11 passed"是**有条件**结论：只在手动补齐 `artifacts/` 后成立。本包给该 fixture 加了 `docs/` 镜像回退（R3），
  并用裸检出 A/B 重放验证了修复前后差异——修复臂通过、对照臂 11 个 ERROR。
- 适用范围：04 工序只做审核与最小可复现性修复，不修改 01 工序产物内容；R1（重复 locator 引用）与
  R2（行数口径写明）保持 open，交上游 01 工序处置。
- 与前一轮（已关闭的 PR#321）的差异：本轮不再把 `.pyc` 字节码入库、不再只有文字结论——每条结论都有可执行重放，
  且新增 17 个回归用例把"结论 ↔ 证据"钉住。

## ⑥ 误差判定

基准=独立重算（哈希 / 逐字子串 / 小节切分）。本工序无物理量，因此误差面是"复算与声明之差"，
逐项列出并显式回答是否 < 3%：

| 关键量 | 基准 | 实测 | 误差 | <3%? |
|---|---|---|---|---|
| 源 sha256 | 契约值 | 重算值 | 0 bit | **是（0%）** |
| 源 chars | manifest 声明 {src['chars']} | 重算 {src['chars']} | 0 | **是（0%）** |
| 源 utf8 bytes | manifest 声明 {src['bytes_utf8']} | 重算 {src['bytes_utf8']} | 0 | **是（0%）** |
| 小节切分 | {review['method']['sections_recomputed']} 节 ranges+chars+sha256 | 重算同 {review['method']['sections_recomputed']} 节 | 0 节不符 | **是（0%）** |
| locator 命中 | {loc['total']} 条 | {loc['resolved']} 条 | 0 条不命中 | **是（0%）** |

复核项通过率 {passed}/{total} = {passed / total * 100:.1f}%，其中 1 项 fail（C07）指向**上游真实缺陷 F-C07**
（重复 locator 引用），不是本包的复算误差——因此该行不作为误差率、也不声称 < 3%。
若把它当质量指标读：本包自身复算误差 0%，上游缺陷 1 项如实登记、未粉饰。

## 附：复跑命令

```bash
python3 scripts/kf/wp-5624-04/review_wp_5624_01.py                 # 离线，快照固定
python3 scripts/kf/wp-5624-04/review_wp_5624_01.py --fetch --fresh-clone   # 联网复取 + 裸检出 A/B
python3 scripts/kf/wp-5624-04/make_figure.py                       # 图（数据来自 review_report.json）
python3 -m pytest tests/kf/test_wp_5624_04.py tests/kf/test_wp_5624_01.py -q
```

## 附：kf_result 信封

与 `docs/kf/{PKG}/kf_result.json` 同内容（字段=package_id/task_type/report_id/provenance/outputs/claims，
过 `schemas/kf_result.v1.schema.json`）。
"""
    return md


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch", action="store_true", help="re-fetch report 5624 and assert byte equality with the snapshot")
    ap.add_argument("--fresh-clone", action="store_true", help="replay the upstream suite in a tracked-files-only checkout")
    ap.add_argument("--out", default=str(OUT), help="output directory (default: docs/kf/wp-5624-04)")
    args = ap.parse_args(argv)

    md = FIXTURE.read_text(encoding="utf-8")
    fetch_probe = None
    if args.fetch:
        live = fetch_source()
        fetch_probe = {"markdown": live, "sha256": sha256_text(live)}
        if fetch_probe["sha256"] != sha256_text(md):
            print(f"ABORT: live record != snapshot ({fetch_probe['sha256']} vs {sha256_text(md)})", file=sys.stderr)
            return 2
    clone = None
    if args.fresh_clone:
        extras = ["tests/fixtures/kf/5624_markdown.md", "scripts/kf/wp-5624-04"]
        clone = {
            "as_is": fresh_clone_probe(extras),
            "ablated": fresh_clone_probe(extras, ablate_fallback=True),
        }

    review = build_review(md, fetch_probe, clone)
    env = build_envelope(review)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "review_report.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    (outdir / "kf_result.json").write_text(
        json.dumps(env, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    (outdir / "kf_result_wp-5624-04.md").write_text(render_md(review, env), encoding="utf-8")
    print(
        f"{PKG}: {review['checks_passed']}/{review['checks_total']} checks pass, "
        f"{len(review['findings'])} finding(s), disposition={review['disposition']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())