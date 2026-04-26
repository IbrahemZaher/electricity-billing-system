# modules/daily_cash.py

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional
from database.connection import db
from database.models import models

logger = logging.getLogger(__name__)

class DailyCashManager:

    def __init__(self):
        self._ensure_categories()

    def _ensure_categories(self):
        categories = [
            ('food', 'شراب وطعام'), ('salaries', 'رواتب'), ('advances', 'سلف'),
            ('office', 'مصاريف مكتب وإدارية'), ('repair', 'إصلاح'), ('expansion', 'توسعة'),
            ('energy', 'طاقة'), ('fuel', 'مازوت')
        ]
        with db.get_cursor() as cursor:
            for code, name in categories:
                cursor.execute("""
                    INSERT INTO expense_categories (name, arabic_name)
                    VALUES (%s, %s) ON CONFLICT (name) DO NOTHING
                """, (code, name))

    # ---------- دوال مساعدة ----------
    @staticmethod
    def _get_current_user_id() -> Optional[int]:
        """محاولة جلب معرف المستخدم الحالي من الجلسة"""
        try:
            from auth.session import Session
            session = Session()
            current_user = session.get_current_user()
            if current_user and 'id' in current_user:
                return current_user['id']
        except Exception as e:
            logger.warning(f"تعذر جلب معرف المستخدم الحالي: {e}")
        return None

    # ---------- دوال الجبايات والأرصدة ----------
    def get_collections_by_date(self, target_date: date, collector_id: int = None) -> Dict:
        with db.get_cursor() as cursor:
            params = [target_date]
            collector_filter = ""
            if collector_id:
                collector_filter = " AND i.user_id = %s"
                params.append(collector_id)

            cursor.execute(f"""
                SELECT
                    i.user_id as collector_id,
                    u.full_name as collector_name,
                    COUNT(i.id) as collection_count,
                    COALESCE(SUM(i.total_amount), 0) as total
                FROM invoices i
                LEFT JOIN users u ON i.user_id = u.id
                WHERE DATE(i.payment_date) = %s
                AND i.status = 'active'
                {collector_filter}
                GROUP BY i.user_id, u.full_name
            """, params)

            rows = cursor.fetchall()
            total = sum(float(r['total']) for r in rows)
            return {'total': total, 'details': [dict(row) for row in rows]}

    def get_initial_balance(self) -> float:
        with db.get_cursor() as cursor:
            cursor.execute("SELECT value FROM settings WHERE key = 'initial_cash_balance'")
            row = cursor.fetchone()
            if row and row['value']:
                try:
                    return float(row['value'])
                except:
                    return 0.0
            return 0.0

    def get_opening_balance(self, for_date: date) -> float:
        prev_date = for_date - timedelta(days=1)
        with db.get_cursor() as cursor:
            cursor.execute("SELECT closing_balance FROM daily_cash WHERE cash_date = %s", (prev_date,))
            row = cursor.fetchone()
            if row:
                return float(row['closing_balance'])
            return self.get_initial_balance()

    def create_or_update_daily_cash(self, cash_date: date, user_id: int) -> Dict:
        opening = self.get_opening_balance(cash_date)
        collections = self.get_collections_by_date(cash_date)
        total_collections = collections['total']
        closing = opening + total_collections

        with db.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO daily_cash (
                    cash_date, opening_balance, total_collections,
                    closing_balance, created_by, updated_by
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (cash_date) DO UPDATE SET
                    total_collections = EXCLUDED.total_collections,
                    opening_balance = EXCLUDED.opening_balance,
                    closing_balance = EXCLUDED.closing_balance,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (cash_date, opening, total_collections, closing, user_id, user_id))
            daily_id = cursor.fetchone()['id']

            cursor.execute("DELETE FROM daily_collections_detail WHERE daily_cash_id = %s", (daily_id,))
            for det in collections['details']:
                cursor.execute("""
                    INSERT INTO daily_collections_detail
                    (daily_cash_id, collector_id, collector_name, total_collected, invoice_count)
                    VALUES (%s, %s, %s, %s, %s)
                """, (daily_id, det['collector_id'], det['collector_name'], det['total'], det['collection_count']))

        models.recalculate_daily_cash(cash_date)

        with db.get_cursor() as cursor:
            cursor.execute("SELECT id, closing_balance FROM daily_cash WHERE cash_date = %s", (cash_date,))
            row = cursor.fetchone()
            return {'success': True, 'daily_cash_id': row['id'], 'closing_balance': float(row['closing_balance'])}

    # ---------- إضافة المصاريف (تم تعديلها) ----------
    def add_expense(self, daily_cash_id: int, category_name: str, amount: float,
                    note: str = '', user_id: int = None) -> Dict:
        """
        إضافة مصروف مع ضمان وجود user_id (يُستمد من الجلسة إذا كان None)
        """
        effective_user_id = user_id
        if effective_user_id is None:
            effective_user_id = self._get_current_user_id()
            if effective_user_id is None:
                effective_user_id = 1  # احتياطي

        with db.get_cursor() as cursor:
            cursor.execute("SELECT id FROM expense_categories WHERE name = %s", (category_name,))
            cat = cursor.fetchone()
            if not cat:
                return {'success': False, 'error': f'التصنيف {category_name} غير موجود'}

            cursor.execute("SELECT cash_date FROM daily_cash WHERE id = %s", (daily_cash_id,))
            row = cursor.fetchone()
            if not row:
                return {'success': False, 'error': 'سجل الصندوق غير موجود'}
            cash_date = row['cash_date']

            cursor.execute("""
                INSERT INTO daily_expenses (daily_cash_id, category_id, amount, note, user_id)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (daily_cash_id, cat['id'], amount, note, effective_user_id))
            expense_id = cursor.fetchone()['id']

        models.recalculate_daily_cash(cash_date)
        return {'success': True, 'expense_id': expense_id}

    # ---------- توزيع الأرباح ----------
    def add_profit_distribution(self, daily_cash_id: int, owner_id: int, amount: float,
                                profit_type: str = 'manager', note: str = '', user_id: int = None) -> Dict:
        effective_user_id = user_id or self._get_current_user_id() or 1
        with db.get_cursor() as cursor:
            cursor.execute("SELECT id FROM company_owners WHERE id = %s AND is_active = TRUE", (owner_id,))
            if not cursor.fetchone():
                return {'success': False, 'error': 'المدير غير موجود أو غير نشط'}

            cursor.execute("SELECT cash_date FROM daily_cash WHERE id = %s", (daily_cash_id,))
            row = cursor.fetchone()
            if not row:
                return {'success': False, 'error': 'سجل الصندوق غير موجود'}
            cash_date = row['cash_date']

            cursor.execute("""
                INSERT INTO profit_distribution (daily_cash_id, owner_id, amount, profit_type, note, user_id)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """, (daily_cash_id, owner_id, amount, profit_type, note, effective_user_id))
            profit_id = cursor.fetchone()['id']

        models.recalculate_daily_cash(cash_date)
        return {'success': True, 'profit_id': profit_id}

    def add_energy_profit_distribution(self, daily_cash_id: int, meter_id: int, amount: float,
                                    note: str = '', user_id: int = None) -> Dict:
        effective_user_id = user_id or self._get_current_user_id() or 1
        with db.get_cursor() as cursor:
            cursor.execute("SELECT id, name FROM energy_meters WHERE id = %s AND is_active = TRUE", (meter_id,))
            meter = cursor.fetchone()
            if not meter:
                return {'success': False, 'error': 'عداد الطاقة غير موجود أو غير نشط'}

            cursor.execute("SELECT cash_date FROM daily_cash WHERE id = %s", (daily_cash_id,))
            row = cursor.fetchone()
            if not row:
                return {'success': False, 'error': 'سجل الصندوق غير موجود'}
            cash_date = row['cash_date']

            # 1. إدراج توزيع أرباح الطاقة (لأغراض الصندوق اليومي)
            cursor.execute("""
                INSERT INTO energy_profit_distribution (daily_cash_id, meter_id, amount, note, user_id)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (daily_cash_id, meter_id, amount, note, effective_user_id))
            profit_id = cursor.fetchone()['id']

        # 2. تسجيل حركة سحب من حساب الطاقة (باستخدام FuelManagement)
        from modules.fuel_management import FuelManagement
        res = FuelManagement.record_payment_for_meter(
            meter_id=meter_id,
            amount=amount,
            profit_id=profit_id,
            user_id=effective_user_id,
            note=note or f"توزيع أرباح طاقة عبر دفتر اليومية - {cash_date}"
        )
        if not res['success']:
            # إذا فشل تسجيل السحب، نحذف سجل التوزيع الذي أضفناه
            with db.get_cursor() as cursor:
                cursor.execute("DELETE FROM energy_profit_distribution WHERE id = %s", (profit_id,))
            return {'success': False, 'error': res['error']}

        # 3. إعادة حساب الصندوق اليومي (بعد تغيير الرصيد)
        models.recalculate_daily_cash(cash_date)
        return {'success': True, 'profit_id': profit_id, 'meter_name': meter['name']}

    # ---------- ملخص المحاسبين ----------
    def get_accountants_summary(self, cash_date: date) -> List[Dict]:
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, full_name, username, role
                FROM users
                WHERE is_active = TRUE
                ORDER BY full_name
            """)
            users = {row['id']: dict(row) for row in cursor.fetchall()}

            cursor.execute("""
                SELECT 
                    i.user_id,
                    COUNT(i.id) as invoice_count,
                    COALESCE(SUM(i.total_amount), 0) as total_collected
                FROM invoices i
                WHERE DATE(i.payment_date) = %s
                AND i.status = 'active'
                GROUP BY i.user_id
            """, (cash_date,))
            collections = {row['user_id']: (row['invoice_count'], float(row['total_collected'])) for row in cursor.fetchall()}

            cursor.execute("""
                SELECT 
                    de.user_id,
                    COALESCE(SUM(de.amount), 0) as total_expenses
                FROM daily_expenses de
                JOIN daily_cash dc ON de.daily_cash_id = dc.id
                WHERE dc.cash_date = %s
                GROUP BY de.user_id
            """, (cash_date,))
            expenses = {row['user_id']: float(row['total_expenses']) for row in cursor.fetchall()}

            cursor.execute("""
                SELECT 
                    pd.user_id,
                    COALESCE(SUM(pd.amount), 0) as total_manager_profit
                FROM profit_distribution pd
                JOIN daily_cash dc ON pd.daily_cash_id = dc.id
                WHERE dc.cash_date = %s
                GROUP BY pd.user_id
            """, (cash_date,))
            manager_profits = {row['user_id']: float(row['total_manager_profit']) for row in cursor.fetchall()}

            cursor.execute("""
                SELECT 
                    epd.user_id,
                    COALESCE(SUM(epd.amount), 0) as total_energy_profit
                FROM energy_profit_distribution epd
                JOIN daily_cash dc ON epd.daily_cash_id = dc.id
                WHERE dc.cash_date = %s
                GROUP BY epd.user_id
            """, (cash_date,))
            energy_profits = {row['user_id']: float(row['total_energy_profit']) for row in cursor.fetchall()}

            result = []
            for user_id, user_info in users.items():
                inv_count, collected = collections.get(user_id, (0, 0.0))
                spent = expenses.get(user_id, 0.0)
                manager_profit = manager_profits.get(user_id, 0.0)
                energy_profit = energy_profits.get(user_id, 0.0)
                net = collected - spent - manager_profit - energy_profit
                result.append({
                    'user_id': user_id,
                    'full_name': user_info['full_name'],
                    'username': user_info['username'],
                    'role': user_info['role'],
                    'invoice_count': inv_count,
                    'total_collected': collected,
                    'total_expenses': spent,
                    'manager_profit': manager_profit,
                    'energy_profit': energy_profit,
                    'net': net
                })
            result.sort(key=lambda x: x['full_name'])
            return result

    # ---------- تفاصيل المحاسب (تم تعديل get_expenses_by_accountant) ----------
    def get_invoices_by_accountant(self, cash_date: date, user_id: int) -> List[Dict]:
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    i.id,
                    i.invoice_number,
                    i.payment_date,
                    i.payment_time,
                    c.name as customer_name,
                    i.kilowatt_amount,
                    i.free_kilowatt,
                    i.discount,
                    i.total_amount,
                    i.receipt_number,
                    i.book_number
                FROM invoices i
                LEFT JOIN customers c ON i.customer_id = c.id
                WHERE DATE(i.payment_date) = %s
                AND i.user_id = %s
                AND i.status = 'active'
                ORDER BY i.payment_time
            """, (cash_date, user_id))
            return [dict(row) for row in cursor.fetchall()]

    def get_expenses_by_accountant(self, cash_date: date, user_id: int) -> List[Dict]:
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    de.id,
                    ec.arabic_name as category,
                    de.amount,
                    de.note,
                    de.created_at
                FROM daily_expenses de
                JOIN daily_cash dc ON de.daily_cash_id = dc.id
                JOIN expense_categories ec ON de.category_id = ec.id
                WHERE dc.cash_date = %s
                ORDER BY de.created_at
            """, (cash_date,))
            return [dict(row) for row in cursor.fetchall()]

    def get_manager_profits_by_accountant(self, cash_date: date, user_id: int) -> List[Dict]:
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    pd.id,
                    co.name as owner_name,
                    pd.amount,
                    pd.note,
                    pd.profit_type,
                    NULL as created_at
                FROM profit_distribution pd
                JOIN daily_cash dc ON pd.daily_cash_id = dc.id
                JOIN company_owners co ON pd.owner_id = co.id
                WHERE dc.cash_date = %s
                AND (pd.user_id = %s OR pd.user_id IS NULL)
                ORDER BY pd.id
            """, (cash_date, user_id))
            return [dict(row) for row in cursor.fetchall()]

    def get_energy_profits_by_accountant(self, cash_date: date, user_id: int) -> List[Dict]:
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    ep.id,
                    em.name as meter_name,
                    ep.amount,
                    ep.note,
                    NULL as created_at
                FROM energy_profit_distribution ep
                JOIN daily_cash dc ON ep.daily_cash_id = dc.id
                JOIN energy_meters em ON ep.meter_id = em.id
                WHERE dc.cash_date = %s
                AND (ep.user_id = %s OR ep.user_id IS NULL)
                ORDER BY ep.id
            """, (cash_date, user_id))
            return [dict(row) for row in cursor.fetchall()]

    # ---------- تعديل وحذف ----------
    def update_expense(self, expense_id: int, amount: float, note: str, user_id: int) -> Dict:
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT de.daily_cash_id, dc.cash_date
                FROM daily_expenses de
                JOIN daily_cash dc ON de.daily_cash_id = dc.id
                WHERE de.id = %s
            """, (expense_id,))
            row = cursor.fetchone()
            if not row:
                return {'success': False, 'error': 'المصروف غير موجود'}
            
            cash_date = row['cash_date']
            cursor.execute("""
                UPDATE daily_expenses
                SET amount = %s, note = %s, user_id = %s
                WHERE id = %s
            """, (amount, note, user_id, expense_id))
        
        models.recalculate_daily_cash(cash_date)
        return {'success': True}

    def delete_expense(self, expense_id: int, user_id: int) -> Dict:
        with db.get_cursor() as cursor:
            cursor.execute("SELECT daily_cash_id FROM daily_expenses WHERE id = %s", (expense_id,))
            row = cursor.fetchone()
            if not row:
                return {'success': False, 'error': 'المصروف غير موجود'}
            daily_cash_id = row['daily_cash_id']

            cursor.execute("SELECT cash_date FROM daily_cash WHERE id = %s", (daily_cash_id,))
            date_row = cursor.fetchone()
            if not date_row:
                return {'success': False, 'error': 'سجل الصندوق غير موجود'}
            cash_date = date_row['cash_date']

            cursor.execute("DELETE FROM daily_expenses WHERE id = %s", (expense_id,))

        models.recalculate_daily_cash(cash_date)
        return {'success': True}

    def update_profit(self, profit_id: int, amount: float, note: str, user_id: int) -> Dict:
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT pd.daily_cash_id, dc.cash_date
                FROM profit_distribution pd
                JOIN daily_cash dc ON pd.daily_cash_id = dc.id
                WHERE pd.id = %s
            """, (profit_id,))
            row = cursor.fetchone()
            if not row:
                return {'success': False, 'error': 'السجل غير موجود'}
            cash_date = row['cash_date']
            cursor.execute("""
                UPDATE profit_distribution
                SET amount = %s, note = %s, user_id = %s
                WHERE id = %s
            """, (amount, note, user_id, profit_id))
        models.recalculate_daily_cash(cash_date)
        return {'success': True}

    def update_energy_profit(self, profit_id: int, amount: float, note: str, user_id: int) -> Dict:
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT ep.daily_cash_id, ep.meter_id, ep.amount as old_amount, dc.cash_date
                FROM energy_profit_distribution ep
                JOIN daily_cash dc ON ep.daily_cash_id = dc.id
                WHERE ep.id = %s
            """, (profit_id,))
            row = cursor.fetchone()
            if not row:
                return {'success': False, 'error': 'السجل غير موجود'}
            cash_date = row['cash_date']
            meter_id = row['meter_id']
            old_amount = float(row['old_amount'])

            # تحديث سجل التوزيع
            cursor.execute("""
                UPDATE energy_profit_distribution
                SET amount = %s, note = %s, user_id = %s
                WHERE id = %s
            """, (amount, note, user_id, profit_id))

        # تحديث حركة السحب في حساب الطاقة
        # نبحث عن حركة السحب المرتبطة بهذا profit_id
        from modules.fuel_management import FuelManagement
        with db.get_cursor() as cursor:
            cursor.execute("SELECT id FROM energy_account_transactions WHERE profit_id = %s", (profit_id,))
            trans = cursor.fetchone()
            if trans:
                # إذا كانت موجودة، نحذفها ونسجل حركة جديدة بالمبلغ المحدث
                cursor.execute("DELETE FROM energy_account_transactions WHERE id = %s", (trans['id'],))
            # نسجل حركة جديدة
            FuelManagement.record_payment_for_meter(
                meter_id=meter_id,
                amount=amount,
                profit_id=profit_id,
                user_id=user_id,
                note=note or f"توزيع أرباح طاقة (معدل) - {cash_date}"
            )

        models.recalculate_daily_cash(cash_date)
        return {'success': True}

    def delete_profit(self, profit_id: int, user_id: int) -> Dict:
        with db.get_cursor() as cursor:
            cursor.execute("SELECT daily_cash_id FROM profit_distribution WHERE id = %s", (profit_id,))
            row = cursor.fetchone()
            if not row:
                return {'success': False, 'error': 'التوزيع غير موجود'}
            daily_cash_id = row['daily_cash_id']

            cursor.execute("SELECT cash_date FROM daily_cash WHERE id = %s", (daily_cash_id,))
            date_row = cursor.fetchone()
            if not date_row:
                return {'success': False, 'error': 'سجل الصندوق غير موجود'}
            cash_date = date_row['cash_date']

            cursor.execute("DELETE FROM profit_distribution WHERE id = %s", (profit_id,))

        models.recalculate_daily_cash(cash_date)
        return {'success': True}

    def delete_energy_profit(self, profit_id: int, user_id: int) -> Dict:
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT daily_cash_id, meter_id FROM energy_profit_distribution WHERE id = %s
            """, (profit_id,))
            row = cursor.fetchone()
            if not row:
                return {'success': False, 'error': 'توزيع أرباح الطاقة غير موجود'}
            daily_cash_id = row['daily_cash_id']
            meter_id = row['meter_id']

            cursor.execute("SELECT cash_date FROM daily_cash WHERE id = %s", (daily_cash_id,))
            date_row = cursor.fetchone()
            if not date_row:
                return {'success': False, 'error': 'سجل الصندوق غير موجود'}
            cash_date = date_row['cash_date']

            # حذف حركة السحب المرتبطة من حساب الطاقة
            cursor.execute("DELETE FROM energy_account_transactions WHERE profit_id = %s", (profit_id,))
            # حذف سجل التوزيع
            cursor.execute("DELETE FROM energy_profit_distribution WHERE id = %s", (profit_id,))

        # إعادة حساب الرصيد للعداد المحدد (لتصحيح الرصيد بعد الحذف)
        from modules.fuel_management import FuelManagement
        FuelManagement.recalculate_meter_balance(meter_id)

        models.recalculate_daily_cash(cash_date)
        return {'success': True}

    def get_daily_cash_report(self, cash_date: date) -> Dict:
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT dc.*, u1.full_name as created_by_name, u2.full_name as updated_by_name
                FROM daily_cash dc
                LEFT JOIN users u1 ON dc.created_by = u1.id
                LEFT JOIN users u2 ON dc.updated_by = u2.id
                WHERE dc.cash_date = %s
            """, (cash_date,))
            daily = cursor.fetchone()
            if not daily:
                return {'success': False, 'error': 'لا توجد بيانات لهذا اليوم'}

            cursor.execute("""
                SELECT collector_name, total_collected, invoice_count
                FROM daily_collections_detail WHERE daily_cash_id = %s
            """, (daily['id'],))
            collections = cursor.fetchall()

            cursor.execute("""
                SELECT ec.arabic_name as category, de.id, de.amount, de.note
                FROM daily_expenses de
                JOIN expense_categories ec ON de.category_id = ec.id
                WHERE de.daily_cash_id = %s
            """, (daily['id'],))
            expenses = cursor.fetchall()

            cursor.execute("""
                SELECT p.id, co.name as owner_name, p.amount, p.note, p.profit_type
                FROM profit_distribution p
                JOIN company_owners co ON p.owner_id = co.id
                WHERE p.daily_cash_id = %s
            """, (daily['id'],))
            profits = cursor.fetchall()

            cursor.execute("""
                SELECT ep.id, em.name as owner_name, ep.amount, ep.note
                FROM energy_profit_distribution ep
                JOIN energy_meters em ON ep.meter_id = em.id
                WHERE ep.daily_cash_id = %s
            """, (daily['id'],))
            energy_profits = cursor.fetchall()

            return {
                'success': True,
                'daily': dict(daily),
                'collections': [dict(c) for c in collections],
                'expenses': [dict(e) for e in expenses],
                'profits': [dict(p) for p in profits],
                'energy_profits': [dict(ep) for ep in energy_profits]
            }

    # ---------- الجرد الأسبوعي ----------
    def generate_weekly_inventory(self, start_date: date, end_date: date, user_id: int) -> Dict:
        with db.get_cursor() as cursor:
            cursor.execute("SELECT opening_balance FROM daily_cash WHERE cash_date = %s", (start_date,))
            first_day = cursor.fetchone()
            total_opening = float(first_day['opening_balance']) if first_day else 0.0

            cursor.execute("SELECT closing_balance FROM daily_cash WHERE cash_date = %s", (end_date,))
            last_day = cursor.fetchone()
            total_closing = float(last_day['closing_balance']) if last_day else 0.0

            cursor.execute("""
                SELECT
                    COALESCE(SUM(total_collections), 0) as total_collections,
                    COALESCE(SUM(total_profits), 0) as total_profits,
                    COALESCE(SUM(total_energy_profits), 0) as total_energy_profits
                FROM daily_cash
                WHERE cash_date BETWEEN %s AND %s
            """, (start_date, end_date))
            totals = cursor.fetchone()

            cursor.execute("""
                SELECT COALESCE(SUM(de.amount), 0) AS val
                FROM daily_expenses de
                JOIN daily_cash dc ON de.daily_cash_id = dc.id
                JOIN expense_categories ec ON de.category_id = ec.id
                WHERE dc.cash_date BETWEEN %s AND %s
                AND ec.name NOT IN ('repair', 'expansion', 'fuel')
            """, (start_date, end_date))
            row = cursor.fetchone()
            total_expenses_general = float(row['val']) if row else 0.0

            cursor.execute("""
                SELECT COALESCE(SUM(de.amount), 0) AS val
                FROM daily_expenses de
                JOIN daily_cash dc ON de.daily_cash_id = dc.id
                JOIN expense_categories ec ON de.category_id = ec.id
                WHERE dc.cash_date BETWEEN %s AND %s
                AND ec.name IN ('repair', 'expansion')
            """, (start_date, end_date))
            row = cursor.fetchone()
            total_repair_expansion = float(row['val']) if row else 0.0

            cursor.execute("""
                SELECT COALESCE(SUM(de.amount), 0) AS val
                FROM daily_expenses de
                JOIN daily_cash dc ON de.daily_cash_id = dc.id
                JOIN expense_categories ec ON de.category_id = ec.id
                WHERE dc.cash_date BETWEEN %s AND %s
                AND ec.name = 'fuel'
            """, (start_date, end_date))
            row = cursor.fetchone()
            total_fuel = float(row['val']) if row else 0.0

            cursor.execute("""
                INSERT INTO weekly_cash_inventory (
                    week_start, week_end,
                    total_opening, total_collections, total_expenses,
                    total_repair_expansion, total_energy_profits, total_fuel,
                    total_profits, total_closing, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (week_start) DO UPDATE SET
                    week_end = EXCLUDED.week_end,
                    total_opening = EXCLUDED.total_opening,
                    total_collections = EXCLUDED.total_collections,
                    total_expenses = EXCLUDED.total_expenses,
                    total_repair_expansion = EXCLUDED.total_repair_expansion,
                    total_energy_profits = EXCLUDED.total_energy_profits,
                    total_fuel = EXCLUDED.total_fuel,
                    total_profits = EXCLUDED.total_profits,
                    total_closing = EXCLUDED.total_closing,
                    notes = EXCLUDED.notes
                RETURNING id
            """, (
                start_date, end_date,
                total_opening,
                totals['total_collections'],
                total_expenses_general,
                total_repair_expansion,
                totals['total_energy_profits'],
                total_fuel,
                totals['total_profits'],
                total_closing,
                f"جرد تلقائي من {start_date} إلى {end_date}"
            ))
            inv_id = cursor.fetchone()['id']
            return {'success': True, 'inventory_id': inv_id}

    def get_weekly_inventories(self) -> List[Dict]:
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'weekly_cash_inventory'
            """)
            existing_cols = {row['column_name'] for row in cursor.fetchall()}
            
            select_fields = [
                "id", "week_start", "week_end",
                "total_opening", "total_collections", "total_expenses",
                "total_profits", "total_closing", "notes", "created_at"
            ]
            for col in ['total_repair_expansion', 'total_energy_profits', 'total_fuel']:
                if col in existing_cols:
                    select_fields.append(col)
                else:
                    select_fields.append(f"0 as {col}")
            
            query = f"""
                SELECT {', '.join(select_fields)}
                FROM weekly_cash_inventory 
                ORDER BY week_start DESC
            """
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def delete_weekly_inventory(self, inv_id: int) -> Dict:
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM weekly_cash_inventory WHERE id = %s", (inv_id,))
            return {'success': True}