# auth/session.py

class Session:
    """إدارة جلسة المستخدم الحالية (Desktop App)"""
    
    current_user = None

    @classmethod
    def login(cls, user: dict):
        """
        user = {
            'id': int,
            'username': str,
            'role': str
        }
        """
        cls.current_user = user

    @classmethod
    def logout(cls):
        cls.current_user = None

    @classmethod
    def is_authenticated(cls) -> bool:
        return cls.current_user is not None

    @classmethod
    def get_role(cls) -> str | None:
        if not cls.current_user:
            return None
        return cls.current_user.get("role")
