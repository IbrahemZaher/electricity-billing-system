# modules/fast_operations.py
"""
وحدة العمليات السريعة للمهام اليومية
تشبه الكود البسيط في السرعة مع الحفاظ على PostgreSQL
"""
import logging
from datetime import datetime
from database.connection import db
import pandas as pd
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class FastOperations:
    """عمليات سريعة للاستخدام اليومي"""
    
    @staticmethod
    def fast_search_customers(search_term: str = "", sector_id: int = None, limit: int = 50) -> List[Dict]:
        """بحث سريع بالزبائن (مشابه للبحث في Excel)"""
        try:
            with db.get_cursor() as cursor:
                query = """
                    SELECT 
                        c.id, c.name, c.box_number, c.serial_number,
                        c.current_balance, c.last_counter_reading,
                        c.visa_balance, c.withdrawal_amount,
                        s.name as sector_name,
                        CONCAT(c.box_number, ' - ', c.name) as display_text
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.is_active = TRUE
                """
                
                params = []
                
                if search_term:
                    # بحث في الاسم أو العلبة أو المسلسل
                    query += """
                        AND (
                            c.name ILIKE %s 
                            OR c.box_number ILIKE %s 
                            OR c.serial_number ILIKE %s
                        )
                    """
                    search_pattern = f"%{search_term}%"
                    params.extend([search_pattern, search_pattern, search_pattern])
                
                if sector_id:
                    query += " AND c.sector_id = %s"
                    params.append(sector_id)
                
                query += " ORDER BY c.name LIMIT %s"
                params.append(limit)
                
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                # تحويل إلى قائمة من القواميس
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"خطأ في البحث السريع: {e}")
            return []
    
    @staticmethod
    def fast_get_customer_details(customer_id: int) -> Dict:
        """جلب بيانات زبون سريعاً"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        c.*, s.name as sector_name,
                        s.code as sector_code,
                        (
                            SELECT invoice_number 
                            FROM invoices 
                            WHERE customer_id = c.id 
                            ORDER BY payment_date DESC, payment_time DESC 
                            LIMIT 1
                        ) as last_invoice
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.id = %s
                """, (customer_id,))
                
                result = cursor.fetchone()
                return dict(result) if result else {}
                
        except Exception as e:
            logger.error(f"خطأ في جلب بيانات الزبون: {e}")
            return {}
                
    @staticmethod
    def fast_process_invoice(customer_id: int, **kwargs):
        """معالجة فاتورة سريعة مع تسجيل في customer_history"""
        try:
            # استقبال البيانات الجديدة
            kilowatt_amount = float(kwargs.get('kilowatt_amount', 0))
            free_kilowatt = float(kwargs.get('free_kilowatt', 0))
            price_per_kilo = float(kwargs.get('price_per_kilo', 7200))
            discount = float(kwargs.get('discount', 0))
            user_id = kwargs.get('user_id', 1)

            with db.get_cursor() as cursor:
                # جلب بيانات الزبون مع FOR UPDATE
                cursor.execute("""
                    SELECT
                        c.current_balance,
                        c.last_counter_reading,
                        c.sector_id,
                        c.name,
                        s.name as sector_name
                    FROM customers c
                    INNER JOIN sectors s ON c.sector_id = s.id
                    WHERE c.id = %s AND c.is_active = TRUE
                    FOR UPDATE
                """, (customer_id,))

                customer = cursor.fetchone()
                if not customer:
                    return {"success": False, "error": "الزبون غير موجود"}

                previous_reading = float(customer['last_counter_reading'] or 0)
                current_balance = float(customer['current_balance'] or 0)

                # الحسابات الجديدة
                new_reading = previous_reading + kilowatt_amount + free_kilowatt
                new_balance = current_balance + kilowatt_amount + free_kilowatt
                total_amount = (kilowatt_amount * price_per_kilo) - discount

                # إنشاء رقم فاتورة
                invoice_number = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{customer_id}"

                # تحديث بيانات الزبون
                cursor.execute("""
                    UPDATE customers
                    SET current_balance = %s,
                        last_counter_reading = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING *
                """, (float(new_balance), float(new_reading), customer_id))

                # إدخال الفاتورة
                cursor.execute("""
                    INSERT INTO invoices (
                        customer_id, sector_id, user_id, invoice_number,
                        payment_date, payment_time, kilowatt_amount, free_kilowatt,
                        price_per_kilo, discount, total_amount,
                        previous_reading, new_reading, visa_application, customer_withdrawal,
                        current_balance, created_at
                    ) VALUES (
                        %s, %s, %s, %s,
                        CURRENT_DATE, CURRENT_TIME, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, CURRENT_TIMESTAMP
                    )
                    RETURNING id
                """, (
                    customer_id, customer['sector_id'], user_id, invoice_number,
                    float(kilowatt_amount), float(free_kilowatt), float(price_per_kilo),
                    float(discount), float(total_amount),
                    float(previous_reading), float(new_reading),
                    kwargs.get('visa_application', ''),
                    kwargs.get('customer_withdrawal', ''),
                    float(new_balance)
                ))

                invoice_id = cursor.fetchone()['id']

                # ✅ تسجيل الحدث في customer_history
                cursor.execute("""
                    INSERT INTO customer_history 
                    (customer_id, action_type, transaction_type, 
                    old_value, new_value, amount,
                    current_balance_before, current_balance_after,
                    notes, created_by, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    customer_id,
                    'invoice_created',            # action_type
                    'payment',                     # transaction_type
                    current_balance,                # old_value (الرصيد قبل)
                    new_balance,                     # new_value (الرصيد بعد)
                    total_amount,                     # amount
                    current_balance,                  # current_balance_before
                    new_balance,                       # current_balance_after
                    f"فاتورة سريعة #{invoice_number} للزبون {customer['name']}",
                    user_id                            # created_by
                ))

                # تسجيل النشاط
                cursor.execute("""
                    INSERT INTO activity_logs (user_id, action_type, description)
                    VALUES (%s, 'fast_invoice', %s)
                """, (user_id, f"فاتورة سريعة #{invoice_number} للزبون {customer['name']}"))

                return {
                    "success": True,
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "customer_name": customer['name'],
                    "previous_reading": previous_reading,
                    "new_reading": new_reading,
                    "kilowatt_amount": kilowatt_amount,
                    "free_kilowatt": free_kilowatt,
                    "total_amount": total_amount,
                    "new_balance": new_balance,
                    "withdrawal_amount": kwargs.get('customer_withdrawal', 0),   # <-- إضافة هذا السطر
                    "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                }

        except Exception as e:
            logger.error(f"خطأ في المعالجة السريعة: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def quick_export_to_excel(data: List[Dict], filename: str) -> str:
        """تصدير سريع إلى Excel"""
        try:
            df = pd.DataFrame(data)
            df.to_excel(filename, index=False, engine='openpyxl')
            return filename
        except Exception as e:
            logger.error(f"خطأ في التصدير: {e}")
            return ""
    
    @staticmethod
    def backup_to_excel_parallel() -> bool:
        """نسخ احتياطي موازي إلى Excel (مثل النظام القديم)"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"backups/parallel_backup_{timestamp}.xlsx"
            
            with pd.ExcelWriter(backup_file, engine='openpyxl') as writer:
                # تصدير الزبائن
                with db.get_cursor() as cursor:
                    cursor.execute("SELECT * FROM customers")
                    customers = cursor.fetchall()
                    if customers:
                        df_customers = pd.DataFrame([dict(c) for c in customers])
                        df_customers.to_excel(writer, sheet_name='customers', index=False)
                
                # تصدير الفواتير الأخيرة (آخر 1000)
                with db.get_cursor() as cursor:
                    cursor.execute("""
                        SELECT i.*, c.name as customer_name, s.name as sector_name
                        FROM invoices i
                        LEFT JOIN customers c ON i.customer_id = c.id
                        LEFT JOIN sectors s ON i.sector_id = s.id
                        ORDER BY i.payment_date DESC, i.payment_time DESC
                        LIMIT 1000
                    """)
                    invoices = cursor.fetchall()
                    if invoices:
                        df_invoices = pd.DataFrame([dict(i) for i in invoices])
                        df_invoices.to_excel(writer, sheet_name='invoices', index=False)

                # في دالة backup_to_excel_parallel() بعد تصدير الفواتير
                # تصدير السجل التاريخي
                with db.get_cursor() as cursor:
                    cursor.execute('''
                        SELECT h.*, c.name as customer_name
                        FROM customer_history h
                        LEFT JOIN customers c ON h.customer_id = c.id
                        ORDER BY h.created_at DESC
                        LIMIT 5000
                    ''')
                    history = cursor.fetchall()
                    if history:
                        df_history = pd.DataFrame([dict(h) for h in history])
                        df_history.to_excel(writer, sheet_name='history', index=False)

            
            logger.info(f"تم النسخ الاحتياطي الموازي: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في النسخ الاحتياطي الموازي: {e}")
            return False
