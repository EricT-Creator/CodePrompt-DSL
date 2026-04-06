import urllib.request
import urllib.error
import ssl
import os
import time
import threading
import concurrent.futures
import queue
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Data classes
@dataclass
class DownloadResult:
    url: str
    filename: str
    success: bool
    size_bytes: int = 0
    duration_seconds: float = 0.0
    retries: int = 0
    error: Optional[str] = None
    
@dataclass
class DownloadStats:
    total_urls: int = 0
    succeeded: int = 0
    failed: int = 0
    total_bytes: int = 0
    total_time_seconds: float = 0.0
    average_speed_bps: float = 0.0
    error_details: List[str] = field(default_factory=list)

@dataclass
class DownloadProgress:
    completed: int = 0
    total: int = 0
    current_url: str = ""
    current_filename: str = ""
    bytes_downloaded: int = 0
    total_bytes: int = 0

# Main downloader class
class ConcurrentDownloader:
    def __init__(
        self,
        output_dir: str = "downloads",
        max_workers: int = 4,
        timeout: float = 30.0,
        max_retries: int = 3,
        ssl_verify: bool = True
    ):
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.timeout = timeout
        self.max_retries = max_retries
        self.ssl_verify = ssl_verify
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Progress callback
        self.progress_callback: Optional[Callable[[DownloadProgress], None]] = None
        
        # Statistics
        self.stats = DownloadStats()
        self.results: List[DownloadResult] = []
        
        # Thread-safe progress tracking
        self._progress_lock = threading.Lock()
        self._progress = DownloadProgress()
        
        # Create SSL context based on verification setting
        self.ssl_context = ssl.create_default_context()
        if not self.ssl_verify:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
    
    def set_progress_callback(self, callback: Callable[[DownloadProgress], None]):
        """Set a callback function to receive progress updates."""
        self.progress_callback = callback
    
    def _update_progress(
        self,
        completed: Optional[int] = None,
        total: Optional[int] = None,
        current_url: Optional[str] = None,
        current_filename: Optional[str] = None,
        bytes_downloaded: Optional[int] = None,
        total_bytes: Optional[int] = None
    ):
        """Thread-safe progress update."""
        with self._progress_lock:
            if completed is not None:
                self._progress.completed = completed
            if total is not None:
                self._progress.total = total
            if current_url is not None:
                self._progress.current_url = current_url
            if current_filename is not None:
                self._progress.current_filename = current_filename
            if bytes_downloaded is not None:
                self._progress.bytes_downloaded = bytes_downloaded
            if total_bytes is not None:
                self._progress.total_bytes = total_bytes
            
            # Call the callback if set
            if self.progress_callback:
                self.progress_callback(self._progress)
    
    def _get_filename_from_url(self, url: str) -> str:
        """Extract filename from URL or generate one."""
        # Try to get filename from URL
        filename = os.path.basename(url.split('?')[0])
        
        if not filename or filename == '':
            # Generate filename from URL hash
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"download_{url_hash}.bin"
        else:
            # Clean filename
            filename = filename.replace('%20', '_').replace('+', '_')
        
        return filename
    
    def _download_single(
        self,
        url: str,
        output_path: str,
        retry_count: int = 0
    ) -> DownloadResult:
        """Download a single file with retry logic."""
        start_time = time.time()
        result = DownloadResult(
            url=url,
            filename=os.path.basename(output_path),
            success=False,
            retries=retry_count
        )
        
        # Update progress
        self._update_progress(current_url=url, current_filename=result.filename)
        
        # Exponential backoff delay
        if retry_count > 0:
            delay = min(2 ** retry_count, 60)  # Max 60 seconds
            logger.info(f"Retry {retry_count} for {url}, waiting {delay} seconds")
            time.sleep(delay)
        
        try:
            # Create request with timeout
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'ConcurrentDownloader/1.0',
                    'Accept': '*/*'
                }
            )
            
            # Download the file
            with urllib.request.urlopen(
                req,
                timeout=self.timeout,
                context=self.ssl_context
            ) as response:
                # Get content length if available
                content_length = response.getheader('Content-Length')
                file_size = int(content_length) if content_length else 0
                
                # Read the data
                data = response.read()
                actual_size = len(data)
                
                # Verify size if content-length was provided
                if file_size > 0 and actual_size != file_size:
                    raise ValueError(f"Download size mismatch: expected {file_size}, got {actual_size}")
                
                # Write to file
                with open(output_path, 'wb') as f:
                    f.write(data)
                
                # Update result
                result.success = True
                result.size_bytes = actual_size
                result.duration_seconds = time.time() - start_time
                
                logger.info(f"Successfully downloaded {url} to {output_path} "
                          f"({actual_size} bytes in {result.duration_seconds:.2f}s)")
                
                # Update statistics
                with self._progress_lock:
                    self.stats.succeeded += 1
                    self.stats.total_bytes += actual_size
                
        except urllib.error.HTTPError as e:
            error_msg = f"HTTP Error {e.code}: {e.reason}"
            result.error = error_msg
            logger.error(f"HTTP error downloading {url}: {error_msg}")
            
        except urllib.error.URLError as e:
            error_msg = f"URL Error: {e.reason}"
            result.error = error_msg
            logger.error(f"URL error downloading {url}: {error_msg}")
            
        except ssl.SSLError as e:
            error_msg = f"SSL Error: {e.reason}"
            result.error = error_msg
            logger.error(f"SSL error downloading {url}: {error_msg}")
            
        except TimeoutError:
            error_msg = f"Timeout after {self.timeout} seconds"
            result.error = error_msg
            logger.error(f"Timeout downloading {url}")
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            result.error = error_msg
            logger.error(f"Unexpected error downloading {url}: {error_msg}")
        
        if not result.success:
            # Update statistics
            with self._progress_lock:
                self.stats.failed += 1
                if result.error:
                    self.stats.error_details.append(f"{url}: {result.error}")
            
            # Retry logic
            if retry_count < self.max_retries:
                logger.info(f"Retrying {url} (attempt {retry_count + 1}/{self.max_retries})")
                return self._download_single(url, output_path, retry_count + 1)
        
        # Update completion progress
        with self._progress_lock:
            self._progress.completed += 1
        
        self._update_progress(completed=self._progress.completed)
        
        return result
    
    def download(
        self,
        urls: List[str],
        custom_filenames: Optional[Dict[str, str]] = None
    ) -> Dict:
        """
        Download multiple files concurrently.
        
        Args:
            urls: List of URLs to download
            custom_filenames: Optional dict mapping URLs to custom filenames
            
        Returns:
            Dictionary with summary statistics and detailed results
        """
        start_time = time.time()
        
        # Reset statistics
        self.stats = DownloadStats(total_urls=len(urls))
        self.results = []
        self._progress = DownloadProgress(total=len(urls))
        
        logger.info(f"Starting download of {len(urls)} URLs with {self.max_workers} workers")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Timeout: {self.timeout}s, Max retries: {self.max_retries}")
        
        # Initialize progress
        if self.progress_callback:
            self.progress_callback(self._progress)
        
        # Prepare download tasks
        download_tasks = []
        for url in urls:
            # Determine filename
            if custom_filenames and url in custom_filenames:
                filename = custom_filenames[url]
            else:
                filename = self._get_filename_from_url(url)
            
            output_path = os.path.join(self.output_dir, filename)
            
            # Avoid overwriting existing files
            counter = 1
            base_name, ext = os.path.splitext(filename)
            while os.path.exists(output_path):
                filename = f"{base_name}_{counter}{ext}"
                output_path = os.path.join(self.output_dir, filename)
                counter += 1
            
            download_tasks.append((url, output_path))
        
        # Use ThreadPoolExecutor for concurrent downloads
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="downloader"
        ) as executor:
            # Submit all download tasks
            future_to_url = {
                executor.submit(self._download_single, url, path): url
                for url, path in download_tasks
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    self.results.append(result)
                except Exception as e:
                    logger.error(f"Error processing {url}: {e}")
                    self.results.append(DownloadResult(
                        url=url,
                        filename=os.path.basename(url),
                        success=False,
                        error=f"Task execution error: {str(e)}"
                    ))
        
        # Calculate final statistics
        end_time = time.time()
        total_time = end_time - start_time
        
        # Update stats
        self.stats.total_time_seconds = total_time
        
        # Calculate average speed if total time > 0
        if total_time > 0 and self.stats.total_bytes > 0:
            self.stats.average_speed_bps = self.stats.total_bytes / total_time
        
        # Prepare summary
        summary = {
            "total_urls": self.stats.total_urls,
            "succeeded": self.stats.succeeded,
            "failed": self.stats.failed,
            "total_bytes": self.stats.total_bytes,
            "total_time_seconds": round(self.stats.total_time_seconds, 2),
            "average_speed_bps": round(self.stats.average_speed_bps, 2),
            "average_speed_mbps": round(self.stats.average_speed_bps / 1_000_000, 2) if self.stats.average_speed_bps > 0 else 0,
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
            "output_directory": self.output_dir,
            "config": {
                "max_workers": self.max_workers,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
                "ssl_verify": self.ssl_verify
            }
        }
        
        # Add detailed results
        detailed_results = []
        for result in self.results:
            detailed_results.append({
                "url": result.url,
                "filename": result.filename,
                "success": result.success,
                "size_bytes": result.size_bytes,
                "duration_seconds": round(result.duration_seconds, 2),
                "retries": result.retries,
                "error": result.error
            })
        
        summary["detailed_results"] = detailed_results
        
        # Log summary
        logger.info("=" * 60)
        logger.info("DOWNLOAD SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total URLs: {summary['total_urls']}")
        logger.info(f"Succeeded: {summary['succeeded']}")
        logger.info(f"Failed: {summary['failed']}")
        logger.info(f"Total bytes: {summary['total_bytes']:,}")
        logger.info(f"Total time: {summary['total_time_seconds']}s")
        logger.info(f"Average speed: {summary['average_speed_mbps']} Mbps")
        
        if self.stats.error_details:
            logger.info("Errors encountered:")
            for error in self.stats.error_details:
                logger.info(f"  - {error}")
        
        logger.info("=" * 60)
        
        return summary

# Utility functions
def default_progress_callback(progress: DownloadProgress):
    """Default progress callback that prints to console."""
    percent = (progress.completed / progress.total * 100) if progress.total > 0 else 0
    print(f"\rProgress: {progress.completed}/{progress.total} ({percent:.1f}%) | "
          f"Current: {progress.current_filename} | "
          f"Bytes: {progress.bytes_downloaded:,}/{progress.total_bytes:,}", end="")

def download_files(
    urls: List[str],
    output_dir: str = "downloads",
    max_workers: int = 4,
    timeout: float = 30.0,
    max_retries: int = 3,
    progress_callback: Optional[Callable[[DownloadProgress], None]] = None
) -> Dict:
    """
    Convenience function for downloading files.
    
    Args:
        urls: List of URLs to download
        output_dir: Directory to save downloaded files
        max_workers: Maximum number of concurrent downloads
        timeout: Timeout per request in seconds
        max_retries: Maximum number of retry attempts
        progress_callback: Optional callback for progress updates
        
    Returns:
        Dictionary with summary statistics
    """
    downloader = ConcurrentDownloader(
        output_dir=output_dir,
        max_workers=max_workers,
        timeout=timeout,
        max_retries=max_retries
    )
    
    if progress_callback:
        downloader.set_progress_callback(progress_callback)
    else:
        downloader.set_progress_callback(default_progress_callback)
    
    return downloader.download(urls)

# Example usage
if __name__ == "__main__":
    # Example URLs to download
    example_urls = [
        "https://raw.githubusercontent.com/python/cpython/3.12/LICENSE",
        "https://raw.githubusercontent.com/python/cpython/3.12/README.rst",
        "https://raw.githubusercontent.com/python/cpython/3.12/Misc/python.icns",
        "https://httpbin.org/image/jpeg",
        "https://httpbin.org/image/png",
        "https://httpbin.org/image/svg",
        "https://httpbin.org/delay/2",  # This will timeout if timeout < 2s
        "https://nonexistent.example.com/file.txt",  # This will fail
    ]
    
    try:
        print("Starting concurrent downloader example...")
        print("-" * 60)
        
        # Download files
        result = download_files(
            urls=example_urls,
            output_dir="example_downloads",
            max_workers=3,
            timeout=5.0,
            max_retries=2
        )
        
        print("\n")  # New line after progress
        print("-" * 60)
        
        # Print summary
        print(f"Download completed in {result['total_time_seconds']} seconds")
        print(f"Success: {result['succeeded']}/{result['total_urls']}")
        print(f"Total data: {result['total_bytes']:,} bytes")
        
        # Print failed downloads
        failed = [r for r in result['detailed_results'] if not r['success']]
        if failed:
            print("\nFailed downloads:")
            for item in failed:
                print(f"  - {item['url']}: {item['error']}")
        
        # Print successful downloads
        successful = [r for r in result['detailed_results'] if r['success']]
        if successful:
            print(f"\nDownloaded to: {result['output_directory']}")
            for item in successful[:3]:  # Show first 3
                print(f"  - {item['filename']} ({item['size_bytes']:,} bytes)")
            if len(successful) > 3:
                print(f"  ... and {len(successful) - 3} more files")
        
    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nExample completed.")