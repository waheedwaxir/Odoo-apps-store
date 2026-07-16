# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request, Response


class HrDashboard360Controller(http.Controller):

    @http.route('/api/v1/hr_employee360/bi_feed', type='http', auth='user', methods=['GET'], csrf=False)
    def get_bi_feed(self, **kwargs):
        if not request.env.user.has_group('wu_hr_employee360.group_hr_dashboard_user'):
            return Response(json.dumps({'error': 'Unauthorized: Employee 360 Dashboard access required'}), status=403, content_type='application/json')

        filters = {
            'company_id': kwargs.get('company_id'),
            'branch_id': kwargs.get('branch_id'),
            'department_id': kwargs.get('department_id')
        }
        data = request.env['hr.dashboard.metrics'].get_dashboard_data(filters)
        return Response(json.dumps(data, default=str), status=200, content_type='application/json')

    @http.route('/api/v1/hr_employee360/export_pdf', type='http', auth='user', methods=['GET'])
    def export_pdf_report(self, **kwargs):
        """Generates and downloads the Executive Summary PDF Report via QWeb."""
        if not request.env.user.has_group('wu_hr_employee360.group_hr_dashboard_user'):
            return Response("Unauthorized", status=403)

        pdf_content, _ = request.env['ir.actions.report']._render_qweb_pdf(
            'wu_hr_employee360.action_report_hr_dashboard_executive',
            res_ids=[request.env.user.company_id.id]
        )
        pdfheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', 'attachment; filename="HR_Executive_Dashboard_Summary_360.pdf"')
        ]
        return request.make_response(pdf_content, headers=pdfheaders)
