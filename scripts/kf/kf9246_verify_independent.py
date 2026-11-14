"""wp-9246-02 独立复核（不复用 build 模块，独立代码路径重算一切）。

刻意与生产者实现解耦：自己取源、自己算哈希、自己回切每个 quote、自己校验 schema 与
报告围栏数；生产者脚本被改坏也不会让复核跟着错。任何一项不过即退出码 1。

用法：python3 scripts/kf/kf9246_verify_independent.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "production" / "wp-9246-02"
DECLARED_HASH = "sha256:80bcb3216845e02d844926b8d2e733882e8de69ebd756ff706296a8ab3e165b5"
DECLARED_CHARS = 11250


def h(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_again() -> str:
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": os.environ.get("TENSOR_AGENT_USER", ""),
                         "password": os.environ.get("TENSOR_AGENT_PASS", "")}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.load(r)["access_token"]
    req = urllib.request.Request(base + "/tensor/reports/9246",
                                 headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["markdown"]


def main() -> int:
    fails: list[str] = []
    md = fetch_again()
    if h(md) != DECLARED_HASH or len(md) != DECLARED_CHARS:
        fails.append(f"source hash/chars: {h(md)} {len(md)}")

    result = json.loads((OUT / "kf_result.json").read_text())
    cls = result["outputs"]["classification.json"]

    from jsonschema import Draft202012Validator
    schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text())
    errs = [e.message for e in Draft202012Validator(schema).iter_errors(result)]
    if errs:
        fails.append(f"schema: {errs}")

    # 每个 quote：逐字存在、偏移自洽、哈希自洽、唯一
    for ev in cls["evidence"]:
        loc = ev["locator"]
        q = loc["quote"]
        if q not in md:
            fails.append(f"{ev['id']}: quote not in source")
            continue
        if md.find(q) != loc["start_offset"]:
            fails.append(f"{ev['id']}: offset mismatch")
        if md[loc["start_offset"]:loc["end_offset"]] != q:
            fails.append(f"{ev['id']}: span mismatch")
        if h(q) != loc["content_hash"]:
            fails.append(f"{ev['id']}: content_hash mismatch")

    # 结论自洽：primary 必须在不被 R1 淘汰的类型里，且其 step-fit 全满足
    primary = cls["report_type"]["primary"]
    tr = cls["report_type"]["decision_trace"]
    sig = cls["signals"]["per_type"]
    if primary not in tr["eligible_after_R1"]:
        fails.append("primary not in eligible_after_R1")
    if sig[primary]["hits"] < 2:
        fails.append("primary below R1 floor")
    if not cls["signals"]["step_fit"][primary]["all_satisfiable"]:
        fails.append("primary step-fit not satisfied")
    if any(v["hits"] > sig[primary]["hits"] for v in sig.values()):
        fails.append("another type scores higher than primary without being argued")

    # 未标 verified；claims 未产出
    blob = json.dumps(cls, ensure_ascii=False)
    for bad in ('"verified"', '"verification_status"', '"assessment_status": "verified"'):
        if bad in blob:
            fails.append(f"forbidden marker {bad}")

    # 报告：唯一 json 块 == 信封
    rpt = (OUT / "KF-RESULT-wp-9246-02.md").read_text()
    blocks = re.findall(r"```json\n(.*?)\n```", rpt, flags=re.S)
    if len(blocks) != 1:
        fails.append(f"json blocks = {len(blocks)}")
    elif json.loads(blocks[0]) != result:
        fails.append("report json block != kf_result.json")
    if rpt.count("```") != 2:
        fails.append("stray code fences in report")
    for need in ("## ①", "## ②", "## ③", "## ④", "## ⑤", "## ⑥", "repro_cmd"):
        if need not in rpt:
            fails.append(f"report missing section {need}")

    # 单 report_id 边界：产物里除 9246 外不应出现别的 report_id 读取
    for name in ("kf_result.json", "classification.json"):
        if cls["scope_guard"]["report_ids_read"] != ["9246"]:
            fails.append(f"{name}: scope guard broken")

    print(json.dumps({"ok": not fails, "failures": fails,
                      "evidence_checked": len(cls["evidence"]),
                      "primary": primary}, ensure_ascii=False, indent=2))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())