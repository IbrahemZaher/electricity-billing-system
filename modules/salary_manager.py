# modules/salary_manager.py

import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Union
from database.connection import db
from modules.daily_cash import DailyCashManager   # استيراد مدير الصندوق اليومي

logger = logging.getLogger(__name__)

class SalaryManager:
    """مدير رواتب الموظفين وسلفهم مع التسجيل التلقائي في دفتر اليومية"""

    def __init__(self):
        self.daily_mgr = DailyCashManager()

    # ------------------- دوال مساعدة -------------------
    @staticmethod
    def _to_date(d: Union[str, date, datetime]) -> date:
        """تحويل المدخل إلى كائن date"""
        if isinstance(d, date):
            return d
        if isinstance(d, datetime):
            return d.date()
        if isinstance(d, str):
            # محاولة تحليل الصيغة YYYY-MM-DD
            try:
                return datetime.strptime(d, '%Y-%m-%d').date()
            except ValueError:
                # محاولة صيغ أخرى إن وجدت
                for fmt in ('%d/%m/%Y', '%m/%d/%Y', '%Y%m%d'):
                    try:
                        return datetime.strptime(d, fmt).date()
                    except ValueError:
                        continue
                raise ValueError(f"صيغة التاريخ غير مدعومة: {d}")
        raise TypeError(f"نوع غير مدعوم للتاريخ: {type(d)}")

    @staticmethod
    def _get_current_user_id() -> Optional[int]:
        """محاولة جلب معرف المستخدم الحالي من الجلسة دون استيراد دائري"""
        try:
            # استيراد متأخر لتجنب الاستيراد الدائري
            from auth.session import Session
            session = Session()
            current_user = session.get_current_user()
            if current_user and 'id' in current_user:
                return current_user['id']
        except Exception as e:
            logger.warning(f"تعذر جلب معرف المستخدم الحالي: {e}")
        return None

    def _get_employee_name(self, employee_id: int) -> str:
        """جلب اسم الموظف من قاعدة البيانات"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT name FROM employees WHERE id = %s", (employee_id,))
                row = cursor.fetchone()
                if row:
                    return row['name']
                return f"موظف {employee_id}"
        except Exception as e:
            logger.error(f"خطأ في جلب اسم الموظف {employee_id}: {e}")
            return f"موظف {employee_id}"

    # ------------------- إدارة الموظفين -------------------
    def add_employee(self, name: str, base_salary: float, hire_date: date, notes: str = '') -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO employees (name, base_salary, hire_date, notes)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (name, base_salary, hire_date, notes))
                return {'success': True, 'id': cursor.fetchone()['id']}
        except Exception as e:
            logger.error(f"خطأ في إضافة موظف: {e}")
            return {'success': False, 'error': str(e)}

    def update_employee(self, employee_id: int, name: str, base_salary: float, hire_date: date, is_active: bool, notes: str = '') -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE employees
                    SET name = %s, base_salary = %s, hire_date = %s, is_active = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (name, base_salary, hire_date, is_active, notes, employee_id))
                return {'success': True}
        except Exception as e:
            logger.error(f"خطأ في تحديث موظف: {e}")
            return {'success': False, 'error': str(e)}

    def delete_employee(self, employee_id: int) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("DELETE FROM employees WHERE id = %s", (employee_id,))
                return {'success': True}
        except Exception as e:
            logger.error(f"خطأ في حذف موظف: {e}")
            return {'success': False, 'error': str(e)}

    def get_all_employees(self, active_only: bool = True) -> List[Dict]:
        try:
            with db.get_cursor() as cursor:
                query = "SELECT id, name, base_salary, hire_date, notes, is_active, created_at FROM employees"
                if active_only:
                    query += " WHERE is_active = TRUE"
                query += " ORDER BY name"
                cursor.execute(query)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"خطأ في جلب قائمة الموظفين: {e}")
            return []

    def get_employee(self, employee_id: int) -> Optional[Dict]:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT * FROM employees WHERE id = %s", (employee_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"خطأ في جلب بيانات الموظف: {e}")
            return None

    # ------------------- سلف -------------------
    def add_advance(self, employee_id: int, amount: float, advance_date: Union[str, date],
                    reason: str = '', user_id: int = None) -> Dict:
        """
        إضافة سلفة جديدة وتسجيلها كمصروف في دفتر اليومية
        advance_date يمكن أن يكون نصاً بصيغة YYYY-MM-DD أو كائن date
        """
        try:
            # تحويل التاريخ إلى كائن date إذا كان نصاً
            try:
                adv_date = self._to_date(advance_date)
            except Exception as e:
                return {'success': False, 'error': f'تاريخ غير صالح: {e}'}

            # محاولة جلب user_id من الجلسة إذا لم يتم تمريره
            effective_user_id = user_id
            if effective_user_id is None:
                effective_user_id = self._get_current_user_id()
                if effective_user_id is None:
                    effective_user_id = 1  # مستخدم افتراضي في حال فشل الجلب
                    logger.warning("لم يتم العثور على مستخدم حالي، تم استخدام user_id=1")

            # جلب اسم الموظف (آمن لأنه خارج أي كتلة cursor)
            employee_name = self._get_employee_name(employee_id)

            # 1. إنشاء أو الحصول على daily_cash لهذا التاريخ
            daily_res = self.daily_mgr.create_or_update_daily_cash(adv_date, effective_user_id)
            if not daily_res['success']:
                return {'success': False, 'error': 'فشل في إنشاء سجل الصندوق اليومي'}

            daily_cash_id = daily_res['daily_cash_id']

            with db.get_cursor() as cursor:
                # 2. إضافة السلفة في جدول employee_advances
                cursor.execute("""
                    INSERT INTO employee_advances (employee_id, amount, advance_date, reason)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (employee_id, amount, adv_date, reason))
                advance_id = cursor.fetchone()['id']

                # 3. إضافة مصروف من نوع 'advances' في daily_expenses
                note = f"سلفة للموظف {employee_name}"
                if reason:
                    note += f" - {reason}"

                expense_res = self.daily_mgr.add_expense(
                    daily_cash_id=daily_cash_id,
                    category_name='advances',
                    amount=amount,
                    note=note,
                    user_id=effective_user_id
                )
                if not expense_res['success']:
                    # التراجع عن إضافة السلفة إذا فشل تسجيل المصروف
                    cursor.execute("DELETE FROM employee_advances WHERE id = %s", (advance_id,))
                    return {'success': False, 'error': expense_res.get('error')}

                return {'success': True, 'id': advance_id}
        except Exception as e:
            logger.error(f"خطأ في إضافة سلفة: {e}")
            return {'success': False, 'error': str(e)}

    def get_unpaid_advances(self, employee_id: int, up_to_date: date = None) -> List[Dict]:
        try:
            with db.get_cursor() as cursor:
                query = """
                    SELECT id, amount, advance_date, reason
                    FROM employee_advances
                    WHERE employee_id = %s AND repaid = FALSE
                """
                params = [employee_id]
                if up_to_date:
                    query += " AND advance_date <= %s"
                    params.append(up_to_date)
                query += " ORDER BY advance_date"
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"خطأ في جلب السلف غير المسددة: {e}")
            return []

    def get_total_unpaid_advances(self, employee_id: int, up_to_date: date = None) -> float:
        advances = self.get_unpaid_advances(employee_id, up_to_date)
        return sum(float(a['amount']) for a in advances)

    def mark_advances_as_repaid(self, employee_id: int, repaid_date: date, advance_ids: List[int] = None) -> bool:
        try:
            with db.get_cursor() as cursor:
                if advance_ids:
                    cursor.execute("""
                        UPDATE employee_advances SET repaid = TRUE, repaid_date = %s
                        WHERE employee_id = %s AND id = ANY(%s)
                    """, (repaid_date, employee_id, advance_ids))
                else:
                    cursor.execute("""
                        UPDATE employee_advances SET repaid = TRUE, repaid_date = %s
                        WHERE employee_id = %s AND repaid = FALSE
                    """, (repaid_date, employee_id))
                return True
        except Exception as e:
            logger.error(f"خطأ في تسديد السلف: {e}")
            return False

    # ------------------- صرف الراتب -------------------
    def calculate_net_salary(self, employee_id: int, payment_date: date) -> Dict:
        emp = self.get_employee(employee_id)
        if not emp:
            return {'success': False, 'error': 'الموظف غير موجود'}
        base = float(emp['base_salary'] or 0)
        advances_total = self.get_total_unpaid_advances(employee_id, payment_date)
        net = base - advances_total
        return {
            'success': True,
            'base_salary': base,
            'total_advances': advances_total,
            'net_salary': net
        }

    def pay_salary(self, employee_id: int, payment_date: Union[str, date], daily_cash_id: int,
                   created_by: int, notes: str = '') -> Dict:
        """
        صرف الراتب للموظف وتسجيله كمصروف في دفتر اليومية
        payment_date يمكن أن يكون نصاً أو كائن date
        """
        # تحويل التاريخ إلى كائن date إذا كان نصاً
        try:
            pay_date = self._to_date(payment_date)
        except Exception as e:
            return {'success': False, 'error': f'تاريخ غير صالح: {e}'}

        calc = self.calculate_net_salary(employee_id, pay_date)
        if not calc['success']:
            return calc

        # جلب اسم الموظف **قبل** الدخول إلى كتلة cursor
        employee_name = self._get_employee_name(employee_id)

        try:
            with db.get_cursor() as cursor:
                # 1. إدراج سجل في salary_payments
                cursor.execute("""
                    INSERT INTO salary_payments
                    (employee_id, payment_date, base_salary, total_advances, net_salary, daily_cash_id, notes, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (employee_id, pay_date, calc['base_salary'], calc['total_advances'],
                      calc['net_salary'], daily_cash_id, notes, created_by))
                payment_id = cursor.fetchone()['id']

                # 2. تسوية السلف (تحديث repaid = True)
                self.mark_advances_as_repaid(employee_id, pay_date)

                # 3. إضافة مصروف من نوع 'salaries' في daily_expenses
                expense_note = f"راتب الموظف {employee_name}"
                if notes:
                    expense_note += f" - {notes}"

                expense_res = self.daily_mgr.add_expense(
                    daily_cash_id=daily_cash_id,
                    category_name='salaries',
                    amount=calc['net_salary'],
                    note=expense_note,
                    user_id=created_by
                )
                if not expense_res['success']:
                    # تسجيل الخطأ فقط دون التراجع عن صرف الراتب
                    logger.error(f"فشل إضافة مصروف الراتب: {expense_res.get('error')}")

                return {'success': True, 'payment_id': payment_id, **calc}
        except Exception as e:
            logger.error(f"خطأ في صرف الراتب: {e}")
            return {'success': False, 'error': str(e)}

    # ------------------- السجل المالي الكامل (جديد) -------------------
    def get_employee_financial_history(self, employee_id: int) -> List[Dict]:
        """
        تجميع جميع السلف والرواتب المدفوعة للموظف وترتيبها زمنياً تنازلياً.
        تعيد قائمة تحتوي على قواميس لكل عملية (سلفة أو راتب).
        """
        history = []
        try:
            with db.get_cursor() as cursor:
                # 1. جلب السلف
                cursor.execute("""
                    SELECT 
                        'advance' AS type,
                        id,
                        amount,
                        advance_date AS transaction_date,
                        reason AS description,
                        repaid,
                        repaid_date
                    FROM employee_advances
                    WHERE employee_id = %s
                """, (employee_id,))
                advances = [dict(row) for row in cursor.fetchall()]

                # 2. جلب دفعات الرواتب
                cursor.execute("""
                    SELECT 
                        'salary' AS type,
                        id,
                        net_salary AS amount,
                        payment_date AS transaction_date,
                        notes AS description,
                        base_salary,
                        total_advances
                    FROM salary_payments
                    WHERE employee_id = %s
                """, (employee_id,))
                salaries = [dict(row) for row in cursor.fetchall()]

                # 3. دمج القائمتين وترتيبها تنازلياً حسب التاريخ
                history = advances + salaries
                history.sort(key=lambda x: x['transaction_date'], reverse=True)

            return history
        except Exception as e:
            logger.error(f"خطأ في جلب السجل المالي للموظف {employee_id}: {e}")
            return []