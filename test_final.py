# test_final.py
import sys
sys.path.append('.')

from auth.permission_engine import permission_engine
from database.connection import db
import logging

logging.basicConfig(level=logging.INFO)

def test():
    print("🔍 اختبار نهائي لنظام الصلاحيات")
    print("=" * 50)
    
    user_id = 1  # admin
    
    # اختبار 1: معلومات المستخدم
    with db.get_cursor() as cursor:
        cursor.execute("SELECT username, role FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        print(f"👤 المستخدم: {user['username']} (دور: {user['role']})")
    
    # اختبار 2: صلاحية محددة
    permission = 'settings.manage_permissions'
    result = permission_engine.has_permission(user_id, permission)
    print(f"\n✅ صلاحية '{permission}': {'نعم' if result else 'لا'}")
    
    # اختبار 3: صلاحيات أخرى للتأكد
    test_permissions = [
        'customers.view',
        'invoices.create',
        'system.manage_users',
        'settings.manage',
        '*.*'
    ]
    
    print("\n🔧 اختبار صلاحيات إضافية:")
    for perm in test_permissions:
        has_perm = permission_engine.has_permission(user_id, perm)
        status = "✅" if has_perm else "❌"
        print(f"  {status} {perm}")

if __name__ == "__main__":
    test()