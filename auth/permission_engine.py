# auth/permission_engine.py
"""
المحرك المركزي لإدارة الصلاحيات
يعمل بنظام هجين:
1. يتحقق من الجداول الجديدة أولاً (permissions_catalog)
2. يعود للنظام القديم للتوافق
"""

from database.connection import db
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class PermissionEngine:
    """محرك الصلاحيات المركزي"""
    
    def __init__(self):
        self.db = db
        
    def has_permission(self, user_id: int, permission_key: str) -> bool:
        """
        التحقق من صلاحية المستخدم
        
        Args:
            user_id: معرف المستخدم
            permission_key: مفتاح الصلاحية (مثل 'customers.view')
            
        Returns:
            bool: True إذا كان لديه الصلاحية، False إذا لم يكن
        """
        # الحل السريع: إذا كان admin، أعطيه كل الصلاحيات
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                if user and user['role'] == 'admin':
                    logger.debug(f"المستخدم {user_id} هو admin، لديه كل الصلاحيات")
                    return True  # المسؤول لديه كل الصلاحيات!
        except Exception as e:
            logger.warning(f"خطأ في التحقق من دور المستخدم: {e}")
            # نتابع بالطرق الأخرى إذا فشل الاستعلام
        
        # 1. أولاً: النظام الجديد (الجداول)
        result = self._check_new_system(user_id, permission_key)
        
        # 2. إذا كان هناك نتيجة محددة (True/False)، نرجعها
        if result is not None:
            return result
        
        # 3. أخيراً: النظام القديم (للتوافق)
        return self._check_old_system(user_id, permission_key)

    def _check_new_system(self, user_id: int, permission_key: str) -> Optional[bool]:
        """
        التحقق من النظام الجديد (الجداول)
        
        Returns:
            bool or None: True/False إذا كان النظام موجوداً، None إذا لم يكن
        """
        try:
            with self.db.get_cursor() as cursor:
                # التحقق من وجود الجداول أولاً
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = 'permissions_catalog'
                    )
                """)
                
                if not cursor.fetchone()['exists']:
                    logger.debug("الجداول الجديدة غير موجودة بعد")
                    return None  # الجداول غير موجودة
                
                # الاستعلام الرئيسي: يجمع الصلاحيات من الأدوار والتجاوزات
                cursor.execute("""
                    WITH user_role AS (
                        SELECT role FROM users WHERE id = %s
                    ),
                    all_permissions AS (
                        -- صلاحية *.* (جميع الصلاحيات)
                        SELECT 
                            CASE 
                                WHEN rp.permission_key = '*.*' THEN TRUE
                                ELSE COALESCE(up.is_allowed, rp.is_allowed)
                            END as has_permission
                        FROM user_role ur
                        LEFT JOIN role_permissions rp ON ur.role = rp.role 
                            AND (rp.permission_key = %s OR rp.permission_key = '*.*')
                        LEFT JOIN user_permissions up ON up.user_id = %s 
                            AND up.permission_key = %s
                    )
                    SELECT 
                        CASE 
                            WHEN COUNT(*) = 0 THEN FALSE
                            WHEN BOOL_OR(has_permission) THEN TRUE
                            ELSE FALSE
                        END as final_permission
                    FROM all_permissions
                """, (user_id, permission_key, user_id, permission_key))
                
                result = cursor.fetchone()
                return result['final_permission'] if result else False
                
        except Exception as e:
            logger.error(f"خطأ في النظام الجديد: {e}", exc_info=True)
            return None  # حدث خطأ، نرجع للنظام القديم
    
    def _check_old_system(self, user_id: int, permission_key: str) -> bool:
        """
        النظام القديم (للتوافق المؤقت)
        
        يعتمد على:
        1. دور 'admin' له كل الصلاحيات
        2. الصلاحيات المخزنة في users.permissions (JSONB)
        3. التحقق المباشر من الدور
        """
        try:
            with self.db.get_cursor() as cursor:
                # جلب بيانات المستخدم
                cursor.execute("""
                    SELECT role, permissions 
                    FROM users 
                    WHERE id = %s
                """, (user_id,))
                
                user = cursor.fetchone()
                if not user:
                    logger.warning(f"المستخدم {user_id} غير موجود")
                    return False
                
                # 1. إذا كان admin
                if user['role'] == 'admin':
                    logger.debug(f"المستخدم {user_id} هو admin، لديه كل الصلاحيات")
                    return True
                
                # 2. التحقق من JSONB القديم
                permissions = user.get('permissions', {})
                
                # إذا كان 'all': true
                if permissions.get('all'):
                    logger.debug(f"المستخدم {user_id} لديه 'all': true في permissions القديمة")
                    return True
                
                # التحقق من الصلاحية المحددة
                if permission_key in permissions:
                    result = permissions[permission_key]
                    logger.debug(f"المستخدم {user_id} لديه الصلاحية {permission_key}: {result} في النظام القديم")
                    return bool(result)
                
                # 3. التحقق من الأدوار التقليدية
                role_permissions_map = {
                    'accountant': [
                        'customers.view', 'invoices.view', 'invoices.create',
                        'reports.view', 'system.import_data'
                    ],
                    'cashier': [
                        'customers.view', 'invoices.view', 'invoices.create',
                        'accounting.access'
                    ],
                    'viewer': [
                        'customers.view', 'reports.view'
                    ]
                }
                
                user_role_permissions = role_permissions_map.get(user['role'], [])
                has_permission = permission_key in user_role_permissions
                
                logger.debug(f"المستخدم {user_id} (دور: {user['role']}) - الصلاحية {permission_key}: {has_permission} في النظام القديم")
                return has_permission
                
        except Exception as e:
            logger.error(f"خطأ في النظام القديم: {e}", exc_info=True)
            return False
    
    def get_user_permissions(self, user_id: int) -> Dict[str, bool]:
        """
        الحصول على جميع صلاحيات المستخدم
        
        Returns:
            dict: {permission_key: True/False}
        """
        permissions = {}
        
        try:
            # أولاً: النظام الجديد
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        pc.permission_key,
                        CASE 
                            WHEN ur.role = 'admin' THEN TRUE
                            WHEN rp.permission_key = '*.*' THEN TRUE
                            ELSE COALESCE(up.is_allowed, rp.is_allowed, FALSE)
                        END as has_permission
                    FROM permissions_catalog pc
                    CROSS JOIN (SELECT role FROM users WHERE id = %s) ur
                    LEFT JOIN role_permissions rp ON ur.role = rp.role 
                        AND (rp.permission_key = pc.permission_key OR rp.permission_key = '*.*')
                    LEFT JOIN user_permissions up ON up.user_id = %s 
                        AND up.permission_key = pc.permission_key
                    WHERE pc.is_active = TRUE
                    ORDER BY pc.category, pc.permission_key
                """, (user_id, user_id))
                
                for row in cursor.fetchall():
                    permissions[row['permission_key']] = row['has_permission']
                
        except Exception as e:
            logger.error(f"خطأ في جلب صلاحيات المستخدم: {e}")
            # إذا فشل النظام الجديد، نستخدم القديم للصلاحيات الأساسية
        
        return permissions
    
    def get_all_permissions(self) -> List[Dict[str, Any]]:
        """الحصول على جميع الصلاحيات في الكتالوج"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT permission_key, name, description, category, is_active
                    FROM permissions_catalog
                    ORDER BY category, permission_key
                """)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"خطأ في جلب جميع الصلاحيات: {e}")
            return []
    
    def update_role_permission(self, role: str, permission_key: str, is_allowed: bool) -> bool:
        """تحديث صلاحية دور"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO role_permissions (role, permission_key, is_allowed)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (role, permission_key) DO UPDATE
                    SET is_allowed = EXCLUDED.is_allowed,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, (role, permission_key, is_allowed))
                
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"خطأ في تحديث صلاحية الدور: {e}")
            return False
    
    def update_user_permission(self, user_id: int, permission_key: str, is_allowed: bool) -> bool:
        """تحديث صلاحية مستخدم (تجاوز)"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_permissions (user_id, permission_key, is_allowed)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, permission_key) DO UPDATE
                    SET is_allowed = EXCLUDED.is_allowed,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, (user_id, permission_key, is_allowed))
                
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"خطأ في تحديث صلاحية المستخدم: {e}")
            return False

# إنشاء كائن عالمي
permission_engine = PermissionEngine()