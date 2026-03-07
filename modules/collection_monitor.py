"""
modules/collection_monitor.py
وحدة تحليل متابعة الجباية وتصنيف المتأخرين مع إضافة تصنيف السحب ودفع الأسبوعي
"""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from database.connection import db
import logging

logger = logging.getLogger(__name__)

class CollectionMonitor:
    """
    محلل متابعة الدفعات وتصنيف المتأخرين حسب الأسابيع مع تحليل السحب.
    """

    def __init__(self):
        self.categories = {
            'on_time': {'range': (0, 0), 'name': '⏱️ مدفوع خلال الأسبوع', 'color': '#27ae60'},
            'week_1': {'range': (1, 7), 'name': '⚠️ متأخر أسبوع واحد', 'color': '#f39c12'},
            'week_2': {'range': (8, 14), 'name': '⚠️ متأخر أسبوعين', 'color': '#e67e22'},
            'week_3': {'range': (15, 21), 'name': '🔴 متأخر 3 أسابيع', 'color': '#e74c3c'},
            'week_4': {'range': (22, 28), 'name': '🔴 متأخر 4 أسابيع', 'color': '#c0392b'},
            'week_5_plus': {'range': (29, None), 'name': '💀 متأخر 5 أسابيع فأكثر (لا يدفع أبداً)', 'color': '#7f8c8d'}
        }

        # خريطة التصنيفات المالية (للترجمة والفلترة)
        self.financial_category_map = {
            'normal': 'عادي',
            'free': 'مجاني',
            'vip': 'VIP',
            'free_vip': 'مجاني+VIP',
            'mobile_accountant': 'محاسبة جوالة'
        }

    def get_last_payment_date(self, customer_id: int) -> date | None:
        """جلب تاريخ آخر دفعة للزبون"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT MAX(payment_date) as last_date
                    FROM invoices
                    WHERE customer_id = %s AND status = 'active'
                """, (customer_id,))
                row = cursor.fetchone()
                if row and row['last_date']:
                    return row['last_date']
                return None
        except Exception as e:
            logger.error(f"خطأ في جلب آخر دفعة للزبون {customer_id}: {e}")
            return None

    def get_average_weekly_consumption(self, customer_id: int, weeks: int = 8) -> float:
        """
        حساب متوسط الاستهلاك الأسبوعي بناءً على آخر 'weeks' أسبوع من الفواتير.
        """
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT kilowatt_amount, payment_date
                    FROM invoices
                    WHERE customer_id = %s AND status = 'active'
                    ORDER BY payment_date DESC
                    LIMIT 20
                """, (customer_id,))
                rows = cursor.fetchall()
                if not rows:
                    return 0.0
                amounts = [float(r['kilowatt_amount']) for r in rows if r['kilowatt_amount']]
                if not amounts:
                    return 0.0
                return sum(amounts) / len(amounts)
        except Exception as e:
            logger.error(f"خطأ في حساب متوسط استهلاك الزبون {customer_id}: {e}")
            return 0.0

    def get_last_visa_date(self, customer_id: int) -> date | None:
        """جلب آخر تاريخ تم فيه تعديل التأشيرة من customer_history"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT MAX(created_at) as last_visa_date
                    FROM customer_history
                    WHERE customer_id = %s AND transaction_type IN ('weekly_visa', 'visa_update', 'visa_adjustment')
                """, (customer_id,))
                row = cursor.fetchone()
                if row and row['last_visa_date']:
                    # تحويل timestamp إلى date
                    return row['last_visa_date'].date()
                return None
        except Exception as e:
            logger.error(f"خطأ في جلب آخر تاريخ تأشيرة للزبون {customer_id}: {e}")
            return None

    def get_last_week_invoice(self, customer_id: int) -> Dict | None:
        """جلب آخر فاتورة خلال آخر 7 أيام"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT kilowatt_amount, free_kilowatt
                    FROM invoices
                    WHERE customer_id = %s
                      AND payment_date >= CURRENT_DATE - INTERVAL '7 days'
                      AND status = 'active'
                    ORDER BY payment_date DESC
                    LIMIT 1
                """, (customer_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'kilowatt_amount': float(row['kilowatt_amount']),
                        'free_kilowatt': float(row['free_kilowatt'])
                    }
                return None
        except Exception as e:
            logger.error(f"خطأ في جلب آخر فاتورة للزبون {customer_id}: {e}")
            return None

    def get_withdrawal_classification(self, withdrawal: float, last_visa_date: date | None = None) -> str:
        """
        تصنيف السحب بناءً على قيمته وتاريخ آخر تأشيرة (إذا كان السحب صفر).
        """
        if withdrawal > 0:
            if withdrawal < 10:
                return 'سحب بسيط'
            elif withdrawal < 20:
                return 'سحب متوسط'
            elif withdrawal < 30:
                return 'سحب كبير'
            else:
                return 'سحب كبير جداً'
        else:  # withdrawal == 0
            if last_visa_date is None:
                return 'لا توجد تأشيرات'
            days_since_visa = (datetime.now().date() - last_visa_date).days
            if days_since_visa >= 21:
                return 'سحبه ثابت (منذ 3 أسابيع)'
            elif days_since_visa >= 14:
                return 'ثابت لمدة أسبوعين'
            else:
                return 'سحب صفر (حديث)'

    def classify_customer(self, customer_id: int, last_payment_date: date | None,
                          current_balance: float, visa_balance: float,
                          last_counter_reading: float, withdrawal_amount: float,
                          financial_category: str) -> Dict[str, Any]:
        """
        تصنيف زبون بناءً على تاريخ آخر دفعة وقيمة السحب.
        """
        today = datetime.now().date()
        if last_payment_date is None:
            days_overdue = 999
        else:
            days_overdue = (today - last_payment_date).days

        weeks_overdue = days_overdue // 7

        # تحديد فئة التأخير
        if days_overdue <= 7:
            category_key = 'on_time'
        elif weeks_overdue == 1:
            category_key = 'week_1'
        elif weeks_overdue == 2:
            category_key = 'week_2'
        elif weeks_overdue == 3:
            category_key = 'week_3'
        elif weeks_overdue == 4:
            category_key = 'week_4'
        else:
            category_key = 'week_5_plus'

        # حساب المبلغ المستحق التقديري
        avg_weekly = self.get_average_weekly_consumption(customer_id)
        # نفترض أن الأسبوع الأول لا يحسب كمتأخر إذا كان ضمن الأسبوع الجاري
        estimated_due = avg_weekly * max(0, weeks_overdue - 1) if weeks_overdue > 1 else 0.0

        # جلب آخر تاريخ تأشيرة (لتصنيف السحب)
        last_visa_date = self.get_last_visa_date(customer_id)
        withdrawal_class = self.get_withdrawal_classification(withdrawal_amount, last_visa_date)

        # حساب دفع السحب الأسبوعي
        last_week_invoice = self.get_last_week_invoice(customer_id)
        if last_week_invoice and withdrawal_amount > 0:
            total_paid = last_week_invoice['kilowatt_amount'] + last_week_invoice['free_kilowatt']
            paid_weekly = 'نعم' if total_paid >= withdrawal_amount else 'لا'
        elif last_week_invoice and withdrawal_amount == 0:
            # إذا كان السحب صفر، يمكن اعتبار أي دفعة تغطي الصفر = نعم (أو لا توجد حاجة)
            paid_weekly = 'لا ينطبق'
        else:
            paid_weekly = 'لا (لا توجد فاتورة)'

        # التصنيف المالي بالعربية
        financial_category_arabic = self.financial_category_map.get(financial_category, financial_category or 'غير محدد')

        return {
            'customer_id': customer_id,
            'last_payment': last_payment_date,
            'days_overdue': days_overdue,
            'weeks_overdue': weeks_overdue,
            'category_key': category_key,
            'category_name': self.categories[category_key]['name'],
            'color': self.categories[category_key]['color'],
            'estimated_due': estimated_due,
            'current_balance': current_balance,
            'visa_balance': visa_balance,
            'last_counter_reading': last_counter_reading,
            'withdrawal_amount': withdrawal_amount,
            'withdrawal_class': withdrawal_class,
            'paid_weekly': paid_weekly,
            'financial_category': financial_category,
            'financial_category_arabic': financial_category_arabic
        }

    def get_all_classifications(self, sector_id: int = None, financial_category: str = None) -> Dict[str, Any]:
        """
        الحصول على تصنيف جميع الزبائن (اختيارياً حسب القطاع والتصنيف المالي)
        """
        try:
            with db.get_cursor() as cursor:
                # جلب جميع الزبائن النشطين مع البيانات المطلوبة، فقط نوع 'زبون'
                query = """
                    SELECT
                        c.id,
                        c.name,
                        c.box_number,
                        c.sector_id,
                        s.name as sector_name,
                        c.current_balance,
                        c.visa_balance,
                        c.last_counter_reading,
                        c.withdrawal_amount,
                        c.financial_category
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.is_active = TRUE
                    AND c.meter_type = 'زبون'
                """
                params = []
                if sector_id:
                    query += " AND c.sector_id = %s"
                    params.append(sector_id)
                if financial_category:
                    query += " AND c.financial_category = %s"
                    params.append(financial_category)

                cursor.execute(query, params)
                customers = cursor.fetchall()

                classifications = []
                for cust in customers:
                    last_date = self.get_last_payment_date(cust['id'])
                    classification = self.classify_customer(
                        cust['id'],
                        last_date,
                        cust.get('current_balance', 0),
                        cust.get('visa_balance', 0),
                        cust.get('last_counter_reading', 0),
                        cust.get('withdrawal_amount', 0),
                        cust.get('financial_category', 'normal')
                    )
                    classification['name'] = cust['name']
                    classification['box_number'] = cust.get('box_number', '')
                    classification['sector_name'] = cust.get('sector_name', 'بدون قطاع')
                    classification['sector_id'] = cust.get('sector_id')
                    classifications.append(classification)

                # تجميع حسب الفئة (للملخص السريع)
                grouped = {}
                for cat_key, cat_info in self.categories.items():
                    grouped[cat_key] = {
                        'name': cat_info['name'],
                        'color': cat_info['color'],
                        'customers': [],
                        'total_estimated_due': 0.0,
                        'count': 0
                    }

                for cls in classifications:
                    key = cls['category_key']
                    grouped[key]['customers'].append(cls)
                    grouped[key]['count'] += 1
                    grouped[key]['total_estimated_due'] += cls['estimated_due']

                return {
                    'success': True,
                    'grouped': grouped,
                    'all_customers': classifications,
                    'total_customers': len(classifications),
                    'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

        except Exception as e:
            logger.error(f"خطأ في تصنيف الزبائن: {e}")
            return {'success': False, 'error': str(e)}