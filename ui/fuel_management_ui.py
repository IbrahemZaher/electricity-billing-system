# ui/fuel_management_ui.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import logging
from datetime import datetime, date, timedelta
import json
import traceback
from modules.fuel_management import FuelManagement
from database.connection import db
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class FuelManagementUI(tk.Toplevel):
    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.parent = parent
        self.user_data = user_data
        self.title("نسب التحويل وإدارة المازوت والطاقة")
        self.geometry("1400x900")
        
        self.colors = {
            'bg': '#f0f2f5',
            'fg': '#1a1a1a',
            'primary': '#0d6efd',
            'success': '#198754',
            'warning': '#ffc107',
            'danger': '#dc3545',
            'info': '#0dcaf0',
            'light': '#e9ecef',
            'dark': '#212529'
        }
        
        pwd = simpledialog.askstring("تأكيد الدخول", "هذه الواجهة مخصصة للمدراء فقط.\nالرجاء إدخال كلمة المرور:", show='*', parent=self)
        if pwd != "eyadkasemadmin123":
            messagebox.showerror("خطأ", "كلمة المرور غير صحيحة")
            self.destroy()
            return
        
        self.setup_styles()
        self.create_widgets()
        self.load_initial_data()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background=self.colors['bg'], borderwidth=0)
        style.configure("TNotebook.Tab", padding=[20, 12], font=('Segoe UI', 10, 'bold'))
        style.map("TNotebook.Tab",
                  background=[("selected", self.colors['primary'])],
                  foreground=[("selected", "white")])
        style.configure("TLabelframe", background=self.colors['bg'], relief='flat', borderwidth=1)
        style.configure("TLabelframe.Label", font=('Segoe UI', 11, 'bold'), foreground=self.colors['dark'])
        style.configure("Treeview",
                        rowheight=32,
                        font=('Segoe UI', 10),
                        background="white",
                        foreground=self.colors['fg'],
                        fieldbackground="white")
        style.configure("Treeview.Heading",
                        font=('Segoe UI', 10, 'bold'),
                        background=self.colors['light'],
                        foreground=self.colors['dark'])
        style.map("Treeview.Heading",
                  background=[('active', self.colors['primary'])])
        style.configure("TCombobox",
                        fieldbackground="white",
                        background="white",
                        padding=5)
        style.configure("TButton",
                        font=('Segoe UI', 10, 'bold'),
                        padding=(12, 6),
                        relief='flat',
                        background=self.colors['primary'],
                        foreground='white')
        style.map("TButton",
                  background=[('active', self.colors['info'])])
        style.configure("TEntry",
                        fieldbackground="white",
                        foreground="black",
                        borderwidth=1,
                        relief="solid")
        style.configure("TLabel",
                        background=self.colors['bg'],
                        foreground="black",
                        font=('Segoe UI', 10))

    def create_widgets(self):
        self.notebook = ttk.Notebook(self, style="TNotebook")
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.setup_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.setup_tab, text="⚙️ ضبط العدادات")
        self.create_setup_tab()

        self.operations_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.operations_tab, text="🛢️ عمليات المازوت")
        self.create_operations_tab()

        self.daily_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.daily_tab, text="📊 القراءات اليومية (مازوت)")
        self.create_daily_tab()

        self.energy_readings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.energy_readings_tab, text="🔋 قراءات الطاقة")
        self.create_energy_readings_tab()

        self.inventory_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.inventory_tab, text="📋 الجرد الأسبوعي")
        self.create_inventory_tab()

        self.history_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.history_tab, text="📋 سجل العمليات")
        self.create_history_tab()

        self.energy_account_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.energy_account_tab, text="💰 حسابات الطاقة")
        self.create_energy_account_tab()

    # -------------------- تبويب ضبط العدادات --------------------
    def create_setup_tab(self):
        main_canvas = tk.Canvas(self.setup_tab, highlightthickness=0, bg=self.colors['bg'])
        v_scroll = ttk.Scrollbar(self.setup_tab, orient='vertical', command=main_canvas.yview)
        main_canvas.configure(yscrollcommand=v_scroll.set)
        v_scroll.pack(side='right', fill='y')
        main_canvas.pack(side='left', fill='both', expand=True)
        
        inner_frame = tk.Frame(main_canvas, bg=self.colors['bg'])
        canvas_window = main_canvas.create_window((0, 0), window=inner_frame, anchor='nw')
        
        def configure_scroll(event):
            main_canvas.configure(scrollregion=main_canvas.bbox('all'))
        inner_frame.bind('<Configure>', configure_scroll)
        main_canvas.bind('<Configure>', lambda e: main_canvas.itemconfig(canvas_window, width=e.width))
        
        top_row = tk.Frame(inner_frame, bg=self.colors['bg'])
        top_row.pack(fill='both', expand=True, padx=10, pady=10)
        
        left_frame = tk.LabelFrame(top_row, text="عدادات المولدة", font=('Segoe UI', 12, 'bold'), bg=self.colors['bg'], fg=self.colors['dark'])
        left_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        self.create_generator_meters_ui(left_frame)
        
        mid_frame = tk.LabelFrame(top_row, text="عدادات القطاعات", font=('Segoe UI', 12, 'bold'), bg=self.colors['bg'], fg=self.colors['dark'])
        mid_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        self.create_sector_meters_ui(mid_frame)
        
        energy_frame = tk.LabelFrame(top_row, text="⚡ عدادات الطاقة", font=('Segoe UI', 12, 'bold'), bg=self.colors['bg'], fg=self.colors['dark'])
        energy_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        self.create_energy_meters_ui(energy_frame)
        
        bottom_frame = tk.LabelFrame(inner_frame, text="خزانات المازوت", font=('Segoe UI', 12, 'bold'), bg=self.colors['bg'], fg=self.colors['dark'])
        bottom_frame.pack(fill='x', padx=10, pady=(0,10))
        self.create_tanks_ui(bottom_frame)

    # -------------------- عدادات المولدة --------------------
    def create_generator_meters_ui(self, parent):
        btn_frame = tk.Frame(parent, bg=self.colors['bg'])
        btn_frame.pack(fill='x', pady=5)
        self._add_styled_button(btn_frame, "➕ إضافة", self.add_generator_meter, self.colors['success']).pack(side='left', padx=5)
        self._add_styled_button(btn_frame, "✏️ تعديل", self.edit_generator_meter, self.colors['warning']).pack(side='left', padx=5)
        self._add_styled_button(btn_frame, "🗑️ حذف", self.delete_generator_meter, self.colors['danger']).pack(side='left', padx=5)
        
        tree_frame = tk.Frame(parent, bg=self.colors['bg'])
        tree_frame.pack(fill='both', expand=True, pady=5)
        
        tree_canvas = tk.Canvas(tree_frame, highlightthickness=0, bg=self.colors['bg'])
        v_scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=tree_canvas.yview)
        h_scroll = ttk.Scrollbar(tree_frame, orient='horizontal', command=tree_canvas.xview)
        tree_canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.pack(side='right', fill='y')
        h_scroll.pack(side='bottom', fill='x')
        tree_canvas.pack(side='left', fill='both', expand=True)
        
        scrollable_frame = tk.Frame(tree_canvas, bg=self.colors['bg'])
        tree_canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        scrollable_frame.bind('<Configure>', lambda e: tree_canvas.configure(scrollregion=tree_canvas.bbox('all')))
        
        columns = ('id', 'name', 'code', 'notes')
        self.gen_tree = ttk.Treeview(scrollable_frame, columns=columns, show='headings', height=12)
        self.gen_tree.heading('id', text='ID')
        self.gen_tree.heading('name', text='الاسم')
        self.gen_tree.heading('code', text='الكود')
        self.gen_tree.heading('notes', text='ملاحظات')
        self.gen_tree.column('id', width=50, anchor='center')
        self.gen_tree.column('name', width=180)
        self.gen_tree.column('code', width=120)
        self.gen_tree.column('notes', width=200)
        self.gen_tree.pack(fill='both', expand=True)
        self._add_zebra_striping(self.gen_tree)

    def add_generator_meter(self):
        main_frame = self._create_dialog("إضافة عداد مولدة")
        tk.Label(main_frame, text="الاسم:*", font=('Segoe UI', 10), bg='white', fg='black').grid(row=0, column=0, padx=10, pady=10, sticky='e')
        name_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        name_entry.grid(row=0, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="الكود:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=1, column=0, padx=10, pady=10, sticky='e')
        code_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        code_entry.grid(row=1, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="ملاحظات:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=2, column=0, padx=10, pady=10, sticky='e')
        notes_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        notes_entry.grid(row=2, column=1, padx=10, pady=10)
        
        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("خطأ", "الاسم مطلوب")
                return
            data = {'name': name, 'code': code_entry.get().strip(), 'notes': notes_entry.get().strip()}
            res = FuelManagement.add_generator_meter(data)
            if res['success']:
                messagebox.showinfo("نجاح", "تمت الإضافة")
                main_frame.master.destroy()
                self.load_generators()
            else:
                messagebox.showerror("خطأ", res['error'])
        btn = self._add_styled_button(main_frame, "حفظ", save, self.colors['success'])
        btn.grid(row=3, columnspan=2, pady=15)

    

    

   

   

    # -------------------- عدادات الطاقة --------------------
    def create_energy_meters_ui(self, parent):
        btn_frame = tk.Frame(parent, bg=self.colors['bg'])
        btn_frame.pack(fill='x', pady=5)
        self._add_styled_button(btn_frame, "➕ إضافة", self.add_energy_meter, self.colors['success']).pack(side='left', padx=5)
        self._add_styled_button(btn_frame, "✏️ تعديل", self.edit_energy_meter, self.colors['warning']).pack(side='left', padx=5)
        self._add_styled_button(btn_frame, "🗑️ حذف", self.delete_energy_meter, self.colors['danger']).pack(side='left', padx=5)
        
        tree_frame = tk.Frame(parent, bg=self.colors['bg'])
        tree_frame.pack(fill='both', expand=True, pady=5)
        
        tree_canvas = tk.Canvas(tree_frame, highlightthickness=0, bg=self.colors['bg'])
        v_scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=tree_canvas.yview)
        h_scroll = ttk.Scrollbar(tree_frame, orient='horizontal', command=tree_canvas.xview)
        tree_canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.pack(side='right', fill='y')
        h_scroll.pack(side='bottom', fill='x')
        tree_canvas.pack(side='left', fill='both', expand=True)
        
        scrollable_frame = tk.Frame(tree_canvas, bg=self.colors['bg'])
        tree_canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        scrollable_frame.bind('<Configure>', lambda e: tree_canvas.configure(scrollregion=tree_canvas.bbox('all')))
        
        columns = ('id', 'name', 'code', 'notes')
        self.energy_tree = ttk.Treeview(scrollable_frame, columns=columns, show='headings', height=12)
        self.energy_tree.heading('id', text='ID')
        self.energy_tree.heading('name', text='الاسم')
        self.energy_tree.heading('code', text='الكود')
        self.energy_tree.heading('notes', text='ملاحظات')
        self.energy_tree.column('id', width=50, anchor='center')
        self.energy_tree.column('name', width=180)
        self.energy_tree.column('code', width=120)
        self.energy_tree.column('notes', width=200)
        self.energy_tree.pack(fill='both', expand=True)
        self._add_zebra_striping(self.energy_tree)

    def add_energy_meter(self):
        main_frame = self._create_dialog("إضافة عداد طاقة")
        tk.Label(main_frame, text="الاسم:*", font=('Segoe UI', 10), bg='white', fg='black').grid(row=0, column=0, padx=10, pady=10, sticky='e')
        name_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        name_entry.grid(row=0, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="الكود:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=1, column=0, padx=10, pady=10, sticky='e')
        code_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        code_entry.grid(row=1, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="ملاحظات:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=2, column=0, padx=10, pady=10, sticky='e')
        notes_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        notes_entry.grid(row=2, column=1, padx=10, pady=10)
        # ✅ حقل سعر التحويل الجديد
        tk.Label(main_frame, text="سعر الكيلو واط (ل.س):", font=('Segoe UI', 10), bg='white', fg='black').grid(row=3, column=0, padx=10, pady=10, sticky='e')
        rate_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        rate_entry.insert(0, "0")
        rate_entry.grid(row=3, column=1, padx=10, pady=10)

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("خطأ", "الاسم مطلوب")
                return
            try:
                rate = float(rate_entry.get())
            except ValueError:
                messagebox.showerror("خطأ", "سعر التحويل غير صحيح")
                return
            data = {
                'name': name,
                'code': code_entry.get().strip(),
                'notes': notes_entry.get().strip(),
                'conversion_rate': rate
            }
            res = FuelManagement.add_energy_meter(data)
            if res['success']:
                messagebox.showinfo("نجاح", "تمت الإضافة")
                main_frame.master.destroy()
                self.load_energy_meters()
            else:
                messagebox.showerror("خطأ", res['error'])
        btn = self._add_styled_button(main_frame, "حفظ", save, self.colors['success'])
        btn.grid(row=4, columnspan=2, pady=15)

    def edit_energy_meter(self):
        selected = self.energy_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "اختر عداداً أولاً")
            return
        values = self.energy_tree.item(selected[0])['values']
        mid = values[0]
        # ✅ جلب سعر التحويل الحالي من قاعدة البيانات
        with db.get_cursor() as cursor:
            cursor.execute("SELECT conversion_rate FROM energy_meters WHERE id=%s", (mid,))
            row = cursor.fetchone()
            old_rate = row['conversion_rate'] if row else 0.0

        main_frame = self._create_dialog("تعديل عداد طاقة")
        tk.Label(main_frame, text="الاسم:*", font=('Segoe UI', 10), bg='white', fg='black').grid(row=0, column=0, padx=10, pady=10, sticky='e')
        name_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10))
        name_entry.insert(0, values[1])
        name_entry.grid(row=0, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="الكود:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=1, column=0, padx=10, pady=10, sticky='e')
        code_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10))
        code_entry.insert(0, values[2])
        code_entry.grid(row=1, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="ملاحظات:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=2, column=0, padx=10, pady=10, sticky='e')
        notes_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10))
        notes_entry.insert(0, values[3])
        notes_entry.grid(row=2, column=1, padx=10, pady=10)
        # ✅ حقل تعديل السعر
        tk.Label(main_frame, text="سعر الكيلو واط (ل.س):", font=('Segoe UI', 10), bg='white', fg='black').grid(row=3, column=0, padx=10, pady=10, sticky='e')
        rate_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10))
        rate_entry.insert(0, str(old_rate))
        rate_entry.grid(row=3, column=1, padx=10, pady=10)

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("خطأ", "الاسم مطلوب")
                return
            try:
                rate = float(rate_entry.get())
            except ValueError:
                messagebox.showerror("خطأ", "سعر التحويل غير صحيح")
                return
            data = {
                'name': name,
                'code': code_entry.get().strip(),
                'notes': notes_entry.get().strip(),
                'conversion_rate': rate,
                'current_balance': None  # لا نغير الرصيد
            }
            res = FuelManagement.update_energy_meter(mid, data)
            if res['success']:
                messagebox.showinfo("نجاح", "تم التحديث")
                main_frame.master.destroy()
                self.load_energy_meters()
            else:
                messagebox.showerror("خطأ", res['error'])
        btn = self._add_styled_button(main_frame, "حفظ", save, self.colors['warning'])
        btn.grid(row=4, columnspan=2, pady=15)

    def delete_energy_meter(self):
        selected = self.energy_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "اختر عداداً أولاً")
            return
        mid = self.energy_tree.item(selected[0])['values'][0]
        if messagebox.askyesno("تأكيد", "هل تريد حذف هذا العداد؟"):
            res = FuelManagement.delete_energy_meter(mid)
            if res['success']:
                messagebox.showinfo("نجاح", "تم الحذف")
                self.load_energy_meters()
            else:
                messagebox.showerror("خطأ", res['error'])



    def add_purchase(self):
        try:
            data = {
                'purchase_date': self.purchase_date.get(),
                'quantity_liters': float(self.purchase_qty.get()),
                'price_per_liter': float(self.purchase_price.get()),
                'notes': self.purchase_notes.get()
            }
            # ✅ تمرير معرف المستخدم لتسجيل العملية
            res = FuelManagement.add_purchase(data, self.user_data.get('id'))
            if res['success']:
                messagebox.showinfo("نجاح", "تم تسجيل الشراء (وأضيف للمصاريف)")
                self.update_warehouse_stock()
                self.load_purchases()
                self.purchase_qty.delete(0, tk.END)
                self.purchase_price.delete(0, tk.END)
                # ✅ تحديث واجهة دفتر اليومية إن كانت مفتوحة
                self._refresh_daily_cash_ui()
            else:
                messagebox.showerror("خطأ", res['error'])
        except ValueError:
            messagebox.showerror("خطأ", "الكمية والسعر يجب أن يكونا أرقاماً")

    def _refresh_daily_cash_ui(self):
        """تحديث واجهة دفتر اليومية إن كانت مفتوحة"""
        for widget in self.parent.winfo_children():
            if widget.__class__.__name__ == 'DailyCashUI':
                widget.load_current()
                break






    def edit_generator_meter(self):
        selected = self.gen_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "اختر عداداً أولاً")
            return
        values = self.gen_tree.item(selected[0])['values']
        mid = values[0]
        main_frame = self._create_dialog("تعديل عداد مولدة")
        tk.Label(main_frame, text="الاسم:*", font=('Segoe UI', 10), bg='white', fg='black').grid(row=0, column=0, padx=10, pady=10, sticky='e')
        name_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        name_entry.insert(0, values[1])
        name_entry.grid(row=0, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="الكود:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=1, column=0, padx=10, pady=10, sticky='e')
        code_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        code_entry.insert(0, values[2])
        code_entry.grid(row=1, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="ملاحظات:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=2, column=0, padx=10, pady=10, sticky='e')
        notes_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        notes_entry.insert(0, values[3])
        notes_entry.grid(row=2, column=1, padx=10, pady=10)
        
        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("خطأ", "الاسم مطلوب")
                return
            data = {'name': name, 'code': code_entry.get().strip(), 'notes': notes_entry.get().strip()}
            res = FuelManagement.update_generator_meter(mid, data)
            if res['success']:
                messagebox.showinfo("نجاح", "تم التحديث")
                main_frame.master.destroy()
                self.load_generators()
            else:
                messagebox.showerror("خطأ", res['error'])
        btn = self._add_styled_button(main_frame, "حفظ", save, self.colors['warning'])
        btn.grid(row=3, columnspan=2, pady=15)

    def delete_generator_meter(self):
        selected = self.gen_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "اختر عداداً أولاً")
            return
        mid = self.gen_tree.item(selected[0])['values'][0]
        if messagebox.askyesno("تأكيد", "هل تريد حذف هذا العداد؟"):
            res = FuelManagement.delete_generator_meter(mid)
            if res['success']:
                messagebox.showinfo("نجاح", "تم الحذف")
                self.load_generators()
            else:
                messagebox.showerror("خطأ", res['error'])

    # -------------------- عدادات القطاعات --------------------
    def create_sector_meters_ui(self, parent):
        btn_frame = tk.Frame(parent, bg=self.colors['bg'])
        btn_frame.pack(fill='x', pady=5)
        self._add_styled_button(btn_frame, "➕ إضافة", self.add_sector_meter, self.colors['success']).pack(side='left', padx=5)
        self._add_styled_button(btn_frame, "✏️ تعديل", self.edit_sector_meter, self.colors['warning']).pack(side='left', padx=5)
        self._add_styled_button(btn_frame, "🗑️ حذف", self.delete_sector_meter, self.colors['danger']).pack(side='left', padx=5)
        
        tree_frame = tk.Frame(parent, bg=self.colors['bg'])
        tree_frame.pack(fill='both', expand=True, pady=5)
        
        tree_canvas = tk.Canvas(tree_frame, highlightthickness=0, bg=self.colors['bg'])
        v_scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=tree_canvas.yview)
        h_scroll = ttk.Scrollbar(tree_frame, orient='horizontal', command=tree_canvas.xview)
        tree_canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.pack(side='right', fill='y')
        h_scroll.pack(side='bottom', fill='x')
        tree_canvas.pack(side='left', fill='both', expand=True)
        
        scrollable_frame = tk.Frame(tree_canvas, bg=self.colors['bg'])
        tree_canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        scrollable_frame.bind('<Configure>', lambda e: tree_canvas.configure(scrollregion=tree_canvas.bbox('all')))
        
        columns = ('id', 'name', 'code', 'sector', 'notes')
        self.sector_tree = ttk.Treeview(scrollable_frame, columns=columns, show='headings', height=12)
        self.sector_tree.heading('id', text='ID')
        self.sector_tree.heading('name', text='الاسم')
        self.sector_tree.heading('code', text='الكود')
        self.sector_tree.heading('sector', text='القطاع')
        self.sector_tree.heading('notes', text='ملاحظات')
        self.sector_tree.column('id', width=50, anchor='center')
        self.sector_tree.column('name', width=180)
        self.sector_tree.column('code', width=120)
        self.sector_tree.column('sector', width=150)
        self.sector_tree.column('notes', width=200)
        self.sector_tree.pack(fill='both', expand=True)
        self._add_zebra_striping(self.sector_tree)

    def add_sector_meter(self):
        main_frame = self._create_dialog("إضافة عداد قطاع")
        tk.Label(main_frame, text="الاسم:*", font=('Segoe UI', 10), bg='white', fg='black').grid(row=0, column=0, padx=10, pady=10, sticky='e')
        name_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        name_entry.grid(row=0, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="الكود:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=1, column=0, padx=10, pady=10, sticky='e')
        code_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        code_entry.grid(row=1, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="القطاع (اختياري):", font=('Segoe UI', 10), bg='white', fg='black').grid(row=2, column=0, padx=10, pady=10, sticky='e')
        
        with db.get_cursor() as cursor:
            cursor.execute("SELECT id, name FROM sectors ORDER BY name")
            sectors = cursor.fetchall()
        sector_var = tk.StringVar()
        sector_combo = ttk.Combobox(main_frame, textvariable=sector_var, state='readonly', width=32, font=('Segoe UI', 10))
        sector_combo['values'] = [''] + [f"{s['id']} - {s['name']}" for s in sectors]
        sector_combo.grid(row=2, column=1, padx=10, pady=10)
        
        tk.Label(main_frame, text="ملاحظات:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=3, column=0, padx=10, pady=10, sticky='e')
        notes_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        notes_entry.grid(row=3, column=1, padx=10, pady=10)
        
        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("خطأ", "الاسم مطلوب")
                return
            sector_val = sector_var.get()
            sector_id = None
            if sector_val and ' - ' in sector_val:
                sector_id = int(sector_val.split(' - ')[0])
            data = {
                'name': name,
                'code': code_entry.get().strip(),
                'sector_id': sector_id,
                'notes': notes_entry.get().strip()
            }
            res = FuelManagement.add_sector_meter(data)
            if res['success']:
                messagebox.showinfo("نجاح", "تمت الإضافة")
                main_frame.master.destroy()
                self.load_sectors()
            else:
                messagebox.showerror("خطأ", res['error'])
        btn = self._add_styled_button(main_frame, "حفظ", save, self.colors['success'])
        btn.grid(row=4, columnspan=2, pady=15)

    def edit_sector_meter(self):
        selected = self.sector_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "اختر عداداً أولاً")
            return
        values = self.sector_tree.item(selected[0])['values']
        mid = values[0]
        main_frame = self._create_dialog("تعديل عداد قطاع")
        tk.Label(main_frame, text="الاسم:*", font=('Segoe UI', 10), bg='white', fg='black').grid(row=0, column=0, padx=10, pady=10, sticky='e')
        name_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        name_entry.insert(0, values[1])
        name_entry.grid(row=0, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="الكود:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=1, column=0, padx=10, pady=10, sticky='e')
        code_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        code_entry.insert(0, values[2])
        code_entry.grid(row=1, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="القطاع:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=2, column=0, padx=10, pady=10, sticky='e')
        
        with db.get_cursor() as cursor:
            cursor.execute("SELECT id, name FROM sectors ORDER BY name")
            sectors = cursor.fetchall()
        sector_var = tk.StringVar()
        sector_combo = ttk.Combobox(main_frame, textvariable=sector_var, state='readonly', width=32, font=('Segoe UI', 10))
        sector_combo['values'] = [''] + [f"{s['id']} - {s['name']}" for s in sectors]
        current_sector_display = values[3] if values[3] else ''
        if current_sector_display:
            sector_combo.set(current_sector_display)
        sector_combo.grid(row=2, column=1, padx=10, pady=10)
        
        tk.Label(main_frame, text="ملاحظات:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=3, column=0, padx=10, pady=10, sticky='e')
        notes_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        notes_entry.insert(0, values[4])
        notes_entry.grid(row=3, column=1, padx=10, pady=10)
        
        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("خطأ", "الاسم مطلوب")
                return
            sector_val = sector_var.get()
            sector_id = None
            if sector_val and ' - ' in sector_val:
                sector_id = int(sector_val.split(' - ')[0])
            data = {
                'name': name,
                'code': code_entry.get().strip(),
                'sector_id': sector_id,
                'notes': notes_entry.get().strip()
            }
            res = FuelManagement.update_sector_meter(mid, data)
            if res['success']:
                messagebox.showinfo("نجاح", "تم التحديث")
                main_frame.master.destroy()
                self.load_sectors()
            else:
                messagebox.showerror("خطأ", res['error'])
        btn = self._add_styled_button(main_frame, "حفظ", save, self.colors['warning'])
        btn.grid(row=4, columnspan=2, pady=15)

    def delete_sector_meter(self):
        selected = self.sector_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "اختر عداداً أولاً")
            return
        mid = self.sector_tree.item(selected[0])['values'][0]
        if messagebox.askyesno("تأكيد", "هل تريد حذف هذا العداد؟"):
            res = FuelManagement.delete_sector_meter(mid)
            if res['success']:
                messagebox.showinfo("نجاح", "تم الحذف")
                self.load_sectors()
            else:
                messagebox.showerror("خطأ", res['error'])










    # -------------------- خزانات المازوت --------------------
    def create_tanks_ui(self, parent):
        btn_frame = tk.Frame(parent, bg=self.colors['bg'])
        btn_frame.pack(fill='x', pady=5)
        self._add_styled_button(btn_frame, "➕ إضافة خزان", self.add_tank, self.colors['success']).pack(side='left', padx=5)
        self._add_styled_button(btn_frame, "✏️ تعديل", self.edit_tank, self.colors['warning']).pack(side='left', padx=5)
        self._add_styled_button(btn_frame, "🗑️ حذف", self.delete_tank, self.colors['danger']).pack(side='left', padx=5)
        
        tree_frame = tk.Frame(parent, bg=self.colors['bg'])
        tree_frame.pack(fill='both', expand=True, pady=5)
        
        tree_canvas = tk.Canvas(tree_frame, highlightthickness=0, bg=self.colors['bg'])
        v_scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=tree_canvas.yview)
        h_scroll = ttk.Scrollbar(tree_frame, orient='horizontal', command=tree_canvas.xview)
        tree_canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.pack(side='right', fill='y')
        h_scroll.pack(side='bottom', fill='x')
        tree_canvas.pack(side='left', fill='both', expand=True)
        
        scrollable_frame = tk.Frame(tree_canvas, bg=self.colors['bg'])
        tree_canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        scrollable_frame.bind('<Configure>', lambda e: tree_canvas.configure(scrollregion=tree_canvas.bbox('all')))
        
        columns = ('id', 'name', 'liters_per_cm', 'notes')
        self.tank_tree = ttk.Treeview(scrollable_frame, columns=columns, show='headings', height=5)
        self.tank_tree.heading('id', text='ID')
        self.tank_tree.heading('name', text='الاسم')
        self.tank_tree.heading('liters_per_cm', text='لتر/سم')
        self.tank_tree.heading('notes', text='ملاحظات')
        self.tank_tree.column('id', width=50, anchor='center')
        self.tank_tree.column('name', width=200)
        self.tank_tree.column('liters_per_cm', width=100, anchor='center')
        self.tank_tree.column('notes', width=300)
        self.tank_tree.pack(fill='both', expand=True)
        self._add_zebra_striping(self.tank_tree)

    def add_tank(self):
        main_frame = self._create_dialog("إضافة خزان مازوت")
        tk.Label(main_frame, text="الاسم:*", font=('Segoe UI', 10), bg='white', fg='black').grid(row=0, column=0, padx=10, pady=10, sticky='e')
        name_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        name_entry.grid(row=0, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="لتر لكل سم:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=1, column=0, padx=10, pady=10, sticky='e')
        liter_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        liter_entry.insert(0, "10.75")
        liter_entry.grid(row=1, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="ملاحظات:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=2, column=0, padx=10, pady=10, sticky='e')
        notes_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        notes_entry.grid(row=2, column=1, padx=10, pady=10)
        
        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("خطأ", "الاسم مطلوب")
                return
            try:
                liters = float(liter_entry.get())
            except:
                messagebox.showerror("خطأ", "قيمة اللتر لكل سم غير صحيحة")
                return
            data = {'name': name, 'liters_per_cm': liters, 'notes': notes_entry.get().strip()}
            res = FuelManagement.add_tank(data)
            if res['success']:
                messagebox.showinfo("نجاح", "تمت الإضافة")
                main_frame.master.destroy()
                self.load_tanks()
                self.update_transfer_tank_list()
            else:
                messagebox.showerror("خطأ", res['error'])
        btn = self._add_styled_button(main_frame, "حفظ", save, self.colors['success'])
        btn.grid(row=3, columnspan=2, pady=15)

    def edit_tank(self):
        selected = self.tank_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "اختر خزاناً أولاً")
            return
        values = self.tank_tree.item(selected[0])['values']
        tid = values[0]
        main_frame = self._create_dialog("تعديل خزان مازوت")
        tk.Label(main_frame, text="الاسم:*", font=('Segoe UI', 10), bg='white', fg='black').grid(row=0, column=0, padx=10, pady=10, sticky='e')
        name_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        name_entry.insert(0, values[1])
        name_entry.grid(row=0, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="لتر لكل سم:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=1, column=0, padx=10, pady=10, sticky='e')
        liter_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        liter_entry.insert(0, values[2])
        liter_entry.grid(row=1, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="ملاحظات:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=2, column=0, padx=10, pady=10, sticky='e')
        notes_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        notes_entry.insert(0, values[3])
        notes_entry.grid(row=2, column=1, padx=10, pady=10)
        
        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("خطأ", "الاسم مطلوب")
                return
            try:
                liters = float(liter_entry.get())
            except:
                messagebox.showerror("خطأ", "قيمة اللتر لكل سم غير صحيحة")
                return
            data = {'name': name, 'liters_per_cm': liters, 'notes': notes_entry.get().strip()}
            res = FuelManagement.update_tank(tid, data)
            if res['success']:
                messagebox.showinfo("نجاح", "تم التحديث")
                main_frame.master.destroy()
                self.load_tanks()
                self.update_transfer_tank_list()
            else:
                messagebox.showerror("خطأ", res['error'])
        btn = self._add_styled_button(main_frame, "حفظ", save, self.colors['warning'])
        btn.grid(row=3, columnspan=2, pady=15)

    def delete_tank(self):
        selected = self.tank_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "اختر خزاناً أولاً")
            return
        tid = self.tank_tree.item(selected[0])['values'][0]
        if messagebox.askyesno("تأكيد", "هل تريد حذف هذا الخزان؟"):
            res = FuelManagement.delete_tank(tid)
            if res['success']:
                self.load_tanks()
                self.update_transfer_tank_list()
            else:
                messagebox.showerror("خطأ", res['error'])

    # -------------------- تبويب عمليات المازوت --------------------
    def create_operations_tab(self):
        frame = tk.Frame(self.operations_tab, bg=self.colors['bg'])
        frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        purchase_frame = tk.LabelFrame(frame, text="شراء مازوت", font=('Segoe UI', 12, 'bold'), bg=self.colors['bg'], fg=self.colors['dark'])
        purchase_frame.pack(fill='x', pady=10)
        self.create_purchase_ui(purchase_frame)
        
        transfer_frame = tk.LabelFrame(frame, text="تنزيل مازوت للخزانات", font=('Segoe UI', 12, 'bold'), bg=self.colors['bg'], fg=self.colors['dark'])
        transfer_frame.pack(fill='x', pady=10)
        self.create_transfer_ui(transfer_frame)
        
        self.warehouse_label = tk.Label(frame, text="رصيد المستودع: -- لتر", font=('Segoe UI', 13, 'bold'), bg=self.colors['bg'], fg=self.colors['primary'])
        self.warehouse_label.pack(pady=20)
        self.update_warehouse_stock()

    def create_purchase_ui(self, parent):
        row = tk.Frame(parent, bg=self.colors['bg'])
        row.pack(fill='x', pady=8, padx=5)
        
        tk.Label(row, text="التاريخ:", font=('Segoe UI', 10), bg=self.colors['bg'], fg='black').pack(side='left', padx=8)
        self.purchase_date = tk.Entry(row, width=12, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        self.purchase_date.insert(0, date.today().isoformat())
        self.purchase_date.pack(side='left', padx=8)
        
        tk.Label(row, text="الكمية (لتر):", font=('Segoe UI', 10), bg=self.colors['bg'], fg='black').pack(side='left', padx=8)
        self.purchase_qty = tk.Entry(row, width=12, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        self.purchase_qty.pack(side='left', padx=8)
        
        tk.Label(row, text="سعر اللتر:", font=('Segoe UI', 10), bg=self.colors['bg'], fg='black').pack(side='left', padx=8)
        self.purchase_price = tk.Entry(row, width=12, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        self.purchase_price.pack(side='left', padx=8)
        
        tk.Label(row, text="ملاحظات:", font=('Segoe UI', 10), bg=self.colors['bg'], fg='black').pack(side='left', padx=8)
        self.purchase_notes = tk.Entry(row, width=20, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        self.purchase_notes.pack(side='left', padx=8)
        
        self._add_styled_button(row, "تسجيل شراء", self.add_purchase, self.colors['success'], padx=10).pack(side='left', padx=10)

    def create_transfer_ui(self, parent):
        row = tk.Frame(parent, bg=self.colors['bg'])
        row.pack(fill='x', pady=8, padx=5)
        
        tk.Label(row, text="التاريخ:", font=('Segoe UI', 10), bg=self.colors['bg'], fg='black').pack(side='left', padx=8)
        self.transfer_date = tk.Entry(row, width=12, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        self.transfer_date.insert(0, date.today().isoformat())
        self.transfer_date.pack(side='left', padx=8)
        
        tk.Label(row, text="الخزان:", font=('Segoe UI', 10), bg=self.colors['bg'], fg='black').pack(side='left', padx=8)
        self.transfer_tank = ttk.Combobox(row, state='readonly', width=20, font=('Segoe UI', 10))
        self.transfer_tank.pack(side='left', padx=8)
        
        tk.Label(row, text="الكمية (لتر):", font=('Segoe UI', 10), bg=self.colors['bg'], fg='black').pack(side='left', padx=8)
        self.transfer_qty = tk.Entry(row, width=12, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        self.transfer_qty.pack(side='left', padx=8)
        
        tk.Label(row, text="ملاحظات:", font=('Segoe UI', 10), bg=self.colors['bg'], fg='black').pack(side='left', padx=8)
        self.transfer_notes = tk.Entry(row, width=20, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        self.transfer_notes.pack(side='left', padx=8)
        
        self._add_styled_button(row, "تنزيل مازوت", self.add_transfer, self.colors['warning'], padx=10).pack(side='left', padx=10)



    def add_transfer(self):
        try:
            selected = self.transfer_tank.get()
            if not selected:
                messagebox.showerror("خطأ", "اختر خزاناً")
                return
            tank_id = int(selected.split(' - ')[0])
            data = {
                'transfer_date': self.transfer_date.get(),
                'tank_id': tank_id,
                'quantity_liters': float(self.transfer_qty.get()),
                'notes': self.transfer_notes.get()
            }
            res = FuelManagement.add_transfer(data)
            if res['success']:
                messagebox.showinfo("نجاح", "تم تنزيل المازوت")
                self.update_warehouse_stock()
                self.load_transfers()
                self.transfer_qty.delete(0, tk.END)
            else:
                messagebox.showerror("خطأ", res['error'])
        except ValueError:
            messagebox.showerror("خطأ", "الكمية يجب أن تكون رقماً")
        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ: {str(e)}")

    def update_warehouse_stock(self):
        try:
            stock = FuelManagement.get_warehouse_stock()
            self.warehouse_label.config(text=f"رصيد المستودع: {stock:,.2f} لتر")
        except:
            self.warehouse_label.config(text="رصيد المستودع: خطأ")

    # -------------------- تبويب القراءات اليومية (مازوت) --------------------
    def create_daily_tab(self):
        self.daily_container = tk.Frame(self.daily_tab, bg=self.colors['bg'])
        self.daily_container.pack(fill='both', expand=True, padx=15, pady=15)

        date_frame = tk.Frame(self.daily_container, bg=self.colors['bg'])
        date_frame.pack(fill='x', pady=10)
        tk.Label(date_frame, text="التاريخ (YYYY-MM-DD):", font=('Segoe UI', 10), bg=self.colors['bg'], fg='black').pack(side='left', padx=5)
        self.reading_date = tk.Entry(date_frame, width=12, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        self.reading_date.insert(0, date.today().isoformat())
        self.reading_date.pack(side='left', padx=5)
        
        self.load_btn = self._add_styled_button(date_frame, "تحميل / إنشاء", self.load_daily_interface, self.colors['primary'])
        self.load_btn.pack(side='left', padx=5)
        self.save_daily_btn = self._add_styled_button(date_frame, "💾 حفظ القراءات", self.save_daily, self.colors['success'], state='disabled')
        self.save_daily_btn.pack(side='left', padx=5)
        self.preview_btn = self._add_styled_button(date_frame, "🧮 معاينة الحسابات", self.preview_daily, self.colors['warning'], state='disabled')
        self.preview_btn.pack(side='left', padx=5)
        self.daily_status = tk.Label(date_frame, text="", fg=self.colors['primary'], bg=self.colors['bg'], font=('Segoe UI', 10))
        self.daily_status.pack(side='left', padx=10)

        history_frame = tk.LabelFrame(self.daily_container, text="القراءات السابقة", font=('Segoe UI', 11, 'bold'), bg=self.colors['bg'], fg=self.colors['dark'])
        history_frame.pack(fill='both', expand=True, pady=10)
        
        self.history_tree = ttk.Treeview(history_frame, columns=('date', 'gen_output', 'sector_output', 'fuel_burned', 'gen_eff', 'sector_eff'), show='headings', height=8)
        self.history_tree.heading('date', text='التاريخ')
        self.history_tree.heading('gen_output', text='إنتاج المولدات')
        self.history_tree.heading('sector_output', text='إنتاج القطاعات')
        self.history_tree.heading('fuel_burned', text='حرق المازوت')
        self.history_tree.heading('gen_eff', text='نسبة تحويل المولدات')
        self.history_tree.heading('sector_eff', text='نسبة تحويل القطاعات')
        for col in ('date', 'gen_output', 'sector_output', 'fuel_burned'):
            self.history_tree.column(col, width=120, anchor='center')
        for col in ('gen_eff', 'sector_eff'):
            self.history_tree.column(col, width=150, anchor='center')
        self.history_tree.pack(fill='both', expand=True)
        self.history_tree.bind('<Double-1>', self.load_selected_reading)
        self._add_zebra_striping(self.history_tree)

        scroll_container = tk.LabelFrame(self.daily_container, text="إدخال القراءات", font=('Segoe UI', 11, 'bold'), bg=self.colors['bg'], fg=self.colors['dark'])
        scroll_container.pack(fill='both', expand=True, pady=10)

        self.canvas = tk.Canvas(scroll_container, highlightthickness=0, bg=self.colors['bg'])
        self.dynamic_scrollbar = ttk.Scrollbar(scroll_container, orient='vertical', command=self.canvas.yview)
        self.dynamic_frame = tk.Frame(self.canvas, bg=self.colors['bg'])

        self.canvas.configure(yscrollcommand=self.dynamic_scrollbar.set)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.dynamic_frame, anchor='nw')

        self.dynamic_scrollbar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)

        self.dynamic_frame.bind('<Configure>', self._on_dynamic_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind("<MouseWheel>", _on_mousewheel)
        self.dynamic_frame.bind("<MouseWheel>", _on_mousewheel)

        self._add_styled_button(date_frame, "🔄 تحديث قائمة القراءات", self.load_readings_list, self.colors['info']).pack(side='left', padx=5)
        
        self.load_readings_list()

    def _on_dynamic_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def load_readings_list(self):
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        readings = FuelManagement.get_daily_readings(date(2000,1,1), date.today())
        for r in readings:
            self.history_tree.insert('', 'end', values=(
                r['reading_date'],
                f"{r['generator_output']:,.0f}",
                f"{r['sector_output']:,.0f}",
                f"{r['total_fuel_burned']:,.0f}",
                f"{r['generator_efficiency']:.4f}",
                f"{r['sector_efficiency']:.4f}"
            ))

    def load_selected_reading(self, event):
        selected = self.history_tree.selection()
        if not selected:
            return
        date_str = self.history_tree.item(selected[0])['values'][0]
        self.reading_date.delete(0, tk.END)
        self.reading_date.insert(0, date_str)
        self.load_daily_interface()

    def preview_daily(self):
        selected_date = self.reading_date.get()
        try:
            d = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except:
            messagebox.showerror("خطأ", "التاريخ بصيغة YYYY-MM-DD")
            return
        gen_readings = {}
        for mid, entry in self.gen_entries.items():
            val = entry.get().strip()
            if val:
                try:
                    gen_readings[str(mid)] = float(val)
                except:
                    messagebox.showerror("خطأ", f"قيمة عداد المولدة {mid} غير رقمية")
                    return
        sec_readings = {}
        for mid, entry in self.sec_entries.items():
            val = entry.get().strip()
            if val:
                try:
                    sec_readings[str(mid)] = float(val)
                except:
                    messagebox.showerror("خطأ", f"قيمة عداد القطاع {mid} غير رقمية")
                    return
        tank_readings = {}
        for tid, entry in self.tank_entries.items():
            val = entry.get().strip()
            if val:
                try:
                    tank_readings[str(tid)] = float(val)
                except:
                    messagebox.showerror("خطأ", f"قيمة خزان {tid} غير رقمية")
                    return
        mock_data = {
            'reading_date': d,
            'generator_readings': gen_readings,
            'sector_readings': sec_readings,
            'tank_readings': tank_readings,
            'energy_readings': {},
            'notes': ''
        }
        res = self.calculate_preview(mock_data)
        if res['success']:
            messagebox.showinfo("معاينة الحسابات",
                f"إنتاج المولدات: {res['generator_output']:.2f}\n"
                f"إنتاج القطاعات: {res['sector_output']:.2f}\n"
                f"حرق المازوت: {res['total_fuel_burned']:.2f}\n"
                f"نسبة تحويل المولدات: {res['gen_efficiency']:.4f}\n"
                f"نسبة تحويل القطاعات: {res['sector_efficiency']:.4f}"
            )
        else:
            messagebox.showerror("خطأ", res['error'])

    def calculate_preview(self, data):
        try:
            reading_date = data['reading_date']
            prev = FuelManagement.get_previous_day_readings(reading_date - timedelta(days=1))
            cur_gen = data.get('generator_readings', {})
            cur_sector = data.get('sector_readings', {})
            cur_tanks = data.get('tank_readings', {})
            prev_gen = prev['generator_readings'] if prev else {}
            prev_sector = prev['sector_readings'] if prev else {}
            prev_tanks = prev['tank_readings'] if prev else {}
            
            gen_output = 0.0
            for mid, cur_val in cur_gen.items():
                prev_val = float(prev_gen.get(str(mid), 0))
                cur_val_f = float(cur_val)
                gen_output += max(cur_val_f - prev_val, 0)
            
            sector_output = 0.0
            for mid, cur_val in cur_sector.items():
                prev_val = float(prev_sector.get(str(mid), 0))
                cur_val_f = float(cur_val)
                sector_output += max(cur_val_f - prev_val, 0)
            
            total_fuel_burned = 0.0
            with db.get_cursor() as cursor:
                cursor.execute(
                    "SELECT tank_id, SUM(quantity_liters) as added FROM fuel_transfers WHERE transfer_date = %s GROUP BY tank_id",
                    (reading_date,)
                )
                added_dict = {row['tank_id']: float(row['added']) for row in cursor.fetchall()}
            
            tanks_info = {t['id']: float(t['liters_per_cm']) for t in FuelManagement.get_tanks()}
            for tank_id, cur_cm in cur_tanks.items():
                prev_cm = float(prev_tanks.get(str(tank_id), 0))
                added = added_dict.get(int(tank_id), 0.0)
                liters_per_cm = tanks_info.get(int(tank_id), 10.75)
                burned = (prev_cm - float(cur_cm)) * liters_per_cm + added
                if burned < 0:
                    burned = 0
                total_fuel_burned += burned
            
            gen_efficiency = gen_output / total_fuel_burned if total_fuel_burned > 0 else 0
            sector_efficiency = sector_output / total_fuel_burned if total_fuel_burned > 0 else 0
            
            return {
                'success': True,
                'generator_output': gen_output,
                'sector_output': sector_output,
                'total_fuel_burned': total_fuel_burned,
                'gen_efficiency': gen_efficiency,
                'sector_efficiency': sector_efficiency
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def load_daily_interface(self):
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()
        self.gen_entries = {}
        self.sec_entries = {}
        self.tank_entries = {}
        self.energy_entries = {}
        
        gen_meters = FuelManagement.get_generator_meters()
        if gen_meters:
            gen_frame = tk.LabelFrame(self.dynamic_frame, text="عدادات المولدة", font=('Segoe UI', 11, 'bold'), bg=self.colors['bg'], fg=self.colors['dark'])
            gen_frame.pack(fill='x', pady=8, padx=5)
            for m in gen_meters:
                row = tk.Frame(gen_frame, bg=self.colors['bg'])
                row.pack(fill='x', pady=4)
                tk.Label(row, text=f"{m['name']} (ID:{m['id']}):", width=25, anchor='e', font=('Segoe UI', 10), bg=self.colors['bg'], fg='black').pack(side='left', padx=8)
                entry = tk.Entry(row, width=18, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
                entry.pack(side='left', padx=8)
                self.gen_entries[m['id']] = entry
        
        sec_meters = FuelManagement.get_sector_meters()
        if sec_meters:
            sec_frame = tk.LabelFrame(self.dynamic_frame, text="عدادات القطاعات", font=('Segoe UI', 11, 'bold'), bg=self.colors['bg'], fg=self.colors['dark'])
            sec_frame.pack(fill='x', pady=8, padx=5)
            for m in sec_meters:
                row = tk.Frame(sec_frame, bg=self.colors['bg'])
                row.pack(fill='x', pady=4)
                label_text = f"{m['name']} (ID:{m['id']})"
                if m.get('sector_name'):
                    label_text += f" - {m['sector_name']}"
                tk.Label(row, text=label_text, width=25, anchor='e', font=('Segoe UI', 10), bg=self.colors['bg'], fg='black').pack(side='left', padx=8)
                entry = tk.Entry(row, width=18, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
                entry.pack(side='left', padx=8)
                self.sec_entries[m['id']] = entry
        
        tanks = FuelManagement.get_tanks()
        if tanks:
            tank_frame = tk.LabelFrame(self.dynamic_frame, text="قراءات خزانات المازوت (بالسنتيمتر)", font=('Segoe UI', 11, 'bold'), bg=self.colors['bg'], fg=self.colors['dark'])
            tank_frame.pack(fill='x', pady=8, padx=5)
            for t in tanks:
                row = tk.Frame(tank_frame, bg=self.colors['bg'])
                row.pack(fill='x', pady=4)
                tk.Label(row, text=f"{t['name']} (ID:{t['id']}) - لتر/سم: {t['liters_per_cm']}:", width=30, anchor='e', font=('Segoe UI', 10), bg=self.colors['bg'], fg='black').pack(side='left', padx=8)
                entry = tk.Entry(row, width=18, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
                entry.pack(side='left', padx=8)
                self.tank_entries[t['id']] = entry
        
        selected_date = self.reading_date.get()
        try:
            d = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except:
            messagebox.showerror("خطأ", "التاريخ بصيغة YYYY-MM-DD")
            return
        existing = FuelManagement.get_daily_readings(d, d)
        if existing:
            row = existing[0]
            gen_data = row['generator_readings']
            for mid, entry in self.gen_entries.items():
                entry.delete(0, tk.END)
                entry.insert(0, str(gen_data.get(str(mid), '')))
            sec_data = row['sector_readings']
            for mid, entry in self.sec_entries.items():
                entry.delete(0, tk.END)
                entry.insert(0, str(sec_data.get(str(mid), '')))
            tank_data = row['tank_readings']
            for tid, entry in self.tank_entries.items():
                entry.delete(0, tk.END)
                entry.insert(0, str(tank_data.get(str(tid), '')))
            self.daily_status.config(text="بيانات محفوظة - قم بتعديل ثم اضغط حفظ")
        else:
            for entry in self.gen_entries.values():
                entry.delete(0, tk.END)
            for entry in self.sec_entries.values():
                entry.delete(0, tk.END)
            for entry in self.tank_entries.values():
                entry.delete(0, tk.END)
            self.daily_status.config(text="بيانات جديدة - أدخل القراءات ثم اضغط حفظ")
        self.save_daily_btn.config(state='normal')
        self.preview_btn.config(state='normal')

    def save_daily(self):
        selected_date = self.reading_date.get()
        try:
            d = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except:
            messagebox.showerror("خطأ", "التاريخ بصيغة YYYY-MM-DD")
            return
        gen_readings = {}
        for mid, entry in self.gen_entries.items():
            val = entry.get().strip()
            if val:
                try:
                    gen_readings[str(mid)] = float(val)
                except:
                    messagebox.showerror("خطأ", f"قيمة عداد المولدة {mid} غير رقمية")
                    return
        sec_readings = {}
        for mid, entry in self.sec_entries.items():
            val = entry.get().strip()
            if val:
                try:
                    sec_readings[str(mid)] = float(val)
                except:
                    messagebox.showerror("خطأ", f"قيمة عداد القطاع {mid} غير رقمية")
                    return
        tank_readings = {}
        for tid, entry in self.tank_entries.items():
            val = entry.get().strip()
            if val:
                try:
                    tank_readings[str(tid)] = float(val)
                except:
                    messagebox.showerror("خطأ", f"قيمة خزان {tid} غير رقمية")
                    return
        data = {
            'reading_date': d,
            'generator_readings': gen_readings,
            'sector_readings': sec_readings,
            'tank_readings': tank_readings,
            'energy_readings': {},
            'notes': ''
        }
        res = FuelManagement.save_daily_reading(data)
        if res['success']:
            messagebox.showinfo("نجاح", f"تم حفظ القراءات لليوم {d}\nإنتاج المولدات: {res['generator_output']:.2f}\nإنتاج القطاعات: {res['sector_output']:.2f}\nحرق المازوت: {res['total_fuel_burned']:.2f}\nنسبة تحويل المولدات: {res['gen_efficiency']:.4f}\nنسبة تحويل القطاعات: {res['sector_efficiency']:.4f}")
            self.daily_status.config(text="تم الحفظ بنجاح")
            self.load_readings_list()
        else:
            messagebox.showerror("خطأ", res['error'])

    # -------------------- تبويب قراءات الطاقة --------------------
    def create_energy_readings_tab(self):
        frame = tk.Frame(self.energy_readings_tab, bg=self.colors['bg'])
        frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        date_frame = tk.Frame(frame, bg=self.colors['bg'])
        date_frame.pack(fill='x', pady=10)
        tk.Label(date_frame, text="التاريخ:", font=('Segoe UI', 10), bg=self.colors['bg'], fg='black').pack(side='left', padx=5)
        self.energy_date = tk.Entry(date_frame, width=12, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        self.energy_date.insert(0, date.today().isoformat())
        self.energy_date.pack(side='left', padx=5)
        self._add_styled_button(date_frame, "تحميل", self.load_energy_readings_interface, self.colors['primary']).pack(side='left', padx=5)
        self._add_styled_button(date_frame, "حفظ القراءات", self.save_energy_readings, self.colors['success']).pack(side='left', padx=5)
        self._add_styled_button(date_frame, "🗑️ حذف القراءة", self.delete_energy_reading, self.colors['danger']).pack(side='left', padx=5)
        
        self.energy_canvas = tk.Canvas(frame, highlightthickness=0, bg=self.colors['bg'])
        energy_scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.energy_canvas.yview)
        self.energy_dynamic_frame = tk.Frame(self.energy_canvas, bg=self.colors['bg'])
        self.energy_canvas.configure(yscrollcommand=energy_scrollbar.set)
        energy_scrollbar.pack(side='right', fill='y')
        self.energy_canvas.pack(side='left', fill='both', expand=True)
        self.energy_canvas_window = self.energy_canvas.create_window((0, 0), window=self.energy_dynamic_frame, anchor='nw')
        self.energy_dynamic_frame.bind('<Configure>', lambda e: self.energy_canvas.configure(scrollregion=self.energy_canvas.bbox('all')))
        self.energy_canvas.bind('<Configure>', lambda e: self.energy_canvas.itemconfig(self.energy_canvas_window, width=e.width))
        
        self.energy_entries = {}
        
        # إطار آخر 10 قراءات
        history_frame = tk.LabelFrame(frame, text="📋 آخر 10 قراءات طاقة", font=('Segoe UI', 11, 'bold'), bg=self.colors['bg'], fg=self.colors['dark'])
        history_frame.pack(fill='both', expand=True, pady=10)

        self.energy_history_tree = ttk.Treeview(history_frame, columns=('date', 'meter', 'value'), show='headings', height=5)
        self.energy_history_tree.heading('date', text='التاريخ')
        self.energy_history_tree.heading('meter', text='العداد')
        self.energy_history_tree.heading('value', text='القراءة')
        self.energy_history_tree.column('date', width=100, anchor='center')
        self.energy_history_tree.column('meter', width=150)
        self.energy_history_tree.column('value', width=100, anchor='center')
        self.energy_history_tree.pack(fill='both', expand=True)
        self._add_zebra_striping(self.energy_history_tree)

        self.load_energy_readings_interface()
        self.refresh_energy_history()

    def refresh_energy_history(self):
        for row in self.energy_history_tree.get_children():
            self.energy_history_tree.delete(row)
        readings = FuelManagement.get_last_energy_readings(10)
        for r in readings:
            self.energy_history_tree.insert('', 'end', values=(
                r['reading_date'],
                f"{r['meter_name']} (ID:{r['meter_id']})",
                f"{r['reading_value']:,.2f}"
            ))

    def load_energy_readings_interface(self):
        for widget in self.energy_dynamic_frame.winfo_children():
            widget.destroy()
        self.energy_entries.clear()
        
        meters = FuelManagement.get_energy_meters()
        if not meters:
            tk.Label(self.energy_dynamic_frame, text="لا توجد عدادات طاقة. قم بإضافتها أولاً من تبويب الضبط.",
                     font=('Segoe UI', 12), bg=self.colors['bg'], fg='red').pack(pady=20)
            return
        
        selected_date = self.energy_date.get()
        try:
            d = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except:
            messagebox.showerror("خطأ", "التاريخ بصيغة YYYY-MM-DD")
            return
        
        existing = FuelManagement.get_energy_readings_for_date(d)
        
        for m in meters:
            row = tk.Frame(self.energy_dynamic_frame, bg=self.colors['bg'])
            row.pack(fill='x', pady=5, padx=10)
            tk.Label(row, text=f"{m['name']} (ID:{m['id']}):", width=25, anchor='e',
                     font=('Segoe UI', 10), bg=self.colors['bg'], fg='black').pack(side='left', padx=8)
            entry = tk.Entry(row, width=20, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
            entry.pack(side='left', padx=8)
            if m['id'] in existing:
                entry.insert(0, str(existing[m['id']]))
            self.energy_entries[m['id']] = entry
        self.refresh_energy_history()

    def save_energy_readings(self):
        selected_date = self.energy_date.get()
        try:
            d = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except:
            messagebox.showerror("خطأ", "التاريخ بصيغة YYYY-MM-DD")
            return
        
        for meter_id, entry in self.energy_entries.items():
            val = entry.get().strip()
            if val:
                try:
                    reading = float(val)
                    res = FuelManagement.save_energy_reading(d, meter_id, reading, "")
                    if not res['success']:
                        messagebox.showerror("خطأ", f"خطأ في حفظ قراءة العداد {meter_id}: {res['error']}")
                        return
                except ValueError:
                    messagebox.showerror("خطأ", f"قيمة العداد {meter_id} غير رقمية")
                    return
        messagebox.showinfo("نجاح", "تم حفظ قراءات الطاقة")
        self.refresh_energy_history()

    def delete_energy_reading(self):
        """حذف قراءة الطاقة لليوم والعداد المختار"""
        selected_date = self.energy_date.get()
        try:
            d = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except:
            messagebox.showerror("خطأ", "التاريخ بصيغة YYYY-MM-DD")
            return
        
        meters = list(self.energy_entries.keys())
        if not meters:
            messagebox.showwarning("تحذير", "لا توجد عدادات طاقة لعرضها")
            return
        
        dialog = tk.Toplevel(self)
        dialog.title("حذف قراءة طاقة")
        dialog.configure(bg='white')
        dialog.grab_set()
        dialog.geometry("400x200")
        
        frame = tk.Frame(dialog, bg='white', padx=20, pady=20)
        frame.pack(fill='both', expand=True)
        
        tk.Label(frame, text="اختر العداد لحذف قراءته:", font=('Segoe UI', 11), bg='white').pack(pady=10)
        
        meter_var = tk.StringVar()
        meter_combo = ttk.Combobox(frame, textvariable=meter_var, state='readonly', width=40)
        meter_options = []
        for mid in meters:
            meter_name = f"عداد {mid}"
            for widget in self.energy_dynamic_frame.winfo_children():
                if isinstance(widget, tk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label) and f"(ID:{mid})" in child.cget('text'):
                            meter_name = child.cget('text').split(':')[0].strip()
                            break
            meter_options.append(f"{mid} - {meter_name}")
        meter_combo['values'] = meter_options
        meter_combo.pack(pady=10)
        
        def confirm_delete():
            selected = meter_var.get()
            if not selected:
                messagebox.showerror("خطأ", "اختر عداداً")
                return
            meter_id = int(selected.split(' - ')[0])
            if messagebox.askyesno("تأكيد الحذف", f"هل تريد حذف قراءة الطاقة للعداد {meter_id} بتاريخ {d}؟"):
                res = FuelManagement.delete_energy_reading(d, meter_id)
                if res['success']:
                    messagebox.showinfo("نجاح", "تم حذف القراءة")
                    dialog.destroy()
                    self.load_energy_readings_interface()
                    self.refresh_energy_history()
                else:
                    messagebox.showerror("خطأ", res['error'])
        
        btn = self._add_styled_button(frame, "حذف", confirm_delete, self.colors['danger'])
        btn.pack(pady=10)

    # -------------------- تبويب الجرد الأسبوعي --------------------
    def create_inventory_tab(self):
        frame = tk.Frame(self.inventory_tab, bg=self.colors['bg'])
        frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        top_frame = tk.Frame(frame, bg=self.colors['bg'])
        top_frame.pack(fill='x', pady=10)
        self._add_styled_button(top_frame, "🔄 تحديث الجرد", self.refresh_inventory, self.colors['info']).pack(side='left', padx=5)
        self._add_styled_button(top_frame, "➕ إنشاء جرد أسبوعي جديد", self.create_new_inventory, self.colors['success']).pack(side='left', padx=5)
        self._add_styled_button(top_frame, "🗑️ حذف جرد", self.delete_inventory, self.colors['danger']).pack(side='left', padx=5)
        
        self.inv_tree = ttk.Treeview(frame, columns=('id', 'cycle', 'start', 'end', 'gen', 'sector', 'fuel', 'gen_eff', 'sector_eff', 'energy', 'total_prod', 'warehouse'), show='headings', height=15)
        self.inv_tree.heading('id', text='ID')
        self.inv_tree.heading('cycle', text='اسم الدورة')
        self.inv_tree.heading('start', text='من تاريخ')
        self.inv_tree.heading('end', text='إلى تاريخ')
        self.inv_tree.heading('gen', text='إنتاج المولدات')
        self.inv_tree.heading('sector', text='إنتاج القطاعات')
        self.inv_tree.heading('fuel', text='حرق المازوت')
        self.inv_tree.heading('gen_eff', text='نسبة تحويل المولدات')
        self.inv_tree.heading('sector_eff', text='نسبة تحويل القطاعات')
        self.inv_tree.heading('energy', text='إنتاج الطاقة')
        self.inv_tree.heading('total_prod', text='الإنتاج الكلي')
        self.inv_tree.heading('warehouse', text='رصيد المستودع')
        
        # توسيع عرض الأعمدة
        self.inv_tree.column('id', width=60, anchor='center')
        self.inv_tree.column('cycle', width=100)
        self.inv_tree.column('start', width=100)
        self.inv_tree.column('end', width=100)
        self.inv_tree.column('gen', width=120)
        self.inv_tree.column('sector', width=120)
        self.inv_tree.column('fuel', width=120)
        self.inv_tree.column('gen_eff', width=120)
        self.inv_tree.column('sector_eff', width=120)
        self.inv_tree.column('energy', width=110)
        self.inv_tree.column('total_prod', width=110)
        self.inv_tree.column('warehouse', width=110)
        
        self.inv_tree.pack(fill='both', expand=True, pady=10)
        self.inv_tree.bind('<Double-1>', self.edit_cycle_name)
        self._add_zebra_striping(self.inv_tree)

    def refresh_inventory(self):
        if messagebox.askyesno("تحديث الجرد", "سيتم إعادة حساب الجرد بناءً على أحدث القراءات اليومية وعمليات المازوت.\nهل تريد المتابعة؟"):
            self.load_inventories()
            messagebox.showinfo("نجاح", "تم تحديث الجرد بنجاح")

    def delete_inventory(self):
        selected = self.inv_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "اختر جرداً أسبوعياً أولاً")
            return
        
        inv_id = self.inv_tree.item(selected[0])['values'][0]
        cycle_name = self.inv_tree.item(selected[0])['values'][1]
        
        pwd = simpledialog.askstring("تأكيد الحذف", "حذف الجرد الأسبوعي يتطلب كلمة مرور المدير.\nالرجاء إدخال كلمة المرور:", show='*', parent=self)
        if pwd != "eyadkasemadmin123":
            messagebox.showerror("خطأ", "كلمة المرور غير صحيحة")
            return
        
        if messagebox.askyesno("تأكيد الحذف", f"هل تريد حذف الجرد الأسبوعي '{cycle_name}' بشكل نهائي؟"):
            res = FuelManagement.delete_weekly_inventory(inv_id)
            if res['success']:
                messagebox.showinfo("نجاح", "تم حذف الجرد الأسبوعي")
                self.load_inventories()
            else:
                messagebox.showerror("خطأ", res['error'])

    def create_new_inventory(self):
        main_frame = self._create_dialog("جرد أسبوعي جديد")
        tk.Label(main_frame, text="اسم الدورة:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=0, column=0, padx=10, pady=10, sticky='e')
        name_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        name_entry.grid(row=0, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="تاريخ البداية (YYYY-MM-DD):", font=('Segoe UI', 10), bg='white', fg='black').grid(row=1, column=0, padx=10, pady=10, sticky='e')
        start_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        start_entry.grid(row=1, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="تاريخ النهاية (YYYY-MM-DD):", font=('Segoe UI', 10), bg='white', fg='black').grid(row=2, column=0, padx=10, pady=10, sticky='e')
        end_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        end_entry.grid(row=2, column=1, padx=10, pady=10)
        
        def generate():
            name = name_entry.get().strip()
            start = start_entry.get().strip()
            end = end_entry.get().strip()
            if not name or not start or not end:
                messagebox.showerror("خطأ", "جميع الحقول مطلوبة")
                return
            try:
                s = datetime.strptime(start, '%Y-%m-%d').date()
                e = datetime.strptime(end, '%Y-%m-%d').date()
            except:
                messagebox.showerror("خطأ", "صيغة التاريخ غير صحيحة")
                return
            res = FuelManagement.generate_weekly_inventory(name, s, e)
            if res['success']:
                messagebox.showinfo("نجاح", f"تم إنشاء الجرد للأسبوع {name}")
                main_frame.master.destroy()
                self.load_inventories()
            else:
                messagebox.showerror("خطأ", res['error'])
        btn = self._add_styled_button(main_frame, "توليد", generate, self.colors['success'])
        btn.grid(row=3, columnspan=2, pady=15)

    def edit_cycle_name(self, event):
        selected = self.inv_tree.selection()
        if not selected: return
        inv_id = self.inv_tree.item(selected[0])['values'][0]
        current_name = self.inv_tree.item(selected[0])['values'][1]
        new_name = simpledialog.askstring("تعديل اسم الدورة", "أدخل الاسم الجديد:", initialvalue=current_name)
        if new_name:
            res = FuelManagement.update_cycle_name(inv_id, new_name)
            if res['success']:
                self.load_inventories()
            else:
                messagebox.showerror("خطأ", res['error'])

    # -------------------- تبويب سجل العمليات --------------------
    def create_history_tab(self):
        main_frame = tk.Frame(self.history_tab, bg=self.colors['bg'])
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        purchase_frame = tk.LabelFrame(main_frame, text="عمليات شراء المازوت", font=('Segoe UI', 11, 'bold'), bg=self.colors['bg'], fg=self.colors['dark'])
        purchase_frame.pack(fill='both', expand=True, pady=5)

        btn_frame = tk.Frame(purchase_frame, bg=self.colors['bg'])
        btn_frame.pack(fill='x', pady=5)
        self._add_styled_button(btn_frame, "➕ إضافة شراء", self.open_add_purchase_dialog, self.colors['success']).pack(side='left', padx=5)
        self._add_styled_button(btn_frame, "✏️ تعديل شراء", self.edit_purchase, self.colors['warning']).pack(side='left', padx=5)
        self._add_styled_button(btn_frame, "🗑️ حذف شراء", self.delete_purchase, self.colors['danger']).pack(side='left', padx=5)

        tree_frame = tk.Frame(purchase_frame, bg=self.colors['bg'])
        tree_frame.pack(fill='both', expand=True)
        self.purchase_tree = ttk.Treeview(tree_frame, columns=('id', 'date', 'qty', 'price', 'total', 'notes'), show='headings', height=6)
        self.purchase_tree.heading('id', text='ID')
        self.purchase_tree.heading('date', text='التاريخ')
        self.purchase_tree.heading('qty', text='الكمية (لتر)')
        self.purchase_tree.heading('price', text='سعر اللتر')
        self.purchase_tree.heading('total', text='الإجمالي')
        self.purchase_tree.heading('notes', text='ملاحظات')
        for col in ('id', 'date', 'qty', 'price', 'total'):
            self.purchase_tree.column(col, width=100, anchor='center')
        self.purchase_tree.column('notes', width=200)
        self.purchase_tree.pack(side='left', fill='both', expand=True)
        scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=self.purchase_tree.yview)
        self.purchase_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self._add_zebra_striping(self.purchase_tree)

        transfer_frame = tk.LabelFrame(main_frame, text="عمليات تنزيل مازوت للخزانات", font=('Segoe UI', 11, 'bold'), bg=self.colors['bg'], fg=self.colors['dark'])
        transfer_frame.pack(fill='both', expand=True, pady=5)

        btn_frame2 = tk.Frame(transfer_frame, bg=self.colors['bg'])
        btn_frame2.pack(fill='x', pady=5)
        self._add_styled_button(btn_frame2, "➕ إضافة تنزيل", self.open_add_transfer_dialog, self.colors['success']).pack(side='left', padx=5)
        self._add_styled_button(btn_frame2, "✏️ تعديل تنزيل", self.edit_transfer, self.colors['warning']).pack(side='left', padx=5)
        self._add_styled_button(btn_frame2, "🗑️ حذف تنزيل", self.delete_transfer, self.colors['danger']).pack(side='left', padx=5)

        tree_frame2 = tk.Frame(transfer_frame, bg=self.colors['bg'])
        tree_frame2.pack(fill='both', expand=True)
        self.transfer_tree = ttk.Treeview(tree_frame2, columns=('id', 'date', 'tank', 'qty', 'notes'), show='headings', height=6)
        self.transfer_tree.heading('id', text='ID')
        self.transfer_tree.heading('date', text='التاريخ')
        self.transfer_tree.heading('tank', text='الخزان')
        self.transfer_tree.heading('qty', text='الكمية (لتر)')
        self.transfer_tree.heading('notes', text='ملاحظات')
        for col in ('id', 'date', 'qty'):
            self.transfer_tree.column(col, width=100, anchor='center')
        self.transfer_tree.column('tank', width=150)
        self.transfer_tree.column('notes', width=200)
        self.transfer_tree.pack(side='left', fill='both', expand=True)
        scroll2 = ttk.Scrollbar(tree_frame2, orient='vertical', command=self.transfer_tree.yview)
        self.transfer_tree.configure(yscrollcommand=scroll2.set)
        scroll2.pack(side='right', fill='y')
        self._add_zebra_striping(self.transfer_tree)

        self.load_purchases()
        self.load_transfers()

    def load_purchases(self):
        for row in self.purchase_tree.get_children():
            self.purchase_tree.delete(row)
        with db.get_cursor() as cursor:
            cursor.execute("SELECT id, purchase_date, quantity_liters, price_per_liter, total_cost, notes FROM fuel_purchases ORDER BY purchase_date DESC")
            rows = cursor.fetchall()
            for r in rows:
                self.purchase_tree.insert('', 'end', values=(r['id'], r['purchase_date'], f"{r['quantity_liters']:,.2f}", f"{r['price_per_liter']:,.2f}", f"{r['total_cost']:,.2f}", r['notes'] or ''))

    def load_transfers(self):
        for row in self.transfer_tree.get_children():
            self.transfer_tree.delete(row)
        with db.get_cursor() as cursor:
            cursor.execute("SELECT ft.id, ft.transfer_date, ft.quantity_liters, ft.notes, ft.tank_id, t.name FROM fuel_transfers ft JOIN fuel_tanks t ON ft.tank_id = t.id ORDER BY ft.transfer_date DESC")
            rows = cursor.fetchall()
            for r in rows:
                self.transfer_tree.insert('', 'end', values=(r['id'], r['transfer_date'], f"{r['name']} (ID:{r['tank_id']})", f"{r['quantity_liters']:,.2f}", r['notes'] or ''))

    def open_add_purchase_dialog(self):
        main_frame = self._create_dialog("إضافة شراء مازوت")
        tk.Label(main_frame, text="التاريخ (YYYY-MM-DD):", font=('Segoe UI', 10), bg='white', fg='black').grid(row=0, column=0, padx=10, pady=10, sticky='e')
        date_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        date_entry.insert(0, date.today().isoformat())
        date_entry.grid(row=0, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="الكمية (لتر):", font=('Segoe UI', 10), bg='white', fg='black').grid(row=1, column=0, padx=10, pady=10, sticky='e')
        qty_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        qty_entry.grid(row=1, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="سعر اللتر:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=2, column=0, padx=10, pady=10, sticky='e')
        price_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        price_entry.grid(row=2, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="ملاحظات:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=3, column=0, padx=10, pady=10, sticky='e')
        notes_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        notes_entry.grid(row=3, column=1, padx=10, pady=10)
        
        def save():
            try:
                data = {
                    'purchase_date': date_entry.get(),
                    'quantity_liters': float(qty_entry.get()),
                    'price_per_liter': float(price_entry.get()),
                    'notes': notes_entry.get()
                }
                res = FuelManagement.add_purchase(data)
                if res['success']:
                    messagebox.showinfo("نجاح", "تمت الإضافة")
                    self.load_purchases()
                    self.update_warehouse_stock()
                    main_frame.master.destroy()
                else:
                    messagebox.showerror("خطأ", res['error'])
            except ValueError:
                messagebox.showerror("خطأ", "الكمية والسعر يجب أن يكونا أرقاماً")
        btn = self._add_styled_button(main_frame, "حفظ", save, self.colors['success'])
        btn.grid(row=4, columnspan=2, pady=15)

    def edit_purchase(self):
        selected = self.purchase_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "اختر عملية شراء أولاً")
            return
        values = self.purchase_tree.item(selected[0])['values']
        pid = values[0]
        main_frame = self._create_dialog("تعديل شراء مازوت")
        tk.Label(main_frame, text="التاريخ (YYYY-MM-DD):", font=('Segoe UI', 10), bg='white', fg='black').grid(row=0, column=0, padx=10, pady=10, sticky='e')
        date_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        date_entry.insert(0, values[1])
        date_entry.grid(row=0, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="الكمية (لتر):", font=('Segoe UI', 10), bg='white', fg='black').grid(row=1, column=0, padx=10, pady=10, sticky='e')
        qty_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        qty_entry.insert(0, values[2].replace(',', ''))
        qty_entry.grid(row=1, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="سعر اللتر:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=2, column=0, padx=10, pady=10, sticky='e')
        price_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        price_entry.insert(0, values[3].replace(',', ''))
        price_entry.grid(row=2, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="ملاحظات:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=3, column=0, padx=10, pady=10, sticky='e')
        notes_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        notes_entry.insert(0, values[5] if len(values)>5 else '')
        notes_entry.grid(row=3, column=1, padx=10, pady=10)
                
        def save():
            try:
                data = {
                    'purchase_date': date_entry.get(),
                    'quantity_liters': self._clean_float(qty_entry.get()),
                    'price_per_liter': self._clean_float(price_entry.get()),
                    'notes': notes_entry.get()
                }
                with db.get_cursor() as cursor:
                    cursor.execute("""
                        UPDATE fuel_purchases 
                        SET purchase_date=%s, quantity_liters=%s, price_per_liter=%s, notes=%s 
                        WHERE id=%s
                    """, (data['purchase_date'], data['quantity_liters'], data['price_per_liter'], data['notes'], pid))
                self.load_purchases()
                self.update_warehouse_stock()
                messagebox.showinfo("نجاح", "تم التحديث")
                main_frame.master.destroy()
            except Exception as e:
                messagebox.showerror("خطأ", str(e))
        btn = self._add_styled_button(main_frame, "حفظ", save, self.colors['warning'])
        btn.grid(row=4, columnspan=2, pady=15)

    def delete_purchase(self):
        selected = self.purchase_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "اختر عملية شراء أولاً")
            return
        pid = self.purchase_tree.item(selected[0])['values'][0]
        if messagebox.askyesno("تأكيد", "هل تريد حذف عملية الشراء؟"):
            with db.get_cursor() as cursor:
                cursor.execute("DELETE FROM fuel_purchases WHERE id=%s", (pid,))
            self.load_purchases()
            self.update_warehouse_stock()
            messagebox.showinfo("نجاح", "تم الحذف")

    def open_add_transfer_dialog(self):
        main_frame = self._create_dialog("إضافة تنزيل مازوت")
        tk.Label(main_frame, text="التاريخ (YYYY-MM-DD):", font=('Segoe UI', 10), bg='white', fg='black').grid(row=0, column=0, padx=10, pady=10, sticky='e')
        date_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        date_entry.insert(0, date.today().isoformat())
        date_entry.grid(row=0, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="الخزان:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=1, column=0, padx=10, pady=10, sticky='e')
        tanks = FuelManagement.get_tanks()
        tank_var = tk.StringVar()
        tank_combo = ttk.Combobox(main_frame, textvariable=tank_var, state='readonly', width=32, font=('Segoe UI', 10))
        tank_combo['values'] = [f"{t['id']} - {t['name']}" for t in tanks]
        tank_combo.grid(row=1, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="الكمية (لتر):", font=('Segoe UI', 10), bg='white', fg='black').grid(row=2, column=0, padx=10, pady=10, sticky='e')
        qty_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        qty_entry.grid(row=2, column=1, padx=10, pady=10)
        tk.Label(main_frame, text="ملاحظات:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=3, column=0, padx=10, pady=10, sticky='e')
        notes_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        notes_entry.grid(row=3, column=1, padx=10, pady=10)
        
        def save():
            try:
                selected = tank_var.get()
                if not selected:
                    messagebox.showerror("خطأ", "اختر خزاناً")
                    return
                tank_id = int(selected.split(' - ')[0])
                data = {
                    'transfer_date': date_entry.get(),
                    'tank_id': tank_id,
                    'quantity_liters': float(qty_entry.get()),
                    'notes': notes_entry.get()
                }
                res = FuelManagement.add_transfer(data)
                if res['success']:
                    messagebox.showinfo("نجاح", "تمت الإضافة")
                    self.load_transfers()
                    self.update_warehouse_stock()
                    main_frame.master.destroy()
                else:
                    messagebox.showerror("خطأ", res['error'])
            except ValueError:
                messagebox.showerror("خطأ", "الكمية يجب أن تكون رقماً")
        btn = self._add_styled_button(main_frame, "حفظ", save, self.colors['success'])
        btn.grid(row=4, columnspan=2, pady=15)

    def edit_transfer(self):
        selected = self.transfer_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "اختر عملية تنزيل أولاً")
            return
        values = self.transfer_tree.item(selected[0])['values']
        tid = values[0]
        tank_display = values[2]
        import re
        match = re.search(r'ID:(\d+)', tank_display)
        if not match:
            messagebox.showerror("خطأ", "تعذر استخراج معرف الخزان")
            return
        tank_id = int(match.group(1))
        
        tanks = FuelManagement.get_tanks()
        tank_name = next((t['name'] for t in tanks if t['id'] == tank_id), "")
        if not tank_name:
            messagebox.showerror("خطأ", "الخزان غير موجود")
            return
        
        main_frame = self._create_dialog("تعديل تنزيل مازوت")
        
        tk.Label(main_frame, text="التاريخ (YYYY-MM-DD):", font=('Segoe UI', 10), bg='white', fg='black').grid(row=0, column=0, padx=10, pady=10, sticky='e')
        date_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        date_entry.insert(0, values[1])
        date_entry.grid(row=0, column=1, padx=10, pady=10)
        
        tk.Label(main_frame, text="الخزان:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=1, column=0, padx=10, pady=10, sticky='e')
        tank_var = tk.StringVar()
        tank_combo = ttk.Combobox(main_frame, textvariable=tank_var, state='readonly', width=32, font=('Segoe UI', 10))
        tank_combo['values'] = [f"{t['id']} - {t['name']}" for t in tanks]
        current_tank_text = f"{tank_id} - {tank_name}"
        tank_combo.set(current_tank_text)
        tank_combo.grid(row=1, column=1, padx=10, pady=10)
        
        tk.Label(main_frame, text="الكمية (لتر):", font=('Segoe UI', 10), bg='white', fg='black').grid(row=2, column=0, padx=10, pady=10, sticky='e')
        qty_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        qty_entry.insert(0, values[3].replace(',', ''))
        qty_entry.grid(row=2, column=1, padx=10, pady=10)
        
        tk.Label(main_frame, text="ملاحظات:", font=('Segoe UI', 10), bg='white', fg='black').grid(row=3, column=0, padx=10, pady=10, sticky='e')
        notes_entry = tk.Entry(main_frame, width=35, font=('Segoe UI', 10), relief='solid', borderwidth=1, bg='white', fg='black')
        notes_entry.insert(0, values[4] if len(values) > 4 else '')
        notes_entry.grid(row=3, column=1, padx=10, pady=10)
        
        def save():
            try:
                selected_tank = tank_var.get()
                if not selected_tank:
                    messagebox.showerror("خطأ", "اختر خزاناً")
                    return
                new_tank_id = int(selected_tank.split(' - ')[0])
                data = {
                    'transfer_date': date_entry.get(),
                    'tank_id': new_tank_id,
                    'quantity_liters': self._clean_float(qty_entry.get()),
                    'notes': notes_entry.get()
                }
                with db.get_cursor() as cursor:
                    cursor.execute("""
                        UPDATE fuel_transfers 
                        SET transfer_date=%s, tank_id=%s, quantity_liters=%s, notes=%s 
                        WHERE id=%s
                    """, (data['transfer_date'], data['tank_id'], data['quantity_liters'], data['notes'], tid))
                self.load_transfers()
                self.update_warehouse_stock()
                messagebox.showinfo("نجاح", "تم التحديث")
                main_frame.master.destroy()
            except Exception as e:
                messagebox.showerror("خطأ", str(e))
        
        btn = self._add_styled_button(main_frame, "حفظ", save, self.colors['warning'])
        btn.grid(row=4, columnspan=2, pady=15)

    def delete_transfer(self):
        selected = self.transfer_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "اختر عملية تنزيل أولاً")
            return
        tid = self.transfer_tree.item(selected[0])['values'][0]
        if messagebox.askyesno("تأكيد", "هل تريد حذف عملية التنزيل؟"):
            with db.get_cursor() as cursor:
                cursor.execute("DELETE FROM fuel_transfers WHERE id=%s", (tid,))
            self.load_transfers()
            self.update_warehouse_stock()
            messagebox.showinfo("نجاح", "تم الحذف")

    # -------------------- دوال تحميل البيانات --------------------
    def load_initial_data(self):
        self.load_generators()
        self.load_sectors()
        self.load_tanks()
        self.load_energy_meters()
        self.load_inventories()
        self.update_transfer_tank_list()
        self.load_purchases()
        self.load_transfers()

    def load_generators(self):
        for row in self.gen_tree.get_children():
            self.gen_tree.delete(row)
        meters = FuelManagement.get_generator_meters()
        for m in meters:
            self.gen_tree.insert('', 'end', values=(m['id'], m['name'], m.get('code',''), m.get('notes','')))

    def load_sectors(self):
        for row in self.sector_tree.get_children():
            self.sector_tree.delete(row)
        meters = FuelManagement.get_sector_meters()
        for m in meters:
            sector_display = m.get('sector_name', '') if m.get('sector_name') else ''
            self.sector_tree.insert('', 'end', values=(m['id'], m['name'], m.get('code',''), sector_display, m.get('notes','')))

    def load_tanks(self):
        for row in self.tank_tree.get_children():
            self.tank_tree.delete(row)
        tanks = FuelManagement.get_tanks()
        for t in tanks:
            self.tank_tree.insert('', 'end', values=(t['id'], t['name'], t['liters_per_cm'], t.get('notes','')))

    def load_energy_meters(self):
        for row in self.energy_tree.get_children():
            self.energy_tree.delete(row)
        meters = FuelManagement.get_energy_meters()
        for m in meters:
            self.energy_tree.insert('', 'end', values=(m['id'], m['name'], m.get('code',''), m.get('notes','')))

    def update_transfer_tank_list(self):
        tanks = FuelManagement.get_tanks()
        self.transfer_tank['values'] = [f"{t['id']} - {t['name']}" for t in tanks]

    def load_inventories(self):
        for row in self.inv_tree.get_children():
            self.inv_tree.delete(row)
        invs = FuelManagement.get_weekly_inventories()
        for inv in invs:
            self.inv_tree.insert('', 'end', values=(
                inv['id'], inv['cycle_name'], inv['start_date'], inv['end_date'],
                f"{inv['total_generator_output']:,.0f}",
                f"{inv['total_sector_output']:,.0f}",
                f"{inv['total_fuel_burned']:,.0f}",
                f"{inv['avg_generator_efficiency']:.4f}",
                f"{inv['avg_sector_efficiency']:.4f}",
                f"{inv['energy_output']:,.0f}",
                f"{inv['total_production']:,.0f}",
                f"{inv['warehouse_remaining_liters']:,.0f}"
            ))

    def on_close(self):
        self.destroy()

    # -------------------- دوال مساعدة --------------------
    def _add_styled_button(self, parent, text, command, bg_color, fg_color='white', state='normal', padx=12, pady=6):
        btn = tk.Button(parent, text=text, command=command, bg=bg_color, fg=fg_color,
                       relief='flat', font=('Segoe UI', 10, 'bold'), padx=padx, pady=pady,
                       state=state, cursor='hand2')
        def on_enter(e):
            btn['background'] = self._darken_color(bg_color)
        def on_leave(e):
            btn['background'] = bg_color
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def _darken_color(self, hex_color, factor=0.85):
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _create_dialog(self, title):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.configure(bg='white')
        dialog.grab_set()
        dialog.update_idletasks()
        width = 550
        height = 450
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.resizable(False, False)
        main_frame = tk.Frame(dialog, bg='white', padx=15, pady=15)
        main_frame.pack(fill='both', expand=True)
        return main_frame

    def _add_zebra_striping(self, treeview):
        def apply_tag():
            items = treeview.get_children()
            for i, item in enumerate(items):
                if i % 2 == 0:
                    treeview.tag_configure('even', background='#f2f2f2')
                    treeview.item(item, tags=('even',))
                else:
                    treeview.tag_configure('odd', background='white')
                    treeview.item(item, tags=('odd',))
        treeview.bind("<<TreeviewOpen>>", lambda e: apply_tag())
        apply_tag()

    def _clean_float(self, value):
        if value is None:
            return 0.0
        cleaned = str(value).strip().replace(',', '').replace(' ', '')
        if cleaned.count('.') > 1:
            parts = cleaned.split('.')
            cleaned = parts[0] + '.' + ''.join(parts[1:])
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def create_energy_account_tab(self):
        frame = tk.Frame(self.energy_account_tab, bg=self.colors['bg'])
        frame.pack(fill='both', expand=True, padx=15, pady=15)

        top = tk.Frame(frame, bg=self.colors['bg'])
        top.pack(fill='x', pady=5)
        tk.Label(top, text="اختر عداد:", font=('Segoe UI', 11), bg=self.colors['bg']).pack(side='left', padx=5)
        self.acc_meter_var = tk.StringVar()
        self.acc_meter_combo = ttk.Combobox(top, textvariable=self.acc_meter_var, state='readonly', width=25, font=('Segoe UI', 10))
        self.acc_meter_combo.pack(side='left', padx=5)
        self._add_styled_button(top, "عرض الكشف", self.show_energy_account, self.colors['primary']).pack(side='left', padx=10)

        # معلومات الحساب
        info_frame = tk.LabelFrame(frame, text="معلومات الحساب", font=('Segoe UI', 11, 'bold'), bg=self.colors['bg'], fg=self.colors['dark'])
        info_frame.pack(fill='x', pady=10)
        self.acc_info_label = tk.Label(info_frame, text="", font=('Segoe UI', 10), bg=self.colors['bg'], justify='right')
        self.acc_info_label.pack(anchor='e', padx=10, pady=5)

        # جدول الحركات
        tbl_frame = tk.LabelFrame(frame, text="سجل الحركات", font=('Segoe UI', 11, 'bold'), bg=self.colors['bg'], fg=self.colors['dark'])
        tbl_frame.pack(fill='both', expand=True, pady=10)

        cols = ('id', 'date', 'type', 'amount', 'balance_before', 'balance_after', 'notes')
        self.acc_tree = ttk.Treeview(tbl_frame, columns=cols, show='headings', height=12)
        self.acc_tree.heading('id', text='ID')
        self.acc_tree.heading('date', text='التاريخ')
        self.acc_tree.heading('type', text='النوع')
        self.acc_tree.heading('amount', text='المبلغ')
        self.acc_tree.heading('balance_before', text='قبل')
        self.acc_tree.heading('balance_after', text='بعد')
        self.acc_tree.heading('notes', text='ملاحظات')
        self.acc_tree.column('id', width=50, anchor='center')
        self.acc_tree.column('date', width=130, anchor='center')
        self.acc_tree.column('type', width=80, anchor='center')
        self.acc_tree.column('amount', width=100, anchor='center')
        self.acc_tree.column('balance_before', width=100, anchor='center')
        self.acc_tree.column('balance_after', width=100, anchor='center')
        self.acc_tree.column('notes', width=200)
        self.acc_tree.pack(side='left', fill='both', expand=True)
        scroll = ttk.Scrollbar(tbl_frame, orient='vertical', command=self.acc_tree.yview)
        self.acc_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self._add_zebra_striping(self.acc_tree)

        # تحميل قائمة العدادات
        self.refresh_account_meter_combo()

    def refresh_account_meter_combo(self):
        meters = FuelManagement.get_energy_meters(active_only=False)
        self.acc_meter_combo['values'] = [f"{m['id']} - {m['name']}" for m in meters]
        if meters:
            self.acc_meter_var.set(f"{meters[0]['id']} - {meters[0]['name']}")

    def show_energy_account(self):
        sel = self.acc_meter_var.get()
        if not sel:
            print("⚠️ لم يتم اختيار عداد")
            return
        meter_id = int(sel.split(' - ')[0])
        print(f"✅ تم اختيار عداد ID: {meter_id}")
        
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM energy_meters WHERE id = %s", (meter_id,))
            meter = cursor.fetchone()
            if not meter:
                print("❌ العداد غير موجود في قاعدة البيانات")
                messagebox.showerror("خطأ", "العداد غير موجود")
                return
            self.acc_info_label.config(
                text=f"العداد: {meter['name']} | سعر الكيلو: {meter['conversion_rate']} ل.س | الرصيد الحالي: {meter['current_balance']:,.0f} ل.س"
            )

        # جلب الحركات
        trans = FuelManagement.get_energy_account_statement(meter_id)
        print(f"📊 عدد الحركات المسترجعة: {len(trans)}")
        if trans:
            print("أول حركة:", trans[0])
        else:
            print("لا توجد حركات مالية لهذا العداد")

        # تنظيف الجدول
        for row in self.acc_tree.get_children():
            self.acc_tree.delete(row)
        
        # إدراج الحركات
        for t in trans:
            ttype = {'production': 'إنتاج', 'payment': 'سحب', 'adjustment': 'تسوية'}.get(t['transaction_type'], t['transaction_type'])
            self.acc_tree.insert('', 'end', values=(
                t['id'],
                t['transaction_date'].strftime('%Y-%m-%d %H:%M') if t['transaction_date'] else '',
                ttype,
                f"{t['amount']:,.0f}",
                f"{t['balance_before']:,.0f}",
                f"{t['balance_after']:,.0f}",
                t['notes'] or ''
            ))
        if not trans:
            messagebox.showinfo("تنبيه", "لا توجد حركات مالية مسجلة لهذا العداد بعد.\nقم بإضافة قراءات طاقة أولاً.")