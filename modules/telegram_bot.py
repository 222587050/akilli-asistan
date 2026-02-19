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
        self.application.add_handler(CommandHandler("bugun", self.today_command))
        self.application.add_handler(CommandHandler("gorev_tamamla", self.complete_task_command))
        self.application.add_handler(CommandHandler("gorev_sil", self.delete_task_command))
        self.application.add_handler(CommandHandler("hatirlatici", self.add_reminder_command))

        # AI Öğretmen komutları
        self.application.add_handler(CommandHandler("dersler_yukle", self.load_courses_command))
        self.application.add_handler(CommandHandler("dersler", self.list_courses_command))
        self.application.add_handler(CommandHandler("ders_detay", self.course_detail_command))
        self.application.add_handler(CommandHandler("ogren", self.learn_command))
        self.application.add_handler(CommandHandler("devam", self.continue_command))
        self.application.add_handler(CommandHandler("quiz", self.quiz_command))
        self.application.add_handler(CommandHandler("quiz_sonuc", self.quiz_result_command))
        self.application.add_handler(CommandHandler("ilerleme", self.progress_command))
        self.application.add_handler(CommandHandler("istatistik", self.statistics_command))
        self.application.add_handler(CommandHandler("plan", self.study_plan_command))
        
        # Görüntü yükseltme komutları (eğer özellik aktifse)
        if self.image_upscaler:
            self.application.add_handler(CommandHandler("upscale", self.upscale_command))
            self.application.add_handler(CommandHandler("upscale_yardim", self.upscale_help))
            
            # Photo handler
            self.application.add_handler(
                MessageHandler(filters.PHOTO, self.handle_photo)
            )
            
            logger.info("✅ Görüntü yükseltme komutları kaydedildi")
        
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
/bugun - Bugünkü görevler ve öğrenilecek konular
/gorev_tamamla [id] - Görevi tamamla
/gorev_sil [id] - Görev sil

*Hatırlatıcı:*
/hatirlatici [mesaj] [tarih/saat] - Hatırlatıcı ekle

*🎓 AI Öğretmen:*
/dersler_yukle - 6 dersi yükle
/dersler - Tüm dersleri listele
/ders_detay [ders_adı] - Ders detayları
/ogren [ders] [konu] - AI konu anlatımı
/devam - Kaldığın yerden devam et
/quiz [ders] - Quiz çöz
/quiz_sonuc - Son quiz sonuçları
/ilerleme - Genel ilerleme raporu
/istatistik - Detaylı istatistikler
/plan - 14 haftalık çalışma planı
"""

        # Görüntü yükseltme komutları ekle (eğer özellik aktifse)
        if self.image_upscaler:
            help_text += """
*🎨 Görüntü Yükseltme:*
/upscale - Fotoğraf kalitesini artır (4x)
/upscale_yardim - Detaylı bilgi
"""

        help_text += """
*Diğer:*
/start - Bot'u başlat
/yardim - Bu yardım mesajı

*Örnekler:*
`/not_ekle Matematik Pisagor teoremi: a² + b² = c²`
`/gorev_ekle Fizik ödevi yap 25.12.2024`
`/ogren Yapay_Zeka gradient_descent`
`/quiz Yapay_Zeka`
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
    
    async def today_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bugünkü görevler ve öğrenilecek konular - /bugun"""
        user_id = update.effective_user.id

        message_parts = []

        # Bugünkü görevler
        tasks = self.schedule_manager.get_today_tasks(user_id)
        if tasks:
            formatted_tasks = format_task_list(tasks)
            message_parts.append(f"📅 *Bugünkü Görevler* ({len(tasks)} adet)\n\n{formatted_tasks}")
        else:
            message_parts.append("📅 *Bugünkü Görevler*\nBugün için görev bulunmuyor. 🎉")

        # Sıradaki öğrenilecek konular
        next_topics = self.db_manager.get_next_topics(user_id, limit=3)
        if next_topics:
            topics_text = "📚 *Sıradaki Konular*\n"
            for i, t in enumerate(next_topics, 1):
                topics_text += f"{i}. {t['course_name']}: {t['topic_title']}\n"
            topics_text += "\n💡 /ogren [ders] [konu] ile öğrenmeye başla!"
            message_parts.append(topics_text)

        await update.message.reply_text(
            "\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n".join(message_parts),
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
    
    # ============ AI ÖĞRETMEN KOMUTLARI ============

    # Önceden tanımlı 6 ders
    PREDEFINED_COURSES = [
        {
            "name": "Ön Yüz Programlama",
            "description": "HTML, CSS, JavaScript, React ile modern web uygulamaları",
            "topics": [
                "HTML5 Temelleri",
                "CSS3 ve Responsive Tasarım",
                "JavaScript Temelleri",
                "DOM Manipülasyonu",
                "Fetch API ve AJAX",
                "React'a Giriş",
                "React Hooks",
                "State Management",
                "Routing",
                "Proje: Portföy Sitesi",
            ],
        },
        {
            "name": "İleri Programlama",
            "description": "Python/C++, OOP, Veri Yapıları ve Algoritmalar",
            "topics": [
                "OOP Temelleri",
                "Sınıflar ve Nesneler",
                "Kalıtım (Inheritance)",
                "Polimorfizm",
                "Veri Yapıları: Liste, Stack, Queue",
                "Ağaç Yapıları",
                "Arama Algoritmaları",
                "Sıralama Algoritmaları",
                "Recursion",
                "Proje: Veri Yapısı Kütüphanesi",
            ],
        },
        {
            "name": "Bilgisayar Destekli Çizim",
            "description": "Autodesk Inventor ile 3D modelleme ve teknik resim",
            "topics": [
                "Inventor Arayüzü",
                "2D Sketch Araçları",
                "3D Modelleme: Extrude, Revolve",
                "Fillet ve Chamfer",
                "Assembly Tasarımı",
                "Constraint'ler",
                "Teknik Resim",
                "BOM (Malzeme Listesi)",
                "Render ve Sunum",
                "Proje: Mekanik Parça Montajı",
            ],
        },
        {
            "name": "Sayısal Tasarım",
            "description": "Dijital mantık, sayı sistemleri, mantık devreleri",
            "topics": [
                "Sayı Sistemleri (Binary, Hex)",
                "Boolean Cebir",
                "Mantık Kapıları",
                "Karnaugh Map",
                "Kombine Devreler",
                "Flip-Floplar",
                "Sayıcılar ve Registerlar",
                "FSM (Finite State Machine)",
                "VHDL/Verilog Giriş",
                "Proje: Dijital Saat Devresi",
            ],
        },
        {
            "name": "Yapay Zeka Uygulamaları",
            "description": "Machine Learning, Deep Learning, Computer Vision, NLP",
            "topics": [
                "AI'ya Giriş",
                "Machine Learning Temelleri",
                "Supervised Learning",
                "Neural Networks",
                "Gradient Descent",
                "CNN ve Computer Vision",
                "RNN ve NLP",
                "Transfer Learning",
                "Model Evaluation",
                "Proje: Görüntü Sınıflandırma",
            ],
        },
        {
            "name": "Sensörler ve Transdüserler",
            "description": "Arduino, IoT sensörleri, veri toplama",
            "topics": [
                "Sensör Temelleri",
                "Arduino'ya Giriş",
                "Sıcaklık Sensörleri",
                "Basınç Sensörleri",
                "Ultrasonik Sensörler",
                "Kızılötesi Sensörler",
                "Sensör Entegrasyonu",
                "IoT Projeleri",
                "Veri Görselleştirme",
                "Proje: IoT Hava İstasyonu",
            ],
        },
    ]

    async def load_courses_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Önceden tanımlı dersleri yükle - /dersler_yukle"""
        user = update.effective_user

        db_user = self.db_manager.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )

        await update.message.reply_text("⏳ Dersler yükleniyor...")

        try:
            for course_data in self.PREDEFINED_COURSES:
                course_id = self.db_manager.add_course(
                    db_user.id, course_data["name"], course_data["description"]
                )
                for week, topic_title in enumerate(course_data["topics"], 1):
                    self.db_manager.add_topic(course_id, topic_title, week)

            await update.message.reply_text(
                "✅ 6 ders yüklendi!\n\n"
                "📚 Dersler:\n"
                "1. Ön Yüz Programlama\n"
                "2. İleri Programlama\n"
                "3. Bilgisayar Destekli Çizim\n"
                "4. Sayısal Tasarım\n"
                "5. Yapay Zeka Uygulamaları\n"
                "6. Sensörler ve Transdüserler\n\n"
                "💡 /bugun ile bugün ne öğreneceğini gör!\n"
                "📊 /ilerleme ile durumunu kontrol et!"
            )
        except Exception as e:
            logger.error(f"Ders yükleme hatası: {e}")
            await update.message.reply_text("❌ Dersler yüklenirken bir hata oluştu.")

    async def list_courses_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Tüm dersleri listele - /dersler"""
        user = update.effective_user
        db_user = self.db_manager.get_or_create_user(telegram_id=user.id)

        courses = self.db_manager.get_user_courses(db_user.id)

        if not courses:
            await update.message.reply_text(
                "Henüz ders yüklenmemiş. /dersler_yukle komutu ile 6 dersi yükleyebilirsin."
            )
            return

        message = "📚 *Derslerim*\n\n"
        for i, c in enumerate(courses, 1):
            total = c['total_topics']
            completed = c['completed_topics']
            pct = int((completed / total) * 100) if total > 0 else 0
            bar = '█' * (pct // 10) + '░' * (10 - pct // 10)
            message += f"{i}. *{c['name']}*\n"
            message += f"   {bar} {pct}% ({completed}/{total} konu)\n\n"

        message += "💡 /ders_detay [ders_adı] ile detayları görebilirsin."
        await update.message.reply_text(message, parse_mode='Markdown')

    async def course_detail_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ders detaylarını göster - /ders_detay"""
        user = update.effective_user
        db_user = self.db_manager.get_or_create_user(telegram_id=user.id)

        if not context.args:
            await update.message.reply_text(
                "❌ Kullanım: /ders_detay [ders_adı]\n\n"
                "Örnek: /ders_detay Yapay_Zeka"
            )
            return

        course_name = " ".join(context.args).replace("_", " ")
        courses = self.db_manager.get_user_courses(db_user.id)
        course = next(
            (c for c in courses if course_name.lower() in c['name'].lower()),
            None
        )

        if not course:
            await update.message.reply_text(f"❌ '{course_name}' dersi bulunamadı. /dersler ile dersleri görebilirsin.")
            return

        topics = self.db_manager.get_course_topics(course['id'])
        message = f"📚 *{course['name']}*\n"
        message += f"📝 {course['description']}\n\n"
        message += f"İlerleme: {course['completed_topics']}/{course['total_topics']} konu\n\n"
        message += "📋 *Konular:*\n"

        for t in topics:
            status = "✅" if t['is_completed'] else "⬜"
            message += f"{status} Hafta {t['week_number']}: {t['title']}\n"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def learn_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """AI ile konu öğren - /ogren"""
        user = update.effective_user

        if not self.ai_teacher or not self.ai_teacher.is_available():
            await update.message.reply_text(
                "❌ AI öğretmen şu anda kullanılamıyor. GEMINI_API_KEY kontrol edin."
            )
            return

        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Kullanım: /ogren [ders] [konu]\n\n"
                "Örnek: /ogren Yapay_Zeka gradient_descent"
            )
            return

        course = context.args[0].replace("_", " ")
        topic = " ".join(context.args[1:]).replace("_", " ")

        await update.message.reply_text(f"🔍 {course} - {topic} anlatılıyor...\n⏳ Lütfen bekleyin...")

        try:
            explanation = await self.ai_teacher.explain_topic(course, topic)

            message = f"🎓 *{course.upper()}*\n"
            message += f"📖 Konu: {topic}\n\n"
            message += "━━━━━━━━━━━━━━━━━━━━━━\n"
            message += "📚 *KONU ANLATIMI*\n"
            message += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            message += explanation['explanation'] + "\n\n"

            if explanation.get('code_example') and explanation['code_example'].lower() != 'kod örneği yok.':
                message += "━━━━━━━━━━━━━━━━━━━━━━\n"
                message += "💻 *KOD ÖRNEĞİ*\n"
                message += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                message += f"```\n{explanation['code_example']}\n```\n\n"

            if explanation.get('key_points'):
                message += "━━━━━━━━━━━━━━━━━━━━━━\n"
                message += "🎯 *ÖNEMLİ NOKTALAR*\n"
                message += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                message += "\n".join(f"• {p}" for p in explanation['key_points']) + "\n\n"

            if explanation.get('practical_tip'):
                message += f"💡 *Pratik İpucu:* {explanation['practical_tip']}\n\n"

            course_arg = course.replace(' ', '_')
            topic_arg = topic.replace(' ', '_')
            message += "━━━━━━━━━━━━━━━━━━━━━━\n"
            message += f"✅ Quiz: /quiz {course_arg}\n"
            message += f"🔄 Devam: /devam"

            # Telegram mesaj boyutu limiti (4096 karakter)
            if len(message) > 4096:
                message = message[:4090] + "..."

            await update.message.reply_text(message, parse_mode='Markdown')

            # İlerlemeyi kaydet
            db_user = self.db_manager.get_or_create_user(telegram_id=user.id)
            self.db_manager.mark_topic_completed(db_user.id, course, topic)

        except Exception as e:
            logger.error(f"Konu öğrenme hatası: {e}")
            await update.message.reply_text("❌ Konu anlatımı sırasında bir hata oluştu. Lütfen tekrar deneyin.")

    async def continue_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Kaldığın yerden devam et - /devam"""
        user = update.effective_user
        db_user = self.db_manager.get_or_create_user(telegram_id=user.id)

        next_topic = self.db_manager.get_next_topic(db_user.id)

        if not next_topic:
            await update.message.reply_text(
                "🎉 Tebrikler! Tüm konuları tamamladın!\n\n"
                "📊 /ilerleme ile istatistiklerini görebilirsin."
            )
            return

        course_arg = next_topic['course_name'].replace(' ', '_')
        topic_arg = next_topic['topic_title'].replace(' ', '_')

        await update.message.reply_text(
            f"📚 Sıradaki konun:\n\n"
            f"🏫 Ders: *{next_topic['course_name']}*\n"
            f"📖 Konu: *{next_topic['topic_title']}*\n"
            f"📅 Hafta: {next_topic['week_number']}\n\n"
            f"▶️ Öğrenmek için:\n"
            f"`/ogren {course_arg} {topic_arg}`",
            parse_mode='Markdown'
        )

    async def quiz_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Quiz çöz - /quiz"""
        user = update.effective_user

        if not self.ai_teacher or not self.ai_teacher.is_available():
            await update.message.reply_text(
                "❌ AI öğretmen şu anda kullanılamıyor. GEMINI_API_KEY kontrol edin."
            )
            return

        if not context.args:
            await update.message.reply_text(
                "❌ Kullanım: /quiz [ders]\n\n"
                "Örnek: /quiz Yapay_Zeka"
            )
            return

        course_name = " ".join(context.args).replace("_", " ")
        db_user = self.db_manager.get_or_create_user(telegram_id=user.id)
        courses = self.db_manager.get_user_courses(db_user.id)
        course = next(
            (c for c in courses if course_name.lower() in c['name'].lower()),
            None
        )

        if not course:
            await update.message.reply_text(
                f"❌ '{course_name}' dersi bulunamadı. /dersler ile dersleri görebilirsin."
            )
            return

        # Tamamlanmış konulardan quiz yap, yoksa ilk konudan yap
        topics = self.db_manager.get_course_topics(course['id'])
        completed_topics = [t for t in topics if t['is_completed']]
        quiz_topic = completed_topics[-1] if completed_topics else (topics[0] if topics else None)

        if not quiz_topic:
            await update.message.reply_text("❌ Bu ders için konu bulunamadı.")
            return

        await update.message.reply_text(
            f"🎯 *{course['name']}* - Quiz\n"
            f"📖 Konu: {quiz_topic['title']}\n\n"
            "⏳ Sorular hazırlanıyor...",
            parse_mode='Markdown'
        )

        try:
            questions = await self.ai_teacher.generate_quiz(course['name'], quiz_topic['title'])

            if not questions:
                await update.message.reply_text("❌ Quiz soruları oluşturulamadı. Lütfen tekrar deneyin.")
                return

            # Quiz state'ini kaydet
            context.user_data['active_quiz'] = {
                'questions': questions,
                'current_index': 0,
                'score': 0,
                'course_name': course['name'],
                'topic_title': quiz_topic['title'],
                'topic_id': quiz_topic['id'],
                'user_db_id': db_user.id,
            }

            # İlk soruyu gönder
            await self._send_quiz_question(update, context)

        except Exception as e:
            logger.error(f"Quiz başlatma hatası: {e}")
            await update.message.reply_text("❌ Quiz başlatılırken hata oluştu.")

    async def _send_quiz_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Quiz sorusunu gönder"""
        quiz = context.user_data.get('active_quiz')
        if not quiz:
            return

        idx = quiz['current_index']
        questions = quiz['questions']

        if idx >= len(questions):
            await self._finish_quiz(update, context)
            return

        q = questions[idx]
        total = len(questions)

        keyboard = []
        for opt in q['options']:
            letter = opt[0]  # "A", "B", "C", "D"
            keyboard.append([InlineKeyboardButton(opt, callback_data=f"quiz_{letter}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❓ *Soru {idx + 1}/{total}*\n\n{q['question']}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _finish_quiz(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Quiz'i bitir ve sonuçları göster"""
        quiz = context.user_data.pop('active_quiz', {})
        score = quiz.get('score', 0)
        total = len(quiz.get('questions', []))
        pct = int((score / total) * 100) if total > 0 else 0

        if pct >= 80:
            emoji = "🏆"
            msg = "Mükemmel!"
        elif pct >= 60:
            emoji = "👍"
            msg = "İyi iş!"
        else:
            emoji = "📚"
            msg = "Daha fazla çalış!"

        result_text = (
            f"{emoji} *Quiz Tamamlandı!* {msg}\n\n"
            f"📊 Sonuç: {score}/{total} doğru ({pct}%)\n"
            f"🏫 Ders: {quiz.get('course_name', '')}\n"
            f"📖 Konu: {quiz.get('topic_title', '')}"
        )

        # Sonucu veritabanına kaydet
        try:
            self.db_manager.add_quiz_result(
                quiz.get('user_db_id'),
                quiz.get('topic_id'),
                score,
                total
            )
        except Exception as e:
            logger.error(f"Quiz sonucu kaydetme hatası: {e}")

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=result_text,
            parse_mode='Markdown'
        )

    async def quiz_result_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Son quiz sonuçları - /quiz_sonuc"""
        user = update.effective_user
        db_user = self.db_manager.get_or_create_user(telegram_id=user.id)

        results = self.db_manager.get_last_quiz_results(db_user.id, limit=5)

        if not results:
            await update.message.reply_text(
                "Henüz quiz çözülmemiş. /quiz [ders] komutu ile quiz çözebilirsin."
            )
            return

        message = "📊 *Son Quiz Sonuçları*\n\n"
        for r in results:
            pct = int((r['score'] / r['total_questions']) * 100) if r['total_questions'] > 0 else 0
            emoji = "🏆" if pct >= 80 else ("👍" if pct >= 60 else "📚")
            message += (
                f"{emoji} {r['topic_title']}\n"
                f"   {r['score']}/{r['total_questions']} ({pct}%)\n\n"
            )

        await update.message.reply_text(message, parse_mode='Markdown')

    async def progress_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """İlerleme raporu göster - /ilerleme"""
        user = update.effective_user
        db_user = self.db_manager.get_or_create_user(telegram_id=user.id)

        courses = self.db_manager.get_user_courses(db_user.id)

        if not courses:
            await update.message.reply_text(
                "Henüz ders yüklenmemiş. /dersler_yukle komutu ile başlayabilirsin."
            )
            return

        message = "📊 *DERS İLERLEME RAPORU*\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

        total_progress = 0

        for c in courses:
            total = c['total_topics']
            completed = c['completed_topics']
            pct = (completed / total) * 100 if total > 0 else 0
            total_progress += pct

            bar = '█' * int(pct / 10) + '░' * (10 - int(pct / 10))
            message += f"📚 *{c['name']}*: {bar} {pct:.0f}%\n"
            message += f"• Tamamlanan: {completed}/{total} konu\n"

            avg_score = self.db_manager.get_avg_quiz_score(db_user.id, c['id'])
            if avg_score is not None:
                message += f"• Quiz ortalaması: {avg_score:.0f}%\n"

            message += "\n"

        avg_total = total_progress / len(courses)
        streak = self.db_manager.get_streak(db_user.id)
        total_quizzes = self.db_manager.get_total_quizzes(db_user.id)

        message += "━━━━━━━━━━━━━━━━━━━━━━\n"
        message += f"📈 Genel İlerleme: {avg_total:.0f}%\n"
        message += f"🔥 Çalışma Streak: {streak} gün\n"
        message += f"✅ Toplam Quiz: {total_quizzes}"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def statistics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Detaylı istatistikler - /istatistik"""
        user = update.effective_user
        db_user = self.db_manager.get_or_create_user(telegram_id=user.id)

        courses = self.db_manager.get_user_courses(db_user.id)
        total_topics = sum(c['total_topics'] for c in courses)
        completed_topics = sum(c['completed_topics'] for c in courses)
        total_quizzes = self.db_manager.get_total_quizzes(db_user.id)
        streak = self.db_manager.get_streak(db_user.id)

        message = "📈 *DETAYLI İSTATİSTİKLER*\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        message += f"🏫 Toplam Ders: {len(courses)}\n"
        message += f"📖 Toplam Konu: {total_topics}\n"
        message += f"✅ Tamamlanan Konu: {completed_topics}\n"
        message += f"⬜ Kalan Konu: {total_topics - completed_topics}\n"
        message += f"🎯 Quiz Sayısı: {total_quizzes}\n"
        message += f"🔥 Streak: {streak} gün\n\n"

        if total_topics > 0:
            pct = int((completed_topics / total_topics) * 100)
            bar = '█' * (pct // 10) + '░' * (10 - pct // 10)
            message += f"Genel İlerleme:\n{bar} {pct}%"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def study_plan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """14 haftalık çalışma planı - /plan"""
        user = update.effective_user
        db_user = self.db_manager.get_or_create_user(telegram_id=user.id)

        courses = self.db_manager.get_user_courses(db_user.id)

        if not courses:
            await update.message.reply_text(
                "Henüz ders yüklenmemiş. /dersler_yukle komutu ile başlayabilirsin."
            )
            return

        message = "📅 *14 HAFTALIK ÇALIŞMA PLANI*\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

        for week in range(1, 15):
            message += f"📆 *Hafta {week}:*\n"
            for c in courses:
                topics = self.db_manager.get_course_topics(c['id'])
                week_topics = [t for t in topics if t['week_number'] == week]
                for t in week_topics:
                    status = "✅" if t['is_completed'] else "⬜"
                    message += f"  {status} {c['name']}: {t['title']}\n"
            message += "\n"

        # Telegram mesaj boyutu limiti
        if len(message) > 4096:
            message = message[:4090] + "..."

        await update.message.reply_text(message, parse_mode='Markdown')

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inline buton tıklamalarını işle"""
        query = update.callback_query
        await query.answer()

        # Quiz cevabı
        if query.data.startswith("quiz_"):
            await self._handle_quiz_answer(update, context, query.data)
            return

        # Callback data'yı işle
        # Gelecekte menüler ve inline butonlar için kullanılabilir
        logger.info(f"Button callback: {query.data}")

    async def _handle_quiz_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Quiz cevabını işle"""
        query = update.callback_query
        quiz = context.user_data.get('active_quiz')

        if not quiz:
            await query.edit_message_text("❌ Aktif quiz bulunamadı. /quiz komutu ile yeni quiz başlatabilirsin.")
            return

        selected = callback_data.replace("quiz_", "")  # "A", "B", "C", "D"
        idx = quiz['current_index']
        q = quiz['questions'][idx]
        correct = q['correct']
        explanation = q.get('explanation', '')

        if selected == correct:
            quiz['score'] += 1
            result_text = f"✅ *Doğru!*\n\n{explanation}"
        else:
            result_text = f"❌ *Yanlış!* Doğru cevap: *{correct}*\n\n{explanation}"

        await query.edit_message_text(result_text, parse_mode='Markdown')

        # Sonraki soruya geç
        quiz['current_index'] += 1
        context.user_data['active_quiz'] = quiz

        if quiz['current_index'] >= len(quiz['questions']):
            await self._finish_quiz(update, context)
        else:
            await self._send_quiz_question(update, context)
    
    async def handle_message(self, update: Update, bot_context: ContextTypes.DEFAULT_TYPE):
        """
        Normal mesajları akıllıca işle
        - Komut benzeri mesajları tespit et ve yönlendir
        - Diğer mesajları AI'ya gönder
        """
        user_message = update.message.text.strip()
        user_id = update.effective_user.id
        
        # Komut benzeri anahtar kelimeler
        command_hints = {
            'not ekle': '/not_ekle',
            'not sil': '/not_sil',
            'notlarım': '/notlar',
            'notları göster': '/notlar',
            'not ara': '/not_ara',
            'görev ekle': '/gorev_ekle',
            'görev sil': '/gorev_sil',
            'görevlerim': '/gorevler',
            'görevleri göster': '/gorevler',
            'bugünkü görevler': '/bugun',
            'görev tamamla': '/gorev_tamamla',
            'hatırlatıcı': '/hatirlatici',
            'hatırlatıcı ekle': '/hatirlatici',
            'yardım': '/yardim',
            'komutlar': '/yardim',
        }
        
        # Mesajı küçük harfe çevir kontrol için
        lower_message = user_message.lower()
        
        # Komut benzeri mi kontrol et
        for hint, command in command_hints.items():
            if hint in lower_message:
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
            await bot_context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            ai_response = self.ai_assistant.simple_chat(
                user_message, 
                context=self.MESSAGE_HANDLER_CONTEXT
            )
            
            await update.message.reply_text(ai_response)
            
            logger.info(f"Normal mesaj işlendi - User: {user_id}")
            
        except Exception as e:
            logger.error(f"Mesaj işleme hatası: {e}")
            await update.message.reply_text(
                "😔 Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.\n\n"
                "Komutları görmek için: /yardim"
            )
    
    async def upscale_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Görüntü yükseltme komutu"""
        if not self.image_upscaler:
            await update.message.reply_text(
                "❌ Görüntü yükseltme özelliği şu anda kullanılamıyor.\n"
                "Lütfen daha sonra tekrar deneyin."
            )
            return
        
        user_id = update.effective_user.id
        
        # Kullanıcıya talimat ver
        await update.message.reply_text(
            "📸 Lütfen kalitesini artırmak istediğiniz fotoğrafı gönderin.\n\n"
            "✨ Çözünürlük 4x artırılacak!\n"
            "⏱️ İşlem 10-15 saniye sürer."
        )
        
        # Kullanıcı state'ini ayarla
        context.user_data['waiting_for_upscale_photo'] = True
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Fotoğraf mesajlarını işle"""
        user_id = update.effective_user.id
        
        # Upscale bekleniyor mu?
        if context.user_data.get('waiting_for_upscale_photo'):
            await self.process_upscale_photo(update, context)
            context.user_data['waiting_for_upscale_photo'] = False
            return
        
        # Genel fotoğraf analizi
        if self.image_upscaler:
            await update.message.reply_text(
                "📸 Fotoğraf aldım!\n\n"
                "Ne yapmak istersiniz?\n"
                "/upscale - Kaliteyi artır (4x)"
            )
        else:
            await update.message.reply_text(
                "📸 Fotoğraf aldım! Ancak görüntü işleme özellikleri şu anda kullanılamıyor."
            )
    
    async def process_upscale_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Upscale işlemini gerçekleştir"""
        user_id = update.effective_user.id
        
        try:
            # İlerleme mesajı
            progress_msg = await update.message.reply_text(
                "🔄 İşleniyor...\n"
                "⏱️ Bu 10-15 saniye sürebilir, lütfen bekleyin."
            )
            
            # En yüksek çözünürlüklü fotoğrafı al
            photo = update.message.photo[-1]
            photo_file = await photo.get_file()
            
            # Görüntü bilgilerini göster
            file_size_mb = photo_file.file_size / (1024 * 1024)
            await progress_msg.edit_text(
                f"📸 Fotoğraf bilgileri:\n"
                f"📊 Boyut: {photo.width}x{photo.height}\n"
                f"💾 Dosya: {file_size_mb:.2f} MB\n\n"
                f"🚀 4x yükseltiliyor... (Replicate AI)\n"
                f"⏱️ 10-15 saniye sürebilir"
            )
            
            # Fotoğrafı indir
            input_path = await self.image_handler.download_photo(photo_file, user_id)
            
            # Upscale işlemi
            output_url = self.image_upscaler.upscale_image(input_path)
            
            if not output_url:
                await progress_msg.edit_text(
                    "❌ Üzgünüm, görüntü işlenemedi.\n"
                    "Lütfen farklı bir fotoğraf deneyin."
                )
                self.image_handler.cleanup_file(input_path)
                return
            
            # Yükseltilmiş görüntüyü indir
            output_path = input_path.replace('.jpg', '_upscaled.jpg')
            success = self.image_upscaler.download_image(output_url, output_path)
            
            if not success:
                await progress_msg.edit_text("❌ Görüntü indirilemedi.")
                self.image_handler.cleanup_file(input_path)
                return
            
            # Sonuç bilgileri - PIL ile görüntü boyutlarını al
            if Image:
                try:
                    with Image.open(output_path) as img:
                        new_width, new_height = img.size
                    dimensions_info = f"📊 Sonrası: {new_width}x{new_height}\n"
                except Exception as e:
                    logger.warning(f"PIL ile boyut alınamadı: {e}")
                    dimensions_info = ""
            else:
                dimensions_info = ""
            
            # Yükseltilmiş fotoğrafı gönder
            with open(output_path, 'rb') as photo_file:
                caption = (
                    f"✨ Görüntü yükseltildi! (Replicate AI)\n\n"
                    f"📊 Öncesi: {photo.width}x{photo.height}\n"
                    f"{dimensions_info}"
                    f"🎨 Kalite artışı: ~4x\n\n"
                    f"💡 Başka bir fotoğraf için /upscale yazın.\n"
                    f"🏆 Powered by Real-ESRGAN"
                )
                
                await update.message.reply_photo(
                    photo=photo_file,
                    caption=caption
                )
            
            # İlerleme mesajını sil
            await progress_msg.delete()
            
            # Geçici dosyaları temizle
            self.image_handler.cleanup_file(input_path)
            self.image_handler.cleanup_file(output_path)
            
            logger.info(f"Upscale tamamlandı - User: {user_id}")
            
        except Exception as e:
            logger.error(f"Upscale hatası: {e}")
            await update.message.reply_text(
                "😔 Bir hata oluştu. Lütfen tekrar deneyin.\n\n"
                "İpuçları:\n"
                "- Fotoğraf 10MB'dan küçük olmalı\n"
                "- JPG veya PNG formatında olmalı"
            )
    
    async def upscale_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Upscale yardım komutu"""
        help_text = """
🎨 *Görüntü Yükseltme Sistemi* (Replicate AI)

📸 *Komutlar:*
/upscale - Fotoğraf kalitesini artır (4x!)
/upscale_yardim - Bu yardım mesajı

✨ *Nasıl Kullanılır:*
1. /upscale komutunu yazın
2. Fotoğrafınızı gönderin
3. 10-15 saniye bekleyin
4. Süper kaliteli fotoğrafı alın!

📊 *Özellikler:*
- 🚀 *4x çözünürlük artırma* (800x600 → 3200x2400!)
- ✨ Gelişmiş AI (Real-ESRGAN)
- 🎨 Netlik iyileştirme
- 🌈 Renk canlandırma
- 🔇 Gürültü azaltma

⚠️ *Limitler:*
- Max dosya boyutu: 10 MB
- Aylık limit: 500 fotoğraf (ücretsiz!)
- Format: JPG, PNG, WebP

💡 *İpuçları:*
- İyi aydınlatmalı fotoğraflar en iyi sonucu verir
- Küçük fotoğrafları 4x büyütür (800x600 → 3200x2400)
- İşlem 10-15 saniye sürer

🏆 *Powered by Replicate AI*
"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
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
