"""
معالج Excel للتصدير والاستيراد
"""
import pandas as pd
from datetime import datetime
import os
from typing import List, Dict, Optional
import tempfile

class ExcelHandler:
    """معالج ملفات Excel"""
    
    @staticmethod
    def export_to_excel(data: List[Dict], 
                       filename: str, 
                       sheet_name: str = "البيانات") -> str:
        """
        تصدير البيانات إلى ملف Excel
        
        Args:
            data: قائمة من القواميس
            filename: اسم الملف الناتج
            sheet_name: اسم الورقة
            
        Returns:
            مسار الملف الناتج
        """
        try:
            # تحويل البيانات إلى DataFrame
            df = pd.DataFrame(data)
            
            # حفظ في Excel
            if not filename.endswith('.xlsx'):
                filename += '.xlsx'
            
            # تأكد من وجود المجلد
            os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', 
                       exist_ok=True)
            
            # التصدير مع دعم العربية
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # ضبط عرض الأعمدة
                worksheet = writer.sheets[sheet_name]
                for column in df:
                    column_width = max(df[column].astype(str).map(len).max(), len(column)) + 2
                    col_idx = df.columns.get_loc(column)
                    worksheet.column_dimensions[chr(65 + col_idx)].width = min(column_width, 50)
            
            return filename
            
        except Exception as e:
            raise Exception(f"خطأ في التصدير إلى Excel: {str(e)}")
    
    @staticmethod
    def import_from_excel(filename: str, sheet_name: str = 0) -> List[Dict]:
        """
        استيراد البيانات من ملف Excel
        
        Args:
            filename: مسار ملف Excel
            sheet_name: اسم أو رقم الورقة
            
        Returns:
            قائمة من القواميس
        """
        try:
            # قراءة الملف
            df = pd.read_excel(filename, sheet_name=sheet_name)
            
            # تحويل إلى قواميس
            data = df.to_dict('records')
            
            # تنظيف القيم NaN
            for item in data:
                for key, value in item.items():
                    if pd.isna(value):
                        item[key] = None
            
            return data
            
        except Exception as e:
            raise Exception(f"خطأ في الاستيراد من Excel: {str(e)}")
    
    @staticmethod
    def export_bills_to_excel(bills_data: List[Dict], 
                             include_customer_info: bool = True) -> str:
        """
        تصدير بيانات الفواتير إلى Excel
        
        Args:
            bills_data: بيانات الفواتير
            include_customer_info: تضمين معلومات العميل
            
        Returns:
            مسار الملف الناتج
        """
        if not bills_data:
            raise Exception("لا توجد بيانات للتصدير")
        
        # إنشاء اسم ملف فريد
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"فواتير_الكهرباء_{timestamp}.xlsx"
        
        return ExcelHandler.export_to_excel(bills_data, filename, "الفواتير")
    
    @staticmethod
    def create_template(template_type: str) -> str:
        """
        إنشاء قوالب Excel
        
        Args:
            template_type: نوع القالب ('customers', 'meter_readings', 'bills')
            
        Returns:
            مسار ملف القالب
        """
        templates = {
            'customers': [
                {
                    'customer_code': 'CUST001',
                    'full_name': 'اسم العميل',
                    'phone': '0555555555',
                    'address': 'العنوان',
                    'meter_number': 'MTR001',
                    'connection_type': 'سكني'
                }
            ],
            'meter_readings': [
                {
                    'customer_code': 'CUST001',
                    'reading_date': '2024-01-15',
                    'current_reading': '1500.50',
                    'reading_type': 'فعلي'
                }
            ],
            'bills': [
                {
                    'customer_code': 'CUST001',
                    'billing_month': '2024-01',
                    'units_consumed': '250.5',
                    'total_amount': '500.75'
                }
            ]
        }
        
        if template_type not in templates:
            raise Exception(f"نموذج غير معروف: {template_type}")
        
        # حفظ القالب
        filename = f"قالب_{template_type}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        return ExcelHandler.export_to_excel(templates[template_type], filename, template_type)

# كائن عام للاستخدام
excel_handler = ExcelHandler()