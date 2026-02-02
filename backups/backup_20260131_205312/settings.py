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

# إعدادات النسخ الاحتياطي
BACKUP_CONFIG = {
    'local_backup_path': str(BACKUP_DIR),
    'remote_backup_paths': [
        r"\\10.10.0.1\D\backups",
        r"\\10.10.0.6\D\backups"
    ],
    'backup_interval_hours': 24
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