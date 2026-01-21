# modules/customers.py
from database.connection import db
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class CustomerManager:
    """مدير عمليات الزبائن"""
        
    def __init__(self):
        self.table_name = "customers"

    def add_customer(self, customer_data: Dict) -> Dict:
        """إضافة زبون جديد"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO customers 
                    (sector_id, box_number, serial_number, name, phone_number,
                    current_balance, last_counter_reading, visa_balance,
                    withdrawal_amount, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, name, box_number, serial_number
                """, (
                    customer_data.get('sector_id'),
                    customer_data.get('box_number', ''),
                    customer_data.get('serial_number', ''),
                    customer_data['name'],
                    customer_data.get('phone_number', ''),
                    customer_data.get('current_balance', 0),
                    customer_data.get('last_counter_reading', 0),
                    customer_data.get('visa_balance', 0),
                    customer_data.get('withdrawal_amount', 0),
                    customer_data.get('notes', '')
                ))
                
                result = cursor.fetchone()
                
                # تسجيل العملية في السجل التاريخي
                if result:
                    cursor.execute("""
                        INSERT INTO customer_history 
                        (customer_id, action_type, transaction_type, 
                        old_value, new_value, amount,
                        current_balance_before, current_balance_after,
                        notes, created_by, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, (
                        result['id'],
                        'add_customer',
                        'new_customer',
                        0,
                        customer_data.get('current_balance', 0),
                        customer_data.get('current_balance', 0),
                        0,
                        customer_data.get('current_balance', 0),
                        f"إضافة زبون جديد: {result['name']}",
                        customer_data.get('user_id', 1)
                    ))
                
                logger.info(f"تم إضافة زبون جديد: {result['name']}")
                return {
                    'success': True,
                    'customer_id': result['id'],
                    'message': f"تم إضافة الزبون {result['name']} بنجاح"
                }
                
        except Exception as e:
            logger.error(f"خطأ في إضافة زبون: {e}")
            return {
                'success': False,
                'error': f"فشل إضافة الزبون: {str(e)}"
            }

    def get_customer(self, customer_id: int) -> Optional[Dict]:
        """الحصول على بيانات زبون"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT c.*, s.name as sector_name
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.id = %s
                """, (customer_id,))
                
                customer = cursor.fetchone()
                return dict(customer) if customer else None
                
        except Exception as e:
            logger.error(f"خطأ في جلب بيانات الزبون: {e}")
            return None

    def search_customers(self, search_term: str = "", sector_id: int = None) -> List[Dict]:
        """بحث الزبائن"""
        try:
            with db.get_cursor() as cursor:
                query = """
                    SELECT c.*, s.name as sector_name
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.is_active = TRUE
                """
                params = []
                
                if search_term:
                    query += " AND (c.name ILIKE %s OR c.box_number ILIKE %s OR c.phone_number ILIKE %s)"
                    params.extend([f"%{search_term}%"] * 3)
                
                if sector_id:
                    query += " AND c.sector_id = %s"
                    params.append(sector_id)
                
                query += " ORDER BY c.name"
                
                cursor.execute(query, params)
                customers = cursor.fetchall()
                
                return [dict(customer) for customer in customers]
                
        except Exception as e:
            logger.error(f"خطأ في بحث الزبائن: {e}")
            return []

    def update_customer(self, customer_id: int, update_data: Dict) -> Dict:
        """تحديث بيانات زبون مع تسجيل التاريخ"""
        try:
            with db.get_cursor() as cursor:
                # 1. جلب البيانات القديمة أولاً
                cursor.execute("""
                    SELECT 
                        c.name, c.phone_number, c.current_balance,
                        c.visa_balance, c.withdrawal_amount,
                        c.last_counter_reading, c.notes,
                        c.sector_id, c.box_number, c.serial_number,
                        c.telegram_username, c.is_active
                    FROM customers c 
                    WHERE id = %s
                """, (customer_id,))
                
                old_data = cursor.fetchone()
                if not old_data:
                    return {'success': False, 'error': 'الزبون غير موجود'}
                
                # 2. تحديث بيانات الزبون
                set_clauses = []
                params = []
                
                # التحقق من الحقول وتحديثها
                fields_to_update = {
                    'name': update_data.get('name'),
                    'sector_id': update_data.get('sector_id'),
                    'box_number': update_data.get('box_number'),
                    'serial_number': update_data.get('serial_number'),
                    'phone_number': update_data.get('phone_number'),
                    'telegram_username': update_data.get('telegram_username'),
                    'current_balance': update_data.get('current_balance'),
                    'last_counter_reading': update_data.get('last_counter_reading'),
                    'visa_balance': update_data.get('visa_balance'),
                    'withdrawal_amount': update_data.get('withdrawal_amount'),
                    'notes': update_data.get('notes'),
                    'is_active': update_data.get('is_active')
                }
                
                for field, value in fields_to_update.items():
                    if value is not None:
                        # إذا كان الرصيد يتغير، نسجل التغير
                        if field in ['current_balance', 'visa_balance', 'withdrawal_amount']:
                            old_value = float(old_data.get(field, 0))
                            new_value = float(value)
                            if old_value != new_value:
                                # تسجيل التغير في السجل التاريخي
                                self._log_balance_change(
                                    customer_id, field, old_value, new_value, 
                                    update_data.get('user_id', 1), 
                                    update_data.get('notes', '')
                                )
                        
                        set_clauses.append(f"{field} = %s")
                        params.append(value)
                
                if not set_clauses:
                    return {'success': True, 'message': 'لم يتم تغيير أي بيانات'}
                
                # إضافة معرف الزبون وتاريخ التحديث
                params.append(customer_id)
                set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                
                # تنفيذ التحديث
                query = f"""
                    UPDATE customers 
                    SET {', '.join(set_clauses)}
                    WHERE id = %s
                    RETURNING id, name
                """
                
                cursor.execute(query, params)
                updated_customer = cursor.fetchone()
                
                if not updated_customer:
                    return {'success': False, 'error': 'فشل تحديث الزبون'}
                
                # 3. تسجيل العملية في سجل النشاطات
                cursor.execute("""
                    INSERT INTO activity_logs (user_id, action_type, description)
                    VALUES (%s, 'update_customer', %s)
                """, (
                    update_data.get('user_id', 1),
                    f"تم تحديث بيانات الزبون {old_data['name']} (ID: {customer_id})"
                ))
                
                # 4. تسجيل التعديل في السجل التاريخي
                self._log_customer_update(customer_id, old_data, update_data)
                
                logger.info(f"تم تحديث الزبون: {updated_customer['name']}")
                return {
                    'success': True,
                    'message': f"تم تحديث بيانات الزبون {updated_customer['name']} بنجاح"
                }
                
        except Exception as e:
            logger.error(f"خطأ في تحديث الزبون: {e}")
            return {
                'success': False,
                'error': f"فشل تحديث الزبون: {str(e)}"
            }

    def _log_balance_change(self, customer_id, field, old_value, new_value, user_id, notes):
        """تسجيل تغيير الرصيد في السجل التاريخي"""
        try:
            field_names = {
                'current_balance': 'الرصيد الحالي',
                'visa_balance': 'رصيد التأشيرة',
                'withdrawal_amount': 'مبلغ السحب'
            }
            
            with db.get_cursor() as cursor:
                # الحصول على الرصيد الحالي قبل التغيير
                cursor.execute("""
                    SELECT current_balance FROM customers WHERE id = %s
                """, (customer_id,))
                current_balance_result = cursor.fetchone()
                current_balance_before = float(current_balance_result['current_balance']) if current_balance_result else 0
                
                # تسجيل التغيير
                cursor.execute("""
                    INSERT INTO customer_history 
                    (customer_id, action_type, transaction_type, 
                    old_value, new_value, amount,
                    current_balance_before, current_balance_after,
                    notes, created_by, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    customer_id,
                    'balance_adjustment',
                    'manual_adjustment',
                    float(old_value),
                    float(new_value),
                    float(new_value - old_value),
                    current_balance_before,
                    float(new_value) if field == 'current_balance' else current_balance_before + (new_value - old_value),
                    f"{field_names.get(field, field)}: {old_value:,.0f} → {new_value:,.0f}. {notes}",
                    user_id
                ))
                
        except Exception as e:
            logger.error(f"خطأ في تسجيل تغيير الرصيد: {e}")

    def _log_customer_update(self, customer_id, old_data, new_data):
        """تسجيل تحديث بيانات الزبون في السجل التاريخي"""
        try:
            changes = []
            
            # مقارنة الحقول وتحديد التغيرات
            for field in ['name', 'phone_number', 'notes', 'box_number', 'serial_number']:
                old_val = old_data.get(field, '')
                new_val = new_data.get(field, '')
                
                if str(old_val).strip() != str(new_val).strip():
                    field_names = {
                        'name': 'الاسم',
                        'phone_number': 'رقم الهاتف',
                        'notes': 'ملاحظات',
                        'box_number': 'رقم العلبة',
                        'serial_number': 'رقم المسلسل'
                    }
                    
                    old_display = old_val if old_val else '(فارغ)'
                    new_display = new_val if new_val else '(فارغ)'
                    
                    changes.append(f"{field_names.get(field, field)}: {old_display} → {new_display}")
            
            if changes:
                with db.get_cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO customer_history 
                        (customer_id, action_type, transaction_type, 
                        details, notes, created_by, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, (
                        customer_id,
                        'customer_update',
                        'info_update',
                        ' | '.join(changes),
                        f"تحديث بيانات الزبون: {new_data.get('name', old_data.get('name', ''))}",
                        new_data.get('user_id', 1)
                    ))
                    
        except Exception as e:
            logger.error(f"خطأ في تسجيل تحديث الزبون: {e}")

    def delete_customer(self, customer_id: int, soft_delete: bool = True) -> Dict:
        """حذف الزبون (حذف ناعم أو فعلي)"""
        try:
            with db.get_cursor() as cursor:
                # جلب بيانات الزبون قبل الحذف
                cursor.execute("SELECT name FROM customers WHERE id = %s", (customer_id,))
                customer = cursor.fetchone()
                
                if not customer:
                    return {'success': False, 'error': 'الزبون غير موجود'}
                
                customer_name = customer['name']
                
                if soft_delete:
                    # حذف ناعم
                    cursor.execute("""
                        UPDATE customers 
                        SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        RETURNING name
                    """, (customer_id,))
                else:
                    # حذف فعلي
                    cursor.execute("""
                        DELETE FROM customers 
                        WHERE id = %s
                        RETURNING name
                    """, (customer_id,))
                
                result = cursor.fetchone()
                
                if result:
                    # تسجيل الحذف في السجل التاريخي
                    cursor.execute("""
                        INSERT INTO customer_history 
                        (customer_id, action_type, transaction_type, 
                        notes, created_by, created_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, (
                        customer_id,
                        'delete_customer',
                        'soft_delete' if soft_delete else 'hard_delete',
                        f"حذف الزبون: {customer_name} ({'ناعم' if soft_delete else 'فعلي'})",
                        1  # user_id افتراضي
                    ))
                    
                    logger.info(f"تم حذف الزبون: {customer_name}")
                    return {
                        'success': True,
                        'message': f"تم حذف الزبون {customer_name} بنجاح"
                    }
                else:
                    return {
                        'success': False,
                        'error': 'فشل حذف الزبون'
                    }
                    
        except Exception as e:
            logger.error(f"خطأ في حذف الزبون: {e}")
            return {
                'success': False,
                'error': f"فشل حذف الزبون: {str(e)}"
            }

    def get_customer_statistics(self) -> Dict:
        """الحصول على إحصائيات الزبائن"""
        try:
            with db.get_cursor() as cursor:
                # إجمالي الزبائن
                cursor.execute("SELECT COUNT(*) FROM customers WHERE is_active = TRUE")
                total_customers = cursor.fetchone()['count']
                
                # الزبائن برصيد سالب
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM customers 
                    WHERE is_active = TRUE AND current_balance < 0
                """)
                negative_balance = cursor.fetchone()['count']
                
                # الزبائن برصيد موجب
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM customers 
                    WHERE is_active = TRUE AND current_balance > 0
                """)
                positive_balance = cursor.fetchone()['count']
                
                # الزبائن بدون رصيد
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM customers 
                    WHERE is_active = TRUE AND current_balance = 0
                """)
                zero_balance = cursor.fetchone()['count']
                
                return {
                    'total_customers': total_customers,
                    'negative_balance': negative_balance,
                    'positive_balance': positive_balance,
                    'zero_balance': zero_balance,
                    'negative_percentage': round((negative_balance / total_customers * 100), 2) if total_customers > 0 else 0,
                    'positive_percentage': round((positive_balance / total_customers * 100), 2) if total_customers > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"خطأ في جلب إحصائيات الزبائن: {e}")
            return {}

    def get_customers_by_sector(self) -> Dict:
        """الحصول على توزيع الزبائن حسب القطاع"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT s.name as sector_name, COUNT(c.id) as customer_count,
                        SUM(c.current_balance) as total_balance
                    FROM sectors s
                    LEFT JOIN customers c ON s.id = c.sector_id AND c.is_active = TRUE
                    GROUP BY s.id, s.name
                    ORDER BY s.name
                """)
                
                results = cursor.fetchall()
                return {
                    'sectors': [dict(row) for row in results],
                    'total': sum(row['customer_count'] or 0 for row in results)
                }
            
        except Exception as e:
            logger.error(f"خطأ في جلب توزيع الزبائن: {e}")
            return {'sectors': [], 'total': 0}

    def delete_all_customers(self, confirm=True) -> Dict:
        """حذف جميع الزبائن (يستخدم مع الحذر)"""
        try:
            with db.get_cursor() as cursor:
                # الحصول على عدد الزبائن قبل الحذف
                cursor.execute("SELECT COUNT(*) as count FROM customers")
                count_before = cursor.fetchone()['count']
                
                if count_before == 0:
                    return {
                        'success': True,
                        'message': 'لا توجد زبائن لحذفها',
                        'deleted_count': 0
                    }
                
                # تسجيل جميع الزبائن المحذوفة في السجل التاريخي
                cursor.execute("""
                    SELECT id, name FROM customers
                """)
                all_customers = cursor.fetchall()
                
                for customer in all_customers:
                    cursor.execute("""
                        INSERT INTO customer_history 
                        (customer_id, action_type, transaction_type, 
                        notes, created_by, created_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, (
                        customer['id'],
                        'delete_customer',
                        'bulk_delete',
                        f"حذف جماعي - الزبون: {customer['name']}",
                        1  # user_id افتراضي
                    ))
                
                # حذف جميع الزبائن
                cursor.execute("DELETE FROM customers RETURNING id, name")
                deleted_customers = cursor.fetchall()
                
                logger.info(f"تم حذف {len(deleted_customers)} زبون")
                
                # إرجاع النتيجة مع تفاصيل الحذف
                return {
                    'success': True,
                    'deleted_count': len(deleted_customers),
                    'deleted_customers': [dict(customer) for customer in deleted_customers],
                    'message': f"تم حذف {len(deleted_customers)} زبون بنجاح"
                }
                
        except Exception as e:
            logger.error(f"خطأ في حذف جميع الزبائن: {e}")
            return {
                'success': False,
                'error': f"فشل حذف الزبائن: {str(e)}"
            }

    def delete_customers_by_sector(self, sector_id: int) -> Dict:
        """حذف زبائن قطاع محدد"""
        try:
            with db.get_cursor() as cursor:
                # الحصول على اسم القطاع
                cursor.execute("SELECT name FROM sectors WHERE id = %s", (sector_id,))
                sector = cursor.fetchone()
                
                if not sector:
                    return {'success': False, 'error': 'القطاع غير موجود'}
                
                # الحصول على زبائن القطاع قبل الحذف
                cursor.execute("""
                    SELECT id, name FROM customers WHERE sector_id = %s
                """, (sector_id,))
                sector_customers = cursor.fetchall()
                
                # تسجيل الحذف في السجل التاريخي لكل زبون
                for customer in sector_customers:
                    cursor.execute("""
                        INSERT INTO customer_history 
                        (customer_id, action_type, transaction_type, 
                        notes, created_by, created_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, (
                        customer['id'],
                        'delete_customer',
                        'sector_delete',
                        f"حذف قطاعي - القطاع: {sector['name']} - الزبون: {customer['name']}",
                        1  # user_id افتراضي
                    ))
                
                # حذف زبائن القطاع
                cursor.execute("""
                    DELETE FROM customers 
                    WHERE sector_id = %s 
                    RETURNING id, name
                """, (sector_id,))
                
                deleted_customers = cursor.fetchall()
                
                logger.info(f"تم حذف {len(deleted_customers)} زبون من قطاع {sector['name']}")
                
                return {
                    'success': True,
                    'deleted_count': len(deleted_customers),
                    'sector_name': sector['name'],
                    'message': f"تم حذف {len(deleted_customers)} زبون من قطاع {sector['name']}"
                }
                
        except Exception as e:
            logger.error(f"خطأ في حذف زبائن القطاع: {e}")
            return {
                'success': False,
                'error': f"فشل حذف زبائن القطاع: {str(e)}"
            }