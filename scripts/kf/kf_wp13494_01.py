#!/usr/bin/env python3
"""KF lane C · task_type=01-asset-registration · driver for wp-13494-01 (report 13494).

Why a driver instead of another entry in ``kf01_register.py:PRESETS``: the shared registrar is a
hot file that several open packages edit at the same time, so this package *reuses* it by
importing ``build / emit_result / verify / render_figure`` rather than appending to the preset
table (zero merge surface on the shared tool, and the manifest's ``producer`` block records both
the generator and this driver).

On top of the five base artefacts produced by the reusable registrar
(``asset_manifest.json``, ``kf_result.json``, ``verification.json``,
``figures/<package>_asset_locator_map.png``, ``report.md``) this package's contract asks for two
extra pieces of evidence, both emitted here from measured values (nothing hand-copied):

``determinism.json``      two independent builds, canonicalised comparison, volatile
                          timestamps named explicitly (no "byte identical" overclaim).
``published_check.json``  live platform record cross-check of report 13494 (status/title/
                          scenario_key/figure inventory/source hash + every locator re-resolved
                          against the live markdown).

``report_payload.json`` is the exact body POSTed to ``/tensor/reports``.

Usage:
  python3 scripts/kf/kf_wp13494_01.py                 # full chain, canonical order
  python3 scripts/kf/kf_wp13494_01.py build result verify figure determinism published report
"""

from __future__ import annotations

import base64
import hashlib
import json
import platform
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import kf01_register as kf  # noqa: E402  (reuse, do not fork, the lane-C registrar)

PKG = "wp-13494-01"
REPORT_ID = "13494"

#: work-package contract values for wp-13494-01 (report 13494).  expected_hash/expected_chars are
#: the contract's provenance anchor: build() refuses to emit anything if the live record disagrees.
CFG = {
    "package_id": PKG,
    "report_id": REPORT_ID,
    "expected_hash": "ad61f9e0bc3dbe8c8f4ae40ce90056f06c98477c9a33302193f8297756783abe",
    "expected_chars": 12251,
    "title": "TensorDEM GPU 100K Gate — CPU Scaling & Correctness Verification",
    "scenario_key": "p447w2-n03-dem-gpu-100k",
    "mission_id": 20520,
    "out_dir": "docs/kf/%s" % PKG,
    "producing_repo": "TensorDEM",
    # the report cites only TensorDEM paths (src/tensordem/..., tests/..., artifacts/dem_gpu_100k/...)
    # and its single figure carries no png_base64 payload -> both stay unresolved / metadata_only.
    "figure_note": (
        "红色条不是缺陷而是**边界的正确表达**：`record.figures[0]`（fig1_scaling）只有 name+caption、"
        "`png_base64` 为空，本包不伪造字节哈希，如实记 `metadata_only`（`referenced_unresolved`）。"
    ),
    "cross_repo_note": [
        "4. **跨仓引用不可解析**：报告引用的 `src/tensordem/dem_vectorized.py`、`tests/test_dem_vectorized_100k.py`、",
        "   `artifacts/dem_gpu_100k/scaling_study.json` 等属 TensorDEM 仓，本工作树（TensorKnowledge）内不存在 → 全部 `referenced_unresolved`，",
        "   并在 `resolution_check.detail` 写明原因，不做「大概存在」的推断。",
    ],
}

OUT = REPO / CFG["out_dir"]

#: fields a run must be allowed to differ in; everything else must be bit-identical content.
VOLATILE = {
    "asset_manifest.json": (("generated_at",),),
    # the envelope carries (a) its own clock and (b) the raw digest *of the manifest*, which is a
    # function of that manifest's clock - both are named here so nothing drifts silently.
    "kf_result.json": (
        ("provenance", "emitted_at"),
        ("outputs", "asset_manifest.json", "sha256"),
    ),
}


# ------------------------------------------------------------------ helpers
def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _strip(doc: dict, paths: tuple) -> dict:
    """Deep copy with each volatile path (a key tuple, so names containing dots stay unambiguous) removed."""
    import copy

    out = copy.deepcopy(doc)
    for keys in paths:
        node = out
        for k in keys[:-1]:
            node = node[k]
        node.pop(keys[-1], None)
    return out


def _normalise_envelope(env: dict, cfg: dict) -> dict:
    """Envelope copy with volatile paths removed and the run-directory path rewritten to the package path."""
    out = _strip(env, VOLATILE["kf_result.json"])
    out["outputs"]["asset_manifest.json"]["path"] = (
        "%s/asset_manifest.json" % cfg["out_dir"]
    )
    return out


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ build (+ driver stamp)
def build(cfg=CFG, out_dir=None):
    out_dir = out_dir or OUT
    kf.build(cfg, out_dir, REPO)
    mp = out_dir / "asset_manifest.json"
    manifest = _read(mp)
    manifest["producer"]["driver"] = "scripts/kf/%s.py" % Path(__file__).stem
    manifest["producer"]["driver_note"] = (
        "scripts/kf/kf01_register.py provides the scanning/locator code; this driver supplies the "
        "package contract, stamps its own identity and emits determinism.json/published_check.json."
    )
    mp.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("stamped producer.driver in %s" % mp.relative_to(REPO))
    return manifest


def result(cfg=CFG):
    return kf.emit_result(cfg, OUT)


def verify(cfg=CFG):
    return kf.verify(cfg, OUT)


def figure(cfg=CFG):
    return kf.render_figure(cfg, OUT)


# ------------------------------------------------------------------ determinism
def _single_build(tag: str, cfg: dict, tmpdirs: list) -> dict:
    """One throw-away build in its own directory (removed by the caller)."""
    tmp = Path(tempfile.mkdtemp(prefix=".kf-det-%s-" % tag, dir=REPO))
    tmpdirs.append(tmp)
    build(
        cfg, tmp
    )  # same driver path as the committed run (incl. the producer stamp), so the
    # canonical hash below is the committed manifest's hash, not a look-alike
    kf.emit_result(cfg, tmp)
    png = kf.render_figure(cfg, tmp)
    man = _read(tmp / "asset_manifest.json")
    env = _read(tmp / "kf_result.json")
    return {
        "run": tag,
        "asset_manifest_bytes_sha256": _sha256_bytes(
            (tmp / "asset_manifest.json").read_bytes()
        ),
        "asset_manifest_canonical_sha256": _sha256_bytes(
            _canonical(_strip(man, VOLATILE["asset_manifest.json"])).encode("utf-8")
        ),
        "kf_result_canonical_sha256": _sha256_bytes(
            _canonical(_normalise_envelope(env, cfg)).encode("utf-8")
        ),
        "figure_bytes_sha256": _sha256_bytes(png.read_bytes()),
        "asset_count": man["counts"]["assets"],
        "generated_at": man["generated_at"],
        "emitted_at": env["provenance"]["emitted_at"],
    }


def determinism(cfg=CFG):
    """Two isolated builds -> one canonical hash pair.  No timestamps are hidden: the two volatile
    ISO-8601 fields are named in the artefact and removed before hashing, so 'deterministic' here
    means exactly 'identical content apart from those two recorded clocks'."""
    runs, tmpdirs = [], []
    try:
        for tag in ("A", "B"):
            runs.append(_single_build(tag, cfg, tmpdirs))
    finally:
        for d in tmpdirs:
            shutil.rmtree(d, ignore_errors=True)
    a, b = runs

    def _same(key):
        return a[key] == b[key]

    invariants = {
        "asset_manifest_canonical_identical": _same("asset_manifest_canonical_sha256"),
        "kf_result_canonical_identical": _same("kf_result_canonical_sha256"),
        "figure_bytes_identical": _same("figure_bytes_sha256"),
        "asset_count_identical": _same("asset_count"),
    }
    expected_differences = {
        "asset_manifest_raw_bytes_identical": _same("asset_manifest_bytes_sha256"),
        "reason": (
            "raw bytes carry each run's build clock (generated_at) and therefore also the envelope's "
            "digest of them; both are listed in method.excluded_volatile_fields and compared after removal"
        ),
    }
    import matplotlib
    from importlib.metadata import version as _pkg_version

    doc = {
        "package_id": cfg["package_id"],
        "report_id": cfg["report_id"],
        "schema": "determinism.v1",
        "checked_at": _now(),
        "claim": "重建即同内容：两次独立构建在去掉两处时间戳后逐字段一致，图为逐字节一致。",
        "method": {
            "builds": 2,
            "isolation": (
                "each run re-logs in and re-fetches GET /api/v1/tensor/reports/%s, then builds "
                "into its own fresh temp directory; the second run does not read the first"
                % cfg["report_id"]
            ),
            "hash_gate": "both runs must reproduce contract source_hash sha256:%s (else build() aborts)"
            % cfg["expected_hash"],
            "canonicalisation": "json.dumps(sort_keys=True, separators=(',',':'), ensure_ascii=False) -> sha256",
            "excluded_volatile_fields": {
                k: [".".join(p) for p in v] for k, v in VOLATILE.items()
            },
            "normalised_fields": {
                "kf_result.outputs.asset_manifest.json.path": (
                    "rewritten to %s/asset_manifest.json: each determinism run builds into its own temp "
                    "directory by design; the committed run's value is asserted separately by "
                    "verification.json::manifest_hash_matches_envelope and published_check.json"
                    % cfg["out_dir"]
                ),
            },
            "figure_comparison": "PNG bytes compared directly (no canonicalisation, no metadata stripping)",
        },
        "source": {
            "report_id": cfg["report_id"],
            "sha256": cfg["expected_hash"],
            "chars": cfg["expected_chars"],
        },
        "runs": runs,
        "invariants": invariants,
        "expected_differences": expected_differences,
        "all_identical": all(invariants.values()),
        "verdict": (
            "deterministic: identical canonical content and byte-identical figure"
            if all(invariants.values())
            else "NOT deterministic (see invariants)"
        ),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "matplotlib": matplotlib.__version__,
            "numpy": _pkg_version("numpy"),
            "jsonschema": _pkg_version("jsonschema"),
        },
        "limitations": [
            "Raw output bytes are deliberately NOT identical: every run records its own build clock "
            "(asset_manifest.generated_at, kf_result.provenance.emitted_at). Those two fields are named "
            "above and removed before hashing; no other field may drift.",
            "Determinism is asserted for one machine/toolchain (see environment); cross-platform byte "
            "equality of matplotlib-rendered PNG is out of scope.",
            "The scan itself has no randomness (no sampling, no dict-order dependence): asset order is "
            "document order, so identical content also means identical asset_id -> span mapping.",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "determinism.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps({**invariants, **expected_differences}, ensure_ascii=False, indent=1)
    )
    return doc


# ------------------------------------------------------------------ published check
def published(cfg=CFG):
    """Cross-check the live platform record against the committed artefacts."""
    token = kf.login()
    meta, md = kf.fetch_report(token, cfg["report_id"])
    raw = md.encode("utf-8")
    manifest = _read(OUT / "asset_manifest.json")
    envelope = _read(OUT / "kf_result.json")
    src = kf.Source(md)

    def check(ok, detail):
        return {"pass": bool(ok), "detail": detail}

    checks = {
        "report_is_published": check(
            meta.get("status") == "published",
            "GET /api/v1/tensor/reports/%s -> status=%r (package registration assumes a published record)"
            % (cfg["report_id"], meta.get("status")),
        ),
        "source_hash_matches_live_record": check(
            _sha256_bytes(raw) == manifest["source"]["hash"] == cfg["expected_hash"],
            "live=%s manifest=%s contract=%s"
            % (_sha256_bytes(raw), manifest["source"]["hash"], cfg["expected_hash"]),
        ),
        "source_chars_match_live_record": check(
            len(md) == manifest["source"]["chars"] == cfg["expected_chars"],
            "live=%d manifest=%d contract=%d"
            % (len(md), manifest["source"]["chars"], cfg["expected_chars"]),
        ),
        "title_matches_live_record": check(
            meta.get("title") == manifest["source"]["title"],
            "live=%r manifest=%r" % (meta.get("title"), manifest["source"]["title"]),
        ),
        "scenario_key_matches_live_record": check(
            meta.get("scenario_key") == manifest["source"]["scenario_key"],
            "live=%r manifest=%r"
            % (meta.get("scenario_key"), manifest["source"]["scenario_key"]),
        ),
        "figure_inventory_matches_live_record": check(
            [f.get("name") for f in (meta.get("figures") or [])]
            == manifest["source"]["platform_figures"],
            "live=%s manifest=%s"
            % (
                [f.get("name") for f in (meta.get("figures") or [])],
                manifest["source"]["platform_figures"],
            ),
        ),
        "manifest_hash_matches_envelope": check(
            _sha256_bytes((OUT / "asset_manifest.json").read_bytes())
            == envelope["outputs"]["asset_manifest.json"]["sha256"],
            "recomputed=%s envelope=%s"
            % (
                _sha256_bytes((OUT / "asset_manifest.json").read_bytes()),
                envelope["outputs"]["asset_manifest.json"]["sha256"],
            ),
        ),
    }

    # every locator re-resolved against the *live* markdown (independent of the build-time self-check)
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        if not (0 <= s < e <= len(md)) or md[s:e] != q:
            bad.append([a["asset_id"], "char_span_quote"])
        elif (
            src.line_of(s) + 1 != loc["start_line"]
            or src.line_of(e - 1) + 1 != loc["end_line"]
        ):
            bad.append([a["asset_id"], "line_map"])
        elif "token" in loc and (
            md[loc["token_span"][0] : loc["token_span"][1]] != loc["token"]
        ):
            bad.append([a["asset_id"], "token_span"])
    checks["all_locators_resolve_in_live_source"] = check(
        not bad,
        "re-resolved %d locators against the live markdown; unresolvable=%s"
        % (len(manifest["assets"]), bad),
    )

    doc = {
        "package_id": cfg["package_id"],
        "report_id": cfg["report_id"],
        "schema": "published_check.v1",
        "checked_at": _now(),
        "api": "GET /api/v1/tensor/reports/%s" % cfg["report_id"],
        "record": {
            "status": meta.get("status"),
            "title": meta.get("title"),
            "scenario_key": meta.get("scenario_key"),
            "mission_id": meta.get("mission_id"),
            "tags": meta.get("tags") or [],
            "figures": [
                {
                    "name": f.get("name"),
                    "png_base64_bytes": len(f.get("png_base64") or ""),
                }
                for f in (meta.get("figures") or [])
            ],
            "created_at": meta.get("created_at"),
            "markdown_chars": len(md),
            "markdown_bytes_utf8": len(raw),
            "markdown_sha256": _sha256_bytes(raw),
        },
        "checks": checks,
        "all_pass": all(c["pass"] for c in checks.values()),
        "notes": [
            "This is a *record* cross-check by the producer, not the authoritative verification: the "
            "platform gate recomputes the hashes itself.",
            "Locators are absolute character offsets into the platform's own markdown, so the check above "
            "is exactly what the platform can redo without trusting this package.",
            "A published record is a publication state, not a knowledge verdict: no claim is marked "
            "verified anywhere in this package.",
        ],
    }
    (OUT / "published_check.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {k: v["pass"] for k, v in checks.items()}, ensure_ascii=False, indent=1
        )
    )
    return doc


# ------------------------------------------------------------------ report
def report(cfg=CFG):
    manifest = _read(OUT / "asset_manifest.json")
    envelope = _read(OUT / "kf_result.json")
    verdict = _read(OUT / "verification.json")
    det = _read(OUT / "determinism.json")
    pub = _read(OUT / "published_check.json")
    png = OUT / "figures" / ("%s_asset_locator_map.png" % cfg["package_id"])
    fig_rel = "figures/" + png.name
    n = manifest["counts"]["assets"]
    counts = manifest["counts"]

    def rows(doc):
        out = []
        for k, v in doc.items():
            out.append(
                "| `%s` | %s | %s |"
                % (
                    k,
                    "PASS" if v["pass"] else "FAIL",
                    str(v["detail"]).replace("|", "\\|")[:150],
                )
            )
        return out

    loc_rows = []
    for a in manifest["assets"]:
        q = a["locator"]["quote"].replace("|", "\\|").replace("\n", " ").strip()
        loc_rows.append(
            "| %s | %s | %s | L%s | `%s` |"
            % (
                a["asset_id"],
                a["asset_class"],
                a["resolution"],
                a["locator"]["start_line"],
                q[:58],
            )
        )

    lines = [
        "# KF-RESULT %s" % cfg["package_id"],
        "",
        "> 工序 01-asset-registration · report_id=%s · lane C · 产出 `asset_manifest.json`（登记，不抽取）"
        % cfg["report_id"],
        "> source_hash（平台可独立重算，sha256 over markdown utf-8 bytes）= `sha256:%s`"
        % manifest["source"]["hash"],
        "> 契约 source_hash = `sha256:%s` → 逐字符一致" % cfg["expected_hash"],
        "",
        "## ① 本工序做了什么",
        "",
        "对 `report_id=%s`（《%s》，scenario_key=`%s`，mission %s，状态 `%s`）执行**资产登记**："
        % (
            cfg["report_id"],
            manifest["source"]["title"],
            manifest["source"]["scenario_key"],
            pub["record"]["mission_id"],
            manifest["source"]["platform_status"],
        ),
        "确认报告 markdown 的字节哈希与契约一致（%d 字符 / %d 字节 utf-8），把正文里可解析的附件/工件登记为带**可复算定位器**的清单："
        % (manifest["source"]["chars"], manifest["source"]["bytes_utf8"]),
        "内嵌图、源码/工件路径引用、表格、复现命令块。**不做抽取、不生成 claim、不标注 verified**。",
        "",
        "规模：登记资产 **%d** 项，claims **0** 项；`counts.by_resolution` = `%s`；"
        "`counts.distinct_referenced_paths` = %d。"
        % (
            n,
            json.dumps(counts["by_resolution"], ensure_ascii=False),
            counts["distinct_referenced_paths"],
        ),
        "",
        "## ② 怎么做的（步骤 / 工具 / 关键设置）",
        "",
        "1. **取原文**：`GET /api/v1/tensor/reports/%s` 取 `markdown` 字段；只碰这一个 report_id，全程未凭记忆复述。"
        % cfg["report_id"],
        "2. **哈希门**：对 markdown 的 utf-8 字节做 sha256，与契约 `source_hash`/`chars` 双比对，不一致直接 `SystemExit`（不产出半成品）。",
        "3. **定位器生成**：逐行长度前缀和求出每行起始字符偏移，资产定位器一律为**绝对字符跨度** + 反推的 1-based 行号；",
        "   `quote` 取自源字节切片 `md[s:e]`，**不存在手抄环节**。",
        "4. **扫描规则**（确定性、无领域硬编码）：行内/围栏代码里的 `*.py|json|png|md|csv|yaml` 路径 → 路径引用（出现级身份 = 路径 × 行号）；",
        "   `record.figures[]` → 内嵌图（`png_base64` 为空则 `metadata_only`，不伪造字节哈希）；连续 `|` 行 → 表格（只记行数×列数几何）；"
        "``` 围栏 → 复现命令块。",
        "5. **本地解析**：路径只在**本交付工作树**内解析（`os.path.isfile` + 命中文件 sha256）；属产出仓 %s 的路径越界即如实记 "
        "`referenced_unresolved`，不读别的仓。" % cfg["producing_repo"],
        "6. **复用而非分叉**：扫描/定位器代码直接 import `scripts/kf/kf01_register.py`（lane C 通用登记器），",
        "   本包不复制一份实现；该共享工具是多个在开 PR 的热文件，本包**不改动它**（manifest `producer` 同时记录 generator 与本 driver）。",
        "7. **两份附加证据**：`determinism.json`（两次独立重建的规范化对比）与 `published_check.json`（对 live 记录的状态/标题/图清单/哈希 + 全部定位器重解析逐条核对）。",
        "8. **自检**：信封按 `schemas/kf_result.v1.schema.json`，清单按 `schemas/asset_manifest.v1.schema.json`（仅放松四处包级固定值），",
        "   jsonschema draft 2020-12；`verification.json` 逐条重算 acceptance。",
        "",
        "## ③ 产出物清单（文件名 → 要点）",
        "",
        "| 文件 | 要点 |",
        "|---|---|",
        "| `asset_manifest.json` | %d 项资产；`by_class`=%s；claims=0；sha256 `%s` |"
        % (
            n,
            json.dumps(counts["by_class"], ensure_ascii=False),
            verdict["manifest_sha256"],
        ),
        "| `kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs/claims），source_hash 与契约一致 |",
        "| `verification.json` | %d 项 acceptance 自检逐条 pass/fail；`all_pass`=%s |"
        % (len(verdict["checks"]), verdict["all_pass"]),
        "| `determinism.json` | 2 次独立重建，规范化后一致；图为逐字节一致；`all_identical`=%s |"
        % det["all_identical"],
        "| `published_check.json` | %d 项 live 记录核对；`all_pass`=%s |"
        % (len(pub["checks"]), pub["all_pass"]),
        "| `report_payload.json` | POST `/tensor/reports` 的请求体（标题/摘要/图内嵌 base64） |",
        "| `report.md` | 本报告（由清单/信封/自检/证据**程序化渲染**，无手抄） |",
        "| `%s` | A) 资产类别×解析状态计数；B) 每个资产在源文档中的字符跨度覆盖图 |"
        % fig_rel,
        "",
        "资产类别分布：`%s`。" % json.dumps(counts["by_class"], ensure_ascii=False),
        "",
        "## ④ 结果图",
        "",
        "![asset locator map](%s)" % fig_rel,
        "",
        "**图注**：A) 资产类别 × 解析状态（绿=源内已解析、红=引用未解析、灰=声明缺失）；B) 每个资产在 markdown 中的字符跨度",
        "（横轴=字符偏移，源文档 %d 字符）。两图直接由 `asset_manifest.json` 绘出，零手抄。"
        % manifest["source"]["chars"],
        cfg["figure_note"],
        "",
        "## ⑤ 证据定位表（资产 → 原文逐字片段，均由 `md[start_char:end_char]` 计算）",
        "",
        "| asset_id | 类别 | 解析 | 行 | 原文片段（逐字） |",
        "|---|---|---|---|---|",
        *loc_rows,
        "",
        "（完整 quote、字符跨度与 `token_span` 见 `asset_manifest.json` 各 `locator`；平台可对每条 quote 做子串 + 行号独立复核，",
        "本包在 `published_check.json::all_locators_resolve_in_live_source` 里已自己先跑过一遍。）",
        "",
        "## ⑥ 注意点与局限",
        "",
        "1. **登记 ≠ 抽取**：清单只回答「报告里有哪些可解析工件、在其中何处」，不回答「报告说了什么」。claims 为空是契约允许的完整结果。",
        "2. **不标 verified**：清单与信封里没有任何 `verified` 状态；验证由平台门计算。",
        "3. **图只有元数据**：`record.figures[]` 共 %d 项且 `png_base64` 为空（0 字节），故只登记 name/caption + 正文出现位置（`metadata_only`）。"
        % len(manifest["source"]["platform_figures"]),
        *cfg["cross_repo_note"],
        "5. **表格内容未复述**：%d 张表只登记几何（行×列）与字符跨度，避免把报表数字二次转写引入漂移。"
        % counts["by_class"].get("report_table", 0),
        "6. **确定性 ≠ 逐字节相同**：两次构建各写自己的构建时钟（`generated_at` / `provenance.emitted_at`），",
        "   这两个字段在 `determinism.json.method.excluded_volatile_fields` 中显式命名并在哈希前移除；其余字段必须逐字段一致。",
        "7. **schema 口径**：`schemas/asset_manifest.v1.schema.json` 把 `package_id/task_type/report_id`/`source.uri` 钉死为 wp-448-01 的包级取值，",
        "   自检时**仅放松这四处包级固定值**（`source.uri` 改为 `^tensor://reports/[0-9]+$`，其余约束照常生效）并如实记录在 `detail` 里。",
        "8. **不提「GPU 已实现」**：源报告的核心结论是 GPU NOT_SUPPORTED（loong64 无 CUDA），本包只登记该结论所在位置，不转述为能力。",
        "",
        "## ⑦ 自检（逐条对照 acceptance）",
        "",
        "| acceptance 项 | 结果 | 细节 |",
        "|---|---|---|",
        *rows(verdict["checks"]),
        "",
        "### ⑦b 确定性（`determinism.json`）",
        "",
        "| 归一化对象 | run A sha256 | run B sha256 | 一致 |",
        "|---|---|---|---|",
        "| `asset_manifest.json`（去 `generated_at`） | `%s` | `%s` | %s |"
        % (
            det["runs"][0]["asset_manifest_canonical_sha256"][:16],
            det["runs"][1]["asset_manifest_canonical_sha256"][:16],
            det["invariants"]["asset_manifest_canonical_identical"],
        ),
        "| `kf_result.json`（去 2 处时钟 + 归一化输出路径） | `%s` | `%s` | %s |"
        % (
            det["runs"][0]["kf_result_canonical_sha256"][:16],
            det["runs"][1]["kf_result_canonical_sha256"][:16],
            det["invariants"]["kf_result_canonical_identical"],
        ),
        "| 定位器图 PNG（逐字节） | `%s` | `%s` | %s |"
        % (
            det["runs"][0]["figure_bytes_sha256"][:16],
            det["runs"][1]["figure_bytes_sha256"][:16],
            det["invariants"]["figure_bytes_identical"],
        ),
        "",
        "环境：python %s / matplotlib %s / jsonschema %s / %s。"
        % (
            det["environment"]["python"],
            det["environment"]["matplotlib"],
            det["environment"]["jsonschema"],
            det["environment"]["machine"],
        ),
        "",
        "### ⑦c 发布状态核对（`published_check.json`）",
        "",
        "| 检查项 | 结果 | 细节 |",
        "|---|---|---|",
        *rows(pub["checks"]),
        "",
        "## 复现",
        "",
        "```bash",
        "python3 scripts/kf/%s.py build result verify figure determinism published report"
        % Path(__file__).stem,
        "```",
        "",
        "repro_cmd: `python3 scripts/kf/%s.py build result verify figure determinism published report`"
        % Path(__file__).stem,
        "",
        "## 结果信封（唯一 json 代码块，原样提交）",
        "",
        "```json",
        json.dumps(envelope, ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    text = "\n".join(lines)
    if text.count("```json") != 1:
        raise SystemExit(
            "report must contain exactly one ```json block, found %d"
            % text.count("```json")
        )
    (OUT / "report.md").write_text(text, encoding="utf-8")
    print("wrote %s" % (OUT / "report.md").relative_to(REPO))

    payload = {
        "title": "KF-RESULT %s" % cfg["package_id"],
        "summary": (
            "资产登记 %s / report_id=%s：《%s》%d 项资产（%s），source_hash 与契约一致；rebuild 确定性 %s，"
            "live 记录核对 %d/%d 通过；claims=0（登记不抽取）。"
            % (
                cfg["package_id"],
                cfg["report_id"],
                manifest["source"]["title"],
                n,
                json.dumps(counts["by_resolution"], ensure_ascii=False),
                "通过" if det["all_identical"] else "未通过",
                sum(1 for c in pub["checks"].values() if c["pass"]),
                len(pub["checks"]),
            )
        ),
        "scenario_key": cfg["scenario_key"],
        "mission_id": cfg["mission_id"],
        "tags": [
            "kf-wp:%s" % cfg["package_id"],
            "asset-registration",
            "lane-C",
            "TensorKnowledge",
            "report_id:%s" % cfg["report_id"],
            "determinism",
            "published-check",
        ],
        "markdown": text,
        "figures": [
            {
                "name": png.name,
                "caption": "%s asset inventory & locator coverage map (computed from asset_manifest.json)"
                % cfg["package_id"],
                "png_base64": base64.b64encode(png.read_bytes()).decode(),
            }
        ],
    }
    (OUT / "report_payload.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print("wrote %s" % (OUT / "report_payload.json").relative_to(REPO))
    return payload


def main(argv=None):
    acts = (argv if argv is not None else sys.argv[1:]) or [
        "build",
        "result",
        "verify",
        "figure",
        "determinism",
        "published",
        "report",
    ]
    order = [
        "build",
        "result",
        "verify",
        "figure",
        "determinism",
        "published",
        "report",
    ]
    for act in order:
        if act in acts:
            {
                "build": build,
                "result": result,
                "verify": verify,
                "figure": figure,
                "determinism": determinism,
                "published": published,
                "report": report,
            }[act]()
    unknown = set(acts) - set(order)
    if unknown:
        raise SystemExit("unknown action(s): %s" % sorted(unknown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
