#!/usr/bin/env python3
"""wp-4129-04: extraction of the source-derived evidence base for the review.

Everything the review quotes is *sliced out of the markdown* here, never retyped,
so the zero-hand-copy rule holds by construction.

Outputs:
  work/wp-4129-04/evidence/quotes.json   quote_id -> verbatim slice (+line, sha256)
  work/wp-4129-04/evidence/path_refs.json re-derived path-reference census
"""
import hashlib
import json
import pathlib
import re

WT = pathlib.Path(".")
MD = (WT / "work/wp-4129-04/source/report_4129.md").read_bytes().decode("utf-8")
lines = MD.rstrip("\n").split("\n")
OUT = WT / "work/wp-4129-04/evidence"


def L(n, col=None):
    """1-based line slice; optional (start,end) character window."""
    s = lines[n - 1]
    if col:
        s = s[col[0]:col[1]]
    return s


def find_line(pred, start=1):
    for i in range(start, len(lines) + 1):
        if pred(lines[i - 1]):
            return i
    raise LookupError("line not found")


def span(needle, line_hint=None):
    """Verbatim substring located by search (optionally constrained to a line)."""
    if line_hint is not None:
        i = lines[line_hint - 1].find(needle)
        assert i >= 0, (needle, line_hint)
        return lines[line_hint - 1][i:i + len(needle)]
    i = MD.find(needle)
    assert i >= 0, needle
    return MD[i:i + len(needle)]


quotes = {}


def q(qid, text, line=None):
    assert text in MD, qid
    quotes[qid] = {"quote": text, "line": line or (MD[:MD.find(text)].count("\n") + 1),
                   "quote_sha256": "sha256:" + hashlib.sha256(text.encode()).hexdigest()}


# --- header / identity ------------------------------------------------------
q("h1_title", L(1), 1)
q("repo_branch_merge", L(3), 3)
q("parent_line", L(4), 4)
q("pr_scope_line", L(8), 8)
q("conflict_table_row", span("| 冲突文件 | **1**（`CHANGELOG.md`） |"))
q("auto_merge_row", span("| 自动合并文件 | 191 |"))
q("mergeable_false", span("PR 因此 `mergeable=false`。"), 11)
q("plate_params_row", span("| 项 | 值 |"))
q("plate_params_body", span("板边长 `1.0 m`、`E = 2.1e+11 Pa`、"), 22)
# --- results table ----------------------------------------------------------
q("results_header", span("| 状态 | 行数 | 非空行 | `## Unreleased` 段数 | Cook 段条目 | 错位到 B-bar 段 | 结构审计 |"))
q("results_branch_row", span("| 分支 `c441d91` | 325 | 243 | 2 | 4 | – | 拒绝（1 项） |"))
q("results_main_row", span("| `main` `7accc4b` | 369 | 283 | 1 | **0** | **2** | 拒绝（3 项） |"))
q("results_replay_row", span("| **未解冲文本合并（重放）** | – | – | – | – | **2** | **拒绝（4 项；冲突标记 1 处）** |"))
q("results_final_row", span("| **解冲结果（入仓）** | 379 | 292 | 1 | 4 | 0 | **通过（0 项）** |"))
q("preservation_header", span("| 对照父提交 | 丢失行 | 显式允许（重复标题去重） | 意外丢失 |"))
q("preservation_branch", span("| 分支父 `c441d91` | 1 | 1 | **0** |"))
q("preservation_main", span("| `main` 父 `7accc4b` | 0 | 0 | **0** |"))
q("anchor_gate_line", span("非负控 anchor **11 项**，"))
q("max_rel_err", span("最大相对误差 **0.4886 %**，"))
q("gate_thresholds", span("逐项门限 0.1 %, 1 %, 3 %，"))
q("all_passed_true", span("`all_passed = True`。"))
q("new_sha", span("新 SHA `b7bbe3707838bc8bb25af16c77134efd58b2b75e`（旧 `c441d91`）。"))
# --- honest-fail rows -------------------------------------------------------
q("honest_not_done", span("| 本地全量套件（1707 项） | 全绿 | **未完成**（见下） | **不计为通过** |"))
q("honest_body", span("本地没有跑完全量套件，不能声明全绿"))
q("gate_test_7p", span("`tests/test_changelog_integrity.py` 7 passed（含 2 负控）；"))
q("plate_test_progress", span("`tests/test_plate_uniform_load.py` 本机进度 6 passed / 0 failed"))
q("tree_identity", span("`git diff 7accc4b HEAD -- src/` 只有新增 `src/tensorfem/plate_uniform_load.py`（445 行），"))
# --- caveats ---------------------------------------------------------------
q("caveat_worktree", span("3. **`import tensorfem` 可能指向别的 worktree。**"))
q("caveat_worktree_src", span("`/root/tp-agent/work/m3182/src`；验证必须 `PYTHONPATH=<本 worktree>/src` 并打印"))
q("caveat_file_token", span("`tensorfem.__file__` 自证，否则测的是别人的代码。"))
q("caveat_timeout", span("4. **满载下 `--timeout` 会造成假失败。**"))
q("caveat_unfixed_layout", span("6. **未修 `main` 的全局版式**（如实）："))
q("fig1_body", span("图 1（左）四种状态的 `CHANGELOG.md` 结构发现数（0 = 干净）"))
q("fig2_body", span("图 2 本 PR 携带的板锚点误差（对数横轴）"))

# --- path-reference census (independent of the producer's numbers) ----------
SPAN = re.compile(r"`([^`\n]+)`")


def is_path(s):
    if s.startswith("/") or "/" in s:
        if s.startswith("PYTHONPATH=") or s.startswith("git ") or s.startswith("setsid"):
            return None
        if s.startswith("agent/"):
            return None            # branch ref, registered as vcs_reference
        if " " in s:
            return None
        return s
    if s.endswith((".md", ".py", ".json", ".png")):
        return s
    return None


sites = []
for i, line in enumerate(lines, 1):
    for raw in SPAN.findall(line):
        p = is_path(raw)
        if p:
            sites.append({"line": i, "token": raw, "registered_scope": "title" if i == 1 else None})

path_refs = {
    "sites_total_in_body": sum(1 for s in sites if s["line"] != 1),
    "sites_including_title_line": len(sites),
    "distinct_tokens": sorted({s["token"] for s in sites}),
    "distinct_count": len({s["token"] for s in sites}),
    "sites": sites,
    "png_links_in_body": re.findall(r"!\[[^\]]*\]\([^)]*\)|<img[^>]*>", MD),
    "trailing_newline": MD.endswith("\n"),
}

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "quotes.json").write_text(json.dumps(quotes, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "path_refs.json").write_text(json.dumps(path_refs, ensure_ascii=False, indent=2), encoding="utf-8")
print("quotes:", len(quotes), "all verbatim:",
      all(v["quote"] in MD for v in quotes.values()))
print("path sites (body):", path_refs["sites_total_in_body"],
      "incl. title:", path_refs["sites_including_title_line"],
      "distinct:", path_refs["distinct_count"])
for s in sites:
    print("  ", s["line"], s["token"])
print("png links in body:", path_refs["png_links_in_body"])
print("trailing newline:", path_refs["trailing_newline"])