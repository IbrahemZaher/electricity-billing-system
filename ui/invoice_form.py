# ui/invoice_form.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class InvoiceForm:
    """نموذج إنشاء فاتورة جديدة"""
    
    def __init__(self, parent, title, sectors, customers, user_data):
        self.parent = parent
        self.title = title
        self.sectors = sectors
        self.customers = customers
        self.user_data = user_data
        self.result = None
        
        self.selected_customer = None
        self.calculation_result = None
        
        self.create_dialog()
        self.create_widgets()
        
        self.dialog.grab_set()
        self.dialog.wait_window()
    
    def create_dialog(self):
        """إنشاء النافذة المنبثقة"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(self.title)
        self.dialog.geometry("800x700")
        self.dialog.resizable(True, True)
        self.dialog.configure(bg='#f5f7fa')
        
        # مركزية النافذة
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'800x700+{x}+{y}')
        
        # ربط زر الإغلاق
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
    
    def create_widgets(self):
        """إنشاء عناصر النموذج"""
        # إطار العنوان
        title_frame = tk.Frame(self.dialog, bg='#2ecc71', height=80)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, text=self.title,
                              font=('Arial', 20, 'bold'),
                              bg='#2ecc71', fg='white')
        title_label.pack(expand=True)
        
        # إطار المحتوى الرئيسي
        main_frame = tk.Frame(self.dialog, bg='#f5f7fa')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # دفتر الملاحظات للتبويب
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill='both', expand=True)
        
        # تبويب اختيار الزبون
        customer_tab = ttk.Frame(notebook)
        self.create_customer_tab(customer_tab)
        notebook.add(customer_tab, text='اختيار الزبون')
        
        # تبويب بيانات الدفع
        payment_tab = ttk.Frame(notebook)
        self.create_payment_tab(payment_tab)
        notebook.add(payment_tab, text='بيانات الدفع')
        
        # تبويب المعاينة
        preview_tab = ttk.Frame(notebook)
        self.create_preview_tab(preview_tab)
        notebook.add(preview_tab, text='معاينة الحساب')
        
        # أزرار التحكم
        self.create_buttons(main_frame)
    
    def create_customer_tab(self, parent):
        """إنشاء تبويب اختيار الزبون"""
        # إطار البحث
        search_frame = tk.Frame(parent, bg='#f5f7fa', padx=20, pady=20)
        search_frame.pack(fill='x')
        
        tk.Label(search_frame, text="🔍 البحث عن الزبون:",
                font=('Arial', 12, 'bold'),
                bg='#f5f7fa').pack(anchor='w')
        
        self.customer_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.customer_search_var,
                                font=('Arial', 12), width=40)
        search_entry.pack(fill='x', pady=10)
        search_entry.bind('<KeyRelease>', self.search_customers)
        
        # قائمة الزبائن
        list_frame = tk.Frame(parent, bg='white', relief='sunken', borderwidth=1)
        list_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        # شريط التمرير
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        # قائمة
        self.customer_listbox = tk.Listbox(list_frame, 
                                          font=('Arial', 11),
                                          yscrollcommand=scrollbar.set,
                                          selectmode='single',
                                          height=10)
        self.customer_listbox.pack(fill='both', expand=True)
        self.customer_listbox.bind('<<ListboxSelect>>', self.on_customer_selected)
        
        scrollbar.config(command=self.customer_listbox.yview)
        
        # تعبئة القائمة الأولية
        self.populate_customer_list()
    
    def search_customers(self, event=None):
        """بحث الزبائن"""
        search_term = self.customer_search_var.get().lower()
        self.customer_listbox.delete(0, tk.END)
        
        for customer in self.customers:
            if (search_term in customer.get('name', '').lower() or 
                search_term in customer.get('box_number', '').lower() or
                search_term in str(customer.get('id', '')).lower()):
                
                display_text = f"{customer['id']} - {customer['name']} | علبة: {customer.get('box_number', '')} | رصيد: {customer.get('current_balance', 0):,.0f} ل.س"
                self.customer_listbox.insert(tk.END, display_text)
                self.customer_listbox.customer_data = getattr(self.customer_listbox, 'customer_data', []) + [customer]
    
    def populate_customer_list(self):
        """تعبئة قائمة الزبائن"""
        self.customer_listbox.delete(0, tk.END)
        self.customer_listbox.customer_data = []
        
        for customer in self.customers[:50]:  # عرض أول 50 زبون فقط
            display_text = f"{customer['id']} - {customer['name']} | علبة: {customer.get('box_number', '')} | رصيد: {customer.get('current_balance', 0):,.0f} ل.س"
            self.customer_listbox.insert(tk.END, display_text)
            self.customer_listbox.customer_data.append(customer)
    
    def on_customer_selected(self, event):
        """عند اختيار زبون"""
        selection = self.customer_listbox.curselection()
        if selection:
            index = selection[0]
            self.selected_customer = self.customer_listbox.customer_data[index]
            self.display_customer_info()
    
    def display_customer_info(self):
        """عرض معلومات الزبون المحدد"""
        if not self.selected_customer:
            return
        
        # إطار معلومات الزبون
        if hasattr(self, 'info_frame'):
            self.info_frame.destroy()
        
        self.info_frame = tk.Frame(self.dialog, bg='#e8f4fc', relief='ridge', borderwidth=2)
        self.info_frame.place(x=20, y=150, width=760, height=100)
        
        info_text = f"""
        👤 الزبون: {self.selected_customer['name']}
        📍 القطاع: {self.selected_customer.get('sector_name', 'غير محدد')}
        📦 العلبة: {self.selected_customer.get('box_number', '')} | المسلسل: {self.selected_customer.get('serial_number', '')}
        💰 الرصيد الحالي: {self.selected_customer.get('current_balance', 0):,.0f} ل.س
        📊 آخر قراءة عداد: {self.selected_customer.get('last_counter_reading', 0):,.0f}
        """
        
        info_label = tk.Label(self.info_frame, text=info_text,
                             font=('Arial', 11),
                             bg='#e8f4fc', fg='#2c3e50',
                             justify='left')
        info_label.pack(padx=10, pady=10)
    
    def create_payment_tab(self, parent):
        """إنشاء تبويب بيانات الدفع"""
        # إطار الحقول
        fields_frame = tk.Frame(parent, bg='#f5f7fa', padx=30, pady=20)
        fields_frame.pack(fill='both', expand=True)
        
        # تعريف الحقول
        fields = [
            ('kilowatt_amount', 'كمية الدفع (كيلو)', 'entry', {'width': 15}),
            ('free_kilowatt', 'المجاني (كيلو)', 'entry', {'width': 15, 'default': '0'}),
            ('price_per_kilo', 'سعر الكيلو (ل.س)', 'entry', {'width': 15, 'default': '7200'}),
            ('discount', 'الحسم (ل.س)', 'entry', {'width': 15, 'default': '0'}),
            ('book_number', 'رقم الدفتر', 'entry', {'width': 20}),
            ('receipt_number', 'رقم الوصل', 'entry', {'width': 20}),
            ('visa_application', 'تنزيل تأشيرة', 'entry', {'width': 20}),
            ('customer_withdrawal', 'سحب المشترك', 'entry', {'width': 20})
        ]
        
        self.payment_vars = {}
        
        for i, (field_name, label, field_type, options) in enumerate(fields):
            row = i // 2
            col = (i % 2) * 2
            
            # تسمية الحقل
            lbl = tk.Label(fields_frame, text=label + ":",
                          font=('Arial', 11, 'bold'),
                          bg='#f5f7fa', fg='#2c3e50',
                          anchor='e')
            lbl.grid(row=row, column=col, sticky='e', padx=10, pady=12)
            
            # حقل الإدخال
            if field_type == 'entry':
                var = tk.StringVar(value=options.get('default', ''))
                entry = ttk.Entry(fields_frame, textvariable=var,
                                 font=('Arial', 11),
                                 width=options.get('width', 20))
                entry.grid(row=row, column=col+1, sticky='w', padx=10, pady=12)
                self.payment_vars[field_name] = var
        
        # زر حساب الفاتورة
        calc_btn = tk.Button(fields_frame, text="🧮 حساب الفاتورة",
                           command=self.calculate_invoice,
                           bg='#3498db', fg='white',
                           font=('Arial', 12, 'bold'),
                           padx=20, pady=10)
        calc_btn.grid(row=len(fields)//2 + 1, column=0, columnspan=4, pady=30)
    
    def calculate_invoice(self):
        """حساب الفاتورة"""
        if not self.selected_customer:
            messagebox.showwarning("تحذير", "يرجى اختيار زبون أولاً")
            return
        
        # التحقق من الحقول المطلوبة
        if not self.payment_vars['kilowatt_amount'].get():
            messagebox.showerror("خطأ", "كمية الدفع مطلوبة")
            return
        
        try:
            # تحميل مدير الفواتير
            from modules.invoices import InvoiceManager
            invoice_manager = InvoiceManager()
            
            # تجميع بيانات الدفع
            payment_data = {
                'kilowatt_amount': float(self.payment_vars['kilowatt_amount'].get()),
                'free_kilowatt': float(self.payment_vars['free_kilowatt'].get() or 0),
                'price_per_kilo': float(self.payment_vars['price_per_kilo'].get() or 7200),
                'discount': float(self.payment_vars['discount'].get() or 0)
            }
            
            # حساب الفاتورة
            self.calculation_result = invoice_manager.calculate_invoice(
                self.selected_customer,
                payment_data
            )
            
            if self.calculation_result:
                # تحديث تبويب المعاينة
                self.update_preview_tab()
                messagebox.showinfo("نجاح", "تم حساب الفاتورة بنجاح")
            else:
                messagebox.showerror("خطأ", "فشل حساب الفاتورة")
                
        except ValueError as e:
            messagebox.showerror("خطأ", "يرجى إدخال أرقام صحيحة في الحقول الرقمية")
        except Exception as e:
            logger.error(f"خطأ في حساب الفاتورة: {e}")
            messagebox.showerror("خطأ", f"فشل حساب الفاتورة: {str(e)}")
    
    def create_preview_tab(self, parent):
        """إنشاء تبويب معاينة الحساب"""
        self.preview_frame = tk.Frame(parent, bg='white')
        self.preview_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # رسالة افتراضية
        self.preview_label = tk.Label(self.preview_frame,
                                     text="سيظهر هنا تفاصيل الفاتورة بعد الحساب",
                                     font=('Arial', 14),
                                     bg='white', fg='#7f8c8d')
        self.preview_label.pack(expand=True)
    
    def update_preview_tab(self):
        """تحديث تبويب المعاينة بالحسابات"""
        if not self.calculation_result or not self.selected_customer:
            return
        
        # مسح المحتوى القديم
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        # إنشاء عرض تفصيلي
        details_frame = tk.Frame(self.preview_frame, bg='#f8f9fa', relief='solid', borderwidth=1)
        details_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # معلومات الزبون
        customer_info = f"""
        الزبون: {self.selected_customer['name']}
        القطاع: {self.selected_customer.get('sector_name', 'غير محدد')}
        العلبة: {self.selected_customer.get('box_number', '')} | المسلسل: {self.selected_customer.get('serial_number', '')}
        الرصيد السابق: {self.selected_customer.get('current_balance', 0):,.0f} ل.س
        """
        
        customer_label = tk.Label(details_frame, text=customer_info,
                                 font=('Arial', 11),
                                 bg='#f8f9fa', fg='#2c3e50',
                                 justify='left', anchor='w')
        customer_label.pack(padx=20, pady=10, anchor='w')
        
        # تفاصيل الحساب
        calc = self.calculation_result
        calculation_info = f"""
        ─────────────────────────────────────
        📊 تفاصيل الفاتورة:
        
        • كمية الدفع: {calc['kilowatt_amount']:,.1f} كيلو
        • المجاني: {calc['free_kilowatt']:,.1f} كيلو
        • الإجمالي المقطوع: {calc['consumed_kilowatt']:,.1f} كيلو
        • سعر الكيلو: {calc['price_per_kilo']:,.0f} ل.س
        • المبلغ قبل الحسم: {calc['net_amount']:,.0f} ل.س
        • الحسم: {calc['discount']:,.0f} ل.س
        
        ─────────────────────────────────────
        💰 المبلغ الإجمالي: {calc['total_amount']:,.0f} ليرة سورية
        ─────────────────────────────────────
        
        📈 قراءات العداد:
        • القراءة السابقة: {calc['previous_reading']:,.0f}
        • القراءة الجديدة: {calc['new_reading']:,.0f}
        • الكمية المقطوعة: {calc['consumed_kilowatt']:,.1f} كيلو
        
        💳 الرصيد الجديد: {calc['current_balance']:,.0f} ل.س
        🔑 كود التيليغرام: {calc.get('telegram_password', '')}
        """
        
        calculation_label = tk.Label(details_frame, text=calculation_info,
                                    font=('Arial', 11),
                                    bg='#f8f9fa', fg='#2c3e50',
                                    justify='left', anchor='w')
        calculation_label.pack(padx=20, pady=10, anchor='w')
    
    def create_buttons(self, parent):
        """إنشاء أزرار التحكم"""
        buttons_frame = tk.Frame(parent, bg='#f5f7fa')
        buttons_frame.pack(fill='x', pady=20)
        
        # زر حفظ وإنشاء الفاتورة
        save_btn = tk.Button(buttons_frame, text="💾 حفظ وإنشاء الفاتورة",
                           command=self.save_invoice,
                           bg='#27ae60', fg='white',
                           font=('Arial', 12, 'bold'),
                           padx=30, pady=12, cursor='hand2')
        save_btn.pack(side='right', padx=10)
        
        # زر الإلغاء
        cancel_btn = tk.Button(buttons_frame, text="❌ إلغاء",
                              command=self.cancel,
                              bg='#e74c3c', fg='white',
                              font=('Arial', 12),
                              padx=30, pady=12, cursor='hand2')
        cancel_btn.pack(side='left', padx=10)
    
    def save_invoice(self):
        """حفظ وإنشاء الفاتورة"""
        if not self.selected_customer:
            messagebox.showerror("خطأ", "يرجى اختيار زبون أولاً")
            return
        
        if not self.calculation_result:
            messagebox.showerror("خطأ", "يرجى حساب الفاتورة أولاً")
            return
        
        # تأكيد الإنشاء
        confirm = messagebox.askyesno(
            "تأكيد الإنشاء",
            "هل تريد إنشاء هذه الفاتورة؟\n\n"
            "سيتم تحديث قراءة العداد والرصيد للزبون."
        )
        
        if not confirm:
            return
        
        try:
            # الحصول على معرف القطاع
            sector_id = None
            for sector in self.sectors:
                if sector['name'] == self.selected_customer.get('sector_name', ''):
                    sector_id = sector['id']
                    break
            
            if not sector_id:
                messagebox.showerror("خطأ", "القطاع غير صالح")
                return
            
            # تجميع بيانات الفاتورة
            invoice_data = {
                'customer_id': self.selected_customer['id'],
                'customer_name': self.selected_customer['name'],
                'sector_id': sector_id,
                'user_id': self.user_data['id'],
                'kilowatt_amount': self.calculation_result['kilowatt_amount'],
                'free_kilowatt': self.calculation_result['free_kilowatt'],
                'price_per_kilo': self.calculation_result['price_per_kilo'],
                'discount': self.calculation_result['discount'],
                'total_amount': self.calculation_result['total_amount'],
                'previous_reading': self.calculation_result['previous_reading'],
                'new_reading': self.calculation_result['new_reading'],
                'current_balance': self.calculation_result['current_balance'],
                'telegram_password': self.calculation_result.get('telegram_password', ''),
                'book_number': self.payment_vars['book_number'].get(),
                'receipt_number': self.payment_vars['receipt_number'].get(),
                'visa_application': self.payment_vars['visa_application'].get(),
                'customer_withdrawal': self.payment_vars['customer_withdrawal'].get()
            }
            
            # إنشاء الفاتورة
            from modules.invoices import InvoiceManager
            invoice_manager = InvoiceManager()
            result = invoice_manager.create_invoice(invoice_data)
            
            if result.get('success'):
                self.result = result
                self.dialog.destroy()
            else:
                messagebox.showerror("خطأ", result.get('error', 'فشل إنشاء الفاتورة'))
                
        except Exception as e:
            logger.error(f"خطأ في إنشاء الفاتورة: {e}")
            messagebox.showerror("خطأ", f"فشل إنشاء الفاتورة: {str(e)}")
    
    def cancel(self):
        """إلغاء العملية"""
        self.result = None
        self.dialog.destroy()