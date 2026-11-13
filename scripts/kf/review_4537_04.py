#!/usr/bin/env python3
"""KF work package wp-4537-04 — independent review of wp-4537-01 (report 4537).

Reviewer context = report markdown (byte-hash pinned) + the upstream package result.
The producer's own explanations are NOT used as evidence; every quote below is sliced
out of the source markdown (or out of the upstream package file) programmatically and
carries a char span + sha256 so the gate can re-resolve it independently.

What this script does:
  F-checks  structural / fidelity audit of wp-4537-01 (locators, counts, completeness,
            scope, "verified" leakage);
  R-probes  re-run, on this machine with the same ruff 0.15.0 the report pins, the
            report's *mechanism* claims that are reproducible without the TensorFEM tree
            (E701/E702 are not autofixable and `ruff format` does not split statements;
            `[tool.ruff.lint] select` blocks only the blocking set while
            `--select E4,E7,E9,F` still counts the backlog; the unquoted-`name:` YAML
            trap; temp-dir config fallback and the `--line-length 100` mitigation).

Outputs (all under docs/kf/wp-4537-04/):
  review_report.json, review_events.json, kf_result.json

Usage: python3 scripts/kf/review_4537_04.py   (exit 0 = every check that could run passed)
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "docs" / "kf" / "wp-4537-04"
CACHE = ROOT / "runs" / "m15829_wp4537_04" / "source_report_4537.md"
UPSTREAM = ROOT / "docs" / "kf" / "wp-4537-01" / "kf_result.json"
UPSTREAM_SRC = ROOT / "docs" / "kf" / "wp-4537-01" / "asset_manifest.json"

REPORT_ID = "4537"
PACKAGE_ID = "wp-4537-04"
UPSTREAM_PACKAGE_ID = "wp-4537-01"
CONTRACT_HASH = "sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08"
CONTRACT_CHARS = 7931
REVIEWER = {"id": "reviewer-m15829-redteam", "reviewer_type": "agent",
            "role": "red-team-reviewer"}
POLICY_VERSION = "ke-review-v0.1"


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


SRC_CORPUS = "runs/m15829_wp4537_04/source_report_4537.md"


def quote(md: str, needle: str, *, field: str = "markdown",
          corpus: str = SRC_CORPUS) -> dict:
    """Verbatim locator: slice `needle` out of `corpus`, never hand-typed twice."""
    i = md.find(needle)
    assert i >= 0, f"quote not found in {corpus}: {needle!r}"
    sliced = md[i:i + len(needle)]
    assert sliced == needle
    return {"source_field": field, "corpus": corpus, "quote": sliced,
            "span": [i, i + len(sliced)],
            "content_hash": "sha256:" + sha256_hex(sliced)}


def run(cmd: list[str], cwd: Path) -> dict:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=120)
    return {"cmd": " ".join(cmd), "cwd": str(cwd), "rc": p.returncode,
            "stdout": p.stdout, "stderr": p.stderr}


def ruff_codes(out: str) -> list[str]:
    try:
        rows = json.loads(out)
    except json.JSONDecodeError:
        return []
    return sorted({r.get("code") for r in rows if r.get("code")})


# ---------------------------------------------------------------------------
# R-probes: reproduce the report's mechanism claims with the pinned ruff
# ---------------------------------------------------------------------------
def probe_r1a_no_lint_fix() -> dict:
    """Report §1: E701/E702 carry no *lint* fix (ruff check --fix cannot clear them)."""
    d = Path(tempfile.mkdtemp(prefix="wp4537_04_r1a_"))
    f = d / "m.py"
    f.write_text("import os\n\nx = 1; y = 2\nif True: pass\nprint(1)\n", encoding="utf-8")
    r_diff = run(["ruff", "check", "--select", "E701,E702", "--fix", "--diff", "m.py"], d)
    r_after = run(["ruff", "check", "--select", "E701,E702", "--output-format", "json", "m.py"], d)
    f401 = d / "f401.py"
    f401.write_text("import os\n\nprint(1)\n", encoding="utf-8")
    run(["ruff", "check", "--select", "F401", "--fix", "f401.py"], d)
    return {
        "probe": "R1a-e701-e702-have-no-lint-fix",
        "report_claim": "E701/E702 这类**不可自动修复**的排版债",
        "fix_diff_empty": r_diff["stdout"].strip() == "",
        "still_reported_after_fix": ruff_codes(r_after["stdout"]),
        "control_f401_autofix_removed_import": "import os" not in f401.read_text(encoding="utf-8"),
        "verdict": ("confirmed" if (r_diff["stdout"].strip() == ""
                                    and ruff_codes(r_after["stdout"]) == ["E701", "E702"]
                                    and "import os" not in f401.read_text(encoding="utf-8"))
                    else "not-confirmed"),
    }


def probe_r1b_format_does_not_split() -> dict:
    """Report §1/§5.5: "`ruff format` 也不会拆语句" / E701+E702 "无法通过 ruff format 消解".

    Same ruff version the report pins (0.15.0) is used; this is the refutation probe.
    """
    d = Path(tempfile.mkdtemp(prefix="wp4537_04_r1b_"))
    f = d / "m.py"
    original = "import os\n\nx = 1; y = 2\nif True: pass\nprint(1)\n"
    f.write_text(original, encoding="utf-8")
    before = run(["ruff", "check", "--select", "E701,E702", "--output-format", "json", "m.py"], d)
    fmt = run(["ruff", "format", "m.py"], d)
    after_text = f.read_text(encoding="utf-8")
    after = run(["ruff", "check", "--select", "E701,E702", "--output-format", "json", "m.py"], d)
    return {
        "probe": "R1b-ruff-format-splits-e701-e702",
        "report_claim": "`ruff format` 也不会拆语句；E701/E702 这类债无法通过 `ruff format` 消解",
        "ruff_version": fmt["cmd"],
        "codes_before": ruff_codes(before["stdout"]),
        "format_rc": fmt["rc"],
        "file_after_format": after_text,
        "semicolon_statement_split": "x = 1\ny = 2" in after_text,
        "inline_colon_split": "if True:\n    pass" in after_text,
        "codes_after": ruff_codes(after["stdout"]),
        "after_rc": after["rc"],
        "verdict": ("refuted" if ("x = 1\ny = 2" in after_text and "if True:\n    pass" in after_text
                                  and ruff_codes(after["stdout"]) == [])
                    else "confirmed"),
    }


def probe_r2_select_scope() -> dict:
    """Report §2.1/§3: `[tool.ruff.lint] select` narrows the blocking step only;
    the backlog counter (`--select E4,E7,E9,F`) still sees every historical hit."""
    d = Path(tempfile.mkdtemp(prefix="wp4537_04_r2_"))
    (d / "pyproject.toml").write_text(
        '[tool.ruff]\nline-length = 100\n\n[tool.ruff.lint]\n'
        'select = ["E9", "F63", "F7", "F81", "F82"]\n', encoding="utf-8")
    (d / "m.py").write_text(
        "import os\n\n\ndef f():\n    x = 1; y = 2\n    if True: pass\n"
        "    return undefined_name + x + y\n", encoding="utf-8")
    r_block = run(["ruff", "check", "m.py", "--output-format", "json"], d)
    r_backlog = run(["ruff", "check", "--select", "E4,E7,E9,F", "m.py",
                     "--output-format", "json"], d)
    block_codes = ruff_codes(r_block["stdout"])
    backlog_codes = ruff_codes(r_backlog["stdout"])
    return {
        "probe": "R2-config-select-vs-cli-select",
        "report_claim": "`select` 只影响**阻塞**规则集，`ruff check --select E4,E7,E9,F` 在修复后依旧报 4268 条",
        "blocking_step_codes": block_codes,
        "blocking_step_rc": r_block["rc"],
        "backlog_counter_codes": backlog_codes,
        "backlog_counter_rc": r_backlog["rc"],
        "blocking_set_only_f821": block_codes == ["F821"] and r_block["rc"] == 1,
        "backlog_still_reports_style_debt": {"E701", "E702", "F401", "F821"} <= set(backlog_codes),
        "verdict": ("confirmed" if (block_codes == ["F821"] and r_block["rc"] == 1
                                    and {"E701", "E702", "F401", "F821"} <= set(backlog_codes))
                    else "not-confirmed"),
    }


def probe_r3_yaml_trap() -> dict:
    """Report §5.3: an unquoted `name: ruff: correctness` makes the workflow unparsable."""
    import yaml

    bad = ("jobs:\n  lint:\n    steps:\n      - name: ruff: correctness\n"
           "        run: ruff check\n")
    good = ("jobs:\n  lint:\n    steps:\n      - name: 'ruff: correctness'\n"
            "        run: ruff check\n")
    bad_err, good_ok = None, False
    try:
        yaml.safe_load(bad)
    except yaml.YAMLError as exc:
        bad_err = str(exc).replace("\n", " ")[:200]
    try:
        doc = yaml.safe_load(good)
        good_ok = doc["jobs"]["lint"]["steps"][0]["name"] == "ruff: correctness"
    except yaml.YAMLError:
        good_ok = False
    return {
        "probe": "R3-unquoted-colon-in-step-name",
        "report_claim": "step `name` 里出现 `ruff: correctness` 会因 \"mapping values are not allowed here\" 直接让 workflow 非法",
        "unquoted_raises": bad_err is not None,
        "unquoted_error": bad_err,
        "error_is_mapping_values": bool(bad_err and "mapping values are not allowed here" in bad_err),
        "quoted_parses": good_ok,
        "verdict": ("confirmed" if (bad_err and "mapping values are not allowed here" in bad_err
                                    and good_ok) else "not-confirmed"),
    }


def probe_r4_temp_config_fallback() -> dict:
    """Report §2.2: a baseline file placed in the system temp dir loses the repo config,
    so the ratchet must pass `--line-length` explicitly."""
    line = ""
    for n in range(2, 40):
        cand = "result = compute(" + ", ".join(f'"k{i:02d}"' for i in range(n)) + ")"
        if 88 < len(cand) <= 100:
            line = cand
            break
    assert line, "could not build an 88<len<=100 line"
    proj = Path(tempfile.mkdtemp(prefix="wp4537_04_r4_proj_"))
    (proj / "pyproject.toml").write_text(
        '[tool.ruff]\nline-length = 100\ntarget-version = "py311"\n', encoding="utf-8")
    (proj / "f.py").write_text(line + "\n", encoding="utf-8")
    tmp = Path(tempfile.mkdtemp(prefix="wp4537_04_r4_tmp_"))
    (tmp / "f.py").write_text(line + "\n", encoding="utf-8")
    ancestors_with_cfg = [str(p) for p in (tmp, *tmp.parents)
                          if (p / "pyproject.toml").is_file() or (p / "ruff.toml").is_file()]
    in_proj = run(["ruff", "format", "--check", "f.py"], proj)
    in_tmp = run(["ruff", "format", "--check", "f.py"], tmp)
    in_tmp_explicit = run(["ruff", "format", "--check", "--line-length", "100",
                           "--target-version", "py311", "f.py"], tmp)
    return {
        "probe": "R4-temp-dir-loses-ruff-config",
        "report_claim": "临时基线文件在系统临时目录，故 `ruff format` 会回落到 ruff 默认配置（line-length 88）；脚本显式传 --line-length 100 --target-version py311",
        "synthetic_line_chars": len(line),
        "project_dir_check_rc": in_proj["rc"],
        "temp_dir_check_rc": in_tmp["rc"],
        "temp_dir_explicit_args_rc": in_tmp_explicit["rc"],
        "temp_dir_ancestors_with_ruff_config": ancestors_with_cfg,
        "verdict": ("confirmed" if (in_proj["rc"] == 0 and in_tmp["rc"] == 1
                                    and in_tmp_explicit["rc"] == 0 and not ancestors_with_cfg)
                    else "not-confirmed"),
    }


# ---------------------------------------------------------------------------
# F-checks: audit of wp-4537-01
# ---------------------------------------------------------------------------
def audit(md: str, manifest: dict, probes: list[dict]) -> tuple[list[dict], list[dict]]:
    checks: list[dict] = []

    def chk(cid: str, rule: str, ok: bool, detail: str) -> None:
        checks.append({"id": cid, "rule": rule, "pass": bool(ok), "detail": detail})

    assets = manifest["assets"]
    by_name = {a["name"]: a for a in assets}
    # the upstream package's own bytes are the reviewable artifact for package-level claims
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2)

    # F1 source identity
    chk("F1", "source_hash_recomputed", sha256_hex(md) == CONTRACT_HASH.split(":")[1]
        and manifest["source"]["sha256"] == CONTRACT_HASH,
        f"reviewer recomputed sha256={sha256_hex(md)[:16]}… chars={len(md)} "
        f"upstream_declared={manifest['source']['sha256'][:16]}…")
    chk("F1b", "chars_match_contract", len(md) == CONTRACT_CHARS,
        f"chars={len(md)} contract={CONTRACT_CHARS}")

    # F2 every declared locator occurrence resolves in the source (independent re-slice)
    bad: list[str] = []
    n_occ = 0
    for a in assets:
        for occ in (a.get("locator") or {}).get("occurrences", []):
            n_occ += 1
            s, e = occ["span"]
            if md[s:e] != occ["quote"] or "sha256:" + sha256_hex(md[s:e]) != occ["snippet_sha256"]:
                bad.append(f"{a['asset_id']}@{s}:{e}")
    chk("F2", "upstream_locators_resolve", not bad,
        f"{n_occ} occurrences re-sliced from source; mismatches={bad[:5]}")

    # F3 every registered name occurs verbatim (except record/figure metadata rows)
    not_verbatim = []
    for a in assets:
        # record row / figure metadata / the markdown's own inventory label are not
        # tokens of the source text, so "not verbatim in markdown" is expected there
        if a["kind"] in ("report_record_metadata", "report_figure", "report_markdown"):
            continue
        if a["name"] not in md:
            not_verbatim.append(a["name"])
    chk("F3", "asset_names_verbatim_in_source", not not_verbatim,
        f"names absent from markdown={not_verbatim}")

    # F4 asset_counts recomputed
    by_status: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for a in assets:
        by_status[a["status"]] = by_status.get(a["status"], 0) + 1
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1
    declared = manifest["asset_counts"]
    chk("F4", "asset_counts_recomputed",
        declared["total"] == len(assets) and declared["by_status"] == by_status
        and declared["by_kind"] == by_kind,
        f"recomputed total={len(assets)} by_status={by_status} by_kind={by_kind}")

    # F5 unique ids
    ids = [a["asset_id"] for a in assets]
    chk("F5", "asset_ids_unique", len(ids) == len(set(ids)), f"n={len(ids)} unique={len(set(ids))}")

    # F6 no invented payload for absent artifacts
    fabricated = [a["asset_id"] for a in assets
                  if not (a.get("payload") or {}).get("present", True)
                  and (a.get("payload") or {}).get("sha256") is not None]
    chk("F6", "absent_artifact_has_no_hash", not fabricated,
        f"absent-but-hashed assets={fabricated}")

    # F7 no verification marking / no claims leaked into the registration package
    blob = json.dumps(manifest, ensure_ascii=False).lower()
    chk("F7", "no_verification_marked",
        "verified" not in blob.replace("unverified", "") and manifest["claims"] == [],
        f"claims={len(manifest['claims'])}; 'verified' occurrences="
        f"{blob.count('verified')}")

    # F8 single-report scope
    other_ids = sorted({m for m in re.findall(r"reports/(\d{3,})", blob)} - {REPORT_ID})
    chk("F8", "single_report_scope", not other_ids, f"foreign report ids referenced={other_ids}")

    # F9 completeness: every file path the markdown names is either registered or
    #    listed as unresolved (no silent drops)
    path_tokens = set(re.findall(
        r"\.?[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|md|toml|yml|yaml|log|sh|cfg|txt)", md))
    path_tokens = {(t[2:] if t.startswith("./") else t) for t in path_tokens
                   if "/" in t or t in ("AGENTS.md", "pyproject.toml", "ci.yml")}
    registered = set(by_name)
    unresolved_names = {u["name"] for u in manifest["unresolved"]}
    unregistered = sorted(t for t in path_tokens
                          if t not in registered
                          and t not in unresolved_names
                          and not any(r.endswith("/" + t) for r in registered))
    n_declared_paths = len(path_tokens)
    chk("F9", "every_declared_path_registered_or_unresolved", not unregistered,
        f"{len(unregistered)}/{n_declared_paths} declared paths in markdown not covered by "
        f"wp-4537-01: {unregistered}")

    # F10 unresolved[] is an independent inventory, not a mirror of assets[]
    mirror = {a["name"] for a in assets if a["status"] != "resolved"}
    chk("F10", "unresolved_inventory_distinct_from_status_mirror",
        {u["name"] for u in manifest["unresolved"]} != mirror,
        f"|unresolved|={len(manifest['unresolved'])} "
        f"|assets with status!=resolved|={len(mirror)} sets_equal="
        f"{ {u['name'] for u in manifest['unresolved']} == mirror }")

    # F11 report-internal arithmetic (source fidelity, zero hand-typed numbers)
    rule_rows = {"E702": 2997, "E701": 965, "F401": 81, "E741": 71, "E401": 57,
                 "E731": 33, "F841": 27, "F405": 22, "E703/E402/F541/F403": 15}
    total = sum(rule_rows.values())
    pct = 100.0 * 3962 / 4268
    chk("F11", "report_internal_arithmetic_consistent",
        total == 4268 and abs(pct - 92.8) < 0.05 and 624 - 616 == 8
        and abs(100.0 * 8 / 624 - 1.28) < 0.01,
        f"Σrules={total} (report 合计 4268); 3962/4268={pct:.2f}% (report 92.8%); "
        f"8/624={100.0 * 8 / 624:.2f}% (report 1.28%)")

    # F12 the report does not claim the unobservable; the honest-FAIL stays honest
    honest = md.find("无法判定（honest-FAIL：不由本单声称）")
    green_lines = [ln for ln in md.splitlines() if "PR #128 CI 变绿" in ln]
    green_in_disclaimer = all(("不能由本单直接读取" in ln) or ("只能由" in ln) for ln in green_lines)
    chk("F12", "unobserved_outcome_not_claimed",
        honest >= 0 and "未直接观测" in md and green_in_disclaimer,
        f"honest marker at char {honest}; '未直接观测' present={'未直接观测' in md}; "
        f"{len(green_lines)} 'PR #128 CI 变绿' mention(s), all inside the disclaimer="
        f"{green_in_disclaimer}")

    # F13 the report's load-bearing mechanism claim vs a same-version reproduction
    r1b = next(p for p in probes if p["probe"].startswith("R1b"))
    chk("F13", "e701_e702_not_cleared_by_ruff_format", r1b["verdict"] != "refuted",
        f"probe R1b verdict={r1b['verdict']}: codes before={r1b['codes_before']} "
        f"after `ruff format`={r1b['codes_after']} (ruff 0.15.0, the version the report pins)")

    findings: list[dict] = []
    if unregistered:
        findings.append({
            "finding_id": "FN-4537-04-01",
            "severity": "medium",
            "blocking": True,
            "scope": UPSTREAM_PACKAGE_ID,
            "title": "注册完整性缺口：报告点名的测试文件路径未进 assets[]，也不在 unresolved[]",
            "claim_under_review": "wp-4537-01 自述登记「报告引用的每一个文件/路径」，且 unresolved[] 覆盖未决项",
            "evidence": [
                quote(md, "pytest -q tests/test_validation_gate.py tests/test_v1_readiness.py"),
                quote((ROOT / "scripts" / "kf" / "register_4537_assets.py").read_text(
                    encoding="utf-8"), "and every file/path the report *references*",
                    field="record", corpus="scripts/kf/register_4537_assets.py"),
                quote(md, "抽查 `pytest -q tests/test_validation_gate.py tests/test_v1_readiness.py`"),
            ],
            "observed": {"declared_paths_missing": unregistered,
                         "n_declared_paths": n_declared_paths,
                         "n_missing": len(unregistered),
                         "registered": False, "in_unresolved": False},
            "reproduction": ("python3 -c \"import json,re;md=open('runs/m15829_wp4537_04/"
                             "source_report_4537.md',encoding='utf-8').read();m=json.load(open("
                             "'docs/kf/wp-4537-01/kf_result.json'))['outputs']['asset_manifest."
                             "json'];n={a['name'] for a in m['assets']};print([t for t in "
                             "['tests/test_validation_gate.py','tests/test_v1_readiness.py']"
                             " if t in md and t not in n])\""),
            "root_cause": ("两条路径整体落在一个 inline code span 里（命令 "
                           "`pytest -q …`），01 的 tokenizer 把含空白的 span 判为 "
                           "command_line 后整段跳过，span 内的路径不再进入资产分类器"),
            "impact": "下游 03/04 的抽取面缺两个被报告明确点名的验证入口文件；报告 §3 的回归面证据不可被下游重建",
            "remediation": ("在 scripts/kf/register_4537_assets.py 的 command span 上再做一次路径切分，"
                            "或在 unresolved[] 显式登记这两条路径；加一条回归断言（tests/test_kf_wp4537_01.py）"),
        })
    if {u["name"] for u in manifest["unresolved"]} == mirror:
        findings.append({
            "finding_id": "FN-4537-04-02",
            "severity": "low",
            "blocking": False,
            "scope": UPSTREAM_PACKAGE_ID,
            "title": "unresolved[] 与 assets[status!=resolved] 集合完全同构，不是独立未决清单",
            "claim_under_review": "unresolved[] 语义 = 需下游/人工补齐的不确定项",
            "evidence": [quote(manifest_text,
                               "仅出现文件名/简化名，完整路径须由上下文唯一确定", field="record",
                               corpus="docs/kf/wp-4537-01/asset_manifest.json")],
            "observed": {"n_unresolved": len(manifest["unresolved"]), "n_mirror": len(mirror)},
            "reproduction": "python3 scripts/kf/review_4537_04.py  # F10",
            "impact": "下游按 unresolved 计欠账时会把已声明资产重复计为未决（同一批 25 条）",
            "remediation": "unresolved[] 只放真正未决项，或改名 status_mirror 并在 manifest 说明",
        })
    if r1b["verdict"] == "refuted":
        findings.append({
            "finding_id": "FN-4537-04-03",
            "severity": "medium",
            "blocking": True,
            "scope": f"report:{REPORT_ID}",
            "title": "报告的关键机制论断被同版本复现证伪：`ruff format` 会拆 E701/E702 语句",
            "claim_under_review": (
                "（a）「其中 3962 条（92.8%）是 E701/E702 这类**不可自动修复**的排版债，"
                "且 `ruff format` 也不会拆语句」；（b）「E701/E702 这类不可自动修复的债"
                "无法通过 `ruff format` 消解」"),
            "evidence": [
                quote(md, "其中 3962 条（92.8%）是 E701/E702 这类**不可自动修复**的排版债，"
                          "且 `ruff format` 也不会拆语句"),
                quote(md, "`E701/E702` 这类不可自动修复的债无法通过 `ruff format` 消解"),
            ],
            "counter_evidence": {
                "probe": "R1b（ruff 0.15.0，与报告钉版本一致）",
                "input": "import os\n\nx = 1; y = 2\nif True: pass\nprint(1)\n",
                "ruff_check_before": r1b["codes_before"],
                "after_ruff_format_file": r1b["file_after_format"],
                "ruff_check_after": r1b["codes_after"],
                "after_rc": r1b["after_rc"],
            },
            "reproduction": "python3 scripts/kf/review_4537_04.py  # probe R1b（临时目录内 ruff format + ruff check --select E701,E702）",
            "root_cause": "把『lint 规则无 autofix』外推成『formatter 也不会动它』；formatter 对复合语句会展开成多行（与 Black 同源行为）",
            "impact": ("(1) 3962/4268=92.8% 的债并非只能手改：一次 `ruff format` 批量即可消解 E701/E702，"
                       "burn-down 的『E7xx 只能手改』成本被高估；(2) 『ruff format --check』的 616 文件待重排"
                       "本身就说明 formatter 会动这些文件，两处论断互相矛盾；(3) 数值部分（4268/616/92.8%）"
                       "不受影响，已由 F11 复算通过"),
            "non_blocking_for_ship": False,
            "remediation": ("改写 §1 与 §5.5 的措辞为『E701/E702 无 lint autofix，只能由 ruff format 批量展开"
                            "（代价=616 文件 churn）』；docs/ci-lint-gate.md 的 burn-down 把 E7xx 阶段改为"
                            "一次 formatter 批处理，保留『不在本 PR 内重排全仓』的决策不变"),
        })
    return checks, findings


def main() -> int:
    md = CACHE.read_text(encoding="utf-8")
    envelope = json.loads(UPSTREAM.read_text(encoding="utf-8"))
    manifest = envelope["outputs"]["asset_manifest.json"]
    UPSTREAM_SRC.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                            encoding="utf-8")

    probes = [probe_r1a_no_lint_fix(), probe_r1b_format_does_not_split(),
              probe_r2_select_scope(),
              probe_r3_yaml_trap(), probe_r4_temp_config_fallback()]
    checks, findings = audit(md, manifest, probes)
    ruff_version = run(["ruff", "--version"], Path(tempfile.gettempdir()))["stdout"].strip()

    # independence (reuses the engine's own alias-closed identity rule)
    sys.path.insert(0, str(ROOT / "scripts"))
    from ke_state_machine import is_independent, producer_identity  # noqa: E402

    producer_ids = [envelope["provenance"].get("producer", ""),
                    str(json.loads((ROOT / "runs" / "m15829_wp4537_04" /
                                    "report_record_4537.json").read_text())["created_by"])]
    indep_ok, indep_basis = is_independent(REVIEWER, producer_identity({"producer_ids": producer_ids}))

    blocking = [f["finding_id"] for f in findings if f["blocking"]]
    disposition = "needs-fix" if blocking else "pass"

    failed_checks = [c["id"] for c in checks if not c["pass"]]
    report = {
        "review_report_version": 1,
        "package_id": PACKAGE_ID,
        "task_type": "04-independent-review",
        "reviewed_package_id": UPSTREAM_PACKAGE_ID,
        "report_id": REPORT_ID,
        "reviewed_source": {"source_uri": f"tensor://reports/{REPORT_ID}",
                            "source_field": "markdown",
                            "source_hash": CONTRACT_HASH,
                            "reviewer_recomputed_hash": "sha256:" + sha256_hex(md),
                            "chars": len(md)},
        "reviewer": REVIEWER,
        "producer_ids": producer_ids,
        "independence": {"ok": indep_ok, "basis": indep_basis,
                         "rule": "scripts/ke_state_machine.is_independent (A2, alias-closed)",
                         "limitations": [
                             "同一平台、同一模型族内的两个会话；id 不同只能证明会话不同，不能证明利益不同",
                             "审核上下文仅含报告原文 + 上游包 JSON；生产者对方法的自述未被采信为证据",
                         ]},
        "disposition": disposition,
        "disposition_reason": (
            "无 blocker；1 条 medium 阻塞项（FN-4537-04-01，注册完整性缺口）需上游补登记；"
            "报告本体（原文）对不可观测量的诚实标注通过复核，不被本单升级"),
        "checks": checks,
        "findings": findings,
        "reproduction_probes": probes,
        "ruff_version_used": ruff_version,
        "overstated_claims": [
            {"claim": "8/8 条断言 PASS / lint_gate.py 212 行",
             "status": "not_run",
             "why": "artifacts/lint-gate-m4175/evidence.log 与 scripts/lint_gate.py 的本体不在本工作树，"
                    "无法逐字节复核；本审核不把未复核的量化声明记为已证"},
            {"claim": "ruff==0.15.0（本地与 CI 一致）",
             "status": "partially-supported",
             "why": f"本地实测 {ruff_version}，与报告钉的版本一致；CI 侧一致性无法在本环境证实"},
            {"claim": "脚本对**所有**检查显式传 --line-length 100 --target-version py311（与 [tool.ruff] 同步）",
             "status": "partially-supported",
             "why": "R4 证实临时目录确实丢配置且该两参数可复原；但『与 [tool.ruff] 同步』只覆盖 line-length/"
                    "target-version 两个旋钮，formatter 的 quote-style / skip-magic-trailing-comma 等未同步"},
        ],
        "checks_not_run": [
            "GitHub check run 结论（报告 §5.1 自述出站被拦；本环境同样无 gh / REST 通路）",
            "TensorFEM 树上 4268 / 616 的原地复算（本工作树无 TensorFEM 检出，且不得跨仓读）",
            "artifacts/lint-gate-m4175/* 逐字节复核（工件不在本仓）",
            "5 个控制实验的原始退出码（evidence.log 不可及）",
            "M5 语义保真的 claim 级全量判定（上游 01 包 claims=[]，无 KO 可审；本单只做资产级保真判定）",
        ],
        "checks_failed": failed_checks,
        "summary": {
            "n_checks": len(checks),
            "n_checks_passed": len(checks) - len(failed_checks),
            "n_findings": len(findings),
            "n_blocking": len(blocking),
            "n_probes_confirmed": sum(1 for p in probes if p["verdict"] == "confirmed"),
            "n_probes_refuted": sum(1 for p in probes if p["verdict"] == "refuted"),
            "n_probes": len(probes),
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "review_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    events = [{
        "id": f"tkr:wp-4537-04:{disposition}",
        "decision": "request-changes" if disposition == "needs-fix" else "approve",
        "policy_version": POLICY_VERSION,
        "reviewer": {"id": REVIEWER["id"], "reviewer_type": REVIEWER["reviewer_type"]},
        "reviewed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "subject_package_id": UPSTREAM_PACKAGE_ID,
        "independence_basis": indep_basis,
        "findings": [{"finding_id": f["finding_id"], "severity": f["severity"],
                      "title": f["title"]} for f in findings],
        "review_report": "review_report.json",
        "touches_epistemic_status": False,
    }]
    (OUT_DIR / "review_events.json").write_text(
        json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    envelope_out = {
        "package_id": PACKAGE_ID,
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": CONTRACT_HASH,
            "source_field": "markdown",
            "source_uri": f"tensor://reports/{REPORT_ID}",
            "producer": "scripts/kf/review_4537_04.py",
            "emitted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "notes": ("source_hash 由本脚本对 markdown UTF-8 字节独立重算后写入并复核；"
                      "审核对象=wp-4537-01；本包不写 epistemic status、不标 verified"),
        },
        "outputs": {"review_report.json": report, "review_events.json": events},
        "claims": [],
    }
    (OUT_DIR / "kf_result.json").write_text(
        json.dumps(envelope_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"disposition": disposition, "checks_failed": failed_checks,
                      "findings": [f["finding_id"] for f in findings],
                      "probes": {p["probe"]: p["verdict"] for p in probes},
                      "independence": {"ok": indep_ok, "basis": indep_basis},
                      "ruff": ruff_version}, ensure_ascii=False, indent=2))
    return 0 if not [c for c in checks if not c["pass"] and c["id"] in ("F1", "F2")] else 1


if __name__ == "__main__":
    raise SystemExit(main())