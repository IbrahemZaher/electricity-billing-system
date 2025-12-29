# ui/customer_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class CustomerUI(tk.Frame):
    """واجهة إدارة الزبائن الكاملة"""
    
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
        """إنشاء شريط الأدوات العلوي"""
        toolbar = tk.Frame(self, bg='#2c3e50', height=60)
        toolbar.pack(fill='x', padx=0, pady=0)
        toolbar.pack_propagate(False)
        
        # عنوان الشريط
        title_label = tk.Label(toolbar, 
                              text="إدارة الزبائن",
                              font=('Arial', 16, 'bold'),
                              bg='#2c3e50', fg='white')
        title_label.pack(side='left', padx=20)
        
        # أزرار الأدوات
        buttons_frame = tk.Frame(toolbar, bg='#2c3e50')
        buttons_frame.pack(side='right', padx=20)
        
        buttons = [
            ("➕ إضافة زبون جديد", self.add_customer, "#27ae60"),
            ("✏️ تعديل المحدد", self.edit_customer, "#3498db"),
            ("🗑️ حذف المحدد", self.delete_customer, "#e74c3c"),
            ("🔄 تحديث القائمة", self.refresh_customers, "#95a5a6"),
            ("📋 عرض التفاصيل", self.show_customer_details, "#9b59b6")
        ]
        
        for text, command, color in buttons:
            btn = tk.Button(buttons_frame, text=text, command=command,
                          bg=color, fg='white',
                          font=('Arial', 10),
                          padx=12, pady=6, cursor='hand2')
            btn.pack(side='left', padx=5)
    
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
        
        # زر بحث متقدم
        adv_search_btn = tk.Button(search_frame, text="بحث متقدم",
                                  bg='#7f8c8d', fg='white',
                                  font=('Arial', 10),
                                  padx=15, pady=4)
        adv_search_btn.pack(side='right', padx=10)
    
    def create_customer_tree(self):
        """إنشاء شجرة عرض الزبائن"""
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
        columns = ('id', 'name', 'sector', 'box', 'serial', 'balance', 'phone', 'visa', 'status')
        
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
            ('name', 'اسم الزبون', 200, 'w'),
            ('sector', 'القطاع', 120, 'center'),
            ('box', 'رقم العلبة', 90, 'center'),
            ('serial', 'المسلسل', 90, 'center'),
            ('balance', 'الرصيد الحالي', 120, 'center'),
            ('phone', 'رقم الهاتف', 120, 'center'),
            ('visa', 'رصيد التأشيرة', 120, 'center'),
            ('status', 'الحالة', 80, 'center')
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
    
    def load_customers(self, search_term="", sector_id=None, balance_filter="الكل"):
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
            
            for customer in customers:
                customer_id = customer['id']
                name = customer['name']
                sector = customer.get('sector_name', 'غير محدد')
                box = customer.get('box_number', '')
                serial = customer.get('serial_number', '')
                balance = customer.get('current_balance', 0)
                phone = customer.get('phone_number', '')
                visa = customer.get('visa_balance', 0)
                is_active = customer.get('is_active', True)
                
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
                    box,
                    serial,
                    f"{balance:,.0f} ل.س",
                    phone,
                    f"{visa:,.0f}",
                    "نشط" if is_active else "غير نشط"
                ), tags=tuple(tags))
                
                customer_count += 1
            
            # تحديث شريط الحالة
            self.status_label.config(text=f"عدد الزبائن: {customer_count}")
            
            # تحديث الإحصائيات
            stats_text = (f"رصيد سالب: {balance_stats['negative']} | "
                         f"رصيد موجب: {balance_stats['positive']} | "
                         f"إجمالي الرصيد: {balance_stats['total_balance']:,.0f} ل.س")
            self.stats_label.config(text=stats_text)
            
        except Exception as e:
            logger.error(f"خطأ في تحميل الزبائن: {e}")
            self.show_error_message(f"خطأ في تحميل البيانات: {str(e)}")
    
    def on_search_changed(self, event=None):
        """عند تغيير نص البحث"""
        search_term = self.search_var.get().strip()
        sector_name = self.sector_var.get()
        balance_filter = self.balance_var.get()
        
        # تحويل اسم القطاع إلى ID
        sector_id = None
        if sector_name and sector_name != 'الكل':
            for sector in self.sectors:
                if sector['name'] == sector_name:
                    sector_id = sector['id']
                    break
        
        self.load_customers(search_term, sector_id, balance_filter)
    
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
        from ui.customer_form import CustomerForm
        form = CustomerForm(self, "إضافة زبون جديد", self.sectors)
        
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
            form = CustomerForm(self, "تعديل بيانات الزبون", self.sectors, customer)
            
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
