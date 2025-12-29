# database/migrations.py
import pandas as pd
import logging
from database.connection import db
from tqdm import tqdm
import os

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
            
            # 1. ترحيل القطاعات
            self.migrate_sectors()
            
            # 2. ترحيل الزبائن من ملفات القطاعات
            for arabic_name, file_name in self.sector_mapping.items():
                file_path = os.path.join(self.excel_folder, f"{file_name.lower()}.xlsx")
                if os.path.exists(file_path):
                    self.migrate_customers_from_file(file_path, arabic_name)
            
            # 3. ترحيل الأرشيف
            archive_path = os.path.join(self.excel_folder, "archive.xlsx")
            if os.path.exists(archive_path):
                self.migrate_invoices_from_archive(archive_path)
            
            logger.info("اكتمل ترحيل البيانات بنجاح")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في ترحيل البيانات: {e}")
            return False
    
    def migrate_sectors(self):
        """ترحيل القطاعات"""
        with db.get_cursor() as cursor:
            for arabic_name, code in self.sector_mapping.items():
                cursor.execute("""
                    INSERT INTO sectors (name, code) 
                    VALUES (%s, %s)
                    ON CONFLICT (name) DO NOTHING
                """, (arabic_name, code))
    
    def migrate_customers_from_file(self, file_path, sector_name):
        """ترحيل الزبائن من ملف قطاع"""
        try:
            df = pd.read_excel(file_path)
            
            # الحصول على معرف القطاع
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id FROM sectors WHERE name = %s", (sector_name,))
                sector_id = cursor.fetchone()['id']
            
            # ترحيل كل زبون
            for _, row in tqdm(df.iterrows(), desc=f"ترحيل زبائن {sector_name}"):
                customer_data = {
                    'sector_id': sector_id,
                    'box_number': str(row.get('علبة', '')).strip(),
                    'serial_number': str(row.get('مسلسل', '')).strip(),
                    'name': str(row.get('اسم الزبون', '')).strip(),
                    'current_balance': float(row.get('الرصيد الحالي', 0) or 0),
                    'last_counter_reading': float(row.get('نهاية جديدة', 0) or 0),
                    'visa_balance': float(row.get('تنزيل تأشيرة', 0) or 0),
                    'withdrawal_amount': float(row.get('سحب المشترك', 0) or 0),
                    'phone_number': str(row.get('رقم واتس الزبون', '')).strip()
                }
                
                self.save_customer(customer_data)
                
        except Exception as e:
            logger.error(f"خطأ في ترحيل زبائن {sector_name}: {e}")
    
    def save_customer(self, customer_data):
        """حفظ الزبون في قاعدة البيانات"""
        with db.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO customers 
                (sector_id, box_number, serial_number, name, current_balance, 
                 last_counter_reading, visa_balance, withdrawal_amount, phone_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (sector_id, name) 
                DO UPDATE SET
                box_number = EXCLUDED.box_number,
                serial_number = EXCLUDED.serial_number,
                current_balance = EXCLUDED.current_balance,
                last_counter_reading = EXCLUDED.last_counter_reading,
                updated_at = CURRENT_TIMESTAMP
            """, (
                customer_data['sector_id'],
                customer_data['box_number'],
                customer_data['serial_number'],
                customer_data['name'],
                customer_data['current_balance'],
                customer_data['last_counter_reading'],
                customer_data['visa_balance'],
                customer_data['withdrawal_amount'],
                customer_data['phone_number']
            ))
    
    def migrate_invoices_from_archive(self, archive_path):
        """ترحيل الفواتير من الأرشيف"""
        try:
            df = pd.read_excel(archive_path)
            
            for _, row in tqdm(df.iterrows(), desc="ترحيل الفواتير"):
                invoice_data = self.prepare_invoice_data(row)
                if invoice_data:
                    self.save_invoice(invoice_data)
                    
        except Exception as e:
            logger.error(f"خطأ في ترحيل الفواتير: {e}")
    
    def prepare_invoice_data(self, row):
        """تحضير بيانات الفاتورة"""
        try:
            # الحصول على معرف القطاع
            sector_name = str(row.get('القطاع', '')).strip()
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id FROM sectors WHERE name = %s", (sector_name,))
                sector_result = cursor.fetchone()
                if not sector_result:
                    return None
                sector_id = sector_result['id']
            
            # الحصول على معرف الزبون
            customer_name = str(row.get('اسم الزبون', '')).strip()
            cursor.execute("""
                SELECT id FROM customers 
                WHERE name = %s AND sector_id = %s
            """, (customer_name, sector_id))
            
            customer_result = cursor.fetchone()
            if not customer_result:
                return None
            
            customer_id = customer_result['id']
            
            return {
                'customer_id': customer_id,
                'sector_id': sector_id,
                'user_id': 1,  # افتراضياً المسؤول
                'invoice_number': f"INV-{row.get('رقم الوصل', '')}",
                'payment_date': pd.to_datetime(row.get('تاريخ الدفع', datetime.now())).date(),
                'payment_time': pd.to_datetime(row.get('توقيت الدفع', datetime.now())).time(),
                'kilowatt_amount': float(row.get('كمية الدفع', 0) or 0),
                'free_kilowatt': float(row.get('المجاني', 0) or 0),
                'price_per_kilo': float(row.get('سعر الكيلو', 0) or 0),
                'discount': float(row.get('الحسم', 0) or 0),
                'total_amount': float(row.get('المبلغ الكلي', 0) or 0),
                'previous_reading': float(row.get('نهاية سابقة', 0) or 0),
                'new_reading': float(row.get('نهاية جديدة', 0) or 0),
                'visa_application': str(row.get('تنزيل تأشيرة', '')),
                'customer_withdrawal': str(row.get('سحب المشترك', '')),
                'book_number': str(row.get('رقم الدفتر', '')),
                'receipt_number': str(row.get('رقم الوصل', '')),
                'current_balance': float(row.get('الرصيد الحالي', 0) or 0)
            }
            
        except Exception as e:
            logger.error(f"خطأ في تحضير بيانات الفاتورة: {e}")
            return None
    
    def save_invoice(self, invoice_data):
        """حفظ الفاتورة في قاعدة البيانات"""
        with db.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO invoices 
                (customer_id, sector_id, user_id, invoice_number, payment_date, 
                 payment_time, kilowatt_amount, free_kilowatt, price_per_kilo, 
                 discount, total_amount, previous_reading, new_reading, 
                 visa_application, customer_withdrawal, book_number, 
                 receipt_number, current_balance)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                invoice_data['current_balance']
            ))

# استخدام الترحيل
if __name__ == "__main__":
    migrator = ExcelMigration(r"C:\Users\dotnet\host")
    migrator.migrate_all_data()