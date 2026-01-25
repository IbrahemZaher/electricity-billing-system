# services/users_service.py
from auth.permissions import require_permission
from db import transaction
from permission_engine import permission_engine
import logging

logger = logging.getLogger(__name__)

class UserService:
    @staticmethod
    def update_user(user_id, update_data):
        require_permission('system.manage_users')
        with transaction() as cursor:
            cursor.execute("""
                UPDATE users 
                SET username=%s, full_name=%s, role=%s, email=%s, updated_at=CURRENT_TIMESTAMP
                WHERE id = %s
            """, (
                update_data.get('username'),
                update_data.get('full_name'),
                update_data.get('role'),
                update_data.get('email'),
                user_id
            ))
        permission_engine.clear_cache(user_id)
        return True

    @staticmethod
    def deactivate_user(user_id):
        require_permission('system.manage_users')
        # منع تعطيل النفس على مستوى الخدمة
        from auth.authentication import auth
        if user_id == auth.current_user_id:
            raise ValueError("لا يمكنك تعطيل حسابك بنفسك")

        with transaction() as cursor:
            cursor.execute("SELECT role, is_active FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if user and user['role'] == 'admin' and user['is_active']:
                cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'admin' AND is_active = TRUE")
                admin_count = cursor.fetchone()['cnt']
                if admin_count <= 1:
                    raise ValueError("لا يمكن تعطيل آخر حساب مدير النظام")

            cursor.execute("""
                UPDATE users 
                SET is_active = FALSE, updated_at=CURRENT_TIMESTAMP 
                WHERE id = %s
            """, (user_id,))

        permission_engine.clear_cache(user_id)
        return True
