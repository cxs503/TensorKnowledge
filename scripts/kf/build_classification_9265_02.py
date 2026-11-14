#!/usr/bin/env python3
"""wp-9265-02 — 工序 02 分类解析（report_id=9265）。

只做分类 + 结构切分 + 判定依据的逐字定位，不做知识抽取（不做 claims），
不改写上游产物，不把任何结论标成 verified。

产物（均落 worktree）：
  artifacts/wp-9265-02/classification.json   工序产物（= KF-RESULT.outputs["classification.json"]）
  artifacts/wp-9265-02/kf_result.json        KF-RESULT v1 结果信封（schema: schemas/kf_result.v1.schema.json）
  artifacts/wp-9265-02/REPORT.md             KF-RESULT 报告正文（含唯一一个 ```json 结果块）
  artifacts/wp-9265-02/classification_figure.png  结构切分 / 信号覆盖诊断图

零手抄：所有引文由 `_loc()` 在原文里 `str.find` 定位，偏移与 content_hash 由程序计算；
任何一条引文若不能在原文逐字定位，脚本直接抛错退出（不产出）。

复跑：
  python3 scripts/kf/build_classification_9265_02.py            # 用已缓存原文
  python3 scripts/kf/build_classification_9265_02.py --fetch     # 先从平台 API 取原文
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG_ID = "wp-9265-02"
TASK_TYPE = "02-classification-parse"
REPORT_ID = "9265"
CONTRACT_VERSION = "1.0"
SOURCE_URI = "tensor://reports/9265"
SOURCE_FIELD = "markdown"
EXPECTED_HASH = "d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c"
EXPECTED_CHARS = 9599
SCENARIO_KEY = "dp_capability_assessment"

OUT_DIR = REPO_ROOT / "docs" / "kf" / PKG_ID
SRC_PATH = OUT_DIR / "report_9265.md"
REGISTRY = REPO_ROOT / "extraction-skills" / "registry.json"


# --------------------------------------------------------------------------
# 原文获取 + 哈希（哈希是门的第一条：不一致就不往下走）
# --------------------------------------------------------------------------
def _http_get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def _http_post(url: str, payload: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def fetch_source() -> bytes:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    tok = _http_post(
        base + "/auth/login",
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        },
    )
    token = tok.get("access_token") or tok.get("token")
    rep = _http_get(base + "/tensor/reports/" + REPORT_ID, token)
    if isinstance(rep.get("data"), dict):
        rep = rep["data"]
    raw = rep["markdown"].encode("utf-8")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SRC_PATH.write_bytes(raw)
    return raw


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# --------------------------------------------------------------------------
# 逐字定位：偏移 + content_hash 全由程序算
# --------------------------------------------------------------------------
class Locator:
    def __init__(self, text: str):
        self.text = text
        self.items: list[dict] = []
        self._seen: set[str] = set()
        self.failures: list[str] = []

    def add(self, loc_id: str, supports: str, quote: str) -> str | None:
        if loc_id in self._seen:
            raise SystemExit(f"duplicate locator id: {loc_id}")
        self._seen.add(loc_id)
        start = self.text.find(quote)
        if start < 0:
            self.failures.append(f"{loc_id}: quote not found verbatim: {quote[:60]!r}")
            return None
        end = start + len(quote)
        self.items.append(
            {
                "id": loc_id,
                "supports": supports,
                "locator_type": "char_range",
                "value": f"{SOURCE_URI}#chars={start}-{end}",
                "start_offset": start,
                "end_offset": end,
                "quote": quote,
                "content_hash": "sha256:" + sha256_bytes(quote.encode("utf-8")),
            }
        )
        return loc_id


# --------------------------------------------------------------------------
# 结构切分（parse 部分）：按 ATX 标题切，保留 char 偏移
# --------------------------------------------------------------------------
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$", re.M)


def parse_structure(text: str) -> list[dict]:
    heads = [(m.start(), len(m.group(1)), m.group(2)) for m in HEADING_RE.finditer(text)]
    sections: list[dict] = []
    for i, (pos, level, title) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        sections.append(
            {
                "index": i,
                "level": level,
                "heading": title,
                "start_offset": pos,
                "end_offset": end,
                "chars": end - pos,
                "body_lines": text[pos:end].count("\n"),
                "tables": len(re.findall(r"^\|", text[pos:end], re.M)),
                "code_blocks": text[pos:end].count("```") // 2,
            }
        )
    return sections


def section_ids(sections: list[dict]) -> dict:
    """把报告自报的六段章节（①..⑥）与标题切分对上，作为 parse 结果的可核项。"""
    mapping = {}
    for s in sections:
        m = re.match(r"^([①②③④⑤⑥])", s["heading"])
        if m:
            mapping[m.group(1)] = s["index"]
    return mapping


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="先经平台 API 拉取原文")
    args = ap.parse_args()

    if args.fetch or not SRC_PATH.exists():
        raw = fetch_source()
    else:
        raw = SRC_PATH.read_bytes()

    digest = sha256_bytes(raw)
    text = raw.decode("utf-8")
    hash_ok = digest == EXPECTED_HASH and len(text) == EXPECTED_CHARS
    if not hash_ok:
        raise SystemExit(
            f"source_hash mismatch: got {digest} chars={len(text)} "
            f"expected {EXPECTED_HASH} chars={EXPECTED_CHARS}"
        )

    loc = Locator(text)

    # ---- A. 主题 / 领域定位依据 -------------------------------------------
    loc.add(
        "L01-domain-dp-definition",
        "topic.domain",
        "DP（dynamic positioning）系统靠推进器合成力/力矩抵消风、浪、流载荷，在无锚条件下保持船位与艏向。",
    )
    loc.add(
        "L02-vessel-type-psv",
        "topic.vessel_type",
        "本节点评估一艘典型 **DP-2 海工供应船（PSV, UT-755 级）** 的 DP 能力",
    )
    loc.add(
        "L03-main-dimensions",
        "topic.geometry",
        "| LOA × B × T | 76.5 × 18.6 × 6.3 m | `reference_psv()` |",
    )
    loc.add(
        "L04-campaign-node-branch",
        "provenance.campaign",
        "**战役节点** IN144-N05 ｜ **仓库** ship-performance-platform ｜ **分支** agent/m7890",
    )

    # ---- B. 类型判定依据（六分型的正面证据） ------------------------------
    loc.add(
        "L10-numerical-kernel-modules",
        "type.software-engineering",
        "**落库模块** `backend/physics/dp_core.py`（物理/数值内核）、`backend/api/dynamic_positioning.py`（FastAPI 端点）",
    )
    loc.add(
        "L11-test-suite",
        "type.software-engineering",
        "**验证** `tests/test_dp_capability.py`（40 项 pytest，22 s 全绿）",
    )
    loc.add(
        "L12-governing-laws",
        "type.scientific-computation",
        "螺旋桨定律 `T = ρD⁴K_Tn²`、`P = 2πρD⁵K_Qn³` ⇒ 消去转速得 **`T ∝ P^{2/3}`",
    )
    loc.add(
        "L13-layered-physics-model",
        "type.scientific-computation",
        "**L2 环境力模型**",
    )
    loc.add(
        "L14-optimisation-problem",
        "type.algorithm-implementation",
        "min_e  Σ (w_i (e_i − r_i)²)        (二次型, 良态)",
    )
    loc.add(
        "L15-solver-iterations",
        "type.scientific-computation",
        "| 受约束（0.5× 推力）工况 QP 迭代数 | 最大 29 |",
    )
    loc.add(
        "L16-two-level-loops",
        "type.algorithm-implementation",
        "**对风速二分**（容差 5e-3 m/s）求可行上界",
    )
    loc.add(
        "L17-error-table",
        "type.scientific-computation",
        "| QP 解 vs KKT 闭式解 | 解析 | 7.1e-15 kN | **是** |",
    )
    loc.add(
        "L18-regulation-comparison",
        "type.scientific-computation",
        "## ④ 与 DNV 规范的对照（定性）",
    )
    loc.add(
        "L19-failure-analysis",
        "topic.dp2-redundancy",
        "### 3.3 单推力器失效能力降级（DP-2 最坏单点失效，1 kn=0.5 m/s 共线流）",
    )
    loc.add(
        "L20-figures",
        "type.scientific-computation",
        "`capability_polar.png` — 极坐标操作包线图（5 条等电流曲线 + 最坏失效虚线）",
    )
    loc.add(
        "L21-repro-commands",
        "type.software-engineering",
        "python3 -m pytest tests/test_dp_capability.py -q          # 40 passed, 22 s",
    )

    # ---- C. 排除其它类型的依据（负面证据，来自报告自述） ------------------
    loc.add(
        "L30-no-referenced-benchmark",
        "exclude.experimental-validation",
        "仓库内没有风洞、模型试验或 OCIMF/Isherwood 回归表可对标 ⇒ **数值层 WITHHELD**",
    )
    loc.add(
        "L31-withheld-numeric-layer",
        "exclude.experimental-validation",
        "**无基准，声明 WITHHELD**",
    )
    loc.add(
        "L32-static-3dof-limitation",
        "exclude.dynamic-simulation",
        "- 静力 3-DOF：无低频/波频动态、无控制器、无瞬态与推力器再分配过程（只用速率限做静态可行性）。",
    )
    loc.add(
        "L33-no-published-envelope-data",
        "exclude.literature-review",
        "仓库内没有可引用的 DNV 已发表包线数值数据集，故**只做方法与定性特征对照**（数值层 WITHHELD）",
    )

    if loc.failures:
        print("\n".join(loc.failures), file=sys.stderr)
        raise SystemExit("verbatim locator(s) unresolved -> 不产出 classification.json")

    sections = parse_structure(text)
    sec_ids = section_ids(sections)

    # ---- D. 信号表：registry 的 identify_signals 是英文关键词（诚实披露） --
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    skills = {s["skill_id"]: s for s in registry["skills"]}
    lowered = text.lower()
    literal_hits = {}
    for sid, s in skills.items():
        hits = []
        for sig in s.get("identify_signals", []):
            n = lowered.count(sig.lower()) if not sig.startswith("citation density") else 0
            hits.append({"signal": sig, "literal_hits": n})
        literal_hits[sid] = hits

    semantic_map = {
        "xsk-scientific-computation": ["L12-governing-laws", "L13-layered-physics-model",
                                       "L15-solver-iterations", "L17-error-table",
                                       "L18-regulation-comparison", "L20-figures"],
        "xsk-algorithm-implementation": ["L14-optimisation-problem", "L16-two-level-loops"],
        "xsk-software-engineering": ["L10-numerical-kernel-modules", "L11-test-suite",
                                     "L21-repro-commands"],
        "xsk-experimental-validation": [],
        "xsk-literature-review": [],
        "xsk-technical-proposal": [],
    }
    signal_table = []
    for sid, s in skills.items():
        literal_total = sum(h["literal_hits"] for h in literal_hits[sid])
        semantic = semantic_map.get(sid, [])
        signal_table.append(
            {
                "skill_id": sid,
                "report_type": s["report_type"],
                "registry_identify_signals": s.get("identify_signals", []),
                "literal_signal_hits_in_source": literal_total,
                "literal_hits_detail": literal_hits[sid],
                "semantic_evidence_locators": semantic,
                "semantic_evidence_count": len(semantic),
                "skill_lifecycle_state": s["lifecycle_state"],
            }
        )

    by_loc = {i["id"]: i for i in loc.items}

    classification = {
        "schema": "classification.v1",
        "package_id": PKG_ID,
        "task_type": TASK_TYPE,
        "contract_version": CONTRACT_VERSION,
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": digest,
            "hash_expected_from_contract": EXPECTED_HASH,
            "hash_matches_contract": hash_ok,
            "chars": len(text),
            "bytes_utf8": len(raw),
            "title": "DP 系统能力评估：推力分配 QP × 环境力平衡 × 操作包线图（IN144-N05 / m7890）",
            "scenario_key": SCENARIO_KEY,
            "campaign": {
                "node": "IN144-N05",
                "repo": "ship-performance-platform",
                "agent_branch": "agent/m7890",
                "evidence": ["L04-campaign-node-branch"],
                "note": "上游产线标识，仅用于溯源；本工序不改写上游产物。",
            },
        },
        "report_type": "scientific-computation",
        "report_type_confidence": "medium",
        "classification_is_hypothesis": True,
        "unclassified_is_legal": True,
        "used_unclassified_fallback": False,
        "report_type_decision": {
            "rule": "取语义证据覆盖报告核心贡献（物理模型 + 数值方法 + 误差判定表 + 图）最多的报告类型为主型；"
                    "只有当同一批证据同时满足其 skill 的步骤前提时才列为副型。分类是可反驳假设，非 verified。",
            "primary_evidence": ["L12-governing-laws", "L13-layered-physics-model",
                                 "L15-solver-iterations", "L17-error-table",
                                 "L18-regulation-comparison", "L20-figures"],
            "why_not_only_algorithm": "报告主体是物理量（风/流/波浪漂移力、包线风速）与其自洽性/误差判定，"
                                      "算法（QP）是为物理服务的一层（② 明列 L1~L4 四层，L3 才是 QP）；"
                                      "见 L13-layered-physics-model 与 L17-error-table。",
            "why_not_software-engineering": "软件工程证据（模块/端点/40 项 pytest）是交付形态，"
                                            "不是报告的知识贡献；见 L10/L11/L21。",
        },
        "secondary_types": [
            {
                "report_type": "algorithm-implementation",
                "confidence": "medium",
                "evidence": ["L14-optimisation-problem", "L16-two-level-loops"],
                "note": "QP 推力分配（无量纲化、等式约束解析消去、三种目标模式）+ 外层对风速二分。",
            },
            {
                "report_type": "software-engineering",
                "confidence": "low",
                "evidence": ["L10-numerical-kernel-modules", "L11-test-suite", "L21-repro-commands"],
                "note": "落库模块/端点/测试/分支信息齐备，但只占报告的外壳。",
            },
        ],
        "excluded_types": [
            {
                "report_type": "experimental-validation",
                "reason": "报告自述无风洞/模型试验/回归表可对标，数值层 WITHHELD；无试验对象、无测量不确定度。",
                "evidence": ["L30-no-referenced-benchmark", "L31-withheld-numeric-layer"],
            },
            {
                "report_type": "literature-review",
                "reason": "无文献综述节、无参考文献列表；DNV 对照仅定性且自述无可引数据集。",
                "evidence": ["L33-no-published-envelope-data", "L18-regulation-comparison"],
            },
            {
                "report_type": "technical-proposal",
                "reason": "主体是已完成的计算与结果，不是方案/路线图；仅 ⑥ 末尾留下一句改进方向。",
                "evidence": ["L32-static-3dof-limitation"],
            },
        ],
        "domain": {
            "discipline": "船舶总体性能",
            "subdomain": "操纵性 · 动力定位（DP）能力评估",
            "lane": "B",
            "tier": "l",
            "scenario_key": SCENARIO_KEY,
            "vessel": {
                "type": "DP-2 海工供应船（PSV, UT-755 级）",
                "principal_dimensions": "76.5 × 18.6 × 6.3 m",
                "evidence": ["L02-vessel-type-psv", "L03-main-dimensions"],
            },
            "topic_tags": [
                {"tag": "dynamic-positioning-capability", "evidence": ["L01-domain-dp-definition"]},
                {"tag": "thrust-allocation-qp", "evidence": ["L14-optimisation-problem"]},
                {"tag": "environmental-loads-wind-current-wave-drift", "evidence": ["L13-layered-physics-model"]},
                {"tag": "operability-envelope-polar", "evidence": ["L20-figures"]},
                {"tag": "dp2-single-point-failure-redundancy", "evidence": ["L19-failure-analysis"]},
                {"tag": "dnv-st-0111-classification-comparison", "evidence": ["L18-regulation-comparison"]},
                {"tag": "static-3dof-conservative-scope", "evidence": ["L32-static-3dof-limitation"]},
            ],
        },
        "skill_selection": {
            "skill_id": "xsk-scientific-computation",
            "skill_version": skills["xsk-scientific-computation"]["skill_version"],
            "registry_version": registry["registry_version"],
            "lifecycle_state": skills["xsk-scientific-computation"]["lifecycle_state"],
            "selection_basis": "report_type 主型 → registry 按 report_type 一对一映射。",
            "registry_state_caveat": "registry 自述全部 skill 为 template-created（无代表报告跑通全流程），"
                                     "故所选 skill 的步骤仅为骨架，03 工序前不应视为已校验的方法学。",
        },
        "signal_table": signal_table,
        "signal_method_note": "registry.identify_signals 全部为英文关键词，本报告为中文正文，"
                              "字面命中数（literal_signal_hits_in_source）系统性偏低甚至为 0，"
                              "不能作为分类依据；因此以逐字定位的中文语义证据为主，"
                              "字面命中只作诊断量如实记录（这是本工序的方法学局限，不是分类结果的证据强度）。",
        "structure": {
            "parser": "ATX heading 切分（^#{1,6}\\s），偏移为 UTF-8 解码后的字符偏移",
            "self_declared_six_sections": sec_ids,
            "self_declared_six_sections_complete": sorted(sec_ids) == list("①②③④⑤⑥"),
            "section_count": len(sections),
            "sections": sections,
        },
        "evidence_locators": loc.items,
        "uncertainty": [
            {
                "item": "类型判定为可反驳假设，未经验证",
                "status": "hypothesis",
                "note": "confidence=medium：主型与副型共享同一批数值证据，registry 的英文关键词无法字面判定。",
            },
            {
                "item": "报告数值层缺基准，能力包线绝对值不可复核",
                "status": "withheld_by_source",
                "evidence": ["L31-withheld-numeric-layer"],
                "note": "原文自述 WITHHELD；本工序只分类，不对数值下任何结论。",
            },
            {
                "item": "报告为静力 3-DOF 模型，动态/控制器未建模",
                "status": "declared_limitation",
                "evidence": ["L32-static-3dof-limitation"],
            },
            {
                "item": "报告对象是 reference_psv() 工程模型船，是否对应某实船未声明",
                "status": "unresolved",
                "evidence": ["L03-main-dimensions", "L02-vessel-type-psv"],
                "note": "原文只给主尺度与模型函数名，absent 信息不补（do_not_invent_missing_information）。",
            },
        ],
        "not_done": [
            "不做知识抽取（claims/evidence/provenance 属 03 工序，本包 objective.register_assets=false 亦未登记附件）",
            "不判 verified：verified 由平台门计算，本产物仅 draft",
        ],
        "generated_by": "scripts/kf/build_classification_9265_02.py",
    }

    # 唯一性 + 可解析自检（写盘前）
    ids = [i["id"] for i in classification["evidence_locators"]]
    assert len(ids) == len(set(ids)), "duplicate locator ids"
    for i in classification["evidence_locators"]:
        assert text[i["start_offset"]:i["end_offset"]] == i["quote"], i["id"]
        assert "sha256:" + sha256_bytes(i["quote"].encode()) == i["content_hash"], i["id"]
    assert classification["report_type"] in registry["report_types"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "classification.json").write_text(
        json.dumps(classification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    kf_result = {
        "package_id": PKG_ID,
        "task_type": TASK_TYPE,
        "contract_version": CONTRACT_VERSION,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + digest,
            "source_hash_matches": True,
            "title": classification["source"]["title"],
            "scenario_key": SCENARIO_KEY,
            "chars": len(text),
        },
        "outputs": {"classification.json": classification},
    }
    (OUT_DIR / "kf_result.json").write_text(
        json.dumps(kf_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # 诊断图（程序化生成，不以图代证）
    make_figure(sections, signal_table, text)

    print("report_id:", REPORT_ID)
    print("chars:", len(text), "sha256:", digest)
    print("locators:", len(ids), "sections:", len(sections), "six:", classification["structure"]["self_declared_six_sections"])
    print("report_type:", classification["report_type"], "skill:", classification["skill_selection"]["skill_id"])
    print("wrote:", OUT_DIR / "classification.json")
    return 0


def make_figure(sections: list[dict], signal_table: list[dict], text: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    # 字体缺 CJK（DejaVu/Noto 无中文字形），标签一律用 ASCII，避免出现豆腐块
    cn_map = {"①": "S1  case-intro", "②": "S2  method", "③": "S3  results",
              "④": "S4  DNV-compare", "⑤": "S5  caveats", "⑥": "S6  error-vs-baseline"}
    labels = []
    for s in sections:
        head = s["heading"]
        if head[:1] in cn_map:
            labels.append(cn_map[head[:1]])
        elif re.match(r"^\d+\.\d+", head):
            labels.append("    " + head.split()[0])
        elif s["level"] == 1:
            labels.append("H1  title")
        else:
            labels.append("    " + ("repro" if "复现" in head else head[:10].encode("ascii", "ignore").decode() or "section"))

    lens = [s["chars"] for s in sections]
    ax1.barh(range(len(sections)), lens, color="#4C78A8")
    ax1.set_yticks(range(len(sections)))
    ax1.set_yticklabels(labels, fontsize=8)
    ax1.invert_yaxis()
    ax1.set_xlabel("section chars")
    ax1.set_title(f"Structure segmentation ({len(sections)} ATX sections, {len(text)} chars)")
    for i, v in enumerate(lens):
        ax1.text(v, i, f" {v}", va="center", fontsize=7)

    ids = [s["skill_id"].replace("xsk-", "") for s in signal_table]
    lit = [s["literal_signal_hits_in_source"] for s in signal_table]
    sem = [s["semantic_evidence_count"] for s in signal_table]
    y = range(len(ids))
    ax2.barh([i - 0.2 for i in y], lit, height=0.4, label="literal (English keyword) hits", color="#B0B0B0")
    ax2.barh([i + 0.2 for i in y], sem, height=0.4, label="semantic locator-backed hits", color="#E45756")
    ax2.set_yticks(list(y))
    ax2.set_yticklabels(ids, fontsize=8)
    ax2.invert_yaxis()
    ax2.set_xlabel("signal hits")
    ax2.set_title("Registry signal coverage: literal vs semantic")
    ax2.legend(fontsize=8)
    fig.tight_layout()
    out = OUT_DIR / "classification_figure.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print("wrote:", out)


if __name__ == "__main__":
    raise SystemExit(main())