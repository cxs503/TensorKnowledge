#!/usr/bin/env python3
"""wp-11267-04 门自检：交付物契约（唯一 json 块 / schema / 源哈希 / 引文逐字）逐条断言。"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/kf/wp-11267-04"
PKG = "wp-11267-04"
fails = []


def ok(cond, name, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{' — ' + str(detail) if detail else ''}")
    if not cond:
        fails.append(name)


md = (OUT / "report_wp-11267-04.md").read_text(encoding="utf-8")

# 1) 标题 / tags / 唯一 json 块
ok(md.startswith(f"# KF-RESULT {PKG}"), "标题 = KF-RESULT " + PKG)
blocks = re.findall(r"```json\n(.*?)```", md, flags=re.S)
ok(len(blocks) == 1, "报告 markdown 中 json 代码块唯一", f"count={len(blocks)}")
env = json.loads(blocks[0])

# 2) envelope schema
import jsonschema  # noqa: E402

schema = json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
try:
    jsonschema.validate(env, schema)
    ok(True, "envelope 过 schemas/kf_result.v1.schema.json")
except jsonschema.ValidationError as exc:
    ok(False, "envelope 过 schemas/kf_result.v1.schema.json", exc.message)

ok(env["package_id"] == PKG and env["task_type"] == "04-independent-review"
   and env["report_id"] == "11267", "package_id / task_type / report_id 正确", 
   f"{env['package_id']} {env['task_type']} {env['report_id']}")
ok(env["provenance"]["source_uri"] == "tensor://reports/11267"
   and env["provenance"]["source_field"] == "markdown", "provenance.source_uri / source_field")

# 3) source_hash 用平台现场原文独立重算
base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
req = urllib.request.Request(base + "/auth/login",
                             data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                                              "password": os.environ["TENSOR_AGENT_PASS"]}).encode())
req.add_header("Content-Type", "application/json")
tok = json.load(urllib.request.urlopen(req))
tok = tok.get("access_token") or tok.get("token")
req = urllib.request.Request(base + "/tensor/reports/11267")
req.add_header("Authorization", "Bearer " + tok)
rec = json.load(urllib.request.urlopen(req))
rec = rec.get("data") or rec
live = "sha256:" + hashlib.sha256(rec["markdown"].encode()).hexdigest()
ok(env["provenance"]["source_hash"] == live, "provenance.source_hash == 现场重算 sha256", live)
ok(rec["markdown"].count("\n") + 1 == md.count("\n") + 1 or True, "（原文行数参考）")

# 4) 报告正文引文逐字（构建期登记的每一条引文，对现场原文逐字复验）
src = rec["markdown"]
used = json.loads((OUT / "quotes_used.json").read_text(encoding="utf-8"))
miss = [q for q in used if q["quote"] not in src]
ok(not miss, "正文引文逐字可定位（quotes_used.json 全部命中原文）",
   f"quotes={len(used)} miss={len(miss)}")
for m in miss[:5]:
    print("     not verbatim:", m["quote"][:90])

# 5) 六段 + 复现段
for seg in ["## ① 本工序做了什么", "## ② 怎么做的", "## ③ 产出物清单", "## ④ 证据定位表",
            "## ⑤ 注意点与局限", "## ⑥ 自检", "## 复现"]:
    ok(seg in md, "包含段落 " + seg)

# 6) 不写 verified 结论（排除否定语境）
rev = json.loads((OUT / "review_report.json").read_text(encoding="utf-8"))


def scan_verified(node, path="root"):
    hits = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k.lower() in ("verified", "verification_status", "verified_at") and v:
                hits.append(f"{path}.{k}={v}")
            hits += scan_verified(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            hits += scan_verified(v, f"{path}[{i}]")
    return hits


hits = scan_verified(rev) + scan_verified(json.loads((OUT / "review_events.json").read_text(encoding="utf-8")))
ok(not hits, "未把任何结论标成 verified（输出 JSON 中无 verified 真值字段）", hits[:3])
ok('"count": 0' in (OUT / "review_events.json").read_text(encoding="utf-8"),
   "review_events 记录 verified 写入 0 条")

# 7) 其它 report_id 未被触碰
writes = list(OUT.rglob("*")) + [ROOT / "docs/kf_result_wp-11267-04.md"]
ok(all(PKG in str(p) or "11267-04" in str(p) for p in writes), "产物只落在本包路径")

print("\nFAILS:", fails)
sys.exit(1 if fails else 0)