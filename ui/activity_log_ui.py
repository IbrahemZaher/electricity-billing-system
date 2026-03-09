# ui/activity_log_ui.py
"""
واجهة السجل التاريخي للعمليات - لكل محاسب على حدة (مشتقة من customer_history)
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from datetime import datetime, timedelta
import os
import webbrowser
import pandas as pd

from database.connection import db
from auth.session import Session

logger = logging.getLogger(__name__)

class ActivityLogUI(tk.Frame):
    """
    واجهة عرض السجل التاريخي للعمليات التي قام بها محاسب معين
    (بناءً على جدول customer_history مع الربط بـ users)
    """

    def __init__(self, parent, user_data=None):
        super().__init__(parent)
        self.parent = parent
        self.user_data = user_data or {}
        self.current_user_id = None
        self.current_user_name = ""
        self.history_data = []  # تخزين آخر سجل تم جلبه

        # إعدادات الألوان (مطابقة لـ ArchiveUI)
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

        # ترجمة أنواع العمليات (من customer_history.transaction_type)
        self.transaction_type_map = {
            'weekly_visa': 'تأشيرة أسبوعية',
            'cash_withdrawal': 'سحب نقدي',
            'counter_reading': 'قراءة عداد',
            'discount': 'حسم',
            'balance_adjustment': 'تعديل رصيد',
            'visa_adjustment': 'تعديل تأشيرة',
            'initial_balance': 'رصيد ابتدائي',
            'manual_adjustment': 'تعديل يدوي',
            'customer_update': 'تحديث بيانات الزبون',
            'new_customer': 'زبون جديد',
            'delete_customer': 'حذف الزبون',
            'info_update': 'تحديث معلومات',
            'soft_delete': 'حذف ناعم',
            'hard_delete': 'حذف فعلي',
            'bulk_delete': 'حذف جماعي',
            'sector_delete': 'حذف قطاعي',
            'invoice_created': 'إنشاء فاتورة',
            'invoice_updated': 'تعديل فاتورة',
            'invoice_cancelled': 'إلغاء فاتورة',
            'invoice_deleted': 'حذف فاتورة',
            'payment': 'دفع',
            'refund': 'استرداد',
            'adjustment': 'تسوية',
            'parent_change': 'تغيير العلبة الأم',
            'parent_removed': 'إزالة العلبة الأم',
            'child_update': 'تحديث ابن',
        }

        self.create_widgets()
        self.load_users_list()          # تحميل قائمة المحاسبين
        self.load_transaction_types()   # تحميل أنواع العمليات الفريدة من customer_history

    # ------------------------------------------------------------
    # بناء الواجهة
    # ------------------------------------------------------------
    def create_widgets(self):
        # إطار رئيسي
        main_frame = tk.Frame(self, bg=self.colors['bg_main'])
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # ========== شريط اختيار المحاسب ==========
        search_frame = tk.LabelFrame(main_frame, text="🔍 اختيار محاسب", font=('Arial', 12, 'bold'),
                                      bg=self.colors['bg_main'], fg=self.colors['dark'],
                                      padx=10, pady=10)
        search_frame.pack(fill='x', pady=(0, 10))

        # صف الاختيار
        row1 = tk.Frame(search_frame, bg=self.colors['bg_main'])
        row1.pack(fill='x', pady=5)

        tk.Label(row1, text="اختر المحاسب:", font=('Arial', 11), bg=self.colors['bg_main']).pack(side='left', padx=5)
        self.user_var = tk.StringVar()
        self.user_combo = ttk.Combobox(row1, textvariable=self.user_var, state='readonly', width=40)
        self.user_combo.pack(side='left', padx=5)
        self.user_combo.bind('<<ComboboxSelected>>', self.on_user_selected)

        # ========== شريط الأدوات (للتاريخ والفلترة) ==========
        toolbar = tk.Frame(main_frame, bg=self.colors['primary'], height=50)
        toolbar.pack(fill='x', pady=(0, 10))
        toolbar.pack_propagate(False)

        self.user_label = tk.Label(toolbar, text="المحاسب: --", font=('Arial', 12, 'bold'),
                                    bg=self.colors['primary'], fg='white')
        self.user_label.pack(side='left', padx=20, pady=10)

        # فلترة التاريخ
        tk.Label(toolbar, text="من تاريخ:", font=('Arial', 10), bg=self.colors['primary'], fg='white').pack(side='left', padx=(20, 2))
        self.start_date = ttk.Entry(toolbar, width=12)
        self.start_date.pack(side='left', padx=2)
        self.start_date.insert(0, (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))

        tk.Label(toolbar, text="إلى تاريخ:", font=('Arial', 10), bg=self.colors['primary'], fg='white').pack(side='left', padx=(10, 2))
        self.end_date = ttk.Entry(toolbar, width=12)
        self.end_date.pack(side='left', padx=2)
        self.end_date.insert(0, datetime.now().strftime('%Y-%m-%d'))

        # فلترة نوع العملية
        tk.Label(toolbar, text="نوع العملية:", font=('Arial', 10), bg=self.colors['primary'], fg='white').pack(side='left', padx=(20, 2))
        self.transaction_var = tk.StringVar()
        self.transaction_combo = ttk.Combobox(toolbar, textvariable=self.transaction_var, state='readonly', width=20)
        self.transaction_combo.pack(side='left', padx=2)
        self.transaction_combo.bind('<<ComboboxSelected>>', self.on_filter_changed)

        # أزرار التحكم
        btn_refresh = tk.Button(toolbar, text="🔄 تحديث", command=self.load_history,
                                 bg=self.colors['success'], fg='white', font=('Arial', 10, 'bold'),
                                 padx=10, cursor='hand2')
        btn_refresh.pack(side='right', padx=5)

        btn_export = tk.Button(toolbar, text="📥 تصدير Excel", command=self.export_history,
                                bg=self.colors['info'], fg='white', font=('Arial', 10, 'bold'),
                                padx=10, cursor='hand2')
        btn_export.pack(side='right', padx=5)

        # ========== عرض السجلات (شجرة مع تمرير) ==========
        tree_container = tk.Frame(main_frame, bg='white')
        tree_container.pack(fill='both', expand=True)

        # شريط تمرير عمودي
        v_scroll = ttk.Scrollbar(tree_container, orient='vertical')
        v_scroll.pack(side='right', fill='y')

        # شريط تمرير أفقي
        h_scroll = ttk.Scrollbar(tree_container, orient='horizontal')
        h_scroll.pack(side='bottom', fill='x')

        # الأعمدة (مشابهة لـ ArchiveUI ولكن بدون عمود المستخدم لأنه معروف)
        columns = ('id', 'date', 'customer', 'action', 'old_val', 'new_val', 'amount', 'balance', 'notes')
        self.tree = ttk.Treeview(tree_container, columns=columns,
                                  yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set,
                                  selectmode='browse', height=20)
        v_scroll.config(command=self.tree.yview)
        h_scroll.config(command=self.tree.xview)

        # تعريف الرؤوس
        self.tree.heading('#0', text='#')
        self.tree.column('#0', width=40, anchor='center')
        self.tree.heading('id', text='ID')
        self.tree.column('id', width=50, anchor='center')
        self.tree.heading('date', text='التاريخ والوقت')
        self.tree.column('date', width=150, anchor='center')
        self.tree.heading('customer', text='الزبون')
        self.tree.column('customer', width=200, anchor='w')
        self.tree.heading('action', text='نوع العملية')
        self.tree.column('action', width=150, anchor='center')
        self.tree.heading('old_val', text='القيمة القديمة')
        self.tree.column('old_val', width=100, anchor='center')
        self.tree.heading('new_val', text='القيمة الجديدة')
        self.tree.column('new_val', width=100, anchor='center')
        self.tree.heading('amount', text='المبلغ (ك.و)')
        self.tree.column('amount', width=100, anchor='center')
        self.tree.heading('balance', text='الرصيد بعد')
        self.tree.column('balance', width=100, anchor='center')
        self.tree.heading('notes', text='ملاحظات')
        self.tree.column('notes', width=250, anchor='w')

        self.tree.pack(side='left', fill='both', expand=True)

        # ربط النقر المزدوج لعرض التفاصيل (يمكن إضافته لاحقاً)
        # self.tree.bind('<Double-1>', self.on_double_click)

        # ========== شريط الإحصائيات ==========
        self.stats_frame = tk.LabelFrame(main_frame, text="📊 إحصائيات المحاسب", font=('Arial', 11, 'bold'),
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
    # تحميل قائمة المحاسبين (users)
    # ------------------------------------------------------------
    def load_users_list(self):
        """تحميل قائمة المستخدمين (المحاسبين) النشطين"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id, username, full_name FROM users WHERE is_active = TRUE ORDER BY full_name")
                users = cursor.fetchall()
                user_list = []
                self.user_map = {}
                for u in users:
                    display = f"{u['id']} - {u['full_name']} ({u['username']})"
                    user_list.append(display)
                    self.user_map[display] = u['id']
                self.user_combo['values'] = user_list
        except Exception as e:
            logger.error(f"خطأ في تحميل قائمة المستخدمين: {e}")
            self.user_map = {}

    # ------------------------------------------------------------
    # تحميل أنواع العمليات الفريدة من customer_history
    # ------------------------------------------------------------
    def load_transaction_types(self):
        """جلب قائمة transaction_type الفريدة من customer_history"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT DISTINCT transaction_type FROM customer_history ORDER BY transaction_type")
                rows = cursor.fetchall()
                # نأخذ القيم الفعلية (الإنجليزية) ولكن نعرضها مترجمة إذا أمكن
                raw_types = [r['transaction_type'] for r in rows if r['transaction_type']]
                # إضافة 'الكل' في البداية
                display_types = ['الكل'] + [self.transaction_type_map.get(t, t) for t in raw_types]
                # نحتاج للاحتفاظ بالخريطة العكسية للفلترة
                self.display_to_raw = {'الكل': None}
                for raw, disp in zip(raw_types, display_types[1:]):
                    self.display_to_raw[disp] = raw
                self.transaction_combo['values'] = display_types
                self.transaction_combo.current(0)
        except Exception as e:
            logger.error(f"خطأ في تحميل أنواع العمليات: {e}")
            self.transaction_combo['values'] = ['الكل']
            self.transaction_combo.current(0)
            self.display_to_raw = {'الكل': None}

    # ------------------------------------------------------------
    # اختيار محاسب
    # ------------------------------------------------------------
    def on_user_selected(self, event=None):
        selected = self.user_var.get()
        if not selected:
            return
        user_id = self.user_map.get(selected)
        if not user_id:
            return
        self.current_user_id = user_id
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT full_name, username FROM users WHERE id = %s", (user_id,))
                u = cursor.fetchone()
                self.current_user_name = u['full_name'] or u['username']
        except Exception as e:
            logger.error(f"خطأ في جلب اسم المستخدم: {e}")
            self.current_user_name = "مستخدم"
        self.user_label.config(text=f"المحاسب: {self.current_user_name} (ID: {user_id})")
        self.load_history()

    # ------------------------------------------------------------
    # حدث تغيير الفلتر
    # ------------------------------------------------------------
    def on_filter_changed(self, event=None):
        self.load_history()

    # ------------------------------------------------------------
    # تحميل السجل التاريخي للمحاسب المحدد
    # ------------------------------------------------------------
    def load_history(self):
        if not self.current_user_id:
            messagebox.showwarning("تحذير", "يرجى اختيار محاسب أولاً")
            return

        # جمع شروط الفلترة
        conditions = ["h.created_by = %s"]
        params = [self.current_user_id]

        # فلترة التاريخ
        start = self.start_date.get().strip()
        if start:
            conditions.append("DATE(h.created_at) >= %s")
            params.append(start)

        end = self.end_date.get().strip()
        if end:
            conditions.append("DATE(h.created_at) <= %s")
            params.append(end)

        # فلترة نوع العملية
        selected_disp = self.transaction_var.get()
        if selected_disp and selected_disp != 'الكل':
            raw_type = self.display_to_raw.get(selected_disp)
            if raw_type:
                conditions.append("h.transaction_type = %s")
                params.append(raw_type)

        # بناء الاستعلام مع ربط بيانات الزبون
        query = f"""
            SELECT
                h.id,
                h.transaction_type,
                h.old_value,
                h.new_value,
                h.amount,
                h.current_balance_after,
                h.notes,
                h.created_at,
                c.name as customer_name,
                c.id as customer_id
            FROM customer_history h
            LEFT JOIN customers c ON h.customer_id = c.id
            WHERE {' AND '.join(conditions)}
            ORDER BY h.created_at DESC
            LIMIT 10000
        """

        try:
            with db.get_cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

            self.history_data = rows
            self.display_history(rows)
            self.update_statistics(rows)

            self.status_bar.config(text=f"✅ تم تحميل {len(rows)} سجل للمحاسب {self.current_user_name}")

        except Exception as e:
            logger.error(f"خطأ في تحميل السجل: {e}", exc_info=True)
            self.show_error(f"فشل تحميل البيانات: {str(e)}")

    # ------------------------------------------------------------
    # عرض السجلات في الشجرة
    # ------------------------------------------------------------
    def display_history(self, records):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for rec in records:
            action_disp = self.transaction_type_map.get(rec['transaction_type'], rec['transaction_type'])
            created_at = rec['created_at']
            if isinstance(created_at, datetime):
                timestamp = created_at.strftime('%Y-%m-%d %H:%M:%S')
            else:
                timestamp = str(created_at)

            # تنسيق القيم الرقمية
            old_val = self.format_number(rec['old_value'])
            new_val = self.format_number(rec['new_value'])
            amount = self.format_number(rec['amount'])
            balance = self.format_number(rec['current_balance_after'])

            values = (
                rec['id'],
                timestamp,
                rec['customer_name'] or f"زبون {rec['customer_id']}",
                action_disp,
                old_val,
                new_val,
                amount,
                balance,
                rec['notes'] or ''
            )
            self.tree.insert('', 'end', text=rec['id'], values=values)

    def format_number(self, val):
        if val is None:
            return '--'
        try:
            return f"{float(val):,.0f}"
        except:
            return str(val)

    # ------------------------------------------------------------
    # إحصائيات المحاسب
    # ------------------------------------------------------------
    def update_statistics(self, records):
        total = len(records)
        action_counts = {}
        for rec in records:
            act = self.transaction_type_map.get(rec['transaction_type'], rec['transaction_type'])
            action_counts[act] = action_counts.get(act, 0) + 1

        top_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        top_str = ', '.join([f"{a}({c})" for a, c in top_actions])

        latest = records[0]['created_at'] if records else None
        latest_str = latest.strftime('%Y-%m-%d %H:%M') if isinstance(latest, datetime) else 'لا يوجد'

        stats_text = f"إجمالي السجلات: {total}  |  آخر نشاط: {latest_str}  |  أكثر العمليات: {top_str}"
        self.stats_label.config(text=stats_text)

    # ------------------------------------------------------------
    # تصدير إلى Excel
    # ------------------------------------------------------------
    def export_history(self):
        if not self.history_data:
            messagebox.showwarning("تحذير", "لا توجد بيانات للتصدير")
            return

        export_dir = "exports"
        os.makedirs(export_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = self.current_user_name.replace(' ', '_')
        filename = f"history_{safe_name}_{timestamp}.xlsx"
        filepath = os.path.join(export_dir, filename)

        try:
            rows = []
            for rec in self.history_data:
                rows.append({
                    'رقم السجل': rec['id'],
                    'التاريخ': rec['created_at'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(rec['created_at'], datetime) else rec['created_at'],
                    'الزبون': rec['customer_name'] or f"زبون {rec['customer_id']}",
                    'نوع العملية': self.transaction_type_map.get(rec['transaction_type'], rec['transaction_type']),
                    'القيمة القديمة': self.format_number(rec['old_value']),
                    'القيمة الجديدة': self.format_number(rec['new_value']),
                    'المبلغ': self.format_number(rec['amount']),
                    'الرصيد بعد': self.format_number(rec['current_balance_after']),
                    'ملاحظات': rec['notes'] or '',
                })

            df = pd.DataFrame(rows)
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='السجل التاريخي', index=False)

                worksheet = writer.sheets['السجل التاريخي']
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

            messagebox.showinfo('نجاح', f'تم تصدير {len(rows)} سجل بنجاح إلى:\n{filepath}')
            self.status_bar.config(text=f'تم التصدير إلى {filename}')
            try:
                if os.name == 'nt':
                    os.startfile(filepath)
                else:
                    webbrowser.open(filepath)
            except:
                pass

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