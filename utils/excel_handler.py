import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ExcelHandler:
    """معالج ملفات Excel مع دعم متقدم للاستيراد والتصدير"""
    
    @staticmethod
    def import_from_excel(filename: str) -> List[Dict[str, Any]]:
        """
        استيراد بيانات من ملف Excel مع معالجة متقدمة
        
        Args:
            filename: مسار ملف Excel
            
        Returns:
            قائمة من القواميس تحتوي على البيانات
        """
        try:
            # قراءة ملف Excel - قراءة جميع الأعمدة كنص
            df = pd.read_excel(filename, dtype=str)
            
            # تحويل NaN إلى None لتفادي مشاكل قاعدة البيانات
            df = df.where(pd.notnull(df), None)
            
            # تحويل DataFrame إلى قائمة من القواميس
            data = df.to_dict('records')
            
            logger.info(f"تم استيراد {len(data)} سطر من ملف Excel: {filename}")
            return data
            
        except FileNotFoundError:
            logger.error(f"الملف غير موجود: {filename}")
            return []
        except Exception as e:
            logger.error(f"خطأ في قراءة ملف Excel {filename}: {e}")
            return []
    
    @staticmethod
    def export_to_excel(data: List[Dict[str, Any]], filename: str, sheet_name: str = "البيانات") -> bool:
        """
        تصدير البيانات إلى ملف Excel
        
        Args:
            data: قائمة البيانات
            filename: مسار ملف الحفظ
            sheet_name: اسم الورقة
            
        Returns:
            نجاح أو فشل العملية
        """
        try:
            if not data:
                return False
            
            # إنشاء DataFrame من البيانات
            df = pd.DataFrame(data)
            
            # استخدام محرك openpyxl مع دعم اللغة العربية
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # ضبط عرض الأعمدة تلقائياً
                worksheet = writer.sheets[sheet_name]
                for column in df:
                    column_length = max(df[column].astype(str).map(len).max(), len(str(column))) + 2
                    col_idx = df.columns.get_loc(column)
                    column_letter = chr(65 + col_idx)  # A, B, C, ...
                    worksheet.column_dimensions[column_letter].width = min(column_length, 50)
            
            logger.info(f"تم تصدير {len(data)} سطر إلى ملف Excel: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في تصدير ملف Excel: {e}")
            return False
    
    @staticmethod
    def clean_value(value):
        """تنظيف وتنسيق القيمة من Excel"""
        if value is None:
            return None
        
        # تحويل إلى نص
        value_str = str(value).strip()
        
        # إذا كانت القيمة فارغة بعد التحويل
        if not value_str or value_str.lower() in ['nan', 'null', 'none', '']:
            return None
        
        return value_str
    
    @staticmethod
    def convert_to_float(value):
        """تحويل القيمة إلى رقم عشري"""
        if value is None:
            return 0.0
        
        try:
            # إزالة الفواصل (مثل 1,000.50)
            clean_val = str(value).replace(',', '').strip()
            if not clean_val:
                return 0.0
            return float(clean_val)
        except:
            return 0.0
    
    @staticmethod
    def get_column_value(record: Dict[str, Any], possible_names: List[str], default=None):
        """
        الحصول على قيمة عمود مع احتمالات متعددة للأسماء
        
        Args:
            record: سجل البيانات
            possible_names: قائمة بالأسماء المحتملة للعمود
            default: القيمة الافتراضية
            
        Returns:
            قيمة العمود أو القيمة الافتراضية
        """
        for name in possible_names:
            if name in record and record[name] is not None:
                return record[name]
        return default