# scripts/migrate_permissions.py
"""
سكربت ترحيل الصلاحيات من النظام القديم إلى الجديد
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_permissions():
    """ترحيل الصلاحيات"""
    try:
        with db.get_cursor() as cursor:
            logger.info("بدء ترحيل الصلاحيات...")
            
            # 1. التحقق من وجود الجداول القديمة
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'permissions'
            """)
            
            if not cursor.fetchone():
                logger.info("لا توجد صلاحيات قديمة لترحيلها")
                return
            
            # 2. جلب جميع المستخدمين
            cursor.execute("""
                SELECT id, role, permissions 
                FROM users 
                WHERE permissions IS NOT NULL 
                AND permissions != '{}'
            """)
            
            users = cursor.fetchall()
            logger.info(f"تم العثور على {len(users)} مستخدم لديهم صلاحيات قديمة")
            
            # 3. تعيين الصلاحيات لكل مستخدم
            for user in users:
                user_id = user['id']
                user_role = user['role']
                old_permissions = user['permissions']
                
                # إذا كان admin، نعطيه كل الصلاحيات
                if user_role == 'admin':
                    cursor.execute("""
                        INSERT INTO user_permissions (user_id, permission_key, is_allowed)
                        SELECT %s, permission_key, TRUE
                        FROM permissions_catalog
                        ON CONFLICT (user_id, permission_key) DO NOTHING
                    """, (user_id,))
                    logger.debug(f"المستخدم {user_id} (admin): منح جميع الصلاحيات")
                    continue
                
                # تحويل الصلاحيات القديمة إلى الجديدة
                if old_permissions.get('all'):
                    # منح جميع الصلاحيات للدور
                    cursor.execute("""
                        INSERT INTO user_permissions (user_id, permission_key, is_allowed)
                        SELECT %s, rp.permission_key, TRUE
                        FROM role_permissions rp
                        WHERE rp.role = %s
                        ON CONFLICT (user_id, permission_key) DO NOTHING
                    """, (user_id, user_role))
                    logger.debug(f"المستخدم {user_id}: منح جميع صلاحيات الدور {user_role}")
                
                # معالجة الصلاحيات الفردية
                for old_key, value in old_permissions.items():
                    if old_key == 'all':
                        continue
                    
                    # محاولة التعرف على الصلاحية القديمة
                    new_key = map_old_permission(old_key)
                    if new_key:
                        cursor.execute("""
                            INSERT INTO user_permissions (user_id, permission_key, is_allowed)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (user_id, permission_key) DO UPDATE
                            SET is_allowed = EXCLUDED.is_allowed
                        """, (user_id, new_key, bool(value)))
                        logger.debug(f"المستخدم {user_id}: {old_key} -> {new_key} = {value}")
            
            logger.info("✅ تم ترحيل الصلاحيات بنجاح!")
            
    except Exception as e:
        logger.error(f"خطأ في ترحيل الصلاحيات: {e}", exc_info=True)
        raise

def map_old_permission(old_key):
    """تعيين الصلاحيات القديمة إلى الجديدة"""
    mapping = {
        'view_customers': 'customers.view',
        'create_bills': 'invoices.create',
        'edit_bills': 'invoices.edit',
        'view_reports': 'reports.view',
        'manage_users': 'system.manage_users'
    }
    return mapping.get(old_key, old_key)

if __name__ == "__main__":
    migrate_permissions()