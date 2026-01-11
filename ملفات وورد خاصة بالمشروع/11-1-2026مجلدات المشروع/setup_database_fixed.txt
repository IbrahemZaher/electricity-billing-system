-- setup_database_fixed.sql
-- إنشاء قاعدة البيانات باستخدام template0 (محايد اللغات)

-- 1. إنشاء قاعدة البيانات
CREATE DATABASE electricity_billing
WITH
OWNER = postgres
ENCODING = 'UTF8'
LC_COLLATE = 'C'        -- استخدام إعداد محايد
LC_CTYPE = 'C'          -- استخدام إعداد محايد
TEMPLATE = template0     -- مهم: استخدام القالب المحايد
CONNECTION LIMIT = -1;

-- 2. إنشاء المستخدم
CREATE USER billing_user WITH PASSWORD 'SecurePassword123!';

-- 3. الاتصال بقاعدة البيانات الجديدة
\c electricity_billing

-- 4. منح الصلاحيات
GRANT ALL PRIVILEGES ON DATABASE electricity_billing TO billing_user;
GRANT ALL ON SCHEMA public TO billing_user;

-- 5. إنشاء امتدادات
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 6. التعليق
COMMENT ON DATABASE electricity_billing IS 'قاعدة بيانات نظام إدارة فواتير مولدة الريان';