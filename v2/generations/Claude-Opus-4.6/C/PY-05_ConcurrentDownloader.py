import os
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from threading import Lock
from typing import Callable, Optional


@dataclass
class DownloadResult:
    url: str
    success: bool
    filepath: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 0
    size: int = 0
    elapsed: float = 0.0


@dataclass
class DownloadSummary:
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    total_bytes: int = 0
    total_time: float = 0.0
    results: list = field(default_factory=list)
    errors: list = field(default_factory=list)


class ConcurrentDownloader:
    def __init__(
        self,
        max_workers: int = 4,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        timeout: int = 30,
        output_dir: str = ".",
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ):
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        self.output_dir = output_dir
        self.progress_callback = progress_callback
        self._lock = Lock()
        self._completed = 0
        self._total = 0

    def _notify_progress(self, url: str) -> None:
        if self.progress_callback:
            with self._lock:
                self._completed += 1
                current = self._completed
            self.progress_callback(url, current, self._total)

    def _download_one(self, url: str) -> DownloadResult:
        start = time.monotonic()
        filename = os.path.basename(url.split("?")[0]) or "download"
        filepath = os.path.join(self.output_dir, filename)
        last_error: Optional[str] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = resp.read()
                os.makedirs(self.output_dir, exist_ok=True)
                with open(filepath, "wb") as f:
                    f.write(data)
                elapsed = time.monotonic() - start
                self._notify_progress(url)
                return DownloadResult(
                    url=url,
                    success=True,
                    filepath=filepath,
                    attempts=attempt,
                    size=len(data),
                    elapsed=elapsed,
                )
            except (urllib.error.URLError, OSError, TimeoutError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt < self.max_retries:
                    time.sleep(self.backoff_factor * (2 ** (attempt - 1)))

        elapsed = time.monotonic() - start
        self._notify_progress(url)
        return DownloadResult(
            url=url,
            success=False,
            error=last_error,
            attempts=self.max_retries,
            elapsed=elapsed,
        )

    def download(self, urls: list[str]) -> DownloadSummary:
        self._total = len(urls)
        self._completed = 0
        summary = DownloadSummary(total=len(urls))
        overall_start = time.monotonic()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._download_one, u): u for u in urls}
            for future in as_completed(futures):
                result = future.result()
                summary.results.append(result)
                if result.success:
                    summary.succeeded += 1
                    summary.total_bytes += result.size
                else:
                    summary.failed += 1
                    summary.errors.append(
                        {"url": result.url, "error": result.error}
                    )

        summary.total_time = time.monotonic() - overall_start
        return summary
