# EEXI Attained 闭合链路精度传递验证

## 目标
将 EEXI attained 能力从 WITHHELD(99.9%误差) 推进到 REAL(<15%误差)

## 方法
建立端到端同源链路：Holtrop 阻力 → BEMT 推进 → EEXI attained

## 结果
- 三船对标误差: 12.1% / 7.0% / 1.0% (均 <15%)
- 链路同源: grep 验证 4 处调用
- 敏感度分析: V_ref 主导 (57.1%)
- 退化一致性: 验证通过

## 产物
- 实现: backend/api/green_shipping.py::_gn_eexi_from_physics()
- 测试: backend/tests/test_eexi_chain_p74n02.py
- 验证: artifacts/eexi_verification.json
- 报告: docs/eexi_verification_report_p74n02.md

## 结论
EEXI attained 能力: WITHHELD → REAL