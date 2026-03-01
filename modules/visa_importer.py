# modules/visa_importer.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import logging
from typing import Dict, List, Optional, Tuple, Any
from database.connection import db
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ExcelLikeTable(tk.Frame):
    """جدول يشبه Excel للتعديل المباشر مع تحسينات كبيرة"""
    
    def __init__(self, parent, columns: List[str], data: List[Dict]):
        super().__init__(parent)
        self.columns = columns
        self.data = data
        self.data = data          # البيانات المعروضة حالياً
        self.all_data = data.copy()  # نسخة احتياطية من جميع البيانات

        self.original_data = data.copy()
        self.cells = {}  # لحفظ مراجع الصفوف
        self.entry = None  # حقل التعديل العائم
        self.current_cell = None  # الخلية الحالية (item, column)
        self.last_edit_value = None  # آخر قيمة قبل التعديل
        self.tooltip = None
        self.tooltip_text = None
        self.current_hover_item = None
        self.current_hover_column = None
        self.setup_ui()
        
    def setup_ui(self):
        """إعداد واجهة الجدول مع تحسينات"""
        # إطار التمرير
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)
        
        # شريط التمرير العمودي
        y_scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # شريط التمرير الأفقي
        x_scrollbar = ttk.Scrollbar(container, orient=tk.HORIZONTAL)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # إنشاء الجدول
        self.tree = ttk.Treeview(
            container,
            columns=self.columns,
            show='headings',
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set,
            height=25,
            selectmode='browse'
        )
        
        # تكوين الأعمدة
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, minwidth=80)
        
        # إضافة البيانات مع الحفاظ على الترتيب الصحيح
        self.populate_data()
        
        # ربط أحداث لوحة المفاتيح والفأرة
        self.bind_events()
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        y_scrollbar.config(command=self.tree.yview)
        x_scrollbar.config(command=self.tree.xview)
        
        # تلوين الصفوف بالتناوب
        #self.tree.tag_configure('evenbox', background='#e8f5e9')  # أخضر فاتح
        #self.tree.tag_configure('oddbox', background='#f1f8e9')   # أخضر أفتح
        self.tree.tag_configure('selected', background='#e3f2fd')
        self.tree.tag_configure('search_result', background='#fff9c4')
        self.tree.tag_configure('modified', background='#ffeaa7')
        self.tree.tag_configure('separator', background='#e0e0e0')
        self.tree.tag_configure('recently_modified', background='#b3e5fc')   # <-- أضف هذا
        self.tree.tag_configure('test', background='red')
        self.apply_row_colors()

        # في setup_ui، بعد تعريف التاغات
        self.tree.tag_configure('evenbox', background='#e8f5e9')  # أخضر فاتح
        self.tree.tag_configure('oddbox', background='#f1f8e9')   # أخضر أفتح
        self.tree.tag_configure('selected', background='#e3f2fd')
        self.tree.tag_configure('search_result', background='#fff9c4')
        self.tree.tag_configure('modified', background='#FFA07A')      # سمون فاتح
        self.tree.tag_configure('separator', background='#e0e0e0')
        self.tree.tag_configure('recently_modified', background='#FFB6C1')  # وردي فاتح        
        
        # التركيز على الجدول
        self.tree.focus_set()
        
    def populate_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.cells = {}
        item_id_counter = 0
        now = datetime.now()  # استخدم التوقيت المحلي
        twenty_four_hours_ago = now - timedelta(hours=96)

        for idx, row in enumerate(self.data):
            values = [row.get(col, '') for col in self.columns]
            item_id = self.tree.insert('', tk.END, values=values, tags=(f'row_{item_id_counter}',))

            # الحصول على updated_at من الصف مباشرة
            updated_at = row.get('updated_at')
            if updated_at and isinstance(updated_at, str):
                try:
                    updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                except:
                    updated_at = None

            is_recent = False
            if updated_at and isinstance(updated_at, datetime):
                if updated_at > twenty_four_hours_ago:
                    is_recent = True

            # طباعة للتصحيح (يمكن إزالتها لاحقاً)
            print(f"الصف {idx}: updated_at = {updated_at}, is_recent = {is_recent}")

            self.cells[item_id] = {
                'row_data': row,
                'original_row': row.copy(),
                'data_index': idx,
                'box': row.get('علبة', ''),
                'serial': row.get('مسلسل', ''),
                'updated_at': updated_at,
                'is_recent': is_recent,
                'is_modified': False
            }
            item_id_counter += 1

        self.apply_row_colors()
            

    def apply_row_colors(self):
        for idx, item in enumerate(self.tree.get_children()):
            if 'separator' in self.tree.item(item, 'tags'):
                continue
            current_tags = list(self.tree.item(item, 'tags'))
            # إزالة جميع التاجات التي نريد إعادة تعيينها
            for tag in ['evenbox', 'oddbox', 'search_result', 'modified', 'recently_modified']:
                if tag in current_tags:
                    current_tags.remove(tag)

            # تحديد حالة الصف
            is_recent = item in self.cells and self.cells[item].get('is_recent', False)
            is_modified = item in self.cells and self.cells[item].get('is_modified', False)

            # إضافة التاجات حسب الأولوية: recently_modified > modified > تناوب عادي
            if is_recent:
                current_tags.append('recently_modified')
            elif is_modified:
                current_tags.append('modified')
            else:
                # تلوين متناوب عادي
                if idx % 2 == 0:
                    current_tags.append('evenbox')
                else:
                    current_tags.append('oddbox')

            self.tree.item(item, tags=tuple(current_tags))
            
                
    def bind_events(self):
        """ربط أحداث لوحة المفاتيح والفأرة"""
        # أحداث الفأرة
        self.tree.bind('<Double-1>', self.on_cell_double_click)
        self.tree.bind('<ButtonRelease-1>', self.on_cell_click)
        
        # أحداث لوحة المفاتيح
        self.tree.bind('<Key>', self.on_key_press)
        self.tree.bind('<Return>', self.on_enter_key)
        self.tree.bind('<F2>', self.start_edit_cell)
        self.tree.bind('<Delete>', self.clear_cell)
        
        # التنقل
        self.tree.bind('<Up>', self.move_up)
        self.tree.bind('<Down>', self.move_down)
        self.tree.bind('<Left>', self.move_left)
        self.tree.bind('<Right>', self.move_right)
        self.tree.bind('<Tab>', self.on_tab_key)
        self.tree.bind('<Shift-Tab>', self.on_shift_tab)
        
        # أحداث التركيز
        self.tree.bind('<FocusIn>', lambda e: self.tree.selection_set(self.tree.focus()))
        # إزالة إخفاء الـ Entry عند فقدان التركيز للشجرة (هذا يسبب اختفاء الحقل فور إنشائه)
        # السابق:
        # self.tree.bind('<FocusOut>', lambda e: self.hide_entry())

        # الجديد: لا تفعل شيئًا عند فقدان تركيز الشجرة
        # (نترك حفظ/إخفاء الحقل لربط حقل الإدخال نفسه عبر entry.bind('<FocusOut>', ...))

        
        # تحديد مباشر عند الكتابة
        self.tree.bind('<KeyPress>', self.on_direct_edit)

        self.tree.bind('<Motion>', self.on_mouse_motion)
        self.tree.bind('<Leave>', self.on_mouse_leave)        
    
    def on_cell_click(self, event):
        """عند النقر على خلية"""
        region = self.tree.identify_region(event.x, event.y)
        if region == 'cell':
            item = self.tree.identify_row(event.y)
            column = self.tree.identify_column(event.x)
            if item and item not in ['', None]:
                # تحديث تلوين الصف المحدد
                self.update_selection(item)
                self.current_cell = (item, column)
                # بدء التعديل مباشرة إذا بدأ المستخدم بالكتابة
                self.tree.focus_set()
    
    def update_selection(self, item):
        """تحديث تلوين الصف المحدد"""
        # إعادة تعيين جميع الصفوف
        for i in self.tree.get_children():
            if i == item:
                continue
            current_tags = list(self.tree.item(i, 'tags'))
            if 'selected' in current_tags:
                current_tags.remove('selected')
                self.tree.item(i, tags=tuple(current_tags))
        
        # تلوين الصف المحدد
        current_tags = list(self.tree.item(item, 'tags'))
        if 'selected' not in current_tags:
            current_tags.append('selected')
            self.tree.item(item, tags=tuple(current_tags))
    
    def on_cell_double_click(self, event):
        """بدء التعديل عند النقر المزدوج"""
        self.start_edit_cell(event)
        return 'break'
    
    def start_edit_cell(self, event=None, direct_edit=False, char=None):
        """بدء تعديل الخلية الحالية"""
        if not self.current_cell:
            item = self.tree.focus()
            if not item:
                # محاولة الحصول على أول عنصر
                children = self.tree.get_children()
                if children:
                    for child in children:
                        # تخطي الفواصل
                        if 'separator' not in self.tree.item(child, 'tags'):
                            item = child
                            break
            
            column = '#1'
            if item:
                self.current_cell = (item, column)
            else:
                return 'break'
        
        item, column = self.current_cell
        if not item or not column:
            return 'break'
        
        # تخطي الفواصل
        if 'separator' in self.tree.item(item, 'tags'):
            return 'break'
        
        # الحصول على إحداثيات الخلية
        bbox = self.tree.bbox(item, column)
        if not bbox:
            return 'break'
        
        # الحصول على قيمة الخلية الحالية
        col_index = int(column.replace('#', '')) - 1
        current_values = self.tree.item(item, 'values')
        if col_index >= len(current_values):
            return 'break'
        
        current_value = current_values[col_index]
        self.last_edit_value = current_value
        
        # إخفاء أي حقل تعديل سابق
        self.hide_entry()
        
        # إنشاء حقل التعديل العائم
        self.entry = tk.Entry(self.tree, font=('Arial', 10), 
                             borderwidth=0, highlightthickness=1,
                             highlightcolor='#2196F3', highlightbackground='#2196F3')
        
        # تحديد موقع الحقل فوق الخلية
        x, y, width, height = bbox
        self.entry.place(x=x, y=y, width=width, height=height)
        
        # إعداد القيمة والأحداث
        if direct_edit and char:
            self.entry.insert(0, char)
            self.entry.select_range(1, tk.END)
            self.entry.icursor(tk.END)
        else:
            self.entry.insert(0, current_value)
            self.entry.select_range(0, tk.END)
        
        self.entry.focus_set()
        
        # ربط الأحداث
        self.entry.bind('<Return>', lambda e: self.save_edit_and_move_down(item, column))
        self.entry.bind('<Escape>', lambda e: self.cancel_edit(item, column))
        self.entry.bind('<Tab>', lambda e: self.save_edit_and_move_right(item, column))
        self.entry.bind('<Shift-Tab>', lambda e: self.save_edit_and_move_left(item, column))
        self.entry.bind('<Up>', lambda e: self.save_edit_and_move_up(item, column))
        self.entry.bind('<Down>', lambda e: self.save_edit_and_move_down(item, column))
        self.entry.bind('<Left>', lambda e: self.save_edit_and_move_left(item, column))
        self.entry.bind('<Right>', lambda e: self.save_edit_and_move_right(item, column))
        
        # حفظ عند فقدان التركيز
        self.entry.bind('<FocusOut>', lambda e: self.save_edit(item, column))
        
        return 'break'
    
    def save_edit(self, item, column, event=None):
        """حفظ التعديل وإخفاء حقل الإدخال"""
        if not self.entry:
            return
        
        # الحصول على القيمة الجديدة
        new_value = self.entry.get()
        
        # الحصول على الفهرس
        col_index = int(column.replace('#', '')) - 1
        
        # تحديث القيمة في الجدول
        values = list(self.tree.item(item, 'values'))
        old_value = values[col_index]
        values[col_index] = new_value
        self.tree.item(item, values=values)
        
        # تحديث البيانات في cells
        if item in self.cells:
            col_name = self.columns[col_index]
            self.cells[item]['row_data'][col_name] = new_value
        
        # تلوين الصف المعدل
        self.mark_row_as_modified(item)
        self.apply_row_colors()
        
        # إخفاء حقل التعديل
        self.hide_entry()
        
        # إعادة التركيز على الجدول
        self.tree.focus_set()
        self.tree.selection_set(item)
        
        return 'break'
        
    def mark_row_as_modified(self, item):
        """تحديد الصف كمعدل وتحديث is_recent إذا لزم الأمر"""
        if item in self.cells:
            current_tags = list(self.tree.item(item, 'tags'))
            if 'modified' not in current_tags:
                current_tags.append('modified')
                self.tree.item(item, tags=tuple(current_tags))
            
            # تحديث is_modified في الخلايا
            self.cells[item]['is_modified'] = True
            # تحديث is_recent (أي تعديل جديد يعتبر حديثاً)
            self.cells[item]['is_recent'] = True
            self.cells[item]['updated_at'] = datetime.now()   # نضع الوقت الحالي افتراضياً
    
    def save_edit_and_move_down(self, item, column):
        """حفظ التعديل والانتقال للأسفل"""
        self.save_edit(item, column)
        self.move_down(None)
        return 'break'
    
    def save_edit_and_move_up(self, item, column):
        """حفظ التعديل والانتقال للأعلى"""
        self.save_edit(item, column)
        self.move_up(None)
        return 'break'
    
    def save_edit_and_move_right(self, item, column):
        """حفظ التعديل والانتقال لليمين"""
        self.save_edit(item, column)
        self.move_right(None)
        return 'break'
    
    def save_edit_and_move_left(self, item, column):
        """حفظ التعديل والانتقال لليسار"""
        self.save_edit(item, column)
        self.move_left(None)
        return 'break'
    
    def cancel_edit(self, item, column):
        """إلغاء التعديل"""
        if self.entry and self.last_edit_value:
            col_index = int(column.replace('#', '')) - 1
            values = list(self.tree.item(item, 'values'))
            values[col_index] = self.last_edit_value
            self.tree.item(item, values=values)
            
            if item in self.cells:
                col_name = self.columns[col_index]
                self.cells[item]['row_data'][col_name] = self.last_edit_value
        
        self.hide_entry()
        self.tree.focus_set()
        return 'break'
    
    def hide_entry(self):
        """إخفاء حقل التعديل"""
        if self.entry:
            self.entry.destroy()
            self.entry = None
            self.last_edit_value = None
    
    def clear_cell(self, event):
        """مسح محتوى الخلية"""
        if self.current_cell:
            item, column = self.current_cell
            col_index = int(column.replace('#', '')) - 1
            
            values = list(self.tree.item(item, 'values'))
            values[col_index] = ''
            self.tree.item(item, values=values)
            
            if item in self.cells:
                col_name = self.columns[col_index]
                self.cells[item]['row_data'][col_name] = ''
            
            self.mark_row_as_modified(item)
        
        return 'break'
    
    def on_key_press(self, event):
        """معالجة ضغطات المفاتيح"""
        # منع السلوك الافتراضي لمفاتيح التنقل عندما يكون هناك حقل تعديل
        if self.entry and event.keysym in ('Up', 'Down', 'Left', 'Right', 'Return', 'Tab'):
            return 'break'
        
        # F2 لبدء التعديل
        if event.keysym == 'F2':
            self.start_edit_cell()
            return 'break'
    
    def on_direct_edit(self, event):
        """بدء التعديل المباشر عند الكتابة"""
        # تجاهل مفاتيح التحكم والوظائف
        if len(event.char) == 0 or event.keysym in ('Shift_L', 'Shift_R', 'Control_L', 'Control_R', 
                                                    'Alt_L', 'Alt_R', 'Caps_Lock', 'Escape', 
                                                    'Return', 'Tab', 'F1', 'F2', 'F3', 'F4',
                                                    'F5', 'F6', 'F7', 'F8', 'F9', 'F10',
                                                    'F11', 'F12', 'space'):
            return
        
        # البدء في التعديل المباشر
        if not self.entry:
            self.start_edit_cell(direct_edit=True, char=event.char)
        else:
            # إذا كان هناك حقل تعديل بالفعل، أضف الحرف إليه
            self.entry.insert(tk.INSERT, event.char)
        
        return 'break'
    
    def on_enter_key(self, event):
        """معالجة مفتاح Enter"""
        if self.entry:
            # إذا كان هناك حقل تعديل، حفظ والانتقال للأسفل
            item, column = self.current_cell
            self.save_edit_and_move_down(item, column)
        else:
            # إذا لم يكن هناك حقل تعديل، بدء التعديل
            self.start_edit_cell()
        
        return 'break'
    
    def move_up(self, event):
        """الانتقال للخلية الأعلى"""
        self.hide_entry()
        current = self.tree.focus()
        if current:
            prev = self.tree.prev(current)
            if prev:
                # تخطي الفواصل
                while prev and 'separator' in self.tree.item(prev, 'tags'):
                    prev = self.tree.prev(prev)
                
                if prev:
                    self.tree.selection_set(prev)
                    self.tree.focus(prev)
                    self.tree.see(prev)
                    self.update_selection(prev)
                    # تحديث الخلية الحالية
                    column = self.current_cell[1] if self.current_cell else '#1'
                    self.current_cell = (prev, column)
        return 'break'
    
    def move_down(self, event):
        """الانتقال للخلية الأسفل"""
        self.hide_entry()
        current = self.tree.focus()
        if current:
            next_item = self.tree.next(current)
            
            # تخطي الفواصل
            while next_item and 'separator' in self.tree.item(next_item, 'tags'):
                next_item = self.tree.next(next_item)
            
            if not next_item:
                children = self.tree.get_children()
                for child in children:
                    if 'separator' not in self.tree.item(child, 'tags'):
                        next_item = child
                        break
            
            if next_item:
                self.tree.selection_set(next_item)
                self.tree.focus(next_item)
                self.tree.see(next_item)
                self.update_selection(next_item)
                # تحديث الخلية الحالية
                column = self.current_cell[1] if self.current_cell else '#1'
                self.current_cell = (next_item, column)
        return 'break'
    
    def move_left(self, event):
        """الانتقال لليسار"""
        self.hide_entry()
        if self.current_cell:
            item, column = self.current_cell
            col_index = int(column.replace('#', '')) - 1
            if col_index > 0:
                new_column = f'#{col_index}'
                self.current_cell = (item, new_column)
        return 'break'
    
    def move_right(self, event):
        """الانتقال لليمين"""
        self.hide_entry()
        if self.current_cell:
            item, column = self.current_cell
            col_index = int(column.replace('#', '')) - 1
            if col_index < len(self.columns) - 1:
                new_column = f'#{col_index + 2}'
                self.current_cell = (item, new_column)
        return 'break'
    
    def on_tab_key(self, event):
        """الانتقال للخلية التالية عند Tab"""
        self.hide_entry()
        current = self.tree.focus()
        if current:
            # الحصول على الخلية التالية (يمين)
            if self.current_cell:
                item, column = self.current_cell
                col_index = int(column.replace('#', '')) - 1
                
                if col_index < len(self.columns) - 1:
                    # الانتقال لليمين في نفس الصف
                    new_column = f'#{col_index + 2}'
                    self.current_cell = (item, new_column)
                else:
                    # الانتقال للصف التالي، العمود الأول
                    next_item = self.tree.next(current)
                    
                    # تخطي الفواصل
                    while next_item and 'separator' in self.tree.item(next_item, 'tags'):
                        next_item = self.tree.next(next_item)
                    
                    if not next_item:
                        children = self.tree.get_children()
                        for child in children:
                            if 'separator' not in self.tree.item(child, 'tags'):
                                next_item = child
                                break
                    
                    if next_item:
                        self.tree.selection_set(next_item)
                        self.tree.focus(next_item)
                        self.tree.see(next_item)
                        self.update_selection(next_item)
                        self.current_cell = (next_item, '#1')
        
        return 'break'
    
    def on_shift_tab(self, event):
        """الانتقال للخلية السابقة عند Shift+Tab"""
        self.hide_entry()
        current = self.tree.focus()
        if current:
            # الحصول على الخلية السابقة (يسار)
            if self.current_cell:
                item, column = self.current_cell
                col_index = int(column.replace('#', '')) - 1
                
                if col_index > 0:
                    # الانتقال لليسار في نفس الصف
                    new_column = f'#{col_index}'
                    self.current_cell = (item, new_column)
                else:
                    # الانتقال للصف السابق، العمود الأخير
                    prev = self.tree.prev(current)
                    
                    # تخطي الفواصل
                    while prev and 'separator' in self.tree.item(prev, 'tags'):
                        prev = self.tree.prev(prev)
                    
                    if prev:
                        self.tree.selection_set(prev)
                        self.tree.focus(prev)
                        self.tree.see(prev)
                        self.update_selection(prev)
                        self.current_cell = (prev, f'#{len(self.columns)}')
        
        return 'break'
        
    def search_in_table(self, search_text: str, search_column: str = "الكل"):
        """بحث في الجدول مع إخفاء الصفوف غير المطابقة"""
        # إعادة تعيين تلوين البحث السابق (ولكننا الآن نخفي الصفوف)
        # نعيد إظهار جميع الصفوف أولاً إذا كان هناك بحث سابق
        all_items = self.tree.get_children()
        for item in all_items:
            if 'separator' in self.tree.item(item, 'tags'):
                continue
            # إذا كان العنصر مخفياً (detached) نعيده
            # لكن tree.get_children لا تعيد العناصر المخفية. لذا نحتاج لتتبع المخفيين.
            # بدلاً من ذلك، سنقوم بإعادة بناء الجدول عند البحث الفارغ.
            pass
        
        # لتسهيل الأمر، سنقوم بتخزين قائمة بجميع العناصر (حتى المخفية) في self.all_items
        # ولكن ليس لدينا. لذا سنستخدم طريقة detach وإعادة الإظهار عبر populate_data.
            
    
        if not search_text:
            # إعادة عرض جميع البيانات
            self.data = self.all_data.copy()
            self.populate_data()
            return []
        
        search_text = search_text.lower()
        filtered_data = []
        
        for row in self.all_data:
            found = False
            if search_column == "الكل":
                for col in self.columns:
                    if search_text in str(row.get(col, '')).lower():
                        found = True
                        break
            else:
                if search_column in self.columns:
                    if search_text in str(row.get(search_column, '')).lower():
                        found = True
            
            if found:
                filtered_data.append(row)
        
        # عرض البيانات المفلترة
        self.data = filtered_data
        self.populate_data()
        
        # تحديث التلوين للنتائج (اختياري، لأن populate_data يعيد التلوين)
        # يمكن إضافة تاغ search_result للصفوف في populate_data إذا أردنا تلوينها.
        
        return filtered_data
        
        # تلوين النتائج (الصفوف التي لا تزال ظاهرة)
        for item in results:
            current_tags = list(self.tree.item(item, 'tags'))
            if 'search_result' not in current_tags:
                current_tags.append('search_result')
                self.tree.item(item, tags=tuple(current_tags))
        
        # إعادة تطبيق الألوان على الصفوف الظاهرة
        self.apply_row_colors()
        
        # إذا كانت هناك نتائج، التمرير للنتيجة الأولى
        if results:
            self.tree.see(results[0])
            self.tree.selection_set(results[0])
            self.update_selection(results[0])
        
        return results
        
    def get_modified_data(self):
        """الحصول على البيانات المعدلة فقط"""
        modified_rows = []
        
        for item in self.tree.get_children():
            # تخطي الفواصل
            if 'separator' in self.tree.item(item, 'tags'):
                continue
            
            if item in self.cells:
                current_values = self.tree.item(item, 'values')
                original_row = self.cells[item]['original_row']
                row_data = self.cells[item]['row_data']
                
                # التحقق من وجود تعديلات
                is_modified = False
                for col_idx, col_name in enumerate(self.columns):
                    current_val = str(current_values[col_idx]).strip()
                    original_val = str(original_row.get(col_name, '')).strip()
                    
                    if current_val != original_val:
                        is_modified = True
                        break
                
                if is_modified:
                    # إضافة البيانات المعدلة
                    modified_row = {
                        'id': original_row.get('id'),
                        'علبة': row_data.get('علبة', ''),
                        'مسلسل': row_data.get('مسلسل', ''),
                        'التأشيرة_الحالية_أصلية': original_row.get('التأشيرة الحالية', ''),
                        'التأشيرة_الجديدة': row_data.get('التأشيرة الجديدة', ''),
                        'previous_withdrawal': original_row.get('previous_withdrawal', 0),      # السحب القديم الأصلي
                        'withdrawal_updated_at': original_row.get('withdrawal_updated_at'),    # وقت آخر تحديث للسحب
                        'row_data': row_data,
                        'original_data': original_row.copy()
                    }
                    modified_rows.append(modified_row)
        
        return modified_rows
    
    def get_all_data(self):
        """الحصول على جميع البيانات"""
        all_data = []
        for item in self.tree.get_children():
            if 'separator' in self.tree.item(item, 'tags'):
                continue
            
            if item in self.cells:
                all_data.append(self.cells[item]['row_data'])
        
        return all_data

    # ... داخل ExcelLikeTable ...

    def on_mouse_motion(self, event):
        """تتبع حركة الماوس لعرض التلميحات"""
        region = self.tree.identify_region(event.x, event.y)
        if region == 'cell':
            item = self.tree.identify_row(event.y)
            column = self.tree.identify_column(event.x)
            if item and column:
                if (item, column) != (self.current_hover_item, self.current_hover_column):
                    self.current_hover_item = item
                    self.current_hover_column = column
                    self.show_tooltip(event, item, column)
        else:
            self.hide_tooltip()

    def on_mouse_leave(self, event):
        self.hide_tooltip()

    def show_tooltip(self, event, item, column):
        """عرض تلميح يحتوي على معلومات الخلية"""
        self.hide_tooltip()
        
        if item not in self.cells:
            return
        
        col_index = int(column.replace('#', '')) - 1
        col_name = self.columns[col_index] if col_index < len(self.columns) else None
        if not col_name:
            return
        
        row_data = self.cells[item]['row_data']
        original_row = self.cells[item]['original_row']
        
        lines = []
        
        # آخر تعديل
        updated_at = row_data.get('updated_at')
        if updated_at:
            if isinstance(updated_at, datetime):
                lines.append(f"آخر تعديل: {updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                lines.append(f"آخر تعديل: {updated_at}")
        else:
            lines.append("آخر تعديل: غير معروف")
        
        # معلومات حسب العمود
        if col_name == 'التأشيرة الجديدة':
            prev_visa = original_row.get('التأشيرة الحالية', '')
            curr_visa = row_data.get('التأشيرة الجديدة', '')
            lines.append(f"التأشيرة السابقة: {prev_visa}")
            lines.append(f"التأشيرة الحالية: {curr_visa}")
        elif col_name == 'السحب الحالي':
            prev_withdrawal = original_row.get('previous_withdrawal', 0)
            curr_withdrawal = row_data.get('السحب الحالي', 0)
            lines.append(f"السحب السابق: {prev_withdrawal}")
            lines.append(f"السحب الحالي: {curr_withdrawal}")
        else:
            original_val = original_row.get(col_name, '')
            current_val = row_data.get(col_name, '')
            if str(original_val) != str(current_val):
                lines.append(f"القيمة الأصلية: {original_val}")
                lines.append(f"القيمة الحالية: {current_val}")
        
        if not lines:
            return
        
        # إنشاء نافذة التلميح
        self.tooltip = tk.Toplevel(self.tree)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
        
        label = tk.Label(self.tooltip, text="\n".join(lines), justify='right',
                        background="#ffffe0", relief='solid', borderwidth=1,
                        font=("Arial", 10))
        label.pack()

    def hide_tooltip(self):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
            self.current_hover_item = None
            self.current_hover_column = None



class VisaEditor:
    """محرر التأشيرات داخل البرنامج مع تحسينات كبيرة"""
    
    def __init__(self, parent, user_id: int):
        self.parent = parent
        self.user_id = user_id
        self.sector_id = None
        self.sector_name = None
        self.customers_data = []
        self.original_customers_data = []  # نسخة احتياطية للبحث
        
        self.setup_ui()
        self.load_sectors()
    
    def setup_ui(self):
        """إعداد الواجهة الرئيسية مع تحسينات"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("محرر التأشيرات - التعديل المباشر")
        self.window.geometry("1400x850")
        
        # إطار شريط الأدوات العلوي
        toolbar_frame = tk.Frame(self.window, bg='#f0f0f0', height=50)
        toolbar_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        toolbar_frame.pack_propagate(False)
        
        # زر حفظ رئيسي كبير في شريط الأدوات
        self.save_btn = tk.Button(
            toolbar_frame,
            text="💾 حفظ التعديلات (Ctrl+S)",
            command=self.save_changes,
            state='disabled',
            bg='#4CAF50',
            fg='white',
            font=('Arial', 12, 'bold'),
            padx=25,
            pady=8,
            relief=tk.RAISED,
            bd=2,
            cursor='hand2'
        )
        self.save_btn.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # مؤشر عدد التعديلات
        self.modified_count_label = tk.Label(
            toolbar_frame,
            text="0 تعديل",
            bg='#f0f0f0',
            fg='#FF9800',
            font=('Arial', 10, 'bold')
        )
        self.modified_count_label.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # زر استعادة في شريط الأدوات
        restore_toolbar_btn = tk.Button(
            toolbar_frame,
            text="↻ استعادة الأصلية",
            command=self.reset_changes,
            bg='#FF9800',
            fg='white',
            font=('Arial', 10),
            padx=15,
            pady=5
        )
        restore_toolbar_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # إطار التحكم العلوي
        control_frame = ttk.Frame(self.window)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # اختيار القطاع
        ttk.Label(control_frame, text="اختر القطاع:").pack(side=tk.LEFT, padx=5)
        
        self.sector_var = tk.StringVar()
        self.sector_combo = ttk.Combobox(control_frame, textvariable=self.sector_var, 
                                         width=30, state='readonly')
        self.sector_combo.pack(side=tk.LEFT, padx=5)
        self.sector_combo.bind('<<ComboboxSelected>>', self.on_sector_selected)
        
        # زر تحميل البيانات
        ttk.Button(control_frame, text="🔍 تحميل الزبائن", 
                  command=self.load_customers).pack(side=tk.LEFT, padx=10)
        
        # معلومات القطاع
        self.info_label = ttk.Label(control_frame, text="", font=('Arial', 10, 'bold'))
        self.info_label.pack(side=tk.LEFT, padx=20)
        
        # إطار البحث
        search_frame = ttk.LabelFrame(control_frame, text="بحث متقدم", padding=5)
        search_frame.pack(side=tk.LEFT, padx=20)
        
        # اختيار حقل البحث
        ttk.Label(search_frame, text="بحث في:").pack(side=tk.LEFT, padx=5)
        
        self.search_column_var = tk.StringVar(value="الكل")
        self.search_column_combo = ttk.Combobox(
            search_frame, 
            textvariable=self.search_column_var,
            width=15,
            state='readonly'
        )
        self.search_column_combo['values'] = ["الكل", "علبة", "مسلسل", "اسم الزبون", "التأشيرة الحالية", "التأشيرة الجديدة"]
        self.search_column_combo.pack(side=tk.LEFT, padx=5)
        
        # حقل البحث
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=25)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<KeyRelease>', self.on_search)
        
        # زر مسح البحث
        ttk.Button(search_frame, text="🗑️ مسح", 
                  command=self.clear_search, width=8).pack(side=tk.LEFT, padx=5)
        
        # زر بحث سريع في التأشيرات
        ttk.Button(search_frame, text="🔎 بحث تأشيرة", 
                  command=self.quick_search_visa, width=12).pack(side=tk.LEFT, padx=5)
        
        # زر التالي في البحث
        ttk.Button(search_frame, text="▶️ التالي", 
                  command=self.find_next, width=8).pack(side=tk.LEFT, padx=5)
        
        # إطار الجدول الرئيسي
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # ملصق حالة الجدول
        self.status_label = ttk.Label(main_frame, text="قم بتحميل القطاع أولاً", 
                                     font=('Arial', 11, 'italic'))
        self.status_label.pack(pady=10)
        
        # مكان الجدول
        self.table_container = ttk.Frame(main_frame)
        self.table_container.pack(fill=tk.BOTH, expand=True)
        
        # إطار الإحصاءات
        self.stats_frame = ttk.Frame(main_frame)
        self.stats_frame.pack(fill=tk.X, pady=5)
        
        self.stats_label = ttk.Label(self.stats_frame, text="", font=('Arial', 10))
        self.stats_label.pack()
        
        # إطار حالة الحفظ في الأسفل
        save_status_frame = ttk.Frame(main_frame)
        save_status_frame.pack(fill=tk.X, pady=5)
        
        self.save_status_label = ttk.Label(
            save_status_frame,
            text="⚪ جاهز",
            font=('Arial', 10, 'italic'),
            foreground='gray'
        )
        self.save_status_label.pack(side=tk.LEFT)
        
        # إطار الأزرار السفلي
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # زر تصدير إلى Excel
        export_btn = tk.Button(
            button_frame,
            text="📄 تصدير إلى Excel",
            command=self.export_to_excel,
            bg='#2196F3',
            fg='white',
            font=('Arial', 10),
            padx=15,
            pady=5
        )
        export_btn.pack(side=tk.LEFT, padx=5)
        
        # زر البحث عن تأشيرة محددة
        ttk.Button(button_frame, text="🔍 بحث رقمي", 
                  command=self.search_numeric).pack(side=tk.LEFT, padx=5)
        
        # زر حفظ إضافي في الأسفل
        save_bottom_btn = tk.Button(
            button_frame,
            text="💾 حفظ التعديلات",
            command=self.save_changes,
            state='disabled',
            bg='#4CAF50',
            fg='white',
            font=('Arial', 10, 'bold'),
            padx=20,
            pady=5
        )
        save_bottom_btn.pack(side=tk.RIGHT, padx=5)
        
        # ربط زر الحفظ السفلي بنفس زر الحفظ العلوي
        self.save_bottom_btn = save_bottom_btn
        
        # زر إغلاق
        close_btn = tk.Button(
            button_frame,
            text="✕ إغلاق",
            command=self.window.destroy,
            bg='#f44336',
            fg='white',
            font=('Arial', 10),
            padx=20,
            pady=5
        )
        close_btn.pack(side=tk.RIGHT, padx=5)
        
        # ربط الاختصارات
        self.window.bind('<Control-s>', lambda e: self.save_changes())
        self.window.bind('<Control-S>', lambda e: self.save_changes())
        self.window.bind('<Control-r>', lambda e: self.reset_changes())
        self.window.bind('<Control-f>', lambda e: self.search_entry.focus())
        self.window.bind('<F3>', lambda e: self.find_next())
        self.window.bind('<Escape>', lambda e: self.window.destroy())
        
        # إضافة تأثيرات التمرير على زر الحفظ
        def on_save_enter(e):
            if self.save_btn['state'] == 'normal':
                self.save_btn.config(bg='#45a049')
        
        def on_save_leave(e):
            if self.save_btn['state'] == 'normal':
                self.save_btn.config(bg='#4CAF50')
        
        self.save_btn.bind('<Enter>', on_save_enter)
        self.save_btn.bind('<Leave>', on_save_leave)
        
        # بدء تحديث حالة الزر تلقائياً
        self.start_save_button_updater()
        
        # مركز النافذة
        self.center_window()
        
    
    def start_save_button_updater(self):
        """بدء تحديث تلقائي لحالة زر الحفظ"""
        self.update_save_button_status()
        # جدولة التحديث كل ثانيتين
        self.window.after(2000, self.start_save_button_updater)
    
    def update_save_button_status(self):
        """تحديث حالة زر الحفظ بناءً على التعديلات"""
        if hasattr(self, 'table'):
            modified_data = self.table.get_modified_data()
            modified_count = len(modified_data)
            
            if modified_count > 0:
                # تفعيل زر الحفظ وتحديث النص
                self.save_btn.config(state='normal', bg='#FF9800')
                self.save_bottom_btn.config(state='normal', bg='#FF9800')
                
                # تحديث مؤشر التعديلات
                if modified_count == 1:
                    self.modified_count_label.config(text="1 تعديل", fg='#FF9800')
                else:
                    self.modified_count_label.config(text=f"{modified_count} تعديلات", fg='#FF9800')
                
                # تحديث حالة الحفظ
                self.save_status_label.config(
                    text=f"⚠️ لديك {modified_count} تعديلات غير محفوظة",
                    foreground='red'
                )
            else:
                # تعطيل زر الحفظ إذا لم توجد تعديلات
                self.save_btn.config(state='disabled', bg='#CCCCCC')
                self.save_bottom_btn.config(state='disabled', bg='#CCCCCC')
                self.modified_count_label.config(text="0 تعديل", fg='#757575')
                self.save_status_label.config(text="✅ لا توجد تعديلات جديدة", foreground='green')
        else:
            # حالة عدم وجود جدول
            self.save_btn.config(state='disabled', bg='#CCCCCC')
            self.save_bottom_btn.config(state='disabled', bg='#CCCCCC')
            self.modified_count_label.config(text="0 تعديل", fg='#757575')
            self.save_status_label.config(text="⚪ لم يتم تحميل بيانات بعد", foreground='gray')
    
    def center_window(self):
        """توسيط النافذة على الشاشة"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def load_sectors(self):
        """تحميل قائمة القطاعات"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, name, code 
                    FROM sectors 
                    WHERE is_active = TRUE 
                    ORDER BY name
                """)
                sectors = cursor.fetchall()
                
                sector_names = []
                self.sectors_map = {}
                
                for sector in sectors:
                    display_name = f"{sector['name']} ({sector['code'] or 'بدون رمز'})"
                    sector_names.append(display_name)
                    self.sectors_map[display_name] = {
                        'id': sector['id'],
                        'name': sector['name'],
                        'code': sector['code']
                    }
                
                self.sector_combo['values'] = sector_names
                
                if sector_names:
                    self.sector_combo.current(0)
                    self.on_sector_selected()
                
        except Exception as e:
            logger.error(f"خطأ في تحميل القطاعات: {e}")
            messagebox.showerror("خطأ", f"فشل تحميل القطاعات: {e}")
    
    def on_sector_selected(self, event=None):
        """عند اختيار قطاع"""
        selected = self.sector_var.get()
        if selected in self.sectors_map:
            sector_info = self.sectors_map[selected]
            self.sector_id = sector_info['id']
            self.sector_name = sector_info['name']
            self.info_label.config(text=f"القطاع: {self.sector_name} (كود: {sector_info['code'] or 'بدون'})")
    
    def on_search(self, event=None):
        """عند البحث في الجدول"""
        if hasattr(self, 'table'):
            search_text = self.search_var.get()
            search_column = self.search_column_var.get()
            
            results = self.table.search_in_table(search_text, search_column)
            
            if search_text:
                self.status_label.config(
                    text=f"تم العثور على {len(results)} نتيجة للبحث عن: '{search_text}'"
                )
            else:
                if hasattr(self, 'table'):
                    all_data = self.table.get_all_data()
                    self.status_label.config(text=f"تم تحميل {len(all_data)} زبون")
    
    def clear_search(self):
        """مسح البحث"""
        self.search_var.set('')
        self.on_search()
    
    def quick_search_visa(self):
        """بحث سريع في التأشيرات"""
        visa_value = simpledialog.askstring("بحث تأشيرة", "أدخل قيمة التأشيرة للبحث:")
        if visa_value:
            self.search_var.set(visa_value)
            self.search_column_var.set("التأشيرة الجديدة")
            self.on_search()
    
    def search_numeric(self):
        """بحث رقمي متقدم"""
        search_window = tk.Toplevel(self.window)
        search_window.title("بحث رقمي متقدم")
        search_window.geometry("400x300")
        search_window.transient(self.window)
        search_window.grab_set()
        
        ttk.Label(search_window, text="بحث رقمي متقدم", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        # حقل البحث
        frame = ttk.Frame(search_window)
        frame.pack(pady=10, padx=20, fill=tk.X)
        
        ttk.Label(frame, text="ابحث عن:").pack(side=tk.LEFT)
        search_entry = ttk.Entry(frame, width=20)
        search_entry.pack(side=tk.LEFT, padx=10)
        search_entry.focus()
        
        # خيارات البحث
        options_frame = ttk.LabelFrame(search_window, text="خيارات البحث", padding=10)
        options_frame.pack(pady=10, padx=20, fill=tk.X)
        
        search_type = tk.StringVar(value="exact")
        
        ttk.Radiobutton(options_frame, text="مطابقة تامة", 
                       variable=search_type, value="exact").pack(anchor=tk.W)
        ttk.Radiobutton(options_frame, text="يحتوي على", 
                       variable=search_type, value="contains").pack(anchor=tk.W)
        ttk.Radiobutton(options_frame, text="أكبر من", 
                       variable=search_type, value="greater").pack(anchor=tk.W)
        ttk.Radiobutton(options_frame, text="أصغر من", 
                       variable=search_type, value="smaller").pack(anchor=tk.W)
        
        def perform_search():
            """تنفيذ البحث"""
            value = search_entry.get()
            search_type_val = search_type.get()
            
            if not value:
                return
            
            # تطبيق البحث
            if hasattr(self, 'table'):
                # البحث في البيانات
                items = self.table.tree.get_children()
                results = []
                
                for item in items:
                    if 'separator' in self.table.tree.item(item, 'tags'):
                        continue
                    
                    values = self.table.tree.item(item, 'values')
                    if not values:
                        continue
                    
                    match = False
                    
                    # البحث في كل الأعمدة
                    for idx, cell_value in enumerate(values):
                        cell_str = str(cell_value).replace(',', '')
                        
                        if search_type_val == "exact":
                            match = cell_str == value
                        elif search_type_val == "contains":
                            match = value in cell_str
                        elif search_type_val == "greater":
                            try:
                                if cell_str.replace('.', '').isdigit():
                                    match = float(cell_str) > float(value)
                            except:
                                pass
                        elif search_type_val == "smaller":
                            try:
                                if cell_str.replace('.', '').isdigit():
                                    match = float(cell_str) < float(value)
                            except:
                                pass
                        
                        if match:
                            results.append(item)
                            break
                
                # تلوين النتائج
                if results:
                    for item in results:
                        current_tags = list(self.table.tree.item(item, 'tags'))
                        if 'search_result' not in current_tags:
                            current_tags.append('search_result')
                            self.table.tree.item(item, tags=tuple(current_tags))
                    
                    # التمرير للنتيجة الأولى
                    self.table.tree.see(results[0])
                    self.table.tree.selection_set(results[0])
                    self.table.update_selection(results[0])
                    
                    messagebox.showinfo("نتيجة البحث", 
                                      f"تم العثور على {len(results)} نتيجة")
                else:
                    messagebox.showinfo("نتيجة البحث", "لم يتم العثور على نتائج")
            
            search_window.destroy()
        
        # أزرار
        btn_frame = ttk.Frame(search_window)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="بحث", command=perform_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="إلغاء", 
                  command=search_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def find_next(self):
        """البحث عن التالي"""
        if hasattr(self, 'table') and self.search_var.get():
            items = self.table.tree.get_children()
            # تصفية العناصر الفارغة والفاصلة
            valid_items = []
            for item in items:
                if 'separator' in self.table.tree.item(item, 'tags'):
                    continue
                values = self.table.tree.item(item, 'values')
                if values and any(str(v).strip() != '' for v in values):
                    valid_items.append(item)
            
            if not valid_items:
                return
            
            selected = self.table.tree.selection()
            
            if selected and selected[0] in valid_items:
                current_idx = valid_items.index(selected[0])
                next_idx = (current_idx + 1) % len(valid_items)
            else:
                next_idx = 0
            
            # البحث عن المطابقة التالية
            search_text = self.search_var.get().lower()
            search_column = self.search_column_var.get()
            
            for i in range(len(valid_items)):
                idx = (next_idx + i) % len(valid_items)
                item = valid_items[idx]
                values = self.table.tree.item(item, 'values')
                
                found = False
                if search_column == "الكل":
                    for value in values:
                        if search_text in str(value).lower():
                            found = True
                            break
                else:
                    if search_column in self.table.columns:
                        col_idx = self.table.columns.index(search_column)
                        if search_text in str(values[col_idx]).lower():
                            found = True
                
                if found:
                    self.table.tree.see(item)
                    self.table.tree.selection_set(item)
                    self.table.update_selection(item)
                    break
                    
    # في VisaEditor.load_customers()
    def load_customers(self):
        """تحميل جميع عدادات القطاع المحدد بالترتيب الهرمي (جميع الأنواع) مع updated_at"""
        if not self.sector_id:
            messagebox.showwarning("تحذير", "الرجاء اختيار قطاع أولاً")
            return

        # تحديث حالة الزر أثناء التحميل
        self.save_btn.config(state='disabled', text="⏳ جاري التحميل...", bg='#FF9800')
        self.save_bottom_btn.config(state='disabled', text="⏳ جاري التحميل...", bg='#FF9800')
        self.save_status_label.config(text="⏳ جاري تحميل البيانات...", foreground='blue')
        self.window.update()

        try:
            # استعلام مباشر لجلب البيانات مع previous_withdrawal و withdrawal_updated_at
            with db.get_cursor() as cursor:
                query = """
                    WITH RECURSIVE meter_tree AS (
                        SELECT 
                            id, name, meter_type, financial_category, visa_balance,
                            box_number, serial_number, parent_meter_id, sector_id,
                            current_balance, withdrawal_amount, updated_at,
                            previous_withdrawal, withdrawal_updated_at,  -- الأعمدة الجديدة
                            0 AS level,
                            ARRAY[id] AS path,
                            ARRAY[name]::VARCHAR[] AS path_names
                        FROM customers
                        WHERE is_active = TRUE
                        AND parent_meter_id IS NULL
                        AND (sector_id = %s OR %s IS NULL)
                        
                        UNION ALL
                        
                        SELECT 
                            c.id, c.name, c.meter_type, c.financial_category, c.visa_balance,
                            c.box_number, c.serial_number, c.parent_meter_id, c.sector_id,
                            c.current_balance, c.withdrawal_amount, c.updated_at,
                            c.previous_withdrawal, c.withdrawal_updated_at,
                            mt.level + 1,
                            mt.path || c.id,
                            mt.path_names || c.name
                        FROM customers c
                        INNER JOIN meter_tree mt ON c.parent_meter_id = mt.id
                        WHERE c.is_active = TRUE
                    )
                    SELECT 
                        mt.*,
                        s.name as sector_name
                    FROM meter_tree mt
                    LEFT JOIN sectors s ON mt.sector_id = s.id
                    ORDER BY mt.path
                """
                cursor.execute(query, (self.sector_id, self.sector_id))
                all_nodes = cursor.fetchall()

            # تحويل إلى صيغة العرض
            display_data = []
            self.original_customers_data = []
            now = datetime.now()

            for node in all_nodes:
                # تحديد ما إذا كان يجب عرض السحب القديم (خلال 3 أيام)
                withdrawal_updated_at = node.get('withdrawal_updated_at')
                show_previous = False
                if withdrawal_updated_at and isinstance(withdrawal_updated_at, datetime):
                    if (now - withdrawal_updated_at).days < 3:
                        show_previous = True

                # قيمة السحب القديم المعروضة
                previous_display = node.get('previous_withdrawal', 0) if show_previous else node.get('withdrawal_amount', 0)

                # بيانات العرض
                row_display = {
                    'id': node['id'],
                    'علبة': node.get('box_number', ''),
                    'مسلسل': node.get('serial_number', ''),
                    'اسم الزبون': node['name'],
                    'نوع العداد': node.get('meter_type', ''),
                    'القطاع': node.get('sector_name', ''),
                    'التأشيرة الحالية': node.get('visa_balance', 0),
                    'التأشيرة الجديدة': node.get('visa_balance', 0),
                    'الرصيد الحالي': node.get('current_balance', 0),
                    'السحب الحالي': node.get('withdrawal_amount', 0),   # هذا هو السحب الجديد (بعد آخر تحديث)
                    'السحب القديم': previous_display,                    # القيمة التي سيتم عرضها (حسب الشرط)
                    'updated_at': node.get('updated_at'),
                    'previous_withdrawal': node.get('previous_withdrawal', 0),
                    'withdrawal_updated_at': withdrawal_updated_at,
                }
                display_data.append(row_display)

                # البيانات الأصلية للحفظ
                original_row = {
                    'id': node['id'],
                    'علبة': node.get('box_number', ''),
                    'مسلسل': node.get('serial_number', ''),
                    'اسم الزبون': node['name'],
                    'القطاع': node.get('sector_name', ''),
                    'التأشيرة الحالية': float(node.get('visa_balance', 0)),
                    'التأشيرة الجديدة': float(node.get('visa_balance', 0)),
                    'الرصيد الحالي': float(node.get('current_balance', 0)),
                    'السحب الحالي': float(node.get('withdrawal_amount', 0)),
                    'previous_withdrawal': float(node.get('previous_withdrawal', 0)),
                    'withdrawal_updated_at': withdrawal_updated_at,
                    'updated_at': node.get('updated_at')
                }
                self.original_customers_data.append(original_row)

            # حساب الإحصاءات
            total_visa = sum(float(c['التأشيرة الحالية']) for c in self.original_customers_data)
            total_balance = sum(float(c['الرصيد الحالي']) for c in self.original_customers_data)

            # عرض البيانات في الجدول مع إضافة عمودي السحب القديم والجديد
            visible_columns = ["علبة", "مسلسل", "اسم الزبون", "نوع العداد", "القطاع", 
                            "التأشيرة الحالية", "التأشيرة الجديدة", "السحب القديم", "السحب الحالي"]
            self.display_customers(display_data, visible_columns)

            # تحديث الإحصاءات
            self.stats_label.config(
                text=f"عدد العدادات: {len(all_nodes)} | إجمالي التأشيرات: {total_visa:,.0f} | إجمالي الأرصدة: {total_balance:,.0f}"
            )

            logger.info(f"تم تحميل {len(all_nodes)} عداد للقطاع {self.sector_name}")

        except Exception as e:
            logger.error(f"خطأ في تحميل العدادات: {e}")
            messagebox.showerror("خطأ", f"فشل تحميل البيانات: {e}")
        finally:
            self.save_btn.config(text="💾 حفظ التعديلات (Ctrl+S)")
            self.save_bottom_btn.config(text="💾 حفظ التعديلات")
            self.update_save_button_status()
            

    def display_customers(self, data: List[Dict], visible_columns: List[str] = None):
        """عرض الزبائن في الجدول مع إمكانية تحديد الأعمدة المرئية"""
        # تنظيف الحاوية السابقة
        for widget in self.table_container.winfo_children():
            widget.destroy()
        
        if not data:
            self.status_label.config(text="لا يوجد عدادات في هذا القطاع")
            self.save_status_label.config(text="❌ لا توجد بيانات", foreground='red')
            self.update_save_button_status()
            return
        
        # تحديث ملصق الحالة
        self.status_label.config(text=f"تم تحميل {len(data)} عداد - يمكنك التعديل الآن")
        
        # تحديد الأعمدة المرئية
        if visible_columns is None:
            visible_columns = ["علبة", "مسلسل", "اسم الزبون", "نوع العداد", "القطاع", 
                            "التأشيرة الحالية", "التأشيرة الجديدة"]
        
        # إنشاء الجدول المحسن
        self.table = ExcelLikeTable(self.table_container, visible_columns, data)
        self.table.pack(fill=tk.BOTH, expand=True)
        
        # تحديث قائمة البحث
        if hasattr(self, 'search_column_combo'):
            self.search_column_combo['values'] = ["الكل"] + visible_columns
        
        # تحديث حالة الزر
        self.save_status_label.config(text="✅ البيانات جاهزة للتعديل", foreground='green')
    
    def reset_changes(self):
        """استعادة القيم الأصلية"""
        if hasattr(self, 'table'):
            modified_data = self.table.get_modified_data()
            if not modified_data:
                messagebox.showinfo("لا توجد تعديلات", "لا توجد تعديلات لاستعادتها")
                return
            
            if messagebox.askyesno("استعادة التعديلات", 
                                  f"هل تريد استعادة {len(modified_data)} تعديلات إلى قيمها الأصلية؟"):
                self.save_btn.config(state='disabled', text="⏳ جاري الاستعادة...", bg='#FF9800')
                self.save_bottom_btn.config(state='disabled', text="⏳ جاري الاستعادة...", bg='#FF9800')
                self.save_status_label.config(text="⏳ جاري استعادة القيم الأصلية...", foreground='orange')
                self.window.update()
                
                # إعادة تحميل البيانات
                self.load_customers()
    
    def export_to_excel(self):
        """تصدير البيانات إلى ملف Excel"""
        try:
            if not hasattr(self, 'table'):
                messagebox.showwarning("لا توجد بيانات", "لا توجد بيانات للتصدير")
                return
            
            import pandas as pd
            from datetime import datetime
            
            # الحصول على جميع البيانات
            all_data = self.table.get_all_data()
            
            if not all_data:
                messagebox.showwarning("لا توجد بيانات", "لا توجد بيانات للتصدير")
                return
            
            # تحويل البيانات إلى DataFrame
            df_data = []
            for row in all_data:
                df_row = {}
                for key, value in row.items():
                    df_row[key] = value
                df_data.append(df_row)
            
            df = pd.DataFrame(df_data)
            
            # إضافة عمود "الفرق" إذا كانت هناك تعديلات
            modified_data = self.table.get_modified_data()
            if modified_data:
                differences = []
                for mod_row in modified_data:
                    differences.append(float(mod_row['التأشيرة_الجديدة'].replace(',', '')) - 
                                      float(mod_row['التأشيرة_الحالية_أصلية']))
                
                # إضافة الفروق إلى DataFrame
                diff_series = pd.Series(differences, index=[i for i in range(len(differences))])
                df['الفرق'] = diff_series
            
            # اختيار الملف للتصدير
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"تأشيرات_{self.sector_name}_{timestamp}.xlsx"
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                initialfile=default_filename
            )
            
            if file_path:
                # تصدير إلى Excel
                df.to_excel(file_path, index=False, engine='openpyxl')
                messagebox.showinfo("نجاح", f"تم التصدير إلى:\n{file_path}")
                
        except ImportError:
            messagebox.showerror("خطأ", "لم يتم العثور على مكتبة pandas. الرجاء تثبيتها باستخدام: pip install pandas openpyxl")
        except Exception as e:
            logger.error(f"خطأ في التصدير: {e}")
            messagebox.showerror("خطأ", f"فشل التصدير: {e}")

         # modules/visa_editor.py

        # ... [ExcelLikeTable class remains exactly the same, no changes needed] ...

    
    def parse_number(self, value):
        """تحويل القيمة إلى رقم عشري مع معالجة الفواصل والنقاط"""
        if value is None:
            return 0.0
        
        # تحويل إلى سلسلة إذا لم يكن كذلك
        str_value = str(value).strip()
        
        # إذا كانت السلسلة فارغة
        if not str_value:
            return 0.0
        
        # إزالة أي رموز غير رقمية (مثل العملة)
        str_value = re.sub(r'[^\d.,-]', '', str_value)
        
        # إذا كانت تحتوي على فاصلة ونقطة، نفترض أن الفاصلة هي فاصل آلاف
        if ',' in str_value and '.' in str_value:
            # إزالة الفواصل (فاصل آلاف) والحفاظ على النقطة كفاصل عشري
            str_value = str_value.replace(',', '')
        
        # إذا كانت تحتوي على فاصلة فقط، تحقق إذا كانت فاصلة آلاف أو عشرية
        elif ',' in str_value:
            # تحقق إذا كانت الفاصلة تستخدم كفاصل آلاف (مثل 1,949)
            parts = str_value.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # إذا كان الجزء بعد الفاصلة يحتوي على رقمين أو أقل، قد تكون فاصلة عشرية
                str_value = str_value.replace(',', '.')
            else:
                # خلاف ذلك، افترض أنها فاصلة آلاف
                str_value = str_value.replace(',', '')
        
        # محاولة التحويل إلى float
        try:
            # معالجة القيم السالبة
            if str_value.endswith('-'):
                str_value = '-' + str_value[:-1]
            
            return float(str_value)
        except (ValueError, TypeError):
            # إذا فشل التحويل، حاول إزالة أي أحرف غير رقمية
            try:
                # استخراج الأرقام فقط
                digits = re.sub(r'[^\d.-]', '', str_value)
                if digits:
                    return float(digits)
                else:
                    return 0.0
            except:
                return 0.0
    
    def format_number(self, value):
        """تنسيق الرقم للعرض مع فواصل الآلاف"""
        try:
            num = float(value)
            # استخدام تنسيق بدون منازع عشرية
            formatted = f"{num:,.0f}"
            return formatted
        except (ValueError, TypeError):
            return str(value)
        
    def save_changes(self):
        """حفظ التعديلات مع السماح بالتخفيض فقط بإدخال الرمز"""
        if not hasattr(self, 'table'):
            messagebox.showinfo("لا توجد بيانات", "لا توجد بيانات للحفظ")
            return
        
        modified_data = self.table.get_modified_data()
        if not modified_data:
            messagebox.showinfo("لا توجد تغييرات", "لم تقم بأي تعديلات")
            return
        
        # تغيير مظهر زر الحفظ
        self.save_btn.config(state='disabled', text="⏳ جاري الحفظ...", bg='#FF9800')
        self.save_bottom_btn.config(state='disabled', text="⏳ جاري الحفظ...", bg='#FF9800')
        self.save_status_label.config(text="⏳ جاري حفظ التعديلات...", foreground='orange')
        self.window.update()
        
        # فحص وجود تخفيضات
        decrease_rows = []
        for mod_row in modified_data:
            old_visa = self.parse_number(mod_row['التأشيرة_الحالية_أصلية'])
            new_visa = self.parse_number(mod_row['التأشيرة_الجديدة'])
            if new_visa < old_visa:
                decrease_rows.append(mod_row)
        
        allow_decrease = False
        if decrease_rows:
            # طلب الرمز الخاص
            special_code = simpledialog.askstring(
                "تأكيد التخفيض",
                f"يوجد {len(decrease_rows)} تعديل(ات) بقيمة أقل من السابق.\n"
                "الرجاء إدخال الرمز الخاص للموافقة على هذه التخفيضات:",
                parent=self.window,
                show='*'
            )
            allow_decrease = (special_code == "eyadkasem")
            if not allow_decrease and special_code is not None:
                # الرمز خاطئ – سنحفظ فقط الزيادات ونتجاهل التخفيضات
                messagebox.showwarning("تنبيه", 
                    "الرمز غير صحيح. سيتم حفظ التعديلات التي تزيد القيمة فقط،\n"
                    "أما التخفيضات فلن يتم حفظها.")
            elif special_code is None:
                # المستخدم ألغى
                self.update_save_button_status()
                return
        
        try:
            total_updated = 0
            skipped_decreases = 0
            failed_updates = []
            
            with db.get_cursor() as cursor:
                for mod_row in modified_data:
                    try:
                        customer_id = mod_row['id']
                        if not customer_id:
                            failed_updates.append(f"الزبون {mod_row.get('علبة')}/{mod_row.get('مسلسل')}: لا يوجد معرف")
                            continue
                        
                        old_visa = self.parse_number(mod_row['التأشيرة_الحالية_أصلية'])
                        new_visa = self.parse_number(mod_row['التأشيرة_الجديدة'])
                        difference = new_visa - old_visa
                        
                        if abs(difference) < 0.01:
                            continue  # لا تغيير فعلي
                        
                        # إذا كان تخفيضاً والرمز غير مسموح → نتخطاه
                        if difference < 0 and not allow_decrease:
                            skipped_decreases += 1
                            continue
                        
                        # البحث عن البيانات الأصلية الكاملة
                        original_customer = next(
                            (c for c in self.original_customers_data if c.get('id') == customer_id),
                            None
                        )
                        if not original_customer:
                            failed_updates.append(f"الزبون {customer_id}: لم يتم العثور على البيانات الأصلية")
                            continue
                        
                        old_balance = self.parse_number(original_customer.get('الرصيد الحالي', 0))
                        old_withdrawal = self.parse_number(original_customer.get('السحب الحالي', 0))
                        
                        new_balance = old_balance - difference
                        new_withdrawal = difference
                        
                        # تحديث قاعدة البيانات
                        cursor.execute("""
                            UPDATE customers 
                            SET visa_balance = %s,
                                current_balance = %s,
                                withdrawal_amount = %s,
                                previous_withdrawal = %s,
                                withdrawal_updated_at = CURRENT_TIMESTAMP,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (new_visa, new_balance, new_withdrawal, old_withdrawal, customer_id))
                        
                        # سجل تاريخي
                        cursor.execute("""
                            INSERT INTO customer_history 
                            (customer_id, action_type, transaction_type, amount, 
                            balance_before, balance_after,
                            current_balance_before, current_balance_after,
                            old_value, new_value, notes, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            customer_id,
                            'visa_update',
                            'تحديث تأشيرة',
                            difference,
                            old_visa,
                            new_visa,
                            old_balance,
                            new_balance,
                            old_visa,
                            new_visa,
                            f'تعديل مباشر - تأشيرة من {self.format_number(old_visa)} إلى {self.format_number(new_visa)}',
                            self.user_id
                        ))
                        
                        total_updated += 1
                        
                    except Exception as e:
                        customer_info = f"{mod_row.get('علبة', '')}/{mod_row.get('مسلسل', '')}"
                        failed_updates.append(f"{customer_info}: {str(e)}")
            
            # عرض النتيجة
            if total_updated > 0 or skipped_decreases > 0:
                msg_parts = []
                if total_updated > 0:
                    msg_parts.append(f"✅ تم تحديث {total_updated} زبون بنجاح")
                if skipped_decreases > 0:
                    msg_parts.append(f"⏭️ تم تخطي {skipped_decreases} تخفيض (غير مصرح به)")
                if failed_updates:
                    msg_parts.append(f"❌ فشل تحديث {len(failed_updates)} زبون")
                    if len(failed_updates) <= 5:
                        msg_parts.append("الأخطاء:\n" + "\n".join(failed_updates))
                    else:
                        msg_parts.append(f"أول 5 أخطاء:\n" + "\n".join(failed_updates[:5]))
                
                messagebox.showinfo("نتيجة الحفظ", "\n\n".join(msg_parts))
                
                self.save_btn.config(text="✅ تم الحفظ!", bg='#2E7D32')
                self.save_bottom_btn.config(text="✅ تم الحفظ!", bg='#2E7D32')
                self.save_status_label.config(
                    text=f"✅ تم حفظ {total_updated} تعديل" + 
                        (f" (تخطي {skipped_decreases} تخفيض)" if skipped_decreases else ""),
                    foreground='green'
                )
                
                # إعادة تحميل البيانات بعد ثانيتين
                self.window.after(2000, self.load_customers)
            else:
                if failed_updates:
                    messagebox.showerror("خطأ", "فشل تحديث جميع الزبائن:\n" + "\n".join(failed_updates[:10]))
                else:
                    messagebox.showinfo("لا توجد تغييرات", "لم يتم تحديث أي زبون")
                self.update_save_button_status()
        
        except Exception as e:
            logger.error(f"خطأ في حفظ التعديلات: {e}")
            messagebox.showerror("خطأ", f"فشل حفظ التعديلات: {e}")
            self.save_btn.config(text="❌ فشل الحفظ", bg='#f44336')
            self.save_bottom_btn.config(text="❌ فشل الحفظ', bg='#f44336'")
            self.save_status_label.config(text="❌ حدث خطأ أثناء الحفظ", foreground='red')
        
        self.window.after(3000, self.update_save_button_status)


        
    

def open_visa_editor(parent, user_id: int):
    """فتح محرر التأشيرات"""
    editor = VisaEditor(parent, user_id)
    return editor.window


   

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    
    editor = VisaEditor(root, user_id=1)
    root.mainloop()   


