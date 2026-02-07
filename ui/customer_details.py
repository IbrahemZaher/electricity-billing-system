# ui/customer_details.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class CustomerDetails:
    """عرض تفاصيل الزبون مع دعم العدادات الهرمية"""
    
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
        self.dialog.geometry("750x650")
        self.dialog.resizable(True, True)
        self.dialog.configure(bg='#f5f7fa')
        
        # مركزية النافذة
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'750x650+{x}+{y}')
    
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
        
        # معلومات العلاقات الهرمية
        hierarchy_tab = ttk.Frame(notebook)
        self.create_hierarchy_info_tab(hierarchy_tab)
        notebook.add(hierarchy_tab, text='العلاقات الهرمية')

        # معلومات التصنيف المالي
        financial_tab = ttk.Frame(notebook)
        self.create_financial_info_tab(financial_tab)
        notebook.add(financial_tab, text='التصنيف المالي')
        
        # أزرار التحكم
        self.create_buttons()
    
    def create_basic_info_tab(self, parent):
        """إنشاء تبويب المعلومات الأساسية مع الحقول الجديدة"""
        # إطار مع تمرير
        canvas = tk.Canvas(parent, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        content_frame = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # تحديث منطقة التمرير
        content_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # عرض العلبة الأم - طريقة مبسطة
        if self.customer_data.get('parent_display'):
            parent_display = self.customer_data.get('parent_display')
        else:
            parent_name = self.customer_data.get('parent_name', '')
            parent_box = self.customer_data.get('parent_box_number', '')
            parent_type = self.customer_data.get('parent_meter_type', '')
            
            # بناء عرض العلبة الأم بنفس الطريقة للجميع
            if parent_box and parent_type and parent_name:
                parent_display = f"{parent_box} ({parent_type}) - {parent_name}"
            elif parent_box and parent_name:
                parent_display = f"{parent_box} - {parent_name}"
            elif parent_name and parent_type:
                parent_display = f"{parent_name} ({parent_type})"
            elif parent_name:
                parent_display = parent_name
            elif parent_box and parent_type:
                parent_display = f"{parent_box} ({parent_type})"
            elif parent_box:
                parent_display = f"علبة {parent_box}"
            else:
                parent_display = 'لا يوجد'
        
        # تعريف المعلومات الأساسية
        meter_type = self.customer_data.get('meter_type', 'زبون')
        
        basic_info = [
            ('اسم الزبون', self.customer_data.get('name', '')),
            ('نوع العداد', meter_type),
            ('العلبة الأم', parent_display),
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
            
            # تحديد لون القيمة بناءً على نوع العداد
            if label == 'نوع العداد':
                color = self.get_meter_type_color(value)
                val = tk.Label(row_frame, text=value or '---',
                            font=('Arial', 11, 'bold'),
                            bg='#f8f9fa', fg=color,
                            relief='ridge', anchor='w',
                            padx=10, pady=5)
            elif label == 'العلبة الأم' and parent_display != 'لا يوجد':
                # إضافة لون مميز للعلبة الأم إذا كانت موجودة
                val = tk.Label(row_frame, text=value or '---',
                            font=('Arial', 11, 'italic'),
                            bg='#f0f8ff', fg='#0066cc',
                            relief='ridge', anchor='w',
                            padx=10, pady=5)
            else:
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
    
    def get_meter_type_color(self, meter_type):
        """الحصول على لون يمثل نوع العداد"""
        colors = {
            'مولدة': '#8e44ad',      # بنفسجي
            'علبة توزيع': '#3498db',  # أزرق
            'رئيسية': '#2ecc71',      # أخضر
            'زبون': '#e74c3c'         # أحمر
        }
        return colors.get(meter_type, '#495057')
    
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
        
        meter_type = self.customer_data.get('meter_type', 'زبون')
        if meter_type == 'مولدة':
            advice_text = "⚡ مولدة رئيسية - عداد توزيع عام"
            advice_color = '#8e44ad'
        elif meter_type == 'علبة توزيع':
            advice_text = "🔌 علبة توزيع - متوسطة المدى"
            advice_color = '#3498db'
        elif meter_type == 'رئيسية':
            advice_text = "🏠 عداد رئيسي - تغذية مبنى"
            advice_color = '#2ecc71'
        else:
            advice_text = "👤 عداد زبون - استهلاك نهائي"
            advice_color = '#e74c3c'
        
        meter_type_label = tk.Label(advice_frame, text=advice_text,
                               font=('Arial', 12, 'bold'),
                               bg='white', fg=advice_color,
                               wraplength=400)
        meter_type_label.pack(pady=(0, 10))
        
        # نصائح إضافية بناءً على نوع العداد والرصيد
        if meter_type in ['مولدة', 'علبة توزيع', 'رئيسية'] and balance < 0:
            extra_advice = f"⚠️ تنبيه: {meter_type} لديه رصيد سالب. قد يؤثر على العدادات التابعة له."
            extra_color = '#e74c3c'
        elif balance > 100000:
            extra_advice = "✓ رصيد ممتاز. يمكن منحه مزايا إضافية."
            extra_color = '#27ae60'
        else:
            extra_advice = "✓ الرصيد ضمن المعدل الطبيعي."
            extra_color = '#3498db'
        
        extra_label = tk.Label(advice_frame, text=extra_advice,
                               font=('Arial', 11, 'italic'),
                               bg='white', fg=extra_color,
                               wraplength=400)
        extra_label.pack()
        
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
    
    def create_hierarchy_info_tab(self, parent):
        """إنشاء تبويب العلاقات الهرمية"""
        canvas = tk.Canvas(parent, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        content_frame = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        content_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # عنوان التبويب
        title_frame = tk.Frame(content_frame, bg='white')
        title_frame.pack(fill='x', padx=20, pady=20)
        
        title_label = tk.Label(title_frame, 
                            text="العلاقات الهرمية للعداد",
                            font=('Arial', 14, 'bold'),
                            bg='white', fg='#2c3e50')
        title_label.pack()
        
        # معلومات العلاقات
        meter_type = self.customer_data.get('meter_type', 'زبون')
        parent_info = self.customer_data.get('parent_name', '')
        parent_box = self.customer_data.get('parent_box_number', '')
        
        hierarchy_info = [
            ('المستوى الهرمي', self.get_hierarchy_level(meter_type)),
            ('العلبة الأم', f"{parent_box} - {parent_info}" if parent_info else 'لا يوجد'),
            ('نوع العلبة الأم', self.customer_data.get('parent_meter_type', '')),
            ('القطاع', self.customer_data.get('sector_name', 'غير محدد'))
        ]
        
        for i, (label, value) in enumerate(hierarchy_info):
            row_frame = tk.Frame(content_frame, bg='white')
            row_frame.pack(fill='x', padx=20, pady=12)
            
            lbl = tk.Label(row_frame, text=label + ":",
                        font=('Arial', 11, 'bold'),
                        bg='white', fg='#2c3e50',
                        width=20, anchor='e')
            lbl.pack(side='left', padx=5)
            
            val = tk.Label(row_frame, text=value or '---',
                        font=('Arial', 11),
                        bg='#f8f9fa', fg='#495057',
                        relief='ridge', anchor='w',
                        padx=15, pady=8)
            val.pack(side='left', fill='x', expand=True, padx=5)
        
        # رسم توضيحي للهرمية
        diagram_frame = tk.Frame(content_frame, bg='white')
        diagram_frame.pack(fill='x', padx=20, pady=30)
        
        diagram_label = tk.Label(diagram_frame, 
                            text="⬇️ هيكل العلاقات الهرمية ⬇️",
                            font=('Arial', 12, 'bold'),
                            bg='white', fg='#2c3e50')
        diagram_label.pack(pady=(0, 20))
        
        # رسم هرمي مرن
        levels = {
            'مولدة': '⚡ [مولدة رئيسية] - المستوى الأعلى',
            'علبة توزيع': '🔌 [علبة توزيع] - مستوى متوسط',
            'رئيسية': '🏠 [عداد رئيسي] - مستوى المبنى',
            'زبون': '👤 [عداد زبون] - مستوى المستهلك'
        }
        
        # معلومات العلاقات
        meter_type = self.customer_data.get('meter_type', 'زبون')
        parent_type = self.customer_data.get('parent_meter_type', '')
        parent_name = self.customer_data.get('parent_name', '')
        parent_box = self.customer_data.get('parent_box_number', '')
        
        # عرض العلاقة الحالية
        current_relation = f"📊 العلاقة الحالية: {levels.get(meter_type, 'نوع غير معروف')}"
        
        if parent_type and parent_name:
            current_relation += f"\n⬆️ متصل بـ: {parent_box} ({parent_type}) - {parent_name}"
        elif meter_type != 'مولدة':
            current_relation += "\n⚠️ غير متصل بأي علبة أم"
        
        # إضافة مربع نص للعلاقة
        relation_label = tk.Label(diagram_frame, 
                                text=current_relation,
                                font=('Arial', 11, 'bold'),
                                bg='white', fg='#2c3e50',
                                justify='left',
                                wraplength=400)
        relation_label.pack(pady=10)
        
        # شرح العلاقات المسموحة
        allowed_relations_text = """
        📋 العلاقات المسموحة في النظام:
        
        ⚡ مولدة ← 🔌 علبة توزيع
        ⚡ مولدة ← 🏠 عداد رئيسي
        ⚡ مولدة ← 👤 زبون مباشر
        
        🔌 علبة توزيع ← 🏠 عداد رئيسي
        🔌 علبة توزيع ← 👤 زبون مباشر
        
        🏠 عداد رئيسي ← 👤 زبون فقط
        """
        
        allowed_label = tk.Label(diagram_frame,
                            text=allowed_relations_text,
                            font=('Arial', 10),
                            bg='white', fg='#7f8c8d',
                            justify='left')
        allowed_label.pack(pady=10)
        
        # معلومات إضافية
        info_frame = tk.Frame(content_frame, bg='white')
        info_frame.pack(fill='x', padx=20, pady=20)
        
        info_text = ""
        if meter_type == 'مولدة':
            info_text = "⚡ المولدة: المستوى الأعلى، تغذي علب التوزيع"
        elif meter_type == 'علبة توزيع':
            info_text = "🔌 علبة التوزيع: تتصل بالمولدة وتغذي العدادات الرئيسية"
        elif meter_type == 'رئيسية':
            info_text = "🏠 العداد الرئيسي: يتصل بعلبة التوزيع ويغذي عدادات الزبائن"
        else:
            info_text = "👤 عداد الزبون: المستوى النهائي، يقيس استهلاك الزبون المباشر"
        
        info_label = tk.Label(info_frame, 
                            text=info_text,
                            font=('Arial', 11, 'italic'),
                            bg='white', fg='#7f8c8d',
                            wraplength=400)
        info_label.pack()
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def get_hierarchy_level(self, meter_type):
        """الحصول على المستوى الهرمي بناءً على نوع العداد"""
        levels = {
            'مولدة': 'المستوى الأول (أعلى)',
            'علبة توزيع': 'المستوى الثاني',
            'رئيسية': 'المستوى الثالث',
            'زبون': 'المستوى الرابع (أدنى)'
        }
        return levels.get(meter_type, 'غير محدد')
    
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



    # إضافة دالة جديدة
    def create_financial_info_tab(self, parent):
        """إنشاء تبويب معلومات التصنيف المالي"""
        canvas = tk.Canvas(parent, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        content_frame = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        content_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # جلب بيانات التصنيف المالي من قاعدة البيانات
        try:
            from database.connection import db
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT financial_category, free_reason, free_amount,
                           free_remaining, free_expiry_date, vip_reason,
                           vip_no_cut_days, vip_expiry_date, vip_grace_period
                    FROM customers WHERE id = %s
                """, (self.customer_data['id'],))
                
                financial_data = cursor.fetchone()
                
                if financial_data:
                    category = financial_data['financial_category']
                    
                    # عرض أيقونة التصنيف
                    category_icons = {
                        'normal': '👤 عادي',
                        'free': '🎁 مجاني',
                        'vip': '⭐ VIP',
                        'free_vip': '🌟 مجاني + VIP'
                    }
                    
                    category_colors = {
                        'normal': '#3498db',
                        'free': '#2ecc71',
                        'vip': '#e67e22',
                        'free_vip': '#9b59b6'
                    }
                    
                    icon_label = tk.Label(content_frame,
                                        text=category_icons.get(category, '❓ غير معروف'),
                                        font=('Arial', 16, 'bold'),
                                        bg='white', fg=category_colors.get(category, '#7f8c8d'))
                    icon_label.pack(pady=20)
                    
                    # عرض معلومات التصنيف
                    info_frame = tk.Frame(content_frame, bg='white')
                    info_frame.pack(fill='x', padx=30, pady=10)
                    
                    # معلومات المجاني
                    if category in ['free', 'free_vip']:
                        free_frame = tk.LabelFrame(info_frame, 
                                                  text="🎁 معلومات المجانية",
                                                  font=('Arial', 12, 'bold'),
                                                  bg='white', fg='#27ae60',
                                                  relief='groove')
                        free_frame.pack(fill='x', pady=10)
                        
                        free_info = [
                            ('السبب', financial_data['free_reason'] or 'غير محدد'),
                            ('المبلغ الكلي', f"{financial_data['free_amount']:,.0f} كيلو واط"),
                            ('المتبقي', f"{financial_data['free_remaining']:,.0f} كيلو واط"),
                            ('تاريخ الانتهاء', self.format_date(financial_data['free_expiry_date']))
                        ]
                        
                        for label, value in free_info:
                            row = tk.Frame(free_frame, bg='white')
                            row.pack(fill='x', pady=5)
                            
                            tk.Label(row, text=label + ":", font=('Arial', 10, 'bold'),
                                   bg='white', width=15, anchor='e').pack(side='left', padx=5)
                            tk.Label(row, text=value, font=('Arial', 10),
                                   bg='#f8f9fa', fg='#495057',
                                   relief='ridge', anchor='w', padx=10, pady=2).pack(side='left', fill='x', expand=True)
                    
                    # معلومات VIP
                    if category in ['vip', 'free_vip']:
                        vip_frame = tk.LabelFrame(info_frame,
                                                 text="⭐ معلومات VIP",
                                                 font=('Arial', 12, 'bold'),
                                                 bg='white', fg='#e67e22',
                                                 relief='groove')
                        vip_frame.pack(fill='x', pady=10)
                        
                        vip_info = [
                            ('السبب', financial_data['vip_reason'] or 'غير محدد'),
                            ('أيام عدم القطع', f"{financial_data['vip_no_cut_days']} يوم"),
                            ('تاريخ انتهاء VIP', self.format_date(financial_data['vip_expiry_date'])),
                            ('فترة السماح', f"{financial_data['vip_grace_period']} يوم")
                        ]
                        
                        for label, value in vip_info:
                            row = tk.Frame(vip_frame, bg='white')
                            row.pack(fill='x', pady=5)
                            
                            tk.Label(row, text=label + ":", font=('Arial', 10, 'bold'),
                                   bg='white', width=15, anchor='e').pack(side='left', padx=5)
                            tk.Label(row, text=value, font=('Arial', 10),
                                   bg='#f8f9fa', fg='#495057',
                                   relief='ridge', anchor='w', padx=10, pady=2).pack(side='left', fill='x', expand=True)
                    
                    # زر إدارة التصنيف
                    if hasattr(self.parent, 'user_data'):
                        manage_btn = tk.Button(content_frame,
                                             text="⚙️ إدارة التصنيف المالي",
                                             command=self.open_financial_manager,
                                             bg='#9b59b6', fg='white',
                                             font=('Arial', 11),
                                             padx=20, pady=10, cursor='hand2')
                        manage_btn.pack(pady=20)
        
        except Exception as e:
            logger.error(f"خطأ في تحميل بيانات التصنيف المالي: {e}")
            error_label = tk.Label(content_frame,
                                 text="⚠️ خطأ في تحميل بيانات التصنيف المالي",
                                 font=('Arial', 12),
                                 bg='white', fg='#e74c3c')
            error_label.pack(pady=50)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def open_financial_manager(self):
        """فتح مدير التصنيف المالي"""
        try:
            from ui.financial_category_ui import FinancialCategoryUI
            FinancialCategoryUI(self.parent, self.customer_data, self.parent.user_data)
        except ImportError as e:
            messagebox.showerror("خطأ", f"لا يمكن تحميل مدير التصنيف المالي: {e}")        