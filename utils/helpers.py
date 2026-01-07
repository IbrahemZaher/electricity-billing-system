# utils/helpers.py
from datetime import datetime, timedelta
from typing import Any, Union, List, Dict


class Helpers:
    """أدوات مساعدة مشتركة للمشروع (Desktop-safe)"""

    @staticmethod
    def format_currency(amount: float, currency: str = "ل.س") -> str:
        """تنسيق المبالغ المالية"""
        try:
            return f"{float(amount):,.0f} {currency}"
        except (ValueError, TypeError):
            return f"0 {currency}"

    @staticmethod
    def format_date(
        date_obj: Union[datetime, str],
        format_str: str = "%Y-%m-%d"
    ) -> str:
        """تنسيق التاريخ"""
        if isinstance(date_obj, str):
            try:
                date_obj = datetime.strptime(date_obj, "%Y-%m-%d")
            except ValueError:
                return date_obj
        return date_obj.strftime(format_str)

    @staticmethod
    def calculate_due_date(
        issue_date: datetime,
        days: int = 30
    ) -> datetime:
        """حساب تاريخ الاستحقاق"""
        return issue_date + timedelta(days=days)

    @staticmethod
    def generate_bill_number(
        customer_code: str,
        month: int,
        year: int
    ) -> str:
        """إنشاء رقم فاتورة فريد"""
        timestamp = datetime.now().strftime("%H%M%S")
        return f"BILL-{customer_code}-{year}{month:02d}-{timestamp}"

    @staticmethod
    def parse_number(value: Any) -> float:
        """تحويل أي قيمة إلى رقم آمن"""
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            return 0.0


# كائن عام
helper = Helpers()
