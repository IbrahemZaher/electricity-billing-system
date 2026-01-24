# auth/permissions.py (محدث كلياً)
"""
نظام الصلاحيات الموحد
يستخدم PermissionEngine المركزي
"""

from auth.permission_engine import permission_engine
from auth.session import Session
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# ==================== واجهة التطبيق ====================

def has_permission(permission_key: str) -> bool:
    """
    التحقق من صلاحية المستخدم الحالي
    
    Args:
        permission_key: مفتاح الصلاحية (مثل 'customers.view')
        
    Returns:
        bool: True إذا كان لديه الصلاحية
    """
    if not Session.is_authenticated():
        logger.warning("المستخدم غير مسجل دخول")
        return False
    
    user_id = Session.current_user['id']
    user_role = Session.get_role()  # تمرير الدور لتجنب استعلام إضافي
    result = permission_engine.has_permission(user_id, permission_key, user_role)
    
    logger.debug(f"التحقق من الصلاحية: {permission_key} للمستخدم {user_id} => {result}")
    return result

def require_permission(permission_key: str):
    """
    ديكوراتور/دالة للتحقق من الصلاحية قبل تنفيذ إجراء
    
    Raises:
        PermissionError: إذا لم يكن لديه الصلاحية
    """
    if not has_permission(permission_key):
        raise PermissionError(f"ليس لديك الصلاحية: {permission_key}")
    return True

# ==================== أدوات المساعدة ====================

def get_current_user_permissions() -> Dict[str, bool]:
    """الحصول على جميع صلاحيات المستخدم الحالي"""
    if not Session.is_authenticated():
        return {}
    
    user_id = Session.current_user['id']
    return permission_engine.get_user_permissions(user_id)

def get_all_permissions() -> List[Dict[str, Any]]:
    """الحصول على جميع الصلاحيات في النظام"""
    return permission_engine.get_all_permissions()

def get_permissions_by_category() -> Dict[str, List[Dict[str, Any]]]:
    """الحصول على الصلاحيات مصنفة حسب الفئة"""
    all_perms = get_all_permissions()
    categorized = {}
    
    for perm in all_perms:
        category = perm['category']
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(perm)
    
    return categorized

# ==================== ديكوراتورات UI ====================

def check_permission_decorator(permission_key: str):
    """
    ديكوراتور للتحقق من الصلاحية قبل فتح واجهة
    
    استخدام:
        @check_permission_decorator('customers.view')
        def open_customers_window():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not has_permission(permission_key):
                import tkinter.messagebox as messagebox
                messagebox.showerror("صلاحيات", f"ليس لديك صلاحية الوصول: {permission_key}")
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator

def disable_without_permission(widget, permission_key: str):
    """
    تعطيل عنصر واجهة إذا لم تكن الصلاحية متاحة
    
    استخدام:
        button = tk.Button(...)
        disable_without_permission(button, 'invoices.create')
    """
    if not has_permission(permission_key):
        widget.config(state='disabled')
    return widget

# ==================== توافق مع النظام القديم ====================

# للحفاظ على التوافق مع الكود الحالي
def check_permission(user, permission):
    """
    واجهة متوافقة مع النظام القديم
    
    Args:
        user: قاموس بيانات المستخدم (مثل Session.current_user)
        permission: اسم الصلاحية القديم
        
    Returns:
        bool: True إذا كان لديه الصلاحية
    """
    if not user:
        return False
    
    # تحويل الصلاحيات القديمة إلى الجديدة
    permission_map = {
        'view_customers': 'customers.view',
        'create_bills': 'invoices.create',
        'edit_bills': 'invoices.edit',
        'view_reports': 'reports.view',
        'manage_users': 'system.manage_users',
        'view_archive': 'system.view_archive',
        'view_activity_log': 'system.view_activity_log',
        'manage_settings': 'settings.manage',
        'manage_import': 'system.advanced_import',
        'import_data': 'system.import_data',
        'export_data': 'system.export_data'
    }
    
    new_permission = permission_map.get(permission, permission)
    
    # استخدام النظام الجديد مع تمرير الدور
    return permission_engine.has_permission(user['id'], new_permission, user.get('role'))