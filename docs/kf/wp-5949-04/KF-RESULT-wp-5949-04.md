# KF-RESULT wp-5949-04

> package_id `wp-5949-04` · task_type `04-independent-review` · report_id `5949` · lane C · status in-review
> 源：`tensor://reports/5949`（field `markdown`）· sha256 `c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002` · 12605 字符 / 17867 字节 utf-8
> 审核对象：`wp-5949-01`（01-asset-registration）@ `ef10acf` · 平台报告 14660
> 判定：**needs-fix**（1 项阻断 F-01；无造假、无张冠李戴）

## ① 本工序做了什么

对 `wp-5949-01` 的资产登记包做独立对抗性审核：不看生产者解释，只拿「报告 5949 原文（自己重新从平台 API 取）」
与「上游交付物（git 只读）」重算。共 **21 项检查**，fail = 5 项（C3、C3b、C6b、C6、C16；明细见 ④ 与 `checks.json`）。
结论不是 pass 也不是 fail：字节身份、计数、claims 纪律都成立；但 locator 有两类坐标缺陷、
两处表述过头。全部数字由 `review_checks.py` 复算后注入。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **独立取原文**：`POST /api/v1/auth/login` → `GET /api/v1/tensor/reports/5949`，取 `markdown`；
   重算 sha256 与契约 `source_hash` 逐位比对（`live sha256=c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002 chars=12605 bytes=17867`）。
2. **取上游产物（只读）**：`git show agent/m15584:docs/kf/wp-5949-01/{kf_result.json,asset_manifest.json,verification.json,report.md}`
   导出到 `work/wp-5949-04/upstream/`，逐文件算 sha256（manifest `3c5564ea75d0988d…` 与信封指针一致）。
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
| `work/wp-5949-04/review_report.json` | 主产物：判定 + 7 条 findings（severity/evidence/reproduction/impact/remediation）+ 21 项检查 + not_run + 独立性声明 |
| `work/wp-5949-04/checks.json` | 21 项复算原始结果（每项 pass/detail，含失败明细） |
| `work/wp-5949-04/review_checks.py` | 独立复算脚本（自带登录取原文，不依赖上游副本） |
| `work/wp-5949-04/build_review.py` | 由 checks.json 组装 review_report.json + 本报告，数字注入不手抄 |
| `work/wp-5949-04/source_5949.md` | 源报告逐字副本（17867 字节，sha256 `c4a082137e7667e9…`） |
| `work/wp-5949-04/upstream/*` | 上游产物只读快照（4 文件 + sha256 固定） |
| `work/wp-5949-04/kf_result.json` | 结果信封（已原样写入本报告唯一 json 块） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

每条引文都是源 markdown 的**逐字切片**（build 时断言 `quote in source`，并给出字符偏移）。

**E1** 7 条声明哈希在原文中的位置（F-01 本应指向这里）· char 155

    > 工件快照 sha256（前 16 位）：coverage `fddd78dbd6e61b17` · seats

**E2** document 级 locator 的 quote 取自首行（F-02）· char 0

    # IN25-T2 · 多样性引擎：氏族矩阵 / 盲预测锁 / 同族查重

**E3** lock_hash 声明自带省略号，故天然不可复算 · char 2901

    | 盲预测锁定工件 | lock_hash `1b96a171b6000fb9…`，40 条预测，复算 ✅，篡改检出 ✅，先跑后锁被拒 ✅ | 三项全真 | ✅ | `artifacts/in25_t2/prereg_lock.json` |

**E4** 19 条 `referenced_unresolved` 的典型形态（代码路径）· char 368

    代码：`tools/diversity/{roster,prereg,dedup,run_node}.py`；测试：`tests/test_diversity_engine.py`。

**E5** 图资产（2 张，源内可定位）· char 10096

    **图 1** 氏族覆盖矩阵：左攻坚者、右破坏者，格子里的数字是该 (族,框架) 格内席位数。

**E6** 报告自述不产生物理量（故本工序只判决策误差）· char 11796

    本节点是**进程/纪律机器**，不产生任何物理量（零平台域语义）

**E7** 另一条截断哈希（blind）· char 338

    > blind `0439b915d213c62f`。

**finding → 复算证据**：F-01（C6b：7/7 偏移错位）· F-02（C3/C3b：3/23 字节不等，A02/A03 line=0）·
F-03（C3C 与 C3 对照）· F-04（report.md ③ 行 vs ② 步骤 7 自相矛盾 + verification.json `all_pass:true`）·
F-05（C12 指针）· F-06（C10 空/缺键）· F-07（C7/C8/C6）。

## ⑤ 注意点与局限

1. **判 needs-fix 而非 fail 的理由**：源字节身份逐位一致（`live sha256=c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002 chars=12605 bytes=17867`），
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
| `upstream_packages_completed` | ✅ | 上游唯一包 `wp-5949-01` 已交付并发布（平台 report 14660，status=published，title `KF-RESULT wp-5949-01`，tags 含 `kf-wp:wp-5949-01`，C14/C17） |
| `judge_semantic_fidelity` | ⚠️ 部分 | 判的是**登记保真**（quote 是否逐字、偏移是否指向 quote、计数是否与实物一致）：发现 F-01/F-02 两类不保真；报告正文的**学科结论**语义门 not_run（不越权） |
| `do_not_mark_claims_as_verified` | ✅ | 无任何 verified/verification_status/verification_level 字段；判定=needs-fix |
| honest-FAIL 不粉饰 | ✅ | F-01 列 blocking=True 且 verdict=needs-fix；not_run 三项显式列出，不当 pass |
| 可复验（本包自测） | ✅ | `python3 -m pytest tests/test_kf_wp5949_review.py -q` → **11 passed**（断言：源哈希、信封 schema、outputs 内联、无自封字段、7 条引文逐字可定位、F-01/F-02 确定性复现、单 json 块） |

**复跑命令**：`cd <worktree> && python3 work/wp-5949-04/review_checks.py --upstream-ref agent/m15584 --out work/wp-5949-04/checks.json && python3 work/wp-5949-04/build_review.py && python3 -m pytest tests/test_kf_wp5949_review.py -q`

## 结果信封（本报告唯一 json 块，供机器门消费）

```json
{
  "package_id": "wp-5949-04",
  "task_type": "04-independent-review",
  "report_id": "5949",
  "provenance": {
    "source_uri": "tensor://reports/5949",
    "source_field": "markdown",
    "source_hash": "sha256:c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002",
    "hash_algo": "sha256",
    "hashed_bytes": "markdown encoded as utf-8",
    "source_chars": 12605,
    "producer": "eco_admin via KF lane C worker (task agent/m15842)",
    "emitted_at": "2026-11-12T02:45:42+00:00",
    "notes": "审核对象 wp-5949-01 @ ef10acfa3cf93f0dd31b28ee128c322c464f822b；判据=独立复算（21 项检查，见 outputs.review_report.json.checks_performed）"
  },
  "outputs": {
    "review_report.json": {
      "package_id": "wp-5949-04",
      "task_type": "04-independent-review",
      "report_id": "5949",
      "review_target": {
        "package_id": "wp-5949-01",
        "task_type": "01-asset-registration",
        "branch": "agent/m15584",
        "commit": "ef10acfa3cf93f0dd31b28ee128c322c464f822b",
        "platform_report_id": 14660,
        "artifact_hashes": {
          "asset_manifest.json": "sha256:3c5564ea75d0988de761c7abca2ead5b259ff83a69333a2e369b8d81d449727e",
          "kf_result.json": "sha256:496c733c8589134e8aa2b0a3e6f93bdf1b4b99dd7e48cf7d2781893006ece06c",
          "verification.json": "sha256:6ae06f7238034a8be5e199c8e62918afb7ff017daf72ac57a62562083fba9658",
          "report.md": "sha256:152a76a48d41d20128244bb2e4ce9a1dd3dc7cd107864dcc20bacd2862b81af2"
        }
      },
      "verdict": "needs-fix",
      "verdict_scope": "上游包的**字节身份与计数**成立（源哈希逐位一致、23/23 quote 可检索、id 唯一、claims 为空、无自封验证字段）；但 locator 作为机器可消费产品有两类坐标缺陷（F-01 高：7/7 digest 偏移错位；F-02 中：document 级 3 条混用）与两处过头表述（F-03/F-04）。故不是 pass，也非 fail（无造假、无张冠李戴）。",
      "blocking_findings": [
        "F-01"
      ],
      "findings": [
        {
          "id": "F-01",
          "severity": "high",
          "likelihood": "certain（7/7 确定性复算）",
          "blocking": true,
          "category": "locator_coordinate_mixing",
          "title": "declared_digests 的 start_char/end_char 是「相对 quote 的偏移」，被当作文档绝对偏移写入",
          "evidence": [
            {
              "artifact": "report_5949.markdown",
              "locator": {
                "method": "search",
                "start_char": 155,
                "end_char": 212
              },
              "quote": "> 工件快照 sha256（前 16 位）：coverage `fddd78dbd6e61b17` · seats",
              "verified_verbatim": true
            },
            {
              "artifact": "asset_manifest.json @ ef10acf",
              "path": "declared_digests.items[]",
              "observation": {
                "coverage": {
                  "declared": [
                    31,
                    49
                  ],
                  "doc_absolute": [
                    155,
                    212
                  ],
                  "slice_at_declared": " 同族查重\n\n> 战役节点 **IN",
                  "prefix_index_within_quote": null
                },
                "seats": {
                  "declared": [
                    2,
                    20
                  ],
                  "doc_absolute": [
                    213,
                    280
                  ],
                  "slice_at_declared": "IN25-T2 · 多样性引擎：氏族",
                  "prefix_index_within_quote": null
                },
                "prereg_lock": {
                  "declared": [
                    35,
                    53
                  ],
                  "doc_absolute": [
                    213,
                    280
                  ],
                  "slice_at_declared": "重\n\n> 战役节点 **IN25-T",
                  "prefix_index_within_quote": null
                },
                "calibration": {
                  "declared": [
                    2,
                    20
                  ],
                  "doc_absolute": [
                    281,
                    337
                  ],
                  "slice_at_declared": "IN25-T2 · 多样性引擎：氏族",
                  "prefix_index_within_quote": null
                },
                "dedup_ledger": {
                  "declared": [
                    36,
                    54
                  ],
                  "doc_absolute": [
                    281,
                    337
                  ],
                  "slice_at_declared": "\n\n> 战役节点 **IN25-T2",
                  "prefix_index_within_quote": null
                },
                "blind": {
                  "declared": [
                    8,
                    26
                  ],
                  "doc_absolute": [
                    338,
                    365
                  ],
                  "slice_at_declared": "2 · 多样性引擎：氏族矩阵 / 盲",
                  "prefix_index_within_quote": null
                },
                "lock_hash": {
                  "declared": [
                    22,
                    41
                  ],
                  "doc_absolute": [
                    2901,
                    3022
                  ],
                  "slice_at_declared": " / 盲预测锁 / 同族查重\n\n> 战",
                  "prefix_index_within_quote": null
                }
              },
              "recomputed": "7/7 条：md[start:end] != quote；把偏移平移到 quote 内部起点后，切片恰为 `+digest_prefix+`（反引号包裹）"
            }
          ],
          "reproduction": "python3 work/wp-5949-04/review_checks.py；看 C6b_digest_offset_semantics：coverage 声明 (31,49)，文档绝对位置 (155,212)，md[31:49]==' 同族查重\\n\\n> 战役节点 **IN'；而 quote[31:49]=='`fddd78dbd6e61b17`'",
          "impact": "字段名承诺的是文档绝对偏移（20 条 asset locator 确实是绝对的），digest 这 7 条却换了坐标系：任何按 start_char/end_char 取值的机器消费者会读到无关字节，E3/E4 语义下判 LOCATOR_BAD_OFFSETS。digest 本身 verifiable=false（16 位截断），不影响轨迹哈希，但 locator 作为产品承诺是错的。",
          "remediation": "把 7 条改成文档绝对偏移（或改字段名为 offset_in_quote 并写明语境），并在 integrity 里加 offset-vs-quote 字节相等校验。",
          "disposition": "request-changes"
        },
        {
          "id": "F-02",
          "severity": "medium",
          "likelihood": "certain（3/3）",
          "blocking": false,
          "category": "locator_semantics",
          "title": "document 级 locator（A01/A02/A03）用全篇跨度配首行 quote，且 A02/A03 的 start_line/end_line=0",
          "evidence": [
            {
              "artifact": "report_5949.markdown",
              "locator": {
                "method": "search",
                "start_char": 0,
                "end_char": 36
              },
              "quote": "# IN25-T2 · 多样性引擎：氏族矩阵 / 盲预测锁 / 同族查重",
              "verified_verbatim": true
            },
            {
              "artifact": "asset_manifest.json @ ef10acf",
              "path": "assets[0..2].locator",
              "observation": "document 级 asset=3 字节相等失败=['A01', 'A02', 'A03']（全篇跨度 0..12605 对比首行 quote → 必然不等，属坐标混用）；line 字段为 0 者=[{'asset': 'A02', 'start_line': 0}, {'asset': 'A03', 'start_line': 0}]"
            }
          ],
          "reproduction": "review_checks.py 的 C3/C3b：checked=23，字节相等失败=['A01','A02','A03']；A02/A03 start_line=0",
          "impact": "文档级资产的 quote 只当锚点、偏移指全篇，二者语义不同；E4 语义下同样判失败（上游在 integrity.quote_uniqueness.note 里声明过该约定，但没改字段语义）。行号 0 是非法值。",
          "remediation": "document 级资产改用 method=document + 无偏移（或 offsets=[0,len] 且另给 anchor_quote 字段），行号填真实值。",
          "disposition": "request-changes"
        },
        {
          "id": "F-03",
          "severity": "medium",
          "likelihood": "certain",
          "blocking": false,
          "category": "overstated_check",
          "title": "verification.json 自述「checked 23 locators against live markdown bytes; failing=[]」不可复算",
          "evidence": [
            {
              "artifact": "verification.json @ ef10acf",
              "sha256": "sha256:6ae06f7238034a8be5e199c8e62918afb7ff017daf72ac57a62562083fba9658",
              "path": "checks.source_locator_resolvable.detail",
              "quote": "checked 23 locators against live markdown bytes; failing=[]"
            },
            {
              "artifact": "checks.json",
              "path": "C3/C6b",
              "observation": "checked=23 failing=[{'asset': 'A01', 'why': 'slice_ne_quote'}, {'asset': 'A02', 'why': 'slice_ne_quote'}, {'asset': 'A03', 'why': 'slice_ne_quote'}]（document 级 3 条另计于 C3b） ; False"
            }
          ],
          "reproduction": "对照 C3（3/23 字节不等）与 C6b（7/7 digest 偏移错位）：该布尔只在「子串检索」语义下成立，在「声明偏移处取值」语义下不成立；而 verification 文本说的是 locator。",
          "impact": "把 search-resolvable 与 offset-resolvable 混成一个布尔，使自检结论偏乐观（failing=[]），下游若引用该布尔会把 locator 缺陷当已排除。",
          "remediation": "拆成两个布尔：quotes_searchable / offsets_byte_equal，并把后者纳入 all_pass。",
          "disposition": "request-changes"
        },
        {
          "id": "F-04",
          "severity": "medium",
          "likelihood": "certain",
          "blocking": false,
          "category": "verification_attribution",
          "title": "报告把自产 verification.json 称作「平台侧独立复算」，且文件内含 verified_at/all_pass=true",
          "evidence": [
            {
              "artifact": "report.md @ ef10acf",
              "sha256": "sha256:152a76a48d41d20128244bb2e4ce9a1dd3dc7cd107864dcc20bacd2862b81af2",
              "path": "③ 产出物清单表 · verification.json 行",
              "quote": "| `docs/kf/wp-5949-01/verification.json` | 平台侧独立复算的 7 项 acceptance 结论（all_pass=True） |"
            },
            {
              "artifact": "report.md @ ef10acf",
              "path": "② 步骤 7",
              "quote": "7. **验收独立复算**：`verify` 子命令重新登录并**重新拉取**原文，重算哈希、重解析全部 locator、重查 id 唯一性与 claims 状态，结果写 `verification.json`；离线 pytest 再用本地副本复验一遍。"
            },
            {
              "artifact": "verification.json @ ef10acf",
              "path": "$",
              "quote": "\"all_pass\": true",
              "note": "同文件含 \"verified_at\": \"2026-11-12T01:25:34.140030+00:00\""
            }
          ],
          "reproduction": "git show agent/m15584:docs/kf/wp-5949-01/report.md | grep 平台侧  → 恰为 ③ 表该行；同一报告的 ② 步骤 7 明说这是本包 verify 子命令产出。",
          "impact": "V1（三状态分离律）：verification_level 只能由平台门计算。此处虽 claims=0、未把任何 claim 标 verified（C9 未命中禁用字段），但「平台侧」措辞 + verified_at/all_pass 会被下游读成已经平台验证，等同自封。",
          "remediation": "改写为「本包 verify 子命令的可复算自检（非平台门签发）」，并把 verified_at 改名为 checked_at、all_pass 改名为 self_check_all_pass。",
          "disposition": "request-changes"
        },
        {
          "id": "F-05",
          "severity": "low",
          "likelihood": "certain",
          "blocking": false,
          "category": "envelope_shape",
          "title": "outputs['asset_manifest.json'] 是文件指针（path/sha256/bytes），不是 schema 要求的内容对象",
          "evidence": [
            {
              "artifact": "kf_result.json @ ef10acf",
              "path": "outputs.asset_manifest.json",
              "observation": "outputs 值键=['asset_count', 'bytes', 'claims', 'path', 'sha256']；sha256 可与 docs/kf/wp-5949-01/asset_manifest.json 对上=True；但值是**指针**不是内容对象（schema 描述要求内容对象）"
            }
          ],
          "reproduction": "review_checks.py C12：指针 sha256 与 agent/m15584 上的 manifest 文件逐位对上（3c5564ea…），说明内容可寻址但未内联；同类先例 wp-5760-01 亦为指针。",
          "impact": "下游工序要落到仓库分支才能取内容；离线/跨仓消费（本单审核即如此）需要额外 git 访问。不影响身份正确性。",
          "remediation": "在 outputs 内联 manifest 内容，或加 pointer_kind 字段显式声明这是指针。",
          "disposition": "accept-with-note"
        },
        {
          "id": "F-06",
          "severity": "low",
          "likelihood": "certain",
          "blocking": false,
          "category": "claim_key_semantics",
          "title": "信封省略 claims 键，报告正文称 claims 为空数组",
          "evidence": [
            {
              "artifact": "kf_result.json @ ef10acf",
              "path": "$",
              "observation": "manifest.claims=[] envelope_has_claims_key=False (信封省略 claims；报告正文称 claims 为空数组——空/缺键语义等价，记差异不记缺陷)"
            },
            {
              "artifact": "report_5949.markdown",
              "locator": {
                "method": "search",
                "start_char": 11796,
                "end_char": 11828
              },
              "quote": "本节点是**进程/纪律机器**，不产生任何物理量（零平台域语义）",
              "verified_verbatim": true
            }
          ],
          "reproduction": "review_checks.py C10：manifest.claims=[] 而 envelope 无 claims 键；kf_result.v1.schema.json 中 claims 非必需 → 两者均合法。",
          "impact": "语义等价（空/缺键），仅措辞不一致；不影响门禁。",
          "remediation": "报告措辞改为「claims 键省略（manifest 内为空数组）」，或信封内补 claims: []。",
          "disposition": "accept-with-note"
        },
        {
          "id": "F-07",
          "severity": "info",
          "likelihood": "certain",
          "blocking": false,
          "category": "coverage_limitation",
          "title": "23 项中 19 项 referenced_unresolved、7 条声明哈希全部不可复算：登记包对报告③表的数字不提供独立字节绑定",
          "evidence": [
            {
              "artifact": "report_5949.markdown",
              "locator": {
                "method": "search",
                "start_char": 2901,
                "end_char": 3022
              },
              "quote": "| 盲预测锁定工件 | lock_hash `1b96a171b6000fb9…`，40 条预测，复算 ✅，篡改检出 ✅，先跑后锁被拒 ✅ | 三项全真 | ✅ | `artifacts/in25_t2/prereg_lock.json` |",
              "verified_verbatim": true
            },
            {
              "artifact": "report_5949.markdown",
              "locator": {
                "method": "search",
                "start_char": 368,
                "end_char": 459
              },
              "quote": "代码：`tools/diversity/{roster,prereg,dedup,run_node}.py`；测试：`tests/test_diversity_engine.py`。",
              "verified_verbatim": true
            },
            {
              "artifact": "checks.json",
              "path": "C7/C8/C6",
              "observation": "assets=23 unique_ids=23 by_resolution={'resolved_in_source': 4, 'referenced_unresolved': 19} ; path_assets=19 wrong=[]"
            }
          ],
          "reproduction": "C7 by_resolution={'resolved_in_source': 4, 'referenced_unresolved': 19}；C8 19 条路径在 agent/m15584 树内均不存在（标未解析无误）；C6 verifiable=0（前缀 16 位）。",
          "impact": "不构成缺陷（上游如实标注、未据此宣称一致），但意味着 wp-5949-01 能证明的只有「源字节身份 + 引用位置」，报告③表的 ✅ 仍只有生产者自述的 pytest/ledger 支撑。审核侧据此把该包的证据强度定在「asset inventory only」。",
          "remediation": "无（属上游工件不在本仓的客观限制）；建议下游消费方不要把该包当数字证据源。",
          "disposition": "accept-with-note"
        }
      ],
      "overstated_claims": [
        {
          "claim": "平台侧独立复算的 7 项 acceptance 结论（all_pass=True）",
          "where": "report.md ③ 产出物清单表",
          "why_overstated": "该文件由本包 verify 子命令在生产者会话内产出；平台门未签发（F-04）"
        },
        {
          "claim": "checked 23 locators against live markdown bytes; failing=[]",
          "where": "verification.json checks.source_locator_resolvable.detail",
          "why_overstated": "只在子串检索语义成立；声明偏移处字节相等实测 3/23 资产 + 7/7 digest 不成立（F-01/F-03）"
        },
        {
          "claim": "登记 23 项资产",
          "where": "report.md ① 与平台 summary",
          "why_overstated": "23 中 4 项为源内可定位资产、19 项为未解析引用；counts.by_resolution 已如实分列，措辞易被读成 23 项已验证资产（F-07）"
        }
      ],
      "checks_performed": [
        {
          "id": "C10_claims_empty",
          "pass": true,
          "detail": "manifest.claims=[] envelope_has_claims_key=False (信封省略 claims；报告正文称 claims 为空数组——空/缺键语义等价，记差异不记缺陷)"
        },
        {
          "id": "C11_envelope_against_canonical_schema",
          "pass": true,
          "detail": "valid vs schemas/kf_result.v1.schema.json"
        },
        {
          "id": "C12_outputs_pointer_dereference",
          "pass": true,
          "detail": "outputs 值键=['asset_count', 'bytes', 'claims', 'path', 'sha256']；sha256 可与 docs/kf/wp-5949-01/asset_manifest.json 对上=True；但值是**指针**不是内容对象（schema 描述要求内容对象）"
        },
        {
          "id": "C13_figures",
          "pass": true,
          "detail": "platform_figures=2 manifest_figure_assets=2 payload_keys=[['caption', 'name'], ['caption', 'name']]"
        },
        {
          "id": "C14_report_single_json_block",
          "pass": true,
          "detail": "json_blocks=1 equals_envelope=True upstream_api_title='KF-RESULT wp-5949-01' upstream_api_tags=['kf-wp:wp-5949-01', 'KF-RESULT', 'asset-registration', 'IN25-T2', 'wp-5949-01'] upstream_status=published"
        },
        {
          "id": "C15_report_claim_repo_schema_absent",
          "pass": true,
          "detail": "报告有该断言=True 上游 commit 树内该文件存在=False"
        },
        {
          "id": "C16_verification_attribution",
          "pass": false,
          "detail": "报告称 verification.json 为「平台侧独立复算」；实际由本包 scripts/kf/build_asset_manifest_5949.py verify 子命令（生产者会话内）产出，含 verified_at/all_pass=True——非平台门签发"
        },
        {
          "id": "C17_upstream_kf_wp_tag",
          "pass": true,
          "detail": "title/tag check on report 14660"
        },
        {
          "id": "C18_figure_captions",
          "pass": true,
          "detail": "manifest.source.platform_figures 与平台 figures[] 的 name/caption 逐字比对"
        },
        {
          "id": "C1_source_identity",
          "pass": true,
          "detail": "live sha256=c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002 chars=12605 bytes=17867"
        },
        {
          "id": "C2_upstream_source_copy",
          "pass": true,
          "detail": "upstream copy sha256=c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002"
        },
        {
          "id": "C3_locator_slices",
          "pass": false,
          "detail": "checked=23 failing=[{'asset': 'A01', 'why': 'slice_ne_quote'}, {'asset': 'A02', 'why': 'slice_ne_quote'}, {'asset': 'A03', 'why': 'slice_ne_quote'}]（document 级 3 条另计于 C3b）"
        },
        {
          "id": "C3b_document_locators",
          "pass": false,
          "detail": "document 级 asset=3 字节相等失败=['A01', 'A02', 'A03']（全篇跨度 0..12605 对比首行 quote → 必然不等，属坐标混用）；line 字段为 0 者=[{'asset': 'A02', 'start_line': 0}, {'asset': 'A03', 'start_line': 0}]"
        },
        {
          "id": "C3c_quotes_searchable",
          "pass": true,
          "detail": "按子串检索 23 条 quote，未命中=[]"
        },
        {
          "id": "C4_locator_line_numbers",
          "pass": true,
          "detail": "mismatch=[]"
        },
        {
          "id": "C5_quote_uniqueness",
          "pass": true,
          "detail": "non_unique=[] declared_checked=20"
        },
        {
          "id": "C6_declared_digests",
          "pass": false,
          "detail": "items=7 verifiable=0 failing=['coverage', 'seats', 'prereg_lock', 'calibration', 'dedup_ledger', 'blind', 'lock_hash'] (前缀 16 位且工件不在树内 → 不可复算，属登记声明而非证据)"
        },
        {
          "id": "C6b_digest_offset_semantics",
          "pass": false,
          "detail": [
            {
              "label": "coverage",
              "declared": [
                31,
                49
              ],
              "doc_absolute": [
                155,
                212
              ],
              "slice_at_declared": " 同族查重\n\n> 战役节点 **IN",
              "matches_line_relative": false
            },
            {
              "label": "seats",
              "declared": [
                2,
                20
              ],
              "doc_absolute": [
                213,
                280
              ],
              "slice_at_declared": "IN25-T2 · 多样性引擎：氏族",
              "matches_line_relative": false
            },
            {
              "label": "prereg_lock",
              "declared": [
                35,
                53
              ],
              "doc_absolute": [
                213,
                280
              ],
              "slice_at_declared": "重\n\n> 战役节点 **IN25-T",
              "matches_line_relative": false
            },
            {
              "label": "calibration",
              "declared": [
                2,
                20
              ],
              "doc_absolute": [
                281,
                337
              ],
              "slice_at_declared": "IN25-T2 · 多样性引擎：氏族",
              "matches_line_relative": false
            },
            {
              "label": "dedup_ledger",
              "declared": [
                36,
                54
              ],
              "doc_absolute": [
                281,
                337
              ],
              "slice_at_declared": "\n\n> 战役节点 **IN25-T2",
              "matches_line_relative": false
            },
            {
              "label": "blind",
              "declared": [
                8,
                26
              ],
              "doc_absolute": [
                338,
                365
              ],
              "slice_at_declared": "2 · 多样性引擎：氏族矩阵 / 盲",
              "matches_line_relative": false
            },
            {
              "label": "lock_hash",
              "declared": [
                22,
                41
              ],
              "doc_absolute": [
                2901,
                3022
              ],
              "slice_at_declared": " / 盲预测锁 / 同族查重\n\n> 战",
              "matches_line_relative": false
            }
          ]
        },
        {
          "id": "C7_counts_consistency",
          "pass": true,
          "detail": "assets=23 unique_ids=23 by_resolution={'resolved_in_source': 4, 'referenced_unresolved': 19}"
        },
        {
          "id": "C8_resolution_falsifiable",
          "pass": true,
          "detail": "path_assets=19 wrong=[]"
        },
        {
          "id": "C9_no_self_verification_fields",
          "pass": true,
          "detail": "manifest_hits=[] envelope_hits=[]"
        }
      ],
      "checks_not_run": [
        {
          "check": "上游 artifacts/in25_t2/*.json 的字节一致性",
          "reason": "工件不在任何可达检出内（C8 已证）；7 条声明哈希只有 16 位前缀，无法重算"
        },
        {
          "check": "上游 schema（schemas/asset_manifest.v1.wp-5949-01.schema.json）重跑 jsonschema",
          "reason": "该 schema 不在本仓主干；本单只验证了信封 vs schemas/kf_result.v1.schema.json（C11 通过），未重跑上游专用 schema"
        },
        {
          "check": "语义门 M6（report 5949 正文结论是否真实成立：多样性引擎的 TPR/FPR/命中率）",
          "reason": "本工序审核对象是 wp-5949-01 的登记正确性；正文算法结论属 IN25-T2 战役自身验收，且其工件不可达 → 明确 not_run，不记 pass"
        },
        {
          "check": "上游 pytest tests/test_kf_wp5949.py 重跑",
          "reason": "测试文件在 agent/m15584 分支但依赖包内脚本与工作树约定；本单以独立复算脚本替代，未重跑"
        }
      ],
      "independence": {
        "reviewer_package": "wp-5949-04",
        "relationship_to_producer": "不同工作包、不同会话；审核对象只经 git 对象读取，未修改",
        "inputs_used": [
          "report 5949 markdown（独立经 GET /api/v1/tensor/reports/5949 取回）",
          "上游 wp-5949-01 的 kf_result.json / asset_manifest.json / verification.json / report.md（git 只读）",
          "schemas/kf_result.v1.schema.json（本仓主干）"
        ],
        "inputs_excluded": [
          "生产者解释性文字（只读其交付报告作为被审对象，不作事实依据；所有事实以复算为准）",
          "其它 report_id（未读写）"
        ],
        "limitations": [
          "本 reviewer 与 producer 同属 AI 智能体群体，但不同会话/工作包；共享的是代码与仓，不共享本次任务的上下文",
          "未做跨模型复核（strong-model sample）"
        ]
      },
      "source_identity": {
        "source_uri": "tensor://reports/5949",
        "source_field": "markdown",
        "source_hash": "sha256:c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002",
        "source_chars": 12605,
        "recomputed": true,
        "upstream_copy_identical": true
      },
      "repro_cmd": "cd <worktree> && python3 work/wp-5949-04/review_checks.py --upstream-ref agent/m15584 --out work/wp-5949-04/checks.json && python3 work/wp-5949-04/build_review.py && python3 -m pytest tests/test_kf_wp5949_review.py -q"
    }
  }
}
```
