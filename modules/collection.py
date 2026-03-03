# modules/collection.py
import logging
from datetime import datetime
from database.connection import db
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class CollectionManager:
    """مدير عمليات التحصيل الميداني"""

    def record_collection(self, collector_id: int, customer_id: int,
                        collected_amount: float, notes: str = '',
                        lat: Optional[float] = None, lon: Optional[float] = None) -> Dict:
        """تسجيل عملية تحصيل جديدة مع تحديث رصيد الزبون"""
        try:
            with db.get_cursor() as cursor:
                # قفل الزبون للتحديث
                cursor.execute("SELECT current_balance FROM customers WHERE id = %s FOR UPDATE", (customer_id,))
                cust = cursor.fetchone()
                if not cust:
                    return {'success': False, 'error': 'الزبون غير موجود'}

                old_balance = cust['current_balance'] or 0
                new_balance = old_balance + collected_amount   # إضافة المبلغ المحصل (يقلل الدين)

                # تحديث رصيد الزبون
                cursor.execute("""
                    UPDATE customers 
                    SET current_balance = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (new_balance, customer_id))

                # إدراج سجل التحصيل
                cursor.execute("""
                    INSERT INTO collection_logs
                    (collector_id, customer_id, collected_amount, expected_amount, notes, location_lat, location_lon)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (collector_id, customer_id, collected_amount, old_balance, notes, lat, lon))
                log_id = cursor.fetchone()['id']

                # تسجيل في customer_history
                cursor.execute("""
                    INSERT INTO customer_history
                    (customer_id, action_type, transaction_type, old_value, new_value, amount,
                    current_balance_before, current_balance_after, notes, created_by, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    customer_id, 'collection', 'mobile_collection',
                    old_balance, new_balance, collected_amount,
                    old_balance, new_balance,
                    f'تحصيل ميداني: {collected_amount} ك.و - {notes}',
                    collector_id
                ))

                logger.info(f"تم تسجيل تحصيل {collected_amount} للزبون {customer_id} بواسطة المحصل {collector_id}")
                return {'success': True, 'log_id': log_id, 'new_balance': new_balance}
        except Exception as e:
            logger.error(f"خطأ في تسجيل التحصيل: {e}")
            return {'success': False, 'error': str(e)}


    def get_last_payment(self, customer_id: int) -> Optional[Dict]:
        """الحصول على آخر دفعة لزبون (من الفواتير أو التحصيلات)"""
        try:
            with db.get_cursor() as cursor:
                # آخر فاتورة (payment_date + payment_time)
                cursor.execute("""
                    SELECT 
                        (payment_date + payment_time) as payment_datetime,
                        total_amount as amount,
                        'invoice' as source
                    FROM invoices
                    WHERE customer_id = %s AND status = 'active'
                    ORDER BY payment_date DESC, payment_time DESC
                    LIMIT 1
                """, (customer_id,))
                invoice = cursor.fetchone()

                # آخر تحصيل
                cursor.execute("""
                    SELECT 
                        collection_date as payment_datetime,
                        collected_amount as amount,
                        'collection' as source
                    FROM collection_logs
                    WHERE customer_id = %s
                    ORDER BY collection_date DESC
                    LIMIT 1
                """, (customer_id,))
                collection = cursor.fetchone()

                # اختيار الأحدث
                last = None
                if invoice and collection:
                    if invoice['payment_datetime'] > collection['payment_datetime']:
                        last = invoice
                    else:
                        last = collection
                elif invoice:
                    last = invoice
                elif collection:
                    last = collection

                return last
        except Exception as e:
            logger.error(f"خطأ في جلب آخر دفعة: {e}")
            return None


    def get_collector_performance(self, collector_id: int, start_date: str, end_date: str) -> Dict:
        """إحصائيات أداء محصل معين خلال فترة"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_collections,
                        SUM(collected_amount) as total_collected,
                        AVG(collected_amount) as avg_collection,
                        MIN(collected_amount) as min_collection,
                        MAX(collected_amount) as max_collection,
                        COUNT(DISTINCT customer_id) as unique_customers
                    FROM collection_logs
                    WHERE collector_id = %s
                      AND collection_date BETWEEN %s::timestamp AND %s::timestamp
                """, (collector_id, start_date, end_date))

                stats = cursor.fetchone()

                # جلب الزبائن المخصصين لهذا المحصل الذين لم يتم تحصيلهم خلال الفترة
                cursor.execute("""
                    SELECT c.id, c.name, c.current_balance
                    FROM customers c
                    LEFT JOIN collection_logs cl ON c.id = cl.customer_id
                        AND cl.collector_id = %s
                        AND cl.collection_date BETWEEN %s::timestamp AND %s::timestamp
                    WHERE c.assigned_collector_id = %s AND c.is_active = TRUE
                      AND cl.id IS NULL
                """, (collector_id, start_date, end_date, collector_id))

                pending = cursor.fetchall()

                return {
                    'success': True,
                    'stats': dict(stats) if stats else {},
                    'pending_customers': [dict(p) for p in pending]
                }
        except Exception as e:
            logger.error(f"خطأ في جلب أداء المحصل: {e}")
            return {'success': False, 'error': str(e)}