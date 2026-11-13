# KF-RESULT wp-5624-04

- package_id: `wp-5624-04` ｜ task_type: `04-independent-review` ｜ lane: C
- report_id: `5624`（本包唯一触碰的报告）｜ source: `tensor://reports/5624` · field=`markdown`
- source_hash: `sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839`
  （独立重算，与契约声明值一致：true）
- 分层标签（原样登记、不解读）：`IN15-O5|in15-o5-artifact-sha256-indexer|s`
- tags: `kf-wp:wp-5624-04`
- 审核对象：`wp-5624-01`（01-asset-registration）
- 状态：draft（verification 由平台门计算，本包不标 verified）

## ① 本工序做了什么

对 wp-5624-01（01-asset-registration）的产出做独立 adversarial review：
独立从平台 API 重取 report 5624 原文，复算 sha256 哈希，逐字验证 9 条 locator，
跑通上游 11 条 pytest，探测提取逻辑缺陷（重复引用/边界/一致性），
给出 severity 分级的审核结论与修复建议。

## ② 怎么做的（步骤/工具/关键设置）

1. **独立取原文**：`POST $TENSOR_API_BASE/auth/login` 取 token → `GET $TENSOR_API_BASE/tensor/reports/5624`。
   仅读 5624 一份；未读写任何其它 report_id。
2. **哈希复算**：`hashlib.sha256(markdown.encode('utf-8'))` 得
   `sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839`，
   与契约值逐字节比对 → 一致。字符数 1833、UTF-8 字节数 3255 均吻合。
3. **逐字验证 locator**：对 asset_manifest.json 中 9 条 locator quote 逐一做
   `quote in markdown`（markdown 项）或 `quote in figure.captions`（figures 项）→ 9/9 命中。
4. **小节切分复算**：按 ATX 标题切分 7 节，逐节复算 chars 与 sha256 → 与 manifest 一致。
5. **缺陷探测**：
   - 检查 referenced_artifacts 的 locator_quote 唯一性 → 发现 ref-01 与 ref-02 重复
   - 检查 lines 计数一致性 → 发现 46 vs 47 的歧义
   - 检查测试环境依赖 → 发现 artifacts/ 目录 gitignored 导致新鲜克隆下测试全崩
6. **跑上游测试**：`python3 -m pytest tests/kf/test_wp_5624_01.py -v` → 11 passed
   （需先补全 artifacts/ 目录，见注意点）。
7. **Schema 校验**：`jsonschema.validate(kf_result, kf_result.v1.schema.json)` → pass。

关键设置：审核不依赖生产者解释；所有数字/引文逐字来自原文或上游产物 JSON；
未跨 worktree 取证；未重算内容摘要值。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-5624-04/review_report.json` | 审核结果信封：package_id / task_type / report_id / provenance / outputs（含 findings） |
| `docs/kf/wp-5624-04/kf_result_wp-5624-04.md` | 本报告（六段 + 唯一 json 块） |

## ④ 证据定位表（审核发现 → 原文/产物引文）

| 发现 | 证据来源 | 引文/数据 |
|---|---|---|
| ref-01/ref-02 重复 | asset_manifest.json `referenced_artifacts` | ref-01 quote = ref-02 quote = `` `artifacts/`（0 文件）与 `runs/`（0 文件），`` |
| 重复 quote 在原文出现次数 | /tmp/md5624.txt（原文） | `md.count(quote) == 1`，位于第 7 行 |
| lines 计数歧义 | asset_manifest.json `size.lines` vs 原文 | manifest=46，split=47（末行空），newline_count=46 |
| 测试环境依赖 | test_wp_5624_01.py fixture | `OUT / "kf_result.json"` 指向 artifacts/（gitignored） |
| 内部矛盾已正确标记 | asset_manifest.json `observations[0]` | `5624-obs-01`: status=unresolved, 三处计数冲突 |
| 哈希一致 | 独立复算 vs 契约 | `sha256:15b2f982...` == `sha256:15b2f982...` |
| 9/9 locator 命中 | 逐字匹配 | 4 条 markdown + 2 条 digest + 3 条 figures 全部 `in` 检查通过 |
| 11 pytest 通过 | pytest 输出 | `11 passed, 1 warning` |

## ⑤ 注意点与局限

1. **未重跑 artifact_indexer 工具**：该工具位于 m4963 的 TensorPlatform worktree，
   超出本包边界，无法独立验证其索引结果的正确性。
2. **工件存在性未核**：报告声明的 `artifacts/`、`runs/` 等路径属于另一 worktree，
   本包不跨树取证，故全部 `existence=not_checked`。
3. **内容摘要值未重算**：索引表 sha256 只登记不重算（源工件不在本 worktree）。
4. **图载荷不可验**：figures 无 png_base64，无法核验图与数据的一致性。
5. **测试需补 artifacts/**：上游测试套件要求 `artifacts/kf/wp-5624-01/kf_result.json` 存在，
   但该路径被 .gitignore 排除。本审核中手动从 docs/ 镜像复制后测试通过。
6. **LLM 同族局限**：审核者与生产者可能共享推理模式，独立性受此限制。

## ⑥ 自检（逐条对照 acceptance 打勾/叉）

| acceptance 项 | 结果 | 证据 |
|---|---|---|
| valid_json | ✅ | review_report.json 可 `json.loads` |
| schema_pass | ✅ | kf_result 信封结构符合 kf_result.v1.schema.json |
| reviewer_independent | ✅ | 独立取原文、复算哈希、逐字验证，未看生产者解释 |
| upstream_packages_completed | ✅ | wp-5624-01 产物存在且 schema 通过 |
| 不标 verified | ✅ | 全文无 "verified" 作为状态值 |
| 单一报告边界 | ✅ | 仅读 report_id=5624 |

### 审核结论

**Disposition: approve_with_notes**

wp-5624-01 产出结构正确：schema 通过、哈希验证通过、9/9 locator 命中、
边界约束满足、claims 策略正确。发现 1 个中等问题（ref-01/ref-02 重复引用）、
2 个低等问题（lines 计数歧义、测试环境依赖），均不阻塞核心登记正确性。
无阻塞性正确性或安全缺陷。

### repro_cmd（一键复跑）

```bash
cd <repo-root> \
 && python3 -c "
import urllib.request, json, os, hashlib
api=os.environ['TENSOR_API_BASE']; u=os.environ['TENSOR_AGENT_USER']; p=os.environ['TENSOR_AGENT_PASS']
t=json.loads(urllib.request.urlopen(urllib.request.Request(f'{api}/auth/login',json.dumps({'username':u,'password':p}).encode(),headers={'Content-Type':'application/json'})).read())['access_token']
md=json.loads(urllib.request.urlopen(urllib.request.Request(f'{api}/tensor/reports/5624',headers={'Authorization':f'Bearer {t}'})).read())['markdown']
print('hash:', 'sha256:'+hashlib.sha256(md.encode()).hexdigest())
print('chars:', len(md))
" \
 && python3 -m pytest tests/kf/test_wp_5624_01.py -v
```

## 附：kf_result.json（唯一 json 块，与 `docs/kf/wp-5624-04/review_report.json` 同结构）

```json
{
  "package_id": "wp-5624-04",
  "task_type": "04-independent-review",
  "report_id": "5624",
  "provenance": {
    "source_hash": "sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839",
    "source_field": "markdown",
    "source_uri": "tensor://reports/5624",
    "producer": "m15837",
    "emitted_at": "2026-11-12T02:45:00Z",
    "notes": "04-independent-review of wp-5624-01 (01-asset-registration); reviewer independently fetched report 5624, recomputed hash, verified all locators, ran upstream tests, and probed for defects"
  },
  "outputs": {
    "review_report.json": {
      "review_target": "wp-5624-01",
      "review_target_type": "01-asset-registration",
      "reviewer": "m15837",
      "review_date": "2026-11-12",
      "independence_statement": "Reviewer independently fetched report 5624 via platform API, recomputed sha256 hash, verified all 9 locators against raw markdown, ran all 11 upstream pytest cases, and probed for extraction defects. Did not consult producer's explanation or internal notes.",
      "independence_limitations": [
        "Same LLM family may share reasoning patterns with producer",
        "Could not independently verify artifact existence (cross-worktree boundary)",
        "Could not re-run the original artifact_indexer tool (lives in m4963's TensorPlatform worktree)"
      ],
      "scope_checks_performed": [
        "Source hash recomputation (sha256 of markdown UTF-8 bytes)",
        "Section splitting verification (7 sections, line ranges, chars, sha256)",
        "All 9 locator quotes verified as verbatim substrings in markdown/figures",
        "Schema validation against kf_result.v1.schema.json",
        "Upstream pytest suite (11 tests) executed",
        "Duplicate ID check (ref/digest/obs IDs unique)",
        "Boundary check (only report 5624 read/written, no verified claims)",
        "Claims policy check (claims=[] allowed for 01 task)",
        "Figure caption matching against platform record figures field",
        "Deterministic rebuild test (re-running generator produces identical manifest)"
      ],
      "findings": [
        {
          "severity": "medium",
          "type": "duplicate_extraction",
          "title": "Duplicate locator quote: 5624-ref-01 and 5624-ref-02 share identical quote",
          "description": "Both ref-01 and ref-02 have the same locator_quote value. This phrase appears exactly once in the source markdown (line 7). Two distinct ref_ids pointing to the same single occurrence indicates a duplication bug in the path extraction regex logic.",
          "evidence": {
            "ref_01_quote": "`artifacts/`（0 文件）与 `runs/`（0 文件），",
            "ref_02_quote": "`artifacts/`（0 文件）与 `runs/`（0 文件），",
            "occurrences_in_markdown": 1,
            "markdown_line": 7,
            "test_coverage_gap": "test_no_duplicate_ids checks ID uniqueness but not quote uniqueness"
          },
          "affected_scope": "referenced_artifacts extraction; cosmetic (does not affect hash/section/claims correctness)",
          "recommendation": "Deduplicate quotes during extraction or merge into a single ref_id with multiple source locations if intended"
        },
        {
          "severity": "low",
          "type": "ambiguity",
          "title": "Lines count: manifest reports 46 but markdown has 47 lines (trailing empty line)",
          "description": "The manifest reports size.lines=46. The markdown has 46 newline characters and ends with a newline, producing 47 lines when split (last line empty). Section ranges end at line 46, so 46 is defensible as content lines, but the counting method is not documented.",
          "evidence": {
            "manifest_lines": 46,
            "actual_split_lines": 47,
            "newline_count": 46,
            "ends_with_newline": true,
            "last_section_end_line": 46
          },
          "affected_scope": "metadata only; no functional impact",
          "recommendation": "Document line counting convention"
        },
        {
          "severity": "low",
          "type": "test_environment_dependency",
          "title": "Test suite requires artifacts/ directory which is gitignored",
          "description": "The test fixture reads from artifacts/kf/wp-5624-01/kf_result.json, but this path is gitignored. In a fresh clone without the artifacts directory, all 11 tests fail with FileNotFoundError.",
          "evidence": {
            "test_fixture_path": "artifacts/kf/wp-5624-01/kf_result.json",
            "gitignored": true,
            "docs_mirror_exists": true,
            "tests_without_artifacts": "11 errors (FileNotFoundError)"
          },
          "affected_scope": "test reproducibility in fresh clones",
          "recommendation": "Add fallback in test fixture to try docs/ path if artifacts/ is missing"
        },
        {
          "severity": "info",
          "type": "positive_finding",
          "title": "Internal inconsistency correctly flagged as unresolved",
          "description": "The upstream package correctly identified the counting contradiction in the original report and registered it as observation 5624-obs-01 with status=unresolved, without inventing a resolution.",
          "evidence": {
            "observation_id": "5624-obs-01",
            "status": "unresolved",
            "conflicting_values": ["0 files (artifacts/)", "0 files (runs/)", "102 files total", "94+8=102 (Fig.1 caption)"]
          }
        },
        {
          "severity": "info",
          "type": "positive_finding",
          "title": "All 11 upstream tests pass; schema validation passes",
          "description": "After providing the missing artifacts directory, all 11 pytest cases pass. The kf_result.json validates against kf_result.v1.schema.json. Source hash matches contract value. All 9 locators resolve. Boundary constraints satisfied.",
          "evidence": {
            "pytest_result": "11 passed",
            "schema_validation": "pass",
            "hash_match": true,
            "locators_resolved": "9/9",
            "boundary_ok": true
          }
        }
      ],
      "checks_not_run": [
        "Independent re-execution of artifact_indexer tool (lives in m4963's TensorPlatform worktree, out of scope)",
        "Artifact existence verification (cross-worktree boundary constraint)",
        "Content digest value recomputation (source artifacts not in this worktree)",
        "Figure image content verification (no png_base64 payload in figures)"
      ],
      "overstated_claims": [
        {
          "claim": "11 pytest passed (in upstream report)",
          "reality": "Tests pass only when artifacts/ directory is populated; in a fresh clone without artifacts, all 11 tests error with FileNotFoundError. The upstream report states pytest 11 passed without noting this environmental dependency."
        }
      ],
      "disposition": "approve_with_notes",
      "disposition_rationale": "The wp-5624-01 output is structurally correct: schema-valid, hash-verified, all locators resolve, boundary constraints met, claims policy followed. The duplicate quote (ref-01/ref-02) is a medium-severity extraction bug but does not affect the core registration correctness. The lines count ambiguity and test environment dependency are low-severity issues. No blocking correctness or security defects found.",
      "remediation": [
        "Deduplicate ref-01/ref-02 or merge into single reference",
        "Document line counting convention in manifest",
        "Add docs/ fallback path in test fixture for fresh-clone reproducibility"
      ]
    }
  },
  "claims": []
}
```
