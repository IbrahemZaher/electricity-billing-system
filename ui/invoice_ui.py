# ui/invoice_ui.py
# السطر 1 في invoice_ui.py يصبح:
from auth import has_permission, require_permission
# بدلاً من:
# from auth.permissions import require_permission, Permission
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime, timedelta
from modules.invoices import InvoiceManager
from modules.customers import CustomerManager
from database.connection import db

logger = logging.getLogger(__name__)

class InvoiceUI(tk.Frame):
    """واجهة إدارة الفواتير"""

    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.user_data = user_data
        self.invoice_manager = InvoiceManager()
        self.customer_manager = CustomerManager()
        
        # إعدادات العرض
        self.current_page = 1
        self.page_size = 50
        self.search_filters = {}
        
        self.create_widgets()
        self.load_invoices()
        self.load_customers_for_filter()
        self.load_sectors_for_filter()
    
    def create_widgets(self):
        """إنشاء عناصر الواجهة"""
        # الجزء العلوي: أدوات البحث والتصفية
        self.create_search_toolbar()
        
        # الجزء الأوسط: جدول الفواتير
        self.create_invoice_table()
        
        # الجزء السفلي: التحكم بالصفحات
        self.create_pagination()
        
        # الجزء الجانبي: تفاصيل الفاتورة
        self.create_detail_panel()
        
        # شريط الأدوات السفلي
        self.create_bottom_toolbar()
    
    def create_search_toolbar(self):
        """إنشاء شريط أدوات البحث"""
        toolbar = tk.Frame(self, bg='#f8f9fa', padx=10, pady=10)
        toolbar.pack(fill='x')
        
        # البحث بالتاريخ
        tk.Label(toolbar, text="من تاريخ:", bg='#f8f9fa').pack(side='left')
        self.start_date_entry = tk.Entry(toolbar, width=12)
        self.start_date_entry.insert(0, (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        self.start_date_entry.pack(side='left', padx=5)
        
        tk.Label(toolbar, text="إلى تاريخ:", bg='#f8f9fa').pack(side='left')
        self.end_date_entry = tk.Entry(toolbar, width=12)
        self.end_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.end_date_entry.pack(side='left', padx=5)
        
        # البحث بالزبون
        tk.Label(toolbar, text="الزبون:", bg='#f8f9fa').pack(side='left')
        self.customer_combo = ttk.Combobox(toolbar, width=20, state='readonly')
        self.customer_combo.pack(side='left', padx=5)
        
        # البحث بالقطاع
        tk.Label(toolbar, text="القطاع:", bg='#f8f9fa').pack(side='left')
        self.sector_combo = ttk.Combobox(toolbar, width=15, state='readonly')
        self.sector_combo.pack(side='left', padx=5)
        
        # زر البحث
        search_btn = tk.Button(toolbar, text="بحث", command=self.apply_filters,
                              bg='#3498db', fg='white')
        search_btn.pack(side='left', padx=10)
        
        # زر إعادة التعيين
        reset_btn = tk.Button(toolbar, text="إعادة تعيين", command=self.reset_filters,
                             bg='#95a5a6', fg='white')
        reset_btn.pack(side='left')
    
    def create_invoice_table(self):
        """إنشاء جدول الفواتير"""
        table_frame = tk.Frame(self)
        table_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # شريط التمرير
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side='right', fill='y')
        
        # تعريف الأعمدة
        columns = ('id', 'invoice_number', 'date', 'customer', 'sector', 
                  'amount', 'status', 'accountant')
        
        self.tree = ttk.Treeview(table_frame, columns=columns, 
                                yscrollcommand=scrollbar.set,
                                selectmode='browse', height=20)
        
        scrollbar.config(command=self.tree.yview)
        
        # تخصيص الأعمدة
        self.tree.column('#0', width=0, stretch=False)
        self.tree.column('id', width=50, anchor='center')
        self.tree.column('invoice_number', width=150, anchor='center')
        self.tree.column('date', width=100, anchor='center')
        self.tree.column('customer', width=180, anchor='w')
        self.tree.column('sector', width=100, anchor='center')
        self.tree.column('amount', width=120, anchor='center')
        self.tree.column('status', width=100, anchor='center')
        self.tree.column('accountant', width=120, anchor='w')
        
        # عناوين الأعمدة
        self.tree.heading('id', text='ID')
        self.tree.heading('invoice_number', text='رقم الفاتورة')
        self.tree.heading('date', text='التاريخ')
        self.tree.heading('customer', text='الزبون')
        self.tree.heading('sector', text='القطاع')
        self.tree.heading('amount', text='المبلغ')
        self.tree.heading('status', text='الحالة')
        self.tree.heading('accountant', text='المحاسب')
        
        self.tree.pack(fill='both', expand=True)
        
        # ربط حدث التحديد
        self.tree.bind('<<TreeviewSelect>>', self.on_invoice_select)
    
    def create_pagination(self):
        """إنشاء عناصر التحكم بالصفحات"""
        pagination_frame = tk.Frame(self, bg='#ecf0f1', pady=10)
        pagination_frame.pack(fill='x')
        
        self.page_label = tk.Label(pagination_frame, 
                                  text="الصفحة 1 من 1", 
                                  bg='#ecf0f1')
        self.page_label.pack(side='left', padx=10)
        
        nav_buttons = [
            ("⏪ الأولى", self.first_page),
            ("◀ السابقة", self.prev_page),
            ("▶ التالية", self.next_page),
            ("⏩ الأخيرة", self.last_page)
        ]
        
        for text, command in nav_buttons:
            btn = tk.Button(pagination_frame, text=text, command=command,
                          bg='#7f8c8d', fg='white', font=('Arial', 9))
            btn.pack(side='left', padx=2)
    
    def create_detail_panel(self):
        """إنشاء لوحة تفاصيل الفاتورة"""
        self.detail_frame = tk.Frame(self, width=350, bg='white',
                                    relief='sunken', borderwidth=2)
        self.detail_frame.pack_propagate(False)
    
    def create_bottom_toolbar(self):
        """إنشاء شريط الأدوات السفلي"""
        toolbar = tk.Frame(self, bg='#2c3e50', pady=8)
        toolbar.pack(fill='x', side='bottom')
        
        actions = [
            ("➕ فاتورة جديدة", self.create_new_invoice, '#27ae60'),
            ("✏️ تعديل الفاتورة", self.edit_invoice, '#3498db'),
            ("🗑️ حذف الفاتورة", self.delete_invoice, '#e74c3c'),
            ("🖨️ طباعة الفاتورة", self.print_invoice, '#9b59b6'),
            ("📊 ملخص اليوم", self.show_daily_summary, '#f39c12'),
            ("📈 تقرير الفواتير", self.generate_report, '#16a085')
        ]
        
        for text, command, color in actions:
            btn = tk.Button(toolbar, text=text, command=command,
                          bg=color, fg='white', font=('Arial', 10))
            btn.pack(side='left', padx=5)
    
    def load_customers_for_filter(self):
        """تحميل قائمة الزبائن للفلترة"""
        try:
            customers = self.customer_manager.search_customers()
            customer_list = ["الكل"]
            self.customer_filter_dict = {"الكل": None}
            
            for customer in customers:
                display_name = f"{customer['name']} - {customer.get('box_number', '')}"
                customer_list.append(display_name)
                self.customer_filter_dict[display_name] = customer['id']
            
            self.customer_combo['values'] = customer_list
            self.customer_combo.current(0)
            
        except Exception as e:
            logger.error(f"خطأ في تحميل الزبائن للفلترة: {e}")
    
    def load_sectors_for_filter(self):
        """تحميل القطاعات للفلترة"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id, name FROM sectors ORDER BY name")
                sectors = cursor.fetchall()
                
                sector_list = ["الكل"]
                self.sector_filter_dict = {"الكل": None}
                
                for sector in sectors:
                    sector_list.append(sector['name'])
                    self.sector_filter_dict[sector['name']] = sector['id']
                
                self.sector_combo['values'] = sector_list
                self.sector_combo.current(0)
                
        except Exception as e:
            logger.error(f"خطأ في تحميل القطاعات للفلترة: {e}")
    
    def load_invoices(self):
        """تحميل الفواتير للعرض"""
        try:
            # مسح البيانات القديمة
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # حساب الإزاحة
            offset = (self.current_page - 1) * self.page_size
            
            # تطبيق الفلاتر
            filters = self.search_filters.copy()
            filters['limit'] = self.page_size
            filters['offset'] = offset
            
            # جلب الفواتير
            invoices = self.invoice_manager.search_invoices(**filters)
            
            # إضافة البيانات للشجرة
            for invoice in invoices:
                self.tree.insert('', 'end', 
                               values=(invoice['id'],
                                       invoice['invoice_number'],
                                       invoice['payment_date'],
                                       invoice.get('customer_name', ''),
                                       invoice.get('sector_name', ''),
                                       f"{invoice['total_amount']:,.0f}",
                                       invoice['status'],
                                       invoice.get('accountant_name', '')),
                               tags=(invoice['status'],))
            
            # تحديث تسمية الصفحة
            # (لاحظ: نحن بحاجة إلى معرفة العدد الإجمالي، لكن search_invoices لا ترجعها حالياً)
            # سنضيف منطقاً للحصول على العدد الإجمالي في الخطوة القادمة
            
            # تلوين الصفوف حسب الحالة
            self.tree.tag_configure('active', background='#e8f5e9')
            self.tree.tag_configure('cancelled', background='#ffebee')
            
        except Exception as e:
            logger.error(f"خطأ في تحميل الفواتير: {e}")
            messagebox.showerror("خطأ", f"فشل تحميل الفواتير: {str(e)}")
    
    def apply_filters(self):
        """تطبيق الفلاتر"""
        self.search_filters = {}
        
        # تاريخ البدء
        start_date = self.start_date_entry.get().strip()
        if start_date:
            self.search_filters['start_date'] = start_date
        
        # تاريخ الانتهاء
        end_date = self.end_date_entry.get().strip()
        if end_date:
            self.search_filters['end_date'] = end_date
        
        # الزبون
        customer = self.customer_combo.get()
        if customer != "الكل":
            customer_id = self.customer_filter_dict.get(customer)
            if customer_id:
                self.search_filters['customer_id'] = customer_id
        
        # القطاع
        sector = self.sector_combo.get()
        if sector != "الكل":
            sector_id = self.sector_filter_dict.get(sector)
            if sector_id:
                self.search_filters['sector_id'] = sector_id
        
        # إعادة تحميل الفواتير
        self.current_page = 1
        self.load_invoices()
    
    def reset_filters(self):
        """إعادة تعيين الفلاتر"""
        self.start_date_entry.delete(0, 'end')
        self.start_date_entry.insert(0, (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        
        self.end_date_entry.delete(0, 'end')
        self.end_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        self.customer_combo.current(0)
        self.sector_combo.current(0)
        
        self.search_filters = {}
        self.current_page = 1
        self.load_invoices()
    
    def on_invoice_select(self, event):
        """عند اختيار فاتورة من القائمة"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        invoice_id = item['values'][0]
        
        # تحميل تفاصيل الفاتورة
        self.show_invoice_details(invoice_id)
    
    def show_invoice_details(self, invoice_id):
        """عرض تفاصيل الفاتورة"""
        try:
            # مسح اللوحة القديمة
            for widget in self.detail_frame.winfo_children():
                widget.destroy()
            
            # إظهار اللوحة
            self.detail_frame.pack(side='right', fill='y', padx=(0, 10), pady=10)
            
            # جلب بيانات الفاتورة
            invoice = self.invoice_manager.get_invoice(invoice_id)
            if not invoice:
                return
            
            # إنشاء محتوى اللوحة
            title = tk.Label(self.detail_frame, text="تفاصيل الفاتورة",
                           font=('Arial', 14, 'bold'), bg='white', fg='#2c3e50')
            title.pack(pady=(10, 5))
            
            # إنشاء إطار التفاصيل
            details_frame = tk.Frame(self.detail_frame, bg='white')
            details_frame.pack(fill='both', expand=True, padx=10)
            
            # عرض البيانات
            details = [
                ("رقم الفاتورة:", invoice['invoice_number']),
                ("التاريخ:", str(invoice['payment_date'])),
                ("الوقت:", str(invoice['payment_time'])),
                ("الزبون:", invoice.get('customer_name', 'غير محدد')),
                ("القطاع:", invoice.get('sector_name', 'غير محدد')),
                ("المحاسب:", invoice.get('accountant_name', 'غير محدد')),
                ("كيلوات الدفع:", f"{invoice['kilowatt_amount']:,.2f}"),
                ("كيلوات مجانية:", f"{invoice['free_kilowatt']:,.2f}"),
                ("سعر الكيلو:", f"{invoice['price_per_kilo']:,.0f}"),
                ("الخصم:", f"{invoice['discount']:,.0f}"),
                ("المبلغ الإجمالي:", f"{invoice['total_amount']:,.0f}"),
                ("القراءة السابقة:", f"{invoice['previous_reading']:,.2f}"),
                ("القراءة الجديدة:", f"{invoice['new_reading']:,.2f}"),
                ("الرصيد الحالي:", f"{invoice['current_balance']:,.0f}"),
                ("الحالة:", invoice['status'])
            ]
            
            for label, value in details:
                frame = tk.Frame(details_frame, bg='white')
                frame.pack(fill='x', pady=2)
                
                lbl = tk.Label(frame, text=label, font=('Arial', 10, 'bold'),
                             bg='white', width=15, anchor='w')
                lbl.pack(side='left')
                
                val = tk.Label(frame, text=value, font=('Arial', 10),
                             bg='white', fg='#555', anchor='w')
                val.pack(side='left', fill='x', expand=True)
            
            # معلومات إضافية
            if invoice.get('visa_application'):
                tk.Label(details_frame, text=f"تنزيل تأشيرة: {invoice['visa_application']}",
                        bg='white', font=('Arial', 10)).pack(anchor='w', pady=2)
            
            if invoice.get('customer_withdrawal'):
                tk.Label(details_frame, text=f"سحب المشترك: {invoice['customer_withdrawal']}",
                        bg='white', font=('Arial', 10)).pack(anchor='w', pady=2)
            
            if invoice.get('book_number'):
                tk.Label(details_frame, text=f"رقم الدفتر: {invoice['book_number']}",
                        bg='white', font=('Arial', 10)).pack(anchor='w', pady=2)
            
            if invoice.get('receipt_number'):
                tk.Label(details_frame, text=f"رقم الوصل: {invoice['receipt_number']}",
                        bg='white', font=('Arial', 10)).pack(anchor='w', pady=2)
            
            # أزرار خاصة بالفاتورة
            action_frame = tk.Frame(self.detail_frame, bg='white', pady=10)
            action_frame.pack(fill='x', padx=10)
            
            if invoice['status'] == 'active':
                tk.Button(action_frame, text="🖨️ طباعة الفاتورة", 
                         command=lambda: self.print_invoice(invoice_id),
                         bg='#3498db', fg='white').pack(fill='x', pady=2)
                
                tk.Button(action_frame, text="✏️ تعديل الفاتورة", 
                         command=lambda: self.edit_invoice(invoice_id),
                         bg='#f39c12', fg='white').pack(fill='x', pady=2)
                
                tk.Button(action_frame, text="❌ إلغاء الفاتورة", 
                         command=lambda: self.cancel_invoice(invoice_id),
                         bg='#e74c3c', fg='white').pack(fill='x', pady=2)
            else:
                tk.Label(action_frame, text="الفاتورة ملغية", 
                        bg='white', fg='red', font=('Arial', 12, 'bold')).pack()
                
        except Exception as e:
            logger.error(f"خطأ في عرض تفاصيل الفاتورة: {e}")
    
    def create_new_invoice(self):
        """إنشاء فاتورة جديدة"""
        try:
            require_permission(Permission.CREATE_BILLS)
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return

        dialog = CreateInvoiceDialog(self, self.user_data)
        self.wait_window(dialog)

        if dialog.result:
            self.load_invoices()
            messagebox.showinfo("نجاح", "تم إنشاء الفاتورة بنجاح")
    
    def edit_invoice(self, invoice_id=None):
        """تعديل فاتورة موجودة"""
        try:
            require_permission(Permission.EDIT_BILLS)
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return

        if not invoice_id:
            selection = self.tree.selection()
            if not selection:
                messagebox.showwarning("تحذير", "يرجى اختيار فاتورة للتعديل")
                return
            item = self.tree.item(selection[0])
            invoice_id = item['values'][0]

        dialog = EditInvoiceDialog(self, invoice_id, self.user_data)
        self.wait_window(dialog)

        if dialog.result:
            self.load_invoices()
            messagebox.showinfo("نجاح", "تم تعديل الفاتورة بنجاح")
    
    def delete_invoice(self):
        """حذف فاتورة"""
        try:
            require_permission(Permission.EDIT_BILLS)
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return

        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("تحذير", "يرجى اختيار فاتورة للحذف")
            return

        item = self.tree.item(selection[0])
        invoice_id = item['values'][0]
        invoice_number = item['values'][1]

        if not messagebox.askyesno("تأكيد الحذف", f"هل أنت متأكد من حذف الفاتورة {invoice_number}؟"):
            return

        try:
            result = self.invoice_manager.delete_invoice(invoice_id)
            if result['success']:
                self.load_invoices()
                self.detail_frame.pack_forget()
                messagebox.showinfo("نجاح", result['message'])
            else:
                messagebox.showerror("خطأ", result['error'])
        except Exception as e:
            logger.error(f"خطأ في حذف الفاتورة: {e}")
            messagebox.showerror("خطأ", f"فشل حذف الفاتورة: {str(e)}")
    
    def print_invoice(self, invoice_id=None):
        """طباعة الفاتورة"""
        try:
            require_permission(Permission.VIEW_REPORTS)
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return

        if not invoice_id:
            selection = self.tree.selection()
            if not selection:
                messagebox.showwarning("تحذير", "يرجى اختيار فاتورة للطباعة")
                return
            item = self.tree.item(selection[0])
            invoice_id = item['values'][0]

        try:
            messagebox.showinfo("طباعة", f"سيتم طباعة الفاتورة #{invoice_id}")
        except Exception as e:
            logger.error(f"خطأ في طباعة الفاتورة: {e}")
            messagebox.showerror("خطأ", f"فشل طباعة الفاتورة: {str(e)}")
    
    def cancel_invoice(self, invoice_id):
        """إلغاء الفاتورة"""
        try:
            require_permission(Permission.EDIT_BILLS)
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return

        if not messagebox.askyesno("تأكيد الإلغاء", "هل أنت متأكد من إلغاء هذه الفاتورة؟"):
            return

        try:
            result = self.invoice_manager.update_invoice(invoice_id, {'status': 'cancelled'})
            if result['success']:
                self.load_invoices()
                self.show_invoice_details(invoice_id)
                messagebox.showinfo("نجاح", result['message'])
            else:
                messagebox.showerror("خطأ", result['error'])
        except Exception as e:
            logger.error(f"خطأ في إلغاء الفاتورة: {e}")
            messagebox.showerror("خطأ", f"فشل إلغاء الفاتورة: {str(e)}")
    
    def show_daily_summary(self):
        """عرض ملخص المبيعات اليومية"""
        try:
            summary = self.invoice_manager.get_daily_summary()
            
            summary_text = f"""
            ملخص المبيعات اليومية:
            
            التاريخ: {summary.get('date', 'غير محدد')}
            عدد الفواتير: {summary.get('total_invoices', 0):,}
            إجمالي المبيعات: {summary.get('total_amount', 0):,.0f} ل.س
            إجمالي الكيلوات: {summary.get('total_kilowatts', 0):,.2f}
            كيلوات مجانية: {summary.get('total_free_kilowatts', 0):,.2f}
            إجمالي الخصم: {summary.get('total_discount', 0):,.0f} ل.س
            """
            
            messagebox.showinfo("ملخص اليوم", summary_text)
            
        except Exception as e:
            logger.error(f"خطأ في عرض الملخص اليومي: {e}")
            messagebox.showerror("خطأ", "فشل تحميل الملخص اليومي")
    
    def generate_report(self):
        """توليد تقرير عن الفواتير"""
        messagebox.showinfo("تقرير الفواتير", "سيتم توليد تقرير الفواتير")
        # سيتم ربط هذا بوحدة التقارير لاحقاً
    
    # دوال التحكم بالصفحات
    def first_page(self):
        self.current_page = 1
        self.load_invoices()
    
    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_invoices()
    
    def next_page(self):
        # هنا نحتاج إلى معرفة العدد الإجمالي للصفحات
        # سنقوم بتعديل load_invoices لتعيد العدد الإجمالي
        self.current_page += 1
        self.load_invoices()
    
    def last_page(self):
        # هنا نحتاج إلى معرفة العدد الإجمالي للصفحات
        self.current_page = 10  # قيمة افتراضية
        self.load_invoices()


class CreateInvoiceDialog(tk.Toplevel):
    """نافذة إنشاء فاتورة جديدة"""
    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.title("إنشاء فاتورة جديدة")
        self.geometry("700x800")
        self.user_data = user_data
        self.result = False
        
        self.customer_manager = CustomerManager()
        self.invoice_manager = InvoiceManager()
        
        self.create_widgets()
        self.center_window()
        self.load_customers()
        self.load_sectors()
    
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
        
        tk.Label(main_frame, text="إنشاء فاتورة جديدة", 
                font=('Arial', 16, 'bold')).pack(pady=(0, 20))
        
        # إنشاء عناصر النموذج
        self.fields = {}
        
        # قسم معلومات الزبون
        customer_frame = tk.LabelFrame(main_frame, text="معلومات الزبون", padx=10, pady=10)
        customer_frame.pack(fill='x', pady=5)
        
        tk.Label(customer_frame, text="الزبون:").grid(row=0, column=0, sticky='w', pady=5)
        self.customer_var = tk.StringVar()
        self.customer_combo = ttk.Combobox(customer_frame, textvariable=self.customer_var, 
                                          width=30, state='readonly')
        self.customer_combo.grid(row=0, column=1, pady=5)
        self.customer_combo.bind('<<ComboboxSelected>>', self.on_customer_select)
        
        tk.Label(customer_frame, text="القطاع:").grid(row=1, column=0, sticky='w', pady=5)
        self.sector_var = tk.StringVar()
        self.sector_combo = ttk.Combobox(customer_frame, textvariable=self.sector_var, 
                                        width=30, state='readonly')
        self.sector_combo.grid(row=1, column=1, pady=5)
        
        # قسم معلومات الفاتورة
        invoice_frame = tk.LabelFrame(main_frame, text="معلومات الفاتورة", padx=10, pady=10)
        invoice_frame.pack(fill='x', pady=5)
        
        fields_config = [
            ("تاريخ الدفع:", "payment_date", "entry"),
            ("وقت الدفع:", "payment_time", "entry"),
            ("القراءة السابقة:", "previous_reading", "entry"),
            ("القراءة الجديدة:", "new_reading", "entry"),
            ("كمية الدفع (كيلووات):", "kilowatt_amount", "entry"),
            ("المجاني (كيلووات):", "free_kilowatt", "entry"),
            ("سعر الكيلو:", "price_per_kilo", "entry"),
            ("الخصم:", "discount", "entry"),
            ("المبلغ الإجمالي:", "total_amount", "entry"),
            ("تنزيل تأشيرة:", "visa_application", "entry"),
            ("سحب المشترك:", "customer_withdrawal", "entry"),
            ("رقم الدفتر:", "book_number", "entry"),
            ("رقم الوصل:", "receipt_number", "entry"),
            ("كلمة مرور التيليغرام:", "telegram_password", "entry"),
            ("الملاحظات:", "notes", "text")
        ]
        
        for i, (label, field_name, field_type) in enumerate(fields_config):
            tk.Label(invoice_frame, text=label).grid(row=i, column=0, sticky='w', pady=5)
            
            if field_type == 'entry':
                entry = tk.Entry(invoice_frame, width=30)
                entry.grid(row=i, column=1, pady=5)
                self.fields[field_name] = entry
            elif field_type == 'text':
                text = tk.Text(invoice_frame, height=3, width=30)
                text.grid(row=i, column=1, pady=5)
                self.fields[field_name] = text
        
        # تعيين القيم الافتراضية
        self.fields['payment_date'].insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.fields['payment_time'].insert(0, datetime.now().strftime("%H:%M"))
        self.fields['price_per_kilo'].insert(0, "7200")
        
        # أزرار الحفظ والإلغاء
        btn_frame = tk.Frame(main_frame, pady=20)
        btn_frame.pack(fill='x')
        
        tk.Button(btn_frame, text="حفظ", command=self.save,
                 bg='#27ae60', fg='white').pack(side='right', padx=5)
        tk.Button(btn_frame, text="إلغاء", command=self.cancel,
                 bg='#e74c3c', fg='white').pack(side='right')
    
    def load_customers(self):
        """تحميل قائمة الزبائن"""
        try:
            customers = self.customer_manager.search_customers()
            customer_list = []
            self.customer_dict = {}
            
            for customer in customers:
                display_name = f"{customer['name']} - علبة: {customer.get('box_number', '')} - رصيد: {customer.get('current_balance', 0):,.0f}"
                customer_list.append(display_name)
                self.customer_dict[display_name] = customer
            
            self.customer_combo['values'] = customer_list
            
        except Exception as e:
            logger.error(f"خطأ في تحميل الزبائن: {e}")
    
    def load_sectors(self):
        """تحميل قائمة القطاعات"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id, name FROM sectors ORDER BY name")
                sectors = cursor.fetchall()
                
                sector_list = [sector['name'] for sector in sectors]
                self.sector_dict = {sector['name']: sector['id'] for sector in sectors}
                
                self.sector_combo['values'] = sector_list
                
        except Exception as e:
            logger.error(f"خطأ في تحميل القطاعات: {e}")
    
    def on_customer_select(self, event):
        """عند اختيار زبون"""
        selected = self.customer_var.get()
        customer = self.customer_dict.get(selected)
        
        if customer:
            # تعبئة بيانات الزبون
            self.sector_var.set(customer.get('sector_name', ''))
            
            # تعبئة القراءة السابقة
            self.fields['previous_reading'].delete(0, 'end')
            self.fields['previous_reading'].insert(0, str(customer.get('last_counter_reading', 0)))
            
            # تعبئة الرصيد الحالي
            self.fields['total_amount'].delete(0, 'end')
            self.fields['total_amount'].insert(0, str(customer.get('current_balance', 0)))
    
    def save(self):
        """حفظ الفاتورة"""
        try:
            # جمع البيانات من الحقول
            invoice_data = {}
            
            # بيانات الزبون
            selected_customer = self.customer_var.get()
            if not selected_customer:
                messagebox.showerror("خطأ", "يرجى اختيار زبون")
                return
            
            customer = self.customer_dict.get(selected_customer)
            invoice_data['customer_id'] = customer['id']
            
            # بيانات القطاع
            selected_sector = self.sector_var.get()
            if not selected_sector:
                messagebox.showerror("خطأ", "يرجى اختيار قطاع")
                return
            
            invoice_data['sector_id'] = self.sector_dict.get(selected_sector)
            
            # بيانات المستخدم
            invoice_data['user_id'] = self.user_data['id']
            
            # البيانات الأخرى
            for field_name, widget in self.fields.items():
                if isinstance(widget, tk.Entry):
                    value = widget.get().strip()
                elif isinstance(widget, tk.Text):
                    value = widget.get("1.0", "end-1c").strip()
                else:
                    continue
                
                # تحويل القيم الرقمية
                if field_name in ['previous_reading', 'new_reading', 'kilowatt_amount',
                                'free_kilowatt', 'price_per_kilo', 'discount', 'total_amount']:
                    try:
                        value = float(value) if value else 0.0
                    except ValueError:
                        value = 0.0
                
                invoice_data[field_name] = value
            
            # حساب الكيلوات إذا كانت القراءات موجودة
            if 'previous_reading' in invoice_data and 'new_reading' in invoice_data:
                if not invoice_data.get('kilowatt_amount'):
                    kilowatt_amount = invoice_data['new_reading'] - invoice_data['previous_reading']
                    invoice_data['kilowatt_amount'] = max(kilowatt_amount, 0)
                    self.fields['kilowatt_amount'].delete(0, 'end')
                    self.fields['kilowatt_amount'].insert(0, str(invoice_data['kilowatt_amount']))
            
            # حساب المبلغ الإجمالي إذا لم يكن موجوداً
            if not invoice_data.get('total_amount') and invoice_data.get('kilowatt_amount'):
                kilowatt_amount = invoice_data.get('kilowatt_amount', 0)
                free_kilowatt = invoice_data.get('free_kilowatt', 0)
                price_per_kilo = invoice_data.get('price_per_kilo', 0)
                discount = invoice_data.get('discount', 0)
                
                total = (kilowatt_amount - free_kilowatt) * price_per_kilo - discount
                invoice_data['total_amount'] = max(total, 0)
                self.fields['total_amount'].delete(0, 'end')
                self.fields['total_amount'].insert(0, str(invoice_data['total_amount']))
            
            # حساب الرصيد الجديد للزبون
            customer_balance = customer.get('current_balance', 0)
            invoice_amount = invoice_data.get('total_amount', 0)
            invoice_data['current_balance'] = customer_balance + invoice_amount
            
            # إنشاء الفاتورة
            result = self.invoice_manager.create_invoice(invoice_data)
            
            if result['success']:
                self.result = True
                self.destroy()
            else:
                messagebox.showerror("خطأ", result['error'])
                
        except Exception as e:
            logger.error(f"خطأ في حفظ الفاتورة: {e}")
            messagebox.showerror("خطأ", f"فشل حفظ الفاتورة: {str(e)}")
    
    def cancel(self):
        """إلغاء العملية"""
        self.destroy()


class EditInvoiceDialog(CreateInvoiceDialog):
    """نافذة تعديل فاتورة"""
    def __init__(self, parent, invoice_id, user_data):
        self.invoice_id = invoice_id
        super().__init__(parent, user_data)
        self.title("تعديل فاتورة")
        
        # تحميل بيانات الفاتورة الحالية
        self.load_invoice_data()
    
    def load_invoice_data(self):
        """تحميل بيانات الفاتورة للعرض"""
        try:
            invoice = self.invoice_manager.get_invoice(self.invoice_id)
            if not invoice:
                messagebox.showerror("خطأ", "الفاتورة غير موجودة")
                self.destroy()
                return
            
            # تعبئة بيانات الزبون
            customer_name = invoice.get('customer_name', '')
            box_number = invoice.get('box_number', '')
            customer_balance = invoice.get('current_balance', 0)
            display_name = f"{customer_name} - علبة: {box_number} - رصيد: {customer_balance:,.0f}"
            
            self.customer_var.set(display_name)
            
            # تعبئة بيانات القطاع
            self.sector_var.set(invoice.get('sector_name', ''))
            
            # تعبئة الحقول الأخرى
            for field_name, widget in self.fields.items():
                value = invoice.get(field_name, '')
                
                if isinstance(widget, tk.Entry):
                    widget.delete(0, 'end')
                    widget.insert(0, str(value))
                elif isinstance(widget, tk.Text):
                    widget.delete("1.0", "end")
                    widget.insert("1.0", str(value))
                    
        except Exception as e:
            logger.error(f"خطأ في تحميل بيانات الفاتورة: {e}")
            messagebox.showerror("خطأ", "فشل تحميل بيانات الفاتورة")
    
    def save(self):
        """حفظ التعديلات"""
        try:
            # جمع البيانات من الحقول
            update_data = {}
            
            # بيانات القطاع
            selected_sector = self.sector_var.get()
            if selected_sector:
                update_data['sector_id'] = self.sector_dict.get(selected_sector)
            
            # البيانات الأخرى
            for field_name, widget in self.fields.items():
                if isinstance(widget, tk.Entry):
                    value = widget.get().strip()
                elif isinstance(widget, tk.Text):
                    value = widget.get("1.0", "end-1c").strip()
                else:
                    continue
                
                # تحويل القيم الرقمية
                if field_name in ['previous_reading', 'new_reading', 'kilowatt_amount',
                                'free_kilowatt', 'price_per_kilo', 'discount', 'total_amount']:
                    try:
                        value = float(value) if value else 0.0
                    except ValueError:
                        value = 0.0
                
                update_data[field_name] = value
            
            # تحديث الفاتورة
            result = self.invoice_manager.update_invoice(self.invoice_id, update_data)
            
            if result['success']:
                self.result = True
                self.destroy()
            else:
                messagebox.showerror("خطأ", result['error'])
                
        except Exception as e:
            logger.error(f"خطأ في تحديث الفاتورة: {e}")
            messagebox.showerror("خطأ", f"فشل تحديث الفاتورة: {str(e)}")