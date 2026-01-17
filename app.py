# app.py
import tkinter as tk
from tkinter import messagebox
import logging
import sys
import os

import threading
from modules.fast_operations import FastOperations

# إعداد سجل الأخطاء
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/application.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# إضافة المسارات للمكتبات
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
def auto_backup():
    """نسخ احتياطي تلقائي كل 6 ساعات"""
    try:
        logger.info("بدء النسخ الاحتياطي التلقائي...")
        fast_ops = FastOperations()
        fast_ops.backup_to_excel_parallel()
        logger.info("اكتمل النسخ الاحتياطي التلقائي")
    except Exception as e:
        logger.error(f"خطأ في النسخ الاحتياطي التلقائي: {e}")

def run_scheduler():
    """تشغيل المجدول في thread منفصل"""
    schedule.every(6).hours.do(auto_backup)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def main():
    try:
        # التحقق من وجود قاعدة البيانات
        from database.models import models
        logger.info("تم تهيئة قاعدة البيانات بنجاح")
        
        # تشغيل نافذة تسجيل الدخول
        from ui.login_window import LoginWindow
        login_window = LoginWindow()
        login_window.run()

        
        # بدء النسخ الاحتياطي التلقائي
        backup_thread = threading.Thread(target=run_scheduler, daemon=True)
        backup_thread.start()
            
    except Exception as e:
        logger.error(f"خطأ في تشغيل البرنامج: {e}")
        messagebox.showerror("خطأ تشغيل", f"فشل تشغيل البرنامج: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()