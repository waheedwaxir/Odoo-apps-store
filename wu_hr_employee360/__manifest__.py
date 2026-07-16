# -*- coding: utf-8 -*-
{
    'name': 'Hr Employee Dashboard 360',
    'version': '19.0.2.1.0',
    'category': 'Human Resources/Employees',
    'summary': 'Complete employee insights from hiring to retirement, GPS Geofencing, Timesheet Intelligence, Smart Alert Center. Features dynamically adapt based on installed modules.HRMS, Payroll , Attendance',
    'description': """
Employee 360° Dashboard Enterprise for Odoo 19
Hr Employee, HRMS, Payroll , Attendance 
==============================================
Tagline: Complete employee insights from hiring to retirement.

Key Features:
-------------
1. **Interactive Clickable KPI Cards**: Total, Active, Present, Absent, On Leave, Late, WFH, Probation, Expiring Visas/Contracts, Birthdays, Anniversaries, New Joiners, Attrition.
2. **Workforce Overview & Demographics**: Interactive drill-down charts across Department, Company, Manager, Job Position, Gender, Nationality, Employment Type, Age Group, Experience, and Grade.
3. **Advanced Attendance & GPS Geofencing**: Live GPS check-in Leaflet Map, geofence radius breach alerts, top overtime/late leaderboards, and 365-day attendance heatmap.
4. **Comprehensive Leave & Time-Off Center**: Real-time balance vs taken, department leave availability matrix, and 1-click pending request approval.
5. **Employee Profile 360° Drawer**: Slide-over modal with comprehensive employee data, a dedicated timesheet analytics tab, and instant action triggers.
6. **Employee Timeline**: Complete chronological history — joining date, promotions, transfers, salary revisions, leave records, appraisals, training, awards, and disciplinary actions. Auto-synthesised from existing Odoo data.
7. **Smart Alert System**: Proactive HR notifications with severity levels (Critical / Warning / Info) covering document expiries, contract renewals, probation ends, birthdays, anniversaries, appraisals overdue, and attendance anomalies. Full dismiss/acknowledge workflow.
8. **Interactive Organization Chart**: Draggable/Zoomable 3D hierarchy tree with instant report counts.
9. **Omnibar & QR ID Scanner**: Cmd+K universal fuzzy search across all employee fields + camera/USB barcode ID badge scanning mode.
10. **Universal Export & BI Feeds**: QWeb PDF Executive Summary Reports, Excel dumps, and live OData feeds for Power BI/Tableau.
11. **Dynamic Module Architecture**: The dashboard intelligently adapts to your installed Odoo Apps. Tabs and KPI cards related to specific modules (like Timesheets, Leaves, Attendance, Recruitment, Payroll, and Appraisals) will automatically hide if the respective module is not installed, preventing clutter and ensuring a seamless experience.
    """,
    'author': 'Engr Waheed',
    'website': 'https://www.techman-solutions.com',
    'license': 'OPL-1',
    'depends': [
        'base',
        'web',
        'hr',
        'mail',
    ],
    'data': [
        'security/hr_dashboard_security.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/hr_dashboard_views.xml',
        'report/report_actions.xml',
        'report/hr_dashboard_executive_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'wu_hr_employee360/static/src/scss/dashboard.scss',
            'wu_hr_employee360/static/src/scss/dark_mode.scss',
            'wu_hr_employee360/static/src/xml/kpi_card.xml',
            'wu_hr_employee360/static/src/xml/chart_panel.xml',
            'wu_hr_employee360/static/src/xml/employee_360_drawer.xml',
            'wu_hr_employee360/static/src/xml/attendance_map.xml',
            'wu_hr_employee360/static/src/xml/smart_search.xml',
            'wu_hr_employee360/static/src/xml/org_chart.xml',
            'wu_hr_employee360/static/src/xml/smart_alert_center.xml',
            'wu_hr_employee360/static/src/xml/dashboard_main.xml',
            'wu_hr_employee360/static/src/js/kpi_card.js',
            'wu_hr_employee360/static/src/js/chart_manager.js',
            'wu_hr_employee360/static/src/js/employee_360_drawer.js',
            'wu_hr_employee360/static/src/js/attendance_map.js',
            'wu_hr_employee360/static/src/js/smart_search.js',
            'wu_hr_employee360/static/src/js/org_chart.js',
            'wu_hr_employee360/static/src/js/smart_alert_center.js',
            'wu_hr_employee360/static/src/js/filter_panel.js',
            'wu_hr_employee360/static/src/js/self_service_portal.js',
            'wu_hr_employee360/static/src/js/excel_exporter.js',
            'wu_hr_employee360/static/src/js/dashboard_action.js',
        ],
    },
    'images': [
        'static/description/banner.png',
        'static/description/thumbnail.png',
        'static/description/icon.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
