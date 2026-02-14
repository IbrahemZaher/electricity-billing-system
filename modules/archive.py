"""
modules/archive.py - مدير عمليات الأرشيف والنسخ الاحتياطي (محدث)
"""

import logging
import os
import shutil
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config.settings import BACKUP_CONFIG, DATABASE_CONFIG
from modules.backup_engine import PostgresBackupEngine


logger = logging.getLogger(__name__)

class ArchiveManager:
    """مدير عمليات الأرشيف والنسخ الاحتياطي (نسخة متقدمة)"""

    def __init__(self):
        self.backup_engine = PostgresBackupEngine()
        self.backup_dir = BACKUP_CONFIG['local_backup_path']
        os.makedirs(self.backup_dir, exist_ok=True)

    def perform_backup(self, backup_type: str = 'full') -> Dict:
        """
        تنفيذ نسخ احتياطي.
        backup_type: 'full' أو 'wal' (WAL archive)
        """
        try:
            if backup_type == 'full':
                result = self.backup_engine.perform_full_backup()
                if result.get('success'):
                    # أرشفة WAL بعد النسخة الكاملة (اختياري)
                    self.backup_engine.archive_wal()
                    # إرسال النسخة إلى المواقع البعيدة
                    backup_path = Path(result['backup_path'])
                    self.backup_engine.send_to_remote(backup_path)
                    # التحقق من السلامة
                    if BACKUP_CONFIG['verification'].get('verify_after_backup', True):
                        verified = self.backup_engine.verify_backup(backup_path, result['metadata'])
                        if not verified:
                            self.backup_engine.send_notification(
                                "فشل التحقق من النسخة الاحتياطية",
                                f"النسخة {backup_path.name} فشلت في التحقق.",
                                success=False
                            )
                    # تطبيق سياسة الاحتفاظ
                    self.backup_engine.apply_retention_policy()
                    # إرسال إشعار نجاح
                    self.backup_engine.send_notification(
                        "نجاح النسخ الاحتياطي",
                        f"تم إنشاء نسخة احتياطية كاملة بنجاح: {backup_path.name}",
                        success=True
                    )
                return result
            elif backup_type == 'wal':
                success = self.backup_engine.archive_wal()
                return {'success': success, 'message': 'تم أرشفة WAL'}
            else:
                return {'success': False, 'error': f'نوع النسخ غير مدعوم: {backup_type}'}
        except Exception as e:
            logger.error(f"فشل النسخ الاحتياطي: {e}")
            self.backup_engine.send_notification(
                "فشل النسخ الاحتياطي",
                f"حدث خطأ: {str(e)}",
                success=False
            )
            return {'success': False, 'error': str(e)}

    def _close_db_connections(self):
        """إغلاق جميع اتصالات قاعدة البيانات الحالية."""
        try:
            from database.connection import db
            db.close_all_connections()
            logger.info("تم إغلاق جميع اتصالات قاعدة البيانات بنجاح.")
        except Exception as e:
            logger.warning(f"فشل إغلاق اتصالات قاعدة البيانات: {e}")

    def restore_backup(self, backup_path: str, recovery_target_time: str = None) -> Dict:
        """
        استعادة نسخة احتياطية - مع إغلاق جميع الاتصالات وإعادة تشغيلها بعد الاستعادة
        """
        try:
            backup_file = Path(backup_path)

            # فك التشفير إذا لزم الأمر
            if backup_file.suffix == '.gpg':
                decrypted = self._decrypt_file(backup_file)
                if not decrypted:
                    return {'success': False, 'error': 'فشل فك التشفير'}
                backup_file = decrypted

            if not backup_file.exists():
                return {'success': False, 'error': f'ملف النسخة غير موجود: {backup_file}'}

            # ========== إغلاق جميع اتصالات قاعدة البيانات ==========
            logger.info("محاولة إغلاق جميع اتصالات قاعدة البيانات...")
            try:
                from database.connection import db
                # إذا كان هناك تجمع اتصالات، نغلقه تمامًا
                if hasattr(db, 'pool') and db.pool:
                    db.pool.closeall()
                    logger.info("تم إغلاق تجمع الاتصالات.")
                # أيضًا إغلاق أي اتصال مباشر
                if hasattr(db, 'connection') and db.connection:
                    db.connection.close()
            except Exception as e:
                logger.warning(f"فشل إغلاق الاتصالات: {e}")

            # ========== بناء الأمر ==========
            # استخدم المسار الكامل لـ pg_restore (عدل الإصدار حسب جهازك)
            pg_restore_path = r"C:\Program Files\PostgreSQL\18\bin\pg_restore.exe"
            if not os.path.exists(pg_restore_path):
                # إذا لم يكن المسار أعلاه صحيحًا، اتركه يعتمد على PATH
                pg_restore_path = "pg_restore"

            cmd = [
                pg_restore_path,
                '-U', DATABASE_CONFIG['user'],
                '-d', DATABASE_CONFIG['database'],
                '-h', DATABASE_CONFIG['host'],
                '-p', str(DATABASE_CONFIG['port']),
                '--clean',
                '--if-exists',
                str(backup_file)
            ]

            # إعداد متغيرات البيئة
            env = os.environ.copy()
            env['PGPASSWORD'] = DATABASE_CONFIG['password']

            # تسجيل الأمر قبل التنفيذ (مهم جدًا)
            logger.info(f"تشغيل الأمر: {' '.join(cmd)}")
            logger.info(f"مع كلمة المرور: {DATABASE_CONFIG['password'][:2]}*** (مخفية)")

            # ========== تنفيذ الأمر ==========
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            # تسجيل الخرج
            if result.stdout:
                logger.info(f"stdout: {result.stdout}")
            if result.stderr:
                logger.error(f"stderr: {result.stderr}")

            if result.returncode != 0:
                error_msg = f"pg_restore فشل (رمز {result.returncode}): {result.stderr}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}

            logger.info(f"تمت استعادة النسخة {backup_file.name} بنجاح")

            # ========== إعادة إنشاء اتصال قاعدة البيانات (اختياري) ==========
            try:
                from database.connection import db
                db.reconnect()  # إذا كانت موجودة، أو ببساطة db.connect()
            except Exception as e:
                logger.warning(f"فشل إعادة الاتصال بقاعدة البيانات: {e}")

            return {'success': True, 'message': 'تمت الاستعادة بنجاح'}

        except Exception as e:
            logger.error(f"استثناء عام في restore_backup: {e}")
            return {'success': False, 'error': str(e)}


    def _decrypt_file(self, encrypted_path: Path) -> Optional[Path]:
        """فك تشفير ملف GPG (يتطلب المفتاح الخاص)."""
        try:
            import gnupg
            gpg = gnupg.GPG()
            decrypted_path = encrypted_path.with_suffix('')  # إزالة .gpg
            with open(encrypted_path, 'rb') as f:
                status = gpg.decrypt_file(f, output=str(decrypted_path))
            if status.ok:
                return decrypted_path
            else:
                logger.error(f"فشل فك التشفير: {status.stderr}")
                return None
        except Exception as e:
            logger.error(f"خطأ في فك التشفير: {e}")
            return None

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
    
