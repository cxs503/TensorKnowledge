# m8554 认知质量试点工件包（owner 亲自接管线）

任务书：`platform-test/epistemic-benchmark/AGENT_TASK.md`（正典）。
执行者：Claude Code 后台会话（glm-5.3），2026-11-09 owner「你直接先接手亲自做吧」接管令。
原任务 m8554（钉 glm-5.2，零席位饥饿）已悬置，本包为亲自执行交付物。

## 结构

| 路径 | 内容 |
|---|---|
| `claims/` | 4 条 Claim 记录（^tkc:，符合 claim-record.schema） |
| `evidence/` | 8 条 Evidence 记录（^tke:，符合 evidence-record.schema；每条含真实源+精确定位+逐字引文） |
| `provenance/` | 3 条 PROV-O 对齐溯源记录（^tkp:，符合 provenance-record.schema） |
| `scenario-scientific.json` | 场景一：科学命题（低风险有界 + 显式条件域） |
| `scenario-contested.json` | 场景二：争议命题（两边保留，supports 与 refutes 并存） |
| `scenario-insufficient.json` | 场景三：证据不足（诱人不蕴涵源，全部 insufficient，无 supports） |
| `../reports/8554.md` | 试点报告（含验证原样输出与九条验收判据） |
| `production-result.json` | 生产结果信封（contract_version 0.1.0） |

## 三场景 ↔ 记录映射

1. **科学命题** `tkc:prov-o:wasattributedto-signature`（established，版本锚定有界）
2. **争议命题** `tkc:fair:requires-open-access`（contested，宽命题）+ `tkc:fair:a1-protocol-conditions`（well-supported，窄命题）——两边证据并存保留
3. **证据不足** `tkc:tkrepo:rocrate-export-production`（not-assessed）——STANDARDS_MAPPING 的 P0 规划行不蕴涵实现

## 纪律声明

- 所有记录 review_status=draft / review_events 空：生产者不自批 approval。
- 证据 assessment_status 保守：场景一二 unassessed、场景三全 insufficient。
- 引文全部为 direct-quotation，来自 2026-11-09 实抓文本；没读过的段落未声称内容。
- valid_time（命题对源文本的成立时点）与 recorded_at（记录落盘时点）分离。
