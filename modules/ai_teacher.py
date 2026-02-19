"""
AI Öğretmen Modülü
Gemini AI ile konu anlatımı ve quiz üretimi
"""
import json
import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class AITeacher:
    """
    Gemini AI ile konu anlatımı yapan öğretmen
    """

    def __init__(self, model):
        """
        AI Öğretmen'i başlat

        Args:
            model: Gemini GenerativeModel nesnesi
        """
        self.model = model

    def is_available(self) -> bool:
        """AI öğretmen kullanılabilir mi?"""
        return self.model is not None

    async def explain_topic(self, course: str, topic: str, level: str = "beginner") -> Dict[str, Any]:
        """
        Konu anlatımı yap

        Args:
            course: Ders adı (örn: "Yapay Zeka Uygulamaları")
            topic: Konu (örn: "Gradient Descent")
            level: Seviye (beginner/intermediate/advanced)

        Returns:
            dict: {
                "explanation": "Detaylı açıklama",
                "code_example": "Kod örneği",
                "key_points": ["Önemli nokta 1", ...],
                "practical_tip": "Pratik ipucu"
            }
        """
        seviye_map = {
            "beginner": "başlangıç",
            "intermediate": "orta",
            "advanced": "ileri",
        }
        seviye = seviye_map.get(level, "başlangıç")

        prompt = f"""Sen bir üniversite öğretmenisin. Türkçe olarak açıkla.

Ders: {course}
Konu: {topic}
Seviye: {seviye}

Lütfen şu formatta açıkla:

## KONU ANLATIMI
[Detaylı, anlaşılır açıklama. Örneklerle anlat.]

## KOD ÖRNEĞİ
[Python/JavaScript/C++ kod örneği. Yorumlu ve çalışır kod. Kod yoksa "Kod örneği yok." yaz.]

## ÖNEMLİ NOKTALAR
- [Nokta 1]
- [Nokta 2]
- [Nokta 3]

## PRATİK İPUCU
[Gerçek hayat uygulaması veya hatırlatma]
"""

        try:
            response = await self.model.generate_content_async(prompt)
            return self._parse_explanation(response.text)
        except Exception as e:
            logger.error(f"Konu anlatımı hatası: {e}")
            return {
                "explanation": f"Konu anlatımı sırasında hata oluştu: {e}",
                "code_example": "",
                "key_points": [],
                "practical_tip": "",
            }

    def _parse_explanation(self, text: str) -> Dict[str, Any]:
        """AI yanıtını ayrıştır"""
        result = {
            "explanation": "",
            "code_example": "",
            "key_points": [],
            "practical_tip": "",
        }

        # Bölümleri ayıkla
        sections = {
            "explanation": r"##\s*KONU ANLATIMI\s*\n(.*?)(?=##|\Z)",
            "code_example": r"##\s*KOD ÖRNEĞİ\s*\n(.*?)(?=##|\Z)",
            "key_points_raw": r"##\s*ÖNEMLİ NOKTALAR\s*\n(.*?)(?=##|\Z)",
            "practical_tip": r"##\s*PRATİK İPUCU\s*\n(.*?)(?=##|\Z)",
        }

        for key, pattern in sections.items():
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                result[key] = match.group(1).strip()

        # Önemli noktaları listeye çevir
        raw = result.pop("key_points_raw", "")
        if raw:
            result["key_points"] = [
                line.lstrip("-•* ").strip()
                for line in raw.splitlines()
                if line.strip() and line.strip() not in ("-", "•", "*")
            ]

        # Eğer ayrıştırma başarısız olduysa tüm metni açıklama olarak kullan
        if not result["explanation"]:
            result["explanation"] = text

        return result

    async def generate_quiz(self, course: str, topic: str, num_questions: int = 5) -> List[Dict[str, Any]]:
        """
        Quiz soruları üret

        Args:
            course: Ders adı
            topic: Konu
            num_questions: Soru sayısı

        Returns:
            list: [
                {
                    "question": "Soru",
                    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
                    "correct": "A",
                    "explanation": "Açıklama"
                },
                ...
            ]
        """
        prompt = f"""{course} - {topic} konusu için {num_questions} adet çoktan seçmeli soru oluştur.

Sadece JSON formatında döndür, başka hiçbir şey yazma:
[
  {{
    "question": "Soru metni",
    "options": ["A) Şık 1", "B) Şık 2", "C) Şık 3", "D) Şık 4"],
    "correct": "A",
    "explanation": "Neden A doğru?"
  }}
]
"""

        try:
            response = await self.model.generate_content_async(prompt)
            raw = response.text.strip()
            # JSON bloğunu ayıkla
            json_match = re.search(r'\[.*\]', raw, re.DOTALL)
            if json_match:
                questions = json.loads(json_match.group(0))
            else:
                questions = json.loads(raw)
            # Doğrulama: her soru gerekli alanlara sahip olmalı
            validated = []
            for q in questions:
                if all(k in q for k in ("question", "options", "correct", "explanation")):
                    validated.append(q)
            return validated
        except json.JSONDecodeError as e:
            logger.error(f"Quiz JSON ayrıştırma hatası: {e}")
            return []
        except Exception as e:
            logger.error(f"Quiz üretme hatası: {e}")
            return []
