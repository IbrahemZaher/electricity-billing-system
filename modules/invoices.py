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
        """إنشاء فاتورة جديدة (محاسبة + حفظ)"""
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
                            status: str = None, limit: int = 100, offset: int = 0) -> List[Dict]:
            """بحث الفواتير"""
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

                    query += " ORDER BY i.created_at DESC LIMIT %s OFFSET %s"
                    params.extend([limit, offset])

                    cursor.execute(query, params)
                    invoices = cursor.fetchall()
                    return [dict(invoice) for invoice in invoices]
            except Exception as e:
                logger.error(f"خطأ في بحث الفواتير: {e}")
                return []

    def update_invoice(self, invoice_id: int, update_data: Dict) -> Dict:
            """تحديث بيانات الفاتورة"""
            try:
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
                    RETURNING id, invoice_number
                """

                with db.get_cursor() as cursor:
                    cursor.execute(query, params)
                    result = cursor.fetchone()

                    if result:
                        # إذا تم تحديث الرصيد، قم بتحديث رصيد الزبون
                        if 'current_balance' in update_data or 'new_reading' in update_data:
                            self.update_customer_balance(
                                update_data.get('customer_id'),
                                update_data.get('current_balance', 0),
                                update_data.get('new_reading', 0)
                            )

                        logger.info(f"تم تحديث الفاتورة: {result['invoice_number']}")
                        return {
                            'success': True,
                            'message': f"تم تحديث الفاتورة {result['invoice_number']} بنجاح"
                        }
                    else:
                        return {'success': False, 'error': 'الفاتورة غير موجودة'}

            except Exception as e:
                logger.error(f"خطأ في تحديث الفاتورة: {e}")
                return {'success': False, 'error': f'فشل تحديث الفاتورة: {str(e)}'}

    def delete_invoice(self, invoice_id: int) -> Dict:
            """حذف الفاتورة"""
            try:
                with db.get_cursor() as cursor:
                    # جلب بيانات الفاتورة قبل الحذف
                    cursor.execute("""
                        SELECT customer_id, current_balance, new_reading 
                        FROM invoices 
                        WHERE id = %s
                    """, (invoice_id,))
                    invoice = cursor.fetchone()

                    if not invoice:
                        return {'success': False, 'error': 'الفاتورة غير موجودة'}

                    # حذف الفاتورة
                    cursor.execute("DELETE FROM invoices WHERE id = %s RETURNING invoice_number", (invoice_id,))
                    result = cursor.fetchone()

                    # إعادة ضبط رصيد الزبون (إذا لزم الأمر)
                    # يمكنك تعديل هذا المنطق حسب احتياجاتك

                    logger.info(f"تم حذف الفاتورة: {result['invoice_number']}")
                    return {
                        'success': True,
                        'message': f"تم حذف الفاتورة {result['invoice_number']} بنجاح"
                    }
            except Exception as e:
                logger.error(f"خطأ في حذف الفاتورة: {e}")
                return {'success': False, 'error': f'فشل حذف الفاتورة: {str(e)}'}

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