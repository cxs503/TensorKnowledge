# KF 工作包 wp-9656-01 —— report 9656 资产登记（01-asset-registration）

本目录是工序产物的唯一落点（committed；`artifacts/` 被仓库 .gitignore 丢弃，故不放那里）。

| 文件 | 内容 |
|---|---|
| `KF-RESULT-wp-9656-01.md` | 交付正文（六段式），其中**唯一**一个 ```json 代码块 = `kf_result.json` 原样内容 |
| `asset_manifest.json` | 登记清单：源资产、记录内图、正文路径引用、表/节清单、integrity |
| `kf_result.json` | 结果信封（package_id / task_type / report_id / provenance / outputs / claims） |
| `verification.json` | acceptance 六项自检 + 定位器计数 + 内部一致性（manifest↔envelope 不自相矛盾） |
| `delivery_probe.json` | 回读本包自己发出的结果报告，实测平台持久化了什么（供下游判读图片字节可得性） |
| `figures/wp9656_01_source_locator_map.png` | 定位器分布图（行剖面 + kind/status 直方图） |

## 一键复跑

```bash
for c in build envelope verify figure; do python3 scripts/kf/wp9656_01_register.py $c; done
python3 scripts/kf/wp9656_01_report.py render     # 重渲染 KF-RESULT 正文
python3 scripts/kf/wp9656_01_report.py post       # 重新发布（mission 15664）
python3 scripts/kf/wp9656_01_report.py probe      # 回读自己发出的报告并记录实测
pytest tests/test_kf_wp9656_01.py tests/test_kf_wp9656_01_guards.py -q   # 离网不变量自检
```

`build/envelope/verify/probe` 需要 `TENSOR_API_BASE` / `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS`；
`figure` 与两组 pytest 离线可跑（源缓存 `runs/wp-9656-01/source_9656.md`）。

## 纪律

- 只碰 `report_id=9656`（源码内 `fetch_record` 对返回 id 做硬校验，越界即 abort）；
- 零抽取、零 claim、零 `verified` 标记（verification 由平台门计算）；
- 所有引文均为 argv 段切片的逐字引用，渲染期断言 `quote in source`；
- 未解析就记 `unresolved` / `metadata_only`，不编造哈希、不用 caption 猜图。