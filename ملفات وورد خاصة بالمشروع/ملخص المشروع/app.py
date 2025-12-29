# app.py
import tkinter as tk
from tkinter import messagebox
import logging
import sys
import os

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

def main():
    try:
        # التحقق من وجود قاعدة البيانات
        from database.models import models
        logger.info("تم تهيئة قاعدة البيانات بنجاح")
        
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