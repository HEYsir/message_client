import os
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

class ImageHandler:
    """图片处理器"""
    def __init__(self, download_dir: str = "./downloads"):
        self.download_dir = download_dir
        self.executor = ThreadPoolExecutor(max_workers=5)
        os.makedirs(download_dir, exist_ok=True)
        
    def download_image(self, url: str, filename: str) -> Optional[str]:
        """下载图片"""
        try:
            filepath = os.path.join(self.download_dir, filename)
            
            response = requests.get(
                url, 
                stream=True, 
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            response.raise_for_status()
            
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
            
            return filepath
        except Exception as e:
            print(f"Failed to download image: {url} - {str(e)}")
            return None
    
    def async_download(self, url: str, filename: str) -> None:
        """异步下载图片"""
        try:
            self.executor.submit(self.download_image, url, filename)
        except Exception as e:
            print(f"Error in async_download: {e}")