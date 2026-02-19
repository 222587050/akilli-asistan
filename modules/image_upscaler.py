import requests
import os
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class ImageUpscaler:
    """DeepAI API ile görüntü yükseltme"""
    
    def __init__(self, api_key: str):
        """
        Args:
            api_key: DeepAI API key
        """
        self.api_key = api_key
        self.base_url = "https://api.deepai.org/api"
        
    def upscale_image(self, image_path: str, model: str = "waifu2x") -> Optional[str]:
        """
        Görüntü kalitesini artır
        
        Args:
            image_path: Yüklenecek görüntü dosyası yolu
            model: DeepAI model ("waifu2x" = 2x, "torch-srgan" = 4x)
            
        Returns:
            Yükseltilmiş görüntü URL'i veya None
        """
        try:
            endpoint = f"{self.base_url}/{model}"
            
            with open(image_path, 'rb') as image_file:
                response = requests.post(
                    endpoint,
                    files={'image': image_file},
                    headers={'api-key': self.api_key},
                    timeout=60
                )
            
            if response.status_code == 200:
                result = response.json()
                output_url = result.get('output_url')
                logger.info(f"Upscale başarılı: {output_url}")
                return output_url
            else:
                logger.error(f"DeepAI API hatası: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Upscale hatası: {e}")
            return None
    
    def download_image(self, url: str, output_path: str) -> bool:
        """
        URL'den görüntü indir
        
        Args:
            url: Görüntü URL'i
            output_path: Kaydedilecek dosya yolu
            
        Returns:
            Başarılı ise True
        """
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Görüntü indirildi: {output_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"İndirme hatası: {e}")
            return False
    
    def get_image_info(self, image_path: str) -> Dict:
        """
        Görüntü bilgilerini al (boyut, format, vb.)
        
        Args:
            image_path: Görüntü dosyası yolu
            
        Returns:
            Görüntü bilgileri dict
        """
        try:
            from PIL import Image
            
            with Image.open(image_path) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'size_mb': os.path.getsize(image_path) / (1024 * 1024)
                }
        except Exception as e:
            logger.error(f"Görüntü bilgisi alma hatası: {e}")
            return {}
