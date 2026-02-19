"""
Telegram Bot Arayüzü
Kullanıcı etkileşimi için komut tabanlı bot
"""
import logging
import re
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

from config import TELEGRAM_BOT_TOKEN
from database import DatabaseManager
from modules.ai_assistant import AIAssistant
from modules.notes_manager import NotesManager
from modules.schedule_manager import ScheduleManager
from utils.helpers import format_note_list, format_task_list, format_date

logger = logging.getLogger(__name__)

# AI asistan için varsayılan context bilgisi
DEFAULT_AI_CONTEXT = (
    "Sen Türkçe konuşan akıllı bir kişisel asistansın. "
    "Kullanıcılara ders konularında, not almada ve görev yönetiminde yardımcı oluyorsun. "
    "Dostça, açık ve anlaşılır cevaplar veriyorsun. "
    "Eğer kullanıcı not veya görev eklemek istiyorsa, ilgili komutları öner "
    "(/not_ekle, /gorev_ekle gibi)."
)

# Komut önerisi için anahtar kelimeler ve önceden derlenmiş regex pattern'leri
COMMAND_HINTS = {
    'not ekle': ('/not_ekle', re.compile(r'\bnot ekle\b')),
    'not sil': ('/not_sil', re.compile(r'\bnot sil\b')),
    'notlarım': ('/notlar', re.compile(r'\bnotlarım\b')),
    'notları göster': ('/notlar', re.compile(r'\bnotları göster\b')),
    'not ara': ('/not_ara', re.compile(r'\bnot ara\b')),
    'görev ekle': ('/gorev_ekle', re.compile(r'\bgörev ekle\b')),
    'görev sil': ('/gorev_sil', re.compile(r'\bgörev sil\b')),
    'görevlerim': ('/gorevler', re.compile(r'\bgörevlerim\b')),
    'görevleri göster': ('/gorevler', re.compile(r'\bgörevleri göster\b')),
    'bugünkü görevler': ('/bugun', re.compile(r'\bbugünkü görevler\b')),
    'görev tamamla': ('/gorev_tamamla', re.compile(r'\bgörev tamamla\b')),
    'hatırlatıcı': ('/hatirlatici', re.compile(r'\bhatırlatıcı\b')),
    'hatırlatıcı ekle': ('/hatirlatici', re.compile(r'\bhatırlatıcı ekle\b')),
    'yardım': ('/yardim', re.compile(r'\byardım\b')),
    'komutlar': ('/yardim', re.compile(r'\bkomutlar\b')),
}


class TelegramBot:
    """Telegram Bot Sınıfı"""
    
    def __init__(self, db_manager: DatabaseManager, ai_assistant: AIAssistant,
                 notes_manager: NotesManager, schedule_manager: ScheduleManager):
        """
        Telegram bot'u başlat
        
        Args:
            db_manager: Veritabanı yöneticisi
            ai_assistant: AI asistan
            notes_manager: Not yöneticisi
            schedule_manager: Ajanda yöneticisi
        """
        self.db_manager = db_manager
        self.ai_assistant = ai_assistant
        self.notes_manager = notes_manager
        self.schedule_manager = schedule_manager
        
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN bulunamadı!")
        
        # Bot uygulamasını oluştur
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Komut handler'larını ekle
        self._register_handlers()
        
        logger.info("TelegramBot başlatıldı")
    
    def _register_handlers(self):
        """Komut handler'larını kaydet"""
        # Komutlar
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("yardim", self.help_command))
        self.application.add_handler(CommandHandler("sohbet", self.chat_command))
        self.application.add_handler(CommandHandler("not_ekle", self.add_note_command))
        self.application.add_handler(CommandHandler("notlar", self.list_notes_command))
        self.application.add_handler(CommandHandler("not_ara", self.search_notes_command))
        self.application.add_handler(CommandHandler("not_sil", self.delete_note_command))
        self.application.add_handler(CommandHandler("gorev_ekle", self.add_task_command))
        self.application.add_handler(CommandHandler("gorevler", self.list_tasks_command))
        self.application.add_handler(CommandHandler("bugun", self.today_tasks_command))
        self.application.add_handler(CommandHandler("gorev_tamamla", self.complete_task_command))
        self.application.add_handler(CommandHandler("gorev_sil", self.delete_task_command))
        self.application.add_handler(CommandHandler("hatirlatici", self.add_reminder_command))
        
        # Callback handler (inline butonlar için)
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # DİKKAT: Bu handler'ı tüm diğer handler'lardan SONRA ekle!
        # Çünkü diğer komutlar önce işlenmeli
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,  # Komut olmayan text mesajlar
                self.handle_message
            )
        )
        
        logger.info("Handler'lar kaydedildi")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bot'u başlat - /start"""
        user = update.effective_user
        
        # Kullanıcıyı veritabanına kaydet
        self.db_manager.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        welcome_message = f"""
🤖 *Merhaba {user.first_name}!*

Ben senin akıllı kişisel asistanınım. Sana şu konularda yardımcı olabilirim:

📚 *Ders Yardımı*
• AI destekli soru cevaplama
• Not özetleme ve açıklama

📝 *Not Yönetimi*
• Kategorilere göre not alma
• Not arama ve listeleme

📅 *Ajanda & Görevler*
• Görev ekleme ve takibi
• Bugünkü görevleri görüntüleme

⏰ *Hatırlatıcılar*
• Ödev ve sınav hatırlatıcıları
• Randevu bildirimleri

Kullanılabilir komutları görmek için /yardim yazabilirsin!
"""
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Yardım mesajı - /yardim"""
        help_text = """
📖 *Komut Listesi*

*AI Sohbet:*
/sohbet [mesajınız] - AI ile sohbet et

*Not İşlemleri:*
/not_ekle [kategori] [not] - Yeni not ekle
/notlar - Tüm notları listele
/not_ara [kelime] - Notlarda ara
/not_sil [id] - Not sil

*Görev İşlemleri:*
/gorev_ekle [görev] [tarih] - Yeni görev ekle
/gorevler - Tüm görevleri listele
/bugun - Bugünkü görevler
/gorev_tamamla [id] - Görevi tamamla
/gorev_sil [id] - Görev sil

*Hatırlatıcı:*
/hatirlatici [mesaj] [tarih/saat] - Hatırlatıcı ekle

*Diğer:*
/start - Bot'u başlat
/yardim - Bu yardım mesajı

*Örnekler:*
`/not_ekle Matematik Pisagor teoremi: a² + b² = c²`
`/gorev_ekle Fizik ödevi yap 25.12.2024`
`/sohbet Kuantum fiziği nedir?`
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """AI ile sohbet - /sohbet"""
        user_id = update.effective_user.id
        
        # Mesajı al
        if not context.args:
            await update.message.reply_text(
                "Lütfen bir mesaj yazın.\nÖrnek: /sohbet Gravitasyon nedir?"
            )
            return
        
        message = " ".join(context.args)
        
        # "Yazıyor..." göstergesi
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # AI'dan yanıt al
        response = self.ai_assistant.chat(user_id, message)
        
        await update.message.reply_text(response)
    
    async def add_note_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Not ekle - /not_ekle"""
        user_id = update.effective_user.id
        
        if len(context.args) < 2:
            await update.message.reply_text(
                "Lütfen kategori ve not içeriği girin.\n"
                "Örnek: /not_ekle Matematik Pisagor teoremi: a² + b² = c²"
            )
            return
        
        category = context.args[0]
        content = " ".join(context.args[1:])
        
        try:
            note = self.notes_manager.add_note(user_id, category, content)
            await update.message.reply_text(
                f"✅ Not eklendi!\n"
                f"📚 Kategori: {note.category}\n"
                f"📅 Tarih: {format_date(note.created_at)}\n"
                f"🆔 ID: {note.id}"
            )
        except Exception as e:
            logger.error(f"Not ekleme hatası: {e}")
            await update.message.reply_text("❌ Not eklenirken bir hata oluştu.")
    
    async def list_notes_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Notları listele - /notlar"""
        user_id = update.effective_user.id
        
        notes = self.notes_manager.get_all_notes(user_id)
        
        if not notes:
            await update.message.reply_text("Henüz not bulunmuyor. /not_ekle komutu ile not ekleyebilirsin.")
            return
        
        formatted_notes = format_note_list(notes)
        
        await update.message.reply_text(
            f"📚 *Notlarınız* ({len(notes)} adet)\n\n{formatted_notes}",
            parse_mode='Markdown'
        )
    
    async def search_notes_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Notlarda ara - /not_ara"""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text(
                "Lütfen arama kelimesi girin.\nÖrnek: /not_ara Pisagor"
            )
            return
        
        keyword = " ".join(context.args)
        notes = self.notes_manager.search_notes(user_id, keyword)
        
        if not notes:
            await update.message.reply_text(f"'{keyword}' ile ilgili not bulunamadı.")
            return
        
        formatted_notes = format_note_list(notes)
        
        await update.message.reply_text(
            f"🔍 *Arama Sonuçları* '{keyword}' ({len(notes)} adet)\n\n{formatted_notes}",
            parse_mode='Markdown'
        )
    
    async def delete_note_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Not sil - /not_sil"""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text(
                "Lütfen not ID'si girin.\nÖrnek: /not_sil 5"
            )
            return
        
        try:
            note_id = int(context.args[0])
            success = self.notes_manager.delete_note(note_id, user_id)
            
            if success:
                await update.message.reply_text(f"✅ Not silindi (ID: {note_id})")
            else:
                await update.message.reply_text(f"❌ Not bulunamadı (ID: {note_id})")
        except ValueError:
            await update.message.reply_text("❌ Geçersiz not ID'si. Lütfen bir sayı girin.")
    
    async def add_task_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Görev ekle - /gorev_ekle"""
        user_id = update.effective_user.id
        
        if len(context.args) < 1:
            await update.message.reply_text(
                "Lütfen görev başlığı girin.\n"
                "Örnek: /gorev_ekle Fizik ödevi yap 25.12.2024"
            )
            return
        
        # Son kelime tarih olabilir, kontrol et
        args = list(context.args)
        due_date_str = None
        
        # Son argüman tarih gibi görünüyor mu?
        if len(args) > 1:
            last_arg = args[-1]
            if any(char.isdigit() for char in last_arg):
                due_date_str = last_arg
                args = args[:-1]
        
        title = " ".join(args)
        
        try:
            task = self.schedule_manager.add_task(
                user_id=user_id,
                title=title,
                priority="orta",
                due_date_str=due_date_str
            )
            
            date_info = f"📅 Tarih: {format_date(task.due_date)}" if task.due_date else "📅 Tarih yok"
            
            await update.message.reply_text(
                f"✅ Görev eklendi!\n"
                f"📋 {task.title}\n"
                f"{date_info}\n"
                f"🆔 ID: {task.id}"
            )
        except Exception as e:
            logger.error(f"Görev ekleme hatası: {e}")
            await update.message.reply_text("❌ Görev eklenirken bir hata oluştu.")
    
    async def list_tasks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Görevleri listele - /gorevler"""
        user_id = update.effective_user.id
        
        tasks = self.schedule_manager.get_all_tasks(user_id, include_completed=False)
        
        if not tasks:
            await update.message.reply_text("Henüz görev bulunmuyor. /gorev_ekle komutu ile görev ekleyebilirsin.")
            return
        
        formatted_tasks = format_task_list(tasks)
        
        await update.message.reply_text(
            f"📋 *Görevleriniz* ({len(tasks)} adet)\n\n{formatted_tasks}",
            parse_mode='Markdown'
        )
    
    async def today_tasks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bugünkü görevler - /bugun"""
        user_id = update.effective_user.id
        
        tasks = self.schedule_manager.get_today_tasks(user_id)
        
        if not tasks:
            await update.message.reply_text("Bugün için görev bulunmuyor. 🎉")
            return
        
        formatted_tasks = format_task_list(tasks)
        
        await update.message.reply_text(
            f"📅 *Bugünkü Görevler* ({len(tasks)} adet)\n\n{formatted_tasks}",
            parse_mode='Markdown'
        )
    
    async def complete_task_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Görevi tamamla - /gorev_tamamla"""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text(
                "Lütfen görev ID'si girin.\nÖrnek: /gorev_tamamla 3"
            )
            return
        
        try:
            task_id = int(context.args[0])
            success = self.schedule_manager.complete_task(task_id, user_id)
            
            if success:
                await update.message.reply_text(f"✅ Görev tamamlandı! (ID: {task_id}) 🎉")
            else:
                await update.message.reply_text(f"❌ Görev bulunamadı (ID: {task_id})")
        except ValueError:
            await update.message.reply_text("❌ Geçersiz görev ID'si. Lütfen bir sayı girin.")
    
    async def delete_task_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Görev sil - /gorev_sil"""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text(
                "Lütfen görev ID'si girin.\nÖrnek: /gorev_sil 3"
            )
            return
        
        try:
            task_id = int(context.args[0])
            success = self.schedule_manager.delete_task(task_id, user_id)
            
            if success:
                await update.message.reply_text(f"✅ Görev silindi (ID: {task_id})")
            else:
                await update.message.reply_text(f"❌ Görev bulunamadı (ID: {task_id})")
        except ValueError:
            await update.message.reply_text("❌ Geçersiz görev ID'si. Lütfen bir sayı girin.")
    
    async def add_reminder_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Hatırlatıcı ekle - /hatirlatici"""
        user_id = update.effective_user.id
        
        if len(context.args) < 2:
            await update.message.reply_text(
                "Lütfen mesaj ve tarih/saat girin.\n"
                "Örnek: /hatirlatici Fizik sınavı yarın 14:00"
            )
            return
        
        # Son argüman tarih/saat olabilir
        args = list(context.args)
        remind_date_str = args[-1]
        message = " ".join(args[:-1])
        
        from utils.helpers import parse_date
        remind_at = parse_date(remind_date_str)
        
        if not remind_at:
            await update.message.reply_text(
                "❌ Geçersiz tarih formatı. Örnekler: '25.12.2024', 'yarın', 'bugün 14:00'"
            )
            return
        
        try:
            reminder = self.db_manager.add_reminder(
                user_id=user_id,
                message=message,
                remind_at=remind_at
            )
            
            await update.message.reply_text(
                f"⏰ Hatırlatıcı eklendi!\n"
                f"📝 {message}\n"
                f"📅 {format_date(remind_at)}"
            )
        except Exception as e:
            logger.error(f"Hatırlatıcı ekleme hatası: {e}")
            await update.message.reply_text("❌ Hatırlatıcı eklenirken bir hata oluştu.")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inline buton tıklamalarını işle"""
        query = update.callback_query
        await query.answer()
        
        # Callback data'yı işle
        # Gelecekte menüler ve inline butonlar için kullanılabilir
        logger.info(f"Button callback: {query.data}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Normal mesajları akıllıca işle
        - Komut benzeri mesajları tespit et ve yönlendir
        - Diğer mesajları AI'ya gönder
        """
        user_message = update.message.text.strip()
        user_id = update.effective_user.id
        
        # Mesajı küçük harfe çevir kontrol için
        lower_message = user_message.lower()
        
        # Komut benzeri mi kontrol et (önceden derlenmiş pattern'ler ile)
        for trigger_phrase, (command, pattern) in COMMAND_HINTS.items():
            if pattern.search(lower_message):
                await update.message.reply_text(
                    f"💡 Bunu mu demek istediniz?\n\n"
                    f"Komut: `{command}`\n\n"
                    f"Kullanım için /yardim yazabilirsiniz.",
                    parse_mode='Markdown'
                )
                return
        
        # Normal mesaj ise AI'ya gönder
        try:
            # "Yazıyor..." göstergesi
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Varsayılan AI context kullan
            ai_response = self.ai_assistant.chat(user_id, user_message, context=DEFAULT_AI_CONTEXT)
            
            await update.message.reply_text(ai_response)
            
            logger.info(f"Normal mesaj işlendi - User: {user_id}")
            
        except Exception as e:
            logger.error(f"Mesaj işleme hatası: {e}")
            await update.message.reply_text(
                "😔 Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.\n\n"
                "Komutları görmek için: /yardim"
            )
    
    async def send_reminder_notification(self, telegram_id: int, message: str):
        """
        Hatırlatıcı bildirimi gönder
        
        Args:
            telegram_id: Telegram kullanıcı ID'si
            message: Hatırlatıcı mesajı
        """
        try:
            await self.application.bot.send_message(
                chat_id=telegram_id,
                text=f"⏰ *Hatırlatıcı*\n\n{message}",
                parse_mode='Markdown'
            )
            logger.info(f"Hatırlatıcı gönderildi: kullanıcı={telegram_id}")
        except Exception as e:
            logger.error(f"Hatırlatıcı gönderme hatası: {e}")
    
    async def start(self):
        """Bot'u başlat"""
        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("Telegram bot başlatıldı ve polling başladı")
        except Exception as e:
            logger.error(f"Bot başlatma hatası: {e}")
            raise
    
    async def stop(self):
        """Bot'u durdur"""
        try:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Telegram bot durduruldu")
        except Exception as e:
            logger.error(f"Bot durdurma hatası: {e}")
    
    def run(self):
        """Bot'u çalıştır (blocking)"""
        try:
            logger.info("Telegram bot başlatılıyor...")
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.error(f"Bot çalıştırma hatası: {e}")
            raise
