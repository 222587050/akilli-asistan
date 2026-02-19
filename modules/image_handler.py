import os
import time
from telegram import File
import logging

logger = logging.getLogger(__name__)

class TelegramImageHandler:
    """Telegram görüntü işleme helper"""
    
    def __init__(self, download_dir: str = "temp_images"):
        """
        Args:
            download_dir: Geçici görüntü dizini
        """
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)
    
    async def download_photo(self, photo_file: File, user_id: int) -> str:
        """
        Telegram'dan fotoğraf indir
        
        Args:
            photo_file: Telegram File objesi
            user_id: Kullanıcı ID
            
        Returns:
            İndirilen dosya yolu
        """
        try:
            file_path = os.path.join(
                self.download_dir,
                f"user_{user_id}_{photo_file.file_id}.jpg"
            )
            
            await photo_file.download_to_drive(file_path)
            logger.info(f"Fotoğraf indirildi: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Fotoğraf indirme hatası: {e}")
            raise
    
    def cleanup_file(self, file_path: str):
        """
        Geçici dosyayı sil
        
        Args:
            file_path: Silinecek dosya yolu
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Dosya silindi: {file_path}")
        except Exception as e:
            logger.error(f"Dosya silme hatası: {e}")
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """
        Eski geçici dosyaları temizle
        
        Args:
            max_age_hours: Maksimum dosya yaşı (saat)
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for filename in os.listdir(self.download_dir):
                file_path = os.path.join(self.download_dir, filename)
                
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    
                    if file_age > max_age_seconds:
                        self.cleanup_file(file_path)
                        
        except Exception as e:
            logger.error(f"Eski dosya temizleme hatası: {e}")
