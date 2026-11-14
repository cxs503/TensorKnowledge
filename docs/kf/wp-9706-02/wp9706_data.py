"""Data tables for work package wp-9706-02 (report 9706, process 02).

Separated from build.py so the declarative part (which source line is evidence
for which judgement) can be reviewed without reading the generator logic.

Every anchor below occurs **exactly once** in the source markdown; build.py
slices the whole surrounding line as the quote, so no quote is ever re-typed.
"""

PACKAGE_ID = "wp-9706-02"
TASK_TYPE = "02-classification-parse"
REPORT_ID = "9706"
SOURCE_URI = "tensor://reports/9706"
SOURCE_FIELD = "markdown"
EXPECTED_HASH = "sha256:7d0e024b8630cd3390f5efc0c3f5abfb467e85a869c78126bbb210a1a2d13534"
EXPECTED_CHARS = 12546
SOURCE_TITLE = ("IN145-N04 DP 系统能力评估：凸推力分配 × 环境力平衡 × 操作包线"
                "（PSV-6450，判据全过）")
SCENARIO_KEY = "dp_capability"
MISSION_ID = "19803"

# (locator id, unique anchor inside the source line, what that line evidences)
ANCHORS = [
    ("L01", "# IN145-N04 动力定位（DP）系统能力评估", "报告标题行（类型/主题首个识别信号）"),
    ("L02", "本文把", "摘要：三个物理环节 + 判据全过的总陈述"),
    ("L03", "τ_req = −F_env", "§2 计算流水线（环境力 → 分配 → 包线）"),
    ("L04", "| 要素 | 模型 | 分级 | 不确定度（声明） |", "§1 证据分级表头（含声明不确定度列）"),
    ("L05", "二阶平均漂移力", "§1 波浪漂移力谱积分行：控制方程型信号"),
    ("L06", "推力器-船体/推力器-推力器干扰 5%", "§1 推力折减行：参数化假设 + 敏感性"),
    ("L07", "因此写成凸二阶锥问题（SOCP）", "摘要：分配写成凸 SOCP"),
    ("L08", "最大迭代从 40 降到 10 量级", "§5 踩坑 2：迭代/停滞退出（收敛讨论）"),
    ("L09", "| 关键量 | 基准（clean-room / 解析） | 本次结果 | 相对偏差 | 是否 < 3% |",
     "§6 误差判定表头：比较对 + <3% 判据"),
    ("L10", "最差扇区风速 vs DNV/IMCA 能力图", "§6 honest-FAIL 行：唯一超差、无定量基准"),
    ("L11", "按 honest-FAIL 纪律如实登记，不粉饰、不覆盖", "§6 结论：honest-FAIL 纪律"),
    ("L12", "python -m pytest tests/test_dp_capability.py -q", "§7 复跑命令（测试）"),
    ("L13", "curl -s -X POST localhost:8001/api/v1/dynamic-positioning/capability", "§7 端点（API 信号）"),
    ("L14", "**审计链**：表 10 给出每个工件的 sha256", "§7 审计链陈述"),
    ("L15", "**局限 1（绝对幅值偏乐观）**", "§5 局限 1：绝对幅值偏乐观"),
    ("L16", "**适用范围**：准静态能力评估", "§5 适用范围"),
    ("L17", "最差扇区 **59.41 kn @ 75°**", "表 5 最差扇区（24 航向口径）"),
    ("L18", "| baseline（interaction 0.95, 1.0 kn, ×1.0） |", "表 8 baseline 行（61.88 kn @ 60°）"),
    ("L19", "判据④（平均/最差航向口径，限值 30%）", "表 6 判据④汇总与口径"),
    ("L20", "| `artifacts/dp_capability/dp_capability_report.json` |", "表 10 工件行：sha256 仅前 16 位"),
    ("L21", "几何先校验后计算（平台纪律：先证 Cb/L/B）", "§1 几何先校验"),
    ("L22", "不是某一实船的图纸数据", "§1 参数化参考船声明"),
    ("L23", "## 3 计算结果", "§3 标题"),
    ("L24", "## 1 案例介绍（物理背景 / 几何 / 参数）", "§1 标题"),
    ("L25", "## 2 怎么做的（方法 / 流程 / 关键设置 / 工具链）", "§2 标题"),
    ("L26", "## 4 结果图", "§4 标题"),
    ("L27", "## 5 注意点（踩过的坑 / 局限 / 适用范围）", "§5 标题"),
    ("L28", "## 6 误差判定", "§6 标题"),
    ("L29", "## 7 复现 / 验收命令", "§7 标题"),
    ("L30", "### 表 7 风-流边界", "表 7 标题（风-流扫掠）"),
    ("L31", "| QP 迭代（最大 / 平均） |", "表 4 迭代行"),
    ("L32", "（1）**环境力**", "摘要：环境力三分解"),
    ("L33", "| 环境力-推力平衡残差（10 工况点） |", "§6 行：力平衡残差 vs 基准 0"),
    ("L34", "DNV/IMCA 定性一致性核查", "表 5 后定性一致性核查"),
    ("L35", "### 表 8 关键假设敏感性", "表 8 标题（敏感性变体）"),
    ("L36", "### 表 5 判据③：操作包线", "表 5 标题（24 航向包线）"),
    ("L37", "### 表 10 工件与审计链（sha256）", "表 10 标题"),
    ("L38", "`artifacts/dp_capability/acceptance.json`", "§7 验收判定文件"),
    ("L39", "44 例，全绿", "测试 44 例全绿（外部仓库）"),
    ("L40", "**测试**：`tests/test_dp_capability.py`（44 例，全绿）", "页首测试行"),
    ("L41", "推力器模型：全回转 w∈R²", "§2 推力器广义力映射"),
    ("L42", "为什么不用", "§2 方法学取舍（第一版启发式废弃）"),
    ("L43", "**局限 2（定性判据不是定量基准）**", "§5 局限 2：无定量基准"),
    ("L44", "**局限 3（漂移力与风系数是近似）**", "§5 局限 3：漂移力/风系数近似"),
    ("L45", "**局限 4（推进器水动力未建模）**", "§5 局限 4：推进器水动力未建模"),
]

# English identify_signals, copied from extraction-skills/registry.json for a
# literal scan (the scan result is reported as-is, including 0 hits).
REGISTRY_SIGNALS = {
    "literature-review": ["related work", "state of the art", "survey", "bibliography"],
    "scientific-computation": ["governing equation", "discretisation", "convergence study",
                               "mesh refinement", "timing table"],
    "algorithm-implementation": ["pseudocode", "complexity", "algorithm block",
                                 "function signature", "O(n"],
    "software-engineering": ["changed files", "commit", "interface", "regression", "API"],
    "technical-proposal": ["proposal", "design", "roadmap", "specification", "plan"],
    "experimental-validation": ["test matrix", "facility", "measurement uncertainty",
                                "validation case", "baseline comparison"],
}

SKILL_BY_TYPE = {
    "literature-review": "xsk-literature-review",
    "scientific-computation": "xsk-scientific-computation",
    "algorithm-implementation": "xsk-algorithm-implementation",
    "software-engineering": "xsk-software-engineering",
    "technical-proposal": "xsk-technical-proposal",
    "experimental-validation": "xsk-experimental-validation",
}

# signal -> (status matched|partial|absent, locator ids, note).  An absent
# signal carries the locator of the section that was *checked*, never a
# fabricated quote.
SIGNAL_JUDGEMENT = {
    "experimental-validation": {
        "test matrix": ("matched", ["L36", "L35", "L30", "L19"],
                        "24 航向包线 + 5 个失效工况 + 7 个敏感性变体 + 4 航向×7 流速扫掠"),
        "facility": ("absent", ["L25"], "无物理试验设施；§2 只给数值工具链"),
        "measurement uncertainty": ("partial", ["L04", "L05"],
                                    "给的是模型不确定度声明（±25%/±15%/±30%），不是测量不确定度/覆盖因子"),
        "validation case": ("matched", ["L33", "L09"], "10 个工况点力平衡 vs 基准 0"),
        "baseline comparison": ("matched", ["L09", "L10", "L43"],
                                "§6 逐项 vs 解析/clean-room 基准，无定量基准项已声明"),
    },
    "scientific-computation": {
        "governing equation": ("matched", ["L05", "L03", "L07"],
                               "漂移力谱积分 + τ_req=−F_env + SOCP 形式"),
        "discretisation": ("absent", ["L25"], "准静态求解，无空间/时间离散"),
        "convergence study": ("partial", ["L08", "L31"],
                              "求解器迭代/停滞退出与残差讨论，无网格或时间步收敛研究"),
        "mesh refinement": ("absent", ["L25"], "无网格"),
        "timing table": ("absent", ["L25"], "无耗时表（只有 QP 迭代次数）"),
    },
    "algorithm-implementation": {
        "pseudocode": ("absent", ["L03"], "§2 只有流水线示意，非伪代码"),
        "complexity": ("absent", ["L03"], "无复杂度分析"),
        "algorithm block": ("partial", ["L07", "L41"], "SOCP 形式与推力器映射，无算法块"),
        "function signature": ("absent", ["L25"], "只提模块路径，无函数签名"),
        "O(n": ("absent", ["L03"], "无渐进复杂度符号"),
    },
    "software-engineering": {
        "changed files": ("partial", ["L42"], "提到第一版实现被废弃，无 changed-files 清单"),
        "commit": ("absent", ["L42"], "只说差异在 git 历史里可查，无 commit id"),
        "interface": ("partial", ["L13"], "一个端点 URL，无接口契约"),
        "regression": ("partial", ["L39", "L40"], "44 例测试全绿（外部仓库，不可核验）"),
        "API": ("matched", ["L13"], "给出 /dynamic-positioning/capability 端点"),
    },
    "technical-proposal": {
        "proposal": ("absent", ["L02"], "无待批方案，结果已产生"),
        "design": ("partial", ["L25"], "有方法设计，但服务于已完成的评估"),
        "roadmap": ("absent", ["L02"], "无路线图"),
        "specification": ("partial", ["L09"], "有判据/容差规格（<3%、30%、<50 次）"),
        "plan": ("absent", ["L02"], "无计划"),
    },
    "literature-review": {
        "related work": ("absent", ["L09"], "无相关工作章节；§6 基准是解析式不是文献"),
        "state of the art": ("absent", ["L09"], "无 SOTA 对比"),
        "survey": ("absent", ["L02"], "非综述"),
        "bibliography": ("absent", ["L09"], "全文无参考文献列表"),
    },
}

# (claim id, statement, locator ids)
CLAIMS = [
    ("C01",
     "报告类型判定依据：本文对三个物理环节（环境力 / 推力分配 / 操作包线）给出模型、判据与数值结果，"
     "属数值计算类评估报告，而非文献综述、算法说明或软件变更报告。",
     ["L01", "L02", "L32"]),
    ("C02",
     "最强类型信号之一：§6 以「关键量 / 基准 / 本次结果 / 相对偏差 / 是否 < 3%」逐项构成"
     "「模型值 vs 独立基准」比较对，这是比较对型报告的核心结构。",
     ["L09", "L33"]),
    ("C03",
     "另一个最强信号：报告自带验收判据与容差（迭代 < 50、力平衡残差 1%、降级限值 30%），"
     "并把唯一超差项按 honest-FAIL 显式登记、声明无定量基准。",
     ["L31", "L19", "L10", "L11"]),
    ("C04",
     "计算类信号：§1/§2 有控制方程型内容（漂移力谱积分、广义力映射 τ_req 与 SOCP 形式）与"
     "求解器迭代/停滞退出的收敛讨论；但无空间离散、无网格、无耗时表。",
     ["L05", "L07", "L03", "L08"]),
    ("C05",
     "工程类信号只到捎带级：给了一个对外端点与 44 例测试陈述，但无 changed-files / commit / "
     "接口契约，故不判 software-engineering。",
     ["L13", "L39", "L42"]),
    ("C06",
     "主题判定：动力定位能力评估——环境力（风/流/二阶漂移）+ 推力分配（凸 SOCP）+ 操作包线/"
     "单点失效降级，落在船舶总体性能学科的「操纵 × 耐波」交叉面。",
     ["L02", "L32", "L36", "L19"]),
    ("C07",
     "对象与适用范围：参数化参考船 PSV-6450（DP-2），结论仅对准静态能力评估成立，"
     "不含 DP 控制器动力学 / 瞬时波动 / 冰区。",
     ["L22", "L16"]),
    ("C08",
     "源文自述证据分级：风/流/漂移力为 REAL（经验系数族 / 工程惯例 / 长波衍射近似），"
     "推力折减为参数化假设；这是源文自述，本工序不定级、不背书。",
     ["L04", "L05", "L06"]),
]

# (element, grade as stated by the source, locator id, note)
GRADE_NOTES = [
    ("风", "REAL（经验系数族，非 CFD）", "L04", "源文自述；幅值 ±25%"),
    ("流", "REAL（工程惯例）", "L04", "源文自述；±15%"),
    ("波浪漂移", "REAL（长波衍射近似）", "L05", "源文自述；±30%，无 RAO/二阶传递函数"),
    ("推力折减", "参数化假设（已做敏感性）", "L06", "源文自述；5% 为 IMCA M140 量级"),
]

# (flag id, statement, locator ids, status, handling)
FLAGS = [
    ("F1",
     "口径不一致（未解决）：表 8 baseline 报「最差扇区 61.88 kn @ 60°」，而表 5（同称 1.0 kn 流、"
     "Hs 2.0 m、24 航向）的最小值是 59.41 kn @ 75°。两表扫描航向集或口径不同，源文未说明，"
     "本工序不替它判定哪个为准。",
     ["L18", "L17"], "unresolved",
     "需 03 工序逐表抽取后由原文/上游工件澄清；本工序不猜"),
    ("F2",
     "工件审计链不可独立重算：表 10 的 sha256 只给前 16 位（省略号截断），工件本体也不在本仓库，"
     "无法按表复算。",
     ["L20", "L37", "L14"], "unresolved",
     "需平台侧或上游仓库提供完整 sha256 / 工件本体"),
    ("F3",
     "外部可核验项：44 例测试全绿、pytest 命令、端点 URL 都指向 ship-performance-platform 仓库，"
     "本工序所在仓库无该代码，故未核验、也不主张其成立。",
     ["L39", "L40", "L12", "L13"], "unresolved",
     "超出本工序边界（跨仓核验不属 02）"),
    ("F4",
     "无定量基准项：最差扇区绝对风速（≈59 kn）与公开能力图 15–30 kn 带显著偏离，源文自评为"
     "模型偏乐观并如实登记为不小于 3%；本工序只记录该自评，不改变其状态。",
     ["L10", "L15", "L43"], "unresolved",
     "无单值基准，属源文 honest-FAIL，需 04 审核判断是否可接受"),
]

NOT_DONE = [
    "未做知识抽取（claims/evidence/provenance 属 03 工序）：本包只做类型/主题判定、结构切分与证据定位。",
    "未给任何结论标 verified：epistemic_status 一律 draft，assessment_status 一律 unassessed，"
    "验证级别由平台门计算。",
    "未核验源文数值本身（表 3–表 10）与外部仓库代码/测试；locator 只证明「原文如此写」。",
    "未读取或写入任何其它 report_id。",
]