# auth/authentication.py
from database.connection import db
import bcrypt
import hashlib  # لإضافة الدعم المرحلي لـ SHA256
import jwt
from datetime import datetime, timedelta
import logging
from config.settings import SECRET_KEY
from auth.session import Session  # إضافة استيراد Session

logger = logging.getLogger(__name__)

class Authentication:
    def __init__(self):
        self.secret_key = SECRET_KEY
    
    def hash_password(self, password):
        """تشفير كلمة المرور باستخدام bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password, hashed_password):
        """التحقق من كلمة المرور - يدعم bcrypt و SHA256 (ترحيل)"""
        # المحاولة الأولى: التحقق باستخدام bcrypt
        try:
            if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
                return True, 'bcrypt'  # نجاح باستخدام bcrypt
        except (ValueError, Exception):
            pass
        
        # المحاولة الثانية: التحقق باستخدام SHA256 (للهاشات القديمة)
        try:
            sha256_hash = hashlib.sha256(password.encode()).hexdigest()
            if sha256_hash == hashed_password:
                return True, 'sha256'  # نجاح باستخدام SHA256
        except Exception:
            pass
        
        return False, None
    
    def create_token(self, user_id, username, role):
        """إنشاء توكن للمستخدم"""
        payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'exp': datetime.utcnow() + timedelta(hours=8)
        }
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        # التأكد من أن التوكن هو str
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        return token
    
    def verify_token(self, token):
        """التحقق من التوكن"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def login(self, username, password):
        """تسجيل الدخول"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, username, password_hash, full_name, role, permissions, is_active
                    FROM users 
                    WHERE username = %s
                """, (username,))
                
                user = cursor.fetchone()
                
                if not user:
                    return {'error': 'اسم المستخدم أو كلمة المرور غير صحيحة'}
                
                if not user['is_active']:
                    return {'error': 'الحساب غير مفعل'}
                
                # التحقق من كلمة المرور (تدعم bcrypt و SHA256)
                is_valid, hash_type = self.verify_password(password, user['password_hash'])
                
                if is_valid:
                    # تحديث وقت آخر دخول
                    cursor.execute("""
                        UPDATE users 
                        SET updated_at = CURRENT_TIMESTAMP 
                        WHERE id = %s
                    """, (user['id'],))
                    
                    # إذا كان الهاش من نوع SHA256، نرقيّه إلى bcrypt
                    if hash_type == 'sha256':
                        new_hash = self.hash_password(password)
                        cursor.execute("""
                            UPDATE users 
                            SET password_hash = %s 
                            WHERE id = %s
                        """, (new_hash, user['id']))
                        logger.info(f"تم ترقية هاش كلمة المرور للمستخدم {username} من SHA256 إلى bcrypt")
                    
                    # إنشاء التوكن
                    token = self.create_token(
                        user['id'], 
                        user['username'], 
                        user['role']
                    )
                    
                    # إنشاء user_payload واستدعاء Session.login
                    user_payload = {
                        'id': user['id'],
                        'username': user['username'],
                        'role': user['role'],
                        'full_name': user.get('full_name'),
                        'permissions': user.get('permissions', {}),
                        'token': token
                    }
                    
                    # استدعاء Session.login (كـ instance method)
                    session_obj = Session()
                    session_obj.login(user_payload)
                    
                    # إرجاع نفس الـ dict كما في الكود الحالي
                    return {
                        'id': user['id'],
                        'username': user['username'],
                        'full_name': user['full_name'],
                        'role': user['role'],
                        'permissions': user['permissions'],
                        'token': token
                    }
                else:
                    return {'error': 'اسم المستخدم أو كلمة المرور غير صحيحة'}
                    
        except Exception as e:
            logger.error(f"خطأ في تسجيل الدخول: {e}")
            return {'error': 'حدث خطأ أثناء تسجيل الدخول'}

    def register_user(self, user_data):
        """تسجيل مستخدم جديد"""
        try:
            with db.get_cursor() as cursor:
                # التحقق من عدم وجود المستخدم
                cursor.execute("SELECT id FROM users WHERE username = %s", 
                             (user_data['username'],))
                if cursor.fetchone():
                    return {'error': 'اسم المستخدم موجود بالفعل'}
                
                # تشفير كلمة المرور باستخدام bcrypt
                hashed_password = self.hash_password(user_data['password'])
                
                # إضافة المستخدم
                cursor.execute("""
                    INSERT INTO users 
                    (username, password_hash, full_name, role, permissions)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    user_data['username'],
                    hashed_password,
                    user_data['full_name'],
                    user_data.get('role', 'accountant'),
                    user_data.get('permissions', {})
                ))
                
                user_id = cursor.fetchone()['id']
                
                # تسجيل النشاط
                self.log_activity(
                    user_id,
                    'register',
                    f'تم تسجيل مستخدم جديد: {user_data["full_name"]}'
                )
                
                return {'success': True, 'user_id': user_id}
                
        except Exception as e:
            logger.error(f"خطأ في تسجيل المستخدم: {e}")
            return {'error': str(e)}
    
    def log_activity(self, user_id, action_type, description, ip_address=None, user_agent=None):
        """تسجيل نشاط المستخدم"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO activity_logs 
                    (user_id, action_type, description, ip_address, user_agent)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, action_type, description, ip_address, user_agent))
                
        except Exception as e:
            logger.error(f"خطأ في تسجيل النشاط: {e}")
    
    def check_permission(self, user, permission):
        """التحقق من صلاحية المستخدم"""
        if user['role'] == 'admin':
            return True
        
        permissions = user.get('permissions', {})
        return permissions.get(permission, False)

# إنشاء كائن المصادقة
auth = Authentication()