"""
Veritabanı Yönetim Sistemi
"""
import logging
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from config import DATABASE_URL, MAX_CHAT_HISTORY
from .models import Base, User, Note, Task, Reminder, ChatHistory, PriorityLevel, Course, Topic, Quiz, StudyProgress

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

    # ============ DERS YÖNETİMİ İŞLEMLERİ ============

    def add_course(self, user_id: int, name: str, description: str) -> int:
        """
        Ders ekle

        Args:
            user_id: Kullanıcı ID'si
            name: Ders adı
            description: Ders açıklaması

        Returns:
            Yeni kurs ID'si
        """
        session = self.get_session()
        try:
            # Aynı kullanıcı için aynı isimde ders varsa güncelle
            existing = session.query(Course).filter_by(user_id=user_id, name=name).first()
            if existing:
                existing.description = description
                session.commit()
                course_id = existing.id
            else:
                course = Course(user_id=user_id, name=name, description=description)
                session.add(course)
                session.commit()
                course_id = course.id
            logger.info(f"Ders eklendi/güncellendi: kullanıcı={user_id}, ders={name}")
            return course_id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ders ekleme hatası: {e}")
            raise
        finally:
            session.close()

    def add_topic(self, course_id: int, title: str, week: int) -> int:
        """
        Kursa konu ekle

        Args:
            course_id: Kurs ID'si
            title: Konu başlığı
            week: Hafta numarası

        Returns:
            Yeni konu ID'si
        """
        session = self.get_session()
        try:
            # Aynı kurs için aynı başlıkta konu varsa atla
            existing = session.query(Topic).filter_by(course_id=course_id, title=title).first()
            if existing:
                return existing.id
            topic = Topic(course_id=course_id, title=title, week_number=week)
            session.add(topic)
            # Kursun total_topics sayısını güncelle
            course = session.query(Course).filter_by(id=course_id).first()
            if course:
                count = session.query(Topic).filter_by(course_id=course_id).count()
                course.total_topics = count + 1
            session.commit()
            topic_id = topic.id
            logger.info(f"Konu eklendi: kurs={course_id}, başlık={title}")
            return topic_id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Konu ekleme hatası: {e}")
            raise
        finally:
            session.close()

    def get_user_courses(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Kullanıcının derslerini getir

        Args:
            user_id: Kullanıcı ID'si

        Returns:
            Ders listesi (dict)
        """
        session = self.get_session()
        try:
            courses = session.query(Course).filter_by(user_id=user_id).order_by(Course.id).all()
            result = []
            for c in courses:
                # Tamamlanan konu sayısını hesapla
                completed = session.query(Topic).filter_by(course_id=c.id, is_completed=True).count()
                total = session.query(Topic).filter_by(course_id=c.id).count()
                result.append({
                    'id': c.id,
                    'name': c.name,
                    'description': c.description,
                    'total_topics': total,
                    'completed_topics': completed,
                    'created_at': c.created_at,
                })
            return result
        except SQLAlchemyError as e:
            logger.error(f"Ders getirme hatası: {e}")
            return []
        finally:
            session.close()

    def get_course_topics(self, course_id: int) -> List[Dict[str, Any]]:
        """
        Kursun konularını getir

        Args:
            course_id: Kurs ID'si

        Returns:
            Konu listesi (dict)
        """
        session = self.get_session()
        try:
            topics = session.query(Topic).filter_by(course_id=course_id).order_by(Topic.week_number).all()
            return [
                {
                    'id': t.id,
                    'title': t.title,
                    'week_number': t.week_number,
                    'is_completed': t.is_completed,
                    'completed_at': t.completed_at,
                }
                for t in topics
            ]
        except SQLAlchemyError as e:
            logger.error(f"Konu getirme hatası: {e}")
            return []
        finally:
            session.close()

    def get_next_topic(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Kullanıcının sıradaki tamamlanmamış konusunu getir

        Args:
            user_id: Kullanıcı ID'si

        Returns:
            Konu bilgisi dict veya None
        """
        session = self.get_session()
        try:
            topic = (
                session.query(Topic, Course)
                .join(Course, Topic.course_id == Course.id)
                .filter(Course.user_id == user_id, Topic.is_completed == False)
                .order_by(Course.id, Topic.week_number)
                .first()
            )
            if topic:
                t, c = topic
                return {
                    'topic_id': t.id,
                    'topic_title': t.title,
                    'week_number': t.week_number,
                    'course_id': c.id,
                    'course_name': c.name,
                }
            return None
        except SQLAlchemyError as e:
            logger.error(f"Sıradaki konu getirme hatası: {e}")
            return None
        finally:
            session.close()

    def get_next_topics(self, user_id: int, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Kullanıcının sıradaki tamamlanmamış konularını getir

        Args:
            user_id: Kullanıcı ID'si
            limit: Maksimum konu sayısı

        Returns:
            Konu listesi (dict)
        """
        session = self.get_session()
        try:
            rows = (
                session.query(Topic, Course)
                .join(Course, Topic.course_id == Course.id)
                .filter(Course.user_id == user_id, Topic.is_completed == False)
                .order_by(Course.id, Topic.week_number)
                .limit(limit)
                .all()
            )
            return [
                {
                    'topic_id': t.id,
                    'topic_title': t.title,
                    'week_number': t.week_number,
                    'course_id': c.id,
                    'course_name': c.name,
                }
                for t, c in rows
            ]
        except SQLAlchemyError as e:
            logger.error(f"Sıradaki konular getirme hatası: {e}")
            return []
        finally:
            session.close()

    def mark_topic_completed(self, user_id: int, course_name: str, topic_title: str) -> bool:
        """
        Konuyu tamamlandı olarak işaretle

        Args:
            user_id: Kullanıcı ID'si
            course_name: Ders adı
            topic_title: Konu başlığı

        Returns:
            Başarılı ise True
        """
        session = self.get_session()
        try:
            course = session.query(Course).filter(
                Course.user_id == user_id,
                Course.name.ilike(f"%{course_name}%")
            ).first()
            if not course:
                return False
            topic = session.query(Topic).filter(
                Topic.course_id == course.id,
                Topic.title.ilike(f"%{topic_title}%")
            ).first()
            if not topic:
                return False
            if not topic.is_completed:
                topic.is_completed = True
                topic.completed_at = datetime.utcnow()
                # completed_topics sayısını güncelle (is_completed True yapıldıktan sonra say)
                completed_count = session.query(Topic).filter_by(
                    course_id=course.id, is_completed=True
                ).count()
                course.completed_topics = completed_count
                # Çalışma ilerlemesini güncelle
                self._update_study_progress(session, user_id, course.id)
                session.commit()
                logger.info(f"Konu tamamlandı: kullanıcı={user_id}, konu={topic_title}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Konu tamamlama hatası: {e}")
            return False
        finally:
            session.close()

    def mark_topic_completed_by_id(self, user_id: int, topic_id: int) -> bool:
        """
        Konu ID'si ile konuyu tamamlandı olarak işaretle

        Args:
            user_id: Kullanıcı ID'si
            topic_id: Konu ID'si

        Returns:
            Başarılı ise True
        """
        session = self.get_session()
        try:
            topic = session.query(Topic).filter_by(id=topic_id).first()
            if not topic:
                return False
            course = session.query(Course).filter_by(id=topic.course_id, user_id=user_id).first()
            if not course:
                return False
            if not topic.is_completed:
                topic.is_completed = True
                topic.completed_at = datetime.utcnow()
                completed_count = session.query(Topic).filter_by(
                    course_id=course.id, is_completed=True
                ).count()
                course.completed_topics = completed_count
                self._update_study_progress(session, user_id, course.id)
                session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Konu tamamlama hatası: {e}")
            return False
        finally:
            session.close()

    def _update_study_progress(self, session: Session, user_id: int, course_id: int):
        """Çalışma ilerlemesini güncelle (internal)"""
        try:
            today = date.today()
            progress = session.query(StudyProgress).filter_by(
                user_id=user_id, course_id=course_id
            ).first()
            if not progress:
                progress = StudyProgress(
                    user_id=user_id,
                    course_id=course_id,
                    last_study_date=today,
                    streak_days=1
                )
                session.add(progress)
            else:
                if progress.last_study_date == today:
                    pass  # Aynı gün, streak değişmez
                elif progress.last_study_date == today - timedelta(days=1):
                    progress.streak_days += 1
                    progress.last_study_date = today
                else:
                    progress.streak_days = 1
                    progress.last_study_date = today
        except SQLAlchemyError as e:
            logger.error(f"Çalışma ilerlemesi güncelleme hatası: {e}")

    def add_quiz_result(self, user_id: int, topic_id: int, score: int, total: int):
        """
        Quiz sonucunu kaydet

        Args:
            user_id: Kullanıcı ID'si
            topic_id: Konu ID'si
            score: Doğru sayısı
            total: Toplam soru sayısı
        """
        session = self.get_session()
        try:
            quiz = Quiz(
                user_id=user_id,
                topic_id=topic_id,
                score=score,
                total_questions=total
            )
            session.add(quiz)
            session.commit()
            logger.info(f"Quiz sonucu kaydedildi: kullanıcı={user_id}, skor={score}/{total}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Quiz sonucu kaydetme hatası: {e}")
        finally:
            session.close()

    def get_avg_quiz_score(self, user_id: int, course_id: int) -> Optional[float]:
        """
        Ders için quiz ortalamasını getir

        Args:
            user_id: Kullanıcı ID'si
            course_id: Kurs ID'si

        Returns:
            Yüzde olarak ortalama skor veya None
        """
        session = self.get_session()
        try:
            topic_ids = [
                t.id for t in session.query(Topic).filter_by(course_id=course_id).all()
            ]
            if not topic_ids:
                return None
            quizzes = session.query(Quiz).filter(
                Quiz.user_id == user_id,
                Quiz.topic_id.in_(topic_ids),
                Quiz.total_questions > 0
            ).all()
            if not quizzes:
                return None
            total_pct = sum(
                (q.score / q.total_questions) * 100 for q in quizzes
            )
            return total_pct / len(quizzes)
        except SQLAlchemyError as e:
            logger.error(f"Quiz ortalaması getirme hatası: {e}")
            return None
        finally:
            session.close()

    def get_streak(self, user_id: int) -> int:
        """
        Kullanıcının en yüksek çalışma streak'ini getir

        Args:
            user_id: Kullanıcı ID'si

        Returns:
            Streak gün sayısı
        """
        session = self.get_session()
        try:
            progresses = session.query(StudyProgress).filter_by(user_id=user_id).all()
            if not progresses:
                return 0
            return max(p.streak_days for p in progresses)
        except SQLAlchemyError as e:
            logger.error(f"Streak getirme hatası: {e}")
            return 0
        finally:
            session.close()

    def get_total_quizzes(self, user_id: int) -> int:
        """
        Kullanıcının toplam quiz sayısını getir

        Args:
            user_id: Kullanıcı ID'si

        Returns:
            Toplam quiz sayısı
        """
        session = self.get_session()
        try:
            return session.query(Quiz).filter_by(user_id=user_id).count()
        except SQLAlchemyError as e:
            logger.error(f"Toplam quiz sayısı getirme hatası: {e}")
            return 0
        finally:
            session.close()

    def get_last_quiz_results(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Son quiz sonuçlarını getir

        Args:
            user_id: Kullanıcı ID'si
            limit: Maksimum sonuç sayısı

        Returns:
            Quiz sonuç listesi (dict)
        """
        session = self.get_session()
        try:
            quizzes = (
                session.query(Quiz, Topic)
                .join(Topic, Quiz.topic_id == Topic.id)
                .filter(Quiz.user_id == user_id)
                .order_by(Quiz.completed_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    'score': q.score,
                    'total_questions': q.total_questions,
                    'completed_at': q.completed_at,
                    'topic_title': t.title,
                }
                for q, t in quizzes
            ]
        except SQLAlchemyError as e:
            logger.error(f"Son quiz sonuçları getirme hatası: {e}")
            return []
        finally:
            session.close()
