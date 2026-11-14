#!/usr/bin/env python3
"""wp-11267-04 独立审核复算器 (red-team reviewer)。

独立复算：不采用生产者的自检结论(verification.json)与其叙述；只读
(a) 报告原文 markdown —— 从平台 API 现场重取（不读磁盘副本）；
(b) 上游工序 wp-11267-01 的机器产物 asset_manifest.json / kf_result.json / 其 pinned schema。

每个判定附 verbatim 定位证据（quote + char span + line），零手抄。
输出 runs/wp-11267-04/independent_recompute.json。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
UP = ROOT / "docs/kf/wp-11267-01"
OUT_RUN = ROOT / "runs/wp-11267-04"
REPORT_ID = "11267"
CONTRACT_HASH = "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f"
# 上游产物生成时刻在册的 schema 版本（git: 548f89e 2026-11-12 09:21 +0800）
EMISSION_SCHEMA_COMMIT = "548f89e"
CURRENT_SCHEMA = ROOT / "schemas/kf_result.v1.schema.json"


def api(path, tok=None, body=None):
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data)
    req.add_header("Content-Type", "application/json")
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def login():
    d = api("/auth/login", body={"username": os.environ["TENSOR_AGENT_USER"],
                                 "password": os.environ["TENSOR_AGENT_PASS"]})
    return d.get("access_token") or d.get("token")


def sha(txt: str) -> str:
    return "sha256:" + hashlib.sha256(txt.encode("utf-8")).hexdigest()


def line_of(md: str, pos: int) -> int:
    return md.count("\n", 0, pos) + 1


PATH_EXT = r"(?:py|json|md|png|csv|npz|npy|txt|yaml|yml|toml|so|cpp|h|hpp|c)"
ABSENCE_PAT = re.compile(r"not measured|未测量|未在本机实测|排队中|queued|无任何集群数据|未完成部分")


def discover(md: str):
    """审核员自己的资产发现规则（独立实现，不复用生产者代码）。"""
    found = {}

    def add(cls, name, quote, pos):
        found.setdefault((cls, name), []).append(
            {"quote": quote, "start_char": pos, "start_line": line_of(md, pos)})

    for m in re.finditer(r"!\[[^\]]*\]\((figures/[^)\s]+)\)", md):
        add("figure_artifact", m.group(1), m.group(1), m.start(1))
    for m in re.finditer(r"`([A-Za-z0-9_./*-]+\.%s)`" % PATH_EXT, md):
        p = m.group(1)
        if "/" not in p:
            continue
        cls = ("test_suite" if Path(p).name.startswith("test_")
               else "code_script" if p.startswith("scripts/")
               else "data_artifact" if p.endswith((".json", ".npz", ".csv"))
               else "code_module_path")
        add(cls, p, m.group(0), m.start(1))
    for m in re.finditer(r"`python -m ([A-Za-z0-9_.]+)`", md):
        add("run_command", m.group(1), m.group(1), m.start(1))
    for m in re.finditer(r"\b(cj\d{3})\b", md):
        add("cluster_job", m.group(1), m.group(1), m.start(1))
    for m in re.finditer(r"`(test_[A-Za-z0-9_]+)`", md):
        add("test_symbol", m.group(1), m.group(1), m.start(1))
    return found


def main() -> int:
    tok = login()
    rec = api(f"/tensor/reports/{REPORT_ID}", tok)
    rec = rec.get("data") or rec
    md = rec["markdown"]                       # ← 原文以 API 现场重取为准
    h = sha(md)
    OUT_RUN.mkdir(parents=True, exist_ok=True)

    man = json.loads((UP / "asset_manifest.json").read_text(encoding="utf-8"))
    env = json.loads((UP / "kf_result.json").read_text(encoding="utf-8"))

    res = {"reviewer": "red-team-reviewer", "package_id": "wp-11267-04",
           "package_reviewed": "wp-11267-01", "report_id": REPORT_ID,
           "source": {"recomputed_sha256": h, "contract_declared": CONTRACT_HASH,
                      "hash_match": h == CONTRACT_HASH, "chars": len(md),
                      "bytes": len(md.encode()), "lines": md.count("\n") + 1,
                      "fetched_via": "GET /tensor/reports/11267 (Bearer, fresh)"},
           "checks": [], "findings": [], "observations": []}

    def check(cid, name, verdict, detail, evidence=None):
        res["checks"].append({"id": cid, "name": name, "verdict": verdict,
                              "detail": detail, "evidence": evidence or []})
        return verdict == "pass"

    # ---- K1 源身份 ---------------------------------------------------------------
    src = man.get("source", {})
    check("K1-source-identity", "源身份：manifest/契约/独立重算三方 hash 与字符数一致",
          "pass" if (src.get("hash") == h == CONTRACT_HASH
                     and src.get("chars") == len(md)
                     and src.get("title") == rec.get("title")
                     and src.get("scenario_key") == rec.get("scenario_key")) else "FAIL",
          {"manifest_hash": src.get("hash"), "recomputed": h,
           "contract_hash": CONTRACT_HASH, "chars": {"manifest": src.get("chars"),
           "recomputed": len(md)}, "bytes_utf8": {"manifest": src.get("bytes_utf8"),
           "recomputed": len(md.encode())},
           "title_match": src.get("title") == rec.get("title"),
           "scenario_match": src.get("scenario_key") == rec.get("scenario_key")},
          [{"quote": md.splitlines()[0], "start_char": 0, "start_line": 1}])

    # ---- K2 locator 逐字符复核（document 型单独口径） ----------------------------
    n_loc = bad = 0
    n_quote = n_span = n_line = n_doc = 0
    bad_ex = []
    for a in man["assets"]:
        for loc in [a.get("locator")] + list(a.get("all_locators") or []):
            if not loc or "quote" not in loc:
                continue
            n_loc += 1
            q, s, e = loc["quote"], loc.get("start_char"), loc.get("end_char")
            probs = []
            if q not in md:
                probs.append("quote_not_in_markdown")
                n_quote += 1
            if isinstance(s, int) and isinstance(e, int):
                if md[s:e] != q:
                    if loc.get("method") == "document":
                        n_doc += 1          # 文档型 locator：span 覆盖全文，quote 仅为身份行
                    else:
                        probs.append("span_mismatch")
                        n_span += 1
                elif loc.get("start_line") is not None and line_of(md, s) != loc["start_line"]:
                    probs.append("line_mismatch")
                    n_line += 1
            if loc.get("quote_sha256") and sha(q) != loc["quote_sha256"]:
                probs.append("quote_sha256_mismatch")
            if probs:
                bad += 1
                bad_ex.append({"asset_id": a["asset_id"], "problems": probs, "quote": q[:60]})
    check("K2-locator-verbatim", "locator 逐字符可定位（quote∈原文 / md[s:e]==quote / 行号重算一致）",
          "pass" if bad == 0 else "FAIL",
          {"locators_checked": n_loc, "bad": bad, "quote_not_in_markdown": n_quote,
           "span_mismatch": n_span, "line_mismatch": n_line,
           "document_method_spans": n_doc, "examples": bad_ex[:5]},
          [{"quote": man["assets"][0]["all_locators"][0]["quote"],
            "start_char": man["assets"][0]["all_locators"][0]["start_char"],
            "start_line": man["assets"][0]["all_locators"][0]["line"]}])

    # ---- K3 counts 自洽 ----------------------------------------------------------
    cnt = man["counts"]
    a_res = Counter(a["resolution"] for a in man["assets"])
    a_cls = Counter(a["asset_class"] for a in man["assets"])
    ok = (cnt["assets"] == len(man["assets"]) == sum(a_res.values())
          and all(cnt["by_resolution"].get(k) == v for k, v in a_res.items())
          and all(cnt["by_class"].get(k) == v for k, v in a_cls.items())
          and sum(cnt["by_class"].values()) == cnt["assets"])
    check("K3-counts-selfconsistent", "counts 与实际数组逐项自洽（总数/按类/按可解性/id 唯一）",
          "pass" if ok else "FAIL",
          {"declared": cnt, "actual_total": len(man["assets"]),
           "actual_by_resolution": dict(a_res), "actual_by_class": dict(a_cls),
           "id_unique": len({a["asset_id"] for a in man["assets"]}) == len(man["assets"]),
           "name_unique": len({a["name"] for a in man["assets"]}) == len(man["assets"])})

    # ---- K4 独立发现 vs 登记：召回 / 幻觉 ---------------------------------------
    disc = discover(md)
    man_names = set()
    for a in man["assets"]:
        n = a["name"]
        man_names |= {n, n.replace("figures/", "").rstrip("/"), Path(n).name}
    missed = []
    for (cls, name), hits in disc.items():
        if not ({name, name.replace("figures/", ""), Path(name).name} & man_names):
            missed.append({"asset_class": cls, "name": name, "hits": hits[:1]})
    check("K4-discovery-recall", "审核员独立发现集无漏登记", "pass" if not missed else "FAIL",
          {"discovered_keys": len(disc), "missed": len(missed), "missed_items": missed},
          [{"quote": m["hits"][0]["quote"], "start_char": m["hits"][0]["start_char"],
            "start_line": m["hits"][0]["start_line"]} for m in missed[:6]])

    phantom = [{"asset_id": a["asset_id"], "name": a["name"], "resolution": a["resolution"]}
               for a in man["assets"]
               if a["asset_class"] != "source_document"
               and (a.get("locator") or {}).get("quote", "\x00") not in md]
    check("K4b-no-phantom-assets", "无“原文中不存在”的幻觉资产（每条 locator quote 均在原文）",
          "pass" if not phantom else "FAIL", {"phantom": phantom})

    # ---- K5 declared_absent 保真（含所在句判定） --------------------------------
    absent = [a for a in man["assets"] if a["resolution"] == "declared_absent"]
    bad_abs, widen_needed = [], []
    for a in absent:
        loc = a.get("locator") or {}
        q = loc.get("quote", "")
        ln = md.splitlines()[loc["start_line"] - 1] if loc.get("start_line") else ""
        in_md = q in md
        gap_in_quote = bool(ABSENCE_PAT.search(q))
        gap_in_line = bool(ABSENCE_PAT.search(ln))
        if not (in_md and gap_in_line):
            bad_abs.append({"asset_id": a["asset_id"], "name": a["name"],
                            "in_md": in_md, "gap_in_quote": gap_in_quote,
                            "gap_in_line": gap_in_line, "quote": q})
        elif not gap_in_quote:
            widen_needed.append({"asset_id": a["asset_id"], "name": a["name"],
                                 "quote": q, "line": loc["start_line"],
                                 "line_text": ln.strip()[:160]})
    unmeasured_rows = [ln for ln in md.splitlines()
                       if "not measured" in ln and ln.strip().startswith("|")]
    gaps_registered = {a["name"] for a in absent}
    missing_gaps = [ln for ln in unmeasured_rows
                    if not any(n in ln for n in gaps_registered)]
    check("K5-declared-absent-fidelity", "declared_absent 每条都是原文自述缺失（句级），且判据表未测量行无遗漏",
          "pass" if (not bad_abs and not missing_gaps) else "FAIL",
          {"declared_absent": len(absent), "bad": bad_abs,
           "locator_narrower_than_sentence": widen_needed,
           "unmeasured_rows_in_report": len(unmeasured_rows),
           "unregistered_unmeasured_rows": missing_gaps},
          [{"quote": a["locator"]["quote"], "start_char": a["locator"]["start_char"],
            "start_line": a["locator"]["start_line"]} for a in absent])

    # ---- K6 图 payload 独立重取 --------------------------------------------------
    probes = man["source"].get("figure_endpoint_probes", {})
    fig, fig_ok = {}, True
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
    for name, d in probes.items():
        req = urllib.request.Request(f"{base}/tensor/reports/{REPORT_ID}/figures/{name}")
        req.add_header("Authorization", "Bearer " + tok)
        try:
            with urllib.request.urlopen(req) as r:
                b = r.read()
            got = "sha256:" + hashlib.sha256(b).hexdigest()
            match = got == d.get("sha256") and len(b) == d.get("bytes")
            fig[name] = {"bytes": len(b), "sha256": got, "match": match,
                         "png_magic": b[:8] == b"\x89PNG\r\n\x1a\n"}
            fig_ok &= match and len(b) > 1000
        except Exception as exc:  # noqa: BLE001
            fig_ok = False
            fig[name] = {"error": str(exc)}
    declared_figs = [a["name"].replace("figures/", "") for a in man["assets"]
                     if a["asset_class"] == "figure_artifact"]
    check("K6-figure-payload", "7 张图现场重取，字节数与 sha256 与登记一致（非占位/非错误体）",
          "pass" if (fig_ok and set(declared_figs) <= set(probes)) else "FAIL",
          {"figures": len(fig), "all_match": fig_ok, "declared_figure_assets": declared_figs,
           "artifact_endpoint_probe": man["source"].get("artifact_endpoint_probe")})

    # ---- K7 工序边界 / 无 verified ----------------------------------------------
    reason = man.get("claims_empty_reason", "")
    scrubbed = reason.lower().replace("do_not_mark_claims_as_verified", "")
    blob = json.dumps(man, ensure_ascii=False)
    other_reports = sorted((set(re.findall(r"reports/(\d+)", blob))
                            | set(re.findall(r'"report_id"\s*:\s*"?(\d+)', blob))) - {REPORT_ID})
    check("K7-scope-boundary", "claims=[] 合规、全库无 verified 判定、只碰本报告",
          "pass" if (man.get("claims") == [] and "verified" not in scrubbed
                     and man.get("report_id") == REPORT_ID and not other_reports) else "FAIL",
          {"claims": man.get("claims"), "claims_empty_reason_len": len(reason),
           "verified_token_in_reason": "verified" in scrubbed,
           "other_report_ids_seen": other_reports})

    # ---- K8 envelope 双版本 schema 判定 -----------------------------------------
    import subprocess

    import jsonschema
    cur = json.loads(CURRENT_SCHEMA.read_text(encoding="utf-8"))
    cur_err = None
    try:
        jsonschema.validate(env, cur)
    except jsonschema.ValidationError as exc:
        cur_err = {"message": exc.message[:300], "path": list(exc.absolute_path)}
    emis_txt = subprocess.run(["git", "show", f"{EMISSION_SCHEMA_COMMIT}:schemas/kf_result.v1.schema.json"],
                              cwd=ROOT, capture_output=True, text=True).stdout
    emis = json.loads(emis_txt) if emis_txt.strip() else None
    emis_err = None
    if emis:
        try:
            jsonschema.validate(env, emis)
        except jsonschema.ValidationError as exc:
            emis_err = {"message": exc.message[:300], "path": list(exc.absolute_path)}
    check("K8-envelope-schema-dual", "信封 schema：按生成时在册版本 vs 按当前版本分别判定",
          "pass" if (emis_err is None and cur_err is None) else
          ("needs-fix" if emis_err is None else "FAIL"),
          {"emission_schema_commit": EMISSION_SCHEMA_COMMIT,
           "emission_schema_errors": emis_err, "current_schema_errors": cur_err,
           "top_level_keys": sorted(env.keys()),
           "provenance_keys": sorted(env.get("provenance", {}).keys())})

    # ---- K9 manifest pinned schema ----------------------------------------------
    pinned = UP / "asset_manifest.schema.json"
    man_err = None
    try:
        jsonschema.validate(man, json.loads(pinned.read_text(encoding="utf-8")))
    except jsonschema.ValidationError as exc:
        man_err = {"message": exc.message[:300], "path": list(exc.absolute_path)}
    check("K9-manifest-schema", "asset_manifest.json 过本包 pinned schema",
          "pass" if man_err is None else "FAIL",
          {"pinned_schema": str(pinned.relative_to(ROOT)), "errors": man_err})

    # ---- K10 派生计数复核 --------------------------------------------------------
    img_links = len(re.findall(r"!\[[^\]]*\]\(figures/[^)\s]+\)", md))
    bare = len(re.findall(r"`[a-z_]+\.png`", md)) + len(
        [ln for ln in md.splitlines() if re.match(r"^\* `[a-z_]+\.png`", ln)])
    my_paths = len({m.group(1) for m in re.finditer(r"`([A-Za-z0-9_./*-]+\.[a-z]{2,4})`", md)})
    check("K10-derived-counts", "派生计数（图链接/图引用/独立路径数）复核",
          "pass" if (cnt["body_image_links"] == img_links) else "FAIL",
          {"manifest_body_image_links": cnt["body_image_links"], "recomputed_image_links": img_links,
           "manifest_figure_references_total": cnt["figure_references_total"],
           "recomputed_bare_png_mentions": bare,
           "manifest_distinct_referenced_paths": cnt["distinct_referenced_paths"],
           "recomputed_backticked_paths": my_paths})

    # ---- K11 worktree_probe 口径 -------------------------------------------------
    contra = [(a["asset_id"], a["name"], (a["resolution_check"]["worktree_probe"]["check"]))
              for a in man["assets"]
              if (a.get("resolution_check") or {}).get("worktree_probe", {}).get("result") == "unresolved"
              and "path exists" in (a["resolution_check"]["worktree_probe"].get("check", ""))]
    abs_leak = [a["asset_id"] for a in man["assets"]
                if str((a.get("resolution_check") or {}).get("worktree_probe", {}).get("path", "")).startswith("/root/")]
    check("K11-worktree-probe-wording", "worktree_probe 的 reason 文本与 result 不自相矛盾、无绝对路径泄漏",
          "needs-fix" if (contra or abs_leak) else "pass",
          {"contradictory_entries": len(contra), "sample": contra[:3],
           "absolute_path_entries": len(abs_leak)})

    # ---- K12 判据资产覆盖（观察项） ---------------------------------------------
    crit_ids = sorted({m.group(0) for m in re.finditer(r"\bC[1-6]_[a-z_0-9]+", md)})
    crit_keys = sorted({c.split("_")[0] for c in crit_ids})
    reg_crit = sorted({a["name"].split("_")[0] for a in man["assets"]
                       if a["asset_class"] == "declared_measurement_gap"})
    unregistered = [k for k in crit_keys if k not in reg_crit]
    res["observations"].append({
        "id": "O1-criteria-coverage",
        "text": "判据 C1–C6 中只有 3 个（未测量的 C1/C2/C4）被登记为资产；C3/C5/C6 已测量出数值，未作资产登记",
        "criteria_in_report": crit_ids, "criteria_keys": crit_keys,
        "registered_as_asset": reg_crit, "criteria_not_registered": unregistered,
        "scope_declared_by_producer": man["scope"]["does_not"][:1]})


    # ---- K13 节段归属复核（in_report_section 是否等于 locator 所在最近标题） --------
    heads = [(i, ln.lstrip("# ").strip()) for i, ln in enumerate(md.splitlines(), 1)
             if ln.startswith("#")]
    def section_at(line: int):
        cur = "(document root)"
        for hl, name in heads:
            if hl == heads[0][0]:      # H1 = 文档标题行，等价于 document root
                continue
            if hl <= line:
                cur = name
            else:
                break
        return cur
    sec_bad = []
    for a in man["assets"]:
        if a["asset_class"] == "source_document":
            continue
        first = (a.get("all_locators") or [a.get("locator")])[0]
        declared = (a.get("in_report_section") or "").strip()
        actual = section_at(first.get("line") or first.get("start_line") or 1)
        # 允许“⑤ 注意点”被写成带括号全称的反向包含
        same = declared == actual or declared in actual or actual in declared
        if not same:
            sec_bad.append({"asset_id": a["asset_id"], "name": a["name"],
                            "declared": declared, "actual": actual,
                            "line": first.get("line") or first.get("start_line")})
    check("K13-section-attribution", "in_report_section 与 locator 实际所在节段一致",
          "pass" if not sec_bad else "FAIL",
          {"assets_checked": len(man["assets"]) - 1, "mismatch": sec_bad})

    # ---- K14 occurrence_count 与 all_locators 一致 -------------------------------
    occ_bad = [{"asset_id": a["asset_id"], "name": a["name"],
                "declared": a.get("occurrence_count"),
                "observed_locators": len(a.get("all_locators") or [])}
               for a in man["assets"]
               if a.get("occurrence_count") not in (None, len(a.get("all_locators") or []))]
    total_locators = sum(len(a.get("all_locators") or []) for a in man["assets"])
    check("K14-occurrence-count", "occurrence_count == len(all_locators)，且总 locator 数可复核",
          "pass" if not occ_bad else "FAIL",
          {"total_locators": total_locators, "mismatch": occ_bad})

    # ---- K15 图题保真：manifest caption 是否逐字来自记录元数据 / 正文 ------------
    rec_figs = {f["name"]: f.get("caption", "") for f in (rec.get("figures") or [])}
    cap_bad = []
    for a in man["assets"]:
        if a["asset_class"] != "figure_artifact":
            continue
        nm = a["name"].replace("figures/", "")
        cap = a.get("figure_caption") or (a.get("figure_record") or {}).get("caption")
        if cap is None:            # manifest 把记录元数据放在 source.record_figures
            cap = next((f.get("caption") for f in (man["source"].get("record_figures") or [])
                        if f.get("name") == nm), None)
        if nm in rec_figs and rec_figs[nm] and cap != rec_figs[nm]:
            cap_bad.append({"asset": nm, "manifest_label": a.get("label"),
                            "manifest_caption": cap, "record_caption": rec_figs[nm]})
        if a.get("label") and a["label"] not in md:
            cap_bad.append({"asset": nm, "problem": "label_not_verbatim_in_body",
                            "label": a["label"]})
    check("K15-caption-fidelity", "图题逐字等于记录元数据 caption（非记忆重述）",
          "pass" if not cap_bad else "FAIL",
          {"record_figures": len(rec_figs), "mismatch": cap_bad})

    # ---- 汇总 -------------------------------------------------------------------
    order = {"pass": 0, "needs-fix": 1, "FAIL": 2, "not_run": 3}
    worst = max(order[c["verdict"]] for c in res["checks"])
    res["summary"] = {"checks": len(res["checks"]),
                      "pass": sum(c["verdict"] == "pass" for c in res["checks"]),
                      "needs_fix": sum(c["verdict"] == "needs-fix" for c in res["checks"]),
                      "fail": sum(c["verdict"] == "FAIL" for c in res["checks"]),
                      "worst": [k for k, v in order.items() if v == worst][0],
                      "failed_ids": [c["id"] for c in res["checks"] if c["verdict"] == "FAIL"],
                      "needs_fix_ids": [c["id"] for c in res["checks"] if c["verdict"] == "needs-fix"]}
    (OUT_RUN / "independent_recompute.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    print(json.dumps(res["summary"], ensure_ascii=False, indent=1))
    for c in res["checks"]:
        print(f"  [{c['verdict']:>9}] {c['id']}: {c['name']}")
        if c["verdict"] != "pass":
            print("        ", json.dumps(c["detail"], ensure_ascii=False)[:800])
    return 0


if __name__ == "__main__":
    sys.exit(main())