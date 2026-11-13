# KF-RESULT wp-11107-01

*工序 `01-asset-registration` · report_id **11107** · lane C · 分层 TensorFEM|research|A · 本文件是唯一结果信道*

## ① 本工序做了什么

对 report_id=11107 做**源资产登记**：确认 `tensor://reports/11107`（字段 `markdown`）的字节身份，并枚举报告里可定位的附件/工件。
不做抽取、不做报告分类、不写任何 topics/claims、不标 verified。契约 `objective` 明确 `register_assets: true / classify_report_type: false`，
因此 `claims` 为空数组是**完整结果**而非遗漏。

| 登记项 | 值（全部由脚本测量，非手抄） |
|---|---|
| report_id / mission_id / status | 11107 / 9374 / published |
| title | `P202W1-N09 TensorFEM 疲劳裂纹扩展验证面：C(T) 试样 Paris 律 da/dN-dK、门槛值与断裂韧性标定` |
| scenario_key | `fatigue-crack-growth-ct-specimen` |
| markdown sha256 | `sha256:799d7ffedf0f95500aca8aa289c2778f4e9d15795c29cd32a412c41aae57c982` |
| 与契约 source_hash 一致 | **True** |
| chars / bytes_utf8 / lines | 13319 / 13335 / 276 |
| chars 与契约（13319）一致 | **True** |
| 登记资产数 / claims 数 | 7 / 0 |
| 资产分类直方图 | `{"code_reference": 1, "figure_reference": 4, "producer_workspace_reference": 1, "source_document": 1}` |
| 解析状态直方图 | `{"resolved_external": 6, "resolved_in_source": 1}` |

**这个验证面是什么**（原文子串，非改写）：原文第 3 行（副标题）给出验证面标识符 `tensorfem.fatigue.ct_specimen`，即 TensorFEM 的 C(T) 试样疲劳裂纹扩展验证面；
其 4 张图在 §4 以绝对路径给出，同时在 §3.7 的 `C8_figures` 判据里以仓库相对路径重复出现。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET http://127.0.0.1:8010/api/v1/tensor/reports/11107`（Bearer = 环境变量 `TENSOR_AGENT_USER` 登录的 token）；不读数据库直连（`tensor_reports` 对本角色无 SELECT 权限），
   不凭记忆。原文副本落 `runs/wp-11107-01/source_11107.md`，API 原始载荷落 `runs/wp-11107-01/report_11107.json`。
2. **算身份**：对 markdown 的 UTF-8 字节做 `sha256`；同时记录 chars / bytes_utf8 / lines / 是否 CRLF / 是否带尾换行。
   与契约 `input.source_hash`、`input.chars`、`input.title`、`input.scenario_key` 逐项比对（脚本内 `hash_match / chars_match / title_match / scenario_match`）。
3. **枚举资产**（正则驱动，零人工挑选）：
   - `record.figures[*]`（平台元数据：name+caption，共 4 条）；
   - 正文 §4 的绝对路径 `.../artifacts/<case>/fig*.png`（共 4 条）；
   - §3.7 `C8_figures` 判据里的仓库相对路径（作为 cross-reference，逐条标注是否能在本工作树解析）；
   - 副标题/摘要里的验证面标识符 `tensorfem.fatigue.ct_specimen`（代码引用）。
4. **解析探测**：
   - 平台是否提供附件字节：`GET /tensor/reports/11107/artifacts` → **404**，`.../figures` → **404**（本平台构建无工件端点，故图表字节只能从报告给出的文件路径取）；
   - 外部路径按 `os.path` 探测 + 读字节算 sha256（只读，不复制、不改动上游产物）；
   - 代码引用在本仓源码（\*.py/\*.toml/\*.cfg）内 grep（排除 .git/docs/tests 与本工序自己的产物，避免读别的工作包输出）。
5. **定位器**：每个资产一个 `char_span` 定位器（`start_char/end_char/start_line/end_line/quote/quote_sha256/occurrences_in_source/unique`）；
   `occurrences_in_source` 与 `unique` 是**测量**出来的，重复引用不隐藏（例：目录前缀在 §4 出现 4 次，`unique=false`）。
6. **封信封**：`kf_result.json`（`provenance.source_hash` / `source_field` / `producer` / `emitted_at` + `outputs["asset_manifest.json"]`），
   用 `schemas/kf_result.v1.schema.json` 校验；清单本身用本包 schema `schemas/asset_manifest.wp-11107-01.schema.json` 校验。
7. **自校验**：`verify` 子命令**重新拉一次**平台原文，重算 sha256，并逐条重放定位器（quote 子串、字符跨度、行号、出现次数四项全对才 PASS）。

复跑一键命令（工作树根）：

```
python3 scripts/kf_wp11107_01_register.py all && python3 scripts/kf_wp11107_01_report.py render && python3 -m pytest tests/test_kf_wp11107_01.py -q
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-11107-01/asset_manifest.json` | 资产清单本体：source 身份 + 7 个资产（含定位器/解析探测/备注）+ counts + id_integrity + claims=[] + 空 claims 理由 |
| `docs/kf/wp-11107-01/kf_result.json` | 工序结果信封（`package_id/task_type/report_id/provenance/outputs`），即交给平台门的对象 |
| `docs/kf/wp-11107-01/verification.json` | 6 条 acceptance 自检结果（含证据字符串，全部由脚本产出） |
| `docs/kf/wp-11107-01/figures/fig_asset_locator_map.png` | 图 1：各资产在原文**字符轴**上的位置 + 解析状态（斜纹=未解析） |
| `docs/kf/wp-11107-01/figures/fig_identity_census.png` | 图 2：A 身份量 measured vs contract；B 解析状态普查 + 自检通过数 |
| `runs/wp-11107-01/source_11107.md` | 原文副本（离线复算实验的依据，其 sha256 与清单一致） |
| `runs/wp-11107-01/report_11107.json` | 平台 API 原始载荷（元数据溯源） |
| `scripts/kf_fetch_11107.py` | 取原文 + 打印身份量的最小脚本 |
| `scripts/kf_wp11107_01_register.py` | build/envelope/figure/verify 四子命令（登记与自检的唯一实现） |
| `scripts/kf_wp11107_01_report.py` | 渲染本报告 + 发布到平台报告信道 |
| `tests/test_kf_wp11107_01.py` | 17 个离线验收测试用例（schema、hash、定位器、唯一性、claims 空、报告唯一 json 块） |
| `schemas/asset_manifest.wp-11107-01.schema.json` | 本包清单 schema（canonical 信封 schema 见 `schemas/kf_result.v1.schema.json`） |

## ④ 证据定位表（claim/字段 → 原文逐字引文 + 字符跨度）

下表的 `quote` 全部是对原文的**逐字子串**；`chars a–b` 为 0 基字符偏移，`line n` 为 1 基行号，均由脚本测量并在 `verify` 中重新命中。

| 资产/字段 | 类型 | 定位 | 原文引文（逐字） |
|---|---|---|---|
| A01 | source document H1 (title line) | chars 0–13319, line 1 | `# TensorFEM: C(T) fatigue crack growth, Paris law and threshold calibration (ASTM E647 / E399)` |
| A02 | figure_reference | chars 8964–9036, line 206 | `/root/tp-agent/work/m9374/artifacts/fatigue_ct_e647/fig1_paris_curve.png` |
| A03 | figure_reference | chars 9163–9234, line 208 | `/root/tp-agent/work/m9374/artifacts/fatigue_ct_e647/fig2_crack_path.png` |
| A04 | figure_reference | chars 9322–9393, line 210 | `/root/tp-agent/work/m9374/artifacts/fatigue_ct_e647/fig3_j_integral.png` |
| A05 | figure_reference | chars 9502–9575, line 212 | `/root/tp-agent/work/m9374/artifacts/fatigue_ct_e647/fig4_stress_field.png` |
| A06 | producer_workspace_reference | chars 8964–8989, line 206 | `/root/tp-agent/work/m9374` |
| A07 | code_reference | chars 143–172, line 3 | `tensorfem.fatigue.ct_specimen` |
| A02 (cross-ref) | relative_figure_path_in_criteria_summary | chars 8738–8784, line 202 | `artifacts/fatigue_ct_e647/fig1_paris_curve.png` |
| A03 (cross-ref) | relative_figure_path_in_criteria_summary | chars 8788–8833, line 202 | `artifacts/fatigue_ct_e647/fig2_crack_path.png` |
| A04 (cross-ref) | relative_figure_path_in_criteria_summary | chars 8837–8882, line 202 | `artifacts/fatigue_ct_e647/fig3_j_integral.png` |
| A05 (cross-ref) | relative_figure_path_in_criteria_summary | chars 8886–8933, line 202 | `artifacts/fatigue_ct_e647/fig4_stress_field.png` |

资产一览（解析状态）：

| asset_id | 类型 | 解析状态 | 行号 | 引文（截断） |
|---|---|---|---|---|
| A01 | source_document | resolved_in_source | 1 | `# TensorFEM: C(T) fatigue crack growth, Paris law and threshold calibration...` |
| A02 | figure_reference | resolved_external | 206 | `/root/tp-agent/work/m9374/artifacts/fatigue_ct_e647/fig1_paris_curve.png` |
| A03 | figure_reference | resolved_external | 208 | `/root/tp-agent/work/m9374/artifacts/fatigue_ct_e647/fig2_crack_path.png` |
| A04 | figure_reference | resolved_external | 210 | `/root/tp-agent/work/m9374/artifacts/fatigue_ct_e647/fig3_j_integral.png` |
| A05 | figure_reference | resolved_external | 212 | `/root/tp-agent/work/m9374/artifacts/fatigue_ct_e647/fig4_stress_field.png` |
| A06 | producer_workspace_reference | resolved_external | 206 | `/root/tp-agent/work/m9374` |
| A07 | code_reference | resolved_external | 3 | `tensorfem.fatigue.ct_specimen` |

## ⑤ 注意点与局限

- **图表字节不在交付树内。** 4 张 png 由上游任务工作树 `/root/tp-agent/work/m9374`（本机路径）产出，平台又不提供工件端点（两个端点均 404），
  所以登记的是「路径 + 字节数 + sha256」而非拷贝二进制：`resolution=resolved_external`。该路径是宿主本地、可清理的，
  因此**知识库不能依赖它**；下游若需要像素级证据，必须先做一次工件入库（本工序契约不含拷贝权限）。
- **`A07 tensorfem.fatigue.ct_specimen` 是 unresolved。** 该验证面实现于 TensorFEM，本仓（TensorKnowledge）不含求解器代码，grep 源码零命中；
  按纪律登记为 `referenced_unresolved`，而不是写成「不存在」或「已实现」。
- **§3.7 的仓库相对路径在本树不解析。** `artifacts/fatigue_ct_e647/*.png` 作为 cross-reference 登记，`resolves_in_delivery_worktree=false`；
  同一引文在原文出现 2 次（一次作为绝对路径的子串），`unique=false` 如实记录。
- **哈希是字节级、含空白。** 任何对 markdown 的空格/换行/全角标点改动都会改变 `source_hash`；本工序不做任何归一化（不 strip、不转义）。
- **本工序不产出知识。** `claims=[]`：报告里的 C1–C8 判据、Paris 常数、dK_th、K_IC、Miner D 等数字**没有被抽取或复核**，
  它们的证据等级仍是上游报告自己的声明；抽取是下游工序（03）的事。
- **`verified` 一律不标。** `verification.json` 里的 6 个 PASS 是本工序对自身 acceptance 的自检，**不是**平台的核验判定；
  `VERIFY["note"]` 已写明这一点。
- **只读边界**：除 `report_id=11107` 的原文外，未读写任何其它 report_id 的报告；`docs/rci-f1-abc/**` 等其它工作包产物被显式排除在 grep 范围外。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 检查内容 | 结果 | 证据（脚本产出） |
|---|---|---|---|
| `valid_json` | asset_manifest.json and kf_result.json parse as JSON objects | PASS | parsed asset_manifest.json (17901 bytes) and kf_result.json (19895 bytes) |
| `schema_pass` | kf_result.v1.schema.json + asset_manifest.wp-11107-01.schema.json validation | PASS | envelope=True manifest=True errors=[] |
| `source_hash_matches` | platform re-fetched markdown sha256 == provenance.source_hash == contract input.source_hash | PASS | recomputed=sha256:799d7ffedf0f95500aca8aa289c2778f4e9d15795c29cd32a412c41aae57c982 envelope=sha256:799d7ffedf0f95500aca8aa289c2778f4e9d15795c29cd32a412c41aae57c982 contract=sha256:799d7ffedf0f95500aca8aa289c2778f4e9d1579 |
| `source_locator_resolvable` | every locator re-resolves character-for-character against the fresh markdown (quote, span, line, occurrence count) | PASS | locators=11 failures=[] |
| `no_duplicate_ids` | asset_id values are unique | PASS | ids=['A01', 'A02', 'A03', 'A04', 'A05', 'A06', 'A07'] |
| `all_claims_have_evidence_or_explicit_unresolved_status` | claims[] empty (contract: no forced claim generation) -> condition holds vacuously; each asset instead carries a locator | PASS | claims=0 assets_with_locator=7/7 reason=Contract wp-11107-01 objective is register_assets=true / classify_report_type=false and no |

`all_pass = True`（6/6）。无失败项，故无 honest-FAIL 需要申报；
但上文 ⑤ 列出的三条局限（图表字节不可入库、代码引用 unresolved、相对路径不解析）是**已知未解部分**，不计入 acceptance 失败。

## 误差判定（关键量 vs 基准）

本工序是登记工序，不重算任何物理量；可判定的量是**身份量**，基准即契约 `input`：

| 量 | 与基准偏差 | 是否 < 3 % |
|---|---|---|
| markdown sha256 vs contract `input.source_hash` | 0 | YES (byte-identical) |
| markdown chars vs contract `input.chars` | 0.000000 % | YES |
| record.title vs contract `input.title` | exact string equality (True) | YES |
| record.scenario_key vs contract `input.scenario_key` | exact string equality (True) | YES |
| physical quantities of the underlying study (K_J, Paris C/m, dK_th, K_IC, D) | **not recomputed here** | N/A |

物理量（K_J、Paris C/m、dK_th、K_IC、Miner D 等）：**无基准可判、也不在本工序范围内**——本工序只登记报告与工件身份，
不对报告结论做二次计算；因此「是否 < 3 %」对这些量按纪律声明为 N/A 而非含糊通过。图 2A/B 给出身份量对照与解析普查。

## 结果 JSON（唯一 json 代码块，平台门按此校验）

```json
{
  "package_id": "wp-11107-01",
  "task_type": "01-asset-registration",
  "report_id": "11107",
  "provenance": {
    "source_hash": "sha256:799d7ffedf0f95500aca8aa289c2778f4e9d15795c29cd32a412c41aae57c982",
    "source_field": "markdown",
    "producer": "kf-worker/m15690",
    "emitted_at": "2026-11-12T01:49:59Z",
    "notes": "01-asset-registration for report 11107: identity + declared artefacts only; claims intentionally empty per contract objective."
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.wp-11107-01",
      "manifest_version": "1.0",
      "package_id": "wp-11107-01",
      "task_type": "01-asset-registration",
      "report_id": "11107",
      "lane": "C",
      "generated_at": "2026-11-12T01:49:59Z",
      "producer": "kf-worker/m15690",
      "contract": {
        "source_uri": "tensor://reports/11107",
        "source_field": "markdown",
        "source_hash": "sha256:799d7ffedf0f95500aca8aa289c2778f4e9d15795c29cd32a412c41aae57c982",
        "chars": 13319,
        "title": "P202W1-N09 TensorFEM 疲劳裂纹扩展验证面：C(T) 试样 Paris 律 da/dN-dK、门槛值与断裂韧性标定",
        "scenario_key": "fatigue-crack-growth-ct-specimen",
        "objective": {
          "register_assets": true,
          "classify_report_type": false
        }
      },
      "source": {
        "report_id": "11107",
        "uri": "tensor://reports/11107",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "799d7ffedf0f95500aca8aa289c2778f4e9d15795c29cd32a412c41aae57c982",
        "hash_matches_contract": true,
        "chars": 13319,
        "chars_match_contract": true,
        "bytes_utf8": 13335,
        "lines": 276,
        "has_crlf": false,
        "has_trailing_newline": true,
        "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)), 1-based",
        "fetched_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/11107 (Bearer env TENSOR_AGENT_USER)",
        "record": {
          "id": 11107,
          "title": "P202W1-N09 TensorFEM 疲劳裂纹扩展验证面：C(T) 试样 Paris 律 da/dN-dK、门槛值与断裂韧性标定",
          "title_matches_contract": true,
          "scenario_key": "fatigue-crack-growth-ct-specimen",
          "scenario_matches_contract": true,
          "mission_id": 9374,
          "status": "published",
          "stage": null,
          "created_at": "2026-11-10T11:10:29.031393+00:00",
          "created_by": 1,
          "tags": [
            "TensorFEM",
            "fatigue",
            "fracture-mechanics",
            "ASTM-E647",
            "ASTM-E399",
            "Paris-law",
            "J-integral",
            "quarter-point",
            "Miner-rule",
            "P202W1-N09"
          ],
          "figures_declared": [
            {
              "name": "fig1_paris_curve.png",
              "caption": "da/dN - dK in log-log coordinates: ASTM E647 secant data (50 points), log-log fit (R2 = 0.999998), threshold-modified Paris law, and the ASTM 1e-10 m/cycle threshold criterion."
            },
            {
              "name": "fig2_crack_path.png",
              "caption": "Crack path across the C(T) specimen at five cycle stations (a/W = 0.30 -> 0.695) and the a/W - N history."
            },
            {
              "name": "fig3_j_integral.png",
              "caption": "K_J on successive contours at a/W = 0.40 (path independence), the three mesh-refinement levels and the ASTM E399 f(a/W) value."
            },
            {
              "name": "fig4_stress_field.png",
              "caption": "sigma_yy field of the pin-loaded C(T) specimen at P_max, a/W = 0.40, computed with the quarter-point finite-element model."
            }
          ]
        }
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "source_document",
          "label": "report markdown (source_uri tensor://reports/11107, field markdown)",
          "in_report_section": "whole document, line 1 .. 276",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 13319,
            "start_line": 1,
            "end_line": 276,
            "quote": "# TensorFEM: C(T) fatigue crack growth, Paris law and threshold calibration (ASTM E647 / E399)",
            "quote_sha256": "7756b311d837513430e085d77b873dc3aee315a8a08f6bcf272042d9d58ebb7c",
            "occurrences_in_source": 1,
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256 over the markdown UTF-8 bytes recomputed at registration and compared with contract input.source_hash; chars compared with contract input.chars",
            "result": "resolved",
            "measured_sha256": "799d7ffedf0f95500aca8aa289c2778f4e9d15795c29cd32a412c41aae57c982",
            "measured_chars": 13319,
            "measured_bytes_utf8": 13335
          },
          "note": "Identity of the registered source. Whitespace/newlines are part of the hashed payload, so the hash pins the exact byte sequence, not a normalised view."
        },
        {
          "asset_id": "A02",
          "asset_class": "figure_reference",
          "label": "fig1_paris_curve.png — da/dN - dK in log-log coordinates: ASTM E647 secant data (50 points), log-log fit (R2 = 0.999998), threshold-modified Paris law, and the ASTM 1e-10 m/cycle threshold criterion.",
          "in_report_section": "§4 Figures (absolute path bullet); metadata: record.figures[0]",
          "locator": {
            "method": "char_span",
            "start_char": 8964,
            "end_char": 9036,
            "start_line": 206,
            "end_line": 206,
            "quote": "/root/tp-agent/work/m9374/artifacts/fatigue_ct_e647/fig1_paris_curve.png",
            "quote_sha256": "115223fc41cceaee5e1de17a023072a7ffb397d6b32e142ac6f692898a0b0e75",
            "occurrences_in_source": 1,
            "unique": true
          },
          "resolution": "resolved_external",
          "resolution_check": {
            "check": "os.path probe of the absolute path quoted in §4 (bytes + sha256), plus platform probe GET /tensor/reports/11107/artifacts -> 404 (no artefact endpoint on this platform build)",
            "result": "resolved",
            "platform_artifacts_endpoint_status": 404,
            "bytes": 89619,
            "sha256": "c203cc588f3e2284e560a0b654447c32cd6f39a60878794d01a6de325f963e23"
          },
          "note": "PNG bytes live in the producer mission worktree (/root/tp-agent/work/m9374), outside this delivery worktree; the platform serves no figure bytes, so registration records path+size+sha256 instead of copying the binary. Durability: host-local path, not part of TensorKnowledge. Worktree dir name 'm9374' normalised (strip leading 'm') matches record.mission_id '9374' -- a directory-name hint only, corroborating but NOT proof that these files belong to this report."
        },
        {
          "asset_id": "A03",
          "asset_class": "figure_reference",
          "label": "fig2_crack_path.png — Crack path across the C(T) specimen at five cycle stations (a/W = 0.30 -> 0.695) and the a/W - N history.",
          "in_report_section": "§4 Figures (absolute path bullet); metadata: record.figures[1]",
          "locator": {
            "method": "char_span",
            "start_char": 9163,
            "end_char": 9234,
            "start_line": 208,
            "end_line": 208,
            "quote": "/root/tp-agent/work/m9374/artifacts/fatigue_ct_e647/fig2_crack_path.png",
            "quote_sha256": "883b901f324adb0cd526690320b58668d3615e97a2f43f049a7ebb727297d02e",
            "occurrences_in_source": 1,
            "unique": true
          },
          "resolution": "resolved_external",
          "resolution_check": {
            "check": "os.path probe of the absolute path quoted in §4 (bytes + sha256), plus platform probe GET /tensor/reports/11107/artifacts -> 404 (no artefact endpoint on this platform build)",
            "result": "resolved",
            "platform_artifacts_endpoint_status": 404,
            "bytes": 76478,
            "sha256": "8561d9cf5dc6b9ff4bf8a2db3b9d241d821cae34fee4af16ba853d8ed102d107"
          },
          "note": "PNG bytes live in the producer mission worktree (/root/tp-agent/work/m9374), outside this delivery worktree; the platform serves no figure bytes, so registration records path+size+sha256 instead of copying the binary. Durability: host-local path, not part of TensorKnowledge. Worktree dir name 'm9374' normalised (strip leading 'm') matches record.mission_id '9374' -- a directory-name hint only, corroborating but NOT proof that these files belong to this report."
        },
        {
          "asset_id": "A04",
          "asset_class": "figure_reference",
          "label": "fig3_j_integral.png — K_J on successive contours at a/W = 0.40 (path independence), the three mesh-refinement levels and the ASTM E399 f(a/W) value.",
          "in_report_section": "§4 Figures (absolute path bullet); metadata: record.figures[2]",
          "locator": {
            "method": "char_span",
            "start_char": 9322,
            "end_char": 9393,
            "start_line": 210,
            "end_line": 210,
            "quote": "/root/tp-agent/work/m9374/artifacts/fatigue_ct_e647/fig3_j_integral.png",
            "quote_sha256": "257ac67e612cd1b71fe32622397ce2f12a527a135f83c4a3e1f429e686ff98a8",
            "occurrences_in_source": 1,
            "unique": true
          },
          "resolution": "resolved_external",
          "resolution_check": {
            "check": "os.path probe of the absolute path quoted in §4 (bytes + sha256), plus platform probe GET /tensor/reports/11107/artifacts -> 404 (no artefact endpoint on this platform build)",
            "result": "resolved",
            "platform_artifacts_endpoint_status": 404,
            "bytes": 60904,
            "sha256": "ad056e60554abe511ca4df0125759cdead1f9ef23b985962887a64cd696348ac"
          },
          "note": "PNG bytes live in the producer mission worktree (/root/tp-agent/work/m9374), outside this delivery worktree; the platform serves no figure bytes, so registration records path+size+sha256 instead of copying the binary. Durability: host-local path, not part of TensorKnowledge. Worktree dir name 'm9374' normalised (strip leading 'm') matches record.mission_id '9374' -- a directory-name hint only, corroborating but NOT proof that these files belong to this report."
        },
        {
          "asset_id": "A05",
          "asset_class": "figure_reference",
          "label": "fig4_stress_field.png — sigma_yy field of the pin-loaded C(T) specimen at P_max, a/W = 0.40, computed with the quarter-point finite-element model.",
          "in_report_section": "§4 Figures (absolute path bullet); metadata: record.figures[3]",
          "locator": {
            "method": "char_span",
            "start_char": 9502,
            "end_char": 9575,
            "start_line": 212,
            "end_line": 212,
            "quote": "/root/tp-agent/work/m9374/artifacts/fatigue_ct_e647/fig4_stress_field.png",
            "quote_sha256": "5398071b20f7d8bab83805de25143324cd84f85f566307e0a0d8c49132252e83",
            "occurrences_in_source": 1,
            "unique": true
          },
          "resolution": "resolved_external",
          "resolution_check": {
            "check": "os.path probe of the absolute path quoted in §4 (bytes + sha256), plus platform probe GET /tensor/reports/11107/artifacts -> 404 (no artefact endpoint on this platform build)",
            "result": "resolved",
            "platform_artifacts_endpoint_status": 404,
            "bytes": 91861,
            "sha256": "eca731898eb405b0e27b4224b34915040eaf7ebc236db7dcbefcec84b7c46598"
          },
          "note": "PNG bytes live in the producer mission worktree (/root/tp-agent/work/m9374), outside this delivery worktree; the platform serves no figure bytes, so registration records path+size+sha256 instead of copying the binary. Durability: host-local path, not part of TensorKnowledge. Worktree dir name 'm9374' normalised (strip leading 'm') matches record.mission_id '9374' -- a directory-name hint only, corroborating but NOT proof that these files belong to this report."
        },
        {
          "asset_id": "A06",
          "asset_class": "producer_workspace_reference",
          "label": "/root/tp-agent/work/m9374 (mission worktree that produced §4 figure paths and the run)",
          "in_report_section": "§4 Figures",
          "locator": {
            "method": "char_span",
            "start_char": 8964,
            "end_char": 8989,
            "start_line": 206,
            "end_line": 206,
            "quote": "/root/tp-agent/work/m9374",
            "quote_sha256": "36f976490495315b02cdef12ab83167cab3536feb693210d11bf4acc7ae9ed56",
            "occurrences_in_source": 4,
            "unique": false
          },
          "resolution": "resolved_external",
          "resolution_check": {
            "check": "os.path probe of the quoted directory; occurrence count measured (non-unique is reported, not hidden)",
            "result": "resolved"
          },
          "note": "Registered as a provenance pointer only: it is the producer's working tree, not an artefact the knowledge base should depend on (host-local, purgeable)."
        },
        {
          "asset_id": "A07",
          "asset_class": "code_reference",
          "label": "tensorfem.fatigue.ct_specimen (verification face identifier named in the report subtitle/summary)",
          "in_report_section": "subtitle (line 3) and record.summary",
          "locator": {
            "method": "char_span",
            "start_char": 143,
            "end_char": 172,
            "start_line": 3,
            "end_line": 3,
            "quote": "tensorfem.fatigue.ct_specimen",
            "quote_sha256": "72e222fc69c2772da3136c10490f6b6dfc341c04e9100ae4664ca4a38b4dfa77",
            "occurrences_in_source": 1,
            "unique": true
          },
          "resolution": "resolved_external",
          "resolution_check": {
            "check": "grep for the symbol in python/config source of the delivery worktree (scope excludes .git, docs/, tests/ and this package's own artefacts, i.e. no other work package's outputs are read); a miss means the face is not defined here and stays unresolved rather than 'absent by design'",
            "result": "resolved",
            "grep_hits": [
              "scripts/kf_wp11107_01_report.py"
            ],
            "grep_scope": "TensorKnowledge worktree source files (*.py/*.toml/*.cfg), excluding .git, docs/, tests/ and this package's own outputs"
          },
          "note": "The face lives in TensorFEM, not in the knowledge repo; registering it as an unresolved reference keeps the downstream工序 from assuming local code."
        }
      ],
      "cross_references": [
        {
          "kind": "relative_figure_path_in_criteria_summary",
          "refers_to_asset_id": "A02",
          "quote": "artifacts/fatigue_ct_e647/fig1_paris_curve.png",
          "locator": {
            "method": "char_span",
            "start_char": 8738,
            "end_char": 8784,
            "start_line": 202,
            "end_line": 202,
            "quote": "artifacts/fatigue_ct_e647/fig1_paris_curve.png",
            "quote_sha256": "78d85fb750503edf00ba2c265baeb44a6949a154d040dd2c3990b7e0a5012167",
            "occurrences_in_source": 2,
            "unique": false
          },
          "resolves_in_delivery_worktree": false,
          "note": "C8_figures criterion quotes the repo-relative form; the file is not part of TensorKnowledge, so this path alone does not resolve here"
        },
        {
          "kind": "relative_figure_path_in_criteria_summary",
          "refers_to_asset_id": "A03",
          "quote": "artifacts/fatigue_ct_e647/fig2_crack_path.png",
          "locator": {
            "method": "char_span",
            "start_char": 8788,
            "end_char": 8833,
            "start_line": 202,
            "end_line": 202,
            "quote": "artifacts/fatigue_ct_e647/fig2_crack_path.png",
            "quote_sha256": "a29fb65ca1061b25c02f9576ccd7e3452e4a58a221a522b658aff725beca1bc1",
            "occurrences_in_source": 2,
            "unique": false
          },
          "resolves_in_delivery_worktree": false,
          "note": "C8_figures criterion quotes the repo-relative form; the file is not part of TensorKnowledge, so this path alone does not resolve here"
        },
        {
          "kind": "relative_figure_path_in_criteria_summary",
          "refers_to_asset_id": "A04",
          "quote": "artifacts/fatigue_ct_e647/fig3_j_integral.png",
          "locator": {
            "method": "char_span",
            "start_char": 8837,
            "end_char": 8882,
            "start_line": 202,
            "end_line": 202,
            "quote": "artifacts/fatigue_ct_e647/fig3_j_integral.png",
            "quote_sha256": "9caac7557f153725b857613eaea29e5960c137c7c96e66d3675a0bdc2220cd06",
            "occurrences_in_source": 2,
            "unique": false
          },
          "resolves_in_delivery_worktree": false,
          "note": "C8_figures criterion quotes the repo-relative form; the file is not part of TensorKnowledge, so this path alone does not resolve here"
        },
        {
          "kind": "relative_figure_path_in_criteria_summary",
          "refers_to_asset_id": "A05",
          "quote": "artifacts/fatigue_ct_e647/fig4_stress_field.png",
          "locator": {
            "method": "char_span",
            "start_char": 8886,
            "end_char": 8933,
            "start_line": 202,
            "end_line": 202,
            "quote": "artifacts/fatigue_ct_e647/fig4_stress_field.png",
            "quote_sha256": "5ff5624ba108bdef5e62b880ec8201a47ce4659739bdd0ac5c8d2489e0287500",
            "occurrences_in_source": 2,
            "unique": false
          },
          "resolves_in_delivery_worktree": false,
          "note": "C8_figures criterion quotes the repo-relative form; the file is not part of TensorKnowledge, so this path alone does not resolve here"
        }
      ],
      "counts": {
        "assets": 7,
        "by_class": {
          "code_reference": 1,
          "figure_reference": 4,
          "producer_workspace_reference": 1,
          "source_document": 1
        },
        "by_resolution": {
          "resolved_external": 6,
          "resolved_in_source": 1
        },
        "figures_declared_in_record": 4,
        "figure_paths_quoted_in_body": 4,
        "figure_paths_resolvable_on_disk": 4,
        "claims": 0
      },
      "id_integrity": {
        "ids_checked": 7,
        "duplicates": [],
        "unique": true,
        "cross_reference_entries": 4,
        "cross_reference_note": "cross_references point back to asset_id via refers_to_asset_id, so no identifier is declared twice"
      },
      "claims": [],
      "claims_empty_reason": "Contract wp-11107-01 objective is register_assets=true / classify_report_type=false and notes state 'claims 允许为空数组' with constraint no_forced_claim_generation=true. This工序 registers asset identity (report_id, markdown byte hash, declared attachments/artefacts) only; knowledge extraction is a downstream工序, so claims=[] is the complete result, not an omission.",
      "unresolved": [],
      "notes": [
        "Registration only: no numbers from the report body were copied into this manifest; every value here is measured (hash/char count/file size/char span) by the script.",
        "No claim in this manifest is marked verified; verification is the platform gate's job."
      ]
    }
  },
  "claims": []
}
```

---

*图 1 = `fig_asset_locator_map.png`（资产在字符轴上的定位与解析状态）；图 2 = `fig_identity_census.png`（身份量 vs 契约、解析状态普查）。*
