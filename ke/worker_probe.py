"""Agent 开工三查 → TK 四维索引的原语客户端（tp_worker 注入面的参考实现）。

现状问题：worker 开工时「三查」直接连 ``knowledge_base`` 写 SQL（或靠 prompt
里一段 SQL），查不到就没有 cited_kb，也留不下「谁用了哪条知识」的计量。
本模块把三查改成三次纯 HTTP 调用，返回一份可直接塞进上下文的知识包，并把
命中事件写进 ``ke_usage``（``event_type=inject``）；任务完成后由
``--cite`` 回报真实引用（``event_type=cite``），构成 KPI-KB-REUSE-RATE 的
分子/分母。

三查（与四维投影对应）：

    查问题  GET /by-problem?problem=<目标关键词>     —— 这条任务踩过的坑/缺口
    查概念  GET /by-concept?concept=<域/系统/关键词> —— 这个对象是什么
    查方法  GET /by-method?method=<goal 词>          —— 结论是怎么得到的
    查证据  GET /by-evidence?evidence=<命中对象 id>  —— 支撑证据链

用法::

    # 只查（注入包打到 stdout）
    python -m ke.worker_probe --base-url http://127.0.0.1:8021 \
        --goal "verify Poiseuille magic relaxation time" --mission-id 15722

    # 任务完成后回报引用（幂等，按 mission+artifact 去重）
    python -m ke.worker_probe --base-url ... --mission-id 15722 \
        --cite tkc:oss-lbm:kruger-poiseuille-validation \
        --artifact runs/m15722/case-a.json

``--base-url`` 缺省时可用 ``KE_DSN`` 在进程内起一个 ASGI 客户端（测试/离线）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

import httpx

_TOKEN = os.environ.get("KE_API_TOKEN", "")
_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were",
    "not", "you", "your", "our", "任务", "验证", "检查", "使用", "请", "的",
    "了", "和", "是", "在", "要", "把", "与", "及",
}


def keywords(goal: str, limit: int = 6) -> list[str]:
    """ASCII/CJK 词提取，保持出现顺序（确定性注入包）。"""
    toks = re.findall(r"[A-Za-z][A-Za-z0-9_\-\.]{1,}|[\u4e00-\u9fff]{2,}", goal or "")
    out: list[str] = []
    for t in toks:
        low = t.lower()
        if low in _STOP or low in out:
            continue
        out.append(low)
        if len(out) >= limit:
            break
    return out


def _client(base_url: str | None) -> httpx.Client:
    if base_url:
        return httpx.Client(base_url=base_url, timeout=20.0)
    if not os.environ.get("KE_DSN"):
        raise SystemExit("need --base-url or KE_DSN for the in-process ASGI client")
    os.environ.setdefault("KE_API_TOKEN", _TOKEN or "local-token")
    from ke import api as api_mod
    from ke import apistore as S

    S.Store(os.environ["KE_DSN"]).ensure_schema()
    return httpx.Client(transport=httpx.ASGITransport(app=api_mod.app),
                        base_url="http://ke.local", timeout=20.0)


def three_checks(client: httpx.Client, goal: str, *, mission_id: int | None,
                 consumer: str, domain: str | None = None, limit: int = 5) -> dict:
    """Run problem / concept / method checks; return a deduped knowledge package."""
    kws = keywords(goal)
    queries: list[dict] = []
    hits: dict[str, dict] = {}

    plan = []
    if kws:
        plan.append(("problem", "/by-problem", "problem", kws[0]))
        plan.append(("concept", "/by-concept", "concept", kws[0]))
        for kw in kws[1:3]:
            plan.append(("concept", "/by-concept", "concept", kw))
        plan.append(("method", "/by-method", "method", kws[0]))
    for dim, path, param, value in plan:
        params: dict[str, Any] = {param: value, "limit": limit, "log": "true",
                                  "consumer": consumer}
        if mission_id is not None:
            params["mission_id"] = mission_id
        if domain and dim in ("concept", "method"):
            params["domain"] = domain
        res = client.get(path, params=params)
        res.raise_for_status()
        body = res.json()
        queries.append({"dim": dim, "path": path, "param": value,
                        "total": body.get("total"), "status": res.status_code})
        for item in body.get("items", []):
            rid = item["id"]
            ent = hits.setdefault(rid, {
                "knowledge_id": rid,
                "kind": item["kind"],
                "domain": item.get("domain"),
                "statement": item.get("statement"),
                "evidence_status": item.get("evidence_status"),
                "dimensions": [],
                "matched": [],
            })
            if dim not in ent["dimensions"]:
                ent["dimensions"].append(dim)
            for m in item.get("matched", []):
                if len(ent["matched"]) < 6:
                    ent["matched"].append({"value": m["value"], "field": m["field"],
                                           "weight": m["weight"]})
    # evidence check: follow the evidence ids cited by the top claim hit
    evidence_refs: list[str] = []
    for ent in hits.values():
        for m in ent["matched"]:
            if str(m.get("field", "")).startswith("evidence_refs"):
                evidence_refs.append(m["value"])
    for eid in evidence_refs[:3]:
        params = {"evidence": eid, "limit": limit, "log": "true", "consumer": consumer}
        if mission_id is not None:
            params["mission_id"] = mission_id
        res = client.get("/by-evidence", params=params)
        res.raise_for_status()
        body = res.json()
        queries.append({"dim": "evidence", "path": "/by-evidence", "param": eid,
                        "total": body.get("total"), "status": res.status_code})
        for item in body.get("items", []):
            ent = hits.setdefault(item["id"], {
                "knowledge_id": item["id"], "kind": item["kind"],
                "domain": item.get("domain"), "statement": item.get("statement"),
                "evidence_status": item.get("evidence_status"),
                "dimensions": [], "matched": []})
            if "evidence" not in ent["dimensions"]:
                ent["dimensions"].append("evidence")

    ranked = sorted(hits.values(), key=lambda h: (-len(h["dimensions"]), h["knowledge_id"]))
    return {
        "schema": "tk-worker-injection/1",
        "mission_id": mission_id,
        "consumer": consumer,
        "goal": goal,
        "keywords": kws,
        "queries": queries,
        "empty": not ranked,
        "knowledge": ranked[: max(limit, 5)],
    }


def cite(client: httpx.Client, knowledge_ids: list[str], *, mission_id: int | None,
         consumer: str, artifact: str, context: dict | None = None) -> list[dict]:
    headers = {"X-KE-Agent": consumer}
    if _TOKEN:
        headers["Authorization"] = f"Bearer {_TOKEN}"
    out = []
    for kid in knowledge_ids:
        res = client.post(f"/ko/{kid}/cite",
                          json={"mission_id": mission_id, "artifact": artifact,
                                "consumer": consumer, "context": context or {}},
                          headers=headers)
        out.append({"knowledge_id": kid, "status": res.status_code,
                    "body": res.json() if res.status_code < 300 else res.text[:200]})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="TK 开工三查 / 引用回报")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--goal", default=None)
    ap.add_argument("--domain", default=None)
    ap.add_argument("--mission-id", type=int, default=None)
    ap.add_argument("--consumer", default="tp-worker")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--cite", nargs="+", default=None, metavar="KNOWLEDGE_ID")
    ap.add_argument("--artifact", default=None)
    args = ap.parse_args(argv)

    client = _client(args.base_url)
    try:
        if args.cite:
            if not args.artifact:
                raise SystemExit("--cite requires --artifact (the produced artifact path)")
            res = cite(client, args.cite, mission_id=args.mission_id,
                       consumer=args.consumer, artifact=args.artifact)
            print(json.dumps({"cited": res}, ensure_ascii=False, indent=2))
            return 0 if all(r["status"] < 300 for r in res) else 1
        if not args.goal:
            raise SystemExit("need --goal (or --cite/--artifact)")
        pack = three_checks(client, args.goal, mission_id=args.mission_id,
                            consumer=args.consumer, domain=args.domain, limit=args.limit)
        print(json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if not pack["empty"] else 3
    finally:
        client.close()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())