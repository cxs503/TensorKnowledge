"""wp-9246-02 分类解析的输入规格：契约常量 / 信号探针 / 逐字证据锚点 / step-fit 表。

零手抄原则：锚点只写"锚串"，真实 quote、偏移、sha256 一律由脚本从原文切出并自证；
锚串必须在原文中恰好出现一次，否则运行即失败（不猜、不近似）。
"""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# --- 契约常量（与工作包 YAML 逐字一致） -------------------------------------
PACKAGE_ID = "wp-9246-02"
TASK_TYPE = "02-classification-parse"
CONTRACT_VERSION = "1.0"
REPORT_ID = "9246"
SOURCE_URI = "tensor://reports/9246"
SOURCE_FIELD = "markdown"
SOURCE_HASH = "sha256:80bcb3216845e02d844926b8d2e733882e8de69ebd756ff706296a8ab3e165b5"
SOURCE_TITLE = ("IN144-N09: Granular Bed Fluid-Solid Coupling - Ergun Pressure Drop & "
                "Richardson-Zaki Settling Validation")
SCENARIO_KEY = "IN144-N09"
SOURCE_CHARS = 11250
LANE = "B"
DELIVERY_REPO = "TensorKnowledge"
MISSION_ID = 19786

REGISTRY = REPO / "extraction-skills" / "registry.json"
RESULT_SCHEMA = REPO / "schemas" / "kf_result.v1.schema.json"
OUT_DIR = REPO / "docs" / "production" / "wp-9246-02"
MIRROR_DIR = REPO / "artifacts" / "wp-9246-02"
CACHE_MD = REPO / "artifacts" / "wp-9246-02" / "source_markdown.md"
FIXTURE_MD = REPO / "tests" / "fixtures" / "kf" / "wp-9246-02" / "source_markdown.md"

#: 事先声明的分类决策规则（打分之前写定，不因结果回头调整）。
DECISION_RULE = {
    "declared": "before signal scoring; not tuned after seeing results",
    "R1_eligibility": ("候选类型必须在其 registry identify_signals 中命中 >= 2 条"
                       "（citation density 这类派生信号按公式计算）。"),
    "R2_step_fit": ("合格候选中，registry skill 的全部 steps 都能由原文满足者为胜"
                    "（step-fit 计数，越高越好）。"),
    "R3_stated_purpose": "R2 打平时，以报告自述目的句（逐字证据）定胜负。",
    "R4_residual": ("仍打平则比目的性证据条数；依旧打平则 report_type='unclassified'，禁止硬猜。"),
    "admissible_types": "registry.report_types 的 6 类 + 'unclassified'",
    "used_in_this_package": "R1 + R2（R2 唯一决胜，R3/R4 未触发，见 decision_trace）",
}

#: 每个 report_type 的 registry identify_signals -> 可执行探针
PROBES: dict[str, list[tuple[str, str]]] = {
    "literature-review": [
        ("related work", r"related\s+work"),
        ("state of the art", r"state\s+of\s+the\s+art"),
        ("survey", r"\bsurvey\b"),
        ("bibliography", r"\bbibliograph"),
        ("citation density >= 5 per 1000 chars", "@DERIVED@"),
    ],
    "scientific-computation": [
        ("governing equations", r"(F_drag\s*=|ε_i\s*=\s*1|C_D\s*=\s*24/Re)"),
        ("discretisation", r"(explicit Euler|Time step:|dt = 0\.1)"),
        ("convergence study", r"(Time-Step Convergence|time-step convergence|dt → dt/2)"),
        ("mesh refinement", r"(mesh\s+(refinement|independence)|grid\s+convergence)"),
        ("timing table", r"(wall[- ]?clock|\bruntime\b|elapsed|speed-?up)"),
    ],
    "algorithm-implementation": [
        ("pseudocode", r"pseudo-?\s?code"),
        ("complexity", r"(computational\s+complexity|algorithmic\s+complexity)"),
        ("algorithm block", r"(?i)\balgorithm\s+(block|listing)"),
        ("function signature", r"\b[a-z_][a-z0-9_]*\(\)"),
        ("O(n", r"O\(n"),
    ],
    "software-engineering": [
        ("changed files", r"(changed\s+files?|files\s+changed)"),
        ("commit", r"\bcommit"),
        ("interface", r"\binterface"),
        ("regression", r"\bregression"),
        ("API", r"\bAPI\b"),
    ],
    "technical-proposal": [
        ("proposal", r"\bproposal\b"),
        ("design", r"\bdesign\b"),
        ("roadmap", r"\broadmap\b"),
        ("specification", r"\bspecification\b"),
        ("plan", r"\bplan\b"),
    ],
    "experimental-validation": [
        ("test matrix", r"(machine-checkable criteria|acceptance criteria)"),
        ("facility", r"(facility|apparatus|test\s+rig|laborator)"),
        ("measurement uncertainty", r"(measurement\s+uncertainty|coverage\s+factor|uncertainty\s+budget)"),
        ("validation case", r"validat"),
        ("baseline comparison", r"(Relative error|relative error|analytical solution|Ergun correlation)"),
    ],
}

#: step-fit：registry 每个 skill 的 steps 是否可由原文满足（每行绑定证据 id）
STEP_FIT: dict[str, list[tuple[str, str, str]]] = {
    "scientific-computation": [
        ("extract-equations-and-parameters", "satisfiable", "EV-04"),
        ("extract-accuracy-statements", "satisfiable", "EV-10"),
        ("extract-assumptions", "satisfiable", "EV-15"),
    ],
    "experimental-validation": [
        ("extract-conditions", "satisfiable", "EV-14"),
        ("extract-comparison-pairs", "satisfiable", "EV-11"),
        # registry 要求不确定度与包含因子逐字照抄；原文只有数值误差来源讨论
        # （见 EV-20 所在章节），无 coverage factor / 测量不确定度声明 -> 不可满足。
        ("extract-uncertainty", "not_satisfiable", "UR-02"),
    ],
    "algorithm-implementation": [("(registry steps not evaluated: type eliminated at R1)",
                                  "not_evaluated", "")],
    "software-engineering": [("(registry steps not evaluated: type eliminated at R1)",
                              "not_evaluated", "")],
    "technical-proposal": [("(registry steps not evaluated: type eliminated at R1)",
                            "not_evaluated", "")],
    "literature-review": [("(registry steps not evaluated: type eliminated at R1)",
                           "not_evaluated", "")],
}

#: 逐字证据锚点：id -> (锚串, 归属字段)
ANCHORS: dict[str, tuple[str, str]] = {
    "EV-01": ("# IN144-N09: Granular Bed Fluid-Solid Coupling Minimum Verifiable Unit",
              "classification.source.title_line"),
    "EV-02": ("The implementation validates two fundamental closure relations",
              "classification.report_type.primary / stated purpose"),
    "EV-03": ("Six machine-checkable criteria validate the implementation:",
              "signals.experimental-validation.test matrix"),
    "EV-04": ("F_drag = c(ε, |u|) · u_slip",
              "signals.scientific-computation.governing equations"),
    "EV-05": ("**Ergun branch** (ε < 0.8): c = V_p [150μ(1-ε)/(ε³d²) + 1.75ρ_f|u|/(ε³d)]",
              "signals.scientific-computation.governing equations (closure form)"),
    "EV-06": ("Semi-coupled batch settling with explicit Euler integration:",
              "signals.scientific-computation.discretisation"),
    "EV-07": ("- Time step: dt = 0.1 τ (τ = drag relaxation time)",
              "signals.scientific-computation.discretisation (dt)"),
    "EV-08": ("### Criterion 6: Time-Step Convergence",
              "signals.scientific-computation.convergence study"),
    "EV-09": ("The steady-state pressure drop is invariant to time-step halving",
              "signals.scientific-computation.convergence study (detail)"),
    "EV-10": ("**Maximum relative error:** 1.47% (threshold: 15%)",
              "signals.experimental-validation.baseline comparison (headline error)"),
    "EV-11": ("| Laminar | 2.0×10⁻³ | 2180.55 | 2212.71 | 1.47% |",
              "signals.experimental-validation.baseline comparison (measured vs reference row)"),
    "EV-12": ("The simulated terminal velocity matches the Schiller-Naumann analytical solution"
              " to within 0.013%",
              "signals.experimental-validation.baseline comparison (analytical reference)"),
    "EV-13": ("The DEM settling simulations recover the Richardson-Zaki exponent to within 0.035",
              "signals.experimental-validation.baseline comparison (correlation reference)"),
    "EV-14": ("- Particle diameter: d = 1.0 mm (monodisperse)",
              "step-fit.experimental-validation.extract-conditions (configuration)"),
    "EV-15": ("1. **Unresolved fluid**: The fluid is a single uniform velocity",
              "step-fit.scientific-computation.extract-assumptions"),
    "EV-16": ("- **Module**: `tensordem.bedcoupling` (closures, packing, bed, study)",
              "signals.software-engineering (audit-trail only)"),
    "EV-17": ("- **Tests**: `tests/test_bedcoupling_*.py` (4 test files, 28 tests, all passing)",
              "signals.software-engineering (audit-trail only)"),
    "EV-18": ("The implementation passes all six acceptance criteria with substantial margin",
              "classification.rationale (conclusion sentence)"),
    "EV-19": ("**Ergun pressure drop correlation** (1952)",
              "signals.literature-review (citation marker)"),
    "EV-20": ("### Error Sources",
              "step-fit.experimental-validation.extract-uncertainty (no coverage factor)"),
    "EV-21": ("- **Acceptance study**: `run_acceptance_study()` (deterministic, seed-controlled)",
              "signals.algorithm-implementation.function signature"),
    "EV-22": ("### Applicability Domain", "classification.applicability_scope"),
}

SHORT = {
    "literature-review": "lit-review",
    "scientific-computation": "sci-computation",
    "algorithm-implementation": "algo-impl",
    "software-engineering": "software-eng",
    "technical-proposal": "tech-proposal",
    "experimental-validation": "exp-validation",
}


def api_base() -> str:
    return os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")