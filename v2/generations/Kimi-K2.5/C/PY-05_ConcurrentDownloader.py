import os
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass

@dataclass
class DownloadResult:
    url: str
    success: bool
    file_path: Optional[str]
    error: Optional[str]
    download_time: float
    file_size: int

class ConcurrentDownloader:
    def __init__(
        self,
        max_workers: int = 4,
        max_retries: int = 3,
        timeout: int = 30,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ):
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.timeout = timeout
        self.progress_callback = progress_callback
        self.results: List[DownloadResult] = []
    
    def _download_with_retry(
        self,
        url: str,
        output_dir: str,
        filename: Optional[str] = None
    ) -> DownloadResult:
        start_time = time.time()
        
        if filename is None:
            filename = os.path.basename(url.split('?')[0]) or f"download_{int(time.time())}"
        
        file_path = os.path.join(output_dir, filename)
        
        for attempt in range(self.max_retries):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
                }
                request = urllib.request.Request(url, headers=headers)
                
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    total_size = int(response.headers.get('Content-Length', 0))
                    downloaded = 0
                    chunk_size = 8192
                    
                    with open(file_path, 'wb') as f:
                        while True:
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if self.progress_callback:
                                self.progress_callback(url, downloaded, total_size)
                
                download_time = time.time() - start_time
                file_size = os.path.getsize(file_path)
                
                return DownloadResult(
                    url=url,
                    success=True,
                    file_path=file_path,
                    error=None,
                    download_time=download_time,
                    file_size=file_size
                )
            
            except urllib.error.HTTPError as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                download_time = time.time() - start_time
                return DownloadResult(
                    url=url,
                    success=False,
                    file_path=None,
                    error=f"HTTP Error {e.code}: {e.reason}",
                    download_time=download_time,
                    file_size=0
                )
            
            except urllib.error.URLError as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                download_time = time.time() - start_time
                return DownloadResult(
                    url=url,
                    success=False,
                    file_path=None,
                    error=f"URL Error: {str(e.reason)}",
                    download_time=download_time,
                    file_size=0
                )
            
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                download_time = time.time() - start_time
                return DownloadResult(
                    url=url,
                    success=False,
                    file_path=None,
                    error=f"Error: {str(e)}",
                    download_time=download_time,
                    file_size=0
                )
        
        download_time = time.time() - start_time
        return DownloadResult(
            url=url,
            success=False,
            file_path=None,
            error="Max retries exceeded",
            download_time=download_time,
            file_size=0
        )
    
    def download(
        self,
        urls: List[str],
        output_dir: str,
        filenames: Optional[List[str]] = None
    ) -> Dict:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        self.results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            for i, url in enumerate(urls):
                filename = filenames[i] if filenames and i < len(filenames) else None
                future = executor.submit(self._download_with_retry, url, output_dir, filename)
                futures[future] = url
            
            for future in as_completed(futures):
                result = future.result()
                self.results.append(result)
                
                status = "✓" if result.success else "✗"
                print(f"{status} {result.url} - {result.file_size} bytes in {result.download_time:.2f}s")
                if result.error:
                    print(f"  Error: {result.error}")
        
        return self.get_summary()
    
    def get_summary(self) -> Dict:
        succeeded = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        
        total_size = sum(r.file_size for r in succeeded)
        total_time = sum(r.download_time for r in self.results)
        
        return {
            "total": len(self.results),
            "succeeded": len(succeeded),
            "failed": len(failed),
            "total_size_bytes": total_size,
            "total_time_seconds": round(total_time, 2),
            "errors": [
                {"url": r.url, "error": r.error}
                for r in failed
            ]
        }

def progress_callback(url: str, downloaded: int, total: int):
    if total > 0:
        percent = (downloaded / total) * 100
        print(f"  Progress: {percent:.1f}% ({downloaded}/{total} bytes)", end='\r')
    else:
        print(f"  Downloaded: {downloaded} bytes", end='\r')

def main():
    urls = [
        "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        "https://www.google.com/robots.txt",
    ]
    
    output_dir = "./downloads"
    
    print(f"Starting download of {len(urls)} files to {output_dir}")
    print(f"Max workers: 4, Max retries: 3, Timeout: 30s")
    print("-" * 60)
    
    downloader = ConcurrentDownloader(
        max_workers=4,
        max_retries=3,
        timeout=30,
        progress_callback=progress_callback
    )
    
    summary = downloader.download(urls, output_dir)
    
    print("\n" + "=" * 60)
    print("Download Summary:")
    print(f"  Total files: {summary['total']}")
    print(f"  Succeeded: {summary['succeeded']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Total size: {summary['total_size_bytes']} bytes")
    print(f"  Total time: {summary['total_time_seconds']}s")
    
    if summary['errors']:
        print("\nErrors:")
        for error in summary['errors']:
            print(f"  - {error['url']}: {error['error']}")

if __name__ == "__main__":
    main()
