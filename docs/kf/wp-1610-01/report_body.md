# KF-RESULT wp-1610-01

**tags**: kf-wp:wp-1610-01, 01-asset-registration, report:1610, lane:C, draft
**package_id**: wp-1610-01 ｜ **task_type**: 01-asset-registration ｜ **report_id**: 1610
**lane**: C ｜ **repo**: TensorKnowledge ｜ **branch**: agent/m15530 (mission 15530)
**date**: 2026-11-12

---

## 1. 本工序做了什么

本工作包做且只做 `report_id=1610` 一份报告的**资产登记**（工序 `01-asset-registration`）：确认 report_id 与其 `markdown` 字段的字节哈希一一对应（平台独立重算的 `sha256` 与契约 `source_hash` 一致），登记报告记录里可解析的附件（`record.figures` 的 3 个 png 元数据）与正文声明的 3 个工件路径，**不做任何内容抽取、不做分类、不产生 claim**（契约 `objective.classify_report_type: false`，`claims` 允许为空数组，本单据此留空）。

边界遵守情况：只以 `GET /api/v1/tensor/reports/1610` 读取该一份报告；未读/写/覆盖任何其它 report_id；未改写上游或其它工作包的产物；**没有把任何结论标成 verified**（本单只做机械哈希恒等，verification 归平台门）。

## 2. 怎么做的（步骤/工具/关键设置）

1. **读契约**：从任务指令取 YAML 契约（`package_id=wp-1610-01`、`report_id=1610`、`source_field=markdown`、`source_hash=sha256:c4269799…a41de`、`chars=5883`、`title`、`scenario_key=cmaes_literature_verification`），并取 `acceptance` 六条作为自检表。
2. **取源**：`POST /api/v1/auth/login`（凭据只从环境变量 `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS` 读，不落盘、不进仓库）→ `GET /api/v1/tensor/reports/1610`（Bearer），取 `markdown` 字段原文；同名报告的 `title/scenario_key/figures/mission_id/status` 一并登记为元数据。
3. **独立验证哈希**：`hashlib.sha256(markdown.encode('utf-8')).hexdigest()`，与契约 `source_hash` 逐字比较；同时记录 `len(markdown)`（字符）与 UTF-8 字节数（中文正文两者不同：5883 字符 / 9536 字节，契约 `chars` 用的是字符数，一致）。
4. **零手抄定位**：把本报告要用到的 **15 条**引文写进脚本常量表，用 `markdown.find(quote)` 逐条解析字符偏移，全部命中才允许出产物（`scripts/kf_wp1610_01_register.py` 里 `unresolved` 非空即 `SystemExit`）。结果落 `docs/kf/wp-1610-01/locator_check.json`（每条引文的 offset / 命中次数）。
5. **登记附件与工件**：附件 = 报告记录 `figures[]` 的 name+caption（3 项，元数据级）；工件 = 正文 §3.5 声明的 `artifacts/cmaes_verification/*.png`（3 项，路径逐字引自正文，`resolvable_from_platform_record=false`，因为二进制不在报告记录里）。
6. **组信封 + 机器校验**：按 `schemas/kf_result.v1.schema.json` 组 `kf_result.v1` 信封（`package_id/task_type/report_id/provenance/outputs`），用 `jsonschema.validate`（draft 2020-12）校验通过后才写盘。
7. **渲染报告**：叙述模板里用三个占位标记（KF_RESULT_JSON / EVIDENCE_TABLE / IDENTITY_TABLE，脚本按名替换），由脚本从 `asset_manifest.json` / `locator_check.json` 直接注入，**报告里的数字与 json 块均为程序化注入，无手抄**。

## 3. 产出物清单

| 输出文件 / 产物 | 路径 | 要点 |
|---|---|---|
| asset_manifest.json（契约声明输出） | `docs/kf/wp-1610-01/asset_manifest.json` | report_id=1610；source_hash 已独立重算并匹配；chars=5883 / bytes=9536；attachments=3（记录 figures）；artifacts=3（正文声明，记录内不可解析）；claims=[] |
| 定位校验报告 | `docs/kf/wp-1610-01/locator_check.json` | 15 条引文全部命中，含字符偏移与命中次数 |
| 源文逐字节副本 | `docs/kf/wp-1610-01/source.md` | API 取回的 markdown 原文（供离线复核子串） |
| 重算摘要 | `docs/kf/wp-1610-01/sha256.txt` | `sha256:c4269799…a41de` |
| 结果信封 | `docs/kf/wp-1610-01/kf_result.json` | kf_result.v1，已过 `jsonschema` 校验 |
| 本报告 | `docs/kf_result_wp-1610-01.md` | 六段 + 唯一一个 json 代码块 |
| 登记脚本 | `scripts/kf_wp1610_01_register.py` | 取源 / 哈希 / 15 条引文解析 / 清单生成（失败即非零退出） |
| 信封与渲染脚本 | `scripts/kf_wp1610_01_result.py` | schema 校验 + 标记注入渲染 |
| 自检测试 | `tests/test_kf_wp1610_01.py` | 离线复算 sha256、逐条子串、schema 校验、清单字段一致性 |
| schema 副本 | `schemas/kf_result.v1.schema.json` | 本检出 main 上缺该文件，从同平台兄弟工作树取回，sha256=`170dba8b0b5d…4c076`（与本单另一份副本逐字节相同） |

## 4. 证据定位表

源报告身份（字段 → 值，全部来自 API 返回与重算）：

@@IDENTITY_TABLE@@

引文 → 原文逐字片段（偏移由 `markdown.find` 机械给出，非人工计数）：

@@EVIDENCE_TABLE@@

上游正文里可登记为旁注的两处数字口径（**仅登记，不判真伪**）：

| 观察点 | 原文逐字片段 | 备注 |
|---|---|---|
| 采样保真两处口径 | `经验协方差相对 Frobenius 误差 0.002（N=6, 180000 次抽样）` / `采样协方差` | §3.3 写 0.002（=0.2%），§5 写「0.24%」；在两位有效数字舍入下可自洽，但字面不等，留给抽取/审计道次核 |
| 检查项计数 | `运行环境：8 项检查` | §6 与报告记录 title 说「8 项检查 / 8/8」，§3.3 表只列 6 行（C2,C4,C5,C6,C7,C8）；按 C1=闭式参数（§3.1）、C3=收敛（§3.2）补齐才等于 8，正文未显式标注 C1/C3 编号，属可追溯性缺口而非数值矛盾 |

## 5. 注意点与局限

- **哈希相等 ≠ 内容正确**：本单只证明「report_id=1610 的 markdown 与契约 `source_hash` 逐字节一致」，不对报告结论做任何背书；正文里「8/8 检查通过」「闭式参数零误差」等是上游作者的表述，本单原样登记、未复核其计算。
- **「检查通过」不等于「全部 <3%」**：上游 §5 自己写明收敛评价数偏差最坏 +80.0%（判据是「比值 ≤3 且全部达标」），并明确「不宣称 3% 精度」。下游抽取时不得把 title 的「8/8 检查通过」读成「3% 精度全项达标」。
- **附件未下载**：3 个 png 只登记了记录里的 name+caption，未下载校验存在性/内容；3 个 §3.5 工件路径只做路径字符串登记（`resolvable_from_platform_record=false`），实际二进制在产出仓（非本平台记录）。
- **§3.1 参数表数值为破折号**：正文把 λ/μ/μ_eff/c_c/c_s/c_1/c_μ/d_σ/χ_N 的具体数值列留空（「—」），只给「最大相对误差=0」；因此**这 9 个参数的具体数字无法从本报告逐字引用**，只对「零误差」这一表述可定位。下游若要参数值须回产出仓 `optimizer/verification/cmaes_reference.py`，本单不做。
- **产物位置（口径说明）**：本仓 `.gitignore` 忽略 `artifacts/`，推送门禁又把 `artifacts/**` 判为 record 丢弃（`tp_pusher.py` `_EXCLUDE`），故本包全部产物落在 **`docs/kf/wp-1610-01/`**（GitHub 可见、可直接复核）；本报告的首版草稿（平台报告 #14585）用了 `artifacts/wp-1610-01/` 口径，其产物文件（清单/定位表/源文/摘要）与本版逐字节相同，仅报告内路径前缀不同；本版为最终口径。
- **schema 来源**：本检出 main 上缺 `schemas/kf_result.v1.schema.json`；为保证 `schema_pass` 可机器裁，从同平台兄弟工作树取回同名文件（sha256 `170dba8b…4c076`，两份副本逐字节相同），未改动其内容，也未改动任何他单产物。
- **无图声明**：本单为纯资产登记（文档/后端类）工序，不产生也不分析场量，没有「场量云图/与解析解比较曲线」可画；按报告纪律④如实声明无图，不造装饰性图。
- **mission 口径**：源报告记录 `mission_id=1884`（产出它的任务），本工作包运行在 mission 15530 下；两者不同属正常，已在 `provenance.source_mission_id` 与清单中分别登记。
- **未完成的边界**：不做 claims 抽取、不做报告类型分类（契约明确 false），因此本单对知识库的知识增量=0 条 claim，只有可追溯的资产锚点。

## 6. 自检（逐条对照 acceptance）

| acceptance | 状态 | 证据 |
|---|---|---|
| valid_json | ✓ | `docs/kf/wp-1610-01/kf_result.json` 与 `docs/kf/wp-1610-01/asset_manifest.json`、`docs/kf/wp-1610-01/locator_check.json` 均经 `json.load` 成功；`tests/test_kf_wp1610_01.py` 复验 |
| schema_pass | ✓ | `jsonschema.validate(envelope, schemas/kf_result.v1.schema.json)` 通过（draft 2020-12，schema sha256 `170dba8b…4c076`）；`required` 四项齐全、`additionalProperties: false` 下无多余键 |
| source_locator_resolvable | ✓ | `tensor://reports/1610` 经 `GET /api/v1/tensor/reports/1610` 200 返回；15/15 引文 `markdown.find` 命中（见 locator_check.json） |
| source_hash_matches | ✓ | 重算 `sha256:c426979905fa50a5cd372e8e7b300ad931596c437ea1cbabb79df59c7aaa41de` == 契约值（match=True） |
| no_duplicate_ids | ✓ | 只登记 report_id=1610 一条资产；`outputs` 只一个键 `asset_manifest.json`；清单内无重复 id |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓ | `claims: []`（契约 `no_forced_claim_generation: true` 允许；schema 亦声明零条为合法完整结果），无凭空声明 |

**无失败项**（无 honest-FAIL 需要申报）。唯一需要读者注意的口径：本单的「verified」只有哈希恒等一层，其余均属登记。

---

## 结果 JSON（本报告唯一 json 块）

@@KF_RESULT_JSON@@

---

**repro_cmd**（工作树根执行；凭据走环境变量，无明文密钥）：

```bash
python3 scripts/kf_wp1610_01_register.py   # 取源+重算哈希+15 条引文定位 → docs/kf/wp-1610-01/
python3 scripts/kf_wp1610_01_result.py     # schema 校验 + 渲染 docs/kf_result_wp-1610-01.md
python3 -m pytest tests/test_kf_wp1610_01.py -q
```