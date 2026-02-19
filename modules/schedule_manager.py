"""
Ajanda ve Görev Yönetim Sistemi
"""
import logging
from datetime import datetime
from typing import List, Optional

from database import DatabaseManager
from database.models import Task, PriorityLevel
from utils.helpers import parse_date

logger = logging.getLogger(__name__)


class ScheduleManager:
    """Ajanda ve görev yönetim sınıfı"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Ajanda yöneticisini başlat
        
        Args:
            db_manager: Veritabanı yöneticisi
        """
        self.db_manager = db_manager
        logger.info("ScheduleManager başlatıldı")
    
    def add_task(self, user_id: int, title: str, description: str = None,
                priority: str = "orta", due_date_str: str = None) -> Task:
        """
        Görev ekle
        
        Args:
            user_id: Kullanıcı ID'si
            title: Görev başlığı
            description: Görev açıklaması
            priority: Öncelik (düşük, orta, yüksek)
            due_date_str: Bitiş tarihi (string)
            
        Returns:
            Oluşturulan görev
        """
        try:
            # Öncelik seviyesini belirle
            priority_map = {
                'düşük': PriorityLevel.LOW,
                'dusuk': PriorityLevel.LOW,
                'low': PriorityLevel.LOW,
                'orta': PriorityLevel.MEDIUM,
                'medium': PriorityLevel.MEDIUM,
                'yüksek': PriorityLevel.HIGH,
                'yuksek': PriorityLevel.HIGH,
                'high': PriorityLevel.HIGH
            }
            
            priority_level = priority_map.get(priority.lower(), PriorityLevel.MEDIUM)
            
            # Tarihi parse et
            due_date = None
            if due_date_str:
                due_date = parse_date(due_date_str)
            
            # Görevi ekle
            task = self.db_manager.add_task(
                user_id=user_id,
                title=title,
                description=description,
                priority=priority_level,
                due_date=due_date
            )
            
            logger.info(f"Görev eklendi: kullanıcı={user_id}, başlık={title}")
            return task
        except Exception as e:
            logger.error(f"Görev ekleme hatası: {e}")
            raise
    
    def get_all_tasks(self, user_id: int, include_completed: bool = False) -> List[Task]:
        """
        Tüm görevleri getir
        
        Args:
            user_id: Kullanıcı ID'si
            include_completed: Tamamlanmış görevleri dahil et
            
        Returns:
            Görev listesi
        """
        try:
            tasks = self.db_manager.get_tasks(user_id, include_completed)
            logger.info(f"Görevler getirildi: kullanıcı={user_id}, adet={len(tasks)}")
            return tasks
        except Exception as e:
            logger.error(f"Görev getirme hatası: {e}")
            return []
    
    def get_today_tasks(self, user_id: int) -> List[Task]:
        """
        Bugünkü görevleri getir
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            Bugünkü görevler
        """
        try:
            tasks = self.db_manager.get_today_tasks(user_id)
            logger.info(f"Bugünkü görevler getirildi: kullanıcı={user_id}, adet={len(tasks)}")
            return tasks
        except Exception as e:
            logger.error(f"Bugünkü görev getirme hatası: {e}")
            return []
    
    def get_upcoming_tasks(self, user_id: int, days: int = 7) -> List[Task]:
        """
        Yaklaşan görevleri getir
        
        Args:
            user_id: Kullanıcı ID'si
            days: Kaç gün sonrasına kadar
            
        Returns:
            Yaklaşan görevler
        """
        try:
            from datetime import timedelta
            now = datetime.now()
            end_date = now + timedelta(days=days)
            
            all_tasks = self.db_manager.get_tasks(user_id, include_completed=False)
            
            # Tarihe göre filtrele
            upcoming_tasks = [
                task for task in all_tasks
                if task.due_date and now <= task.due_date <= end_date
            ]
            
            # Tarihe göre sırala
            upcoming_tasks.sort(key=lambda x: x.due_date)
            
            logger.info(f"Yaklaşan görevler getirildi: kullanıcı={user_id}, adet={len(upcoming_tasks)}")
            return upcoming_tasks
        except Exception as e:
            logger.error(f"Yaklaşan görev getirme hatası: {e}")
            return []
    
    def complete_task(self, task_id: int, user_id: int) -> bool:
        """
        Görevi tamamla
        
        Args:
            task_id: Görev ID'si
            user_id: Kullanıcı ID'si
            
        Returns:
            Başarılı ise True
        """
        try:
            success = self.db_manager.update_task_status(task_id, user_id, True)
            if success:
                logger.info(f"Görev tamamlandı: id={task_id}, kullanıcı={user_id}")
            else:
                logger.warning(f"Görev bulunamadı: id={task_id}, kullanıcı={user_id}")
            return success
        except Exception as e:
            logger.error(f"Görev tamamlama hatası: {e}")
            return False
    
    def uncomplete_task(self, task_id: int, user_id: int) -> bool:
        """
        Görev tamamlanmasını geri al
        
        Args:
            task_id: Görev ID'si
            user_id: Kullanıcı ID'si
            
        Returns:
            Başarılı ise True
        """
        try:
            success = self.db_manager.update_task_status(task_id, user_id, False)
            if success:
                logger.info(f"Görev tamamlanması geri alındı: id={task_id}, kullanıcı={user_id}")
            else:
                logger.warning(f"Görev bulunamadı: id={task_id}, kullanıcı={user_id}")
            return success
        except Exception as e:
            logger.error(f"Görev güncelleme hatası: {e}")
            return False
    
    def delete_task(self, task_id: int, user_id: int) -> bool:
        """
        Görev sil
        
        Args:
            task_id: Görev ID'si
            user_id: Kullanıcı ID'si
            
        Returns:
            Başarılı ise True
        """
        try:
            success = self.db_manager.delete_task(task_id, user_id)
            if success:
                logger.info(f"Görev silindi: id={task_id}, kullanıcı={user_id}")
            else:
                logger.warning(f"Görev bulunamadı: id={task_id}, kullanıcı={user_id}")
            return success
        except Exception as e:
            logger.error(f"Görev silme hatası: {e}")
            return False
    
    def get_task_count(self, user_id: int, completed: bool = None) -> int:
        """
        Görev sayısını getir
        
        Args:
            user_id: Kullanıcı ID'si
            completed: Tamamlanma durumu filtresi
            
        Returns:
            Görev sayısı
        """
        try:
            if completed is None:
                tasks = self.db_manager.get_tasks(user_id, include_completed=True)
            else:
                all_tasks = self.db_manager.get_tasks(user_id, include_completed=True)
                tasks = [t for t in all_tasks if t.is_completed == completed]
            return len(tasks)
        except Exception as e:
            logger.error(f"Görev sayısı getirme hatası: {e}")
            return 0
