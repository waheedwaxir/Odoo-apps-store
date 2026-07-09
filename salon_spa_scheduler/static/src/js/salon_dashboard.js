/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class SalonDashboard extends Component {
    static template = "salon_spa_scheduler.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            dateFilter: 'all', // 'today', 'this_week', 'this_month', 'all'
            data: {
                total_count: 0,
                draft_count: 0,
                confirmed_count: 0,
                ongoing_count: 0,
                done_count: 0,
                cancel_count: 0,
                total_revenue: 0.0,
                paid_revenue: 0.0,
                unpaid_revenue: 0.0,
                avg_value: 0.0,
                total_commissions: 0.0,
                paid_commissions: 0.0,
                pending_commissions: 0.0,
                total_tips: 0.0,
                paid_tips: 0.0,
                unpaid_tips: 0.0,
                waitlist_count: 0,
                avg_rating: 5.0,
                staff_stats: [],
                service_stats: [],
                recent_appointments: [],
            }
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        const data = await this.orm.call("salon.appointment", "get_dashboard_data", [], {
            date_filter: this.state.dateFilter
        });
        this.state.data = data;
    }

    async changeFilter(filter) {
        this.state.dateFilter = filter;
        await this.loadData();
    }

    formatMonetary(amount) {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
    }

    formatPercent(value, total) {
        if (!total) return '0%';
        return Math.round((value / total) * 100) + '%';
    }

    getStars(rating) {
        const fullStars = Math.floor(rating);
        const halfStar = rating % 1 >= 0.5 ? 1 : 0;
        const emptyStars = 5 - fullStars - halfStar;
        return '★'.repeat(fullStars) + (halfStar ? '½' : '') + '☆'.repeat(emptyStars);
    }

    openAppointments(state = false) {
        let domain = [];
        let name = "All Appointments";
        if (state) {
            domain = [['state', '=', state]];
            const stateLabels = {
                'draft': 'Draft',
                'confirmed': 'Confirmed',
                'progress': 'In Progress',
                'done': 'Done',
                'cancel': 'Cancelled'
            };
            name = `${stateLabels[state] || state} Appointments`;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: "salon.appointment",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            target: "current",
        });
    }

    openAppointment(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "salon.appointment",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openPOS() {
        this.action.doAction("point_of_sale.action_pos_config_kanban");
    }



    openReviews() {
        this.action.doAction("salon_spa_scheduler.action_salon_review");
    }

    openCommissions() {
        this.action.doAction("salon_spa_scheduler.action_salon_commission");
    }

    openTips() {
        this.action.doAction("salon_spa_scheduler.action_salon_staff_tip");
    }

    openStaff(staffId = false) {
        const options = {
            type: "ir.actions.act_window",
            name: "Beauticians/Staff",
            res_model: "salon.staff",
            views: [[false, "list"], [false, "form"]],
            target: "current"
        };
        if (staffId) {
            options.res_id = staffId;
            options.views = [[false, "form"]];
        }
        this.action.doAction(options);
    }
}

registry.category("actions").add("salon_spa_scheduler.dashboard", SalonDashboard);
