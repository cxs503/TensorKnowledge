import json, os, urllib.request

base = os.environ["TENSOR_API_BASE"]
tok = open("/tmp/tk_token.txt").read().strip()

md = open("/root/tp-agent/work/m15246/docs/audit-m15180-kbm-schema-w1.md").read()
body = {
    "title": "交差审计 m15180 · KBM-SCHEMA-W1：三件套核验通过，判级 L2，verdict 落表",
    "summary": "board-audit 独立复跑 m15180 交付：pytest 30/30 全绿、repro_cmd 重跑 6/6 verified 且卡片集合与提交工件一致、run_artifacts 齐全、报告六段齐全；tensor_benchmark_cases 无此锚点 case（表不在本地 DB），按任务自带判据裁判。判级 L2（真代码 input→compute→output+单测+可复现 demo；无平台集成调用方，未达 L3/L4）。verdict 已 INSERT tensor_maturity_verdicts (level=2)。遗留：抽样一致率待 KBM-CLEAN-W1 补跑、报告 API 发布缺失。",
    "scenario_key": "KBM-SCHEMA-W1",
    "mission_id": 15246,
    "tags": ["board-audit", "kbm", "maturity-verdict", "m15180"],
    "markdown": md,
    "figures": [],
}
req = urllib.request.Request(
    base + "/tensor/reports",
    data=json.dumps(body, ensure_ascii=False).encode(),
    headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req) as r:
    d = json.load(r)
print("published:", json.dumps(d, ensure_ascii=False)[:400])
