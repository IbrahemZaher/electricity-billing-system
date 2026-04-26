# ui/settings_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from database.connection import db
from datetime import datetime, timedelta

class SettingsUI:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.settings_file = "config/settings.json"
        self.load_settings()
        self.create_widgets()

    def load_settings(self):
        default_settings = {
            "company_name": "مولدة الريان للطاقة الكهربائية",
            "company_phone": "011-1234567",
            "currency": "ل.س",
            "tax_rate": 10,
            "backup_auto": True,
            "initial_cash_balance": 0
        }
        # أولاً: حاول تحميل من ملف JSON (للإعدادات الأخرى)
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    self.settings = json.load(f)
            else:
                self.settings = default_settings.copy()
        except:
            self.settings = default_settings.copy()

        # ثانياً: قراءة الرصيد الافتتاحي من قاعدة البيانات (المصدر الأساسي)
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT value FROM settings WHERE key = 'initial_cash_balance'")
                row = cursor.fetchone()
                if row:
                    self.settings['initial_cash_balance'] = float(row['value'])
        except Exception as e:
            print(f"خطأ في قراءة الرصيد الافتتاحي من قاعدة البيانات: {e}")

    def save_settings(self):
        try:
            # حفظ الرصيد الافتتاحي في قاعدة البيانات أولاً
            with db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO settings (key, value, description)
                    VALUES ('initial_cash_balance', %s, 'الرصيد الافتتاحي لأول يوم في النظام')
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """, (str(self.initial_balance.get()),))

            # تحديث باقي الإعدادات في self.settings
            self.settings['company_name'] = self.company_name.get()
            self.settings['company_phone'] = self.company_phone.get()
            self.settings['backup_auto'] = self.backup_var.get()
            self.settings['currency'] = self.currency.get()
            self.settings['tax_rate'] = float(self.tax_rate.get())
            self.settings['initial_cash_balance'] = float(self.initial_balance.get())

            # حفظ في ملف JSON
            os.makedirs("config", exist_ok=True)
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)

            # إذا تم تغيير الرصيد الافتتاحي، يجب إعادة حساب الصندوق اليومي لليوم الأول
            # هنا يمكن استدعاء دالة إعادة الحساب من models
            from database.models import models
            # نفترض أن اليوم الأول هو أول يوم في جدول daily_cash (أو نحدد تاريخ معين)
            # يمكننا جلب أول تاريخ موجود في daily_cash أو استخدام تاريخ اليوم
            with db.get_cursor() as cursor:
                cursor.execute("SELECT MIN(cash_date) as first_date FROM daily_cash")
                first = cursor.fetchone()
                if first and first['first_date']:
                    models.recalculate_daily_cash(first['first_date'])
                    # إعادة حساب الجرد الأسبوعي إذا لزم الأمر
                    # نحدد بداية الأسبوع لذلك التاريخ
                    week_start = first['first_date'] - timedelta(days=first['first_date'].weekday())
                    models.recalculate_week_cash_inventory(week_start)

            messagebox.showinfo("نجاح", "تم حفظ الإعدادات")
            return True
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل الحفظ: {str(e)}")
            return False

    def create_widgets(self):
        for widget in self.parent.winfo_children():
            widget.destroy()

        frame = ttk.Frame(self.parent)
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        title = ttk.Label(frame, text="إعدادات النظام", font=("Arial", 20, "bold"))
        title.pack(pady=10)

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

        # تبويب المدراء
        owners_frame = ttk.Frame(notebook)
        notebook.add(owners_frame, text="المدراء")
        self.create_owners_tab(owners_frame)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="حفظ", command=self.save_settings).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="إعادة تعيين", command=self.reset_settings).pack(side='left', padx=5)

    def create_general_tab(self, parent):
        form_frame = ttk.Frame(parent)
        form_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(form_frame, text="اسم الشركة:").grid(row=0, column=0, sticky='e', pady=5)
        self.company_name = ttk.Entry(form_frame, width=40)
        self.company_name.grid(row=0, column=1, pady=5, padx=5)
        self.company_name.insert(0, self.settings.get("company_name", ""))

        ttk.Label(form_frame, text="هاتف الشركة:").grid(row=1, column=0, sticky='e', pady=5)
        self.company_phone = ttk.Entry(form_frame, width=40)
        self.company_phone.grid(row=1, column=1, pady=5, padx=5)
        self.company_phone.insert(0, self.settings.get("company_phone", ""))

        self.backup_var = tk.BooleanVar(value=self.settings.get("backup_auto", True))
        ttk.Checkbutton(form_frame, text="النسخ الاحتياطي التلقائي",
                       variable=self.backup_var).grid(row=2, column=1, sticky='w', pady=5)

    def create_financial_tab(self, parent):
        form_frame = ttk.Frame(parent)
        form_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(form_frame, text="العملة:").grid(row=0, column=0, sticky='e', pady=5)
        self.currency = ttk.Entry(form_frame, width=20)
        self.currency.grid(row=0, column=1, pady=5, padx=5, sticky='w')
        self.currency.insert(0, self.settings.get("currency", "ل.س"))

        ttk.Label(form_frame, text="نسبة الضريبة (%):").grid(row=1, column=0, sticky='e', pady=5)
        self.tax_rate = ttk.Entry(form_frame, width=20)
        self.tax_rate.grid(row=1, column=1, pady=5, padx=5, sticky='w')
        self.tax_rate.insert(0, str(self.settings.get("tax_rate", 10)))

        ttk.Label(form_frame, text="الرصيد الافتتاحي للنظام (ل.س):").grid(row=2, column=0, sticky='e', pady=5)
        self.initial_balance = ttk.Entry(form_frame, width=20)
        self.initial_balance.grid(row=2, column=1, pady=5, padx=5, sticky='w')
        self.initial_balance.insert(0, str(self.settings.get("initial_cash_balance", 0)))

    def create_owners_tab(self, parent):
        """إدارة أسماء المدراء (الشركاء) لتوزيع الأرباح"""
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        # إطار الإضافة
        add_frame = ttk.LabelFrame(frame, text="إضافة مدير جديد")
        add_frame.pack(fill='x', pady=5)
        ttk.Label(add_frame, text="الاسم:").pack(side='left', padx=5)
        self.new_owner_name = ttk.Entry(add_frame, width=30)
        self.new_owner_name.pack(side='left', padx=5)
        ttk.Button(add_frame, text="إضافة", command=self.add_owner).pack(side='left', padx=5)

        # قائمة المدراء
        list_frame = ttk.LabelFrame(frame, text="قائمة المدراء")
        list_frame.pack(fill='both', expand=True, pady=5)

        columns = ('id', 'name', 'status')
        self.owners_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        self.owners_tree.heading('id', text='الرقم')
        self.owners_tree.heading('name', text='الاسم')
        self.owners_tree.heading('status', text='الحالة')
        self.owners_tree.column('id', width=50)
        self.owners_tree.column('name', width=200)
        self.owners_tree.column('status', width=100)
        self.owners_tree.pack(fill='both', expand=True, padx=5, pady=5)

        # أزرار التحكم
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', pady=5)
        ttk.Button(btn_frame, text="حذف المحدد", command=self.delete_owner).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="تفعيل/تعطيل", command=self.toggle_owner_status).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="تحديث القائمة", command=self.load_owners).pack(side='left', padx=5)

        self.load_owners()

    def load_owners(self):
        """تحميل قائمة المدراء من قاعدة البيانات"""
        for row in self.owners_tree.get_children():
            self.owners_tree.delete(row)
        with db.get_cursor() as cursor:
            cursor.execute("SELECT id, name, is_active FROM company_owners ORDER BY name")
            for row in cursor.fetchall():
                status = "نشط" if row['is_active'] else "غير نشط"
                self.owners_tree.insert('', 'end', values=(row['id'], row['name'], status))

    def add_owner(self):
        name = self.new_owner_name.get().strip()
        if not name:
            messagebox.showerror("خطأ", "الاسم مطلوب")
            return
        with db.get_cursor() as cursor:
            # إضافة المدير إذا لم يكن موجوداً
            cursor.execute("""
                INSERT INTO company_owners (name, is_active)
                SELECT %s, TRUE
                WHERE NOT EXISTS (SELECT 1 FROM company_owners WHERE name = %s)
            """, (name, name))
        self.new_owner_name.delete(0, tk.END)
        self.load_owners()
        messagebox.showinfo("تم", "تمت إضافة المدير")

    def delete_owner(self):
        selected = self.owners_tree.selection()
        if not selected:
            messagebox.showwarning("تنبيه", "اختر مديراً للحذف")
            return
        owner_id = self.owners_tree.item(selected[0])['values'][0]
        owner_name = self.owners_tree.item(selected[0])['values'][1]
        
        # التحقق من وجود أرباح مرتبطة (باستخدام name لأن الجدول قديم)
        with db.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM profit_distribution WHERE manager_name = %s", (owner_name,))
            count = cursor.fetchone()['count']
            if count > 0:
                if not messagebox.askyesno("تحذير", f"هذا المدير له {count} سجل أرباح. هل تريد حذفها أيضاً؟"):
                    messagebox.showwarning("غير مسموح", "لا يمكن حذف مدير له أرباح مسجلة ما لم توافق على حذفها.")
                    return
                else:
                    # حذف الأرباح المرتبطة أولاً
                    cursor.execute("DELETE FROM profit_distribution WHERE manager_name = %s", (owner_name,))
        
        # حذف المدير
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM company_owners WHERE id = %s", (owner_id,))
        self.load_owners()
        messagebox.showinfo("تم", "تم حذف المدير")

    def toggle_owner_status(self):
        selected = self.owners_tree.selection()
        if not selected:
            messagebox.showwarning("تنبيه", "اختر مديراً")
            return
        owner_id = self.owners_tree.item(selected[0])['values'][0]
        with db.get_cursor() as cursor:
            cursor.execute("SELECT is_active FROM company_owners WHERE id = %s", (owner_id,))
            current = cursor.fetchone()
            if current:
                new_status = not current['is_active']
                cursor.execute("UPDATE company_owners SET is_active = %s WHERE id = %s", (new_status, owner_id))
        self.load_owners()
        messagebox.showinfo("تم", "تم تغيير الحالة")

    def reset_settings(self):
        if messagebox.askyesno("تأكيد", "هل تريد إعادة تعيين جميع الإعدادات؟"):
            self.settings = {}
            self.create_widgets()
            messagebox.showinfo("نجاح", "تم إعادة تعيين الإعدادات")