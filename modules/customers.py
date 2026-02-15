# modules/customers.py
from database.connection import db
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class CustomerManager:
    def get_cut_lists_by_box(self, min_balance: float = 0, max_balance: float = -1000, exclude_categories: list = None) -> dict:
        """
        جلب قوائم القطع لكل علبة (مولدة/علبة توزيع/رئيسية) مع زبائنها الذين رصيدهم السالب ضمن مجال محدد، مع استثناء تصنيفات مالية معينة.
        :param min_balance: الحد الأدنى للرصيد (عادة 0)
        :param max_balance: الحد الأعلى للرصيد (سالب)
        :param exclude_categories: قائمة التصنيفات المالية المستثناة (مثل VIP، مجاني)
        :return: dict {box_id: {box_info, customers: [...]}}
        """
        try:
            if exclude_categories is None:
                exclude_categories = []
            with db.get_cursor() as cursor:
                # جلب جميع العلب (مولدة/علبة توزيع/رئيسية)
                cursor.execute("""
                    SELECT id, name, box_number, meter_type, sector_id
                    FROM customers
                    WHERE meter_type IN ('مولدة', 'علبة توزيع', 'رئيسية')
                      AND is_active = TRUE
                """)
                boxes = cursor.fetchall()
                result = {}
                for box in boxes:
                    box_id = box['id']
                    # جلب الزبائن التابعين لهذه العلبة وضمن مجال الرصيد المطلوب
                    query = """
                        SELECT id, name, box_number, current_balance, financial_category, phone_number
                        FROM customers
                        WHERE parent_meter_id = %s
                          AND is_active = TRUE
                          AND current_balance <= %s AND current_balance >= %s
                    """
                    params = [box_id, min_balance, max_balance]
                    if exclude_categories:
                        query += " AND financial_category NOT IN (%s)" % (', '.join(['%s']*len(exclude_categories)))
                        params.extend(exclude_categories)
                    query += " ORDER BY current_balance ASC"
                    cursor.execute(query, params)
                    customers = cursor.fetchall()
                    if customers:
                        result[box_id] = {
                            'box_info': dict(box),
                            'customers': [dict(c) for c in customers]
                        }
                return result
        except Exception as e:
            logger.error(f"خطأ في جلب قوائم القطع: {e}")
            return {}

    def get_negative_balance_customers_by_sector(self, financial_category: str = None, sector_id: int = None) -> dict:
        """
        جلب الزبائن ذوي الرصيد السالب (قوائم الكسر) مرتبين من الأكبر إلى الأصغر لكل قطاع مع إمكانية الفلترة حسب التصنيف المالي والقطاع.
        :param financial_category: تصنيف الزبون المالي (اختياري: عادي، مجاني، VIP ...)
        :param sector_id: رقم القطاع (اختياري)
        :return: dict {اسم القطاع: [قائمة الزبائن]}
        """
        try:
            with db.get_cursor() as cursor:
                query = """
                    SELECT 
                        s.name as sector_name,
                        s.id as sector_id,
                        c.id,
                        c.name,
                        c.box_number,
                        c.current_balance,
                        c.financial_category,
                        c.phone_number
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.current_balance < 0
                      AND c.is_active = TRUE
                """
                params = []
                if financial_category:
                    query += " AND c.financial_category = %s"
                    params.append(financial_category)
                if sector_id:
                    query += " AND c.sector_id = %s"
                    params.append(sector_id)
                query += " ORDER BY s.name, c.current_balance ASC"  # ASC لأن الرصيد سالب (الأكبر فالأصغر)
                cursor.execute(query, params)
                rows = cursor.fetchall()
                sector_dict = {}
                for row in rows:
                    sector = row['sector_name'] or 'بدون قطاع'
                    if sector not in sector_dict:
                        sector_dict[sector] = {'customers': []}
                    sector_dict[sector]['customers'].append(dict(row))
                return sector_dict
        except Exception as e:
            logger.error(f"خطأ في جلب قوائم الكسر: {e}")
            return {}

    def report_free_customers_by_sector(self) -> dict:
        """تقرير الزبائن المجانيين حسب القطاع - نسخة مبسطة"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        s.name as sector_name,
                        c.id,
                        c.name,
                        c.box_number,
                        c.current_balance,
                        c.withdrawal_amount,
                        c.visa_balance,
                        c.phone_number
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.financial_category IN ('free', 'free_vip')
                    AND c.is_active = TRUE
                    ORDER BY s.name, c.name
                """)
                
                rows = cursor.fetchall()
                sector_dict = {}
                
                for row in rows:
                    sector = row['sector_name'] or 'بدون قطاع'
                    if sector not in sector_dict:
                        sector_dict[sector] = {'customers': []}
                    sector_dict[sector]['customers'].append(dict(row))
                
                return sector_dict
                
        except Exception as e:
            logger.error(f"خطأ في تقرير الزبائن المجانيين: {e}")
            return {}
        

    """مدير عمليات الزبائن مع دعم العدادات الهرمية"""

    def __init__(self):
        self.table_name = "customers"

    def add_customer(self, customer_data: Dict) -> Dict:
        """إضافة زبون جديد مع دعم العلاقات الهرمية"""
        try:
            # التحقق من parent_meter_id إذا كان موجودًا
            parent_meter_id = customer_data.get('parent_meter_id')
            if parent_meter_id:
                with db.get_cursor() as cursor:
                    # التحقق من وجود العلبة الأم وأنها في نفس القطاع
                    cursor.execute("""
                        SELECT sector_id, meter_type FROM customers 
                        WHERE id = %s AND is_active = TRUE
                    """, (parent_meter_id,))
                    parent = cursor.fetchone()
                    
                    if not parent:
                        raise ValueError("العلبة الأم غير موجودة")
                    
                    if parent['sector_id'] != customer_data.get('sector_id'):
                        raise ValueError("العلبة الأم يجب أن تكون في نفس القطاع")
                    
                    # التحقق من توافق أنواع العدادات
                    meter_type = customer_data.get('meter_type', 'زبون')
                    parent_meter_type = parent['meter_type']
                    
                    if not self._validate_meter_hierarchy(parent_meter_type, meter_type):
                        raise ValueError(f"نوع العداد '{meter_type}' غير متوافق مع العلبة الأم من نوع '{parent_meter_type}'")
            
            with db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO customers 
                    (sector_id, box_number, serial_number, name, phone_number,
                    current_balance, last_counter_reading, visa_balance,
                    withdrawal_amount, notes, meter_type, parent_meter_id, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, name, box_number, serial_number, meter_type, parent_meter_id
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
                    customer_data.get('notes', ''),
                    customer_data.get('meter_type', 'زبون'),
                    parent_meter_id,
                    customer_data.get('is_active', True)
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
                        f"إضافة زبون جديد: {result['name']} (نوع: {customer_data.get('meter_type', 'زبون')}, علبة أم: {parent_meter_id if parent_meter_id else 'لا يوجد'})",
                        customer_data.get('user_id', 1)
                    ))
                
                logger.info(f"تم إضافة زبون جديد: {result['name']} - نوع: {result.get('meter_type', 'زبون')}")
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

    def _validate_meter_hierarchy(self, parent_type: str, child_type: str) -> bool:
        """التحقق من صحة الهرمية بين نوعي العدادات - نسخة مرنة"""
        
        # القواعد المرنة:
        # 1. المولدة يمكن أن يكون لها: علب توزيع، عدادات رئيسية، وزبائن مباشرة
        # 2. علبة التوزيع يمكن أن يكون لها: عدادات رئيسية، وزبائن
        # 3. العداد الرئيسي يمكن أن يكون له: زبائن فقط
        # 4. الزبون لا يمكن أن يكون له أبناء
        
        # تعريف الشجرة الهرمية المرنة
        hierarchy_rules = {
            'مولدة': ['علبة توزيع', 'رئيسية', 'زبون'],  # مولدة ← (جميع الأنواع)
            'علبة توزيع': ['رئيسية', 'زبون'],           # علبة توزيع ← (رئيسية، زبون)
            'رئيسية': ['زبون'],                         # رئيسية ← زبون فقط
            'زبون': []                                  # زبون ← لا شيء
        }
        
        # التحقق من وجود النوع الأم في القواعد
        if parent_type not in hierarchy_rules:
            logger.warning(f"نوع العداد الأم '{parent_type}' غير معروف في القواعد الهرمية")
            return False
        
        # الحصول على الأنواع المسموح بها كأبناء
        allowed_children = hierarchy_rules[parent_type]
        
        # التحقق إذا كان النوع الابن مسموحاً
        is_allowed = child_type in allowed_children
        
        if not is_allowed:
            logger.warning(f"نوع العداد '{child_type}' غير مسموح به تحت '{parent_type}'. المسموح: {allowed_children}")
        
        return is_allowed

    def get_allowed_parent_types(self, child_type: str) -> List[str]:
        """الحصول على الأنواع المسموح بها كعلبة أم لنوع معين"""
        allowed_parents = {
            'مولدة': [],  # لا تحتاج إلى علبة أم
            'علبة توزيع': ['مولدة'],
            'رئيسية': ['مولدة', 'علبة توزيع'],
            'زبون': ['مولدة', 'علبة توزيع', 'رئيسية']
        }
        
        return allowed_parents.get(child_type, [])

            
    def get_customer(self, customer_id: int) -> Optional[Dict]:
        """الحصول على بيانات زبون مع العلاقات الهرمية"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        c.*,
                        s.name as sector_name,
                        s.code as sector_code,
                        p.name as parent_name,
                        p.box_number as parent_box_number,
                        p.meter_type as parent_meter_type,
                        p.serial_number as parent_serial_number
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    LEFT JOIN customers p ON c.parent_meter_id = p.id
                    WHERE c.id = %s
                """, (customer_id,))

                customer = cursor.fetchone()
                if not customer:
                    return None

                customer_dict = dict(customer)

                # --- بناء parent_display بنفس منطق بقية الدوال ---
                parent_meter = customer_dict.get('parent_name', '') or ''
                parent_box = customer_dict.get('parent_box_number', '') or ''
                parent_type = customer_dict.get('parent_meter_type', '') or ''

                if parent_box and parent_type and parent_meter:
                    parent_display = f"{parent_box} ({parent_type}) - {parent_meter}"
                elif parent_box and parent_meter:
                    parent_display = f"{parent_box} - {parent_meter}"
                elif parent_meter and parent_type:
                    parent_display = f"{parent_meter} ({parent_type})"
                elif parent_meter:
                    parent_display = parent_meter
                elif parent_box and parent_type:
                    parent_display = f"{parent_box} ({parent_type})"
                elif parent_box:
                    parent_display = parent_box
                else:
                    parent_display = ''

                customer_dict['parent_display'] = parent_display
                # --- نهاية بناء parent_display ---

                # جلب الأبناء إذا كان هناك أبناء
                if customer_dict.get('meter_type') in ['مولدة', 'علبة توزيع', 'رئيسية']:
                    cursor.execute("""
                        SELECT id, name, box_number, meter_type, current_balance, serial_number
                        FROM customers 
                        WHERE parent_meter_id = %s AND is_active = TRUE
                        ORDER BY meter_type, name
                    """, (customer_id,))

                    children = cursor.fetchall()
                    customer_dict['children'] = [dict(child) for child in children]
                    customer_dict['children_count'] = len(children)

                return customer_dict

        except Exception as e:
            logger.error(f"خطأ في جلب بيانات الزبون: {e}")
            return None


    def search_customers(self, search_term: str = "", sector_id: int = None) -> List[Dict]:
        """بحث الزبائن مع العلاقات الهرمية"""
        try:
            with db.get_cursor() as cursor:
                query = """
                    SELECT 
                        c.*,
                        s.name as sector_name,
                        s.code as sector_code,
                        p.name as parent_name,
                        p.box_number as parent_box_number,
                        p.meter_type as parent_meter_type,
                        p.serial_number as parent_serial_number
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    LEFT JOIN customers p ON c.parent_meter_id = p.id
                    WHERE c.is_active = TRUE
                """
                params = []
                
                if search_term:
                    query += " AND (c.name ILIKE %s OR c.box_number ILIKE %s OR c.phone_number ILIKE %s OR c.meter_type ILIKE %s OR c.serial_number ILIKE %s)"
                    params.extend([f"%{search_term}%"] * 5)
                
                if sector_id:
                    query += " AND c.sector_id = %s"
                    params.append(sector_id)
                
                query += """ ORDER BY 
                    CASE c.meter_type 
                        WHEN 'مولدة' THEN 1
                        WHEN 'علبة توزيع' THEN 2
                        WHEN 'رئيسية' THEN 3
                        WHEN 'زبون' THEN 4
                    END,
                    c.parent_meter_id NULLS FIRST,
                    c.name"""
                
                cursor.execute(query, params)
                customers = cursor.fetchall()
                
                # معالجة البيانات لضمان وجود الحقول المطلوبة
                processed_customers = []
                for customer in customers:
                    customer_dict = dict(customer)
                    
                    # =========== إضافة مهمة: بناء parent_display لجميع الزبائن ===========
                    parent_meter = customer_dict.get('parent_name', '')
                    parent_box = customer_dict.get('parent_box_number', '')
                    parent_type = customer_dict.get('parent_meter_type', '')
                    
                    # بناء عرض العلبة الأم بنفس الطريقة للجميع
                    if parent_box and parent_type and parent_meter:
                        parent_display = f"{parent_box} ({parent_type}) - {parent_meter}"
                    elif parent_box and parent_meter:
                        parent_display = f"{parent_box} - {parent_meter}"
                    elif parent_meter and parent_type:
                        parent_display = f"{parent_meter} ({parent_type})"
                    elif parent_meter:
                        parent_display = parent_meter
                    elif parent_box and parent_type:
                        parent_display = f"{parent_box} ({parent_type})"
                    elif parent_box:
                        parent_display = parent_box
                    else:
                        parent_display = ''
                    
                    # إضافة parent_display إلى بيانات الزبون
                    customer_dict['parent_display'] = parent_display
                    # =========== نهاية الإضافة ===========
                    
                    processed_customers.append(customer_dict)
                
                return processed_customers
                    
        except Exception as e:
            logger.error(f"خطأ في بحث الزبائن: {e}")
            return []
            

    def update_customer(self, customer_id: int, update_data: Dict) -> Dict:
        """تحديث بيانات زبون مع التحقق من العلاقات الهرمية"""
        try:
            # التحقق من parent_meter_id إذا كان موجودًا
            parent_meter_id = update_data.get('parent_meter_id')
            if parent_meter_id and parent_meter_id != 'None' and str(parent_meter_id).strip():
                with db.get_cursor() as cursor:
                    # التحقق من وجود العلبة الأم وأنها في نفس القطاع
                    cursor.execute("""
                        SELECT sector_id, meter_type FROM customers 
                        WHERE id = %s AND is_active = TRUE
                    """, (parent_meter_id,))
                    parent = cursor.fetchone()
                    
                    if not parent:
                        raise ValueError("العلبة الأم غير موجودة")
                    
                    # جلب sector_id الحالي للزبون
                    cursor.execute("""
                        SELECT sector_id, meter_type FROM customers WHERE id = %s
                    """, (customer_id,))
                    current = cursor.fetchone()
                    
                    if parent['sector_id'] != (update_data.get('sector_id') or (current['sector_id'] if current else None)):
                        raise ValueError("العلبة الأم يجب أن تكون في نفس القطاع")
                    
                    # التحقق من توافق أنواع العدادات
                    meter_type = update_data.get('meter_type') or (current['meter_type'] if current else 'زبون')
                    parent_meter_type = parent['meter_type']
                    
                    if not self._validate_meter_hierarchy(parent_meter_type, meter_type):
                        raise ValueError(f"نوع العداد '{meter_type}' غير متوافق مع العلبة الأم من نوع '{parent_meter_type}'")
            else:
                # إذا كان parent_meter_id فارغًا أو "None" أو ""، نضبطه على None
                parent_meter_id = None
            
            with db.get_cursor() as cursor:
                # 1. جلب البيانات القديمة أولاً
                cursor.execute("""
                    SELECT 
                        c.name, c.phone_number, c.current_balance,
                        c.visa_balance, c.withdrawal_amount,
                        c.last_counter_reading, c.notes,
                        c.sector_id, c.box_number, c.serial_number,
                        c.telegram_username, c.is_active, c.meter_type,
                        c.parent_meter_id,
                        parent.name as parent_name,
                        parent.box_number as parent_box_number,
                        parent.meter_type as parent_meter_type
                    FROM customers c 
                    LEFT JOIN customers parent ON c.parent_meter_id = parent.id
                    WHERE c.id = %s
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
                    'is_active': update_data.get('is_active'),
                    'meter_type': update_data.get('meter_type'),
                    'parent_meter_id': parent_meter_id
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
                    RETURNING id, name, meter_type, parent_meter_id
                """
                
                cursor.execute(query, params)
                updated_customer = cursor.fetchone()
                
                if not updated_customer:
                    return {'success': False, 'error': 'فشل تحديث الزبون'}
                
                # 3. الحصول على بيانات العلبة الأم لعرضها (الإضافة المطلوبة)
                parent_display = ""
                if updated_customer['parent_meter_id']:
                    cursor.execute("""
                        SELECT name, box_number, meter_type 
                        FROM customers 
                        WHERE id = %s
                    """, (updated_customer['parent_meter_id'],))
                    parent_data = cursor.fetchone()
                    
                    if parent_data:
                        parent_meter = parent_data.get('name', '')
                        parent_box = parent_data.get('box_number', '')
                        parent_type = parent_data.get('meter_type', '')
                        
                        # طرق عرض متعددة للعلبة الأم (الإضافة المطلوبة)
                        if parent_box and parent_type and parent_meter:
                            parent_display = f"{parent_box} ({parent_type}) - {parent_meter}"
                        elif parent_box and parent_meter:
                            parent_display = f"{parent_box} - {parent_meter}"
                        elif parent_meter and parent_type:
                            parent_display = f"{parent_meter} ({parent_type})"
                        elif parent_meter:
                            parent_display = parent_meter
                        elif parent_box and parent_type:
                            parent_display = f"{parent_box} ({parent_type})"
                        elif parent_box:
                            parent_display = parent_box
                        else:
                            parent_display = ''
                
                # 4. تسجيل العملية في سجل النشاطات
                cursor.execute("""
                    INSERT INTO activity_logs (user_id, action_type, description)
                    VALUES (%s, 'update_customer', %s)
                """, (
                    update_data.get('user_id', 1),
                    f"تم تحديث بيانات الزبون {old_data['name']} (ID: {customer_id})"
                ))
                
                # 5. تسجيل التعديل في السجل التاريخي
                self._log_customer_update(customer_id, old_data, update_data)
                
                logger.info(f"تم تحديث الزبون: {updated_customer['name']} - نوع: {updated_customer.get('meter_type')}")
                return {
                    'success': True,
                    'message': f"تم تحديث بيانات الزبون {updated_customer['name']} بنجاح",
                    'customer_id': updated_customer['id'],
                    'parent_meter_id': updated_customer['parent_meter_id'],
                    'parent_display': parent_display  # الإضافة المطلوبة
                }
                
        except Exception as e:
            logger.error(f"خطأ في تحديث الزبون: {e}")
            return {
                'success': False,
                'error': f"فشل تحديث الزبون: {str(e)}"
            }


    def get_customers_list(self, filters: Dict = None) -> List[Dict]:
        """جلب قائمة الزبائن مع معلومات العلبة الأم"""
        try:
            with db.get_cursor() as cursor:
                query = """
                    SELECT 
                        c.id, c.name, c.phone_number, c.current_balance,
                        c.visa_balance, c.withdrawal_amount,
                        c.last_counter_reading, c.notes,
                        c.sector_id, c.box_number, c.serial_number,
                        c.telegram_username, c.is_active, c.meter_type,
                        c.parent_meter_id,
                        c.created_at, c.updated_at,
                        s.name as sector_name,
                        parent.name as parent_name,
                        parent.box_number as parent_box_number,
                        parent.meter_type as parent_meter_type
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    LEFT JOIN customers parent ON c.parent_meter_id = parent.id
                    WHERE 1=1
                """
                params = []
                
                # تطبيق الفلاتر
                if filters:
                    if filters.get('sector_id'):
                        query += " AND c.sector_id = %s"
                        params.append(filters['sector_id'])
                    
                    if filters.get('is_active') is not None:
                        query += " AND c.is_active = %s"
                        params.append(filters['is_active'])
                    
                    if filters.get('meter_type'):
                        query += " AND c.meter_type = %s"
                        params.append(filters['meter_type'])
                    
                    if filters.get('parent_meter_id'):
                        query += " AND c.parent_meter_id = %s"
                        params.append(filters['parent_meter_id'])
                
                query += " ORDER BY c.created_at DESC"
                
                cursor.execute(query, params)
                customers = cursor.fetchall()
                
                # معالجة البيانات وإضافة parent_display لكل زبون
                result = []
                for customer in customers:
                    customer_dict = dict(customer)
                    
                    # داخل loop الزبائن - الإضافة المطلوبة
                    parent_meter = customer.get('parent_name', '')
                    parent_box = customer.get('parent_box_number', '')
                    parent_type = customer.get('parent_meter_type', '')

                    # طرق عرض متعددة للعلبة الأم
                    if parent_box and parent_type and parent_meter:
                        parent_display = f"{parent_box} ({parent_type}) - {parent_meter}"
                    elif parent_box and parent_meter:
                        parent_display = f"{parent_box} - {parent_meter}"
                    elif parent_meter and parent_type:
                        parent_display = f"{parent_meter} ({parent_type})"
                    elif parent_meter:
                        parent_display = parent_meter
                    elif parent_box and parent_type:
                        parent_display = f"{parent_box} ({parent_type})"
                    elif parent_box:
                        parent_display = parent_box
                    else:
                        parent_display = ''
                    
                    customer_dict['parent_display'] = parent_display
                    result.append(customer_dict)
                
                return result
                
        except Exception as e:
            logger.error(f"خطأ في جلب قائمة الزبائن: {e}")
            return []
            

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
            field_names = {
                'name': 'الاسم',
                'phone_number': 'رقم الهاتف',
                'notes': 'ملاحظات',
                'box_number': 'رقم العلبة',
                'serial_number': 'رقم المسلسل',
                'meter_type': 'نوع العداد',
                'parent_meter_id': 'العلبة الأم'
            }
            
            for field in ['name', 'phone_number', 'notes', 'box_number', 'serial_number', 'meter_type']:
                old_val = old_data.get(field, '')
                new_val = new_data.get(field, '')
                
                if str(old_val).strip() != str(new_val).strip():
                    old_display = old_val if old_val else '(فارغ)'
                    new_display = new_val if new_val else '(فارغ)'
                    
                    changes.append(f"{field_names.get(field, field)}: {old_display} → {new_display}")
            
            # تسجيل تغيير parent_meter_id بشكل خاص
            old_parent = old_data.get('parent_meter_id')
            new_parent = new_data.get('parent_meter_id')
            
            if str(old_parent) != str(new_parent):
                old_parent_display = old_parent if old_parent else '(فارغ)'
                new_parent_display = new_parent if new_parent else '(فارغ)'
                changes.append(f"{field_names.get('parent_meter_id', 'العلبة الأم')}: {old_parent_display} → {new_parent_display}")
            
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
        """حذف الزبون مع التحقق من العلاقات الهرمية"""
        try:
            with db.get_cursor() as cursor:
                # جلب بيانات الزبون قبل الحذف
                cursor.execute("SELECT name, meter_type, parent_meter_id FROM customers WHERE id = %s", (customer_id,))
                customer = cursor.fetchone()
                
                if not customer:
                    return {'success': False, 'error': 'الزبون غير موجود'}
                
                customer_name = customer['name']
                meter_type = customer['meter_type']
                parent_meter_id = customer['parent_meter_id']
                
                # التحقق من وجود أبناء قبل الحذف
                if meter_type in ['مولدة', 'علبة توزيع', 'رئيسية']:
                    cursor.execute("""
                        SELECT COUNT(*) as child_count 
                        FROM customers 
                        WHERE parent_meter_id = %s AND is_active = TRUE
                    """, (customer_id,))
                    
                    child_result = cursor.fetchone()
                    if child_result and child_result['child_count'] > 0:
                        return {
                            'success': False,
                            'error': f"لا يمكن حذف {meter_type} '{customer_name}' لأنه يحتوي على {child_result['child_count']} عداد تابع. قم بحذف أو نقل العدادات التابعة أولاً."
                        }
                
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
                        f"حذف الزبون: {customer_name} ({'ناعم' if soft_delete else 'فعلي'}) - نوع: {meter_type}",
                        1  # user_id افتراضي
                    ))
                    
                    logger.info(f"تم حذف الزبون: {customer_name} - نوع: {meter_type}")
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


    def debug_customer_relationships(self, customer_id: int) -> Dict:
        """فحص وتشخيص علاقات الزبون"""
        try:
            with db.get_cursor() as cursor:
                # 1. جلب بيانات الزبون
                cursor.execute("""
                    SELECT c.*, p.name as parent_name, p.box_number as parent_box 
                    FROM customers c 
                    LEFT JOIN customers p ON c.parent_meter_id = p.id 
                    WHERE c.id = %s
                """, (customer_id,))
                
                customer = cursor.fetchone()
                
                if not customer:
                    return {'error': 'الزبون غير موجود'}
                
                # 2. جلب معلومات العلبة الأم
                parent_info = {}
                if customer['parent_meter_id']:
                    cursor.execute("""
                        SELECT id, name, box_number, meter_type 
                        FROM customers 
                        WHERE id = %s
                    """, (customer['parent_meter_id'],))
                    parent_info = cursor.fetchone()
                
                # 3. جلب الأبناء
                cursor.execute("""
                    SELECT COUNT(*) as children_count 
                    FROM customers 
                    WHERE parent_meter_id = %s
                """, (customer_id,))
                children = cursor.fetchone()
                
                return {
                    'success': True,
                    'customer_id': customer_id,
                    'customer_name': customer['name'],
                    'parent_meter_id': customer['parent_meter_id'],
                    'parent_exists': bool(parent_info),
                    'parent_info': parent_info,
                    'children_count': children['children_count'],
                    'raw_data': dict(customer)
                }
                
        except Exception as e:
            logger.error(f"خطأ في تشخيص علاقات الزبون: {e}")
            return {'error': str(e)}



    def get_customer_statistics(self) -> Dict:
        """الحصول على إحصائيات الزبائن مع تقسيم حسب نوع العداد"""
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
                
                # إحصائيات حسب نوع العداد
                cursor.execute("""
                    SELECT 
                        meter_type,
                        COUNT(*) as count,
                        SUM(current_balance) as total_balance
                    FROM customers 
                    WHERE is_active = TRUE
                    GROUP BY meter_type
                    ORDER BY 
                        CASE meter_type 
                            WHEN 'مولدة' THEN 1
                            WHEN 'علبة توزيع' THEN 2
                            WHEN 'رئيسية' THEN 3
                            WHEN 'زبون' THEN 4
                        END
                """)
                
                meter_type_stats = cursor.fetchall()
                
                return {
                    'total_customers': total_customers,
                    'negative_balance': negative_balance,
                    'positive_balance': positive_balance,
                    'zero_balance': zero_balance,
                    'negative_percentage': round((negative_balance / total_customers * 100), 2) if total_customers > 0 else 0,
                    'positive_percentage': round((positive_balance / total_customers * 100), 2) if total_customers > 0 else 0,
                    'meter_type_stats': [dict(row) for row in meter_type_stats]
                }
                
        except Exception as e:
            logger.error(f"خطأ في جلب إحصائيات الزبائن: {e}")
            return {}

    def get_customers_by_sector(self) -> Dict:
        """الحصول على توزيع الزبائن حسب القطاع مع أنواع العدادات"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT s.name as sector_name, 
                           COUNT(c.id) as customer_count,
                           SUM(c.current_balance) as total_balance,
                           COUNT(CASE WHEN c.meter_type = 'مولدة' THEN 1 END) as generator_count,
                           COUNT(CASE WHEN c.meter_type = 'علبة توزيع' THEN 1 END) as distribution_count,
                           COUNT(CASE WHEN c.meter_type = 'رئيسية' THEN 1 END) as main_count,
                           COUNT(CASE WHEN c.meter_type = 'زبون' THEN 1 END) as customer_count_type
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
        """حذف جميع الزبائن"""
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
                    SELECT id, name, meter_type FROM customers
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
                        f"حذف جماعي - الزبون: {customer['name']} (نوع: {customer['meter_type']})",
                        1  # user_id افتراضي
                    ))
                
                # حذف جميع الزبائن
                cursor.execute("DELETE FROM customers RETURNING id, name, meter_type")
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
                    SELECT id, name, meter_type FROM customers WHERE sector_id = %s
                """, (sector_id,))
                sector_customers = cursor.fetchall()
                
                # التحقق من وجود علاقات هرمية بين القطاعات المختلفة
                for customer in sector_customers:
                    cursor.execute("""
                        SELECT COUNT(*) as child_count 
                        FROM customers 
                        WHERE parent_meter_id = %s AND sector_id != %s
                    """, (customer['id'], sector_id))
                    
                    child_result = cursor.fetchone()
                    if child_result and child_result['child_count'] > 0:
                        return {
                            'success': False,
                            'error': f"لا يمكن حذف قطاع {sector['name']} لأن الزبون {customer['name']} له {child_result['child_count']} عداد تابع في قطاعات أخرى."
                        }
                
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
                        f"حذف قطاعي - القطاع: {sector['name']} - الزبون: {customer['name']} (نوع: {customer['meter_type']})",
                        1  # user_id افتراضي
                    ))
                
                # حذف زبائن القطاع
                cursor.execute("""
                    DELETE FROM customers 
                    WHERE sector_id = %s 
                    RETURNING id, name, meter_type
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

    # إضافة دوال التصنيف المالي إلى الكلاس

    """مدير عمليات الزبائن مع دعم التصنيفات المالية"""
    
    def update_financial_category(self, customer_id: int, category_data: Dict) -> Dict:
        """تحديث التصنيف المالي للزبون"""
        try:
            with db.get_cursor() as cursor:
                # جلب التصنيف الحالي
                cursor.execute("""
                    SELECT financial_category, free_amount, free_remaining,
                           vip_no_cut_days, vip_expiry_date
                    FROM customers WHERE id = %s
                """, (customer_id,))
                
                current = cursor.fetchone()
                if not current:
                    return {'success': False, 'error': 'الزبون غير موجود'}
                
                old_category = current['financial_category']
                new_category = category_data.get('financial_category', old_category)
                
                # التحقق من صحة البيانات
                if new_category not in ['normal', 'free', 'vip', 'free_vip']:
                    return {'success': False, 'error': 'تصنيف غير صالح'}
                
                # إعداد بيانات التحديث
                update_fields = []
                update_values = []
                
                # تحديث التصنيف الأساسي
                update_fields.append("financial_category = %s")
                update_values.append(new_category)
                
                # معالجة تفاصيل المجاني
                if 'free' in new_category:
                    free_reason = category_data.get('free_reason', '')
                    free_amount = float(category_data.get('free_amount', 0))
                    free_remaining = float(category_data.get('free_remaining', free_amount))
                    free_expiry_date = category_data.get('free_expiry_date')
                    
                    update_fields.extend([
                        "free_reason = %s",
                        "free_amount = %s",
                        "free_remaining = %s",
                        "free_expiry_date = %s"
                    ])
                    update_values.extend([
                        free_reason,
                        free_amount,
                        free_remaining,
                        free_expiry_date
                    ])
                else:
                    # إعادة تعيين قيم المجاني
                    update_fields.extend([
                        "free_reason = NULL",
                        "free_amount = 0",
                        "free_remaining = 0",
                        "free_expiry_date = NULL"
                    ])
                
                # معالجة تفاصيل VIP
                if 'vip' in new_category:
                    vip_reason = category_data.get('vip_reason', '')
                    vip_no_cut_days = int(category_data.get('vip_no_cut_days', 0))
                    vip_expiry_date = category_data.get('vip_expiry_date')
                    vip_grace_period = int(category_data.get('vip_grace_period', 0))
                    
                    update_fields.extend([
                        "vip_reason = %s",
                        "vip_no_cut_days = %s",
                        "vip_expiry_date = %s",
                        "vip_grace_period = %s"
                    ])
                    update_values.extend([
                        vip_reason,
                        vip_no_cut_days,
                        vip_expiry_date,
                        vip_grace_period
                    ])
                else:
                    # إعادة تعيين قيم VIP
                    update_fields.extend([
                        "vip_reason = NULL",
                        "vip_no_cut_days = 0",
                        "vip_expiry_date = NULL",
                        "vip_grace_period = 0"
                    ])
                
                # إضافة تاريخ التحديث
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                
                # تنفيذ التحديث
                query = f"UPDATE customers SET {', '.join(update_fields)} WHERE id = %s"
                update_values.append(customer_id)
                
                cursor.execute(query, tuple(update_values))
                
                # تسجيل التغيير في السجل
                cursor.execute("""
                    INSERT INTO customer_financial_logs 
                    (customer_id, old_category, new_category, category_type,
                     free_reason, free_amount, free_remaining, free_expiry_date,
                     vip_reason, vip_no_cut_days, vip_expiry_date, vip_grace_period,
                     changed_by, change_notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    customer_id, old_category, new_category,
                    'both' if new_category == 'free_vip' else new_category,
                    category_data.get('free_reason', ''),
                    category_data.get('free_amount', 0),
                    category_data.get('free_remaining', 0),
                    category_data.get('free_expiry_date'),
                    category_data.get('vip_reason', ''),
                    category_data.get('vip_no_cut_days', 0),
                    category_data.get('vip_expiry_date'),
                    category_data.get('vip_grace_period', 0),
                    category_data.get('user_id', 1),
                    category_data.get('change_notes', 'تحديث تصنيف مالي')
                ))
                
                # تسجيل في سجل النشاطات
                cursor.execute("""
                    INSERT INTO activity_logs (user_id, action_type, description)
                    VALUES (%s, 'update_financial_category', %s)
                """, (
                    category_data.get('user_id', 1),
                    f"تحديث التصنيف المالي للزبون {customer_id}: {old_category} -> {new_category}"
                ))
                
                logger.info(f"تم تحديث التصنيف المالي للزبون {customer_id} إلى {new_category}")
                return {
                    'success': True,
                    'message': f'تم تحديث التصنيف المالي إلى "{self.get_category_name(new_category)}"'
                }
                
        except Exception as e:
            logger.error(f"خطأ في تحديث التصنيف المالي: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_category_name(self, category_code: str) -> str:
        """تحويل رمز التصنيف إلى اسم عربي"""
        categories = {
            'normal': 'عادي',
            'free': 'مجاني',
            'vip': 'VIP',
            'free_vip': 'مجاني + VIP'
        }
        return categories.get(category_code, 'غير معروف')
    
    def consume_free_amount(self, customer_id: int, amount: float) -> Dict:
        """استهلاك من رصيد المجاني"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT free_remaining, financial_category
                    FROM customers 
                    WHERE id = %s AND financial_category IN ('free', 'free_vip')
                    FOR UPDATE
                """, (customer_id,))
                
                customer = cursor.fetchone()
                if not customer:
                    return {'success': False, 'error': 'الزبون ليس لديه تصنيف مجاني'}
                
                free_remaining = float(customer['free_remaining'] or 0)
                
                if free_remaining < amount:
                    return {
                        'success': False,
                        'error': f'الرصيد المتاح غير كافي ({free_remaining:,.0f})'
                    }
                
                # تحديث الرصيد المتبقي
                new_remaining = free_remaining - amount
                cursor.execute("""
                    UPDATE customers 
                    SET free_remaining = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (new_remaining, customer_id))
                
                # تسجيل الاستهلاك
                cursor.execute("""
                    INSERT INTO customer_financial_logs 
                    (customer_id, old_category, new_category, category_type,
                     free_amount, free_remaining, change_notes, changed_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    customer_id,
                    customer['financial_category'],
                    customer['financial_category'],
                    'free',
                    amount,
                    new_remaining,
                    f'استهلاك من رصيد المجاني: {amount:,.0f}',
                    1  # النظام
                ))
                
                return {
                    'success': True,
                    'free_remaining': new_remaining,
                    'consumed': amount,
                    'message': f'تم استهلاك {amount:,.0f} من رصيد المجاني'
                }
                
        except Exception as e:
            logger.error(f"خطأ في استهلاك رصيد المجاني: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_financial_logs(self, customer_id: int, limit: int = 50) -> List[Dict]:
        """جلب سجل التصنيفات المالية للزبون"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        fl.*,
                        u.full_name as changed_by_name,
                        u.username
                    FROM customer_financial_logs fl
                    LEFT JOIN users u ON fl.changed_by = u.id
                    WHERE fl.customer_id = %s
                    ORDER BY fl.created_at DESC
                    LIMIT %s
                """, (customer_id, limit))
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"خطأ في جلب سجل التصنيفات المالية: {e}")
            return []
    
    def get_customers_by_financial_category(self, category: str) -> List[Dict]:
        """جلب الزبائن حسب التصنيف المالي"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        c.*,
                        s.name as sector_name,
                        s.code as sector_code
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.financial_category = %s
                    AND c.is_active = TRUE
                    ORDER BY c.name
                """, (category,))
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"خطأ في جلب الزبائن حسب التصنيف: {e}")
            return []
    
    def check_vip_protection(self, customer_id: int) -> Dict:
        """التحقق من حماية الزبون VIP من القطع"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        vip_no_cut_days,
                        vip_expiry_date,
                        vip_grace_period,
                        financial_category
                    FROM customers 
                    WHERE id = %s
                """, (customer_id,))
                
                customer = cursor.fetchone()
                if not customer:
                    return {'is_vip': False}
                
                is_vip = 'vip' in customer['financial_category']
                
                if not is_vip:
                    return {'is_vip': False}
                
                # التحقق من صلاحية VIP
                expiry_date = customer['vip_expiry_date']
                is_active = True
                
                if expiry_date:
                    from datetime import date
                    is_active = date.today() <= expiry_date
                
                return {
                    'is_vip': True,
                    'active': is_active,
                    'no_cut_days': customer['vip_no_cut_days'],
                    'expiry_date': customer['vip_expiry_date'],
                    'grace_period': customer['vip_grace_period'],
                    'category': customer['financial_category']
                }
                
        except Exception as e:
            logger.error(f"خطأ في التحقق من حماية VIP: {e}")
            return {'is_vip': False}
    
    def get_meter_hierarchy(self, customer_id: int) -> Dict:
        """الحصول على الشجرة الهرمية للعداد"""
        try:
            with db.get_cursor() as cursor:
                # جلب الزبون الرئيسي
                cursor.execute("""
                    SELECT c.*, s.name as sector_name
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.id = %s
                """, (customer_id,))
                
                customer = cursor.fetchone()
                if not customer:
                    return None
                
                hierarchy = {
                    'customer': dict(customer),
                    'parent': None,
                    'children': []
                }
                
                # جلب العلبة الأم إذا وجدت
                if customer['parent_meter_id']:
                    cursor.execute("""
                        SELECT c.*, s.name as sector_name
                        FROM customers c
                        LEFT JOIN sectors s ON c.sector_id = s.id
                        WHERE c.id = %s
                    """, (customer['parent_meter_id'],))
                    
                    parent = cursor.fetchone()
                    if parent:
                        hierarchy['parent'] = dict(parent)
                
                # جلب الأبناء إذا كان هناك أبناء
                cursor.execute("""
                    SELECT c.*, s.name as sector_name
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.parent_meter_id = %s AND c.is_active = TRUE
                    ORDER BY c.meter_type, c.name
                """, (customer_id,))
                
                children = cursor.fetchall()
                hierarchy['children'] = [dict(child) for child in children]
                
                return hierarchy
                
        except Exception as e:
            logger.error(f"خطأ في جلب الشجرة الهرمية: {e}")
            return None


    def get_customer_hierarchy(self, sector_id: int = None) -> List[Dict]:
        """
        جلب جميع العدادات (زبائن، مولدة، علب توزيع، رئيسية) بترتيب هرمي (عمق أول)
        يطابق ترتيب عمود "المسار الهرمي" في تقرير Excel.
        """
        try:
            with db.get_cursor() as cursor:
                # استعلام عودي لبناء الشجرة والمسار
                query = """
                    WITH RECURSIVE customer_tree AS (
                        -- 1. العقد الجذرية (بدون أب)
                        SELECT 
                            c.id,
                            c.name,
                            c.meter_type,
                            c.financial_category,
                            c.visa_balance,
                            c.current_balance,
                            c.withdrawal_amount,
                            c.box_number,
                            c.serial_number,
                            c.phone_number,
                            c.parent_meter_id,
                            c.sector_id,
                            c.is_active,
                            s.name as sector_name,
                            0 AS level,
                            ARRAY[c.name]::VARCHAR[] AS path_names,
                            ARRAY[c.meter_type]::VARCHAR[] AS path_types
                        FROM customers c
                        LEFT JOIN sectors s ON c.sector_id = s.id
                        WHERE c.parent_meter_id IS NULL
                        AND c.is_active = TRUE
                        AND (c.sector_id = %s OR %s IS NULL)
                        
                        UNION ALL
                        
                        -- 2. الأبناء
                        SELECT 
                            c.id,
                            c.name,
                            c.meter_type,
                            c.financial_category,
                            c.visa_balance,
                            c.current_balance,
                            c.withdrawal_amount,
                            c.box_number,
                            c.serial_number,
                            c.phone_number,
                            c.parent_meter_id,
                            c.sector_id,
                            c.is_active,
                            s.name as sector_name,
                            ct.level + 1,
                            ct.path_names || c.name,
                            ct.path_types || c.meter_type
                        FROM customers c
                        INNER JOIN customer_tree ct ON c.parent_meter_id = ct.id
                        LEFT JOIN sectors s ON c.sector_id = s.id
                        WHERE c.is_active = TRUE
                    )
                    SELECT 
                        id,
                        name,
                        meter_type,
                        financial_category,
                        visa_balance,
                        current_balance,
                        withdrawal_amount,
                        box_number,
                        serial_number,
                        phone_number,
                        parent_meter_id,
                        sector_id,
                        sector_name,
                        is_active,
                        level,
                        path_names,
                        path_types,
                        array_to_string(path_names, ' ← ') as path_display
                    FROM customer_tree
                    ORDER BY path_names  -- ترتيب عمق أول (نفس ترتيب Excel)
                """
                cursor.execute(query, (sector_id, sector_id))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"خطأ في جلب التسلسل الهرمي: {e}")
            return []


    def get_customer_balance_by_sector(self) -> Dict:
        """
        حساب لنا وعلينا لكل قطاع بدقة عالية:
        - لنا: مجموع أرصدة العدادات من نوع زبون أو غير مصنف ورصيدهم سالب
        - علينا: مجموع أرصدة العدادات من نوع زبون أو غير مصنف ورصيدهم موجب
        فقط للزبائن النشطين وذوي sector_id صحيح
        """
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        s.name as sector_name,
                        s.id as sector_id,
                        COALESCE(SUM(CASE 
                            WHEN (c.meter_type IS NULL OR TRIM(c.meter_type) NOT IN ('مولدة', 'علبة توزيع', 'رئيسية')) 
                            AND c.current_balance < 0 
                            THEN ABS(c.current_balance)  -- القيمة المطلقة للرصيد السالب
                            ELSE 0 
                        END), 0) as lana_amount,
                        COALESCE(SUM(CASE 
                            WHEN (c.meter_type IS NULL OR TRIM(c.meter_type) NOT IN ('مولدة', 'علبة توزيع', 'رئيسية')) 
                            AND c.current_balance > 0 
                            THEN c.current_balance  -- الرصيد الموجب كما هو
                            ELSE 0 
                        END), 0) as alayna_amount,
                        COUNT(CASE 
                            WHEN (c.meter_type IS NULL OR TRIM(c.meter_type) NOT IN ('مولدة', 'علبة توزيع', 'رئيسية')) 
                            AND c.current_balance < 0 
                            THEN 1 
                        END) as lana_count,
                        COUNT(CASE 
                            WHEN (c.meter_type IS NULL OR TRIM(c.meter_type) NOT IN ('مولدة', 'علبة توزيع', 'رئيسية')) 
                            AND c.current_balance > 0 
                            THEN 1 
                        END) as alayna_count
                    FROM customers c
                    INNER JOIN sectors s ON c.sector_id = s.id
                    WHERE c.is_active = TRUE
                    GROUP BY s.id, s.name
                    ORDER BY s.name
                """)
                
                results = cursor.fetchall()
                
                # حساب الإجماليات
                total_lana_amount = sum(row['lana_amount'] or 0 for row in results)
                total_alayna_amount = sum(row['alayna_amount'] or 0 for row in results)
                total_lana_count = sum(row['lana_count'] or 0 for row in results)
                total_alayna_count = sum(row['alayna_count'] or 0 for row in results)
                
                return {
                    'sectors': [dict(row) for row in results],
                    'total_lana_amount': total_lana_amount,
                    'total_alayna_amount': total_alayna_amount,
                    'total_lana_count': total_lana_count,
                    'total_alayna_count': total_alayna_count
                }
                
        except Exception as e:
            logger.error(f"خطأ في حساب لنا وعلينا حسب القطاع: {e}")
            return {
                'sectors': [], 
                'total_lana_amount': 0, 
                'total_alayna_amount': 0,
                'total_lana_count': 0,
                'total_alayna_count': 0
            }

    def get_negative_balance_customers_advanced(
        self, 
        min_balance: float = None,
        max_balance: float = 0,
        exclude_categories: list = None,
        include_meter_types: list = None,
        sector_id: int = None,
        sort_by: str = "balance_desc"
    ) -> dict:
        """
        جلب الزبائن ذوي الرصيد السالب مع خيارات فلترة متقدمة
        
        :param min_balance: الحد الأدنى للرصيد (سالب)
        :param max_balance: الحد الأقصى للرصيد (سالب، الافتراضي 0)
        :param exclude_categories: قائمة التصنيفات المالية المستثناة
        :param include_meter_types: قائمة أنواع العدادات المطلوبة
        :param sector_id: رقم القطاع المحدد
        :param sort_by: طريقة الترتيب (balance_desc, balance_asc, name)
        :return: dict {sector_name: {customers: [], stats: {}}}
        """
        try:
            # القيم الافتراضية
            if min_balance is None:
                min_balance = -1000000
            
            if exclude_categories is None:
                exclude_categories = []
            
            if include_meter_types is None:
                include_meter_types = ["زبون"]
            
            with db.get_cursor() as cursor:
                query = """
                    SELECT 
                        s.name as sector_name,
                        c.id,
                        c.name,
                        c.box_number,
                        c.serial_number,
                        c.current_balance,
                        c.withdrawal_amount,
                        c.visa_balance,
                        c.financial_category,
                        c.phone_number,
                        c.meter_type,
                        c.last_counter_reading
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.is_active = TRUE
                    AND c.current_balance < 0
                    AND c.current_balance BETWEEN %s AND %s
                """
                
                params = [min_balance, max_balance]
                
                if sector_id:
                    query += " AND c.sector_id = %s"
                    params.append(sector_id)
                
                if exclude_categories:
                    placeholders = ', '.join(['%s'] * len(exclude_categories))
                    query += f" AND c.financial_category NOT IN ({placeholders})"
                    params.extend(exclude_categories)
                
                if include_meter_types:
                    placeholders = ', '.join(['%s'] * len(include_meter_types))
                    query += f" AND c.meter_type IN ({placeholders})"
                    params.extend(include_meter_types)
                
                # إضافة الترتيب
                if sort_by == "balance_desc":
                    query += " ORDER BY c.current_balance ASC"
                elif sort_by == "balance_asc":
                    query += " ORDER BY c.current_balance DESC"
                elif sort_by == "name":
                    query += " ORDER BY c.name"
                else:
                    query += " ORDER BY s.name, c.current_balance ASC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                sector_dict = {}
                for row in rows:
                    sector = row['sector_name'] or 'بدون قطاع'
                    if sector not in sector_dict:
                        sector_dict[sector] = {'customers': []}
                    
                    # حساب الرصيد الجديد
                    new_balance = row['current_balance']
                    withdrawal = row['withdrawal_amount'] or 0
                    visa = row['visa_balance'] or 0
                    calculated_new_balance = new_balance - withdrawal + visa
                    
                    customer_data = dict(row)
                    customer_data['calculated_new_balance'] = calculated_new_balance
                    sector_dict[sector]['customers'].append(customer_data)
                
                return sector_dict
                
        except Exception as e:
            logger.error(f"خطأ في جلب قوائم الكسر المتقدمة: {e}")
            return {}  
                
    def get_potential_children(self, parent_id: int) -> List[Dict]:
        """
        جلب قائمة الزبائن المحتملين ليكونوا أبناء لوالد معين.
        يتم تحديدهم حسب:
        - نفس القطاع
        - نوع العدد المسموح به حسب نوع الوالد
        - إظهار ما إذا كانوا أبناءً حاليين لهذا الوالد أم لا
        """
        try:
            with db.get_cursor() as cursor:
                # جلب معلومات الوالد (النوع والقطاع)
                cursor.execute("""
                    SELECT meter_type, sector_id FROM customers 
                    WHERE id = %s AND is_active = TRUE
                """, (parent_id,))
                parent = cursor.fetchone()
                if not parent:
                    return []
                
                parent_type = parent['meter_type']
                sector_id = parent['sector_id']
                
                # تحديد أنواع الأبناء المسموح بها
                allowed_child_types = []
                if parent_type == 'مولدة':
                    allowed_child_types = ['علبة توزيع', 'رئيسية', 'زبون']
                elif parent_type == 'علبة توزيع':
                    allowed_child_types = ['رئيسية', 'زبون']
                elif parent_type == 'رئيسية':
                    allowed_child_types = ['زبون']
                else:
                    return []  # الزبون لا يمكن أن يكون أباً
                
                # جلب جميع الزبائن في نفس القطاع من الأنواع المسموح بها
                cursor.execute("""
                    SELECT 
                        id, name, box_number, serial_number, meter_type,
                        current_balance, phone_number,
                        (parent_meter_id = %s) as is_current_child
                    FROM customers
                    WHERE sector_id = %s
                    AND meter_type = ANY(%s)
                    AND is_active = TRUE
                    AND id != %s  -- لا ندرج الوالد نفسه
                    ORDER BY 
                        box_number ASC NULLS LAST,
                        serial_number ASC NULLS LAST
                """, (parent_id, sector_id, allowed_child_types, parent_id))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"خطأ في جلب الأبناء المحتملين: {e}")
            return []

            
    def update_children(self, parent_id: int, child_ids: List[int], user_id: int) -> Dict:
        """
        تحديث أبناء والد معين:
        - تعيين parent_meter_id = parent_id لكل ابن في child_ids
        - إعادة تعيين parent_meter_id = NULL للأبناء الذين كانوا تابعين لهذا الوالد سابقاً ولم يعدوا في القائمة
        """
        try:
            with db.get_cursor() as cursor:
                # التحقق من وجود الوالد
                cursor.execute("SELECT meter_type, sector_id FROM customers WHERE id = %s AND is_active = TRUE", (parent_id,))
                parent = cursor.fetchone()
                if not parent:
                    return {'success': False, 'error': 'الوالد غير موجود'}
                
                # تحديد أنواع الأبناء المسموح بها (للتحقق)
                allowed_child_types = []
                if parent['meter_type'] == 'مولدة':
                    allowed_child_types = ['علبة توزيع', 'رئيسية', 'زبون']
                elif parent['meter_type'] == 'علبة توزيع':
                    allowed_child_types = ['رئيسية', 'زبون']
                elif parent['meter_type'] == 'رئيسية':
                    allowed_child_types = ['زبون']
                else:
                    return {'success': False, 'error': 'هذا النوع لا يمكن أن يكون أباً'}
                
                # 1. تحديث الأبناء المحددين (جدد أو قدامى)
                if child_ids:
                    # التحقق من أن جميع child_ids موجودة ومن نفس القطاع ومن الأنواع المسموحة
                    cursor.execute("""
                        SELECT id, meter_type FROM customers 
                        WHERE id = ANY(%s) AND sector_id = %s AND is_active = TRUE
                    """, (child_ids, parent['sector_id']))
                    valid_children = cursor.fetchall()
                    valid_ids = [c['id'] for c in valid_children]
                    
                    # التحقق من الأنواع
                    for child in valid_children:
                        if child['meter_type'] not in allowed_child_types:
                            return {
                                'success': False,
                                'error': f'الزبون {child["id"]} من نوع {child["meter_type"]} غير مسموح به لهذا الوالد'
                            }
                    
                    # تعيين parent_meter_id للقائمة
                    cursor.execute("""
                        UPDATE customers 
                        SET parent_meter_id = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ANY(%s)
                    """, (parent_id, valid_ids))
                    
                    # تسجيل العملية لكل ابن
                    for child_id in valid_ids:
                        cursor.execute("""
                            INSERT INTO customer_history 
                            (customer_id, action_type, transaction_type, 
                            details, notes, created_by, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        """, (
                            child_id,
                            'child_update',
                            'parent_change',
                            f'تم تعيين العداد {parent_id} كوالد',
                            f'تحديد كابن للوالد {parent_id}',
                            user_id
                        ))
                
                # 2. إزالة الأبناء السابقين الذين لم يعدوا في القائمة
                cursor.execute("""
                    UPDATE customers 
                    SET parent_meter_id = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE parent_meter_id = %s AND id != ALL(%s)
                """, (parent_id, child_ids if child_ids else [-1]))
                
                # تسجيل العملية للأبناء الذين تمت إزالتهم
                cursor.execute("""
                    SELECT id FROM customers 
                    WHERE parent_meter_id IS NULL AND updated_at = CURRENT_TIMESTAMP
                """)
                removed = cursor.fetchall()
                for child in removed:
                    cursor.execute("""
                        INSERT INTO customer_history 
                        (customer_id, action_type, transaction_type, 
                        details, notes, created_by, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, (
                        child['id'],
                        'child_update',
                        'parent_removed',
                        f'تم إزالة العلاقة مع الوالد {parent_id}',
                        'إزالة من الأبناء',
                        user_id
                    ))
                
                logger.info(f"تم تحديث أبناء الوالد {parent_id}: {len(child_ids)} ابن جديد، {len(removed)} تمت إزالتهم")
                return {
                    'success': True,
                    'message': f"تم تحديث الأبناء بنجاح: {len(child_ids)} ابن تمت إضافتهم/تأكيدهم، {len(removed)} تمت إزالتهم"
                }
                
        except Exception as e:
            logger.error(f"خطأ في تحديث الأبناء: {e}")
            return {'success': False, 'error': str(e)}                                