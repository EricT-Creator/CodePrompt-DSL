import os
import sys
import time
import math
import threading
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional


class ConcurrentDownloader:
    def __init__(
        self,
        max_workers: int = 4,
        max_retries: int = 3,
        timeout: int = 30,
        chunk_size: int = 8192,
    ):
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.timeout = timeout
        self.chunk_size = chunk_size
        self._lock = threading.Lock()
        self._progress_lock = threading.Lock()
        self._progress_callback: Optional[callable] = None
        self.results: Dict[str, Dict] = {}

    def set_progress_callback(self, callback: callable):
        self._progress_callback = callback

    def _report_progress(self, url: str, status: str, message: str = ""):
        if self._progress_callback:
            with self._progress_lock:
                self._progress_callback(url, status, message)

    def _download_one(self, url: str, output_dir: str) -> Dict:
        parsed = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed.path) or "index.html"
        if not filename:
            filename = f"download_{hash(url) % 100000}"
        filepath = os.path.join(output_dir, filename)

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                self._report_progress(url, "downloading", f"attempt {attempt}/{self.max_retries}")
                req = urllib.request.Request(url, headers={"User-Agent": "ConcurrentDownloader/1.0"})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    with open(filepath, "wb") as f:
                        while True:
                            chunk = resp.read(self.chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                self._report_progress(url, "success", filepath)
                return {"url": url, "path": filepath, "status": "success", "attempts": attempt}

            except urllib.error.URLError as e:
                last_error = str(e.reason) if hasattr(e, "reason") else str(e)
                self._report_progress(url, "retrying", f"attempt {attempt} failed: {last_error}")
                if attempt < self.max_retries:
                    delay = min(2 ** attempt, 10)
                    time.sleep(delay)

            except Exception as e:
                last_error = str(e)
                self._report_progress(url, "retrying", f"attempt {attempt} failed: {last_error}")
                if attempt < self.max_retries:
                    delay = min(2 ** attempt, 10)
                    time.sleep(delay)

        self._report_progress(url, "failed", last_error or "unknown error")
        return {"url": url, "path": None, "status": "failed", "error": last_error, "attempts": self.max_retries}

    def download(self, urls: List[str], output_dir: str) -> Dict:
        os.makedirs(output_dir, exist_ok=True)
        results = {"succeeded": [], "failed": [], "errors": []}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._download_one, url, output_dir): url for url in urls}
            for future in as_completed(futures):
                result = future.result()
                with self._lock:
                    self.results[result["url"]] = result
                    if result["status"] == "success":
                        results["succeeded"].append({"url": result["url"], "path": result["path"]})
                    else:
                        results["failed"].append({"url": result["url"], "error": result.get("error")})
                        results["errors"].append(result.get("error"))

        results["summary"] = {
            "total": len(urls),
            "succeeded": len(results["succeeded"]),
            "failed": len(results["failed"]),
        }
        return results


import urllib.parse


def progress_callback(url: str, status: str, message: str):
    print(f"  [{status.upper()}] {url[:60]}{'...' if len(url) > 60 else ''} {message}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python ConcurrentDownloader.py <url_list_file_or_urls> <output_dir>")
        print("  Or pass URLs directly: python ConcurrentDownloader.py http://a.com http://b.com ./downloads")
        sys.exit(1)

    args = sys.argv[1:]
    if len(args) == 2:
        url_file = args[0]
        output_dir = args[1]
        with open(url_file, "r") as f:
            urls = [line.strip() for line in f if line.strip() and line.strip().startswith("http")]
    else:
        output_dir = args[-1]
        urls = [u for u in args[:-1] if u.startswith("http")]

    if not urls:
        print("No valid URLs provided.")
        sys.exit(1)

    print(f"Downloading {len(urls)} URLs to '{output_dir}' (max_workers=4, timeout=30s, max_retries=3)")
    downloader = ConcurrentDownloader(max_workers=4, max_retries=3, timeout=30)
    downloader.set_progress_callback(progress_callback)
    results = downloader.download(urls, output_dir)
    print(f"\n=== Summary ===")
    print(f"Total: {results['summary']['total']}")
    print(f"Succeeded: {results['summary']['succeeded']}")
    print(f"Failed: {results['summary']['failed']}")
    return results


if __name__ == "__main__":
    main()
