# ui/salary_ui.py

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
from modules.salary_manager import SalaryManager
from modules.daily_cash import DailyCashManager
from database.connection import db

class SalaryUI(tk.Frame):
    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.user_data = user_data
        self.salary_mgr = SalaryManager()
        self.daily_mgr = DailyCashManager()
        self.current_employee_id = None
        self.create_widgets()
        self.load_employees()

    def create_widgets(self):
        toolbar = tk.Frame(self, bg='#2c3e50', height=50)
        toolbar.pack(fill='x')
        toolbar.pack_propagate(False)
        tk.Label(toolbar, text="💰 إدارة رواتب الموظفين وسلفهم", font=('Arial', 14, 'bold'),
                 bg='#2c3e50', fg='white').pack(side='left', padx=20)

        main_paned = tk.PanedWindow(self, orient='horizontal')
        main_paned.pack(fill='both', expand=True)

        # ---------- الجزء الأيسر: قائمة الموظفين مع أزرار الإدارة ----------
        left_frame = tk.LabelFrame(main_paned, text="الموظفون", padx=5, pady=5)
        main_paned.add(left_frame, width=350)

        columns = ('id', 'name', 'base_salary', 'status')
        self.emp_tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=15)
        self.emp_tree.heading('id', text='ID')
        self.emp_tree.heading('name', text='الاسم')
        self.emp_tree.heading('base_salary', text='الراتب الأساسي')
        self.emp_tree.heading('status', text='الحالة')
        self.emp_tree.column('id', width=40, anchor='center')
        self.emp_tree.column('name', width=150)
        self.emp_tree.column('base_salary', width=100, anchor='center')
        self.emp_tree.column('status', width=70, anchor='center')
        self.emp_tree.pack(fill='both', expand=True)
        self.emp_tree.bind('<<TreeviewSelect>>', self.on_employee_select)

        # أزرار إدارة الموظفين
        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(fill='x', pady=5)
        tk.Button(btn_frame, text="➕ إضافة موظف", command=self.add_employee_dialog,
                  bg='#27ae60', fg='white').pack(side='left', padx=2)
        tk.Button(btn_frame, text="✏️ تعديل", command=self.edit_employee_dialog,
                  bg='#f39c12', fg='white').pack(side='left', padx=2)
        tk.Button(btn_frame, text="🗑️ حذف", command=self.delete_employee,
                  bg='#e74c3c', fg='white').pack(side='left', padx=2)
        tk.Button(btn_frame, text="🔄 تحديث", command=self.load_employees,
                  bg='#3498db', fg='white').pack(side='left', padx=2)

        # ---------- الجزء الأيمن: تفاصيل الموظف ----------
        right_frame = tk.LabelFrame(main_paned, text="تفاصيل الموظف", padx=10, pady=10)
        main_paned.add(right_frame, width=550)

        self.detail_notebook = ttk.Notebook(right_frame)
        self.detail_notebook.pack(fill='both', expand=True)

        # تبويب الراتب الأساسي
        self.salary_tab = ttk.Frame(self.detail_notebook)
        self.detail_notebook.add(self.salary_tab, text="الراتب الأساسي")
        self._create_salary_tab()

        # تبويب السلف
        self.advances_tab = ttk.Frame(self.detail_notebook)
        self.detail_notebook.add(self.advances_tab, text="السلف")
        self._create_advances_tab()

        # تبويب صرف الراتب
        self.payment_tab = ttk.Frame(self.detail_notebook)
        self.detail_notebook.add(self.payment_tab, text="صرف الراتب")
        self._create_payment_tab()

        # تبويب السجل المالي الكامل (جديد)
        self.history_tab = ttk.Frame(self.detail_notebook)
        self.detail_notebook.add(self.history_tab, text="السجل المالي")
        self._create_history_tab()

        # تعطيل التبويبات حتى اختيار موظف
        self.detail_notebook.tab(1, state='disabled')
        self.detail_notebook.tab(2, state='disabled')
        self.detail_notebook.tab(3, state='disabled')

    # ------------------- تبويب الراتب الأساسي -------------------
    def _create_salary_tab(self):
        frame = ttk.Frame(self.salary_tab, padding=10)
        frame.pack(fill='both', expand=True)

        ttk.Label(frame, text="الراتب الأساسي الشهري:").grid(row=0, column=0, sticky='e', pady=5)
        self.base_salary_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.base_salary_var, width=20).grid(row=0, column=1, padx=5)

        ttk.Label(frame, text="تاريخ السريان:").grid(row=1, column=0, sticky='e', pady=5)
        self.effective_date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(frame, textvariable=self.effective_date_var, width=20).grid(row=1, column=1, padx=5)

        ttk.Label(frame, text="ملاحظات:").grid(row=2, column=0, sticky='e', pady=5)
        self.salary_notes = tk.Text(frame, height=3, width=40)
        self.salary_notes.grid(row=2, column=1, padx=5, pady=5)

        ttk.Button(frame, text="حفظ الراتب", command=self.save_base_salary).grid(row=3, column=1, pady=10)

        self.salary_history_tree = ttk.Treeview(frame, columns=('effective', 'amount', 'notes'), show='headings', height=5)
        self.salary_history_tree.heading('effective', text='تاريخ السريان')
        self.salary_history_tree.heading('amount', text='المبلغ')
        self.salary_history_tree.heading('notes', text='ملاحظات')
        self.salary_history_tree.grid(row=4, column=0, columnspan=2, sticky='nsew', pady=10)

        frame.grid_rowconfigure(4, weight=1)
        frame.grid_columnconfigure(1, weight=1)

    # ------------------- تبويب السلف -------------------
    def _create_advances_tab(self):
        frame = ttk.Frame(self.advances_tab, padding=10)
        frame.pack(fill='both', expand=True)

        add_frame = ttk.LabelFrame(frame, text="إضافة سلفة جديدة", padding=5)
        add_frame.pack(fill='x', pady=5)

        ttk.Label(add_frame, text="المبلغ:").grid(row=0, column=0, sticky='e')
        self.adv_amount_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.adv_amount_var, width=15).grid(row=0, column=1, padx=5)

        ttk.Label(add_frame, text="التاريخ:").grid(row=0, column=2, sticky='e')
        self.adv_date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(add_frame, textvariable=self.adv_date_var, width=12).grid(row=0, column=3, padx=5)

        ttk.Label(add_frame, text="السبب:").grid(row=1, column=0, sticky='e')
        self.adv_reason_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.adv_reason_var, width=40).grid(row=1, column=1, columnspan=3, padx=5, pady=5)

        ttk.Button(add_frame, text="إضافة السلفة", command=self.add_advance).grid(row=2, column=1, pady=5)

        list_frame = ttk.LabelFrame(frame, text="السلف غير المسددة", padding=5)
        list_frame.pack(fill='both', expand=True, pady=5)

        self.advances_tree = ttk.Treeview(list_frame, columns=('id', 'date', 'amount', 'reason'), show='headings')
        self.advances_tree.heading('id', text='ID')
        self.advances_tree.heading('date', text='التاريخ')
        self.advances_tree.heading('amount', text='المبلغ')
        self.advances_tree.heading('reason', text='السبب')
        self.advances_tree.column('id', width=50, anchor='center')
        self.advances_tree.column('date', width=100)
        self.advances_tree.column('amount', width=100)
        self.advances_tree.pack(fill='both', expand=True)

        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill='x', pady=5)
        ttk.Button(btn_frame, text="حذف المحدد", command=self.delete_advance).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="تحديث", command=self.load_advances).pack(side='left', padx=5)

    # ------------------- تبويب صرف الراتب -------------------
    def _create_payment_tab(self):
        frame = ttk.Frame(self.payment_tab, padding=10)
        frame.pack(fill='both', expand=True)

        ttk.Label(frame, text="تاريخ الصرف:").grid(row=0, column=0, sticky='e', pady=5)
        self.pay_date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(frame, textvariable=self.pay_date_var, width=15).grid(row=0, column=1, padx=5, sticky='w')

        ttk.Button(frame, text="احتساب الصافي", command=self.calculate_net).grid(row=0, column=2, padx=10)

        info_frame = ttk.LabelFrame(frame, text="ملخص الراتب", padding=10)
        info_frame.grid(row=1, column=0, columnspan=3, sticky='ew', pady=10)
        info_frame.columnconfigure(0, weight=1)

        self.base_salary_label = ttk.Label(info_frame, text="الراتب الأساسي: -")
        self.base_salary_label.grid(row=0, column=0, sticky='w')
        self.advances_total_label = ttk.Label(info_frame, text="إجمالي السلف: -")
        self.advances_total_label.grid(row=1, column=0, sticky='w')
        self.net_salary_label = ttk.Label(info_frame, text="الصافي: -", font=('Arial', 12, 'bold'))
        self.net_salary_label.grid(row=2, column=0, sticky='w', pady=5)

        ttk.Label(frame, text="ملاحظات:").grid(row=2, column=0, sticky='ne', pady=5)
        self.pay_notes = tk.Text(frame, height=3, width=50)
        self.pay_notes.grid(row=2, column=1, columnspan=2, pady=5, sticky='w')

        self.pay_button = ttk.Button(frame, text="صرف الراتب وتسجيله في دفتر اليومية",
                                    command=self.pay_salary, state='disabled')
        self.pay_button.grid(row=3, column=1, pady=20)
        frame.columnconfigure(1, weight=1)

    # ------------------- تبويب السجل المالي الكامل (جديد) -------------------
    def _create_history_tab(self):
        frame = ttk.Frame(self.history_tab, padding=10)
        frame.pack(fill='both', expand=True)

        # إطار للتحكم
        ctrl_frame = ttk.Frame(frame)
        ctrl_frame.pack(fill='x', pady=5)

        ttk.Button(ctrl_frame, text="🔄 تحديث السجل", command=self.load_financial_history).pack(side='left', padx=5)

        # جدول العرض
        columns = ('date', 'type', 'amount', 'description')
        self.history_tree = ttk.Treeview(frame, columns=columns, show='headings', height=15)
        self.history_tree.heading('date', text='التاريخ')
        self.history_tree.heading('type', text='النوع')
        self.history_tree.heading('amount', text='المبلغ')
        self.history_tree.heading('description', text='الوصف')
        self.history_tree.column('date', width=100, anchor='center')
        self.history_tree.column('type', width=80, anchor='center')
        self.history_tree.column('amount', width=120, anchor='center')
        self.history_tree.column('description', width=250)

        # شريط تمرير
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    # ------------------- دوال إدارة الموظفين -------------------
    def load_employees(self):
        for row in self.emp_tree.get_children():
            self.emp_tree.delete(row)
        employees = self.salary_mgr.get_all_employees(active_only=False)
        for emp in employees:
            status = "✅ نشط" if emp['is_active'] else "❌ غير نشط"
            salary = f"{emp['base_salary']:,.0f}" if emp['base_salary'] else "غير محدد"
            self.emp_tree.insert('', 'end', values=(emp['id'], emp['name'], salary, status))

    def add_employee_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("إضافة موظف جديد")
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="الاسم:").pack(pady=5)
        name_entry = ttk.Entry(dialog, width=30)
        name_entry.pack()

        ttk.Label(dialog, text="الراتب الأساسي:").pack(pady=5)
        salary_entry = ttk.Entry(dialog, width=30)
        salary_entry.pack()

        ttk.Label(dialog, text="تاريخ التعيين (YYYY-MM-DD):").pack(pady=5)
        hire_entry = ttk.Entry(dialog, width=30)
        hire_entry.insert(0, date.today().isoformat())
        hire_entry.pack()

        ttk.Label(dialog, text="ملاحظات:").pack(pady=5)
        notes_text = tk.Text(dialog, height=3, width=40)
        notes_text.pack()

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("خطأ", "الاسم مطلوب")
                return
            try:
                base = float(salary_entry.get() or 0)
            except:
                messagebox.showerror("خطأ", "الراتب الأساسي غير صحيح")
                return
            hire_date = hire_entry.get()
            notes = notes_text.get('1.0', 'end-1c')
            res = self.salary_mgr.add_employee(name, base, hire_date, notes)
            if res['success']:
                messagebox.showinfo("تم", "تمت إضافة الموظف")
                dialog.destroy()
                self.load_employees()
            else:
                messagebox.showerror("خطأ", res['error'])

        ttk.Button(dialog, text="حفظ", command=save).pack(pady=20)

    def edit_employee_dialog(self):
        sel = self.emp_tree.selection()
        if not sel:
            messagebox.showwarning("تنبيه", "اختر موظفاً")
            return
        emp_id = self.emp_tree.item(sel[0])['values'][0]
        emp = self.salary_mgr.get_employee(emp_id)
        if not emp:
            return

        dialog = tk.Toplevel(self)
        dialog.title("تعديل بيانات الموظف")
        dialog.geometry("400x350")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="الاسم:").pack(pady=5)
        name_entry = ttk.Entry(dialog, width=30)
        name_entry.insert(0, emp['name'])
        name_entry.pack()

        ttk.Label(dialog, text="الراتب الأساسي:").pack(pady=5)
        salary_entry = ttk.Entry(dialog, width=30)
        salary_entry.insert(0, str(emp['base_salary']))
        salary_entry.pack()

        ttk.Label(dialog, text="تاريخ التعيين:").pack(pady=5)
        hire_entry = ttk.Entry(dialog, width=30)
        hire_entry.insert(0, emp['hire_date'].isoformat() if emp['hire_date'] else '')
        hire_entry.pack()

        is_active_var = tk.BooleanVar(value=emp['is_active'])
        ttk.Checkbutton(dialog, text="نشط", variable=is_active_var).pack(pady=5)

        ttk.Label(dialog, text="ملاحظات:").pack(pady=5)
        notes_text = tk.Text(dialog, height=3, width=40)
        notes_text.insert('1.0', emp['notes'] or '')
        notes_text.pack()

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("خطأ", "الاسم مطلوب")
                return
            try:
                base = float(salary_entry.get() or 0)
            except:
                messagebox.showerror("خطأ", "الراتب الأساسي غير صحيح")
                return
            hire_date = hire_entry.get()
            notes = notes_text.get('1.0', 'end-1c')
            res = self.salary_mgr.update_employee(emp_id, name, base, hire_date, is_active_var.get(), notes)
            if res['success']:
                messagebox.showinfo("تم", "تم تعديل الموظف")
                dialog.destroy()
                self.load_employees()
                # إذا كان الموظف الحالي هو المعدّل، نقوم بتحديث التبويبات
                if self.current_employee_id == emp_id:
                    self.on_employee_select(None)
            else:
                messagebox.showerror("خطأ", res['error'])

        ttk.Button(dialog, text="حفظ", command=save).pack(pady=20)

    def delete_employee(self):
        sel = self.emp_tree.selection()
        if not sel:
            return
        emp_id = self.emp_tree.item(sel[0])['values'][0]
        name = self.emp_tree.item(sel[0])['values'][1]
        if messagebox.askyesno("تأكيد", f"هل تريد حذف الموظف '{name}'؟"):
            res = self.salary_mgr.delete_employee(emp_id)
            if res['success']:
                self.load_employees()
                if self.current_employee_id == emp_id:
                    self.current_employee_id = None
                    self.detail_notebook.tab(1, state='disabled')
                    self.detail_notebook.tab(2, state='disabled')
                    self.detail_notebook.tab(3, state='disabled')
                messagebox.showinfo("تم", "تم حذف الموظف")
            else:
                messagebox.showerror("خطأ", res['error'])

    # ------------------- دوال التبويبات (معدلة لاستخدام employee_id) -------------------
    def on_employee_select(self, event):
        sel = self.emp_tree.selection()
        if not sel:
            return
        self.current_employee_id = self.emp_tree.item(sel[0])['values'][0]
        # تفعيل التبويبات
        self.detail_notebook.tab(1, state='normal')
        self.detail_notebook.tab(2, state='normal')
        self.detail_notebook.tab(3, state='normal')
        self.load_salary_history()
        self.load_advances()
        self.clear_payment_tab()
        self.load_financial_history()   # تحميل السجل المالي
        self.pay_button.config(state='normal')

    def load_salary_history(self):
        for row in self.salary_history_tree.get_children():
            self.salary_history_tree.delete(row)
        if not self.current_employee_id:
            return
        # نعرض فقط الراتب الحالي للموظف (يمكن تطويره لاحقاً لسجل التغييرات)
        emp = self.salary_mgr.get_employee(self.current_employee_id)
        if emp:
            self.salary_history_tree.insert('', 'end', values=(
                emp['hire_date'], f"{emp['base_salary']:,.0f}", emp['notes'] or ''
            ))

    def save_base_salary(self):
        if not self.current_employee_id:
            return
        try:
            amount = float(self.base_salary_var.get())
            eff_date = self.effective_date_var.get()
            notes = self.salary_notes.get('1.0', 'end-1c')
            # تحديث الراتب في جدول employees مباشرة
            with db.get_cursor() as cursor:
                cursor.execute("UPDATE employees SET base_salary = %s, notes = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                               (amount, notes, self.current_employee_id))
            messagebox.showinfo("تم", "تم تحديث الراتب الأساسي")
            self.load_salary_history()
            self.load_employees()
        except ValueError:
            messagebox.showerror("خطأ", "المبلغ غير صحيح")

    def load_advances(self):
        for row in self.advances_tree.get_children():
            self.advances_tree.delete(row)
        if not self.current_employee_id:
            return
        advances = self.salary_mgr.get_unpaid_advances(self.current_employee_id)
        for adv in advances:
            self.advances_tree.insert('', 'end', values=(
                adv['id'], adv['advance_date'], f"{adv['amount']:,.0f}", adv['reason']
            ))

    def add_advance(self):
        if not self.current_employee_id:
            return
        try:
            amount = float(self.adv_amount_var.get())
            adv_date = self.adv_date_var.get()
            reason = self.adv_reason_var.get()
            res = self.salary_mgr.add_advance(self.current_employee_id, amount, adv_date, reason)
            if res['success']:
                messagebox.showinfo("تم", "تمت إضافة السلفة")
                self.load_advances()
                self.load_financial_history()  # تحديث السجل المالي
                self.adv_amount_var.set('')
                self.adv_reason_var.set('')
            else:
                messagebox.showerror("خطأ", res['error'])
        except ValueError:
            messagebox.showerror("خطأ", "المبلغ غير صحيح")

    def delete_advance(self):
        sel = self.advances_tree.selection()
        if not sel:
            return
        adv_id = self.advances_tree.item(sel[0])['values'][0]
        with db.get_cursor() as cursor:
            cursor.execute("UPDATE employee_advances SET repaid = TRUE, notes = notes || ' (ملغاة)' WHERE id = %s", (adv_id,))
        self.load_advances()
        self.load_financial_history()  # تحديث السجل المالي

    def calculate_net(self):
        if not self.current_employee_id:
            return
        pay_date = self.pay_date_var.get()
        calc = self.salary_mgr.calculate_net_salary(self.current_employee_id, pay_date)
        if calc['success']:
            self.base_salary_label.config(text=f"الراتب الأساسي: {calc['base_salary']:,.0f} ل.س")
            self.advances_total_label.config(text=f"إجمالي السلف: {calc['total_advances']:,.0f} ل.س")
            self.net_salary_label.config(text=f"الصافي: {calc['net_salary']:,.0f} ل.س")
            self.temp_calc = calc
        else:
            messagebox.showerror("خطأ", calc['error'])

    def clear_payment_tab(self):
        self.base_salary_label.config(text="الراتب الأساسي: -")
        self.advances_total_label.config(text="إجمالي السلف: -")
        self.net_salary_label.config(text="الصافي: -")
        self.temp_calc = None

    def pay_salary(self):
        if not self.current_employee_id or not hasattr(self, 'temp_calc'):
            messagebox.showwarning("تنبيه", "قم باحتساب الصافي أولاً")
            return
        pay_date_str = self.pay_date_var.get()
        try:
            # تحويل النص إلى كائن date
            pay_date = datetime.strptime(pay_date_str, '%Y-%m-%d').date()
        except ValueError:
            messagebox.showerror("خطأ", "صيغة التاريخ غير صحيحة (YYYY-MM-DD)")
            return

        daily_res = self.daily_mgr.create_or_update_daily_cash(pay_date, self.user_data.get('id', 1))
        if not daily_res['success']:
            messagebox.showerror("خطأ", "تعذر إنشاء سجل دفتر اليومية")
            return
        daily_id = daily_res['daily_cash_id']
        notes = self.pay_notes.get('1.0', 'end-1c')
        result = self.salary_mgr.pay_salary(
            employee_id=self.current_employee_id,
            payment_date=pay_date,
            daily_cash_id=daily_id,
            created_by=self.user_data.get('id', 1),
            notes=notes
        )
        if result['success']:
            messagebox.showinfo("تم", f"تم صرف الراتب الصافي: {result['net_salary']:,.0f} ل.س")
            self.clear_payment_tab()
            self.load_advances()
            self.load_financial_history()  # تحديث السجل المالي
        else:
            messagebox.showerror("خطأ", result['error'])

    # ------------------- تحميل السجل المالي الكامل (جديد) -------------------
    def load_financial_history(self):
        """تحميل وعرض جميع السلف والرواتب للموظف الحالي في تبويب السجل المالي"""
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        if not self.current_employee_id:
            return

        history = self.salary_mgr.get_employee_financial_history(self.current_employee_id)
        for entry in history:
            trans_type = "💵 سلفة" if entry['type'] == 'advance' else "💰 راتب"
            amount = entry['amount']
            date_str = entry['transaction_date'].strftime('%Y-%m-%d') if isinstance(entry['transaction_date'], date) else str(entry['transaction_date'])
            description = entry.get('description') or ''

            # إضافة ملاحظة إذا كانت السلفة مسددة
            if entry['type'] == 'advance' and entry.get('repaid'):
                description += " (مسددة)"

            self.history_tree.insert('', 'end', values=(
                date_str,
                trans_type,
                f"{amount:,.0f} ل.س",
                description
            ))