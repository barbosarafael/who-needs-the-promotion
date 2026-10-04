"""Pinned, opt-in retrieval of the public RetailHero source files."""

from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

SOURCE = "https://huggingface.co/datasets/pytorch-lifestream/retailhero-uplift/resolve"
REVISION = "7744156a4f89f4828607921e8c9668f04801f4de"
FILES = {
    "clients": "data/clients.csv.gz",
    "products": "data/products.csv.gz",
    "purchases": "data/purchases.csv.gz",
    "uplift_train": "data/uplift_train.csv.gz",
    "uplift_test": "data/uplift_test.csv.gz",
}


def retrieve_files(
    destination: str | Path, *, timeout: int = 60
) -> dict[str, dict[str, str | int]]:
    """Download all pinned CSV.GZ files and return byte size + SHA-256 metadata.

    Writes atomically; callers explicitly opt into large downloads (purchases
    alone is ~609 MB compressed). No dataset bytes are returned in memory.
    """
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict[str, str | int]] = {}
    for name, relative in FILES.items():
        target = root / Path(relative).name
        temporary = target.with_suffix(target.suffix + ".part")
        digest = hashlib.sha256()
        size = 0
        request = urllib.request.Request(
            f"{SOURCE}/{REVISION}/{relative}", headers={"User-Agent": "data-audit/1.0"}
        )
        try:
            with (
                urllib.request.urlopen(request, timeout=timeout) as response,
                temporary.open("wb") as out,
            ):
                while chunk := response.read(1024 * 1024):
                    out.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            temporary.replace(target)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        results[name] = {"path": str(target), "bytes": size, "sha256": digest.hexdigest()}
    return results
