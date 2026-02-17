# modules/printing.py

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont
from escpos.printer import Network
import logging
from datetime import datetime
import os
import sys

logger = logging.getLogger(__name__)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class FastPrinter:
    """طابعة سريعة تستخدم الصور لطباعة الفواتير بالعربية بشكل صحيح"""
    
    def __init__(self):
        self.config = {
            'ip': '10.10.0.4',
            'port': 9100,
            'timeout': 10,
            'paper_width': 570
        }
        self.printer = None
        self.font_regular = None
        self.font_bold = None
        self._load_fonts()
    
    def _load_fonts(self):
        # مسارات ممكنة للخطوط
        regular_paths = [
            resource_path("fonts/arial.ttf"),
            resource_path("fonts/DejaVuSans.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
        ]
        bold_paths = [
            resource_path("fonts/DejaVuSans-Bold.ttf"),
            resource_path("fonts/arialbd.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf",
        ]
        
        for path in regular_paths:
            try:
                self.font_regular = ImageFont.truetype(path, 32)
                break
            except:
                continue
        
        for path in bold_paths:
            try:
                self.font_bold = ImageFont.truetype(path, 32)
                break
            except:
                continue
        
        if self.font_regular is None:
            self.font_regular = ImageFont.load_default()
        if self.font_bold is None:
            self.font_bold = self.font_regular
    
    def connect(self):
        try:
            self.printer = Network(self.config['ip'], self.config['port'], 
                                 timeout=self.config['timeout'])
            return True
        except Exception as e:
            logger.error(f"خطأ في الاتصال بالطابعة: {e}")
            return False
    
    def _arabic(self, text):
        if not text:
            return ""
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    
    def print_fast_invoice(self, invoice_data: dict):
        """
        طباعة فاتورة بتصميم متطور باستخدام البيانات المحسوبة مسبقاً
        - تم إضافة صندوق منفصل للرصيد الحالي
        - تم استبدال الرصيد في الجدول 2×2 بقيمة السحب (إن وجدت)
        """
        try:
            if not self.printer and not self.connect():
                return False

            # استخراج البيانات من المدخلات
            data = {
                'customer_name': invoice_data.get('customer_name', ''),
                'sector_name': invoice_data.get('sector_name', ''),
                'box_number': invoice_data.get('box_number', ''),
                'serial_number': invoice_data.get('serial_number', ''),
                'previous_reading': invoice_data.get('previous_reading', 0),
                'new_reading': invoice_data.get('new_reading', 0),
                'kilowatt_amount': invoice_data.get('kilowatt_amount', 0),
                'free_kilowatt': invoice_data.get('free_kilowatt', 0),
                'consumption': invoice_data.get('consumption', 
                                               invoice_data.get('kilowatt_amount', 0) + invoice_data.get('free_kilowatt', 0)),
                'price_per_kilo': invoice_data.get('price_per_kilo', 7200),
                'discount': invoice_data.get('discount', 0),
                'total_amount': invoice_data.get('total_amount', 0),
                'new_balance': invoice_data.get('new_balance', 0),
                'invoice_number': invoice_data.get('invoice_number', ''),
                'visa_application': invoice_data.get('visa_application', ''),
                'withdrawal_amount': invoice_data.get('withdrawal_amount', 0),  # القيمة المضافة (السحب)
                'accountant_name': invoice_data.get('accountant_name', 'محاسب'),
            }
            
            now = datetime.now()
            data['date'] = now.strftime('%Y-%m-%d')
            data['time'] = now.strftime('%H:%M:%S')
            data['receipt_book'] = f"دفتر{now.strftime('%m%Y')}"

            # دوال مساعدة
            def ar(text):
                return self._arabic(text)

            def get_font(size, bold=False):
                try:
                    if bold:
                        if self.font_bold:
                            return ImageFont.truetype(self.font_bold.path, size)
                    else:
                        if self.font_regular:
                            return ImageFont.truetype(self.font_regular.path, size)
                except:
                    pass
                return ImageFont.load_default()

            # إعدادات القياسات
            PAPER_WIDTH = self.config['paper_width']
            MARGIN = 10
            img_height = 1700  # ارتفاع مؤقت
            img = Image.new("RGB", (PAPER_WIDTH, img_height), "white")
            draw = ImageDraw.Draw(img)
            y = 20

            # 1. الترويسة (بدون تغيير)
            title = ar("شركة الريان للطاقة الكهربائية")
            font_title = get_font(36, bold=True)
            w_title = draw.textlength(title, font=font_title)
            draw.text(((PAPER_WIDTH - w_title) / 2, y), title,
                    font=font_title, fill="black")
            y += 50

            copy_txt = ar("فاتورة كهرباء")
            font_copy = get_font(26)
            w_copy = draw.textlength(copy_txt, font=font_copy)
            draw.text(((PAPER_WIDTH - w_copy) / 2, y), copy_txt,
                    font=font_copy, fill="black")
            y += 45

            date_time = ar(f"{data['date']}  -  {data['time']}")
            w_dt = draw.textlength(date_time, font=font_copy)
            draw.text(((PAPER_WIDTH - w_dt) / 2, y), date_time,
                    font=font_copy, fill="#333333")
            y += 40

            draw.line([(MARGIN, y), (PAPER_WIDTH - MARGIN, y)], fill="black", width=2)
            y += 15

            # 2. بيانات المشترك
            font_value = get_font(28)
            name_txt = ar(f"اسم الزبون: {data['customer_name']}")
            draw.text((PAPER_WIDTH - MARGIN - 30, y), name_txt,
                    font=font_value, fill="black", anchor="ra")
            y += 40

            sector_txt = ar(f"القطاع: {data['sector_name']}")
            draw.text((PAPER_WIDTH - MARGIN - 30, y), sector_txt,
                    font=font_value, fill="black", anchor="ra")
            y += 40

            box_txt = ar(f"علبة: {data['box_number']} - {data['serial_number']}")
            draw.text((PAPER_WIDTH - MARGIN - 30, y), box_txt, font=font_value, fill="black", anchor="ra")
            y += 45

            if data.get('invoice_number'):
                receipt_text = ar(f"رقم الفاتورة: {data['invoice_number']}")
                w_br = draw.textlength(receipt_text, font=font_value)
                draw.text(((PAPER_WIDTH - w_br) / 2, y), receipt_text, font=font_value, fill="black")
                y += 45
            else:
                y += 10

            draw.line([(MARGIN, y), (PAPER_WIDTH - MARGIN, y)], fill="black", width=2)
            y += 15

            # 3. جدول 2×2 للقراءات والسحب/التأشيرة
            table_height = 85
            draw.rectangle([(MARGIN, y), (PAPER_WIDTH - MARGIN, y + table_height)],
                        outline="#333333", width=2)
            draw.line([(PAPER_WIDTH / 2, y), (PAPER_WIDTH / 2, y + table_height)],
                    fill="#333333", width=1)
            draw.line([(MARGIN, y + table_height/2), (PAPER_WIDTH - MARGIN, y + table_height/2)],
                    fill="#333333", width=1)

            # دالة مساعدة لوضع النص في منتصف الخلية
            def draw_in_cell(text, x_left, x_right, y_top, y_bottom, font, fill="black"):
                """رسم النص في منتصف الخلية المحددة"""
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x_center = (x_left + x_right) / 2
                y_center = (y_top + y_bottom) / 2
                draw.text((x_center - text_width/2, y_center - text_height/2), text, font=font, fill=fill)

            # الخانة العلوية اليسرى: قراءة سابقة
            prev_txt = ar(f"قطع سابق: {data['previous_reading']:,.0f}")
            draw_in_cell(prev_txt, MARGIN, PAPER_WIDTH/2, y, y + table_height/2, get_font(26))

            # الخانة العلوية اليمنى: قراءة جديدة
            new_txt = ar(f"قطع جديد: {data['new_reading']:,.0f}")
            draw_in_cell(new_txt, PAPER_WIDTH/2, PAPER_WIDTH - MARGIN, y, y + table_height/2, get_font(26))

            # الخانة السفلية اليسرى: السحب
            withdrawal_txt = ar(f"سحب: {data['withdrawal_amount']:,.0f}")
            draw_in_cell(withdrawal_txt, MARGIN, PAPER_WIDTH/2, y + table_height/2, y + table_height, get_font(26))

            # الخانة السفلية اليمنى: تأشيرة
            visa_value = data.get('visa_application', 0)
            try:
                visa_float = float(visa_value)
                visa_display = f"{visa_float:,.0f}"
            except:
                visa_display = str(visa_value)
            visa_txt = ar(f"تأشيرة: {visa_display}")
            draw_in_cell(visa_txt, PAPER_WIDTH/2, PAPER_WIDTH - MARGIN, y + table_height/2, y + table_height, get_font(26))

            y += table_height + 25
            # 4. صندوق الرصيد الحالي (مستطيل منفصل)
            balance_box_height = 65
            draw.rectangle([(MARGIN, y), (PAPER_WIDTH - MARGIN, y + balance_box_height)],
                        fill="#f8f8f8", outline="#333333", width=2)
            balance_lbl = ar("الرصيد الحالي (ك.واط):")
            balance_val = ar(f"{data['new_balance']:,.0f}")
            font_balance_lbl = get_font(26)
            font_balance_val = get_font(32, bold=True)
            lbl_width = draw.textlength(balance_lbl, font=font_balance_lbl)
            draw.text((PAPER_WIDTH - MARGIN - 40, y + 15), balance_lbl,
                    font=font_balance_lbl, fill="black", anchor="ra")
            draw.text((PAPER_WIDTH - MARGIN - 150 - lbl_width - 10, y + 15), balance_val,
                    font=font_balance_val, fill="#333333", anchor="la")
            y += balance_box_height + 15

            # 5. صندوق الكمية (يبقى كما هو)
            quantity_box_height = 65
            draw.rectangle([(MARGIN, y), (PAPER_WIDTH - MARGIN, y + quantity_box_height)],
                        fill="#f8f8f8", outline="#333333", width=2)
            quantity_val = ar(f"{data['kilowatt_amount']:,.1f}")
            quantity_lbl = ar("الكمية المقطوعة بالكيلو:")
            font_quantity_lbl = get_font(26)
            font_quantity_val = get_font(32, bold=True)
            lbl_width = draw.textlength(quantity_lbl, font=font_quantity_lbl)
            draw.text((PAPER_WIDTH - MARGIN - 40, y + 15), quantity_lbl,
                    font=font_quantity_lbl, fill="black", anchor="ra")
            draw.text((PAPER_WIDTH - MARGIN - 150 - lbl_width - 10, y + 15), quantity_val,
                    font=font_quantity_val, fill="#333333", anchor="la")
            y += quantity_box_height + 15

            # 6. جدول 2×3 للسعر والمجاني والحسم (بدون تغيير)
            table2_height = 70
            col_width = (PAPER_WIDTH - 2 * MARGIN) / 3
            draw.rectangle([(MARGIN, y), (PAPER_WIDTH - MARGIN, y + table2_height)],
                        outline="#666666", width=1)
            draw.line([(MARGIN + col_width, y), (MARGIN + col_width, y + table2_height)],
                    fill="#666666", width=1)
            draw.line([(MARGIN + 2*col_width, y), (MARGIN + 2*col_width, y + table2_height)],
                    fill="#666666", width=1)
            draw.line([(MARGIN, y + table2_height/2), (PAPER_WIDTH - MARGIN, y + table2_height/2)],
                    fill="#666666", width=1)

            font_header = get_font(22)
            price_header = ar("سعر الكيلو")
            w_price = draw.textlength(price_header, font=font_header)
            draw.text((MARGIN + col_width/2 - w_price/2, y + 10), price_header,
                    font=font_header, fill="black")
            free_header = ar("المجاني")
            w_free = draw.textlength(free_header, font=font_header)
            draw.text((MARGIN + col_width + col_width/2 - w_free/2, y + 10), free_header,
                    font=font_header, fill="green")
            discount_header = ar("الحسم")
            w_discount = draw.textlength(discount_header, font=font_header)
            draw.text((MARGIN + 2*col_width + col_width/2 - w_discount/2, y + 10), discount_header,
                    font=font_header, fill="blue")

            font_data = get_font(26)
            price_val = ar(f"{data['price_per_kilo']:,.0f}")
            w_price_val = draw.textlength(price_val, font=font_data)
            draw.text((MARGIN + col_width/2 - w_price_val/2, y + table2_height/2 + 10), price_val,
                    font=font_data, fill="black")
            free_val = ar(f"{data['free_kilowatt']:,.1f}")
            w_free_val = draw.textlength(free_val, font=font_data)
            draw.text((MARGIN + col_width + col_width/2 - w_free_val/2, y + table2_height/2 + 10), free_val,
                    font=font_data, fill="green")
            discount_val = ar(f"{data['discount']:,.0f}")
            w_discount_val = draw.textlength(discount_val, font=font_data)
            draw.text((MARGIN + 2*col_width + col_width/2 - w_discount_val/2, y + table2_height/2 + 10), discount_val,
                    font=font_data, fill="blue")

            y += table2_height + 20

            draw.line([(MARGIN, y), (PAPER_WIDTH - MARGIN, y)], fill="black", width=2)
            y += 15

            # 7. صندوق المبلغ الإجمالي
            total_box_height = 85
            draw.rectangle([(MARGIN, y), (PAPER_WIDTH - MARGIN, y + total_box_height)],
                        fill="black", outline="black", width=2)
            total_lbl = ar("المبلغ المدفوع:")
            total_val = ar(f"{data['total_amount']:,.0f} ل.س")
            font_total_lbl = get_font(30, bold=True)
            font_total_val = get_font(45, bold=True)
            lbl_width = draw.textlength(total_lbl, font=font_total_lbl)
            val_width = draw.textlength(total_val, font=font_total_val)
            draw.text(((PAPER_WIDTH - lbl_width) / 2, y + 10), total_lbl,
                    font=font_total_lbl, fill="white")
            draw.text(((PAPER_WIDTH - val_width) / 2, y + 40), total_val,
                    font=font_total_val, fill="white")
            y += total_box_height + 20

            # 8. جملة المسؤولية
            note_text = ar("لسنا مسؤولين عن الأعطال التي تصيب الأجهزة الكهربائية")
            font_note = get_font(20)
            w_note = draw.textlength(note_text, font=font_note)
            draw.text(((PAPER_WIDTH - w_note) / 2, y), note_text,
                    font=font_note, fill="black")
            y += 35

            # 9. التذييل
            font_small = get_font(18)
            accountant_txt = ar(f"المحاسب: {data['accountant_name']}")
            draw.text((MARGIN + 10, y), accountant_txt,
                    font=font_small, fill="black", anchor="la")
            phone_txt = ar("هاتف: 0952411882")
            w_phone = draw.textlength(phone_txt, font=font_small)
            draw.text(((PAPER_WIDTH - w_phone) / 2, y), phone_txt,
                    font=font_small, fill="black")
            y += 40

            # قص الصورة وإرسالها
            final_img = img.crop((0, 0, PAPER_WIDTH, y))
            self.printer.image(final_img.convert("1"))
            self.printer.cut()
            return True

        except Exception as e:
            logger.error(f"خطأ في الطباعة: {e}")
            return False