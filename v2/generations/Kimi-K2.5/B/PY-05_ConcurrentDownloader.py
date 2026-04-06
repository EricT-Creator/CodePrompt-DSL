import os
import time
import hashlib
from typing import List, Dict, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from socket import timeout as SocketTimeout


class ConcurrentDownloader:
    """Concurrent file downloader using threading and urllib."""
    
    def __init__(
        self,
        max_workers: int = 4,
        timeout: int = 30,
        max_retries: int = 3,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ):
        self.max_workers = max_workers
        self.timeout = timeout
        self.max_retries = max_retries
        self.progress_callback = progress_callback
    
    def _exponential_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        return min(2 ** attempt, 60)  # Cap at 60 seconds
    
    def _download_single(
        self,
        url: str,
        output_dir: str,
        filename: Optional[str] = None
    ) -> Dict[str, any]:
        """Download a single file with retry logic."""
        result = {
            "url": url,
            "success": False,
            "filename": None,
            "bytes_downloaded": 0,
            "error": None,
            "retries": 0
        }
        
        # Generate filename if not provided
        if not filename:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"download_{url_hash}"
        
        output_path = os.path.join(output_dir, filename)
        
        for attempt in range(self.max_retries + 1):
            try:
                # Create request with headers
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
                }
                request = Request(url, headers=headers)
                
                # Open connection with timeout
                response = urlopen(request, timeout=self.timeout)
                
                # Get content length if available
                content_length = response.headers.get('Content-Length')
                total_size = int(content_length) if content_length else 0
                
                # Download file
                bytes_downloaded = 0
                chunk_size = 8192
                
                with open(output_path, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        
                        # Call progress callback
                        if self.progress_callback:
                            self.progress_callback(url, bytes_downloaded, total_size)
                
                result["success"] = True
                result["filename"] = filename
                result["bytes_downloaded"] = bytes_downloaded
                return result
                
            except (HTTPError, URLError, SocketTimeout) as e:
                result["retries"] = attempt + 1
                result["error"] = str(e)
                
                if attempt < self.max_retries:
                    delay = self._exponential_backoff(attempt)
                    time.sleep(delay)
                else:
                    # Clean up partial download
                    if os.path.exists(output_path):
                        os.remove(output_path)
        
        return result
    
    def download(
        self,
        urls: List[str],
        output_dir: str,
        filenames: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """
        Download multiple files concurrently.
        
        Args:
            urls: List of URLs to download
            output_dir: Directory to save files
            filenames: Optional list of filenames (must match urls length)
        
        Returns:
            Summary dict with results
        """
        # Validate inputs
        if not urls:
            return {"error": "No URLs provided"}
        
        if filenames and len(filenames) != len(urls):
            return {"error": "Filenames list must match URLs list length"}
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Prepare download tasks
        tasks = []
        for i, url in enumerate(urls):
            filename = filenames[i] if filenames else None
            tasks.append((url, filename))
        
        # Execute downloads concurrently
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {
                executor.submit(self._download_single, url, output_dir, filename): url
                for url, filename in tasks
            }
            
            for future in as_completed(future_to_url):
                result = future.result()
                results.append(result)
        
        # Build summary
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        total_bytes = sum(r["bytes_downloaded"] for r in successful)
        total_retries = sum(r["retries"] for r in results)
        
        return {
            "total_urls": len(urls),
            "successful": len(successful),
            "failed": len(failed),
            "total_bytes_downloaded": total_bytes,
            "total_retries": total_retries,
            "output_directory": output_dir,
            "results": results
        }


def default_progress_callback(url: str, downloaded: int, total: int):
    """Default progress callback that prints progress."""
    if total > 0:
        percent = (downloaded / total) * 100
        print(f"  {url[:50]:<50} {percent:>6.1f}% ({downloaded}/{total} bytes)")
    else:
        print(f"  {url[:50]:<50} {downloaded} bytes downloaded")


def main():
    """Example usage."""
    # Example URLs (replace with actual URLs)
    urls = [
        "https://www.example.com/file1.txt",
        "https://www.example.com/file2.txt",
        "https://www.example.com/file3.txt",
    ]
    
    output_dir = "downloads"
    
    downloader = ConcurrentDownloader(
        max_workers=4,
        timeout=30,
        max_retries=3,
        progress_callback=default_progress_callback
    )
    
    print(f"Starting download of {len(urls)} files...")
    summary = downloader.download(urls, output_dir)
    
    print("\n" + "="*60)
    print("DOWNLOAD SUMMARY")
    print("="*60)
    print(f"Total URLs:      {summary['total_urls']}")
    print(f"Successful:      {summary['successful']}")
    print(f"Failed:          {summary['failed']}")
    print(f"Total bytes:     {summary['total_bytes_downloaded']:,}")
    print(f"Total retries:   {summary['total_retries']}")
    print(f"Output dir:      {summary['output_directory']}")
    
    if summary['failed'] > 0:
        print("\nFailed downloads:")
        for r in summary['results']:
            if not r['success']:
                print(f"  - {r['url']}: {r['error']}")


if __name__ == "__main__":
    main()
