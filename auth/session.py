# auth/session.py
import threading
import logging
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class _ClassProperty:
    """Descriptor لعمل خاصية على مستوى الكلاس (class property)."""
    def __init__(self, fget):
        self.fget = fget
    def __get__(self, obj, owner):
        return self.fget(owner)

def classproperty(func):
    return _ClassProperty(func)

class Session:
    """إدارة جلسة المستخدم الحالية (Desktop App) - Thread-safe"""
    
    _local = threading.local()
    _last_refresh = {}  # {user_id: timestamp} آخر وقت تم فيه تحديث الجلسة

    @classmethod
    def login(cls, user: Dict[str, Any]):
        """
        user = {
            'id': int,
            'username': str,
            'role': str,
            ...
        }
        """
        cls._local.current_user = user
        if user:
            user_id = user.get('id')
            cls._last_refresh[user_id] = time.time()
        logger.info(f"تم تسجيل دخول المستخدم: {user.get('username')} (ID: {user.get('id')})")

    @classmethod
    def logout(cls):
        user = getattr(cls._local, 'current_user', None)
        if user:
            user_id = user.get('id')
            if user_id in cls._last_refresh:
                del cls._last_refresh[user_id]
            logger.info(f"تم تسجيل خروج المستخدم: {user.get('username')}")
        cls._local.current_user = None

    @classmethod
    def is_authenticated(cls) -> bool:
        return getattr(cls._local, 'current_user', None) is not None

    @classmethod
    def get_role(cls) -> Optional[str]:
        user = getattr(cls._local, 'current_user', None)
        return user.get('role') if user else None

    @classmethod
    def get_current_user(cls) -> Optional[Dict[str, Any]]:
        """طرق الوصول البرمجية (explicit) للحصول على المستخدم الحالي."""
        return getattr(cls._local, 'current_user', None)

    # == خاصية صفّية متوافقة مع الوصول القديم Session.current_user ==
    @classproperty
    def current_user(cls) -> Optional[Dict[str, Any]]:
        """
        تسمح بالوصول عبر Session.current_user ليتصرف كقيمة (وليس method).
        هذا يحافظ على التوافق مع كل الكود الموجود.
        """
        return cls.get_current_user()

    @classmethod
    def refresh_user_data(cls, force: bool = False) -> bool:
        """تحديث بيانات المستخدم من قاعدة البيانات"""
        from database.connection import db
        
        user = cls.current_user
        if not user:
            return False
        
        user_id = user.get('id')
        if not user_id:
            return False
        
        # التحقق من وقت آخر تحديث (كل 10 ثوانٍ كحد أدنى)
        last_time = cls._last_refresh.get(user_id, 0)
        current_time = time.time()
        
        if not force and (current_time - last_time) < 10:
            return False  # لم يمر وقت كافٍ منذ آخر تحديث
        
        try:
            with db.get_cursor() as cursor:
                # جلب بيانات المستخدم المحدثة
                cursor.execute("""
                    SELECT id, username, full_name, role, email, permissions, is_active
                    FROM users 
                    WHERE id = %s
                """, (user_id,))
                
                user_data = cursor.fetchone()
                if not user_data:
                    return False
                
                # تحديث بيانات المستخدم في الجلسة
                cls._local.current_user.update({
                    'id': user_data['id'],
                    'username': user_data['username'],
                    'full_name': user_data['full_name'],
                    'role': user_data['role'],
                    'email': user_data['email'],
                    'permissions': user_data.get('permissions', {}),
                    'is_active': user_data['is_active']
                })
                
                # تحديث وقت التحديث
                cls._last_refresh[user_id] = current_time
                
                logger.info(f"✅ تم تحديث جلسة المستخدم: {user_data['username']}")
                return True
                    
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث جلسة المستخدم: {e}")
            return False

    @classmethod
    def force_refresh_all_users(cls, role: str = None):
        """إجبار تحديث جلسات جميع المستخدمين (أو مستخدمي دور معين)"""
        from database.connection import db
        
        try:
            with db.get_cursor() as cursor:
                if role:
                    cursor.execute("SELECT id, username FROM users WHERE role = %s", (role,))
                else:
                    cursor.execute("SELECT id, username FROM users")
                
                users = cursor.fetchall()
                logger.info(f"🔄 سيتم إعادة تحميل جلسات {len(users)} مستخدم")
                return users
        except Exception as e:
            logger.error(f"❌ خطأ في جلب قائمة المستخدمين: {e}")
            return []

# ضبط logging بسيط إن لم يكن مضبوطاً سابقاً
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)