#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wp-9645-01 门的证伪实验：篡改多少，门就得红多少。

一套「永远绿」的验收门没有证据价值。本脚本对 wp-9645-01 的两道门做**受控篡改**：

  A. locator 门（工序 01 的 ``build_locator_check``）——把 manifest 里前 k 个 section
     哈希换成 poison 值（k = 0…8），统计门检出的失败项数；
  B. 快照门（``scripts/kf/wp_9645_01_snapshot.py::verify_snapshot``）——在快照字节里
     定点翻转 n 个字符（n = 0/1/2/4/8/16），统计门是否仍然 all_pass。

期望（可证伪的判据，写在产物里，不写在嘴上）：
  * k=0 → 失败项 0（无假阳性）；
  * k≥1 → 失败项恰为 k（1:1 检出，不漏检、不放大）；
  * n=0 → all_pass=True；n≥1 → all_pass=False（单字符即可翻红）。

产物（程序化生成，数值零手抄）：
  docs/kf/wp-9645-01/gate_sensitivity.json
  docs/kf/wp-9645-01/gate_sensitivity.png

用法：python3 scripts/kf/wp_9645_01_gate_sensitivity.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PKG = os.path.join(ROOT, "docs", "kf", "wp-9645-01")
SNAPSHOT_MD = os.path.join(PKG, "source", "report_9645.md")
OUT_JSON = os.path.join(PKG, "gate_sensitivity.json")
OUT_PNG = os.path.join(PKG, "gate_sensitivity.png")

REGISTER = os.path.join(ROOT, "scripts", "kf", "wp_9645_01_register.py")
SNAPTOOL = os.path.join(ROOT, "scripts", "kf", "wp_9645_01_snapshot.py")

# 定点翻转：抓快照里确定存在的锚点字符，逐次改成另一个仍合法的字符
FLIP_ANCHORS = (
    ("ISO 19906", "ISO 19907"),
    ("gamma_f", "gamma_g"),
    ("FORM", "FQRM"),
    ("Newton", "Newt0n"),
    ("importance", "importanc3"),
    ("beta", "b3ta"),
)


def _load(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def locator_sensitivity(register, manifest: dict, markdown: str) -> list:
    rows = []
    n = len(manifest["sections"])
    base = register.build_locator_check(manifest, markdown)
    for k in range(n + 1):
        poisoned = json.loads(json.dumps(manifest))
        for sec in poisoned["sections"][:k]:
            sec["sha256"] = "sha256:" + "0" * 64
        verdict = register.build_locator_check(poisoned, markdown)
        failed = sum(1 for c in verdict["checks"] if not c["pass"])
        rows.append(
            {
                "tampered_sections": k,
                "failed_checks": failed,
                "gate_all_pass": verdict["all_pass"],
                "detection_ratio": (failed / k) if k else None,
                "false_positive": bool(k == 0 and failed != 0),
            }
        )
    return rows, base["all_pass"]


def snapshot_sensitivity(snapshot_tool, manifest: dict, markdown: str) -> list:
    targets = snapshot_tool.pinned_targets(manifest)
    rows = []
    for n in (0, 1, 2, 4, 8, 16):
        text = markdown
        flips = 0
        for idx in range(n):
            anchor, replacement = FLIP_ANCHORS[idx % len(FLIP_ANCHORS)]
            if anchor not in text:
                continue
            text = text.replace(anchor, replacement, 1)
            flips += 1
        verdict = snapshot_tool.verify_snapshot(text.encode("utf-8"), targets)
        rows.append(
            {
                "flipped_chars": flips,
                "verify_all_pass": verdict["all_pass"],
                "failed_items": [c["item"] for c in verdict["checks"] if not c["pass"]],
                "detected": not verdict["all_pass"],
            }
        )
    return rows, snapshot_tool.verify_snapshot(markdown.encode("utf-8"), targets)["all_pass"]


def plot(rows_a: list, rows_b: list, manifest: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    k = np.array([r["tampered_sections"] for r in rows_a])
    failed = np.array([r["failed_checks"] for r in rows_a])
    ax1.plot([0, k.max()], [0, k.max()], "--", color="#999999", lw=1, label="ideal 1:1 detection")
    ax1.bar(k, failed, width=0.55, color="#c62828", alpha=0.85, label="failed checks in locator gate")
    ax1.set_xlabel("tampered section hashes (k, corruption injected)", fontsize=10)
    ax1.set_ylabel("failed checks reported by build_locator_check", fontsize=10)
    ax1.set_title(
        "Gate A — locator gate: 8 sections, %d/%d detected at full corruption"
        % (rows_a[-1]["failed_checks"], len(manifest["sections"])),
        fontsize=11,
    )
    ax1.set_xticks(k)
    ax1.legend(fontsize=8, loc="upper left")
    ax1.grid(alpha=0.3)

    n = np.array([r["flipped_chars"] for r in rows_b])
    detected = np.array([1.0 if r["detected"] else 0.0 for r in rows_b])
    colors = ["#2e7d32" if d else "#c62828" for d in detected]
    ax2.bar(range(len(n)), detected, width=0.55, color=colors, alpha=0.85)
    ax2.set_xticks(range(len(n)))
    ax2.set_xticklabels([str(int(v)) for v in n])
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(["no alarm\n(≤0 passes)", "alarm\n(snapshot rejected)"])
    ax2.set_ylim(0, 1.25)
    ax2.set_xlabel("flipped characters in the 11824-char source snapshot", fontsize=10)
    ax2.set_title(
        "Gate B — snapshot verifier: 1:\\u200bchar flip is already fatal", fontsize=11
    )
    for i, r in enumerate(rows_b):
        ax2.text(
            i,
            detected[i] + 0.04,
            "pass" if not r["detected"] else "rejected",
            ha="center",
            fontsize=8,
        )
    ax2.grid(alpha=0.3, axis="y")

    fig.suptitle(
        "wp-9645-01 falsifiability experiment — gates must go red exactly when the source drifts",
        fontsize=12,
    )
    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    plt.close()


def main() -> int:
    register = _load(REGISTER, "wp9645_register")
    snapshot_tool = _load(SNAPTOOL, "wp9645_snapshot")
    with open(os.path.join(PKG, "asset_manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    with open(SNAPSHOT_MD, "rb") as f:
        markdown = f.read().decode("utf-8")

    rows_a, clean_a = locator_sensitivity(register, manifest, markdown)
    rows_b, clean_b = snapshot_sensitivity(snapshot_tool, manifest, markdown)

    checks = {
        "no_false_positive_at_k0": rows_a[0]["failed_checks"] == 0,
        "one_to_one_detection": all(
            r["failed_checks"] == r["tampered_sections"] for r in rows_a[1:]
        ),
        "clean_locator_gate_passes": clean_a is True,
        "single_char_flip_is_fatal": rows_b[1]["detected"] is True,
        "clean_snapshot_passes": rows_b[0]["verify_all_pass"] is True and clean_b is True,
        "no_missed_flips": all(r["detected"] for r in rows_b[1:]),
    }

    result = {
        "package_id": "wp-9645-01",
        "report_id": "9645",
        "generator": "scripts/kf/wp_9645_01_gate_sensitivity.py",
        "definition": {
            "gate_a": "register.build_locator_check(manifest with first k section hashes poisoned, snapshot)",
            "gate_b": "scripts/kf/wp_9645_01_snapshot.py::verify_snapshot(snapshot with n flipped chars)",
        },
        "sections": len(manifest["sections"]),
        "source_chars": len(markdown),
        "gate_a_locator": rows_a,
        "gate_b_snapshot": rows_b,
        "checks": checks,
        "all_pass": all(checks.values()),
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    plot(rows_a, rows_b, manifest)
    print(json.dumps({"all_pass": result["all_pass"], "checks": checks}, ensure_ascii=False, indent=2))
    print("WROTE", os.path.relpath(OUT_JSON, ROOT))
    print("WROTE", os.path.relpath(OUT_PNG, ROOT))
    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())