#!/usr/bin/env python3
"""kb_ab_experiment —— KB 消费受控 A/B（m15181 / KBM-CONSUME-W1 ②）

设计（判据先于动手，prereg 见 prereg/kb_ab_v1.json，运行前算 sha256 入账）：
  决策：KB 卡该以何种形态/时机进入 agent 上下文才被真用。
  臂：A=无 KB（现状多数任务的实际情形，因检索面不可达）
      B=被动注入（模拟『开工三查』检索命中的同域卡，原文 verbatim 进 prompt）
      C=主动检索（只给目录 titles+domain，模型自己 RETRIEVE: key，二轮取卡再答）
  锚：K1 ITTC-1957 摩擦系数（数值可判，KB-ITTC1957）
      K2 平台纪律（集群递交/架构分判，KB-CLUSTER-FIRST + KB-LOONG-X86-ARCH）
      K3 capability 卡粒度（长卡 verbatim vs 短摘要，cap:TensorFEM:m14687_GAP-FEM-MORTAR）
  单位：单次 LLM 调用（temperature=0）；每臂 reps 次；判分=确定性规则，不用 LLM 裁判。
  指标：通过率、prompt/completion token、C 臂检索命中率、耗时。

用法：python3 scripts/kb_ab_experiment.py --reps 4 [--model qwen3.7-plus]
产出：runs/kb_ab_<utc>/{prereg.sha256,results.jsonl,summary.json}
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import math
import os
import pathlib
import re
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PSQL = ["psql", "-U", "postgres", "-d", "tensorplatform", "-h", "/var/run/postgresql", "-tA", "-F", "\x1f"]


def env_cfg(path="/root/tp-agent/agent.env"):
    cfg = {}
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg


CFG = env_cfg()


def kb_rows():
    import subprocess
    sql = ("SELECT kb_key,ktype,domain,title,content FROM knowledge_base ORDER BY id")
    out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True).stdout
    rows = {}
    for line in out.splitlines():
        p = line.split("\x1f")
        if len(p) == 5:
            rows[p[0]] = {"kb_key": p[0], "ktype": p[1], "domain": p[2], "title": p[3], "content": p[4]}
    return rows


def chat(messages, model, max_tokens=900):
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.0}
    req = urllib.request.Request(
        CFG["LLM_BASE_URL"].rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + CFG["LLM_API_KEY"]})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    u = d.get("usage", {}) or {}
    return {
        "text": d["choices"][0]["message"].get("content") or "",
        "prompt_tokens": u.get("prompt_tokens", 0),
        "completion_tokens": u.get("completion_tokens", 0),
        "latency_s": round(time.time() - t0, 2),
    }


# ── 判分器（确定性，无 LLM 裁判）──
def grade_k1(text):
    """ITTC-1957：Re=1e8→0.002083，Re=1e9→0.001531（0.075/(log10Re-2)^2）。
    命中判据：文本里同时出现与两个真值相对误差 ≤1% 的数（科学计数或小数）。"""
    truth = {"re1e8": 0.075 / (math.log10(1e8) - 2) ** 2, "re1e9": 0.075 / (math.log10(1e9) - 2) ** 2}
    nums = [float(x) for x in re.findall(r"\d+\.\d+(?:[eE]-?\d+)?|\d+[eE]-?\d+", text)]
    hit = {k: any(abs(n - v) / v <= 0.01 for n in nums) for k, v in truth.items()}
    return {"pass": all(hit.values()), "detail": hit, "truth": {k: round(v, 6) for k, v in truth.items()}}


def grade_k2(text):
    """平台纪律三要素：①集群递交 ②不在 99 控制面压重算 ③架构分判 loong64/x86。"""
    t = text.lower()
    c1 = ("cluster" in t or "集群" in text) and ("submit" in t or "递交" in text or "cj" in t)
    c2 = "99" in text and ("控制面" in text or "control" in t or "本地" in text)
    c3 = ("loong" in t or "loongarch" in t) and ("x86" in t)
    return {"pass": bool(c1 and c2 and c3), "detail": {"cluster_submit": c1, "not_on_99": c2, "arch_split": c3}}


def grade_k3(text):
    """capability 卡事实：收敛率 0.07、force err≈32.3%、level 2 / 未达 L3。"""
    nums = [float(x) for x in re.findall(r"\d+\.\d+|\d+", text)]
    c1 = any(abs(n - 0.07) < 0.005 for n in nums)
    c2 = any(abs(n - 32.3) < 1.5 for n in nums)
    return {"pass": bool(c1 and c2), "detail": {"convergence_0p07": c1, "force_err_32p3": c2}}


ANCHORS = {
    "K1": {
        "prompt": ("请用 ITTC-1957 公式计算平板摩擦阻力系数 C_F，分别给出 Re=1e8 和 Re=1e9 的数值。"
                   "只给公式与两个数值（保留 6 位有效数字），不要解释背景。"),
        "kb_keys": ["KB-ITTC1957"],
        "grade": grade_k1,
    },
    "K2": {
        "prompt": ("背景：你在本平台（99 容器 + 双节点 loong64 集群 + GitHub CI）要跑一次全量 pytest，"
                   "预估 25 分钟、8 核。请给出三条具体执行动作（按本平台纪律），每条一句话。"),
        "kb_keys": ["KB-CLUSTER-FIRST", "KB-LOONG-X86-ARCH"],
        "grade": grade_k2,
    },
    "K3": {
        "prompt": ("查 TensorFEM 的 m14687 GAP-FEM-MORTAR 能力现状：收敛率是多少、力误差是多少、"
                   "当前能力等级是多少？用一行 JSON 回答 {convergence_rate, force_err_pct, level}。"),
        "kb_keys": ["cap:TensorFEM:m14687_GAP-FEM-MORTAR"],
        "grade": grade_k3,
    },
}


def render_cards(rows, keys):
    parts = []
    for k in keys:
        r = rows.get(k)
        if not r:
            continue
        parts.append(f"[{r['kb_key']}] ({r['ktype']}/{r['domain']}) {r['title']}\n{r['content']}")
    return "\n\n".join(parts)


def digest(rows, keys, n=280):
    out = []
    for k in keys:
        r = rows.get(k)
        if not r:
            continue
        out.append(f"[{r['kb_key']}] ({r['ktype']}/{r['domain']}) {r['title']}\n{r['content'][:n]}…")
    return "\n\n".join(out)


CATALOG = ""


def run_one(rows, anchor_id, arm, rep, model):
    a = ANCHORS[anchor_id]
    system = "你是本平台的建设 agent。只输出最终答案，不写过程。"
    if arm == "A":
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": a["prompt"]}]
        r1 = chat(msgs, model)
        res = {"arm": arm, "rounds": 1, "retrieved": [], "prompt_tokens": r1["prompt_tokens"],
               "completion_tokens": r1["completion_tokens"], "latency_s": r1["latency_s"],
               "text": r1["text"]}
    elif arm == "B":
        cards = render_cards(rows, a["kb_keys"])
        user = f"【平台经验库·同域条目（开工三查命中）】\n{cards}\n\n【任务】\n{a['prompt']}"
        r1 = chat([{"role": "system", "content": system}, {"role": "user", "content": user}], model)
        res = {"arm": arm, "rounds": 1, "retrieved": list(a["kb_keys"]),
               "prompt_tokens": r1["prompt_tokens"], "completion_tokens": r1["completion_tokens"],
               "latency_s": r1["latency_s"], "text": r1["text"]}
    else:  # C：主动检索
        user = (f"【平台知识库目录（仅标题/域，可按需取卡）】\n{CATALOG}\n\n【任务】\n{a['prompt']}\n\n"
                "需要卡内容时，先只输出至多 2 行 `RETRIEVE: <kb_key>`（不要答题）；"
                "若不需要，直接答题。")
        r1 = chat([{"role": "system", "content": system}, {"role": "user", "content": user}], model)
        keys = re.findall(r"RETRIEVE:\s*([A-Za-z0-9:_\-\.]+)", r1["text"])
        hit = [k for k in keys if k in a["kb_keys"]]
        if keys:
            cards = render_cards(rows, keys[:2])
            user2 = (f"【取回的卡】\n{cards}\n\n【任务】\n{a['prompt']}\n\n只输出最终答案。")
            r2 = chat([{"role": "system", "content": system}, {"role": "user", "content": user2}], model)
            res = {"arm": arm, "rounds": 2, "retrieved": keys[:2], "retrieval_hit": bool(hit),
                   "prompt_tokens": r1["prompt_tokens"] + r2["prompt_tokens"],
                   "completion_tokens": r1["completion_tokens"] + r2["completion_tokens"],
                   "latency_s": round(r1["latency_s"] + r2["latency_s"], 2), "text": r2["text"]}
        else:
            res = {"arm": arm, "rounds": 1, "retrieved": [], "retrieval_hit": False,
                   "prompt_tokens": r1["prompt_tokens"], "completion_tokens": r1["completion_tokens"],
                   "latency_s": r1["latency_s"], "text": r1["text"]}
    g = a["grade"](res["text"])
    res.update({"anchor": anchor_id, "rep": rep, "model": model, **g})
    return res


def run_granularity(rows, rep, model):
    """K3 粒度子实验：长卡 verbatim vs 摘要（同锚同题）。"""
    a = ANCHORS["K3"]
    outs = []
    for arm, render in (("B_long", render_cards), ("B_short", lambda r, k: digest(r, k))):
        cards = render(rows, a["kb_keys"])
        user = f"【平台经验库条目】\n{cards}\n\n【任务】\n{a['prompt']}"
        r1 = chat([{"role": "system", "content": "你是本平台的建设 agent。只输出最终答案。"},
                   {"role": "user", "content": user}], model)
        g = a["grade"](r1["text"])
        outs.append({"anchor": "K3", "arm": arm, "rep": rep, "model": model,
                     "prompt_tokens": r1["prompt_tokens"], "completion_tokens": r1["completion_tokens"],
                     "latency_s": r1["latency_s"], "injected_chars": len(cards), "text": r1["text"], **g})
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--model", default=CFG.get("LLM_MODEL", "qwen3.7-plus"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    global CATALOG
    rows = kb_rows()
    CATALOG = "\n".join(f"{r['kb_key']} | {r['ktype']} | {r['domain']} | {r['title']}" for r in rows.values())

    utc = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = pathlib.Path(args.out or ROOT / "runs" / f"kb_ab_{utc}")
    out.mkdir(parents=True, exist_ok=True)
    prereg = {"schema": "kb-ab-prereg/1", "anchors": {k: {"prompt": v["prompt"], "kb_keys": v["kb_keys"]}
                                                      for k, v in ANCHORS.items()},
              "arms": ["A=no-kb", "B=passive-inject", "C=active-retrieve"],
              "reps": args.reps, "model": args.model, "temperature": 0.0,
              "metrics": ["pass_rate", "prompt_tokens", "completion_tokens", "latency_s", "retrieval_hit"],
              "pass_threshold": {"K1": "两数均 ≤1% 相对误差", "K2": "三要素全中", "K3": "收敛率±0.005 且力误差±1.5pp"},
              "kb_snapshot": {k: len(v["content"]) for k, v in rows.items()},
              "frozen_at": utc}
    pj = json.dumps(prereg, ensure_ascii=False, indent=1)
    (out / "prereg.json").write_text(pj)
    sha = hashlib.sha256(pj.encode()).hexdigest()
    (out / "prereg.sha256").write_text(sha + "\n")
    print("prereg sha256:", sha)

    tasks = [(anc, arm, rep) for anc in ANCHORS for arm in ("A", "B", "C") for rep in range(args.reps)]
    results = []
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(run_one, rows, a, arm, rep, args.model): (a, arm, rep) for a, arm, rep in tasks}
        for f in cf.as_completed(futs):
            try:
                results.append(f.result())
            except Exception as e:
                a, arm, rep = futs[f]
                results.append({"anchor": a, "arm": arm, "rep": rep, "error": f"{type(e).__name__}: {e}",
                                "pass": None})
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(run_granularity, rows, rep, args.model) for rep in range(args.reps)]
        for f in cf.as_completed(futs):
            try:
                results.extend(f.result())
            except Exception as e:
                results.append({"anchor": "K3", "arm": "B_long/B_short", "error": str(e)[:200], "pass": None})

    with open(out / "results.jsonl", "w") as fh:
        for r in sorted(results, key=lambda x: (x.get("anchor", ""), x.get("arm", ""), x.get("rep", 0))):
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 汇总
    def agg(sel):
        xs = [r for r in results if sel(r)]
        ok = [r for r in xs if r.get("pass")]
        pt = [r["prompt_tokens"] for r in xs if "prompt_tokens" in r]
        ct = [r["completion_tokens"] for r in xs if "completion_tokens" in r]
        lt = [r["latency_s"] for r in xs if "latency_s" in r]
        return {"n": len(xs), "pass": len(ok), "pass_rate": round(len(ok) / len(xs), 3) if xs else None,
                "prompt_tokens_mean": round(sum(pt) / len(pt), 1) if pt else None,
                "completion_tokens_mean": round(sum(ct) / len(ct), 1) if ct else None,
                "latency_s_mean": round(sum(lt) / len(lt), 2) if lt else None,
                "errors": sum(1 for r in xs if r.get("error"))}
    summary = {"schema": "kb-ab-result/1", "prereg_sha256": sha, "model": args.model,
               "reps": args.reps, "run_dir": str(out), "cells": {}, "arms": {}}
    for anc in ANCHORS:
        for arm in ("A", "B", "C"):
            summary["cells"][f"{anc}/{arm}"] = agg(lambda r, a=anc, b=arm: r.get("anchor") == a and r.get("arm") == b)
        summary["cells"][f"{anc}/B_long"] = agg(lambda r, a=anc: r.get("anchor") == a and r.get("arm") == "B_long")
        summary["cells"][f"{anc}/B_short"] = agg(lambda r, a=anc: r.get("anchor") == a and r.get("arm") == "B_short")
    for arm in ("A", "B", "C"):
        summary["arms"][arm] = agg(lambda r, b=arm: r.get("arm") == b)
    cr = [r for r in results if r.get("arm") == "C"]
    summary["retrieval"] = {
        "n": len(cr),
        "retrieved_any": sum(1 for r in cr if r.get("retrieved")),
        "hit": sum(1 for r in cr if r.get("retrieval_hit")),
        "hit_rate": round(sum(1 for r in cr if r.get("retrieval_hit")) / len(cr), 3) if cr else None,
        "keys_requested": sorted({k for r in cr for k in (r.get("retrieved") or [])}),
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()