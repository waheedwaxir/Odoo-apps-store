import polib

translations_to_inject = {
    "Attendance Overview": "نظرة عامة على الحضور",
    "Attendance Trend": "اتجاه الحضور",
    "Leave Summary": "ملخص الإجازات",
    "Payroll Overview": "نظرة عامة على الرواتب",
    "HR Alerts": "تنبيهات الموارد البشرية",
    "Department Overview": "نظرة عامة على القسم",
    "Recruitment Overview": "نظرة عامة على التوظيف",
    "Employee Distribution": "توزيع الموظفين",
    "Compliance Overview": "نظرة عامة على الامتثال",
    "Smart Calendar": "التقويم الذكي",
    "Today's Activities": "أنشطة اليوم",
    "Top Performers": "أفضل الأداء",
    "Leave Requests": "طلبات الإجازة",
    "Quick Actions": "إجراءات سريعة",
    "Export Layout": "تصدير التخطيط",
    "Import Layout": "استيراد التخطيط",
    "Toggle Dashboard Widgets": "تبديل واجهات لوحة المعلومات"
}

po = polib.pofile('/Users/developer/WS/odoo-19.0/custom-addons/testing-modules/wu_hr_employee360/i18n/ar.po')

updated = 0
for entry in po:
    stripped = entry.msgid.strip()
    if stripped in translations_to_inject:
        entry.msgstr = translations_to_inject[stripped]
        if '#. odoo-javascript' not in entry.flags:
            entry.flags.append('odoo-javascript')
        updated += 1
        
# If they are not in the po file, we add them manually
for key, val in translations_to_inject.items():
    found = False
    for entry in po:
        if entry.msgid.strip() == key:
            found = True
            break
    if not found:
        po.append(polib.POEntry(
            msgid=key,
            msgstr=val,
            flags=['odoo-javascript'],
            occurrences=[('code:addons/wu_hr_employee360/static/src/xml/dashboard_main.xml', '0')]
        ))
        updated += 1

po.save('/Users/developer/WS/odoo-19.0/custom-addons/testing-modules/wu_hr_employee360/i18n/ar.po')
print(f"Injected {updated} translations into ar.po")
