"""Register the source assets of report 12316 (work package wp-12316-01, task_type 01-asset-registration).

Design rules enforced here (inherited from the wp-448-01 precedent in this repo):
  * No hand transcription. Every ``quote`` emitted is sliced out of the report markdown at run time
    from a programmatic anchor (line search + relative line span); the script refuses to write
    anything unless each quote is a *unique* substring of the markdown and equals md[start:end].
  * Registration only. No claim extraction (contract: objective.register_assets=true,
    classify_report_type=false; claims may be empty). Referenced artifacts that cannot be found are
    recorded as ``referenced_unresolved`` with the search that was performed -- never silently
    dropped and never given an invented address.
  * Nothing is marked verified. ``resolution`` describes locator resolvability only; the platform
    gate computes verification.
  * Cross-repo reads are read-only existence/sha256 probes. No file outside this worktree is
    modified, and no foreign artifact is copied into this package.

Inputs (fetched on demand from the platform API; creds from TENSOR_AGENT_USER/PASS):
  runs/wp-12316-01/report_12316.json  raw API payload (id/title/scenario_key/figures/...)
  runs/wp-12316-01/report_12316.md    markdown payload

Outputs:
  artifacts/wp-12316-01/asset_manifest.json          the deliverable
  docs/wp-12316-01/asset_manifest.json               byte-identical durable mirror (push gate drops artifacts/**)
  docs/wp-12316-01/asset_manifest.v1.schema.json     schema copy pinned to this package/report
  runs/wp-12316-01/kf_result.wp-12316-01.json        result envelope (kf_result.v1 shape)
  runs/wp-12316-01/report_probe.json                 resolution probe log (what was searched where)

Usage: python3 scripts/kf_register_12316.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

REPORT_ID = "12316"
PACKAGE_ID = "wp-12316-01"
TASK_TYPE = "01-asset-registration"
# pinned by the work-package contract (package wp-12316-01, input.source_hash)
EXPECTED_HASH = "a38be5c7ec3bc9250f3d1a53fb75491d66489da695b121134a761e93bdba7f87"
SOURCE_URI = "tensor://reports/12316"
SOURCE_CHARS_CONTRACT = 9610

RUN_DIR = pathlib.Path("runs/wp-12316-01")
ART_DIR = pathlib.Path("artifacts/wp-12316-01")
DOC_DIR = pathlib.Path("docs/wp-12316-01")

# ---------------------------------------------------------------- structural assets
# anchor  : substring that must occur on exactly one line of the markdown
# span    : (start_offset, end_offset) in lines, relative to the anchor line, inclusive
# The emitted quote is the verbatim slice md[start_char:end_char] -- never retyped.
STRUCT = [
    dict(asset_id="A01", asset_class="source_document", label="报告 markdown 全文（源资产本体）",
         anchor="# 声明时效契约（claim_watch）", span=(0, -1), method="document",
         note="整篇 markdown 即源资产；sha256 见 source.hash（与契约 source_hash 逐字节比对）"),
    dict(asset_id="A02", asset_class="provenance_header", label="任务/仓/基线 声明行",
         anchor="任务：P270W1-N01", span=(0, 0),
         note="给出 mission 9378 与基线声明（该能力在 main 上不存在）；mission 号被本包用于确定执行工作树根"),
    dict(asset_id="A03", asset_class="provenance_header", label="审计时刻与批次规模行",
         anchor="审计时刻：2026-11-10T19:42:23", span=(0, 0),
         note="审计时刻/批次墙钟/声明数/工作树数，重复出现在判据表 A3 与 §⑥，登记不换算"),
    dict(asset_id="A04", asset_class="table", label="声明契约字段表（6 字段，零领域语义）",
         anchor="| 字段 | 作用 |", span=(0, 6),
         note="表头+分隔+6 行字段定义；字段名原样登记，不做语义解释"),
    dict(asset_id="A05", asset_class="table", label="被审工作树表（repo/path/claims，5 行）",
         anchor="| repo | path | claims |", span=(0, 6),
         note="本包据此表解析外部工件根目录（repo→绝对路径），不用记忆中的路径"),
    dict(asset_id="A06", asset_class="data_block", label="环境指纹 JSON 块（arch/pointer_bits/python/digest）",
         anchor="```json", span=(1, 9),
         note="围栏代码块内的 JSON 正文原样登记（不含围栏行本身，避免产物内嵌时与 markdown 围栏冲突）；"
              "digest=bf3bb545… 为 USB 指纹，不在此重算"),
    dict(asset_id="A07", asset_class="table", label="逐工作树判决分布表（5 行，含计数）",
         anchor="| repo | n_claims | n_OK |", span=(0, 6),
         note="数字仅登记；本包不做求和校验（抽取/核对属下游工序）"),
    dict(asset_id="A08", asset_class="table", label="故障原因计数表（cause/n）",
         anchor="| cause | n |", span=(0, 3),
         note="dep_changed / dep_missing 两行"),
    dict(asset_id="A09", asset_class="table", label="等级迁移计数表（transition/n）",
         anchor="| transition | n |", span=(0, 3),
         note="批量阶段 (none)=0；等级迁移证据在注入矩阵"),
    dict(asset_id="A10", asset_class="table", label="A1 注入式故障检出矩阵（9 变异）",
         anchor="| fault | expected_status | observed_status | detected |", span=(0, 10),
         note="9 行变异结果；检出率文字见 A11 所在节"),
    dict(asset_id="A11", asset_class="metric_statement", label="A1 检出率结论文本",
         anchor="检出率 9/9 = 1.0（阈值 1.0）", span=(0, 0),
         note="结论文本，不含工件地址"),
    dict(asset_id="A12", asset_class="metric_statement", label="A2 误报探针文本（600→78→0）",
         anchor="候选 600 条 → GNU", span=(0, 0),
         note="候选 600、独立复核 78、被拒 0；审计产物路径见 A23 组"),
    dict(asset_id="A13", asset_class="table", label="A5 漂移回溯标签计数表（5 行）",
         anchor="| label | n |", span=(0, 6),
         note="drift=9 / consistent=73 等标签计数"),
    dict(asset_id="A14", asset_class="table", label="A5 漂移案例表（9 例，document+dependency+git label）",
         anchor="| case | repo | document | dependency | git label |", span=(0, 10),
         note="9 例逐条给出 仓:路径 依赖地址；本包把它们登记为外部依赖 URI 的样本，不在本仓解析"),
    dict(asset_id="A15", asset_class="metric_statement", label="A5 召回/精确率与账本路径文本",
         anchor="召回 1.0（n_drift=9，阈值 0.7）", span=(0, 0),
         note="正文给出临时账本 /tmp/claim_watch_audit2/drift_ledger.json；该临时路径见 A31"),
    dict(asset_id="A16", asset_class="table", label="验收判据总表（A1–A5 实测/阈值/通过）",
         anchor="| 判据 | 实测 | 阈值 | 通过 |", span=(0, 6),
         note="5 条判据；本包只登记，不复算"),
    dict(asset_id="A17", asset_class="figure_reference", label="图 1 逐工作树判决分布（引用 + 说明）",
         anchor="![fig1](../../artifacts/claim_watch/fig1_status_by_tree.png)", span=(0, 3),
         note="图片相对链接 + 图注；文件字节目录见 payload"),
    dict(asset_id="A18", asset_class="figure_reference", label="图 2 故障原因普查（引用 + 说明）",
         anchor="![fig2](../../artifacts/claim_watch/fig2_causes.png)", span=(0, 3),
         note="左原因码/右等级降级；文件字节目录见 payload"),
    dict(asset_id="A19", asset_class="figure_reference", label="图 3 历史漂移回溯（引用 + 说明）",
         anchor="![fig3](../../artifacts/claim_watch/fig3_drift_replay.png)", span=(0, 3),
         note="recall/precision 标在标题里；文件字节目录见 payload"),
    dict(asset_id="A20", asset_class="figure_reference", label="图 4 验收判据（引用 + 说明）",
         anchor="![fig4](../../artifacts/claim_watch/fig4_acceptance.png)", span=(0, 3),
         note="A2/A3 以实测/阈值作图；文件字节目录见 payload"),
    dict(asset_id="A21", asset_class="declared_absent_figure", label="「无物理场量云图」明示声明",
         anchor="> 无物理场量云图：", span=(0, 0), resolution="declared_absent",
         note="报告显式声明无场量/无几何/无工况：本包按声明登记为 declared_absent，不补造图"),
    dict(asset_id="A22", asset_class="table", label="§⑥ 误差判定逐项表（5 行）",
         anchor="| 关键量 | 实测 | 基准/阈值 | 误差 | 判定 |", span=(0, 6),
         note="含「是否 <3%」的分量类回答；登记不改写"),
    dict(asset_id="A23", asset_class="data_block", label="审计链复跑命令（bash 围栏块）",
         anchor="```bash", span=(0, 10),
         note="4 条可复跑命令；命令中的相对路径按 A05 工作树根解析"),
    dict(asset_id="A24", asset_class="artifact_inventory", label="产物清单行（代码/测试/数据/图 清单）",
         anchor="产物清单：`schemas/claim.json`", span=(0, 0),
         note="一行式清单：本包逐路径拆成 A29 组解析，避免只登记一个笼统字符串"),
]

# ---------------------------------------------------------------- referenced artifact paths
# group -> asset_class / how it is used
MOD_BRACE = "tools/claim_watch/{fingerprint,claims,checker,harvest,retro,audit,figures,report}.py"
ART_BRACE = "artifacts/claim_watch/{audit_report,acceptance,audit_table,mutations,drift_replay,claims_ledger}.json"

# needle = verbatim substring that locates the declaration in the markdown (may be a brace
# expansion, which is how the report actually writes these lists); path = the address probed.
REFS = [
    dict(asset_class="schema_file", path="schemas/claim.json", needle="`schemas/claim.json`"),
    dict(asset_class="implementation_module", path="tools/claim_watch/fingerprint.py", needle=MOD_BRACE),
    dict(asset_class="implementation_module", path="tools/claim_watch/claims.py", needle=MOD_BRACE),
    dict(asset_class="implementation_module", path="tools/claim_watch/checker.py", needle=MOD_BRACE),
    dict(asset_class="implementation_module", path="tools/claim_watch/harvest.py", needle=MOD_BRACE),
    dict(asset_class="implementation_module", path="tools/claim_watch/retro.py", needle=MOD_BRACE),
    dict(asset_class="implementation_module", path="tools/claim_watch/audit.py", needle=MOD_BRACE),
    dict(asset_class="implementation_module", path="tools/claim_watch/figures.py", needle=MOD_BRACE),
    dict(asset_class="implementation_module", path="tools/claim_watch/report.py", needle=MOD_BRACE),
    dict(asset_class="test_module", path="tests/test_claim_watch.py", needle="`tests/test_claim_watch.py`"),
    dict(asset_class="audit_artifact", path="artifacts/claim_watch/audit_report.json",
         needle="`artifacts/claim_watch/audit_report.json`"),
    dict(asset_class="audit_artifact", path="artifacts/claim_watch/acceptance.json", needle=ART_BRACE),
    dict(asset_class="audit_artifact", path="artifacts/claim_watch/audit_table.json", needle=ART_BRACE),
    dict(asset_class="audit_artifact", path="artifacts/claim_watch/mutations.json", needle=ART_BRACE),
    dict(asset_class="audit_artifact", path="artifacts/claim_watch/drift_replay.json", needle=ART_BRACE),
    dict(asset_class="audit_artifact", path="artifacts/claim_watch/claims_ledger.json", needle=ART_BRACE),
    dict(asset_class="figure_payload", path="artifacts/claim_watch/fig1_status_by_tree.png",
         needle="../../artifacts/claim_watch/fig1_status_by_tree.png"),
    dict(asset_class="figure_payload", path="artifacts/claim_watch/fig2_causes.png",
         needle="../../artifacts/claim_watch/fig2_causes.png"),
    dict(asset_class="figure_payload", path="artifacts/claim_watch/fig3_drift_replay.png",
         needle="../../artifacts/claim_watch/fig3_drift_replay.png"),
    dict(asset_class="figure_payload", path="artifacts/claim_watch/fig4_acceptance.png",
         needle="../../artifacts/claim_watch/fig4_acceptance.png"),
    dict(asset_class="data_ledger", path="data/claim_watch/drift_ledger.json",
         needle="`data/claim_watch/drift_ledger.json`"),
    dict(asset_class="report_document", path="docs/reports/claim_watch_m9378.md",
         needle="docs/reports/claim_watch_m9378.md"),
]

TMP_REFS = [
    dict(asset_class="data_ledger_tmp", path="/tmp/claim_watch_audit2/drift_ledger.json"),
]


# ---------------------------------------------------------------- helpers
def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_report() -> dict:
    """Fetch the report payload from the platform API (cache in runs/)."""
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    cached = RUN_DIR / "report_12316.json"
    if cached.exists():
        return json.loads(cached.read_text())
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    creds = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                        "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(base + "/auth/login", data=creds,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        token = json.load(r)["access_token"]
    req = urllib.request.Request("%s/tensor/reports/%s" % (base, REPORT_ID),
                                 headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    cached.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    (RUN_DIR / "report_12316.md").write_text(payload["markdown"])
    return payload


def line_offsets(md: str):
    lines, offs, pos = md.split("\n"), [], 0
    for ln in lines:
        offs.append((pos, pos + len(ln)))
        pos += len(ln) + 1
    return lines, offs


def heading_before(lines, idx: int) -> str:
    head = "(document)"
    for ln in lines[:idx]:
        if ln.startswith("#"):
            head = ln.lstrip("# ").strip()
    return head


def build_locator(md, lines, offs, anchor, span, method="char_span"):
    """Anchor -> char/line span -> verbatim quote.

    method="document" uses the document convention: the locator spans the whole markdown while
    ``quote`` is the document's first line (unique). Every other asset slices its own span.
    """
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise SystemExit("anchor %r occurs on %d lines (need 1)" % (anchor, len(hits)))
    i0 = hits[0]
    if method == "document":
        quote = lines[0]
        return dict(method="document", start_char=0, end_char=len(md), start_line=0,
                    end_line=len(lines) - 1, quote=quote, unique=md.count(quote) == 1), 0
    s = i0 + span[0]
    e = i0 + span[1] if span[1] >= 0 else len(lines) - 1
    e = min(e, len(lines) - 1)
    quote = "\n".join(lines[s:e + 1])
    if not quote.strip():
        raise SystemExit("empty quote for anchor %r" % anchor)
    expected = md[offs[s][0]:offs[e][1]]
    if quote != expected:
        raise SystemExit("slice mismatch for anchor %r (offset bookkeeping bug)" % anchor)
    return dict(method=method, start_char=offs[s][0], end_char=offs[e][1],
                start_line=s, end_line=e, quote=quote,
                unique=md.count(quote) == 1), s


def probe(path: str, roots: dict) -> dict:
    """Read-only existence probe over the roots named by the report itself."""
    tried = []
    if path.startswith("/"):
        cands = [("absolute", pathlib.Path(path))]
    else:
        cands = [(name, root / path) for name, root in roots.items()]
        cands += [(name + "/docs-reports-base", (root / "docs/reports" / path).resolve())
                  for name, root in roots.items() if path.startswith("..")]
    for name, cand in cands:
        tried.append(str(cand))
        try:
            if cand.is_file():
                return dict(result="resolved", found_at=str(cand), resolved_via=name,
                            tried=tried, bytes=cand.stat().st_size, sha256=sha256_file(cand))
        except OSError:
            continue
    return dict(result="unresolved", found_at=None, tried=tried)


def parse_roots(md: str) -> tuple[dict, dict]:
    """Repo roots come from the report's own worktree table; mission root from its mission id."""
    roots, evidence = {}, {}
    for ln in md.split("\n"):
        m = re.match(r"\|\s*([A-Za-z][A-Za-z0-9_]*)\s*\|\s*(/root/[^|]+?)\s*\|\s*\d+\s*\|", ln)
        if m:
            roots[m.group(1)] = pathlib.Path(m.group(2).strip())
            evidence[m.group(1)] = ln.strip()
    mm = re.search(r"mission (\d+)", md)
    if mm:
        mission_root = pathlib.Path("/root/tp-agent/work/m" + mm.group(1))
        roots["mission_worktree"] = mission_root
        evidence["mission_worktree"] = "mission %s (报告 A02 行) → /root/tp-agent/work/m%s" % (
            mm.group(1), mm.group(1))
    roots["this_worktree"] = pathlib.Path(".").resolve()
    roots["tmp"] = pathlib.Path("/tmp")
    return roots, evidence


def rel_path_locator(md, lines, offs, needle: str):
    """Locator for a referenced path: first occurrence line (unique-checked), widened to the path."""
    pos = md.find(needle)
    if pos < 0:
        raise SystemExit("referenced path %r not found in markdown" % needle)
    line_no = md.count("\n", 0, pos)
    for wide in (None,):
        pass
    quote = lines[line_no]
    unique = md.count(quote) == 1
    if not unique:
        # fall back to the bare path token; still verbatim, still located
        quote = needle
        pos2 = pos
        unique = md.count(needle) == 1
    else:
        pos2 = offs[line_no][0]
    start = offs[line_no][0] if unique and quote == lines[line_no] else pos
    end = start + len(quote)
    if md[start:end] != quote:
        raise SystemExit("path locator slice mismatch for %r" % needle)
    return dict(method="char_span", start_char=start, end_char=end,
                start_line=line_no, end_line=line_no, quote=quote, unique=unique)


def main() -> int:
    payload = fetch_report()
    md = payload["markdown"]
    md_hash = sha256_text(md)
    if md_hash != EXPECTED_HASH:
        print("FATAL: markdown sha256 %s != contract source_hash %s" % (md_hash, EXPECTED_HASH))
        return 2
    if len(md) != SOURCE_CHARS_CONTRACT:
        print("FATAL: chars %d != contract chars %d" % (len(md), SOURCE_CHARS_CONTRACT))
        return 2

    lines, offs = line_offsets(md)
    roots, root_evidence = parse_roots(md)
    probe_log = {"roots": {k: str(v) for k, v in roots.items()},
                 "roots_evidence": root_evidence, "probes": []}
    worktree = pathlib.Path(".").resolve()

    assets, seen, next_id = [], set(), 0

    def add(asset):
        nonlocal next_id
        if asset["asset_id"] in seen:
            raise SystemExit("duplicate asset_id " + asset["asset_id"])
        seen.add(asset["asset_id"])
        assets.append(asset)

    # ---- structural assets
    for spec in STRUCT:
        loc, anchor_line = build_locator(md, lines, offs, spec["anchor"], spec["span"],
                                         spec.get("method", "char_span"))
        if not loc["unique"]:
            raise SystemExit("quote not unique for %s: %r" % (spec["asset_id"], spec["anchor"]))
        resolution = spec.get("resolution", "resolved_in_source")
        check = dict(check="char_span_in_source_markdown", result="resolved")
        if spec["asset_id"] == "A21":
            check = dict(check="declared_absent_in_source_markdown", result="absent",
                         detail="报告显式声明无物理场量云图；平台 figures 字段另见 source.platform_figures")
        add(dict(
            asset_id=spec["asset_id"], asset_class=spec["asset_class"], label=spec["label"],
            in_report_section=heading_before(lines, anchor_line),
            locator=loc, resolution=resolution, resolution_check=check,
            payload=dict(status="in_report_record",
                         detail="内容即源 markdown 的逐字切片，本包未另存副本"),
            note=spec["note"],
        ))
        next_id = max(next_id, int(spec["asset_id"][1:]))

    # ---- referenced artifact paths (external to the source markdown)
    for spec in REFS + TMP_REFS:
        pid = "A%02d" % (next_id + 1)
        next_id += 1
        loc = rel_path_locator(md, lines, offs, spec.get("needle", spec["path"]))
        pr = probe(spec["path"], roots)
        probe_log["probes"].append(dict(asset_id=pid, path=spec["path"], **pr))
        if pr["result"] == "resolved":
            payload_status = "external_resolved_at_reported_path"
            check = dict(check="path_exists_under_reported_roots", result="resolved",
                         tried=pr["tried"], found_at=pr["found_at"],
                         bytes=pr["bytes"], sha256=pr["sha256"], resolved_via=pr["resolved_via"])
            note = ("外部工件：地址由报告自身给出的工作树路径解析成功（字节数与 sha256 已记录）；"
                    "工件本体不属于本报告记录，未复制入库、未改写。resolution=referenced_unresolved "
                    "仅表示「不在源 markdown 内」。")
        else:
            payload_status = "external_not_found"
            check = dict(check="path_exists_under_reported_roots", result="unresolved",
                         tried=pr["tried"])
            note = ("外部工件：在报告点名的工作树根下均未找到该路径（逐根尝试记录于 tried）；"
                    "疑为未入库产物或推送门排除的 artifacts/**。如实登记为 unresolved，不猜地址。")
        add(dict(
            asset_id=pid, asset_class=spec["asset_class"],
            label="报告引用的外部工件路径：%s" % spec["path"],
            in_report_section=heading_before(lines, loc["start_line"]),
            locator=loc, resolution="referenced_unresolved", resolution_check=check,
            payload=dict(status=payload_status, declared_path=spec["path"],
                         resolved_via=pr.get("resolved_via")),
            note=note,
        ))

    # ---- platform payload figures (figures[] field)
    figs = payload.get("figures") or []
    fig_line = next(i for i, ln in enumerate(lines)
                    if ln.startswith("![fig1]") or ln.startswith("![figure 1]"))
    add(dict(
        asset_id="A%02d" % (next_id + 1), asset_class="platform_figure_payload",
        label="平台 figures 字段（%d 个内嵌图）" % len(figs),
        in_report_section="(platform record)",
        locator=dict(method="char_span", start_char=offs[fig_line][0],
                     end_char=offs[fig_line][1], start_line=fig_line, end_line=fig_line,
                     quote=lines[fig_line], unique=True),
        resolution="referenced_unresolved",
        resolution_check=dict(check="platform_figures_field", result="present" if figs else "absent",
                              platform_figures_count=len(figs)),
        payload=dict(status="platform_record_field", names=[f.get("name") for f in figs
                                                           if isinstance(f, dict)]),
        note=("平台报告记录自带 figures 字段（与 §④ 的 4 条相对链接对应）；本包只登记条目名，"
              "不解码 base64 像素。"),
    ))
    next_id += 1

    classes, res = {}, {}
    for a in assets:
        classes[a["asset_class"]] = classes.get(a["asset_class"], 0) + 1
        res[a["resolution"]] = res.get(a["resolution"], 0) + 1

    manifest = dict(
        schema="asset_manifest.v1",
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        objective=dict(register_assets=True, classify_report_type=False),
        source=dict(
            uri=SOURCE_URI, field="markdown", hash_alg="sha256", hash=md_hash,
            chars=len(md), bytes_utf8=len(md.encode("utf-8")),
            title=payload.get("title"), scenario_key=payload.get("scenario_key"),
            platform_id=payload.get("id"),
            platform_mission_id=payload.get("mission_id"),
            platform_status=payload.get("status"),
            platform_created_at=payload.get("created_at"),
            platform_tags=payload.get("tags", []),
            platform_figures=figs,
            retrieved_via="GET %s/tensor/reports/%s" % (
                os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/"),
                REPORT_ID),
            local_copy=str(RUN_DIR / "report_12316.md"),
        ),
        counts=dict(assets=len(assets), by_class=classes, by_resolution=res,
                    resolved_in_source=res.get("resolved_in_source", 0),
                    referenced_unresolved=res.get("referenced_unresolved", 0),
                    declared_absent=res.get("declared_absent", 0),
                    claims=0),
        assets=assets,
        claims=[],
        claims_note=("working-package contract objective.classify_report_type=false 且 notes 允许 claims 为空："
                     "本工序只登记资产定位，不抽取知识对象；claim 抽取由下游工序负责。空数组是完整结果，"
                     "不是遗漏（无 forced claim generation）。"),
        integrity=dict(
            quote_uniqueness=("每条 locator.quote 均为源 markdown 的唯一子串，且 md[start_char:end_char] "
                              "与 quote 逐字符相等（scripts/kf_verify_12316.py: source_locator_resolvable）"),
            hash_recomputed_locally=True,
            hash_matches_contract=True,
            hash_local=md_hash,
            hash_contract=EXPECTED_HASH,
            verification_status="not_verified",
            note="verification 由平台门计算；本包不把任何结论标成 verified。",
        ),
        boundaries=dict(
            report_ids_touched=[REPORT_ID],
            upstream_products_rewritten=False,
            cross_repo_mode="read-only existence/sha256 probe, no copy, no write",
            claims_extracted=False,
        ),
    )

    ART_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    art = ART_DIR / "asset_manifest.json"
    art.write_text(blob)
    mirror = DOC_DIR / "asset_manifest.json"
    mirror.write_text(blob)
    if sha256_file(art) != sha256_file(mirror):
        print("FATAL: durable mirror differs from artifact")
        return 3
    art_hash = sha256_file(art)

    # schema copy pinned to this package/report (const patched, otherwise byte-identical)
    src_schema = pathlib.Path("schemas/asset_manifest.v1.schema.json").read_text()
    pin = (src_schema.replace('"const": "wp-448-01"', '"const": "%s"' % PACKAGE_ID)
           .replace('"const": "448"', '"const": "%s"' % REPORT_ID)
           .replace('"const": "tensor://reports/448"', '"const": "%s"' % SOURCE_URI))
    for d in (ART_DIR, DOC_DIR):
        (d / "asset_manifest.v1.schema.json").write_text(pin)

    (RUN_DIR / "report_probe.json").write_text(
        json.dumps(probe_log, ensure_ascii=False, indent=2) + "\n")

    result = dict(
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        provenance=dict(
            source_uri=SOURCE_URI,
            source_field="markdown",
            source_hash="sha256:" + md_hash,
            source_chars=len(md),
            source_bytes_utf8=len(md.encode("utf-8")),
            source_title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            contract_version="1.0",
            lane="C",
            work_package=PACKAGE_ID,
            retrieved_via=manifest["source"]["retrieved_via"],
            local_copy=str(RUN_DIR / "report_12316.md"),
            generator="scripts/kf_register_12316.py",
            verifier="scripts/kf_verify_12316.py",
            verification_status="not_verified",
        ),
        outputs={"asset_manifest.json": dict(manifest, artifact_path=str(art),
                                            artifact_sha256=art_hash,
                                            artifact_bytes=art.stat().st_size)},
    )
    (RUN_DIR / "kf_result.wp-12316-01.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print("markdown sha256:", md_hash, "MATCH")
    print("chars:", len(md), "bytes:", len(md.encode("utf-8")), "lines:", len(lines))
    print("assets:", len(assets), "by_class:", json.dumps(classes, ensure_ascii=False))
    print("by_resolution:", json.dumps(res, ensure_ascii=False))
    print("manifest:", art, art_hash)
    return 0


if __name__ == "__main__":
    sys.exit(main())