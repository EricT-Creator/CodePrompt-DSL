import os
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

ProgressCallback = Callable[[str, int, int, bool, str], None]


def default_progress_callback(url: str, completed: int, total: int, success: bool, message: str) -> None:
    status = "OK" if success else "FAILED"
    print(f"[{completed}/{total}] {status} {url} -> {message}")


def filename_from_url(url: str, fallback_index: int) -> str:
    parsed = urllib.parse.urlparse(url)
    name = os.path.basename(parsed.path)
    if not name:
        name = f"download_{fallback_index}"
    return name


def download_one(url: str, output_dir: str, fallback_index: int, timeout: int = 30, max_retries: int = 3) -> tuple[bool, str]:
    destination = os.path.join(output_dir, filename_from_url(url, fallback_index))
    last_error = "unknown error"

    for attempt in range(max_retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "ConcurrentDownloader/1.0"})
            with urllib.request.urlopen(request, timeout=timeout) as response, open(destination, "wb") as file_handle:
                file_handle.write(response.read())
            return True, destination
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as error:
            last_error = str(error)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    return False, last_error


def download_urls(
    urls: list[str],
    output_dir: str,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)
    callback = progress_callback or default_progress_callback

    succeeded = 0
    failed = 0
    errors: dict[str, str] = {}
    completed = 0

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_map = {
            executor.submit(download_one, url, output_dir, index, 30, 3): url
            for index, url in enumerate(urls, start=1)
        }

        for future in as_completed(future_map):
            url = future_map[future]
            try:
                success, detail = future.result()
            except Exception as error:
                success, detail = False, str(error)

            completed += 1
            if success:
                succeeded += 1
            else:
                failed += 1
                errors[url] = detail
            callback(url, completed, len(urls), success, detail)

    return {
        "succeeded": succeeded,
        "failed": failed,
        "errors": errors,
    }


if __name__ == "__main__":
    SAMPLE_URLS = [
        "https://example.com/",
        "https://httpbin.org/bytes/32",
    ]
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "downloads")
    summary = download_urls(SAMPLE_URLS, OUTPUT_DIR)
    print(summary)
