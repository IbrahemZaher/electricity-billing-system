# auth/authentication.py
import bcrypt
import hashlib
import jwt
from datetime import datetime, timedelta
import logging
import json  # أضف هذا الاستيراد
from config.settings import SECRET_KEY
from auth.session import Session
from auth.permissions import require_permission
import os
# إزالة: from db import transaction, get_cursor
from database.connection import db  # استخدام db فقط من هنا

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
                return True, 'bcrypt'
        except (ValueError, Exception):
            pass
        
        # المحاولة الثانية: التحقق باستخدام SHA256 (للهاشات القديمة)
        try:
            sha256_hash = hashlib.sha256(password.encode()).hexdigest()
            if sha256_hash == hashed_password:
                return True, 'sha256'
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
    
    def login(self, username, password, db_connection=None):
        db_obj = db_connection if db_connection is not None else db
        try:
            with db_obj.get_cursor() as cursor:
                # تحقق إن كان العمود موجودًا قبل بناء الاستعلام
                cursor.execute("""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = %s AND column_name = %s
                """, ('users', 'email'))
                has_email = cursor.fetchone() is not None

                if has_email:
                    cursor.execute("""
                        SELECT id, username, password_hash, full_name, role, permissions, is_active, email
                        FROM users
                        WHERE username = %s
                    """, (username,))
                else:
                    cursor.execute("""
                        SELECT id, username, password_hash, full_name, role, permissions, is_active
                        FROM users
                        WHERE username = %s
                    """, (username,))

                user = cursor.fetchone()

                if not user:
                    return {'success': False, 'error': 'اسم المستخدم أو كلمة المرور غير صحيحة'}

                if not user.get('is_active'):
                    return {'success': False, 'error': 'الحساب غير مفعل'}

                is_valid, hash_type = self.verify_password(password, user['password_hash'])

                if not is_valid:
                    return {'success': False, 'error': 'اسم المستخدم أو كلمة المرور غير صحيحة'}

                # تحديث وقت آخر دخول
                cursor.execute("""
                    UPDATE users 
                    SET updated_at = CURRENT_TIMESTAMP 
                    WHERE id = %s
                """, (user['id'],))

                # ترقية هاش من sha256 إلى bcrypt إن لزم
                if hash_type == 'sha256':
                    new_hash = self.hash_password(password)
                    cursor.execute("""
                        UPDATE users 
                        SET password_hash = %s 
                        WHERE id = %s
                    """, (new_hash, user['id']))
                    logger.info(f"تم ترقية هاش كلمة المرور للمستخدم {username} من SHA256 إلى bcrypt")

                token = self.create_token(user['id'], user['username'], user['role'])

                user_payload = {
                    'id': user['id'],
                    'username': user['username'],
                    'role': user['role'],
                    'full_name': user.get('full_name'),
                    'email': user.get('email'),
                    'permissions': user.get('permissions', {}),
                    'token': token
                }

                Session.login(user_payload)

                return {
                    'success': True,
                    'user': {
                        'id': user['id'],
                        'username': user['username'],
                        'full_name': user.get('full_name'),
                        'email': user.get('email'),
                        'role': user.get('role'),
                        'permissions': user.get('permissions', {})
                    },
                    'token': token
                }

        except Exception as e:
            logger.exception(f"خطأ في تسجيل الدخول: {e}")
            return {'success': False, 'error': 'حدث خطأ أثناء تسجيل الدخول'}
    
    def register_user(self, user_data, db_connection=None, performed_by=None):
        """
        تسجيل مستخدم جديد.
        """
        # 1) حالة الإعداد (setup) — مفعل يدوياً عبر متغير بيئة
        allow_setup = os.getenv('ALLOW_SETUP_USER_CREATION', 'false').lower() == 'true'

        if performed_by is None and not allow_setup:
            # لا يوجد من قام بالعملية ولا السماح بالإعداد -> اطلب صلاحية الجلسة الحالية
            try:
                require_permission('system.manage_users')
            except Exception as exc:
                logger.error("محاولة إنشاء مستخدم بدون صلاحية أو خلال إعداد غير مسموح", exc_info=True)
                raise

        # 2) الآن ننفذ الإنشاء داخل معاملة آمنة
        try:
            # استخدام db من database.connection بشكل مباشر
            db_obj = db_connection if db_connection is not None else db
            
            with db_obj.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (username, password_hash, full_name, role, permissions, email, is_active, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    RETURNING id
                """, (
                    user_data['username'],
                    self.hash_password(user_data['password']),
                    user_data.get('full_name', ''),
                    user_data.get('role', 'accountant'),
                    json.dumps(user_data.get('permissions', {})),
                    user_data.get('email'),
                    user_data.get('is_active', True)
                ))
                result = cursor.fetchone()
                user_id = result['id'] if result else None

            # تسجيل النشاط إن كان performed_by موجوداً
            if performed_by:
                try:
                    self.log_activity(
                        performed_by,
                        'register',
                        f'تم تسجيل مستخدم جديد: {user_data.get("full_name", user_data["username"])}',
                        db_connection
                    )
                except Exception:
                    logger.exception("فشل تسجيل النشاط بعد إنشاء المستخدم")

            return {'success': True, 'user_id': user_id}

        except Exception as e:
            error_msg = str(e).lower()
            if 'unique' in error_msg or 'duplicate' in error_msg:
                if 'username' in error_msg:
                    return {'success': False, 'error': 'اسم المستخدم مستخدم بالفعل'}
                elif 'email' in error_msg:
                    return {'success': False, 'error': 'البريد الإلكتروني مستخدم بالفعل'}
            logger.error(f"خطأ في تسجيل المستخدم: {e}", exc_info=True)
            return {'success': False, 'error': 'حدث خطأ في إنشاء المستخدم'}
    
    def log_activity(self, user_id, action, description, db_connection=None, 
                     ip_address=None, request_id=None, before_snapshot=None, after_snapshot=None):
        """تسجيل نشاط المستخدم مع معلومات إضافية"""
        try:
            # استخدام db من database.connection إذا لم يتم تمرير اتصال
            db_obj = db_connection if db_connection is not None else db
            
            with db_obj.get_cursor() as cursor:
                # التحقق من وجود الأعمدة أولاً
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'activity_logs'
                """)
                
                columns = [row['column_name'] for row in cursor.fetchall()]
                
                if 'before_snapshot' in columns and 'after_snapshot' in columns:
                    cursor.execute("""
                        INSERT INTO activity_logs 
                        (user_id, action_type, description, ip_address, before_snapshot, after_snapshot, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, (
                        user_id,
                        action,
                        description,
                        ip_address,
                        before_snapshot,
                        after_snapshot
                    ))
                else:
                    # استخدام الاستعلام البسيط
                    cursor.execute("""
                        INSERT INTO activity_logs 
                        (user_id, action_type, description, ip_address, created_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, (
                        user_id,
                        action,
                        description,
                        ip_address
                    ))
        except Exception as e:
            logger.error(f"خطأ في تسجيل النشاط: {e}", exc_info=True)
            
                
    def check_permission(self, user, permission):
        """التحقق من صلاحية المستخدم"""
        if user['role'] == 'admin':
            return True
        
        permissions = user.get('permissions', {})
        return permissions.get(permission, False)

# إنشاء كائن المصادقة
auth = Authentication()