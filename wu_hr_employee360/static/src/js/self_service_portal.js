/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/**
 * SelfServicePortal — the dashboard view for regular employees.
 * Shows only the current employee's own data:
 *   - My Profile card
 *   - Leave balance widget
 *   - Attendance summary (last 30 days)
 *   - My Timeline (most recent 10 events)
 *   - My Pending requests
 */
export class SelfServicePortal extends Component {
    static template = "wu_hr_employee360.SelfServicePortal";
    static props = {
        dashboardData: { type: Object },
    };

    setup() {
        this.orm          = useService("orm");
        this.notification = useService("notification");
        this.action       = useService("action");

        this.state = useState({
            loading:       true,
            myProfile:     null,
            myTimeline:    [],
            myLeave:       null,
            myAttendance:  null,
        });

        onWillStart(async () => {
            await this._loadMyData();
        });
    }

    async _loadMyData() {
        this.state.loading = true;
        try {
            // Get current employee id from dashboard data (already scoped to self)
            const empList = this.props.dashboardData?.employee_list || [];
            const emp = empList[0] || null;

            if (emp && emp.id) {
                // Load 360 profile for self (timeline, leave, attendance)
                const profile = await this.orm.call(
                    "hr.employee", "get_employee_360_details", [emp.id]
                );
                this.state.myProfile    = profile;
                this.state.myTimeline   = (profile.timeline || []).slice(0, 10);
                this.state.myLeave      = profile.leave || {};
                this.state.myAttendance = profile.attendance || {};
            } else {
                // Fallback: use dashboard data as-is
                this.state.myProfile = { name: "My Profile", id: 0 };
            }
        } catch (e) {
            console.warn("SelfServicePortal: could not load employee data", e);
        } finally {
            this.state.loading = false;
        }
    }

    // ---------------------------------------------------------------- //
    //  Computed helpers                                                  //
    // ---------------------------------------------------------------- //
    get greeting() {
        const hour = new Date().getHours();
        if (hour < 12) return "Good morning";
        if (hour < 17) return "Good afternoon";
        return "Good evening";
    }

    get attendanceSummary() {
        const att = this.state.myAttendance || {};
        return {
            present: att.attendance_rate || 0,
            late:    att.late_days || 0,
            absent:  att.absent_days || 0,
            overtime: att.overtime_hours || 0,
        };
    }

    get leaveBalance() {
        const leave = this.state.myLeave || {};
        return {
            annual:  leave.annual_balance || 0,
            sick:    leave.sick_balance   || 0,
            pending: leave.pending_leave  || 0,
        };
    }

    get pendingRequests() {
        const leave = this.props.dashboardData?.leave_dashboard || {};
        return (leave.leave_records || []).filter(
            r => r.state === 'confirm' || r.state === 'validate1'
        ).slice(0, 5);
    }

    leaveBarWidth(taken, total) {
        if (!total || total <= 0) return "0%";
        return `${Math.min(100, Math.round((taken / total) * 100))}%`;
    }

    timelineColorClass(color) {
        const map = {
            green: "bg-success", blue: "bg-primary", orange: "bg-warning text-dark",
            purple: "bg-purple", red: "bg-danger", teal: "bg-info", gray: "bg-secondary",
        };
        return map[color] || "bg-secondary";
    }

    // ---------------------------------------------------------------- //
    //  Actions                                                           //
    // ---------------------------------------------------------------- //
    async openLeaveRequest() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.leave",
            views: [[false, "form"]],
            target: "new",
            context: { default_holiday_status_id: false },
        });
    }

    async reload() {
        await this._loadMyData();
        this.notification.add(_t("Profile refreshed!"), { type: "success" });
    }
}
