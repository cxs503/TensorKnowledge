#!/usr/bin/env python3
"""从受版本控制的交付镜像重建 wp-615-01 的工作区（artifacts/kf/wp-615-01/）。

为什么需要它
------------
`artifacts/**` 被 .gitignore 忽略（mission-push 门会丢弃该目录），而交付镜像
`knowledge/kf/wp-615-01/` 才随分支进 git。于是**全新检出上 artifacts/ 是空的**，
`tests/test_kf_wp_615_01.py` 会因缺文件整体报红——这正是 PR#253 关闭后这套交付物
在 main 上"看起来在、实际不可复验"的故障根因。

本脚本把「受控镜像 → 工作区」的重建过程显式化，并且**不只搬运，还要复算**：

  1. `asset_manifest.json` / `kf_result.json`：镜像 → 工作区（字节复制）。
  2. `source_snapshot/report_615.json`：由镜像 `report_615.md`（唯一权威源）+
     清单 `source.record_fields` 复原记录壳；复原前先重算 markdown 的 sha256，
     必须等于契约 `source_hash`，否则立即失败。
  3. `checks.json`：不直接复制，改由 `verify()` 在**离线**下把每一项重算一遍
     （哈希/引文逐字可定位/偏移回读/ID 唯一/两条 JSON Schema），
     重算结果必须与镜像逐字节相同，才落盘。
  4. `figures/wp61501_asset_registry.png`：镜像（已提交二进制，跨 matplotlib 版本
     逐字节稳定）→ 工作区；镜像缺图时才重绘并回写镜像 + `figure_meta.json`。
  5. `docs/kf/KF-RESULT-wp-615-01.md` 与 `report_payload.json`：由 `emit()` 重新渲染，
     渲染结果必须与提交件逐字节相同，否则判定"文档与清单漂移"并失败。

全程离线：不访问平台、不需要 token。

用法：
  python3 scripts/kf/wp_615_01_bootstrap_artifacts.py             # 重建 + 复算 + 漂移检查
  python3 scripts/kf/wp_615_01_bootstrap_artifacts.py --render-figure  # 强制重绘图件
  python3 scripts/kf/wp_615_01_bootstrap_artifacts.py --status    # 只报告工作区状态
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))  # 复用工序 01 的校验器与渲染器，避免出现第二套口径

import build_wp_615_01_report as render  # noqa: E402
import wp_615_01_register_assets as reg  # noqa: E402

PKG = "wp-615-01"
OUT = ROOT / "artifacts" / "kf" / PKG
MIRROR = ROOT / "knowledge" / "kf" / PKG
DOCS = ROOT / "docs" / "kf" / f"KF-RESULT-{PKG}.md"
FIG_NAME = render.FIG_NAME
BYTE_COPIED = ("asset_manifest.json", "kf_result.json")


class ArtifactDriftError(RuntimeError):
    """重建结果与提交件不一致：说明文档/图件不是清单的确定性函数。"""


def _sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_record(mirror: Path = MIRROR) -> dict[str, Any]:
    """由镜像 markdown + 清单记录字段复原 report 615 的记录壳（离线，不含网络字段）。"""
    manifest = json.loads((mirror / "asset_manifest.json").read_text())
    md = (mirror / "report_615.md").read_bytes().decode("utf-8")
    digest = _sha256(md.encode("utf-8"))
    pinned = manifest["source"]["source_hash"]
    if digest != pinned:
        raise ArtifactDriftError(
            f"镜像 markdown 指纹与清单不符：重算 {digest} ≠ 清单 {pinned}"
        )
    rf = manifest["source"]["record_fields"]
    fig = next((a for a in manifest["assets"] if a["kind"] == "figure"), None)
    return {
        "id": int(manifest["source"]["report_id"]),
        "title": rf["title"],
        "markdown": md,
        "scenario_key": rf["scenario_key"],
        "mission_id": rf["mission_id"],
        "status": rf["status"],
        "created_at": rf["created_at"],
        "tags": list(rf["tags"]),
        "figures": (
            [{"name": fig["uri"].rsplit("/", 1)[-1], "caption": fig["caption"]}] if fig else []
        ),
    }


def _write_if_changed(path: Path, data: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == data:
        return False
    path.write_bytes(data)
    return True


def _write_figure_meta(mirror: Path, out: Path, fig_bytes: bytes) -> Path:
    """登记图件渲染来源（版本/尺寸/DPI/输入指纹），让"图件是哪次渲染出来的"可审计。"""
    import matplotlib

    w = h = None
    png = out / "figures" / FIG_NAME
    try:  # 只读 IHDR，不引入额外依赖
        raw = png.read_bytes()
        w, h = int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big")
    except Exception:  # pragma: no cover
        pass
    manifest = json.loads((out / "asset_manifest.json").read_text())
    meta = {
        "file": FIG_NAME,
        "sha256": _sha256(fig_bytes),
        "bytes": len(fig_bytes),
        "width_px": w,
        "height_px": h,
        "dpi": 150,
        "matplotlib": matplotlib.__version__,
        "producer": "scripts/kf/build_wp_615_01_report.py::make_figure",
        "inputs": {
            "asset_manifest_sha256": _sha256((out / "asset_manifest.json").read_bytes()),
            "checks_sha256": _sha256((out / "checks.json").read_bytes()),
            "source_hash": manifest["source"]["source_hash"],
        },
        "note": ("跨环境的 matplotlib 版本会改变 PNG 编码字节，故提交本图件作为交付二进制；"
                 "知识包内这份图件即工作区 artifacts/ 的逐字节来源。"),
    }
    path = mirror / "figures" / "figure_meta.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    return path


def bootstrap(out: Path = OUT, mirror: Path = MIRROR, render_figure: bool = False,
              strict: bool = True) -> dict[str, Any]:
    """重建 out 目录并复算全部不变量；strict 时对任何漂移抛 ArtifactDriftError。"""
    out, mirror = Path(out), Path(mirror)
    committed_docs = DOCS.read_bytes() if DOCS.exists() else None
    committed_mirror_docs = (mirror / "KF-RESULT.md").read_bytes() if (mirror / "KF-RESULT.md").exists() else None

    # 1. 清单/信封：字节复制
    facts: dict[str, Any] = {"byte_copied": [], "recomputed": {}, "written": []}
    for name in BYTE_COPIED:
        data = (mirror / name).read_bytes()
        if _write_if_changed(out / name, data):
            facts["written"].append(name)
        facts["byte_copied"].append(name)

    # 2. 源快照：markdown 由镜像逐字节落盘，记录壳由清单复原
    rec = build_record(mirror)
    snap_dir = out / "source_snapshot"
    snap_json = (json.dumps(rec, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    for path, data in ((snap_dir / "report_615.md", rec["markdown"].encode("utf-8")),
                       (snap_dir / "report_615.json", snap_json)):
        if _write_if_changed(path, data):
            facts["written"].append(str(path.relative_to(out)))

    # 3. checks.json：离线复算后与镜像逐字节比对（不盲复制）
    manifest = json.loads((mirror / "asset_manifest.json").read_text())
    recomputed = reg.verify(manifest, None, md_source=rec["markdown"])
    recomputed_bytes = (json.dumps(recomputed, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    committed_checks = (mirror / "checks.json").read_bytes()
    facts["recomputed"]["checks_match_mirror"] = recomputed_bytes == committed_checks
    facts["recomputed"]["all_pass"] = bool(recomputed.get("all_pass"))
    if strict and recomputed_bytes != committed_checks:
        out_checks = json.loads(committed_checks)
        diff = {k: (out_checks.get(k), recomputed.get(k))
                for k in set(out_checks) | set(recomputed) if out_checks.get(k) != recomputed.get(k)}
        raise ArtifactDriftError(f"离线复算与镜像 checks.json 不一致：{diff}")
    if _write_if_changed(out / "checks.json", recomputed_bytes):
        facts["written"].append("checks.json")

    # 4 + 5. 图件 / 文档 / 平台载荷：交给 render.emit（图件默认复用镜像字节）
    payload = render.emit(out, render_figure=render_figure)
    fig_bytes = (out / "figures" / FIG_NAME).read_bytes()
    facts["figure_sha256"] = _sha256(fig_bytes)
    facts["payload_b64_chars"] = len(payload["figures"][0]["png_base64"])
    if render_figure or not (mirror / "figures" / "figure_meta.json").exists():
        _write_figure_meta(mirror, out, fig_bytes)
    facts["figure_meta"] = json.loads((mirror / "figures" / "figure_meta.json").read_text())

    # 漂移检查：重新渲染的文档必须与提交件逐字节相同
    if strict:
        for label, path, before in (("docs", DOCS, committed_docs),
                                    ("mirror", mirror / "KF-RESULT.md", committed_mirror_docs)):
            if before is None:
                continue
            after = path.read_bytes()
            if after != before:
                path.write_bytes(before)  # 立刻回滚，别把漂移留在工作区
                raise ArtifactDriftError(
                    f"{label} 文档不是清单的确定性函数：渲染 {len(after)}B ≠ 提交 {len(before)}B ({path})"
                )
    facts["docs_byte_identical"] = True
    return facts


def status(out: Path = OUT) -> dict[str, Any]:
    """只报告工作区必备文件是否齐备（不写任何东西）。"""
    need = [out / n for n in ("asset_manifest.json", "kf_result.json", "checks.json",
                              "report_payload.json",
                              "source_snapshot/report_615.json", "source_snapshot/report_615.md",
                              f"figures/{FIG_NAME}")]
    return {str(p.relative_to(out)): p.exists() for p in need}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--mirror", default=str(MIRROR))
    ap.add_argument("--render-figure", action="store_true", help="强制重绘图件并回写知识包")
    ap.add_argument("--status", action="store_true", help="只报告工作区状态")
    ap.add_argument("--no-strict", action="store_true", help="漂移只报错不抛异常（排障用）")
    args = ap.parse_args()
    if args.status:
        print(json.dumps(status(Path(args.out)), ensure_ascii=False, indent=2))
        return 0
    try:
        facts = bootstrap(Path(args.out), Path(args.mirror), render_figure=args.render_figure,
                          strict=not args.no_strict)
    except ArtifactDriftError as exc:
        print(f"DRIFT: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(facts, ensure_ascii=False, indent=2))
    return 0 if facts["recomputed"]["checks_match_mirror"] else 1


if __name__ == "__main__":
    raise SystemExit(main())