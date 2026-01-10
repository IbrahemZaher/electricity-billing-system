# ui/activity_log_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ActivityLogUI:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.create_widgets()
    
    def create_widgets(self):
        """إنشاء واجهة سجل النشاط"""
        for widget in self.parent.winfo_children():
            widget.destroy()
        
        frame = ttk.Frame(self.parent)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        title = ttk.Label(frame, text="سجل النشاط", font=("Arial", 20, "bold"))
        title.pack(pady=10)
        
        # شريط البحث
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill='x', pady=10)
        
        ttk.Label(search_frame, text="بحث:").pack(side='left', padx=5)
        self.search_entry = ttk.Entry(search_frame, width=40)
        self.search_entry.pack(side='left', padx=5)
        ttk.Button(search_frame, text="بحث", command=self.search_logs).pack(side='left', padx=5)
        
        # جدول سجل النشاط
        columns = ('id', 'user', 'action', 'timestamp', 'details')
        self.tree = ttk.Treeview(frame, columns=columns, show='headings', height=15)
        
        # تعريف العناوين
        self.tree.heading('id', text='#')
        self.tree.heading('user', text='المستخدم')
        self.tree.heading('action', text='الإجراء')
        self.tree.heading('timestamp', text='التاريخ والوقت')
        self.tree.heading('details', text='التفاصيل')
        
        self.tree.pack(fill='both', expand=True, pady=10)
        
        # تحميل بيانات تجريبية
        self.load_sample_data()
    
    def load_sample_data(self):
        """تحميل بيانات تجريبية"""
        sample_data = [
            (1, 'admin', 'تسجيل دخول', '2024-01-10 13:13:53', 'تم تسجيل الدخول إلى النظام'),
            (2, 'admin', 'فتح الزبائن', '2024-01-10 13:15:23', 'عرض قائمة الزبائن'),
            (3, 'admin', 'فتح الفواتير', '2024-01-10 13:15:49', 'عرض قائمة الفواتير'),
        ]
        
        for data in sample_data:
            self.tree.insert('', 'end', values=data)
    
    def search_logs(self):
        """بحث في سجلات النشاط"""
        search_term = self.search_entry.get()
        messagebox.showinfo("بحث", f"سيتم البحث عن: {search_term}")