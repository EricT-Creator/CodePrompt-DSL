from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

ProgressCallback = Callable[[str, int, int | None, int], None]
_progress_lock = threading.Lock()


def default_progress_callback(url: str, downloaded: int, total: int | None, attempt: int) -> None:
    with _progress_lock:
        if total:
            percent = downloaded / total * 100
            print(f"[{attempt}] {url} -> {downloaded}/{total} bytes ({percent:.1f}%)")
        else:
            print(f"[{attempt}] {url} -> {downloaded} bytes")


def derive_filename(url: str, index: int) -> str:
    parsed = urllib.parse.urlparse(url)
    name = Path(parsed.path).name or f"download_{index + 1}"
    return name


def ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def download_one(
    url: str,
    output_dir: Path,
    index: int,
    timeout: int = 30,
    max_retries: int = 3,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, object]:
    callback = progress_callback or default_progress_callback
    last_error = ""

    for attempt in range(1, max_retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "ConcurrentDownloader/1.0"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                total_header = response.headers.get("Content-Length")
                total = int(total_header) if total_header and total_header.isdigit() else None
                target_path = ensure_unique_path(output_dir / derive_filename(url, index))
                downloaded = 0

                with target_path.open("wb") as output_file:
                    while True:
                        chunk = response.read(64 * 1024)
                        if not chunk:
                            break
                        output_file.write(chunk)
                        downloaded += len(chunk)
                        callback(url, downloaded, total, attempt)

                return {
                    "url": url,
                    "status": "success",
                    "path": str(target_path),
                    "bytes": downloaded,
                }
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
            if attempt == max_retries:
                break
            time.sleep(2 ** (attempt - 1))

    return {
        "url": url,
        "status": "failed",
        "error": last_error or "unknown error",
    }


def download_all(
    urls: list[str],
    output_dir: str,
    max_workers: int = 4,
    timeout: int = 30,
    max_retries: int = 3,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, object]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    successes: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="downloader") as executor:
        futures = {
            executor.submit(
                download_one,
                url,
                destination,
                index,
                timeout,
                max_retries,
                progress_callback,
            ): url
            for index, url in enumerate(urls)
        }

        for future in as_completed(futures):
            result = future.result()
            if result["status"] == "success":
                successes.append(result)
            else:
                failures.append(result)

    return {
        "success": len(successes),
        "failed": len(failures),
        "files": successes,
        "errors": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Concurrent downloader using urllib and threads")
    parser.add_argument("output_dir", help="Directory used to store downloaded files")
    parser.add_argument("urls", nargs="+", help="List of URLs to download")
    parser.add_argument("--workers", type=int, default=4, help="Number of download threads")
    parser.add_argument("--timeout", type=int, default=30, help="Per-request timeout in seconds")
    parser.add_argument("--retries", type=int, default=3, help="Retry count for each URL")
    args = parser.parse_args()

    summary = download_all(
        urls=args.urls,
        output_dir=args.output_dir,
        max_workers=args.workers,
        timeout=args.timeout,
        max_retries=args.retries,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
