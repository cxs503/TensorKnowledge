"""wp-11478-01 · claim registration for report 11478 (no extraction, no verification).

Each claim is bound to a byte-exact locator in the report markdown, or is explicitly
`unresolved` with a machine-readable reason. Nothing here is marked verified: platform
verification gate owns that field.

Output: runs/wp-11478-01/claims_11478.json
"""
import hashlib
import json
import pathlib
import sys

PKG = "wp-11478-01"
REPORT_ID = "11478"
RUN_DIR = pathlib.Path("runs") / PKG

CLAIMS = [
    dict(claim_id="C01-report-values-come-from-m9713-artifact",
         text="报告 §③/§⑥ 的全部数值唯一取自工件 docs/m9713/six_dim_power_validation.json",
         status="unresolved",
         quotes=["生成 `docs/m9713/six_dim_power_validation.json`",
                 "全部取自 `docs/m9713/six_dim_power_validation.json`"],
         unresolved_reason="工件与生成脚本均不在本（TensorKnowledge）工作树，本工序只能登记"
                           "「出处声明」本身，无法打开工件逐值核对；不标 verified"),
    dict(claim_id="C02-error-table-honest-no-cosmetic",
         text="§⑥ 对 3 项误差 >3% 的指标显式标注「否」，未以口径调整粉饰",
         status="supported",
         quotes=["| 族判决功效内部一致性 0.608（n=20 两维同时显著） | 独立维预测 0.644 | 绝对 0.036 / 相对 5.5% | **否**（Monte-Carlo + 独立维近似，如实列出） |",
                 "| MDE(n) n=40 数值 0.4100 | 解析 0.4529 | −9.5% | **否**（同上，二分网格 + 置换离散所致） |"],
         note="判定依据=原文自身的三处「否」标注与结论句并列出现；只证「如实列出」这一文本事实，"
              "不证数值正确"),
    dict(claim_id="C03-tests-abm-161-green-with-38-guards",
         text="上游自报 tests/abm 161 条全绿，其中 38 条为「文档印值↔工件」溯源守卫",
         status="unresolved",
         quotes=["新增 `tests/abm/test_m8716_provenance.py`（38 条）", "`tests/abm` 161 条全绿"],
         unresolved_reason="测试文件与测试运行记录均不在本工作树，本工序未执行该测试；"
                           "「161 passed」「38 条」为上游自报"),
    dict(claim_id="C04-push-gate-is-root-cause",
         text="工件丢失根因是推送门禁正则整目录滤除 artifacts/runs，而非人工遗忘",
         status="partially-supported",
         quotes=["`_EXCLUDE=^(artifacts?/|runs/|results-/)`", "**根因是门禁不是遗忘**",
                 "会静默滤除证据目录"],
         unresolved_reason="原文两处同义陈述构成文本证据；门禁实现（ops/taskplane/tp_pusher.py）"
                           "不在本工作树，本工序无法复现滤除行为，故不足以上升为 supported"),
]


def build_locator(md: str, quote: str) -> dict:
    n = md.count(quote)
    if n != 1:
        raise SystemExit(f"FATAL: evidence quote not unique/found ({n} hits): {quote[:60]!r}")
    start = md.index(quote)
    start_line = md.count("\n", 0, start)
    return dict(method="char_span", start_char=start, end_char=start + len(quote),
                start_line=start_line, end_line=start_line + quote.count("\n"),
                quote=quote, unique=True)


def main() -> int:
    md = (RUN_DIR / f"report_{REPORT_ID}.md").read_text()
    out = []
    for c in CLAIMS:
        ev = [dict(quote=q, source_field="markdown", locator=build_locator(md, q))
              for q in c["quotes"]]
        item = dict(claim_id=c["claim_id"], text=c["text"], status=c["status"], evidence=ev,
                    source_hash="sha256:" + hashlib.sha256(md.encode()).hexdigest(),
                    verified=False)
        if c.get("unresolved_reason"):
            item["unresolved_reason"] = c["unresolved_reason"]
        if c.get("note"):
            item["note"] = c["note"]
        out.append(item)
    (RUN_DIR / "claims_11478.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps(dict(claims=len(out),
                          by_status={s: sum(1 for c in out if c["status"] == s)
                                     for s in sorted({c["status"] for c in out})}),
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())