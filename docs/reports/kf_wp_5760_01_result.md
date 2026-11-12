# KF-RESULT wp-5760-01

> 工作包 `wp-5760-01`（task_type=`01-asset-registration`，lane C，交付仓 TensorKnowledge，status=draft）。
> 唯一对象：`report_id=5760`（`tensor://reports/5760`，source_field=`markdown`）。
> 本工序只登记源资产，**不做抽取、不生成 claim、不写任何 verified 标记**（verification 由平台门计算）。
> 本报告全部数字由 `scripts/kf/report_wp5760.py` 从 `asset_manifest.json` / `verification.json` / `kf_result.json`
> 程序化注入（下方 JSON 块由 `kf_result.json` 逐字节拷入），正文无手抄数字。

## ① 本工序做了什么

对报告 5760（IN20-R5 停摆自检自愈）执行"源资产登记"这一个动作：

1. **确认身份**：`report_id=5760` 存在且 `markdown` 字段可取；该字段 UTF-8 字节的 sha256 与契约 `source_hash` **逐字节一致**；字符数 6808 与契约 `chars` 相符（契约未给字节数，10847 bytes 为本包独立实测）。
2. **清点可解析资产**：把 markdown 里"可定位的东西"逐项登记为 52 个资产——文首源文档 1 个、章节标题 11 个、Markdown 表格 7 个、图引用 1 个、平台图元数据 1 个、文件路径引用 20 个、目录/glob 引用 5 个、无前缀文件名引用 5 个、复现命令块 1 个。
3. **给每条登记配可机器复算的定位**：`locator` = 字符区间 + 行号 + 原文引文（引文由 `markdown[start:end]` 切片得到，不是手打），因此"引文逐字可定位"是构造性成立的，并在验证阶段被独立重算一次。
4. **如实分级解析状态**：20 个 `resolved_in_source`（来源 markdown 内有字节）、31 个 `referenced_unresolved`（报告提到了，但目标字节不在本工作包边界内）、1 个 `declared_absent`（平台 `figures` 数组只有 name+caption，无 `png_base64`，零字节可声明）。
5. **claims 留空**：契约 notes 明确"claims 允许为空数组"，objective 也要求 `classify_report_type=false`，故 `claims: []`——没有抽取就没有可过期的断言，也没有任何断言被标成 verified。

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步 | 动作 | 工具 / 设置 |
|---|---|---|
| 1 | 取源：`GET {TENSOR_API_BASE}/tensor/reports/5760`，Bearer 用 `$TENSOR_AGENT_USER` 登录换取 | `scripts/kf/build_asset_manifest_5760.py fetch_report()`；只读，不写平台 |
| 2 | 落快照：markdown 原字节写 `runs/wp-5760-01/report_5760.md`，非 markdown 字段（title/scenario_key/tags/figures/mission_id/created_at）写 `report_5760_meta.json` | 快照 sha256 与契约哈希比对，供离线测试复算 |
| 3 | 定哈希：`sha256(markdown.encode("utf-8"))` | 契约值 `sha256:95a6ffec44f492fe4f7f39f8d6bb989d845f6a781cd5749197177b6c05308bfe`；不一致直接 `SystemExit`，绝不"先写后查" |
| 4 | 切定位：预先算每行起始偏移，`line_of(char)` 二分定位；`locator.quote = md[start:end]` | 构造性保证"引文逐字来自原文"，杜绝手抄漂移 |
| 5 | 分类引用：文件（带扩展名且含 `/`）、目录/glob（已知前缀或 `{a,b}/` 通配）、裸文件名（无目录） | 三次返工才收敛：先误捕 `systemd/`、`60 s/样本`（散文斜杠），再误捕 `pending/queued/ready/todo/not_started`、`since/fired/cooldown`（状态词表），最后给目录判定加"已知产物前缀"白名单才干净 |
| 6 | 解析校验：每个被引路径在**本工作树**内做存在性探测（`resolve_local`），结果写进 `local_resolution` | 跨仓不猜：报告产物属 TensorPlatform 仓，超出本工作包边界 → 一律 `unresolved` 并写明理由 |
| 7 | schema 校验：`jsonschema` draft-07 对 `asset_manifest.schema.json` 全文校验 | 仓内 `schemas/asset_manifest.v1.schema.json` 把 `package_id` 写死为 `wp-448-01`，不可直接复用，故派生包级 schema（见 ⑤ 局限） |
| 8 | 独立复验：`verify` 子命令**重新拉一次线上 markdown**，重算哈希、逐条重解 locator、核对 counts/integrity/claims | `docs/kf/wp-5760-01/verification.json`，all_pass=true |
| 9 | 离线复现：`build_offline()` 只吃快照重建 manifest，与已交付 manifest 逐资产比对 | `tests/test_kf_wp5760.py::test_manifest_is_reproducible_from_snapshot`（不联网也能证"清单不是手改的"） |

关键设置：只读平台接口；不写任何其它 report_id 的对象；`artifacts/` 被 `mission-push` 门过滤，故产物一律落 `docs/kf/wp-5760-01/`；`figures` 里的 png 不复制、不重编码，只登记元数据。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-5760-01/asset_manifest.json` | 主产物：52 个资产 + 源身份 + counts + integrity；sha256 `c68aae2630dc40475db080dc49966c035308999722eb2a4f2613bc3dc9b9efb8`，57776 bytes |
| `docs/kf/wp-5760-01/asset_manifest.schema.json` | 包级 draft-07 schema（`schema_pass` 的可复算靶子；仓内无 `kf_result.v1.schema.json`，说明见 ⑤） |
| `docs/kf/wp-5760-01/kf_result.json` | 交付信封（package_id/task_type/report_id/provenance/outputs），下附 JSON 块源文件 |
| `docs/kf/wp-5760-01/verification.json` | 本包自己的 10 项机器检查与说明（**不是**平台 verification 标记） |
| `docs/kf/wp-5760-01/figures/asset_inventory.png` | 资产清单图（按类别×解析状态堆叠 + 解析状态合计），数据直接读 manifest |
| `docs/kf/wp-5760-01/published_report.json` | 本报告发表回执（平台 id / status） |
| `runs/wp-5760-01/report_5760.md` | 源 markdown 原字节快照（sha256 与契约一致，离线测试的锚点） |
| `runs/wp-5760-01/report_5760_meta.json` | 平台侧非 markdown 字段（title/scenario_key/tags/figures/…），原始未改写 |
| `scripts/kf/build_asset_manifest_5760.py` | 构建 + 独立验证 + 信封派生（`build` / `verify` / `result` / `all`），含三次误捕返工的判定规则 |
| `scripts/kf/fig_wp5760_inventory.py` | 清单图生成器（零手抄：全部读 manifest） |
| `scripts/kf/report_wp5760.py` | 本报告合成器（模板 + 程序化注入 + 唯一 json 块自检 + 发表） |
| `tests/test_kf_wp5760.py` | 17 项离线验收测试：快照哈希、schema、逐个 locator 重解、counts/integrity 自洽、claims 纪律、表数覆盖、可复现性、信封绑定 |

资产类别分布（`asset_manifest.json:counts.by_class`）：

| asset_class | 个数 |
|---|---|
| artifact_directory_reference | 5 |
| bare_filename_reference | 5 |
| figure_metadata | 1 |
| figure_reference | 1 |
| file_reference | 20 |
| repro_command_block | 1 |
| section | 11 |
| source_document | 1 |
| table | 7 |

## ④ 证据定位表（字段 / 资产 → 原文引文片段）

claims 为空（本工序不做抽取），故下表按"登记字段 → 原文引文"给出可复算定位；`chars/lines` 为 markdown 字符区间与行号，平台可对同一 markdown 重放校验。

| 资产 | 类别 | 字段/说明 | 原文引文（逐字切片） | 定位 |
|---|---|---|---|---|
| A01 | source_document | `report 5760 markdown (source_field=mark…` | # IN20-R5 · 停摆自检自愈（stall detector，daemon 级机制替身） | chars 0–6808 / lines 1–186 |
| A02 | section | `section heading ## ① 案例介绍（问题 / 数据 / 参数）` | ## ① 案例介绍（问题 / 数据 / 参数） | chars 308–331 / lines 9–9 |
| A13 | table | `markdown table: 项 \| 值` | \| 项 \| 值 \|\n\|---\|---\|\n\| 回归样例 \| 2026-11-07T00:35:00+00:00 → 2026… | chars 536–941 / lines 17–26 |
| A19 | table | `markdown table: 关键量 \| 基准 \| 本实现 \| 误差` | \| 关键量 \| 基准 \| 本实现 \| 误差 \| 是否 <3% \|\n\|---\|---\|---\|---\|---\|\n\|… | chars 5269–5639 / lines 154–160 |
| A20 | figure_reference | `inline image reference: fig_stall_timel…` | ![stop timeline](fig_stall_timeline.png) | chars 4097–4137 / lines 121–121 |
| A21 | figure_metadata | `platform figures[0] metadata: fig_stall…` | fig_stall_timeline.png | figures[0] |
| A23 | file_reference | `artifacts/in20_r5/criteria.json` | artifacts/in20_r5/criteria.json | chars 129–160 / lines 4–4 |
| A24 | file_reference | `deploy/taskplane/tp-stall-detector.serv…` | deploy/taskplane/tp-stall-detector.service | chars 245–287 / lines 6–6 |
| A35 | file_reference | `ops/taskplane/stall_detector.py` | ops/taskplane/stall_detector.py | chars 5746–5777 / lines 168–168 |
| A40 | artifact_directory_reference | `artifacts/in20_r5/{replay,live}/` | artifacts/in20_r5/{replay,live}/ | chars 6096–6128 / lines 173–173 |
| A52 | repro_command_block | `fenced bash block: reproduction command…` | python3 ops/taskplane/stall_detector.py --fixture tests/fixtures/stall_… | chars 6253–6803 / lines 178–184 |

源身份证据：`sha256(markdown utf-8 bytes) = 95a6ffec44f492fe4f7f39f8d6bb989d845f6a781cd5749197177b6c05308bfe`（契约同值）；`chars=6808`、`bytes_utf8=10847`；
该哈希在构建时、`verify` 时（重新拉线上 markdown）、离线测试时（快照）三处独立重算，均相等。

## ⑤ 注意点与局限

1. **图只有元数据**：平台 `figures` 数组存 `name`+`caption`，无 `png_base64`；`fig_stall_timeline.png` 在本工作树也不存在，故图为 `declared_absent`（零字节可声明）。**不补图、不重画**——本工序不碰上游产物。
2. **路径引用全部 `referenced_unresolved`**：报告正文提到的 `ops/taskplane/stall_detector.py`、`artifacts/in20_r5/**`、`deploy/taskplane/tp-stall-detector.service` 等属于产出仓 TensorPlatform，超出本工作包边界；`local_resolution` 记录"在本工作树内查过、查不到"，属于**如实未解析**而非漏登记。
3. **平台侧无附件接口**：`/tensor/reports/5760/artifacts`、`/attachments`、`/tensor/artifacts?report_id=5760` 三个探测均 HTTP 404（结果留在 `artifact_endpoint_probe`），所以"可解析附件"只能以 markdown 内引用为准，无法交叉核对平台附件表。
4. **出现级身份**：同一路径被引用多次即多次登记（各自带自己的字符区间）。`quote_uniqueness.checked=52`、`unique=30`，非唯一的是 A21, A23, A24, A27, A28, A29, A31, A32, A33, A35, A36, A37, A38, A39, A41, A42, A43, A45, A46, A47, A48, A50——它们**不是**重复登记错误，而是同一 token 在文中出现多次；去重视图见 `counts.distinct_referenced_paths=19`。
5. **三次误捕返工（诚实记录）**：初版把散文斜杠（`systemd/容器`、`60 s/样本`）当目录、把 `{replay,live}` 通配拆成两个残片、把状态词表（`pending/queued/ready/todo/not_started`、`since/fired/cooldown`）当路径。修正规则后重算，资产数 52→54→50→52 收敛；最终规则是"文件=有扩展名且含 `/`；目录=已知产物前缀或带 `{}` 通配；裸名=无目录的纯文件名"，散文斜杠与词表按设计被排除。
6. **未登记的东西**：报告里出现的 SQL 表名/字段名（campaign DAG 节点表、`saturation_pulse`、`factory_resident_workers`）与阈值不是字节可寻址附件，**故意不登记**为资产；`state.rolled_back.<epoch>.json` 是占位模板不是真实路径，也排除。
7. **schema 缺口**：契约引用的 `schemas/kf_result.v1.schema.json` 在仓内不存在，`schemas/asset_manifest.v1.schema.json` 又把 `package_id` 写死为 `wp-448-01`。本包派生了 `asset_manifest.schema.json`（通用化 const + 增 `report_field` locator 方法）作为 `schema_pass` 的靶子；**若平台侧 schema 不同，以平台门为准，本产物须返修**。
8. **未执行上游复现命令**：报告附录的 bash 块按文本登记（`repro_command_block`），**没有运行**——它会读写 TensorPlatform 的 `artifacts/in20_r5/**`，越过本工作包边界。
9. **既有失败非本单引入**：`tests/test_kf_wp448.py` 在本工作树缺 `runs/wp-448-01/*` 与 `artifacts/wp-448-01/*` 而报错（既有状态，与本单改动无交集）；本单只新增文件。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 判定 | 依据 |
|---|---|---|
| valid_json | ✓ | json.loads OK |
| schema_pass | ✓ | jsonschema draft-07 validation against docs/kf/wp-5760-01/asset_manifest.schema.json |
| source_locator_resolvable | ✓ | checked 52 locators live; missing/unresolvable=[] span_mismatch=[] |
| source_hash_matches | ✓ | live=95a6ffec44f492fe4f7f39f8d6bb989d845f6a781cd5749197177b6c05308bfe declared=95a6ffec44f492fe… |
| no_duplicate_ids | ✓ | 52 ids, 52 distinct |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓ | claims=0 (empty array allowed by contract); problems=[] |
| counts_consistent *(加固项)* | ✓ | {"resolved_in_source": 20, "referenced_unresolved": 31, "declared_absent": 1} |
| integrity_selfconsistent *(加固项)* | ✓ | char_span_exact=50 |
| scope_single_report *(加固项)* | ✓ | every asset locator points into report 5760 markdown / its platform metadata |

补充自检：

- 唯一 JSON 围栏块：报告合成器硬断言"json 围栏块计数 == 1"（不满足即拒绝出稿），块内容 = `kf_result.json` 逐字节。
- 标题 / tags：标题 `KF-RESULT wp-5760-01`；tags 含 `kf-wp:wp-5760-01`。
- 未标 verified：manifest 中无 `"status": "verified"` / `verification_passed`，测试 `test_claims_are_empty_and_never_marked_verified` 断言。
- 测试：`17 passed, 1 warning in 0.25s`。
- 无手抄：本报告正文数字全部由 `scripts/kf/report_wp5760.py` 从机读产物注入；未替换的模板 token 会令合成失败。

### 误差判定（关键量 vs 基准，逐项回答是否 <3%）

| 关键量 | 基准 | 本实现 | 误差 | 是否 <3% |
|---|---|---|---|---|
| markdown 字节哈希 | 契约 `sha256:95a6ffec44f492fe4f7f39f8d6bb989d845f6a781cd5749197177b6c05308bfe` | 构建/verify/快照三处独立重算同值 | 0（逐字节相等） | 是（0%） |
| markdown 字符数 | 契约 `chars=6808` | `len(markdown)=6808` | 0 | 是（0%） |
| markdown 字节数 | 本实现 `bytes_utf8=10847`（契约未给，故不比契约） | 10847 | 0（同源实测） | 是（0%，但基准=自身同源，**不构成独立校验**） |
| locator 可解析率 | 52/52 | `source_locator_resolvable` 重解 52 条，0 不符 | 0 | 是（0%） |
| Markdown 表格覆盖率 | 文中可识别表格 7 | 登记表格 7 | 0 | 是（0%） |
| claim 数 | 契约允许 0 | 0（未抽取） | 0 | 是（0%） |
| 资产总数 vs 人工通读清单 | 无法机械化基准 | 52 | **无基准** | **不能声称 <3%**（见下） |

唯一**无基准**的量：资产总数（"该报告到底有多少个可定位资产"没有机器金标准，只有人工通读判断）。本单按 honest-WITHHELD 处理：给出类别分解与每条引文定位供复核，**不做百分比误差承诺，也不写 verified**。

## 附：复现命令（repro_cmd）

工作树根 = 本仓库检出；全部命令幂等、只读平台、只写本工作包目录：

```bash
# 0) 依赖：python3 + jsonschema + matplotlib（离线测试只需前两者）
python3 -c "import jsonschema, matplotlib"

# 1) 一键全链：取源 → 哈希校验 → 清点 → 独立验证 → 派生 kf_result
TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=... \
TENSOR_API_BASE=http://127.0.0.1:8010/api/v1 \
python3 scripts/kf/build_asset_manifest_5760.py all

# 2) 只复验（重拉线上 markdown，逐条重解 locator / 重算哈希）
python3 scripts/kf/build_asset_manifest_5760.py verify

# 3) 离线验收测试（不联网，用 runs/wp-5760-01/report_5760.md 快照）
python3 -m pytest tests/test_kf_wp5760.py -q

# 4) 清单图 + 报告合成（重复合成应得到逐字节相同的 md）
python3 scripts/kf/fig_wp5760_inventory.py
python3 scripts/kf/report_wp5760.py
```

## KF-RESULT JSON（本报告唯一 JSON 围栏块，info string = json）

```json
{
  "package_id": "wp-5760-01",
  "task_type": "01-asset-registration",
  "report_id": "5760",
  "provenance": {
    "source_uri": "tensor://reports/5760",
    "source_field": "markdown",
    "source_hash": "sha256:95a6ffec44f492fe4f7f39f8d6bb989d845f6a781cd5749197177b6c05308bfe",
    "hash_algo": "sha256",
    "hashed_bytes": "markdown encoded as utf-8",
    "source_chars": 6808,
    "source_bytes_utf8": 10847,
    "fetched_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/5760",
    "generator": "scripts/kf/build_asset_manifest_5760.py",
    "contract_version": "1.0"
  },
  "outputs": {
    "asset_manifest.json": {
      "path": "docs/kf/wp-5760-01/asset_manifest.json",
      "sha256": "c68aae2630dc40475db080dc49966c035308999722eb2a4f2613bc3dc9b9efb8",
      "bytes": 57776,
      "asset_count": 52,
      "claims": 0
    }
  }
}
```