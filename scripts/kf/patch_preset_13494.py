"""One-off patch: add the wp-13494-01 preset to scripts/kf/kf01_register.py and de-hardcode the
report renderer's producing-repository prose (it was pinned to the wp-7450-01 package).

Run once: python3 scripts/kf/patch_preset_13494.py   (idempotent: exits 0 if already applied)
"""
from __future__ import annotations

import pathlib

P = pathlib.Path("scripts/kf/kf01_register.py")
src = P.read_text(encoding="utf-8")

PRESET_ANCHOR = '    }\n}\n\nBASE = os.environ["TENSOR_API_BASE"].rstrip("/")'
PRESET_NEW = '''    },
    "wp-13494-01": {
        "package_id": "wp-13494-01",
        "report_id": "13494",
        "expected_hash": "ad61f9e0bc3dbe8c8f4ae40ce90056f06c98477c9a33302193f8297756783abe",
        "expected_chars": 12251,
        "title": "TensorDEM GPU 100K Gate \\u2014 CPU Scaling & Correctness Verification",
        "scenario_key": "p447w2-n03-dem-gpu-100k",
        "out_dir": "docs/kf/wp-13494-01",
        "producer_repo": "TensorDEM",
        "mission_id": 15761,
    },
}

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")'''

DERIVED_ANCHOR = '    n = manifest["counts"]["assets"]\n'
DERIVED_NEW = '''    n = manifest["counts"]["assets"]
    pkg = cfg["package_id"]
    producer = cfg.get("producer_repo", "(producing repository not declared by the package config)")
    cnt = manifest["counts"]
    # Prose facts are derived from the manifest, not typed per package.
    unref = sorted({a.get("path_reference") for a in manifest["assets"]
                    if a.get("resolution") == "referenced_unresolved" and a.get("path_reference")})
    meta_figs = [a for a in manifest["assets"] if a.get("asset_class") == "embedded_figure"
                 and a.get("resolution_detail") == "metadata_only"]
    blob_figs = [a for a in manifest["assets"] if a.get("asset_class") == "embedded_figure"
                 and a.get("resolution_detail") == "payload_present"]
    n_tables = cnt["by_class"].get("report_table", 0)
    red_note = (
        "红色柱不是缺陷而是**边界的正确表达**：这些路径属产出仓（%s），本包不得读写，"
        "故只能如实记 `referenced_unresolved`。" % producer if cnt["referenced_unresolved"] else
        "本清单没有 `referenced_unresolved` 资产：报告引用的可解析工件全部落在本工作树内。")
    figs_note = (
        "3. **图 %d 项只有元数据**：`record.figures[]` 共 %d 项，其中 %d 项 `png_base64` 为空（0 字节），"
        "只登记 name/caption + 正文出现位置，记 `metadata_only`（`resolution=referenced_unresolved`），"
        "**不宣称拿到图字节**。" % (len(meta_figs), len(meta_figs) + len(blob_figs), len(meta_figs))
        if meta_figs else
        "3. **图 %d 项带载荷**：`record.figures[]` 每项都有 `png_base64`，已按 sha256 记为 resolved。" % len(blob_figs))
    refs_note = (
        "4. **跨仓引用不可解析**：报告引用的 %s 等 %d 个路径属产出仓 %s，本工作树（TensorKnowledge）内不存在 "
        "→ 全部 `referenced_unresolved`，并在 `resolution_check.detail` 写明原因，不做「大概存在」的推断。"
        % ("、".join("`%s`" % p for p in unref[:2]) or "（无）", len(unref), producer)
        if unref else
        "4. **无跨仓引用**：清单没有 `referenced_unresolved` 路径资产。")
'''

REPLACEMENTS = [
    # ② step 5: producing repository is a package setting, not a literal
    ('        "5. **本地解析**：路径只在**本交付工作树**内解析（`os.path.isfile` + 命中文件 sha256）；'
     '属产出仓 ship-performance-platform 的路径",\n',
     '        "5. **本地解析**：路径只在**本交付工作树**内解析（`os.path.isfile` + 命中文件 sha256）；'
     '属产出仓 %s 的路径" % producer,\n'),
    # ④ red-bar note
    ('        "红色柱不是缺陷而是**边界的正确表达**：这些路径属产出仓（ship-performance-platform），'
     '本包不得读写，故只能如实记 `referenced_unresolved`。",\n',
     '        red_note,\n'),
    # ⑥ item 3 (figures) and item 4 (cross-repo refs), item 5 (tables)
    ('        "3. **图只有元数据**：报告记录 `figures[]` 两项均无 `png_base64` 载荷（0 字节），'
     '故只登记 name/caption + 正文出现位置，",\n'
     '        "   记 `metadata_only`（`resolution=referenced_unresolved`），**不宣称拿到图字节**。",\n',
     '        figs_note,\n'),
    ('        "4. **跨仓引用不可解析**：报告引用的 `backend/...py`、'
     '`artifacts/cii_crosscheck_m6284/...py` 等属 ship-performance-platform 仓，",\n'
     '        "   本工作树（TensorKnowledge）内不存在 → 全部 `referenced_unresolved`，'
     '并在 `resolution_check.detail` 写明原因，不做「大概存在」的推断。",\n',
     '        refs_note,\n'),
    ('        "5. **表格内容未复述**：表 1/2/3 只登记几何（行×列）与字符跨度，'
     '避免把报表数字二次转写引入漂移。",\n',
     '        "5. **表格内容未复述**：%d 张表只登记几何（行×列）与字符跨度，'
     '避免把报表数字二次转写引入漂移。" % n_tables,\n'),
    # repro command + payload caption carry the package id
    ('        "python3 scripts/kf/kf01_register.py --preset wp-7450-01 build result verify figure report'
     '   # 一键复跑（全流程）",\n',
     '        "python3 scripts/kf/kf01_register.py --preset %s build result verify figure report'
     '   # 一键复跑（全流程）" % pkg,\n'),
    ('        "repro_cmd: `python3 scripts/kf/kf01_register.py --preset wp-7450-01 build result verify'
     ' figure report`",\n',
     '        "repro_cmd: `python3 scripts/kf/kf01_register.py --preset %s build result verify'
     ' figure report`" % pkg,\n'),
    ('            "caption": "wp-7450-01 asset inventory & locator coverage map '
     '(computed from asset_manifest.json)",\n',
     '            "caption": "%s asset inventory & locator coverage map '
     '(computed from asset_manifest.json)" % pkg,\n'),
]


def main() -> int:
    updated = src
    applied = []
    if '"wp-13494-01": {' not in updated:
        if PRESET_ANCHOR not in updated:
            raise SystemExit("preset anchor not found; file drifted")
        updated = updated.replace(PRESET_ANCHOR, PRESET_NEW, 1)
        applied.append("preset")
    if 'pkg = cfg["package_id"]\n    producer = cfg.get("producer_repo"' not in updated:
        if DERIVED_ANCHOR not in updated:
            raise SystemExit("derived-var anchor not found; file drifted")
        updated = updated.replace(DERIVED_ANCHOR, DERIVED_NEW, 1)
        applied.append("derived-vars")
    for old, new in REPLACEMENTS:
        if old in updated:
            updated = updated.replace(old, new, 1)
            applied.append(old.strip()[:40])
        elif new not in updated:
            raise SystemExit("neither old nor new form present: %r" % old[:60])
    if not applied:
        print("already applied; nothing to do")
        return 0
    P.write_text(updated, encoding="utf-8")
    print("applied:", applied)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())