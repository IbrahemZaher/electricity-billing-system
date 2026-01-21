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

    def update_customer_history_table(self):
        """تحديث جدول سجل الزبائن بإضافة/تصحيح الأعمدة المفقودة"""
        try:
            with db.get_cursor() as cursor:
                # قائمة الأعمدة التي يجب التحقق منها وإضافتها
                columns_to_add = [
                    ('created_by', 'INTEGER REFERENCES users(id)'),
                    ('transaction_type', 'VARCHAR(50)'),
                    ('amount', 'DECIMAL(15, 2)'),
                    ('balance_before', 'DECIMAL(15, 2)'),
                    ('balance_after', 'DECIMAL(15, 2)'),
                    ('current_balance_before', 'DECIMAL(15, 2)'),
                    ('current_balance_after', 'DECIMAL(15, 2)'),
                    ('kilowatt_amount', 'DECIMAL(10, 2)'),
                    ('free_kilowatt', 'DECIMAL(10, 2) DEFAULT 0'),
                    ('price_per_kilo', 'DECIMAL(10, 2)'),
                    ('total_amount', 'DECIMAL(15, 2)'),
                    ('invoice_number', 'VARCHAR(50)'),
                    ('receipt_number', 'VARCHAR(50)'),
                    ('notes', 'TEXT'),
                    ('created_at', 'TIMESTAMP') 
                ]
                
                for column_name, column_type in columns_to_add:
                    # التحقق إذا كان العمود موجوداً
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'customer_history' 
                        AND column_name = %s
                    """, (column_name,))
                    
                    if not cursor.fetchone():
                        # إضافة العمود إذا لم يكن موجوداً
                        cursor.execute(f"""
                            ALTER TABLE customer_history 
                            ADD COLUMN {column_name} {column_type}
                        """)
                        logger.info(f"تم إضافة العمود {column_name} إلى جدول customer_history")
                        
                        # إذا كان العمود created_at، نقوم بتحديث القيم من performed_at
                        if column_name == 'created_at':
                            cursor.execute("""
                                UPDATE customer_history 
                                SET created_at = performed_at 
                                WHERE created_at IS NULL
                            """)
                            logger.info("تم تحديث قيم created_at من performed_at")
                    else:
                        logger.info(f"العمود {column_name} موجود بالفعل")
                    
                # حذف العمود performed_by إذا كان موجوداً (لإزالة التضارب)
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'customer_history' 
                    AND column_name = 'performed_by'
                """)
                
                if cursor.fetchone():
                    # حذف الفهرس أولاً
                    cursor.execute("DROP INDEX IF EXISTS idx_customer_history_performed_by")
                    # ثم حذف العمود
                    cursor.execute("ALTER TABLE customer_history DROP COLUMN performed_by")
                    logger.info("تم حذف العمود performed_by من جدول customer_history")
                
        except Exception as e:
            logger.error(f"خطأ في تحديث جدول customer_history: {e}")

    def fix_customer_history_numeric_values(self):
        """تصحيح القيم النصية في الأعمدة الرقمية في جدول customer_history"""
        try:
            with db.get_cursor() as cursor:
                # التحقق من نوع البيانات في الأعمدة
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'customer_history' 
                    AND column_name IN ('old_value', 'new_value', 'amount', 'current_balance_after')
                """)
                
                columns_info = cursor.fetchall()
                logger.info(f"معلومات أعمدة customer_history: {columns_info}")
                
                # تحديث القيم النصية إلى رقمية
                cursor.execute("""
                    UPDATE customer_history 
                    SET 
                        old_value = CASE 
                            WHEN old_value IS NULL THEN 0
                            WHEN old_value ~ '^[0-9]+(\\.[0-9]+)?$' THEN CAST(old_value AS DECIMAL(15, 2))
                            ELSE 0 
                        END,
                        new_value = CASE 
                            WHEN new_value IS NULL THEN 0
                            WHEN new_value ~ '^[0-9]+(\\.[0-9]+)?$' THEN CAST(new_value AS DECIMAL(15, 2))
                            ELSE 0 
                        END,
                        amount = CASE 
                            WHEN amount IS NULL THEN 0
                            WHEN amount ~ '^[0-9]+(\\.[0-9]+)?$' THEN CAST(amount AS DECIMAL(15, 2))
                            ELSE 0 
                        END,
                        current_balance_after = CASE 
                            WHEN current_balance_after IS NULL THEN 0
                            WHEN current_balance_after ~ '^[0-9]+(\\.[0-9]+)?$' THEN CAST(current_balance_after AS DECIMAL(15, 2))
                            ELSE 0 
                        END
                    WHERE 
                        old_value !~ '^[0-9]+(\\.[0-9]+)?$' OR 
                        new_value !~ '^[0-9]+(\\.[0-9]+)?$' OR 
                        amount !~ '^[0-9]+(\\.[0-9]+)?$' OR 
                        current_balance_after !~ '^[0-9]+(\\.[0-9]+)?$' OR
                        old_value IS NULL OR
                        new_value IS NULL OR
                        amount IS NULL OR
                        current_balance_after IS NULL
                """)
                
                rows_updated = cursor.rowcount
                if rows_updated > 0:
                    logger.info(f"تم تحديث {rows_updated} صف في جدول customer_history لتصحيح القيم الرقمية")
                else:
                    logger.info("لم تكن هناك حاجة لتحديث القيم الرقمية في جدول customer_history")
                
                # تغيير نوع البيانات للأعمدة إذا كانت لا تزال نصية
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'customer_history' 
                    AND column_name IN ('old_value', 'new_value', 'amount', 'current_balance_after')
                    AND data_type != 'numeric'
                """)
                
                text_columns = cursor.fetchall()
                for column in text_columns:
                    column_name = column['column_name']
                    logger.info(f"تغيير نوع العمود {column_name} من {column['data_type']} إلى numeric")
                    
                    # تغيير نوع العمود إلى numeric
                    cursor.execute(f"""
                        ALTER TABLE customer_history 
                        ALTER COLUMN {column_name} TYPE DECIMAL(15, 2)
                        USING {column_name}::DECIMAL(15, 2)
                    """)
                    
                    logger.info(f"تم تغيير نوع العمود {column_name} إلى DECIMAL(15, 2)")
                    
        except Exception as e:
            logger.error(f"خطأ في تصحيح القيم الرقمية في جدول customer_history: {e}")

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
            
            # جدول الفواتير (مع الأعمدة المحدثة)
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
                notes TEXT,
                
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
            """,
            
            # جدول السجل التاريخي للزبائن - النسخة المحدثة
            """
            CREATE TABLE IF NOT EXISTS customer_history (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
                
                -- معلومات العملية
                action_type VARCHAR(50) NOT NULL,
                transaction_type VARCHAR(50),
                details TEXT,
                notes TEXT,
                
                -- القيم القديمة والجديدة
                old_value DECIMAL(15, 2),
                new_value DECIMAL(15, 2),
                
                -- المبالغ المالية
                amount DECIMAL(15, 2),
                balance_before DECIMAL(15, 2),
                balance_after DECIMAL(15, 2),
                current_balance_before DECIMAL(15, 2),
                current_balance_after DECIMAL(15, 2),
                
                -- معلومات الفاتورة
                kilowatt_amount DECIMAL(10, 2),
                free_kilowatt DECIMAL(10, 2) DEFAULT 0,
                price_per_kilo DECIMAL(10, 2),
                total_amount DECIMAL(15, 2),
                invoice_number VARCHAR(50),
                receipt_number VARCHAR(50),
                
                -- معلومات النظام
                created_by INTEGER REFERENCES users(id),
                performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  
            )
            """
        ]
        
        try:
            with db.get_cursor() as cursor:
                # إنشاء جميع الجداول
                for sql in tables_sql:
                    cursor.execute(sql)
                logger.info("تم إنشاء جميع الجداول بنجاح")
                
                # إضافة البيانات الأساسية
                self.seed_initial_data(cursor)
                
                # إنشاء الفهارس
                self.create_indexes(cursor)
                
        except Exception as e:
            logger.error(f"خطأ في إنشاء الجداول: {e}")
            raise
        finally:
            # تحديث جدول الفواتير بإضافة الأعمدة المفقودة (للتوافق مع الإصدارات القديمة)
            self.update_invoices_table()
            # تحديث جدول سجل الزبائن
            self.update_customer_history_table()
            # إنشاء فهارس إضافية لجدول التاريخ بعد التحديث
            self.create_history_indexes()
            # تصحيح القيم النصية في الأعمدة الرقمية
            self.fix_customer_history_numeric_values()

    def create_history_indexes(self):
        """إنشاء فهارس لجدول التاريخ"""
        try:
            with db.get_cursor() as cursor:
                history_indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_customer_history_customer_id ON customer_history(customer_id);",
                    "CREATE INDEX IF NOT EXISTS idx_customer_history_action_type ON customer_history(action_type);",
                    "CREATE INDEX IF NOT EXISTS idx_customer_history_transaction_type ON customer_history(transaction_type);",
                    "CREATE INDEX IF NOT EXISTS idx_customer_history_performed_at ON customer_history(performed_at DESC);",
                    "CREATE INDEX IF NOT EXISTS idx_customer_history_created_at ON customer_history(created_at DESC);",  # أضفت فهرس لـ created_at
                    "CREATE INDEX IF NOT EXISTS idx_customer_history_created_by ON customer_history(created_by);",
                    "CREATE INDEX IF NOT EXISTS idx_customer_history_invoice_number ON customer_history(invoice_number);",
                    "CREATE INDEX IF NOT EXISTS idx_customer_history_amount ON customer_history(amount);",
                    "CREATE INDEX IF NOT EXISTS idx_customer_history_current_balance_after ON customer_history(current_balance_after);"
                ]
                
                for index_sql in history_indexes:
                    cursor.execute(index_sql)
                
                logger.info("تم إنشاء فهارس جدول التاريخ بنجاح")
                
        except Exception as e:
            logger.error(f"خطأ في إنشاء فهارس التاريخ: {e}")

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
            VALUES ('admin', 'scrypt:32768:8:1$wFnfT6hB9u3xKXqg$afb5fb045f9afab01e2036b5b7b7d4c6c9c6b2e7e6f7a8b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3', 'المسؤول العام', 'admin', '{"all": true}')
            ON CONFLICT (username) DO NOTHING
        """)
        
        # إضافة الإعدادات الافتراضية
        settings = [
            ('printer_ip', '10.10.0.5', 'عنوان IP للطابعة'),
            ('printer_port', '9100', 'منفذ الطابعة'),
            ('default_price_per_kilo', '7200', 'سعر الكيلو الافتراضي'),
            ('company_name', 'شركة الريان للطاقة الكهربائية', 'اسم الشركة'),
            ('company_phone', '0952411882', 'هاتف الشركة'),
            ('company_address', '', 'عنوان الشركة'),
            ('receipt_header', 'شركة الريان للطاقة الكهربائية', 'عنوان الفاتورة الرئيسي'),
            ('receipt_subheader', 'مدينة عريمة - شارع البريد', 'عنوان الفاتورة الفرعي'),
            ('vat_percentage', '0', 'نسبة الضريبة المضافة'),
            ('vat_number', '', 'الرقم الضريبي')
        ]
        
        for key, value, description in settings:
            cursor.execute("""
                INSERT INTO settings (key, value, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO NOTHING
            """, (key, value, description))
                
        # database/models.py - تحديث دالة fix_customer_history_numeric_values فقط

    def fix_customer_history_numeric_values(self):
        """تصحيح القيم النصية في الأعمدة الرقمية في جدول customer_history"""
        try:
            with db.get_cursor() as cursor:
                # التحقق من نوع البيانات في الأعمدة
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'customer_history' 
                    AND column_name IN ('old_value', 'new_value', 'amount', 'current_balance_after')
                """)
                
                columns_info = cursor.fetchall()
                logger.info(f"معلومات أعمدة customer_history: {columns_info}")
                
                # تحديث القيم النصية إلى رقمية للأعمدة التي لا تزال نصية فقط
                for column in columns_info:
                    column_name = column['column_name']
                    data_type = column['data_type']
                    
                    if data_type == 'text':
                        logger.info(f"معالجة العمود النصي: {column_name}")
                        
                        # تحويل القيم النصية إلى رقمية
                        cursor.execute(f"""
                            UPDATE customer_history 
                            SET {column_name} = CASE 
                                WHEN {column_name} IS NULL THEN 0
                                WHEN {column_name} ~ '^[0-9]+(\\.[0-9]+)?$' THEN CAST({column_name} AS DECIMAL(15, 2))
                                ELSE 0 
                            END
                            WHERE {column_name} IS NULL 
                            OR {column_name} !~ '^[0-9]+(\\.[0-9]+)?$'
                            OR {column_name} = ''
                        """)
                        
                        # تغيير نوع العمود إلى numeric
                        try:
                            cursor.execute(f"""
                                ALTER TABLE customer_history 
                                ALTER COLUMN {column_name} TYPE DECIMAL(15, 2)
                                USING {column_name}::DECIMAL(15, 2)
                            """)
                            logger.info(f"تم تغيير نوع العمود {column_name} من text إلى DECIMAL(15, 2)")
                        except Exception as alter_error:
                            logger.warning(f"لا يمكن تغيير نوع العمود {column_name}: {alter_error}")
                    
                    elif data_type == 'numeric':
                        logger.info(f"العمود {column_name} بالفعل من نوع numeric، لا حاجة للتحديث")
                    
                    # التعامل مع القيم الفارغة في الأعمدة الرقمية
                    cursor.execute(f"""
                        UPDATE customer_history 
                        SET {column_name} = 0
                        WHERE {column_name} IS NULL
                    """)
                    
                    rows_updated = cursor.rowcount
                    if rows_updated > 0:
                        logger.info(f"تم تحديث {rows_updated} قيمة فارغة في العمود {column_name}")
                
                logger.info("تم الانتهاء من تصحيح القيم الرقمية في جدول customer_history")
                
        except Exception as e:
            logger.error(f"خطأ في تصحيح القيم الرقمية في جدول customer_history: {e}")
            # لا نرفع الخطأ حتى لا يمنع تشغيل التطبيق        
                    
                
                        
# تأكد أن هذا السطر موجود في النهاية
models = Models()