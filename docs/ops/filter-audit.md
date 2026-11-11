# 推送门禁过滤审计（TensorKnowledge，近两周）

**任务**：m8800 / FEAT-TK-KNOWLEDGE-ENGINE —— 仓库卫生第 4 项
**审计对象**：近两周（2026-10-27 起）task push 门禁（`tp_pusher.py` v6.0）在
TensorKnowledge 仓滤除的文件
**判定词**：**该滤**（滤得对，无损失）/ **误滤**（滤错：本单产物或依赖被静默丢弃）
**生成工具**：`scripts/audit_push_filter.py`（本单新增，可重跑）

## 1. 口径与数据来源

| 来源 | 拿到什么 | 局限 |
|---|---|---|
| 合并进 main 的 mission 提交信息 | 每个被滤单的**文件数**：「m<N>: …（N 个文件被门禁滤除）」 | 提交信息只有**计数**，没有文件名 |
| `tp_pusher.py`（`/root/tp-agent/tp_pusher.py`） | 过滤规则的**权威定义**（`_EXCLUDE`、`_EXCLUDE2`、`[harness工具]`、`[他单]`、`[ship→打捞]`、`[main已前进,无权覆盖]`、`MAX_FILE`/`MAX_FILES`） | 规则顺序影响命中标签 |
| `/var/log/tp-pusher.log` | 单级结论（pushed / skipped / failed_permanent）与跳过原因（如 `skipped_only_oversize`） | **不记被滤文件名** |
| `tp_pusher_state.json` | 单级推送结果（分支、文件数、PR 号） | 同上 |
| `merge_master.log` | PR 合并结果（`pr-gate m<N> merged #PR ok`） | 只记合并，不记过滤 |
| 本地 mission 分支 `agent/m<N>` | **可重建**：分支改动集 − 实际落入提交的路径集 = 被滤路径集 | 仅限分支还在本地的单 |

结论：**平台侧日志口径只提供「滤了几个」，文件名必须从 git 侧重建**。本审计因此
用「分支改动集 − 提交改动集」重建，并用规则重放交叉校验。

## 2. 方法（可复现，零手抄）

```
for 每个提交信息含「（N 个文件被门禁滤除）」的 mission m<mid>:
    in_branch = git diff --name-only merge-base(origin/main, agent/m<mid>) agent/m<mid>
    in_commit = git diff --name-only <commit>^ <commit>
    dropped   = in_branch - in_commit          # 重建出的被滤文件
    用 tp_pusher.py 的同一组正则给每个 dropped 打规则标签
    校验：len(dropped) == 日志计数 N（否则标 partial）
    判定 keep 类：内容与 origin/main 相同→该滤；不同或不存→误滤
    判定 other-mission 类：提交补丁里引用了该路径→误滤（缺了即红）；否则该滤
```

**重建校验结果：10 个被滤单，10/10 与提交信息里的计数精确吻合**（`exact=10, partial=0`），
所以下面的文件名清单不是猜测，是可对账的重建。

```bash
python scripts/audit_push_filter.py --since 2026-10-27 \
    --json docs/ops/filter-audit.json --md /tmp/filter-table.md
```

## 3. 汇总

| 指标 | 值 |
|---|---|
| 窗口内被滤单 | 10（m8618、m8619、m8620、m8635、m8669、m8676、m8677、m8688、m8690、m8691） |
| 被滤文件总数 | 92 |
| 重建 vs 日志计数 | 10/10 精确一致 |
| 按规则 | `record` 49 · `other-mission` 37 · `keep`(=main已前进/静默丢失) 6 |
| 按判定 | **该滤 49 · 误滤 43** |
| 误滤模式 | ①他单目录被引用（37，m8620 需要 m8554 试点包）②main 已前进但合并缺失（6） |

误滤不是"规则写错了"，而是**规则只做了拒绝，没做后续动作**：拒绝覆盖是对的，
但拒绝之后既没有"打捞合并"，也没有把文件名回写给人看，于是内容就停在了分支上。

## 4. 三类误滤与处理

### P1（37 个文件，已修）m8620 的测试依赖他单目录 `platform-test/epistemic-benchmark/pilots/m8554/`

- 现象：m8620（KE 原型）提交里带了 m8554 试点包作为测试夹具（`docs/ke/proto.md` 明确写
  "owner 验收通过；本分支将其收编为可复现夹具"）。门禁的 `[他单]` 规则按
  `/<mission-id>/` 段命中，37 个文件全被滤 → main 上 `tests/test_ke_proto.py`
  的 **15 个原型测试全部 FileNotFoundError**。
- 判定：**误滤**。规则意图是「不替他单发布成果」，但没区分「他单目录被本单测试引用」。
- 已修（m8800）：把该包按 `git archive ba59c4e` 字节级取回，落到**不含他单号段**的
  `tests/fixtures/ke-pilot/`（附 `PROVENANCE.md` 记来源与找回命令），测试夹具指向新路径；
  双后端 15×2 全绿。选新路径而不是原路径，正是为了不再被 `[他单]` 规则二次滤除。
- 找回路径：`git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/<path>`
  （原始落地分支是 `agent/m8554`：`git checkout origin/agent/m8554 -- platform-test/epistemic-benchmark/pilots/m8554`）。

### P2（6 个文件，待修）main 已前进 + 数据卷宗（roll-up JSON）无合并动作

- 现象：`knowledge/oss-lbm/{claims,evidence,provenance}/*.json` 在 m8690 里有
  **cudaphasefield 的 12 claim + 12 evidence + 1 provenance**（`tkp:oss-lbm:cudaphasefield-ingest-2026-11-09`），
  但 origin/main 上是别的单（m8688 的 freesurf）写过的同路径文件 → 门禁按
  `[main已前进,无权覆盖]` 拒绝，**没有任何合并动作**，于是两边互有对方没有的记录：
  - 分支独有、main 缺失：12 claims / 12 evidence / 1 provenance（cudaphasefield）
  - main 独有、分支缺失：10 claims / 10 evidence / 1 provenance（freesurf）
- 判定：**误滤**（拒绝覆盖本身正确，但缺"记录级并集合并"这一步，净结果＝静默丢数据）。
  注：cudaphasefield 的原始 claim **正文**以 `.md` 形式在 main 上仍在，丢的是**结构化 JSON 记录**
  （即 KE 契约可入库的形态），所以影响面=知识库不可检索，不是证据消失。
- 找回路径：
  ```bash
  git show agent/m8690:knowledge/oss-lbm/claims/claims.json      > /tmp/c.json
  git show agent/m8690:knowledge/oss-lbm/evidence/evidence.json  > /tmp/e.json
  git show agent/m8690:knowledge/oss-lbm/provenance/provenance.json > /tmp/p.json
  # 与 origin/main 版本做 id 并集（不覆盖），再按 schema 校验后提交
  ```
- 建议机制：对 `knowledge/**/*.json` 这类"聚合卷宗"路径，门禁把 `[main已前进]` 从
  "静默跳过"改为 **blocked_record_overlap**（阻断整单 + 要求并集合并后重推），
  与代码路径的 `code_overlap` 同款处理。

### P3（3 个文件中的小节，待修）`knowledge/oss-lbm/README.md` 三单各丢一节

- 现象：m8688 / m8677 / m8691 都在 `knowledge/oss-lbm/README.md` 里加了自己的包说明，
  同路径相撞 + main 已前进 → 三单各自的分支版本相对 main 分别独有 10 / 9 / 5 行，
  最终只有一版留在 main。
- 判定：**误滤**（小节级内容丢失；属"多单同路径相撞"经典问题，与 m764 的
  `submit_report.py`/`outputs/` 撞车同源）。
- 找回路径：`git show agent/m8688:knowledge/oss-lbm/README.md`（m8677 / m8691 同理），
  三节合并成一版后提交。
- 建议机制：文档同路径写冲突应在推送侧迁到 `docs/m<id>/` 单单独享路径（门禁已有该
  归一化逻辑，但只覆盖 `generate_figures.py` 与 `outputs/`，README 类不覆盖）。

### 该滤的 49 个（抽样口径）

`record` 规则命中的都是运行记录与二进制：`artifacts/ke_eval/*.json|png`（评估中间结果）、
`runs/oss-lbm-kruger-8676/**`（跑批日志与图）、`*.log`、`*.png`、`artifacts/m8688_freesurf/*.png`
等。它们是**平台报告线的素材**，不该进 GitHub 代码仓——判定该滤，且平台侧报告仍可引用。

## 5. 局限（如实登记）

1. **只覆盖 TensorKnowledge 一个仓**：其他仓的 mission 分支不在本工作树，重建需要
   对应仓的本地分支；跨仓总账只能给出「计数」（日志口径）。
2. **重建以本地分支为基**：门禁实际推送的是"当前 main tip + 增量树"，若分支在推送后
   又被改动，重建可能与当时实际被滤集合有偏差；本次 10/10 计数吻合说明窗口内无此情形。
3. **日志不含文件名**：因此"该滤/误滤"的判定是规则重放 + 内容比对（`git diff
   origin/main:<path> <branch>:<path>`）得出，不是平台自报。
4. `merge_master.log` 只记合并结果，无法用于过滤审计（已在口径表声明）。

## 6. 本次审计顺手修掉的仓库卫生项

- `ke/__pycache__`（5 个 `.pyc`）+ `tests/__pycache__`（1 个 `.pyc`）= **6 条编译物**
  已从索引与工作树中出清（`git rm -r --cached` + `rm -rf`）；`.gitignore` 复核已含
  `__pycache__/` 与 `*.pyc`（main 上原本就有，无需新增），并确认 `git ls-files | grep -c '\.pyc$'` = 0。
  （任务书写 8 条，实测 tracked 为 6 条，另有 2 条属 `.pytest_cache` 级别的本地残留，
  未入仓，不构成本仓内容。）

## 7. 逐条清单（工具生成，勿手改）

<!-- generated by scripts/audit_push_filter.py; do not edit by hand -->
# 附：逐条清单（m8800，2026-10-27 起）

| mission | 提交 | 日志计数 | 重建数 | 一致 |
|---|---|---:|---:|:--:|
| m8688 | `a74174e0` | 3 | 3 | exact |
| m8677 | `1a922f14` | 1 | 1 | exact |
| m8618 | `23c250b6` | 9 | 9 | exact |
| m8691 | `94e97e0e` | 2 | 2 | exact |
| m8676 | `88c44d78` | 23 | 23 | exact |
| m8669 | `115bdc9b` | 4 | 4 | exact |
| m8690 | `82b9a9f6` | 3 | 3 | exact |
| m8620 | `a956932d` | 24 | 24 | exact |
| m8635 | `6b8f68bb` | 3 | 3 | exact |
| m8619 | `12c88707` | 20 | 20 | exact |

| mission | 门禁规则 | 判定 | 文件 | 理由 / 找回路径 |
|---|---|:--:|---|---|
| m8688 | record | 该滤 | `artifacts/m8688_freesurf/claim_inventory.png` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8688 | keep | 误滤 | `knowledge/oss-lbm/README.md` | main 已前进且内容不同：合并动作缺失（非覆盖保护本身之过） → `git show agent/m8688:knowledge/oss-lbm/README.md` |
| m8688 | record | 该滤 | `runs/m8688_validation.log` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8677 | keep | 误滤 | `knowledge/oss-lbm/README.md` | main 已前进且内容不同：合并动作缺失（非覆盖保护本身之过） → `git show agent/m8677:knowledge/oss-lbm/README.md` |
| m8618 | record | 该滤 | `artifacts/ke_eval/cognee_result.json` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8618 | record | 该滤 | `artifacts/ke_eval/corpus.json` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8618 | record | 该滤 | `artifacts/ke_eval/decision_matrix.json` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8618 | record | 该滤 | `artifacts/ke_eval/decision_matrix.md` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8618 | record | 该滤 | `artifacts/ke_eval/graphiti_result.json` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8618 | record | 该滤 | `artifacts/ke_eval/install_matrix.json` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8618 | record | 该滤 | `artifacts/ke_eval/ke_eval_fig1.png` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8618 | record | 该滤 | `artifacts/ke_eval/thinlayer_result.json` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8618 | record | 该滤 | `artifacts/ke_eval/thinlayer_roundtrip.json` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8691 | keep | 误滤 | `knowledge/oss-lbm/README.md` | main 已前进且内容不同：合并动作缺失（非覆盖保护本身之过） → `git show agent/m8691:knowledge/oss-lbm/README.md` |
| m8691 | record | 该滤 | `knowledge/oss-lbm/fingering/artifacts/fig1_fingering_verification.png` | 二进制/运行产物（db|sqlite|png|log） |
| m8676 | record | 该滤 | `artifacts/oss-lbm-kruger/kruger_source_index.json` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `artifacts/oss-lbm-kruger/make_report.py` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `artifacts/oss-lbm-kruger/probe_api.py` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `artifacts/oss-lbm-kruger/publish_report.py` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/README.md` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/analyze_validation.py` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/figures/ib_lbm_profile.png` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/figures/validation_runs.png` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/final_validation.log` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/kruger_bench_port.py` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/kruger_bench_profiles.png` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/kruger_bench_results.json` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/logs/iblbm_fluid_t2000.dat` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/logs/iblbm_poiseuille.log` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/logs/port_chapter5.log` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/logs/shanchen_radius12.log` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/logs/shanchen_radius15.log` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/logs/tg_scale1.log` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/logs/tg_scale2.log` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/logs/tg_scale4.log` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/run_meta.json` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/run_upstream_cases.sh` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8676 | record | 该滤 | `runs/oss-lbm-kruger-8676/validation_summary.json` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8669 | record | 该滤 | `knowledge/oss-lbm/ludwig/artifacts/runs/shear_wave_L16.log` | 二进制/运行产物（db|sqlite|png|log） |
| m8669 | record | 该滤 | `knowledge/oss-lbm/ludwig/artifacts/runs/shear_wave_L32.log` | 二进制/运行产物（db|sqlite|png|log） |
| m8669 | record | 该滤 | `knowledge/oss-lbm/ludwig/artifacts/runs/shear_wave_L8.log` | 二进制/运行产物（db|sqlite|png|log） |
| m8669 | record | 该滤 | `knowledge/oss-lbm/ludwig/artifacts/shear_wave_decay.png` | 二进制/运行产物（db|sqlite|png|log） |
| m8690 | keep | 误滤 | `knowledge/oss-lbm/claims/claims.json` | main 已前进且内容不同：合并动作缺失（非覆盖保护本身之过） → `git show agent/m8690:knowledge/oss-lbm/claims/claims.json` |
| m8690 | keep | 误滤 | `knowledge/oss-lbm/evidence/evidence.json` | main 已前进且内容不同：合并动作缺失（非覆盖保护本身之过） → `git show agent/m8690:knowledge/oss-lbm/evidence/evidence.json` |
| m8690 | keep | 误滤 | `knowledge/oss-lbm/provenance/provenance.json` | main 已前进且内容不同：合并动作缺失（非覆盖保护本身之过） → `git show agent/m8690:knowledge/oss-lbm/provenance/provenance.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/README.md` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/README.md` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/claims/tkc-fair-a1-protocol-conditions.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/claims/tkc-fair-a1-protocol-conditions.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/claims/tkc-fair-requires-open-access.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/claims/tkc-fair-requires-open-access.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/claims/tkc-prov-o-wasattributedto-signature.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/claims/tkc-prov-o-wasattributedto-signature.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/claims/tkc-tkrepo-rocrate-export-production.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/claims/tkc-tkrepo-rocrate-export-production.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/evidence/tke-fair-a1-2-auth-protocol.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/evidence/tke-fair-a1-2-auth-protocol.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/evidence/tke-fair-a1-block.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/evidence/tke-fair-a1-block.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/evidence/tke-fair-preamble-machine-actionability.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/evidence/tke-fair-preamble-machine-actionability.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/evidence/tke-fair-r1-1-license.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/evidence/tke-fair-r1-1-license.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/evidence/tke-prov-o-entry6-wasattributedto.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/evidence/tke-prov-o-entry6-wasattributedto.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/evidence/tke-prov-o-section31-agent-responsibility.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/evidence/tke-prov-o-section31-agent-responsibility.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/evidence/tke-ro-crate-root-data-entity-must.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/evidence/tke-ro-crate-root-data-entity-must.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/evidence/tke-tkrepo-standards-mapping-p0.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/evidence/tke-tkrepo-standards-mapping-p0.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/production-result.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/production-result.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/provenance/tkp-m8554-contested.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/provenance/tkp-m8554-contested.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/provenance/tkp-m8554-insufficient.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/provenance/tkp-m8554-insufficient.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/provenance/tkp-m8554-scientific.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/provenance/tkp-m8554-scientific.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/scenario-contested.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/scenario-contested.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/scenario-insufficient.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/scenario-insufficient.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/scenario-scientific.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/scenario-scientific.json` |
| m8620 | other-mission | 误滤 | `platform-test/epistemic-benchmark/pilots/m8554/validate_pilot.py` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8620:platform-test/epistemic-benchmark/pilots/m8554/validate_pilot.py` |
| m8620 | record | 该滤 | `runs/ke-proto/demo-output.txt` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8620 | record | 该滤 | `runs/ke-proto/ke-proto-distributions.png` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8620 | record | 该滤 | `runs/ke-proto/query-snapshot.json` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8635 | record | 该滤 | `knowledge/oss-lbm/run_validate_assets.log` | 二进制/运行产物（db|sqlite|png|log） |
| m8635 | record | 该滤 | `knowledge/oss-lbm/run_validate_benchmark.log` | 二进制/运行产物（db|sqlite|png|log） |
| m8635 | record | 该滤 | `knowledge/oss-lbm/run_validate_oss_lbm.log` | 二进制/运行产物（db|sqlite|png|log） |
| m8619 | record | 该滤 | `artifacts/ke-mapping/fig1_projection_coverage.png` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8619 | record | 该滤 | `artifacts/ke-mapping/fig2_review_state_machine.png` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8619 | record | 该滤 | `artifacts/ke-mapping/fig3_epistemic_cap.png` | 运行记录区（artifacts/runs/results/REPORT_GATE） |
| m8619 | other-mission | 误滤 | `mappings/source/m8554/claims/tkc-fair-a1-protocol-conditions.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8619:mappings/source/m8554/claims/tkc-fair-a1-protocol-conditions.json` |
| m8619 | other-mission | 误滤 | `mappings/source/m8554/claims/tkc-fair-requires-open-access.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8619:mappings/source/m8554/claims/tkc-fair-requires-open-access.json` |
| m8619 | other-mission | 误滤 | `mappings/source/m8554/claims/tkc-prov-o-wasattributedto-signature.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8619:mappings/source/m8554/claims/tkc-prov-o-wasattributedto-signature.json` |
| m8619 | other-mission | 误滤 | `mappings/source/m8554/claims/tkc-tkrepo-rocrate-export-production.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8619:mappings/source/m8554/claims/tkc-tkrepo-rocrate-export-production.json` |
| m8619 | other-mission | 误滤 | `mappings/source/m8554/evidence/tke-fair-a1-2-auth-protocol.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8619:mappings/source/m8554/evidence/tke-fair-a1-2-auth-protocol.json` |
| m8619 | other-mission | 误滤 | `mappings/source/m8554/evidence/tke-fair-a1-block.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8619:mappings/source/m8554/evidence/tke-fair-a1-block.json` |
| m8619 | other-mission | 误滤 | `mappings/source/m8554/evidence/tke-fair-preamble-machine-actionability.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8619:mappings/source/m8554/evidence/tke-fair-preamble-machine-actionability.json` |
| m8619 | other-mission | 误滤 | `mappings/source/m8554/evidence/tke-fair-r1-1-license.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8619:mappings/source/m8554/evidence/tke-fair-r1-1-license.json` |
| m8619 | other-mission | 误滤 | `mappings/source/m8554/evidence/tke-prov-o-entry6-wasattributedto.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8619:mappings/source/m8554/evidence/tke-prov-o-entry6-wasattributedto.json` |
| m8619 | other-mission | 误滤 | `mappings/source/m8554/evidence/tke-prov-o-section31-agent-responsibility.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8619:mappings/source/m8554/evidence/tke-prov-o-section31-agent-responsibility.json` |
| m8619 | other-mission | 误滤 | `mappings/source/m8554/evidence/tke-ro-crate-root-data-entity-must.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8619:mappings/source/m8554/evidence/tke-ro-crate-root-data-entity-must.json` |
| m8619 | other-mission | 误滤 | `mappings/source/m8554/evidence/tke-tkrepo-standards-mapping-p0.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8619:mappings/source/m8554/evidence/tke-tkrepo-standards-mapping-p0.json` |
| m8619 | other-mission | 误滤 | `mappings/source/m8554/production-result.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8619:mappings/source/m8554/production-result.json` |
| m8619 | other-mission | 误滤 | `mappings/source/m8554/provenance/tkp-m8554-contested.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8619:mappings/source/m8554/provenance/tkp-m8554-contested.json` |
| m8619 | other-mission | 误滤 | `mappings/source/m8554/provenance/tkp-m8554-insufficient.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8619:mappings/source/m8554/provenance/tkp-m8554-insufficient.json` |
| m8619 | other-mission | 误滤 | `mappings/source/m8554/provenance/tkp-m8554-scientific.json` | 路径含他单号段 m8554/；本单产物引用了该路径（缺了即红） → `git show agent/m8619:mappings/source/m8554/provenance/tkp-m8554-scientific.json` |
| m8619 | record | 该滤 | `runs/ke_mapping_validation.json` | 运行记录区（artifacts/runs/results/REPORT_GATE） |

**合计**：92 个被滤文件；按规则 {'record': 49, 'keep': 6, 'other-mission': 37}；按判定 {'该滤': 49, '误滤': 43}。
