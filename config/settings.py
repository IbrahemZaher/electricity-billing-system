# config/settings.py
import os
from pathlib import Path

# مسارات الملفات
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
LOG_DIR = BASE_DIR / 'logs'
BACKUP_DIR = BASE_DIR / 'backups'

# إنشاء المجلدات
for directory in [DATA_DIR, LOG_DIR, BACKUP_DIR]:
    directory.mkdir(exist_ok=True)

# إعدادات قاعدة البيانات

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

DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'electricity_billing'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '521990')
}

# الصلاحيات الافتراضية
DEFAULT_PERMISSIONS = {
    'admin': {
        'all': True,
        'manage_import': True,
        'system.advanced_export': True,
        'delete_all_customers': True    },
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
        'manage_import': True  # ← أضف هذا السطر
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

# config/settings.py (الإضافات الجديدة)

# إعدادات النسخ الاحتياطي (المعدلة)
BACKUP_CONFIG = {
    'local_backup_path': str(BACKUP_DIR),
    'remote_backup_paths': [
        #r"\\10.10.0.1\D\backups",
        #r"\\10.10.0.6\D\backups"
    ],
    'backup_interval_hours': 24,

    # إعدادات جديدة للنسخ الاحتياطي المتقدم
    'wal_archive_path': str(BASE_DIR / 'wal_archive'),      # مسار أرشيف WAL
    'recovery_target_time': None,                           # وقت الاستعادة الافتراضي (اختياري)
    'retention_policy': {
        'daily': 30,          # احتفاظ بالنسخ اليومية لمدة 30 يوم
        'weekly': 12,         # احتفاظ بالنسخ الأسبوعية لمدة 12 أسبوع
        'monthly': 12,        # احتفاظ بالنسخ الشهرية لمدة 12 شهر
    },
    'encryption': {
        'enabled': False,
        'method': 'gpg',      # أو 'openssl'
        'public_key_path': str(BASE_DIR / 'keys' / 'backup_public.asc'),
        'recipient': 'backup@example.com',  # لمفتاح GPG
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
        'slack_webhook': 'https://hooks.slack.com/services/...',  # اختياري
    },
    'verification': {
        'enabled': True,
        'verify_after_backup': True,          # التحقق من سلامة النسخة بعد إنشائها
        'verify_random_sample': True,         # استرجاع عينة عشوائية للتحقق
        'sample_size': 10,                    # عدد السجلات العشوائية للاسترجاع
    },
    'parallel_backup': True,                  # تشغيل النسخ المتوازية (لأدوات متعددة)
}

# إعدادات الأداء
PERFORMANCE_SETTINGS = {
    'fast_search_limit': 50,  # عدد نتائج البحث
    'auto_save_interval': 60,  # ثانية للحفظ التلقائي
    'cache_customers': True,   # تخزين مؤقت للزبائن
    'parallel_backup': True,   # نسخ احتياطي موازي
    'fast_printing': True,     # طباعة سريعة
}

# إعدادات الاتصال
CONNECTION_POOL = {
    'min_connections': 5,
    'max_connections': 50,
    'connection_timeout': 30,
}