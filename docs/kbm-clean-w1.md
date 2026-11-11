# KBM-CLEAN-W1 · 知识语料清洗层（第 2 轮：调研结合）

> 锚点=KBM-CLEAN-W1；判据（总账）：**洗掘｜W1-clean｜清洗规则可复跑 + 全量覆盖 + 剔除分类账数字可复算**
> 前轮 m15179 honest-FAIL（未调用 finish / fail_stage=no_progress，仅留下未提交的 `clean_corpus_v1.py`）。
> 本轮的处置：把「清洗」从一次性脚本升级为**可机器复核的账本机制**，并用抽检把规则精度量出来、再改规则。

## ① 问题设定与基准出处

**对象**：KBM（知识库挖掘）的两类源语料——
1. 仓内知识语料 `knowledge/`（286 个文件，19375759 B）；
2. KBM 抽取的源语料 = 平台 `tensor_reports`（已发布报告，本次快照 9504 条，88717319 B）。

**判据（预注册，机器裁决）**：
| # | 判据 | 机器判法 | 结果 |
|---|---|---|---|
| C1 | 规则可复跑 | 同快照两次运行 `ledger_sha256` 相同（`tests/test_kbm_clean.py::test_determinism_same_digest`）+ `verify` 重算全等 | ✅ |
| C2 | 全量覆盖 | `len(ledger) == 语料单元数`（文件面与磁盘 count 对拍、报告面与 DB count 对拍） | ✅ knowledge 286/286；reports 9504/9504 |
| C3 | 剔除分类账可复算 | `summary.json` 每个数字 == 由 `ledger.jsonl` 重新聚合；主因码加总 == 剔除总数；字节账 in == out + excluded + repair_delta | ✅（`ke.clean verify` 逐项比对，手改即红） |
| C4 | 剔除精度 | 内容质量类剔除项中带量纲/公式结构证据（疑似误剔）比例 ≤ 5% | ✅ 0/325 = 0.00% |

**基准/教训出处**：`negative_knowledge_ledger` keywords='TensorKnowledge'（failure_kind=inflated_delivery：「先核判据方案勿信报告声明」；m8846 pycache-only 空交付判例）+ 前轮 m15179 的 fail_stage=no_progress。

## ② 方法与实现

**方法谱系（external anchors，均非本仓发明）**
- ISO/IEC 25012:2008 数据质量维度（完整性/一致性/可追溯性）→ 本层的 kept/repaired/excluded 三分与「零手抄账本」。
- RFC 3629 (UTF-8) + Unicode UAX #15 (NFC) → R01/R04 规范化。
- gitleaks / trufflehog 的「正则 + 熵」秘密扫描族 → X04（本层只取正则族，熵只作命中摘要，不作判据，避免高熵假阳性）。
- OpenRefine 的 key-collision 去重范式 → X03（用内容 sha256 精确去重，不做模糊聚类；模糊聚类留待 W2）。

**实现**：`ke/clean.py`（规则引擎 + 两个适配器 + 复算器）
- 适配器：`iter_file_items()`（文件面）/ `fetch_reports()`（psql COPY，报告面）
- 规则：规范化 R01..R05；剔除 X01..X07（**单一主因码 + 全部命中码**，保证账本可加总）
- 复算器：`verify()` 五项不变量 + `resummarize()`（从账本重算汇总，证明账本是唯一事实源）
- 抽检器：`scripts/cleaning_audit_sample.py`（分层抽样回取原文，算独立结构信号）
- A/B 器：`scripts/cleaning_ab_rules.py`（v1 vs v2 差分 + 误剔反证）

## ③ 参数表

| 参数 | 值 | 含义 |
|---|---|---|
| `file_min_bytes` | 40 | 文件面空壳阈值 |
| `report_min_chars` | 120 | 报告面空壳阈值 |
| `boilerplate_line_frac` | 0.20 | 跨文档出现率 ≥20% 的行视为模板行 |
| `boilerplate_min_docs` | 20 | 模板扣除启用的语料规模下限（小语料退化保护） |
| `boilerplate_residual_chars` | 200 | 去模板后残余字符阈值 |
| `boilerplate_cov_min` | 0.80 | **v2**：模板行须占去壳字符 ≥80% |
| `process_knowledge_min` | 2 | **v2**（v1 为 3）：知识标记族命中数下限 |
| `report_max_scan` | 200000 | 单条报告扫描窗口（字符） |
| 语料规模 | knowledge 286 文件 / reports 9504 报告 | 快照身份见 `snapshot_digest` |
| 保留率 | knowledge 按条数 0.9930 / reports 0.9592 | kept+repaired 占比 |
| 剔除率（字节） | knowledge 0.0066% / reports 1.2489% | excluded 字节占比 |

## ④ 对照表（v1 基线 → v2 结构护栏，逐项裁决）

| 指标 | v1（基线，无结构护栏） | v2（本轮） | 裁决 |
|---|---|---|---|
| reports 剔除总数 | 1813 | 388 | v1 误剔 1444 条被召回 |
| 其中 X06 流程日志 | 1554 | 140 | 抽检见下 |
| 其中 X05 纯模板 | 11 | 0 | v1 用绝对残余阈值 → 误剔短技术报告，v2 加 ≥80% 模板覆盖门 |
| 其中 X02 空壳 | 185 | 185 | 不变（阈值未动） |
| 其中 X03 冗余副本 | 63 | 63 | 不变（内容 sha256 精确判） |
| **v1 误剔被召回**（v1剔/v2留） | — | **1444** 条 | 其中带量纲证据 33 条、带公式 2 条 = v1 的硬误剔证据 |
| v2 新增剔除（v1留/v2剔） | — | **19** 条（主因 {'X06_process_log': 19}） | 更专指的编排词表抓到的 v1 漏网 |
| 矛盾率（内容质量类剔除带结构证据） | 未入账（无法复算） | **0.00%**（≤5% 门）✅ | v2 起结构信号逐条入账，可复算 |
| knowledge 面剔除 | 8 | 2 | v1 把 `__init__.py`/`.input` 计为「纯模板」，v2 模板规则限定散文后修正 |

**抽检证据**（`runs/cleaning-w1/reports/audit_sample.json`，分层抽样，每层 ≤25 条）：v1 的典型误剔样例 ——
`report:10321`（Helmholtz BEM 水下声辐射验证报告，量纲命中 2、表格 26 行）被判 X06；v2 因结构护栏召回。
`report:10`（议事会提案补报）v1 判 X06 亦被 v2 召回（量纲 6），属边界样本：编排语义强但携带工程数字 ——
**诚实登记为已知边界**，见 ⑥。

## ⑤ 参数敏感性（子样本 n=2428，id%4==0 的确定性抽样）

| process_knowledge_min | boilerplate_cov_min | 剔除总数 | X06 | X05 | 矛盾率 |
|---|---|---|---|---|---|
| 1 | 0.8 | 56 | 11 | 0 | 0.00% |
| 2 | 0.8 | 81 | 36 | 0 | 0.00% |
| 3 | 0.8 | 124 | 79 | 0 | 0.00% |
| 2 | 0.5 | 81 | 36 | 0 | 0.00% |
| 2 | 0.95 | 81 | 36 | 0 | 0.00% |

读法：`process_knowledge_min` 是唯一真正敏感的参数（1→3 使 X06 剔除 11→79），说明「流程日志 vs 技术报告」的
边界本质上是知识标记密度问题；`boilerplate_cov_min` 在 0.5–0.95 区间对结果**完全不敏感**（X05 恒为 0），
因为模板覆盖门一旦存在，命中者极少——保留 0.80 作保守默认（宁漏不误剔）。

## ⑥ 失败模式、工件与复跑

**工件**
- `runs/cleaning-w1/knowledge/{ledger.jsonl,summary.json,report.md}`（286 条）
- `runs/cleaning-w1/reports/{ledger.jsonl,summary.json,report.md}`（9504 条）
- `runs/cleaning-w1/reports-v1-baseline/`、`knowledge-v1-baseline/`（v1 基线账本，A/B 对照用）
- `runs/cleaning-w1/ab_rules_v1_v2.json`、`sensitivity.json`、`reports/audit_sample.json`

**repro_cmd**
```bash
python -m ke.clean run    --scope files --root knowledge --out runs/cleaning-w1/knowledge
python -m ke.clean verify --scope files --root knowledge --out runs/cleaning-w1/knowledge
TP_PG_USER=foundation python -m ke.clean run --scope reports --out runs/cleaning-w1/reports
python -m ke.clean verify --scope reports --out runs/cleaning-w1/reports
python -m pytest tests/test_kbm_clean.py -q          # 15 passed
python scripts/cleaning_audit_sample.py --ledger runs/cleaning-w1/reports/ledger.jsonl     --per-stratum 25 --out runs/cleaning-w1/reports/audit_sample.json
python scripts/cleaning_ab_rules.py --ledger-a runs/cleaning-w1/reports-v1-baseline/ledger.jsonl     --ledger-b runs/cleaning-w1/reports/ledger.jsonl --out runs/cleaning-w1/ab_rules_v1_v2.json
```

**失败模式与限制（honest）**
1. **报告面语料是活流**：v1 快照 9503 → v2 快照 9504（期间平台又发布报告）。
   故 `reports` 面的「全量覆盖」只对**单次快照**成立；`snapshot_digest` 即快照身份，跨快照比数必然漂移。
2. **X06 边界样本**：编排语义强但携带工程数字的报告（如 `report:10`）v2 判 kept——这是**故意取向**（宁漏不误剔），
   代价是 process-log 类噪声仍可能进入语料；量化方式见矛盾率门（当前 0.00%）。
3. **秘密扫描只覆盖正则族**（PGPASSWORD/API key/Bearer/AKIA/私钥头）；高熵随机密钥族未纳入（假阳性风险）。
   命中明细只记 span 与 token sha256 前 12 位，**不落原文**（`test_secret_leak_excluded_and_redacted` 断言）。
4. **未做语义级去重**（近重复/改述），仅精确 sha256；W2 可接 MinHash/SimHash。
5. **调研步骤 ①的部分未完成**：`oss_inventory` 现 33 行无清洗类条目（`task_key ilike '%W1%'` 0 行），
   集群 `~/oss-cache` 清单作业 cj1028 提交后 9 分钟仍在排队（241 单在前），未取回 → 该子项记 **WITHHELD**，
   方法谱系改由标准文献锚定（见 ②）。
6. **仓内既有 6 项测试失败与本次改动无关**：对 `git archive HEAD` 的干净导出跑
   `tests/test_ke_migrate.py + tests/test_sediment_ke_relay.py` 同样 6 failed（计数漂移 369 vs 257），
   属既有欠账，未在本单修（不掩盖）。

**上游 Stub 计划**：`ke/consume.py` 的检索面可直接消费本层账本（excluded 集合 = 检索屏蔽名单），
迁移方案已登记 `oss_solutions(feature_slug='KBM-CLEAN-W1')`。
