# ui/invoice_preview.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
from PIL import Image, ImageTk

logger = logging.getLogger(__name__)

class InvoicePreview:
    """معاينة الفاتورة قبل الطباعة"""
    
    def __init__(self, parent, invoice_data, user_data):
        self.parent = parent
        self.invoice_data = invoice_data
        self.user_data = user_data
        
        self.create_dialog()
        self.create_widgets()
        
        self.dialog.grab_set()
    
    def create_dialog(self):
        """إنشاء النافذة المنبثقة"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"معاينة الفاتورة - {self.invoice_data.get('invoice_number', '')}")
        self.dialog.geometry("900x700")
        self.dialog.resizable(True, True)
        self.dialog.configure(bg='#f5f7fa')
        
        # مركزية النافذة
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'900x700+{x}+{y}')
    
    def create_widgets(self):
        """إنشاء عناصر المعاينة"""
        # إطار العنوان
        title_frame = tk.Frame(self.dialog, bg='#9b59b6', height=70)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, 
                              text=f"معاينة الفاتورة - {self.invoice_data.get('invoice_number', '')}",
                              font=('Arial', 18, 'bold'),
                              bg='#9b59b6', fg='white')
        title_label.pack(expand=True)
        
        # إطار المحتوى الرئيسي
        main_frame = tk.Frame(self.dialog, bg='#f5f7fa')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # إنشاء عرض الفاتورة
        self.create_invoice_display(main_frame)
        
        # أزرار التحكم
        self.create_buttons(main_frame)
    
    def create_invoice_display(self, parent):
        """إنشاء عرض الفاتورة"""
        # إطار مع تمرير
        canvas = tk.Canvas(parent, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        content_frame = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=content_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # تحديث منطقة التمرير
        content_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # محاكاة تصميم الفاتورة المطبوعة
        self.create_invoice_layout(content_frame)
        
        # تعبئة وإظهار
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def create_invoice_layout(self, parent):
        """إنشاء تخطيط الفاتورة"""
        # عرض المعلومات بشكل مشابه للطباعة
        
        # رأس الفاتورة
        header_frame = tk.Frame(parent, bg='white', relief='solid', borderwidth=2)
        header_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(header_frame, text="شركة الريان للطاقة الكهربائية",
                font=('Arial', 20, 'bold'),
                bg='white', fg='#2c3e50').pack(pady=5)
        
        tk.Label(header_frame, text="فاتورة استهلاك كهرباء",
                font=('Arial', 16),
                bg='white', fg='#2c3e50').pack()
        
        tk.Label(header_frame, text="نسخة المعاينة",
                font=('Arial', 12),
                bg='white', fg='#7f8c8d').pack()
        
        tk.Label(header_frame, 
                text=f"التاريخ: {self.invoice_data.get('payment_date', '')} - الوقت: {self.invoice_data.get('payment_time', '')}",
                font=('Arial', 11),
                bg='white', fg='#34495e').pack(pady=5)
        
        # خط فاصل
        tk.Frame(parent, height=2, bg='#34495e').pack(fill='x', padx=20, pady=10)
        
        # معلومات الزبون
        info_frame = tk.Frame(parent, bg='#f8f9fa', relief='ridge', borderwidth=1)
        info_frame.pack(fill='x', padx=20, pady=10)
        
        customer_info = f"""
        اسم الزبون: {self.invoice_data.get('customer_name', '')}
        القطاع: {self.invoice_data.get('sector_name', '')}
        العلبة: {self.invoice_data.get('box_number', '')} | المسلسل: {self.invoice_data.get('serial_number', '')}
        رقم الدفتر: {self.invoice_data.get('book_number', '')} | رقم الوصل: {self.invoice_data.get('receipt_number', '')}
        """
        
        tk.Label(info_frame, text=customer_info,
                font=('Arial', 11),
                bg='#f8f9fa', fg='#2c3e50',
                justify='left', anchor='w').pack(padx=10, pady=10)
        
        # تفاصيل الدفع
        payment_frame = tk.Frame(parent, bg='white')
        payment_frame.pack(fill='x', padx=20, pady=15)
        
        # جدول تفاصيل الدفع
        details = [
            ("الكمية المدفوعة:", f"{float(self.invoice_data.get('kilowatt_amount', 0)):,.1f} كيلو"),
            ("الكمية المجانية:", f"{float(self.invoice_data.get('free_kilowatt', 0)):,.1f} كيلو"),
            ("الإجمالي المقطوع:", f"{float(self.invoice_data.get('kilowatt_amount', 0)) + float(self.invoice_data.get('free_kilowatt', 0)):,.1f} كيلو"),
            ("سعر الكيلو:", f"{float(self.invoice_data.get('price_per_kilo', 0)):,.0f} ل.س"),
            ("الحسم:", f"{float(self.invoice_data.get('discount', 0)):,.0f} ل.س"),
            ("المبلغ قبل الحسم:", f"{float(self.invoice_data.get('kilowatt_amount', 0)) * float(self.invoice_data.get('price_per_kilo', 0)):,.0f} ل.س")
        ]
        
        for label, value in details:
            row_frame = tk.Frame(payment_frame, bg='white')
            row_frame.pack(fill='x', pady=3)
            
            tk.Label(row_frame, text=label,
                    font=('Arial', 11, 'bold'),
                    bg='white', fg='#2c3e50',
                    width=20, anchor='w').pack(side='left')
            
            tk.Label(row_frame, text=value,
                    font=('Arial', 11),
                    bg='white', fg='#34495e',
                    anchor='w').pack(side='left')
        
        # خط فاصل
        tk.Frame(parent, height=1, bg='#bdc3c7').pack(fill='x', padx=20, pady=10)
        
        # المبلغ الإجمالي
        total_frame = tk.Frame(parent, bg='#2ecc71', relief='solid', borderwidth=2)
        total_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(total_frame, text="المبلغ الإجمالي:",
                font=('Arial', 16, 'bold'),
                bg='#2ecc71', fg='white').pack(pady=5)
        
        tk.Label(total_frame, text=f"{float(self.invoice_data.get('total_amount', 0)):,.0f} ليرة سورية",
                font=('Arial', 20, 'bold'),
                bg='#2ecc71', fg='white').pack(pady=5)
        
        # قراءات العداد
        counter_frame = tk.Frame(parent, bg='#e8f4fc', relief='solid', borderwidth=1)
        counter_frame.pack(fill='x', padx=20, pady=15)
        
        counter_info = f"""
        قراءة العداد:
        • القراءة السابقة: {float(self.invoice_data.get('previous_reading', 0)):,.0f}
        • القراءة الجديدة: {float(self.invoice_data.get('new_reading', 0)):,.0f}
        • الكمية المقطوعة: {float(self.invoice_data.get('kilowatt_amount', 0)) + float(self.invoice_data.get('free_kilowatt', 0)):,.1f} كيلو
        • الرصيد الجديد: {float(self.invoice_data.get('current_balance', 0)):,.0f} ل.س
        """
        
        tk.Label(counter_frame, text=counter_info,
                font=('Arial', 11),
                bg='#e8f4fc', fg='#2c3e50',
                justify='left', anchor='w').pack(padx=10, pady=10)
        
        # معلومات إضافية
        if self.invoice_data.get('visa_application') or self.invoice_data.get('customer_withdrawal'):
            extra_frame = tk.Frame(parent, bg='#fff9e6', relief='solid', borderwidth=1)
            extra_frame.pack(fill='x', padx=20, pady=10)
            
            extra_info = []
            if self.invoice_data.get('visa_application'):
                extra_info.append(f"تنزيل تأشيرة: {self.invoice_data.get('visa_application')}")
            if self.invoice_data.get('customer_withdrawal'):
                extra_info.append(f"سحب المشترك: {self.invoice_data.get('customer_withdrawal')}")
            if self.invoice_data.get('telegram_password'):
                extra_info.append(f"كود التيليغرام: {self.invoice_data.get('telegram_password')}")
            
            if extra_info:
                tk.Label(extra_frame, text="\n".join(extra_info),
                        font=('Arial', 10),
                        bg='#fff9e6', fg='#d35400',
                        justify='left', anchor='w').pack(padx=10, pady=10)
        
        # تذييل الفاتورة
        footer_frame = tk.Frame(parent, bg='#f5f5f5', relief='solid', borderwidth=1)
        footer_frame.pack(fill='x', padx=20, pady=15)
        
        footer_text = f"""
        المحاسب: {self.invoice_data.get('accountant_name', '')}
        هاتف: 0952411882
        أرضي: 310344
        
        ملاحظة: لسنا مسؤولين عن الأعطال التي تصيب الأجهزة الكهربائية
        """
        
        tk.Label(footer_frame, text=footer_text,
                font=('Arial', 10),
                bg='#f5f5f5', fg='#7f8c8d',
                justify='center').pack(padx=10, pady=10)
    
    def create_buttons(self, parent):
        """إنشاء أزرار التحكم"""
        buttons_frame = tk.Frame(parent, bg='#f5f7fa')
        buttons_frame.pack(fill='x', pady=20)
        
        # زر الطباعة
        print_btn = tk.Button(buttons_frame, text="🖨️ طباعة الفاتورة",
                             command=self.print_invoice,
                             bg='#3498db', fg='white',
                             font=('Arial', 12, 'bold'),
                             padx=30, pady=10, cursor='hand2')
        print_btn.pack(side='right', padx=10)
        
        # زر الطباعة بدون رصيد
        print_no_balance_btn = tk.Button(buttons_frame, text="🖨️ طباعة بدون رصيد",
                                       command=self.print_without_balance,
                                       bg='#9b59b6', fg='white',
                                       font=('Arial', 12),
                                       padx=20, pady=10, cursor='hand2')
        print_no_balance_btn.pack(side='right', padx=10)
        
        # زر الإغلاق
        close_btn = tk.Button(buttons_frame, text="إغلاق",
                             command=self.dialog.destroy,
                             bg='#95a5a6', fg='white',
                             font=('Arial', 12),
                             padx=30, pady=10, cursor='hand2')
        close_btn.pack(side='left', padx=10)
    
    def print_invoice(self):
        """طباعة الفاتورة"""
        try:
            from utils.printer import InvoicePrinter
            printer = InvoicePrinter()
            
            if printer.print_invoice(self.invoice_data):
                messagebox.showinfo("نجاح", "تم إرسال الفاتورة للطابعة بنجاح")
            else:
                messagebox.showerror("خطأ", "فشل إرسال الفاتورة للطابعة")
                
        except Exception as e:
            logger.error(f"خطأ في الطباعة: {e}")
            messagebox.showerror("خطأ", f"فشل الطباعة: {str(e)}")
    
    def print_without_balance(self):
        """طباعة الفاتورة بدون عرض الرصيد"""
        try:
            # نسخ بيانات الفاتورة
            invoice_copy = self.invoice_data.copy()
            invoice_copy['current_balance'] = 0  # إخفاء الرصيد
            
            from utils.printer import InvoicePrinter
            printer = InvoicePrinter()
            
            if printer.print_invoice(invoice_copy):
                messagebox.showinfo("نجاح", "تم طباعة الفاتورة بدون رصيد")
            else:
                messagebox.showerror("خطأ", "فشل الطباعة")
                
        except Exception as e:
            logger.error(f"خطأ في الطباعة بدون رصيد: {e}")
            messagebox.showerror("خطأ", f"فشل الطباعة: {str(e)}")