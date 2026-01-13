# ui/customer_details.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class CustomerDetails:
    """عرض تفاصيل الزبون"""
    
    def __init__(self, parent, customer_data):
        self.parent = parent
        self.customer_data = customer_data
        
        self.create_dialog()
        self.create_widgets()
        
        self.dialog.grab_set()
    
    def create_dialog(self):
        """إنشاء النافذة المنبثقة"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"تفاصيل الزبون - {self.customer_data['name']}")
        self.dialog.geometry("700x600")
        self.dialog.resizable(True, True)
        self.dialog.configure(bg='#f5f7fa')
        
        # مركزية النافذة
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'700x600+{x}+{y}')
    
    def create_widgets(self):
        """إنشاء عناصر العرض"""
        # إطار العنوان
        title_frame = tk.Frame(self.dialog, bg='#9b59b6', height=80)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, 
                              text=f"تفاصيل الزبون: {self.customer_data['name']}",
                              font=('Arial', 18, 'bold'),
                              bg='#9b59b6', fg='white')
        title_label.pack(expand=True)
        
        # دفتر الملاحظات للتبويب
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # معلومات أساسية
        basic_tab = ttk.Frame(notebook)
        self.create_basic_info_tab(basic_tab)
        notebook.add(basic_tab, text='معلومات أساسية')
        
        # معلومات مالية
        financial_tab = ttk.Frame(notebook)
        self.create_financial_info_tab(financial_tab)
        notebook.add(financial_tab, text='معلومات مالية')
        
        # معلومات العداد
        counter_tab = ttk.Frame(notebook)
        self.create_counter_info_tab(counter_tab)
        notebook.add(counter_tab, text='معلومات العداد')
        
        # أزرار التحكم
        self.create_buttons()
    
    def create_basic_info_tab(self, parent):
        """إنشاء تبويب المعلومات الأساسية"""
        # إطار مع تمرير
        canvas = tk.Canvas(parent, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        content_frame = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # تحديث منطقة التمرير
        content_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # تعريف المعلومات الأساسية
        basic_info = [
            ('اسم الزبون', self.customer_data.get('name', '')),
            ('القطاع', self.customer_data.get('sector_name', 'غير محدد')),
            ('رقم العلبة', self.customer_data.get('box_number', '')),
            ('المسلسل', self.customer_data.get('serial_number', '')),
            ('رقم الهاتف', self.customer_data.get('phone_number', '')),
            ('حساب التيليغرام', self.customer_data.get('telegram_username', '')),
            ('الحالة', 'نشط' if self.customer_data.get('is_active', True) else 'غير نشط'),
            ('تاريخ التسجيل', self.format_date(self.customer_data.get('created_at'))),
            ('آخر تحديث', self.format_date(self.customer_data.get('updated_at')))
        ]
        
        # عرض المعلومات
        for i, (label, value) in enumerate(basic_info):
            # إطار السطر
            row_frame = tk.Frame(content_frame, bg='white')
            row_frame.pack(fill='x', padx=20, pady=10)
            
            # التسمية
            lbl = tk.Label(row_frame, text=label + ":",
                          font=('Arial', 11, 'bold'),
                          bg='white', fg='#2c3e50',
                          width=20, anchor='e')
            lbl.pack(side='left', padx=5)
            
            # القيمة
            val = tk.Label(row_frame, text=value or '---',
                          font=('Arial', 11),
                          bg='#f8f9fa', fg='#495057',
                          relief='ridge', anchor='w',
                          padx=10, pady=5)
            val.pack(side='left', fill='x', expand=True, padx=5)
        
        # الملاحظات
        notes_frame = tk.Frame(content_frame, bg='white')
        notes_frame.pack(fill='x', padx=20, pady=20)
        
        notes_label = tk.Label(notes_frame, text="ملاحظات:",
                              font=('Arial', 11, 'bold'),
                              bg='white', fg='#2c3e50')
        notes_label.pack(anchor='w', pady=(0, 5))
        
        notes_text = tk.Text(notes_frame, height=6,
                            font=('Arial', 11),
                            bg='#f8f9fa', fg='#495057',
                            wrap='word', state='disabled')
        notes_text.pack(fill='x', padx=5)
        
        notes = self.customer_data.get('notes', '')
        notes_text.config(state='normal')
        notes_text.insert('1.0', notes or 'لا توجد ملاحظات')
        notes_text.config(state='disabled')
        
        # تعبئة وإظهار
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def create_financial_info_tab(self, parent):
        """إنشاء تبويب المعلومات المالية"""
        canvas = tk.Canvas(parent, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        content_frame = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        content_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # المعلومات المالية
        balance = self.customer_data.get('current_balance', 0)
        balance_color = '#e74c3c' if balance < 0 else '#27ae60' if balance > 0 else '#7f8c8d'
        balance_status = 'سالب' if balance < 0 else 'موجب' if balance > 0 else 'صفر'
        
        financial_info = [
            ('الرصيد الحالي', f"{balance:,.0f} كيلو واط", balance_color),
            ('حالة الرصيد', balance_status, balance_color),
            ('رصيد التأشيرة', f"{self.customer_data.get('visa_balance', 0):,.0f}", '#3498db'),
            ('سحب المشترك', f"{self.customer_data.get('withdrawal_amount', 0):,.0f}", '#9b59b6')
        ]
        
        # عرض المعلومات
        for i, (label, value, color) in enumerate(financial_info):
            row_frame = tk.Frame(content_frame, bg='white')
            row_frame.pack(fill='x', padx=20, pady=15)
            
            lbl = tk.Label(row_frame, text=label + ":",
                          font=('Arial', 12, 'bold'),
                          bg='white', fg='#2c3e50',
                          width=20, anchor='e')
            lbl.pack(side='left', padx=5)
            
            val = tk.Label(row_frame, text=value,
                          font=('Arial', 12, 'bold'),
                          bg='#f8f9fa', fg=color,
                          relief='solid', anchor='center',
                          padx=20, pady=10)
            val.pack(side='left', fill='x', expand=True, padx=5)
        
        # رسالة إرشادية بناءً على الرصيد
        advice_frame = tk.Frame(content_frame, bg='white')
        advice_frame.pack(fill='x', padx=20, pady=30)
        
        if balance < 0:
            advice_text = "⚠️ هذا الزبون لديه رصيد سالب. يرجى متابعته للسداد."
            advice_color = '#e74c3c'
        elif balance > 100000:
            advice_text = "✓ رصيد ممتاز. يمكن منحه مزايا إضافية."
            advice_color = '#27ae60'
        else:
            advice_text = "✓ الرصيد ضمن المعدل الطبيعي."
            advice_color = '#3498db'
        
        advice_label = tk.Label(advice_frame, text=advice_text,
                               font=('Arial', 11, 'italic'),
                               bg='white', fg=advice_color,
                               wraplength=400)
        advice_label.pack()
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def create_counter_info_tab(self, parent):
        """إنشاء تبويب معلومات العداد"""
        canvas = tk.Canvas(parent, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        content_frame = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        content_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # معلومات العداد
        counter_info = [
            ('آخر قراءة عداد', f"{self.customer_data.get('last_counter_reading', 0):,.0f}"),
            ('متوسط الاستهلاك الشهري', 'تحت التطوير'),
            ('آخر فاتورة', 'تحت التطوير'),
            ('تاريخ آخر قراءة', 'تحت التطوير')
        ]
        
        for i, (label, value) in enumerate(counter_info):
            row_frame = tk.Frame(content_frame, bg='white')
            row_frame.pack(fill='x', padx=20, pady=15)
            
            lbl = tk.Label(row_frame, text=label + ":",
                          font=('Arial', 11, 'bold'),
                          bg='white', fg='#2c3e50',
                          width=25, anchor='e')
            lbl.pack(side='left', padx=5)
            
            val = tk.Label(row_frame, text=value,
                          font=('Arial', 11),
                          bg='#f8f9fa', fg='#495057',
                          relief='ridge', anchor='w',
                          padx=15, pady=8)
            val.pack(side='left', fill='x', expand=True, padx=5)
        
        # إحصائيات الفواتير (سيتم تطويرها لاحقاً)
        stats_frame = tk.Frame(content_frame, bg='white')
        stats_frame.pack(fill='x', padx=20, pady=30)
        
        stats_label = tk.Label(stats_frame, 
                              text="إحصائيات الفواتير قيد التطوير\nسيتم عرض تاريخ الفواتير واستهلاك الزبون",
                              font=('Arial', 11, 'italic'),
                              bg='white', fg='#7f8c8d',
                              wraplength=400)
        stats_label.pack()
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def create_buttons(self):
        """إنشاء أزرار التحكم"""
        buttons_frame = tk.Frame(self.dialog, bg='#f5f7fa')
        buttons_frame.pack(fill='x', pady=10, padx=20)
        
        # زر الطباعة (سيتم تطويره لاحقاً)
        print_btn = tk.Button(buttons_frame, text="🖨️ طباعة التقرير",
                             bg='#3498db', fg='white',
                             font=('Arial', 11),
                             padx=20, pady=8, cursor='hand2')
        print_btn.pack(side='right', padx=5)
        
        # زر الإغلاق
        close_btn = tk.Button(buttons_frame, text="إغلاق",
                             command=self.dialog.destroy,
                             bg='#95a5a6', fg='white',
                             font=('Arial', 11),
                             padx=30, pady=8, cursor='hand2')
        close_btn.pack(side='left', padx=5)
    
    def format_date(self, date_value):
        """تنسيق التاريخ"""
        if not date_value:
            return 'غير محدد'
        
        try:
            if isinstance(date_value, str):
                return date_value
            
            if hasattr(date_value, 'strftime'):
                return date_value.strftime("%Y-%m-%d %H:%M")
        except:
            pass
        
        return str(date_value)