# KF-RESULT wp-5687-01

## ① 本工序做了什么

- 执行报告→知识产线的单一工序 **01-asset-registration**（源资产登记），对象仅 report_id=5687。
- 确认源 markdown 字节哈希与契约一致：`sha256:a4eaa764c52e072a87f6629009b94e3a5ae97d4aab543fe851599a732fcfeb3d`（4236 字符 / 6382 字节 UTF-8）。
- 列出全部可解析附件/工件：1 源 markdown（resolved）+ 3 图元数据（metadata_only）+ 7 条正文路径引用（unresolved，显式状态）= **11 个资产**，每条带行号逐字定位。
- 按契约不做抽取：claims 为空数组；未标任何 verified（verification 由平台门计算）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET /api/v1/tensor/reports/5687`（Bearer 登录），取 `markdown` 字段；psql 直连被拒（permission denied），全程走平台 API。
2. **哈希校验**：对 utf-8 字节重算 sha256，与契约 `source_hash` 及 `chars=4236` 双比对，不一致即中止（build 内置硬门）。
3. **引用扫描**：三组正则（markdown 图片 / 反引号路径 / 裸路径）逐行扫描，命中按 occurrence 级登记（identity=(path, line)），quote 直接取自抓取字节，零手抄。
4. **解析范围**：只在 TensorKnowledge 交付 worktree 内解析；指向 TensorPlatform 仓的 `tools/chronicle/*` 等引用越界，显式标 `unresolved`（显式状态，非失败判决）。
5. **图元数据**：平台记录 figures[] 仅存 name+caption、无 png_base64 载荷 → `metadata_only`（不可算哈希，如实登记）。
6. **生成器**：`scripts/kf/build_asset_manifest_5687.py` 一键 build+verify；verify 独立重取活库源、重跑 6 项验收并落 `verification.json`。

repro_cmd：

```
cd <TensorKnowledge worktree> && python3 scripts/kf/build_asset_manifest_5687.py build verify
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-5687-01/asset_manifest.json` | 11 资产（1 源 resolved + 3 图 metadata_only + 7 引用 unresolved），claims=[]，sha256=3766d86fed43dfb57fd1e16566678314182fb59c1a195e322075a6ceaa5d2e0c，10450 B |
| `docs/kf/wp-5687-01/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs），provenance.source_hash 与活库重算一致 |
| `docs/kf/wp-5687-01/verification.json` | 6 项验收自检 all_pass=true |
| `docs/kf/wp-5687-01/source_markdown_5687.md` | 源 markdown 逐字缓存（审计用，4236 字符，非改写） |
| `scripts/kf/build_asset_manifest_5687.py` | 生成器+校验器（build/verify 两步，verify 独立重取活库源） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

下表引文均为源 markdown 逐字子串（verify 步程序化断言 line==quote 且 quote∈md，非人工誊抄）：

| claim/字段 | 定位 | 原文引文（行号） |
|---|---|---|
| 源标题 | L1 | `# IN18-T2 战史官编年史与指标计算器成熟化（TensorPlatform · tools/chronicle）` |
| r5687:ref:01 collector.py | L22 | 按任务书「若 T1 未并 main 则自带最小采集并声明」：本单自带 `tools/chronicle/collector.py` |
| r5687:ref:02 metrics.py | L30 | 2. **5 项指标**（`tools/chronicle/metrics.py`，纯函数 + PG 装载分离，离线可测）： |
| r5687:ref:03/04 crosscheck.py / metrics.py | L36 | 3. **交叉验证**（`crosscheck.py`）：独立手算 SQL（查询文本不复用 metrics.py 构造） |
| r5687:ref:05 GLOBAL_CHRONICLE.md | L40 | 工件 `artifacts/chronicle/`（GLOBAL_CHRONICLE.md + 5 指标 CSV + crosscheck + 3 图）。 |
| r5687:ref:06/07 crosscheck.py / metrics.py | L84 | 基准 = 独立手算 SQL（crosscheck.py，查询文本与 metrics.py 不同源）： |
| figures 01–03 | 平台 figures 元数据（无字节载荷） | fig1_parallelism_saturation.png / fig2_coverage_heatmap.png / fig3_bp_coverage.png |
| source_hash | 契约常量 + 本地重算 | sha256:a4eaa764c52e072a87f6629009b94e3a5ae97d4aab543fe851599a732fcfeb3d（重算见 verification.json） |

## ⑤ 注意点与局限

- 仅登记：无抽取、无 claim 生成、无 verified 标记（verification 由平台门计算）。
- 7 条路径引用指向 TensorPlatform 仓（tools/chronicle/*、GLOBAL_CHRONICLE.md 等），在本 worktree 边界之外，显式标 `unresolved`——是显式状态而非失败判决。
- 3 张图在平台记录中无 png_base64 载荷 → `metadata_only`，不可算字节哈希，如实登记。
- 目录引用 `artifacts/chronicle/` 非文件，未登记为资产；其中文件 GLOBAL_CHRONICLE.md 已登记。
- 上游报告自身结论（4/4 PASS 等）不在本工序复验范围；本工序只登记资产。
- 本工序无新图：纯登记/文档任务，未生成任何新图；源报告 3 图无字节载荷可再嵌入，故 figures=[]。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 证据 |
|---|---|---|
| valid_json | ✅ | json.loads OK（verification.json） |
| schema_pass | ✅ | missing_top=[] missing_provenance=[] |
| source_locator_resolvable | ✅ | 11/11 locators 可解析（行号+逐字引文） |
| source_hash_matches | ✅ | actual=declared=contract=a4eaa764…feb3d |
| no_duplicate_ids | ✅ | 11 ids, 11 distinct |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | 0 claims（契约允许空数组） |
| 边界：只碰 report_id=5687 | ✅ | 脚本常量 REPORT_ID=5687，未读写其它 report_id |
| 零手抄 | ✅ | 全部引文程序化取自抓取字节；verify 独立重取活库源重断言 |

honest-FAIL：无。

## KF-RESULT

```json
{
  "package_id": "wp-5687-01",
  "task_type": "01-asset-registration",
  "report_id": "5687",
  "provenance": {
    "source_uri": "tensor://reports/5687",
    "source_field": "markdown",
    "source_hash": "sha256:a4eaa764c52e072a87f6629009b94e3a5ae97d4aab543fe851599a732fcfeb3d",
    "hash_algo": "sha256",
    "hashed_bytes": "markdown encoded as utf-8",
    "source_chars": 4236,
    "source_bytes_utf8": 6382,
    "fetched_via": "GET /api/v1/tensor/reports/5687",
    "generator": "scripts/kf/build_asset_manifest_5687.py",
    "contract_version": "1.0"
  },
  "outputs": {
    "asset_manifest.json": {
      "path": "docs/kf/wp-5687-01/asset_manifest.json",
      "sha256": "3766d86fed43dfb57fd1e16566678314182fb59c1a195e322075a6ceaa5d2e0c",
      "bytes": 10450,
      "asset_count": 11,
      "claims": 0
    }
  }
}
```
