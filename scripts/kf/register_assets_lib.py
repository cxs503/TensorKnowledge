#!/usr/bin/env python3
"""KF 工序 01-asset-registration 的共用库：取源 / markdown 行索引 / 选择器定位。

设计约束（与 KF-RESULT 工作包契约一致）：
- report_id 硬锁：非本单 report_id 的源记录一律拒绝；
- quote 一律取 markdown **整行原文**（不裁不改），定位靠选择器而不是手打长文本；
- 每条 quote 做双重校验：`quote in markdown` 与 `markdown[offset:offset+len] == quote`。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path


def api_base() -> str:
    return os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")


def get_token() -> str | None:
    """登录取 token；失败返回 None（离线场景不抛）。"""
    try:
        body = json.dumps(
            {
                "username": os.environ["TENSOR_AGENT_USER"],
                "password": os.environ["TENSOR_AGENT_PASS"],
            }
        ).encode()
        req = urllib.request.Request(
            api_base() + "/auth/login", data=body, headers={"Content-Type": "application/json"}
        )
        d = json.load(urllib.request.urlopen(req, timeout=30))
        return d.get("access_token") or d.get("token")
    except Exception:  # noqa: BLE001 - 无网/无凭证即离线模式
        return None


def fetch_report(report_id: str, record_file: Path | None = None) -> dict:
    """取源记录（markdown + 元数据）。record_file 给出时走离线重建。"""
    if record_file is not None:
        rec = json.loads(Path(record_file).read_text(encoding="utf-8"))
        rec["_retrieved_via"] = "record-file:" + str(record_file)
    else:
        tok = get_token()
        if not tok:
            raise SystemExit("登录失败：无 token，且未给 --record-file（无法取源）")
        req = urllib.request.Request(
            api_base() + "/tensor/reports/" + report_id,
            headers={"Authorization": "Bearer " + tok},
        )
        rec = json.load(urllib.request.urlopen(req, timeout=60))
        rec["_retrieved_via"] = "GET /api/v1/tensor/reports/%s (Bearer token)" % report_id
    if str(rec.get("id")) != str(report_id):
        raise SystemExit("report_id 不符，拒绝产出：期望 %r 实得 %r" % (report_id, rec.get("id")))
    if not (rec.get("markdown") or ""):
        raise SystemExit("markdown 字段为空，拒绝产出")
    return rec


def probe(endpoint: str, token: str | None) -> dict:
    """端点探针：确认工件字节是否可经 API 取得；失败如实记录，不抛。"""
    if not token:
        return {"endpoint": endpoint, "http_status": None, "note": "no token (offline rebuild)"}
    req = urllib.request.Request(api_base() + endpoint, headers={"Authorization": "Bearer " + token})
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return {"endpoint": endpoint, "http_status": r.status, "bytes": len(r.read())}
    except urllib.error.HTTPError as e:
        return {"endpoint": endpoint, "http_status": e.code, "bytes": 0}
    except Exception as e:  # noqa: BLE001
        return {"endpoint": endpoint, "http_status": None, "note": repr(e)}


def sha256_of(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


class Md:
    """markdown 行索引 + 选择器定位。"""

    def __init__(self, text: str):
        self.text = text
        self.lines: list[tuple[int, str]] = []
        off = 0
        for ln in text.splitlines():
            self.lines.append((off, ln))
            off += len(ln) + 1

    # -- 基础 --------------------------------------------------------------
    def find_line(self, token: str, nth: int = 0) -> tuple[int, str]:
        hits = [(o, ln) for o, ln in self.lines if token in ln]
        if len(hits) <= nth:
            raise LookupError("token not found (nth=%d): %r" % (nth, token))
        return hits[nth]

    def header_index(self, token: str) -> int:
        for idx, (_o, ln) in enumerate(self.lines):
            if ln.lstrip().startswith("#") and token in ln:
                return idx
        raise LookupError("header not found: %r" % token)

    def nth_nonempty_after(self, header_token: str, n: int) -> tuple[int, str]:
        idx = self.header_index(header_token)
        cnt = 0
        for o, ln in self.lines[idx + 1:]:
            if not ln.strip():
                continue
            cnt += 1
            if cnt == n:
                return o, ln
        raise LookupError("not enough lines after %r (n=%d)" % (header_token, n))

    def table_block(self, header_token: str) -> tuple[tuple[int, str], list[tuple[int, str]]]:
        """返回 (表头行, 数据行列表)。表头行以 | 开头且含 header_token。"""
        idx = None
        for i, (_o, ln) in enumerate(self.lines):
            if ln.startswith("|") and header_token in ln:
                idx = i
                break
        if idx is None:
            raise LookupError("table header not found: %r" % header_token)
        rows: list[tuple[int, str]] = []
        for o, ln in self.lines[idx + 2:]:
            if not ln.startswith("|"):
                break
            rows.append((o, ln))
        return self.lines[idx], rows

    def bullets_after(self, header_token: str) -> list[tuple[int, str]]:
        idx = self.header_index(header_token)
        out: list[tuple[int, str]] = []
        started = False
        for o, ln in self.lines[idx + 1:]:
            if started and ln.lstrip().startswith("#"):
                break
            if not started:
                if ln.lstrip().startswith("- ") or re.match(r"^\d+\.\s", ln.lstrip()):
                    started = True
                else:
                    continue
            out.append((o, ln))
        return out

    # -- 选择器 ------------------------------------------------------------
    def locate(self, sel: str, title: str = "") -> tuple[int, str, dict]:
        meta: dict = {}
        if sel == "h1":
            for o, ln in self.lines:
                if ln.startswith("# "):
                    return o, ln, meta
            raise LookupError("no H1")
        if sel.startswith("after:"):
            _, header, n = sel.split(":", 2)
            o, ln = self.nth_nonempty_after(header, int(n))
            return o, ln, meta
        if sel.startswith("table_row:"):
            _, hdr, i = sel.split(":", 2)
            _h, rows = self.table_block(hdr)
            meta["data_rows"] = len(rows)
            if len(rows) <= int(i):
                raise LookupError("table row index out of range")
            return rows[int(i)][0], rows[int(i)][1], meta
        if sel.startswith("table:"):
            hdr = sel[len("table:"):]
            (ho, hl), rows = self.table_block(hdr)
            meta["data_rows"] = len(rows)
            meta["header_quote"] = hl
            return ho, hl, meta
        if sel.startswith("bullet:"):
            _, header, token = sel.split(":", 2)
            for o, ln in self.bullets_after(header):
                if token in ln:
                    return o, ln, meta
            raise LookupError("bullet not found: %r in %r" % (token, header))
        if sel.startswith("token:"):
            parts = sel[len("token:"):].split(":")
            token = title if parts[0] == "__TITLE__" else parts[0]
            nth = int(parts[1]) if len(parts) > 1 else 0
            o, ln = self.find_line(token, nth)
            return o, ln, meta
        raise LookupError("bad selector: %r" % sel)


def locate_all(md: Md, spec: list[dict], title: str, report_id: str) -> tuple[list, dict]:
    """按 SPEC 逐条定位，返回 (assets, locator_checks)。未命中的如实登记 unresolved。"""
    assets, checks = [], {}
    for s in spec:
        status = s.get("status", "resolved")
        aid = "asset-%s-%s" % (report_id, s["id"])
        try:
            offset, quote, meta = md.locate(s["sel"], title)
        except LookupError as e:
            assets.append(
                dict(
                    asset_id=aid,
                    kind=s["kind"],
                    uri="tensor://reports/%s#markdown/%s" % (report_id, s["section"]),
                    status=s.get("status", "unresolved"),
                    unresolved_reason=s.get("unresolved_reason")
                    or "选择器未命中（%s）：工件字节不可定位，不代上游补写。" % e,
                    notes=s.get("note", ""),
                )
            )
            continue
        occ = md.text.count(quote)
        back = md.text[offset:offset + len(quote)] == quote
        entry = dict(
            asset_id=aid,
            kind=s["kind"],
            uri="tensor://reports/%s#markdown/%s" % (report_id, s["section"]),
            status=status,
            chars=len(quote),
            locator=dict(
                source_field="markdown",
                section=s["section"],
                quote=quote,
                quote_verified=bool((quote in md.text) and back),
                offset_chars=offset,
                count_occurrences=occ,
                note=s.get("note", ""),
            ),
        )
        if meta:
            entry["stats"] = meta
        if status != "resolved":
            entry["unresolved_reason"] = s["unresolved_reason"]
        assets.append(entry)
        checks[aid] = dict(
            quote=quote,
            resolvable_in_markdown=quote in md.text,
            offset_chars=offset,
            back_read_ok=back,
            count_occurrences=occ,
        )
    return assets, checks