# 训练出口闸门 train_gate（FEAT-SIM-DATAHOUSE · 子件4）

> 语义来源：owner 令「与多模态模型训练工作相结合」+ TK 定位令既定语义
> **published / reviewed 才进训练集**。本文件是闸门表、API、held-out 切分与
> 数据集 v1.0 接线的契约说明；可执行验收见 `artifacts/feat-sim-datahouse/ACCEPTANCE.md`。

## 0. 要防的两病

| 病 | 表现 | 本实现的止血点 |
|---|---|---|
| 未审数据泄入训练 | 训练侧能下到 `draft` / 未审版本的 JSONL | `train_gate.review_level='none'` → 下载端点 403；`include=all` 在边缘直接 403（旧泄漏口已封） |
| 评测集混入训练集（泄漏） | held-out 基准案出现在训练行里 | 名单 `benchmarks/heldout/heldout_cases_v1.json`（≥15 案）+ builder 入库前强制排除 + manifest 声明 + 入库后复核 |

## 1. 表结构

### `train_gate`（一版本一行，训练出口决定）

| 列 | 含义 |
|---|---|
| `dataset_id`, `version` | 主键 |
| `review_level` | 审级：`none` \| `reviewed` \| `published` |
| `reviewer` | 审定人（定级行必填，且 ≠ `producer`） |
| `evidence_chain` | 证据链（定级行必填，JSON 文本或单条 ref，至少 1 条） |
| `producer` | 产出方（数据流水线），用于四眼原则的基数 |
| `admitted_at` | 入训练集时间：首次到达 `reviewed`/`published` 时打点，撤销后置空 |
| `created_at`, `updated_at` | 行生命周期 |

### `train_gate_audit`（只增审计）

`register` / `transition` / `revoke` 每次动作一行：`from_level → to_level`、
审定人、证据链、actor、note、时间。触发器禁止 `UPDATE`/`DELETE`。

### `train_gate_token`（内部流转令牌）

只有 `transition()` / `revoke()` 在同一事务里先插令牌，`train_gate` 的 UPDATE
才被放行。详见 §4 红队。

## 2. 三态流转

```
none ──review(reviewer≠producer, 证据链≥1)──► reviewed ──publish(另一名审定人)──► published
  ▲                                             │                                   │
  └──────────────── revoke(需 note，留痕) ───────┴───────────────────────────────────┘
```

* 跨级跳（`none → published`）拒绝：422。
* 重复流转（`reviewed → reviewed`）拒绝：422。
* 自审（`reviewer == producer`）拒绝：422。
* 同一人 review 后再 publish 拒绝（四眼）：422。
* 撤销回落 `none`，训练侧立即再次 403。

## 3. API（`ke/train_gate_api.py`）

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/v1/knowledge/train-gate` | GET | 闸门表 + 审级计数 + 审计对账告警；过滤参数 `dataset_id` / `version` / `level` / `visible` |
| `/api/v1/knowledge/train-gate/audit` | GET | 审计行（append-only，按 `audit_id` 升序） |
| `/api/v1/knowledge/train-gate` | POST | 登记（`to_level=none` 且行不存在）或推进审级；需 `Authorization: Bearer $KE_API_TOKEN` |
| `/api/v1/knowledge/held-out` | GET | held-out 名单（id / sha256 / 案表） |

写面在 `KE_API_TOKEN` 未配置时 503（不开放匿名写），token 不符 401。
独立进程入口：`python -m uvicorn ke.train_gate_api:standalone_app --port 8022`
（`KE_TRAIN_GATE_DB` 指定库文件）。挂载进 KE 主服务由 `ke/api.py` 完成。

POST 示例（推进到 reviewed）：

```json
{"dataset_id":"FEAT-SIM-DATAHOUSE","version":"v1.0","to_level":"reviewed",
 "reviewer":"rev-zhang",
 "evidence_chain":["tkc:sim-datahouse:review-form-v1.0","tke:sim-datahouse:geometry-cb-check-v1.0"],
 "actor":"rev-zhang","note":"几何 Cb/L/B 复核 + 样本抽检"}
```

## 4. 红队：伪造审级直改库

数据库层（不是应用层）拦四条路，逐条有测试（`tests/test_train_gate.py`）：

| 攻击 | 拦截者 | 报错 |
|---|---|---|
| `UPDATE train_gate SET review_level='published'` | `trg_tg_update_guard`（无令牌） | `train_gate: unguarded UPDATE (forged grade/reviewer)` |
| 已定级行偷换 `reviewer`（不改审级） | 同上（触发器覆盖任何列变更） | 同上 |
| 插入 `reviewed` 行但缺审定人/证据链 | `CHECK` + `trg_tg_insert_guard` | `IntegrityError` |
| 改/删审计行 | `trg_tg_audit_no_update` / `_no_delete` | `train_gate_audit is append-only` |
| 删掉已定级 gate 行 | `trg_tg_no_delete_graded` | `graded row cannot be deleted (use revoke)` |
| 绕过 API 直插行（无审计） | `integrity_alerts()` 对账告警 | `{"kind":"missing_audit", …}` |

**局限（诚实声明）**：以上是**库内防伪**，防的是 ORM/脚本层「顺手改一行」和半截伪造；
对拥有文件写权限并愿意重建整张表 + 触发器的人（例如 `PRAGMA writable_schema`
或直接改 .sqlite 二进制），SQLite 自身给不出密码学保证。要防这一类，需把审计行
外送到只增存储或对 `(train_gate, train_gate_audit)` 做签名/hash 链——本子件未做，
列为后续项（见 `artifacts/feat-sim-datahouse/ACCEPTANCE.md` §7 之后的说明）。

## 5. held-out 评测切分约定

* 名单：`benchmarks/heldout/heldout_cases_v1.json`（`schema=tk-heldout/1`，
  当前 21 案，覆盖阻力/推进/耐波/操纵/稳性/结构/振动噪声/绿色航行/冰区）。
* 判定：行内 `case_id` / `benchmark_id` / `benchmark_name` / `source_case`
  命中名单，或 `split ∈ {held-out, held_out, heldout, test}` → 排除。
* 强制点：`ke.dataset_builder.build_dataset()` 在 `store.register()` **之前**过滤，
  入库后再复核（`verify_no_leak`），行数必须对得上；没有「跳过排除」开关。
* manifest 声明块（冻结在 `manifest_json`，`promote()` 后仍在）：

```json
"held_out": {
  "policy": "held-out cases never enter training rows",
  "list_id": "ship-perf-heldout-v1", "list_version": "1.0.0",
  "list_sha256": "e95503…", "case_count": 21,
  "source_rows": 26, "training_rows": 18, "excluded_count": 8,
  "excluded": ["HO-MAN-001", "HO-PRO-002", "…"],
  "enforced_by": "ke.dataset_builder.build_dataset"
}
```

* 名单改动 = `list_sha256` 变化 → 与旧 manifest 对账即可发现「同一版本号换了切分」。

## 6. 训练侧消费

* 下载端点 `GET /datasets/{name}/{version}/download`：
  * `review_level='none'` → **403**（无论 include 取何值）；
  * `reviewed` → 只认 `include=reviewed`（默认 `published` 仍 403）；
  * `published` → 默认即可下载；
  * `include=all` → **403**（边缘拒绝，永不下传）。
  * 成功响应带 `X-Train-Gate-Level` 头，训练日志可直接落审级。
* `ke/tk_eval_loader.py` 把 403 转成 `PermissionError`：训练侧必须硬失败，
  不许换个 include 重试。

## 7. 已知边界

1. `train_gate` 只约束**通过 TK 下载端点**的消费；训练作业若自行从别处拷 JSONL，
   闸门管不到——纪律要求训练配置记录 `name+version+sha256+gate level`。
2. 数据集自身审级（`datasets.status`）与闸门审级是**两道独立门**，都要过；
   这样「数据集内部 draft」不会被闸门一句 reviewed 洗白。
3. SQLite 单写者：跨进程并发写 gate 表靠 `busy_timeout=5000` 串行化，量级上够用。
4. 审计外送/签名链未做（见 §4 局限）。
## 8. 上线开关与匹配语义

* `KE_TRAIN_GATE_STRICT=1`（`make_server()` 读取）→ **fail-closed**：没有 `train_gate`
  行的数据集版本一律 403，即使它自行声明 `datasets.status='published'`。
  默认（未设）= 兼容闸门上线前登记的历史数据集，由 `datasets.status` 自行把关。
  生产接训练出口时建议打开，验收见 `runs/feat-sim-datahouse/ACCEPTANCE.md`。
* `dataset_id` / `version` **精确匹配（大小写敏感）**：`train_gate` 的行必须与
  `datasets.name/version` 完全一致；`ke.dataset_builder.build_dataset()` 用同一个
  名字登记两边，构造上不会错位。手工登记时务必原样复制。
* `include` 只接受 `published` / `reviewed`；其他值（含历史上的 `all`）在 HTTP
  边缘 403，不下传到存储层。
