import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

ProgressCallback = Callable[[Dict[str, object]], None]


def _filename_from_url(url: str, index: int) -> str:
    parsed = urllib.parse.urlparse(url)
    name = os.path.basename(parsed.path) or f"download_{index + 1}"
    if not Path(name).suffix:
        name = f"{name}.bin"
    return name


def download_files(
    urls: Iterable[str],
    output_dir: str,
    max_workers: int = 4,
    timeout: int = 30,
    progress_callback: Optional[ProgressCallback] = None,
) -> Dict[str, object]:
    url_list = list(urls)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    lock = threading.Lock()
    summary: Dict[str, object] = {
        "succeeded": 0,
        "failed": 0,
        "errors": [],
    }

    def notify(payload: Dict[str, object]) -> None:
        if progress_callback is not None:
            progress_callback(payload)

    def worker(index: int, url: str) -> Dict[str, object]:
        filename = _filename_from_url(url, index)
        target_path = destination / f"{index + 1:03d}_{filename}"
        last_error = ""

        for attempt in range(1, 4):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "ConcurrentDownloader/1.0"})
                with urllib.request.urlopen(request, timeout=timeout) as response, open(target_path, "wb") as handle:
                    while True:
                        chunk = response.read(1024 * 64)
                        if not chunk:
                            break
                        handle.write(chunk)

                result = {
                    "url": url,
                    "path": str(target_path),
                    "success": True,
                    "attempt": attempt,
                }
                with lock:
                    summary["succeeded"] = int(summary["succeeded"]) + 1
                notify(result)
                return result
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
                last_error = str(exc)
                if attempt < 3:
                    time.sleep(2 ** (attempt - 1))

        failure = {
            "url": url,
            "path": str(target_path),
            "success": False,
            "attempt": 3,
            "error": last_error,
        }
        with lock:
            summary["failed"] = int(summary["failed"]) + 1
            errors = list(summary["errors"])
            errors.append({"url": url, "error": last_error})
            summary["errors"] = errors
        notify(failure)
        return failure

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(worker, index, url) for index, url in enumerate(url_list)]
        for future in as_completed(futures):
            future.result()

    return summary


if __name__ == "__main__":
    def print_progress(info: Dict[str, object]) -> None:
        status = "OK" if info.get("success") else "FAIL"
        print(f"[{status}] {info.get('url')} -> {info.get('path')}")

    demo_urls = []
    print(download_files(demo_urls, "downloads", progress_callback=print_progress))
