#!/usr/bin/env python3
"""KBM-RCI-F1-ABC 预注册工件（prereg）生成器。

纪律：
  * 五个指标与判定阈值在本文件里**冻结**（METRICS / THRESHOLDS），
    执行后改动必须新版本号 v2，并保留 v1 供对照——禁止看完结果改指标。
  * prereg_id = sha256(canonical(prereg 内容))，批次 digest 一并绑定，
    形成「批次×指标×阈值」的不可变锚。
  * 生成后由平台 /tensor/reports 以报告形式打时间戳（先于任何臂执行）。

用法: python scripts/rci_f1_prereg.py --out-dir artifacts/rci-f1-abc
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os

PREREG_VERSION = "rci-f1-abc-prereg/1.0"
REGISTERED_AT = "2026-11-12T00:45:00Z"  # 预注册落盘时刻（早于 A/B/C 臂执行）

# ---- 冻结面（执行后不得修改；改=新版本） ----
METRICS = {
    "M1_unit_cost": {
        "name": "单位成本（每份文档）",
        "definition": (
            "三元组：tokens_per_doc = Σtokens/N；compute_per_doc = Σcompute_core_seconds/N；"
            "agent_hours_per_doc = wall_hours×agent_count/N（N=该臂完成的文档数，"
            "分母口径见 MO5 缺失数据规则）。另报固定权重合成指数 "
            "U = tokens/1000 + compute_seconds/60 + agent_hours（权重 w=(1,1,1)，先验声明，"
            "不随结果调整；三分量同时给出以便读者重加权）。"
        ),
        "unit": "tokens/份, core_s/份, agent_h/份, U 无量纲指数",
        "source": "arm run manifest（每 work package 的执行日志）+ 平台 mission budget/eval 字段",
    },
    "M2_throughput": {
        "name": "单位时间产量",
        "definition": "T = N_pass / wall_hours，N_pass = 通过结构门+证据门(+语义门, 仅 C)的文档数；"
                      "wall_hours = 臂首发派单到最后一份工件落盘的挂钟小时。",
        "unit": "份/小时",
        "source": "mission created_at / 最后工件 mtime / 校验器结果",
    },
    "M3_extraction_accuracy": {
        "name": "抽取准确率（独立盲审）",
        "definition": "四字段二元判定等权均值：claim 忠实原文 / evidence 定位可达 / "
                      "conditions 未臆造 / KO 类型适配。准确率 = 通过项数/判定项数。"
                      "审核者看不到 lane 标签；人工抽样 ≥30 条交叉验证，报 Cohen's κ。",
        "unit": "比例 [0,1]",
        "source": "blind_pack 评审回执 + human30 复核表",
    },
    "M4_evidence_completeness": {
        "name": "证据完整率",
        "definition": "E = locator_success_rate × evidence_coverage；"
                      "locator_success_rate = 可反查且片段匹配(sha256+行区间)的证据指针/全部证据指针；"
                      "evidence_coverage = 至少含 1 条可反查证据的 claim 数/全部 claim 数。"
                      "两因子分列报告，乘积为综合值。",
        "unit": "比例 [0,1]",
        "source": "证据门程序化校验回执（不采信抽取器自报 verified）",
    },
    "M5_knowledge_reuse": {
        "name": "知识复用效果（首周引用计数）",
        "definition": "R = 入库后 7×24h 内被下游消费/检索命中/引用次数（KE 消费日志按 KO id 计数），"
                      "按臂分列；首周未到 → WITHHELD（不得记 0）。",
        "unit": "次/周",
        "source": "ke 消费日志 / 检索命中日志（长线跟踪，T+7d 结算）",
    },
}

THRESHOLDS = {
    "accuracy_non_inferiority_pp": 3.0,       # C 相对 A 的准确率允许落后百分点
    "evidence_non_inferiority_pp": 3.0,
    "throughput_advantage_min": 3.0,          # C 吞吐 ≥ 3×A
    "cost_advantage_max_ratio": 1.0,          # C 单位成本 ≤ A
    "min_pass_rate_per_arm": 0.8,             # 低于此=该臂「未完成」，判定降级为 WITHHELD
    "human_sample_min": 30,
    "kappa_min_acceptable": 0.6,              # 盲审可靠性下限
    "significance": "两个比例差异用 Wilson 95% CI；CI 重叠即判「未分胜负」",
}

DECISION_RULE = {
    "H1_quality": "C 的 M3、M4 均不低于 A − 3pp（非劣性）",
    "H2_scale": "C 的 M2 ≥ 3×A 的 M2",
    "H3_cost": "C 的 M1 合成指数 U ≤ A 的 U",
    "verdict_scalable": "H1∧H2∧H3 同时成立 → 「大量普通 Agent + 治理可承担大规模工作」成立",
    "verdict_conditional": "H1 成立但 H2 或 H3 不成立 → 条件成立（写明成立条件与瓶颈）",
    "verdict_not_scalable": "H1 不成立 → 不成立（如实报，不粉饰）",
    "verdict_withheld": "任一臂 pass_rate < 0.8 或关键指标不可得 → WITHHELD（不判成立/不成立）",
}

STOPPING_RULES = [
    "单臂挂钟上限 4h；到线即冻结，指标按完成包子集计算并附完成率。",
    "单 work package 返工帽 2 次；再败记 failed 留痕（不吞、不计入 N_pass）。",
    "某臂结构性失败率 >50%（JSON/Schema 级，非语义级）→ 中止该臂，判 WITHHELD 并记录中止原因。",
    "预注册落盘后指标/阈值冻结；任何事后改动以 v2 预注册重新锚定，不得覆盖 v1。",
]

MISSING_DATA_RULES = {
    "MO1": "分子分母只统计「已落盘且被门禁裁决过」的包；未完成包不进分母。",
    "MO2": "未到结算时点（M5 首周）→ 记 null + status=WITHHELD，禁止填 0。",
    "MO3": "臂未启动/无工件 → 该臂全部指标 WITHHELD，并在报告中写明原因（不推断）。",
    "MO4": "异常值（单包 tokens 或墙钟 > 臂中位数 3 倍）保留在原始数据中，另报去极值敏感性。",
    "MO5": "N_pass 与 N_total 同时报告；不达标臂不得用 N_total 冒充产量。",
}

BLIND_PROTOCOL = {
    "blinding": "样本去标识：sample_id=sha256(seed|ko_id)[:12]；抹除 lane/repo/path/model/package_id；"
                "同一评审包内混合三臂样本、按哈希定序（消除评审漂移）。",
    "context": "审核者上下文 = 原文片段（±3 行）+ 知识对象（claims/evidence/conditions），"
               "不看生产者解释、不看生产 prompt（与 SPEC ④ 一致）。",
    "assignment": "每条样本 1 名独立审核者（verifier 席位），由 sample_id 哈希轮转指派，非人工挑选。",
    "rubric": "四字段二元判定：claim_faithful / locator_resolvable / conditions_not_invented / "
              "type_fit；附 ±0 上下文引用位置供复核。",
    "sealed_key": "sample_id→(lane, ko_id) 映射封存于 blind_key.json，其 sha256 写入预注册；"
                  "评分回执齐全后才允许解封对账。",
    "human_cross_validation": "人工抽样 ≥30 条（三臂按产量比例分层）逐字段复核，"
                              "与盲审评分算 Cohen's κ；κ<0.6 → 盲审可靠性不达标，M3 降级 WITHHELD。",
}

ANALYSIS_PLAN = {
    "unit_of_analysis": "文档（doc_id）；包级汇总后按臂聚合，避免包大小不等造成权重偏差。",
    "primary_comparison": "C vs A（标准产线 vs 单强 Agent），C vs B 为机制消融对照（审核/Skill 的边际贡献）。",
    "pairing": "B/C 共用 doc→package 映射（配对），文档级配对差分的符号检验作补充。",
    "uncertainty": "比例指标 Wilson 95% CI；吞吐用 wall_hours 单调性说明；不做 p 值挑选用以替代效应量。",
    "outliers": "见 MO4；去极值结果与原始结果并列。",
    "reuse_measurement": "M5 在 T+7d 结算，需 KE 消费日志可用；不可用则 WITHHELD 并记基础设施缺口。",
    "no_peeking": "臂未结算前不读臂间质量对比明细（只看进度/成本流水），防止中途调阈值。",
}

CONFOUNDERS = {
    "model_mix": "A 臂钉强档模型（fleet 强档：Qwen3.8-27B），B/C 用普通档（deepseek-v4-flash 为主）"
                 "——这是设计变量（组织方式含模型档位），报告须明示不可把差异全归组织方式。",
    "doc_difficulty": "三臂同批同文档，难度不构成臂间差异，但影响绝对水平。",
    "review_load": "C 臂含独立审核工序（成本计入 C），B 臂无审核；B 的产出准确率仍用同一盲审评定。",
    "time_of_day": "并发调度导致的排队延迟计入挂钟，属平台噪声，记录但不剔除。",
    "skill_maturity": "C 臂 Skill v1 成熟度有限，Skills 效果差异只能在后续轮次扩大样本验证。",
}

SELF_AUDIT = [
    "预注册先于执行：prereg 报告时间戳早于 A/B/C 臂首个 mission created_at。",
    "指标冻结：METRICS 五键与 v1 摘要 sha256 入测试断言，改动即测试红。",
    "允许失败不允许伪造：任何指标不可得写 WITHHELD，禁填 0/均值。",
    "零手抄：报告数字由 artifacts/rci-f1-abc/metrics.json 程序化注入。",
]


def canonical(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def build(out_dir: str) -> dict:
    batch_path = os.path.join(out_dir, "batch60.json")
    wps_path = os.path.join(out_dir, "tk_work_packages.json")
    batch = json.load(open(batch_path, encoding="utf-8"))
    wps = json.load(open(wps_path, encoding="utf-8"))
    prereg = {
        "version": PREREG_VERSION,
        "anchor": "KBM-RCI-F1-ABC",
        "mission_id": 15496,
        "registered_at": REGISTERED_AT,
        "batch": {
            "digest": batch["digest"],
            "n": batch["n"],
            "batch_file_sha256": hashlib.sha256(open(batch_path, "rb").read()).hexdigest(),
            "workpackages_file_sha256": hashlib.sha256(open(wps_path, "rb").read()).hexdigest(),
            "lanes": {"A": 1, "B": 20, "C": 20},
            "packages_total": len(wps["packages"]),
        },
        "arms": {
            "A": {"org": "1 个强 Agent 独立加工整批", "model_tier": "strong (Qwen3.8-27B)",
                  "review": "none", "skills": "none", "packages": 1},
            "B": {"org": "20 普通 Agent 并行", "model_tier": "ordinary (deepseek-v4-flash)",
                  "review": "none", "skills": "none", "packages": 20},
            "C": {"org": "20 普通 Agent + 独立审核 + 成熟 Skills（标准产线）",
                  "model_tier": "ordinary (deepseek-v4-flash)",
                  "review": "independent reviewer + semantic gate", "skills": "v1", "packages": 20},
        },
        "sole_variable": "组织方式（含模型档位/审核/Skill 三要素的整体配置，非单因子拆解）",
        "metrics": METRICS,
        "thresholds": THRESHOLDS,
        "decision_rule": DECISION_RULE,
        "stopping_rules": STOPPING_RULES,
        "missing_data_rules": MISSING_DATA_RULES,
        "blind_protocol": BLIND_PROTOCOL,
        "analysis_plan": ANALYSIS_PLAN,
        "confounders": CONFOUNDERS,
        "self_audit": SELF_AUDIT,
    }
    prereg["prereg_id"] = hashlib.sha256(canonical(prereg)).hexdigest()
    path = os.path.join(out_dir, "prereg.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(prereg, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return prereg


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="artifacts/rci-f1-abc")
    args = ap.parse_args()
    p = build(args.out_dir)
    print(json.dumps({"prereg_id": p["prereg_id"], "batch_digest": p["batch"]["digest"],
                      "metrics": list(p["metrics"]), "registered_at": p["registered_at"]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()