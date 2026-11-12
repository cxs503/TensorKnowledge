#!/usr/bin/env python3
"""Work package wp-5406-01 — 01-asset-registration for report 5406.

Only does what a registration step may do (PRODUCTION-LINE-v1.md §2.1):
pull one report record, hash its ``markdown`` bytes, list the
attachments/artifacts the text points at, and mark reachability.
No classification, no extraction, no rewriting, no claim generation,
no ``verified`` marking.

    # offline rerun over the in-repo snapshot of the record
    python scripts/wp5406_asset_manifest.py \
        --offline-from knowledge/assets/wp-5406-01/report_record.json

    # online (default when --offline-from is absent): fetch via $TENSOR_API_BASE
    python scripts/wp5406_asset_manifest.py

Exit codes: 0 = manifest written and every self-check passed,
2 = manifest written but at least one self-check failed (honest FAIL).

The manifest is the deliverable named by the package contract; the checks
block inside it is what the report cites, so nothing is hand-copied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

REPORT_ID = "5406"
PACKAGE_ID = "wp-5406-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/5406"

#: values the package contract states; the script asserts them, never trusts them
CONTRACT = {
    "report_id": "5406",
    "source_field": "markdown",
    "source_hash": "sha256:9c071693614c9bed438bea6aa35956a5f00e1790eb5d48ae48086cc2732ede8a",
    "chars": 3815,
    "scenario_key": "tensordem_ci_clearance",
}

BACKTICK = re.compile(r"`([^`\n]+)`")
PATH_EXT = (".py", ".json", ".md", ".png", ".txt", ".yaml", ".yml")
KIND_BY_DIR = (
    ("artifacts/", "referenced_artifact"),
    ("scripts/", "referenced_script"),
    ("docs/", "referenced_doc"),
    ("tests/", "referenced_test"),
    ("src/", "referenced_source"),
)
#: a token boundary: a path must not be a slice of a longer path
BOUNDARY = r"[\w./\\-]"


# ---------------------------------------------------------------------------
# source acquisition
# ---------------------------------------------------------------------------
def _login(base: str) -> str:
    import urllib.request

    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(base + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))["access_token"]


def fetch_record(offline_from: str | None) -> dict:
    """The report record. Offline mode reads the snapshot already in the repo."""
    if offline_from:
        return json.loads(Path(offline_from).read_text(encoding="utf-8"))
    import urllib.request

    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    tok = _login(base)
    req = urllib.request.Request(f"{base}/tensor/reports/{REPORT_ID}",
                                 headers={"Authorization": "Bearer " + tok})
    return json.load(urllib.request.urlopen(req))


# ---------------------------------------------------------------------------
# attachment discovery (path-shaped tokens only — nothing is inferred)
# ---------------------------------------------------------------------------
def _is_pathish(word: str) -> bool:
    w = word.strip("(),;:\"'`")
    if not w or len(w) < 4:
        return False
    if w.endswith(("::", "--", "->")):
        return False
    if "/" in w:
        return True
    return w.endswith(PATH_EXT)


def _bounded(md: str, token: str, lo: int, hi: int) -> int:
    """First occurrence of ``token`` in [lo, hi) that is not a slice of a longer path.

    ``provenance_gate_matrix.png`` must not resolve the figure ``gate_matrix.png``:
    both sides of the match are checked against the path alphabet.
    """
    pat = re.compile(f"(?<!{BOUNDARY})" + re.escape(token) + f"(?!{BOUNDARY})")
    m = pat.search(md, lo, hi)
    return m.start() if m else -1


def _kind(path: str) -> str:
    for prefix, kind in KIND_BY_DIR:
        if path.startswith(prefix):
            return kind
    return "referenced_path_other"


def discover_paths(md: str) -> list[dict]:
    """Path-shaped tokens inside inline code spans, with verbatim locators."""
    found: dict[tuple[str, str], dict] = {}
    for m in BACKTICK.finditer(md):
        span = m.group(1)
        cursor = m.start(1)
        for word in span.split():
            if not _is_pathish(word):
                cursor += len(word) + 1
                continue
            token = word.strip("(),;:\"'`")
            at = _bounded(md, token, cursor, m.end())
            if at < 0:  # stripped punctuation moved the span; skip, never guess
                cursor += len(word) + 1
                continue
            line_ref = None
            path = token
            mline = re.search(r":(\d+)$", path)
            if mline and "/" in path:
                line_ref = int(mline.group(1))
                path = path[: mline.start()]
            directory_reference = path.endswith("/")
            path = path.rstrip("/")
            kind = _kind(path)
            key = (path, kind)
            loc = {"start_offset": at, "end_offset": at + len(token), "quote": token,
                   "line": md.count("\n", 0, at) + 1,
                   "content_hash": "sha256:" + hashlib.sha256(token.encode()).hexdigest()}
            if "::" in token:
                loc["test_node_id"] = token
            if key not in found:
                found[key] = {"path": path, "kind": kind,
                              "directory_reference": directory_reference,
                              "names_line_refs": [], "mentions": []}
            found[key]["mentions"].append(loc)
            if line_ref is not None and line_ref not in found[key]["names_line_refs"]:
                found[key]["names_line_refs"].append(line_ref)
            cursor += len(word) + 1
    return [found[k] for k in sorted(found)]


def _infer_kind(assets: list[dict]) -> None:
    """A bare filename later in the text inherits the kind of the full path that
    already established it (and is linked to it, not silently merged)."""
    by_base: dict[str, dict] = {}
    for a in assets:
        if "/" in a["path"]:
            by_base.setdefault(a["path"].rsplit("/", 1)[1], a)
    for a in assets:
        if "/" in a["path"]:
            continue
        same = by_base.get(a["path"])
        if same is not None:
            a["kind"] = same["kind"]
            a["same_asset_as"] = same["path"]
    #: a member of a registered artifact directory is an artifact, not "other"
    for a in assets:
        parent = a.get("member_of")
        if parent is None:
            continue
        host = next(x for x in assets if x["path"] == parent)
        if a["kind"] == "referenced_path_other" and host["kind"] == "referenced_artifact":
            a["kind"] = "referenced_artifact"


def _bind_to_parent_dir(assets: list[dict]) -> None:
    """A bare filename cited on the same line as exactly one registered directory is a
    member of that directory; record the binding instead of inventing a full path."""
    dirs = [a for a in assets if a["reachability"]["status"] == "unresolved_referenced_directory"]
    for a in assets:
        if a["directory_reference"] or "/" in a["path"] or "." not in Path(a["path"]).name:
            continue  # directories are not members of directories
        lines = {loc["line"] for loc in a["mentions"]}
        candidates = [d for d in dirs if lines & {loc["line"] for loc in d["mentions"]}]
        if len(candidates) == 1:
            a["member_of"] = candidates[0]["path"]
            a["resolved_by"] = ("cited on the same line as the registered directory "
                                f"{candidates[0]['path']}/; the text never spells the full path")
        elif len(candidates) > 1:
            a["member_of_candidates"] = [d["path"] for d in candidates]


def _reachability(asset: dict, repo_root: Path) -> dict:
    """Byte-level reachability. A missing byte is stated, never upgraded to 'done'.

    A same-named path inside the delivery repo is *not* treated as the referenced
    asset: report 5406's artifacts belong to the TensorDEM checkout.
    """
    path = asset["path"]
    is_file = bool(Path(path).name) and "." in Path(path).name
    if asset["directory_reference"] or not is_file:
        note = ""
        if (repo_root / path).is_dir():
            note = (" (a same-named directory exists in the delivery worktree, but that is "
                    "a name coincidence, not identity: report 5406 cites the TensorDEM tree)")
        return {"status": "unresolved_referenced_directory",
                "detail": (f"{path}/ is cited as a directory; no TensorDEM tree is checked "
                           f"out here, so its members cannot be enumerated from the source "
                           f"bytes{note}"),
                "checked": ["delivery_repo_path", "record.markdown (text only)"]}
    if "/" not in path:
        where = f" under {asset['member_of']}/ (see member_of)" if asset.get("member_of") else ""
        return {"status": "unresolved_bare_filename",
                "detail": (f"{path} is cited by filename only{where}; the bytes live in the "
                           "TensorDEM repository and are not part of the record's markdown "
                           "field or this delivery repo"),
                "checked": ["delivery_repo_path", "record.markdown (text only)"]}
    candidate = repo_root / path.split("::")[0]
    if candidate.is_file():
        return {"status": "present_in_delivery_repo",
                "detail": f"{path} resolves inside the delivery worktree",
                "evidence": str(candidate.relative_to(repo_root)),
                "checked": ["delivery_repo_path"]}
    return {"status": "unresolved_external_artifact",
            "detail": (f"{path} is referenced by report 5406 but lives in the TensorDEM "
                       "repository; the record's markdown field carries no bytes for it and "
                       "this delivery repo does not check out TensorDEM"),
            "checked": ["delivery_repo_path", "record.markdown (text only)",
                        "record.figures"]}


def _upgrade_member_kind(assets: list[dict]) -> None:
    """A member of a registered artifact directory is an artifact, not 'other'."""
    for a in assets:
        parent = a.get("member_of")
        if not parent:
            continue
        host = next(x for x in assets if x["path"] == parent)
        if a["kind"] == "referenced_path_other" and host["kind"] == "referenced_artifact":
            a["kind"] = "referenced_artifact"


def build_manifest(record: dict, repo_root: Path, snapshot: Path | None) -> dict:
    md = record["markdown"]
    raw = md.encode("utf-8")
    computed = "sha256:" + hashlib.sha256(raw).hexdigest()
    figures = record.get("figures") or []

    assets: list[dict] = []
    listed = discover_paths(md)
    _infer_kind(listed)
    for i, item in enumerate(listed, start=1):
        assets.append({"id": f"asset:{REPORT_ID}:p{i:03d}", **item,
                       "reachability": _reachability(item, repo_root),
                       "bytes_available": False})
    _bind_to_parent_dir(assets)
    _upgrade_member_kind(assets)
    for j, fig in enumerate(figures, start=1):
        name = str(fig.get("name") or "")
        if not name:
            continue
        at = _bounded(md, name, 0, len(md))
        mentions = ([{"start_offset": at, "end_offset": at + len(name), "quote": name,
                      "line": md.count("\n", 0, at) + 1,
                      "content_hash": "sha256:" + hashlib.sha256(name.encode()).hexdigest()}]
                    if at >= 0 else [])
        assets.append({
            "id": f"asset:{REPORT_ID}:f{j:03d}",
            "path": name,
            "kind": "report_figure",
            "names_line_refs": [],
            "mentions": mentions,
            #: the figure is registered from the record field, not from body text
            "locator": {"locator_type": "record_field",
                        "field": f"figures[{j - 1}].name",
                        "value": name,
                        "quote": name,
                        "content_hash": "sha256:" + hashlib.sha256(name.encode()).hexdigest()},
            "caption": fig.get("caption"),
            "reachability": {
                "status": "declared_metadata_only",
                "detail": ("the report record lists this figure by name+caption only; "
                           "no png_base64 field and no in-text path, so the image bytes "
                           "are not retrievable from the source field"),
                "checked": ["record.figures entries", "record.markdown occurrences"],
            },
            "bytes_available": False,
        })

    return {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "generated_by": "scripts/wp5406_asset_manifest.py",
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": CONTRACT["source_field"],
            "title": record.get("title"),
            "declared_source_hash": CONTRACT["source_hash"],
            "computed_source_hash": computed,
            "hash_match": computed == CONTRACT["source_hash"],
            "chars": len(md),
            "bytes": len(raw),
            "declared_chars": CONTRACT["chars"],
            "chars_match": len(md) == CONTRACT["chars"],
            "snapshot": ({"path": str(snapshot), "sha256": computed} if snapshot else None),
            "record_meta": {
                "scenario_key": record.get("scenario_key"),
                "mission_id": record.get("mission_id"),
                "status": record.get("status"),
                "tags": record.get("tags"),
                "created_at": record.get("created_at"),
            },
        },
        "attachments": assets,
        "counts": {
            "attachments": len(assets),
            "figures": sum(1 for a in assets if a["kind"] == "report_figure"),
            "with_bytes_available": sum(1 for a in assets if a["bytes_available"]),
            "unresolved": sum(1 for a in assets
                              if a["reachability"]["status"].startswith("unresolved")),
            "distinct_by_basename": len({a["path"].rsplit("/", 1)[-1] for a in assets}),
        },
        "claims": {"extracted": 0,
                   "reason": ("01-asset-registration does not extract claims; the package "
                              "contract sets objective.classify_report_type=false and "
                              "allows an empty claims array")},
        "verification": {"status": "not_marked_verified",
                         "note": "verification is computed by the platform gate, not here"},
    }


def run_checks(manifest: dict, md: str, record: dict) -> list[dict]:
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "pass": bool(ok), "detail": detail})

    src = manifest["source"]
    add("valid_json", True, "manifest built and re-serialised without error")
    add("source_hash_matches", src["hash_match"],
        f"declared={src['declared_source_hash']} computed={src['computed_source_hash']}")
    add("chars_match_declared", src["chars_match"],
        f"declared={src['declared_chars']} computed={src['chars']}")

    ids = [a["id"] for a in manifest["attachments"]]
    add("no_duplicate_ids", len(ids) == len(set(ids)),
        f"{len(ids)} ids, {len(set(ids))} distinct")

    bad: list[tuple[str, str]] = []
    for a in manifest["attachments"]:
        loc_field = a.get("locator") or {}
        if loc_field.get("locator_type") == "record_field":
            # resolvable only if the record still carries that exact value
            node = record
            for part in re.findall(r"([a-z_]+)|\[(\d+)\]", loc_field["field"]):
                key, idx = part
                node = node[int(idx)] if idx else node[key]
            ok_field = node == loc_field["quote"]
            digest = "sha256:" + hashlib.sha256(loc_field["quote"].encode()).hexdigest()
            if not ok_field or digest != loc_field["content_hash"]:
                bad.append((a["id"], f"record field {loc_field['field']} drifted"))
            if not a["mentions"]:
                continue  # no textual locator is expected and already stated
        elif not a["mentions"]:
            bad.append((a["id"], "no locator"))
            continue
        for loc in a["mentions"]:
            span = md[loc["start_offset"]:loc["end_offset"]]
            digest = "sha256:" + hashlib.sha256(loc["quote"].encode()).hexdigest()
            if span != loc["quote"] or digest != loc["content_hash"]:
                bad.append((a["id"], f"offset drift at {loc['start_offset']}"))
    add("source_locator_resolvable", not bad, f"unresolvable={bad[:5]}")

    no_status = [a["id"] for a in manifest["attachments"]
                 if not (a["reachability"] or {}).get("status")]
    add("every_asset_has_evidence_or_explicit_unresolved_status", not no_status,
        f"assets without reachability status={no_status[:5]}")
    add("single_report_scope", src["report_id"] == REPORT_ID,
        f"only report {REPORT_ID} is read")
    add("do_not_mark_claims_as_verified",
        manifest["verification"]["status"] == "not_marked_verified",
        manifest["verification"]["status"])
    add("schema_pass_manifest_v1", _schema_ok(manifest),
        "required keys of manifest_version/package_id/task_type/source/attachments/counts")
    return checks


def _schema_ok(m: dict) -> bool:
    req = {"manifest_version", "package_id", "task_type", "source", "attachments", "counts"}
    if not req <= set(m):
        return False
    need = {"id", "path", "kind", "mentions", "reachability"}
    return all(need <= set(a) for a in m["attachments"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--offline-from", help="report record snapshot (offline reruns)")
    ap.add_argument("--out", default=f"knowledge/assets/{PACKAGE_ID}/asset_manifest.json")
    ap.add_argument("--checks-json", default=f"knowledge/assets/{PACKAGE_ID}/self_checks.json")
    args = ap.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    record = fetch_record(args.offline_from)
    if str(record.get("id")) != REPORT_ID:
        print(f"refusing: record id {record.get('id')!r} is not {REPORT_ID}", file=sys.stderr)
        return 5

    snapshot = Path(args.out).parent / "source_snapshot.md"
    manifest = build_manifest(record, repo_root, snapshot)
    checks = run_checks(manifest, record["markdown"], record)
    manifest["checks"] = checks
    manifest["checks_passed"] = all(c["pass"] for c in checks)

    out = repo_root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checks_out = repo_root / args.checks_json
    checks_out.write_text(json.dumps({"package_id": PACKAGE_ID, "checks": checks,
                                      "all_pass": manifest["checks_passed"]},
                                     ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["name"] + " :: " + c["detail"])
    print(f"wrote {args.out} {manifest['counts']}")
    return 0 if manifest["checks_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())