"""Register the source assets of report 10647 (work package wp-10647-01, task_type 01-asset-registration).

Report: 【长跑生存层】核心转储取证 + 位级幂等断点续跑 + 资源降级阶梯（m9082 / p148w2-n03）
         scenario_key = crash-forensics-resume  (platform infra, no ship/domain semantics)

Design rules enforced by this script
  * No hand transcription. Every ``quote`` is sliced out of the report markdown at run time from a
    programmatic anchor (anchor must be *unique* in the markdown), and every quote is re-checked to be
    a unique substring before anything is written.
  * ``in_report_section`` is derived from the document (nearest preceding markdown heading), never typed.
  * Registration only: no claim extraction (contract objective.register_assets only, claims may be []).
    Nothing is marked verified -- ``resolution`` describes locator resolvability only.
  * Referenced-but-not-resolvable items stay visible as ``referenced_unresolved`` / ``declared_absent``
    with the executed check and its result; they are never dropped and never given an invented address.
  * Upstream numeric tables are located, not recomputed: runs/m9082/evidence.json does not exist in
    this worktree, so their numbers are registered as *located* text with an explicit trace note.

Inputs
  runs/wp-10647-01/report_10647.md    markdown payload (verbatim, sha256 pinned by the contract)
  runs/wp-10647-01/report_10647.json  raw API payload (id/title/scenario_key/figures/tags/mission)

Outputs
  artifacts/wp-10647-01/asset_manifest.json          the deliverable of the work package
  runs/wp-10647-01/kf_result.wp-10647-01.json        result envelope (kf_result.v1 shape)
  runs/wp-10647-01/kf_result_block.wp-10647-01.json  same JSON, for the single ```json block

Usage: python3 scripts/kf_register_10647.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

REPORT_ID = "10647"
PACKAGE_ID = "wp-10647-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/10647"
EXPECTED_HASH = "aa10fd7a44acab4a0c877a58dab70f087877e249a28e2684f9a6a7a2d6dfbf31"
EXPECTED_CHARS = 10814

RUN_DIR = pathlib.Path("runs/wp-10647-01")
ART_DIR = pathlib.Path("artifacts/wp-10647-01")
DOC_DIR = pathlib.Path("docs/kf/wp-10647-01")
REPO_ROOT = pathlib.Path(".").resolve()

# ---------------------------------------------------------------------------------------------
# Asset specification. Each entry: anchor (unique substring in the markdown) + slice mode.
# slice modes: line | block (consecutive non-blank lines) | table (consecutive '|' lines from anchor
#              line) | table_after (first table block after anchor) | fence (enclosing ``` block)
# ---------------------------------------------------------------------------------------------
SPECS = [
    dict(id="A01", cls="code_module", label="TensorPlatform 新模块目录 tools/longrun/（零领域语义共性机制）",
         anchor="**落库**：`TensorPlatform` → 新模块 `tools/longrun/`", mode="line",
         res="referenced_unresolved", check=("worktree_paths", ["tools/longrun/"]),
         note="TensorPlatform 仓内路径；本工作树（TensorKnowledge）无该目录，模块实体不可在此解析"),
    dict(id="A02", cls="evidence_dataset", label="证据工件 runs/m9082/evidence.json（全部数字的程序化来源）",
         anchor="**证据**：`runs/m9082/evidence.json`", mode="line",
         res="referenced_unresolved", check=("worktree_paths", ["runs/m9082/evidence.json"]),
         note="报告声明全部数字由此工件程序化生成；工件不在本工作树，故本工序只定位不复核数值"),
    dict(id="A03", cls="figure_set", label="图工件目录 runs/m9082/figures/fig1..4（matplotlib 生成）",
         anchor="**图**：`runs/m9082/figures/fig1..4`", mode="line",
         res="referenced_unresolved", check=("worktree_paths", ["runs/m9082/figures/"]),
         note="目录不在本工作树；四张图的名称/说明另见平台 payload（A22–A25）"),
    dict(id="A04", cls="test_suite", label="测试套件 tests/test_longrun_{forensics,checkpoint_resume,ladder,overhead}.py（共 32 用例）",
         anchor="**测试**：`tests/test_longrun_{forensics,checkpoint_resume,ladder,overhead}.py`", mode="line",
         res="referenced_unresolved",
         quote_contains="tests/test_longrun_{forensics,checkpoint_resume,ladder,overhead}.py",
         check=("worktree_paths", ["tests/test_longrun_forensics.py", "tests/test_longrun_checkpoint_resume.py",
                                   "tests/test_longrun_ladder.py", "tests/test_longrun_overhead.py"]),
         note="TensorPlatform 的 tests/；本仓 tests/ 内无同名文件（本仓 tests/ 是 TensorKnowledge 的）"),
    dict(id="A05", cls="code_module", label="崩溃取证部件 guardian.py（ptrace 监护 + gdb 取证）与 forensics.py（记录仪/分类/完整率）",
         anchor="| 崩溃取证 | `guardian.py`", mode="line",
         res="referenced_unresolved", check=("worktree_paths", ["tools/longrun/guardian.py", "tools/longrun/forensics.py"]),
         note="能力表首行；模块实体在 TensorPlatform 仓，本工作树不可解析"),
    dict(id="A06", cls="code_module", label="断点续跑部件 checkpoint.py（位级摘要+原子写+链式清单）与 resume.py（幂等键+审计）",
         anchor="| 断点续跑 | `checkpoint.py`", mode="line",
         res="referenced_unresolved", check=("worktree_paths", ["tools/longrun/checkpoint.py", "tools/longrun/resume.py"]),
         note="能力表第二行；模块实体不在本工作树"),
    dict(id="A07", cls="code_module", label="资源降级部件 ladder.py（四级阶梯）",
         anchor="| 资源降级 | `ladder.py`", mode="line",
         res="referenced_unresolved", check=("worktree_paths", ["tools/longrun/ladder.py"]),
         note="能力表第三行；模块实体不在本工作树"),
    dict(id="A08", cls="code_module", label="负控部件 runner.py 与基准脚本 bench_m9082.py",
         anchor="| 负控 | `runner.py`", mode="line",
         res="referenced_unresolved", check=("worktree_paths", ["tools/longrun/runner.py", "tools/longrun/bench_m9082.py"]),
         note="能力表第四行；模块实体不在本工作树"),
    dict(id="A09", cls="test_job_spec", label="测试作业 job.py::SyntheticIterativeJob（线性迭代松弛 u ← u + dt·(∇²u + c)，无物理语义）",
         anchor="`job.py::SyntheticIterativeJob`", mode="block",
         res="referenced_unresolved", check=("worktree_paths", ["tools/longrun/job.py"]),
         note="合成作业定义在 TensorPlatform 仓；本工作树无此文件，作业实现不可解析"),
    dict(id="A10", cls="design_table", label="能力→部件→判据映射表（4 行）",
         anchor="| 能力 | 部件 | 关键判据 |", mode="table",
         res="resolved_in_source", check=("in_source", None),
         note="上游自报的部件划分与判据；本工序只登记不复核判据是否达成。本资产为容器级跨度，"
              "刻意包含 A05–A08 四个逐行资产（见 artifacts/wp-10647-01/verification.json 的 span_nesting 白名单）"),
    dict(id="A11", cls="procedure_spec", label="ptrace 监护流程伪代码（fork→PTRACE_TRACEME→execve→waitpid→DETACH→gdb -batch→SIGKILL）",
         anchor="fork → 子进程 ptrace(PTRACE_TRACEME) → execve(job)", mode="fence",
         res="resolved_in_source", check=("tool_probe", ["gdb", "addr2line"]),
         note="流程图以代码块给出；工具可用性探测见 resolution_check（探测对象=本工作树容器，非作者容器）"),
    dict(id="A12", cls="measurement_table", label="两级取证工件表（tier-1 stackcore.json 8.9–30.8 KB / tier-2 ELF core 14 MB 与 4.44 GB）",
         anchor="### 2.3 两级取证工件", mode="table_after",
         res="resolved_in_source", check=("in_source", None),
         note="体积数字唯一可溯源副本为 runs/m9082/evidence.json（本工作树缺失），故只定位不复算"),
    dict(id="A13", cls="measurement_protocol", label="开销测量方法学留证：AB-only 位置偏置（幻影 +5.27 %/−3.03 %）→ ABBA + 中位数门",
         anchor="**方法学留证**", mode="block",
         res="resolved_in_source", check=("in_source", None),
         note="描述了测量协议的迭代与理由；逐轮开销值见 A14 上游（§3.1 表）"),
    dict(id="A14", cls="measurement_table", label="§3.1 负控开销表（逐轮 12 值、中位数 −0.65 %、最大 +14.52 %、仪器自计 0.0889 %）",
         anchor="### 3.1 负控：正常作业取证开销 ≤ 2%", mode="table_after",
         res="resolved_in_source", check=("artifact_trace", "runs/m9082/evidence.json"),
         note="数值可逐字定位；复算需 evidence.json（本工作树缺失）→ 仅登记，不做数值复核"),
    dict(id="A15", cls="measurement_schema", label="崩溃取证表（5 种注入模式：segv/abort/exception/memory_error/sigkill，完整率均 100 %）",
         anchor="### 3.2 崩溃取证：五种故意崩溃", mode="table_after",
         res="resolved_in_source", check=("artifact_trace", "runs/m9082/evidence.json"),
         note="上传上游自报 100 %；本工序不复核，也不标 verified"),
    dict(id="A16", cls="measurement_schema", label="取证完整率口径：15 个必需字段（schema/job_id/pid/…/最后检查点摘要）+ 信号类崩溃额外计入 ELF core",
         anchor="完整率按 15 个必需字段计", mode="block",
         res="resolved_in_source", check=("in_source", None),
         note="完整率的分母定义在此；缺此口径则 100 % 不可解释"),
    dict(id="A17", cls="measurement_table", label="§3.3 位级幂等续跑表（断点 10/20/35，摘要 f80ed84ab59f2374 全一致，幂等键 1dbad8a55a4f/93f94d256fec）",
         anchor="### 3.3 位级幂等续跑", mode="table_after",
         res="resolved_in_source", check=("artifact_trace", "runs/m9082/evidence.json"),
         note="断点 35 的幂等键上游明确留白（见 evidence.json），本工序不补造"),
    dict(id="A18", cls="formula", label="位级摘要定义：sha256(dtype‖shape‖状态字节)，即 0 ULP 判据而非容差判据",
         anchor="位级 = `sha256(dtype‖shape‖状态字节)`", mode="block",
         res="resolved_in_source", check=("in_source", None),
         note="该定义决定“一致”的含义（位级 vs 容差）；跨 ISA 适用性限制登记为 A28"),
    dict(id="A19", cls="measurement_table", label="§3.4 检查点损坏检出表（载荷翻转 40/40、盲翻转 60/60、清单篡改 1/1、删数组 1/1、残留 .tmp 正确忽略）",
         anchor="### 3.4 检查点损坏检出", mode="table_after",
         res="resolved_in_source", check=("artifact_trace", "runs/m9082/evidence.json"),
         note="检出率为上游自报；探针构造方式依赖 checkpoint.py（本工作树缺失）不可复现"),
    dict(id="A20", cls="measurement_note", label="盲翻转落进 zip 簿记区（extra-field/padding）不算漏检的论证（开发期曾 58/60）",
         anchor="注：盲翻转若落进 zip 的 extra-field/padding", mode="block",
         res="resolved_in_source", check=("in_source", None),
         note="上游对“检出率不足 100 %”的反例与辩解，保留原文不做判定"),
    dict(id="A21", cls="measurement_table", label="§3.5 降级阶梯结果（占用 65536→8192 B=0.125×、末态 grid 32→16、退出码 75）",
         anchor="### 3.5 降级阶梯", mode="table_after",
         res="resolved_in_source", check=("artifact_trace", "runs/m9082/evidence.json"),
         note="退出码 75 语义（sysexits EX_TEMPFAIL）在 §2.7 阶梯表给出"),
    dict(id="A22", cls="measurement_table", label="§3.6 ELF 真核结果（14 048 136 B、reopen_ok=True、13 帧、取证 0.264 s、cap=1 MiB 守卫）",
         anchor="### 3.6 ELF 真核（tier-2）", mode="table_after",
         res="resolved_in_source", check=("artifact_trace", "runs/m9082/evidence.json"),
         note="numpy 进程 4 448 817 440 B 为“开发期一次，未重跑省磁盘”，不可复现项已由上游自陈"),
    dict(id="A23", cls="figure", label="图 fig1_overhead.png（12 轮 ABBA 开销柱状 + 2 % 预算线 + 中位线）",
         anchor="| `fig1_overhead.png` |", mode="line",
         res="referenced_unresolved", check=("figure_platform", "fig1_overhead.png"),
         note="平台 payload 有 name/caption；png_base64 为空且 runs/m9082/figures/ 不在本工作树 → 位图在本环境不可得（平台响应不回传图件字节，见 platform_figure_probe.json，不推断作者是否附图）"),
    dict(id="A24", cls="figure", label="图 fig2_autopsy.png（五模式完整率 + tier-1 体积）",
         anchor="| `fig2_autopsy.png` |", mode="line",
         res="referenced_unresolved", check=("figure_platform", "fig2_autopsy.png"),
         note="同上：仅元数据可解析，位图在本环境不可得"),
    dict(id="A25", cls="figure", label="图 fig3_resume.png（断点位置 vs 位级一致性）",
         anchor="| `fig3_resume.png` |", mode="line",
         res="referenced_unresolved", check=("figure_platform", "fig3_resume.png"),
         note="同上：仅元数据可解析，位图在本环境不可得"),
    dict(id="A26", cls="figure", label="图 fig4_ladder.png（内存利用率探测/阈值 + 状态占用阶梯）",
         anchor="| `fig4_ladder.png` |", mode="line",
         res="referenced_unresolved", check=("figure_platform", "fig4_ladder.png"),
         note="同上：仅元数据可解析，位图在本环境不可得"),
    dict(id="A27", cls="environment_limitation", label="内核自发 core 采集不可用（容器 core_pattern 指向 systemd-coredump，无 systemd）",
         anchor="* **内核 core_pattern 在本容器不可用**", mode="bullet",
         res="declared_absent", check=("core_pattern_probe", None),
         note="上游明确记为“无基准项”而非“未测充数”；本工序在本容器复跑同一探针，不改写上游结论"),
    dict(id="A28", cls="scope_limitation", label="适用范围限制：位级一致限同机同库，跨 ISA（loong64 vs x86）须改用 tools/repro_digest（ULP/12 位有效数字）",
         anchor="* **位级一致限于同机同库**", mode="bullet",
         res="resolved_in_source", check=("in_source", None),
         note="该限制是 A17/A18 位级判据的适用边界，登记以备下游抽取时携带"),
    dict(id="A29", cls="measurement_table", label="§6 误差判定表（8 行，逐项显式回答“是否 < 3 %”）",
         anchor="## ⑥ 误差判定", mode="table_after",
         res="resolved_in_source", check=("artifact_trace", "runs/m9082/evidence.json"),
         note="误差栏全部为 0 %/0 位差型判据；本工序只登记不复核，且不把“是否<3%”标成 verified"),
    dict(id="A30", cls="repro_command", label="一键复现命令块（pytest 四模块 + bench_m9082 重生成 evidence.json 与图）",
         anchor="python3 -m pytest tests/test_longrun_forensics.py", mode="fence",
         res="resolved_in_source", check=("in_source", None),
         note="命令指向 TensorPlatform 仓；本工作树无法执行（仓内无 tools.longrun）"),
    dict(id="A31", cls="code_snippet", label="单次使用示例（supervise.supervise(...) 返回 failure_mode/core.status/bundle_completeness）",
         anchor="from tools.longrun import supervise", mode="fence",
         res="resolved_in_source", check=("in_source", None),
         note="API 契约样例；import 目标模块不在本工作树，未执行"),
]


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def slice_from(md: str, anchor: str, mode: str) -> tuple[int, int]:
    """Return (start, end) char offsets of the slice identified by ``anchor`` + ``mode``."""
    n = md.count(anchor)
    if n != 1:
        raise SystemExit("anchor not unique (%d hits): %r" % (n, anchor))
    pos = md.index(anchor)
    line_start = md.rfind("\n", 0, pos) + 1
    if mode == "line":
        nl = md.find("\n", pos)
        return line_start, (len(md) if nl < 0 else nl)
    if mode == "block":
        i = line_start
        while True:
            nl = md.find("\n", i)
            if nl < 0:
                return line_start, len(md)
            if md[i:nl].strip() == "":
                return line_start, i - 1
            i = nl + 1
    if mode == "bullet":
        i = line_start
        while True:
            nl = md.find("\n", i)
            if nl < 0:
                return line_start, len(md)
            nxt = md[nl + 1:]
            nxt_line = nxt.split("\n", 1)[0]
            if nxt_line.strip() == "" or nxt_line.startswith("* ") or nxt_line.startswith("- "):
                return line_start, nl
            i = nl + 1
    if mode == "table":
        i = line_start
        if not md[i:].lstrip().startswith("|"):
            raise SystemExit("table mode anchor is not on a table line: %r" % anchor)
        while True:
            nl = md.find("\n", i)
            seg = md[i:(len(md) if nl < 0 else nl)]
            if not seg.startswith("|"):
                return line_start, i - 1
            if nl < 0:
                return line_start, len(md)
            i = nl + 1
    if mode == "table_after":
        i = line_start
        while True:
            nl = md.find("\n", i)
            if nl < 0:
                raise SystemExit("no table found after anchor: %r" % anchor)
            seg = md[i:nl]
            if seg.startswith("|"):
                return slice_from(md, seg, "table") if md.count(seg) == 1 else _table_from(md, i)
            i = nl + 1
    if mode == "fence":
        open_i = md.rfind("```", 0, pos)
        if open_i < 0:
            raise SystemExit("no opening fence before anchor: %r" % anchor)
        open_line_start = md.rfind("\n", 0, open_i) + 1
        close_i = md.find("```", md.find("\n", pos))
        if close_i < 0:
            raise SystemExit("no closing fence after anchor: %r" % anchor)
        return open_line_start, close_i + 3
    raise SystemExit("unknown mode: %r" % mode)


def _table_from(md: str, line_start: int) -> tuple[int, int]:
    i = line_start
    while True:
        nl = md.find("\n", i)
        seg = md[i:(len(md) if nl < 0 else nl)]
        if not seg.startswith("|"):
            return line_start, i - 1
        if nl < 0:
            return line_start, len(md)
        i = nl + 1


def derive_section(md: str, start_char: int) -> str:
    """Nearest preceding markdown heading line, verbatim (machine-derived, not typed)."""
    head = md[:start_char]
    lines = head.split("\n")
    for line in reversed(lines[:-1] if head.endswith("\n") is False else lines):
        if line.startswith("#"):
            return line
    return lines[0]


def probe_core_pattern() -> dict:
    """Re-run the report's environment probe in *this* container (informational, not a verdict)."""
    detail = {"probe": "cat /proc/sys/kernel/core_pattern + coredumpctl availability",
              "container_note": "本工作树容器，非报告作者的容器；只作可复现探针记录，不据此判定上游结论"}
    try:
        cp = pathlib.Path("/proc/sys/kernel/core_pattern").read_text(errors="replace").strip()
    except Exception as exc:  # pragma: no cover
        cp = "unreadable: %r" % (exc,)
    detail["core_pattern"] = cp
    pipe = None
    if cp.startswith("|"):
        pipe = cp[1:].split()[0]
    detail["pipe_target"] = pipe
    detail["pipe_target_exists"] = bool(pipe) and os.path.exists(pipe)
    cctl = shutil.which("coredumpctl")
    detail["coredumpctl"] = cctl
    cctl_ok = None
    if cctl:
        try:
            p = subprocess.run([cctl, "--version"], capture_output=True, timeout=20)
            cctl_ok = p.returncode == 0
            detail["coredumpctl_version_rc"] = p.returncode
            detail["coredumpctl_stderr_head"] = p.stderr.decode("utf-8", "replace").splitlines()[:1]
        except Exception as exc:  # pragma: no cover
            detail["coredumpctl_error"] = repr(exc)
    detail["coredumpctl_functional"] = cctl_ok
    detail["result_note"] = "内核自发 core 路由不可用 = 上游声明；本容器探针仅记录现状"
    return detail


def probe_tools(tools: list[str]) -> dict:
    found = {t: shutil.which(t) for t in tools}
    return {"tools": found, "all_present": all(found.values())}


def path_check(paths: list[str]) -> dict:
    present = [p for p in paths if (REPO_ROOT / p).exists()]
    missing = [p for p in paths if p not in present]
    return {"check": "worktree_path_exists", "repo": "TensorKnowledge", "paths": paths,
            "present": present, "missing": missing,
            "result": "resolved" if not missing else "unresolved"}


def build_manifest(md: str, payload: dict) -> dict:
    figs = payload.get("figures") or []
    fig_names = [f.get("name") for f in figs]
    assets = []
    for spec in SPECS:
        start, end = slice_from(md, spec["anchor"], spec["mode"])
        quote = md[start:end]
        if md.count(quote) != 1:
            raise SystemExit("%s quote not unique in markdown" % spec["id"])
        kind, arg = spec["check"]
        if kind == "in_source":
            check = {"check": "char_span_in_source_markdown", "result": "resolved"}
        elif kind == "worktree_paths":
            check = path_check(arg)
            if spec.get("quote_contains"):
                needles = spec["quote_contains"] if isinstance(spec["quote_contains"], list) else [spec["quote_contains"]]
            else:
                needles = [p.rstrip("/").split("/")[-1] for p in arg]
            for needle in needles:
                if needle and needle not in quote:
                    raise SystemExit("%s: %r not present in quote" % (spec["id"], needle))
        elif kind == "figure_platform":
            f = next((x for x in figs if x.get("name") == arg), None)
            b64 = (f or {}).get("png_base64") or ""
            check = {"check": "platform_figure_metadata", "figure_name": arg,
                     "name_in_payload": f is not None,
                     "caption_in_payload": bool((f or {}).get("caption")),
                     "png_bytes_in_payload": len(b64),
                     "name_in_quote": arg in quote,
                     "result": "unresolved",
                     "detail": ("payload 提供 name/caption；png_base64 为空且目录不在本工作树 → 位图在本环境不可得。"
                                "同平台实测（docs/kf/wp-10647-01/platform_figure_probe.json）：本工单提交的非空 png "
                                "在 API 响应中同样返回 0 字节，且无图件下载端点 → 空字节是响应侧行为，"
                                "不能据此推断作者未附图")}
        elif kind == "artifact_trace":
            p = path_check([arg])
            check = {"check": "artifact_trace", "artifact": arg,
                     "present_in_worktree": bool(p["present"]), "result": "resolved",
                     "detail": "引文可定位（resolved）；数值复算需 %s，本工作树缺失 → 未复算" % arg}
        elif kind == "tool_probe":
            tp = probe_tools(arg)
            check = {"check": "tool_probe", "tools": tp["tools"], "all_present": tp["all_present"],
                     "result": "resolved", "detail": "流程规范自身可在原文解析；工具探测只记录本容器现状"}
        elif kind == "core_pattern_probe":
            cp = probe_core_pattern()
            check = {"check": "core_pattern_probe", "result": "absent"}
            check.update(cp)
        else:  # pragma: no cover
            raise SystemExit("unknown check kind %r" % kind)
        start_line = md.count("\n", 0, start)
        end_line = md.count("\n", 0, max(end - 1, start))
        assets.append({
            "asset_id": spec["id"],
            "asset_class": spec["cls"],
            "label": spec["label"],
            "in_report_section": derive_section(md, start),
            "locator": {"method": "char_span", "start_char": start, "end_char": end,
                        "start_line": start_line, "end_line": end_line,
                        "quote": quote, "unique": True},
            "resolution": spec["res"],
            "resolution_check": check,
            "note": spec["note"],
        })

    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    ids = [a["asset_id"] for a in assets]
    if len(set(ids)) != len(ids):
        raise SystemExit("duplicate asset_id")

    return {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": sha256_hex(md.encode("utf-8")),
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "title": payload.get("title"),
            "scenario_key": payload.get("scenario_key"),
            "platform_figures": [{"name": f.get("name"), "caption": f.get("caption"),
                                  "png_bytes": len(f.get("png_base64") or "")} for f in figs],
            "platform_tags": payload.get("tags") or [],
            "platform_mission_id": payload.get("mission_id"),
            "platform_status": payload.get("status"),
        },
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_res.items())),
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
        },
        "assets": assets,
        "claims": [],
        "claims_note": ("按工作包契约 objective.classify_report_type=false 且 notes 允许 claims 为空数组："
                        "本工序只登记资产定位，不做抽取，不生成未经抽取的“知识”条目；claim 抽取由下游工序负责。"),
        "integrity": {
            "quote_uniqueness": ("每条引文均为源 markdown 的唯一子串（本脚本 slice 后 md.count(quote)==1 断言；"
                                 "scripts/kf_verify_10647.py 独立重算）"),
            "hash_recomputed_locally": sha256_hex(md.encode("utf-8")) == EXPECTED_HASH,
            "hash_matches_contract": sha256_hex(md.encode("utf-8")) == EXPECTED_HASH,
            "claims_empty_by_contract": True,
            "no_verified_marker": not any(
                str(a.get("resolution", "")).lower() == "verified"
                or str(a.get("resolution_check", {}).get("status", "")).lower() == "verified"
                for a in assets),
            "verified_status_objects": 0,
            "word_verified_disclaimers": [
                {"asset_id": a["asset_id"], "field": "note", "snippet": a["note"]}
                for a in assets if "verified" in a["note"].lower()
            ],
        },
    }


def main() -> int:
    md_path = RUN_DIR / "report_10647.md"
    payload_path = RUN_DIR / "report_10647.json"
    if not md_path.exists() or not payload_path.exists():
        print("ERROR: run scripts/kf_fetch_10647.py first")
        return 1
    md = md_path.read_text(encoding="utf-8")
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    h = sha256_hex(md.encode("utf-8"))
    if h != EXPECTED_HASH:
        print("ERROR: markdown hash mismatch: %s != %s" % (h, EXPECTED_HASH))
        return 2
    if len(md) != EXPECTED_CHARS:
        print("ERROR: char count mismatch: %d != %d" % (len(md), EXPECTED_CHARS))
        return 2

    manifest = build_manifest(md, payload)

    ART_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    (ART_DIR / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DOC_DIR / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": "sha256:" + h,
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "title": payload.get("title"),
            "scenario_key": payload.get("scenario_key"),
            "producer": "scripts/kf_register_10647.py",
            "emitted_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).isoformat(timespec="seconds"),
            "notes": ("asset registration only; claims intentionally empty; nothing marked verified"),
            "contract_declared_hash": "sha256:" + EXPECTED_HASH,
            "hash_match": True,
            "platform_mission_id": payload.get("mission_id"),
            "platform_status": payload.get("status"),
            "platform_tags": payload.get("tags") or [],
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    text = json.dumps(envelope, ensure_ascii=False, indent=2) + "\n"
    (RUN_DIR / "kf_result.wp-10647-01.json").write_text(text, encoding="utf-8")
    (RUN_DIR / "kf_result_block.wp-10647-01.json").write_text(text, encoding="utf-8")

    print("assets            :", manifest["counts"]["assets"])
    print("by_resolution     :", manifest["counts"]["by_resolution"])
    print("by_class          :", manifest["counts"]["by_class"])
    print("claims            :", len(manifest["claims"]))
    print("hash_matches      :", manifest["integrity"]["hash_matches_contract"])
    print("no_verified_marker:", manifest["integrity"]["no_verified_marker"])
    return 0


if __name__ == "__main__":
    sys.exit(main())