import polib

translations_to_inject = {
    "Total Employees": "إجمالي الموظفين",
    "Present Today": "حاضر اليوم",
    "On Vacation": "في إجازة",
    "Late Today": "متأخر اليوم",
    "Early Checkout": "خروج مبكر",
    "Overtime Today": "وقت إضافي اليوم",
    "New Joiners (": "منضمون جدد (",
    "Leaving (": "مغادرون (",
    "Contracts Expiring (30 Days)": "عقود تنتهي (30 يوماً)",
    "Visa Expiring (30 Days)": "تأشيرات تنتهي (30 يوماً)",
    "Birthdays (": "أعياد ميلاد (",
    "Probation Employees": "موظفون تحت التجربة",
    "Company: All Companies": "الشركة: جميع الشركات",
    "Department: All Departments": "القسم: جميع الأقسام",
    "Monthly Leave Requests Trend": "مؤشر طلبات الإجازة الشهرية",
    "Leave Breakdown by Department": "تفصيل الإجازات حسب القسم",
    "Employment Type Breakdown": "تفصيل أنواع التوظيف",
    "DRILL-DOWN ENABLED": "إمكانية التعمق متاحة",
    "No Department": "بدون قسم",
    "Jan": "يناير",
    "Feb": "فبراير",
    "Mar": "مارس",
    "Apr": "أبريل",
    "May": "مايو",
    "Jun": "يونيو",
    "Jul": "يوليو",
    "Aug": "أغسطس",
    "Sep": "سبتمبر",
    "Oct": "أكتوبر",
    "Nov": "نوفمبر",
    "Dec": "ديسمبر",
    "Annual:": "سنوي:",
    "Sick:": "مرضي:",
    "Unpaid:": "غير مدفوع:",
    "Pending:": "قيد الانتظار:",
    "Leaving (Today)": "المغادرون (اليوم)",
    "New Joiners (Today)": "المنضمون الجدد (اليوم)",
    "Birthdays (Today)": "أعياد الميلاد (اليوم)",
    "Annual Leave Balance": "رصيد الإجازة السنوية",
    "Sick Leave Balance": "رصيد الإجازة المرضية",
    "Leave": "إجازة",
    "Unexcused Absences": "غياب بدون عذر",
    "Top Performers": "أفضل الموظفين أداءً",
    "Top Late Arrivals (Month)": "أكثر المتأخرين (الشهر)"
}

po = polib.pofile('/Users/developer/WS/odoo-19.0/custom-addons/testing-modules/wu_hr_employee360/i18n/ar.po')

updated = 0
for entry in po:
    if entry.msgid in translations_to_inject:
        entry.msgstr = translations_to_inject[entry.msgid]
        updated += 1
    # also strip
    stripped = entry.msgid.strip()
    if stripped in translations_to_inject:
        entry.msgstr = translations_to_inject[stripped]
        updated += 1

po.save('/Users/developer/WS/odoo-19.0/custom-addons/testing-modules/wu_hr_employee360/i18n/ar.po')
print(f"Injected {updated} translations into ar.po")
