#!/usr/bin/env python3
"""
Download DATAHACKS2026 training and validation data.

Usage:
    python download_data.py                 # download both train + validation
    python download_data.py --only train    # download only training data
    python download_data.py --only validation
    python download_data.py --list          # show available data
    python download_data.py --force         # re-download even if present
"""

import argparse
import os
import stat
import shutil
import sqlite3
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_DATA_DIR = _HERE / "data"

_BUNDLE_URLS: dict[str, str] = {
    "train": "https://polymarket-btc-data.s3.amazonaws.com/hackathon-bundles/train.tar.gz",
    "validation": "https://polymarket-btc-data.s3.amazonaws.com/hackathon-bundles/validation.tar.gz",
}

_EXPECTED_CONTENTS = {
    "polymarket.db": "SQLite database (market prices + Chainlink reference prices for BTC/ETH/SOL)",
    "polymarket_books/": "Order book snapshots (CSV, 1-second, 9 markets across BTC/ETH/SOL)",
    "binance_lob/": "Binance LOB (per-symbol Parquet: btcusdt, ethusdt, solusdt, 10-level depth)",
}


def _force_rmtree(path: Path) -> None:
    """Remove a directory tree, handling read-only files (Windows/OneDrive)."""
    def _on_error(_func, _path, _exc_info):
        os.chmod(_path, stat.S_IWRITE)
        _func(_path)
    shutil.rmtree(path, onerror=_on_error)


def _sizeof_fmt(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def _download_with_progress(url: str, dest_path: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "datahacks2026-downloader/1.0"})
    with urllib.request.urlopen(req) as resp:
        total = resp.headers.get("Content-Length")
        total = int(total) if total else None
        downloaded = 0
        with open(dest_path, "wb") as fp:
            while True:
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                fp.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(
                        f"\r  {_sizeof_fmt(downloaded)} / {_sizeof_fmt(total)} ({pct:.0f}%)",
                        end="", flush=True,
                    )
                else:
                    print(f"\r  {_sizeof_fmt(downloaded)}", end="", flush=True)
    print()


def _extract_tarball(tarball_path: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tarball_path, "r:gz") as tf:
        for member in tf.getmembers():
            member_path = (dest_dir / member.name).resolve()
            if not str(member_path).startswith(str(dest_dir.resolve())):
                raise RuntimeError(f"Tarball contains unsafe path: {member.name}")
        tf.extractall(dest_dir)


def _describe_db(db_path: Path) -> str:
    try:
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT MIN(timestamp_us), MAX(timestamp_us) FROM market_prices"
        ).fetchone()
        conn.close()
        if row and row[0]:
            from datetime import datetime, timezone
            start = datetime.fromtimestamp(row[0] / 1e6, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            end = datetime.fromtimestamp(row[1] / 1e6, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            hours = (row[1] - row[0]) / 1e6 / 3600
            return f"{start} to {end} UTC ({hours:.1f}h)"
    except Exception:
        pass
    return ""


def _verify_data(data_dir: Path) -> bool:
    ok = True
    for name, desc in _EXPECTED_CONTENTS.items():
        target = data_dir / name
        if name.endswith("/"):
            if target.is_dir():
                count = sum(1 for _ in target.iterdir())
                print(f"    [OK]   {name:24s} ({count} files)")
            else:
                print(f"    [MISS] {name:24s} -- {desc}")
                ok = False
        else:
            if target.is_file():
                size = _sizeof_fmt(target.stat().st_size)
                extra = _describe_db(target) if name == "polymarket.db" else ""
                extra = f"  {extra}" if extra else ""
                print(f"    [OK]   {name:24s} ({size}){extra}")
            else:
                print(f"    [MISS] {name:24s} -- {desc}")
                ok = False
    return ok


def download_bundle(name: str, force: bool = False) -> bool:
    url = _BUNDLE_URLS.get(name, "")
    dest = _DATA_DIR / name

    if dest.is_dir() and not force:
        print(f"\n  [{name}] Already exists. Use --force to re-download.")
        _verify_data(dest)
        return True

    if not url:
        print(f"\n  [{name}] ERROR: No download URL configured.")
        return False

    print(f"\n  [{name}] Downloading from {url}...")

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        _download_with_progress(url, tmp_path)
        if dest.is_dir() and force:
            _force_rmtree(dest)
        print(f"  Extracting to {dest}...")
        _extract_tarball(tmp_path, dest)
    except urllib.error.URLError as e:
        print(f"\n  ERROR: Download failed -- {e.reason}")
        return False
    except Exception as e:
        print(f"\n  ERROR: {e}")
        return False
    finally:
        tmp_path.unlink(missing_ok=True)

    print(f"  [{name}] Contents:")
    _verify_data(dest)
    return True


def list_data() -> None:
    print(f"\nData directory: {_DATA_DIR}\n")
    for name in ("train", "validation"):
        dest = _DATA_DIR / name
        if dest.is_dir():
            db = dest / "polymarket.db"
            if db.exists():
                desc = _describe_db(db)
                size = _sizeof_fmt(db.stat().st_size)
                print(f"  {name:12s}  [DOWNLOADED]  {size}")
                if desc:
                    print(f"               {desc}")
            else:
                print(f"  {name:12s}  [INCOMPLETE]")
            _verify_data(dest)
        else:
            print(f"  {name:12s}  [NOT DOWNLOADED]")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download DATAHACKS2026 training and validation data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--only", choices=["train", "validation"],
                        help="Download only one bundle")
    parser.add_argument("--list", action="store_true", dest="list_data",
                        help="Show available data")
    parser.add_argument("--force", action="store_true",
                        help="Re-download even if data exists")
    args = parser.parse_args()

    if args.list_data:
        list_data()
        return 0

    bundles = [args.only] if args.only else ["train", "validation"]
    ok = True
    for name in bundles:
        if not download_bundle(name, force=args.force):
            ok = False

    if ok:
        print("\n  Done! Run your strategy:")
        print("    python run_backtest.py strategy_template.py")
        print("    python run_backtest.py strategy_template.py --data data/validation/\n")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
