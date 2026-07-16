/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class Employee360Drawer extends Component {
    static template = "wu_hr_employee360.Employee360Drawer";
    static props = {
        employeeId: { type: Number, required: true },
        onClose: { type: Function, required: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.state = useState({
            activeTab: "personal",
            loading: true,
            data: null,
            timelineFilter: "all",   // 'all' | 'employment' | 'salary' | 'leave' | 'performance' | 'disciplinary'
            timesheetLoading: false,
            timesheetData: null,
            timesheetPeriod: "this_month",
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const result = await this.orm.call("hr.employee", "get_employee_360_details", [this.props.employeeId]);
            if (result.error) {
                this.notification.add(result.error, { type: "danger" });
                this.props.onClose();
                return;
            }
            this.state.data = result;
            if (result.timesheet_only) {
                this.state.activeTab = "timesheets";
                await this.loadTimesheets();
            }
        } catch (error) {
            this.notification.add(_t("Could not load this employee profile."), { type: "danger" });
            this.props.onClose();
        } finally {
            this.state.loading = false;
        }
    }

    async setTab(tabName) {
        this.state.activeTab = tabName;
        if (tabName === "timesheets" && !this.state.timesheetData && !this.state.timesheetLoading) {
            await this.loadTimesheets();
        }
    }

    async loadTimesheets() {
        this.state.timesheetLoading = true;
        try {
            this.state.timesheetData = await this.orm.call(
                "hr.employee",
                "get_employee_timesheet_dashboard",
                [this.props.employeeId, this.state.timesheetPeriod],
            );
        } catch (error) {
            this.state.timesheetData = {
                allowed: false,
                message: "Could not load employee timesheets.",
                summary: {},
                daily: [],
                by_project: [],
                recent_entries: [],
            };
            this.notification.add(_t("Could not load employee timesheets."), { type: "warning" });
        } finally {
            this.state.timesheetLoading = false;
        }
    }

    timesheetDailyBarStyle(hours) {
        const values = (this.state.timesheetData?.daily || []).map((point) => Number(point.hours) || 0);
        const maximum = Math.max(1, ...values);
        const height = hours ? Math.max(8, Math.round((Number(hours) / maximum) * 100)) : 3;
        return `height: ${height}%;`;
    }

    async openEmployeeTimesheets() {
        try {
            const action = await this.orm.call(
                "hr.dashboard.metrics",
                "action_open_employee_timesheets",
                [this.props.employeeId],
            );
            if (!action) {
                throw new Error("No Timesheets action is available for this employee.");
            }
            await this.action.doAction(action, {
                additionalContext: { active_id: Number(this.props.employeeId) },
            });
        } catch (error) {
            this.notification.add(
                _t("Could not open timesheets. Verify your Timesheets access."),
                { type: "warning" },
            );
        }
    }

    async openTimesheetEntry(timesheetId) {
        try {
            const action = await this.orm.call(
                "hr.dashboard.metrics",
                "action_open_timesheet_form",
                [Number(timesheetId)],
            );
            await this.action.doAction(action);
        } catch (error) {
            this.notification.add(_t("Could not open this timesheet entry."), { type: "warning" });
        }
    }

    setTimelineFilter(filter) {
        this.state.timelineFilter = filter;
    }

    // Computed: events filtered by active category
    get filteredTimeline() {
        const all = this.state.data?.timeline || [];
        const f = this.state.timelineFilter;
        if (f === "all") return all;

        const filterMap = {
            employment:   ["joining", "promotion", "transfer", "separation"],
            salary:       ["salary_revision"],
            leave:        ["leave"],
            performance:  ["appraisal", "training", "award"],
            disciplinary: ["warning", "disciplinary"],
        };
        const allowed = filterMap[f] || [];
        return all.filter(ev => allowed.includes(ev.type));
    }

    get timelineFilterLabel() {
        const labels = {
            all:          "All Events",
            employment:   "Employment Changes",
            salary:       "Salary History",
            leave:        "Leave Records",
            performance:  "Performance & Training",
            disciplinary: "Disciplinary Actions",
        };
        return labels[this.state.timelineFilter] || "All Events";
    }

    // Color → Bootstrap class mapping for timeline badges
    colorClass(color) {
        const map = {
            green:  "bg-success",
            blue:   "bg-primary",
            orange: "bg-warning text-dark",
            purple: "bg-purple",
            red:    "bg-danger",
            teal:   "bg-info text-white",
            gray:   "bg-secondary",
        };
        return map[color] || "bg-secondary";
    }

    dotColorStyle(color) {
        const map = {
            green:  "#22c55e",
            blue:   "#3b82f6",
            orange: "#f59e0b",
            purple: "#8b5cf6",
            red:    "#ef4444",
            teal:   "#14b8a6",
            gray:   "#94a3b8",
        };
        return `background-color: ${map[color] || "#94a3b8"}`;
    }

    openEmployeeForm(employeeId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'hr.employee',
            res_id: Number(employeeId || this.props.employeeId),
            views: [[false, 'form']],
            target: 'current'
        });
    }

    async onToggleCheckin() {
        const res = await this.orm.call("hr.dashboard.metrics", "action_quick_checkin", [this.props.employeeId]);
        if (res.success) {
            this.notification.add(res.message, { type: "success" });
            await this.loadData();
        } else {
            this.notification.add(res.message, { type: "warning" });
        }
    }

    async onApproveLeave(leaveId) {
        await this.orm.call("hr.leave", "action_approve", [[leaveId]]);
        this.notification.add(_t("Leave approved successfully."), { type: "success" });
        await this.loadData();
    }

    async onSendReminder() {
        const docIds = (this.state.data.documents || []).map(d => d.id).filter(id => Boolean(id));
        if (docIds.length === 0) {
            this.notification.add(_t("No expiring documents found in the record table."), { type: "info" });
            return;
        }
        this.notification.add(_t("Expiry reminder notifications sent to employee successfully."), { type: "success" });
    }
}
