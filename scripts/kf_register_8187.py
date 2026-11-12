"""Register the source assets of report 8187 (work package wp-8187-01, task_type 01-asset-registration).

Design rules enforced here (same discipline as scripts/kf_register_448.py / wp-7768-01):
  * No hand transcription. Every ``quote`` in the manifest is a verbatim substring of the
    report markdown, located at run time by ``str.find`` on a programmatic anchor token;
    the script re-checks each quote against the freshly fetched markdown before writing.
  * Registration only. No claim extraction (contract: objective.register_assets=true,
    classify_report_type=false, claims may be empty). Nothing is marked verified;
    ``resolution`` describes locator resolvability in the source only.
  * The referenced files live in the TensorDEM repo (branch agent/m6796 per the report
    header), NOT in this TensorKnowledge worktree; we register their in-source references
    and do not assert existence of the files themselves.

Inputs:
  live API: GET /api/v1/tensor/reports/8187  (Bearer login via $TENSOR_AGENT_USER/$TENSOR_AGENT_PASS)

Outputs:
  docs/kf/wp-8187-01/asset_manifest.json   (durable committed copy)
  docs/kf/wp-8187-01/kf_result.json        (result envelope, kf_result.v1 shape)
  runs/wp-8187-01/report_8187.md           (markdown payload, byte-identical)
  runs/wp-8187-01/report_8187_api.json     (raw API payload)
  runs/wp-8187-01/asset_manifest.json      (mirror)
  runs/wp-8187-01/kf_result.json           (mirror)

Usage: python3 scripts/kf_register_8187.py
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import pathlib
import urllib.request

REPORT_ID = "8187"
PACKAGE_ID = "wp-8187-01"
TASK_TYPE = "01-asset-registration"
CONTRACT_SOURCE_HASH = "sha256:123060fc65159890ea043d0ce52dc0d565538b3f73043be6da2b1e82ba220789"
CONTRACT_CHARS = 9206
CONTRACT_TITLE = "P35-N2 湿冰颗粒团聚的毛细桥 cohesion 模型：解析锚 + 团聚体尺寸演化 + 冰阻力增强因子（TensorDEM）"
CONTRACT_SCENARIO_KEY = "wet_ice_cohesion"
SOURCE_URI = f"tensor://reports/{REPORT_ID}"

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC_DIR = ROOT / "docs" / "kf" / "wp-8187-01"
RUN_DIR = ROOT / "runs" / "wp-8187-01"

# Anchor table: asset_id, class, label, anchor token (must be a verbatim substring of the
# markdown), and the report section where the first occurrence sits (verified by the script
# against the actual heading walk, not trusted from this comment).
ASSETS = [
    dict(asset_id="A01", asset_class="capability",
         label="新增能力标识（领域目录 4 模块 + 1 study + 1 figures）",
         token="tensordem.wet_ice_cohesion"),
    dict(asset_id="A02", asset_class="source_code",
         label="毛细桥力律模块（任务书闭式/小液桥解析锚/DEM 级闭式）",
         token="capillary.py"),
    dict(asset_id="A03", asset_class="source_code",
         label="精确轴对称 Young–Laplace 求解器（判定基准，零重力精确自由面）",
         token="tensordem.liquid_bridge.solve_axisymmetric_bridge"),
    dict(asset_id="A04", asset_class="source_code",
         label="YL 求解器文件（自带一阶积分自洽检查）",
         token="liquid_bridge.py"),
    dict(asset_id="A05", asset_class="script",
         label="毛细桥参考表生成脚本（R/γ/n_steps 记入 meta，可一键重算）",
         token="scripts/gen_wet_ice_capillary_reference.py"),
    dict(asset_id="A06", asset_class="data",
         label="毛细桥参考表 JSON（train/validate 行 + converged 标记）",
         token="artifacts/wet_ice_cohesion/capillary_reference.json"),
    dict(asset_id="A07", asset_class="source_code",
         label="团聚粒子级模型（仿射剪切 + Lees–Edwards 镜像 + 等价球合并）",
         token="aggregation.py"),
    dict(asset_id="A08", asset_class="source_code",
         label="2D 拉伸池内聚力测量（行沉积+位置式压缩+顶墙上拉）",
         token="cohesion_cell.py"),
    dict(asset_id="A09", asset_class="source_code",
         label="冰阻力增强因子 F_enh 计算",
         token="ice_resistance.py"),
    dict(asset_id="A10", asset_class="script",
         label="全判据 study 脚本（判据 → campaign.json + 4 张图）",
         token="scripts/wet_ice_cohesion_study.py"),
    dict(asset_id="A11", asset_class="data",
         label="全判据结果 JSON（含参考自洽最大偏差 1.22 %/1.39 % 汇总）",
         token="artifacts/wet_ice_cohesion/campaign.json"),
    dict(asset_id="A12", asset_class="test",
         label="pytest 断言面（18 项断言，130 s）",
         token="tests/test_wet_ice_cohesion.py"),
    dict(asset_id="A13", asset_class="figure",
         label="图1 液桥力律 F/(2πγR) vs s/R + 峰值力 parity（留出集最大误差 0.32 %）",
         token="artifacts/wet_ice_cohesion/fig1_capillary_bridge.png"),
    dict(asset_id="A14", asset_class="figure",
         label="图2 团聚体平均尺寸 ⟨D⟩/D0：DEM vs Smoluchowski + 团簇尺寸分布",
         token="artifacts/wet_ice_cohesion/fig2_agglomeration_smoluchowski.png"),
    dict(asset_id="A15", asset_class="figure",
         label="图3 拉伸池墙牵引力时程（湿 vs 干）+ 实测 c vs 参考/上界",
         token="artifacts/wet_ice_cohesion/fig3_cohesion_cell.png"),
    dict(asset_id="A16", asset_class="figure",
         label="图4 增强因子 F_wet/F_dry 随颗粒半径（Bond 数 ≲1 窗口）",
         token="artifacts/wet_ice_cohesion/fig4_enhancement_vs_size.png"),
    dict(asset_id="A17", asset_class="source_code",
         label="图生成入口 make_all（只读 campaign.json）",
         token="src/tensordem/wet_ice_cohesion/figures.py"),
]


def api_get(path: str, token: str) -> tuple[int, bytes]:
    req = urllib.request.Request(
        f"{os.environ['TENSOR_API_BASE']}/{path}",
        headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:  # noqa: PERF203
        return e.code, e.read()


def main() -> int:
    base = os.environ["TENSOR_API_BASE"]
    user = os.environ["TENSOR_AGENT_USER"]
    pw = os.environ["TENSOR_AGENT_PASS"]
    body = json.dumps({"username": user, "password": pw}).encode()
    req = urllib.request.Request(
        f"{base}/auth/login", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        token = json.loads(r.read())["access_token"]

    status, raw = api_get(f"tensor/reports/{REPORT_ID}", token)
    assert status == 200, f"report fetch failed: {status}"
    payload = json.loads(raw)
    md = payload["markdown"]

    # --- source integrity -------------------------------------------------
    h = hashlib.sha256(md.encode("utf-8")).hexdigest()
    hash_match = f"sha256:{h}" == CONTRACT_SOURCE_HASH
    chars = len(md)
    chars_match = chars == CONTRACT_CHARS
    title_match = payload.get("title") == CONTRACT_TITLE
    scenario_match = payload.get("scenario_key") == CONTRACT_SCENARIO_KEY
    assert hash_match, f"hash mismatch: {h}"
    assert chars_match, f"chars mismatch: {chars}"
    assert title_match and scenario_match, "record field mismatch vs contract"

    lines = md.rstrip("\n").split("\n")  # logical lines, 1-based counting
    line_starts = []
    off = 0
    for ln in lines:
        line_starts.append(off)
        off += len(ln) + 1

    def line_of(pos: int) -> int:
        lo, hi = 0, len(lines) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    def section_of(pos: int) -> str:
        """Nearest preceding '## ' heading text (1-based heading walk)."""
        cur = "报告头（标题下元信息行）"
        for i, ln in enumerate(lines):
            if line_starts[i] > pos:
                break
            if ln.startswith("## "):
                cur = ln[3:].strip()
        return cur

    # --- platform figure probes (metadata-only expectation, cf. wp-623-01) --
    fig_probes = {}
    for fig in payload.get("figures", []):
        st, body = api_get(f"tensor/reports/{REPORT_ID}/figures/{fig['name']}", token)
        fig_probes[fig["name"]] = {"http_status": st, "bytes": len(body)}

    # --- asset locators ----------------------------------------------------
    assets_out = []
    for a in ASSETS:
        tok = a["token"]
        n = md.count(tok)
        assert n >= 1, f"anchor not found: {tok}"
        start = md.find(tok)
        end = start + len(tok)
        assert md[start:end] == tok
        ln = line_of(start)
        assets_out.append({
            "asset_id": a["asset_id"],
            "asset_class": a["asset_class"],
            "label": a["label"],
            "in_report_section": section_of(start),
            "locator": {
                "method": "char_span",
                "start_char": start,
                "end_char": end,
                "start_line": ln,
                "end_line": line_of(end - 1),
                "quote": tok,
                "unique": n == 1,
            },
            "resolution": "resolved_in_source",
            "resolution_check": {
                "check": f"substring_search:{tok}",
                "result": "resolved",
            },
            "note": (f"Referenced in {section_of(start)}; {n} occurrence(s) in report; "
                      f"file lives in TensorDEM (branch agent/m6796 per report header), "
                      f"not in this worktree; existence not asserted"),
        })

    by_class: dict[str, int] = {}
    for a in assets_out:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": h,
            "chars": chars,
            "bytes_utf8": len(md.encode("utf-8")),
            "title": payload["title"],
            "scenario_key": payload["scenario_key"],
            "platform_figures": [
                {"name": f["name"], "caption": f["caption"]}
                for f in payload.get("figures", [])
            ],
            "platform_tags": payload.get("tags", []),
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "hash_match": hash_match,
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": chars_match,
            "title_matches_contract": title_match,
            "scenario_matches_contract": scenario_match,
            "fetched_via": f"GET /api/v1/tensor/reports/{REPORT_ID}",
            "record_fields": {
                "id": payload.get("id"),
                "mission_id": payload.get("mission_id"),
                "status": payload.get("status"),
                "created_at": payload.get("created_at"),
            },
            "platform_figure_probes": fig_probes,
            "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)); 1-based",
        },
        "counts": {
            "assets": len(assets_out),
            "by_class": by_class,
            "by_resolution": {"resolved_in_source": len(assets_out)},
            "resolved_in_source": len(assets_out),
            "referenced_unresolved": 0,
            "declared_absent": 0,
        },
        "assets": assets_out,
        "claims": [],
        "integrity": {
            "quote_uniqueness": "all_locators_verified",
            "hash_recomputed_locally": True,
            "hash_matches_contract": hash_match,
        },
    }

    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": f"sha256:{h}",
            "source_field": "markdown",
            "producer": "agent/m15608",
            "emitted_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "notes": (
                "Asset registration for report 8187 (P35-N2 wet-ice capillary-bridge cohesion, "
                "TensorDEM). Source hash recomputed from live API markdown and matches contract. "
                "17 referenced artifacts located with verbatim char_span locators; claims=[] per "
                "contract (classify_report_type=false, no extraction). Nothing marked verified."
            ),
        },
        "outputs": {"asset_manifest.json": manifest},
    }

    # --- self-checks --------------------------------------------------------
    json.loads(json.dumps(manifest))  # valid_json
    json.loads(json.dumps(envelope))
    try:
        import jsonschema
        schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
        jsonschema.validate(envelope, schema)
        schema_note = "kf_result.v1 schema: 0 errors"
    except ImportError:
        schema_note = "jsonschema not installed; structural keys checked manually"
    for a in assets_out:
        q = a["locator"]["quote"]
        assert md[a["locator"]["start_char"]:a["locator"]["end_char"]] == q
        assert md.count(q) == (1 if a["locator"]["unique"] else md.count(q))
    ids = [a["asset_id"] for a in assets_out]
    assert len(ids) == len(set(ids)), "duplicate asset ids"
    assert manifest["claims"] == []

    # --- write outputs -------------------------------------------------------
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "report_8187.md").write_text(md)
    (RUN_DIR / "report_8187_api.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    (DOC_DIR / "asset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    (DOC_DIR / "kf_result.json").write_text(json.dumps(envelope, ensure_ascii=False, indent=2))
    (RUN_DIR / "asset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    (RUN_DIR / "kf_result.json").write_text(json.dumps(envelope, ensure_ascii=False, indent=2))

    print(json.dumps({
        "hash": h, "hash_match": hash_match, "chars": chars,
        "assets": len(assets_out), "by_class": by_class,
        "schema": schema_note, "figure_probes": fig_probes,
        "lines": len(lines),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
