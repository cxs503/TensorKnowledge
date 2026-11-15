#!/usr/bin/env python3
"""Evidence figure for the wp-4129-01 reproducibility fix (round 2 / mission 21160).

Everything plotted here is *computed*, never typed in:

  panel A — regeneration determinism: the committed manifest is compared with
            `--offline` regeneration executed from three different working
            directories (after the fix), and with the same regeneration against
            the pre-fix manifest taken from `git show HEAD:` (before the fix).
  panel B — producer-path leakage census: occurrences of the producing checkout
            root (`/srv/tensor/agent/work/<producer>`) and of the foreign path that
            is quoted *from the source report* (allowed source data), before and
            after the fix.
  panel C — the KF gate tests of the touched packages, counted by running pytest.

Output: docs/kf/figures/wp-4129-01-repro.png
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts" / "kf_wp_4129_01_register.py"
MANIFEST_REL = "knowledge/kf/wp-4129-01/asset_manifest.json"
MANIFEST = ROOT / MANIFEST_REL
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    ROOT / "docs" / "kf" / "figures" / "wp-4129-01-repro.png")
GATES = [
    "tests/test_kf_wp_4129_01.py",
    "tests/test_kf_wp_4129_04.py",
    "tests/test_kf_wp_5559_01.py",
]


def _strip(manifest: dict) -> dict:
    m = json.loads(json.dumps(manifest))
    m.pop("generated_at", None)
    return m


def _leaf_diffs(a, b, path=""):
    """Paths of differing leaves between two decoded JSON payloads."""
    if type(a) is not type(b):
        return [path]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k in ("generated_at",):
                continue
            if k not in a or k not in b:
                out.append(f"{path}/{k}")
            else:
                out.extend(_leaf_diffs(a[k], b[k], f"{path}/{k}"))
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [path]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(_leaf_diffs(x, y, f"{path}[{i}]"))
        return out
    return [] if a == b else [path]


def regen(cwd: Path) -> dict:
    out = Path(tempfile.mkdtemp()) / "regen.json"
    subprocess.run([sys.executable, str(GEN), "--offline", "--out", str(out)],
                   check=True, cwd=str(cwd), capture_output=True)
    return json.loads(out.read_text(encoding="utf-8"))


def main() -> int:
    committed = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cwds = [Path("/tmp"), Path("/root"), ROOT]
    repro = [regen(c) for c in cwds]
    same_after = [(_strip(r) == _strip(committed)) for r in repro]
    diff_count_after = [len(_leaf_diffs(_strip(r), _strip(committed))) for r in repro]

    head = subprocess.run(["git", "show", f"HEAD:{MANIFEST_REL}"],
                          cwd=str(ROOT), capture_output=True, text=True, check=True)
    before = json.loads(head.stdout)
    dialect = _leaf_diffs(_strip(before), _strip(committed))

    source_text = (ROOT / "knowledge" / "kf" / "wp-4129-01" /
                   "source_report_4129.md").read_text(encoding="utf-8")

    def leak(blob: str) -> tuple[int, int]:
        """(producer-root occurrences, source-quoted-root occurrences).

        A `/srv/tensor/agent/work/mNNNN` token that also appears in the frozen source
        report is source data quoted from report 4129 and must stay; only tokens
        that come from the producing checkout are leakage.
        """
        producer = foreign = 0
        for tok in re.findall(r"/srv/tensor/agent/work/m\d+", blob):
            if tok in source_text:
                foreign += 1
            else:
                producer += 1
        return producer, foreign

    payloads = ["knowledge/kf/wp-4129-01/asset_manifest.json",
                "knowledge/kf/wp-4129-01/kf_result.json",
                "docs/kf/wp-4129-01.md"]
    before_leak, after_leak = [], []
    for rel in payloads:
        old = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=str(ROOT),
                             capture_output=True, text=True, check=True).stdout
        before_leak.append(leak(old)[0])
        after_leak.append(leak((ROOT / rel).read_text(encoding="utf-8"))[0])

    gates = []
    for rel in GATES:
        proc = subprocess.run([sys.executable, "-m", "pytest", rel, "-q"],
                              cwd=str(ROOT), capture_output=True, text=True)
        tail = proc.stdout.strip().split("\n")[-1]
        passed = int(re.search(r"(\d+) passed", tail).group(1)) if "passed" in tail else 0
        failed = int(re.search(r"(\d+) failed", tail).group(1)) if "failed" in tail else 0
        gates.append((rel.split("/")[-1], passed, failed))

    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.0))
    fig.suptitle("wp-4129-01 round 2 · manifest reproducibility: defect, fix, gate",
                 fontsize=13, y=0.98)

    # ---------------------------------------------------------------- panel A
    ax = axes[0]
    labels = [f"regen  cwd={c}" for c in cwds] + ["regen vs pre-fix manifest\n(HEAD)"]
    values = diff_count_after + [len(dialect)]
    colors = ["#2ca02c" if v == 0 else "#d62728" for v in values]
    bars = ax.barh(range(len(labels)), [max(v, 0) for v in values], color=colors,
                   height=0.55)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("differing leaves vs committed manifest (`generated_at` excluded)")
    ax.set_xlim(0, max(values + [1]) * 1.35 + 0.2)
    for b, v in zip(bars, values):
        ax.text(b.get_width() + 0.15, b.get_y() + b.get_height() / 2,
                "identical" if v == 0 else f"{v}", va="center", fontsize=8)
    ax.set_title("A · `--offline` regeneration determinism\n"
                 f"{sum(same_after)}/{len(cwds)} cwds reproduce; pre-fix drift = {len(dialect)} leaves",
                 fontsize=10)
    ax.grid(axis="x", ls=":", lw=0.6, alpha=0.6)

    # ---------------------------------------------------------------- panel B
    ax = axes[1]
    x = range(len(payloads))
    ax.bar([i - 0.18 for i in x], before_leak, width=0.34, color="#d62728",
           label="before (HEAD)")
    ax.bar([i + 0.18 for i in x], after_leak, width=0.34, color="#2ca02c",
           label="after (this unit)")
    for i, (b0, a0) in enumerate(zip(before_leak, after_leak)):
        ax.text(i - 0.18, b0 + 0.2, str(b0), ha="center", fontsize=8)
        ax.text(i + 0.18, a0 + 0.2, str(a0), ha="center", fontsize=8)
    ax.set_xticks(list(x))
    ax.set_xticklabels([p.split("/")[-1] for p in payloads], rotation=18, fontsize=8)
    ax.set_ylabel("producing-checkout path occurrences")
    ax.set_title("B · producer-path leakage census\n"
                 "(source-quoted foreign path excluded: it is report data)", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(axis="y", ls=":", lw=0.6, alpha=0.6)

    # ---------------------------------------------------------------- panel C
    ax = axes[2]
    names = [g[0] for g in gates]
    pas = [g[1] for g in gates]
    fail = [g[2] for g in gates]
    ax.bar(names, pas, color="#2ca02c", label="passed")
    ax.bar(names, fail, bottom=pas, color="#d62728", label="failed")
    for i, (p, f) in enumerate(zip(pas, fail)):
        ax.text(i, p + f + 0.4, f"{p}P/{f}F", ha="center", fontsize=8)
    ax.set_ylabel("tests")
    ax.set_title("C · KF gate tests of the touched packages", fontsize=10)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels([n.replace("test_", "").replace(".py", "") for n in names],
                       rotation=18, fontsize=8)
    ax.legend(fontsize=8)
    ax.grid(axis="y", ls=":", lw=0.6, alpha=0.6)

    fig.tight_layout(rect=(0, 0, 1, 0.94))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=160)
    print(json.dumps({
        "figure": str(OUT),
        "regen_same_after_fix": same_after,
        "diff_leaves_after_fix": diff_count_after,
        "prefix_drift_leaves": len(dialect),
        "prefix_drift_examples": dialect[:3],
        "producer_path_occurrences": {"payloads": payloads,
                                      "before": before_leak, "after": after_leak},
        "gate_tests": gates,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())