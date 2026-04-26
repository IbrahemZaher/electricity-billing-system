# ui/daily_cash_ui.py

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
import logging
from modules.daily_cash import DailyCashManager
from database.connection import db

logger = logging.getLogger(__name__)

class DailyCashUI(tk.Frame):

    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.user_data = user_data
        self.daily_mgr = DailyCashManager()
        self.current_date = date.today()
        self.show_inactive_var = tk.BooleanVar(value=True)
        self.current_detail_window = None
        self.create_widgets()
        self.load_current()

    def create_widgets(self):
        # إطار التاريخ والأزرار
        date_frame = tk.Frame(self)
        date_frame.pack(fill='x', padx=10, pady=5)

        tk.Button(date_frame, text="◀ اليوم السابق", command=self.prev_day).pack(side='left')
        self.date_label = tk.Label(date_frame, text="", font=('Arial', 14, 'bold'))
        self.date_label.pack(side='left', padx=20)
        tk.Button(date_frame, text="اليوم التالي ▶", command=self.next_day).pack(side='left')
        tk.Button(date_frame, text="اليوم", command=self.load_today).pack(side='left', padx=10)

        tk.Label(date_frame, text="أو انتقل إلى تاريخ:").pack(side='left', padx=10)
        self.date_entry = tk.Entry(date_frame, width=12)
        self.date_entry.pack(side='left', padx=5)
        self.date_entry.insert(0, date.today().isoformat())
        tk.Button(date_frame, text="اذهب", command=self.go_to_date).pack(side='left')

        chk = tk.Checkbutton(date_frame, text="إظهار المحاسبين بدون حركة",
                             variable=self.show_inactive_var, command=self.refresh_accountants_table)
        chk.pack(side='right', padx=20)

        # لوحة ملخص الرصيد
        self.balance_frame = tk.LabelFrame(self, text="💰 ملخص الصندوق", padx=10, pady=10)
        self.balance_frame.pack(fill='x', padx=10, pady=5)

        self.opening_label = tk.Label(self.balance_frame, text="رصيد أول المدة: ---", font=('Arial', 11, 'bold'))
        self.opening_label.pack(side='left', padx=20)
        self.closing_label = tk.Label(self.balance_frame, text="رصيد آخر المدة: ---", font=('Arial', 11, 'bold'))
        self.closing_label.pack(side='left', padx=20)
        self.net_label = tk.Label(self.balance_frame, text="صافي اليوم: ---", font=('Arial', 11, 'bold'))
        self.net_label.pack(side='left', padx=20)

        # إطار عرض ملخص المحاسبين
        accountants_frame = tk.LabelFrame(self, text="📊 ملخص المحاسبين", padx=10, pady=10)
        accountants_frame.pack(fill='both', expand=True, padx=10, pady=5)

        columns = ('name', 'invoices', 'collected', 'expenses', 'manager_profit', 'energy_profit', 'net')
        self.acc_tree = ttk.Treeview(accountants_frame, columns=columns, show='headings', height=12)
        self.acc_tree.heading('name', text='المحاسب')
        self.acc_tree.heading('invoices', text='عدد الفواتير')
        self.acc_tree.heading('collected', text='الجباية (ل.س)')
        self.acc_tree.heading('expenses', text='المصاريف (ل.س)')
        self.acc_tree.heading('manager_profit', text='أرباح مدير (ل.س)')
        self.acc_tree.heading('energy_profit', text='أرباح طاقة (ل.س)')
        self.acc_tree.heading('net', text='الصافي (ل.س)')

        self.acc_tree.column('name', width=150)
        self.acc_tree.column('invoices', width=80, anchor='center')
        self.acc_tree.column('collected', width=120, anchor='center')
        self.acc_tree.column('expenses', width=120, anchor='center')
        self.acc_tree.column('manager_profit', width=120, anchor='center')
        self.acc_tree.column('energy_profit', width=120, anchor='center')
        self.acc_tree.column('net', width=120, anchor='center')
        self.acc_tree.pack(fill='both', expand=True)

        self.acc_tree.bind('<Double-1>', self.on_accountant_double_click)

        action_frame = tk.Frame(self)
        action_frame.pack(fill='x', padx=10, pady=5)
        tk.Button(action_frame, text="➕ إضافة مصروف", command=self.add_expense_dialog,
                  bg='#e67e22', fg='white').pack(side='left', padx=5)
        tk.Button(action_frame, text="📊 الجرد الأسبوعي", command=self.show_weekly_inventory,
                  bg='#3498db', fg='white').pack(side='left', padx=5)
        tk.Button(action_frame, text="🔄 تحديث", command=self.load_current,
                  bg='#2ecc71', fg='white').pack(side='left', padx=5)

        self.status_label = tk.Label(self, text="", bd=1, relief='sunken', anchor='w')
        self.status_label.pack(side='bottom', fill='x')

    def load_current(self):
        self.load_for_date(self.current_date)

    def load_for_date(self, target_date):
        self.current_date = target_date
        self.date_label.config(text=target_date.strftime('%Y-%m-%d'))
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, target_date.isoformat())

        res = self.daily_mgr.create_or_update_daily_cash(target_date, self.user_data.get('id', 1))
        if not res['success']:
            messagebox.showerror("خطأ", f"فشل تحميل اليوم: {res.get('error')}")
            return

        self.refresh_accountants_table()
        self.update_balance_panel(target_date)

        report = self.daily_mgr.get_daily_cash_report(target_date)
        if report['success']:
            daily = report['daily']
            self.status_label.config(text=f"آخر تحديث: {daily['updated_at']} بواسطة {daily.get('updated_by_name', '')} | رصيد ختامي: {daily['closing_balance']:,.0f} ل.س")
        else:
            self.status_label.config(text="")

    def update_balance_panel(self, target_date):
        with db.get_cursor() as cursor:
            cursor.execute("SELECT opening_balance, closing_balance, total_collections, total_expenses, total_profits, total_energy_profits FROM daily_cash WHERE cash_date = %s", (target_date,))
            row = cursor.fetchone()
            if row:
                opening = row['opening_balance'] or 0
                closing = row['closing_balance'] or 0
                net = closing - opening
                self.opening_label.config(text=f"رصيد أول المدة: {opening:,.0f} ل.س")
                self.closing_label.config(text=f"رصيد آخر المدة: {closing:,.0f} ل.س")
                color = 'green' if net >= 0 else 'red'
                self.net_label.config(text=f"صافي اليوم: {net:,.0f} ل.س", fg=color)
            else:
                self.opening_label.config(text="رصيد أول المدة: ---")
                self.closing_label.config(text="رصيد آخر المدة: ---")
                self.net_label.config(text="صافي اليوم: ---", fg='black')

    def refresh_accountants_table(self):
        for item in self.acc_tree.get_children():
            self.acc_tree.delete(item)

        summary = self.daily_mgr.get_accountants_summary(self.current_date)
        show_inactive = self.show_inactive_var.get()

        total_collected = 0.0
        total_expenses = 0.0
        total_manager = 0.0
        total_energy = 0.0
        total_net = 0.0
        count = 0

        for acc in summary:
            has_activity = (acc['invoice_count'] > 0 or acc['total_expenses'] > 0 
                            or acc['manager_profit'] > 0 or acc['energy_profit'] > 0)
            if not show_inactive and not has_activity:
                continue

            values = (
                acc['full_name'],
                acc['invoice_count'],
                f"{acc['total_collected']:,.0f}",
                f"{acc['total_expenses']:,.0f}",
                f"{acc['manager_profit']:,.0f}",
                f"{acc['energy_profit']:,.0f}",
                f"{acc['net']:,.0f}"
            )
            tag = 'positive' if acc['net'] >= 0 else 'negative'
            self.acc_tree.insert('', 'end', values=values, tags=(tag,))
            total_collected += acc['total_collected']
            total_expenses += acc['total_expenses']
            total_manager += acc['manager_profit']
            total_energy += acc['energy_profit']
            total_net += acc['net']
            count += 1

        self.acc_tree.tag_configure('positive', foreground='green')
        self.acc_tree.tag_configure('negative', foreground='red')

        if count > 0:
            self.acc_tree.insert('', 'end', values=(
                'الإجمالي', '', 
                f"{total_collected:,.0f}", 
                f"{total_expenses:,.0f}", 
                f"{total_manager:,.0f}", 
                f"{total_energy:,.0f}", 
                f"{total_net:,.0f}"
            ), tags=('total',))
            self.acc_tree.tag_configure('total', font=('Arial', 10, 'bold'))

    def on_accountant_double_click(self, event):
        selection = self.acc_tree.selection()
        if not selection:
            return
        item = selection[0]
        values = self.acc_tree.item(item, 'values')
        if not values or values[0] == 'الإجمالي':
            return
        full_name = values[0]
        summary = self.daily_mgr.get_accountants_summary(self.current_date)
        acc = next((a for a in summary if a['full_name'] == full_name), None)
        if not acc:
            messagebox.showerror("خطأ", "لم يتم العثور على بيانات المحاسب")
            return
        self.show_accountant_details(acc['user_id'], acc['full_name'])

    def show_accountant_details(self, user_id: int, full_name: str):
        win = tk.Toplevel(self)
        win.title(f"تفاصيل المحاسب: {full_name} - {self.current_date}")
        win.geometry("950x650")
        self.current_detail_window = win
        win.full_name = full_name
        win.user_id = user_id

        invoices = self.daily_mgr.get_invoices_by_accountant(self.current_date, user_id)
        expenses = self.daily_mgr.get_expenses_by_accountant(self.current_date, user_id)
        manager_profits = self.daily_mgr.get_manager_profits_by_accountant(self.current_date, user_id)
        energy_profits = self.daily_mgr.get_energy_profits_by_accountant(self.current_date, user_id)

        nb = ttk.Notebook(win)
        nb.pack(fill='both', expand=True, padx=10, pady=10)

        # === تبويب الفواتير ===
        inv_frame = ttk.Frame(nb)
        nb.add(inv_frame, text=f"📄 الفواتير ({len(invoices)})")

        inv_tree = ttk.Treeview(inv_frame, columns=('number', 'time', 'customer', 'kw', 'free', 'discount', 'total'), show='headings')
        inv_tree.heading('number', text='رقم الفاتورة')
        inv_tree.heading('time', text='الوقت')
        inv_tree.heading('customer', text='الزبون')
        inv_tree.heading('kw', text='كيلووات')
        inv_tree.heading('free', text='مجاني')
        inv_tree.heading('discount', text='حسم')
        inv_tree.heading('total', text='المبلغ')
        inv_tree.column('number', width=120)
        inv_tree.column('time', width=80)
        inv_tree.column('customer', width=150)
        inv_tree.column('kw', width=80, anchor='center')
        inv_tree.column('free', width=80, anchor='center')
        inv_tree.column('discount', width=80, anchor='center')
        inv_tree.column('total', width=100, anchor='center')
        inv_tree.pack(fill='both', expand=True)

        total_inv_amount = 0.0
        for inv in invoices:
            inv_tree.insert('', 'end', values=(
                inv['invoice_number'],
                inv['payment_time'].strftime('%H:%M') if inv['payment_time'] else '',
                inv['customer_name'] or '---',
                f"{inv['kilowatt_amount']:,.0f}",
                f"{inv['free_kilowatt']:,.0f}",
                f"{inv['discount']:,.0f}",
                f"{inv['total_amount']:,.0f}"
            ))
            total_inv_amount += float(inv['total_amount'])

        inv_summary = tk.Label(inv_frame, text=f"إجمالي الفواتير: {len(invoices)} | المبلغ الكلي: {total_inv_amount:,.0f} ل.س",
                               font=('Arial', 11, 'bold'))
        inv_summary.pack(pady=5)

        # === تبويب المصاريف ===
        exp_frame = ttk.Frame(nb)
        nb.add(exp_frame, text=f"💸 المصاريف ({len(expenses)})")

        exp_toolbar = tk.Frame(exp_frame)
        exp_toolbar.pack(fill='x', pady=5)
        tk.Button(exp_toolbar, text="✏️ تعديل", command=lambda: self.edit_selected_expense(exp_tree, user_id),
                  bg='#f39c12', fg='white').pack(side='left', padx=5)
        tk.Button(exp_toolbar, text="🗑️ حذف", command=lambda: self.delete_selected_expense(exp_tree, user_id),
                  bg='#e74c3c', fg='white').pack(side='left', padx=5)

        exp_tree = ttk.Treeview(exp_frame, columns=('id', 'category', 'amount', 'note', 'time'), show='headings')
        exp_tree.heading('id', text='ID')
        exp_tree.heading('category', text='التصنيف')
        exp_tree.heading('amount', text='المبلغ')
        exp_tree.heading('note', text='ملاحظات')
        exp_tree.heading('time', text='الوقت')
        exp_tree.column('id', width=50, anchor='center')
        exp_tree.column('category', width=150)
        exp_tree.column('amount', width=100, anchor='center')
        exp_tree.column('note', width=200)
        exp_tree.column('time', width=120, anchor='center')
        exp_tree.pack(fill='both', expand=True)

        total_exp_amount = 0.0
        for exp in expenses:
            exp_tree.insert('', 'end', values=(
                exp['id'],
                exp['category'],
                f"{exp['amount']:,.0f}",
                exp['note'] or '',
                exp['created_at'].strftime('%H:%M') if exp['created_at'] else ''
            ))
            total_exp_amount += float(exp['amount'])

        exp_summary = tk.Label(exp_frame, text=f"إجمالي المصاريف: {total_exp_amount:,.0f} ل.س",
                               font=('Arial', 11, 'bold'))
        exp_summary.pack(pady=5)
        win.exp_tree = exp_tree

        # === تبويب أرباح مدير ===
        man_frame = ttk.Frame(nb)
        nb.add(man_frame, text=f"🏆 أرباح مدير ({len(manager_profits)})")

        man_toolbar = tk.Frame(man_frame)
        man_toolbar.pack(fill='x', pady=5)
        tk.Button(man_toolbar, text="✏️ تعديل", command=lambda: self.edit_selected_profit(man_tree, user_id, 'manager'),
                  bg='#f39c12', fg='white').pack(side='left', padx=5)
        tk.Button(man_toolbar, text="🗑️ حذف", command=lambda: self.delete_selected_profit(man_tree, user_id, 'manager'),
                  bg='#e74c3c', fg='white').pack(side='left', padx=5)

        man_tree = ttk.Treeview(man_frame, columns=('id', 'owner', 'amount', 'note', 'time'), show='headings')
        man_tree.heading('id', text='ID')
        man_tree.heading('owner', text='المدير')
        man_tree.heading('amount', text='المبلغ')
        man_tree.heading('note', text='ملاحظات')
        man_tree.heading('time', text='الوقت')
        man_tree.column('id', width=50, anchor='center')
        man_tree.column('owner', width=150)
        man_tree.column('amount', width=100, anchor='center')
        man_tree.column('note', width=200)
        man_tree.column('time', width=120, anchor='center')
        man_tree.pack(fill='both', expand=True)

        total_man = 0.0
        for p in manager_profits:
            man_tree.insert('', 'end', values=(
                p['id'],
                p['owner_name'],
                f"{p['amount']:,.0f}",
                p['note'] or '',
                p['created_at'].strftime('%H:%M') if p['created_at'] else ''
            ))
            total_man += float(p['amount'])
        tk.Label(man_frame, text=f"إجمالي أرباح المدير: {total_man:,.0f} ل.س",
                 font=('Arial', 11, 'bold')).pack(pady=5)
        win.man_tree = man_tree

        # === تبويب أرباح طاقة ===
        en_frame = ttk.Frame(nb)
        nb.add(en_frame, text=f"⚡ أرباح طاقة ({len(energy_profits)})")

        en_toolbar = tk.Frame(en_frame)
        en_toolbar.pack(fill='x', pady=5)
        tk.Button(en_toolbar, text="✏️ تعديل", command=lambda: self.edit_selected_profit(en_tree, user_id, 'energy'),
                  bg='#f39c12', fg='white').pack(side='left', padx=5)
        tk.Button(en_toolbar, text="🗑️ حذف", command=lambda: self.delete_selected_profit(en_tree, user_id, 'energy'),
                  bg='#e74c3c', fg='white').pack(side='left', padx=5)

        en_tree = ttk.Treeview(en_frame, columns=('id', 'meter', 'amount', 'note', 'time'), show='headings')
        en_tree.heading('id', text='ID')
        en_tree.heading('meter', text='عداد الطاقة')
        en_tree.heading('amount', text='المبلغ')
        en_tree.heading('note', text='ملاحظات')
        en_tree.heading('time', text='الوقت')
        en_tree.column('id', width=50, anchor='center')
        en_tree.column('meter', width=150)
        en_tree.column('amount', width=100, anchor='center')
        en_tree.column('note', width=200)
        en_tree.column('time', width=120, anchor='center')
        en_tree.pack(fill='both', expand=True)

        total_en = 0.0
        for p in energy_profits:
            en_tree.insert('', 'end', values=(
                p['id'],
                p['meter_name'],
                f"{p['amount']:,.0f}",
                p['note'] or '',
                p['created_at'].strftime('%H:%M') if p['created_at'] else ''
            ))
            total_en += float(p['amount'])
        tk.Label(en_frame, text=f"إجمالي أرباح الطاقة: {total_en:,.0f} ل.س",
                 font=('Arial', 11, 'bold')).pack(pady=5)
        win.en_tree = en_tree

    def edit_selected_expense(self, tree, user_id):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("تنبيه", "اختر مصروفاً لتعديله")
            return
        item = selection[0]
        values = tree.item(item, 'values')
        expense_id = int(values[0])
        old_amount = float(values[2].replace(',', ''))
        old_note = values[3]

        dialog = tk.Toplevel(self)
        dialog.title("تعديل مصروف")
        dialog.geometry("300x250")
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="المبلغ (ل.س):").pack(pady=5)
        amount_entry = tk.Entry(dialog)
        amount_entry.insert(0, str(old_amount))
        amount_entry.pack(pady=5)

        tk.Label(dialog, text="ملاحظات:").pack(pady=5)
        note_text = tk.Text(dialog, height=4)
        note_text.insert('1.0', old_note)
        note_text.pack(pady=5, fill='x')

        def save():
            try:
                new_amount = float(amount_entry.get())
            except:
                messagebox.showerror("خطأ", "المبلغ غير صحيح")
                return
            new_note = note_text.get("1.0", "end-1c").strip()
            res = self.daily_mgr.update_expense(expense_id, new_amount, new_note, self.user_data.get('id', 1))
            if res['success']:
                dialog.destroy()
                self.load_current()
                messagebox.showinfo("تم", "تم تعديل المصروف")
                if self.current_detail_window and self.current_detail_window.winfo_exists():
                    uid = self.current_detail_window.user_id
                    fname = self.current_detail_window.full_name
                    self.current_detail_window.destroy()
                    self.show_accountant_details(uid, fname)
            else:
                messagebox.showerror("خطأ", res.get('error'))

        tk.Button(dialog, text="حفظ", command=save, bg='#27ae60', fg='white').pack(pady=10)

    def delete_selected_expense(self, tree, user_id):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("تنبيه", "اختر مصروفاً لحذفه")
            return
        item = selection[0]
        values = tree.item(item, 'values')
        expense_id = int(values[0])

        if not messagebox.askyesno("تأكيد", "هل تريد حذف هذا المصروف؟"):
            return

        res = self.daily_mgr.delete_expense(expense_id, self.user_data.get('id', 1))
        if res['success']:
            self.load_current()
            messagebox.showinfo("تم", "تم حذف المصروف")
            if self.current_detail_window and self.current_detail_window.winfo_exists():
                uid = self.current_detail_window.user_id
                fname = self.current_detail_window.full_name
                self.current_detail_window.destroy()
                self.show_accountant_details(uid, fname)
        else:
            messagebox.showerror("خطأ", res.get('error'))

    def edit_selected_profit(self, tree, user_id, profit_type):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("تنبيه", "اختر سجلاً لتعديله")
            return
        item = selection[0]
        values = tree.item(item, 'values')
        profit_id = int(values[0])
        old_amount = float(values[2].replace(',', ''))
        old_note = values[3]

        dialog = tk.Toplevel(self)
        dialog.title(f"تعديل {'أرباح مدير' if profit_type == 'manager' else 'أرباح طاقة'}")
        dialog.geometry("300x250")
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="المبلغ (ل.س):").pack(pady=5)
        amount_entry = tk.Entry(dialog)
        amount_entry.insert(0, str(old_amount))
        amount_entry.pack(pady=5)

        tk.Label(dialog, text="ملاحظات:").pack(pady=5)
        note_text = tk.Text(dialog, height=4)
        note_text.insert('1.0', old_note)
        note_text.pack(pady=5, fill='x')

        def save():
            try:
                new_amount = float(amount_entry.get())
            except:
                messagebox.showerror("خطأ", "المبلغ غير صحيح")
                return
            new_note = note_text.get("1.0", "end-1c").strip()
            if profit_type == 'manager':
                res = self.daily_mgr.update_profit(profit_id, new_amount, new_note, self.user_data.get('id', 1))
            else:
                res = self.daily_mgr.update_energy_profit(profit_id, new_amount, new_note, self.user_data.get('id', 1))
            if res['success']:
                dialog.destroy()
                self.load_current()
                messagebox.showinfo("تم", "تم التعديل")
                if self.current_detail_window and self.current_detail_window.winfo_exists():
                    uid = self.current_detail_window.user_id
                    fname = self.current_detail_window.full_name
                    self.current_detail_window.destroy()
                    self.show_accountant_details(uid, fname)
            else:
                messagebox.showerror("خطأ", res.get('error'))

        tk.Button(dialog, text="حفظ", command=save, bg='#27ae60', fg='white').pack(pady=10)

    def delete_selected_profit(self, tree, user_id, profit_type):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("تنبيه", "اختر سجلاً لحذفه")
            return
        item = selection[0]
        values = tree.item(item, 'values')
        profit_id = int(values[0])

        if not messagebox.askyesno("تأكيد", "هل تريد حذف هذا السجل؟"):
            return

        if profit_type == 'manager':
            res = self.daily_mgr.delete_profit(profit_id, self.user_data.get('id', 1))
        else:
            res = self.daily_mgr.delete_energy_profit(profit_id, self.user_data.get('id', 1))

        if res['success']:
            self.load_current()
            messagebox.showinfo("تم", "تم الحذف")
            if self.current_detail_window and self.current_detail_window.winfo_exists():
                uid = self.current_detail_window.user_id
                fname = self.current_detail_window.full_name
                self.current_detail_window.destroy()
                self.show_accountant_details(uid, fname)
        else:
            messagebox.showerror("خطأ", res.get('error'))

    def go_to_date(self):
        try:
            new_date = datetime.strptime(self.date_entry.get(), '%Y-%m-%d').date()
            self.current_date = new_date
            self.load_current()
        except:
            messagebox.showerror("خطأ", "صيغة التاريخ غير صحيحة. استخدم YYYY-MM-DD")

    def prev_day(self):
        self.current_date -= timedelta(days=1)
        self.load_current()

    def next_day(self):
        self.current_date += timedelta(days=1)
        self.load_current()

    def load_today(self):
        self.current_date = date.today()
        self.load_current()

    def add_expense_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("إضافة مصروف أو توزيع أرباح")
        dialog.geometry("400x350")
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="اختر التصنيف:").pack(pady=5)
        categories = [
            ('شراب وطعام', 'food'), ('رواتب', 'salaries'), ('سلف', 'advances'),
            ('مصاريف مكتب', 'office'), ('إصلاح', 'repair'), ('توسعة', 'expansion'),
            ('طاقة', 'energy'), ('مازوت', 'fuel'),
            ('🏆 أرباح مدير', 'manager_profit'),
            ('⚡ أرباح طاقة', 'energy_profit')
        ]
        cat_var = tk.StringVar()
        cat_combo = ttk.Combobox(dialog, textvariable=cat_var, values=[c[0] for c in categories], state='readonly')
        cat_combo.pack(pady=5)

        tk.Label(dialog, text="المبلغ (ل.س):").pack(pady=5)
        amount_entry = tk.Entry(dialog)
        amount_entry.pack(pady=5)

        tk.Label(dialog, text="ملاحظات:").pack(pady=5)
        note_text = tk.Text(dialog, height=4)
        note_text.pack(pady=5, fill='x')

        def save():
            cat_arabic = cat_var.get()
            cat_code = next((c[1] for c in categories if c[0] == cat_arabic), None)
            if not cat_code:
                messagebox.showerror("خطأ", "اختر تصنيفاً")
                return
            try:
                amount = float(amount_entry.get())
            except:
                messagebox.showerror("خطأ", "المبلغ غير صحيح")
                return
            note = note_text.get("1.0", "end-1c").strip()

            with db.get_cursor() as cursor:
                cursor.execute("SELECT id FROM daily_cash WHERE cash_date = %s", (self.current_date,))
                row = cursor.fetchone()
                if not row:
                    messagebox.showerror("خطأ", "لم يتم العثور على سجل اليوم")
                    return
                daily_id = row['id']

            if cat_code == 'manager_profit':
                self._select_owner_for_profit(daily_id, amount, note, 'manager', dialog)
            elif cat_code == 'energy_profit':
                self._select_owner_for_profit(daily_id, amount, note, 'energy', dialog)
            else:
                res = self.daily_mgr.add_expense(daily_id, cat_code, amount, note, self.user_data.get('id', 1))
                if res['success']:
                    dialog.destroy()
                    self.load_current()
                    messagebox.showinfo("تم", "تمت إضافة المصروف")
                else:
                    messagebox.showerror("خطأ", res.get('error'))

        tk.Button(dialog, text="حفظ", command=save, bg='#27ae60', fg='white').pack(pady=10)

    def _select_owner_for_profit(self, daily_id, amount, note, profit_type, parent_dialog):
        if profit_type == 'manager':
            table = 'company_owners'
            name_field = 'name'
            title = "اختر المدير"
            add_method = self.daily_mgr.add_profit_distribution
            extra_args = ('manager',)
            query = f"SELECT id, {name_field} FROM {table} WHERE is_active = TRUE ORDER BY {name_field}"
        else:
            table = 'energy_meters'
            name_field = 'name'
            title = "اختر عداد الطاقة"
            add_method = self.daily_mgr.add_energy_profit_distribution
            extra_args = ()
            query = f"SELECT id, {name_field} FROM {table} WHERE is_active = TRUE ORDER BY {name_field}"

        with db.get_cursor() as cursor:
            cursor.execute(query)
            owners = [(row['id'], row[name_field]) for row in cursor.fetchall()]

        if not owners:
            messagebox.showerror("خطأ", f"لا يوجد {title} نشط.")
            return

        sel_dialog = tk.Toplevel(parent_dialog)
        sel_dialog.title(title)
        sel_dialog.geometry("350x250")
        sel_dialog.transient(parent_dialog)
        sel_dialog.grab_set()
        sel_dialog.attributes('-topmost', True)

        tk.Label(sel_dialog, text="اختر المستفيد:", font=('Arial', 12)).pack(pady=15)
        owner_var = tk.StringVar()
        owner_combo = ttk.Combobox(sel_dialog, textvariable=owner_var,
                                   values=[name for _, name in owners], state='readonly', width=30)
        owner_combo.pack(pady=10)
        owner_combo.focus_set()

        tk.Label(sel_dialog, text=f"المبلغ: {amount:,.0f} ل.س", font=('Arial', 11)).pack(pady=5)

        def confirm():
            selected_name = owner_var.get()
            if not selected_name:
                messagebox.showerror("خطأ", "اختر مستفيداً")
                return
            owner_id = next((oid for oid, name in owners if name == selected_name), None)
            if not owner_id:
                messagebox.showerror("خطأ", "المستفيد غير موجود")
                return
            if profit_type == 'manager':
                res = add_method(daily_id, owner_id, amount, *extra_args, note, self.user_data.get('id', 1))
            else:
                res = add_method(daily_id, owner_id, amount, note, self.user_data.get('id', 1))
            if res['success']:
                sel_dialog.destroy()
                parent_dialog.destroy()
                self.load_current()
                messagebox.showinfo("تم", "تم توزيع الأرباح بنجاح")
            else:
                messagebox.showerror("خطأ", res.get('error'))

        tk.Button(sel_dialog, text="تأكيد", command=confirm, bg='#27ae60', fg='white', width=15).pack(pady=20)
        tk.Button(sel_dialog, text="إلغاء", command=sel_dialog.destroy, bg='#e74c3c', fg='white', width=15).pack(pady=5)

    def show_weekly_inventory(self):
        win = tk.Toplevel(self)
        win.title("الجرد الأسبوعي للصندوق")
        win.geometry("1200x500")  # تكبير قليلاً لاستيعاب الأعمدة الجديدة

        frame = tk.Frame(win)
        frame.pack(fill='x', padx=10, pady=10)

        tk.Label(frame, text="من تاريخ:").pack(side='left')
        start_entry = tk.Entry(frame, width=12)
        start_entry.pack(side='left', padx=5)
        start_entry.insert(0, (date.today() - timedelta(days=7)).isoformat())

        tk.Label(frame, text="إلى تاريخ:").pack(side='left')
        end_entry = tk.Entry(frame, width=12)
        end_entry.pack(side='left', padx=5)
        end_entry.insert(0, date.today().isoformat())

        def generate():
            try:
                s = datetime.strptime(start_entry.get(), '%Y-%m-%d').date()
                e = datetime.strptime(end_entry.get(), '%Y-%m-%d').date()
            except:
                messagebox.showerror("خطأ", "صيغة التاريخ غير صحيحة")
                return
            res = self.daily_mgr.generate_weekly_inventory(s, e, self.user_data.get('id', 1))
            if res['success']:
                messagebox.showinfo("تم", "تم إنشاء الجرد الأسبوعي")
                load_inventories()
            else:
                messagebox.showerror("خطأ", res.get('error'))

        tk.Button(frame, text="توليد الجرد", command=generate, bg='#3498db', fg='white').pack(side='left', padx=10)

        # تعريف الأعمدة بالترتيب المطلوب
        columns = ('id', 'start', 'end', 'opening', 'collections', 'expenses',
                   'repair_expansion', 'energy', 'fuel', 'profits', 'closing')
        tree = ttk.Treeview(win, columns=columns, show='headings')

        tree.heading('id', text='ID')
        tree.heading('start', text='بداية الأسبوع')
        tree.heading('end', text='نهاية الأسبوع')
        tree.heading('opening', text='رصيد أول')
        tree.heading('collections', text='الجبايات')
        tree.heading('expenses', text='المصاريف')
        tree.heading('repair_expansion', text='إصلاح وتوسعة')
        tree.heading('energy', text='أرباح طاقة')
        tree.heading('fuel', text='مازوت')
        tree.heading('profits', text='الأرباح')
        tree.heading('closing', text='رصيد آخر')

        tree.column('id', width=40, anchor='center')
        tree.column('start', width=100, anchor='center')
        tree.column('end', width=100, anchor='center')
        tree.column('opening', width=110, anchor='center')
        tree.column('collections', width=110, anchor='center')
        tree.column('expenses', width=100, anchor='center')
        tree.column('repair_expansion', width=120, anchor='center')
        tree.column('energy', width=100, anchor='center')
        tree.column('fuel', width=90, anchor='center')
        tree.column('profits', width=90, anchor='center')
        tree.column('closing', width=110, anchor='center')

        tree.pack(fill='both', expand=True, padx=10, pady=10)

        def load_inventories():
            for item in tree.get_children():
                tree.delete(item)
            invs = self.daily_mgr.get_weekly_inventories()
            for inv in invs:
                tree.insert('', 'end', values=(
                    inv['id'],
                    inv['week_start'],
                    inv['week_end'],
                    f"{inv['total_opening']:,.0f}",
                    f"{inv['total_collections']:,.0f}",
                    f"{inv['total_expenses']:,.0f}",
                    f"{inv['total_repair_expansion']:,.0f}",
                    f"{inv['total_energy_profits']:,.0f}",
                    f"{inv['total_fuel']:,.0f}",
                    f"{inv['total_profits']:,.0f}",
                    f"{inv['total_closing']:,.0f}"
                ))

        load_inventories()

        def delete_selected():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("تنبيه", "اختر جرداً لحذفه")
                return
            inv_id = tree.item(selected[0])['values'][0]
            if messagebox.askyesno("تأكيد", f"هل تريد حذف الجرد رقم {inv_id}؟"):
                self.daily_mgr.delete_weekly_inventory(inv_id)
                load_inventories()
                messagebox.showinfo("تم", "تم حذف الجرد")

        tk.Button(win, text="🗑️ حذف الجرد المحدد", command=delete_selected, bg='#e74c3c', fg='white').pack(pady=5)