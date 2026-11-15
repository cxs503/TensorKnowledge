"""TensorKnowledge — dataset HTTP API server (m8813).

Endpoints
---------
GET /datasets                              — list all dataset versions
GET /datasets/{name}/{version}/manifest    — get manifest JSON
GET /datasets/{name}/{version}/download    — JSONL stream + X-Dataset-SHA256 header
GET /datasets/{name}/{version}/diff?since= — incremental rows since a version

Epistemic discipline
--------------------
* download 默认 published-only
* ?include=reviewed 才并入 reviewed
* draft 永不可下 → 403 Forbidden
* 同版本 sha256 不符 → 409 Conflict

Usage
-----
    python -m ke.dataset_server --db /tmp/datasets.db --port 8090
"""
from __future__ import annotations

import argparse
import json
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from ke.datasets import DatasetStore

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

_DATASET_LIST_RE = re.compile(r"^/datasets$")
_DATASET_MANIFEST_RE = re.compile(r"^/datasets/([^/]+)/([^/]+)/manifest$")
_DATASET_DOWNLOAD_RE = re.compile(r"^/datasets/([^/]+)/([^/]+)/download$")
_DATASET_DIFF_RE = re.compile(r"^/datasets/([^/]+)/([^/]+)/diff$")


class DatasetHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dataset API."""

    store: DatasetStore  # set by server

    def log_message(self, fmt, *args):
        # Suppress default stderr logging; callers can enable via --verbose
        pass

    # -- helpers ------------------------------------------------------------

    def _send_json(self, code: int, obj: object, headers: dict | None = None):
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _send_jsonl_stream(self, rows: list[str], sha256: str, gate_level: str = "ungated"):
        """Stream JSONL rows with SHA256 + train-gate level headers."""
        body = "\n".join(rows)
        if rows:
            body += "\n"
        body_bytes = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/x-jsonl")
        self.send_header("X-Dataset-SHA256", sha256)
        self.send_header("X-Train-Gate-Level", gate_level)
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)

    def _send_error(self, code: int, message: str):
        self._send_json(code, {"error": message})

    def _parse_include(self, qs: dict[str, list[str]]) -> str:
        """Training-side visibility only exposes published/reviewed.

        ``include=all`` used to leak draft rows through this endpoint; it is now
        rejected at the edge (403) instead of being passed down to the store.
        """
        inc = qs.get("include", ["published"])[0]
        if inc not in ("published", "reviewed"):
            return "__forbidden__"
        return inc

    # -- GET handlers -------------------------------------------------------

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        path = parsed.path

        # GET /datasets
        m = _DATASET_LIST_RE.match(path)
        if m:
            return self._handle_list()

        # GET /datasets/{name}/{version}/manifest
        m = _DATASET_MANIFEST_RE.match(path)
        if m:
            return self._handle_manifest(m.group(1), m.group(2))

        # GET /datasets/{name}/{version}/download
        m = _DATASET_DOWNLOAD_RE.match(path)
        if m:
            return self._handle_download(m.group(1), m.group(2), qs)

        # GET /datasets/{name}/{version}/diff
        m = _DATASET_DIFF_RE.match(path)
        if m:
            return self._handle_diff(m.group(1), m.group(2), qs)

        self._send_error(404, f"not found: {path}")

    def _handle_list(self):
        try:
            datasets = self.store.list_datasets()
            self._send_json(200, {"datasets": datasets})
        except Exception as e:
            self._send_error(500, str(e))

    def _handle_manifest(self, name: str, version: str):
        manifest = self.store.get_manifest(name, version)
        if manifest is None:
            self._send_error(404, f"dataset {name}/{version} not found")
            return
        self._send_json(200, manifest)

    def _handle_download(self, name: str, version: str, qs: dict):
        include = self._parse_include(qs)
        if include == "__forbidden__":
            self._send_error(403, "include must be 'published' or 'reviewed'; "
                                  "'all' is never exposed to the training side")
            return
        try:
            rows, sha = self.store.download_rows_jsonl(name, version, include=include)
        except KeyError:
            self._send_error(404, f"dataset {name}/{version} not found")
            return
        except PermissionError as e:
            self._send_error(403, str(e))
            return
        except Exception as e:
            self._send_error(500, str(e))
            return

        # Verify integrity before serving
        if not self.store.verify_integrity(name, version):
            self._send_error(409, f"integrity check failed for {name}/{version}")
            return

        gate = getattr(self.store, "gate", None)
        gate_level = "ungated"
        if gate is not None:
            row = gate.get(name, version)
            gate_level = row["review_level"] if row else "ungated"
        self._send_jsonl_stream(rows, sha, gate_level)

    def _handle_diff(self, name: str, version: str, qs: dict):
        since_list = qs.get("since")
        if not since_list:
            self._send_error(400, "missing required query parameter: since")
            return
        since = since_list[0]
        include = self._parse_include(qs)
        try:
            diff_rows = self.store.diff(name, version, since, include=include)
        except KeyError as e:
            self._send_error(404, str(e))
            return
        except PermissionError as e:
            self._send_error(403, str(e))
            return
        except Exception as e:
            self._send_error(500, str(e))
            return

        self._send_json(200, {
            "name": name,
            "version": version,
            "since": since,
            "new_rows": diff_rows,
            "new_row_count": len(diff_rows),
        })


def make_server(db_path: str, port: int, host: str = "127.0.0.1",
                gate_enabled: bool = True) -> HTTPServer:
    """Create and return an HTTPServer with the dataset store (+ train gate)."""
    store = DatasetStore(db_path)
    if gate_enabled:
        # 同一 SQLite 连接上的 train_gate 表：下载端点先过闸门再审级。
        # KE_TRAIN_GATE_STRICT=1 → 无 gate 行即拒绝（生产 fail-closed）；
        # 默认放开以兼容闸门上线前登记的历史数据集。
        from .train_gate import TrainGateStore

        strict = os.environ.get("KE_TRAIN_GATE_STRICT", "0") not in ("", "0", "false", "False")
        store.attach_gate(TrainGateStore(conn=store.conn, strict=strict))
    # Attach store to handler class
    DatasetHandler.store = store
    server = HTTPServer((host, port), DatasetHandler)
    return server


def main():
    ap = argparse.ArgumentParser(description="TensorKnowledge Dataset API Server")
    ap.add_argument("--db", default=":memory:", help="SQLite DB path (default: :memory:)")
    ap.add_argument("--port", type=int, default=8090, help="Listen port (default: 8090)")
    ap.add_argument("--host", default="127.0.0.1", help="Listen host (default: 127.0.0.1)")
    ap.add_argument("--verbose", action="store_true", help="Enable request logging")
    args = ap.parse_args()

    if args.verbose:
        # Re-enable logging
        DatasetHandler.log_message = BaseHTTPRequestHandler.log_message

    server = make_server(args.db, args.port, args.host)
    print(f"Dataset API server listening on {args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
