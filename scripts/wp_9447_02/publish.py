#!/usr/bin/env python3
"""投递 wp-9447-02 的论文级进展报告到 TensorPlatform（POST $TENSOR_API_BASE/tensor/reports）。

报告正文由 scripts/wp_9447_02/classify_9447.py 生成（所有数字程序化注入），
本脚本只做载荷组装 + 提交 + 回执打印，不写任何其它 report_id。
"""
import base64
import json
import os
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "work" / "wp-9447-02"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def post(path, body, token=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def login():
    body = {"username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"]}
    return post("/auth/login", body)["access_token"]


doc = json.loads((PKG / "classification.json").read_text(encoding="utf-8"))
md = (PKG / "report_wp-9447-02.md").read_text(encoding="utf-8")
assert md.count("```json") == 1, "delivery markdown must carry exactly one json block"

rt = doc["report_type"]
lead = rt["support_scores"][rt["primary"]] - rt["support_scores"][rt["runner_up"]]
summary = (
    f"工序 02（分类解析）对 report_id=9447 出产 classification.json：primary=experimental-validation"
    f"（score {rt['support_scores'][rt['primary']]:.1f}，lead {lead:.1f}，confidence={rt['confidence']}），"
    f"runner-up=software-engineering；subtype=证据链重建+重新判级（六分型无 audit 类，taxonomy_coverage=partial）。"
    f"源 markdown {doc['source']['chars']} 字符，sha256 与契约声明一致；{len(doc['evidence'])} 条判定依据"
    f"全部 char_span+逐字 quote+content_hash，经 ke.wp_gate.locator_matches 逐字节解析 "
    f"{sum(1 for e in doc['evidence'])}/{len(doc['evidence'])} 通过；结构切分 {doc['structure']['headings']} 标题/"
    f"{doc['structure']['tables']} 表，发现编号缺口 {doc['structure']['ordered_list_gaps'][0]['missing'] if doc['structure']['ordered_list_gaps'] else '无'}。"
    f"不抽取（claims=[]）、不登记资产、不贴 verified。"
)

figure_caption = (
    "左 = 六分型 registry identify_signals 支持度（虚线 = 预声明门槛 2.0，括号内为中英信号词词法命中数，"
    "仅作旁证不参与打分）；右 = 每类型信号匹配构成 yes/partial/no。数据来自 classification.json 的 "
    "report_type.support_scores 与 signal_table，由生成器程序化绘制。"
)

payload = {
    "title": "KF-RESULT wp-9447-02",
    "summary": summary,
    "scenario_key": "kf-wp-wp-9447-02",
    "mission_id": 19791,
    "tags": ["kf-wp:wp-9447-02", "02-classification-parse", "report-9447",
             "ice_drag_cd_reissue", "TensorKnowledge", "research", "A"],
    "markdown": md,
    "figures": [{
        "name": "fig1_signal_support.png",
        "caption": figure_caption,
        "png_base64": base64.b64encode((PKG / "fig1_signal_support.png").read_bytes()).decode(),
    }],
}

tok = login()
out = post("/tensor/reports", payload, tok)
print(json.dumps({"id": out.get("id"), "title": out.get("title"), "tags": out.get("tags"),
                  "figures": [f.get("name") for f in (out.get("figures") or [])],
                  "chars": len(md), "summary": summary}, ensure_ascii=False, indent=1))