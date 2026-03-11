# ui/accounting_ui.py - واجهة محاسبة متكاملة بتصميم ناعم وواضح جداً (تحديث الوضوح)
# تم التحديث: تحسين التباين، تكبير الخطوط، إضافة نافذة تأكيد مخصصة، مع الحفاظ على جميع الوظائف.
# إضافة التصنيف المالي (عادي، مجاني، VIP، مجاني+VIP) مع أيقونة ملونة و tooltip.
# التعديلات التشخيصية: إضافة نقاط تتبع (print) وتعديلات في التنسيق للتأكد من ظهور التصنيف المالي.

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
from datetime import datetime
from modules.fast_operations import FastOperations
from modules.printing import FastPrinter

logger = logging.getLogger(__name__)

class AccountingUI(tk.Frame):
    """واجهة محاسبة - مزيج من الأناقة والوضوح الوظيفي"""
    
    def __init__(self, parent, user_data):
        super().__init__(parent)
        self.parent = parent
        self.user_data = user_data
        self.fast_ops = FastOperations()
        self.printer = FastPrinter()
        
        # ألوان باستيل محسّنة للتباين والوضوح
        self.colors = {
            'bg_main': '#FDF2F4',           # وردي باهت جداً للخلفية الرئيسية
            'primary': '#B37D7D',            # وردي داكن للأعمدة والعناوين البارزة
            'secondary': '#7FB394',          # أخضر هادئ وواضح للأزرار الرئيسية
            'accent': '#FFFFFF',              # أبيض للخلفيات المهمة
            'text_dark': '#2D2D2D',           # رمادي غامق جداً (شبه أسود) للنصوص
            'card_bg': '#FFFFFF',             # البطاقات بيضاء لتعطي عمقاً ووضوحاً
            'danger': '#E57373',               # أحمر فاتح للإلغاء أو الحذف
            'success': '#81C784',              # أخضر للنجاح
            'info': '#7986CB',                  # أزرق للمعلومات
            'warning': '#FFD54F',               # أصفر للتحذيرات
            'terminal_bg': '#2D2D2D',           # خلفية داكنة لمنطقة النتائج (لمزيد من الراحة)
            'terminal_fg': '#81C784',            # نص أخضر في منطقة النتائج
            'border_strong': '#B37D7D'           # حدود واضحة بلون أساسي
        }
        # ⬇️ أضف هذين السطرين
        self.info_labels = {}          # لتخزين مراجع عناصر Label
        self.last_visa_update = None   # (اختياري) لتخزين آخر تاريخ تحديث للتأشيرة
        
        self.selected_customer = None
        self.sectors = []
        self.last_invoice_result = None
        self.search_results_data = []
        
        self.pack(fill='both', expand=True)
        self.load_sectors()
        self.create_widgets()
        self.center_window()
    
    def load_sectors(self):
        """تحميل القطاعات مرة واحدة (بدون تغيير)"""
        from database.connection import db
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id, name FROM sectors WHERE is_active = TRUE ORDER BY name")
                self.sectors = cursor.fetchall()
        except Exception as e:
            logger.error(f"خطأ في تحميل القطاعات: {e}")
            self.sectors = []
                
    def create_widgets(self):
        """إنشاء واجهة محاسبة واضحة جداً مع الاحتفاظ بجميع العناصر (نسخة معدلة)"""
        # إزالة أي عناصر سابقة
        for widget in self.winfo_children():
            widget.destroy()
        
        # الحاوية الرئيسية
        self.main_container = tk.Frame(self, bg=self.colors['bg_main'])
        self.main_container.pack(fill='both', expand=True)
        
        # ========== الهيدر (شريط العنوان) ==========
        self.header = tk.Frame(self.main_container, bg=self.colors['primary'], height=80)
        self.header.pack(fill='x', side='top')
        self.header.pack_propagate(False)
        
        # زر العودة (لا يزال كما هو لكن بلون أوضح)
        btn_close = tk.Button(self.header, text="✕", command=self.close_window,
                            bg=self.colors['danger'], fg='white', 
                            font=('Segoe UI', 14, 'bold'),
                            bd=0, cursor='hand2', width=4, activebackground='#EF5350',
                            relief='flat')
        btn_close.pack(side='left', padx=20, pady=15)
        
        title_frame = tk.Frame(self.header, bg=self.colors['primary'])
        title_frame.pack(side='left', padx=10)
        
        tk.Label(title_frame, text="مولدة الريان الذكية", font=('Segoe UI', 24, 'bold'),
                bg=self.colors['primary'], fg='white').pack(anchor='w')
        tk.Label(title_frame, text="نظام الإدارة المالية المتكامل", font=('Segoe UI', 11),
                bg=self.colors['primary'], fg='#F0F0F0').pack(anchor='w')
        
        # معلومات المستخدم
        user_frame = tk.Frame(self.header, bg=self.colors['primary'])
        user_frame.pack(side='right', padx=20)
        user_role = self.user_data.get('role', '')
        user_name = self.user_data.get('full_name', '')
        tk.Label(user_frame, text=f"👤 {user_name}", 
                font=('Segoe UI', 12, 'bold'), bg=self.colors['primary'], fg='white').pack(anchor='e')
        tk.Label(user_frame, text=f"الدور: {user_role}", 
                font=('Segoe UI', 10), bg=self.colors['primary'], fg='#F0F0F0').pack(anchor='e')
        
        # ========== منطقة العمل الرئيسية ==========
        self.work_area = tk.Frame(self.main_container, bg=self.colors['bg_main'])
        self.work_area.pack(fill='both', expand=True, padx=30, pady=25)
        
        # ---- العمود الأيسر (البحث والمعلومات) ----
        left_column = tk.Frame(self.work_area, bg=self.colors['bg_main'])
        left_column.pack(side='left', fill='both', expand=True, padx=(0, 20))
        
        # 1. بطاقة البحث (بارزة جداً)
        search_card = tk.Frame(left_column, bg=self.colors['card_bg'], 
                            highlightbackground=self.colors['border_strong'], 
                            highlightthickness=2)
        search_card.pack(fill='x', pady=(0, 20))
        
        tk.Label(search_card, text="🔍 ابحث عن المشترك (الاسم أو رقم العلبة):", 
                font=('Segoe UI', 15, 'bold'),
                bg=self.colors['card_bg'], fg=self.colors['text_dark']).pack(anchor='e', padx=15, pady=(10, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_card, textvariable=self.search_var,
                                    font=('Segoe UI', 18), bg='#FFFFFF', fg='#000000',
                                    relief='flat', insertbackground=self.colors['primary'])
        self.search_entry.pack(fill='x', padx=15, pady=(0, 15), ipady=8)
        self.search_entry.bind('<KeyRelease>', self.quick_search)
        self.search_entry.focus_set()
        
        # قائمة النتائج (بحجم خط أكبر)
        self.results_listbox = tk.Listbox(left_column, font=('Segoe UI', 14),
                                        bg='white', fg=self.colors['text_dark'],
                                        selectbackground=self.colors['secondary'],
                                        selectforeground='white', height=5)
        self.results_listbox.pack(fill='x', pady=(0, 20))
        self.results_listbox.bind('<<ListboxSelect>>', self.on_search_select)
        
        # 2. بطاقة معلومات المشترك
        self.info_card = tk.Frame(left_column, bg=self.colors['card_bg'], 
                                highlightbackground='#E0E0E0', highlightthickness=1)
        self.info_card.pack(fill='both', expand=True)

        # عنوان البطاقة
        tk.Label(self.info_card, text="📋 ملف المشترك المختار", 
                font=('Segoe UI', 15, 'bold'),
                bg=self.colors['primary'], fg='white').pack(fill='x', ipady=5)

        # ---------- شريط التصنيف المالي (سيتم حزمه لاحقاً عند الحاجة) ----------
        self.category_frame = tk.Frame(self.info_card, bg=self.colors['card_bg'], height=34)
        # لا نقوم بحزمه هنا - سيتم حزمه في toggle_category_and_scroll

        self.category_icon = tk.Label(self.category_frame, text="", font=('Segoe UI', 14),
                                    bg=self.colors['card_bg'])
        self.category_icon.pack(side='left', padx=5)

        self.category_label = tk.Label(self.category_frame, text="", font=('Segoe UI', 11, 'bold'),
                                        bg=self.colors['card_bg'])
        self.category_label.pack(side='left', padx=(5,0))

        self.category_progress = None  # سيتم إنشاؤه لاحقاً عند الحاجة

        self.category_details_label = tk.Label(self.info_card, text="", font=('Segoe UI', 9),
                                                bg=self.colors['card_bg'], fg=self.colors['text_dark'],
                                                anchor='w', padx=15)
        # لا نقوم بحزم category_details_label هنا أيضاً - سيتم حزمه مع category_frame
        # ---------------------------------------------------------------

        # إطار داخلي للمعلومات مع إضافة سكرول عمودي
        canvas_container = tk.Frame(self.info_card, bg='white')
        canvas_container.pack(fill='both', expand=True, padx=0, pady=0)

        # إنشاء Canvas
        self.info_canvas = tk.Canvas(canvas_container, bg='white', highlightthickness=0)
        self.info_scrollbar = tk.Scrollbar(canvas_container, orient='vertical', command=self.info_canvas.yview)
        self.info_canvas.configure(yscrollcommand=self.info_scrollbar.set)

        # لا نقوم بحزم scrollbar هنا (سيتم حزمه فقط عند الحاجة)
        self.info_canvas.pack(side='right', fill='both', expand=True)

        # إطار داخلي سيحتوي على محتويات info_inner السابقة
        self.info_inner = tk.Frame(self.info_canvas, bg='white', padx=20, pady=15)
        self.info_inner_window = self.info_canvas.create_window((0, 0), window=self.info_inner, anchor='nw')

        # تحديث منطقة التمرير عندما يتغير حجم الإطار الداخلي
        def configure_inner(event):
            self.info_canvas.configure(scrollregion=self.info_canvas.bbox('all'))
            # بعد تغيير الحجم، نتحقق من الحاجة لشريط التمرير
            self.check_scroll_needed()
        self.info_inner.bind('<Configure>', configure_inner)

        # تحديث عرض الإطار الداخلي عندما يتغير حجم الـ Canvas
        def configure_canvas(event):
            canvas_width = event.width
            self.info_canvas.itemconfig(self.info_inner_window, width=canvas_width)
            self.check_scroll_needed()
        self.info_canvas.bind('<Configure>', configure_canvas)

        # ربط عجلة الفأرة للتمرير داخل الـ Canvas
        def on_mousewheel(event):
            self.info_canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
        self.info_canvas.bind('<MouseWheel>', on_mousewheel)

        # الآن ننقل الحقول إلى self.info_inner
        self.info_vars = {}
        
        # قائمة الحقول بالترتيب: (التسمية, المفتاح)
        right_fields = [
            ("الاسم الكامل", "name"),
            ("القطاع", "sector"),
            ("رقم العلبة", "box"),
            ("المسلسل", "serial")
        ]
        left_fields = [
            ("آخر قراءة (ك.واط)", "reading"),
            ("الرصيد الحالي (ك.واط)", "balance"),
            ("التأشيرة (ك.واط)", "visa"),
            ("السحب (ك.واط)", "withdrawal")
        ]
        
        # العمود الأيمن
        right_frame = tk.Frame(self.info_inner, bg='white')
        right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        for label, key in right_fields:
            row = tk.Frame(right_frame, bg='white', pady=5)
            row.pack(fill='x')
            tk.Label(row, text=label, font=('Segoe UI', 12), bg='white', 
                    fg='#7F8C8D', anchor='e').pack(fill='x')
            var = tk.StringVar(value="---")
            lbl = tk.Label(row, textvariable=var, font=('Segoe UI', 14, 'bold'), 
                    bg='white', fg=self.colors['text_dark'], anchor='e')
            lbl.pack(fill='x')
            self.info_vars[key] = var
            self.info_labels[key] = lbl   # حفظ المرجع للاستخدام في التلميحات
        
        # العمود الأيسر
        left_frame = tk.Frame(self.info_inner, bg='white')
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        # إنشاء إطار الملاحظات
        # بعد الأعمدة اليمنى واليسرى (right_frame, left_frame) وقبل نهاية الدالة
        # إنشاء إطار الملاحظات
        notes_frame = tk.Frame(self.info_inner, bg='white', padx=15, pady=50)
        notes_frame.pack(fill='x', pady=(10, 0))

        # عنوان الملاحظات مع أيقونة
        header_frame = tk.Frame(notes_frame, bg='white')
        header_frame.pack(fill='x')
        tk.Label(header_frame, text="📝 ملاحظات:", font=('Segoe UI', 12, 'bold'),
                bg='white', fg=self.colors['primary']).pack(side='right')

        # متغير لتخزين نص الملاحظات (اختياري، يمكنك استخدام النص مباشرة)
        self.notes_var = tk.StringVar(value="")

        # حقل عرض الملاحظات (نص قابل للتمرير إذا طال)
        self.notes_text = scrolledtext.ScrolledText(
            notes_frame, 
            font=('Segoe UI', 11),
            bg='#FFF9C4',           # خلفية صفراء فاتحة لجذب الانتباه
            fg=self.colors['text_dark'],
            wrap='word',            # التفاف النص تلقائياً
            height=3,               # ارتفاع مناسب لـ 3 أسطر (يزيد تلقائياً عند الحاجة)
            relief='flat',
            bd=1,
            highlightbackground='#E0E0E0'
        )
        self.notes_text.pack(fill='x', pady=(5, 0))
        self.notes_text.config(state='disabled')   # للقراءة فقط (يمكن جعله قابلاً للتحرير لاحقاً)

        # ربط تغيير حجم النافذة بفحص شريط التمرير (إذا أردت)
        self.notes_text.bind('<Configure>', lambda e: self.check_scroll_needed())
                
        for label, key in left_fields:
            row = tk.Frame(left_frame, bg='white', pady=5)
            row.pack(fill='x')
            tk.Label(row, text=label, font=('Segoe UI', 12), bg='white', 
                    fg='#7F8C8D', anchor='e').pack(fill='x')
            var = tk.StringVar(value="---")
            # ⬇️ أنشئ مرجعاً للـ Label
            lbl = tk.Label(row, textvariable=var, font=('Segoe UI', 14, 'bold'), 
                    bg='white', fg=self.colors['text_dark'], anchor='e')
            lbl.pack(fill='x')
            self.info_vars[key] = var
            self.info_labels[key] = lbl   # ⬅️ احفظ المرجع هنا
        
        # ---- العمود الأيمن (الإدخال والمعالجة) ----
        right_column = tk.Frame(self.work_area, bg=self.colors['bg_main'], width=500)
        right_column.pack(side='right', fill='both', expand=True, padx=(20, 0))
        
        # 3. بطاقة الإدخال المالي (تصميم جديد واضح)
        input_card = tk.Frame(right_column, bg=self.colors['card_bg'],
                            highlightbackground='#E0E0E0', highlightthickness=1)
        input_card.pack(fill='x', pady=(0, 15))
        
        tk.Label(input_card, text="💰 إدخال دفعة جديدة", 
                font=('Segoe UI', 16, 'bold'),
                bg=self.colors['secondary'], fg='white').pack(fill='x', ipady=5)
        
        entry_form = tk.Frame(input_card, bg='white', padx=20, pady=15)
        entry_form.pack(fill='x')
        
        # كمية الدفع (حقل ضخم)
        tk.Label(entry_form, text="كمية الدفع (ك.واط):", font=('Segoe UI', 14), 
                bg='white', fg=self.colors['secondary']).grid(row=0, column=2, sticky='e', pady=5)
        self.kilowatt_var = tk.StringVar()
        self.kilowatt_entry = tk.Entry(entry_form, textvariable=self.kilowatt_var, 
                                    font=('Segoe UI', 30, 'bold'), 
                                    width=8, bg='#F1F8E9', relief='flat', justify='center',
                                    highlightthickness=1, highlightcolor=self.colors['secondary'])
        self.kilowatt_entry.grid(row=0, column=1, padx=10)
        
        # أزرار التعديل السريع (بجانب الحقل)
        btns_quick = tk.Frame(entry_form, bg='white')
        btns_quick.grid(row=0, column=0)
        self.create_flat_btn(btns_quick, "+100", lambda: self.adjust_kilowatt(100), self.colors['secondary']).pack(side='left', padx=2)
        self.create_flat_btn(btns_quick, "+10", lambda: self.adjust_kilowatt(10), self.colors['secondary']).pack(side='left', padx=2)
        self.create_flat_btn(btns_quick, "-10", lambda: self.adjust_kilowatt(-10), self.colors['danger']).pack(side='left', padx=2)
        
        # باقي الحقول (بخطوط واضحة)
        # المجاني
        tk.Label(entry_form, text="المجاني (ك.واط):", font=('Segoe UI', 12), 
                bg='white', fg=self.colors['text_dark']).grid(row=1, column=2, sticky='e', pady=10)
        self.free_var = tk.StringVar(value="0")
        tk.Entry(entry_form, textvariable=self.free_var, font=('Segoe UI', 14), 
                bg='#F8F9FA', relief='flat', width=15, justify='center').grid(row=1, column=1, pady=10)
        
        # سعر الكيلو
        tk.Label(entry_form, text="سعر الكيلو (ل.س):", font=('Segoe UI', 12), 
                bg='white', fg=self.colors['text_dark']).grid(row=2, column=2, sticky='e', pady=10)
        self.price_var = tk.StringVar(value="7200")
        tk.Entry(entry_form, textvariable=self.price_var, font=('Segoe UI', 14), 
                bg='#F8F9FA', relief='flat', width=15, justify='center').grid(row=2, column=1, pady=10)
        
        # الحسم
        tk.Label(entry_form, text="الحسم (ل.س):", font=('Segoe UI', 12), 
                bg='white', fg=self.colors['text_dark']).grid(row=3, column=2, sticky='e', pady=10)
        self.discount_var = tk.StringVar(value="0")
        tk.Entry(entry_form, textvariable=self.discount_var, font=('Segoe UI', 14), 
                bg='#F8F9FA', relief='flat', width=15, justify='center').grid(row=3, column=1, pady=10)
        
        # 4. أزرار الإجراءات (كبيرة وواضحة)
        action_frame = tk.Frame(right_column, bg=self.colors['bg_main'])
        action_frame.pack(fill='x', pady=10)
        
        btn_row = tk.Frame(action_frame, bg=self.colors['bg_main'])
        btn_row.pack(fill='x')
        
        # زر المعالجة (الأهم)
        self.process_btn = self.create_action_btn(btn_row, "⚡ معالجة وحفظ", self.fast_process, self.colors['secondary'])
        self.process_btn.pack(side='left', fill='both', expand=True, padx=5)
        
        # زر الطباعة
        self.print_btn = self.create_action_btn(btn_row, "🖨️ طباعة", self.print_invoice, self.colors['primary'])
        self.print_btn.pack(side='left', fill='both', expand=True, padx=5)
        
        # الصف الثاني من الأزرار
        btn_row2 = tk.Frame(action_frame, bg=self.colors['bg_main'])
        btn_row2.pack(fill='x', pady=(5, 0))
        
        # زر المعاينة
        preview_btn = self.create_action_btn(btn_row2, "🧮 معاينة", self.calculate_preview, self.colors['info'])
        preview_btn.pack(side='left', fill='both', expand=True, padx=5)
        
        # زر التصفير
        clear_btn = self.create_action_btn(btn_row2, "🗑️ تصفير", self.clear_fields, self.colors['warning'])
        clear_btn.pack(side='left', fill='both', expand=True, padx=5)
        
        # 5. منطقة النتائج (بطريقة Dark Mode)
        result_card = tk.Frame(right_column, bg=self.colors['terminal_bg'],
                            highlightbackground=self.colors['border_strong'], 
                            highlightthickness=1)
        result_card.pack(fill='both', expand=True, pady=10)
        
        self.result_text = scrolledtext.ScrolledText(result_card, font=('Consolas', 13), 
                                                    bg=self.colors['terminal_bg'], 
                                                    fg=self.colors['terminal_fg'], 
                                                    bd=0, padx=10, pady=10,
                                                    insertbackground=self.colors['primary'])
        self.result_text.pack(fill='both', expand=True)
        self.result_text.config(state='disabled')
        
        self.show_result_message("🔍 جهاز الاستقبال جاهز... بانتظار اختيار زبون")
        
        # بعد إنشاء كل العناصر، نضمن إخفاء category_frame في البداية
        self.toggle_category_and_scroll(False)
        
        # ربط حدث تغيير حجم النافذة لفحص الحاجة للتمرير
        self.parent.bind('<Configure>', lambda e: self.check_scroll_needed())



    def check_scroll_needed(self):
        """فحص ما إذا كان المحتوى يحتاج إلى شريط تمرير عمودي، وإظهار/إخفاء scrollbar وفقاً لذلك"""
        # التأكد من أن canvas والمحتوى قد تم رسمهما
        self.info_canvas.update_idletasks()
        content_height = self.info_inner.winfo_reqheight()
        canvas_height = self.info_canvas.winfo_height()
        
        # نعتبر أن هناك حاجة للتمرير إذا كان المحتوى أكبر من مساحة العرض بفارق أكثر من 5 بكسل
        # لتجنب الظهور بسبب فروق بسيطة في الحساب
        if content_height > canvas_height + 5:
            # نحتاج إلى شريط تمرير
            if not self.info_scrollbar.winfo_ismapped():
                self.info_scrollbar.pack(side='left', fill='y')
        else:
            # لا حاجة لشريط التمرير
            if self.info_scrollbar.winfo_ismapped():
                self.info_scrollbar.pack_forget()
        
        # تحديث منطقة التمرير
        self.info_canvas.configure(scrollregion=self.info_canvas.bbox('all'))

    def bind_tooltip(self, widget, text):
        """ربط tooltip يظهر أسفل العنصر، وإذا لم تكن مساحة كافية يظهر فوقه"""
        def enter(event):
            # حساب موقع التلميح
            x = widget.winfo_rootx() + 10
            y_below = widget.winfo_rooty() + widget.winfo_height() + 5
            y_above = widget.winfo_rooty() - 5  # سنضبط الارتفاع لاحقاً
            
            # إنشاء نافذة التلميح مؤقتاً لقياس ارتفاعها
            temp_tip = tk.Toplevel(widget)
            temp_tip.wm_overrideredirect(True)
            temp_tip.wm_geometry("+0+0")
            label = tk.Label(temp_tip, text=text, justify='right',
                            background="#ffffe0", relief='solid', borderwidth=1,
                            font=("Arial", 10))
            label.pack()
            temp_tip.update_idletasks()
            tip_height = temp_tip.winfo_reqheight()
            temp_tip.destroy()
            
            # التحقق من المساحة المتاحة أسفل
            screen_height = widget.winfo_screenheight()
            if y_below + tip_height < screen_height:
                y = y_below
            else:
                y = y_above - tip_height
            
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            label = tk.Label(self.tooltip, text=text, justify='right',
                            background="#ffffe0", relief='solid', borderwidth=1,
                            font=("Arial", 10))
            label.pack()
        
        def leave(event):
            if hasattr(self, 'tooltip'):
                try:
                    self.tooltip.destroy()
                    del self.tooltip
                except:
                    pass
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)

    
    # ----- دوال مساعدة للتصميم (بدون تغيير) -----
    def create_flat_btn(self, parent, text, command, color):
        btn = tk.Button(parent, text=text, command=command, bg=color, fg=self.colors['text_dark'],
                        font=('Segoe UI', 10, 'bold'), relief='flat', padx=10, cursor='hand2')
        btn.bind("<Enter>", lambda e: btn.config(bg=self.lighten_color(color)))
        btn.bind("<Leave>", lambda e: btn.config(bg=color))
        return btn
    
    def create_action_btn(self, parent, text, command, color):
        btn = tk.Button(parent, text=text, command=command, bg=color, fg='white' if color in [self.colors['primary'], self.colors['secondary'], self.colors['info']] else self.colors['text_dark'],
                        font=('Segoe UI', 14, 'bold'), relief='flat', pady=12, cursor='hand2',
                        activebackground=self.lighten_color(color), activeforeground='white')
        btn.bind("<Enter>", lambda e: btn.config(bg=self.lighten_color(color)))
        btn.bind("<Leave>", lambda e: btn.config(bg=color))
        return btn
    
    def lighten_color(self, hex_color):
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, int(r * 1.2))
        g = min(255, int(g * 1.2))
        b = min(255, int(b * 1.2))
        return f'#{r:02x}{g:02x}{b:02x}'
    
    # ----- دوال النافذة -----
    def close_window(self):
        self.parent.destroy()
    
    def center_window(self):
        root = self.parent.winfo_toplevel()
        root.update_idletasks()
        width, height = 1400, 900   # أكبر قليلاً للوضوح
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')
        root.minsize(1300, 800)
    
    # ----- دوال البحث والاختيار (كما كانت تماماً) -----
    def quick_search(self, event=None):
        search_term = self.search_var.get().strip()
        if len(search_term) < 2:
            self.results_listbox.delete(0, tk.END)
            return
        if hasattr(self, '_search_job'):
            self.after_cancel(self._search_job)
        self._search_job = self.after(300, self._perform_search, search_term)
    
    def _perform_search(self, search_term):
        if not search_term:
            return
        results = self.fast_ops.fast_search_customers(search_term, limit=30)
        self.results_listbox.delete(0, tk.END)
        self.search_results_data = results
        for customer in results:
            display_text = f"👤 {customer['name']} | علبة: {customer['box_number']} | رصيد: {customer['current_balance']:,.0f}"
            self.results_listbox.insert(tk.END, display_text)
    
    def on_search_select(self, event=None):
        selection = self.results_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        if hasattr(self, 'search_results_data') and idx < len(self.search_results_data):
            customer = self.search_results_data[idx]
            self.select_customer(customer['id'])
        
    def select_customer(self, customer_id):
        """تحديد زبون وعرض بياناته (بدون تغيير في المنطق) + تحديث التصنيف"""
        try:
            customer_data = self.fast_ops.fast_get_customer_details(customer_id)
            # [تشخيص] طباعة البيانات القادمة من الدالة
            #print("بيانات الزبون:", customer_data)
            
            if not customer_data:
                messagebox.showwarning("تحذير", "لم يتم العثور على بيانات الزبون")
                return
            self.last_invoice_result = None   # فاتورة سابقة لم تعد صالحة لهذا الزبون    
            self.selected_customer = customer_data
            
            # الحقول النصية (مع تحويل None إلى '---')
            self.info_vars['name'].set(customer_data.get('name') or '---')
            self.info_vars['sector'].set(customer_data.get('sector_name') or '---')
            self.info_vars['box'].set(customer_data.get('box_number') or '---')
            self.info_vars['serial'].set(customer_data.get('serial_number') or '---')
            
            # الحقول الرقمية (مع تحويل None إلى 0)
            last_reading = customer_data.get('last_counter_reading')
            self.info_vars['reading'].set(f"{float(last_reading) if last_reading is not None else 0:,.0f}")
            
            current_balance = customer_data.get('current_balance')
            self.info_vars['balance'].set(f"{float(current_balance) if current_balance is not None else 0:,.0f} ك.واط")
            
            visa_balance = customer_data.get('visa_balance')
            self.info_vars['visa'].set(f"{float(visa_balance) if visa_balance is not None else 0:,.0f}")
            
            withdrawal_amount = customer_data.get('withdrawal_amount')
            self.info_vars['withdrawal'].set(f"{float(withdrawal_amount) if withdrawal_amount is not None else 0:,.0f}")
            
            self.kilowatt_var.set("")
            self.free_var.set("0")
            self.price_var.set("7200")
            self.discount_var.set("0")
            
            # تحديث الملاحظات (التعامل الآمن مع None)
            notes = customer_data.get('notes')
            self.notes_text.config(state='normal')
            self.notes_text.delete(1.0, tk.END)
            if notes and str(notes).strip():
                self.notes_text.insert(tk.END, str(notes).strip())
            else:
                self.notes_text.insert(tk.END, "(لا توجد ملاحظات)")
            self.notes_text.config(state='disabled')
            
            self.process_btn.config(state='normal', bg=self.colors['secondary'])
            self.print_btn.config(state='normal', bg=self.colors['primary'])
            
            # تحديث عرض التصنيف المالي
            self.update_financial_category_display(customer_data)
            # ⬇️ أضف هذا السطر لربط التلميح بالتأشيرة
            self.bind_visa_tooltip(customer_id)
            
            self.show_result_message(f"✅ تم تحديد الزبون: {customer_data.get('name', '')}\n"
                                    f"الرصيد الحالي: {float(current_balance) if current_balance is not None else 0:,.0f} ك.واط\n"
                                    f"آخر قراءة عداد: {float(last_reading) if last_reading is not None else 0:,.0f}\n\n"
                                    f"⚠️ أدخل كمية الدفع والمجاني ثم اضغط على 'معالجة سريعة'")
            self.kilowatt_entry.focus_set()
            
            # تحديث شريط التمرير بعد تحميل البيانات
            self.check_scroll_needed()
            
        except Exception as e:
            logger.error(f"خطأ في تحديد الزبون: {e}")
            messagebox.showerror("خطأ", f"فشل تحميل بيانات الزبون: {str(e)}")
            
                
    # ----- دوال التصنيف المالي (جديدة) -----
    def update_financial_category_display(self, customer_data):
        """تحديث عرض التصنيف المالي مع إخفاء الشريط والسكرول للزبون العادي"""
        #print("✅ update_financial_category_display تم استدعاؤها")
        #print("البيانات المستقبلة:", customer_data.keys())
        
        category = customer_data.get('financial_category')
        if not category:
            category = 'normal'
            #print("تم تعيين تصنيف افتراضي: normal")
        
        # إعدادات الأيقونة واللون
        icons = {
            'normal': '👤',
            'free': '🎁',
            'vip': '⭐',
            'free_vip': '🌟'
        }
        colors = {
            'normal': '#3498db',      # أزرق
            'free': '#2ecc71',        # أخضر
            'vip': '#e67e22',         # برتقالي
            'free_vip': '#9b59b6'     # بنفسجي
        }
        names = {
            'normal': 'عادي',
            'free': 'مجاني',
            'vip': 'VIP',
            'free_vip': 'مجاني + VIP'
        }
        bg_colors = {
            'normal': '#EAF3FF',      # أزرق فاتح جداً
            'free': '#E9F7EF',        # أخضر فاتح جداً
            'vip': '#FFF7EA',          # برتقالي فاتح جداً
            'free_vip': '#F4EAF7'      # بنفسجي فاتح جداً
        }
        
        icon = icons.get(category, '👤')
        color = colors.get(category, '#7f8c8d')
        name = names.get(category, 'غير معروف')
        bg = bg_colors.get(category, self.colors['card_bg'])
        
        # تحديث الشريط بالكامل
        self.category_frame.config(bg=bg)
        self.category_icon.config(text=icon, fg=color, bg=bg)
        self.category_label.config(text=name, fg=color, bg=bg)
        self.category_details_label.config(bg=bg, fg=self.colors['text_dark'])
        
        # بناء نص التفاصيل للـ tooltip والملخص
        tooltip_text = self.build_category_tooltip(customer_data)
        details_summary = self.build_category_summary(customer_data)
        
        # تحديث سطر الملخص
        self.category_details_label.config(text=details_summary)
        
        # ربط tooltip لجميع عناصر الشريط
        self.bind_tooltip(self.category_icon, tooltip_text)
        self.bind_tooltip(self.category_label, tooltip_text)
        self.bind_tooltip(self.category_details_label, tooltip_text)
        
        # إدارة شريط تقدم المجاني (category_progress)
        if self.category_progress:
            self.category_progress.destroy()
            self.category_progress = None
        
        # إضافة شريط تقدم المجاني إذا كان التصنيف يحتوي على مجاني
        if category in ('free', 'free_vip'):
            total = float(customer_data.get('free_amount', 0))
            remaining = float(customer_data.get('free_remaining', 0))
            if total > 0:
                percent = (remaining / total) * 100
                progress_text = f" {remaining:,.0f}/{total:,.0f} ك.و"
                self.category_progress = tk.Label(self.category_frame, text=progress_text,
                                                font=('Segoe UI', 9), fg='#2ecc71', bg=bg)
                self.category_progress.pack(side='left', padx=5)
                self.bind_tooltip(self.category_progress, tooltip_text)
        
        # إظهار أو إخفاء شريط التصنيف بناءً على التصنيف
        self.toggle_category_and_scroll(category != 'normal')

            
    def toggle_category_and_scroll(self, show):
        """
        إظهار أو إخفاء شريط التصنيف (category_frame) وشريط التمرير بناءً على show.
        """
        if show:
            # إظهار شريط التصنيف إذا كان مخفياً
            if not self.category_frame.winfo_ismapped():
                self.category_frame.pack(fill='x', padx=10, pady=(10, 0))
                # حزم category_details_label أيضاً لأنه جزء من التصنيف
                self.category_details_label.pack(fill='x', pady=(4, 10))
        else:
            # إخفاء شريط التصنيف إذا كان ظاهراً
            if self.category_frame.winfo_ismapped():
                self.category_frame.pack_forget()
                self.category_details_label.pack_forget()
        
        # بعد تغيير ظهور category_frame، نتحقق من الحاجة لشريط التمرير
        self.check_scroll_needed()   


    def build_category_summary(self, customer_data):
        """بناء ملخص مختصر للتصنيف المالي (سطر واحد)"""
        category = customer_data.get('financial_category', 'normal')
        parts = []
        
        if category in ('free', 'free_vip'):
            remaining = float(customer_data.get('free_remaining', 0))
            total = float(customer_data.get('free_amount', 0))
            if total > 0:
                parts.append(f"مجاني متبقي: {remaining:,.0f} ك.و")
        
        if category in ('vip', 'free_vip'):
            days = customer_data.get('vip_no_cut_days', 0)
            expiry = customer_data.get('vip_expiry_date')
            if expiry:
                parts.append(f"VIP حتى {expiry}")
            elif days:
                parts.append(f"VIP {days} يوم")
        
        return " | ".join(parts) if parts else ""
    
    def build_category_tooltip(self, customer_data):
        """بناء نص التفاصيل للتصنيف المالي"""
        category = customer_data.get('financial_category', 'normal')
        lines = []
        
        if category in ('free', 'free_vip'):
            lines.append(f"سبب المجانية: {customer_data.get('free_reason', 'غير محدد')}")
            lines.append(f"المبلغ المجاني: {float(customer_data.get('free_amount', 0)):,.0f} ك.و")
            lines.append(f"المتبقي: {float(customer_data.get('free_remaining', 0)):,.0f} ك.و")
            if expiry := customer_data.get('free_expiry_date'):
                lines.append(f"تاريخ الانتهاء: {expiry}")
        
        if category in ('vip', 'free_vip'):
            lines.append(f"سبب VIP: {customer_data.get('vip_reason', 'غير محدد')}")
            lines.append(f"أيام عدم القطع: {customer_data.get('vip_no_cut_days', 0)} يوم")
            if expiry := customer_data.get('vip_expiry_date'):
                lines.append(f"تاريخ انتهاء VIP: {expiry}")
            lines.append(f"فترة السماح: {customer_data.get('vip_grace_period', 0)} يوم")
        
        return "\n".join(lines) if lines else "لا توجد تفاصيل إضافية"
    
    
    # ----- دوال الإدخال والتعديل (كما كانت) -----
    def adjust_kilowatt(self, amount):
        try:
            current = float(self.kilowatt_var.get() or 0)
            new_value = current + amount
            if new_value >= 0:
                self.kilowatt_var.set(str(int(new_value)))
        except ValueError:
            self.kilowatt_var.set("0")
    
    def calculate_preview(self):
        """معاينة (بدون تغيير)"""
        if not self.selected_customer:
            messagebox.showerror("خطأ", "يرجى اختيار زبون أولاً")
            return
        try:
            if not self.kilowatt_var.get().strip():
                messagebox.showerror("خطأ", "يرجى إدخال كمية الدفع")
                return
            kilowatt_amount = float(self.kilowatt_var.get())
            free_kilowatt = float(self.free_var.get() or 0)
            price_per_kilo = float(self.price_var.get() or 7200)
            discount = float(self.discount_var.get() or 0)
            last_reading = float(self.selected_customer.get('last_counter_reading', 0))
            current_balance = float(self.selected_customer.get('current_balance', 0))
            new_reading = last_reading + kilowatt_amount + free_kilowatt
            new_balance = current_balance + kilowatt_amount + free_kilowatt
            total_amount = (kilowatt_amount * price_per_kilo) - discount
            preview_text = f"""
📊 معاينة الحساب (غير محفوظة):

الزبون: {self.selected_customer.get('name', '')}

البيانات المدخلة:
• كمية الدفع: {kilowatt_amount:,.1f} كيلو
• المجاني: {free_kilowatt:,.1f} كيلو
• سعر الكيلو: {price_per_kilo:,.0f} ل.س
• الحسم: {discount:,.0f} ل.س

نتائج الحساب:
• القراءة السابقة: {last_reading:,.0f}
• القراءة الجديدة: {new_reading:,.0f}
• الإجمالي المقطوع: {(kilowatt_amount + free_kilowatt):,.1f} كيلو
• المبلغ الإجمالي: {total_amount:,.0f} ل.س
• الرصيد الجديد: {new_balance:,.0f} ك.واط

للحفظ الفعلي اضغط على "⚡ معالجة سريعة"
"""
            self.show_result_message(preview_text)
        except ValueError:
            messagebox.showerror("خطأ", "يرجى إدخال أرقام صحيحة في الحقول الرقمية")
        except Exception as e:
            logger.error(f"خطأ في حساب المعاينة: {e}")
            messagebox.showerror("خطأ", f"فشل حساب المعاينة: {str(e)}")
    
    # ----- نافذة التأكيد المخصصة الجديدة (واضحة وكبيرة) -----
    def show_custom_confirm_dialog(self):
        """نافذة تأكيد مخصصة قبل المعالجة الفعلية - بحجم تلقائي مناسب للمحتوى"""
        if not self.selected_customer:
            messagebox.showwarning("تنبيه", "يرجى اختيار مشترك أولاً")
            return
        
        # التحقق من صحة المدخلات
        try:
            kilowatt_amount = float(self.kilowatt_var.get() or 0)
            free_kilowatt = float(self.free_var.get() or 0)
            price_per_kilo = float(self.price_var.get() or 7200)
            discount = float(self.discount_var.get() or 0)
        except ValueError:
            messagebox.showerror("خطأ", "يرجى إدخال أرقام صحيحة")
            return
        
        # إنشاء نافذة التأكيد (بدون تحديد حجم ثابت)
        dialog = tk.Toplevel(self)
        dialog.title("تأكيد العملية")
        dialog.configure(bg='white')
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # إطار رئيسي يمتد ليملأ النافذة
        main_frame = tk.Frame(dialog, bg='white')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # العنوان
        tk.Label(main_frame, text="⚠️ تأكيد حفظ الفاتورة", font=('Segoe UI', 22, 'bold'), 
                bg='#FFF9C4', fg='#F57F17', pady=20).pack(fill='x')
        
        # تفاصيل العملية (في إطار قابل للتمدد)
        details_frame = tk.Frame(main_frame, bg='white', pady=20)
        details_frame.pack(fill='both', expand=True)
        
        customer = self.selected_customer
        total_kw = kilowatt_amount + free_kilowatt
        total_amount = (kilowatt_amount * price_per_kilo) - discount
        
        # تحويل القيم من Decimal إلى float لتجنب أخطاء الجمع
        last_reading = float(customer.get('last_counter_reading', 0))
        new_reading = last_reading + total_kw
        current_balance = float(customer.get('current_balance', 0))
        new_balance = current_balance + total_kw
        
        details_text = f"""
    الزبون: {customer.get('name', '')}
    القطاع: {customer.get('sector_name', '')}   |   رقم العلبة: {customer.get('box_number', '')}

    ════════════════════════════════
    كمية الدفع: {kilowatt_amount:,.0f} ك.واط
    المجاني: {free_kilowatt:,.0f} ك.واط
    الإجمالي المقطوع: {total_kw:,.0f} ك.واط
    سعر الكيلو: {price_per_kilo:,.0f} ل.س
    الحسم: {discount:,.0f} ل.س
    المبلغ الإجمالي: {total_amount:,.0f} ل.س

    القراءة السابقة: {last_reading:,.0f}
    القراءة الجديدة: {new_reading:,.0f}
    الرصيد الجديد: {new_balance:,.0f} ك.واط
    ════════════════════════════════
        """
        
        lbl_details = tk.Label(details_frame, text=details_text, font=('Segoe UI', 14), 
                            bg='white', justify='right', anchor='ne')
        lbl_details.pack(pady=10)
        
        # الأزرار في الأسفل (إطار منفصل)
        btn_row = tk.Frame(main_frame, bg='white', pady=20)
        btn_row.pack(fill='x', side='bottom')
        
        def on_confirm():
            dialog.destroy()
            self._execute_fast_process()
        
        tk.Button(btn_row, text="✅ نعم، حفظ وطباعة", font=('Segoe UI', 16, 'bold'), 
                bg=self.colors['secondary'], fg='white', 
                width=18, command=on_confirm, cursor='hand2').pack(side='right', padx=20)
        
        tk.Button(btn_row, text="❌ إلغاء", font=('Segoe UI', 16), 
                bg='#E0E0E0', fg=self.colors['text_dark'], 
                width=12, command=dialog.destroy, cursor='hand2').pack(side='left', padx=20)
        
        # بعد إنشاء كل المحتوى، نقوم بضبط حجم النافذة ليتناسب مع المحتوى
        dialog.update_idletasks()
        width = dialog.winfo_reqwidth() + 30   # إضافة هامش بسيط
        height = dialog.winfo_reqheight() + 30
        dialog.geometry(f"{width}x{height}")
        
        # توسيط النافذة بالنسبة للنافذة الأم
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (width // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (height // 2)
        dialog.geometry(f"+{x}+{y}")
    
    # ----- دوال المعالجة الفعلية (منقولة من fast_process) -----
    def _execute_fast_process(self):
        """تنفيذ المعالجة بعد التأكيد"""
        try:
            kilowatt_amount = float(self.kilowatt_var.get())
            free_kilowatt = float(self.free_var.get() or 0)
            price_per_kilo = float(self.price_var.get() or 7200)
            discount = float(self.discount_var.get() or 0)
            
            if kilowatt_amount < 0 or free_kilowatt < 0:
                messagebox.showerror("خطأ", "كمية الدفع والمجاني يجب أن تكون أرقاماً موجبة")
                return
            
            result = self.fast_ops.fast_process_invoice(
                customer_id=self.selected_customer['id'],
                
                kilowatt_amount=kilowatt_amount,
                free_kilowatt=free_kilowatt,
                price_per_kilo=price_per_kilo,
                discount=discount,
                user_id=self.user_data.get('id', 1),
                customer_withdrawal=self.selected_customer.get('withdrawal_amount', 0),   
            )
            # ✅ تأكد من وجود customer_id في النتيجة (أضف هذا السطر)
            if 'customer_id' not in result:
                result['customer_id'] = self.selected_customer['id']            
            self.last_invoice_result = result
            if result.get('success'):
                result_text = f"""
✅ تمت المعالجة بنجاح!

تفاصيل الفاتورة:
• رقم الفاتورة: {result.get('invoice_number', 'N/A')}
• الزبون: {result.get('customer_name', 'N/A')}
• كمية الدفع: {result.get('kilowatt_amount', 0):,.1f} كيلو
• المجاني: {result.get('free_kilowatt', 0):,.1f} كيلو
• الإجمالي المقطوع: {(result.get('kilowatt_amount', 0) + result.get('free_kilowatt', 0)):,.1f} كيلو
• القراءة السابقة: {result.get('previous_reading', 0):,.0f}
• القراءة الجديدة: {result.get('new_reading', 0):,.0f}
• المبلغ الإجمالي: {result.get('total_amount', 0):,.0f} ل.س
• الرصيد الجديد: {result.get('new_balance', 0):,.0f}
• وقت المعالجة: {result.get('processed_at', 'N/A')}

يمكنك الآن طباعة الفاتورة.
"""
                self.show_result_message(result_text)
                self.last_invoice_result = result
                self.selected_customer['current_balance'] = result['new_balance']
                self.selected_customer['last_counter_reading'] = result['new_reading']
                self.info_vars['balance'].set(f"{result['new_balance']:,.0f} ك.واط")
                self.info_vars['reading'].set(f"{result['new_reading']:,.0f}")
                
                if messagebox.askyesno("طباعة", "هل تريد طباعة الفاتورة الآن؟"):
                    self.print_invoice()
                self.clear_input_fields()
            else:
                error_msg = result.get('error', 'حدث خطأ غير معروف')
                self.show_result_message(f"❌ فشل المعالجة:\n{error_msg}")
                messagebox.showerror("خطأ", f"فشل المعالجة: {error_msg}")
        except ValueError:
            messagebox.showerror("خطأ", "يرجى إدخال أرقام صحيحة في الحقول الرقمية")
        except Exception as e:
            logger.error(f"خطأ في المعالجة: {e}")
            messagebox.showerror("خطأ", f"حدث خطأ غير متوقع: {str(e)}")


    def _get_visa_history(self, customer_id):
        """
        جلب جميع تعديلات التأشيرة للزبون من جدول customer_history.
        يتم جلب كل السجلات أولاً ثم تصفيتها في بايثون لتجنب مشاكل SQL.
        """
        if not customer_id:
            return []
        try:
            from database.connection import db
            with db.get_cursor() as cursor:
                # جلب كل السجلات لهذا الزبون
                cursor.execute("""
                    SELECT created_at, old_value, new_value, notes, transaction_type
                    FROM customer_history
                    WHERE customer_id = %s
                    ORDER BY created_at DESC
                """, (customer_id,))
                all_records = cursor.fetchall()
                
                # تصفية السجلات التي تتعلق بالتأشيرة
                visa_records = []
                for record in all_records:
                    transaction_type = record.get('transaction_type', '') or ''
                    notes = record.get('notes', '') or ''
                    
                    # التحقق من وجود كلمات مفتاحية تشير إلى تعديل التأشيرة
                    if ('visa' in transaction_type.lower() or 
                        'تأشيرة' in transaction_type or
                        'visa' in notes.lower() or 
                        'تأشيرة' in notes):
                        visa_records.append(record)
                
                # للتشخيص
                print(f"عدد سجلات التأشيرة للزبون {customer_id}: {len(visa_records)} (من أصل {len(all_records)})")
                return visa_records
                
        except Exception as e:
            logger.error(f"خطأ في جلب سجل التأشيرات: {e}")
            return []

    def bind_visa_tooltip(self, customer_id):
        visa_label = self.info_labels.get('visa')
        if not visa_label:
            return

        history = self._get_visa_history(customer_id)
        print(f"عدد سجلات التأشيرة التي تم جلبها: {len(history)}")   # تشخيص

        if not history:
            tooltip_text = "لا توجد تعديلات سابقة على رصيد التأشيرة."
        else:
            # ... باقي الكود ...

            lines = []
            for record in history:
                created_at = record['created_at']
                if isinstance(created_at, datetime):
                    date_str = created_at.strftime('%Y-%m-%d %H:%M')
                else:
                    date_str = str(created_at)

                old_val = record.get('old_value')
                new_val = record.get('new_value')
                notes = record.get('notes', '') or ''

                if old_val is not None and new_val is not None:
                    try:
                        old_float = float(old_val)
                        new_float = float(new_val)
                        diff = new_float - old_float
                        sign = '+' if diff > 0 else ''
                        lines.append(f"{date_str}: {old_float:,.0f} → {new_float:,.0f} ({sign}{diff:,.0f})")
                    except (ValueError, TypeError):
                        lines.append(f"{date_str}: تعديل (القيم: {old_val} → {new_val})")
                elif notes:
                    lines.append(f"{date_str}: {notes}")
                else:
                    lines.append(f"{date_str}: تعديل")

            tooltip_text = "\n".join(lines)

        self.bind_tooltip(visa_label, tooltip_text)


    def fast_process(self):
        """الواجهة الجديدة للمعالجة: تعرض نافذة التأكيد بدلاً من messagebox"""
        self.show_custom_confirm_dialog()
    
    # ----- بقية الدوال كما هي (print_invoice, show_result_message, clear_input_fields, clear_fields) -----
    def print_invoice(self):
        if not hasattr(self, 'last_invoice_result') or not self.last_invoice_result:
            messagebox.showwarning("تحذير", "لا توجد فاتورة حديثة للطباعة")
            return
        
        if self.last_invoice_result.get('customer_id') != self.selected_customer.get('id'):
            messagebox.showwarning("تحذير", "الفاتورة السابقة لا تخص هذا الزبون، قم بمعالجة فاتورة جديدة أولاً")
            return
        
        try:
            invoice_data = {
                'customer_name': self.selected_customer.get('name', ''),
                'sector_name': self.selected_customer.get('sector_name', ''),
                'box_number': self.selected_customer.get('box_number', ''),
                'serial_number': self.selected_customer.get('serial_number', ''),
                'previous_reading': self.last_invoice_result.get('previous_reading', 0),
                'new_reading': self.last_invoice_result.get('new_reading', 0),
                'kilowatt_amount': self.last_invoice_result.get('kilowatt_amount', 0),
                'free_kilowatt': self.last_invoice_result.get('free_kilowatt', 0),
                'consumption': self.last_invoice_result.get('kilowatt_amount', 0) + self.last_invoice_result.get('free_kilowatt', 0),
                'price_per_kilo': self.last_invoice_result.get('price_per_kilo', 7200),
                'total_amount': self.last_invoice_result.get('total_amount', 0),
                'new_balance': self.last_invoice_result.get('new_balance', 0),
                'invoice_number': self.last_invoice_result.get('invoice_number', ''),
                'discount': self.last_invoice_result.get('discount', 0),
                'withdrawal_amount': self.selected_customer.get('withdrawal_amount', 0),
                'visa_application': self.selected_customer.get('visa_balance', 0),
                'customer_id': self.selected_customer.get('id', 0),   # <-- إضافة هذا السطر
            }
            
            if self.printer.print_fast_invoice(invoice_data):
                self.show_result_message("🖨️ تمت الطباعة بنجاح!")
                messagebox.showinfo("نجاح", "تمت طباعة الفاتورة بنجاح")
            else:
                self.show_result_message("❌ فشل الطباعة. تحقق من اتصال الطابعة.")
                messagebox.showerror("خطأ", "فشل الطباعة. تحقق من اتصال الطابعة.")
        except SystemExit:
            # منع إنهاء البرنامج إذا حاولت مكتبة الطباعة استدعاء exit()
            logger.error("محاولة إنهاء البرنامج أثناء الطباعة - تم منعها")
            messagebox.showerror("خطأ", "حدثت محاولة إنهاء البرنامج بسبب مشكلة في الطابعة. تم منع الإنهاء.")
            self.show_result_message("❌ فشل الطباعة (محاولة إنهاء البرنامج)")
        except Exception as e:
            logger.error(f"خطأ في الطباعة: {e}", exc_info=True)
            messagebox.showerror("خطأ", f"فشل الطباعة: {str(e)}")
            self.show_result_message(f"❌ خطأ في الطباعة: {str(e)}")
    
    def show_result_message(self, message):
        self.result_text.config(state='normal')
        self.result_text.delete(1.0, tk.END)
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.result_text.insert(tk.END, f"> [{timestamp}] {message}")
        self.result_text.config(state='disabled')
        self.result_text.see(tk.END)
    
    def clear_input_fields(self):
        self.kilowatt_var.set("")
        self.free_var.set("0")
        self.price_var.set("7200")
        self.discount_var.set("0")
        if self.selected_customer:
            self.kilowatt_entry.focus_set()
            
    def clear_fields(self):
        """مسح جميع الحقول وإعادة تعيين الواجهة"""
        self.search_var.set("")
        self.kilowatt_var.set("")
        self.free_var.set("0")
        self.price_var.set("7200")
        self.discount_var.set("0")
        for key in self.info_vars:
            self.info_vars[key].set("---")
        self.results_listbox.delete(0, tk.END)
        self.show_result_message("🔍 ابدأ بالبحث عن زبون باستخدام حقل البحث أعلاه...")
        self.selected_customer = None
        self.last_invoice_result = None
        self.process_btn.config(state='disabled', bg='#D4A5A5')
        self.print_btn.config(state='disabled', bg='#D4A5A5')
        self.search_entry.focus_set()
        
        # إخفاء شريط التصنيف وشريط التمرير
        self.toggle_category_and_scroll(False)
        # إعادة تعيين نصوص التصنيف
        self.category_icon.config(text="", fg='black')
        self.category_label.config(text="", fg='black')
        self.category_details_label.config(text="")
        if self.category_progress:
            self.category_progress.destroy()
            self.category_progress = None

        # مسح الملاحظات
        self.notes_text.config(state='normal')
        self.notes_text.delete(1.0, tk.END)
        self.notes_text.config(state='disabled')            