import re

filepath = "/Users/developer/WS/odoo-19.0/custom-addons/testing-modules/wu_hr_employee360/i18n/ar.po"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace msgid "something" with the code reference, but ignore msgid ""
# We can use a regex: msgid "(?!")
new_content = re.sub(
    r'^msgid "(.*?)"$',
    lambda m: f'#. odoo-javascript\n#: code:addons/wu_hr_employee360/static/src/xml/dashboard_main.xml:0\nmsgid "{m.group(1)}"' if m.group(1) else m.group(0),
    content,
    flags=re.MULTILINE
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Fixed ar.po successfully.")
