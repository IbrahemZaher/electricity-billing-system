-- =====================================================
-- ملف: fix_cash.sql
-- الهدف: حذف جميع المصاريف (العادية + أرباح مدير + أرباح طاقة)
--        وإعادة حساب أرصدة الصندوق اليومي من الصفر
-- =====================================================

BEGIN;

-- 1. حذف جميع المصاريف وأرباح المدير وأرباح الطاقة
DELETE FROM daily_expenses;
SELECT '✅ تم حذف جميع سجلات daily_expenses' AS status;

DELETE FROM profit_distribution;
SELECT '✅ تم حذف جميع سجلات profit_distribution' AS status;

DELETE FROM energy_profit_distribution;
SELECT '✅ تم حذف جميع سجلات energy_profit_distribution' AS status;

-- 2. تحديث الإجماليات في daily_cash (ستصبح 0 باستثناء total_collections)
UPDATE daily_cash dc
SET 
    total_expenses = 0,
    total_profits = 0,
    total_energy_profits = 0;
SELECT '✅ تم تصفير إجماليات المصاريف والأرباح في daily_cash' AS status;

-- 3. إعادة حساب الأرصدة الافتتاحية والختامية بالتسلسل الصحيح
WITH RECURSIVE ordered_days AS (
    SELECT 
        id,
        cash_date,
        COALESCE(total_collections, 0) AS total_collections,
        COALESCE(total_expenses, 0) AS total_expenses,
        COALESCE(total_profits, 0) AS total_profits,
        COALESCE(total_energy_profits, 0) AS total_energy_profits,
        ROW_NUMBER() OVER (ORDER BY cash_date) AS rn
    FROM daily_cash
),
recalc AS (
    SELECT 
        od.id,
        od.rn,
        (dc.opening_balance)::NUMERIC AS new_opening,
        (dc.opening_balance + od.total_collections - od.total_expenses - od.total_profits - od.total_energy_profits)::NUMERIC AS new_closing
    FROM ordered_days od
    JOIN daily_cash dc ON dc.id = od.id
    WHERE od.rn = 1
    
    UNION ALL
    
    SELECT 
        od.id,
        od.rn,
        (r.new_closing)::NUMERIC AS new_opening,
        (r.new_closing + od.total_collections - od.total_expenses - od.total_profits - od.total_energy_profits)::NUMERIC AS new_closing
    FROM ordered_days od
    JOIN recalc r ON od.rn = r.rn + 1
)
UPDATE daily_cash dc
SET 
    opening_balance = r.new_opening,
    closing_balance = r.new_closing,
    updated_at = CURRENT_TIMESTAMP
FROM recalc r
WHERE dc.id = r.id;
SELECT '✅ تم إعادة حساب الأرصدة الافتتاحية والختامية' AS status;

-- 4. عرض أول 5 أيام للتحقق
SELECT cash_date, opening_balance, total_collections, total_expenses, total_profits, total_energy_profits, closing_balance
FROM daily_cash
ORDER BY cash_date
LIMIT 5;

-- 5. التحقق من عدم وجود أرصدة سالبة
SELECT cash_date, closing_balance
FROM daily_cash
WHERE closing_balance < 0;

COMMIT;