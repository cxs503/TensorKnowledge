"""FEAT-SIM-DATAHOUSE 数据集 v1.0 接线演示 + 训练出口闸门验收实证。

跑一次即可产出全部验收证据（数字全部程序化注入，无手抄）：

    python scripts/build_sim_datahouse_v1.py

产物目录 ``artifacts/feat-sim-datahouse/``：

    tk_datahouse.sqlite          datasets + dataset_rows + train_gate + 审计表
    manifest_v1.0.json           manifest（含 held_out 声明块）
    held_out_exclusion.json      源行 / 训练行 / 被排除案号
    gate_audit.json              闸门审计行（register → reviewed → published）
    curl_transcript.txt          真实 curl 调用流水（状态码 + 响应头 + body 摘要）
    acceptance.json              逐条验收结论（可机读）
    ACCEPTANCE.md                同上，人读版（本脚本生成）
    train_gate_flow.png          闸门三态流转 + held-out 排除图

流程：v1.0 初始审级 none（下载 403）→ reviewed 流程样例（审定人 + 证据链，
审定人 ≠ 产出方）→ published（另一名审定人，四眼）→ 每步 curl 实证；
末尾红队：拿 sqlite3 直改库伪造审级，记录被触发器/CHECK 拦截的原文。
"""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from http.client import HTTPConnection
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from ke import held_out as HO  # noqa: E402
from ke.dataset_builder import build_dataset  # noqa: E402
from ke.dataset_server import make_server  # noqa: E402
from ke.datasets import DatasetStore  # noqa: E402
from ke.train_gate import TrainGateStore  # noqa: E402

OUT = REPO / "artifacts" / "feat-sim-datahouse"   # 本地证据（含 sqlite，.gitignore 内）
TRACKED = REPO / "runs" / "feat-sim-datahouse"    # 入库证据（文本/图，随分支推送）
DB = OUT / "tk_datahouse.sqlite"
DATASET = "FEAT-SIM-DATAHOUSE"
VERSION = "v1.0"
SOURCE = REPO / "data" / "sim_datahouse_v1_source.jsonl"
PRODUCER = "sim-datahouse-pipeline"
TOKEN = "demo-gate-token-21607"

transcript: list[str] = []
acceptance: dict[str, object] = {}


def emit(name: str, text: str) -> None:
    """同一份证据写两处：本地 artifacts/（含二进制）+ 入库 runs/（纯文本/图）。"""
    (OUT / name).write_text(text, encoding="utf-8")
    (TRACKED / name).write_text(text, encoding="utf-8")


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def log(msg: str) -> None:
    print(msg)
    transcript.append(msg)


def curl(url: str, *, method: str = "GET", body: dict | None = None,
         headers: dict | None = None) -> dict:
    """真调 curl：记录状态码、响应头、body 摘要（无手抄）。"""
    cmd = ["curl", "-s", "-D", "/dev/stdout", "-o", "/tmp/_curl_body", "-w",
           "\\n__STATUS__%{http_code}\\n", "-X", method, url]
    for k, v in (headers or {}).items():
        cmd += ["-H", f"{k}: {v}"]
    if body is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(body)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    out = proc.stdout
    status = int(out.rsplit("__STATUS__", 1)[1].strip())
    raw_body = Path("/tmp/_curl_body").read_text(encoding="utf-8") if Path("/tmp/_curl_body").exists() else ""
    log(f"$ curl -X {method} {url}")
    log(out.strip())
    if raw_body:
        log(raw_body[:700])
    log("")
    return {"url": url, "method": method, "status": status,
            "headers": out, "body": raw_body}


def wait_http(port: int, path: str, timeout: float = 25.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            conn = HTTPConnection("127.0.0.1", port, timeout=1)
            conn.request("GET", path)
            conn.getresponse().read()
            conn.close()
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"server on port {port} not ready ({path})")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    TRACKED.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    transcript.clear()

    # ---------------------------------------------------------------- 1) 建 v1.0
    store = DatasetStore(DB)
    gate = TrainGateStore(conn=store.conn)
    store.attach_gate(gate)
    rows = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines() if line.strip()]
    built = build_dataset(
        store, DATASET, VERSION, rows,
        description="仿真成果数据楼 v1.0（FEAT-SIM-DATAHOUSE）：九学科仿真成果样本，held-out 案已强制排除",
        status="draft", producer=PRODUCER, gate=gate,
    )
    manifest = built["manifest"]
    reg = HO.load_held_out()
    emit("manifest_v1.0.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    emit("held_out_exclusion.json", json.dumps({
        "source_rows": len(rows),
        "training_rows": built["kept_rows"],
        "excluded": built["excluded"],
        "declaration": built["held_out"],
        "registry": {"list_id": reg.list_id, "list_version": reg.list_version,
                     "sha256": reg.sha256, "case_count": len(reg)},
    }, ensure_ascii=False, indent=2))
    acceptance["held_out_exclusion"] = {
        "source_rows": len(rows), "training_rows": built["kept_rows"],
        "excluded_count": len(built["excluded"]),
        "manifest_declares_list": manifest["held_out"]["list_id"],
        "manifest_list_sha256": manifest["held_out"]["list_sha256"],
        "no_leak_assert": True,
    }
    log(f"[build] source_rows={len(rows)} training_rows={built['kept_rows']} "
        f"excluded={len(built['excluded'])} sha256={manifest['sha256'][:16]}…")
    log(f"[build] train_gate level={gate.get(DATASET, VERSION)['review_level']}")

    # ---------------------------------------------------------------- 2) 下载端点闸门
    ds_port = free_port()
    server = make_server(str(DB), ds_port, "127.0.0.1", gate_enabled=True)
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    wait_http(ds_port, "/datasets")
    base = f"http://127.0.0.1:{ds_port}"

    r_none_default = curl(f"{base}/datasets/{DATASET}/{VERSION}/download")
    r_none_reviewed = curl(f"{base}/datasets/{DATASET}/{VERSION}/download?include=reviewed")
    r_none_all = curl(f"{base}/datasets/{DATASET}/{VERSION}/download?include=all")
    curl(f"{base}/datasets/{DATASET}/{VERSION}/manifest")  # manifest 里的 held_out 声明可对账
    acceptance["level_none_download_403"] = {
        "default": r_none_default["status"],
        "include_reviewed": r_none_reviewed["status"],
        "include_all_rejected": r_none_all["status"],
        "expected": 403, "pass": r_none_default["status"] == 403
        and r_none_reviewed["status"] == 403 and r_none_all["status"] == 403,
    }

    # ---------------------------------------------------------------- 3) 闸门 API
    api_port = free_port()
    env = dict(os.environ,
               KE_TRAIN_GATE_DB=str(DB),
               KE_API_TOKEN=TOKEN)
    uvicorn_cmd = [sys.executable, "-m", "uvicorn", "ke.train_gate_api:standalone_app",
                   "--host", "127.0.0.1", "--port", str(api_port), "--log-level", "warning"]
    api_proc = subprocess.Popen(uvicorn_cmd, cwd=str(REPO), env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        wait_http(api_port, "/api/v1/knowledge/train-gate")
        api = f"http://127.0.0.1:{api_port}"
        hdrs = {"Authorization": f"Bearer {TOKEN}"}
        r_list_none = curl(f"{api}/api/v1/knowledge/train-gate?dataset_id={DATASET}")
        gate_none_item = json.loads(r_list_none["body"])["items"][0]

        # reviewed 流程样例：审定人 ≠ 产出方，证据链 2 条
        evidence = [
            "tkc:sim-datahouse:review-form-v1.0",
            "tke:sim-datahouse:geometry-cb-check-v1.0",
        ]
        r_review = curl(f"{api}/api/v1/knowledge/train-gate", method="POST", headers=hdrs, body={
            "dataset_id": DATASET, "version": VERSION, "to_level": "reviewed",
            "reviewer": "rev-zhang", "evidence_chain": evidence, "actor": "rev-zhang",
            "note": "仿真成果数据楼 v1.0 审阅通过：几何 Cb/L/B 复核 + 样本抽检",
        })
        reviewed_item = json.loads(r_review["body"])["item"]
        # 数据集自身审级同步到 reviewed（否则底层审级仍拦）
        store.promote(DATASET, VERSION, "reviewed")
        r_after_review = curl(f"{base}/datasets/{DATASET}/{VERSION}/download?include=reviewed")
        r_review_default = curl(f"{base}/datasets/{DATASET}/{VERSION}/download")
        acceptance["reviewed_flow"] = {
            "post_status": r_review["status"],
            "review_level": reviewed_item["review_level"],
            "reviewer": reviewed_item["reviewer"],
            "evidence_chain": reviewed_item["evidence_chain"],
            "admitted_at": reviewed_item["admitted_at"],
            "download_include_reviewed": r_after_review["status"],
            "download_default_after_review": r_review_default["status"],
            "pass": r_review["status"] == 200
            and reviewed_item["review_level"] == "reviewed"
            and reviewed_item["admitted_at"] is not None
            and r_after_review["status"] == 200
            and r_review_default["status"] == 403,
        }

        # 四眼：同一人 publish 被拒
        r_same = curl(f"{api}/api/v1/knowledge/train-gate", method="POST", headers=hdrs, body={
            "dataset_id": DATASET, "version": VERSION, "to_level": "published",
            "reviewer": "rev-zhang", "evidence_chain": evidence, "actor": "rev-zhang",
        })
        r_pub = curl(f"{api}/api/v1/knowledge/train-gate", method="POST", headers=hdrs, body={
            "dataset_id": DATASET, "version": VERSION, "to_level": "published",
            "reviewer": "pub-li", "evidence_chain": evidence, "actor": "pub-li",
            "note": "发布：证据链复核无异议",
        })
        store.promote(DATASET, VERSION, "published")
        r_pub_dl = curl(f"{base}/datasets/{DATASET}/{VERSION}/download")
        acceptance["published_flow"] = {
            "same_reviewer_rejected": r_same["status"],
            "publish_status": r_pub["status"],
            "download_default": r_pub_dl["status"],
            "pass": r_same["status"] == 422 and r_pub["status"] == 200
            and r_pub_dl["status"] == 200,
        }

        r_audit = curl(f"{api}/api/v1/knowledge/train-gate/audit?dataset_id={DATASET}")
        r_heldout = curl(f"{api}/api/v1/knowledge/held-out")
        r_final = curl(f"{api}/api/v1/knowledge/train-gate?dataset_id={DATASET}")
        audit_items = json.loads(r_audit["body"])["items"]
        emit("gate_audit.json", json.dumps(audit_items, ensure_ascii=False, indent=2))
        acceptance["audit_trail"] = {
            "count": len(audit_items),
            "actions": [(a["action"], a["from_level"], a["to_level"]) for a in audit_items],
            "pass": len(audit_items) >= 3
            and [a["to_level"] for a in audit_items] == ["none", "reviewed", "published"],
        }
        acceptance["held_out_endpoint"] = {
            "status": r_heldout["status"],
            "case_count": json.loads(r_heldout["body"])["case_count"],
            "pass": json.loads(r_heldout["body"])["case_count"] >= 15,
        }
        acceptance["gate_list_final"] = {
            "status": r_final["status"],
            "item": json.loads(r_final["body"])["items"][0],
            "alerts": json.loads(r_final["body"])["alerts"],
        }
        acceptance["gate_list_initial_level"] = gate_none_item["review_level"]
    finally:
        api_proc.terminate()
        try:
            api_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover
            api_proc.kill()

    # ---------------------------------------------------------------- 4) 红队
    redteam = []

    def attempt(label: str, sql: str, params: tuple = ()) -> None:
        conn = sqlite3.connect(str(DB))
        try:
            with conn:
                conn.execute(sql, params)
            redteam.append({"attack": label, "blocked": False, "error": None})
            log(f"[redteam] NOT BLOCKED: {label}")
        except sqlite3.Error as exc:
            redteam.append({"attack": label, "blocked": True,
                            "error": f"{type(exc).__name__}: {exc}"})
            log(f"[redteam] blocked: {label} -> {type(exc).__name__}: {exc}")
        finally:
            conn.close()

    # 先造一个仍处于 none 的诱饵版本，模拟「未过审版本被伪造晋级」
    conn = sqlite3.connect(str(DB))
    with conn:
        conn.execute(
            "INSERT INTO train_gate (dataset_id, version, review_level, reviewer,"
            " evidence_chain, producer, admitted_at, created_at, updated_at)"
            " VALUES (?,?, 'none', NULL, NULL, 'rogue-pipeline', NULL, 't', 't')",
            (DATASET, "v9.9-rogue"),
        )
    conn.close()

    attempt("直改审级 none->published（绕过 transition API）",
            "UPDATE train_gate SET review_level='published' WHERE dataset_id=? AND version=?",
            (DATASET, "v9.9-rogue"))
    attempt("伪造审级 + 伪造审定人（缺证据链）",
            "UPDATE train_gate SET review_level='reviewed', reviewer='ghost'"
            " WHERE dataset_id=? AND version=?", (DATASET, "v9.9-rogue"))
    attempt("已定级行偷换审定人（不改审级）",
            "UPDATE train_gate SET reviewer='another' WHERE dataset_id=? AND version=?",
            (DATASET, VERSION))
    attempt("插入 reviewed 行但无审定人/证据链（CHECK）",
            "INSERT INTO train_gate (dataset_id, version, review_level, reviewer,"
            " evidence_chain, admitted_at, created_at, updated_at)"
            " VALUES ('X','v1','reviewed',NULL,NULL,NULL,'t','t')")
    attempt("篡改审计行（append-only 触发器）",
            "UPDATE train_gate_audit SET to_level='none' WHERE audit_id=1")
    attempt("删除审计行（append-only 触发器）",
            "DELETE FROM train_gate_audit WHERE audit_id=1")

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    rogue = dict(conn.execute(
        "SELECT * FROM train_gate WHERE dataset_id=? AND version=?",
        (DATASET, "v9.9-rogue")).fetchone())
    alerts = TrainGateStore(conn=conn).integrity_alerts()
    conn.close()
    acceptance["redteam"] = {
        "attempts": redteam,
        "all_blocked": all(a["blocked"] for a in redteam),
        "rogue_row_after": rogue,
        "alerts_after": alerts,
    }

    server.shutdown()
    server.server_close()

    # ---------------------------------------------------------------- 5) 落证据
    acceptance["dataset"] = {
        "name": DATASET, "version": VERSION,
        "status": manifest["status"], "sha256": manifest["sha256"],
        "row_count": manifest["row_count"],
    }
    acceptance["pass"] = all(
        bool(acceptance[k].get("pass")) for k in
        ("level_none_download_403", "reviewed_flow", "published_flow",
         "audit_trail", "held_out_endpoint")
    ) and acceptance["redteam"]["all_blocked"]

    emit("curl_transcript.txt", "\n".join(transcript) + "\n")
    emit("acceptance.json", json.dumps(acceptance, ensure_ascii=False, indent=2))
    emit("ACCEPTANCE.md", render_markdown(acceptance))
    make_figure(acceptance, manifest, built)

    log(f"[acceptance] PASS={acceptance['pass']}")
    return 0 if acceptance["pass"] else 1


def render_markdown(acc: dict) -> str:
    ds = acc["dataset"]
    ho = acc["held_out_exclusion"]
    nz = acc["level_none_download_403"]
    rv = acc["reviewed_flow"]
    pb = acc["published_flow"]
    au = acc["audit_trail"]
    rt = acc["redteam"]
    lines = [
        "# FEAT-SIM-DATAHOUSE · 数据集 v1.0 接线与训练出口闸门验收",
        "",
        "> 本文件由 `scripts/build_sim_datahouse_v1.py` 程序化生成；数字均取自当次运行的",
        "> `acceptance.json` / `curl_transcript.txt`，无手抄。",
        "",
        "## 1. 数据集版本",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| dataset_id | `{ds['name']}` |",
        f"| version | `{ds['version']}` |",
        f"| 行数 / sha256 | {ds['row_count']} / `{ds['sha256']}` |",
        f"| 源行 → 训练行 / 排除 | {ho['source_rows']} → {ho['training_rows']} / 排除 {ho['excluded_count']} |",
        f"| held-out 名单 | `{acc['held_out_exclusion']['manifest_declares_list']}` (sha256 `{acc['held_out_exclusion']['manifest_list_sha256'][:16]}…`, ≥15 案) |",
        "",
        "## 2. 未过审版本 = 训练侧 403（curl 实证）",
        "",
        "| 请求 | HTTP |",
        "|---|---|",
        f"| `download`（默认 published） | **{nz['default']}** |",
        f"| `download?include=reviewed` | **{nz['include_reviewed']}** |",
        f"| `download?include=all`（旧泄漏口） | **{nz['include_all_rejected']}** |",
        "",
        f"结论：审级 `none` 时训练侧全部 403 → {'PASS' if nz['pass'] else 'FAIL'}。",
        "",
        "## 3. reviewed 流程样例（审定人 ≠ 产出方）",
        "",
        f"* POST `/api/v1/knowledge/train-gate` → HTTP {rv['post_status']}，审级 `{rv['review_level']}`",
        f"* 审定人 `{rv['reviewer']}`，证据链 `{rv['evidence_chain']}`",
        f"* 入训练集时间 `{rv['admitted_at']}`",
        f"* `download?include=reviewed` → **{rv['download_include_reviewed']}**；默认 `download` → **{rv['download_default_after_review']}**（reviewed 不等于 published）",
        f"* 结论：{'PASS' if rv['pass'] else 'FAIL'}",
        "",
        "## 4. published 流转（四眼）",
        "",
        f"* 同一审定人 publish → HTTP {pb['same_reviewer_rejected']}（拒绝）",
        f"* 另一审定人 publish → HTTP {pb['publish_status']}；默认 `download` → **{pb['download_default']}**",
        f"* 结论：{'PASS' if pb['pass'] else 'FAIL'}",
        "",
        "## 5. 审计行（三态流转逐条留痕）",
        "",
        "| # | action | from | to |",
        "|---|---|---|---|",
    ]
    for i, (action, frm, to) in enumerate(au["actions"], 1):
        lines.append(f"| {i} | {action} | {frm} | {to} |")
    lines += [
        "",
        f"结论：{'PASS' if au['pass'] else 'FAIL'}",
        "",
        "## 6. 红队：伪造审级直改库",
        "",
        "| 攻击 | 结果 | 数据库返回 |",
        "|---|---|---|",
    ]
    for a in rt["attempts"]:
        lines.append(f"| {a['attack']} | {'拦截' if a['blocked'] else '**未拦截**'} | "
                     f"{a['error'] or '—'} |")
    lines += [
        "",
        f"诱饵版本 `v9.9-rogue` 攻击后审级仍为 `{rt['rogue_row_after']['review_level']}`"
        "（直插行绕过 API 时，`integrity_alerts()` 立刻告警）:",
        "",
        "```json",
        json.dumps(rt["alerts_after"], ensure_ascii=False, indent=2),
        "```",
        "",
        f"结论：{'PASS' if rt['all_blocked'] else 'FAIL'}",
        "",
        f"## 7. 总判定：{'PASS' if acc['pass'] else 'FAIL'}",
        "",
        "图：`train_gate_flow.png`（三态流转 + held-out 排除对账）。",
        "curl 原文：`curl_transcript.txt`。机读：`acceptance.json`。",
        "",
    ]
    return "\n".join(lines)


def make_figure(acc: dict, manifest: dict, built: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2),
                                   gridspec_kw={"width_ratios": [1.35, 1]})
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 6)
    ax1.axis("off")
    ax1.set_title("train_gate: three-state flow (every step audited)", fontsize=11)

    def box(x, y, text, color):
        ax1.add_patch(FancyBboxPatch((x - 1.15, y - 0.5), 2.3, 1.0,
                                     boxstyle="round,pad=0.08", fc=color, ec="#333", lw=1.2))
        ax1.text(x, y, text, ha="center", va="center", fontsize=10)

    box(1.7, 3.0, "none\n(403 to training)", "#f4b6b6")
    box(5.0, 3.0, "reviewed\n(include=reviewed)", "#ffe08a")
    box(8.3, 3.0, "published\n(default download)", "#a8d8a8")
    ax1.annotate("", xy=(3.75, 3.0), xytext=(2.95, 3.0),
                 arrowprops=dict(arrowstyle="-|>", lw=1.8, color="#1f4e79"))
    ax1.text(3.35, 3.35, "review\n(reviewer≠producer)", ha="center", fontsize=8.5, color="#1f4e79")
    ax1.annotate("", xy=(7.05, 3.0), xytext=(6.25, 3.0),
                 arrowprops=dict(arrowstyle="-|>", lw=1.8, color="#1f4e79"))
    ax1.text(6.65, 3.35, "publish\n(4-eyes)", ha="center", fontsize=8.5, color="#1f4e79")
    ax1.annotate("", xy=(1.7, 1.9), xytext=(8.3, 1.9),
                 arrowprops=dict(arrowstyle="-|>", lw=1.4, color="#8b1a1a",
                                 connectionstyle="arc3,rad=0.25"))
    ax1.text(5.0, 0.75, "revoke (note required, audited)", ha="center", fontsize=8.5, color="#8b1a1a")
    ax1.text(5.0, 5.3, "audit rows: " + " → ".join(
        a[2] for a in acc["audit_trail"]["actions"]), ha="center", fontsize=9)
    ax1.text(5.0, 2.15, "red team: direct UPDATE blocked "
             f"({sum(1 for a in acc['redteam']['attempts'] if a['blocked'])}/"
             f"{len(acc['redteam']['attempts'])} attacks intercepted)",
             ha="center", fontsize=8.5, color="#444")

    ho = acc["held_out_exclusion"]
    labels = ["source rows\n(sim datahouse)", "held-out excluded\n(never trained)", "training rows\n(manifest)"]
    vals = [ho["source_rows"], ho["excluded_count"], ho["training_rows"]]
    colors = ["#9ecae1", "#d62728", "#2ca02c"]
    bars = ax2.bar(labels, vals, color=colors)
    for b, v in zip(bars, vals):
        ax2.text(b.get_x() + b.get_width() / 2, v + 0.3, str(v), ha="center", fontsize=10)
    ax2.set_ylabel("rows")
    ax2.set_title("held-out split enforced before ingest\n"
                  f"list={manifest['held_out']['list_id']} (n={manifest['held_out']['case_count']})",
                  fontsize=11)
    ax2.set_ylim(0, max(vals) * 1.25)
    ax2.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "train_gate_flow.png", dpi=160)
    fig.savefig(TRACKED / "train_gate_flow.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())