# modules/financial_reports.py
import logging
from typing import Dict, List
from database.connection import db

logger = logging.getLogger(__name__)

class FinancialReports:
    """تقارير التصنيفات المالية"""
    
    def get_financial_summary(self) -> Dict:
        """الحصول على ملخص التصنيفات المالية"""
        try:
            with db.get_cursor() as cursor:
                # إحصائيات التصنيفات
                cursor.execute("""
                    SELECT 
                        financial_category,
                        COUNT(*) as customer_count,
                        SUM(current_balance) as total_balance,
                        SUM(free_amount) as total_free_amount,
                        SUM(free_remaining) as remaining_free_amount,
                        AVG(vip_no_cut_days) as avg_vip_days
                    FROM customers 
                    WHERE is_active = TRUE
                    GROUP BY financial_category
                    ORDER BY 
                        CASE financial_category 
                            WHEN 'normal' THEN 1
                            WHEN 'free' THEN 2
                            WHEN 'vip' THEN 3
                            WHEN 'free_vip' THEN 4
                        END
                """)
                
                category_stats = cursor.fetchall()
                
                # الزبائن المجانيين الذين على وشك الانتهاء
                cursor.execute("""
                    SELECT 
                        c.id, c.name, c.box_number, s.name as sector_name,
                        c.free_remaining, c.free_expiry_date,
                        DATEDIFF(c.free_expiry_date, CURDATE()) as days_left
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.is_active = TRUE 
                    AND c.free_expiry_date IS NOT NULL
                    AND c.free_expiry_date >= CURDATE()
                    AND c.free_expiry_date <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
                    ORDER BY c.free_expiry_date
                """)
                
                expiring_free = cursor.fetchall()
                
                # الزبائن VIP الذين على وشك الانتهاء
                cursor.execute("""
                    SELECT 
                        c.id, c.name, c.box_number, s.name as sector_name,
                        c.vip_no_cut_days, c.vip_expiry_date,
                        DATEDIFF(c.vip_expiry_date, CURDATE()) as days_left
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.is_active = TRUE 
                    AND c.vip_expiry_date IS NOT NULL
                    AND c.vip_expiry_date >= CURDATE()
                    AND c.vip_expiry_date <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
                    ORDER BY c.vip_expiry_date
                """)
                
                expiring_vip = cursor.fetchall()
                
                return {
                    'success': True,
                    'category_stats': category_stats,
                    'expiring_free': expiring_free,
                    'expiring_vip': expiring_vip
                }
                
        except Exception as e:
            logger.error(f"خطأ في جمل ملخص التصنيفات: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_free_customers_report(self) -> List[Dict]:
        """تقرير الزبائن المجانيين للجرد"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        c.id, c.name, c.box_number, c.serial_number,
                        s.name as sector_name, s.code as sector_code,
                        c.free_reason, c.free_amount, c.free_remaining,
                        c.free_expiry_date,
                        c.current_balance, c.visa_balance,
                        DATEDIFF(c.free_expiry_date, CURDATE()) as days_left
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.is_active = TRUE 
                    AND c.financial_category IN ('free', 'free_vip')
                    ORDER BY s.name, c.name
                """)
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"خطأ في جلب تقرير المجانيين: {e}")
            return []
    
    def get_vip_customers_report(self) -> List[Dict]:
        """تقرير الزبائن VIP"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        c.id, c.name, c.box_number, c.serial_number,
                        s.name as sector_name, s.code as sector_code,
                        c.vip_reason, c.vip_no_cut_days, c.vip_expiry_date,
                        c.vip_grace_period, c.current_balance,
                        DATEDIFF(c.vip_expiry_date, CURDATE()) as days_left,
                        CASE 
                            WHEN c.current_balance < 0 THEN 'رصيد سالب'
                            WHEN c.current_balance = 0 THEN 'رصيد صفر'
                            ELSE 'رصيد موجب'
                        END as balance_status
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.is_active = TRUE 
                    AND c.financial_category IN ('vip', 'free_vip')
                    ORDER BY s.name, c.name
                """)
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"خطأ في جلب تقرير VIP: {e}")
            return []