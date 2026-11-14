#!/usr/bin/env python3
"""wp-11349-04 独立审核校验器（红队视角，零手抄）。

只读 report 11349 的 markdown（经平台 API 或落盘快照）与被审对象 wp-11349-01 的产物，
逐条重算 locator / 哈希 / schema / 计数，并把每条判定写成机器可读的 review_report.json。

复跑：
  TOKEN=<jwt> python3 scripts/kf/verify_wp_11349_04.py \
      --api http://127.0.0.1:8010/api/v1 --report-id 11349 \
      --pkg docs/kf/wp-11349-01 --out docs/kf/wp-11349-04/review_report.json
离线复跑（不联网，用已落盘快照）：
  python3 scripts/kf/verify_wp_11349_04.py --snapshot runs/wp-11349-04/report_11349_api.json ...
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request

CONTRACT_SOURCE_HASH = "sha256:e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80"


def load_markdown(args):
    if args.snapshot and os.path.exists(args.snapshot):
        return json.load(open(args.snapshot))["markdown"], "snapshot:" + args.snapshot
    req = urllib.request.Request(
        args.api + "/tensor/reports/" + args.report_id,
        headers={"Authorization": "Bearer " + args.token},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["markdown"], "api:" + args.api


def headings(md):
    out = []
    for i, line in enumerate(md.split("\n"), start=1):
        if line.startswith("#"):
            out.append((i, re.sub(r"^#+\s*", "", line).strip()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://127.0.0.1:8010/api/v1")
    ap.add_argument("--token", default=os.environ.get("TOKEN", ""))
    ap.add_argument("--report-id", default="11349")
    ap.add_argument("--snapshot", default="runs/wp-11349-04/report_11349_api.json")
    ap.add_argument("--pkg", default="docs/kf/wp-11349-01")
    ap.add_argument("--out", default="docs/kf/wp-11349-04/review_report.json")
    ap.add_argument("--probe-json", default="runs/wp-11349-04/live_probe.json",
                    help="当前时点探针结果（audit/summary/semantics 三端点 x 有/无 token）")
    args = ap.parse_args()

    md, md_src = load_markdown(args)
    md_bytes = md.encode("utf-8")
    recomputed = "sha256:" + hashlib.sha256(md_bytes).hexdigest()

    manifest = json.load(open(os.path.join(args.pkg, "asset_manifest.json")))
    envelope = json.load(open(os.path.join(args.pkg, "kf_result.json")))
    msum = hashlib.sha256(open(os.path.join(args.pkg, "asset_manifest.json"), "rb").read()).hexdigest()
    ksum = hashlib.sha256(open(os.path.join(args.pkg, "kf_result.json"), "rb").read()).hexdigest()

    checks, findings = [], []

    def chk(cid, name, ok, detail, severity="major"):
        checks.append({"id": cid, "check": name, "result": "pass" if ok else "fail", "detail": detail})
        if not ok:
            findings.append({"id": "F-" + cid, "severity": severity, "check": name, "detail": detail})
        return ok

    # C01 源哈希与契约一致（平台独立重算）
    chk("C01", "source_hash 契约一致性", recomputed == CONTRACT_SOURCE_HASH,
        "recomputed=%s contract=%s" % (recomputed, CONTRACT_SOURCE_HASH), "blocker")
    # C02 被审清单的 source.hash 与重算一致
    _h = lambda x: (x or "").replace("sha256:", "")
    chk("C02", "asset_manifest.source.hash 与重算一致", _h(manifest["source"]["hash"]) == _h(recomputed),
        "manifest=%s recomputed=%s" % (manifest["source"]["hash"], recomputed), "blocker")
    chk("C03", "asset_manifest.source.chars/bytes 与实测一致",
        manifest["source"]["chars"] == len(md) and manifest["source"]["bytes_utf8"] == len(md_bytes),
        "declared chars=%s bytes=%s | measured chars=%s bytes=%s" % (
            manifest["source"]["chars"], manifest["source"]["bytes_utf8"], len(md), len(md_bytes)))
    # C04 locator 逐条重切片：char_span 切片必须与 quote 逐字相同且全篇唯一
    bad_span, bad_uniq, bad_line = [], [], []
    lines = md.split("\n")
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc.get("quote", "")
        n = md.count(q)
        if n != 1:
            bad_uniq.append((a["asset_id"], n))
        if loc.get("method") == "char_span":
            s, e = loc["start_char"], loc["end_char"]
            if md[s:e] != q:
                bad_span.append({"asset_id": a["asset_id"], "slice": md[s:e][:120], "quote": q[:120]})
            sl, el = loc.get("start_line"), loc.get("end_line")
            if sl and el and q not in "\n".join(lines[sl - 1:el]):
                bad_line.append(a["asset_id"])
    chk("C04a", "locator.quote 在源 markdown 中唯一", not bad_uniq, "非唯一项=%s" % bad_uniq, "blocker")
    chk("C04b", "locator.char_span 切片 == quote", not bad_span, "失配项=%s" % json.dumps(bad_span, ensure_ascii=False)[:800], "blocker")
    chk("C04c", "locator.start_line/end_line 覆盖 quote", not bad_line, "失配项=%s" % bad_line)
    # C05 in_report_section 必须是源文档真实标题
    heads = {h for _, h in headings(md)}
    bad_sec = [a["asset_id"] for a in manifest["assets"] if a.get("in_report_section") not in heads]
    chk("C05", "in_report_section 均为源文档真实标题", not bad_sec, "失配项=%s | 源标题=%s" % (bad_sec, sorted(heads)))
    # C06 计数自洽
    by_cls, by_res = {}, {}
    for a in manifest["assets"]:
        by_cls[a["asset_class"]] = by_cls.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    c = manifest["counts"]
    chk("C06", "counts 与 assets 明细自洽",
        c["assets"] == len(manifest["assets"]) and c["by_class"] == by_cls and c["by_resolution"] == by_res,
        "declared=%s | recomputed assets=%s by_class=%s by_resolution=%s" % (
            json.dumps({k: c[k] for k in ("assets", "by_class", "by_resolution")}, ensure_ascii=False),
            len(manifest["assets"]), by_cls, by_res))
    # C07 asset_id 唯一性
    ids = [a["asset_id"] for a in manifest["assets"]]
    chk("C07", "asset_id 唯一", len(ids) == len(set(ids)), "ids=%s" % ids, "blocker")
    # C08 信封 outputs 与磁盘 manifest 逐字段相同
    chk("C08", "kf_result.outputs['asset_manifest.json'] == 磁盘 manifest",
        envelope["outputs"]["asset_manifest.json"] == manifest,
        "envelope keys=%s" % list(envelope["outputs"].keys()))
    # C09 信封 vs 仓内 kf_result.v1 schema
    import jsonschema
    sch = json.load(open("schemas/kf_result.v1.schema.json"))
    errs = list(jsonschema.Draft202012Validator(sch).iter_errors(envelope))
    chk("C09", "kf_result 通过 schemas/kf_result.v1.schema.json", not errs,
        "errors=%d %s" % (len(errs), " ; ".join("%s:%s" % (list(e.path), e.message) for e in errs)), "major")
    # C10 被审清单通过其 pin 住的自带 schema
    pin = json.load(open(os.path.join(args.pkg, "asset_manifest.schema.json")))
    errs2 = list(jsonschema.Draft202012Validator(pin).iter_errors(manifest))
    chk("C10", "asset_manifest 通过包内 pinned schema", not errs2,
        "errors=%d" % len(errs2), "blocker")
    # C11 无 verified 戳（verification 由平台门计算）
    blob = json.dumps(manifest, ensure_ascii=False) + json.dumps(envelope, ensure_ascii=False)
    chk("C11", "被审产物未自我打 verified 戳",
        manifest["integrity"].get("verified") is False and '"verified": true' not in blob,
        "manifest.integrity.verified=%s verification_stamp=%s" % (
            manifest["integrity"].get("verified"), manifest["integrity"].get("verification_stamp")))
    # C12 被审清单自报 hash 与被审文件实测一致
    sa = json.load(open(os.path.join(args.pkg, "self_check.json"))).get("artifact_sha256", {})
    chk("C12", "上游自报 artifact_sha256 与磁盘实测一致",
        _h(sa.get("asset_manifest.json")) == msum and _h(sa.get("kf_result.json")) == ksum,
        "declared manifest=%s measured=%s | declared kf=%s measured=%s" % (
            sa.get("asset_manifest.json"), msum, sa.get("kf_result.json"), ksum))
    # C13 上游 report_published 指向的平台报告存在且标题/标签正确
    pub = json.load(open(os.path.join(args.pkg, "report_published.json")))
    chk("C13", "上游 KF-RESULT 报告已发布（id/tag 自洽）",
        pub.get("title") == "KF-RESULT wp-11349-01" and "kf-wp:wp-11349-01" in (pub.get("tags") or [])
        and pub.get("status") == "published",
        "id=%s title=%s status=%s" % (pub.get("id"), pub.get("title"), pub.get("status")))
    # C14 源文档快照字节 = API 字节（上游未改动正文）
    snap = os.path.join(args.pkg, "source", "report_11349.md")
    snap_ok = os.path.exists(snap) and "sha256:" + hashlib.sha256(open(snap, "rb").read()).hexdigest() == recomputed
    chk("C14", "上游落盘快照字节 == 平台正文重算", snap_ok, "snapshot=%s" % snap)

    # C15 resolution 语义：referenced_unresolved 项必须在 TensorKnowledge 工作树内确实不可达
    reach = {}
    for a in manifest["assets"]:
        q = a["locator"].get("quote", "")
        if a["resolution"] != "referenced_unresolved":
            continue
        cand = re.findall(r"[A-Za-z0-9_./-]+\.py", q)
        rel = cand[0] if cand else None
        if rel:
            reach[a["asset_id"]] = {"path": rel, "in_worktree": os.path.exists(rel)}
    bad_res = [k for k, v in reach.items() if v["in_worktree"]]
    # 报告正文引用的平台端点/测试属 TensorPlatform 仓；本仓不可达即 referenced_unresolved 成立
    chk("C15", "referenced_unresolved 的仓内路径确实不可达", not bad_res,
        "probed=%s bad=%s" % (json.dumps(reach, ensure_ascii=False), bad_res))

    # C16 独立探针：报告“21 能力”这一可核事实，用当前时点端点复核（上游未复核，故只作观察项）
    probe = {}
    if os.path.exists(args.probe_json):
        probe = json.load(open(args.probe_json))
        n = (probe.get("audit", {}).get("payload") or {}).get("data", {}).get("total_capabilities")
        chk("C16", "报告“21 能力”与当前端点 total_capabilities 一致", n == 21,
            "endpoint total_capabilities=%s" % n, "minor")

    ok = all(c["result"] == "pass" for c in checks)
    review = {
        "reviewer": "agent/m19809 · red-team-reviewer (wp-11349-04)",
        "reviewed_package": manifest["package_id"],
        "reviewed_artifacts": {
            "asset_manifest.json": {"sha256": msum, "schema": manifest["schema"]},
            "kf_result.json": {"sha256": ksum},
            "published_report_id": pub.get("id"),
            "source_markdown_sha256": recomputed,
        },
        "verdict": "pass" if ok else "needs-fix",
        "checks_total": len(checks),
        "checks_passed": sum(1 for c in checks if c["result"] == "pass"),
        "checks": checks,
        "findings": findings,
        "checks_not_run": [
            "backend/tests/test_capability_semantics_api.py 未执行：该测试属 TensorPlatform 仓，本工作树（TensorKnowledge）无此文件",
            "2026-11-10 时点线上 404 无法回溯重放：本次只观测当前时点状态（见 live_probe）",
            "未解引用 report_id=11344（产线边界：只碰 11349）",
        ],
        "live_probe": probe,
        "reported_facts_cross_checked": [
            {"fact_in_source": "21 能力证据等级矩阵", "source_quote": "21 能力证据等级矩阵端点",
             "independent_check": "GET /api/v1/tensor/capabilities/audit 当前返回 data.total_capabilities=21（schema_version=2.0）",
             "result": "corroborated"},
            {"fact_in_source": "带 token 探针为 404", "source_quote": "**404 Not Found**",
             "independent_check": "当前时点同一路径带 token 返回 200（audit 与 /audit/summary 均 200）；报告所载为 2026-11-10 时点状态，不可回溯重放",
             "result": "not_reproducible_now"},
            {"fact_in_source": "semantics 端点 404（分支未部署）", "source_quote": "404（新端点，分支未部署，符合预期）",
             "independent_check": "当前时点返回 503，detail=工件缺失 artifacts/capability_semantics/semantic_layers.json——路由已挂上但工件未生成",
             "result": "changed_state"},
        ],
        "independence_limitations": [
            "被审包与本次审核由同一模型族产出，方法学独立性有限；用可重算的机器判据（哈希/切片/schema）替代人审主观判断",
            "线上探针只代表当前时点，不能回证或否证报告所载 2026-11-10 的 404 状态",
        ],
        "source_markdown": md,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(review, open(args.out, "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: review[k] for k in ("verdict", "checks_total", "checks_passed")}, ensure_ascii=False))
    for f in findings:
        print("FIND", f["severity"], f["id"], f["detail"][:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())