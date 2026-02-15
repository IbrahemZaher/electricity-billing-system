# ui/manage_children.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class ManageChildrenDialog:
    """نافذة إدارة الأبناء لوالد معين"""
    
    def __init__(self, parent, customer_manager, parent_data, user_id):
        self.parent = parent
        self.customer_manager = customer_manager
        self.parent_data = parent_data
        self.user_id = user_id
        self.potential_children = []
        self.check_vars = {}  # child_id -> tk.BooleanVar
        
        self.create_dialog()
        self.load_data()
        
        self.dialog.grab_set()
        self.dialog.wait_window()
    
    def create_dialog(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"إدارة الأبناء - {self.parent_data['name']}")
        self.dialog.geometry("750x600")
        self.dialog.resizable(True, True)
        self.dialog.configure(bg='#f5f7fa')
        
        # إطار العنوان
        title_frame = tk.Frame(self.dialog, bg='#3498db', height=60)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        
        tk.Label(title_frame, 
                text=f"👥 إدارة الأبناء للوالد: {self.parent_data['name']} ({self.parent_data['meter_type']})",
                font=('Arial', 14, 'bold'),
                bg='#3498db', fg='white').pack(expand=True)
        
        # إطار القائمة مع تمرير
        list_frame = tk.Frame(self.dialog, bg='white')
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # شريط تمرير
        canvas = tk.Canvas(list_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg='white')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # إطار الأزرار السفلية
        btn_frame = tk.Frame(self.dialog, bg='#f5f7fa', height=60)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Button(btn_frame, text="💾 حفظ التغييرات", 
                 command=self.save_changes,
                 bg='#27ae60', fg='white',
                 font=('Arial', 11, 'bold'),
                 padx=20, pady=8).pack(side='right', padx=5)
        
        tk.Button(btn_frame, text="❌ إلغاء", 
                 command=self.dialog.destroy,
                 bg='#e74c3c', fg='white',
                 font=('Arial', 11),
                 padx=20, pady=8).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="✅ تحديد الكل", 
                 command=self.select_all,
                 bg='#3498db', fg='white',
                 font=('Arial', 10),
                 padx=15, pady=5).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="❎ إلغاء الكل", 
                 command=self.deselect_all,
                 bg='#95a5a6', fg='white',
                 font=('Arial', 10),
                 padx=15, pady=5).pack(side='left', padx=5)
    
    def load_data(self):
        """تحميل قائمة الأبناء المحتملين وعرضها"""
        self.potential_children = self.customer_manager.get_potential_children(self.parent_data['id'])
        
        if not self.potential_children:
            tk.Label(self.scrollable_frame, 
                    text="لا يوجد أبناء محتملين لهذا الوالد",
                    font=('Arial', 12),
                    bg='white', fg='#7f8c8d').pack(pady=50)
            return
        
        # رؤوس الأعمدة
        header_frame = tk.Frame(self.scrollable_frame, bg='#ecf0f1', height=30)
        header_frame.pack(fill='x', pady=(0, 5))
        
        tk.Label(header_frame, text="تحديد", width=8, bg='#ecf0f1', font=('Arial', 10, 'bold')).pack(side='left')
        tk.Label(header_frame, text="النوع", width=12, bg='#ecf0f1', font=('Arial', 10, 'bold')).pack(side='left')
        tk.Label(header_frame, text="رقم العلبة", width=12, bg='#ecf0f1', font=('Arial', 10, 'bold')).pack(side='left')
        tk.Label(header_frame, text="الاسم", width=20, bg='#ecf0f1', font=('Arial', 10, 'bold')).pack(side='left', expand=True, fill='x')
        tk.Label(header_frame, text="الرصيد", width=12, bg='#ecf0f1', font=('Arial', 10, 'bold')).pack(side='left')
        tk.Label(header_frame, text="الحالية", width=10, bg='#ecf0f1', font=('Arial', 10, 'bold')).pack(side='left')
        
        # عرض كل ابن محتمل
        for child in self.potential_children:
            row_frame = tk.Frame(self.scrollable_frame, bg='white', pady=2)
            row_frame.pack(fill='x', pady=1)
            
            # متغير التحديد
            var = tk.BooleanVar(value=child.get('is_current_child', False))
            self.check_vars[child['id']] = var
            
            # مربع اختيار
            cb = tk.Checkbutton(row_frame, variable=var, bg='white')
            cb.pack(side='left', padx=5)
            
            # نوع العداد مع أيقونة
            meter_type = child['meter_type']
            icon = '⚡' if meter_type == 'مولدة' else '🔌' if meter_type == 'علبة توزيع' else '🏠' if meter_type == 'رئيسية' else '👤'
            tk.Label(row_frame, text=f"{icon} {meter_type}", width=12, bg='white', anchor='w').pack(side='left')
            
            # رقم العلبة
            tk.Label(row_frame, text=child.get('box_number', ''), width=12, bg='white', anchor='w').pack(side='left')
            
            # الاسم
            tk.Label(row_frame, text=child['name'], width=20, bg='white', anchor='w').pack(side='left', expand=True, fill='x')
            
            # الرصيد
            balance = child.get('current_balance', 0)
            balance_color = '#e74c3c' if balance < 0 else '#27ae60' if balance > 0 else '#7f8c8d'
            tk.Label(row_frame, text=f"{balance:,.0f}", width=12, bg='white', fg=balance_color, anchor='e').pack(side='left')
            
            # حالة الأبوة الحالية
            status = "✓ ابن حالي" if child.get('is_current_child') else "---"
            status_color = '#27ae60' if child.get('is_current_child') else '#95a5a6'
            tk.Label(row_frame, text=status, width=10, bg='white', fg=status_color, anchor='center').pack(side='left')
    
    def select_all(self):
        """تحديد جميع الأبناء"""
        for var in self.check_vars.values():
            var.set(True)
    
    def deselect_all(self):
        """إلغاء تحديد جميع الأبناء"""
        for var in self.check_vars.values():
            var.set(False)
    
    def save_changes(self):
        """حفظ التغييرات (تحديث قائمة الأبناء)"""
        selected_ids = [child_id for child_id, var in self.check_vars.items() if var.get()]
        
        # تأكيد
        msg = f"سيتم تعيين {len(selected_ids)} ابناً للوالد الحالي.\n"
        msg += "هل أنت متأكد من رغبتك في المتابعة؟"
        
        if not messagebox.askyesno("تأكيد", msg):
            return
        
        result = self.customer_manager.update_children(self.parent_data['id'], selected_ids, self.user_id)
        
        if result.get('success'):
            messagebox.showinfo("نجاح", result['message'])
            self.dialog.destroy()
            # يمكن إرسال إشارة للتحديث في النافذة الرئيسية إذا أردنا
            if hasattr(self.parent, 'refresh_customers'):
                self.parent.refresh_customers()
        else:
            messagebox.showerror("خطأ", result.get('error', 'فشل تحديث الأبناء'))