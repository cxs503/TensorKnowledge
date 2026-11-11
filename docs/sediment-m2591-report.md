# m2591 知识沉淀：Wigley 前进波阻「压力路径」honest-FAIL 定谳（四契约提取）

**来源**：mission 2591（TensorBEM，branch `agent/m2591`，model deepseek-v4-flash，状态 succeeded）。
**本单**：mission 8830（TensorKnowledge），task_key `tk-sediment-m2591`，产物 `knowledge/sediment/m2591/`。
**sha 解析**：平台 `source_head_sha` 为 PENDING；按源单 result 报告 Appendix「Commit: a9f77b1 (branch agent/m2591)」解析为
`a9f77b14d4d835ab5ecff3ba093dc504a1c04e6c`，并在本地 TensorBEM 对象库核实 `git cat-file -t a9f77b1` → commit（未编造）。

## ① 案例介绍

Wigley 数学船型前进波阻的**两条路径之争**：Kochin 远场（一阶薄船/Michell）路径已对收敛求积校核，压力路径
`wave_resistance_pressure` 是它的「近场」对照，两路径相差 103–284 %、压力路径处处为负，源仓以 honest-FAIL 挂着，
并把成因归给「薄船近似在 B/L=0.1 下仅勉强成立」。

| 参数 | 值 |
|---|---|
| L | 2.0 m |
| B | 0.2 m（B/L = 0.10） |
| T | 0.125 m（T/L = 0.0625） |
| 船型 | `y = (B/2)(1-(2x/L)²)(1-(z/T)²)`，Cb = 4/9 ≈ 0.4444 |
| ρ / g | 1025 kg/m³ / 9.80665 m/s² |
| Fr | 0.20, 0.25, 0.30, 0.35, 0.40 |
| 参考 | Kochin 远场路径（对收敛求积校核到 2.6e−5） |
| 网格 | 8×4（128 面板）… 64×32（8192 面板） |

（几何校验：B/L=0.10、T/L=0.0625、Cb=0.4444 与解析式一致，与源工件 `case` 字典逐项核对。）

## ② 怎么做的

本单是**知识沉淀提取**，不是重做物理；方法分两侧，互相独立：

1. **知识侧（四契约）**：从 `git show a9f77b1:<path>` 里按行号切出**逐字引句**（不手抄），生成 5 × claim /
   7 × evidence / 5 × provenance（PROV-O），`epistemic_status=draft`、`assessment_status=unassessed`，
   **不产出 review-event**（生产者不自审，review_status=pending 交独立席位）。
2. **数值侧（复证）**：把 `git archive a9f77b1` 解到干净目录，重跑
   `PYTHONPATH=src python3 -m tensorbem.benchmarks.wigley_pressure_audit` 与
   `PYTHONPATH=src python3 -m pytest tests/test_wigley_pressure_path_audit.py -q`。
3. **校验链**：`verify_sediment.py`（7 项检查：jsonschema / 双向交叉引用 / 逐字引句@sha / 文件 sha256 /
   生产者契约 / INDEX.md 一致性）。

## ③ 计算结果（程序化注入，零手抄）

重跑结果与源单提交件**逐字节一致**：`results.json` IDENTICAL、`summary.md` IDENTICAL（`diff -q` 无输出）；
测试 **13 passed in 29.89 s**。

| 检查 | 实测 | 基准 | 误差 | 是否 <3 % |
|---|---|---|---|---|
| 截断波数扫掠 k_max/k0 = 5…160（Fr=0.30, 512 面板） | R_W = −1.5807e−02 … −5.2744e−02 N，极差 37.6 % | Kochin 9.8341e−02 N | 最好点 ratio −0.1607 → 116.1 %；最差 153.6 % | **否** |
| 网格阶梯 128 → 8192 面板（Fr=0.30） | R_W = −4.6375e−02 → −2.7121e−03 N（趋 0） | Kochin 9.8341e−02 N | rel. diff 1.472 → 1.028（趋 1） | **否**（102.8 % @8192） |
| 求积节点 32 → 512（Fr=0.30） | 128 节点起锁定 −2.0300e−02 N（七位一致） | Kochin 9.8341e−02 N | 恒 120.6 % | **否** |
| 自由面残差（Fr=0.20…0.40） | 0.7528 … 0.9299（印刷约定 1.000） | 0（应为自由波） | O(1) 违约；色散曲线上节点数 0 | **否** |

## ④ 结果图

三面板（数据全部来自重跑的 `results.json`）：
**(a)** 网格加密使相对 Kochin 的差趋向 1（红线=3 % 判据），收敛方向指向 0 而非参考值；
**(b)** 截断波数扫掠无收敛趋势，摆幅 37.6 %；**(c)** 求积已收敛却仍偏 120.6 % —— 求积细化救不了被积函数错。

## ⑤ 注意点 / 局限

* **「收敛」不等于「收敛到正确答案」**：求积七位收敛同时 120.6 % 偏移，是本案例最有迁移价值的判据教训；
  检出不变量应取支配方程残差，而非求积分辨率。
* **网格加密趋向 0 是指纹**：离散误差随加密相对参考值趋 0，本例趋 1（值本身趋 0），二者可判别。
* **ratio 散布先于常数因子猜测**：Fr 上 ratio −0.774…−0.197（散布 0.577），排除「乘个常数就能对上」。
* **局限**：只审计 Wigley 前进速度模块；Rankine/Dawson 独立近场路径与文献 Cw（参考面积须声明）仍属未实现/UNSUPPORTED。
* **未复跑项**：源单记录的回归子集 59 passed / 5 failed 未在本单复跑（那 5 条在未改动 HEAD 上同样失败）。
* **schema 增补**：`claim-record.schema.json` 的 `epistemic_status` 枚举原无「生产者未评审」态，本单**最小增补** `draft`
  （纯增量、未删除任何既有值，已在 INDEX.md 写明理由）以满足「draft + 过 jsonschema」双约束。

## ⑥ 误差判定

逐项回答「是否 <3 %」：截断扫掠 **否**（最好 116.1 %）、网格阶梯 **否**（102.8 %）、求积节点 **否**（120.6 %）、
自由面残差 **否**（O(1)，非百分比误差）。唯一 <3 % 的量是**参考路径自身**的求积自洽性（2.6e−5），它不是本节被审对象。
定谳：该 honest-FAIL **未被修复**，被**诊断**并降级为诊断工具；「两路径 5 % 吻合」判据在一阶薄船理论内不可达，应撤销。