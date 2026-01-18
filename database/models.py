# database/models.py
from database.connection import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Models:
    def __init__(self):
        self.create_tables()

    def update_invoices_table(self):
        """تحديث جدول الفواتير بإضافة الأعمدة المفقودة"""
        try:
            with db.get_cursor() as cursor:
                # التحقق من وجود الأعمدة وإضافتها إذا كانت غير موجودة
                columns_to_add = [
                    ('free_kilowatt', 'DECIMAL(10, 2) DEFAULT 0'),
                    ('visa_application', 'VARCHAR(100)'),
                    ('customer_withdrawal', 'VARCHAR(100)'),
                    ('notes', 'TEXT')
                ]
                
                for column_name, column_type in columns_to_add:
                    # التحقق إذا كان العمود موجوداً
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'invoices' 
                        AND column_name = %s
                    """, (column_name,))
                    
                    if not cursor.fetchone():
                        # إضافة العمود إذا لم يكن موجوداً
                        cursor.execute(f"""
                            ALTER TABLE invoices 
                            ADD COLUMN {column_name} {column_type}
                        """)
                        logger.info(f"تم إضافة العمود {column_name} إلى جدول invoices")
                    else:
                        logger.info(f"العمود {column_name} موجود بالفعل")
                        
        except Exception as e:
            logger.error(f"خطأ في تحديث جدول invoices: {e}")
    
    def create_indexes(self, cursor):
        """إنشاء الفهارس للبحث السريع"""
        try:
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);",
                "CREATE INDEX IF NOT EXISTS idx_customers_box_number ON customers(box_number);",
                "CREATE INDEX IF NOT EXISTS idx_customers_sector_id ON customers(sector_id);",
                "CREATE INDEX IF NOT EXISTS idx_customers_is_active ON customers(is_active);",
                
                "CREATE INDEX IF NOT EXISTS idx_invoices_customer_id ON invoices(customer_id);",
                "CREATE INDEX IF NOT EXISTS idx_invoices_payment_date ON invoices(payment_date);",
                "CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number ON invoices(invoice_number);",
                
                "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
                "CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);",
                
                "CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON activity_logs(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON activity_logs(created_at);"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            logger.info("تم إنشاء الفهارس للبحث السريع")
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء الفهارس: {e}")
            raise
    
    def create_tables(self):
        """إنشاء جميع الجداول الضرورية"""
        tables_sql = [
            # جدول المستخدمين مع الصلاحيات
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'accountant',
                permissions JSONB DEFAULT '{}',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # جدول القطاعات
            """
            CREATE TABLE IF NOT EXISTS sectors (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                code VARCHAR(10) UNIQUE NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE
            )
            """,
            
            # جدول الزبائن
            """
            CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY,
                sector_id INTEGER REFERENCES sectors(id),
                box_number VARCHAR(20),
                serial_number VARCHAR(20),
                name VARCHAR(100) NOT NULL,
                phone_number VARCHAR(20),
                telegram_username VARCHAR(50),
                current_balance DECIMAL(15, 2) DEFAULT 0,
                last_counter_reading DECIMAL(15, 2) DEFAULT 0,
                visa_balance DECIMAL(15, 2) DEFAULT 0,
                withdrawal_amount DECIMAL(15, 2) DEFAULT 0,
                notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # جدول الفواتير
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id SERIAL PRIMARY KEY,
                invoice_number VARCHAR(50) UNIQUE NOT NULL,
                customer_id INTEGER REFERENCES customers(id),
                sector_id INTEGER REFERENCES sectors(id),
                user_id INTEGER REFERENCES users(id),
                
                -- بيانات الدفع
                payment_date DATE NOT NULL,
                payment_time TIME NOT NULL,
                kilowatt_amount DECIMAL(10, 2) NOT NULL,
                free_kilowatt DECIMAL(10, 2) DEFAULT 0,
                price_per_kilo DECIMAL(10, 2) NOT NULL,
                discount DECIMAL(10, 2) DEFAULT 0,
                total_amount DECIMAL(15, 2) NOT NULL,
                
                -- قراءات العداد
                previous_reading DECIMAL(15, 2) NOT NULL,
                new_reading DECIMAL(15, 2) NOT NULL,
                
                -- التأشيرات والسحب
                visa_application VARCHAR(100),
                customer_withdrawal VARCHAR(100),
                
                -- المستندات
                book_number VARCHAR(50),
                receipt_number VARCHAR(50),
                
                -- معلومات إضافية
                current_balance DECIMAL(15, 2),
                telegram_password VARCHAR(50),
                
                -- حالة الفاتورة
                status VARCHAR(20) DEFAULT 'active',
                printed_count INTEGER DEFAULT 0,
                
                -- أرشفة
                archived_at TIMESTAMP,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # جدول سجل النشاطات
            """
            CREATE TABLE IF NOT EXISTS activity_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                action_type VARCHAR(50) NOT NULL,
                description TEXT NOT NULL,
                ip_address INET,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # جدول أرشيف الفواتير (للأرشفة المنفصلة)
            """
            CREATE TABLE IF NOT EXISTS invoice_archive (
                id SERIAL PRIMARY KEY,
                original_invoice_id INTEGER,
                invoice_data JSONB NOT NULL,
                archived_by INTEGER REFERENCES users(id),
                archive_reason VARCHAR(100),
                archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # جدول الإعدادات
            """
            CREATE TABLE IF NOT EXISTS settings (
                id SERIAL PRIMARY KEY,
                key VARCHAR(100) UNIQUE NOT NULL,
                value TEXT,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        try:
            with db.get_cursor() as cursor:
                for sql in tables_sql:
                    cursor.execute(sql)
                logger.info("تم إنشاء جميع الجداول بنجاح")
                
                # إضافة البيانات الأساسية
                self.seed_initial_data(cursor)
                
                # إنشاء الفهارس
                self.create_indexes(cursor)
                
            # تحديث جدول الفواتير بإضافة الأعمدة المفقودة
            self.update_invoices_table()
                
        except Exception as e:
            logger.error(f"خطأ في إنشاء الجداول: {e}")
            raise
    
    def seed_initial_data(self, cursor):
        """إضافة البيانات الأولية"""
        # إضافة القطاعات الأساسية
        sectors = [
            ("بيدر", "BAIDAR"),
            ("غبور", "GABOR"),
            ("الحديقة", "GARDEN"),
            ("القمر", "MOON"),
            ("صمصم", "SAMSAM"),
            ("تغرة", "TAGRA")
        ]
        
        for name, code in sectors:
            cursor.execute("""
                INSERT INTO sectors (name, code) 
                VALUES (%s, %s)
                ON CONFLICT (name) DO NOTHING
            """, (name, code))
        
        # إضافة المستخدم الإداري الافتراضي
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, role, permissions)
            VALUES ('admin', 'admin123', 'المسؤول العام', 'admin', '{"all": true}')
            ON CONFLICT (username) DO NOTHING
        """)
        
        # إضافة الإعدادات الافتراضية
        settings = [
            ('printer_ip', '10.10.0.5', 'عنوان IP للطابعة'),
            ('printer_port', '9100', 'منفذ الطابعة'),
            ('default_price_per_kilo', '7200', 'سعر الكيلو الافتراضي'),
            ('company_name', 'شركة الريان للطاقة الكهربائية', 'اسم الشركة'),
            ('company_phone', '0952411882', 'هاتف الشركة'),
            ('company_address', '', 'عنوان الشركة')
        ]
        
        for key, value, description in settings:
            cursor.execute("""
                INSERT INTO settings (key, value, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO NOTHING
            """, (key, value, description))

# إنشاء كائن النماذج
models = Models()