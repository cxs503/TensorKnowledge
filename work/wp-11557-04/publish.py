#!/usr/bin/env python3
"""Publish the wp-11557-04 progress report (six elements + embedded figures)."""
import base64
import json
import os
import pathlib
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "docs/kf/wp-11557-04"
BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
PKG = "wp-11557-04"


def req(path, data=None, token=None):
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(BASE + path, data=body, method="POST" if body else "GET")
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(r, timeout=120) as resp:
        return json.loads(resp.read().decode())


tok = req("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                          "password": os.environ["TENSOR_AGENT_PASS"]})
tok = tok.get("access_token") or tok.get("token")

md = (OUT / "KF-RESULT-wp-11557-04.md").read_text(encoding="utf-8")
figs = []
for name, cap in (
    ("fig1_resistance_modes.png",
     "报告自报的三条阻力公式随冰速变化：R_bend(V=0)=7.20 MN 恒小于 R_crush(75–112.5 MN)，"
     "所谓压溃→弯曲转变是分类器 0.5·Vc/2·V_c 硬阈值的重述；真正的阻力交叉需 V≈94 m/s。"),
    ("fig2_pass_vs_threshold.png",
     "四条被判 PASS 的判据：实测偏差与其自报阈值的对比（对数轴）。C1 报范围宽于 10% 容差带 "
     "15.6–23 倍、C4 52.9%>30%、C5 6310%>20%、C8 绝对量不可与 5% 相对判据比较。"),
    ("fig3_vc_circularity.png",
     "同一解析式 0.1·√(σf/(ρh)) 换密度即得两个「不同」数字：ρ=917 → 2.763 m/s 被称作 Timco 基准，"
     "ρ≈4142 kg/m³ → 1.3 m/s 被称作模型值。C4 的 53% 是同式自比的产物。"),
):
    p = OUT / "figures" / name
    figs.append({"name": name, "caption": cap,
                 "png_base64": base64.b64encode(p.read_bytes()).decode()})

summary = (
    "独立审核报告 11557（DEM 多面体颗粒 + 冰-结构混合模式失效验证面）。数字无造假且逐位复现，"
    "但 3 条判据（C1/C4/C5）被判 PASS 而报告自身数字已越阈、§6 又写「否」；C4 的 Timco 基准即模型"
    "自身解析式（同式换密度），C5 把无量纲比值当百分数印（6310% → 「63%」，低报 100×）；"
    "C8 的相对判据被绝对量替代且测试断言恒真；C3 相图实为压溃/弯曲/劈裂（mixed=0 格）。"
    "判决 needs-fix，8 条发现（3 high / 3 medium / 2 low）。")

payload = {
    "title": f"KF-RESULT {PKG}",
    "summary": summary,
    "scenario_key": "P180W2-N05",
    "mission_id": 19820,
    "tags": ["KF-RESULT", f"kf-wp:{PKG}", "independent-review", "red-team",
             "DEM", "ice-structure", "needs-fix", "report:11557"],
    "markdown": md,
    "figures": figs,
}
resp = req("/tensor/reports", payload, token=tok)
print(json.dumps(resp, ensure_ascii=False)[:900])