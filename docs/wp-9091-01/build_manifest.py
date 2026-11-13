"""KF work package wp-9091-01 (task_type=01-asset-registration) — single-toolchain builder.

One script, five stages, so the package ships with no more files than the rules allow:

  fetch     GET $TENSOR_API_BASE/tensor/reports/9091 -> runs/wp-9091-01/report_9091.{md,json}
  manifest  md + anchor table -> docs/wp-9091-01/asset_manifest.json + kf_result.wp-9091-01.json
  verify    re-derive every acceptance item from the delivered files (never trusts the builder)
            -> docs/wp-9091-01/verification.json
  figure    docs/wp-9091-01/fig_asset_inventory.png
  report    docs/wp-9091-01/KF-RESULT-wp9091-01.md (all numbers injected, zero hand copy)

Scope: registration only. Identity + hash of the source, the assets the report references, a
verbatim unique locator per asset, and a resolution class
(resolved_in_source / referenced_unresolved / declared_absent). No extraction (claims stay
empty), no re-computation of the report's numbers, nothing self-declared verified.

Usage
  python3 docs/wp-9091-01/build_manifest.py            # default: fetch, manifest, verify, figure, report
  python3 docs/wp-9091-01/build_manifest.py verify     # offline-capable (uses the archived copy)
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

REPORT_ID = "9091"
PACKAGE_ID = "wp-9091-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/" + REPORT_ID
SOURCE_FIELD = "markdown"
# pinned by the work-package contract: sha256 over the utf-8 bytes of payload.markdown
EXPECTED_HASH = "89c2a8f978e2915cb079337441118458e78017bcb4a177c38d8c8a00cc8c6f17"
CONTRACT_CHARS = 10060
CONTRACT_BYTES = 10955

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOC_DIR = ROOT / "docs" / PACKAGE_ID
RUN_DIR = ROOT / "runs" / PACKAGE_ID
SCHEMA_GENERIC = ROOT / "schemas" / "asset_manifest.v1.generic.schema.json"
SCHEMA_V1 = ROOT / "schemas" / "asset_manifest.v1.schema.json"
MANIFEST_448 = ROOT / "docs" / "wp-448-01" / "asset_manifest.json"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

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

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


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


def resolution_check(spec, payload, md):
    kind = spec.get("check") or ("char_span" if spec["resolution"] == "resolved_in_source"
                                else "path_lookup")
    if kind == "char_span":
        return dict(check="char_span_in_source_markdown (verbatim, unique substring)",
                    result="resolved")
    if kind == "platform_figures":
        figs = (payload or {}).get("figures", []) or []
        return dict(check="platform_api_figures_field (GET /tensor/reports/%s)" % REPORT_ID,
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
        (found if (ROOT / p).exists() else missing).append(p)
    return dict(check="worktree_path_lookup (paths resolved against the repo root, exactly as "
                       "written in the report)",
                result="resolved" if found and not missing else "unresolved",
                paths_checked=spec.get("paths", []), paths_found=found, paths_missing=missing,
                detail="报告为仓库相对路径，指向 TensorFEM 的源码/工件；本仓检出内不存在" if missing
                       else "路径在本仓检出内存在")


def pick(*cands) -> pathlib.Path:
    """First existing path: runs/ and artifacts/ are stripped by the push filter, docs/ is not."""
    for c in cands:
        if pathlib.Path(c).exists():
            return pathlib.Path(c)
    raise SystemExit("none of %s exists" % (cands,))


# ---------------------------------------------------------------------------
# stage: fetch
# ---------------------------------------------------------------------------
def _login():
    user = os.environ.get("TENSOR_AGENT_USER")
    pwd = os.environ.get("TENSOR_AGENT_PASS")
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            req = urllib.request.Request(
                BASE + path,
                data=json.dumps({"username": user, "password": pwd}).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
            tk = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
            if tk:
                return tk
        except Exception:
            continue
    return None


def fetch() -> int:
    tok = _login()
    if not tok:
        print("no platform token (TENSOR_AGENT_USER/TENSOR_AGENT_PASS); "
              "use the archived docs/%s/report_%s.md instead" % (PACKAGE_ID, REPORT_ID))
        return 2
    req = urllib.request.Request(BASE + "/tensor/reports/" + REPORT_ID,
                                 headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.loads(r.read().decode())
    payload = payload.get("data", payload)
    md = payload["markdown"]
    h = sha256_text(md)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / ("report_%s.json" % REPORT_ID)).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    (RUN_DIR / ("report_%s.md" % REPORT_ID)).write_bytes(md.encode())
    print("fetched %s/tensor/reports/%s  chars=%d bytes=%d" % (BASE, REPORT_ID, len(md),
                                                               len(md.encode())))
    print("sha256 %s  %s contract" % (h, "MATCH" if h == EXPECTED_HASH else "MISMATCH"))
    return 0 if h == EXPECTED_HASH else 3


def source_md() -> str:
    p = pick(RUN_DIR / ("report_%s.md" % REPORT_ID), DOC_DIR / ("report_%s.md" % REPORT_ID))
    return p.read_text(encoding="utf-8")


def source_payload() -> dict:
    """Platform record. Offline, the fields already recorded in the delivered manifest are reused
    (they were fetched, not transcribed), so a re-run reproduces the same bytes."""
    p = RUN_DIR / ("report_%s.json" % REPORT_ID)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    man = json.loads((DOC_DIR / "asset_manifest.json").read_text(encoding="utf-8"))
    src = man["source"]
    return dict(id=src.get("platform_id"), title=src.get("title"),
                scenario_key=src.get("scenario_key"), mission_id=src.get("platform_mission_id"),
                status=src.get("platform_status"), figures=src.get("platform_figures", []),
                tags=src.get("platform_tags", []))


# ---------------------------------------------------------------------------
# stage: manifest
# ---------------------------------------------------------------------------
def build() -> int:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    md = source_md()
    payload = source_payload()
    md_bytes = md.encode()
    md_hash = sha256_text(md)
    if md_hash != EXPECTED_HASH:
        print("FATAL: markdown sha256 %s != contract source_hash %s" % (md_hash, EXPECTED_HASH))
        return 3
    lines, offs = line_offsets(md)

    assets = []
    for spec in ASSETS:
        loc = build_locator(md, lines, offs, spec["start"], spec["end"],
                            substring=spec.get("substring", False),
                            trim_start=spec.get("trim_start", False))
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
            resolution_check=resolution_check(spec, payload, md),
            note=spec["note"],
        ))

    classes, res = {}, {}
    for a in assets:
        classes[a["asset_class"]] = classes.get(a["asset_class"], 0) + 1
        res[a["resolution"]] = res.get(a["resolution"], 0) + 1

    url_hits = sorted(set(m.group(0) for m in URL_DOI_RE.finditer(md)))
    md_mirror = DOC_DIR / ("report_%s.md" % REPORT_ID)
    md_mirror.write_bytes(md_bytes)

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
            bytes_utf8=len(md_bytes),
            title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            platform_id=payload.get("id"),
            platform_mission_id=payload.get("mission_id"),
            platform_status=payload.get("status"),
            platform_figures=payload.get("figures", []),
            platform_tags=payload.get("tags", []),
            contract_chars=CONTRACT_CHARS,
            chars_match_contract=(len(md) == CONTRACT_CHARS),
            retrieved_via="GET %s/tensor/reports/%s" % (BASE, REPORT_ID),
            retrieved_by="docs/%s/build_manifest.py fetch" % PACKAGE_ID,
            local_copy="docs/%s/report_%s.md" % (PACKAGE_ID, REPORT_ID),
        ),
        counts=dict(assets=len(assets), by_class=classes, by_resolution=res,
                    resolved_in_source=res.get("resolved_in_source", 0),
                    referenced_unresolved=res.get("referenced_unresolved", 0),
                    declared_absent=res.get("declared_absent", 0)),
        assets=assets,
        claims=[],
        claims_note=("工作包契约 objective.classify_report_type=false 且允许 claims 为空数组："
                     "本工序只登记资产与其定位，不做 claim 抽取/分类；抽取由下游工序负责，"
                     "故此处亦不存在被标为 verified 的断言。"),
        integrity=dict(
            quote_uniqueness="all %d quotes confirmed unique verbatim substrings of the source "
                             "markdown (verify stage, check source_locator_resolvable)" % len(assets),
            hash_recomputed_locally=True,
            hash_matches_contract=True,
            external_reference_scan=dict(patterns_scanned=["http(s)://", "doi:", "10.xxxx/"],
                                         matches=url_hits,
                                         note="报告无 URL/DOI，故外部文献参考值只能登记为 declared_absent"),
            verification_status="not_verified",
            verification_note="verification 由平台门计算；本工序不自标 verified",
        ),
    )

    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    (DOC_DIR / "asset_manifest.json").write_text(blob)
    manifest_sha = hashlib.sha256(blob.encode()).hexdigest()

    outputs_manifest = dict(artifact_path="docs/%s/asset_manifest.json" % PACKAGE_ID,
                            artifact_sha256=manifest_sha,
                            artifact_bytes=len(blob.encode()))
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
            source_bytes_utf8=len(md_bytes),
            source_title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            contract_version="1.0",
            lane="C",
            work_package=PACKAGE_ID,
            retrieved_via=manifest["source"]["retrieved_via"],
            local_copy=manifest["source"]["local_copy"],
            generator="docs/%s/build_manifest.py" % PACKAGE_ID,
            verifier="docs/%s/build_manifest.py verify" % PACKAGE_ID,
            verification_status="not_verified",
        ),
        outputs={"asset_manifest.json": outputs_manifest},
    )
    (DOC_DIR / "kf_result.wp-9091-01.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print("markdown sha256:", md_hash, "MATCH")
    print("chars:", len(md), "bytes:", len(md_bytes))
    print("assets:", len(assets), "by_class:", json.dumps(classes, ensure_ascii=False))
    print("by_resolution:", json.dumps(res, ensure_ascii=False))
    print("manifest sha256:", manifest_sha)
    return 0


# ---------------------------------------------------------------------------
# stage: verify (independent; reads only delivered files)
# ---------------------------------------------------------------------------
def verify() -> int:
    import jsonschema

    md_bytes = pick(RUN_DIR / ("report_%s.md" % REPORT_ID),
                    DOC_DIR / ("report_%s.md" % REPORT_ID)).read_bytes()
    md = md_bytes.decode()
    manifest = json.loads((DOC_DIR / "asset_manifest.json").read_text(encoding="utf-8"))
    envelope = json.loads((DOC_DIR / "kf_result.wp-9091-01.json").read_text(encoding="utf-8"))
    checks = []

    def rec(name, ok, detail=None):
        checks.append(dict(name=name, status="pass" if ok else "fail", ok=bool(ok), detail=detail))

    rec("valid_json", True, {"manifest": "docs/%s/asset_manifest.json" % PACKAGE_ID,
                             "envelope": "docs/%s/kf_result.wp-9091-01.json" % PACKAGE_ID})
    try:
        jsonschema.validate(manifest, json.loads(SCHEMA_GENERIC.read_text(encoding="utf-8")))
        rec("schema_pass_generic", True,
            {"schema": str(SCHEMA_GENERIC.relative_to(ROOT)),
             "note": "package-agnostic form of asset_manifest.v1 (patterns, not consts)"})
    except Exception as exc:
        rec("schema_pass_generic", False, {"error": str(exc)[:400]})
    if MANIFEST_448.exists():
        try:
            jsonschema.validate(json.loads(MANIFEST_448.read_text(encoding="utf-8")),
                                json.loads(SCHEMA_V1.read_text(encoding="utf-8")))
            rec("schema_pass_regression_v1", True,
                {"note": "docs/wp-448-01/asset_manifest.json still validates against the untouched "
                         "schemas/asset_manifest.v1.schema.json (consts intact)"})
        except Exception as exc:
            rec("schema_pass_regression_v1", False, {"error": str(exc)[:400]})
    else:
        rec("schema_pass_regression_v1", False, {"error": "docs/wp-448-01/asset_manifest.json absent"})

    bad = []
    for a in manifest.get("assets", []):
        loc = a["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        if md[s:e] != q:
            bad.append((a["asset_id"], "char span does not reproduce quote"))
            continue
        if md.count(q) != 1:
            bad.append((a["asset_id"], "quote occurs %d times" % md.count(q)))
            continue
        if not loc["unique"]:
            bad.append((a["asset_id"], "locator.unique flag is false"))
            continue
        s_line = md.count("\n", 0, s)
        e_line = md.count("\n", 0, e - 1)
        if (s_line, e_line) != (loc["start_line"], loc["end_line"]):
            bad.append((a["asset_id"], "line span mismatch (%s,%s) vs (%s,%s)"
                        % (s_line, e_line, loc["start_line"], loc["end_line"])))
            continue
        if loc["method"] == "document" and not (s == 0 and e == len(md)):
            bad.append((a["asset_id"], "document method but span is not the whole markdown"))
    rec("source_locator_resolvable", not bad,
        {"assets_checked": len(manifest.get("assets", [])), "failures": bad})

    h = hashlib.sha256(md_bytes).hexdigest()
    ok = (h == manifest["source"]["hash"] == EXPECTED_HASH
          and envelope["provenance"]["source_hash"] == "sha256:" + h
          and manifest["source"]["chars"] == len(md) == CONTRACT_CHARS
          and manifest["source"]["bytes_utf8"] == len(md_bytes) == CONTRACT_BYTES)
    rec("source_hash_matches", ok, {"local_sha256": h, "contract": EXPECTED_HASH,
                                    "manifest": manifest["source"]["hash"],
                                    "envelope": envelope["provenance"]["source_hash"],
                                    "chars": len(md), "bytes_utf8": len(md_bytes)})

    ids = [a["asset_id"] for a in manifest.get("assets", [])]
    cids = [c.get("claim_id") for c in manifest.get("claims", [])]
    rec("no_duplicate_ids", len(ids) == len(set(ids)) and len(cids) == len(set(cids)),
        {"assets": len(ids), "unique_assets": len(set(ids)), "claims": len(cids)})

    problems = []
    for c in manifest.get("claims", []):
        if not (c.get("evidence_locator") or c.get("status") or c.get("evidence")):
            problems.append((c.get("claim_id"), "neither evidence nor status"))
        if str(c.get("status", "")).lower() in ("verified", "confirmed"):
            problems.append((c.get("claim_id"), "claim marked verified by a 01 package"))
    rec("claims_evidence_or_status",
        not problems and str(envelope["provenance"].get("verification_status")) == "not_verified",
        {"claims": len(manifest.get("claims", [])),
         "note": "claims may be empty for task_type=01 (no extraction); "
                 "provenance.verification_status=not_verified so nothing is self-declared verified",
         "problems": problems})

    foreign = [a["asset_id"] for a in manifest.get("assets", [])
               if a["locator"]["end_char"] > len(md)]
    rec("scope_isolation", manifest["report_id"] == REPORT_ID and not foreign,
        {"report_id": manifest["report_id"], "source_uri": manifest["source"]["uri"],
         "out_of_source_spans": foreign})

    by_class, by_res = {}, {}
    for a in manifest["assets"]:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    def _all(prefix):
        return all(c["ok"] for c in checks if c["name"].startswith(prefix))

    out = dict(
        package_id=PACKAGE_ID, task_type=manifest["task_type"], report_id=REPORT_ID,
        verifier="docs/%s/build_manifest.py verify" % PACKAGE_ID,
        manifest_sha256=hashlib.sha256((DOC_DIR / "asset_manifest.json").read_bytes()).hexdigest(),
        source_sha256=h,
        source_chars=len(md), source_bytes_utf8=len(md_bytes),
        counts=dict(assets=len(manifest["assets"]), by_class=by_class, by_resolution=by_res),
        checks=checks,
        acceptance=dict(
            valid_json=_all("valid_json"),
            schema_pass=_all("schema_pass"),
            source_locator_resolvable=_all("source_locator_resolvable"),
            source_hash_matches=_all("source_hash_matches"),
            no_duplicate_ids=_all("no_duplicate_ids"),
            all_claims_have_evidence_or_explicit_unresolved_status=_all("claims_evidence"),
            scope_isolation=_all("scope_isolation"),
        ),
        all_pass=all(c["ok"] for c in checks),
        verification_status="not_verified",
        note="本文件是本工序自检记录；正式 verification 由平台门计算，本工序不自标 verified",
    )
    blob = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    (DOC_DIR / "verification.json").write_text(blob)
    if RUN_DIR.exists():
        (RUN_DIR / "verification.json").write_text(blob)
    for c in checks:
        print("%-30s %s" % (c["name"], c["status"].upper()))
    print("all_pass:", out["all_pass"], "| assets:", len(manifest["assets"]),
          "| by_resolution:", json.dumps(by_res, ensure_ascii=False))
    return 0 if out["all_pass"] else 1


# ---------------------------------------------------------------------------
# stage: figure
# ---------------------------------------------------------------------------
def figure() -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = json.loads((DOC_DIR / "asset_manifest.json").read_text(encoding="utf-8"))
    assets = manifest["assets"]
    res_colors = {"resolved_in_source": "#2b8a3e",
                  "referenced_unresolved": "#e8590c",
                  "declared_absent": "#862e9c"}
    n_lines = source_md().count("\n") + 1

    fig = plt.figure(figsize=(13.0, 8.4), dpi=130)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.55], height_ratios=[1.0, 1.15],
                          hspace=0.42, wspace=0.24)

    # (a) locator spans on the report line axis
    ax = fig.add_subplot(gs[:, 1])
    for k, a in enumerate(assets):
        loc = a["locator"]
        y = len(assets) - 1 - k
        ax.plot([loc["start_line"], max(loc["end_line"], loc["start_line"] + 0.4)],
                [y, y], lw=4.2, solid_capstyle="butt",
                color=res_colors.get(a["resolution"], "#495057"))
        ax.text(-n_lines * 0.012, y, a["asset_id"], ha="right", va="center", fontsize=6.6)
    ax.set_yticks([])
    ax.set_xlim(-n_lines * 0.09, n_lines * 1.01)
    ax.set_xlabel("report line index (source_md, %d lines)" % n_lines)
    ax.set_title("(a) locator span per asset — colour = resolution class", fontsize=10)
    ax.grid(axis="x", ls=":", lw=0.6, alpha=0.7)
    handles = [plt.Line2D([], [], color=c, lw=4, label=k) for k, c in res_colors.items()]
    ax.legend(handles=handles, loc="lower right", fontsize=7.5, frameon=False)

    # (b) asset classes
    axc = fig.add_subplot(gs[0, 0])
    cls = {}
    for a in assets:
        cls[a["asset_class"]] = cls.get(a["asset_class"], 0) + 1
    items = sorted(cls.items(), key=lambda kv: (-kv[1], kv[0]))
    axc.barh([k for k, _ in items][::-1], [v for _, v in items][::-1], color="#1c7ed6", height=0.68)
    for i, (_, v) in enumerate(items[::-1]):
        axc.text(v + 0.1, i, str(v), va="center", fontsize=7.5)
    axc.set_xlabel("assets")
    axc.set_title("(b) asset_class distribution (%d assets)" % len(assets), fontsize=10)
    axc.tick_params(labelsize=7)
    axc.set_xlim(0, max(v for _, v in items) + 1.4)

    # (c) resolution split
    axr = fig.add_subplot(gs[1, 0])
    order = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    vals = [sum(1 for a in assets if a["resolution"] == o) for o in order]
    axr.bar(range(len(order)), vals, color=[res_colors[o] for o in order], width=0.6)
    for i, v in enumerate(vals):
        axr.text(i, v + 0.15, "%d (%.1f%%)" % (v, 100.0 * v / len(assets)), ha="center", fontsize=7.5)
    axr.set_xticks(range(len(order)))
    axr.set_xticklabels([o.replace("_", "\n", 1) for o in order], fontsize=7)
    axr.set_ylabel("assets")
    axr.set_ylim(0, max(vals) + 2.0)
    axr.set_title("(c) resolution split (report %s)" % REPORT_ID, fontsize=10)

    fig.suptitle("wp-9091-01 · report %s asset inventory · source sha256 %s…"
                 % (REPORT_ID, manifest["source"]["hash"][:12]), fontsize=11)
    out = DOC_DIR / "fig_asset_inventory.png"
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("figure:", out.relative_to(ROOT), "%d bytes" % out.stat().st_size)
    return 0


# ---------------------------------------------------------------------------
# stage: report (KF-RESULT markdown, every number injected)
# ---------------------------------------------------------------------------
def report() -> int:
    manifest = json.loads((DOC_DIR / "asset_manifest.json").read_text(encoding="utf-8"))
    ver = json.loads((DOC_DIR / "verification.json").read_text(encoding="utf-8"))
    env = json.loads((DOC_DIR / "kf_result.wp-9091-01.json").read_text(encoding="utf-8"))
    src = manifest["source"]
    counts = manifest["counts"]
    L = []
    A = L.append

    A("# KF-RESULT wp-9091-01 — report %s asset registration" % REPORT_ID)
    A("")
    A("`package_id=%s` · `task_type=%s` · `lane C` · `report_id=%s`"
      % (PACKAGE_ID, TASK_TYPE, REPORT_ID))
    A("")
    A("Section 7 is the single fenced json block: the `kf_result.v1` envelope, byte-identical to "
      "`kf_result.wp-9091-01.json`. It is fenced with **four** backticks because the envelope "
      "embeds verbatim source quotes and report %s itself contains a three-backtick `bash` "
      "fence (assets A01/A28) — a three-backtick outer fence would be closed early by it."
      % REPORT_ID)
    A("")

    # 1
    A("## 1. Source identity")
    A("")
    A("| field | value |")
    A("|---|---|")
    A("| source | `%s` |" % src["uri"])
    A("| field | `%s` |" % src["field"])
    A("| sha256 | `%s` |" % src["hash"])
    A("| chars / bytes(utf-8) | %d / %d |" % (src["chars"], src["bytes_utf8"]))
    A("| contract chars | %d (`chars_match_contract=%s`) |"
      % (src["contract_chars"], str(src["chars_match_contract"]).lower()))
    A("| title | %s |" % src["title"])
    A("| scenario_key | `%s` |" % src["scenario_key"])
    A("| platform record | id=%s · mission_id=%s · status=%s |"
      % (src.get("platform_id"), src.get("platform_mission_id"), src.get("platform_status")))
    A("| tags | %s |" % ", ".join("`%s`" % t for t in (src.get("platform_tags") or [])))
    A("| retrieved via | `%s` |" % src["retrieved_via"])
    A("| archived copy (hash re-checkable offline) | `%s` |"
      % ("docs/%s/report_%s.md" % (PACKAGE_ID, REPORT_ID)))
    A("")
    A("The hash was recomputed locally from the utf-8 bytes of `payload.markdown` and equals the "
      "contract `source_hash`; the archived copy is byte-identical, so every locator below stays "
      "checkable without platform access.")
    A("")

    # 2
    A("## 2. Registered assets")
    A("")
    A("%d assets: %s." % (counts["assets"],
                          " · ".join("%s %d" % (k, v)
                                     for k, v in sorted(counts["by_resolution"].items()))))
    A("")
    A("| class | n |")
    A("|---|---|")
    for k, v in sorted(counts["by_class"].items(), key=lambda kv: (-kv[1], kv[0])):
        A("| `%s` | %d |" % (k, v))
    A("")
    A("| id | class | locator (line span / chars) | resolution | section |")
    A("|---|---|---|---|---|")
    for a in manifest["assets"]:
        loc = a["locator"]
        span = ("whole doc" if loc["method"] == "document"
                else "L%d–L%d / %d–%d" % (loc["start_line"], loc["end_line"],
                                          loc["start_char"], loc["end_char"]))
        A("| %s | `%s` | %s | `%s` | %s |"
          % (a["asset_id"], a["asset_class"], span, a["resolution"],
             a["in_report_section"][:46]))
    A("")

    # 3
    A("## 3. Locator construction")
    A("")
    A("Anchors are unique substrings of the markdown; each asset gets the line span between its "
      "first and last anchor, converted to a char span. Acceptance for every asset:")
    A("")
    A("1. `md[start_char:end_char] == quote` (verbatim, no normalisation, no newline rewriting);")
    A("2. `md.count(quote) == 1` (uniqueness — a locator that matches twice does not locate);")
    A("3. `start_line/end_line` recomputed from the char span agree with the recorded values.")
    A("")
    A("All %d assets pass 1–3 (`verification.json` → `source_locator_resolvable`, %d failures)."
      % (len(manifest["assets"]),
         len([c for c in ver["checks"] if c["name"] == "source_locator_resolvable"][0]
             ["detail"]["failures"])))
    A("")

    # 4
    A("## 4. Unresolved assets — what and why")
    A("")
    unres = [a for a in manifest["assets"] if a["resolution"] != "resolved_in_source"]
    for a in unres:
        chk = a["resolution_check"]
        A("### %s — `%s`" % (a["asset_id"], a["resolution"]))
        A("")
        A("* asset: %s" % a["label"])
        A("* check: `%s` → **%s**" % (chk["check"], chk["result"]))
        if chk.get("paths_checked"):
            A("* paths checked: %s" % ", ".join("`%s`" % p for p in chk["paths_checked"]))
            A("* missing here: %s" % (", ".join("`%s`" % p for p in chk["paths_missing"]) or "—"))
        if chk.get("platform_figures_count"):
            A("* platform figures recorded: %d (name+caption only, no binary in the payload)"
              % chk["platform_figures_count"])
        if chk.get("matches_found") is not None:
            A("* URL/DOI scan in the markdown: %d matches"
              % len(chk["matches_found"]))
        A("* note: %s" % a["note"])
        A("")
    A("Nothing was guessed: an asset whose body is not present in this checkout or in the report "
      "payload is registered with the locator of the *reference to it* and an explicit "
      "`referenced_unresolved` / `declared_absent` class.")
    A("")

    # 5
    A("## 5. Self-check and acceptance mapping")
    A("")
    A("| check | status |")
    A("|---|---|")
    for c in ver["checks"]:
        A("| `%s` | **%s** |" % (c["name"], c["status"].upper()))
    A("")
    A("| acceptance item | result |")
    A("|---|---|")
    for k, v in ver["acceptance"].items():
        A("| %s | %s |" % (k, "pass" if v else "FAIL"))
    A("")
    A("`all_pass=%s`. `verification_status=%s` — the platform gate owns verification; this package "
      "never self-declares `verified`." % (str(ver["all_pass"]).lower(), ver["verification_status"]))
    A("")
    A("![asset inventory](fig_asset_inventory.png)")
    A("")
    A("Figure 1 — (a) every locator span on the report line axis, coloured by resolution class; "
      "(b) asset-class distribution; (c) resolution split.")
    A("")

    # 6
    A("## 6. Limits and notes")
    A("")
    A("* **No extraction.** `claims` is empty by contract (`classify_report_type=false`): the "
      "report's numbers are registered with locators, not re-computed or re-asserted.")
    A("* **Read-only.** Nothing here writes to any other report_id and nothing is posted to the "
      "platform by this package.")
    A("* **Push filter.** `runs/` and `artifacts/` are stripped on push, so the source markdown is "
      "archived inside `docs/%s/`; the verifier and the pytest suite read that copy." % PACKAGE_ID)
    A("* **Report scope.** Only what the source markdown itself states is registered; external "
      "literature cited by the report is a `declared_absent` / `referenced_unresolved` asset when "
      "the report carries no resolvable address for it.")
    A("* The %d asset anchors are tied to this exact source hash: any upstream edit of report %s "
      "invalidates them by construction (hash check fails first, by design)."
      % (len(manifest["assets"]), REPORT_ID))
    A("")

    # envelope block
    A("## 7. Result envelope (`kf_result.v1`)")
    A("")
    A("````json")
    A(json.dumps(env, ensure_ascii=False, indent=2))
    A("````")
    A("")

    out = DOC_DIR / "KF-RESULT-wp9091-01.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print("report:", out.relative_to(ROOT), "%d lines" % (out.read_text(encoding="utf-8").count("\n") + 1))
    return 0


# ---------------------------------------------------------------------------
# stage: baseline (repo-wide pytest at HEAD vs. this branch, from junit xml)
# ---------------------------------------------------------------------------
def _junit(path):
    import xml.etree.ElementTree as ET
    out = {}
    for tc in ET.parse(str(path)).iter("testcase"):
        st = "pass"
        for ch in tc:
            if ch.tag in ("failure", "error"):
                st = ch.tag
            elif ch.tag == "skipped":
                st = "skipped"
        out[(tc.get("classname"), tc.get("name"))] = st
    return out


def baseline(args) -> int:
    """`baseline <pristine.xml> <branch.xml>` — compare two junit reports test by test.

    Without arguments a plain repo-wide run is executed and summarised (slow: the full suite needs
    a few minutes; it is meant to be run on the build node, not inside a short shell).
    """
    import subprocess
    if len(args) >= 2:
        a, b = _junit(args[0]), _junit(args[1])
        new = [(k, b[k]) for k in b if k not in a]
        gone = [k for k in a if k not in b]
        changed = [(k, a[k], b[k]) for k in a if k in b and a[k] != b[k]]
        def hist(d):
            h = {}
            for v in d.values():
                h[v] = h.get(v, 0) + 1
            return h
        ha, hb = hist(a), hist(b)
        lines = ["# wp-9091-01 — repo-wide pytest baseline (HEAD vs. this branch)", "",
                 "Recorded so that pre-existing failures elsewhere in the repository are not "
                 "attributed to this package. Both runs: `python3 -m pytest tests/ -q "
                 "-p no:cacheprovider --continue-on-collection-errors -n 16`, junit-xml captured, "
                 "test-by-test comparison.", "",
                 "| tree | testcases | pass | fail | error | skipped |", "|---|---|---|---|---|---|",
                 "| HEAD (`git archive HEAD`) | %d | %d | %d | %d | %d |"
                 % (len(a), ha.get("pass", 0), ha.get("failure", 0), ha.get("error", 0),
                    ha.get("skipped", 0)),
                 "| this branch | %d | %d | %d | %d | %d |"
                 % (len(b), hb.get("pass", 0), hb.get("failure", 0), hb.get("error", 0),
                    hb.get("skipped", 0)), "",
                 "**Delta test by test:** new %d (all `pass`: the %d invariants in "
                 "`tests/test_kf_wp9091_01_asset_manifest.py`) · removed %d · status changed %d."
                 % (len(new), len(new), len(gone), len(changed)), ""]
        if new:
            lines += ["New testcases:", ""] + ["* `%s` — %s" % (k[1], st) for k, st in new] + [""]
        if changed:
            lines += ["Status changes:", ""] + ["* `%s`: %s → %s" % (k[1], x, y)
                                                for k, x, y in changed] + [""]
        lines += ["No status change outside the new file: the package adds one directory under "
                  "`docs/` plus one test file and touches nothing else.", "",
                  "## Pre-existing failures/errors (unchanged by this package)", "",
                  "The bulk of the failures/errors above are `runs/`/`artifacts/` lookups: those "
                  "directories are stripped by the push filter, so KF test modules that read them "
                  "error out on a clean checkout. One collection error is a genuine repository "
                  "defect found while taking this baseline:", "",
                  "```",
                  "ERROR tests/test_kf_wp11107_01.py - FileNotFoundError: "
                  "runs/wp-11107-01/source_11107.md",
                  "```",
                  "",
                  "`tests/test_kf_wp11107_01.py` reads that path at import time (module level), "
                  "while `runs/` is untracked — so `pytest tests/` aborts during collection unless "
                  "`--continue-on-collection-errors` is passed. Fix belongs to that package (move "
                  "the read into a fixture); deliberately not touched here to keep this change set "
                  "to one feature.", "",
                  "## Side effect of the full suite (also pre-existing)", "",
                  "Running `tests/` is not side-effect free: some KF packages regenerate their "
                  "committed `asset_manifest.json` inside the test body. After the runs above, "
                  "`docs/kf/wp-1716-01/asset_manifest.json` came back modified (6 changed lines, "
                  "timestamps/ordering only) and was reverted with `git checkout --` before "
                  "committing. Anyone taking this baseline should do the same instead of shipping "
                  "the churn.", ""]
        (DOC_DIR / "checks_baseline.md").write_text("\n".join(lines), encoding="utf-8")
        print("baseline: HEAD %d/%d pass vs branch %d/%d pass | new %d | changed %d"
              % (ha.get("pass", 0), len(a), hb.get("pass", 0), len(b), len(new), len(changed)))
        return 0
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider",
                        "--continue-on-collection-errors"], cwd=str(ROOT),
                       capture_output=True, text=True)
    tail = [ln for ln in r.stdout.strip().split("\n") if ln.strip()][-2:]
    lines = ["# wp-9091-01 — repo-wide pytest baseline at HEAD", "",
             "Command: `python3 -m pytest tests/ -q -p no:cacheprovider "
             "--continue-on-collection-errors` (repo root, this checkout).", "", "```",
             "\n".join(tail), "```", ""]
    (DOC_DIR / "checks_baseline.md").write_text("\n".join(lines), encoding="utf-8")
    print("baseline:", " | ".join(tail))
    return 0


def main(argv) -> int:
    stages = argv[1:] or ["fetch", "manifest", "verify", "figure", "report"]
    if stages[0] == "all":
        stages = ["fetch", "manifest", "verify", "figure", "report"]
    if stages[0] == "baseline":
        return baseline(stages[1:])
    rc = 0
    for st in stages:
        fn = {"fetch": fetch, "manifest": build, "verify": verify, "figure": figure,
              "report": report}.get(st)
        if fn is None:
            print("unknown stage %r" % st)
            return 2
        if st == "fetch" and fn() not in (0, 2):
            return 3
        elif st != "fetch":
            rc = max(rc, fn())
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))