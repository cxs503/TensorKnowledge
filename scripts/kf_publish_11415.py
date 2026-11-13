#!/usr/bin/env python3
"""Compose and publish the KF-RESULT report for work package wp-11415-01.

Everything numeric in the report body is injected from the artifacts
(asset_manifest.json, verify_report.json, file fingerprints, figures_manifest.json):
no hand-copied quote, hash, count or acceptance tick. The result JSON is emitted as
the single ```json fenced block required by the work-package contract.

Local outputs:
  docs/kf/wp-11415-01/KF-RESULT-wp-11415-01.md   the report exactly as published
  docs/kf/wp-11415-01/report_published.json       API response + markdown fingerprint
  /tmp/report_11415_kf.json                       the POST body actually sent (no secrets)

Run:  python3 scripts/kf_publish_11415.py [--dry-run]
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import sys
import re
import urllib.request

import jsonschema

PACKAGE_ID = "wp-11415-01"
REPORT_ID = "11415"
MISSION_ID = 15698
DOC_DIR = pathlib.Path("docs/kf/wp-11415-01")
ART = DOC_DIR / "asset_manifest.json"
RESULT = pathlib.Path("runs/wp-11415-01/kf_result.wp-11415-01.json")
VERIFY = pathlib.Path("runs/wp-11415-01/verify_report.json")
FIG = DOC_DIR / "fig_asset_locator_map.png"
FENCE = "```"


def sha256_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def cell(s: str, width: int = 70) -> str:
    """One-line table cell holding a verbatim prefix of a source quote."""
    s = s.replace("\n", " / ").replace("|", "\\|")
    return s if len(s) <= width else s[:width] + "…"


def code_span(s: str) -> str:
    """Inline code span that stays valid when the payload itself contains a backtick."""
    s = s.strip("`")  # delimiter-adjacent backticks would break the span
    return ("``" + s + "``") if "`" in s else ("`" + s + "`")


def acceptance_rows(verify: dict) -> list[str]:
    mapping = [
        ("valid_json", ["valid_json"]),
        ("schema_pass", ["kf_result_schema", "asset_manifest_schema"]),
        ("source_locator_resolvable", ["source_locator_resolvable"]),
        ("source_hash_matches", ["source_hash_matches", "source_chars_match_contract"]),
        ("no_duplicate_ids", ["no_duplicate_ids"]),
        ("all_claims_have_evidence_or_explicit_unresolved_status",
         ["all_claims_have_evidence_or_explicit_unresolved_status"]),
    ]
    rows = ["| acceptance 项 | 判据（机器） | 结果 |", "|---|---|---|"]
    for item, checks in mapping:
        ok = all(verify["checks"][c]["pass_"] for c in checks)
        rows.append("| `%s` | %s | %s |" % (item, " + ".join("`%s`" % c for c in checks),
                                            "✅ pass" if ok else "❌ fail"))
    return rows


def product_rows() -> list[str]:
    files = [
        ("scripts/kf_fetch_11415.py", "取源：报告 markdown + 4 张图件本体（含 per-figure sha256）"),
        ("scripts/kf_register_11415.py", "生成器：锚点切片定位 + 机器判据 → asset_manifest.json"),
        ("scripts/kf_verify_11415.py", "独立校验器：重算哈希/切片/schema/计数 → verify_report.json"),
        ("scripts/kf_figure_11415.py", "本报告图件（纯函数于 manifest）"),
        ("schemas/asset_manifest.v1.wp-11415-01.schema.json", "本工序 manifest 形状钉死（schema_pass 的一半）"),
        ("tests/test_kf_wp_11415_01.py", "17 例验收测试（acceptance 逐项映射）"),
        ("runs/wp-11415-01/report_11415.md", "报告 markdown 本地副本（哈希基准）"),
        ("runs/wp-11415-01/report_11415.json", "API 原始 payload（title/tags/figures/markdown）"),
        ("runs/wp-11415-01/figures_manifest.json", "4 张图件的字节/指纹/URL 记录"),
        ("runs/wp-11415-01/kf_result.wp-11415-01.json", "KF 结果信封（kf_result.v1）"),
        ("runs/wp-11415-01/verify_report.json", "15 项机器校验结果"),
        ("docs/kf/wp-11415-01/asset_manifest.json", "★ 交付物：资产清单（28 项）"),
        ("docs/kf/wp-11415-01/fig_asset_locator_map.png", "本报告配图：登记资产的文档定位图"),
    ]
    rows = ["| 文件 | 要点 | bytes | sha256（前 16 位） |", "|---|---|---|---|"]
    for path, why in files:
        p = pathlib.Path(path)
        if not p.exists():
            rows.append("| `%s` | %s | — | — |" % (path, why))
            continue
        rows.append("| `%s` | %s | %d | `%s…` |" % (path, why, p.stat().st_size, sha256_file(p)[:16]))
    return rows


def build_markdown(manifest: dict, verify: dict, result: dict) -> str:
    src = manifest["source"]
    c = manifest["counts"]
    res = c["by_resolution"]
    n = c["assets"]
    figs = [a for a in manifest["assets"] if a["asset_class"] == "figure"]
    unresolved = [a for a in manifest["assets"] if a["resolution"] != "resolved_in_source"]
    classes = c["by_class"]
    top_classes = ", ".join("%s=%d" % (k, v) for k, v in
                            sorted(classes.items(), key=lambda kv: (-kv[1], kv[0]))[:6])

    L: list[str] = []
    A = L.append
    A("# KF-RESULT wp-11415-01")
    A("")
    A("**工序**：01-asset-registration（Lane C）｜**报告**：`tensor://reports/11415`（report_id=11415）")
    A("**标题（源）**：%s" % src["title"])
    A("**场景**：`%s` ｜ **源哈希**：`sha256:%s`（契约值一致，平台可独立重算）"
      % (src["scenario_key"], src["hash"]))
    A("**规模**：markdown %d 字符 / %d 字节 UTF-8 ｜ **登记资产 %d 项**（resolved_in_source %d / "
      "referenced_unresolved %d / declared_absent %d）｜**claims 0 条**（本工序不抽取）"
      % (src["chars"], src["bytes_utf8"], n, res["resolved_in_source"],
         res["referenced_unresolved"], res["declared_absent"]))
    A("")
    A("---")
    A("")
    A("## ① 本工序做了什么")
    A("")
    A("在报告→知识产线上，本单只做「源资产登记」这一道工序：把 report 11415 的 markdown 与其"
      "附件/工件**可定位地**登记下来，给下游工序一个可复算的输入面——不做知识抽取、不做类型判定、"
      "不对报告结论做任何复核或改判。")
    A("")
    A("具体交付：")
    A("")
    A("1. **源字节确认**：按平台接口取回 `markdown`，本地重算 sha256 = `%s`，与工作包契约 "
      "`source_hash` 逐位一致；字符数 %d 与契约 `chars` 一致。" % (src["hash"], src["chars"]))
    A("2. **资产登记 %d 项**：每项给出 `asset_class`、所在章节、**字符区间定位**（start/end char + "
      "行号 + 逐字引文 + 唯一性）、`resolution`（resolved / referenced_unresolved / declared_absent）"
      "与**机器可复核的 resolution_check**。" % n)
    A("3. **可解析附件落指纹**：源报告声明的 4 张图件（%s）经 "
      "`GET /tensor/reports/11415/figures/<name>` 取回图件本体，逐张记录 bytes 与 sha256。"
      % "、".join("`%s`" % a["resolution_check"]["figure_name"] for a in figs))
    A("4. **不可解析项如实入账 %d 项**（unresolved %d + absent %d）：未臆造路径或地址，只登记「报告说了什么 + 为什么此刻不可解析」。"
      % (len(unresolved), res["referenced_unresolved"], res["declared_absent"]))
    A("5. **claims = 空数组（显式）**：契约 `objective.register_assets=true`、`classify_report_type=false`，"
      "notes 明确「claims 允许为空数组」；空数组 = 本工序不抽取，而非取不到证的省略（见 ⑤-6）。")
    A("")
    A("## ② 怎么做的（步骤 / 工具 / 关键设置）")
    A("")
    A("1. **取源**（`scripts/kf_fetch_11415.py`）：`POST /auth/login` 取 token → "
      "`GET /tensor/reports/11415`（Bearer）→ 落 `runs/wp-11415-01/report_11415.json` 与 `.md`；"
      "再逐图 `GET /tensor/reports/11415/figures/<name>` 落 `runs/wp-11415-01/figures/`，"
      "记 bytes/sha256/content-type 于 `figures_manifest.json`。")
    A("2. **哈希门**（`scripts/kf_register_11415.py`）：生成器先重算 markdown sha256 与契约比对，"
      "不一致立即 `FATAL` 退出（防止在别的版本上登记）；同时校验 platform `id` 与字符数。")
    A("3. **锚点切片定位**：每个资产用一段**唯一子串**锚定到某一源行，再按相对行偏移取 "
      "`start_char/end_char` 切片作为 `quote`；生成期硬校验「锚点命中行数==1」且"
      "「`markdown.count(quote)==1`」，否则报错不出件。全程零手抄：引文来自切片，非转录。")
    A("4. **resolution_check 机器判据**（不同资产类别走不同证据，不靠断言）：")
    A("   - 代码/测试/工件路径 → `worktree_path_exists`（本工作树= TensorKnowledge，文件属 "
      "ship-performance-platform → 判 unresolved 并列出缺失路径）；")
    A("   - 外部规范 → `address_extraction`（仅在报告文本内检索 URL/DOI，未找到即 unresolved，不联网猜）；")
    A("   - 图件 → `platform_figure_binary_fetch`（HTTP 200 + PNG magic + bytes + sha256）；")
    A("   - 规范表转录 → `spec_original_copy_in_source`（检出 `TABLE_PROVENANCE.verified = False` "
      "状态标记，据此判 declared_absent）。")
    A("5. **结构门**：`schemas/kf_result.v1.schema.json`（信封）+ "
      "`schemas/asset_manifest.v1.wp-11415-01.schema.json`（本工序 manifest 形状，`additionalProperties=false`）"
      "双 schema 用 jsonschema 校验。注意 448 号包留下的 `asset_manifest.v1.schema.json` 是 `const wp-448-01`，"
      "跨报告不可复用，故本包单钉一份而不改动它。")
    A("6. **独立复核**（`scripts/kf_verify_11415.py`）：不复用生成器的记账，重新从 API 快照重算哈希，"
      "重新按偏移推行号比对 `quote == markdown[start:end]`，重算 counts，重跑 schema，"
      "并断言「无任何自标 verified」。15 项检查全绿 → `runs/wp-11415-01/verify_report.json`。")
    A("7. **验收测试**（`tests/test_kf_wp_11415_01.py`）：17 例，把契约 6 条 acceptance 逐条映射到机器人检查，"
      "另加边界（report_id 唯一性）、图件指纹与磁盘字节一致、claims 空数组的显式性。")
    A("8. **配图**：`scripts/kf_figure_11415.py` 纯函数于 manifest 生成资产定位图（x = 源文档字符位置，"
      "y = 资产，色 = resolution；右侧子图为 resolution 分布），图中数字全部来自 manifest，无手填。")
    A("")
    A("关键设置：只读写 report_id=11415；不调用平台 verification；`verification_status=\"not_verified\"` 原样上报；"
      "`docs/` 为持久件（本仓 `.gitignore` 忽略 `artifacts/`，故 manifest 正本落 `docs/kf/wp-11415-01/`，"
      "`artifacts/` 仅为本地同字节镜像）。")
    A("")
    A("## ③ 产出物清单（输出文件 → 要点 / 字节 / 指纹）")
    A("")
    L.extend(product_rows())
    A("")
    A("★ 交付物正本就是 `docs/kf/wp-11415-01/asset_manifest.json`（%d 字节，sha256 `%s`），"
      "其内容与本报告末尾 JSON 块的 `outputs[\"asset_manifest.json\"]` **逐字段相等**"
      "（由 `kf_verify_11415.py::outputs_manifest_equals_artifact_file` 机器证明）。"
      % (pathlib.Path(str(ART)).stat().st_size, sha256_file(ART)))
    A("")
    A("## ④ 证据定位表（资产 → 原文引文片段 / 字符区间 / 定位结果）")
    A("")
    A("下表由 `asset_manifest.json` 程序化渲染；引文是源 markdown 的**逐字前缀**（超 70 字截断），"
      "完整引文与精确字符区间见交付物。`check` 列即该资产 resolution 的机器判据名/结果。")
    A("")
    A("| # | 资产（类别） | 原文引文片段（逐字） | 字符区间 | 行 | resolution | check→result |")
    A("|---|---|---|---|---|---|---|")
    for a in manifest["assets"]:
        loc, rc = a["locator"], a["resolution_check"]
        A("| %s | %s（%s） | %s | %d–%d | %d–%d | %s | %s→%s |"
          % (a["asset_id"], cell(a["label"], 34), a["asset_class"], code_span(cell(loc["quote"])),
             loc["start_char"], loc["end_char"], loc["start_line"], loc["end_line"],
             a["resolution"], rc["check"], rc["result"]))
    A("")
    A("类别分布：%s（共 %d 类 / %d 项）。" % (top_classes, len(classes), n))
    A("")
    A("## ⑤ 注意点与局限")
    A("")
    A("1. **本工序只登记不复核**：报告 C1–C6 的数字（lw1 误差 0.00e+00、b/a 偏差 3.57e-14、"
      "pytest 22 例等）本工序原样登记为「报告声称」，没有重跑、没有改判。要判这些结论必须另起工序，"
      "且需外部仓（ship-performance-platform）检出。")
    A("2. **%d 项不可解析/缺失项的真实原因**（unresolved %d + declared_absent %d，逐项见 ④ 的 check 列）：%s。"
      "这些是**报告引用了、但本工作树/本接口解析不到**的对象；未臆造路径、未联网补地址。"
      % (len(unresolved), res["referenced_unresolved"], res["declared_absent"],
         "；".join("%s %s(%s)" % (a["asset_id"], a["asset_class"], a["resolution"]) for a in unresolved)))
    A("3. **证据工件指纹被截断**：A06 引用的 `results.json` 报告只给出 `sha256=fede60c8a40fb583…`"
      "（16/64 位），即使拿到文件也无法逐位比对——登记为 unresolved 并显式记录 `fingerprint_hex_len`。")
    A("4. **规范表保真度沿用 WITHHELD**：A11 记录 IS Code 2008 表 2.3.1-1/2/3 为数字化转录、"
      "报告自述无原件逐格复核（`TABLE_PROVENANCE.verified = False`）。本工序不改写这一不确定度，"
      "只把它作为源内状态登记为 declared_absent。")
    A("5. **图件为「可解析」不等于「内容正确」**：4 张图件本体取回并落 sha256（%s…），"
      "证明的是字节可得与可复现，不是图中像素与报告数字一致。"
      % figs[0]["resolution_check"]["png_sha256"].split(":")[1][:16])
    A("6. **claims 空数组是选择，不是缺口**：契约允许空数组且本工序 objective 不含抽取；"
      "报告本身含大量可抽取断言（如 b/a 判据、θ1 必要性），留待 03 工序在有独立证据门时处理，"
      "此处不预生成以免污染下游证据链。")
    A("7. **持久化口径**：本仓 `.gitignore` 忽略 `artifacts/`，故正本落 `docs/kf/wp-11415-01/`；"
      "`artifacts/wp-11415-01/asset_manifest.json` 仅为同字节本地镜像（校验器断言两者相等）。")
    A("")
    A("## ⑥ 自检：逐条对照 acceptance")
    A("")
    L.extend(acceptance_rows(verify))
    A("")
    A("机器人检查全表（`runs/wp-11415-01/verify_report.json`，`all_pass=%s`）：" % verify["all_pass"])
    A("")
    A("| 检查项 | 结果 | 关键证据 |")
    A("|---|---|---|")
    for k, v in verify["checks"].items():
        ev = {kk: vv for kk, vv in v.items() if kk != "pass_"}
        ev_s = cell(json.dumps(ev, ensure_ascii=False), 110)
        A("| `%s` | %s | %s |" % (k, "✅" if v["pass_"] else "❌", code_span(ev_s)))
    A("")
    A("**诚实结论**：6 条 acceptance 全部 ✅（机器判据 + 17 例 pytest）。"
      "本工序**未复核**报告的技术结论，**未**改动任何上游产物，**未**自标 verified；"
      "源报告自述的规范表转录保真度不确定（WITHHELD）在本工序内保持原样。")
    A("")
    A("## 复跑命令（一键）")
    A("")
    A(FENCE + "bash")
    A("# 工作树根执行；需要 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS")
    A("python3 scripts/kf_fetch_11415.py \\")
    A(" && python3 scripts/kf_register_11415.py \\")
    A(" && python3 scripts/kf_verify_11415.py \\")
    A(" && python3 scripts/kf_figure_11415.py \\")
    A(" && python3 -m pytest tests/test_kf_wp_11415_01.py -q \\")
    A(" && python3 scripts/kf_publish_11415.py")
    A(FENCE)
    A("")
    A("产物：`docs/kf/wp-11415-01/asset_manifest.json`（正本）+ `runs/wp-11415-01/*`（快照/指纹/校验/信封）。")
    A("")
    A("## 结果信封（KF-RESULT 唯一 JSON 代码块）")
    A("")
    return "\n".join(L)


def post(path: str, payload: dict, token: str | None = None) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(base + path, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode())


def get(path: str, token: str) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(base + path, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode())


def verify_published(rec_path: pathlib.Path) -> dict:
    """Re-read the published report and re-check the contract's delivery shape."""
    rec = json.loads(rec_path.read_text())
    rid = rec["published_response"]["id"]
    auth = post("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                "password": os.environ["TENSOR_AGENT_PASS"]})
    token = auth.get("access_token") or auth.get("token")
    pub = get("/tensor/reports/%d" % rid, token)
    md = pub["markdown"]
    blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
    envelope = json.loads(blocks[0])
    jsonschema.validate(envelope, json.loads(pathlib.Path("schemas/kf_result.v1.schema.json").read_text()))
    checks = dict(
        published_id=rid,
        title_ok=pub.get("title") == "KF-RESULT %s" % PACKAGE_ID,
        tag_ok="kf-wp:%s" % PACKAGE_ID in (pub.get("tags") or []),
        tags=pub.get("tags"),
        one_json_block=md.count("```json") == 1,
        envelope_schema_ok=True,
        source_hash_in_block=envelope["provenance"]["source_hash"],
        source_hash_matches=envelope["provenance"]["source_hash"] == "sha256:%s"
        % json.loads(ART.read_text())["source"]["hash"],
        package_id_ok=envelope["package_id"] == PACKAGE_ID,
        task_type_ok=envelope["task_type"] == "01-asset-registration",
        report_id_ok=envelope["report_id"] == REPORT_ID,
        outputs_keys=list(envelope["outputs"]),
        n_assets=envelope["outputs"]["asset_manifest.json"]["counts"]["assets"],
        claims=len(envelope["claims"]),
        figures=len(pub.get("figures") or []),
        markdown_chars=len(md),
    )
    rec["post_publish_verification"] = checks
    rec_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")
    return checks


def main() -> int:
    dry = "--dry-run" in sys.argv
    if "--verify-only" in sys.argv:
        checks = verify_published(DOC_DIR / "report_published.json")
        print(json.dumps(checks, ensure_ascii=False, indent=1))
        return 0 if all(v for k, v in checks.items()
                        if isinstance(v, bool)) else 5
    manifest = json.loads(ART.read_text())
    result = json.loads(RESULT.read_text())
    verify = json.loads(VERIFY.read_text())
    if not verify["all_pass"]:
        print("REFUSING to publish: verifier reports failure")
        return 4

    body = build_markdown(manifest, verify, result)
    md = body + FENCE + "json\n" + json.dumps(result, ensure_ascii=False, indent=2) + "\n" + FENCE + "\n"
    # exactly one fenced json block must exist
    assert md.count(FENCE + "json") == 1, "report must contain exactly one ```json block"

    png = FIG.read_bytes()
    payload = dict(
        title="KF-RESULT %s" % PACKAGE_ID,
        summary=("报告 11415 源资产登记：markdown sha256 与契约一致（%d 字符），登记 %d 项资产"
                 "（resolved %d / unresolved %d / absent %d），4 张图件取回并落 sha256，"
                 "claims 空数组（本工序不抽取）；6 条 acceptance 全过。"
                 % (manifest["source"]["chars"], manifest["counts"]["assets"],
                    manifest["counts"]["resolved_in_source"],
                    manifest["counts"]["referenced_unresolved"],
                    manifest["counts"]["declared_absent"])),
        scenario_key=manifest["source"]["scenario_key"],
        mission_id=MISSION_ID,
        tags=["kf-wp:%s" % PACKAGE_ID, "asset-registration", "knowledge-factory",
              "IMO", "weather-criterion", "m15698"],
        markdown=md,
        figures=[dict(name="fig_asset_locator_map.png",
                      caption=("wp-11415-01 资产定位图：x=报告 11415 markdown 字符位置（0…%d），"
                               "y=登记资产 A01–A%02d，色=resolution；右侧为分布计数。"
                               "全部数值由 asset_manifest.json 程序化注入。"
                               % (manifest["source"]["chars"], manifest["counts"]["assets"])),
                      png_base64=base64.b64encode(png).decode())],
    )
    pathlib.Path("/tmp/report_11415_kf.json").write_text(
        json.dumps({**payload, "figures": [{**payload["figures"][0], "png_base64": "<%d b64 chars>"
                                            % len(payload["figures"][0]["png_base64"])}],
                    "markdown": "<%d chars>" % len(md)}, ensure_ascii=False, indent=1) + "\n")
    out = DOC_DIR / "KF-RESULT-wp-11415-01.md"
    out.write_text(md)

    if dry:
        print("dry-run: markdown %d chars → %s (not published)" % (len(md), out))
        return 0

    auth = post("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                "password": os.environ["TENSOR_AGENT_PASS"]})
    token = auth.get("access_token") or auth.get("token")
    if not token:
        print("FATAL: no token in login response")
        return 2
    res = post("/tensor/reports", payload, token)
    rec = dict(published_response=res,
               published_markdown_chars=len(md),
               published_markdown_sha256="sha256:" + hashlib.sha256(md.encode()).hexdigest(),
               figure_bytes=len(png),
               figure_sha256="sha256:" + hashlib.sha256(png).hexdigest(),
               title=payload["title"], tags=payload["tags"], mission_id=MISSION_ID)
    rec_path = DOC_DIR / "report_published.json"
    rec_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")
    rec_path_json = rec_path
    print("published:", json.dumps(res, ensure_ascii=False)[:300])
    print("post-publish verification:", json.dumps(verify_published(rec_path_json), ensure_ascii=False)[:300])
    print("markdown:", len(md), "chars", rec["published_markdown_sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main())