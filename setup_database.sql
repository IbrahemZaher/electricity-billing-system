-- setup_database.sql
-- إنشاء قاعدة البيانات والمستخدم

-- 1. إنشاء قاعدة البيانات
CREATE DATABASE electricity_billing
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'Arabic_Saudi Arabia.1256'
    LC_CTYPE = 'Arabic_Saudi Arabia.1256'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

-- 2. إنشاء المستخدم
CREATE USER billing_user WITH PASSWORD 'SecurePassword123!';

-- 3. منح الصلاحيات
GRANT ALL PRIVILEGES ON DATABASE electricity_billing TO billing_user;

-- 4. الاتصال بقاعدة البيانات الجديدة
\c electricity_billing

-- 5. إنشاء امتداد للتعامل مع JSON بشكل أفضل
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 6. منح صلاحيات إضافية للمستخدم
GRANT ALL ON SCHEMA public TO billing_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO billing_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO billing_user;

-- 7. إضافة التعليقات
COMMENT ON DATABASE electricity_billing IS 'قاعدة بيانات نظام إدارة فواتير مولدة الريان';