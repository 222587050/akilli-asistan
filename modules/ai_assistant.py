"""
Google Gemini Pro AI Asistan Entegrasyonu
"""
import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE, GEMINI_MAX_TOKENS, CONTEXT_WINDOW
from database import DatabaseManager

logger = logging.getLogger(__name__)


class AIAssistant:
    """Google Gemini Pro AI Asistan Sınıfı"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        AI Asistan'ı başlat
        
        Args:
            db_manager: Veritabanı yöneticisi
        """
        self.db_manager = db_manager
        self.model = None
        self.model_name = None
        
        if not GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY bulunamadı!")
            return
        
        try:
            # Gemini API'yi yapılandır
            genai.configure(api_key=GEMINI_API_KEY)
            
            # Model öncelik sırası (yeniden eskiye)
            models_to_try = [
                'gemini-2.5-flash',      # En yeni kararlı, hızlı
                'gemini-2.5-pro',        # Daha güçlü ama yavaş
                'gemini-flash-latest',   # Otomatik güncel
                'gemini-2.0-flash',      # Yedek model
                'gemini-1.5-flash',      # Eski ama kararlı
            ]
            
            # Sistem yönergesi (Türkçe AI asistan davranışı)
            # Note: System instruction is defined here (not in config) because it's
            # integral to the GenerativeModel initialization and Gemini API requires
            # it at model creation time, not as part of message history
            system_instruction = """Sen yardımsever bir Türkçe asistansın. Öğrencilere ders konularında yardımcı oluyorsun.
Görevlerin:
- Ders sorularını açık ve anlaşılır şekilde yanıtlamak
- Not özetleme ve açıklama yapmak
- Öğrenme sürecinde rehberlik etmek
- Türkçe ve nazik bir dil kullanmak

Her zaman yapıcı, teşvik edici ve eğitici ol."""
            
            # Model yapılandırması
            generation_config = {
                'temperature': GEMINI_TEMPERATURE,
                'max_output_tokens': GEMINI_MAX_TOKENS,
            }
            
            # İlk çalışan modeli kullan
            model_found = False
            for model_name in models_to_try:
                try:
                    test_model = genai.GenerativeModel(
                        model_name=model_name,
                        generation_config=generation_config,
                        system_instruction=system_instruction
                    )
                    # Modeli test et
                    test_model.count_tokens("test")
                    self.model = test_model
                    self.model_name = model_name
                    logger.info(f"✅ Gemini AI modeli başlatıldı: {model_name}")
                    model_found = True
                    break
                except Exception as e:
                    logger.warning(f"⚠️ {model_name} kullanılamıyor ({str(e)}), sonraki deneniyor...")
                    continue
            
            if not model_found:
                raise Exception("❌ Hiçbir Gemini model bulunamadı! API key'inizi kontrol edin.")
                
        except Exception as e:
            logger.error(f"Gemini AI başlatma hatası: {e}")
    
    def is_available(self) -> bool:
        """AI asistan kullanılabilir mi?"""
        return self.model is not None
    
    def chat(self, user_id: int, message: str, use_context: bool = True, context: str = None) -> str:
        """
        Kullanıcı ile sohbet et
        
        Args:
            user_id: Kullanıcı ID'si
            message: Kullanıcı mesajı
            use_context: Sohbet geçmişini kullan
            context: Ek bağlam bilgisi (opsiyonel)
            
        Returns:
            AI yanıtı
        """
        if not self.is_available():
            return "Üzgünüm, AI asistan şu anda kullanılamıyor. Lütfen GEMINI_API_KEY ayarlandığından emin olun."
        
        try:
            # Context varsa mesaja ekle
            if context:
                full_message = f"{context}\n\nKullanıcı mesajı: {message}"
            else:
                full_message = message
            
            # Kullanıcı mesajını kaydet (orijinal mesaj)
            self.db_manager.add_chat_message(user_id, 'user', message)
            
            # Sohbet geçmişini al
            if use_context:
                history = self.db_manager.get_chat_history(user_id, limit=CONTEXT_WINDOW)
            else:
                history = []
            
            # Sohbet oturumu başlat (system_instruction modelde tanımlı)
            chat_session = self.model.start_chat(history=history)
            
            # Yanıt oluştur (context varsa full_message kullan)
            response = chat_session.send_message(full_message)
            ai_response = response.text
            
            # AI yanıtını kaydet (Gemini'de 'model' rolü kullanılır)
            self.db_manager.add_chat_message(user_id, 'model', ai_response)
            
            logger.info(f"AI yanıt oluşturuldu: kullanıcı={user_id}")
            return ai_response
            
        except Exception as e:
            logger.error(f"AI sohbet hatası: {e}")
            return f"Üzgünüm, bir hata oluştu: {str(e)}"
    
    def summarize_notes(self, notes_content: str) -> str:
        """
        Notları özetle
        
        Args:
            notes_content: Not içeriği
            
        Returns:
            Özet
        """
        if not self.is_available():
            return "AI asistan kullanılamıyor."
        
        try:
            prompt = f"""Aşağıdaki notları özetle. Önemli noktaları vurgula ve düzenli bir şekilde sun:

{notes_content}

Özet:"""
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Not özetleme hatası: {e}")
            return f"Not özetleme hatası: {str(e)}"
    
    def explain_topic(self, topic: str, detail_level: str = "orta") -> str:
        """
        Bir konuyu açıkla
        
        Args:
            topic: Konu
            detail_level: Detay seviyesi (basit, orta, detaylı)
            
        Returns:
            Açıklama
        """
        if not self.is_available():
            return "AI asistan kullanılamıyor."
        
        try:
            detail_instructions = {
                "basit": "Basit ve anlaşılır bir dille, örneklerle açıkla.",
                "orta": "Orta seviyede detayla, örnekler ve açıklamalarla sun.",
                "detaylı": "Detaylı ve kapsamlı bir şekilde, örnekler ve uygulamalarla açıkla."
            }
            
            instruction = detail_instructions.get(detail_level, detail_instructions["orta"])
            
            prompt = f"""Aşağıdaki konuyu Türkçe olarak açıkla:

Konu: {topic}

Açıklama seviyesi: {instruction}

Açıklama:"""
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Konu açıklama hatası: {e}")
            return f"Konu açıklama hatası: {str(e)}"
    
    def answer_question(self, question: str, context: str = None) -> str:
        """
        Soru yanıtla
        
        Args:
            question: Soru
            context: Bağlam bilgisi (opsiyonel)
            
        Returns:
            Yanıt
        """
        if not self.is_available():
            return "AI asistan kullanılamıyor."
        
        try:
            if context:
                prompt = f"""Bağlam: {context}

Soru: {question}

Yanıt:"""
            else:
                prompt = f"""Soru: {question}

Lütfen soruyu detaylı ve anlaşılır bir şekilde Türkçe yanıtla.

Yanıt:"""
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Soru yanıtlama hatası: {e}")
            return f"Soru yanıtlama hatası: {str(e)}"
    
    def generate_study_plan(self, subject: str, duration_days: int = 7) -> str:
        """
        Çalışma planı oluştur
        
        Args:
            subject: Ders/Konu
            duration_days: Gün sayısı
            
        Returns:
            Çalışma planı
        """
        if not self.is_available():
            return "AI asistan kullanılamıyor."
        
        try:
            prompt = f""""{subject}" konusu için {duration_days} günlük bir çalışma planı oluştur.

Plan:
- Günlük hedefler
- Çalışma süreleri
- Önerilen kaynaklar
- Tekrar zamanları

Çalışma Planı:"""
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Çalışma planı oluşturma hatası: {e}")
            return f"Çalışma planı oluşturma hatası: {str(e)}"
