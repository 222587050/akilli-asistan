import replicate
import requests
import os
from typing import Optional, Dict
import logging
from PIL import Image

logger = logging.getLogger(__name__)

class ImageUpscaler:
    """Replicate API ile görüntü yükseltme (4x Real-ESRGAN)"""
    
    def __init__(self, api_token: str):
        """
        Args:
            api_token: Replicate API token
        """
        self.api_token = api_token
        os.environ["REPLICATE_API_TOKEN"] = api_token
        
    def upscale_image(self, image_path: str) -> Optional[str]:
        """
        Görüntü kalitesini artır (4x upscaling)
        
        Args:
            image_path: Yüklenecek görüntü dosyası yolu
            
        Returns:
            Yükseltilmiş görüntü URL'i veya None
        """
        try:
            logger.info(f"Upscaling başlatılıyor: {image_path}")
            
            # Replicate model: Real-ESRGAN (4x upscaling)
            output = replicate.run(
                "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b",
                input={
                    "image": open(image_path, "rb"),
                    "scale": 4,
                    "face_enhance": False
                }
            )
            
            # Output bir URL string
            if output:
                logger.info(f"Upscale başarılı: {output}")
                return output
            else:
                logger.error("Replicate boş sonuç döndü")
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
            response = requests.get(url, timeout=60)  # Replicate için timeout artırıldı
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
