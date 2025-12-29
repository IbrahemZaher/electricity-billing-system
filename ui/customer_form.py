# ui/customer_form.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging

logger = logging.getLogger(__name__)

class CustomerForm:
    """نموذج إضافة وتعديل الزبون"""
    
    def __init__(self, parent, title, sectors, customer_data=None):
        self.parent = parent
        self.title = title
        self.sectors = sectors
        self.customer_data = customer_data
        self.result = None
        
        self.create_dialog()
        self.create_widgets()
        self.load_customer_data()
        
        self.dialog.grab_set()
        self.dialog.wait_window()
    
    def create_dialog(self):
        """إنشاء النافذة المنبثقة"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(self.title)
        self.dialog.geometry("500x650")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg='#f5f7fa')
        
        # مركزية النافذة
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'500x650+{x}+{y}')
        
        # ربط زر الإغلاق
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
    
    def create_widgets(self):
        """إنشاء عناصر النموذج"""
        # إطار العنوان
        title_frame = tk.Frame(self.dialog, bg='#3498db', height=70)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, text=self.title,
                              font=('Arial', 18, 'bold'),
                              bg='#3498db', fg='white')
        title_label.pack(expand=True)
        
        # إطار النموذج الرئيسي
        main_frame = tk.Frame(self.dialog, bg='#f5f7fa', padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # إنشاء الحقول
        self.create_fields(main_frame)
        
        # أزرار التحكم
        self.create_buttons(main_frame)
    
    def create_fields(self, parent):
        """إنشاء حقول الإدخال"""
        # إطار الحقول مع تمرير
        canvas = tk.Canvas(parent, bg='#f5f7fa', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        
        fields_frame = tk.Frame(canvas, bg='#f5f7fa')
        
        canvas.create_window((0, 0), window=fields_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # تحديث منطقة التمرير
        fields_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # تعريف الحقول
        fields = [
            ('sector', 'القطاع *', 'combobox', {'values': [s['name'] for s in self.sectors]}),
            ('name', 'اسم الزبون *', 'entry', {}),
            ('box_number', 'رقم العلبة', 'entry', {}),
            ('serial_number', 'المسلسل', 'entry', {}),
            ('phone_number', 'رقم الهاتف', 'entry', {}),
            ('current_balance', 'الرصيد الحالي', 'entry', {'default': '0'}),
            ('last_counter_reading', 'آخر قراءة عداد', 'entry', {'default': '0'}),
            ('visa_balance', 'رصيد التأشيرة', 'entry', {'default': '0'}),
            ('withdrawal_amount', 'سحب المشترك', 'entry', {'default': '0'}),
            ('notes', 'ملاحظات', 'textarea', {'height': 4})
        ]
        
        self.field_vars = {}
        
        for i, (field_name, label, field_type, options) in enumerate(fields):
            # تسمية الحقل
            lbl = tk.Label(fields_frame, text=label,
                          font=('Arial', 11, 'bold'),
                          bg='#f5f7fa', fg='#2c3e50',
                          anchor='e')
            lbl.grid(row=i, column=0, sticky='e', padx=5, pady=8)
            
            # حقل الإدخال
            if field_type == 'entry':
                var = tk.StringVar(value=options.get('default', ''))
                entry = ttk.Entry(fields_frame, textvariable=var,
                                 font=('Arial', 11))
                entry.grid(row=i, column=1, sticky='ew', padx=5, pady=8)
                self.field_vars[field_name] = var
                
            elif field_type == 'combobox':
                var = tk.StringVar()
                combo = ttk.Combobox(fields_frame, textvariable=var,
                                    font=('Arial', 11), state='readonly')
                combo['values'] = options.get('values', [])
                combo.grid(row=i, column=1, sticky='ew', padx=5, pady=8)
                self.field_vars[field_name] = var
                
            elif field_type == 'textarea':
                text_frame = tk.Frame(fields_frame, bg='white', relief='sunken', borderwidth=1)
                text_frame.grid(row=i, column=1, sticky='nsew', padx=5, pady=8)
                
                text_widget = tk.Text(text_frame, height=options.get('height', 3),
                                     font=('Arial', 11), wrap='word',
                                     bg='white', fg='#2c3e50')
                text_widget.pack(fill='both', expand=True)
                
                scrollbar_text = ttk.Scrollbar(text_frame, orient='vertical',
                                              command=text_widget.yview)
                scrollbar_text.pack(side='right', fill='y')
                text_widget.configure(yscrollcommand=scrollbar_text.set)
                
                self.field_vars[field_name] = text_widget
        
        # جعل العمود الثاني قابلاً للتوسع
        fields_frame.columnconfigure(1, weight=1)
        
        # تعبئة وإظهار
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def create_buttons(self, parent):
        """إنشاء أزرار التحكم"""
        buttons_frame = tk.Frame(parent, bg='#f5f7fa')
        buttons_frame.pack(fill='x', pady=20)
        
        # زر الحفظ
        save_btn = tk.Button(buttons_frame, text="💾 حفظ",
                           command=self.save,
                           bg='#27ae60', fg='white',
                           font=('Arial', 12, 'bold'),
                           padx=30, pady=10, cursor='hand2')
        save_btn.pack(side='right', padx=10)
        
        # زر الإلغاء
        cancel_btn = tk.Button(buttons_frame, text="❌ إلغاء",
                              command=self.cancel,
                              bg='#e74c3c', fg='white',
                              font=('Arial', 12),
                              padx=30, pady=10, cursor='hand2')
        cancel_btn.pack(side='left', padx=10)
    
    def load_customer_data(self):
        """تحميل بيانات الزبون في حالة التعديل"""
        if not self.customer_data:
            return
        
        # تعبئة الحقول ببيانات الزبون
        for field_name, widget in self.field_vars.items():
            value = self.customer_data.get(field_name, '')
            
            if isinstance(widget, tk.StringVar):
                widget.set(str(value))
            elif isinstance(widget, tk.Text):
                widget.delete('1.0', 'end')
                widget.insert('1.0', str(value))
    
    def validate(self):
        """التحقق من صحة البيانات"""
        # التحقق من الحقول المطلوبة
        if not self.field_vars['sector'].get():
            messagebox.showerror("خطأ", "الرجاء اختيار القطاع")
            return False
        
        if not self.field_vars['name'].get().strip():
            messagebox.showerror("خطأ", "اسم الزبون مطلوب")
            return False
        
        # التحقق من القيم الرقمية
        numeric_fields = ['current_balance', 'last_counter_reading', 
                         'visa_balance', 'withdrawal_amount']
        
        for field in numeric_fields:
            try:
                value = self.field_vars[field].get()
                if value:
                    float(value)
            except ValueError:
                messagebox.showerror("خطأ", f"القيمة في '{field}' يجب أن تكون رقمية")
                return False
        
        return True
    
    def save(self):
        """حفظ البيانات"""
        if not self.validate():
            return
        
        try:
            # الحصول على معرف القطاع
            sector_name = self.field_vars['sector'].get()
            sector_id = None
            
            for sector in self.sectors:
                if sector['name'] == sector_name:
                    sector_id = sector['id']
                    break
            
            if not sector_id:
                messagebox.showerror("خطأ", "القطاع المحدد غير صالح")
                return
            
            # تجميع البيانات
            self.result = {
                'sector_id': sector_id,
                'name': self.field_vars['name'].get().strip(),
                'box_number': self.field_vars['box_number'].get().strip(),
                'serial_number': self.field_vars['serial_number'].get().strip(),
                'phone_number': self.field_vars['phone_number'].get().strip(),
                'current_balance': float(self.field_vars['current_balance'].get() or 0),
                'last_counter_reading': float(self.field_vars['last_counter_reading'].get() or 0),
                'visa_balance': float(self.field_vars['visa_balance'].get() or 0),
                'withdrawal_amount': float(self.field_vars['withdrawal_amount'].get() or 0),
                'notes': self.field_vars['notes'].get('1.0', 'end-1c').strip()
            }
            
            self.dialog.destroy()
            
        except Exception as e:
            logger.error(f"خطأ في حفظ البيانات: {e}")
            messagebox.showerror("خطأ", f"فشل حفظ البيانات: {str(e)}")
    
    def cancel(self):
        """إلغاء العملية"""
        self.result = None
        self.dialog.destroy()