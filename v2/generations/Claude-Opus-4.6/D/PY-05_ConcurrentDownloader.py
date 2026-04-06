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

    def _notify(self, url: str) -> None:
        if self.progress_callback:
            with self._lock:
                self._completed += 1
                n = self._completed
            self.progress_callback(url, n, self._total)

    def _fetch(self, url: str) -> DownloadResult:
        t0 = time.monotonic()
        fname = os.path.basename(url.split("?")[0]) or "file"
        dest = os.path.join(self.output_dir, fname)
        err: Optional[str] = None

        for i in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    body = r.read()
                os.makedirs(self.output_dir, exist_ok=True)
                with open(dest, "wb") as fp:
                    fp.write(body)
                dt = time.monotonic() - t0
                self._notify(url)
                return DownloadResult(
                    url=url, success=True, filepath=dest,
                    attempts=i, size=len(body), elapsed=dt,
                )
            except (urllib.error.URLError, OSError, TimeoutError) as exc:
                err = f"{type(exc).__name__}: {exc}"
                if i < self.max_retries:
                    time.sleep(self.backoff_factor * (2 ** (i - 1)))

        dt = time.monotonic() - t0
        self._notify(url)
        return DownloadResult(
            url=url, success=False, error=err,
            attempts=self.max_retries, elapsed=dt,
        )

    def download(self, urls: list[str]) -> DownloadSummary:
        self._total = len(urls)
        self._completed = 0
        summary = DownloadSummary(total=len(urls))
        t0 = time.monotonic()

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futs = {pool.submit(self._fetch, u): u for u in urls}
            for fut in as_completed(futs):
                res = fut.result()
                summary.results.append(res)
                if res.success:
                    summary.succeeded += 1
                    summary.total_bytes += res.size
                else:
                    summary.failed += 1
                    summary.errors.append({"url": res.url, "error": res.error})

        summary.total_time = time.monotonic() - t0
        return summary
