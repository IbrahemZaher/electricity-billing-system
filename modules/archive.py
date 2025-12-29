# modules/archive.py
import logging
import os
import shutil
from datetime import datetime
from database.connection import db

logger = logging.getLogger(__name__)

class ArchiveManager:
    """مدير عمليات الأرشيف والنسخ الاحتياطي"""
    
    def __init__(self):
        self.backup_dir = "backups"
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def perform_backup(self):
        """تنفيذ نسخ احتياطي كامل"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_folder = os.path.join(self.backup_dir, f"backup_{timestamp}")
            os.makedirs(backup_folder, exist_ok=True)
            
            # تصدير البيانات من قاعدة البيانات
            self.export_database_tables(backup_folder)
            
            # نسخ ملفات النظام
            self.backup_system_files(backup_folder)
            
            logger.info(f"تم النسخ الاحتياطي في: {backup_folder}")
            return {
                'success': True,
                'backup_path': backup_folder,
                'message': f"تم النسخ الاحتياطي بنجاح في {backup_folder}"
            }
            
        except Exception as e:
            logger.error(f"فشل النسخ الاحتياطي: {e}")
            return {
                'success': False,
                'error': f"فشل النسخ الاحتياطي: {str(e)}"
            }
    
    def export_database_tables(self, backup_folder):
        """تصدير جداول قاعدة البيانات"""
        tables = ['customers', 'invoices', 'users', 'sectors', 'activity_logs']
        
        for table in tables:
            try:
                with db.get_cursor() as cursor:
                    cursor.execute(f"SELECT * FROM {table}")
                    rows = cursor.fetchall()
                    
                    if rows:
                        # تصدير كملف CSV
                        import csv
                        csv_file = os.path.join(backup_folder, f"{table}.csv")
                        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                            writer.writeheader()
                            writer.writerows([dict(row) for row in rows])
                            
            except Exception as e:
                logger.error(f"خطأ في تصدير جدول {table}: {e}")
    
    def backup_system_files(self, backup_folder):
        """نسخ ملفات النظام"""
        system_files = ['config/settings.py', 'requirements.txt']
        
        for file_path in system_files:
            if os.path.exists(file_path):
                try:
                    shutil.copy2(file_path, backup_folder)
                except Exception as e:
                    logger.error(f"خطأ في نسخ ملف {file_path}: {e}")
    
    def restore_backup(self, backup_folder):
        """استعادة النسخ الاحتياطي"""
        try:
            # هنا سيتم تنفيذ منطق الاستعادة
            logger.info(f"بدأت عملية الاستعادة من: {backup_folder}")
            return {
                'success': True,
                'message': "بدأت عملية الاستعادة"
            }
            
        except Exception as e:
            logger.error(f"فشل استعادة النسخ الاحتياطي: {e}")
            return {
                'success': False,
                'error': f"فشل استعادة النسخ الاحتياطي: {str(e)}"
            }