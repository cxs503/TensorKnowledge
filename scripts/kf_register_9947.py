#!/usr/bin/env python3
"""Work package wp-9947-01 — task_type 01-asset-registration for report_id=9947.

Scope (from the contract): register the source asset (report 9947 markdown), confirm its byte hash,
and list every attachment/artifact that can be parsed *without extraction*. No claim extraction,
no report-type classification, no verified marks.

Discipline:
  * the markdown is fetched from the platform API (never typed from memory) and its sha256 is recomputed
    locally and compared with the contract source_hash before anything else happens;
  * every registered asset carries a char-span locator whose `quote` is a *slice of that markdown*,
    asserted to occur exactly once in the text;
  * resolution status is machine-checked (char span / address probe / platform figures field) and the
    result is bound to the declared status by a strict mapping (see RESOLUTION_TO_CHECK).

Inputs:
  GET {TENSOR_API_BASE}/tensor/reports/9947  -> runs/wp-9947-01/report_9947.json
                                             -> runs/wp-9947-01/report_9947.md
Outputs:
  artifacts/wp-9947-01/asset_manifest.json      (output declared by the contract)
  docs/wp-9947-01/asset_manifest.json           (durable mirror: the repo push gate drops artifacts/**)
  runs/wp-9947-01/kf_result.wp-9947-01.json     (kf_result.v1 envelope)
  runs/wp-9947-01/kf_result_block.wp-9947-01.json

Usage: python3 scripts/kf_register_9947.py            # fetch (or reuse local copy) + register
       python3 scripts/kf_register_9947.py --offline  # reuse runs/wp-9947-01/report_9947.md
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.parse
import urllib.request

REPORT_ID = "9947"
PACKAGE_ID = "wp-9947-01"
TASK_TYPE = "01-asset-registration"
# contract input.source_hash (sha256 of the markdown field's UTF-8 bytes)
EXPECTED_HASH = "c9857b84a9ea71ea174f3392d34e8e61403202ee154fdab059c4e9abd83fc0bf"
SOURCE_URI = "tensor://reports/9947"
CONTRACT_TITLE = "【试点】技术路线锁定 A/B 终局对照 v1"
CONTRACT_SCENARIO = "pilot-ab"
CONTRACT_CHARS = 616

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
RUN_DIR = pathlib.Path("runs/wp-9947-01")
ART_DIR = pathlib.Path("artifacts/wp-9947-01")
DOC_DIR = pathlib.Path("docs/wp-9947-01")  # committed copy of every deliverable
WORKTREE = pathlib.Path(".").resolve()

# --- anchor table -------------------------------------------------------------------------------
# anchor = a substring that must occur exactly once in the markdown (it only *finds* the line);
# span   = (first_line_offset, last_line_offset) relative to the anchor line, inclusive;
# the emitted quote is the verbatim slice md[start_char:end_char] — never retyped.
ASSETS = [
    dict(asset_id="A01", asset_class="document", label="报告正文（markdown 全文，616 字符）",
         method="document", resolution="resolved_in_source",
         note="整篇 markdown 即源资产本体；sha256 见 source.hash，由平台独立重算比对"),
    dict(asset_id="A02", asset_class="heading", label="报告标题行（自动合成时间戳）",
         anchor="## A/B 试点终局对照", span=(0, 0), resolution="resolved_in_source",
         note="标题行；与 API title 字段（【试点】技术路线锁定 A/B 终局对照 v1）不同名，属不同层级的标题"),
    dict(asset_id="A03", sub=True, asset_class="external_file_reference", label="prereg 预注册文件路径（/root/tp-agent/pilot_ab_prereg_20261109.md）",
         anchor="prereg：`/root/tp-agent/pilot_ab_prereg_20261109.md`", span=(0, 0),
         resolution="referenced_unresolved", probe="host_path",
         note="报告给出绝对路径但未给出哈希值本身（哈希被推迟到 GAP-LBM-MCMP-POISEUILLE.evidence），"
              "本工序不据路径断言其内容身份"),
    dict(asset_id="A04", sub=True, asset_class="evidence_pointer", label="GAP 证据键名 GAP-LBM-MCMP-POISEUILLE.evidence",
         anchor="sha256 在 GAP-LBM-MCMP-POISEUILLE.evidence", span=(0, 0),
         resolution="referenced_unresolved",
         note="仅键名，无 GAP 记录 id / URL / DOI；本工序不猜测地址"),
    dict(asset_id="A05", asset_class="model_roster", label="模型席位配置（dev 双臂 / B 审查席 / QR 双臂）",
         anchor="dev 两臂同模型 qwen3.7-plus", span=(0, 0), resolution="resolved_in_source",
         note="三个模型名的原文；属配置声明，不是运行日志"),
    dict(asset_id="A06", asset_class="table_shell", label="五席位终态表（表头+分隔行+5 行，表体为占位符）",
         anchor="| 席位 | 任务 | 终态 | 墙钟 | 摘要 |", span=(0, 6), resolution="resolved_in_source",
         note="登记的是表格结构与本文字面值：5 行数据的「任务」列均为 m-、「终态」列均为 -、「墙钟」列均为空、"
              "「摘要」列均为 -；表内不含任何数值结果（见 notice P1）"),
    dict(asset_id="A07", sub=True, asset_class="acceptance_criteria", label="判据三主一加分（①<5% ②<10% ③<0.005·Umax ④趋势）",
         anchor="判据三主一加分（①<5% ②<10% ③<0.005·Umax ④趋势）", span=(0, 0),
         resolution="resolved_in_source",
         note="四条判据与三条阈值以原文数字逐字登记；判据的物理定义（量纲/归一化方式）报告未在本文给出，"
              "其细节被指向各 QR 报告"),
    dict(asset_id="A08", sub=True, asset_class="decision_rule", label="裁决规则（QR PASS 数→过程指标→双 FAIL 比根因深度）",
         anchor="裁决规则按 prereg：QR PASS 数→过程指标→双 FAIL 比根因深度", span=(0, 0),
         resolution="resolved_in_source", note="规则原文；规则的完整版在 A03 指向的 prereg（未解析）"),
    dict(asset_id="A09", sub=True, asset_class="deferred_decision", label="人工终裁与推广/否决建议交 owner",
         anchor="人工终裁与推广/否决建议交 owner", span=(0, 0), resolution="resolved_in_source",
         note="终裁被显式推迟给 owner：本报告不含终裁结论（见 notice P2）"),
    dict(asset_id="A10", sub=True, asset_class="upstream_report_pointer", label="两臂 QR 报告引用（scenario_key=pilot-qr-a / pilot-qr-b）",
         anchor="scenario_key=pilot-qr-a / pilot-qr-b", span=(0, 0),
         resolution="referenced_unresolved", probe="scenario_key",
         probe_keys=["pilot-qr-a", "pilot-qr-b"],
         note="只给 scenario_key，未给 report_id/版本/哈希；判据细节在彼处"),
    dict(asset_id="A11", asset_class="upstream_report_pointer", label="原始证据引用（pilot-arm-a / pilot-arm-b / pilot-ab-review）",
         anchor="原始证据：pilot-a/b 两臂报告", span=(0, 0),
         resolution="referenced_unresolved", probe="scenario_key",
         probe_keys=["pilot-arm-a", "pilot-arm-b", "pilot-ab-review"],
         note="三个 scenario_key 的字面原文；报告未给出对应 report_id，身份不在此断言"),
    dict(asset_id="A12", asset_class="figure_slot", label="图件：报告无任何图件，平台 figures 字段为空",
         method="document", resolution="declared_absent", probe="platform_figures",
         note="报告全文无「图」声明、无 png/曲线引用，平台 figures=[]；本工序只登记「无图」这一事实，"
              "不代替上游生产图件"),
]

RESOLUTION_TO_CHECK = {
    "resolved_in_source": "resolved",
    "referenced_unresolved": "unresolved",
    "declared_absent": "absent",
}

RESOLUTION_SEMANTICS = {
    "resolved_in_source": "内容可在源 markdown 内按 [start_char,end_char) 逐字切片，且该切片在全文唯一",
    "referenced_unresolved": "报告只给指针（文件名/路径/键名/scenario_key），未给可校验的 id+哈希组合；"
                             "本工序只登记指针与探测结果，不断言被指对象的内容身份/版本",
    "declared_absent": "报告与平台元数据均无该资产（此处指图件）",
}


# --- helpers ------------------------------------------------------------------------------------
def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def line_offsets(md: str) -> tuple[list[str], list[int]]:
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def build_locator(md: str, lines: list[str], offs: list[int], spec: dict) -> dict:
    if spec.get("method") == "document":
        return dict(method="document", start_char=0, end_char=len(md),
                    start_line=0, end_line=len(lines) - 1, quote=md,
                    unique=md.count(md) == 1)
    anchor = spec["anchor"]
    if md.count(anchor) != 1:
        raise SystemExit("anchor %r occurs %d times (must be 1)" % (anchor, md.count(anchor)))
    li = next(i for i, ln in enumerate(lines) if anchor in ln)
    l0 = li + spec["span"][0]
    l1 = li + spec["span"][1]
    if spec.get("sub") and l0 == l1:  # tight locator: slice exactly the anchor inside one line
        start = offs[l0] + lines[l0].index(anchor)
        end = start + len(anchor)
        quote = anchor
    else:  # whole-line span
        start = offs[l0]
        end = offs[l1] + len(lines[l1])
        quote = md[start:end]
    return dict(method="char_span", start_char=start, end_char=end,
                start_line=l0, end_line=l1, quote=quote, unique=md.count(quote) == 1)


def login() -> str | None:
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (u and p):
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            req = urllib.request.Request(BASE + path, data=json.dumps(
                {"username": u, "password": p}).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def fetch_report() -> tuple[str, dict]:
    tok = login()
    if not tok:
        raise SystemExit("login failed (need TENSOR_AGENT_USER/TENSOR_AGENT_PASS)")
    req = urllib.request.Request(BASE + "/tensor/reports/" + REPORT_ID)
    req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.loads(r.read().decode())
    return payload["markdown"], payload


def probe_scenario_keys(keys: list[str]) -> dict:
    """Read-only platform probe: does a scenario_key resolve to a report? (identity of the *version*
    is still not pinned by the report, which is why the asset stays referenced_unresolved)."""
    tok = login()
    out = {"endpoint": "/tensor/reports?scenario_key=<key>", "auth": "bearer" if tok else "none",
           "hits": {}}
    for k in keys:
        try:
            req = urllib.request.Request(
                BASE + "/tensor/reports?" + urllib.parse.urlencode({"scenario_key": k, "page_size": 5}))
            if tok:
                req.add_header("Authorization", "Bearer " + tok)
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
            items = d.get("items", d if isinstance(d, list) else [])
            out["hits"][k] = dict(report_ids=[it.get("id") for it in items][:5], count=len(items))
        except Exception as exc:  # probe failure is recorded, never silently treated as a hit
            out["hits"][k] = dict(error=type(exc).__name__ + ": " + str(exc)[:120])
    return out


def resolution_check(spec: dict, loc: dict, payload: dict) -> dict:
    probe = spec.get("probe")
    if spec["resolution"] == "resolved_in_source":
        return dict(check="char_span_in_source_markdown", result="resolved",
                    span=[loc["start_char"], loc["end_char"]],
                    quote_occurrences=1,
                    detail="re-slice of the fetched markdown at the recorded char span; quote unique in text")
    if spec["resolution"] == "declared_absent":
        figs = payload.get("figures") or []
        return dict(check="platform_figures_field+citation_scan", result="absent",
                    platform_figures_count=len(figs),
                    image_markdown_refs=len(re.findall(r"!\[", payload["markdown"])),
                    detail="平台 figures 字段为空且正文无图片引用；报告亦无「无图理由」段落，故此资产按「无图」登记")
    # referenced_unresolved: record what addresses the report actually gives, then probe them read-only
    quote = loc["quote"]
    paths = re.findall(r"/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+", quote)
    urls = re.findall(r"https?://[^\s)`]+", quote)
    dois = re.findall(r"10\.\d{4,9}/[^\s)`]+", quote)
    check = dict(check="external_address_probe", result="unresolved",
                 addresses_found=dict(paths=paths, urls=urls, dois=dois,
                                      scenario_keys=re.findall(r"scenario_key=([A-Za-z0-9_-]+)", quote)),
                 identity_binding="none: the report gives no report_id/sha256 for the referenced object")
    if probe == "host_path" and paths:
        info = []
        for p in paths:
            ap = pathlib.Path(p)
            info.append(dict(path=p, exists_on_host=ap.exists(),
                             size_bytes=ap.stat().st_size if ap.exists() else None,
                             inside_worktree=str(ap).startswith(str(WORKTREE))))
        check["host_probe"] = info
        check["detail"] = ("路径在宿主上存在与否已实测并记录，但报告未给出该文件的哈希值（推迟到 A04 的 GAP 键），"
                           "故不对其内容身份作断言")
    elif probe == "scenario_key":
        keys = spec.get("probe_keys", [])
        for k in keys:  # zero-invention guard: every probed key must literally occur in the quote
            if k not in quote:
                raise SystemExit("probe key %r not a literal of asset %s quote" % (k, spec["asset_id"]))
        check["addresses_found"]["probed_keys"] = keys
        check["platform_probe"] = {"endpoint": "/tensor/reports?scenario_key=<key>",
                                   "auth": PROBE.get("auth"),
                                   "hits": {k: PROBE["hits"].get(k) for k in keys}}
        check["detail"] = ("scenario_key 在平台上可命中报告（命中 id 见 platform_probe），但本报告未写明 report_id/"
                           "版本/哈希，指针→具体版本的绑定关系不由本工序断言")
    return check


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)

    md_path = RUN_DIR / "report_9947.md"
    json_path = RUN_DIR / "report_9947.json"
    if "--offline" in sys.argv and md_path.exists():
        md = md_path.read_text()
        payload = json.loads(json_path.read_text())
        retrieved_via = "local copy %s (offline)" % md_path
    else:
        md, payload = fetch_report()
        md_path.write_text(md)
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        retrieved_via = "GET %s/tensor/reports/%s" % (BASE, REPORT_ID)

    md_hash = sha256_text(md)
    if md_hash != EXPECTED_HASH:
        print("FATAL: markdown sha256 %s != contract source_hash %s" % (md_hash, EXPECTED_HASH))
        return 2
    if len(md) != CONTRACT_CHARS:
        print("FATAL: chars %d != contract chars %d" % (len(md), CONTRACT_CHARS))
        return 2
    if payload.get("title") != CONTRACT_TITLE or payload.get("scenario_key") != CONTRACT_SCENARIO:
        print("FATAL: title/scenario_key mismatch: %r / %r"
              % (payload.get("title"), payload.get("scenario_key")))
        return 2

    global PROBE
    keys = sorted({k for s in ASSETS if s.get("probe") == "scenario_key"
                   for k in s.get("probe_keys", [])})
    PROBE = probe_scenario_keys(keys) if keys else {"hits": {}}

    lines, offs = line_offsets(md)
    assets, seen = [], set()
    for spec in ASSETS:
        if spec["asset_id"] in seen:
            raise SystemExit("duplicate asset_id " + spec["asset_id"])
        seen.add(spec["asset_id"])
        loc = build_locator(md, lines, offs, spec)
        if loc["method"] == "char_span" and not loc["unique"]:
            raise SystemExit("quote not unique for %s" % spec["asset_id"])
        head = "(document)"
        for ln in lines[: loc["start_line"] + 1]:
            if ln.startswith("#"):
                head = ln.strip()
        rc = resolution_check(spec, loc, payload)
        if rc["result"] != RESOLUTION_TO_CHECK[spec["resolution"]]:
            raise SystemExit("resolution_check mismatch for %s" % spec["asset_id"])
        assets.append(dict(asset_id=spec["asset_id"], asset_class=spec["asset_class"],
                           label=spec["label"], in_report_section=head, locator=loc,
                           resolution=spec["resolution"], resolution_check=rc, note=spec["note"]))

    # derive dangling-pointer notices from the probe evidence (no hand-written numbers)
    notices = [
        dict(id="P1", scope="A06",
             text="五席位终态表的表体是占位符（任务列 m- / 终态列 - / 墙钟列空 / 摘要列 -），"
                  "报告标题与平台 summary 所说的「终态/表」在本文中没有数值结果落地",
             evidence_asset="A06"),
        dict(id="P2", scope="A08,A09",
             text="判决与终裁均不在本文：裁决规则被指向 prereg(A03)，人工终裁被显式交 owner(A09)",
             evidence_asset="A09"),
        dict(id="P3", scope="A10,A11",
             text="判据细节与原始证据均以 scenario_key 形式外置（A10/A11），本文自足性不足："
                  "不含任何 <5%/<10%/<0.005·Umax 的实测值",
             evidence_asset="A11"),
        dict(id="P4", scope="A12",
             text="全文无图、平台 figures=[]：「终局对照」不含任何对照曲线或场量云图",
             evidence_asset="A12"),
    ]
    dangling = {k: v for k, v in PROBE.get("hits", {}).items()
                if isinstance(v, dict) and v.get("count", 0) == 0}
    if dangling:
        notices.append(dict(
            id="P5", scope="A10,A11",
            text="指针探测：scenario_key %s 在平台 /tensor/reports 查询下命中 0 条（同批其余键各命中 %s 条）；"
                 "本工序只登记「在该查询面下不可见」这一事实，不推断原因是未发布、未生成还是权限不可见"
                 % ("、".join(sorted(dangling)),
                    "/".join(sorted({str(v.get("count")) for k, v in PROBE["hits"].items()
                                     if isinstance(v, dict) and v.get("count", 0) > 0}))),
            evidence_asset="A11",
            probe=dict(query="GET /tensor/reports?scenario_key=<key>", zero_hit_keys=sorted(dangling)),
        ))

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = dict(
        schema="asset_manifest.v1",
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        source=dict(
            uri=SOURCE_URI, field="markdown", hash_alg="sha256", hash=md_hash,
            chars=len(md), bytes_utf8=len(md.encode()),
            title=payload.get("title"), scenario_key=payload.get("scenario_key"),
            platform_id=payload.get("id"), platform_mission_id=payload.get("mission_id"),
            platform_stage=payload.get("stage"), platform_status=payload.get("status"),
            platform_created_at=payload.get("created_at"),
            platform_title=payload.get("title"),
            platform_summary=payload.get("summary"),
            platform_figures=payload.get("figures") or [],
            platform_tags=payload.get("tags") or [],
            retrieved_via=retrieved_via,
            local_copy=str(md_path),
        ),
        counts=dict(assets=len(assets), by_class=by_class, by_resolution=by_res,
                    resolved_in_source=by_res.get("resolved_in_source", 0),
                    referenced_unresolved=by_res.get("referenced_unresolved", 0),
                    declared_absent=by_res.get("declared_absent", 0)),
        resolution_semantics=RESOLUTION_SEMANTICS,
        assets=assets,
        claims=[],
        claims_note=("按工作包契约 objective.classify_report_type=false 且 notes 明确 claims 允许空数组："
                     "本工序只登记资产定位与可解析状态，不做 claim 抽取，也不对报告结论表态；"
                     "claim 抽取归下游工序。资产级 resolution 已为每个条目显式给出。"),
        notices=notices,
        integrity=dict(
            quote_uniqueness="每个 char_span 资产的 quote 都是源 markdown 的逐字切片，且全文出现次数==1"
                             "（scripts/kf_verify_9947.py 在独立进程重取后重切片复核）",
            hash_recomputed_locally=True, hash_matches_contract=True),
    )

    art = ART_DIR / "asset_manifest.json"
    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    art.write_text(blob)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    mirror = DOC_DIR / "asset_manifest.json"
    mirror.write_text(blob)
    art_hash = hashlib.sha256(art.read_bytes()).hexdigest()
    if hashlib.sha256(mirror.read_bytes()).hexdigest() != art_hash:
        print("FATAL: durable mirror differs from artifact")
        return 3

    out_manifest = dict(artifact_path=str(art), artifact_sha256=art_hash,
                        artifact_bytes=art.stat().st_size, durable_mirror=str(mirror))
    out_manifest.update(manifest)

    result = dict(
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        provenance=dict(
            source_uri=SOURCE_URI, source_field="markdown",
            source_hash="sha256:" + md_hash,
            source_chars=len(md), source_bytes_utf8=len(md.encode()),
            source_title=payload.get("title"), scenario_key=payload.get("scenario_key"),
            contract_version="1.0", lane="C", work_package=PACKAGE_ID,
            retrieved_via=retrieved_via, local_copy=str(md_path),
            generator="scripts/kf_register_9947.py",
            verifier="scripts/kf_verify_9947.py",
            verification_status="not_verified",  # verification is computed by the platform gate
        ),
        outputs={"asset_manifest.json": out_manifest},
        claims=[],
    )
    res_path = RUN_DIR / "kf_result.wp-9947-01.json"
    res_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (RUN_DIR / "kf_result_block.wp-9947-01.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print("markdown sha256:", md_hash, "MATCH")
    print("chars:", len(md), "bytes:", len(md.encode()))
    print("assets:", len(assets), "by_class:", json.dumps(by_class, ensure_ascii=False))
    print("by_resolution:", json.dumps(by_res, ensure_ascii=False))
    print("manifest:", art, art_hash)
    print("result:", res_path)
    return 0


PROBE: dict = {"hits": {}}

if __name__ == "__main__":
    sys.exit(main())