import urllib.request
import threading
import time
from concurrent.futures import ThreadPoolExecutor

def download(url, output_dir, retries=3):
    for i in range(retries):
        try:
            filename = url.split('/')[-1]
            urllib.request.urlretrieve(url, f"{output_dir}/{filename}")
            return True
        except Exception as e:
            time.sleep(2**i)
    return False

def concurrent_downloader(urls, output_dir, max_workers=4):
    results = {"success": 0, "failed": 0}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download, url, output_dir) for url in urls]
        for f in futures:
            if f.result(): results["success"] += 1
            else: results["failed"] += 1
    return results
