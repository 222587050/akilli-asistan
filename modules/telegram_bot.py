"""
Telegram Bot Arayüzü
Kullanıcı etkileşimi için komut tabanlı bot
"""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes,
    filters
)

try:
    from PIL import Image
except ImportError:
    Image = None

from config import TELEGRAM_BOT_TOKEN
from database import DatabaseManager
from modules.ai_assistant import AIAssistant
from modules.ai_teacher import AITeacher
from modules.web_search import WebSearchAssistant
from modules.notes_manager import NotesManager
from modules.schedule_manager import ScheduleManager
from utils.helpers import format_note_list, format_task_list, format_date

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram Bot Sınıfı"""
    
    # AI mesaj handler için context bilgisi
    MESSAGE_HANDLER_CONTEXT = (
        "Sen Türkçe konuşan akıllı bir kişisel asistansın. "
        "Kullanıcılara ders konularında, not almada ve görev yönetiminde yardımcı oluyorsun. "
        "Dostça, açık ve anlaşılır cevaplar veriyorsun. "
        "Eğer kullanıcı not veya görev eklemek istiyorsa, ilgili komutları öner "
        "(/not_ekle, /gorev_ekle gibi)."
    )
    
    def __init__(self, db_manager: DatabaseManager, ai_assistant: AIAssistant,
                 notes_manager: NotesManager, schedule_manager: ScheduleManager,
                 replicate_api_token: str = None, ai_teacher: AITeacher = None):
        """
        Telegram bot'u başlat
        
        Args:
            db_manager: Veritabanı yöneticisi
            ai_assistant: AI asistan
            notes_manager: Not yöneticisi
            schedule_manager: Ajanda yöneticisi
            replicate_api_token: Replicate API token (opsiyonel)
            ai_teacher: AI öğretmen (opsiyonel)
        """
        self.db_manager = db_manager
        self.ai_assistant = ai_assistant
        self.notes_manager = notes_manager
        self.schedule_manager = schedule_manager
        self.ai_teacher = ai_teacher

        # Web Search Asistanı (AI asistan modelini kullan)
        self.web_search_assistant = None
        if ai_assistant and ai_assistant.is_available():
            self.web_search_assistant = WebSearchAssistant(ai_assistant.model)
            logger.info("✅ Web Search Asistanı başlatıldı")
        
        # Görüntü işleme modülleri (eğer API token varsa)
        self.image_upscaler = None
        self.image_handler = None
        
        if replicate_api_token:
            from modules.image_upscaler import ImageUpscaler
            from modules.image_handler import TelegramImageHandler
            
            self.image_upscaler = ImageUpscaler(replicate_api_token)
            self.image_handler = TelegramImageHandler()
            logger.info("✅ Replicate görüntü yükseltme modülü başlatıldı (4x upscaling)")
        else:
            logger.warning("⚠️ REPLICATE_API_TOKEN bulunamadı. Görüntü yükseltme özellikleri çalışmayacak.")
        
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN bulunamadı!")
        
        # Bot uygulamasını oluştur
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Komut handler'larını ekle
        self._register_handlers()
        
        logger.info("TelegramBot başlatıldı")
