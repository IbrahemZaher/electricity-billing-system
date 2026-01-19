# modules/printing.py

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont
from escpos.printer import Network
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class FastPrinter:
    """طابعة سريعة تشبه الكود البسيط"""
    
    def __init__(self):
        self.config = {
            'ip': '10.10.0.5',
            'port': 9100,
            'timeout': 10,
            'paper_width': 570
        }
        self.printer = None
    
    def connect(self):
        """الاتصال بالطابعة"""
        try:
            self.printer = Network(self.config['ip'], self.config['port'], 
                                 timeout=self.config['timeout'])
            return True
        except Exception as e:
            logger.error(f"خطأ في الاتصال بالطابعة: {e}")
            return False
    
    def print_fast_invoice(self, invoice_data: dict):
        """طباعة فاتورة سريعة"""
        try:
            if not self.printer and not self.connect():
                return False
            
            # معالجة النصوص العربية
            def arabic_text(text):
                if not text:
                    return ""
                reshaped = arabic_reshaper.reshape(str(text))
                return get_display(reshaped)
            
            # بيانات الفاتورة
            company = arabic_text("شركة الريان للطاقة الكهربائية")
            customer = arabic_text(f"الزبون: {invoice_data.get('customer_name', '')}")
            sector = arabic_text(f"القطاع: {invoice_data.get('sector_name', '')}")
            box = arabic_text(f"العلبة: {invoice_data.get('box_number', '')}")
            
            # القراءات
            previous = invoice_data.get('previous_reading', 0)
            new = invoice_data.get('new_reading', 0)
            consumption = invoice_data.get('consumption', 0)
            
            # المبالغ
            price = invoice_data.get('price_per_kilo', 7200)
            total = invoice_data.get('total_amount', 0)
            balance = invoice_data.get('new_balance', 0)

            # الحصول على القيم الجديدة
            kilowatt_amount = invoice_data.get('kilowatt_amount', 0)
            free_kilowatt = invoice_data.get('free_kilowatt', 0)
                
            # الطباعة
            self.printer.set(align='center')
            self.printer.textln(company + "\n")
            
            self.printer.set(align='right')
            self.printer.textln(f"فاتورة كهرباء\n")
            
            self.printer.set(align='right')
            self.printer.textln(f"التاريخ: {datetime.now().strftime('%Y/%m/%d')}\n")
            self.printer.textln(f"الوقت: {datetime.now().strftime('%H:%M:%S')}\n")
            
            self.printer.textln("-" * 32 + "\n")
            
            self.printer.textln(customer + "\n")
            self.printer.textln(sector + "\n")
            self.printer.textln(box + "\n")
            
            if invoice_data.get('serial_number'):
                serial = arabic_text(f"المسلسل: {invoice_data.get('serial_number')}")
                self.printer.textln(serial + "\n")
            
            self.printer.textln("-" * 32 + "\n")
            
            # القراءات
            self.printer.textln(f"القراءة السابقة: {previous:,.0f}\n")
            self.printer.textln(f"القراءة الجديدة: {new:,.0f}\n")
            self.printer.textln(f"الكمية: {consumption:,.1f} كيلو\n")

             # في قسم الكميات
            if free_kilowatt > 0:
                self.printer.textln(f"الكمية المدفوعة: {kilowatt_amount:,.1f} كيلو\n")
                self.printer.textln(f"المجاني: {free_kilowatt:,.1f} كيلو\n")
                self.printer.textln(f"إجمالي القطع: {(kilowatt_amount + free_kilowatt):,.1f} كيلو\n")
            else:
                self.printer.textln(f"الكمية: {kilowatt_amount:,.1f} كيلو\n")
                
            # السعر والمبلغ
            self.printer.textln(f"سعر الكيلو: {price:,.0f} ل.س\n")
            
            if invoice_data.get('discount', 0) > 0:
                discount_text = arabic_text(f"الحسم: {invoice_data.get('discount', 0):,.0f} ل.س")
                self.printer.textln(discount_text + "\n")
            
            self.printer.set(align='center', bold=True)
            self.printer.textln(f"المبلغ الإجمالي: {total:,.0f} ليرة سورية\n")
            
            self.printer.set(align='right', bold=False)
            self.printer.textln(f"الرصيد الجديد: {balance:,.0f}\n")
            
            if invoice_data.get('visa_application'):
                visa = arabic_text(f"تنزيل تأشيرة: {invoice_data.get('visa_application')}")
                self.printer.textln(visa + "\n")
            
            self.printer.textln("-" * 32 + "\n")
            
            # التذييل
            self.printer.set(align='center')
            self.printer.textln("هاتف: 0952411882\n")
            self.printer.textln("لسنا مسؤولين عن الأعطال\n")
            self.printer.textln("التي تصيب الأجهزة الكهربائية\n")
            
            self.printer.textln("\n\n")
            self.printer.cut()
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في الطباعة السريعة: {e}")
            return False
    
    def close(self):
        """إغلاق الاتصال"""
        try:
            if self.printer:
                self.printer.close()
        except:
            pass
