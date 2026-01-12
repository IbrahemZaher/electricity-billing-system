import pandas as pd
import logging
from database.connection import db
from tqdm import tqdm
import os
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)

class ExcelMigration:
    def __init__(self, excel_folder):
        self.excel_folder = excel_folder
        self.sector_mapping = {
            "بيدر": "BAIDAR",
            "غبور": "GABOR", 
            "الحديقة": "GARDEN",
            "القمر": "MOON",
            "صمصم": "SAMSAM",
            "تغرة": "TAGRA"
        }
    
    def migrate_all_data(self):
        """ترحيل جميع البيانات من Excel إلى PostgreSQL"""
        try:
            logger.info("بدء ترحيل البيانات من Excel إلى PostgreSQL")
            
            # 1. ترحيل القطاعات أولاً
            self.migrate_sectors()
            
            # 2. الحصول على mapping للقطاعات
            sector_map = self.get_sector_mapping()
            logger.info(f"تم تحميل {len(sector_map)} قطاع")
            
            # 3. ترحيل الزبائن من ملفات القطاعات
            total_customers = 0
            for arabic_name, file_name in self.sector_mapping.items():
                file_path = os.path.join(self.excel_folder, f"{file_name.lower()}.xlsx")
                if os.path.exists(file_path):
                    logger.info(f"جاري معالجة ملف: {file_path}")
                    count = self.migrate_customers_from_file(file_path, arabic_name, sector_map)
                    total_customers += count
                    logger.info(f"تم ترحيل {count} زبون من قطاع {arabic_name}")
                else:
                    logger.warning(f"الملف غير موجود: {file_path}")
            
            logger.info(f"اكتمل ترحيل البيانات بنجاح. إجمالي الزبائن: {total_customers}")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في ترحيل البيانات: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def get_sector_mapping(self):
        """الحصول على mapping للقطاعات"""
        sector_map = {}
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id, name, code FROM sectors")
                for sector in cursor.fetchall():
                    sector_map[sector['name']] = sector['id']
                    sector_map[sector['code']] = sector['id']
            return sector_map
        except Exception as e:
            logger.error(f"خطأ في جلب القطاعات: {e}")
            return {}
    
    def migrate_sectors(self):
        """ترحيل القطاعات"""
        try:
            with db.get_cursor() as cursor:
                for arabic_name, code in self.sector_mapping.items():
                    # إدخال القطاع
                    cursor.execute("""
                        INSERT INTO sectors (name, code, is_active) 
                        VALUES (%s, %s, %s)
                        ON CONFLICT (name) DO UPDATE 
                        SET code = EXCLUDED.code,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id
                    """, (arabic_name, code, True))
                    
                    result = cursor.fetchone()
                    logger.info(f"تم إدخال/تحديث القطاع: {arabic_name} (ID: {result['id']})")
        except Exception as e:
            logger.error(f"خطأ في ترحيل القطاعات: {e}")
    
    def migrate_customers_from_file(self, file_path, sector_name, sector_map):
        """ترحيل الزبائن من ملف قطاع"""
        customer_count = 0
        
        try:
            # قراءة ملف Excel
            df = pd.read_excel(file_path)
            logger.info(f"تم قراءة ملف {file_path}، عدد الصفوف: {len(df)}")
            
            # الحصول على معرف القطاع
            sector_id = sector_map.get(sector_name)
            if not sector_id:
                logger.error(f"القطاع غير موجود: {sector_name}")
                return 0
            
            # ترحيل كل زبون
            for index, row in tqdm(df.iterrows(), total=len(df), desc=f"ترحيل زبائن {sector_name}"):
                try:
                    # استخراج البيانات مع معالجة القيم الفارغة
                    box_number = str(row.get('علبة', '')).strip() if pd.notna(row.get('علبة', '')) else ''
                    serial_number = str(row.get('مسلسل', '')).strip() if pd.notna(row.get('مسلسل', '')) else ''
                    name = str(row.get('اسم الزبون', '')).strip() if pd.notna(row.get('اسم الزبون', '')) else ''
                    phone_number = str(row.get('رقم واتس الزبون', '')).strip() if pd.notna(row.get('رقم واتس الزبون', '')) else ''
                    
                    # تحويل القيم الرقمية بشكل آمن
                    def safe_float(value, default=0):
                        try:
                            if pd.isna(value):
                                return default
                            return float(value)
                        except:
                            return default
                    
                    # إنشاء بيانات الزبون
                    customer_data = {
                        'sector_id': sector_id,
                        'box_number': box_number,
                        'serial_number': serial_number,
                        'name': name,
                        'phone_number': phone_number,
                        'current_balance': safe_float(row.get('الرصيد الحالي', 0)),
                        'last_counter_reading': safe_float(row.get('نهاية جديدة', 0)),
                        'visa_balance': safe_float(row.get('تنزيل تأشيرة', 0)),
                        'withdrawal_amount': safe_float(row.get('سحب المشترك', 0)),
                        'notes': f"تم الاستيراد من {sector_name} في {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        'is_active': True
                    }
                    
                    # حذف المسافات الزائدة من الأسماء
                    if customer_data['name']:
                        customer_data['name'] = ' '.join(customer_data['name'].split())
                    
                    # حفظ الزبون في قاعدة البيانات
                    if self.save_customer(customer_data):
                        customer_count += 1
                    
                except Exception as e:
                    logger.error(f"خطأ في صف {index}: {e}")
                    continue
            
            return customer_count
            
        except Exception as e:
            logger.error(f"خطأ في ترحيل زبائن {sector_name}: {e}")
            logger.error(traceback.format_exc())
            return 0

    def save_customer(self, customer_data):
        """حفظ الزبون في قاعدة البيانات"""
        try:
            with db.get_cursor() as cursor:
                # أولاً: التحقق من وجود الزبون
                cursor.execute("""
                    SELECT id FROM customers 
                    WHERE sector_id = %s AND name = %s
                """, (customer_data['sector_id'], customer_data['name']))
                
                existing_customer = cursor.fetchone()
                
                if existing_customer:
                    # تحديث الزبون الموجود
                    cursor.execute("""
                        UPDATE customers 
                        SET box_number = %s,
                            serial_number = %s,
                            phone_number = %s,
                            current_balance = %s,
                            last_counter_reading = %s,
                            visa_balance = %s,
                            withdrawal_amount = %s,
                            notes = %s,
                            is_active = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (
                        customer_data['box_number'],
                        customer_data['serial_number'],
                        customer_data['phone_number'],
                        customer_data['current_balance'],
                        customer_data['last_counter_reading'],
                        customer_data['visa_balance'],
                        customer_data['withdrawal_amount'],
                        customer_data['notes'],
                        customer_data['is_active'],
                        existing_customer['id']
                    ))
                    logger.debug(f"تم تحديث الزبون: {customer_data['name']}")
                    return True
                else:
                    # إضافة زبون جديد
                    cursor.execute("""
                        INSERT INTO customers 
                        (sector_id, box_number, serial_number, name, phone_number,
                         current_balance, last_counter_reading, visa_balance,
                         withdrawal_amount, notes, is_active, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        RETURNING id
                    """, (
                        customer_data['sector_id'],
                        customer_data['box_number'],
                        customer_data['serial_number'],
                        customer_data['name'],
                        customer_data['phone_number'],
                        customer_data['current_balance'],
                        customer_data['last_counter_reading'],
                        customer_data['visa_balance'],
                        customer_data['withdrawal_amount'],
                        customer_data['notes'],
                        customer_data['is_active']
                    ))
                    
                    result = cursor.fetchone()
                    logger.debug(f"تم إضافة الزبون الجديد: {customer_data['name']} (ID: {result['id']})")
                    return True
                        
        except Exception as e:
            logger.error(f"خطأ في حفظ الزبون '{customer_data['name']}': {e}")
            return False
    
    def migrate_invoices_from_archive(self, archive_path):
        """ترحيل الفواتير من الأرشيف"""
        try:
            if not os.path.exists(archive_path):
                logger.warning(f"ملف الأرشيف غير موجود: {archive_path}")
                return 0
            
            df = pd.read_excel(archive_path)
            invoice_count = 0
            
            logger.info(f"جاري ترحيل الفواتير من {archive_path}، عدد الصفوف: {len(df)}")
            
            for index, row in tqdm(df.iterrows(), total=len(df), desc="ترحيل الفواتير"):
                try:
                    invoice_data = self.prepare_invoice_data(row)
                    if invoice_data:
                        if self.save_invoice(invoice_data):
                            invoice_count += 1
                except Exception as e:
                    logger.error(f"خطأ في صف الفاتورة {index}: {e}")
                    continue
            
            logger.info(f"تم ترحيل {invoice_count} فاتورة")
            return invoice_count
            
        except Exception as e:
            logger.error(f"خطأ في ترحيل الفواتير: {e}")
            logger.error(traceback.format_exc())
            return 0
    
    def prepare_invoice_data(self, row):
        """تحضير بيانات الفاتورة"""
        try:
            # الحصول على معرف القطاع
            sector_name = str(row.get('القطاع', '')).strip()
            if not sector_name:
                return None
            
            # البحث عن القطاع
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id FROM sectors WHERE name = %s OR code = %s", 
                             (sector_name, sector_name))
                sector_result = cursor.fetchone()
                
                if not sector_result:
                    logger.warning(f"القطاع غير موجود: {sector_name}")
                    return None
                
                sector_id = sector_result['id']
            
            # الحصول على معرف الزبون
            customer_name = str(row.get('اسم الزبون', '')).strip()
            if not customer_name:
                return None
            
            with db.get_cursor() as cursor:
                # البحث عن الزبون بالاسم والقطاع
                cursor.execute("""
                    SELECT id FROM customers 
                    WHERE name = %s AND sector_id = %s
                    LIMIT 1
                """, (customer_name, sector_id))
                
                customer_result = cursor.fetchone()
                
                if not customer_result:
                    # محاولة البحث بدون القطاع
                    cursor.execute("""
                        SELECT id FROM customers 
                        WHERE name = %s 
                        LIMIT 1
                    """, (customer_name,))
                    customer_result = cursor.fetchone()
                
                if not customer_result:
                    logger.warning(f"الزبون غير موجود: {customer_name}")
                    return None
                
                customer_id = customer_result['id']
            
            # معالجة القيم الرقمية
            def safe_float(value, default=0):
                try:
                    if pd.isna(value):
                        return default
                    return float(value)
                except:
                    return default
            
            # تحضير بيانات الفاتورة
            invoice_number = str(row.get('رقم الوصل', '')).strip()
            if not invoice_number:
                invoice_number = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{customer_id}"
            
            # معالجة التواريخ
            try:
                payment_date = pd.to_datetime(row.get('تاريخ الدفع', datetime.now())).date()
            except:
                payment_date = datetime.now().date()
            
            try:
                payment_time = pd.to_datetime(row.get('توقيت الدفع', datetime.now())).time()
            except:
                payment_time = datetime.now().time()
            
            return {
                'customer_id': customer_id,
                'sector_id': sector_id,
                'user_id': 1,  # افتراضياً المسؤول
                'invoice_number': invoice_number,
                'payment_date': payment_date,
                'payment_time': payment_time,
                'kilowatt_amount': safe_float(row.get('كمية الدفع', 0)),
                'free_kilowatt': safe_float(row.get('المجاني', 0)),
                'price_per_kilo': safe_float(row.get('سعر الكيلو', 0)),
                'discount': safe_float(row.get('الحسم', 0)),
                'total_amount': safe_float(row.get('المبلغ الكلي', 0)),
                'previous_reading': safe_float(row.get('نهاية سابقة', 0)),
                'new_reading': safe_float(row.get('نهاية جديدة', 0)),
                'visa_application': str(row.get('تنزيل تأشيرة', '')).strip() if pd.notna(row.get('تنزيل تأشيرة', '')) else '',
                'customer_withdrawal': str(row.get('سحب المشترك', '')).strip() if pd.notna(row.get('سحب المشترك', '')) else '',
                'book_number': str(row.get('رقم الدفتر', '')).strip() if pd.notna(row.get('رقم الدفتر', '')) else '',
                'receipt_number': str(row.get('رقم الوصل', '')).strip() if pd.notna(row.get('رقم الوصل', '')) else '',
                'current_balance': safe_float(row.get('الرصيد الحالي', 0)),
                'notes': f"تم الاستيراد من الأرشيف في {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
            
        except Exception as e:
            logger.error(f"خطأ في تحضير بيانات الفاتورة: {e}")
            return None
    
    def save_invoice(self, invoice_data):
        """حفظ الفاتورة في قاعدة البيانات"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO invoices 
                    (customer_id, sector_id, user_id, invoice_number, payment_date, 
                     payment_time, kilowatt_amount, free_kilowatt, price_per_kilo, 
                     discount, total_amount, previous_reading, new_reading, 
                     visa_application, customer_withdrawal, book_number, 
                     receipt_number, current_balance, notes, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                            %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (invoice_number) DO UPDATE SET
                    customer_id = EXCLUDED.customer_id,
                    sector_id = EXCLUDED.sector_id,
                    payment_date = EXCLUDED.payment_date,
                    payment_time = EXCLUDED.payment_time,
                    kilowatt_amount = EXCLUDED.kilowatt_amount,
                    free_kilowatt = EXCLUDED.free_kilowatt,
                    price_per_kilo = EXCLUDED.price_per_kilo,
                    discount = EXCLUDED.discount,
                    total_amount = EXCLUDED.total_amount,
                    previous_reading = EXCLUDED.previous_reading,
                    new_reading = EXCLUDED.new_reading,
                    visa_application = EXCLUDED.visa_application,
                    customer_withdrawal = EXCLUDED.customer_withdrawal,
                    book_number = EXCLUDED.book_number,
                    receipt_number = EXCLUDED.receipt_number,
                    current_balance = EXCLUDED.current_balance,
                    notes = EXCLUDED.notes,
                    updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, (
                    invoice_data['customer_id'],
                    invoice_data['sector_id'],
                    invoice_data['user_id'],
                    invoice_data['invoice_number'],
                    invoice_data['payment_date'],
                    invoice_data['payment_time'],
                    invoice_data['kilowatt_amount'],
                    invoice_data['free_kilowatt'],
                    invoice_data['price_per_kilo'],
                    invoice_data['discount'],
                    invoice_data['total_amount'],
                    invoice_data['previous_reading'],
                    invoice_data['new_reading'],
                    invoice_data['visa_application'],
                    invoice_data['customer_withdrawal'],
                    invoice_data['book_number'],
                    invoice_data['receipt_number'],
                    invoice_data['current_balance'],
                    invoice_data['notes']
                ))
                
                result = cursor.fetchone()
                if result:
                    logger.debug(f"تم حفظ الفاتورة: {invoice_data['invoice_number']}")
                    return True
                else:
                    logger.warning(f"فشل في حفظ الفاتورة: {invoice_data['invoice_number']}")
                    return False
                    
        except Exception as e:
            logger.error(f"خطأ في حفظ الفاتورة {invoice_data.get('invoice_number', 'غير معروف')}: {e}")
            return False