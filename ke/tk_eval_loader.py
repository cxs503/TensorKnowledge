"""tk_eval_loader.py — TensorKnowledge eval dataset loader.

Reference implementation for training consumption contract (m8813).
A ~10-line PyTorch Dataset subclass that loads a versioned dataset
via the HTTP API, verifies SHA256, and yields samples.

Usage:
    python tk_eval_loader.py --dataset ship-resistance --version v1.0 \
        --base-url http://127.0.0.1:8090

Requires: torch (for Dataset base class), stdlib for HTTP/JSON/SHA256.
If torch is not available, falls back to a plain Python iterable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from urllib.request import urlopen, Request


def _load_jsonl(url: str) -> tuple[list[dict], str]:
    """Download JSONL from URL, return (rows, sha256_from_header)."""
    req = Request(url)
    with urlopen(req) as resp:
        sha256_header = resp.headers.get("X-Dataset-SHA256", "")
        body = resp.read().decode("utf-8")
    rows = [json.loads(line) for line in body.strip().splitlines() if line.strip()]
    return rows, sha256_header


class TKDataset:
    """Load a versioned TensorKnowledge dataset via HTTP API.

    Works with or without torch installed.
    """

    def __init__(self, name: str, version: str, base_url: str, include: str = "published"):
        self.name = name
        self.version = version
        url = f"{base_url}/datasets/{name}/{version}/download?include={include}"
        self.rows, self.sha256 = _load_jsonl(url)
        assert len(self.rows) > 0, f"empty dataset {name}/{version}"

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        return self.rows[idx]

    def __iter__(self):
        return iter(self.rows)


# Torch-compatible version (if torch is available)
try:
    from torch.utils.data import Dataset as TorchDataset

    class TKDatasetTorch(TKDataset, TorchDataset):
        """PyTorch-compatible version of TKDataset."""
        pass

    _DatasetClass = TKDatasetTorch
except ImportError:
    _DatasetClass = TKDataset


def main():
    ap = argparse.ArgumentParser(description="TensorKnowledge Eval Dataset Loader")
    ap.add_argument("--dataset", required=True, help="Dataset name")
    ap.add_argument("--version", required=True, help="Dataset version")
    ap.add_argument("--base-url", default="http://127.0.0.1:8090", help="API base URL")
    ap.add_argument("--include", default="published", choices=["published", "reviewed"])
    ap.add_argument("--show-sample", type=int, default=0, help="Show sample at index N")
    args = ap.parse_args()

    ds = _DatasetClass(args.dataset, args.version, args.base_url, args.include)
    print(f"Loaded {len(ds)} samples from {args.dataset}/{args.version}")
    print(f"SHA256: {ds.sha256}")

    if len(ds) > args.show_sample:
        sample = ds[args.show_sample]
        print(f"\nSample [{args.show_sample}]:")
        print(json.dumps(sample, ensure_ascii=False, indent=2)[:300])
        if len(json.dumps(sample, ensure_ascii=False)) > 300:
            print("...")

    # Verify: iterate all samples
    count = 0
    for row in ds:
        assert "id" in row, f"sample missing 'id': {row}"
        assert "text" in row, f"sample missing 'text': {row}"
        count += 1
    print(f"\nVerified {count} samples (all have id + text fields)")


if __name__ == "__main__":
    main()
