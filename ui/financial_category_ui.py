# ui/financial_category_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class FinancialCategoryUI:
    """واجهة إدارة التصنيف المالي للزبائن"""
    
    def __init__(self, parent, customer_data, user_data):
        self.parent = parent
        self.customer_data = customer_data
        self.user_data = user_data
        self.customer_manager = None
        
        self.load_customer_manager()
        self.create_dialog()
        self.create_widgets()
        self.load_current_category()
        
        self.dialog.grab_set()
    
    def load_customer_manager(self):
        """تحميل مدير الزبائن"""
        try:
            from modules.customers import CustomerManager
            self.customer_manager = CustomerManager()
        except ImportError:
            messagebox.showerror("خطأ", "لا يمكن تحميل وحدة الزبائن")
    
    def create_dialog(self):
        """إنشاء النافذة المنبثقة مع شريط تمرير عام"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"التصنيف المالي - {self.customer_data['name']}")
        self.dialog.geometry("700x800")  # حجم أولي مناسب
        self.dialog.resizable(True, True)  # السماح بتغيير الحجم
        self.dialog.configure(bg='#f5f7fa')
        
        # إنشاء Canvas رئيسي مع شريط تمرير عمودي
        self.main_canvas = tk.Canvas(self.dialog, bg='#f5f7fa', highlightthickness=0)
        self.main_scrollbar = ttk.Scrollbar(self.dialog, orient='vertical', command=self.main_canvas.yview)
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)
        
        # إطار داخلي يحتوي على كل المحتوى
        self.main_frame = tk.Frame(self.main_canvas, bg='#f5f7fa')
        self.main_canvas.create_window((0, 0), window=self.main_frame, anchor='nw', width=self.main_canvas.winfo_width())
        
        # ترتيب Canvas و Scrollbar
        self.main_canvas.pack(side='left', fill='both', expand=True)
        self.main_scrollbar.pack(side='right', fill='y')
        
        # تحديث منطقة التمرير عند تغيير حجم الإطار الداخلي
        self.main_frame.bind('<Configure>', self._on_frame_configure)
        self.main_canvas.bind('<Configure>', self._on_canvas_configure)
        
        # ربط عجلة الفأرة بالتمرير
        self._bind_mousewheel()
        
        # مركزية النافذة بعد إنشائها
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'+{x}+{y}')

    def _on_frame_configure(self, event):
        """تحديث منطقة التمرير عند تغيير حجم الإطار الداخلي"""
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox('all'))

    def _on_canvas_configure(self, event):
        """ضبط عرض الإطار الداخلي ليتناسب مع عرض Canvas"""
        self.main_canvas.itemconfig(1, width=event.width)  # 1 هو معرف النافذة الداخلية

    def _bind_mousewheel(self):
        """ربط عجلة الفأرة بالتمرير"""
        def _on_mousewheel(event):
            self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.dialog.bind("<MouseWheel>", _on_mousewheel)
        # إلغاء الربط عند إغلاق النافذة لتجنب التأثير على النوافذ الأخرى
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        """معالج إغلاق النافذة - إلغاء ربط عجلة الفأرة"""
        self.dialog.unbind_all("<MouseWheel>")
        self.dialog.destroy()

    def create_widgets(self):
        """إنشاء عناصر الواجهة داخل main_frame"""
        # إطار العنوان
        title_frame = tk.Frame(self.main_frame, bg='#9b59b6', height=70)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, 
                            text=f"📊 التصنيف المالي - {self.customer_data['name']}",
                            font=('Arial', 16, 'bold'),
                            bg='#9b59b6', fg='white')
        title_label.pack(expand=True)
        
        # إطار المعلومات الأساسية
        info_frame = tk.Frame(self.main_frame, bg='#e8f4fc', relief='ridge', borderwidth=1)
        info_frame.pack(fill='x', padx=20, pady=10)
        
        info_text = f"""
        👤 الزبون: {self.customer_data['name']} | 📦 العلبة: {self.customer_data.get('box_number', '')}
        📍 القطاع: {self.customer_data.get('sector_name', 'غير محدد')} | 📞 الهاتف: {self.customer_data.get('phone_number', '')}
        """
        
        info_label = tk.Label(info_frame, text=info_text,
                            font=('Arial', 11),
                            bg='#e8f4fc', fg='#2c3e50',
                            justify='left')
        info_label.pack(padx=10, pady=10)
        
        # إنشاء دفتر التبويبات
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # تبويب التصنيف الحالي
        current_tab = ttk.Frame(notebook)
        self.create_current_category_tab(current_tab)
        notebook.add(current_tab, text='التصنيف الحالي')
        
        # تبويب تغيير التصنيف
        change_tab = ttk.Frame(notebook)
        self.create_change_category_tab(change_tab)
        notebook.add(change_tab, text='تغيير التصنيف')
        
        # تبويب السجل
        history_tab = ttk.Frame(notebook)
        self.create_history_tab(history_tab)
        notebook.add(history_tab, text='سجل التغييرات')
        
        # أزرار التحكم (الآن داخل main_frame)
        self.create_buttons()
        
            
    def create_current_category_tab(self, parent):
        """إنشاء تبويب التصنيف الحالي"""
        canvas = tk.Canvas(parent, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        content_frame = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        content_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # عنوان القسم
        title_label = tk.Label(content_frame,
                              text="📋 التصنيف المالي الحالي",
                              font=('Arial', 14, 'bold'),
                              bg='white', fg='#2c3e50')
        title_label.pack(pady=(10, 20))
        
        # إطار لعرض التصنيف الحالي (سيتم تحديثه لاحقاً)
        self.current_category_frame = tk.Frame(content_frame, bg='white')
        self.current_category_frame.pack(fill='x', padx=20, pady=10)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def load_current_category(self):
        """تحميل وتعبئة بيانات التصنيف الحالي"""
        if not self.customer_manager:
            return
        
        # مسح الإطار الحالي
        for widget in self.current_category_frame.winfo_children():
            widget.destroy()
        
        # جلب البيانات من قاعدة البيانات
        try:
            from database.connection import db
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT financial_category, free_reason, free_amount,
                           free_remaining, free_expiry_date, vip_reason,
                           vip_no_cut_days, vip_expiry_date, vip_grace_period
                    FROM customers WHERE id = %s
                """, (self.customer_data['id'],))
                
                category_data = cursor.fetchone()
                
                if not category_data:
                    return
                
                category = category_data['financial_category']
                
                # عرض التصنيف
                category_info = [
                    ('التصنيف الحالي', self.customer_manager.get_category_name(category), 
                     self.get_category_color(category))
                ]
                
                if category in ['free', 'free_vip']:
                    free_info = [
                        ('سبب المجانية', category_data['free_reason'] or 'غير محدد'),
                        ('المبلغ المجاني', f"{category_data['free_amount']:,.0f} كيلو واط"),
                        ('المتبقي', f"{category_data['free_remaining']:,.0f} كيلو واط"),
                        ('تاريخ الانتهاء', self.format_date(category_data['free_expiry_date']))
                    ]
                    category_info.extend(free_info)
                
                if category in ['vip', 'free_vip']:
                    vip_info = [
                        ('سبب VIP', category_data['vip_reason'] or 'غير محدد'),
                        ('أيام عدم القطع', f"{category_data['vip_no_cut_days']} يوم"),
                        ('تاريخ انتهاء VIP', self.format_date(category_data['vip_expiry_date'])),
                        ('فترة السماح', f"{category_data['vip_grace_period']} يوم")
                    ]
                    category_info.extend(vip_info)
                
                # عرض المعلومات
                for i, (label, value, *color) in enumerate(category_info):
                    row_frame = tk.Frame(self.current_category_frame, bg='white')
                    row_frame.pack(fill='x', pady=8)
                    
                    lbl = tk.Label(row_frame, text=label + ":",
                                  font=('Arial', 11, 'bold'),
                                  bg='white', fg='#2c3e50',
                                  width=20, anchor='e')
                    lbl.pack(side='left', padx=5)
                    
                    fg_color = color[0] if color else '#495057'
                    val = tk.Label(row_frame, text=value,
                                  font=('Arial', 11),
                                  bg='#f8f9fa', fg=fg_color,
                                  relief='ridge', anchor='w',
                                  padx=10, pady=5)
                    val.pack(side='left', fill='x', expand=True, padx=5)
                
                # إضافة أيقونة توضيحية
                icon_label = tk.Label(self.current_category_frame,
                                    text=self.get_category_icon(category),
                                    font=('Arial', 24),
                                    bg='white', fg=self.get_category_color(category))
                icon_label.pack(pady=20)
                
        except Exception as e:
            logger.error(f"خطأ في تحميل التصنيف الحالي: {e}")
    
    def get_category_color(self, category):
        """الحصول على لون يمثل التصنيف"""
        colors = {
            'normal': '#3498db',   # أزرق
            'free': '#2ecc71',     # أخضر
            'vip': '#e67e22',      # برتقالي
            'free_vip': '#9b59b6',  # بنفسجي
            'mobile_accountant': '#f1c40f'   # أصفر ذهبي
        }
        return colors.get(category, '#7f8c8d')
        
    def get_category_icon(self, category):
        icons = {
            'normal': '👤',
            'free': '🎁',
            'vip': '⭐',
            'free_vip': '🌟',
            'mobile_accountant': '📱'   # أيقونة الهاتف
        }
        return icons.get(category, '❓')
    
    def create_change_category_tab(self, parent):
        """إنشاء تبويب تغيير التصنيف"""
        canvas = tk.Canvas(parent, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        content_frame = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        content_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # عنوان القسم
        title_label = tk.Label(content_frame,
                              text="🔄 تغيير التصنيف المالي",
                              font=('Arial', 14, 'bold'),
                              bg='white', fg='#2c3e50')
        title_label.pack(pady=(10, 20))
        
        # متغيرات التصنيف
        self.category_var = tk.StringVar(value='normal')
        
        # إطار اختيار التصنيف
        category_frame = tk.Frame(content_frame, bg='white')
        category_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(category_frame, text="اختر التصنيف:",
                font=('Arial', 12, 'bold'),
                bg='white').pack(anchor='w', pady=5)
        
        categories = [
            ('عادي', 'normal'),
            ('مجاني', 'free'),
            ('VIP', 'vip'),
            ('مجاني + VIP', 'free_vip'),
            ('محاسبة جوالة', 'mobile_accountant')
        ]        
        for name, value in categories:
            rb = tk.Radiobutton(category_frame, text=name, value=value,
                              variable=self.category_var,
                              font=('Arial', 11),
                              bg='white',
                              command=self.on_category_changed)
            rb.pack(anchor='w', pady=2)
        
        # ========== إضافة إطار المحصل (للتصنيف محاسبة جوالة) ==========
        self.collector_frame = tk.LabelFrame(content_frame, 
                                              text="تعيين محصل",
                                              font=('Arial', 11, 'bold'),
                                              bg='white', fg='#9b59b6',
                                              relief='groove', borderwidth=1)
        self.collector_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(self.collector_frame, text="اختر المحصل:",
                font=('Arial', 10), bg='white').pack(anchor='w', padx=5, pady=5)
        
        self.collector_var = tk.StringVar()
        self.collector_combo = ttk.Combobox(self.collector_frame, textvariable=self.collector_var,
                                             state='readonly', width=40)
        self.collector_combo.pack(pady=5, padx=5, fill='x')
        
        # تحميل قائمة المحصلين النشطين
        self.load_collectors_list()
        
        # إخفاء الإطار في البداية (سيظهر عند اختيار التصنيف المناسب)
        self.collector_frame.pack_forget()
        # ============================================================
        
        # إطار تفاصيل المجاني
        self.free_details_frame = tk.LabelFrame(content_frame, 
                                               text="تفاصيل المجانية",
                                               font=('Arial', 11, 'bold'),
                                               bg='white', fg='#27ae60',
                                               relief='groove', borderwidth=1)
        self.free_details_frame.pack(fill='x', padx=20, pady=10)
        
        # حقول المجاني
        tk.Label(self.free_details_frame, text="سبب المجانية:",
                font=('Arial', 10),
                bg='white').grid(row=0, column=0, sticky='e', padx=5, pady=5)
        
        self.free_reason_text = tk.Text(self.free_details_frame, height=3,
                                       font=('Arial', 10), wrap='word')
        self.free_reason_text.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        tk.Label(self.free_details_frame, text="المبلغ المجاني (كيلو واط):",
                font=('Arial', 10),
                bg='white').grid(row=1, column=0, sticky='e', padx=5, pady=5)
        
        self.free_amount_var = tk.StringVar(value='0')
        tk.Entry(self.free_details_frame, textvariable=self.free_amount_var,
                font=('Arial', 10)).grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        
        tk.Label(self.free_details_frame, text="تاريخ الانتهاء:",
                font=('Arial', 10),
                bg='white').grid(row=2, column=0, sticky='e', padx=5, pady=5)
        
        self.free_expiry_var = tk.StringVar()
        tk.Entry(self.free_details_frame, textvariable=self.free_expiry_var,
                font=('Arial', 10)).grid(row=2, column=1, padx=5, pady=5, sticky='ew')
        
        self.free_details_frame.grid_columnconfigure(1, weight=1)
        
        # إطار تفاصيل VIP
        self.vip_details_frame = tk.LabelFrame(content_frame, 
                                              text="تفاصيل VIP",
                                              font=('Arial', 11, 'bold'),
                                              bg='white', fg='#e67e22',
                                              relief='groove', borderwidth=1)
        self.vip_details_frame.pack(fill='x', padx=20, pady=10)
        
        # حقول VIP
        tk.Label(self.vip_details_frame, text="سبب الترقية:",
                font=('Arial', 10),
                bg='white').grid(row=0, column=0, sticky='e', padx=5, pady=5)
        
        self.vip_reason_text = tk.Text(self.vip_details_frame, height=3,
                                      font=('Arial', 10), wrap='word')
        self.vip_reason_text.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        tk.Label(self.vip_details_frame, text="أيام عدم القطع:",
                font=('Arial', 10),
                bg='white').grid(row=1, column=0, sticky='e', padx=5, pady=5)
        
        self.vip_days_var = tk.StringVar(value='0')
        tk.Entry(self.vip_details_frame, textvariable=self.vip_days_var,
                font=('Arial', 10)).grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        
        tk.Label(self.vip_details_frame, text="تاريخ انتهاء VIP:",
                font=('Arial', 10),
                bg='white').grid(row=2, column=0, sticky='e', padx=5, pady=5)
        
        self.vip_expiry_var = tk.StringVar()
        tk.Entry(self.vip_details_frame, textvariable=self.vip_expiry_var,
                font=('Arial', 10)).grid(row=2, column=1, padx=5, pady=5, sticky='ew')

        
        tk.Label(self.vip_details_frame, text="فترة السماح (أيام):",
                font=('Arial', 10),
                bg='white').grid(row=3, column=0, sticky='e', padx=5, pady=5)
        
        self.vip_grace_var = tk.StringVar(value='0')
        tk.Entry(self.vip_details_frame, textvariable=self.vip_grace_var,
                font=('Arial', 10)).grid(row=3, column=1, padx=5, pady=5, sticky='ew')
        
        self.vip_details_frame.grid_columnconfigure(1, weight=1)
        
        # ملاحظات التغيير
        tk.Label(content_frame, text="ملاحظات التغيير:",
                font=('Arial', 11, 'bold'),
                bg='white').pack(anchor='w', padx=20, pady=(10, 5))
        
        self.change_notes_text = tk.Text(content_frame, height=4,
                                        font=('Arial', 10), wrap='word')
        self.change_notes_text.pack(fill='x', padx=20, pady=(0, 20))
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # إخفاء الإطارات في البداية
        self.free_details_frame.pack_forget()
        self.vip_details_frame.pack_forget()
        # collector_frame مخفي بالفعل بواسطة pack_forget أعلاه
    
    def load_collectors_list(self):
        """تحميل قائمة المحصلين النشطين"""
        try:
            from database.connection import db
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, full_name, username 
                    FROM users 
                    WHERE role = 'collector' AND is_active = TRUE 
                    ORDER BY full_name
                """)
                collectors = cursor.fetchall()
                self.collector_map = {
                    f"{c['full_name']} ({c['username']})": c['id'] 
                    for c in collectors
                }
                self.collector_combo['values'] = list(self.collector_map.keys())
        except Exception as e:
            logger.error(f"خطأ في تحميل قائمة المحصلين: {e}")
            self.collector_map = {}
    
    def on_category_changed(self):
        """عند تغيير اختيار التصنيف"""
        category = self.category_var.get()
        
        # إظهار/إخفاء إطارات التفاصيل
        if category in ['free', 'free_vip']:
            self.free_details_frame.pack(fill='x', padx=20, pady=10)
        else:
            self.free_details_frame.pack_forget()
        
        if category in ['vip', 'free_vip']:
            self.vip_details_frame.pack(fill='x', padx=20, pady=10)
        else:
            self.vip_details_frame.pack_forget()
        
        # إظهار/إخفاء إطار المحصل حسب التصنيف
        if category == 'mobile_accountant':
            self.collector_frame.pack(fill='x', padx=20, pady=10)
        else:
            self.collector_frame.pack_forget()
    
    def create_history_tab(self, parent):
        """إنشاء تبويب سجل التغييرات"""
        # إطار الشجرة
        tree_frame = tk.Frame(parent)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # شريط التمرير
        v_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical')
        v_scrollbar.pack(side='right', fill='y')
        
        # إنشاء الشجرة
        columns = ('date', 'old_cat', 'new_cat', 'free_amount', 'vip_days', 'notes', 'user')
        
        self.history_tree = ttk.Treeview(tree_frame, columns=columns,
                                        yscrollcommand=v_scrollbar.set,
                                        selectmode='browse',
                                        show='headings',
                                        height=15)
        
        v_scrollbar.config(command=self.history_tree.yview)
        
        # تعريف رؤوس الأعمدة
        columns_config = [
            ('date', 'التاريخ', 150, 'center'),
            ('old_cat', 'التصنيف السابق', 100, 'center'),
            ('new_cat', 'التصنيف الجديد', 100, 'center'),
            ('free_amount', 'المبلغ المجاني', 120, 'center'),
            ('vip_days', 'أيام عدم القطع', 120, 'center'),
            ('notes', 'ملاحظات', 200, 'w'),
            ('user', 'المستخدم', 120, 'center')
        ]
        
        for col_id, heading, width, anchor in columns_config:
            self.history_tree.heading(col_id, text=heading)
            self.history_tree.column(col_id, width=width, anchor=anchor)
        
        self.history_tree.pack(fill='both', expand=True)
        
        # تحميل السجل
        self.load_history()
    
    def load_history(self):
        """تحميل سجل التغييرات"""
        if not self.customer_manager:
            return
        
        # مسح البيانات الحالية
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        try:
            logs = self.customer_manager.get_financial_logs(self.customer_data['id'])
            
            for log in logs:
                self.history_tree.insert('', 'end', values=(
                    log['created_at'].strftime('%Y-%m-%d %H:%M'),
                    self.customer_manager.get_category_name(log['old_category']) if log['old_category'] else '--',
                    self.customer_manager.get_category_name(log['new_category']),
                    f"{log['free_amount']:,.0f}" if log['free_amount'] else '--',
                    f"{log['vip_no_cut_days']} يوم" if log['vip_no_cut_days'] else '--',
                    log['change_notes'] or '',
                    log['changed_by_name'] or 'نظام'
                ))
                
        except Exception as e:
            logger.error(f"خطأ في تحميل سجل التغييرات: {e}")
    
    def create_buttons(self):
        """إنشاء أزرار التحكم"""
        buttons_frame = tk.Frame(self.dialog, bg='#f5f7fa')
        buttons_frame.pack(fill='x', pady=10, padx=20)
        
        # زر الحفظ
        save_btn = tk.Button(buttons_frame, text="💾 حفظ التغييرات",
                           command=self.save_changes,
                           bg='#27ae60', fg='white',
                           font=('Arial', 12, 'bold'),
                           padx=20, pady=8, cursor='hand2')
        save_btn.pack(side='right', padx=5)
        
        # زر التحديث
        refresh_btn = tk.Button(buttons_frame, text="🔄 تحديث",
                              command=self.refresh_data,
                              bg='#3498db', fg='white',
                              font=('Arial', 11),
                              padx=15, pady=8, cursor='hand2')
        refresh_btn.pack(side='right', padx=5)
        
        # زر الإغلاق
        close_btn = tk.Button(buttons_frame, text="إغلاق",
                             command=self.dialog.destroy,
                             bg='#95a5a6', fg='white',
                             font=('Arial', 11),
                             padx=30, pady=8, cursor='hand2')
        close_btn.pack(side='left', padx=5)
    
    def refresh_data(self):
        """تحديث البيانات"""
        self.load_current_category()
        self.load_history()
    
    def save_changes(self):
        """حفظ التغييرات"""
        if not self.customer_manager:
            messagebox.showerror("خطأ", "مدير الزبائن غير متاح")
            return
        
        try:
            category = self.category_var.get()
            category_data = {
                'financial_category': category,
                'user_id': self.user_data.get('id', 1),
                'change_notes': self.change_notes_text.get('1.0', 'end-1c').strip()
            }
            
            # بيانات المجاني
            if category in ['free', 'free_vip']:
                category_data['free_reason'] = self.free_reason_text.get('1.0', 'end-1c').strip()
                category_data['free_amount'] = float(self.free_amount_var.get() or 0)
                category_data['free_remaining'] = float(self.free_amount_var.get() or 0)
                category_data['free_expiry_date'] = self.free_expiry_var.get() or None
            
            # بيانات VIP
            if category in ['vip', 'free_vip']:
                category_data['vip_reason'] = self.vip_reason_text.get('1.0', 'end-1c').strip()
                category_data['vip_no_cut_days'] = int(self.vip_days_var.get() or 0)
                category_data['vip_expiry_date'] = self.vip_expiry_var.get() or None
                category_data['vip_grace_period'] = int(self.vip_grace_var.get() or 0)
            
            # ===== بيانات المحصل للتصنيف "محاسبة جوالة" =====
            if category == 'mobile_accountant':
                selected = self.collector_var.get()
                if not selected:
                    messagebox.showerror("خطأ", "يجب اختيار محصل للتصنيف 'محاسبة جوالة'")
                    return
                collector_id = self.collector_map.get(selected)
                if not collector_id:
                    messagebox.showerror("خطأ", "المحصل المحدد غير صالح")
                    return
                category_data['assigned_collector_id'] = collector_id
            else:
                # إذا لم يكن التصنيف محاسبة جوالة، نضمن إلغاء التعيين (إذا كان موجوداً سابقاً)
                category_data['assigned_collector_id'] = None
            # ================================================
            
            # حفظ التغييرات
            result = self.customer_manager.update_financial_category(
                self.customer_data['id'], category_data
            )
            
            if result['success']:
                messagebox.showinfo("نجاح", result['message'])
                self.refresh_data()
            else:
                messagebox.showerror("خطأ", result.get('error', 'فشل حفظ التغييرات'))
                
        except ValueError as e:
            messagebox.showerror("خطأ", f"قيم غير صالحة: {str(e)}")
        except Exception as e:
            logger.error(f"خطأ في حفظ التغييرات: {e}")
            messagebox.showerror("خطأ", f"فشل حفظ التغييرات: {str(e)}")
    
    def format_date(self, date_value):
        """تنسيق التاريخ"""
        if not date_value:
            return 'غير محدد'
        
        try:
            if hasattr(date_value, 'strftime'):
                return date_value.strftime('%Y-%m-%d')
        except:
            pass
        
        return str(date_value)