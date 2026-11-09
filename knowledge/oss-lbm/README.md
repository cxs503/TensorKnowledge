# OSS-LBM Knowledge Package

LBM 开源多相/MCMP 知识落库 TensorKnowledge（mission 8634，锚点 FEAT-TK-OSS-LANDING）。

## 概览

| 指标 | 值 |
|---|---|
| Claims | 23 |
| Evidence | 30 |
| Provenance | 8 |
| 覆盖仓 | openLBMPM, sailfish, lbmpy, Krüger textbook, MPLBM-UT, ludwig, mcmp-lbm, LUMA |
| GAP 锚点 | GAP-LBM-MCMP-POISEUILLE, GAP-LBM-MCMP-HIGHDENSITY |

## 结构

```
knowledge/oss-lbm/
├── claims/          # 23 条 claim JSON（schema: claim-record）
├── evidence/        # 30 条 evidence JSON（schema: evidence-record）
├── provenance/      # 8 条 provenance JSON（schema: provenance-record）
├── validate_oss_lbm.py  # 自带校验器（schema+xref+计数+GAP 锚点）
└── README.md        # 本文件
```

## 知识来源

每条 claim 基于实读 oss-inventory 报告中的源码分析（非搬运盘点报告原文），evidence 定位 = repo@commit + 文件:行 + 逐字 quote。

### 覆盖的开源仓

| 仓 | 核心能力 | 证据数 |
|---|---|---|
| openLBMPM | Porter 2012 显式力 / 颜色梯度 CSF / 各向同性 stencil / P-R EOS（未启用） | 6 |
| sailfish | 自由能 Cahn-Hilliard / 双组分 SC 重均速度 / sympy+mako 代码生成 | 5 |
| lbmpy | 碰撞谱系（SRT→Cumulant）/ 9 力项模型 / MCMP 教程 / SCMP 密度比 | 4 |
| Krüger textbook | 两组分 SC / Young-Laplace 标定 / Guo 力项 / Poiseuille 验证 / Taylor-Green | 5 |
| MPLBM-UT | 双 lattice SC / Palabos 封装 / 润湿 BB / 无高密度比 | 4 |
| ludwig | 自由能+胶体耦合 | 1 |
| mcmp-lbm | MRT+Taichi / CS EOS / 稀疏存储 | 3 |
| LUMA | 多相内核族（SC/自由能/颜色梯度） | 1 |

## 验证

```bash
python3 knowledge/oss-lbm/validate_oss_lbm.py
python3 scripts/validate_epistemic_benchmark.py
```

两条校验均 ALL PASS。

## 认知纪律

- oss_solutions 表只是线索索引——每条记录基于实读对应仓源码后独立认定
- evidence 定位 = repo@commit + 文件:行 + 逐字 quote
- epistemic_status 保守：代码里白纸黑字 = established/descriptive
- 全部 review_events 空、review_status=draft、不自批

## GAP 锚点映射

每条 claim 的 notes 字段包含 `映射 feature_ledger: GAP-LBM-*` 指回 feature_ledger 锚点，供开发单按锚点消费。
