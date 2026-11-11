# KE Export — 物理 AI 训练知识导出器

## 概述

`ke/export.py` 提供三件套导出器，将 TensorKnowledge 中的知识对象导出为物理 AI 训练可用的格式：

| 导出类型 | 格式 | 用途 | 硬门 |
|---------|------|------|------|
| `sft` | JSONL (messages) | SFT 训练语料 | 仅 published/reviewed 状态 |
| `eval` | JSONL | 评测基准集 | 容差+来源齐全 |
| `triples` | JSONL | 知识图谱三元组 | 关系类型标注 |

## CLI 用法

```bash
# 导出 SFT 训练语料
python -m ke.cli export <pilot_dir> --kind sft --out <DIR>

# 导出评测集
python -m ke.cli export <pilot_dir> --kind eval --out <DIR>

# 导出知识三元组
python -m ke.cli export <pilot_dir> --kind triples --out <DIR>

# 使用已有数据库
python -m ke.cli export <pilot_dir> --kind sft --out <DIR> --db <path.ke.db>
```

## 输出格式

### SFT 语料 (sft.jsonl)

每行一条训练样本，messages 格式：

```json
{
  "messages": [
    {"role": "system", "content": "You are a scientific knowledge assistant..."},
    {"role": "user", "content": "Claim: ..."},
    {"role": "assistant", "content": "**Evidence Basis:**\n..."}
  ],
  "claim_id": "tkc:oss-lbm:lbmpy-chapman-enskog",
  "epistemic_status": "established",
  "domain": "lattice-Boltzmann-method",
  "provenance_sha256": "abc123..."
}
```

### 评测集 (eval.jsonl)

每行一条评测样本：

```json
{
  "claim_id": "tkc:oss-lbm:lbmpy-chapman-enskog",
  "domain": "lattice-Boltzmann-method",
  "input": {"domain": "...", "system": "...", "conditions": [...]},
  "expected": {"claim_statement": "...", "evidence_count": 1, "evidence_sources": [...]},
  "tolerance": 0.1,
  "tolerance_basis": "assessment_status=unassessed",
  "source_claim_id": "tkc:oss-lbm:lbmpy-chapman-enskog",
  "epistemic_status": "established"
}
```

评测集包含两类条目：
1. **基于 claim 的条目**：从知识包中的 claim+evidence 自动生成
2. **标准 LBM 基准条目**：GAP-LBM-POISEUILLE-2D、GAP-LBM-COUETTE-2D、GAP-LBM-TAYLOR-GREEN、MCMP-CYLINDER-DRAG 等校准工装数据

### 三元组 (triples.jsonl)

每行一条知识关系三元组：

```json
{
  "subject": "tkc:oss-lbm:lbmpy-chapman-enskog",
  "predicate": "supports",
  "object": "tke:oss-lbm:lbmpy-ce-src",
  "claim_id": "tkc:oss-lbm:lbmpy-chapman-enskog",
  "evidence_id": "tke:oss-lbm:lbmpy-ce-src",
  "domain": "lattice-Boltzmann-method",
  "claim_statement": "...",
  "evidence_relation": "supports",
  "evidence_assessment": "unassessed",
  "provenance_sha256": "abc123..."
}
```

谓词类型：`supports`, `refutes`, `derived_from`, `qualifies`, `contextualizes`, `mentions`。

## Manifest 文件

每个导出类型附带 manifest JSON：

```json
{
  "export_type": "sft",
  "generated_at": "2026-11-10T03:45:59Z",
  "upstream_commit": "edbc20a",
  "total_claims": 27,
  "included": 27,
  "excluded": 0,
  "excluded_reasons": {},
  "status_distribution": {"established": 27},
  "domain_distribution": {"lattice-Boltzmann-method": 27}
}
```

## 认识论硬门 (Epistemic Hard Gate)

SFT 导出严格执行认识论状态过滤：

| 状态 | 是否进入训练集 | 说明 |
|------|--------------|------|
| `established` | ✅ | 已建立/已发表 |
| `well-supported` | ✅ | 有充分支持 |
| `contested` | ❌ | 有争议 |
| `not-assessed` | ❌ | 未评估 |
| `draft` | ❌ | 草稿 |

被排除的条目在 manifest 的 `excluded_reasons` 中记录排除原因和数量。

## 此语料训练用途与禁用场景

### ✅ 适用场景

1. **科学领域 SFT 微调**：训练模型理解 LBM 及相关计算流体力学领域的知识主张与证据关系
2. **知识检索增强**：作为 RAG 系统的知识源，提供 claim→evidence→source 的完整溯源链
3. **科学推理评估**：eval 集可用于评估模型对科学主张的证据识别能力
4. **知识图谱构建**：triples 可用于构建/扩展科学知识图谱

### ❌ 禁用场景

1. **直接数值预测**：语料中的 claim 是关于代码实现的描述性主张，不是数值模拟结果。不可用于训练模型直接预测流场、阻力系数等物理量。
2. **工程决策依据**：知识主张的认识论状态为 "established" 仅代表对开源代码的分析结论已确认，不代表该代码在工程应用中的可靠性。工程决策需另行验证。
3. **替代实验/仿真**：语料不包含实验数据或仿真结果，不可替代 CFD 仿真或风洞/水池实验。
4. **跨领域泛化**：当前语料仅覆盖 lattice-Boltzmann-method 领域，不可直接用于其他 CFD 方法（FVM/FEM/SPH 等）的训练，除非有对应领域的知识包。
5. **无溯源使用**：所有训练/评估必须保留 provenance_sha256 溯源链，禁止剥离溯源信息后使用。

## 数据卡 (oss-lbm)

| 指标 | SFT | Eval | Triples |
|------|-----|------|---------|
| 总条目数 | 27 | 31 | 27 |
| 领域分布 | lattice-Boltzmann-method: 27 | lattice-Boltzmann-method: 31 | lattice-Boltzmann-method: 27 |
| 状态分布 | established: 27 | - | - |
| 关系分布 | - | - | supports: 27 |
| 容差分布 | - | 0.03: 2, 0.05: 2, 0.1: 27 | - |
| 上游 commit | edbc20a | edbc20a | edbc20a |

## API 参考

```python
from ke.export import export, export_sft, export_eval, export_triples

# 统一导出
manifest = export(kind="sft", pilot_dir="knowledge/oss-lbm", out_dir="output/")

# 单独导出
from ke import store
conn = store.connect(":memory:")
store.ingest_pilot("knowledge/oss-lbm", conn)
manifest = export_sft(conn, out_dir=Path("output/"))
```
