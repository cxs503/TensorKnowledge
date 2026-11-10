# AnchorCard: AC-IMO-MANEUVER-001 — IMO操纵性标准验证锚卡

## 元数据
- **Card ID**: AC-IMO-MANEUVER-001
- **Domain**: 实船与实验锚 × ITTC规程 (seatrial-experiment-ittc-seatrial)
- **Type**: Standard/Procedure Anchor
- **Created**: 2026-11-10
- **Mission**: m8817

## IMO操纵性标准 (Res. MSC.137(76))

### 回转试验判据
| 判据 | 限制值 | 单位 |
|------|--------|------|
| 进距(Ad) | ≤ 4.5 L | m |
| 横距(Tr) | ≤ 2.5 L | m |
| 稳定回转直径 | ≤ 5.0 L | m |

### Z形操舵判据
| 判据 | 限制值 | 单位 |
|------|--------|------|
| 第一超调角(10/10) | ≤ 10° | deg |
| 第二超调角(10/10) | ≤ 20° | deg |
| 第一超调角(20/20) | ≤ 20° | deg |
| 第二超调角(20/20) | ≤ 25° | deg |

### 停船判据
| 判据 | 限制值 | 单位 |
|------|--------|------|
| 停船距离 | ≤ 15 L | m |

## 验证判据
- 模拟回转直径与试验误差 < 10%
- Z形操舵超调角误差 < 15%
- 停船距离误差 < 10%

## KPI对齐
- 对齐 KPI-KB-10K: 操纵性 KPI-MAN-001

## 证据溯源
- IMO Resolution MSC.137(76) "Standards for Ship Maneuverability"
- ITTC Recommended Procedures 7.5-02-06-02
- ship-performance-platform-incoming ch03_maneuvering/maneuvering.py
