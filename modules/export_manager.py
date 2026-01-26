# modules/export_manager.py
import os
import re
import logging
import unicodedata
from datetime import datetime
from typing import Dict, Any, Callable, List, Optional, Union

import pandas as pd
from database.connection import db

logger = logging.getLogger(__name__)


def sanitize_filename(name: str, max_length: int = 120) -> str:
    """
    تحويل اسم القطاع إلى اسم ملف آمن لنظام الملفات.
    """
    if not name:
        return "sector"
    
    # Normalize unicode
    name = unicodedata.normalize("NFKD", str(name))
    # استبدال المسافات بسطر منخفض
    name = re.sub(r'\s+', '_', name)
    # إزالة أي حرف غير مقبول
    name = re.sub(r'[^\w\-.]', '', name, flags=re.UNICODE)
    name = name.strip("._-")
    
    if not name:
        name = "sector"
    if len(name) > max_length:
        name = name[:max_length]
    
    return name.lower()


def safe_float(value: Union[str, int, float, None], default: float = 0.0) -> float:
    """تحويل آمن إلى float."""
    try:
        if value is None:
            return float(default)
        
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return float(default)
            # استبدال الفاصلة بنقطة
            value = value.replace(',', '.')
        
        return float(value)
    except (ValueError, TypeError):
        return float(default)


def safe_str(value: Any) -> str:
    """تحويل آمن إلى string."""
    if value is None:
        return ''
    return str(value).strip()


class ExportManager:
    """
    مدير التصدير المتقدم.
    ينتج ملف Excel لكل قطاع بصيغة متوافقة مع ImportManager/ExcelMigration.
    """

    SECTOR_FILENAME_TEMPLATE = "{sector_code}.xlsx"
    
    # أسماء الأعمدة كما يتوقعها ExcelMigration
    COLUMN_MAPPING = {
        'box_number': 'علبة',
        'serial_number': 'مسلسل',
        'name': 'اسم الزبون',
        'phone_number': 'رقم واتس الزبون',
        'current_balance': 'الرصيد',
        'last_counter_reading': 'نهاية جديدة',
        'visa_balance': 'تنزيل تأشيرة',
        'withdrawal_amount': 'سحب المشترك',
        'notes': 'ملاحظات'
    }

    def __init__(self, output_dir: str, overwrite: bool = True):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.overwrite = overwrite

    def _get_safe_filename(self, base_name: str) -> str:
        """إنشاء اسم ملف آمن مع تجنب التكرار."""
        base_name = sanitize_filename(base_name)
        filename = self.SECTOR_FILENAME_TEMPLATE.format(sector_code=base_name)
        filepath = os.path.join(self.output_dir, filename)
        
        if os.path.exists(filepath) and not self.overwrite:
            base, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{base}_{timestamp}{ext}"
        
        return filename

    def export_customers_by_sector(
        self,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        يصدر ملفات Excel لكل قطاع.
        Returns: dict with keys: success(bool), files(list), message(str)
        """
        def _update_progress(percent: int, message: str):
            """تحديث التقدم بأمان."""
            if progress_callback:
                try:
                    progress_callback(percent, message)
                except Exception as e:
                    logger.warning(f"خطأ في progress_callback: {e}")

        try:
            _update_progress(5, "جاري الاتصال بقاعدة البيانات...")
            
            with db.get_cursor() as cursor:
                # جلب القطاعات النشطة
                cursor.execute("""
                    SELECT id, name, code 
                    FROM sectors 
                    WHERE is_active = TRUE 
                    ORDER BY name
                """)
                sectors = cursor.fetchall()
                
                if not sectors:
                    return {
                        'success': False, 
                        'files': [], 
                        'message': 'لا يوجد قطاعات للتصدير.'
                    }
                
                total_sectors = len(sectors)
                exported_files = []
                arabic_columns = list(self.COLUMN_MAPPING.values())
                
                for idx, sector in enumerate(sectors, 1):
                    # التصحيح: استخدام المفاتيح النصية بدلاً من الفهرس الرقمي
                    sector_id = sector['id']
                    sector_name = sector['name'] or f"قطاع_{sector_id}"
                    sector_code = sector['code'] or sector_name
                    
                    _update_progress(
                        10 + int((idx - 1) / total_sectors * 80),
                        f"جاري تصدير قطاع: {sector_name} ({idx}/{total_sectors})"
                    )
                    
                    # جلب الزبائن للقطاع
                    cursor.execute("""
                        SELECT 
                            box_number, serial_number, name, phone_number,
                            current_balance, last_counter_reading, 
                            visa_balance, withdrawal_amount, notes
                        FROM customers 
                        WHERE sector_id = %s AND is_active = TRUE
                        ORDER BY name
                    """, (sector_id,))
                    
                    customers = cursor.fetchall()
                    
                    # تحضير البيانات
                    data = []
                    for cust in customers:
                        # التصحيح: استخدام المفاتيح النصية بدلاً من الفهرس الرقمي
                        data.append({
                            'علبة': safe_str(cust['box_number']),
                            'مسلسل': safe_str(cust['serial_number']),
                            'اسم الزبون': safe_str(cust['name']),
                            'رقم واتس الزبون': safe_str(cust['phone_number']),
                            'الرصيد': safe_float(cust['current_balance']),
                            'نهاية جديدة': safe_float(cust['last_counter_reading']),
                            'تنزيل تأشيرة': safe_str(cust['visa_balance']),
                            'سحب المشترك': safe_str(cust['withdrawal_amount']),
                            'ملاحظات': safe_str(cust['notes'])
                        })
                    
                    # إنشاء DataFrame
                    df = pd.DataFrame(data, columns=arabic_columns)
                    
                    # إنشاء اسم الملف
                    filename = self._get_safe_filename(sector_code)
                    filepath = os.path.join(self.output_dir, filename)
                    
                    # حفظ إلى Excel
                    df.to_excel(filepath, index=False, engine='openpyxl')
                    exported_files.append(filepath)
                    
                    logger.info(f"تم تصدير {len(df)} زبون لقطاع {sector_name} إلى {filename}")
                
                _update_progress(100, "اكتمل التصدير بنجاح!")
                
                # تسجيل النتائج
                logger.info(f"تم تصدير {len(exported_files)} ملف في {self.output_dir}")
                
                return {
                    'success': True,
                    'files': exported_files,
                    'message': f'تم التصدير إلى {len(exported_files)} ملف في المجلد: {self.output_dir}',
                    'export_dir': self.output_dir,
                    'file_count': len(exported_files)
                }
                
        except Exception as e:
            logger.exception("خطأ غير متوقع في التصدير المتقدم")
            return {
                'success': False,
                'files': [],
                'message': f'خطأ في التصدير: {str(e)}'
            }