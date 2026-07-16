/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class KpiCard extends Component {
    static template = "wu_hr_employee360.KpiCard";
    static props = {
        id: { type: String, required: true },
        title: { type: String, required: true },
        value: { type: [Number, String], required: true },
        icon: { type: String, optional: true },
        colorClass: { type: String, optional: true },
        trend: { type: String, optional: true },
        trendUp: { type: Boolean, optional: true },
        subtitle: { type: String, optional: true },
        active: { type: Boolean, optional: true },
        onClick: { type: Function, optional: true },
    };

    onClick() {
        if (this.props.onClick) {
            this.props.onClick(this.props.id);
        }
    }
}
