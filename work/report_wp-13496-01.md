# KF-RESULT wp-13496-01

tags: kf-wp:wp-13496-01, asset-registration, fem, elastoplastic, j2-flow

## ① 本工序做了什么

工作包 `wp-13496-01`（工序 `01-asset-registration`）对报告 `report_id=13496` 执行源资产登记：
- 确认报告 markdown 字节哈希与契约给定值一致（`sha256:e4fbd73df939124daad974547c532a55e3e3b83301a21c662217ed9688d966e5`）
- 从报告原文中识别并列出 15 项可解析附件/工件（4 源码 + 1 测试 + 1 基准运行器 + 2 数据工件 + 7 结果图）
- 生成 `asset_manifest.json` 并封装为 `kf_result.v1` 信封
- claims 数组为空（01-asset-registration 工序不执行知识抽取，符合契约）

## ② 怎么做的（步骤/工具/关键设置）

1. **获取报告**：通过 `POST /api/v1/auth/login` 获取 Bearer token，再 `GET /api/v1/tensor/reports/13496` 取 `markdown` 字段（10640 字符）
2. **哈希校验**：`hashlib.sha256(md.encode()).hexdigest()` 计算结果与契约 `source_hash` 逐位比对 → **MATCH**
3. **资产识别**：逐段扫描报告原文 §2（方法）、§4（结果图）、§7（可复现与审计链），提取所有带路径引用的文件
4. **清单构建**：按 asset 类型分组（source_code/tests/benchmarks/data_artifacts/figures），每项附 asset_id、path、description、section_ref
5. **信封封装**：按 `schemas/kf_result.v1.schema.json` 组装 package_id/task_type/report_id/provenance/outputs/claims
6. **JSON 校验**：Python `json.load` + 正则校验所有 pattern 字段

## ③ 产出物清单

| 输出文件 | 要点 |
|---|---|
| `artifacts/asset_manifest.json` | 15 项资产清单，分 5 类，每项含 asset_id/path/description/section_ref |
| `work/kf_result_wp-13496-01.json` | kf_result.v1 信封，含 provenance（source_hash 已验证）+ outputs（asset_manifest.json 内容）+ claims=[] |

## ④ 证据定位表

| claim/字段 | 原文引文片段 | 定位 |
|---|---|---|
| source_hash | `sha256:e4fbd73df939124daad974547c532a55e3e3b83301a21c662217ed9688d966e5` | 契约 input.source_hash；API 返回 markdown 经 sha256 计算确认 |
| 源码 constitutive.py | `src/tensorphysics/fem_elastoplastic/{constitutive,axisym,thick_cylinder,verification}.py` | §7 可复现与审计链 |
| 测试文件 | `tests/test_fem_elastoplastic_j2.py`（18 用例，9.1 s 全绿） | §7 可复现与审计链 |
| 运行器 | `benchmarks/elastoplastic_j2/run_p447w2_n04.py`（33.9 s） | 报告首段 + §7 |
| results.json | `artifacts/j2_elastoplastic/results.json` | §7 可复现与审计链 |
| provenance.json | `artifacts/j2_elastoplastic/provenance.json`（commit `5c273c8b2789`） | §7 可复现与审计链 |
| 7 张结果图 | `artifacts/j2_elastoplastic/fig_*.png`（每图 sha256 前缀见 §4） | §4 结果图 |

## ⑤ 注意点与局限

- **零手抄**：所有资产路径/描述均逐字引自报告原文 §2/§4/§7，未凭记忆重述
- **claims 为空**：01-asset-registration 工序契约不要求知识抽取，claims=[] 为合法完整结果
- **未验证资产物理存在**：本工序仅登记报告中声明的资产路径，未检查文件是否实际存在于仓库中（属后续工序职责）
- **sha256 前缀**：图中 sha256 仅记录原文给出的前缀（16 字符），完整哈希需从实际文件计算
- **未改动上游**：仅读取 report_id=13496，未读/写/覆盖其它 report_id

## ⑥ 自检（逐条对照 acceptance）

| 验收项 | 状态 | 说明 |
|---|---|---|
| valid_json | ✅ | 双端 json.load 通过 |
| schema_pass | ✅ | 所有 required 字段存在，pattern 校验通过 |
| source_locator_resolvable | ✅ | 所有 section_ref 指向报告原文 §2/§4/§7 可定位段落 |
| source_hash_matches | ✅ | 计算哈希 = e4fbd73df939124daad974547c532a55e3e3b83301a21c662217ed9688d966e5 |
| no_duplicate_ids | ✅ | 15 个 asset_id 全部唯一 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=[]（空数组，合法） |

**结论：全部 acceptance 项通过，无 honest-FAIL。**

## 复跑命令

```bash
cd /root/tp-agent/work/m15762
python3 work/verify_and_register.py
```

```json
{
  "package_id": "wp-13496-01",
  "task_type": "01-asset-registration",
  "report_id": "13496",
  "provenance": {
    "source_hash": "sha256:e4fbd73df939124daad974547c532a55e3e3b83301a21c662217ed9688d966e5",
    "source_field": "markdown",
    "producer": "agent/m15762",
    "emitted_at": "2026-11-12T02:27:00Z",
    "notes": "Asset registration for report 13496: FEM elastoplastic J2 flow verification (3 cases + GCI). Hash verified against platform API response."
  },
  "outputs": {
    "asset_manifest.json": {
      "report_id": "13496",
      "source_uri": "tensor://reports/13496",
      "source_hash": "sha256:e4fbd73df939124daad974547c532a55e3e3b83301a21c662217ed9688d966e5",
      "source_field": "markdown",
      "title": "p447w2-n04 FEM 弹塑性 J2 流动验证三算例：单轴硬化 2e-16 / 纯剪屈服 0% / 厚壁筒 r_p ≤0.14%（n=16）+ GCI ≤1.1%",
      "scenario_key": "structural_elastoplastic_j2_fem_verification",
      "assets": {
        "source_code": [
          {
            "asset_id": "src-constitutive",
            "path": "src/tensorphysics/fem_elastoplastic/constitutive.py",
            "description": "J2 flow constitutive kernel with Mandel notation, radial return mapping, consistent tangent",
            "section_ref": "§2 本构核"
          },
          {
            "asset_id": "src-axisym",
            "path": "src/tensorphysics/fem_elastoplastic/axisym.py",
            "description": "Axisymmetric FEM kernel: Q8 serendipity / Q4 elements, assembly, internal pressure loading, Newton solver",
            "section_ref": "§2 轴对称有限元核"
          },
          {
            "asset_id": "src-thick-cylinder",
            "path": "src/tensorphysics/fem_elastoplastic/thick_cylinder.py",
            "description": "Closed-form Lamé/Hill elastoplastic thick cylinder solution with interface radius bisection",
            "section_ref": "§2 闭式参照解"
          },
          {
            "asset_id": "src-verification",
            "path": "src/tensorphysics/fem_elastoplastic/verification.py",
            "description": "Verification runner orchestrating cases A–D",
            "section_ref": "§7 可复现与审计链"
          }
        ],
        "tests": [
          {
            "asset_id": "test-j2-flow",
            "path": "tests/test_fem_elastoplastic_j2.py",
            "description": "18 test cases, 9.1 s all green; includes consistent tangent center-diff check, 1D vs 3D cross-validation, n_axial=1 vs 2 equivalence",
            "section_ref": "§7 可复现与审计链"
          }
        ],
        "benchmarks": [
          {
            "asset_id": "bench-runner",
            "path": "benchmarks/elastoplastic_j2/run_p447w2_n04.py",
            "description": "Benchmark runner: 33.9 s, commit 5c273c8b2789, python 3.11.6 / numpy 2.4.6",
            "section_ref": "§7 可复现与审计链"
          }
        ],
        "data_artifacts": [
          {
            "asset_id": "results-json",
            "path": "artifacts/j2_elastoplastic/results.json",
            "description": "Full criteria results, curves, profiles, figure sha256 hashes",
            "section_ref": "§7 可复现与审计链"
          },
          {
            "asset_id": "provenance-json",
            "path": "artifacts/j2_elastoplastic/provenance.json",
            "description": "Provenance: commit 5c273c8b2789, python 3.11.6, numpy 2.4.6, 2026-11-11T07:09:37Z",
            "section_ref": "§7 可复现与审计链"
          }
        ],
        "figures": [
          {
            "asset_id": "fig-a-uniaxial",
            "path": "artifacts/j2_elastoplastic/fig_a_uniaxial.png",
            "description": "Case A: uniaxial tension hardening curve (numerical vs analytic) and anchor-point relative errors",
            "sha256_prefix": "4578af0384de8ce9",
            "section_ref": "§4 结果图"
          },
          {
            "asset_id": "fig-b-pure-shear",
            "path": "artifacts/j2_elastoplastic/fig_b_pure_shear.png",
            "description": "Case B: pure shear stress-strain curve with von Mises first-yield stress",
            "sha256_prefix": "8ee414e0652e2eed",
            "section_ref": "§4 结果图"
          },
          {
            "asset_id": "fig-d-unloading",
            "path": "artifacts/j2_elastoplastic/fig_d_unloading.png",
            "description": "Case D: loading to 3% axial strain followed by unloading to zero stress",
            "sha256_prefix": "7b34841afb89403e",
            "section_ref": "§4 结果图"
          },
          {
            "asset_id": "fig-c-profiles",
            "path": "artifacts/j2_elastoplastic/fig_c_thick_cylinder_profiles.png",
            "description": "Case C: radial stress distribution, yield-ratio indicator, equivalent plastic strain and axial reaction stress",
            "sha256_prefix": "5d1d646ebcd685fd",
            "section_ref": "§4 结果图"
          },
          {
            "asset_id": "fig-c-cloud",
            "path": "artifacts/j2_elastoplastic/fig_c_eq_stress_cloud.png",
            "description": "Case C: equivalent-stress cloud over the meridian section",
            "sha256_prefix": "274a0c5d78fb5989",
            "section_ref": "§4 结果图"
          },
          {
            "asset_id": "fig-e-convergence",
            "path": "artifacts/j2_elastoplastic/fig_e_mesh_convergence.png",
            "description": "Case E: monotone mesh convergence of interface radius and Roache GCI",
            "sha256_prefix": "3a37db2c2de1496c",
            "section_ref": "§4 结果图"
          },
          {
            "asset_id": "fig-elast-accuracy",
            "path": "artifacts/j2_elastoplastic/fig_elast_element_accuracy.png",
            "description": "Diagnostic: elastic Lamé thick-cylinder stress error of Q4 vs Q8 elements",
            "sha256_prefix": "ee2c5776db5a4b2a",
            "section_ref": "§4 结果图"
          }
        ]
      },
      "asset_counts": {
        "source_code": 4,
        "tests": 1,
        "benchmarks": 1,
        "data_artifacts": 2,
        "figures": 7,
        "total": 15
      },
      "registered_at": "2026-11-12T02:27:00Z",
      "registered_by": "agent/m15762"
    }
  },
  "claims": []
}
```
