# TK agent cases — 知识 ↔ 数值的对接面（m19445）

机器可读判据：`summary.json`；逐案：`case-a-taylor-green.json`、`case-b-provenance.json`、
`case-c-exactness-scope.json`。所有数字由 `runs/oss-lbm-kruger-8676/validation_summary.json` / `runs/oss-lbm-kruger-8676/kruger_bench_results.json` 程序化注入，
`pytest tests/test_tk_agent_cases.py` 逐条回读校验（零手抄）。

| case | 问题 | 维度 | 判定 | 失败项 |
|---|---|---|---|---|
| case-a-taylor-green | Taylor-Green 涡衰减：知识卡上的精度主张能否被复现？ | D2(类型) → 可复现数值：claim 的精度主张必须落到一条被记录的运行工件上 | `pass_with_scope_exclusion` | ib_lbm_centreline_err |
| case-b-provenance | 溯源：这张卡引用的误差数字到底从哪来？链到哪一层为止？ | D4(溯源定位) → 结构化完整性与活性的区分 | `structural_complete_liveness_withheld` | — |
| case-c-exactness-scope | 精确性边界：引用误差能否被当成「分辨率无关」的结论？ | D3(信任) × 精确性粒度：引用值 / 复现值 / 判据三层必须分开陈述 | `pass_with_granularity_constraint` | — |

## 关键数字（判据 3%）

| 量 | 值 | 来源 |
|---|---|---|
| TG 能量衰减偏差 NX=32/64/128 | -1.531% / -0.383% / -0.096% | `runs/oss-lbm-kruger-8676/validation_summary.json` |
| L2(u_x) 实测收敛阶（32→64 / 64→128） | 2.002 / 2.003 | 同上 |
| Poiseuille(BB) 剖面 L2 | 7.57e-16 | `runs/oss-lbm-kruger-8676/kruger_bench_results.json` |
| IB-LBM 中心线偏差 | -6.47%（出界，登记为 honest-FAIL） | `runs/oss-lbm-kruger-8676/validation_summary.json` |

图：`fig-taylor-green.png`（衰减 + 收敛）、`fig-poiseuille.png`（端口 vs IB-LBM）、
`fig-exactness-scope.png`（精确性等级）。

## 未闭合项（如实）

- claim `tkc:oss-lbm:kruger-taylor-green-decay` 无 claim 级 PROV 记录（包内 provenance 未覆盖全部 claim）→ lineage 只能主张 citation 级。
- 上游 `lbm-principles-practice/code` 未 vendor → 定位符活性 WITHHELD。
- 无 256² 以上分辨率运行 → 渐近精度断言 WITHHELD。

## 复现

```bash
pytest tests/test_tk_agent_cases.py -q          # 校验 JSON↔工件、图与判据
python tests/test_tk_agent_cases.py --regen     # 由工件重生成 case/图（数据不再手抄）
```
