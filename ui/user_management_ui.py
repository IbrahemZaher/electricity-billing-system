# ui/user_management_ui.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import csv
import json
from datetime import datetime
from auth.authentication import auth
from auth.permissions import has_permission, require_permission
from database.connection import db  # تغيير هنا
from auth.permission_engine import permission_engine  # تغيير هنا
import psycopg2
from auth.session import Session

logger = logging.getLogger(__name__)


class UsersUI:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.create_widgets()
        self.load_users()
        self.after_id = None  # لتخزين معرف after للبحث المؤجل

    def create_widgets(self):
        """إنشاء واجهة إدارة المستخدمين"""
        for widget in self.parent.winfo_children():
            widget.destroy()

        frame = ttk.Frame(self.parent)
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        title = ttk.Label(frame, text="إدارة المستخدمين", font=("Arial", 20, "bold"))
        title.pack(pady=10)

        # أزرار الإدارة
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', pady=10)

        self.add_button = ttk.Button(btn_frame, text="إضافة مستخدم جديد", command=self.add_user)
        self.add_button.pack(side='left', padx=5)

        self.edit_button = ttk.Button(btn_frame, text="تعديل مستخدم", command=self.edit_user)
        self.edit_button.pack(side='left', padx=5)

        self.delete_button = ttk.Button(btn_frame, text="تعطيل مستخدم", command=self.delete_user)
        self.delete_button.pack(side='left', padx=5)

        ttk.Button(btn_frame, text="صلاحيات المستخدم", command=self.open_user_permissions).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="تصدير قائمة المستخدمين", command=self.export_users).pack(side='left', padx=5)

        # شريط البحث مع debounce
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill='x', pady=5)

        ttk.Label(search_frame, text="بحث:").pack(side='left', padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side='left', padx=5, fill='x', expand=True)
        self.search_entry.bind('<KeyRelease>', self.filter_users_debounced)

        # جدول المستخدمين
        columns = ('id', 'username', 'full_name', 'role', 'email', 'created_at', 'status')
        self.tree = ttk.Treeview(frame, columns=columns, show='headings', height=15)

        # تعريف العناوين
        self.tree.heading('id', text='المعرف')
        self.tree.heading('username', text='اسم المستخدم')
        self.tree.heading('full_name', text='الاسم الكامل')
        self.tree.heading('role', text='الدور')
        self.tree.heading('email', text='البريد الإلكتروني')
        self.tree.heading('created_at', text='تاريخ الإنشاء')
        self.tree.heading('status', text='الحالة')

        # تعيين عرض الأعمدة
        self.tree.column('id', width=60)
        self.tree.column('username', width=120)
        self.tree.column('full_name', width=150)
        self.tree.column('role', width=100)
        self.tree.column('email', width=180)
        self.tree.column('created_at', width=120)
        self.tree.column('status', width=80)

        self.tree.pack(fill='both', expand=True, pady=10)

        # معلومات إحصائية
        stats_frame = ttk.Frame(frame)
        stats_frame.pack(fill='x', pady=10)

        self.stats_label = ttk.Label(stats_frame, text="جاري تحميل الإحصائيات...")
        self.stats_label.pack()

        # تعطيل الأزرار إذا لم يكن لدى المستخدم الصلاحية
        if not has_permission('system.manage_users'):
            self.add_button.config(state='disabled')
            self.edit_button.config(state='disabled')
            self.delete_button.config(state='disabled')

    def load_users(self):
        """تحميل قائمة المستخدمين من قاعدة البيانات"""
        try:
            with db.get_cursor() as cursor:  # تغيير هنا
                cursor.execute("""
                    SELECT id, username, full_name, role, email, created_at, is_active
                    FROM users
                    ORDER BY id
                """)
                rows = cursor.fetchall()

            # مسح الجدول أولاً
            for item in self.tree.get_children():
                self.tree.delete(item)

            # إضافة البيانات
            active_count = 0
            admin_count = 0
            accountant_count = 0
            cashier_count = 0
            viewer_count = 0

            for row in rows:
                # نحدد النص المعروض للحالة
                status = "نشط" if row['is_active'] else "معطل"
                display_name = row['full_name'] or row['username']

                # تنسيق التاريخ
                created_at = row.get('created_at')
                if created_at:
                    if isinstance(created_at, datetime):
                        created_display = created_at.strftime('%Y-%m-%d %H:%M')
                    else:
                        created_display = str(created_at)
                else:
                    created_display = ''

                self.tree.insert('', 'end', values=(
                    row['id'],
                    row['username'],
                    display_name,
                    row['role'],
                    row.get('email', ''),
                    created_display,
                    status
                ))

                # للإحصائيات
                if row['is_active']:
                    active_count += 1
                if row['role'] == 'admin':
                    admin_count += 1
                elif row['role'] == 'accountant':
                    accountant_count += 1
                elif row['role'] == 'cashier':
                    cashier_count += 1
                elif row['role'] == 'viewer':
                    viewer_count += 1

            # تحديث الإحصائيات
            self.stats_label.config(
                text=f"إجمالي المستخدمين: {len(rows)} | "
                     f"النشطين: {active_count} | "
                     f"المديرين: {admin_count} | "
                     f"المحاسبين: {accountant_count} | "
                     f"أمناء الصندوق: {cashier_count} | "
                     f"المشاهدين: {viewer_count}"
            )

            logger.info(f"تم تحميل {len(rows)} مستخدم من قاعدة البيانات")
            return rows
        except psycopg2.DatabaseError as e:
            logger.error(f"خطأ في قاعدة البيانات أثناء تحميل المستخدمين: {e}", exc_info=True)
            messagebox.showerror("خطأ", "فشل الاتصال بقاعدة البيانات")
            return []
        except Exception as e:
            logger.error(f"خطأ غير متوقع أثناء تحميل المستخدمين: {e}", exc_info=True)
            messagebox.showerror("خطأ", "حدث خطأ غير متوقع")
            return []

    def filter_users_debounced(self, event=None):
        """فلترة المستخدمين مع debounce لتحسين الأداء"""
        if self.after_id:
            try:
                self.parent.after_cancel(self.after_id)
            except Exception:
                pass

        # إلغاء البحث إذا كان الحقل فارغاً
        if not self.search_var.get().strip():
            self.load_users()
            return

        # جدولة البحث بعد 300ms
        self.after_id = self.parent.after(300, self.filter_users)

    def filter_users(self):
        """فلترة المستخدمين حسب البحث"""
        search_term = self.search_var.get().strip().lower()

        if not search_term:
            self.load_users()
            return

        try:
            with db.get_cursor() as cursor:  # تغيير هنا
                cursor.execute("""
                    SELECT id, username, full_name, role, email, created_at, is_active
                    FROM users 
                    WHERE LOWER(username) LIKE %s 
                       OR LOWER(full_name) LIKE %s 
                       OR LOWER(email) LIKE %s 
                       OR LOWER(role) LIKE %s
                    ORDER BY id
                """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
                rows = cursor.fetchall()

            # مسح الجدول أولاً
            for item in self.tree.get_children():
                self.tree.delete(item)

            for row in rows:
                status = "نشط" if row['is_active'] else "معطل"
                display_name = row['full_name'] or row['username']

                # تنسيق التاريخ
                created_at = row.get('created_at')
                if created_at:
                    if isinstance(created_at, datetime):
                        created_display = created_at.strftime('%Y-%m-%d %H:%M')
                    else:
                        created_display = str(created_at)
                else:
                    created_display = ''

                self.tree.insert('', 'end', values=(
                    row['id'],
                    row['username'],
                    display_name,
                    row['role'],
                    row.get('email', ''),
                    created_display,
                    status
                ))

            self.stats_label.config(text=f"تم العثور على {len(rows)} مستخدم")

        except Exception as e:
            logger.error(f"خطأ في فلترة المستخدمين: {e}")
            messagebox.showerror("خطأ", f"فشل فلترة المستخدمين: {str(e)}")

    def add_user(self):
        """إضافة مستخدم جديد"""
        # التحقق من الصلاحية
        try:
            require_permission('system.manage_users')
        except PermissionError as e:
            messagebox.showerror("خطأ في الصلاحية", str(e))
            return

        logger.info("فتح نافذة إضافة مستخدم جديد")

        # نافذة إضافة مستخدم
        top = tk.Toplevel(self.parent)
        top.title("إضافة مستخدم جديد")
        top.geometry("400x350")
        top.transient(self.parent)
        top.grab_set()

        ttk.Label(top, text="اسم المستخدم:*").pack(pady=5)
        entry_username = ttk.Entry(top)
        entry_username.pack(pady=5)

        ttk.Label(top, text="الاسم الكامل:").pack(pady=5)
        entry_fullname = ttk.Entry(top)
        entry_fullname.pack(pady=5)

        ttk.Label(top, text="البريد الإلكتروني:").pack(pady=5)
        entry_email = ttk.Entry(top)
        entry_email.pack(pady=5)

        ttk.Label(top, text="الدور:*").pack(pady=5)
        role_var = tk.StringVar()
        role_combo = ttk.Combobox(top, textvariable=role_var,
                                  values=['admin', 'accountant', 'cashier', 'viewer'])
        role_combo.pack(pady=5)

        ttk.Label(top, text="كلمة المرور:*").pack(pady=5)
        entry_password = ttk.Entry(top, show="*")
        entry_password.pack(pady=5)

        ttk.Label(top, text="تأكيد كلمة المرور:*").pack(pady=5)
        entry_password_confirm = ttk.Entry(top, show="*")
        entry_password_confirm.pack(pady=5)

        def submit():
            username = entry_username.get().strip()
            full_name = entry_fullname.get().strip()
            email = entry_email.get().strip()
            role = role_var.get()
            password = entry_password.get()
            password_confirm = entry_password_confirm.get()

            # التحقق من الحقول المطلوبة
            if not username or not password or not role:
                messagebox.showerror("خطأ", "جميع الحقول المميزة ب * إلزامية")
                return

            if password != password_confirm:
                messagebox.showerror("خطأ", "كلمة المرور غير متطابقة")
                return

            if role not in ('admin', 'accountant', 'cashier', 'viewer'):
                messagebox.showerror("خطأ", "الدور غير صالح")
                return

            # التحقق من عدم تكرار اسم المستخدم أو البريد الإلكتروني (note: atomicity handled by register_user)
            try:
                with db.get_cursor() as cursor:  # تغيير هنا
                    cursor.execute("SELECT id FROM users WHERE username=%s OR email=%s",
                                   (username, email))
                    if cursor.fetchone():
                        messagebox.showerror("خطأ", "اسم المستخدم أو البريد الإلكتروني مستخدم بالفعل")
                        return
            except Exception as e:
                logger.error(f"خطأ في التحقق من التكرار: {e}")
                messagebox.showerror("خطأ", "فشل التحقق من بيانات المستخدم")
                return

            data = {
                'username': username,
                'full_name': full_name,
                'password': password,
                'role': role,
                'email': email,
                'permissions': {}
            }

            # Note: لا نسجل كلمات المرور
            logger.info(f"محاولة إنشاء مستخدم جديد: {username}")

            result = auth.register_user(data)
            if result.get('success'):
                messagebox.showinfo("نجاح", "تم إنشاء المستخدم بنجاح")
                # تسجيل النشاط
                try:
                    auth.log_activity(auth.current_user_id, 'add_user', f'تم إضافة المستخدم {username}')
                except Exception:
                    logger.exception("فشل تسجيل النشاط بعد إنشاء المستخدم")
                top.destroy()
                self.load_users()
            else:
                messagebox.showerror("فشل", result.get('error', 'حدث خطأ غير معروف'))

        ttk.Button(top, text="إضافة", command=submit).pack(pady=20)

    def edit_user(self):
        """تعديل مستخدم"""
        try:
            require_permission('system.manage_users')
        except PermissionError as e:
            messagebox.showerror("خطأ في الصلاحية", str(e))
            return

        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "يرجى اختيار مستخدم من القائمة")
            return

        user_data = self.tree.item(selected[0])['values']
        user_id = user_data[0]

        # جلب البيانات الحالية للمستخدم من قاعدة البيانات
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                current_user = cursor.fetchone()
        except Exception as e:
            logger.error(f"خطأ في جلب بيانات المستخدم: {e}")
            messagebox.showerror("خطأ", "فشل تحميل بيانات المستخدم")
            return

        # نافذة التعديل
        top = tk.Toplevel(self.parent)
        top.title("تعديل مستخدم")
        top.geometry("400x400")  # زيادة الارتفاع لاستيعاب حقلي كلمة المرور
        top.transient(self.parent)
        top.grab_set()

        # حقول النموذج
        ttk.Label(top, text="اسم المستخدم:*").pack(pady=5)
        entry_username = ttk.Entry(top)
        entry_username.insert(0, current_user['username'])
        entry_username.pack(pady=5)

        ttk.Label(top, text="الاسم الكامل:").pack(pady=5)
        entry_fullname = ttk.Entry(top)
        entry_fullname.insert(0, current_user['full_name'] or '')
        entry_fullname.pack(pady=5)

        ttk.Label(top, text="البريد الإلكتروني:").pack(pady=5)
        entry_email = ttk.Entry(top)
        entry_email.insert(0, current_user['email'] or '')
        entry_email.pack(pady=5)

        ttk.Label(top, text="الدور:*").pack(pady=5)
        role_var = tk.StringVar()
        role_combo = ttk.Combobox(top, textvariable=role_var,
                                values=['admin', 'accountant', 'cashier', 'viewer'])
        role_combo.set(current_user['role'])
        role_combo.pack(pady=5)

        # حقول كلمة المرور الجديدة (اختيارية)
        ttk.Label(top, text="كلمة المرور الجديدة (اتركها فارغة لعدم التغيير):").pack(pady=5)
        entry_password = ttk.Entry(top, show="*")
        entry_password.pack(pady=5)

        ttk.Label(top, text="تأكيد كلمة المرور الجديدة:").pack(pady=5)
        entry_password_confirm = ttk.Entry(top, show="*")
        entry_password_confirm.pack(pady=5)

        def submit():
            username = entry_username.get().strip()
            full_name = entry_fullname.get().strip()
            email = entry_email.get().strip()
            role = role_var.get()
            password = entry_password.get().strip()
            password_confirm = entry_password_confirm.get().strip()

            # التحقق من الحقول المطلوبة
            if not username or not role:
                messagebox.showerror("خطأ", "جميع الحقول المميزة ب * إلزامية")
                return

            if role not in ('admin', 'accountant', 'cashier', 'viewer'):
                messagebox.showerror("خطأ", "الدور غير صالح")
                return

            # التحقق من كلمة المرور إذا تم إدخالها
            new_password_hash = None
            if password or password_confirm:
                if password != password_confirm:
                    messagebox.showerror("خطأ", "كلمة المرور غير متطابقة")
                    return
                if len(password) < 6:
                    messagebox.showerror("خطأ", "كلمة المرور قصيرة جدًا (6 أحرف على الأقل)")
                    return
                # تشفير كلمة المرور الجديدة
                from auth.authentication import auth
                new_password_hash = auth.hash_password(password)

            # snapshot قبل التعديل
            before_snapshot = {
                'username': current_user.get('username'),
                'full_name': current_user.get('full_name'),
                'role': current_user.get('role'),
                'email': current_user.get('email')
            }

            try:
                with db.get_cursor() as cursor:
                    if new_password_hash:
                        # تحديث مع تغيير كلمة المرور
                        cursor.execute("""
                            UPDATE users 
                            SET username=%s, full_name=%s, role=%s, email=%s, password_hash=%s,
                                updated_at=CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (username, full_name, role, email, new_password_hash, user_id))
                    else:
                        # تحديث بدون تغيير كلمة المرور
                        cursor.execute("""
                            UPDATE users 
                            SET username=%s, full_name=%s, role=%s, email=%s,
                                updated_at=CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (username, full_name, role, email, user_id))
                    cursor.connection.commit()
            except Exception as e:
                logger.error(f"خطأ في تعديل المستخدم: {e}", exc_info=True)
                try:
                    if 'cursor' in locals() and hasattr(cursor, 'connection'):
                        cursor.connection.rollback()
                except Exception:
                    pass
                messagebox.showerror("خطأ", f"فشل تعديل المستخدم: {str(e)}")
                return

            # مسح كاش الصلاحيات للمستخدم
            try:
                from auth.permission_engine import permission_engine
                permission_engine.clear_cache(user_id)
            except Exception:
                logger.exception("فشل مسح كاش الصلاحيات")

            # إعادة تحميل القائمة
            self.load_users()
            top.destroy()
            messagebox.showinfo("نجاح", "تم تعديل المستخدم بنجاح")

            # snapshot بعد التعديل
            after_snapshot = {
                'username': username,
                'full_name': full_name,
                'role': role,
                'email': email
            }

            # تسجيل النشاط مع snapshots
            try:
                from auth.authentication import auth
                auth.log_activity(
                    Session.current_user['id'] if Session.is_authenticated() else 1,
                    'edit_user',
                    f'تم تعديل المستخدم {user_id}',
                    ip_address=None,
                    request_id=None,
                    before_snapshot=json.dumps(before_snapshot),
                    after_snapshot=json.dumps(after_snapshot)
                )
            except Exception:
                logger.exception("فشل تسجيل النشاط بعد التعديل")

        ttk.Button(top, text="حفظ", command=submit).pack(pady=20)
        

    def delete_user(self):
        """حذف (تعطيل) مستخدم"""
        # التحقق من الصلاحية
        try:
            require_permission('system.manage_users')
        except PermissionError as e:
            messagebox.showerror("خطأ في الصلاحية", str(e))
            return

        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "يرجى اختيار مستخدم من القائمة")
            return

        user_data = self.tree.item(selected[0])['values']
        user_id = user_data[0]
        username = user_data[1]

        # منع تعطيل النفس
        if user_id == auth.current_user_id:
            messagebox.showerror("خطأ", "لا يمكنك تعطيل حسابك بنفسك")
            return

        # التحقق من آخر إداري
        try:
            with db.get_cursor() as cursor:  # تغيير هنا
                cursor.execute("SELECT role, is_active FROM users WHERE id = %s", (user_id,))
                row = cursor.fetchone()
                if row and row['role'] == 'admin' and row['is_active']:
                    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'admin' AND is_active = TRUE")
                    cnt = cursor.fetchone()['cnt']
                    if cnt <= 1:
                        messagebox.showerror("خطأ", "لا يمكن تعطيل آخر حساب مدير النظام")
                        return
        except Exception as e:
            logger.error(f"خطأ في التحقق من حالة المدير: {e}", exc_info=True)
            messagebox.showerror("خطأ", "فشل التحقق من حالة المستخدم")
            return

        confirm = messagebox.askyesno("تأكيد التعطيل",
                                      f"هل أنت متأكد من تعطيل المستخدم: {username}؟")

        if confirm:
            try:
                with db.get_cursor() as cursor:  # تغيير هنا
                    cursor.execute("""
                        UPDATE users SET is_active = FALSE, updated_at=CURRENT_TIMESTAMP 
                        WHERE id = %s
                    """, (user_id,))
                    cursor.connection.commit()
            except Exception as e:
                logger.error(f"خطأ في تعطيل المستخدم: {e}", exc_info=True)
                try:
                    if 'cursor' in locals() and hasattr(cursor, 'connection'):
                        cursor.connection.rollback()
                except Exception:
                    pass
                messagebox.showerror("خطأ", f"فشل تعطيل المستخدم: {str(e)}")
                return

            # مسح كاش الصلاحيات للمستخدم
            try:
                permission_engine.clear_cache(user_id)
            except Exception:
                logger.exception("فشل مسح كاش الصلاحيات بعد التعطيل")

            # إعادة تحميل القائمة
            self.load_users()
            messagebox.showinfo("نجاح", "تم تعطيل المستخدم بنجاح")

            # تسجيل النشاط
            try:
                auth.log_activity(auth.current_user_id, 'delete_user', f'تم تعطيل المستخدم {user_id}')
            except Exception:
                logger.exception("فشل تسجيل النشاط بعد التعطيل")

    def open_user_permissions(self):
        """فتح واجهة صلاحيات المستخدم"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "يرجى اختيار مستخدم من القائمة")
            return

        user_data = self.tree.item(selected[0])['values']
        user_id = user_data[0]

        # فتح واجهة صلاحيات المستخدم
        try:
            from ui.permission_settings_ui import PermissionSettingsUI
            # إنشاء نافذة جديدة لصلاحيات المستخدم
            top = tk.Toplevel(self.parent)
            top.title(f"صلاحيات المستخدم - {user_data[1]}")
            top.geometry("800x600")
            # تمرير بيانات المستخدم إلى PermissionSettingsUI
            PermissionSettingsUI(top, user_data={'id': user_id, 'username': user_data[1]})
        except ImportError as e:
            logger.error(f"خطأ في استيراد واجهة الصلاحيات: {e}", exc_info=True)
            messagebox.showwarning("تحذير", "واجهة إدارة الصلاحيات غير متاحة حالياً")

    def export_users(self):
        """تصدير قائمة المستخدمين إلى ملف CSV"""
        try:
            # جلب البيانات من قاعدة البيانات
            with db.get_cursor() as cursor:  # تغيير هنا
                cursor.execute("""
                    SELECT id, username, full_name, role, email, created_at, is_active
                    FROM users
                    ORDER BY id
                """)
                rows = cursor.fetchall()

            if not rows:
                messagebox.showinfo("تصدير", "لا توجد بيانات للتصدير")
                return

            # فتح مربع حوار للحفظ
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("ملف CSV", "*.csv"), ("جميع الملفات", "*.*")]
            )

            if not file_path:
                return  # المستخدم ألغى العملية

            # كتابة البيانات إلى ملف CSV
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # كتابة العنوان
                writer.writerow(['ID', 'اسم المستخدم', 'الاسم الكامل', 'الدور',
                                 'البريد الإلكتروني', 'تاريخ الإنشاء', 'الحالة'])

                # كتابة البيانات
                for row in rows:
                    status = "نشط" if row['is_active'] else "معطل"
                    created_at = row.get('created_at')
                    if created_at:
                        if isinstance(created_at, datetime):
                            created_display = created_at.strftime('%Y-%m-%d %H:%M')
                        else:
                            created_display = str(created_at)
                    else:
                        created_display = ''

                    writer.writerow([
                        row['id'],
                        row['username'],
                        row['full_name'] or '',
                        row['role'],
                        row.get('email', ''),
                        created_display,
                        status
                    ])

            messagebox.showinfo("نجاح", f"تم تصدير البيانات إلى:\n{file_path}")
            logger.info(f"تم تصدير {len(rows)} مستخدم إلى {file_path}")

        except Exception as e:
            logger.error(f"خطأ في تصدير المستخدمين: {e}", exc_info=True)
            messagebox.showerror("خطأ", f"فشل تصدير المستخدمين: {str(e)}")