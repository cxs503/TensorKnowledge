# KF-RESULT wp-5624-01

- package_id: `wp-5624-01` ｜ task_type: `01-asset-registration` ｜ lane: C
- report_id: `5624`（本包唯一触碰的报告）｜ source: `tensor://reports/5624` · field=`markdown`
- source_hash: `sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839`
  （独立重算，与契约声明值一致：true）
- 分层标签（原样登记、不解读）：`IN15-O5|in15-o5-artifact-sha256-indexer|s`
- 状态：draft（verification 由平台门计算，本包不标 verified）

## ① 本工序做了什么

只做「源资产登记」，不做抽取。核对 report_id=5624 与其 markdown 的字节哈希，登记：
平台记录元数据、正文小节切分（7 节，含行区间与每节 sha256）、
可解析附件（figures 3 条，仅 name/caption 元数据）、
正文声明的路径引用（4 条）与内容摘要引用
（2 条），并为每条引文提供逐字可定位 locator
（9/9 全部命中）。`claims` 为空数组——合同
`objective.register_assets=true` / `classify_report_type=false`，且 notes 明确
「claims 允许为空数组」，故不生成任何 claim（不做强制抽取）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文**：`POST $TENSOR_API_BASE/auth/login` 取 token → `GET $TENSOR_API_BASE/tensor/reports/5624`。
   只读 5624 一份；未读写任何其它 report_id（见 manifest `boundary`）。
2. **哈希复算**：`hashlib.sha256(markdown.encode('utf-8'))` 与契约 `source_hash` 逐字节比对；
   同时比对字符数（运行时 1833 vs 契约
   1833）与 UTF-8 字节数
   （3255）。
3. **小节切分**：按 ATX 标题切分，记录 `level/heading/line_start/line_end/chars/sha256`
   （7 节），供后续工序按节取证。
4. **引用抽取**：仅从反引号代码片段抽路径（`PATH_RE`/`MODULE_RE`）与十六进制摘要
   （`DIGEST_RE`）；locator 一律取**原文整行**，因此逐字可定位（脚本机检，非人工粘贴）。
   截断式摘要与全量式摘要另做前缀一致性机检（`content_digests[].prefix_consistent`）。
5. **附件登记**：读平台记录 `figures` 字段（3 条），只登记
   name/caption 与「是否存在 png_base64 载荷」标记；未下载、未解码图像。
6. **零手抄**：`scripts/kf/wp-5624-01/register_assets.py` 内无任何手写数字/引文；
   本文数字与引文全部由 `make_report.py` 从 JSON 产物与原文行注入。
7. **自检**：`register_assets.py --check` 跑 schema 校验 + locator 逐字匹配 + id 唯一性 +
   哈希一致性；`tests/kf/test_wp_5624_01.py` 共 11 条用例（含联网重取原文复算与确定性重建）。

关键设置：产物落 `artifacts/kf/wp-5624-01/`（本地、被 .gitignore/推送门过滤），
同字节镜像落 `docs/kf/wp-5624-01/`（git 可追踪）；工件存在性一律标 `not_checked`。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-5624-01/kf_result.json`（= `artifacts/kf/wp-5624-01/kf_result.json` 同字节） | 结果信封：package_id / task_type / report_id / provenance(source_hash,source_field,source_uri) / outputs / claims=[] |
| `docs/kf/wp-5624-01/asset_manifest.json`（同上镜像） | 登记清单：source_asset（hash/size/metadata/layer hint）、attachments（3）、sections（7）、referenced_artifacts（4）、content_digests（2）、observations（1）、locator_check（9/9）、unresolved（3）、boundary |
| `docs/kf/wp-5624-01/fig_acceptance.png` | 验收图：左=locator 按桶解析数；右=acceptance 自检逐项（数据由 JSON 程序化读取） |
| `docs/kf/wp-5624-01/kf_result_wp-5624-01.md` | 本报告（六段 + 唯一 json 块） |
| `scripts/kf/wp-5624-01/register_assets.py` | 生成器：`--check` 打印 acceptance 自检，`--from-file/--record-json` 支持离线复跑 |
| `scripts/kf/wp-5624-01/make_report.py` | 报告生成器（引文由 manifest 注入，json 块与产物同字节） |
| `scripts/kf/wp-5624-01/make_figure.py` | 验收图生成器 |
| `tests/kf/test_wp_5624_01.py` | 11 条回归（schema/哈希复算/逐字引文/唯一性/确定性重建/单一报告边界/不标 verified） |

## ④ 证据定位表（字段 → 原文引文，逐字）

| 字段 | 原文引文（逐字） |
|---|---|
| 引用路径（正文代码片段） · `5624-ref-01` · source_field=markdown | ``artifacts/`（0 文件）与 `runs/`（0 文件），` |
| 引用路径（正文代码片段） · `5624-ref-02` · source_field=markdown | ``artifacts/`（0 文件）与 `runs/`（0 文件），` |
| 引用路径（正文代码片段） · `5624-ref-03` · source_field=markdown | ``tools/artifact_indexer/`，纯标准库，不触碰任何既有 API/schema/表。` |
| 引用路径（正文代码片段） · `5624-ref-04` · source_field=markdown | `- 工具链：python3.11 标准库（hashlib/json/os/random），CLI `python3 -m tools.artifact_indexer {build|check|verify|show}`，` |
| 正文引用的内容摘要值 · `5624-dig-01` · source_field=markdown | `| 索引文件 sha256（前后一致） | `7223cab4b4edf2f1dbad8cba148bf4c56b7cbc938dd9a2620ba146dd6ed20bb7` |` |
| 正文引用的内容摘要值 · `5624-dig-02` · source_field=markdown | `- 幂等：二次构建索引 sha256 前后一致（`7223cab4b4edf2f1…`），**通过 ✓**` |
| 附件（figures 字段图注） · `fig-1` · source_field=figures | `Fig.1 索引清单：按根目录统计文件数与字节数（artifacts/ 94 + runs/ 8 = 102）。` |
| 附件（figures 字段图注） · `fig-2` · source_field=figures | `Fig.2 工件尺寸分布：对数直方图与 CDF（最大单件 471 KB，无 GB 级大件）。` |
| 附件（figures 字段图注） · `fig-3` · source_field=figures | `Fig.3 验收证据：左=抽查 20/20 全中；右=冷构建全量哈希 vs 二次构建 0 重算（mtime 未变跳过，幂等）。` |

全部 locator 均机检通过：`9/9` 解析成功、未解析
`0` 条（方法：markdown 项 `quote in markdown`，figures 项
`caption == figure.caption`）。

内部一致性观察（不裁决，如实登记）：

1. `5624-obs-01`（internal_inconsistency, status=unresolved）：正文对两个工件根的文件数自述为 0 文件，同段末又给出>0 的文件总数；Fig.1 caption 给出按根目录的分解（94+8）。三处计数口径不一致。
   - 引文：``artifacts/`（0 文件）与 `runs/`（0 文件），`
   - 引文：`共 **102 文件 / 6.45 MB**。判据（任务书）：索引建立后抽查 20 文件全中 +`
   - 引文：`Fig.1 索引清单：按根目录统计文件数与字节数（artifacts/ 94 + runs/ 8 = 102）。`

## ⑤ 注意点与局限

1. **原文内部计数矛盾（honest-unresolved）**：正文自述两个工件根各「0 文件」，同段末给出
   「共 102 文件 / 6.45 MB」，而 Fig.1 caption 给出分解「94 + 8 = 102」。三处口径不一致。
   本工序不臆断哪个为准（`do_not_invent_missing_information`）——裁决需要在 m4963 的
   TensorPlatform worktree 里重跑索引器，超出本包边界。
2. **工件存在性未核**：报告声明的 `artifacts/`、`runs/`、`tools/artifact_indexer/` 属于
   m4963 的 TensorPlatform worktree，本包工作树为 TensorKnowledge，跨树取证会越界；
   故全部 `existence=not_checked`，不主张这些工件存在或其哈希正确。
3. **摘要值未重算**：正文引用的索引表 sha256（及 16 位截断式）只登记不重算，仅机检
   「截断式是全量式前缀」（prefix_consistent=true）。
4. **不做抽取语义判定**：报告 5624 的 20/20 抽查、102/102 全量 verify、pytest 10 passed
   等结论属上游自述，本包只登记其位置备查，不背书、不复算、不标 verified。
5. **附件载荷**：figures 仅元数据（无 png_base64），无法核验图与其数据的一致性。
6. 适用范围：生成器可复用于任意 report 的资产登记（改 `REPORT_ID`/`CONTRACT_*` 常量），
   前提是只登记不解读。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 证据 |
|---|---|---|
| valid_json | ✅ | `kf_result.json` / `asset_manifest.json` 均 `json.loads` 通过 |
| schema_pass | ✅ | jsonschema 校验 `schemas/kf_result.v1.schema.json`（`--check` 输出 `schema_pass: true`） |
| source_locator_resolvable | ✅ | `locator_check 9/9`，`all_resolved: true` |
| source_hash_matches | ✅ | 重算 `sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839` == 契约值；字符数 1833 == 1833 |
| no_duplicate_ids | ✅ | ref/digest/obs 共 7 个 id 全唯一（`--check` 输出 `no_duplicate_ids: true`） |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅（空集，合同允许） | `claims: []`；`boundary.claims_generated: 0` 与 envelope 一致；未强造 claim |
| 不标 verified / 单一报告边界 | ✅ | `boundary.report_ids_read/written: ["5624"]`；`verification_status: none` |
| pytest | ✅ | `python3 -m pytest tests/kf/test_wp_5624_01.py -q` → 11 passed |

诚实声明：上表 ✅ 只表示**本工序的登记动作正确**，不代表报告 5624 的科学结论已获验证；
`observations` 中的计数矛盾保持 unresolved，未做粉饰。若有任何项失败，亦在本节如实列出。

### repro_cmd（一键复跑）

```bash
cd <repo-root> \
 && python3 scripts/kf/wp-5624-01/register_assets.py --check \
 && python3 scripts/kf/wp-5624-01/make_report.py \
 && python3 scripts/kf/wp-5624-01/make_figure.py \
 && python3 -m pytest tests/kf/test_wp_5624_01.py -q
```

离线复跑（无平台凭据）：`python3 scripts/kf/wp-5624-01/register_assets.py --from-file /tmp/md5624.txt --record-json /tmp/r5624.json --check`。

## 附：kf_result.json（唯一 json 块，与 `docs/kf/wp-5624-01/kf_result.json` 同字节）

```json
{
  "package_id": "wp-5624-01",
  "task_type": "01",
  "report_id": "5624",
  "provenance": {
    "source_hash": "sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839",
    "source_field": "markdown",
    "source_uri": "tensor://reports/5624",
    "producer": "m15571",
    "emitted_at": "2026-11-12T01:21:53Z",
    "notes": "01-asset-registration：仅登记源资产/附件/引用清单与引文定位，未做抽取；claims=[]（合同允许），verification 交平台门计算"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-5624-01",
      "task_type": "01-asset-registration",
      "objective": {
        "register_assets": true,
        "classify_report_type": false,
        "extraction_performed": false
      },
      "generated_at": "2026-11-12T01:21:53Z",
      "generator": "agent/m15571",
      "source_asset": {
        "uri": "tensor://reports/5624",
        "field": "markdown",
        "platform_record_id": 5624,
        "hash": {
          "algorithm": "sha256",
          "value": "sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839",
          "scope": "UTF-8 bytes of tensor_reports.markdown (report 5624)",
          "contract_expected": "sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839",
          "matches_contract": true
        },
        "size": {
          "chars": 1833,
          "bytes_utf8": 3255,
          "lines": 46,
          "contract_chars": 1833,
          "chars_match_contract": true
        },
        "record_metadata": {
          "title": "IN15-O5 工件 sha256 索引器：102 工件索引 + 20/20 抽查全中 + 幂等增量（m4963）",
          "scenario_key": "in15-o5-artifact-sha256-indexer",
          "tags": [
            "IN15-O5",
            "artifact-indexer",
            "sha256",
            "integrity",
            "reproducibility",
            "m4963"
          ],
          "status": "published",
          "created_by": 1,
          "created_at": "2026-11-07T01:04:07.872855+00:00",
          "mission_id": 4963,
          "stage": null
        },
        "contract_layer_hint": {
          "value": "IN15-O5|in15-o5-artifact-sha256-indexer|s",
          "interpreted": false,
          "note": "契约 notes 中的分层标签原样登记；objective.classify_report_type=false，不解读"
        }
      },
      "attachments": {
        "count": 3,
        "items": [
          {
            "name": "fig1_inventory.png",
            "caption": "Fig.1 索引清单：按根目录统计文件数与字节数（artifacts/ 94 + runs/ 8 = 102）。",
            "payload_field_present": false,
            "png_base64_len": 0
          },
          {
            "name": "fig2_sizes.png",
            "caption": "Fig.2 工件尺寸分布：对数直方图与 CDF（最大单件 471 KB，无 GB 级大件）。",
            "payload_field_present": false,
            "png_base64_len": 0
          },
          {
            "name": "fig3_acceptance.png",
            "caption": "Fig.3 验收证据：左=抽查 20/20 全中；右=冷构建全量哈希 vs 二次构建 0 重算（mtime 未变跳过，幂等）。",
            "payload_field_present": false,
            "png_base64_len": 0
          }
        ],
        "scan": {
          "record_figures_len": 3,
          "png_base64_present": false,
          "markdown_image_syntax_hits": 0,
          "external_url_hits": 0,
          "returned_all": true
        },
        "note": "附件=平台记录 figures 字段登记的 3 张图（仅元数据：name/caption），正文自述为后端完整性工具、无物理场量云图；未下载/未解码图像载荷"
      },
      "sections": [
        {
          "ordinal": 1,
          "level": 1,
          "heading": "IN15-O5 · 工件 sha256 索引器（自回归燃料⑤：可复算）",
          "line_start": 1,
          "line_end": 1,
          "chars": 37,
          "sha256": "sha256:5b7dc7952d60a4d29564513bf5c77f4597fc343a8de016a3de235c8e9678e54a"
        },
        {
          "ordinal": 2,
          "level": 2,
          "heading": "① 案例介绍（背景/对象/参数）",
          "line_start": 3,
          "line_end": 10,
          "chars": 335,
          "sha256": "sha256:4e6dfe8256742dceded3668c7334584288fbdd6e0a6b3879eeced3d4c069ce27"
        },
        {
          "ordinal": 3,
          "level": 2,
          "heading": "② 怎么做的（方法/流程/工具链）",
          "line_start": 12,
          "line_end": 18,
          "chars": 418,
          "sha256": "sha256:c541a6e602ec299d866ebabad46106b0665cb901acdcb36b10948b39a1bfb83c"
        },
        {
          "ordinal": 4,
          "level": 2,
          "heading": "③ 计算结果（程序化注入，零手抄）",
          "line_start": 20,
          "line_end": 29,
          "chars": 437,
          "sha256": "sha256:db6022790fa7fad61bbf3b9acaaaad52c85b631672b958530168bb84a30f6a55"
        },
        {
          "ordinal": 5,
          "level": 2,
          "heading": "④ 结果图",
          "line_start": 31,
          "line_end": 32,
          "chars": 61,
          "sha256": "sha256:b72cb8da6fbe5b1e61d1e0597e813d178e491faacb80b26005a2737249b33967"
        },
        {
          "ordinal": 6,
          "level": 2,
          "heading": "⑤ 注意点（坑/局限/适用范围）",
          "line_start": 34,
          "line_end": 39,
          "chars": 293,
          "sha256": "sha256:2e98f1acf264d6c6c1eddbfac2e21f2e27d0886d61727aa77c139c847d7a88a8"
        },
        {
          "ordinal": 7,
          "level": 2,
          "heading": "⑥ 误差判定",
          "line_start": 41,
          "line_end": 46,
          "chars": 239,
          "sha256": "sha256:78d38d09f957edce07625e64a756b55f397ad21cac9d03c216fe008a63e7367e"
        }
      ],
      "referenced_artifacts": [
        {
          "raw_text": "artifacts/",
          "path_kind": "declared_in_report_code_span",
          "occurrences": 1,
          "first_line": 7,
          "locator_quote": "`artifacts/`（0 文件）与 `runs/`（0 文件），",
          "ref_id": "5624-ref-01",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m4963 的 TensorPlatform worktree（工件根/工具目录），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=5624，不跨 worktree 取证，故存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "runs/",
          "path_kind": "declared_in_report_code_span",
          "occurrences": 1,
          "first_line": 7,
          "locator_quote": "`artifacts/`（0 文件）与 `runs/`（0 文件），",
          "ref_id": "5624-ref-02",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m4963 的 TensorPlatform worktree（工件根/工具目录），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=5624，不跨 worktree 取证，故存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "tools/artifact_indexer/",
          "path_kind": "declared_in_report_code_span",
          "occurrences": 1,
          "first_line": 10,
          "locator_quote": "`tools/artifact_indexer/`，纯标准库，不触碰任何既有 API/schema/表。",
          "ref_id": "5624-ref-03",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m4963 的 TensorPlatform worktree（工件根/工具目录），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=5624，不跨 worktree 取证，故存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "tools/artifact_indexer",
          "path_kind": "declared_in_report_code_span",
          "occurrences": 1,
          "first_line": 17,
          "locator_quote": "- 工具链：python3.11 标准库（hashlib/json/os/random），CLI `python3 -m tools.artifact_indexer {build|check|verify|show}`，",
          "ref_id": "5624-ref-04",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m4963 的 TensorPlatform worktree（工件根/工具目录），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=5624，不跨 worktree 取证，故存在性/内容一致性留待上游门或后续工序"
        }
      ],
      "content_digests": [
        {
          "raw_text": "7223cab4b4edf2f1dbad8cba148bf4c56b7cbc938dd9a2620ba146dd6ed20bb7",
          "digits": 64,
          "occurrences": 1,
          "first_line": 25,
          "locator_quote": "| 索引文件 sha256（前后一致） | `7223cab4b4edf2f1dbad8cba148bf4c56b7cbc938dd9a2620ba146dd6ed20bb7` |",
          "digest_id": "5624-dig-01",
          "algorithm": "sha256",
          "note": "报告正文引用的内容摘要值，本工序只登记不重算（对应工件不在本 worktree）"
        },
        {
          "raw_text": "7223cab4b4edf2f1",
          "digits": 16,
          "occurrences": 1,
          "first_line": 45,
          "locator_quote": "- 幂等：二次构建索引 sha256 前后一致（`7223cab4b4edf2f1…`），**通过 ✓**",
          "digest_id": "5624-dig-02",
          "algorithm": "sha256_truncated",
          "note": "报告正文引用的内容摘要值，本工序只登记不重算（对应工件不在本 worktree）",
          "prefix_of": [
            "5624-dig-01"
          ],
          "prefix_consistent": true
        }
      ],
      "observations": [
        {
          "id": "5624-obs-01",
          "kind": "internal_inconsistency",
          "status": "unresolved",
          "statement": "正文对两个工件根的文件数自述为 0 文件，同段末又给出>0 的文件总数；Fig.1 caption 给出按根目录的分解（94+8）。三处计数口径不一致。",
          "locators": {
            "zero_file_lines": [
              7
            ],
            "total_count_line": 8,
            "other_file_count_lines": [
              43
            ],
            "attachment_id": "fig-1"
          },
          "quotes": [
            "`artifacts/`（0 文件）与 `runs/`（0 文件），",
            "共 **102 文件 / 6.45 MB**。判据（任务书）：索引建立后抽查 20 文件全中 +",
            "Fig.1 索引清单：按根目录统计文件数与字节数（artifacts/ 94 + runs/ 8 = 102）。"
          ],
          "note": "本工序不裁决哪个数字为准（不臆造），交由上游/复核工序追溯运行日志"
        }
      ],
      "locator_check": {
        "total": 9,
        "resolved": 9,
        "all_resolved": true,
        "method": "每条 quote 对 markdown 做逐字子串匹配（str in markdown）",
        "items": [
          {
            "bucket": "referenced_artifacts",
            "id": "5624-ref-01",
            "source_field": "markdown",
            "resolvable": true,
            "quote": "`artifacts/`（0 文件）与 `runs/`（0 文件），"
          },
          {
            "bucket": "referenced_artifacts",
            "id": "5624-ref-02",
            "source_field": "markdown",
            "resolvable": true,
            "quote": "`artifacts/`（0 文件）与 `runs/`（0 文件），"
          },
          {
            "bucket": "referenced_artifacts",
            "id": "5624-ref-03",
            "source_field": "markdown",
            "resolvable": true,
            "quote": "`tools/artifact_indexer/`，纯标准库，不触碰任何既有 API/schema/表。"
          },
          {
            "bucket": "referenced_artifacts",
            "id": "5624-ref-04",
            "source_field": "markdown",
            "resolvable": true,
            "quote": "- 工具链：python3.11 标准库（hashlib/json/os/random），CLI `python3 -m tools.artifact_indexer {build|check|verify|show}`，"
          },
          {
            "bucket": "content_digests",
            "id": "5624-dig-01",
            "source_field": "markdown",
            "resolvable": true,
            "quote": "| 索引文件 sha256（前后一致） | `7223cab4b4edf2f1dbad8cba148bf4c56b7cbc938dd9a2620ba146dd6ed20bb7` |"
          },
          {
            "bucket": "content_digests",
            "id": "5624-dig-02",
            "source_field": "markdown",
            "resolvable": true,
            "quote": "- 幂等：二次构建索引 sha256 前后一致（`7223cab4b4edf2f1…`），**通过 ✓**"
          },
          {
            "bucket": "attachments",
            "id": "fig-1",
            "source_field": "figures",
            "resolvable": true,
            "quote": "Fig.1 索引清单：按根目录统计文件数与字节数（artifacts/ 94 + runs/ 8 = 102）。",
            "note": "图注存于记录 figures 字段，正文 markdown 无该文本，故对 figures 记录做逐字匹配"
          },
          {
            "bucket": "attachments",
            "id": "fig-2",
            "source_field": "figures",
            "resolvable": true,
            "quote": "Fig.2 工件尺寸分布：对数直方图与 CDF（最大单件 471 KB，无 GB 级大件）。",
            "note": "图注存于记录 figures 字段，正文 markdown 无该文本，故对 figures 记录做逐字匹配"
          },
          {
            "bucket": "attachments",
            "id": "fig-3",
            "source_field": "figures",
            "resolvable": true,
            "quote": "Fig.3 验收证据：左=抽查 20/20 全中；右=冷构建全量哈希 vs 二次构建 0 重算（mtime 未变跳过，幂等）。",
            "note": "图注存于记录 figures 字段，正文 markdown 无该文本，故对 figures 记录做逐字匹配"
          }
        ],
        "unresolved_items": []
      },
      "unresolved": [
        {
          "item": "referenced_artifacts[].existence",
          "status": "unresolved",
          "reason": "工件根位于 m4963 的 TensorPlatform worktree，本包不跨 worktree 读取（边界约束）"
        },
        {
          "item": "content_digests[].value_recomputation",
          "status": "unresolved",
          "reason": "被摘要工件不在本 worktree，不重算、不主张其正确性"
        },
        {
          "item": "observations[0].which_count_is_authoritative",
          "status": "unresolved",
          "reason": "原文三处计数口径冲突，本工序不裁决（do_not_invent_missing_information）"
        }
      ],
      "boundary": {
        "report_ids_read": [
          "5624"
        ],
        "report_ids_written": [
          "5624"
        ],
        "claims_generated": 0,
        "claims_policy": "no_forced_claim_generation：01 工序只登记资产，envelope.claims=[] 为完整结果",
        "verification_status": "none — 由平台门独立计算，本包不标 verified"
      }
    }
  },
  "claims": []
}
```
