import os
import time
import threading
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, field


@dataclass
class DownloadResult:
    url: str
    filepath: str
    success: bool
    error: Optional[str] = None
    retries: int = 0
    size_bytes: int = 0
    elapsed_seconds: float = 0.0


@dataclass
class DownloadSummary:
    succeeded: int = 0
    failed: int = 0
    total: int = 0
    results: List[DownloadResult] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)


def _get_filename_from_url(url: str) -> str:
    path = urllib.request.urlparse(url).path
    filename = os.path.basename(path)
    if not filename:
        filename = "download_" + str(hash(url) % 100000)
    return filename


def _download_single(
    url: str,
    output_dir: str,
    max_retries: int = 3,
    timeout: int = 30,
) -> DownloadResult:
    filename = _get_filename_from_url(url)
    filepath = os.path.join(output_dir, filename)

    start_time = time.monotonic()
    last_error = None

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ConcurrentDownloader/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = response.read()
                with open(filepath, "wb") as f:
                    f.write(data)
                elapsed = time.monotonic() - start_time
                return DownloadResult(
                    url=url,
                    filepath=filepath,
                    success=True,
                    retries=attempt,
                    size_bytes=len(data),
                    elapsed_seconds=round(elapsed, 3),
                )
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                backoff = (2 ** attempt) + (hash(url) % 100) / 100.0
                time.sleep(backoff)

    elapsed = time.monotonic() - start_time
    return DownloadResult(
        url=url,
        filepath=filepath,
        success=False,
        error=last_error,
        retries=max_retries,
        elapsed_seconds=round(elapsed, 3),
    )


def download(
    urls: List[str],
    output_dir: str,
    max_workers: int = 4,
    max_retries: int = 3,
    timeout: int = 30,
    progress_callback: Optional[Callable[[DownloadResult, int, int], None]] = None,
) -> Dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)

    summary = DownloadSummary(total=len(urls))
    completed_count = 0
    lock = threading.Lock()

    def on_complete(result: DownloadResult):
        nonlocal completed_count
        with lock:
            completed_count += 1
            summary.results.append(result)
            if result.success:
                summary.succeeded += 1
            else:
                summary.failed += 1
                summary.errors[result.url] = result.error or "Unknown error"

            if progress_callback:
                try:
                    progress_callback(result, completed_count, summary.total)
                except Exception:
                    pass

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _download_single, url, output_dir, max_retries, timeout
            ): url
            for url in urls
        }

        for future in as_completed(futures):
            try:
                result = future.result()
            except Exception as e:
                url = futures[future]
                result = DownloadResult(
                    url=url,
                    filepath="",
                    success=False,
                    error=str(e),
                )
            on_complete(result)

    return {
        "succeeded": summary.succeeded,
        "failed": summary.failed,
        "total": summary.total,
        "errors": summary.errors,
        "results": [
            {
                "url": r.url,
                "filepath": r.filepath,
                "success": r.success,
                "error": r.error,
                "retries": r.retries,
                "size_bytes": r.size_bytes,
                "elapsed_seconds": r.elapsed_seconds,
            }
            for r in summary.results
        ],
    }


def default_progress_callback(result: DownloadResult, completed: int, total: int):
    status = "OK" if result.success else f"FAILED ({result.error})"
    print(f"[{completed}/{total}] {result.url} - {status}")


if __name__ == "__main__":
    test_urls = [
        "https://httpbin.org/bytes/1024",
        "https://httpbin.org/bytes/2048",
        "https://httpbin.org/bytes/512",
        "https://httpbin.org/status/404",
    ]
    output = os.path.join(os.path.dirname(__file__), "downloads")
    result = download(
        urls=test_urls,
        output_dir=output,
        max_workers=4,
        progress_callback=default_progress_callback,
    )
    print(f"\nSummary: {result['succeeded']} succeeded, {result['failed']} failed out of {result['total']}")
    if result["errors"]:
        print("Errors:")
        for url, err in result["errors"].items():
            print(f"  {url}: {err}")
