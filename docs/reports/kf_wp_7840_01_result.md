# KF-RESULT wp-7840-01

**package_id** `wp-7840-01` · **task_type** `01-asset-registration` · **report_id** `7840` · **lane** C · **status** draft
**source** `tensor://reports/7840` (field `markdown`) ·
**source_hash** `sha256:eaf940b5a606c4b1ad613ea2283219434fb88265bee60999953e2f33d35a2a3d`
**mission** 15602 · **scenario** IN59-N09 · **报告标题** IN59-N09 ACV/SES 气垫压力-泄漏-波阻闭式链
**tags** `kf-wp:wp-7840-01` `asset-registration` `report-7840`

> verification 由平台门计算；本文件只做自检（honest self-check），不含 `verified` 标记。

---

## ① 本工序做了什么

工作包 `wp-7840-01` = `01-asset-registration`（资产登记，不做抽取）。做的三件事：

1. **钉住源资产身份**：从平台取回 `report_id=7840` 的 `markdown` 字段（6896 字符 /
   10262 字节 UTF-8），本地重算 sha256，与契约 `input.source_hash`
   逐字符比对一致，字符数与 `input.chars` 一致。
2. **枚举可解析资产**：登记 25 个资产 = 源 markdown 1 + `figures[]` 元数据 4 +
   正文路径引用 20（occurrence 级，同一文件在不同行算不同资产）。
   每条引用都带**逐字引文定位器**（行号 + 该行原文），不靠记忆重述。
3. **如实标注可解析性**：1 个 resolved（源 markdown）、
   4 个 metadata_only（平台只存图名+图注，无 png 载荷，故不声明任何 figure 哈希）、
   20 个 unresolved（报告声明的 `repository=ship-performance-platform` 树不在本工作包可达范围）。
   **不把 unresolved 写成 resolved，不为凑数生成 claims**（`claims=[]` 是契约允许的完整结果）。

## ② 怎么做的（步骤/工具/关键设置）

| 步骤 | 做法 | 关键设置 |
|---|---|---|
| 1 取源 | `GET /api/v1/tensor/reports/7840`（Bearer 登录） | 只取 7840，未读任何其它 report_id |
| 2 校身份 | `sha256(markdown.encode("utf-8"))` 与契约常量比对 | 不一致即 `SystemExit`，不降级继续 |
| 3 扫引用 | 3 类扫描：markdown 图片 `![..](path)`、反引号路径、裸路径（含 `fig*.png` 通配与 `path:line` 行锚） | 目录型引用单独成类；裸文件名按同一行引用的目录拼接 |
| 4 解析 | 只在 `TensorKnowledge` 交付工作树内解析（含 glob 展开），不跨仓猜测 | 解析不到 = `unresolved` + 写明原因 |
| 5 反查漏 | **第二套独立写法**的 tokenizer 全篇重扫，与登记表做差集 | 差集非空即判门失败（`coverage_sweep_gap_free`） |
| 6 自检 | 逐条重跑 acceptance（重新拉活源，不复用 build 期状态） | `docs/kf/wp-7840-01/verification.json` |
| 7 交付 | `kf_result.json` 信封见文末唯一 json 块 | 结构照 `schemas/kf_result.v1.schema.json` |

一键复跑（工作树根目录）：

```bash
python3 scripts/kf/build_asset_manifest_7840.py build result verify && \
python3 scripts/kf/render_report_7840.py render && \
python3 -m pytest -q tests/test_kf_wp_7840_01.py
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-7840-01/asset_manifest.json` | 全网关主体：25 资产、25 条逐字定位器、`coverage_sweep` 漏检差集、`artifact_endpoint_probe` 探测记录（两个附件端点均 `http_404`，故不假设存在附件事务） |
| `docs/kf/wp-7840-01/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs），`provenance.source_hash` 与活源一致 |
| `docs/kf/wp-7840-01/verification.json` | 自检判定（acceptance + 边界自检），`all_pass=true` |
| `scripts/kf/build_asset_manifest_7840.py` | 可复跑构建器 + 独立 verifier + 信封生成 |
| `scripts/kf/render_report_7840.py` | 本报告渲染器（数字/引文全部注入，零手抄） |
| `tests/test_kf_wp_7840_01.py` | 13 个 pytest 不变量断言（含活源逐字引文与漏检差集） |

**资产总表**（`*` = 路径由同行目录拼接而来，非逐字原文；见 manifest 的 `path_reference_constructed`）：

| asset_id | class | resolution | path_reference(literal) | L |
|---|---|---|---|---|
| r7840:source | report_markdown | resolved | `—` | — |
| r7840:figure:01 | embedded_figure | metadata_only | `—` | — |
| r7840:figure:02 | embedded_figure | metadata_only | `—` | — |
| r7840:figure:03 | embedded_figure | metadata_only | `—` | — |
| r7840:figure:04 | embedded_figure | metadata_only | `—` | — |
| r7840:ref:01 | directory_reference | unresolved | `backend/physics/acv/` | 99 |
| r7840:ref:02 | source_code_reference | unresolved | `static_equilibrium.py`* | 99 |
| r7840:ref:03 | source_code_reference | unresolved | `leakage.py`* | 99 |
| r7840:ref:04 | source_code_reference | unresolved | `wave_resistance.py`* | 99 |
| r7840:ref:05 | source_code_reference | unresolved | `closed_chain.py`* | 99 |
| r7840:ref:06 | source_code_reference | unresolved | `backend/api/acv.py` | 100 |
| r7840:ref:07 | source_code_reference | unresolved | `tests/test_acv_closed_chain.py` | 101 |
| r7840:ref:08 | figure_reference | unresolved | `artifacts/acv_in59_n09/fig1_resistance_speed.png` | 165 |
| r7840:ref:09 | figure_reference | unresolved | `artifacts/acv_in59_n09/fig2_wave_resistance_fn.png` | 171 |
| r7840:ref:10 | figure_reference | unresolved | `artifacts/acv_in59_n09/fig3_power_ledger.png` | 177 |
| r7840:ref:11 | figure_reference | unresolved | `artifacts/acv_in59_n09/fig4_resistance_breakdown.png` | 183 |
| r7840:ref:12 | source_code_reference | unresolved | `backend/physics/acv/static_equilibrium.py` | 254 |
| r7840:ref:13 | source_code_reference | unresolved | `backend/physics/acv/leakage.py` | 255 |
| r7840:ref:14 | source_code_reference | unresolved | `backend/physics/acv/wave_resistance.py` | 256 |
| r7840:ref:15 | source_code_reference | unresolved | `backend/physics/acv/closed_chain.py` | 257 |
| r7840:ref:16 | source_code_reference | unresolved | `backend/api/acv.py` | 258 |
| r7840:ref:17 | source_code_reference | unresolved | `tests/test_acv_closed_chain.py` | 259 |
| r7840:ref:18 | figure_reference | unresolved | `artifacts/acv_in59_n09/fig*.png` | 260 |
| r7840:ref:19 | data_artifact_reference | unresolved | `artifacts/acv_in59_n09/acv_closed_chain_data.json` | 261 |
| r7840:ref:20 | source_code_reference | unresolved | `tests/test_acv_closed_chain.py` | 276 |

## ④ 证据定位表（claim/字段 → 原文引文片段，逐字）

本工序 `claims=[]`（不做抽取），下面给出的是**登记字段**的证据定位：每条路径引用都能在同一行原文里逐字找到。
行号为活源 markdown 的 1-based 行号，`asset_manifest.json` 的 `locator.line/quote` 与之逐字相等（自检逐条重解过）。

| # | asset | 字段 | 原文引文（逐字） | 行 |
|---|---|---|---|---|
| 1 | r7840:ref:01 | path_reference | `- **物理模块**：`backend/physics/acv/`（static_equilibrium.py, leakage.py, wave_resistance.py, closed_chain.py）` | L99 |
| 2 | r7840:ref:02 | path_reference | `- **物理模块**：`backend/physics/acv/`（static_equilibrium.py, leakage.py, wave_resistance.py, closed_chain.py）` | L99 |
| 3 | r7840:ref:03 | path_reference | `- **物理模块**：`backend/physics/acv/`（static_equilibrium.py, leakage.py, wave_resistance.py, closed_chain.py）` | L99 |
| 4 | r7840:ref:04 | path_reference | `- **物理模块**：`backend/physics/acv/`（static_equilibrium.py, leakage.py, wave_resistance.py, closed_chain.py）` | L99 |
| 5 | r7840:ref:05 | path_reference | `- **物理模块**：`backend/physics/acv/`（static_equilibrium.py, leakage.py, wave_resistance.py, closed_chain.py）` | L99 |
| 6 | r7840:ref:06 | path_reference | `- **API**：`backend/api/acv.py`（FastAPI 端点）` | L100 |
| 7 | r7840:ref:07 | path_reference | `- **测试**：`tests/test_acv_closed_chain.py`（35 个 pytest 用例）` | L101 |
| 8 | r7840:ref:08 | path_reference | `![Resistance-Speed Curve](artifacts/acv_in59_n09/fig1_resistance_speed.png)` | L165 |
| 9 | r7840:ref:09 | path_reference | `![Wave Resistance vs Fn_c](artifacts/acv_in59_n09/fig2_wave_resistance_fn.png)` | L171 |
| 10 | r7840:ref:10 | path_reference | `![Power Ledger](artifacts/acv_in59_n09/fig3_power_ledger.png)` | L177 |
| 11 | r7840:ref:11 | path_reference | `![Resistance Breakdown](artifacts/acv_in59_n09/fig4_resistance_breakdown.png)` | L183 |
| 12 | r7840:ref:12 | path_reference | `\| 静平衡 \| `backend/physics/acv/static_equilibrium.py` \| p_c = (W - L_hydro) / A_c \|` | L254 |
| 13 | r7840:ref:13 | path_reference | `\| 泄漏 \| `backend/physics/acv/leakage.py` \| Orifice 模型 + 风机功率 \|` | L255 |
| 14 | r7840:ref:14 | path_reference | `\| 波阻 \| `backend/physics/acv/wave_resistance.py` \| Newman-Poole 闭式 \|` | L256 |
| 15 | r7840:ref:15 | path_reference | `\| 闭式链 \| `backend/physics/acv/closed_chain.py` \| 三段串联 + 排水船对比 \|` | L257 |
| 16 | r7840:ref:16 | path_reference | `\| API \| `backend/api/acv.py` \| FastAPI 端点 \|` | L258 |
| 17 | r7840:ref:17 | path_reference | `\| 测试 \| `tests/test_acv_closed_chain.py` \| 35 用例，全部通过 \|` | L259 |
| 18 | r7840:ref:18 | path_reference | `\| 图 \| `artifacts/acv_in59_n09/fig*.png` \| 4 幅结果图 \|` | L260 |
| 19 | r7840:ref:19 | path_reference | `\| 数据 \| `artifacts/acv_in59_n09/acv_closed_chain_data.json` \| 完整数值结果 \|` | L261 |
| 20 | r7840:ref:20 | path_reference | `*测试执行：pytest tests/test_acv_closed_chain.py -v → 35 passed*` | L276 |

> 上表共 20 条行级定位；另有 5 条非行级定位：源 markdown 1 条（`report_field=markdown`）+ `figures[]` 4 条（按索引定位，载荷缺失）。

## ⑤ 注意点与局限

1. **报告声明的附件/代码仓不在本工作包边界内**：`20` 个 unresolved 全部指向
   `ship-performance-platform` 的 `backend/physics/acv/*`、`backend/api/acv.py`、`tests/test_acv_closed_chain.py`、
   `artifacts/acv_in59_n09/*`。登记器严格只在交付工作树内解析——**有就是有，没有就是 unresolved**，不做跨仓臆断。
2. **`figures[]` 无字节载荷**：平台记录只有 `name`+`caption`，`png_base64` 为空串。因此 4 条 figure 资产标
   `metadata_only`，`sha256=null`；把图哈希写成任何值都属伪造。
3. **occurrence 级身份**：`tests/test_acv_closed_chain.py` 在 L101/L259/L276 三次出现 → 3 个 asset_id；
   `backend/physics/acv/*.py` 在 L99 与 L254-L257 各出现一次 → 各自独立。去重视图见 `summary.distinct_referenced_paths=13`。
4. **自检≠验收**：`verification.json` 是我自己的检查器；权威判定在平台门。本文件不写 `verified`。
5. **踩坑（本轮自查发现并修正的两个扫描缺陷）**：
   - 目录正则把数学片段 `V/√(gL_c)` 里的 `V/` 误判成目录 → 加"路径段 ≥2 字符"约束后消失；
   - L99 的裸文件名（`static_equilibrium.py` 等）原本没有父目录，路径不完整 → 改为与同行引用的
     `backend/physics/acv/` 拼接，并**显式标注 `path_reference_constructed=true`** 且保留 `path_reference_literal`，
     避免推断路径冒充原文。
6. **未做（属其它工序）**：不抽取 claim、不判 report_type、不做数值复算/对标、不写 knowledge node。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 依据（自检器输出） |
|---|---|---|
| `valid_json` | ✓ | json.loads OK on asset_manifest.json |
| `schema_pass` | ✓ | envelope_missing=[] envelope_extra=[] provenance_ok=True manifest_missing=[] assets_missing_fields=[] |
| `source_locator_resolvable` | ✓ | checked 25 locators against live markdown (277 lines); unresolvable=[] |
| `source_hash_matches` | ✓ | recomputed=eaf940b5a606c4b1ad613ea2283219434fb88265bee60999953e2f33d35a2a3d manifest=eaf940b5a606c4b1ad613ea2283219434fb88265bee60999953e2f33d35a2a3d envelope=eaf940b5a606c4b1ad613ea2283219434fb88265bee60999953e2f33d35a2a3d contract=eaf940b5a606c4b1ad613ea2283219434fb88265bee60999953e2f33d35a2a3d chars=6896/6896 |
| `no_duplicate_ids` | ✓ | assets=25 unique=25 |
| `coverage_sweep_gap_free` | ✓ | independent sweep tokens=16 unregistered=[] recorded==recomputed=True |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✓ | claims=0 violating=0 (empty array: vacuously satisfied per contract notes) |

边界自检（契约之外的加严项）：

| 检查 | 结果 | 依据 |
|---|---|---|
| `no_verified_marks` | ✓ | neither manifest.claims nor envelope.claims carries a 'verified' status |
| `single_report_scope` | ✓ | every report_id field in the package outputs equals 7840 |
| `constructed_paths_flagged` | ✓ | 4 constructed path(s) carry both literal and joined forms |
| `no_forced_claims` | ✓ | claims array empty by contract note; no synthesis to hit a metric |

`all_pass = true`；无失败项，故本单无 honest-FAIL 需要申报——
但第 ⑤ 节的 2/3 两条是**能力边界**（figure 无载荷、跨仓引用不可达），不是粉饰项。

---

## 唯一结果 JSON

```json
{
  "package_id": "wp-7840-01",
  "task_type": "01-asset-registration",
  "report_id": "7840",
  "provenance": {
    "source_uri": "tensor://reports/7840",
    "source_field": "markdown",
    "source_hash": "sha256:eaf940b5a606c4b1ad613ea2283219434fb88265bee60999953e2f33d35a2a3d",
    "hash_algo": "sha256",
    "hashed_bytes": "markdown encoded as utf-8",
    "source_chars": 6896,
    "source_bytes_utf8": 10262,
    "producer": "scripts/kf/build_asset_manifest_7840.py",
    "emitted_at": "2026-11-12T01:29:15.767304+00:00",
    "notes": "asset registration only; no extraction performed; no claim status asserted here (verification is platform-gated)"
  },
  "outputs": {
    "asset_manifest.json": {
      "path": "docs/kf/wp-7840-01/asset_manifest.json",
      "sha256": "0b3980382c4d3cc0f87fe1aa7e96083f1fd40d4cbfb7ba01178f718b6b36653c",
      "bytes": 27184,
      "asset_count": 25,
      "by_kind": {
        "report_markdown": 1,
        "embedded_figure": 4,
        "directory_reference": 1,
        "source_code_reference": 13,
        "figure_reference": 5,
        "data_artifact_reference": 1
      },
      "by_resolution": {
        "resolved": 1,
        "unresolved": 20,
        "metadata_only": 4
      },
      "claims": 0
    }
  }
}
```
