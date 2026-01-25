# db.py
from contextlib import contextmanager
import logging
import os
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

# استخدم متغير البيئة DATABASE_URL لتحديد اتصال قاعدة البيانات
# مثال: postgresql://user:pass@localhost:5432/mydb
DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    """ارجع اتصال psycopg2 جديد"""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL غير معرف. عيّنه كمتغير بيئة.")
    conn = psycopg2.connect(DATABASE_URL)
    return conn

@contextmanager
def get_cursor():
    """
    سياق يعيد cursor dict-like (psycopg2.extras.RealDictCursor).
    الاستخدام:
        with get_cursor() as cursor:
            cursor.execute(...)
            rows = cursor.fetchall()
    """
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cur
    finally:
        try:
            if cur:
                cur.close()
            if conn:
                conn.close()
        except Exception:
            pass

@contextmanager
def transaction():
    """
    مدير سياق للمعاملات. يقوم بالـ commit عند النجاح والـ rollback عند الفشل.
    مثال:
        with transaction() as cursor:
            cursor.execute("UPDATE users SET ...")
    """
    cursor = None
    try:
        with get_cursor() as cur:
            cursor = cur
            yield cursor
            # commit على مستوى الاتصال المرتبط بالـ cursor
            if hasattr(cursor, 'connection'):
                cursor.connection.commit()
    except Exception as e:
        if cursor and hasattr(cursor, 'connection'):
            try:
                cursor.connection.rollback()
            except Exception as rollback_error:
                logger.error(f"خطأ في rollback: {rollback_error}")
        raise
