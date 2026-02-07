# ui/hierarchical_waste_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Dict, List, Any
import threading
from datetime import datetime
import webbrowser
import json

logger = logging.getLogger(__name__)

class HierarchicalWasteUI(tk.Frame):
    """واجهة تحليل الهدر الهرمي متعددة المستويات - الإصدار المحسن"""
    
    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.user_data = user_data
        self.sectors = []
        self.current_report = None
        self.current_sector_id = None
        
        # ألوان الواجهة
        self.colors = {
            'primary': '#283593',     # أزرق داكن
            'secondary': '#5c6bc0',   # أزرق
            'accent': '#2196f3',      # أزرق فاتح
            'light': '#f5f7fa',
            'dark': '#263238',
            'success': '#388e3c',
            'warning': '#ffa000',
            'danger': '#d32f2f',
            'info': '#00bcd4',
            
            # ألوان المستويات
            'generator': '#283593',   # مولدة
            'distribution_box': '#5c6bc0',  # علب توزيع
            'main_meter': '#9fa8da',  # عدادات رئيسية
            'customer': '#e8eaf6',    # زبائن
            
            # ألوان الحالة
            'critical': '#d32f2f',
            'high': '#f57c00',
            'medium': '#fbc02d',
            'low': '#4caf50',
            'normal': '#2196f3'
        }
        
        self.load_dependencies()
        self.create_widgets()
        self.load_initial_data()
    
    def load_dependencies(self):
        """تحميل التبعيات"""
        try:
            from modules.waste_calculator import HierarchicalWasteCalculator
            self.waste_calculator = HierarchicalWasteCalculator()
            
            from database.connection import db
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id, name FROM sectors WHERE is_active = TRUE ORDER BY name")
                self.sectors = cursor.fetchall()
                
        except Exception as e:
            logger.error(f"خطأ في تحميل التبعيات: {e}")
            messagebox.showerror("خطأ", f"لا يمكن تحميل حاسبة الهدر الهرمية: {str(e)}")
    
    def create_widgets(self):
        """إنشاء واجهة متعددة المستويات"""
        self.configure(bg=self.colors['light'])
        
        # شريط العنوان
        self.create_header()
        
        # دفتر الملاحظات الرئيسي
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # تبويبات التحليل
        self.create_hierarchy_tab()      # الهيكل الهرمي
        self.create_waste_levels_tab()   # مستويات الهدر
        self.create_financial_tab()      # التحليل المالي
        self.create_comparison_tab()     # المقارنات
        self.create_actions_tab()        # بنود العمل
        self.create_full_report_tab()    # التقرير الكامل
        self.create_calculation_tab()    # تفاصيل الحسابات
        
        # شريط الحالة
        self.status_bar = tk.Frame(self, bg=self.colors['dark'], height=30)
        self.status_bar.pack(fill='x', padx=5, pady=(0, 5))
        self.status_bar.pack_propagate(False)
        
        self.status_label = tk.Label(self.status_bar,
                                    text="⚡ نظام التحليل الهرمي للهدر جاهز",
                                    bg=self.colors['dark'],
                                    fg='white',
                                    font=('Arial', 9))
        self.status_label.pack(side='left', padx=10)
        
        # زر المساعدة
        tk.Button(self.status_bar, text="❔ مساعدة", 
                 command=self.show_help,
                 bg=self.colors['accent'],
                 fg='white',
                 font=('Arial', 9),
                 padx=10).pack(side='right', padx=5)
    
    def create_header(self):
        """إنشاء شريط العنوان"""
        header = tk.Frame(self, bg=self.colors['primary'], height=120)
        header.pack(fill='x', padx=0, pady=0)
        header.pack_propagate(False)
        
        # العنوان
        title_frame = tk.Frame(header, bg=self.colors['primary'])
        title_frame.pack(expand=True)
        
        tk.Label(title_frame,
                text="🏗️ نظام التحليل الهرمي للهدر الكهربائي",
                font=('Arial', 20, 'bold'),
                bg=self.colors['primary'],
                fg='white').pack(pady=(10, 0))
        
        tk.Label(title_frame,
               text="4 مستويات: مولدة ← علب توزيع ← عدادات رئيسية ← زبائن",
               font=('Arial', 11),
               bg=self.colors['primary'],
               fg='#bbdefb').pack(pady=(0, 10))
        
        # شريط التحكم
        self.create_control_bar(header)
        
    def create_control_bar(self, parent):
        """شريط التحكم"""
        control_bar = tk.Frame(parent, bg=self.colors['dark'], height=40)
        control_bar.pack(fill='x', side='bottom')
        control_bar.pack_propagate(False)
        
        # اختيار القطاع
        tk.Label(control_bar, text="اختر القطاع:", 
                font=('Arial', 10),
                bg=self.colors['dark'],
                fg='white').pack(side='left', padx=(10, 5))
        
        self.sector_var = tk.StringVar()
        self.sector_combo = ttk.Combobox(control_bar, textvariable=self.sector_var,
                                        values=[s['name'] for s in self.sectors],
                                        state='readonly',
                                        font=('Arial', 10),
                                        width=25)
        self.sector_combo.pack(side='left', padx=5)
        self.sector_combo.bind('<<ComboboxSelected>>', self.on_sector_selected)
        
        # أزرار التحكم
        control_buttons = [
            ("🔍 تحليل مفصل", self.analyze_sector, self.colors['primary']),
            ("📊 تحليل مالي", self.show_financial_analysis, self.colors['success']),
            ("📈 مقارنة", self.show_comparison, self.colors['warning']),
            ("📋 تقرير كامل", self.generate_full_report, self.colors['info']),
            ("🧮 تفاصيل الحسابات", self.show_calculations, self.colors['accent']),
            ("🖨️ تصدير", self.export_report, self.colors['secondary']),
            ("🔄 تحديث", self.refresh_data, '#9c27b0')
        ]
        
        for text, command, color in control_buttons:
            btn = tk.Button(control_bar, text=text, command=command,
                        bg=color, fg='white',
                        font=('Arial', 9),
                        padx=10, pady=4)
            btn.pack(side='left', padx=2, pady=5)
    
    def create_hierarchy_tab(self):
        """تبويب عرض الهيكل الهرمي"""
        self.hierarchy_tab = tk.Frame(self.notebook, bg=self.colors['light'])
        self.notebook.add(self.hierarchy_tab, text='🏗️ الهيكل الهرمي')
        
        # إطار العرض
        self.hierarchy_frame = tk.Frame(self.hierarchy_tab, bg=self.colors['light'])
        self.hierarchy_frame.pack(fill='both', expand=True)
        
        # رسالة ترحيبية
        self.hierarchy_welcome = tk.Label(self.hierarchy_frame,
                                         text="👈 اختر قطاعاً لعرض الهيكل الهرمي للهدر",
                                         font=('Arial', 14),
                                         bg=self.colors['light'],
                                         fg=self.colors['dark'])
        self.hierarchy_welcome.pack(expand=True)
    
    def create_waste_levels_tab(self):
        """تبويب مستويات الهدر"""
        self.levels_tab = tk.Frame(self.notebook, bg=self.colors['light'])
        self.notebook.add(self.levels_tab, text='📉 مستويات الهدر')
        
        self.levels_frame = tk.Frame(self.levels_tab, bg=self.colors['light'])
        self.levels_frame.pack(fill='both', expand=True)
        
        tk.Label(self.levels_frame,
                text="سيظهر هنا تحليل تفصيلي للهدر على كل مستوى",
                font=('Arial', 12),
                bg=self.colors['light'],
                fg=self.colors['dark']).pack(expand=True)
    
    def create_financial_tab(self):
        """تبويب التحليل المالي"""
        self.financial_tab = tk.Frame(self.notebook, bg=self.colors['light'])
        self.notebook.add(self.financial_tab, text='💰 التحليل المالي')
        
        self.financial_frame = tk.Frame(self.financial_tab, bg=self.colors['light'])
        self.financial_frame.pack(fill='both', expand=True)
        
        tk.Label(self.financial_frame,
                text="سيظهر هنا التأثير المالي للهدر وإمكانيات التوفير",
                font=('Arial', 12),
                bg=self.colors['light'],
                fg=self.colors['dark']).pack(expand=True)
    
    def create_comparison_tab(self):
        """تبويب المقارنات"""
        self.comparison_tab = tk.Frame(self.notebook, bg=self.colors['light'])
        self.notebook.add(self.comparison_tab, text='📊 المقارنات')
        
        self.comparison_frame = tk.Frame(self.comparison_tab, bg=self.colors['light'])
        self.comparison_frame.pack(fill='both', expand=True)
        
        tk.Label(self.comparison_frame,
                text="سيظهر هنا مقارنة القطاع مع القطاعات الأخرى",
                font=('Arial', 12),
                bg=self.colors['light'],
                fg=self.colors['dark']).pack(expand=True)
    
    def create_actions_tab(self):
        """تبويب بنود العمل"""
        self.actions_tab = tk.Frame(self.notebook, bg=self.colors['light'])
        self.notebook.add(self.actions_tab, text='🛠️ بنود العمل')
        
        self.actions_frame = tk.Frame(self.actions_tab, bg=self.colors['light'])
        self.actions_frame.pack(fill='both', expand=True)
        
        tk.Label(self.actions_frame,
                text="سيظهر هنا قائمة الإجراءات القابلة للتنفيذ",
                font=('Arial', 12),
                bg=self.colors['light'],
                fg=self.colors['dark']).pack(expand=True)
    
    def create_full_report_tab(self):
        """تبويب التقرير الكامل"""
        self.report_tab = tk.Frame(self.notebook, bg=self.colors['light'])
        self.notebook.add(self.report_tab, text='📋 التقرير الكامل')
        
        self.report_frame = tk.Frame(self.report_tab, bg=self.colors['light'])
        self.report_frame.pack(fill='both', expand=True)
        
        tk.Label(self.report_frame,
                text="سيظهر هنا التقرير الشامل لكل شيء",
                font=('Arial', 12),
                bg=self.colors['light'],
                fg=self.colors['dark']).pack(expand=True)
    
    def create_calculation_tab(self):
        """تبويب تفاصيل الحسابات"""
        self.calculation_tab = tk.Frame(self.notebook, bg=self.colors['light'])
        self.notebook.add(self.calculation_tab, text='🧮 تفاصيل الحسابات')
        
        self.calculation_frame = tk.Frame(self.calculation_tab, bg=self.colors['light'])
        self.calculation_frame.pack(fill='both', expand=True)
        
        tk.Label(self.calculation_frame,
                text="سيظهر هنا تفاصيل الحسابات الرياضية للهدر",
                font=('Arial', 12),
                bg=self.colors['light'],
                fg=self.colors['dark']).pack(expand=True)
    
    def load_initial_data(self):
        """تحميل البيانات الأولية"""
        self.status_label.config(text="⚡ نظام التحليل الهرمي جاهز للاستخدام")
    
    def on_sector_selected(self, event=None):
        """عند اختيار قطاع"""
        sector_name = self.sector_var.get()
        if not sector_name:
            return
        
        # العثور على معرف القطاع
        self.current_sector_id = None
        for sector in self.sectors:
            if sector['name'] == sector_name:
                self.current_sector_id = sector['id']
                break
        
        if self.current_sector_id:
            self.analyze_sector(self.current_sector_id)
    
    def analyze_sector(self, sector_id=None):
        """تحليل القطاع"""
        if not sector_id:
            if not self.current_sector_id:
                messagebox.showwarning("تحذير", "يرجى اختيار قطاع أولاً")
                return
            sector_id = self.current_sector_id
        
        self.status_label.config(text=f"جاري تحليل القطاع...")
        
        # التحليل في خيط منفصل
        threading.Thread(target=self._analyze_sector_background, 
                        args=(sector_id,), daemon=True).start()
    
    def _analyze_sector_background(self, sector_id):
        """تحليل القطاع في الخلفية"""
        try:
            report = self.waste_calculator.generate_comprehensive_report(sector_id)
            self.after(0, self._display_analysis, report)
        except Exception as e:
            self.after(0, self._show_error, "خطأ في التحليل", str(e))
    
    def _display_analysis(self, report):
        """عرض نتائج التحليل"""
        if not report.get('success'):
            self._show_error("خطأ في التحليل", report.get('error', 'خطأ غير معروف'))
            return
        
        self.current_report = report
        self.status_label.config(text="✅ تم تحليل القطاع بنجاح")
        
        # عرض في كل التبويبات
        self.display_hierarchy_enhanced(report)
        self.display_waste_levels_enhanced(report)
        self.display_financial_analysis_enhanced(report)
        self.display_comparison(report)
        self.display_actions_enhanced(report)
        self.display_full_report_enhanced(report)
        self.display_calculation_details(report)
    
    def display_hierarchy_enhanced(self, report):
        """عرض الهيكل الهرمي في جداول مميزة"""
        for widget in self.hierarchy_frame.winfo_children():
            widget.destroy()
        
        hierarchy = report.get('hierarchy', {})
        if not hierarchy:
            return
        
        # إنشاء إطار رئيسي مع Canvas للتمرير
        main_container = tk.Frame(self.hierarchy_frame, bg='white')
        main_container.pack(fill='both', expand=True)
        
        # Create canvas with scrollbar
        canvas = tk.Canvas(main_container, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient='vertical', command=canvas.yview)
        content_frame = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        content_frame.bind("<Configure>", on_frame_configure)
        
        # عنوان التبويب
        title_frame = tk.Frame(content_frame, bg=self.colors['primary'], height=50)
        title_frame.pack(fill='x', padx=10, pady=(10, 5))
        title_frame.pack_propagate(False)
        
        tk.Label(title_frame,
                text="🏗️ الهيكل الهرمي للشبكة الكهربائية",
                font=('Arial', 14, 'bold'),
                bg=self.colors['primary'],
                fg='white').pack(expand=True)
        
        # عرض المولدة في جدول
        self._display_generator_table(content_frame, hierarchy)
        
        # عرض علب التوزيع في جدول
        detailed_analysis = report.get('detailed_analysis', {})
        if detailed_analysis:
            dist_box_analysis = detailed_analysis.get('distribution_box_waste', {})
            if dist_box_analysis:
                self._display_distribution_boxes_table(content_frame, dist_box_analysis)
        
        # عرض العدادات الرئيسية في جدول
        main_meter_analysis = detailed_analysis.get('main_meter_waste', {}) if detailed_analysis else {}
        if main_meter_analysis:
            self._display_main_meters_table(content_frame, main_meter_analysis)
        
        canvas.pack(side='left', fill='both', expand=True, padx=(10, 0))
        scrollbar.pack(side='right', fill='y', padx=(0, 10))
    
    def _display_generator_table(self, parent, hierarchy):
        """عرض جدول المولدة"""
        meter = hierarchy.get('meter', {})
        
        table_frame = tk.Frame(parent, bg='white', relief='solid', borderwidth=1)
        table_frame.pack(fill='x', padx=10, pady=5)
        
        # عنوان الجدول
        title_label = tk.Label(table_frame,
                              text="🔌 المولدة الرئيسية",
                              font=('Arial', 12, 'bold'),
                              bg=self.colors['generator'],
                              fg='white',
                              padx=10,
                              pady=5)
        title_label.pack(fill='x')
        
        # إنشاء Treeview
        columns = ['النوع', 'الاسم', 'السحب (ك.و)', 'عدد الأبناء', 'سحب الأبناء (ك.و)', 'الهدر (ك.و)', 'نسبة الهدر%', 'الكفاءة%', 'الحالة']
        
        tree_frame = tk.Frame(table_frame, bg='white')
        tree_frame.pack(fill='x', padx=10, pady=10)
        
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=2)
        
        # تحديد عرض الأعمدة
        column_widths = [80, 150, 100, 80, 120, 100, 100, 80, 100]
        
        for col, width in zip(columns, column_widths):
            tree.heading(col, text=col)
            tree.column(col, width=width, anchor='center')
        
        # إضافة بيانات المولدة
        children_count = hierarchy.get('children_count', 0)
        children_withdrawal = hierarchy.get('total_children_withdrawal', 0)
        waste_amount = hierarchy.get('waste_amount', 0)
        waste_percentage = hierarchy.get('waste_percentage', 0)
        efficiency = hierarchy.get('efficiency', 0)
        
        # تحديد الحالة
        status = "حرج" if waste_percentage > 15 else "مرتفع" if waste_percentage > 8 else "طبيعي" if waste_percentage > 0 else "ممتاز"
        
        tree.insert('', 'end', values=[
            meter.get('type_arabic', 'مولدة'),
            meter.get('name', ''),
            f"{meter.get('withdrawal_amount', 0):.1f}",
            children_count,
            f"{children_withdrawal:.1f}",
            f"{waste_amount:.1f}",
            f"{waste_percentage:.1f}%",
            f"{efficiency:.1f}%",
            status
        ])
        
        # تلوين الصف حسب الحالة
        if status == "حرج":
            tree.tag_configure('critical', background='#ffebee')
            tree.item(tree.get_children()[0], tags=('critical',))
        elif status == "مرتفع":
            tree.tag_configure('warning', background='#fff3e0')
            tree.item(tree.get_children()[0], tags=('warning',))
        
        tree.pack(fill='x')
        
        # عرض تفاصيل الحساب
        calc_frame = tk.Frame(table_frame, bg='#f5f5f5')
        calc_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        calc_text = f"📐 الحساب: {meter.get('withdrawal_amount', 0):.1f} - {children_withdrawal:.1f} = {waste_amount:.1f} ك.و"
        tk.Label(calc_frame, text=calc_text,
                font=('Arial', 10),
                bg='#f5f5f5',
                fg=self.colors['dark']).pack(pady=5)
    
    def _display_distribution_boxes_table(self, parent, dist_box_analysis):
        """عرض جدول علب التوزيع"""
        boxes_data = dist_box_analysis.get('detailed_box_analysis', [])
        
        if not boxes_data:
            return
        
        table_frame = tk.Frame(parent, bg='white', relief='solid', borderwidth=1)
        table_frame.pack(fill='x', padx=10, pady=5)
        
        # عنوان الجدول
        title_label = tk.Label(table_frame,
                              text=f"📦 علب التوزيع ({dist_box_analysis.get('total_boxes', 0)})",
                              font=('Arial', 12, 'bold'),
                              bg=self.colors['distribution_box'],
                              fg='white',
                              padx=10,
                              pady=5)
        title_label.pack(fill='x')
        
        # إحصائيات عامة
        stats_frame = tk.Frame(table_frame, bg='#e8eaf6')
        stats_frame.pack(fill='x', padx=10, pady=(10, 0))
        
        stats_text = f"""
        عدد علب التوزيع: {dist_box_analysis.get('total_boxes', 0)} | إجمالي السحب: {dist_box_analysis.get('total_box_withdrawal', 0):.1f} ك.و
        إجمالي هدر علب التوزيع: {dist_box_analysis.get('total_waste_amount', 0):.1f} ك.و | نسبة الهدر الإجمالية: {dist_box_analysis.get('total_waste_percentage', 0):.1f}%
        """
        
        tk.Label(stats_frame,
                text=stats_text,
                font=('Arial', 10),
                bg='#e8eaf6',
                justify='left').pack(padx=10, pady=5)
        
        # إنشاء Treeview مفصل
        columns = ['رقم العلبة', 'اسم العلبة', 'سحب العلبة (ك.و)', 'عدد الأبناء', 'سحب الأبناء (ك.و)', 'الهدر (ك.و)', 'نسبة الهدر%', 'الكفاءة%', 'الحالة']
        
        tree_frame = tk.Frame(table_frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # شريط التمرير
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        tree = ttk.Treeview(tree_frame, 
                           columns=columns, 
                           show='headings',
                           yscrollcommand=vsb.set,
                           xscrollcommand=hsb.set,
                           height=min(len(boxes_data), 10))
        
        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)
        
        # تحديد عرض الأعمدة
        column_widths = [80, 150, 100, 80, 120, 100, 100, 80, 100]
        
        for col, width in zip(columns, column_widths):
            tree.heading(col, text=col)
            tree.column(col, width=width, anchor='center')
        
        # إضافة البيانات
        for box in boxes_data:
            values = [
                box.get('box_number', ''),
                box.get('box_name', ''),
                f"{box.get('box_withdrawal', 0):.1f}",
                box.get('children_count', 0),
                f"{box.get('children_withdrawal', 0):.1f}",
                f"{box.get('waste', 0):.1f}",
                f"{box.get('waste_percentage', 0):.1f}%",
                f"{box.get('efficiency', 0):.1f}%",
                box.get('status', '')
            ]
            
            item = tree.insert('', 'end', values=values)
            
            # تلوين حسب الحالة
            status = box.get('status', '')
            waste_type = box.get('waste_type', '')
            
            if "مشكلة" in waste_type:
                tree.tag_configure('problem', background='#ffebee')
                tree.item(item, tags=('problem',))
            elif status == 'حرج':
                tree.tag_configure('critical', background='#ffebee')
                tree.item(item, tags=('critical',))
            elif status == 'مرتفع':
                tree.tag_configure('warning', background='#fff3e0')
                tree.item(item, tags=('warning',))
            elif status == 'طبيعي':
                tree.tag_configure('normal', background='#e8f5e9')
                tree.item(item, tags=('normal',))
            elif status == 'ممتاز':
                tree.tag_configure('excellent', background='#e3f2fd')
                tree.item(item, tags=('excellent',))
        
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # عرض الملاحظات
        if dist_box_analysis.get('problem_count', 0) > 0:
            notes_frame = tk.Frame(table_frame, bg='#fff3e0', relief='solid', borderwidth=1)
            notes_frame.pack(fill='x', padx=10, pady=(0, 10))
            
            notes_text = f"⚠️ يوجد {dist_box_analysis.get('problem_count', 0)} علبة توزيع بها مشاكل في الحسابات (سحب الأبناء أكبر من سحب العلبة)"
            tk.Label(notes_frame, text=notes_text,
                    font=('Arial', 10, 'bold'),
                    bg='#fff3e0',
                    fg=self.colors['warning']).pack(padx=10, pady=5)
    
    def _display_main_meters_table(self, parent, main_meter_analysis):
        """عرض جدول العدادات الرئيسية"""
        meters_data = main_meter_analysis.get('summary_table', [])
        
        if not meters_data:
            return
        
        table_frame = tk.Frame(parent, bg='white', relief='solid', borderwidth=1)
        table_frame.pack(fill='x', padx=10, pady=5)
        
        # عنوان الجدول
        title_label = tk.Label(table_frame,
                            text=f"🔢 العدادات الرئيسية ({main_meter_analysis.get('total_meters', 0)})",
                            font=('Arial', 12, 'bold'),
                            bg=self.colors['main_meter'],
                            fg='black',
                            padx=10,
                            pady=5)
        title_label.pack(fill='x')
        
        # إحصائيات عامة
        stats_frame = tk.Frame(table_frame, bg='#f5f5f5')
        stats_frame.pack(fill='x', padx=10, pady=(10, 0))
        
        total_customers = 0
        total_children = 0
        for m in meters_data:
            # معالجة عدد الزبائن
            customers_value = m.get('عدد الزبائن', 0)
            if customers_value is not None:
                try:
                    if isinstance(customers_value, (int, float)):
                        total_customers += int(customers_value)
                    elif isinstance(customers_value, str):
                        # محاولة تحويل النص إلى عدد
                        if customers_value.replace('.', '', 1).isdigit():
                            total_customers += int(float(customers_value))
                except (ValueError, TypeError):
                    pass
            
            # معالجة عدد الأبناء
            children_value = m.get('عدد الأبناء', 0)
            if children_value is not None:
                try:
                    if isinstance(children_value, (int, float)):
                        total_children += int(children_value)
                    elif isinstance(children_value, str):
                        # محاولة تحويل النص إلى عدد
                        if children_value.replace('.', '', 1).isdigit():
                            total_children += int(float(children_value))
                except (ValueError, TypeError):
                    pass        
        stats_text = f"""
        عدد العدادات: {main_meter_analysis.get('total_meters', 0)} | إجمالي السحب: {main_meter_analysis.get('total_meter_withdrawal', 0):.1f} ك.و
        إجمالي الهدر: {main_meter_analysis.get('total_waste_amount', 0):.1f} ك.و | نسبة الهدر الإجمالية: {main_meter_analysis.get('total_waste_percentage', 0):.1f}%
        عدد الزبائن الكلي: {total_customers} | عدد الأبناء الكلي: {total_children}
        """
        
        tk.Label(stats_frame,
                text=stats_text,
                font=('Arial', 10),
                bg='#f5f5f5',
                justify='left').pack(padx=10, pady=5)
        
        # إنشاء Treeview مع عمود "عدد الأبناء"
        columns = ['العداد', 'سحب العداد (ك.و)', 'سحب الزبائن (ك.و)', 'عدد الزبائن', 'عدد الأبناء', 'الهدر (ك.و)', 'نسبة الهدر%', 'الكفاءة%', 'العلبة الأم', 'الحالة']
        
        tree_frame = tk.Frame(table_frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # شريط التمرير
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        tree = ttk.Treeview(tree_frame, 
                        columns=columns, 
                        show='headings',
                        yscrollcommand=vsb.set,
                        xscrollcommand=hsb.set,
                        height=min(len(meters_data), 12))
        
        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)
        
        # تحديد عرض الأعمدة
        column_widths = [120, 90, 100, 80, 80, 80, 90, 80, 120, 80]
        
        for col, width in zip(columns, column_widths):
            tree.heading(col, text=col)
            tree.column(col, width=width, anchor='center')
        
        # إضافة البيانات مع تلوين حسب عدد الأبناء
        for meter in meters_data:
            # تحويل الأعداد من نص إلى أرقام إذا لزم الأمر
            try:
                num_customers = int(meter.get('عدد الزبائن', 0))
            except (ValueError, TypeError):
                num_customers = 0
                
            try:
                num_children = int(meter.get('عدد الأبناء', 0))
            except (ValueError, TypeError):
                num_children = 0
            
            values = [
                meter.get('العداد', ''),
                meter.get('سحب العداد', '0.0'),
                meter.get('سحب الزبائن', '0.0'),
                str(num_customers),
                str(num_children),
                meter.get('الهدر', '0.0'),
                meter.get('نسبة الهدر%', '0.0%'),
                meter.get('الكفاءة%', '0.0%'),
                meter.get('العلبة الأم', ''),
                meter.get('الحالة', '')
            ]
            
            item = tree.insert('', 'end', values=values)
            
            # تلوين حسب الحالة
            status = meter.get('الحالة', '')
            waste_percentage = float(meter.get('نسبة الهدر%', '0.0').replace('%', '') or 0)
            
            if status == 'حرج' or waste_percentage > 15:
                tree.tag_configure('critical', background='#ffebee')
                tree.item(item, tags=('critical',))
            elif status == 'مرتفع' or (5 < waste_percentage <= 15):
                tree.tag_configure('warning', background='#fff3e0')
                tree.item(item, tags=('warning',))
            elif status == 'طبيعي' or (0 < waste_percentage <= 5):
                tree.tag_configure('normal', background='#e8f5e9')
                tree.item(item, tags=('normal',))
            elif status == 'ممتاز' or waste_percentage == 0:
                tree.tag_configure('excellent', background='#e3f2fd')
                tree.item(item, tags=('excellent',))
            
            # تلوين خاص للأعداد المرتفعة من الأبناء
            if num_children > 10:
                tree.tag_configure('many_children', background='#fff3e0')
                tree.item(item, tags=('many_children',))
        
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        

    def display_waste_levels_enhanced(self, report):
        """عرض مستويات الهدر في تبويبات مفصلة"""
        for widget in self.levels_frame.winfo_children():
            widget.destroy()
        
        detailed_analysis = report.get('detailed_analysis', {})
        if not detailed_analysis:
            return
        
        # إنشاء Notebook داخلي
        inner_notebook = ttk.Notebook(self.levels_frame)
        inner_notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # تبويب 1: هدر ما قبل علب التوزيع
        pre_dist_tab = tk.Frame(inner_notebook, bg='white')
        inner_notebook.add(pre_dist_tab, text='ما قبل علب التوزيع')
        
        # تبويب 2: هدر علب التوزيع
        dist_box_tab = tk.Frame(inner_notebook, bg='white')
        inner_notebook.add(dist_box_tab, text='علب التوزيع')
        
        # تبويب 3: هدر العدادات الرئيسية
        main_meter_tab = tk.Frame(inner_notebook, bg='white')
        inner_notebook.add(main_meter_tab, text='العدادات الرئيسية')
        
        # تبويب 4: الخسائر الإجمالية
        network_loss_tab = tk.Frame(inner_notebook, bg='white')
        inner_notebook.add(network_loss_tab, text='الخسائر الإجمالية')
        
        # ملء التبويبات
        self._fill_pre_distribution_tab(pre_dist_tab, detailed_analysis.get('pre_distribution_waste', {}))
        self._fill_distribution_box_tab(dist_box_tab, detailed_analysis.get('distribution_box_waste', {}))
        self._fill_main_meter_tab(main_meter_tab, detailed_analysis.get('main_meter_waste', {}))
        self._fill_network_loss_tab(network_loss_tab, detailed_analysis.get('network_loss', {}))
    
    def _fill_pre_distribution_tab(self, parent, analysis):
        """ملء تبويب هدر ما قبل علب التوزيع"""
        for widget in parent.winfo_children():
            widget.destroy()
        
        if not analysis:
            return
        
        # إنشاء Canvas للتمرير
        canvas = tk.Canvas(parent, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        content.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # العنوان
        tk.Label(content, 
                text="⚡ هدر ما قبل علب التوزيع",
                font=('Arial', 14, 'bold'),
                bg='white',
                fg=self.colors['primary']).pack(pady=(10, 5))
        
        # الوصف
        tk.Label(content, 
                text=analysis.get('description', ''),
                font=('Arial', 10),
                bg='white',
                fg=self.colors['dark']).pack(pady=(0, 10))
        
        # إطار البيانات
        data_frame = tk.Frame(content, bg='white', relief='solid', borderwidth=1)
        data_frame.pack(fill='x', padx=20, pady=10)
        
        # بيانات الهدر
        data_points = [
            ('المولدة:', analysis.get('generator_name', '')),
            ('سحب المولدة (ك.و):', f"{analysis.get('generator_withdrawal', 0):.1f}"),
            ('عدد الأبناء المباشرين:', analysis.get('direct_children_count', 0)),
            ('سحب الأبناء المباشرين (ك.و):', f"{analysis.get('direct_children_withdrawal', 0):.1f}"),
            ('كمية الهدر (ك.و):', f"{analysis.get('waste_amount', 0):.1f}"),
            ('نسبة الهدر (%):', f"{analysis.get('waste_percentage', 0):.1f}%"),
            ('الكفاءة (%):', f"{analysis.get('efficiency', 0):.1f}%"),
            ('نوع الهدر:', analysis.get('waste_type', '')),
            ('الحالة:', analysis.get('status', ''))
        ]
        
        for i, (label, value) in enumerate(data_points):
            row_frame = tk.Frame(data_frame, bg='white')
            row_frame.pack(fill='x', padx=10, pady=5)
            
            tk.Label(row_frame, text=label, 
                    font=('Arial', 10, 'bold'),
                    bg='white',
                    width=25,
                    anchor='w').pack(side='left')
            
            tk.Label(row_frame, text=value,
                    font=('Arial', 10),
                    bg='white',
                    fg=self.colors['dark']).pack(side='left')
        
        # عرض تفاصيل الحساب
        calc_frame = tk.Frame(content, bg='#f5f5f5', relief='solid', borderwidth=1)
        calc_frame.pack(fill='x', padx=20, pady=10)
        
        calc_text = f"📐 تفاصيل الحساب: {analysis.get('calculation', '')}"
        tk.Label(calc_frame, text=calc_text,
                font=('Arial', 10, 'bold'),
                bg='#f5f5f5',
                fg=self.colors['primary']).pack(padx=10, pady=10)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def _fill_distribution_box_tab(self, parent, analysis):
        """ملء تبويب هدر علب التوزيع"""
        for widget in parent.winfo_children():
            widget.destroy()
        
        if not analysis:
            return
        
        # إنشاء Canvas للتمرير
        canvas = tk.Canvas(parent, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        content.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # العنوان
        tk.Label(content, 
                text="📦 هدر علب التوزيع والكابلات",
                font=('Arial', 14, 'bold'),
                bg='white',
                fg=self.colors['primary']).pack(pady=(10, 5))
        
        # الوصف
        tk.Label(content, 
                text=analysis.get('description', ''),
                font=('Arial', 10),
                bg='white',
                fg=self.colors['dark']).pack(pady=(0, 10))
        
        # إحصائيات عامة
        stats_frame = tk.Frame(content, bg='#e8eaf6', relief='solid', borderwidth=1)
        stats_frame.pack(fill='x', padx=20, pady=10)
        
        stats_data = [
            ('عدد علب التوزيع:', f"{analysis.get('total_boxes', 0)}"),
            ('إجمالي سحب العلب (ك.و):', f"{analysis.get('total_box_withdrawal', 0):.1f}"),
            ('إجمالي سحب الأبناء (ك.و):', f"{analysis.get('total_children_withdrawal', 0):.1f}"),
            ('إجمالي الهدر (ك.و):', f"{analysis.get('total_waste_amount', 0):.1f}"),
            ('نسبة الهدر الإجمالية (%):', f"{analysis.get('total_waste_percentage', 0):.1f}%"),
            ('الكفاءة الإجمالية (%):', f"{analysis.get('total_efficiency', 0):.1f}%"),
            ('متوسط الهدر لكل علبة (ك.و):', f"{analysis.get('average_waste_per_box', 0):.1f}"),
            ('عدد العلب الحرجة:', f"{len(analysis.get('critical_boxes', []))}"),
            ('عدد العلب بالمشاكل:', f"{analysis.get('problem_count', 0)}")
        ]
        
        for i, (label, value) in enumerate(stats_data):
            row_frame = tk.Frame(stats_frame, bg='#e8eaf6')
            row_frame.pack(fill='x', padx=10, pady=5)
            
            tk.Label(row_frame, text=label, 
                    font=('Arial', 10, 'bold'),
                    bg='#e8eaf6',
                    width=30,
                    anchor='w').pack(side='left')
            
            tk.Label(row_frame, text=value,
                    font=('Arial', 10),
                    bg='#e8eaf6',
                    fg=self.colors['dark']).pack(side='left')
        
        # إذا كانت هناك مشاكل
        if analysis.get('problem_count', 0) > 0:
            warning_frame = tk.Frame(content, bg='#fff3e0', relief='solid', borderwidth=1)
            warning_frame.pack(fill='x', padx=20, pady=10)
            
            warning_text = f"⚠️ تنبيه: يوجد {analysis.get('problem_count', 0)} علبة توزيع بها مشاكل في القياسات"
            tk.Label(warning_frame, text=warning_text,
                    font=('Arial', 10, 'bold'),
                    bg='#fff3e0',
                    fg=self.colors['warning']).pack(padx=10, pady=10)
            
            # عرض أسماء العلب بالمشاكل
            problem_boxes = analysis.get('problem_boxes', [])
            if problem_boxes:
                problem_text = "العلب المتأثرة: " + ", ".join([b['box_name'] for b in problem_boxes[:5]])
                if len(problem_boxes) > 5:
                    problem_text += f" و{len(problem_boxes) - 5} أخرى"
                
                tk.Label(warning_frame, text=problem_text,
                        font=('Arial', 9),
                        bg='#fff3e0',
                        fg=self.colors['dark']).pack(padx=10, pady=(0, 10))
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def _fill_main_meter_tab(self, parent, analysis):
        """ملء تبويب هدر العدادات الرئيسية"""
        for widget in parent.winfo_children():
            widget.destroy()
        
        if not analysis:
            return
        
        # إنشاء Canvas للتمرير
        canvas = tk.Canvas(parent, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        content.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # العنوان
        tk.Label(content, 
                text="🔢 هدر العدادت الرئيسية",
                font=('Arial', 14, 'bold'),
                bg='white',
                fg=self.colors['primary']).pack(pady=(10, 5))
        
        # الوصف
        tk.Label(content, 
                text=analysis.get('description', ''),
                font=('Arial', 10),
                bg='white',
                fg=self.colors['dark']).pack(pady=(0, 10))
        
        # إحصائيات عامة
        stats_frame = tk.Frame(content, bg='#f5f5f5', relief='solid', borderwidth=1)
        stats_frame.pack(fill='x', padx=20, pady=10)
        
        stats_data = [
            ('عدد العدادات:', f"{analysis.get('total_meters', 0)}"),
            ('إجمالي سحب العدادات (ك.و):', f"{analysis.get('total_meter_withdrawal', 0):.1f}"),
            ('إجمالي سحب الزبائن (ك.و):', f"{analysis.get('total_customers_withdrawal', 0):.1f}"),
            ('إجمالي الهدر (ك.و):', f"{analysis.get('total_waste_amount', 0):.1f}"),
            ('نسبة الهدر الإجمالية (%):', f"{analysis.get('total_waste_percentage', 0):.1f}%"),
            ('الكفاءة الإجمالية (%):', f"{analysis.get('total_efficiency', 0):.1f}%"),
            ('متوسط الهدر لكل عداد (ك.و):', f"{analysis.get('average_waste_per_meter', 0):.1f}"),
            ('عدد العدادات الحرجة:', f"{len(analysis.get('critical_meters', []))}"),
            ('عدد العدادات بالمشاكل:', f"{len(analysis.get('problem_meters', []))}")
        ]
        
        for i, (label, value) in enumerate(stats_data):
            row_frame = tk.Frame(stats_frame, bg='#f5f5f5')
            row_frame.pack(fill='x', padx=10, pady=5)
            
            tk.Label(row_frame, text=label, 
                    font=('Arial', 10, 'bold'),
                    bg='#f5f5f5',
                    width=30,
                    anchor='w').pack(side='left')
            
            tk.Label(row_frame, text=value,
                    font=('Arial', 10),
                    bg='#f5f5f5',
                    fg=self.colors['dark']).pack(side='left')
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def _fill_network_loss_tab(self, parent, analysis):
        """ملء تبويب الخسائر الإجمالية"""
        for widget in parent.winfo_children():
            widget.destroy()
        
        if not analysis:
            return
        
        # إنشاء Canvas للتمرير
        canvas = tk.Canvas(parent, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        content.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # العنوان
        tk.Label(content, 
                text="🌐 خسائر الشبكة الإجمالية",
                font=('Arial', 14, 'bold'),
                bg='white',
                fg=self.colors['primary']).pack(pady=(10, 5))
        
        # الوصف
        tk.Label(content, 
                text=analysis.get('description', ''),
                font=('Arial', 10),
                bg='white',
                fg=self.colors['dark']).pack(pady=(0, 10))
        
        # إحصائيات عامة
        stats_frame = tk.Frame(content, bg='#e3f2fd', relief='solid', borderwidth=1)
        stats_frame.pack(fill='x', padx=20, pady=10)
        
        stats_data = [
            ('السحب الكلي من المولدة (ك.و):', f"{analysis.get('total_withdrawal', 0):.1f}"),
            ('إجمالي سحب جميع الزبائن (ك.و):', f"{analysis.get('total_customers_withdrawal', 0):.1f}"),
            ('الخسارة الإجمالية (ك.و):', f"{analysis.get('total_loss', 0):.1f}"),
            ('نسبة الخسارة (%):', f"{analysis.get('loss_percentage', 0):.1f}%"),
            ('كفاءة الشبكة (%):', f"{analysis.get('network_efficiency', 0):.1f}%"),
            ('عدد الزبائن:', analysis.get('customers_count', 0)),
            ('متوسط سحب الزبون الواحد (ك.و):', f"{analysis.get('average_customer_withdrawal', 0):.1f}"),
            ('حالة الشبكة:', analysis.get('status', ''))
        ]
        
        for i, (label, value) in enumerate(stats_data):
            row_frame = tk.Frame(stats_frame, bg='#e3f2fd')
            row_frame.pack(fill='x', padx=10, pady=5)
            
            tk.Label(row_frame, text=label, 
                    font=('Arial', 10, 'bold'),
                    bg='#e3f2fd',
                    width=30,
                    anchor='w').pack(side='left')
            
            tk.Label(row_frame, text=value,
                    font=('Arial', 10),
                    bg='#e3f2fd',
                    fg=self.colors['dark']).pack(side='left')
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def display_financial_analysis_enhanced(self, report):
        """عرض التحليل المالي"""
        for widget in self.financial_frame.winfo_children():
            widget.destroy()
        
        financial = report.get('financial_analysis', {})
        if not financial:
            return
        
        # إنشاء Canvas للتمرير
        canvas = tk.Canvas(self.financial_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.financial_frame, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        content.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # العنوان
        tk.Label(content,
                text="💰 التحليل المالي للخسائر",
                font=('Arial', 14, 'bold'),
                bg='white',
                fg=self.colors['primary']).pack(pady=(10, 20))
        
        # معلومات السعر
        price_frame = tk.Frame(content, bg='#f5f5f5', relief='solid', borderwidth=1)
        price_frame.pack(fill='x', padx=20, pady=5)
        
        tk.Label(price_frame,
                text=f"💰 سعر الكيلوواط الساعي: {financial.get('price_per_kwh', 0):,.0f} ل.س",
                font=('Arial', 12, 'bold'),
                bg='#f5f5f5',
                fg=self.colors['success']).pack(padx=10, pady=10)
        
        # الخسائر اليومية والشهرية والسنوية
        loss_analysis = financial.get('loss_analysis', {})
        
        periods = [
            ('اليومية', loss_analysis.get('daily_kwh', 0), loss_analysis.get('daily_cost', 0)),
            ('الشهرية', loss_analysis.get('monthly_kwh', 0), loss_analysis.get('monthly_cost', 0)),
            ('السنوية', loss_analysis.get('annual_kwh', 0), loss_analysis.get('annual_cost', 0))
        ]
        
        for period_name, kwh, cost in periods:
            period_frame = tk.Frame(content, bg='#e8f5e9' if period_name == 'اليومية' else '#e3f2fd' if period_name == 'الشهرية' else '#fff3e0',
                                   relief='solid', borderwidth=1)
            period_frame.pack(fill='x', padx=20, pady=5)
            
            tk.Label(period_frame, 
                    text=f"الخسارة {period_name}: {kwh:,.1f} ك.و ↔ {cost:,.0f} ل.س",
                    font=('Arial', 11, 'bold'),
                    bg=period_frame['bg'],
                    fg=self.colors['dark']).pack(padx=10, pady=10)
        
        # ملخص مالي
        summary_frame = tk.Frame(content, bg='#f5f5f5', relief='solid', borderwidth=1)
        summary_frame.pack(fill='x', padx=20, pady=10)
        
        summary_text = f"""
        📊 الملخص المالي:
        
        • الخسارة الشهرية: {loss_analysis.get('monthly_cost', 0):,.0f} ل.س
        • الخسارة السنوية: {loss_analysis.get('annual_cost', 0):,.0f} ل.س
        • سعر الكيلوواط: {financial.get('price_per_kwh', 0):,.0f} ل.س
        
        💡 توفير محتمل:
        يمكن توفير ما يصل إلى {loss_analysis.get('monthly_cost', 0) * 0.3:,.0f} ل.س شهرياً
        من خلال تحسين الكفاءة بنسبة 30%
        """
        
        tk.Label(summary_frame,
                text=summary_text,
                font=('Arial', 11),
                bg='#f5f5f5',
                fg=self.colors['dark'],
                justify='left').pack(padx=20, pady=10)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def display_comparison(self, report):
        """عرض المقارنات"""
        for widget in self.comparison_frame.winfo_children():
            widget.destroy()
        
        # هذه الميزة تحت التطوير
        tk.Label(self.comparison_frame,
                text="🔄 ميزة المقارنات قيد التطوير",
                font=('Arial', 14, 'bold'),
                bg=self.colors['light'],
                fg=self.colors['primary']).pack(pady=50)
    
    def display_actions_enhanced(self, report):
        """عرض بنود العمل"""
        for widget in self.actions_frame.winfo_children():
            widget.destroy()
        
        reports_data = report.get('reports', {})
        actions = reports_data.get('action_items', [])
        
        if not actions:
            tk.Label(self.actions_frame,
                    text="✅ لا توجد إجراءات مطلوبة حالياً",
                    font=('Arial', 14),
                    bg=self.colors['light'],
                    fg=self.colors['success']).pack(pady=50)
            return
        
        # إنشاء Canvas للتمرير
        canvas = tk.Canvas(self.actions_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.actions_frame, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        content.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        tk.Label(content, text="🛠️ بنود العمل القابلة للتنفيذ",
                font=('Arial', 14, 'bold'),
                bg='white',
                fg=self.colors['primary']).pack(pady=(10, 20))
        
        # عد الإجراءات حسب الأولوية
        priority_counts = {
            'عالية': len([a for a in actions if a['priority'] == 'عالية']),
            'متوسطة': len([a for a in actions if a['priority'] == 'متوسطة']),
            'منخفضة': len([a for a in actions if a['priority'] == 'منخفضة'])
        }
        
        stats_frame = tk.Frame(content, bg='#f5f5f5', relief='solid', borderwidth=1)
        stats_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        stats_text = f"📊 إجمالي الإجراءات: {len(actions)} (عالي: {priority_counts['عالية']} | متوسط: {priority_counts['متوسطة']} | منخفض: {priority_counts['منخفضة']})"
        tk.Label(stats_frame, text=stats_text,
                font=('Arial', 11),
                bg='#f5f5f5').pack(padx=10, pady=10)
        
        # عرض الإجراءات
        for i, action in enumerate(actions, 1):
            self._display_action_item_enhanced(content, action, i)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def _display_action_item_enhanced(self, parent, action, index):
        """عرض بند عمل واحد بشكل محسن"""
        # تحديد لون حسب الأولوية
        priority_colors = {
            'عالية': '#ffebee',
            'متوسطة': '#fff3e0',
            'منخفضة': '#e8f5e9'
        }
        
        bg_color = priority_colors.get(action.get('priority', ''), '#f5f5f5')
        
        frame = tk.Frame(parent, bg=bg_color, relief='solid', borderwidth=1)
        frame.pack(fill='x', padx=20, pady=5)
        
        # الرقم والعنوان
        header = tk.Frame(frame, bg=bg_color)
        header.pack(fill='x', padx=10, pady=(10, 5))
        
        tk.Label(header, text=f"{index}. {action.get('action', '')}",
                font=('Arial', 11, 'bold'),
                bg=bg_color,
                fg=self.colors['dark']).pack(side='left')
        
        # الأولوية
        priority_color = '#d32f2f' if action.get('priority') == 'عالية' else '#f57c00' if action.get('priority') == 'متوسطة' else '#4caf50'
        tk.Label(header, text=f"الأولوية: {action.get('priority', '')}",
                font=('Arial', 10, 'bold'),
                bg=bg_color,
                fg=priority_color).pack(side='right')
        
        # التفاصيل
        details = tk.Frame(frame, bg=bg_color)
        details.pack(fill='x', padx=20, pady=(0, 10))
        
        details_text = f"""
        الوصف: {action.get('description', '')}
        التوفير المتوقع: {action.get('estimated_saving', 0):,.0f} ك.و
        الجدول الزمني: {action.get('timeline', '')}
        المسؤول: {action.get('responsible', '')}
        """
        
        tk.Label(details, text=details_text,
                font=('Arial', 9),
                bg=bg_color,
                fg=self.colors['dark'],
                justify='left').pack(anchor='w')
        
        # إذا كان هناك تفاصيل حساب
        if action.get('calculation'):
            calc_frame = tk.Frame(details, bg='#f5f5f5', relief='solid', borderwidth=1)
            calc_frame.pack(fill='x', pady=(5, 0))
            
            tk.Label(calc_frame, text=f"🧮 {action.get('calculation', '')}",
                    font=('Arial', 8),
                    bg='#f5f5f5',
                    fg=self.colors['dark']).pack(padx=5, pady=2)
    
    def display_full_report_enhanced(self, report):
        """عرض التقرير الكامل"""
        for widget in self.report_frame.winfo_children():
            widget.destroy()
        
        # إنشاء Canvas للتمرير
        canvas = tk.Canvas(self.report_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.report_frame, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        content.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        summary = report.get('summary', {})
        executive = report.get('reports', {}).get('executive_summary', {})
        financial = report.get('financial_analysis', {})
        validation = report.get('validation', {})
        
        tk.Label(content,
                text="📋 التقرير الشامل - ملخص تنفيذي",
                font=('Arial', 16, 'bold'),
                bg='white',
                fg=self.colors['primary']).pack(pady=(20, 10))
        
        if summary:
            hierarchy_info = summary.get('hierarchy_info', {})
            performance = summary.get('performance_indicators', {})
            waste_breakdown = summary.get('waste_breakdown', {})
            system_health = summary.get('system_health', {})
            
            # معلومات النظام
            sys_frame = tk.Frame(content, bg='#f5f5f5', relief='solid', borderwidth=1)
            sys_frame.pack(fill='x', padx=20, pady=10)
            
            sys_text = f"""
            🏢 معلومات النظام:
            • القطاع: {hierarchy_info.get('sector', '')}
            • المولدة: {hierarchy_info.get('generator', '')}
            • عدد العدادات: {hierarchy_info.get('total_meters', 0)}
            • عدد علب التوزيع: {hierarchy_info.get('distribution_boxes', 0)}
            • عدد العدادات الرئيسية: {hierarchy_info.get('main_meters', 0)}
            • عدد الزبائن: {hierarchy_info.get('total_customers', 0)}
            """
            
            tk.Label(sys_frame, text=sys_text,
                    font=('Arial', 11),
                    bg='#f5f5f5',
                    fg=self.colors['dark'],
                    justify='left').pack(padx=20, pady=10)
            
            # أداء النظام
            perf_frame = tk.Frame(content, bg='#e3f2fd', relief='solid', borderwidth=1)
            perf_frame.pack(fill='x', padx=20, pady=10)
            
            perf_text = f"""
            ⚡ أداء النظام:
            • السحب الكلي: {performance.get('total_withdrawal', 0):,.0f} ك.و
            • كفاءة الشبكة: {performance.get('network_efficiency', 0):.1f}%
            • الخسائر الكلية: {performance.get('loss_percentage', 0):.1f}%
            • حالة النظام: {executive.get('system_status', 'غير معروف')}
            """
            
            tk.Label(perf_frame, text=perf_text,
                    font=('Arial', 11),
                    bg='#e3f2fd',
                    fg=self.colors['dark'],
                    justify='left').pack(padx=20, pady=10)
            
            # تفصيل الهدر
            waste_frame = tk.Frame(content, bg='#f5f5f5', relief='solid', borderwidth=1)
            waste_frame.pack(fill='x', padx=20, pady=10)
            
            waste_text = f"""
            📉 تفصيل الهدر:
            
            1. هدر ما قبل علب التوزيع:
               • النسبة: {waste_breakdown.get('pre_distribution', {}).get('percentage', 0):.1f}%
               • الكمية: {waste_breakdown.get('pre_distribution', {}).get('amount', 0):.1f} ك.و
               • الحالة: {waste_breakdown.get('pre_distribution', {}).get('status', '')}
            
            2. هدر علب التوزيع:
               • النسبة: {waste_breakdown.get('distribution_boxes', {}).get('percentage', 0):.1f}%
               • الكمية: {waste_breakdown.get('distribution_boxes', {}).get('amount', 0):.1f} ك.و
               • عدد العلب: {waste_breakdown.get('distribution_boxes', {}).get('boxes_count', 0)}
               • العلب بالمشاكل: {waste_breakdown.get('distribution_boxes', {}).get('problem_boxes', 0)}
            
            3. هدر العدادات الرئيسية:
               • النسبة: {waste_breakdown.get('main_meters', {}).get('percentage', 0):.1f}%
               • الكمية: {waste_breakdown.get('main_meters', {}).get('amount', 0):.1f} ك.و
               • عدد العدادات: {waste_breakdown.get('main_meters', {}).get('meters_count', 0)}
               • العدادات بالمشاكل: {waste_breakdown.get('main_meters', {}).get('problem_meters', 0)}
            """
            
            tk.Label(waste_frame, text=waste_text,
                    font=('Arial', 11),
                    bg='#f5f5f5',
                    fg=self.colors['dark'],
                    justify='left').pack(padx=20, pady=10)
            
            # التأثير المالي
            if financial:
                fin_frame = tk.Frame(content, bg='#e8f5e9', relief='solid', borderwidth=1)
                fin_frame.pack(fill='x', padx=20, pady=10)
                
                loss_analysis = financial.get('loss_analysis', {})
                fin_text = f"""
                💰 التأثير المالي:
                • الخسارة اليومية: {loss_analysis.get('daily_cost', 0):,.0f} ل.س
                • الخسارة الشهرية: {loss_analysis.get('monthly_cost', 0):,.0f} ل.س
                • الخسارة السنوية: {loss_analysis.get('annual_cost', 0):,.0f} ل.س
                • سعر الكيلوواط: {financial.get('price_per_kwh', 0):,.0f} ل.س
                """
                
                tk.Label(fin_frame, text=fin_text,
                        font=('Arial', 11),
                        bg='#e8f5e9',
                        fg=self.colors['dark'],
                        justify='left').pack(padx=20, pady=10)
            
            # حالة النظام
            health_frame = tk.Frame(content, bg='#fff3e0', relief='solid', borderwidth=1)
            health_frame.pack(fill='x', padx=20, pady=10)
            
            health_text = f"""
            🏥 حالة النظام:
            • الحالة: {system_health.get('status', '')}
            • كفاءة النظام: {system_health.get('efficiency_score', 0):.1f}%
            • المشاكل الحرجة: {system_health.get('critical_issues', 0)}
            • الصيانة المطلوبة: {system_health.get('maintenance_required', '')}
            • حالة التحقق: {summary.get('validation_status', 'غير معروف')}
            """
            
            tk.Label(health_frame, text=health_text,
                    font=('Arial', 11),
                    bg='#fff3e0',
                    fg=self.colors['dark'],
                    justify='left').pack(padx=20, pady=10)
            
            # التوصيات
            rec_summary = summary.get('recommendations_summary', {})
            rec_frame = tk.Frame(content, bg='#f3e5f5', relief='solid', borderwidth=1)
            rec_frame.pack(fill='x', padx=20, pady=10)
            
            rec_text = f"""
            💡 التوصيات:
            • إجمالي الإجراءات: {rec_summary.get('total_actions', 0)}
            • عالية الأولوية: {rec_summary.get('high_priority', 0)}
            • متوسطة الأولوية: {rec_summary.get('medium_priority', 0)}
            • منخفضة الأولوية: {rec_summary.get('low_priority', 0)}
            • التوفير المتوقع: {rec_summary.get('estimated_total_saving', 0):,.0f} ك.و
            """
            
            tk.Label(rec_frame, text=rec_text,
                    font=('Arial', 11),
                    bg='#f3e5f5',
                    fg=self.colors['dark'],
                    justify='left').pack(padx=20, pady=10)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def display_calculation_details(self, report):
        """عرض تفاصيل الحسابات"""
        for widget in self.calculation_frame.winfo_children():
            widget.destroy()
        
        calculation_details = report.get('calculation_details', {})
        validation = report.get('validation', {})
        
        if not calculation_details:
            return
        
        # إنشاء Canvas للتمرير
        canvas = tk.Canvas(self.calculation_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.calculation_frame, orient='vertical', command=canvas.yview)
        content = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        content.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        tk.Label(content,
                text="🧮 تفاصيل الحسابات الرياضية",
                font=('Arial', 16, 'bold'),
                bg='white',
                fg=self.colors['primary']).pack(pady=(20, 10))
        
        # ملخص الحسابات
        if validation.get('total_issues', 0) > 0:
            warning_frame = tk.Frame(content, bg='#ffebee', relief='solid', borderwidth=1)
            warning_frame.pack(fill='x', padx=20, pady=10)
            
            warning_text = f"⚠️ تم اكتشاف {validation.get('total_issues', 0)} مشكلة في الحسابات"
            tk.Label(warning_frame, text=warning_text,
                    font=('Arial', 12, 'bold'),
                    bg='#ffebee',
                    fg=self.colors['danger']).pack(padx=10, pady=10)
        
        # تفاصيل حسابات علب التوزيع
        box_calcs = calculation_details.get('box_calculations', [])
        if box_calcs:
            box_frame = tk.Frame(content, bg='#f5f5f5', relief='solid', borderwidth=1)
            box_frame.pack(fill='x', padx=20, pady=10)
            
            tk.Label(box_frame, text="📦 حسابات علب التوزيع",
                    font=('Arial', 12, 'bold'),
                    bg='#f5f5f5',
                    fg=self.colors['primary']).pack(pady=(10, 5))
            
            for calc in box_calcs:
                calc_text = f"• {calc['box']} ← {calc['parent']}: {calc['calculation']}"
                tk.Label(box_frame, text=calc_text,
                        font=('Arial', 10),
                        bg='#f5f5f5',
                        fg=self.colors['dark'],
                        justify='left').pack(anchor='w', padx=20, pady=2)
        
        # تفاصيل حسابات العدادات الرئيسية
        meter_calcs = calculation_details.get('meter_calculations', [])
        if meter_calcs:
            meter_frame = tk.Frame(content, bg='#f5f5f5', relief='solid', borderwidth=1)
            meter_frame.pack(fill='x', padx=20, pady=10)
            
            tk.Label(meter_frame, text="🔢 حسابات العدادات الرئيسية",
                    font=('Arial', 12, 'bold'),
                    bg='#f5f5f5',
                    fg=self.colors['primary']).pack(pady=(10, 5))
            
            for calc in meter_calcs:
                calc_text = f"• {calc['meter']} ← {calc['parent']}: {calc['calculation']}"
                tk.Label(meter_frame, text=calc_text,
                        font=('Arial', 10),
                        bg='#f5f5f5',
                        fg=self.colors['dark'],
                        justify='left').pack(anchor='w', padx=20, pady=2)
        
        # معلومات التقرير
        meta = report.get('report_metadata', {})
        meta_frame = tk.Frame(content, bg='#e8f5e9', relief='solid', borderwidth=1)
        meta_frame.pack(fill='x', padx=20, pady=10)
        
        meta_text = f"""
        📄 معلومات التقرير:
        • تم إنشاؤه في: {meta.get('generated_at', 'غير معروف')}
        • رقم القطاع: {meta.get('sector_id', 'غير معروف')}
        • إصدار التقرير: {meta.get('report_version', 'غير معروف')}
        • نوع التقرير: {meta.get('report_type', 'غير معروف')}
        """
        
        tk.Label(meta_frame, text=meta_text,
                font=('Arial', 10),
                bg='#e8f5e9',
                fg=self.colors['dark'],
                justify='left').pack(padx=20, pady=10)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def show_financial_analysis(self):
        """عرض التحليل المالي"""
        if not self.current_report:
            messagebox.showinfo("معلومة", "يرجى تحليل قطاع أولاً")
            return
        
        self.notebook.select(self.financial_tab)
    
    def show_comparison(self):
        """عرض المقارنات"""
        if not self.current_report:
            messagebox.showinfo("معلومة", "يرجى تحليل قطاع أولاً")
            return
        
        self.notebook.select(self.comparison_tab)
    
    def generate_full_report(self):
        """توليد تقرير كامل"""
        if not self.current_report:
            messagebox.showinfo("معلومة", "يرجى تحليل قطاع أولاً")
            return
        
        self.notebook.select(self.report_tab)
        messagebox.showinfo("تقرير", "التقرير الشامل جاهز للعرض والتصدير")
    
    def show_calculations(self):
        """عرض تفاصيل الحسابات"""
        if not self.current_report:
            messagebox.showinfo("معلومة", "يرجى تحليل قطاع أولاً")
            return
        
        self.notebook.select(self.calculation_tab)
    
    def export_report(self):
        """تصدير التقرير"""
        if not self.current_report:
            messagebox.showinfo("معلومة", "لا يوجد تقرير للتصدير")
            return
        
        # عرض خيارات التصدير
        from tkinter import simpledialog
        options = ["JSON", "PDF (قريباً)", "Excel (قريباً)", "طباعة (قريباً)"]
        
        choice = simpledialog.askstring("تصدير التقرير",
                                       "اختر نوع الملف:\n" + "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)]),
                                       parent=self)
        
        if choice and choice.isdigit() and 1 <= int(choice) <= len(options):
            if int(choice) == 1:  # JSON
                self._export_to_json()
            else:
                messagebox.showinfo("قريباً", f"ميزة التصدير إلى {options[int(choice)-1]} قيد التطوير")
        else:
            self._export_to_json()
    
    def _export_to_json(self):
        """تصدير التقرير إلى JSON"""
        try:
            import json
            from datetime import datetime
            
            # تنظيف التقرير للتخزين (إزالة أي كائنات غير قابلة للتسلسل)
            report_to_export = self._clean_report_for_export(self.current_report)
            
            # إنشاء اسم الملف
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sector_name = self.sector_var.get().replace(" ", "_")
            filename = f"تقرير_هدر_{sector_name}_{timestamp}.json"
            
            # حفظ الملف
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report_to_export, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("نجاح", f"تم تصدير التقرير بنجاح إلى: {filename}")
            
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في تصدير التقرير: {str(e)}")
    
    def _clean_report_for_export(self, report):
        """تنظيف التقرير للتخزين"""
        import copy
        
        cleaned = copy.deepcopy(report)
        
        # إزالة أي كائنات غير قابلة للتسلسل
        def clean_dict(d):
            for key, value in list(d.items()):
                if hasattr(value, '__dict__'):  # كائنات
                    del d[key]
                elif isinstance(value, dict):
                    clean_dict(value)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            clean_dict(item)
            return d
        
        return clean_dict(cleaned)
    
    def refresh_data(self):
        """تحديث البيانات"""
        self.status_label.config(text="🔄 جاري تحديث البيانات...")
        
        try:
            self.load_dependencies()
            
            # تحديث قائمة القطاعات في Combobox
            self.sector_combo['values'] = [s['name'] for s in self.sectors]
            
            self.status_label.config(text="✅ تم تحديث البيانات بنجاح")
            
            # إذا كان هناك قطاع محدد مسبقاً، قم بتحليله مجدداً
            if self.current_sector_id:
                self.analyze_sector(self.current_sector_id)
                
        except Exception as e:
            self.status_label.config(text="❌ فشل في تحديث البيانات")
            messagebox.showerror("خطأ", f"فشل في تحديث البيانات: {str(e)}")
    
    def print_report(self):
        """طباعة التقرير"""
        if not self.current_report:
            messagebox.showinfo("معلومة", "لا يوجد تقرير للطباعة")
            return
        
        messagebox.showinfo("طباعة", "ميزة الطباعة قيد التطوير")
    
    def show_help(self):
        """عرض المساعدة"""
        help_text = """
        🆘 مساعدة نظام التحليل الهرمي للهدر:
        
        1. اختيار القطاع:
           - اختر قطاعاً من القائمة المنسدلة
           - سيتم تحليل الهيكل الهرمي تلقائياً
        
        2. تبويبات النظام:
           • 🏗️ الهيكل الهرمي: عرض الهيكل كاملاً في جداول
           • 📉 مستويات الهدر: تحليل مفصل لكل مستوى
           • 💰 التحليل المالي: التأثير المالي للهدر
           • 📊 المقارنات: مقارنة مع القطاعات الأخرى
           • 🛠️ بنود العمل: الإجراءات المطلوبة
           • 📋 التقرير الكامل: ملاح شامل
           • 🧮 تفاصيل الحسابات: التفاصيل الرياضية
        
        3. أزرار التحكم:
           • 🔍 تحليل مفصل: تحليل القطاع المختار
           • 📊 تحليل مالي: الانتقال للتحليل المالي
           • 📈 مقارنة: عرض المقارنات
           • 📋 تقرير كامل: توليد التقرير الشامل
           • 🧮 تفاصيل الحسابات: عرض الحسابات الرياضية
           • 🖨️ تصدير: تصدير التقرير إلى ملف
           • 🔄 تحديث: تحديث البيانات من النظام
        
        4. تفسير الألوان:
           • 🔴 أحمر: حالة حرجة (هدر > 15%)
           • 🟡 برتقالي: تحذير (هدر > 8%)
           • 🟢 أخضر: حالة جيدة
           • 🔵 أزرق: حالة ممتازة
        
        5. ملاحظات:
           - يمكن تصدير التقرير إلى ملف JSON
           - يتم التحقق من الحسابات تلقائياً
           - يتم اكتشاف المشاكل في القياسات
        
        للاستفسارات: فريق الدعم الفني
        """
        
        # إنشاء نافذة المساعدة
        help_window = tk.Toplevel(self)
        help_window.title("مساعدة النظام")
        help_window.geometry("600x500")
        help_window.configure(bg='white')
        
        # إطار النص
        text_frame = tk.Frame(help_window, bg='white')
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # شريط التمرير
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side='right', fill='y')
        
        # نص المساعدة
        help_text_widget = tk.Text(text_frame, 
                                  wrap='word',
                                  font=('Arial', 10),
                                  bg='white',
                                  fg=self.colors['dark'],
                                  yscrollcommand=scrollbar.set)
        help_text_widget.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=help_text_widget.yview)
        
        # إدخال النص
        help_text_widget.insert('1.0', help_text)
        help_text_widget.config(state='disabled')
        
        # زر الإغلاق
        tk.Button(help_window, text="إغلاق", 
                 command=help_window.destroy,
                 bg=self.colors['primary'],
                 fg='white',
                 padx=20,
                 pady=5).pack(pady=10)
    
    def _show_error(self, title, message):
        """عرض رسالة خطأ"""
        self.status_label.config(text="❌ فشل في التحليل")
        messagebox.showerror(title, message)