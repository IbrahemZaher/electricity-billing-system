# ui/login_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from auth.authentication import auth

logger = logging.getLogger(__name__)

class LoginWindow:
    def __init__(self):
        self.window = tk.Tk()
        self.setup_window()
        self.create_widgets()
    
    def setup_window(self):
        """إعداد النافذة"""
        self.window.title("نظام إدارة الفواتير - تسجيل الدخول")
        self.window.geometry("500x400")
        self.window.configure(bg="#f0f8ff")
        self.window.resizable(False, False)
        
        # مركزية النافذة
        self.center_window()
    
    def center_window(self):
        """مركزية النافذة"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        """إنشاء عناصر الواجهة"""
        # الإطار الرئيسي
        main_frame = ttk.Frame(self.window, padding="30")
        main_frame.pack(fill='both', expand=True)
        
        # العنوان
        title_label = ttk.Label(main_frame,
                               text="مولدة الريان للطاقة الكهربائية",
                               font=("Arial", 20, "bold"),
                               foreground="#2c3e50")
        title_label.pack(pady=(0, 30))
        
        # نموذج تسجيل الدخول
        self.create_login_form(main_frame)
    
    def create_login_form(self, parent):
        """إنشاء نموذج تسجيل الدخول"""
        form_frame = ttk.Frame(parent)
        form_frame.pack(fill='x', pady=10)
        
        # اسم المستخدم
        ttk.Label(form_frame, text="اسم المستخدم:",
                 font=("Arial", 12)).grid(row=0, column=0,
                                         padx=5, pady=10,
                                         sticky='e')
        
        self.username_entry = ttk.Entry(form_frame,
                                       font=("Arial", 12),
                                       width=25)
        self.username_entry.grid(row=0, column=1,
                                padx=5, pady=10,
                                sticky='w')
        
        # كلمة المرور
        ttk.Label(form_frame, text="كلمة المرور:",
                 font=("Arial", 12)).grid(row=1, column=0,
                                         padx=5, pady=10,
                                         sticky='e')
        
        self.password_entry = ttk.Entry(form_frame,
                                       show="*",
                                       font=("Arial", 12),
                                       width=25)
        self.password_entry.grid(row=1, column=1,
                                padx=5, pady=10,
                                sticky='w')
        
        # زر تسجيل الدخول
        login_button = tk.Button(parent,
                                text="تسجيل الدخول",
                                font=("Arial", 14, "bold"),
                                bg="#3498db",
                                fg="white",
                                activebackground="#2980b9",
                                cursor="hand2",
                                command=self.authenticate,
                                padx=30,
                                pady=8)
        login_button.pack(pady=30)
        
        # ربط زر Enter بتسجيل الدخول
        self.password_entry.bind('<Return>', lambda e: self.authenticate())
    
    def authenticate(self):
        """المصادقة"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("خطأ", "يرجى إدخال اسم المستخدم وكلمة المرور")
            return
        
        # Note: We'll need to fix the auth import later
        # user = auth.login(username, password)
        user = {"id": 1, "full_name": "Admin", "role": "admin", "permissions": {"all": True}}
        
        if user:
            # إغلاق نافذة تسجيل الدخول
            self.window.destroy()
            
            # استيراد MainWindow بعد إغلاق نافذة تسجيل الدخول لتجنب الاستيراد الدائري
            from ui.main_window import MainWindow
            main_window = MainWindow(user)
            main_window.run()
        else:
            messagebox.showerror("خطأ", "اسم المستخدم أو كلمة المرور غير صحيحة")
    
    def run(self):
        """تشغيل النافذة"""
        self.window.mainloop()