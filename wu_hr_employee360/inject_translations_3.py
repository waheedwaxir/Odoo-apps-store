import polib

translations_to_inject = {
    "%s%% of total": "%s%% من الإجمالي",
    "%s %s%% vs last month": "%s %s%% مقارنة بالشهر الماضي",
    "%s %s%% of total": "%s %s%% من الإجمالي",
    "0%% of total": "0%% من الإجمالي",
}

po = polib.pofile('/Users/developer/WS/odoo-19.0/custom-addons/testing-modules/wu_hr_employee360/i18n/ar.po')

updated = 0
for entry in po:
    stripped = entry.msgid.strip()
    if stripped in translations_to_inject:
        entry.msgstr = translations_to_inject[stripped]
        updated += 1
        
# If they are not in the po file, we add them manually
for key, val in translations_to_inject.items():
    found = False
    for entry in po:
        if entry.msgid == key:
            found = True
            break
    if not found:
        po.append(polib.POEntry(
            msgid=key,
            msgstr=val,
            occurrences=[('models/hr_dashboard_metrics.py', '0')]
        ))
        updated += 1

po.save('/Users/developer/WS/odoo-19.0/custom-addons/testing-modules/wu_hr_employee360/i18n/ar.po')
print(f"Injected {updated} translations into ar.po")
