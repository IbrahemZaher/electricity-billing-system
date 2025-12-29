# database/connection.py
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import logging
from contextlib import contextmanager
import os
from config.settings import DATABASE_CONFIG

logger = logging.getLogger(__name__)

class DatabaseConnection:
    _instance = None
    _connection_pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance._initialize_pool()
        return cls._instance
    
    def _initialize_pool(self):
        try:
            self._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                **DATABASE_CONFIG
            )
            logger.info("تم إنشاء مجموعة اتصالات قاعدة البيانات بنجاح")
        except Exception as e:
            logger.error(f"فشل إنشاء مجموعة الاتصالات: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = self._connection_pool.getconn()
            yield conn
        except Exception as e:
            logger.error(f"خطأ في الحصول على الاتصال: {e}")
            raise
        finally:
            if conn:
                self._connection_pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, connection=None):
        if connection:
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            try:
                yield cursor
                connection.commit()
            except Exception as e:
                connection.rollback()
                logger.error(f"خطأ في تنفيذ الاستعلام: {e}")
                raise
            finally:
                cursor.close()
        else:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                try:
                    yield cursor
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    logger.error(f"خطأ في تنفيذ الاستعلام: {e}")
                    raise
                finally:
                    cursor.close()
    
    def close_all(self):
        if self._connection_pool:
            self._connection_pool.closeall()
            logger.info("تم إغلاق جميع اتصالات قاعدة البيانات")

# إنشاء كائن قاعدة البيانات العام
db = DatabaseConnection()