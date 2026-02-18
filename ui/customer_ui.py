# ui/customer_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
from typing import List, Dict, Optional
from auth.permissions import has_permission, require_permission
import threading

logger = logging.getLogger(__name__)

class CustomerUI(tk.Frame):
    """واجهة إدارة الزبائن الكاملة مع دعم العدادات الهرمية - نسخة محسنة بصرياً ووظيفياً (مستقرة)"""

    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.user_data = user_data
        self.customer_manager = None
        self.sectors = []

        # إعداد الأنماط لتكبير الصفوف والعناوين
        self.setup_styles()

        self.load_customer_manager()
        self.load_sectors()

        self.create_widgets()
        self.load_customers()

    def setup_styles(self):
        """إعداد التنسيقات العامة للواجهة - تكبير الخطوط وارتفاع الصفوف"""
        style = ttk.Style()
        style.configure("Treeview.Heading", font=('Arial', 12, 'bold'))
        style.configure("Treeview", font=('Arial', 11), rowheight=35)

    def load_customer_manager(self):
        try:
            from modules.customers import CustomerManager
            self.customer_manager = CustomerManager()
        except ImportError as e:
            logger.error(f"خطأ في تحميل مدير الزبائن: {e}")
            messagebox.showerror("خطأ", "لا يمكن تحميل وحدة الزبائن")

    def load_sectors(self):
        try:
            from database.connection import db
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id, name FROM sectors WHERE is_active = TRUE ORDER BY name")
                self.sectors = cursor.fetchall()
        except Exception as e:
            logger.error(f"خطأ في تحميل القطاعات: {e}")
            self.sectors = []

    def create_widgets(self):
        self.create_toolbar()
        self.create_search_bar()
        self.create_customer_tree()
        self.create_statusbar()

    def create_toolbar(self):
        """شريط أدوات علوي بصفين من الأزرار متساوية الحجم والتباعد"""
        toolbar = tk.Frame(self, bg='#1a252f', height=140)
        toolbar.pack(fill='x', padx=0, pady=0)
        toolbar.pack_propagate(False)

        # عنوان الشريط (يُبقي على اليمين)
        title_label = tk.Label(toolbar,
                            text="📋 إدارة حسابات الزبائن",
                            font=('Arial', 18, 'bold'),
                            bg='#1a252f', fg='#ecf0f1')
        title_label.pack(side='right', padx=25, pady=(15, 5))

        # حاوية الأزرار (تملأ المساحة المتبقية)
        buttons_container = tk.Frame(toolbar, bg='#1a252f')
        buttons_container.pack(side='left', fill='both', expand=True, padx=10, pady=(5, 10))

        # قائمة الأزرار بنفس ترتيبك الأصلي
        all_buttons = [
            ("➕ إضافة", self.add_customer, "#27ae60", 'customers.add'),
            ("✏️ تعديل", self.edit_customer, "#3498db", 'customers.edit'),
            ("🗑️ حذف", self.delete_customer, "#e74c3c", 'customers.delete'),
            ("🔄 تحديث", self.refresh_customers, "#95a5a6", 'customers.view'),
            ("📋 تفاصيل", self.show_customer_details, "#9b59b6", 'customers.view_details'),
            ("📜 سجل", self.show_customer_history, "#8e44ad", 'customers.view_history'),
            ("💰 تأشيرات", self.import_visas, "#f39c12", 'customers.import_visas'),
            ("🗑️🔥 إعادة", self.delete_and_reimport, "#e74c3c", 'customers.reimport'),
            ("🗑️ قطاع", self.delete_sector_customers, "#c0392b", 'customers.manage_sectors'),
            ("📊 تصنيفات", self.manage_financial_categories, "#9b59b6", 'customers.manage_financial_categories'),
            ("👥 إدارة الأبناء", self.manage_children, "#f39c12", 'customers.manage_children'),
            ("📊 لنا/علينا", self.show_balance_stats, "#34495e", 'customers.view')
        ]

        # تقسيم الأزرار إلى صفين
        row1_buttons = all_buttons[:6]
        row2_buttons = all_buttons[6:]

        # عرض ثابت لجميع الأزرار (يمكنك تعديل الرقم حسب رغبتك)
        BTN_WIDTH = 14  # بوحدة عدد الأحرف

        def create_row(parent, buttons):
            """إنشاء صف من الأزرار متساوية العرض والتباعد"""
            row_frame = tk.Frame(parent, bg='#1a252f')
            row_frame.pack(fill='x', pady=5)

            # استخدام grid لجعل الأعمدة متساوية العرض
            for col, (text, command, color, permission) in enumerate(buttons):
                # جعل جميع الأعمدة تأخذ وزناً متساوياً
                row_frame.columnconfigure(col, weight=1, uniform='btn_group')

                if has_permission(permission):
                    btn = tk.Button(row_frame, text=text, command=command,
                                    bg=color, fg='white',
                                    font=('Arial', 11, 'bold'),
                                    width=BTN_WIDTH,
                                    cursor='hand2',
                                    relief='flat', activebackground='#ecf0f1')
                else:
                    btn = tk.Button(row_frame, text=text,
                                    state='disabled',
                                    bg='#95a5a6', fg='white',
                                    font=('Arial', 11, 'bold'),
                                    width=BTN_WIDTH,
                                    relief='flat')

                # وضع الزر في العمود مع توسيط أفقي وتباعد بسيط
                btn.grid(row=0, column=col, padx=4, pady=2, sticky='ew')

        # إنشاء الصفين
        create_row(buttons_container, row1_buttons)
        create_row(buttons_container, row2_buttons)
        
                
    def create_search_bar(self):
        """شريط البحث والتصفية (محسّن)"""
        search_frame = tk.Frame(self, bg='#f8f9fa', pady=15, padx=15, relief='flat')
        search_frame.pack(fill='x')

        search_box = tk.LabelFrame(search_frame, text=" 🔍 أدوات التصفية السريعة ",
                                   font=('Arial', 10, 'bold'), fg='#2c3e50', bg='#f8f9fa')
        search_box.pack(fill='x', padx=5)

        def add_filter(parent, label, var_name, values=None, is_combo=False):
            container = tk.Frame(parent, bg='#f8f9fa')
            container.pack(side='right', padx=15, pady=10)

            tk.Label(container, text=label, font=('Arial', 11, 'bold'), bg='#f8f9fa').pack(side='top', anchor='e')

            if is_combo:
                combo = ttk.Combobox(container, textvariable=var_name, values=values,
                                     state='readonly', width=18, font=('Arial', 11))
                combo.pack(side='bottom', pady=5)
                combo.bind('<<ComboboxSelected>>', self.on_filter_changed)
                return combo
            else:
                entry = ttk.Entry(container, textvariable=var_name, width=25, font=('Arial', 11))
                entry.pack(side='bottom', pady=5)
                entry.bind('<KeyRelease>', self.on_search_changed)
                return entry

        self.search_var = tk.StringVar()
        add_filter(search_box, "البحث بالاسم أو الرقم:", self.search_var)

        self.sector_var = tk.StringVar(value='الكل')
        add_filter(search_box, "القطاع:", self.sector_var, ['الكل'] + [s['name'] for s in self.sectors], True)

        self.meter_type_var = tk.StringVar(value='الكل')
        add_filter(search_box, "نوع العداد:", self.meter_type_var, ['الكل', 'مولدة', 'علبة توزيع', 'رئيسية', 'زبون'], True)

        self.balance_var = tk.StringVar(value='الكل')
        add_filter(search_box, "حالة الرصيد:", self.balance_var, ['الكل', 'سالب فقط', 'موجب فقط', 'صفر فقط'], True)

    def create_customer_tree(self):
        """شجرة عرض الزبائن مع تحسين الرؤية والحفاظ على جميع الأعمدة"""
        tree_frame = tk.Frame(self, bg='white')
        tree_frame.pack(fill='both', expand=True, padx=15, pady=10)

        v_scroll = ttk.Scrollbar(tree_frame, orient='vertical')
        v_scroll.pack(side='right', fill='y')
        h_scroll = ttk.Scrollbar(tree_frame, orient='horizontal')
        h_scroll.pack(side='bottom', fill='x')

        # الأعمدة (باستثناء الاسم الذي سيكون في العمود #0)
        columns = ('id', 'sector', 'meter_type', 'parent', 'box', 'serial', 'balance', 'phone', 'visa', 'status')
        self.tree = ttk.Treeview(tree_frame, columns=columns,
                                 yscrollcommand=v_scroll.set,
                                 xscrollcommand=h_scroll.set,
                                 selectmode='browse',
                                 show='tree headings',
                                 height=20)

        v_scroll.config(command=self.tree.yview)
        h_scroll.config(command=self.tree.xview)

        # رأس العمود الأول (الشجرة) - لعرض الاسم
        self.tree.heading('#0', text='اسم الزبون / العداد', anchor='center')
        self.tree.column('#0', width=250)

        # تعريف بقية الأعمدة
        columns_config = [
            ('id', 'ID', 50, 'center'),
            ('sector', 'القطاع', 120, 'center'),
            ('meter_type', 'النوع', 100, 'center'),
            ('parent', 'العلبة الأم', 120, 'center'),
            ('box', 'رقم العلبة', 90, 'center'),
            ('serial', 'المسلسل', 100, 'center'),
            ('balance', 'الرصيد الحالي (ك.و)', 150, 'center'),
            ('phone', 'الهاتف', 110, 'center'),
            ('visa', 'رصيد التأشيرة', 120, 'center'),
            ('status', 'الحالة', 80, 'center')
        ]

        for col_id, heading, width, anchor in columns_config:
            self.tree.heading(col_id, text=heading, anchor='center')
            self.tree.column(col_id, width=width, anchor=anchor)

        self.tree.pack(fill='both', expand=True)

        # تنسيقات الألوان
        self.tree.tag_configure('negative', foreground='#c0392b', font=('Arial', 11, 'bold'))
        self.tree.tag_configure('positive', foreground='#27ae60', font=('Arial', 11, 'bold'))
        self.tree.tag_configure('zero', foreground='#7f8c8d')
        self.tree.tag_configure('inactive', background='#f2f2f2', foreground='#bdc3c7')

        self.tree.bind('<Double-Button-1>', self.on_double_click)
        self.tree.bind('<<TreeviewSelect>>', self.on_selection_changed)

    def create_statusbar(self):
        self.statusbar = tk.Frame(self, bg='#2c3e50', height=40)
        self.statusbar.pack(fill='x')
        self.statusbar.pack_propagate(False)

        self.status_label = tk.Label(self.statusbar,
                                     text="جاهز | عدد الزبائن: 0",
                                     bg='#2c3e50', fg='white',
                                     font=('Arial', 11))
        self.status_label.pack(side='right', padx=20)

        self.stats_label = tk.Label(self.statusbar,
                                    text="",
                                    bg='#2c3e50', fg='#f1c40f',
                                    font=('Arial', 11, 'bold'))
        self.stats_label.pack(side='left', padx=20)

    def load_customers(self, search_term="", sector_id=None, meter_type_filter="الكل", balance_filter="الكل"):
        """تحميل قائمة الزبائن بالترتيب الهرمي مع دعم البحث والفلاتر (من الكود الأصلي مع تحسينات)"""
        if not self.customer_manager:
            self.show_error_message("مدير الزبائن غير متاح")
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            # تحديد sector_id من الاسم إذا لزم
            if sector_id is None:
                sector_name = self.sector_var.get()
                if sector_name and sector_name != 'الكل':
                    for s in self.sectors:
                        if s['name'] == sector_name:
                            sector_id = s['id']
                            break

            # جلب جميع العقد بالترتيب الهرمي
            nodes = self.customer_manager.get_customer_hierarchy(sector_id=sector_id)

            # تطبيق البحث إذا وجد (منطق الكود الأصلي)
            if search_term:
                search_term_lower = search_term.lower()
                matching_ids = set()
                for node in nodes:
                    if (search_term_lower in node['name'].lower() or
                        search_term_lower in node.get('box_number', '').lower() or
                        search_term_lower in node.get('serial_number', '').lower() or
                        search_term_lower in node.get('phone_number', '').lower()):
                        matching_ids.add(node['id'])

                # إضافة الآباء للحفاظ على الهيكل
                visible_ids = set(matching_ids)
                for node in nodes:
                    if node['id'] in matching_ids:
                        parent_id = node.get('parent_meter_id')
                        while parent_id:
                            visible_ids.add(parent_id)
                            parent_node = next((n for n in nodes if n['id'] == parent_id), None)
                            if parent_node:
                                parent_id = parent_node.get('parent_meter_id')
                            else:
                                break
                nodes = [node for node in nodes if node['id'] in visible_ids]

            # تطبيق فلاتر نوع العداد والرصيد
            filtered_nodes = []
            for node in nodes:
                balance = node.get('current_balance', 0)

                # فلتر الرصيد
                if balance_filter == 'سالب فقط' and balance >= 0:
                    continue
                if balance_filter == 'موجب فقط' and balance <= 0:
                    continue
                if balance_filter == 'صفر فقط' and balance != 0:
                    continue

                # فلتر نوع العداد
                if meter_type_filter != 'الكل' and node['meter_type'] != meter_type_filter:
                    continue

                filtered_nodes.append(node)

            # بناء الشجرة بشكل هرمي
            children_by_parent = {}
            for node in filtered_nodes:
                parent_id = node.get('parent_meter_id')
                children_by_parent.setdefault(parent_id, []).append(node)

            def insert_node(parent_id, parent_iid=''):
                for node in children_by_parent.get(parent_id, []):
                    balance = node.get('current_balance', 0)
                    tags = []
                    if balance < 0:
                        tags.append('negative')
                    elif balance > 0:
                        tags.append('positive')
                    else:
                        tags.append('zero')
                    if not node.get('is_active', True):
                        tags.append('inactive')

                    # الحصول على اسم الأب لعرضه في عمود parent
                    parent_name = ''
                    if node.get('parent_meter_id'):
                        parent_node = next((n for n in filtered_nodes if n['id'] == node['parent_meter_id']), None)
                        if parent_node:
                            parent_name = parent_node['name']

                    iid = self.tree.insert(
                        parent_iid, 'end',
                        text=f" {node['name']}",
                        values=(
                            node['id'],
                            node.get('sector_name', ''),
                            node['meter_type'],
                            parent_name,
                            node.get('box_number', '-'),
                            node.get('serial_number', '-'),
                            f"{balance:,.1f}",
                            node.get('phone_number', ''),
                            f"{node.get('visa_balance', 0):,.0f}",
                            "نشط" if node.get('is_active', True) else "غير نشط"
                        ),
                        tags=tuple(tags)
                    )
                    insert_node(node['id'], iid)

            insert_node(None)

            # تحديث الإحصائيات
            customer_count = len([n for n in filtered_nodes if n['meter_type'] == 'زبون'])
            self.status_label.config(text=f"عدد الزبائن في العرض: {customer_count}")
            self.stats_label.config(text=f"إجمالي العقد: {len(filtered_nodes)}" + (" (نتائج بحث)" if search_term else ""))

        except Exception as e:
            logger.error(f"خطأ في تحميل الزبائن: {e}")
            self.show_error_message(f"خطأ في تحميل البيانات: {str(e)}")

    def on_search_changed(self, event=None):
        search_term = self.search_var.get().strip()
        sector_name = self.sector_var.get()
        meter_type_filter = self.meter_type_var.get()
        balance_filter = self.balance_var.get()

        sector_id = None
        if sector_name and sector_name != 'الكل':
            for sector in self.sectors:
                if sector['name'] == sector_name:
                    sector_id = sector['id']
                    break

        self.load_customers(search_term, sector_id, meter_type_filter, balance_filter)

    def on_filter_changed(self, event=None):
        self.on_search_changed()

    def on_double_click(self, event):
        self.show_customer_details()

    def on_selection_changed(self, event):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            customer_name = item['text']
            self.status_label.config(text=f"المحدد: {customer_name}")

    def get_selected_customer_id(self):
        selection = self.tree.selection()
        if not selection:
            return None
        item = self.tree.item(selection[0])
        return item['values'][0]

    # باقي الدوال (add, edit, delete, ...) كما هي من الكود الأصلي
    def add_customer(self):
        try:
            require_permission('customers.add')
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return

        from ui.customer_form import CustomerForm
        form = CustomerForm(self, "إضافة زبون جديد", self.sectors, user_id=self.user_data.get('id'))

        if form.result:
            try:
                result = self.customer_manager.add_customer(form.result)
                if result.get('success'):
                    messagebox.showinfo("نجاح", result['message'])
                    self.refresh_customers()
                else:
                    messagebox.showerror("خطأ", result.get('error', 'فشل إضافة الزبون'))
            except Exception as e:
                logger.error(f"خطأ في إضافة الزبون: {e}")
                messagebox.showerror("خطأ", f"فشل إضافة الزبون: {str(e)}")

    def edit_customer(self):
        try:
            require_permission('customers.edit')
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return

        customer_id = self.get_selected_customer_id()
        if not customer_id:
            messagebox.showwarning("تحذير", "يرجى تحديد زبون أولاً")
            return

        try:
            customer = self.customer_manager.get_customer(customer_id)
            if not customer:
                messagebox.showerror("خطأ", "الزبون غير موجود")
                return

            from ui.customer_form import CustomerForm
            form = CustomerForm(self, "تعديل بيانات الزبون", self.sectors, customer, user_id=self.user_data.get('id'))

            if form.result:
                result = self.customer_manager.update_customer(customer_id, form.result)
                if result.get('success'):
                    messagebox.showinfo("نجاح", result['message'])
                    self.refresh_customers()
                else:
                    messagebox.showerror("خطأ", result.get('error', 'فشل تحديث الزبون'))

        except Exception as e:
            logger.error(f"خطأ في تعديل الزبون: {e}")
            messagebox.showerror("خطأ", f"فشل تعديل الزبون: {str(e)}")

    def delete_customer(self):
        try:
            require_permission('customers.delete')
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return

        customer_id = self.get_selected_customer_id()
        if not customer_id:
            messagebox.showwarning("تحذير", "يرجى تحديد زبون أولاً")
            return

        confirm = messagebox.askyesno(
            "تأكيد الحذف",
            "هل أنت متأكد من حذف هذا الزبون؟\n\n"
            "سيتم إلغاء تفعيل الزبون (حذف ناعم)."
        )

        if not confirm:
            return

        try:
            result = self.customer_manager.delete_customer(customer_id)
            if result.get('success'):
                messagebox.showinfo("نجاح", result['message'])
                self.refresh_customers()
            else:
                messagebox.showerror("خطأ", result.get('error', 'فشل حذف الزبون'))

        except Exception as e:
            logger.error(f"خطأ في حذف الزبون: {e}")
            messagebox.showerror("خطأ", f"فشل حذف الزبون: {str(e)}")

    def show_customer_details(self):
        customer_id = self.get_selected_customer_id()
        if not customer_id:
            messagebox.showwarning("تحذير", "يرجى تحديد زبون أولاً")
            return

        try:
            customer = self.customer_manager.get_customer(customer_id)
            if not customer:
                messagebox.showerror("خطأ", "الزبون غير موجود")
                return

            from ui.customer_details import CustomerDetails
            CustomerDetails(self, customer)

        except Exception as e:
            logger.error(f"خطأ في عرض التفاصيل: {e}")
            messagebox.showerror("خطأ", f"فشل عرض التفاصيل: {str(e)}")

    def refresh_customers(self):
        self.load_customers()
        self.status_label.config(text="✅ تم تحديث البيانات بنجاح")

    def show_error_message(self, message):
        messagebox.showerror("خطأ", message)

    def show_customer_history(self):
        customer_id = self.get_selected_customer_id()
        if not customer_id:
            messagebox.showwarning("تحذير", "يرجى تحديد زبون أولاً")
            return

        try:
            customer = self.customer_manager.get_customer(customer_id)
            if not customer:
                messagebox.showerror("خطأ", "الزبون غير موجود")
                return

            from ui.customer_history_ui import CustomerHistoryUI
            CustomerHistoryUI(self, customer, self.user_data)

        except Exception as e:
            logger.error(f"خطأ في عرض السجل التاريخي: {e}")
            messagebox.showerror("خطأ", f"فشل عرض السجل: {str(e)}")

    def import_visas(self):
        try:
            require_permission('customers.import_visas')
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return

        try:
            from modules.visa_importer import VisaEditor
            root_window = self.winfo_toplevel()
            editor = VisaEditor(root_window, user_id=self.user_data.get('id', 1))
            logger.info(f"تم فتح محرر التأشيرات للمستخدم {self.user_data.get('id', 1)}")

        except ImportError as e:
            logger.error(f"خطأ في تحميل محرر التأشيرات: {e}")
            messagebox.showerror("خطأ",
                f"❌ لا يمكن تحميل محرر التأشيرات\n\n"
                f"السبب: {str(e)}\n\n"
                f"تأكد من وجود ملف: modules/visa_editor.py")
        except Exception as e:
            logger.error(f"خطأ في فتح محرر التأشيرات: {e}")
            messagebox.showerror("خطأ", f"❌ فشل فتح محرر التأشيرات: {str(e)}")

    def delete_and_reimport(self):
        try:
            require_permission('customers.reimport')
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return

        warning_msg = """
        ⚠️  تحذير شديد - هذا الإجراء خطير!

        سيؤدي هذا إلى:
        1. حذف جميع الزبائن من قاعدة البيانات
        2. حذف جميع الفواتير المرتبطة بهم
        3. فقدان جميع البيانات التاريخية

        هل أنت متأكد تماماً من رغبتك في المتابعة؟
        """

        confirm = messagebox.askyesno("تحذير شديد", warning_msg)
        if not confirm:
            return

        double_check = messagebox.askyesno("تأكيد نهائي",
                                        "⚠️ تأكيد نهائي: هل أنت متأكد 100%؟\n"
                                        "هذا الإجراء لا يمكن التراجع عنه!")
        if not double_check:
            return

        try:
            from tkinter import filedialog
            excel_folder = filedialog.askdirectory(
                title="اختر مجلد ملفات Excel"
            )

            if not excel_folder:
                return

            import os
            excel_files = [f for f in os.listdir(excel_folder) if f.endswith('.xlsx')]
            if not excel_files:
                messagebox.showerror("خطأ", "لا توجد ملفات Excel في المجلد المحدد")
                return

            files_msg = f"سيتم استيراد {len(excel_files)} ملف:\n\n"
            for file in excel_files:
                files_msg += f"• {file}\n"

            if not messagebox.askyesno("تأكيد الملفات", files_msg + "\nهل تريد المتابعة؟"):
                return

            delete_result = self.customer_manager.delete_all_customers()

            if not delete_result.get('success'):
                messagebox.showerror("خطأ", f"فشل حذف الزبائن: {delete_result.get('error')}")
                return

            from database.migrations import ExcelMigration

            progress_window = tk.Toplevel(self)
            progress_window.title("جاري الاستيراد...")
            progress_window.geometry("400x150")
            progress_window.resizable(False, False)

            progress_label = tk.Label(progress_window,
                                    text="جاري استيراد البيانات من Excel...",
                                    font=('Arial', 12))
            progress_label.pack(pady=20)

            progress_bar = ttk.Progressbar(progress_window,
                                        mode='indeterminate',
                                        length=300)
            progress_bar.pack(pady=10)
            progress_bar.start()

            status_label = tk.Label(progress_window,
                                text="يرجى الانتظار...",
                                font=('Arial', 10))
            status_label.pack()

            progress_window.update()

            migrator = ExcelMigration(excel_folder)
            success = migrator.migrate_all_data()

            progress_bar.stop()
            progress_window.destroy()

            if success:
                self.refresh_customers()

                report = f"""
                ✅ تمت العملية بنجاح!

                نتائج العملية:
                • تم حذف {delete_result.get('deleted_count', 0)} زبون
                • تم استيراد {len(excel_files)} ملف Excel

                يمكنك الآن:
                1. مراجعة البيانات المستوردة
                2. التحقق من دقة المعلومات
                3. بدء استخدام النظام
                """

                messagebox.showinfo("تمت العملية", report)
                logger.info(f"تم حذف وإعادة استيراد {delete_result.get('deleted_count', 0)} زبون")

            else:
                messagebox.showerror("خطأ", "فشل استيراد البيانات من Excel")

        except Exception as e:
            logger.error(f"خطأ في حذف وإعادة الاستيراد: {e}")
            messagebox.showerror("خطأ", f"فشل العملية: {str(e)}")

    def manage_financial_categories(self):
        try:
            require_permission('customers.manage_financial_categories')
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return

        customer_id = self.get_selected_customer_id()
        if not customer_id:
            messagebox.showwarning("تحذير", "يرجى تحديد زبون أولاً")
            return

        try:
            customer = self.customer_manager.get_customer(customer_id)
            if not customer:
                messagebox.showerror("خطأ", "الزبون غير موجود")
                return

            from ui.financial_category_ui import FinancialCategoryUI
            # فقط إنشاء الكائن، وهو سينشئ نافذة Toplevel خاصة به
            FinancialCategoryUI(self, customer, self.user_data)

        except Exception as e:
            logger.error(f"خطأ في فتح مدير التصنيف المالي: {e}")
            messagebox.showerror("خطأ", f"فشل فتح مدير التصنيف: {str(e)}")

            
    def delete_sector_customers(self):
        try:
            require_permission('customers.manage_sectors')
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return

        sector_dialog = tk.Toplevel(self)
        sector_dialog.title("حذف زبائن قطاع")
        sector_dialog.geometry("400x200")
        sector_dialog.resizable(False, False)

        tk.Label(sector_dialog,
                text="اختر القطاع لحذف زبائنه:",
                font=('Arial', 12, 'bold')).pack(pady=10)

        sector_var = tk.StringVar()
        sector_combo = ttk.Combobox(sector_dialog,
                                textvariable=sector_var,
                                values=[s['name'] for s in self.sectors],
                                state='readonly',
                                font=('Arial', 11),
                                width=30)
        sector_combo.pack(pady=10)

        def confirm_delete():
            sector_name = sector_var.get()
            if not sector_name:
                messagebox.showwarning("تحذير", "يرجى اختيار قطاع")
                return

            warning = f"""
            ⚠️ تحذير!

            سيتم حذف جميع زبائن قطاع: {sector_name}
            هل أنت متأكد؟
            """

            if messagebox.askyesno("تحذير", warning):
                sector_id = None
                for sector in self.sectors:
                    if sector['name'] == sector_name:
                        sector_id = sector['id']
                        break

                if sector_id:
                    result = self.customer_manager.delete_customers_by_sector(sector_id)
                    if result.get('success'):
                        messagebox.showinfo("نجاح", result['message'])
                        self.refresh_customers()
                        sector_dialog.destroy()
                    else:
                        messagebox.showerror("خطأ", result.get('error', 'فشل الحذف'))

        btn_frame = tk.Frame(sector_dialog)
        btn_frame.pack(pady=20)

        tk.Button(btn_frame, text="حذف", command=confirm_delete,
                bg='#e74c3c', fg='white',
                font=('Arial', 11)).pack(side='left', padx=10)

        tk.Button(btn_frame, text="إلغاء",
                command=sector_dialog.destroy,
                bg='#95a5a6', fg='white',
                font=('Arial', 11)).pack(side='left', padx=10)

    def show_balance_stats(self):
        stats = self.customer_manager.get_customer_balance_by_sector()

        window = tk.Toplevel(self)
        window.title("إحصائيات لنا وعلينا لكل قطاع")
        window.geometry("700x500")

        title_frame = tk.Frame(window, bg='#2c3e50', height=60)
        title_frame.pack(fill='x', pady=(0, 10))
        title_frame.pack_propagate(False)

        tk.Label(title_frame,
                text="💰 إحصائيات لنا وعلينا لكل قطاع",
                font=('Arial', 16, 'bold'),
                bg='#2c3e50', fg='white').pack(pady=15)

        tree_frame = tk.Frame(window)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=5)

        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical')
        scrollbar.pack(side='right', fill='y')

        columns = ("sector", "lana_count", "lana_amount", "alayna_count", "alayna_amount", "net_balance")
        tree = ttk.Treeview(tree_frame, columns=columns, yscrollcommand=scrollbar.set, show="headings")
        scrollbar.config(command=tree.yview)

        tree.heading("sector", text="القطاع")
        tree.heading("lana_count", text="عدد (لنا)")
        tree.heading("lana_amount", text="مجموع لنا (ك.و)")
        tree.heading("alayna_count", text="عدد (علينا)")
        tree.heading("alayna_amount", text="مجموع علينا (ك.و)")
        tree.heading("net_balance", text="الرصيد الصافي")

        tree.column("sector", width=150)
        tree.column("lana_count", width=80, anchor="center")
        tree.column("lana_amount", width=120, anchor="center")
        tree.column("alayna_count", width=80, anchor="center")
        tree.column("alayna_amount", width=120, anchor="center")
        tree.column("net_balance", width=120, anchor="center")

        tree.pack(fill='both', expand=True)

        for row in stats['sectors']:
            lana_amount = row.get('lana_amount', 0)
            alayna_amount = row.get('alayna_amount', 0)
            net_balance = alayna_amount - lana_amount

            tags = ()
            if net_balance > 0:
                tags = ('positive',)
            elif net_balance < 0:
                tags = ('negative',)

            tree.insert('', 'end', values=(
                row['sector_name'],
                row.get('lana_count', 0),
                f"{lana_amount:,.0f}",
                row.get('alayna_count', 0),
                f"{alayna_amount:,.0f}",
                f"{net_balance:,.0f}"
            ), tags=tags)

        tree.tag_configure('positive', foreground='#27ae60')
        tree.tag_configure('negative', foreground='#e74c3c')

        total_frame = tk.Frame(window, bg='#f8f9fa', relief='groove', borderwidth=2)
        total_frame.pack(fill='x', padx=10, pady=10)

        tk.Label(total_frame,
                text=f"🧮 الإجماليات:",
                font=('Arial', 12, 'bold'),
                bg='#f8f9fa').pack(side='left', padx=10, pady=5)

        totals_text = f"""
        • عدد الزبائن (لنا): {stats['total_lana_count']} زبون
        • إجمالي المبالغ (لنا): {stats['total_lana_amount']:,.0f} ك.و
        • عدد الزبائن (علينا): {stats['total_alayna_count']} زبون
        • إجمالي المبالغ (علينا): {stats['total_alayna_amount']:,.0f} ك.و
        • الرصيد الصافي العام: {(stats['total_alayna_amount'] - stats['total_lana_amount']):,.0f} ك.و
        """

        tk.Label(total_frame,
                text=totals_text,
                font=('Arial', 10),
                bg='#f8f9fa',
                justify='left').pack(side='left', padx=10, pady=5)

        def export_stats():
            try:
                from datetime import datetime
                import csv

                filename = f"احصائيات_لنا_علينا_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

                with open(filename, 'w', newline='', encoding='utf-8-sig') as file:
                    writer = csv.writer(file)
                    writer.writerow(['القطاع', 'عدد (لنا)', 'مجموع لنا (ك.و)', 'عدد (علينا)', 'مجموع علينا (ك.و)', 'الرصيد الصافي'])

                    for row in stats['sectors']:
                        writer.writerow([
                            row['sector_name'],
                            row.get('lana_count', 0),
                            row.get('lana_amount', 0),
                            row.get('alayna_count', 0),
                            row.get('alayna_amount', 0),
                            row.get('alayna_amount', 0) - row.get('lana_amount', 0)
                        ])

                    writer.writerow([])
                    writer.writerow(['الإجمالي العام',
                                stats['total_lana_count'],
                                stats['total_lana_amount'],
                                stats['total_alayna_count'],
                                stats['total_alayna_amount'],
                                stats['total_alayna_amount'] - stats['total_lana_amount']])

                messagebox.showinfo("نجاح", f"تم تصدير البيانات إلى: {filename}")

            except Exception as e:
                logger.error(f"خطأ في تصدير الإحصائيات: {e}")
                messagebox.showerror("خطأ", f"فشل التصدير: {str(e)}")

        btn_frame = tk.Frame(window)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="📥 تصدير إلى CSV",
                command=export_stats,
                bg='#3498db', fg='white',
                font=('Arial', 10)).pack(side='left', padx=5)

        tk.Button(btn_frame, text="إغلاق",
                command=window.destroy,
                bg='#95a5a6', fg='white',
                font=('Arial', 10)).pack(side='left', padx=5)

    def manage_children(self):
        try:
            require_permission('customers.manage_children')
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return

        customer_id = self.get_selected_customer_id()
        if not customer_id:
            messagebox.showwarning("تحذير", "يرجى تحديد والد (مولدة/علبة توزيع/رئيسية) أولاً")
            return

        try:
            parent = self.customer_manager.get_customer(customer_id)
            if not parent:
                messagebox.showerror("خطأ", "الوالد غير موجود")
                return

            if parent['meter_type'] not in ['مولدة', 'علبة توزيع', 'رئيسية']:
                messagebox.showwarning("تحذير", "هذا العنصر ليس من الأنواع التي يمكن أن تكون أباً (مولدة/علبة توزيع/رئيسية)")
                return

            from ui.manage_children import ManageChildrenDialog
            ManageChildrenDialog(self, self.customer_manager, parent, self.user_data.get('id', 1))

        except ImportError as e:
            logger.error(f"خطأ في تحميل وحدة إدارة الأبناء: {e}")
            messagebox.showerror("خطأ", "لا يمكن تحميل وحدة إدارة الأبناء")
        except Exception as e:
            logger.error(f"خطأ في فتح إدارة الأبناء: {e}")
            messagebox.showerror("خطأ", f"فشل فتح النافذة: {str(e)}")