import sys
env = env
lang = 'ar_001' # wait, what is the exact language code in Odoo? usually 'ar' or 'ar_SY'
# Let's check installed languages
langs = env['res.lang'].search([])
print("Installed languages:", langs.mapped('code'))

# Get web translations for the arabic language
for l in langs:
    if 'ar' in l.code:
        translations = env['ir.http'].get_web_translations(l.code)
        # Check if our strings are in it
        messages = translations.get('messages', [])
        found = False
        for msg in messages:
            if msg.get('id') == 'Total Employees':
                print(f"Found in {l.code}: {msg}")
                found = True
        if not found:
            print(f"Total Employees NOT found in {l.code}")
