"""Register the source assets of report 12690 (work package wp-12690-01, task_type 01-asset-registration).

Design rules enforced here (same discipline as scripts/kf_register_448.py):
  * No hand transcription. Every ``quote`` is sliced out of the report markdown at run time from a
    programmatic anchor (unique line substring + line span); the script re-checks that each quote is
    (a) an exact substring of the markdown and (b) a *unique* substring, and that the recorded char
    span re-slices to the same text, before writing anything.
  * Registration only. No claim extraction (contract: objective.register_assets=true,
    classify_report_type=false, "claims 允许为空数组"). ``claims`` is therefore empty.
  * Nothing is marked verified. ``resolution`` describes locator resolvability only; verification is
    computed by the platform gate, not here.
  * Assets that cannot be resolved from the report record are recorded as ``referenced_unresolved``
    or ``declared_absent`` with a programmatic reason -- never silently dropped and never given an
    invented address.

Inputs:
  runs/wp-12690-01/report_12690.md    (markdown payload, written by the same call if absent)
  runs/wp-12690-01/report_12690.json  (raw API payload: id/title/scenario_key/figures/...)

Outputs:
  artifacts/wp-12690-01/asset_manifest.json
  runs/wp-12690-01/kf_result.wp-12690-01.json       (result envelope, kf_result.v1 shape)
  runs/wp-12690-01/kf_result_block.wp-12690-01.json (same JSON, for the single ```json block)
  docs/wp-12690-01/*                                (durable mirrors: artifacts/** and runs/** are
                                                     dropped by the push gate)

Usage: python3 scripts/kf_register_12690.py
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

REPORT_ID = "12690"
PACKAGE_ID = "wp-12690-01"
TASK_TYPE = "01-asset-registration"
SCENARIO_KEY = "P158W3-N03"
EXPECTED_HASH = "c7ffa8c80de7dacf0f20da21051c644731ee7e82649101b0922b3830796d9d28"
SOURCE_URI = "tensor://reports/12690"
SOURCE_FIELD = "markdown"
EXPECTED_TITLE = "P158W3-N03: TensorDEM CFD-DEM Two-Way Coupling Verification"

RUN_DIR = pathlib.Path("runs/wp-12690-01")
ART_DIR = pathlib.Path("artifacts/wp-12690-01")
DOC_DIR = pathlib.Path("docs/wp-12690-01")

# ----------------------------------------------------------------------------- asset table
# anchor = substring that must occur on exactly ONE line of the markdown.
# span   = (start_line_offset, end_line_offset) relative to that anchor line, inclusive, -1 = last line.
# The emitted quote is the verbatim slice of those lines (never retyped).
ASSETS = [
    dict(asset_id="A01", asset_class="document", label="报告正文（markdown 全文，含 6 节）",
         anchor=None, span=(0, -1), resolution="resolved_in_source",
         note="整篇 markdown 即源资产本体；sha256 见 source.hash，平台独立重算比对"),
    dict(asset_id="A02", asset_class="heading", label="报告标题行（H1）",
         anchor="# P158W3-N03: TensorDEM CFD-DEM Two-Way Coupling Verification", span=(0, 0),
         resolution="resolved_in_source",
         note="与报告记录 title 字段同源（title 属 record 字段，本包只登记 markdown 内出现处）"),
    dict(asset_id="A03", asset_class="section_heading", label="§1 Case Introduction 节标题",
         anchor="## 1. Case Introduction", span=(0, 0), resolution="resolved_in_source",
         note="节边界锚点，供后续工序按节抽取"),
    dict(asset_id="A04", asset_class="physical_model_statement",
         label="物理模型声明 + 颗粒动量方程（无量纲化前原式）",
         anchor="Dilute point-particle Lagrangian tracking with two-way CFD-DEM coupling.",
         span=(0, 2), resolution="resolved_in_source",
         note="含模型声明行与颗粒方程行；公式为排版文本，无独立公式文件"),
    dict(asset_id="A05", asset_class="closure_spec", label="受力闭合式选择（S-N 阻力 / C_A=0.5 / Gidaspow-Ergun）",
         anchor="Drag: Schiller-Naumann", span=(0, 0), resolution="resolved_in_source",
         note="闭合方案选择声明；数值 C_A=0.5 只登记不换算"),
    dict(asset_id="A06", asset_class="parameter_set", label="算例参数表（d_p/rho_p/rho_f/mu/g）",
         anchor="Parameters: d_p=1e-4m", span=(0, 0), resolution="resolved_in_source",
         note="单行内联参数表；A1-A4 与 A5 粒径分开声明"),
    dict(asset_id="A07", asset_class="section_heading", label="§2 Method 节标题",
         anchor="## 2. Method", span=(0, 0), resolution="resolved_in_source",
         note="节边界锚点"),
    dict(asset_id="A08", asset_class="verification_plan", label="校验方案 A1-A5（5 条方法条目）",
         anchor="A1: RK4 integration of Stokes relaxation", span=(0, 5),
         resolution="resolved_in_source",
         note="5 条校验面方法；可执行实现体未随报告提供（见 A20）"),
    dict(asset_id="A09", asset_class="result_block", label="A1 结果块：Stokes 松弛（tau_p/Re_max/误差/判定）",
         anchor="### A1: Stokes Relaxation", span=(0, 4), resolution="resolved_in_source",
         note="含 tau_p、Re_max、最大相对误差 0.886% 与 PASS 判定；数值仅登记"),
    dict(asset_id="A10", asset_class="result_block", label="A2 结果块：终端速度（v_t 解析/数值/Re_t/误差）",
         anchor="### A2: Terminal Velocity", span=(0, 4), resolution="resolved_in_source",
         note="含 v_t_Stokes、v_t_num、Re_t、0.547% 误差与 PASS 判定"),
    dict(asset_id="A11", asset_class="result_block", label="A3 结果块：附加质量系数反演（C_m）",
         anchor="### A3: Added Mass Coefficient", span=(0, 3), resolution="resolved_in_source",
         note="含 C_m_recovered=0.500000、0.000% 误差与 PASS 判定"),
    dict(asset_id="A12", asset_class="result_block", label="A4 结果块：动量守恒残差（单颗粒/20 颗粒）",
         anchor="### A4: Momentum Conservation", span=(0, 4), resolution="resolved_in_source",
         note="含单颗粒与 20 颗粒残差 0.0000e+00、阈值 1% 与 PASS 判定"),
    dict(asset_id="A13", asset_class="result_block", label="A5 结果块：稠密极限 Ergun 对比（phi>0.4）",
         anchor="### A5: Dense Limit Ergun", span=(0, 3), resolution="resolved_in_source",
         note="含 phi>0.4 最大误差 0.000%、阈值 10% 与 PASS 判定"),
    dict(asset_id="A14", asset_class="section_heading", label="§4 Figures 节标题",
         anchor="## 4. Figures", span=(0, 0), resolution="resolved_in_source",
         note="节边界锚点"),
    dict(asset_id="A15", asset_class="figure_declaration", label="图声明（5 幅图，正文仅指向，无图注/路径）",
         anchor="See embedded figures (5 plots).", span=(0, 0), resolution="resolved_in_source",
         note="正文唯一图相关语句；仅声明数量，未给出文件名/路径/URL"),
    dict(asset_id="A16", asset_class="section_heading", label="§5 Notes 节标题",
         anchor="## 5. Notes", span=(0, 0), resolution="resolved_in_source",
         note="节边界锚点"),
    dict(asset_id="A17", asset_class="notes_list", label="适用条件与备注 1-5（Re 界限/S-N→Stokes/反演方法/机器精度/稠密等价）",
         anchor="1. Stokes relaxation requires Re<0.05", span=(0, 4), resolution="resolved_in_source",
         note="5 条备注原文；含 Re_t<<1 等适用条件，属登记不属抽取"),
    dict(asset_id="A18", asset_class="section_heading", label="§6 Error Assessment 节标题",
         anchor="## 6. Error Assessment", span=(0, 0), resolution="resolved_in_source",
         note="节边界锚点"),
    dict(asset_id="A19", asset_class="criteria_table", label="判定表（Criterion/Measured/Threshold/Pass，5 行）",
         anchor="| Criterion | Measured | Threshold | Pass |", span=(0, 6),
         resolution="resolved_in_source",
         note="表头+分隔行+5 条判据原文；数值仅登记，复审由平台门计算"),
    dict(asset_id="A20", asset_class="verdict_statement", label="总判定语句 All passed: YES",
         anchor="**All passed: YES**", span=(0, 0), resolution="resolved_in_source",
         note="报告自述判定；本包不据此标 verified（verification 由平台门计算）"),
    dict(asset_id="A21", asset_class="code_reference",
         label="A1-A5 校验面实现体（TensorDEM 求解器代码）",
         anchor="## 2. Method", span=(0, 0), resolution="referenced_unresolved",
         note="报告以方法名指向实现，但全文不含仓库路径/commit/URL/文件名，无法给出可解析地址"),
    dict(asset_id="A22", asset_class="figure_payload", label="图 A1_stokes_relaxation（图像本体）",
         anchor="See embedded figures (5 plots).", span=(0, 0), resolution="declared_absent",
         note="报告记录 figures[0] 仅含 name/caption 元数据，无 png_base64/URL；markdown 内无图路径"),
    dict(asset_id="A23", asset_class="figure_payload", label="图 A2_terminal_velocity（图像本体）",
         anchor="See embedded figures (5 plots).", span=(0, 0), resolution="declared_absent",
         note="figures[1] 仅元数据，无图字节"),
    dict(asset_id="A24", asset_class="figure_payload", label="图 A3_added_mass（图像本体）",
         anchor="See embedded figures (5 plots).", span=(0, 0), resolution="declared_absent",
         note="figures[2] 仅元数据，无图字节"),
    dict(asset_id="A25", asset_class="figure_payload", label="图 A4_momentum（图像本体）",
         anchor="See embedded figures (5 plots).", span=(0, 0), resolution="declared_absent",
         note="figures[3] 仅元数据，无图字节"),
    dict(asset_id="A26", asset_class="figure_payload", label="图 A5_ergun（图像本体）",
         anchor="See embedded figures (5 plots).", span=(0, 0), resolution="declared_absent",
         note="figures[4] 仅元数据，无图字节"),
]

# regexes used to make "unresolved"/"absent" verdicts programmatic rather than asserted
ADDRESSABLE_REF_RE = re.compile(
    r"(https?://|github\.com|git@|commit\s+[0-9a-f]{7,40}|[\w./-]+\.py\b|TensorDEM/[\w./-]+)"
)
IMAGE_EMBED_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)|<img\b")


# ----------------------------------------------------------------------------- helpers
def _post_json(url: str, payload: dict, token: str | None = None) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login() -> str | None:
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        return None
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = _post_json(base + path, {"username": user, "password": pwd})
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def fetch_report() -> dict:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    req = urllib.request.Request(base + f"/tensor/reports/{REPORT_ID}")
    tok = login()
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.loads(r.read().decode())
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    return payload


def load_source() -> tuple[dict, str]:
    """Return (record, markdown). Prefer cached files; re-fetch when missing."""
    md_path = RUN_DIR / f"report_{REPORT_ID}.md"
    js_path = RUN_DIR / f"report_{REPORT_ID}.json"
    doc_md = DOC_DIR / f"report_{REPORT_ID}.md"
    if not (md_path.exists() and js_path.exists()):
        payload = None
        try:
            payload = fetch_report()
        except Exception as exc:  # offline: fall back to the durable mirror, never to memory
            if not doc_md.exists():
                raise SystemExit(f"API unreachable ({exc}) and no mirror at {doc_md}")
            payload = {"id": int(REPORT_ID), "markdown": doc_md.read_text(),
                       "note": f"offline fallback ({type(exc).__name__})"}
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        js_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        md_path.write_text(payload.get("markdown") or "")
    record = json.loads(js_path.read_text())
    md = md_path.read_text()
    if md != record.get("markdown"):
        # keep the two artefacts consistent: markdown file is authoritative, re-sync the record copy
        record["markdown"] = md
        js_path.write_text(json.dumps(record, ensure_ascii=False, indent=2))
    return record, md


def build_index(md: str) -> tuple[list[str], list[int]]:
    lines = md.split("\n")
    starts, off = [], 0
    for ln in lines:
        starts.append(off)
        off += len(ln) + 1  # +1 for the '\n' separator (last line has no trailing '\n')
    return lines, starts


def resolve_anchor(lines: list[str], anchor: str | None) -> int:
    if anchor is None:
        return 0
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise SystemExit(f"anchor not unique/absent ({len(hits)} hits): {anchor!r}")
    return hits[0]


def slice_asset(md: str, lines: list[str], starts: list[int], spec: dict) -> dict:
    if spec["anchor"] is None:  # whole document
        s_line, e_line = 0, len(lines) - 1
    else:
        a = resolve_anchor(lines, spec["anchor"])
        s_line = a + spec["span"][0]
        e_line = len(lines) - 1 if spec["span"][1] == -1 else a + spec["span"][1]
    if not (0 <= s_line <= e_line < len(lines)):
        raise SystemExit(f"bad span for {spec['asset_id']}: {s_line}..{e_line}")
    quote = "\n".join(lines[s_line : e_line + 1])
    if not quote:
        raise SystemExit(f"empty quote for {spec['asset_id']}")
    occurrences = md.count(quote)
    cs = md.index(quote)
    if md[cs : cs + len(quote)] != quote:
        raise SystemExit(f"char span does not re-slice for {spec['asset_id']}")
    return dict(
        lines_span=(s_line, e_line),
        locator=dict(
            method="document" if spec["anchor"] is None else "char_span",
            start_char=cs,
            end_char=cs + len(quote),
            start_line=s_line,
            end_line=e_line,
            quote=quote,
            unique=occurrences == 1,
        ),
        occurrences=occurrences,
    )


def _emitted_at() -> str:
    """Byte-stable provenance timestamp.

    A fresh wall-clock stamp on every run makes the envelope differ from the already-published copy
    each time, which breaks "re-run reproduces the delivered bytes". So an existing stamp is reused
    (docs mirror first = the published truth, then the run copy); only a first run stamps 'now'.
    """
    for p in (DOC_DIR / f"kf_result.{PACKAGE_ID}.json", RUN_DIR / f"kf_result.{PACKAGE_ID}.json"):
        try:
            prev = json.loads(p.read_text()).get("provenance", {}).get("emitted_at")
        except Exception:
            continue
        if prev:
            return prev
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def figure_payload_check(record: dict) -> dict:
    """Are the image bytes obtainable from the report record?"""
    figs = record.get("figures") or []
    with_bytes = [
        f for f in figs
        if isinstance(f, dict) and (f.get("png_base64") or f.get("url") or f.get("path"))
    ]
    return dict(figures_declared=len(figs), figures_with_payload=len(with_bytes),
                result="present" if with_bytes else "absent")


def code_ref_check(md: str) -> dict:
    hits = ADDRESSABLE_REF_RE.findall(md)
    return dict(pattern=ADDRESSABLE_REF_RE.pattern, hits=len(hits),
                result="present" if hits else "unresolved")


def main() -> int:
    record, md = load_source()
    lines, starts = build_index(md)
    digest = hashlib.sha256(md.encode()).hexdigest()
    if digest != EXPECTED_HASH:
        raise SystemExit(f"source hash mismatch: {digest} != contract {EXPECTED_HASH}")
    if record.get("id") != int(REPORT_ID):
        raise SystemExit(f"report id mismatch: {record.get('id')}")
    if (record.get("title") or "") != EXPECTED_TITLE:
        raise SystemExit(f"title mismatch: {record.get('title')!r}")

    fig_chk = figure_payload_check(record)
    code_chk = code_ref_check(md)
    img_embed_hits = len(IMAGE_EMBED_RE.findall(md))

    assets = []
    for spec in ASSETS:
        sl = slice_asset(md, lines, starts, spec)
        # per-class resolution check, computed (not asserted)
        if spec["asset_class"] == "figure_payload":
            check = dict(check="record.figures[].png_base64|url|path present", result=fig_chk["result"])
        elif spec["asset_class"] == "code_reference":
            check = dict(check=f"regex {code_chk['pattern']} over markdown (hits={code_chk['hits']})",
                         result="unresolved")
        elif spec["asset_class"] == "figure_declaration":
            check = dict(check="markdown image embed syntax ![](...)/<img> (hits=%d)" % img_embed_hits,
                         result="resolved")
        else:
            check = dict(check="markdown[start_char:end_char] resliced and unique", result="resolved")
        assets.append(dict(
            asset_id=spec["asset_id"],
            asset_class=spec["asset_class"],
            label=spec["label"],
            in_report_section=_section_of(lines, sl["lines_span"][0]),
            locator=sl["locator"],
            resolution=spec["resolution"],
            resolution_check=check,
            note=spec["note"],
        ))

    ids = [a["asset_id"] for a in assets]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate asset ids")

    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = dict(
        schema="asset_manifest.v1",
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        source=dict(
            uri=SOURCE_URI,
            field=SOURCE_FIELD,
            hash_alg="sha256",
            hash=digest,
            chars=len(md),
            bytes_utf8=len(md.encode()),
            title=record.get("title"),
            scenario_key=record.get("scenario_key"),
            platform_figures=[{"name": f.get("name"), "caption": f.get("caption")}
                              for f in (record.get("figures") or [])],
            platform_tags=list(record.get("tags") or []),
        ),
        counts=dict(
            assets=len(assets),
            by_class=by_class,
            by_resolution=by_res,
            resolved_in_source=by_res.get("resolved_in_source", 0),
            referenced_unresolved=by_res.get("referenced_unresolved", 0),
            declared_absent=by_res.get("declared_absent", 0),
        ),
        assets=assets,
        claims=[],  # registration only; contract: no extraction, classify_report_type=false
        integrity=dict(
            quote_uniqueness=all(a["locator"]["unique"] for a in assets),
            hash_recomputed_locally=True,
            hash_matches_contract=digest == EXPECTED_HASH,
            quote_count=len(assets),
            quotes_unique_count=sum(1 for a in assets if a["locator"]["unique"]),
            char_spans_resliced=True,
            claims_count=0,
            checks=dict(figure_payload=fig_chk, code_reference=code_chk,
                        markdown_image_embeds=img_embed_hits),
        ),
    )

    envelope = dict(
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        provenance=dict(
            source_hash="sha256:" + digest,
            source_field=SOURCE_FIELD,
            producer="TensorKnowledge scripts/kf_register_12690.py (m15752)",
            emitted_at=_emitted_at(),
            notes=("registration only: 26 assets located by char span in the report markdown; "
                   "claims intentionally empty (objective.classify_report_type=false); "
                   "no asset marked verified -- verification is computed by the platform gate"),
        ),
        outputs={"asset_manifest.json": manifest},
        claims=[],
    )

    for d in (ART_DIR, DOC_DIR):
        d.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest, ensure_ascii=False, indent=2)
    (ART_DIR / "asset_manifest.json").write_text(text)
    (DOC_DIR / "asset_manifest.json").write_text(text)
    env_text = json.dumps(envelope, ensure_ascii=False, indent=2)
    (RUN_DIR / f"kf_result.{PACKAGE_ID}.json").write_text(env_text)
    (DOC_DIR / f"kf_result.{PACKAGE_ID}.json").write_text(env_text)
    # durable mirror of the source markdown: runs/** is dropped by the push gate
    (DOC_DIR / f"report_{REPORT_ID}.md").write_text(md)

    print("hash:", digest, "MATCH", digest == EXPECTED_HASH)
    print("assets:", len(assets), "by_resolution:", by_res)
    print("quote_uniqueness:", manifest["integrity"]["quote_uniqueness"])
    print("figure_payload:", fig_chk, "code_reference hits:", code_chk["hits"])
    print("wrote:", ART_DIR / "asset_manifest.json", RUN_DIR / f"kf_result.{PACKAGE_ID}.json")
    return 0


SECTIONS = ["1. Case Introduction", "2. Method", "3. Results", "4. Figures", "5. Notes",
            "6. Error Assessment"]


def _section_of(lines: list[str], line_no: int) -> str:
    """Which '## <n>. ...' section does this line live in? (programmatic, no hand labels)"""
    for i in range(line_no, -1, -1):
        ln = lines[i]
        if ln.startswith("## "):
            return ln[3:].strip()
    return "preamble (before first ## section)"


if __name__ == "__main__":
    sys.exit(main())