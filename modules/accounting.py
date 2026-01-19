# modules/accounting.py

import logging
from datetime import datetime
from database.connection import db

logger = logging.getLogger(__name__)

class AccountingEngine:
    """
    محرك المحاسبة الرئيسي
    مسؤول عن:
    - حساب الاستهلاك
    - حساب المبلغ
    - تحديث رصيد الزبون
    - تحديث قراءة العداد
    """

    def __init__(self, kilowatt_price: float):
        self.kilowatt_price = kilowatt_price

    # =========================
    # الحسابات الأساسية
    # =========================

    def calculate_consumption(self, previous_reading: float, new_reading: float) -> float:
        """حساب الاستهلاك"""
        if new_reading < previous_reading:
            raise ValueError("القراءة الجديدة أقل من القراءة السابقة")

        return new_reading - previous_reading

    def calculate_amount(self, consumption: float) -> float:
        """حساب المبلغ المستحق"""
        return consumption * self.kilowatt_price

    # =========================
    # العملية الكاملة للفاتورة
    # =========================

    def process_invoice(
        self,
        customer_id: int,
        kilowatt_amount: float,      # كمية الدفع (بدلاً من new_reading)
        free_kilowatt: float = 0,    # المجاني
        visa_amount: float = 0,
        discount: float = 0,
        accountant_id: int = None
    ) -> dict:
        """تنفيذ عملية محاسبة كاملة للفاتورة"""
        try:
            with db.get_cursor() as cursor:
                # 1. جلب بيانات الزبون
                cursor.execute("""
                    SELECT id, name, current_balance, last_counter_reading
                    FROM customers
                    WHERE id = %s AND is_active = TRUE
                """, (customer_id,))
                customer = cursor.fetchone()
                if not customer:
                    return {'success': False, 'error': 'الزبون غير موجود'}
                
                previous_reading = float(customer['last_counter_reading'] or 0)
                current_balance = float(customer['current_balance'] or 0)
                
                # 2. الحسابات الجديدة (مثل البرنامج البسيط)
                # القراءة الجديدة = القراءة السابقة + كمية الدفع + المجاني
                new_reading = previous_reading + kilowatt_amount + free_kilowatt
                
                # المبلغ = (كمية الدفع * سعر الكيلو) - الحسم
                amount = kilowatt_amount * self.kilowatt_price
                total_amount = amount - discount
                
                # الرصيد الجديد = الرصيد القديم + كمية الدفع + المجاني
                new_balance = current_balance + kilowatt_amount + free_kilowatt
                
                # 3. تحديث بيانات الزبون
                cursor.execute("""
                    UPDATE customers
                    SET
                        current_balance = %s,
                        last_counter_reading = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (
                    new_balance,
                    new_reading,
                    customer_id
                ))
                
                logger.info(
                    f"محاسبة زبون {customer['name']} | "
                    f"كمية الدفع: {kilowatt_amount} | المجاني: {free_kilowatt} | "
                    f"المبلغ: {total_amount}"
                )
                
                # 4. إرجاع البيانات
                return {
                    'success': True,
                    'customer_id': customer_id,
                    'customer_name': customer['name'],
                    'previous_reading': previous_reading,
                    'new_reading': new_reading,
                    'kilowatt_amount': kilowatt_amount,
                    'free_kilowatt': free_kilowatt,
                    'consumption': kilowatt_amount + free_kilowatt,  # إجمالي الاستهلاك
                    'kilowatt_price': self.kilowatt_price,
                    'amount': amount,
                    'discount': discount,
                    'visa_amount': visa_amount,
                    'total_amount': total_amount,
                    'new_balance': new_balance,
                    'processed_at': datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                
        except Exception as e:
            logger.error(f"خطأ في المحاسبة: {e}")
            return {'success': False, 'error': str(e)}
