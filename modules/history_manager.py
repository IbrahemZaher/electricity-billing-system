# modules/history_manager.py - تصحيح الأخطاء

import logging
from datetime import datetime
from database.connection import db
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class HistoryManager:
    """مدير سجل العمليات التاريخية للزبائن"""
    
    TRANSACTION_TYPES = {
        'weekly_visa': 'إضافة تأشيرة أسبوعية',
        'cash_withdrawal': 'سحب نقدي',
        'counter_reading': 'قراءة عداد',
        'discount': 'حسم',
        'balance_adjustment': 'تعديل رصيد',
        'visa_adjustment': 'تعديل تأشيرة',
        'initial_balance': 'رصيد ابتدائي',
        'manual_adjustment': 'تعديل يدوي',
        'customer_update': 'تحديث بيانات الزبون',
        'new_customer': 'زبون جديد',
        'delete_customer': 'حذف الزبون',
        'info_update': 'تحديث معلومات',
        'balance_adjustment': 'تعديل رصيد',
        'visa_adjustment': 'تعديل تأشيرة',
        'soft_delete': 'حذف ناعم',
        'hard_delete': 'حذف فعلي',
        'bulk_delete': 'حذف جماعي',
        'sector_delete': 'حذف قطاعي'
    }
    
    def _safe_format_number(self, value, default=0.0):
        """تنسيق الأرقام بشكل آمن"""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def log_transaction(self, 
                       customer_id: int,
                       transaction_type: str,
                       old_value: float = 0,
                       new_value: float = 0,
                       amount: float = 0,
                       current_balance_after: float = 0,
                       notes: str = '',
                       created_by: int = None) -> Dict:
        """تسجيل عملية في السجل التاريخي"""
        
        try:
            with db.get_cursor() as cursor:
                cursor.execute('''
                    INSERT INTO customer_history 
                    (customer_id, transaction_type, old_value, new_value,
                     amount, current_balance_after, notes, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at
                ''', (
                    customer_id,
                    transaction_type,
                    old_value,
                    new_value,
                    amount,
                    current_balance_after,
                    notes,
                    created_by
                ))
                
                result = cursor.fetchone()
                
                logger.info(
                    f"تم تسجيل عملية تاريخية: {transaction_type} "
                    f"للزبون {customer_id}"
                )
                
                return {
                    'success': True,
                    'transaction_id': result['id'],
                    'created_at': result['created_at']
                }
                
        except Exception as e:
            logger.error(f"خطأ في تسجيل العملية التاريخية: {e}")
            return {'success': False, 'error': str(e)}
    
    def add_weekly_visa(self, 
                       customer_id: int,
                       visa_amount: float,
                       notes: str = '',
                       user_id: int = None) -> Dict:
        """إضافة تأشيرة أسبوعية للزبون"""
        
        try:
            with db.get_cursor() as cursor:
                # 1. جلب بيانات الزبون الحالية
                cursor.execute('''
                    SELECT visa_balance, current_balance
                    FROM customers 
                    WHERE id = %s
                    FOR UPDATE
                ''', (customer_id,))
                
                customer = cursor.fetchone()
                if not customer:
                    return {'success': False, 'error': 'الزبون غير موجود'}
                
                old_visa = float(customer['visa_balance'] or 0)
                old_balance = float(customer['current_balance'] or 0)
                
                # 2. حساب القيم الجديدة
                new_visa = old_visa + visa_amount
                new_balance = old_balance + visa_amount
                
                # 3. تحديث بيانات الزبون
                cursor.execute('''
                    UPDATE customers 
                    SET visa_balance = %s,
                        current_balance = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id
                ''', (new_visa, new_balance, customer_id))
                
                # 4. تسجيل العملية في السجل التاريخي
                history_result = self.log_transaction(
                    customer_id=customer_id,
                    transaction_type='weekly_visa',
                    old_value=old_visa,
                    new_value=new_visa,
                    amount=visa_amount,
                    current_balance_after=new_balance,
                    notes=f"{notes} - إضافة تأشيرة أسبوعية: {visa_amount:,.0f}",
                    created_by=user_id
                )
                
                if not history_result['success']:
                    cursor.execute("ROLLBACK")
                    return history_result
                
                return {
                    'success': True,
                    'customer_id': customer_id,
                    'old_visa': old_visa,
                    'new_visa': new_visa,
                    'old_balance': old_balance,
                    'new_balance': new_balance,
                    'amount': visa_amount,
                    'transaction_id': history_result.get('transaction_id'),
                    'message': f'تم إضافة تأشيرة أسبوعية: {visa_amount:,.0f}'
                }
                
        except Exception as e:
            logger.error(f"خطأ في إضافة التأشيرة الأسبوعية: {e}")
            return {'success': False, 'error': str(e)}
    
    def add_cash_withdrawal(self,
                          customer_id: int,
                          withdrawal_amount: float,
                          notes: str = '',
                          user_id: int = None) -> Dict:
        """إضافة سحب نقدي للزبون"""
        
        try:
            with db.get_cursor() as cursor:
                # 1. جلب بيانات الزبون الحالية
                cursor.execute('''
                    SELECT withdrawal_amount, current_balance
                    FROM customers 
                    WHERE id = %s
                    FOR UPDATE
                ''', (customer_id,))
                
                customer = cursor.fetchone()
                if not customer:
                    return {'success': False, 'error': 'الزبون غير موجود'}
                
                old_withdrawal = float(customer['withdrawal_amount'] or 0)
                old_balance = float(customer['current_balance'] or 0)
                
                # 2. حساب القيم الجديدة
                new_withdrawal = old_withdrawal + withdrawal_amount
                new_balance = old_balance - withdrawal_amount  # السحب يقلل الرصيد
                
                # 3. تحديث بيانات الزبون
                cursor.execute('''
                    UPDATE customers 
                    SET withdrawal_amount = %s,
                        current_balance = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id
                ''', (new_withdrawal, new_balance, customer_id))
                
                # 4. تسجيل العملية في السجل التاريخي
                history_result = self.log_transaction(
                    customer_id=customer_id,
                    transaction_type='cash_withdrawal',
                    old_value=old_withdrawal,
                    new_value=new_withdrawal,
                    amount=withdrawal_amount,
                    current_balance_after=new_balance,
                    notes=f"{notes} - سحب نقدي: {withdrawal_amount:,.0f}",
                    created_by=user_id
                )
                
                if not history_result['success']:
                    cursor.execute("ROLLBACK")
                    return history_result
                
                return {
                    'success': True,
                    'customer_id': customer_id,
                    'old_withdrawal': old_withdrawal,
                    'new_withdrawal': new_withdrawal,
                    'old_balance': old_balance,
                    'new_balance': new_balance,
                    'amount': withdrawal_amount,
                    'transaction_id': history_result.get('transaction_id'),
                    'message': f'تم إضافة سحب نقدي: {withdrawal_amount:,.0f}'
                }
                
        except Exception as e:
            logger.error(f"خطأ في إضافة السحب النقدي: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_counter_reading(self,
                             customer_id: int,
                             new_reading: float,
                             notes: str = '',
                             user_id: int = None) -> Dict:
        """تحديث قراءة العداد"""
        
        try:
            with db.get_cursor() as cursor:
                # 1. جلب بيانات الزبون الحالية
                cursor.execute('''
                    SELECT last_counter_reading, current_balance
                    FROM customers 
                    WHERE id = %s
                    FOR UPDATE
                ''', (customer_id,))
                
                customer = cursor.fetchone()
                if not customer:
                    return {'success': False, 'error': 'الزبون غير موجود'}
                
                old_reading = float(customer['last_counter_reading'] or 0)
                current_balance = float(customer['current_balance'] or 0)
                
                if new_reading < old_reading:
                    return {
                        'success': False,
                        'error': 'القراءة الجديدة أقل من القراءة السابقة'
                    }
                
                # 2. تحديث بيانات الزبون
                cursor.execute('''
                    UPDATE customers 
                    SET last_counter_reading = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id, current_balance
                ''', (new_reading, customer_id))
                
                updated_customer = cursor.fetchone()
                if updated_customer:
                    current_balance = float(updated_customer['current_balance'] or 0)
                
                # 3. تسجيل العملية في السجل التاريخي
                history_result = self.log_transaction(
                    customer_id=customer_id,
                    transaction_type='counter_reading',
                    old_value=old_reading,
                    new_value=new_reading,
                    amount=new_reading - old_reading,  # كمية الاستهلاك
                    current_balance_after=current_balance,
                    notes=f"{notes} - تحديث قراءة العداد: {old_reading:,.0f} → {new_reading:,.0f}",
                    created_by=user_id
                )
                
                if not history_result['success']:
                    cursor.execute("ROLLBACK")
                    return history_result
                
                return {
                    'success': True,
                    'customer_id': customer_id,
                    'old_reading': old_reading,
                    'new_reading': new_reading,
                    'consumption': new_reading - old_reading,
                    'current_balance': current_balance,
                    'transaction_id': history_result.get('transaction_id'),
                    'message': f'تم تحديث قراءة العداد: {old_reading:,.0f} → {new_reading:,.0f}'
                }
                
        except Exception as e:
            logger.error(f"خطأ في تحديث قراءة العداد: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_customer_history(self, 
                           customer_id: int,
                           limit: int = 100,
                           offset: int = 0) -> Dict:
        """جلب السجل التاريخي للزبون"""
        
        try:
            with db.get_cursor() as cursor:
                # 1. جلب إجمالي عدد السجلات
                cursor.execute('''
                    SELECT COUNT(*) as total_count
                    FROM customer_history
                    WHERE customer_id = %s
                ''', (customer_id,))
                
                total = cursor.fetchone()['total_count']
                
                # 2. جلب السجلات
                cursor.execute('''
                    SELECT 
                        h.id,
                        h.transaction_type,
                        h.old_value,
                        h.new_value,
                        h.amount,
                        h.current_balance_after,
                        h.notes,
                        h.created_at,
                        u.full_name as created_by_name
                    FROM customer_history h
                    LEFT JOIN users u ON h.created_by = u.id
                    WHERE h.customer_id = %s
                    ORDER BY h.created_at DESC
                    LIMIT %s OFFSET %s
                ''', (customer_id, limit, offset))
                
                history = cursor.fetchall()
                
                # 3. تحويل الأرقام وتنسيق البيانات
                formatted_history = []
                for record in history:
                    formatted_record = dict(record)
                    
                    # تحويل القيم الرقمية بشكل آمن
                    formatted_record['old_value'] = self._safe_format_number(formatted_record['old_value'])
                    formatted_record['new_value'] = self._safe_format_number(formatted_record['new_value'])
                    formatted_record['amount'] = self._safe_format_number(formatted_record['amount'])
                    formatted_record['current_balance_after'] = self._safe_format_number(formatted_record['current_balance_after'])
                    
                    # تنسيق نوع العملية
                    transaction_type = formatted_record['transaction_type']
                    formatted_record['transaction_type_arabic'] = \
                        self.TRANSACTION_TYPES.get(transaction_type, transaction_type)
                    
                    # تنسيق التواريخ
                    if formatted_record['created_at']:
                        formatted_record['created_at_formatted'] = \
                            formatted_record['created_at'].strftime('%Y-%m-%d %H:%M')
                    else:
                        formatted_record['created_at_formatted'] = ''
                    
                    formatted_history.append(formatted_record)
                
                return {
                    'success': True,
                    'customer_id': customer_id,
                    'history': formatted_history,
                    'total_count': total,
                    'limit': limit,
                    'offset': offset
                }
                
        except Exception as e:
            logger.error(f"خطأ في جلب السجل التاريخي: {e}")
            return {'success': False, 'error': str(e)}
        
    def get_history_summary(self, customer_id: int) -> Dict:
        """جلب ملخص السجل التاريخي للزبون"""
        
        try:
            with db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_transactions,
                        COALESCE(SUM(CASE WHEN transaction_type = 'weekly_visa' THEN amount ELSE 0 END), 0) as total_visa,
                        COALESCE(SUM(CASE WHEN transaction_type = 'cash_withdrawal' THEN amount ELSE 0 END), 0) as total_withdrawal,
                        MIN(created_at) as first_transaction,
                        MAX(created_at) as last_transaction
                    FROM customer_history
                    WHERE customer_id = %s
                ''', (customer_id,))
                
                result = cursor.fetchone()
                
                if result:
                    summary = dict(result)
                    
                    # استخدام _safe_format_number للقيم الرقمية
                    summary['total_visa'] = self._safe_format_number(summary.get('total_visa', 0))
                    summary['total_withdrawal'] = self._safe_format_number(summary.get('total_withdrawal', 0))
                    
                    # تنسيق التواريخ إذا كانت موجودة
                    if summary.get('first_transaction'):
                        summary['first_transaction'] = summary['first_transaction'].strftime('%Y-%m-%d %H:%M')
                    else:
                        summary['first_transaction'] = 'غير متوفر'
                        
                    if summary.get('last_transaction'):
                        summary['last_transaction'] = summary['last_transaction'].strftime('%Y-%m-%d %H:%M')
                    else:
                        summary['last_transaction'] = 'غير متوفر'
                    
                    return {
                        'success': True,
                        'customer_id': customer_id,
                        'summary': summary
                    }
                else:
                    return {
                        'success': True,
                        'customer_id': customer_id,
                        'summary': {
                            'total_transactions': 0,
                            'total_visa': 0,
                            'total_withdrawal': 0,
                            'first_transaction': 'غير متوفر',
                            'last_transaction': 'غير متوفر'
                        }
                    }
                    
        except Exception as e:
            logger.error(f"خطأ في جلب ملخص السجل: {e}")
            return {'success': False, 'error': str(e)}

    def process_visa_import(self, customer_id: int, visa_amount: float, 
                           notes: str = '', user_id: int = None) -> Dict:
        """معالجة تأشيرة مستوردة من ملف Excel"""
        
        try:
            with db.get_cursor() as cursor:
                # 1. جلب بيانات الزبون الحالية
                cursor.execute('''
                    SELECT current_balance, visa_balance
                    FROM customers 
                    WHERE id = %s
                    FOR UPDATE
                ''', (customer_id,))
                
                customer = cursor.fetchone()
                if not customer:
                    return {'success': False, 'error': 'الزبون غير موجود'}
                
                old_balance = float(customer['current_balance'] or 0)
                old_visa = float(customer['visa_balance'] or 0)
                
                # 2. حساب القيم الجديدة
                new_balance = old_balance + visa_amount
                new_visa = old_visa + visa_amount
                
                # 3. تحديث بيانات الزبون
                cursor.execute('''
                    UPDATE customers 
                    SET current_balance = %s,
                        visa_balance = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (new_balance, new_visa, customer_id))
                
                # 4. تسجيل العملية في السجل التاريخي
                history_result = self.log_transaction(
                    customer_id=customer_id,
                    transaction_type='weekly_visa',
                    old_value=old_visa,
                    new_value=new_visa,
                    amount=visa_amount,
                    current_balance_after=new_balance,
                    notes=f"استيراد تأشيرة من ملف Excel: {visa_amount:,.0f} | {notes}",
                    created_by=user_id
                )
                
                if not history_result['success']:
                    cursor.execute("ROLLBACK")
                    return history_result
                
                return {
                    'success': True,
                    'customer_id': customer_id,
                    'old_balance': old_balance,
                    'new_balance': new_balance,
                    'old_visa': old_visa,
                    'new_visa': new_visa,
                    'amount': visa_amount,
                    'transaction_id': history_result.get('transaction_id'),
                    'message': f'تم استيراد تأشيرة: {visa_amount:,.0f}'
                }
                
        except Exception as e:
            logger.error(f"خطأ في معالجة تأشيرة مستوردة: {e}")
            return {'success': False, 'error': str(e)}