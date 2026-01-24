-- 1. تأكد من وجود الصلاحيات
INSERT INTO permissions_catalog (permission_key, name, category, is_active)
VALUES 
    ('settings.manage_permissions', 'إدارة الصلاحيات', 'settings', TRUE),
    ('*.*', 'جميع الصلاحيات', 'system', TRUE)
ON CONFLICT (permission_key) DO NOTHING;

-- 2. منح كل الصلاحيات للمسؤولين
INSERT INTO role_permissions (role, permission_key, is_allowed)
SELECT DISTINCT 'admin', permission_key, TRUE
FROM permissions_catalog
WHERE is_active = TRUE
UNION ALL
SELECT 'admin', '*.*', TRUE
ON CONFLICT (role, permission_key) DO UPDATE SET is_allowed = TRUE;

-- 3. عرض النتيجة
SELECT '✅ تم الإصلاح بنجاح' as نتيجة;
SELECT role, permission_key, is_allowed 
FROM role_permissions 
WHERE role = 'admin' 
ORDER BY permission_key;