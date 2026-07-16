import polib

translations_to_inject = {
    "Today": "اليوم",
    "Yesterday": "أمس",
    "This Week": "هذا الأسبوع",
    "Last Week": "الأسبوع الماضي",
    "This Month": "هذا الشهر",
    "Last Month": "الشهر الماضي",
    "This Quarter": "هذا الربع",
    "Last Quarter": "الربع الماضي",
    "This Year": "هذا العام",
    "Last Year": "العام الماضي",
    "This Period": "هذه الفترة",
    "Overview": "نظرة عامة",
    "Analytics": "التحليلات",
    "Org Chart": "الهيكل التنظيمي",
    "Recruitment": "التوظيف",
    "Payroll": "مسير الرواتب",
    "Reports": "التقارير",
    "Dashboard": "لوحة المعلومات",
    "All": "الكل"
}

po = polib.pofile('/Users/developer/WS/odoo-19.0/custom-addons/testing-modules/wu_hr_employee360/i18n/ar.po')

updated = 0
for entry in po:
    stripped = entry.msgid.strip()
    if stripped in translations_to_inject:
        entry.msgstr = translations_to_inject[stripped]
        updated += 1
    elif entry.msgid in translations_to_inject:
        entry.msgstr = translations_to_inject[entry.msgid]
        updated += 1

po.save('/Users/developer/WS/odoo-19.0/custom-addons/testing-modules/wu_hr_employee360/i18n/ar.po')
print(f"Injected {updated} translations into ar.po")
