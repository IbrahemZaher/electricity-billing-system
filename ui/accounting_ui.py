"""
ui/accounting_ui.py - واجهة محاسبة متكاملة تعمل على الشاشة كاملة
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
from datetime import datetime
from modules.fast_operations import FastOperations
from modules.printing import FastPrinter

logger = logging.getLogger(__name__)

class AccountingUI(tk.Frame):
    """واجهة محاسبة محسنة وسريعة تعمل على الشاشة كاملة"""
    
    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.parent = parent
        self.user_data = user_data
        self.fast_ops = FastOperations()
        self.printer = FastPrinter()
        
        self.selected_customer = None
        self.sectors = []
        
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
        """إنشاء واجهة كاملة الشاشة"""
        # إزالة أي عناصر سابقة
        for widget in self.winfo_children():
            widget.destroy()
        
        # الإطار الرئيسي مع تمرير
        main_frame = tk.Frame(self, bg='#f5f7fa')
        main_frame.pack(fill='both', expand=True)
        
        # شريط الأدوات العلوي
        self.create_toolbar(main_frame)
        
                # إطار المحتوى القابل للتمرير
        canvas = tk.Canvas(main_frame, bg='#f5f7fa', highlightthickness=0)
        canvas.pack(fill='both', expand=True, padx=20, pady=10)

        scrollbar = tk.Scrollbar(main_frame, orient='vertical', command=canvas.yview)
        scrollbar.pack(side='right', fill='y')

        canvas.configure(yscrollcommand=scrollbar.set)

        content_frame = tk.Frame(canvas, bg='#f5f7fa')
        canvas.create_window((0, 0), window=content_frame, anchor='nw')

        def on_configure(event):
            canvas.configure(scrollregion=canvas.bbox('all'))

        content_frame.bind('<Configure>', on_configure)

        
        # ===================== قسم البحث السريع =====================
        search_section = tk.LabelFrame(content_frame, text="🔍 بحث سريع عن الزبائن", 
                                      font=('Arial', 14, 'bold'),
                                      bg='white', fg='#2c3e50',
                                      padx=15, pady=15, relief='groove')
        search_section.pack(fill='x', pady=(0, 10))
        
        # صف البحث
        search_row = tk.Frame(search_section, bg='white')
        search_row.pack(fill='x', pady=5)
        
        tk.Label(search_row, text="ابحث بالاسم أو العلبة:", 
                bg='white', font=('Arial', 12), fg='#34495e').pack(side='left', padx=5)
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_row, textvariable=self.search_var,
                                    font=('Arial', 14), width=50,
                                    bg='#ecf0f1', relief='solid')
        self.search_entry.pack(side='left', padx=5, fill='x', expand=True)
        self.search_entry.bind('<KeyRelease>', self.quick_search)
        
        # زر البحث
        search_btn = tk.Button(search_row, text="بحث", 
                              command=self.perform_search,
                              bg='#3498db', fg='white',
                              font=('Arial', 12, 'bold'),
                              padx=20, pady=5)
        search_btn.pack(side='left', padx=5)
        
        # نتائج البحث في إطار مع تمرير
        results_frame = tk.Frame(search_section, bg='white', height=200)
        results_frame.pack(fill='both', expand=True, pady=10)
        results_frame.pack_propagate(False)
        
        # شريط التمرير
        scrollbar = tk.Scrollbar(results_frame)
        scrollbar.pack(side='right', fill='y')
        
        # قائمة النتائج
        self.results_listbox = tk.Listbox(results_frame, 
                                         font=('Arial', 12),
                                         bg='white', fg='#2c3e50',
                                         selectbackground='#3498db',
                                         selectforeground='white',
                                         yscrollcommand=scrollbar.set,
                                         height=8)
        self.results_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.results_listbox.yview)
        self.results_listbox.bind('<<ListboxSelect>>', self.on_search_select)
        
        # ===================== قسم بيانات الزبون =====================
        info_section = tk.LabelFrame(content_frame, text="📋 بيانات الزبون المحدد", 
                                    font=('Arial', 14, 'bold'),
                                    bg='white', fg='#2c3e50',
                                    padx=15, pady=15, relief='groove')
        info_section.pack(fill='x', pady=(0, 10))
        
        # إطار بيانات الزبون مع تمرير
        info_frame = tk.Frame(info_section, bg='white')
        info_frame.pack(fill='both', expand=True)
        
        # إنشاء شبكة لعرض البيانات
        info_labels = [
            ("اسم الزبون:", "name"),
            ("القطاع:", "sector"),
            ("العلبة:", "box"),
            ("المسلسل:", "serial"),
            ("الرصيد الحالي:", "balance"),
            ("آخر قراءة عداد:", "reading"),
            ("رصيد التأشيرة:", "visa"),
            ("سحب المشترك:", "withdrawal")
        ]
        
        self.info_vars = {}
        for i, (label_text, key) in enumerate(info_labels):
            row = i // 2
            col = (i % 2) * 2
            
            tk.Label(info_frame, text=label_text, 
                    bg='white', font=('Arial', 11, 'bold'),
                    fg='#34495e').grid(row=row, column=col, 
                                      sticky='e', padx=5, pady=8)
            
            var = tk.StringVar(value="---")
            entry = tk.Entry(info_frame, textvariable=var,
                           font=('Arial', 11), state='readonly',
                           bg='#f8f9fa', fg='#2c3e50',
                           relief='solid', width=25)
            entry.grid(row=row, column=col+1, padx=5, pady=8, sticky='ew')
            self.info_vars[key] = var
        
        # جعل الأعمدة قابلة للتوسع
        info_frame.columnconfigure(1, weight=1)
        info_frame.columnconfigure(3, weight=1)
        
        # ===================== قسم المحاسبة السريعة =====================
        acc_section = tk.LabelFrame(content_frame, text="💰 إدخال بيانات الفاتورة", 
                                   font=('Arial', 14, 'bold'),
                                   bg='white', fg='#2c3e50',
                                   padx=15, pady=15, relief='groove')
        acc_section.pack(fill='x', pady=(0, 10))
        
        # شبكة لإدخال البيانات
        acc_frame = tk.Frame(acc_section, bg='white')
        acc_frame.pack(fill='both', expand=True)

        acc_frame.columnconfigure(0, weight=0)
        acc_frame.columnconfigure(1, weight=1)

        
        # حقل القراءة الجديدة
        tk.Label(acc_frame, text="القراءة الجديدة:", 
                bg='white', font=('Arial', 12),
                fg='#34495e').grid(row=0, column=0, sticky='e', padx=5, pady=12)
        
        reading_frame = tk.Frame(acc_frame, bg='white')
        reading_frame.grid(row=0, column=1, padx=5, pady=12, sticky='ew')
        
        self.reading_var = tk.StringVar()
        self.reading_entry = tk.Entry(reading_frame, textvariable=self.reading_var,
                                     font=('Arial', 12), width=15,
                                     bg='#ecf0f1', relief='solid')
        self.reading_entry.pack(side='left', padx=2)
        
        # أزرار التحكم في القراءة
        tk.Button(reading_frame, text="+100", 
                 command=lambda: self.adjust_reading(100),
                 bg='#3498db', fg='white',
                 font=('Arial', 10)).pack(side='left', padx=2)
        
        tk.Button(reading_frame, text="+10", 
                 command=lambda: self.adjust_reading(10),
                 bg='#3498db', fg='white',
                 font=('Arial', 10)).pack(side='left', padx=2)
        
        tk.Button(reading_frame, text="-10", 
                 command=lambda: self.adjust_reading(-10),
                 bg='#e74c3c', fg='white',
                 font=('Arial', 10)).pack(side='left', padx=2)
        
        # حقل التأشيرة
        tk.Label(acc_frame, text="تنزيل تأشيرة:", 
                bg='white', font=('Arial', 12),
                fg='#34495e').grid(row=1, column=0, sticky='e', padx=5, pady=12)
        
        self.visa_var = tk.StringVar()
        self.visa_entry = tk.Entry(acc_frame, textvariable=self.visa_var,
                                  font=('Arial', 12), width=20,
                                  bg='#ecf0f1', relief='solid')
        self.visa_entry.grid(row=1, column=1, padx=5, pady=12, sticky='w')
        
        # حقل الحسم
        tk.Label(acc_frame, text="الحسم:", 
                bg='white', font=('Arial', 12),
                fg='#34495e').grid(row=2, column=0, sticky='e', padx=5, pady=12)
        
        self.discount_var = tk.StringVar()
        self.discount_entry = tk.Entry(acc_frame, textvariable=self.discount_var,
                                      font=('Arial', 12), width=20,
                                      bg='#ecf0f1', relief='solid')
        self.discount_entry.grid(row=2, column=1, padx=5, pady=12, sticky='w')
        
        # جعل الأعمدة قابلة للتوسع
        acc_frame.columnconfigure(1, weight=1)
        
        # ===================== قسم أزرار التحكم =====================
        btn_section = tk.Frame(content_frame, bg='#f5f7fa')
        btn_section.pack(fill='x', pady=20)
        
        # أزرار كبيرة وواضحة
        btn_frame = tk.Frame(btn_section, bg='#f5f7fa')
        btn_frame.pack()
        
        # زر المعالجة السريعة
        self.process_btn = tk.Button(btn_frame, text="⚡ معالجة سريعة", 
                                   command=self.fast_process,
                                   bg='#27ae60', fg='white',
                                   font=('Arial', 14, 'bold'),
                                   padx=40, pady=15,
                                   state='disabled', cursor='hand2')
        self.process_btn.pack(side='left', padx=10)
        
        # زر الطباعة
        self.print_btn = tk.Button(btn_frame, text="🖨️ طباعة الفاتورة", 
                                 command=self.print_invoice,
                                 bg='#3498db', fg='white',
                                 font=('Arial', 14),
                                 padx=40, pady=15,
                                 state='disabled', cursor='hand2')
        self.print_btn.pack(side='left', padx=10)
        
        # زر التصفير
        clear_btn = tk.Button(btn_frame, text="🗑️ تصفير الحقول", 
                            command=self.clear_fields,
                            bg='#e74c3c', fg='white',
                            font=('Arial', 14),
                            padx=40, pady=15, cursor='hand2')
        clear_btn.pack(side='left', padx=10)
        
        # ===================== قسم النتائج =====================
        result_section = tk.LabelFrame(content_frame, text="📊 تفاصيل المعالجة", 
                                      font=('Arial', 14, 'bold'),
                                      bg='white', fg='#2c3e50',
                                      padx=15, pady=15, relief='groove')
        result_section.pack(fill='both', expand=True, pady=(0, 10))
        
        # منطقة النص للنتائج
        self.result_text = scrolledtext.ScrolledText(result_section,
                                                    height=10,
                                                    font=('Arial', 11),
                                                    bg='#f8f9fa',
                                                    fg='#2c3e50',
                                                    wrap='word')
        self.result_text.pack(fill='both', expand=True)
        self.result_text.config(state='disabled')
    
    def create_toolbar(self, parent):
        """إنشاء شريط الأدوات العلوي"""
        toolbar = tk.Frame(parent, bg='#2c3e50', height=60)
        toolbar.pack(fill='x', side='top')
        toolbar.pack_propagate(False)
        
        # العنوان
        title_label = tk.Label(toolbar, 
                              text="مولدة الريان - نظام المحاسبة السريعة",
                              font=('Arial', 18, 'bold'),
                              bg='#2c3e50', fg='white')
        title_label.pack(side='left', padx=20)
        
        # معلومات المستخدم
        user_info = tk.Label(toolbar,
                            text=f"المستخدم: {self.user_data.get('full_name', '')} | الدور: {self.user_data.get('role', '')}",
                            font=('Arial', 12),
                            bg='#2c3e50', fg='#ecf0f1')
        user_info.pack(side='right', padx=20)
    
    def center_window(self):
        root = self.parent.winfo_toplevel()

        root.update_idletasks()

        width = 1200
        height = 700

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

        root.geometry(f'{width}x{height}+{x}+{y}')

    def quick_search(self, event=None):
        """بحث فوري أثناء الكتابة"""
        search_term = self.search_var.get().strip()
        if len(search_term) < 2:
            self.results_listbox.delete(0, tk.END)
            return
        
        # إلغاء البحث السابق إذا كان هناك واحد
        if hasattr(self, '_search_job'):
            self.after_cancel(self._search_job)
        
        # جدولة بحث جديد بعد تأخير 300 مللي ثانية
        self._search_job = self.after(300, self._perform_search, search_term)
    
    def _perform_search(self, search_term):
        """تنفيذ البحث الفعلي"""
        if not search_term:
            return
        
        results = self.fast_ops.fast_search_customers(search_term, limit=30)
        self.results_listbox.delete(0, tk.END)
        
        # حفظ بيانات العملاء للوصول السريع
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
        if hasattr(self, 'search_results_data') and self.search_results_data:
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
            
            # تعبئة حقل القراءة الجديدة بالقراءة السابقة
            last_reading = customer_data.get('last_counter_reading', 0)
            self.reading_var.set(str(last_reading))
            
            # تفعيل الأزرار
            self.process_btn.config(state='normal', bg='#27ae60')
            self.print_btn.config(state='normal', bg='#3498db')
            
            # إظهار رسالة في منطقة النتائج
            self.show_result_message(f"✅ تم تحديد الزبون: {customer_data.get('name', '')}\nيمكنك الآن إدخال القراءة الجديدة وإجراء المحاسبة.")
            
        except Exception as e:
            logger.error(f"خطأ في تحديد الزبون: {e}")
            messagebox.showerror("خطأ", f"فشل تحميل بيانات الزبون: {str(e)}")
    
    def adjust_reading(self, amount):
        """ضبط القراءة بزيادة/نقصان"""
        try:
            current = float(self.reading_var.get() or 0)
            new_value = current + amount
            if new_value >= 0:
                self.reading_var.set(str(int(new_value)))
        except ValueError:
            self.reading_var.set("0")
    
    def fast_process(self):
        """معالجة فاتورة سريعة"""
        if not self.selected_customer:
            messagebox.showerror("خطأ", "يرجى اختيار زبون أولاً")
            return
        
        try:
            # التحقق من المدخلات
            if not self.reading_var.get().strip():
                messagebox.showerror("خطأ", "يرجى إدخال القراءة الجديدة")
                return
            
            new_reading = float(self.reading_var.get())
            visa_amount = float(self.visa_var.get() or 0)
            discount = float(self.discount_var.get() or 0)
            
            # التحقق من القراءة الجديدة
            last_reading = float(self.selected_customer.get('last_counter_reading', 0))
            if new_reading < last_reading:
                messagebox.showerror("خطأ", "القراءة الجديدة يجب أن تكون أكبر من أو تساوي القراءة السابقة")
                return
            
            # إظهار تأكيد
            confirm_msg = f"""
            هل أنت متأكد من معالجة الفاتورة؟
            
            الزبون: {self.selected_customer.get('name', '')}
            القراءة السابقة: {last_reading:,.0f}
            القراءة الجديدة: {new_reading:,.0f}
            الاستهلاك: {new_reading - last_reading:,.1f} كيلو
            """
            
            if not messagebox.askyesno("تأكيد المعالجة", confirm_msg):
                return
            
            # معالجة الفاتورة
            result = self.fast_ops.fast_process_invoice(
                customer_id=self.selected_customer['id'],
                new_reading=new_reading,
                visa_amount=visa_amount,
                discount=discount,
                user_id=self.user_data.get('id', 1)
            )
            
            if result.get('success'):
                # عرض النتيجة
                result_text = f"""
                ✅ تمت المعالجة بنجاح!
                
                تفاصيل الفاتورة:
                • رقم الفاتورة: {result.get('invoice_number', 'N/A')}
                • الزبون: {result.get('customer_name', 'N/A')}
                • القراءة السابقة: {result.get('previous_reading', 0):,.0f}
                • القراءة الجديدة: {result.get('new_reading', 0):,.0f}
                • الاستهلاك: {result.get('consumption', 0):,.1f} كيلو
                • المبلغ الإجمالي: {result.get('total_amount', 0):,.0f} ليرة سورية
                • الرصيد الجديد: {result.get('new_balance', 0):,.0f}
                • وقت المعالجة: {result.get('processed_at', 'N/A')}
                
                يمكنك الآن طباعة الفاتورة.
                """
                
                self.show_result_message(result_text)
                
                # حفظ نتيجة المعالجة للطباعة
                self.last_invoice_result = result
                
                # تحديث بيانات الزبون المعروضة
                self.selected_customer['current_balance'] = result['new_balance']
                self.selected_customer['last_counter_reading'] = new_reading
                self.info_vars['balance'].set(f"{result['new_balance']:,.0f}")
                self.info_vars['reading'].set(f"{new_reading:,.0f}")
                
                # سؤال عن الطباعة
                if messagebox.askyesno("طباعة", "هل تريد طباعة الفاتورة الآن؟"):
                    self.print_invoice()
                
                # تصفير حقول الإدخال
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
            # تحضير بيانات الطباعة
            invoice_data = {
                'customer_name': self.selected_customer.get('name', ''),
                'sector_name': self.selected_customer.get('sector_name', ''),
                'box_number': self.selected_customer.get('box_number', ''),
                'serial_number': self.selected_customer.get('serial_number', ''),
                'previous_reading': self.last_invoice_result.get('previous_reading', 0),
                'new_reading': self.last_invoice_result.get('new_reading', 0),
                'consumption': self.last_invoice_result.get('consumption', 0),
                'price_per_kilo': 7200,  # يمكن جلبها من الإعدادات
                'total_amount': self.last_invoice_result.get('total_amount', 0),
                'new_balance': self.last_invoice_result.get('new_balance', 0),
                'invoice_number': self.last_invoice_result.get('invoice_number', ''),
                'discount': 0
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
        self.visa_var.set("")
        self.discount_var.set("")
        if self.selected_customer:
            last_reading = self.selected_customer.get('last_counter_reading', 0)
            self.reading_var.set(str(last_reading))
    
    def clear_fields(self):
        """تصفير جميع الحقول"""
        self.search_var.set("")
        self.reading_var.set("")
        self.visa_var.set("")
        self.discount_var.set("")
        
        # تصفير حقول المعلومات
        for var in self.info_vars.values():
            var.set("---")
        
        # تصفير قائمة النتائج
        self.results_listbox.delete(0, tk.END)
        
        # تصفير منطقة النتائج
        self.show_result_message("🔍 ابدأ بالبحث عن زبون...")
        
        # إلغاء تحديد الزبون
        self.selected_customer = None
        
        # تعطيل الأزرار
        self.process_btn.config(state='disabled', bg='#95a5a6')
        self.print_btn.config(state='disabled', bg='#95a5a6')