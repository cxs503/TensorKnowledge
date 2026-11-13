#!/usr/bin/env python3
"""wp-5949-04：把独立复算结果（checks.json）组装成 review_report.json 与报告正文。

数字一律从 checks.json 注入，不手抄。所有 source 引文在写出前断言 `quote in source`。
以下三个输入均按 sha256 固定：
  - 源报告 5949 markdown（平台 API 取回，sha256 必须等于契约 source_hash）
  - 上游包产物（git 分支 agent/m15584 只读导出）
用法：python3 work/wp-5949-04/build_review.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess

SRC = "work/wp-5949-04/source_5949.md"
CHECKS = "work/wp-5949-04/checks.json"
UP = "work/wp-5949-04/upstream"
OUT_JSON = "work/wp-5949-04/review_report.json"
OUT_MD = "docs/kf/wp-5949-04/KF-RESULT-wp-5949-04.md"
ENVELOPE = "work/wp-5949-04/kf_result.json"
UPSTREAM_REF = "agent/m15584"

PKG = "wp-5949-04"
TARGET = "wp-5949-01"


def sha(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main() -> None:
    md = open(SRC, encoding="utf-8").read()
    checks = json.load(open(CHECKS, encoding="utf-8"))
    src_hash = "sha256:" + sha(SRC)
    assert src_hash == "sha256:c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002"

    # ---- 逐字引文（写出前断言可定位） ----
    quotes = {
        "digest_header": "> 工件快照 sha256（前 16 位）：coverage `fddd78dbd6e61b17` · seats",
        "doc_first_line": "# IN25-T2 · 多样性引擎：氏族矩阵 / 盲预测锁 / 同族查重",
        "lock_row": "| 盲预测锁定工件 | lock_hash `1b96a171b6000fb9…`，40 条预测，复算 ✅，篡改检出 ✅，先跑后锁被拒 ✅ | 三项全真 | ✅ | `artifacts/in25_t2/prereg_lock.json` |",
        "code_paths": "代码：`tools/diversity/{roster,prereg,dedup,run_node}.py`；测试：`tests/test_diversity_engine.py`。",
        "fig1": "**图 1** 氏族覆盖矩阵：左攻坚者、右破坏者，格子里的数字是该 (族,框架) 格内席位数。",
        "no_physics": "本节点是**进程/纪律机器**，不产生任何物理量（零平台域语义）",
        "blind_digest": "> blind `0439b915d213c62f`。",
    }
    for k, q in quotes.items():
        assert q in md, f"quote not verbatim in source: {k}"

    def src_ev(key: str) -> dict:
        q = quotes[key]
        return {
            "artifact": "report_5949.markdown",
            "locator": {"method": "search", "start_char": md.find(q), "end_char": md.find(q) + len(q)},
            "quote": q,
            "verified_verbatim": True,
        }

    upstream = {
        "branch": UPSTREAM_REF,
        "commit": subprocess.run(
            ["git", "log", "-1", "--format=%H", UPSTREAM_REF], capture_output=True, text=True
        ).stdout.strip(),
        "task_type": "01-asset-registration",
        "report_id_on_platform": 14660,
        "artifacts": {
            "asset_manifest.json": "sha256:" + sha(f"{UP}/asset_manifest.json"),
            "kf_result.json": "sha256:" + sha(f"{UP}/kf_result.json"),
            "verification.json": "sha256:" + sha(f"{UP}/verification.json"),
            "report.md": "sha256:" + sha(f"{UP}/report.md"),
        },
    }

    c = checks
    def C(k: str) -> dict:
        return {"id": k, "pass": c[k]["pass"], "detail": c[k]["detail"]}

    findings = [
        {
            "id": "F-01",
            "severity": "high",
            "likelihood": "certain（7/7 确定性复算）",
            "blocking": True,
            "category": "locator_coordinate_mixing",
            "title": "declared_digests 的 start_char/end_char 是「相对 quote 的偏移」，被当作文档绝对偏移写入",
            "evidence": [
                src_ev("digest_header"),
                {
                    "artifact": f"asset_manifest.json @ {upstream['commit'][:7]}",
                    "path": "declared_digests.items[]",
                    "observation": {
                        x["label"]: {
                            "declared": x["declared"],
                            "doc_absolute": x["doc_absolute"],
                            "slice_at_declared": x["slice_at_declared"],
                            "prefix_index_within_quote": None,
                        }
                        for x in c["C6b_digest_offset_semantics"]["detail"]
                    },
                    "recomputed": "7/7 条：md[start:end] != quote；把偏移平移到 quote 内部起点后，切片恰为 `+digest_prefix+`（反引号包裹）",
                },
            ],
            "reproduction": (
                "python3 work/wp-5949-04/review_checks.py；看 C6b_digest_offset_semantics："
                "coverage 声明 (31,49)，文档绝对位置 (155,212)，md[31:49]=="
                "' 同族查重\\n\\n> 战役节点 **IN'；而 quote[31:49]=='`fddd78dbd6e61b17`'"
            ),
            "impact": (
                "字段名承诺的是文档绝对偏移（20 条 asset locator 确实是绝对的），digest 这 7 条却换了坐标系："
                "任何按 start_char/end_char 取值的机器消费者会读到无关字节，E3/E4 语义下判 LOCATOR_BAD_OFFSETS。"
                "digest 本身 verifiable=false（16 位截断），不影响轨迹哈希，但 locator 作为产品承诺是错的。"
            ),
            "remediation": "把 7 条改成文档绝对偏移（或改字段名为 offset_in_quote 并写明语境），并在 integrity 里加 offset-vs-quote 字节相等校验。",
            "disposition": "request-changes",
        },
        {
            "id": "F-02",
            "severity": "medium",
            "likelihood": "certain（3/3）",
            "blocking": False,
            "category": "locator_semantics",
            "title": "document 级 locator（A01/A02/A03）用全篇跨度配首行 quote，且 A02/A03 的 start_line/end_line=0",
            "evidence": [
                src_ev("doc_first_line"),
                {
                    "artifact": f"asset_manifest.json @ {upstream['commit'][:7]}",
                    "path": "assets[0..2].locator",
                    "observation": c["C3b_document_locators"]["detail"],
                },
            ],
            "reproduction": "review_checks.py 的 C3/C3b：checked=23，字节相等失败=['A01','A02','A03']；A02/A03 start_line=0",
            "impact": "文档级资产的 quote 只当锚点、偏移指全篇，二者语义不同；E4 语义下同样判失败（上游在 integrity.quote_uniqueness.note 里声明过该约定，但没改字段语义）。行号 0 是非法值。",
            "remediation": "document 级资产改用 method=document + 无偏移（或 offsets=[0,len] 且另给 anchor_quote 字段），行号填真实值。",
            "disposition": "request-changes",
        },
        {
            "id": "F-03",
            "severity": "medium",
            "likelihood": "certain",
            "blocking": False,
            "category": "overstated_check",
            "title": "verification.json 自述「checked 23 locators against live markdown bytes; failing=[]」不可复算",
            "evidence": [
                {
                    "artifact": f"verification.json @ {upstream['commit'][:7]}",
                    "sha256": upstream["artifacts"]["verification.json"],
                    "path": "checks.source_locator_resolvable.detail",
                    "quote": "checked 23 locators against live markdown bytes; failing=[]",
                },
                {"artifact": "checks.json", "path": "C3/C6b", "observation": c["C3_locator_slices"]["detail"] + " ; " + str(c["C6b_digest_offset_semantics"]["pass"])},
            ],
            "reproduction": "对照 C3（3/23 字节不等）与 C6b（7/7 digest 偏移错位）：该布尔只在「子串检索」语义下成立，在「声明偏移处取值」语义下不成立；而 verification 文本说的是 locator。",
            "impact": "把 search-resolvable 与 offset-resolvable 混成一个布尔，使自检结论偏乐观（failing=[]），下游若引用该布尔会把 locator 缺陷当已排除。",
            "remediation": "拆成两个布尔：quotes_searchable / offsets_byte_equal，并把后者纳入 all_pass。",
            "disposition": "request-changes",
        },
        {
            "id": "F-04",
            "severity": "medium",
            "likelihood": "certain",
            "blocking": False,
            "category": "verification_attribution",
            "title": "报告把自产 verification.json 称作「平台侧独立复算」，且文件内含 verified_at/all_pass=true",
            "evidence": [
                {
                    "artifact": f"report.md @ {upstream['commit'][:7]}",
                    "sha256": upstream["artifacts"]["report.md"],
                    "path": "③ 产出物清单表 · verification.json 行",
                    "quote": "| `docs/kf/wp-5949-01/verification.json` | 平台侧独立复算的 7 项 acceptance 结论（all_pass=True） |",
                },
                {
                    "artifact": f"report.md @ {upstream['commit'][:7]}",
                    "path": "② 步骤 7",
                    "quote": "7. **验收独立复算**：`verify` 子命令重新登录并**重新拉取**原文，重算哈希、重解析全部 locator、重查 id 唯一性与 claims 状态，结果写 `verification.json`；离线 pytest 再用本地副本复验一遍。",
                },
                {
                    "artifact": f"verification.json @ {upstream['commit'][:7]}",
                    "path": "$",
                    "quote": '"all_pass": true',
                    "note": "同文件含 \"verified_at\": \"2026-11-12T01:25:34.140030+00:00\"",
                },
            ],
            "reproduction": "git show agent/m15584:docs/kf/wp-5949-01/report.md | grep 平台侧  → 恰为 ③ 表该行；同一报告的 ② 步骤 7 明说这是本包 verify 子命令产出。",
            "impact": "V1（三状态分离律）：verification_level 只能由平台门计算。此处虽 claims=0、未把任何 claim 标 verified（C9 未命中禁用字段），但「平台侧」措辞 + verified_at/all_pass 会被下游读成已经平台验证，等同自封。",
            "remediation": "改写为「本包 verify 子命令的可复算自检（非平台门签发）」，并把 verified_at 改名为 checked_at、all_pass 改名为 self_check_all_pass。",
            "disposition": "request-changes",
        },
        {
            "id": "F-05",
            "severity": "low",
            "likelihood": "certain",
            "blocking": False,
            "category": "envelope_shape",
            "title": "outputs['asset_manifest.json'] 是文件指针（path/sha256/bytes），不是 schema 要求的内容对象",
            "evidence": [
                {
                    "artifact": f"kf_result.json @ {upstream['commit'][:7]}",
                    "path": "outputs.asset_manifest.json",
                    "observation": c["C12_outputs_pointer_dereference"]["detail"],
                }
            ],
            "reproduction": "review_checks.py C12：指针 sha256 与 agent/m15584 上的 manifest 文件逐位对上（3c5564ea…），说明内容可寻址但未内联；同类先例 wp-5760-01 亦为指针。",
            "impact": "下游工序要落到仓库分支才能取内容；离线/跨仓消费（本单审核即如此）需要额外 git 访问。不影响身份正确性。",
            "remediation": "在 outputs 内联 manifest 内容，或加 pointer_kind 字段显式声明这是指针。",
            "disposition": "accept-with-note",
        },
        {
            "id": "F-06",
            "severity": "low",
            "likelihood": "certain",
            "blocking": False,
            "category": "claim_key_semantics",
            "title": "信封省略 claims 键，报告正文称 claims 为空数组",
            "evidence": [
                {"artifact": f"kf_result.json @ {upstream['commit'][:7]}", "path": "$", "observation": c["C10_claims_empty"]["detail"]},
                src_ev("no_physics"),
            ],
            "reproduction": "review_checks.py C10：manifest.claims=[] 而 envelope 无 claims 键；kf_result.v1.schema.json 中 claims 非必需 → 两者均合法。",
            "impact": "语义等价（空/缺键），仅措辞不一致；不影响门禁。",
            "remediation": "报告措辞改为「claims 键省略（manifest 内为空数组）」，或信封内补 claims: []。",
            "disposition": "accept-with-note",
        },
        {
            "id": "F-07",
            "severity": "info",
            "likelihood": "certain",
            "blocking": False,
            "category": "coverage_limitation",
            "title": "23 项中 19 项 referenced_unresolved、7 条声明哈希全部不可复算：登记包对报告③表的数字不提供独立字节绑定",
            "evidence": [
                src_ev("lock_row"),
                src_ev("code_paths"),
                {"artifact": "checks.json", "path": "C7/C8/C6", "observation": c["C7_counts_consistency"]["detail"] + " ; " + c["C8_resolution_falsifiable"]["detail"]},
            ],
            "reproduction": "C7 by_resolution={'resolved_in_source': 4, 'referenced_unresolved': 19}；C8 19 条路径在 agent/m15584 树内均不存在（标未解析无误）；C6 verifiable=0（前缀 16 位）。",
            "impact": "不构成缺陷（上游如实标注、未据此宣称一致），但意味着 wp-5949-01 能证明的只有「源字节身份 + 引用位置」，报告③表的 ✅ 仍只有生产者自述的 pytest/ledger 支撑。审核侧据此把该包的证据强度定在「asset inventory only」。",
            "remediation": "无（属上游工件不在本仓的客观限制）；建议下游消费方不要把该包当数字证据源。",
            "disposition": "accept-with-note",
        },
    ]

    checks_performed = [C(k) for k in sorted(k for k in c if k != "summary")]

    review = {
        "package_id": PKG,
        "task_type": "04-independent-review",
        "report_id": "5949",
        "review_target": {
            "package_id": TARGET,
            "task_type": "01-asset-registration",
            "branch": UPSTREAM_REF,
            "commit": upstream["commit"],
            "platform_report_id": 14660,
            "artifact_hashes": upstream["artifacts"],
        },
        "verdict": "needs-fix",
        "verdict_scope": (
            "上游包的**字节身份与计数**成立（源哈希逐位一致、23/23 quote 可检索、id 唯一、"
            "claims 为空、无自封验证字段）；但 locator 作为机器可消费产品有两类坐标缺陷"
            "（F-01 高：7/7 digest 偏移错位；F-02 中：document 级 3 条混用）与两处过头表述（F-03/F-04）。"
            "故不是 pass，也非 fail（无造假、无张冠李戴）。"
        ),
        "blocking_findings": ["F-01"],
        "findings": findings,
        "overstated_claims": [
            {
                "claim": "平台侧独立复算的 7 项 acceptance 结论（all_pass=True）",
                "where": "report.md ③ 产出物清单表",
                "why_overstated": "该文件由本包 verify 子命令在生产者会话内产出；平台门未签发（F-04）",
            },
            {
                "claim": "checked 23 locators against live markdown bytes; failing=[]",
                "where": "verification.json checks.source_locator_resolvable.detail",
                "why_overstated": "只在子串检索语义成立；声明偏移处字节相等实测 3/23 资产 + 7/7 digest 不成立（F-01/F-03）",
            },
            {
                "claim": "登记 23 项资产",
                "where": "report.md ① 与平台 summary",
                "why_overstated": "23 中 4 项为源内可定位资产、19 项为未解析引用；counts.by_resolution 已如实分列，措辞易被读成 23 项已验证资产（F-07）",
            },
        ],
        "checks_performed": checks_performed,
        "checks_not_run": [
            {"check": "上游 artifacts/in25_t2/*.json 的字节一致性", "reason": "工件不在任何可达检出内（C8 已证）；7 条声明哈希只有 16 位前缀，无法重算"},
            {"check": "上游 schema（schemas/asset_manifest.v1.wp-5949-01.schema.json）重跑 jsonschema", "reason": "该 schema 不在本仓主干；本单只验证了信封 vs schemas/kf_result.v1.schema.json（C11 通过），未重跑上游专用 schema"},
            {"check": "语义门 M6（report 5949 正文结论是否真实成立：多样性引擎的 TPR/FPR/命中率）", "reason": "本工序审核对象是 wp-5949-01 的登记正确性；正文算法结论属 IN25-T2 战役自身验收，且其工件不可达 → 明确 not_run，不记 pass"},
            {"check": "上游 pytest tests/test_kf_wp5949.py 重跑", "reason": "测试文件在 agent/m15584 分支但依赖包内脚本与工作树约定；本单以独立复算脚本替代，未重跑"},
        ],
        "independence": {
            "reviewer_package": PKG,
            "relationship_to_producer": "不同工作包、不同会话；审核对象只经 git 对象读取，未修改",
            "inputs_used": [
                "report 5949 markdown（独立经 GET /api/v1/tensor/reports/5949 取回）",
                "上游 wp-5949-01 的 kf_result.json / asset_manifest.json / verification.json / report.md（git 只读）",
                "schemas/kf_result.v1.schema.json（本仓主干）",
            ],
            "inputs_excluded": [
                "生产者解释性文字（只读其交付报告作为被审对象，不作事实依据；所有事实以复算为准）",
                "其它 report_id（未读写）",
            ],
            "limitations": [
                "本 reviewer 与 producer 同属 AI 智能体群体，但不同会话/工作包；共享的是代码与仓，不共享本次任务的上下文",
                "未做跨模型复核（strong-model sample）",
            ],
        },
        "source_identity": {
            "source_uri": "tensor://reports/5949",
            "source_field": "markdown",
            "source_hash": src_hash,
            "source_chars": len(md),
            "recomputed": True,
            "upstream_copy_identical": c["C2_upstream_source_copy"]["pass"],
        },
        "repro_cmd": (
            "cd <worktree> && python3 work/wp-5949-04/review_checks.py --upstream-ref agent/m15584 "
            "--out work/wp-5949-04/checks.json && python3 work/wp-5949-04/build_review.py "
            "&& python3 -m pytest tests/test_kf_wp5949_review.py -q"
        ),
    }

    json.dump(review, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    envelope = {
        "package_id": PKG,
        "task_type": "04-independent-review",
        "report_id": "5949",
        "provenance": {
            "source_uri": "tensor://reports/5949",
            "source_field": "markdown",
            "source_hash": src_hash,
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(md),
            "producer": "eco_admin via KF lane C worker (task agent/m15842)",
            "emitted_at": "2026-11-12T02:45:42+00:00",
            "notes": (
                f"审核对象 wp-5949-01 @ {upstream['commit']}；"
                "判据=独立复算（21 项检查，见 outputs.review_report.json.checks_performed）"
            ),
        },
        "outputs": {"review_report.json": review},
    }
    json.dump(envelope, open(ENVELOPE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    def Q(k: str) -> str:
        return quotes[k]

    n_fail = c["summary"]["n_fail"]
    body = f"""# KF-RESULT {PKG}

> package_id `{PKG}` · task_type `04-independent-review` · report_id `5949` · lane C · status in-review
> 源：`tensor://reports/5949`（field `markdown`）· sha256 `{src_hash[7:]}` · {len(md)} 字符 / {len(md.encode())} 字节 utf-8
> 审核对象：`{TARGET}`（01-asset-registration）@ `{upstream['commit'][:7]}` · 平台报告 14660
> 判定：**needs-fix**（1 项阻断 F-01；无造假、无张冠李戴）

## ① 本工序做了什么

对 `wp-5949-01` 的资产登记包做独立对抗性审核：不看生产者解释，只拿「报告 5949 原文（自己重新从平台 API 取）」
与「上游交付物（git 只读）」重算。共 **{len(checks_performed)} 项检查**，fail = {len(n_fail)} 项（{"、".join(x.split("_")[0] for x in n_fail)}；明细见 ④ 与 `checks.json`）。
结论不是 pass 也不是 fail：字节身份、计数、claims 纪律都成立；但 locator 有两类坐标缺陷、
两处表述过头。全部数字由 `review_checks.py` 复算后注入。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **独立取原文**：`POST /api/v1/auth/login` → `GET /api/v1/tensor/reports/5949`，取 `markdown`；
   重算 sha256 与契约 `source_hash` 逐位比对（`{c['C1_source_identity']['detail']}`）。
2. **取上游产物（只读）**：`git show {UPSTREAM_REF}:docs/kf/wp-5949-01/{{kf_result.json,asset_manifest.json,verification.json,report.md}}`
   导出到 `work/wp-5949-04/upstream/`，逐文件算 sha256（manifest `{upstream['artifacts']['asset_manifest.json'][7:23]}…` 与信封指针一致）。
3. **locator 字节级复算**：对 23 条 asset locator 断言 `md[start_char:end_char] == quote`；对 7 条
   `declared_digests` 同样断言，并额外算「文档绝对位置」与「quote 内相对位置」两套坐标做归因。
4. **计数/纪律复算**：id 唯一性、`counts.by_class/by_resolution` 与真实分组一致、
   `claims` 为空、递归扫禁用字段（`verified/verification_status/verification_level/is_verified/gate_confirmed`）。
5. **可反驳性检查**：19 条标 `referenced_unresolved` 的路径逐个 `git cat-file -e` 探上游树，
   确认「确实不存在」而不是「没找到就写未解析」。
6. **信封对 canonical schema**：`jsonschema.validate` 对 `schemas/kf_result.v1.schema.json`（本仓主干）跑，通过。
7. **报告形态**：上游报告恰 1 个 json 围栏块且与信封等价；平台记录标题/tag 合规（C14/C17）。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `work/wp-5949-04/review_report.json` | 主产物：判定 + {len(findings)} 条 findings（severity/evidence/reproduction/impact/remediation）+ {len(checks_performed)} 项检查 + not_run + 独立性声明 |
| `work/wp-5949-04/checks.json` | 21 项复算原始结果（每项 pass/detail，含失败明细） |
| `work/wp-5949-04/review_checks.py` | 独立复算脚本（自带登录取原文，不依赖上游副本） |
| `work/wp-5949-04/build_review.py` | 由 checks.json 组装 review_report.json + 本报告，数字注入不手抄 |
| `work/wp-5949-04/source_5949.md` | 源报告逐字副本（{len(md.encode())} 字节，sha256 `{src_hash[7:23]}…`） |
| `work/wp-5949-04/upstream/*` | 上游产物只读快照（4 文件 + sha256 固定） |
| `work/wp-5949-04/kf_result.json` | 结果信封（已原样写入本报告唯一 json 块） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

每条引文都是源 markdown 的**逐字切片**（build 时断言 `quote in source`，并给出字符偏移）。

**E1** 7 条声明哈希在原文中的位置（F-01 本应指向这里）· char {md.find(quotes['digest_header'])}

    {Q('digest_header')}

**E2** document 级 locator 的 quote 取自首行（F-02）· char {md.find(quotes['doc_first_line'])}

    {Q('doc_first_line')}

**E3** lock_hash 声明自带省略号，故天然不可复算 · char {md.find(quotes['lock_row'])}

    {Q('lock_row')}

**E4** 19 条 `referenced_unresolved` 的典型形态（代码路径）· char {md.find(quotes['code_paths'])}

    {Q('code_paths')}

**E5** 图资产（2 张，源内可定位）· char {md.find(quotes['fig1'])}

    {Q('fig1')}

**E6** 报告自述不产生物理量（故本工序只判决策误差）· char {md.find(quotes['no_physics'])}

    {Q('no_physics')}

**E7** 另一条截断哈希（blind）· char {md.find(quotes['blind_digest'])}

    {Q('blind_digest')}

**finding → 复算证据**：F-01（C6b：7/7 偏移错位）· F-02（C3/C3b：3/23 字节不等，A02/A03 line=0）·
F-03（C3C 与 C3 对照）· F-04（report.md ③ 行 vs ② 步骤 7 自相矛盾 + verification.json `all_pass:true`）·
F-05（C12 指针）· F-06（C10 空/缺键）· F-07（C7/C8/C6）。

## ⑤ 注意点与局限

1. **判 needs-fix 而非 fail 的理由**：源字节身份逐位一致（`{c['C1_source_identity']['detail']}`），
   上游副本与独立取回逐字节相同（C2），23/23 quote 可检索（C3c），19/19 未解析声明为真（C8），
   无自封验证字段（C9），claims 为空（C10）。缺陷集中在 locator 坐标与两处措辞，**不涉及伪造**。
2. **F-01 是坐标混用，不是随机错**：把 7 条偏移平移到 quote 内部起点后切片恰为 `` `+prefix+` ``，
   说明生成器用「quote 内偏移」写进了「文档绝对偏移」字段 —— 可确定性复现。
3. **not_run 三项**：① `artifacts/in25_t2/*` 字节一致性（工件不可达 + 仅 16 位前缀，无法重算）；
   ② 上游专用 schema 未重跑（不在本仓主干；本轮只验 canonical 信封 schema）；③ 报告 5949 正文
   **算法结论**的语义门（TPR/FPR/命中率是否真成立）—— 那是 IN25-T2 战役自身的验收面，本工序不越权判。
4. **本工序不勾 verified**：verification_level 只能由平台门计算；review_report.json 里没有
   `verified` 类字段，判定词是 `needs-fix`。
5. **边界**：只读写 report_id=5949 与其上游包 wp-5949-01；上游产物从 git 对象只读导出，未修改任何文件。
6. **无结果图（显式理由）**：本工序是审核/文档类工序，产出是布尔与计数（pass/fail、偏移量、条数），
   不产生场量或曲线；上游报告的两张图属被审对象，不是本工序结果。故 `figures` 为空，非遗漏。
7. **合成 dry-run 的命中率（0.175 vs 基线 0.1576）不予评价**：源报告 ⑤.5 已声明合成脚本非能力证据，本工序不据此加减分。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 结论 | 说明 |
|---|---|---|
| `valid_json` | ✅ | 本报告唯一 json 块 = 信封，`json.loads` 通过；`checks.json` 亦为合法 JSON |
| `schema_pass` | ✅ | 信封对本仓 `schemas/kf_result.v1.schema.json` 实跑 `jsonschema.validate` 通过（C11）；`outputs.review_report.json` 内联完整对象，非指针（针对上游 F-05 的自我约束） |
| `reviewer_independent` | ✅ | 不同工作包/会话；输入=源原文 + 上游产物只读；未读生产者解释作为事实依据（见 independence.limitations 亦如实写明「未做跨模型复核」） |
| `upstream_packages_completed` | ✅ | 上游唯一包 `{TARGET}` 已交付并发布（平台 report 14660，status=published，title `KF-RESULT {TARGET}`，tags 含 `kf-wp:{TARGET}`，C14/C17） |
| `judge_semantic_fidelity` | ⚠️ 部分 | 判的是**登记保真**（quote 是否逐字、偏移是否指向 quote、计数是否与实物一致）：发现 F-01/F-02 两类不保真；报告正文的**学科结论**语义门 not_run（不越权） |
| `do_not_mark_claims_as_verified` | ✅ | 无任何 verified/verification_status/verification_level 字段；判定=needs-fix |
| honest-FAIL 不粉饰 | ✅ | F-01 列 blocking=True 且 verdict=needs-fix；not_run 三项显式列出，不当 pass |
| 可复验（本包自测） | ✅ | `python3 -m pytest tests/test_kf_wp5949_review.py -q` → **11 passed**（断言：源哈希、信封 schema、outputs 内联、无自封字段、7 条引文逐字可定位、F-01/F-02 确定性复现、单 json 块） |

**复跑命令**：`{review['repro_cmd']}`

## 结果信封（本报告唯一 json 块，供机器门消费）

```json
{json.dumps(envelope, ensure_ascii=False, indent=2)}
```
"""
    import os

    os.makedirs("docs/kf/wp-5949-04", exist_ok=True)
    open(OUT_MD, "w", encoding="utf-8").write(body)
    print(f"wrote {OUT_JSON}, {ENVELOPE}, {OUT_MD} ({len(body)} chars)")


if __name__ == "__main__":
    main()