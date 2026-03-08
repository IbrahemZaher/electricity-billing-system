# ui/archive_ui.py
"""
واجهة الأرشيف المتقدمة - عرض السجل التاريخي الكامل للزبون مع تحليلات وتصدير
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from datetime import datetime, timedelta
import os
import webbrowser
import pandas as pd

from modules.history_manager import HistoryManager
from modules.customers import CustomerManager
from modules.collection_monitor import CollectionMonitor
from database.connection import db

logger = logging.getLogger(__name__)

class ArchiveUI(tk.Frame):
    """
    واجهة عرض السجل التاريخي للزبون - بحث، فلترة، تحليل، تصدير
    """

    def __init__(self, parent, user_data=None):
        super().__init__(parent)
        self.parent = parent
        self.user_data = user_data or {}
        self.history_manager = HistoryManager()
        self.customer_manager = CustomerManager()
        self.collection_monitor = CollectionMonitor()
        self.current_customer_id = None
        self.current_customer_name = ""
        self.history_data = []  # تخزين آخر سجل تم جلبه

        # إعدادات الألوان (انسجاماً مع باقي الواجهات)
        self.colors = {
            'bg_main': '#F5F7FA',
            'primary': '#2C3E50',
            'secondary': '#3498DB',
            'success': '#27AE60',
            'warning': '#F39C12',
            'danger': '#E74C3C',
            'info': '#9B59B6',
            'light': '#ECF0F1',
            'dark': '#2C3E50',
            'border': '#BDC3C7'
        }

        self.create_widgets()
        self.load_sectors()

    # ------------------------------------------------------------
    # بناء الواجهة
    # ------------------------------------------------------------
    def create_widgets(self):
        # إطار رئيسي
        main_frame = tk.Frame(self, bg=self.colors['bg_main'])
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # ========== شريط البحث ==========
        search_frame = tk.LabelFrame(main_frame, text="🔍 بحث عن زبون", font=('Arial', 12, 'bold'),
                                      bg=self.colors['bg_main'], fg=self.colors['dark'],
                                      padx=10, pady=10)
        search_frame.pack(fill='x', pady=(0, 10))

        # صف البحث
        row1 = tk.Frame(search_frame, bg=self.colors['bg_main'])
        row1.pack(fill='x', pady=5)

        tk.Label(row1, text="اسم الزبون / رقم العلبة / مسلسل / هاتف:",
                 font=('Arial', 11), bg=self.colors['bg_main']).pack(side='left', padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(row1, textvariable=self.search_var, font=('Arial', 11), width=40)
        self.search_entry.pack(side='left', padx=5)
        self.search_entry.bind('<KeyRelease>', self.on_search_typed)

        # صف الفلاتر الإضافية
        row2 = tk.Frame(search_frame, bg=self.colors['bg_main'])
        row2.pack(fill='x', pady=5)

        tk.Label(row2, text="القطاع:", font=('Arial', 11), bg=self.colors['bg_main']).pack(side='left', padx=5)
        self.sector_var = tk.StringVar()
        self.sector_combo = ttk.Combobox(row2, textvariable=self.sector_var, state='readonly', width=20)
        self.sector_combo.pack(side='left', padx=5)
        self.sector_combo.bind('<<ComboboxSelected>>', self.on_search_typed)

        # قائمة نتائج البحث
        self.results_listbox = tk.Listbox(search_frame, height=5, font=('Arial', 11),
                                           selectbackground=self.colors['secondary'], selectforeground='white')
        self.results_listbox.pack(fill='x', pady=5)
        self.results_listbox.bind('<<ListboxSelect>>', self.on_customer_selected)

        # ========== شريط الأدوات (للتاريخ) ==========
        toolbar = tk.Frame(main_frame, bg=self.colors['primary'], height=50)
        toolbar.pack(fill='x', pady=(0, 10))
        toolbar.pack_propagate(False)

        self.customer_label = tk.Label(toolbar, text="الزبون: --", font=('Arial', 12, 'bold'),
                                        bg=self.colors['primary'], fg='white')
        self.customer_label.pack(side='left', padx=20, pady=10)

        # فلترة التاريخ
        tk.Label(toolbar, text="من تاريخ:", font=('Arial', 10), bg=self.colors['primary'], fg='white').pack(side='left', padx=(20, 2))
        self.start_date = ttk.Entry(toolbar, width=12)
        self.start_date.pack(side='left', padx=2)
        self.start_date.insert(0, (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'))

        tk.Label(toolbar, text="إلى تاريخ:", font=('Arial', 10), bg=self.colors['primary'], fg='white').pack(side='left', padx=(10, 2))
        self.end_date = ttk.Entry(toolbar, width=12)
        self.end_date.pack(side='left', padx=2)
        self.end_date.insert(0, datetime.now().strftime('%Y-%m-%d'))

        # فلترة نوع العملية
        tk.Label(toolbar, text="نوع العملية:", font=('Arial', 10), bg=self.colors['primary'], fg='white').pack(side='left', padx=(20, 2))
        self.action_type_var = tk.StringVar()
        self.action_combo = ttk.Combobox(toolbar, textvariable=self.action_type_var, state='readonly', width=20)
        self.action_combo['values'] = ['الكل', 'تأشيرة', 'سحب', 'فاتورة', 'تعديل رصيد', 'تحديث بيانات', 'حذف']
        self.action_combo.pack(side='left', padx=2)
        self.action_combo.current(0)

        # أزرار التحكم
        btn_refresh = tk.Button(toolbar, text="🔄 تحديث", command=self.load_history,
                                 bg=self.colors['success'], fg='white', font=('Arial', 10, 'bold'),
                                 padx=10, cursor='hand2')
        btn_refresh.pack(side='right', padx=5)

        btn_export = tk.Button(toolbar, text="📥 تصدير Excel", command=self.export_history,
                                bg=self.colors['info'], fg='white', font=('Arial', 10, 'bold'),
                                padx=10, cursor='hand2')
        btn_export.pack(side='right', padx=5)

        # ========== عرض السجل التاريخي (شجرة مع تمرير) ==========
        tree_container = tk.Frame(main_frame, bg='white')
        tree_container.pack(fill='both', expand=True)

        # شريط تمرير عمودي
        v_scroll = ttk.Scrollbar(tree_container, orient='vertical')
        v_scroll.pack(side='right', fill='y')

        # شريط تمرير أفقي
        h_scroll = ttk.Scrollbar(tree_container, orient='horizontal')
        h_scroll.pack(side='bottom', fill='x')

        # الأعمدة: التاريخ، نوع العملية، الحقل المتغير، القيمة القديمة، الجديدة، المبلغ، الرصيد بعد، المستخدم، ملاحظات، السحب، التأشيرة، آخر قراءة
        columns = ('date', 'action_type', 'field', 'old_val', 'new_val', 'amount',
                   'balance_after', 'user', 'notes', 'withdrawal', 'visa', 'last_reading')
        self.tree = ttk.Treeview(tree_container, columns=columns,
                                  yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set,
                                  selectmode='browse', height=20)
        v_scroll.config(command=self.tree.yview)
        h_scroll.config(command=self.tree.xview)

        # تعريف الرؤوس
        self.tree.heading('#0', text='#')
        self.tree.column('#0', width=40, anchor='center')
        self.tree.heading('date', text='التاريخ والوقت')
        self.tree.column('date', width=150, anchor='center')
        self.tree.heading('action_type', text='نوع العملية')
        self.tree.column('action_type', width=120, anchor='center')
        self.tree.heading('field', text='الحقل المتغير')
        self.tree.column('field', width=150, anchor='center')
        self.tree.heading('old_val', text='القيمة القديمة')
        self.tree.column('old_val', width=120, anchor='center')
        self.tree.heading('new_val', text='القيمة الجديدة')
        self.tree.column('new_val', width=120, anchor='center')
        self.tree.heading('amount', text='المبلغ (ك.و)')
        self.tree.column('amount', width=100, anchor='center')
        self.tree.heading('balance_after', text='الرصيد بعد')
        self.tree.column('balance_after', width=120, anchor='center')
        self.tree.heading('user', text='المستخدم')
        self.tree.column('user', width=150, anchor='center')
        self.tree.heading('notes', text='ملاحظات')
        self.tree.column('notes', width=200, anchor='w')
        self.tree.heading('withdrawal', text='السحب (ك.و)')
        self.tree.column('withdrawal', width=100, anchor='center')
        self.tree.heading('visa', text='رصيد التأشيرة')
        self.tree.column('visa', width=120, anchor='center')
        self.tree.heading('last_reading', text='آخر قراءة')
        self.tree.column('last_reading', width=100, anchor='center')

        self.tree.pack(side='left', fill='both', expand=True)

        # ========== شريط الإحصائيات ==========
        self.stats_frame = tk.LabelFrame(main_frame, text="📊 إحصائيات الزبون", font=('Arial', 11, 'bold'),
                                          bg=self.colors['bg_main'], fg=self.colors['dark'],
                                          padx=10, pady=5)
        self.stats_frame.pack(fill='x', pady=(10, 0))

        self.stats_label = tk.Label(self.stats_frame, text="", font=('Arial', 10),
                                     bg=self.colors['bg_main'], fg=self.colors['dark'], anchor='w')
        self.stats_label.pack(fill='x')

        # ========== شريط الحالة ==========
        self.status_bar = tk.Label(self, text="جاهز", bd=1, relief='sunken', anchor='w',
                                    bg=self.colors['light'], fg=self.colors['dark'])
        self.status_bar.pack(side='bottom', fill='x')

    # ------------------------------------------------------------
    # تحميل القطاعات للبحث
    # ------------------------------------------------------------
    def load_sectors(self):
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id, name FROM sectors WHERE is_active = TRUE ORDER BY name")
                sectors = cursor.fetchall()
                sector_names = ['الكل'] + [s['name'] for s in sectors]
                self.sector_combo['values'] = sector_names
                self.sector_combo.current(0)
        except Exception as e:
            logger.error(f"خطأ في تحميل القطاعات: {e}")

    # ------------------------------------------------------------
    # البحث عن الزبون (مع debounce)
    # ------------------------------------------------------------
    def on_search_typed(self, event=None):
        search_term = self.search_var.get().strip()
        if len(search_term) < 2:
            self.results_listbox.delete(0, tk.END)
            return
        # debounce
        if hasattr(self, '_search_job'):
            self.after_cancel(self._search_job)
        self._search_job = self.after(400, self.perform_search, search_term)

    def perform_search(self, search_term):
        try:
            # استخدام البحث السريع من CustomerManager
            customers = self.customer_manager.search_customers(search_term)
            self.results_listbox.delete(0, tk.END)
            self.search_results = customers
            for cust in customers:
                display = f"{cust['id']} | {cust['name']} | علبة: {cust.get('box_number','')} | {cust.get('sector_name','')}"
                self.results_listbox.insert(tk.END, display)
        except Exception as e:
            logger.error(f"خطأ في البحث: {e}")

    # ------------------------------------------------------------
    # اختيار زبون من القائمة
    # ------------------------------------------------------------
    def on_customer_selected(self, event):
        selection = self.results_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        customer = self.search_results[idx]
        self.current_customer_id = customer['id']
        self.current_customer_name = customer['name']
        self.customer_label.config(text=f"الزبون: {customer['name']} (ID: {customer['id']})")
        self.load_history()

    # ------------------------------------------------------------
    # تحميل السجل التاريخي للزبون المحدد مع تطبيق الفلاتر
    # ------------------------------------------------------------
    def load_history(self):
        if not self.current_customer_id:
            messagebox.showwarning("تحذير", "يرجى اختيار زبون أولاً")
            return

        # جمع معايير الفلترة
        filters = {}
        start = self.start_date.get().strip()
        end = self.end_date.get().strip()
        if start:
            filters['start_date'] = start
        if end:
            filters['end_date'] = end

        action_filter = self.action_type_var.get()
        if action_filter != 'الكل':
            # ترجمة النص إلى أنواع العمليات المتوقعة في قاعدة البيانات
            action_map = {
                'تأشيرة': ['weekly_visa', 'visa_update', 'visa_adjustment'],
                'سحب': ['cash_withdrawal', 'withdrawal_adjustment'],
                'فاتورة': ['invoice_created', 'invoice_updated', 'invoice_cancelled', 'invoice_deleted'],
                'تعديل رصيد': ['balance_adjustment'],
                'تحديث بيانات': ['customer_update', 'info_update'],
                'حذف': ['delete_customer', 'soft_delete', 'hard_delete', 'bulk_delete', 'sector_delete']
            }
            filters['action_types'] = action_map.get(action_filter, [])

        try:
            # جلب التاريخ من HistoryManager
            result = self.history_manager.get_customer_history(
                customer_id=self.current_customer_id,
                limit=10000  # عدد كبير لجلب كل السجلات
            )
            if not result.get('success'):
                self.show_error(result.get('error', 'خطأ في جلب البيانات'))
                return

            records = result.get('history', [])
            self.history_data = records

            # تطبيق الفلاتر يدوياً (لأن HistoryManager قد لا يدعمها مباشرة)
            filtered = []
            for rec in records:
                # فلترة التاريخ
                if start:
                    try:
                        rec_date = datetime.strptime(rec['created_at_formatted'], '%Y-%m-%d %H:%M')
                        if rec_date < datetime.strptime(start, '%Y-%m-%d'):
                            continue
                    except:
                        pass
                if end:
                    try:
                        rec_date = datetime.strptime(rec['created_at_formatted'], '%Y-%m-%d %H:%M')
                        if rec_date > datetime.strptime(end, '%Y-%m-%d') + timedelta(days=1):
                            continue
                    except:
                        pass
                # فلترة نوع العملية
                if action_filter != 'الكل' and rec['transaction_type'] not in filters.get('action_types', []):
                    continue
                filtered.append(rec)

            # عرض البيانات في الشجرة
            self.display_history(filtered)

            # تحديث الإحصائيات
            self.update_statistics(filtered)

            self.status_bar.config(text=f"✅ تم تحميل {len(filtered)} سجل للزبون {self.current_customer_name}")

        except Exception as e:
            logger.error(f"خطأ في تحميل التاريخ: {e}", exc_info=True)
            self.show_error(f"فشل تحميل التاريخ: {str(e)}")

    # ------------------------------------------------------------
    # عرض السجلات في الشجرة
    # ------------------------------------------------------------
    def display_history(self, records):
        # مسح الشجرة
        for item in self.tree.get_children():
            self.tree.delete(item)

        for idx, rec in enumerate(records, 1):
            # تحديد الحقل المتغير بناءً على نوع العملية
            field = self.get_changed_field(rec)
            old_val = self.format_value(rec.get('old_value'))
            new_val = self.format_value(rec.get('new_value'))
            amount = self.format_value(rec.get('amount'))
            balance_after = self.format_value(rec.get('current_balance_after'))
            user = rec.get('created_by_name') or 'نظام'
            notes = rec.get('notes', '')
            action_arabic = rec.get('transaction_type_arabic', rec['transaction_type'])

            values = (
                rec['created_at_formatted'],
                action_arabic,
                field,
                old_val,
                new_val,
                amount,
                balance_after,
                user,
                notes,
                self.format_value(rec.get('snapshot_withdrawal_amount')),
                self.format_value(rec.get('snapshot_visa_balance')),
                self.format_value(rec.get('snapshot_last_counter_reading'))
            )
            self.tree.insert('', 'end', text=str(idx), values=values)

    def get_changed_field(self, record):
        """تحديد الحقل الذي تم تغييره من نوع العملية"""
        ttype = record['transaction_type']
        if ttype in ('weekly_visa', 'visa_update', 'visa_adjustment'):
            return 'رصيد التأشيرة'
        elif ttype in ('cash_withdrawal', 'withdrawal_adjustment'):
            return 'مبلغ السحب'
        elif ttype in ('invoice_created', 'invoice_updated'):
            return 'فاتورة'
        elif ttype == 'counter_reading':
            return 'قراءة العداد'
        elif ttype in ('balance_adjustment', 'manual_adjustment'):
            return 'الرصيد الحالي'
        elif ttype in ('customer_update', 'info_update'):
            return 'بيانات الزبون'
        elif ttype in ('delete_customer', 'soft_delete', 'hard_delete', 'bulk_delete', 'sector_delete'):
            return 'حذف الزبون'
        else:
            return '--'

    def format_value(self, val):
        if val is None:
            return '--'
        try:
            if isinstance(val, float) or (isinstance(val, str) and val.replace('.','',1).isdigit()):
                return f"{float(val):,.0f}"
        except:
            pass
        return str(val)

    # ------------------------------------------------------------
    # إحصائيات السجل
    # ------------------------------------------------------------
    def update_statistics(self, records):
        total_records = len(records)
        total_additions = 0.0
        total_withdrawals = 0.0
        total_visa = 0.0
        net_change = 0.0

        for rec in records:
            amount = rec.get('amount') or 0.0
            ttype = rec['transaction_type']
            if ttype in ('weekly_visa', 'visa_update', 'visa_adjustment'):
                total_visa += amount
                if amount > 0:
                    total_additions += amount
                else:
                    total_withdrawals += abs(amount)
            elif ttype in ('cash_withdrawal', 'withdrawal_adjustment'):
                total_withdrawals += amount
                if amount < 0:
                    total_additions += abs(amount)
                else:
                    total_withdrawals += amount
            elif ttype in ('invoice_created', 'invoice_updated'):
                # الفاتورة تزيد الرصيد (عادةً) حسب المنطق
                total_additions += amount
            elif ttype in ('balance_adjustment', 'manual_adjustment'):
                if amount > 0:
                    total_additions += amount
                else:
                    total_withdrawals += abs(amount)
            net_change += amount

        # تصنيف السحب باستخدام CollectionMonitor إذا أمكن
        withdrawal_class = 'غير معروف'
        if self.current_customer_id:
            # نأخذ آخر سحب للزبون من جدول customers
            try:
                cust = self.customer_manager.get_customer(self.current_customer_id)
                if cust:
                    last_visa = self.collection_monitor.get_last_visa_date(self.current_customer_id)
                    withdrawal_class = self.collection_monitor.get_withdrawal_classification(
                        cust.get('withdrawal_amount', 0), last_visa)
            except:
                pass

        stats_text = (
            f"إجمالي العمليات: {total_records}  |  "
            f"إجمالي الإضافات: {total_additions:,.0f} ك.و  |  "
            f"إجمالي السحوبات: {total_withdrawals:,.0f} ك.و  |  "
            f"صافي التغيير: {net_change:,.0f} ك.و  |  "
            f"إجمالي التأشيرات المضافة: {total_visa:,.0f} ك.و  |  "
            f"تصنيف السحب: {withdrawal_class}"
        )
        self.stats_label.config(text=stats_text)

    # ------------------------------------------------------------
    # تصدير إلى Excel
    # ------------------------------------------------------------
    def export_history(self):
        if not self.history_data:
            messagebox.showwarning("تحذير", "لا توجد بيانات للتصدير")
            return

        # إنشاء مجلد exports إذا لم يكن موجوداً
        export_dir = "exports"
        os.makedirs(export_dir, exist_ok=True)

        # توليد اسم الملف تلقائياً (بدون طلب من المستخدم)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"history_{self.current_customer_name}_{timestamp}.xlsx"
        filepath = os.path.join(export_dir, filename)

        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # صفحة الملخص
                summary_data = {
                    'اسم الزبون': self.current_customer_name,
                    'معرف الزبون': self.current_customer_id,
                    'تاريخ التصدير': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'عدد السجلات': len(self.history_data),
                }
                summary_df = pd.DataFrame([summary_data])
                summary_df.to_excel(writer, sheet_name='ملخص', index=False)

                # صفحة التفاصيل
                rows = []
                for rec in self.history_data:
                    row = {
                        'التاريخ': rec.get('created_at_formatted', ''),
                        'نوع العملية': rec.get('transaction_type_arabic', rec['transaction_type']),
                        'الحقل المتغير': self.get_changed_field(rec),
                        'القيمة القديمة': self.format_value(rec.get('old_value')),
                        'القيمة الجديدة': self.format_value(rec.get('new_value')),
                        'المبلغ (ك.و)': self.format_value(rec.get('amount')),
                        'الرصيد بعد العملية': self.format_value(rec.get('current_balance_after')),
                        'السحب (ك.و)': self.format_value(rec.get('snapshot_withdrawal_amount')),
                        'رصيد التأشيرة': self.format_value(rec.get('snapshot_visa_balance')),
                        'آخر قراءة': self.format_value(rec.get('snapshot_last_counter_reading')),
                        'المستخدم': rec.get('created_by_name', 'نظام'),
                        'ملاحظات': rec.get('notes', '')
                    }
                    rows.append(row)
                df = pd.DataFrame(rows)
                df.to_excel(writer, sheet_name='السجل التاريخي', index=False)

                # ضبط عرض الأعمدة
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
            self.status_bar.config(text=f'تم التصدير إلى {filename}')

            # فتح الملف تلقائياً
            try:
                if os.name == 'nt':
                    os.startfile(filepath)
                else:
                    webbrowser.open(filepath)
            except Exception as e:
                logger.error(f"خطأ في فتح الملف: {e}")

        except ImportError:
            messagebox.showerror('خطأ', 'مكتبة pandas غير مثبتة')
        except Exception as e:
            logger.error(f"خطأ في التصدير: {e}", exc_info=True)
            messagebox.showerror('خطأ', f'فشل التصدير: {str(e)}')

    # ------------------------------------------------------------
    # دوال مساعدة
    # ------------------------------------------------------------
    def show_error(self, message):
        self.status_bar.config(text=f"❌ {message}")
        messagebox.showerror("خطأ", message)