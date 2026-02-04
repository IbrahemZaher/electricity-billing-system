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
        
        # تأكد من هيكل الجدول عند بداية التشغيل
        self._ensure_permissions_table_structure()
    
    def _ensure_permissions_table_structure(self):
        """تأكد من هيكل جدول role_permissions"""
        try:
            with self.db.get_cursor() as cursor:
                # 1. تحقق من وجود الجدول
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = 'role_permissions'
                    )
                """)
                
                if not cursor.fetchone()['exists']:
                    logger.warning("❌ جدول role_permissions غير موجود!")
                    return
                
                # 2. تحقق من وجود القيد الفريد
                cursor.execute("""
                    SELECT con.conname, con.contype
                    FROM pg_constraint con
                    JOIN pg_class rel ON rel.oid = con.conrelid
                    WHERE rel.relname = 'role_permissions'
                    AND con.contype = 'u'
                    AND array_length(con.conkey, 1) = 2
                    AND con.conkey::text LIKE '%1,2%'  -- الأعمدة role و permission_key
                """)
                
                constraints = cursor.fetchall()
                
                if not constraints:
                    logger.warning("⚠️ لا يوجد قيد فريد على (role, permission_key).")
                    logger.warning("⚠️ هذا قد يسبب مشاكل في حفظ التعديلات.")
                else:
                    logger.info(f"✅ يوجد قيد فريد: {constraints[0]['conname']}")
                    
        except Exception as e:
            logger.error(f"❌ خطأ في التحقق من هيكل الجدول: {e}")
    
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
                    return None
                
                # الاستعلام الرئيسي: يجمع الصلاحيات من الأدوار والتجاوزات
                cursor.execute("""
                    WITH user_role AS (
                        SELECT role FROM users WHERE id = %s
                    ),
                    role_perms AS (
                        -- صلاحيات الدور (بما فيها *.*)
                        SELECT permission_key, is_allowed
                        FROM role_permissions
                        WHERE role = (SELECT role FROM users WHERE id = %s)
                        AND (permission_key = %s OR permission_key = '*.*')
                    ),
                    user_perms AS (
                        -- صلاحيات المستخدم المباشرة
                        SELECT permission_key, is_allowed
                        FROM user_permissions
                        WHERE user_id = %s AND permission_key = %s
                    )
                    SELECT
                        CASE
                            -- أولاً: إذا كان هناك *.* مفعل للدور، يمنح كل الصلاحيات
                            WHEN EXISTS (SELECT 1 FROM role_perms WHERE permission_key = '*.*' AND is_allowed = TRUE) THEN TRUE
                            -- ثانياً: إذا كان هناك *.* معطل للدور، يمنع كل الصلاحيات
                            WHEN EXISTS (SELECT 1 FROM role_perms WHERE permission_key = '*.*' AND is_allowed = FALSE) THEN FALSE
                            -- ثالثاً: صلاحية المستخدم المباشرة (تجاوز)
                            WHEN EXISTS (SELECT 1 FROM user_perms) THEN (
                                SELECT is_allowed FROM user_perms LIMIT 1
                            )
                            -- رابعاً: صلاحية الدور المحددة
                            WHEN EXISTS (SELECT 1 FROM role_perms WHERE permission_key = %s) THEN (
                                SELECT is_allowed FROM role_perms WHERE permission_key = %s LIMIT 1
                            )
                            -- أخيراً: لا توجد صلاحية
                            ELSE FALSE
                        END as final_permission
                """, (user_id, user_id, permission_key, user_id, permission_key, permission_key, permission_key))
                
                result = cursor.fetchone()
                final_result = result['final_permission'] if result else False
                
                # تسجيل النتيجة للتحقق
                logger.debug(f"النظام الجديد - صلاحية {permission_key} للمستخدم {user_id}: {final_result}")
                return final_result
                    
        except Exception as e:
            logger.error(f"خطأ في النظام الجديد: {e}", exc_info=True)
            return None
                    
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
            # 2. النظام الجديد مع التصحيح
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT
                        pc.permission_key,
                        CASE
                            WHEN ur.role = 'admin' THEN TRUE
                            WHEN rp.permission_key = '*.*' AND rp.is_allowed = TRUE THEN TRUE
                            WHEN rp.permission_key = '*.*' AND rp.is_allowed = FALSE THEN FALSE
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
    
    def get_role_permissions_timestamp(self, role: str) -> int:
        """الحصول على آخر وقت تحديث لصلاحيات دور معين"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT MAX(updated_at) as last_update
                    FROM role_permissions
                    WHERE role = %s
                """, (role,))
                
                result = cursor.fetchone()
                if result and result['last_update']:
                    return int(result['last_update'].timestamp())
                return 0
        except Exception as e:
            logger.error(f"خطأ في جلب وقت تحديث صلاحيات الدور: {e}")
            return 0
    
    def get_role_permissions_version(self, role: str) -> int:
        """الحصول على إصدار صلاحيات الدور (للكشف عن التغييرات)"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT MAX(id) as max_id, COUNT(*) as perm_count
                    FROM role_permissions
                    WHERE role = %s
                """, (role,))
                
                result = cursor.fetchone()
                return (result['max_id'] or 0) + (result['perm_count'] or 0)
        except Exception as e:
            logger.error(f"خطأ في جلب إصدار صلاحيات الدور: {e}")
            return 0
    
    def invalidate_role_cache(self, role: str):
        """إبطال كاش جميع المستخدمين الذين لديهم دور معين"""
        try:
            with self.db.get_cursor() as cursor:
                # جلب جميع مستخدمي هذا الدور
                cursor.execute("SELECT id FROM users WHERE role = %s", (role,))
                users = cursor.fetchall()
                
                # مسح كاش كل مستخدم
                for user in users:
                    self.clear_cache(user['id'])
                
                logger.info(f"🗑️ تم إبطال كاش {len(users)} مستخدم للدور {role}")
                return len(users)
        except Exception as e:
            logger.error(f"خطأ في إبطال كاش الدور: {e}")
            return 0
    
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
        """تحديث صلاحية دور مع تحديث الجلسات - طريقة مضمونة 100%"""
        try:
            with self.db.get_cursor() as cursor:
                # 1. تسجيل محاولة التحديث
                logger.info(f"🚀 بدء تحديث: {role}.{permission_key} = {is_allowed}")
                
                # 2. استعلام بسيط جداً: حذف القديم وأدخل الجديد
                # هذا يحل مشكلة عدم وجود قيد فريد
                cursor.execute("""
                    -- أولاً: حذف أي صفوف قديمة
                    DELETE FROM role_permissions 
                    WHERE role = %s AND permission_key = %s
                """, (role, permission_key))
                
                # 3. إدراج الصف الجديد
                cursor.execute("""
                    INSERT INTO role_permissions (role, permission_key, is_allowed, created_at, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id, is_allowed, updated_at
                """, (role, permission_key, is_allowed))
                
                result = cursor.fetchone()
                
                if result:
                    logger.info(f"✅ تم الحفظ بنجاح! ID: {result['id']}, القيمة: {result['is_allowed']}")
                    
                    # 4. التحقق المباشر من قاعدة البيانات
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM role_permissions 
                        WHERE role = %s AND permission_key = %s AND is_allowed = %s
                    """, (role, permission_key, is_allowed))
                    
                    verify = cursor.fetchone()
                    logger.info(f"🔍 التحقق: يوجد {verify['count']} صف مطابق في قاعدة البيانات")
                    
                    # 5. مسح الكاش
                    self.clear_cache()
                    affected_users = self.invalidate_role_cache(role)
                    
                    # 6. تسجيل النجاح
                    logger.info(f"🎉 تم تحديث صلاحية {permission_key} للدور {role} إلى {is_allowed}")
                    return True
                else:
                    logger.error("❌ فشل الإدراج - لم يتم إرجاع أي نتيجة")
                    return False
                    
        except Exception as e:
            logger.error(f"💥 خطأ في تحديث صلاحية الدور: {e}", exc_info=True)
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

    def check_database_directly(self, role: str, permission_key: str):
        """فحص مباشر لقاعدة البيانات - يعرض كل شيء"""
        try:
            with self.db.get_cursor() as cursor:
                # 1. تحقق من جدول role_permissions
                cursor.execute("""
                    SELECT id, is_allowed, created_at, updated_at 
                    FROM role_permissions 
                    WHERE role = %s AND permission_key = %s
                    ORDER BY updated_at DESC
                """, (role, permission_key))
                
                role_perms = cursor.fetchall()
                
                # 2. تحقق من جدول permissions_catalog
                cursor.execute("""
                    SELECT permission_key, name, category 
                    FROM permissions_catalog 
                    WHERE permission_key = %s
                """, (permission_key,))
                
                catalog_info = cursor.fetchone()
                
                # 3. عرض النتائج
                print("\n" + "="*60)
                print(f"🔍 فحص مباشر لقاعدة البيانات:")
                print(f"   الدور: {role}")
                print(f"   الصلاحية: {permission_key}")
                print("="*60)
                
                if catalog_info:
                    print(f"📋 معلومات من permissions_catalog:")
                    print(f"   الاسم: {catalog_info['name']}")
                    print(f"   الفئة: {catalog_info['category']}")
                else:
                    print("❌ هذه الصلاحية غير موجودة في permissions_catalog!")
                
                print(f"\n📊 سجلات في role_permissions: {len(role_perms)}")
                
                for i, perm in enumerate(role_perms, 1):
                    status = "✅ مفعل" if perm['is_allowed'] else "❌ معطل"
                    print(f"\n   السجل #{i}:")
                    print(f"   ID: {perm['id']}")
                    print(f"   الحالة: {status}")
                    print(f"   أنشئ في: {perm['created_at']}")
                    print(f"   آخر تحديث: {perm['updated_at']}")
                
                if not role_perms:
                    print("\n⚠️ لا يوجد أي سجل في role_permissions لهذه الصلاحية!")
                
                print("="*60 + "\n")
                
        except Exception as e:
            print(f"💥 خطأ في الفحص: {e}")

# إنشاء كائن عالمي
permission_engine = PermissionEngine()