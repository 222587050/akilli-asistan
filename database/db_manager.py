"""
Veritabanı Yönetim Sistemi
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from config import DATABASE_URL, MAX_CHAT_HISTORY
from .models import Base, User, Note, Task, Reminder, ChatHistory, PriorityLevel

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Veritabanı işlemlerini yöneten sınıf"""
    
    def __init__(self, db_url: str = DATABASE_URL):
        """
        Veritabanı yöneticisini başlat
        
        Args:
            db_url: Veritabanı bağlantı URL'si
        """
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._create_tables()
    
    def _create_tables(self):
        """Veritabanı tablolarını oluştur"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Veritabanı tabloları oluşturuldu")
        except SQLAlchemyError as e:
            logger.error(f"Tablo oluşturma hatası: {e}")
            raise
    
    def get_session(self) -> Session:
        """Yeni bir veritabanı oturumu döndür"""
        return self.SessionLocal()
    
    # ============ KULLANICI İŞLEMLERİ ============
    
    def get_or_create_user(self, telegram_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None) -> User:
        """
        Kullanıcıyı getir veya oluştur
        
        Args:
            telegram_id: Telegram kullanıcı ID'si
            username: Kullanıcı adı
            first_name: Ad
            last_name: Soyad
            
        Returns:
            User nesnesi (detached)
        """
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                session.add(user)
                session.commit()
                logger.info(f"Yeni kullanıcı oluşturuldu: {telegram_id}")
            else:
                # Kullanıcı bilgilerini güncelle
                user.username = username or user.username
                user.first_name = first_name or user.first_name
                user.last_name = last_name or user.last_name
                user.last_active = datetime.utcnow()
                session.commit()
            
            # Load all attributes before expunging
            _ = user.id, user.telegram_id, user.username, user.first_name, user.last_name
            session.expunge(user)
            return user
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Kullanıcı işlemi hatası: {e}")
            raise
        finally:
            session.close()
    
    # ============ NOT İŞLEMLERİ ============
    
    def add_note(self, user_id: int, category: str, content: str) -> Note:
        """
        Not ekle
        
        Args:
            user_id: Kullanıcı ID'si
            category: Not kategorisi
            content: Not içeriği
            
        Returns:
            Note nesnesi (detached)
        """
        session = self.get_session()
        try:
            note = Note(user_id=user_id, category=category, content=content)
            session.add(note)
            session.commit()
            logger.info(f"Not eklendi: kullanıcı={user_id}, kategori={category}")
            # Load attributes before expunging
            _ = note.id, note.category, note.content, note.created_at
            session.expunge(note)
            return note
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Not ekleme hatası: {e}")
            raise
        finally:
            session.close()
    
    def get_notes(self, user_id: int, category: str = None) -> List[Note]:
        """
        Kullanıcının notlarını getir
        
        Args:
            user_id: Kullanıcı ID'si
            category: Kategori filtresi (opsiyonel)
            
        Returns:
            Not listesi
        """
        session = self.get_session()
        try:
            query = session.query(Note).filter_by(user_id=user_id)
            
            if category:
                query = query.filter_by(category=category)
            
            notes = query.order_by(Note.created_at.desc()).all()
            return notes
        except SQLAlchemyError as e:
            logger.error(f"Not getirme hatası: {e}")
            return []
        finally:
            session.close()
    
    def search_notes(self, user_id: int, keyword: str) -> List[Note]:
        """
        Notlarda arama yap
        
        Args:
            user_id: Kullanıcı ID'si
            keyword: Arama kelimesi
            
        Returns:
            Bulunan notlar
        """
        session = self.get_session()
        try:
            notes = session.query(Note).filter(
                and_(
                    Note.user_id == user_id,
                    or_(
                        Note.content.contains(keyword),
                        Note.category.contains(keyword)
                    )
                )
            ).order_by(Note.created_at.desc()).all()
            return notes
        except SQLAlchemyError as e:
            logger.error(f"Not arama hatası: {e}")
            return []
        finally:
            session.close()
    
    def delete_note(self, note_id: int, user_id: int) -> bool:
        """
        Not sil
        
        Args:
            note_id: Not ID'si
            user_id: Kullanıcı ID'si
            
        Returns:
            Başarılı ise True
        """
        session = self.get_session()
        try:
            note = session.query(Note).filter_by(id=note_id, user_id=user_id).first()
            if note:
                session.delete(note)
                session.commit()
                logger.info(f"Not silindi: {note_id}")
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Not silme hatası: {e}")
            return False
        finally:
            session.close()
    
    # ============ GÖREV İŞLEMLERİ ============
    
    def add_task(self, user_id: int, title: str, description: str = None,
                priority: PriorityLevel = PriorityLevel.MEDIUM, 
                due_date: datetime = None) -> Task:
        """
        Görev ekle
        
        Args:
            user_id: Kullanıcı ID'si
            title: Görev başlığı
            description: Görev açıklaması
            priority: Öncelik seviyesi
            due_date: Bitiş tarihi
            
        Returns:
            Task nesnesi (detached)
        """
        session = self.get_session()
        try:
            task = Task(
                user_id=user_id,
                title=title,
                description=description,
                priority=priority,
                due_date=due_date
            )
            session.add(task)
            session.commit()
            logger.info(f"Görev eklendi: kullanıcı={user_id}, başlık={title}")
            # Load attributes before expunging
            _ = task.id, task.title, task.priority, task.due_date
            session.expunge(task)
            return task
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Görev ekleme hatası: {e}")
            raise
        finally:
            session.close()
    
    def get_tasks(self, user_id: int, include_completed: bool = False) -> List[Task]:
        """
        Kullanıcının görevlerini getir
        
        Args:
            user_id: Kullanıcı ID'si
            include_completed: Tamamlanmış görevleri dahil et
            
        Returns:
            Görev listesi
        """
        session = self.get_session()
        try:
            query = session.query(Task).filter_by(user_id=user_id)
            
            if not include_completed:
                query = query.filter_by(is_completed=False)
            
            tasks = query.order_by(Task.due_date.asc()).all()
            return tasks
        except SQLAlchemyError as e:
            logger.error(f"Görev getirme hatası: {e}")
            return []
        finally:
            session.close()
    
    def get_today_tasks(self, user_id: int) -> List[Task]:
        """
        Bugünkü görevleri getir
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            Bugünkü görevler
        """
        session = self.get_session()
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            tasks = session.query(Task).filter(
                and_(
                    Task.user_id == user_id,
                    Task.is_completed == False,
                    Task.due_date >= today_start,
                    Task.due_date < today_end
                )
            ).order_by(Task.due_date.asc()).all()
            return tasks
        except SQLAlchemyError as e:
            logger.error(f"Bugünkü görevleri getirme hatası: {e}")
            return []
        finally:
            session.close()
    
    def update_task_status(self, task_id: int, user_id: int, is_completed: bool) -> bool:
        """
        Görev durumunu güncelle
        
        Args:
            task_id: Görev ID'si
            user_id: Kullanıcı ID'si
            is_completed: Tamamlanma durumu
            
        Returns:
            Başarılı ise True
        """
        session = self.get_session()
        try:
            task = session.query(Task).filter_by(id=task_id, user_id=user_id).first()
            if task:
                task.is_completed = is_completed
                task.completed_at = datetime.utcnow() if is_completed else None
                session.commit()
                logger.info(f"Görev durumu güncellendi: {task_id}")
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Görev güncelleme hatası: {e}")
            return False
        finally:
            session.close()
    
    def delete_task(self, task_id: int, user_id: int) -> bool:
        """
        Görev sil
        
        Args:
            task_id: Görev ID'si
            user_id: Kullanıcı ID'si
            
        Returns:
            Başarılı ise True
        """
        session = self.get_session()
        try:
            task = session.query(Task).filter_by(id=task_id, user_id=user_id).first()
            if task:
                session.delete(task)
                session.commit()
                logger.info(f"Görev silindi: {task_id}")
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Görev silme hatası: {e}")
            return False
        finally:
            session.close()
    
    # ============ HATIRLATICI İŞLEMLERİ ============
    
    def add_reminder(self, user_id: int, message: str, remind_at: datetime,
                    is_recurring: bool = False, recurrence_pattern: str = None) -> Reminder:
        """
        Hatırlatıcı ekle
        
        Args:
            user_id: Kullanıcı ID'si
            message: Hatırlatıcı mesajı
            remind_at: Hatırlatma zamanı
            is_recurring: Tekrarlanan mı
            recurrence_pattern: Tekrar düzeni
            
        Returns:
            Reminder nesnesi (detached)
        """
        session = self.get_session()
        try:
            reminder = Reminder(
                user_id=user_id,
                message=message,
                remind_at=remind_at,
                is_recurring=is_recurring,
                recurrence_pattern=recurrence_pattern
            )
            session.add(reminder)
            session.commit()
            logger.info(f"Hatırlatıcı eklendi: kullanıcı={user_id}, zaman={remind_at}")
            # Load attributes before expunging
            _ = reminder.id, reminder.message, reminder.remind_at
            session.expunge(reminder)
            return reminder
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Hatırlatıcı ekleme hatası: {e}")
            raise
        finally:
            session.close()
    
    def get_pending_reminders(self) -> List[Reminder]:
        """
        Bekleyen hatırlatıcıları getir
        
        Returns:
            Hatırlatıcı listesi
        """
        session = self.get_session()
        try:
            now = datetime.utcnow()
            reminders = session.query(Reminder).filter(
                and_(
                    Reminder.is_sent == False,
                    Reminder.remind_at <= now
                )
            ).all()
            return reminders
        except SQLAlchemyError as e:
            logger.error(f"Hatırlatıcı getirme hatası: {e}")
            return []
        finally:
            session.close()
    
    def mark_reminder_sent(self, reminder_id: int) -> bool:
        """
        Hatırlatıcıyı gönderildi olarak işaretle
        
        Args:
            reminder_id: Hatırlatıcı ID'si
            
        Returns:
            Başarılı ise True
        """
        session = self.get_session()
        try:
            reminder = session.query(Reminder).filter_by(id=reminder_id).first()
            if reminder:
                reminder.is_sent = True
                session.commit()
                logger.info(f"Hatırlatıcı gönderildi işaretlendi: {reminder_id}")
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Hatırlatıcı işaretleme hatası: {e}")
            return False
        finally:
            session.close()
    
    # ============ SOHBET GEÇMİŞİ İŞLEMLERİ ============
    
    def add_chat_message(self, user_id: int, role: str, message: str) -> ChatHistory:
        """
        Sohbet mesajı ekle
        
        Args:
            user_id: Kullanıcı ID'si
            role: Rol ('user' veya 'assistant')
            message: Mesaj içeriği
            
        Returns:
            ChatHistory nesnesi (detached)
        """
        session = self.get_session()
        try:
            chat = ChatHistory(user_id=user_id, role=role, message=message)
            session.add(chat)
            session.commit()
            
            # Eski mesajları temizle
            self._cleanup_old_messages(session, user_id)
            
            session.expunge(chat)
            return chat
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Sohbet mesajı ekleme hatası: {e}")
            raise
        finally:
            session.close()
    
    def get_chat_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Sohbet geçmişini getir
        
        Args:
            user_id: Kullanıcı ID'si
            limit: Maksimum mesaj sayısı
            
        Returns:
            Sohbet geçmişi listesi
        """
        session = self.get_session()
        try:
            messages = session.query(ChatHistory).filter_by(
                user_id=user_id
            ).order_by(
                ChatHistory.created_at.desc()
            ).limit(limit).all()
            
            # Eski mesajlardan yeniye sıralama
            messages.reverse()
            
            # Gemini API format: role must be 'user' or 'model' 
            # Map 'assistant' -> 'model' for compatibility
            result = []
            for msg in messages:
                # Normalize role to Gemini-compatible values
                if msg.role == 'assistant':
                    role = 'model'
                elif msg.role == 'user':
                    role = 'user'
                elif msg.role == 'model':
                    role = 'model'
                else:
                    # Skip invalid roles to prevent API errors
                    logger.warning(f"Skipping message with invalid role: {msg.role}")
                    continue
                
                result.append({
                    'role': role,
                    'parts': [{'text': msg.message}]
                })
            
            return result
        except SQLAlchemyError as e:
            logger.error(f"Sohbet geçmişi getirme hatası: {e}")
            return []
        finally:
            session.close()
    
    def _cleanup_old_messages(self, session: Session, user_id: int):
        """Eski mesajları temizle"""
        try:
            count = session.query(ChatHistory).filter_by(user_id=user_id).count()
            
            if count > MAX_CHAT_HISTORY:
                # En eski mesajları sil
                delete_count = count - MAX_CHAT_HISTORY
                old_messages = session.query(ChatHistory).filter_by(
                    user_id=user_id
                ).order_by(
                    ChatHistory.created_at.asc()
                ).limit(delete_count).all()
                
                for msg in old_messages:
                    session.delete(msg)
                
                session.commit()
                logger.info(f"Eski mesajlar temizlendi: {delete_count} adet")
        except SQLAlchemyError as e:
            logger.error(f"Mesaj temizleme hatası: {e}")
