"""KF work package wp-12025-01 — task_type=01-asset-registration, report_id=12025.

Scope (per contract): register the *source asset* of report 12025 — confirm its identity and the
byte hash of its markdown, and enumerate the attachments/artifacts that can (or cannot) be resolved
from that markdown. No extraction, no classification, no claim generation, nothing marked verified.

Zero-transcription discipline: every quote in the emitted locator is *sliced out of the fetched
markdown* by character offsets; nothing is retyped from memory. The fetch happens in this process
(token→GET /tensor/reports/12025) and the recomputed sha256 must equal the contract source_hash,
otherwise the script aborts before writing anything.

Outputs:
  runs/wp-12025-01/report_12025.md    (markdown payload, byte-identical to the platform field)
  runs/wp-12025-01/report_12025.json  (raw API payload: id/title/scenario_key/figures/...)
  artifacts/wp-12025-01/asset_manifest.json
  docs/wp-12025-01/asset_manifest.json        (durable mirror, byte-identical; artifacts/ is dropped
                                               by the mission-push gate, docs/ is not)
  runs/wp-12025-01/kf_result.wp-12025-01.json (result envelope, kf_result.v1 shape)

Usage: python3 scripts/kf_register_12025.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

REPORT_ID = "12025"
PACKAGE_ID = "wp-12025-01"
TASK_TYPE = "01-asset-registration"
EXPECTED_HASH = "6ebcceb70d4aa23bd429e13496cfa2ac2fc933c83461eef0a0c58a29321df0ed"
SOURCE_URI = "tensor://reports/12025"
TITLE = "DEM多面体颗粒接触与休止角验证"
SCENARIO_KEY = "AG29W1-N06"

RUN_DIR = pathlib.Path("runs/wp-12025-01")
ART_DIR = pathlib.Path("artifacts/wp-12025-01")
DOC_DIR = pathlib.Path("docs/wp-12025-01")
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

# Anchor table. `anchor` = the single markdown line containing the asset; `span` = inclusive line
# offsets relative to that anchor; `sub` (optional) = exact sub-string of the anchor line (the quote is the slice at its offset),
# which is how sub-line assets are pinned without retyping text. resolution:
#   resolved_in_source   = an artifact that exists inside the markdown itself
#   referenced_unresolved= an artifact named by the report whose payload is not resolvable from it
#   declared_absent      = artifact class with no payload in the report
# (see manifest note: `declared_absent` here is *observed absent* unless the report says so itself)
ASSETS = [
    dict(asset_id="A01", asset_class="document", label="报告正文（markdown 全文，432 字符）",
         anchor="--doc--", span=(0, -1), resolution="resolved_in_source",
         note="整篇 markdown 即源资产；sha256 见 source.hash，与契约 source_hash 逐字节相同"),
    dict(asset_id="A02", asset_class="heading", label="报告标题行（英文标题）",
         anchor="# Polyhedral Particle Contact & Repose Angle Validation", span=(0, 0),
         resolution="resolved_in_source",
         note="与 API title 字段（中文）不同语言，二者互不覆盖：title 取自 record，标题行取自 markdown"),
    dict(asset_id="A03", asset_class="abstract", label="范围声明段（实现了什么）",
         anchor="Implemented GJK/EPA contact detection", span=(0, 0),
         resolution="resolved_in_source",
         note="单段范围声明；不含数值结果，仅声明实现与验证对象"),
    dict(asset_id="A04", asset_class="deliverables_list", label="交付物清单（标题+3 条）",
         anchor="## Deliverables", span=(0, 3), resolution="resolved_in_source",
         note="清单本身在页内；三条指向的实体分别登记为 A05/A06/A07"),
    dict(asset_id="A05", asset_class="code_artifact", label="polyhedra_repose.py（450 行）",
         anchor="- polyhedra_repose.py (450 lines)", span=(0, 0),
         sub="polyhedra_repose.py (450 lines)", resolution="referenced_unresolved",
         note="报告只给文件名与行数，无仓库相对路径/URL/commit，无 sha256；代码本体不可由本报告解析"),
    dict(asset_id="A06", asset_class="test_evidence_statement", label="测试计数声明（42 tests，14 new + 28 existing）",
         anchor="- 42 tests passing (14 new + 28 existing)", span=(0, 0),
         sub="42 tests passing (14 new + 28 existing)", resolution="resolved_in_source",
         note="声明文本在页内可逐字定位；支撑该计数的测试套件与运行日志未在报告中给出（见 A05/A12），"
              "故此处只登记声明，不把计数当作已复核事实"),
    dict(asset_id="A07", asset_class="report_document_ref", label="上游验证报告 docs/polyhedra_repose_angle_validation.md",
         anchor="- Report: docs/polyhedra_repose_angle_validation.md", span=(0, 0),
         sub="docs/polyhedra_repose_angle_validation.md", resolution="referenced_unresolved",
         note="仓库相对路径；本工作树（TensorKnowledge）内不存在，属外部仓库（TensorDEM）产物，本报告未附内容"),
    dict(asset_id="A08", asset_class="verification_checklist", label="验证条目 C2/C5（两条带 ✓ 的自检项）",
         anchor="## Verification", span=(0, 2), resolution="resolved_in_source",
         note="仅两条“通过”标记，无实测值/基准值/样本量；C2 的 <5% 为判据阈值而非测量结果"),
    dict(asset_id="A09", asset_class="solver_context", label="所属求解器 TensorDEM（仓名）",
         anchor="in TensorDEM.", span=(0, 0), sub="TensorDEM", resolution="referenced_unresolved",
         note="仅出现仓名，无提交号/版本/分支；TensorDEM 检出不在本工作树内，无法解析到具体代码状态"),
    dict(asset_id="A10", asset_class="figure_assets", label="图件（场量云图/对比曲线）",
         anchor="--doc--", span=(0, -1), resolution="declared_absent",
         note="观测式登记：markdown 无任何图片引用，API figures 字段为空数组；报告自身未写“无图”声明，"
              "故这是 observed-absent 而非 author-declared-absent"),
    dict(asset_id="A11", asset_class="quantitative_result_table", label="定量结果表（参数表/误差表）",
         anchor="--doc--", span=(0, -1), resolution="declared_absent",
         note="观测式登记：全文无 markdown 表格、无实测数值与基准数值对照；仅 A08 的两条判据阈值"),
    dict(asset_id="A12", asset_class="reproduction_record", label="复现记录（commit / 运行命令 / 运行 ID / 种子）",
         anchor="--doc--", span=(0, -1), resolution="declared_absent",
         note="观测式登记：全文无 git commit、无命令行、无 run id、无随机种子——450 行代码与 42 个测试均无可复现句柄"),
]


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def line_offsets(md: str):
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def build_locator(md: str, lines, offs, spec):
    anchor, span = spec["anchor"], spec["span"]
    if anchor == "--doc--":
        return dict(method="document", start_char=0, end_char=len(md),
                    start_line=0, end_line=len(lines) - 1,
                    quote=md, unique=True)
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise SystemExit(f"anchor not unique/found ({len(hits)} hits): {anchor!r}")
    a = hits[0]
    i0, i1 = a + span[0], a + span[1]
    i1 = len(lines) - 1 if i1 < 0 else i1
    start = offs[i0]
    end = offs[i1] + len(lines[i1])
    if spec.get("sub"):
        sub = spec["sub"]
        if lines[a].count(sub) != 1:
            raise SystemExit(f"sub-string not unique in anchor line: {sub!r}")
        c0 = lines[a].index(sub)
        start = offs[i0] + c0
        end = offs[i0] + c0 + len(sub)
    quote = md[start:end]
    uniq = md.count(quote) == 1
    return dict(method="char_span", start_char=start, end_char=end,
                start_line=i0, end_line=i0 if spec.get("sub") else i1,
                quote=quote, unique=uniq)


def section_of(lines, idx: int) -> str:
    head = ""
    for ln in lines[: idx + 1]:
        if ln.startswith("#"):
            head = ln.strip()
    return head or "(document)"


def worktree_search(worktree: pathlib.Path, name: str, limit: int = 20000):
    """Look for a file name anywhere inside the worktree (no network, no guessing)."""
    hits = []
    for p in worktree.rglob(name):
        if ".git" in p.parts:
            continue
        hits.append(str(p.relative_to(worktree)))
        if len(hits) >= limit:
            break
    return hits


def resolution_check(spec, loc, worktree: pathlib.Path, payload: dict):
    """Machine check backing the declared resolution status (no invented results)."""
    aid = spec["asset_id"]
    if aid == "A05":
        found = re.findall(r"(https?://\S+|doi:\S+|10\.\d{4,}/\S+)", loc["quote"])
        in_tree = worktree_search(worktree, "polyhedra_repose.py")
        return dict(check="address_extraction+worktree_file_search",
                    addresses_found=found, worktree_matches=in_tree,
                    result="resolved" if (found or in_tree) else "unresolved",
                    detail="仅在报告文本内检索 URL/DOI，并在工作树内按文件名搜索；不联网猜测地址")
    if aid == "A07":
        rel = loc["quote"]
        exists = (worktree / rel).exists()
        return dict(check="worktree_path_exists", paths=[rel], missing=[] if exists else [rel],
                    result="resolved" if exists else "unresolved")
    if aid == "A09":
        cands = [p for p in ("TensorDEM", "tensor_dem", "TensorDem") if (worktree / p).exists()]
        return dict(check="worktree_checkout_search", candidates=["TensorDEM", "tensor_dem", "TensorDem"],
                    found=cands, result="resolved" if cands else "unresolved",
                    detail="本工作树内无 TensorDEM 检出；报告亦无 commit/版本可解析")
    if aid == "A06" or aid == "A08":
        return dict(check="char_span_in_source_markdown", result="resolved",
                    detail="文本可逐字定位；其数值支撑（测试套件/实测值）不在报告内，故不判为已复核")
    if aid == "A10":
        figs = payload.get("figures") or []
        img_syntax = re.findall(r"!\[[^\]]*\]\([^)]*\)|<img\b", loc["quote"])
        return dict(check="markdown_image_syntax+platform_figures_field",
                    image_syntax_hits=img_syntax, platform_figures_count=len(figs),
                    result="present" if (figs or img_syntax) else "absent",
                    detail="observed-absent：作者未作无图声明，此处只登记观测结果")
    if aid == "A11":
        rows = [ln for ln in loc["quote"].split("\n") if ln.strip().startswith("|")]
        nums = re.findall(r"\d+\.\d+|\d+e[-+]?\d+", loc["quote"])
        return dict(check="markdown_table_and_numeric_literal_scan",
                    table_rows=rows, numeric_literals=nums,
                    result="present" if rows else "absent",
                    detail="observed-absent：无表格行；numeric_literals 仅含行数/测试计数/阈值，非实测结果值")
    if aid == "A12":
        pats = {"git_commit": r"\b[0-9a-f]{7,40}\b", "command": r"\b(python3?|pytest|mpirun|make)\b",
                "run_id": r"\brun[-_ ]?id\b", "seed": r"\bseed\b"}
        found = {k: re.findall(v, loc["quote"], flags=re.I) for k, v in pats.items()}
        return dict(check="reproduction_handle_scan", found=found,
                    result="absent" if not any(found.values()) else "present",
                    detail="observed-absent：无 commit/命令/run id/seed 任一可复现句柄")
    return dict(check="char_span_in_source_markdown", result="resolved")


def fetch_payload():
    """Fresh fetch in this process: GET /tensor/reports/12025 with a just-minted token."""
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    tok = None
    if u and p:
        req = urllib.request.Request(BASE + "/auth/login",
                                     data=json.dumps({"username": u, "password": p}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())
        tok = d.get("access_token") or d.get("token")
    req = urllib.request.Request(BASE + "/tensor/reports/" + REPORT_ID,
                                 headers={"Authorization": "Bearer " + tok} if tok else {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    payload = fetch_payload()
    md = payload["markdown"]
    (RUN_DIR / "report_12025.md").write_text(md)
    (RUN_DIR / "report_12025.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    md_hash = sha256_text(md)
    if md_hash != EXPECTED_HASH:
        print(f"FATAL: markdown sha256 {md_hash} != contract source_hash {EXPECTED_HASH}")
        return 2

    lines, offs = line_offsets(md)
    worktree = pathlib.Path(".").resolve()

    assets, seen = [], set()
    for spec in ASSETS:
        if spec["asset_id"] in seen:
            raise SystemExit(f"duplicate asset_id {spec['asset_id']}")
        seen.add(spec["asset_id"])
        loc = build_locator(md, lines, offs, spec)
        if not loc["unique"]:
            raise SystemExit(f"quote not unique for {spec['asset_id']}: {spec['anchor']!r}")
        assets.append(dict(
            asset_id=spec["asset_id"],
            asset_class=spec["asset_class"],
            label=spec["label"],
            in_report_section=("(document)" if loc["method"] == "document"
                               else section_of(lines, loc["start_line"])),
            resolution=spec["resolution"],
            resolution_check=resolution_check(spec, loc, worktree, payload),
            locator=loc,
            note=spec["note"],
        ))

    classes, res = {}, {}
    for a in assets:
        classes[a["asset_class"]] = classes.get(a["asset_class"], 0) + 1
        res[a["resolution"]] = res.get(a["resolution"], 0) + 1

    manifest = dict(
        schema="asset_manifest.v1",
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        source=dict(
            uri=SOURCE_URI,
            field="markdown",
            hash_alg="sha256",
            hash=md_hash,
            chars=len(md),
            bytes_utf8=len(md.encode()),
            title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            platform_id=payload.get("id"),
            platform_mission_id=payload.get("mission_id"),
            platform_stage=payload.get("stage"),
            platform_status=payload.get("status"),
            platform_figures=payload.get("figures") or [],
            platform_tags=payload.get("tags") or [],
            retrieved_via=f"GET {BASE}/tensor/reports/{REPORT_ID}",
            local_copy=str(RUN_DIR / "report_12025.md"),
        ),
        counts=dict(assets=len(assets), by_class=classes, by_resolution=res,
                    resolved_in_source=res.get("resolved_in_source", 0),
                    referenced_unresolved=res.get("referenced_unresolved", 0),
                    declared_absent=res.get("declared_absent", 0)),
        assets=assets,
        claims=[],
        claims_note=("按工作包契约 objective.classify_report_type=false 且 notes 允许 claims 为空数组："
                     "本工序只登记资产定位，不做 claim 抽取；claim 抽取由下游工作包负责。"
                     "空数组使 acceptance 项 all_claims_have_evidence_or_explicit_unresolved_status 空真通过。"),
        observed_absent_note=("resolution=declared_absent 的三条（A10/A11/A12）是观测式登记："
                              "报告全文未作“无图/无表/无复现记录”的声明，缺失是由扫描判定，不是作者自述。"),
        integrity=dict(
            quote_uniqueness="每条 locator.quote 均为源 markdown 的唯一子串（本脚本断言，"
                             "scripts/kf_verify_12025.py 独立重算复核）",
            hash_recomputed_locally=True, hash_matches_contract=True),
    )

    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    art = ART_DIR / "asset_manifest.json"
    art.write_text(blob)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    mirror = DOC_DIR / "asset_manifest.json"
    mirror.write_text(blob)
    art_hash = hashlib.sha256(art.read_bytes()).hexdigest()
    if hashlib.sha256(mirror.read_bytes()).hexdigest() != art_hash:
        print("FATAL: durable mirror differs from artifact")
        return 3

    # outputs[<declared file name>] is the file content itself (the manifest object verbatim), so the
    # envelope stays hand-inspectable and the platform can schema-check the payload independently.

    result = dict(
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        provenance=dict(
            source_uri=SOURCE_URI,
            source_field="markdown",
            source_hash="sha256:" + md_hash,
            source_chars=len(md),
            source_bytes_utf8=len(md.encode()),
            source_title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            contract_version="1.0",
            lane="C",
            work_package=PACKAGE_ID,
            retrieved_via=f"GET {BASE}/tensor/reports/{REPORT_ID}",
            local_copy=str(RUN_DIR / "report_12025.md"),
            artifact_path=str(art),
            artifact_sha256=art_hash,
            artifact_bytes=art.stat().st_size,
            durable_mirror=str(mirror),
            generator="scripts/kf_register_12025.py",
            verifier="scripts/kf_verify_12025.py",
            verification_status="not_verified",  # gate computes verification; this producer does not
        ),
        outputs={"asset_manifest.json": manifest},
    )

    res_path = RUN_DIR / f"kf_result.{PACKAGE_ID}.json"
    res_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (RUN_DIR / f"kf_result_block.{PACKAGE_ID}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print("markdown sha256:", md_hash, "MATCH")
    print("assets:", len(assets), "by_class:", json.dumps(classes, ensure_ascii=False))
    print("by_resolution:", json.dumps(res, ensure_ascii=False))
    print("manifest:", art, art_hash)
    print("result:", res_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())