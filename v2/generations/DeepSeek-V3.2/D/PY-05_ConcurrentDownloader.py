import urllib.request
import urllib.error
import urllib.parse
import ssl
import time
import threading
import queue
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Callable, Any
from enum import Enum
import hashlib

# 上下文设置：禁用SSL验证（仅用于演示，生产环境应正确处理）
ssl._create_default_https_context = ssl._create_unverified_context

class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    SUCCESS = "success"
    FAILED = "failed"

@dataclass
class DownloadTask:
    """下载任务"""
    url: str
    output_path: str
    status: DownloadStatus = DownloadStatus.PENDING
    retry_count: int = 0
    file_size: int = 0
    downloaded_bytes: int = 0
    error_message: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

@dataclass
class DownloadResult:
    """下载结果"""
    url: str
    output_path: str
    status: DownloadStatus
    file_size: int
    duration: float
    retry_count: int
    error_message: Optional[str] = None
    file_hash: Optional[str] = None

class ConcurrentDownloader:
    """并发下载器"""
    
    def __init__(
        self, 
        max_workers: int = 4,
        timeout: int = 30,
        max_retries: int = 3,
        output_dir: str = "downloads"
    ):
        """
        初始化下载器
        
        Args:
            max_workers: 最大工作线程数
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            output_dir: 输出目录
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.max_retries = max_retries
        self.output_dir = output_dir
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 进度回调函数
        self.progress_callback: Optional[Callable[[str, int, int], None]] = None
        
        # 统计信息
        self.stats = {
            "total_tasks": 0,
            "successful": 0,
            "failed": 0,
            "total_bytes": 0,
            "total_time": 0.0
        }
        
        # 线程安全的队列和锁
        self.task_queue = queue.Queue()
        self.lock = threading.Lock()
    
    def set_progress_callback(self, callback: Callable[[str, int, int], None]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def _generate_output_path(self, url: str) -> str:
        """根据URL生成输出路径"""
        # 从URL提取文件名
        parsed_url = urllib.parse.urlparse(url)
        path = parsed_url.path
        
        if not path or path == '/':
            # 如果没有路径，使用域名作为文件名
            filename = parsed_url.netloc.replace('.', '_') + '.html'
        else:
            # 使用路径的最后一部分作为文件名
            filename = os.path.basename(path)
            if not filename:
                filename = "index.html"
        
        # 确保文件名唯一
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        name, ext = os.path.splitext(filename)
        if not ext:
            ext = '.bin'
        
        unique_filename = f"{name}_{url_hash}{ext}"
        return os.path.join(self.output_dir, unique_filename)
    
    def _download_with_exponential_backoff(self, task: DownloadTask) -> bool:
        """使用指数退避策略下载文件"""
        task.start_time = time.time()
        task.status = DownloadStatus.DOWNLOADING
        
        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*'
        }
        
        for attempt in range(self.max_retries + 1):
            try:
                # 创建请求对象
                req = urllib.request.Request(task.url, headers=headers)
                
                # 执行请求（带超时）
                response = urllib.request.urlopen(req, timeout=self.timeout)
                
                # 获取文件大小
                file_size = int(response.headers.get('Content-Length', 0))
                task.file_size = file_size
                
                # 创建目标文件
                downloaded = 0
                chunk_size = 8192  # 8KB chunks
                
                with open(task.output_path, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 更新任务状态
                        task.downloaded_bytes = downloaded
                        
                        # 调用进度回调
                        if self.progress_callback:
                            self.progress_callback(task.url, downloaded, file_size)
                
                # 计算文件哈希
                task.file_hash = self._calculate_file_hash(task.output_path)
                
                task.end_time = time.time()
                task.status = DownloadStatus.SUCCESS
                
                with self.lock:
                    self.stats["total_bytes"] += downloaded
                
                return True
                
            except urllib.error.URLError as e:
                task.error_message = f"URL错误: {str(e)}"
            except urllib.error.HTTPError as e:
                task.error_message = f"HTTP错误 {e.code}: {e.reason}"
            except TimeoutError:
                task.error_message = "请求超时"
            except Exception as e:
                task.error_message = f"未知错误: {str(e)}"
            
            # 记录重试次数
            task.retry_count = attempt + 1
            
            # 如果不是最后一次尝试，执行指数退避
            if attempt < self.max_retries:
                backoff_time = 2 ** attempt  # 指数退避：1, 2, 4, 8秒...
                time.sleep(backoff_time)
        
        task.end_time = time.time()
        task.status = DownloadStatus.FAILED
        return False
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件的MD5哈希"""
        hash_md5 = hashlib.md5()
        
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
        except Exception:
            return "hash_calculation_failed"
        
        return hash_md5.hexdigest()
    
    def _download_worker(self, task: DownloadTask) -> DownloadResult:
        """下载工作线程"""
        result = self._download_with_exponential_backoff(task)
        
        duration = (task.end_time or time.time()) - (task.start_time or time.time())
        
        return DownloadResult(
            url=task.url,
            output_path=task.output_path,
            status=task.status,
            file_size=task.file_size,
            duration=duration,
            retry_count=task.retry_count,
            error_message=task.error_message,
            file_hash=task.file_hash
        )
    
    def download_urls(
        self, 
        urls: List[str],
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        并发下载多个URL
        
        Args:
            urls: URL列表
            progress_callback: 进度回调函数
        
        Returns:
            Dict: 下载汇总结果
        """
        if progress_callback:
            self.set_progress_callback(progress_callback)
        
        # 准备下载任务
        tasks = []
        for url in urls:
            output_path = self._generate_output_path(url)
            tasks.append(DownloadTask(url=url, output_path=output_path))
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(self._download_worker, task): task
                for task in tasks
            }
            
            results = []
            failed_urls = []
            
            # 处理完成的任务
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                
                try:
                    result = future.result(timeout=self.timeout + 5)
                    results.append(result)
                    
                    with self.lock:
                        if result.status == DownloadStatus.SUCCESS:
                            self.stats["successful"] += 1
                        else:
                            self.stats["failed"] += 1
                            failed_urls.append({
                                "url": result.url,
                                "error": result.error_message,
                                "retries": result.retry_count
                            })
                    
                    # 实时进度输出
                    if self.progress_callback:
                        print(f"完成: {task.url} ({result.status.value})")
                    
                except Exception as e:
                    failed_result = DownloadResult(
                        url=task.url,
                        output_path=task.output_path,
                        status=DownloadStatus.FAILED,
                        file_size=0,
                        duration=0.0,
                        retry_count=task.retry_count,
                        error_message=f"任务执行异常: {str(e)}"
                    )
                    results.append(failed_result)
                    
                    with self.lock:
                        self.stats["failed"] += 1
                        failed_urls.append({
                            "url": task.url,
                            "error": str(e),
                            "retries": task.retry_count
                        })
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # 更新统计信息
        self.stats["total_tasks"] = len(urls)
        self.stats["total_time"] = total_duration
        
        # 构建结果汇总
        summary = {
            "total_tasks": len(urls),
            "successful": self.stats["successful"],
            "failed": self.stats["failed"],
            "total_bytes": self.stats["total_bytes"],
            "total_duration_seconds": total_duration,
            "average_download_speed_kbps": (
                self.stats["total_bytes"] / total_duration / 1024
                if total_duration > 0 else 0
            ),
            "failed_urls": failed_urls,
            "download_results": [asdict(r) for r in results],
            "output_directory": os.path.abspath(self.output_dir),
            "completion_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time))
        }
        
        return summary
    
    def download_urls_with_callback(
        self, 
        urls: List[str],
        callback: Optional[Callable[[str, Dict], None]] = None
    ) -> Dict[str, Any]:
        """
        带回调的下载方法（便于集成）
        
        Args:
            urls: URL列表
            callback: 完成回调函数
        
        Returns:
            Dict: 下载结果
        """
        summary = self.download_urls(urls)
        
        if callback:
            callback("download_complete", summary)
        
        return summary

# 示例用法和命令行接口
def main():
    """主函数：命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="并发下载器 - 使用标准库实现多线程下载"
    )
    parser.add_argument(
        "urls", 
        nargs="*",
        help="要下载的URL列表（也可通过文件提供）"
    )
    parser.add_argument(
        "-f", "--file",
        help="包含URL列表的文件（每行一个URL）"
    )
    parser.add_argument(
        "-o", "--output",
        default="downloads",
        help="输出目录（默认：downloads）"
    )
    parser.add_argument(
        "-t", "--threads",
        type=int,
        default=4,
        help="并发线程数（默认：4）"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="超时时间（秒，默认：30）"
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="最大重试次数（默认：3）"
    )
    parser.add_argument(
        "-j", "--json",
        action="store_true",
        help="输出JSON格式结果"
    )
    
    args = parser.parse_args()
    
    # 收集URL
    urls = list(args.urls)
    
    if args.file:
        try:
            with open(args.file, 'r') as f:
                urls.extend([line.strip() for line in f if line.strip()])
        except FileNotFoundError:
            print(f"错误：文件不存在 {args.file}")
            return 1
    
    if not urls:
        print("错误：没有提供URL")
        parser.print_help()
        return 1
    
    print(f"开始下载 {len(urls)} 个URL...")
    print(f"输出目录: {args.output}")
    print(f"并发线程: {args.threads}")
    print(f"超时时间: {args.timeout}秒")
    print(f"最大重试: {args.retries}")
    print("-" * 50)
    
    # 创建下载器实例
    downloader = ConcurrentDownloader(
        max_workers=args.threads,
        timeout=args.timeout,
        max_retries=args.retries,
        output_dir=args.output
    )
    
    # 进度回调函数
    def progress_callback(url: str, downloaded: int, total: int):
        """进度回调"""
        if total > 0:
            percent = (downloaded / total) * 100
            sys.stdout.write(f"\r下载进度: {url[:50]}... {percent:.1f}% ({downloaded}/{total} bytes)")
            sys.stdout.flush()
    
    downloader.set_progress_callback(progress_callback)
    
    # 执行下载
    try:
        summary = downloader.download_urls(urls)
        
        print("\n" + "=" * 50)
        print("下载完成！")
        print("=" * 50)
        
        if args.json:
            # 输出JSON格式结果
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            # 输出易读格式结果
            print(f"总任务数: {summary['total_tasks']}")
            print(f"成功: {summary['successful']}")
            print(f"失败: {summary['failed']}")
            print(f"总下载大小: {summary['total_bytes']:,} 字节")
            print(f"总耗时: {summary['total_duration_seconds']:.2f} 秒")
            print(f"平均速度: {summary['average_download_speed_kbps']:.2f} KB/s")
            print(f"输出目录: {summary['output_directory']}")
            
            if summary['failed_urls']:
                print("\n失败的URL:")
                for failed in summary['failed_urls']:
                    print(f"  - {failed['url']}")
                    print(f"    错误: {failed['error']}")
                    print(f"    重试: {failed['retries']}次")
            
            print(f"\n完成时间: {summary['completion_time']}")
        
        return 0 if summary['failed'] == 0 else 1
        
    except KeyboardInterrupt:
        print("\n\n用户中断下载")
        return 130
    except Exception as e:
        print(f"\n下载过程发生错误: {str(e)}")
        return 1

# 进度回调示例
def example_progress_callback(url: str, downloaded: int, total: int):
    """进度回调示例"""
    if total > 0:
        percent = (downloaded / total) * 100
        print(f"进度: {url[:30]}... {percent:.1f}%")

# 使用示例
if __name__ == "__main__":
    # 示例URL列表
    sample_urls = [
        "https://httpbin.org/image/jpeg",  # JPEG图片
        "https://httpbin.org/html",         # HTML页面
        "https://httpbin.org/json",         # JSON数据
        "https://httpbin.org/robots.txt",   # 文本文件
    ]
    
    # 示例1：基本用法
    if len(sys.argv) == 1:
        print("测试模式：使用示例URL列表")
        print("如果要使用命令行，请提供URL参数")
        print("例如: python PY_05_ConcurrentDownloader.py https://example.com/file1.zip https://example.com/file2.zip")
        print("-" * 50)
        
        downloader = ConcurrentDownloader(
            max_workers=2,
            timeout=15,
            max_retries=2
        )
        
        summary = downloader.download_urls(sample_urls)
        
        print("\n下载汇总:")
        print(f"成功: {summary['successful']}")
        print(f"失败: {summary['failed']}")
        print(f"总大小: {summary['total_bytes']:,} 字节")
        print(f"耗时: {summary['total_duration_seconds']:.2f} 秒")
        
        sys.exit(0)
    else:
        # 命令行模式
        sys.exit(main())