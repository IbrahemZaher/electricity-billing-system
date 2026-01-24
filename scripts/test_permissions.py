# scripts/test_permissions.py
"""
سكربت اختبار نظام الصلاحيات الجديد
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.permission_engine import permission_engine
from database.connection import db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_permission_system():
    """اختبار نظام الصلاحيات"""
    logger.info("🚀 بدء اختبار نظام الصلاحيات...")
    
    try:
        with db.get_cursor() as cursor:
            # اختبار 1: التحقق من وجود الجداول
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name IN ('permissions_catalog', 'role_permissions', 'user_permissions')
            """)
            
            tables = cursor.fetchall()
            logger.info(f"✅ الجداول الموجودة: {[t['table_name'] for t in tables]}")
            
            # اختبار 2: عد الصلاحيات
            cursor.execute("SELECT COUNT(*) as count FROM permissions_catalog")
            perm_count = cursor.fetchone()['count']
            logger.info(f"✅ عدد الصلاحيات في الكتالوج: {perm_count}")
            
            # اختبار 3: عد الأدوار
            cursor.execute("SELECT DISTINCT role FROM role_permissions")
            roles = [r['role'] for r in cursor.fetchall()]
            logger.info(f"✅ الأدوار الموجودة: {roles}")
            
            # اختبار 4: جلب مستخدم للاختبار
            cursor.execute("SELECT id, username, role FROM users LIMIT 3")
            test_users = cursor.fetchall()
            
            for user in test_users:
                logger.info(f"\n🔍 اختبار المستخدم: {user['username']} (دور: {user['role']})")
                
                # اختبار صلاحيات أساسية
                test_permissions = [
                    'customers.view',
                    'invoices.create',
                    'system.manage_users',
                    'settings.manage'
                ]
                
                for perm in test_permissions:
                    has_perm = permission_engine.has_permission(user['id'], perm)
                    status = "✅" if has_perm else "❌"
                    logger.info(f"  {status} {perm}: {has_perm}")
            
            logger.info("\n🎉 جميع الاختبارات اكتملت بنجاح!")
            
    except Exception as e:
        logger.error(f"❌ فشل الاختبار: {e}", exc_info=True)
        return False
    
    return True

if __name__ == "__main__":
    test_permission_system()