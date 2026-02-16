import tkinter as tk
from tkinter import messagebox
import logging
import sys
import os

# ⭐⭐⭐ تحديد المسار الأساسي (يدعم وضع التطوير والتجميع) ⭐⭐⭐
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ⭐⭐⭐ إنشاء مجلد السجلات تلقائياً ⭐⭐⭐
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, 'application.log')

# إعداد سجل الأخطاء باستخدام المسار المطلق
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# إضافة المسارات للمكتبات (يبقى كما هو لضمان توافق الوحدات)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    try:
        # ⭐⭐⭐ التحقق من وجود قاعدة البيانات دون إعادة تعيين الصلاحيات ⭐⭐⭐
        logger.info("بدء التحقق من قاعدة البيانات...")
        
        # التحقق البسيط من الاتصال بدلاً من استدعاء models
        from database.connection import db
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                logger.info("✅ اتصال قاعدة البيانات نشط")
        except Exception as e:
            logger.error(f"❌ خطأ في اتصال قاعدة البيانات: {e}")
            raise
        
        # ⭐⭐⭐ تهيئة الجداول فقط إذا كانت غير موجودة ⭐⭐⭐
        try:
            from database.models import models
            logger.info("✅ تم التحقق من بنية قاعدة البيانات")
        except Exception as e:
            logger.error(f"❌ خطأ في تهيئة الجداول: {e}")
            # إعادة المحاولة مرة واحدة فقط
            try:
                from database.models import models
                logger.info("✅ تم إصلاح بنية قاعدة البيانات")
            except Exception as e2:
                logger.error(f"❌ فشل إصلاح قاعدة البيانات: {e2}")
                raise
        
        # تشغيل نافذة تسجيل الدخول
        from ui.login_window import LoginWindow
        login_window = LoginWindow()
        login_window.run()
        
    except Exception as e:
        logger.error(f"خطأ في تشغيل البرنامج: {e}")
        messagebox.showerror("خطأ تشغيل", f"فشل تشغيل البرنامج: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()