#!/usr/bin/env python3
"""Build and publish the KF-RESULT report for wp-12563-01.

One-command re-run (after the register script has produced kf_result.json):
    python3 scripts/kf_wp12563_01_publish_report.py

Builds the six-section report body, embeds the KF-RESULT envelope as the
single ```json block, and POSTs it to the platform reports API.
All quotes in the evidence table are pulled from the (already verbatim-
checked) asset manifest - zero hand-typed numbers.
"""
import json
import os
import urllib.request

API_BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(HERE, "docs", "kf", "wp-12563-01")


def http_json(method, path, body=None, token=None):
    req = urllib.request.Request(API_BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    with urllib.request.urlopen(req, data=data, timeout=120) as r:
        return json.loads(r.read().decode())


def q(s, n=96):
    s = s.replace("\n", " / ")
    return s if len(s) <= n else s[:n] + " ..."


def main():
    env = json.load(open(os.path.join(PKG, "kf_result.json"), encoding="utf-8"))
    man = env["outputs"]["asset_manifest.json"]
    prov = man["provenance"]
    assets = man["assets"]

    ev_rows = []
    for a in assets:
        loc = a["locator"]
        ev_rows.append("| %s | %s | `%s` | L%d-L%d, char %d-%d, occ=%d |" % (
            a["asset_id"], a["asset_class"],
            q(a["label"]),
            loc["start_line"], loc["end_line"],
            loc["start_char"], loc["end_char"], loc["occurrences"]))
    ev_table = "\n".join(ev_rows)

    body = """# KF-RESULT wp-12563-01

## 1. What this step did

Executed **01-asset-registration** for report_id=12563 (`tensor://reports/12563`,
scenario_key=`lbm_d3q27_poiseuille_stokes`): confirmed the byte hash of the report's
`markdown` field against the contract, and registered the source asset plus every
figure / code / data / table / block reference **named verbatim in the report body**
(3 figures, 4 code, 2 data, 1 code pointer, 2 blocks, 12 tables = 25 assets), each
with a resolvable verbatim-quote locator. **No extraction, no classification, no
claim generation** (claims = empty array per contract objective.classify_report_type=false);
**nothing is marked verified** (verification is computed by the platform gate).

## 2. How it was done (steps / tools / key settings)

1. `POST /api/v1/auth/login` (Bearer) -> `GET /api/v1/tensor/reports/12563`, take the
   `markdown` field (the only source field this package may use).
2. Recomputed `hashlib.sha256(markdown.encode('utf-8'))` locally and compared with the
   contract `source_hash`; compared `len(markdown)` with contract `chars`; compared
   title / scenario_key with the contract.
3. Every asset quote was located with `str.find` / `str.count` on the **fetched**
   markdown; character spans and line numbers are computed programmatically
   (zero hand-typed offsets). A missing quote aborts the script.
4. Independent re-check from on-disk `source.md`: quotes verbatim, spans reproduce
   quotes, line numbers correct, asset_ids unique, claims empty, hash consistent.
5. Envelope validated against `schemas/kf_result.v1.schema.json` (draft 2020-12).

Key settings: hash object = UTF-8 bytes of the markdown field (16033 bytes /
15874 code points; difference from CJK multi-byte); `chars` semantics = python str
length (code points).

## 3. Deliverables (paths inside the worktree)

| file | key points |
|---|---|
| `docs/kf/wp-12563-01/asset_manifest.json` | contract-declared output: 25 assets + provenance + counts + integrity |
| `docs/kf/wp-12563-01/kf_result.json` | platform envelope (package_id/task_type/report_id/provenance/outputs/claims=[]) |
| `docs/kf/wp-12563-01/locator_check.json` | 25 locator re-check records (found/occurrences/span/lines) |
| `docs/kf/wp-12563-01/source.md` | fetched markdown original (hash object) |
| `docs/kf/wp-12563-01/sha256.txt` | recomputed hash record |
| `scripts/kf_wp12563_01_register.py` | one-command re-run generator (fetch -> verify hash -> build manifest -> schema check) |
| `scripts/kf_wp12563_01_publish_report.py` | this report's build/publish script |

## 4. Evidence locator table (claim/field -> verbatim quote from report 12563 markdown)

| asset | class | label | locator |
|---|---|---|---|
""" + ev_table + """

Identity fields: recomputed sha256 `e6097b4c6c824f48a253303de23e66a9a1c16f0fdcbcf163683158e3bd5cd816`
= contract value; chars 15874 = contract value; title and scenario_key match the
contract. Report identity line (L6): `*Repo `TensorLBM` @ `7efbcfc0808b` (branch
`agent/m10870`), torch 2.7.1 - loongarch64 - 128 cores - generated 2026-11-10T21:43:08Z*`.

## 5. Notes and limitations

- The 24 non-source assets are `referenced_unresolved`: the quote resolves verbatim
  inside the registered markdown, but the file bodies (PNG / code / JSON) are not part
  of the report record and no artifact endpoint serves their bytes - this step
  registers references only; it does not fetch bytes or verify content.
- A10 (unit test pinning the wall position): the report states the test exists but
  does not name the file; registered as declared-only with the statement as locator.
- A11's commit is the short prefix `7efbcfc0808b` as printed in the report; the full
  40-hex sha is not stated in the report.
- A06/A12 share the first line of the Reproduce block (same span, two asset views);
  noted in integrity.
- No computation and no figures in this step: pure registration task, no field
  quantities and no comparison curves, hence figures=[] (reason = task type).
- Not done: any read/write of other report_ids; upstream artifacts untouched;
  .git config untouched.

## 6. Self-check (item-by-item against acceptance)

| acceptance | result | basis |
|---|---|---|
| valid_json | PASS | `kf_result.json` written by json.dump, re-loaded with json.load |
| schema_pass | PASS | jsonschema validation against `schemas/kf_result.v1.schema.json` |
| source_locator_resolvable | PASS | 25/25 quotes verbatim-hit, spans reproduce quotes (locator_check.json) |
| source_hash_matches | PASS | recomputed `e6097b4c...cd816` = contract value (hard compare in script, exits on mismatch) |
| no_duplicate_ids | PASS | 25 asset_ids still 25 after dedup (assert in script + independent re-check) |
| all_claims_have_evidence_or_explicit_unresolved_status | PASS | claims=[] (empty array allowed by contract); all 24 non-source assets carry an explicit resolution status |

honest-FAIL items: none. All four identity checks (hash / chars / title / scenario_key) passed.

repro_cmd: `python3 scripts/kf_wp12563_01_register.py && python3 scripts/kf_wp12563_01_publish_report.py`

```json
"""
    body += json.dumps(env, ensure_ascii=False, indent=2) + "\n```\n"

    assert body.count("```json") == 1, "must contain exactly one json block"
    assert body.count("```") % 2 == 0

    payload = {
        "title": "KF-RESULT wp-12563-01",
        "summary": "wp-12563-01 (01-asset-registration) for report 12563: sha256 of "
                   "the markdown field recomputed and matched the contract "
                   "(e6097b4c...cd816, 15874 chars); 25 assets registered with "
                   "verbatim-checked locators; claims empty by contract; nothing "
                   "marked verified.",
        "scenario_key": "lbm_d3q27_poiseuille_stokes",
        "mission_id": 15748,
        "tags": ["kf-wp:wp-12563-01", "KF", "asset-registration", "D3Q27", "TensorLBM"],
        "markdown": body,
        "figures": [],
    }
    with open("/tmp/report.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    if os.environ.get("KF_PUBLISH") != "1":
        print("dry-run: /tmp/report.json written, not published (set KF_PUBLISH=1)")
        print("report body chars:", len(body))
        return
    login = http_json("POST", "/auth/login", {"username": USER, "password": PASS})
    resp = http_json("POST", "/tensor/reports", payload, token=login["access_token"])
    print("published report id:", resp.get("id"), "status:", resp.get("status"))
    print("report body chars:", len(body))


if __name__ == "__main__":
    main()
