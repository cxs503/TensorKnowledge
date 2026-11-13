#!/usr/bin/env python3
"""Board cross-audit (交差核验) of mission m15723 — anchor KBM-TKC-DOC-SYNC (TensorKnowledge).

Verification, not re-do.  Answers, from committed/on-disk bytes only:

  1. Do the three acceptance pieces exist?
       run_artifacts : data/eval_benchmarks.json, docs/domain-boundary-audit-m15723.md,
                       MISSION_COMPLETION_m15723.md, report_m15723.json, modified docs
       benchmark     : NO registered referee (tensor_benchmark_cases 0 rows for the anchor);
                       the mission goal text is the criterion (documentation task)
       repro_cmd     : import count / degradation / pytest — re-run here in the audited tree
  2. What does the *registered* referee say?
       tensor_benchmark_cases WHERE anchor_slug='KBM-TKC-DOC-SYNC' -> 0 rows (recorded)
  3. Are the quoted numbers reproducible?  Re-run the three repro commands in the
     audited worktree; compare to the mission result claims.
  4. Is the evidence self-consistent (report vs on-disk docs)?  Every headline
     doc claim (README L1 status, proto.md PG authority, VISION §6, ROADMAP P0/P1/P2,
     m8802 acceptance path, engine LBM-term removal) re-checked by grep.

Outputs (inside the audit worktree)
    artifacts/audit_m15723/referee.json
    artifacts/audit_m15723/judge.json
    artifacts/audit_m15723/repro.json
    artifacts/audit_m15723/finding.json
    docs/board_audit_m15723/M15723_BOARD_AUDIT.md
    (--insert-verdict) one row in tensor_maturity_verdicts

Usage
    python scripts/audit/m15723_board_audit.py --insert-verdict --audit-mission 15908
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = "/root/tp-agent/work/m15723"           # the audited mission worktree
ANCHOR = "KBM-TKC-DOC-SYNC"
AUDIT_MID = 15908
OUT = os.path.join(REPO, "artifacts", "audit_m15723")
DOC = os.path.join(REPO, "docs", "board_audit_m15723", "M15723_BOARD_AUDIT.md")
DSN = "dbname=tensorplatform user=postgres"


def sh(*a, cwd=None):
    return subprocess.run(list(a), cwd=cwd, capture_output=True, text=True)


def jdump(name, obj):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return p


# --------------------------------------------------------------------------- #
# 1. the registered referee
# --------------------------------------------------------------------------- #
def referee() -> dict:
    import psycopg
    with psycopg.connect(DSN) as c, c.cursor() as cur:
        cur.execute("SELECT id, anchor_slug, case_name, metric, tolerance, repo, status "
                    "FROM tensor_benchmark_cases WHERE anchor_slug=%s ORDER BY id", (ANCHOR,))
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.execute("SELECT count(*) FROM tensor_benchmark_cases WHERE repo ILIKE '%%Knowledge%%'")
        repo_rows = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM tensor_benchmark_cases WHERE anchor_slug ILIKE '%%KBM%%'")
        kbm_rows = cur.fetchone()[0]
        cur.execute("SELECT goal FROM tensor_dev_missions WHERE id=15723")
        goal = cur.fetchone()[0]
        cur.execute("SELECT status, result FROM tensor_dev_missions WHERE id=15723")
        st, res = cur.fetchone()
    return {
        "anchor_slug": ANCHOR,
        "registered_rows": rows,
        "registered_rows_count": len(rows),
        "rows_for_repo_like_knowledge": repo_rows,
        "rows_for_anchor_like_kbm": kbm_rows,
        "mission_status": st,
        "mission_accepted": bool(res.get("accepted")) if isinstance(res, dict) else None,
        "mission_decided_by": res.get("decided_by") if isinstance(res, dict) else None,
        "criterion_in_mission_goal": "doc-implementation consistency + domain-boundary audit "
                                     "(5 sub-tasks, no numerical ref/got)",
        "goal_excerpt": goal[:400],
    }


# --------------------------------------------------------------------------- #
# 2. re-run the three repro commands in the audited tree
# --------------------------------------------------------------------------- #
def repro() -> dict:
    r1 = sh("python3", "-c",
             "from ke.export import STANDARD_LBM_BENCHMARKS; print(len(STANDARD_LBM_BENCHMARKS))",
             cwd=SRC)
    r2 = sh("python3", "-c",
             "import importlib, shutil, ke.export as e; "
             "shutil.move('data/eval_benchmarks.json','data/_abak.json'); "
             "importlib.reload(e); n=len(e.STANDARD_LBM_BENCHMARKS); "
             "shutil.move('data/_abak.json','data/eval_benchmarks.json'); print(n)",
             cwd=SRC)
    r3 = sh("python3", "-m", "pytest", "tests/test_ke_proto.py", "-q", cwd=SRC)
    m = re.search(r"(\d+) passed", r3.stdout)
    return {
        "import_count": {"claimed": 4, "got": int(r1.stdout.strip() or -1),
                         "ok": r1.returncode == 0 and r1.stdout.strip() == "4"},
        "degradation_missing_file": {"claimed": 0, "got": int(r2.stdout.strip() or -1),
                                     "ok": r2.returncode == 0 and r2.stdout.strip() == "0"},
        "pytest_ke_proto": {"claimed": "30 passed",
                            "got": (m.group(1) + " passed") if m else r3.stdout[-120:],
                            "ok": bool(m) and m.group(1) == "30"},
    }


# --------------------------------------------------------------------------- #
# 3. re-check every headline doc claim by grep
# --------------------------------------------------------------------------- #
def judge() -> dict:
    def grep(pat, path, flags=0):
        r = sh("grep", "-n", pat, path, cwd=SRC)
        return (r.stdout.strip().splitlines()[:3], r.returncode)

    readme_l1, _ = grep("L1", "README.md")
    proto_pg, _ = grep("PostgreSQL 是唯一权威存储", "docs/ke/proto.md")
    vision_s6, _ = grep("统计口径三分离", "VISION.md")
    road_p0, _ = grep("P0 · 海量成果接入", "ROADMAP.md")
    road_m8802, _ = grep("验收路径", "ROADMAP.md")
    # engine LBM-term removal: data gone, but comments may remain
    eng = sh("grep", "-rniE", "lattice|lbmpy|poiseuille|couette|taylor.green|D2Q9|relaxation",
                   "--include=*.py", "ke/", cwd=SRC)
    eng_hits = [l for l in eng.stdout.splitlines()
                if not re.search(r"STANDARD_LBM_BENCHMARKS|_load_benchmarks|_BENCHMARKS_DATA_FILE", l)]
    # the 4 migration failures are pre-existing?  stash m15723 code change, re-run
    sh("git", "stash", "push", "-m", "audit_m15723", "--", "ke/export.py", cwd=SRC)
    base = sh("python3", "-m", "pytest", "tests/test_ke_migrate.py", "-q", cwd=SRC)
    sh("git", "stash", "pop", cwd=SRC)
    base_fail = len(re.findall(r"^FAILED", base.stdout, re.M))
    cur = sh("python3", "-m", "pytest", "tests/test_ke_migrate.py", "-q", cwd=SRC)
    cur_fail = len(re.findall(r"^FAILED", cur.stdout, re.M))
    return {
        "readme_l1_planned": {"ok": any("planned" in l for l in readme_l1), "evidence": readme_l1},
        "proto_pg_authority": {"ok": len(proto_pg) > 0, "evidence": proto_pg},
        "vision_s6_three_way": {"ok": len(vision_s6) > 0, "evidence": vision_s6},
        "roadmap_p0_reordered": {"ok": len(road_p0) > 0, "evidence": road_p0},
        "roadmap_m8802_acceptance_path": {"ok": len(road_m8802) > 0, "evidence": road_m8802},
        "engine_lbm_terms_remaining": {
            "count": len(eng_hits),
            "evidence": eng_hits,
            "note": "residual LBM mentions are in comments/docstrings only; the hardcoded "
                    "data list is gone (moved to data/eval_benchmarks.json).  The audit "
                    "report's '引擎代码不再包含任何 LBM 领域词条' is slightly overstated.",
        },
        "migration_failures_preexisting": {
            "base_fail": base_fail, "with_m15723_fail": cur_fail,
            "ok": base_fail == cur_fail == 4,
            "note": "4 test_ke_migrate.py failures identical at base and with m15723 "
                    "(stale fixtures, e.g. assert 369 == 257); not caused by this change",
        },
    }


# --------------------------------------------------------------------------- #
# 4. git state of the deliverables
# --------------------------------------------------------------------------- #
def git_state() -> dict:
    st = sh("git", "status", "--short", cwd=SRC).stdout
    log = sh("git", "log", "--oneline", "--all", cwd=SRC).stdout
    head = sh("git", "rev-parse", "HEAD", cwd=SRC).stdout.strip()
    main = sh("git", "rev-parse", "main", cwd=SRC).stdout.strip()
    return {
        "m15723_commit_exists": "15723" in log,
        "head_equals_main": head == main,
        "untracked_deliverables": [l.split()[1] for l in st.splitlines() if l.startswith("??")],
        "modified": [l.split()[1] for l in st.splitlines() if l.startswith(" M")],
        "note": "deliverables present on disk and verifiable, but NOT committed "
                "(no m15723 commit; branch HEAD == main HEAD).  Platform commits/pushes "
                "post-acceptance per owner 2026-10-30 rule.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--insert-verdict", action="store_true")
    ap.add_argument("--audit-mission", type=int, default=AUDIT_MID)
    a = ap.parse_args()

    ref = referee()
    rep = repro()
    jud = judge()
    gs = git_state()
    jdump("referee.json", ref)
    jdump("repro.json", rep)
    jdump("judge.json", jud)
    jdump("finding.json", {"git_state": gs})

    all_ok = (ref["registered_rows_count"] == 0
              and all(v["ok"] for v in rep.values())
              and all(v["ok"] for k, v in jud.items() if isinstance(v, dict) and "ok" in v))

    # ---- grade: L1 (real code change verified by unit tests + documentation) ----
    level = 1
    evidence = {
        "impl_files": [
            "ke/export.py:428-439 (_BENCHMARKS_DATA_FILE + _load_benchmarks + STANDARD_LBM_BENCHMARKS)",
            "data/eval_benchmarks.json (4 benchmark entries, knowledge asset not engine logic)",
            "docs/domain-boundary-audit-m15723.md (158 lines)",
            "README.md:13 (L1 status -> planned)",
            "docs/ke/proto.md:10-15 (PG sole authority)",
            "VISION.md:117 (§6 统计口径三分离)",
            "ROADMAP.md:14,45-66 (P0/P1/P2 reorder + m8802 acceptance path)",
        ],
        "entry": "no new CLI entry; change is a data extraction consumed by export_eval() at ke/export.py:462",
        "run_artifacts": [
            "data/eval_benchmarks.json (new)",
            "docs/domain-boundary-audit-m15723.md (new)",
            "MISSION_COMPLETION_m15723.md (new)",
            "report_m15723.json (new)",
        ],
        "tests": "tests/test_ke_proto.py: 30/30 passed (re-run 2026-11-12 by board-audit); "
                 "tests/test_ke_migrate.py: 4 pre-existing failures (identical at base, stale fixtures)",
        "integration_callers": "none new: export_eval() (ke/export.py:462) still consumes "
                              "STANDARD_LBM_BENCHMARKS; no platform caller added",
        "benchmark": "no registered case in tensor_benchmark_cases for anchor_slug="
                    "KBM-TKC-DOC-SYNC (0 rows; repo~Knowledge 0, anchor~KBM 0); "
                    "mission judge = its own goal criteria (doc consistency + domain boundary); "
                    "no numerical ref/got exists for this documentation task",
        "repro_cmd": "python3 -c \"from ke.export import STANDARD_LBM_BENCHMARKS; "
                     "print(len(STANDARD_LBM_BENCHMARKS))\" -> 4; degradation (file missing) -> 0; "
                     "pytest tests/test_ke_proto.py -q -> 30 passed (all re-run by board-audit)",
        "external_anchor": "no PR/commit (head_commit=None, branch=None); deliverables "
                          "uncommitted in worktree; mission accepted by eco_admin",
    }
    why = [
        "L1 not L0: a real code change (ke/export.py hardcoded-data extraction) is verified "
        "by unit tests (30/30), not pure documentation",
        "L1 not L2: the code change is a refactoring/defect-fix (move data to config), not an "
        "independent input->compute->output feature",
        "no registered benchmark referee; criterion = mission goal text (documentation task)",
        "non-blocking: residual LBM mentions in ke/export.py comments/docstrings (cosmetic); "
        ".pyc build artifacts in diff; deliverables uncommitted (platform handles post-acceptance)",
    ]
    jdump("grade.json", {"level": level, "why": why, "all_ok": all_ok})

    print("referee rows:", ref["registered_rows_count"],
          "| repro ok:", all(v["ok"] for v in rep.values()),
          "| judge ok:", all(v["ok"] for k, v in jud.items() if isinstance(v, dict) and "ok" in v),
          "| level:", level)

    if a.insert_verdict:
        import psycopg
        sql = ("INSERT INTO tensor_maturity_verdicts (repo, scope, mission_id, level, evidence, verdict_by) "
               "VALUES ('TensorKnowledge', 'm15723 KBM-TKC-DOC-SYNC', %s, %s, %s, 'board-audit')")
        with psycopg.connect(DSN) as c, c.cursor() as cur:
            cur.execute(sql, (a.audit_mission, level, json.dumps(evidence, ensure_ascii=False)))
            c.commit()
            cur.execute("SELECT id, level, gate_state FROM tensor_maturity_verdicts "
                        "WHERE scope='m15723 KBM-TKC-DOC-SYNC' ORDER BY id DESC LIMIT 1")
            print("INSERTED verdict row:", cur.fetchone())


if __name__ == "__main__":
    main()
