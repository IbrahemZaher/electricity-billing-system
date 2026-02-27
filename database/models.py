# database/models.py
from database.connection import db
from datetime import datetime
import logging
import json


logger = logging.getLogger(__name__)

class Models:
    def __init__(self):
        self.create_tables()
        self.update_customers_table()  # أضف هذه السطر

    def update_invoices_table(self):
        """تحديث جدول الفواتير بإضافة الأعمدة المفقودة"""
        try:
            with db.get_cursor() as cursor:
                # التحقق من وجود الأعمدة وإضافتها إذا كانت غير موجودة
                columns_to_add = [
                    ('free_kilowatt', 'DECIMAL(10, 2) DEFAULT 0'),
                    ('visa_application', 'VARCHAR(100)'),
                    ('customer_withdrawal', 'VARCHAR(100)'),
                    ('notes', 'TEXT'),
                    ('payment_method', "VARCHAR(20) DEFAULT 'cash'"),
                    ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')   # ← أضف هذا السطر   # العمود الجديد
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

    def create_indexes(self, cursor):
        """إنشاء الفهارس للبحث السريع"""
        try:
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);",
                "CREATE INDEX IF NOT EXISTS idx_customers_box_number ON customers(box_number);",
                "CREATE INDEX IF NOT EXISTS idx_customers_sector_id ON customers(sector_id);",
                "CREATE INDEX IF NOT EXISTS idx_customers_is_active ON customers(is_active);",
                "CREATE INDEX IF NOT EXISTS idx_customers_parent_meter ON customers(parent_meter_id);",
                "CREATE INDEX IF NOT EXISTS idx_customers_meter_type ON customers(meter_type);",

                "CREATE INDEX IF NOT EXISTS idx_invoices_customer_id ON invoices(customer_id);",
                "CREATE INDEX IF NOT EXISTS idx_invoices_payment_date ON invoices(payment_date);",
                "CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number ON invoices(invoice_number);",

                "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
                "CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);",

                "CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON activity_logs(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON activity_logs(created_at);",
                "CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id);"
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
                email VARCHAR(255),              
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
                is_active BOOLEAN DEFAULT TRUE,
                default_generator_id INTEGER REFERENCES customers(id)
            )
            """,
            
            # جدول الزبائن - النسخة المحدثة
            """
            CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY,
                sector_id INTEGER REFERENCES sectors(id),
                box_number VARCHAR(20),
                serial_number VARCHAR(20),
                parent_meter_id INTEGER,  -- أضف هذا العمود
                meter_type VARCHAR(50) DEFAULT 'زبون',  -- أضف هذا العمود
                name VARCHAR(100) NOT NULL,
                phone_number VARCHAR(20),
                telegram_username VARCHAR(50),
                current_balance DECIMAL(15, 2) DEFAULT 0,
                last_counter_reading DECIMAL(15, 2) DEFAULT 0,
                visa_balance DECIMAL(15, 2) DEFAULT 0,
                withdrawal_amount DECIMAL(15, 2) DEFAULT 0,

                financial_category VARCHAR(20) DEFAULT 'normal',
                free_reason TEXT,
                free_amount DECIMAL(15, 2) DEFAULT 0,
                free_remaining DECIMAL(15, 2) DEFAULT 0,
                free_expiry_date DATE, 
                               
                vip_reason TEXT,
                vip_no_cut_days INTEGER DEFAULT 0,
                vip_expiry_date DATE,
                vip_grace_period INTEGER DEFAULT 0,
                notes TEXT,

                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # معلوات التصنيفات
            """
            CREATE TABLE IF NOT EXISTS customer_financial_logs (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
                
                
                old_category VARCHAR(20),
                new_category VARCHAR(20) NOT NULL,
                category_type VARCHAR(10) NOT NULL, -- 'free' أو 'vip' أو 'both'
                
                
                free_reason TEXT,
                free_amount DECIMAL(15, 2),
                free_remaining DECIMAL(15, 2),
                free_expiry_date DATE,
                
                
                vip_reason TEXT,
                vip_no_cut_days INTEGER,
                vip_expiry_date DATE,
                vip_grace_period INTEGER,
                
                
                changed_by INTEGER REFERENCES users(id),
                change_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            """,
            # جدول كتالوج الصلاحيات
            """
            CREATE TABLE IF NOT EXISTS permissions_catalog (
                id SERIAL PRIMARY KEY,
                permission_key VARCHAR(100) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                category VARCHAR(50),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,

            # جدول صلاحيات الأدوار
            """
            CREATE TABLE IF NOT EXISTS role_permissions (
                id SERIAL PRIMARY KEY,
                role VARCHAR(20) NOT NULL,
                permission_key VARCHAR(100) NOT NULL,
                is_allowed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(role, permission_key)
            )
            """,

            # جدول صلاحيات المستخدمين (للتجاوزات)
            """
            CREATE TABLE IF NOT EXISTS user_permissions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                permission_key VARCHAR(100) NOT NULL,
                is_allowed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, permission_key)
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
            # تحديث جدول المستخدمين
            self.update_users_table()
            # تحديث جدول الزبائن
            self.update_customers_table()
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
                    "CREATE INDEX IF NOT EXISTS idx_customer_history_created_at ON customer_history(created_at DESC);",
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
        
        # استيراد auth داخل الدالة لتجنب الاستيرادات الدائرية
        from auth.authentication import auth
        # إضافة المستخدم الإداري الافتراضي (كلمة المرور: admin)
        admin_password = 'admin'
        admin_hash = auth.hash_password(admin_password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, role, permissions)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
        """, (
            'admin',
            admin_hash,  # ✅ استخدام الهاش المولد ديناميكياً
            'المسؤول العام',
            'admin',
            '{"all": true}'
        ))
        
        # إضافة الصلاحيات إلى الكتالوج
        permissions_data = [
            # فئة الزبائن
            ('customers.view', 'عرض الزبائن', 'customers'),
            ('customers.add', 'إضافة زبون جديد', 'customers'),
            ('customers.edit', 'تعديل الزبائن', 'customers'),
            ('customers.delete', 'حذف الزبائن', 'customers'),
            ('customers.view_details', 'عرض تفاصيل الزبون', 'customers'),
            ('customers.view_history', 'عرض السجل التاريخي', 'customers'),
            ('customers.manage_sectors', 'إدارة قطاعات الزبائن', 'customers'),
            ('customers.reimport', 'حذف وإعادة الاستيراد', 'customers'),
            ('customers.export', 'تصدير بيانات الزبائن', 'customers'),
            ('customers.import_visas', 'استيراد تأشيرات الزبائن', 'customers'),
            
            # فئة الفواتير
            ('invoices.view', 'عرض الفواتير', 'invoices'),
            ('invoices.create', 'إنشاء فواتير جديدة', 'invoices'),
            ('invoices.edit', 'تعديل الفواتير', 'invoices'),
            ('invoices.delete', 'حذف الفواتير', 'invoices'),
            ('invoices.cancel', 'إلغاء الفواتير', 'invoices'),
            ('invoices.print', 'طباعة الفواتير', 'invoices'),
            ('invoices.print_without_balance', 'طباعة بدون رصيد', 'invoices'),
            ('invoices.fast_process', 'معالجة سريعة', 'invoices'),
            ('invoices.view_daily_summary', 'عرض ملخص اليوم', 'invoices'),
            
            # فئة التقارير
            ('reports.view', 'عرض التقارير', 'reports'),
            ('reports.dashboard', 'لوحة التحكم', 'reports'),
            ('reports.customers', 'تقارير الزبائن', 'reports'),
            ('reports.balance', 'تقارير الرصيد', 'reports'),
            ('reports.sales', 'تقارير المبيعات', 'reports'),
            ('reports.sectors', 'تقارير القطاعات', 'reports'),
            ('reports.export', 'تصدير التقارير', 'reports'),
            ('waste_analysis.view', 'عرض تحليل الهدر', 'reports'),
            ('reports.view_collections', 'عرض تقرير جبايات المحاسب', 'reports'),
            
            # فئة النظام
            ('system.manage_users', 'إدارة المستخدمين', 'system'),
            ('system.view_activity_log', 'عرض سجل النشاط', 'system'),
            ('system.manage_backup', 'إدارة النسخ الاحتياطي', 'system'),
            ('system.import_data', 'استيراد البيانات', 'system'),
            ('system.export_data', 'تصدير البيانات', 'system'),
            ('system.advanced_import', 'استيراد متقدم', 'system'),
            ('system.advanced_export', 'تصدير متقدم', 'system'),
            ('system.view_archive', 'عرض الأرشيف', 'system'),
            
            # فئة الإعدادات
            ('settings.manage', 'إدارة الإعدادات', 'settings'),
            ('settings.manage_permissions', 'إدارة الصلاحيات', 'settings'),
            ('settings.printer', 'إعدادات الطابعة', 'settings'),
            
            # فئة المحاسبة
            ('accounting.access', 'الدخول لوحدة المحاسبة', 'accounting'),
            ('accounting.fast_operations', 'عمليات محاسبية سريعة', 'accounting'),
            # إضافة صلاحيات في قسم permissions_data
            ('customers.manage_financial_categories', 'إدارة التصنيفات المالية', 'customers'),
            ('customers.view_financial_reports', 'عرض تقارير التصنيفات المالية', 'reports'),
            ('invoices.apply_free_discount', 'تطبيق خصم المجاني', 'invoices'),
            ('system.manage_vip_protection', 'إدارة حماية VIP', 'system'),
            # أضف هذا السطر في permissions_data ضمن seed_initial_data
            ('customers.manage_children', 'إدارة الأبناء (العدادات التابعة)', 'customers'),
            ('customers.view_balance_stats', 'عرض إحصائيات لنا/علينا', 'customers'),
        ]

        for permission_key, name, category in permissions_data:
            cursor.execute("""
                INSERT INTO permissions_catalog (permission_key, name, category)
                VALUES (%s, %s, %s)
                ON CONFLICT (permission_key) DO UPDATE
                SET name = EXCLUDED.name,
                    category = EXCLUDED.category,
                    is_active = TRUE
            """, (permission_key, name, category))

        # إضافة صلاحيات الأدوار الافتراضية
        role_permissions = {
            'admin': ['*.*'],  # جميع الصلاحيات
            
            'accountant': [
                'customers.view',  
                'customers.view_details', 'invoices.view',
               'invoices.print', 'reports.view', 'reports.dashboard',
                'reports.customers', 'reports.balance', 'reports.sales', 'system.import_data',
                'system.export_data','reports.view_collections'
            ],
            
            'cashier': [
                'customers.view', 'invoices.view', 'invoices.create', 'invoices.print',
                'accounting.access', 'accounting.fast_operations'
            ],
            
            'viewer': [
                'customers.view', 'reports.view'
            ]
        }

        for role, permissions in role_permissions.items():
            for permission_key in permissions:
                cursor.execute("""
                    INSERT INTO role_permissions (role, permission_key, is_allowed)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (role, permission_key) DO UPDATE
                    SET is_allowed = EXCLUDED.is_allowed,
                        updated_at = CURRENT_TIMESTAMP
                """, (role, permission_key, True))
        
        # إضافة الإعدادات الافتراضية
        settings = [
            ('printer_ip', '10.10.0.4', 'عنوان IP للطابعة'),
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

    def update_users_table(self):
        """تحديث جدول المستخدمين بإضافة الأعمدة المفقودة"""
        try:
            with db.get_cursor() as cursor:
                # التحقق من وجود عمود email وإضافته إذا لم يكن موجوداً
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND column_name = 'email'
                """)
                
                if not cursor.fetchone():
                    # إضافة العمود إذا لم يكن موجوداً
                    cursor.execute("""
                        ALTER TABLE users 
                        ADD COLUMN email VARCHAR(255)
                    """)
                    logger.info("تم إضافة العمود email إلى جدول users")
                else:
                    logger.info("العمود email موجود بالفعل في جدول users")
                
        except Exception as e:
            logger.error(f"خطأ في تحديث جدول users: {e}")

    # ======= الدوال المضافة من الملف القديم =======

    def get_customer_count_for_sector(self, sector_id):
        """الحصول على عدد الزبائن في قطاع معين"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM customers 
                    WHERE sector_id = %s AND is_active = TRUE
                """, (sector_id,))
                result = cursor.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            logger.error(f"خطأ في الحصول على عدد زبائن القطاع: {e}")
            return 0

    def get_customer_count(self):
        """الحصول على إجمالي عدد الزبائن النشطين"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM customers 
                    WHERE is_active = TRUE
                """)
                result = cursor.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            logger.error(f"خطأ في الحصول على عدد الزبائن: {e}")
            return 0

    def get_sectors_with_counts(self):
        """الحصول على جميع القطاعات مع عدد الزبائن في كل قطاع"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT s.*, 
                           COUNT(c.id) as customer_count,
                           COALESCE(SUM(c.current_balance), 0) as total_balance
                    FROM sectors s
                    LEFT JOIN customers c ON s.id = c.sector_id AND c.is_active = TRUE
                    WHERE s.is_active = TRUE
                    GROUP BY s.id
                    ORDER BY s.name
                """)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"خطأ في الحصول على القطاعات مع العداد: {e}")
            return []

    def get_total_current_balance(self):
        """الحصول على إجمالي الرصيد الحالي لجميع الزبائن"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT COALESCE(SUM(current_balance), 0) as total_balance
                    FROM customers 
                    WHERE is_active = TRUE
                """)
                result = cursor.fetchone()
                return result['total_balance'] if result else 0
        except Exception as e:
            logger.error(f"خطأ في الحصول على إجمالي الرصيد: {e}")
            return 0

    def get_daily_summary(self, date=None):
        """الحصول على ملخص المبيعات ليوم معين"""
        try:
            if date is None:
                date = datetime.now().date()
                
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as invoice_count,
                        COALESCE(SUM(kilowatt_amount), 0) as total_kilowatt,
                        COALESCE(SUM(total_amount), 0) as total_amount,
                        COALESCE(SUM(discount), 0) as total_discount,
                        COALESCE(SUM(free_kilowatt), 0) as total_free_kilowatt
                    FROM invoices
                    WHERE DATE(payment_date) = %s
                    AND status = 'active'
                """, (date,))
                
                result = cursor.fetchone()
                return {
                    'invoice_count': result['invoice_count'] if result else 0,
                    'total_kilowatt': float(result['total_kilowatt']) if result else 0,
                    'total_amount': float(result['total_amount']) if result else 0,
                    'total_discount': float(result['total_discount']) if result else 0,
                    'total_free_kilowatt': float(result['total_free_kilowatt']) if result else 0,
                    'date': date
                }
        except Exception as e:
            logger.error(f"خطأ في الحصول على ملخص اليوم: {e}")
            return {
                'invoice_count': 0,
                'total_kilowatt': 0,
                'total_amount': 0,
                'total_discount': 0,
                'total_free_kilowatt': 0,
                'date': date
            }

    def get_monthly_summary(self, year=None, month=None):
        """الحصول على ملخص المبيعات لشهر معين"""
        try:
            if year is None or month is None:
                now = datetime.now()
                year = now.year
                month = now.month
                
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        DATE(payment_date) as sale_date,
                        COUNT(*) as invoice_count,
                        COALESCE(SUM(kilowatt_amount), 0) as total_kilowatt,
                        COALESCE(SUM(total_amount), 0) as total_amount,
                        COALESCE(SUM(discount), 0) as total_discount
                    FROM invoices
                    WHERE EXTRACT(YEAR FROM payment_date) = %s
                      AND EXTRACT(MONTH FROM payment_date) = %s
                      AND status = 'active'
                    GROUP BY DATE(payment_date)
                    ORDER BY sale_date
                """, (year, month))
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"خطأ في الحصول على ملخص الشهر: {e}")
            return []

    def get_top_customers(self, limit=10, order_by='balance'):
        """الحصول على أفضل الزبائن حسب المعيار المحدد"""
        try:
            with db.get_cursor() as cursor:
                if order_by == 'balance':
                    order_clause = "ORDER BY current_balance DESC"
                elif order_by == 'purchases':
                    order_clause = """
                        ORDER BY purchase_count DESC, total_purchased DESC
                    """
                else:
                    order_clause = "ORDER BY c.name"
                
                cursor.execute(f"""
                    SELECT 
                        c.id,
                        c.name,
                        c.box_number,
                        c.current_balance,
                        s.name as sector_name,
                        COUNT(i.id) as purchase_count,
                        COALESCE(SUM(i.total_amount), 0) as total_purchased,
                        COALESCE(SUM(i.kilowatt_amount), 0) as total_kilowatt
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    LEFT JOIN invoices i ON c.id = i.customer_id 
                        AND i.status = 'active'
                    WHERE c.is_active = TRUE
                    GROUP BY c.id, c.name, c.box_number, c.current_balance, s.name
                    {order_clause}
                    LIMIT %s
                """, (limit,))
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"خطأ في الحصول على أفضل الزبائن: {e}")
            return []

    def search_customers(self, search_term, limit=50):
        """بحث عن الزبائن باستخدام مصطلح بحث"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        c.*,
                        s.name as sector_name,
                        s.code as sector_code
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.is_active = TRUE
                      AND (
                        c.name ILIKE %s OR
                        c.box_number ILIKE %s OR
                        c.serial_number ILIKE %s OR
                        c.phone_number ILIKE %s OR
                        s.name ILIKE %s
                      )
                    ORDER BY c.name
                    LIMIT %s
                """, (f'%{search_term}%', f'%{search_term}%', 
                      f'%{search_term}%', f'%{search_term}%', 
                      f'%{search_term}%', limit))
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"خطأ في بحث الزبائن: {e}")
            return []

    def get_invoice_by_number(self, invoice_number):
        """الحصول على فاتورة باستخدام رقم الفاتورة"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        i.*,
                        c.name as customer_name,
                        c.box_number,
                        c.serial_number,
                        c.phone_number,
                        s.name as sector_name,
                        u.full_name as user_name
                    FROM invoices i
                    LEFT JOIN customers c ON i.customer_id = c.id
                    LEFT JOIN sectors s ON i.sector_id = s.id
                    LEFT JOIN users u ON i.user_id = u.id
                    WHERE i.invoice_number = %s
                    AND i.status = 'active'
                """, (invoice_number,))
                
                result = cursor.fetchone()
                return result
        except Exception as e:
            logger.error(f"خطأ في الحصول على الفاتورة: {e}")
            return None

    def get_customer_invoices(self, customer_id, limit=100):
        """الحصول على فواتير زبون معين"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        i.*,
                        s.name as sector_name,
                        u.full_name as user_name
                    FROM invoices i
                    LEFT JOIN sectors s ON i.sector_id = s.id
                    LEFT JOIN users u ON i.user_id = u.id
                    WHERE i.customer_id = %s
                    AND i.status = 'active'
                    ORDER BY i.payment_date DESC, i.payment_time DESC
                    LIMIT %s
                """, (customer_id, limit))
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"خطأ في الحصول على فواتير الزبون: {e}")
            return []

    def get_recent_invoices(self, days=7, limit=100):
        """الحصول على الفواتير الحديثة"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        i.*,
                        c.name as customer_name,
                        c.box_number,
                        s.name as sector_name,
                        u.full_name as user_name
                    FROM invoices i
                    LEFT JOIN customers c ON i.customer_id = c.id
                    LEFT JOIN sectors s ON i.sector_id = s.id
                    LEFT JOIN users u ON i.user_id = u.id
                    WHERE i.payment_date >= CURRENT_DATE - INTERVAL '%s days'
                    AND i.status = 'active'
                    ORDER BY i.payment_date DESC, i.payment_time DESC
                    LIMIT %s
                """, (days, limit))
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"خطأ في الحصول على الفواتير الحديثة: {e}")
            return []

    def get_user_permissions(self, user_id):
        """الحصول على صلاحيات مستخدم معين"""
        try:
            with db.get_cursor() as cursor:
                # الحصول على دور المستخدم
                cursor.execute("""
                    SELECT role FROM users WHERE id = %s
                """, (user_id,))
                user = cursor.fetchone()
                
                if not user:
                    return {}
                
                role = user['role']
                
                # إذا كان المستخدم مديراً، نعطيه جميع الصلاحيات
                if role == 'admin':
                    return {'*.*': True}
                
                # الحصول على صلاحيات الدور
                cursor.execute("""
                    SELECT permission_key 
                    FROM role_permissions 
                    WHERE role = %s AND is_allowed = TRUE
                """, (role,))
                
                role_permissions = {row['permission_key']: True for row in cursor.fetchall()}
                
                # الحصول على صلاحيات المستخدم الفردية (للتجاوزات)
                cursor.execute("""
                    SELECT permission_key, is_allowed
                    FROM user_permissions
                    WHERE user_id = %s
                """, (user_id,))
                
                user_permissions = {row['permission_key']: row['is_allowed'] for row in cursor.fetchall()}
                
                # دمج الصلاحيات (صلاحيات المستخدم تتجاوز صلاحيات الدور)
                permissions = {**role_permissions, **user_permissions}
                
                return permissions
                
        except Exception as e:
            logger.error(f"خطأ في الحصول على صلاحيات المستخدم: {e}")
            return {}

    def check_permission(self, user_id, permission_key):
        """التحقق من صلاحية مستخدم معينة"""
        try:
            permissions = self.get_user_permissions(user_id)
            
            # إذا كانت هناك صلاحية عامة (*.*) فيتم السماح بكل شيء
            if '*.*' in permissions and permissions['*.*']:
                return True
            
            # التحقق من الصلاحية المحددة
            return permissions.get(permission_key, False)
            
        except Exception as e:
            logger.error(f"خطأ في التحقق من الصلاحية: {e}")
            return False

    def log_activity(self, user_id, action_type, description, ip_address=None, user_agent=None):
        """تسجيل نشاط في سجل النشاطات"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO activity_logs 
                    (user_id, action_type, description, ip_address, user_agent)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, action_type, description, ip_address, user_agent))
                
                return True
        except Exception as e:
            logger.error(f"خطأ في تسجيل النشاط: {e}")
            return False

    def get_activity_logs(self, user_id=None, action_type=None, days=30, limit=100):
        """الحصول على سجل النشاطات"""
        try:
            with db.get_cursor() as cursor:
                query = """
                    SELECT 
                        al.*,
                        u.username,
                        u.full_name
                    FROM activity_logs al
                    LEFT JOIN users u ON al.user_id = u.id
                    WHERE al.created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                """
                params = [days]
                
                if user_id:
                    query += " AND al.user_id = %s"
                    params.append(user_id)
                
                if action_type:
                    query += " AND al.action_type = %s"
                    params.append(action_type)
                
                query += " ORDER BY al.created_at DESC LIMIT %s"
                params.append(limit)
                
                cursor.execute(query, params)
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"خطأ في الحصول على سجل النشاطات: {e}")
            return []

    def archive_invoice(self, invoice_id, user_id, reason="أرشفة يدوية"):
        """أرشفة فاتورة معينة"""
        try:
            with db.get_cursor() as cursor:
                # الحصول على بيانات الفاتورة الأصلية
                cursor.execute("""
                    SELECT * FROM invoices WHERE id = %s
                """, (invoice_id,))
                
                invoice_data = cursor.fetchone()
                
                if not invoice_data:
                    return False
                
                # تحويل بيانات الفاتورة إلى JSON
                invoice_json = json.dumps(dict(invoice_data), default=str)
                
                # إضافة إلى جدول الأرشيف
                cursor.execute("""
                    INSERT INTO invoice_archive 
                    (original_invoice_id, invoice_data, archived_by, archive_reason)
                    VALUES (%s, %s, %s, %s)
                """, (invoice_id, invoice_json, user_id, reason))
                
                # تحديث حالة الفاتورة الأصلية
                cursor.execute("""
                    UPDATE invoices 
                    SET status = 'archived', archived_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (invoice_id,))
                
                return True
                
        except Exception as e:
            logger.error(f"خطأ في أرشفة الفاتورة: {e}")
            return False

    def get_setting(self, key, default=None):
        """الحصول على إعداد من جدول الإعدادات"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT value FROM settings WHERE key = %s
                """, (key,))
                
                result = cursor.fetchone()
                return result['value'] if result else default
        except Exception as e:
            logger.error(f"خطأ في الحصول على الإعداد: {e}")
            return default

    def update_setting(self, key, value):
        """تحديث أو إضافة إعداد في جدول الإعدادات"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO settings (key, value) 
                    VALUES (%s, %s)
                    ON CONFLICT (key) 
                    DO UPDATE SET value = EXCLUDED.value, 
                                 updated_at = CURRENT_TIMESTAMP
                """, (key, value))
                
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث الإعداد: {e}")
            return False


    def update_customers_table(self):
        """تحديث جدول customers بإضافة الحقول الجديدة"""
        try:
            with db.get_cursor() as cursor:
                # التحقق من وجود الحقول الجديدة وإضافتها إذا لم تكن موجودة
                new_columns = [
                    ('financial_category', "VARCHAR(20) DEFAULT 'normal'"),
                    ('free_reason', 'TEXT'),
                    ('free_amount', 'DECIMAL(15, 2) DEFAULT 0'),
                    ('free_remaining', 'DECIMAL(15, 2) DEFAULT 0'),
                    ('free_expiry_date', 'DATE'),
                    ('vip_reason', 'TEXT'),
                    ('vip_no_cut_days', 'INTEGER DEFAULT 0'),
                    ('vip_expiry_date', 'DATE'),
                    ('vip_grace_period', 'INTEGER DEFAULT 0'),
                    ('parent_meter_id', 'INTEGER'),
                    ('meter_type', "VARCHAR(50) DEFAULT 'زبون'"),
                    ('default_generator_id', 'INTEGER REFERENCES customers(id)'),  # أضف هذا العمود
                ]
                
                for column_name, column_type in new_columns:
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'customers' 
                        AND column_name = %s
                    """, (column_name,))
                    
                    if not cursor.fetchone():
                        cursor.execute(f"""
                            ALTER TABLE customers 
                            ADD COLUMN {column_name} {column_type}
                        """)
                        logger.info(f"تم إضافة العمود {column_name} إلى جدول customers")
                        
        except Exception as e:
            logger.error(f"خطأ في تحديث جدول customers: {e}")


# إنشاء كائن Models
models = Models()