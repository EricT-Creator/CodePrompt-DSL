import os
import time
import threading
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional


class DownloadResult:
    def __init__(self, url: str, status: str, filepath: Optional[str] = None,
                 size: int = 0, elapsed: float = 0.0, error: Optional[str] = None):
        self.url = url
        self.status = status  # "success", "failed", "retrying"
        self.filepath = filepath
        self.size = size
        self.elapsed = elapsed
        self.error = error

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "status": self.status,
            "filepath": self.filepath,
            "size": self.size,
            "elapsed": round(self.elapsed, 3),
            "error": self.error,
        }


def download_file(
    url: str,
    output_dir: str,
    max_retries: int = 3,
    timeout: int = 30,
    progress_callback: Optional[Callable[[str, str, int, int], None]] = None,
) -> DownloadResult:
    """Download a single file with retry and exponential backoff.

    Args:
        url: URL to download
        output_dir: Directory to save the file
        max_retries: Maximum number of retry attempts
        timeout: Timeout in seconds per attempt
        progress_callback: Optional callback(url, status, bytes_downloaded, total_bytes)
    """
    # Derive filename from URL
    filename = url.rstrip("/").split("/")[-1]
    if not filename or filename == "":
        filename = "download_" + str(int(time.time()))
    if "?" in filename:
        filename = filename.split("?")[0]
    filepath = os.path.join(output_dir, filename)

    for attempt in range(max_retries):
        start_time = time.time()
        try:
            req = Request(url, headers={"User-Agent": "ConcurrentDownloader/1.0"})
            with urlopen(req, timeout=timeout) as response:
                total_size = int(response.headers.get("Content-Length", -1))
                downloaded = 0
                with open(filepath, "wb") as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(url, "downloading", downloaded, total_size)

                elapsed = time.time() - start_time
                if progress_callback:
                    progress_callback(url, "success", downloaded, downloaded)

                return DownloadResult(
                    url=url,
                    status="success",
                    filepath=filepath,
                    size=downloaded,
                    elapsed=elapsed,
                )

        except (URLError, HTTPError, OSError) as e:
            elapsed = time.time() - start_time
            error_str = str(e)
            if attempt < max_retries - 1:
                if progress_callback:
                    progress_callback(url, f"retrying (attempt {attempt + 2}/{max_retries})", 0, 0)
                # Exponential backoff: 1s, 2s, 4s...
                backoff = 2 ** attempt
                time.sleep(backoff)
            else:
                if progress_callback:
                    progress_callback(url, "failed", 0, 0)
                return DownloadResult(
                    url=url,
                    status="failed",
                    filepath=filepath,
                    size=0,
                    elapsed=elapsed,
                    error=error_str,
                )

    return DownloadResult(url=url, status="failed", error="Max retries exceeded")


def download_all(
    urls: list[str],
    output_dir: str,
    max_workers: int = 4,
    max_retries: int = 3,
    timeout: int = 30,
    progress_callback: Optional[Callable[[str, str, int, int], None]] = None,
) -> dict:
    """Concurrently download multiple files.

    Args:
        urls: List of URLs to download
        output_dir: Directory to save files
        max_workers: Maximum concurrent threads (default 4)
        max_retries: Maximum retry attempts per URL (default 3)
        timeout: Timeout per request in seconds (default 30)
        progress_callback: Optional callback(url, status, bytes_downloaded, total_bytes)

    Returns:
        Summary dict with total, success, failed, results list
    """
    os.makedirs(output_dir, exist_ok=True)

    results = []
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(
                download_file,
                url, output_dir, max_retries, timeout, progress_callback,
            ): url
            for url in urls
        }

        for future in as_completed(future_to_url):
            result = future.result()
            with lock:
                results.append(result)

    success_count = sum(1 for r in results if r.status == "success")
    failed_count = sum(1 for r in results if r.status == "failed")

    return {
        "total": len(urls),
        "success": success_count,
        "failed": failed_count,
        "max_workers": max_workers,
        "results": [r.to_dict() for r in results],
    }


if __name__ == "__main__":
    def on_progress(url: str, status: str, downloaded: int, total: int):
        print(f"  [{status}] {url} ({downloaded}/{total})")

    urls = [
        "https://httpbin.org/bytes/1024",
        "https://httpbin.org/bytes/2048",
        "https://httpbin.org/bytes/4096",
    ]

    print(f"Downloading {len(urls)} files...")
    summary = download_all(
        urls=urls,
        output_dir="./downloads",
        max_workers=4,
        progress_callback=on_progress,
    )
    print(f"\nSummary: {summary['success']}/{summary['total']} succeeded")
    for r in summary["results"]:
        status_icon = "✓" if r["status"] == "success" else "✗"
        print(f"  {status_icon} {r['url']}: {r['status']} ({r.get('size', 0)} bytes, {r.get('elapsed', 0)}s)")
