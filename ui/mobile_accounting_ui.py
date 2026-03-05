# ui/mobile_accounting_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime, timedelta
import pandas as pd
import os

from modules.customers import CustomerManager
from modules.collection import CollectionManager
from database.connection import db

logger = logging.getLogger(__name__)

class MobileAccountingUI(tk.Frame):
    """واجهة المحاسبة الجوالة – لوحة تحكم المحصل والإدارة"""

    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.user_data = user_data
        self.customer_manager = CustomerManager()
        self.collection_manager = CollectionManager()

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
            tk.Label(toolbar, text='المحصل:', bg='#2c3e50', fg='white').pack(side='left', padx=(20,5))
            self.collector_var = tk.StringVar()
            self.collector_combo = ttk.Combobox(toolbar, textvariable=self.collector_var,
                                                 state='readonly', width=20)
            self.collector_combo.pack(side='left', padx=5)
            self.collector_combo.bind('<<ComboboxSelected>>', self.on_collector_change)
            self.load_collectors_list()

        content = tk.Frame(self)
        content.pack(fill='both', expand=True, padx=10, pady=10)

        # إحصائيات سريعة
        self.stats_frame = tk.LabelFrame(content, text='📊 إحصائيات سريعة', padx=10, pady=10)
        self.stats_frame.pack(fill='x', pady=(0,10))

        # قائمة الزبائن
        customers_frame = tk.LabelFrame(content, text='👥 الزبائن المخصصون', padx=10, pady=10)
        customers_frame.pack(fill='both', expand=True)

        # شريط أدوات القائمة
        cust_toolbar = tk.Frame(customers_frame)
        cust_toolbar.pack(fill='x', pady=(0,5))

        tk.Button(cust_toolbar, text='🔄 تحديث', command=self.load_data,
                  bg='#3498db', fg='white').pack(side='left', padx=2)
        tk.Button(cust_toolbar, text='📥 تصدير Excel', command=self.export_to_excel,
                  bg='#27ae60', fg='white').pack(side='left', padx=2)

        # Notebook للقطاعات
        self.sector_notebook = ttk.Notebook(customers_frame)
        self.sector_notebook.pack(fill='both', expand=True)

        # شريط الحالة
        self.status_bar = tk.Label(self, text='جاهز', bd=1, relief='sunken', anchor='w')
        self.status_bar.pack(side='bottom', fill='x')

    def load_data(self):
        collector_id = None
        if self.is_collector:
            collector_id = self.user_data.get('id')
        elif self.is_admin:
            selected = self.collector_var.get()
            if selected:
                collector_id = self.collector_map.get(selected)

        if not collector_id:
            self.update_status('يرجى اختيار محصل')
            return

        customers = self.customer_manager.get_customers_by_collector(collector_id)
        self.display_customers(customers, collector_id)
        self.update_stats(collector_id)

    def display_customers(self, customers, collector_id):
        # حذف التبويبات القديمة
        for tab in self.sector_notebook.tabs():
            self.sector_notebook.forget(tab)

        today = datetime.now().date()
        sectors_dict = {}
        for cust in customers:
            sector_name = cust.get('sector_name') or 'بدون قطاع'
            sectors_dict.setdefault(sector_name, []).append(cust)

        self.sector_trees = {}

        for sector_name in sorted(sectors_dict.keys()):
            cust_list = sectors_dict[sector_name]
            tab_frame = tk.Frame(self.sector_notebook)
            self.sector_notebook.add(tab_frame, text=sector_name)

            # إضافة عمودين جديدين: visa_balance و last_reading
            columns = ('id', 'box_number', 'name', 'balance', 'visa_balance', 'last_reading',
                       'last_collection', 'expected', 'status')
            tree = ttk.Treeview(tab_frame, columns=columns, show='headings', height=12)

            # تعريف رؤوس الأعمدة
            tree.heading('id', text='ID')
            tree.heading('box_number', text='رقم العلبة')
            tree.heading('name', text='الاسم')
            tree.heading('balance', text='الرصيد (ك.و)')
            tree.heading('visa_balance', text='رصيد التأشيرة')
            tree.heading('last_reading', text='آخر قراءة')
            tree.heading('last_collection', text='آخر تحصيل')
            tree.heading('expected', text='المتوقع اليوم')
            tree.heading('status', text='الحالة')

            # ضبط عرض الأعمدة
            tree.column('id', width=40, anchor='center')
            tree.column('box_number', width=70, anchor='center')
            tree.column('name', width=150)
            tree.column('balance', width=90, anchor='center')
            tree.column('visa_balance', width=90, anchor='center')
            tree.column('last_reading', width=80, anchor='center')
            tree.column('last_collection', width=130, anchor='center')
            tree.column('expected', width=90, anchor='center')
            tree.column('status', width=90, anchor='center')

            # شريط تمرير
            scrollbar = ttk.Scrollbar(tab_frame, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')

            for cust in cust_list:
                current_balance = cust.get('current_balance', 0)
                visa_balance = cust.get('visa_balance', 0)
                last_reading = cust.get('last_counter_reading', '')
                last_payment = self.collection_manager.get_last_payment(cust['id'])
                last_date = last_payment['payment_datetime'] if last_payment else None
                last_amount = last_payment['amount'] if last_payment else 0
                source = last_payment['source'] if last_payment else None

                # منطق الحالة
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

                last_display = 'لم يحصل'
                if last_date:
                    if source == 'invoice':
                        last_display = f"فاتورة {last_date.strftime('%Y-%m-%d')} ({last_amount:,.0f})"
                    else:
                        last_display = f"تحصيل {last_date.strftime('%Y-%m-%d')} ({last_amount:,.0f})"

                tree.insert('', 'end', values=(
                    cust['id'],
                    cust.get('box_number', ''),
                    cust['name'],
                    f"{current_balance:,.0f}",
                    f"{visa_balance:,.0f}",
                    last_reading,
                    last_display,
                    f"{current_balance:,.0f}",
                    status
                ), tags=(tag,))

            tree.tag_configure('settled', background='#ccffcc')
            tree.tag_configure('collected_today', background='#ccffcc')
            tree.tag_configure('recent', background='#ffffcc')
            tree.tag_configure('late', background='#ffcccc')

            tree.bind('<Double-1>', self.open_collection_dialog)
            self.sector_trees[sector_name] = tree

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

        # استخراج القيم مع التأكد من عدم وجود None
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
        tree = event.widget
        selection = tree.selection()
        if not selection:
            return
        item = tree.item(selection[0])
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
        """تصدير البيانات إلى Excel مع ورقة منفصلة لكل قطاع وورقة ملخص"""
        try:
            if not hasattr(self, 'sector_trees') or not self.sector_trees:
                messagebox.showwarning('تحذير', 'لا توجد بيانات للتصدير')
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mobile_collection_{timestamp}.xlsx"
            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)
            filepath = os.path.join(export_dir, filename)

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # بيانات الملخص
                summary_data = []
                grand_total_customers = 0
                grand_total_balance = 0.0

                for sector_name, tree in self.sector_trees.items():
                    customers = []
                    total_balance = 0.0
                    for item in tree.get_children():
                        values = tree.item(item)['values']
                        if len(values) >= 9:  # الآن 9 أعمدة
                            balance_str = values[3]
                            visa_str = values[4]
                            try:
                                balance = float(str(balance_str).replace(',', '').replace('ك.و', '').strip())
                            except:
                                balance = 0.0
                            try:
                                visa = float(str(visa_str).replace(',', '').replace('ك.و', '').strip())
                            except:
                                visa = 0.0
                            total_balance += balance
                            customers.append({
                                'id': values[0],
                                'box_number': values[1],
                                'name': values[2],
                                'balance': balance,
                                'visa_balance': visa,
                                'last_reading': values[5],
                                'last_collection': values[6],
                                'expected': values[7],
                                'status': values[8]
                            })

                    sector_info = {
                        'name': sector_name,
                        'customers': customers,
                        'total_customers': len(customers),
                        'total_balance': total_balance
                    }
                    summary_data.append(sector_info)
                    grand_total_customers += len(customers)
                    grand_total_balance += total_balance

                    # ورقة خاصة بالقطاع
                    if customers:
                        df_sector = pd.DataFrame(customers)
                        # ترتيب الأعمدة
                        df_sector = df_sector[['id', 'box_number', 'name', 'balance', 'visa_balance',
                                               'last_reading', 'last_collection', 'expected', 'status']]
                        df_sector.columns = ['المعرف', 'رقم العلبة', 'الاسم', 'الرصيد',
                                             'رصيد التأشيرة', 'آخر قراءة', 'آخر تحصيل', 'المتوقع', 'الحالة']

                        # إضافة صف إجمالي (يظهر فقط الرصيد الكلي)
                        total_row = pd.DataFrame([[
                            'إجمالي القطاع',
                            f"{len(customers)} زبون",
                            '',
                            f"{total_balance:,.0f}",
                            '',
                            '',
                            '',
                            '',
                            ''
                        ]], columns=df_sector.columns)
                        df_sector = pd.concat([df_sector, total_row], ignore_index=True)

                        sheet_name = sector_name[:31]
                        df_sector.to_excel(writer, sheet_name=sheet_name, index=False)

                # ورقة الملخص
                summary_rows = []
                for sec in summary_data:
                    summary_rows.append([
                        sec['name'],
                        sec['total_customers'],
                        f"{sec['total_balance']:,.0f}"
                    ])
                summary_rows.append(['الإجمالي العام', grand_total_customers, f"{grand_total_balance:,.0f}"])

                df_summary = pd.DataFrame(summary_rows, columns=['القطاع', 'عدد الزبائن', 'إجمالي الرصيد'])
                df_summary.to_excel(writer, sheet_name='ملخص القطاعات', index=False)

                # تنسيق عرض الأعمدة
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for col in worksheet.columns:
                        max_len = 0
                        col_letter = col[0].column_letter
                        for cell in col:
                            try:
                                if cell.value and len(str(cell.value)) > max_len:
                                    max_len = len(str(cell.value))
                            except:
                                pass
                        worksheet.column_dimensions[col_letter].width = min(max_len + 2, 50)

            messagebox.showinfo('نجاح', f'تم التصدير بنجاح إلى:\n{filepath}')
            self.update_status(f'تم التصدير إلى {filename}')
            try:
                os.startfile(filepath)
            except:
                pass

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