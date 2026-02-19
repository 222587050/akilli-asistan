"""
Yapılandırma Ayarları
"""
import os
import logging
from dotenv import load_dotenv
from pathlib import Path

# .env dosyasını yükle
load_dotenv()

# Proje dizini
BASE_DIR = Path(__file__).resolve().parent

# API Anahtarları
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# Veritabanı
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR}/data/assistant.db')

# Zaman Dilimi
TIMEZONE = os.getenv('TIMEZONE', 'Europe/Istanbul')

# Loglama Ayarları
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Loglama yapılandırması
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)

# Logger
logger = logging.getLogger(__name__)

# Yapılandırma kontrolü
def check_config():
    """Gerekli yapılandırmaları kontrol et"""
    missing = []
    
    if not GEMINI_API_KEY:
        missing.append('GEMINI_API_KEY')
    
    if not TELEGRAM_BOT_TOKEN:
        missing.append('TELEGRAM_BOT_TOKEN')
    
    if missing:
        logger.warning(f"Eksik yapılandırma: {', '.join(missing)}")
        logger.warning("Lütfen .env dosyasını oluşturun ve gerekli değerleri ekleyin")
        return False
    
    return True

# Gemini AI Ayarları
GEMINI_MODEL = 'gemini-pro'
GEMINI_TEMPERATURE = 0.7
GEMINI_MAX_TOKENS = 2048

# Chat Geçmişi Limitleri
MAX_CHAT_HISTORY = 50  # Veritabanında saklanacak maksimum mesaj sayısı
CONTEXT_WINDOW = 10    # AI'ya gönderilecek son mesaj sayısı

# Hatırlatıcı Ayarları
REMINDER_CHECK_INTERVAL = 60  # Saniye cinsinden kontrol aralığı
