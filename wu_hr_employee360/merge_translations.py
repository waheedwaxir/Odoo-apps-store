import polib
import json

pot = polib.pofile('/Users/developer/WS/odoo-19.0/custom-addons/testing-modules/wu_hr_employee360/i18n/wu_hr_employee360.pot')
try:
    po = polib.pofile('/Users/developer/WS/odoo-19.0/custom-addons/testing-modules/wu_hr_employee360/i18n/ar.po')
    existing = {entry.msgid: entry.msgstr for entry in po if entry.msgstr}
except:
    existing = {}

missing = {}
for entry in pot:
    # If the string exists and is translated
    if entry.msgid in existing and existing[entry.msgid]:
        entry.msgstr = existing[entry.msgid]
    else:
        # Check if a stripped version exists
        stripped_id = entry.msgid.strip()
        found = False
        for ex_id, ex_str in existing.items():
            if ex_id.strip() == stripped_id and ex_str:
                entry.msgstr = ex_str
                found = True
                break
        
        if not found and entry.msgid:
            missing[entry.msgid] = ""

pot.save('/Users/developer/WS/odoo-19.0/custom-addons/testing-modules/wu_hr_employee360/i18n/ar.po')

with open('/Users/developer/WS/odoo-19.0/custom-addons/testing-modules/wu_hr_employee360/missing.json', 'w') as f:
    json.dump(missing, f, indent=4)

print(f"Missing translations: {len(missing)}")
