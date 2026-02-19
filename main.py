"""
Akıllı Kişisel Asistan - Ana Uygulama
Telegram bot ve hatırlatıcı sistemi ile çalışan AI destekli kişisel asistan
"""
import logging
import signal
import sys
import asyncio
from pathlib import Path

from config import check_config, logger, REPLICATE_API_TOKEN
from database import DatabaseManager
from modules.ai_assistant import AIAssistant
from modules.ai_teacher import AITeacher
from modules.notes_manager import NotesManager
from modules.schedule_manager import ScheduleManager
from modules.telegram_bot import TelegramBot
from modules.whatsapp_bot import WhatsAppBot
from utils.reminders import ReminderScheduler

# Global değişkenler
db_manager = None
telegram_bot = None
reminder_scheduler = None
whatsapp_bot = None


def setup_logging():
    """Loglama sistemini kur"""
    # Konsol handler zaten config.py'de ayarlandı
    # İsteğe bağlı olarak dosya handler eklenebilir
    
    # Log dizinini oluştur
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Dosya handler ekle
    file_handler = logging.FileHandler(log_dir / "assistant.log", encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Root logger'a ekle
    logging.getLogger().addHandler(file_handler)
    
    logger.info("Loglama sistemi kuruldu")


def initialize_database():
    """Veritabanını başlat"""
    global db_manager
    
    try:
        db_manager = DatabaseManager()
        logger.info("Veritabanı başarıyla başlatıldı")
        return db_manager
    except Exception as e:
        logger.error(f"Veritabanı başlatma hatası: {e}")
        raise


def check_reminders():
    """Bekleyen hatırlatıcıları kontrol et ve gönder"""
    global db_manager, telegram_bot
    
    if not db_manager or not telegram_bot:
        return
    
    try:
        # Bekleyen hatırlatıcıları al
        reminders = db_manager.get_pending_reminders()
        
        for reminder in reminders:
            # Telegram kullanıcı ID'sini al
            session = db_manager.get_session()
            try:
                from database.models import User
                user = session.query(User).filter_by(id=reminder.user_id).first()
                
                if user:
                    # Hatırlatıcı gönder
                    asyncio.create_task(
                        telegram_bot.send_reminder_notification(
                            user.telegram_id,
                            reminder.message
                        )
                    )
                    
                    # Hatırlatıcıyı gönderildi olarak işaretle
                    db_manager.mark_reminder_sent(reminder.id)
                    
                    logger.info(f"Hatırlatıcı gönderildi: ID={reminder.id}, kullanıcı={user.telegram_id}")
            finally:
                session.close()
                
    except Exception as e:
        logger.error(f"Hatırlatıcı kontrolü hatası: {e}")


def initialize_components():
    """Tüm bileşenleri başlat"""
    global db_manager, telegram_bot, reminder_scheduler, whatsapp_bot
    
    logger.info("Bileşenler başlatılıyor...")
    
    # Veritabanını başlat
    db_manager = initialize_database()
    
    # AI Asistan'ı başlat
    ai_assistant = AIAssistant(db_manager)
    if not ai_assistant.is_available():
        logger.warning("AI asistan kullanılamıyor. GEMINI_API_KEY kontrol edin.")

    # AI Öğretmen'i başlat (mevcut Gemini modelini kullan)
    ai_teacher = None
    if ai_assistant.is_available():
        ai_teacher = AITeacher(ai_assistant.model)
        logger.info("✅ AI Öğretmen başlatıldı")
    else:
        logger.warning("⚠️ AI Öğretmen başlatılamadı (AI asistan kullanılamıyor)")
    
    # Not yöneticisini başlat
    notes_manager = NotesManager(db_manager)
    
    # Ajanda yöneticisini başlat
    schedule_manager = ScheduleManager(db_manager)
    
    # Telegram bot'u başlat
    telegram_bot = TelegramBot(
        db_manager=db_manager,
        ai_assistant=ai_assistant,
        notes_manager=notes_manager,
        schedule_manager=schedule_manager,
        replicate_api_token=REPLICATE_API_TOKEN,
        ai_teacher=ai_teacher,
    )
    
    # Hatırlatıcı zamanlayıcısını başlat
    reminder_scheduler = ReminderScheduler(reminder_callback=check_reminders)
    reminder_scheduler.start()
    
    # WhatsApp bot (placeholder)
    whatsapp_bot = WhatsAppBot()
    
    logger.info("Tüm bileşenler başarıyla başlatıldı")


def signal_handler(sig, frame):
    """Graceful shutdown için signal handler"""
    logger.info(f"Signal alındı: {sig}")
    logger.info("Uygulama kapatılıyor...")
    
    # Hatırlatıcı zamanlayıcısını durdur
    if reminder_scheduler:
        reminder_scheduler.stop()
    
    # WhatsApp bot'u durdur (placeholder)
    if whatsapp_bot:
        whatsapp_bot.stop()
    
    logger.info("Uygulama başarıyla kapatıldı")
    sys.exit(0)


def print_banner():
    """Başlangıç banner'ı yazdır"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║       🤖  AKILLI KİŞİSEL ASİSTAN  🤖                     ║
║                                                           ║
║   AI Destekli Ders Yardımcısı ve Kişisel Ajanda         ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(banner)
    logger.info("Akıllı Kişisel Asistan başlatılıyor...")


def main():
    """Ana fonksiyon"""
    try:
        # Banner yazdır
        print_banner()
        
        # Loglama sistemini kur
        setup_logging()
        
        # Yapılandırmayı kontrol et
        if not check_config():
            logger.error("Yapılandırma eksik! Lütfen .env dosyasını oluşturun ve gerekli değerleri ekleyin.")
            logger.info("Örnek için .env.example dosyasına bakın.")
            sys.exit(1)
        
        logger.info("Yapılandırma kontrolü başarılı")
        
        # Signal handler'ları kaydet
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Bileşenleri başlat
        initialize_components()
        
        # Bot'u çalıştır (blocking)
        logger.info("Telegram bot çalıştırılıyor...")
        logger.info("Bot çalışıyor... Durdurmak için Ctrl+C'ye basın.")
        
        telegram_bot.run()
        
    except KeyboardInterrupt:
        logger.info("Kullanıcı tarafından durduruldu")
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        logger.error(f"Kritik hata: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
