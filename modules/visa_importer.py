# modules/visa_importer.py
import pandas as pd
import logging
import os
from datetime import datetime
from typing import Dict, List
from database.connection import db

logger = logging.getLogger(__name__)

class VisaImporter:
    """مستورد تأشيرات الزبائن من ملفات Excel"""
    
    def __init__(self, user_id=None):
        self.user_id = user_id
        self.results = {
            'total_rows': 0,
            'successful': 0,
            'failed': 0,
            'errors': [],
            'processed_customers': []
        }
    
    def import_from_excel(self, file_path: str, identifier_column: str = None, amount_column: str = None) -> Dict:
        """
        استيراد تأشيرات الزبائن من ملف Excel
        """
        try:
            # 1. استخراج اسم القطاع من اسم الملف
            sector_name = self._extract_sector_name(file_path)
            
            # 2. قراءة ملف Excel
            df = pd.read_excel(file_path, engine='openpyxl')
            self.results['total_rows'] = len(df)
            
            if df.empty:
                return {
                    'success': False,
                    'message': 'الملف فارغ أو لا يحتوي على بيانات',
                    **self.results
                }
            
            # 3. تحديد أسماء الأعمدة
            arabic_columns = {
                'box': ['علبة', 'رقم العلبة', 'رقم علبة'],
                'serial': ['مسلسل', 'مسلسل رقم'],
                'amount': ['تنزيل تأشيرة', 'تأشيرة', 'مبلغ التأشيرة'],
                'name': ['اسم الزبون', 'اسم', 'الاسم']
            }
            
            # البحث عن أسماء الأعمدة الفعلية في الملف
            actual_columns = self._find_actual_columns(df, arabic_columns, identifier_column, amount_column)
            
            if not actual_columns['box'] and not actual_columns['serial'] and not actual_columns['name']:
                return {
                    'success': False,
                    'message': 'لم يتم العثور على عمود العلبة أو المسلسل أو الاسم في الملف',
                    **self.results
                }
            
            # 4. معالجة كل صف
            for index, row in df.iterrows():
                try:
                    # البحث عن الزبون بعدة طرق
                    customer = None
                    box_number = None
                    serial_number = None
                    name = None
                    
                    # أولا: البحث برقم العلبة
                    if actual_columns['box']:
                        box_number = str(row[actual_columns['box']]).strip()
                        if box_number and box_number != 'nan':
                            customer = self._find_customer_by_box(sector_name, box_number)
                    
                    # ثانيا: البحث بالمسلسل إذا لم يتم العثور
                    if not customer and actual_columns['serial']:
                        serial_number = str(row[actual_columns['serial']]).strip()
                        if serial_number and serial_number != 'nan':
                            customer = self._find_customer_by_serial(sector_name, serial_number)
                    
                    # ثالثا: البحث بالاسم إذا لم يتم العثور
                    if not customer and actual_columns['name']:
                        name = str(row[actual_columns['name']]).strip()
                        if name and name != 'nan':
                            customer = self._find_customer_by_name(sector_name, name)
                    
                    if not customer:
                        self.results['failed'] += 1
                        identifier = box_number or serial_number or name or 'غير معروف'
                        self.results['errors'].append({
                            'row': index + 2,
                            'identifier': identifier,
                            'sector': sector_name,
                            'error': 'لم يتم العثور على الزبون'
                        })
                        continue
                    
                    # 5. استخراج مبلغ التأشيرة
                    visa_amount = 0
                    if actual_columns['amount']:
                        visa_amount = self._parse_amount(row[actual_columns['amount']])
                    
                    if visa_amount <= 0:
                        continue  # تخطي إذا كان المبلغ صفر أو غير صالح
                    
                    # 6. تحديث الرصيد
                    result = self._update_customer_balance(customer['id'], visa_amount)
                    
                    if result['success']:
                        self.results['successful'] += 1
                        self.results['processed_customers'].append({
                            'customer_id': customer['id'],
                            'name': customer['name'],
                            'visa_amount': visa_amount,
                            'old_balance': result['old_balance'],
                            'new_balance': result['new_balance']
                        })
                    else:
                        self.results['failed'] += 1
                        self.results['errors'].append({
                            'row': index + 2,
                            'identifier': customer['name'],
                            'sector': sector_name,
                            'error': result.get('error', 'خطأ في التحديث')
                        })
                        
                except Exception as e:
                    self.results['failed'] += 1
                    self.results['errors'].append({
                        'row': index + 2,
                        'identifier': 'غير معروف',
                        'sector': sector_name,
                        'error': f'خطأ في معالجة الصف: {str(e)}'
                    })
                    logger.error(f"خطأ في صف {index + 2}: {e}")
            
            # إنشاء تقرير النتائج
            report = self._generate_report()
            
            return {
                'success': True,
                'message': f'تم استيراد {self.results["successful"]} تأشيرة بنجاح لقطاع {sector_name}',
                'report': report,
                **self.results
            }
            
        except Exception as e:
            logger.error(f"خطأ في قراءة ملف Excel: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'فشل قراءة الملف: {str(e)}',
                **self.results
            }
    
    def _extract_sector_name(self, file_path: str) -> str:
        """استخراج اسم القطاع من اسم الملف"""
        filename = os.path.basename(file_path)
        # إزالة الامتداد
        sector_name = os.path.splitext(filename)[0]
        # تنظيف الاسم من أي أرقام أو رموز
        import re
        sector_name = re.sub(r'[_\-\d]', '', sector_name)
        return sector_name.strip()
    
    def _find_actual_columns(self, df, arabic_columns, identifier_column=None, amount_column=None):
        """العثور على أسماء الأعمدة الفعلية في DataFrame"""
        actual = {}
        
        # إذا تم تحديد عمود معرف من المستخدم
        if identifier_column:
            if identifier_column in df.columns:
                # تحقق إذا كان العمود ينتمي إلى فئة العلبة أو المسلسل
                if identifier_column in arabic_columns['box']:
                    actual['box'] = identifier_column
                    actual['serial'] = None
                elif identifier_column in arabic_columns['serial']:
                    actual['serial'] = identifier_column
                    actual['box'] = None
                else:
                    # افتراض أنه عمود علبة
                    actual['box'] = identifier_column
                    actual['serial'] = None
            else:
                # إذا العمود غير موجود، البحث تلقائياً
                for key, possible_names in arabic_columns.items():
                    for name in possible_names:
                        if name in df.columns:
                            actual[key] = name
                            break
                    else:
                        actual[key] = None
        else:
            # البحث التلقائي
            for key, possible_names in arabic_columns.items():
                for name in possible_names:
                    if name in df.columns:
                        actual[key] = name
                        break
                else:
                    actual[key] = None
        
        # إذا تم تحديد عمود المبلغ من المستخدم
        if amount_column and amount_column in df.columns:
            actual['amount'] = amount_column
        elif not actual.get('amount'):
            # البحث عن عمود المبلغ تلقائياً
            for name in arabic_columns['amount']:
                if name in df.columns:
                    actual['amount'] = name
                    break
            else:
                actual['amount'] = None
        
        return actual
    
    def _parse_amount(self, value):
        """تحليل مبلغ التأشيرة من أي تنسيق"""
        try:
            if pd.isna(value):
                return 0
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                # إزالة الفواصل والمسافات
                value = value.replace(',', '').replace(' ', '')
                return float(value)
            return 0
        except:
            return 0
    
    def _find_customer_by_box(self, sector_name: str, box_number: str):
        """البحث عن الزبون برقم العلبة"""
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT c.id, c.name, c.current_balance, c.visa_balance
                FROM customers c
                JOIN sectors s ON c.sector_id = s.id
                WHERE s.name = %s AND c.box_number = %s
                AND c.is_active = TRUE
            """, (sector_name, box_number))
            return cursor.fetchone()
    
    def _find_customer_by_serial(self, sector_name: str, serial_number: str):
        """البحث عن الزبون بالمسلسل"""
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT c.id, c.name, c.current_balance, c.visa_balance
                FROM customers c
                JOIN sectors s ON c.sector_id = s.id
                WHERE s.name = %s AND c.serial_number = %s
                AND c.is_active = TRUE
            """, (sector_name, serial_number))
            return cursor.fetchone()
    
    def _find_customer_by_name(self, sector_name: str, name: str):
        """البحث عن الزبون بالاسم"""
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT c.id, c.name, c.current_balance, c.visa_balance
                FROM customers c
                JOIN sectors s ON c.sector_id = s.id
                WHERE s.name = %s AND c.name = %s
                AND c.is_active = TRUE
            """, (sector_name, name))
            return cursor.fetchone()
    
    def _update_customer_balance(self, customer_id: int, visa_amount: float) -> Dict:
        """تحديث رصيد الزبون وإضافة التأشيرة"""
        try:
            with db.get_cursor() as cursor:
                # جلب الرصيد الحالي
                cursor.execute("""
                    SELECT current_balance, visa_balance 
                    FROM customers 
                    WHERE id = %s
                """, (customer_id,))
                customer = cursor.fetchone()
                
                if not customer:
                    return {'success': False, 'error': 'الزبون غير موجود'}
                
                old_balance = float(customer['current_balance'] or 0)
                old_visa = float(customer['visa_balance'] or 0)
                
                # الحساب الجديد
                new_balance = old_balance + visa_amount
                new_visa = old_visa + visa_amount
                
                # تحديث قاعدة البيانات
                cursor.execute("""
                    UPDATE customers 
                    SET current_balance = %s,
                        visa_balance = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (new_balance, new_visa, customer_id))
                
                # تسجيل في السجل التاريخي
                cursor.execute("""
                    INSERT INTO customer_history 
                    (customer_id, action_type, transaction_type,
                     old_value, new_value, amount,
                     current_balance_before, current_balance_after,
                     notes, created_by, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    customer_id,
                    'visa_import',
                    'weekly_visa',
                    old_visa,
                    new_visa,
                    visa_amount,
                    old_balance,
                    new_balance,
                    f'استيراد تأشيرة: {visa_amount:,.0f} كيلو واط',
                    self.user_id
                ))
                
                return {
                    'success': True,
                    'old_balance': old_balance,
                    'new_balance': new_balance
                }
                
        except Exception as e:
            logger.error(f"خطأ في تحديث رصيد الزبون {customer_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_report(self) -> str:
        """إنشاء تقرير مفصل عن عملية الاستيراد"""
        report_lines = [
            "=" * 60,
            f"تقرير استيراد التأشيرات - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            f"إجمالي الصفوف في الملف: {self.results['total_rows']}",
            f"✅ تمت بنجاح: {self.results['successful']}",
            f"❌ فشلت: {self.results['failed']}",
            ""
        ]
        
        if self.results['processed_customers']:
            report_lines.append("الزبائن الذين تم تحديث رصيدهم:")
            report_lines.append("-" * 40)
            for i, customer in enumerate(self.results['processed_customers'], 1):
                report_lines.append(
                    f"{i}. {customer['name']} (ID: {customer['customer_id']})"
                )
                report_lines.append(
                    f"   التأشيرة: {customer['visa_amount']:,.0f} ← الرصيد: {customer['old_balance']:,.0f} → {customer['new_balance']:,.0f}"
                )
        
        if self.results['errors']:
            report_lines.append("")
            report_lines.append("الأخطاء:")
            report_lines.append("-" * 40)
            for error in self.results['errors'][:10]:  # عرض أول 10 أخطاء فقط
                report_lines.append(
                    f"• صف {error['row']}: {error['identifier']} - {error['error']}"
                )
            
            if len(self.results['errors']) > 10:
                report_lines.append(f"... و {len(self.results['errors']) - 10} أخطاء أخرى")
        
        report_lines.append("\n" + "=" * 60)
        
        return "\n".join(report_lines)