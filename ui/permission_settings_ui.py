# ui/permission_settings_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from auth.permissions import get_permissions_by_category, get_all_permissions
from auth.permission_engine import permission_engine
from database.connection import db

logger = logging.getLogger(__name__)

class PermissionSettingsUI:
    """واجهة إعدادات الصلاحيات - مبسطة مع تمرير ذكي"""
    
    def __init__(self, parent_frame, user_data=None):
        self.parent = parent_frame
        self.user_data = user_data
        self.current_role = tk.StringVar(value="accountant")
        self.current_category = tk.StringVar(value="customers")
        self.permission_vars = {}
        
        # تتبع الفئة السابقة لتجنب التحديثات غير الضرورية
        self.last_category = None
        self.last_role = None
        
        self.create_widgets()
        self.load_role_permissions()
    
    def create_widgets(self):
        """إنشاء واجهة مع تمرير ذكي"""
        # مسح المحتوى القديم
        for widget in self.parent.winfo_children():
            widget.destroy()
        
        # الإطار الرئيسي مع تمرير رأسي
        main_frame = tk.Frame(self.parent, bg='white')
        main_frame.pack(fill='both', expand=True)
        
        # =============== إطار التمرير الرئيسي ===============
        self.canvas = tk.Canvas(main_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient='vertical', command=self.canvas.yview)
        self.content_frame = tk.Frame(self.canvas, bg='white')
        
        self.canvas.create_window((0, 0), window=self.content_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # ربط حدث التمرير بالماوس
        self.content_frame.bind('<Enter>', self._bind_to_mousewheel)
        self.content_frame.bind('<Leave>', self._unbind_from_mousewheel)
        
        # تحديد منطقة التمرير عند تغيير حجم الإطار
        self.content_frame.bind('<Configure>', self._on_frame_configure)
        
        self.canvas.pack(side='left', fill='both', expand=True, padx=(20, 0))
        scrollbar.pack(side='right', fill='y')
        
        # =============== المحتوى ===============
        # العنوان
        title = tk.Label(self.content_frame,
                        text="⚙️ إدارة الصلاحيات - 3 خطوات بسيطة",
                        font=('Arial', 18, 'bold'),
                        bg='white', fg='#2c3e50')
        title.pack(pady=20)
        
        subtitle = tk.Label(self.content_frame,
                           text="اختر الدور، ثم المجال، ثم اضبط الصلاحيات",
                           font=('Arial', 11),
                           bg='white', fg='gray')
        subtitle.pack()
        
        # =============== الخطوة 1: اختيار الدور ===============
        self.create_step1()
        
        # =============== الخطوة 2: اختيار المجال ===============
        self.create_step2()
        
        # =============== الخطوة 3: الصلاحيات مع تمرير داخلي ===============
        self.create_step3()
        
        # =============== أزرار التحكم ===============
        self.create_control_buttons()
    
    def create_step1(self):
        """إنشاء خطوة اختيار الدور"""
        step1_frame = tk.Frame(self.content_frame, bg='white', bd=2, relief='groove')
        step1_frame.pack(fill='x', pady=15, padx=20)
        
        # عنوان الخطوة
        step1_title = tk.Label(step1_frame,
                              text="الخطوة 1: اختر دوراً",
                              font=('Arial', 14, 'bold'),
                              bg='white', fg='#2c3e50')
        step1_title.pack(anchor='w', padx=15, pady=10)
        
        # شرح بسيط
        step1_desc = tk.Label(step1_frame,
                             text="حدد الدور الذي تريد تعديل صلاحياته:",
                             font=('Arial', 10),
                             bg='white', fg='#666')
        step1_desc.pack(anchor='w', padx=15, pady=(0, 10))
        
        # أزرار الراديو للأدوار
        roles_frame = tk.Frame(step1_frame, bg='white')
        roles_frame.pack(fill='x', padx=15, pady=10)
        
        roles = [
            ('admin', '👑 مدير النظام', '#27ae60'),
            ('accountant', '📊 محاسب', '#3498db'),
            ('cashier', '💰 أمين صندوق', '#9b59b6'),
            ('viewer', '👀 مشاهد فقط', '#95a5a6')
        ]
        
        for role_key, role_name, color in roles:
            role_btn = tk.Radiobutton(roles_frame,
                                     text=role_name,
                                     variable=self.current_role,
                                     value=role_key,
                                     command=self.on_role_changed,
                                     bg='white',
                                     font=('Arial', 11),
                                     fg=color,
                                     selectcolor='white',
                                     activebackground='white')
            role_btn.pack(side='left', padx=20, pady=5)
    
    def create_step2(self):
        """إنشاء خطوة اختيار المجال"""
        step2_frame = tk.Frame(self.content_frame, bg='white', bd=2, relief='groove')
        step2_frame.pack(fill='x', pady=15, padx=20)
        
        step2_title = tk.Label(step2_frame,
                              text="الخطوة 2: اختر مجال الصلاحيات",
                              font=('Arial', 14, 'bold'),
                              bg='white', fg='#2c3e50')
        step2_title.pack(anchor='w', padx=15, pady=10)
        
        step2_desc = tk.Label(step2_frame,
                             text="اختر المجال الذي تريد التحكم بصلاحياته:",
                             font=('Arial', 10),
                             bg='white', fg='#666')
        step2_desc.pack(anchor='w', padx=15, pady=(0, 10))
        
        # أزرار المجالات في شبكة 2×3
        categories = [
            ('customers', '👥 الزبائن', '#1abc9c'),
            ('invoices', '🧾 الفواتير', '#e74c3c'),
            ('reports', '📈 التقارير', '#f39c12'),
            ('system', '⚙️ النظام', '#34495e'),
            ('settings', '🔧 الإعدادات', '#7f8c8d'),
            ('accounting', '💼 المحاسبة', '#16a085')
        ]
        
        categories_frame = tk.Frame(step2_frame, bg='white')
        categories_frame.pack(padx=15, pady=10)
        
        for i, (cat_key, cat_name, color) in enumerate(categories):
            row = i // 3
            col = i % 3
            
            cat_btn = tk.Radiobutton(categories_frame,
                                    text=cat_name,
                                    variable=self.current_category,
                                    value=cat_key,
                                    command=self.on_category_changed,
                                    bg='white',
                                    font=('Arial', 10),
                                    fg=color,
                                    selectcolor='white',
                                    activebackground='white')
            cat_btn.grid(row=row, column=col, padx=10, pady=10, sticky='w')
    
    def create_step3(self):
        """إنشاء خطوة الصلاحيات مع تمرير داخلي"""
        step3_frame = tk.Frame(self.content_frame, bg='white', bd=2, relief='groove')
        step3_frame.pack(fill='both', expand=True, pady=15, padx=20)
        
        step3_title = tk.Label(step3_frame,
                              text="الخطوة 3: اضبط الصلاحيات",
                              font=('Arial', 14, 'bold'),
                              bg='white', fg='#2c3e50')
        step3_title.pack(anchor='w', padx=15, pady=10)
        
        # العنوان الديناميكي
        self.header_label = tk.Label(step3_frame,
                                    text="صلاحيات المحاسب في مجال الزبائن",
                                    font=('Arial', 12, 'bold'),
                                    bg='white', fg='#2c3e50')
        self.header_label.pack(anchor='w', padx=15, pady=(0, 15))
        
        # =============== إطار التمرير الداخلي للصلاحيات ===============
        # إطار يحوي Canvas وScrollbar
        permissions_container = tk.Frame(step3_frame, bg='white')
        permissions_container.pack(fill='both', expand=True, padx=15, pady=(0, 15))
        
        # Canvas للصلاحيات
        self.permissions_canvas = tk.Canvas(permissions_container,
                                           bg='white',
                                           highlightthickness=0,
                                           height=350)  # ارتفاع مناسب
        
        # Scrollbar عمودي
        permissions_scrollbar = ttk.Scrollbar(permissions_container,
                                            orient='vertical',
                                            command=self.permissions_canvas.yview)
        
        # الإطار الداخلي للصلاحيات
        self.permissions_frame = tk.Frame(self.permissions_canvas, bg='white')
        
        # نافذة في Canvas
        self.permissions_canvas.create_window((0, 0),
                                             window=self.permissions_frame,
                                             anchor='nw',
                                             width=self.permissions_canvas.winfo_reqwidth())
        
        # تكوين Scrollbar
        self.permissions_canvas.configure(yscrollcommand=permissions_scrollbar.set)
        
        # ربط أحداث التمرير
        self.permissions_frame.bind('<Configure>',
                                  lambda e: self.permissions_canvas.configure(
                                      scrollregion=self.permissions_canvas.bbox('all')
                                  ))
        
        # تمرير بالماوس
        self.permissions_frame.bind('<Enter>',
                                  lambda e: self.permissions_canvas.bind_all(
                                      '<MouseWheel>',
                                      lambda event: self.permissions_canvas.yview_scroll(
                                          int(-1 * (event.delta / 120)), 'units'
                                      )
                                  ))
        
        self.permissions_frame.bind('<Leave>',
                                  lambda e: self.permissions_canvas.unbind_all('<MouseWheel>'))
        
        # التخطيط
        self.permissions_canvas.pack(side='left', fill='both', expand=True)
        permissions_scrollbar.pack(side='right', fill='y')
        
        # أزرار التحكم السريع
        quick_controls_frame = tk.Frame(step3_frame, bg='white')
        quick_controls_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Button(quick_controls_frame,
                 text="✅ منح كل الصلاحيات في هذا المجال",
                 command=self.select_all_in_category,
                 bg='#27ae60', fg='white',
                 font=('Arial', 10),
                 padx=15, pady=8).pack(side='left', padx=5)
        
        tk.Button(quick_controls_frame,
                 text="❌ سحب كل الصلاحيات في هذا المجال",
                 command=self.deselect_all_in_category,
                 bg='#e74c3c', fg='white',
                 font=('Arial', 10),
                 padx=15, pady=8).pack(side='left', padx=5)
    
    def create_control_buttons(self):
        """إنشاء أزرار التحكم النهائية"""
        control_frame = tk.Frame(self.content_frame, bg='white', pady=20)
        control_frame.pack(fill='x')
        
        # زر المساعدة
        tk.Button(control_frame,
                 text="❓ كيف أستخدم هذا؟",
                 command=self.show_help,
                 bg='#f39c12', fg='white',
                 font=('Arial', 10),
                 padx=20, pady=8).pack(side='left', padx=20)
        
        # زر إعادة التحميل
        tk.Button(control_frame,
                 text="🔄 إعادة التحميل",
                 command=self.reload_permissions,
                 bg='#3498db', fg='white',
                 font=('Arial', 10),
                 padx=20, pady=8).pack(side='right', padx=10)
        
        # زر الحفظ
        self.save_btn = tk.Button(control_frame,
                                 text="💾 حفظ التغييرات",
                                 command=self.save_permissions,
                                 bg='#2c3e50', fg='white',
                                 font=('Arial', 11, 'bold'),
                                 padx=30, pady=10)
        self.save_btn.pack(side='right', padx=10)
    
    def _on_frame_configure(self, event=None):
        """تحديث منطقة التمرير عند تغيير حجم الإطار"""
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def _bind_to_mousewheel(self, event):
        """ربط عجلة الماوس للتمرير"""
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)
    
    def _unbind_from_mousewheel(self, event):
        """فك ربط عجلة الماوس"""
        self.canvas.unbind_all('<MouseWheel>')
    
    def _on_mousewheel(self, event):
        """معالجة تمرير عجلة الماوس"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
    
    def on_role_changed(self):
        """عند تغيير الدور"""
        current_role = self.current_role.get()
        current_category = self.current_category.get()
        
        # تحديث فقط إذا تغير الدور
        if current_role != self.last_role:
            self.last_role = current_role
            self.update_header()
            self.load_role_permissions()
    
    def on_category_changed(self):
        """عند تغيير الفئة"""
        current_role = self.current_role.get()
        current_category = self.current_category.get()
        
        # تحديث فقط إذا تغيرت الفئة
        if current_category != self.last_category:
            self.last_category = current_category
            self.update_header()
            self.load_role_permissions()
    
    def update_header(self):
        """تحديث العنوان"""
        role = self.current_role.get()
        category = self.current_category.get()
        
        role_names = {
            'admin': 'مدير النظام',
            'accountant': 'المحاسب',
            'cashier': 'أمين الصندوق',
            'viewer': 'المشاهد'
        }
        
        category_names = {
            'customers': 'الزبائن',
            'invoices': 'الفواتير',
            'reports': 'التقارير',
            'system': 'النظام',
            'settings': 'الإعدادات',
            'accounting': 'المحاسبة'
        }
        
        role_name = role_names.get(role, role)
        category_name = category_names.get(category, category)
        
        self.header_label.config(text=f"صلاحيات {role_name} في مجال {category_name}")
        
        # تعطيل/تفعيل زر الحفظ
        if role == 'admin':
            self.save_btn.config(state='disabled', bg='#95a5a6')
        else:
            self.save_btn.config(state='normal', bg='#2c3e50')
    
    def load_role_permissions(self):
        """تحميل الصلاحيات مع إدارة التمرير"""
        # مسح المحتوى القديم
        for widget in self.permissions_frame.winfo_children():
            widget.destroy()
        
        role = self.current_role.get()
        category = self.current_category.get()
        
        # إذا كان الدور admin، عرض رسالة خاصة
        if role == 'admin':
            self.show_admin_message()
            return
        
        # تحميل الصلاحيات
        categorized_perms = get_permissions_by_category()
        permissions = categorized_perms.get(category, [])
        
        if not permissions:
            no_data_label = tk.Label(self.permissions_frame,
                                    text=f"لا توجد صلاحيات في فئة '{self.get_category_name(category)}'",
                                    font=('Arial', 11),
                                    bg='white', fg='gray')
            no_data_label.pack(pady=50)
            return
        
        # إعادة تهيئة المتغيرات
        self.permission_vars.clear()
        
        # عرض الصلاحيات
        for perm in permissions:
            self.add_permission_row(perm, role)
        
        # تحديث منطقة التمرير بعد إضافة المحتوى
        self.permissions_frame.update_idletasks()
        self.permissions_canvas.configure(scrollregion=self.permissions_canvas.bbox('all'))
        
        # التمرير للأعلى
        self.permissions_canvas.yview_moveto(0.0)
    
    def show_admin_message(self):
        """عرض رسالة المدير"""
        message_frame = tk.Frame(self.permissions_frame, bg='white')
        message_frame.pack(expand=True, fill='both', pady=40)
        
        tk.Label(message_frame,
                text="👑",
                font=('Arial', 48),
                bg='white', fg='gold').pack()
        
        tk.Label(message_frame,
                text="مدير النظام لديه جميع الصلاحيات",
                font=('Arial', 16, 'bold'),
                bg='white', fg='green').pack(pady=10)
        
        tk.Label(message_frame,
                text="المدير (admin) يملك صلاحية الوصول إلى كل شيء تلقائياً\nلا تحتاج لتعديل أي صلاحية لهذا الدور",
                font=('Arial', 11),
                bg='white', fg='#666',
                justify='center').pack()
    
    def add_permission_row(self, permission, role):
        """إضافة صف صلاحية"""
        row_frame = tk.Frame(self.permissions_frame, bg='white')
        row_frame.pack(fill='x', pady=3, padx=5)
        
        # متغير الصلاحية
        var = tk.BooleanVar()
        self.permission_vars[permission['permission_key']] = var
        
        # تحميل القيمة الحالية
        self.load_permission_value(role, permission['permission_key'], var)
        
        # خانة الاختيار
        cb = tk.Checkbutton(row_frame,
                           variable=var,
                           bg='white',
                           activebackground='white')
        cb.pack(side='right', padx=(10, 0))
        
        # معلومات الصلاحية
        info_frame = tk.Frame(row_frame, bg='white')
        info_frame.pack(side='left', fill='x', expand=True)
        
        # اسم الصلاحية
        tk.Label(info_frame,
                text=f"• {permission['name']}",
                font=('Arial', 10, 'bold'),
                bg='white', fg='#2c3e50',
                anchor='w').pack(anchor='w')
        
        # وصف الصلاحية
        if permission.get('description'):
            tk.Label(info_frame,
                    text=f"   {permission['description']}",
                    font=('Arial', 9),
                    bg='white', fg='#666',
                    anchor='w').pack(anchor='w')
    
    def load_permission_value(self, role, permission_key, var):
        """تحميل قيمة الصلاحية"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT is_allowed FROM role_permissions
                    WHERE role = %s AND permission_key = %s
                """, (role, permission_key))
                
                result = cursor.fetchone()
                var.set(result['is_allowed'] if result else False)
        except Exception as e:
            logger.error(f"خطأ في تحميل قيمة الصلاحية: {e}")
            var.set(False)
    
    def select_all_in_category(self):
        """منح كل الصلاحيات"""
        role = self.current_role.get()
        if role == 'admin':
            return
        
        for var in self.permission_vars.values():
            var.set(True)
    
    def deselect_all_in_category(self):
        """سحب كل الصلاحيات"""
        role = self.current_role.get()
        if role == 'admin':
            return
        
        for var in self.permission_vars.values():
            var.set(False)
    
    def get_role_name(self, role_key):
        """ترجمة أسماء الأدوار"""
        role_names = {
            'admin': 'مدير النظام',
            'accountant': 'محاسب',
            'cashier': 'أمين صندوق',
            'viewer': 'مشاهد'
        }
        return role_names.get(role_key, role_key)
    
    def get_category_name(self, category_key):
        """ترجمة أسماء الفئات"""
        category_names = {
            'customers': 'الزبائن',
            'invoices': 'الفواتير',
            'reports': 'التقارير',
            'system': 'النظام',
            'settings': 'الإعدادات',
            'accounting': 'المحاسبة'
        }
        return category_names.get(category_key, category_key)
    
    def save_permissions(self):
        """حفظ التغييرات"""
        role = self.current_role.get()
        
        if role == 'admin':
            messagebox.showinfo("معلومة", "لا يمكن تعديل صلاحيات مدير النظام")
            return
        
        try:
            changes_count = 0
            
            for permission_key, var in self.permission_vars.items():
                is_allowed = var.get()
                
                if permission_engine.update_role_permission(role, permission_key, is_allowed):
                    changes_count += 1
            
            if changes_count > 0:
                messagebox.showinfo("نجاح",
                    f"✓ تم حفظ {changes_count} صلاحية للدور: {self.get_role_name(role)}\n"
                    f"في مجال: {self.get_category_name(self.current_category.get())}")
            else:
                messagebox.showinfo("معلومة", "⚠️ لم يتم إجراء أي تغييرات")
                
        except Exception as e:
            logger.error(f"خطأ في حفظ الصلاحيات: {e}")
            messagebox.showerror("خطأ", f"✗ فشل حفظ التغييرات: {str(e)}")
    
    def reload_permissions(self):
        """إعادة تحميل"""
        if messagebox.askyesno("تأكيد",
                              "هل تريد إعادة تحميل الصلاحيات؟\n"
                              "سيتم فقدان التغييرات غير المحفوظة."):
            self.load_role_permissions()
    
    def show_help(self):
        """عرض المساعدة"""
        help_text = """
        🎯 **كيفية استخدام إدارة الصلاحيات:**
        
        فقط اتبع هذه الخطوات الثلاث:
        
        1️⃣ **اختر دوراً** من القائمة
           • 👑 مدير النظام: يملك كل الصلاحيات
           • 📊 محاسب: إدارة الزبائن والفواتير
           • 💰 أمين صندوق: معالجة الفواتير
           • 👀 مشاهد: عرض فقط
        
        2️⃣ **اختر مجال الصلاحيات**
           • 👥 الزبائن: إدارة العملاء والرصيد
           • 🧾 الفواتير: إنشاء وتعديل الفواتير
           • 📈 التقارير: عرض التقارير
           • ⚙️ النظام: إدارة المستخدمين
           • 🔧 الإعدادات: إعدادات النظام
           • 💼 المحاسبة: عمليات محاسبية
        
        3️⃣ **اضبط الصلاحيات**
           • ✓ شغل: منح الصلاحية
           • ✗ أطفئ: سحب الصلاحية
           • استخدم "✅ منح كل الصلاحيات" للسرعة
           • استخدم "❌ سحب كل الصلاحيات" للإلغاء
        
        أخيراً: اضغط **"💾 حفظ التغييرات"** لتطبيقها!
        
        💡 **نصائح مهمة:**
        • استخدم عجلة الماوس للتمرير في قائمة الصلاحيات
        • يمكنك التمرير في الصفحة الرئيسية أيضاً
        • التغييرات تنطبق على كل من لديه هذا الدور
        • كن حذراً عند منح صلاحيات حساسة
        """
        messagebox.showinfo("🚀 شرح مبسط", help_text)