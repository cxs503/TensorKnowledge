"""Work package wp-13278-01 (task_type=01-asset-registration) — asset registration for report 13278.

Scope (hard boundary): this script touches report_id=13278 only. It does NOT extract claims, does NOT
classify the report, and does NOT mark anything as verified (verification is computed by the platform
gate; the local verifier scripts/kf_verify_wp13278.py only replays the acceptance list).

Zero hand-copy discipline: every quote emitted into the manifest is sliced out of the markdown that was
fetched in this process from GET /tensor/reports/13278, and the byte hash of that markdown is recomputed
here and compared with the contract source_hash before anything is written.

Inputs (fetched, not remembered):
  runs/wp-13278-01/report_13278.md    (markdown payload)
  runs/wp-13278-01/report_13278.json  (raw API payload: id/title/scenario_key/figures/...)

Outputs:
  artifacts/wp-13278-01/asset_manifest.json
  docs/wp-13278-01/asset_manifest.json        (byte-identical durable mirror; artifacts/ is dropped
                                               by the mission-push gate, docs/ is what gets committed)
  runs/wp-13278-01/kf_result.wp-13278-01.json (result envelope, kf_result.v1 shape)
  runs/wp-13278-01/kf_result_block.wp-13278-01.json (same bytes, for the single ```json block)

Usage: python3 scripts/kf_register_wp13278.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

REPORT_ID = "13278"
PACKAGE_ID = "wp-13278-01"
TASK_TYPE = "01-asset-registration"
EXPECTED_HASH = "f9c336f0d77c618b2a03ff4dd4fbc7d04b0d78a16bb29406537cfac742dcc90f"
SOURCE_URI = "tensor://reports/13278"
CONTRACT_TITLE = "TensorBEM bem_finite_depth 验证算例缺失图件补全"
SCENARIO_KEY = "bem_finite_depth_verification"
CONTRACT_CHARS = 1592

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
RUN_DIR = pathlib.Path("runs/wp-13278-01")
ART_DIR = pathlib.Path("artifacts/wp-13278-01")
DOC_DIR = pathlib.Path("docs/wp-13278-01")

# Probe roots: the report refers to a *different* repository (TensorBEM). This worktree is
# TensorKnowledge, so those file assets can never resolve here; we probe the producing worktree
# read-only, purely to record whether the referenced bodies exist somewhere on this host.
PROBE_ROOT = pathlib.Path("/root/tp-agent/work/m13784")
PROBE_PATHS = {
    "test": "tests/test_bem_finite_depth_anchors.py",
    "generator": "src/tensorbem/benchmarks/bem_finite_depth_anchors.py",
    "data": "benchmarks/verified/bem_finite_depth/result.json",
    "figures_dir": "benchmarks/verified/bem_finite_depth/figures",
}

# Anchor table. `span` = inclusive line range in the source markdown (0-based); the emitted quote is
# md[start_char:end_char] i.e. verbatim. `resolution` refers to the asset *body*, not to the quote:
#   resolved_in_source   - the body IS the quoted text (source material itself)
#   referenced_unresolved- the report only names an external body; no address/hash resolvable from it
ASSETS = [
    dict(asset_id="A01", asset_class="document", label="报告正文（markdown 全文，1592 字符）",
         span=(0, -1), resolution="resolved_in_source", method="document",
         note="整篇 markdown 即源资产本体；sha256 由 provenance/contract 双端复核一致"),
    dict(asset_id="A02", asset_class="heading", label="报告标题（markdown H1）",
         span=(0, 0), resolution="resolved_in_source", method="char_span",
         note="H1 与平台 title 字段措辞不同（title 为受控短名），此处二者都登记但不互相覆盖"),
    dict(asset_id="A03", asset_class="metadata_block", label="任务/分支/日期/仓/归仓理由 声明",
         span=(2, 4), resolution="resolved_in_source", method="char_span",
         note="上游任务号 m13784、分支 agent/m13784、仓 TensorBEM 的唯一来源"),
    dict(asset_id="A04", asset_class="edit_whitelist", label="EDIT_WHITELIST 声明（仅 figures/ 目录）",
         span=(6, 6), resolution="resolved_in_source", method="char_span",
         note="写入边界的自证：本单只允许改该目录，与「未修改求解器代码」的自述互相印证"),
    dict(asset_id="A05", asset_class="section", label="§1 问题陈述",
         span=(10, 15), resolution="resolved_in_source", method="char_span",
         note="失败断言+目录缺失+历史 CI 记录的整段上下文"),
    dict(asset_id="A06", asset_class="external_file_ref", label="失败测试文件 tests/test_bem_finite_depth_anchors.py::test_case_artifacts_and_documentation_exist",
         span=(12, 12), resolution="referenced_unresolved", method="char_span", probe="test",
         note="报告只给仓库相对路径，无 URL/commit 锚；本工作树（TensorKnowledge）内不存在该文件"),
    dict(asset_id="A07", asset_class="external_dir_ref", label="被断言存在的图件目录 benchmarks/verified/bem_finite_depth/figures/（≥4 张 PNG）",
         span=(13, 13), resolution="referenced_unresolved", method="char_span", probe="figures_dir",
         note="目录本体不在报告内；「≥4 张」为断言阈值，不是实测计数"),
    dict(asset_id="A08", asset_class="ci_evidence_ref", label="历史 CI 记录 PR#306(m8788) / PR#312(m8799)",
         span=(14, 15), resolution="referenced_unresolved", method="char_span",
         note="无 PR URL / run id / 日志工件地址，报告侧不可解析；只能作为下游复核的检索线索"),
    dict(asset_id="A09", asset_class="external_code_ref", label="图件生成模块 src/tensorbem/benchmarks/bem_finite_depth_anchors.py 的 make_figures()",
         span=(17, 17), resolution="referenced_unresolved", method="char_span", probe="generator",
         note="生成逻辑本体不在报告内；报告只声明存在该函数与其产物"),
]
# second half of the anchor table (split only for readability)
ASSETS += [
    dict(asset_id="A10", asset_class="figure_declaration", label="4 张图件的名称-内容声明",
         span=(18, 21), resolution="resolved_in_source", method="char_span",
         note="四条声明的原文；图件二进制本体登记为 A13（未解析）"),
    dict(asset_id="A11", asset_class="repro_command", label="复跑命令（§2 bash 块）",
         span=(23, 29), resolution="resolved_in_source", method="char_span",
         note="含 `--stage merge` 关键参数；命令未在本工序执行（属 TensorBEM 仓，越界）"),
    dict(asset_id="A12", asset_class="execution_log", label="生成输出日志（4 行 figure -> 路径）",
         span=(31, 37), resolution="resolved_in_source", method="char_span",
         note="上游粘贴的控制台输出；本工序仅登记不复跑，不视作已复现证据"),
    dict(asset_id="A13", asset_class="figure_binary", label="4 个 PNG 图件本体（fig_energy_identities / fig_kramers_kronig / fig_deep_water_limit / fig_section_matrix）",
         span=(33, 33), resolution="referenced_unresolved", method="char_span", probe="figures_dir",
         note="报告未内嵌任何图件（平台 figures 字段为空数组），也未给 sha256；仅 A12 日志给出相对路径。"
              "同目录另 3 条路径见 A12 第 34-36 行"),
    dict(asset_id="A14", asset_class="test_evidence", label="§3 验证块（pytest 命令 + 17 passed 汇总行）",
         span=(39, 44), resolution="resolved_in_source", method="char_span",
         note="上游粘贴的测试摘要；无 junit/日志工件，逐条用例结果不可核 —— 只登记不回填"),
    dict(asset_id="A15", asset_class="statement", label="全通过断言（17 条，唯一历史失败项已修复）",
         span=(46, 46), resolution="resolved_in_source", method="char_span",
         note="属上游自述结论，登记为陈述而非已验证事实（verification 由平台门计算）"),
    dict(asset_id="A16", asset_class="limitation_set", label="§4 局限（2 条）",
         span=(48, 51), resolution="resolved_in_source", method="char_span",
         note="含「仅补工件、未改求解器/测试」与「依赖 result.json 已有数据」两条边界"),
]


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def login() -> str | None:
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (u and p):
        return None
    for path in ("/auth/login", "/auth/token", "/tensor/auth/login"):
        req = urllib.request.Request(
            BASE + path, data=json.dumps({"username": u, "password": p}).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read().decode())
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def fetch_report() -> dict:
    tok = login()
    req = urllib.request.Request(BASE + "/tensor/reports/" + REPORT_ID,
                                 headers={"Authorization": "Bearer " + tok} if tok else {})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    if isinstance(d.get("data"), dict):
        d = d["data"]
    return d


def line_offsets(md: str) -> tuple[list[str], list[int]]:
    lines = md.split("\n")
    offs, acc = [], 0
    for ln in lines:
        offs.append(acc)
        acc += len(ln) + 1
    return lines, offs


def heading_for(lines: list[str], start_line: int) -> str:
    head = ""
    for ln in lines[: max(start_line, 0) + 1]:
        if ln.startswith("#"):
            head = ln.strip()
    return head or "(document)"


def build_locator(md: str, lines: list[str], offs: list[int], spec: dict) -> dict:
    if spec.get("method") == "document":
        return dict(method="document", start_char=0, end_char=len(md), start_line=0,
                    end_line=len(lines) - 1, quote=md, unique=md.count(md) == 1)
    s, e = spec["span"]
    if e == -1:
        e = len(lines) - 1
    start = offs[s]
    end = offs[e] + len(lines[e])
    quote = md[start:end]
    return dict(method="char_span", start_char=start, end_char=end, start_line=s, end_line=e,
                quote=quote, unique=md.count(quote) == 1)


def probe(kind: str) -> dict:
    rel = PROBE_PATHS[kind]
    hit = PROBE_ROOT / rel
    return dict(exists_on_host=hit.exists(), probe_path=str(hit),
                note="只读存在性探测（不联网、不改外部树）；命中不代表报告已给出可解析地址")


def resolution_check(spec: dict, loc: dict, payload: dict) -> dict:
    if spec["resolution"] == "resolved_in_source":
        return dict(check="char_span_in_source_markdown", result="resolved",
                    quote_len=len(loc["quote"]),
                    detail="引文为源 markdown 的逐字切片，且 md.count(quote)==1")
    if spec["resolution"] == "referenced_unresolved":
        d = dict(check="external_body_not_carried_by_report", result="unresolved",
                 detail="报告只给出相对路径/编号，无 URL/DOI/commit/内容哈希；本工作树内不可解析")
        if "probe" in spec:
            d["probe"] = probe(spec["probe"])
        if spec["asset_id"] == "A13":
            figs = payload.get("figures") or []
            d["platform_figures_count"] = len(figs)
            d["detail"] = ("平台 figures 字段为空数组（%d 条），报告未内嵌图件；"
                           "仅有 A12 日志中的仓库相对路径" % len(figs))
        return d
    return dict(check="declared_absent", result="absent")


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    payload = fetch_report()
    md = payload.get("markdown", "")
    (RUN_DIR / "report_13278.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    (RUN_DIR / "report_13278.md").write_text(md)

    md_hash = sha256_text(md)
    if md_hash != EXPECTED_HASH:
        print("FATAL: markdown sha256 %s != contract source_hash %s" % (md_hash, EXPECTED_HASH))
        return 2
    if len(md) != CONTRACT_CHARS:
        print("FATAL: chars %d != contract chars %d" % (len(md), CONTRACT_CHARS))
        return 2
    if (payload.get("title") or "") != CONTRACT_TITLE:
        print("WARN: platform title %r != contract title %r" % (payload.get("title"), CONTRACT_TITLE))

    lines, offs = line_offsets(md)

    assets, seen = [], set()
    for spec in ASSETS:
        if spec["asset_id"] in seen:
            raise SystemExit("duplicate asset_id %s" % spec["asset_id"])
        seen.add(spec["asset_id"])
        loc = build_locator(md, lines, offs, spec)
        if not loc["unique"]:
            raise SystemExit("quote not unique for %s" % spec["asset_id"])
        if loc["method"] == "char_span" and md[loc["start_char"]:loc["end_char"]] != loc["quote"]:
            raise SystemExit("round-trip slice mismatch for %s" % spec["asset_id"])
        assets.append(dict(
            asset_id=spec["asset_id"],
            asset_class=spec["asset_class"],
            label=spec["label"],
            in_report_section=heading_for(lines, loc["start_line"]),
            locator=loc,
            resolution=spec["resolution"],
            resolution_check=resolution_check(spec, loc, payload),
            note=spec["note"],
        ))

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    covered: set[int] = set()
    for a in assets:
        if a["locator"]["method"] == "document":
            continue
        covered |= set(range(a["locator"]["start_char"], a["locator"]["end_char"]))

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
            platform_status=payload.get("status"),
            platform_figures=payload.get("figures") or [],
            platform_tags=payload.get("tags") or [],
            contract_title=CONTRACT_TITLE,
            contract_chars=CONTRACT_CHARS,
            retrieved_via="GET %s/tensor/reports/%s" % (BASE, REPORT_ID),
            local_copy=str(RUN_DIR / "report_13278.md"),
        ),
        counts=dict(
            assets=len(assets), by_class=by_class, by_resolution=by_res,
            resolved_in_source=by_res.get("resolved_in_source", 0),
            referenced_unresolved=by_res.get("referenced_unresolved", 0),
            declared_absent=by_res.get("declared_absent", 0),
        ),
        coverage=dict(covered_chars=len(covered), source_chars=len(md),
                      pct=round(100.0 * len(covered) / len(md), 2),
                      method="union of char_span locators (document locator excluded)"),
        assets=assets,
        claims=[],
        claims_note=("契约 objective.classify_report_type=false 且 notes 明确 claims 允许为空数组："
                     "本工序只登记资产定位，不做抽取；claim 抽取属下游工作包。"),
        integrity=dict(
            quote_uniqueness="all %d char_span quotes verified unique substrings of the fetched markdown"
                             % (len(assets) - 1),
            hash_recomputed_locally=True,
            hash_matches_contract=True,
            chars_matches_contract=(len(md) == CONTRACT_CHARS),
        ),
    )

    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    art = ART_DIR / "asset_manifest.json"
    art.write_text(blob)
    mirror = DOC_DIR / "asset_manifest.json"
    mirror.write_text(blob)
    if hashlib.sha256(mirror.read_bytes()).hexdigest() != hashlib.sha256(art.read_bytes()).hexdigest():
        print("FATAL: durable mirror differs from artifact")
        return 3
    art_sha = hashlib.sha256(art.read_bytes()).hexdigest()

    # NOTE: kf_result.v1 has additionalProperties=false -> no schema_version key (strict conformance).
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
            retrieved_via=manifest["source"]["retrieved_via"],
            local_copy=str(RUN_DIR / "report_13278.md"),
            generator="scripts/kf_register_wp13278.py",
            verifier="scripts/kf_verify_wp13278.py",
            artifact_path=str(art),
            artifact_sha256=art_sha,
            artifact_bytes=art.stat().st_size,
            verification_status="not_verified",
        ),
        outputs={"asset_manifest.json": manifest},
    )

    res = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    (RUN_DIR / "kf_result.wp-13278-01.json").write_text(res)
    (RUN_DIR / "kf_result_block.wp-13278-01.json").write_text(res)

    print("markdown sha256:", md_hash, "MATCH" if md_hash == EXPECTED_HASH else "MISMATCH")
    print("chars:", len(md), "assets:", len(assets),
          "by_resolution:", json.dumps(by_res, ensure_ascii=False))
    print("coverage: %d/%d chars (%.2f%%)" % (len(covered), len(md), 100.0 * len(covered) / len(md)))
    print("manifest:", art, art_sha)
    print("result:", RUN_DIR / "kf_result.wp-13278-01.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())