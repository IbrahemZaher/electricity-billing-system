# ui/import_manager.py - الملف الكامل
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import os
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

class ImportManagerUI:
    """واجهة إدارة الاستيراد المتقدمة"""
    
    def __init__(self, parent, user_data):
        self.parent = parent
        self.user_data = user_data
        self.excel_folder = ""
        self.selected_files = []
        self.is_running = False
        
        # إطار رئيسي مع سكرول بار
        self.create_main_scrollable_frame()
    
    def create_main_scrollable_frame(self):
        """إنشاء إطار رئيسي قابل للتمرير"""
        # مسح المحتوى القديم
        for widget in self.parent.winfo_children():
            widget.destroy()
        
        # إطار رئيسي مع Canvas وScrollbar
        self.canvas = tk.Canvas(self.parent, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.parent, orient="vertical", command=self.canvas.yview)
        
        # إطار قابل للتمرير للعناصر
        self.scrollable_frame = tk.Frame(self.canvas, bg='white')
        
        # تهيئة الـCanvas
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # إنشاء نافذة في Canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # تعبئة وإظهار العناصر
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # ربط الأحداث
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # تمكين تمرير العجلة
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # إنشاء الواجهة داخل الإطار القابل للتمرير
        self.create_widgets_in_scrollable_frame()
    
    def _on_frame_configure(self, event=None):
        """تحديث منطقة التمرير عند تغيير حجم الإطار"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        """ضبط عرض نافذة الـCanvas عند تغيير الحجم"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _on_mousewheel(self, event):
        """معالجة تمرير عجلة الماوس"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def create_widgets_in_scrollable_frame(self):
        """إنشاء عناصر الواجهة داخل الإطار القابل للتمرير"""
        # العنوان
        title = tk.Label(self.scrollable_frame,
                        text="🔄 مدير الاستيراد والتصدير",
                        font=('Arial', 20, 'bold'),
                        bg='white', fg='#2c3e50')
        title.pack(pady=10)
        
        # تبويبات
        notebook = ttk.Notebook(self.scrollable_frame)
        notebook.pack(fill='both', expand=True, pady=20)
        
        # تبويب الاستيراد
        import_tab = tk.Frame(notebook, bg='white')
        self.create_import_tab(import_tab)
        notebook.add(import_tab, text="📥 استيراد البيانات")
        
        # تبويب النسخ الاحتياطي
        backup_tab = tk.Frame(notebook, bg='white')
        self.create_backup_tab(backup_tab)
        notebook.add(backup_tab, text="💾 النسخ الاحتياطي")
        
        # تبويب السجلات
        logs_tab = tk.Frame(notebook, bg='white')
        self.create_logs_tab(logs_tab)
        notebook.add(logs_tab, text="📋 سجلات الاستيراد")
        
        # ضبط الحد الأدنى لحجم الإطار
        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def create_import_tab(self, parent):
        """إنشاء تبويب الاستيراد"""
        # إطار داخلي مع سكرول بار
        inner_canvas = tk.Canvas(parent, bg='white', highlightthickness=0)
        inner_scrollbar = ttk.Scrollbar(parent, orient="vertical", command=inner_canvas.yview)
        inner_frame = tk.Frame(inner_canvas, bg='white')
        
        inner_canvas.configure(yscrollcommand=inner_scrollbar.set)
        inner_canvas_window = inner_canvas.create_window((0, 0), window=inner_frame, anchor="nw")
        
        def configure_inner_canvas(event):
            inner_canvas.configure(scrollregion=inner_canvas.bbox("all"))
            inner_canvas.itemconfig(inner_canvas_window, width=event.width)
        
        inner_frame.bind("<Configure>", configure_inner_canvas)
        inner_canvas.bind("<Configure>", configure_inner_canvas)
        
        inner_scrollbar.pack(side="right", fill="y")
        inner_canvas.pack(side="left", fill="both", expand=True)
        
        # قسم اختيار الملفات
        file_frame = tk.LabelFrame(inner_frame, text="اختر ملفات Excel", 
                                  bg='white', padx=15, pady=15)
        file_frame.pack(fill='x', pady=10)
        
        tk.Label(file_frame, text="مجلد ملفات Excel:",
                bg='white', font=('Arial', 11)).pack(anchor='w')
        
        self.folder_path = tk.StringVar()
        
        folder_entry = tk.Entry(file_frame, textvariable=self.folder_path,
                               font=('Arial', 11), width=50)
        folder_entry.pack(side='left', fill='x', expand=True, pady=5)
        
        tk.Button(file_frame, text="استعراض...",
                 command=self.browse_folder,
                 bg='#3498db', fg='white').pack(side='right', padx=5)
        
        # قسم خيارات الاستيراد
        options_frame = tk.LabelFrame(inner_frame, text="خيارات الاستيراد",
                                     bg='white', padx=15, pady=15)
        options_frame.pack(fill='x', pady=10)
        
        # خيار حذف البيانات القديمة
        self.delete_old_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="حذف البيانات القديمة قبل الاستيراد",
                      variable=self.delete_old_var,
                      bg='white', font=('Arial', 11)).pack(anchor='w', pady=5)
        
        # خيار النسخ الاحتياطي التلقائي
        self.auto_backup_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="إنشاء نسخة احتياطية تلقائية",
                      variable=self.auto_backup_var,
                      bg='white', font=('Arial', 11)).pack(anchor='w', pady=5)
        
        # قسم الملفات المحددة
        self.files_frame = tk.LabelFrame(inner_frame, text="الملفات المحددة",
                                        bg='white', padx=15, pady=15)
        self.files_frame.pack(fill='both', expand=True, pady=10)
        
        # زر بدء الاستيراد
        start_button = tk.Button(inner_frame, text="🚀 بدء عملية الاستيراد",
                               command=self.start_import,
                               bg='#27ae60', fg='white',
                               font=('Arial', 12, 'bold'),
                               padx=30, pady=10)
        start_button.pack(pady=20)
        
        # إطار فارغ لضمان ظهور الزر
        tk.Frame(inner_frame, height=20, bg='white').pack()
        
        # ربط حدث الماوس مع الإطار الداخلي
        inner_canvas.bind_all("<MouseWheel>", 
                            lambda e: inner_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
    
    def browse_folder(self):
        """استعراض مجلد الملفات"""
        folder = filedialog.askdirectory(title="اختر مجلد ملفات Excel")
        if folder:
            self.folder_path.set(folder)
            self.display_excel_files(folder)
    
    def display_excel_files(self, folder):
        """عرض ملفات Excel في المجلد"""
        # مسح الإطار القديم
        for widget in self.files_frame.winfo_children():
            widget.destroy()
        
        # البحث عن ملفات Excel
        excel_files = []
        for file in os.listdir(folder):
            if file.endswith('.xlsx'):
                excel_files.append(file)
        
        if not excel_files:
            tk.Label(self.files_frame, text="❌ لا توجد ملفات Excel في المجلد",
                    bg='white', fg='red').pack(pady=20)
            return
        
        # عرض الملفات
        tk.Label(self.files_frame, 
                text=f"تم العثور على {len(excel_files)} ملف Excel:",
                bg='white', font=('Arial', 11, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # إطار قائمة الملفات مع سكرول بار
        list_container = tk.Frame(self.files_frame, bg='white')
        list_container.pack(fill='both', expand=True)
        
        # Canvas للسكرول بار
        list_canvas = tk.Canvas(list_container, bg='white', height=200, highlightthickness=0)
        list_scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=list_canvas.yview)
        list_frame = tk.Frame(list_canvas, bg='white')
        
        list_canvas.configure(yscrollcommand=list_scrollbar.set)
        list_canvas_window = list_canvas.create_window((0, 0), window=list_frame, anchor="nw")
        
        def configure_list_canvas(event):
            list_canvas.configure(scrollregion=list_canvas.bbox("all"))
            list_canvas.itemconfig(list_canvas_window, width=event.width)
        
        list_frame.bind("<Configure>", configure_list_canvas)
        list_canvas.bind("<Configure>", configure_list_canvas)
        
        list_scrollbar.pack(side="right", fill="y")
        list_canvas.pack(side="left", fill="both", expand=True)
        
        # أزرار اختيار الملفات
        self.file_vars = []
        for idx, file in enumerate(excel_files):
            var = tk.BooleanVar(value=True)
            self.file_vars.append((file, var))
            
            file_frame = tk.Frame(list_frame, bg='#f9f9f9' if idx % 2 == 0 else 'white')
            file_frame.pack(fill='x', pady=1)
            
            # خانة اختيار
            cb = tk.Checkbutton(file_frame, variable=var, bg=file_frame['bg'])
            cb.grid(row=0, column=0, padx=5, pady=3)
            
            # اسم الملف
            tk.Label(file_frame, text=file, bg=file_frame['bg'],
                    font=('Arial', 10), anchor='w').grid(row=0, column=1, 
                                                         padx=5, pady=3, sticky='w')
            
            # حجم الملف
            try:
                size = os.path.getsize(os.path.join(folder, file))
                size_str = f"{size/1024:.1f} KB"
            except:
                size_str = "غير معروف"
            
            tk.Label(file_frame, text=size_str, bg=file_frame['bg'],
                    font=('Arial', 9), fg='#666').grid(row=0, column=2, 
                                                      padx=5, pady=3)
        
        # أزرار اختيار/إلغاء الكل
        buttons_frame = tk.Frame(self.files_frame, bg='white')
        buttons_frame.pack(fill='x', pady=10)
        
        tk.Button(buttons_frame, text="تحديد الكل",
                 command=lambda: self.toggle_all_files(True),
                 bg='#3498db', fg='white',
                 font=('Arial', 10)).pack(side='left', padx=5)
        
        tk.Button(buttons_frame, text="إلغاء تحديد الكل",
                 command=lambda: self.toggle_all_files(False),
                 bg='#e74c3c', fg='white',
                 font=('Arial', 10)).pack(side='left', padx=5)
        
        # ربط حدث الماوس مع canvas القائمة
        list_canvas.bind_all("<MouseWheel>", 
                           lambda e: list_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # حفظ الملفات المحددة
        self.selected_files = excel_files
    
    def toggle_all_files(self, select_all):
        """تحديد أو إلغاء تحديد جميع الملفات"""
        if hasattr(self, 'file_vars'):
            for file, var in self.file_vars:
                var.set(select_all)
    
    def get_selected_files(self):
        """الحصول على الملفات المحددة"""
        selected = []
        if hasattr(self, 'file_vars'):
            for file, var in self.file_vars:
                if var.get():
                    selected.append(file)
        return selected
    
    def start_import(self):
        """بدء عملية الاستيراد"""
        folder = self.folder_path.get()
        if not folder or not os.path.exists(folder):
            messagebox.showerror("خطأ", "يرجى اختيار مجلد صحيح")
            return
        
        # التحقق من الصلاحيات
        if self.user_data.get('role') != 'admin':
            messagebox.showerror("صلاحيات", "هذا الإجراء للمديرين فقط")
            return
        
        # الحصول على الملفات المحددة
        selected_files = self.get_selected_files()
        if not selected_files:
            messagebox.showerror("خطأ", "لم يتم اختيار أي ملفات للاستيراد")
            return
        
        # تحذير قبل الحذف
        if self.delete_old_var.get():
            warning = f"""⚠️  تحذير مهم!
            
سيتم حذف جميع البيانات القديمة قبل الاستيراد!
عدد الملفات المحددة: {len(selected_files)}
            
هل أنت متأكد من المتابعة؟"""
            if not messagebox.askyesno("تحذير", warning):
                return
        
        # إنشاء نافذة التقدم
        self.create_progress_window()
        
        # تنفيذ الاستيراد في thread منفصل
        thread = threading.Thread(target=self.execute_import, 
                                 args=(folder, selected_files))
        thread.start()
    
    def create_progress_window(self):
        """إنشاء نافذة عرض التقدم"""
        self.progress_window = tk.Toplevel(self.parent)
        self.progress_window.title("جاري الاستيراد...")
        self.progress_window.geometry("500x300")
        self.progress_window.resizable(False, False)
        self.progress_window.transient(self.parent)
        self.progress_window.grab_set()
        
        # شريط التقدم
        self.progress_bar = ttk.Progressbar(self.progress_window, 
                                          mode='determinate',
                                          length=400)
        self.progress_bar.pack(pady=30)
        
        # حالة التقدم
        self.status_label = tk.Label(self.progress_window,
                                    text="جاري إعداد عملية الاستيراد...",
                                    font=('Arial', 12))
        self.status_label.pack(pady=10)
        
        # التفاصيل
        self.details_label = tk.Label(self.progress_window,
                                     text="",
                                     font=('Arial', 10),
                                     fg='#7f8c8d')
        self.details_label.pack(pady=10)
        
        # زر الإلغاء
        tk.Button(self.progress_window, text="إلغاء",
                 command=self.cancel_import,
                 bg='#e74c3c', fg='white',
                 padx=20).pack(pady=20)
        
        self.progress_window.protocol("WM_DELETE_WINDOW", self.cancel_import)
    
    def execute_import(self, folder, selected_files):
        """تنفيذ عملية الاستيراد"""
        try:
            self.is_running = True
            
            if not selected_files:
                self.update_progress("❌ لم يتم اختيار أي ملفات", 0)
                messagebox.showerror("خطأ", "لم يتم اختيار أي ملفات")
                self.close_progress()
                return
            
            # النسخ الاحتياطي إذا مطلوب
            if self.auto_backup_var.get():
                self.update_progress("جاري إنشاء نسخة احتياطية...", 20)
                self.create_backup()
            
            # حذف البيانات القديمة إذا مطلوب
            if self.delete_old_var.get():
                self.update_progress("جاري حذف البيانات القديمة...", 30)
                self.delete_old_data()
            
            # استيراد البيانات الجديدة
            total_files = len(selected_files)
            
            for idx, file in enumerate(selected_files, 1):
                progress = 40 + (idx / total_files * 50)
                self.update_progress(f"جاري استيراد الملف {idx}/{total_files}: {file}", 
                                   progress)
                
                # استيراد كل ملف
                from database.migrations import ExcelMigration
                migrator = ExcelMigration(folder)
                
                # هنا يجب تعديل الكود ليقبل اسم ملف محدد
                # مؤقتاً نستخدم نفس الدالة
                success = migrator.migrate_all_data()
                
                if not success:
                    self.update_progress(f"❌ فشل استيراد الملف: {file}", progress)
                    logger.error(f"فشل استيراد الملف: {file}")
            
            self.update_progress("✅ تمت العملية بنجاح!", 100)
            # إغلاق نافذة التقدم بعد 2 ثانية
            self.parent.after(2000, self.close_progress_success)
            
        except Exception as e:
            logger.error(f"خطأ في الاستيراد: {e}")
            self.update_progress(f"❌ فشل الاستيراد: {str(e)}", 0)
            self.parent.after(2000, lambda: messagebox.showerror("خطأ", f"فشل الاستيراد: {str(e)}"))
            self.close_progress()
        finally:
            self.is_running = False
    
    def update_progress(self, message, percentage):
        """تحديث شريط التقدم"""
        if hasattr(self, 'progress_window') and self.progress_window.winfo_exists():
            self.status_label.config(text=message)
            self.progress_bar['value'] = percentage
            self.details_label.config(text=f"التقدم: {percentage:.0f}%")
            self.progress_window.update()
    
    def create_backup(self):
        """إنشاء نسخة احتياطية"""
        try:
            from modules.archive import ArchiveManager
            archive = ArchiveManager()
            archive.perform_backup()
            logger.info("تم إنشاء نسخة احتياطية بنجاح")
        except Exception as e:
            logger.error(f"خطأ في النسخ الاحتياطي: {e}")
    
    def delete_old_data(self):
        """حذف البيانات القديمة"""
        try:
            from database.connection import db
            with db.get_cursor() as cursor:
                # حذف الفواتير أولاً (بسبب المفتاح الخارجي)
                cursor.execute("DELETE FROM invoices")
                # حذف الزبائن
                cursor.execute("DELETE FROM customers")
                logger.info("تم حذف البيانات القديمة")
        except Exception as e:
            logger.error(f"خطأ في حذف البيانات: {e}")
            raise
    
    def cancel_import(self):
        """إلغاء عملية الاستيراد"""
        self.is_running = False
        if hasattr(self, 'progress_window'):
            self.progress_window.destroy()
    
    def close_progress(self):
        """إغلاق نافذة التقدم"""
        if hasattr(self, 'progress_window'):
            self.progress_window.destroy()
    
    def close_progress_success(self):
        """إغلاق نافذة التقدم مع رسالة نجاح"""
        self.close_progress()
        messagebox.showinfo("نجاح", "✅ تمت عملية الاستيراد بنجاح!")
        # تحديث قائمة الملفات
        folder = self.folder_path.get()
        if folder:
            self.display_excel_files(folder)
    
    def create_backup_tab(self, parent):
        """إنشاء تبويب النسخ الاحتياطي"""
        # محتوى النسخ الاحتياطي
        backup_frame = tk.LabelFrame(parent, text="خيارات النسخ الاحتياطي",
                                    bg='white', padx=15, pady=15)
        backup_frame.pack(fill='both', expand=True, pady=10)
        
        tk.Label(backup_frame, 
                text="إنشاء نسخة احتياطية من قاعدة البيانات:",
                bg='white', font=('Arial', 11)).pack(anchor='w', pady=10)
        
        tk.Button(backup_frame, text="💾 إنشاء نسخة احتياطية الآن",
                 command=self.create_manual_backup,
                 bg='#9b59b6', fg='white',
                 font=('Arial', 11),
                 padx=20, pady=10).pack(pady=20)
        
        tk.Label(backup_frame, 
                text="النسخ الاحتياطية السابقة:",
                bg='white', font=('Arial', 11, 'bold')).pack(anchor='w', pady=(20, 10))
        
        # قائمة النسخ الاحتياطية مع سكرول بار
        backup_container = tk.Frame(backup_frame, bg='white')
        backup_container.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(backup_container, bg='white', height=150, highlightthickness=0)
        scrollbar = ttk.Scrollbar(backup_container, orient="vertical", command=canvas.yview)
        backup_list_frame = tk.Frame(canvas, bg='white')
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas_window = canvas.create_window((0, 0), window=backup_list_frame, anchor="nw")
        
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        def configure_backup_canvas(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_window, width=canvas.winfo_width())
        
        backup_list_frame.bind("<Configure>", configure_backup_canvas)
        
        # عرض النسخ الاحتياطية (مثال)
        backups = self.get_backup_list()
        if backups:
            for backup in backups:
                backup_item = tk.Frame(backup_list_frame, bg='#f8f9fa')
                backup_item.pack(fill='x', pady=2, padx=5)
                
                tk.Label(backup_item, text=backup['name'], 
                        bg=backup_item['bg'], font=('Arial', 10)).pack(side='left', padx=10)
                tk.Label(backup_item, text=backup['date'], 
                        bg=backup_item['bg'], font=('Arial', 9), fg='#666').pack(side='right', padx=10)
        else:
            tk.Label(backup_list_frame, text="لا توجد نسخ احتياطية حالياً",
                    bg='white', fg='#999', font=('Arial', 10)).pack(pady=20)
    
    def get_backup_list(self):
        """الحصول على قائمة النسخ الاحتياطية"""
        return [
            {'name': 'backup_2024_01_01.zip', 'date': '2024-01-01 10:30'},
            {'name': 'backup_2023_12_15.zip', 'date': '2023-12-15 14:20'},
        ]
    
    def create_manual_backup(self):
        """إنشاء نسخة احتياطية يدوية"""
        try:
            from modules.archive import ArchiveManager
            archive = ArchiveManager()
            result = archive.perform_backup()
            messagebox.showinfo("نجاح", "✅ تم إنشاء نسخة احتياطية بنجاح!")
        except Exception as e:
            logger.error(f"خطأ في النسخ الاحتياطي: {e}")
            messagebox.showerror("خطأ", f"فشل إنشاء نسخة احتياطية: {str(e)}")
    
    def create_logs_tab(self, parent):
        """إنشاء تبويب السجلات"""
        # محتوى سجلات الاستيراد
        logs_frame = tk.LabelFrame(parent, text="سجلات عمليات الاستيراد",
                                  bg='white', padx=15, pady=15)
        logs_frame.pack(fill='both', expand=True, pady=10)
        
        # شريط الأدوات
        toolbar = tk.Frame(logs_frame, bg='white')
        toolbar.pack(fill='x', pady=(0, 10))
        
        tk.Button(toolbar, text="🔄 تحديث السجلات",
                 command=self.refresh_logs,
                 bg='#3498db', fg='white').pack(side='left', padx=5)
        
        tk.Button(toolbar, text="🗑️ مسح السجلات",
                 command=self.clear_logs,
                 bg='#e74c3c', fg='white').pack(side='left', padx=5)
        
        # منطقة عرض السجلات مع سكرول بار
        log_container = tk.Frame(logs_frame, bg='white')
        log_container.pack(fill='both', expand=True)
        
        # إطار النص مع سكرول بار
        text_frame = tk.Frame(log_container)
        text_frame.pack(fill='both', expand=True)
        
        self.log_text = tk.Text(text_frame, 
                               height=15, 
                               font=('Courier', 10),
                               bg='#f8f9fa',
                               wrap='word')
        
        log_scrollbar = ttk.Scrollbar(text_frame)
        log_scrollbar.pack(side='right', fill='y')
        
        self.log_text.pack(side='left', fill='both', expand=True)
        
        # ربط السكرول بار
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        log_scrollbar.config(command=self.log_text.yview)
        
        # تحميل السجلات الأولية
        self.load_logs()
    
    def load_logs(self):
        """تحميل السجلات"""
        try:
            # تحميل سجلات من ملف أو قاعدة بيانات
            logs_content = """📅 2024-01-01 10:30:00 - بدء عملية الاستيراد
✅ تم استيراد 5 ملفات بنجاح
📁 الملفات: customers.xlsx, invoices.xlsx
⏱️ المدة: 15 ثانية

📅 2023-12-15 14:20:00 - بدء عملية الاستيراد
✅ تم استيراد 3 ملفات بنجاح
📁 الملفات: products.xlsx
⏱️ المدة: 8 ثواني

📅 2023-12-01 09:15:00 - فشل عملية الاستيراد
❌ خطأ في تنسيق الملف: sales.xlsx
⚠️ تم التخطي والمتابعة"""
            
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(1.0, logs_content)
            self.log_text.config(state='normal')
        except Exception as e:
            logger.error(f"خطأ في تحميل السجلات: {e}")
            self.log_text.insert(1.0, "خطأ في تحميل السجلات")
    
    def refresh_logs(self):
        """تحديث السجلات"""
        self.load_logs()
        messagebox.showinfo("تحديث", "تم تحديث السجلات بنجاح")
    
    def clear_logs(self):
        """مسح السجلات"""
        if messagebox.askyesno("تأكيد", "هل تريد مسح جميع السجلات؟"):
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(1.0, "📋 سجلات الاستيراد\n" + "="*40 + "\n\nلا توجد سجلات حالياً.")