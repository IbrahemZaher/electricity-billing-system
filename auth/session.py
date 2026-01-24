# auth/session.py
import threading
import logging
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
        logger.info(f"تم تسجيل دخول المستخدم: {user.get('username')} (ID: {user.get('id')})")

    @classmethod
    def logout(cls):
        user = getattr(cls._local, 'current_user', None)
        if user:
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

# ضبط logging بسيط إن لم يكن مضبوطاً سابقاً
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)
