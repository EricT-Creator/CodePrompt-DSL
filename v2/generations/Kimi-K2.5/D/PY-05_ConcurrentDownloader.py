import urllib.request
import urllib.error
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass
import time

@dataclass
class DownloadResult:
    url: str
    success: bool
    filepath: Optional[str] = None
    error: Optional[str] = None
    retries: int = 0

class ConcurrentDownloader:
    def __init__(self, max_workers: int = 4, timeout: int = 30):
        self.max_workers = max_workers
        self.timeout = timeout
    
    def download_single(
        self, 
        url: str, 
        output_dir: str, 
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> DownloadResult:
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                filename = os.path.basename(url.split('?')[0]) or f"download_{int(time.time())}"
                filepath = os.path.join(output_dir, filename)
                
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
                })
                
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    total_size = int(response.headers.get('Content-Length', 0))
                    downloaded = 0
                    chunk_size = 8192
                    
                    os.makedirs(output_dir, exist_ok=True)
                    
                    with open(filepath, 'wb') as f:
                        while True:
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback:
                                progress_callback(url, downloaded, total_size)
                
                return DownloadResult(url=url, success=True, filepath=filepath, retries=retry_count)
                
            except urllib.error.HTTPError as e:
                retry_count += 1
                if retry_count >= max_retries:
                    return DownloadResult(url=url, success=False, error=f"HTTP {e.code}: {e.reason}", retries=retry_count)
                time.sleep(2 ** retry_count)
            except urllib.error.URLError as e:
                retry_count += 1
                if retry_count >= max_retries:
                    return DownloadResult(url=url, success=False, error=f"URL Error: {str(e.reason)}", retries=retry_count)
                time.sleep(2 ** retry_count)
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    return DownloadResult(url=url, success=False, error=str(e), retries=retry_count)
                time.sleep(2 ** retry_count)
        
        return DownloadResult(url=url, success=False, error="Max retries exceeded", retries=retry_count)
    
    def download(
        self,
        urls: List[str],
        output_dir: str,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, any]:
        results: List[DownloadResult] = []
        success_count = 0
        failed_count = 0
        errors: Dict[str, str] = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {
                executor.submit(self.download_single, url, output_dir, progress_callback): url 
                for url in urls
            }
            
            for future in as_completed(future_to_url):
                result = future.result()
                results.append(result)
                
                if result.success:
                    success_count += 1
                else:
                    failed_count += 1
                    errors[result.url] = result.error or "Unknown error"
        
        return {
            "total": len(urls),
            "success": success_count,
            "failed": failed_count,
            "results": [
                {
                    "url": r.url,
                    "success": r.success,
                    "filepath": r.filepath,
                    "retries": r.retries
                } for r in results
            ],
            "errors": errors
        }


def download_files(
    urls: List[str],
    output_dir: str,
    max_workers: int = 4,
    timeout: int = 30,
    progress_callback: Optional[Callable[[str, int, int], None]] = None
) -> Dict[str, any]:
    downloader = ConcurrentDownloader(max_workers=max_workers, timeout=timeout)
    return downloader.download(urls, output_dir, progress_callback)


if __name__ == "__main__":
    def progress(url: str, downloaded: int, total: int):
        percent = (downloaded / total * 100) if total > 0 else 0
        print(f"{url}: {percent:.1f}%")
    
    urls = [
        "https://example.com/file1.txt",
        "https://example.com/file2.txt",
    ]
    
    result = download_files(urls, "./downloads", progress_callback=progress)
    print(f"\n汇总: 成功 {result['success']}, 失败 {result['failed']}")
