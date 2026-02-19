"""
SQLAlchemy Veritabanı Modelleri
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


class PriorityLevel(enum.Enum):
    """Öncelik seviyeleri"""
    LOW = "düşük"
    MEDIUM = "orta"
    HIGH = "yüksek"


class User(Base):
    """Kullanıcı modeli"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


class Note(Base):
    """Not modeli"""
    __tablename__ = 'notes'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)  # Matematik, Fizik, vb.
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Note(id={self.id}, user_id={self.user_id}, category={self.category})>"


class Task(Base):
    """Görev/Ajanda modeli"""
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    priority = Column(Enum(PriorityLevel), default=PriorityLevel.MEDIUM)
    due_date = Column(DateTime)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Task(id={self.id}, user_id={self.user_id}, title={self.title}, priority={self.priority})>"


class Reminder(Base):
    """Hatırlatıcı modeli"""
    __tablename__ = 'reminders'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    message = Column(Text, nullable=False)
    remind_at = Column(DateTime, nullable=False, index=True)
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String(50))  # daily, weekly, monthly
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Reminder(id={self.id}, user_id={self.user_id}, remind_at={self.remind_at})>"


class ChatHistory(Base):
    """Sohbet geçmişi modeli (AI context için)"""
    __tablename__ = 'chat_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' veya 'assistant'
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<ChatHistory(id={self.id}, user_id={self.user_id}, role={self.role})>"
