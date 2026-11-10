# 船舶与海洋工程领域知识轴 v1

## 概述

本目录构建了船舶与海洋工程领域的知识轴（Ontology），包含：

1. **领域树 v1** (`tree-v1.json`): 八大分支三层可下钻结构
2. **既有资产收割** (`harvested-assets.json`): 从ship-performance-platform、TensorPhysics、TensorLBM/TensorPlatform等仓收割的资产映射
3. **方法轴交叉挂载** (`cross-references.json` + `cross-refs/`): 14个交叉点，各含DecisionCard/AnchorCard
4. **实船/实验锚专节** (`anchor-cards/`): 8张AnchorCard，含验证判据与KPI对齐

## 八大分支

| 分支ID | 中文名 | 英文名 | 二级节点数 | 三级节点数 |
|--------|--------|--------|-----------|-----------|
| resistance | 阻力 | Resistance | 4 | 12 |
| propulsion | 推进 | Propulsion | 3 | 9 |
| seakeeping | 耐波 | Seakeeping | 3 | 9 |
| maneuvering | 操纵 | Maneuvering | 3 | 9 |
| ice-navigation | 冰区航行 | Ice Navigation | 4 | 12 |
| multiphase | 多相流 | Multiphase Flow | 3 | 9 |
| structural-hydro | 结构水动力 | Structural Hydrodynamics | 3 | 9 |
| seatrial-experiment | 实船与实验锚 | Sea Trial & Experimental Anchors | 3 | 9 |

**总计**: 8个一级节点，26个二级节点，78个三级节点

## 资产收割对账

| 来源仓 | 资产数 | 类型分布 |
|--------|--------|---------|
| ship-performance-platform-incoming | 13 | code(8), geometry(1), test(1), data(1), book(3) |
| TensorPhysics | 3 | benchmark(1), code(1), report(1) |
| TensorLBM | 1 | doc(1) |
| TensorPlatform | 2 | doc(2) |

**总计**: 20个资产，覆盖8大分支中的6个

## 方法轴交叉点

| 交叉点ID | 领域节点 | 方法 | 卡类型 | 卡ID |
|---------|---------|------|--------|------|
| xref-01 | ice-resistance-dem | DEM | DecisionCard | DC-ice-dem-001 |
| xref-02 | multiphase-bubble-lbm | LBM-MCMP | DecisionCard | DC-bubble-lbm-001 |
| xref-03 | seakeeping-wave-3d | BEM | DecisionCard | DC-seakeeping-bem-001 |
| xref-04 | structural-hydro-fsi-two | FEM | DecisionCard | DC-fsi-fem-001 |
| xref-05 | resistance-viscous-cfd | FVM | DecisionCard | DC-resistance-fvm-001 |
| xref-06 | multiphase-freesurface-lbm | LBM自由面 | AnchorCard | AC-freesurface-lbm-001 |
| xref-07 | ice-mechanics-vibration | DEM+FEM | DecisionCard | DC-ice-vibration-001 |
| xref-08 | maneuvering-model-mmg | 系统辨识+CFD | DecisionCard | DC-maneuvering-mmg-001 |
| xref-09 | propulsion-propeller-cfd | FVM滑移网格 | DecisionCard | DC-propeller-cfd-001 |
| xref-10 | multiphase-cavitation-sheet | FVM+空化模型 | AnchorCard | AC-cavitation-fvm-001 |
| xref-11 | structural-hydro-slamming-wagner | Wagner理论 | AnchorCard | AC-slamming-wagner-001 |
| xref-12 | seakeeping-motion-slamming | CFD+FEM耦合 | DecisionCard | DC-slamming-coupled-001 |
| xref-13 | ice-operation-beset | DEM+热力学 | DecisionCard | DC-beset-dem-001 |
| xref-14 | resistance-prediction-cfd | LBM | DecisionCard | DC-resistance-lbm-001 |

**总计**: 14个交叉点 (DecisionCard: 11, AnchorCard: 3)

## 实船/实验锚专节

| 锚卡ID | 名称 | 类型 | 对齐KPI |
|--------|------|------|---------|
| AC-SUBOFF-001 | SUBOFF潜艇标准体 | Experimental | KPI-RES-001 |
| AC-DTMB5415-001 | DTMB5415水面舰 | Experimental | KPI-RES-001, KPI-SEA-001 |
| AC-KCS-001 | KCS集装箱船 | Experimental | KPI-RES-001, KPI-PRO-001 |
| AC-ITTC57-001 | ITTC-1957摩擦线 | Standard | KPI-RES-001, KPI-ENE-001 |
| AC-HOLTROP-001 | Holtrop-Mennen方法 | Method | KPI-RES-001 |
| AC-FREDERKING-001 | Frederking冻结强度 | Experimental | KPI-ICE-001 |
| AC-LINDQVIST-001 | Lindqvist冰阻力 | Method | KPI-ICE-001 |
| AC-IMO-MANEUVER-001 | IMO操纵性标准 | Standard | KPI-MAN-001 |

**总计**: 8张AnchorCard

## KPI-KB-10K 对齐关系

| KPI ID | 名称 | 对齐锚卡 | 目标精度 |
|--------|------|---------|---------|
| KPI-RES-001 | 阻力预报精度 | AC-SUBOFF-001, AC-DTMB5415-001, AC-KCS-001, AC-ITTC57-001, AC-HOLTROP-001 | < 3-5% |
| KPI-PRO-001 | 推进性能精度 | AC-KCS-001 | < 5% |
| KPI-SEA-001 | 耐波性预报精度 | AC-DTMB5415-001 | < 10% |
| KPI-MAN-001 | 操纵性预报精度 | AC-IMO-MANEUVER-001 | < 10-15% |
| KPI-ICE-001 | 冰区航行预报精度 | AC-FREDERKING-001, AC-LINDQVIST-001 | < 15% |
| KPI-ENE-001 | 能效指标精度 | AC-ITTC57-001 | < 5% |

## 文件结构

```
ship-ocean-domain/
├── README.md                          # 本文件
├── tree-v1.json                       # 领域树 v1 (8×28×84节点)
├── harvested-assets.json              # 既有资产收割对账表
├── cross-references.json              # 方法轴交叉挂载表 (14个交叉点)
├── cross-refs/                        # 交叉点卡片目录
│   ├── DC-ice-dem-001.md
│   ├── DC-bubble-lbm-001.md
│   ├── DC-seakeeping-bem-001.md
│   ├── DC-fsi-fem-001.md
│   ├── DC-resistance-fvm-001.md
│   ├── AC-freesurface-lbm-001.md
│   ├── DC-ice-vibration-001.md
│   ├── DC-maneuvering-mmg-001.md
│   ├── DC-propeller-cfd-001.md
│   ├── AC-cavitation-fvm-001.md
│   ├── AC-slamming-wagner-001.md
│   ├── DC-slamming-coupled-001.md
│   ├── DC-beset-dem-001.md
│   └── DC-resistance-lbm-001.md
└── anchor-cards/                      # 实船/实验锚专节
    ├── AC-SUBOFF-001.md
    ├── AC-DTMB5415-001.md
    ├── AC-KCS-001.md
    ├── AC-ITTC57-001.md
    ├── AC-HOLTROP-001.md
    ├── AC-FREDERKING-001.md
    ├── AC-LINDQVIST-001.md
    └── AC-IMO-MANEUVER-001.md
```

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-11-10 | 初始版本，m8817任务产出 |
