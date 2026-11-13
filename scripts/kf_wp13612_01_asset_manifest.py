#!/usr/bin/env python3
"""Knowledge-Factory work package wp-13612-01 — task_type 01-asset-registration.

Contract scope (verbatim): "登记源资产：确认 report_id 与其 markdown 的字节哈希，
列出可解析的附件/工件，不做抽取。claims 允许为空数组。"

Three things only:
  1. pin the source: report 13612's ``markdown`` field, sha256 over UTF-8 bytes, compared
     with the contract hash (byte-identical snapshot kept in the tree);
  2. inventory the assets the report points at (document, sections, tables, operator spec,
     training config, metric definition, the external artifact/code/test paths, the 5
     figures with their fetched-payload digests, run-output tokens), each with a verbatim
     single-occurrence locator (char span + line range + quote);
  3. emit ``asset_manifest.json`` + the ``kf_result.v1`` envelope, then verify both.

No claim extraction (``claims: []`` is the contract-permitted complete result), no report
classification, nothing stamped ``verified``, no writes outside ``docs/kf/wp-13612-01/``.

Usage::

    python3 scripts/kf_wp13612_01_asset_manifest.py --fetch          # refresh md snapshot
    python3 scripts/kf_wp13612_01_asset_manifest.py --fetch-figures  # refresh figure payloads
    python3 scripts/kf_wp13612_01_asset_manifest.py                  # rebuild offline
    python3 scripts/kf_wp13612_01_asset_manifest.py --verify         # re-check outputs
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(HERE, "docs", "kf", "wp-13612-01")
SNAPSHOT = os.path.join(OUTDIR, "source", "report_13612.md")
FIGDIR = os.path.join(OUTDIR, "figures")
FIGFETCH = os.path.join(OUTDIR, "figure_fetch.json")
MANIFEST = os.path.join(OUTDIR, "asset_manifest.json")
RESULT = os.path.join(OUTDIR, "kf_result.json")
SELFCHECK = os.path.join(OUTDIR, "selfcheck.json")

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
ENVELOPE_SCHEMA = os.path.join(HERE, "schemas", "kf_result.v1.schema.json")

CONTRACT = {
    "package_id": "wp-13612-01",
    "task_type": "01-asset-registration",
    "report_id": "13612",
    "source_uri": "tensor://reports/13612",
    "source_field": "markdown",
    "source_hash": "sha256:85bbae874e9babb342a5d216c19e00265dcc108115d6dcb53f1991af48846888",
    "title": "物理信息神经算子（FNO）船体阻力/耐波实时代理模型（P284W3-N09）",
    "scenario_key": "p284w3-n09-fno-surrogate",
    "chars": 5526,
    "lane": "C",
}
FIGURES_ENDPOINT = "/tensor/reports/13612/figures/{name}"

# ---------------------------------------------------------------------------
# asset inventory (declarative; every quote is checked verbatim + unique)
# resolution: resolved_in_source | referenced_unresolved | declared_absent
# ---------------------------------------------------------------------------
ASSETS = [
    dict(asset_id="A01", asset_class="report_document", in_report_section="document",
         label="report 13612 markdown as a whole (5526 chars / 9350 UTF-8 bytes)",
         quote="# 物理信息神经算子（FNO）船体阻力/耐波实时代理模型（P284W3-N09）",
         method="document", resolution="resolved_in_source",
         check="sha256(markdown utf8) vs contract source_hash", result="resolved",
         note="document-level locator = [0, len(markdown)); quote is the title line (unique)"),
    dict(asset_id="A02", asset_class="section", in_report_section="§1",
         label="§1 案例介绍 (background / data sources / parameter table / operator form)",
         quote="## 1. 案例介绍", resolution="resolved_in_source",
         check="heading present verbatim", result="resolved", note="section heading"),
    dict(asset_id="A03", asset_class="section", in_report_section="§2",
         label="§2 方法 (architecture / physics constraints / training / error metric)",
         quote="## 2. 方法", resolution="resolved_in_source",
         check="heading present verbatim", result="resolved", note="section heading"),
    dict(asset_id="A04", asset_class="section", in_report_section="§3",
         label="§3 计算结果 (criteria table / per-split errors / extrapolation bounds)",
         quote="## 3. 计算结果", resolution="resolved_in_source",
         check="heading present verbatim", result="resolved", note="section heading"),
    dict(asset_id="A05", asset_class="section", in_report_section="§4",
         label="§4 结果图 (collective pointer to the 5 embedded figures)",
         quote="## 4. 结果图", resolution="resolved_in_source",
         check="heading present verbatim", result="resolved", note="section heading"),
    dict(asset_id="A06", asset_class="section", in_report_section="§5",
         label="§5 注意点与局限 (5 numbered limitation items)",
         quote="## 5. 注意点与局限", resolution="resolved_in_source",
         check="heading present verbatim", result="resolved", note="section heading"),
    dict(asset_id="A07", asset_class="section", in_report_section="§6",
         label="§6 误差判定（逐项，显式回答）— criterion-vs-measured table + honest-FAIL statement",
         quote="## 6. 误差判定（逐项，显式回答）", resolution="resolved_in_source",
         check="heading present verbatim", result="resolved", note="section heading"),
    dict(asset_id="A08", asset_class="artifact_path", in_report_section="§1.2",
         label="dataset artifact artifacts/p284w3_n09_fno/dataset.npz (digest truncated to 16 hex)",
         quote="数据集：`artifacts/p284w3_n09_fno/dataset.npz`（sha256 `a778060b577942ed`），训练域",
         resolution="referenced_unresolved",
         check="worktree lookup of repo-relative path + digest length check", result="unresolved",
         note="path is relative to the producing repo (not named in the report); digest is a "
              "16-hex prefix so the payload cannot be hash-pinned from this record. Not copied, "
              "not re-generated."),
    dict(asset_id="A09", asset_class="code_path", in_report_section="§1.2",
         label="label kernel backend/api/domain/resistance_holtrop.py (sha256 prefix 27ba0a9b2664)",
         quote="| `C_T, R_T` | `backend/api/domain/resistance_holtrop.py` |",
         resolution="referenced_unresolved",
         check="worktree lookup of repo-relative path + digest length check", result="unresolved",
         note="12-hex prefix only; no repo/commit identity in the report"),
    dict(asset_id="A10", asset_class="code_path", in_report_section="§1.2",
         label="label kernel backend/api/seakeeping_physics.py (sha256 prefix 307afd4d2f65)",
         quote="| `RAO_φ, RAO_z` | `backend/api/seakeeping_physics.py` |",
         resolution="referenced_unresolved",
         check="worktree lookup of repo-relative path + digest length check", result="unresolved",
         note="12-hex prefix only; no repo/commit identity in the report"),
    dict(asset_id="A11", asset_class="code_path", in_report_section="§2.1",
         label="FNO implementation src/neural_operators/field_operator.py",
         quote="FNO（`src/neural_operators/field_operator.py`）：lift → ×4（SpectralConv2d +",
         resolution="referenced_unresolved",
         check="worktree lookup of repo-relative path", result="unresolved",
         note="no digest and no commit identity inside report 13612"),
    dict(asset_id="A12", asset_class="test_path", in_report_section="§5 item 1",
         label="regression test test_input_tensor_channels_and_mask, named as the §5-1 regression guard",
         quote="回归防护：`test_input_tensor_channels_and_mask` + 数据集清单登记特征定义。",
         resolution="referenced_unresolved",
         check="test-name lookup inside this worktree", result="unresolved",
         note="test name only: no file path, no suite/commit identity"),
    dict(asset_id="A13", asset_class="table", in_report_section="§1.2",
         label="label-source table (kernel, method, evidence grade, source sha256 prefix per target)",
         quote="| 标签 | 内核 | 方法与证据等级 | 源码 sha256（前 12 位） |",
         resolution="resolved_in_source", check="table header present verbatim", result="resolved",
         note="4 columns, 2 data rows (C_T/R_T and RAO_z/RAO_φ)"),
    dict(asset_id="A14", asset_class="table", in_report_section="§1.3",
         label="sampling-domain parameter table (L, Fr, L/B, β, B/T, GM/B, Cb, KG/T, Cwp, λ/L)",
         quote="| L | 60–320 m（对数均匀） | Fr | 0.08–0.40（外推 0.40–0.55） |",
         resolution="resolved_in_source", check="table row present verbatim", result="resolved",
         note="sampled ranges incl. extrapolation ranges"),
    dict(asset_id="A15", asset_class="operator_input_spec", in_report_section="§1.4",
         label="operator input field spec: u(x,z), 24 channels, 16x4 grid, 18 non-dimensional conditions",
         quote="输入场 `u(x,z)`（24 通道，网格 16×4）：逐站剖面面积比 `A(x)/(B·T)`、淹没掩膜、半宽比",
         resolution="resolved_in_source", check="spec sentence present verbatim", result="resolved",
         note="names the field channels; the remaining channels continue on the next lines"),
    dict(asset_id="A16", asset_class="gate_predicate", in_report_section="§1.2",
         label="geometry pre-check: buoyancy identity, max deviation 3.3e-16",
         quote="`3.3e-16`（浮力守恒），Cb·L·B·T 与排水量自洽。",
         resolution="resolved_in_source", check="sentence present verbatim", result="resolved",
         note="the report's own geometry-verification evidence (∫(A/(B·T))dx = Cb); not re-run here"),
    dict(asset_id="A17", asset_class="physics_constraint_spec", in_report_section="§2.2",
         label="hard constraint #3: RAO_φ ∝ |sin β|, exact 0 at β=0/180°, residual <1e-12",
         quote="3. 对称性：`RAO_φ ∝ |sin β|`（β=0/180° 恒为 0，float64 计算后残差 <1e-12）；",
         resolution="resolved_in_source", check="list item present verbatim", result="resolved",
         note="one of the four by-construction exact constraints"),
    dict(asset_id="A18", asset_class="training_config", in_report_section="§2.3",
         label="ensemble config: 2-member deep ensemble (log-space mean + member std σ)",
         quote="60，**2 成员深度集成**（对数空间均值 + 成员标准差 σ）；",
         resolution="resolved_in_source", check="config sentence present verbatim", result="resolved",
         note="preceded by AdamW lr=0.006/wd=0.0001, cosine, batch 64, epochs 60"),
    dict(asset_id="A19", asset_class="metric_definition", in_report_section="§2.4",
         label="MAPE definition with floor = 0.02 × training-set median, plus strict_mape_pct",
         quote="`mape_pct = mean |Δ|/max(|truth|, floor)×100`，`floor = 0.02 × 训练集中位数`",
         resolution="resolved_in_source", check="definition present verbatim", result="resolved",
         note="the report's error-yardstick declaration; every §3/§6 percentage depends on this floor"),
    dict(asset_id="A20", asset_class="table", in_report_section="§3.1",
         label="criteria table row (b) test-set R_T <5% → 6.36% FAIL",
         quote="| (b) 测试集 R_T | <5% | 6.36% | FAIL |",
         resolution="resolved_in_source", check="table row present verbatim", result="resolved",
         note="criterion row carried with its FAIL verdict unchanged"),
    dict(asset_id="A21", asset_class="table", in_report_section="§3.1",
         label="criteria table row (a) train-set R_T <3% → 4.49% FAIL",
         quote="| (a) 训练集 R_T | <3% | 4.49% | FAIL |",
         resolution="resolved_in_source", check="table row present verbatim", result="resolved",
         note="the only criterion naming a 3% threshold; registered so no downstream 工序 lifts it"),
    dict(asset_id="A22", asset_class="table", in_report_section="§3.1",
         label="criteria table row (d) CPU latency <10 ms → median 6.65 ms (p95 9.63 ms) PASS",
         quote="| (d) 单点推理时延（CPU） | <10 ms | 中位 6.65 ms（p95 9.63 ms） | PASS |",
         resolution="resolved_in_source", check="table row present verbatim", result="resolved",
         note="one of the two PASS criteria (with (c), which the source itself downgrades)"),
    dict(asset_id="A23", asset_class="table", in_report_section="§3.2",
         label="per-split error table, extrapolation row (R_T / RAO_z / RAO_φ, strict in parentheses)",
         quote="| 外推集（Fr>0.4 或 β>60°） | 28.67% (28.68%) | 43191.09% (66933.87%) | 107215.54% (586642.06%) |",
         resolution="resolved_in_source", check="table row present verbatim", result="resolved",
         note="extrapolation errors of 1e4–1e5 % are the source's own numbers"),
    dict(asset_id="A24", asset_class="table", in_report_section="§3.3",
         label="extrapolation-bound table, RAO_z row (q 18.70→55.7%; 4553709.86→90.0%; width inf)",
         quote="| RAO_z | 18.70（55.7%） | 4553709.86（90.0%） | inf（inf=区间宽度不可度量，模型外推无信息量） |",
         resolution="resolved_in_source", check="table row present verbatim", result="resolved",
         note="records the q magnitudes that make criterion (c) a weak pass"),
    dict(asset_id="A25", asset_class="table", in_report_section="§3.3",
         label="interpolation-limit control experiment, n_train=1600 row (plain MLP surrogate)",
         quote="| 1600 | 2.81e-02 / 8.01e-02 / 7.39e-02 | 13.5% | 54.5% | 55.6% | 3.44 |",
         resolution="resolved_in_source", check="table row present verbatim", result="resolved",
         note="control-experiment row (the n=640 row is the line above)"),
    dict(asset_id="A26", asset_class="run_output_token", in_report_section="§3.3",
         label="empirical sample-size scaling for R_T: e∝n^(-0.30), 3.0% needs ~233404 samples",
         quote="标度 e∝n^(-0.30)；按此外推达 3.0% 需 ~233404 样本",
         resolution="resolved_in_source", check="token present verbatim", result="resolved",
         note="derived number quoted only; not recomputed by this package"),
    dict(asset_id="A27", asset_class="run_output_token", in_report_section="§2.3",
         label="training wall clock 1302.0 s (local CPU, oversubscribed host)",
         quote="1302.0 s（本地 CPU，宿主机 load ≫ 核数，非最优算力）。",
         resolution="resolved_in_source", check="token present verbatim", result="resolved",
         note="no run id / log file referenced by the report"),
    dict(asset_id="A28", asset_class="table", in_report_section="§6",
         label="§6 error-judgement row R_T (test set): threshold <5%, measured 6.36%, answer 否",
         quote="| R_T（测试集） | 同上 | <5% | 6.36% | **否** |",
         resolution="resolved_in_source", check="table row present verbatim", result="resolved",
         note="the source answers 否; this package stamps nothing as verified"),
    dict(asset_id="A29", asset_class="self_declared_non_pass", in_report_section="§6",
         label="honest-FAIL declaration for criteria (a)(b)",
         quote="**honest FAIL 声明**：判据 (a)(b) 的精度阈值本节点**未达成**，上述 FAIL 不做任何粉饰；",
         resolution="resolved_in_source", check="declaration present verbatim", result="resolved",
         note="carried verbatim so no downstream step lifts it to a pass"),
    dict(asset_id="A30", asset_class="self_declared_non_pass", in_report_section="§3.1",
         label="weak-pass caveat for criterion (c): coverage 89.3% only with q≈1e6-scale intervals",
         quote="因此 (c) 属**弱通过**：PICP 单独不足以证明外推可用，必须同时报告区间宽度（表中已列，量级 1e6）。",
         resolution="resolved_in_source", check="caveat present verbatim", result="resolved",
         note="the report downgrades its own PASS to weak; preserved"),
    dict(asset_id="A31", asset_class="limitation_item", in_report_section="§5 item 1",
         label="dimensional-frequency bug (ω·√(L/g) vs ω/√(gL)) found and fixed; RAO error 100%→61%",
         quote="1. **量纲错误（本节点踩到并修正）**：无因次频率必须是 `ω·√(L/g)`，不是 `ω/√(gL)`。",
         resolution="resolved_in_source", check="list item present verbatim", result="resolved",
         note="registered as a reusable trap; not re-verified here"),
    dict(asset_id="A32", asset_class="limitation_item", in_report_section="§5 item 3",
         label="interpolation-limit limitation (≥10-dim input space, thousand-scale samples sparse)",
         quote="3. **插值极限（关键局限）**：输入为 ≥10 维无因次群，千级样本在 10 维空间里仍属稀疏——对照",
         resolution="resolved_in_source", check="list item present verbatim", result="resolved",
         note="basis of the 1e5–1e6 sample-count estimate"),
    dict(asset_id="A33", asset_class="limitation_item", in_report_section="§5 item 4",
         label="label-kernel ceiling: Holtrop ±5–10%, STF 2D coefficients analytic approximations",
         quote="4. **训练标签是回归/切片理论内核**（Holtrop ±5–10%；STF 2D 系数为解析近似），因此本代理的",
         resolution="resolved_in_source", check="list item present verbatim", result="resolved",
         note="no experimental benchmark was performed by the source node (its own words)"),
]

FIGURE_SPECS = [
    ("A34", "fig1_parity", "预测-真值一致性（测试集 vs 外推集，含误差带）"),
    ("A35", "fig2_error_vs_condition", "外推域相对误差随 Fr / 浪向 β 的分布"),
    ("A36", "fig3_uncertainty", "外推域 conformal 区间覆盖与各目标覆盖率"),
    ("A37", "fig4_fields", "内部场：几何输入 → 阻力密度场 → 散度残差"),
    ("A38", "fig5_training", "集成成员训练曲线（数据+物理损失）"),
]
FIG_QUOTE = "见 figures（内嵌 PNG）：parity、误差-工况、外推覆盖、内部场、训练曲线。"

OBSERVATIONS = [
    {
        "observation_id": "13612-o000",
        "kind": "digest_not_verifiable",
        "description": ("All upstream digests quoted in the report are truncated prefixes: dataset 16 hex "
                        "(a778060b577942ed), the two kernel sources 12 hex (27ba0a9b2664 / 307afd4d2f65). "
                        "None can be checked against a payload from here, so those paths are registered "
                        "reference-only; this package neither re-hashes nor re-generates them."),
        "quotes": ["数据集：`artifacts/p284w3_n09_fno/dataset.npz`（sha256 `a778060b577942ed`），训练域",
                   "| `C_T, R_T` | `backend/api/domain/resistance_holtrop.py` |",
                   "| `RAO_φ, RAO_z` | `backend/api/seakeeping_physics.py` |"],
        "assigned_status": "unresolved",
        "unresolved_reason": "digest truncated inside report 13612; full sha256 unavailable",
    },
    {
        "observation_id": "13612-o001",
        "kind": "provenance_gap",
        "description": ("Upstream paths are repo-relative (backend/…, src/…, artifacts/…) but report 13612 "
                        "names no repository, branch, commit or run id; the training wall clock has no run "
                        "id either. Those paths cannot be hash-pinned to a commit from this record, so they "
                        "are textual references with present_in_worktree=false (this worktree is "
                        "TensorKnowledge and holds none of the five referenced paths)."),
        "quotes": ["FNO（`src/neural_operators/field_operator.py`）：lift → ×4（SpectralConv2d +",
                   "1302.0 s（本地 CPU，宿主机 load ≫ 核数，非最优算力）。"],
        "assigned_status": "unresolved",
        "unresolved_reason": "no commit identity and no full-length digest inside report 13612",
    },
    {
        "observation_id": "13612-o002",
        "kind": "figure_name_mapping",
        "description": ("The markdown names the figures only collectively by caption fragments, while the "
                        "record `figures` field supplies fig1…fig5 file names. The 5↔5 pairing used here is "
                        "by order/caption semantics; each payload was nevertheless fetched and hashed "
                        "individually, so every figure asset is bound to its own sha256."),
        "quotes": [FIG_QUOTE],
        "assigned_status": "supported",
        "note": "name↔caption pairing inferred; payload digest is the authoritative binding",
    },
    {
        "observation_id": "13612-o003",
        "kind": "self_declared_non_pass_rows",
        "description": ("The source itself reports FAIL for criteria (a)(b) and calls criterion (c) a weak "
                        "pass with q≈1e6-scale intervals. Statuses are registered unchanged; this package "
                        "computes nothing and marks nothing verified."),
        "quotes": ["**honest FAIL 声明**：判据 (a)(b) 的精度阈值本节点**未达成**，上述 FAIL 不做任何粉饰；",
                   "因此 (c) 属**弱通过**：PICP 单独不足以证明外推可用，必须同时报告区间宽度（表中已列，量级 1e6）。"],
        "assigned_status": "unresolved",
        "unresolved_reason": "kept exactly as the source states it (FAIL / weak pass)",
    },
]


# ---------------------------------------------------------------------------
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def char_locator(md: str, quote: str, method: str = "char_span") -> dict:
    n = md.count(quote)
    if n != 1:
        raise SystemExit(f"quote must occur exactly once (found {n}): {quote[:80]!r}")
    start = md.find(quote)
    end = start + len(quote)
    return {"method": method, "start_char": start, "end_char": end,
            "start_line": md.count("\n", 0, start) + 1,
            "end_line": md.count("\n", 0, end - 1) + 1,
            "quote": quote, "unique": True}


def api_call(path: str, body: dict | None = None, tok: str | None = None, timeout: int = 60):
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def login() -> str:
    st, body = api_call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                        "password": os.environ["TENSOR_AGENT_PASS"]})
    if st != 200:
        raise SystemExit(f"login failed: {st} {body[:300]!r}")
    return json.loads(body)["access_token"]


def fetch_source() -> dict:
    tok = login()
    st, body = api_call(f"/tensor/reports/{CONTRACT['report_id']}", tok=tok)
    if st != 200:
        raise SystemExit(f"GET report failed: {st} {body[:300]!r}")
    rec = json.loads(body)
    md = rec["markdown"]
    os.makedirs(os.path.dirname(SNAPSHOT), exist_ok=True)
    with open(SNAPSHOT, "w", encoding="utf-8") as fh:
        fh.write(md)
    meta = {"report_id": rec["id"], "title": rec["title"],
            "scenario_key": rec["scenario_key"],
            "platform_tags": rec.get("tags", []), "platform_figures": rec.get("figures", []),
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "chars": len(md), "bytes_utf8": len(md.encode("utf-8")),
            "sha256": sha256_bytes(md.encode("utf-8"))}
    with open(os.path.join(OUTDIR, "source_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print(f"fetched report {rec['id']}: {len(md)} chars, sha256 {meta['sha256']}")
    return meta


def fetch_figures() -> dict:
    tok = login()
    os.makedirs(FIGDIR, exist_ok=True)
    out = {}
    for _aid, name, caption in FIGURE_SPECS:
        st, payload = api_call(FIGURES_ENDPOINT.format(name=name), tok=tok)
        entry = {"name": name, "caption": caption, "method": "GET",
                 "endpoint": FIGURES_ENDPOINT.format(name=name), "http_status": st}
        if st == 200 and payload:
            path = os.path.join(FIGDIR, f"{name}.png")
            with open(path, "wb") as fh:
                fh.write(payload)
            entry.update({"bytes": len(payload), "sha256": sha256_bytes(payload),
                          "png_magic_ok": payload[:8] == b"\x89PNG\r\n\x1a\n",
                          "local_copy": os.path.relpath(path, HERE), "resolvable": True})
        else:
            entry.update({"resolvable": False,
                          "error_body": payload[:200].decode("utf-8", "replace")})
        out[name] = entry
        print(name, st, entry.get("bytes"), (entry.get("sha256") or "")[:16], entry.get("resolvable"))
    with open(FIGFETCH, "w", encoding="utf-8") as fh:
        json.dump({"report_id": CONTRACT["report_id"],
                   "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "figures": out}, fh, ensure_ascii=False, indent=1)
    return out


def load_figures() -> dict:
    if not os.path.exists(FIGFETCH):
        raise SystemExit("figure_fetch.json missing — run with --fetch-figures first")
    return json.load(open(FIGFETCH, encoding="utf-8"))["figures"]


def load_source() -> tuple[str, dict]:
    with open(SNAPSHOT, encoding="utf-8") as fh:
        md = fh.read()
    mp = os.path.join(OUTDIR, "source_meta.json")
    meta = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
    return md, meta


# ---------------------------------------------------------------------------
def build() -> dict:
    md, meta = load_source()
    md_bytes = md.encode("utf-8")
    digest = sha256_bytes(md_bytes)
    expected = CONTRACT["source_hash"].split(":", 1)[1]
    if digest != expected:
        raise SystemExit(f"source hash mismatch: {digest} != {expected}")
    if len(md) != CONTRACT["chars"]:
        raise SystemExit(f"chars mismatch: {len(md)} != {CONTRACT['chars']}")
    if meta:
        if meta.get("title") != CONTRACT["title"]:
            raise SystemExit("title mismatch vs contract")
        if meta.get("scenario_key") != CONTRACT["scenario_key"]:
            raise SystemExit("scenario_key mismatch vs contract")

    figs = load_figures()
    assets = []
    for spec in ASSETS:
        assets.append({
            "asset_id": spec["asset_id"],
            "asset_class": spec["asset_class"],
            "label": spec["label"],
            "in_report_section": spec["in_report_section"],
            "locator": char_locator(md, spec["quote"], spec.get("method", "char_span")),
            "resolution": spec["resolution"],
            "resolution_check": {"check": spec["check"], "result": spec["result"]},
            "note": spec["note"],
        })

    fig_loc = char_locator(md, FIG_QUOTE)
    for aid, name, caption in FIGURE_SPECS:
        e = figs.get(name, {})
        ok = bool(e.get("resolvable"))
        assets.append({
            "asset_id": aid,
            "asset_class": "figure",
            "label": f"figure {name} — {caption} (record `figures` entry; markdown names it only collectively)",
            "in_report_section": "§4",
            "locator": dict(fig_loc),
            "resolution": "resolved_in_source" if ok else "declared_absent",
            "resolution_check": {
                "check": f"GET {FIGURES_ENDPOINT.format(name=name)} → http status + sha256(payload)",
                "result": "resolved" if ok else "absent",
                "http_status": e.get("http_status"),
                "bytes": e.get("bytes"),
                "payload_sha256": ("sha256:" + e["sha256"]) if e.get("sha256") else None,
                "png_magic_ok": e.get("png_magic_ok"),
                "local_copy": e.get("local_copy"),
                "declared_name_from_record": name,
                "declared_caption_from_record": caption,
            },
            "note": ("payload fetched and hashed by this package (binary not re-rendered); the markdown "
                     "mention is the collective §4 sentence, hence the shared locator"),
        })

    ids = [a["asset_id"] for a in assets]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate asset ids")

    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    quotes_checked = len(assets) + sum(len(o.get("quotes", [])) for o in OBSERVATIONS)
    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "report_id": CONTRACT["report_id"],
        "lane": CONTRACT["lane"],
        "source": {
            "uri": CONTRACT["source_uri"], "field": CONTRACT["source_field"],
            "hash_alg": "sha256", "hash": digest,
            "chars": len(md), "bytes_utf8": len(md_bytes),
            "title": meta.get("title", CONTRACT["title"]),
            "scenario_key": meta.get("scenario_key", CONTRACT["scenario_key"]),
            "snapshot": os.path.relpath(SNAPSHOT, HERE),
            "platform_tags": meta.get("platform_tags", []),
            "platform_figures": meta.get("platform_figures", []),
        },
        "assets": assets,
        "observations": OBSERVATIONS,
        "counts": {
            "assets": len(assets), "by_class": by_class, "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "claims_registered": 0,
        },
        "claims": [],
        "claims_note": ("task_type 01 registers no knowledge claims; the empty array is the "
                        "contract-permitted complete result (constraint no_forced_claim_generation). "
                        "The report's numbers are locatable through the assets above but are NOT "
                        "extracted here and NOT marked verified."),
        "integrity": {
            "hash_recomputed_locally": "sha256:" + digest,
            "hash_matches_contract": True,
            "chars_match_contract": True,
            "quote_uniqueness": {"quotes_checked": quotes_checked,
                                 "verbatim_ok": quotes_checked,
                                 "unique_ok": quotes_checked,
                                 "spans_rechecked": True},
            "asset_ids_unique": True,
            "claims_registered": 0,
            "nothing_marked_verified": True,
            "envelope_schema": os.path.relpath(ENVELOPE_SCHEMA, HERE),
        },
        "repro_cmd": ("python3 scripts/kf_wp13612_01_asset_manifest.py && "
                      "python3 scripts/kf_wp13612_01_asset_manifest.py --verify && "
                      "python3 -m pytest tests/test_kf_wp13612_01_asset_registration.py -q"),
        "tools": {"generator": "scripts/kf_wp13612_01_asset_manifest.py",
                  "python": sys.version.split()[0]},
    }

    envelope = {
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "report_id": CONTRACT["report_id"],
        "provenance": {
            "source_hash": CONTRACT["source_hash"],
            "source_field": CONTRACT["source_field"],
            "producer": "agent/m15765 (TensorKnowledge) · wp-13612-01",
            "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "notes": ("markdown snapshot pinned at " + os.path.relpath(SNAPSHOT, HERE) +
                      "; sha256 recomputed locally and equal to the contract hash"),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    os.makedirs(OUTDIR, exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    with open(RESULT, "w", encoding="utf-8") as fh:
        json.dump(envelope, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"wrote {os.path.relpath(MANIFEST, HERE)} ({len(assets)} assets, "
          f"{quotes_checked} quotes) and {os.path.relpath(RESULT, HERE)}")
    return manifest


# ---------------------------------------------------------------------------
def verify() -> dict:
    from jsonschema import Draft202012Validator

    checks: dict[str, object] = {}
    md, _meta = load_source()
    digest = sha256_bytes(md.encode("utf-8"))
    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    envelope = json.load(open(RESULT, encoding="utf-8"))

    # both committed artifacts parsed as JSON above, so valid_json is a real check, not a claim
    checks["valid_json"] = isinstance(manifest, dict) and isinstance(envelope, dict)
    checks["source_hash_matches_contract"] = digest == CONTRACT["source_hash"].split(":", 1)[1]
    checks["chars_match_contract"] = len(md) == CONTRACT["chars"]
    checks["envelope_source_hash"] = envelope["provenance"]["source_hash"] == CONTRACT["source_hash"]
    checks["envelope_report_id"] = envelope["report_id"] == CONTRACT["report_id"]
    checks["envelope_task_type"] = envelope["task_type"] == CONTRACT["task_type"]
    checks["envelope_package_id"] = envelope["package_id"] == CONTRACT["package_id"]

    env_schema = json.load(open(ENVELOPE_SCHEMA, encoding="utf-8"))
    errs = sorted(Draft202012Validator(env_schema).iter_errors(envelope), key=lambda e: list(e.path))
    checks["schema_pass"] = not errs
    checks["schema_errors"] = [f"{list(e.path)}: {e.message}" for e in errs][:5]

    # manifest invariants (no separate schema file: the platform's canonical envelope
    # schema above is the gate; these are the manifest-level invariants it cannot see)
    ids = [a["asset_id"] for a in manifest["assets"]]
    checks["no_duplicate_ids"] = len(ids) == len(set(ids))
    checks["outputs_has_asset_manifest"] = "asset_manifest.json" in envelope["outputs"]
    checks["outputs_equal_committed_manifest"] = envelope["outputs"]["asset_manifest.json"] == manifest
    checks["claims_empty_as_permitted"] = manifest["claims"] == []

    bad_spans, nonverbatim, nonunique = [], [], []
    for a in manifest["assets"]:
        loc = a["locator"]
        span_ok = md[loc["start_char"]:loc["end_char"]] == loc["quote"]
        verb = loc["quote"] in md
        uniq = md.count(loc["quote"]) == 1
        if not span_ok:
            bad_spans.append(a["asset_id"])
        if not verb:
            nonverbatim.append(a["asset_id"])
        if not uniq:
            nonunique.append(a["asset_id"])
    for o in manifest["observations"]:
        for q in o.get("quotes", []):
            if q not in md:
                nonverbatim.append(o["observation_id"])
            if md.count(q) != 1:
                nonunique.append(o["observation_id"])
    checks["source_locator_resolvable"] = not bad_spans
    checks["locator_span_mismatch"] = bad_spans
    checks["all_quotes_verbatim"] = not nonverbatim
    checks["quote_not_verbatim"] = nonverbatim
    checks["all_quotes_unique"] = not nonunique
    checks["quote_not_unique"] = nonunique

    # every asset carries either a resolution or an explicit unresolved note
    missing = [a["asset_id"] for a in manifest["assets"]
               if a["resolution"] == "referenced_unresolved" and not a.get("note")]
    checks["all_assets_have_evidence_or_unresolved_status"] = not missing

    # every claim (none here) must carry evidence or an explicit status; empty => vacuously ok
    bad_claims = [c.get("claim_id") for c in manifest["claims"] + envelope["claims"]
                  if not c.get("evidence") and not c.get("status")]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = not bad_claims

    # nothing may be marked verified anywhere
    blob = json.dumps(envelope, ensure_ascii=False).lower()
    checks["nothing_marked_verified"] = '"verified"' not in blob and "status\": \"verified" not in blob

    # figure payloads re-hashed from the committed local copies
    fig_ok, fig_bad = 0, []
    for a in manifest["assets"]:
        if a["asset_class"] != "figure":
            continue
        rc = a["resolution_check"]
        local = rc.get("local_copy")
        path = os.path.join(HERE, local) if local else None
        if path and os.path.exists(path):
            got = "sha256:" + sha256_bytes(open(path, "rb").read())
            if got == rc.get("payload_sha256"):
                fig_ok += 1
            else:
                fig_bad.append(a["asset_id"])
        else:
            fig_bad.append(a["asset_id"])
    checks["figure_payloads_rehashed_ok"] = fig_ok
    checks["figure_payload_mismatch"] = fig_bad
    checks["figures_all_resolvable"] = not fig_bad

    checks["counts_consistent"] = (manifest["counts"]["assets"] == len(manifest["assets"]) and
                                   manifest["counts"]["assets"] == sum(
                                       manifest["counts"]["by_resolution"].values()))

    failures = [k for k, v in checks.items() if v is False]
    checks["FAILURES"] = failures
    checks["ok"] = not failures
    with open(SELFCHECK, "w", encoding="utf-8") as fh:
        json.dump(checks, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(json.dumps({k: v for k, v in checks.items() if k != "FAILURES"}, ensure_ascii=False, indent=1))
    print("VERIFY", "PASS" if checks["ok"] else f"FAIL {failures}")
    return checks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="refresh the markdown snapshot from the API")
    ap.add_argument("--fetch-figures", action="store_true", help="refresh figure payloads from the API")
    ap.add_argument("--verify", action="store_true", help="re-check committed outputs")
    args = ap.parse_args()
    if args.fetch:
        fetch_source()
    if args.fetch_figures:
        fetch_figures()
    if args.verify:
        checks = verify()
        raise SystemExit(0 if checks["ok"] else 1)
    if not (args.fetch or args.fetch_figures):
        build()


if __name__ == "__main__":
    main()