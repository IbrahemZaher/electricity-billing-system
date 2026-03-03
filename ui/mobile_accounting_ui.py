# ui/mobile_accounting_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime, timedelta
import threading
import os

from modules.customers import CustomerManager
from modules.collection import CollectionManager
from auth.permissions import require_permission
from database.connection import db  # ✅ تم إضافة الاستيراد المفقود

logger = logging.getLogger(__name__)

class MobileAccountingUI(tk.Frame):
    """واجهة المحاسبة الجوالة – لوحة تحكم المحصل والإدارة"""

    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.user_data = user_data
        self.customer_manager = CustomerManager()
        self.collection_manager = CollectionManager()

        # تحديد ما إذا كان المستخدم محصلاً أم مديراً
        self.is_collector = (user_data.get('role') == 'collector')
        self.is_admin = (user_data.get('role') == 'admin')

        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        # شريط أدوات
        toolbar = tk.Frame(self, bg='#2c3e50', height=50)
        toolbar.pack(fill='x')
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text='📱 نظام المحاسبة الجوالة',
                 font=('Arial', 14, 'bold'), bg='#2c3e50', fg='white').pack(side='left', padx=20)

        if self.is_admin:
            # قائمة المحصلين للاختيار (للمدير)
            tk.Label(toolbar, text='المحصل:', bg='#2c3e50', fg='white').pack(side='left', padx=(20,5))
            self.collector_var = tk.StringVar()
            self.collector_combo = ttk.Combobox(toolbar, textvariable=self.collector_var,
                                                 state='readonly', width=20)
            self.collector_combo.pack(side='left', padx=5)
            self.collector_combo.bind('<<ComboboxSelected>>', self.on_collector_change)
            self.load_collectors_list()

        # إطار المحتوى الرئيسي
        content = tk.Frame(self)
        content.pack(fill='both', expand=True, padx=10, pady=10)

        # قسم الإحصائيات السريعة
        self.stats_frame = tk.LabelFrame(content, text='📊 إحصائيات سريعة', padx=10, pady=10)
        self.stats_frame.pack(fill='x', pady=(0,10))

        # قسم قائمة الزبائن
        customers_frame = tk.LabelFrame(content, text='👥 الزبائن المخصصون', padx=10, pady=10)
        customers_frame.pack(fill='both', expand=True)

        # شريط أدوات قائمة الزبائن
        cust_toolbar = tk.Frame(customers_frame)
        cust_toolbar.pack(fill='x', pady=(0,5))

        tk.Button(cust_toolbar, text='🔄 تحديث', command=self.load_data,
                  bg='#3498db', fg='white').pack(side='left', padx=2)
        tk.Button(cust_toolbar, text='📥 تصدير Excel', command=self.export_to_excel,
                  bg='#27ae60', fg='white').pack(side='left', padx=2)

        # شجرة الزبائن
        self.create_customers_tree(customers_frame)

        # شريط الحالة
        self.status_bar = tk.Label(self, text='جاهز', bd=1, relief='sunken', anchor='w')
        self.status_bar.pack(side='bottom', fill='x')

    def create_customers_tree(self, parent):
        """إنشاء شجرة عرض الزبائن مع أعمدة الأداء"""
        columns = ('id', 'name', 'sector', 'balance', 'last_collection', 'expected', 'status')
        self.tree = ttk.Treeview(parent, columns=columns, show='headings', height=15)

        # تعريف الأعمدة
        self.tree.heading('id', text='ID')
        self.tree.heading('name', text='الاسم')
        self.tree.heading('sector', text='القطاع')
        self.tree.heading('balance', text='الرصيد (ك.و)')
        self.tree.heading('last_collection', text='آخر تحصيل')
        self.tree.heading('expected', text='المتوقع اليوم')
        self.tree.heading('status', text='الحالة')

        self.tree.column('id', width=50, anchor='center')
        self.tree.column('name', width=200)
        self.tree.column('sector', width=100, anchor='center')
        self.tree.column('balance', width=100, anchor='center')
        self.tree.column('last_collection', width=120, anchor='center')
        self.tree.column('expected', width=100, anchor='center')
        self.tree.column('status', width=100, anchor='center')

        # شريط التمرير
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # ربط النقر المزدوج لتسجيل تحصيل
        self.tree.bind('<Double-1>', self.open_collection_dialog)

    def load_data(self):
        """تحميل البيانات حسب المستخدم الحالي أو المحصل المختار"""
        collector_id = None
        if self.is_collector:
            collector_id = self.user_data.get('id')
        elif self.is_admin:
            selected = self.collector_var.get()
            if selected:
                # استخراج id من النص (يمكن تحسينه)
                collector_id = self.collector_map.get(selected)

        if not collector_id:
            self.update_status('يرجى اختيار محصل')
            return

        # جلب الزبائن
        customers = self.customer_manager.get_customers_by_collector(collector_id)
        self.display_customers(customers, collector_id)

        # تحديث الإحصائيات
        self.update_stats(collector_id)

    def display_customers(self, customers, collector_id):
        for item in self.tree.get_children():
            self.tree.delete(item)

        today = datetime.now().date()

        for cust in customers:
            current_balance = cust.get('current_balance', 0)
            # استخدام آخر دفعة (من أي مصدر)
            last_payment = self.collection_manager.get_last_payment(cust['id'])
            last_date = last_payment['payment_datetime'] if last_payment else None
            last_amount = last_payment['amount'] if last_payment else 0
            source = last_payment['source'] if last_payment else None

            # منطق الحالة:
            if current_balance > 0:
                status = '✅ مسدد'
                tag = 'settled'
            else:
                if last_date and last_date.date() == today:
                    status = '✅ تم اليوم'
                    tag = 'collected_today'
                elif last_date and last_date.date() >= (today - timedelta(days=7)):
                    status = '🟢 خلال الأسبوع'
                    tag = 'recent'
                else:
                    status = '🔴 متأخر'
                    tag = 'late'

            # صياغة نص آخر دفعة
            last_display = 'لم يحصل'
            if last_date:
                if source == 'invoice':
                    last_display = f"فاتورة {last_date.strftime('%Y-%m-%d')} ({last_amount:,.0f})"
                else:
                    last_display = f"تحصيل {last_date.strftime('%Y-%m-%d')} ({last_amount:,.0f})"

            self.tree.insert('', 'end', values=(
                cust['id'],
                cust['name'],
                cust.get('sector_name', ''),
                f"{current_balance:,.0f}",
                last_display,
                f"{current_balance:,.0f}",  # المتوقع (يمكن تعديله)
                status
            ), tags=(tag,))

        self.tree.tag_configure('settled', background='#ccffcc')
        self.tree.tag_configure('collected_today', background='#ccffcc')
        self.tree.tag_configure('recent', background='#ffffcc')
        self.tree.tag_configure('late', background='#ffcccc')

    def get_last_collection(self, customer_id, collector_id):
        """الحصول على آخر تحصيل لزبون من قبل محصل معين"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT collection_date, collected_amount
                    FROM collection_logs
                    WHERE customer_id = %s AND collector_id = %s
                    ORDER BY collection_date DESC
                    LIMIT 1
                """, (customer_id, collector_id))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"خطأ في جلب آخر تحصيل: {e}")
            return None

    def update_stats(self, collector_id):
        """تحديث الإحصائيات السريعة"""
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # إحصائيات اليوم
        perf_today = self.collection_manager.get_collector_performance(
            collector_id,
            today.strftime('%Y-%m-%d 00:00:00'),
            today.strftime('%Y-%m-%d 23:59:59')
        )
        # إحصائيات الأسبوع
        perf_week = self.collection_manager.get_collector_performance(
            collector_id,
            week_ago.strftime('%Y-%m-%d 00:00:00'),
            today.strftime('%Y-%m-%d 23:59:59')
        )
        # إحصائيات الشهر
        perf_month = self.collection_manager.get_collector_performance(
            collector_id,
            month_ago.strftime('%Y-%m-%d 00:00:00'),
            today.strftime('%Y-%m-%d 23:59:59')
        )

        # عرض في stats_frame
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        # ✅ استخراج القيم مع التأكد من عدم وجود None
        def safe_int(value):
            return value if value is not None else 0

        total_today = safe_int(perf_today.get('stats', {}).get('total_collected'))
        total_week = safe_int(perf_week.get('stats', {}).get('total_collected'))
        total_month = safe_int(perf_month.get('stats', {}).get('total_collected'))
        count_today = safe_int(perf_today.get('stats', {}).get('total_collections'))
        count_week = safe_int(perf_week.get('stats', {}).get('total_collections'))
        count_month = safe_int(perf_month.get('stats', {}).get('total_collections'))
        pending = len(perf_week.get('pending_customers', []))

        stats_text = (
            f"📅 اليوم: {count_today} عمليات | "
            f"المجموع: {total_today:,.0f} ك.و\n"
            f"📆 الأسبوع: {count_week} عمليات | "
            f"المجموع: {total_week:,.0f} ك.و\n"
            f"📆 الشهر: {count_month} عمليات | "
            f"المجموع: {total_month:,.0f} ك.و\n"
            f"⏳ زبائن لم يحصلوا هذا الأسبوع: {pending}"
        )
        tk.Label(self.stats_frame, text=stats_text, justify='left', font=('Arial', 10)).pack()

    def open_collection_dialog(self, event):
        """فتح نافذة تسجيل تحصيل للزبون المختار"""
        selection = self.tree.selection()
        if not selection:
            return
        item = self.tree.item(selection[0])
        customer_id = item['values'][0]

        # نافذة جديدة
        dialog = tk.Toplevel(self)
        dialog.title('تسجيل تحصيل جديد')
        dialog.geometry('400x300')
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text='المبلغ المحصل (ك.و):').pack(pady=10)
        amount_var = tk.StringVar()
        tk.Entry(dialog, textvariable=amount_var, font=('Arial', 14)).pack(pady=5)

        tk.Label(dialog, text='ملاحظات:').pack(pady=10)
        notes_text = tk.Text(dialog, height=4)
        notes_text.pack(pady=5, padx=10, fill='x')

        def save():
            try:
                amount = float(amount_var.get())
                notes = notes_text.get('1.0', 'end-1c').strip()
                # هنا يمكن إضافة إحداثيات GPS إذا أمكن
                result = self.collection_manager.record_collection(
                    collector_id=self.user_data['id'],
                    customer_id=customer_id,
                    collected_amount=amount,
                    notes=notes
                )
                if result['success']:
                    messagebox.showinfo('نجاح', 'تم تسجيل التحصيل بنجاح')
                    dialog.destroy()
                    self.load_data()  # تحديث البيانات
                else:
                    messagebox.showerror('خطأ', result.get('error', 'فشل التسجيل'))
            except ValueError:
                messagebox.showerror('خطأ', 'الرجاء إدخال رقم صحيح')

        tk.Button(dialog, text='حفظ', command=save, bg='#27ae60', fg='white').pack(pady=20)

    def export_to_excel(self):
        """تصدير قائمة الزبائن مع آخر التحصيلات إلى Excel"""
        try:
            import pandas as pd
            from datetime import datetime

            data = []
            for item in self.tree.get_children():
                values = self.tree.item(item)['values']
                data.append({
                    'ID': values[0],
                    'الاسم': values[1],
                    'القطاع': values[2],
                    'الرصيد': float(values[3].replace(',', '')) if isinstance(values[3], str) else values[3],
                    'آخر تحصيل': values[4],
                    'المتوقع': values[5],
                    'الحالة': values[6]
                })

            df = pd.DataFrame(data)
            filename = f"mobile_collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(filename, index=False, engine='openpyxl')
            messagebox.showinfo('نجاح', f'تم التصدير إلى {filename}')
        except Exception as e:
            logger.error(f"خطأ في التصدير: {e}")
            messagebox.showerror('خطأ', f'فشل التصدير: {str(e)}')

    def load_collectors_list(self):
        """تحميل قائمة المحصلين للمدير"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id, full_name, username FROM users WHERE role = 'collector' AND is_active = TRUE")
                collectors = cursor.fetchall()
                self.collector_map = {f"{c['full_name']} ({c['username']})": c['id'] for c in collectors}
                self.collector_combo['values'] = list(self.collector_map.keys())
        except Exception as e:
            logger.error(f"خطأ في تحميل قائمة المحصلين: {e}")

    def on_collector_change(self, event):
        self.load_data()

    def update_status(self, message):
        self.status_bar.config(text=message)