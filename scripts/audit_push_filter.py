#!/usr/bin/env python3
"""Audit which files the mission-push gate filtered out (m8800).

The push gate (``tp_pusher.py``) builds a commit from the mission branch's
change set and silently drops paths matching its exclusion rules; the *count*
lands in the commit message ("（N 个文件被门禁滤除）") but the file names are
nowhere.  This script reconstructs them:

1. read the merged mission commits of a repo and parse the filtered count;
2. for each mission with a local ``agent/m<N>`` branch, compute the branch's
   change set and subtract the paths that actually made it into the commit;
3. classify every leftover path with the *same* rules the pusher uses
   (``artifacts/``/``runs/``/``results-``+db/png/log, ``submit_report.py``,
   other-mission ``/m<N>/`` segments, ship vocabulary) and cross-check that the
   reconstructed number of dropped files equals the count in the commit message.

Usage::

    python scripts/audit_push_filter.py [--repo PATH] [--since 2026-10-27] [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

MARKER = re.compile(r"m(\d+):.*（(\d+) 个文件被门禁滤除）")

# --- the pusher's exclusion rules (kept in sync with tp_pusher.py v6.0) ------
R_RECORD = re.compile(r"^(artifacts?/|runs/|results[-/]|REPORT_GATE)")
R_BINARY = re.compile(r"\.(db|sqlite3?|png|log)$")
R_OTHER_MISSION = re.compile(r"(?:^|/)m(\d{2,})/")
R_SHIP = re.compile(
    r"(ship|holtrop|wigley|michell|kvlcc|suboff|seakeep|manoeuv|maneuver|propeller"
    r"|hydrostatic|[/_.-](?:polar|kcs|dtmb)(?:[/_.-]|$))", re.I)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True,
                          text=True, check=True).stdout


def classify(path: str, mid: str, repo_name: str) -> tuple[str, str]:
    """Return (gate_rule, why) for one path — mirrors tp_pusher.py's order."""
    if path == "submit_report.py":
        return "harness", "平台上报 harness 工具，非成果"
    if R_RECORD.search(path):
        return "record", "运行记录区（artifacts/runs/results/REPORT_GATE）"
    if R_BINARY.search(path) and not (path.startswith("docs/") and path.endswith((".png", ".svg"))):
        return "record", "二进制/运行产物（db|sqlite|png|log）"
    others = [m for m in R_OTHER_MISSION.findall(path) if m != mid]
    if others:
        return "other-mission", f"路径含他单号段 m{others[0]}/"
    if repo_name == "TensorPlatform" and R_SHIP.search(path):
        return "ship", "船舶语汇路径（TensorPlatform 边界门）"
    return "keep", "未被任何门禁规则命中"


def missions(repo: Path, since: str) -> list[dict]:
    out = []
    log = git(repo, "log", "--all", "--format=%H|%ad|%s", "--date=short")
    for line in log.splitlines():
        sha, date, subject = line.split("|", 2)
        m = MARKER.search(subject)
        if not m or date < since:
            continue
        out.append({"sha": sha, "date": date, "mid": m.group(1),
                    "filtered": int(m.group(2)), "subject": subject})
    return out


def changed_paths(repo: Path, rev: str) -> set[str]:
    """Paths touched by ``rev`` relative to its first parent."""
    try:
        out = git(repo, "diff", "--name-only", f"{rev}^", rev)
    except subprocess.CalledProcessError:
        out = git(repo, "show", "--name-only", "--format=", rev)
    return {p for p in out.splitlines() if p}


def branch_paths(repo: Path, branch: str, base: str) -> set[str]:
    try:
        mb = git(repo, "merge-base", base, branch).strip()
    except subprocess.CalledProcessError:
        return set()
    out = git(repo, "diff", "--name-only", mb, branch)
    return {p for p in out.splitlines() if p}


def referenced(repo: Path, sha: str, path: str) -> bool:
    """True if the mission's own commit mentions this file (or its directory)."""
    try:
        patch = git(repo, "show", "--format=", sha)
    except subprocess.CalledProcessError:
        return False
    parts = path.split("/")
    probes = [path]
    if len(parts) > 2:
        probes.append("/".join(parts[:3]))
        probes.append("/".join(parts[:-1]) + "/")
    return any(probe in patch for probe in probes)


def same_on_main(repo: Path, main_ref: str, path: str, branch: str) -> bool | None:
    """None if absent on main, else whether content is identical."""
    if not _path_on(repo, main_ref, path):
        return None
    rc = subprocess.run(["git", "diff", "--quiet", f"{main_ref}:{path}", f"{branch}:{path}"],
                        cwd=repo, capture_output=True).returncode
    return rc == 0


def _path_on(repo: Path, ref: str, path: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", f"{ref}:{path}"],
                          cwd=repo, capture_output=True).returncode == 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--since", default="2026-10-27", help="window start (YYYY-MM-DD)")
    ap.add_argument("--main-ref", default="origin/main", help="reference main tip for content compares")
    ap.add_argument("--json", default=None, help="write the audit data as JSON")
    ap.add_argument("--md", default=None, help="write a Markdown table")
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    repo_name = repo.name
    base = next((r for r in (args.main_ref, "main") if _has(repo, r)), "main")

    rows, summary = [], {"repo": repo_name, "since": args.since, "missions": [],
                         "reconstructed_exact": 0, "reconstructed_partial": 0,
                         "no_branch": 0}
    for m in missions(repo, args.since):
        mid = m["mid"]
        branch = f"agent/m{mid}"
        entry = {"mid": mid, "sha": m["sha"], "date": m["date"],
                 "filtered_logged": m["filtered"], "branch": branch}
        if not _has(repo, branch):
            entry.update({"reconstructed": None, "note": "分支不在本地，无法重建"})
            summary["no_branch"] += 1
            summary["missions"].append(entry)
            continue
        in_commit = changed_paths(repo, m["sha"])
        in_branch = branch_paths(repo, branch, base)
        dropped = sorted(in_branch - in_commit)
        files = []
        for p in dropped:
            rule, why = classify(p, mid, repo_name)
            if rule == "other-mission":
                needed = referenced(repo, m["sha"], p)
                verdict = "误滤" if needed else "该滤"
                why += ("；本单产物引用了该路径（缺了即红）" if needed
                        else "；本单未引用，属他单成果")
            elif rule == "keep":
                same = same_on_main(repo, args.main_ref, p, branch)
                if same is False:
                    verdict, why = "误滤", "main 已前进且内容不同：合并动作缺失（非覆盖保护本身之过）"
                elif same is True:
                    verdict, why = "该滤", "main 已前进且内容相同：无需覆盖"
                else:
                    verdict, why = "误滤", "main 上不存在该路径：静默丢失"
            else:
                verdict = "该滤"
            files.append({"path": p, "rule": rule, "verdict": verdict, "why": why})
        entry.update({"reconstructed": len(files), "files": files})
        if len(files) == m["filtered"]:
            entry["match"] = "exact"
            summary["reconstructed_exact"] += 1
        else:
            entry["match"] = "partial"
            summary["reconstructed_partial"] += 1
        summary["missions"].append(entry)
        rows.extend((mid, f) for f in files)

    by_rule: dict[str, int] = {}
    by_verdict: dict[str, int] = {}
    for _mid, f in rows:
        by_rule[f["rule"]] = by_rule.get(f["rule"], 0) + 1
        by_verdict[f["verdict"]] = by_verdict.get(f["verdict"], 0) + 1
    summary["files_total"] = len(rows)
    summary["files_by_rule"] = by_rule
    summary["files_by_verdict"] = by_verdict

    print(f"repo={repo_name} window>={args.since} missions={len(summary['missions'])} "
          f"files={len(rows)} by_rule={by_rule} "
          f"exact={summary['reconstructed_exact']} "
          f"partial={summary['reconstructed_partial']} "
          f"no_branch={summary['no_branch']}")
    for mid, f in rows:
        print(f"  m{mid}\t{f['rule']}\t{f['path']}")

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")
    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text(render_md(summary), encoding="utf-8")
    return 0


def _has(repo: Path, ref: str) -> bool:
    return subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref],
                          cwd=repo, capture_output=True).returncode == 0


def render_md(summary: dict) -> str:
    out = ["<!-- generated by scripts/audit_push_filter.py; do not edit by hand -->",
           f"# 附：逐条清单（{summary['repo']}，{summary['since']} 起）\n",
           "| mission | 提交 | 日志计数 | 重建数 | 一致 |",
           "|---|---|---:|---:|:--:|"]
    for e in summary["missions"]:
        out.append(f"| m{e['mid']} | `{e['sha'][:8]}` | {e['filtered_logged']} | "
                   f"{e.get('reconstructed')} | {e.get('match', e.get('note', ''))} |")
    out += ["", "| mission | 门禁规则 | 判定 | 文件 | 理由 / 找回路径 |", "|---|---|:--:|---|---|"]
    for e in summary["missions"]:
        for f in e.get("files", []):
            recall = "" if f["verdict"] == "该滤" else f"`git show agent/m{e['mid']}:{f['path']}`"
            out.append(f"| m{e['mid']} | {f['rule']} | {f['verdict']} | `{f['path']}` | {f['why']}"
                       + (f" → {recall}" if recall else "") + " |")
    by = summary.get("files_by_rule", {})
    byv = summary.get("files_by_verdict", {})
    out += ["", f"**合计**：{summary['files_total']} 个被滤文件；按规则 {by}；按判定 {byv}。"]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())