# auth/permissions.py

from enum import Enum
from auth.session import Session


class Role(Enum):
    ADMIN = "admin"
    ACCOUNTANT = "accountant"
    VIEWER = "viewer"


class Permission(Enum):
    VIEW_CUSTOMERS = "view_customers"
    CREATE_BILLS = "create_bills"
    EDIT_BILLS = "edit_bills"
    VIEW_REPORTS = "view_reports"
    MANAGE_USERS = "manage_users"


ROLE_PERMISSIONS = {
    Role.ADMIN: list(Permission),
    Role.ACCOUNTANT: [
        Permission.VIEW_CUSTOMERS,
        Permission.CREATE_BILLS,
        Permission.EDIT_BILLS,
        Permission.VIEW_REPORTS
    ],
    Role.VIEWER: [
        Permission.VIEW_CUSTOMERS,
        Permission.VIEW_REPORTS
    ]
}


def has_permission(permission: Permission) -> bool:
    """التحقق من صلاحية المستخدم الحالي"""
    role = Session.get_role()
    if not role:
        return False

    try:
        role_enum = Role(role)
    except ValueError:
        return False

    return permission in ROLE_PERMISSIONS.get(role_enum, [])


def require_permission(permission: Permission):
    """
    تستخدم داخل UI قبل تنفيذ أي عملية
    """
    if not has_permission(permission):
        raise PermissionError("ليس لديك الصلاحية لتنفيذ هذا الإجراء")
