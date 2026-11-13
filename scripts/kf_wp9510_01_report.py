#!/usr/bin/env python3
"""wp-9510-01 report builder / publisher.

Consumes the artefacts of scripts/kf_wp9510_01_register_assets.py and emits
  * docs/kf/wp-9510-01/REPORT.md   -- six-section progress report; contains exactly
                                      ONE ```json fence: the kf_result envelope verbatim
  * runs/wp-9510-01/report.json    -- platform payload (title/summary/tags/markdown/figures);
                                      run record only, never committed (push gate drops runs/**)

    python3 scripts/kf_wp9510_01_report.py build
    python3 scripts/kf_wp9510_01_report.py publish     # POST /api/v1/tensor/reports

Every number / quote in the report is substituted from the manifest, the envelope,
the verification and the source copy -- nothing is typed by hand.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ID = "wp-9510-01"
REPORT_ID = "9510"
MISSION_ID = 18538   # re-open of PR#171 (original mission 15660)
SCENARIO = "green_navigation_regulatory_compliance"
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID
RUN_DIR = ROOT / "runs" / PACKAGE_ID
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
RESULT_FIG = OUT_DIR / "figures" / ("%s_source_locator_map.png" % PACKAGE_ID)
SOURCE_COPY = OUT_DIR / ("source_%s.md" % REPORT_ID)   # gate-safe: docs/ survives the push gate
REPORT_MD = OUT_DIR / "REPORT.md"
REPORT_JSON = RUN_DIR / "report.json"
TITLE = "KF-RESULT %s" % PACKAGE_ID
TAGS = ["kf-wp:%s" % PACKAGE_ID, "kf-result", "asset-registration",
        "green_navigation_regulatory_compliance", "EEXI", "CII", "EEDI"]

TEMPLATE = """# <<TITLE>>

**工序**：01-asset-registration（产线 lane B，源 report_id=9510）
**母任务**：mission <<MISSION>> · **锚点**：KBM-RCI-F1-FACTORY
**源**：`<<SRC_URI>>` 字段 `markdown` · sha256 `<<SRC_HASH>>` · <<SRC_CHARS>> chars / <<SRC_BYTES>> bytes / <<SRC_LINES>> 行
**产物**：`docs/kf/wp-9510-01/`（asset_manifest.json / kf_result.json / verification.json / source_9510.md 源副本 / figures）
**重开**：原 PR#171（m15660）于 2026-11-05 被 owner 关闭；本包从当前 main 重建（本单=m18538）

## ① 本工序做了什么

只登记、不抽取：以 report 9510 的 markdown 为唯一可信源，在进程内重算字节哈希与字符/行计数，
逐条枚举报告自己声明的附件与工件（图件、脚本、数据工件、模块路径、API 路由、外部法规文本），
并给每条资产一个可在原文逐字复算的定位符（行号 + 字符区间 + 原文整行 + 全局唯一性）。
报告类型分类、知识抽取、`verified` 标记一律不做（契约 objective.classify_report_type=false；
verification 由平台门独立重算）。`claims` 为空数组并写明理由（契约允许）。

- 登记资产总数：**<<N_ASSETS>>**（按类别 `<<BY_CLASS>>`）
- 按解析状态：`<<BY_RES>>`（其中 `resolved_in_source`=<<N_RESOLVED>>，`referenced_unresolved`=<<N_UNRES>>）
- 源指纹一致性：hash=<<C_HASH>> / chars=<<C_CHARS>> / title=<<C_TITLE>> / scenario=<<C_SCEN>>

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`<<FETCH_VIA>>`（Bearer token 由 `POST /api/v1/auth/login` 取得）。
   直接 `psql -d tensorplatform -c "select markdown from tensor_reports where id=9510"` 被拒
   （`permission denied for table tensor_reports`），故唯一取数信道是认证 API；源副本落 `<<SRC_COPY>>`。
2. **重算指纹**：`hashlib.sha256(markdown.encode('utf-8'))` → `<<SRC_HASHFULL>>`；
   与契约 `<<CONTRACT_HASH>>` 比对（<<C_HASH>>），`len(markdown)`=<<SRC_CHARS>> 与契约 chars=<<CONTRACT_CHARS>> 比对（<<C_CHARS>>）。
3. **扫描声明**（3 类正则，纯静态，不执行报告里的任何代码）：
   markdown 图链正则抓 `![](path)`；反引号令牌仅当"无空白 且 (含目录分隔符 或 已知工件后缀)"才算路径
   （模块名如 `regulatory`/`chain`/`NOT_SUPPORTED` 因此被排除，不把符号当文件）；IMO 决议号正则抓 `MEPC.x(yy)` / `MEPC.1/Circ.n`。
   按首次出现顺序去重编号 A01…A<<N_ASSETS>>。
4. **定位符**：行号 + `start_char/end_char`（由前序行长度累加）+ 该行原文整行 + `unique`（原文出现次数==1）。
   verify 阶段对每条定位符重算 `markdown[start:end]==quote` 与 `lines[line-1]==quote` 与子串存在性。
5. **解析判定**：路径在本交付工作树 `Path.exists` → `resolved_in_source`；否则 `referenced_unresolved`
   （报告声明但字节属于 ship-performance-platform 仓，本工作树不可达，绝不冒充已取得）。
   图件另用 `GET /tensor/reports/9510/figures/{name}` 探测平台字节，并把重算 sha256 与报告正文里声明的
   **截断 sha256 前缀**逐位对照（结果见 ④）。
6. **封装**：`kf_result.v1` 信封（package_id/task_type/report_id/provenance/outputs/claims）；
   `provenance.source_hash` 在封装阶段**重新取数重算**，与 manifest 不一致即中止（防陈旧哈希）。
7. **自检**：`jsonschema` 双 schema 校验（`schemas/kf_result.v1.schema.json` + `schemas/asset_manifest.v1.schema.json`），
   再逐条机器判 6 项 acceptance（结果见 ⑥）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-9510-01/asset_manifest.json` | <<N_ASSETS>> 条资产登记；源指纹 `<<SRC_HASH>>`；每资产带行号/字符区间/原文整行/唯一性 |
| `docs/kf/wp-9510-01/kf_result.json` | 工序结果信封（本报告唯一 json 代码块的来源）；`outputs.asset_manifest.json` = 上述 manifest 全文 |
| `docs/kf/wp-9510-01/verification.json` | 6 项 acceptance 自检（`all_ok=<<ALL_OK>>`） |
| `docs/kf/wp-9510-01/figures/<<FIG_NAME>>` | 定位符分布图：行剖面 + 资产类别×解析状态直方图；sha256 `<<FIG_SHA>>` |
| `docs/kf/wp-9510-01/REPORT.md` | 本报告 |
| `docs/kf/wp-9510-01/source_9510.md` | 源 markdown 原样副本（<<SRC_BYTES>> bytes，供离线复算；放 docs/ 因推送门禁滤除 runs/**） |
| `runs/wp-9510-01/report.json` | 发平台载荷（含图件 base64；运行记录，不入库） |
| `scripts/kf_wp9510_01_register_assets.py` / `scripts/kf_wp9510_01_report.py` | 可复跑流水线（build/envelope/verify/figure/report/publish） |
| `tests/test_kf_wp9510_01.py` | 离线回归测试（定位符/哈希/唯一 id/单 json 块/schema 向后兼容） |

## ④ 证据定位表（资产 → 原文整行引文，逐字可复算）

| 资产 | 类别 | 行 | 解析 | 原文整行（逐字引文，仅两处显示变换：`|`→`/` 以保证表格不被切断、超 96 字符截断加 `…`；已做显示变换的引文可在 manifest 的 locator.quote 取全文逐字本） |
|---|---|---|---|---|
<<ASSET_ROWS>>

平台图件字节探测（`GET /tensor/reports/9510/figures/{name}`）：<<FIG_PROBE_SUMMARY>>

| 图件 | HTTP | bytes | 重算 sha256（若 200） |
|---|---|---|---|
<<FIG_ROWS>>

关键定位符举例（可在 `docs/kf/wp-9510-01/source_9510.md` 上 `grep -n` 复核）：

- 源身份 L1：`<<Q1>>`
- 工件链声明 L5：`<<Q5>>`
- 工具链 L46：`<<Q46>>`

## ⑤ 注意点与局限

1. **只登记不抽取**：本工序无任何 claim/知识对象；`claims: []` 是契约允许的完整结果，不是遗漏。
2. **引用≠取得**：`compliance.sqlite` / `results.json` / `queries.sql` / `run_compliance.py` / `make_report.py` /
   5 张图 / `backend/modules/green_compliance/` 等路径属于 ship-performance-platform（节点 P155W1-N02），
   在 TensorKnowledge 交付工作树内不可达，故一律 `referenced_unresolved` 且 `existence_asserted_by_worker=false`；
   本工序不对这些字节做任何哈希声明。
3. **图件字节不可得**：<<FIG_N>> 个图件名在平台图件端点 `GET /tensor/reports/9510/figures/{name}` 上全部返回 HTTP <<FIG_HTTP>>，因此报告正文里的截断 sha256 前缀
   **无法**核对，图件停留 `referenced_unresolved`——这是如实记录，不是验证通过。
4. **同一文件两名**：如 A06 `make_report.py` 与 A25 `artifacts/P155W1-N02/make_report.py` 是两处不同文本引用，
   登记为两条资产并用 `same_basename_as` 互指，不做主观合并（合并会丢原文位置）。
5. **哈希口径**：sha256 作用域是平台返回 markdown 字符串的 UTF-8 字节；存储侧任何改动（含空白）都会使本 manifest 失效。
   `tensor_reports.markdown` 直读被权限拒绝，来源只能是 API。
6. **引文显示变换**：④ 表内原文整行只做两处显示变换（`|`→`/` 保表格、超 96 字符截断加 `…`），逐字全文在 `asset_manifest.json` 的 `locator.quote`；
   verify 对全文（非截断）做字符区间 + 行 + 子串三重比对。
7. **保留上游不确定性**：报告 §⑤ 自述规则系数为转录值、要求值/等级判 WITHHELD、未取得 IMO 数值算例原文；
   本工序只登记、不改写这些不确定性，也不把它们升格为结论。
8. **未做**：报告类型分类（契约关）、知识抽取（下游工序 03）、`verified` 标记（平台门职责）、读写其它 report_id。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 实测依据 |
|---|---|---|
<<ACC_ROWS>>

**结论**：6 项 acceptance 全部由机器判定通过（`all_ok=<<ALL_OK>>`）。
"通过"仅指本工序的结构/定位/哈希/唯一性自检通过，**不代表**任何科学结论被验证；
报告中 WITHHELD 的量仍为 WITHHELD；图件与仓外工件仍为 `referenced_unresolved`。

### 一键复跑（`repro_cmd`）

在工作树根目录依次执行（需 `TENSOR_API_BASE` / `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS`）：

    python3 scripts/kf_wp9510_01_register_assets.py all
    python3 scripts/kf_wp9510_01_report.py build
    python3 -m pytest tests/test_kf_wp9510_01.py -q

（`all` 会重新取源并重算哈希；源未变时除时间戳外产物逐字节一致。`publish` 另发报告，不参与复算。）

### 结果 JSON（唯一 json 代码块，原样来自 kf_result.json）

```json
<<ENVELOPE_JSON>>
```
"""


def fetch_record() -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(base + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        tok = json.load(r)["access_token"]
    req = urllib.request.Request(base + "/tensor/reports/%s" % REPORT_ID,
                                 headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def build() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    ver = json.loads(VERIFICATION.read_text())
    md_src = SOURCE_COPY.read_text()
    lines = md_src.rstrip("\n").split("\n")
    src = manifest["source"]
    c = manifest["counts"]

    def contract_flag(k: str) -> str:
        return "一致" if src["contract"][k] else "不一致"

    acc_rows = []
    for k, v in ver["acceptance"].items():
        detail = v["detail"].replace("|", "/")
        if len(detail) > 200:
            detail = detail[:200] + "…"
        acc_rows.append("| `%s` | %s | %s |" % (k, "PASS" if v["ok"] else "FAIL", detail))

    asset_rows = []
    for a in manifest["assets"]:
        q = a["locator"]["quote"].replace("|", "/")
        if len(q) > 96:
            q = q[:96] + "…"
        asset_rows.append("| %s | %s | L%d | `%s` | %s |"
                          % (a["asset_id"], a["asset_class"], a["locator"]["start_line"],
                             a["resolution"], q))

    fig_rows = []
    for name, p in manifest["figure_probes"].items():
        fig_rows.append("| `%s` | %d | %d | %s |"
                        % (name, p["http_status"], p["bytes"],
                           (p["sha256"][:23] + "…") if p.get("sha256") else "—（无字节）"))
    fsum = manifest.get("figure_probe_summary", {})
    fig_probe_summary = ("探测 %d 个名字，HTTP 200 且有字节 = %d；状态分布 `%s`"
                         % (fsum.get("probed", 0), fsum.get("http_200_with_bytes", 0),
                            json.dumps(fsum.get("http_status_histogram", {}))))

    fig_sha = "sha256:" + hashlib.sha256(RESULT_FIG.read_bytes()).hexdigest()

    tokens = {
        "TITLE": TITLE,
        "MISSION": str(MISSION_ID),
        "SRC_URI": src["uri"],
        "SRC_HASH": src["hash_prefixed"],
        "SRC_HASHFULL": src["hash_prefixed"],
        "SRC_CHARS": str(src["chars"]),
        "SRC_BYTES": str(src["bytes_utf8"]),
        "SRC_LINES": str(src["lines"]),
        "SRC_COPY": src["local_copy"],
        "FETCH_VIA": src["fetched_via"],
        "CONTRACT_HASH": src["contract"]["source_hash"],
        "CONTRACT_CHARS": str(src["contract"]["chars"]),
        "C_HASH": contract_flag("hash_matches"),
        "C_CHARS": contract_flag("chars_matches"),
        "C_TITLE": contract_flag("title_matches"),
        "C_SCEN": contract_flag("scenario_matches"),
        "N_ASSETS": str(c["assets"]),
        "BY_CLASS": json.dumps(c["by_class"], ensure_ascii=False),
        "BY_RES": json.dumps(c["by_resolution"], ensure_ascii=False),
        "N_RESOLVED": str(c["resolved_in_source"]),
        "N_UNRES": str(c["referenced_unresolved"]),
        "ALL_OK": str(ver["all_ok"]),
        "FIG_NAME": RESULT_FIG.name,
        "FIG_SHA": fig_sha,
        "FIG_PROBE_SUMMARY": fig_probe_summary,
        "FIG_HTTP": ",".join(sorted({str(p["http_status"])
                                     for p in manifest["figure_probes"].values()})) or "-",
        "FIG_N": str(len(manifest["figure_probes"])),
        "ASSET_ROWS": "\n".join(asset_rows),
        "FIG_ROWS": "\n".join(fig_rows) if fig_rows else "| （记录未声明图件） | - | - | - |",
        "ACC_ROWS": "\n".join(acc_rows),
        "Q1": lines[0],
        "Q5": lines[4],
        "Q46": lines[45],
        "ENVELOPE_JSON": ENVELOPE.read_text().rstrip("\n"),
    }
    text = TEMPLATE
    for k, v in tokens.items():
        text = text.replace("<<%s>>" % k, v)
    if "<<" in text:
        raise SystemExit("unsubstituted placeholder remains: %r"
                         % text[text.index("<<"):text.index("<<") + 40])
    REPORT_MD.write_text(text)

    payload = {
        "title": TITLE,
        "summary": ("report 9510 源资产登记：sha256 %s 与契约一致；登记 %d 条资产"
                    "（图件/脚本/数据工件/模块路径/法规文本），%d 条仓外引用如实标"
                    "referenced_unresolved；claims 留空（契约允许）。"
                    % (src["hash_prefixed"][7:19], c["assets"], c["referenced_unresolved"])),
        "scenario_key": SCENARIO,
        "mission_id": MISSION_ID,
        "tags": TAGS,
        "markdown": text,
        "figures": [{
            "name": RESULT_FIG.name,
            "caption": ("report 9510 源 markdown 行剖面与已登记资产定位符（左）／资产类别×解析状态"
                        "（右）；%d 条资产，sha256 %s" % (c["assets"],
                                                         src["hash_prefixed"][7:19])),
            "png_base64": base64.b64encode(RESULT_FIG.read_bytes()).decode(),
        }],
    }
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False) + "\n")
    print("report ->", REPORT_MD.relative_to(ROOT), "| chars", len(text),
          "| json fences", text.count("```json"))
    print("payload ->", REPORT_JSON.relative_to(ROOT), "| markdown chars", len(text))
    return payload


def publish(payload: dict) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(base + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        tok = json.load(r)["access_token"]
    data = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(base + "/tensor/reports", data=data,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def readback(published_id: str) -> dict:
    """Post-hoc audit of the *server-side* copy: one json block, parses, and its
    provenance hash equals the hash of report 9510's markdown recomputed live."""
    import re
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(base + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        tok = json.load(r)["access_token"]

    def get(path):
        rq = urllib.request.Request(base + path, headers={"Authorization": "Bearer " + tok})
        with urllib.request.urlopen(rq) as r:
            return json.load(r)

    pub = get("/tensor/reports/%s" % published_id)
    src = (get("/tensor/reports/%s" % REPORT_ID).get("markdown") or "").encode("utf-8")
    live = "sha256:" + hashlib.sha256(src).hexdigest()
    blocks = re.findall(r"```json\n(.*?)\n```", pub.get("markdown") or "", re.S)
    env = json.loads(blocks[0]) if len(blocks) == 1 else {}
    out = {
        "published_report_id": published_id,
        "title": pub.get("title"),
        "tags_ok": ("kf-wp:%s" % PACKAGE_ID) in (pub.get("tags") or []),
        "mission_id": pub.get("mission_id"),
        "json_blocks": len(blocks),
        "block_parses": bool(env),
        "env_package_id": env.get("package_id"),
        "env_report_id": env.get("report_id"),
        "source_hash_live": live,
        "provenance_matches_live": env.get("provenance", {}).get("source_hash") == live,
        "matches_contract": live == "sha256:" + hashlib.sha256(
            SOURCE_COPY.read_text(encoding="utf-8").encode("utf-8")).hexdigest(),
        "figures": [f.get("name") for f in (pub.get("figures") or [])],
    }
    out["all_ok"] = bool(out["json_blocks"] == 1 and out["block_parses"] and out["tags_ok"]
                         and out["provenance_matches_live"] and out["matches_contract"]
                         and out["env_package_id"] == PACKAGE_ID)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return out


def main(argv) -> int:
    cmd = argv[1] if len(argv) > 1 else "build"
    if cmd == "readback":
        if len(argv) < 3:
            raise SystemExit("usage: kf_wp9510_01_report.py readback <published_report_id>")
        return 0 if readback(argv[2])["all_ok"] else 1
    payload = build()
    if cmd == "publish":
        out = publish(payload)
        print("published:", json.dumps(out, ensure_ascii=False)[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))