import os
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional


def download_file(
    url: str,
    output_dir: str,
    max_retries: int = 3,
    timeout: int = 30,
    progress_callback: Optional[Callable[[str, str, int, int], None]] = None,
) -> Dict:
    """Download a single file with retry and exponential backoff.

    Returns a dict with url, status, path, size, attempts, error.
    """
    filename = url.split("/")[-1].split("?")[0] or "download"
    filepath = os.path.join(output_dir, filename)
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            if progress_callback:
                progress_callback(url, "starting", attempt, max_retries)

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ConcurrentDownloader/1.0"},
            )
            response = urllib.request.urlopen(req, timeout=timeout)
            data = response.read()

            os.makedirs(output_dir, exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(data)

            if progress_callback:
                progress_callback(url, "completed", attempt, max_retries)

            return {
                "url": url,
                "status": "success",
                "path": filepath,
                "size": len(data),
                "attempts": attempt,
                "error": None,
            }
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
            last_error = str(e)
            if progress_callback:
                progress_callback(url, f"retry {attempt}/{max_retries}", attempt, max_retries)
            if attempt < max_retries:
                backoff = 2 ** (attempt - 1)
                time.sleep(backoff)

    return {
        "url": url,
        "status": "failed",
        "path": None,
        "size": 0,
        "attempts": max_retries,
        "error": last_error,
    }


def concurrent_download(
    urls: List[str],
    output_dir: str,
    max_workers: int = 4,
    max_retries: int = 3,
    timeout: int = 30,
    progress_callback: Optional[Callable[[str, str, int, int], None]] = None,
) -> Dict:
    """Download multiple URLs concurrently using ThreadPoolExecutor.

    Args:
        urls: List of URLs to download.
        output_dir: Directory to save downloaded files.
        max_workers: Maximum number of concurrent threads.
        max_retries: Maximum retry attempts per URL.
        timeout: Timeout in seconds per request.
        progress_callback: Optional callback(url, status, attempt, max_retries).

    Returns:
        Summary dict with total, succeeded, failed counts and per-file results.
    """
    os.makedirs(output_dir, exist_ok=True)
    results: List[Dict] = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(
                download_file, url, output_dir, max_retries, timeout, progress_callback
            ): url
            for url in urls
        }

        for future in as_completed(future_to_url):
            result = future.result()
            results.append(result)

    elapsed = time.time() - start_time
    succeeded = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]
    total_bytes = sum(r["size"] for r in succeeded)

    return {
        "total": len(urls),
        "succeeded": len(succeeded),
        "failed": len(failed),
        "total_bytes": total_bytes,
        "elapsed_seconds": round(elapsed, 2),
        "results": results,
    }


def default_progress(url: str, status: str, attempt: int, max_retries: int) -> None:
    short_url = url[:60] + "..." if len(url) > 60 else url
    print(f"[{status:>20}] (attempt {attempt}/{max_retries}) {short_url}")


if __name__ == "__main__":
    sample_urls = [
        "https://httpbin.org/bytes/1024",
        "https://httpbin.org/bytes/2048",
        "https://httpbin.org/bytes/4096",
        "https://httpbin.org/bytes/512",
        "https://httpbin.org/status/404",
    ]

    output = "downloads"
    summary = concurrent_download(
        urls=sample_urls,
        output_dir=output,
        max_workers=4,
        max_retries=3,
        timeout=30,
        progress_callback=default_progress,
    )

    print("\n=== Download Summary ===")
    print(f"Total:     {summary['total']}")
    print(f"Succeeded: {summary['succeeded']}")
    print(f"Failed:    {summary['failed']}")
    print(f"Bytes:     {summary['total_bytes']}")
    print(f"Time:      {summary['elapsed_seconds']}s")

    for r in summary["results"]:
        status_icon = "✓" if r["status"] == "success" else "✗"
        print(f"  {status_icon} {r['url']} -> {r['path'] or r['error']}")
