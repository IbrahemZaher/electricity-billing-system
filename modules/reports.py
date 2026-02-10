# modules/reports.py - النسخة المحسنة
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from database.connection import db
import pandas as pd
import os

logger = logging.getLogger(__name__)


class ReportManager:
    """مدير عمليات التقارير والإحصائيات المحسّن"""

    def __init__(self):
        self.customer_manager = None

    def _get_customer_manager(self):
        """استيراد CustomerManager عند الحاجة"""
        if self.customer_manager is None:
            from modules.customers import CustomerManager
            self.customer_manager = CustomerManager()
        return self.customer_manager

    # ============== الوظائف القديمة من reports.py (الإصدار السابق) ==============

    def get_negative_balance_lists_report_old(self, financial_category: str = None, sector_id: int = None) -> Dict[str, Any]:
        """
        تقرير قوائم الكسر: الزبائن ذوو الرصيد السالب مرتبين من الأكبر إلى الأصغر لكل قطاع مع الفلترة.
        """
        from modules.customers import CustomerManager
        cm = CustomerManager()
        data = cm.get_negative_balance_customers_by_sector(financial_category=financial_category, sector_id=sector_id)
        # تجهيز ملخصات
        sectors_list = []
        total_count = 0
        total_balance = 0
        for sector, info in data.items():
            customers = info['customers']
            sectors_list.append({
                'sector_name': sector,
                'customers': customers,
                'count': len(customers),
                'total_negative_balance': sum(c['current_balance'] for c in customers)
            })
            total_count += len(customers)
            total_balance += sum(c['current_balance'] for c in customers)
        return {
            'sectors': sectors_list,
            'total': {
                'count': total_count,
                'total_negative_balance': total_balance
            },
            'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_cut_lists_report_old(self, min_balance: float = 0, max_balance: float = -1000, exclude_categories: list = None) -> Dict[str, Any]:
        """
        تقرير قوائم القطع: لكل علبة قائمة زبائنها ذوي الرصيد السالب ضمن مجال محدد مع استثناءات التصنيف المالي.
        """
        from modules.customers import CustomerManager
        cm = CustomerManager()
        data = cm.get_cut_lists_by_box(min_balance=min_balance, max_balance=max_balance, exclude_categories=exclude_categories)
        # تجهيز ملخصات
        boxes_list = []
        total_customers = 0
        for box_id, info in data.items():
            customers = info['customers']
            box_info = info['box_info']
            boxes_list.append({
                'box_id': box_id,
                'box_info': box_info,
                'customers': customers,
                'count': len(customers)
            })
            total_customers += len(customers)
        return {
            'boxes': boxes_list,
            'total_customers': total_customers,
            'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_free_customers_by_sector_report_old(self) -> Dict[str, Any]:
        """تقرير الزبائن المجانيين - نسخة مبسطة جداً"""
        try:
            with db.get_cursor() as cursor:
                # جلب الزبائن المجانيين فقط
                cursor.execute("""
                    SELECT 
                        c.name,
                        c.box_number,
                        c.current_balance,
                        c.withdrawal_amount,
                        c.visa_balance,
                        c.phone_number,
                        s.name as sector_name
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE (c.financial_category = 'free' OR c.financial_category = 'free_vip')
                    AND c.is_active = TRUE
                    ORDER BY s.name, c.name
                """)
                
                customers = cursor.fetchall()
                
                # تجميع حسب القطاع
                sectors_dict = {}
                for customer in customers:
                    sector = customer['sector_name'] or 'بدون قطاع'
                    if sector not in sectors_dict:
                        sectors_dict[sector] = []
                    
                    sectors_dict[sector].append({
                        'name': customer['name'],
                        'box_number': customer['box_number'],
                        'current_balance': customer['current_balance'],
                        'withdrawal_amount': customer['withdrawal_amount'],
                        'visa_balance': customer['visa_balance'],
                        'phone_number': customer['phone_number']
                    })
                
                # تحويل إلى الصيغة المطلوبة
                sectors_list = []
                total_free_count = 0
                total_balance = 0
                total_visa_balance = 0
                
                for sector_name, customers_list in sectors_dict.items():
                    sectors_list.append({
                        'sector_name': sector_name,
                        'customers': customers_list,
                        'free_count': len(customers_list),
                        'total_balance': sum(c['current_balance'] for c in customers_list),
                        'total_visa_balance': sum(c['visa_balance'] for c in customers_list)
                    })
                    
                    total_free_count += len(customers_list)
                    total_balance += sum(c['current_balance'] for c in customers_list)
                    total_visa_balance += sum(c['visa_balance'] for c in customers_list)
                
                return {
                    'sectors': sectors_list,
                    'total': {
                        'free_count': total_free_count,
                        'total_balance': total_balance,
                        'total_visa_balance': total_visa_balance
                    },
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
        except Exception as e:
            logger.error(f"خطأ في تقرير الزبائن المجانيين: {e}")
            return {
                'sectors': [],
                'total': {'free_count': 0, 'total_balance': 0, 'total_visa_balance': 0},
                'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    # ============== تقارير الزبائن القديمة ==============

    def get_customer_balance_report(self, balance_type: str = "all") -> Dict[str, Any]:
        """تقرير رصيد الزبائن
        balance_type: all, negative, positive, zero
        """
        try:
            with db.get_cursor() as cursor:
                query = """
                SELECT 
                    c.id,
                    c.name,
                    s.name as sector_name,
                    c.box_number,
                    c.serial_number,
                    c.current_balance,
                    c.phone_number,
                    c.last_counter_reading,
                    c.visa_balance,
                    c.withdrawal_amount,
                    CASE 
                        WHEN c.current_balance < 0 THEN 'سالب'
                        WHEN c.current_balance > 0 THEN 'موجب'
                        ELSE 'صفر'
                    END as balance_status
                FROM customers c
                LEFT JOIN sectors s ON c.sector_id = s.id
                WHERE c.is_active = TRUE
                """
                
                if balance_type == "negative":
                    query += " AND c.current_balance < 0"
                elif balance_type == "positive":
                    query += " AND c.current_balance > 0"
                elif balance_type == "zero":
                    query += " AND c.current_balance = 0"
                
                query += " ORDER BY c.current_balance"
                
                cursor.execute(query)
                customers = cursor.fetchall()
                
                # حساب الإجماليات
                total_balance = 0
                negative_total = 0
                positive_total = 0
                
                for customer in customers:
                    balance = customer['current_balance']
                    total_balance += balance
                    if balance < 0:
                        negative_total += balance
                    elif balance > 0:
                        positive_total += balance
                
                return {
                    'customers': [dict(c) for c in customers],
                    'total_count': len(customers),
                    'total_balance': total_balance,
                    'negative_total': negative_total,
                    'positive_total': positive_total,
                    'report_type': balance_type,
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
        except Exception as e:
            logger.error(f"خطأ في توليد تقرير الرصيد: {e}")
            return {'error': str(e)}

    def get_customers_by_sector_report(self) -> Dict[str, Any]:
        """تقرير توزيع الزبائن حسب القطاع"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                SELECT 
                    s.name as sector_name,
                    COUNT(c.id) as customer_count,
                    SUM(c.current_balance) as total_balance,
                    AVG(c.current_balance) as average_balance,
                    MIN(c.current_balance) as min_balance,
                    MAX(c.current_balance) as max_balance,
                    SUM(CASE WHEN c.current_balance < 0 THEN 1 ELSE 0 END) as negative_count,
                    SUM(CASE WHEN c.current_balance > 0 THEN 1 ELSE 0 END) as positive_count,
                    SUM(CASE WHEN c.current_balance = 0 THEN 1 ELSE 0 END) as zero_count
                FROM sectors s
                LEFT JOIN customers c ON s.id = c.sector_id AND c.is_active = TRUE
                GROUP BY s.id, s.name
                ORDER BY customer_count DESC
                """)
                
                sectors = cursor.fetchall()
                
                return {
                    'sectors': [dict(s) for s in sectors],
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
        except Exception as e:
            logger.error(f"خطأ في توليد تقرير القطاعات: {e}")
            return {'error': str(e)}

    # ============== تقارير المبيعات القديمة ==============

    def get_sales_report(self, start_date: str = None, end_date: str = None, 
                        group_by: str = 'daily') -> Dict[str, Any]:
        """تقرير المبيعات
        group_by: daily, monthly, yearly, sector
        """
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            
            with db.get_cursor() as cursor:
                # بناء الاستعلام حسب نوع التجميع
                if group_by == 'daily':
                    group_clause = "DATE(i.payment_date)"
                    select_fields = "DATE(i.payment_date) as period"
                elif group_by == 'monthly':
                    group_clause = "EXTRACT(YEAR FROM i.payment_date), EXTRACT(MONTH FROM i.payment_date)"
                    select_fields = "TO_CHAR(i.payment_date, 'YYYY-MM') as period"
                elif group_by == 'yearly':
                    group_clause = "EXTRACT(YEAR FROM i.payment_date)"
                    select_fields = "EXTRACT(YEAR FROM i.payment_date) as period"
                elif group_by == 'sector':
                    group_clause = "s.id"
                    select_fields = "s.name as period"
                
                query = f"""
                SELECT 
                    {select_fields},
                    COUNT(i.id) as invoice_count,
                    SUM(i.total_amount) as total_amount,
                    SUM(i.kilowatt_amount) as total_kilowatts,
                    SUM(i.free_kilowatt) as total_free,
                    SUM(i.discount) as total_discount,
                    AVG(i.total_amount) as average_amount,
                    MIN(i.total_amount) as min_amount,
                    MAX(i.total_amount) as max_amount
                FROM invoices i
                """
                
                if group_by == 'sector':
                    query += " LEFT JOIN sectors s ON i.sector_id = s.id"
                
                query += f"""
                WHERE i.payment_date BETWEEN %s AND %s
                GROUP BY {group_clause}
                ORDER BY period
                """
                
                cursor.execute(query, (start_date, end_date))
                sales_data = cursor.fetchall()
                
                # حساب الإجماليات
                cursor.execute("""
                SELECT 
                    COUNT(i.id) as total_invoices,
                    SUM(i.total_amount) as grand_total,
                    SUM(i.kilowatt_amount) as total_kilowatts,
                    SUM(i.free_kilowatt) as total_free,
                    SUM(i.discount) as total_discount
                FROM invoices i
                WHERE i.payment_date BETWEEN %s AND %s
                """, (start_date, end_date))
                
                totals = cursor.fetchone()
                
                return {
                    'period': {
                        'start_date': start_date,
                        'end_date': end_date
                    },
                    'group_by': group_by,
                    'sales_data': [dict(d) for d in sales_data],
                    'totals': dict(totals),
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
        except Exception as e:
            logger.error(f"خطأ في توليد تقرير المبيعات: {e}")
            return {'error': str(e)}

    def get_daily_sales_summary(self, date: str = None) -> Dict[str, Any]:
        """ملخص المبيعات اليومية"""
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            
            with db.get_cursor() as cursor:
                # بيانات اليوم
                cursor.execute("""
                SELECT 
                    COUNT(*) as invoice_count,
                    SUM(total_amount) as total_amount,
                    SUM(kilowatt_amount) as total_kilowatts,
                    SUM(free_kilowatt) as total_free,
                    SUM(discount) as total_discount,
                    AVG(total_amount) as average_amount
                FROM invoices
                WHERE payment_date = %s
                """, (date,))
                
                today = cursor.fetchone()
                
                # بيانات الأمس للمقارنة
                yesterday = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
                
                cursor.execute("""
                SELECT 
                    COUNT(*) as invoice_count,
                    SUM(total_amount) as total_amount
                FROM invoices
                WHERE payment_date = %s
                """, (yesterday,))
                
                yesterday_data = cursor.fetchone()
                
                # حساب نسبة التغير
                if yesterday_data and yesterday_data['total_amount']:
                    change_percentage = ((today['total_amount'] or 0) - yesterday_data['total_amount']) / yesterday_data['total_amount'] * 100
                else:
                    change_percentage = 0
                
                # أفضل 5 زبائن في اليوم
                cursor.execute("""
                SELECT 
                    c.name as customer_name,
                    s.name as sector_name,
                    COUNT(i.id) as invoice_count,
                    SUM(i.total_amount) as total_amount
                FROM invoices i
                LEFT JOIN customers c ON i.customer_id = c.id
                LEFT JOIN sectors s ON i.sector_id = s.id
                WHERE i.payment_date = %s
                GROUP BY c.id, c.name, s.name
                ORDER BY total_amount DESC
                LIMIT 5
                """, (date,))
                
                top_customers = cursor.fetchall()
                
                return {
                    'date': date,
                    'today': dict(today),
                    'yesterday': dict(yesterday_data),
                    'change_percentage': round(change_percentage, 2),
                    'top_customers': [dict(c) for c in top_customers],
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
        except Exception as e:
            logger.error(f"خطأ في توليد ملخص المبيعات اليومية: {e}")
            return {'error': str(e)}

    # ============== تقارير الفواتير القديمة ==============

    def get_invoice_detailed_report(self, start_date: str = None, end_date: str = None,
                                customer_id: int = None, sector_id: int = None) -> Dict[str, Any]:
        """تقرير تفصيلي للفواتير"""
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            
            with db.get_cursor() as cursor:
                query = """
                SELECT 
                    i.id,
                    i.invoice_number,
                    i.payment_date,
                    i.payment_time,
                    c.name as customer_name,
                    s.name as sector_name,
                    i.kilowatt_amount,
                    i.free_kilowatt,
                    i.price_per_kilo,
                    i.discount,
                    i.total_amount,
                    i.previous_reading,
                    i.new_reading,
                    i.current_balance,
                    u.full_name as accountant_name,
                    i.book_number,
                    i.receipt_number
                FROM invoices i
                LEFT JOIN customers c ON i.customer_id = c.id
                LEFT JOIN sectors s ON i.sector_id = s.id
                LEFT JOIN users u ON i.user_id = u.id
                WHERE i.payment_date BETWEEN %s AND %s
                """
                
                params = [start_date, end_date]
                
                if customer_id:
                    query += " AND i.customer_id = %s"
                    params.append(customer_id)
                
                if sector_id:
                    query += " AND i.sector_id = %s"
                    params.append(sector_id)
                
                query += " ORDER BY i.payment_date DESC, i.payment_time DESC"
                
                cursor.execute(query, params)
                invoices = cursor.fetchall()
                
                return {
                    'period': {
                        'start_date': start_date,
                        'end_date': end_date
                    },
                    'invoices': [dict(i) for i in invoices],
                    'total_count': len(invoices),
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
        except Exception as e:
            logger.error(f"خطأ في توليد تقرير الفواتير: {e}")
            return {'error': str(e)}

    # ============== التقارير الإحصائية القديمة ==============

    def get_dashboard_statistics(self) -> Dict[str, Any]:
        """إحصائيات لوحة التحكم"""
        try:
            with db.get_cursor() as cursor:
                # إجمالي الزبائن
                cursor.execute("SELECT COUNT(*) FROM customers WHERE is_active = TRUE")
                total_customers = cursor.fetchone()['count']
                
                # الفواتير اليوم
                today = datetime.now().strftime("%Y-%m-%d")
                cursor.execute("""
                SELECT COUNT(*) as count, COALESCE(SUM(total_amount), 0) as total
                FROM invoices WHERE payment_date = %s
                """, (today,))
                today_result = cursor.fetchone()
                
                # الفواتير الشهر
                first_day_of_month = datetime.now().replace(day=1).strftime("%Y-%m-%d")
                cursor.execute("""
                SELECT COUNT(*) as count, COALESCE(SUM(total_amount), 0) as total
                FROM invoices WHERE payment_date >= %s
                """, (first_day_of_month,))
                month_result = cursor.fetchone()
                
                # الرصيد السالب
                cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(current_balance), 0) as total
                FROM customers WHERE is_active = TRUE AND current_balance < 0
                """)
                negative_result = cursor.fetchone()
                
                # الرصيد الموجب
                cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(current_balance), 0) as total
                FROM customers WHERE is_active = TRUE AND current_balance > 0
                """)
                positive_result = cursor.fetchone()
                
                # أفضل القطاعات أداءً
                cursor.execute("""
                SELECT s.name, COUNT(i.id) as invoice_count, 
                    COALESCE(SUM(i.total_amount), 0) as total_amount
                FROM sectors s
                LEFT JOIN invoices i ON s.id = i.sector_id 
                    AND i.payment_date >= %s
                GROUP BY s.id, s.name
                ORDER BY total_amount DESC
                LIMIT 5
                """, (first_day_of_month,))
                top_sectors = cursor.fetchall()
                
                return {
                    'total_customers': total_customers,
                    'today_invoices': today_result['count'],
                    'today_amount': float(today_result['total']),
                    'month_invoices': month_result['count'],
                    'month_amount': float(month_result['total']),
                    'negative_count': negative_result['count'],
                    'negative_total': float(negative_result['total']),
                    'positive_count': positive_result['count'],
                    'positive_total': float(positive_result['total']),
                    'top_sectors': [dict(s) for s in top_sectors],
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
        except Exception as e:
            logger.error(f"خطأ في جلب إحصائيات لوحة التحكم: {e}")
            return self.get_sample_statistics()

    def get_sample_statistics(self) -> Dict[str, Any]:
        """إرجاع إحصائيات تجريبية في حالة الخطأ"""
        return {
            'total_customers': 150,
            'today_invoices': 25,
            'today_amount': 1250000,
            'month_invoices': 500,
            'month_amount': 25000000,
            'negative_count': 12,
            'negative_total': -50000,
            'positive_count': 138,
            'positive_total': 2550000,
            'top_sectors': [],
            'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # ============== الوظائف الجديدة المحسنة ==============

    def get_negative_balance_lists_report(
        self, 
        min_balance: float = None,
        max_balance: float = 0,
        exclude_categories: List[str] = None,
        include_meter_types: List[str] = None,
        sector_id: int = None,
        sort_by: str = "balance_desc"
    ) -> Dict[str, Any]:
        """
        تقرير قوائم الكسر المحسّن مع خيارات ديناميكية متعددة
        
        Args:
            min_balance: الحد الأدنى للرصيد (سالب)
            max_balance: الحد الأقصى للرصيد (سالب، الافتراضي 0)
            exclude_categories: قائمة التصنيفات المالية المستثناة
            include_meter_types: قائمة أنواع العدادات المطلوبة
            sector_id: رقم القطاع المحدد
            sort_by: طريقة الترتيب (balance_desc, balance_asc, name)
        """
        try:
            # القيم الافتراضية
            if min_balance is None:
                min_balance = -1000000  # قيمة كبيرة جداً لاستيعاب كل القيم
            
            if exclude_categories is None:
                exclude_categories = []
            
            if include_meter_types is None:
                include_meter_types = ["زبون"]  # فقط الزبائن افتراضياً
            
            with db.get_cursor() as cursor:
                query = """
                    SELECT 
                        s.name as sector_name,
                        s.id as sector_id,
                        c.id as customer_id,
                        c.name as customer_name,
                        c.box_number,
                        c.serial_number,
                        c.current_balance,
                        c.withdrawal_amount,
                        c.visa_balance,
                        c.financial_category,
                        c.phone_number,
                        c.meter_type,
                        c.last_counter_reading,
                        c.parent_meter_id,
                        parent.name as parent_name,
                        parent.box_number as parent_box_number
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    LEFT JOIN customers parent ON c.parent_meter_id = parent.id
                    WHERE c.is_active = TRUE
                    AND c.current_balance < 0
                    AND c.current_balance BETWEEN %s AND %s
                """
                
                params = [min_balance, max_balance]
                
                # فلترة حسب القطاع
                if sector_id:
                    query += " AND c.sector_id = %s"
                    params.append(sector_id)
                
                # فلترة حسب التصنيفات المالية
                if exclude_categories:
                    placeholders = ', '.join(['%s'] * len(exclude_categories))
                    query += f" AND c.financial_category NOT IN ({placeholders})"
                    params.extend(exclude_categories)
                
                # فلترة حسب أنواع العدادات
                if include_meter_types:
                    placeholders = ', '.join(['%s'] * len(include_meter_types))
                    query += f" AND c.meter_type IN ({placeholders})"
                    params.extend(include_meter_types)
                
                # إضافة الترتيب
                if sort_by == "balance_desc":
                    query += " ORDER BY c.current_balance ASC"  # ASC لأن الرصيد سالب (-1000 < -100)
                elif sort_by == "balance_asc":
                    query += " ORDER BY c.current_balance DESC"
                elif sort_by == "name":
                    query += " ORDER BY c.name"
                else:
                    query += " ORDER BY s.name, c.current_balance ASC"
                
                cursor.execute(query, params)
                customers = cursor.fetchall()
                
                # تجميع حسب القطاع
                sectors_dict = {}
                for customer in customers:
                    sector = customer['sector_name'] or 'بدون قطاع'
                    sector_id_val = customer['sector_id']
                    
                    if sector not in sectors_dict:
                        sectors_dict[sector] = {
                            'sector_id': sector_id_val,
                            'customers': [],
                            'total_balance': 0,
                            'total_withdrawal': 0,
                            'total_visa': 0,
                            'customer_count': 0
                        }
                    
                    # حساب رصيد الجديد بعد السحب والتأشيرة
                    new_balance = customer['current_balance']
                    withdrawal = customer['withdrawal_amount'] or 0
                    visa = customer['visa_balance'] or 0
                    # الرصيد الجديد = الرصيد الحالي - السحب + التأشيرة
                    calculated_new_balance = new_balance - withdrawal + visa
                    
                    customer_dict = {
                        'id': customer['customer_id'],
                        'name': customer['customer_name'],
                        'box_number': customer['box_number'],
                        'serial_number': customer['serial_number'],
                        'current_balance': float(new_balance),
                        'withdrawal_amount': float(withdrawal),
                        'visa_balance': float(visa),
                        'calculated_new_balance': float(calculated_new_balance),
                        'financial_category': customer['financial_category'],
                        'phone_number': customer['phone_number'],
                        'meter_type': customer['meter_type'],
                        'last_counter_reading': customer['last_counter_reading'],
                        'parent_info': f"{customer.get('parent_name', '')} ({customer.get('parent_box_number', '')})"
                    }
                    
                    sectors_dict[sector]['customers'].append(customer_dict)
                    sectors_dict[sector]['total_balance'] += new_balance
                    sectors_dict[sector]['total_withdrawal'] += withdrawal
                    sectors_dict[sector]['total_visa'] += visa
                    sectors_dict[sector]['customer_count'] += 1
                
                # تحويل إلى قائمة
                sectors_list = []
                grand_total = {
                    'customer_count': 0,
                    'total_balance': 0,
                    'total_withdrawal': 0,
                    'total_visa': 0,
                    'total_calculated_balance': 0
                }
                
                for sector_name, data in sectors_dict.items():
                    if data['customers']:  # فقط القطاعات التي بها زبائن
                        sectors_list.append({
                            'sector_name': sector_name,
                            'sector_id': data['sector_id'],
                            'customers': data['customers'],
                            'customer_count': data['customer_count'],
                            'total_balance': data['total_balance'],
                            'total_withdrawal': data['total_withdrawal'],
                            'total_visa': data['total_visa'],
                            'total_calculated_balance': data['total_balance'] - data['total_withdrawal'] + data['total_visa']
                        })
                        
                        grand_total['customer_count'] += data['customer_count']
                        grand_total['total_balance'] += data['total_balance']
                        grand_total['total_withdrawal'] += data['total_withdrawal']
                        grand_total['total_visa'] += data['total_visa']
                        grand_total['total_calculated_balance'] += (data['total_balance'] - data['total_withdrawal'] + data['total_visa'])
                
                # حساب المتوسطات
                if grand_total['customer_count'] > 0:
                    grand_total['average_balance'] = grand_total['total_balance'] / grand_total['customer_count']
                    grand_total['average_withdrawal'] = grand_total['total_withdrawal'] / grand_total['customer_count']
                    grand_total['average_visa'] = grand_total['total_visa'] / grand_total['customer_count']
                else:
                    grand_total.update({
                        'average_balance': 0,
                        'average_withdrawal': 0,
                        'average_visa': 0
                    })
                
                return {
                    'sectors': sectors_list,
                    'grand_total': grand_total,
                    'filters': {
                        'min_balance': min_balance,
                        'max_balance': max_balance,
                        'exclude_categories': exclude_categories,
                        'include_meter_types': include_meter_types,
                        'sector_id': sector_id,
                        'sort_by': sort_by
                    },
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'report_title': 'تقرير قوائم الكسر المحسّن'
                }
                
        except Exception as e:
            logger.error(f"خطأ في تقرير قوائم الكسر: {e}", exc_info=True)
            return {
                'sectors': [],
                'grand_total': {
                    'customer_count': 0,
                    'total_balance': 0,
                    'total_withdrawal': 0,
                    'total_visa': 0,
                    'total_calculated_balance': 0
                },
                'filters': {},
                'error': str(e),
                'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    def get_cut_lists_report(
        self,
        min_balance: float = None,
        max_balance: float = 0,
        exclude_categories: List[str] = None,
        exclude_free: bool = True,
        exclude_vip: bool = True,
        only_meter_type: str = "زبون",
        box_id: int = None,
        sort_by: str = "balance_asc"
    ) -> Dict[str, Any]:
        """
        تقرير قوائم القطع المحسّن مع خيارات ديناميكية متقدمة
        
        Args:
            min_balance: الحد الأدنى للرصيد للقطع (سالب)
            max_balance: الحد الأقصى للرصيد للقطع (سالب)
            exclude_categories: تصنيفات مالية مستثناة
            exclude_free: استبعاد الزبائن المجانيين
            exclude_vip: استبعاد زبائن VIP
            only_meter_type: نوع العداد المطلوب (افتراضي: زبون)
            box_id: رقم علبة محددة
            sort_by: طريقة الترتيب
        """
        try:
            # القيم الافتراضية
            if min_balance is None:
                min_balance = -1000
            
            if max_balance is None:
                max_balance = 0
            
            if exclude_categories is None:
                exclude_categories = []
            
            # إضافة free و vip إذا كان الاستبعاد مفعلاً
            if exclude_free and 'free' not in exclude_categories:
                exclude_categories.extend(['free', 'free_vip'])
            
            if exclude_vip and 'vip' not in exclude_categories:
                exclude_categories.extend(['vip', 'free_vip'])
            
            with db.get_cursor() as cursor:
                # جلب جميع العلب (المولدات، علب التوزيع، الرئيسية)
                query_boxes = """
                    SELECT 
                        c.id as box_id,
                        c.name as box_name,
                        c.box_number,
                        c.meter_type as box_type,
                        c.sector_id,
                        s.name as sector_name,
                        COUNT(child.id) as total_customers_count,
                        COALESCE(SUM(CASE WHEN child.current_balance < 0 THEN 1 ELSE 0 END), 0) as negative_customers_count
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    LEFT JOIN customers child ON child.parent_meter_id = c.id 
                        AND child.is_active = TRUE
                        AND child.current_balance < 0
                    WHERE c.is_active = TRUE
                    AND c.meter_type IN ('مولدة', 'علبة توزيع', 'رئيسية')
                """
                
                box_params = []
                
                if box_id:
                    query_boxes += " AND c.id = %s"
                    box_params.append(box_id)
                
                query_boxes += """
                    GROUP BY c.id, c.name, c.box_number, c.meter_type, c.sector_id, s.name
                    ORDER BY c.meter_type, c.name
                """
                
                cursor.execute(query_boxes, box_params)
                boxes = cursor.fetchall()
                
                boxes_list = []
                grand_total = {
                    'total_boxes': 0,
                    'total_customers': 0,
                    'total_balance': 0,
                    'total_withdrawal': 0,
                    'total_visa': 0,
                    'total_calculated_balance': 0
                }
                
                for box in boxes:
                    box_id = box['box_id']
                    
                    # جلب الزبائن التابعين لهذه العلبة مع الفلاتر
                    query_customers = """
                        SELECT 
                            c.id,
                            c.name,
                            c.box_number,
                            c.serial_number,
                            c.current_balance,
                            c.withdrawal_amount,
                            c.visa_balance,
                            c.financial_category,
                            c.phone_number,
                            c.meter_type,
                            c.last_counter_reading
                        FROM customers c
                        WHERE c.parent_meter_id = %s
                        AND c.is_active = TRUE
                        AND c.current_balance BETWEEN %s AND %s
                        AND c.meter_type = %s
                    """
                    
                    customer_params = [box_id, min_balance, max_balance, only_meter_type]
                    
                    # فلترة حسب التصنيفات المالية
                    if exclude_categories:
                        placeholders = ', '.join(['%s'] * len(exclude_categories))
                        query_customers += f" AND c.financial_category NOT IN ({placeholders})"
                        customer_params.extend(exclude_categories)
                    
                    # إضافة الترتيب
                    if sort_by == "balance_asc":
                        query_customers += " ORDER BY c.current_balance ASC"
                    elif sort_by == "balance_desc":
                        query_customers += " ORDER BY c.current_balance DESC"
                    elif sort_by == "name":
                        query_customers += " ORDER BY c.name"
                    else:
                        query_customers += " ORDER BY c.current_balance ASC"
                    
                    cursor.execute(query_customers, customer_params)
                    customers = cursor.fetchall()
                    
                    if customers:  # فقط العلب التي بها زبائن ضمن الشروط
                        customers_list = []
                        box_total_balance = 0
                        box_total_withdrawal = 0
                        box_total_visa = 0
                        
                        for customer in customers:
                            balance = float(customer['current_balance'])
                            withdrawal = float(customer['withdrawal_amount'] or 0)
                            visa = float(customer['visa_balance'] or 0)
                            calculated_new_balance = balance - withdrawal + visa
                            
                            customer_dict = {
                                'id': customer['id'],
                                'name': customer['name'],
                                'box_number': customer['box_number'],
                                'serial_number': customer['serial_number'],
                                'current_balance': balance,
                                'withdrawal_amount': withdrawal,
                                'visa_balance': visa,
                                'calculated_new_balance': calculated_new_balance,
                                'financial_category': customer['financial_category'],
                                'phone_number': customer['phone_number'],
                                'meter_type': customer['meter_type'],
                                'last_counter_reading': customer['last_counter_reading']
                            }
                            
                            customers_list.append(customer_dict)
                            box_total_balance += balance
                            box_total_withdrawal += withdrawal
                            box_total_visa += visa
                        
                        box_info = {
                            'box_id': box['box_id'],
                            'box_name': box['box_name'],
                            'box_number': box['box_number'],
                            'box_type': box['box_type'],
                            'sector_name': box['sector_name'],
                            'sector_id': box['sector_id'],
                            'total_customers_count': box['total_customers_count'],
                            'negative_customers_count': box['negative_customers_count'],
                            'customers': customers_list,
                            'filtered_customer_count': len(customers_list),
                            'box_total_balance': box_total_balance,
                            'box_total_withdrawal': box_total_withdrawal,
                            'box_total_visa': box_total_visa,
                            'box_calculated_balance': box_total_balance - box_total_withdrawal + box_total_visa
                        }
                        
                        boxes_list.append(box_info)
                        
                        # تحديث الإجماليات
                        grand_total['total_boxes'] += 1
                        grand_total['total_customers'] += len(customers_list)
                        grand_total['total_balance'] += box_total_balance
                        grand_total['total_withdrawal'] += box_total_withdrawal
                        grand_total['total_visa'] += box_total_visa
                        grand_total['total_calculated_balance'] += (box_total_balance - box_total_withdrawal + box_total_visa)
                
                # حساب المتوسطات
                if grand_total['total_boxes'] > 0:
                    grand_total['average_customers_per_box'] = grand_total['total_customers'] / grand_total['total_boxes']
                    grand_total['average_balance_per_box'] = grand_total['total_balance'] / grand_total['total_boxes']
                    grand_total['average_balance_per_customer'] = grand_total['total_balance'] / max(grand_total['total_customers'], 1)
                
                return {
                    'boxes': boxes_list,
                    'grand_total': grand_total,
                    'filters': {
                        'min_balance': min_balance,
                        'max_balance': max_balance,
                        'exclude_categories': exclude_categories,
                        'exclude_free': exclude_free,
                        'exclude_vip': exclude_vip,
                        'only_meter_type': only_meter_type,
                        'box_id': box_id,
                        'sort_by': sort_by
                    },
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'report_title': 'تقرير قوائم القطع المحسّن'
                }
                
        except Exception as e:
            logger.error(f"خطأ في تقرير قوائم القطع: {e}", exc_info=True)
            return {
                'boxes': [],
                'grand_total': {
                    'total_boxes': 0,
                    'total_customers': 0,
                    'total_balance': 0
                },
                'filters': {},
                'error': str(e),
                'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    # ============== دوال مساعدة للتقرير ==============

    def get_available_sectors(self) -> List[Dict]:
        """جلب جميع القطاعات المتاحة"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, name, code 
                    FROM sectors 
                    WHERE is_active = TRUE 
                    ORDER BY name
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"خطأ في جلب القطاعات: {e}")
            return []

    def get_available_boxes(self, box_type: str = None) -> List[Dict]:
        """جلب جميع العلب المتاحة"""
        try:
            with db.get_cursor() as cursor:
                query = """
                    SELECT id, name, box_number, meter_type, sector_id 
                    FROM customers 
                    WHERE is_active = TRUE 
                    AND meter_type IN ('مولدة', 'علبة توزيع', 'رئيسية')
                """
                
                params = []
                if box_type:
                    query += " AND meter_type = %s"
                    params.append(box_type)
                
                query += " ORDER BY meter_type, name"
                cursor.execute(query, params)
                
                boxes = cursor.fetchall()
                
                # جلب أسماء القطاعات
                result = []
                for box in boxes:
                    box_dict = dict(box)
                    if box_dict['sector_id']:
                        cursor.execute("SELECT name FROM sectors WHERE id = %s", 
                                    (box_dict['sector_id'],))
                        sector = cursor.fetchone()
                        box_dict['sector_name'] = sector['name'] if sector else ''
                    else:
                        box_dict['sector_name'] = ''
                    
                    result.append(box_dict)
                
                return result
        except Exception as e:
            logger.error(f"خطأ في جلب العلب: {e}")
            return []

    def get_financial_categories(self) -> List[str]:
        """جلب جميع التصنيفات المالية المتاحة"""
        return ['normal', 'free', 'vip', 'free_vip']

    def get_meter_types(self) -> List[str]:
        """جلب جميع أنواع العدادات"""
        return ['مولدة', 'علبة توزيع', 'رئيسية', 'زبون']

    # ============== دوال التصدير ==============

    def export_negative_balance_report_to_excel(
        self, 
        report_data: Dict[str, Any],
        filename: str = None
    ) -> Tuple[bool, str]:
        """تصدير تقرير قوائم الكسر إلى Excel"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"قوائم_الكسر_{timestamp}.xlsx"
            
            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)
            filepath = os.path.join(export_dir, filename)
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # ورقة الإجماليات
                summary_data = []
                summary_data.append(['تقرير قوائم الكسر', report_data.get('report_title', '')])
                summary_data.append(['تاريخ الإنشاء', report_data.get('generated_at', '')])
                summary_data.append([''])
                summary_data.append(['الإجماليات:'])
                
                grand_total = report_data.get('grand_total', {})
                summary_data.append(['عدد الزبائن', f"{grand_total.get('customer_count', 0):,}"])
                summary_data.append(['إجمالي الرصيد', f"{grand_total.get('total_balance', 0):,.0f}"])
                summary_data.append(['إجمالي السحب', f"{grand_total.get('total_withdrawal', 0):,.0f}"])
                summary_data.append(['إجمالي التأشيرة', f"{grand_total.get('total_visa', 0):,.0f}"])
                summary_data.append(['الرصيد الجديد', f"{grand_total.get('total_calculated_balance', 0):,.0f}"])
                summary_data.append([''])
                
                # إضافة الفلاتر
                filters = report_data.get('filters', {})
                summary_data.append(['الفلاتر المطبقة:'])
                summary_data.append(['الحد الأدنى للرصيد', filters.get('min_balance', 'غير محدد')])
                summary_data.append(['الحد الأقصى للرصيد', filters.get('max_balance', 0)])
                summary_data.append(['التصنيفات المستثناة', ', '.join(filters.get('exclude_categories', [])) or 'لا يوجد'])
                summary_data.append(['أنواع العدادات', ', '.join(filters.get('include_meter_types', [])) or 'الكل'])
                
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='ملخص', index=False, header=False)
                
                # ورقة لكل قطاع
                for sector_data in report_data.get('sectors', []):
                    sector_name = sector_data['sector_name']
                    customers = sector_data.get('customers', [])
                    
                    if customers:
                        # تحضير البيانات
                        data_list = []
                        for customer in customers:
                            data_list.append([
                                customer['name'],
                                customer['box_number'],
                                customer['serial_number'],
                                customer['current_balance'],
                                customer['withdrawal_amount'],
                                customer['visa_balance'],
                                customer['calculated_new_balance'],
                                customer['financial_category'],
                                customer['meter_type'],
                                customer['phone_number'],
                                customer['parent_info']
                            ])
                        
                        # إنشاء DataFrame
                        columns = [
                            'اسم الزبون', 'رقم العلبة', 'رقم المسلسل',
                            'الرصيد الحالي', 'مبلغ السحب', 'رصيد التأشيرة',
                            'الرصيد الجديد', 'التصنيف المالي', 'نوع العداد',
                            'رقم الهاتف', 'العلبة الأم'
                        ]
                        
                        df_sector = pd.DataFrame(data_list, columns=columns)
                        
                        # إضافة صف الإجمالي
                        total_row = pd.DataFrame([[
                            f"إجمالي {sector_name}",
                            f"{sector_data['customer_count']} زبون",
                            '',
                            sector_data['total_balance'],
                            sector_data['total_withdrawal'],
                            sector_data['total_visa'],
                            sector_data['total_calculated_balance'],
                            '',
                            '',
                            '',
                            ''
                        ]], columns=columns)
                        
                        df_sector = pd.concat([df_sector, total_row], ignore_index=True)
                        
                        # حفظ في Excel (تحديد اسم الورقة)
                        sheet_name = sector_name[:31]  # Excel يسمح بحد أقصى 31 حرفاً
                        df_sector.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # تنسيق الأعمدة
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if cell.value and len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
            
            return True, filepath
            
        except Exception as e:
            logger.error(f"خطأ في تصدير تقرير الكسر: {e}")
            return False, str(e)

    def export_cut_lists_report_to_excel(
        self, 
        report_data: Dict[str, Any],
        filename: str = None
    ) -> Tuple[bool, str]:
        """تصدير تقرير قوائم القطع إلى Excel"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"قوائم_القطع_{timestamp}.xlsx"
            
            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)
            filepath = os.path.join(export_dir, filename)
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # ورقة الإجماليات
                summary_data = []
                summary_data.append(['تقرير قوائم القطع', report_data.get('report_title', '')])
                summary_data.append(['تاريخ الإنشاء', report_data.get('generated_at', '')])
                summary_data.append([''])
                summary_data.append(['الإجماليات:'])
                
                grand_total = report_data.get('grand_total', {})
                summary_data.append(['عدد العلب', f"{grand_total.get('total_boxes', 0):,}"])
                summary_data.append(['عدد الزبائن', f"{grand_total.get('total_customers', 0):,}"])
                summary_data.append(['إجمالي الرصيد', f"{grand_total.get('total_balance', 0):,.0f}"])
                summary_data.append(['إجمالي السحب', f"{grand_total.get('total_withdrawal', 0):,.0f}"])
                summary_data.append(['إجمالي التأشيرة', f"{grand_total.get('total_visa', 0):,.0f}"])
                summary_data.append(['الرصيد الجديد', f"{grand_total.get('total_calculated_balance', 0):,.0f}"])
                summary_data.append([''])
                
                # إضافة الفلاتر
                filters = report_data.get('filters', {})
                summary_data.append(['الفلاتر المطبقة:'])
                summary_data.append(['الحد الأدنى للرصيد', filters.get('min_balance', -1000)])
                summary_data.append(['الحد الأقصى للرصيد', filters.get('max_balance', 0)])
                summary_data.append(['استبعاد المجانيين', 'نعم' if filters.get('exclude_free') else 'لا'])
                summary_data.append(['استبعاد VIP', 'نعم' if filters.get('exclude_vip') else 'لا'])
                summary_data.append(['نوع العداد', filters.get('only_meter_type', 'زبون')])
                
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='ملخص', index=False, header=False)
                
                # ورقة لكل علبة
                for box_data in report_data.get('boxes', []):
                    box_name = box_data['box_name']
                    customers = box_data.get('customers', [])
                    
                    if customers:
                        # تحضير البيانات
                        data_list = []
                        for customer in customers:
                            data_list.append([
                                customer['name'],
                                customer['box_number'],
                                customer['serial_number'],
                                customer['current_balance'],
                                customer['withdrawal_amount'],
                                customer['visa_balance'],
                                customer['calculated_new_balance'],
                                customer['financial_category'],
                                customer['meter_type'],
                                customer['phone_number']
                            ])
                        
                        # إنشاء DataFrame
                        columns = [
                            'اسم الزبون', 'رقم العلبة', 'رقم المسلسل',
                            'الرصيد الحالي', 'مبلغ السحب', 'رصيد التأشيرة',
                            'الرصيد الجديد', 'التصنيف المالي', 'نوع العداد',
                            'رقم الهاتف'
                        ]
                        
                        df_box = pd.DataFrame(data_list, columns=columns)
                        
                        # إضافة صف الإجمالي
                        total_row = pd.DataFrame([[
                            f"إجمالي {box_name}",
                            f"{box_data['filtered_customer_count']} زبون",
                            '',
                            box_data['box_total_balance'],
                            box_data['box_total_withdrawal'],
                            box_data['box_total_visa'],
                            box_data['box_calculated_balance'],
                            '',
                            '',
                            ''
                        ]], columns=columns)
                        
                        df_box = pd.concat([df_box, total_row], ignore_index=True)
                        
                        # إضافة معلومات العلبة
                        info_rows = [
                            ['معلومات العلبة:'],
                            ['اسم العلبة', box_data['box_name']],
                            ['رقم العلبة', box_data['box_number']],
                            ['نوع العلبة', box_data['box_type']],
                            ['القطاع', box_data['sector_name']],
                            ['عدد الزبائن الكلي', box_data['total_customers_count']],
                            ['عدد الزبائن برصيد سالب', box_data['negative_customers_count']],
                            ['عدد الزبائن بعد الفلترة', box_data['filtered_customer_count']],
                            [''],
                            ['تفاصيل الزبائن:']
                        ]
                        
                        df_info = pd.DataFrame(info_rows)
                        
                        # حفظ في Excel
                        sheet_name = f"{box_name}_{box_data['box_number']}"[:31]
                        df_info.to_excel(writer, sheet_name=sheet_name, 
                                    index=False, header=False, startrow=0)
                        df_box.to_excel(writer, sheet_name=sheet_name, 
                                    index=False, startrow=len(info_rows))
                
                # تنسيق الأعمدة
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if cell.value and len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
            
            return True, filepath
            
        except Exception as e:
            logger.error(f"خطأ في تصدير تقرير القطع: {e}")
            return False, str(e)

    # ============== تصدير التقارير القديمة ==============

    def export_report_to_excel(self, report_data: Dict[str, Any], report_type: str) -> str:
        """تصدير التقرير إلى ملف Excel (للتوافق مع الوظائف القديمة)"""
        try:
            import pandas as pd
            import os
            
            # إنشاء مجلد التصدير إذا لم يكن موجوداً
            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)
            
            # اسم الملف
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{export_dir}/{report_type}_{timestamp}.xlsx"
            
            # تحويل البيانات إلى DataFrame
            df = pd.DataFrame()
            
            if 'customers' in report_data:
                df = pd.DataFrame(report_data['customers'])
            elif 'sales_data' in report_data:
                df = pd.DataFrame(report_data['sales_data'])
            elif 'invoices' in report_data:
                df = pd.DataFrame(report_data['invoices'])
            elif 'sectors' in report_data:
                df = pd.DataFrame(report_data['sectors'])
            
            # حفظ في Excel
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Report', index=False)
                
                # تنسيق الأعمدة
                worksheet = writer.sheets['Report']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            return filename
            
        except Exception as e:
            logger.error(f"خطأ في تصدير التقرير: {e}")
            return ""

    # ============== تقارير أخرى محسّنة ==============

    def get_free_customers_by_sector_report(
        self,
        include_vip: bool = True,
        sector_id: int = None
    ) -> Dict[str, Any]:
        """تقرير الزبائن المجانيين المحسّن"""
        try:
            with db.get_cursor() as cursor:
                # بناء الاستعلام
                categories = ["'free'"]
                if include_vip:
                    categories.append("'free_vip'")
                
                query = f"""
                    SELECT 
                        c.name,
                        c.box_number,
                        c.current_balance,
                        c.withdrawal_amount,
                        c.visa_balance,
                        c.phone_number,
                        c.financial_category,
                        c.meter_type,
                        c.last_counter_reading,
                        s.name as sector_name,
                        s.id as sector_id
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.financial_category IN ({','.join(categories)})
                    AND c.is_active = TRUE
                """
                
                params = []
                if sector_id:
                    query += " AND c.sector_id = %s"
                    params.append(sector_id)
                
                query += " ORDER BY s.name, c.name"
                
                cursor.execute(query, params)
                customers = cursor.fetchall()
                
                # تجميع حسب القطاع
                sectors_dict = {}
                for customer in customers:
                    sector = customer['sector_name'] or 'بدون قطاع'
                    if sector not in sectors_dict:
                        sectors_dict[sector] = []
                    
                    sectors_dict[sector].append({
                        'name': customer['name'],
                        'box_number': customer['box_number'],
                        'current_balance': customer['current_balance'],
                        'withdrawal_amount': customer['withdrawal_amount'],
                        'visa_balance': customer['visa_balance'],
                        'phone_number': customer['phone_number'],
                        'financial_category': customer['financial_category'],
                        'meter_type': customer['meter_type'],
                        'last_counter_reading': customer['last_counter_reading']
                    })
                
                # تحويل إلى الصيغة المطلوبة
                sectors_list = []
                total_free_count = 0
                total_balance = 0
                total_withdrawal = 0
                total_visa_balance = 0
                
                for sector_name, customers_list in sectors_dict.items():
                    sector_total_balance = sum(c['current_balance'] for c in customers_list)
                    sector_total_withdrawal = sum(c['withdrawal_amount'] for c in customers_list)
                    sector_total_visa = sum(c['visa_balance'] for c in customers_list)
                    
                    sectors_list.append({
                        'sector_name': sector_name,
                        'customers': customers_list,
                        'free_count': len(customers_list),
                        'total_balance': sector_total_balance,
                        'total_withdrawal': sector_total_withdrawal,
                        'total_visa_balance': sector_total_visa,
                        'calculated_balance': sector_total_balance - sector_total_withdrawal + sector_total_visa
                    })
                    
                    total_free_count += len(customers_list)
                    total_balance += sector_total_balance
                    total_withdrawal += sector_total_withdrawal
                    total_visa_balance += sector_total_visa
                
                return {
                    'sectors': sectors_list,
                    'total': {
                        'free_count': total_free_count,
                        'total_balance': total_balance,
                        'total_withdrawal': total_withdrawal,
                        'total_visa_balance': total_visa_balance,
                        'calculated_balance': total_balance - total_withdrawal + total_visa_balance
                    },
                    'filters': {
                        'include_vip': include_vip,
                        'sector_id': sector_id
                    },
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'report_title': 'تقرير الزبائن المجانيين المحسّن'
                }
                
        except Exception as e:
            logger.error(f"خطأ في تقرير الزبائن المجانيين: {e}")
            return {
                'sectors': [],
                'total': {'free_count': 0, 'total_balance': 0, 'total_visa_balance': 0},
                'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    # ============== واجهات للوظائف القديمة للحفاظ على التوافق ==============

    def get_negative_balance_lists_report_old_interface(self, financial_category: str = None, sector_id: int = None):
        """واجهة للدالة القديمة للحفاظ على التوافق"""
        return self.get_negative_balance_lists_report_old(financial_category, sector_id)

    def get_cut_lists_report_old_interface(self, min_balance: float = 0, max_balance: float = -1000, exclude_categories: list = None):
        """واجهة للدالة القديمة للحفاظ على التوافق"""
        return self.get_cut_lists_report_old(min_balance, max_balance, exclude_categories)

    def get_free_customers_by_sector_report_old_interface(self):
        """واجهة للدالة القديمة للحفاظ على التوافق"""
        return self.get_free_customers_by_sector_report_old()

    # إضافة دوال التصدير إلى Excel
def export_free_customers_to_excel(self, report_data: Dict[str, Any], filename: str = None) -> Tuple[bool, str]:
    """تصدير تقرير الزبائن المجانيين إلى Excel"""
    try:
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"الزبائن_المجانيين_{timestamp}.xlsx"
        
        export_dir = "exports"
        os.makedirs(export_dir, exist_ok=True)
        filepath = os.path.join(export_dir, filename)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # ورقة الإجماليات
            summary_data = []
            summary_data.append(['تقرير الزبائن المجانيين', report_data.get('report_title', '')])
            summary_data.append(['تاريخ الإنشاء', report_data.get('generated_at', '')])
            summary_data.append([''])
            summary_data.append(['الإجماليات:'])
            
            total = report_data.get('total', {})
            summary_data.append(['عدد الزبائن المجانيين', f"{total.get('free_count', 0):,}"])
            summary_data.append(['إجمالي الرصيد', f"{total.get('total_balance', 0):,.0f}"])
            summary_data.append(['إجمالي السحب', f"{total.get('total_withdrawal', 0):,.0f}"])
            summary_data.append(['إجمالي التأشيرة', f"{total.get('total_visa_balance', 0):,.0f}"])
            summary_data.append(['الرصيد الجديد', f"{total.get('calculated_balance', 0):,.0f}"])
            summary_data.append([''])
            
            # إضافة الفلاتر
            filters = report_data.get('filters', {})
            summary_data.append(['الفلاتر المطبقة:'])
            summary_data.append(['تضمين VIP', 'نعم' if filters.get('include_vip', True) else 'لا'])
            summary_data.append(['القطاع', filters.get('sector_id', 'الكل')])
            
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='ملخص', index=False, header=False)
            
            # ورقة لكل قطاع
            for sector_data in report_data.get('sectors', []):
                sector_name = sector_data['sector_name']
                customers = sector_data.get('customers', [])
                
                if customers:
                    # تحضير البيانات
                    data_list = []
                    for customer in customers:
                        data_list.append([
                            customer['name'],
                            customer['box_number'],
                            customer['current_balance'],
                            customer['withdrawal_amount'],
                            customer['visa_balance'],
                            customer['current_balance'] - customer['withdrawal_amount'] + customer['visa_balance'],
                            customer.get('financial_category', ''),
                            customer.get('meter_type', ''),
                            customer.get('phone_number', ''),
                            customer.get('last_counter_reading', '')
                        ])
                    
                    # إنشاء DataFrame
                    columns = [
                        'اسم الزبون', 'رقم العلبة', 'الرصيد الحالي', 
                        'مبلغ السحب', 'رصيد التأشيرة', 'الرصيد الجديد',
                        'التصنيف المالي', 'نوع العداد', 'رقم الهاتف', 'آخر قراءة'
                    ]
                    
                    df_sector = pd.DataFrame(data_list, columns=columns)
                    
                    # إضافة صف الإجمالي
                    total_row = pd.DataFrame([[
                        f"إجمالي {sector_name}",
                        f"{sector_data['free_count']} زبون",
                        sector_data['total_balance'],
                        sector_data['total_withdrawal'],
                        sector_data['total_visa_balance'],
                        sector_data['calculated_balance'],
                        '',
                        '',
                        '',
                        ''
                    ]], columns=columns)
                    
                    df_sector = pd.concat([df_sector, total_row], ignore_index=True)
                    
                    # حفظ في Excel
                    sheet_name = sector_name[:31]
                    df_sector.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # تنسيق الأعمدة
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if cell.value and len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        return True, filepath
        
    except Exception as e:
        logger.error(f"خطأ في تصدير تقرير الزبائن المجانيين: {e}")
        return False, str(e)

    def export_to_excel_generic(self, report_data: Dict[str, Any], report_type: str) -> Tuple[bool, str]:
        """دالة عامة لتصدير أي تقرير إلى Excel"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{report_type}_{timestamp}.xlsx"
            
            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)
            filepath = os.path.join(export_dir, filename)
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # تحديد نوع التقرير وتحويله إلى DataFrame
                if report_type == "sales":
                    if 'sales_data' in report_data:
                        df = pd.DataFrame(report_data['sales_data'])
                        df.to_excel(writer, sheet_name='المبيعات', index=False)
                    
                    if 'totals' in report_data:
                        totals_df = pd.DataFrame([report_data['totals']])
                        totals_df.to_excel(writer, sheet_name='الإجماليات', index=False)
                
                elif report_type == "invoices":
                    if 'invoices' in report_data:
                        df = pd.DataFrame(report_data['invoices'])
                        df.to_excel(writer, sheet_name='الفواتير', index=False)
                
                elif report_type == "dashboard":
                    # إنشاء ورقة للإحصائيات
                    stats_data = [
                        ['إجمالي الزبائن', report_data.get('total_customers', 0)],
                        ['فواتير اليوم', f"{report_data.get('today_invoices', 0)} - {report_data.get('today_amount', 0):,.0f} ك.و"],
                        ['فواتير الشهر', f"{report_data.get('month_invoices', 0)} - {report_data.get('month_amount', 0):,.0f} ك.و"],
                        ['زبائن برصيد سالب', f"{report_data.get('negative_count', 0)} - {report_data.get('negative_total', 0):,.0f} ك.و"],
                        ['زبائن برصيد موجب', f"{report_data.get('positive_count', 0)} - {report_data.get('positive_total', 0):,.0f} ك.و"],
                        ['', ''],
                        ['أفضل القطاعات أداءً:', '']
                    ]
                    
                    for sector in report_data.get('top_sectors', []):
                        stats_data.append([sector['name'], f"{sector['invoice_count']} فاتورة - {sector['total_amount']:,.0f} ك.و"])
                    
                    df = pd.DataFrame(stats_data)
                    df.to_excel(writer, sheet_name='الإحصائيات', index=False, header=False)
                
                # تنسيق الأعمدة
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if cell.value and len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
            
            return True, filepath
            
        except Exception as e:
            logger.error(f"خطأ في تصدير التقرير العام: {e}")
            return False, str(e)