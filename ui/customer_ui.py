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
    """واجهة إدارة الزبائن الكاملة مع دعم العدادات الهرمية"""
    
    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.user_data = user_data
        self.customer_manager = None
        self.sectors = []
        
        self.load_customer_manager()
        self.load_sectors()
        
        self.create_widgets()
        self.load_customers()
    
    def load_customer_manager(self):
        """تحميل مدير الزبائن"""
        try:
            from modules.customers import CustomerManager
            self.customer_manager = CustomerManager()
        except ImportError as e:
            logger.error(f"خطأ في تحميل مدير الزبائن: {e}")
            messagebox.showerror("خطأ", "لا يمكن تحميل وحدة الزبائن")
    
    def load_sectors(self):
        """تحميل قائمة القطاعات"""
        try:
            from database.connection import db
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id, name FROM sectors WHERE is_active = TRUE ORDER BY name")
                self.sectors = cursor.fetchall()
        except Exception as e:
            logger.error(f"خطأ في تحميل القطاعات: {e}")
            self.sectors = []
    
    def create_widgets(self):
        """إنشاء عناصر الواجهة"""
        # شريط الأدوات العلوي
        self.create_toolbar()
        
        # شريط البحث والتصفية
        self.create_search_bar()
        
        # شجرة عرض الزبائن
        self.create_customer_tree()
        
        # شريط الحالة السفلي
        self.create_statusbar()
    
    def create_toolbar(self):
        """إنشاء شريط الأدوات العلوي مع إمكانية التمرير"""
        toolbar = tk.Frame(self, bg='#2c3e50', height=70)
        toolbar.pack(fill='x', padx=0, pady=0)
        toolbar.pack_propagate(False)
        
        title_label = tk.Label(toolbar, 
                            text="إدارة الزبائن",
                            font=('Arial', 16, 'bold'),
                            bg='#2c3e50', fg='white')
        title_label.pack(side='left', padx=20)
        
        # إطار داخلي قابل للتمرير
        toolbar_container = tk.Frame(toolbar, bg='#2c3e50')
        toolbar_container.pack(side='right', fill='both', expand=True, padx=(0, 10))
        
        # Canvas مع شريط تمرير
        canvas = tk.Canvas(toolbar_container, bg='#2c3e50', highlightthickness=0, height=70)
        scrollbar = ttk.Scrollbar(toolbar_container, orient='horizontal', command=canvas.xview)
        
        canvas.configure(xscrollcommand=scrollbar.set)
        canvas.pack(side='top', fill='x')
        scrollbar.pack(side='bottom', fill='x')
        
        # إطار للأزرار داخل Canvas
        buttons_frame = tk.Frame(canvas, bg='#2c3e50')
        canvas_window = canvas.create_window((0, 0), window=buttons_frame, anchor='nw')
        
        # استخدام الصلاحيات بدلاً من التحقق المباشر
        buttons = [
            ("➕ إضافة", self.add_customer, "#27ae60", 'customers.add'),
            ("✏️ تعديل", self.edit_customer, "#3498db", 'customers.edit'),
            ("🗑️ حذف", self.delete_customer, "#e74c3c", 'customers.delete'),
            ("🔄 تحديث", self.refresh_customers, "#95a5a6", 'customers.view'),
            ("📋 تفاصيل", self.show_customer_details, "#9b59b6", 'customers.view_details'),
            ("📜 سجل", self.show_customer_history, "#8e44ad", 'customers.view_history'),
            ("💰 تأشيرات", self.import_visas, "#f39c12", 'customers.import_visas'),
            ("🗑️🔥 إعادة", self.delete_and_reimport, "#e74c3c", 'customers.reimport'),
            ("🗑️ قطاع", self.delete_sector_customers, "#c0392b", 'customers.manage_sectors')
        ]
        
        for text, command, color, permission in buttons:
            if has_permission(permission):
                btn = tk.Button(buttons_frame, text=text, command=command,
                            bg=color, fg='white',
                            font=('Arial', 9),
                            padx=10, pady=4, cursor='hand2')
                btn.pack(side='left', padx=3)
            else:
                # زر معطل
                btn = tk.Button(buttons_frame, text=text,
                            state='disabled',
                            bg='#95a5a6', fg='white',
                            font=('Arial', 9),
                            padx=10, pady=4)
                btn.pack(side='left', padx=3)
        
        # تحديث حجم Canvas
        def configure_canvas(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_window, width=max(buttons_frame.winfo_reqwidth(), canvas.winfo_width()))
        
        buttons_frame.bind("<Configure>", configure_canvas)
        canvas.bind("<Configure>", configure_canvas)

    def create_search_bar(self):
        """إنشاء شريط البحث والتصفية"""
        search_frame = tk.Frame(self, bg='#f1f8ff', relief='groove', borderwidth=2)
        search_frame.pack(fill='x', padx=10, pady=10)
        
        # البحث بالاسم
        tk.Label(search_frame, text="🔍 البحث:", 
                font=('Arial', 11, 'bold'), 
                bg='#f1f8ff').pack(side='left', padx=10)
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var,
                                font=('Arial', 11), width=30)
        search_entry.pack(side='left', padx=5)
        search_entry.bind('<KeyRelease>', self.on_search_changed)
        
        # تصفية بالقطاع
        tk.Label(search_frame, text="القطاع:", 
                font=('Arial', 11, 'bold'), 
                bg='#f1f8ff').pack(side='left', padx=(20,5))
        
        self.sector_var = tk.StringVar()
        self.sector_combo = ttk.Combobox(search_frame, textvariable=self.sector_var,
                                        width=15, state='readonly', font=('Arial', 11))
        self.sector_combo['values'] = ['الكل'] + [s['name'] for s in self.sectors]
        self.sector_combo.set('الكل')
        self.sector_combo.pack(side='left', padx=5)
        self.sector_combo.bind('<<ComboboxSelected>>', self.on_filter_changed)
        
        # تصفية بنوع العداد
        tk.Label(search_frame, text="نوع العداد:", 
                font=('Arial', 11, 'bold'), 
                bg='#f1f8ff').pack(side='left', padx=(20,5))
        
        self.meter_type_var = tk.StringVar()
        meter_type_combo = ttk.Combobox(search_frame, textvariable=self.meter_type_var,
                                    width=12, state='readonly', font=('Arial', 11))
        meter_type_combo['values'] = ['الكل', 'مولدة', 'علبة توزيع', 'رئيسية', 'زبون']
        meter_type_combo.set('الكل')
        meter_type_combo.pack(side='left', padx=5)
        meter_type_combo.bind('<<ComboboxSelected>>', self.on_filter_changed)
        
        # تصفية بالرصيد
        tk.Label(search_frame, text="حالة الرصيد:", 
                font=('Arial', 11, 'bold'), 
                bg='#f1f8ff').pack(side='left', padx=(20,5))
        
        self.balance_var = tk.StringVar()
        balance_combo = ttk.Combobox(search_frame, textvariable=self.balance_var,
                                    width=12, state='readonly', font=('Arial', 11))
        balance_combo['values'] = ['الكل', 'سالب فقط', 'موجب فقط', 'صفر فقط']
        balance_combo.set('الكل')
        balance_combo.pack(side='left', padx=5)
        balance_combo.bind('<<ComboboxSelected>>', self.on_filter_changed)
    
    def create_customer_tree(self):
        """إنشاء شجرة عرض الزبائن مع الحقول الجديدة"""
        # إطار يحتوي على الشجرة وشريط التمرير
        tree_frame = tk.Frame(self)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # شريط تمرير عمودي
        v_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical')
        v_scrollbar.pack(side='right', fill='y')
        
        # شريط تمرير أفقي
        h_scrollbar = ttk.Scrollbar(tree_frame, orient='horizontal')
        h_scrollbar.pack(side='bottom', fill='x')
        
        # إنشاء الشجرة
        columns = ('id', 'name', 'sector', 'meter_type', 'parent', 'box', 'serial', 'balance', 'phone', 'visa', 'status')
        
        self.tree = ttk.Treeview(tree_frame, columns=columns,
                                yscrollcommand=v_scrollbar.set,
                                xscrollcommand=h_scrollbar.set,
                                selectmode='browse',
                                show='headings',
                                height=20)
        
        v_scrollbar.config(command=self.tree.yview)
        h_scrollbar.config(command=self.tree.xview)
        
        # تعريف رؤوس الأعمدة
        columns_config = [
            ('id', 'ID', 50, 'center'),
            ('name', 'اسم الزبون', 180, 'w'),
            ('sector', 'القطاع', 100, 'center'),
            ('meter_type', 'نوع العداد', 100, 'center'),
            ('parent', 'العلبة الأم', 120, 'center'),
            ('box', 'رقم العلبة', 80, 'center'),
            ('serial', 'المسلسل', 80, 'center'),
            ('balance', 'الرصيد الحالي', 100, 'center'),
            ('phone', 'رقم الهاتف', 100, 'center'),
            ('visa', 'رصيد التأشيرة', 100, 'center'),
            ('status', 'الحالة', 70, 'center')
        ]
        
        for col_id, heading, width, anchor in columns_config:
            self.tree.heading(col_id, text=heading)
            self.tree.column(col_id, width=width, anchor=anchor)
        
        self.tree.pack(fill='both', expand=True)
        
        # إضافة تنسيقات للألوان
        self.tree.tag_configure('negative', foreground='#e74c3c')
        self.tree.tag_configure('positive', foreground='#27ae60')
        self.tree.tag_configure('zero', foreground='#7f8c8d')
        self.tree.tag_configure('inactive', foreground='#95a5a6')
        
        # ربط الأحداث
        self.tree.bind('<Double-Button-1>', self.on_double_click)
        self.tree.bind('<<TreeviewSelect>>', self.on_selection_changed)
    
    def create_statusbar(self):
        """إنشاء شريط الحالة السفلي"""
        self.statusbar = tk.Frame(self, bg='#34495e', height=30)
        self.statusbar.pack(fill='x', padx=10, pady=5)
        self.statusbar.pack_propagate(False)
        
        # معلومات الحالة
        self.status_label = tk.Label(self.statusbar,
                                    text="جاهز | عدد الزبائن: 0",
                                    bg='#34495e', fg='white',
                                    font=('Arial', 10))
        self.status_label.pack(side='left', padx=10)
        
        # معلومات الإحصائيات
        self.stats_label = tk.Label(self.statusbar,
                                   text="",
                                   bg='#34495e', fg='#bdc3c7',
                                   font=('Arial', 9))
        self.stats_label.pack(side='right', padx=10)
            
    def load_customers(self, search_term="", sector_id=None, meter_type_filter="الكل", balance_filter="الكل"):
        """تحميل قائمة الزبائن مع إمكانية البحث والتصفية"""
        if not self.customer_manager:
            self.show_error_message("مدير الزبائن غير متاح")
            return
        
        # مسح البيانات الحالية
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            # جلب الزبائن من قاعدة البيانات
            customers = self.customer_manager.search_customers(
                search_term=search_term,
                sector_id=sector_id
            )
            
            # تطبيق فلتر نوع العداد
            if meter_type_filter != "الكل":
                customers = [c for c in customers if c.get('meter_type', 'زبون') == meter_type_filter]
            
            # تطبيق فلتر الرصيد
            if balance_filter == "سالب فقط":
                customers = [c for c in customers if c.get('current_balance', 0) < 0]
            elif balance_filter == "موجب فقط":
                customers = [c for c in customers if c.get('current_balance', 0) > 0]
            elif balance_filter == "صفر فقط":
                customers = [c for c in customers if c.get('current_balance', 0) == 0]
            
            # إضافة الزبائن إلى الشجرة
            customer_count = 0
            balance_stats = {'negative': 0, 'positive': 0, 'zero': 0, 'total_balance': 0}
            meter_type_stats = {'مولدة': 0, 'علبة توزيع': 0, 'رئيسية': 0, 'زبون': 0}
            
            for customer in customers:
                customer_id = customer['id']
                name = customer['name']
                sector = customer.get('sector_name', 'غير محدد')
                meter_type = customer.get('meter_type', 'زبون')
                
                # =========== استخدام parent_display مباشرة من بيانات الزبون ===========
                # تأكد من وجود parent_display في البيانات
                parent_display = customer.get('parent_display', '')
                
                # إذا لم يكن موجوداً، حاول بناؤه
                if not parent_display:
                    parent_meter = customer.get('parent_name', '')
                    parent_box = customer.get('parent_box_number', '')
                    parent_type = customer.get('parent_meter_type', '')
                    
                    if parent_box and parent_type and parent_meter:
                        parent_display = f"{parent_box} ({parent_type}) - {parent_meter}"
                    elif parent_box and parent_meter:
                        parent_display = f"{parent_box} - {parent_meter}"
                    elif parent_meter:
                        parent_display = parent_meter
                    elif parent_box:
                        parent_display = f"علبة {parent_box}"
                    else:
                        parent_display = ''
                # =========== نهاية التعديل ===========
                
                box = customer.get('box_number', '')
                serial = customer.get('serial_number', '')
                balance = customer.get('current_balance', 0)
                phone = customer.get('phone_number', '')
                visa = customer.get('visa_balance', 0)
                is_active = customer.get('is_active', True)
                
                # تحديث إحصائيات نوع العداد
                if meter_type in meter_type_stats:
                    meter_type_stats[meter_type] += 1
                
                # تحديد اللون بناءً على الرصيد
                tags = []
                if balance < 0:
                    tags.append('negative')
                    balance_stats['negative'] += 1
                elif balance > 0:
                    tags.append('positive')
                    balance_stats['positive'] += 1
                else:
                    tags.append('zero')
                    balance_stats['zero'] += 1
                
                if not is_active:
                    tags.append('inactive')
                
                balance_stats['total_balance'] += balance
                
                # إضافة الزبون للشجرة
                self.tree.insert("", "end", values=(
                    customer_id,
                    name,
                    sector,
                    meter_type,
                    parent_display,  # استخدام parent_display مباشرة
                    box,
                    serial,
                    f"{balance:,.0f} كيلو واط",
                    phone,
                    f"{visa:,.0f}",
                    "نشط" if is_active else "غير نشط"
                ), tags=tuple(tags))
                
                customer_count += 1
            
            # تحديث شريط الحالة
            self.status_label.config(text=f"عدد الزبائن: {customer_count}")
            
            # تحديث الإحصائيات
            stats_text = (f"مولدة: {meter_type_stats['مولدة']} | "
                        f"علبة توزيع: {meter_type_stats['علبة توزيع']} | "
                        f"رئيسية: {meter_type_stats['رئيسية']} | "
                        f"زبون: {meter_type_stats['زبون']}")
            self.stats_label.config(text=stats_text)
            
        except Exception as e:
            logger.error(f"خطأ في تحميل الزبائن: {e}")
            self.show_error_message(f"خطأ في تحميل البيانات: {str(e)}")


    def on_search_changed(self, event=None):
        """عند تغيير نص البحث"""
        search_term = self.search_var.get().strip()
        sector_name = self.sector_var.get()
        meter_type_filter = self.meter_type_var.get()
        balance_filter = self.balance_var.get()
        
        # تحويل اسم القطاع إلى ID
        sector_id = None
        if sector_name and sector_name != 'الكل':
            for sector in self.sectors:
                if sector['name'] == sector_name:
                    sector_id = sector['id']
                    break
        
        self.load_customers(search_term, sector_id, meter_type_filter, balance_filter)
    
    def on_filter_changed(self, event=None):
        """عند تغيير عوامل التصفية"""
        self.on_search_changed()
    
    def on_double_click(self, event):
        """عند النقر المزدوج على صف"""
        self.show_customer_details()
    
    def on_selection_changed(self, event):
        """عند تغيير العنصر المحدد"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            customer_name = item['values'][1]
            self.status_label.config(text=f"محدد: {customer_name}")
    
    def get_selected_customer_id(self):
        """الحصول على معرف الزبون المحدد"""
        selection = self.tree.selection()
        if not selection:
            return None
        
        item = self.tree.item(selection[0])
        return item['values'][0]  # العمود الأول هو ID
    
    def add_customer(self):
        """فتح نموذج إضافة زبون جديد"""
        try:
            require_permission('customers.add')
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return
        
        from ui.customer_form import CustomerForm
        form = CustomerForm(self, "إضافة زبون جديد", self.sectors, user_id=self.user_data.get('id'))
        
        if form.result:
            # حفظ الزبون الجديد في قاعدة البيانات
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
        """فتح نموذج تعديل الزبون المحدد"""
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
            # جلب بيانات الزبون
            customer = self.customer_manager.get_customer(customer_id)
            if not customer:
                messagebox.showerror("خطأ", "الزبون غير موجود")
                return
            
            from ui.customer_form import CustomerForm
            form = CustomerForm(self, "تعديل بيانات الزبون", self.sectors, customer, user_id=self.user_data.get('id'))
            
            if form.result:
                # تحديث بيانات الزبون
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
        """حذف الزبون المحدد"""
        try:
            require_permission('customers.delete')
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return

        customer_id = self.get_selected_customer_id()
        if not customer_id:
            messagebox.showwarning("تحذير", "يرجى تحديد زبون أولاً")
            return
        
        # تأكيد الحذف
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
        """عرض تفاصيل الزبون المحدد"""
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
        """تحديث قائمة الزبائن"""
        self.load_customers()
        self.status_label.config(text="تم تحديث القائمة")
    
    def show_error_message(self, message):
        """عرض رسالة خطأ"""
        messagebox.showerror("خطأ", message)
    
    def show_customer_history(self):
        """عرض السجل التاريخي للزبون"""
        customer_id = self.get_selected_customer_id()
        if not customer_id:
            messagebox.showwarning("تحذير", "يرجى تحديد زبون أولاً")
            return
        
        try:
            # جلب بيانات الزبون
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
        """فتح محرر التأشيرات الجديد"""
        try:
            require_permission('customers.import_visas')
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return
        
        try:
            # استيراد محرر التأشيرات وفتحه مباشرة
            from modules.visa_importer import VisaEditor
            
            # الحصول على النافذة الرئيسية
            root_window = self.winfo_toplevel()
            
            # فتح محرر التأشيرات
            editor = VisaEditor(root_window, user_id=self.user_data.get('id', 1))
            
            logger.info(f"تم فتح محرر التأشيرات للمستخدم {self.user_data.get('id', 1)}")
            
        except ImportError as e:
            logger.error(f"خطأ في تحميل محرر التأشيرات: {e}")
            messagebox.showerror("خطأ", 
                f"❌ لا يمكن تحميل محرر التأشيرات\n\n"
                f"السبب: {str(e)}\n\n"
                f"تأكد من وجود ملف: modules/visa_editor.py"
            )
        except Exception as e:
            logger.error(f"خطأ في فتح محرر التأشيرات: {e}")
            messagebox.showerror("خطأ", f"❌ فشل فتح محرر التأشيرات: {str(e)}")
    
    def delete_and_reimport(self):
        """حذف جميع الزبائن وإعادة الاستيراد"""
        try:
            require_permission('customers.reimport')
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return
        
        # تحذير شديد
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
        
        # تأكيد إضافي
        double_check = messagebox.askyesno("تأكيد نهائي", 
                                        "⚠️ تأكيد نهائي: هل أنت متأكد 100%؟\n"
                                        "هذا الإجراء لا يمكن التراجع عنه!")
        if not double_check:
            return
        
        try:
            # 1. عرض نافذة اختيار مجلد Excel
            from tkinter import filedialog
            excel_folder = filedialog.askdirectory(
                title="اختر مجلد ملفات Excel"
            )
            
            if not excel_folder:
                return
            
            # 2. التحقق من وجود ملفات Excel
            import os
            excel_files = [f for f in os.listdir(excel_folder) if f.endswith('.xlsx')]
            if not excel_files:
                messagebox.showerror("خطأ", "لا توجد ملفات Excel في المجلد المحدد")
                return
            
            # 3. عرض الملفات التي سيتم استيرادها
            files_msg = f"سيتم استيراد {len(excel_files)} ملف:\n\n"
            for file in excel_files:
                files_msg += f"• {file}\n"
            
            if not messagebox.askyesno("تأكيد الملفات", files_msg + "\nهل تريد المتابعة؟"):
                return
            
            # 4. حذف جميع الزبائن
            delete_result = self.customer_manager.delete_all_customers()
            
            if not delete_result.get('success'):
                messagebox.showerror("خطأ", f"فشل حذف الزبائن: {delete_result.get('error')}")
                return
            
            # 5. استيراد البيانات الجديدة
            from database.migrations import ExcelMigration
            
            # شريط تقدم
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
                                text="يرجاء الانتظار...",
                                font=('Arial', 10))
            status_label.pack()
            
            progress_window.update()
            
            # تنفيذ الاستيراد
            migrator = ExcelMigration(excel_folder)
            success = migrator.migrate_all_data()
            
            progress_bar.stop()
            progress_window.destroy()
            
            if success:
                # 6. تحديث القائمة
                self.refresh_customers()
                
                # 7. عرض تقرير النتائج
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
    
    def delete_sector_customers(self):
        """حذف زبائن قطاع معين"""
        try:
            require_permission('customers.manage_sectors')
        except PermissionError as e:
            messagebox.showerror("صلاحيات", str(e))
            return
        
        # نافذة اختيار القطاع
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
        
        # زر التأكيد
        def confirm_delete():
            sector_name = sector_var.get()
            if not sector_name:
                messagebox.showwarning("تحذير", "يرجى اختيار قطاع")
                return
            
            # تحذير
            warning = f"""
            ⚠️ تحذير!
            
            سيتم حذف جميع زبائن قطاع: {sector_name}
            هل أنت متأكد؟
            """
            
            if messagebox.askyesno("تحذير", warning):
                # البحث عن معرف القطاع
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