# database/models.py
from database.connection import db
from datetime import datetime
import logging
import json


logger = logging.getLogger(__name__)

class Models:
    def __init__(self):
        self.create_tables()
        self.update_profit_distribution_table()
        self.update_energy_tables()
        self.update_customers_table()
        self.update_daily_expenses_table()   # <--- أضف هذا السطر هنا
        self.update_daily_cash_add_energy_profits()   # <--- أضف هذا السطر
        self.update_energy_meters_for_accounts()
        self.create_energy_account_tables()
        self.update_daily_cash_add_fuel_column()
        self.update_energy_meters_for_accounts()
        self.create_energy_account_tables()                    

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
                    ('created_at', 'TIMESTAMP'),
                    # 👇 أضف هذه الأسطر الثلاثة الجديدة
                    ('snapshot_withdrawal_amount', 'DECIMAL(15, 2)'),
                    ('snapshot_visa_balance', 'DECIMAL(15, 2)'),
                    ('snapshot_last_counter_reading', 'DECIMAL(15, 2)'),
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
                "CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id);",

                # فهارس جداول الطاقة
                "CREATE INDEX IF NOT EXISTS idx_energy_meters_name ON energy_meters(name);",
                "CREATE INDEX IF NOT EXISTS idx_energy_daily_readings_date ON energy_daily_readings(reading_date);",
                "CREATE INDEX IF NOT EXISTS idx_energy_daily_readings_meter ON energy_daily_readings(meter_id);",
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- الأعمدة الجديدة للقطة
                snapshot_withdrawal_amount DECIMAL(15, 2),
                snapshot_visa_balance DECIMAL(15, 2),
                snapshot_last_counter_reading DECIMAL(15, 2)
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
            """,
            # في قائمة tables_sql (داخل create_tables)، أضف ما يلي:

            # ... (بعد جدول user_permissions مثلاً)

            # جدول سجل عمليات التحصيل الميداني
            """
            CREATE TABLE IF NOT EXISTS collection_logs (
                id SERIAL PRIMARY KEY,
                collector_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
                collection_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                collected_amount DECIMAL(15, 2) NOT NULL,
                expected_amount DECIMAL(15, 2),
                notes TEXT,
                location_lat DECIMAL(10, 8),
                location_lon DECIMAL(11, 8),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,

            # جدول أهداف الأداء اليومية/الشهرية
            """
            CREATE TABLE IF NOT EXISTS collector_targets (
                id SERIAL PRIMARY KEY,
                collector_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                target_date DATE NOT NULL,
                target_amount DECIMAL(15, 2) NOT NULL,
                achieved_amount DECIMAL(15, 2) DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # ... داخل دالة create_tables، بعد جدول collector_targets ...

            # جداول إدارة المازوت ونسب التحويل
            """
            CREATE TABLE IF NOT EXISTS generator_meters (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                code VARCHAR(50) UNIQUE,
                notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sector_meters (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                code VARCHAR(50) UNIQUE,
                sector_id INTEGER REFERENCES sectors(id) ON DELETE SET NULL,
                notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS fuel_tanks (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                liters_per_cm DECIMAL(10,2) NOT NULL DEFAULT 10.75,
                notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS fuel_purchases (
                id SERIAL PRIMARY KEY,
                purchase_date DATE NOT NULL DEFAULT CURRENT_DATE,
                quantity_liters DECIMAL(15,2) NOT NULL,
                price_per_liter DECIMAL(15,2) NOT NULL,
                total_cost DECIMAL(15,2) GENERATED ALWAYS AS (quantity_liters * price_per_liter) STORED,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS fuel_transfers (
                id SERIAL PRIMARY KEY,
                transfer_date DATE NOT NULL DEFAULT CURRENT_DATE,
                tank_id INTEGER NOT NULL REFERENCES fuel_tanks(id),
                quantity_liters DECIMAL(15,2) NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS daily_readings (
                id SERIAL PRIMARY KEY,
                reading_date DATE NOT NULL UNIQUE,
                generator_readings JSONB NOT NULL,     -- {meter_id: reading}
                sector_readings JSONB NOT NULL,        -- {meter_id: reading}
                tank_readings JSONB NOT NULL,          -- {tank_id: reading_cm}
                energy_readings JSONB,                 -- {meter_id: reading} (اختياري، أسبوعي)
                generator_output DECIMAL(15,2),
                sector_output DECIMAL(15,2),
                total_fuel_burned DECIMAL(15,2),
                generator_efficiency DECIMAL(10,4),    -- نسبة تحويل المولدات
                sector_efficiency DECIMAL(10,4),       -- نسبة تحويل القطاعات
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS weekly_inventory (
                id SERIAL PRIMARY KEY,
                cycle_name VARCHAR(100) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                total_generator_output DECIMAL(15,2),
                total_sector_output DECIMAL(15,2),
                total_fuel_burned DECIMAL(15,2),
                avg_generator_efficiency DECIMAL(10,4),
                avg_sector_efficiency DECIMAL(10,4),
                tank_final_readings JSONB,              -- {tank_id: final_cm, final_liters}
                warehouse_remaining_liters DECIMAL(15,2),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # جداول عدادات الطاقة
            """
            CREATE TABLE IF NOT EXISTS energy_meters (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                code VARCHAR(50),
                notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS energy_daily_readings (
                id SERIAL PRIMARY KEY,
                reading_date DATE NOT NULL,
                meter_id INTEGER NOT NULL REFERENCES energy_meters(id) ON DELETE CASCADE,
                reading_value NUMERIC(12,2) NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(reading_date, meter_id)
            )
            """,

            # ✅ جدول مالكي الشركة (لأرباح المدراء) - جديد مع قيد UNIQUE
            """
            CREATE TABLE IF NOT EXISTS company_owners (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,

            # ... بعد الجداول الموجودة وقبل `# إنشاء الفهارس`

            # جداول دفتر اليومية المتكامل - معدلة (profit_distribution تستخدم owner_id)
            """
            CREATE TABLE IF NOT EXISTS expense_categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                arabic_name VARCHAR(100) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS daily_expenses (
                id SERIAL PRIMARY KEY,
                daily_cash_id INTEGER NOT NULL,
                category_id INTEGER REFERENCES expense_categories(id),
                amount DECIMAL(15,2) NOT NULL,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS profit_distribution (
                id SERIAL PRIMARY KEY,
                daily_cash_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL REFERENCES company_owners(id) ON DELETE RESTRICT,
                amount DECIMAL(15,2) NOT NULL,
                profit_type VARCHAR(20) DEFAULT 'manager',
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS daily_cash (
                id SERIAL PRIMARY KEY,
                cash_date DATE NOT NULL UNIQUE,
                opening_balance DECIMAL(15,2) NOT NULL,
                total_collections DECIMAL(15,2) DEFAULT 0,
                total_expenses DECIMAL(15,2) DEFAULT 0,
                total_profits DECIMAL(15,2) DEFAULT 0,
                closing_balance DECIMAL(15,2) NOT NULL,
                status VARCHAR(20) DEFAULT 'draft',
                created_by INTEGER REFERENCES users(id),
                updated_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS daily_collections_detail (
                id SERIAL PRIMARY KEY,
                daily_cash_id INTEGER NOT NULL,
                collector_id INTEGER REFERENCES users(id),
                collector_name VARCHAR(100),
                total_collected DECIMAL(15,2) NOT NULL,
                invoice_count INTEGER DEFAULT 0
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS daily_cash_audit (
                id SERIAL PRIMARY KEY,
                daily_cash_id INTEGER NOT NULL,
                action_type VARCHAR(20),
                old_data JSONB,
                new_data JSONB,
                changed_by INTEGER REFERENCES users(id),
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """

            CREATE TABLE IF NOT EXISTS weekly_cash_inventory (
                id SERIAL PRIMARY KEY,
                week_start DATE NOT NULL,
                week_end DATE NOT NULL,
                total_opening DECIMAL(15,2),
                total_collections DECIMAL(15,2),
                total_expenses DECIMAL(15,2),
                total_repair_expansion DECIMAL(15,2) DEFAULT 0,
                total_energy_profits DECIMAL(15,2) DEFAULT 0,
                total_fuel DECIMAL(15,2) DEFAULT 0,
                total_profits DECIMAL(15,2),
                total_closing DECIMAL(15,2),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # جدول الموظفين
            """
            CREATE TABLE IF NOT EXISTS employees (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                base_salary DECIMAL(15,2) NOT NULL DEFAULT 0,
                hire_date DATE,
                notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
                        # جدول الرواتب الأساسية للموظفين
            """
            CREATE TABLE IF NOT EXISTS employee_salaries (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                base_salary DECIMAL(15,2) NOT NULL,
                effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, effective_date)
            )
            """,

            # جدول السلف
            """
            CREATE TABLE IF NOT EXISTS employee_advances (
                id SERIAL PRIMARY KEY,
                employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
                amount DECIMAL(15,2) NOT NULL,
                advance_date DATE NOT NULL DEFAULT CURRENT_DATE,
                reason TEXT,
                repaid BOOLEAN DEFAULT FALSE,
                repaid_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,

            # جدول دفعات الرواتب (لربطها مع دفتر اليومية)
            """
            CREATE TABLE IF NOT EXISTS salary_payments (
                id SERIAL PRIMARY KEY,
                employee_id INTEGER NOT NULL REFERENCES employees(id),
                payment_date DATE NOT NULL,
                base_salary DECIMAL(15,2) NOT NULL,
                total_advances DECIMAL(15,2) DEFAULT 0,
                net_salary DECIMAL(15,2) NOT NULL,
                daily_cash_id INTEGER REFERENCES daily_cash(id),
                notes TEXT,
                created_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,

            # ... تابع إنشاء الفهارس            
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
            self.update_daily_expenses_table()   # <--- أضف هنا أيضاً
            self.update_daily_cash_add_energy_profits()   # <--- أضف هنا
            self.update_profit_distribution_add_user_id()          # <-- أضف
            self.update_energy_profit_distribution_add_user_id()   # <-- أضف
            self.update_weekly_cash_inventory_table()   # <-- أضف هنا

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
        # داخل seed_initial_data
        # إضافة تصنيفات المصروفات
        expense_cats = [
            ('food', 'شراب وطعام'),
            ('salaries', 'رواتب'),
            ('advances', 'سلف'),
            ('office', 'مصاريف مكتب وإدارية'),
            ('repair', 'إصلاح'),
            ('expansion', 'توسعة'),
            ('energy', 'طاقة'),
            ('fuel', 'مازوت')
        ]
        for code, name in expense_cats:
            cursor.execute("""
                INSERT INTO expense_categories (name, arabic_name)
                VALUES (%s, %s)
                ON CONFLICT (name) DO NOTHING
            """, (code, name))        
        
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
            # ... المحاسبة الجوالة
            ('mobile.view', 'عرض المحاسبة الجوالة', 'mobile'),
            ('mobile.collect', 'تسجيل تحصيل ميداني', 'mobile'),
            ('mobile.reports', 'تقارير أداء المحصلين', 'mobile'),
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
            ],
            'collector': [
                'mobile.view',
                'mobile.collect',
                'customers.view', 
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
        
        # ✅ إضافة الإعدادات الافتراضية (بما فيها initial_cash_balance)
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
            ('vat_number', '', 'الرقم الضريبي'),
            ('initial_cash_balance', '0', 'الرصيد الافتتاحي لأول يوم في النظام'),  # ✅ جديد
        ]
        
        for key, value, description in settings:
            cursor.execute("""
                INSERT INTO settings (key, value, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO NOTHING
            """, (key, value, description))

        # ✅ إضافة المدراء الافتراضيين - مع منع التكرار (لن يتم إدراجهم إذا تم حذفهم لاحقاً)
        # باستخدام ON CONFLICT DO NOTHING، لكن إذا حذف المدير يدوياً، لن يعود تلقائياً.
        # إذا أردت منع عودتهم نهائياً بعد الحذف، يمكن إضافة شرط EXISTS.
        # لكن الأبسط: نضيفهم فقط إذا لم يكونوا موجودين من قبل.
        #owners = ['أحمد كساب', 'محمد كساب', 'ياسر كساب']
        #  for owner in owners:
        #   #    cursor.execute("""
        #        INSERT INTO company_owners (name)
        #   #        SELECT %s
        #   #        WHERE NOT EXISTS (SELECT 1 FROM company_owners WHERE name = %s)
        #    """, (owner, owner))

    def update_users_table(self):
        """تحديث جدول المستخدمين بإضافة الأعمدة المفقودة وتحديث قيم الدور"""
        try:
            with db.get_cursor() as cursor:
                # ---------- إضافة عمود email إذا لم يكن موجوداً ----------
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND column_name = 'email'
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
                    logger.info("تم إضافة العمود email إلى جدول users")
                else:
                    logger.info("العمود email موجود بالفعل في جدول users")

                # ---------- تحديث قيد CHECK على عمود role ----------
                # حذف القيد القديم إذا كان موجوداً (الاسم المفترض: users_role_check)
                cursor.execute("""
                    DO $$
                    BEGIN
                        IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'users_role_check') THEN
                            ALTER TABLE users DROP CONSTRAINT users_role_check;
                        END IF;
                    END $$;
                """)
                # إضافة القيد الجديد بالقيم المحدثة (admin, accountant, cashier, viewer, collector)
                cursor.execute("""
                    ALTER TABLE users
                    ADD CONSTRAINT users_role_check
                    CHECK (role IN ('admin', 'accountant', 'cashier', 'viewer', 'collector'))
                """)
                logger.info("تم تحديث قيد role في جدول users ليشمل collector")

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

    def ensure_fuel_tables(self):
        """إنشاء جداول إدارة المازوت إذا لم تكن موجودة (للتحديث اليدوي)"""
        with db.get_cursor() as cursor:
            # يمكنك استدعاء نفس SQL أعلاه هنا، لكن الأسهل تشغيلها من create_tables
            pass            

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
                    ('default_generator_id', 'INTEGER REFERENCES customers(id)'),
                    # الأعمدة الجديدة للسحب القديم وتوقيت التحديث
                    ('previous_withdrawal', 'DECIMAL(15, 2) DEFAULT 0'),
                    ('withdrawal_updated_at', 'TIMESTAMP'),
                    ('assigned_collector_id', 'INTEGER REFERENCES users(id)'),
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
                        
                # تعيين قيمة افتراضية للصفوف الموجودة في withdrawal_updated_at
                cursor.execute("""
                    UPDATE customers 
                    SET withdrawal_updated_at = CURRENT_TIMESTAMP 
                    WHERE withdrawal_updated_at IS NULL
                """)
                
        except Exception as e:
            logger.error(f"خطأ في تحديث جدول customers: {e}")

    def update_profit_distribution_table(self):
        """تحديث جدول profit_distribution إلى الهيكل الصحيح (باستخدام owner_id وإضافة profit_type)"""
        try:
            with db.get_cursor() as cursor:
                # 1. التحقق من وجود الجدول أصلاً
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'profit_distribution'
                    )
                """)
                if not cursor.fetchone()['exists']:
                    logger.info("جدول profit_distribution غير موجود، سيتم إنشاؤه لاحقاً")
                    return
                
                # 2. التحقق من وجود عمود owner_id
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'profit_distribution' 
                    AND column_name = 'owner_id'
                """)
                has_owner_id = cursor.fetchone() is not None
                
                # 3. التحقق من وجود عمود manager_name (القديم)
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'profit_distribution' 
                    AND column_name = 'manager_name'
                """)
                has_manager_name = cursor.fetchone() is not None
                
                # 4. إضافة عمود profit_type إذا لم يكن موجوداً
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'profit_distribution' 
                    AND column_name = 'profit_type'
                """)
                has_profit_type = cursor.fetchone() is not None
                
                if not has_owner_id:
                    # إضافة عمود owner_id
                    cursor.execute("ALTER TABLE profit_distribution ADD COLUMN owner_id INTEGER")
                    logger.info("تم إضافة العمود owner_id إلى profit_distribution")
                    
                    # إذا كان هناك عمود manager_name، نحاول تحويل البيانات
                    if has_manager_name:
                        # تعيين owner_id من company_owners بناءً على manager_name
                        cursor.execute("""
                            UPDATE profit_distribution p
                            SET owner_id = co.id
                            FROM company_owners co
                            WHERE p.manager_name = co.name
                        """)
                        logger.info("تم تحويل manager_name إلى owner_id")
                        
                        # حذف عمود manager_name بعد التحويل
                        cursor.execute("ALTER TABLE profit_distribution DROP COLUMN manager_name")
                        logger.info("تم حذف العمود manager_name")
                    else:
                        # إذا لم يكن هناك manager_name، قد تكون البيانات غير صالحة
                        # نحذف جميع السجلات التي ليس لها owner_id
                        cursor.execute("DELETE FROM profit_distribution WHERE owner_id IS NULL")
                        logger.warning("تم حذف سجلات profit_distribution بدون owner_id")
                else:
                    # إذا كان owner_id موجوداً، نتأكد من عدم وجود manager_name
                    if has_manager_name:
                        cursor.execute("ALTER TABLE profit_distribution DROP COLUMN manager_name")
                        logger.info("تم حذف العمود manager_name الزائد")
                
                # إضافة عمود profit_type إذا لم يكن موجوداً
                if not has_profit_type:
                    cursor.execute("ALTER TABLE profit_distribution ADD COLUMN profit_type VARCHAR(20) DEFAULT 'manager'")
                    logger.info("تم إضافة العمود profit_type إلى profit_distribution")
                
                # 5. إضافة قيد المفتاح الخارجي إذا لم يكن موجوداً
                cursor.execute("""
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name = 'fk_profit_distribution_owner'
                    AND table_name = 'profit_distribution'
                """)
                if not cursor.fetchone():
                    cursor.execute("""
                        ALTER TABLE profit_distribution
                        ADD CONSTRAINT fk_profit_distribution_owner
                        FOREIGN KEY (owner_id) REFERENCES company_owners(id) ON DELETE RESTRICT
                    """)
                    logger.info("تم إضافة قيد المفتاح الخارجي لـ profit_distribution")
                
                # 6. تنظيف أي سجلات قديمة لا تشير إلى owner_id موجود
                cursor.execute("""
                    DELETE FROM profit_distribution
                    WHERE owner_id IS NOT NULL 
                    AND NOT EXISTS (SELECT 1 FROM company_owners WHERE id = owner_id)
                """)
                if cursor.rowcount > 0:
                    logger.info(f"تم حذف {cursor.rowcount} سجل(ات) profit_distribution بمرجع غير صالح")
                    
        except Exception as e:
            logger.error(f"خطأ في تحديث جدول profit_distribution: {e}")


    def update_energy_tables(self):
        """إنشاء جدول توزيع أرباح الطاقة المرتبط بـ energy_meters، مع تنظيف البنية القديمة"""
        try:
            with db.get_cursor() as cursor:
                # 1. التحقق من وجود الجدول القديم ووجود عمود meter_id
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'energy_profit_distribution'
                    )
                """)
                table_exists = cursor.fetchone()['exists']
                
                if table_exists:
                    # التحقق من وجود عمود meter_id
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'energy_profit_distribution' 
                        AND column_name = 'meter_id'
                    """)
                    has_meter_id = cursor.fetchone() is not None
                    
                    if not has_meter_id:
                        # الجدول موجود بهيكل قديم (يحتوي على owner_id مثلاً)
                        logger.warning("جدول energy_profit_distribution قديم (بدون meter_id). سيتم حذفه وإعادة إنشائه.")
                        cursor.execute("DROP TABLE IF EXISTS energy_profit_distribution CASCADE")
                        table_exists = False
                
                # 2. إنشاء الجدول إذا لم يكن موجوداً (أو بعد حذفه)
                if not table_exists:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS energy_profit_distribution (
                            id SERIAL PRIMARY KEY,
                            daily_cash_id INTEGER NOT NULL,
                            meter_id INTEGER NOT NULL REFERENCES energy_meters(id) ON DELETE RESTRICT,
                            amount DECIMAL(15,2) NOT NULL,
                            note TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    logger.info("تم إنشاء جدول energy_profit_distribution (مرتبط بـ energy_meters)")
                
                # 3. حذف جدول energy_owners إذا كان موجوداً (تنظيف)
                cursor.execute("DROP TABLE IF EXISTS energy_owners CASCADE")
                logger.info("تم حذف جدول energy_owners (إن وجد)")
                
        except Exception as e:
            logger.error(f"خطأ في تحديث جداول الطاقة: {e}")


    #def cleanup_old_energy_tables(self):
     #   """تنظيف الجداول القديمة المتعلقة بالطاقة"""
      #  try:
       #     with db.get_cursor() as cursor:
        #        cursor.execute("DROP TABLE IF EXISTS energy_owners CASCADE")
         #       cursor.execute("DROP TABLE IF EXISTS energy_profit_distribution_old CASCADE")
          #      logger.info("تم تنظيف الجداول القديمة للطاقة")
        #except Exception as e:
         #   logger.error(f"خطأ في تنظيف الجداول: {e}")


    # ========== دوال الصندوق اليومي والجرد الأسبوعي الجديدة ==========

    def recalculate_daily_cash(self, target_date):
        """إعادة حساب الصندوق اليومي بشكل صحيح (تجنب الأخطاء إن لم توجد جداول)"""
        from datetime import timedelta
        try:
            with db.get_cursor() as cursor:
                # 1. حساب إجمالي الإيرادات
                total_income = 0.0
                try:
                    cursor.execute("""
                        SELECT COALESCE(SUM(total_collected), 0) as total_collections
                        FROM daily_collections_detail
                        WHERE daily_cash_id = (SELECT id FROM daily_cash WHERE cash_date = %s)
                    """, (target_date,))
                    row = cursor.fetchone()
                    if row:
                        total_income = row['total_collections']
                except Exception as e:
                    logger.warning(f"تعذر حساب الإيرادات: {e}")
                
                # 2. حساب إجمالي المصروفات
                total_expenses = 0.0
                try:
                    cursor.execute("""
                        SELECT COALESCE(SUM(amount), 0) as total_expenses
                        FROM daily_expenses
                        WHERE daily_cash_id = (SELECT id FROM daily_cash WHERE cash_date = %s)
                    """, (target_date,))
                    row = cursor.fetchone()
                    if row:
                        total_expenses = row['total_expenses']
                except Exception as e:
                    logger.warning(f"تعذر حساب المصروفات: {e}")
                
                # 3. حساب إجمالي أرباح المدراء
                total_profits = 0.0
                try:
                    cursor.execute("""
                        SELECT COALESCE(SUM(amount), 0) as total_profits
                        FROM profit_distribution
                        WHERE daily_cash_id = (SELECT id FROM daily_cash WHERE cash_date = %s)
                    """, (target_date,))
                    row = cursor.fetchone()
                    if row:
                        total_profits = row['total_profits']
                except Exception as e:
                    logger.warning(f"تعذر حساب الأرباح: {e}")

                # 4. حساب إجمالي أرباح الطاقة
                total_energy_profits = 0.0
                try:
                    cursor.execute("""
                        SELECT COALESCE(SUM(amount), 0) as total_energy_profits
                        FROM energy_profit_distribution
                        WHERE daily_cash_id = (SELECT id FROM daily_cash WHERE cash_date = %s)
                    """, (target_date,))
                    row = cursor.fetchone()
                    if row:
                        total_energy_profits = row['total_energy_profits']
                except Exception as e:
                    logger.warning(f"تعذر حساب أرباح الطاقة: {e}")
                
                # 5. جلب الرصيد الافتتاحي
                previous_date = target_date - timedelta(days=1)
                cursor.execute("SELECT closing_balance FROM daily_cash WHERE cash_date = %s", (previous_date,))
                prev = cursor.fetchone()
                opening_balance = prev['closing_balance'] if prev else 0.0
                
                # 6. حساب الرصيد الختامي
                closing_balance = opening_balance + total_income - total_expenses - total_profits - total_energy_profits
                
                # 7. تحديث أو إدراج سجل اليوم
                cursor.execute("""
                    INSERT INTO daily_cash (cash_date, opening_balance, total_collections, total_expenses, total_profits, total_energy_profits, closing_balance, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'final')
                    ON CONFLICT (cash_date) DO UPDATE SET
                        opening_balance = EXCLUDED.opening_balance,
                        total_collections = EXCLUDED.total_collections,
                        total_expenses = EXCLUDED.total_expenses,
                        total_profits = EXCLUDED.total_profits,
                        total_energy_profits = EXCLUDED.total_energy_profits,
                        closing_balance = EXCLUDED.closing_balance,
                        updated_at = CURRENT_TIMESTAMP,
                        status = 'final'
                """, (target_date, opening_balance, total_income, total_expenses, total_profits, total_energy_profits, closing_balance))
                
                logger.info(f"تم إعادة حساب الصندوق لليوم {target_date}: ختامي={closing_balance}")
                return True
        except Exception as e:
            logger.error(f"خطأ في إعادة حساب الصندوق اليومي: {e}")
            return False

    def recalculate_week_cash_inventory(self, week_start_date):
        """إعادة حساب الجرد الأسبوعي للصندوق بقيم صحيحة (أول يوم رصيد افتتاحي، آخر يوم رصيد ختامي)"""
        from datetime import timedelta
        try:
            week_end_date = week_start_date + timedelta(days=6)
            with db.get_cursor() as cursor:
                # الحصول على الرصيد الافتتاحي لأول يوم في الأسبوع
                cursor.execute("""
                    SELECT opening_balance 
                    FROM daily_cash 
                    WHERE cash_date = %s
                """, (week_start_date,))
                first_day = cursor.fetchone()
                total_opening = float(first_day['opening_balance']) if first_day else 0.0

                # الحصول على الرصيد الختامي لآخر يوم في الأسبوع
                cursor.execute("""
                    SELECT closing_balance 
                    FROM daily_cash 
                    WHERE cash_date = %s
                """, (week_end_date,))
                last_day = cursor.fetchone()
                total_closing = float(last_day['closing_balance']) if last_day else 0.0

                # الحصول على مجاميع الأسبوع
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(total_collections), 0) as total_collections,
                        COALESCE(SUM(total_expenses), 0) as total_expenses,
                        COALESCE(SUM(total_profits), 0) as total_profits
                    FROM daily_cash
                    WHERE cash_date BETWEEN %s AND %s
                """, (week_start_date, week_end_date))
                totals = cursor.fetchone()

                # تحديث أو إدراج الجرد الأسبوعي
                cursor.execute("""
                    INSERT INTO weekly_cash_inventory (
                        week_start, week_end, total_opening, total_collections, 
                        total_expenses, total_profits, total_closing
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (week_start) DO UPDATE SET
                        week_end = EXCLUDED.week_end,
                        total_opening = EXCLUDED.total_opening,
                        total_collections = EXCLUDED.total_collections,
                        total_expenses = EXCLUDED.total_expenses,
                        total_profits = EXCLUDED.total_profits,
                        total_closing = EXCLUDED.total_closing,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    week_start_date, week_end_date,
                    total_opening,
                    totals['total_collections'], totals['total_expenses'], totals['total_profits'],
                    total_closing
                ))
                logger.info(f"تم إعادة حساب الجرد الأسبوعي للأسبوع {week_start_date} إلى {week_end_date} بقيم صحيحة")
                return True
        except Exception as e:
            logger.error(f"خطأ في إعادة حساب الجرد الأسبوعي: {e}")
            return False


    def update_daily_expenses_table(self):
        """تحديث جدول daily_expenses بإضافة عمود user_id وربطه بالمستخدمين"""
        try:
            with db.get_cursor() as cursor:
                # التحقق من وجود العمود
                cursor.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'daily_expenses'
                    AND column_name = 'user_id'
                """)
                if not cursor.fetchone():
                    # إضافة العمود مع ربطه بجدول users
                    cursor.execute("""
                        ALTER TABLE daily_expenses 
                        ADD COLUMN user_id INTEGER REFERENCES users(id)
                    """)
                    logger.info("✅ تم إضافة العمود user_id إلى جدول daily_expenses")
                else:
                    logger.info("ℹ️ العمود user_id موجود بالفعل في daily_expenses")
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث جدول daily_expenses: {e}")    

    def update_daily_cash_add_energy_profits(self):
        """إضافة عمود total_energy_profits إلى جدول daily_cash"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'daily_cash'
                    AND column_name = 'total_energy_profits'
                """)
                if not cursor.fetchone():
                    cursor.execute("""
                        ALTER TABLE daily_cash 
                        ADD COLUMN total_energy_profits DECIMAL(15,2) DEFAULT 0
                    """)
                    logger.info("✅ تم إضافة العمود total_energy_profits إلى جدول daily_cash")
                else:
                    logger.info("ℹ️ العمود total_energy_profits موجود بالفعل")
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث جدول daily_cash: {e}")                    


    def update_profit_distribution_add_user_id(self):
        """إضافة عمود user_id إلى profit_distribution"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'profit_distribution' AND column_name = 'user_id'
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE profit_distribution ADD COLUMN user_id INTEGER REFERENCES users(id)")
                    logger.info("✅ تم إضافة العمود user_id إلى profit_distribution")
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث profit_distribution: {e}")

    def update_energy_profit_distribution_add_user_id(self):
        """إضافة عمود user_id إلى energy_profit_distribution"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'energy_profit_distribution' AND column_name = 'user_id'
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE energy_profit_distribution ADD COLUMN user_id INTEGER REFERENCES users(id)")
                    logger.info("✅ تم إضافة العمود user_id إلى energy_profit_distribution")
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث energy_profit_distribution: {e}")


    def update_weekly_cash_inventory_table(self):
        """إضافة أعمدة total_repair_expansion و total_fuel و total_energy_profits إلى weekly_cash_inventory"""
        try:
            with db.get_cursor() as cursor:
                columns_to_add = [
                    ('total_repair_expansion', 'DECIMAL(15,2) DEFAULT 0'),
                    ('total_energy_profits', 'DECIMAL(15,2) DEFAULT 0'),
                    ('total_fuel', 'DECIMAL(15,2) DEFAULT 0'),
                    ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
                ]
                for col_name, col_type in columns_to_add:
                    cursor.execute("""
                        SELECT column_name FROM information_schema.columns
                        WHERE table_name = 'weekly_cash_inventory' AND column_name = %s
                    """, (col_name,))
                    if not cursor.fetchone():
                        cursor.execute(f"ALTER TABLE weekly_cash_inventory ADD COLUMN {col_name} {col_type}")
                        logger.info(f"✅ تم إضافة العمود {col_name} إلى weekly_cash_inventory")
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث جدول weekly_cash_inventory: {e}")


    # ========== تحديث جداول الطاقة لتلائم الحسابات المباشرة ==========
    def update_energy_meters_for_accounts(self):
        """إضافة conversion_rate و current_balance إلى energy_meters (إذا لم تكن موجودة)"""
        try:
            with db.get_cursor() as cursor:
                for col_name, col_type in [
                    ('conversion_rate', 'DECIMAL(12,4) DEFAULT 0'),
                    ('current_balance', 'DECIMAL(15,2) DEFAULT 0')
                ]:
                    cursor.execute(f"""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='energy_meters' AND column_name=%s
                    """, (col_name,))
                    if not cursor.fetchone():
                        cursor.execute(f"ALTER TABLE energy_meters ADD COLUMN {col_name} {col_type}")
                        logger.info(f"✅ تم إضافة العمود {col_name} إلى energy_meters")
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث energy_meters: {e}")

    def create_energy_account_tables(self):
        """إنشاء جدول حركات حساب الطاقة"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS energy_account_transactions (
                        id SERIAL PRIMARY KEY,
                        meter_id INTEGER NOT NULL REFERENCES energy_meters(id) ON DELETE CASCADE,
                        transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('production', 'payment', 'adjustment')),
                        amount DECIMAL(15,2) NOT NULL,
                        balance_before DECIMAL(15,2),
                        balance_after DECIMAL(15,2),
                        reading_id INTEGER REFERENCES energy_daily_readings(id) ON DELETE SET NULL,
                        profit_id INTEGER REFERENCES energy_profit_distribution(id) ON DELETE SET NULL,
                        notes TEXT,
                        created_by INTEGER REFERENCES users(id),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_energy_trans_meter ON energy_account_transactions(meter_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_energy_trans_date ON energy_account_transactions(transaction_date)")
                # تنظيف أي جداول قديمة (energy_owners) قد تكون استُخدمت سابقاً
                cursor.execute("DROP TABLE IF EXISTS energy_owners CASCADE")
                logger.info("✅ تم إنشاء جداول حركات الطاقة")
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء جداول الطاقة: {e}")

    # داخل __init__ أضف الاستدعاءات:


    def update_energy_meters_for_accounts(self):
        """إضافة conversion_rate و current_balance إلى energy_meters"""
        try:
            with db.get_cursor() as cursor:
                for col_name, col_type in [
                    ('conversion_rate', 'DECIMAL(12,4) DEFAULT 0'),
                    ('current_balance', 'DECIMAL(15,2) DEFAULT 0')
                ]:
                    cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='energy_meters' AND column_name=%s", (col_name,))
                    if not cursor.fetchone():
                        cursor.execute(f"ALTER TABLE energy_meters ADD COLUMN {col_name} {col_type}")
                        logger.info(f"✅ عمود {col_name} أضيف إلى energy_meters")
        except Exception as e:
            logger.error(f"❌ خطأ في update_energy_meters_for_accounts: {e}")

    def create_energy_account_tables(self):
        """إنشاء جدول energy_account_transactions"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS energy_account_transactions (
                        id SERIAL PRIMARY KEY,
                        meter_id INTEGER NOT NULL REFERENCES energy_meters(id) ON DELETE CASCADE,
                        transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('production', 'payment', 'adjustment')),
                        amount DECIMAL(15,2) NOT NULL,
                        balance_before DECIMAL(15,2),
                        balance_after DECIMAL(15,2),
                        reading_id INTEGER REFERENCES energy_daily_readings(id) ON DELETE SET NULL,
                        profit_id INTEGER REFERENCES energy_profit_distribution(id) ON DELETE SET NULL,
                        notes TEXT,
                        created_by INTEGER REFERENCES users(id),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_energy_trans_meter ON energy_account_transactions(meter_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_energy_trans_date ON energy_account_transactions(transaction_date)")
                cursor.execute("DROP TABLE IF EXISTS energy_owners CASCADE")
                logger.info("✅ تم إنشاء جداول حركات الطاقة")
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء جداول الطاقة: {e}")

    def update_daily_cash_add_fuel_column(self):
        """إضافة عمود total_fuel إلى daily_cash إن لم يكن موجوداً"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='daily_cash' AND column_name='total_fuel'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE daily_cash ADD COLUMN total_fuel DECIMAL(15,2) DEFAULT 0")
                    logger.info("✅ عمود total_fuel أضيف إلى daily_cash")
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة total_fuel: {e}")    


# إنشاء كائن Models
models = Models()