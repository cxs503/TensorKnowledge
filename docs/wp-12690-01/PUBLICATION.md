# wp-12690-01 发布记录（含一次重复发布的事故说明）

> 本文件是**审计留痕**，不是工作包产物；权威产物是 `docs/kf_result_wp-12690-01.md` 与其内唯一 JSON 块。

## 权威发布件

| 字段 | 值 |
|---|---|
| 报告 id | **14863** |
| 标题 | `KF-RESULT wp-12690-01` |
| mission_id | 15752 |
| tags | `kf-wp:wp-12690-01` 等（见报告） |
| 源报告 | 12690（sha256 `c7ffa8c80de7dacf0f20da21051c644731ee7e82649101b0922b3830796d9d28`） |
| markdown | 与 `docs/kf_result_wp-12690-01.md` 逐字节相同（`scripts/kf_publish_12690.py` 的幂等门自检 `markdown identical: True`） |

## 重复发布事故（如实登记）

- 首次发布 **14859** 后，我修改了报告正文的两处：①`repro_cmd` 增加服务端复核步骤
  （`kf_check_published_12690.py`）；②产出物清单增加 `published_check.json` 与源 markdown 镜像两行。
  重新生成后**又发布了一次**，得到 **14863**。
- 平台 **没有** 报告更新/删除端点：`PUT/PATCH/DELETE /api/v1/tensor/reports/14859` 均返回
  **405 Method Not Allowed**（2026-11-12 实测），因此无法回滚 14859。
- 于是 14859 成为**过期副本**：内容与 14863 的差异仅在上述两处（不涉及任何数字、引文、
  哈希或验收结论）。**以 14863 为准**。
- 已加结构性防复发：`scripts/kf_publish_12690.py` 增加了幂等门——发布前查同标题报告，
  若已存在且 markdown 相同则 `SKIP publish`（返回 0），内容不同则拒绝并提示需 `--force`。
  这样后续复跑不会再产生第二个同标题报告。

## 可复现性（字节稳定）

`provenance.emitted_at` 首次运行写入后即被复用（`_emitted_at()` 先读 `docs/` 镜像、再读 `runs/` 副本），
所以现场重跑会**逐字节**复现已发布的信封与报告正文；`kf_check_published_12690.py` 的
`block_equals_shipped_envelope` 就是这条性质的机器判据（当前 PASS）。

## 已知小瑕疵（不影响验收）

- `A15`（figure_declaration）的 `resolution_check` 写的是"markdown 中 `![](...)`/`<img>` 命中数=0"
  而 `result=resolved`：前者服务于 A22–A26 的 `declared_absent` 结论，后者指"该声明行本身可在正文定位"。
  两个语义挤在同一个字段里，读起来易混；已在此说明，未为改一个元数据字段而再发布第三份同标题报告。

## 复核方式

- 服务端复核：`python3 scripts/kf_check_published_12690.py`（默认 id=14863，
  校验唯一 json 块、与信封等价、平台重算哈希一致、claims 空、无 verified 标签、tag/title 正确）。
- 现场全链复跑：见 `docs/kf_result_wp-12690-01.md` 的「复跑命令」。