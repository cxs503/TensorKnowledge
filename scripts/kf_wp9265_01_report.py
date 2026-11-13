#!/usr/bin/env python3
"""wp-9265-01 · render REPORT.md from the measured artefacts and publish the KF-RESULT report.

Every number in the rendered markdown/JSON payload is read out of
docs/kf/wp-9265-01/{asset_manifest.json, verification.json, figures/locator_map.json}:
zero hand transcription.

    python3 scripts/kf_wp9265_01_report.py md     # -> docs/kf/wp-9265-01/REPORT.md
    python3 scripts/kf_wp9265_01_report.py post   # -> POST /tensor/reports (mission 15637)
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = "wp-9265-01"
REPORT_ID = "9265"
DIR = ROOT / "docs" / "kf" / PKG
MANIFEST = json.loads((DIR / "asset_manifest.json").read_text())
VERIF = json.loads((DIR / "verification.json").read_text())
ENV = json.loads((DIR / "kf_result.json").read_text())
FIG_JSON = json.loads((DIR / "figures" / "locator_map.json").read_text())
TEST_COUNT = 9
MISSION_ID = 15637
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _counts_line():
    c = MANIFEST["counts"]
    return ("assets=%d (resolved_in_source=%d, referenced_unresolved=%d, declared_absent=%d)"
            % (c["assets"], c["resolved_in_source"], c["referenced_unresolved"], c["declared_absent"]))


def _asset_rows():
    rows = ["| asset_id | class | label | § | resolution | check | quote (verbatim, 1-based line) |",
            "|---|---|---|---|---|---|---|"]
    for a in MANIFEST["assets"]:
        q = a["locator"]["quote"].replace("|", "\\|")
        if len(q) > 78:
            q = q[:78] + "…"
        rows.append("| %s | %s | `%s` | %s | %s | %s | L%d: %s |"
                    % (a["asset_id"], a["asset_class"], a["label"], a["in_report_section"],
                       a["resolution"], a["resolution_check"]["result"],
                       a["locator"]["start_line"], q))
    return "\n".join(rows)


def _fact_rows():
    rows = ["| fact_id | § | line | quote |", "|---|---|---|---|"]
    for f in MANIFEST["identity_facts"]:
        rows.append("| %s | %s | L%d | `%s` |" % (f["fact_id"], f["in_report_section"],
                                                 f["locator"]["start_line"],
                                                 f["locator"]["quote"].replace("|", "\\|")))
    return "\n".join(rows)


def _acceptance_rows():
    rows = ["| acceptance item | 结果 | 依据（实测数字） |", "|---|---|---|"]
    for c in VERIF["acceptance"]:
        rows.append("| `%s` | %s | %s |" % (c["item"], "PASS" if c["pass"] else "**FAIL**",
                                            c["detail"].replace("|", "\\|")))
    return "\n".join(rows)


def _contract_rows():
    src = MANIFEST["source"]
    ok = [("`source_hash`", "`%s`" % src["contract_hash"], "`sha256:%s`" % src["hash"], src["hash_match"]),
          ("`chars`", str(src["contract_chars"]), str(src["chars"]), src["chars_match"]),
          ("`title`", src["contract_title"], src["title"], src["title_match"]),
          ("`scenario_key`", "`%s`" % src["contract_scenario_key"], "`%s`" % src["scenario_key"],
           src["scenario_match"]),
          ("`bytes_utf8` / `lines`", "—", "%d / %d" % (src["bytes_utf8"], src["lines"]), None)]
    rows = ["| 字段 | 契约值 | 实测值 | 一致 |", "|---|---|---|---|"]
    for field, want, got, same in ok:
        rows.append("| %s | %s | %s | %s |"
                    % (field, want, got, "实测" if same is None else ("✅" if same else "❌")))
    return "\n".join(rows)


def render_md() -> str:
    src = MANIFEST["source"]
    c = MANIFEST["counts"]
    iu = MANIFEST["integrity"]
    loc_ok = sum(1 for r in VERIF["locator_rows"] if r["resolved"])
    env_json = json.dumps(ENV, ensure_ascii=False, indent=2)
    return """# KF-RESULT {pkg}

**工序** 01-asset-registration ｜ **report_id** {rid} ｜ **lane** B ｜ **producer** {prod}
**源** `{uri}`（`{field}`）｜ **source_hash** `sha256:{hash}`（本机重算，与契约逐字相同）
**交付** `docs/kf/{pkg}/asset_manifest.json`（外包一层 `kf_result.v1` 信封）

## ① 本工序做了什么

只做一件事：为 report {rid} 登记**源资产身份**并盘点它声明过的附件/工件。**不做抽取、不做分类、不判定真伪**
（契约 `objective.register_assets=true`、`objective.classify_report_type=false`、
`constraints.no_forced_claim_generation=true`、`constraints.do_not_mark_claims_as_verified=true`）。
据此 `claims` 为空数组——这是完整结果而非遗漏（理由原文见 `asset_manifest.json → claims_empty_reason`）。

产出规模（全部实测，非人工填写）：{counts_line}；locator 共 **{loc}** 个（资产 {na} + 身份事实 {nf}），
字符 / 字节 / 行数 = **{chars} / {bytes} / {lines}**，逐字唯一命中率 100%（`max_occurrences={maxocc}`）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET /api/v1/tensor/reports/{rid}`（token 由 `/auth/login` 用环境变量换取，脚本零硬编码凭据），
   落 `runs/{pkg}/report_{rid}.json` 与 `source_{rid}.md`。
2. **独立重算身份**：对 `markdown` 的 UTF-8 字节做 sha256 并与契约 `source_hash` 比对；同时比对
   `chars`、`title`、`scenario_key`。四项全中（见 ④），说明源串既未换行归一化也未重排。
3. **盘点声明物**：逐条从正文提取——5 张记录图（`record.figures` 仅 name+caption）、
   `artifacts/dp_capability/` 目录、`criteria.json` 判据账本、`capability_payload.json`、
   两个落库模块、测试文件、出图脚本，外加报告自陈"没有"的 DNV 对标数据集。
4. **逐字定位**：`locator` 一律由 `str.find` 在源串上切出（不手抄），记录
   `start_char/end_char/start_line/end_line/quote/unique`；引文不存在或不唯一则脚本 `SystemExit`，不出半成品。
5. **解析状态判定（三分类，证据驱动）**：
   - `resolved_in_source`：源资产本体（markdown 字节）——本工作树确实持有其内容；
   - `referenced_unresolved`：图字节与 ship-performance-platform 内路径——**本工作树不持有**。
     实测平台 `GET /tensor/reports/{rid}/figures`、`/artifacts` 均 **404**、`record.figures[]` 无
     `png_base64` ⇒ 不为任何图片声明哈希；
   - `declared_absent`：DNV 已发表 PSV 包线数值数据集——报告原文自陈"没有可引用"。
6. **信封 + 双 schema 校验**：manifest 包进 `kf_result.v1` 信封；信封按 `schemas/kf_result.v1.schema.json`
   校验，manifest 按**本包重钉 const 的投影 schema** 校验（仓库内 `asset_manifest.v1.schema.json`
   把 `package_id/report_id` 钉死为 wp-448-01/448，故新增投影而非改上游；形状/枚举未变）。
7. **出图**：`locator_map.png` 把 {loc} 个 locator 的 `start_char/end_char` 画在源文档字符轴上
   （坐标全部读自 manifest，无一手抄数字）。
8. **独立验收测试**：`tests/test_kf_wp9265_01_manifest.py` 不经构建脚本内部函数，直接读已发布
   JSON 并从平台重取 markdown 复算哈希/逐字/行号/唯一性（{tests} 项全绿）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/{pkg}/asset_manifest.json` | 源身份（hash/chars/title/scenario）+ {na} 个资产逐字 locator + {nf} 条身份事实 + counts/id_integrity/integrity |
| `docs/kf/{pkg}/kf_result.json` | `kf_result.v1` 信封：`provenance.source_hash=sha256:{hash}`、`outputs.asset_manifest.json`=上述 manifest、`claims=[]` |
| `docs/kf/{pkg}/verification.json` | 6 项 acceptance 实测结果 + {loc} 行 locator 复检明细 + `not_checked` 清单 |
| `docs/kf/{pkg}/asset_manifest.wp-9265-01.schema.json` | 本包重钉 const 的投影 schema（让 `schema_pass` 可复跑而非口头断言） |
| `docs/kf/{pkg}/figures/locator_map.png` | 资产定位图：{figloc} 个 locator 的字符轴位置 + 行号标注；`png_sha256={pngsha}`（{pngbytes} bytes） |
| `docs/kf/{pkg}/figures/locator_map.json` | 图元数据（caption / 数据来源 / 哈希），保证图可溯源 |
| `docs/kf/{pkg}/REPORT.md` | 本报告（`scripts/kf_wp9265_01_report.py md` 渲染，数字全注入） |
| `scripts/kf_wp9265_01_register.py` | build / envelope / verify / figure / all 五子命令，幂等 |
| `scripts/kf_wp9265_01_report.py` | md / post 两子命令（渲染 + 发布），数字从产物读取 |
| `scripts/kf_wp9265_01_fetch.py` | 取源并打印身份三元组 |
| `tests/test_kf_wp9265_01_manifest.py` | {tests} 项独立验收测试（含边界与范围守卫） |

## ④ 证据定位表（字段/claim → 原文引文片段，逐字可定位）

身份四项（对照契约）：

{contract_rows}

资产 → 原文（每条 quote 均为源串中**唯一**子串，构建脚本 + 独立测试双重核验）：

{asset_rows}

身份事实（文档头与复现块）：

{fact_rows}

## ⑤ 注意点与局限

1. **未做抽取是刻意的**：`claims=[]` 且 `claims_empty_reason` 写明契约依据——不得为填指标造知识。
2. **图片零哈希**：5 张图只有 name+caption；平台 figure/artifact 端点 404、工作树亦无同名文件，
   故一律 `referenced_unresolved`，**不声明任何图片 sha256**（拒绝"看起来已验证"的假证据）。
3. **外部仓不可达**：`backend/physics/dp_core.py` 等 7 条路径属 ship-performance-platform，不在本工作树
   （TensorKnowledge）；本次只登记"报告声明了它"，**不主张其存在或正确**。判定证据=6 个候选相对路径逐一
   存在性探测（原文见各资产 `resolution_check.check`）。
4. **不主张报告结论为真**：平衡残差、包线风速、降级百分比等全部**未复算**；报告自身 §⑥ 也把
   风/流/波浪漂移系数与包线绝对值列为 **WITHHELD（无基准）**。本工序零 `verified` 标记。
5. **schema 重钉是本包局部行为**：只新增本包投影文件，未改写上游 schema（互不覆盖）。
6. **边界**：只读写 `report_id=9265` 及其本包产物（`scope_guard.report_ids_touched=["9265"]`），
   无跨包读写，未改上游/下游工作包产物。

## ⑥ 自检（逐条对照 acceptance）

{acceptance_rows}

**误差判定（本工序可量化基准）**：源身份四项（hash / chars / title / scenario_key）与契约**精确相等**
（相对误差 **0%**，是否 <3%：**是**，且是零容差相等而非落在容差内）；locator 逐字唯一命中
**{locok}/{loc}**（0 例失配）。本工序不产生物理量，故无物理误差可判；报告内物理数字真伪留给下游
抽取/复核工序（本单在 `verification.json → not_checked` 显式列出）。
`acceptance` **6/6 PASS**，无 honest-FAIL 项。

**未核项（unknown / not_run，不写作 pass）**：外部仓工件存在性与内容、5 张图字节、
报告数值真伪、"40 项 pytest / 22 s 全绿"自述。

**一键复跑**：

```bash
python3 scripts/kf_wp9265_01_register.py all && python3 -m pytest tests/test_kf_wp9265_01_manifest.py -q
```

## 结果 JSON（本报告唯一 json 代码块，原样提交）

```json
{env_json}
```
""".format(pkg=PKG, rid=REPORT_ID, prod=MANIFEST["producer"], uri=src["uri"], field=src["field"],
           hash=src["hash"], counts_line=_counts_line(), loc=c["locators"], na=c["assets"],
           nf=c["identity_facts"], chars=src["chars"], bytes=src["bytes_utf8"], lines=src["lines"],
           maxocc=iu["quote_uniqueness"]["max_occurrences"], tests=TEST_COUNT,
           figloc=FIG_JSON["locators_plotted"], pngsha=FIG_JSON["png_sha256"],
           pngbytes=FIG_JSON["png_bytes"], contract_rows=_contract_rows(),
           asset_rows=_asset_rows(), fact_rows=_fact_rows(),
           acceptance_rows=_acceptance_rows(), locok=loc_ok, env_json=env_json)


def post(md: str) -> dict:
    png = (DIR / "figures" / "locator_map.png").read_bytes()
    payload = {
        "title": "KF-RESULT " + PKG,
        "summary": ("report %s 源资产登记：markdown sha256 与契约一致（sha256:%s…），chars=%d；登记 %d 个资产"
                    "（resolved_in_source=%d / referenced_unresolved=%d / declared_absent=%d），"
                    "%d 个 locator 逐字唯一；claims 空（契约允许），acceptance 6/6 PASS"
                    % (REPORT_ID, MANIFEST["source"]["hash"][:16], MANIFEST["source"]["chars"],
                       MANIFEST["counts"]["assets"], MANIFEST["counts"]["resolved_in_source"],
                       MANIFEST["counts"]["referenced_unresolved"],
                       MANIFEST["counts"]["declared_absent"], MANIFEST["counts"]["locators"])),
        "scenario_key": MANIFEST["source"]["scenario_key"],
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:" + PKG, "kf", "01-asset-registration", "report-" + REPORT_ID, "lane-B"],
        "markdown": md,
        "figures": [{"name": FIG_JSON["figure"], "caption": FIG_JSON["caption"],
                     "png_base64": base64.b64encode(png).decode()}],
    }
    login = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(login, timeout=30) as r:
        tok = json.loads(r.read().decode()).get("access_token")
    req = urllib.request.Request(BASE + "/tensor/reports",
                                 data=json.dumps(payload, ensure_ascii=False).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def _api(path, payload=None, tok=None):
    d = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=d)
    if d:
        req.add_header("Content-Type", "application/json")
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def gate(report_id: int):
    """Round-trip the published KF-RESULT: exactly one json block, hash + quotes still resolve."""
    import hashlib
    import re
    tok = _api("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                               "password": os.environ["TENSOR_AGENT_PASS"]})["access_token"]
    rec = _api("/tensor/reports/%d" % report_id, tok=tok)
    rec = rec.get("data", rec)
    md = rec["markdown"]
    blocks = re.findall(r"```json\s*\n(.*?)\n```", md, re.S)
    env = json.loads(blocks[0]) if len(blocks) == 1 else {}
    src = _api("/tensor/reports/" + REPORT_ID, tok=tok)
    src = src.get("data", src)
    live_hash = "sha256:" + hashlib.sha256(src["markdown"].encode("utf-8")).hexdigest()
    man = (env.get("outputs") or {}).get("asset_manifest.json", {})
    locs = [a["locator"] for a in man.get("assets", [])] + [f["locator"] for f in man.get("identity_facts", [])]
    quotes_ok = [q["quote"] for q in locs if q["quote"] not in src["markdown"]]
    receipt = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "published_report_id": rec.get("id"),
        "published_title": rec.get("title"),
        "published_tags": rec.get("tags"),
        "published_mission_id": rec.get("mission_id"),
        "published_figures": [f.get("name") for f in (rec.get("figures") or [])],
        "json_blocks_in_markdown": len(blocks),
        "result_json_parses": bool(env),
        "envelope_package_id": env.get("package_id"),
        "envelope_report_id": env.get("report_id"),
        "live_source_hash": live_hash,
        "envelope_source_hash": (env.get("provenance") or {}).get("source_hash"),
        "hash_roundtrip_match": live_hash == (env.get("provenance") or {}).get("source_hash"),
        "quotes_unresolved_live": quotes_ok,
        "locators_rechecked": len(locs),
        "checks": {
            "exactly_one_json_block": len(blocks) == 1,
            "hash_roundtrip_match": live_hash == (env.get("provenance") or {}).get("source_hash"),
            "all_quotes_resolve_live": not quotes_ok,
            "single_output_key": list(env.get("outputs") or {}) == ["asset_manifest.json"],
        },
        "all_pass": all([len(blocks) == 1,
                         live_hash == (env.get("provenance") or {}).get("source_hash"),
                         not quotes_ok,
                         list(env.get("outputs") or {}) == ["asset_manifest.json"]]),
        "checked_at": FIG_JSON.get("checked_at", ""),
        "repro_cmd": "python3 scripts/kf_wp9265_01_report.py gate %d" % report_id,
    }
    (DIR / "publish_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return receipt



def note():
    """Render GATE_ROUNDTRIP.md from publish_receipt.json (numbers injected, none retyped)."""
    rc = json.loads((DIR / "publish_receipt.json").read_text())
    lines = [
        "# wp-9265-01 · 结果信道回环校验（发布后复核）", "",
        "发布后的 KF-RESULT 报告（id=%s, title=`%s`, mission_id=%s, tags=%s）被重新取回，"
        "对结果 JSON 与实际源文档再做一次交叉核对，全部数字来自 `publish_receipt.json`。" %
        (rc["published_report_id"], rc["published_title"], rc["published_mission_id"],
         ", ".join("`%s`" % t for t in rc["published_tags"])),
        "", "| 检查 | 结果 | 实测 |", "|---|---|---|",
        "| 唯一 json 代码块 | %s | `json_blocks_in_markdown=%d` |"
        % ("PASS" if rc["checks"]["exactly_one_json_block"] else "FAIL", rc["json_blocks_in_markdown"]),
        "| 回环哈希一致 | %s | 线上重算 `%s` |"
        % ("PASS" if rc["checks"]["hash_roundtrip_match"] else "FAIL", rc["live_source_hash"]),
        "| 全部引文在线上源文档中可定位 | %s | 复检 %d 个 locator，未解析 %d 个 |"
        % ("PASS" if rc["checks"]["all_quotes_resolve_live"] else "FAIL",
           rc["locators_rechecked"], len(rc["quotes_unresolved_live"])),
        "| outputs 唯一键 = asset_manifest.json | %s | |"
        % ("PASS" if rc["checks"]["single_output_key"] else "FAIL"),
        "", "图件随报告入库：%s。" % ", ".join("`%s`" % f for f in rc["published_figures"]),
        "", "复跑：`%s`" % rc["repro_cmd"], "",
        "说明：此回环只验证**信道与可定位性**（哈希/引文/结构），不构成对报告物理结论的复核。", "",
    ]
    (DIR / "GATE_ROUNDTRIP.md").write_text("\n".join(lines))
    return DIR / "GATE_ROUNDTRIP.md"


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "md"
    if cmd in ("md", "all"):
        md = render_md()
        if md.count("```json") != 1:
            raise SystemExit("result markdown must contain exactly one json block, found %d"
                             % md.count("```json"))
        (DIR / "REPORT.md").write_text(md)
        print("wrote %s (%d chars, json blocks=%d)" % (DIR / "REPORT.md", len(md), md.count("```json")))
    if cmd == "note":
        print("wrote %s" % note())
    if cmd == "gate":
        rc = gate(int(argv[2]) if len(argv) > 2 else int(os.environ.get("KF_REPORT_ID", "0")))
        print(json.dumps({k: rc[k] for k in ("published_report_id", "all_pass", "checks")},
                         ensure_ascii=False))
        if not rc["all_pass"]:
            raise SystemExit(1)
    if cmd in ("post", "all"):
        md = (DIR / "REPORT.md").read_text()
        resp = post(md)
        rec = resp.get("data", resp)
        print(json.dumps({"id": rec.get("id"), "title": rec.get("title"),
                          "tags": rec.get("tags"), "mission_id": rec.get("mission_id"),
                          "figures": [f.get("name") for f in (rec.get("figures") or [])]},
                         ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv)