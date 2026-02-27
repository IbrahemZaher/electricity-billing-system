# modules/waste_calculator.py
import logging
from typing import Dict, List, Tuple, Optional, Any, Set
from datetime import datetime, timedelta
import math
from collections import defaultdict, Counter
import statistics
import numpy as np

logger = logging.getLogger(__name__)

class HierarchicalWasteCalculator:
    """حاسبة هدر هرمية متعددة المستويات لشبكة الكهرباء - الإصدار المصحح"""
    
    def __init__(self, waste_threshold=10.0):
        self.waste_threshold = waste_threshold
        self.levels = {
            'generator': 'مولدة',
            'distribution_box': 'علبة توزيع',
            'main_meter': 'رئيسية',
            'customer': 'زبون'
        }
        
    # ==================== التحليل الهيكلي الأساسي ====================
        
    def analyze_sector_hierarchy(self, sector_id: int) -> Dict[str, Any]:
        """
        تحليل كامل للهيكل الهرمي لقطاع معين، مع دعم المولدة الافتراضية.
        """
        try:
            from database.connection import db
            with db.get_cursor() as cursor:
                # 1. جلب القطاع لمعرفة المولدة الافتراضية
                cursor.execute("SELECT default_generator_id FROM sectors WHERE id = %s", (sector_id,))
                sector = cursor.fetchone()
                default_generator_id = sector['default_generator_id'] if sector else None

                generator = None
                if default_generator_id:
                    # 2. إذا كان هناك مولدة افتراضية، استخدمها
                    cursor.execute("""
                        SELECT c.id, c.name, c.withdrawal_amount, c.box_number,
                            c.serial_number, c.sector_id, s.name as sector_name
                        FROM customers c
                        LEFT JOIN sectors s ON c.sector_id = s.id
                        WHERE c.id = %s AND c.is_active = TRUE
                    """, (default_generator_id,))
                    generator = cursor.fetchone()
                    if not generator:
                        logger.warning(f"المولدة الافتراضية {default_generator_id} غير موجودة أو غير نشطة")
                
                if not generator:
                    # 3. إذا لم توجد مولدة افتراضية، ابحث عن مولدة داخل القطاع (السلوك القديم)
                    cursor.execute("""
                        SELECT c.id, c.name, c.withdrawal_amount, c.box_number,
                            c.serial_number, c.sector_id, s.name as sector_name
                        FROM customers c
                        LEFT JOIN sectors s ON c.sector_id = s.id
                        WHERE c.sector_id = %s
                        AND c.meter_type = 'مولدة'
                        AND c.parent_meter_id IS NULL
                        AND c.is_active = TRUE
                    """, (sector_id,))
                    generator = cursor.fetchone()

                if not generator:
                    return {'success': False, 'error': 'لا توجد مولدة محددة لهذا القطاع ولا مولدة داخلية'}

                generator_withdrawal = float(generator.get('withdrawal_amount') or 0)

                # 4. تحليل جميع المستويات تحت المولدة (قد تكون في قطاع آخر)
                hierarchy = self._analyze_meter_hierarchy(generator['id'])

            # ... باقي الكود كما هو ...
                
                # 3. حساب الهدر على كل مستوى
                waste_analysis = self._calculate_waste_by_level(hierarchy)
                
                # 4. تحليل مفصل لكل نوع من الهدر - بالإصدار المصحح
                detailed_analysis = {
                    'pre_distribution_waste': self._calculate_pre_distribution_waste(hierarchy),
                    'distribution_box_waste': self._calculate_distribution_box_waste_corrected(hierarchy),
                    'main_meter_waste': self._calculate_main_meter_waste_corrected(hierarchy),
                    'network_loss': self._calculate_network_loss(hierarchy)
                }
                
                # 5. تقارير مفصلة
                reports = self._generate_detailed_reports(hierarchy, waste_analysis)
                
                # 6. التحقق من الحسابات
                validation = self._validate_calculations(hierarchy)
                
                return {
                    'success': True,
                    'sector': {
                        'id': sector_id,
                        'name': generator.get('sector_name', ''),
                        'generator': dict(generator)
                    },
                    'hierarchy': hierarchy,
                    'waste_analysis': waste_analysis,
                    'detailed_analysis': detailed_analysis,
                    'reports': reports,
                    'summary': self._generate_hierarchy_summary(hierarchy, waste_analysis),
                    'validation': validation,
                    'calculation_details': self._get_calculation_details(hierarchy)
                }
                
        except Exception as e:
            logger.error(f"خطأ في تحليل هيكل القطاع {sector_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _analyze_meter_hierarchy(self, meter_id: int, level: int = 0, path: List = None) -> Dict:
        """تحليل هرمي متكرر للعداد وكل ما تحته"""
        try:
            from database.connection import db
            
            with db.get_cursor() as cursor:
                # جلب بيانات العداد
                cursor.execute("""
                    SELECT c.id, c.name, c.meter_type, c.withdrawal_amount,
                           c.sector_id, s.name as sector_name,
                           c.box_number, c.serial_number,
                           c.parent_meter_id, c.current_balance
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.id = %s AND c.is_active = TRUE
                """, (meter_id,))
                
                meter = cursor.fetchone()
                if not meter:
                    return {}
                
                current_path = (path or []) + [meter['name']]
                
                # جلب الأبناء المباشرين
                cursor.execute("""
                    SELECT c.id, c.name, c.meter_type, c.withdrawal_amount,
                           c.sector_id, s.name as sector_name,
                           c.box_number, c.serial_number,
                           c.parent_meter_id, c.current_balance
                    FROM customers c
                    LEFT JOIN sectors s ON c.sector_id = s.id
                    WHERE c.parent_meter_id = %s 
                    AND c.is_active = TRUE
                    ORDER BY c.meter_type, c.withdrawal_amount DESC
                """, (meter_id,))
                
                children = cursor.fetchall()
                
                # تحليل كل ابن بشكل متكرر
                children_analysis = []
                total_children_withdrawal = 0
                
                for child in children:
                    child_analysis = self._analyze_meter_hierarchy(child['id'], level + 1, current_path)
                    if child_analysis:  # فقط إذا كان التحليل ناجحاً
                        children_analysis.append(child_analysis)
                        total_children_withdrawal += child_analysis.get('meter', {}).get('withdrawal_amount', 0)
                
                # حساب الهدر لهذا المستوى - تصحيح الحساب
                meter_withdrawal = float(meter.get('withdrawal_amount') or 0)
                waste_amount = meter_withdrawal - total_children_withdrawal
                
                # إذا كان الهدر سالباً، فهناك مشكلة في القياس
                if waste_amount < 0:
                    waste_amount = abs(waste_amount)  # استخدام القيمة المطلقة
                    waste_type = "مشكلة: سحب الأبناء أكبر من سحب الأب"
                else:
                    waste_type = "هدر طبيعي"
                
                waste_percentage = (waste_amount / meter_withdrawal * 100) if meter_withdrawal > 0 else 0
                efficiency = (total_children_withdrawal / meter_withdrawal * 100) if meter_withdrawal > 0 else 0
                
                return {
                    'meter': {
                        'id': meter['id'],
                        'name': meter['name'],
                        'meter_type': meter.get('meter_type', ''),
                        'type_arabic': self._get_meter_type_arabic(meter.get('meter_type', '')),
                        'withdrawal_amount': meter_withdrawal,
                        'sector_name': meter.get('sector_name', ''),
                        'box_number': meter.get('box_number', ''),
                        'serial_number': meter.get('serial_number', ''),
                        'current_balance': float(meter.get('current_balance') or 0),
                        'hierarchy_level': level,
                        'hierarchy_path': ' → '.join(current_path)
                    },
                    'children': children_analysis,
                    'children_count': len(children_analysis),
                    'total_children_withdrawal': total_children_withdrawal,
                    'waste_amount': waste_amount,
                    'waste_percentage': waste_percentage,
                    'efficiency': min(efficiency, 100),  # لا تتجاوز 100%
                    'waste_type': waste_type,
                    'direct_customers': [c for c in children if c.get('meter_type') == 'زبون'],
                    'direct_distribution_boxes': [c for c in children if c.get('meter_type') == 'علبة توزيع'],
                    'direct_main_meters': [c for c in children if c.get('meter_type') == 'رئيسية'],
                    'calculation': f"{meter_withdrawal} - {total_children_withdrawal} = {waste_amount}"
                }
                
        except Exception as e:
            logger.error(f"خطأ في التحليل الهرمي للعداد {meter_id}: {e}")
            return {}
    
    def _get_meter_type_arabic(self, meter_type: str) -> str:
        """تحويل نوع العداد إلى العربية"""
        type_map = {
            'generator': 'مولدة',
            'مولدة': 'مولدة',
            'distribution_box': 'علبة توزيع',
            'علبة توزيع': 'علبة توزيع',
            'main_meter': 'رئيسية',
            'رئيسية': 'رئيسية',
            'customer': 'زبون',
            'زبون': 'زبون'
        }
        return type_map.get(meter_type, meter_type)
    
    def _calculate_waste_by_level(self, hierarchy: Dict) -> Dict[str, Any]:
        """حساب الهدر حسب كل مستوى في الهيكل"""
        waste_by_level = defaultdict(lambda: {
            'total_withdrawal': 0,
            'total_waste': 0,
            'meter_count': 0,
            'meters': []
        })
        
        def traverse(node: Dict):
            if not node:
                return
            
            meter = node.get('meter', {})
            level = meter.get('hierarchy_level', 0)
            
            # تحديث بيانات المستوى
            level_key = f"المستوى {level}"
            waste_by_level[level_key]['total_withdrawal'] += meter.get('withdrawal_amount', 0)
            waste_by_level[level_key]['total_waste'] += node.get('waste_amount', 0)
            waste_by_level[level_key]['meter_count'] += 1
            waste_by_level[level_key]['meters'].append({
                'name': meter.get('name', ''),
                'type': meter.get('type_arabic', ''),
                'withdrawal': meter.get('withdrawal_amount', 0),
                'waste': node.get('waste_amount', 0),
                'waste_percentage': node.get('waste_percentage', 0),
                'efficiency': node.get('efficiency', 0)
            })
            
            # تصنيف حسب نوع العداد
            meter_type_key = f"نوع: {meter.get('type_arabic', '')}"
            if meter_type_key not in waste_by_level:
                waste_by_level[meter_type_key] = {
                    'total_withdrawal': 0,
                    'total_waste': 0,
                    'meter_count': 0,
                    'meters': []
                }
            
            waste_by_level[meter_type_key]['total_withdrawal'] += meter.get('withdrawal_amount', 0)
            waste_by_level[meter_type_key]['total_waste'] += node.get('waste_amount', 0)
            waste_by_level[meter_type_key]['meter_count'] += 1
            
            # الانتقال للأبناء
            for child in node.get('children', []):
                traverse(child)
        
        traverse(hierarchy)
        
        # حساب النسب المئوية لكل مستوى
        for key, data in waste_by_level.items():
            total_withdrawal = data['total_withdrawal']
            if total_withdrawal > 0:
                data['waste_percentage'] = (data['total_waste'] / total_withdrawal) * 100
                data['efficiency'] = 100 - data['waste_percentage']
            else:
                data['waste_percentage'] = 0
                data['efficiency'] = 0
        
        return dict(waste_by_level)
    
    def _calculate_pre_distribution_waste(self, hierarchy: Dict) -> Dict[str, Any]:
        """حساب هدر ما قبل علب التوزيع (المستوى الأول)"""
        generator = hierarchy.get('meter', {})
        generator_withdrawal = generator.get('withdrawal_amount', 0)
        
        # جمع سحب جميع الأبناء المباشرين
        direct_children_withdrawal = hierarchy.get('total_children_withdrawal', 0)
        
        # حساب الهدر
        waste_amount = generator_withdrawal - direct_children_withdrawal
        if waste_amount < 0:
            waste_type = "مشكلة: سحب الأبناء أكبر من المولدة"
            waste_amount = abs(waste_amount)
        else:
            waste_type = "هدر طبيعي"
        
        waste_percentage = (waste_amount / generator_withdrawal * 100) if generator_withdrawal > 0 else 0
        efficiency = (direct_children_withdrawal / generator_withdrawal * 100) if generator_withdrawal > 0 else 0
        
        return {
            'name': 'هدر ما قبل علب التوزيع',
            'description': 'الفرق بين سحب عداد المولدة وجميع أبنائه المباشرين',
            'generator_name': generator.get('name', ''),
            'generator_withdrawal': generator_withdrawal,
            'direct_children_withdrawal': direct_children_withdrawal,
            'waste_amount': waste_amount,
            'waste_percentage': waste_percentage,
            'efficiency': min(efficiency, 100),
            'waste_type': waste_type,
            'direct_children_count': hierarchy.get('children_count', 0),
            'calculation': f"{generator_withdrawal} - {direct_children_withdrawal} = {waste_amount} ك.و",
            'status': 'حرج' if waste_percentage > 15 else 'مرتفع' if waste_percentage > 8 else 'طبيعي' if waste_percentage > 0 else 'ممتاز'
        }
    
    def _calculate_distribution_box_waste_corrected(self, hierarchy: Dict) -> Dict[str, Any]:
        """حساب هدر علب التوزيع والكابلات - الإصدار المصحح"""
        distribution_boxes = []
        
        def find_distribution_boxes(node: Dict):
            if not node:
                return
            
            meter = node.get('meter', {})
            meter_type = meter.get('meter_type', '')
            
            # تصحيح: التحقق من نوع العداد
            if meter_type in ['علبة توزيع', 'distribution_box']:
                box_withdrawal = float(meter.get('withdrawal_amount') or 0)
                
                # حساب سحب جميع الأبناء المباشرين
                children_withdrawal = 0
                children_details = []
                
                for child in node.get('children', []):
                    child_meter = child.get('meter', {})
                    child_withdrawal = float(child_meter.get('withdrawal_amount') or 0)
                    children_withdrawal += child_withdrawal
                    
                    children_details.append({
                        'name': child_meter.get('name', ''),
                        'type': child_meter.get('type_arabic', ''),
                        'withdrawal': child_withdrawal,
                        'meter_type': child_meter.get('meter_type', '')
                    })
                
                # حساب الهدر
                waste_amount = box_withdrawal - children_withdrawal
                
                # تحديد نوع المشكلة إن وجدت
                if waste_amount < 0:
                    waste_type = "⚠️ مشكلة: سحب الأبناء أكبر من العلبة"
                    absolute_waste = abs(waste_amount)
                    efficiency = 100  # إذا كان سحب الأبناء أكبر، فالكفاءة 100%
                else:
                    waste_type = "هدر طبيعي"
                    absolute_waste = waste_amount
                    efficiency = (children_withdrawal / box_withdrawal * 100) if box_withdrawal > 0 else 0
                
                waste_percentage = (absolute_waste / box_withdrawal * 100) if box_withdrawal > 0 else 0
                
                distribution_boxes.append({
                    'box': meter,
                    'box_name': meter.get('name', ''),
                    'box_number': meter.get('box_number', ''),
                    'box_withdrawal': box_withdrawal,
                    'children_count': node.get('children_count', 0),
                    'children_withdrawal': children_withdrawal,
                    'waste_amount': waste_amount,  # قد يكون سالباً
                    'absolute_waste': absolute_waste,  # القيمة المطلقة
                    'waste_percentage': waste_percentage,
                    'efficiency': min(efficiency, 100),
                    'waste_type': waste_type,
                    'children_details': children_details,
                    'calculation': f"{box_withdrawal} - {children_withdrawal} = {waste_amount}",
                    'status': 'حرج' if waste_percentage > 15 else 'مرتفع' if waste_percentage > 8 else 'طبيعي' if waste_percentage > 0 else 'ممتاز'
                })
            
            # البحث في الأبناء
            for child in node.get('children', []):
                find_distribution_boxes(child)
        
        find_distribution_boxes(hierarchy)
        
        # حساب الإجماليات المصححة
        total_boxes = len(distribution_boxes)
        
        if total_boxes > 0:
            total_box_withdrawal = sum(b['box_withdrawal'] for b in distribution_boxes)
            total_children_withdrawal = sum(b['children_withdrawal'] for b in distribution_boxes)
            total_absolute_waste = sum(b['absolute_waste'] for b in distribution_boxes)
            
            # الكفاءة الإجمالية = (إجمالي سحب الأبناء / إجمالي سحب العلب) * 100
            if total_box_withdrawal > 0:
                total_efficiency = (total_children_withdrawal / total_box_withdrawal) * 100
            else:
                total_efficiency = 0
            
            total_waste_percentage = (total_absolute_waste / total_box_withdrawal * 100) if total_box_withdrawal > 0 else 0
        else:
            total_box_withdrawal = 0
            total_children_withdrawal = 0
            total_absolute_waste = 0
            total_efficiency = 0
            total_waste_percentage = 0
        
        # ترتيب العلب حسب الهدر (من الأعلى إلى الأقل)
        distribution_boxes_sorted = sorted(distribution_boxes, 
                                         key=lambda x: x['waste_percentage'], 
                                         reverse=True)
        
        # تحليل مفصل لكل علبة
        detailed_box_analysis = []
        for box in distribution_boxes_sorted:
            detailed_box_analysis.append({
                'box_name': box['box_name'],
                'box_number': box.get('box_number', ''),
                'box_withdrawal': box['box_withdrawal'],
                'children_count': box['children_count'],
                'children_withdrawal': box['children_withdrawal'],
                'waste': box['absolute_waste'],
                'waste_percentage': box['waste_percentage'],
                'efficiency': box['efficiency'],
                'status': box['status'],
                'waste_type': box['waste_type'],
                'calculation': box['calculation']
            })
        
        # تحليل المشاكل
        problem_boxes = [b for b in distribution_boxes if b['waste_amount'] < 0]
        
        return {
            'name': 'هدر علب التوزيع والكابلات',
            'description': 'الفرق بين سحب عداد علبة التوزيع وأبنائه الخاصين به',
            'total_boxes': total_boxes,
            'total_box_withdrawal': total_box_withdrawal,
            'total_children_withdrawal': total_children_withdrawal,
            'total_waste_amount': total_absolute_waste,
            'total_waste_percentage': total_waste_percentage,
            'total_efficiency': min(total_efficiency, 100),
            'average_waste_per_box': total_absolute_waste / total_boxes if total_boxes > 0 else 0,
            'boxes_analysis': distribution_boxes_sorted,
            'detailed_box_analysis': detailed_box_analysis,
            'problem_boxes': problem_boxes,
            'problem_count': len(problem_boxes),
            'critical_boxes': [b for b in distribution_boxes_sorted if b['waste_percentage'] > 15],
            'warning_boxes': [b for b in distribution_boxes_sorted if 5 < b['waste_percentage'] <= 15],
            'efficient_boxes': [b for b in distribution_boxes_sorted if b['waste_percentage'] <= 5],
            'summary_table': [
                {
                    'العلبة': b['box_name'],
                    'سحب العلبة': f"{b['box_withdrawal']:.1f}",
                    'سحب الأبناء': f"{b['children_withdrawal']:.1f}",
                    'الهدر': f"{b['absolute_waste']:.1f}",
                    'نسبة الهدر%': f"{b['waste_percentage']:.1f}",
                    'الكفاءة%': f"{b['efficiency']:.1f}",
                    'الحالة': b['status']
                }
                for b in distribution_boxes_sorted
            ]
        }
    
    def _calculate_main_meter_waste_corrected(self, hierarchy: Dict) -> Dict[str, Any]:
        """حساب هدر العلب - الإصدار المصحح"""
        main_meters = []
        
        def find_main_meters(node: Dict):
            if not node:
                return
            
            meter = node.get('meter', {})
            meter_type = meter.get('meter_type', '')
            
            if meter_type in ['رئيسية', 'main_meter']:
                # حساب هدر هذا العداد الرئيسي
                meter_withdrawal = float(meter.get('withdrawal_amount') or 0)
                children_withdrawal = 0
                customers_analysis = []
                
                for child in node.get('children', []):
                    child_meter = child.get('meter', {})
                    child_withdrawal = float(child_meter.get('withdrawal_amount') or 0)
                    children_withdrawal += child_withdrawal
                    
                    if child_meter.get('meter_type') in ['زبون', 'customer']:
                        customers_analysis.append({
                            'name': child_meter.get('name', ''),
                            'withdrawal': child_withdrawal,
                            'current_balance': child_meter.get('current_balance', 0)
                        })
                
                # حساب الهدر
                waste_amount = meter_withdrawal - children_withdrawal
                
                if waste_amount < 0:
                    waste_type = "⚠️ مشكلة: سحب الزبائن أكبر من العداد"
                    absolute_waste = abs(waste_amount)
                    efficiency = 100  # إذا كان سحب الزبائن أكبر، فالكفاءة 100%
                else:
                    waste_type = "هدر طبيعي"
                    absolute_waste = waste_amount
                    efficiency = (children_withdrawal / meter_withdrawal * 100) if meter_withdrawal > 0 else 0
                
                waste_percentage = (absolute_waste / meter_withdrawal * 100) if meter_withdrawal > 0 else 0
                
                main_meters.append({
                    'meter': meter,
                    'meter_name': meter.get('name', ''),
                    'meter_withdrawal': meter_withdrawal,
                    'customers_withdrawal': children_withdrawal,
                    'waste_amount': waste_amount,
                    'absolute_waste': absolute_waste,
                    'waste_percentage': waste_percentage,
                    'efficiency': min(efficiency, 100),
                    'waste_type': waste_type,
                    'customers_count': len(customers_analysis),
                    'customers_analysis': customers_analysis,
                    'parent_box': self._find_parent_box_name(node, hierarchy),
                    'calculation': f"{meter_withdrawal} - {children_withdrawal} = {waste_amount}",
                    'status': 'حرج' if waste_percentage > 15 else 'مرتفع' if waste_percentage > 8 else 'طبيعي' if waste_percentage > 0 else 'ممتاز'
                })
            
            # البحث في الأبناء
            for child in node.get('children', []):
                find_main_meters(child)
        
        find_main_meters(hierarchy)
        
        # حساب الإجماليات
        total_meters = len(main_meters)
        
        if total_meters > 0:
            total_meter_withdrawal = sum(m['meter_withdrawal'] for m in main_meters)
            total_customers_withdrawal = sum(m['customers_withdrawal'] for m in main_meters)
            total_absolute_waste = sum(m['absolute_waste'] for m in main_meters)
            
            if total_meter_withdrawal > 0:
                total_efficiency = (total_customers_withdrawal / total_meter_withdrawal) * 100
            else:
                total_efficiency = 0
            
            total_waste_percentage = (total_absolute_waste / total_meter_withdrawal * 100) if total_meter_withdrawal > 0 else 0
        else:
            total_meter_withdrawal = 0
            total_customers_withdrawal = 0
            total_absolute_waste = 0
            total_efficiency = 0
            total_waste_percentage = 0
        
        # ترتيب العدادات حسب الهدر
        main_meters_sorted = sorted(main_meters, 
                                   key=lambda x: x['waste_percentage'], 
                                   reverse=True)
        
        return {
            'name': 'هدر العلب',
            'description': 'الفرق بين سحب العداد الرئيسي والزبائن الخاصين به',
            'total_meters': total_meters,
            'total_meter_withdrawal': total_meter_withdrawal,
            'total_customers_withdrawal': total_customers_withdrawal,
            'total_waste_amount': total_absolute_waste,
            'total_waste_percentage': total_waste_percentage,
            'total_efficiency': min(total_efficiency, 100),
            'average_waste_per_meter': total_absolute_waste / total_meters if total_meters > 0 else 0,
            'meters_analysis': main_meters_sorted,
            'problem_meters': [m for m in main_meters if m['waste_amount'] < 0],
            'critical_meters': [m for m in main_meters_sorted if m['waste_percentage'] > 15],
            'warning_meters': [m for m in main_meters_sorted if 5 < m['waste_percentage'] <= 15],
            'efficient_meters': [m for m in main_meters_sorted if m['waste_percentage'] <= 5],
            'summary_table': [
                {
                    'العداد': m['meter_name'],
                    'سحب العداد': f"{m['meter_withdrawal']:.1f}",
                    'سحب الزبائن': f"{m['customers_withdrawal']:.1f}",
                    'الهدر': f"{m['absolute_waste']:.1f}",
                    'نسبة الهدر%': f"{m['waste_percentage']:.1f}",
                    'الكفاءة%': f"{m['efficiency']:.1f}",
                    'العلبة الأم': m['parent_box'],
                    'الحالة': m['status']
                }
                for m in main_meters_sorted
            ]
        }
    
    # دالة للحفاظ على التوافق مع الكود السابق
    def _calculate_distribution_box_waste(self, hierarchy: Dict) -> Dict[str, Any]:
        """حساب هدر علب التوزيع والكابلات (الإصدار القديم للحفاظ على التوافق)"""
        # نستخدم الإصدار المصحح
        return self._calculate_distribution_box_waste_corrected(hierarchy)
    
    # دالة للحفاظ على التوافق مع الكود السابق
    def _calculate_main_meter_waste(self, hierarchy: Dict) -> Dict[str, Any]:
        """حساب هدر العلب (الإصدار القديم للحفاظ على التوافق)"""
        # نستخدم الإصدار المصحح
        return self._calculate_main_meter_waste_corrected(hierarchy)
    
    def _find_parent_box_name(self, node: Dict, hierarchy: Dict) -> str:
        """العثور على اسم العلبة الأم للعداد"""
        def find_parent(current_node, target_id):
            for child in current_node.get('children', []):
                child_meter = child.get('meter', {})
                if child_meter.get('id') == target_id:
                    return current_node.get('meter', {}).get('name', 'غير معروف')
                
                result = find_parent(child, target_id)
                if result:
                    return result
            
            return None
        
        node_id = node.get('meter', {}).get('id')
        return find_parent(hierarchy, node_id) or 'مباشر من المولدة'
    
    def _calculate_network_loss(self, hierarchy: Dict) -> Dict[str, Any]:
        """حساب خسائر الشبكة الإجمالية"""
        total_withdrawal = hierarchy.get('meter', {}).get('withdrawal_amount', 0)
        
        # جمع سحب جميع الزبائن في كل المستويات
        total_customers_withdrawal = 0
        customers_count = 0
        
        def sum_customers(node: Dict):
            nonlocal total_customers_withdrawal, customers_count
            
            meter = node.get('meter', {})
            if meter.get('meter_type') in ['زبون', 'customer']:
                total_customers_withdrawal += meter.get('withdrawal_amount', 0)
                customers_count += 1
            
            for child in node.get('children', []):
                sum_customers(child)
        
        sum_customers(hierarchy)
        
        # حساب الخسارة الإجمالية
        total_loss = total_withdrawal - total_customers_withdrawal
        loss_percentage = (total_loss / total_withdrawal * 100) if total_withdrawal > 0 else 0
        network_efficiency = (total_customers_withdrawal / total_withdrawal * 100) if total_withdrawal > 0 else 0
        
        return {
            'name': 'خسائر الشبكة الإجمالية',
            'description': 'الفرق بين سحب المولدة وإجمالي سحب جميع الزبائن',
            'total_withdrawal': total_withdrawal,
            'total_customers_withdrawal': total_customers_withdrawal,
            'total_loss': total_loss,
            'loss_percentage': loss_percentage,
            'network_efficiency': min(network_efficiency, 100),
            'customers_count': customers_count,
            'average_customer_withdrawal': total_customers_withdrawal / customers_count if customers_count > 0 else 0,
            'status': 'حرج' if loss_percentage > 20 else 'مرتفع' if loss_percentage > 15 else 'متوسط' if loss_percentage > 10 else 'جيد' if loss_percentage > 5 else 'ممتاز'
        }
    
    def _generate_detailed_reports(self, hierarchy: Dict, waste_analysis: Dict) -> Dict[str, Any]:
        """توليد تقارير مفصلة عن النظام"""
        reports = {
            'executive_summary': self._generate_executive_summary(hierarchy, waste_analysis),
            'level_wise_analysis': self._generate_level_wise_analysis(waste_analysis),
            'performance_metrics': self._calculate_performance_metrics(hierarchy),
            'comparative_analysis': self._generate_comparative_analysis(hierarchy),
            'action_items': self._generate_action_items(hierarchy, waste_analysis)
        }
        
        return reports
    
    def _get_calculation_details(self, hierarchy: Dict) -> Dict[str, Any]:
        """الحصول على تفاصيل الحسابات"""
        details = {
            'hierarchy_summary': self._get_hierarchy_summary(hierarchy),
            'box_calculations': [],
            'meter_calculations': []
        }
        
        def collect_calculations(node: Dict, parent_name: str = ""):
            if not node:
                return
            
            meter = node.get('meter', {})
            meter_name = meter.get('name', '')
            meter_type = meter.get('meter_type', '')
            
            if meter_type in ['علبة توزيع', 'distribution_box']:
                details['box_calculations'].append({
                    'box': meter_name,
                    'parent': parent_name,
                    'withdrawal': meter.get('withdrawal_amount', 0),
                    'children_withdrawal': node.get('total_children_withdrawal', 0),
                    'waste': node.get('waste_amount', 0),
                    'calculation': node.get('calculation', '')
                })
            elif meter_type in ['رئيسية', 'main_meter']:
                details['meter_calculations'].append({
                    'meter': meter_name,
                    'parent': parent_name,
                    'withdrawal': meter.get('withdrawal_amount', 0),
                    'children_withdrawal': node.get('total_children_withdrawal', 0),
                    'waste': node.get('waste_amount', 0),
                    'calculation': node.get('calculation', '')
                })
            
            for child in node.get('children', []):
                collect_calculations(child, meter_name)
        
        collect_calculations(hierarchy)
        return details
    
    def _get_hierarchy_summary(self, hierarchy: Dict) -> Dict[str, Any]:
        """ملخص الهيكل"""
        summary = {
            'total_nodes': 0,
            'by_type': defaultdict(int),
            'by_level': defaultdict(int)
        }
        
        def count_nodes(node: Dict, level: int = 0):
            if not node:
                return
            
            summary['total_nodes'] += 1
            summary['by_level'][level] += 1
            
            meter = node.get('meter', {})
            meter_type = meter.get('meter_type', '')
            summary['by_type'][meter_type] += 1
            
            for child in node.get('children', []):
                count_nodes(child, level + 1)
        
        count_nodes(hierarchy)
        return dict(summary)
    
    def _validate_calculations(self, hierarchy: Dict) -> Dict[str, Any]:
        """التحقق من صحة الحسابات"""
        issues = []
        
        def validate_node(node: Dict, parent_name: str = ""):
            if not node:
                return
            
            meter = node.get('meter', {})
            meter_name = meter.get('name', '')
            meter_type = meter.get('meter_type', '')
            
            withdrawal = meter.get('withdrawal_amount', 0)
            children_withdrawal = node.get('total_children_withdrawal', 0)
            waste = node.get('waste_amount', 0)
            
            # التحقق من أن حساب الهدر صحيح
            calculated_waste = withdrawal - children_withdrawal
            
            if abs(calculated_waste - waste) > 0.01:  # تسامح 0.01 للتقريب
                issues.append({
                    'node': meter_name,
                    'type': meter_type,
                    'issue': f'حساب الهدر غير صحيح: {withdrawal} - {children_withdrawal} = {calculated_waste:.2f} ≠ {waste:.2f}',
                    'severity': 'عالية'
                })
            
            # إذا كان سحب الأبناء أكبر من سحب الأب
            if children_withdrawal > withdrawal:
                issues.append({
                    'node': meter_name,
                    'type': meter_type,
                    'issue': f'سحب الأبناء ({children_withdrawal:.2f}) أكبر من سحب الأب ({withdrawal:.2f})',
                    'severity': 'متوسطة',
                    'difference': children_withdrawal - withdrawal
                })
            
            for child in node.get('children', []):
                validate_node(child, meter_name)
        
        validate_node(hierarchy)
        
        return {
            'total_issues': len(issues),
            'critical_issues': len([i for i in issues if i['severity'] == 'عالية']),
            'warning_issues': len([i for i in issues if i['severity'] == 'متوسطة']),
            'issues': issues,
            'status': 'جيد' if len(issues) == 0 else 'تحتاج مراجعة'
        }
    
    def _generate_executive_summary(self, hierarchy: Dict, waste_analysis: Dict) -> Dict[str, Any]:
        """توليد ملاح تنفيذي للنظام"""
        generator = hierarchy.get('meter', {})
        
        # جمع الإحصائيات الرئيسية
        total_meters = 0
        total_customers = 0
        total_withdrawal = generator.get('withdrawal_amount', 0)
        
        def count_meters(node: Dict):
            nonlocal total_meters, total_customers
            
            meter = node.get('meter', {})
            meter_type = meter.get('meter_type', '')
            
            if meter_type in ['مولدة', 'علبة توزيع', 'رئيسية']:
                total_meters += 1
            elif meter_type == 'زبون':
                total_customers += 1
            
            for child in node.get('children', []):
                count_meters(child)
        
        count_meters(hierarchy)
        
        # حساب الكفاءة الإجمالية
        network_loss = self._calculate_network_loss(hierarchy)
        network_efficiency = network_loss.get('network_efficiency', 0)
        
        # تحديد حالة النظام
        if network_efficiency >= 95:
            system_status = 'ممتاز'
            status_color = 'green'
        elif network_efficiency >= 90:
            system_status = 'جيد جداً'
            status_color = 'blue'
        elif network_efficiency >= 85:
            system_status = 'جيد'
            status_color = 'yellow'
        elif network_efficiency >= 80:
            system_status = 'متوسط'
            status_color = 'orange'
        else:
            system_status = 'ضعيف'
            status_color = 'red'
        
        # الحصول على تحليل الهدر
        pre_dist_waste = self._calculate_pre_distribution_waste(hierarchy)
        dist_box_waste = self._calculate_distribution_box_waste_corrected(hierarchy)
        main_meter_waste = self._calculate_main_meter_waste_corrected(hierarchy)
        
        return {
            'system_name': generator.get('name', ''),
            'sector': generator.get('sector_name', ''),
            'total_meters': total_meters,
            'total_customers': total_customers,
            'total_withdrawal': total_withdrawal,
            'network_efficiency': network_efficiency,
            'system_status': system_status,
            'status_color': status_color,
            'key_metrics': {
                'pre_distribution_loss': {
                    'percentage': pre_dist_waste['waste_percentage'],
                    'amount': pre_dist_waste['waste_amount'],
                    'status': pre_dist_waste['status']
                },
                'distribution_box_loss': {
                    'percentage': dist_box_waste['total_waste_percentage'],
                    'amount': dist_box_waste['total_waste_amount'],
                    'boxes_count': dist_box_waste['total_boxes']
                },
                'main_meter_loss': {
                    'percentage': main_meter_waste['total_waste_percentage'],
                    'amount': main_meter_waste['total_waste_amount'],
                    'meters_count': main_meter_waste['total_meters']
                }
            },
            'problems_summary': {
                'pre_distribution': pre_dist_waste.get('waste_type', ''),
                'distribution_boxes': f"{dist_box_waste.get('problem_count', 0)} علب بها مشاكل",
                'main_meters': f"{len(main_meter_waste.get('problem_meters', []))} عدادات بها مشاكل"
            },
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _generate_level_wise_analysis(self, waste_analysis: Dict) -> List[Dict]:
        """تحليل مفصل لكل مستوى"""
        level_analysis = []
        
        for level_key, data in waste_analysis.items():
            if level_key.startswith('المستوى'):
                analysis = {
                    'level': level_key,
                    'total_withdrawal': data['total_withdrawal'],
                    'total_waste': data['total_waste'],
                    'waste_percentage': data['waste_percentage'],
                    'efficiency': data['efficiency'],
                    'meter_count': data['meter_count'],
                    'top_waste_meters': sorted(data['meters'], 
                                              key=lambda x: x['waste_percentage'], 
                                              reverse=True)[:5]
                }
                level_analysis.append(analysis)
        
        return level_analysis
    
    def _calculate_performance_metrics(self, hierarchy: Dict) -> Dict[str, Any]:
        """حساب مقاييس الأداء للنظام"""
        metrics = {
            'load_distribution': self._analyze_load_distribution(hierarchy),
            'voltage_stability': self._estimate_voltage_stability(hierarchy),
            'power_quality': self._estimate_power_quality(hierarchy),
            'reliability_index': self._calculate_reliability_index(hierarchy)
        }
        
        return metrics
    
    def _analyze_load_distribution(self, hierarchy: Dict) -> Dict[str, Any]:
        """تحليل توزيع الأحمال"""
        loads = []
        
        def collect_loads(node: Dict):
            meter = node.get('meter', {})
            if meter.get('meter_type') in ['علبة توزيع', 'رئيسية']:
                loads.append({
                    'name': meter.get('name', ''),
                    'type': meter.get('type_arabic', ''),
                    'withdrawal': meter.get('withdrawal_amount', 0),
                    'children_count': node.get('children_count', 0)
                })
            
            for child in node.get('children', []):
                collect_loads(child)
        
        collect_loads(hierarchy)
        
        if not loads:
            return {'status': 'لا توجد بيانات', 'balance_score': 0}
        
        # حساب معامل التوازن
        withdrawals = [l['withdrawal'] for l in loads]
        avg_load = statistics.mean(withdrawals) if withdrawals else 0
        std_load = statistics.stdev(withdrawals) if len(withdrawals) > 1 else 0
        
        balance_score = 100 - (std_load / avg_load * 100) if avg_load > 0 else 0
        
        return {
            'status': 'جيد' if balance_score > 80 else 'بحاجة لتحسين',
            'balance_score': balance_score,
            'average_load': avg_load,
            'load_variance': std_load,
            'max_load': max(withdrawals) if withdrawals else 0,
            'min_load': min(withdrawals) if withdrawals else 0,
            'load_distribution': loads
        }
    
    def _estimate_voltage_stability(self, hierarchy: Dict) -> Dict[str, Any]:
        """تقدير استقرار الجهد"""
        # هذا تقدير مبسط يعتمد على توزيع الأحمال
        load_distribution = self._analyze_load_distribution(hierarchy)
        balance_score = load_distribution.get('balance_score', 0)
        
        if balance_score > 90:
            stability = 'ممتاز'
            score = 95
        elif balance_score > 80:
            stability = 'جيد'
            score = 85
        elif balance_score > 70:
            stability = 'متوسط'
            score = 75
        else:
            stability = 'ضعيف'
            score = 60
        
        return {
            'stability': stability,
            'score': score,
            'factors': ['توازن الأحمال', 'طول الخطوط', 'مقاطع الكابلات'],
            'recommendations': [
                'تحسين توزيع الأحمال' if balance_score < 80 else '',
                'تعديل مقاطع الكابلات' if balance_score < 70 else ''
            ]
        }
    
    def _estimate_power_quality(self, hierarchy: Dict) -> Dict[str, Any]:
        """تقدير جودة الطاقة"""
        waste_analysis = self._calculate_waste_by_level(hierarchy)
        
        # حساب نسبة التوافقيات (تقديرية)
        total_waste_percentage = sum(data['waste_percentage'] for data in waste_analysis.values() 
                                    if isinstance(data, dict) and 'waste_percentage' in data)
        avg_waste = total_waste_percentage / len(waste_analysis) if waste_analysis else 0
        
        if avg_waste < 5:
            quality = 'ممتازة'
            score = 90
        elif avg_waste < 10:
            quality = 'جيدة'
            score = 80
        elif avg_waste < 15:
            quality = 'متوسطة'
            score = 70
        else:
            quality = 'ضعيفة'
            score = 50
        
        return {
            'quality': quality,
            'score': score,
            'total_harmonic_distortion': f"{avg_waste:.1f}%",  # تقديري
            'voltage_variation': 'ضمن الحدود' if avg_waste < 10 else 'خارج الحدود',
            'frequency_stability': 'مستقر' if avg_waste < 8 else 'غير مستقر'
        }
    
    def _calculate_reliability_index(self, hierarchy: Dict) -> Dict[str, Any]:
        """حساب مؤشر الاعتمادية"""
        # مؤشر مبسط يعتمد على كفاءة النظام
        network_loss = self._calculate_network_loss(hierarchy)
        efficiency = network_loss.get('network_efficiency', 0)
        
        # SAIDI (System Average Interruption Duration Index) تقديري
        if efficiency > 90:
            saidi = 1.2  # ساعات/سنة
            saifi = 0.8  # مرة/سنة
        elif efficiency > 80:
            saidi = 3.5
            saifi = 2.5
        elif efficiency > 70:
            saidi = 8.0
            saifi = 5.0
        else:
            saidi = 15.0
            saifi = 10.0
        
        return {
            'reliability': 'عالية' if efficiency > 85 else 'متوسطة' if efficiency > 75 else 'منخفضة',
            'efficiency_score': efficiency,
            'saidi': saidi,
            'saifi': saifi,
            'asa': 8760 - saidi,  # Annual Service Availability
            'customer_satisfaction': 'عالية' if saidi < 5 else 'متوسطة' if saidi < 10 else 'منخفضة'
        }
    
    def _generate_comparative_analysis(self, hierarchy: Dict) -> Dict[str, Any]:
        """تحليل مقارن مع معايير الصناعة"""
        network_loss = self._calculate_network_loss(hierarchy)
        industry_standards = {
            'excellent': {'loss': 5, 'efficiency': 95},
            'good': {'loss': 8, 'efficiency': 92},
            'average': {'loss': 12, 'efficiency': 88},
            'poor': {'loss': 15, 'efficiency': 85}
        }
        
        actual_efficiency = network_loss.get('network_efficiency', 0)
        actual_loss = 100 - actual_efficiency
        
        # مقارنة مع المعايير
        comparison = {}
        for level, standard in industry_standards.items():
            if actual_loss <= standard['loss']:
                comparison['industry_benchmark'] = level
                comparison['benchmark_efficiency'] = standard['efficiency']
                comparison['comparison'] = 'أفضل' if actual_efficiency > standard['efficiency'] else 'مماثل'
                break
        
        return {
            'actual_efficiency': actual_efficiency,
            'actual_loss': actual_loss,
            'industry_comparison': comparison,
            'improvement_potential': max(0, industry_standards['excellent']['efficiency'] - actual_efficiency),
            'key_gaps': self._identify_gaps_with_standards(hierarchy, industry_standards)
        }
    
    def _identify_gaps_with_standards(self, hierarchy: Dict, standards: Dict) -> List[str]:
        """تحديد الفجوات مع المعايير"""
        gaps = []
        
        # تحليل هدر المستويات
        pre_dist_waste = self._calculate_pre_distribution_waste(hierarchy)
        dist_box_waste = self._calculate_distribution_box_waste_corrected(hierarchy)
        main_meter_waste = self._calculate_main_meter_waste_corrected(hierarchy)
        
        if pre_dist_waste['waste_percentage'] > 8:
            gaps.append(f"هدر ما قبل التوزيع مرتفع ({pre_dist_waste['waste_percentage']:.1f}%)")
        
        if dist_box_waste['total_waste_percentage'] > 10:
            gaps.append(f"هدر علب التوزيع مرتفع ({dist_box_waste['total_waste_percentage']:.1f}%)")
        
        if main_meter_waste['total_waste_percentage'] > 12:
            gaps.append(f"هدر العدادت الرئيسية مرتفع ({main_meter_waste['total_waste_percentage']:.1f}%)")
        
        # تحليل التوازن
        load_dist = self._analyze_load_distribution(hierarchy)
        if load_dist.get('balance_score', 0) < 75:
            gaps.append("عدم توازن في توزيع الأحمال")
        
        return gaps
    
    def _generate_action_items(self, hierarchy: Dict, waste_analysis: Dict) -> List[Dict]:
        """توليد بنود عمل قابلة للتنفيذ"""
        actions = []
        
        # 1. تحليل هدر ما قبل التوزيع
        pre_dist_waste = self._calculate_pre_distribution_waste(hierarchy)
        if pre_dist_waste['waste_percentage'] > 10:
            actions.append({
                'priority': 'عالية',
                'action': 'فحص وتقليل الهدر ما قبل علب التوزيع',
                'description': f"هدر مرتفع ({pre_dist_waste['waste_percentage']:.1f}%) بين المولدة وعلب التوزيع: {pre_dist_waste.get('waste_type', '')}",
                'estimated_saving': pre_dist_waste['waste_amount'] * 0.3,
                'timeline': '2-4 أسابيع',
                'responsible': 'فريق الصيانة الرئيسي',
                'calculation': pre_dist_waste.get('calculation', '')
            })
        
        # 2. تحليل علب التوزيع
        dist_box_waste = self._calculate_distribution_box_waste_corrected(hierarchy)
        critical_boxes = [b for b in dist_box_waste['boxes_analysis'] 
                         if b['waste_percentage'] > 15 or b['waste_amount'] < 0]
        
        for box in critical_boxes[:5]:  # أول 5 علب حرجة
            actions.append({
                'priority': 'عالية' if box['waste_percentage'] > 15 else 'متوسطة',
                'action': f"فحص علبة التوزيع {box['box_name']}",
                'description': f"نسبة هدر: {box['waste_percentage']:.1f}% - {box.get('waste_type', '')}",
                'estimated_saving': box['absolute_waste'] * 0.4,
                'timeline': '1-2 أسابيع',
                'responsible': 'فني المنطقة',
                'calculation': box.get('calculation', '')
            })
        
        # 3. تحليل العدادات الرئيسية
        main_meter_waste = self._calculate_main_meter_waste_corrected(hierarchy)
        critical_meters = [m for m in main_meter_waste['meters_analysis'] 
                          if m['waste_percentage'] > 15 or m['waste_amount'] < 0]
        
        for meter in critical_meters[:5]:  # أول 5 عدادات حرجة
            actions.append({
                'priority': 'متوسطة',
                'action': f"فحص العداد الرئيسي {meter['meter_name']}",
                'description': f"نسبة هدر: {meter['waste_percentage']:.1f}% - {meter.get('waste_type', '')}",
                'estimated_saving': meter['absolute_waste'] * 0.5,
                'timeline': '1 أسبوع',
                'responsible': 'فني القطاع',
                'calculation': meter.get('calculation', '')
            })
        
        # 4. إذا كانت هناك مشاكل في الحسابات (سحب الأبناء > سحب الأب)
        validation = self._validate_calculations(hierarchy)
        if validation['total_issues'] > 0:
            actions.append({
                'priority': 'عالية',
                'action': 'مراجعة حسابات القياسات',
                'description': f"تم اكتشاف {validation['total_issues']} مشكلة في حسابات القياسات",
                'estimated_saving': 'غير محدد',
                'timeline': 'فوري',
                'responsible': 'مهندس النظام',
                'issues_count': validation['total_issues']
            })
        
        # 5. تحسين التوازن
        load_dist = self._analyze_load_distribution(hierarchy)
        if load_dist.get('balance_score', 0) < 80:
            actions.append({
                'priority': 'متوسطة',
                'action': 'تحسين توازن توزيع الأحمال',
                'description': 'تفاوت كبير في أحمال علب التوزيع',
                'estimated_saving': dist_box_waste['total_waste_amount'] * 0.2,
                'timeline': '4-8 أسابيع',
                'responsible': 'مهندس التوزيع'
            })
        
        # 6. إجراءات وقائية عامة
        actions.append({
            'priority': 'منخفضة',
            'action': 'الصيانة الوقائية الدورية',
            'description': 'فحص دوري للشبكة والمعدات',
            'estimated_saving': 'وقائي',
            'timeline': 'شهري',
            'responsible': 'فريق الصيانة'
        })
        
        return actions
    
    def _generate_hierarchy_summary(self, hierarchy: Dict, waste_analysis: Dict) -> Dict[str, Any]:
        """توليد ملاح شامل للنظام"""
        generator = hierarchy.get('meter', {})
        
        # جمع الإحصاءات
        stats = self._collect_hierarchy_statistics(hierarchy)
        
        # حساب المؤشرات الرئيسية
        network_loss = self._calculate_network_loss(hierarchy)
        pre_dist_waste = self._calculate_pre_distribution_waste(hierarchy)
        dist_box_waste = self._calculate_distribution_box_waste_corrected(hierarchy)
        main_meter_waste = self._calculate_main_meter_waste_corrected(hierarchy)
        
        summary = {
            'hierarchy_info': {
                'generator': generator.get('name', ''),
                'sector': generator.get('sector_name', ''),
                'total_levels': max([meter.get('hierarchy_level', 0) for data in waste_analysis.values() 
                                    if isinstance(data, dict) and data.get('meters') for meter in data['meters']], default=0) + 1 if waste_analysis else 1,
                'total_meters': stats['total_meters'],
                'total_customers': stats['total_customers'],
                'distribution_boxes': stats['distribution_boxes'],
                'main_meters': stats['main_meters']
            },
            'performance_indicators': {
                'total_withdrawal': generator.get('withdrawal_amount', 0),
                'network_efficiency': network_loss.get('network_efficiency', 0),
                'total_loss': network_loss.get('total_loss', 0),
                'loss_percentage': network_loss.get('loss_percentage', 0),
                'customers_per_meter': stats['total_customers'] / stats['total_meters'] 
                    if stats['total_meters'] > 0 else 0
            },
            'waste_breakdown': {
                'pre_distribution': {
                    'percentage': pre_dist_waste['waste_percentage'],
                    'amount': pre_dist_waste['waste_amount'],
                    'status': pre_dist_waste['status']
                },
                'distribution_boxes': {
                    'percentage': dist_box_waste['total_waste_percentage'],
                    'amount': dist_box_waste['total_waste_amount'],
                    'boxes_count': dist_box_waste['total_boxes'],
                    'problem_boxes': dist_box_waste.get('problem_count', 0)
                },
                'main_meters': {
                    'percentage': main_meter_waste['total_waste_percentage'],
                    'amount': main_meter_waste['total_waste_amount'],
                    'meters_count': main_meter_waste['total_meters'],
                    'problem_meters': len(main_meter_waste.get('problem_meters', []))
                }
            },
            'system_health': self._assess_system_health(hierarchy),
            'recommendations_summary': self._generate_recommendations_summary(hierarchy),
            'validation_status': self._validate_calculations(hierarchy)['status']
        }
        
        return summary
    
    def _collect_hierarchy_statistics(self, hierarchy: Dict) -> Dict[str, int]:
        """جمع إحصائيات الهيكل"""
        stats = {
            'total_meters': 0,
            'total_customers': 0,
            'distribution_boxes': 0,
            'main_meters': 0,
            'direct_customers': 0
        }
        
        def traverse(node: Dict):
            meter = node.get('meter', {})
            meter_type = meter.get('meter_type', '')
            
            if meter_type in ['مولدة', 'علبة توزيع', 'رئيسية']:
                stats['total_meters'] += 1
                
                if meter_type == 'علبة توزيع':
                    stats['distribution_boxes'] += 1
                elif meter_type == 'رئيسية':
                    stats['main_meters'] += 1
            
            elif meter_type == 'زبون':
                stats['total_customers'] += 1
            
            for child in node.get('children', []):
                traverse(child)
        
        traverse(hierarchy)
        return stats
    
    def _assess_system_health(self, hierarchy: Dict) -> Dict[str, Any]:
        """تقييم صحة النظام"""
        network_loss = self._calculate_network_loss(hierarchy)
        efficiency = network_loss.get('network_efficiency', 0)
        
        if efficiency >= 95:
            health = 'ممتاز'
            color = '#4CAF50'  # أخضر
            issues = 0
        elif efficiency >= 90:
            health = 'جيد جداً'
            color = '#8BC34A'  # أخضر فاتح
            issues = 1
        elif efficiency >= 85:
            health = 'جيد'
            color = '#FFC107'  # أصفر
            issues = 2
        elif efficiency >= 80:
            health = 'متوسط'
            color = '#FF9800'  # برتقالي
            issues = 3
        else:
            health = 'ضعيف'
            color = '#F44336'  # أحمر
            issues = 4
        
        return {
            'status': health,
            'color': color,
            'efficiency_score': efficiency,
            'critical_issues': issues,
            'maintenance_required': 'فوري' if issues >= 3 else 'قريب' if issues >= 2 else 'وقائي'
        }
    
    def _generate_recommendations_summary(self, hierarchy: Dict) -> Dict[str, Any]:
        """ملاح للتوصيات"""
        actions = self._generate_action_items(hierarchy, {})
        
        return {
            'total_actions': len(actions),
            'high_priority': len([a for a in actions if a['priority'] == 'عالية']),
            'medium_priority': len([a for a in actions if a['priority'] == 'متوسطة']),
            'low_priority': len([a for a in actions if a['priority'] == 'منخفضة']),
            'estimated_total_saving': sum([a.get('estimated_saving', 0) 
                                          for a in actions 
                                          if isinstance(a.get('estimated_saving'), (int, float))]),
            'timeline': {
                'short_term': '1-2 أسابيع',
                'medium_term': '2-4 أسابيع',
                'long_term': '4-8 أسابيع'
            }
        }
    
    # ==================== واجهات التقرير المفصلة ====================
    
    def generate_comprehensive_report(self, sector_id: int) -> Dict[str, Any]:
        """توليد تقرير شامل لكل شيء"""
        analysis = self.analyze_sector_hierarchy(sector_id)
        
        if not analysis.get('success'):
            return analysis
        
        # إضافة حسابات مالية
        financial_analysis = self._calculate_financial_impact(analysis['hierarchy'])
        
        # إضافة تحليل مقارن مع القطاعات الأخرى
        comparative_analysis = self._compare_with_other_sectors(sector_id)
        
        # إضافة توقعات وتحليل تنبؤي
        predictive_analysis = self._generate_predictive_analysis(analysis['hierarchy'])
        
        report = {
            **analysis,
            'financial_analysis': financial_analysis,
            'comparative_analysis': comparative_analysis,
            'predictive_analysis': predictive_analysis,
            'report_metadata': {
                'generated_at': datetime.now().isoformat(),
                'sector_id': sector_id,
                'report_version': '2.1',
                'report_type': 'شامل - مصحح'
            }
        }
        
        return report
    
    def _calculate_financial_impact(self, hierarchy: Dict) -> Dict[str, Any]:
        """حساب الأثر المالي للهدر"""
        # سعر الكيلوواط (يمكن جلبها من قاعدة البيانات)
        price_per_kwh = 7200  # افتراضي
        
        network_loss = self._calculate_network_loss(hierarchy)
        total_loss_kwh = network_loss.get('total_loss', 0)
        
        # حساب الخسارة اليومية والشهرية والسنوية
        daily_loss = total_loss_kwh
        monthly_loss = daily_loss * 30
        annual_loss = daily_loss * 365
        
        daily_cost = daily_loss * price_per_kwh
        monthly_cost = monthly_loss * price_per_kwh
        annual_cost = annual_loss * price_per_kwh
        
        return {
            'price_per_kwh': price_per_kwh,
            'loss_analysis': {
                'daily_kwh': daily_loss,
                'monthly_kwh': monthly_loss,
                'annual_kwh': annual_loss,
                'daily_cost': daily_cost,
                'monthly_cost': monthly_cost,
                'annual_cost': annual_cost
            },
            'summary': f"الخسارة الشهرية: {monthly_cost:,.0f} ل.س - الخسارة السنوية: {annual_cost:,.0f} ل.س"
        }
    
    def _compare_with_other_sectors(self, current_sector_id: int) -> Dict[str, Any]:
        """مقارنة القطاع الحالي مع القطاعات الأخرى"""
        try:
            from database.connection import db
            
            with db.get_cursor() as cursor:
                # جلب جميع القطاعات
                cursor.execute("""
                    SELECT id, name, code 
                    FROM sectors 
                    WHERE is_active = TRUE 
                    ORDER BY name
                """)
                sectors = cursor.fetchall()
                
                sector_comparisons = []
                
                for sector in sectors:
                    if sector['id'] == current_sector_id:
                        continue
                    
                    # تحليل كل قطاع
                    sector_analysis = self.analyze_sector_hierarchy(sector['id'])
                    if sector_analysis.get('success'):
                        summary = sector_analysis.get('summary', {})
                        performance = summary.get('performance_indicators', {})
                        
                        sector_comparisons.append({
                            'sector_id': sector['id'],
                            'sector_name': sector['name'],
                            'efficiency': performance.get('network_efficiency', 0),
                            'total_customers': summary.get('hierarchy_info', {}).get('total_customers', 0),
                            'total_loss_percentage': performance.get('loss_percentage', 0)
                        })
                
                # ترتيب القطاعات حسب الكفاءة
                sector_comparisons.sort(key=lambda x: x['efficiency'], reverse=True)
                
                # العثور على ترتيب القطاع الحالي
                current_rank = None
                current_efficiency = None
                
                for i, sector in enumerate(sector_comparisons, 1):
                    if sector['sector_id'] == current_sector_id:
                        current_rank = i
                        current_efficiency = sector['efficiency']
                        break
                
                # حساب المتوسطات
                efficiencies = [s['efficiency'] for s in sector_comparisons]
                avg_efficiency = statistics.mean(efficiencies) if efficiencies else 0
                
                return {
                    'total_sectors_compared': len(sector_comparisons),
                    'current_sector_rank': current_rank or len(sector_comparisons) + 1,
                    'current_sector_efficiency': current_efficiency or 0,
                    'average_efficiency': avg_efficiency,
                    'best_sector': sector_comparisons[0] if sector_comparisons else None,
                    'worst_sector': sector_comparisons[-1] if sector_comparisons else None,
                    'sector_rankings': sector_comparisons[:10]  # أفضل 10 قطاعات فقط
                }
                
        except Exception as e:
            logger.error(f"خطأ في المقارنة مع القطاعات الأخرى: {e}")
            return {'error': str(e)}
    
    def _generate_predictive_analysis(self, hierarchy: Dict) -> Dict[str, Any]:
        """توليد تحليل تنبؤي"""
        # جمع بيانات تاريخية (هنا نستخدم البيانات الحالية كنقطة بداية)
        current_stats = self._collect_hierarchy_statistics(hierarchy)
        network_loss = self._calculate_network_loss(hierarchy)
        current_efficiency = network_loss.get('network_efficiency', 0)
        
        # توقعات مستقبلية (تنبؤات بسيطة)
        predictions = {
            'next_month': {
                'efficiency': max(0, min(100, current_efficiency * 0.98)),  # افتراضي -2%
                'customers_growth': current_stats['total_customers'] * 1.02,  # نمو 2%
                'load_growth': 1.03  # نمو أحمال 3%
            },
            'next_quarter': {
                'efficiency': max(0, min(100, current_efficiency * 0.95)),
                'customers_growth': current_stats['total_customers'] * 1.05,
                'load_growth': 1.08
            },
            'next_year': {
                'efficiency': max(0, min(100, current_efficiency * 0.9)),
                'customers_growth': current_stats['total_customers'] * 1.15,
                'load_growth': 1.2
            }
        }
        
        # تحذيرات
        warnings = []
        if current_efficiency < 80:
            warnings.append("الكفاءة منخفضة - تحتاج لإجراءات عاجلة")
        if current_stats['total_customers'] / current_stats['total_meters'] > 30:
            warnings.append("نسبة الزبائن للعداد عالية - قد تحتاج لتوسيع الشبكة")
        
        return {
            'current_baseline': {
                'efficiency': current_efficiency,
                'total_customers': current_stats['total_customers'],
                'total_meters': current_stats['total_meters']
            },
            'predictions': predictions,
            'warnings': warnings,
            'recommendations': [
                "تركيب أنظمة مراقبة ذكية",
                "تحديث المعدات القديمة",
                "تدريب الفنيين على كشف الهدر",
                "تطبيق صيانة وقائية منتظمة"
            ]
        }

    def _calculate_main_meter_waste_corrected(self, hierarchy: Dict) -> Dict[str, Any]:
        """حساب هدر العلب - الإصدار المصحح"""
        main_meters = []
        
        def find_main_meters(node: Dict):
            if not node:
                return
            
            meter = node.get('meter', {})
            meter_type = meter.get('meter_type', '')
            
            if meter_type in ['رئيسية', 'main_meter']:
                # حساب هدر هذا العداد الرئيسي
                meter_withdrawal = float(meter.get('withdrawal_amount') or 0)
                children_withdrawal = 0
                customers_analysis = []
                total_children = node.get('children_count', 0)  # عدد الأبناء الكلي
                
                for child in node.get('children', []):
                    child_meter = child.get('meter', {})
                    child_withdrawal = float(child_meter.get('withdrawal_amount') or 0)
                    children_withdrawal += child_withdrawal
                    
                    if child_meter.get('meter_type') in ['زبون', 'customer']:
                        customers_analysis.append({
                            'name': child_meter.get('name', ''),
                            'withdrawal': child_withdrawal,
                            'current_balance': child_meter.get('current_balance', 0)
                        })
                
                # حساب الهدر
                waste_amount = meter_withdrawal - children_withdrawal
                
                if waste_amount < 0:
                    waste_type = "⚠️ مشكلة: سحب الزبائن أكبر من العداد"
                    absolute_waste = abs(waste_amount)
                    efficiency = 100  # إذا كان سحب الزبائن أكبر، فالكفاءة 100%
                else:
                    waste_type = "هدر طبيعي"
                    absolute_waste = waste_amount
                    efficiency = (children_withdrawal / meter_withdrawal * 100) if meter_withdrawal > 0 else 0
                
                waste_percentage = (absolute_waste / meter_withdrawal * 100) if meter_withdrawal > 0 else 0
                
                main_meters.append({
                    'meter': meter,
                    'meter_name': meter.get('name', ''),
                    'meter_withdrawal': meter_withdrawal,
                    'customers_withdrawal': children_withdrawal,
                    'waste_amount': waste_amount,
                    'absolute_waste': absolute_waste,
                    'waste_percentage': waste_percentage,
                    'efficiency': min(efficiency, 100),
                    'waste_type': waste_type,
                    'customers_count': len(customers_analysis),
                    'total_children_count': total_children,  # عدد الأبناء الكلي
                    'customers_analysis': customers_analysis,
                    'parent_box': self._find_parent_box_name(node, hierarchy),
                    'calculation': f"{meter_withdrawal} - {children_withdrawal} = {waste_amount}",
                    'status': 'حرج' if waste_percentage > 15 else 'مرتفع' if waste_percentage > 8 else 'طبيعي' if waste_percentage > 0 else 'ممتاز'
                })
            
            # البحث في الأبناء
            for child in node.get('children', []):
                find_main_meters(child)
        
        find_main_meters(hierarchy)
        
        # حساب الإجماليات
        total_meters = len(main_meters)
        
        if total_meters > 0:
            total_meter_withdrawal = sum(m['meter_withdrawal'] for m in main_meters)
            total_customers_withdrawal = sum(m['customers_withdrawal'] for m in main_meters)
            total_absolute_waste = sum(m['absolute_waste'] for m in main_meters)
            
            if total_meter_withdrawal > 0:
                total_efficiency = (total_customers_withdrawal / total_meter_withdrawal) * 100
            else:
                total_efficiency = 0
            
            total_waste_percentage = (total_absolute_waste / total_meter_withdrawal * 100) if total_meter_withdrawal > 0 else 0
        else:
            total_meter_withdrawal = 0
            total_customers_withdrawal = 0
            total_absolute_waste = 0
            total_efficiency = 0
            total_waste_percentage = 0
        
        # ترتيب العدادات حسب الهدر
        main_meters_sorted = sorted(main_meters, 
                                key=lambda x: x['waste_percentage'], 
                                reverse=True)
        
        return {
            'name': 'هدر العلب',
            'description': 'الفرق بين سحب العداد الرئيسي والزبائن الخاصين به',
            'total_meters': total_meters,
            'total_meter_withdrawal': total_meter_withdrawal,
            'total_customers_withdrawal': total_customers_withdrawal,
            'total_waste_amount': total_absolute_waste,
            'total_waste_percentage': total_waste_percentage,
            'total_efficiency': min(total_efficiency, 100),
            'average_waste_per_meter': total_absolute_waste / total_meters if total_meters > 0 else 0,
            'meters_analysis': main_meters_sorted,
            'problem_meters': [m for m in main_meters if m['waste_amount'] < 0],
            'critical_meters': [m for m in main_meters_sorted if m['waste_percentage'] > 15],
            'warning_meters': [m for m in main_meters_sorted if 5 < m['waste_percentage'] <= 15],
            'efficient_meters': [m for m in main_meters_sorted if m['waste_percentage'] <= 5],
            'summary_table': [
                {
                    'العداد': m['meter_name'],
                    'سحب العداد': f"{m['meter_withdrawal']:.1f}",
                    'سحب الزبائن': f"{m['customers_withdrawal']:.1f}",
                    'عدد الزبائن': m['customers_count'],
                    'عدد الأبناء': m['total_children_count'],  # إضافة عدد الأبناء
                    'الهدر': f"{m['absolute_waste']:.1f}",
                    'نسبة الهدر%': f"{m['waste_percentage']:.1f}",
                    'الكفاءة%': f"{m['efficiency']:.1f}",
                    'العلبة الأم': m['parent_box'],
                    'الحالة': m['status']
                }
                for m in main_meters_sorted
            ]
        }        