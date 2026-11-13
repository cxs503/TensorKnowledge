# KF-RESULT wp-5347-04

**工作包** `wp-5347-04` ｜ 工序 04 独立审核（red-team-reviewer） ｜ 被审对象 **wp-5347-01** （`asset_manifest.json`, sha256 `d6468dbe0ee596d7…`） ｜ report_id `5347` ｜ 判决 **needs-fix**

## ① 本工序做了什么

只做一件事：以报告 5347 的原文（平台 API 现取字节，sha256 `sha256:bdd7bb0e76c120366d71fe047057056333cf83cfef6e0a2ca1ca125082a9d2e1`，4206 字符 / 6475 字节）为唯一真值面，对上游 01 包（资产登记）做**逐条从字节重算**的对抗式复核，并按 G2 的 fail-closed 语义判 pass / needs-fix。

- 复核 26 条资产 locator、计数账目、开放账目、记录字段定位与报告表算术，共 12 项检查（10 通过）。
- 判决 = **needs-fix**：主因 1 条 quote 被改写（本报告 F1），且 `quote_sha256` 与 `quote` 自相矛盾。
- 未读生产者自述（`README.md` / `KF-RESULT-wp-5347-01.md` / 回执未打开），只读行为产物 `asset_manifest.json`。不给任何验证状态判定（验证级别由平台门计算，本工序不代算）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET /tensor/reports/5347`，只取 `markdown` 字段；重算 sha256 = `sha256:bdd7bb0e76c120366d71fe047057056333cf83cfef6e0a2ca1ca125082a9d2e1`，与契约 `source_hash` 字节相等（不做换行归一）。
2. **locator 逐条重算**（`work/review_wp5347_04.py`）：声明了 offset 就要求 `markdown[start:end] == quote`（字节相等）；无 offset 要求 quote 可逐字检索；再核 `quote_sha256 == sha256(quote)`，并核 registered `path` 是否逐字出现在其 quote 内。
3. **账目闭合**：`counts.assets / by_kind / by_reachability / unresolved` 与实测逐项比对；开放账目的 path 集合须与资产集合一致（无孤儿、无悬空、无重复）。
4. **记录字段定位**：`locator_type=record_field` 的图资产，核 `value_sha256 == sha256(name)` 且 `declared_caption` 与平台记录 `figures[].caption` 逐字相等。
5. **覆盖探针**：用独立正则回扫正文 path-like token，检查登记是否漏项（advisory）。
6. **算术探针**：从正文表格行取值，检验报告印刷的 `TRACKED 占比` 能否由同表可见行复算（advisory）。
7. **端点实测**：`GET /tensor/reports/5347/figures` 与 `/figures/provenance_gate_matrix.png` 亲自打点，核 01 包关于『图像字节不可取回』的陈述。
8. **零手抄护栏**：`scripts/review_wp5347_04_report.py` 在写产物前断言每条被嵌入的引文都是原文子串，不满足即构建失败（本报告所有 quote 均通过该断言）。

## ③ 计算结果（复核矩阵）

| # | 检查 | 结果 | 关键数字 |
|---|---|---|---|
| 1 | `R1.source_hash` | PASS | 重算/契约/清单 三方同一：`sha256:bdd7bb0e76c12036` |
| 2 | `R2.char_count` | PASS | 重算 4206 字符（6475 字节）= 契约 4206 |
| 3 | `R3.quote_at_declared_offsets` | **FAIL** | 核 26 条；不符 1 条 |
| 4 | `R4.quote_sha256_matches` | **FAIL** | 不符 1 条 |
| 5 | `R5.quote_searchable_when_no_offsets` | PASS | 不符 0 条 |
| 6 | `R6.registered_path_occurs_in_quote` | PASS | 不符 0 条 |
| 7 | `R9.record_field_locator_resolvable` | PASS | record_field 2 条，caption 不符 0 条 |
| 8 | `R7.counts_consistent` | PASS | assets 26；kind 10 类；reach 5 类；unresolved 26 |
| 9 | `R8.coverage_probe_recall` | PASS | 正文 token 22 个，未登记 1 个（code/test/doc） |
| 10 | `R10.record_identity_fields_match` | PASS | title/scenario_key/status/tags/created_at 全等 |
| 11 | `R11.unresolved_account_closed` | PASS | unresolved 26 vs assets 26，孤儿 0 |
| 12 | `R12.report_ratio_reproducible` | PASS | 可见行复算 [0.633, 0.6291] vs 印刷 [0.8472, 0.8476] |

**逐资产结论**：登记 26 条资产中 25 条 locator 字节级可定位，1 条不可（`asset-5347-024`；同一资产在 R3/R4 两项检查里各记一次违规，去重后按资产计 1 条）。

**阻塞发现 F1（quote 被改写）**：

- 声明 span `[3448, 3522)`，原文该切片为：`- **集群不适用**：外协方双节点 loong64 环境缺 `libflexiblas.so.3`/`scipy`，`pytest` 收集期即`
- 01 包实际提交的 quote 为：`- **集群不适用**：外协方双节点 loong64 环境缺 `libflexiblas.so.3`/`scipy`，`pytest` 收集期即`
- 该包声明的 `quote_sha256` = `5471f57c35e9675dddb2decbd77396c6d14a00c422504b94873802f2966a799d`，恰好等于**原文切片**的哈希；而 `sha256(提交的 quote)` = `2840238c344ba7b46b03c481b419c4301c9b31d892a1931e36ef6f214218355c` —— 即「哈希记的是原文、正文被替换过」，自证改写。

**非阻塞发现**：F2 占比行不可由同表复算（缺 `doc:TRACKED` 行，可见行复算 [0.633, 0.6291]，隐含该行为 [178, 192]）；F3 图资产 404 措辞把路由级 404 与资产级 404 混写；F4 三条资产共用 span `[673, 764)`。

图 1：12 项复核逐项判定（红色=FAIL；标 advisory 的两项不参与判决）。图 2：26 条资产按 kind×locator_type 的可定位性堆叠（25 绿 / 1 红）。

## ④ 证据定位表（claim / 字段 → 原文引文，逐字）

引文均为 report 5347 markdown 的字节切片（构建期断言命中；含 `|` 的表格行用缩进代码块原样给出，不做转义）：

- 被改写的原文切片（span 3448–3522）：

      - **集群不适用**：外协方双节点 loong64 环境缺 `libflexiblas.so.3`/`scipy`，`pytest` 收集期即

- 契约 source_hash（= 现取 markdown 字节哈希 = 清单 source.source_hash）：

      sha256:bdd7bb0e76c120366d71fe047057056333cf83cfef6e0a2ca1ca125082a9d2e1

- 账本扫描文档数（提交态 145 → 重生成 152）：

      | 扫描文档数 | 145 | 152 |

- 指针数（831 → 879）：

      | 指针数 | 831 | 879 |

- code:TRACKED（275 → 290）：

      | `code:TRACKED` | 275 | 290 |

- test:TRACKED（251 → 263）：

      | `test:TRACKED` | 251 | 263 |

- 印刷 TRACKED 占比（F2：不可由同表可见行复算）：

      | 判 `TRACKED` 占比 | 0.8472 | 0.8476 |

- ORPHAN 保持 0：

      | 失效指针 ORPHAN | 0 | 0 |

- 自托管布局 main 假红 / 修复版 PASS（F1 所在章节相邻结论）：

      | self-hosted loong64 (.../ci_env/_work/...) | FAIL | PASS |

- 报告自认未跑全量（honest-FAIL）：

      本轮未把 `python -m pytest -q` 全量跑完

被审 01 包的字段侧定位（引用 manifest 自身字段，不经平台原文重算）：`asset_manifest.json` 中 `assets[].locator.start_offset/end_offset/quote/quote_sha256`、`counts.*`、`unresolved[].path`；被审字节以 `artifact_sha256` 钉住。

## ⑤ 注意点与局限

- **不是对技术结论真伪的判定**：报告 5347 关于 TensorDEM 仓内事实（20 passed / 36 passed / 152 篇 879 条 / ORPHAN 0）无法在本工作树复现（无该仓检出），本报告一律记 not_run，不代替 CI 结论。
- **只审 01，不越界代做 03**：该链当前无 claims / evidence 包，语义门没有对象；未生成任何知识对象。
- **上游字节身份**：被审清单取自兄弟工作树路径，已用 `artifact_sha256` 钉住；若他人看到不同字节，以哈希对照即可判定，勿以『同名文件』代替。
- **F1 的修复不影响证据本身**：原文切片在报告里本就是公开文本；quote 字段永不可编辑，需要脱敏只能缩短 span 或另设 redaction 字段。
- **对抗式复核的能力边界**：字节级比对能抓改写/错位/换 hash，抓不到『原文本身写错』——那要靠下游 语义门与 CI 复跑。

## ⑥ 自检（对照 acceptance 逐条）

| acceptance | 结论 | 依据 |
|---|---|---|
| `valid_json` | 勾 | 产物 `review_report.json` 由 `json.dump` 写出并可 `json.load` 回读 |
| `schema_pass` | 勾 | 对 `schemas/kf_result.v1.schema.json` 校验通过（jsonschema，本地实测） |
| `reviewer_independent` | 勾 | 审核者=mission 15832 工作树；被审包生产者=mission 15564（清单 `registration.producer`），非同包同树，未协作 |
| `upstream_packages_completed` | 勾（内容有阻塞缺陷） | 01 包存在且结构自洽（26 条资产 / 计数闭合 / 开放账目闭合）；但 F1 使其不满足 G2 证据门的字节相等要求 → 判 needs-fix |
| 附带：不标 verified | 勾 | 产物内无任何验证状态判定字段，只输出重算结果 |
| 附带：零手抄 | 勾 | 所有引文经构建期断言（子串必须命中原文）后才写入 |

误差判定（关键量 vs 基准，逐项）：

| 关键量 | 基准 | 实测 | 误差 | <3%？ |
|---|---|---|---|---|
| 原文 sha256 | 契约 source_hash | 重算同值 | 0（布尔） | 是 |
| 字符数 | 契约 chars=4206 | 4206 | 0 | 是 |
| 资产 locator 字节相等率 | 26/26 应相等 | 25/26 | 偏差 3.8% | **否**（1 条不符，>3%） |
| 计数账目 | 实测值 | 与声明全等 | 0 | 是 |
| 占比行可复算性 | 应可由同表复算 | 不可复算（隐含 1 行） | 数值差 21.4% | **否**（advisory，非判决项） |

结论：**关键判据（哈希/字符数/计数）零误差；locator 一律性 1/26 不符（3.8% > 3%），故本审核不通过上游 01 包，判 needs-fix**。未完成项=仓内实测复跑（not_run），不粉饰。

```json
{
  "package_id": "wp-5347-04",
  "task_type": "04-independent-review",
  "report_id": "5347",
  "provenance": {
    "source_hash": "sha256:bdd7bb0e76c120366d71fe047057056333cf83cfef6e0a2ca1ca125082a9d2e1",
    "source_field": "markdown",
    "producer": "mission 15832 (agent m15832, TensorKnowledge)",
    "emitted_at": "2026-11-12T02:50:00+00:00",
    "notes": "review_report.json built from fresh platform bytes; all embedded quotes asserted verbatim against the report markdown and the reviewed manifest before writing."
  },
  "outputs": {
    "review_report.json": {
      "review": {
        "package_id": "wp-5347-04",
        "task_type": "04-independent-review",
        "report_id": "5347",
        "reviewer_role": "red-team-reviewer",
        "reviewed": {
          "package_id": "wp-5347-01",
          "task_type": "01-asset-registration",
          "artifact": "asset_manifest.json",
          "artifact_sha256": "sha256:d6468dbe0ee596d7ad83a2315f5741b73b80d1a58e6479ebadd3b6db42cb35db",
          "artifact_bytes": 28773,
          "artifact_origin": "/root/tp-agent/work/m15817/docs/production/wp-5347-01/asset_manifest.json",
          "source_hash": "sha256:bdd7bb0e76c120366d71fe047057056333cf83cfef6e0a2ca1ca125082a9d2e1"
        },
        "verdict": "needs-fix",
        "verdict_scope": "wp-5347-01 的 asset_manifest.json 内容面；不涉及 02/03/05 工序",
        "verdict_rationale": "26 条资产里 25 条 locator 逐字可定位、计数与开放账目全闭合；唯一阻塞项 F1 是 1 条 quote 被改写（字节不等）且 quote_sha256 与 quote 自相矛盾。按 G2 E3/E4 的 fail-closed 语义，该包在修复前不满足证据门；因缺陷单点且修复路径明确，判 needs-fix（request-changes），不判 reject。",
        "severity_counts": {
          "high": 1,
          "medium": 1,
          "low": 2
        },
        "semantic_fidelity": {
          "judged": true,
          "result": "partially-faithful",
          "basis": "逐条把 manifest 的 quote 与报告 markdown 字节比对（26/26），并核 registered path 是否逐字出现在其 quote 内（26/26）；25 条完全忠实，1 条（asset-5347-024）把原文机构名替换后仍保留原文哈希。",
          "not_judged": "报告对 TensorDEM 仓库侧事实（20 passed / 36 passed / 账本 152 篇 879 条）的语义真伪——本工作树无该仓库检出，属 not_run（见 checks_not_run）。"
        },
        "checks": [
          {
            "check": "R1.source_hash",
            "ok": true,
            "blocking": true,
            "detail": {
              "recomputed": "sha256:bdd7bb0e76c120366d71fe047057056333cf83cfef6e0a2ca1ca125082a9d2e1",
              "contract": "sha256:bdd7bb0e76c120366d71fe047057056333cf83cfef6e0a2ca1ca125082a9d2e1",
              "manifest": "sha256:bdd7bb0e76c120366d71fe047057056333cf83cfef6e0a2ca1ca125082a9d2e1"
            }
          },
          {
            "check": "R2.char_count",
            "ok": true,
            "blocking": true,
            "detail": {
              "recomputed_chars": 4206,
              "bytes": 6475,
              "contract_chars": 4206,
              "manifest_chars": 4206
            }
          },
          {
            "check": "R3.quote_at_declared_offsets",
            "ok": false,
            "blocking": true,
            "detail": {
              "violations": [
                {
                  "asset_id": "asset-5347-024",
                  "declared": [
                    3448,
                    3522
                  ],
                  "source_slice": "- **集群不适用**：外协方双节点 loong64 环境缺 `libflexiblas.so.3`/`scipy`，`pytest` 收集期即",
                  "shipped_quote": "- **集群不适用**：外协方双节点 loong64 环境缺 `libflexiblas.so.3`/`scipy`，`pytest` 收集期即",
                  "byte_equal": false
                }
              ],
              "assets_checked": 26
            }
          },
          {
            "check": "R4.quote_sha256_matches",
            "ok": false,
            "blocking": true,
            "detail": {
              "violations": [
                {
                  "asset_id": "asset-5347-024",
                  "recomputed": "sha256:2840238c344ba7b46b03c481b419c4301c9b31d892a1931e36ef6f214218355c",
                  "declared": "sha256:5471f57c35e9675dddb2decbd77396c6d14a00c422504b94873802f2966a799d"
                }
              ]
            }
          },
          {
            "check": "R5.quote_searchable_when_no_offsets",
            "ok": true,
            "blocking": true,
            "detail": {
              "violations": []
            }
          },
          {
            "check": "R6.registered_path_occurs_in_quote",
            "ok": true,
            "blocking": true,
            "detail": {
              "violations": []
            }
          },
          {
            "check": "R9.record_field_locator_resolvable",
            "ok": true,
            "blocking": true,
            "detail": {
              "violations": [],
              "caption_violations": [],
              "record_figure_names": [
                "provenance_gate_matrix.png",
                "ledger_regeneration.png"
              ]
            }
          },
          {
            "check": "R7.counts_consistent",
            "ok": true,
            "blocking": true,
            "detail": {
              "assets": 26,
              "declared_assets": 26,
              "by_kind_recomputed": {
                "environment_layout": 8,
                "document": 1,
                "code": 5,
                "evidence_ledger": 1,
                "artifact": 2,
                "script": 2,
                "ephemeral_sandbox": 2,
                "test": 2,
                "environment_dependency": 1,
                "figure": 2
              },
              "by_kind_declared": {
                "artifact": 2,
                "code": 5,
                "document": 1,
                "environment_dependency": 1,
                "environment_layout": 8,
                "ephemeral_sandbox": 2,
                "evidence_ledger": 1,
                "figure": 2,
                "script": 2,
                "test": 2
              },
              "by_reach_recomputed": {
                "environment_layout": 8,
                "external_repo_artifact": 13,
                "ephemeral_sandbox": 2,
                "environment_dependency": 1,
                "metadata_only": 2
              },
              "by_reach_declared": {
                "environment_dependency": 1,
                "environment_layout": 8,
                "ephemeral_sandbox": 2,
                "external_repo_artifact": 13,
                "metadata_only": 2
              },
              "unresolved_recomputed": 26,
              "unresolved_declared": 26
            }
          },
          {
            "check": "R8.coverage_probe_recall",
            "ok": true,
            "blocking": false,
            "detail": {
              "tokens_found": 22,
              "registered_paths": 35,
              "not_registered_count": 1,
              "not_registered": [
                "code/test/doc"
              ],
              "note": "advisory probe: manifest declares its own token grammar; misses matter only if they are real repo paths named in the report"
            }
          },
          {
            "check": "R10.record_identity_fields_match",
            "ok": true,
            "blocking": true,
            "detail": {
              "title": {
                "manifest": "TensorDEM main CI 清红（m4829）：runner 路径断言与证据账本过期",
                "record": "TensorDEM main CI 清红（m4829）：runner 路径断言与证据账本过期",
                "equal": true
              },
              "scenario_key": {
                "manifest": "ci_clearance",
                "record": "ci_clearance",
                "equal": true
              },
              "status": {
                "manifest": "published",
                "record": "published",
                "equal": true
              },
              "tags": {
                "manifest": [
                  "CI",
                  "gate",
                  "provenance",
                  "doc-evidence",
                  "TensorDEM",
                  "main-red"
                ],
                "record": [
                  "CI",
                  "gate",
                  "provenance",
                  "doc-evidence",
                  "TensorDEM",
                  "main-red"
                ],
                "equal": true
              },
              "created_at_prefix": {
                "manifest": "2026-11-06T14:46:12.438974+00:00",
                "record_starts_with_it": true
              }
            }
          },
          {
            "check": "R11.unresolved_account_closed",
            "ok": true,
            "blocking": true,
            "detail": {
              "unresolved_paths": 26,
              "asset_paths": 26,
              "only_in_unresolved": [],
              "only_in_assets": [],
              "dup_unresolved": []
            }
          },
          {
            "check": "R12.report_ratio_reproducible",
            "ok": true,
            "blocking": false,
            "detail": {
              "rows_found": {
                "code:TRACKED": [
                  275,
                  290
                ],
                "test:TRACKED": [
                  251,
                  263
                ],
                "指针数": [
                  831,
                  879
                ],
                "TRACKED占比": [
                  "0.8472",
                  "0.8476"
                ]
              },
              "printed_ratio": [
                0.8472,
                0.8476
              ],
              "ratio_from_visible_rows": [
                0.633,
                0.6291
              ],
              "reproducible_from_visible_rows": false,
              "implied_doc_tracked_not_shown": [
                178,
                192
              ],
              "conclusion": "printed ratio needs an unshown doc:TRACKED row (178 -> 192); not recomputable from the printed table alone, but arithmetically consistent with such a row"
            }
          }
        ],
        "checks_passed": 10,
        "checks_total": 12,
        "findings": [
          {
            "id": "F1",
            "severity": "high",
            "blocking": true,
            "title": "asset-5347-024 的 quote 不是逐字原文：机构名被替换（外协方 -> 外协方），而 quote_sha256 仍是原文哈希",
            "scope": "wp-5347-01 / asset_manifest.json / asset-5347-024",
            "evidence": {
              "source_slice_at_declared_offsets": {
                "start_offset": 3448,
                "end_offset": 3522,
                "text": "- **集群不适用**：外协方双节点 loong64 环境缺 `libflexiblas.so.3`/`scipy`，`pytest` 收集期即",
                "sha256": "sha256:5471f57c35e9675dddb2decbd77396c6d14a00c422504b94873802f2966a799d"
              },
              "shipped_quote": {
                "text": "- **集群不适用**：外协方双节点 loong64 环境缺 `libflexiblas.so.3`/`scipy`，`pytest` 收集期即",
                "sha256": "sha256:2840238c344ba7b46b03c481b419c4301c9b31d892a1931e36ef6f214218355c"
              },
              "declared_quote_sha256": "sha256:5471f57c35e9675dddb2decbd77396c6d14a00c422504b94873802f2966a799d",
              "byte_equal_at_offsets": false,
              "declared_hash_equals_source_slice_hash": true,
              "shipped_quote_sha256_matches_declared": false
            },
            "why_it_matters": "G2 的 E3/E4 是 fail-closed：声明了偏移就必须 md[start:end] == quote 字节相等；哈希与 quote 自相矛盾说明文本是在抽取后被改写的，属『篡改 quote』等价物。下游 03 若以此节点做证据，会把改写后的文本当作原文引用。",
            "reproduction": "python3 work/review_wp5347_04.py --json /tmp/rv.json ; 看 R3.quote_at_declared_offsets / R4.quote_sha256_matches 两条 violations",
            "remediation": [
              "把 quote 恢复为 md[3448:3522] 的逐字切片（上述 source_slice_at_declared_offsets.text）；若确需脱敏，改为缩短 span 到不含机构名的子串（例如自『环境缺 `libflexiblas.so.3`』起），或另设显式 redaction 字段并在其中记录被替换的原文；quote 字段本身永不可编辑。"
            ]
          },
          {
            "id": "F2",
            "severity": "medium",
            "blocking": false,
            "title": "报告表的『TRACKED 占比』无法用同表可见行复算（缺 doc:TRACKED 行）：可见行复算 0.633/0.6291 vs 印刷 0.8472/0.8476",
            "scope": "report 5347 §③『证据账本计数』表（对下游 03 为 advisory）",
            "evidence": {
              "printed_rows": [
                "| 扫描文档数 | 145 | 152 |",
                "| 指针数 | 831 | 879 |",
                "| `code:TRACKED` | 275 | 290 |",
                "| `test:TRACKED` | 251 | 263 |",
                "| 判 `TRACKED` 占比 | 0.8472 | 0.8476 |"
              ],
              "recomputed_from_visible_rows": [
                0.633,
                0.6291
              ],
              "printed_ratio": [
                0.8472,
                0.8476
              ],
              "implied_unshown_row_doc_TRACKED": [
                178,
                192
              ]
            },
            "why_it_matters": "该行若被下游直接引用为『账本健康度』，引用者无法自证；补一行 doc:TRACKED 即可闭环。算术上与『存在一行 doc:TRACKED=192』自洽（152 篇态），故非造假，属『不可独立复算』。",
            "reproduction": "python3 work/review_wp5347_04.py --json /tmp/rv.json ; 看 R12",
            "remediation": [
              "报告或账本工件中显式给出 doc:TRACKED 计数行，或直接引用 docs/doc_evidence_ledger.json 的机器可读字段。"
            ]
          },
          {
            "id": "F3",
            "severity": "low",
            "blocking": false,
            "title": "图资产登记的理由陈述可复现但措辞不精确：/tensor/reports/5347/figures 是路由级 404，图级 404 来自 /figures/<name>",
            "scope": "wp-5347-01 / asset-5347-025、asset-5347-026（reachability=metadata_only）",
            "evidence": {
              "probe": "GET /tensor/reports/5347/figures -> 404 {\"detail\":\"Not Found\"} ; GET /tensor/reports/5347/figures/provenance_gate_matrix.png -> 404 {\"detail\":\"figure not found\"}",
              "record_figures": [
                "provenance_gate_matrix.png",
                "ledger_regeneration.png"
              ],
              "declared_caption_matches_record": true
            },
            "why_it_matters": "结论（图像字节不可取回、只能登记为 metadata_only）成立；但把两条不同 404 混为一句，下游复现时可能误判为『报告无图』。",
            "reproduction": "见上 probe 两条 GET；或读 review_evidence.json 的 R9 段",
            "remediation": [
              "把 note 写成『/figures/<name> 返回 figure not found，/figures 路由不存在』，区分路由缺失与资产缺失。"
            ]
          },
          {
            "id": "F4",
            "severity": "low",
            "blocking": false,
            "title": "asset-5347-001/002/003 共用同一 char_span [673,764]，span 身份 ≠ 资产身份",
            "scope": "wp-5347-01 / asset_manifest.json",
            "evidence": {
              "shared_span": [
                673,
                673,
                673
              ],
              "paths": [
                "/home/runner/work/<repo>/<repo>",
                "/work/",
                ".../_work/<repo>/<repo>"
              ]
            },
            "why_it_matters": "合规（三个 path token 都逐字出现在该 span 内），但下游若按 offset 去重会把三条资产折叠成一条。",
            "reproduction": "review_evidence.json R6（26/26 通过）+ 直接读 manifest 三条 locator",
            "remediation": [
              "在 manifest 里注明『span 可被多资产共享，去重键是 (path, span)』。"
            ]
          }
        ],
        "checks_not_run": [
          {
            "item": "TensorDEM main@524821fd 的 pytest / ruff / 账本 --check 实际输出",
            "status": "not_run",
            "reason": "本工作树只有 TensorKnowledge 检出，未含 TensorDEM 仓库；报告自述 20 passed / 36 passed 无法在此复现"
          },
          {
            "item": "docs/doc_evidence_ledger.json 的逐状态计数（152 篇 / 879 条 / ORPHAN 0）",
            "status": "not_run",
            "reason": "账本在 TensorDEM 仓内；本单只允许用 report 5347 的 markdown 作原文，未取该仓工件"
          },
          {
            "item": "两张结果图的图像内容（provenance_gate_matrix.png / ledger_regeneration.png）",
            "status": "not_run",
            "reason": "记录只有 name/caption 元数据，/figures/<name> 返回 figure not found（已实测），无可比对字节"
          },
          {
            "item": "02/03 工序产物（classification / claims / evidence）的审核",
            "status": "not_applicable",
            "reason": "该报告链当前只存在 01 包；无 claim 可做语义门审核，未越界代做"
          }
        ],
        "scope": {
          "inputs_used": [
            "GET /tensor/reports/5347 的 markdown 字段（sha256 与契约一致：sha256:bdd7bb0e76c120366d71fe047057056333cf83cfef6e0a2ca1ca125082a9d2e1）"
          ],
          "bytes_pinned": {
            "markdown_sha256": "sha256:bdd7bb0e76c120366d71fe047057056333cf83cfef6e0a2ca1ca125082a9d2e1",
            "markdown_chars": 4206,
            "markdown_bytes": 6475,
            "manifest_sha256": "sha256:d6468dbe0ee596d7ad83a2315f5741b73b80d1a58e6479ebadd3b6db42cb35db"
          },
          "checks_performed": [
            "R1 source_hash",
            "R2 char_count",
            "R3 quote_at_declared_offsets",
            "R4 quote_sha256",
            "R5 quote_searchable",
            "R6 registered_path_in_quote",
            "R7 counts_consistency",
            "R8 coverage_probe",
            "R9 record_field_locator",
            "R10 record_identity",
            "R11 unresolved_account_closure",
            "R12 report_ratio_reproducibility",
            "F3 端点实测探测"
          ]
        },
        "context_isolation": {
          "producer_explanation_excluded": true,
          "files_read_from_upstream_package": [
            "asset_manifest.json"
          ],
          "files_present_but_not_opened": [
            "README.md",
            "KF-RESULT-wp-5347-01.md",
            "kf_result.json",
            "publish_receipt.json",
            "live_gate.json",
            "platform_gate.json",
            "checks.json"
          ],
          "note": "只读 01 工序的行为产物（asset_manifest.json），不读生产者自述/回执；因此本审核不引用生产者的任何解释性文字。"
        },
        "independence_limitations": [
          "上游产物取自兄弟工作树 /root/tp-agent/work/m15817/docs/production/wp-5347-01/asset_manifest.json（不在平台包 API 上），已用 artifact_sha256=sha256:d6468dbe0ee596d7ad83a2315f5741b73b80d1a58e6479ebadd3b6db42cb35db 钉住被审字节；若他人看到的是不同字节，以其哈希与本报告 sha256:d6468dbe0ee5 对照即可判定。",
          "审核者=mission 15832 工人；被审包生产者=mission 15564 工人（见 manifest registration.producer 字段），非同一包、非同一工作树、未协作。",
          "语义门（M6）本质不可程序化：本报告的语义判断建立在 26 条 locator 的字节比对与 1 条算术探针上，不是对报告技术结论真伪的判定（那需要 TensorDEM 检出）。",
          "未使用任何生产者 prompt / 解释文本，方法为从源字节独立重算（对抗式复核）。"
        ],
        "disposition": "request-changes",
        "blocking_remediation": [
          "F1：把 asset-5347-024 的 quote 改为 md[3448:3522] 的逐字切片（或缩短 span 以规避机构名，quote 字段永不编辑），重生成后重跑 R3/R4 应为 0 violations。"
        ],
        "non_blocking_suggestions": [
          "F2：补 doc:TRACKED 行或直接引用账本工件字段",
          "F3：区分路由 404 与资产 404",
          "F4：注明 span 可被多资产共享、去重键是 (path, span)"
        ],
        "status_boundary_note": "本报告只输出复核结果（recomputed/matched），不含任何验证状态判定；验证级别由平台门计算。",
        "reproduce": "python3 work/review_wp5347_04.py --json docs/kf/wp-5347-04/review_evidence.json && python3 scripts/review_wp5347_04_report.py"
      }
    }
  }
}
```
