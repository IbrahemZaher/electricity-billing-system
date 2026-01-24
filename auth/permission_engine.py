# auth/permission_engine.py
"""
المحرك المركزي لإدارة الصلاحيات
يعمل بنظام هجين:
1. يتحقق من الجداول الجديدة أولاً (permissions_catalog)
2. يعود للنظام القديم للتوافق
"""

from database.connection import db
import logging
import time
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class PermissionEngine:
    """محرك الصلاحيات المركزي"""
    
    def __init__(self):
        self.db = db
        self._permissions_cache = {}  # user_id -> (timestamp, permissions_dict)
        self._cache_ttl = 30  # seconds
        
    def has_permission(self, user_id: int, permission_key: str, user_role: str | None = None) -> bool:
        """
        التحقق من صلاحية المستخدم
        
        Args:
            user_id: معرف المستخدم
            permission_key: مفتاح الصلاحية (مثل 'customers.view')
            user_role: دور المستخدم (اختياري) لتجنب استعلام إضافي
            
        Returns:
            bool: True إذا كان لديه الصلاحية، False إذا لم يكن
        """
        # 1. اختصار للمسؤولين - إذا تم تمرير الدور أو جلب من الكاش
        if user_role == 'admin':
            logger.debug(f"تم تمرير role=admin للمستخدم {user_id} → صلاحيات كاملة (shortcut)")
            return True
        
        # 2. إذا لم يتم تمرير الدور، نحاول الحصول عليه من الكاش أولاً
        if user_role is None:
            cached = self._permissions_cache.get(user_id)
            if cached and (time.time() - cached[0]) < self._cache_ttl:
                cached_role = cached[1].get('_role')
                if cached_role == 'admin':
                    logger.debug(f"المستخدم {user_id} في الكاش هو admin، لديه كل الصلاحيات")
                    return True
                user_role = cached_role
            
        # 3. إذا لم يكن الدور في الكاش، نجلب من قاعدة البيانات
        if user_role is None:
            try:
                with self.db.get_cursor() as cursor:
                    cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
                    user = cursor.fetchone()
                    if user and user.get('role') == 'admin':
                        logger.debug(f"المستخدم {user_id} في DB هو admin، لديه كل الصلاحيات")
                        return True
                    user_role = user.get('role') if user else None
            except Exception as e:
                logger.warning(f"خطأ في التحقق من دور المستخدم: {e}")
                # نتابع بالطرق الأخرى إذا فشل الاستعلام
        
        # 4. أولاً: النظام الجديد (الجداول)
        result = self._check_new_system(user_id, permission_key, user_role)
        
        # 5. إذا كان هناك نتيجة محددة (True/False)، نرجعها
        if result is not None:
            return result
        
        # 6. أخيراً: النظام القديم (للتوافق)
        return self._check_old_system(user_id, permission_key, user_role)

    def _check_new_system(self, user_id: int, permission_key: str, user_role: str | None) -> Optional[bool]:
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
    
    def _check_old_system(self, user_id: int, permission_key: str, user_role: str | None) -> bool:
        """
        النظام القديم (للتوافق المؤقت)
        
        يعتمد على:
        1. دور 'admin' له كل الصلاحيات
        2. الصلاحيات المخزنة في users.permissions (JSONB)
        3. التحقق المباشر من الدور
        """
        try:
            with self.db.get_cursor() as cursor:
                # جلب بيانات المستخدم (إذا لم نكن نعرف الدور بالفعل)
                if user_role is None:
                    cursor.execute("""
                        SELECT role, permissions 
                        FROM users 
                        WHERE id = %s
                    """, (user_id,))
                    user = cursor.fetchone()
                    if not user:
                        logger.warning(f"المستخدم {user_id} غير موجود")
                        return False
                    user_role = user.get('role')
                    permissions = user.get('permissions', {})
                else:
                    # إذا كان الدور معروفاً، نحتاج فقط permissions
                    cursor.execute("SELECT permissions FROM users WHERE id = %s", (user_id,))
                    user = cursor.fetchone()
                    permissions = user.get('permissions', {}) if user else {}
                
                # 1. إذا كان admin
                if user_role == 'admin':
                    logger.debug(f"المستخدم {user_id} هو admin، لديه كل الصلاحيات")
                    return True
                
                # 2. التحقق من JSONB القديم
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
                
                user_role_permissions = role_permissions_map.get(user_role, [])
                has_permission = permission_key in user_role_permissions
                
                logger.debug(f"المستخدم {user_id} (دور: {user_role}) - الصلاحية {permission_key}: {has_permission} في النظام القديم")
                return has_permission
                
        except Exception as e:
            logger.error(f"خطأ في النظام القديم: {e}", exc_info=True)
            return False
    
    def _get_user_permissions_old(self, user_id: int) -> Dict[str, bool]:
        """
        الحصول على صلاحيات المستخدم من النظام القديم
        
        Returns:
            dict: {permission_key: True/False}
        """
        permissions = {}
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT role, permissions FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                if not user:
                    return {}
                
                # تحميل صلاحيات JSON إذا وجدت
                user_permissions = user.get('permissions', {})
                if isinstance(user_permissions, dict):
                    permissions.update(user_permissions)
                
                # إضافة الصلاحيات الافتراضية للدور
                role = user.get('role')
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
                
                for perm in role_permissions_map.get(role, []):
                    permissions.setdefault(perm, True)
                
                # إضافة الدور كحقل خاص للمساعدة في الكاش
                permissions['_role'] = role
                
        except Exception as e:
            logger.error(f"خطأ في جلب صلاحيات النظام القديم: {e}")
        
        return permissions
    
    def get_user_permissions(self, user_id: int) -> Dict[str, bool]:
        """
        الحصول على جميع صلاحيات المستخدم
        
        Returns:
            dict: {permission_key: True/False}
        """
        # 1. التحقق من الكاش أولاً
        cached = self._permissions_cache.get(user_id)
        if cached and (time.time() - cached[0]) < self._cache_ttl:
            logger.debug(f"استخدام صلاحيات الكاش للمستخدم {user_id}")
            return cached[1]
        
        permissions = {}
        
        try:
            # 2. أولاً: النظام الجديد
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
                
                # إذا كان هناك نتائج، نضيف الدور
                if permissions:
                    cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
                    user = cursor.fetchone()
                    if user:
                        permissions['_role'] = user.get('role')
                
        except Exception as e:
            logger.error(f"خطأ في جلب صلاحيات النظام الجديد: {e}")
            # نستخدم النظام القديم كـ fallback
            permissions = self._get_user_permissions_old(user_id)
        
        # 3. إذا كانت الصلاحيات فارغة أو النظام الجديد لم يعط نتائج، نستخدم النظام القديم
        if not permissions:
            permissions = self._get_user_permissions_old(user_id)
        
        # 4. تخزين في الكاش
        self._permissions_cache[user_id] = (time.time(), permissions)
        logger.debug(f"تم تخزين صلاحيات المستخدم {user_id} في الكاش ({len(permissions)} صلاحية)")
        
        return permissions
    
    def clear_cache(self, user_id: int | None = None):
        """مسح الكاش إما لمستخدم محدد أو الكل"""
        if user_id is None:
            self._permissions_cache.clear()
            logger.debug("تم مسح كل الكاش")
        elif user_id in self._permissions_cache:
            del self._permissions_cache[user_id]
            logger.debug(f"تم مسح الكاش للمستخدم {user_id}")
    
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
                
                # مسح الكاش لأن الصلاحيات تغيرت
                self.clear_cache()
                
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
                
                # مسح كاش المستخدم المحدد
                self.clear_cache(user_id)
                
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"خطأ في تحديث صلاحية المستخدم: {e}")
            return False

# إنشاء كائن عالمي
permission_engine = PermissionEngine()