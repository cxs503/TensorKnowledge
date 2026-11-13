#!/usr/bin/env python3
"""Build /tmp/report.json for the KF-RESULT report post (wp-11557-01)."""
import json

md = open("docs/kf/wp-11557-01/KF-RESULT-wp-11557-01.md").read()
payload = {
    "title": "KF-RESULT wp-11557-01",
    "summary": "01-asset-registration 工序完成：report_id=11557（DEM多面体颗粒与冰-结构混合模式失效验证面, P180W2-N05, 1953字符）markdown 字节哈希本地重算与契约一致（sha256:471f8b21…b1cb3）；登记 11 项源资产（9 resolved_in_source / 1 referenced_unresolved / 1 declared_absent），claims=[]（契约允许，不做抽取），未标记 verified。8 项 acceptance 自检全过。",
    "scenario_key": "P180W2-N05",
    "mission_id": 15725,
    "tags": ["kf-wp:wp-11557-01", "asset-registration", "report-11557", "DEM", "ice-structure"],
    "markdown": md,
    "figures": [],
}
json.dump(payload, open("/tmp/report.json", "w"), ensure_ascii=False)
print("payload ready:", len(md), "chars markdown")
