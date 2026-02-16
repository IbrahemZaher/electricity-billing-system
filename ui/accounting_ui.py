# ui/accounting_ui.py - واجهة محاسبة متكاملة مع النظام الجديد
# تم التحديث لدعم نظام كمية الدفع والمجاني بدلاً من القراءة الجديدة
# تحسين المظهر: خطوط أكبر، ألوان مريحة، تباعد أفضل

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
from datetime import datetime
from modules.fast_operations import FastOperations
from modules.printing import FastPrinter

logger = logging.getLogger(__name__)

class AccountingUI(tk.Frame):
    """واجهة محاسبة محسنة تعمل بالنظام الجديد (كمية الدفع + مجاني) بتصميم مريح"""
    
    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.parent = parent
        self.user_data = user_data
        self.fast_ops = FastOperations()
        self.printer = FastPrinter()
        
        self.selected_customer = None
        self.sectors = []
        self.last_invoice_result = None
        self.search_results_data = []
        
        # تكوين الإطار ليملأ الشاشة كاملة
        self.pack(fill='both', expand=True)
        
        self.load_sectors()
        self.create_widgets()
        self.center_window()
    
    def load_sectors(self):
        """تحميل القطاعات مرة واحدة"""
        from database.connection import db
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id, name FROM sectors WHERE is_active = TRUE ORDER BY name")
                self.sectors = cursor.fetchall()
        except Exception as e:
            logger.error(f"خطأ في تحميل القطاعات: {e}")
            self.sectors = []
    
    def create_widgets(self):
        """إنشاء واجهة محاسبة بتصميم ثنائي الأعمدة محسن"""
        # إزالة أي عناصر سابقة
        for widget in self.winfo_children():
            widget.destroy()
        
        # الإطار الرئيسي بخلفية ناعمة
        main_frame = tk.Frame(self, bg='#e9ecef')
        main_frame.pack(fill='both', expand=True)
        
        # شريط الأدوات العلوي (مع زر إغلاق) بتدرج لوني
        self.create_toolbar(main_frame)
        
        # إطار المحتوى الرئيسي مقسم إلى عمودين مع هوامش مناسبة
        content_frame = tk.Frame(main_frame, bg='#e9ecef')
        content_frame.pack(fill='both', expand=True, padx=20, pady=15)
        
        # ========== العمود الأيمن (إدخال البيانات والنتائج) ==========
        right_column = tk.Frame(content_frame, bg='#f8f9fa', width=550, relief='ridge', bd=2)
        right_column.pack(side='right', fill='both', expand=True, padx=(10, 0))
        right_column.pack_propagate(False)
        
        # ========== العمود الأيسر (بحث ومعلومات الزبون) ==========
        left_column = tk.Frame(content_frame, bg='#f8f9fa', width=550, relief='ridge', bd=2)
        left_column.pack(side='left', fill='both', expand=True, padx=(0, 10))
        left_column.pack_propagate(False)
        
        # ----- العمود الأيسر: بحث ونتائج ومعلومات الزبون -----
        
        # قسم البحث بتصميم محسن
        search_frame = tk.LabelFrame(left_column, text="🔍 البحث عن زبون", 
                                      font=('Segoe UI', 14, 'bold'),
                                      bg='#f8f9fa', fg='#1e3c5c',
                                      padx=15, pady=15, relief='flat')
        search_frame.pack(fill='x', pady=(10, 15), padx=10)
        
        search_row = tk.Frame(search_frame, bg='#f8f9fa')
        search_row.pack(fill='x')
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_row, textvariable=self.search_var,
                                     font=('Segoe UI', 12), bg='white', fg='#2c3e50',
                                     relief='solid', bd=1, highlightthickness=1,
                                     highlightcolor='#3498db', highlightbackground='#ced4da')
        self.search_entry.pack(side='left', fill='x', expand=True, padx=(0, 8), ipady=5)
        self.search_entry.bind('<KeyRelease>', self.quick_search)
        self.search_entry.focus_set()
        
        search_btn = tk.Button(search_row, text="بحث", command=self.perform_search,
                               bg='#3498db', fg='white', font=('Segoe UI', 11, 'bold'),
                               padx=18, pady=4, bd=0, cursor='hand2', activebackground='#2980b9')
        search_btn.pack(side='left')
        
        # نتائج البحث (قائمة) مع تحسينات
        results_frame = tk.Frame(search_frame, bg='#f8f9fa', height=130)
        results_frame.pack(fill='x', pady=(12, 0))
        results_frame.pack_propagate(False)
        
        scrollbar_results = tk.Scrollbar(results_frame, orient='vertical', bg='#b0c4de')
        scrollbar_results.pack(side='right', fill='y')
        
        self.results_listbox = tk.Listbox(results_frame, font=('Segoe UI', 11),
                                           bg='white', fg='#1e3c5c',
                                           selectbackground='#3498db',
                                           selectforeground='white',
                                           yscrollcommand=scrollbar_results.set,
                                           height=5, bd=1, relief='solid',
                                           highlightthickness=0)
        self.results_listbox.pack(side='left', fill='both', expand=True)
        scrollbar_results.config(command=self.results_listbox.yview)
        self.results_listbox.bind('<<ListboxSelect>>', self.on_search_select)
        
        # قسم معلومات الزبون بتصميم مريح
        info_frame = tk.LabelFrame(left_column, text="📋 بيانات الزبون المحدد", 
                                    font=('Segoe UI', 14, 'bold'),
                                    bg='#f8f9fa', fg='#1e3c5c',
                                    padx=15, pady=15, relief='flat')
        info_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # عرض المعلومات في شبكة 4x2 مع تباعد أكبر
        info_grid = tk.Frame(info_frame, bg='#f8f9fa')
        info_grid.pack(fill='x', pady=5)
        
        info_labels = [
            ("الاسم:", "name"), ("القطاع:", "sector"),
            ("العلبة:", "box"), ("المسلسل:", "serial"),
            ("الرصيد (ك.واط):", "balance"), ("آخر قراءة:", "reading"),
            ("التأشيرة (ك.واط):", "visa"), ("السحب (ك.واط):", "withdrawal")
        ]
        
        self.info_vars = {}
        for i, (label_text, key) in enumerate(info_labels):
            row = i // 2
            col = (i % 2) * 2
            
            label = tk.Label(info_grid, text=label_text, bg='#f8f9fa', font=('Segoe UI', 11),
                             fg='#2c3e50', anchor='e')
            label.grid(row=row, column=col, sticky='e', padx=(10,5), pady=8)
            
            var = tk.StringVar(value="---")
            entry = tk.Entry(info_grid, textvariable=var,
                             font=('Segoe UI', 11, 'bold'), state='readonly',
                             bg='white', fg='#1e3c5c', readonlybackground='#ecf0f1',
                             relief='solid', bd=1, width=18, justify='right')
            entry.grid(row=row, column=col+1, sticky='w', padx=(0,10), pady=8)
            self.info_vars[key] = var
        
        # ----- العمود الأيمن: إدخال البيانات والأزرار والنتائج -----
        
        # قسم إدخال بيانات الفاتورة (4 حقول) بتصميم محسن
        input_frame = tk.LabelFrame(right_column, text="💰 إدخال بيانات الفاتورة", 
                                      font=('Segoe UI', 14, 'bold'),
                                      bg='#f8f9fa', fg='#1e3c5c',
                                      padx=15, pady=15, relief='flat')
        input_frame.pack(fill='x', pady=(10, 15), padx=10)
        
        # ترتيب الحقول في صفوف (كل صف حقل واحد مع أزرار التحكم لكمية الدفع)
        fields_frame = tk.Frame(input_frame, bg='#f8f9fa')
        fields_frame.pack(fill='x')
        
        # كمية الدفع (مع أزرار) - صف 1
        row1 = tk.Frame(fields_frame, bg='#f8f9fa')
        row1.pack(fill='x', pady=8)
        lbl1 = tk.Label(row1, text="كمية الدفع (كيلو):*", bg='#f8f9fa', font=('Segoe UI', 11),
                        fg='#c0392b', width=16, anchor='w')
        lbl1.pack(side='left')
        self.kilowatt_var = tk.StringVar()
        self.kilowatt_entry = tk.Entry(row1, textvariable=self.kilowatt_var,
                                        font=('Segoe UI', 11), width=12,
                                        bg='white', fg='#2c3e50', relief='solid', bd=1,
                                        highlightthickness=1, highlightcolor='#3498db')
        self.kilowatt_entry.pack(side='left', padx=5, ipady=3)
        
        btn_style = {'bg': '#3498db', 'fg': 'white', 'font': ('Segoe UI', 9, 'bold'),
                     'width': 4, 'bd': 0, 'cursor': 'hand2', 'activebackground': '#2980b9'}
        tk.Button(row1, text="+100", command=lambda: self.adjust_kilowatt(100), **btn_style).pack(side='left', padx=2)
        tk.Button(row1, text="+10", command=lambda: self.adjust_kilowatt(10), **btn_style).pack(side='left', padx=2)
        tk.Button(row1, text="-10", command=lambda: self.adjust_kilowatt(-10),
                  bg='#e74c3c', fg='white', font=('Segoe UI', 9, 'bold'),
                  width=4, bd=0, cursor='hand2', activebackground='#c0392b').pack(side='left', padx=2)
        
        # المجاني
        row2 = tk.Frame(fields_frame, bg='#f8f9fa')
        row2.pack(fill='x', pady=8)
        lbl2 = tk.Label(row2, text="المجاني (كيلو):", bg='#f8f9fa', font=('Segoe UI', 11),
                        fg='#2c3e50', width=16, anchor='w')
        lbl2.pack(side='left')
        self.free_var = tk.StringVar(value="0")
        self.free_entry = tk.Entry(row2, textvariable=self.free_var,
                                   font=('Segoe UI', 11), width=12,
                                   bg='white', fg='#2c3e50', relief='solid', bd=1,
                                   highlightthickness=1, highlightcolor='#3498db')
        self.free_entry.pack(side='left', padx=5, ipady=3)
        
        # سعر الكيلو
        row3 = tk.Frame(fields_frame, bg='#f8f9fa')
        row3.pack(fill='x', pady=8)
        lbl3 = tk.Label(row3, text="سعر الكيلو (ل.س):", bg='#f8f9fa', font=('Segoe UI', 11),
                        fg='#2c3e50', width=16, anchor='w')
        lbl3.pack(side='left')
        self.price_var = tk.StringVar(value="7200")
        self.price_entry = tk.Entry(row3, textvariable=self.price_var,
                                    font=('Segoe UI', 11), width=12,
                                    bg='white', fg='#2c3e50', relief='solid', bd=1,
                                    highlightthickness=1, highlightcolor='#3498db')
        self.price_entry.pack(side='left', padx=5, ipady=3)
        
        # الحسم
        row4 = tk.Frame(fields_frame, bg='#f8f9fa')
        row4.pack(fill='x', pady=8)
        lbl4 = tk.Label(row4, text="الحسم (ل.س):", bg='#f8f9fa', font=('Segoe UI', 11),
                        fg='#2c3e50', width=16, anchor='w')
        lbl4.pack(side='left')
        self.discount_var = tk.StringVar(value="0")
        self.discount_entry = tk.Entry(row4, textvariable=self.discount_var,
                                       font=('Segoe UI', 11), width=12,
                                       bg='white', fg='#2c3e50', relief='solid', bd=1,
                                       highlightthickness=1, highlightcolor='#3498db')
        self.discount_entry.pack(side='left', padx=5, ipady=3)
        
        # قسم الأزرار
        btn_frame = tk.LabelFrame(right_column, text="⚙️ الإجراءات", 
                                    font=('Segoe UI', 14, 'bold'),
                                    bg='#f8f9fa', fg='#1e3c5c',
                                    padx=15, pady=15, relief='flat')
        btn_frame.pack(fill='x', pady=(0, 15), padx=10)
        
        buttons_row = tk.Frame(btn_frame, bg='#f8f9fa')
        buttons_row.pack(pady=5)
        
        # أزرار بحجم أكبر وألوان مريحة
        btn_large_style = {'font': ('Segoe UI', 11, 'bold'), 'padx': 18, 'pady': 8,
                           'bd': 0, 'cursor': 'hand2', 'relief': 'flat'}
        
        self.process_btn = tk.Button(buttons_row, text="⚡ معالجة سريعة", command=self.fast_process,
                                      bg='#27ae60', fg='white', state='disabled',
                                      **btn_large_style, activebackground='#2ecc71')
        self.process_btn.pack(side='left', padx=6)
        
        self.print_btn = tk.Button(buttons_row, text="🖨️ طباعة", command=self.print_invoice,
                                   bg='#3498db', fg='white', state='disabled',
                                   **btn_large_style, activebackground='#5dade2')
        self.print_btn.pack(side='left', padx=6)
        
        clear_btn = tk.Button(buttons_row, text="🗑️ تصفير", command=self.clear_fields,
                              bg='#e67e22', fg='white',
                              **btn_large_style, activebackground='#f39c12')
        clear_btn.pack(side='left', padx=6)
        
        preview_btn = tk.Button(buttons_row, text="🧮 معاينة", command=self.calculate_preview,
                                bg='#9b59b6', fg='white',
                                **btn_large_style, activebackground='#af7ac5')
        preview_btn.pack(side='left', padx=6)
        
        # قسم تفاصيل المعالجة
        result_frame = tk.LabelFrame(right_column, text="📊 تفاصيل المعالجة", 
                                       font=('Segoe UI', 14, 'bold'),
                                       bg='#f8f9fa', fg='#1e3c5c',
                                       padx=15, pady=15, relief='flat')
        result_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        self.result_text = scrolledtext.ScrolledText(result_frame,
                                                      height=10,
                                                      font=('Segoe UI', 11),
                                                      bg='white',
                                                      fg='#2c3e50',
                                                      wrap='word',
                                                      bd=1,
                                                      relief='solid')
        self.result_text.pack(fill='both', expand=True)
        self.result_text.config(state='disabled')
        
        self.show_result_message("🔍 ابدأ بالبحث عن زبون...")
    
    def create_toolbar(self, parent):
        """إنشاء شريط الأدوات العلوي بتصميم جذاب"""
        toolbar = tk.Frame(parent, bg='#1e3c5c', height=60)
        toolbar.pack(fill='x', side='top')
        toolbar.pack_propagate(False)
        
        # زر إغلاق (×) بشكل دائري تقريباً
        close_btn = tk.Button(toolbar, text="✕", command=self.close_window,
                              bg='#c0392b', fg='white', font=('Segoe UI', 14, 'bold'),
                              bd=0, padx=18, pady=6, cursor='hand2',
                              activebackground='#e74c3c', relief='flat')
        close_btn.pack(side='left', padx=15)
        
        # العنوان
        title_label = tk.Label(toolbar, 
                              text="مولدة الريان - نظام المحاسبة السريعة",
                              font=('Segoe UI', 18, 'bold'),
                              bg='#1e3c5c', fg='#ecf0f1')
        title_label.pack(side='left', padx=25)
        
        # معلومات المستخدم
        user_info = tk.Label(toolbar,
                            text=f"المستخدم: {self.user_data.get('full_name', '')} | الدور: {self.user_data.get('role', '')}",
                            font=('Segoe UI', 11),
                            bg='#1e3c5c', fg='#bdc3c7')
        user_info.pack(side='right', padx=20)
    
    def close_window(self):
        """إغلاق النافذة المنبثقة"""
        self.parent.destroy()
    
    def center_window(self):
        """توسيط النافذة على الشاشة"""
        root = self.parent.winfo_toplevel()
        root.update_idletasks()

        width = 1300
        height = 750

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

        root.geometry(f'{width}x{height}+{x}+{y}')
        root.minsize(1100, 650)
    
    def quick_search(self, event=None):
        """بحث فوري أثناء الكتابة"""
        search_term = self.search_var.get().strip()
        if len(search_term) < 2:
            self.results_listbox.delete(0, tk.END)
            return
        
        if hasattr(self, '_search_job'):
            self.after_cancel(self._search_job)
        
        self._search_job = self.after(300, self._perform_search, search_term)
    
    def _perform_search(self, search_term):
        """تنفيذ البحث الفعلي"""
        if not search_term:
            return
        
        results = self.fast_ops.fast_search_customers(search_term, limit=30)
        self.results_listbox.delete(0, tk.END)
        
        self.search_results_data = results
        
        for customer in results:
            display_text = f"{customer['name']} | علبة: {customer['box_number']} | رصيد: {customer['current_balance']:,.0f} | آخر قراءة: {customer['last_counter_reading']:,.0f}"
            self.results_listbox.insert(tk.END, display_text)
    
    def perform_search(self):
        """بحث يدوي"""
        search_term = self.search_var.get().strip()
        if search_term:
            self._perform_search(search_term)
    
    def on_search_select(self, event=None):
        """عند اختيار نتيجة من البحث"""
        selection = self.results_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        if hasattr(self, 'search_results_data') and idx < len(self.search_results_data):
            customer = self.search_results_data[idx]
            self.select_customer(customer['id'])
    
    def select_customer(self, customer_id):
        """تحديد زبون وعرض بياناته"""
        try:
            customer_data = self.fast_ops.fast_get_customer_details(customer_id)
            if not customer_data:
                messagebox.showwarning("تحذير", "لم يتم العثور على بيانات الزبون")
                return
            
            self.selected_customer = customer_data
            
            # تحديث حقول المعلومات
            self.info_vars['name'].set(customer_data.get('name', '---'))
            self.info_vars['sector'].set(customer_data.get('sector_name', '---'))
            self.info_vars['box'].set(customer_data.get('box_number', '---'))
            self.info_vars['serial'].set(customer_data.get('serial_number', '---'))
            self.info_vars['balance'].set(f"{customer_data.get('current_balance', 0):,.0f}")
            self.info_vars['reading'].set(f"{customer_data.get('last_counter_reading', 0):,.0f}")
            self.info_vars['visa'].set(f"{customer_data.get('visa_balance', 0):,.0f}")
            self.info_vars['withdrawal'].set(f"{customer_data.get('withdrawal_amount', 0):,.0f}")
            
            # تصفير حقول الإدخال
            self.kilowatt_var.set("")
            self.free_var.set("0")
            self.price_var.set("7200")
            self.discount_var.set("0")
            
            # تفعيل الأزرار
            self.process_btn.config(state='normal', bg='#27ae60')
            self.print_btn.config(state='normal', bg='#3498db')
            
            self.show_result_message(f"✅ تم تحديد الزبون: {customer_data.get('name', '')}\n"
                                f"الرصيد الحالي: {customer_data.get('current_balance', 0):,.0f} كيلو واط\n"
                                f"آخر قراءة عداد: {customer_data.get('last_counter_reading', 0):,.0f}\n\n"
                                f"⚠️ أدخل كمية الدفع والمجاني ثم اضغط على 'معالجة سريعة'")
            
            self.kilowatt_entry.focus_set()
            
        except Exception as e:
            logger.error(f"خطأ في تحديد الزبون: {e}")
            messagebox.showerror("خطأ", f"فشل تحميل بيانات الزبون: {str(e)}")
    
    def adjust_kilowatt(self, amount):
        """ضبط كمية الدفع بزيادة/نقصان"""
        try:
            current = float(self.kilowatt_var.get() or 0)
            new_value = current + amount
            if new_value >= 0:
                self.kilowatt_var.set(str(int(new_value)))
        except ValueError:
            self.kilowatt_var.set("0")
    
    def calculate_preview(self):
        """حساب معاينة الفاتورة دون حفظ"""
        if not self.selected_customer:
            messagebox.showerror("خطأ", "يرجى اختيار زبون أولاً")
            return
        
        try:
            if not self.kilowatt_var.get().strip():
                messagebox.showerror("خطأ", "يرجى إدخال كمية الدفع")
                return
            
            kilowatt_amount = float(self.kilowatt_var.get())
            free_kilowatt = float(self.free_var.get() or 0)
            price_per_kilo = float(self.price_var.get() or 7200)
            discount = float(self.discount_var.get() or 0)
            
            last_reading = float(self.selected_customer.get('last_counter_reading', 0))
            current_balance = float(self.selected_customer.get('current_balance', 0))
            
            new_reading = last_reading + kilowatt_amount + free_kilowatt
            new_balance = current_balance + kilowatt_amount + free_kilowatt
            total_amount = (kilowatt_amount * price_per_kilo) - discount
            
            preview_text = f"""
            📊 معاينة الحساب (غير محفوظة):
            
            الزبون: {self.selected_customer.get('name', '')}
            
            البيانات المدخلة:
            • كمية الدفع: {kilowatt_amount:,.1f} كيلو
            • المجاني: {free_kilowatt:,.1f} كيلو
            • سعر الكيلو: {price_per_kilo:,.0f} ل.س
            • الحسم: {discount:,.0f} ل.س
            
            نتائج الحساب:
            • القراءة السابقة: {last_reading:,.0f}
            • القراءة الجديدة: {new_reading:,.0f}
            • الإجمالي المقطوع: {(kilowatt_amount + free_kilowatt):,.1f} كيلو
            • المبلغ الإجمالي: {total_amount:,.0f} ليرة سورية
            • الرصيد الجديد: {new_balance:,.0f} كيلو واط
            
            للحفظ الفعلي اضغط على "⚡ معالجة سريعة"
            """
            
            self.show_result_message(preview_text)
            
        except ValueError:
            messagebox.showerror("خطأ", "يرجى إدخال أرقام صحيحة في الحقول الرقمية")
        except Exception as e:
            logger.error(f"خطأ في حساب المعاينة: {e}")
            messagebox.showerror("خطأ", f"فشل حساب المعاينة: {str(e)}")
    
    def fast_process(self):
        """معالجة فاتورة سريعة بالنظام الجديد"""
        if not self.selected_customer:
            messagebox.showerror("خطأ", "يرجى اختيار زبون أولاً")
            return
        
        try:
            if not self.kilowatt_var.get().strip():
                messagebox.showerror("خطأ", "يرجى إدخال كمية الدفع")
                return
            
            kilowatt_amount = float(self.kilowatt_var.get())
            free_kilowatt = float(self.free_var.get() or 0)
            price_per_kilo = float(self.price_var.get() or 7200)
            discount = float(self.discount_var.get() or 0)
            
            if kilowatt_amount < 0 or free_kilowatt < 0:
                messagebox.showerror("خطأ", "كمية الدفع والمجاني يجب أن تكون أرقاماً موجبة")
                return
            
            last_reading = float(self.selected_customer.get('last_counter_reading', 0))
            total_kilowatt = kilowatt_amount + free_kilowatt
            
            confirm_msg = f"""
            هل أنت متأكد من معالجة الفاتورة؟
            
            الزبون: {self.selected_customer.get('name', '')}
            
            البيانات المدخلة:
            • كمية الدفع: {kilowatt_amount:,.1f} كيلو
            • المجاني: {free_kilowatt:,.1f} كيلو
            • الإجمالي: {total_kilowatt:,.1f} كيلو
            • سعر الكيلو: {price_per_kilo:,.0f} ل.س
            • الحسم: {discount:,.0f} ل.س
            
            ستصبح القراءة الجديدة: {last_reading + total_kilowatt:,.0f}
            """
            
            if not messagebox.askyesno("تأكيد المعالجة", confirm_msg):
                return
            
            result = self.fast_ops.fast_process_invoice(
                customer_id=self.selected_customer['id'],
                kilowatt_amount=kilowatt_amount,
                free_kilowatt=free_kilowatt,
                price_per_kilo=price_per_kilo,
                discount=discount,
                user_id=self.user_data.get('id', 1)
            )
            
            if result.get('success'):
                result_text = f"""
                ✅ تمت المعالجة بنجاح!
                
                تفاصيل الفاتورة:
                • رقم الفاتورة: {result.get('invoice_number', 'N/A')}
                • الزبون: {result.get('customer_name', 'N/A')}
                • كمية الدفع: {result.get('kilowatt_amount', 0):,.1f} كيلو
                • المجاني: {result.get('free_kilowatt', 0):,.1f} كيلو
                • الإجمالي المقطوع: {(result.get('kilowatt_amount', 0) + result.get('free_kilowatt', 0)):,.1f} كيلو
                • القراءة السابقة: {result.get('previous_reading', 0):,.0f}
                • القراءة الجديدة: {result.get('new_reading', 0):,.0f}
                • المبلغ الإجمالي: {result.get('total_amount', 0):,.0f} ليرة سورية
                • الرصيد الجديد: {result.get('new_balance', 0):,.0f}
                • وقت المعالجة: {result.get('processed_at', 'N/A')}
                
                يمكنك الآن طباعة الفاتورة.
                """
                
                self.show_result_message(result_text)
                self.last_invoice_result = result
                
                # تحديث بيانات الزبون المعروضة
                self.selected_customer['current_balance'] = result['new_balance']
                self.selected_customer['last_counter_reading'] = result['new_reading']
                self.info_vars['balance'].set(f"{result['new_balance']:,.0f}")
                self.info_vars['reading'].set(f"{result['new_reading']:,.0f}")
                
                if messagebox.askyesno("طباعة", "هل تريد طباعة الفاتورة الآن؟"):
                    self.print_invoice()
                
                self.clear_input_fields()
                
            else:
                error_msg = result.get('error', 'حدث خطأ غير معروف')
                self.show_result_message(f"❌ فشل المعالجة:\n{error_msg}")
                messagebox.showerror("خطأ", f"فشل المعالجة: {error_msg}")
                
        except ValueError as e:
            messagebox.showerror("خطأ", "يرجى إدخال أرقام صحيحة في الحقول الرقمية")
        except Exception as e:
            logger.error(f"خطأ في المعالجة: {e}")
            messagebox.showerror("خطأ", f"حدث خطأ غير متوقع: {str(e)}")
    
    def print_invoice(self):
        """طباعة الفاتورة"""
        if not hasattr(self, 'last_invoice_result') or not self.last_invoice_result:
            messagebox.showwarning("تحذير", "لا توجد فاتورة حديثة للطباعة")
            return
        
        try:
            invoice_data = {
                'customer_name': self.selected_customer.get('name', ''),
                'sector_name': self.selected_customer.get('sector_name', ''),
                'box_number': self.selected_customer.get('box_number', ''),
                'serial_number': self.selected_customer.get('serial_number', ''),
                'previous_reading': self.last_invoice_result.get('previous_reading', 0),
                'new_reading': self.last_invoice_result.get('new_reading', 0),
                'kilowatt_amount': self.last_invoice_result.get('kilowatt_amount', 0),
                'free_kilowatt': self.last_invoice_result.get('free_kilowatt', 0),
                'consumption': self.last_invoice_result.get('kilowatt_amount', 0) + self.last_invoice_result.get('free_kilowatt', 0),
                'price_per_kilo': 7200,
                'total_amount': self.last_invoice_result.get('total_amount', 0),
                'new_balance': self.last_invoice_result.get('new_balance', 0),
                'invoice_number': self.last_invoice_result.get('invoice_number', ''),
                'discount': self.last_invoice_result.get('discount', 0)
            }
            
            if self.printer.print_fast_invoice(invoice_data):
                self.show_result_message("🖨️ تمت الطباعة بنجاح!")
                messagebox.showinfo("نجاح", "تمت طباعة الفاتورة بنجاح")
            else:
                self.show_result_message("❌ فشل الطباعة. تحقق من اتصال الطابعة.")
                messagebox.showerror("خطأ", "فشل الطباعة. تحقق من اتصال الطابعة.")
                
        except Exception as e:
            logger.error(f"خطأ في الطباعة: {e}")
            messagebox.showerror("خطأ", f"فشل الطباعة: {str(e)}")
    
    def show_result_message(self, message):
        """عرض رسالة في منطقة النتائج"""
        self.result_text.config(state='normal')
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(1.0, message)
        self.result_text.config(state='disabled')
    
    def clear_input_fields(self):
        """تصفير حقول الإدخال فقط"""
        self.kilowatt_var.set("")
        self.free_var.set("0")
        self.price_var.set("7200")
        self.discount_var.set("0")
        
        if self.selected_customer:
            self.kilowatt_entry.focus_set()
    
    def clear_fields(self):
        """تصفير جميع الحقول"""
        self.search_var.set("")
        self.kilowatt_var.set("")
        self.free_var.set("0")
        self.price_var.set("7200")
        self.discount_var.set("0")
        
        for key in self.info_vars:
            self.info_vars[key].set("---")
        
        self.results_listbox.delete(0, tk.END)
        self.show_result_message("🔍 ابدأ بالبحث عن زبون باستخدام حقل البحث أعلاه...")
        
        self.selected_customer = None
        self.last_invoice_result = None
        
        self.process_btn.config(state='disabled', bg='#95a5a6')
        self.print_btn.config(state='disabled', bg='#95a5a6')
        
        self.search_entry.focus_set()