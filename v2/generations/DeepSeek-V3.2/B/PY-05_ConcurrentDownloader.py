import concurrent.futures
import hashlib
import os
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse


class DownloadResult:
    """Result of a single download attempt"""
    
    def __init__(self, url: str, output_path: str):
        self.url = url
        self.output_path = output_path
        self.success = False
        self.error: Optional[str] = None
        self.size_bytes = 0
        self.duration_seconds = 0.0
        self.attempts = 0
        self.checksum: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary"""
        return {
            'url': self.url,
            'output_path': self.output_path,
            'success': self.success,
            'error': self.error,
            'size_bytes': self.size_bytes,
            'duration_seconds': round(self.duration_seconds, 3),
            'attempts': self.attempts,
            'checksum': self.checksum,
        }


class ConcurrentDownloader:
    """Concurrent file downloader with retry and progress tracking"""
    
    def __init__(self, output_dir: str, max_workers: int = 4, timeout: int = 30):
        """
        Initialize downloader.
        
        Args:
            output_dir: Directory to save downloaded files
            max_workers: Maximum number of concurrent downloads
            timeout: Request timeout in seconds
        """
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.timeout = timeout
        self.results: List[DownloadResult] = []
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Configure SSL context for better compatibility
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        self.ssl_context = ssl_context
        
        # Progress callback storage
        self.progress_callback = None
    
    def set_progress_callback(self, callback):
        """Set callback for progress updates"""
        self.progress_callback = callback
    
    def _download_single(self, url: str, output_path: str, retry_count: int = 0) -> DownloadResult:
        """
        Download a single file with retry logic.
        
        Args:
            url: URL to download
            output_path: Local file path to save to
            retry_count: Current retry attempt number
        
        Returns:
            DownloadResult with outcome details
        """
        result = DownloadResult(url, output_path)
        result.attempts = retry_count + 1
        
        start_time = time.time()
        
        try:
            # Create request with headers
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'ConcurrentDownloader/1.0')
            
            # Execute request with timeout
            with urllib.request.urlopen(request, timeout=self.timeout, context=self.ssl_context) as response:
                # Get file size if available
                content_length = response.headers.get('Content-Length')
                if content_length:
                    result.size_bytes = int(content_length)
                
                # Read content in chunks to handle large files
                chunk_size = 8192
                data = bytearray()
                
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    data.extend(chunk)
                
                # Update actual size
                result.size_bytes = len(data)
                
                # Calculate checksum
                result.checksum = hashlib.md5(data).hexdigest()
                
                # Save to file
                with open(output_path, 'wb') as f:
                    f.write(data)
                
                result.success = True
                
                # Call progress callback
                if self.progress_callback:
                    self.progress_callback({
                        'url': url,
                        'status': 'completed',
                        'size': result.size_bytes,
                        'path': output_path,
                    })
        
        except urllib.error.HTTPError as e:
            result.error = f"HTTP Error: {e.code} {e.reason}"
        except urllib.error.URLError as e:
            result.error = f"URL Error: {e.reason}"
        except TimeoutError:
            result.error = f"Timeout after {self.timeout} seconds"
        except Exception as e:
            result.error = f"Unexpected error: {str(e)}"
        
        result.duration_seconds = time.time() - start_time
        
        # Retry logic with exponential backoff
        if not result.success and retry_count < 2:  # Max 3 attempts (0, 1, 2)
            wait_time = (2 ** retry_count) * 2  # Exponential backoff: 2, 4, 8 seconds
            time.sleep(wait_time)
            
            # Call progress callback for retry
            if self.progress_callback:
                self.progress_callback({
                    'url': url,
                    'status': 'retrying',
                    'attempt': retry_count + 1,
                    'wait': wait_time,
                })
            
            return self._download_single(url, output_path, retry_count + 1)
        
        return result
    
    def _get_filename_from_url(self, url: str) -> str:
        """Extract filename from URL"""
        parsed = urlparse(url)
        path = parsed.path
        
        if not path or path == '/':
            # Generate filename from URL hash
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            return f"file_{url_hash}.bin"
        
        # Extract filename from path
        filename = os.path.basename(path)
        
        if not filename:
            # Use last part of path as filename
            path_parts = [p for p in path.split('/') if p]
            if path_parts:
                filename = path_parts[-1] + '.bin'
            else:
                filename = 'download.bin'
        
        return filename
    
    def download(self, urls: List[str]) -> Dict:
        """
        Download multiple files concurrently.
        
        Args:
            urls: List of URLs to download
        
        Returns:
            Summary dictionary with download statistics
        """
        if not urls:
            return {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'total_size_bytes': 0,
                'total_time_seconds': 0,
                'results': [],
            }
        
        start_time = time.time()
        self.results = []
        
        # Prepare download tasks
        tasks = []
        for url in urls:
            # Generate output path
            filename = self._get_filename_from_url(url)
            output_path = os.path.join(self.output_dir, filename)
            tasks.append((url, output_path))
        
        # Execute downloads concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self._download_single, url, output_path): (url, output_path)
                for url, output_path in tasks
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_task):
                url, output_path = future_to_task[future]
                
                try:
                    result = future.result()
                    self.results.append(result)
                    
                    # Call progress callback for completion
                    if self.progress_callback:
                        self.progress_callback({
                            'url': url,
                            'status': 'finished',
                            'success': result.success,
                            'size': result.size_bytes,
                        })
                
                except Exception as e:
                    # Handle unexpected errors in future
                    error_result = DownloadResult(url, output_path)
                    error_result.success = False
                    error_result.error = f"Executor error: {str(e)}"
                    self.results.append(error_result)
        
        end_time = time.time()
        
        # Compile summary
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        total_size = sum(r.size_bytes for r in successful)
        
        summary = {
            'total': len(urls),
            'successful': len(successful),
            'failed': len(failed),
            'total_size_bytes': total_size,
            'total_time_seconds': round(end_time - start_time, 3),
            'average_speed_bps': round(total_size / (end_time - start_time), 2) if successful else 0,
            'start_time': datetime.fromtimestamp(start_time).isoformat(),
            'end_time': datetime.fromtimestamp(end_time).isoformat(),
            'results': [r.to_dict() for r in self.results],
        }
        
        return summary
    
    def get_detailed_results(self) -> List[Dict]:
        """Get detailed results for all downloads"""
        return [r.to_dict() for r in self.results]
    
    def clear_results(self):
        """Clear stored results"""
        self.results = []


def example_progress_callback(info: Dict):
    """Example progress callback function"""
    if info['status'] == 'completed':
        print(f"✓ Downloaded: {info['url']} ({info['size']} bytes)")
    elif info['status'] == 'retrying':
        print(f"↻ Retrying {info['url']} (attempt {info['attempt']}, wait {info['wait']}s)")
    elif info['status'] == 'finished':
        success_msg = "successfully" if info['success'] else "failed"
        print(f"→ Download {success_msg}: {info['url']}")


def main():
    """Example usage of ConcurrentDownloader"""
    import argparse
    import json
    import sys
    
    parser = argparse.ArgumentParser(description='Concurrent file downloader')
    parser.add_argument('urls', nargs='+', help='URLs to download')
    parser.add_argument('--output-dir', '-o', default='./downloads',
                       help='Output directory (default: ./downloads)')
    parser.add_argument('--max-workers', '-w', type=int, default=4,
                       help='Maximum concurrent downloads (default: 4)')
    parser.add_argument('--timeout', '-t', type=int, default=30,
                       help='Request timeout in seconds (default: 30)')
    parser.add_argument('--json', '-j', action='store_true',
                       help='Output results as JSON')
    
    args = parser.parse_args()
    
    # Create downloader instance
    downloader = ConcurrentDownloader(
        output_dir=args.output_dir,
        max_workers=args.max_workers,
        timeout=args.timeout,
    )
    
    # Set progress callback (optional)
    if not args.json:
        downloader.set_progress_callback(example_progress_callback)
    
    print(f"Starting download of {len(args.urls)} files...")
    print(f"Output directory: {args.output_dir}")
    print(f"Max workers: {args.max_workers}")
    print(f"Timeout: {args.timeout}s")
    print("-" * 50)
    
    # Execute downloads
    summary = downloader.download(args.urls)
    
    print("-" * 50)
    
    if args.json:
        # Output as JSON
        print(json.dumps(summary, indent=2))
    else:
        # Output human-readable summary
        print(f"Download Summary:")
        print(f"  Total files: {summary['total']}")
        print(f"  Successful: {summary['successful']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Total size: {summary['total_size_bytes']:,} bytes")
        print(f"  Total time: {summary['total_time_seconds']:.2f}s")
        
        if summary['successful'] > 0:
            avg_speed = summary['total_size_bytes'] / summary['total_time_seconds']
            print(f"  Average speed: {avg_speed:,.2f} B/s ({avg_speed * 8:,.2f} bps)")
        
        # Show failed downloads
        failed_results = [r for r in downloader.results if not r.success]
        if failed_results:
            print(f"\nFailed downloads:")
            for result in failed_results:
                print(f"  {result.url}: {result.error}")


if __name__ == "__main__":
    main()