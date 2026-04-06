import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
import time

def download(url, output_dir):
    try:
        retries = 0
        while retries < 3:
            try:
                with urllib.request.urlopen(url, timeout=30) as response:
                    content = response.read()
                    with open(f"{output_dir}/{url.split('/')[-1]}", 'wb') as f:
                        f.write(content)
                    return True
            except (urllib.error.URLError, TimeoutError):
                retries += 1
                time.sleep(2 ** retries)
        return False
    except:
        return False

def run_downloader(urls, output_dir):
    results = {"success": 0, "failed": 0, "errors": []}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(download, url, output_dir): url for url in urls}
        for future in futures:
            if future.result():
                results["success"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(futures[future])
    return results
