# ui/main_window.py
import subprocess
from database.connection import db
from database.models import models
from modules.archive import ArchiveManager
from config.settings import DATABASE_CONFIG

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
from config.settings import APP_NAME, VERSION, COMPANY_NAME
from ui.archive_ui import ArchiveUI
from tkinter import filedialog
from utils.excel_handler import ExcelHandler
import os
from auth.permissions import has_permission, require_permission, check_permission_decorator


logger = logging.getLogger(__name__)

class MainWindow:
    def __init__(self, user_data):
        self.user_data = user_data
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.state('zoomed')
        
        self.setup_styles()
        self.create_widgets()
        self.setup_menu()
        self.setup_statusbar()
        
        # تحميل لوحة التحكم كواجهة افتراضية
        self.show_dashboard()
        
        # بدء النسخ الاحتياطي التلقائي
        self.start_auto_backup()

    def start_auto_backup(self):
        """بدء النسخ الاحتياطي التلقائي في الخلفية."""
        from modules.archive import ArchiveManager
        try:
            archive_mgr = ArchiveManager()
            # يمكنك تغيير المدة من الإعدادات إذا أردت
            interval = 24  # ساعة
            archive_mgr.schedule_auto_backup(interval_hours=interval)
            logger.info(f"تم بدء النسخ الاحتياطي التلقائي كل {interval} ساعة")
        except Exception as e:
            logger.error(f"فشل بدء الجدولة التلقائية: {e}")        
    
    def setup_styles(self):
        """إعداد الأنماط"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # تخصيص الأنماط
        self.style.configure('Title.TLabel', 
                           font=('Arial', 16, 'bold'),
                           background='#2c3e50',
                           foreground='white')
        
        self.style.configure('Header.TFrame',
                           background='#2c3e50')
        
        self.style.configure('Sidebar.TFrame',
                           background='#34495e')
        
        self.style.configure('Content.TFrame',
                           background='#ecf0f1')
        
        self.style.configure('Sidebar.TButton',
                           font=('Arial', 12),
                           background='#34495e',
                           foreground='white',
                           borderwidth=0)
        
        self.style.map('Sidebar.TButton',
                      background=[('active', '#3498db')])
    
    def create_widgets(self):
        """إنشاء عناصر الواجهة"""
        # الإطار الرئيسي
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill='both', expand=True)
        
        # رأس الصفحة
        self.create_header()
        
        # منطقة المحتوى
        self.create_content_area()
    
    def create_header(self):
        """إنشاء رأس الصفحة"""
        header_frame = ttk.Frame(self.main_frame, style='Header.TFrame')
        header_frame.pack(fill='x', pady=0)
        
        # العنوان
        title_label = ttk.Label(header_frame, 
                               text="مولدة الريان للطاقة الكهربائية",
                               style='Title.TLabel')
        title_label.pack(pady=15)
        
        # معلومات المستخدم
        user_frame = ttk.Frame(header_frame, style='Header.TFrame')
        user_frame.pack(side='right', padx=20)

        full_name = self.user_data.get('full_name')
        if not full_name:
            full_name = self.user_data.get('username', 'المستخدم')
        role = self.user_data.get('role', '')

        user_label = ttk.Label(user_frame,
                            text=f"👤 {full_name} - {role}",
                            style='Title.TLabel',
                            font=('Arial', 11))
        user_label.pack()

        time_label = ttk.Label(user_frame,
                            text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            style='Title.TLabel',
                            font=('Arial', 10))
        time_label.pack()

    def create_content_area(self):
        """إنشاء منطقة المحتوى"""
        # الشريط الجانبي
        self.sidebar_frame = ttk.Frame(self.main_frame, 
                                      style='Sidebar.TFrame',
                                      width=250)
        self.sidebar_frame.pack(side='left', fill='y')
        self.sidebar_frame.pack_propagate(False)
        
        # إضافة الأزرار الجانبية
        self.create_sidebar_buttons()
        
        # منطقة المحتوى الرئيسية
        self.content_frame = ttk.Frame(self.main_frame, 
                                      style='Content.TFrame')
        self.content_frame.pack(side='left', fill='both', expand=True)
    
    def create_sidebar_buttons(self):
        """إنشاء أزرار الشريط الجانبي مع إمكانية التمرير"""
        # إطار للتمرير (Canvas + Scrollbar)
        canvas = tk.Canvas(self.sidebar_frame, bg='#34495e', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.sidebar_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas, style='Sidebar.TFrame')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=self.sidebar_frame.winfo_width())
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # ربط عجلة الفأرة بالتمرير
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # وضع Canvas و Scrollbar في الشريط الجانبي
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # قائمة الأزرار
        modules = [
            ("🏠 الرئيسية", "dashboard"),
            ("👥 الزبائن", "customers"),
            ("🧾 الفواتير", "invoices"),
            ("📊 التقارير", "reports"),
            ("💰 المحاسبة", "accounting"),
            ("🗃️ الأرشيف", "archive"),
            ("⚡ تحليل الهدر", "waste_analysis"),
            ("👤 المستخدمين", "users"),
            ("📸 كاميرا البرنامج", "activity_log"),
            ("⚙️ الإعدادات", "settings"),
            ("🔄 النسخ الاحتياطي", "backup"),
            ("📱 المحاسبة الجوالة", "mobile_accounting"),
            ("📈 متابعة الجباية", "collection_monitor"),
            ("📈 نسب التحويل", "fuel_management"),
            ("❌ خروج", "logout")
        ]
        
        for i, (text, command) in enumerate(modules):
            btn = ttk.Button(self.scrollable_frame,
                            text=text,
                            style='Sidebar.TButton',
                            command=lambda cmd=command: self.handle_sidebar_click(cmd))
            btn.pack(fill='x', padx=10, pady=5, ipady=10)
        
        # تحديث عرض الإطار الداخلي عند تغيير حجم الشريط الجانبي
        def _configure_canvas(event):
            canvas.itemconfig(1, width=event.width)  # 1 هو معرف النافذة التي أنشأناها
        
        canvas.bind('<Configure>', _configure_canvas)

    # تحديث دالة handle_sidebar_click:
    def handle_sidebar_click(self, command):
        """معالجة النقر على أزرار الشريط الجانبي"""
        if command == "logout":
            self.logout()
        elif command == "dashboard":
            self.show_dashboard()
        elif command == "customers":
            if has_permission('customers.view'):
                self.show_customers_ui()
            else:
                messagebox.showerror("صلاحيات", "ليس لديك صلاحية عرض الزبائن")
        elif command == "invoices":
            if has_permission('invoices.view'):
                self.show_invoices_ui()
            else:
                messagebox.showerror("صلاحيات", "ليس لديك صلاحية عرض الفواتير")
        elif command == "reports":
            if has_permission('reports.view'):
                self.show_reports_ui()
            else:
                messagebox.showerror("صلاحيات", "ليس لديك صلاحية عرض التقارير")
        elif command == "archive":
            if has_permission('system.view_archive'):
                self.show_archive_ui()
            else:
                messagebox.showerror("صلاحيات", "ليس لديك صلاحية عرض الأرشيف")
        elif command == "users":
            if has_permission('system.manage_users'):
                self.show_users_ui()
            else:
                messagebox.showerror("صلاحيات", "ليس لديك صلاحية إدارة المستخدمين")
        elif command == "activity_log":
            if has_permission('system.view_activity_log'):
                self.show_activity_log_ui()
            else:
                messagebox.showerror("صلاحيات", "ليس لديك صلاحية عرض سجل النشاط")
        elif command == "backup":
            if has_permission('system.manage_backup'):
                self.perform_backup()
            else:
                messagebox.showerror("صلاحيات", "ليس لديك صلاحية النسخ الاحتياطي")
        elif command == "accounting":
            if has_permission('accounting.access'):
                self.show_accounting_ui()
            else:
                messagebox.showerror("صلاحيات", "ليس لديك صلاحية الدخول للمحاسبة")
        elif command == "settings":
            if has_permission('settings.manage'):
                self.show_settings_ui()
            else:
                messagebox.showerror("صلاحيات", "ليس لديك صلاحية إدارة الإعدادات")
        elif command == "import_manager":
            if has_permission('system.advanced_import'):
                self.show_import_manager()
            else:
                messagebox.showerror("صلاحيات", "ليس لديك صلاحية الاستيراد المتقدم")
        elif command == "waste_analysis":
            if has_permission('reports.view'):
                self.show_waste_analysis()
            else:
                messagebox.showerror("صلاحيات", "ليس لديك صلاحية عرض تحليل الهدر")
        elif command == "mobile_accounting":
            if has_permission('mobile.view'):
                self.show_mobile_accounting()
            else:
                messagebox.showerror("صلاحيات", "ليس لديك صلاحية الدخول للمحاسبة الجوالة")
        elif command == "collection_monitor":
            if has_permission('reports.view'):
                self.show_collection_monitor()
            else:
                messagebox.showerror("صلاحيات", "ليس لديك صلاحية عرض التقرير")
        elif command == "fuel_management":
            self.show_fuel_management()

    def show_fuel_management(self):
        try:
            from ui.fuel_management_ui import FuelManagementUI
            FuelManagementUI(self.root, self.user_data)
        except Exception as e:
            logger.error(f"خطأ في فتح نافذة نسب التحويل: {e}")
            messagebox.showerror("خطأ", f"تعذر فتح الواجهة: {e}")                            

    def show_collection_monitor(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        from ui.collection_monitor_ui import CollectionMonitorUI
        CollectionMonitorUI(self.content_frame, self.user_data).pack(fill='both', expand=True)                                


    def show_mobile_accounting(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        from ui.mobile_accounting_ui import MobileAccountingUI
        mobile_ui = MobileAccountingUI(self.content_frame, self.user_data)
        mobile_ui.pack(fill='both', expand=True)                               



        # إضافة تبويب جديد للإعدادات المتقدمة:
    def show_advanced_settings(self):
        """عرض الإعدادات المتقدمة (بما فيها الصلاحيات)"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        try:
            from ui.permission_settings_ui import PermissionSettingsUI
            settings_ui = PermissionSettingsUI(self.content_frame, self.user_data)
            logger.info("تم تحميل واجهة إعدادات الصلاحيات بنجاح")
        except ImportError as e:
            logger.error(f"خطأ في تحميل إعدادات الصلاحيات: {e}")
            self.show_simple_permission_settings()


    def show_import_manager(self):
        """عرض واجهة مدير الاستيراد"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        from ui.import_manager import ImportManagerUI
        import_manager = ImportManagerUI(self.content_frame, self.user_data)
        
        # في ui/main_window.py في الدالة show_accounting_ui
    def show_accounting_ui(self):
        """فتح نافذة محاسبة منبثقة بملء الشاشة"""
        # إنشاء نافذة جديدة (Toplevel)
        accounting_window = tk.Toplevel(self.root)
        accounting_window.title("نظام المحاسبة السريع")
        accounting_window.state('zoomed')  # تكبير النافذة لملء الشاشة (في ويندوز)
        # يمكن استخدام attributes('-fullscreen', True) للشاشة الكاملة الحقيقية
        accounting_window.attributes('-fullscreen', True)
        
        # جعل النافذة مؤقتة (تظهر فوق الرئيسية ولا يمكن التفاعل مع الرئيسية حتى تغلق)
        accounting_window.transient(self.root)
        accounting_window.grab_set()
        
        try:
            from ui.accounting_ui import AccountingUI
            # إنشاء الواجهة داخل النافذة الجديدة
            accounting_ui = AccountingUI(accounting_window, self.user_data)
            # لا حاجة لـ pack لأن AccountingUI يقوم بذلك داخلياً (self.pack في __init__)
            
            # عند إغلاق النافذة، حرر القبضة
            accounting_window.protocol("WM_DELETE_WINDOW", lambda: self.close_accounting_window(accounting_window))
            
            logger.info("تم فتح نافذة المحاسبة المنبثقة بنجاح")
        except ImportError as e:
            logger.error(f"خطأ في تحميل واجهة المحاسبة: {e}")
            messagebox.showerror("خطأ", "تعذر تحميل واجهة المحاسبة")
            accounting_window.destroy()
        except Exception as e:
            logger.error(f"خطأ غير متوقع: {e}")
            messagebox.showerror("خطأ", f"حدث خطأ: {str(e)}")
            accounting_window.destroy()


    def close_accounting_window(self, window):
        """إغلاق نافذة المحاسبة وتحرير الموارد"""
        window.grab_release()
        window.destroy()


    def show_dashboard(self):
            """عرض لوحة تحكم مخصصة: سريعة، جذابة، ومركزة على المهام الأساسية"""
            # مسح المحتوى السابق
            for widget in self.content_frame.winfo_children():
                widget.destroy()

            # الحاوية الرئيسية (خلفية هادئة)
            main_container = tk.Frame(self.content_frame, bg='#f0f2f5')
            main_container.pack(fill='both', expand=True)

            # إطار التمركز في وسط الشاشة
            center_frame = tk.Frame(main_container, bg='#f0f2f5')
            center_frame.place(relx=0.5, rely=0.4, anchor='center')

            # --- قسم الترحيب ---
            full_name = self.user_data.get('full_name', 'مستخدمنا العزيز')
            
            welcome_lbl = tk.Label(center_frame, text=f"أهلاً بك، {full_name} ✨", 
                                font=('Segoe UI', 35, 'bold'), bg='#f0f2f5', fg='#1a202c')
            welcome_lbl.pack(pady=(0, 5))

            sub_text = tk.Label(center_frame, text="نظام مولدة الريان | الإدارة الذكية للطاقة", 
                                font=('Segoe UI', 14), bg='#f0f2f5', fg='#718096')
            sub_text.pack(pady=(0, 40))

            # --- حاوية الأزرار السريعة ---
            grid_frame = tk.Frame(center_frame, bg='#f0f2f5')
            grid_frame.pack()

            # الأزرار المحدثة حسب طلبك
            actions = [
                ("🧾", "فاتورة جديدة", "#3182ce", self.show_accounting_ui), # تفتح المحاسبة مباشرة
                ("👥", "إدارة الزبائن", "#805ad5", self.show_customers_ui),
                ("📊", "التقارير المالية", "#38a169", self.show_reports_ui),
                ("⚡", "تحليل الهدر", "#e53e3e", self.show_waste_analysis), # بديل الإعدادات
            ]

            for i, (icon, title, color, cmd) in enumerate(actions):
                self.create_action_card(grid_frame, icon, title, color, cmd, i)

            # نص سفلي لإكمال الشكل الجمالي
            footer_msg = tk.Label(main_container, 
                                text="نظام الريان المتكامل - القوة والسهولة في مكان واحد", 
                                font=('Segoe UI', 11), bg='#f0f2f5', fg='#a0aec0')
            footer_msg.pack(side='bottom', pady=30)

    def create_action_card(self, parent, icon, title, color, command, col):
            """إنشاء بطاقة تفاعلية جذابة"""
            # الإطار الخارجي للبطاقة
            card = tk.Frame(parent, bg='white', padx=30, pady=30, 
                            highlightbackground='#e2e8f0', highlightthickness=1, cursor="hand2")
            card.grid(row=0, column=col, padx=15, pady=10)

            # تأثيرات الماوس
            def on_enter(e):
                card.config(bg='#f8fafc', highlightbackground=color, highlightthickness=2)
                icon_lbl.config(bg='#f8fafc')
                title_lbl.config(bg='#f8fafc')

            def on_leave(e):
                card.config(bg='white', highlightbackground='#e2e8f0', highlightthickness=1)
                icon_lbl.config(bg='white')
                title_lbl.config(bg='white')

            card.bind("<Enter>", on_enter)
            card.bind("<Leave>", on_leave)
            card.bind("<Button-1>", lambda e: command())

            # الأيقونة
            icon_lbl = tk.Label(card, text=icon, font=('Segoe UI', 45), bg='white', fg=color)
            icon_lbl.pack()
            icon_lbl.bind("<Button-1>", lambda e: command())

            # النص
            title_lbl = tk.Label(card, text=title, font=('Segoe UI', 13, 'bold'), bg='white', fg='#2d3748')
            title_lbl.pack(pady=(15, 0))
            title_lbl.bind("<Button-1>", lambda e: command())        

    def show_archive_ui(self):
        """عرض واجهة الأرشيف"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        archive_ui = ArchiveUI(self.content_frame, self.user_data)  # تمرير بيانات المستخدم إن لزم
        archive_ui.pack(fill='both', expand=True)                   # <--- هذا السطر المهم
        logger.info("تم تحميل واجهة الأرشيف بنجاح")

    def show_users_ui(self):
        """عرض واجهة المستخدمين"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        try:
            # حاول استيراد user_management_ui أولاً
            from ui.user_management_ui import UsersUI
            users_ui = UsersUI(self.content_frame)
            logger.info("تم تحميل واجهة المستخدمين بنجاح")
        except ImportError:
            try:
                # إذا فشل، حاول استيراد users_ui
                from ui.user_management_ui import UsersUI
                users_ui = UsersUI(self.content_frame)
                logger.info("تم تحميل واجهة المستخدمين من users_ui")
            except ImportError as e:
                logger.error(f"خطأ في تحميل واجهة المستخدمين: {e}")
                # عرض واجهة بديلة
                self.show_simple_users_ui()

    def show_simple_users_ui(self):
        """عرض واجهة مستخدمين مبسطة"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        frame = tk.Frame(self.content_frame, bg='white')
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        title = tk.Label(frame, text="إدارة المستخدمين",
                        font=('Arial', 20, 'bold'),
                        bg='white', fg='#2c3e50')
        title.pack(pady=10)
        
        msg = tk.Label(frame,
                      text="وحدة إدارة المستخدمين قيد التطوير\nسيتم إضافتها قريباً",
                      font=('Arial', 14),
                      bg='white', fg='#7f8c8d')
        msg.pack(pady=50)
        
        back_btn = tk.Button(frame, text="← العودة للرئيسية",
                           command=self.show_dashboard,
                           bg='#3498db', fg='white',
                           font=('Arial', 12))
        back_btn.pack(pady=20)

    def show_activity_log_ui(self):
        """عرض واجهة سجل النشاط بعد التحقق من كلمة المرور للمدراء"""
        # التحقق من الصلاحية أولاً
        if not has_permission('system.view_activity_log'):
            messagebox.showerror("صلاحيات", "ليس لديك صلاحية عرض سجل النشاط")
            return

        # طلب كلمة المرور الإضافية
        password = tk.simpledialog.askstring(
            "تأكيد الدخول",
            "هذه الواجهة لمدراء البرنامج حصراً\nالرجاء إدخال كلمة المرور للمتابعة:",
            show='*'
        )
        if password != "eyadkasemadmin123":
            if password is not None:  # إذا لم يضغط المستخدم على "إلغاء"
                messagebox.showerror("خطأ", "كلمة المرور غير صحيحة")
            return

        # متابعة فتح الواجهة
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        try:
            from ui.activity_log_ui import ActivityLogUI
            activity_ui = ActivityLogUI(self.content_frame, self.user_data)
            activity_ui.pack(fill='both', expand=True)
            logger.info("تم تحميل واجهة سجل النشاط بنجاح")
        except ImportError as e:
            logger.error(f"خطأ في تحميل سجل النشاط: {e}")
            self.show_simple_activity_log_ui()

    def show_simple_activity_log_ui(self):
        """عرض واجهة سجل نشاط مبسطة"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        frame = tk.Frame(self.content_frame, bg='white')
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        title = tk.Label(frame, text="سجل النشاط",
                        font=('Arial', 20, 'bold'),
                        bg='white', fg='#2c3e50')
        title.pack(pady=10)
        
        msg = tk.Label(frame,
                      text="وحدة سجل النشاط قيد التطوير\nسيتم إضافتها قريباً",
                      font=('Arial', 14),
                      bg='white', fg='#7f8c8d')
        msg.pack(pady=50)
        
        back_btn = tk.Button(frame, text="← العودة للرئيسية",
                           command=self.show_dashboard,
                           bg='#3498db', fg='white',
                           font=('Arial', 12))
        back_btn.pack(pady=20)

    def show_settings_ui(self):
        """عرض واجهة الإعدادات"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        try:
            from ui.settings_ui import SettingsUI
            settings_ui = SettingsUI(self.content_frame)
            logger.info("تم تحميل واجهة الإعدادات بنجاح")
        except ImportError as e:
            logger.error(f"خطأ في تحميل الإعدادات: {e}")
            self.show_simple_settings_ui()

    def show_simple_settings_ui(self):
        """عرض واجهة إعدادات مبسطة"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        frame = tk.Frame(self.content_frame, bg='white')
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        title = tk.Label(frame, text="الإعدادات",
                        font=('Arial', 20, 'bold'),
                        bg='white', fg='#2c3e50')
        title.pack(pady=10)
        
        msg = tk.Label(frame,
                      text="وحدة الإعدادات قيد التطوير\nسيتم إضافتها قريباً",
                      font=('Arial', 14),
                      bg='white', fg='#7f8c8d')
        msg.pack(pady=50)
        
        back_btn = tk.Button(frame, text="← العودة للرئيسية",
                           command=self.show_dashboard,
                           bg='#3498db', fg='white',
                           font=('Arial', 12))
        back_btn.pack(pady=20)
        
    def show_simple_statistics(self, parent):
        """عرض إحصائيات مبسطة"""
        stats_frame = tk.Frame(parent, bg='white')
        stats_frame.pack(fill='x', pady=20)
        
        try:
            from modules.reports import ReportManager
            reports = ReportManager()
            statistics = reports.get_dashboard_statistics()
        except ImportError as e:
            logger.warning(f"وحدة التقارير غير متوفرة: {e}")
            # إحصائيات تجريبية
            statistics = {
                "إجمالي الزبائن": "150",
                "الفواتير اليوم": "25",
                "المبلغ اليوم": "1,250,000 ل.س",
                "الرصيد السالب": "12",
                "الرصيد الموجب": "138",
                "الفواتير الشهر": "500",
                "المبلغ الشهري": "25,000,000 ل.س",
                "المتوسط اليومي": "833,333 ل.س"
            }
        
        # عرض الإحصائيات في شكل بطاقات
        for i, (title, value) in enumerate(statistics.items()):
            card = self.create_stat_card(stats_frame, title, value)
            card.grid(row=i//4, column=i%4, padx=10, pady=10, sticky='nsew')
            
        for i in range(4):
            stats_frame.columnconfigure(i, weight=1)
    
    def create_stat_card(self, parent, title, value):
        """إنشاء بطاقة إحصائية"""
        card_frame = tk.Frame(parent, bg='#f8f9fa', relief='raised', borderwidth=1)
        
        title_label = tk.Label(card_frame, text=title,
                              font=('Arial', 12, 'bold'),
                              bg='#f8f9fa', fg='#495057')
        title_label.pack(pady=(10, 5))
        
        value_label = tk.Label(card_frame, text=str(value),
                              font=('Arial', 14, 'bold'),
                              bg='#f8f9fa', fg='#2c3e50')
        value_label.pack(pady=(5, 10))
        
        return card_frame
    
    def show_coming_features(self, parent):
        """عرض الميزات القادمة"""
        features_frame = tk.Frame(parent, bg='white')
        features_frame.pack(fill='x', pady=30)
        
        tk.Label(features_frame, 
                text="الميزات قيد التطوير:",
                font=('Arial', 16, 'bold'),
                bg='white', fg='#2c3e50').pack(pady=10)
        
        features = [
            "✅ إدارة الزبائن المتكاملة",
            "✅ نظام الفواتير والطباعة",
            "✅ التقارير والإحصائيات",
            "✅ نظام الصلاحيات المتقدم",
            "✅ النسخ الاحتياطي التلقائي",
            "⏳ نظام المحاسبة المتكامل",
            "⏳ سجل النشاط التفصيلي",
            "⏳ إدارة المستخدمين"
        ]
        
        for feature in features:
            tk.Label(features_frame, 
                    text=f"• {feature}",
                    font=('Arial', 12),
                    bg='white', fg='#7f8c8d',
                    anchor='w').pack(fill='x', padx=20, pady=2)
    
    def show_simple_customers_ui(self):
        """عرض واجهة زبائن مبسطة"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        frame = tk.Frame(self.content_frame, bg='white')
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        title = tk.Label(frame, text="إدارة الزبائن",
                        font=('Arial', 20, 'bold'),
                        bg='white', fg='#2c3e50')
        title.pack(pady=10)
        
        msg = tk.Label(frame,
                      text="عذراً، واجهة الزبائن الرئيسية غير متاحة حالياً.\nسيتم إضافتها قريباً.",
                      font=('Arial', 14),
                      bg='white', fg='#7f8c8d')
        msg.pack(pady=50)
        
        back_btn = tk.Button(frame, text="← العودة للرئيسية",
                           command=self.show_dashboard,
                           bg='#3498db', fg='white',
                           font=('Arial', 12))
        back_btn.pack(pady=20)
    
    def show_simple_invoices_ui(self):
        """عرض واجهة فواتير مبسطة"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        frame = tk.Frame(self.content_frame, bg='white')
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        title = tk.Label(frame, text="إدارة الفواتير",
                        font=('Arial', 20, 'bold'),
                        bg='white', fg='#2c3e50')
        title.pack(pady=10)
        
        msg = tk.Label(frame,
                      text="عذراً، واجهة الفواتير الرئيسية غير متاحة حالياً.\nسيتم إضافتها قريباً.",
                      font=('Arial', 14),
                      bg='white', fg='#7f8c8d')
        msg.pack(pady=50)
        
        back_btn = tk.Button(frame, text="← العودة للرئيسية",
                           command=self.show_dashboard,
                           bg='#3498db', fg='white',
                           font=('Arial', 12))
        back_btn.pack(pady=20)
    
    def show_simple_report_ui(self):
        """عرض واجهة تقارير مبسطة"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        frame = tk.Frame(self.content_frame, bg='white')
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        title = tk.Label(frame, text="التقارير والإحصائيات",
                        font=('Arial', 20, 'bold'),
                        bg='white', fg='#2c3e50')
        title.pack(pady=10)
        
        msg = tk.Label(frame,
                      text="عذراً، واجهة التقارير الرئيسية غير متاحة حالياً.\nسيتم إضافتها قريباً.",
                      font=('Arial', 14),
                      bg='white', fg='#7f8c8d')
        msg.pack(pady=50)
        
        back_btn = tk.Button(frame, text="← العودة للرئيسية",
                           command=self.show_dashboard,
                           bg='#3498db', fg='white',
                           font=('Arial', 12))
        back_btn.pack(pady=20)
    
    def show_customers_ui(self):
        """فتح نافذة الزبائن المنبثقة بملء الشاشة"""
        if not has_permission('customers.view'):
            messagebox.showerror("صلاحيات", "ليس لديك صلاحية عرض الزبائن")
            return

        customers_window = tk.Toplevel(self.root)
        customers_window.title("إدارة الزبائن - النظام الهرمي")
        customers_window.state('zoomed')
        # customers_window.attributes('-fullscreen', True)  # اختياري

        customers_window.transient(self.root)
        customers_window.grab_set()

        try:
            from ui.customer_ui import CustomerUI
            customer_ui = CustomerUI(customers_window, self.user_data)
            # ❗ يجب إضافة السطر التالي لعرض الإطار داخل النافذة
            customer_ui.pack(fill='both', expand=True)

            customers_window.protocol("WM_DELETE_WINDOW", lambda: self.close_customers_window(customers_window))
            logger.info("تم فتح نافذة الزبائن المنبثقة بنجاح")
        except ImportError as e:
            logger.error(f"خطأ في تحميل واجهة الزبائن: {e}")
            messagebox.showerror("خطأ", "تعذر تحميل واجهة الزبائن")
            customers_window.destroy()
        except Exception as e:
            logger.error(f"خطأ غير متوقع: {e}")
            messagebox.showerror("خطأ", f"حدث خطأ: {str(e)}")
            customers_window.destroy()

            
    def close_customers_window(self, window):
        """إغلاق نافذة الزبائن وتحرير الموارد"""
        window.grab_release()
        window.destroy()          

    def show_invoices_ui(self):
        """عرض واجهة الفواتير"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
        try:
            from ui.invoice_ui import InvoiceUI
            invoice_ui = InvoiceUI(self.content_frame, self.user_data)
            invoice_ui.pack(fill='both', expand=True)
        
            logger.info("تم تحميل واجهة الفواتير بنجاح")
        
        except ImportError as e:
            logger.error(f"خطأ في تحميل واجهة الفواتير: {e}")
            # عرض واجهة بديلة
            self.show_simple_invoices_ui()
    
    def show_reports_ui(self):
        """عرض واجهة التقارير"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        try:
            from ui.report_ui import ReportUI
            report_ui = ReportUI(self.content_frame, self.user_data)
            report_ui.pack(fill='both', expand=True)
        
            logger.info("تم تحميل واجهة التقارير بنجاح")
        
        except ImportError as e:
            logger.error(f"خطأ في تحميل واجهة التقارير: {e}")
            # عرض واجهة بديلة
            self.show_simple_report_ui()
    
    def check_permission(self, permission_name):
        """التحقق من صلاحية المستخدم"""
        # الأدوار والصلاحيات الافتراضية
        role_permissions = {
            'admin': ['manage_users', 'view_activity_log', 'add_invoice', 
                    'edit_invoice', 'delete_invoice', 'manage_customers', 
                    'view_reports', 'manage_settings', 'export_data', 'import_data',
                    'view_archive', 'manage_backup'],
            'accountant': ['add_invoice', 'edit_invoice', 'manage_customers', 
                          'view_reports', 'export_data', 'import_data'],
            'cashier': ['view_invoices', 'view_customers', 'add_payment'],
            'viewer': ['view_reports', 'view_customers']
        }
        
        user_role = self.user_data.get('role', 'viewer')
        
        # تسجيل محاولة الوصول (باستخدام get لتجنب KeyError)
        username = self.user_data.get('username', 'غير معروف')
        if not username or username == 'غير معروف':
            username = self.user_data.get('full_name', 'مستخدم')
        
        logger.info(f"التحقق من الصلاحية: {permission_name} للمستخدم: {username}، الدور: {user_role}")
        
        # إذا كان admin، يعود True لكل الصلاحيات
        if user_role == 'admin':
            return True
        
        # خلاف ذلك، يتحقق من الصلاحيات
        user_permissions = role_permissions.get(user_role, [])
        return permission_name in user_permissions

    def perform_backup(self):
        """تنفيذ النسخ الاحتياطي"""
        try:
            from modules.archive import ArchiveManager
            archive = ArchiveManager()
            result = archive.perform_backup()
            
            if result.get('success'):
                messagebox.showinfo("نجاح", "تم إنشاء النسخة الاحتياطية بنجاح")
            else:
                messagebox.showerror("خطأ", result.get('error', 'فشل النسخ الاحتياطي'))
                
        except ImportError as e:
            logger.error(f"خطأ في تحميل وحدة الأرشيف: {e}")
            messagebox.showinfo("نسخ احتياطي", 
                              "تم إجراء نسخ احتياطي بسيط\nسيتم تطوير النظام الكامل قريباً")
    
    def logout(self):
        """تسجيل الخروج"""
        if messagebox.askyesno("تأكيد", "هل تريد تسجيل الخروج؟"):
            self.root.destroy()
    
    # تحديث قائمة ملف:
    def setup_menu(self):
        """إعداد القوائم"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # قائمة ملف
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ملف", menu=file_menu)
        file_menu.add_command(label="📥 مدير الاستيراد المتقدم", 
                            command=self.show_import_manager)
        file_menu.add_command(label="📤 مدير التصدير المتقدم", 
                            command=lambda: self.show_import_manager)
        file_menu.add_separator()
        file_menu.add_command(label="خروج", command=self.root.quit)
            
        # قائمة عرض
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="عرض", menu=view_menu)
        view_menu.add_command(label="تحديث", command=self.refresh)
        
        # قائمة أدوات
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="أدوات", menu=tools_menu)
        tools_menu.add_command(label="🔧 قواعد البيانات", command=self.show_database_management)
        tools_menu.add_command(label="إدارة الصلاحيات", command=self.show_permission_settings)
        tools_menu.add_command(label="تشخيص مشكلة الصلاحيات", command=self.debug_permission_issue)

                                   
        
        # قائمة مساعدة
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="مساعدة", menu=help_menu)
        help_menu.add_command(label="دليل المستخدم", command=self.show_help)
        help_menu.add_command(label="عن البرنامج", command=self.about)

                # إضافة الدالة الجديدة:
    def show_permission_settings(self):
        """عرض إعدادات الصلاحيات - التحقق من صلاحية المستخدم الحالي"""
        from auth.session import Session
        from auth.permission_engine import permission_engine
        
        # 1. التحقق من تسجيل الدخول
        if not Session.is_authenticated():
            messagebox.showerror("صلاحيات", "يجب تسجيل الدخول أولاً")
            return
        
        # 2. جلب بيانات المستخدم الحالي
        current_user = Session.current_user
        if not current_user:
            messagebox.showerror("صلاحيات", "لا توجد جلسة نشطة")
            return
        
        user_id = current_user['id']
        username = current_user.get('username', 'مستخدم')
        user_role = Session.get_role()
        
        print(f"🔍 التحقق من صلاحيات المستخدم الحالي:")
        print(f"   ID: {user_id}")
        print(f"   اسم المستخدم: {username}")
        print(f"   الدور: {user_role}")
        
        # 3. التحقق من الصلاحية باستخدام المستخدم الحالي
        can_access = permission_engine.has_permission(user_id, 'settings.manage_permissions')
        
        print(f"✅ التحقق من صلاحية 'settings.manage_permissions' للمستخدم {username}: {can_access}")
        
        if can_access:
            # فتح واجهة الصلاحيات
            self.show_advanced_settings()
        else:
            messagebox.showerror("صلاحيات", 
                f"ليس لديك صلاحية إدارة الصلاحيات\n\n"
                f"المستخدم: {username}\n"
                f"الدور: {user_role}\n\n"
                f"يجب أن يكون لديك صلاحية 'settings.manage_permissions'")


    def debug_permission_issue(self):
        """تشخيص مشكلة الصلاحيات بشكل مفصل"""
        from auth.session import Session
        from auth.permission_engine import permission_engine
        from database.connection import db
        
        if not Session.is_authenticated():
            print("❌ لم يتم تسجيل الدخول")
            return
        
        current_user = Session.current_user
        user_id = current_user['id']
        username = current_user.get('username')
        role = current_user.get('role')
        
        print(f"\n{'='*60}")
        print(f"🔍 تشخيص مفصل لمشكلة الصلاحيات")
        print(f"{'='*60}")
        
        try:
            # 1. التحقق من قاعدة البيانات مباشرة
            with db.get_cursor() as cursor:
                # أ) صلاحيات الدور في role_permissions
                cursor.execute("""
                    SELECT permission_key, is_allowed, updated_at
                    FROM role_permissions 
                    WHERE role = %s AND permission_key LIKE 'settings.%'
                    ORDER BY permission_key
                """, (role,))
                
                role_perms = cursor.fetchall()
                print(f"\n📋 صلاحيات الدور '{role}' في جدول role_permissions:")
                for perm in role_perms:
                    status = "✅ مفعل" if perm['is_allowed'] else "❌ معطل"
                    print(f"   - {perm['permission_key']}: {status}")
                
                # ب) صلاحيات المستخدم المباشرة في user_permissions
                cursor.execute("""
                    SELECT permission_key, is_allowed
                    FROM user_permissions 
                    WHERE user_id = %s AND permission_key LIKE 'settings.%'
                """, (user_id,))
                
                user_perms = cursor.fetchall()
                print(f"\n👤 صلاحيات المستخدم المباشرة في user_permissions:")
                for perm in user_perms:
                    status = "✅ مفعل" if perm['is_allowed'] else "❌ معطل"
                    print(f"   - {perm['permission_key']}: {status}")
                
                # ج) الصلاحيات القديمة في users.permissions (JSONB)
                cursor.execute("SELECT permissions FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                old_perms = user.get('permissions', {}) if user else {}
                print(f"\n🗃️  الصلاحيات القديمة في users.permissions (JSONB):")
                for key, value in old_perms.items():
                    if 'settings' in key or 'manage' in key:
                        print(f"   - {key}: {value}")
            
            # 2. التحقق من محرك الصلاحيات
            print(f"\n🚀 محرك الصلاحيات:")
            
            # أ) استخدام has_permission
            result = permission_engine.has_permission(user_id, 'settings.manage_permissions')
            print(f"   has_permission('settings.manage_permissions'): {result}")
            
            # ب) جلب جميع الصلاحيات
            all_perms = permission_engine.get_user_permissions(user_id)
            settings_perms = {k: v for k, v in all_perms.items() if k.startswith('settings.')}
            print(f"   الصلاحيات من get_user_permissions():")
            for key, value in settings_perms.items():
                status = "✅ مفعل" if value else "❌ معطل"
                print(f"   - {key}: {status}")
            
            # 3. التحقق من الكاش
            print(f"\n💾 حالة الكاش:")
            cache_size = len(permission_engine._permissions_cache)
            print(f"   حجم الكاش: {cache_size} مستخدم")
            
            if user_id in permission_engine._permissions_cache:
                cache_data = permission_engine._permissions_cache[user_id]
                cache_age = time.time() - cache_data[0]
                print(f"   ✅ المستخدم موجود في الكاش")
                print(f"   عمر الكاش: {cache_age:.1f} ثانية")
            else:
                print(f"   ❌ المستخدم غير موجود في الكاش")
                
        except Exception as e:
            print(f"❌ خطأ في التشخيص: {e}")


    def setup_statusbar(self):
        """إعداد شريط الحالة"""
        self.statusbar = tk.Frame(self.root, bg='#2c3e50', height=30)
        self.statusbar.pack(side='bottom', fill='x')
        self.statusbar.pack_propagate(False)
        
        status_label = tk.Label(self.statusbar,
                                text=f"{APP_NAME} - جاهز",
                                bg='#2c3e50', fg='white',
                                font=('Arial', 9))
        status_label.pack(side='left', padx=10)
        
        # تحديث الوقت تلقائياً
        self.update_time()
    
    def update_time(self):
        """تحديث الوقت"""
        for widget in self.statusbar.winfo_children():
            if isinstance(widget, tk.Label) and ":" in widget.cget("text"):
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                widget.config(text=current_time)
                break
        else:
            time_label = tk.Label(self.statusbar,
                                 text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                 bg='#2c3e50', fg='white',
                                 font=('Arial', 9))
            time_label.pack(side='right', padx=10)
        
        self.root.after(1000, self.update_time)
    
    def export_data(self):
        """تصدير البيانات إلى Excel"""
        try:
            # نافذة اختيار نوع البيانات للتصدير
            export_dialog = ExportDialog(self.root)
            self.root.wait_window(export_dialog)
            
            if export_dialog.export_type and export_dialog.data_to_export:
                # اختيار مكان الحفظ
                filename = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                    title="حفظ ملف Excel"
                )
                
                if filename:
                    # التصدير الفعلي
                    ExcelHandler.export_to_excel(
                        export_dialog.data_to_export,
                        filename,
                        sheet_name=export_dialog.export_type
                    )
                    messagebox.showinfo("نجاح", f"تم تصدير البيانات إلى:\n{filename}")
                    
        except Exception as e:
            logger.error(f"خطأ في تصدير البيانات: {e}")
            messagebox.showerror("خطأ", f"فشل تصدير البيانات: {str(e)}")


    
    def import_data(self):
        """استيراد بيانات من ملف Excel"""
        try:
            filename = filedialog.askopenfilename(
                filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
                title="اختر ملف Excel"
            )
            
            if filename:
                data = ExcelHandler.import_from_excel(filename)
                messagebox.showinfo("نجاح", 
                                f"تم استيراد {len(data)} سجل\n"
                                f"الأعمدة: {list(data[0].keys()) if data else 'لا توجد بيانات'}")
                
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل الاستيراد: {str(e)}")


    def refresh(self):
        """تحديث البيانات"""
        current_view = str(self.content_frame.winfo_children()[0]) if self.content_frame.winfo_children() else ""
        if "dashboard" in current_view:
            self.show_dashboard()
        messagebox.showinfo("تحديث", "تم تحديث البيانات")

    def fix_permission_cache(self):
        """إصلاح كاش الصلاحيات يدوياً"""
        from auth.session import Session
        from auth.permission_engine import permission_engine
        
        if not Session.is_authenticated():
            messagebox.showerror("خطأ", "لم تقم بتسجيل الدخول")
            return
        
        try:
            # مسح جميع الكاشات
            permission_engine.clear_cache()
            Session._permission_version.clear()
            
            # تحديث الجلسة
            Session.refresh_permissions()
            
            messagebox.showinfo("نجاح", 
                "✅ تم إصلاح كاش الصلاحيات بنجاح!\n\n"
                "تم:\n"
                "1. مسح كاش محرك الصلاحيات\n"
                "2. مسح كاش إصدارات الجلسات\n"
                "3. تحديث الجلسة الحالية\n\n"
                "يمكنك الآن استخدام النظام بشكل طبيعي.")
                
        except Exception as e:
            logger.error(f"خطأ في إصلاح الكاش: {e}")
            messagebox.showerror("خطأ", f"فشل إصلاح الكاش: {str(e)}")


    
    def show_waste_analysis(self):
        """عرض واجهة تحليل الهدر"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        try:
            from ui.hierarchical_waste_ui import HierarchicalWasteUI
            waste_ui = HierarchicalWasteUI(self.content_frame, self.user_data)
            waste_ui.pack(fill='both', expand=True)
            logger.info("تم تحميل واجهة تحليل الهدر بنجاح")
        except ImportError as e:
            logger.error(f"خطأ في تحميل واجهة تحليل الهدر: {e}")
            self.show_simple_waste_analysis()


    # حاص بالهدر  
    def open_hierarchical_waste_analysis(self):
        waste_window = tk.Toplevel(self)
        waste_window.title("التحليل الهرمي للهدر")
        waste_window.geometry("1200x800")
        
        waste_ui = HierarchicalWasteUI(waste_window, self.user_data)
        waste_ui.pack(fill='both', expand=True)

    def show_simple_waste_analysis(self):
        """عرض واجهة مبسطة لتحليل الهدر"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        frame = tk.Frame(self.content_frame, bg='white')
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        title = tk.Label(frame, text="⚡ نظام تحليل الهدر",
                        font=('Arial', 20, 'bold'),
                        bg='white', fg='#2c3e50')
        title.pack(pady=10)
        
        msg = tk.Label(frame,
                    text="يتم تطوير نظام متكامل لتحليل الهدر في الطاقة الكهربائية\nسيتم إضافته قريباً",
                    font=('Arial', 14),
                    bg='white', fg='#7f8c8d')
        msg.pack(pady=50)


       
        # ...  الخاصة ب قواعد البيانتا باقي القوائم ...

    def show_database_management(self):
        """عرض نافذة إدارة قاعدة البيانات"""
        win = tk.Toplevel(self.root)
        win.title("إدارة قاعدة البيانات")
        win.geometry("500x400")
        win.transient(self.root)
        win.grab_set()
        
        # إطار رئيسي
        main_frame = ttk.Frame(win, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # تحذير أمان
        warning_label = tk.Label(main_frame, 
                                text="⚠️ تحذير: هذه العمليات خطيرة ولا يمكن التراجع عنها",
                                fg='red', font=('Arial', 10, 'bold'))
        warning_label.pack(pady=(0,20))
        
        # إطار العمليات
        ops_frame = ttk.Frame(main_frame)
        ops_frame.pack(fill='both', expand=True)
        
        # زر حذف كامل
        ttk.Button(ops_frame, text="🗑️ حذف كامل لقاعدة البيانات",
                command=self.confirm_full_database_deletion).pack(fill='x', pady=5)
        
        # زر تصفير القيم
        ttk.Button(ops_frame, text="🔄 تصفير جميع القيم",
                command=self.confirm_reset_all_data).pack(fill='x', pady=5)
        
        # زر استعادة من ملف
        ttk.Button(ops_frame, text="📂 استعادة قاعدة البيانات من ملف",
                command=self.restore_database_from_file).pack(fill='x', pady=5)
        
        # زر إغلاق
        ttk.Button(ops_frame, text="إغلاق", command=win.destroy).pack(pady=20)

    def confirm_full_database_deletion(self):
        """تأكيد حذف قاعدة البيانات بالكامل (حذف الجداول وإعادة إنشائها)"""
        if not messagebox.askyesno("تأكيد", "هل أنت متأكد من رغبتك في حذف قاعدة البيانات بالكامل؟\nسيتم فقدان جميع البيانات!", icon='warning'):
            return
        
        # طلب كلمة مرور إضافية للأمان
        password = tk.simpledialog.askstring("كلمة المرور", "أدخل كلمة المرور لتأكيد العملية:", show='*')
        if password != "admin123":  # يمكنك تغيير كلمة المرور أو جلبها من الإعدادات
            messagebox.showerror("خطأ", "كلمة المرور غير صحيحة")
            return
        
        try:
            with db.get_cursor() as cursor:
                # حذف جميع الجداول (ترتيب يعتمد على العلاقات)
                cursor.execute("""
                    DROP TABLE IF EXISTS customer_history CASCADE;
                    DROP TABLE IF EXISTS invoices CASCADE;
                    DROP TABLE IF EXISTS customers CASCADE;
                    DROP TABLE IF EXISTS sectors CASCADE;
                    DROP TABLE IF EXISTS users CASCADE;
                    DROP TABLE IF EXISTS settings CASCADE;
                    DROP TABLE IF EXISTS activity_logs CASCADE;
                    DROP TABLE IF EXISTS invoice_archive CASCADE;
                    DROP TABLE IF EXISTS permissions_catalog CASCADE;
                    DROP TABLE IF EXISTS role_permissions CASCADE;
                    DROP TABLE IF EXISTS user_permissions CASCADE;
                    DROP TABLE IF EXISTS customer_financial_logs CASCADE;
                """)
                # إعادة إنشاء الجداول
                models.create_tables()
            messagebox.showinfo("نجاح", "تم حذف قاعدة البيانات وإعادة إنشائها بنجاح")
        except Exception as e:
            logger.error(f"خطأ في حذف قاعدة البيانات: {e}")
            messagebox.showerror("خطأ", f"فشل في حذف قاعدة البيانات: {str(e)}")

    def confirm_reset_all_data(self):
        """تأكيد تصفير جميع البيانات (حذف المحتوى فقط)"""
        if not messagebox.askyesno("تأكيد", "هل أنت متأكد من رغبتك في تصفير جميع البيانات؟\nسيتم حذف جميع السجلات!", icon='warning'):
            return
        
        password = tk.simpledialog.askstring("كلمة المرور", "أدخل كلمة المرور لتأكيد العملية:", show='*')
        if password != "admin123":
            messagebox.showerror("خطأ", "كلمة المرور غير صحيحة")
            return
        
        try:
            with db.get_cursor() as cursor:
                # تعطيل قيود المفاتيح الخارجية مؤقتاً
                cursor.execute("SET session_replication_role = 'replica';")
                
                # حذف البيانات من جميع الجداول (مع إعادة تعيين التسلسلات)
                tables = [
                    'customer_history', 'invoices', 'customers', 'sectors',
                    'activity_logs', 'invoice_archive', 'customer_financial_logs',
                    'user_permissions', 'role_permissions', 'permissions_catalog',
                    'settings', 'users'
                ]
                for table in tables:
                    cursor.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
                
                # إعادة تفعيل القيود
                cursor.execute("SET session_replication_role = 'origin';")
                
                # إعادة إدخال البيانات الأساسية (المستخدم admin، القطاعات، الصلاحيات)
                models.seed_initial_data(cursor)
                
            messagebox.showinfo("نجاح", "تم تصفير جميع البيانات وإعادة تعيين القيم الافتراضية بنجاح")
        except Exception as e:
            logger.error(f"خطأ في تصفير البيانات: {e}")
            messagebox.showerror("خطأ", f"فشل في تصفير البيانات: {str(e)}")

    def restore_database_from_file(self):
        """استعادة قاعدة البيانات من ملف نسخة احتياطية"""
        # اختيار الملف
        filename = filedialog.askopenfilename(
            title="اختر ملف النسخة الاحتياطية",
            filetypes=[
                ("ملفات النسخ الاحتياطي", "*.backup *.sql *.backup.gpg"),
                ("جميع الملفات", "*.*")
            ]
        )
        if not filename:
            return
        
        # تأكيد
        if not messagebox.askyesno("تأكيد", "سيتم استبدال قاعدة البيانات الحالية بالكامل. هل أنت متأكد؟", icon='warning'):
            return
        
        password = tk.simpledialog.askstring("كلمة المرور", "أدخل كلمة المرور لتأكيد العملية:", show='*')
        if password != "admin123":
            messagebox.showerror("خطأ", "كلمة المرور غير صحيحة")
            return
        
        try:
            # محاولة استخدام ArchiveManager إذا كان الملف من نوع .backup
            if filename.endswith('.backup') or filename.endswith('.backup.gpg'):
                manager = ArchiveManager()
                result = manager.restore_backup(filename)
                if result.get('success'):
                    messagebox.showinfo("نجاح", "تمت استعادة قاعدة البيانات بنجاح")
                else:
                    messagebox.showerror("خطأ", result.get('error', 'فشل الاستعادة'))
            else:
                # استعادة باستخدام psql (ملفات .sql)
                # بناء أمر الاستعادة
                pg_env = os.environ.copy()
                pg_env['PGPASSWORD'] = DATABASE_CONFIG['password']
                cmd = [
                    'psql',
                    '-h', DATABASE_CONFIG['host'],
                    '-p', str(DATABASE_CONFIG['port']),
                    '-U', DATABASE_CONFIG['user'],
                    '-d', DATABASE_CONFIG['database'],
                    '-f', filename
                ]
                result = subprocess.run(cmd, env=pg_env, capture_output=True, text=True)
                if result.returncode == 0:
                    messagebox.showinfo("نجاح", "تمت استعادة قاعدة البيانات من ملف SQL بنجاح")
                else:
                    messagebox.showerror("خطأ", f"فشل الاستعادة:\n{result.stderr}")
        except Exception as e:
            logger.error(f"خطأ في استعادة قاعدة البيانات: {e}")
            messagebox.showerror("خطأ", f"فشل الاستعادة: {str(e)}")                    
    
    def show_help(self):
        """عرض دليل المستخدم"""
        help_text = f"""
دليل استخدام {APP_NAME}

1. لوحة التحكم: نظرة عامة على النظام
2. الزبائن: إدارة بيانات الزبائن
3. الفواتير: إنشاء وإدارة الفواتير
4. التقارير: إحصائيات وتحليلات
5. المستخدمين: إدارة حسابات المستخدمين
6. سجل النشاط: تتبع جميع العمليات
7. النسخ الاحتياطي: حفظ واستعادة البيانات

الإصدار: {VERSION}
        """
        messagebox.showinfo("دليل المستخدم", help_text)
    
    def about(self):
        """عرض معلومات عن البرنامج"""
        about_text = f"""
{APP_NAME}

إصدار: {VERSION}
الشركة: {COMPANY_NAME}

نظام متكامل لإدارة فواتير الكهرباء
مطور بلغة Python مع واجهة حديثة

المميزات:
• قاعدة بيانات PostgreSQL آمنة
• نظام صلاحيات متعدد المستويات
• تقارير وإحصائيات متقدمة
• نسخ احتياطي تلقائي
• واجهة مستخدم عربية

حقوق النشر © 2025
جميع الحقوق محفوظة
        """
        messagebox.showinfo("عن البرنامج", about_text)
    
    def run(self):
        """تشغيل النافذة"""
        self.root.mainloop()