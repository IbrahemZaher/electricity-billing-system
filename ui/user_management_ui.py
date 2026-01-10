# ui/users_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging

logger = logging.getLogger(__name__)

class UsersUI:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.create_widgets()
        self.load_users()
    
    def create_widgets(self):
        """إنشاء واجهة إدارة المستخدمين"""
        for widget in self.parent.winfo_children():
            widget.destroy()
        
        frame = ttk.Frame(self.parent)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        title = ttk.Label(frame, text="إدارة المستخدمين", font=("Arial", 20, "bold"))
        title.pack(pady=10)
        
        # أزرار الإدارة
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', pady=10)
        
        ttk.Button(btn_frame, text="إضافة مستخدم جديد", command=self.add_user).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="تعديل مستخدم", command=self.edit_user).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="حذف مستخدم", command=self.delete_user).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="تصدير قائمة المستخدمين", command=self.export_users).pack(side='left', padx=5)
        
        # جدول المستخدمين
        columns = ('id', 'username', 'full_name', 'role', 'email', 'created_at')
        self.tree = ttk.Treeview(frame, columns=columns, show='headings', height=15)
        
        # تعريف العناوين
        self.tree.heading('id', text='المعرف')
        self.tree.heading('username', text='اسم المستخدم')
        self.tree.heading('full_name', text='الاسم الكامل')
        self.tree.heading('role', text='الدور')
        self.tree.heading('email', text='البريد الإلكتروني')
        self.tree.heading('created_at', text='تاريخ الإنشاء')
        
        self.tree.pack(fill='both', expand=True, pady=10)
        
        # معلومات إحصائية
        stats_frame = ttk.Frame(frame)
        stats_frame.pack(fill='x', pady=10)
        
        self.stats_label = ttk.Label(stats_frame, text="جاري تحميل الإحصائيات...")
        self.stats_label.pack()
    
    def load_users(self):
        """تحميل قائمة المستخدمين"""
        try:
            # بيانات تجريبية - ستحل محلها استعلام قاعدة البيانات
            users = [
                (1, 'admin', 'مدير النظام', 'admin', 'admin@rayan.com', '2024-01-01'),
                (2, 'accountant1', 'محاسب 1', 'accountant', 'acc1@rayan.com', '2024-02-01'),
                (3, 'cashier1', 'أمين صندوق 1', 'cashier', 'cash1@rayan.com', '2024-03-01'),
            ]
            
            # مسح الجدول أولاً
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # إضافة البيانات
            for user in users:
                self.tree.insert('', 'end', values=user)
            
            # تحديث الإحصائيات
            self.stats_label.config(text=f"إجمالي المستخدمين: {len(users)} | المديرين: 1 | المحاسبين: 1 | أمناء الصندوق: 1")
            
            logger.info(f"تم تحميل {len(users)} مستخدم")
        except Exception as e:
            logger.error(f"خطأ في تحميل المستخدمين: {e}")
            messagebox.showerror("خطأ", f"فشل تحميل المستخدمين: {str(e)}")
    
    def add_user(self):
        """إضافة مستخدم جديد"""
        logger.info("فتح نافذة إضافة مستخدم جديد")
        messagebox.showinfo("إضافة مستخدم", "سيتم فتح نافذة إضافة مستخدم جديد")
        # هنا سيتم فتح نافذة إضافة مستخدم
    
    def edit_user(self):
        """تعديل مستخدم"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "يرجى اختيار مستخدم من القائمة")
            return
        logger.info("تعديل المستخدم المحدد")
    
    def delete_user(self):
        """حذف مستخدم"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "يرجى اختيار مستخدم من القائمة")
            return
        
        user_data = self.tree.item(selected[0])['values']
        confirm = messagebox.askyesno("تأكيد الحذف", f"هل أنت متأكد من حذف المستخدم: {user_data[2]}؟")
        
        if confirm:
            logger.info(f"حذف المستخدم: {user_data[1]}")
            self.tree.delete(selected[0])
            messagebox.showinfo("نجاح", "تم حذف المستخدم بنجاح")
    
    def export_users(self):
        """تصدير قائمة المستخدمين"""
        logger.info("تصدير قائمة المستخدمين")
        messagebox.showinfo("تصدير", "سيتم تصدير قائمة المستخدمين إلى ملف Excel")