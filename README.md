# 🤖 Akıllı Kişisel Asistan

Google Gemini Pro AI destekli Türkçe kişisel asistan. Ders yardımı, not yönetimi, görev takibi ve hatırlatıcı özellikleri içerir.

## ✨ Özellikler

### 🎓 AI Ders Asistanı (Gemini Pro)
- Ders sorularına detaylı yanıtlar
- Not özetleme ve açıklama
- Konu anlatımı (basit, orta, detaylı seviyeler)
- Çalışma planı oluşturma
- Bağlam tabanlı sohbet geçmişi

### 📝 Not Yönetimi
- Kategorilere göre not alma (Matematik, Fizik, vb.)
- Not listeleme ve arama
- Tam metin araması
- Tarih/zaman damgası ile kayıt

### 📅 Görev ve Ajanda Sistemi
- Görev ekleme, güncelleme, silme
- Öncelik seviyeleri (düşük, orta, yüksek)
- Tarih/saat bazlı takip
- Bugünkü görevleri listeleme
- Tamamlanma durumu takibi

### ⏰ Hatırlatıcı Sistemi
- APScheduler ile zamanlanmış hatırlatıcılar
- Ödev/sınav hatırlatmaları
- Telegram üzerinden otomatik bildirim
- Tekrarlanan hatırlatıcı desteği

### 💬 Telegram Bot Arayüzü
Kullanıcı dostu komutlarla tüm özelliklere erişim:
- `/start` - Bot'u başlat
- `/sohbet [mesaj]` - AI ile sohbet
- `/not_ekle [kategori] [not]` - Not ekle
- `/notlar` - Notları listele
- `/not_ara [kelime]` - Not ara
- `/gorev_ekle [görev] [tarih]` - Görev ekle
- `/gorevler` - Görevleri listele
- `/bugun` - Bugünkü görevler
- `/hatirlatici [mesaj] [tarih]` - Hatırlatıcı ekle
- `/yardim` - Tüm komutları göster

## 📋 Gereksinimler

- Python 3.8 veya üzeri
- Google Gemini API Key
- Telegram Bot Token
- İnternet bağlantısı

## 🚀 Kurulum

### 1. Repository'yi Klonlayın

```bash
git clone https://github.com/222587050/akilli-asistan.git
cd akilli-asistan
```

### 2. Virtual Environment Oluşturun

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

### 4. API Anahtarlarını Ayarlayın

`.env.example` dosyasını `.env` olarak kopyalayın:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

`.env` dosyasını düzenleyin ve API anahtarlarınızı ekleyin:

```env
GEMINI_API_KEY=your_gemini_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

#### Google Gemini API Key Alma

1. [Google AI Studio](https://makersuite.google.com/app/apikey) sayfasına gidin
2. Google hesabınızla giriş yapın
3. "Create API Key" butonuna tıklayın
4. Oluşturulan API key'i kopyalayın
5. `.env` dosyasındaki `GEMINI_API_KEY` değerine yapıştırın

#### Telegram Bot Token Alma

1. Telegram'da [@BotFather](https://t.me/botfather) botunu açın
2. `/newbot` komutunu gönderin
3. Bot için bir isim seçin (örn: "Benim Asistanım")
4. Bot için bir kullanıcı adı seçin (örn: "benim_asistan_bot")
5. BotFather size bir token verecek
6. Token'ı kopyalayın ve `.env` dosyasındaki `TELEGRAM_BOT_TOKEN` değerine yapıştırın

### 5. Uygulamayı Başlatın

```bash
python main.py
```

Bot çalışmaya başladığında, Telegram'da botunuzu bulun ve `/start` komutu ile başlayın!

## 📖 Kullanım Örnekleri

### AI ile Sohbet

```
/sohbet Kuantum fiziği nedir?
/sohbet Pisagor teoremini açıkla
/sohbet Python'da liste comprehension nasıl kullanılır?
```

### Not İşlemleri

```
/not_ekle Matematik Pisagor teoremi: a² + b² = c²
/not_ekle Fizik Newton'un ikinci yasası: F = m × a
/not_ekle Kimya Su molekülü: H₂O
/notlar
/not_ara Pisagor
/not_sil 5
```

### Görev İşlemleri

```
/gorev_ekle Matematik ödevi yap 25.12.2024
/gorev_ekle Fizik sınavına çalış yarın
/gorevler
/bugun
/gorev_tamamla 3
/gorev_sil 5
```

### Hatırlatıcılar

```
/hatirlatici Fizik sınavı yarın
/hatirlatici Ödev teslimi 25.12.2024 14:00
/hatirlatici Randevu bugün 15:30
```

## 🗂️ Proje Yapısı

```
akilli-asistan/
├── README.md                  # Bu dosya
├── requirements.txt           # Python bağımlılıkları
├── .env.example              # API key şablonu
├── .gitignore                # Git ignore kuralları
├── config.py                 # Yapılandırma ayarları
├── main.py                   # Ana uygulama
├── modules/
│   ├── __init__.py
│   ├── ai_assistant.py       # Google Gemini Pro entegrasyonu
│   ├── notes_manager.py      # Not yönetim sistemi
│   ├── schedule_manager.py   # Görev yönetimi
│   ├── telegram_bot.py       # Telegram bot arayüzü
│   └── whatsapp_bot.py       # WhatsApp placeholder
├── database/
│   ├── __init__.py
│   ├── db_manager.py         # Veritabanı işlemleri
│   └── models.py             # SQLAlchemy modelleri
├── utils/
│   ├── __init__.py
│   ├── helpers.py            # Yardımcı fonksiyonlar
│   └── reminders.py          # Hatırlatıcı zamanlayıcı
├── data/
│   └── assistant.db          # SQLite veritabanı (otomatik oluşur)
└── logs/
    └── assistant.log         # Log dosyası (otomatik oluşur)
```

## 🗄️ Veritabanı

Proje SQLite veritabanı kullanır ve aşağıdaki tabloları içerir:

- **users** - Kullanıcı bilgileri
- **notes** - Notlar (kategori, içerik, tarih)
- **tasks** - Görevler (başlık, öncelik, tarih, durum)
- **reminders** - Hatırlatıcılar (mesaj, tarih, tekrar)
- **chat_history** - AI sohbet geçmişi

Veritabanı ilk çalıştırmada otomatik olarak oluşturulur.

## 🔧 Yapılandırma

`config.py` dosyasında aşağıdaki ayarları değiştirebilirsiniz:

- **TIMEZONE** - Zaman dilimi (varsayılan: Europe/Istanbul)
- **LOG_LEVEL** - Log seviyesi (DEBUG, INFO, WARNING, ERROR)
- **MAX_CHAT_HISTORY** - Maksimum sohbet geçmişi (varsayılan: 50)
- **CONTEXT_WINDOW** - AI'ya gönderilecek son mesaj sayısı (varsayılan: 10)
- **GEMINI_TEMPERATURE** - AI yanıt çeşitliliği (0.0-1.0, varsayılan: 0.7)

## 🐛 Sorun Giderme

### Bot çalışmıyor

- `.env` dosyasının doğru oluşturulduğundan emin olun
- API anahtarlarının doğru girildiğinden emin olun
- İnternet bağlantınızı kontrol edin
- Log dosyasını (`logs/assistant.log`) kontrol edin

### AI yanıt vermiyor

- `GEMINI_API_KEY` değerinin doğru olduğundan emin olun
- [Google AI Studio](https://makersuite.google.com/) hesabınızın aktif olduğunu kontrol edin
- API limitinizi aşmadığınızdan emin olun

### Telegram bot'a erişemiyorum

- `TELEGRAM_BOT_TOKEN` değerinin doğru olduğundan emin olun
- BotFather'dan aldığınız token'ı kontrol edin
- Bot'un çalıştığından emin olun (`python main.py`)

### Veritabanı hatası

- `data` klasörünün var olduğundan emin olun
- Klasör yazma izinlerini kontrol edin
- SQLite yüklü olduğundan emin olun

### Hatırlatıcılar gelmiyor

- Bot'un çalışır durumda olduğundan emin olun
- Tarih formatının doğru olduğundan emin olun
- Timezone ayarlarını kontrol edin

## 📦 Bağımlılıklar

- `python-telegram-bot>=20.0` - Telegram bot API
- `google-generativeai>=0.3.0` - Google Gemini AI
- `sqlalchemy>=2.0.0` - Veritabanı ORM
- `python-dotenv>=1.0.0` - Ortam değişkenleri
- `apscheduler>=3.10.0` - Görev zamanlama
- `python-dateutil>=2.8.0` - Tarih işleme
- `pytz>=2023.3` - Zaman dilimi desteği

## 🚧 Gelecek Özellikler

- [ ] WhatsApp entegrasyonu
- [ ] Sesli komut desteği
- [ ] Web arayüzü
- [ ] Grafik ve istatistikler
- [ ] Çoklu dil desteği
- [ ] Dosya ve resim yükleme
- [ ] Grup çalışma özellikleri
- [ ] Not paylaşımı
- [ ] Quiz ve test oluşturma
- [ ] Pomodoro zamanlayıcı

## 🤝 Katkıda Bulunma

Katkılarınızı bekliyoruz! Lütfen pull request göndermeden önce:

1. Kodu test edin
2. Türkçe yorum ve dokümantasyon ekleyin
3. Kod standartlarına uyun
4. Değişikliklerinizi açıklayan commit mesajları yazın

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 👨‍💻 Geliştirici

Bu proje eğitim amaçlı geliştirilmiştir.

## 🙏 Teşekkürler

- Google Gemini AI ekibine
- Telegram Bot API'sine
- Açık kaynak topluluğuna

## 📞 İletişim

Sorularınız için GitHub Issues kullanabilirsiniz.

---

**Not:** Bu bot eğitim amaçlıdır. API kullanım limitlerini ve maliyetlerini göz önünde bulundurun.

🌟 **Projeyi beğendiyseniz yıldız vermeyi unutmayın!**
