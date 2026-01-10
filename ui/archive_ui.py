# ui/archive_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ArchiveUI:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.create_widgets()
    
    def create_widgets(self):
        """إنشاء واجهة الأرشيف"""
        # مسح المحتوى القديم
        for widget in self.parent.winfo_children():
            widget.destroy()
        
        frame = ttk.Frame(self.parent)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        title = ttk.Label(frame, text="الأرشيف - الفواتير المؤرشفة", font=("Arial", 20, "bold"))
        title.pack(pady=10)
        
        # شريط البحث
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill='x', pady=10)
        
        ttk.Label(search_frame, text="بحث:").pack(side='left', padx=5)
        self.search_entry = ttk.Entry(search_frame, width=40)
        self.search_entry.pack(side='left', padx=5)
        ttk.Button(search_frame, text="بحث", command=self.search_archive).pack(side='left', padx=5)
        ttk.Button(search_frame, text="عرض الكل", command=self.load_all).pack(side='left', padx=5)
        
        # جدول الأرشيف
        columns = ('id', 'customer_name', 'invoice_number', 'amount', 'date', 'status')
        self.tree = ttk.Treeview(frame, columns=columns, show='headings', height=15)
        
        # تعريف العناوين
        self.tree.heading('id', text='المعرف')
        self.tree.heading('customer_name', text='اسم الزبون')
        self.tree.heading('invoice_number', text='رقم الفاتورة')
        self.tree.heading('amount', text='المبلغ')
        self.tree.heading('date', text='التاريخ')
        self.tree.heading('status', text='الحالة')
        
        self.tree.pack(fill='both', expand=True, pady=10)
        
        # أزرار التحكم
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="عرض التفاصيل", command=self.view_details).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="استعادة", command=self.restore_item).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="تصدير إلى Excel", command=self.export_to_excel).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="طباعة", command=self.print_report).pack(side='left', padx=5)
    
    def search_archive(self):
        """بحث في الأرشيف"""
        search_term = self.search_entry.get()
        logger.info(f"بحث في الأرشيف عن: {search_term}")
        messagebox.showinfo("بحث", f"سيتم البحث عن: {search_term}")
    
    def load_all(self):
        """تحميل جميع العناصر"""
        logger.info("تحميل كافة العناصر المؤرشفة")
        # هنا سيتم جلب البيانات من قاعدة البيانات
    
    def view_details(self):
        """عرض تفاصيل العنصر المحدد"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "يرجى اختيار عنصر من القائمة")
            return
        logger.info("عرض تفاصيل العنصر المحدد")
    
    def restore_item(self):
        """استعادة العنصر المحدد"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "يرجى اختيار عنصر من القائمة")
            return
        logger.info("استعادة العنصر المحدد")
    
    def export_to_excel(self):
        """تصدير إلى Excel"""
        logger.info("تصدير الأرشيف إلى Excel")
        messagebox.showinfo("تصدير", "سيتم تصدير البيانات إلى ملف Excel")
    
    def print_report(self):
        """طباعة تقرير الأرشيف"""
        logger.info("طباعة تقرير الأرشيف")