import os
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, Dict, Any, Optional


class ConcurrentDownloader:
    def __init__(
        self,
        max_workers: int = 4,
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.max_workers = max_workers
        self.timeout = timeout
        self.max_retries = max_retries

    def _download_with_retry(
        self,
        url: str,
        output_path: str,
        progress_callback: Optional[Callable[[str, bool, str], None]] = None
    ) -> Dict[str, Any]:
        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
                    }
                )
                
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    total_size = int(response.headers.get('Content-Length', 0))
                    downloaded = 0
                    chunk_size = 8192
                    
                    with open(output_path, 'wb') as f:
                        while True:
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                
                result = {
                    "url": url,
                    "output_path": output_path,
                    "success": True,
                    "size": downloaded,
                    "error": None
                }
                
                if progress_callback:
                    progress_callback(url, True, f"Downloaded {downloaded} bytes")
                
                return result
                
            except urllib.error.HTTPError as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                error_msg = f"HTTP Error {e.code}: {e.reason}"
                
            except urllib.error.URLError as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                error_msg = f"URL Error: {e.reason}"
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                error_msg = f"Error: {str(e)}"
        
        result = {
            "url": url,
            "output_path": output_path,
            "success": False,
            "size": 0,
            "error": error_msg
        }
        
        if progress_callback:
            progress_callback(url, False, error_msg)
        
        return result

    def download(
        self,
        urls: List[str],
        output_dir: str,
        progress_callback: Optional[Callable[[str, bool, str], None]] = None
    ) -> Dict[str, Any]:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        results = []
        succeeded = 0
        failed = 0
        errors = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {}
            
            for url in urls:
                filename = os.path.basename(url.split('?')[0]) or f"download_{int(time.time())}"
                output_path = os.path.join(output_dir, filename)
                
                future = executor.submit(
                    self._download_with_retry,
                    url,
                    output_path,
                    progress_callback
                )
                future_to_url[future] = url
            
            for future in as_completed(future_to_url):
                result = future.result()
                results.append(result)
                
                if result["success"]:
                    succeeded += 1
                else:
                    failed += 1
                    errors.append({
                        "url": result["url"],
                        "error": result["error"]
                    })
        
        return {
            "total": len(urls),
            "succeeded": succeeded,
            "failed": failed,
            "errors": errors,
            "results": results
        }


def download_files(
    urls: List[str],
    output_dir: str,
    max_workers: int = 4,
    timeout: int = 30,
    progress_callback: Optional[Callable[[str, bool, str], None]] = None
) -> Dict[str, Any]:
    downloader = ConcurrentDownloader(
        max_workers=max_workers,
        timeout=timeout
    )
    return downloader.download(urls, output_dir, progress_callback)


if __name__ == "__main__":
    def on_progress(url: str, success: bool, message: str):
        status = "✓" if success else "✗"
        print(f"{status} {url}: {message}")
    
    test_urls = [
        "https://www.example.com",
        "https://httpbin.org/get",
    ]
    
    result = download_files(
        urls=test_urls,
        output_dir="./downloads",
        max_workers=2,
        progress_callback=on_progress
    )
    
    print("\n--- Summary ---")
    print(f"Total: {result['total']}")
    print(f"Succeeded: {result['succeeded']}")
    print(f"Failed: {result['failed']}")
    
    if result['errors']:
        print("\nErrors:")
        for error in result['errors']:
            print(f"  - {error['url']}: {error['error']}")
