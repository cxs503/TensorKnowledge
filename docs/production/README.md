# docs/production — 报告→知识生产线

本目录只放**生产线规范层**（契约、工序、门禁规则），不含领域内容、不含治理政策。
治理层在 `governance/`，知识引擎在 `ke/`，机读契约在 `schemas/`。

| 文件 | 是什么 | 可执行面 |
|---|---|---|
| `PRODUCTION-LINE-v1.md` | 生产线规范 v1：标准工作包契约、五工序、三道门、技能库、角色两层、范围令 | — |
| `GATE-RULES.md` | 三道门校验规则清单（S*/E*/M*/V*/K*），每条附代码位置与失败夹具 | 可执行优先：`ke/wp_gate.py` |

配套工件（仓内其他位置）：

* `schemas/work-package-contract.schema.json` — 标准工作包契约（可直接 `$ref`）
* `schemas/extraction-summary.schema.json` — `extraction_summary.json` 结构
* `schemas/extraction-skill.schema.json` — 抽取技能注册表条目 + 生命周期前置条件
* `ke/wp_gate.py` — 结构门 + 证据门 + 语义门准备 + 验证阶梯
* `scripts/validate_work_package.py` — CLI（批量扫、在线/离线源、技能库校验）
* `scripts/build_extraction_fixtures.py` — 由合成源推导离线夹具（禁止手改夹具）
* `extraction-skills/` — 六类报告分型骨架 + 技能库注册表 + 生产/审核 prompt
* `tests/test_wp_gate.py` — 40 项门禁自测

入口命令：

```bash
python scripts/validate_work_package.py --root <packages> --online \
    --review-ledger-dir <ledgers> --tickets-dir <tickets> \
    --skills extraction-skills/registry.json --json runs/gate-report.json
python -m pytest tests/test_wp_gate.py -q
```
