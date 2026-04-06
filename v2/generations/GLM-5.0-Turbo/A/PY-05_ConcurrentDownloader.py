import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Callable, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


def download_file(
    url: str,
    output_dir: str,
    timeout: int = 30,
    max_retries: int = 3,
) -> Dict[str, str]:
    """Download a single file with retry logic and exponential backoff."""
    filename = url.split("/")[-1].split("?")[0]
    if not filename:
        filename = f"file_{hash(url) % 100000}"

    filepath = os.path.join(output_dir, filename)

    for attempt in range(1, max_retries + 1):
        try:
            req = Request(url, headers={"User-Agent": "ConcurrentDownloader/1.0"})
            with urlopen(req, timeout=timeout) as response:
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 8192

                with open(filepath, "wb") as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                return {
                    "url": url,
                    "filepath": filepath,
                    "status": "success",
                    "size": downloaded,
                    "attempts": attempt,
                }
        except (URLError, HTTPError, OSError, TimeoutError) as e:
            if attempt < max_retries:
                backoff = (2 ** (attempt - 1)) * 0.5
                time.sleep(backoff)
                continue
            return {
                "url": url,
                "filepath": filepath,
                "status": "failed",
                "error": str(e),
                "attempts": attempt,
            }

    return {"url": url, "filepath": filepath, "status": "failed", "error": "Max retries exceeded"}


def concurrent_download(
    urls: List[str],
    output_dir: str,
    max_workers: int = 4,
    max_retries: int = 3,
    timeout: int = 30,
    progress_callback: Optional[Callable[[Dict[str, str]], None]] = None,
) -> Dict[str, object]:
    """Download multiple files concurrently with ThreadPoolExecutor.

    Args:
        urls: List of URLs to download.
        output_dir: Directory to save downloaded files.
        max_workers: Maximum number of concurrent download threads.
        max_retries: Maximum retry attempts per URL with exponential backoff.
        timeout: Timeout in seconds for each HTTP request.
        progress_callback: Optional callback function called after each download completes.

    Returns:
        Summary dict with succeeded count, failed count, and error details.
    """
    os.makedirs(output_dir, exist_ok=True)

    results = []
    lock = threading.Lock()

    def task_wrapper(url: str) -> Dict[str, str]:
        result = download_file(url, output_dir, timeout=timeout, max_retries=max_retries)
        with lock:
            results.append(result)
            if progress_callback:
                progress_callback(result)
        return result

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(task_wrapper, url): url for url in urls}

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                url = futures[future]
                with lock:
                    results.append({
                        "url": url,
                        "status": "failed",
                        "error": str(e),
                    })

    succeeded = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]

    return {
        "total": len(urls),
        "succeeded": len(succeeded),
        "failed": len(failed),
        "results": results,
        "errors": [{"url": r["url"], "error": r.get("error", "")} for r in failed],
    }


if __name__ == "__main__":
    def on_progress(result: dict):
        status = result["status"]
        url = result["url"]
        if status == "success":
            print(f"  [OK] {url} -> {result['filepath']} ({result['size']} bytes)")
        else:
            print(f"  [FAIL] {url} -> {result.get('error', 'unknown')}")

    test_urls = [
        "https://httpbin.org/bytes/1024",
        "https://httpbin.org/bytes/2048",
        "https://httpbin.org/bytes/512",
        "https://httpbin.org/bytes/4096",
    ]

    print("Starting concurrent download...")
    summary = concurrent_download(
        urls=test_urls,
        output_dir="./downloads",
        max_workers=4,
        max_retries=3,
        timeout=30,
        progress_callback=on_progress,
    )

    print(f"\nSummary: {summary['succeeded']}/{summary['total']} succeeded, {summary['failed']} failed")
