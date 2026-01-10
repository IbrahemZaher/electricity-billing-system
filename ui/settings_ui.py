# ui/settings_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

class SettingsUI:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.settings_file = "config/settings.json"
        self.load_settings()
        self.create_widgets()
    
    def load_settings(self):
        """تحميل الإعدادات"""
        default_settings = {
            "company_name": "مولدة الريان للطاقة الكهربائية",
            "company_phone": "011-1234567",
            "currency": "ل.س",
            "tax_rate": 10,
            "backup_auto": True
        }
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    self.settings = json.load(f)
            else:
                self.settings = default_settings
        except:
            self.settings = default_settings
    
    def save_settings(self):
        """حفظ الإعدادات"""
        try:
            os.makedirs("config", exist_ok=True)
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            messagebox.showinfo("نجاح", "تم حفظ الإعدادات")
            return True
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل الحفظ: {str(e)}")
            return False
    
    def create_widgets(self):
        """إنشاء واجهة الإعدادات"""
        for widget in self.parent.winfo_children():
            widget.destroy()
        
        frame = ttk.Frame(self.parent)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        title = ttk.Label(frame, text="إعدادات النظام", font=("Arial", 20, "bold"))
        title.pack(pady=10)
        
        # تبويبات
        notebook = ttk.Notebook(frame)
        notebook.pack(fill='both', expand=True, pady=10)
        
        # تبويب عام
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="عام")
        self.create_general_tab(general_frame)
        
        # تبويب مالي
        financial_frame = ttk.Frame(notebook)
        notebook.add(financial_frame, text="مالي")
        self.create_financial_tab(financial_frame)
        
        # أزرار الحفظ
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="حفظ", command=self.save_settings).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="إعادة تعيين", command=self.reset_settings).pack(side='left', padx=5)
    
    def create_general_tab(self, parent):
        """إنشاء تبويب الإعدادات العامة"""
        form_frame = ttk.Frame(parent)
        form_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # اسم الشركة
        ttk.Label(form_frame, text="اسم الشركة:").grid(row=0, column=0, sticky='e', pady=5)
        self.company_name = ttk.Entry(form_frame, width=40)
        self.company_name.grid(row=0, column=1, pady=5, padx=5)
        self.company_name.insert(0, self.settings.get("company_name", ""))
        
        # هاتف الشركة
        ttk.Label(form_frame, text="هاتف الشركة:").grid(row=1, column=0, sticky='e', pady=5)
        self.company_phone = ttk.Entry(form_frame, width=40)
        self.company_phone.grid(row=1, column=1, pady=5, padx=5)
        self.company_phone.insert(0, self.settings.get("company_phone", ""))
        
        # النسخ الاحتياطي التلقائي
        self.backup_var = tk.BooleanVar(value=self.settings.get("backup_auto", True))
        ttk.Checkbutton(form_frame, text="النسخ الاحتياطي التلقائي", 
                       variable=self.backup_var).grid(row=2, column=1, sticky='w', pady=5)
    
    def create_financial_tab(self, parent):
        """إنشاء تبويب الإعدادات المالية"""
        form_frame = ttk.Frame(parent)
        form_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # العملة
        ttk.Label(form_frame, text="العملة:").grid(row=0, column=0, sticky='e', pady=5)
        self.currency = ttk.Entry(form_frame, width=20)
        self.currency.grid(row=0, column=1, pady=5, padx=5, sticky='w')
        self.currency.insert(0, self.settings.get("currency", "ل.س"))
        
        # نسبة الضريبة
        ttk.Label(form_frame, text="نسبة الضريبة (%):").grid(row=1, column=0, sticky='e', pady=5)
        self.tax_rate = ttk.Entry(form_frame, width=20)
        self.tax_rate.grid(row=1, column=1, pady=5, padx=5, sticky='w')
        self.tax_rate.insert(0, str(self.settings.get("tax_rate", 10)))
    
    def reset_settings(self):
        """إعادة تعيين الإعدادات"""
        if messagebox.askyesno("تأكيد", "هل تريد إعادة تعيين جميع الإعدادات؟"):
            self.settings = {}
            self.create_widgets()
            messagebox.showinfo("نجاح", "تم إعادة تعيين الإعدادات")