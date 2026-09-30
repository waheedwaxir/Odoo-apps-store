import re

with open('reports/product_report.xml', 'r') as f:
    content = f.read()

# Replace d-flex align-items-center in stat-cards with float-based layout
content = content.replace('class="stat-card card-blue d-flex align-items-center"', 'class="stat-card card-blue" style="overflow: hidden;"')
content = content.replace('class="stat-card card-teal d-flex align-items-center"', 'class="stat-card card-teal" style="overflow: hidden;"')
content = content.replace('class="stat-card card-purple d-flex align-items-center"', 'class="stat-card card-purple" style="overflow: hidden;"')
content = content.replace('class="stat-card card-orange d-flex align-items-center"', 'class="stat-card card-orange" style="overflow: hidden;"')
content = content.replace('class="stat-card card-green d-flex align-items-center"', 'class="stat-card card-green" style="overflow: hidden;"')

content = content.replace('class="icon-circle icon-blue me-3"', 'class="icon-circle icon-blue me-3" style="float: left;"')
content = content.replace('class="icon-circle icon-teal me-3"', 'class="icon-circle icon-teal me-3" style="float: left;"')
content = content.replace('class="icon-circle icon-purple me-3"', 'class="icon-circle icon-purple me-3" style="float: left;"')
content = content.replace('class="icon-circle icon-orange me-3"', 'class="icon-circle icon-orange me-3" style="float: left;"')
content = content.replace('class="icon-circle icon-green me-3"', 'class="icon-circle icon-green me-3" style="float: left;"')

# Fix table-custom to prevent wkhtmltopdf thead disappearing bug
# Sometimes adding `page-break-inside: auto;` on table and `page-break-inside: avoid;` on tr helps.
# Also `webkit-print-color-adjust: exact;`
css_fix = """
                        .table-custom { width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 20px; page-break-inside: auto; }
                        .table-custom tr { page-break-inside: avoid; page-break-after: auto; }
                        .table-custom thead { display: table-header-group; }
                        .table-custom tfoot { display: table-row-group; }
"""
content = re.sub(r'\.table-custom \{ width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 20px; \}', css_fix, content)

with open('reports/product_report.xml', 'w') as f:
    f.write(content)
print("Done")
