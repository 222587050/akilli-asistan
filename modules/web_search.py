"""
Web Search Asistan Modülü
Gemini AI ile güncel bilgi araştırma
"""
import logging
from typing import List

logger = logging.getLogger(__name__)


class WebSearchAssistant:
    """Gemini AI ile güncel bilgi araştırması yapan asistan"""

    # Web araması gerektiren anahtar kelimeler
    SEARCH_TRIGGERS: List[str] = [
        "hava", "weather", "sıcaklık", "yağmur", "kar",
        "ezan", "namaz", "vakit", "öğle", "akşam", "imsak",
        "dolar", "euro", "kur", "tl",
        "maç", "skor", "sonuç", "gol",
        "haber", "son dakika", "gündem",
        "açık mı", "kapalı mı", "çalışıyor mu",
        "saat kaçta", "ne zaman", "hangi gün",
    ]

    def __init__(self, model):
        """
        Web Search Asistan'ı başlat

        Args:
            model: Gemini GenerativeModel nesnesi
        """
        self.model = model

    def is_available(self) -> bool:
        """Web search asistan kullanılabilir mi?"""
        return self.model is not None

    def needs_web_search(self, message: str) -> bool:
        """
        Mesajın web araması gerektirip gerektirmediğini kontrol et

        Args:
            message: Kullanıcı mesajı

        Returns:
            bool: Web araması gerekiyorsa True
        """
        message_lower = message.lower()
        return any(trigger in message_lower for trigger in self.SEARCH_TRIGGERS)

    async def search_and_answer(self, question: str) -> str:
        """
        İnternetten araştırarak soruya cevap ver

        Args:
            question: Kullanıcı sorusu

        Returns:
            str: Kaynaklarla birlikte cevap
        """
        prompt = f"""Şu soruya güncel, doğru bilgilerle cevap ver.

Soru: {question}

Lütfen:
- Güncel bilgi ver (tarih belirt)
- Kaynak göster
- Türkçe cevapla
- Net ve öz ol

Format:
[CEVAP]

📚 Kaynaklar:
• [Kaynak 1]
• [Kaynak 2]
"""
        try:
            response = await self.model.generate_content_async(prompt)
            # response.text can raise if the response is blocked or empty
            try:
                return response.text
            except ValueError:
                logger.warning("Web search yanıtı boş veya engellendi")
                return "Üzgünüm, bu soruya şu anda cevap veremiyorum."
        except Exception as e:
            logger.error(f"Web search hatası: {e}")
            return "Araştırma yaparken bir hata oluştu. Lütfen tekrar deneyin."
