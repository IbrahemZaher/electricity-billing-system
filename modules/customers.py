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
        """تحديث بيانات الزبون"""
        try:
            # بناء الاستعلام الديناميكي
            set_clauses = []
            params = []
            
            for field, value in update_data.items():
                if field in ['name', 'box_number', 'serial_number', 'phone_number',
                           'current_balance', 'last_counter_reading', 'visa_balance',
                           'withdrawal_amount', 'notes', 'sector_id']:
                    set_clauses.append(f"{field} = %s")
                    params.append(value)
            
            if not set_clauses:
                return {'success': False, 'error': 'لا توجد بيانات للتحديث'}
            
            params.append(customer_id)
            
            query = f"""
                UPDATE customers 
                SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, name
            """
            
            with db.get_cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()
                
                if result:
                    logger.info(f"تم تحديث الزبون: {result['name']}")
                    return {
                        'success': True,
                        'message': f"تم تحديث الزبون {result['name']} بنجاح"
                    }
                else:
                    return {
                        'success': False,
                        'error': 'الزبون غير موجود'
                    }
                    
        except Exception as e:
            logger.error(f"خطأ في تحديث الزبون: {e}")
            return {
                'success': False,
                'error': f"فشل تحديث الزبون: {str(e)}"
            }
    
    def delete_customer(self, customer_id: int, soft_delete: bool = True) -> Dict:
        """حذف الزبون (حذف ناعم أو فعلي)"""
        try:
            with db.get_cursor() as cursor:
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
                    logger.info(f"تم حذف الزبون: {result['name']}")
                    return {
                        'success': True,
                        'message': f"تم حذف الزبون {result['name']} بنجاح"
                    }
                else:
                    return {
                        'success': False,
                        'error': 'الزبون غير موجود'
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