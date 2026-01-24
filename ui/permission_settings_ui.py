# ui/permission_settings_ui.py
"""
واجهة إعدادات الصلاحيات
تتيح إدارة الصلاحيات لكل دور
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from auth.permissions import get_permissions_by_category, get_all_permissions
from auth.permission_engine import permission_engine
from database.connection import db

logger = logging.getLogger(__name__)

class PermissionSettingsUI:
    """واجهة إعدادات الصلاحيات"""
    
    def __init__(self, parent_frame, user_data):
        self.parent = parent_frame
        self.user_data = user_data
        self.roles = []
        self.permission_vars = {}  # {role: {permission_key: BooleanVar}}
        
        self.load_roles()
        self.create_widgets()
    
    def load_roles(self):
        """تحميل قائمة الأدوار"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT role FROM users 
                    WHERE role IS NOT NULL 
                    ORDER BY role
                """)
                self.roles = [row['role'] for row in cursor.fetchall()]
                
                # إضافة الأدوار الأساسية إذا لم تكن موجودة
                base_roles = ['admin', 'accountant', 'cashier', 'viewer']
                for role in base_roles:
                    if role not in self.roles:
                        self.roles.append(role)
                
                self.roles.sort()
        except Exception as e:
            logger.error(f"خطأ في تحميل الأدوار: {e}")
            self.roles = ['admin', 'accountant', 'cashier', 'viewer']
    
    def create_widgets(self):
        """إنشاء واجهة الإعدادات"""
        # مسح المحتوى القديم
        for widget in self.parent.winfo_children():
            widget.destroy()
        
        # الإطار الرئيسي مع تمرير
        main_frame = tk.Frame(self.parent, bg='white')
        main_frame.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(main_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient='vertical', command=canvas.yview)
        content_frame = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # تحديث منطقة التمرير
        def on_configure(event):
            canvas.configure(scrollregion=canvas.bbox('all'))
        
        content_frame.bind('<Configure>', on_configure)
        
        # العنوان
        title = tk.Label(content_frame,
                        text="⚙️ إدارة الصلاحيات - التحكم بالوصول",
                        font=('Arial', 18, 'bold'),
                        bg='white', fg='#2c3e50')
        title.pack(pady=20)
        
        # تبويبات لكل فئة
        notebook = ttk.Notebook(content_frame)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # تحميل الصلاحيات مصنفة
        categorized_perms = get_permissions_by_category()
        
        # إعداد متغيرات الصلاحيات لكل دور
        for role in self.roles:
            self.permission_vars[role] = {}
        
        # إنشاء تبويب لكل فئة
        for category, permissions in categorized_perms.items():
            tab = ttk.Frame(notebook)
            notebook.add(tab, text=self.get_category_name(category))
            
            self.create_category_tab(tab, category, permissions)
        
        # أزرار التحكم
        self.create_control_buttons(content_frame)
        
        # تعبئة وإظهار
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
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
    
    def create_category_tab(self, parent, category, permissions):
        """إنشاء تبويب لفئة معينة"""
        # إطار مع تمرير
        canvas = tk.Canvas(parent, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        tab_content = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=tab_content, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # رؤوس الأعمدة
        headers_frame = tk.Frame(tab_content, bg='#f8f9fa', relief='solid', borderwidth=1)
        headers_frame.pack(fill='x', pady=(0, 10))
        
        # اسم الصلاحية
        tk.Label(headers_frame, text="الصلاحية",
                font=('Arial', 11, 'bold'),
                bg='#f8f9fa', fg='#2c3e50',
                width=30).pack(side='left', padx=5, pady=5)
        
        # الأدوار
        for role in self.roles:
            role_name = self.get_role_name(role)
            tk.Label(headers_frame, text=role_name,
                    font=('Arial', 11, 'bold'),
                    bg='#f8f9fa', fg='#2c3e50',
                    width=15).pack(side='left', padx=5, pady=5)
        
        # إضافة الصلاحيات
        for perm in permissions:
            perm_frame = tk.Frame(tab_content, bg='white')
            perm_frame.pack(fill='x', pady=2)
            
            # اسم ووصف الصلاحية
            perm_info_frame = tk.Frame(perm_frame, bg='white')
            perm_info_frame.pack(side='left', fill='y', padx=5)
            
            tk.Label(perm_info_frame, text=perm['name'],
                    font=('Arial', 10),
                    bg='white', fg='#34495e',
                    anchor='w', width=30).pack(anchor='w')
            
            if perm.get('description'):
                tk.Label(perm_info_frame, text=f"({perm['description']})",
                        font=('Arial', 9),
                        bg='white', fg='#7f8c8d',
                        anchor='w').pack(anchor='w')
            
            # خانات اختيار لكل دور
            for role in self.roles:
                role_frame = tk.Frame(perm_frame, bg='white')
                role_frame.pack(side='left', padx=5)
                
                # استثناء: صلاحية admin لها كل شيء
                if role == 'admin':
                    tk.Label(role_frame, text="✅",
                            font=('Arial', 12),
                            bg='white', fg='#27ae60').pack()
                    continue
                
                var = tk.BooleanVar()
                self.permission_vars[role][perm['permission_key']] = var
                
                # تحميل القيمة الحالية
                self.load_permission_value(role, perm['permission_key'], var)
                
                # خانة الاختيار
                cb = tk.Checkbutton(role_frame, variable=var,
                                  bg='white', cursor='hand2')
                cb.pack()
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def get_role_name(self, role_key):
        """ترجمة أسماء الأدوار"""
        role_names = {
            'admin': 'مدير',
            'accountant': 'محاسب',
            'cashier': 'أمين صندوق',
            'viewer': 'مشاهد'
        }
        return role_names.get(role_key, role_key)
    
    def load_permission_value(self, role, permission_key, var):
        """تحميل قيمة الصلاحية الحالية"""
        try:
            with db.get_cursor() as cursor:
                # صلاحية *.* للadmin
                if role == 'admin':
                    var.set(True)
                    return
                
                cursor.execute("""
                    SELECT is_allowed FROM role_permissions
                    WHERE role = %s AND permission_key = %s
                """, (role, permission_key))
                
                result = cursor.fetchone()
                if result:
                    var.set(result['is_allowed'])
                else:
                    var.set(False)
        except Exception as e:
            logger.error(f"خطأ في تحميل قيمة الصلاحية: {e}")
            var.set(False)
    
    def create_control_buttons(self, parent):
        """إنشاء أزرار التحكم"""
        btn_frame = tk.Frame(parent, bg='white', pady=20)
        btn_frame.pack(fill='x')
        
        # زر الحفظ
        save_btn = tk.Button(btn_frame, text="💾 حفظ التغييرات",
                           command=self.save_permissions,
                           bg='#27ae60', fg='white',
                           font=('Arial', 12, 'bold'),
                           padx=30, pady=10)
        save_btn.pack(side='right', padx=10)
        
        # زر إعادة التحميل
        reload_btn = tk.Button(btn_frame, text="🔄 إعادة التحميل",
                             command=self.reload_permissions,
                             bg='#3498db', fg='white',
                             font=('Arial', 12),
                             padx=30, pady=10)
        reload_btn.pack(side='right', padx=10)
        
        # زر مساعدة
        help_btn = tk.Button(btn_frame, text="❓ مساعدة",
                           command=self.show_help,
                           bg='#f39c12', fg='white',
                           font=('Arial', 12),
                           padx=30, pady=10)
        help_btn.pack(side='left', padx=10)
    
    def save_permissions(self):
        """حفظ جميع التغييرات"""
        try:
            changes_count = 0
            
            for role in self.roles:
                if role == 'admin':
                    continue  # admin لديه كل الصلاحيات
                
                for permission_key, var in self.permission_vars[role].items():
                    is_allowed = var.get()
                    
                    # تحديث في قاعدة البيانات
                    if permission_engine.update_role_permission(role, permission_key, is_allowed):
                        changes_count += 1
            
            if changes_count > 0:
                messagebox.showinfo("نجاح", f"تم حفظ {changes_count} تغيير بنجاح")
                logger.info(f"تم تحديث {changes_count} صلاحية")
            else:
                messagebox.showinfo("معلومات", "لم يتم إجراء أي تغييرات")
                
        except Exception as e:
            logger.error(f"خطأ في حفظ الصلاحيات: {e}")
            messagebox.showerror("خطأ", f"فشل حفظ التغييرات: {str(e)}")
    
    def reload_permissions(self):
        """إعادة تحميل الصلاحيات"""
        if messagebox.askyesno("تأكيد", "هل تريد إعادة تحميل الصلاحيات؟\nسيتم فقدان التغييرات غير المحفوظة"):
            self.create_widgets()
    
    def show_help(self):
        """عرض تعليمات الاستخدام"""
        help_text = """
        🆘 مساعدة إدارة الصلاحيات
        
        كيفية الاستخدام:
        1. حدد الصلاحيات لكل دور باستخدام خانات الاختيار
        2. اضغط على "💾 حفظ التغييرات" لتطبيقها
        3. يمكنك "🔄 إعادة التحميل" لاستعادة الإعدادات السابقة
        
        ملاحظات:
        • المدير (admin) لديه جميع الصلاحيات تلقائيًا
        • التغييرات تؤثر على المستخدمين الجدد فورًا
        • المستخدمون الحاليون يحتاجون لإعادة تسجيل الدخول
        • يمكن تجاوز صلاحيات دور لمستخدم محدد
        
        ⚠️ تحذير: كن حذراً عند منح الصلاحيات
        """
        messagebox.showinfo("مساعدة", help_text)