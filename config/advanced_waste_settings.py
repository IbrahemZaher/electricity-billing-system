# config/advanced_waste_settings.py
"""
إعدادات متقدمة لنظام تحليل الهدر التفصيلي
"""

# عتبات الهدر التفصيلية
ADVANCED_WASTE_THRESHOLDS = {
    # هدر العلب
    'box_waste': {
        'critical': 20.0,      # حرج - أحمر
        'high': 15.0,          # عالي - برتقالي
        'medium': 10.0,        # متوسط - أصفر
        'low': 5.0,            # منخفض - أخضر فاتح
        'normal': 2.0          # طبيعي - أخضر داكن
    },
    
    # هدر الشبكة
    'network_waste': {
        'critical': 15.0,      # حرج - أحمر
        'high': 10.0,          # عالي - برتقالي
        'medium': 7.0,         # متوسط - أصفر
        'low': 4.0,            # منخفض - أخضر
        'normal': 2.0          # طبيعي - أزرق
    },
    
    # هدر المولدات
    'generator_waste': {
        'critical': 10.0,      # حرج - أحمر
        'high': 7.0,           # عالي - برتقالي
        'medium': 5.0,         # متوسط - أصفر
        'low': 3.0,            # منخفض - أخضر
        'normal': 1.5          # طبيعي - أزرق
    }
}

# معايير تحليل الزبائن
CUSTOMER_ANALYSIS_CRITERIA = {
    'suspicious_low_consumption': 0.3,      # أقل من 30% من المتوسط
    'suspicious_high_share': 20.0,          # أكثر من 20% من الهدر
    'high_variance_threshold': 2.0,         # انحراف معياري > 2
    'uneven_distribution_threshold': 0.5,   # أعلى 20% يستهلكون أكثر من 50%
    'coefficient_of_variation': 50.0        # معامل الاختلاف > 50%
}

# معايير تحليل العلب
BOX_ANALYSIS_CRITERIA = {
    'large_box_customer_count': 25,         # علبة كبيرة إذا كان لديها أكثر من 25 زبون
    'critical_box_count': 3,                # عدد العلب الحرجة للتنبيه
    'high_waste_box_count': 5,              # عدد العلب عالية الهدر للتنبيه
    'average_waste_threshold': 15.0,        # عتبة متوسط الهدر للقطاع
    'efficiency_excellent': 90.0,           # كفاءة ممتازة
    'efficiency_good': 80.0,                # كفاءة جيدة
    'efficiency_average': 70.0,             # كفاءة متوسطة
    'efficiency_poor': 60.0                 # كفاءة ضعيفة
}

# ألوان الواجهة المتقدمة
ADVANCED_COLORS = {
    # ألوان حسب مستوى الخطورة
    'critical': '#d32f2f',      # أحمر داكن
    'high': '#f57c00',          # برتقالي
    'medium': '#fbc02d',        # أصفر
    'low': '#4caf50',           # أخضر
    'normal': '#2196f3',        # أزرق
    
    # ألوان حسب النوع
    'box': '#5c6bc0',           # بنفسجي أزرق
    'customer': '#26a69a',      # تركواز
    'network': '#ffa726',       # برتقالي فاتح
    'generator': '#ab47bc',     # بنفسجي
    
    # ألوان الواجهة
    'primary': '#283593',       # أزرق داكن
    'secondary': '#3949ab',     # أزرق
    'accent': '#5c6bc0',        # أزرق فاتح
    'light': '#f5f7fa',         # فاتح جداً
    'dark': '#263238',          # داكن
    'success': '#388e3c',       # أخضر داكن
    'warning': '#ffa000',       # برتقالي داكن
    'danger': '#d32f2f',        # أحمر
    'info': '#0288d1',          # أزرق سماوي
    'background': '#fafafa'     # خلفية
}

# إعدادات التقارير المتقدمة
ADVANCED_REPORT_SETTINGS = {
    'auto_refresh_interval': 300,           # التحديث التلقائي كل 5 دقائق
    'save_analysis_history': True,          # حفظ تاريخ التحليلات
    'notify_critical_boxes': True,          # إشعار بالعلب الحرجة
    'notify_high_waste': True,              # إشعار بالهدر العالي
    'generate_daily_reports': True,         # توليد تقارير يومية
    'export_formats': ['pdf', 'excel', 'html', 'json'],  # صيغ التصدير
    'report_retention_days': 90,            # احتفاظ بالتقارير لمدة 90 يوماً
    'auto_backup': True,                    # نسخ احتياطي تلقائي
    'backup_location': './reports/backups/' # موقع النسخ الاحتياطي
}

# إعدادات التحليل المتقدم
ANALYSIS_SETTINGS = {
    'max_network_depth': 10,                # أقصى عمق لتحليل الشبكة
    'min_customers_for_analysis': 3,        # أقل عدد زبائن للتحليل
    'trend_analysis_days': 30,              # عدد الأيام لتحليل الاتجاهات
    'prediction_days': 7,                   # عدد الأيام للتنبؤ
    'confidence_threshold': 0.7,            # عتبة الثقة للتنبؤات
    'seasonal_pattern_days': 7,             # أيام لاكتشاف الأنماط الموسمية
    'peak_detection_sensitivity': 1.5,      # حساسية كشف القمم
    'anomaly_detection_threshold': 3.0      # عتبة كشف الشذوذ
}

# إعدادات الأداء
PERFORMANCE_SETTINGS = {
    'max_concurrent_analyses': 3,           # أقصى عدد تحليلات متزامنة
    'cache_duration': 300,                  # مدة التخزين المؤقت (ثواني)
    'batch_size': 50,                       # حجم الدفعة للمعالجة
    'timeout_seconds': 30,                  # وقت المهلة للتحليلات
    'memory_limit_mb': 512,                 # حد الذاكرة بالميجابايت
    'log_level': 'INFO',                    # مستوى التسجيل
    'debug_mode': False                     # وضع التصحيح
}

# إعدادات التصدير والاستيراد
EXPORT_IMPORT_SETTINGS = {
    'default_export_format': 'excel',       # صيغة التصدير الافتراضية
    'include_charts': True,                 # تضمين الرسوم البيانية
    'include_raw_data': True,               # تضمين البيانات الخام
    'include_analysis': True,               # تضمين التحليل
    'include_recommendations': True,        # تضمين التوصيات
    'compress_files': True,                 # ضغط الملفات
    'password_protect': False,              # حماية بكلمة مرور
    'watermark_reports': True              