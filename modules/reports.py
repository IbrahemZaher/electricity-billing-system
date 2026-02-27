# modules/reports.py - النسخة المحسنة (بدون عمود الرصيد الجديد + إضافة تقرير أوراق التأشيرات)
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
        if self.customer_manager is None:
            from modules.customers import CustomerManager
            self.customer_manager = CustomerManager()
        return self.customer_manager

    # ============== الوظائف القديمة من reports.py (الإصدار السابق) ==============

    def get_negative_balance_lists_report_old(self, financial_category: str = None, sector_id: int = None) -> Dict[str, Any]:
        from modules.customers import CustomerManager
        cm = CustomerManager()
        data = cm.get_negative_balance_customers_by_sector(financial_category=financial_category, sector_id=sector_id)
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
            'total': {'count': total_count, 'total_negative_balance': total_balance},
            'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_cut_lists_report_old(self, min_balance: float = 0, max_balance: float = -1000, exclude_categories: list = None) -> Dict[str, Any]:
        from modules.customers import CustomerManager
        cm = CustomerManager()
        data = cm.get_cut_lists_by_box(min_balance=min_balance, max_balance=max_balance, exclude_categories=exclude_categories)
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
        try:
            with db.get_cursor() as cursor:
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
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            with db.get_cursor() as cursor:
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
                    'period': {'start_date': start_date, 'end_date': end_date},
                    'group_by': group_by,
                    'sales_data': [dict(d) for d in sales_data],
                    'totals': dict(totals),
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        except Exception as e:
            logger.error(f"خطأ في توليد تقرير المبيعات: {e}")
            return {'error': str(e)}

    def get_daily_sales_summary(self, date: str = None) -> Dict[str, Any]:
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            with db.get_cursor() as cursor:
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
                yesterday = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
                cursor.execute("""
                SELECT 
                    COUNT(*) as invoice_count,
                    SUM(total_amount) as total_amount
                FROM invoices
                WHERE payment_date = %s
                """, (yesterday,))
                yesterday_data = cursor.fetchone()
                change_percentage = 0
                if yesterday_data and yesterday_data['total_amount']:
                    change_percentage = ((today['total_amount'] or 0) - yesterday_data['total_amount']) / yesterday_data['total_amount'] * 100
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
                    'period': {'start_date': start_date, 'end_date': end_date},
                    'invoices': [dict(i) for i in invoices],
                    'total_count': len(invoices),
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        except Exception as e:
            logger.error(f"خطأ في توليد تقرير الفواتير: {e}")
            return {'error': str(e)}

    # ============== التقارير الإحصائية القديمة ==============

    def get_dashboard_statistics(self) -> Dict[str, Any]:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM customers WHERE is_active = TRUE")
                total_customers = cursor.fetchone()['count']
                today = datetime.now().strftime("%Y-%m-%d")
                cursor.execute("""
                SELECT COUNT(*) as count, COALESCE(SUM(total_amount), 0) as total
                FROM invoices WHERE payment_date = %s
                """, (today,))
                today_result = cursor.fetchone()
                first_day_of_month = datetime.now().replace(day=1).strftime("%Y-%m-%d")
                cursor.execute("""
                SELECT COUNT(*) as count, COALESCE(SUM(total_amount), 0) as total
                FROM invoices WHERE payment_date >= %s
                """, (first_day_of_month,))
                month_result = cursor.fetchone()
                cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(current_balance), 0) as total
                FROM customers WHERE is_active = TRUE AND current_balance < 0
                """)
                negative_result = cursor.fetchone()
                cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(current_balance), 0) as total
                FROM customers WHERE is_active = TRUE AND current_balance > 0
                """)
                positive_result = cursor.fetchone()
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

    # ============== الوظائف الجديدة المحسنة (بدون الرصيد الجديد) ==============

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
        تقرير قوائم الكسر المحسّن - بدون حساب الرصيد الجديد
        """
        try:
            if min_balance is None:
                min_balance = -1000000
            if exclude_categories is None:
                exclude_categories = []
            if include_meter_types is None:
                include_meter_types = ["زبون"]
            
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
                if sector_id:
                    query += " AND c.sector_id = %s"
                    params.append(sector_id)
                if exclude_categories:
                    placeholders = ', '.join(['%s'] * len(exclude_categories))
                    query += f" AND c.financial_category NOT IN ({placeholders})"
                    params.extend(exclude_categories)
                if include_meter_types:
                    placeholders = ', '.join(['%s'] * len(include_meter_types))
                    query += f" AND c.meter_type IN ({placeholders})"
                    params.extend(include_meter_types)
                
                if sort_by == "balance_desc":
                    query += " ORDER BY c.current_balance ASC"
                elif sort_by == "balance_asc":
                    query += " ORDER BY c.current_balance DESC"
                elif sort_by == "name":
                    query += " ORDER BY c.name"
                else:
                    query += " ORDER BY s.name, c.current_balance ASC"
                
                cursor.execute(query, params)
                customers = cursor.fetchall()
                
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
                    
                    new_balance = customer['current_balance']
                    withdrawal = customer['withdrawal_amount'] or 0
                    visa = customer['visa_balance'] or 0
                    
                    # ❌ تم حذف calculated_new_balance نهائياً
                    customer_dict = {
                        'id': customer['customer_id'],
                        'name': customer['customer_name'],
                        'box_number': customer['box_number'],
                        'serial_number': customer['serial_number'],
                        'current_balance': float(new_balance),
                        'withdrawal_amount': float(withdrawal),
                        'visa_balance': float(visa),
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
                
                sectors_list = []
                grand_total = {
                    'customer_count': 0,
                    'total_balance': 0,
                    'total_withdrawal': 0,
                    'total_visa': 0,
                    # ❌ تم حذف total_calculated_balance
                }
                
                for sector_name, data in sectors_dict.items():
                    if data['customers']:
                        sectors_list.append({
                            'sector_name': sector_name,
                            'sector_id': data['sector_id'],
                            'customers': data['customers'],
                            'customer_count': data['customer_count'],
                            'total_balance': data['total_balance'],
                            'total_withdrawal': data['total_withdrawal'],
                            'total_visa': data['total_visa'],
                            # ❌ تم حذف total_calculated_balance
                        })
                        grand_total['customer_count'] += data['customer_count']
                        grand_total['total_balance'] += data['total_balance']
                        grand_total['total_withdrawal'] += data['total_withdrawal']
                        grand_total['total_visa'] += data['total_visa']
                
                if grand_total['customer_count'] > 0:
                    grand_total['average_balance'] = grand_total['total_balance'] / grand_total['customer_count']
                    grand_total['average_withdrawal'] = grand_total['total_withdrawal'] / grand_total['customer_count']
                    grand_total['average_visa'] = grand_total['total_visa'] / grand_total['customer_count']
                else:
                    grand_total.update({'average_balance': 0, 'average_withdrawal': 0, 'average_visa': 0})
                
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
                    # ❌ تم حذف total_calculated_balance
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
        only_meter_type: str = "زبون",
        box_id: int = None,          # للفلترة بمعرف علبة معينة
        sector_id: int = None,       # الفلترة حسب القطاع
        sort_by: str = "balance_asc"
    ) -> Dict[str, Any]:
        """
        تقرير قوائم القطع المحسّن - بدون حساب الرصيد الجديد
        """
        try:
            if min_balance is None:
                min_balance = -1000
            if max_balance is None:
                max_balance = 0
            if exclude_categories is None:
                exclude_categories = []
            
            with db.get_cursor() as cursor:
                # استعلام العلب الأم مع إمكانية فلترة حسب القطاع
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
                if sector_id:
                    query_boxes += " AND c.sector_id = %s"
                    box_params.append(sector_id)
                query_boxes += """
                    GROUP BY c.id, c.name, c.box_number, c.meter_type, c.sector_id, s.name
                    ORDER BY c.meter_type, c.name
                """
                cursor.execute(query_boxes, box_params)
                boxes = cursor.fetchall()
                
                # باقي الكود كما هو...
                
                boxes_list = []
                grand_total = {
                    'total_boxes': 0,
                    'total_customers': 0,
                    'total_balance': 0,
                    'total_withdrawal': 0,
                    'total_visa': 0,
                }
                
                for box in boxes:
                    box_id_val = box['box_id']
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
                    customer_params = [box_id_val, min_balance, max_balance, only_meter_type]
                    
                    if exclude_categories:
                        placeholders = ', '.join(['%s'] * len(exclude_categories))
                        query_customers += f" AND c.financial_category NOT IN ({placeholders})"
                        customer_params.extend(exclude_categories)
                    
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
                    
                    if customers:
                        customers_list = []
                        box_total_balance = 0
                        box_total_withdrawal = 0
                        box_total_visa = 0
                        
                        for customer in customers:
                            balance = float(customer['current_balance'])
                            withdrawal = float(customer['withdrawal_amount'] or 0)
                            visa = float(customer['visa_balance'] or 0)
                            
                            customer_dict = {
                                'id': customer['id'],
                                'name': customer['name'],
                                'box_number': customer['box_number'],
                                'serial_number': customer['serial_number'],
                                'current_balance': balance,
                                'withdrawal_amount': withdrawal,
                                'visa_balance': visa,
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
                        }
                        
                        boxes_list.append(box_info)
                        grand_total['total_boxes'] += 1
                        grand_total['total_customers'] += len(customers_list)
                        grand_total['total_balance'] += box_total_balance
                        grand_total['total_withdrawal'] += box_total_withdrawal
                        grand_total['total_visa'] += box_total_visa
                
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
                    'total_balance': 0,
                    'total_withdrawal': 0,
                    'total_visa': 0,
                },
                'filters': {},
                'error': str(e),
                'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    # ============== تقارير جديدة: أوراق التأشيرات ==============

    def get_visa_sheets_report(self, sector_id: int = None) -> Dict[str, Any]:
        """
        تقرير أوراق التأشيرات - عرض هرمي كامل (مولدة ← علب توزيع ← عدادات رئيسية ← زبائن)
        مع إدراج الزبائن الذين ليس لهم أب تحت عقدة "بدون أب".
        """
        try:
            with db.get_cursor() as cursor:
                # استعلام عودي لبناء الشجرة مع تحويل الأنواع لضمان التوافق
                query = """
                    WITH RECURSIVE meter_tree AS (
                        -- 1. العقد الجذرية: عدادات بدون أب (من الأنواع المسموح بها)
                        SELECT 
                            id,
                            name,
                            meter_type,
                            financial_category,
                            visa_balance,
                            box_number,
                            serial_number,
                            parent_meter_id,
                            sector_id,
                            0 AS level,
                            ARRAY[id] AS path,
                            ARRAY[name]::VARCHAR[] AS path_names,
                            ARRAY[meter_type]::VARCHAR[] AS path_types
                        FROM customers
                        WHERE is_active = TRUE
                        AND parent_meter_id IS NULL
                        AND meter_type IN ('مولدة', 'علبة توزيع', 'رئيسية')
                        AND (sector_id = %s OR %s IS NULL)
                        
                        UNION ALL
                        
                        -- 2. الأبناء المباشرون (عدادات فرعية أو زبائن)
                        SELECT 
                            c.id,
                            c.name,
                            c.meter_type,
                            c.financial_category,
                            c.visa_balance,
                            c.box_number,
                            c.serial_number,
                            c.parent_meter_id,
                            c.sector_id,
                            mt.level + 1,
                            mt.path || c.id,
                            (mt.path_names || c.name)::VARCHAR[],
                            (mt.path_types || c.meter_type)::VARCHAR[]
                        FROM customers c
                        INNER JOIN meter_tree mt ON c.parent_meter_id = mt.id
                        WHERE c.is_active = TRUE
                        AND c.meter_type IN ('علبة توزيع', 'رئيسية', 'زبون')
                    )
                    -- جلب جميع العقد مع اسم القطاع
                    SELECT 
                        mt.*,
                        s.name as sector_name
                    FROM meter_tree mt
                    LEFT JOIN sectors s ON mt.sector_id = s.id
                    ORDER BY 
                        COALESCE(s.name, 'بدون قطاع'), 
                        mt.path
                """
                params = [sector_id, sector_id]  # لشرط IS NULL
                cursor.execute(query, params)
                rows = cursor.fetchall()

                # ---- إضافة الزبائن الذين ليس لهم أب (لأنهم لم يدخلوا في العودية) ----
                extra_query = """
                    SELECT 
                        c.id,
                        c.name,
                        c.meter_type,
                        c.financial_category,
                        c.visa_balance,
                        c.box_number,
                        c.serial_number,
                        c.parent_meter_id,
                        c.sector_id,
                        0 AS level,
                        ARRAY[c.id] AS path,
                        ARRAY[c.name]::VARCHAR[] AS path_names,
                        ARRAY[c.meter_type]::VARCHAR[] AS path_types,
                        s.name as sector_name
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.is_active = TRUE
                    AND c.meter_type = 'زبون'
                    AND c.parent_meter_id IS NULL
                    AND (c.sector_id = %s OR %s IS NULL)
                """
                cursor.execute(extra_query, [sector_id, sector_id])
                extra_rows = cursor.fetchall()
                rows.extend(extra_rows)

            # بناء الشجرة في الذاكرة
            nodes_by_id = {}
            root_nodes = []

            for row in rows:
                node = dict(row)
                node['children'] = []
                nodes_by_id[node['id']] = node
                if node['parent_meter_id'] is None:
                    root_nodes.append(node)

            # ربط الأبناء بالآباء
            for node in nodes_by_id.values():
                parent_id = node['parent_meter_id']
                if parent_id and parent_id in nodes_by_id:
                    nodes_by_id[parent_id]['children'].append(node)

            # تجميع حسب القطاع
            sectors_dict = {}
            for root in root_nodes:
                sector_name = root.get('sector_name') or 'بدون قطاع'
                if sector_name not in sectors_dict:
                    sectors_dict[sector_name] = {
                        'sector_id': root['sector_id'],
                        'roots': [],
                        'total_customers': 0,
                        'total_visa': 0.0
                    }
                sectors_dict[sector_name]['roots'].append(root)

            # دالة مساعدة لحساب الإحصائيات
            def count_customers(node):
                if node['meter_type'] == 'زبون':
                    return 1, float(node['visa_balance'] or 0)
                total_c = 0
                total_v = 0.0
                for child in node['children']:
                    c, v = count_customers(child)
                    total_c += c
                    total_v += v
                return total_c, total_v

            for sector_data in sectors_dict.values():
                for root in sector_data['roots']:
                    c, v = count_customers(root)
                    sector_data['total_customers'] += c
                    sector_data['total_visa'] += v

            # ترتيب القطاعات أبجدياً
            sectors_list = []
            for sector_name in sorted(sectors_dict.keys()):
                data = sectors_dict[sector_name]
                sectors_list.append({
                    'sector_name': sector_name,
                    'sector_id': data['sector_id'],
                    'roots': data['roots'],
                    'total_customers': data['total_customers'],
                    'total_visa': data['total_visa']
                })

            grand_total = {
                'total_customers': sum(s['total_customers'] for s in sectors_list),
                'total_visa': sum(s['total_visa'] for s in sectors_list)
            }

            return {
                'sectors': sectors_list,
                'grand_total': grand_total,
                'filters': {'sector_id': sector_id},
                'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'report_title': 'تقرير أوراق التأشيرات (هرمي كامل)'
            }

        except Exception as e:
            logger.error(f"خطأ في تقرير أوراق التأشيرات: {e}", exc_info=True)
            return {
                'sectors': [],
                'grand_total': {'total_customers': 0, 'total_visa': 0},
                'filters': {},
                'error': str(e),
                'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }            

    def _get_category_name(self, category_code: str) -> str:
        """تحويل رمز التصنيف المالي إلى اسم عربي"""
        categories = {
            'normal': 'عادي',
            'free': 'مجاني',
            'vip': 'VIP',
            'free_vip': 'مجاني+VIP'
        }
        return categories.get(category_code, category_code or 'غير محدد')

    def _get_parent_sort_order(self, parent_type: str) -> int:
        """إعطاء أولوية ترتيب لأنواع العلبات الأم"""
        order = {
            'مولدة': 1,
            'علبة توزيع': 2,
            'رئيسية': 3
        }
        return order.get(parent_type, 4)

    # ============== دوال مساعدة للتقرير ==============

    def get_available_sectors(self) -> List[Dict]:
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id, name, code FROM sectors WHERE is_active = TRUE ORDER BY name")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"خطأ في جلب القطاعات: {e}")
            return []

    def get_available_boxes(self, box_type: str = None) -> List[Dict]:
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
                result = []
                for box in boxes:
                    box_dict = dict(box)
                    if box_dict['sector_id']:
                        cursor.execute("SELECT name FROM sectors WHERE id = %s", (box_dict['sector_id'],))
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
        return ['normal', 'free', 'vip', 'free_vip']

    def get_meter_types(self) -> List[str]:
        return ['مولدة', 'علبة توزيع', 'رئيسية', 'زبون']

    # ============== دوال التصدير (بدون عمود الرصيد الجديد) ==============

    def export_negative_balance_report_to_excel(
        self, 
        report_data: Dict[str, Any],
        filename: str = None
    ) -> Tuple[bool, str]:
        """تصدير تقرير قوائم الكسر إلى Excel - بدون عمود الرصيد الجديد"""
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
                # ❌ تم حذف صف الرصيد الجديد
                summary_data.append([''])
                
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
                        data_list = []
                        for customer in customers:
                            data_list.append([
                                customer['name'],
                                customer['box_number'],
                                customer['serial_number'],
                                customer['current_balance'],
                                customer['withdrawal_amount'],
                                customer['visa_balance'],
                                # ❌ تم حذف القيمة السابعة (calculated_new_balance)
                                customer['financial_category'],
                                customer['meter_type'],
                                customer['phone_number'],
                                customer['parent_info']
                            ])
                        
                        columns = [
                            'اسم الزبون', 'رقم العلبة', 'رقم المسلسل',
                            'الرصيد الحالي', 'مبلغ السحب', 'رصيد التأشيرة',
                            # ❌ تم حذف 'الرصيد الجديد'
                            'التصنيف المالي', 'نوع العداد',
                            'رقم الهاتف', 'العلبة الأم'
                        ]
                        
                        df_sector = pd.DataFrame(data_list, columns=columns)
                        
                        total_row = pd.DataFrame([[
                            f"إجمالي {sector_name}",
                            f"{sector_data['customer_count']} زبون",
                            '',
                            sector_data['total_balance'],
                            sector_data['total_withdrawal'],
                            sector_data['total_visa'],
                            # ❌ تم حذف total_calculated_balance
                            '',
                            '',
                            '',
                            ''
                        ]], columns=columns)
                        
                        df_sector = pd.concat([df_sector, total_row], ignore_index=True)
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
            logger.error(f"خطأ في تصدير تقرير الكسر: {e}")
            return False, str(e)

    def export_cut_lists_report_to_excel(
        self, 
        report_data: Dict[str, Any],
        filename: str = None
    ) -> Tuple[bool, str]:
        """تصدير تقرير قوائم القطع إلى Excel - كل قطاع في ورقة منفصلة"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"قوائم_القطع_{timestamp}.xlsx"
            
            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)
            filepath = os.path.join(export_dir, filename)
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # ========== ورقة معلومات التقرير ==========
                info_data = []
                info_data.append(['تقرير قوائم القطع', report_data.get('report_title', '')])
                info_data.append(['تاريخ الإنشاء', report_data.get('generated_at', '')])
                info_data.append([''])
                info_data.append(['الإجماليات:'])
                
                grand_total = report_data.get('grand_total', {})
                info_data.append(['عدد العلب', f"{grand_total.get('total_boxes', 0):,}"])
                info_data.append(['عدد الزبائن', f"{grand_total.get('total_customers', 0):,}"])
                info_data.append(['إجمالي الرصيد', f"{grand_total.get('total_balance', 0):,.0f}"])
                info_data.append(['إجمالي السحب', f"{grand_total.get('total_withdrawal', 0):,.0f}"])
                info_data.append(['إجمالي التأشيرة', f"{grand_total.get('total_visa', 0):,.0f}"])
                info_data.append([''])
                
                filters = report_data.get('filters', {})
                info_data.append(['الفلاتر المطبقة:'])
                info_data.append(['الحد الأدنى للرصيد', filters.get('min_balance', -1000)])
                info_data.append(['الحد الأقصى للرصيد', filters.get('max_balance', 0)])
                info_data.append(['استبعاد المجانيين', 'نعم' if filters.get('exclude_free') else 'لا'])
                info_data.append(['استبعاد VIP', 'نعم' if filters.get('exclude_vip') else 'لا'])
                info_data.append(['نوع العداد', filters.get('only_meter_type', 'زبون')])
                
                df_info = pd.DataFrame(info_data)
                df_info.to_excel(writer, sheet_name='معلومات', index=False, header=False)
                
                # ========== تجميع البيانات حسب القطاع ==========
                sectors_dict = {}  # sector_name -> list of customers with box info
                for box_data in report_data.get('boxes', []):
                    sector_name = box_data.get('sector_name', 'بدون قطاع')
                    if sector_name not in sectors_dict:
                        sectors_dict[sector_name] = []
                    
                    box_info = {
                        'box_name': box_data['box_name'],
                        'box_number': box_data['box_number'],
                        'box_type': box_data['box_type'],
                        'sector_name': sector_name
                    }
                    
                    for customer in box_data.get('customers', []):
                        customer_row = {
                            **box_info,
                            'customer_name': customer['name'],
                            'customer_box_number': customer['box_number'],
                            'serial_number': customer['serial_number'],
                            'current_balance': customer['current_balance'],
                            'withdrawal_amount': customer['withdrawal_amount'],
                            'visa_balance': customer['visa_balance'],
                            'financial_category': customer['financial_category'],
                            'meter_type': customer['meter_type'],
                            'phone_number': customer['phone_number']
                        }
                        sectors_dict[sector_name].append(customer_row)
                
                # ========== ورقة ملخص القطاعات ==========
                sectors_summary = []
                for sector_name, customers in sectors_dict.items():
                    if customers:
                        total_balance = sum(c['current_balance'] for c in customers)
                        total_withdrawal = sum(c['withdrawal_amount'] for c in customers)
                        total_visa = sum(c['visa_balance'] for c in customers)
                        sectors_summary.append([
                            sector_name,
                            len(customers),
                            total_balance,
                            total_withdrawal,
                            total_visa
                        ])
                
                if sectors_summary:
                    df_sectors_summary = pd.DataFrame(sectors_summary, columns=[
                        'القطاع', 'عدد الزبائن', 'إجمالي الرصيد', 'إجمالي السحب', 'إجمالي التأشيرة'
                    ])
                    df_sectors_summary.to_excel(writer, sheet_name='ملخص القطاعات', index=False)
                
                # ========== ورقة لكل قطاع ==========
                for sector_name, customers in sectors_dict.items():
                    if not customers:
                        continue
                    
                    # تجهيز البيانات
                    data_list = []
                    for cust in customers:
                        data_list.append([
                            cust['box_name'],
                            cust['box_number'],
                            cust['box_type'],
                            cust['customer_name'],
                            cust['customer_box_number'],
                            cust['serial_number'],
                            cust['current_balance'],
                            cust['withdrawal_amount'],
                            cust['visa_balance'],
                            cust['financial_category'],
                            cust['meter_type'],
                            cust['phone_number']
                        ])
                    
                    columns = [
                        'اسم العلبة', 'رقم العلبة', 'نوع العلبة',
                        'اسم الزبون', 'رقم علبة الزبون', 'رقم المسلسل',
                        'الرصيد الحالي', 'مبلغ السحب', 'رصيد التأشيرة',
                        'التصنيف المالي', 'نوع العداد', 'رقم الهاتف'
                    ]
                    
                    df_sector = pd.DataFrame(data_list, columns=columns)
                    
                    # إضافة صف إجمالي
                    total_balance = sum(c['current_balance'] for c in customers)
                    total_withdrawal = sum(c['withdrawal_amount'] for c in customers)
                    total_visa = sum(c['visa_balance'] for c in customers)
                    
                    total_row = pd.DataFrame([[
                        f"إجمالي {sector_name}",
                        f"{len(customers)} زبون",
                        '',
                        '',
                        '',
                        '',
                        total_balance,
                        total_withdrawal,
                        total_visa,
                        '',
                        '',
                        ''
                    ]], columns=columns)
                    
                    df_sector = pd.concat([df_sector, total_row], ignore_index=True)
                    
                    # اسم الورقة (مختصر إذا كان طويلاً)
                    sheet_name = sector_name[:31]
                    df_sector.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # تنسيق الأعمدة لجميع الأوراق
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

    def export_visa_report_to_excel(self, report_data: Dict[str, Any], filename: str = None) -> Tuple[bool, str]:
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"اوراق_التأشيرات_{timestamp}.xlsx"

            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)
            filepath = os.path.join(export_dir, filename)

            # تجميع جميع العقد (وليس فقط الزبائن) مع مسارها الهرمي
            nodes_data = []

            def collect_nodes(node, path_parts):
                # بناء المسار الكامل لهذه العقدة
                current_path = path_parts + [node.get('name', '')]  # نضيف اسم العقدة الحالية للمسار
                path_str = ' ← '.join(current_path)
                
                # معلومات العقدة
                node_name = node.get('name', '')
                meter_type = node.get('meter_type', '')
                financial_cat = node.get('financial_category', '')
                visa_balance = float(node.get('visa_balance') or 0)
                
                # نوع الزبون (للعدادات غير الزبون نضع المكافئ، أو نتركه فارغاً؟ النموذج وضع "عادي" للمولدة أيضاً. يبدو أنهم يعتبرون التصنيف المالي لكل الأصول. لذا نعرض التصنيف المالي كما هو.)
                customer_type = self._get_category_name(financial_cat) if financial_cat else ''
                
                # إضافة صف لهذه العقدة
                nodes_data.append({
                    'المسار الهرمي': path_str,
                    'اسم الزبون': node_name,
                    'نوع العداد': meter_type,
                    'نوع الزبون': customer_type,
                    'رصيد التأشيرة': visa_balance,
                    'التاريخ1': '',
                    'التاريخ2': '',
                    'التاريخ3': ''
                })
                
                # ثم معالجة الأبناء بنفس المسار (بدون إضافة العقدة الحالية مرة أخرى لأننا أضفناها للمسار)
                for child in node.get('children', []):
                    collect_nodes(child, current_path)  # نمرر current_path كمسار أساسي للأبناء

            for sector in report_data.get('sectors', []):
                sector_name = sector['sector_name']
                for root in sector.get('roots', []):
                    # نبدأ المسار ب "قطاع: sector_name" ثم نضيف الجذر
                    collect_nodes(root, [f"قطاع: {sector_name}"])

            # ترتيب البيانات حسب المسار لضمان التسلسل الهرمي (اختياري)
            # df = pd.DataFrame(nodes_data)
            # يمكن ترتيبها حسب المسار، لكن المسار نصي وقد لا يرتب جيداً، نكتفي بترتيب الإدراج الطبيعي.

            df = pd.DataFrame(nodes_data)

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='أوراق التأشيرات', index=False)
                worksheet = writer.sheets['أوراق التأشيرات']
                worksheet.column_dimensions['A'].width = 70  # المسار
                worksheet.column_dimensions['B'].width = 25  # اسم الزبون
                worksheet.column_dimensions['C'].width = 15  # نوع العداد
                worksheet.column_dimensions['D'].width = 15  # نوع الزبون
                worksheet.column_dimensions['E'].width = 18  # رصيد التأشيرة
                for col in ['F', 'G', 'H']:
                    worksheet.column_dimensions[col].width = 15

            return True, filepath

        except Exception as e:
            logger.error(f"خطأ في تصدير تقرير أوراق التأشيرات: {e}")
            return False, str(e)
                                    
    # ============== تقارير أخرى محسّنة ==============

    def get_free_customers_by_sector_report(
        self,
        include_vip: bool = True,
        sector_id: int = None
    ) -> Dict[str, Any]:
        """تقرير الزبائن المجانيين المحسّن - بدون الرصيد الجديد"""
        try:
            with db.get_cursor() as cursor:
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
                        # ❌ تم حذف calculated_balance
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
                        # ❌ تم حذف calculated_balance
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

    def export_free_customers_to_excel(
        self, 
        report_data: Dict[str, Any],
        filename: str = None
    ) -> Tuple[bool, str]:
        """تصدير تقرير الزبائن المجانيين إلى Excel - بدون عمود الرصيد الجديد"""
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
                # ❌ تم حذف صف الرصيد الجديد
                summary_data.append([''])
                
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
                        data_list = []
                        for customer in customers:
                            data_list.append([
                                customer['name'],
                                customer['box_number'],
                                customer['current_balance'],
                                customer['withdrawal_amount'],
                                customer['visa_balance'],
                                # ❌ تم حذف الرصيد الجديد (لم يعد يُحسب)
                                customer.get('financial_category', ''),
                                customer.get('meter_type', ''),
                                customer.get('phone_number', ''),
                                customer.get('last_counter_reading', '')
                            ])
                        
                        columns = [
                            'اسم الزبون', 'رقم العلبة', 'الرصيد الحالي', 
                            'مبلغ السحب', 'رصيد التأشيرة',
                            # ❌ تم حذف 'الرصيد الجديد'
                            'التصنيف المالي', 'نوع العداد', 'رقم الهاتف', 'آخر قراءة'
                        ]
                        
                        df_sector = pd.DataFrame(data_list, columns=columns)
                        
                        total_row = pd.DataFrame([[
                            f"إجمالي {sector_name}",
                            f"{sector_data['free_count']} زبون",
                            sector_data['total_balance'],
                            sector_data['total_withdrawal'],
                            sector_data['total_visa_balance'],
                            # ❌ تم حذف calculated_balance
                            '',
                            '',
                            '',
                            ''
                        ]], columns=columns)
                        
                        df_sector = pd.concat([df_sector, total_row], ignore_index=True)
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
        """دالة عامة لتصدير أي تقرير إلى Excel (بدون تعديل لأنها لا تحتوي على الرصيد الجديد)"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{report_type}_{timestamp}.xlsx"
            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)
            filepath = os.path.join(export_dir, filename)
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
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

    # ============== واجهات للوظائف القديمة للحفاظ على التوافق ==============

    def get_negative_balance_lists_report_old_interface(self, financial_category: str = None, sector_id: int = None):
        return self.get_negative_balance_lists_report_old(financial_category, sector_id)

    def get_cut_lists_report_old_interface(self, min_balance: float = 0, max_balance: float = -1000, exclude_categories: list = None):
        return self.get_cut_lists_report_old(min_balance, max_balance, exclude_categories)

    def get_free_customers_by_sector_report_old_interface(self):
        return self.get_free_customers_by_sector_report_old()

            # ============== تقرير جبايات المحاسب ==============

    def get_accountant_collections_report(
        self,
        accountant_id: Optional[int] = None,
        start_datetime: Optional[str] = None,
        end_datetime: Optional[str] = None,
        detailed: bool = True
    ) -> Dict[str, Any]:
        """
        تقرير جبايات المحاسب (فواتير محصلة) خلال فترة زمنية.
        - إذا تم تحديد accountant_id: يُرجع بيانات المحاسب مع فواتيره.
        - إذا لم يتم تحديد: يُرجع قائمة بكل الفواتير مع بيانات المحاسبين.
        """
        try:
            with db.get_cursor() as cursor:
                # 1. جلب الفواتير مع بيانات المحاسب والزبون (تفاصيل كاملة)
                invoices_query = """
                    SELECT 
                        i.id,
                        i.invoice_number,
                        i.payment_date,
                        i.payment_time,
                        i.customer_id,
                        c.name AS customer_name,
                        i.user_id AS accountant_id,
                        u.full_name AS accountant_name,
                        i.kilowatt_amount,
                        i.free_kilowatt,
                        i.discount,
                        i.total_amount,
                        i.payment_method,
                        i.receipt_number,
                        i.book_number
                    FROM invoices i
                    JOIN users u ON i.user_id = u.id
                    LEFT JOIN customers c ON i.customer_id = c.id
                    WHERE i.status = 'active'
                """
                invoices_params = []

                # إضافة شروط التاريخ
                if start_datetime:
                    invoices_query += " AND (i.payment_date + i.payment_time) >= %s"
                    invoices_params.append(start_datetime)
                if end_datetime:
                    invoices_query += " AND (i.payment_date + i.payment_time) <= %s"
                    invoices_params.append(end_datetime)
                if accountant_id:
                    invoices_query += " AND i.user_id = %s"
                    invoices_params.append(accountant_id)

                invoices_query += " ORDER BY i.payment_date DESC, i.payment_time DESC"

                cursor.execute(invoices_query, invoices_params)
                invoices = cursor.fetchall()
                invoices_list = [dict(inv) for inv in invoices]

                # 2. حساب المجاميع لكل محاسب (للملخص)
                # نستخدم نفس الشروط ولكن مع GROUP BY
                summary_query = """
                    SELECT 
                        u.id AS accountant_id,
                        u.full_name AS accountant_name,
                        COUNT(i.id) AS invoice_count,
                        COALESCE(SUM(i.total_amount), 0) AS total_collected,
                        COALESCE(SUM(i.kilowatt_amount), 0) AS total_kilowatts,
                        COALESCE(SUM(i.free_kilowatt), 0) AS total_free_kilowatts,
                        COALESCE(SUM(i.discount), 0) AS total_discount,
                        JSONB_BUILD_OBJECT(
                            'cash', COALESCE(SUM(CASE WHEN i.payment_method = 'cash' THEN i.total_amount ELSE 0 END), 0),
                            'visa', COALESCE(SUM(CASE WHEN i.payment_method = 'visa' THEN i.total_amount ELSE 0 END), 0),
                            'other', COALESCE(SUM(CASE WHEN i.payment_method NOT IN ('cash', 'visa') OR i.payment_method IS NULL THEN i.total_amount ELSE 0 END), 0)
                        ) AS breakdown_by_method
                    FROM invoices i
                    JOIN users u ON i.user_id = u.id
                    WHERE i.status = 'active'
                """
                summary_params = []

                # نفس الشروط بنفس الترتيب
                if start_datetime:
                    summary_query += " AND (i.payment_date + i.payment_time) >= %s"
                    summary_params.append(start_datetime)
                if end_datetime:
                    summary_query += " AND (i.payment_date + i.payment_time) <= %s"
                    summary_params.append(end_datetime)
                if accountant_id:
                    summary_query += " AND i.user_id = %s"
                    summary_params.append(accountant_id)

                summary_query += " GROUP BY u.id, u.full_name ORDER BY u.full_name"

                cursor.execute(summary_query, summary_params)
                summaries = cursor.fetchall()
                summaries_list = [dict(s) for s in summaries]

                # بناء النتيجة
                result = {
                    'report_title': 'تقرير جبايات المحاسبين (مفصل)',
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'start_datetime': start_datetime,
                    'end_datetime': end_datetime,
                    'invoices': invoices_list,
                    'summaries': summaries_list,
                }

                if accountant_id and summaries_list:
                    # إذا كان محاسب واحد، ندمج بياناته مع الفواتير لسهولة العرض
                    result.update(summaries_list[0])
                    result['accountant_name'] = summaries_list[0]['accountant_name']
                    result['accountant_id'] = accountant_id

                # إجماليات عامة
                result['total_all'] = sum(s['total_collected'] for s in summaries_list)
                result['total_kilowatts_all'] = sum(s['total_kilowatts'] for s in summaries_list)
                result['total_free_all'] = sum(s['total_free_kilowatts'] for s in summaries_list)
                result['total_discount_all'] = sum(s['total_discount'] for s in summaries_list)

                return result

        except Exception as e:
            logger.error(f"خطأ في تقرير جبايات المحاسب: {e}")
            return {
                'error': str(e),
                'report_title': 'تقرير جبايات المحاسب',
                'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    def get_accountants_list(self) -> List[Dict[str, Any]]:
        """جلب قائمة المحاسبين (المستخدمين النشطين)"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, full_name, username
                    FROM users
                    WHERE is_active = TRUE
                    ORDER BY full_name
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"خطأ في جلب قائمة المحاسبين: {e}")
            return []

    def export_accountant_collections_to_excel(
        self,
        report_data: Dict[str, Any],
        filename: str = None
    ) -> Tuple[bool, str]:
        """تصدير تقرير جبايات المحاسب إلى Excel (نسخة مفصلة)"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"جبايات_المحاسب_{timestamp}.xlsx"

            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)
            filepath = os.path.join(export_dir, filename)

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # ورقة الفواتير (التفاصيل)
                if report_data.get('invoices'):
                    df_invoices = pd.DataFrame(report_data['invoices'])
                    # ترجمة الأعمدة واختيار الحقول المطلوبة
                    columns_map = {
                        'invoice_number': 'رقم الفاتورة',
                        'payment_date': 'التاريخ',
                        'payment_time': 'الوقت',
                        'customer_name': 'الزبون',
                        'accountant_name': 'المحاسب',
                        'kilowatt_amount': 'الكيلوات',
                        'free_kilowatt': 'المجاني',
                        'discount': 'الحسم',
                        'total_amount': 'المبلغ',
                        'payment_method': 'طريقة الدفع',
                        'receipt_number': 'رقم الوصل',
                        'book_number': 'رقم الدفتر'
                    }
                    # اختيار الأعمدة الموجودة
                    available_cols = {k: v for k, v in columns_map.items() if k in df_invoices.columns}
                    df_invoices = df_invoices[list(available_cols.keys())].rename(columns=available_cols)
                    df_invoices.to_excel(writer, sheet_name='الفواتير', index=False)

                # ورقة ملخص المحاسبين
                if report_data.get('summaries'):
                    df_summary = pd.DataFrame(report_data['summaries'])
                    summary_cols = {
                        'accountant_name': 'المحاسب',
                        'invoice_count': 'عدد الفواتير',
                        'total_kilowatts': 'الكيلوات',
                        'total_free_kilowatts': 'المجاني',
                        'total_discount': 'الحسم',
                        'total_collected': 'الإجمالي',
                        'breakdown_by_method': 'تفاصيل الدفع'
                    }
                    # استخراج تفاصيل الدفع من JSON
                    if 'breakdown_by_method' in df_summary.columns:
                        df_summary['نقداً'] = df_summary['breakdown_by_method'].apply(lambda x: x.get('cash', 0))
                        df_summary['بطاقة'] = df_summary['breakdown_by_method'].apply(lambda x: x.get('visa', 0))
                        df_summary['أخرى'] = df_summary['breakdown_by_method'].apply(lambda x: x.get('other', 0))
                        # إضافة الأعمدة الجديدة للقائمة
                        summary_cols.update({
                            'نقداً': 'نقداً',
                            'بطاقة': 'بطاقة',
                            'أخرى': 'أخرى'
                        })

                    available_sum_cols = {k: v for k, v in summary_cols.items() if k in df_summary.columns}
                    df_summary = df_summary[list(available_sum_cols.keys())].rename(columns=available_sum_cols)
                    df_summary.to_excel(writer, sheet_name='ملخص المحاسبين', index=False)

                # ورقة معلومات التقرير
                info_data = [
                    ['تقرير جبايات المحاسبين', report_data.get('report_title', '')],
                    ['تاريخ التوليد', report_data.get('generated_at', '')],
                    ['من تاريخ', report_data.get('start_datetime', '')],
                    ['إلى تاريخ', report_data.get('end_datetime', '')],
                    ['إجمالي الفواتير', len(report_data.get('invoices', []))],
                    ['إجمالي الكيلوات', f"{report_data.get('total_kilowatts_all', 0):,.0f}"],
                    ['إجمالي المجاني', f"{report_data.get('total_free_all', 0):,.0f}"],
                    ['إجمالي الحسم', f"{report_data.get('total_discount_all', 0):,.0f}"],
                    ['الإجمالي العام', f"{report_data.get('total_all', 0):,.0f}"],
                ]
                df_info = pd.DataFrame(info_data)
                df_info.to_excel(writer, sheet_name='معلومات', index=False, header=False)

                # تنسيق الأعمدة
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        col_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if cell.value and len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)

            return True, filepath

        except Exception as e:
            logger.error(f"خطأ في تصدير تقرير جبايات المحاسب: {e}")
            return False, str(e)


    def _get_we_vs_them_with_visa_adjustment(self, start_date: str, end_date: str, after: bool = True) -> Dict:
        """
        حساب لنا وعلينا مع إمكانية تعديل تأثير التأشيرات.
        after=True: يستخدم الرصيد الحالي (بعد التأشيرات).
        after=False: يطرح التأشيرات المضافة في الفترة للحصول على الرصيد قبل التأشيرات.
        """
        from collections import defaultdict

        with db.get_cursor() as cursor:
            # جلب جميع الزبائن النشطين مع بيانات القطاع والرصيد الحالي
            cursor.execute("""
                SELECT c.id, c.sector_id, s.name as sector_name, c.current_balance
                FROM customers c
                JOIN sectors s ON c.sector_id = s.id
                WHERE c.is_active = TRUE
            """)
            customers = cursor.fetchall()

            # إذا كنا نريد before، نجمع تأثير التأشيرات لكل زبون خلال الفترة
            visa_effects = {}
            if not after:
                cursor.execute("""
                    SELECT customer_id, COALESCE(SUM(amount), 0) as total_visa
                    FROM customer_history
                    WHERE transaction_type IN ('weekly_visa', 'visa_update', 'visa_adjustment')
                    AND created_at BETWEEN %s AND %s
                    GROUP BY customer_id
                """, (start_date, end_date))
                for row in cursor.fetchall():
                    visa_effects[row['customer_id']] = float(row['total_visa'])

        # تجميع النتائج حسب القطاع
        sectors_dict = defaultdict(lambda: {
            'sector_name': '',
            'lana_count': 0,
            'lana_amount': 0.0,
            'alayna_count': 0,
            'alayna_amount': 0.0,
        })

        for cust in customers:
            cust_id = cust['id']
            sector_id = cust['sector_id']
            sector_name = cust['sector_name']
            current_balance = float(cust['current_balance'])

            # الرصيد المعدل
            if after:
                balance = current_balance
            else:
                visa = visa_effects.get(cust_id, 0.0)
                balance = current_balance - visa  # نطرح التأشيرات المضافة

            # تصنيف الرصيد
            if balance < 0:
                sectors_dict[sector_id]['lana_count'] += 1
                sectors_dict[sector_id]['lana_amount'] += balance
            elif balance > 0:
                sectors_dict[sector_id]['alayna_count'] += 1
                sectors_dict[sector_id]['alayna_amount'] += balance
            # صفر يتجاهل

            # تأكد من وجود اسم القطاع
            sectors_dict[sector_id]['sector_name'] = sector_name

        # تحويل القاموس إلى قائمة مع الإجماليات
        sectors_list = []
        total_lana_count = 0
        total_lana_amount = 0.0
        total_alayna_count = 0
        total_alayna_amount = 0.0

        for sector_id, data in sectors_dict.items():
            sectors_list.append({
                'sector_id': sector_id,
                'sector_name': data['sector_name'],
                'lana_count': data['lana_count'],
                'lana_amount': data['lana_amount'],
                'alayna_count': data['alayna_count'],
                'alayna_amount': data['alayna_amount'],
            })
            total_lana_count += data['lana_count']
            total_lana_amount += data['lana_amount']
            total_alayna_count += data['alayna_count']
            total_alayna_amount += data['alayna_amount']

        return {
            'sectors': sectors_list,
            'totals': {
                'total_lana_count': total_lana_count,
                'total_lana_amount': total_lana_amount,
                'total_alayna_count': total_alayna_count,
                'total_alayna_amount': total_alayna_amount,
            }
        }            


    def get_cycle_inventory_report(self, start_date=None, end_date=None, include_visa_effect=False):
        """
        تقرير جرد الدورة (لنا وعلينا، هدر العلب، أرصدة المجاني، إحصائيات الفواتير)
        
        Args:
            start_date: تاريخ بداية الفترة (YYYY-MM-DD) - اختياري
            end_date: تاريخ نهاية الفترة (YYYY-MM-DD) - اختياري
            include_visa_effect: إذا كان True يتم تضمين بيانات لنا وعلينا قبل وبعد التأشيرات
        
        Returns:
            dict يحتوي على الأقسام الأربعة
        """
        from datetime import datetime, timedelta
        import logging
        logger = logging.getLogger(__name__)

        # تعيين الفترة الافتراضية إذا لم تكن محددة (الاثنين الماضي → الأحد الحالي)
        if not end_date:
            today = datetime.now().date()
            days_until_sunday = (6 - today.weekday()) % 7
            end_date = (today + timedelta(days=days_until_sunday)).strftime('%Y-%m-%d')
        if not start_date:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            start_date = (end - timedelta(days=6)).strftime('%Y-%m-%d')

        result = {
            'report_title': '📋 جرد الدورة',
            'period': {'start': start_date, 'end': end_date},
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'sections': {}
        }

        try:
            # ====== 1. لنا وعلينا ======
            try:
                if include_visa_effect:
                    before = self._get_we_vs_them_with_visa_adjustment(start_date, end_date, after=False)
                    after = self._get_we_vs_them_with_visa_adjustment(start_date, end_date, after=True)
                    result['sections']['we_vs_them'] = {
                        'title': 'لنا وعلينا (قبل وبعد التأشيرات)',
                        'before': before,
                        'after': after,
                    }
                else:
                    from modules.customers import CustomerManager
                    cm = CustomerManager()
                    balance_stats = cm.get_customer_balance_by_sector()
                    result['sections']['we_vs_them'] = {
                        'title': 'لنا وعلينا حسب القطاع',
                        'sectors': balance_stats.get('sectors', []),
                        'totals': {
                            'total_lana_amount': balance_stats.get('total_lana_amount', 0),
                            'total_alayna_amount': balance_stats.get('total_alayna_amount', 0),
                            'total_lana_count': balance_stats.get('total_lana_count', 0),
                            'total_alayna_count': balance_stats.get('total_alayna_count', 0),
                        }
                    }
            except Exception as e:
                logger.error(f"فشل جلب بيانات لنا وعلينا: {e}")
                result['sections']['we_vs_them'] = {'sectors': [], 'totals': {}}

            # ====== 2. هدر العلب ======
            try:
                waste_query = """
                    SELECT
                        s.id as sector_id,
                        s.name as sector_name,
                        COALESCE(SUM(CASE WHEN c.meter_type = 'زبون' THEN c.withdrawal_amount ELSE 0 END), 0) as customers_withdrawal,
                        COALESCE(SUM(CASE WHEN c.meter_type = 'رئيسية' THEN c.withdrawal_amount ELSE 0 END), 0) as main_meters_withdrawal
                    FROM sectors s
                    LEFT JOIN customers c ON s.id = c.sector_id AND c.is_active = TRUE
                    WHERE s.is_active = TRUE
                    GROUP BY s.id, s.name
                    ORDER BY s.name
                """
                with db.get_cursor() as cursor:
                    cursor.execute(waste_query)
                    rows = cursor.fetchall()
                    waste_by_sector = []
                    total_customers_withdrawal = 0
                    total_main_withdrawal = 0

                    for row in rows:
                        cust_w = float(row['customers_withdrawal'] or 0)
                        main_w = float(row['main_meters_withdrawal'] or 0)
                        waste = main_w - cust_w
                        waste_pct = (waste / main_w * 100) if main_w > 0 else 0

                        waste_by_sector.append({
                            'sector_id': row['sector_id'],
                            'sector_name': row['sector_name'],
                            'customers_withdrawal': cust_w,
                            'main_meters_withdrawal': main_w,
                            'waste': waste,
                            'waste_percentage': waste_pct,
                        })

                        total_customers_withdrawal += cust_w
                        total_main_withdrawal += main_w

                    result['sections']['waste'] = {
                        'title': 'هدر العلب (الفرق بين سحب الرئيسيات والزبائن)',
                        'sectors': waste_by_sector,
                        'totals': {
                            'total_customers_withdrawal': total_customers_withdrawal,
                            'total_main_withdrawal': total_main_withdrawal,
                            'total_waste': total_main_withdrawal - total_customers_withdrawal,
                        }
                    }
            except Exception as e:
                logger.error(f"فشل جلب بيانات الهدر: {e}")
                result['sections']['waste'] = {'sectors': [], 'totals': {}}

            # ====== 3. أرصدة المجاني ======
            try:
                free_query = """
                    SELECT
                        COUNT(*) as free_customers_count,
                        COALESCE(SUM(current_balance), 0) as total_free_remaining,
                        COALESCE(SUM(withdrawal_amount), 0) as total_free_withdrawal
                    FROM customers
                    WHERE financial_category IN ('free', 'free_vip')
                    AND is_active = TRUE
                """
                with db.get_cursor() as cursor:
                    cursor.execute(free_query)
                    free_row = cursor.fetchone()
                    result['sections']['free_balances'] = {
                        'title': 'أرصدة الزبائن المجانيين',
                        'count': free_row['free_customers_count'] if free_row else 0,
                        'total_free_remaining': float(free_row['total_free_remaining']) if free_row else 0,
                        'total_free_withdrawal': float(free_row['total_free_withdrawal']) if free_row else 0,
                    }
            except Exception as e:
                logger.error(f"فشل جلب أرصدة المجاني: {e}")
                result['sections']['free_balances'] = {'count': 0, 'total_free_remaining': 0, 'total_free_withdrawal': 0}

            # ====== 4. إحصائيات الفواتير ======
            try:
                invoice_query = """
                    SELECT
                        COUNT(*) as invoice_count,
                        COALESCE(SUM(kilowatt_amount), 0) as total_kilowatts,
                        COALESCE(SUM(free_kilowatt), 0) as total_free_kilowatts,
                        COALESCE(SUM(discount), 0) as total_discount,
                        COALESCE(SUM(total_amount), 0) as total_amount
                    FROM invoices
                    WHERE payment_date BETWEEN %s AND %s
                    AND status = 'active'
                """
                with db.get_cursor() as cursor:
                    cursor.execute(invoice_query, (start_date, end_date))
                    inv_row = cursor.fetchone()
                    result['sections']['invoices'] = {
                        'title': f'الكيليات المقطوعة من {start_date} إلى {end_date}',
                        'start_date': start_date,
                        'end_date': end_date,
                        'invoice_count': inv_row['invoice_count'] if inv_row else 0,
                        'total_kilowatts': float(inv_row['total_kilowatts']) if inv_row else 0,
                        'total_free_kilowatts': float(inv_row['total_free_kilowatts']) if inv_row else 0,
                        'total_discount': float(inv_row['total_discount']) if inv_row else 0,
                        'total_amount': float(inv_row['total_amount']) if inv_row else 0,
                    }
            except Exception as e:
                logger.error(f"فشل جلب إحصائيات الفواتير: {e}")
                result['sections']['invoices'] = {}

            return result

        except Exception as e:
            logger.error(f"خطأ عام في تقرير جرد الدورة: {e}", exc_info=True)
            return {'error': str(e)}


    def export_cycle_inventory_to_excel(self, report_data: Dict[str, Any], filename: str = None) -> Tuple[bool, str]:
        """
        تصدير تقرير جرد الدورة إلى Excel مع 4 أوراق منفصلة.
        """
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"جرد_الدورة_{timestamp}.xlsx"

            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)
            filepath = os.path.join(export_dir, filename)

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                sections = report_data.get('sections', {})

                # ========== ورقة معلومات عامة ==========
                info_data = [
                    ['تقرير جرد الدورة', report_data.get('report_title', '')],
                    ['تاريخ الإنشاء', report_data.get('generated_at', '')],
                    ['الفترة من', report_data.get('period', {}).get('start', '')],
                    ['الفترة إلى', report_data.get('period', {}).get('end', '')],
                ]
                df_info = pd.DataFrame(info_data)
                df_info.to_excel(writer, sheet_name='معلومات', index=False, header=False)

                # ========== 1. لنا وعلينا ==========
                we_vs_them = sections.get('we_vs_them', {})
                if 'before' in we_vs_them and 'after' in we_vs_them:
                    # تصدير قبل
                    self._write_we_vs_them_sheet(writer, we_vs_them['before'], 'لنا وعلينا قبل')
                    # تصدير بعد
                    self._write_we_vs_them_sheet(writer, we_vs_them['after'], 'لنا وعلينا بعد')
                else:
                    # تصدير عادي
                    self._write_we_vs_them_sheet(writer, we_vs_them, 'لنا وعلينا')

                sectors_we = we_vs_them.get('sectors', [])
                if sectors_we:
                    data_we = []
                    for sec in sectors_we:
                        data_we.append([
                            sec['sector_name'],
                            sec.get('lana_count', 0),
                            sec.get('lana_amount', 0),
                            sec.get('alayna_count', 0),
                            sec.get('alayna_amount', 0),
                            sec.get('alayna_amount', 0) - sec.get('lana_amount', 0)
                        ])
                    df_we = pd.DataFrame(data_we, columns=[
                        'القطاع', 'عدد لنا', 'مجموع لنا (ك.و)', 'عدد علينا', 'مجموع علينا (ك.و)', 'الصافي'
                    ])
                    # إضافة صف الإجماليات
                    totals = we_vs_them.get('totals', {})
                    total_row = pd.DataFrame([[
                        'الإجمالي العام',
                        totals.get('total_lana_count', 0),
                        totals.get('total_lana_amount', 0),
                        totals.get('total_alayna_count', 0),
                        totals.get('total_alayna_amount', 0),
                        totals.get('total_alayna_amount', 0) - totals.get('total_lana_amount', 0)
                    ]], columns=df_we.columns)
                    df_we = pd.concat([df_we, total_row], ignore_index=True)
                    df_we.to_excel(writer, sheet_name='لنا وعلينا', index=False)

                # ========== 2. هدر العلب ==========
                waste = sections.get('waste', {})
                sectors_waste = waste.get('sectors', [])
                if sectors_waste:
                    data_waste = []
                    for sec in sectors_waste:
                        data_waste.append([
                            sec['sector_name'],
                            sec.get('customers_withdrawal', 0),
                            sec.get('main_meters_withdrawal', 0),
                            sec.get('waste', 0),
                            sec.get('waste_percentage', 0)
                        ])
                    df_waste = pd.DataFrame(data_waste, columns=[
                        'القطاع', 'سحب الزبائن (ك.و)', 'سحب الرئيسيات (ك.و)', 'الهدر (ك.و)', 'نسبة الهدر %'
                    ])
                    # إجماليات
                    tot_waste = waste.get('totals', {})
                    total_row = pd.DataFrame([[
                        'الإجمالي',
                        tot_waste.get('total_customers_withdrawal', 0),
                        tot_waste.get('total_main_withdrawal', 0),
                        tot_waste.get('total_waste', 0),
                        ''
                    ]], columns=df_waste.columns)
                    df_waste = pd.concat([df_waste, total_row], ignore_index=True)
                    df_waste.to_excel(writer, sheet_name='هدر العلب', index=False)

                # ========== 3. أرصدة المجاني ==========
                free = sections.get('free_balances', {})
                if free:
                    free_data = [
                        ['عدد الزبائن المجانيين', free.get('count', 0)],
                        ['إجمالي الرصيد المتبقي (ك.و)', free.get('total_free_remaining', 0)],
                        ['إجمالي سحب المجانيين (ك.و)', free.get('total_free_withdrawal', 0)]
                    ]
                    df_free = pd.DataFrame(free_data)
                    df_free.to_excel(writer, sheet_name='أرصدة المجاني', index=False, header=False)

                # ========== 4. إحصائيات الفواتير ==========
                invoices = sections.get('invoices', {})
                if invoices:
                    inv_data = [
                        ['عدد الفواتير', invoices.get('invoice_count', 0)],
                        ['مجموع الكيليلات (ك.و)', invoices.get('total_kilowatts', 0)],
                        ['مجموع الكيليلات المجانية (ك.و)', invoices.get('total_free_kilowatts', 0)],
                        ['مجموع الحسميات (ل.س)', invoices.get('total_discount', 0)],
                        ['المبلغ الكلي (ل.س)', invoices.get('total_amount', 0)]
                    ]
                    df_inv = pd.DataFrame(inv_data)
                    df_inv.to_excel(writer, sheet_name='إحصائيات الفواتير', index=False, header=False)

                # ========== تنسيق الأعمدة (اختياري) ==========
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for col in worksheet.columns:
                        max_len = 0
                        col_letter = col[0].column_letter
                        for cell in col:
                            try:
                                if cell.value and len(str(cell.value)) > max_len:
                                    max_len = len(str(cell.value))
                            except:
                                pass
                        worksheet.column_dimensions[col_letter].width = min(max_len + 2, 50)

            return True, filepath

        except Exception as e:
            logger.error(f"خطأ في تصدير تقرير جرد الدورة: {e}")
            return False, str(e)

    def _write_we_vs_them_sheet(self, writer, data, sheet_name):
        """يكتب ورقة Excel لبيانات لنا وعلينا"""
        sectors = data.get('sectors', [])
        if not sectors:
            return
        rows = []
        for sec in sectors:
            rows.append([
                sec['sector_name'],
                sec['lana_count'],
                sec['lana_amount'],
                sec['alayna_count'],
                sec['alayna_amount'],
                sec['alayna_amount'] - sec['lana_amount']
            ])
        df = pd.DataFrame(rows, columns=['القطاع', 'عدد لنا', 'مجموع لنا', 'عدد علينا', 'مجموع علينا', 'الصافي'])
        totals = data.get('totals', {})
        total_row = pd.DataFrame([[
            'الإجمالي',
            totals.get('total_lana_count', 0),
            totals.get('total_lana_amount', 0),
            totals.get('total_alayna_count', 0),
            totals.get('total_alayna_amount', 0),
            totals.get('total_alayna_amount', 0) - totals.get('total_lana_amount', 0)
        ]], columns=df.columns)
        df = pd.concat([df, total_row], ignore_index=True)
        df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

    def get_vip_full_report(self, sector_id: int = None) -> Dict[str, Any]:
        """
        تقرير شامل لزبائن VIP (vip و free_vip) مع جميع القيم المالية.
        """
        try:
            with db.get_cursor() as cursor:
                # استعلام لجلب جميع زبائن VIP مع كافة التفاصيل
                query = """
                    SELECT
                        c.id,
                        c.name,
                        c.box_number,
                        c.serial_number,
                        c.phone_number,
                        c.current_balance,
                        c.visa_balance,
                        c.withdrawal_amount,
                        c.financial_category,
                        c.vip_reason,
                        c.vip_no_cut_days,
                        c.vip_expiry_date,
                        c.vip_grace_period,
                        c.free_reason,
                        c.free_amount,
                        c.free_remaining,
                        c.free_expiry_date,
                        c.last_counter_reading,
                        c.notes,
                        s.name as sector_name,
                        s.id as sector_id,
                        parent.name as parent_name,
                        parent.box_number as parent_box_number,
                        parent.meter_type as parent_meter_type
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    LEFT JOIN customers parent ON c.parent_meter_id = parent.id
                    WHERE c.is_active = TRUE
                    AND c.financial_category IN ('vip', 'free_vip')
                """
                params = []
                if sector_id:
                    query += " AND c.sector_id = %s"
                    params.append(sector_id)
                query += " ORDER BY s.name, c.name"

                cursor.execute(query, params)
                rows = cursor.fetchall()

                # تجميع البيانات حسب القطاع (اختياري)
                sectors_dict = {}
                for row in rows:
                    sector = row['sector_name'] or 'بدون قطاع'
                    if sector not in sectors_dict:
                        sectors_dict[sector] = {
                            'customers': [],
                            'total_balance': 0,
                            'total_visa': 0,
                            'total_withdrawal': 0,
                            'total_free_remaining': 0
                        }
                    customer = dict(row)
                    sectors_dict[sector]['customers'].append(customer)
                    sectors_dict[sector]['total_balance'] += float(customer.get('current_balance', 0))
                    sectors_dict[sector]['total_visa'] += float(customer.get('visa_balance', 0))
                    sectors_dict[sector]['total_withdrawal'] += float(customer.get('withdrawal_amount', 0))
                    if customer.get('free_remaining'):
                        sectors_dict[sector]['total_free_remaining'] += float(customer['free_remaining'])

                # تحويل إلى قائمة
                sectors_list = []
                grand_total = {
                    'customer_count': 0,
                    'total_balance': 0,
                    'total_visa': 0,
                    'total_withdrawal': 0,
                    'total_free_remaining': 0
                }
                for sector_name, data in sectors_dict.items():
                    sector_info = {
                        'sector_name': sector_name,
                        'customers': data['customers'],
                        'customer_count': len(data['customers']),
                        'total_balance': data['total_balance'],
                        'total_visa': data['total_visa'],
                        'total_withdrawal': data['total_withdrawal'],
                        'total_free_remaining': data['total_free_remaining']
                    }
                    sectors_list.append(sector_info)
                    grand_total['customer_count'] += len(data['customers'])
                    grand_total['total_balance'] += data['total_balance']
                    grand_total['total_visa'] += data['total_visa']
                    grand_total['total_withdrawal'] += data['total_withdrawal']
                    grand_total['total_free_remaining'] += data['total_free_remaining']

                return {
                    'success': True,
                    'sectors': sectors_list,
                    'grand_total': grand_total,
                    'filters': {'sector_id': sector_id},
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'report_title': 'تقرير VIP شامل'
                }

        except Exception as e:
            logger.error(f"خطأ في تقرير VIP الشامل: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def export_vip_report_to_excel(self, report_data: Dict[str, Any], filename: str = None) -> Tuple[bool, str]:
        """
        تصدير تقرير VIP الشامل إلى Excel.
        """
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"تقرير_VIP_{timestamp}.xlsx"

            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)
            filepath = os.path.join(export_dir, filename)

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # ورقة الإجماليات
                summary_data = []
                summary_data.append(['تقرير VIP الشامل', report_data.get('report_title', '')])
                summary_data.append(['تاريخ الإنشاء', report_data.get('generated_at', '')])
                summary_data.append([''])
                summary_data.append(['الإجماليات:'])

                grand_total = report_data.get('grand_total', {})
                summary_data.append(['عدد الزبائن', f"{grand_total.get('customer_count', 0):,}"])
                summary_data.append(['إجمالي الرصيد', f"{grand_total.get('total_balance', 0):,.0f}"])
                summary_data.append(['إجمالي التأشيرة', f"{grand_total.get('total_visa', 0):,.0f}"])
                summary_data.append(['إجمالي السحب', f"{grand_total.get('total_withdrawal', 0):,.0f}"])
                summary_data.append(['إجمالي الرصيد المجاني المتبقي', f"{grand_total.get('total_free_remaining', 0):,.0f}"])
                summary_data.append([''])

                filters = report_data.get('filters', {})
                summary_data.append(['الفلاتر المطبقة:'])
                summary_data.append(['القطاع', filters.get('sector_id', 'الكل')])

                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='ملخص', index=False, header=False)

                # ورقة لكل قطاع
                for sector_data in report_data.get('sectors', []):
                    sector_name = sector_data['sector_name']
                    customers = sector_data.get('customers', [])
                    if not customers:
                        continue

                    data_list = []
                    for customer in customers:
                        # بناء نص العلبة الأم
                        parent_info = ''
                        if customer.get('parent_name'):
                            parent_parts = []
                            if customer.get('parent_box_number'):
                                parent_parts.append(f"علبة: {customer['parent_box_number']}")
                            parent_parts.append(customer['parent_name'])
                            if customer.get('parent_meter_type'):
                                parent_parts.append(f"({customer['parent_meter_type']})")
                            parent_info = ' - '.join(parent_parts)

                        data_list.append([
                            customer.get('id'),
                            customer.get('name'),
                            customer.get('box_number'),
                            customer.get('serial_number'),
                            customer.get('phone_number'),
                            customer.get('current_balance', 0),
                            customer.get('visa_balance', 0),
                            customer.get('withdrawal_amount', 0),
                            customer.get('financial_category'),
                            customer.get('vip_reason', ''),
                            customer.get('vip_no_cut_days', 0),
                            customer.get('vip_expiry_date'),
                            customer.get('vip_grace_period', 0),
                            customer.get('free_reason', ''),
                            customer.get('free_amount', 0),
                            customer.get('free_remaining', 0),
                            customer.get('free_expiry_date'),
                            customer.get('last_counter_reading', 0),
                            customer.get('notes', ''),
                            parent_info,
                            customer.get('sector_name')
                        ])

                    columns = [
                        'المعرف', 'الاسم', 'رقم العلبة', 'المسلسل', 'الهاتف',
                        'الرصيد الحالي', 'رصيد التأشيرة', 'السحب', 'التصنيف',
                        'سبب VIP', 'أيام عدم القطع', 'تاريخ انتهاء VIP', 'فترة السماح',
                        'سبب المجاني', 'المبلغ المجاني', 'المتبقي من المجاني',
                        'تاريخ انتهاء المجاني', 'آخر قراءة عداد', 'ملاحظات',
                        'العلبة الأم', 'القطاع'
                    ]

                    df_sector = pd.DataFrame(data_list, columns=columns)

                    # إضافة صف إجمالي
                    total_row = [
                        f"إجمالي {sector_name}", '',
                        f"{sector_data['customer_count']} زبون", '', '',
                        f"{sector_data['total_balance']:,.0f}",
                        f"{sector_data['total_visa']:,.0f}",
                        f"{sector_data['total_withdrawal']:,.0f}",
                        '', '', '', '', '', '', '',
                        f"{sector_data['total_free_remaining']:,.0f}",
                        '', '', '', '', ''
                    ]
                    # تأكد من تطابق عدد الأعمدة
                    total_row = total_row[:len(columns)]  # قص الزائد إذا لزم
                    df_sector = pd.concat([df_sector, pd.DataFrame([total_row], columns=columns)], ignore_index=True)

                    # اسم الورقة (مختصر)
                    sheet_name = sector_name[:31]
                    df_sector.to_excel(writer, sheet_name=sheet_name, index=False)

                    # تنسيق عرض الأعمدة
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
            logger.error(f"خطأ في تصدير تقرير VIP: {e}")
            return False, str(e)                                                    