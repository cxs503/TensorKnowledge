#!/usr/bin/env python3
"""RCI pilot200 语料快照的溯源校验器（anchor KBM-RCI-S2B-PILOT）。

问题：`knowledge/rci-pilot200/corpus/` 存的是**上游仓文档原文**。这类文件一旦入库，
单看内容无法判断它是不是原件：可能是手写、可能被改过、也可能 PR 里只剩一个
`+0/-0` 的占位（PR#184 第一轮就是这样：清单写着有文件，实际没有字节）。
本工具把「原件」变成可机检的三条约束：

  1. **哈希钉扎**：每个文件 sha256 必须等于冻结清单 `PROVENANCE.json` 记的
     `sha256`，且该值必须与扫描上游时的 `inventory_sha256` 相等
     （两者不一致 ⇒ 扫描后文件漂移，不是原件）。
  2. **第二份独立副本互证**：每份子集文档必须与本仓另一条链路
     `docs/rci-f1-abc/snapshot/` 里同 sha256 的副本逐字节相同 —— 两次独立落盘，
     互相印证不是同一处手写笔误。
  3. **清单与磁盘互为完备**：清单列的必须在；磁盘 `corpus/` 下的每一个文件都必须
     被清单覆盖（防止塞入未溯源文件）；`snapshot_path` 必须严格等于
     `<corpus_root>/<repo>/<path>`（保证 ko 证据 locator 能按规则解析回磁盘）。

用法:
  python3 scripts/rci_corpus_provenance.py            # 校验，全部通过退出 0
  python3 scripts/rci_corpus_provenance.py --json     # 机器可读回执
  python3 scripts/rci_corpus_provenance.py --root /tmp/x --manifest m.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_REL = "knowledge/rci-pilot200/PROVENANCE.json"

Reader = Callable[[Path], bytes]


def _read(path: Path) -> bytes:
    return path.read_bytes()


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def sha256_file(path: Path, reader: Reader | None = None) -> str:
    return sha256_bytes((reader or _read)(path))


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _issue(code: str, detail: str, path: str = "") -> dict[str, str]:
    return {"code": code, "path": path, "detail": detail}


def expected_snapshot_path(manifest: dict[str, Any], doc: dict[str, Any]) -> str:
    """locator → 磁盘的映射规则：<corpus_root>/<repo>/<path>。"""
    return "/".join(
        [str(manifest["corpus_root"]).rstrip("/"), str(doc["repo"]).strip("/"), str(doc["path"]).lstrip("/")]
    )


def check_documents(
    manifest: dict[str, Any],
    root: Path,
    reader: Reader | None = None,
    cross_read: Reader | None = None,
) -> list[dict[str, str]]:
    """逐文档校验：存在性 / 体积 / 哈希 / 扫描期钉扎 / 路径规则 / 第二副本互证。"""
    issues: list[dict[str, str]] = []
    for doc in manifest.get("documents", []):
        rel = str(doc["snapshot_path"])
        path = root / rel
        want = expected_snapshot_path(manifest, doc)
        if rel != want:
            issues.append(_issue("E_SNAPSHOT_PATH_RULE", f"snapshot_path={rel} 应等于 {want}", rel))
        if not path.is_file():
            issues.append(_issue("E_SNAPSHOT_MISSING", "清单登记的文件不存在", rel))
            continue
        blob = (reader or _read)(path)
        if len(blob) != int(doc.get("bytes", -1)):
            issues.append(_issue("E_BYTES_MISMATCH", f"实际 {len(blob)} B != 清单 {doc.get('bytes')} B", rel))
        got = sha256_bytes(blob)
        if got != doc.get("sha256"):
            issues.append(_issue("E_SHA256_MISMATCH", f"实际 {got} != 清单 {doc.get('sha256')}", rel))
        if doc.get("sha256") != doc.get("inventory_sha256"):
            issues.append(
                _issue(
                    "E_INVENTORY_PIN_DISAGREE",
                    f"快照钉扎 {doc.get('sha256')} != 扫描期钉扎 {doc.get('inventory_sha256')}",
                    rel,
                )
            )
        f1_rel = str(doc.get("f1_snapshot_path") or "")
        if f1_rel:
            f1_path = root / f1_rel
            if not f1_path.is_file():
                issues.append(_issue("E_CROSS_COPY_MISSING", "第二链路副本不存在", f1_rel))
            else:
                f1_sha = sha256_file(f1_path, cross_read)
                if f1_sha != doc.get("sha256"):
                    issues.append(
                        _issue("E_CROSS_COPY_MISMATCH", f"第二副本 {f1_sha} != 快照 {doc.get('sha256')}", f1_rel)
                    )
    return issues


def check_coverage(manifest: dict[str, Any], root: Path) -> list[dict[str, str]]:
    """清单 ↔ 磁盘互为完备（不许有未溯源文件，也不许清单数与文件数不符）。"""
    issues: list[dict[str, str]] = []
    corpus_root = root / str(manifest["corpus_root"])
    listed = {str(d["snapshot_path"]) for d in manifest.get("documents", [])}
    if int(manifest.get("documents_in_repo", -1)) != len(listed):
        issues.append(
            _issue(
                "E_MANIFEST_SELF_COUNT",
                f"documents_in_repo={manifest.get('documents_in_repo')} 与 documents 条目数 {len(listed)} 不一致",
            )
        )
    if not corpus_root.is_dir():
        issues.append(_issue("E_CORPUS_ROOT_MISSING", "corpus 根目录不存在", str(manifest["corpus_root"])))
        return issues
    on_disk = {
        p.relative_to(root).as_posix() for p in corpus_root.rglob("*") if p.is_file()
    }
    for rel in sorted(on_disk - listed):
        issues.append(_issue("E_UNLISTED_FILE", "磁盘上存在清单未登记的文件（无法溯源）", rel))
    return issues


def verify(root: Path | str = REPO_ROOT, manifest_path: Path | str | None = None) -> list[dict[str, str]]:
    root = Path(root)
    manifest = load_manifest(Path(manifest_path) if manifest_path else root / MANIFEST_REL)
    return check_documents(manifest, root) + check_coverage(manifest, root)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="RCI pilot200 语料快照溯源校验（anchor KBM-RCI-S2B-PILOT）")
    ap.add_argument("--root", default=str(REPO_ROOT), help="仓库根（默认本仓）")
    ap.add_argument("--manifest", default=None, help=f"清单路径（默认 <root>/{MANIFEST_REL}）")
    ap.add_argument("--json", action="store_true", help="输出机器可读回执")
    args = ap.parse_args(argv)

    root = Path(args.root)
    manifest = load_manifest(Path(args.manifest) if args.manifest else root / MANIFEST_REL)
    issues = check_documents(manifest, root) + check_coverage(manifest, root)
    docs = manifest.get("documents", [])

    if args.json:
        print(
            json.dumps(
                {
                    "anchor": manifest.get("anchor"),
                    "documents_in_pilot": manifest.get("documents_in_pilot"),
                    "documents_in_repo": len(docs),
                    "verified": [d["snapshot_path"] for d in docs],
                    "issues": issues,
                    "ok": not issues,
                },
                ensure_ascii=False,
                indent=1,
                sort_keys=True,
            )
        )
    else:
        for doc in docs:
            print(f"OK  {doc['snapshot_path']}  sha256={str(doc['sha256'])[:16]}…  {doc['bytes']} B")
        for issue in issues:
            print(f"FAIL [{issue['code']}] {issue['path']} {issue['detail']}", file=sys.stderr)
        print(
            f"{len(docs)} document(s) checked, {len(issues)} issue(s)"
            + ("" if issues else " — 全部与冻结清单一致"),
            file=sys.stderr,
        )
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())