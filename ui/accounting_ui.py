# ui/accounting_ui.py - واجهة محاسبة متكاملة بتصميم ناعم جداً (ألوان باستيل هادئة)
# تم التحديث: تخفيف إضاءة البطاقات الثلاث (بحث، ملف مشترك، دفعة جديدة)

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
from datetime import datetime
from modules.fast_operations import FastOperations
from modules.printing import FastPrinter

logger = logging.getLogger(__name__)

class AccountingUI(tk.Frame):
    """واجهة محاسبة بتصميم ناعم وألوان باستيل هادئة مع توزيع مثالي للمعلومات"""
    
    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.parent = parent
        self.user_data = user_data
        self.fast_ops = FastOperations()
        self.printer = FastPrinter()
        
        # ألوان باستيل ناعمة جداً ومريحة
        self.colors = {
            'bg_main': '#FFF0F5',          # خلفية رئيسية وردي فاتح جداً
            'primary': '#D4A5A5',           # وردي باستيل
            'secondary': '#A8D5BA',         # نعناعي فاتح
            'accent': '#FADADD',            # وردي فاتح جداً
            'text_dark': '#4A4A4A',         # رمادي داكن للنص
            'white': '#FFFFFF',              # أبيض ناصع (للنصوص فقط)
            'card_bg': '#FDF5F5',            # خلفية البطاقات (أبيض وردي ناعم)
            'danger': '#F8C7CC',             # وردي فاتح
            'success': '#A8D5BA',            # نعناعي
            'info': '#C5CAE9',                # خزامي فاتح
            'warning': '#FFF2CC',             # أصفر باستيل
            'terminal_bg': '#FCE4E6',         # وردي فاتح جداً للطرفية
            'terminal_fg': '#4A4A4A',         # نص داكن للطرفية
            'border_light': '#E6B0B0'         # لون الحدود الناعم
        }
        
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
        """إنشاء واجهة محاسبة بتصميم ناعم جداً"""
        # إزالة أي عناصر سابقة
        for widget in self.winfo_children():
            widget.destroy()
        
        # الحاوية الرئيسية
        self.main_container = tk.Frame(self, bg=self.colors['bg_main'])
        self.main_container.pack(fill='both', expand=True)
        
        # 1. شريط العنوان
        self.header = tk.Frame(self.main_container, bg=self.colors['primary'], height=70)
        self.header.pack(fill='x', side='top')
        self.header.pack_propagate(False)
        
        # زر العودة
        btn_close = tk.Button(self.header, text="✕", command=self.close_window,
                            bg=self.colors['danger'], fg=self.colors['text_dark'], 
                            font=('Segoe UI', 12, 'bold'),
                            bd=0, cursor='hand2', width=4, activebackground='#E6B0B0',
                            relief='flat')
        btn_close.pack(side='left', padx=20, pady=15)
        
        title_frame = tk.Frame(self.header, bg=self.colors['primary'])
        title_frame.pack(side='left', padx=10)
        
        tk.Label(title_frame, text="مولدة الريان الذكية", font=('Segoe UI', 20, 'bold'),
                 bg=self.colors['primary'], fg='#FFFFFF').pack(anchor='w')
        tk.Label(title_frame, text="نظام الإدارة المالية المتكامل", font=('Segoe UI', 9),
                 bg=self.colors['primary'], fg='#F5F5F5').pack(anchor='w')
        
        # معلومات المستخدم
        user_frame = tk.Frame(self.header, bg=self.colors['primary'])
        user_frame.pack(side='right', padx=20)
        
        user_role = self.user_data.get('role', '')
        user_name = self.user_data.get('full_name', '')
        tk.Label(user_frame, text=f"👤 {user_name}", 
                 font=('Segoe UI', 11, 'bold'), bg=self.colors['primary'], fg='white').pack(anchor='e')
        tk.Label(user_frame, text=f"الدور: {user_role}", 
                 font=('Segoe UI', 9), bg=self.colors['primary'], fg='#F5F5F5').pack(anchor='e')
        
        # 2. منطقة العمل الرئيسية
        self.work_area = tk.Frame(self.main_container, bg=self.colors['bg_main'])
        self.work_area.pack(fill='both', expand=True, padx=25, pady=20)
        
        # --- العمود الأيسر (البحث والمعلومات) ---
        left_column = tk.Frame(self.work_area, bg=self.colors['bg_main'], width=500)
        left_column.pack(side='left', fill='both', expand=True, padx=(0, 15))
        
        # بطاقة البحث (خلفية ناعمة)
        search_card = tk.Frame(left_column, bg=self.colors['card_bg'], bd=0)
        search_card.pack(fill='x', pady=(0, 15))
        self.add_shadow(search_card)
        
        tk.Label(search_card, text="🔍 ابحث عن المشترك", font=('Segoe UI', 13, 'bold'),
                 bg=self.colors['card_bg'], fg=self.colors['primary']).pack(anchor='e', padx=15, pady=(10, 5))
        
        search_inner = tk.Frame(search_card, bg=self.colors['card_bg'])
        search_inner.pack(fill='x', padx=15, pady=(0, 15))
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_inner, textvariable=self.search_var,
                                   font=('Segoe UI', 13), bg='#F8F9FA', fg=self.colors['text_dark'],
                                   relief='flat', insertbackground=self.colors['primary'])
        self.search_entry.pack(side='right', fill='x', expand=True, ipady=8)
        self.search_entry.bind('<KeyRelease>', self.quick_search)
        self.search_entry.focus_set()
        
        # قائمة النتائج
        results_frame = tk.Frame(search_card, bg=self.colors['card_bg'])
        results_frame.pack(fill='x', padx=15, pady=(0, 15))
        
        scrollbar_results = tk.Scrollbar(results_frame, orient='vertical', bg=self.colors['accent'])
        scrollbar_results.pack(side='right', fill='y')
        
        self.results_listbox = tk.Listbox(results_frame, font=('Segoe UI', 11),
                                        bg='#FDFDFD', fg=self.colors['text_dark'],
                                        selectbackground=self.colors['primary'],
                                        selectforeground='white',
                                        yscrollcommand=scrollbar_results.set,
                                        height=4, relief='flat', bd=0,
                                        highlightthickness=1, highlightcolor=self.colors['primary'])
        self.results_listbox.pack(side='left', fill='both', expand=True)
        scrollbar_results.config(command=self.results_listbox.yview)
        self.results_listbox.bind('<<ListboxSelect>>', self.on_search_select)
        
        # بطاقة معلومات الزبون (خلفية ناعمة)
        self.info_card = tk.Frame(left_column, bg=self.colors['card_bg'])
        self.info_card.pack(fill='both', expand=True)
        self.add_shadow(self.info_card)
        
        tk.Label(self.info_card, text="📋 ملف المشترك", font=('Segoe UI', 13, 'bold'),
                 bg=self.colors['card_bg'], fg=self.colors['primary']).pack(anchor='e', padx=15, pady=10)
        
        info_grid = tk.Frame(self.info_card, bg=self.colors['card_bg'])
        info_grid.pack(fill='both', padx=15, pady=(0, 15))
        
        # حقول المعلومات
        right_column_labels = [
            ("الاسم الكامل", "name"),
            ("القطاع", "sector"),
            ("رقم العلبة", "box"),
            ("المسلسل", "serial")
        ]
        
        left_column_labels = [
            ("آخر قراءة", "reading"),
            ("الرصيد الحالي (ك.واط)", "balance"),
            ("التأشيرة (ك.واط)", "visa"),
            ("السحب (ك.واط)", "withdrawal")
        ]
        
        self.info_vars = {}
        
        right_frame = tk.Frame(info_grid, bg=self.colors['card_bg'])
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        left_frame = tk.Frame(info_grid, bg=self.colors['card_bg'])
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        # تعبئة العمود الأيمن
        for label_text, key in right_column_labels:
            f = tk.Frame(right_frame, bg=self.colors['card_bg'])
            f.pack(fill='x', pady=6)
            
            tk.Label(f, text=label_text, font=('Segoe UI', 10), 
                     bg=self.colors['card_bg'], fg='#7F8C8D', anchor='e').pack(fill='x')
            var = tk.StringVar(value="---")
            tk.Label(f, textvariable=var, font=('Segoe UI', 12, 'bold'), 
                     bg=self.colors['card_bg'], fg=self.colors['text_dark'], anchor='e').pack(fill='x')
            self.info_vars[key] = var
        
        # تعبئة العمود الأيسر
        for label_text, key in left_column_labels:
            f = tk.Frame(left_frame, bg=self.colors['card_bg'])
            f.pack(fill='x', pady=6)
            
            tk.Label(f, text=label_text, font=('Segoe UI', 10), 
                     bg=self.colors['card_bg'], fg='#7F8C8D', anchor='e').pack(fill='x')
            var = tk.StringVar(value="---")
            tk.Label(f, textvariable=var, font=('Segoe UI', 12, 'bold'), 
                     bg=self.colors['card_bg'], fg=self.colors['text_dark'], anchor='e').pack(fill='x')
            self.info_vars[key] = var
        
        # --- العمود الأيمن (الإدخال والمعالجة) ---
        right_column = tk.Frame(self.work_area, bg=self.colors['bg_main'], width=500)
        right_column.pack(side='right', fill='both', expand=True, padx=(15, 0))
        
        # بطاقة الإدخال المالي (خلفية ناعمة)
        input_card = tk.Frame(right_column, bg=self.colors['card_bg'])
        input_card.pack(fill='x', pady=(0, 15))
        self.add_shadow(input_card)
        
        tk.Label(input_card, text="💰 تفاصيل الدفعة الجديدة", font=('Segoe UI', 13, 'bold'),
                 bg=self.colors['card_bg'], fg=self.colors['secondary']).pack(anchor='e', padx=15, pady=10)
        
        entry_form = tk.Frame(input_card, bg=self.colors['card_bg'])
        entry_form.pack(fill='x', padx=20, pady=10)
        
        # كمية الدفع
        tk.Label(entry_form, text="كمية الدفع (ك.واط):", font=('Segoe UI', 11), 
                 bg=self.colors['card_bg'], fg=self.colors['secondary']).grid(row=0, column=2, sticky='e', pady=5)
        self.kilowatt_var = tk.StringVar()
        self.kilowatt_entry = tk.Entry(entry_form, textvariable=self.kilowatt_var, 
                                      font=('Segoe UI', 18, 'bold'), 
                                      width=10, bg='#E8F5E9', relief='flat', justify='center',
                                      highlightthickness=1, highlightcolor=self.colors['secondary'])
        self.kilowatt_entry.grid(row=0, column=1, padx=10)
        
        # أزرار التعديل
        btns_quick = tk.Frame(entry_form, bg=self.colors['card_bg'])
        btns_quick.grid(row=0, column=0)
        self.create_flat_btn(btns_quick, "+100", lambda: self.adjust_kilowatt(100), self.colors['secondary']).pack(side='left', padx=2)
        self.create_flat_btn(btns_quick, "+10", lambda: self.adjust_kilowatt(10), self.colors['secondary']).pack(side='left', padx=2)
        self.create_flat_btn(btns_quick, "-10", lambda: self.adjust_kilowatt(-10), self.colors['danger']).pack(side='left', padx=2)
        
        # المجاني
        tk.Label(entry_form, text="المجاني (ك.واط):", font=('Segoe UI', 10), 
                 bg=self.colors['card_bg'], fg=self.colors['text_dark']).grid(row=1, column=2, sticky='e', pady=10)
        self.free_var = tk.StringVar(value="0")
        tk.Entry(entry_form, textvariable=self.free_var, font=('Segoe UI', 11), 
                 bg='#F8F9FA', relief='flat', width=15, justify='center').grid(row=1, column=1, pady=10)
        
        # سعر الكيلو
        tk.Label(entry_form, text="سعر الكيلو (ل.س):", font=('Segoe UI', 10), 
                 bg=self.colors['card_bg'], fg=self.colors['text_dark']).grid(row=2, column=2, sticky='e', pady=10)
        self.price_var = tk.StringVar(value="7200")
        tk.Entry(entry_form, textvariable=self.price_var, font=('Segoe UI', 11), 
                 bg='#F8F9FA', relief='flat', width=15, justify='center').grid(row=2, column=1, pady=10)
        
        # الحسم
        tk.Label(entry_form, text="الحسم (ل.س):", font=('Segoe UI', 10), 
                 bg=self.colors['card_bg'], fg=self.colors['text_dark']).grid(row=3, column=2, sticky='e', pady=10)
        self.discount_var = tk.StringVar(value="0")
        tk.Entry(entry_form, textvariable=self.discount_var, font=('Segoe UI', 11), 
                 bg='#F8F9FA', relief='flat', width=15, justify='center').grid(row=3, column=1, pady=10)
        
        # الأزرار
        action_frame = tk.Frame(right_column, bg=self.colors['bg_main'])
        action_frame.pack(fill='x', pady=10)
        
        btn_row = tk.Frame(action_frame, bg=self.colors['bg_main'])
        btn_row.pack(fill='x')
        
        self.process_btn = self.create_action_btn(btn_row, "⚡ معالجة سريعة", self.fast_process, self.colors['secondary'])
        self.process_btn.pack(side='left', fill='both', expand=True, padx=5)
        
        self.print_btn = self.create_action_btn(btn_row, "🖨️ طباعة", self.print_invoice, self.colors['primary'])
        self.print_btn.pack(side='left', fill='both', expand=True, padx=5)
        
        btn_row2 = tk.Frame(action_frame, bg=self.colors['bg_main'])
        btn_row2.pack(fill='x', pady=(5, 0))
        
        preview_btn = self.create_action_btn(btn_row, "🧮 معاينة", self.calculate_preview, self.colors['info'])
        preview_btn.pack(side='left', fill='both', expand=True, padx=5)
        
        clear_btn = self.create_action_btn(btn_row, "🗑️ تصفير", self.clear_fields, self.colors['warning'])
        clear_btn.pack(side='left', fill='both', expand=True, padx=5)
        
        # منطقة النتائج
        result_card = tk.Frame(right_column, bg=self.colors['terminal_bg'])
        result_card.pack(fill='both', expand=True, pady=10)
        self.add_shadow(result_card, color=self.colors['border_light'])
        
        self.result_text = scrolledtext.ScrolledText(result_card, font=('Consolas', 10), 
                                                   bg=self.colors['terminal_bg'], fg=self.colors['terminal_fg'], 
                                                   bd=0, padx=10, pady=10,
                                                   highlightthickness=1, highlightbackground=self.colors['border_light'],
                                                   insertbackground=self.colors['primary'])
        self.result_text.pack(fill='both', expand=True)
        self.result_text.config(state='disabled')
        
        self.show_result_message("🔍 جهاز الاستقبال جاهز... بانتظار اختيار زبون")
    
    def create_flat_btn(self, parent, text, command, color):
        """إنشاء زر مسطح مع تأثير hover"""
        btn = tk.Button(parent, text=text, command=command, bg=color, fg=self.colors['text_dark'],
                        font=('Segoe UI', 9, 'bold'), relief='flat', padx=10, cursor='hand2')
        btn.bind("<Enter>", lambda e: btn.config(bg=self.lighten_color(color)))
        btn.bind("<Leave>", lambda e: btn.config(bg=color))
        return btn
    
    def create_action_btn(self, parent, text, command, color):
        """إنشاء زر إجراء كبير مع تأثير hover"""
        btn = tk.Button(parent, text=text, command=command, bg=color, fg=self.colors['text_dark'],
                        font=('Segoe UI', 11, 'bold'), relief='flat', pady=10, cursor='hand2',
                        activebackground=self.lighten_color(color), activeforeground=self.colors['text_dark'])
        btn.bind("<Enter>", lambda e: btn.config(bg=self.lighten_color(color)))
        btn.bind("<Leave>", lambda e: btn.config(bg=color))
        return btn
    
    def add_shadow(self, widget, color=None):
        """إضافة تأثير ظل خفيف للبطاقة"""
        if color is None:
            color = self.colors['border_light']
        widget.config(highlightbackground=color, highlightthickness=1)
    
    def lighten_color(self, hex_color):
        """تفتيح اللون بنسبة 20% (تقريب بسيط)"""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, int(r * 1.2))
        g = min(255, int(g * 1.2))
        b = min(255, int(b * 1.2))
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def close_window(self):
        """إغلاق النافذة المنبثقة"""
        self.parent.destroy()
    
    def center_window(self):
        """توسيط النافذة على الشاشة"""
        root = self.parent.winfo_toplevel()
        root.update_idletasks()
        width, height = 1300, 800
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')
        root.minsize(1200, 700)
    
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
            display_text = f"👤 {customer['name']} | علبة: {customer['box_number']} | رصيد: {customer['current_balance']:,.0f}"
            self.results_listbox.insert(tk.END, display_text)
    
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
        """تحديد زبون وعرض بياناته بالتوزيع الجديد"""
        try:
            customer_data = self.fast_ops.fast_get_customer_details(customer_id)
            if not customer_data:
                messagebox.showwarning("تحذير", "لم يتم العثور على بيانات الزبون")
                return
            self.selected_customer = customer_data
            self.info_vars['name'].set(customer_data.get('name', '---'))
            self.info_vars['sector'].set(customer_data.get('sector_name', '---'))
            self.info_vars['box'].set(customer_data.get('box_number', '---'))
            self.info_vars['serial'].set(customer_data.get('serial_number', '---'))
            self.info_vars['reading'].set(f"{customer_data.get('last_counter_reading', 0):,.0f}")
            self.info_vars['balance'].set(f"{customer_data.get('current_balance', 0):,.0f} ك.واط")
            self.info_vars['visa'].set(f"{customer_data.get('visa_balance', 0):,.0f}")
            self.info_vars['withdrawal'].set(f"{customer_data.get('withdrawal_amount', 0):,.0f}")
            self.kilowatt_var.set("")
            self.free_var.set("0")
            self.price_var.set("7200")
            self.discount_var.set("0")
            self.process_btn.config(state='normal', bg=self.colors['secondary'])
            self.print_btn.config(state='normal', bg=self.colors['primary'])
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
                user_id=self.user_data.get('id', 1),
                customer_withdrawal=self.selected_customer.get('withdrawal_amount', 0),   
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
                self.selected_customer['current_balance'] = result['new_balance']
                self.selected_customer['last_counter_reading'] = result['new_reading']
                self.info_vars['balance'].set(f"{result['new_balance']:,.0f} ك.واط")
                self.info_vars['reading'].set(f"{result['new_reading']:,.0f}")
                if messagebox.askyesno("طباعة", "هل تريد طباعة الفاتورة الآن؟"):
                    self.print_invoice()
                self.clear_input_fields()
            else:
                error_msg = result.get('error', 'حدث خطأ غير معروف')
                self.show_result_message(f"❌ فشل المعالجة:\n{error_msg}")
                messagebox.showerror("خطأ", f"فشل المعالجة: {error_msg}")
        except ValueError:
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
                'price_per_kilo': self.last_invoice_result.get('price_per_kilo', 7200),   # من النتيجة
                'total_amount': self.last_invoice_result.get('total_amount', 0),
                'new_balance': self.last_invoice_result.get('new_balance', 0),
                'invoice_number': self.last_invoice_result.get('invoice_number', ''),
                'discount': self.last_invoice_result.get('discount', 0),
                'withdrawal_amount': self.selected_customer.get('withdrawal_amount', 0),
                'visa_application': self.selected_customer.get('visa_balance', 0)   # <-- إضافة هذا السطر
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
        """عرض رسالة في منطقة النتائج بتنسيق جميل"""
        self.result_text.config(state='normal')
        self.result_text.delete(1.0, tk.END)
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.result_text.insert(tk.END, f"> [{timestamp}] {message}")
        self.result_text.config(state='disabled')
        self.result_text.see(tk.END)
    
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
        self.process_btn.config(state='disabled', bg='#D4A5A5')
        self.print_btn.config(state='disabled', bg='#D4A5A5')
        self.search_entry.focus_set()