#!/usr/bin/env python3
"""Publish the wp-11930-04 result report to the platform (/tensor/reports).

The markdown body is docs/kf/wp-11930-04/KF-RESULT-wp-11930-04.md (single ```json block =
the kf_result payload). The figure is the reviewer-side recomputation panel.
"""
import base64
import json
import os
import urllib.error
import urllib.request

REPO = "/root/tp-agent/work/m19840"
BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
MD = os.path.join(REPO, "docs/kf/wp-11930-04/KF-RESULT-wp-11930-04.md")
FIG = os.path.join(REPO, "work/wp-11930-04/fig_review_reproducibility.png")


def token():
    req = urllib.request.Request(BASE + "/auth/login",
                                 data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                                                  "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
                                 method="POST")
    req.add_header("Content-Type", "application/json")
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    return d.get("access_token") or d.get("token") or d["data"]["access_token"]


def main():
    md = open(MD, encoding="utf-8").read()
    png = base64.b64encode(open(FIG, "rb").read()).decode()
    payload = {
        "title": "KF-RESULT wp-11930-04",
        "summary": ("独立对抗式审核 report 11930（BPM 三目标联合标定可行性）：35 条机器检查（PASS 28/WARN 7/FAIL 0），"
                    "上游 wp-11930-01 资产登记 pass（14/14 定位器、6/6 图字节）；报告语义保真 needs-fix —— "
                    "可复算主数字 14/14 <3%，但 Brun γ=6.71 与 ρ=0.978 不自洽（标准定义给 4.80/9.49）、"
                    "“局部 m”列 0.080/0.045 与全局 m=262.976 差 3 个量级；核心结论（rank 3/6 结构不可辨识、分支 (c) 不可行）成立。"),
        "scenario_key": "p270w2c-n08-bpm-calibration-feasibility",
        "mission_id": 19840,
        "tags": ["kf-wp:wp-11930-04", "kf-task:04-independent-review", "report:11930",
                 "reviewed-package:wp-11930-01", "verdict:needs-fix", "Brun-collinearity", "identifiability"],
        "markdown": md,
        "figures": [{
            "name": "fig_review_reproducibility.png",
            "caption": ("wp-11930-04 独立复算对照：(A) 报告公开数字 vs 评审侧复算值的相对偏差（2% 带内 14/14，最大 1.30%）；"
                        "(B) 最坏参数对 ['k_c','k_p'] 的 Brun 共线性指数——发布 6.71 vs 标准 Brun 4.80 / Belsley 9.49，"
                        "仅非标准 1/√(1−ρ) 给出 6.75；(C) “局部 m”列 0.080/0.045 与全局 m=262.976 相差 3 个量级，"
                        "数值只与局部指数 1/m（m≈12.5/22.2）相容。"),
            "png_base64": png,
        }],
    }
    req = urllib.request.Request(BASE + "/tensor/reports",
                                 data=json.dumps(payload).encode(),
                                 method="POST")
    req.add_header("Authorization", "Bearer " + token())
    req.add_header("Content-Type", "application/json")
    try:
        resp = json.loads(urllib.request.urlopen(req, timeout=180).read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print("HTTP", exc.code, body[:800])
        raise
    with open(os.path.join(REPO, "work/wp-11930-04/publish_response.json"), "w", encoding="utf-8") as f:
        json.dump(resp, f, ensure_ascii=False, indent=1)
    d = resp.get("data", resp)
    print(json.dumps({"id": d.get("id"), "title": d.get("title"), "status": d.get("status"),
                      "chars": len(md)}, ensure_ascii=False))


if __name__ == "__main__":
    main()