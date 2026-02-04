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
        
        # زر تحديث الجلسة الشخصية
        tk.Button(control_frame,
                text="🔄 تحديث جلستي",
                command=self.refresh_my_session,
                bg='#3498db', fg='white',
                font=('Arial', 10),
                padx=20, pady=8).pack(side='left', padx=20)

        # زر التحقق من قاعدة البيانات
        tk.Button(control_frame,
                text="🔍 تحقق من قاعدة البيانات",
                command=self.verify_database_state,
                bg='#e67e22', fg='white',
                font=('Arial', 10),
                padx=20, pady=8).pack(side='left', padx=10)

        # زر الفحص المباشر
        tk.Button(control_frame,
                text="🔍 فحص قاعدة البيانات مباشرة",
                command=self.direct_db_inspection,
                bg='#e74c3c', fg='white',
                font=('Arial', 10),
                padx=20, pady=8).pack(side='left', padx=10)                
        
        # زر المساعدة
        tk.Button(control_frame,
                text="❓ كيف أستخدم هذا؟",
                command=self.show_help,
                bg='#f39c12', fg='white',
                font=('Arial', 10),
                padx=20, pady=8).pack(side='left', padx=10)
        
        # زر إعادة التحميل
        tk.Button(control_frame,
                text="🔄 إعادة التحميل",
                command=self.reload_permissions,
                bg='#9b59b6', fg='white',
                font=('Arial', 10),
                padx=20, pady=8).pack(side='right', padx=10)

        # أضف هذا الزر قبل زر الحفظ:
        tk.Button(control_frame,
                text="🔄 تحديث الواجهة",
                command=self.force_refresh_ui,
                bg='#3498db', fg='white',
                font=('Arial', 10),
                padx=20, pady=8).pack(side='right', padx=5)
        
        # زر الحفظ
        self.save_btn = tk.Button(control_frame,
                                text="💾 حفظ التغييرات",
                                command=self.save_permissions,
                                bg='#2c3e50', fg='white',
                                font=('Arial', 11, 'bold'),
                                padx=30, pady=10)
        self.save_btn.pack(side='right', padx=10)

        # زر الفحص:
        tk.Button(control_frame,
                text="🔍 فحص *.*",
                command=self.check_wildcard_permissions,
                bg='#e74c3c', fg='white',
                font=('Arial', 10),
                padx=20, pady=8).pack(side='left', padx=10)

    def refresh_my_session(self):
        """تحديث جلسة المستخدم الحالي"""
        from auth.session import Session
        
        if not Session.is_authenticated():
            messagebox.showwarning("تحذير", "لم تقم بتسجيل الدخول")
            return
        
        username = Session.current_user.get('username', 'مستخدم')
        role = Session.get_role()
        
        if Session.refresh_user_data(force=True):
            messagebox.showinfo("نجاح",
                f"✅ تم تحديث جلستك بنجاح!\n\n"
                f"المستخدم: {username}\n"
                f"الدور: {role}\n\n"
                f"تم تحميل أحدث الصلاحيات من قاعدة البيانات.")
        else:
            messagebox.showwarning("تحذير",
                "⚠️ لم يتم تحديث الجلسة\n\n"
                "قد يكون بسبب:\n"
                "1. لم يمر وقت كافٍ منذ آخر تحديث (10 ثوانٍ)\n"
                "2. مشكلة في الاتصال بقاعدة البيانات\n"
                "3. حسابك غير موجود")
        

    def check_wildcard_permissions(self):
        """فحص صلاحيات *.* وإزالتها إذا كانت تسبب مشاكل"""
        from database.connection import db
        
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT role, is_allowed 
                    FROM role_permissions 
                    WHERE permission_key = '*.*'
                """)
                
                wildcards = cursor.fetchall()
                
                if wildcards:
                    message = "⚠️ تحذير: توجد صلاحيات *.* (جميع الصلاحيات):\n\n"
                    for wc in wildcards:
                        status = "✅ مفعلة" if wc['is_allowed'] else "❌ معطلة"
                        message += f"الدور '{wc['role']}': {status}\n"
                    
                    message += "\nهذه الصلاحيات قد تسبب مشاكل في النظام.\n"
                    message += "هل تريد إزالتها؟"
                    
                    import tkinter.messagebox as messagebox
                    if messagebox.askyesno("تحذير", message):
                        cursor.execute("DELETE FROM role_permissions WHERE permission_key = '*.*'")
                        messagebox.showinfo("نجاح", "تم إزالة جميع صلاحيات *.*")
                        self.reload_permissions()
        except Exception as e:
            logger.error(f"خطأ في فحص صلاحيات *.*: {e}")

            
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
        """تحميل الصلاحيات مع إجبار التحديث من قاعدة البيانات"""
        # مسح المحتوى القديم
        for widget in self.permissions_frame.winfo_children():
            widget.destroy()
        
        role = self.current_role.get()
        category = self.current_category.get()
        
        # إذا كان الدور admin، عرض رسالة خاصة
        if role == 'admin':
            self.show_admin_message()
            return
        
        # تحميل الصلاحيات مباشرة من قاعدة البيانات
        try:
            from database.connection import db
            
            with db.get_cursor() as cursor:
                # استعلام محسّن - يعرض كل شيء
                cursor.execute("""
                    SELECT 
                        pc.permission_key, 
                        pc.name, 
                        pc.description,
                        COALESCE(rp.is_allowed, FALSE) as is_allowed,
                        rp.updated_at,
                        rp.id as rp_id
                    FROM permissions_catalog pc
                    LEFT JOIN role_permissions rp ON pc.permission_key = rp.permission_key
                        AND rp.role = %s
                    WHERE pc.category = %s AND pc.is_active = TRUE
                    ORDER BY pc.permission_key
                """, (role, category))
                
                permissions = cursor.fetchall()
                
                # تسجيل تفصيلي
                logger.info(f"🔍 تم تحميل {len(permissions)} صلاحية للدور '{role}' في فئة '{category}'")
                
                # تسجيل كل صلاحية على حدة
                for perm in permissions:
                    status = "✅ مفعل" if perm['is_allowed'] else "❌ معطل"
                    logger.debug(f"   • {perm['permission_key']}: {status} (ID: {perm['rp_id']}, آخر تحديث: {perm['updated_at']})")
        
        except Exception as e:
            logger.error(f"💥 خطأ في تحميل الصلاحيات من قاعدة البيانات: {e}")
            # استخدام الطريقة القديمة كبديل
            from auth.permissions import get_permissions_by_category
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
        
    def load_permission_value(self, role: str, permission_key: str, var: tk.BooleanVar, force_db: bool = True):
        """تحميل قيمة الصلاحية مباشرة من قاعدة البيانات"""
        try:
            # إذا طُلب إجبار التحميل من قاعدة البيانات، نمسح الكاش أولاً
            if force_db:
                from auth.permission_engine import permission_engine
                permission_engine.clear_cache()
            
            from database.connection import db
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT is_allowed FROM role_permissions
                    WHERE role = %s AND permission_key = %s
                """, (role, permission_key))
                
                result = cursor.fetchone()
                value = result['is_allowed'] if result else False
                
                # تحديث المتغير
                var.set(value)
                
                # تسجيل للتحقق
                logger.debug(f"🔍 تحميل قيمة {permission_key} للدور {role}: {value}")
                
                return value

                # التحقق المباشر من القيمة في قاعدة البيانات
            try:
                from database.connection import db
                with db.get_cursor() as verify_cursor:
                    verify_cursor.execute("""
                        SELECT is_allowed, updated_at 
                        FROM role_permissions 
                        WHERE role = %s AND permission_key = %s
                    """, (role, permission_key))
                    
                    verify_result = verify_cursor.fetchone()
                    if verify_result:
                        logger.info(f"✅ تحقق مباشر من DB: {permission_key} = {verify_result['is_allowed']} (آخر تحديث: {verify_result['updated_at']})")
            except Exception as e:
                logger.debug(f"تعذر التحقق من القيمة المباشرة: {e}")
                            
        except Exception as e:
            logger.error(f"خطأ في تحميل قيمة الصلاحية: {e}")
            var.set(False)
            return False
            
                
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
        """حفظ التغييرات مع تحديث الواجهة مباشرة"""
        role = self.current_role.get()
        
        if role == 'admin':
            messagebox.showinfo("معلومة", "لا يمكن تعديل صلاحيات مدير النظام")
            return
        
        try:
            changes_count = 0
            
            # جمع التغييرات أولاً
            changes = []
            for permission_key, var in self.permission_vars.items():
                is_allowed = var.get()
                
                # التحقق من القيمة الحالية أولاً (دون مسح الكاش)
                current_value = self.load_permission_value(role, permission_key, var, force_db=False)
                
                # فقط إذا كانت القيمة مختلفة
                if current_value != is_allowed:
                    changes.append((permission_key, is_allowed))
                    logger.info(f"📝 تغيير {permission_key}: {current_value} → {is_allowed}")
            
            if not changes:
                messagebox.showinfo("معلومة", "⚠️ لم يتم إجراء أي تغييرات (القيم نفسها كانت مضبوطة مسبقاً)")
                return
            
            # تطبيق التغييرات
            for permission_key, is_allowed in changes:
                from auth.permission_engine import permission_engine
                
                if permission_engine.update_role_permission(role, permission_key, is_allowed):
                    changes_count += 1
                    
                    # تحديث المتغير مباشرة
                    for key, var in self.permission_vars.items():
                        if key == permission_key:
                            var.set(is_allowed)
                            break
            
            if changes_count > 0:
                # 1. إجبار تحديث الواجهة
                self.force_refresh_ui()
                
                # 2. عرض رسالة النجاح
                messagebox.showinfo("نجاح",
                    f"✅ تم حفظ {changes_count} صلاحية للدور: {self.get_role_name(role)}\n"
                    f"📋 المجال: {self.get_category_name(self.current_category.get())}\n\n"
                    f"🔄 تم تحديث الواجهة مباشرة.")
                
                # 3. تسجيل النشاط
                try:
                    from auth.authentication import auth
                    from auth.session import Session
                    
                    auth.log_activity(
                        Session.current_user['id'] if Session.is_authenticated() else 1,
                        'permission_update',
                        f'تم تحديث {changes_count} صلاحية للدور {role}'
                    )
                except Exception as e:
                    logger.error(f"خطأ في تسجيل النشاط: {e}")
                    
            else:
                messagebox.showinfo("معلومة", "⚠️ لم يتم إجراء أي تغييرات")
                
        except Exception as e:
            logger.error(f"خطأ في حفظ الصلاحيات: {e}", exc_info=True)
            messagebox.showerror("خطأ", f"❌ فشل حفظ التغييرات: {str(e)}")
            

    def force_refresh_ui(self):
        """إجبار تحديث الواجهة بالكامل"""
        try:
            # 1. مسح جميع الكاشات
            from auth.permission_engine import permission_engine
            permission_engine.clear_cache()
            
            # 2. تحديث إطار الصلاحيات
            current_role = self.current_role.get()
            current_category = self.current_category.get()
            
            # حفظ الموضع الحالي
            old_role = current_role
            old_category = current_category
            
            # إعادة تحميل القوائم
            self.load_role_permissions()
            
            # تحديث العنوان
            self.update_header()
            
            # تسجيل النجاح
            logger.info(f"🔄 تم تحديث الواجهة للدور {old_role} والفئة {old_category}")
            
        except Exception as e:
            logger.error(f"خطأ في تحديث الواجهة: {e}")


    def verify_database_changes(self):
        """التحقق من التغييرات مباشرة في قاعدة البيانات"""
        from database.connection import db
        import tkinter.messagebox as messagebox
        
        role = self.current_role.get()
        category = self.current_category.get()
        
        try:
            with db.get_cursor() as cursor:
                # 1. التحقق من عدد الصلاحيات
                cursor.execute("""
                    SELECT COUNT(*) as total_perms
                    FROM role_permissions 
                    WHERE role = %s
                """, (role,))
                total_count = cursor.fetchone()['total_perms']
                
                # 2. التحقق من الصلاحيات في هذه الفئة
                cursor.execute("""
                    SELECT rp.permission_key, rp.is_allowed, rp.updated_at
                    FROM role_permissions rp
                    JOIN permissions_catalog pc ON rp.permission_key = pc.permission_key
                    WHERE rp.role = %s AND pc.category = %s
                    ORDER BY rp.permission_key
                """, (role, category))
                
                permissions = cursor.fetchall()
                
                # بناء رسالة النتائج
                message = f"🔍 التحقق من قاعدة البيانات للدور '{role}':\n\n"
                message += f"إجمالي الصلاحيات المخزنة: {total_count}\n"
                message += f"الصلاحيات في فئة '{category}': {len(permissions)}\n\n"
                
                for perm in permissions:
                    status = "✅ مفعل" if perm['is_allowed'] else "❌ معطل"
                    message += f"• {perm['permission_key']}: {status} (آخر تحديث: {perm['updated_at']})\n"
                
                messagebox.showinfo("نتيجة التحقق", message)
                
        except Exception as e:
            logger.error(f"خطأ في التحقق من قاعدة البيانات: {e}")
            messagebox.showerror("خطأ", f"فشل التحقق: {str(e)}")
                
    def reload_permissions(self):
        """إعادة تحميل"""
        if messagebox.askyesno("تأكيد",
                              "هل تريد إعادة تحميل الصلاحيات؟\n"
                              "سيتم فقدان التغييرات غير المحفوظة."):
            self.load_role_permissions()


    def direct_db_inspection(self):
        """فحص مباشر لقاعدة البيانات"""
        from database.connection import db
        import tkinter.messagebox as messagebox
        
        role = self.current_role.get()
        category = self.current_category.get()
        
        try:
            with db.get_cursor() as cursor:
                # 1. الحصول على جميع الصلاحيات في هذه الفئة
                cursor.execute("""
                    SELECT permission_key, name 
                    FROM permissions_catalog 
                    WHERE category = %s AND is_active = TRUE
                    ORDER BY permission_key
                """, (category,))
                
                all_perms = cursor.fetchall()
                
                message = f"🔍 الفحص المباشر لقاعدة البيانات:\n\n"
                message += f"الدور: {role}\n"
                message += f"الفئة: {category}\n"
                message += f"عدد الصلاحيات في الفئة: {len(all_perms)}\n\n"
                
                message += "تفاصيل كل صلاحية:\n"
                message += "-" * 40 + "\n"
                
                for perm in all_perms:
                    perm_key = perm['permission_key']
                    
                    # فحص القيمة في role_permissions
                    cursor.execute("""
                        SELECT is_allowed, updated_at, id 
                        FROM role_permissions 
                        WHERE role = %s AND permission_key = %s
                    """, (role, perm_key))
                    
                    role_perm = cursor.fetchone()
                    
                    if role_perm:
                        status = "✅ مفعل" if role_perm['is_allowed'] else "❌ معطل"
                        message += f"• {perm_key} ({perm['name']}):\n"
                        message += f"  {status} (ID: {role_perm['id']}, آخر تحديث: {role_perm['updated_at']})\n\n"
                    else:
                        message += f"• {perm_key} ({perm['name']}):\n"
                        message += f"  ⚠️ لا يوجد سجل في role_permissions (سيستخدم القيمة الافتراضية: False)\n\n"
                
                messagebox.showinfo("الفحص المباشر", message)
                
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل الفحص: {str(e)}")


    def update_role_permission(self, role: str, permission_key: str, is_allowed: bool) -> bool:
        """تحديث صلاحية دور مع تحديث الجلسات - طريقة مضمونة 100%"""
        try:
            with self.db.get_cursor() as cursor:
                # 1. تسجيل محاولة التحديث
                logger.info(f"🚀 بدء تحديث: {role}.{permission_key} = {is_allowed}")
                
                # 2. استعلام بسيط جداً: حذف القديم وأدخل الجديد
                cursor.execute("""
                    -- أولاً: حذف أي صفوف قديمة
                    DELETE FROM role_permissions 
                    WHERE role = %s AND permission_key = %s
                """, (role, permission_key))
                
                # 3. إدراج الصف الجديد
                cursor.execute("""
                    INSERT INTO role_permissions (role, permission_key, is_allowed, created_at, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id, is_allowed, updated_at
                """, (role, permission_key, is_allowed))
                
                result = cursor.fetchone()
                
                if result:
                    logger.info(f"✅ تم الحفظ بنجاح! ID: {result['id']}, القيمة: {result['is_allowed']}")
                    
                    # 4. التحقق المباشر من قاعدة البيانات
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM role_permissions 
                        WHERE role = %s AND permission_key = %s AND is_allowed = %s
                    """, (role, permission_key, is_allowed))
                    
                    verify = cursor.fetchone()
                    logger.info(f"🔍 التحقق: يوجد {verify['count']} صف مطابق في قاعدة البيانات")
                    
                    # ⭐⭐⭐ 5. مسح الكاش بشكل كامل للتأكد ⭐⭐⭐
                    self.clear_cache()
                    
                    # ⭐⭐⭐ 6. مسح جلسات جميع مستخدمي هذا الدور ⭐⭐⭐
                    from auth.session import Session
                    affected_users = 0
                    try:
                        cursor.execute("SELECT id FROM users WHERE role = %s", (role,))
                        users = cursor.fetchall()
                        for user in users:
                            Session._permission_version.pop(user['id'], None)
                            affected_users += 1
                        logger.info(f"🔄 تم مسح {affected_users} جلسة للمستخدمين بالدور {role}")
                    except Exception as e:
                        logger.error(f"⚠️ خطأ في مسح الجلسات: {e}")
                    
                    # 7. تسجيل النجاح
                    logger.info(f"🎉 تم تحديث صلاحية {permission_key} للدور {role} إلى {is_allowed}")
                    return True
                else:
                    logger.error("❌ فشل الإدراج - لم يتم إرجاع أي نتيجة")
                    return False
                    
        except Exception as e:
            logger.error(f"💥 خطأ في تحديث صلاحية الدور: {e}", exc_info=True)
            return False           


    def verify_database_state(self):
        """التحقق من حالة قاعدة البيانات بشكل مفصل"""
        from database.connection import db
        import tkinter.messagebox as messagebox
        
        role = self.current_role.get()
        category = self.current_category.get()
        
        try:
            with db.get_cursor() as cursor:
                # 1. التحقق من صلاحيات الدور
                cursor.execute("""
                    SELECT permission_key, is_allowed, updated_at
                    FROM role_permissions
                    WHERE role = %s
                    ORDER BY permission_key
                """, (role,))
                
                all_perms = cursor.fetchall()
                
                # 2. صلاحيات هذا الدور في هذه الفئة
                cursor.execute("""
                    SELECT rp.permission_key, rp.is_allowed, rp.updated_at
                    FROM role_permissions rp
                    JOIN permissions_catalog pc ON rp.permission_key = pc.permission_key
                    WHERE rp.role = %s AND pc.category = %s
                    ORDER BY rp.permission_key
                """, (role, category))
                
                category_perms = cursor.fetchall()
                
                # بناء الرسالة
                message = f"🔍 حالة قاعدة البيانات للدور: '{role}'\n\n"
                message += f"إجمالي الصلاحيات المخزنة: {len(all_perms)}\n"
                message += f"الصلاحيات في فئة '{category}': {len(category_perms)}\n\n"
                
                if category_perms:
                    message += "تفاصيل الصلاحيات في هذه الفئة:\n"
                    for perm in category_perms:
                        status = "✅ مفعل" if perm['is_allowed'] else "❌ معطل"
                        message += f"  • {perm['permission_key']}: {status} (آخر تحديث: {perm['updated_at']})\n"
                
                messagebox.showinfo("حالة قاعدة البيانات", message)
                
        except Exception as e:
            logger.error(f"خطأ في التحقق من قاعدة البيانات: {e}")
            messagebox.showerror("خطأ", f"فشل التحقق: {str(e)}")


    def diagnose_permission_issue(self):
        """تشخيص مشكلة الصلاحيات"""
        from auth.session import Session
        from auth.permission_engine import permission_engine
        
        if not Session.is_authenticated():
            return
        
        user_id = Session.current_user['id']
        role = Session.get_role()
        
        # جمع معلومات التشخيص
        info = f"""
    🔍 تشخيص مشكلة الصلاحيات:

    📊 معلومات المستخدم:
        - ID: {user_id}
        - الدور: {role}
        - اسم المستخدم: {Session.current_user.get('username')}

    💾 حالة الكاش:
        - إصدار الصلاحيات في الجلسة: {Session.current_user.get('_permissions_version', 0)}
        - عدد المستخدمين في كاش المحرك: {len(permission_engine._permissions_cache)}

    🔄 الإجراءات الموصى بها:
        1. انقر على 'إعادة التحميل' لتحديث الجلسة
        2. تأكد من حفظ التغييرات بعد التعديل
        3. إذا استمرت المشكلة، أعد تسجيل الدخول

    ✅ الحل التلقائي:
        - النظام يقوم بتحديث الجلسة تلقائياً كل 30 ثانية
        - يتم تحديث الكاش عند كل تعديل في الصلاحيات
    """
        
        messagebox.showinfo("تشخيص المشكلة", info)

        
    
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