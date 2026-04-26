# modules/fuel_management.py
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from database.connection import db

logger = logging.getLogger(__name__)

class FuelManagement:
    """إدارة عدادات المولدة والقطاعات والخزانات والطاقة والقراءات اليومية والجرد الأسبوعي"""

    # ==================== عدادات المولدة ====================
    @staticmethod
    def get_generator_meters(active_only=True) -> List[Dict]:
        with db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM generator_meters WHERE is_active = %s ORDER BY name",
                (active_only,)
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def add_generator_meter(data: Dict) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO generator_meters (name, code, notes) VALUES (%s, %s, %s) RETURNING id",
                    (data['name'], data.get('code'), data.get('notes'))
                )
                return {'success': True, 'id': cursor.fetchone()['id']}
        except Exception as e:
            logger.error(f"خطأ في إضافة عداد مولدة: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def update_generator_meter(meter_id: int, data: Dict) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE generator_meters SET name=%s, code=%s, notes=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
                    (data['name'], data.get('code'), data.get('notes'), meter_id)
                )
                return {'success': True}
        except Exception as e:
            logger.error(f"خطأ في تحديث عداد مولدة: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def delete_generator_meter(meter_id: int) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("DELETE FROM generator_meters WHERE id = %s", (meter_id,))
                return {'success': True}
        except Exception as e:
            logger.error(f"خطأ في حذف عداد مولدة: {e}")
            return {'success': False, 'error': str(e)}

    # ==================== عدادات القطاعات ====================
    @staticmethod
    def get_sector_meters(active_only=True, sector_id=None) -> List[Dict]:
        with db.get_cursor() as cursor:
            sql = "SELECT sm.*, s.name as sector_name FROM sector_meters sm LEFT JOIN sectors s ON sm.sector_id = s.id WHERE sm.is_active = %s"
            params = [active_only]
            if sector_id is not None:
                sql += " AND sm.sector_id = %s"
                params.append(sector_id)
            sql += " ORDER BY sm.name"
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def add_sector_meter(data: Dict) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO sector_meters (name, code, sector_id, notes) VALUES (%s, %s, %s, %s) RETURNING id",
                    (data['name'], data.get('code'), data.get('sector_id'), data.get('notes'))
                )
                return {'success': True, 'id': cursor.fetchone()['id']}
        except Exception as e:
            logger.error(f"خطأ في إضافة عداد قطاع: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def update_sector_meter(meter_id: int, data: Dict) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE sector_meters SET name=%s, code=%s, sector_id=%s, notes=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
                    (data['name'], data.get('code'), data.get('sector_id'), data.get('notes'), meter_id)
                )
                return {'success': True}
        except Exception as e:
            logger.error(f"خطأ في تحديث عداد قطاع: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def delete_sector_meter(meter_id: int) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("DELETE FROM sector_meters WHERE id = %s", (meter_id,))
                return {'success': True}
        except Exception as e:
            logger.error(f"خطأ في حذف عداد قطاع: {e}")
            return {'success': False, 'error': str(e)}

    # ==================== خزانات المازوت ====================
    @staticmethod
    def get_tanks(active_only=True) -> List[Dict]:
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM fuel_tanks WHERE is_active = %s ORDER BY name", (active_only,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def add_tank(data: Dict) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO fuel_tanks (name, liters_per_cm, notes) VALUES (%s, %s, %s) RETURNING id",
                    (data['name'], data.get('liters_per_cm', 10.75), data.get('notes'))
                )
                return {'success': True, 'id': cursor.fetchone()['id']}
        except Exception as e:
            logger.error(f"خطأ في إضافة خزان: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def update_tank(tank_id: int, data: Dict) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE fuel_tanks SET name=%s, liters_per_cm=%s, notes=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
                    (data['name'], data['liters_per_cm'], data.get('notes'), tank_id)
                )
                return {'success': True}
        except Exception as e:
            logger.error(f"خطأ في تحديث خزان: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def delete_tank(tank_id: int) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("DELETE FROM fuel_tanks WHERE id = %s", (tank_id,))
                return {'success': True}
        except Exception as e:
            logger.error(f"خطأ في حذف خزان: {e}")
            return {'success': False, 'error': str(e)}

    # ==================== عدادات الطاقة ====================
    @staticmethod
    def get_energy_meters(active_only=True) -> List[Dict]:
        with db.get_cursor() as cursor:
            if active_only:
                cursor.execute("SELECT * FROM energy_meters WHERE is_active = TRUE ORDER BY name")
            else:
                cursor.execute("SELECT * FROM energy_meters ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def add_energy_meter(data: Dict) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO energy_meters (name, code, notes, conversion_rate, current_balance)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id
                """, (
                    data['name'],
                    data.get('code'),
                    data.get('notes'),
                    data.get('conversion_rate', 0),
                    data.get('current_balance', 0)
                ))
                return {'success': True, 'id': cursor.fetchone()['id']}
        except Exception as e:
            logger.error(f"خطأ في إضافة عداد طاقة: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def update_energy_meter(meter_id: int, data: Dict) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE energy_meters 
                    SET name=%s, code=%s, notes=%s, conversion_rate=%s, current_balance=%s, updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s
                """, (
                    data['name'],
                    data.get('code'),
                    data.get('notes'),
                    data.get('conversion_rate', 0),
                    data.get('current_balance', 0),
                    meter_id
                ))
                return {'success': True}
        except Exception as e:
            logger.error(f"خطأ في تحديث عداد طاقة: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def delete_energy_meter(meter_id: int) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("DELETE FROM energy_meters WHERE id = %s", (meter_id,))
                return {'success': True}
        except Exception as e:
            logger.error(f"خطأ في حذف عداد طاقة: {e}")
            return {'success': False, 'error': str(e)}

    # ==================== قراءات الطاقة ====================
    @staticmethod
    def save_energy_reading(reading_date: date, meter_id: int, reading_value: float, notes: str = "") -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO energy_daily_readings (reading_date, meter_id, reading_value, notes)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (reading_date, meter_id) DO UPDATE SET
                        reading_value = EXCLUDED.reading_value,
                        notes = EXCLUDED.notes,
                        updated_at = CURRENT_TIMESTAMP
                """, (reading_date, meter_id, reading_value, notes))
            FuelManagement.process_energy_production(meter_id, reading_date)
            return {'success': True}
        except Exception as e:
            logger.error(f"خطأ في حفظ قراءة الطاقة: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def delete_energy_reading(reading_date: date, meter_id: int) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM energy_daily_readings
                    WHERE reading_date = %s AND meter_id = %s
                """, (reading_date, meter_id))
                reading = cursor.fetchone()
                if not reading:
                    return {'success': False, 'error': 'القراءة غير موجودة'}
                reading_id = reading['id']
                cursor.execute("DELETE FROM energy_account_transactions WHERE reading_id = %s", (reading_id,))
                cursor.execute("DELETE FROM energy_daily_readings WHERE id = %s", (reading_id,))
                FuelManagement.recalculate_meter_balance(meter_id)
                return {'success': True}
        except Exception as e:
            logger.error(f"خطأ في حذف قراءة الطاقة: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_energy_readings_for_date(reading_date: date) -> Dict[int, float]:
        with db.get_cursor() as cursor:
            cursor.execute(
                "SELECT meter_id, reading_value FROM energy_daily_readings WHERE reading_date = %s",
                (reading_date,)
            )
            return {row['meter_id']: float(row['reading_value']) for row in cursor.fetchall()}

    @staticmethod
    def get_energy_readings_range(start_date: date, end_date: date) -> List[Dict]:
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT er.reading_date, er.meter_id, er.reading_value, em.name as meter_name
                FROM energy_daily_readings er
                JOIN energy_meters em ON er.meter_id = em.id
                WHERE er.reading_date BETWEEN %s AND %s
                ORDER BY er.reading_date, em.name
            """, (start_date, end_date))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_last_energy_readings(limit=10) -> List[Dict]:
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT er.reading_date, er.meter_id, er.reading_value, em.name as meter_name
                FROM energy_daily_readings er
                JOIN energy_meters em ON er.meter_id = em.id
                ORDER BY er.reading_date DESC, em.name
                LIMIT %s
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def calculate_energy_output(start_date: date, end_date: date) -> float:
        meters = FuelManagement.get_energy_meters()
        if not meters:
            return 0.0
        total_output = 0.0
        for meter in meters:
            mid = meter['id']
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT reading_value FROM energy_daily_readings
                    WHERE meter_id = %s AND reading_date <= %s
                    ORDER BY reading_date DESC LIMIT 1
                """, (mid, start_date))
                start_row = cursor.fetchone()
                start_val = float(start_row['reading_value']) if start_row else 0.0
                cursor.execute("""
                    SELECT reading_value FROM energy_daily_readings
                    WHERE meter_id = %s AND reading_date <= %s
                    ORDER BY reading_date DESC LIMIT 1
                """, (mid, end_date))
                end_row = cursor.fetchone()
                end_val = float(end_row['reading_value']) if end_row else 0.0
                output = max(end_val - start_val, 0.0)
                total_output += output
        return total_output

    # ==================== عمليات شراء وتنزيل المازوت (معدلة) ====================
    @staticmethod
    def add_purchase(data: Dict, user_id: int = None) -> Dict:
        try:
            # تحويل purchase_date إلى كائن date إذا كان نصاً
            purchase_date_raw = data.get('purchase_date', date.today())
            if isinstance(purchase_date_raw, str):
                purchase_date = datetime.strptime(purchase_date_raw, '%Y-%m-%d').date()
            else:
                purchase_date = purchase_date_raw

            total_cost = float(data['quantity_liters']) * float(data['price_per_liter'])

            with db.get_cursor() as cursor:
                # 1. إدراج عملية الشراء
                cursor.execute(
                    "INSERT INTO fuel_purchases (purchase_date, quantity_liters, price_per_liter, notes) VALUES (%s, %s, %s, %s) RETURNING id",
                    (purchase_date, data['quantity_liters'], data['price_per_liter'], data.get('notes'))
                )
                purchase_id = cursor.fetchone()['id']

                # 2. البحث عن سجل الصندوق اليومي أو إنشاؤه
                cursor.execute("SELECT id FROM daily_cash WHERE cash_date = %s", (purchase_date,))
                row = cursor.fetchone()
                if not row:
                    from modules.daily_cash import DailyCashManager
                    DailyCashManager().create_or_update_daily_cash(purchase_date, user_id or 1)
                    cursor.execute("SELECT id FROM daily_cash WHERE cash_date = %s", (purchase_date,))
                    row = cursor.fetchone()
                daily_cash_id = row['id']

                # 3. تصنيف "مازوت"
                cursor.execute("SELECT id FROM expense_categories WHERE name = 'fuel'")
                cat = cursor.fetchone()
                if not cat:
                    cursor.execute("INSERT INTO expense_categories (name, arabic_name) VALUES ('fuel', 'مازوت') RETURNING id")
                    category_id = cursor.fetchone()['id']
                else:
                    category_id = cat['id']

                # 4. إدراج المصروف
                cursor.execute("""
                    INSERT INTO daily_expenses (daily_cash_id, category_id, amount, note, user_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (daily_cash_id, category_id, total_cost,
                      f"شراء مازوت: {data['quantity_liters']} لتر بسعر {data['price_per_liter']} ل.س",
                      user_id))

            # 5. إعادة حساب الصندوق
            from database.models import models
            models.recalculate_daily_cash(purchase_date)

            return {'success': True, 'id': purchase_id}
        except Exception as e:
            logger.error(f"خطأ في إضافة عملية شراء: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def update_purchase(purchase_id: int, data: Dict, user_id: int = None) -> Dict:
        try:
            # تحويل التواريخ
            new_date_raw = data.get('purchase_date')
            if isinstance(new_date_raw, str):
                new_date = datetime.strptime(new_date_raw, '%Y-%m-%d').date()
            else:
                new_date = new_date_raw

            with db.get_cursor() as cursor:
                cursor.execute("SELECT purchase_date, quantity_liters, price_per_liter FROM fuel_purchases WHERE id = %s", (purchase_id,))
                old = cursor.fetchone()
                if not old:
                    return {'success': False, 'error': 'عملية الشراء غير موجودة'}

                old_date = old['purchase_date']
                new_total = float(data['quantity_liters']) * float(data['price_per_liter'])

                # تحديث جدول الشراء
                cursor.execute("""
                    UPDATE fuel_purchases
                    SET purchase_date=%s, quantity_liters=%s, price_per_liter=%s, notes=%s
                    WHERE id=%s
                """, (new_date, data['quantity_liters'], data['price_per_liter'], data.get('notes'), purchase_id))

                # تحديث المصروف في daily_expenses
                cursor.execute("SELECT id FROM daily_cash WHERE cash_date = %s", (new_date,))
                daily = cursor.fetchone()
                if daily:
                    cursor.execute("""
                        UPDATE daily_expenses
                        SET amount=%s, note=%s
                        WHERE daily_cash_id=%s AND category_id=(SELECT id FROM expense_categories WHERE name='fuel')
                    """, (new_total, f"شراء مازوت: {data['quantity_liters']} لتر بسعر {data['price_per_liter']} ل.س", daily['id']))

            from database.models import models
            models.recalculate_daily_cash(new_date)
            if old_date != new_date:
                models.recalculate_daily_cash(old_date)

            return {'success': True}
        except Exception as e:
            logger.error(f"خطأ في تحديث شراء: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def delete_purchase(purchase_id: int) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT purchase_date FROM fuel_purchases WHERE id = %s", (purchase_id,))
                row = cursor.fetchone()
                if not row:
                    return {'success': False, 'error': 'عملية الشراء غير موجودة'}
                purchase_date = row['purchase_date']

                cursor.execute("""
                    DELETE FROM daily_expenses
                    WHERE daily_cash_id=(SELECT id FROM daily_cash WHERE cash_date=%s)
                    AND category_id=(SELECT id FROM expense_categories WHERE name='fuel')
                """, (purchase_date,))

                cursor.execute("DELETE FROM fuel_purchases WHERE id=%s", (purchase_id,))

            from database.models import models
            models.recalculate_daily_cash(purchase_date)
            return {'success': True}
        except Exception as e:
            logger.error(f"خطأ في حذف شراء: {e}")
            return {'success': False, 'error': str(e)}

    # ... (باقي الدوال كما في الملف الذي أرفقته، بدون تغيير) ...
    # لتجنب التكرار، سأكتفي بالإشارة إلى أن باقي الدوال مثل add_transfer, get_warehouse_stock,
    # daily readings, inventory, energy accounts ... ستبقى كما هي تماماً كما أرفقتها في آخر ملف لك.







    @staticmethod
    def add_transfer(data: Dict) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO fuel_transfers (transfer_date, tank_id, quantity_liters, notes) VALUES (%s, %s, %s, %s) RETURNING id",
                    (data.get('transfer_date', date.today()), data['tank_id'], data['quantity_liters'], data.get('notes'))
                )
                return {'success': True, 'id': cursor.fetchone()['id']}
        except Exception as e:
            logger.error(f"خطأ في إضافة عملية تنزيل مازوت: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_warehouse_stock() -> float:
        with db.get_cursor() as cursor:
            cursor.execute("SELECT COALESCE(SUM(quantity_liters),0) FROM fuel_purchases")
            total_purchased = cursor.fetchone()['coalesce']
            cursor.execute("SELECT COALESCE(SUM(quantity_liters),0) FROM fuel_transfers")
            total_transferred = cursor.fetchone()['coalesce']
            return total_purchased - total_transferred

    @staticmethod
    def get_warehouse_stock_at_date(target_date: date) -> float:
        with db.get_cursor() as cursor:
            cursor.execute("SELECT COALESCE(SUM(quantity_liters),0) FROM fuel_purchases WHERE purchase_date <= %s", (target_date,))
            purchased = cursor.fetchone()['coalesce']
            cursor.execute("SELECT COALESCE(SUM(quantity_liters),0) FROM fuel_transfers WHERE transfer_date <= %s", (target_date,))
            transferred = cursor.fetchone()['coalesce']
            return float(purchased) - float(transferred)

    # ==================== القراءات اليومية للمازوت والحسابات ====================
    @staticmethod
    def get_daily_reading_by_date(reading_date: date) -> Optional[Dict]:
        with db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM daily_readings WHERE reading_date = %s",
                (reading_date,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            result = dict(row)
            for col in ['generator_readings', 'sector_readings', 'tank_readings', 'energy_readings']:
                val = result.get(col)
                if isinstance(val, str):
                    result[col] = json.loads(val)
                elif val is None:
                    result[col] = {}
            for col in ['generator_output', 'sector_output', 'total_fuel_burned', 'generator_efficiency', 'sector_efficiency']:
                if result.get(col) is not None:
                    result[col] = float(result[col])
            return result

    @staticmethod
    def get_previous_day_readings(prev_date: date) -> Optional[Dict]:
        return FuelManagement.get_daily_reading_by_date(prev_date)

    @staticmethod
    def save_daily_reading(data: Dict) -> Dict:
        try:
            reading_date = data['reading_date']
            prev = FuelManagement.get_previous_day_readings(reading_date - timedelta(days=1))
            
            cur_gen = data.get('generator_readings', {})
            cur_sector = data.get('sector_readings', {})
            cur_tanks = data.get('tank_readings', {})
            
            prev_gen = prev['generator_readings'] if prev else {}
            prev_sector = prev['sector_readings'] if prev else {}
            prev_tanks = prev['tank_readings'] if prev else {}
            
            gen_output = 0.0
            for mid, cur_val in cur_gen.items():
                prev_val = float(prev_gen.get(str(mid), 0))
                cur_val_f = float(cur_val)
                gen_output += max(cur_val_f - prev_val, 0)
            
            sector_output = 0.0
            for mid, cur_val in cur_sector.items():
                prev_val = float(prev_sector.get(str(mid), 0))
                cur_val_f = float(cur_val)
                sector_output += max(cur_val_f - prev_val, 0)
            
            total_fuel_burned = 0.0
            with db.get_cursor() as cursor:
                cursor.execute(
                    "SELECT tank_id, SUM(quantity_liters) as added FROM fuel_transfers WHERE transfer_date = %s GROUP BY tank_id",
                    (reading_date,)
                )
                added_dict = {row['tank_id']: float(row['added']) for row in cursor.fetchall()}
            
            tanks_info = {t['id']: float(t['liters_per_cm']) for t in FuelManagement.get_tanks()}
            for tank_id, cur_cm in cur_tanks.items():
                prev_cm = float(prev_tanks.get(str(tank_id), 0))
                added = added_dict.get(int(tank_id), 0.0)
                liters_per_cm = tanks_info.get(int(tank_id), 10.75)
                burned = (prev_cm - float(cur_cm)) * liters_per_cm + added
                if burned < 0:
                    burned = 0
                total_fuel_burned += burned
            
            gen_efficiency = gen_output / total_fuel_burned if total_fuel_burned > 0 else 0
            sector_efficiency = sector_output / total_fuel_burned if total_fuel_burned > 0 else 0
            
            gen_json = json.dumps({str(k): float(v) for k, v in cur_gen.items()})
            sec_json = json.dumps({str(k): float(v) for k, v in cur_sector.items()})
            tank_json = json.dumps({str(k): float(v) for k, v in cur_tanks.items()})
            energy_json = json.dumps(data.get('energy_readings', {}))
            
            with db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO daily_readings
                    (reading_date, generator_readings, sector_readings, tank_readings, energy_readings,
                     generator_output, sector_output, total_fuel_burned,
                     generator_efficiency, sector_efficiency, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (reading_date) DO UPDATE SET
                        generator_readings = EXCLUDED.generator_readings,
                        sector_readings = EXCLUDED.sector_readings,
                        tank_readings = EXCLUDED.tank_readings,
                        energy_readings = EXCLUDED.energy_readings,
                        generator_output = EXCLUDED.generator_output,
                        sector_output = EXCLUDED.sector_output,
                        total_fuel_burned = EXCLUDED.total_fuel_burned,
                        generator_efficiency = EXCLUDED.generator_efficiency,
                        sector_efficiency = EXCLUDED.sector_efficiency,
                        notes = EXCLUDED.notes,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    reading_date, gen_json, sec_json, tank_json, energy_json,
                    float(gen_output), float(sector_output), float(total_fuel_burned),
                    float(gen_efficiency), float(sector_efficiency),
                    data.get('notes', '')
                ))
            return {
                'success': True,
                'generator_output': gen_output,
                'sector_output': sector_output,
                'total_fuel_burned': total_fuel_burned,
                'gen_efficiency': gen_efficiency,
                'sector_efficiency': sector_efficiency
            }
        except Exception as e:
            logger.error(f"خطأ في حفظ القراءة اليومية: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_daily_readings(start_date: date, end_date: date) -> List[Dict]:
        with db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM daily_readings WHERE reading_date BETWEEN %s AND %s ORDER BY reading_date",
                (start_date, end_date)
            )
            rows = cursor.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                for col in ['generator_readings', 'sector_readings', 'tank_readings', 'energy_readings']:
                    val = d.get(col)
                    if isinstance(val, str):
                        d[col] = json.loads(val)
                    elif val is None:
                        d[col] = {}
                for col in ['generator_output', 'sector_output', 'total_fuel_burned', 'generator_efficiency', 'sector_efficiency']:
                    if d.get(col) is not None:
                        d[col] = float(d[col])
                result.append(d)
            return result

    # ==================== الجرد الأسبوعي ====================
    @staticmethod
    def get_weekly_inventories() -> List[Dict]:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT cycle_name, start_date, end_date, id, notes
                    FROM weekly_inventory
                    ORDER BY start_date DESC
                """)
                cycles = cursor.fetchall()
                result = []
                for cycle in cycles:
                    cycle_name = cycle['cycle_name']
                    start = cycle['start_date']
                    end = cycle['end_date']
                    
                    readings = FuelManagement.get_daily_readings(start, end)
                    if not readings:
                        continue
                    total_gen = sum(r['generator_output'] for r in readings)
                    total_sector = sum(r['sector_output'] for r in readings)
                    total_fuel = sum(r['total_fuel_burned'] for r in readings)
                    avg_gen_eff = total_gen / total_fuel if total_fuel > 0 else 0
                    avg_sector_eff = total_sector / total_fuel if total_fuel > 0 else 0
                    
                    energy_output = FuelManagement.calculate_energy_output(start, end)
                    total_production = total_gen + energy_output
                    
                    warehouse = FuelManagement.get_warehouse_stock_at_date(end)
                    result.append({
                        'id': cycle['id'],
                        'cycle_name': cycle_name,
                        'start_date': start,
                        'end_date': end,
                        'total_generator_output': total_gen,
                        'total_sector_output': total_sector,
                        'total_fuel_burned': total_fuel,
                        'avg_generator_efficiency': avg_gen_eff,
                        'avg_sector_efficiency': avg_sector_eff,
                        'energy_output': energy_output,
                        'total_production': total_production,
                        'warehouse_remaining_liters': warehouse,
                        'notes': cycle['notes'] or ''
                    })
                return result
        except Exception as e:
            logger.error(f"خطأ في جلب الجرد الأسبوعي: {e}")
            return []

    @staticmethod
    def generate_weekly_inventory(cycle_name: str, start_date: date, end_date: date) -> Dict:
        try:
            readings = FuelManagement.get_daily_readings(start_date, end_date)
            if not readings:
                return {'success': False, 'error': 'لا توجد قراءات مازوت في هذه الفترة'}
            total_gen = sum(r['generator_output'] for r in readings)
            total_sector = sum(r['sector_output'] for r in readings)
            total_fuel = sum(r['total_fuel_burned'] for r in readings)
            avg_gen_eff = total_gen / total_fuel if total_fuel > 0 else 0
            avg_sector_eff = total_sector / total_fuel if total_fuel > 0 else 0

            energy_output = FuelManagement.calculate_energy_output(start_date, end_date)
            total_production = total_gen + energy_output

            last_day = readings[-1]
            tank_readings = last_day['tank_readings']
            tanks_info = {t['id']: float(t['liters_per_cm']) for t in FuelManagement.get_tanks()}
            final_tank_status = {}
            for tank_id, cm in tank_readings.items():
                liters = float(cm) * tanks_info.get(int(tank_id), 10.75)
                final_tank_status[str(tank_id)] = {'cm': cm, 'liters': liters}

            warehouse_remaining = FuelManagement.get_warehouse_stock_at_date(end_date)

            with db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO weekly_inventory
                    (cycle_name, start_date, end_date, total_generator_output, total_sector_output,
                     total_fuel_burned, avg_generator_efficiency, avg_sector_efficiency,
                     tank_final_readings, warehouse_remaining_liters, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    cycle_name, start_date, end_date,
                    total_gen, total_sector, total_fuel,
                    avg_gen_eff, avg_sector_eff,
                    json.dumps(final_tank_status), warehouse_remaining,
                    f"جرد تلقائي للدورة {cycle_name}"
                ))
                inv_id = cursor.fetchone()['id']
            return {'success': True, 'id': inv_id, 'total_generator_output': total_gen,
                    'total_sector_output': total_sector, 'total_fuel_burned': total_fuel,
                    'energy_output': energy_output, 'total_production': total_production,
                    'warehouse_remaining': warehouse_remaining}
        except Exception as e:
            logger.error(f"خطأ في توليد الجرد الأسبوعي: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def update_cycle_name(inv_id: int, new_name: str) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("UPDATE weekly_inventory SET cycle_name = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (new_name, inv_id))
                return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def delete_weekly_inventory(inv_id: int) -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("DELETE FROM weekly_inventory WHERE id = %s", (inv_id,))
                return {'success': True}
        except Exception as e:
            logger.error(f"خطأ في حذف الجرد الأسبوعي: {e}")
            return {'success': False, 'error': str(e)}

    # ==================== الحسابات المالية للطاقة ====================
    @staticmethod
    def process_energy_production(meter_id: int, reading_date: date) -> Optional[Dict]:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, reading_value FROM energy_daily_readings
                    WHERE meter_id = %s AND reading_date = %s
                """, (meter_id, reading_date))
                current = cursor.fetchone()
                if not current:
                    return None
                reading_id = current['id']
                current_val = float(current['reading_value'])

                cursor.execute("""
                    SELECT reading_value FROM energy_daily_readings
                    WHERE meter_id = %s AND reading_date < %s
                    ORDER BY reading_date DESC LIMIT 1
                """, (meter_id, reading_date))
                prev = cursor.fetchone()
                prev_val = float(prev['reading_value']) if prev else 0.0

                production_kw = max(current_val - prev_val, 0.0)

                cursor.execute("SELECT conversion_rate, current_balance FROM energy_meters WHERE id = %s", (meter_id,))
                meter = cursor.fetchone()
                if not meter:
                    return None
                rate = float(meter['conversion_rate'] or 0)
                financial_amount = production_kw * rate
                if financial_amount == 0:
                    return None

                balance_before = float(meter['current_balance'])
                balance_after = balance_before + financial_amount

                cursor.execute("""
                    INSERT INTO energy_account_transactions
                    (meter_id, transaction_date, transaction_type, amount, balance_before, balance_after, reading_id, notes)
                    VALUES (%s, %s, 'production', %s, %s, %s, %s, %s)
                """, (
                    meter_id,
                    datetime.combine(reading_date, datetime.min.time()),
                    financial_amount,
                    balance_before,
                    balance_after,
                    reading_id,
                    f"إنتاج تلقائي من قراءة يوم {reading_date}"
                ))

                cursor.execute("UPDATE energy_meters SET current_balance = %s WHERE id = %s", (balance_after, meter_id))

                logger.info(f"عداد {meter_id}: إنتاج {financial_amount:.2f} ل.س (رصيد {balance_before} -> {balance_after})")
                return {
                    'production_kw': production_kw,
                    'financial_amount': financial_amount,
                    'balance_before': balance_before,
                    'balance_after': balance_after
                }
        except Exception as e:
            logger.error(f"خطأ في process_energy_production: {e}")
            return None

    @staticmethod
    def record_payment_for_meter(meter_id: int, amount: float, profit_id: int = None,
                                 user_id: int = None, note: str = "") -> Dict:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT current_balance FROM energy_meters WHERE id = %s", (meter_id,))
                row = cursor.fetchone()
                if not row:
                    return {'success': False, 'error': 'العداد غير موجود'}
                balance_before = float(row['current_balance'])
                balance_after = balance_before - amount

                cursor.execute("""
                    INSERT INTO energy_account_transactions
                    (meter_id, transaction_date, transaction_type, amount, balance_before, balance_after,
                     profit_id, notes, created_by)
                    VALUES (%s, CURRENT_TIMESTAMP, 'payment', %s, %s, %s, %s, %s, %s)
                """, (
                    meter_id,
                    -amount,
                    balance_before,
                    balance_after,
                    profit_id,
                    note or "توزيع أرباح طاقة",
                    user_id
                ))

                cursor.execute("UPDATE energy_meters SET current_balance = %s WHERE id = %s",
                               (balance_after, meter_id))
                return {'success': True, 'balance_before': balance_before, 'balance_after': balance_after}
        except Exception as e:
            logger.error(f"خطأ في تسجيل دفعة للعداد {meter_id}: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_energy_account_statement(meter_id: int, start_date: date = None, end_date: date = None) -> List[Dict]:
        with db.get_cursor() as cursor:
            params = [meter_id]
            where = ""
            if start_date:
                where += " AND t.transaction_date >= %s"
                params.append(start_date)
            if end_date:
                where += " AND t.transaction_date < %s"
                params.append(end_date + timedelta(days=1))
            cursor.execute(f"""
                SELECT t.*, u.full_name as created_by_name
                FROM energy_account_transactions t
                LEFT JOIN users u ON t.created_by = u.id
                WHERE t.meter_id = %s {where}
                ORDER BY t.transaction_date
            """, params)
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def recalculate_meter_balance(meter_id: int):
        with db.get_cursor() as cursor:
            cursor.execute("SELECT COALESCE(SUM(amount),0) FROM energy_account_transactions WHERE meter_id = %s", (meter_id,))
            total = float(cursor.fetchone()['coalesce'])
            cursor.execute("UPDATE energy_meters SET current_balance = %s WHERE id = %s", (total, meter_id))