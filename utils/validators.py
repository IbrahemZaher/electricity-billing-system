"""
نظام التحقق من صحة البيانات لـ electricity-billing-system
"""
import re
from datetime import datetime
from typing import Any, Tuple, Optional

class Validators:
    """فئة التحقق من صحة المدخلات"""
    
    @staticmethod
    def validate_number(value: Any, min_val: float = None, max_val: float = None) -> Tuple[bool, str]:
        """التحقق من صحة الرقم"""
        try:
            num = float(value)
            
            if min_val is not None and num < min_val:
                return False, f"القيمة يجب أن تكون أكبر من أو تساوي {min_val}"
            
            if max_val is not None and num > max_val:
                return False, f"القيمة يجب أن تكون أقل من أو تساوي {max_val}"
                
            return True, "صالح"
        except (ValueError, TypeError):
            return False, "يجب إدخال رقم صحيح"
    
    @staticmethod
    def validate_positive_number(value: Any) -> Tuple[bool, str]:
        """التحقق من أن الرقم موجب"""
        return Validators.validate_number(value, min_val=0)
    
    @staticmethod
    def validate_meter_reading(current: float, previous: float) -> Tuple[bool, str]:
        """التحقق من قراءة العداد"""
        if current < previous:
            return False, "القراءة الحالية يجب أن تكون أكبر من القراءة السابقة"
        return True, "صالح"
    
    @staticmethod
    def validate_date(date_str: str, date_format: str = "%Y-%m-%d") -> Tuple[bool, str]:
        """التحقق من صحة التاريخ"""
        try:
            datetime.strptime(date_str, date_format)
            return True, "صالح"
        except ValueError:
            return False, f"التاريخ يجب أن يكون بالصيغة {date_format}"
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """التحقق من صحة البريد الإلكتروني"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email):
            return True, "صالح"
        return False, "بريد إلكتروني غير صالح"
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str]:
        """التحقق من صحة رقم الهاتف"""
        # إزالة المسافات والإشارات
        clean_phone = re.sub(r'[\s\+\-\(\)]', '', phone)
        
        if len(clean_phone) < 8:
            return False, "رقم الهاتف قصير جدًا"
        
        if not clean_phone.isdigit():
            return False, "يجب أن يحتوي رقم الهاتف على أرقام فقط"
            
        return True, "صالح"
    
    @staticmethod
    def validate_string(value: str, min_len: int = 1, max_len: int = 255) -> Tuple[bool, str]:
        """التحقق من صحة النص"""
        if not isinstance(value, str):
            return False, "يجب إدخال نص"
        
        value = value.strip()
        
        if len(value) < min_len:
            return False, f"النص قصير جدًا (الحد الأدنى {min_len} حرف)"
        
        if len(value) > max_len:
            return False, f"النص طويل جدًا (الحد الأقصى {max_len} حرف)"
            
        return True, "صالح"

# كائن عام للاستخدام في المشروع
validator = Validators()