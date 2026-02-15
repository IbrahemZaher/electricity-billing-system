# modules/invoices.py
import logging
from datetime import datetime
from typing import List, Dict, Optional
from database.connection import db
from modules.accounting import AccountingEngine

logger = logging.getLogger(__name__)

class InvoiceManager:
    """مدير عمليات الفواتير"""

    def __init__(self):
        self.table_name = "invoices"

    from modules.accounting import AccountingEngine

    def create_invoice(self, invoice_data: Dict) -> Dict:
        """إنشاء فاتورة جديدة (محاسبة + حفظ) مع تسجيل في customer_history"""
        try:
            engine = AccountingEngine(
                kilowatt_price=invoice_data.get('price_per_kilo', 0)
            )

            # 1️⃣ تنفيذ المحاسبة
            result = engine.process_invoice(
                customer_id=invoice_data['customer_id'],
                new_reading=invoice_data['new_reading'],
                visa_amount=invoice_data.get('visa_application', 0),
                discount=invoice_data.get('discount', 0),
                accountant_id=invoice_data.get('user_id')
            )

            if not result.get('success'):
                return result

            with db.get_cursor() as cursor:
                invoice_number = self.generate_invoice_number()

                cursor.execute("""
                    INSERT INTO invoices (
                        invoice_number, customer_id, sector_id, user_id,
                        payment_date, payment_time,
                        kilowatt_amount, free_kilowatt, price_per_kilo,
                        discount, total_amount,
                        previous_reading, new_reading,
                        visa_application, customer_withdrawal,
                        book_number, receipt_number,
                        current_balance, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s)
                    RETURNING id, invoice_number
                """, (
                    invoice_number,
                    invoice_data['customer_id'],
                    invoice_data.get('sector_id'),
                    invoice_data.get('user_id'),
                    datetime.now().date(),
                    datetime.now().time(),
                    result['consumption'],
                    invoice_data.get('free_kilowatt', 0),
                    result['kilowatt_price'],
                    result['discount'],
                    result['total_amount'],
                    result['previous_reading'],
                    result['new_reading'],
                    invoice_data.get('visa_application', 0),
                    invoice_data.get('customer_withdrawal', ''),
                    invoice_data.get('book_number', ''),
                    invoice_data.get('receipt_number', ''),
                    result['new_balance'],
                    'active'
                ))

                invoice = cursor.fetchone()

                # ✅ تسجيل الحدث في customer_history
                cursor.execute("""
                    INSERT INTO customer_history 
                    (customer_id, action_type, transaction_type, 
                    old_value, new_value, amount,
                    current_balance_before, current_balance_after,
                    notes, created_by, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    invoice_data['customer_id'],
                    'invoice_created',                    # action_type
                    'payment',                             # transaction_type
                    result.get('previous_balance', 0),     # old_value (الرصيد قبل)
                    result['new_balance'],                  # new_value (الرصيد بعد)
                    result['total_amount'],                  # amount
                    result.get('previous_balance', 0),      # current_balance_before
                    result['new_balance'],                   # current_balance_after
                    f"إنشاء فاتورة {invoice['invoice_number']} بمبلغ {result['total_amount']}",
                    invoice_data.get('user_id')              # created_by
                ))

            return {
                'success': True,
                'invoice_id': invoice['id'],
                'invoice_number': invoice['invoice_number'],
                **result
            }

        except Exception as e:
            logger.error(f"خطأ في إنشاء الفاتورة: {e}")
            return {'success': False, 'error': str(e)}

            
    def generate_invoice_number(self) -> str:
            """توليد رقم فاتورة تلقائي"""
            try:
                with db.get_cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) as count 
                        FROM invoices 
                        WHERE DATE(created_at) = CURRENT_DATE
                    """)
                    result = cursor.fetchone()
                    count_today = result['count'] + 1
                    date_str = datetime.now().strftime("%Y%m%d")
                    return f"INV-{date_str}-{count_today:04d}"
            except Exception as e:
                logger.error(f"خطأ في توليد رقم الفاتورة: {e}")
                return f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def update_customer_balance(self, customer_id: int, new_balance: float, new_reading: float):
            """تحديث رصيد وقراءة العداد للزبون"""
            try:
                with db.get_cursor() as cursor:
                    cursor.execute("""
                        UPDATE customers 
                        SET current_balance = %s, 
                            last_counter_reading = %s,
                            updated_at = CURRENT_TIMESTAMP 
                        WHERE id = %s
                    """, (new_balance, new_reading, customer_id))
            except Exception as e:
                logger.error(f"خطأ في تحديث رصيد الزبون: {e}")

    def get_invoice(self, invoice_id: int) -> Optional[Dict]:
            """الحصول على بيانات فاتورة"""
            try:
                with db.get_cursor() as cursor:
                    cursor.execute("""
                        SELECT i.*, 
                            c.name as customer_name,
                            c.box_number, c.serial_number,
                            s.name as sector_name,
                            u.full_name as accountant_name
                        FROM invoices i
                        LEFT JOIN customers c ON i.customer_id = c.id
                        LEFT JOIN sectors s ON i.sector_id = s.id
                        LEFT JOIN users u ON i.user_id = u.id
                        WHERE i.id = %s
                    """, (invoice_id,))
                    invoice = cursor.fetchone()
                    return dict(invoice) if invoice else None
            except Exception as e:
                logger.error(f"خطأ في جلب بيانات الفاتورة: {e}")
                return None

    def search_invoices(self, start_date: str = None, end_date: str = None,
                        customer_id: int = None, sector_id: int = None,
                        status: str = None, customer_name: str = None,   # معامل جديد
                        limit: int = 100, offset: int = 0) -> List[Dict]:
        """بحث الفواتير مع إمكانية البحث باسم الزبون"""
        try:
            with db.get_cursor() as cursor:
                query = """
                    SELECT i.*, 
                        c.name as customer_name,
                        s.name as sector_name,
                        u.full_name as accountant_name
                    FROM invoices i
                    LEFT JOIN customers c ON i.customer_id = c.id
                    LEFT JOIN sectors s ON i.sector_id = s.id
                    LEFT JOIN users u ON i.user_id = u.id
                    WHERE 1=1
                """
                params = []

                if start_date:
                    query += " AND i.payment_date >= %s"
                    params.append(start_date)
                if end_date:
                    query += " AND i.payment_date <= %s"
                    params.append(end_date)
                if customer_id:
                    query += " AND i.customer_id = %s"
                    params.append(customer_id)
                if sector_id:
                    query += " AND i.sector_id = %s"
                    params.append(sector_id)
                if status:
                    query += " AND i.status = %s"
                    params.append(status)
                if customer_name:
                    query += " AND c.name ILIKE %s"   # ILIKE للبحث غير الحساس لحالة الأحرف
                    params.append(f"%{customer_name}%")

                query += " ORDER BY i.created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])

                cursor.execute(query, params)
                invoices = cursor.fetchall()
                return [dict(invoice) for invoice in invoices]
        except Exception as e:
            logger.error(f"خطأ في بحث الفواتير: {e}")
            return []

    def update_invoice(self, invoice_id: int, update_data: Dict) -> Dict:
        """تحديث بيانات الفاتورة مع تسجيل التغيير في customer_history"""
        try:
            # 1. جلب الفاتورة القديمة
            old_invoice = self.get_invoice(invoice_id)
            if not old_invoice:
                return {'success': False, 'error': 'الفاتورة غير موجودة'}

            old_balance = old_invoice['current_balance']
            old_reading = old_invoice['new_reading']
            customer_id = old_invoice['customer_id']

            set_clauses = []
            params = []

            for field, value in update_data.items():
                if field in ['customer_id', 'sector_id', 'user_id',
                            'payment_date', 'payment_time', 'kilowatt_amount',
                            'free_kilowatt', 'price_per_kilo', 'discount',
                            'total_amount', 'previous_reading', 'new_reading',
                            'visa_application', 'customer_withdrawal',
                            'book_number', 'receipt_number', 'current_balance',
                            'telegram_password', 'status']:
                    set_clauses.append(f"{field} = %s")
                    params.append(value)

            if not set_clauses:
                return {'success': False, 'error': 'لا توجد بيانات للتحديث'}

            params.append(invoice_id)
            query = f"""
                UPDATE invoices 
                SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP 
                WHERE id = %s 
                RETURNING id, invoice_number, current_balance, new_reading
            """

            with db.get_cursor() as cursor:
                cursor.execute(query, params)
                updated = cursor.fetchone()

                if not updated:
                    return {'success': False, 'error': 'الفاتورة غير موجودة'}

                # 3. التحقق مما إذا كان الرصيد أو القراءة قد تغيرا
                new_balance = updated['current_balance']
                new_reading = updated['new_reading']
                changed = False

                # إذا تغير الرصيد أو القراءة، قم بتحديث الزبون وتسجيل الحدث
                if abs(new_balance - old_balance) > 0.01 or abs(new_reading - old_reading) > 0.01:
                    # تحديث رصيد الزبون وقراءته (إذا لم يتم بالفعل)
                    self.update_customer_balance(customer_id, new_balance, new_reading)
                    changed = True

                # تسجيل الحدث في customer_history إذا كان هناك تغيير
                if changed:
                    cursor.execute("""
                        INSERT INTO customer_history 
                        (customer_id, action_type, transaction_type, 
                        old_value, new_value, amount,
                        current_balance_before, current_balance_after,
                        notes, created_by, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, (
                        customer_id,
                        'invoice_updated',                               # action_type
                        'adjustment',                                    # transaction_type
                        old_balance,                                     # old_value
                        new_balance,                                     # new_value
                        abs(new_balance - old_balance),                  # amount (مقدار التغيير)
                        old_balance,                                     # current_balance_before
                        new_balance,                                     # current_balance_after
                        f"تعديل الفاتورة {updated['invoice_number']} - تغير الرصيد من {old_balance} إلى {new_balance}",
                        update_data.get('user_id')                       # created_by
                    ))

                logger.info(f"تم تحديث الفاتورة: {updated['invoice_number']}")
                return {
                    'success': True,
                    'message': f"تم تحديث الفاتورة {updated['invoice_number']} بنجاح"
                }

        except Exception as e:
            logger.error(f"خطأ في تحديث الفاتورة: {e}")
            return {'success': False, 'error': f'فشل تحديث الفاتورة: {str(e)}'}

            

    def cancel_invoice(self, invoice_id: int, user_id: int = None) -> Dict:
        """
        إلغاء الفاتورة مع عكس التأثير على الزبون (استعادة الرصيد وقراءة العداد)
        وتسجيل الحدث في سجل الزبون (customer_history)
        """
        try:
            with db.get_cursor() as cursor:
                # 1. التحقق من وجود الفاتورة وأنها نشطة
                cursor.execute("""
                    SELECT customer_id, kilowatt_amount, free_kilowatt, 
                        previous_reading, new_reading, current_balance,
                        invoice_number
                    FROM invoices 
                    WHERE id = %s AND status = 'active'
                """, (invoice_id,))
                invoice = cursor.fetchone()
                if not invoice:
                    return {'success': False, 'error': 'الفاتورة غير موجودة أو ملغاة سابقاً'}

                # 2. جلب بيانات الزبون الحالية
                cursor.execute("""
                    SELECT current_balance, last_counter_reading 
                    FROM customers 
                    WHERE id = %s
                """, (invoice['customer_id'],))
                customer = cursor.fetchone()
                if not customer:
                    return {'success': False, 'error': 'الزبون غير موجود'}

                # 3. حساب الكمية الإجمالية المستهلكة في الفاتورة (تحويل إلى float)
                kilowatt_amount = float(invoice['kilowatt_amount'])
                free_kilowatt = float(invoice['free_kilowatt'])
                total_kilowatt = kilowatt_amount + free_kilowatt

                # 4. حساب الرصيد الجديد والقراءة الجديدة بعد الإلغاء (طرح الكمية)
                #    تحويل قيم الزبون إلى float
                current_balance = float(customer['current_balance'])
                last_reading = float(customer['last_counter_reading'])
                
                restored_balance = current_balance - total_kilowatt
                restored_reading = last_reading - total_kilowatt

                # 5. تحديث رصيد الزبون وقراءة العداد
                cursor.execute("""
                    UPDATE customers 
                    SET current_balance = %s, 
                        last_counter_reading = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (restored_balance, restored_reading, invoice['customer_id']))

                # 6. تحديث حالة الفاتورة إلى ملغاة
                cursor.execute("""
                    UPDATE invoices 
                    SET status = 'cancelled', 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (invoice_id,))

                # 7. تسجيل الحدث في customer_history
                created_by = user_id if user_id is not None else 1

                # تحويل invoice['current_balance'] إلى float
                invoice_balance = float(invoice['current_balance'])

                cursor.execute("""
                    INSERT INTO customer_history 
                    (customer_id, action_type, transaction_type, 
                    old_value, new_value, amount,
                    current_balance_before, current_balance_after,
                    notes, created_by, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    invoice['customer_id'],
                    'invoice_cancelled',
                    'refund',
                    invoice_balance,
                    restored_balance,
                    total_kilowatt,
                    invoice_balance,
                    restored_balance,
                    f"إلغاء الفاتورة {invoice['invoice_number']} واسترداد {total_kilowatt} كيلو واط",
                    created_by
                ))

                logger.info(f"تم إلغاء الفاتورة {invoice['invoice_number']} واستعادة رصيد الزبون")
                return {
                    'success': True,
                    'message': f"تم إلغاء الفاتورة {invoice['invoice_number']} واستعادة رصيد الزبون"
                }

        except Exception as e:
            logger.error(f"خطأ في إلغاء الفاتورة: {e}")
            return {'success': False, 'error': str(e)}

    def delete_invoice(self, invoice_id: int, user_id: int = None) -> Dict:
        """
        حذف الفاتورة فعلياً بعد استعادة تأثيرها على الزبون (إذا كانت نشطة).
        إذا كانت الفاتورة ملغاة، يتم الحذف فقط دون تعديل الرصيد.
        """
        try:
            with db.get_cursor() as cursor:
                # 1. جلب بيانات الفاتورة قبل الحذف
                cursor.execute("""
                    SELECT customer_id, kilowatt_amount, free_kilowatt, 
                        previous_reading, new_reading, current_balance,
                        invoice_number, status
                    FROM invoices 
                    WHERE id = %s
                """, (invoice_id,))
                invoice = cursor.fetchone()
                if not invoice:
                    return {'success': False, 'error': 'الفاتورة غير موجودة'}

                # إذا كانت الفاتورة ملغاة، لا نعدل رصيد الزبون
                if invoice['status'] == 'cancelled':
                    # حذف الفاتورة مباشرة
                    cursor.execute("DELETE FROM invoices WHERE id = %s RETURNING invoice_number", (invoice_id,))
                    result = cursor.fetchone()
                    logger.info(f"تم حذف الفاتورة الملغاة: {result['invoice_number']}")
                    return {
                        'success': True,
                        'message': f"تم حذف الفاتورة الملغاة {result['invoice_number']}"
                    }

                # باقي الكود (إذا كانت الفاتورة نشطة) كما هو...
                # 2. جلب بيانات الزبون الحالية
                cursor.execute("""
                    SELECT current_balance, last_counter_reading 
                    FROM customers 
                    WHERE id = %s
                """, (invoice['customer_id'],))
                customer = cursor.fetchone()
                if not customer:
                    return {'success': False, 'error': 'الزبون غير موجود'}

                # 3. حساب الكمية الإجمالية
                kilowatt_amount = float(invoice['kilowatt_amount'])
                free_kilowatt = float(invoice['free_kilowatt'])
                total_kilowatt = kilowatt_amount + free_kilowatt

                # 4. حساب الرصيد والقراءة بعد الحذف (نطرح الكمية)
                current_balance = float(customer['current_balance'])
                last_reading = float(customer['last_counter_reading'])
                new_balance = current_balance - total_kilowatt
                new_reading = last_reading - total_kilowatt

                # 5. تحديث الزبون
                cursor.execute("""
                    UPDATE customers 
                    SET current_balance = %s, 
                        last_counter_reading = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (new_balance, new_reading, invoice['customer_id']))

                # 6. تسجيل الحدث في customer_history
                created_by = user_id if user_id is not None else 1
                invoice_balance = float(invoice['current_balance'])

                cursor.execute("""
                    INSERT INTO customer_history 
                    (customer_id, action_type, transaction_type, 
                    old_value, new_value, amount,
                    current_balance_before, current_balance_after,
                    notes, created_by, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    invoice['customer_id'],
                    'invoice_deleted',
                    'refund',
                    invoice_balance,
                    new_balance,
                    total_kilowatt,
                    invoice_balance,
                    new_balance,
                    f"حذف الفاتورة {invoice['invoice_number']} واسترداد {total_kilowatt} كيلو واط",
                    created_by
                ))

                # 7. حذف الفاتورة
                cursor.execute("DELETE FROM invoices WHERE id = %s RETURNING invoice_number", (invoice_id,))
                result = cursor.fetchone()

                logger.info(f"تم حذف الفاتورة: {result['invoice_number']} واستعادة رصيد الزبون")
                return {
                    'success': True,
                    'message': f"تم حذف الفاتورة {result['invoice_number']} واستعادة رصيد الزبون"
                }

        except Exception as e:
            logger.error(f"خطأ في حذف الفاتورة: {e}")
            return {'success': False, 'error': str(e)}




    def get_daily_summary(self, date: str = None) -> Dict:
            """الحصول على ملخص المبيعات اليومية"""
            try:
                if not date:
                    date = datetime.now().strftime("%Y-%m-%d")

                with db.get_cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_invoices,
                            SUM(total_amount) as total_amount,
                            SUM(kilowatt_amount) as total_kilowatts,
                            SUM(free_kilowatt) as total_free_kilowatts,
                            SUM(discount) as total_discount
                        FROM invoices 
                        WHERE payment_date = %s AND status = 'active'
                    """, (date,))
                    result = cursor.fetchone()

                    return {
                        'date': date,
                        'total_invoices': result['total_invoices'] or 0,
                        'total_amount': float(result['total_amount'] or 0),
                        'total_kilowatts': float(result['total_kilowatts'] or 0),
                        'total_free_kilowatts': float(result['total_free_kilowatts'] or 0),
                        'total_discount': float(result['total_discount'] or 0)
                    }
            except Exception as e:
                logger.error(f"خطأ في جلب الملخص اليومي: {e}")
                return {}