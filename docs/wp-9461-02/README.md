# wp-9461-02 · 02-classification-parse（report 9461）

工序：给报告 9461（EEOI/CII 营运指标闭环验证，scenario `green-navigation.eeoi_cii`）打类型/主题标签 + 结构切分。
**不做抽取**（契约 `objective.register_assets=false`，notes「不做抽取」），不给任何结论标 verified。

判定：`report_type=experimental-validation`，`selected_skill_id=xsk-experimental-validation`；
备选 `algorithm-implementation`(rank 2)、`scientific-computation`(rank 3) 及被否理由见 `classification.json.report_type_alternatives`。

| 文件 | 用途 |
|---|---|
| `KF-RESULT-wp-9461-02.json` | kf_result.v1 交付载荷（报告 markdown 里唯一 json 块的逐字节副本） |
| `classification.json` | 工序产物：类型判定 + 7 主题标签 + 22 段结构切分 + 12 条判定断言（20 个逐字定位器）+ registry 信号实测 |
| `report.md` | 六段工序报告（已发布到平台，report id 18015） |
| `posted.json` | 平台发布回执（id/title/status/tags/figures） |

复跑：

    python3 scripts/kf_wp9461_02_classify.py --check
    python3 scripts/kf_wp9461_02_publish.py --dry-run     # 只组装，不递交

原文快照 `runs/wp-9461-02/source_9461.md` 的 sha256 必须等于
`c839141234f9b547f153399b3e09784457d55832f3449d16c7b5b21a278a92b1`，否则构建脚本拒绝继续。
