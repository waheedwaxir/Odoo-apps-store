with open('static/description/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace all 15 panel-heading blocks
old_heading_start = '<div class="panel-heading" style="background: #0F172A; color: #FFFFFF; padding: 16px 24px;">'
new_heading_start = '<div class="panel-heading" style="background-color: #F1F5F9; border-bottom: 2px solid #CBD5E1; color: #000000; padding: 20px 24px;">'

content = content.replace(old_heading_start, new_heading_start)
content = content.replace('<h3 style="font-size: 22px; font-weight: 700; margin: 0; color: #FFFFFF;">',
                          '<h3 style="font-size: 26px; font-weight: 800; margin: 0; color: #000000; line-height: 1.3;">')
content = content.replace('<p style="font-size: 15px; color: #94A3B8; margin: 4px 0 0;">',
                          '<p style="font-size: 18px; font-weight: 600; color: #111827; margin: 8px 0 0; line-height: 1.6;">')

# 2. Replace the footer section
old_footer = """<!-- Author & Support Footer (Engr Waheed) -->
<section class="oe_container my-5">
    <div class="p-5 shadow-sm text-center" style="background: linear-gradient(135deg, #1E293B 0%, #0F766E 100%); color: #FFFFFF; border-radius: 16px; border: 1px solid rgba(255,255,255,0.2);">
        <h2 style="font-size: 32px; font-weight: 800; margin-bottom: 12px; color: #FFFFFF;">
            Engineered & Maintained by Engr Waheed
        </h2>
        <p style="font-size: 18px; color: #CCFBF1; max-width: 720px; margin: 0 auto 32px; line-height: 1.6;">
            For enterprise implementation, custom Odoo 19 module development, multi-branch POS configuration, or dedicated technical support, get in touch instantly:
        </p>
        <div class="d-flex justify-content-center flex-wrap" style="gap: 20px;">
            <a href="https://www.linkedin.com/in/waheed-ullah-810082151/" target="_blank" rel="noopener" class="px-4 py-3" style="background: #0A66C2; color: #FFFFFF; font-weight: 700; font-size: 16px; border-radius: 999px; text-decoration: none; box-shadow: 0 6px 16px rgba(0,0,0,0.3); display: inline-flex; align-items: center;">
                <span>🔗 LinkedIn: /in/waheed-ullah-810082151/</span>
            </a>
            <a href="https://wa.me/97430643395" target="_blank" rel="noopener" class="px-4 py-3" style="background: #25D366; color: #FFFFFF; font-weight: 700; font-size: 16px; border-radius: 999px; text-decoration: none; box-shadow: 0 6px 16px rgba(0,0,0,0.3); display: inline-flex; align-items: center;">
                <span>💬 WhatsApp: +974 3064 3395</span>
            </a>
        </div>
    </div>
</section>"""

new_footer = """<!-- Author & Support Footer (Engr Waheed) -->
<section class="oe_container my-5">
    <div class="p-5 shadow-sm text-center" style="background-color: #F8FAFC; color: #000000; border-radius: 16px; border: 3px solid #CBD5E1;">
        <h2 style="font-size: 36px; font-weight: 800; margin-bottom: 14px; color: #000000;">
            Engineered & Maintained by Engr Waheed
        </h2>
        <p style="font-size: 20px; font-weight: 700; color: #000000; max-width: 820px; margin: 0 auto 32px; line-height: 1.6;">
            For enterprise implementation, custom Odoo 19 module development, multi-branch POS configuration, or dedicated technical support, get in touch instantly:
        </p>
        <div class="d-flex justify-content-center flex-wrap" style="gap: 20px;">
            <a href="https://www.linkedin.com/in/waheed-ullah-810082151/" target="_blank" rel="noopener" class="px-4 py-3" style="background-color: #FFFFFF; border: 3px solid #000000; color: #000000; font-weight: 800; font-size: 19px; border-radius: 999px; text-decoration: none; box-shadow: 0 6px 16px rgba(0,0,0,0.15); display: inline-flex; align-items: center;">
                <strong style="color: #000000 !important; font-size: 19px;">🔗 LinkedIn: /in/waheed-ullah-810082151/</strong>
            </a>
            <a href="https://wa.me/97430643395" target="_blank" rel="noopener" class="px-4 py-3" style="background-color: #25D366; border: 3px solid #15803D; color: #000000; font-weight: 800; font-size: 19px; border-radius: 999px; text-decoration: none; box-shadow: 0 6px 16px rgba(37,211,102,0.3); display: inline-flex; align-items: center;">
                <strong style="color: #000000 !important; font-size: 19px;">💬 WhatsApp: +974 3064 3395</strong>
            </a>
        </div>
    </div>
</section>"""

if old_footer in content:
    content = content.replace(old_footer, new_footer)
    print("Footer successfully replaced!")
else:
    print("Warning: old_footer not exact match, replacing by regex/string search...")
    # Let's do fallback replacement if spacing varied slightly
    import re
    content = re.sub(r'<!-- Author & Support Footer \(Engr Waheed\) -->.*?<!-- Bootstrap JS for Tabs', new_footer + '\n\n<!-- Bootstrap JS for Tabs', content, flags=re.DOTALL)
    print("Footer replaced via regex!")

with open('static/description/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated index.html successfully!")
