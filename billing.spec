# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ['app.py'],
    pathex=['C:\\Users\\وسام\\Desktop\\electricity_billing_system'],
    binaries=[],
    datas=[
        ('config/settings.py', 'config'),
        ('config/advanced_waste_settings.py', 'config'),
        ('fonts/*', 'fonts'),
        ('logs', 'logs'),
        ('backups', 'backups'),
        ('prints', 'prints'),
        ('setup_database_fixed.sql', '.'),
    ] + collect_data_files('escpos'),   # إضافة ملفات البيانات الخاصة بمكتبة escpos
    hiddenimports=[
        'auth', 'auth.permission_engine', 'auth.permissions', 'auth.session',
        'database.connection', 'database.migrations', 'database.models',
        'modules', 'modules.customers', 'modules.invoices', 'modules.reports',
        'modules.accounting', 'modules.archive', 'modules.backup_engine',
        'modules.export_manager', 'modules.fast_operations', 'modules.history_manager',
        'modules.waste_calculator', 'modules.financial_reports',
        'services.users_service',
        'ui', 'ui.*',
        'utils.excel_handler', 'utils.helpers', 'utils.printer', 'utils.validators',
        # استيرادات خفية للمكتبات
        'pandas', 'pandas._libs.tslibs.timedeltas', 'pandas._libs.tslibs.nattype',
        'psycopg2', 'psycopg2._json', 'psycopg2.extensions',
        'boto3', 'botocore',
        'gnupg',
        'PIL', 'PIL._tkinter_finder',
        'escpos', 'escpos.printer', 'escpos.escpos', 'escpos.constants', 'escpos.exceptions',
        'arabic_reshaper', 'bidi.algorithm',
        'bcrypt', 'jwt',
        'tqdm',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MawladahAlRayyan',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)