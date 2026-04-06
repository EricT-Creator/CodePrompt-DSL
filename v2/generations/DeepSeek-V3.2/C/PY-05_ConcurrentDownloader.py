#!/usr/bin/env python3
"""
并发下载器 - 使用标准库实现
支持多线程并发下载、重试机制和进度回调
"""

import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
import ssl
import hashlib
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Union, Any
from pathlib import Path
from urllib.parse import urlparse
import mimetypes
import json


# 数据类
@dataclass
class DownloadTask:
    """下载任务"""
    url: str
    output_path: str
    retry_count: int = 0
    max_retries: int = 3
    timeout: float = 30.0
    chunk_size: int = 8192  # 8KB chunks
    headers: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        # 确保输出目录存在
        output_dir = os.path.dirname(self.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 设置默认User-Agent
        if 'User-Agent' not in self.headers:
            self.headers['User-Agent'] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )


@dataclass
class DownloadResult:
    """下载结果"""
    url: str
    output_path: str
    success: bool
    file_size: int = 0
    download_time: float = 0.0
    error_message: Optional[str] = None
    retry_count: int = 0
    content_type: Optional[str] = None
    status_code: Optional[int] = None
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "url": self.url,
            "output_path": self.output_path,
            "success": self.success,
            "file_size": self.file_size,
            "download_time": round(self.download_time, 2),
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "content_type": self.content_type,
            "status_code": self.status_code,
            "checksum_md5": self.checksum_md5,
            "checksum_sha256": self.checksum_sha256
        }


@dataclass
class DownloadProgress:
    """下载进度"""
    url: str
    bytes_downloaded: int
    total_bytes: Optional[int] = None
    percentage: float = 0.0
    speed_bytes_per_sec: float = 0.0
    elapsed_time: float = 0.0
    estimated_time_remaining: Optional[float] = None
    status: str = "downloading"  # "downloading", "completed", "failed", "retrying"


@dataclass
class DownloadSummary:
    """下载摘要"""
    total_tasks: int = 0
    succeeded: int = 0
    failed: int = 0
    total_bytes: int = 0
    total_time: float = 0.0
    average_speed: float = 0.0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_tasks": self.total_tasks,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "total_bytes": self.total_bytes,
            "total_time": round(self.total_time, 2),
            "average_speed": round(self.average_speed, 2),
            "success_rate": round(self.succeeded / self.total_tasks * 100, 2) if self.total_tasks > 0 else 0.0,
            "errors": self.errors
        }


# 进度回调管理器
class ProgressManager:
    """进度管理器"""
    
    def __init__(self, callback: Optional[Callable[[DownloadProgress], None]] = None):
        self.callback = callback
        self._lock = threading.Lock()
        self._progress_data: Dict[str, DownloadProgress] = {}
    
    def update_progress(self, progress: DownloadProgress) -> None:
        """更新进度"""
        with self._lock:
            self._progress_data[progress.url] = progress
        
        if self.callback:
            try:
                self.callback(progress)
            except Exception:
                pass  # 忽略回调错误
    
    def get_progress(self, url: str) -> Optional[DownloadProgress]:
        """获取指定URL的进度"""
        with self._lock:
            return self._progress_data.get(url)
    
    def get_all_progress(self) -> List[DownloadProgress]:
        """获取所有进度"""
        with self._lock:
            return list(self._progress_data.values())
    
    def clear(self) -> None:
        """清除进度数据"""
        with self._lock:
            self._progress_data.clear()


# 下载器类
class ConcurrentDownloader:
    """并发下载器"""
    
    def __init__(
        self,
        max_workers: int = 4,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay_base: float = 1.0,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ):
        """
        初始化下载器
        
        Args:
            max_workers: 最大工作线程数
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            retry_delay_base: 重试延迟基数（秒）
            progress_callback: 进度回调函数
        """
        self.max_workers = max_workers
        self.default_timeout = timeout
        self.max_retries = max_retries
        self.retry_delay_base = retry_delay_base
        
        self.progress_manager = ProgressManager(progress_callback)
        self._summary = DownloadSummary()
        self._lock = threading.Lock()
        
        # 创建SSL上下文（允许不验证证书，用于下载HTTPS）
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
    
    def _calculate_retry_delay(self, retry_count: int) -> float:
        """计算指数退避延迟"""
        return self.retry_delay_base * (2 ** retry_count)
    
    def _get_file_size_from_url(self, url: str, headers: Dict[str, str]) -> Optional[int]:
        """通过HEAD请求获取文件大小"""
        try:
            req = urllib.request.Request(url, method='HEAD', headers=headers)
            
            with urllib.request.urlopen(req, timeout=5, context=self.ssl_context) as response:
                content_length = response.headers.get('Content-Length')
                if content_length:
                    return int(content_length)
        except Exception:
            pass
        
        return None
    
    def _calculate_checksums(self, file_path: str) -> Dict[str, str]:
        """计算文件校验和"""
        try:
            md5_hash = hashlib.md5()
            sha256_hash = hashlib.sha256()
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    md5_hash.update(chunk)
                    sha256_hash.update(chunk)
            
            return {
                'md5': md5_hash.hexdigest(),
                'sha256': sha256_hash.hexdigest()
            }
        except Exception:
            return {}
    
    def _download_single(self, task: DownloadTask) -> DownloadResult:
        """下载单个文件"""
        start_time = time.time()
        retry_count = 0
        last_error = None
        
        # 更新进度：开始下载
        progress = DownloadProgress(
            url=task.url,
            bytes_downloaded=0,
            total_bytes=None,
            status="downloading"
        )
        self.progress_manager.update_progress(progress)
        
        # 尝试获取文件大小
        try:
            file_size = self._get_file_size_from_url(task.url, task.headers)
            if file_size:
                progress.total_bytes = file_size
                self.progress_manager.update_progress(progress)
        except Exception:
            pass
        
        while retry_count <= task.max_retries:
            try:
                # 重试时等待
                if retry_count > 0:
                    delay = self._calculate_retry_delay(retry_count - 1)
                    time.sleep(delay)
                    
                    # 更新进度：重试中
                    progress.status = "retrying"
                    self.progress_manager.update_progress(progress)
                
                # 创建请求
                req = urllib.request.Request(task.url, headers=task.headers)
                
                # 打开URL连接
                with urllib.request.urlopen(
                    req,
                    timeout=task.timeout,
                    context=self.ssl_context
                ) as response:
                    status_code = response.getcode()
                    content_type = response.headers.get('Content-Type')
                    
                    # 如果之前没有获取到文件大小，尝试从响应获取
                    if progress.total_bytes is None:
                        content_length = response.headers.get('Content-Length')
                        if content_length:
                            progress.total_bytes = int(content_length)
                            self.progress_manager.update_progress(progress)
                    
                    # 下载文件
                    bytes_downloaded = 0
                    last_update_time = start_time
                    
                    with open(task.output_path, 'wb') as f:
                        while True:
                            chunk = response.read(task.chunk_size)
                            if not chunk:
                                break
                            
                            f.write(chunk)
                            bytes_downloaded += len(chunk)
                            
                            # 更新进度（限制更新频率）
                            current_time = time.time()
                            if current_time - last_update_time >= 0.1:  # 每100ms更新一次
                                progress.bytes_downloaded = bytes_downloaded
                                progress.elapsed_time = current_time - start_time
                                
                                # 计算下载速度
                                if progress.elapsed_time > 0:
                                    progress.speed_bytes_per_sec = bytes_downloaded / progress.elapsed_time
                                
                                # 计算进度百分比
                                if progress.total_bytes:
                                    progress.percentage = (bytes_downloaded / progress.total_bytes) * 100
                                    
                                    # 计算剩余时间
                                    if progress.speed_bytes_per_sec > 0:
                                        remaining_bytes = progress.total_bytes - bytes_downloaded
                                        progress.estimated_time_remaining = remaining_bytes / progress.speed_bytes_per_sec
                                
                                self.progress_manager.update_progress(progress)
                                last_update_time = current_time
                    
                    # 下载完成
                    download_time = time.time() - start_time
                    
                    # 计算校验和
                    checksums = self._calculate_checksums(task.output_path)
                    
                    # 获取实际文件大小
                    actual_file_size = os.path.getsize(task.output_path)
                    
                    # 更新最终进度
                    progress.bytes_downloaded = actual_file_size
                    progress.percentage = 100.0
                    progress.elapsed_time = download_time
                    progress.status = "completed"
                    self.progress_manager.update_progress(progress)
                    
                    # 返回成功结果
                    return DownloadResult(
                        url=task.url,
                        output_path=task.output_path,
                        success=True,
                        file_size=actual_file_size,
                        download_time=download_time,
                        retry_count=retry_count,
                        content_type=content_type,
                        status_code=status_code,
                        checksum_md5=checksums.get('md5'),
                        checksum_sha256=checksums.get('sha256')
                    )
                    
            except urllib.error.HTTPError as e:
                last_error = f"HTTP错误 {e.code}: {e.reason}"
                retry_count += 1
            except urllib.error.URLError as e:
                last_error = f"URL错误: {e.reason}"
                retry_count += 1
            except TimeoutError:
                last_error = "连接超时"
                retry_count += 1
            except Exception as e:
                last_error = f"下载错误: {str(e)}"
                retry_count += 1
        
        # 下载失败
        download_time = time.time() - start_time
        
        # 清理可能部分下载的文件
        if os.path.exists(task.output_path):
            try:
                os.remove(task.output_path)
            except Exception:
                pass
        
        # 更新进度：失败
        progress.status = "failed"
        progress.error_message = last_error
        self.progress_manager.update_progress(progress)
        
        return DownloadResult(
            url=task.url,
            output_path=task.output_path,
            success=False,
            download_time=download_time,
            error_message=last_error,
            retry_count=retry_count
        )
    
    def download(
        self,
        urls: List[str],
        output_dir: str,
        custom_headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None
    ) -> DownloadSummary:
        """
        并发下载多个文件
        
        Args:
            urls: URL列表
            output_dir: 输出目录
            custom_headers: 自定义HTTP头部
            timeout: 超时时间（覆盖默认值）
            max_retries: 最大重试次数（覆盖默认值）
            
        Returns:
            DownloadSummary: 下载摘要
        """
        start_time = time.time()
        
        # 准备任务
        tasks = []
        for i, url in enumerate(urls):
            # 解析URL获取文件名
            parsed_url = urlparse(url)
            url_path = parsed_url.path
            
            if not url_path or url_path == '/':
                filename = f"file_{i+1}.bin"
            else:
                filename = os.path.basename(url_path)
                if not filename:
                    filename = f"file_{i+1}.bin"
            
            # 清理文件名
            filename = self._sanitize_filename(filename)
            
            # 创建输出路径
            output_path = os.path.join(output_dir, filename)
            
            # 处理重复文件名
            counter = 1
            while os.path.exists(output_path):
                name, ext = os.path.splitext(filename)
                output_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
                counter += 1
            
            # 创建任务
            task = DownloadTask(
                url=url,
                output_path=output_path,
                timeout=timeout or self.default_timeout,
                max_retries=max_retries or self.max_retries
            )
            
            # 添加自定义头部
            if custom_headers:
                task.headers.update(custom_headers)
            
            tasks.append(task)
        
        # 重置摘要
        self._summary = DownloadSummary(total_tasks=len(tasks))
        
        # 使用线程池执行下载
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(self._download_single, task): task
                for task in tasks
            }
            
            # 处理结果
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                
                try:
                    result = future.result()
                    
                    with self._lock:
                        if result.success:
                            self._summary.succeeded += 1
                            self._summary.total_bytes += result.file_size
                        else:
                            self._summary.failed += 1
                            self._summary.errors.append(result.to_dict())
                        
                        # 更新摘要统计
                        self._summary.total_time = time.time() - start_time
                        if self._summary.total_time > 0:
                            self._summary.average_speed = (
                                self._summary.total_bytes / self._summary.total_time
                            )
                
                except Exception as e:
                    with self._lock:
                        self._summary.failed += 1
                        self._summary.errors.append({
                            "url": task.url,
                            "error": f"任务执行异常: {str(e)}"
                        })
        
        return self._summary
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除非法字符"""
        # 移除或替换非法字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # 限制文件名长度
        max_length = 255
        name, ext = os.path.splitext(filename)
        if len(name) > max_length - len(ext):
            name = name[:max_length - len(ext)]
        
        return name + ext
    
    def get_summary(self) -> DownloadSummary:
        """获取下载摘要"""
        return self._summary
    
    def save_summary_json(self, file_path: str) -> None:
        """保存摘要到JSON文件"""
        summary_dict = self._summary.to_dict()
        
        # 添加详细结果
        if hasattr(self, '_detailed_results'):
            summary_dict['detailed_results'] = [
                r.to_dict() for r in self._detailed_results
            ]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(summary_dict, f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def create_default_progress_callback() -> Callable[[DownloadProgress], None]:
        """创建默认进度回调函数"""
        def callback(progress: DownloadProgress):
            if progress.total_bytes:
                size_mb = progress.total_bytes / (1024 * 1024)
                downloaded_mb = progress.bytes_downloaded / (1024 * 1024)
                speed_mbps = progress.speed_bytes_per_sec / (1024 * 1024)
                
                if progress.status == "downloading":
                    print(f"\r{progress.url[:50]:<50} | "
                          f"{downloaded_mb:.1f}/{size_mb:.1f} MB "
                          f"({progress.percentage:.1f}%) | "
                          f"{speed_mbps:.1f} MB/s", end='')
                elif progress.status == "completed":
                    print(f"\r{progress.url[:50]:<50} | "
                          f"完成 ({size_mb:.1f} MB, {progress.elapsed_time:.1f}s)")
                elif progress.status == "failed":
                    print(f"\r{progress.url[:50]:<50} | "
                          f"失败: {progress.error_message}")
            else:
                if progress.status == "downloading":
                    print(f"\r{progress.url[:50]:<50} | "
                          f"{progress.bytes_downloaded:,} 字节 | "
                          f"{progress.speed_bytes_per_sec/1024:.1f} KB/s", end='')
        
        return callback


# 命令行接口
def main():
    """命令行入口点"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="并发下载器 - 使用标准库实现的多线程文件下载工具"
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="包含URL列表的文件路径（每行一个URL）或直接使用逗号分隔的URL"
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="输出目录路径"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=4,
        help="并发工作线程数（默认：4）"
    )
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=30.0,
        help="超时时间（秒）（默认：30）"
    )
    parser.add_argument(
        "-r", "--retries",
        type=int,
        default=3,
        help="最大重试次数（默认：3）"
    )
    parser.add_argument(
        "--show-progress",
        action="store_true",
        help="显示下载进度"
    )
    parser.add_argument(
        "--save-summary",
        help="保存下载摘要到JSON文件"
    )
    
    args = parser.parse_args()
    
    # 准备URL列表
    urls = []
    
    if os.path.exists(args.input):
        # 从文件读取URL
        with open(args.input, 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                if url and not url.startswith('#'):
                    urls.append(url)
    else:
        # 从参数解析URL（逗号分隔）
        urls = [url.strip() for url in args.input.split(',') if url.strip()]
    
    if not urls:
        print("错误：没有找到有效的URL")
        sys.exit(1)
    
    # 确保输出目录存在
    os.makedirs(args.output, exist_ok=True)
    
    print(f"开始下载 {len(urls)} 个文件到目录: {args.output}")
    print(f"配置: {args.workers} 个工作线程, {args.timeout}秒超时, {args.retries}次重试")
    print("-" * 80)
    
    # 创建下载器
    progress_callback = None
    if args.show_progress:
        progress_callback = ConcurrentDownloader.create_default_progress_callback()
    
    downloader = ConcurrentDownloader(
        max_workers=args.workers,
        timeout=args.timeout,
        max_retries=args.retries,
        progress_callback=progress_callback
    )
    
    # 开始下载
    try:
        summary = downloader.download(
            urls=urls,
            output_dir=args.output,
            timeout=args.timeout,
            max_retries=args.retries
        )
        
        # 打印结果
        print("\n" + "=" * 80)
        print("下载完成！")
        print(f"总计: {summary.total_tasks} 个文件")
        print(f"成功: {summary.succeeded} 个文件")
        print(f"失败: {summary.failed} 个文件")
        print(f"成功率: {summary.succeeded / summary.total_tasks * 100:.1f}%")
        print(f"总大小: {summary.total_bytes / (1024*1024):.2f} MB")
        print(f"总时间: {summary.total_time:.2f} 秒")
        print(f"平均速度: {summary.average_speed / (1024*1024):.2f} MB/s")
        
        if summary.failed > 0:
            print("\n失败的文件:")
            for error in summary.errors[:5]:  # 只显示前5个错误
                print(f"  - {error.get('url', '未知URL')}: {error.get('error_message', '未知错误')}")
            if len(summary.errors) > 5:
                print(f"  ... 还有 {len(summary.errors) - 5} 个错误")
        
        # 保存摘要
        if args.save_summary:
            downloader.save_summary_json(args.save_summary)
            print(f"\n摘要已保存到: {args.save_summary}")
        
    except KeyboardInterrupt:
        print("\n\n下载被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n下载过程中发生错误: {str(e)}")
        sys.exit(1)


# 使用示例
if __name__ == "__main__":
    # 如果直接运行，使用命令行接口
    main()
    
    # 编程使用示例：
    """
    # 示例1：基本使用
    urls = [
        "https://example.com/file1.zip",
        "https://example.com/file2.pdf",
        "https://example.com/file3.jpg"
    ]
    
    downloader = ConcurrentDownloader(max_workers=4)
    summary = downloader.download(urls, "./downloads")
    
    # 示例2：带进度回调
    def my_progress_callback(progress):
        print(f"{progress.url}: {progress.percentage:.1f}%")
    
    downloader = ConcurrentDownloader(
        max_workers=4,
        progress_callback=my_progress_callback
    )
    
    # 示例3：自定义参数
    custom_headers = {
        "User-Agent": "MyCustomDownloader/1.0",
        "Authorization": "Bearer token123"
    }
    
    summary = downloader.download(
        urls=urls,
        output_dir="./downloads",
        custom_headers=custom_headers,
        timeout=60,
        max_retries=5
    )
    
    # 保存摘要
    downloader.save_summary_json("download_summary.json")
    """