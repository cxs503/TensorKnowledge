# KF 工作包 wp-9645-01 资产登记报告

## ① 案例介绍

- **报告 ID**: 9645
- **标题**: IN101-N09 ISO 19906 冰压设计分项系数目标可靠度反标定（成熟化）
- **场景键**: ice_partial_factors_target_inverse
- **标签**: IN101-N09, ISO19906, partial-factors, FORM, importance-sampling, negative-control, ice
- **状态**: published
- **创建时间**: 2026-11-09T07:20:15.875461+00:00
- **Mission ID**: 8350

## ② 怎么做的

本工作包执行 KF 产线工序 01（asset-registration），职责边界：

- 只读 report_id=9645 的 record/markdown
- 计算源 markdown 的 SHA-256 哈希并自证
- 索引 markdown 结构（标题层级/行号/字符数/段哈希）
- 扫描引用的工件路径与外部 API 端点
- **不做抽取**：claims 为空数组（合同允许）
- 零手抄：所有数值由脚本从 API 返回体计算

## ③ 计算结果

| 指标 | 值 |
|---|---|
| 源字符数 | 11824 |
| 源 UTF-8 字节数 | 15967 |
| 源行数 | 196 |
| SHA-256 | `sha256:a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00` |
| 哈希匹配契约 | True |
| 结构段数 | 8 |
| 声明图件数 | 6 |
| 引用工件数 | 3 |
| 外部引用数 | 0 |

## ④ 结果图

本工序为纯文档/后端资产登记任务，无可视化场量云图或比较曲线。
asset_coverage.png 为资产覆盖范围示意图（程序化生成）。

## ⑤ 注意点

- 引用的工件路径位于工作树之外，本包边界禁止越界读取
- 存在性/内容一致性留给上游门或后续工序
- 本工序不下载图件载荷，仅登记 figures 元数据

## ⑥ 误差判定

本工序为资产登记（非数值计算），无误差判定项。
源哈希自证：computed == contract_expected → True
