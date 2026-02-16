# utils/printer.py
import logging
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class InvoicePrinter:
    """نظام طباعة الفواتير المحسن"""
    
    def __init__(self):
        self.paper_width = 570
        self.margin = 10
        
        # تحميل الخطوط
        self.load_fonts()
    
    def load_fonts(self):
        """تحميل الخطوط"""
        try:
            # محاولة تحميل الخطوط من مجلد fonts
            fonts_path = "fonts"
            if os.path.exists(fonts_path):
                self.font_title = ImageFont.truetype(os.path.join(fonts_path, "arial.ttf"), 36)
                self.font_normal = ImageFont.truetype(os.path.join(fonts_path, "arial.ttf"), 28)
                self.font_bold = ImageFont.truetype(os.path.join(fonts_path, "arialbd.ttf"), 30)
                self.font_small = ImageFont.truetype(os.path.join(fonts_path, "arial.ttf"), 24)
            else:
                # استخدام الخط الافتراضي
                self.font_title = ImageFont.load_default()
                self.font_normal = self.font_title
                self.font_bold = self.font_title
                self.font_small = self.font_title
        except:
            # في حالة فشل تحميل الخطوط
            default_font = ImageFont.load_default()
            self.font_title = default_font
            self.font_normal = default_font
            self.font_bold = default_font
            self.font_small = default_font
    
    def process_text(self, text):
        """معالجة النص العربي"""
        if not text:
            return ""
        try:
            reshaped_text = arabic_reshaper.reshape(str(text))
            return get_display(reshaped_text)
        except:
            return str(text)
    
    def create_invoice_image(self, invoice_data, copy_name="نسخة المشترك"):
        """إنشاء صورة الفاتورة للطباعة"""
        try:
            # ارتفاع الصورة (سيتم تعديله لاحقاً)
            img_height = 2000
            img = Image.new("RGB", (self.paper_width, img_height), "white")
            draw = ImageDraw.Draw(img)
            
            y = 20  # نقطة البداية
            
            # 1. الترويسة
            title = self.process_text("شركة الريان للطاقة الكهربائية")
            w_title = draw.textlength(title, font=self.font_title)
            draw.text(((self.paper_width - w_title) / 2, y), title,
                     font=self.font_title, fill="black")
            y += 50
            
            # نوع النسخة
            copy_txt = self.process_text(copy_name)
            w_copy = draw.textlength(copy_txt, font=self.font_bold)
            draw.text(((self.paper_width - w_copy) / 2, y), copy_txt,
                     font=self.font_bold, fill="black")
            y += 45
            
            # التاريخ والوقت
            current_time = datetime.now()
            date_time = self.process_text(f"{current_time.strftime('%Y-%m-%d')}  -  {current_time.strftime('%H:%M')}")
            w_dt = draw.textlength(date_time, font=self.font_normal)
            draw.text(((self.paper_width - w_dt) / 2, y), date_time,
                     font=self.font_normal, fill="#333333")
            y += 40
            
            # خط فاصل
            y = self.draw_separator(draw, y)
            
            # 2. بيانات المشترك
            # الاسم
            name_txt = self.process_text(f"اسم الزبون: {invoice_data.get('customer_name', '')}")
            draw.text((self.paper_width - self.margin - 30, y), name_txt,
                     font=self.font_normal, fill="black", anchor="ra")
            y += 40
            
            # الموقع
            sector_txt = self.process_text(f"الموقع: {invoice_data.get('sector_name', '')}")
            draw.text((self.paper_width - self.margin - 30, y), sector_txt,
                     font=self.font_normal, fill="black", anchor="ra")
            y += 40
            
            # علبة ومسلسل
            box_txt = self.process_text(f"علبة: {invoice_data.get('box_number', '')} - {invoice_data.get('serial_number', '')}")
            draw.text((self.paper_width - self.margin - 30, y), box_txt,
                     font=self.font_normal, fill="black", anchor="ra")
            y += 45
            
            # [رقم الفاتورة]{dir="rtl"}
            invoice_number = invoice_data.get('invoice_number', '')
            if invoice_number:
                invoice_text = self.process_text(f"[رقم الفاتورة]: {invoice_number}")
                w_inv = draw.textlength(invoice_text, font=self.font_normal)
                draw.text(((self.paper_width - w_inv) / 2, y), invoice_text,
                        font=self.font_normal, fill="black")
                y += 45

            y = self.draw_separator(draw, y)
            y += 10
            
            # 3. جدول نهايات العداد
            table_y_start = y
            table_height = 85
            
            # إطار الجدول
            draw.rectangle([(self.margin, y), (self.paper_width - self.margin, y + table_height)],
                          outline="#333333", width=2)
            
            # خطوط التقسيم
            draw.line([(self.paper_width / 2, y), (self.paper_width / 2, y + table_height)],
                     fill="#333333", width=1)
            draw.line([(self.margin, y + table_height/2), (self.paper_width - self.margin, y + table_height/2)],
                     fill="#333333", width=1)
            
            # قراءة جديدة
            new_reading = float(invoice_data.get('new_reading', 0))
            new_txt = self.process_text(f"قطع جديد: {new_reading:,.0f}")
            draw.text((self.paper_width - 40, y + 20), new_txt,
                     font=self.font_normal, fill="black", anchor="ra")
            
            # قراءة سابقة
            prev_reading = float(invoice_data.get('previous_reading', 0))
            prev_txt = self.process_text(f"قطع سابق: {prev_reading:,.0f}")
            draw.text((self.margin + 40, y + 20), prev_txt,
                     font=self.font_normal, fill="black", anchor="la")
            
            # التأشيرة
            if invoice_data.get('visa_application'):
                visa_txt = self.process_text(f"تأشيرة العداد: {invoice_data.get('visa_application')}")
                draw.text((self.paper_width - 40, y + table_height/2 + 20), visa_txt,
                         font=self.font_normal, fill="black", anchor="ra")
            
            # الرصيد
            balance = float(invoice_data.get('current_balance', 0))
            balance_txt = self.process_text(f"رصيد: {balance:,.0f}")
            draw.text((self.margin + 40, y + table_height/2 + 20), balance_txt,
                     font=self.font_normal, fill="black", anchor="la")
            
            y += table_height + 25
            
            # 4. مستطيل الكمية
            quantity_box_height = 65
            draw.rectangle([(self.margin, y), (self.paper_width - self.margin, y + quantity_box_height)],
                          fill="#f8f8f8", outline="#333333", width=2)
            
            # كمية الدفع
            kilowatt = float(invoice_data.get('kilowatt_amount', 0))
            free_kilowatt = float(invoice_data.get('free_kilowatt', 0))
            total_kilowatt = kilowatt + free_kilowatt
            
            quantity_val = self.process_text(f"{total_kilowatt:,.1f}")
            quantity_lbl = self.process_text("الكمية المقطوعة بالكيلو:")
            
            val_width = draw.textlength(quantity_val, font=self.font_bold)
            lbl_width = draw.textlength(quantity_lbl, font=self.font_normal)
            
            draw.text((self.paper_width - self.margin - 40, y + 15), quantity_lbl,
                     font=self.font_normal, fill="black", anchor="ra")
            draw.text((self.paper_width - self.margin - 150 - lbl_width - 10, y + 15), quantity_val,
                     font=self.font_bold, fill="#333333", anchor="la")
            
            y += quantity_box_height + 15
            
            # 5. جدول الأسعار
            table2_y_start = y
            table2_height = 70
            col_width = (self.paper_width - 2 * self.margin) / 3
            
            # إطار الجدول
            draw.rectangle([(self.margin, y), (self.paper_width - self.margin, y + table2_height)],
                          outline="#666666", width=1)
            
            # خطوط التقسيم
            draw.line([(self.margin + col_width, y), (self.margin + col_width, y + table2_height)],
                     fill="#666666", width=1)
            draw.line([(self.margin + 2*col_width, y), (self.margin + 2*col_width, y + table2_height)],
                     fill="#666666", width=1)
            draw.line([(self.margin, y + table2_height/2), (self.paper_width - self.margin, y + table2_height/2)],
                     fill="#666666", width=1)
            
            # العناوين
            price_header = self.process_text("سعر الكيلو")
            free_header = self.process_text("المجاني")
            discount_header = self.process_text("الحسم")
            
            w_price = draw.textlength(price_header, font=self.font_small)
            w_free = draw.textlength(free_header, font=self.font_small)
            w_discount = draw.textlength(discount_header, font=self.font_small)
            
            draw.text((self.margin + col_width/2 - w_price/2, y + 10), price_header,
                     font=self.font_small, fill="black")
            draw.text((self.margin + col_width + col_width/2 - w_free/2, y + 10), free_header,
                     font=self.font_small, fill="green")
            draw.text((self.margin + 2*col_width + col_width/2 - w_discount/2, y + 10), discount_header,
                     font=self.font_small, fill="blue")
            
            # القيم
            price_per_kilo = float(invoice_data.get('price_per_kilo', 0))
            free_kw = float(invoice_data.get('free_kilowatt', 0))
            discount = float(invoice_data.get('discount', 0))
            
            price_val = self.process_text(f"{price_per_kilo:,.0f}")
            free_val = self.process_text(f"{free_kw:,.1f}")
            discount_val = self.process_text(f"{discount:,.0f}")
            
            w_price_val = draw.textlength(price_val, font=self.font_normal)
            w_free_val = draw.textlength(free_val, font=self.font_normal)
            w_discount_val = draw.textlength(discount_val, font=self.font_normal)
            
            draw.text((self.margin + col_width/2 - w_price_val/2, y + table2_height/2 + 10), price_val,
                     font=self.font_normal, fill="black")
            draw.text((self.margin + col_width + col_width/2 - w_free_val/2, y + table2_height/2 + 10), free_val,
                     font=self.font_normal, fill="green")
            draw.text((self.margin + 2*col_width + col_width/2 - w_discount_val/2, y + table2_height/2 + 10), discount_val,
                     font=self.font_normal, fill="blue")
            
            y += table2_height + 20
            
            y = self.draw_separator(draw, y)
            
            # 6. المبلغ الإجمالي
            total_box_height = 85
            draw.rectangle([(self.margin, y), (self.paper_width - self.margin, y + total_box_height)],
                          fill="black", outline="black", width=2)
            
            total_amount = float(invoice_data.get('total_amount', 0))
            total_lbl = self.process_text("المبلغ المدفوع:")
            total_val = self.process_text(f"{total_amount:,.0f} ل.س")
            
            lbl_width = draw.textlength(total_lbl, font=self.font_bold)
            val_width = draw.textlength(total_val, font=self.font_title)
            
            draw.text(((self.paper_width - lbl_width) / 2, y + 10), total_lbl,
                     font=self.font_bold, fill="white")
            draw.text(((self.paper_width - val_width) / 2, y + 40), total_val,
                     font=self.font_title, fill="white")
            
            y += total_box_height + 20
            
            # 7. الملاحظات
            note_text = self.process_text("لسنا مسؤولين عن الأعطال التي تصيب الأجهزة الكهربائية")
            w_note = draw.textlength(note_text, font=self.font_small)
            draw.text(((self.paper_width - w_note) / 2, y), note_text,
                     font=self.font_small, fill="black")
            y += 35
            
            # 8. التذييل
            # المحاسب
            accountant = invoice_data.get('accountant_name', '')
            if accountant:
                accountant_txt = self.process_text(f"المحاسب: {accountant}")
                draw.text((self.margin + 10, y), accountant_txt,
                         font=self.font_small, fill="black", anchor="la")
            
            # الهاتف
            phone_txt = self.process_text("هاتف: 0952411882")
            w_phone = draw.textlength(phone_txt, font=self.font_small)
            draw.text(((self.paper_width - w_phone) / 2, y), phone_txt,
                     font=self.font_small, fill="black")
            
            # كود التيليغرام
            telegram_pass = invoice_data.get('telegram_password', '')
            if telegram_pass:
                tele_txt = self.process_text(f"كود التيليغرام: {telegram_pass}")
                draw.text((self.paper_width - self.margin - 10, y), tele_txt,
                         font=self.font_small, fill="black", anchor="ra")
            
            y += 40
            
            # قص الصورة للارتفاع الفعلي
            final_img = img.crop((0, 0, self.paper_width, y))
            return final_img
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء صورة الفاتورة: {e}")
            return None
    
    def draw_separator(self, draw, y):
        """رسم خط فاصل"""
        draw.line([(self.margin, y), (self.paper_width - self.margin, y)], fill="black", width=2)
        return y + 15
    
    def print_invoice(self, invoice_data):
        """طباعة الفاتورة"""
        try:
            # إنشاء صورتين (نسختين)
            copies = ["نسخة المشترك", "نسخة الأرشيف"]
            
            for copy_name in copies:
                # إنشاء الصورة
                invoice_image = self.create_invoice_image(invoice_data, copy_name)
                if invoice_image:
                    # حفظ الصورة للمعاينة (للاختبار)
                    if not os.path.exists("prints"):
                        os.makedirs("prints")
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"prints/invoice_{invoice_data.get('invoice_number', '')}_{timestamp}_{copy_name}.png"
                    invoice_image.save(filename)
                    
                    logger.info(f"تم حفظ صورة الفاتورة: {filename}")
                    
                    # هنا سيتم إرسال الصورة للطابعة الفعلية
                    # self.send_to_printer(invoice_image)
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في طباعة الفاتورة: {e}")
            return False
    
    def send_to_printer(self, image):
        """إرسال الصورة للطابعة الفعلية"""
        try:
            # استخدام python-escpos للطباعة على طابعة الشبكة
            from escpos.printer import Network
            
            # اتصال بالطابعة
            printer_ip = "10.10.0.5"  # عنوان IP الطابعة
            printer_port = 9100
            
            p = Network(printer_ip, printer_port, timeout=10)
            
            # تحويل الصورة للطباعة
            p.image(image.convert("1"))
            p.cut()
            p.close()
            
            logger.info(f"تم إرسال الفاتورة للطابعة: {printer_ip}")
            
        except Exception as e:
            logger.error(f"خطأ في إرسال الفاتورة للطابعة: {e}")
            raise