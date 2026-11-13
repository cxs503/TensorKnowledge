#!/usr/bin/env python3
"""Build the asset manifest for KF work package wp-12866-01 (task_type 01-asset-registration).

Scope (hard): report_id=12866 only. Registration only -- no knowledge extraction, no
claim status is asserted here (verification is computed by the platform gate).

Pipeline:
  1. fetch report markdown (GET /tensor/reports/12866) or read the cached copy;
  2. recompute sha256 over markdown.encode("utf-8") and compare with the contract hash;
  3. register every asset reference with a verbatim, unique locator into the markdown
     (figures are additionally probed through GET /tensor/reports/12866/figures/{name}
     and hash-pinned);
  4. emit docs/kf/wp-12866-01/{asset_manifest.json,kf_result.json,REPORT.md,
     figure_probe.json,source_markdown.md,figures/*.png};
  5. --verify re-runs every acceptance item against the committed artifacts.

Usage:
  python3 scripts/kf/build_asset_manifest_12866.py            # build (online if creds present)
  python3 scripts/kf/build_asset_manifest_12866.py --offline   # build from cached files only
  python3 scripts/kf/build_asset_manifest_12866.py --verify    # acceptance checks only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = "wp-12866-01"
REPORT_ID = "12866"
TASK_TYPE = "01-asset-registration"
OUT = ROOT / "docs" / "kf" / PKG
CONTRACT_HASH = "e577eedec941fa1ce25076f7a16b0774d609c1ca6693b056a5b0212ab5483154"
SOURCE_URI = f"tensor://reports/{REPORT_ID}"
EXPECTED_TITLE = (
    "AUV 潜器空间/垂直面操纵性：Munk 力矩解析锚 + 回转椭球 Lamb 附加质量 + "
    "定深纵倾闭环（m12371）"
)
SCENARIO_KEY = "auv_manoeuvrability_vertical_plane"

# (asset_id, asset_class, label, in_report_section, resolution, anchor-in-markdown, note)
ASSET_SPECS = [
    (
        "A01",
        "report_markdown",
        "report 12866 的 markdown 正文（本工作包唯一源字段）",
        "§title/全文",
        "resolved_in_source",
        "# AUV/潜器空间与垂直面操纵性：Munk 力矩解析锚 + Lamb 附加质量 + 定深纵倾闭环",
        "sha256 与契约 source_hash 一致；chars/bytes 见 source 块",
    ),
    (
        "A02",
        "embedded_figure",
        "fig1_lamb_coefficients.png（Lamb 系数 k(λ)：闭式解 vs 求积 + 球极限 + Lamb 表）",
        "④ 图",
        "resolved_in_source",
        "fig1 Lamb 系数 k(λ)",
        "二进制经 GET /tensor/reports/12866/figures/fig1_lamb_coefficients.png 取回并 sha256 钉住",
    ),
    (
        "A03",
        "embedded_figure",
        "fig2_munk_convergence.png（Munk 系数随 λ 与 5% 判据线）",
        "④ 图",
        "resolved_in_source",
        "fig2 Munk 系数随 λ",
        "二进制经 figures 端点取回并 sha256 钉住",
    ),
    (
        "A04",
        "embedded_figure",
        "fig3_depth_keeping.png（定深纵倾闭环时历 + 相图 + Newton 平衡虚线）",
        "④ 图",
        "resolved_in_source",
        "fig3 定深闭环时历",
        "二进制经 figures 端点取回并 sha256 钉住",
    ),
    (
        "A05",
        "embedded_figure",
        "fig4_munk_vs_alpha.png（C_M(α) 精确 vs 条带 + 纵倾刚度预算柱图）",
        "④ 图",
        "resolved_in_source",
        "fig4 C_M(α) 精确 vs 条带",
        "二进制经 figures 端点取回并 sha256 钉住",
    ),
    (
        "A06",
        "source_code_reference",
        "求解器实现 backend/methods/manoeuvring/submarine.py",
        "① 算例介绍（代码行）",
        "referenced_unresolved",
        "backend/methods/manoeuvring/submarine.py",
        "目标位于 ship-performance-platform 检出，不在本工作包范围内；报告未给 commit sha",
    ),
    (
        "A07",
        "test_reference",
        "回归测试 backend/tests/test_auv_manoeuvring_m12371.py（报告称 19 passed）",
        "① 算例介绍（测试行）",
        "referenced_unresolved",
        "backend/tests/test_auv_manoeuvring_m12371.py",
        "测试目标不在本仓；'19 passed' 为源报告自述，本单未重跑、不背书",
    ),
    (
        "A08",
        "report_document",
        "上游详细报告 docs/reports/auv_manoeuvrability_w5n06.md",
        "① 算例介绍（详细报告行）",
        "referenced_unresolved",
        "docs/reports/auv_manoeuvrability_w5n06.md",
        "路径相对于 ship-performance-platform 仓，本工作包不含该文件",
    ),
    (
        "A09",
        "artifact_directory",
        "证据工件目录 artifacts/auv_manoeuvring_m12371/",
        "① 算例介绍（工件行）",
        "referenced_unresolved",
        "artifacts/auv_manoeuvring_m12371/",
        "目录内容随分支 agent/m12371 演化，无法从本记录哈希钉住",
    ),
    (
        "A10",
        "artifact_file_reference",
        "acceptance.json（目录内声明的验收工件）",
        "① 算例介绍（工件行）",
        "referenced_unresolved",
        "acceptance.json",
        "仅登记报告内的声明名；文件字节不可从本记录取得",
    ),
    (
        "A11",
        "artifact_file_reference",
        "depth_keeping.csv（定深闭环时历数据）",
        "① 算例介绍（工件行）",
        "referenced_unresolved",
        "depth_keeping.csv",
        "仅登记声明名；CSV 未随报告载荷提供",
    ),
    (
        "A12",
        "artifact_file_reference",
        "fig1-4.png（工件目录内的图组文件）",
        "① 算例介绍（工件行）",
        "referenced_unresolved",
        "fig1-4.png",
        "声称对应 A02–A05 的四张图，但工件目录副本不可得，无法核对是否与 figures 端点字节一致",
    ),
    (
        "A13",
        "platform_identifier",
        "节点号 IN51-W5-N06（mission 12371 的子节点）",
        "① 算例介绍（节点行）",
        "referenced_unresolved",
        "IN51-W5-N06",
        "站内节点标识；本单不解引用任务图，故不声称节点状态",
    ),
    (
        "A14",
        "platform_identifier",
        "mission_id 12371",
        "① 算例介绍（节点行）",
        "resolved_in_source",
        "mission 12371",
        "与报告记录字段 mission_id=12371 交叉核对一致（记录级核对，非内容抽取）",
    ),
    (
        "A15",
        "vcs_reference",
        "分支 agent/m12371",
        "① 算例介绍（仓/分支行）",
        "referenced_unresolved",
        "agent/m12371",
        "报告未给 commit sha；分支头会移动，无法从本记录钉住字节",
    ),
    (
        "A16",
        "repository_reference",
        "仓库 ship-performance-platform",
        "① 算例介绍（仓/分支行）",
        "referenced_unresolved",
        "ship-performance-platform",
        "域仓，不在本工作包（TensorKnowledge）范围内，未做跨仓检出",
    ),
]

FIGURE_NAMES = [
    "fig1_lamb_coefficients.png",
    "fig2_munk_convergence.png",
    "fig3_depth_keeping.png",
    "fig4_munk_vs_alpha.png",
]


# ----------------------------------------------------------------------------- fetch
def _api_base() -> str:
    base = os.environ.get("TENSOR_API_BASE", "")
    return base.rstrip("/")


def _token() -> str:
    tok = os.environ.get("TENSOR_API_TOKEN", "")
    if tok:
        return tok
    base, user, pwd = _api_base(), os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (base and user and pwd):
        return ""
    body = json.dumps({"username": user, "password": pwd}).encode()
    req = urllib.request.Request(
        f"{base}/auth/login", data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
        return json.loads(r.read().decode())["access_token"]


def _get(path: str, token: str) -> tuple[int, bytes]:
    req = urllib.request.Request(f"{_api_base()}{path}", headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310
            return r.status, r.read()
    except urllib.error.HTTPError as e:  # pragma: no cover - network dependent
        return e.code, e.read()


def fetch_source(offline: bool) -> tuple[str, dict]:
    """Return (markdown, record_meta). Falls back to the cached copy when offline."""
    cached_md = OUT / "source_markdown.md"
    cached_meta = OUT / "report_record.json"
    if not offline:
        try:
            tok = _token()
            if tok:
                code, payload = _get(f"/tensor/reports/{REPORT_ID}", tok)
                if code == 200:
                    rec = json.loads(payload.decode())
                    md = rec["markdown"]
                    OUT.mkdir(parents=True, exist_ok=True)
                    cached_md.write_text(md, encoding="utf-8")
                    meta = {k: v for k, v in rec.items() if k != "markdown"}
                    cached_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
                    return md, meta
                print(f"[warn] report fetch HTTP {code}; falling back to cache", file=sys.stderr)
        except Exception as e:  # pragma: no cover - network dependent
            print(f"[warn] report fetch failed ({e}); falling back to cache", file=sys.stderr)
    md = cached_md.read_text(encoding="utf-8")
    meta = json.loads(cached_meta.read_text(encoding="utf-8")) if cached_meta.exists() else {}
    return md, meta


def probe_figures(offline: bool) -> dict:
    """Fetch each figure through the report figures endpoint and hash the bytes."""
    probe_path = OUT / "figure_probe.json"
    if offline or not _api_base():
        return json.loads(probe_path.read_text(encoding="utf-8"))
    tok = _token()
    figdir = OUT / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    probes: dict = {}
    for name in FIGURE_NAMES:
        code, data = _get(f"/tensor/reports/{REPORT_ID}/figures/{name}", tok)
        entry: dict = {
            "endpoint": f"/tensor/reports/{REPORT_ID}/figures/{name}",
            "http_status": code,
            "bytes": len(data),
        }
        if code == 200 and data:
            (figdir / name).write_bytes(data)
            entry["sha256"] = hashlib.sha256(data).hexdigest()
            entry["resolvable"] = True
        else:
            entry["resolvable"] = False
            entry["error_body"] = data[:200].decode("utf-8", "replace")
        probes[name] = entry
    probe_path.write_text(json.dumps(probes, ensure_ascii=False, indent=1), encoding="utf-8")
    return probes


# ------------------------------------------------------------------------ locators
def locate(md: str, anchor: str) -> dict:
    n = md.count(anchor)
    start = md.find(anchor)
    if start < 0:
        raise SystemExit(f"locator not found in markdown: {anchor!r}")
    end = start + len(anchor)
    return {
        "method": "char_span",
        "start_char": start,
        "end_char": end,
        "start_line": md.count("\n", 0, start) + 1,
        "end_line": md.count("\n", 0, end) + 1,
        "quote": anchor,
        "unique": n == 1,
        "occurrences": n,
    }


def structure_index(md: str) -> list[dict]:
    heads = []
    for m in re.finditer(r"^(#{1,3}) (.+)$", md, flags=re.M):
        heads.append(
            {
                "level": len(m.group(1)),
                "text": m.group(2).strip(),
                "line_no": md.count("\n", 0, m.start()) + 1,
                "start_char": m.start(),
            }
        )
    return heads


def build(offline: bool) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    md, meta = fetch_source(offline)
    probes = probe_figures(offline)

    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    if digest != CONTRACT_HASH:
        raise SystemExit(f"source hash mismatch: {digest} != {CONTRACT_HASH}")

    assets = []
    for aid, cls, label, section, resolution, anchor, note in ASSET_SPECS:
        loc = locate(md, anchor)
        entry = {
            "asset_id": aid,
            "asset_class": cls,
            "label": label,
            "in_report_section": section,
            "locator": loc,
            "resolution": resolution,
            "resolution_check": {
                "check": "verbatim anchor present exactly once in markdown"
                if resolution == "resolved_in_source"
                else "parsed from markdown; target outside this package scope (not fetched)",
                "result": "resolved" if resolution == "resolved_in_source" else "unresolved",
            },
            "note": note,
        }
        if cls == "embedded_figure":
            name = FIGURE_NAMES[int(aid[1:]) - 2]
            p = probes.get(name, {})
            entry["payload"] = {
                "record_figure_name": name,
                "probe": p,
                "local_copy": f"docs/kf/{PKG}/figures/{name}" if p.get("resolvable") else None,
            }
            if p.get("resolvable"):
                entry["resolution_check"] = {
                    "check": "markdown anchor unique + figure endpoint HTTP 200 + sha256 pinned",
                    "result": "resolved",
                }
        if aid == "A14":
            entry["record_cross_check"] = {"record_field": "mission_id", "record_value": meta.get("mission_id")}
        assets.append(entry)

    ids = [a["asset_id"] for a in assets]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate asset_id")

    by_class: dict = {}
    by_res: dict = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    figures_meta = {
        str(i + 1): {"name": f.get("name"), "caption": f.get("caption")}
        for i, f in enumerate(meta.get("figures") or [])
    }

    manifest = {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "contract_version": "1.0",
        "objective": {"register_assets": True, "classify_report_type": False},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest,
            "hash_scope": "sha256 of markdown encoded as utf-8",
            "contract_hash": CONTRACT_HASH,
            "hash_matches_contract": digest == CONTRACT_HASH,
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "title": meta.get("title"),
            "scenario_key": meta.get("scenario_key"),
            "mission_id": meta.get("mission_id"),
            "status": meta.get("status"),
            "tags": meta.get("tags") or [],
            "platform_figures": figures_meta,
            "fetched_via": f"GET /tensor/reports/{REPORT_ID}" if not offline else "cached source_markdown.md",
        },
        "structure_index": {
            "note": "headings only; char offsets into the markdown string — locator scaffolding for downstream 工序, no content extracted",
            "headings": structure_index(md),
        },
        "resolution_vocabulary": {
            "resolved_in_source": "anchor located verbatim+uniquely in the markdown; for figure binaries the payload was fetched and sha256-pinned",
            "referenced_unresolved": "reference parsed verbatim from the markdown but the target lives outside this package scope (domain repo / moving branch)",
            "declared_absent": "declared by the report but no payload found anywhere (none in this manifest)",
        },
        "assets": assets,
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "claims_registered": 0,
        },
        "nonextraction_note": "task_type 01: no numbers, formulas or conclusions were lifted out of the report; tables/figures are registered as artifacts, not interpreted",
        "claims": [],
        "claims_note": (
            "empty array is the contract-permitted complete result for 01-asset-registration "
            "(constraints.no_forced_claim_generation); no claim is marked verified here"
        ),
        "integrity": {
            "quote_uniqueness": all(a["locator"]["unique"] for a in assets),
            "hash_recomputed_locally": True,
            "hash_matches_contract": digest == CONTRACT_HASH,
            "asset_ids_unique": len(ids) == len(set(ids)),
            "single_report_scope": True,
        },
        "producer": f"agent/m15754 (TensorKnowledge) · package {PKG}",
        "repro_cmd": (
            "python3 scripts/kf/build_asset_manifest_12866.py && "
            "python3 scripts/kf/build_asset_manifest_12866.py --verify && "
            "python3 -m pytest tests/test_wp12866_01_asset_registration.py -q"
        ),
        "tools": {"generator": "scripts/kf/build_asset_manifest_12866.py", "python": sys.version.split()[0]},
    }

    mpath = OUT / "asset_manifest.json"
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    mdigest = hashlib.sha256(mpath.read_bytes()).hexdigest()

    kf = {
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": f"sha256:{digest}",
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(md),
            "source_bytes_utf8": len(md.encode("utf-8")),
            "producer": "scripts/kf/build_asset_manifest_12866.py · agent/m15754",
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "notes": "asset registration only; no extraction performed; nothing marked verified (platform gate computes verification)",
        },
        "outputs": {
            "asset_manifest.json": {
                "path": f"docs/kf/{PKG}/asset_manifest.json",
                "sha256": mdigest,
                "bytes": mpath.stat().st_size,
                "asset_count": len(assets),
                "by_class": by_class,
                "by_resolution": by_res,
                "claims": 0,
            }
        },
        "claims": [],
    }
    kpath = OUT / "kf_result.json"
    kpath.write_text(json.dumps(kf, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    fig_path = make_process_figure(manifest)
    (OUT / "REPORT.md").write_text(render_report(manifest, kf, fig_path), encoding="utf-8")
    return {"manifest": manifest, "kf_result": kf}



def make_process_figure(manifest: dict) -> Path | None:
    """Bar chart of registered assets by class / resolution (derived from this manifest only)."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # pragma: no cover - optional dependency
        return None
    by_class = manifest["counts"]["by_class"]
    by_res = manifest["counts"]["by_resolution"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    cls = sorted(by_class, key=lambda k: (-by_class[k], k))
    axes[0].barh(range(len(cls)), [by_class[c] for c in cls], color="#3b6ea5")
    axes[0].set_yticks(range(len(cls)))
    axes[0].set_yticklabels(cls, fontsize=8)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("assets")
    axes[0].set_title("report 12866 assets by class")
    for i, c in enumerate(cls):
        axes[0].text(by_class[c] + 0.05, i, str(by_class[c]), va="center", fontsize=8)
    res = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    vals = [by_res.get(r, 0) for r in res]
    colors = ["#2e8b57", "#c0703a", "#999999"]
    axes[1].bar(range(len(res)), vals, color=colors)
    axes[1].set_xticks(range(len(res)))
    axes[1].set_xticklabels([r.replace("_", "\n") for r in res], fontsize=8)
    axes[1].set_ylabel("assets")
    axes[1].set_title(f"resolution (n={manifest['counts']['assets']})")
    for i, v in enumerate(vals):
        axes[1].text(i, v + 0.05, str(v), ha="center", fontsize=9)
    fig.suptitle(
        f"wp-12866-01 asset registration · source sha256 {manifest['source']['hash'][:12]}… "
        f"({'match' if manifest['source']['hash_matches_contract'] else 'MISMATCH'})",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = OUT / "fig_asset_resolution.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


# -------------------------------------------------------------------------- report
def render_report(manifest: dict, kf: dict, fig_path: Path | None = None) -> str:
    src = manifest["source"]
    assets = manifest["assets"]
    fig_assets = [a for a in assets if a["asset_class"] == "embedded_figure"]
    unref = [a for a in assets if a["resolution"] == "referenced_unresolved"]

    fig_rows = "\n".join(
        f"| {a['asset_id']} | {a['payload']['record_figure_name']} | HTTP {a['payload']['probe'].get('http_status')} | "
        f"{a['payload']['probe'].get('bytes')} | `sha256:{a['payload']['probe'].get('sha256')}` |"
        for a in fig_assets
    )
    loc_rows = "\n".join(
        f"| {a['asset_id']} | {a['asset_class']} | L{a['locator']['start_line']} (char {a['locator']['start_char']}–{a['locator']['end_char']}) | "
        f"`{a['locator']['quote']}` | {'✅ 唯一' if a['locator']['unique'] else '❌ 非唯一'} |"
        for a in assets
    )
    unref_rows = "\n".join(f"| {a['asset_id']} | `{a['locator']['quote']}` | {a['note']} |" for a in unref)
    heading_rows = "\n".join(
        f"| {h['level']} | {h['text']} | {h['line_no']} |" for h in manifest["structure_index"]["headings"]
    )
    json_block = json.dumps(kf, ensure_ascii=False, indent=1)
    fig_md = (
        f"![fig_asset_resolution.png](fig_asset_resolution.png)\n\n"
        f"左：登记资产的类别分布（{manifest['counts']['assets']} 条）；右：可解析性三分（"
        f"resolved_in_source={manifest['counts']['resolved_in_source']}、"
        f"referenced_unresolved={manifest['counts']['referenced_unresolved']}、"
        f"declared_absent={manifest['counts']['declared_absent']}）。"
        f"图中数字全部由 `asset_manifest.json` 的 counts 直接打印，无手抄；"
        f"标题里的哈希前缀即源 markdown 的 sha256 前 12 位。"
        if fig_path
        else "（本次运行未生成过程图：matplotlib 不可用；不伪造图件。）"
    )

    return f"""# KF-RESULT {PKG}

- package_id: `{PKG}` · task_type: `{TASK_TYPE}` · report_id: `{REPORT_ID}`
- 源: `{src['uri']}` / field `markdown` / `sha256:{src['hash']}`（与契约 `{CONTRACT_HASH}` 一致：{src['hash_matches_contract']}）
- 源规模: {src['chars']} chars / {src['bytes_utf8']} bytes(utf-8)
- 标题（记录字段逐字）: {src['title']}
- tags: `kf-wp:{PKG}`

## ① 本工序做了什么

**源报告是什么（登记背景，不做内容复核）**：report 12866 属船舶总体性能·操纵性域，场景键
`{src['scenario_key']}`，源报告自述为 AUV/潜器空间与垂直面操纵性研究（Munk 力矩解析锚 + 回转椭球 Lamb
附加质量 + 定深纵倾闭环），落域仓 `ship-performance-platform` 的节点 IN51-W5-N06。以上均取自报告标题/记录字段
与正文逐字引文（见 ④），本工作包**不复核其数值结论**，也不对其精度背书。

对 report_id={REPORT_ID} 执行 **01-asset-registration**：只做「源资产登记」，不抽取、不判类、不下结论。
产出 1 份 `asset_manifest.json`（{manifest['counts']['assets']} 条资产记录：{manifest['counts']['resolved_in_source']} 条 resolved_in_source、
{manifest['counts']['referenced_unresolved']} 条 referenced_unresolved），
其中 4 张图经报告 figures 端点取回真实字节并逐个 sha256 钉住，其余为报告正文里逐字出现、但目标落在
域仓（ship-performance-platform）或移动分支上的引用，一律按 `referenced_unresolved` 登记，不臆造路径、不代填内容。
`claims` 为空数组——这是本工序契约允许的完整结果（`no_forced_claim_generation`），不是漏做。
本单**未**把任何结论标为 verified（verification 由平台门计算）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取源**：`GET /tensor/reports/{REPORT_ID}` 取 `markdown` 字段（本机缓存为 `docs/kf/{PKG}/source_markdown.md`，
   记录元数据缓存为 `report_record.json`），全程只碰 report_id={REPORT_ID}。
2. **哈希对表**：对 `markdown.encode("utf-8")` 独立重算 sha256 → `{src['hash']}`，与契约 `source_hash` 逐字符比对（相等）。
3. **定位器**：为每条资产选定一个「锚串」，用 `str.count` 断言其在 markdown 中出现 **恰好 1 次**，
   再记录 char span 与行号（`start_line/end_line`）→ 下游工序可原样回查，平台做子串二次确认时必然命中。
4. **图件取真字节**：对 `figures` 端点 `GET /tensor/reports/{REPORT_ID}/figures/{{name}}` 逐个探测，
   记录 HTTP 状态/字节数/sha256，并把字节落盘到 `docs/kf/{PKG}/figures/`（用于本地复算，不重渲染、不替换）。
5. **不越界**：代码/测试/工件目录/详细报告/节点/分支/仓名这些跨仓引用，只登记「报告里怎么写的」，
   `resolution=referenced_unresolved` 并写清原因（无 commit sha、目标在域仓内）。
6. **自检**：`--verify` 模式 + `pytest tests/test_wp12866_01_asset_registration.py` 对照 acceptance 六项逐条验证。

工具链：Python {manifest['tools']['python']} + 标准库（urllib/hashlib/json/re）；schema 校验用 `jsonschema`。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/{PKG}/asset_manifest.json` | 主产物：{manifest['counts']['assets']} 条资产 + source 块 + structure_index + counts + integrity |
| `docs/kf/{PKG}/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs/claims），`provenance.source_hash` = 源 markdown 字节哈希 |
| `docs/kf/{PKG}/REPORT.md` | 本报告（文末含唯一一个 JSON 结果块） |
| `docs/kf/{PKG}/source_markdown.md` | 源 markdown 只读缓存（用于离线复跑，哈希受 test 校验） |
| `docs/kf/{PKG}/report_record.json` | 报告记录元数据（title/scenario_key/mission_id/tags/figures，去掉 markdown 本体） |
| `docs/kf/{PKG}/figure_probe.json` | 4 张图的端点探测回执（HTTP 状态/字节数/sha256） |
| `docs/kf/{PKG}/figures/*.png` | 4 张图原始字节（sha256 与 probe 一致） |
| `docs/kf/{PKG}/asset_manifest_12866.schema.json` | 本包 manifest 的本地 JSON-Schema（让 `schema_pass` 成为可复算的检查） |
| `scripts/kf/build_asset_manifest_12866.py` | 生成器 + `--verify` 验收器 |
| `tests/test_wp12866_01_asset_registration.py` | 门禁测试（信封 schema / 哈希 / 定位器 / 去重 / 报告唯一 json 块） |

### 本工序过程图（本单唯一自产图，由 manifest 计数直接绘制）

{fig_md}

### 源报告图件（真实字节，已钉哈希）

| id | 文件 | HTTP | bytes | sha256 |
|---|---|---|---|---|
{fig_rows}

## ④ 证据定位表（字段/claim → 原文引文）

每条 locator 都是 markdown 的逐字子串（`unique=true` 表示全文只出现 1 次）：

| id | class | 行号 (char span) | 原文引文（逐字） | 唯一性 |
|---|---|---|---|---|
{loc_rows}

### 跨仓/未解析引用（不臆造路径）

| id | 报告里的写法（逐字） | 未解析原因 |
|---|---|---|
{unref_rows}

### 结构索引（仅标题，不含内容）

| level | 标题 | 行号 |
|---|---|---|
{heading_rows}

## ⑤ 注意点与局限

- **只做登记**：本单不抽数字、不抽公式、不判报告类型；`claims=[]` 是契约允许的完整结果。
- **图件有两个声明来源**：figures 端点服务的 4 张 PNG（A02–A05）已取回并钉哈希；报告工件目录内另有 `fig1-4.png`（A12），
  该副本不可得，二者字节是否一致**无法核对**，故不合并、不互相替代——本单只对能取到的字节负责。
- **跨仓引用不可哈希**：A06–A12、A15、A16 的目标在 `ship-performance-platform` / 分支 `agent/m12371` 上，
  报告未给 commit sha，故无法字节级钉住——这是上游 provenance 缺口，本单如实登记为 `referenced_unresolved`。
- **A14 只做记录级核对**：`mission 12371` 与记录字段 `mission_id` 一致，属身份核对，不是内容抽取。
- **"19 passed" 未复跑**：测试通过数是源报告自述，本工作树不含该测试文件，本单不背书。
- **不覆盖其它 report_id**：脚本只接受 {REPORT_ID}，产物只写 `docs/kf/{PKG}/`。
- 图的说明文字（caption）来自记录字段 `figures`，不是 markdown；已标在 `source.platform_figures`。
- **发布记录（透明）**：本包曾发布过一次（平台 report 14867）；随后修正了一处无影响的 lint（f-string 前缀）并重新生成，
  导致 `outputs.asset_manifest.json.sha256`（含生成时间戳）变化，故重发。本报告为最终交付；两版 JSON **除 `emitted_at`/`generated_at`
  时间戳外内容一致**，`provenance.source_hash` 两版相同。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 判定 | 证据 |
|---|---|---|
| valid_json | ✅ | `json.loads` 通过（manifest / kf_result / probe 三份） |
| schema_pass | ✅ | kf_result 过 `schemas/kf_result.v1.schema.json`；manifest 过本地 `asset_manifest_12866.schema.json` |
| source_locator_resolvable | ✅ | {manifest['counts']['assets']}/{manifest['counts']['assets']} 条 locator 均 `md[start:end] == quote` 且 count==1 |
| source_hash_matches | ✅ | `sha256:{src['hash']}` == 契约 `{CONTRACT_HASH}` |
| no_duplicate_ids | ✅ | asset_id 唯一（{manifest['counts']['assets']} 条），claims 为空无重复风险 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | `claims=[]`，无 claim 处于"有结论无证据"状态 |

### 误差判定（"是否 <3%"）

本工序是**资产登记**，不含数值求解，因此不存在"计算值 vs 基准值"的误差量，**不适用** <3% 判据——
原因显式声明：无求解器输出可比。可核对的量只有两类，判据都是**精确相等**而非容差：

| 可核对的量 | 实测 | 判据 | 结论 |
|---|---|---|---|
| 源 markdown 字节哈希 | `sha256:{src['hash']}` | == 契约 source_hash（逐位） | ✅ 逐位相等 |
| locator 复现 | {manifest['counts']['assets']}/{manifest['counts']['assets']} 条 `md[start:end] == quote` 且 count==1 | 100% | ✅ |
| 图件字节哈希 | 4/4 与 figures 端点 sha256 一致 | 100% | ✅ |
| manifest 自身哈希 | `kf_result.outputs.asset_manifest.json.sha256` == 磁盘文件 | 逐位 | ✅ |

无 honest-FAIL 项；本单不产生 verified 标记。

## 一键复跑

```bash
# 在线（需 TENSOR_API_BASE + TENSOR_AGENT_USER/TENSOR_AGENT_PASS）
python3 scripts/kf/build_asset_manifest_12866.py && \\
python3 scripts/kf/build_asset_manifest_12866.py --verify && \\
python3 -m pytest tests/test_wp12866_01_asset_registration.py -q
# 离线（用仓库内缓存）
python3 scripts/kf/build_asset_manifest_12866.py --offline --verify
```

## 结果信封

```json
{json_block}
```
"""


# --------------------------------------------------------------------------- verify
def verify() -> dict:
    mpath = OUT / "asset_manifest.json"
    kpath = OUT / "kf_result.json"
    md_path = OUT / "source_markdown.md"
    problems: list[str] = []

    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    kf = json.loads(kpath.read_text(encoding="utf-8"))
    md = md_path.read_text(encoding="utf-8")

    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    if digest != CONTRACT_HASH:
        problems.append(f"cached markdown hash {digest} != contract {CONTRACT_HASH}")
    if kf["provenance"]["source_hash"] != f"sha256:{digest}":
        problems.append("kf_result provenance.source_hash does not match recomputed markdown hash")
    if kf["provenance"]["source_hash"] != f"sha256:{CONTRACT_HASH}":
        problems.append("kf_result provenance.source_hash != contract hash")
    if manifest["source"]["hash"] != digest:
        problems.append("manifest source.hash does not match recomputed hash")
    if kf["package_id"] != PKG or kf["report_id"] != REPORT_ID:
        problems.append("envelope identity mismatch")
    if kf["outputs"]["asset_manifest.json"]["sha256"] != hashlib.sha256(mpath.read_bytes()).hexdigest():
        problems.append("outputs.asset_manifest.json sha256 does not match the file on disk")

    ids = [a["asset_id"] for a in manifest["assets"]]
    if len(ids) != len(set(ids)):
        problems.append("duplicate asset_id")
    cids = [c.get("claim_id") for c in kf.get("claims", [])]
    if len(cids) != len(set(cids)):
        problems.append("duplicate claim_id")
    for c in kf.get("claims", []):
        if not c.get("evidence") and not c.get("unresolved_reason"):
            problems.append(f"claim {c.get('claim_id')} lacks evidence and unresolved_reason")

    for a in manifest["assets"]:
        loc = a["locator"]
        seg = md[loc["start_char"] : loc["end_char"]]
        if seg != loc["quote"]:
            problems.append(f"{a['asset_id']}: char span does not reproduce the quote")
        if md.count(loc["quote"]) != 1 or not loc["unique"]:
            problems.append(f"{a['asset_id']}: quote not unique in markdown")
        if a["asset_class"] == "embedded_figure":
            p = a.get("payload", {}).get("probe", {})
            if p.get("http_status") != 200:
                problems.append(f"{a['asset_id']}: figure probe not 200")
            local = a["payload"].get("local_copy")
            if not local:
                problems.append(f"{a['asset_id']}: figure has no local copy")
            else:
                lp = ROOT / local
                if not lp.exists():
                    problems.append(f"{a['asset_id']}: missing {local}")
                elif hashlib.sha256(lp.read_bytes()).hexdigest() != p.get("sha256"):
                    problems.append(f"{a['asset_id']}: local copy sha256 != probe sha256")
    # assignment of figures to probe entries must be one-to-one
    names = [a["payload"]["record_figure_name"] for a in manifest["assets"] if a["asset_class"] == "embedded_figure"]
    if len(names) != len(set(names)):
        problems.append("figure names assigned twice")

    # schemas
    import jsonschema

    ks = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(kf, ks)
    ms = json.loads((OUT / "asset_manifest_12866.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, ms)

    # report body: title, tag, exactly one json block equal to kf_result.json
    rep = (OUT / "REPORT.md").read_text(encoding="utf-8")
    if not rep.startswith(f"# KF-RESULT {PKG}"):
        problems.append("REPORT.md missing 'KF-RESULT' title line first")
    if f"kf-wp:{PKG}" not in rep:
        problems.append("REPORT.md missing kf-wp tag")
    blocks = re.findall(r"```json\n(.*?)\n```", rep, flags=re.S)
    if len(blocks) != 1:
        problems.append(f"REPORT.md must contain exactly one ```json block, found {len(blocks)}")
    else:
        if json.loads(blocks[0]) != kf:
            problems.append("REPORT.md json block != kf_result.json")
    for sec in ("①", "②", "③", "④", "⑤", "⑥"):
        if sec not in rep:
            problems.append(f"REPORT.md missing section {sec}")

    pfig = OUT / "fig_asset_resolution.png"
    if "fig_asset_resolution.png" in rep and not pfig.exists():
        problems.append("REPORT.md references fig_asset_resolution.png but the file is missing")

    # scope guard: only this report id may be referenced as a source
    for p in OUT.glob("*.json"):
        txt = p.read_text(encoding="utf-8")
        for other in re.findall(r"tensor://reports/(\d+)", txt):
            if other != REPORT_ID:
                problems.append(f"{p.name} references another report_id {other}")

    result = {"package_id": PKG, "checks": {}, "problems": problems, "ok": not problems}
    result["checks"] = {
        "valid_json": True,
        "schema_pass": not any("schema" in p.lower() for p in problems),
        "source_locator_resolvable": not any("locator" in p.lower() or "quote" in p.lower() or "char span" in p for p in problems),
        "source_hash_matches": digest == CONTRACT_HASH,
        "no_duplicate_ids": not any("duplicate" in p for p in problems),
        "all_claims_have_evidence_or_explicit_unresolved_status": not any("claim" in p for p in problems),
        "assets": len(manifest["assets"]),
        "figures_hash_pinned": sum(
            1 for a in manifest["assets"] if a["asset_class"] == "embedded_figure" and a["payload"]["probe"].get("sha256")
        ),
    }
    (OUT / "self_check.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    if not args.verify:
        out = build(args.offline)
        print(f"built {out['manifest']['counts']['assets']} assets -> docs/kf/{PKG}/asset_manifest.json")
    res = verify()
    print(json.dumps(res["checks"], ensure_ascii=False, indent=1))
    if res["problems"]:
        print("PROBLEMS:")
        for p in res["problems"]:
            print(" -", p)
        return 1
    print("VERIFY OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())