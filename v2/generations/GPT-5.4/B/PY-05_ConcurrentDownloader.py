import argparse
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen

ProgressCallback = Callable[[int, int, Dict[str, object]], None]


def sanitize_filename(name: str) -> str:
    sanitized = "".join(character if character.isalnum() or character in "-_." else "_" for character in name)
    return sanitized or "downloaded_file"


def build_filename(index: int, url: str) -> str:
    parsed = urlsplit(url)
    candidate = os.path.basename(unquote(parsed.path)) or f"file_{index + 1}"
    return f"{index + 1:03d}_{sanitize_filename(candidate)}"


def download_single(url: str, destination: str, timeout: int, max_retries: int) -> Dict[str, object]:
    last_error: Optional[str] = None

    for attempt in range(1, max_retries + 1):
        try:
            with urlopen(url, timeout=timeout) as response:
                data = response.read()
            with open(destination, "wb") as file_handle:
                file_handle.write(data)
            return {
                "url": url,
                "path": destination,
                "status": "success",
                "attempts": attempt,
                "bytes": len(data),
            }
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
            if attempt < max_retries:
                time.sleep(2 ** (attempt - 1))

    return {
        "url": url,
        "path": destination,
        "status": "failed",
        "attempts": max_retries,
        "error": last_error or "unknown error",
    }


def download_urls(
    urls: Iterable[str],
    output_dir: str,
    max_workers: int = 4,
    progress_callback: Optional[ProgressCallback] = None,
    timeout: int = 30,
) -> Dict[str, object]:
    url_list = list(urls)
    os.makedirs(output_dir, exist_ok=True)

    summary: Dict[str, object] = {
        "output_dir": os.path.abspath(output_dir),
        "total": len(url_list),
        "succeeded": 0,
        "failed": 0,
        "results": [],
    }
    results: List[Dict[str, object]] = []
    completed = 0
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {}
        for index, url in enumerate(url_list):
            filename = build_filename(index, url)
            destination = os.path.join(output_dir, filename)
            future = executor.submit(download_single, url, destination, timeout, 3)
            future_map[future] = url

        for future in as_completed(future_map):
            result = future.result()
            results.append(result)
            completed += 1

            with lock:
                if result["status"] == "success":
                    summary["succeeded"] = int(summary["succeeded"]) + 1
                else:
                    summary["failed"] = int(summary["failed"]) + 1

            if progress_callback is not None:
                progress_callback(completed, len(url_list), result)

    results.sort(key=lambda item: str(item["url"]))
    summary["results"] = results
    return summary


def default_progress_callback(completed: int, total: int, info: Dict[str, object]) -> None:
    status = info.get("status", "unknown")
    url = info.get("url", "")
    print(f"[{completed}/{total}] {status.upper()} {url}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Concurrent downloader using urllib + ThreadPoolExecutor")
    parser.add_argument("urls", nargs="+", help="URLs to download")
    parser.add_argument("--output-dir", required=True, help="Directory for downloaded files")
    parser.add_argument("--max-workers", type=int, default=4, help="Maximum concurrent workers")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = download_urls(
        urls=args.urls,
        output_dir=args.output_dir,
        max_workers=args.max_workers,
        progress_callback=default_progress_callback,
        timeout=args.timeout,
    )
    print(summary)


if __name__ == "__main__":
    main()
