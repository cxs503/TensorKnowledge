# 夹具来源与找回路径（ke-pilot）

本目录是 **m8554 认知试点包**的字节级拷贝，作为 KE 原型测试的冻结夹具。

## 为什么在这里

- 试点包的原始位置是 `platform-test/epistemic-benchmark/pilots/m8554/`，
  由提交 `ba59c4e`（分支 `agent/m8554`）加入；**该分支从未合入 `main`**，
  因此 `main` 上 `tests/test_ke_proto.py` 的 15 个原型测试全部因
  `FileNotFoundError` 变红（见 `docs/ops/filter-audit.md` 的审计条目）。
- m8800 的 KE 双后端改造需要这份地面真值，故按「零手抄」原则从 git 对象直接取出，
  不重写、不改内容，仅做一次搬家。

## 怎么取出来的（可复现）

```bash
git archive ba59c4e platform-test/epistemic-benchmark/pilots/m8554 \
  | tar -x -C /tmp
cp -r /tmp/platform-test/epistemic-benchmark/pilots/m8554 tests/fixtures/ke-pilot
```

唯一改动：`validate_pilot.py` 里定位仓库根的两行改成「向上找含 `schemas/` 的祖先目录」，
使包在新位置仍能自校验（语义不变，校验项一字未动）。

## 校验

```bash
python tests/fixtures/ke-pilot/validate_pilot.py      # -> ALL PASS
python -m pytest -q tests/test_ke_proto.py            # -> 双后端全绿
```

## 找回路径（若日后需要回到原位置）

```bash
git checkout origin/agent/m8554 -- platform-test/epistemic-benchmark/pilots/m8554
```

注意：推送门禁会把路径中含 `/<mission-id>/` 段的文件判为他单产物而滤除
（`tp_pusher.py` 的 `[他单]` 规则），所以**不要**把本夹具放回带 `m8xxx/` 段的路径，
否则会在推送时被静默丢弃、导致 `main` 再次变红。