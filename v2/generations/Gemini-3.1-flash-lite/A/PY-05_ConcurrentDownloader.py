import threading
from concurrent.futures import ThreadPoolExecutor
import urllib.request
import time
import os

class ConcurrentDownloader:
    def __init__(self, max_workers=4, timeout=30):
        self.max_workers = max_workers
        self.timeout = timeout

    def download(self, urls, output_dir, callback=None):
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        summary = {"succeeded": 0, "failed": 0, "errors": {}}
        
        def _download(url):
            for i in range(3):
                try:
                    with urllib.request.urlopen(url, timeout=self.timeout) as response:
                        filename = os.path.join(output_dir, os.path.basename(url))
                        with open(filename, 'wb') as f: f.write(response.read())
                    return True, url
                except Exception as e:
                    if i == 2: return False, (url, str(e))
                    time.sleep(2 ** i)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(_download, urls))
            for success, val in results:
                if success:
                    summary["succeeded"] += 1
                    if callback: callback(val)
                else:
                    summary["failed"] += 1
                    summary["errors"][val[0]] = val[1]
        return summary
