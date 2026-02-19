"""
Not Yönetim Sistemi
"""
import logging
from typing import List, Optional

from database import DatabaseManager
from database.models import Note
from utils.helpers import validate_category

logger = logging.getLogger(__name__)


class NotesManager:
    """Not yönetim sınıfı"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Not yöneticisini başlat
        
        Args:
            db_manager: Veritabanı yöneticisi
        """
        self.db_manager = db_manager
        logger.info("NotesManager başlatıldı")
    
    def add_note(self, user_id: int, category: str, content: str) -> Note:
        """
        Not ekle
        
        Args:
            user_id: Kullanıcı ID'si
            category: Not kategorisi
            content: Not içeriği
            
        Returns:
            Oluşturulan not
        """
        try:
            # Kategoriyi validate et
            category = validate_category(category)
            
            # Notu ekle
            note = self.db_manager.add_note(user_id, category, content)
            logger.info(f"Not eklendi: kullanıcı={user_id}, kategori={category}")
            return note
        except Exception as e:
            logger.error(f"Not ekleme hatası: {e}")
            raise
    
    def get_all_notes(self, user_id: int) -> List[Note]:
        """
        Tüm notları getir
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            Not listesi
        """
        try:
            notes = self.db_manager.get_notes(user_id)
            logger.info(f"Notlar getirildi: kullanıcı={user_id}, adet={len(notes)}")
            return notes
        except Exception as e:
            logger.error(f"Not getirme hatası: {e}")
            return []
    
    def get_notes_by_category(self, user_id: int, category: str) -> List[Note]:
        """
        Kategoriye göre notları getir
        
        Args:
            user_id: Kullanıcı ID'si
            category: Kategori adı
            
        Returns:
            Not listesi
        """
        try:
            category = validate_category(category)
            notes = self.db_manager.get_notes(user_id, category)
            logger.info(f"Kategori notları getirildi: kullanıcı={user_id}, kategori={category}, adet={len(notes)}")
            return notes
        except Exception as e:
            logger.error(f"Kategori notu getirme hatası: {e}")
            return []
    
    def search_notes(self, user_id: int, keyword: str) -> List[Note]:
        """
        Notlarda arama yap
        
        Args:
            user_id: Kullanıcı ID'si
            keyword: Arama kelimesi
            
        Returns:
            Bulunan notlar
        """
        try:
            notes = self.db_manager.search_notes(user_id, keyword)
            logger.info(f"Not araması yapıldı: kullanıcı={user_id}, kelime={keyword}, bulunan={len(notes)}")
            return notes
        except Exception as e:
            logger.error(f"Not arama hatası: {e}")
            return []
    
    def delete_note(self, note_id: int, user_id: int) -> bool:
        """
        Not sil
        
        Args:
            note_id: Not ID'si
            user_id: Kullanıcı ID'si
            
        Returns:
            Başarılı ise True
        """
        try:
            success = self.db_manager.delete_note(note_id, user_id)
            if success:
                logger.info(f"Not silindi: id={note_id}, kullanıcı={user_id}")
            else:
                logger.warning(f"Not bulunamadı: id={note_id}, kullanıcı={user_id}")
            return success
        except Exception as e:
            logger.error(f"Not silme hatası: {e}")
            return False
    
    def get_categories(self, user_id: int) -> List[str]:
        """
        Kullanıcının tüm kategorilerini getir
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            Kategori listesi
        """
        try:
            notes = self.db_manager.get_notes(user_id)
            categories = list(set(note.category for note in notes))
            categories.sort()
            logger.info(f"Kategoriler getirildi: kullanıcı={user_id}, adet={len(categories)}")
            return categories
        except Exception as e:
            logger.error(f"Kategori getirme hatası: {e}")
            return []
    
    def get_note_count(self, user_id: int, category: str = None) -> int:
        """
        Not sayısını getir
        
        Args:
            user_id: Kullanıcı ID'si
            category: Kategori (opsiyonel)
            
        Returns:
            Not sayısı
        """
        try:
            if category:
                notes = self.db_manager.get_notes(user_id, category)
            else:
                notes = self.db_manager.get_notes(user_id)
            return len(notes)
        except Exception as e:
            logger.error(f"Not sayısı getirme hatası: {e}")
            return 0
