# KF-RESULT wp-4537-01

**工作包** `wp-4537-01` · task_type `01-asset-registration` · lane C · report_id **4537** · mission_id 15537 · 交付仓 TensorKnowledge · status draft（verification 由平台门计算，本单不做 verified 标记）

## ① 本工序做了什么（案例介绍）

**工序职责**：为源报告 `tensor://reports/4537`（标题见下方记录层字段）做**资产登记**——确认 report_id 与其 markdown 的字节哈希、列出可解析的附件/工件并给出可独立复算的定位。本工序**不做抽取**（`objective.extraction_performed=false`）、**不生成 claim**（`claims=[]`，零强制生成）、**不判定报告类型**（`classify_report_type=false`）、**不标 verified**。

- 记录层标题（record.title，非 markdown 引文）：TensorFEM PR#128 CI 修红：把永久红的全仓 lint 门拆成「正确性阻塞门 + 格式棘轮 + 历史债计数」
- scenario_key：`tensorfem_pr128_ci_lint_fix` · status `published` · created_at `2026-11-05T11:27:59.863304+00:00` · mission_id 4175
- 契约分层提示（原样登记、不解读）：`CI修复|tensorfem_pr128_ci_lint_fix|m`
- 源文本：7931 字符 / 12973 UTF-8 字节 / 178 行 / 11 个标题（首行 `## 1. 案例介绍`，末节标题 `7. 交付物与复现入口`）

**一句话结论**：哈希与字符数**精确匹配**契约；登记资产 **27** 项，其中**真正带字节的仅 2 项**（源 markdown 本身 + 平台记录），其余 25 项按「报告声明了、但本仓/本接口拿不到字节」如实标为未解析——这些外部工件属于 TensorFEM 仓，本单不下载、不复制、不臆造哈希。

## ② 怎么做的（步骤/工具/关键设置）

1. **取源（只读、单报告）**：`GET $TENSOR_API_BASE/tensor/reports/4537`（Bearer=agent token），只读 `markdown` 与记录字段；全程未访问任何其它 report_id（测试 `test_manifest_matches_source_report_only` 用正则兜底扫描全部 `tensor://reports/N` 字面值）。
2. **哈希独立重算**：对 markdown 的 UTF-8 字节算 sha256，与契约 `source_hash` 和 `chars` 双向比对（`hash_scope` 写入 manifest）。
3. **结构索引（不做语义解读）**：正则抽 `^#{1,4}` 标题，记录 `char_span`（标题行）与 `section_span`（到下一个任意级标题起点），标题串另存 sha256。明确**不**做层级展开（避免把子节内容算进父节）。
4. **工件发现（全量、零过滤）**：扫 markdown 中所有反引号行内代码，按规则分类为 `path_file` / `path_directory` / `path_basename_shorthand` / `vcs_branch` / `vcs_commit` / `inline_code`；前三类与 vcs 引用进 `assets`，行内代码片段（命令/告警串）进 `inline_code_index`（42 项，只给定位、不计为工件）。
5. **定位可解性**：每个 token 记录其在 markdown 中的字符区间 `[start,end)` 与片段 sha256；门侧只需切片比对即可判定定位是否可解（本单共登记 38 个片段区间，全部逐字复算通过）。
6. **外部可解析性探测**：把每个声明路径拿去本地工作树 `Path.exists()` 检查；不存在则 `payload.present=false`、`sha256=null`，status 降为 `declared_only`/`declared_shorthand`（诚实计负，不送分）。
7. **附件扫描**：记录 `figures[]` 长度、markdown 图片语法命中数、markdown 明文 URL 命中数，全量登记不裁剪。
8. **自检**：`python3 -m pytest tests/test_kf_wp4537_01.py -q` → 10 项不变量（含 envelope 走 `schemas/kf_result.v1.schema.json`、逐 span 复解、去重、构建器确定性）；图 `asset_status.png` 由 manifest 现场计数渲染。

**工具链**：Python 3.11 标准库（urllib/hashlib/json）+ matplotlib 3.10.8 + jsonschema 4.26.0 + pytest；无第三方抓取、无手抄。

## ③ 产出物清单（输出文件名 → 要点）

| 路径 | 类型 | 要点 |
|---|---|---|
| `docs/kf/wp-4537-01/asset_manifest.json` | 交付物（本工序唯一声明输出） | 27 项资产登记；状态分布 resolved 2，declared_metadata_only 6，declared_shorthand 6，declared_only 13；源哈希与契约精确相等；claims 空数组 |
| `docs/kf/wp-4537-01/kf_result.json` | 结果信封 | 按 `schemas/kf_result.v1.schema.json` 组织：package_id/task_type/report_id/provenance/outputs(+claims) |
| `docs/kf/wp-4537-01/asset_status.png` | 结果图 | 资产状态×种类构成 + 哈希/自检摘要（数字由 manifest 现场统计） |
| `scripts/kf/register_4537_assets.py` | 构建器 | 取源→重算哈希→分类→定位→写 manifest/信封；`--from-cache` 可离线复算 |
| `scripts/kf/make_4537_figure.py` | 图生成器 | 只读 manifest 计数，零手抄 |
| `tests/test_kf_wp4537_01.py` | 不变量测试 | 10 项：哈希/字符数/逐 span 复解/去重/claims 空/无 verified/确定性/单报告范围 |
| `schemas/kf_result.v1.schema.json` | 契约（随包引入） | 与平台侧同名 schema 逐字节一致（sha256 `170dba8b…c076`），供信封结构门本地复跑 |
| `runs/m15537_wp4537_01/source_report_4537.md` | 运行缓存（不入库） | 取源快照，供离线复算；不作为第二份真相 |

## ④ 证据定位表（claim/字段 → 原文引文片段）

**claims 为空数组**：本工序 objective 不含抽取，故无 claim 需要证据；下表登记的是**资产/字段级定位**，每行引文均由 manifest 记录的 span 现场切片得到（不是重述）。

| 资产/字段 | kind | 字面值 | 原文引文（逐字切片） | markdown 字符区间 |
|---|---|---|---|---|
| `asset-4537-report-markdown` | report_markdown | `tensor_reports.markdown` | —（无逐字出现，见 notes） | 0 |
| `asset-4537-record` | report_record_metadata | `tensor_reports row` | —（无逐字出现，见 notes） | 0 |
| `asset-4537-figure-1` | report_figure | `lint_gate_m4175.png` | 图 1 左 | 870–875 |
| `asset-4537-path-basename-shorthand-agents-md` | path_basename_shorthand | `AGENTS.md` | AGENTS.md | 3578–3587 |
| `asset-4537-path-basename-shorthand-init-py` | path_basename_shorthand | `__init__.py` | __init__.py | 6172–6183 |
| `asset-4537-path-basename-shorthand-ci-yml` | path_basename_shorthand | `ci.yml` | ci.yml | 694–700 |
| `asset-4537-path-basename-shorthand-evidence-log` | path_basename_shorthand | `evidence.log` | evidence.log | 4110–4122 |
| `asset-4537-path-basename-shorthand-make-figure-py` | path_basename_shorthand | `make_figure.py` | make_figure.py | 5299–5313 |
| `asset-4537-path-basename-shorthand-pyproject-toml` | path_basename_shorthand | `pyproject.toml` | pyproject.toml | 1564–1578 |
| `asset-4537-path-directory-artifacts` | path_directory | `artifacts/` | artifacts/ | 6289–6299 |
| `asset-4537-path-directory-benchmarks` | path_directory | `benchmarks/` | benchmarks/ | 6302–6313 |
| `asset-4537-path-directory-src` | path_directory | `src/` | src/ | 4989–4993 |
| `asset-4537-path-file-github-workflows-ci-yml` | path_file | `.github/workflows/ci.yml` | .github/workflows/ci.yml | 135–159 |
| `asset-4537-path-file-artifacts-lint-gate-m4175-evidence-log` | path_file | `artifacts/lint-gate-m4175/evidence.log` | artifacts/lint-gate-m4175/evidence.log | 3681–3719 |
| `asset-4537-path-file-artifacts-lint-gate-m4175-make-figure-py` | path_file | `artifacts/lint-gate-m4175/make_figure.py` | artifacts/lint-gate-m4175/make_figure.py | 7803–7843 |
| `asset-4537-path-file-artifacts-lint-gate-m4175-run-evidence-sh` | path_file | `artifacts/lint-gate-m4175/run_evidence.sh` | artifacts/lint-gate-m4175/run_evidence.sh | 7650–7691 |
| `asset-4537-path-file-docs-pr65-cure-status-md` | path_file | `docs/PR65_CURE_STATUS.md` | docs/PR65_CURE_STATUS.md | 364–388 |
| `asset-4537-path-file-docs-ci-lint-gate-md` | path_file | `docs/ci-lint-gate.md` | docs/ci-lint-gate.md | 3475–3495 |
| `asset-4537-path-file-docs-merge-cure-pr65-round3-m3891-md` | path_file | `docs/merge-cure-pr65-round3-m3891.md` | docs/merge-cure-pr65-round3-m3891.md | 391–427 |
| `asset-4537-path-file-scripts-lint-gate-py` | path_file | `scripts/lint_gate.py` | scripts/lint_gate.py | 2272–2292 |
| `asset-4537-path-file-tests-test-cohesive-py` | path_file | `tests/test_cohesive.py` | tests/test_cohesive.py | 4479–4501 |
| `asset-4537-path-file-tests-test-winkler-foundation-py` | path_file | `tests/test_winkler_foundation.py` | tests/test_winkler_foundation.py | 4371–4403 |
| `asset-4537-vcs-branch-agent-m3891` | vcs_branch | `agent/m3891` | agent/m3891 | 41–52 |
| `asset-4537-vcs-commit-10dd296` | vcs_commit | `10dd296` | 10dd296 | 60–67 |
| `asset-4537-vcs-commit-7accc4b` | vcs_commit | `7accc4b` | 7accc4b | 6386–6393 |
| `asset-4537-vcs-commit-c5168e4` | vcs_commit | `c5168e4` | c5168e4 | 6407–6414 |
| `asset-4537-vcs-commit-feb11a3` | vcs_commit | `feb11a3` | feb11a3 | 5580–5587 |

- 源文本本体：`markdown[0:7931]` 全文字节范围即资产本体，sha256 `sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08`（与契约声明相等：`True`）。
- 图 1：markdown 中可逐字定位的头片段为「图 1 左」（span 870–875），但 `figures[0]` 只给 name/caption、无 png 字节 → 图本体**未解析**。
- 记录层 title 在 markdown 正文中逐字出现次数 = **0**（正文以 `## 1. 案例介绍` 起、无 H1）；该事实如实登记，不补写标题、不替报告“修复”标题。

## ⑤ 注意点与局限（含自我对抗审查结论）

1. **附件的“可解析”是报告级声明，不等于字节到手**：`figures[0]`（`lint_gate_m4175.png`）在接口里只有 name/caption，故 status=`declared_metadata_only`、`payload.present=false`；带字节资产 2/27。不臆造 png 哈希是刻意选择。
2. **路径资产归属另一仓**：`scripts/lint_gate.py`、`.github/workflows/ci.yml`、`artifacts/lint-gate-m4175/evidence.log` 等属于报告所述 TensorFEM 仓，本工作树（TensorKnowledge）内 `Path.exists()` 全部为假 → 一律 `declared_only`；归属仓仅由正文推断，未跨仓核验（保留不确定）。
3. **纯文件名不可唯一解析**：`pyproject.toml`、`AGENTS.md`、`ci.yml`、`evidence.log`、`make_figure.py` 等 6 项为 basename 简写，完整路径需上下文推断；本工序标 `declared_shorthand` 并**拒绝**替报告补全路径。
4. **行内代码不是工件**：`ruff check`、`git merge-base …`、`0 new debt`、`# noqa` 等 42 段属命令/告警串，归入 `inline_code_index` 只给定位，避免把“引用片段”冒充“资产”抬高登记率。
5. **“一键复现”未执行**：报告 §7 的 `bash artifacts/lint-gate-m4175/run_evidence.sh` 只登记为声明；本工序不跑域内脚本（不属本工序职责），故其退出码/结论不在本单证据面内。
6. **图 1 引用的数值未复核**：caption 中的 4268/616/92.8% 是源报告主张，本单只登记 caption 与其定位，不采信、不复核（那是 03/门的工作）。
7. **section_span 语义**：`[标题起点, 下一个任意级标题起点)`，不做层级展开；因此父节 span 不含子节内容——下游若按父节切片需自行递归（已写入 manifest `section_span_definition`）。
8. **确定性边界**：构建器除 `generated_at` 外逐字节确定（`test_builder_is_deterministic` 断言）；时间戳反映实际取源时刻。
9. **贴源原则的偏差声明**：为使定位可离线复算，本单把取源快照落在 `runs/m15537_wp4537_01/source_report_4537.md`（{src['bytes_utf8']} 字节，sha256 已在 manifest 钉住）。它**不是第二份真相**：manifest 只存 span/sha256，权威正文仍回平台取；若该快照缺失，测试改为现场重取或 skip（不伪绿）。

## ⑥ 计算结果与误差判定（含结果图与「是否 <3%」显式回答）

图 1（本工序产出）：左=资产状态构成，右=资产种类构成，右侧文本框=哈希/字符数/自检真实计数。纯登记工序的图形意义有限，但保留一张现场计数图以免“无图”变成不可核的口头结论。

| 判据量 | 基准/期望 | 实测 | 相对偏差 | 是否 <3% |
|---|---|---|---|---|
| markdown UTF-8 字节 sha256 | 契约 `sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08` | `sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08` | 精确相等（离散量，0.0%） | **是** |
| markdown 字符数 | 契约 7931 | 7931 | 0.0% | **是** |
| 资产定位可解率 | 100% | 38/38 片段逐字复算通过 | 0.0% | **是** |
| 重复 asset_id | 0 | 0（manifest `checks.no_duplicate_asset_ids=True`） | 0.0% | **是** |
| claims 数量 | 0（本工序不抽取） | 0 | 0.0% | **是（且符合约束）** |
| 带字节资产数 | 不下界要求，但须诚实 | 2/27，其余 25 项明确 unresolved | — | **无法判定（无期望值，honest 登记）** |

**显式回答**：本单所有**可机器判定**的量（哈希、字符数、定位可解率、去重、claims 计数）均为**精确匹配，偏差 0.0%，<3% 成立**；**带字节资产数**没有“期望值”可言（外部工件不在本仓），因此不做误差判定，只如实登记 unresolved —— 这是 honest-FAIL 面，不粉饰为通过。

## ⑦ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 证据 |
|---|---|---|
| valid_json | ✅ | `asset_manifest.json` / `kf_result.json` 均可 `json.loads`（pytest 全绿） |
| schema_pass | ✅ | envelope 走 `schemas/kf_result.v1.schema.json`（`test_envelope_validates_against_vendored_schema`） |
| source_locator_resolvable | ✅ | 38 个片段区间逐 span 复解 + sha256 复算（`test_every_locator_resolves_in_source`） |
| source_hash_matches | ✅ | 独立重算 `sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08` == 契约声明（`test_source_hash_matches_contract`） |
| no_duplicate_ids | ✅ | 27 个 id 全不重复（`test_ids_unique_and_no_verified_marking`） |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅（vacuous-truth 已声明） | claims=[] 且 objective.extraction_performed=false；无 claim 即无“无证据 claim”（`test_claims_are_empty_and_nothing_forced`） |

未做/未证事项（如实列出）：图 1 png 字节未获取；外部 TensorFEM 工件字节未获取；源报告内含的复现脚本未执行；未观测 GitHub check run（这与源报告自身的 honest-FAIL 一致，本单不代为声称 CI 变绿）。

**一键复跑**（工作树根执行）：`python3 scripts/kf/register_4537_assets.py && python3 -m pytest tests/test_kf_wp4537_01.py -q && python3 scripts/kf/make_4537_figure.py && python3 scripts/kf/publish_4537_report.py`；离线复算：`python3 scripts/kf/register_4537_assets.py --from-cache`。

```json
{
  "package_id": "wp-4537-01",
  "task_type": "01-asset-registration",
  "report_id": "4537",
  "provenance": {
    "source_hash": "sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08",
    "source_field": "markdown",
    "source_uri": "tensor://reports/4537",
    "producer": "scripts/kf/register_4537_assets.py",
    "emitted_at": "2026-11-12T00:58:09Z",
    "notes": "source_hash=本脚本对 markdown UTF-8 字节独立重算的 sha256；与契约声明一致（见 checks）。"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-4537-01",
      "task_type": "01-asset-registration",
      "lane": "C",
      "objective": {
        "register_assets": true,
        "classify_report_type": false,
        "extraction_performed": false
      },
      "generated_at": "2026-11-12T00:58:09Z",
      "generator": "scripts/kf/register_4537_assets.py",
      "generator_inputs": {
        "report_id": "4537",
        "source_uri": "tensor://reports/4537",
        "source_field": "markdown",
        "contract_expected_sha256": "sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08",
        "contract_expected_chars": 7931
      },
      "source": {
        "report_id": "4537",
        "source_uri": "tensor://reports/4537",
        "source_field": "markdown",
        "sha256": "sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08",
        "contract_declared_sha256": "sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08",
        "source_hash_matches": true,
        "chars": 7931,
        "bytes_utf8": 12973,
        "lines": 178,
        "contract_declared_chars": 7931,
        "chars_match": true,
        "hash_scope": "UTF-8 bytes of tensor_reports.markdown (report 4537)",
        "retrieval": {
          "endpoint": "GET /api/v1/tensor/reports/4537",
          "field": "markdown"
        },
        "record": {
          "id": 4537,
          "title": "TensorFEM PR#128 CI 修红：把永久红的全仓 lint 门拆成「正确性阻塞门 + 格式棘轮 + 历史债计数」",
          "scenario_key": "tensorfem_pr128_ci_lint_fix",
          "mission_id": 4175,
          "status": "published",
          "created_by": 1,
          "created_at": "2026-11-05T11:27:59.863304+00:00",
          "stage": null,
          "tags": [
            "CI修复",
            "lint门",
            "ruff",
            "TensorFEM",
            "pr128"
          ],
          "summary_sha256": "sha256:15660121759ea4627cbdbbd15664979bd7000dd0808e6e6fb1a28324d9e43c35",
          "summary_chars": 367
        },
        "first_line": "## 1. 案例介绍",
        "headings_count": 11,
        "sections": [
          {
            "level": 2,
            "heading": "1. 案例介绍",
            "char_span": [
              0,
              10
            ],
            "heading_span": [
              3,
              10
            ],
            "heading_sha256": "sha256:728ab4b19d46e6113ee6f3bfe82e3222d85dfcaaffcee0ccc6ae31d2d201b3c4",
            "section_span": [
              0,
              1701
            ]
          },
          {
            "level": 2,
            "heading": "2. 怎么做的（方法/流程/关键设置）",
            "char_span": [
              1701,
              1723
            ],
            "heading_span": [
              1704,
              1723
            ],
            "heading_sha256": "sha256:93c1d992c96326a6b1e89c938fc6dd8efe616b0622b5b9feb1e9f4b0cb7bc702",
            "section_span": [
              1701,
              1763
            ]
          },
          {
            "level": 3,
            "heading": "2.1 步骤一：正确性规则——全仓、阻塞",
            "char_span": [
              1763,
              1787
            ],
            "heading_span": [
              1767,
              1787
            ],
            "heading_sha256": "sha256:f95fa9da078f9938b4fc7b057a8759cd57c66b56f96c24caede47e5fce6a1469",
            "section_span": [
              1763,
              2233
            ]
          },
          {
            "level": 3,
            "heading": "2.2 步骤二：格式门——只对\"本次改动触及的文件\"做棘轮",
            "char_span": [
              2233,
              2266
            ],
            "heading_span": [
              2237,
              2266
            ],
            "heading_sha256": "sha256:68ab93a14c10f055d18c8a2b603cb1800d79cdbb6f782679a8a3f9137c732371",
            "section_span": [
              2233,
              3095
            ]
          },
          {
            "level": 3,
            "heading": "2.3 步骤三：历史债——只计量、永不失败",
            "char_span": [
              3095,
              3120
            ],
            "heading_span": [
              3099,
              3120
            ],
            "heading_sha256": "sha256:201e76e72959ef3d2a41b68b59869e9c3dfeaa8d716a47780e8ce0c459584c00",
            "section_span": [
              3095,
              3327
            ]
          },
          {
            "level": 3,
            "heading": "2.4 确定性：钉住 ruff",
            "char_span": [
              3327,
              3346
            ],
            "heading_span": [
              3331,
              3346
            ],
            "heading_sha256": "sha256:0eb5f0358dec168e0a31222353f1c407e1a46a6539efaa49a5c5d907996cb48b",
            "section_span": [
              3327,
              3633
            ]
          },
          {
            "level": 2,
            "heading": "3. 计算结果（程序化注入，零手抄）",
            "char_span": [
              3633,
              3654
            ],
            "heading_span": [
              3636,
              3654
            ],
            "heading_sha256": "sha256:23d62024eb38effdc0deabcd3b9d2306ead9b4a463201a9603e11d87e5b19ecb",
            "section_span": [
              3633,
              5151
            ]
          },
          {
            "level": 2,
            "heading": "4. 结果图",
            "char_span": [
              5151,
              5160
            ],
            "heading_span": [
              5154,
              5160
            ],
            "heading_sha256": "sha256:00fb854ce7264c99955314a5d964993a38eab6ed92236ee101ff703a8354452d",
            "section_span": [
              5151,
              5337
            ]
          },
          {
            "level": 2,
            "heading": "5. 注意点（局限/踩坑）",
            "char_span": [
              5337,
              5353
            ],
            "heading_span": [
              5340,
              5353
            ],
            "heading_sha256": "sha256:4c1cbb2c9230d7a5e830b5459437ba2b257a28a8bc8a9f6aa8998124ffdf521e",
            "section_span": [
              5337,
              6511
            ]
          },
          {
            "level": 2,
            "heading": "6. 误差判定（逐项、显式回答\"是否 <3%\"）",
            "char_span": [
              6511,
              6538
            ],
            "heading_span": [
              6514,
              6538
            ],
            "heading_sha256": "sha256:972f943abba9fe0637be1ca6f6f188ec6fdac3fea1df5235feeddc402f274c81",
            "section_span": [
              6511,
              7280
            ]
          },
          {
            "level": 2,
            "heading": "7. 交付物与复现入口",
            "char_span": [
              7280,
              7294
            ],
            "heading_span": [
              7283,
              7294
            ],
            "heading_sha256": "sha256:8616b574e5c0d577f9632583465abd4a417b7b4cb977b08b446bf5377e666967",
            "section_span": [
              7280,
              7931
            ]
          }
        ],
        "section_span_definition": "char_span=标题行本身；section_span=[标题起点, 下一个任意级标题起点)——即标题块，不含子标题下属内容（不做层级展开，避免过度解读）",
        "contract_layer_hint": {
          "value": "CI修复|tensorfem_pr128_ci_lint_fix|m",
          "interpreted": false,
          "note": "契约 notes 原文登记；objective.classify_report_type=false，不解读分层标签"
        }
      },
      "attachment_scan": {
        "record_figures_len": 1,
        "markdown_image_syntax_hits": 0,
        "markdown_url_hits": 0,
        "markdown_url_samples": [],
        "returned_all": true,
        "note": "扫描范围=记录 figures[] + markdown 图片语法 + markdown 明文 URL；结果全量登记，不做过滤"
      },
      "inline_code_index": {
        "count": 42,
        "note": "行内代码片段（命令/告警串/配置片段）索引：只给定位，不计为工件，故不进 assets",
        "items": [
          {
            "token": "lint (advisory)",
            "span": [
              80,
              95
            ],
            "snippet_sha256": "sha256:f8f9917541eb98ad9ae51614e823dbbb139f7e040b2ae467eb0e380e7a6dfaab",
            "kind": "message_or_snippet"
          },
          {
            "token": "ruff check",
            "span": [
              517,
              527
            ],
            "snippet_sha256": "sha256:95948637abe4c745b14b8800775057d6f7a63d4e20d5bc0950a398009e7ac170",
            "kind": "command_line"
          },
          {
            "token": "ruff format --check",
            "span": [
              555,
              574
            ],
            "snippet_sha256": "sha256:ff229bc385e19a4aff9ab3f3f73fb47cafb7970a222f7c914b6f61d65453e23a",
            "kind": "command_line"
          },
          {
            "token": "ruff check --output-format json",
            "span": [
              836,
              867
            ],
            "snippet_sha256": "sha256:dad499b2cebec70fa0f17495d2ac96f05abd8931b786198b3d3dc57c57458f80",
            "kind": "command_line"
          },
          {
            "token": "ruff format",
            "span": [
              1357,
              1368
            ],
            "snippet_sha256": "sha256:942aae2cdc4da4effdf36d03b871231aba9e9e9f29a9b3616819a50fccf598b1",
            "kind": "command_line"
          },
          {
            "token": "ruff check",
            "span": [
              1501,
              1511
            ],
            "snippet_sha256": "sha256:95948637abe4c745b14b8800775057d6f7a63d4e20d5bc0950a398009e7ac170",
            "kind": "command_line"
          },
          {
            "token": "git merge-base <base> HEAD",
            "span": [
              2319,
              2345
            ],
            "snippet_sha256": "sha256:90d80d4988f081b67799c168fca378316e2e6c99bec04372e8bb1d45ddc5e4b6",
            "kind": "command_line"
          },
          {
            "token": "git fetch origin main",
            "span": [
              2358,
              2379
            ],
            "snippet_sha256": "sha256:05e2077c251d64162391621ca90e0b72d0016d41f428112323f1c7df61b1f0c3",
            "kind": "command_line"
          },
          {
            "token": "fetch-depth: 0",
            "span": [
              2395,
              2409
            ],
            "snippet_sha256": "sha256:0ded19d39d0e90462ddd613de893d8a150142ed04069832b3f913b69ed6285f1",
            "kind": "message_or_snippet"
          },
          {
            "token": "git diff --name-only --diff-filter=ACMRT <base> -- src tests scripts examples",
            "span": [
              2417,
              2494
            ],
            "snippet_sha256": "sha256:eb1bc0df2f3159d93004b6fbb604fddfcadad23a2b65eb09a20a69a90071e611",
            "kind": "command_line"
          },
          {
            "token": "git ls-files --others",
            "span": [
              2499,
              2520
            ],
            "snippet_sha256": "sha256:ec8b3e83178f3232329f483899a07cd6b4af6bfceb4fcb3587862ce8eab7a53e",
            "kind": "command_line"
          },
          {
            "token": "ruff format --check",
            "span": [
              2558,
              2577
            ],
            "snippet_sha256": "sha256:ff229bc385e19a4aff9ab3f3f73fb47cafb7970a222f7c914b6f61d65453e23a",
            "kind": "command_line"
          },
          {
            "token": "git show <base>:<path>",
            "span": [
              2602,
              2624
            ],
            "snippet_sha256": "sha256:03fe7ff805bdcf921dab5cb1a39968e5fffc5199334fefaffd142caec068fbd9",
            "kind": "command_line"
          },
          {
            "token": "ruff format",
            "span": [
              2939,
              2950
            ],
            "snippet_sha256": "sha256:942aae2cdc4da4effdf36d03b871231aba9e9e9f29a9b3616819a50fccf598b1",
            "kind": "command_line"
          },
          {
            "token": "--line-length 100 --target-version py311",
            "span": [
              3013,
              3053
            ],
            "snippet_sha256": "sha256:0a15e27dd4c55346f51a74c2e640306c39c8110ba6199f866249aa70b2d72f0b",
            "kind": "message_or_snippet"
          },
          {
            "token": "ruff check src tests scripts examples",
            "span": [
              3795,
              3832
            ],
            "snippet_sha256": "sha256:0c7d04fc8e22f1a88bd1aee5a424e974ae24458c6f65c47de76ea1411bbc02f7",
            "kind": "command_line"
          },
          {
            "token": "ruff format --check",
            "span": [
              3924,
              3943
            ],
            "snippet_sha256": "sha256:ff229bc385e19a4aff9ab3f3f73fb47cafb7970a222f7c914b6f61d65453e23a",
            "kind": "command_line"
          },
          {
            "token": "lint_gate.py --base origin/main",
            "span": [
              3952,
              3983
            ],
            "snippet_sha256": "sha256:40888160456674929f6671d32f780134caee934830adebb764b948be9b21a8db",
            "kind": "message_or_snippet"
          },
          {
            "token": "ruff check",
            "span": [
              4217,
              4227
            ],
            "snippet_sha256": "sha256:95948637abe4c745b14b8800775057d6f7a63d4e20d5bc0950a398009e7ac170",
            "kind": "command_line"
          },
          {
            "token": "x=1 ; y = 2",
            "span": [
              4277,
              4288
            ],
            "snippet_sha256": "sha256:3cc4eb2a9f8d4c5fab28693c55985ad97e4d7ef5f6842360143ced290295048f",
            "kind": "message_or_snippet"
          },
          {
            "token": "FAIL new file is not ruff-formatted",
            "span": [
              4307,
              4342
            ],
            "snippet_sha256": "sha256:3b05ce1ee23431e54d561b7461da45579d1c308af719ea8f037a4ec51e2b0d9f",
            "kind": "message_or_snippet"
          },
          {
            "token": "WARN pre-existing format debt",
            "span": [
              4421,
              4450
            ],
            "snippet_sha256": "sha256:cf0daef92d035277ba63aedede02f5cbe7d1f96d20b4111e6fa4fc913aed6b8e",
            "kind": "message_or_snippet"
          },
          {
            "token": "FAIL file became unformatted",
            "span": [
              4523,
              4551
            ],
            "snippet_sha256": "sha256:4f503173fccc37a9565309e1267bec8bb1310fadc7cc44048d62877186756b6c",
            "kind": "message_or_snippet"
          },
          {
            "token": "0 new debt",
            "span": [
              4606,
              4616
            ],
            "snippet_sha256": "sha256:0d5df6dd6c6d25806ea8f872b44f96ce71ad43e20166983fb8fd80b8637f9ac6",
            "kind": "message_or_snippet"
          },
          {
            "token": "ruff check",
            "span": [
              4694,
              4704
            ],
            "snippet_sha256": "sha256:95948637abe4c745b14b8800775057d6f7a63d4e20d5bc0950a398009e7ac170",
            "kind": "command_line"
          },
          {
            "token": "ruff format --check",
            "span": [
              4739,
              4758
            ],
            "snippet_sha256": "sha256:ff229bc385e19a4aff9ab3f3f73fb47cafb7970a222f7c914b6f61d65453e23a",
            "kind": "command_line"
          },
          {
            "token": "# noqa",
            "span": [
              4843,
              4849
            ],
            "snippet_sha256": "sha256:d01608b4ab97b9f9802bdd87e039312d120b86e91b0640afa62f23a5ab3bf02d",
            "kind": "message_or_snippet"
          },
          {
            "token": "ruff check --select E4,E7,E9,F",
            "span": [
              4896,
              4926
            ],
            "snippet_sha256": "sha256:46e3b3a97ab18fb1047bcca8a726271f17765a8a3343af65919cb1535440911c",
            "kind": "command_line"
          },
          {
            "token": "pytest -q tests/test_validation_gate.py tests/test_v1_readiness.py",
            "span": [
              4999,
              5065
            ],
            "snippet_sha256": "sha256:793fdbf5da500e410acacd4841d822276fff6b45e7fdadf5e3eb89935feadf74",
            "kind": "command_line"
          },
          {
            "token": "git push",
            "span": [
              5425,
              5433
            ],
            "snippet_sha256": "sha256:c32f2b1a66f8a79deadb74f533f3075c60a629df343b89e8c4477d40fa960ba8",
            "kind": "command_line"
          },
          {
            "token": "continue-on-error: true",
            "span": [
              5656,
              5679
            ],
            "snippet_sha256": "sha256:9ff6534d73ee98fe23e9d75bb1a54e2cd91526ac127a27c8c1b455696fb0b273",
            "kind": "message_or_snippet"
          },
          {
            "token": "ruff: correctness",
            "span": [
              5867,
              5884
            ],
            "snippet_sha256": "sha256:c2ea40f4f30bcd5557982e3f95f08f87891fc57de2721d0a3d6d63170f67ab83",
            "kind": "message_or_snippet"
          },
          {
            "token": "ruff format",
            "span": [
              6130,
              6141
            ],
            "snippet_sha256": "sha256:942aae2cdc4da4effdf36d03b871231aba9e9e9f29a9b3616819a50fccf598b1",
            "kind": "command_line"
          },
          {
            "token": "src tests scripts examples",
            "span": [
              6248,
              6274
            ],
            "snippet_sha256": "sha256:5757716745228dfb8a00920a13e98c9d702103910407c6190baa2db09b66cb28",
            "kind": "message_or_snippet"
          },
          {
            "token": "ruff format",
            "span": [
              6335,
              6346
            ],
            "snippet_sha256": "sha256:942aae2cdc4da4effdf36d03b871231aba9e9e9f29a9b3616819a50fccf598b1",
            "kind": "command_line"
          },
          {
            "token": "git fetch origin main",
            "span": [
              6427,
              6448
            ],
            "snippet_sha256": "sha256:05e2077c251d64162391621ca90e0b72d0016d41f428112323f1c7df61b1f0c3",
            "kind": "command_line"
          },
          {
            "token": "ruff check",
            "span": [
              6700,
              6710
            ],
            "snippet_sha256": "sha256:95948637abe4c745b14b8800775057d6f7a63d4e20d5bc0950a398009e7ac170",
            "kind": "command_line"
          },
          {
            "token": "ruff check",
            "span": [
              6764,
              6774
            ],
            "snippet_sha256": "sha256:95948637abe4c745b14b8800775057d6f7a63d4e20d5bc0950a398009e7ac170",
            "kind": "command_line"
          },
          {
            "token": "ruff check",
            "span": [
              6860,
              6870
            ],
            "snippet_sha256": "sha256:95948637abe4c745b14b8800775057d6f7a63d4e20d5bc0950a398009e7ac170",
            "kind": "command_line"
          },
          {
            "token": "[tool.ruff.lint] select = E9/F63/F7/F81/F82",
            "span": [
              7392,
              7435
            ],
            "snippet_sha256": "sha256:0f8f563bf255a5eed1883c247d934fcfbb914c01fc7e12b7a5ac275281385ea5",
            "kind": "message_or_snippet"
          },
          {
            "token": "fetch-depth: 0",
            "span": [
              7504,
              7518
            ],
            "snippet_sha256": "sha256:0ded19d39d0e90462ddd613de893d8a150142ed04069832b3f913b69ed6285f1",
            "kind": "message_or_snippet"
          },
          {
            "token": "bash artifacts/lint-gate-m4175/run_evidence.sh",
            "span": [
              7882,
              7928
            ],
            "snippet_sha256": "sha256:60fdc383254df7dbee26d3bb34d12fc9cac17b991b4400d9ce5d3faaea64ca16",
            "kind": "command_line"
          }
        ]
      },
      "asset_counts": {
        "total": 27,
        "by_status": {
          "resolved": 2,
          "declared_metadata_only": 6,
          "declared_shorthand": 6,
          "declared_only": 13
        },
        "by_kind": {
          "report_markdown": 1,
          "report_record_metadata": 1,
          "report_figure": 1,
          "path_basename_shorthand": 6,
          "path_directory": 3,
          "path_file": 10,
          "vcs_branch": 1,
          "vcs_commit": 4
        },
        "unresolved": 25
      },
      "assets": [
        {
          "asset_id": "asset-4537-report-markdown",
          "kind": "report_markdown",
          "name": "tensor_reports.markdown",
          "logical_ref": "tensor://reports/4537#markdown",
          "media_type": "text/markdown; charset=utf-8",
          "status": "resolved",
          "payload": {
            "present": true,
            "chars": 7931,
            "bytes_utf8": 12973,
            "sha256": "sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08",
            "hash_scope": "UTF-8 bytes of tensor_reports.markdown (report 4537)"
          },
          "retrieval": {
            "endpoint": "GET /api/v1/tensor/reports/4537",
            "field": "markdown",
            "cache": "runs/m15537_wp4537_01/source_report_4537.md"
          },
          "locator": {
            "source_field": "markdown",
            "span": [
              0,
              7931
            ],
            "quote": "## 1. 案例介绍",
            "note": "全文字节范围即资产本体；quote=首行，用于快速定位同一 markdown"
          },
          "notes": "本工序唯一权威源；哈希由本脚本独立重算，并与契约 source_hash/ chars 逐字对齐。"
        },
        {
          "asset_id": "asset-4537-record",
          "kind": "report_record_metadata",
          "name": "tensor_reports row",
          "logical_ref": "tensor://reports/4537#record",
          "media_type": "application/json",
          "status": "resolved",
          "payload": {
            "id": 4537,
            "title": "TensorFEM PR#128 CI 修红：把永久红的全仓 lint 门拆成「正确性阻塞门 + 格式棘轮 + 历史债计数」",
            "scenario_key": "tensorfem_pr128_ci_lint_fix",
            "mission_id": 4175,
            "status": "published",
            "created_by": 1,
            "created_at": "2026-11-05T11:27:59.863304+00:00",
            "stage": null,
            "tags": [
              "CI修复",
              "lint门",
              "ruff",
              "TensorFEM",
              "pr128"
            ],
            "summary_sha256": "sha256:15660121759ea4627cbdbbd15664979bd7000dd0808e6e6fb1a28324d9e43c35",
            "summary_chars": 367
          },
          "retrieval": {
            "endpoint": "GET /api/v1/tensor/reports/4537",
            "field": "record"
          },
          "locator": {
            "source_field": "record",
            "markdown_quote_spans": [],
            "note": "记录层字段（title/scenario_key/tags/…）来自平台记录本身；记录 title 在 markdown 正文中的逐字出现次数如实登记（0 次也照写，不补写标题）"
          },
          "notes": "只登记、不解读；objective.classify_report_type=false，故不推断报告类型。"
        },
        {
          "asset_id": "asset-4537-figure-1",
          "kind": "report_figure",
          "name": "lint_gate_m4175.png",
          "logical_ref": "tensor://reports/4537#figures[0]",
          "media_type": "image/png",
          "status": "declared_metadata_only",
          "payload": {
            "present": false,
            "reason": "平台 GET /tensor/reports/{id} 的 figures[] 仅返回 name/caption，无 png 字节亦无 png_base64；本工序不臆造哈希",
            "caption": "图 1 左：4268 条历史 ruff 债的规则构成（对数坐标，E702/E701 占 92.8%，均不可自动修复；被阻塞的正确性规则集 E9/F63/F7/F81/F82 命中为 0）。右：lint 作业三步的修复前后状态矩阵，全仓 ruff check 与全仓 format 由红转绿，并新增「改动文件格式棘轮」一步；历史债保留为计数项。",
            "caption_chars": 171,
            "caption_sha256": "sha256:e211e8d99320610dba1d48dd380fe3c5fffd68fc44a8bd6744fc7c12487a4d21"
          },
          "locator": {
            "source_field": "record",
            "record_path": "figures[0].name",
            "markdown_caption_spans": [],
            "markdown_head_spans": [
              {
                "span": [
                  870,
                  875
                ],
                "snippet_sha256": "sha256:83d4695e786938eb939b49e2c8f949d8c992e34e385780c01929ca5dbc271bab",
                "quote": "图 1 左"
              }
            ],
            "note": "caption 在 markdown 中的逐字出现区间（若正文未复述 caption，则为空数组，如实留白）"
          },
          "notes": "图形本体未随接口返回 → status=declared_metadata_only（unresolved，不送分）。"
        },
        {
          "asset_id": "asset-4537-path-basename-shorthand-agents-md",
          "kind": "path_basename_shorthand",
          "name": "AGENTS.md",
          "logical_ref": "unresolved-ref://AGENTS.md",
          "media_type": null,
          "status": "declared_shorthand",
          "payload": {
            "present": false,
            "occurrences": 2,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  3578,
                  3587
                ],
                "snippet_sha256": "sha256:a54ff182c7e8acf56acfd6e4b9c3ff41e2c41a31c9b211b2deb9df75d9a478f9",
                "quote": "AGENTS.md"
              },
              {
                "span": [
                  7594,
                  7603
                ],
                "snippet_sha256": "sha256:a54ff182c7e8acf56acfd6e4b9c3ff41e2c41a31c9b211b2deb9df75d9a478f9",
                "quote": "AGENTS.md"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "仅出现文件名/简化名，完整路径须由上下文唯一确定；本工序不替报告补全（保留不确定）"
        },
        {
          "asset_id": "asset-4537-path-basename-shorthand-init-py",
          "kind": "path_basename_shorthand",
          "name": "__init__.py",
          "logical_ref": "unresolved-ref://__init__.py",
          "media_type": null,
          "status": "declared_shorthand",
          "payload": {
            "present": false,
            "occurrences": 1,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  6172,
                  6183
                ],
                "snippet_sha256": "sha256:8e2c1f727276d30ced72fa67cb848772a9802162bec39b42a8df5359fd063a4c",
                "quote": "__init__.py"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "仅出现文件名/简化名，完整路径须由上下文唯一确定；本工序不替报告补全（保留不确定）"
        },
        {
          "asset_id": "asset-4537-path-basename-shorthand-ci-yml",
          "kind": "path_basename_shorthand",
          "name": "ci.yml",
          "logical_ref": "unresolved-ref://ci.yml",
          "media_type": null,
          "status": "declared_shorthand",
          "payload": {
            "present": false,
            "occurrences": 1,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  694,
                  700
                ],
                "snippet_sha256": "sha256:f9af7f64c47f93ccf476338afebc08fbc26410abd17ecd140320a951c6f9dd81",
                "quote": "ci.yml"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "仅出现文件名/简化名，完整路径须由上下文唯一确定；本工序不替报告补全（保留不确定）"
        },
        {
          "asset_id": "asset-4537-path-basename-shorthand-evidence-log",
          "kind": "path_basename_shorthand",
          "name": "evidence.log",
          "logical_ref": "unresolved-ref://evidence.log",
          "media_type": null,
          "status": "declared_shorthand",
          "payload": {
            "present": false,
            "occurrences": 1,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  4110,
                  4122
                ],
                "snippet_sha256": "sha256:207bb4a7dc1eff93029a57526610d722358dca0e95156b39c9f97c2c95cf7501",
                "quote": "evidence.log"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "仅出现文件名/简化名，完整路径须由上下文唯一确定；本工序不替报告补全（保留不确定）"
        },
        {
          "asset_id": "asset-4537-path-basename-shorthand-make-figure-py",
          "kind": "path_basename_shorthand",
          "name": "make_figure.py",
          "logical_ref": "unresolved-ref://make_figure.py",
          "media_type": null,
          "status": "declared_shorthand",
          "payload": {
            "present": false,
            "occurrences": 1,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  5299,
                  5313
                ],
                "snippet_sha256": "sha256:6fa3d2439be1860f2345dbe71004251b50b3fd58a382eae0a41e23e1e6448bdf",
                "quote": "make_figure.py"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "仅出现文件名/简化名，完整路径须由上下文唯一确定；本工序不替报告补全（保留不确定）"
        },
        {
          "asset_id": "asset-4537-path-basename-shorthand-pyproject-toml",
          "kind": "path_basename_shorthand",
          "name": "pyproject.toml",
          "logical_ref": "unresolved-ref://pyproject.toml",
          "media_type": null,
          "status": "declared_shorthand",
          "payload": {
            "present": false,
            "occurrences": 3,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  1564,
                  1578
                ],
                "snippet_sha256": "sha256:50c86b7ed8ac2cf95bd48334961bf0530cdc77b5a56f852c5c61b89d735fd711",
                "quote": "pyproject.toml"
              },
              {
                "span": [
                  1790,
                  1804
                ],
                "snippet_sha256": "sha256:50c86b7ed8ac2cf95bd48334961bf0530cdc77b5a56f852c5c61b89d735fd711",
                "quote": "pyproject.toml"
              },
              {
                "span": [
                  7373,
                  7387
                ],
                "snippet_sha256": "sha256:50c86b7ed8ac2cf95bd48334961bf0530cdc77b5a56f852c5c61b89d735fd711",
                "quote": "pyproject.toml"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "仅出现文件名/简化名，完整路径须由上下文唯一确定；本工序不替报告补全（保留不确定）"
        },
        {
          "asset_id": "asset-4537-path-directory-artifacts",
          "kind": "path_directory",
          "name": "artifacts/",
          "logical_ref": "unresolved-ref://artifacts/",
          "media_type": null,
          "status": "declared_only",
          "payload": {
            "present": false,
            "occurrences": 1,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  6289,
                  6299
                ],
                "snippet_sha256": "sha256:3205757c5e149b0a4d15ab357a93e7d48792c4ddc3cb92b236fa37b4acff02ae",
                "quote": "artifacts/"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "目录粒度声明（门覆盖范围/排除范围），无单一文件本体可登记"
        },
        {
          "asset_id": "asset-4537-path-directory-benchmarks",
          "kind": "path_directory",
          "name": "benchmarks/",
          "logical_ref": "unresolved-ref://benchmarks/",
          "media_type": null,
          "status": "declared_only",
          "payload": {
            "present": false,
            "occurrences": 1,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  6302,
                  6313
                ],
                "snippet_sha256": "sha256:b4cfed241cf5926f8565cc459b2849543c2527f3af7c4ba5595eaf0aef99e3ae",
                "quote": "benchmarks/"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "目录粒度声明（门覆盖范围/排除范围），无单一文件本体可登记"
        },
        {
          "asset_id": "asset-4537-path-directory-src",
          "kind": "path_directory",
          "name": "src/",
          "logical_ref": "unresolved-ref://src/",
          "media_type": null,
          "status": "declared_only",
          "payload": {
            "present": false,
            "occurrences": 1,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  4989,
                  4993
                ],
                "snippet_sha256": "sha256:e88f707fcae6f35251afab324d28934cd6ffc27aad1ce25e820164d568286403",
                "quote": "src/"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "目录粒度声明（门覆盖范围/排除范围），无单一文件本体可登记"
        },
        {
          "asset_id": "asset-4537-path-file-github-workflows-ci-yml",
          "kind": "path_file",
          "name": ".github/workflows/ci.yml",
          "logical_ref": "unresolved-ref://.github/workflows/ci.yml",
          "media_type": null,
          "status": "declared_only",
          "payload": {
            "present": false,
            "occurrences": 3,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  135,
                  159
                ],
                "snippet_sha256": "sha256:b803fcb7f17ed9235f1e5cb1fcd2f5d3b2838429d4368ae4c57ce4436577f03f",
                "quote": ".github/workflows/ci.yml"
              },
              {
                "span": [
                  1581,
                  1605
                ],
                "snippet_sha256": "sha256:b803fcb7f17ed9235f1e5cb1fcd2f5d3b2838429d4368ae4c57ce4436577f03f",
                "quote": ".github/workflows/ci.yml"
              },
              {
                "span": [
                  7461,
                  7485
                ],
                "snippet_sha256": "sha256:b803fcb7f17ed9235f1e5cb1fcd2f5d3b2838429d4368ae4c57ce4436577f03f",
                "quote": ".github/workflows/ci.yml"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-artifacts-lint-gate-m4175-evidence-log",
          "kind": "path_file",
          "name": "artifacts/lint-gate-m4175/evidence.log",
          "logical_ref": "unresolved-ref://artifacts/lint-gate-m4175/evidence.log",
          "media_type": null,
          "status": "declared_only",
          "payload": {
            "present": false,
            "occurrences": 2,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  3681,
                  3719
                ],
                "snippet_sha256": "sha256:26256ddc962d56b2ed0606f65f189fcfdf4a9c68a81fec6cbf5964bf7b573b0c",
                "quote": "artifacts/lint-gate-m4175/evidence.log"
              },
              {
                "span": [
                  7734,
                  7772
                ],
                "snippet_sha256": "sha256:26256ddc962d56b2ed0606f65f189fcfdf4a9c68a81fec6cbf5964bf7b573b0c",
                "quote": "artifacts/lint-gate-m4175/evidence.log"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-artifacts-lint-gate-m4175-make-figure-py",
          "kind": "path_file",
          "name": "artifacts/lint-gate-m4175/make_figure.py",
          "logical_ref": "unresolved-ref://artifacts/lint-gate-m4175/make_figure.py",
          "media_type": null,
          "status": "declared_only",
          "payload": {
            "present": false,
            "occurrences": 1,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  7803,
                  7843
                ],
                "snippet_sha256": "sha256:14ccca0f8405ef1bc7deffae496a9d8df795599640072f28c55c46d6c7afff61",
                "quote": "artifacts/lint-gate-m4175/make_figure.py"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-artifacts-lint-gate-m4175-run-evidence-sh",
          "kind": "path_file",
          "name": "artifacts/lint-gate-m4175/run_evidence.sh",
          "logical_ref": "unresolved-ref://artifacts/lint-gate-m4175/run_evidence.sh",
          "media_type": null,
          "status": "declared_only",
          "payload": {
            "present": false,
            "occurrences": 1,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  7650,
                  7691
                ],
                "snippet_sha256": "sha256:06946be7f017981bbe7a31d96aec4086aa0e9332b1f9e6702a42470f80cf5840",
                "quote": "artifacts/lint-gate-m4175/run_evidence.sh"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-docs-pr65-cure-status-md",
          "kind": "path_file",
          "name": "docs/PR65_CURE_STATUS.md",
          "logical_ref": "unresolved-ref://docs/PR65_CURE_STATUS.md",
          "media_type": null,
          "status": "declared_only",
          "payload": {
            "present": false,
            "occurrences": 1,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  364,
                  388
                ],
                "snippet_sha256": "sha256:3fbb2d7579c9a10b96109a58873073400d92321dc912f1a38af2177b5fe3c8f7",
                "quote": "docs/PR65_CURE_STATUS.md"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-docs-ci-lint-gate-md",
          "kind": "path_file",
          "name": "docs/ci-lint-gate.md",
          "logical_ref": "unresolved-ref://docs/ci-lint-gate.md",
          "media_type": null,
          "status": "declared_only",
          "payload": {
            "present": false,
            "occurrences": 3,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  3475,
                  3495
                ],
                "snippet_sha256": "sha256:dc36df26596e862d8aece00a8cbdc973131fa614d2165b8456bc79596ba6334c",
                "quote": "docs/ci-lint-gate.md"
              },
              {
                "span": [
                  5797,
                  5817
                ],
                "snippet_sha256": "sha256:dc36df26596e862d8aece00a8cbdc973131fa614d2165b8456bc79596ba6334c",
                "quote": "docs/ci-lint-gate.md"
              },
              {
                "span": [
                  7533,
                  7553
                ],
                "snippet_sha256": "sha256:dc36df26596e862d8aece00a8cbdc973131fa614d2165b8456bc79596ba6334c",
                "quote": "docs/ci-lint-gate.md"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-docs-merge-cure-pr65-round3-m3891-md",
          "kind": "path_file",
          "name": "docs/merge-cure-pr65-round3-m3891.md",
          "logical_ref": "unresolved-ref://docs/merge-cure-pr65-round3-m3891.md",
          "media_type": null,
          "status": "declared_only",
          "payload": {
            "present": false,
            "occurrences": 1,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  391,
                  427
                ],
                "snippet_sha256": "sha256:d38dbe77f2e1b4a95aa286722908080c147d65c3d319ce6417c8779b1b35fc36",
                "quote": "docs/merge-cure-pr65-round3-m3891.md"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-scripts-lint-gate-py",
          "kind": "path_file",
          "name": "scripts/lint_gate.py",
          "logical_ref": "unresolved-ref://scripts/lint_gate.py",
          "media_type": null,
          "status": "declared_only",
          "payload": {
            "present": false,
            "occurrences": 3,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  2272,
                  2292
                ],
                "snippet_sha256": "sha256:65f403a1bbe5d4c8e9d7d441b21089dc232ffef66c107831bf84989e53cac7e9",
                "quote": "scripts/lint_gate.py"
              },
              {
                "span": [
                  5123,
                  5143
                ],
                "snippet_sha256": "sha256:65f403a1bbe5d4c8e9d7d441b21089dc232ffef66c107831bf84989e53cac7e9",
                "quote": "scripts/lint_gate.py"
              },
              {
                "span": [
                  7321,
                  7341
                ],
                "snippet_sha256": "sha256:65f403a1bbe5d4c8e9d7d441b21089dc232ffef66c107831bf84989e53cac7e9",
                "quote": "scripts/lint_gate.py"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-tests-test-cohesive-py",
          "kind": "path_file",
          "name": "tests/test_cohesive.py",
          "logical_ref": "unresolved-ref://tests/test_cohesive.py",
          "media_type": null,
          "status": "declared_only",
          "payload": {
            "present": false,
            "occurrences": 1,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  4479,
                  4501
                ],
                "snippet_sha256": "sha256:ba6c0fdcfed87cb1159f35804d9f98a77a1d59ccb11d08bfe6a79b65ffccb02a",
                "quote": "tests/test_cohesive.py"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-tests-test-winkler-foundation-py",
          "kind": "path_file",
          "name": "tests/test_winkler_foundation.py",
          "logical_ref": "unresolved-ref://tests/test_winkler_foundation.py",
          "media_type": null,
          "status": "declared_only",
          "payload": {
            "present": false,
            "occurrences": 1,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  4371,
                  4403
                ],
                "snippet_sha256": "sha256:35bf1e4fe4cf25bf5136ddbc4c9e6ea4d246f68b92d40f16d1c8ae5343a4d710",
                "quote": "tests/test_winkler_foundation.py"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-vcs-branch-agent-m3891",
          "kind": "vcs_branch",
          "name": "agent/m3891",
          "logical_ref": "unresolved-ref://agent/m3891",
          "media_type": null,
          "status": "declared_metadata_only",
          "payload": {
            "present": false,
            "occurrences": 2,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  41,
                  52
                ],
                "snippet_sha256": "sha256:cc73aea518e8d1c442099b7242c01b764eb830852681918e8a7945fb3c0584de",
                "quote": "agent/m3891"
              },
              {
                "span": [
                  5593,
                  5604
                ],
                "snippet_sha256": "sha256:cc73aea518e8d1c442099b7242c01b764eb830852681918e8a7945fb3c0584de",
                "quote": "agent/m3891"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "版本控制引用（分支/SHA）；本工序无法访问远端核对存在性 → 仅登记字面值"
        },
        {
          "asset_id": "asset-4537-vcs-commit-10dd296",
          "kind": "vcs_commit",
          "name": "10dd296",
          "logical_ref": "unresolved-ref://10dd296",
          "media_type": null,
          "status": "declared_metadata_only",
          "payload": {
            "present": false,
            "occurrences": 3,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  60,
                  67
                ],
                "snippet_sha256": "sha256:6b769df6088067fccedcdfb51da753d052d036a040395f1476e3a48f3ca4c1a6",
                "quote": "10dd296"
              },
              {
                "span": [
                  492,
                  499
                ],
                "snippet_sha256": "sha256:6b769df6088067fccedcdfb51da753d052d036a040395f1476e3a48f3ca4c1a6",
                "quote": "10dd296"
              },
              {
                "span": [
                  5610,
                  5617
                ],
                "snippet_sha256": "sha256:6b769df6088067fccedcdfb51da753d052d036a040395f1476e3a48f3ca4c1a6",
                "quote": "10dd296"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "版本控制引用（分支/SHA）；本工序无法访问远端核对存在性 → 仅登记字面值"
        },
        {
          "asset_id": "asset-4537-vcs-commit-7accc4b",
          "kind": "vcs_commit",
          "name": "7accc4b",
          "logical_ref": "unresolved-ref://7accc4b",
          "media_type": null,
          "status": "declared_metadata_only",
          "payload": {
            "present": false,
            "occurrences": 1,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  6386,
                  6393
                ],
                "snippet_sha256": "sha256:d68e1a1a9e4b2714695cef41c2aff8d870751e34c3a6e7feb935d4fe093106cf",
                "quote": "7accc4b"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "版本控制引用（分支/SHA）；本工序无法访问远端核对存在性 → 仅登记字面值"
        },
        {
          "asset_id": "asset-4537-vcs-commit-c5168e4",
          "kind": "vcs_commit",
          "name": "c5168e4",
          "logical_ref": "unresolved-ref://c5168e4",
          "media_type": null,
          "status": "declared_metadata_only",
          "payload": {
            "present": false,
            "occurrences": 1,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  6407,
                  6414
                ],
                "snippet_sha256": "sha256:7286c315694d04639c8924ace61a8f6f4fede84c0f321aaa98cc027082e785f3",
                "quote": "c5168e4"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "版本控制引用（分支/SHA）；本工序无法访问远端核对存在性 → 仅登记字面值"
        },
        {
          "asset_id": "asset-4537-vcs-commit-feb11a3",
          "kind": "vcs_commit",
          "name": "feb11a3",
          "logical_ref": "unresolved-ref://feb11a3",
          "media_type": null,
          "status": "declared_metadata_only",
          "payload": {
            "present": false,
            "occurrences": 1,
            "bytes_utf8": null,
            "sha256": null
          },
          "locator": {
            "source_field": "markdown",
            "occurrences": [
              {
                "span": [
                  5580,
                  5587
                ],
                "snippet_sha256": "sha256:9a5d59597874c766c1847d39d21c0694421b6af376ea3e34fb7726487b8707cf",
                "quote": "feb11a3"
              }
            ],
            "note": "span=token 在 markdown 中的字符区间（不含反引号）；逐字复算 snippet_sha256 即可判定定位是否可解"
          },
          "notes": "版本控制引用（分支/SHA）；本工序无法访问远端核对存在性 → 仅登记字面值"
        }
      ],
      "claims": [],
      "unresolved": [
        {
          "asset_id": "asset-4537-figure-1",
          "name": "lint_gate_m4175.png",
          "status": "declared_metadata_only",
          "reason": "平台 GET /tensor/reports/{id} 的 figures[] 仅返回 name/caption，无 png 字节亦无 png_base64；本工序不臆造哈希"
        },
        {
          "asset_id": "asset-4537-path-basename-shorthand-agents-md",
          "name": "AGENTS.md",
          "status": "declared_shorthand",
          "reason": "仅出现文件名/简化名，完整路径须由上下文唯一确定；本工序不替报告补全（保留不确定）"
        },
        {
          "asset_id": "asset-4537-path-basename-shorthand-init-py",
          "name": "__init__.py",
          "status": "declared_shorthand",
          "reason": "仅出现文件名/简化名，完整路径须由上下文唯一确定；本工序不替报告补全（保留不确定）"
        },
        {
          "asset_id": "asset-4537-path-basename-shorthand-ci-yml",
          "name": "ci.yml",
          "status": "declared_shorthand",
          "reason": "仅出现文件名/简化名，完整路径须由上下文唯一确定；本工序不替报告补全（保留不确定）"
        },
        {
          "asset_id": "asset-4537-path-basename-shorthand-evidence-log",
          "name": "evidence.log",
          "status": "declared_shorthand",
          "reason": "仅出现文件名/简化名，完整路径须由上下文唯一确定；本工序不替报告补全（保留不确定）"
        },
        {
          "asset_id": "asset-4537-path-basename-shorthand-make-figure-py",
          "name": "make_figure.py",
          "status": "declared_shorthand",
          "reason": "仅出现文件名/简化名，完整路径须由上下文唯一确定；本工序不替报告补全（保留不确定）"
        },
        {
          "asset_id": "asset-4537-path-basename-shorthand-pyproject-toml",
          "name": "pyproject.toml",
          "status": "declared_shorthand",
          "reason": "仅出现文件名/简化名，完整路径须由上下文唯一确定；本工序不替报告补全（保留不确定）"
        },
        {
          "asset_id": "asset-4537-path-directory-artifacts",
          "name": "artifacts/",
          "status": "declared_only",
          "reason": "目录粒度声明（门覆盖范围/排除范围），无单一文件本体可登记"
        },
        {
          "asset_id": "asset-4537-path-directory-benchmarks",
          "name": "benchmarks/",
          "status": "declared_only",
          "reason": "目录粒度声明（门覆盖范围/排除范围），无单一文件本体可登记"
        },
        {
          "asset_id": "asset-4537-path-directory-src",
          "name": "src/",
          "status": "declared_only",
          "reason": "目录粒度声明（门覆盖范围/排除范围），无单一文件本体可登记"
        },
        {
          "asset_id": "asset-4537-path-file-github-workflows-ci-yml",
          "name": ".github/workflows/ci.yml",
          "status": "declared_only",
          "reason": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-artifacts-lint-gate-m4175-evidence-log",
          "name": "artifacts/lint-gate-m4175/evidence.log",
          "status": "declared_only",
          "reason": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-artifacts-lint-gate-m4175-make-figure-py",
          "name": "artifacts/lint-gate-m4175/make_figure.py",
          "status": "declared_only",
          "reason": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-artifacts-lint-gate-m4175-run-evidence-sh",
          "name": "artifacts/lint-gate-m4175/run_evidence.sh",
          "status": "declared_only",
          "reason": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-docs-pr65-cure-status-md",
          "name": "docs/PR65_CURE_STATUS.md",
          "status": "declared_only",
          "reason": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-docs-ci-lint-gate-md",
          "name": "docs/ci-lint-gate.md",
          "status": "declared_only",
          "reason": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-docs-merge-cure-pr65-round3-m3891-md",
          "name": "docs/merge-cure-pr65-round3-m3891.md",
          "status": "declared_only",
          "reason": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-scripts-lint-gate-py",
          "name": "scripts/lint_gate.py",
          "status": "declared_only",
          "reason": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-tests-test-cohesive-py",
          "name": "tests/test_cohesive.py",
          "status": "declared_only",
          "reason": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-path-file-tests-test-winkler-foundation-py",
          "name": "tests/test_winkler_foundation.py",
          "status": "declared_only",
          "reason": "报告声明的外部工件路径；本体不在本仓工作树内 → 只登记声明，不下载、不复制"
        },
        {
          "asset_id": "asset-4537-vcs-branch-agent-m3891",
          "name": "agent/m3891",
          "status": "declared_metadata_only",
          "reason": "版本控制引用（分支/SHA）；本工序无法访问远端核对存在性 → 仅登记字面值"
        },
        {
          "asset_id": "asset-4537-vcs-commit-10dd296",
          "name": "10dd296",
          "status": "declared_metadata_only",
          "reason": "版本控制引用（分支/SHA）；本工序无法访问远端核对存在性 → 仅登记字面值"
        },
        {
          "asset_id": "asset-4537-vcs-commit-7accc4b",
          "name": "7accc4b",
          "status": "declared_metadata_only",
          "reason": "版本控制引用（分支/SHA）；本工序无法访问远端核对存在性 → 仅登记字面值"
        },
        {
          "asset_id": "asset-4537-vcs-commit-c5168e4",
          "name": "c5168e4",
          "status": "declared_metadata_only",
          "reason": "版本控制引用（分支/SHA）；本工序无法访问远端核对存在性 → 仅登记字面值"
        },
        {
          "asset_id": "asset-4537-vcs-commit-feb11a3",
          "name": "feb11a3",
          "status": "declared_metadata_only",
          "reason": "版本控制引用（分支/SHA）；本工序无法访问远端核对存在性 → 仅登记字面值"
        }
      ],
      "checks": {
        "source_hash_matches_contract": true,
        "chars_match_contract": true,
        "all_locators_resolve": true,
        "no_duplicate_asset_ids": true,
        "claims_empty": true,
        "no_inline_code_in_assets": true,
        "inline_code_spans_resolve": true,
        "no_verification_marked": true,
        "single_report_scope": true
      },
      "repro": {
        "cmd": "python3 scripts/kf/register_4537_assets.py && python3 -m pytest tests/test_kf_wp4537_01.py -q",
        "rebuild_from_cache": "python3 scripts/kf/register_4537_assets.py --from-cache",
        "env": [
          "TENSOR_API_BASE",
          "TENSOR_AGENT_USER",
          "TENSOR_AGENT_PASS"
        ],
        "note": "重跑会重新拉取 report 4537 并重算哈希；--from-cache 用 runs/ 缓存复算（离线可跑）"
      }
    }
  },
  "claims": []
}
```
