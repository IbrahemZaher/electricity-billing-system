# config/settings.py
import sys
import os
from pathlib import Path

def get_base_path():
    """إرجاع المسار الأساسي للمشروع سواء كان في وضع التطوير أو بعد التعبئة"""
    if getattr(sys, 'frozen', False):
        # إذا كان التطبيق مجمداً (أي exe)
        return Path(sys.executable).parent
    else:
        # وضع التطوير العادي
        return Path(__file__).resolve().parent.parent

# مسارات الملفات
BASE_DIR = get_base_path()
DATA_DIR = BASE_DIR / 'data'
LOG_DIR = BASE_DIR / 'logs'
BACKUP_DIR = BASE_DIR / 'backups'
WAL_ARCHIVE_DIR = BASE_DIR / 'wal_archive'
KEYS_DIR = BASE_DIR / 'keys'

# إنشاء المجلدات (تأكد من وجودها)
for directory in [DATA_DIR, LOG_DIR, BACKUP_DIR, WAL_ARCHIVE_DIR, KEYS_DIR]:
    directory.mkdir(exist_ok=True)

# إعدادات قاعدة البيانات
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'electricity_billing'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '521990')
}

# المفتاح السري للتشفير
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here-change-in-production')

# إعدادات النظام
APP_NAME = 'مولدة الريان - نظام إدارة الفواتير'
COMPANY_NAME = 'شركة الريان للطاقة الكهربائية'
VERSION = '3.0.0'

# إعدادات الطباعة
PRINTER_CONFIG = {
    'ip': '10.10.0.5',
    'port': 9100,
    'timeout': 10,
    'paper_width': 570
}

# الصلاحيات الافتراضية
DEFAULT_PERMISSIONS = {
    'admin': {
        'all': True,
        'manage_import': True,
        'system.advanced_export': True,
        'delete_all_customers': True
    },
    'manager': {
        'view_customers': True,
        'add_customers': True,
        'edit_customers': True,
        'delete_customers': True,
        'create_invoices': True,
        'view_invoices': True,
        'edit_invoices': True,
        'delete_invoices': True,
        'view_reports': True,
        'export_data': True,
        'manage_users': False,
        'view_activity_log': True,
        'system.advanced_export': True,
        'manage_import': True
    },
    'accountant': {
        'view_customers': True,
        'add_customers': True,
        'edit_customers': True,
        'create_invoices': True,
        'view_invoices': True,
        'view_reports': True
    }
}

# إعدادات النسخ الاحتياطي (المعدلة)
BACKUP_CONFIG = {
    'local_backup_path': str(BACKUP_DIR),
    'remote_backup_paths': [
        # r"\\10.10.0.1\D\backups",
        # r"\\10.10.0.6\D\backups"
    ],
    'backup_interval_hours': 24,

    # إعدادات جديدة للنسخ الاحتياطي المتقدم
    'wal_archive_path': str(WAL_ARCHIVE_DIR),
    'recovery_target_time': None,
    'retention_policy': {
        'daily': 30,
        'weekly': 12,
        'monthly': 12,
    },
    'encryption': {
        'enabled': False,
        'method': 'gpg',
        'public_key_path': str(KEYS_DIR / 'backup_public.asc'),
        'recipient': 'backup@example.com',
    },
    'notification': {
        'enabled': False,
        'email': {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'username': 'user@gmail.com',
            'password': 'app_password',
            'from_addr': 'user@gmail.com',
            'to_addrs': ['admin@example.com']
        },
        'slack_webhook': 'https://hooks.slack.com/services/...',
    },
    'verification': {
        'enabled': True,
        'verify_after_backup': True,
        'verify_random_sample': True,
        'sample_size': 10,
    },
    'parallel_backup': True,
}

# إعدادات الأداء
PERFORMANCE_SETTINGS = {
    'fast_search_limit': 50,
    'auto_save_interval': 60,
    'cache_customers': True,
    'parallel_backup': True,
    'fast_printing': True,
}

# إعدادات الاتصال
CONNECTION_POOL = {
    'min_connections': 5,
    'max_connections': 50,
    'connection_timeout': 30,
}