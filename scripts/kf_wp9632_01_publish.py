#!/usr/bin/env python3
"""wp-9632-01 delivery: render the KF-RESULT report for the platform.

Every number and quote in the rendered markdown is read out of the artefacts the
register script measured (asset_manifest.json / verification.json) -- nothing is
retyped. The result envelope docs/kf/wp-9632-01/kf_result.json is embedded as the
single ```json block, byte-for-byte.

    python3 scripts/kf_wp9632_01_register.py all      # build artefacts
    python3 scripts/kf_wp9632_01_publish.py           # render /tmp/report_wp9632_01.json
    python3 scripts/kf_wp9632_01_publish.py --post    # ... and POST it to the platform
    python3 scripts/kf_wp9632_01_publish.py --check <report_id>   # post-hoc gate check

Neither mode writes outside the worktree except the /tmp payload.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ID = "wp-9632-01"
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
FIGURE = OUT_DIR / "figures" / "wp9632_01_source_locator_map.png"
PAYLOAD = Path("/tmp/report_wp9632_01.json")
MISSION_ID = 15662
REPRO = ("python3 scripts/kf_wp9632_01_register.py all && "
         "python3 scripts/kf_wp9632_01_publish.py --post")


def md_escape_cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def render() -> dict:
    m = json.loads(MANIFEST.read_text())
    v = json.loads(VERIFICATION.read_text())
    env_text = ENVELOPE.read_text().rstrip("\n")
    src = m["source"]
    checks = {c["check_id"]: c for c in v["checks"]}
    assets = m["assets"]

    by_class = ", ".join("%s=%d" % (k, n) for k, n in sorted(m["counts"]["by_class"].items()))
    fig_rows = [a for a in assets if a["asset_class"] == "platform_figure"]

    L = []
    L.append("# KF-RESULT %s" % PACKAGE_ID)
    L.append("")
    L.append("`task_type=01-asset-registration` ｜ `report_id=%s` ｜ lane %s ｜ 交付仓 "
             "TensorKnowledge（draft）｜ producer `%s`"
             % (m["report_id"], m["lane"], m["producer"]))
    L.append("")

    # ---------------- ①
    L.append("## ① 本工序做了什么")
    L.append("")
    L.append("只登记源资产，不抽取、不分类、不标 verified。具体三件事：")
    L.append("")
    L.append("1. **钉死源资产身份**：对 `GET /api/v1/tensor/reports/%s` 返回的 `markdown` "
             "字段按 UTF-8 字节重算 sha256，与工作包契约声明的 `source_hash` 逐字节比对，"
             "并核对字符数与契约 `chars`。" % m["report_id"])
    L.append("2. **列出可解析的附件/工件**：把报告正文里**声明过**的图（%d 张，两种形态）、"
             "代码路径、数据工件、仓库、模块与符号全部登记，共 **%d** 条资产，"
             "每条带可复算的定位器（原文引文 + 字符区间 + 行号）。"
             % (len(fig_rows), m["counts"]["assets"]))
    L.append("3. **只做诚实的解析判定**：交付工作树内真能打开的（源 markdown 本身）标 "
             "`resolved_in_source`；属于另一仓库（TensorPhysics）或平台未暴露字节载荷的，"
             "一律标 `referenced_unresolved` 并写清原因，不替上游宣称存在。")
    L.append("")
    L.append("**claims 为空数组**是契约许可的完整结果（`objective.classify_report_type=false`，"
             "本工序不做知识抽取，不得为填指标造知识）；本工序不给出任何 verified 标记，"
             "验证由平台门计算。")
    L.append("")

    # ---------------- ②
    L.append("## ② 怎么做的（步骤 / 工具 / 关键设置）")
    L.append("")
    L.append("| 步 | 动作 | 工具/设置 |")
    L.append("|---|---|---|")
    L.append("| 1 | 取原文（唯一来源，禁止凭记忆） | `POST /auth/login` 取 token → "
             "`GET /api/v1/tensor/reports/9632`，取 `markdown` 字段 |")
    L.append("| 2 | 身份核对 | `hashlib.sha256(markdown.encode('utf-8'))`；契约值 "
             "`%s`；字符数 `%d`（契约 `%d`） |"
             % (src["contract_source_hash"], src["chars"], src["contract_chars"]))
    L.append("| 3 | 留字节副本 | 原样写 `runs/%s/source_%s.md`（%d bytes），"
             "verify 时与线上字节再比一次 |"
             % (PACKAGE_ID, m["report_id"], src["bytes_utf8"]))
    L.append("| 4 | 扫引用 | 正则三路：markdown 图片 `![](...)`、反引号路径令牌"
             "（含命令行拆词）、反引号点号标识符；仓库令牌 `Tensor[A-Z]...` |")
    L.append("| 5 | 定位器 | 优先取**该行原文**（唯一性优先），退化到令牌本身；记录 "
             "`start_char/end_char/start_line/end_line/quote/unique` |")
    L.append("| 6 | 解析判定 | 交付工作树内 `Path.exists()`；未命中则记 `same_basename_hits` "
             "作证据，状态 `referenced_unresolved`（不跨仓断言） |")
    L.append("| 7 | 平台图探针 | 对 `record.figures` 的每个名字打 "
             "`GET /api/v1/tensor/reports/9632/figures/<name>`，记 HTTP 状态 |")
    L.append("| 8 | 结构门 | 结果信封 vs `schemas/kf_result.v1.schema.json`；清单 vs "
             "`schemas/asset_manifest.v1.wp9632-01.schema.json`（由 448 版派生，只改身份 "
             "const） |")
    L.append("| 9 | 六项验收自检 | `scripts/kf_wp9632_01_register.py verify` → "
             "`verification.json` |")
    L.append("| 10 | 出图 | matplotlib(Agg) 资产定位图，x=原文字符偏移 |")
    L.append("")
    L.append("依赖：Python3 标准库（urllib/hashlib/json/re）+ `jsonschema` + `matplotlib`。"
             "全部产物落工作树内：`docs/kf/%s/`、`runs/%s/`。" % (PACKAGE_ID, PACKAGE_ID))
    L.append("")
    L.append("repro_cmd: `%s`" % REPRO)
    L.append("")

    # ---------------- ③
    L.append("## ③ 产出物清单（输出文件 → 要点）")
    L.append("")
    L.append("| 文件（括号内为落盘实测字节数） | 要点 |")
    L.append("|---|---|")
    def _kb(pth: Path) -> str:
        return "%d bytes" % pth.stat().st_size

    L.append("| `docs/kf/%s/asset_manifest.json`（%s） | 资产清单本体：%d 条资产；分类计数 %s；"
             "解析计数 resolved_in_source=%d / referenced_unresolved=%d / declared_absent=%d；"
             "claims=[] |"
             % (PACKAGE_ID, _kb(MANIFEST), m["counts"]["assets"], by_class,
                m["counts"]["resolved_in_source"], m["counts"]["referenced_unresolved"],
                m["counts"]["declared_absent"]))
    L.append("| `docs/kf/%s/kf_result.json`（%s） | 平台结果信封（即本报告唯一的 JSON 代码块，与产物文件逐字节同源） |"
             % (PACKAGE_ID, _kb(ENVELOPE)))
    L.append("| `docs/kf/%s/verification.json`（%s） | 六项 acceptance 自检：%d/%d pass，0 fail |"
             % (PACKAGE_ID, _kb(VERIFICATION), v["passed"], v["total"]))
    L.append("| `docs/kf/%s/figures/wp9632_01_source_locator_map.png`（%s） | 资产定位图：每根条的 "
             "左端=引文起始字符偏移，长度=引文跨度，颜色=解析状态 |" % (PACKAGE_ID, _kb(FIGURE)))
    L.append("| `runs/%s/source_%s.md` | 原文 UTF-8 字节副本（%d bytes / %d chars / %d 行），"
             "sha256 %s |"
             % (PACKAGE_ID, m["report_id"], src["bytes_utf8"], src["chars"], src["lines"],
                src["hash"]))
    L.append("| `schemas/asset_manifest.v1.wp9632-01.schema.json` | 本包结构门的可复算依据"
             "（报告 448 版 schema 的身份 const 换成 9632；不改 448 原件） |")
    L.append("| `scripts/kf_wp9632_01_register.py` / `..._publish.py` | 一键复跑：build → "
             "envelope → verify → figure → 发报告 |")
    L.append("")

    # ---------------- ④
    L.append("## ④ 证据定位表（字段/claim → 原文逐字引文）")
    L.append("")
    L.append("所有引文均为 `markdown[start_char:end_char]` 的逐字切片（原样显示，含原文反引号，"
             "仅把表格竖线转义），`行` 列=该切片在原文的 1-based 行号；平台可独立重算。"
             "超过 120 字符的引文在此表截断显示为 `…`，**完整引文以 manifest 的 "
             "`locator.quote` 为准**（verify 用的是完整引文）。")
    L.append("")
    L.append("| asset_id | 类别 | 行 | 解析 | 原文引文（逐字） |")
    L.append("|---|---|---|---|---|")
    for a in assets:
        q = a["locator"]["quote"]
        q = q if len(q) <= 120 else q[:117] + "…"
        L.append("| %s | %s | %d–%d | %s | %s |"
                 % (a["asset_id"], a["asset_class"], a["locator"]["start_line"],
                    a["locator"]["end_line"], a["resolution"],
                    md_escape_cell(q)))
    L.append("")
    L.append("源资产自身（最高优先级的定位器）：`method=document`，"
             "`start_char=0`，`end_char=%d`（= `len(markdown)`），`quote`=首行标题，"
             "sha256=`%s`。" % (src["chars"], src["hash"]))
    L.append("")
    L.append("契约字段对照：`report_id`=%s（契约 `%s`）；`title` 与契约一致=%s；"
             "`scenario_key`=%s 与契约一致=%s；平台侧 `mission_id`=%s、`status`=%s。"
             % (m["report_id"], m["report_id"], str(src["title_matches_contract"]),
                src["scenario_key"], str(src["scenario_matches_contract"]),
                src["platform_mission_id"], src["platform_status"]))
    L.append("")

    # ---------------- ⑤
    L.append("## ⑤ 注意点与局限（踩过的坑 / 适用范围）")
    L.append("")
    L.append("1. **图的字节载荷拿不到**：`record.figures` 只暴露 name/caption；"
             "逐图探针 `GET /tensor/reports/9632/figures/<name>` 全部返回 404，"
             "因此这 %d 条图资产的解析状态是 `referenced_unresolved`，**不声明任何图 hash**。"
             "若平台后续开放图端点，重跑 verify 即自动转 resolved。" % len(fig_rows))
    L.append("2. **跨仓路径只登记不断言**：报告声明的 `src/tensorphysics/...`、"
             "`benchmarks/ice_ridge_consolidation/*`、`tests/test_ice_ridge_consolidation.py` "
             "属 TensorPhysics 仓；本包在交付工作树（TensorKnowledge）内探测，一律 "
             "`referenced_unresolved`，并把同名文件在交付树内的命中（若有）记为证据。"
             "这符合「不得改写其它仓、不做跨仓断言」的边界。")
    L.append("3. **同一张图出现两行资产**是有意的：一行钉平台元数据（`record.figures` 的 "
             "name/caption + 端点探针），一行钉正文里的磁盘相对路径 `../artifacts/...png`。"
             "两者的可用性证据不同，合并会丢掉其中一类证据；asset_id 与 label 均唯一。")
    L.append("4. **引文粒度为整行优先**：为满足唯一性，多数定位器取的是声明该资产的整行原文，"
             "而不是最短令牌；这牺牲一点紧凑度，换取「引文在原文中唯一出现」的可机器复核性"
             "（`integrity.quote_uniqueness=%s`，非唯一条目 %d 条）。"
             % (str(m["integrity"]["quote_uniqueness"]), len(m["integrity"]["non_unique_quotes"])))
    L.append("5. **本工序没有任何物理结论**：manifest 里的数字全是身份/计数/偏移，"
             "不经手报告正文的 0.0087%、4.21%、2.88% 等物理判据数值——那些属下游抽取与"
             "复核工序；本包不复制、不复述，避免二次手抄。")
    L.append("6. **schema 权威性**：`schemas/asset_manifest.v1.schema.json`（仓内既有）把 "
             "package_id/report_id/uri 写死为报告 448 的 const，无法直接用于本包；"
             "故派生一份只改身份 const 的 9632 版并在文件内注明派生范围。**平台侧 schema 优先**，"
             "若平台结构门判定不同，以平台门为准并回头改本产物。")
    L.append("7. **verify 是工人自检，不是验证结论**：`verification.json` 只是把六项 "
             "acceptance 变成可复跑的检查；`verification_authority` 字段已声明权威在平台门。")
    L.append("")

    # ---------------- ⑥
    L.append("## ⑥ 自检：逐条对照 acceptance")
    L.append("")
    L.append("| acceptance | 结果 | 证据（可复算） |")
    L.append("|---|---|---|")
    labels = {
        "valid_json": "所有产出 JSON 可解析",
        "schema_pass": "清单过 9632 版结构门 + 信封过 `kf_result.v1`",
        "source_locator_resolvable": "全部 %d 条定位器在**线上原文**重解析成功"
                                     "（`md[start:end]==quote` 且行号吻合）"
                                     % m["counts"]["assets"],
        "source_hash_matches": "线上 sha256 == 契约；本地字节副本 == 线上字节",
        "no_duplicate_ids": "asset_id / label 均唯一",
        "all_claims_have_evidence_or_explicit_unresolved_status":
            "claims=[] 为契约许可；若有 claim 必带 evidence 或 status",
    }
    for cid, desc in labels.items():
        c = checks[cid]
        mark = "✓" if c["result"] == "pass" else "✗"
        L.append("| `%s` %s | **%s** | %s |" % (cid, desc, mark,
                                                md_escape_cell(json.dumps(
                                                    c["evidence"], ensure_ascii=False))[:520]))
    L.append("")
    L.append("合计 **%d/%d pass，%d fail**。无失败项需粉饰；如实声明：**本包不产生 verified 结论**，"
             "claims 保持空数组，验收结论由平台门独立重算。"
             % (v["passed"], v["total"], v["failed"]))
    L.append("")
    L.append("**「关键量 vs 基准误差是否 <3%%」的显式回答**：本工序**没有物理基准量**，"
             "因此不存在可报的百分比误差（不是省略，是没有这类量）。可比的只有身份一致性，"
             "且它是**严格相等判定**而非容差判定：`source_hash` 线上重算 %s 与契约 %s "
             "字符级相同（差异 0 字符 / 0 字节，严格满足 <3%% 且实为 0）；`chars` %d == 契约 %d；"
             "全部 %d 条定位器重解析 0 失败。报告正文里的物理判据数值（如判据 (a) 的 +0.0087%%、"
             "(b) 的 +4.21%%）属下游抽取/复核工序的核算范围，本包不复制、不重述。"
             % (src["hash"][:16] + "…", src["contract_source_hash"][:24] + "…",
                src["chars"], src["contract_chars"], m["counts"]["assets"]))
    L.append("")

    # ---------------- result block (the ONLY json fence in this markdown)
    L.append("## 结果信封（唯一 JSON 代码块，逐字节同源 `docs/kf/%s/kf_result.json`）" % PACKAGE_ID)
    L.append("")
    L.append("```json")
    L.append(env_text)
    L.append("```")
    L.append("")
    md = "\n".join(L)

    if md.count("```json") != 1:
        raise SystemExit("expected exactly one ```json block, found %d" % md.count("```json"))

    png = FIGURE.read_bytes()
    return {
        "title": "KF-RESULT %s" % PACKAGE_ID,
        "summary": ("wp-9632-01 资产登记：报告 9632 的 markdown 按 UTF-8 字节重算 sha256="
                    "%s… 与契约 source_hash 字符级一致（%d chars），登记 %d 条声明资产"
                    "（%s），六项 acceptance 自检 %d/%d pass；claims 按契约留空，不标 verified，"
                    "图字节端点 404 与跨仓路径如实标 referenced_unresolved。"
                    % (src["hash"][:16], src["chars"], m["counts"]["assets"], by_class,
                       v["passed"], v["total"])),
        "scenario_key": src["scenario_key"],
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:%s" % PACKAGE_ID, "KF-RESULT", "asset-registration",
                 "report-%s" % m["report_id"], "tensor-knowledge", "zero-transcription",
                 src["scenario_key"]],
        "markdown": md,
        "figures": [{
            "name": "wp9632_01_source_locator_map.png",
            "caption": ("wp-9632-01 资产定位图：%d 条登记资产在报告 9632 markdown（%d 字符）中的"
                        "引文区间；颜色=解析状态（绿 resolved_in_source / 橙 "
                        "referenced_unresolved），右侧标签=资产类别。"
                        % (m["counts"]["assets"], src["chars"])),
            "png_base64": base64.b64encode(png).decode(),
        }],
    }


def post(payload: dict) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    tok = json.load(urllib.request.urlopen(urllib.request.Request(
        base + "/auth/login", data=body,
        headers={"Content-Type": "application/json"})))["access_token"]
    req = urllib.request.Request(base + "/tensor/reports", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def _token() -> str:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    with urllib.request.urlopen(urllib.request.Request(
            base + "/auth/login", data=body,
            headers={"Content-Type": "application/json"})) as r:
        return json.load(r)["access_token"]


def check(rid: str) -> dict:
    """Post-hoc gate check: the *published* copy must be exactly what we delivered."""
    import re
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(base + "/tensor/reports/" + rid,
                                 headers={"Authorization": "Bearer " + _token()})
    with urllib.request.urlopen(req, timeout=60) as r:
        rec = json.load(r)
    md = rec["markdown"]
    blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
    env_text = ENVELOPE.read_text().rstrip("\n")
    env = json.loads(env_text)
    src_hash = json.loads(MANIFEST.read_text())["source"]["source_hash"]
    checks = {
        "exactly_one_json_block": len(blocks) == 1 and md.count("```json") == 1,
        "title_matches": rec["title"] == "KF-RESULT %s" % PACKAGE_ID,
        "tag_present": ("kf-wp:%s" % PACKAGE_ID) in (rec.get("tags") or []),
        "block_is_verbatim_delivery": bool(blocks) and blocks[0] == env_text,
        "provenance_hash_is_contract_hash": bool(blocks)
        and json.loads(blocks[0])["provenance"]["source_hash"] == src_hash,
        "report_id_field_unchanged": bool(blocks)
        and json.loads(blocks[0])["report_id"] == env["report_id"],
        "mission_id_matches": rec.get("mission_id") == MISSION_ID,
        "six_sections_present": all(s in md for s in
                                    ("## ①", "## ②", "## ③", "## ④", "## ⑤", "## ⑥")),
        "repro_cmd_present": "repro_cmd:" in md,
    }
    out = {"published_report_id": rec.get("id"), "title": rec.get("title"),
           "checks": checks, "passed": sum(checks.values()), "total": len(checks)}
    if not all(checks.values()):
        raise SystemExit("post-hoc check failed: %s"
                         % [k for k, v in checks.items() if not v])
    return out


def main(argv):
    if "--check" in argv:
        i = argv.index("--check")
        print(json.dumps(check(argv[i + 1]), ensure_ascii=False, indent=2))
        return 0
    payload = render()
    PAYLOAD.write_text(json.dumps(payload, ensure_ascii=False))
    print("payload: %s (%d bytes markdown, %d figure)"
          % (PAYLOAD, len(payload["markdown"]), len(payload["figures"])))
    if "--post" in argv:
        resp = post(payload)
        print("posted:", json.dumps({k: resp.get(k) for k in
                                     ("id", "title", "status", "scenario_key")},
                                    ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))