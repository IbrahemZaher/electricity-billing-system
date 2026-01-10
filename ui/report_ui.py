# ui/report_ui.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from datetime import datetime, timedelta
from modules.reports import ReportManager
import webbrowser
import os

logger = logging.getLogger(__name__)

class ReportUI(tk.Frame):
    """واجهة التقارير والإحصائيات"""
    
    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.user_data = user_data
        self.report_manager = ReportManager()
        self.current_report = None
        self.create_widgets()
    
    def create_widgets(self):
        # قسم اختيار نوع التقرير
        report_type_frame = tk.LabelFrame(self, text="نوع التقرير", padx=10, pady=10)
        report_type_frame.pack(fill='x', padx=10, pady=10)
        
        # أزرار أنواع التقارير
        report_types = [
            ("📊 لوحة التحكم", self.show_dashboard_report),
            ("👥 تقرير الزبائن", self.show_customer_report),
            ("💰 تقرير الرصيد", self.show_balance_report),
            ("🧾 تقرير الفواتير", self.show_invoice_report),
            ("📈 تقرير المبيعات", self.show_sales_report),
            ("📅 المبيعات اليومية", self.show_daily_sales),
            ("🏢 تقرير القطاعات", self.show_sector_report)
        ]
        
        for i, (text, command) in enumerate(report_types):
            btn = tk.Button(report_type_frame, text=text, command=command,
                          width=15, height=2, bg='#3498db', fg='white')
            btn.grid(row=i//4, column=i%4, padx=5, pady=5, sticky='nsew')
        
        # إطار الفلاتر والتاريخ
        self.filter_frame = tk.LabelFrame(self, text="فلاتر التقرير", padx=10, pady=10)
        self.filter_frame.pack(fill='x', padx=10, pady=10)
        
        # تاريخ البداية
        tk.Label(self.filter_frame, text="من تاريخ:").grid(row=0, column=0, padx=5, pady=5)
        self.start_date_entry = tk.Entry(self.filter_frame, width=12)
        self.start_date_entry.grid(row=0, column=1, padx=5, pady=5)
        self.start_date_entry.insert(0, (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        
        # تاريخ النهاية
        tk.Label(self.filter_frame, text="إلى تاريخ:").grid(row=0, column=2, padx=5, pady=5)
        self.end_date_entry = tk.Entry(self.filter_frame, width=12)
        self.end_date_entry.grid(row=0, column=3, padx=5, pady=5)
        self.end_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        # زر تطبيق الفلاتر
        tk.Button(self.filter_frame, text="تطبيق الفلاتر", 
                 command=self.apply_filters, bg='#27ae60', fg='white').grid(row=0, column=4, padx=10)
        
        # زر تصدير
        tk.Button(self.filter_frame, text="📥 تصدير إلى Excel", 
                 command=self.export_report, bg='#f39c12', fg='white').grid(row=0, column=5, padx=5)
        
        # زر طباعة
        tk.Button(self.filter_frame, text="🖨️ طباعة التقرير", 
                 command=self.print_report, bg='#9b59b6', fg='white').grid(row=0, column=6, padx=5)
        
        # منطقة عرض التقرير
        report_display_frame = tk.Frame(self)
        report_display_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # إنشاء Notebook (تبويبات) لعرض التقارير
        self.notebook = ttk.Notebook(report_display_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # تبويب النتائج
        self.results_frame = tk.Frame(self.notebook)
        self.notebook.add(self.results_frame, text="النتائج")
        
        # تبويب الإحصائيات
        self.stats_frame = tk.Frame(self.notebook)
        self.notebook.add(self.stats_frame, text="الإحصائيات")
        
        # تبويب الرسوم البيانية
        self.charts_frame = tk.Frame(self.notebook)
        self.notebook.add(self.charts_frame, text="الرسوم البيانية")
        
        # عرض لوحة التحكم افتراضياً
        self.show_dashboard_report()
    
    def show_dashboard_report(self):
        """عرض تقرير لوحة التحكم"""
        try:
            report = self.report_manager.get_dashboard_statistics()
            self.current_report = report
            
            # مسح الإطارات السابقة
            self.clear_frames()
            
            # عرض النتائج
            self.display_dashboard_results(report)
            
        except Exception as e:
            logger.error(f"خطأ في عرض تقرير لوحة التحكم: {e}")
            messagebox.showerror("خطأ", f"فشل تحميل التقرير: {str(e)}")
    
    def show_customer_report(self):
        """عرض تقرير الزبائن"""
        try:
            report = self.report_manager.get_customers_by_sector_report()
            self.current_report = report
            
            self.clear_frames()
            self.display_customer_report(report)
            
        except Exception as e:
            logger.error(f"خطأ في عرض تقرير الزبائن: {e}")
    
    def show_balance_report(self):
        """عرض تقرير الرصيد"""
        # نافذة اختيار نوع الرصيد
        balance_dialog = BalanceTypeDialog(self)
        self.wait_window(balance_dialog)
        
        if balance_dialog.balance_type:
            try:
                report = self.report_manager.get_customer_balance_report(balance_dialog.balance_type)
                self.current_report = report
                
                self.clear_frames()
                self.display_balance_report(report)
                
            except Exception as e:
                logger.error(f"خطأ في عرض تقرير الرصيد: {e}")
    
    def show_invoice_report(self):
        """عرض تقرير الفواتير"""
        try:
            start_date = self.start_date_entry.get()
            end_date = self.end_date_entry.get()
            
            report = self.report_manager.get_invoice_detailed_report(start_date, end_date)
            self.current_report = report
            
            self.clear_frames()
            self.display_invoice_report(report)
            
        except Exception as e:
            logger.error(f"خطأ في عرض تقرير الفواتير: {e}")
    
    def show_sales_report(self):
        """عرض تقرير المبيعات"""
        # نافذة اختيار نوع التجميع
        sales_dialog = SalesGroupDialog(self)
        self.wait_window(sales_dialog)
        
        if sales_dialog.group_by:
            try:
                start_date = self.start_date_entry.get()
                end_date = self.end_date_entry.get()
                
                report = self.report_manager.get_sales_report(start_date, end_date, sales_dialog.group_by)
                self.current_report = report
                
                self.clear_frames()
                self.display_sales_report(report)
                
            except Exception as e:
                logger.error(f"خطأ في عرض تقرير المبيعات: {e}")
    
    def show_daily_sales(self):
        """عرض تقرير المبيعات اليومية"""
        try:
            report = self.report_manager.get_daily_sales_summary()
            self.current_report = report
            
            self.clear_frames()
            self.display_daily_sales(report)
            
        except Exception as e:
            logger.error(f"خطأ في عرض تقرير المبيعات اليومية: {e}")
    
    def show_sector_report(self):
        """عرض تقرير القطاعات"""
        try:
            report = self.report_manager.get_customers_by_sector_report()
            self.current_report = report
            
            self.clear_frames()
            self.display_sector_report(report)
            
        except Exception as e:
            logger.error(f"خطأ في عرض تقرير القطاعات: {e}")
    
    def apply_filters(self):
        """تطبيق الفلاتر على التقرير الحالي"""
        messagebox.showinfo("تطبيق الفلاتر", "تم تطبيق الفلاتر بنجاح")
    
    def export_report(self):
        """تصدير التقرير الحالي إلى Excel"""
        if not self.current_report:
            messagebox.showwarning("تحذير", "لا يوجد تقرير للتصدير")
            return
        
        try:
            # تحديد نوع التقرير للتصدير
            report_type = "report"
            if 'report_type' in self.current_report:
                report_type = self.current_report['report_type']
            elif 'group_by' in self.current_report:
                report_type = f"sales_{self.current_report['group_by']}"
            
            filename = self.report_manager.export_report_to_excel(self.current_report, report_type)
            
            if filename and os.path.exists(filename):
                messagebox.showinfo("نجاح", f"تم تصدير التقرير إلى:\n{filename}")
                
                # فتح الملف
                try:
                    webbrowser.open(filename)
                except:
                    pass
            else:
                messagebox.showerror("خطأ", "فشل تصدير التقرير")
                
        except Exception as e:
            logger.error(f"خطأ في تصدير التقرير: {e}")
            messagebox.showerror("خطأ", f"فشل تصدير التقرير: {str(e)}")
    
    def print_report(self):
        """طباعة التقرير"""
        if not self.current_report:
            messagebox.showwarning("تحذير", "لا يوجد تقرير للطباعة")
            return
        
        messagebox.showinfo("طباعة", "سيتم إرسال التقرير إلى الطابعة")
        # هنا يمكن إضافة منطق الطباعة الفعلي
    
    def clear_frames(self):
        """مسح محتوى الإطارات"""
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        
        for widget in self.charts_frame.winfo_children():
            widget.destroy()
    
    def display_dashboard_results(self, report):
        """عرض نتائج لوحة التحكم"""
        # النتائج
        results_text = tk.Text(self.results_frame, wrap='word', height=20)
        results_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        text = f"""
        {'='*50}
        لوحة التحكم - إحصائيات النظام
        {'='*50}
        
        الزبائن:
        --------
        • إجمالي الزبائن: {report.get('total_customers', 0):,}
        • زبائن برصيد سالب: {report.get('negative_count', 0):,} ({abs(report.get('negative_total', 0)):,.0f} ل.س)
        • زبائن برصيد موجب: {report.get('positive_count', 0):,} ({report.get('positive_total', 0):,.0f} ل.س)
        
        المبيعات:
        ---------
        • الفواتير اليوم: {report.get('today_invoices', 0):,} فاتورة
        • إجمالي اليوم: {report.get('today_amount', 0):,.0f} ل.س
        • الفواتير الشهرية: {report.get('month_invoices', 0):,} فاتورة
        • إجمالي الشهر: {report.get('month_amount', 0):,.0f} ل.س
        
        أفضل القطاعات أداءً هذا الشهر:
        --------------------------
        """
        
        for sector in report.get('top_sectors', []):
            text += f"• {sector['name']}: {sector['invoice_count']} فاتورة ({sector['total_amount']:,.0f} ل.س)\n"
        
        text += f"\nتم الإنشاء: {report.get('generated_at', '')}"
        
        results_text.insert('1.0', text)
        results_text.config(state='disabled')
        
        # الإحصائيات
        stats_text = tk.Text(self.stats_frame, wrap='word')
        stats_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        stats = f"""
        الإحصائيات:
        -----------
        
        متوسط قيمة الفاتورة اليومية: {report.get('today_amount', 0) / max(report.get('today_invoices', 1), 1):,.0f} ل.س
        متوسط قيمة الفاتورة الشهرية: {report.get('month_amount', 0) / max(report.get('month_invoices', 1), 1):,.0f} ل.س
        
        نسبة الزبائن برصيد سالب: {(report.get('negative_count', 0) / max(report.get('total_customers', 1), 1) * 100):.1f}%
        نسبة الزبائن برصيد موجب: {(report.get('positive_count', 0) / max(report.get('total_customers', 1), 1) * 100):.1f}%
        
        صافي الرصيد: {(report.get('positive_total', 0) + report.get('negative_total', 0)):,.0f} ل.س
        """
        
        stats_text.insert('1.0', stats)
        stats_text.config(state='disabled')
    
    def display_balance_report(self, report):
        """عرض تقرير الرصيد"""
        # إنشاء Treeview لعرض الزبائن
        tree_frame = tk.Frame(self.results_frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('ID', 'الاسم', 'القطاع', 'الرصيد', 'الحالة', 'الهاتف')
        
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        tree.column('الاسم', width=150)
        
        # إضافة البيانات
        for customer in report.get('customers', []):
            balance = customer['current_balance']
            status = 'سالب' if balance < 0 else 'موجب' if balance > 0 else 'صفر'
            
            tree.insert('', 'end', values=(
                customer['id'],
                customer['name'],
                customer.get('sector_name', ''),
                f"{balance:,.0f}",
                status,
                customer.get('phone_number', '')
            ))
        
        # شريط التمرير
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # عرض الإحصائيات
        stats_text = tk.Text(self.stats_frame, wrap='word')
        stats_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        stats = f"""
        تقرير الرصيد ({report.get('report_type', 'all')})
        {'='*50}
        
        إجمالي الزبائن: {report.get('total_count', 0):,}
        إجمالي الرصيد: {report.get('total_balance', 0):,.0f} ل.س
        إجمالي الرصيد السالب: {report.get('negative_total', 0):,.0f} ل.س
        إجمالي الرصيد الموجب: {report.get('positive_total', 0):,.0f} ل.س
        صافي الرصيد: {(report.get('positive_total', 0) + report.get('negative_total', 0)):,.0f} ل.س
        
        تم الإنشاء: {report.get('generated_at', '')}
        """
        
        stats_text.insert('1.0', stats)
        stats_text.config(state='disabled')
    
    def display_invoice_report(self, report):
        """عرض تقرير الفواتير"""
        # Treeview للفواتير
        tree_frame = tk.Frame(self.results_frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('الرقم', 'التاريخ', 'الزبون', 'القطاع', 'الكيلوات', 'المبلغ', 'المحاسب')
        
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        tree.column('الزبون', width=150)
        tree.column('الرقم', width=120)
        
        # إضافة البيانات
        for invoice in report.get('invoices', []):
            tree.insert('', 'end', values=(
                invoice['invoice_number'],
                invoice['payment_date'],
                invoice['customer_name'],
                invoice.get('sector_name', ''),
                f"{invoice.get('kilowatt_amount', 0):.1f}",
                f"{invoice.get('total_amount', 0):,.0f}",
                invoice.get('accountant_name', '')
            ))
        
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # الإحصائيات
        stats_text = tk.Text(self.stats_frame, wrap='word')
        stats_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        stats = f"""
        تقرير الفواتير
        {'='*50}
        
        الفترة: من {report['period']['start_date']} إلى {report['period']['end_date']}
        إجمالي الفواتير: {report.get('total_count', 0):,}
        
        تم الإنشاء: {report.get('generated_at', '')}
        """
        
        stats_text.insert('1.0', stats)
        stats_text.config(state='disabled')
    
    def display_sales_report(self, report):
        """عرض تقرير المبيعات"""
        # Treeview للمبيعات
        tree_frame = tk.Frame(self.results_frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('الفترة', 'عدد الفواتير', 'إجمالي المبلغ', 'إجمالي الكيلوات', 'متوسط الفاتورة')
        
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)
        
        # إضافة البيانات
        for data in report.get('sales_data', []):
            avg_amount = data.get('average_amount', 0)
            tree.insert('', 'end', values=(
                data['period'],
                data.get('invoice_count', 0),
                f"{data.get('total_amount', 0):,.0f}",
                f"{data.get('total_kilowatts', 0):.1f}",
                f"{avg_amount:,.0f}" if avg_amount else '0'
            ))
        
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # الإحصائيات
        stats_text = tk.Text(self.stats_frame, wrap='word')
        stats_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        totals = report.get('totals', {})
        stats = f"""
        تقرير المبيعات ({report.get('group_by', 'daily')})
        {'='*50}
        
        الفترة: من {report['period']['start_date']} إلى {report['period']['end_date']}
        
        الإجماليات:
        • عدد الفواتير: {totals.get('total_invoices', 0):,}
        • إجمالي المبلغ: {totals.get('grand_total', 0):,.0f} ل.س
        • إجمالي الكيلوات: {totals.get('total_kilowatts', 0):.1f}
        • إجمالي الخصم: {totals.get('total_discount', 0):,.0f} ل.س
        
        المتوسطات:
        • متوسط الفاتورة: {totals.get('grand_total', 0) / max(totals.get('total_invoices', 1), 1):,.0f} ل.س
        • متوسط الكيلوات/فاتورة: {totals.get('total_kilowatts', 0) / max(totals.get('total_invoices', 1), 1):.1f}
        
        تم الإنشاء: {report.get('generated_at', '')}
        """
        
        stats_text.insert('1.0', stats)
        stats_text.config(state='disabled')
    
    def display_daily_sales(self, report):
        """عرض تقرير المبيعات اليومية"""
        # النتائج
        results_text = tk.Text(self.results_frame, wrap='word')
        results_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        today = report.get('today', {})
        yesterday = report.get('yesterday', {})
        
        text = f"""
        تقرير المبيعات اليومية
        {'='*50}
        
        التاريخ: {report.get('date', '')}
        
        أداء اليوم:
        • عدد الفواتير: {today.get('invoice_count', 0):,}
        • إجمالي المبلغ: {today.get('total_amount', 0):,.0f} ل.س
        • إجمالي الكيلوات: {today.get('total_kilowatts', 0):.1f}
        • متوسط الفاتورة: {today.get('average_amount', 0):,.0f} ل.س
        
        المقارنة مع الأمس:
        • عدد فواتير الأمس: {yesterday.get('invoice_count', 0):,}
        • إجمالي أمس: {yesterday.get('total_amount', 0):,.0f} ل.س
        • نسبة التغير: {report.get('change_percentage', 0):.1f}%
        
        أفضل 5 زبائن اليوم:
        -----------------
        """
        
        for i, customer in enumerate(report.get('top_customers', []), 1):
            text += f"{i}. {customer['customer_name']} ({customer.get('sector_name', '')}): "
            text += f"{customer['invoice_count']} فواتير، {customer['total_amount']:,.0f} ل.س\n"
        
        text += f"\nتم الإنشاء: {report.get('generated_at', '')}"
        
        results_text.insert('1.0', text)
        results_text.config(state='disabled')
    
    def display_sector_report(self, report):
        """عرض تقرير القطاعات"""
        # Treeview للقطاعات
        tree_frame = tk.Frame(self.results_frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('القطاع', 'عدد الزبائن', 'إجمالي الرصيد', 'متوسط الرصيد', 'سالب', 'موجب', 'صفر')
        
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        tree.column('القطاع', width=150)
        
        # إضافة البيانات
        for sector in report.get('sectors', []):
            tree.insert('', 'end', values=(
                sector['sector_name'],
                sector.get('customer_count', 0),
                f"{sector.get('total_balance', 0):,.0f}",
                f"{sector.get('average_balance', 0):,.0f}",
                sector.get('negative_count', 0),
                sector.get('positive_count', 0),
                sector.get('zero_count', 0)
            ))
        
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')


class BalanceTypeDialog(tk.Toplevel):
    """نافذة اختيار نوع تقرير الرصيد"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("اختر نوع تقرير الرصيد")
        self.geometry("300x200")
        self.balance_type = None
        
        self.create_widgets()
        self.center_window()
    
    def center_window(self):
        """توسيط النافذة"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        """إنشاء عناصر الواجهة"""
        main_frame = tk.Frame(self, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        tk.Label(main_frame, text="اختر نوع تقرير الرصيد:", 
                font=('Arial', 12, 'bold')).pack(pady=(0, 20))
        
        balance_types = [
            ("الكل", "all"),
            ("رصيد سالب فقط", "negative"),
            ("رصيد موجب فقط", "positive"),
            ("رصيد صفر فقط", "zero")
        ]
        
        self.selected_type = tk.StringVar(value="all")
        
        for text, value in balance_types:
            rb = tk.Radiobutton(main_frame, text=text, variable=self.selected_type,
                              value=value, font=('Arial', 10))
            rb.pack(anchor='w', pady=5)
        
        btn_frame = tk.Frame(main_frame, pady=20)
        btn_frame.pack(fill='x')
        
        tk.Button(btn_frame, text="موافق", command=self.on_ok,
                 bg='#27ae60', fg='white').pack(side='right', padx=5)
        tk.Button(btn_frame, text="إلغاء", command=self.cancel,
                 bg='#e74c3c', fg='white').pack(side='right')
    
    def on_ok(self):
        """معالجة زر موافق"""
        self.balance_type = self.selected_type.get()
        self.destroy()
    
    def cancel(self):
        """إلغاء العملية"""
        self.balance_type = None
        self.destroy()

class SalesGroupDialog(tk.Toplevel):
    """نافذة اختيار نوع تجميع تقرير المبيعات"""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("اختر نوع التجميع")
        self.geometry("300x250")
        self.group_by = None
        
        self.create_widgets()
        self.center_window()
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        main_frame = tk.Frame(self, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        tk.Label(main_frame, text="اختر نوع تجميع البيانات:", 
                font=('Arial', 12, 'bold')).pack(pady=(0, 20))
        
        group_types = [
            ("يومي", "daily"),
            ("شهري", "monthly"),
            ("سنوي", "yearly"),
            ("حسب القطاع", "sector")
        ]
        
        self.selected_group = tk.StringVar(value="daily")
        
        for text, value in group_types:
            rb = tk.Radiobutton(main_frame, text=text, variable=self.selected_group,
                              value=value, font=('Arial', 10))
            rb.pack(anchor='w', pady=5)
        
        btn_frame = tk.Frame(main_frame, pady=20)
        btn_frame.pack(fill='x')
        
        tk.Button(btn_frame, text="موافق", command=self.ok,
                 bg='#27ae60', fg='white').pack(side='right', padx=5)
        tk.Button(btn_frame, text="إلغاء", command=self.cancel,
                 bg='#e74c3c', fg='white').pack(side='right')
    
    def ok(self):
        self.group_by = self.selected_group.get()
        self.destroy()
    
    def cancel(self):
        self.destroy()