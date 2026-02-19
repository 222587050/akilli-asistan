"""
Yardımcı Fonksiyonlar
"""
import logging
from datetime import datetime
from typing import Optional
from dateutil import parser
import pytz

from config import TIMEZONE
from database.models import PriorityLevel

logger = logging.getLogger(__name__)


def format_date(dt: datetime, include_time: bool = True) -> str:
    """
    Tarihi Türkçe formatla
    
    Args:
        dt: Datetime nesnesi
        include_time: Saati dahil et
        
    Returns:
        Formatlanmış tarih stringi
    """
    if not dt:
        return "Belirtilmemiş"
    
    try:
        # UTC'den yerel zamana çevir
        tz = pytz.timezone(TIMEZONE)
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        local_dt = dt.astimezone(tz)
        
        if include_time:
            return local_dt.strftime("%d.%m.%Y %H:%M")
        else:
            return local_dt.strftime("%d.%m.%Y")
    except Exception as e:
        logger.error(f"Tarih formatlama hatası: {e}")
        return str(dt)


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Tarih stringini parse et
    
    Args:
        date_str: Tarih stringi (örn: "2024-01-15", "15.01.2024", "yarın")
        
    Returns:
        Datetime nesnesi veya None
    """
    if not date_str:
        return None
    
    try:
        # Türkçe kısayolları kontrol et
        now = datetime.now()
        date_str_lower = date_str.lower().strip()
        
        if date_str_lower in ['bugün', 'bugun']:
            return now.replace(hour=12, minute=0, second=0, microsecond=0)
        elif date_str_lower in ['yarın', 'yarin']:
            tomorrow = now.replace(hour=12, minute=0, second=0, microsecond=0)
            return tomorrow.replace(day=tomorrow.day + 1)
        
        # dateutil parser kullan
        parsed_date = parser.parse(date_str, dayfirst=True)
        
        # Timezone bilgisi ekle
        tz = pytz.timezone(TIMEZONE)
        if parsed_date.tzinfo is None:
            parsed_date = tz.localize(parsed_date)
        
        return parsed_date
    except Exception as e:
        logger.error(f"Tarih parse hatası: {e}")
        return None


def format_task_priority(priority: PriorityLevel) -> str:
    """
    Görev önceliğini emoji ile formatla
    
    Args:
        priority: PriorityLevel enum
        
    Returns:
        Emoji ile formatlanmış öncelik
    """
    emoji_map = {
        PriorityLevel.LOW: "🟢",
        PriorityLevel.MEDIUM: "🟡",
        PriorityLevel.HIGH: "🔴"
    }
    
    emoji = emoji_map.get(priority, "⚪")
    return f"{emoji} {priority.value.capitalize()}"


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Metni kısalt
    
    Args:
        text: Metin
        max_length: Maksimum uzunluk
        
    Returns:
        Kısaltılmış metin
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def format_note_list(notes: list) -> str:
    """
    Not listesini formatla
    
    Args:
        notes: Not listesi
        
    Returns:
        Formatlanmış string
    """
    if not notes:
        return "Henüz not bulunmuyor."
    
    result = []
    for i, note in enumerate(notes, 1):
        date_str = format_date(note.created_at, include_time=False)
        content_preview = truncate_text(note.content, 80)
        result.append(
            f"{i}. 📚 *{note.category}*\n"
            f"   {content_preview}\n"
            f"   📅 {date_str}\n"
            f"   🆔 ID: {note.id}"
        )
    
    return "\n\n".join(result)


def format_task_list(tasks: list) -> str:
    """
    Görev listesini formatla
    
    Args:
        tasks: Görev listesi
        
    Returns:
        Formatlanmış string
    """
    if not tasks:
        return "Henüz görev bulunmuyor."
    
    result = []
    for i, task in enumerate(tasks, 1):
        status = "✅" if task.is_completed else "⏳"
        priority_str = format_task_priority(task.priority)
        date_str = format_date(task.due_date) if task.due_date else "Tarih yok"
        
        result.append(
            f"{i}. {status} *{task.title}*\n"
            f"   {priority_str}\n"
            f"   📅 {date_str}\n"
            f"   🆔 ID: {task.id}"
        )
    
    return "\n\n".join(result)


def validate_category(category: str) -> str:
    """
    Kategori adını validate et ve standartlaştır
    
    Args:
        category: Kategori adı
        
    Returns:
        Standartlaştırılmış kategori adı
    """
    if not category:
        return "Genel"
    
    # İlk harfi büyük yap
    return category.strip().capitalize()
