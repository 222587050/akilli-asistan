"""
Hatırlatıcı Zamanlama Sistemi
APScheduler ile zamanlanmış görevler
"""
import logging
from datetime import datetime
from typing import Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import pytz

from config import TIMEZONE, REMINDER_CHECK_INTERVAL

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Hatırlatıcı zamanlama sistemi"""
    
    def __init__(self, reminder_callback: Callable = None):
        """
        Scheduler'ı başlat
        
        Args:
            reminder_callback: Hatırlatıcı tetiklendiğinde çağrılacak fonksiyon
        """
        self.scheduler = BackgroundScheduler(timezone=TIMEZONE)
        self.reminder_callback = reminder_callback
        self.is_running = False
        
        logger.info("ReminderScheduler oluşturuldu")
    
    def start(self):
        """Scheduler'ı başlat"""
        if not self.is_running:
            try:
                self.scheduler.start()
                self.is_running = True
                logger.info("Hatırlatıcı zamanlayıcı başlatıldı")
                
                # Periyodik kontrol görevini ekle
                if self.reminder_callback:
                    self.scheduler.add_job(
                        self._check_reminders,
                        'interval',
                        seconds=REMINDER_CHECK_INTERVAL,
                        id='reminder_checker',
                        replace_existing=True
                    )
                    logger.info(f"Hatırlatıcı kontrolü her {REMINDER_CHECK_INTERVAL} saniyede bir çalışacak")
            except Exception as e:
                logger.error(f"Scheduler başlatma hatası: {e}")
                raise
    
    def stop(self):
        """Scheduler'ı durdur"""
        if self.is_running:
            try:
                self.scheduler.shutdown(wait=False)
                self.is_running = False
                logger.info("Hatırlatıcı zamanlayıcı durduruldu")
            except Exception as e:
                logger.error(f"Scheduler durdurma hatası: {e}")
    
    def _check_reminders(self):
        """Bekleyen hatırlatıcıları kontrol et"""
        if self.reminder_callback:
            try:
                self.reminder_callback()
            except Exception as e:
                logger.error(f"Hatırlatıcı kontrol hatası: {e}")
    
    def add_reminder(self, reminder_id: int, remind_at: datetime, 
                    callback: Callable, *args, **kwargs):
        """
        Tek seferlik hatırlatıcı ekle
        
        Args:
            reminder_id: Hatırlatıcı ID'si
            remind_at: Hatırlatma zamanı
            callback: Çağrılacak fonksiyon
            *args, **kwargs: Callback fonksiyonuna geçilecek argümanlar
        """
        try:
            # Timezone bilgisi ekle
            tz = pytz.timezone(TIMEZONE)
            if remind_at.tzinfo is None:
                remind_at = tz.localize(remind_at)
            
            job_id = f"reminder_{reminder_id}"
            
            self.scheduler.add_job(
                callback,
                trigger=DateTrigger(run_date=remind_at),
                args=args,
                kwargs=kwargs,
                id=job_id,
                replace_existing=True
            )
            
            logger.info(f"Hatırlatıcı zamanlandı: ID={reminder_id}, Zaman={remind_at}")
        except Exception as e:
            logger.error(f"Hatırlatıcı ekleme hatası: {e}")
    
    def remove_reminder(self, reminder_id: int):
        """
        Hatırlatıcıyı kaldır
        
        Args:
            reminder_id: Hatırlatıcı ID'si
        """
        try:
            job_id = f"reminder_{reminder_id}"
            self.scheduler.remove_job(job_id)
            logger.info(f"Hatırlatıcı kaldırıldı: ID={reminder_id}")
        except Exception as e:
            logger.warning(f"Hatırlatıcı kaldırma hatası: {e}")
    
    def add_recurring_reminder(self, reminder_id: int, recurrence_pattern: str,
                              start_date: datetime, callback: Callable, 
                              *args, **kwargs):
        """
        Tekrarlanan hatırlatıcı ekle
        
        Args:
            reminder_id: Hatırlatıcı ID'si
            recurrence_pattern: Tekrar düzeni (daily, weekly, monthly)
            start_date: Başlangıç tarihi
            callback: Çağrılacak fonksiyon
            *args, **kwargs: Callback fonksiyonuna geçilecek argümanlar
        """
        try:
            job_id = f"reminder_{reminder_id}"
            
            # Tekrar düzenini belirle
            if recurrence_pattern == 'daily':
                trigger = 'cron'
                trigger_args = {
                    'hour': start_date.hour,
                    'minute': start_date.minute
                }
            elif recurrence_pattern == 'weekly':
                trigger = 'cron'
                trigger_args = {
                    'day_of_week': start_date.weekday(),
                    'hour': start_date.hour,
                    'minute': start_date.minute
                }
            elif recurrence_pattern == 'monthly':
                trigger = 'cron'
                trigger_args = {
                    'day': start_date.day,
                    'hour': start_date.hour,
                    'minute': start_date.minute
                }
            else:
                logger.warning(f"Bilinmeyen tekrar düzeni: {recurrence_pattern}")
                return
            
            self.scheduler.add_job(
                callback,
                trigger=trigger,
                args=args,
                kwargs=kwargs,
                id=job_id,
                replace_existing=True,
                **trigger_args
            )
            
            logger.info(f"Tekrarlanan hatırlatıcı zamanlandı: ID={reminder_id}, Düzen={recurrence_pattern}")
        except Exception as e:
            logger.error(f"Tekrarlanan hatırlatıcı ekleme hatası: {e}")
    
    def get_scheduled_jobs_count(self) -> int:
        """Zamanlanmış görev sayısını döndür"""
        return len(self.scheduler.get_jobs())
