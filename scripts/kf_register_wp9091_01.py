"""KF work package wp-9091-01 / task_type=01-asset-registration: register the assets of report 9091.

Scope (contract): confirm report_id + markdown byte hash, list the parsable attachments/artifacts,
do NOT extract knowledge (claims may be empty). Every registered asset carries a locator that is a
verbatim, unique substring of the source markdown plus an explicit resolution status
(resolved_in_source / referenced_unresolved / declared_absent) - no invented information.

Inputs (produced by scripts/kf_fetch_report.py):
  runs/wp-9091-01/report_9091.md    markdown payload (byte-identical to what the platform hashes)
  runs/wp-9091-01/report_9091.json  raw API payload (id/title/scenario_key/figures/tags/...)

Outputs:
  artifacts/wp-9091-01/asset_manifest.json                 the registered asset manifest
  docs/wp-9091-01/asset_manifest.json                      durable mirror (push gate strips artifacts/ & runs/)
  docs/wp-9091-01/report_9091.md                           durable mirror of the source markdown
  runs/wp-9091-01/kf_result.wp-9091-01.json                kf_result.v1 result envelope
  runs/wp-9091-01/kf_result_block.wp-9091-01.json          same JSON, for the single ```json block
  docs/wp-9091-01/kf_result.wp-9091-01.json                durable mirror of the envelope

Usage: python3 scripts/kf_register_wp9091_01.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys

REPORT_ID = "9091"
PACKAGE_ID = "wp-9091-01"
TASK_TYPE = "01-asset-registration"
EXPECTED_HASH = "89c2a8f978e2915cb079337441118458e78017bcb4a177c38d8c8a00cc8c6f17"
SOURCE_URI = "tensor://reports/9091"
SOURCE_FIELD = "markdown"

RUN_DIR = pathlib.Path("runs/wp-9091-01")
ART_DIR = pathlib.Path("artifacts/wp-9091-01")
DOC_DIR = pathlib.Path("docs/wp-9091-01")

# ---------------------------------------------------------------------------
# Anchor table. Each entry: asset_id, asset_class, label, and either
#   (start_anchor, end_anchor)  -> line span [line(start), line(end)] found by unique substring
#   (start_anchor, None)        -> single line
# The emitted quote is the verbatim slice of the markdown covering that line span.
# resolution: how the *asset body* resolves relative to this worktree / platform payload.
# ---------------------------------------------------------------------------
ASSETS = [
    dict(asset_id="A01", asset_class="document", label="报告正文（markdown 全文，sha256 见 source.hash）",
         start=None, end=None, resolution="resolved_in_source",
         note="整篇 markdown 即源资产；此为唯一 method=document 的资产"),
    dict(asset_id="A02", asset_class="heading", label="报告中文主标题行",
         start="# FSI 验证阶梯（弱耦合→强耦合）IN70-N04 — 阶段结论", end=None,
         resolution="resolved_in_source",
         note="与 API title 字段同源；英文标题行紧随其后，未重复登记"),
    dict(asset_id="A03", asset_class="status_statement", label="总体状态声明（partial, honest；rung2 未取得资格）",
         start="Status: **partial, honest**.", end="elastic trailing edge) is **not qualified**:",
         resolution="resolved_in_source",
         note="逐级状态：rung1/rung3 过门，rung2 因流体半程门槛失败未取得资格"),
    dict(asset_id="A04", asset_class="artifact_index_declaration", label="工件索引声明（JSON 在 artifacts/，图在 artifacts/*.png）",
         start="Everything below quotes measured numbers", end="`artifacts/*.png`.",
         trim_start=True, resolution="resolved_in_source",
         note="报告自述的记录/图件落位；本体在本工作树内不存在，见 A17/A18"),
    dict(asset_id="A05", asset_class="table", label="模块清单表（模块→职责，6 行）",
         start="| module | role |", end="tests/test_fsi_{beam2d",
         resolution="resolved_in_source",
         note="表内 6 条职责声明；模块/脚本/测试路径本体属 TensorFEM 仓，见 A06"),
    dict(asset_id="A06", asset_class="external_file_set", label="代码模块与脚本路径（src/tensorfem/fsi/*.py, scripts/fsi_ladder_*.py, tests/test_fsi_*.py）",
         start="`src/tensorfem/fsi/beam2d.py`", end=None, substring=True,
         resolution="referenced_unresolved",
         note="locator 只钉住表中首个模块路径；完整路径清单见 paths（5 模块 + 2 脚本），本工作树无 src/ 与 scripts/fsi_ladder_*，属 TensorFEM 仓产物，未解析",
         paths=["src/tensorfem/fsi/beam2d.py", "src/tensorfem/fsi/flow2d.py",
                "src/tensorfem/fsi/coupling.py", "src/tensorfem/fsi/theodorsen.py",
                "src/tensorfem/fsi/benchmarks.py", "src/tensorfem/fsi/",
                "scripts/fsi_ladder_run.py", "scripts/fsi_ladder_figures.py"]),
    dict(asset_id="A07", asset_class="parameter_set", label="rung1 梁参数（E, ν, ρ, h, L, 40 单元）",
         start="Clamped-free beam, `E = 2e11 Pa`", end="40 elements.",
         resolution="resolved_in_source",
         note="参数原文；本工序只登记不换算、不复核"),
    dict(asset_id="A08", asset_class="table", label="rung1 结构解析对照表（4 量：位移 + f1/f2/f3）",
         start="| quantity | computed | analytic | error |", end="711.9738 Hz",
         resolution="resolved_in_source",
         note="上游自报误差 <1e−15 / 0.048 % / 0.34 % / 0.80 %；本工序不复核数值"),
    dict(asset_id="A09", asset_class="verification_statement", label="平面应变有效模量断言（1−ν²=0.91）与 Newmark 能量漂移 <5e−3",
         start="Plane strain switches the modulus", end="relative drift < 5e−3 over 400 steps.",
         resolution="resolved_in_source",
         note="指向 test_plane_strain_uses_effective_modulus（测试本体见 A06，未解析）"),
    dict(asset_id="A10", asset_class="formula", label="Theodorsen 升力亏损函数闭式 C(k) 表达式",
         start="`C(k) = H₁⁽²⁾(k)/(H₁⁽²⁾(k) + iH₀⁽²⁾(k))`", end=None,
         resolution="resolved_in_source",
         note="闭式定义（单行）；实现与独立 Bessel 实现的双路校验见 A11"),
    dict(asset_id="A11", asset_class="verification_statement", label="C(k) 双路实现差 1.1e−16 与解析极限 C(1e−12)=1, C(1e7)=0.5",
         start="`scipy.special.hankel2`", end="`C(1e7) = 0.50000`.",
         resolution="resolved_in_source",
         note="解析极限复现属闭式自检，非外部基准，报告亦未据此宣称外部验证"),
    dict(asset_id="A12", asset_class="verification_statement", label="Jones (1940) 二极点近似：k≤0.2 时 |C| 差 <3%（最差 2.1%）",
         start="* Jones (1940) two-pole approximation", end="(worst sample 2.1 %).",
         resolution="resolved_in_source",
         note="外部锚点=Jones 1940；报告未给页码/公式号，未解析到可核对原文"),
    dict(asset_id="A13", asset_class="verification_statement", label="三极点有理拟合误差（max 0.171 %，mean 0.076 %，400 个对数样本）",
         start="* The three-pole rational fit", end="(400 log-spaced samples).",
         resolution="resolved_in_source",
         note="时域路径所用的 C(k) 有理拟合精度；样本数与区间均在原文"),
    dict(asset_id="A14", asset_class="parameter_set", label="经典二维剖面参数（μ=20, a=−0.2, x_θ=0.2, r_θ=0.5, ω_h=1, ω_α=2, b=0.5）",
         start="Classical section (`μ = 20`", end="p-k eigenvalue iteration:",
         resolution="resolved_in_source",
         note="颤振算例的输入参数全集；p-k 结果表见 A15"),
    dict(asset_id="A15", asset_class="table", label="p-k 颤振边界结果表（U_f, k_f, ω_f, 阻尼, 括号校验，8 行）",
         start="| quantity | value |", end="| bracket check |",
         resolution="resolved_in_source",
         note="rung3 的合格结果锚点（U_f=1.1874 m/s）；本工序只登记"),
    dict(asset_id="A16", asset_class="table", label="跨路径时域增长率表（σ at U/U_f = 0.45/1.0/1.6/2.5）",
         start="| U/U_f | 0.45 | 1.0 | 1.6 | 2.5 |", end="| σ [1/s] (time domain) |",
         resolution="resolved_in_source",
         note="honest FAIL 的原始数字来源：时域边界落在 1.6U_f~2.5U_f，与 p-k 分歧 >60 %"),
    dict(asset_id="A17", asset_class="external_dataset", label="DFG 2D-2 算例记录与图件（artifacts/fsi_dfg2d2.json / artifacts/fsi_dfg2d2.png）",
         start="(`artifacts/fsi_dfg2d2.json`", end=None,
         resolution="referenced_unresolved",
         note="本工作树内 artifacts/fsi_dfg2d2.{json,png} 不存在；平台报告 payload 亦未内嵌二进制",
         paths=["artifacts/fsi_dfg2d2.json", "artifacts/fsi_dfg2d2.png"]),
    dict(asset_id="A18", asset_class="external_dataset", label="Theodorsen 算例记录（artifacts/fsi_theodorsen.json）与全部图件（artifacts/*.png）",
         start="python scripts/fsi_ladder_run.py theodorsen", end="--out artifacts/fsi_theodorsen.json",
         resolution="referenced_unresolved",
         note="复现命令中声明的输出路径；文件本体不在本工作树，见 A19 平台 figures 字段交叉核对",
         paths=["artifacts/fsi_theodorsen.json", "artifacts/*.png"]),
    dict(asset_id="A19", asset_class="platform_figure_set", label="平台 figures 字段（3 张：fsi_theodorsen_ck / fsi_flutter_boundary / fsi_dfg2d2）",
         start="figure `artifacts/fsi_dfg2d2.png`", end=None, substring=True,
         resolution="referenced_unresolved",
         check="platform_figures",
         note="payload.figures 有 3 条 name+caption（present），但该字段不含图片本体；正文只字面点名 fsi_dfg2d2.png，另两张仅以 artifacts/*.png 概括（A04）"),
    dict(asset_id="A20", asset_class="table", label="DFG 2D-2 对照表（computed vs Turek & Hron 2006，4 行）",
         start="| quantity | computed | reference (Turek & Hron 2006) | error |", end="max |∇·u| (interior)",
         resolution="resolved_in_source",
         note="外部基准=Turek & Hron 2006 的 C_D/St 参考值；表内误差为上游自报（80.7 %/869 %/37.4 %），本工序不复核"),
    dict(asset_id="A21", asset_class="defect_pointer", label="缺陷定位声明：物体载荷重构（F=−ρ∫χ∇p dV 均匀铺开）为主导缺陷，含 strict-xfail 测试名",
         start="The pressure projection itself is exact", end="the diffuse body leaks.",
         resolution="resolved_in_source",
         note="指向 test_immersed_body_is_driven_to_the_prescribed_velocity（strict xfail）；测试体见 A06，未解析"),
    dict(asset_id="A22", asset_class="consequence_statement", label="WITHHELD 判定与放弃生产的声明（无 Turek–Hron/VIV 结论；生产算例被弃跑）",
         start="Consequence: **no Turek–Hron FSI-2", end="rather than reporting a number the solver cannot support.",
         resolution="resolved_in_source",
         note="不可被覆盖为通过的关键否定性声明；判定汇总见 A26"),
    dict(asset_id="A23", asset_class="mechanism_spec", label="强耦合驱动机制规格（子迭代固定点、Aitken 松弛、闭合能量账本）",
         start="`ImplicitCouplingDriver` re-runs", end="`relative_residual = |work − storage − dissipated| / Σ|work|`.",
         resolution="resolved_in_source",
         note="机制与三条残差/账本定义；验证范围为静水初值，见 A24"),
    dict(asset_id="A24", asset_class="verification_statement", label="机制已验证行为 4 条 + 能量判据 WITHHELD 声明",
         start="Verified behaviours (tests): a quiescent start", end="rather than claimed.",
         resolution="resolved_in_source",
         note="子迭代残差门与账本有限性已验证；绕流耦合响应未验证（能量 <5 % 判据 WITHHELD）"),
    dict(asset_id="A25", asset_class="limitation_set", label="已知缺陷与局限 6 条（载荷重构 / 非方形网格泄漏 / 定系数投影 / 梁理论 / 指示函数模型 / 单进程上限）",
         start="1. Immersed-body load reconstruction", end="the shared development node under load.",
         resolution="resolved_in_source",
         note="局限清单原文；与 A21/A22 互为交叉引用，不重复登记缺陷本体"),
    dict(asset_id="A26", asset_class="table", label="判定汇总表（5 条判据：WITHHELD / 部分通过 / 机制实现并验证）",
         start="| 判据 | 结果 | 数字 |", end="| 能量守恒误差 <5% |",
         resolution="resolved_in_source",
         note="逐条判据结论表；本工序只登记结论标签与数字出处，不改变判定"),
    dict(asset_id="A27", asset_class="external_reference", label="外部颤振文献参考值表（声明离线不可得）",
         start="No external table could be consulted", end="not as a pass.",
         trim_start=True, resolution="declared_absent",
         check="declared_absent",
         note="报告声明离线环境无法查阅外部表，颤振速度仅对闭式解与其解析极限验证；全文无 URL/DOI 可供解析（见 integrity.external_reference_scan）"),
    dict(asset_id="A28", asset_class="reproduce_commands", label="复现命令块（pytest 4 个测试文件 + fsi_ladder_run theodorsen/dfg + 出图）",
         start="```bash", end="python scripts/fsi_ladder_figures.py",
         resolution="resolved_in_source",
         note="locator 覆盖 ```bash 起至最后一条命令（不含收尾围栏）；所调脚本属 TensorFEM 仓（A06，未解析），本工序未执行它们"),
    dict(asset_id="A29", asset_class="honest_disclaimer", label="诚实声明（未达成 FSI-2 振幅/频率、VIV 锁定与 Theodorsen 跨方法 3%）",
         start="诚实声明：本节点未达成", end=None,
         resolution="resolved_in_source",
         note="不可覆盖为通过的自我声明；与 A22/A26 一致"),
]

URL_DOI_RE = re.compile(r"(https?://\S+|doi:\s*\S+|10\.[0-9]{4,}/\S+)")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def line_offsets(md: str):
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def find_line(lines, anchor: str) -> int:
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise SystemExit("anchor %r matched %d lines: %s" % (anchor, len(hits), hits[:5]))
    return hits[0]


def build_locator(md, lines, offs, start, end, substring=False, trim_start=False):
    if substring:
        if end is not None:
            raise SystemExit("substring locator takes a single anchor")
        n = md.count(start)
        if n != 1:
            raise SystemExit("substring anchor %r occurs %d times" % (start, n))
        s0 = md.find(start)
        li = md.count("\n", 0, s0)
        return dict(method="char_span", start_char=s0, end_char=s0 + len(start),
                    start_line=li, end_line=li + start.count("\n"), quote=start, unique=True)
    if start is None:  # whole document
        return dict(method="document", start_char=0, end_char=len(md), start_line=0,
                    end_line=md.count("\n", 0, len(md) - 1), quote=md, unique=True)
    i = find_line(lines, start)
    j = i if end is None else find_line(lines, end)
    if j < i:
        raise SystemExit("end anchor %r before start anchor %r" % (end, start))
    s, e = offs[i], offs[j] + len(lines[j])
    if trim_start:  # cut the leading fragment of the first line so the quote starts at the anchor
        k = md.find(start, offs[i], offs[i] + len(lines[i]))
        if k < 0:
            raise SystemExit("trim_start anchor not on its own line? %r" % start)
        s = k
    quote = md[s:e]
    return dict(method="char_span", start_char=s, end_char=e, start_line=i, end_line=j,
                quote=quote, unique=(md.count(quote) == 1))


def resolution_check(spec, worktree, payload, md):
    kind = spec.get("check") or ("char_span" if spec["resolution"] == "resolved_in_source" else "path_lookup")
    if kind == "char_span":
        return dict(check="char_span_in_source_markdown (verbatim, unique substring)",
                    result="resolved")
    if kind == "platform_figures":
        figs = (payload or {}).get("figures", []) or []
        return dict(check="platform_api_figures_field (GET /tensor/reports/9091)",
                    result="present" if figs else "absent",
                    platform_figures_count=len(figs),
                    detail="payload.figures carries name+caption only, no image binary")
    if kind == "declared_absent":
        hits = sorted(set(m.group(0) for m in URL_DOI_RE.finditer(md)))
        return dict(check="url_doi_scan_in_markdown", result="absent" if not hits else "present",
                    matches_found=hits[:10],
                    detail="报告声明离线不可查阅外部表；全文检索 URL/DOI 结果如上，无外部表可解析地址")
    found, missing = [], []
    for p in spec.get("paths", []):
        (found if (worktree / p).exists() else missing).append(p)
    return dict(check="worktree_path_lookup (repo root=%s; relative paths as written in the report)" % worktree,
                result="resolved" if found and not missing else "unresolved",
                paths_checked=spec.get("paths", []), paths_found=found, paths_missing=missing,
                detail="报告为仓库相对路径，指向 TensorFEM 的源码/工件；本仓检出内不存在" if missing else
                       "路径在本仓检出内存在")


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.loads((RUN_DIR / ("report_%s.json" % REPORT_ID)).read_text())
    md = (RUN_DIR / ("report_%s.md" % REPORT_ID)).read_text()

    md_hash = sha256_text(md)
    if md_hash != EXPECTED_HASH:
        print("FATAL: markdown sha256 %s != contract source_hash %s" % (md_hash, EXPECTED_HASH))
        return 2

    lines, offs = line_offsets(md)
    worktree = pathlib.Path(".").resolve()

    assets, seen = [], set()
    for spec in ASSETS:
        if spec["asset_id"] in seen:
            raise SystemExit("duplicate asset_id %s" % spec["asset_id"])
        seen.add(spec["asset_id"])
        loc = build_locator(md, lines, offs, spec["start"], spec["end"], spec.get("substring", False),
                            spec.get("trim_start", False))
        if not loc["unique"]:
            raise SystemExit("quote not unique for %s (anchor %r)" % (spec["asset_id"], spec["start"]))
        head = "(document)"
        for ln in lines[: loc["start_line"]]:
            if ln.startswith("#"):
                head = ln.strip()
        assets.append(dict(
            asset_id=spec["asset_id"],
            asset_class=spec["asset_class"],
            label=spec["label"],
            in_report_section=head,
            locator=loc,
            resolution=spec["resolution"],
            resolution_check=resolution_check(spec, worktree, payload, md),
            note=spec["note"],
        ))

    classes, res = {}, {}
    for a in assets:
        classes[a["asset_class"]] = classes.get(a["asset_class"], 0) + 1
        res[a["resolution"]] = res.get(a["resolution"], 0) + 1

    url_hits = sorted(set(m.group(0) for m in URL_DOI_RE.finditer(md)))
    manifest = dict(
        schema="asset_manifest.v1",
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        source=dict(
            uri=SOURCE_URI,
            field=SOURCE_FIELD,
            hash_alg="sha256",
            hash=md_hash,
            chars=len(md),
            bytes_utf8=len(md.encode()),
            title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            platform_id=payload.get("id"),
            platform_mission_id=payload.get("mission_id"),
            platform_status=payload.get("status"),
            platform_figures=payload.get("figures", []),
            platform_tags=payload.get("tags", []),
            contract_chars=10060,
            chars_match_contract=(len(md) == 10060),
            retrieved_via="GET %s/tensor/reports/%s" % (
                os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/"), REPORT_ID),
            retrieved_by="scripts/kf_fetch_report.py",
            local_copy=str(RUN_DIR / ("report_%s.md" % REPORT_ID)),
        ),
        counts=dict(assets=len(assets), by_class=classes, by_resolution=res,
                    resolved_in_source=res.get("resolved_in_source", 0),
                    referenced_unresolved=res.get("referenced_unresolved", 0),
                    declared_absent=res.get("declared_absent", 0)),
        assets=assets,
        claims=[],
        claims_note=("工作包契约 objective.classify_report_type=false 且 notes 允许 claims 为空数组："
                     "本工序只登记资产与其定位，不做 claim 抽取/分类；抽取由下游工序负责，"
                     "故此处亦不存在被标为 verified 的断言。"),
        integrity=dict(
            quote_uniqueness="all %d quotes confirmed unique verbatim substrings of the source markdown "
                             "(scripts/kf_verify_wp9091_01.py, checks.source_locator_resolvable)" % len(assets),
            hash_recomputed_locally=True,
            hash_matches_contract=True,
            external_reference_scan=dict(patterns_scanned=["http(s)://", "doi:", "10.xxxx/"],
                                         matches=url_hits,
                                         note="报告无 URL/DOI，故外部文献参考值只能登记为 declared_absent"),
            verification_status="not_verified",
            verification_note="verification 由平台门计算；本工序不自标 verified",
        ),
    )

    # durable mirror of the source markdown (push gate strips runs/): lets the verifier and the
    # pytest suite re-check hash + locators from a clean checkout without platform access.
    md_mirror = DOC_DIR / ("report_%s.md" % REPORT_ID)
    md_mirror.write_bytes(md.encode())
    if sha256_text(md_mirror.read_text()) != EXPECTED_HASH:
        print("FATAL: markdown mirror hash mismatch")
        return 4

    art = ART_DIR / "asset_manifest.json"
    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    art.write_text(blob)
    mirror = DOC_DIR / "asset_manifest.json"
    mirror.write_text(blob)
    art_hash = hashlib.sha256(art.read_bytes()).hexdigest()
    if hashlib.sha256(mirror.read_bytes()).hexdigest() != art_hash:
        print("FATAL: durable mirror differs from artifact")
        return 3

    outputs_manifest = dict(artifact_path=str(art), artifact_sha256=art_hash,
                            artifact_bytes=art.stat().st_size)
    outputs_manifest.update({k: v for k, v in manifest.items()})

    result = dict(
        schema_version="kf_result.v1",
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        provenance=dict(
            source_uri=SOURCE_URI,
            source_field=SOURCE_FIELD,
            source_hash="sha256:" + md_hash,
            source_chars=len(md),
            source_bytes_utf8=len(md.encode()),
            source_title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            contract_version="1.0",
            lane="C",
            work_package=PACKAGE_ID,
            retrieved_via=manifest["source"]["retrieved_via"],
            local_copy=manifest["source"]["local_copy"],
            generator="scripts/kf_register_wp9091_01.py",
            verifier="scripts/kf_verify_wp9091_01.py",
            verification_status="not_verified",
        ),
        outputs={"asset_manifest.json": outputs_manifest},
    )

    (RUN_DIR / "kf_result.wp-9091-01.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (RUN_DIR / "kf_result_block.wp-9091-01.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (DOC_DIR / "kf_result.wp-9091-01.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print("markdown sha256:", md_hash, "MATCH" if md_hash == EXPECTED_HASH else "MISMATCH")
    print("chars:", len(md), "bytes:", len(md.encode()))
    print("assets:", len(assets), "by_class:", json.dumps(classes, ensure_ascii=False))
    print("by_resolution:", json.dumps(res, ensure_ascii=False))
    print("manifest:", art, art_hash)
    print("result:", RUN_DIR / "kf_result.wp-9091-01.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())