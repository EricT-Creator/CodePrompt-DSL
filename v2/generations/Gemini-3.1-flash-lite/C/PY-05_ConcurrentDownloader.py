import urllib.request
from concurrent.futures import ThreadPoolExecutor
import time
import os

def download(url, folder):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            filename = os.path.join(folder, os.path.basename(url))
            with open(filename, 'wb') as f:
                f.write(response.read())
            return True, None
    except Exception as e:
        return False, str(e)

def run_downloader(urls, folder):
    if not os.path.exists(folder): os.makedirs(folder)
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(download, url, folder): url for url in urls}
        results = {"succeeded": 0, "failed": 0, "errors": {}}
        
        for future in futures:
            success, error = future.result()
            if success:
                results["succeeded"] += 1
            else:
                results["failed"] += 1
                results["errors"][futures[future]] = error
    return results

if __name__ == "__main__":
    urls = ["https://example.com/file1.txt", "https://example.com/file2.txt"]
    print(run_downloader(urls, "./downloads"))
