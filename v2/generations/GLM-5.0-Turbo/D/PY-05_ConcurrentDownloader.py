"""
并发下载器 - 使用ThreadPoolExecutor + urllib
指数退避重试，超时控制，进度回调
"""

import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from typing import Callable, Optional


def download_single(
    url: str,
    output_dir: str,
    timeout: int = 30,
    max_retries: int = 3,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> dict:
    filename = url.rsplit("/", 1)[-1] or "index.html"
    if "?" in filename:
        filename = filename.split("?")[0]

    filepath = os.path.join(output_dir, filename)

    for attempt in range(max_retries):
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
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
                            progress_callback(url, downloaded, total_size)

            return {
                "url": url,
                "filepath": filepath,
                "filename": filename,
                "size": downloaded,
                "success": True,
                "attempts": attempt + 1,
            }

        except (URLError, HTTPError, OSError) as e:
            if attempt < max_retries - 1:
                wait = min(2 ** attempt, 30)
                time.sleep(wait)
                continue
            return {
                "url": url,
                "filepath": filepath,
                "filename": filename,
                "size": 0,
                "success": False,
                "error": str(e),
                "attempts": attempt + 1,
            }

    return {
        "url": url,
        "filepath": filepath,
        "filename": filename,
        "size": 0,
        "success": False,
        "error": "重试次数耗尽",
        "attempts": max_retries,
    }


class ConcurrentDownloader:
    def __init__(
        self,
        max_workers: int = 4,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.max_workers = max_workers
        self.timeout = timeout
        self.max_retries = max_retries
        self._lock = threading.Lock()
        self._completed = 0
        self._total = 0

    def _progress(self, url: str, downloaded: int, total: int):
        with self._lock:
            self._completed += 1
            current = self._completed
            total = self._total
        print(f"  [{current}/{total}] {url[:60]}... ({downloaded} bytes)")

    def download(
        self,
        urls: list[str],
        output_dir: str,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> dict:
        os.makedirs(output_dir, exist_ok=True)

        self._total = len(urls)
        self._completed = 0

        results = {"success": [], "failed": []}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {
                executor.submit(
                    download_single,
                    url,
                    output_dir,
                    self.timeout,
                    self.max_retries,
                    progress_callback or self._progress,
                ): url
                for url in urls
            }

            for future in as_completed(future_to_url):
                result = future.result()
                if result["success"]:
                    results["success"].append(result)
                else:
                    results["failed"].append(result)

        summary = {
            "total": len(urls),
            "success_count": len(results["success"]),
            "failed_count": len(results["failed"]),
            "success_files": [r["filepath"] for r in results["success"]],
            "failed_details": [
                {"url": r["url"], "error": r.get("error", "unknown")}
                for r in results["failed"]
            ],
        }

        return summary


def main():
    urls = [
        "https://www.python.org",
        "https://httpbin.org/get",
        "https://httpbin.org/ip",
        "https://httpbin.org/headers",
        "https://httpbin.org/user-agent",
    ]

    downloader = ConcurrentDownloader(max_workers=4, timeout=30, max_retries=3)
    output_dir = "./downloads"

    print(f"开始下载 {len(urls)} 个文件到 {output_dir}/")
    result = downloader.download(urls, output_dir)
    print(f"\n下载完成: 成功 {result['success_count']}/{result['total']}")

    if result["failed_details"]:
        print("失败详情:")
        for fd in result["failed_details"]:
            print(f"  - {fd['url']}: {fd['error']}")

    return result


if __name__ == "__main__":
    main()
