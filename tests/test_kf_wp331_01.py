"""wp-331-01（01-asset-registration）交付物的离线验收测试。

全部离线：只读工作树内的产物（manifest / 源快照 / schema / 报告 md），
不访问平台、不依赖网络，因此门重跑与评审者都能复算。

覆盖契约 acceptance（包 contract 见工单）：
  valid_json / schema_pass / source_locator_resolvable /
  source_hash_matches / no_duplicate_ids /
  all_claims_have_evidence_or_explicit_unresolved_status

以及本工序自加的不变量：单一 json 结果块、claims 必须为空（不抽取）、
未解析资产必须带理由、引文长度过平台门限、报告标题与 tag 规范。
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "kf" / "wp-331-01"
MANIFEST = ART / "asset_manifest.json"
SNAPSHOT = ART / "source_snapshot" / "report_331.markdown"
SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
REPORT_MD = ROOT / "docs" / "kf" / "wp-331-01-asset-registration.md"

PACKAGE_ID = "wp-331-01"
REPORT_ID = "331"
CONTRACT_HASH = "sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717"
MIN_QUOTE_CHARS = 12   # 平台门 kf gates.min_quote_chars

_JSON_BLOCK = re.compile(r"```json\s*\n(.*?)```", re.S)


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def snapshot() -> str:
    return SNAPSHOT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def envelope() -> dict:
    blocks = _JSON_BLOCK.findall(REPORT_MD.read_text(encoding="utf-8"))
    assert len(blocks) == 1, f"report must carry exactly one ```json block, got {len(blocks)}"
    return json.loads(blocks[0])


# --------------------------------------------------------------- source hash
def test_snapshot_matches_contract_hash(snapshot):
    assert _sha(snapshot) == CONTRACT_HASH


def test_manifest_pins_same_hash(manifest, snapshot):
    src = manifest["source"]
    assert src["source_hash"] == CONTRACT_HASH
    assert src["expected_source_hash"] == CONTRACT_HASH
    assert src["hash_matches"] is True
    # 记账口径与源一致（字符/字节都不许漂）
    assert src["chars"] == len(snapshot)
    assert src["bytes_utf8"] == len(snapshot.encode("utf-8"))
    assert src["report_id"] == REPORT_ID
    assert src["source_field"] == "markdown"
    assert src["source_uri"] == f"tensor://reports/{REPORT_ID}"


def test_envelope_provenance_hash_matches_source(envelope, snapshot):
    prov = envelope["provenance"]
    assert prov["source_hash"] == _sha(snapshot) == CONTRACT_HASH
    assert prov["source_field"] == "markdown"


# ------------------------------------------------------------------ structure
def test_outputs_carry_the_manifest(envelope, manifest):
    assert envelope["outputs"]["asset_manifest.json"] == manifest


def test_envelope_identity(envelope):
    assert envelope["package_id"] == PACKAGE_ID
    assert envelope["report_id"] == REPORT_ID
    assert str(envelope["task_type"]).split("-")[0] == "01"


def test_schema_pass(envelope):
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(
        json.loads(SCHEMA.read_text(encoding="utf-8")))
    errs = sorted(validator.iter_errors(envelope), key=lambda e: list(e.path))
    assert not errs, [(list(e.path), e.message) for e in errs]


# ------------------------------------------------------------- locators / ids
def test_asset_locator_quotes_resolve_verbatim(manifest, snapshot):
    for a in manifest["assets"]:
        loc = a.get("locator") or {}
        quote = loc.get("quote")
        if quote is None:
            assert loc.get("source_field") == "record", a["asset_id"]
            continue
        assert len(quote) >= MIN_QUOTE_CHARS, (a["asset_id"], len(quote))
        assert quote in snapshot, (a["asset_id"], quote)


def test_locator_check_block_agrees_with_snapshot(manifest, snapshot):
    checks = manifest["locator_checks"]
    assert checks, "locator_checks must not be empty"
    raw = snapshot.encode("utf-8")
    for key, rec in checks.items():
        assert rec["resolvable_in_markdown"] is True, key
        assert record_ok(rec["quote"], raw, rec["offset_bytes"]), key


def record_ok(quote: str, raw: bytes, offset: int) -> bool:
    return offset >= 0 and raw[offset:offset + len(quote.encode("utf-8"))] == quote.encode("utf-8")


def test_no_duplicate_asset_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(REPORT_ID in i for i in ids), ids      # 命名空间带 report_id，跨包不会撞
    assert not manifest.get("claims"), "工序 01 不得抽取 claim"


def test_every_asset_has_status_and_unresolved_have_reason(manifest):
    resolved, unresolved = [], []
    for a in manifest["assets"]:
        assert a["status"], a["asset_id"]
        if a["status"] == "resolved":
            resolved.append(a)
        else:
            unresolved.append(a)
            assert (a.get("unresolved_reason") or "").strip(), a["asset_id"]
    listed = {u["asset_id"] for u in manifest["unresolved"]}
    assert listed == {a["asset_id"] for a in unresolved}
    counts = manifest["asset_status_counts"]
    assert counts.get("resolved", 0) == len(resolved)
    assert sum(counts.values()) == len(manifest["assets"])


def test_no_claim_is_marked_verified(manifest, envelope):
    """verification 由平台门计算：本工序不得产出任何 verified 状态。"""
    assert envelope.get("claims") == []
    for c in envelope.get("claims") or []:
        assert c.get("status") != "verified"
    assert manifest["scope"]["extraction_performed"] is False
    assert manifest["scope"]["claims_emitted"] == 0


# --------------------------------------------------------------- report layer
def test_report_title_and_scope_statement():
    md = REPORT_MD.read_text(encoding="utf-8")
    assert md.splitlines()[0].strip() == f"# KF-RESULT {PACKAGE_ID}"
    for section in ("①", "②", "③", "④", "⑤", "⑥"):
        assert f"## {section}" in md, section
    assert "repro" in md.lower() or "复现命令" in md


def test_report_quotes_are_traceable(manifest, snapshot):
    """报告正文里出现的每段登记引文，必须在源快照里逐字存在（零手抄的机器证据）。"""
    md = REPORT_MD.read_text(encoding="utf-8")
    for rec in manifest["locator_checks"].values():
        assert rec["quote"] in snapshot
        assert rec["quote"] in md, rec["quote"][:40]

# ------------------------------------------------------------- gate dry-run
DRYRUN = ART / "gate_dryrun.json"


def test_gate_dryrun_passed_with_platform_gate_code():
    """工作树内用平台同一份门代码干跑：结果必须是全门通过，且 schema 副本与门用的一致。"""
    if not DRYRUN.is_file():
        pytest.skip("gate_dryrun.json 未生成（本机无平台门代码）")
    rec = json.loads(DRYRUN.read_text(encoding="utf-8"))
    if rec.get("status") != "ok":
        pytest.skip(f"dry-run degraded: {rec.get('reason')}")
    assert rec["gates_ok"] is True
    assert all(g["ok"] for g in rec["gates"]), [g["gate"] for g in rec["gates"] if not g["ok"]]
    assert rec["contract_hash_matches_source"] is True
    assert rec["payload_equals_envelope_file"] is True
    assert rec["extract_payload_error"] is None
    # 门用的 schema 必须与仓库内副本逐字节相同，否则"离线 schema_pass"证明的是别的文件
    assert rec["schema_sha256"] == hashlib.sha256(SCHEMA.read_bytes()).hexdigest()
