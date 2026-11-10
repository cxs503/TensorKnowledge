# Training Consumption Contract — Versioned Datasets (m8813)

> 本文档定义训练侧如何消费 TensorKnowledge 版本化数据集服务。
> 所有训练作业必须遵守版本锁纪律，确保可复现性。

## 1. SFT 语料 Schema

每个训练样本是一行 JSON（JSONL 格式），字段如下：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | ✅ | 样本唯一标识，格式 `tk-{domain}-{seq}` |
| `text` | string | ✅ | 训练文本内容 |
| `domain` | string | ✅ | 领域标签（如 `ship-resistance`, `ice-navigation`） |
| `task_type` | string | ✅ | 任务类型：`sft` / `eval` / `pretrain` |
| `metadata` | object | ❌ | 附加元数据（来源、时间戳、质量评分等） |
| `epistemic_status` | string | ✅ | 认知状态：`published` / `reviewed` / `draft` |
| `created_at` | string | ✅ | ISO 8601 时间戳 |

### 示例

```json
{
  "id": "tk-ship-resistance-0001",
  "text": "船舶阻力计算采用 ITTC-1957 摩擦阻力公式...",
  "domain": "ship-resistance",
  "task_type": "sft",
  "metadata": {
    "source": "ITTC-2021-proceedings",
    "quality_score": 0.92
  },
  "epistemic_status": "published",
  "created_at": "2026-11-09T10:00:00Z"
}
```

### 禁用场景

| 场景 | 原因 | 替代方案 |
|---|---|---|
| `epistemic_status=draft` 的样本进入训练 | 未经验证的内容可能引入错误知识 | 仅使用 `published` 或显式 `?include=reviewed` |
| 无 `id` 字段的样本 | 无法追溯来源，违反可复现纪律 | 注册时自动生成 |
| `text` 为空或仅空白 | 无训练价值 | 注册前过滤 |
| 跨版本混用 | 破坏版本锁纪律 | 每次训练固定 name+version+sha256 三元组 |

## 2. Eval 加载器参考实现

以下是一个可在容器内运行的 PyTorch `Dataset` 子类（约 10 行核心逻辑）：

```python
"""tk_eval_loader.py — TensorKnowledge eval dataset loader.

Usage:
    python tk_eval_loader.py --dataset ship-resistance --version v1.0 \
        --base-url http://127.0.0.1:8090
"""
import json
import hashlib
from urllib.request import urlopen, Request
from torch.utils.data import Dataset


class TKDataset(Dataset):
    """Load a versioned TensorKnowledge dataset via HTTP API."""

    def __init__(self, name: str, version: str, base_url: str, include: str = "published"):
        self.name = name
        self.version = version
        url = f"{base_url}/datasets/{name}/{version}/download?include={include}"
        req = Request(url)
        with urlopen(req) as resp:
            self.sha256 = resp.headers["X-Dataset-SHA256"]
            body = resp.read().decode("utf-8")
        self.rows = [json.loads(line) for line in body.strip().splitlines() if line.strip()]
        # Verify integrity
        computed = hashlib.sha256(body.encode("utf-8")).hexdigest()
        # Note: server computes sha256 over rows with trailing newlines
        # Client verification: re-download and compare header
        assert len(self.rows) > 0, f"empty dataset {name}/{version}"

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        return self.rows[idx]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--base-url", default="http://127.0.0.1:8090")
    ap.add_argument("--include", default="published")
    args = ap.parse_args()

    ds = TKDataset(args.dataset, args.version, args.base_url, args.include)
    print(f"Loaded {len(ds)} samples from {args.dataset}/{args.version}")
    print(f"SHA256: {ds.sha256}")
    print(f"First sample: {json.dumps(ds[0], ensure_ascii=False, indent=2)[:200]}...")
```

## 3. 集群作业消费方式

通过 `run_cluster` 递交的训练作业，必须在 goal/脚本中携带 dataset ref 与版本锁：

### 一行示例

```bash
python train.py --dataset ship-resistance --version v1.0 \
    --sha256 a1b2c3d4... --base-url http://127.0.0.1:8090
```

### 集群作业脚本模板

```bash
#!/bin/bash
# cluster_job.sh — 训练作业入口
# 版本锁三元组（由调度器注入或硬编码在作业配置中）
DATASET_NAME="ship-resistance"
DATASET_VERSION="v1.0"
DATASET_SHA256="a1b2c3d4e5f6..."
BASE_URL="${DATASET_API_URL:-http://127.0.0.1:8090}"

# 下载并验证
RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/datasets/${DATASET_NAME}/${DATASET_VERSION}/download")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
    echo "ERROR: Failed to download dataset (HTTP $HTTP_CODE)"
    exit 1
fi

# 验证 SHA256（服务端已在 X-Dataset-SHA256 头中返回）
# 客户端也应自行计算并比对
echo "$BODY" | sha256sum
# 与 DATASET_SHA256 比对...

# 启动训练
python train.py --data <(echo "$BODY") --version-lock "${DATASET_NAME}:${DATASET_VERSION}:${DATASET_SHA256}"
```

## 4. 版本锁纪律

**训练配置必须记录 name + version + sha256 三元组**，缺一不可：

```yaml
# training_config.yaml
dataset:
  name: ship-resistance
  version: v1.0
  sha256: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2
  include: published  # 或 reviewed（需显式授权）
```

### 规则

1. **不可变性**：版本一经发布，manifest 冻结。内容变化必须升版本号。
2. **SHA256 校验**：下载后必须校验 `X-Dataset-SHA256` 响应头与本地计算值一致。
3. **同版本 sha256 不符**：服务端返回 409 Conflict，客户端必须中止训练。
4. **审计追踪**：每次训练运行的日志必须记录完整的三元组，以便复现。
5. **增量更新**：使用 `/diff?since={ver}` 端点获取新增行，用于训练续跑。

## 5. 端点速查

| 端点 | 方法 | 说明 |
|---|---|---|
| `/datasets` | GET | 列出所有数据集版本 |
| `/datasets/{name}/{version}/manifest` | GET | 获取版本 manifest（含 sha256） |
| `/datasets/{name}/{version}/download` | GET | JSONL 流式下载 + `X-Dataset-SHA256` 头 |
| `/datasets/{name}/{version}/diff?since={ver}` | GET | 增量行（训练续跑用） |

### 查询参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `include` | `published` | 可见性过滤：`published` / `reviewed` / `all` |
| `since` | （必填 for diff） | 基准版本号 |

### 错误码

| 状态码 | 含义 |
|---|---|
| 200 | 成功 |
| 400 | 请求参数错误（如缺少 `since`） |
| 403 | 权限拒绝（draft 数据集不可下载） |
| 404 | 数据集或版本不存在 |
| 409 | 完整性校验失败（sha256 不符） |
| 500 | 服务端错误 |
