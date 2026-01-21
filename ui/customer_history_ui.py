# ui/customer_history_ui.py

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class CustomerHistoryUI:
    """واجهة عرض السجل التاريخي للزبون"""
    
    def __init__(self, parent, customer_data, user_data):
        self.parent = parent
        self.customer_data = customer_data
        self.user_data = user_data
        self.history_manager = None
        
        self.load_history_manager()
        self.create_dialog()
        self.create_widgets()
        self.load_history()
        
        self.dialog.grab_set()
    
    def load_history_manager(self):
        """تحميل مدير السجل التاريخي"""
        try:
            from modules.history_manager import HistoryManager
            self.history_manager = HistoryManager()
        except ImportError as e:
            logger.error(f"خطأ في تحميل مدير السجل التاريخي: {e}")
            messagebox.showerror("خطأ", "لا يمكن تحميل وحدة السجل التاريخي")
    
    def create_dialog(self):
        """إنشاء النافذة المنبثقة"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"سجل العمليات - {self.customer_data['name']}")
        self.dialog.geometry("1000x700")
        self.dialog.resizable(True, True)
        self.dialog.configure(bg='#f5f7fa')
        
        # مركزية النافذة
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'1000x700+{x}+{y}')
    
    def create_widgets(self):
        """إنشاء عناصر الواجهة"""
        # إطار العنوان
        title_frame = tk.Frame(self.dialog, bg='#3498db', height=80)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        
        title_text = f"📜 سجل العمليات التاريخية - {self.customer_data['name']}"
        title_label = tk.Label(title_frame, text=title_text,
                              font=('Arial', 16, 'bold'),
                              bg='#3498db', fg='white')
        title_label.pack(expand=True)
        
        # إطار معلومات الزبون
        info_frame = tk.Frame(self.dialog, bg='#e8f4fc', relief='ridge', borderwidth=1)
        info_frame.pack(fill='x', padx=10, pady=10)
        
        # تنسيق الأرقام بشكل آمن
        current_balance = self._safe_float(self.customer_data.get('current_balance', 0))
        visa_balance = self._safe_float(self.customer_data.get('visa_balance', 0))
        withdrawal_amount = self._safe_float(self.customer_data.get('withdrawal_amount', 0))
        
        info_text = f"""
        👤 الزبون: {self.customer_data['name']} | 📍 القطاع: {self.customer_data.get('sector_name', 'غير محدد')}
        📦 العلبة: {self.customer_data.get('box_number', '')} | 💰 الرصيد الحالي: {current_balance:,.0f} كيلو واط
        🏦 رصيد التأشيرة: {visa_balance:,.0f} | 💵 السحب: {withdrawal_amount:,.0f}
        """
        
        info_label = tk.Label(info_frame, text=info_text,
                             font=('Arial', 11),
                             bg='#e8f4fc', fg='#2c3e50',
                             justify='left')
        info_label.pack(padx=10, pady=10)
        
        # شريط الأدوات
        toolbar_frame = tk.Frame(self.dialog, bg='#2c3e50', height=50)
        toolbar_frame.pack(fill='x', pady=(0, 10))
        toolbar_frame.pack_propagate(False)
        
        # أزرار الأدوات
        tools = tk.Frame(toolbar_frame, bg='#2c3e50')
        tools.pack()
        
        tk.Button(tools, text="🔄 تحديث",
                 command=self.refresh_history,
                 bg='#3498db', fg='white',
                 font=('Arial', 10)).pack(side='left', padx=5)
        
        tk.Button(tools, text="📊 ملخص",
                 command=self.show_summary,
                 bg='#9b59b6', fg='white',
                 font=('Arial', 10)).pack(side='left', padx=5)
        
        tk.Button(tools, text="📤 تصدير Excel",
                 command=self.export_history,
                 bg='#27ae60', fg='white',
                 font=('Arial', 10)).pack(side='left', padx=5)
        
        # إطار الشجرة
        tree_frame = tk.Frame(self.dialog)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # شريط التمرير
        v_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical')
        v_scrollbar.pack(side='right', fill='y')
        
        h_scrollbar = ttk.Scrollbar(tree_frame, orient='horizontal')
        h_scrollbar.pack(side='bottom', fill='x')
        
        # إنشاء الشجرة
        columns = ('id', 'date', 'type', 'old_value', 'new_value', 
                  'amount', 'balance_after', 'notes', 'user')
        
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
            ('id', '#', 50, 'center'),
            ('date', 'التاريخ والوقت', 150, 'center'),
            ('type', 'نوع العملية', 150, 'center'),
            ('old_value', 'القيمة القديمة', 120, 'center'),
            ('new_value', 'القيمة الجديدة', 120, 'center'),
            ('amount', 'المبلغ', 100, 'center'),
            ('balance_after', 'الرصيد بعد', 120, 'center'),
            ('notes', 'ملاحظات', 200, 'w'),
            ('user', 'المستخدم', 120, 'center')
        ]
        
        for col_id, heading, width, anchor in columns_config:
            self.tree.heading(col_id, text=heading)
            self.tree.column(col_id, width=width, anchor=anchor)
        
        self.tree.pack(fill='both', expand=True)
        
        # شريط الحالة
        self.status_frame = tk.Frame(self.dialog, bg='#34495e', height=30)
        self.status_frame.pack(fill='x', padx=10, pady=(0, 10))
        self.status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(self.status_frame,
                                    text="جارٍ تحميل السجل...",
                                    bg='#34495e', fg='white',
                                    font=('Arial', 10))
        self.status_label.pack(side='left', padx=10)
    
    def _safe_float(self, value, default=0.0):
        """تحويل قيمة إلى float بشكل آمن"""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def load_history(self):
        """تحميل السجل التاريخي"""
        if not self.history_manager:
            self.show_error("مدير السجل غير متاح")
            return
        
        try:
            # مسح البيانات الحالية
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # جلب البيانات
            result = self.history_manager.get_customer_history(
                customer_id=self.customer_data['id']
            )
            
            if not result['success']:
                self.show_error(result.get('error', 'خطأ في جلب البيانات'))
                return
            
            # إضافة البيانات إلى الشجرة
            for record in result['history']:
                # تحويل القيم إلى float بشكل آمن
                old_value = self._safe_float(record.get('old_value', 0))
                new_value = self._safe_float(record.get('new_value', 0))
                amount = self._safe_float(record.get('amount', 0))
                balance_after = self._safe_float(record.get('current_balance_after', 0))
                
                values = (
                    record['id'],
                    record.get('created_at_formatted', ''),
                    record.get('transaction_type_arabic', ''),
                    f"{old_value:,.0f}",
                    f"{new_value:,.0f}",
                    f"{amount:,.0f}",
                    f"{balance_after:,.0f}",
                    (record.get('notes', '') or '')[:50] + ('...' if len(record.get('notes', '') or '') > 50 else ''),
                    record.get('created_by_name', 'نظام')
                )
                
                self.tree.insert('', 'end', values=values)
            
            # تحديث شريط الحالة
            self.status_label.config(
                text=f"عدد السجلات: {result['total_count']} | آخر تحديث: {datetime.now().strftime('%H:%M:%S')}"
            )
            
        except Exception as e:
            logger.error(f"خطأ في تحميل السجل التاريخي: {e}")
            self.show_error(f"خطأ في تحميل البيانات: {str(e)}")
    
    def refresh_history(self):
        """تحديث السجل"""
        self.load_history()
    
    def show_summary(self):
        """عرض ملخص السجل"""
        if not self.history_manager:
            return
        
        try:
            result = self.history_manager.get_history_summary(
                customer_id=self.customer_data['id']
            )
            
            if result['success']:
                summary = result['summary']
                
                # استخدام _safe_float للقيم الرقمية
                total_visa = self._safe_float(summary.get('total_visa', 0))
                total_withdrawal = self._safe_float(summary.get('total_withdrawal', 0))
                
                message = f"""
                📊 ملخص السجل التاريخي:
                
                • إجمالي العمليات: {summary.get('total_transactions', 0)}
                • إجمالي التأشيرات: {total_visa:,.0f}
                • إجمالي السحوبات: {total_withdrawal:,.0f}
                • أول عملية: {summary.get('first_transaction', 'غير متوفر')}
                • آخر عملية: {summary.get('last_transaction', 'غير متوفر')}
                """
                
                messagebox.showinfo("ملخص السجل", message)
            
        except Exception as e:
            logger.error(f"خطأ في عرض الملخص: {e}")
            messagebox.showerror("خطأ", f"فشل عرض الملخص: {str(e)}")
    
    def export_history(self):
        """تصدير السجل إلى Excel"""
        try:
            from modules.history_manager import HistoryManager
            history_mgr = HistoryManager()
            
            result = history_mgr.get_customer_history(
                customer_id=self.customer_data['id'],
                limit=10000  # جلب جميع السجلات
            )
            
            if not result['success']:
                messagebox.showerror("خطأ", "فشل في جلب البيانات للتصدير")
                return
            
            # إنشاء DataFrame
            import pandas as pd
            from datetime import datetime
            
            data = []
            for record in result['history']:
                data.append({
                    'التاريخ': record.get('created_at_formatted', ''),
                    'نوع العملية': record.get('transaction_type_arabic', ''),
                    'القيمة القديمة': self._safe_float(record.get('old_value', 0)),
                    'القيمة الجديدة': self._safe_float(record.get('new_value', 0)),
                    'المبلغ': self._safe_float(record.get('amount', 0)),
                    'الرصيد بعد العملية': self._safe_float(record.get('current_balance_after', 0)),
                    'ملاحظات': record.get('notes', ''),
                    'المستخدم': record.get('created_by_name', 'نظام')
                })
            
            df = pd.DataFrame(data)
            
            # حفظ في ملف Excel
            filename = f"history_{self.customer_data['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(filename, index=False, engine='openpyxl')
            
            messagebox.showinfo("نجاح", f"تم التصدير إلى: {filename}")
            
        except Exception as e:
            logger.error(f"خطأ في التصدير: {e}")
            messagebox.showerror("خطأ", f"فشل التصدير: {str(e)}")
    
    def show_error(self, message):
        """عرض رسالة خطأ"""
        messagebox.showerror("خطأ", message)
        self.status_label.config(text=f"خطأ: {message}")