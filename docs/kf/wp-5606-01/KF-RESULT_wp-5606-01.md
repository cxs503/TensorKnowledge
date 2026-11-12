# KF-RESULT wp-5606-01

tags: kf-wp:wp-5606-01, KF, 01-asset-registration, report-5606, TensorKnowledge

package_id: `wp-5606-01` ｜ task_type: `01-asset-registration` ｜ report_id: `5606` ｜
source_uri: `tensor://reports/5606` ｜ source_field: `markdown`

## ①本工序做了什么

对 report_id=**5606** 做**资产登记**（01-asset-registration）：确认报告 markdown 的字节
SHA-256 与工作包契约一致，清点正文与平台记录里**声明**的附件/被引用工件，给每个条目配
可解析的原文定位（行号+逐字引文）。**不做抽取**（`objective.extraction_performed=false`），
**不做报告类型分类**（`objective.classify_report_type=false`），**不把任何结论标成 verified**
（verification 由平台门计算）。

源资产确认结果：

| 项 | 值 |
|---|---|
| 报告标题（平台记录） | IN18-T3 顶刊报告框架与防造假溯源管线（快照+SHA-256+重跑 SQL 门禁） |
| scenario_key | `campaign:IN18-T3:chronicle-report-v2` |
| 状态 / 创建者 / 创建时间 | published / 1 / 2026-11-07T00:50:52.693855+00:00 |
| 记录 mission_id | 4976 |
| markdown 字符数（契约 5853） | 5853（`chars_match_contract=True`） |
| markdown UTF-8 字节数 | 8896 |
| 行数 | 138 |
| 实测 sha256 | `sha256:da0d91e5c5eae1aa240fba2fcc6b0ebab3960fb49f0f31378cf9a7f866b14edd` |
| 契约 source_hash | `sha256:da0d91e5c5eae1aa240fba2fcc6b0ebab3960fb49f0f31378cf9a7f866b14edd` |
| 是否一致 | **True** |
| 标题/场景/字符数与契约交叉校验 | title=True，scenario=True，chars=True |

## ②怎么做的（步骤/工具/关键设置）

1. **取原文**：以任务身份登录平台，`GET /tensor/reports/5606`，只读 `markdown` 字段；同时留存
   `figures`（图件声明）与记录元数据。全程只碰 report_id=5606，未读未写其它报告。
2. **哈希**：对 markdown 的 **UTF-8 字节**算 SHA-256（不是字符序列、不是 JSON 序列化后字节），
   与契约 `source_hash` 逐字比对。
3. **附件清点**（三条来源，全部程序化）：
   - 平台记录 `figures[*]`：取 name/caption，并**枚举该条目实际携带的键**判断有无二进制载荷；
   - 正文图件账本表：正则抓 `` `fig-00N` | 名称 | 文件, 文件 | `hash, hash` `` 行，拆出 6 个文件名与
     各自的**声明哈希前缀**；
   - 正文里以绝对路径/裸名出现的被引用工件：冻结输入 JSON、5 个 `.py` 模块（basename）。
4. **可解析性判定**（只做只读探测，不臆断）：
   - 报告正文有无 `![` 图像语法、http 外链、base64 载荷 → 扫描计数 `0` / `0` / 0；
   - 冻结工件路径用 `Path.is_file()` 探测真实存在性；
   - 代码模块在 TensorKnowledge 工作树内按 basename 全树搜索。
   **解析不到就写 `resolvable=false` + 原因**，不把「声明存在」写成「已取得」。
5. **定位器**：每个条目生成 `{source_field, line, quote, resolvable}`，quote 取原文该行去首尾空白的
   整行文本，并当场断言 `quote in markdown`（共 16 条）。
6. **结构清单**：按 `^#{1,6} ` 切节，登记每节的标题/层级/起止行/字符数/节文本 sha256（7 节）。
7. **自检与签名**：生成 `asset_manifest.json` 后按 v1 schema 校验信封；`claims` 输出空数组
   （契约允许，本工序不产知识）。
8. **工具链**：Python 3.11（stdlib `hashlib`/`json`/`urllib`/`re`）+ `jsonschema` 校验；无新增第三方依赖。

## ③产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `runs/wp-5606-01/asset_manifest.json` | 交付本体：源资产（哈希/尺寸/元数据/契约交叉校验）、15 条附件与引用工件、16 条可解析定位器、7 节结构清单、自检布尔 |
| `runs/wp-5606-01/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs/claims=[]），本报告 ④ 的 json 块即此文件逐字内容 |
| `runs/wp-5606-01/source_5606.md` | 取回的报告原文快照（只读留档，用于定位复现；哈希=上文 source_hash） |
| `runs/wp-5606-01/verify_wp5606_01.py` | 独立校验器：重新拉取原文、重算哈希、逐条验定位器落在所述行、查 id 唯一/作用域/claims 纪律；**不**自称 verified |
| `scripts/kf/build_asset_manifest_wp5606_01.py` | 生成器（幂等；重跑结果除时间戳外一致） |
| `scripts/kf/emit_wp5606_01_report.py` | 本报告的生成器（正文数字全部从 manifest 注入，零手抄） |
| `runs/wp-5606-01/fig_acceptance.png` | ④-1 的结果图（左=资产清点柱图，右=acceptance 自检面板），由 manifest 程序化生成 |
| `scripts/kf/make_wp5606_01_figure.py` | 结果图生成器（matplotlib Agg，英文标签，数字零手抄） |
| `tests/test_kf_wp5606_01_asset_manifest.py` | 5 项 pytest：结构 + 校验器通过 + **2 个负例**（篡改引文、篡改 source_hash 必须 FAIL） |
| `schemas/kf_result.v1.schema.json` | 本检出原先缺失的结果信封 schema，按工作包契约声明路径补齐（内容与仓内既有副本逐字一致，sha256 `170dba8b0b5d54012490aaadc0b68647a9520ecb869e9d03f873afb99b74c076`） |

## ④结果图与证据定位表

### ④-1 结果图（`runs/wp-5606-01/fig_acceptance.png`，sha256 `sha256:eb8deb9b757c7532b779717e7194de6854435ddf4312963b77af4a9ecd54bb84`）

![fig_acceptance.png](runs/wp-5606-01/fig_acceptance.png)

- **左panel A. 资产清点**：按条类（figure record entry / figure file / frozen input artifact /
  code module reference）画「报告声明条数」、「引文可解析条数」、「文件字节可取得条数」三组柱。
  15 条声明 / 15 条引文可解析 / 0 条字节可得 —— 缺口就是⑤要说的那件事。
- **右panel B. acceptance 自检**：六项 acceptance 逐项绿/红；绿=本工序机械自检通过，
  **不是**平台 verification 结论。
- **为什么没有场量云图/与解析解的对比曲线**：本工序是**资产登记**（`extraction_performed=false`），
  不产生任何场量、不重算任何物理量；报告 5606 本身也不含场数据载荷（正文无图件字节）。
  强行画云图等于编造，故此处出的是"机器派生的状态图"而非场图。所有柱子数字由
  `scripts/kf/make_wp5606_01_figure.py` 从 `asset_manifest.json` 读取，零手抄；无 CJK 字体，
  图内标签用英文（数据值仍以原文中文引文形式留在下文表中）。

### ④-2 证据定位表（claim/字段 → 原文引文片段）

登记条目的定位器（`resolvable`=该引文是否在原文逐字命中并落在所述行；**附件字节是否可取**是另一件事，
见 ⑤）。共 15 条：figure_record_entry=3、
figure_file=6、frozen_input_artifact=1、
code_module_reference=5。

- 「引文命中+落行」= `locator.resolvable`：引文在原文逐字存在**且**在所述行 → 15/15 条通过。
- 「字节可取得」= `attachment.resolvable`：条目对应的**文件字节**是否能被本工序取得 → 0/15 条可得（原因见 ⑤）。

| asset_id | kind | name | 引文命中+落行 | 字节可取得 | 行 | 原文引文（截断） |
|---|---|---|---|---|---|---|
| `att-fig-rec-001` | figure_record_entry | fig1_saturation | 是 | 否 | L88 | "\| `fig-001` \| fig1_saturation \| fig1_saturation.png, fi…" |
| `att-fig-rec-002` | figure_record_entry | fig2_coverage_heatmap | 是 | 否 | L89 | "\| `fig-002` \| fig2_coverage_heatmap \| fig2_coverage_hea…" |
| `att-fig-rec-003` | figure_record_entry | fig3_success_funnel | 是 | 否 | L90 | "\| `fig-003` \| fig3_success_funnel \| fig3_success_funnel…" |
| `att-fig1-saturation-png` | figure_file | fig1_saturation.png | 是 | 否 | L88 | "\| `fig-001` \| fig1_saturation \| fig1_saturation.png, fi…" |
| `att-fig1-saturation-pdf` | figure_file | fig1_saturation.pdf | 是 | 否 | L88 | "\| `fig-001` \| fig1_saturation \| fig1_saturation.png, fi…" |
| `att-fig2-coverage-heatmap-png` | figure_file | fig2_coverage_heatmap.png | 是 | 否 | L89 | "\| `fig-002` \| fig2_coverage_heatmap \| fig2_coverage_hea…" |
| `att-fig2-coverage-heatmap-pdf` | figure_file | fig2_coverage_heatmap.pdf | 是 | 否 | L89 | "\| `fig-002` \| fig2_coverage_heatmap \| fig2_coverage_hea…" |
| `att-fig3-success-funnel-png` | figure_file | fig3_success_funnel.png | 是 | 否 | L90 | "\| `fig-003` \| fig3_success_funnel \| fig3_success_funnel…" |
| `att-fig3-success-funnel-pdf` | figure_file | fig3_success_funnel.pdf | 是 | 否 | L90 | "\| `fig-003` \| fig3_success_funnel \| fig3_success_funnel…" |
| `att-frozen-ledger-json` | frozen_input_artifact | capability_ledger_resolved.json | 是 | 否 | L10 | "被冻结的真实工件：`/root/tp-agent/work/m4976/artifacts/capability_l…" |
| `att-code-figures` | code_module_reference | figures.py | 是 | 否 | L36 | "- **图件层** `figures.py`：饱和曲线 / 覆盖度热图 / 成功漏斗，数组全部由 SQL 窗口函数与…" |
| `att-code-provenance` | code_module_reference | provenance.py | 是 | 否 | L31 | "- **溯源层** `provenance.py`：稿中数字唯一合法形态为 `数值 {{prov:<id>}}`，记…" |
| `att-code-skeleton` | code_module_reference | skeleton.py | 是 | 否 | L33 | "- **骨架层** `skeleton.py`：十节顶刊结构（Abstract/Introduction/Syste…" |
| `att-code-snapshot` | code_module_reference | snapshot.py | 是 | 否 | L29 | "- **快照层** `snapshot.py`：真实工件 JSON → SQLite（capability/evid…" |
| `att-code-verify` | code_module_reference | verify.py | 是 | 否 | L38 | "- **门禁层** `verify.py`：重跑每条记录的 SQL、重算快照与图件哈希、比对印刷值，" |

关键字段的定位：

| 字段 | 值 | 原文位置 |
|---|---|---|
| 快照哈希（SQLite 字节 SHA-256） | `f46ab6f316a2c10c1c38b67594643eb0483c0e7cbe7d67c7e20dfcb374f9f572` | L11："快照哈希 `f46ab6f316a2c10c1c38b67594643eb0483c0e7cbe7d…" |
| 冻结输入工件路径 | `/root/tp-agent/work/m4976/artifacts/capability_ledger/capability_ledger_resolved.json` | L10 |
| 平台记录 summary 的 sha256（登记值，非原文引文） | `sha256:5d280260c65f4d8b5e114ee77fc2730da621617d64b295bb68c6c8fbdbccd5ff` | 记录 `summary` 字段，source_field=summary |
| markdown 字节哈希 | `sha256:da0d91e5c5eae1aa240fba2fcc6b0ebab3960fb49f0f31378cf9a7f866b14edd` | 全文 UTF-8 字节（平台可独立重算） |

> 逐字校验口径：`quote in markdown` 且 `quote in lines[line-1]`。校验器重跑输出
> `locators_checked=16`、`locators_failed=[]`。

## ⑤注意点与局限

1. **附件只有声明、没有字节**：正文无 `![` 图像语法、无 http 外链、记录 `figures[*]` 只有
   name+caption（无 base64 载荷）。6 个图件文件（3×(PNG+PDF)）在正文里**只登记了 11 位 sha256 前缀**
   （如 `fig-001` → `c2c890360ad3, 037bb6c488eb`），因此本工序**无法**重算图件字节哈希，
   `resolvable` 一律记 false——这是如实记录，不是判定"图不存在"。
2. **冻结输入工件在构建时不存在**：正文引用的 `/root/tp-agent/work/m4976/artifacts/capability_ledger/capability_ledger_resolved.json` 指向另一 mission 的工作树，
   `is_file()` 探测为 False，登记为未解析；快照哈希
   `f46ab6f316a2c10c1c38b67594643eb0483c0e7cbe7d67c7e20dfcb374f9f572` 只能作为"报告声明值"转述，无法在本工序复算。
3. **只登记了 1 个完整 64-hex 值**（快照哈希）；图件哈希与表内 `f46ab6f316a2` 前缀均为截断形式
   （`scan.full_sha256_literals=1`）。
4. **代码模块不可从报告内解析**：`snapshot.py/provenance.py/skeleton.py/figures.py/verify.py` 只给
   basename，无仓库/路径信息；TensorKnowledge 检出内无同名胜任文件 → `resolvable=false`。
   平台记录 `summary` 字段称这批模块落在论文生产线工具树 `tools/chronicle/report/`（**该串出自 `summary` 而非
   `markdown`**，本工序只登记、不据此断言代码位置），该树不在 TensorKnowledge 检出内，属跨仓引用。
5. **mission 号不一致**：平台记录 `mission_id=4976`，本工作包由
   mission 15569 的产线派发，契约 `mission_id: null`。三个值原样登记，**不做调和**（本工序无裁定权）。
6. **契约分层提示 `IN18-T3|campaign:IN18-T3:chronicle-report-v2|m`** 原样登记不解读
   （`classify_report_type=false`）。
7. **未做的事**（写进 manifest 的 `not_performed`）：知识抽取/claim 生成、报告类型分类、
   任何 claim 的验证、图件字节级校验。
8. 本报告中的一切数字都由 `emit_wp5606_01_report.py` 从 manifest 注入，人工零手抄；改动 manifest 后重跑
   生成器即可让正文与产物保持一致。

## ⑥自检：逐条对照 acceptance

| acceptance 项 | 结果 | 证据 |
|---|---|---|
| `valid_json` | ✅ | 生成器自检 `True`；`json.load` 产物成功 |
| `schema_pass` | ✅ | `jsonschema.validate(envelope, schemas/kf_result.v1.schema.json)` → `True`（独立校验器复核同结果） |
| `source_locator_resolvable` | ✅ | 16 条定位器全部 `quote in markdown` 且在所述行；`locators_failed=[]` |
| `source_hash_matches` | ✅ | 重算 `sha256:da0d91e5c5eae1aa240fba2fcc6b0ebab3960fb49f0f31378cf9a7f866b14edd` == 契约值（`True`），独立校验器用**新拉取**原文复算亦一致 |
| `no_duplicate_ids` | ✅ | 15 个 asset_id 唯一（生成器 + 校验器双查） |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✅（空集） | `claims=[]`，契约允许（`notes`：claims 允许为空数组）；`claims_registration.reason` 已写明缘由 |

如实说明的**非本合同**发现（不粉饰，也不当作失败项）：附件字节不可得（⑤-1/2），故 `attachments.resolvable_count=0`。
这是报告载荷的客观状态，不是本工序的疏漏，已在 manifest 中逐条给出 `resolution` 理由。

## repro_cmd（一键复跑）

```bash
# 环境：TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS 已注入
cd <repo>
python3 scripts/kf/build_asset_manifest_wp5606_01.py --report-id 5606 --out runs/wp-5606-01   # 生成
python3 runs/wp-5606-01/verify_wp5606_01.py                                                  # 独立校验（PASS 退出 0）
python3 scripts/kf/emit_wp5606_01_report.py                                                  # 重建本报告
python3 -m pytest tests/test_kf_wp5606_01_asset_manifest.py -q                               # 5 passed（含 2 负例）
```

## 结果 JSON（唯一 json 块，逐字来自 runs/wp-5606-01/kf_result.json）

```json
{
  "package_id": "wp-5606-01",
  "task_type": "01-asset-registration",
  "report_id": "5606",
  "provenance": {
    "source_hash": "sha256:da0d91e5c5eae1aa240fba2fcc6b0ebab3960fb49f0f31378cf9a7f866b14edd",
    "source_field": "markdown",
    "source_uri": "tensor://reports/5606",
    "producer": "agent/m15569",
    "emitted_at": "2026-11-12T01:20:22Z",
    "notes": "01-asset-registration: source hash confirmed, attachments/referenced artifacts inventoried with verbatim locators; no extraction performed; claims empty (legal per contract); verification is left to the platform gate"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-5606-01",
      "task_type": "01-asset-registration",
      "report_id": "5606",
      "objective": {
        "register_assets": true,
        "classify_report_type": false,
        "extraction_performed": false
      },
      "generated_at": "2026-11-12T01:20:22Z",
      "generator": "agent/m15569",
      "source_asset": {
        "uri": "tensor://reports/5606",
        "field": "markdown",
        "platform_record_id": 5606,
        "hash": {
          "algorithm": "sha256",
          "value": "sha256:da0d91e5c5eae1aa240fba2fcc6b0ebab3960fb49f0f31378cf9a7f866b14edd",
          "scope": "UTF-8 bytes of tensor_reports.markdown (report 5606)",
          "contract_expected": "sha256:da0d91e5c5eae1aa240fba2fcc6b0ebab3960fb49f0f31378cf9a7f866b14edd",
          "matches_contract": true
        },
        "size": {
          "chars": 5853,
          "bytes_utf8": 8896,
          "lines": 138,
          "contract_chars": 5853,
          "chars_match_contract": true
        },
        "record_metadata": {
          "title": "IN18-T3 顶刊报告框架与防造假溯源管线（快照+SHA-256+重跑 SQL 门禁）",
          "scenario_key": "campaign:IN18-T3:chronicle-report-v2",
          "tags": [
            "IN18-T3",
            "TensorPlatform",
            "paper-line-v2",
            "provenance",
            "anti-fabrication",
            "snapshot",
            "pytest-negative-controls"
          ],
          "status": "published",
          "created_by": 1,
          "created_at": "2026-11-07T00:50:52.693855+00:00",
          "mission_id": 4976,
          "stage": null,
          "figures_declared": 3,
          "summary_sha256": "sha256:5d280260c65f4d8b5e114ee77fc2730da621617d64b295bb68c6c8fbdbccd5ff"
        },
        "contract_cross_check": {
          "title_matches_contract": true,
          "scenario_key_matches_contract": true,
          "chars_match_contract": true,
          "contract_layer_hint": {
            "value": "IN18-T3|campaign:IN18-T3:chronicle-report-v2|m",
            "interpreted": false,
            "note": "objective.classify_report_type=false → hint registered verbatim, not interpreted"
          }
        }
      },
      "attachments": {
        "count": 15,
        "resolvable_count": 0,
        "items": [
          {
            "asset_id": "att-fig-rec-001",
            "kind": "figure_record_entry",
            "role": "figure",
            "name": "fig1_saturation",
            "declared_sha256": null,
            "payload_present": false,
            "resolvable": false,
            "resolution": {
              "method": "scan record.figures entry for binary payload keys",
              "payload_keys": [
                "caption",
                "name"
              ],
              "note": "record carries caption/name only; no png_base64 or byte payload"
            },
            "caption": "图1 证据获取饱和曲线：累计证据行 vs 累计获证能力数，终态饱和比 0.30",
            "locator": {
              "source_field": "markdown",
              "line": 88,
              "quote": "| `fig-001` | fig1_saturation | fig1_saturation.png, fig1_saturation.pdf | `c2c890360ad3, 037bb6c488eb` |",
              "resolvable": true
            }
          },
          {
            "asset_id": "att-fig-rec-002",
            "kind": "figure_record_entry",
            "role": "figure",
            "name": "fig2_coverage_heatmap",
            "declared_sha256": null,
            "payload_present": false,
            "resolvable": false,
            "resolution": {
              "method": "scan record.figures entry for binary payload keys",
              "payload_keys": [
                "caption",
                "name"
              ],
              "note": "record carries caption/name only; no png_base64 or byte payload"
            },
            "caption": "图2 证据覆盖度热图：领域 × 证据等级（REAL 列仅 1 项）",
            "locator": {
              "source_field": "markdown",
              "line": 89,
              "quote": "| `fig-002` | fig2_coverage_heatmap | fig2_coverage_heatmap.png, fig2_coverage_heatmap.pdf | `00e5bb968654, fea7a9751b20` |",
              "resolvable": true
            }
          },
          {
            "asset_id": "att-fig-rec-003",
            "kind": "figure_record_entry",
            "role": "figure",
            "name": "fig3_success_funnel",
            "declared_sha256": null,
            "payload_present": false,
            "resolvable": false,
            "resolution": {
              "method": "scan record.figures entry for binary payload keys",
              "payload_keys": [
                "caption",
                "name"
              ],
              "note": "record carries caption/name only; no png_base64 or byte payload"
            },
            "caption": "图3 能力存活漏斗：claimed 21 → machine-checked 6 → OK 4 → REAL 1",
            "locator": {
              "source_field": "markdown",
              "line": 90,
              "quote": "| `fig-003` | fig3_success_funnel | fig3_success_funnel.png, fig3_success_funnel.pdf | `f5a14a4b1ddf, d1996496a632` |",
              "resolvable": true
            }
          },
          {
            "asset_id": "att-fig1-saturation-png",
            "kind": "figure_file",
            "role": "figure",
            "name": "fig1_saturation.png",
            "ledger_pid": "fig-001",
            "declared_sha256": "c2c890360ad3",
            "declared_sha256_is_prefix_only": true,
            "payload_present": false,
            "resolvable": false,
            "resolution": {
              "method": "look for file bytes in report payload and worktree",
              "payload_search": "no base64/binary payload and no markdown image link in report",
              "worktree_search": "file not present in TensorKnowledge worktree",
              "note": "only the 11-hex SHA-256 prefix is registered in the report text"
            },
            "locator": {
              "source_field": "markdown",
              "line": 88,
              "quote": "| `fig-001` | fig1_saturation | fig1_saturation.png, fig1_saturation.pdf | `c2c890360ad3, 037bb6c488eb` |",
              "resolvable": true
            }
          },
          {
            "asset_id": "att-fig1-saturation-pdf",
            "kind": "figure_file",
            "role": "figure",
            "name": "fig1_saturation.pdf",
            "ledger_pid": "fig-001",
            "declared_sha256": "037bb6c488eb",
            "declared_sha256_is_prefix_only": true,
            "payload_present": false,
            "resolvable": false,
            "resolution": {
              "method": "look for file bytes in report payload and worktree",
              "payload_search": "no base64/binary payload and no markdown image link in report",
              "worktree_search": "file not present in TensorKnowledge worktree",
              "note": "only the 11-hex SHA-256 prefix is registered in the report text"
            },
            "locator": {
              "source_field": "markdown",
              "line": 88,
              "quote": "| `fig-001` | fig1_saturation | fig1_saturation.png, fig1_saturation.pdf | `c2c890360ad3, 037bb6c488eb` |",
              "resolvable": true
            }
          },
          {
            "asset_id": "att-fig2-coverage-heatmap-png",
            "kind": "figure_file",
            "role": "figure",
            "name": "fig2_coverage_heatmap.png",
            "ledger_pid": "fig-002",
            "declared_sha256": "00e5bb968654",
            "declared_sha256_is_prefix_only": true,
            "payload_present": false,
            "resolvable": false,
            "resolution": {
              "method": "look for file bytes in report payload and worktree",
              "payload_search": "no base64/binary payload and no markdown image link in report",
              "worktree_search": "file not present in TensorKnowledge worktree",
              "note": "only the 11-hex SHA-256 prefix is registered in the report text"
            },
            "locator": {
              "source_field": "markdown",
              "line": 89,
              "quote": "| `fig-002` | fig2_coverage_heatmap | fig2_coverage_heatmap.png, fig2_coverage_heatmap.pdf | `00e5bb968654, fea7a9751b20` |",
              "resolvable": true
            }
          },
          {
            "asset_id": "att-fig2-coverage-heatmap-pdf",
            "kind": "figure_file",
            "role": "figure",
            "name": "fig2_coverage_heatmap.pdf",
            "ledger_pid": "fig-002",
            "declared_sha256": "fea7a9751b20",
            "declared_sha256_is_prefix_only": true,
            "payload_present": false,
            "resolvable": false,
            "resolution": {
              "method": "look for file bytes in report payload and worktree",
              "payload_search": "no base64/binary payload and no markdown image link in report",
              "worktree_search": "file not present in TensorKnowledge worktree",
              "note": "only the 11-hex SHA-256 prefix is registered in the report text"
            },
            "locator": {
              "source_field": "markdown",
              "line": 89,
              "quote": "| `fig-002` | fig2_coverage_heatmap | fig2_coverage_heatmap.png, fig2_coverage_heatmap.pdf | `00e5bb968654, fea7a9751b20` |",
              "resolvable": true
            }
          },
          {
            "asset_id": "att-fig3-success-funnel-png",
            "kind": "figure_file",
            "role": "figure",
            "name": "fig3_success_funnel.png",
            "ledger_pid": "fig-003",
            "declared_sha256": "f5a14a4b1ddf",
            "declared_sha256_is_prefix_only": true,
            "payload_present": false,
            "resolvable": false,
            "resolution": {
              "method": "look for file bytes in report payload and worktree",
              "payload_search": "no base64/binary payload and no markdown image link in report",
              "worktree_search": "file not present in TensorKnowledge worktree",
              "note": "only the 11-hex SHA-256 prefix is registered in the report text"
            },
            "locator": {
              "source_field": "markdown",
              "line": 90,
              "quote": "| `fig-003` | fig3_success_funnel | fig3_success_funnel.png, fig3_success_funnel.pdf | `f5a14a4b1ddf, d1996496a632` |",
              "resolvable": true
            }
          },
          {
            "asset_id": "att-fig3-success-funnel-pdf",
            "kind": "figure_file",
            "role": "figure",
            "name": "fig3_success_funnel.pdf",
            "ledger_pid": "fig-003",
            "declared_sha256": "d1996496a632",
            "declared_sha256_is_prefix_only": true,
            "payload_present": false,
            "resolvable": false,
            "resolution": {
              "method": "look for file bytes in report payload and worktree",
              "payload_search": "no base64/binary payload and no markdown image link in report",
              "worktree_search": "file not present in TensorKnowledge worktree",
              "note": "only the 11-hex SHA-256 prefix is registered in the report text"
            },
            "locator": {
              "source_field": "markdown",
              "line": 90,
              "quote": "| `fig-003` | fig3_success_funnel | fig3_success_funnel.png, fig3_success_funnel.pdf | `f5a14a4b1ddf, d1996496a632` |",
              "resolvable": true
            }
          },
          {
            "asset_id": "att-frozen-ledger-json",
            "kind": "frozen_input_artifact",
            "role": "upstream_data",
            "name": "capability_ledger_resolved.json",
            "declared_path": "/root/tp-agent/work/m4976/artifacts/capability_ledger/capability_ledger_resolved.json",
            "file_byte_hash_declared": null,
            "recorded_snapshot_sha256": "f46ab6f316a2c10c1c38b67594643eb0483c0e7cbe7d67c7e20dfcb374f9f572",
            "hash_note": "the only 64-hex value in the report is the SQLite snapshot hash; the report does not declare a byte hash of the ledger JSON itself, so file_byte_hash_declared stays null",
            "payload_present": false,
            "resolvable": false,
            "resolution": {
              "method": "local filesystem is_file()",
              "path": "/root/tp-agent/work/m4976/artifacts/capability_ledger/capability_ledger_resolved.json",
              "exists": false,
              "note": "referenced path is outside this worktree / not present at build time"
            },
            "locator": {
              "source_field": "markdown",
              "line": 10,
              "quote": "被冻结的真实工件：`/root/tp-agent/work/m4976/artifacts/capability_ledger/capability_ledger_resolved.json`；",
              "resolvable": true
            }
          },
          {
            "asset_id": "att-code-figures",
            "kind": "code_module_reference",
            "role": "implementation",
            "name": "figures.py",
            "payload_present": false,
            "resolvable": false,
            "resolution": {
              "method": "basename search inside TensorKnowledge worktree",
              "hits": [],
              "note": "report names the module by basename only (no repository/path); not resolvable from the report text alone"
            },
            "locator": {
              "source_field": "markdown",
              "line": 36,
              "quote": "- **图件层** `figures.py`：饱和曲线 / 覆盖度热图 / 成功漏斗，数组全部由 SQL 窗口函数与分组查询产出，",
              "resolvable": true
            }
          },
          {
            "asset_id": "att-code-provenance",
            "kind": "code_module_reference",
            "role": "implementation",
            "name": "provenance.py",
            "payload_present": false,
            "resolvable": false,
            "resolution": {
              "method": "basename search inside TensorKnowledge worktree",
              "hits": [],
              "note": "report names the module by basename only (no repository/path); not resolvable from the report text alone"
            },
            "locator": {
              "source_field": "markdown",
              "line": 31,
              "quote": "- **溯源层** `provenance.py`：稿中数字唯一合法形态为 `数值 {{prov:<id>}}`，记录绑定",
              "resolvable": true
            }
          },
          {
            "asset_id": "att-code-skeleton",
            "kind": "code_module_reference",
            "role": "implementation",
            "name": "skeleton.py",
            "payload_present": false,
            "resolvable": false,
            "resolution": {
              "method": "basename search inside TensorKnowledge worktree",
              "hits": [],
              "note": "report names the module by basename only (no repository/path); not resolvable from the report text alone"
            },
            "locator": {
              "source_field": "markdown",
              "line": 33,
              "quote": "- **骨架层** `skeleton.py`：十节顶刊结构（Abstract/Introduction/System Architecture/Methods/",
              "resolvable": true
            }
          },
          {
            "asset_id": "att-code-snapshot",
            "kind": "code_module_reference",
            "role": "implementation",
            "name": "snapshot.py",
            "payload_present": false,
            "resolvable": false,
            "resolution": {
              "method": "basename search inside TensorKnowledge worktree",
              "hits": [],
              "note": "report names the module by basename only (no repository/path); not resolvable from the report text alone"
            },
            "locator": {
              "source_field": "markdown",
              "line": 29,
              "quote": "- **快照层** `snapshot.py`：真实工件 JSON → SQLite（capability/evidence/视图）→ 对库文件字节取",
              "resolvable": true
            }
          },
          {
            "asset_id": "att-code-verify",
            "kind": "code_module_reference",
            "role": "implementation",
            "name": "verify.py",
            "payload_present": false,
            "resolvable": false,
            "resolution": {
              "method": "basename search inside TensorKnowledge worktree",
              "hits": [],
              "note": "report names the module by basename only (no repository/path); not resolvable from the report text alone"
            },
            "locator": {
              "source_field": "markdown",
              "line": 38,
              "quote": "- **门禁层** `verify.py`：重跑每条记录的 SQL、重算快照与图件哈希、比对印刷值，",
              "resolvable": true
            }
          }
        ],
        "scan": {
          "record_figures_len": 3,
          "markdown_image_syntax_hits": 0,
          "markdown_url_hits": 0,
          "markdown_absolute_path_hits": 1,
          "markdown_code_module_hits": 5,
          "full_sha256_literals": 1
        },
        "composition": {
          "figure_record_entry": 3,
          "figure_file": 6,
          "frozen_input_artifact": 1,
          "code_module_reference": 5
        },
        "note": "no embedded binary/base64 payload and no image link in the report markdown; figure files and the frozen input artifact are declared, not shipped — registration records the declaration and the failed local resolution attempt"
      },
      "declared_hashes": [
        {
          "value": "f46ab6f316a2c10c1c38b67594643eb0483c0e7cbe7d67c7e20dfcb374f9f572",
          "locator": {
            "source_field": "markdown",
            "line": 11,
            "quote": "快照哈希 `f46ab6f316a2c10c1c38b67594643eb0483c0e7cbe7d67c7e20dfcb374f9f572`（采集于 `2026-11-07T00:50:00+00:00`），",
            "resolvable": true
          },
          "is_full_sha256": true,
          "appears_in_report": true
        }
      ],
      "sections": [
        {
          "ordinal": 1,
          "level": 1,
          "heading": "IN18-T3 顶刊报告框架与防造假溯源管线（论文生产线 v2 血统）",
          "line_start": 1,
          "line_end": 2,
          "chars": 38,
          "sha256": "sha256:b049f8471aa47c0efe78f5e6fac48480efc3f6c8bce903224b672d0bff14d1cd"
        },
        {
          "ordinal": 2,
          "level": 2,
          "heading": "1. 案例介绍",
          "line_start": 3,
          "line_end": 26,
          "chars": 688,
          "sha256": "sha256:bdf69b2f0e1dc1bd3ec711df5fd47c5e7017dcc8e8a6c970d116f4d6f38a54d1"
        },
        {
          "ordinal": 3,
          "level": 2,
          "heading": "2. 怎么做的",
          "line_start": 27,
          "line_end": 41,
          "chars": 779,
          "sha256": "sha256:07e8bfc5486f9fb7afcba7d14322b06767ec42b19120ec2c783571651581f5de"
        },
        {
          "ordinal": 4,
          "level": 2,
          "heading": "3. 计算结果（全部程序化注入）",
          "line_start": 42,
          "line_end": 91,
          "chars": 2796,
          "sha256": "sha256:6034307e4740f869624a9693d55ec58b943bd666ddcb3536de20f963179b7034"
        },
        {
          "ordinal": 5,
          "level": 2,
          "heading": "4. 结果图",
          "line_start": 92,
          "line_end": 105,
          "chars": 356,
          "sha256": "sha256:f58baa421b04a87f7bf1a69b7fe52b1c7a7f11901e42613b46e1565ecc12b8f0"
        },
        {
          "ordinal": 6,
          "level": 2,
          "heading": "5. 注意点（踩坑与局限）",
          "line_start": 106,
          "line_end": 120,
          "chars": 590,
          "sha256": "sha256:c67958a979b9bb0783b65ec348ec1af21499efd11ae255f94f5abd17f7d13696"
        },
        {
          "ordinal": 7,
          "level": 2,
          "heading": "6. 误差判定",
          "line_start": 121,
          "line_end": 138,
          "chars": 600,
          "sha256": "sha256:ae37b3433968945e9bd9d51af50c05e505d6746dbfd91d0b342cb0d5ecf6b329"
        }
      ],
      "claims_registration": {
        "claims_emitted": 0,
        "claims_allowed_empty": true,
        "reason": "task_type 01-asset-registration: objective.register_assets=true, no extraction; empty claims array is a legal complete result per contract"
      },
      "not_performed": [
        "knowledge extraction / claim generation (out of scope for 01)",
        "report type classification (objective.classify_report_type=false)",
        "verification of any report claim (verification is computed by the platform gate)",
        "byte-level check of figure PNG/PDF files (only 11-hex prefixes exist in the text, no payload)"
      ],
      "limitations": [
        "Figure attachments are registered from declarations only; their bytes were not available to this work package, so their hashes cannot be re-verified here.",
        "The frozen input artifact path points at another mission worktree and does not exist at build time; resolution status is recorded as false, not assumed.",
        "Code modules are named by basename without repository/path, so they cannot be resolved from the report text alone.",
        "Record mission_id and this work package mission differ; both values are registered verbatim without reconciliation."
      ],
      "acceptance_selfcheck": {
        "valid_json": true,
        "source_hash_matches": true,
        "source_locator_resolvable": true,
        "source_locator_count": 16,
        "source_locator_failures": [],
        "no_duplicate_ids": true,
        "all_claims_have_evidence_or_explicit_unresolved_status": true,
        "claims_empty_legal": true,
        "schema_pass": true,
        "schema_path": "schemas/kf_result.v1.schema.json"
      }
    }
  },
  "claims": []
}
```
