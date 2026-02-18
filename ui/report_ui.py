# ui/report_ui.py - الإصدار المعدل (بدون عمود الرصيد الجديد + إضافة تقرير أوراق التأشيرات)
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
import os
import webbrowser

logger = logging.getLogger(__name__)



class ReportUI(tk.Frame):
    """واجهة التقارير والإحصائيات المحسّنة"""
    
    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.user_data = user_data
        
        # ✅ محاولة تحميل ReportManager مباشرة (مثل القديم)
        try:
            from modules.reports import ReportManager
            self.report_manager = ReportManager()
            logger.info("✅ تم تحميل مدير التقارير بنجاح")
            self.report_loaded = True
        except ImportError as e:
            logger.error(f"❌ خطأ في استيراد ReportManager: {e}")
            messagebox.showerror("خطأ", f"لم يتم تحميل نظام التقارير: {e}")
            self.report_manager = None
            self.report_loaded = False
            return

        self.btn_colors = {
            'generate': '#27ae60',  # أخضر للتوليد
            'export': '#2980b9',    # أزرق للتصدير
            'print': '#8e44ad',     # بنفسجي للطباعة
            'filter': '#f39c12',    # برتقالي للفلترة
            'normal': '#3498db',    # أزرق فاتح للأزرار العادية
            'bg_light': '#f8f9fa'
        }
        
        self.current_report = None
        self.current_report_type = None
        self.create_widgets() 

    def load_report_manager(self):
        """تحميل مدير التقارير"""
        try:
            from modules.reports import ReportManager
            self.report_manager = ReportManager()
            logger.info("تم تحميل مدير التقارير بنجاح")
        except ImportError as e:
            logger.error(f"خطأ في استيراد ReportManager: {e}")
            self.report_manager = self.create_dummy_report_manager()
            messagebox.showwarning("تحذير", f"تم تحميل نسخة تجريبية من نظام التقارير: {e}")
        except Exception as e:
            logger.error(f"خطأ في تحميل مدير التقارير: {e}")
            self.report_manager = self.create_dummy_report_manager()
            messagebox.showwarning("تحذير", f"تم تحميل نسخة تجريبية من نظام التقارير: {e}")

    def create_dummy_report_manager(self):
        """إنشاء ReportManager تجريبي للاختبار"""
        class DummyReportManager:
            def __init__(self):
                self.dummy = True
            def get_negative_balance_lists_report_old_interface(self):
                return {'sectors': [], 'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            def get_cut_lists_report_old_interface(self):
                return {'boxes': [], 'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            def get_free_customers_by_sector_report_old_interface(self):
                return {'sectors': [], 'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            def get_dashboard_statistics(self):
                return {
                    'total_customers': 0,
                    'today_invoices': 0,
                    'today_amount': 0,
                    'month_invoices': 0,
                    'month_amount': 0,
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        return DummyReportManager()


    def create_styled_button(self, parent, text, command, color_type='normal', width=None):
        """إنشاء زر بحجم كبير وألوان جذابة"""
        color = self.btn_colors.get(color_type, '#7f8c8d')
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg='white',
            font=('Arial', 11, 'bold'),
            padx=15,
            pady=8,
            cursor='hand2',
            relief='flat',
            activebackground='#34495e',
            activeforeground='white',
            width=width
        )
        # تأثير hover
        def on_enter(e): btn.config(bg=self.lighten_color(color))
        def on_leave(e): btn.config(bg=color)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def lighten_color(self, hex_color):
        """تفتيح طفيف للون (يمكنك تطويرها لاحقاً)"""
        # للتبسيط، نعيد نفس اللون أو نغير إلى لون أغمق قليلاً
        return '#34495e'  # لون داكن ثابت                
    
    def create_widgets(self):
        if not self.report_loaded:
            error_frame = tk.Frame(self)
            error_frame.pack(fill='both', expand=True)
            tk.Label(error_frame, 
                    text="❌ لم يتم تحميل نظام التقارير",
                    font=('Arial', 16, 'bold'),
                    fg='red').pack(pady=20)
            tk.Label(error_frame,
                    text="يرجى التحقق من:\n1. وجود ملف modules/reports.py\n2. أن الكود لا يحتوي على أخطاء",
                    font=('Arial', 12)).pack(pady=10)
            return
        
        # شريط الأدوات العلوي
        toolbar = tk.Frame(self, bg='#2c3e50', height=50)
        toolbar.pack(fill='x', padx=10, pady=5)
        
        tk.Label(toolbar, text="📊 نظام التقارير المتقدم", 
                font=('Arial', 14, 'bold'), 
                bg='#2c3e50', fg='white').pack(side='left', padx=10)
        
        # قسم رئيسي
        main_frame = tk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # قسم اختيار التقارير (يسار)
        left_frame = tk.LabelFrame(main_frame, text="أنواع التقارير", 
                                  font=('Arial', 12, 'bold'),
                                  padx=10, pady=10)
        left_frame.pack(side='left', fill='y', padx=(0, 10))
        
        # إنشاء قائمة التقارير
        reports = [
            ("📉 قوائم الكسر (قديم)", self.show_negative_balance_old),
            ("📉 قوائم الكسر (متقدم)", self.show_negative_balance_advanced),
            ("✂️ قوائم القطع (قديم)", self.show_cut_lists_old),
            ("✂️ قوائم القطع (متقدم)", self.show_cut_lists_advanced),
            ("🆓 الزبائن المجانيين (قديم)", self.show_free_customers_old),
            ("🆓 الزبائن المجانيين (متقدم)", self.show_free_customers_advanced),
            ("📊 إحصائيات عامة", self.show_dashboard_statistics),
            ("💰 تقرير المبيعات", self.show_sales_report),
            ("🧾 تقرير الفواتير", self.show_invoice_report),
            ("🖨️ أوراق التأشيرات", self.show_visa_report),   # إضافة الزر الجديد
                        ("💰 جبايات المحاسب", self.show_accountant_collections_report),   # إضافة الزر الجديد
        ]
        
        for report_name, command in reports:
            btn = self.create_styled_button(left_frame, report_name, command, color_type='normal')
            btn.config(anchor='w', justify='left')  # للحفاظ على المحاذاة لليسار
            btn.pack(fill='x', pady=2)        
        # قسم عرض التقرير (يمين)
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side='right', fill='both', expand=True)
        
        # إضافة أزرار التحكم
        control_frame = tk.Frame(right_frame)
        control_frame.pack(fill='x', pady=(0, 10))
                
        self.export_excel_btn = self.create_styled_button(control_frame, "📥 تصدير Excel", 
                                                        self.export_current_to_excel, 'export')
        self.export_excel_btn.pack(side='left', padx=5)

        self.filter_btn = self.create_styled_button(control_frame, "🔍 فلترة متقدمة", 
                                                    self.show_advanced_filter, 'filter')
        self.filter_btn.pack(side='left', padx=5)        
        # إنشاء Notebook (تبويبات)
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # تبويب النتائج
        self.results_frame = tk.Frame(self.notebook)
        self.notebook.add(self.results_frame, text="📋 النتائج")
        
        # تبويب الإحصائيات
        self.stats_frame = tk.Frame(self.notebook)
        self.notebook.add(self.stats_frame, text="📊 الإحصائيات")
        
        # تبويب التصدير
        self.export_frame = tk.Frame(self.notebook)
        self.notebook.add(self.export_frame, text="💾 التصدير")
        
        # شريط الحالة
        self.status_bar = tk.Label(self, text="جاهز", 
                                  bd=1, relief='sunken', anchor='w')
        self.status_bar.pack(side='bottom', fill='x', padx=10, pady=5)
        
        # عرض تقرير افتراضي
        self.show_dashboard_statistics()
    
    # ============== دوال عرض التقارير ==============
    
    def show_negative_balance_old(self):
        """عرض تقرير قوائم الكسر القديم"""
        if not self.report_manager:
            self.show_error("لم يتم تحميل نظام التقارير")
            return
        
        self.clear_frames()
        try:
            report = self.report_manager.get_negative_balance_lists_report_old_interface()
            self.display_report_old(report, "قوائم الكسر (قديم)")
            self.current_report = report
            self.current_report_type = "negative_balance_old"
            self.export_excel_btn.config(state='disabled')
            self.filter_btn.config(state='disabled')
            self.update_status("تم توليد تقرير قوائم الكسر القديم")
        except Exception as e:
            self.show_error(f"خطأ في عرض التقرير: {e}")
    
    def show_negative_balance_advanced(self):
        """عرض تقرير قوائم الكسر المتقدم"""
        response = messagebox.askquestion("فلترة", 
            "هل تريد تطبيق فلترة متقدمة؟\n\nنعم: فلترة متقدمة\nلا: فلترة بسيطة",
            icon='question')
        
        if response == 'yes':
            self.show_negative_balance_advanced_filter()
        else:
            self.show_negative_balance_simple_filter()
    
    def show_negative_balance_simple_filter(self):
        """عرض نافذة فلترة بسيطة لقوائم الكسر"""
        if not self.report_manager:
            self.show_error("لم يتم تحميل نظام التقارير")
            return
        
        filter_window = tk.Toplevel(self)
        filter_window.title("فلترة قوائم الكسر")
        filter_window.geometry("400x300")
        
        tk.Label(filter_window, text="فلترة قوائم الكسر", 
                font=('Arial', 14, 'bold')).pack(pady=10)
        
        tk.Label(filter_window, text="رقم القطاع (اترك فارغاً للكل):").pack(pady=5)
        sector_entry = tk.Entry(filter_window)
        sector_entry.pack(pady=5)
        
        def apply_filter():
            try:
                sector_id = sector_entry.get().strip()
                sector_id = int(sector_id) if sector_id else None
                filter_window.destroy()
                self.clear_frames()
                report = self.report_manager.get_negative_balance_lists_report(
                    sector_id=sector_id
                )
                self.display_negative_balance_advanced(report)
                self.current_report = report
                self.current_report_type = "negative_balance_advanced"
                self.export_excel_btn.config(state='normal')
                self.filter_btn.config(state='normal')
                self.setup_export_options("negative_balance_advanced")
                self.update_status("تم توليد تقرير قوائم الكسر المتقدم")
            except ValueError:
                messagebox.showerror("خطأ", "رقم القطاع يجب أن يكون رقماً")
            except Exception as e:
                self.show_error(f"خطأ في عرض التقرير: {e}")
        
        tk.Button(filter_window, text="تطبيق", command=apply_filter,
                 bg='#27ae60', fg='white').pack(pady=10)
        tk.Button(filter_window, text="إلغاء", command=filter_window.destroy,
                 bg='#e74c3c', fg='white').pack(pady=5)
    
    def show_cut_lists_old(self):
        """عرض تقرير قوائم القطع القديم"""
        if not self.report_manager:
            self.show_error("لم يتم تحميل نظام التقارير")
            return
        
        self.clear_frames()
        try:
            report = self.report_manager.get_cut_lists_report_old_interface()
            self.display_cut_lists_old(report)
            self.current_report = report
            self.current_report_type = "cut_lists_old"
            self.export_excel_btn.config(state='disabled')
            self.filter_btn.config(state='disabled')
            self.update_status("تم توليد تقرير قوائم القطع القديم")
        except Exception as e:
            self.show_error(f"خطأ في عرض التقرير: {e}")
    
    def show_cut_lists_advanced(self):
        """عرض تقرير قوائم القطع المتقدم مع فلترة متقدمة"""
        if not self.report_manager:
            self.show_error("لم يتم تحميل نظام التقارير")
            return

        # نافذة فلترة متقدمة للقطع
        filter_window = tk.Toplevel(self)
        filter_window.title("فلترة قوائم القطع المتقدمة")
        filter_window.geometry("500x650")

        filter_window.update_idletasks()
        x = (filter_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (filter_window.winfo_screenheight() // 2) - (650 // 2)
        filter_window.geometry(f"500x650+{x}+{y}")

        main_canvas = tk.Canvas(filter_window)
        main_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(filter_window, orient="vertical", command=main_canvas.yview)
        scrollbar.pack(side="right", fill="y")

        main_canvas.configure(yscrollcommand=scrollbar.set)
        main_canvas.bind('<Configure>', lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))

        main_frame = tk.Frame(main_canvas, padx=20, pady=20)
        main_canvas.create_window((0, 0), window=main_frame, anchor="nw", width=460)

        tk.Label(main_frame, text="فلترة متقدمة - قوائم القطع", 
                font=('Arial', 14, 'bold')).pack(pady=(0, 20))

        # مجال الرصيد
        balance_frame = tk.LabelFrame(main_frame, text="مجال الرصيد للقطع", padx=10, pady=10)
        balance_frame.pack(fill='x', pady=10)
        tk.Label(balance_frame, text="من:").grid(row=0, column=0, padx=5, pady=5)
        min_balance_entry = tk.Entry(balance_frame, width=15)
        min_balance_entry.insert(0, "-1000")
        min_balance_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(balance_frame, text="إلى:").grid(row=0, column=2, padx=5, pady=5)
        max_balance_entry = tk.Entry(balance_frame, width=15)
        max_balance_entry.insert(0, "0")
        max_balance_entry.grid(row=0, column=3, padx=5, pady=5)

        # أنواع العدادات
        meter_frame = tk.LabelFrame(main_frame, text="أنواع العدادات", padx=10, pady=10)
        meter_frame.pack(fill='x', pady=10)
        meter_types = ['مولدة', 'علبة توزيع', 'رئيسية', 'زبون']
        meter_vars = {}
        for i, meter_type in enumerate(meter_types):
            var = tk.BooleanVar(value=True if meter_type == 'زبون' else False)
            chk = tk.Checkbutton(meter_frame, text=meter_type, variable=var)
            chk.grid(row=i//2, column=i%2, sticky='w', padx=10, pady=5)
            meter_vars[meter_type] = var

        # التصنيفات المالية المستثناة
        category_frame = tk.LabelFrame(main_frame, text="استبعاد التصنيفات", padx=10, pady=10)
        category_frame.pack(fill='x', pady=10)
        categories = ['normal', 'free', 'vip', 'free_vip']
        category_names = {
            'normal': 'عادي',
            'free': 'مجاني',
            'vip': 'VIP',
            'free_vip': 'مجاني + VIP'
        }
        category_vars = {}
        for i, category in enumerate(categories):
            var = tk.BooleanVar(value=False)
            chk = tk.Checkbutton(category_frame, 
                            text=category_names.get(category, category),
                            variable=var)
            chk.grid(row=i//2, column=i%2, sticky='w', padx=10, pady=5)
            category_vars[category] = var

        # القطاع
        sector_frame = tk.LabelFrame(main_frame, text="القطاع", padx=10, pady=10)
        sector_frame.pack(fill='x', pady=10)
        tk.Label(sector_frame, text="اختر قطاع:").pack(side='left', padx=5)
        sectors = self.report_manager.get_available_sectors()
        sector_options = [("الكل", None)]
        sector_options.extend([(s['name'], s['id']) for s in sectors])
        sector_combo = ttk.Combobox(sector_frame, 
                                values=[name for name, _ in sector_options],
                                state='readonly', width=30)
        sector_combo.pack(side='left', padx=5)
        sector_combo.current(0)

        # حالة القطع
        cut_status_frame = tk.LabelFrame(main_frame, text="حالة القطع", padx=10, pady=10)
        cut_status_frame.pack(fill='x', pady=10)
        cut_status_var = tk.StringVar(value="all")
        tk.Radiobutton(cut_status_frame, text="الكل", 
                    variable=cut_status_var, value="all").pack(anchor='w', pady=2)
        tk.Radiobutton(cut_status_frame, text="تم القطع فقط", 
                    variable=cut_status_var, value="cut").pack(anchor='w', pady=2)
        tk.Radiobutton(cut_status_frame, text="لم يتم القطع", 
                    variable=cut_status_var, value="not_cut").pack(anchor='w', pady=2)

        # الترتيب
        sort_frame = tk.LabelFrame(main_frame, text="طريقة الترتيب", padx=10, pady=10)
        sort_frame.pack(fill='x', pady=10)
        sort_var = tk.StringVar(value="balance_desc")
        tk.Radiobutton(sort_frame, text="الرصيد تنازلياً (الأكبر فالأصغر)", 
                    variable=sort_var, value="balance_desc").pack(anchor='w', pady=2)
        tk.Radiobutton(sort_frame, text="الرصيد تصاعدياً (الأصغر فالأكبر)", 
                    variable=sort_var, value="balance_asc").pack(anchor='w', pady=2)
        tk.Radiobutton(sort_frame, text="الاسم أبجدياً", 
                    variable=sort_var, value="name").pack(anchor='w', pady=2)

        # أزرار التحكم في إطار سفلي منفصل
        button_frame = tk.Frame(filter_window)
        button_frame.pack(side="bottom", fill="x", padx=20, pady=10)

        def apply_filter():
            try:
                min_balance = float(min_balance_entry.get())
                max_balance = float(max_balance_entry.get())
                
                include_meter_types = [mt for mt, var in meter_vars.items() if var.get()]
                exclude_categories = [cat for cat, var in category_vars.items() if var.get()]
                
                selected_sector = sector_combo.get()
                sector_id = None
                for name, sid in sector_options:
                    if name == selected_sector:
                        sector_id = sid
                        break
                
                cut_status = cut_status_var.get()
                sort_by = sort_var.get()
                
                filter_window.destroy()
                self.clear_frames()
                
                only_meter_type = "زبون"
                if include_meter_types:
                    only_meter_type = include_meter_types[0]
                
                report = self.report_manager.get_cut_lists_report(
                    min_balance=min_balance,
                    max_balance=max_balance,
                    exclude_categories=exclude_categories,
                    only_meter_type=only_meter_type,
                    sector_id=sector_id,   # استخدم sector_id بدلاً من box_id
                    sort_by=sort_by
                )
                
                self.display_cut_lists_advanced(report)
                self.current_report = report
                self.current_report_type = "cut_lists_advanced"
                self.export_excel_btn.config(state='normal')
                self.filter_btn.config(state='normal')
                self.setup_export_options("cut_lists_advanced")
                self.update_status("تم توليد تقرير قوائم القطع مع الفلترة المتقدمة")
                
            except ValueError:
                messagebox.showerror("خطأ", "قيم غير صحيحة. تأكد من إدخال أرقام صحيحة")
            except Exception as e:
                self.show_error(f"خطأ في التصفية: {e}")

        tk.Button(button_frame, text="تطبيق", command=apply_filter,
            bg='#27ae60', fg='white', width=15).pack(side='right', padx=5)
        tk.Button(button_frame, text="إلغاء", command=filter_window.destroy,
            bg='#e74c3c', fg='white', width=15).pack(side='right', padx=5)
        tk.Button(button_frame, text="إعادة تعيين",
            command=lambda: self.reset_filter_fields_cut(
                min_balance_entry, max_balance_entry,
                meter_vars, category_vars,
                sector_combo, cut_status_var, sort_var
            ),
            bg='#3498db', fg='white', width=15).pack(side='right', padx=5)
    
    def reset_filter_fields_cut(self, min_entry, max_entry, meter_vars, 
                               category_vars, sector_combo, cut_status_var, sort_var):
        min_entry.delete(0, 'end')
        min_entry.insert(0, "-1000")
        max_entry.delete(0, 'end')
        max_entry.insert(0, "0")
        for var in meter_vars.values():
            var.set(False)
        meter_vars['زبون'].set(True)
        for var in category_vars.values():
            var.set(False)
        sector_combo.current(0)
        cut_status_var.set("all")
        sort_var.set("balance_desc")
    
    def show_free_customers_old(self):
        """عرض تقرير الزبائن المجانيين القديم"""
        if not self.report_manager:
            self.show_error("لم يتم تحميل نظام التقارير")
            return
        
        self.clear_frames()
        try:
            report = self.report_manager.get_free_customers_by_sector_report_old_interface()
            self.display_free_customers_old(report)
            self.current_report = report
            self.current_report_type = "free_customers_old"
            self.export_excel_btn.config(state='disabled')
            self.filter_btn.config(state='disabled')
            self.update_status("تم توليد تقرير الزبائن المجانيين القديم")
        except Exception as e:
            self.show_error(f"خطأ في عرض التقرير: {e}")
    
    def show_free_customers_advanced(self):
        """عرض تقرير الزبائن المجانيين المتقدم"""
        if not self.report_manager:
            self.show_error("لم يتم تحميل نظام التقارير")
            return
        
        self.clear_frames()
        try:
            report = self.report_manager.get_free_customers_by_sector_report()
            self.display_free_customers_advanced(report)
            self.current_report = report
            self.current_report_type = "free_customers_advanced"
            self.export_excel_btn.config(state='normal')
            self.filter_btn.config(state='normal')
            self.setup_export_options("free_customers_advanced")
            self.update_status("تم توليد تقرير الزبائن المجانيين المتقدم")
        except Exception as e:
            self.show_error(f"خطأ في عرض التقرير: {e}")
    
    def show_dashboard_statistics(self):
        """عرض إحصائيات لوحة التحكم"""
        if not self.report_manager:
            self.show_error("لم يتم تحميل نظام التقارير")
            return
        
        self.clear_frames()
        try:
            report = self.report_manager.get_dashboard_statistics()
            self.display_dashboard_statistics(report)
            self.current_report = report
            self.current_report_type = "dashboard"
            self.export_excel_btn.config(state='normal')
            self.filter_btn.config(state='disabled')
            self.setup_export_options("dashboard")
            self.update_status("تم تحميل إحصائيات لوحة التحكم")
        except Exception as e:
            self.show_error(f"خطأ في عرض الإحصائيات: {e}")
    
    def show_sales_report(self):
        """عرض تقرير المبيعات"""
        if not self.report_manager:
            self.show_error("لم يتم تحميل نظام التقارير")
            return
        
        self.clear_frames()
        try:
            report = self.report_manager.get_sales_report()
            self.display_sales_report(report)
            self.current_report = report
            self.current_report_type = "sales"
            self.export_excel_btn.config(state='normal')
            self.filter_btn.config(state='disabled')
            self.setup_export_options("sales")
            self.update_status("تم توليد تقرير المبيعات")
        except Exception as e:
            self.show_error(f"خطأ في عرض التقرير: {e}")
    
    def show_invoice_report(self):
        """عرض تقرير الفواتير"""
        if not self.report_manager:
            self.show_error("لم يتم تحميل نظام التقارير")
            return
        
        self.clear_frames()
        try:
            report = self.report_manager.get_invoice_detailed_report()
            self.display_invoice_report(report)
            self.current_report = report
            self.current_report_type = "invoices"
            self.export_excel_btn.config(state='normal')
            self.filter_btn.config(state='disabled')
            self.setup_export_options("invoices")
            self.update_status("تم توليد تقرير الفواتير")
        except Exception as e:
            self.show_error(f"خطأ في عرض التقرير: {e}")
    
    # ============== دوال العرض ==============
    
    def display_report_old(self, report, title):
        """عرض تقرير قديم"""
        text_widget = tk.Text(self.results_frame, wrap='word')
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        content = f"تقرير: {title}\n"
        content += f"تاريخ الإنشاء: {report.get('generated_at', '')}\n"
        content += "="*50 + "\n\n"
        if 'sectors' in report:
            for sector in report['sectors']:
                content += f"القطاع: {sector['sector_name']}\n"
                content += f"عدد الزبائن: {sector['count']}\n"
                content += f"إجمالي الرصيد السالب: {sector['total_negative_balance']}\n"
                content += "-"*30 + "\n"
                for customer in sector['customers']:
                    content += f"  • {customer['name']}: {customer['current_balance']}\n"
                content += "\n"
        text_widget.insert('1.0', content)
        text_widget.config(state='disabled')
    
    def display_negative_balance_advanced(self, report):
        """عرض تقرير قوائم الكسر المتقدم - بدون عمود الرصيد الجديد"""
        frame = tk.Frame(self.results_frame)
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        info_frame = tk.LabelFrame(frame, text="معلومات التقرير", padx=10, pady=10)
        info_frame.pack(fill='x', pady=(0, 10))
        tk.Label(info_frame, text=f"عنوان التقرير: {report.get('report_title', '')}", 
                anchor='w').pack(fill='x')
        tk.Label(info_frame, text=f"تاريخ الإنشاء: {report.get('generated_at', '')}", 
                anchor='w').pack(fill='x')
        
        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill='both', expand=True)
        
        scrollbar_y = ttk.Scrollbar(tree_frame)
        scrollbar_y.pack(side='right', fill='y')
        scrollbar_x = ttk.Scrollbar(tree_frame, orient='horizontal')
        scrollbar_x.pack(side='bottom', fill='x')
        
        # ❌ تم حذف عمود 'الجديد'
        tree = ttk.Treeview(tree_frame, 
                           yscrollcommand=scrollbar_y.set,
                           xscrollcommand=scrollbar_x.set,
                           columns=('الاسم', 'رقم العلبة', 'الرصيد', 'السحب', 'التأشيرة', 'التصنيف', 'الهاتف'))
        
        scrollbar_y.config(command=tree.yview)
        scrollbar_x.config(command=tree.xview)
        
        tree.heading('#0', text='القطاع')
        tree.column('#0', width=150)
        for col in tree['columns']:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        for sector in report.get('sectors', []):
            sector_id = tree.insert('', 'end', text=sector['sector_name'], 
                                  values=('', '', f"{sector['total_balance']:,.0f}", 
                                         f"{sector['total_withdrawal']:,.0f}", 
                                         f"{sector['total_visa']:,.0f}",
                                         '', ''))
            for customer in sector.get('customers', []):
                tree.insert(sector_id, 'end', text='', 
                          values=(customer['name'],
                                 customer['box_number'],
                                 f"{customer['current_balance']:,.0f}",
                                 f"{customer['withdrawal_amount']:,.0f}",
                                 f"{customer['visa_balance']:,.0f}",
                                 customer.get('financial_category', ''),
                                 customer.get('phone_number', '')))
        
        tree.pack(fill='both', expand=True)
        
        grand_total = report.get('grand_total', {})
        total_frame = tk.LabelFrame(frame, text="الإجماليات", padx=10, pady=10)
        total_frame.pack(fill='x', pady=10)
        tk.Label(total_frame, 
                text=f"عدد الزبائن: {grand_total.get('customer_count', 0):,} | "
                     f"إجمالي الرصيد: {grand_total.get('total_balance', 0):,.0f} | "
                     f"إجمالي السحب: {grand_total.get('total_withdrawal', 0):,.0f} | "
                     f"إجمالي التأشيرة: {grand_total.get('total_visa', 0):,.0f}",
                font=('Arial', 10, 'bold')).pack()
    
    def display_cut_lists_old(self, report):
        """عرض تقرير قوائم القطع القديم"""
        text_widget = tk.Text(self.results_frame, wrap='word')
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        content = f"تقرير: قوائم القطع (قديم)\n"
        content += f"تاريخ الإنشاء: {report.get('generated_at', '')}\n"
        content += f"إجمالي الزبائن: {report.get('total_customers', 0)}\n"
        content += "="*50 + "\n\n"
        if 'boxes' in report:
            for box in report['boxes']:
                content += f"العلبة: {box['box_info'].get('name', '')} ({box['box_info'].get('box_number', '')})\n"
                content += f"عدد الزبائن: {box['count']}\n"
                content += "-"*30 + "\n"
                for customer in box['customers']:
                    content += f"  • {customer['name']}: {customer['current_balance']}\n"
                content += "\n"
        text_widget.insert('1.0', content)
        text_widget.config(state='disabled')
    
    def display_cut_lists_advanced(self, report):
        """عرض تقرير قوائم القطع المتقدم - بدون عمود الرصيد الجديد"""
        frame = tk.Frame(self.results_frame)
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        info_frame = tk.LabelFrame(frame, text="معلومات التقرير", padx=10, pady=10)
        info_frame.pack(fill='x', pady=(0, 10))
        tk.Label(info_frame, text=f"عنوان التقرير: {report.get('report_title', '')}", 
                anchor='w').pack(fill='x')
        tk.Label(info_frame, text=f"تاريخ الإنشاء: {report.get('generated_at', '')}", 
                anchor='w').pack(fill='x')
        
        filters = report.get('filters', {})
        if filters:
            filters_text = f"الفلاتر: مجال الرصيد من {filters.get('min_balance', -1000)} إلى {filters.get('max_balance', 0)}"
            tk.Label(info_frame, text=filters_text, anchor='w').pack(fill='x')
        
        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill='both', expand=True)
        
        scrollbar_y = ttk.Scrollbar(tree_frame)
        scrollbar_y.pack(side='right', fill='y')
        scrollbar_x = ttk.Scrollbar(tree_frame, orient='horizontal')
        scrollbar_x.pack(side='bottom', fill='x')
        
        # ❌ تم حذف عمود 'الجديد'
        tree = ttk.Treeview(tree_frame, 
                           yscrollcommand=scrollbar_y.set,
                           xscrollcommand=scrollbar_x.set,
                           columns=('الاسم', 'رقم العلبة', 'الرصيد', 'السحب', 'التأشيرة', 'التصنيف', 'الهاتف'))
        
        scrollbar_y.config(command=tree.yview)
        scrollbar_x.config(command=tree.xview)
        
        tree.heading('#0', text='العلبة')
        tree.column('#0', width=200)
        for col in tree['columns']:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        for box in report.get('boxes', []):
            box_id = tree.insert('', 'end', 
                               text=f"{box['box_name']} ({box['box_number']}) - {box['sector_name']}",
                               values=('', '', f"{box['box_total_balance']:,.0f}", 
                                      f"{box['box_total_withdrawal']:,.0f}", 
                                      f"{box['box_total_visa']:,.0f}",
                                      '', ''))
            for customer in box.get('customers', []):
                tree.insert(box_id, 'end', text='', 
                          values=(customer['name'],
                                 customer['box_number'],
                                 f"{customer['current_balance']:,.0f}",
                                 f"{customer['withdrawal_amount']:,.0f}",
                                 f"{customer['visa_balance']:,.0f}",
                                 customer.get('financial_category', ''),
                                 customer.get('phone_number', '')))
        
        tree.pack(fill='both', expand=True)
        
        grand_total = report.get('grand_total', {})
        total_frame = tk.LabelFrame(frame, text="الإجماليات", padx=10, pady=10)
        total_frame.pack(fill='x', pady=10)
        tk.Label(total_frame, 
                text=f"عدد العلب: {grand_total.get('total_boxes', 0):,} | "
                     f"عدد الزبائن: {grand_total.get('total_customers', 0):,} | "
                     f"إجمالي الرصيد: {grand_total.get('total_balance', 0):,.0f}",
                font=('Arial', 10, 'bold')).pack()
    
    def display_free_customers_old(self, report):
        """عرض تقرير الزبائن المجانيين القديم"""
        text_widget = tk.Text(self.results_frame, wrap='word')
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        content = f"تقرير: الزبائن المجانيين (قديم)\n"
        content += f"تاريخ الإنشاء: {report.get('generated_at', '')}\n"
        content += "="*50 + "\n\n"
        if 'sectors' in report:
            for sector in report['sectors']:
                content += f"القطاع: {sector['sector_name']}\n"
                content += f"عدد الزبائن المجانيين: {sector['free_count']}\n"
                content += f"إجمالي الرصيد: {sector['total_balance']}\n"
                content += f"إجمالي التأشيرة: {sector['total_visa_balance']}\n"
                content += "-"*30 + "\n"
                for customer in sector['customers']:
                    content += f"  • {customer['name']}: رصيد={customer['current_balance']}, سحب={customer['withdrawal_amount']}, تأشيرة={customer['visa_balance']}\n"
                content += "\n"
        total = report.get('total', {})
        content += f"\nالإجماليات:\n"
        content += f"عدد الزبائن المجانيين: {total.get('free_count', 0)}\n"
        content += f"إجمالي الرصيد: {total.get('total_balance', 0)}\n"
        content += f"إجمالي التأشيرة: {total.get('total_visa_balance', 0)}\n"
        text_widget.insert('1.0', content)
        text_widget.config(state='disabled')
    
    def display_free_customers_advanced(self, report):
        """عرض تقرير الزبائن المجانيين المتقدم - بدون عمود الرصيد الجديد"""
        frame = tk.Frame(self.results_frame)
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        info_frame = tk.LabelFrame(frame, text="معلومات التقرير", padx=10, pady=10)
        info_frame.pack(fill='x', pady=(0, 10))
        tk.Label(info_frame, text=f"عنوان التقرير: {report.get('report_title', '')}", 
                anchor='w').pack(fill='x')
        tk.Label(info_frame, text=f"تاريخ الإنشاء: {report.get('generated_at', '')}", 
                anchor='w').pack(fill='x')
        
        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill='both', expand=True)
        
        scrollbar_y = ttk.Scrollbar(tree_frame)
        scrollbar_y.pack(side='right', fill='y')
        scrollbar_x = ttk.Scrollbar(tree_frame, orient='horizontal')
        scrollbar_x.pack(side='bottom', fill='x')
        
        # ❌ تم حذف عمود 'الجديد'
        tree = ttk.Treeview(tree_frame, 
                           yscrollcommand=scrollbar_y.set,
                           xscrollcommand=scrollbar_x.set,
                           columns=('الاسم', 'رقم العلبة', 'الرصيد', 'السحب', 'التأشيرة', 'التصنيف', 'الهاتف', 'نوع العداد'))
        
        scrollbar_y.config(command=tree.yview)
        scrollbar_x.config(command=tree.xview)
        
        tree.heading('#0', text='القطاع')
        tree.column('#0', width=150)
        for col in tree['columns']:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        for sector in report.get('sectors', []):
            sector_id = tree.insert('', 'end', text=sector['sector_name'], 
                                  values=('', '', f"{sector['total_balance']:,.0f}", 
                                         f"{sector['total_withdrawal']:,.0f}", 
                                         f"{sector['total_visa_balance']:,.0f}",
                                         '', '', ''))
            for customer in sector.get('customers', []):
                tree.insert(sector_id, 'end', text='', 
                          values=(customer['name'],
                                 customer['box_number'],
                                 f"{customer['current_balance']:,.0f}",
                                 f"{customer['withdrawal_amount']:,.0f}",
                                 f"{customer['visa_balance']:,.0f}",
                                 customer.get('financial_category', ''),
                                 customer.get('phone_number', ''),
                                 customer.get('meter_type', '')))
        
        tree.pack(fill='both', expand=True)
        
        total = report.get('total', {})
        total_frame = tk.LabelFrame(frame, text="الإجماليات", padx=10, pady=10)
        total_frame.pack(fill='x', pady=10)
        tk.Label(total_frame, 
                text=f"عدد الزبائن: {total.get('free_count', 0):,} | "
                     f"إجمالي الرصيد: {total.get('total_balance', 0):,.0f} | "
                     f"إجمالي السحب: {total.get('total_withdrawal', 0):,.0f} | "
                     f"إجمالي التأشيرة: {total.get('total_visa_balance', 0):,.0f}",
                font=('Arial', 10, 'bold')).pack()
    
    def display_dashboard_statistics(self, report):
        """عرض إحصائيات لوحة التحكم"""
        text_widget = tk.Text(self.results_frame, wrap='word')
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        content = f"📊 إحصائيات لوحة التحكم\n"
        content += f"تاريخ الإنشاء: {report.get('generated_at', '')}\n"
        content += "="*50 + "\n\n"
        content += f"👥 إجمالي الزبائن: {report.get('total_customers', 0):,}\n"
        content += f"📅 فواتير اليوم: {report.get('today_invoices', 0):,} - مبلغ: {report.get('today_amount', 0):,.0f} ك.و\n"
        content += f"📅 فواتير الشهر: {report.get('month_invoices', 0):,} - مبلغ: {report.get('month_amount', 0):,.0f} ك.و\n"
        content += f"🔻 زبائن برصيد سالب: {report.get('negative_count', 0):,} - إجمالي: {report.get('negative_total', 0):,.0f} ك.و\n"
        content += f"🔼 زبائن برصيد موجب: {report.get('positive_count', 0):,} - إجمالي: {report.get('positive_total', 0):,.0f} ك.و\n"
        content += "\n🏆 أفضل القطاعات أداءً هذا الشهر:\n"
        for sector in report.get('top_sectors', []):
            content += f"  • {sector['name']}: {sector['invoice_count']:,} فاتورة - {sector['total_amount']:,.0f} ك.و\n"
        text_widget.insert('1.0', content)
        text_widget.config(state='disabled')
    
    def display_sales_report(self, report):
        """عرض تقرير المبيعات"""
        text_widget = tk.Text(self.results_frame, wrap='word')
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        content = f"💰 تقرير المبيعات\n"
        content += f"تاريخ الإنشاء: {report.get('generated_at', '')}\n"
        content += f"الفترة: من {report['period']['start_date']} إلى {report['period']['end_date']}\n"
        content += "="*50 + "\n\n"
        if 'sales_data' in report:
            for data in report['sales_data']:
                content += f"{data.get('period', '')}:\n"
                content += f"  عدد الفواتير: {data.get('invoice_count', 0):,}\n"
                content += f"  إجمالي المبلغ: {data.get('total_amount', 0):,.0f} ك.و\n"
                content += f"  إجمالي الكيلوات: {data.get('total_kilowatts', 0):,.0f}\n"
                content += f"  إجمالي المجاني: {data.get('total_free', 0):,.0f}\n"
                content += f"  إجمالي الخصم: {data.get('total_discount', 0):,.0f}\n"
                content += "-"*30 + "\n"
        if 'totals' in report:
            totals = report['totals']
            content += f"\n📊 الإجماليات:\n"
            content += f"عدد الفواتير: {totals.get('total_invoices', 0):,}\n"
            content += f"إجمالي المبيعات: {totals.get('grand_total', 0):,.0f} ك.و\n"
            content += f"إجمالي الكيلوات: {totals.get('total_kilowatts', 0):,.0f}\n"
            content += f"إجمالي المجاني: {totals.get('total_free', 0):,.0f}\n"
            content += f"إجمالي الخصم: {totals.get('total_discount', 0):,.0f}\n"
        text_widget.insert('1.0', content)
        text_widget.config(state='disabled')
    
    def display_invoice_report(self, report):
        """عرض تقرير الفواتير"""
        text_widget = tk.Text(self.results_frame, wrap='word')
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        content = f"🧾 تقرير الفواتير\n"
        content += f"تاريخ الإنشاء: {report.get('generated_at', '')}\n"
        content += f"الفترة: من {report['period']['start_date']} إلى {report['period']['end_date']}\n"
        content += f"عدد الفواتير: {report.get('total_count', 0):,}\n"
        content += "="*50 + "\n\n"
        if 'invoices' in report:
            for invoice in report['invoices'][:50]:
                content += f"فاتورة #{invoice.get('invoice_number', '')}\n"
                content += f"  التاريخ: {invoice.get('payment_date', '')} {invoice.get('payment_time', '')}\n"
                content += f"  الزبون: {invoice.get('customer_name', '')}\n"
                content += f"  القطاع: {invoice.get('sector_name', '')}\n"
                content += f"  الكيلوات: {invoice.get('kilowatt_amount', 0):,.0f}\n"
                content += f"  المبلغ: {invoice.get('total_amount', 0):,.0f} ك.و\n"
                content += f"  المحاسب: {invoice.get('accountant_name', '')}\n"
                content += "-"*30 + "\n"
            if len(report['invoices']) > 50:
                content += f"\n... وعرض {len(report['invoices']) - 50} فاتورة إضافية\n"
        text_widget.insert('1.0', content)
        text_widget.config(state='disabled')
    
    # ============== دوال تقرير أوراق التأشيرات الجديدة ==============

    def show_visa_report(self):
        """عرض تقرير أوراق التأشيرات"""
        if not self.report_manager:
            self.show_error("لم يتم تحميل نظام التقارير")
            return
        
        # يمكن إضافة فلترة بسيطة باختيار القطاع (اختياري)
        response = messagebox.askquestion("فلترة", 
            "هل تريد تطبيق فلترة حسب قطاع معين؟\n\nنعم: اختر قطاعاً\nلا: جميع القطاعات",
            icon='question')
        
        sector_id = None
        if response == 'yes':
            # نافذة اختيار قطاع
            sector_window = tk.Toplevel(self)
            sector_window.title("اختر قطاع")
            sector_window.geometry("300x150")
            tk.Label(sector_window, text="القطاع:").pack(pady=10)
            
            sectors = self.report_manager.get_available_sectors()
            sector_names = ['الكل'] + [s['name'] for s in sectors]
            sector_var = tk.StringVar()
            sector_combo = ttk.Combobox(sector_window, textvariable=sector_var,
                                        values=sector_names, state='readonly')
            sector_combo.pack(pady=5)
            sector_combo.current(0)
            
            def on_select():
                nonlocal sector_id
                selected = sector_var.get()
                if selected != 'الكل':
                    for s in sectors:
                        if s['name'] == selected:
                            sector_id = s['id']
                            break
                sector_window.destroy()
                self._generate_visa_report(sector_id)
            
            tk.Button(sector_window, text="تطبيق", command=on_select,
                     bg='#27ae60', fg='white').pack(pady=10)
        else:
            self._generate_visa_report(None)

    def _generate_visa_report(self, sector_id):
        """توليد وعرض تقرير أوراق التأشيرات"""
        self.clear_frames()
        try:
            report = self.report_manager.get_visa_sheets_report(sector_id=sector_id)
            self.display_visa_report(report)
            self.current_report = report
            self.current_report_type = "visa_report"
            self.export_excel_btn.config(state='normal')
            self.filter_btn.config(state='disabled')  # لا حاجة لفلترة إضافية حالياً
            self.setup_export_options("visa_report")
            self.update_status("تم توليد تقرير أوراق التأشيرات")
        except Exception as e:
            self.show_error(f"خطأ في عرض التقرير: {e}")

    def display_visa_report(self, report):
        """عرض تقرير أوراق التأشيرات في شجرة (Treeview) مع تجميع هرمي"""
        frame = tk.Frame(self.results_frame)
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # معلومات التقرير
        info_frame = tk.LabelFrame(frame, text="معلومات التقرير", padx=10, pady=10)
        info_frame.pack(fill='x', pady=(0, 10))
        tk.Label(info_frame, text=f"عنوان التقرير: {report.get('report_title', '')}", 
                anchor='w').pack(fill='x')
        tk.Label(info_frame, text=f"تاريخ الإنشاء: {report.get('generated_at', '')}", 
                anchor='w').pack(fill='x')
        
        # إنشاء شجرة للعرض
        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill='both', expand=True)
        
        scrollbar_y = ttk.Scrollbar(tree_frame)
        scrollbar_y.pack(side='right', fill='y')
        scrollbar_x = ttk.Scrollbar(tree_frame, orient='horizontal')
        scrollbar_x.pack(side='bottom', fill='x')
        
        # الأعمدة: اسم الزبون، النوع، التأشيرة، 3 أعمدة تاريخ
        tree = ttk.Treeview(tree_frame, 
                           yscrollcommand=scrollbar_y.set,
                           xscrollcommand=scrollbar_x.set,
                           columns=('name', 'type', 'visa', 'date1', 'date2', 'date3'))
        
        scrollbar_y.config(command=tree.yview)
        scrollbar_x.config(command=tree.xview)
        
        # رؤوس الأعمدة
        tree.heading('#0', text='القطاع / العلبة الأم')
        tree.column('#0', width=250)
        
        tree.heading('name', text='اسم الزبون')
        tree.column('name', width=200)
        tree.heading('type', text='نوع الزبون')
        tree.column('type', width=100)
        tree.heading('visa', text='رصيد التأشيرة')
        tree.column('visa', width=120)
        for i, col in enumerate(['date1', 'date2', 'date3'], start=1):
            tree.heading(col, text=f'التاريخ {i}')
            tree.column(col, width=80, anchor='center')
        
        # تعبئة البيانات
        for sector in report.get('sectors', []):
            sector_id = tree.insert('', 'end', 
                                   text=f"قطاع: {sector['sector_name']} (إجمالي: {sector['total_customers']} زبون، تأشيرات: {sector['total_visa']:,.0f})",
                                   values=('', '', '', '', '', ''))
            
            for parent in sector.get('parents', []):
                parent_id = tree.insert(sector_id, 'end',
                                       text=f"⬤ {parent['parent_name']}",
                                       values=('', '', '', '', '', ''))
                
                for customer in parent.get('customers', []):
                    tree.insert(parent_id, 'end', text='',
                              values=(customer['name'],
                                     customer['financial_category'],
                                     f"{customer['visa_balance']:,.0f}",
                                     '', '', ''))
        
        tree.pack(fill='both', expand=True)
        
        # إجماليات
        grand_total = report.get('grand_total', {})
        total_frame = tk.LabelFrame(frame, text="الإجماليات", padx=10, pady=10)
        total_frame.pack(fill='x', pady=10)
        tk.Label(total_frame, 
                text=f"إجمالي عدد الزبائن: {grand_total.get('total_customers', 0):,} | "
                     f"إجمالي رصيد التأشيرات: {grand_total.get('total_visa', 0):,.0f}",
                font=('Arial', 10, 'bold')).pack()
    
    # ============== دوال مساعدة ==============
    
    def clear_frames(self):
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        for widget in self.export_frame.winfo_children():
            widget.destroy()
    
    def update_status(self, message: str):
        self.status_bar.config(text=message, fg='#27ae60')
    
    def show_error(self, message: str):
        self.status_bar.config(text=f"خطأ: {message}", fg='#e74c3c')
        messagebox.showerror("خطأ", message)

    def setup_export_options(self, report_type: str):
        for widget in self.export_frame.winfo_children():
            widget.destroy()
        export_frame = tk.Frame(self.export_frame, padx=20, pady=20)
        export_frame.pack(fill='both', expand=True)
        tk.Label(export_frame, text="خيارات التصدير", 
                font=('Arial', 14, 'bold')).pack(pady=(0, 20))
        name_frame = tk.Frame(export_frame)
        name_frame.pack(fill='x', pady=10)
        tk.Label(name_frame, text="اسم الملف:", 
                font=('Arial', 10)).pack(side='left', padx=(0, 10))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"تقرير_{report_type}_{timestamp}"
        self.filename_entry = tk.Entry(name_frame, width=40)
        self.filename_entry.insert(0, default_name)
        self.filename_entry.pack(side='left')
        btn_frame = tk.Frame(export_frame, pady=20)
        btn_frame.pack(fill='x')
        tk.Button(btn_frame, text="📥 تصدير إلى Excel", 
                command=lambda: self.export_current_report_to_excel(report_type),
                bg='#f39c12', fg='white',
                font=('Arial', 11, 'bold'),
                width=15).pack()

    def export_current_report_to_excel(self, report_type: str):
        if not self.current_report:
            messagebox.showwarning("تحذير", "لا يوجد تقرير للتصدير")
            return
        try:
            filename = self.filename_entry.get().strip()
            if not filename:
                filename = f"تقرير_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if not filename.lower().endswith('.xlsx'):
                filename += ".xlsx"
            success = False
            filepath = ""
            if report_type == "negative_balance_advanced":
                success, filepath = self.report_manager.export_negative_balance_report_to_excel(
                    self.current_report, filename
                )
            elif report_type == "cut_lists_advanced":
                success, filepath = self.report_manager.export_cut_lists_report_to_excel(
                    self.current_report, filename
                )
            elif report_type == "free_customers_advanced":
                success, filepath = self.report_manager.export_free_customers_to_excel(
                    self.current_report, filename
                )
            elif report_type in ["sales", "invoices", "dashboard"]:
                success, filepath = self.report_manager.export_to_excel_generic(
                    self.current_report, report_type
                )
            elif report_type == "visa_report":
                success, filepath = self.report_manager.export_visa_report_to_excel(
                    self.current_report, filename
                )
            elif report_type == "accountant_collections":   # إضافة هذا الفرع
                success, filepath = self.report_manager.export_accountant_collections_to_excel(
                    self.current_report, filename
                )
            else:
                messagebox.showwarning("تحذير", "نوع التقرير غير مدعوم للتصدير")
                return
            if success:
                messagebox.showinfo("نجاح", f"تم تصدير التقرير بنجاح إلى:\n{filepath}")
                try:
                    os.startfile(filepath) if os.name == 'nt' else webbrowser.open(filepath)
                except:
                    pass
                self.update_status("تم تصدير التقرير بنجاح")
            else:
                messagebox.showerror("خطأ", f"فشل تصدير التقرير: {filepath}")
                self.show_error(f"خطأ: {filepath}")
        except Exception as e:
            logger.error(f"خطأ في تصدير التقرير: {e}")
            messagebox.showerror("خطأ", f"فشل تصدير التقرير: {str(e)}")
            self.show_error(f"خطأ: {str(e)}")

    def export_current_to_excel(self):
        if self.current_report and self.current_report_type:
            self.export_current_report_to_excel(self.current_report_type)
        else:
            messagebox.showwarning("تحذير", "لا يوجد تقرير للتصدير")

    def show_advanced_filter(self):
        if self.current_report_type == "negative_balance_advanced":
            self.show_negative_balance_advanced_filter()
        elif self.current_report_type == "cut_lists_advanced":
            self.show_cut_lists_advanced()
        elif self.current_report_type == "free_customers_advanced":
            self.show_free_customers_advanced_filter()
        else:
            messagebox.showinfo("فلترة", "الفلترة المتقدمة غير متاحة لهذا النوع من التقارير")

    def show_negative_balance_advanced_filter(self):
        filter_window = tk.Toplevel(self)
        filter_window.title("فلترة متقدمة - قوائم الكسر")
        filter_window.geometry("500x650")
        
        filter_window.update_idletasks()
        x = (filter_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (filter_window.winfo_screenheight() // 2) - (650 // 2)
        filter_window.geometry(f"500x650+{x}+{y}")
        
        # إنشاء canvas مع scrollbar للمحتوى القابل للتمرير
        main_canvas = tk.Canvas(filter_window)
        main_canvas.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(filter_window, orient="vertical", command=main_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        
        main_canvas.configure(yscrollcommand=scrollbar.set)
        main_canvas.bind('<Configure>', lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))
        
        main_frame = tk.Frame(main_canvas, padx=20, pady=20)
        main_canvas.create_window((0, 0), window=main_frame, anchor="nw", width=460)
        
        tk.Label(main_frame, text="فلترة متقدمة - قوائم الكسر", 
                font=('Arial', 14, 'bold')).pack(pady=(0, 20))
        
        # مجال الرصيد
        balance_frame = tk.LabelFrame(main_frame, text="مجال الرصيد", padx=10, pady=10)
        balance_frame.pack(fill='x', pady=10)
        tk.Label(balance_frame, text="من:").grid(row=0, column=0, padx=5, pady=5)
        min_balance_entry = tk.Entry(balance_frame, width=15)
        min_balance_entry.insert(0, "-1000000")
        min_balance_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(balance_frame, text="إلى:").grid(row=0, column=2, padx=5, pady=5)
        max_balance_entry = tk.Entry(balance_frame, width=15)
        max_balance_entry.insert(0, "0")
        max_balance_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # أنواع العدادات
        meter_frame = tk.LabelFrame(main_frame, text="أنواع العدادات", padx=10, pady=10)
        meter_frame.pack(fill='x', pady=10)
        meter_types = ['مولدة', 'علبة توزيع', 'رئيسية', 'زبون']
        meter_vars = {}
        for i, meter_type in enumerate(meter_types):
            var = tk.BooleanVar(value=True if meter_type == 'زبون' else False)
            chk = tk.Checkbutton(meter_frame, text=meter_type, variable=var)
            chk.grid(row=i//2, column=i%2, sticky='w', padx=10, pady=5)
            meter_vars[meter_type] = var
        
        # التصنيفات المالية المستثناة
        category_frame = tk.LabelFrame(main_frame, text="استبعاد التصنيفات", padx=10, pady=10)
        category_frame.pack(fill='x', pady=10)
        categories = ['normal', 'free', 'vip', 'free_vip']
        category_names = {
            'normal': 'عادي',
            'free': 'مجاني',
            'vip': 'VIP',
            'free_vip': 'مجاني + VIP'
        }
        category_vars = {}
        for i, category in enumerate(categories):
            var = tk.BooleanVar(value=False)
            chk = tk.Checkbutton(category_frame, 
                            text=category_names.get(category, category),
                            variable=var)
            chk.grid(row=i//2, column=i%2, sticky='w', padx=10, pady=5)
            category_vars[category] = var
        
        # القطاع
        sector_frame = tk.LabelFrame(main_frame, text="القطاع", padx=10, pady=10)
        sector_frame.pack(fill='x', pady=10)
        tk.Label(sector_frame, text="اختر قطاع:").pack(side='left', padx=5)
        sectors = self.report_manager.get_available_sectors()
        sector_options = [("الكل", None)]
        sector_options.extend([(s['name'], s['id']) for s in sectors])
        sector_combo = ttk.Combobox(sector_frame, 
                                values=[name for name, _ in sector_options],
                                state='readonly', width=30)
        sector_combo.pack(side='left', padx=5)
        sector_combo.current(0)
        
        # طريقة الترتيب
        sort_frame = tk.LabelFrame(main_frame, text="طريقة الترتيب", padx=10, pady=10)
        sort_frame.pack(fill='x', pady=10)
        sort_var = tk.StringVar(value="balance_desc")
        tk.Radiobutton(sort_frame, text="الرصيد تنازلياً (الأكبر فالأصغر)", 
                    variable=sort_var, value="balance_desc").pack(anchor='w', pady=2)
        tk.Radiobutton(sort_frame, text="الرصيد تصاعدياً (الأصغر فالأكبر)", 
                    variable=sort_var, value="balance_asc").pack(anchor='w', pady=2)
        tk.Radiobutton(sort_frame, text="الاسم أبجدياً", 
                    variable=sort_var, value="name").pack(anchor='w', pady=2)
        
        # إطار الأزرار في الأسفل (خارج الـ canvas)
        button_frame = tk.Frame(filter_window)
        button_frame.pack(side="bottom", fill="x", padx=20, pady=10)
        
        def apply_filter():
            try:
                min_balance = float(min_balance_entry.get())
                max_balance = float(max_balance_entry.get())
                include_meter_types = [mt for mt, var in meter_vars.items() if var.get()]
                exclude_categories = [cat for cat, var in category_vars.items() if var.get()]
                selected_sector = sector_combo.get()
                sector_id = None
                for name, sid in sector_options:
                    if name == selected_sector:
                        sector_id = sid
                        break
                sort_by = sort_var.get()
                filter_window.destroy()
                self.clear_frames()
                report = self.report_manager.get_negative_balance_lists_report(
                    min_balance=min_balance,
                    max_balance=max_balance,
                    exclude_categories=exclude_categories,
                    include_meter_types=include_meter_types,
                    sector_id=sector_id,
                    sort_by=sort_by
                )
                self.display_negative_balance_advanced(report)
                self.current_report = report
                self.current_report_type = "negative_balance_advanced"
                self.export_excel_btn.config(state='normal')
                self.filter_btn.config(state='normal')
                self.setup_export_options("negative_balance_advanced")
                self.update_status("تم توليد تقرير قوائم الكسر مع الفلترة المتقدمة")
            except ValueError:
                messagebox.showerror("خطأ", "قيم غير صحيحة. تأكد من إدخال أرقام صحيحة")
            except Exception as e:
                self.show_error(f"خطأ في التصفية: {e}")
        
        tk.Button(button_frame, text="تطبيق", command=apply_filter,
                bg='#27ae60', fg='white', width=15).pack(side='right', padx=5)
        tk.Button(button_frame, text="إلغاء", command=filter_window.destroy,
                bg='#e74c3c', fg='white', width=15).pack(side='right', padx=5)
        tk.Button(button_frame, text="إعادة تعيين", 
                command=lambda: self.reset_filter_fields(min_balance_entry, max_balance_entry,
                                                        meter_vars, category_vars,
                                                        sector_combo, sort_var),
                bg='#3498db', fg='white', width=15).pack(side='right', padx=5)


    def reset_filter_fields(self, min_balance_entry, max_balance_entry, 
                          meter_vars, category_vars, sector_combo, sort_var):
        min_balance_entry.delete(0, 'end')
        min_balance_entry.insert(0, "-1000000")
        max_balance_entry.delete(0, 'end')
        max_balance_entry.insert(0, "0")
        for var in meter_vars.values():
            var.set(False)
        meter_vars['زبون'].set(True)
        for var in category_vars.values():
            var.set(False)
        sector_combo.current(0)
        sort_var.set("balance_desc")
    
    def show_free_customers_advanced_filter(self):
        messagebox.showinfo("فلترة", "فلترة الزبائن المجانيين المتقدمة قريباً")

            # ============== تقرير جبايات المحاسب ==============

    def show_accountant_collections_report(self):
        """عرض تقرير جبايات المحاسب مع نافذة اختيار الفترة والمحاسب"""
        if not self.report_manager:
            self.show_error("لم يتم تحميل نظام التقارير")
            return

        # نافذة الفلترة
        filter_window = tk.Toplevel(self)
        filter_window.title("تقرير جبايات المحاسب")
        filter_window.geometry("500x400")
        filter_window.resizable(False, False)

        main_frame = tk.Frame(filter_window, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)

        tk.Label(main_frame, text="تقرير جبايات المحاسب", 
                font=('Arial', 14, 'bold')).pack(pady=(0, 20))

        # حقل تاريخ البدء
        tk.Label(main_frame, text="تاريخ البداية (YYYY-MM-DD HH:MM:SS):").pack(anchor='w')
        start_entry = tk.Entry(main_frame, width=30)
        start_entry.insert(0, datetime.now().strftime("%Y-%m-%d 00:00:00"))
        start_entry.pack(fill='x', pady=5)

        # حقل تاريخ النهاية
        tk.Label(main_frame, text="تاريخ النهاية (YYYY-MM-DD HH:MM:SS):").pack(anchor='w')
        end_entry = tk.Entry(main_frame, width=30)
        end_entry.insert(0, datetime.now().strftime("%Y-%m-%d 23:59:59"))
        end_entry.pack(fill='x', pady=5)

        # اختيار المحاسب (اختياري)
        tk.Label(main_frame, text="المحاسب (اختياري):").pack(anchor='w')
        accountants = self.report_manager.get_accountants_list()
        accountant_names = ['الكل'] + [acc['full_name'] for acc in accountants]
        accountant_dict = {acc['full_name']: acc['id'] for acc in accountants}
        accountant_var = tk.StringVar(value='الكل')
        accountant_combo = ttk.Combobox(main_frame, textvariable=accountant_var,
                                        values=accountant_names, state='readonly')
        accountant_combo.pack(fill='x', pady=5)

        def apply_filter():
            try:
                start = start_entry.get().strip()
                end = end_entry.get().strip()
                selected_name = accountant_var.get()
                acc_id = accountant_dict.get(selected_name) if selected_name != 'الكل' else None

                filter_window.destroy()
                self.clear_frames()

                report = self.report_manager.get_accountant_collections_report(
                    accountant_id=acc_id,
                    start_datetime=start if start else None,
                    end_datetime=end if end else None
                )

                self.display_accountant_collections_report(report)
                self.current_report = report
                self.current_report_type = "accountant_collections"
                self.export_excel_btn.config(state='normal')
                self.filter_btn.config(state='disabled')
                self.setup_export_options("accountant_collections")
                self.update_status("تم توليد تقرير جبايات المحاسب")

            except Exception as e:
                self.show_error(f"خطأ في تطبيق الفلترة: {e}")

        # أزرار التحكم
        btn_frame = tk.Frame(main_frame, pady=20)
        btn_frame.pack(fill='x')
        tk.Button(btn_frame, text="تطبيق", command=apply_filter,
                 bg='#27ae60', fg='white', width=15).pack(side='right', padx=5)
        tk.Button(btn_frame, text="إلغاء", command=filter_window.destroy,
                 bg='#e74c3c', fg='white', width=15).pack(side='right', padx=5)

    def display_accountant_collections_report(self, report):
        """عرض تقرير جبايات المحاسب بشكل مفصل (كل فاتورة في صف)"""
        frame = tk.Frame(self.results_frame)
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        # معلومات التقرير
        info_frame = tk.LabelFrame(frame, text="معلومات التقرير", padx=10, pady=10)
        info_frame.pack(fill='x', pady=(0, 10))

        tk.Label(info_frame, text=f"عنوان التقرير: {report.get('report_title', '')}", 
                anchor='w').pack(fill='x')
        tk.Label(info_frame, text=f"تاريخ الإنشاء: {report.get('generated_at', '')}", 
                anchor='w').pack(fill='x')
        tk.Label(info_frame, text=f"الفترة: من {report.get('start_datetime', '')} إلى {report.get('end_datetime', '')}", 
                anchor='w').pack(fill='x')

        # ملخص سريع
        if 'accountant_name' in report:
            summary_text = f"المحاسب: {report['accountant_name']} | "
        else:
            summary_text = ""
        summary_text += (f"عدد الفواتير: {len(report.get('invoices', [])):,} | "
                        f"إجمالي الكيلوات: {report.get('total_kilowatts_all',0):,.0f} | "
                        f"المجاني: {report.get('total_free_all',0):,.0f} | "
                        f"الحسم: {report.get('total_discount_all',0):,.0f} | "
                        f"الإجمالي: {report.get('total_all',0):,.0f}")
        tk.Label(info_frame, text=summary_text, font=('Arial', 10, 'bold'),
                fg='#2c3e50').pack(anchor='w', pady=5)

        # جدول الفواتير
        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill='both', expand=True)

        scrollbar_y = ttk.Scrollbar(tree_frame)
        scrollbar_y.pack(side='right', fill='y')
        scrollbar_x = ttk.Scrollbar(tree_frame, orient='horizontal')
        scrollbar_x.pack(side='bottom', fill='x')

        # تحديد الأعمدة بناءً على وجود عدة محاسبين
        if 'accountant_name' in report:
            columns = ('رقم الفاتورة', 'التاريخ', 'الوقت', 'الزبون', 'الكيلوات', 'المجاني', 'الحسم', 'المبلغ', 'رقم الوصل')
        else:
            columns = ('المحاسب', 'رقم الفاتورة', 'التاريخ', 'الوقت', 'الزبون', 'الكيلوات', 'المجاني', 'الحسم', 'المبلغ', 'رقم الوصل')

        tree = ttk.Treeview(tree_frame,
                        yscrollcommand=scrollbar_y.set,
                        xscrollcommand=scrollbar_x.set,
                        columns=columns)
        scrollbar_y.config(command=tree.yview)
        scrollbar_x.config(command=tree.xview)

        tree.heading('#0', text='')
        tree.column('#0', width=0, stretch=False)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)

        # تعبئة الفواتير
        for inv in report.get('invoices', []):
            if 'accountant_name' in report:
                values = (
                    inv['invoice_number'],
                    inv['payment_date'],
                    inv['payment_time'],
                    inv.get('customer_name', ''),
                    f"{inv.get('kilowatt_amount', 0):,.0f}",
                    f"{inv.get('free_kilowatt', 0):,.0f}",
                    f"{inv.get('discount', 0):,.0f}",
                    f"{inv['total_amount']:,.0f}",
                    inv.get('receipt_number', '')
                )
            else:
                values = (
                    inv.get('accountant_name', ''),
                    inv['invoice_number'],
                    inv['payment_date'],
                    inv['payment_time'],
                    inv.get('customer_name', ''),
                    f"{inv.get('kilowatt_amount', 0):,.0f}",
                    f"{inv.get('free_kilowatt', 0):,.0f}",
                    f"{inv.get('discount', 0):,.0f}",
                    f"{inv['total_amount']:,.0f}",
                    inv.get('receipt_number', '')
                )
            tree.insert('', 'end', values=values)

        tree.pack(fill='both', expand=True)

        # عرض ملخص المحاسبين بشكل منفصل (اختياري) - يمكن إضافته في تبويب آخر أو كجدول صغير
        if 'summaries' in report and len(report['summaries']) > 1:
            summary_frame = tk.LabelFrame(frame, text="ملخص المحاسبين", padx=10, pady=10)
            summary_frame.pack(fill='x', pady=10)

            # إنشاء جدول صغير للملخص
            summary_tree = ttk.Treeview(summary_frame,
                                        columns=('المحاسب', 'عدد الفواتير', 'الكيلوات', 'المجاني', 'الحسم', 'الإجمالي'),
                                        height=5)
            summary_tree.heading('#0', text='')
            summary_tree.column('#0', width=0)
            for col in summary_tree['columns']:
                summary_tree.heading(col, text=col)
                summary_tree.column(col, width=100)

            for summ in report['summaries']:
                summary_tree.insert('', 'end', values=(
                    summ['accountant_name'],
                    f"{summ['invoice_count']:,}",
                    f"{summ.get('total_kilowatts',0):,.0f}",
                    f"{summ.get('total_free_kilowatts',0):,.0f}",
                    f"{summ.get('total_discount',0):,.0f}",
                    f"{summ['total_collected']:,.0f}"
                ))
            summary_tree.pack(fill='x')