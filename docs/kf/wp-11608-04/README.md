# wp-11608-04 — independent review of report 11608

工序：`04-independent-review`（lane C）｜报告：report_id=11608｜scenario：`p73w3-n04-fvm-numerical-viscosity`
源哈希：`sha256:8a9602aca712ab3ac8656d7382e0fef762ba0f30657cf8b631b36ba514e8db62`（7342 字符 / 10392 字节 UTF-8）
审核对象：上游 `wp-11608-01`（asset registration）+ 报告正文；**不读**生产者代码/测试/产物/解释。
disposition：**needs-fix**（major 3 / medium 2 / minor 2 / info 1）；本轮标 verified 的断言数 = 0。

## 一键复跑

```bash
python3 runs/wp-11608-04/fetch_source.py         # 取源 + 校验 sha256（需 TENSOR_AGENT_USER/PASS/TENSOR_API_BASE）
python3 runs/wp-11608-04/independent_checks.py   # -> checks.json（四格式重实现 + 6 判据块 + 负向对照）
python3 runs/wp-11608-04/build_review.py         # -> review_report.json / review_events.json / 4 张图
python3 runs/wp-11608-04/make_kf_result.py       # -> kf_result 信封（schema 校验）+ docs staging
python3 runs/wp-11608-04/make_report.py          # -> KF-RESULT-wp-11608-04.md（本目录）
python3 runs/wp-11608-04/publish_report.py       # -> 平台报告（mission 19821）+ publish.json 回执
python3 -m pytest tests/test_kf_wp11608_04.py -q # 13 项验收不变量
```

## 目录内容

| 文件 | 说明 |
|---|---|
| `KF-RESULT-wp-11608-04.md` | 报告正文（六段）+ 唯一 json 代码块 |
| `review_report.json` | 主产出：8 findings / 独立性 / 检查清单 / disposition / 验收自检 |
| `review_events.json` | 审核决策事件账本 |
| `checks.json` | 独立重算的全部数字（机器生成，零手抄） |
| `kf_result.wp-11608-04.json` | 平台结果信封（`provenance.source_hash` = 契约哈希） |
| `independent_checks.py` / `build_review.py` / `make_kf_result.py` / `make_report.py` / `fetch_source.py` / `publish_report.py` | 复现链 |
| `source_report_11608.md` | 源报告字节级副本（供 hermetic 测试比对哈希与引文 span） |
| `fig1..fig4*.png` | 四张结果图（数字均由 checks.json 注入） |
| `verification.json` | 本地机械校验清单（`gate=pending_platform_verification`，无 verified 标记） |
| `publish.json` | 平台发布回执（无认证材料） |

## 结论速览

- 成立（独立重算）：迎风 `ν_th=cΔx(1-C)/2`；CD2 纯色散 `|G(π/2)|=1.118/1.281`；L–W 近乎无耗散（界成立，裕度 5.6 倍而非 1–2 个量级）；`ν ∝ Δx`（比值 0.4994–0.5000）。
- 证伪 / 不可复现：§3.1 逐行 ν_meas（精确偏差小 1.7–124 倍，C=0.5 三行反号）；QUICK 前阶黏性公式（应为 `cΔx(5-4C)/8`，且**大于**迎风）；§3.3 L–W 值与其 θ/C 标度；§3.4 增长区间（仅 2/9 工况成立）；判据 (b) 的绝对/相对定义冲突与 `|G|→0` 除零。
- 未核验（记为 not_run）：8 个工件路径与字节数、227 KB JSON、"57 passed"、commit；2D 交叉导数项。