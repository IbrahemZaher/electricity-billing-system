"""
ui/collection_monitor_ui.py
واجهة متابعة الجباية وتصنيف المتأخرين مع إضافة عمود التصنيف المالي وفلترته
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from datetime import datetime
import os
import webbrowser
import pandas as pd

from modules.collection_monitor import CollectionMonitor
from database.connection import db

logger = logging.getLogger(__name__)

class CollectionMonitorUI(tk.Frame):
    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.user_data = user_data
        self.monitor = CollectionMonitor()
        self.sectors = []
        self.financial_categories = []  # قائمة بأكواد التصنيفات المالية
        self.sector_trees = {}
        self.create_widgets()
        self.load_sectors()
        self.load_financial_categories()
        self.refresh_data()

    def load_financial_categories(self):
        """تحميل قائمة التصنيفات المالية المتاحة (من قاعدة البيانات أو من الخريطة)"""
        # يمكن جلبها من قاعدة البيانات، لكننا نستخدم الخريطة الموجودة في الكلاس
        self.financial_categories = list(self.monitor.financial_category_map.keys())
        # إضافة "الكل" في البداية
        names = ['الكل'] + [self.monitor.financial_category_map.get(code, code) for code in self.financial_categories]
        self.financial_combo['values'] = names
        self.financial_combo.current(0)

    def create_widgets(self):
        # شريط الأدوات العلوي
        toolbar = tk.Frame(self, bg='#2c3e50', height=50)
        toolbar.pack(fill='x')
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text='📊 متابعة الجباية وتصنيف المتأخرين',
                 font=('Arial', 14, 'bold'), bg='#2c3e50', fg='white').pack(side='left', padx=20)

        # فلترة بالقطاع
        tk.Label(toolbar, text='القطاع:', bg='#2c3e50', fg='white').pack(side='left', padx=(20,5))
        self.sector_var = tk.StringVar(value='الكل')
        self.sector_combo = ttk.Combobox(toolbar, textvariable=self.sector_var,
                                          state='readonly', width=20)
        self.sector_combo.pack(side='left', padx=5)
        self.sector_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_data())

        # فلترة بالتصنيف المالي
        tk.Label(toolbar, text='التصنيف المالي:', bg='#2c3e50', fg='white').pack(side='left', padx=(20,5))
        self.financial_var = tk.StringVar(value='الكل')
        self.financial_combo = ttk.Combobox(toolbar, textvariable=self.financial_var,
                                             state='readonly', width=20)
        self.financial_combo.pack(side='left', padx=5)
        self.financial_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_data())

        # زر تحديث
        tk.Button(toolbar, text='🔄 تحديث', command=self.refresh_data,
                  bg='#3498db', fg='white').pack(side='left', padx=5)

        # زر تصدير
        tk.Button(toolbar, text='📥 تصدير Excel', command=self.export_to_excel,
                  bg='#27ae60', fg='white').pack(side='left', padx=5)

        # إطار المحتوى الرئيسي
        main_frame = tk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # إطار ملخص سريع
        self.summary_frame = tk.LabelFrame(main_frame, text='📋 ملخص سريع', padx=10, pady=10)
        self.summary_frame.pack(fill='x', pady=(0,10))

        self.summary_label = tk.Label(self.summary_frame, text='', font=('Arial', 11))
        self.summary_label.pack()

        # إطار الجدول الرئيسي (شجرة) مع شريط تمرير
        tree_frame = tk.Frame(main_frame)
        tree_frame.pack(fill='both', expand=True)

        v_scroll = ttk.Scrollbar(tree_frame, orient='vertical')
        v_scroll.pack(side='right', fill='y')

        h_scroll = ttk.Scrollbar(tree_frame, orient='horizontal')
        h_scroll.pack(side='bottom', fill='x')

        # الشجرة - الأعمدة الجديدة: withdrawal, withdrawal_class, paid_weekly, financial_category
        columns = ('id', 'name', 'box', 'sector', 'last_payment', 'days', 'weeks', 'category',
                   'balance', 'visa', 'last_reading', 'withdrawal', 'withdrawal_class',
                   'paid_weekly', 'estimated_due', 'financial_cat')
        self.tree = ttk.Treeview(tree_frame, columns=columns,
                                  yscrollcommand=v_scroll.set,
                                  xscrollcommand=h_scroll.set,
                                  show='headings', height=20)
        v_scroll.config(command=self.tree.yview)
        h_scroll.config(command=self.tree.xview)

        # تعريف رؤوس الأعمدة
        col_config = [
            ('id', '#', 50, 'center'),
            ('name', 'اسم الزبون', 200, 'w'),
            ('box', 'رقم العلبة', 80, 'center'),
            ('sector', 'القطاع', 120, 'center'),
            ('last_payment', 'آخر دفعة', 100, 'center'),
            ('days', 'أيام متأخرة', 80, 'center'),
            ('weeks', 'أسابيع', 70, 'center'),
            ('category', 'التصنيف', 180, 'w'),
            ('balance', 'الرصيد (ك.و)', 100, 'center'),
            ('visa', 'رصيد التأشيرة', 100, 'center'),
            ('last_reading', 'آخر قراءة', 100, 'center'),
            ('withdrawal', 'السحب (ك.و)', 100, 'center'),
            ('withdrawal_class', 'تصنيف السحب', 150, 'w'),
            ('paid_weekly', 'دفع الأسبوعي؟', 100, 'center'),
            ('estimated_due', 'المستحق التقديري (ك.و)', 140, 'center'),
            ('financial_cat', 'التصنيف المالي', 100, 'center')
        ]
        for col_id, heading, width, anchor in col_config:
            self.tree.heading(col_id, text=heading)
            self.tree.column(col_id, width=width, anchor=anchor)

        self.tree.pack(side='left', fill='both', expand=True)

        # شريط الحالة
        self.status_bar = tk.Label(self, text='', bd=1, relief='sunken', anchor='w')
        self.status_bar.pack(side='bottom', fill='x')

    def load_sectors(self):
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id, name FROM sectors WHERE is_active = TRUE ORDER BY name")
                self.sectors = cursor.fetchall()
                names = ['الكل'] + [s['name'] for s in self.sectors]
                self.sector_combo['values'] = names
                self.sector_combo.current(0)
        except Exception as e:
            logger.error(f"خطأ في تحميل القطاعات: {e}")

    def refresh_data(self):
        sector_name = self.sector_var.get()
        sector_id = None
        if sector_name != 'الكل':
            for s in self.sectors:
                if s['name'] == sector_name:
                    sector_id = s['id']
                    break

        financial_filter = None
        fin_name = self.financial_var.get()
        if fin_name != 'الكل':
            for code, display in self.monitor.financial_category_map.items():
                if display == fin_name:
                    financial_filter = code
                    break

        data = self.monitor.get_all_classifications(sector_id=sector_id, financial_category=financial_filter)
        if not data['success']:
            messagebox.showerror('خطأ', data.get('error', 'فشل تحميل البيانات'))
            return

        # ------------------- بداية الفرز المخصص -------------------
        def sort_key(cust):
            # تحديد الأولوية
            if cust['paid_weekly'] in ('لا', 'لا (لا توجد فاتورة)'):
                group = 0  # المجموعة الأولى: لم يدفع السحب الأسبوعي
            elif cust['paid_weekly'] == 'نعم' and cust['current_balance'] < 0:
                group = 1  # المجموعة الثانية: دفع السحب لكن رصيده سالب
            else:
                group = 2  # المجموعة الثالثة: البقية (ملتزمون)

            # الرصيد: الأكثر سالباً يأتي أولاً (ترتيب تصاعدي)
            balance = cust['current_balance']

            # أيام التأخير: الأكبر أولاً (نفرز تنازلياً باستخدام القيمة السالبة)
            days = -cust['days_overdue']

            # الاسم للترتيب الأبجدي داخل كل مجموعة
            name = cust['name']

            return (group, balance, days, name)

        # تطبيق الفرز
        sorted_customers = sorted(data['all_customers'], key=sort_key)
        # ------------------- نهاية الفرز -------------------

        # مسح الشجرة
        for item in self.tree.get_children():
            self.tree.delete(item)

        # إدخال البيانات بالترتيب الجديد
        for cust in sorted_customers:
            last_payment_str = cust['last_payment'].strftime('%Y-%m-%d') if cust['last_payment'] else 'لا يوجد'
            financial_cat_display = cust.get('financial_category_arabic', cust.get('financial_category', ''))
            item_id = self.tree.insert('', 'end', values=(
                cust['customer_id'],
                cust['name'],
                cust.get('box_number', ''),
                cust.get('sector_name', ''),
                last_payment_str,
                cust['days_overdue'],
                cust['weeks_overdue'],
                cust['category_name'],
                f"{cust['current_balance']:.1f}",
                f"{cust['visa_balance']:.1f}",
                f"{cust['last_counter_reading']:.1f}",
                f"{cust['withdrawal_amount']:.1f}",
                cust['withdrawal_class'],
                cust['paid_weekly'],
                f"{cust['estimated_due']:.1f}",
                financial_cat_display
            ))
            # تطبيق تلوين الصف
            self.tree.item(item_id, tags=(cust['category_key'],))

        # تكوين التاجات (الألوان)
        for cat_key, cat_data in data['grouped'].items():
            self.tree.tag_configure(cat_key, background=cat_data['color'])

        # تحديث الملخص
        total = data['total_customers']
        summary_text = f"إجمالي الزبائن: {total} | "
        for cat_key, cat_data in data['grouped'].items():
            if cat_data['count'] > 0:
                summary_text += f"{cat_data['name']}: {cat_data['count']} (تقديري {cat_data['total_estimated_due']:.0f} ك.و)  "

        self.summary_label.config(text=summary_text)
        self.status_bar.config(text=f"آخر تحديث: {data['generated_at']}")

        # تخزين البيانات للتصدير (بنفس ترتيب العرض)
        self.all_customers_data = sorted_customers

    def export_to_excel(self):
        """تصدير البيانات إلى Excel مع ورقة منفصلة لكل قطاع وورقة ملخص متقدم"""
        try:
            if not hasattr(self, 'all_customers_data') or not self.all_customers_data:
                messagebox.showwarning('تحذير', 'لا توجد بيانات للتصدير')
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"collection_monitor_{timestamp}.xlsx"
            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)
            filepath = os.path.join(export_dir, filename)

            # تجميع البيانات حسب القطاع
            sectors_dict = {}
            for cust in self.all_customers_data:
                sector = cust.get('sector_name', 'بدون قطاع')
                if sector not in sectors_dict:
                    sectors_dict[sector] = []
                sectors_dict[sector].append(cust)

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # ========== ورقة تحليل متقدم ==========
                self._write_advanced_summary(writer, self.all_customers_data)

                # ========== أوراق القطاعات ==========
                grand_total_customers = 0
                grand_total_estimated = 0.0
                summary_rows = []  # لورقة الملخص البسيط

                for sector_name, cust_list in sectors_dict.items():
                    # إنشاء DataFrame للقطاع
                    rows = []
                    for cust in cust_list:
                        rows.append({
                            'المعرف': cust.get('customer_id', ''),
                            'اسم الزبون': cust.get('name', ''),
                            'رقم العلبة': cust.get('box_number', ''),
                            'القطاع': cust.get('sector_name', ''),
                            'التصنيف المالي': cust.get('financial_category_arabic', cust.get('financial_category', '')),
                            'آخر دفعة': cust['last_payment'].strftime('%Y-%m-%d') if cust.get('last_payment') else 'لا يوجد',
                            'أيام متأخرة': cust.get('days_overdue', 0),
                            'أسابيع': cust.get('weeks_overdue', 0),
                            'التصنيف حسب التأخير': cust.get('category_name', ''),
                            'الرصيد (ك.و)': cust.get('current_balance', 0.0),
                            'رصيد التأشيرة (ك.و)': cust.get('visa_balance', 0.0),
                            'آخر قراءة عداد': cust.get('last_counter_reading', 0.0),
                            'السحب (ك.و)': cust.get('withdrawal_amount', 0.0),
                            'تصنيف السحب': cust.get('withdrawal_class', ''),
                            'دفع السحب الأسبوعي؟': cust.get('paid_weekly', ''),
                            'المستحق التقديري (ك.و)': cust.get('estimated_due', 0.0)
                        })
                    df_sector = pd.DataFrame(rows)

                    # إضافة صف إجمالي القطاع
                    sector_total_customers = len(cust_list)
                    sector_total_balance = sum(float(c.get('current_balance', 0)) for c in cust_list)
                    sector_total_visa = sum(float(c.get('visa_balance', 0)) for c in cust_list)
                    sector_total_withdrawal = sum(float(c.get('withdrawal_amount', 0)) for c in cust_list)
                    sector_total_estimated = sum(float(c.get('estimated_due', 0)) for c in cust_list)

                    total_row = pd.DataFrame([[
                        'إجمالي القطاع',
                        f"{sector_total_customers} زبون",
                        '', '', '', '', '', '',
                        f"{sector_total_balance:,.0f}",
                        f"{sector_total_visa:,.0f}",
                        '',
                        f"{sector_total_withdrawal:,.0f}",
                        '',
                        '',
                        '',
                        f"{sector_total_estimated:,.0f}"
                    ]], columns=df_sector.columns)
                    df_sector = pd.concat([df_sector, total_row], ignore_index=True)

                    sheet_name = sector_name[:31]
                    df_sector.to_excel(writer, sheet_name=sheet_name, index=False)

                    # تجميع بيانات الملخص البسيط
                    summary_rows.append([
                        sector_name,
                        sector_total_customers,
                        f"{sector_total_estimated:,.0f}"
                    ])
                    grand_total_customers += sector_total_customers
                    grand_total_estimated += sector_total_estimated

                # ========== ورقة ملخص بسيط (إجماليات القطاعات) ==========
                summary_rows.append(['الإجمالي العام', grand_total_customers, f"{grand_total_estimated:,.0f}"])
                df_summary = pd.DataFrame(summary_rows, columns=['القطاع', 'عدد الزبائن', 'إجمالي المستحق التقديري'])
                df_summary.to_excel(writer, sheet_name='ملخص', index=False)

                # تنسيق عرض الأعمدة في جميع الأوراق
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
            try:
                os.startfile(filepath) if os.name == 'nt' else webbrowser.open(filepath)
            except:
                pass

        except ImportError:
            messagebox.showerror('خطأ', 'مكتبة pandas غير مثبتة')
        except Exception as e:
            logger.error(f"خطأ في التصدير: {e}", exc_info=True)
            messagebox.showerror('خطأ', f'فشل التصدير: {str(e)}')

    def _write_advanced_summary(self, writer, all_customers):
        """كتابة ورقة تحليل متقدم تحتوي على تفاصيل دقيقة عن كل فئة (مع تحويل Decimal إلى float)"""
        # تصنيف العملاء حسب weeks_overdue و paid_weekly
        categories = {}
        for cust in all_customers:
            weeks = cust.get('weeks_overdue', 0)
            if weeks <= 0:
                cat_key = 'في الموعد'
            elif weeks == 1:
                cat_key = 'متأخر أسبوع'
            elif weeks == 2:
                cat_key = 'متأخر أسبوعين'
            elif weeks == 3:
                cat_key = 'متأخر 3 أسابيع'
            elif weeks == 4:
                cat_key = 'متأخر 4 أسابيع'
            else:
                cat_key = 'متأخر 5 أسابيع فأكثر'

            # تصنيف حسب دفع السحب
            paid = cust.get('paid_weekly', '')
            if paid in ('لا', 'لا (لا توجد فاتورة)'):
                sub_key = 'لم يدفع السحب الأسبوعي'
            elif paid == 'نعم':
                sub_key = 'دفع السحب الأسبوعي'
            else:
                sub_key = 'لا ينطبق'

            # هيكل التجميع
            if cat_key not in categories:
                categories[cat_key] = {}
            if sub_key not in categories[cat_key]:
                categories[cat_key][sub_key] = {
                    'count': 0,
                    'total_withdrawal': 0.0,
                    'total_balance': 0.0,
                    'total_estimated': 0.0,
                    'avg_days': 0.0,
                    'customers': []
                }

            cat = categories[cat_key][sub_key]
            cat['count'] += 1
            # تحويل القيم إلى float لتجنب مشكلة Decimal
            cat['total_withdrawal'] += float(cust.get('withdrawal_amount', 0.0))
            cat['total_balance'] += float(cust.get('current_balance', 0.0))
            cat['total_estimated'] += float(cust.get('estimated_due', 0.0))
            cat['avg_days'] += float(cust.get('days_overdue', 0))
            cat['customers'].append(cust.get('name', ''))

        # حساب المتوسطات
        for cat_key in categories:
            for sub_key in categories[cat_key]:
                cat = categories[cat_key][sub_key]
                if cat['count'] > 0:
                    cat['avg_days'] /= cat['count']

        # ترتيب الفئات حسب الأهمية
        ordered_cats = ['متأخر 5 أسابيع فأكثر', 'متأخر 4 أسابيع', 'متأخر 3 أسابيع',
                        'متأخر أسبوعين', 'متأخر أسبوع', 'في الموعد']

        # بناء DataFrame للعرض
        rows = []
        for cat_key in ordered_cats:
            if cat_key in categories:
                # صف عنوان الفئة
                rows.append([f"** {cat_key} **", '', '', '', '', '', ''])
                for sub_key, data in categories[cat_key].items():
                    customers_sample = '، '.join(data['customers'][:3]) + ('...' if len(data['customers']) > 3 else '')
                    rows.append([
                        f"   {sub_key}",
                        data['count'],
                        f"{data['total_withdrawal']:,.0f}",
                        f"{data['total_balance']:,.0f}",
                        f"{data['total_estimated']:,.0f}",
                        f"{data['avg_days']:.1f}",
                        customers_sample
                    ])
                rows.append(['', '', '', '', '', '', ''])  # سطر فاصل

        # إضافة إجماليات عامة
        total_count = len(all_customers)
        total_withdrawal = sum(float(c.get('withdrawal_amount', 0)) for c in all_customers)
        total_balance = sum(float(c.get('current_balance', 0)) for c in all_customers)
        total_estimated = sum(float(c.get('estimated_due', 0)) for c in all_customers)

        rows.append(['الإجمالي العام', total_count, f"{total_withdrawal:,.0f}",
                    f"{total_balance:,.0f}", f"{total_estimated:,.0f}", '', ''])

        df_advanced = pd.DataFrame(rows, columns=[
            'الفئة', 'العدد', 'إجمالي السحب (ك.و)', 'إجمالي الأرصدة (ك.و)',
            'إجمالي المستحق (ك.و)', 'متوسط الأيام', 'نماذج من العملاء'
        ])
        df_advanced.to_excel(writer, sheet_name='تحليل متقدم', index=False)