/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onWillStart, onMounted, onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { KpiCard } from "./kpi_card";
import { ChartManager } from "./chart_manager";
import { Employee360Drawer } from "./employee_360_drawer";
import { AttendanceMap } from "./attendance_map";
import { SmartSearchModal } from "./smart_search";
import { OrgChartTree } from "./org_chart";
import { SmartAlertCenter } from "./smart_alert_center";
import { FilterPanel } from "./filter_panel";
import { SelfServicePortal } from "./self_service_portal";
console.log('wu_hr_employee360 DashboardAction JS loaded');
import { ExcelExporter } from "./excel_exporter";

export class DashboardClientAction extends Component {
    static template = "wu_hr_employee360.DashboardMain";
    static props = ["*"];
    static components = {
        KpiCard,
        ChartManager,
        Employee360Drawer,
        AttendanceMap,
        SmartSearchModal,
        OrgChartTree,
        SmartAlertCenter,
        FilterPanel,
        SelfServicePortal,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.busService = useService("bus_service");

        // Initialize dark mode based on Odoo's color scheme or system preference
        const initColorScheme = document.documentElement.getAttribute('data-color-scheme') || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

        this.state = useState({
            loading: true,
            data: null,
            activeTab: "overview",
            activeKpi: null,
            activeLeaveKpi: null,
            activeLifecycleKpi: null,
            activeRecruitmentKpi: null,
            activeComplianceKpi: null,
            activeSlice: null,
            selectedEmployeeId: null,
            showSearchModal: false,
            darkMode: initColorScheme === 'dark',
            showConfigPopover: false,
            smartAlertsLoading: false,
            showFilterPanel: false,
            activeFilters: {},
            exportLoading: false,
            panelOrder: (() => {
                try {
                    const saved = localStorage.getItem('hr_dashboard_panel_order');
                    return saved ? JSON.parse(saved) : [
                        'attendance_overview', 'attendance_trend', 'leave_summary', 'payroll_overview', 'hr_alerts',
                        'dept_overview', 'recruitment_overview', 'employee_distribution',
                        'compliance_overview', 'smart_calendar', 'todays_activities',
                        'top_performers', 'leave_requests', 'quick_actions'
                    ];
                } catch(e) {
                    return [
                        'attendance_overview', 'attendance_trend', 'leave_summary', 'payroll_overview', 'hr_alerts',
                        'dept_overview', 'recruitment_overview', 'employee_distribution',
                        'compliance_overview', 'smart_calendar', 'todays_activities',
                        'top_performers', 'leave_requests', 'quick_actions'
                    ];
                }
            })(),
            panelVisibility: (() => {
                try {
                    const saved = localStorage.getItem('hr_dashboard_panel_visibility');
                    return saved ? JSON.parse(saved) : {
                        attendance_overview: true, attendance_trend: true, leave_summary: true, payroll_overview: true, hr_alerts: true,
                        dept_overview: true, recruitment_overview: true, employee_distribution: true,
                        compliance_overview: true, smart_calendar: true, todays_activities: true,
                        top_performers: true, leave_requests: true, quick_actions: true
                    };
                } catch(e) {
                    return {
                        attendance_overview: true, attendance_trend: true, leave_summary: true, payroll_overview: true, hr_alerts: true,
                        dept_overview: true, recruitment_overview: true, employee_distribution: true,
                        compliance_overview: true, smart_calendar: true, todays_activities: true,
                        top_performers: true, leave_requests: true, quick_actions: true
                    };
                }
            })(),
            tileConfigs: (() => {
                try {
                    const saved = localStorage.getItem('hr_dashboard_tile_configs');
                    return saved ? JSON.parse(saved) : {};
                } catch(e) {
                    return {};
                }
            })(),
            tileTitles: (() => {
                try {
                    const saved = localStorage.getItem('hr_dashboard_tile_titles');
                    return saved ? JSON.parse(saved) : {};
                } catch(e) {
                    return {};
                }
            })(),
            editingTile: null,
            editingTitleInline: null,
            editingConfig: {},
            edition: "enterprise", // 'standard' | 'professional' | 'enterprise'
            filters: {
                employee_search: "",
                company_id: "",
                department_id: "",
                manager_id: "",
                job_id: "",
                gender: "",
                employment_type: "",
                date_filter: "today",
                start_date: "",
                end_date: "",
            },
            meta: {
                companies: [],
                departments: [],
            }
        });

        // Handle Cmd+K global shortcut
        this._onKeyDown = (event) => {
            if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
                event.preventDefault();
                this.openSmartSearchModal();
            }
        };

        onWillStart(async () => {
            await this.loadMetadata();
            await this.fetchData();
        });

        onMounted(() => {
            window.addEventListener("keydown", this._onKeyDown);
            
            // Set up background refresh interval (every 30 seconds)
            this.refreshInterval = setInterval(() => {
                this.fetchData(true);
            }, 30000);

            // Observe Odoo theme changes natively
            this.themeObserver = new MutationObserver((mutations) => {
                for (let mutation of mutations) {
                    if (mutation.attributeName === 'data-color-scheme') {
                        const scheme = document.documentElement.getAttribute('data-color-scheme');
                        this.state.darkMode = scheme === 'dark';
                    }
                }
            });
            this.themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-color-scheme'] });

            // Subscribe to real-time WebSockets notifications via Odoo bus service
            if (this.busService) {
                this._boundOnBusNotification = this._onBusNotification.bind(this);
                this.busService.addChannel("hr_dashboard_updates");
                this.busService.addEventListener("notification", this._boundOnBusNotification);
            }
        });

        onWillDestroy(() => {
            window.removeEventListener("keydown", this._onKeyDown);
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
            }
            if (this.themeObserver) {
                this.themeObserver.disconnect();
            }
            if (this.busService && this._boundOnBusNotification) {
                this.busService.removeEventListener("notification", this._boundOnBusNotification);
            }
        });
    }

    _onBusNotification(event) {
        const { detail: notifications } = event;
        for (const notification of notifications) {
            if (notification.payload && notification.payload.type === "hr_dashboard_updates") {
                this.notification.add(_t("Live update received from server."), { type: "info" });
                this.fetchData(true);
            } else if (notification.type === "hr_dashboard_updates") {
                this.notification.add(_t("Live update received from server."), { type: "info" });
                this.fetchData(true);
            }
        }
    }

    async loadMetadata() {
        try {
            const [companies, departments] = await Promise.all([
                this.orm.searchRead("res.company", [], ["id", "name"]),
                this.orm.searchRead("hr.department", [], ["id", "name"])
            ]);
            this.state.meta.companies = companies || [];
            this.state.meta.departments = departments || [];
        } catch (e) {
            console.warn("Could not load some metadata models:", e);
        }
    }

    async fetchData(background = false) {
        if (!background) {
            this.state.loading = true;
        }
        try {
            const result = await this.orm.call("hr.dashboard.metrics", "get_dashboard_data", [this.state.filters]);
            this.state.data = result;
        } catch (err) {
            if (!background) {
                this.notification.add(_t("Could not fetch dashboard metrics. Verify database connections."), { type: "danger" });
            }
        } finally {
            if (!background) {
                this.state.loading = false;
            }
        }
    }

    setTab(tabName) {
        this.state.activeTab = tabName;
    }

    setEdition(editionName) {
        this.state.edition = editionName;
        this.notification.add(_t("Switched to %s Edition View").replace("%s", editionName.toUpperCase()), { type: "info" });
    }

    async refreshData() {
        this.notification.add(_t("Refreshing dashboard metrics..."), { type: "info" });
        await this.fetchData();
    }

    onFilterChange() {
        this.fetchData();
    }

    clearFilters() {
        this.state.filters = {
            employee_search: "",
            company_id: "",
            branch_id: "",
            department_id: "",
            manager_id: "",
            job_id: "",
            gender: "",
            employment_type: "",
        };
        this.state.activeKpi = null;
        this.fetchData();
    }

    hasActiveFilters() {
        return Object.values(this.state.filters).some(v => Boolean(v)) || Boolean(this.state.activeKpi);
    }

    get displayedEmployees() {
        const list = this.state.data?.employee_list || [];
        if (!this.state.activeKpi || this.state.activeKpi === 'total_employees') {
            return list;
        }
        if (this.state.activeKpi === 'birthday_today') {
            return list.filter(e => e.is_birthday_this_month);
        }
        if (this.state.activeKpi === 'present_today') {
            return list.filter(e => e.status === 'Present');
        }
        if (this.state.activeKpi === 'on_leave_today') {
            return list.filter(e => e.status === 'On Leave');
        }
        if (this.state.activeKpi === 'late_today') {
            return list.filter(e => e.is_late);
        }
        if (this.state.activeKpi === 'visa_expiring') {
            return list.filter(e => e.is_visa_expiring);
        }
        if (this.state.activeKpi === 'contract_expiring') {
            return list.filter(e => e.is_contract_expiring);
        }
        if (this.state.activeKpi === 'probation_employees') {
            return list.filter(e => e.is_probation);
        }
        if (this.state.activeKpi === 'new_joiners') {
            return list.filter(e => e.is_new_joiner);
        }
        if (this.state.activeKpi === 'resigned_employees') {
            return list.filter(e => e.is_resigned);
        }
        if (this.state.activeKpi === 'on_vacation_today') {
            return list.filter(e => e.is_on_vacation);
        }
        if (this.state.activeKpi === 'checked_in') {
            return list.filter(e => e.is_checked_in);
        }
        if (this.state.activeKpi === 'checked_out') {
            return list.filter(e => e.is_checked_out);
        }
        if (this.state.activeKpi === 'early_checkout') {
            return list.filter(e => e.is_early_checkout);
        }
        if (this.state.activeKpi === 'overtime_today') {
            return list.filter(e => e.is_overtime);
        }
        if (this.state.activeKpi === 'birthday_today_exact') {
            return list.filter(e => e.is_birthday_today);
        }
        if (this.state.activeKpi === 'work_anniversaries') {
            return list.filter(e => e.is_anniversary_today);
        }
        if (this.state.activeKpi === 'attendance_missing') {
            return list.filter(e => e.is_missing_checkout);
        }
        if (this.state.activeKpi === 'contracts_expiring_today') {
            return list.filter(e => e.is_contract_expiring);
        }
        if (this.state.activeKpi === 'employees_on_leave_today') {
            return list.filter(e => e.status === 'On Leave');
        }
        if (this.state.activeSlice) {
            const s = String(this.state.activeSlice).toLowerCase();
            return list.filter(e => 
                (e.department && String(e.department).toLowerCase() === s) ||
                (e.company && String(e.company).toLowerCase() === s) ||
                (e.manager && String(e.manager).toLowerCase() === s) ||
                (e.job_title && String(e.job_title).toLowerCase() === s) ||
                (e.gender && String(e.gender).toLowerCase() === s) ||
                (e.nationality && String(e.nationality).toLowerCase() === s) ||
                (e.employment_type && String(e.employment_type).toLowerCase() === s) ||
                (e.age_group && String(e.age_group).toLowerCase() === s) ||
                (e.experience_group && String(e.experience_group).toLowerCase() === s) ||
                (e.join_month && String(e.join_month).toLowerCase() === s) ||
                (e.status && String(e.status).toLowerCase() === s)
            );
        }
        return list;
    }

    get displayedApplicants() {
        if (!this.state.data || !this.state.data.recruitment_dashboard || !this.state.data.recruitment_dashboard.applicant_list) {
            return [];
        }
        const appList = this.state.data.recruitment_dashboard.applicant_list;
        if (this.state.activeSlice) {
            const s = String(this.state.activeSlice).toLowerCase();
            return appList.filter(a =>
                (a.source && String(a.source).toLowerCase() === s) ||
                (a.create_month && String(a.create_month).toLowerCase() === s) ||
                (a.stage && String(a.stage).toLowerCase() === s) ||
                (a.job && String(a.job).toLowerCase() === s)
            );
        }
        return appList;
    }

    onKpiClick(kpiId) {
        if (this.state.activeKpi === kpiId) {
            this.state.activeKpi = null;
            this.state.activeTab = "overview";
        } else {
            this.state.activeKpi = kpiId;
            this.state.activeSlice = null;
            this.state.activeTab = "list";
        }
    }

    onChartDrilldown(sliceLabel) {
        this.notification.add(`Drill-Down activated: ${sliceLabel}`, { type: "info" });
        if (this.state.activeSlice === sliceLabel) {
            this.state.activeSlice = null;
            this.state.activeTab = "overview";
        } else {
            this.state.activeSlice = sliceLabel;
            this.state.activeKpi = null;
            this.state.activeTab = "list";
        }
    }

    // Leave Dashboard KPI Card Click Handler
    onLeaveKpiClick(leaveKpiId) {
        if (this.state.activeLeaveKpi === leaveKpiId) {
            this.state.activeLeaveKpi = null;
        } else {
            this.state.activeLeaveKpi = leaveKpiId;
        }
    }

    clearLeaveKpi() {
        this.state.activeLeaveKpi = null;
    }

    get leaveKpiLabel() {
        const labels = {
            'balance': 'Total Leave Balance',
            'approved': 'Approved Leaves',
            'pending': 'Pending Approval',
            'sick': 'Sick Leaves',
            'annual': 'Annual Leaves',
            'upcoming': 'Upcoming Leaves',
        };
        return labels[this.state.activeLeaveKpi] || this.state.activeLeaveKpi;
    }

    get displayedLeaveRecords() {
        const records = this.state.data?.leave_dashboard?.leave_records || [];
        if (!this.state.activeLeaveKpi || this.state.activeLeaveKpi === 'balance') {
            return [];
        }
        return records.filter(r => r.categories && r.categories.includes(this.state.activeLeaveKpi));
    }

    get displayedAllocationRecords() {
        if (this.state.activeLeaveKpi !== 'balance') {
            return [];
        }
        return this.state.data?.leave_dashboard?.allocation_records || [];
    }

    openLeaveForm(leaveId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'hr.leave',
            res_id: Number(leaveId),
            views: [[false, 'form']],
            target: 'current'
        });
    }

    // Lifecycle Dashboard KPI Card Click Handler
    onLifecycleKpiClick(kpiId) {
        if (this.state.activeLifecycleKpi === kpiId) {
            this.state.activeLifecycleKpi = null;
        } else {
            this.state.activeLifecycleKpi = kpiId;
        }
    }

    clearLifecycleKpi() {
        this.state.activeLifecycleKpi = null;
    }

    get lifecycleKpiLabel() {
        const labels = {
            'onboarding': 'Onboarding (New Joiners)',
            'probation': 'Probation Period',
            'confirmation': 'Confirmed Employees',
            'resignations': 'Resigned Employees',
            'promotions': 'Promotions',
            'transfers': 'Transfers',
            'salary_revisions': 'Salary Revisions',
            'training': 'Training Enrollments',
            'reviews': 'Reviews Pending',
            'exit_interviews': 'Exit Interviews',
            'terminations': 'Terminations',
            'retirements': 'Retirements'
        };
        return labels[this.state.activeLifecycleKpi] || this.state.activeLifecycleKpi;
    }

    get displayedLifecycleRecords() {
        const records = this.state.data?.lifecycle_dashboard?.lifecycle_records || [];
        if (!this.state.activeLifecycleKpi) {
            return [];
        }
        return records.filter(r => r.categories && r.categories.includes(this.state.activeLifecycleKpi));
    }

    // Recruitment Dashboard KPI Card Click Handler
    onRecruitmentKpiClick(kpiId) {
        if (this.state.activeRecruitmentKpi === kpiId) {
            this.state.activeRecruitmentKpi = null;
        } else {
            this.state.activeRecruitmentKpi = kpiId;
        }
    }

    clearRecruitmentKpi() {
        this.state.activeRecruitmentKpi = null;
    }

    get recruitmentKpiLabel() {
        const labels = {
            'applicants': 'Active Applicants',
            'interview': 'In Interview Stage'
        };
        return labels[this.state.activeRecruitmentKpi] || this.state.activeRecruitmentKpi;
    }

    get displayedRecruitmentRecords() {
        const records = this.state.data?.recruitment_dashboard?.applicant_list || [];
        if (!this.state.activeRecruitmentKpi) {
            return [];
        }
        if (this.state.activeRecruitmentKpi === 'applicants') {
            return records;
        }
        if (this.state.activeRecruitmentKpi === 'interview') {
            return records.filter(r => r.stage && r.stage.toLowerCase().includes('interview'));
        }
        return [];
    }

    openApplicantForm(applicantId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'hr.applicant',
            res_id: Number(applicantId),
            views: [[false, 'form']],
            target: 'current'
        });
    }

    // Compliance Dashboard KPI Card Click Handler
    onComplianceKpiClick(kpiId) {
        if (this.state.activeComplianceKpi === kpiId) {
            this.state.activeComplianceKpi = null;
        } else {
            this.state.activeComplianceKpi = kpiId;
        }
    }

    clearComplianceKpi() {
        this.state.activeComplianceKpi = null;
    }

    get complianceKpiLabel() {
        const labels = {
            'contract': 'Employment Contract Expiring',
            'visa': 'Work Visa Expiring',
            'passport': 'National ID Expiring',
            'probation': 'Probation Period Ending',
        };
        return labels[this.state.activeComplianceKpi] || this.state.activeComplianceKpi;
    }

    get displayedComplianceRecords() {
        const records = this.state.data?.compliance_dashboard?.expiring_list || [];
        if (!this.state.activeComplianceKpi) {
            return records; // default behavior: show all
        }
        return records.filter(r => r.doc_category === this.state.activeComplianceKpi);
    }

    open360Drawer(employeeId) {
        this.state.selectedEmployeeId = Number(employeeId);
    }

    openEmployeeForm(employeeId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'hr.employee',
            res_id: Number(employeeId),
            views: [[false, 'form']],
            target: 'current'
        });
    }

    get timesheetDashboard() {
        return this.state.data?.timesheet_dashboard || {
            allowed: false,
            summary: {},
            daily: [],
            by_project: [],
            by_employee: [],
            recent_entries: [],
            missing_loggers: [],
        };
    }

    timesheetDailyBarStyle(hours) {
        const values = (this.timesheetDashboard.daily || []).map((point) => Number(point.hours) || 0);
        const maximum = Math.max(1, ...values);
        const height = hours ? Math.max(8, Math.round((Number(hours) / maximum) * 100)) : 3;
        return `height: ${height}%;`;
    }

    openTimesheets() {
        return this.action.doAction('hr_timesheet.timesheet_action_all');
    }

    async openTimesheetForm() {
        try {
            const action = await this.orm.call(
                'hr.dashboard.metrics',
                'action_open_timesheet_form',
                [false],
            );
            await this.action.doAction(action);
        } catch (error) {
            this.notification.add(_t('Could not open the Timesheets form. Verify your access.'), { type: 'warning' });
        }
    }

    async openTimesheetEntry(timesheetId) {
        try {
            const action = await this.orm.call(
                'hr.dashboard.metrics',
                'action_open_timesheet_form',
                [Number(timesheetId)],
            );
            await this.action.doAction(action);
        } catch (error) {
            this.notification.add(_t('Could not open this timesheet entry.'), { type: 'warning' });
        }
    }

    async openEmployeeTimesheets(employeeId) {
        try {
            const action = await this.orm.call(
                'hr.dashboard.metrics',
                'action_open_employee_timesheets',
                [Number(employeeId)],
            );
            await this.action.doAction(action, {
                additionalContext: { active_id: Number(employeeId) },
            });
        } catch (error) {
            this.notification.add(
                _t('Could not open this employee\'s timesheets. Verify your Timesheets access.'),
                { type: 'warning' },
            );
        }
    }

    close360Drawer() {
        this.state.selectedEmployeeId = null;
        this.fetchData(); // Refresh metrics in case actions occurred inside drawer
    }

    openSmartSearchModal() {
        this.state.showSearchModal = true;
    }

    closeSmartSearchModal() {
        this.state.showSearchModal = false;
    }

    toggleDarkMode() {
        this.state.darkMode = !this.state.darkMode;
    }

    async onQuickAction(actionType) {
        const actionMap = {
            'add_employee': { name: "Create Employee Record", res_model: "hr.employee", icon: "fa-user-plus" },
            'leave': { name: "Create Leave Request", res_model: "hr.leave", icon: "fa-plane" },
            'attendance': { name: "Log Manual Check-In / Out", res_model: "hr.attendance", icon: "fa-clock-o" },
            'payslip': { name: "Generate Employee Payslip", res_model: "hr.payslip", icon: "fa-money" },
            'expense': { name: "Create Expense Report", res_model: "hr.expense", icon: "fa-credit-card" },
            'loan': { name: "Issue Employee Loan / Advance", res_model: "hr.loan", icon: "fa-bank" },
            'advance': { name: "Salary Advance Request", res_model: "hr.advance", icon: "fa-dollar" },
            'warning': { name: "Issue Disciplinary Warning Notice", res_model: "hr.employee.timeline.event", context: { default_event_type: 'warning', default_color: 'red' } },
            'promotion': { name: "Process Employee Promotion", res_model: "hr.employee.timeline.event", context: { default_event_type: 'promotion', default_color: 'green' } },
            'transfer': { name: "Branch / Department Transfer", res_model: "hr.employee.timeline.event", context: { default_event_type: 'transfer', default_color: 'blue' } },
            'termination': { name: "Initiate Separation / Termination", res_model: "hr.employee.timeline.event", context: { default_event_type: 'separation', default_color: 'red' } },
        };

        if (actionMap[actionType] && await this.orm.call("ir.model", "search_count", [[["model", "=", actionMap[actionType].res_model]]])) {
            const viewMode = actionMap[actionType].view_mode || "form";
            const views = viewMode.split(",").map(m => [false, m.trim()]);
            this.action.doAction({
                name: actionMap[actionType].name,
                type: "ir.actions.act_window",
                res_model: actionMap[actionType].res_model,
                view_mode: viewMode,
                views: views,
                target: "new",
                context: actionMap[actionType].context || {}
            });
        } else if (actionType === 'email') {
            window.location.href = "mailto:?subject=HR Announcement - Employee 360 Pro";
        } else if (actionType === 'whatsapp') {
            window.open("https://web.whatsapp.com/", "_blank");
        } else if (actionType === 'print_id') {
            window.open("/report/pdf/hr.report_employee_badge", "_blank");
        } else if (actionType === 'download_contract') {
            window.open("/api/v1/hr_employee360/export_pdf", "_blank");
        } else if (actionType === 'import') {
            this.notification.add(_t("Opening Odoo Batch Import Wizard for Employees"), { type: "info" });
            this.action.doAction({
                name: "Import Employees",
                type: "ir.actions.act_window",
                res_model: "hr.employee",
                view_mode: "list,form",
                views: [[false, "list"], [false, "form"]],
                target: "current"
            });
        } else if (actionType === 'export') {
            this.exportFilteredPDF();
        } else if (actionType === 'birthday') {
            window.location.href = "mailto:?subject=Happy Birthday from HR & Leadership Team! 🎉";
        } else {
            this.notification.add(`Quick action triggered: ${actionType.toUpperCase()}`, { type: "info" });
        }
    }

    // Drag and Drop & Configurability Methods
    onDragStart(ev, panelId) {
        ev.dataTransfer.setData("text/plain", panelId);
        ev.currentTarget.classList.add("dragging");
    }

    onDragOver(ev) {
        ev.preventDefault();
    }

    onDrop(ev, targetPanelId) {
        ev.preventDefault();
        const sourcePanelId = ev.dataTransfer.getData("text/plain");
        if (sourcePanelId === targetPanelId) return;

        const order = [...this.state.panelOrder];
        const sourceIdx = order.indexOf(sourcePanelId);
        const targetIdx = order.indexOf(targetPanelId);

        if (sourceIdx > -1 && targetIdx > -1) {
            order.splice(sourceIdx, 1);
            order.splice(targetIdx, 0, sourcePanelId);
            this.state.panelOrder = order;
            localStorage.setItem('hr_dashboard_panel_order', JSON.stringify(order));
        }
    }

    onDragEnd(ev) {
        ev.currentTarget.classList.remove("dragging");
    }

    togglePanelVisibility(panelId) {
        this.state.panelVisibility[panelId] = !this.state.panelVisibility[panelId];
        localStorage.setItem('hr_dashboard_panel_visibility', JSON.stringify(this.state.panelVisibility));
    }

    toggleConfigPopover() {
        this.state.showConfigPopover = !this.state.showConfigPopover;
    }

    async toggleGlobalAccessControl() {
        const nextValue = !this.state.data.access_managers_only;
        await this.orm.call("hr.dashboard.metrics", "toggle_dashboard_access", [nextValue]);
        this.notification.add(
            nextValue 
                ? "Dashboard restricted to Managers and Administrators." 
                : "Dashboard opened to all users.", 
            { type: "success" }
        );
        await this.fetchData();
    }

    exportDashboardLayout() {
        const config = {
            panel_order: this.state.panelOrder,
            panel_visibility: this.state.panelVisibility
        };
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(config, null, 4));
        const downloadAnchor = document.createElement('a');
        downloadAnchor.setAttribute("href", dataStr);
        downloadAnchor.setAttribute("download", "hr_dashboard_layout.json");
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();
        this.notification.add(_t("Dashboard layout configuration exported successfully!"), { type: "success" });
    }

    triggerImportInput() {
        this.refs.importLayoutInput.click();
    }

    async importDashboardLayout(ev) {
        const file = ev.target.files[0];
        if (!file) return;

        try {
            const content = await file.text();
            const config = JSON.parse(content);

            if (config.panel_order && config.panel_visibility) {
                this.state.panelOrder = config.panel_order;
                this.state.panelVisibility = config.panel_visibility;

                localStorage.setItem('hr_dashboard_panel_order', JSON.stringify(config.panel_order));
                localStorage.setItem('hr_dashboard_panel_visibility', JSON.stringify(config.panel_visibility));

                this.notification.add(_t("Dashboard layout configuration imported successfully!"), { type: "success" });
            } else {
                this.notification.add(_t("Invalid dashboard configuration file. Missing layout parameters."), { type: "danger" });
            }
        } catch (err) {
            this.notification.add(_t("Error reading layout configuration file."), { type: "danger" });
        } finally {
            ev.target.value = ""; // Reset input
        }
    }

    openTileConfigurator(panelId) {
        this.state.editingTile = panelId;
        const currentConfig = this.state.tileConfigs[panelId] || {};
        this.state.editingConfig = {
            fontStyle: currentConfig.fontStyle || 'inherit',
            fontColor: currentConfig.fontColor || '#0f172a',
            icon: currentConfig.icon || '',
            bgColor: currentConfig.bgColor || 'bg-white',
            layout: currentConfig.layout || 'layout-1',
            groupBy: currentConfig.groupBy || '',
            sortBy: currentConfig.sortBy || '',
            limit: currentConfig.limit || '5',
            filterCondition: currentConfig.filterCondition || ''
        };
    }

    closeTileConfigurator() {
        this.state.editingTile = null;
        this.state.editingConfig = {};
    }

    startInlineEdit(panelId) {
        this.state.editingTitleInline = panelId;
    }

    saveInlineEdit(panelId, ev) {
        const newTitle = ev.target.value.trim();
        if (newTitle) {
            this.state.tileTitles[panelId] = newTitle;
            localStorage.setItem('hr_dashboard_tile_titles', JSON.stringify(this.state.tileTitles));
            this.notification.add(_t("Title updated instantly!"), { type: "success" });
        }
        this.state.editingTitleInline = null;
    }

    selectLayout(layoutName) {
        this.state.editingConfig.layout = layoutName;
    }

    saveTileConfig() {
        const panelId = this.state.editingTile;
        if (!panelId) return;

        this.state.tileConfigs[panelId] = { ...this.state.editingConfig };
        localStorage.setItem('hr_dashboard_tile_configs', JSON.stringify(this.state.tileConfigs));
        this.notification.add(_t("Tile customizations applied successfully!"), { type: "success" });
        this.closeTileConfigurator();
    }

    // Getters that apply Dynamic Filtration & Sorting to Dashboard lists
    get displayedDeptOverview() {
        let records = this.state.data?.department_overview || [];
        const config = this.state.tileConfigs?.dept_overview;
        if (!config) return records;

        // FilterCondition
        if (config.filterCondition === 'high_cost') {
            records = records.filter(r => parseFloat(String(r.cost).replace(/[^0-9.]/g, '')) > 5000);
        } else if (config.filterCondition === 'high_attendance') {
            records = records.filter(r => parseFloat(String(r.att_pct)) > 90);
        }

        // SortBy
        if (config.sortBy === 'name_asc') {
            records = [...records].sort((a, b) => a.dept.localeCompare(b.dept));
        } else if (config.sortBy === 'name_desc') {
            records = [...records].sort((a, b) => b.dept.localeCompare(a.dept));
        } else if (config.sortBy === 'value_desc') {
            records = [...records].sort((a, b) => b.emp - a.emp);
        } else if (config.sortBy === 'value_asc') {
            records = [...records].sort((a, b) => a.emp - b.emp);
        }

        // Limit
        if (config.limit) {
            records = records.slice(0, Number(config.limit));
        }
        return records;
    }

    get displayedTopPerformers() {
        let records = this.state.data?.top_performers || [];
        const config = this.state.tileConfigs?.top_performers;
        if (!config) return records;

        // SortBy
        if (config.sortBy === 'name_asc') {
            records = [...records].sort((a, b) => a.name.localeCompare(b.name));
        } else if (config.sortBy === 'name_desc') {
            records = [...records].sort((a, b) => b.name.localeCompare(a.name));
        } else if (config.sortBy === 'value_desc') {
            records = [...records].sort((a, b) => b.rating - a.rating);
        } else if (config.sortBy === 'value_asc') {
            records = [...records].sort((a, b) => a.rating - b.rating);
        }

        // Limit
        if (config.limit) {
            records = records.slice(0, Number(config.limit));
        }
        return records;
    }

    get displayedLeaveRequests() {
        let records = this.state.data?.leave_requests || [];
        const config = this.state.tileConfigs?.leave_requests;
        if (!config) return records;

        // SortBy
        if (config.sortBy === 'name_asc') {
            records = [...records].sort((a, b) => a.name.localeCompare(b.name));
        } else if (config.sortBy === 'name_desc') {
            records = [...records].sort((a, b) => b.name.localeCompare(a.name));
        }

        // Limit
        if (config.limit) {
            records = records.slice(0, Number(config.limit));
        }
        return records;
    }

    get displayedCalendarEvents() {
        let records = this.state.data?.calendar_events || [];
        const config = this.state.tileConfigs?.smart_calendar;
        if (!config) return records;

        // SortBy
        if (config.sortBy === 'name_asc') {
            records = [...records].sort((a, b) => a.title.localeCompare(b.title));
        } else if (config.sortBy === 'name_desc') {
            records = [...records].sort((a, b) => b.title.localeCompare(a.title));
        }

        // Limit
        if (config.limit) {
            records = records.slice(0, Number(config.limit));
        }
        return records;
    }

    // ---------------------------------------------------------------- //
    //  Smart Alert Center helpers                                        //
    // ---------------------------------------------------------------- //
    get smartAlerts() {
        return this.state.data?.smart_alerts || { critical: [], warning: [], info: [], total: 0, unread: 0 };
    }

    async refreshSmartAlerts() {
        this.state.smartAlertsLoading = true;
        await this.fetchData(true);
        this.state.smartAlertsLoading = false;
        this.notification.add(_t("Smart Alerts refreshed!"), { type: "success" });
    }

    // ---------------------------------------------------------------- //
    //  Role-based helpers                                                //
    // ---------------------------------------------------------------- //
    get userRole() {
        return this.state.data?.user_role || "employee";
    }

    get isHrManager() { return this.userRole === "hr_manager"; }
    get isHrOfficer() { return this.userRole === "hr_officer" || this.isHrManager; }
    get isDeptManager() { return this.userRole === "dept_manager" || this.isHrOfficer; }
    get isEmployee() { return this.userRole === "employee"; }

    get roleBadgeClass() {
        const map = {
            hr_manager:  "badge-role-manager",
            hr_officer:  "badge-role-officer",
            dept_manager:"badge-role-dept",
            employee:    "badge-role-employee",
        };
        return map[this.userRole] || "badge-secondary";
    }

    get roleBadgeLabel() {
        const map = {
            hr_manager:  "HR Manager",
            hr_officer:  "HR Officer",
            dept_manager:"Dept. Manager",
            employee:    "Employee",
        };
        return map[this.userRole] || "User";
    }

    // ---------------------------------------------------------------- //
    //  Advanced Filter Panel                                             //
    // ---------------------------------------------------------------- //
    toggleFilterPanel() {
        this.state.showFilterPanel = !this.state.showFilterPanel;
    }

    async applyFilters(filters) {
        this.state.activeFilters = filters || {};
        await this.fetchData(true);
        const count = Object.keys(this.state.activeFilters).length;
        this.notification.add(
            count > 0
                ? `Filters applied (${count} active). Dashboard updated.`
                : "All filters cleared.",
            { type: "info" }
        );
    }

    async resetFilters() {
        this.state.activeFilters = {};
        await this.fetchData(true);
        this.notification.add(_t("Filters reset. Showing full dataset."), { type: "info" });
    }

    // Override fetchData to pass active filters
    async fetchDataWithFilters() {
        const filters = Object.assign({}, this.state.activeFilters);
        const data = await this.orm.call("hr.dashboard.metrics", "get_dashboard_data", [filters]);
        this.state.data = data;
    }

    // ---------------------------------------------------------------- //
    //  Excel Export                                                      //
    // ---------------------------------------------------------------- //
    async exportExcel() {
        if (!this.state.data) {
            this.notification.add(_t("No data to export. Load the dashboard first."), { type: "warning" });
            return;
        }
        this.state.exportLoading = true;
        try {
            ExcelExporter.exportToExcel(this.state.data, this.state.activeFilters);
            this.notification.add(_t("Excel file downloaded successfully! Check your Downloads folder."), { type: "success" });
        } catch (e) {
            this.notification.add(_t("Excel export failed: ") + (e.message || e), { type: "danger" });
        } finally {
            this.state.exportLoading = false;
        }
    }

    exportFilteredPDF() {
        const filters = this.state.activeFilters || {};
        const params = new URLSearchParams(
            Object.fromEntries(Object.entries(filters).filter(([, v]) => v))
        ).toString();
        const url = `/api/v1/hr_employee360/export_pdf${params ? '?' + params : ''}`;
        window.open(url, "_blank");
        this.notification.add(_t("PDF report opening in new tab..."), { type: "info" });
    }

    // ---------------------------------------------------------------- //
    //  Email Digest & WhatsApp (Smart Alert integration)                 //
    // ---------------------------------------------------------------- //
    async sendEmailDigest() {
        try {
            const res = await this.orm.call("hr.smart.alert", "send_digest_now", []);
            if (res.success) {
                this.notification.add(res.message, { type: "success" });
            } else {
                this.notification.add(res.message || _t("Email failed."), { type: "warning" });
            }
        } catch (e) {
            this.notification.add(_t("Email sending error: ") + (e.message || e), { type: "danger" });
        }
    }

    async openWhatsApp(alertId) {
        try {
            const res = await this.orm.call("hr.smart.alert", "get_whatsapp_link", [alertId]);
            if (res.success && res.url) {
                window.open(res.url, "_blank");
            } else {
                this.notification.add(res.message || _t("Could not generate WhatsApp link."), { type: "warning" });
            }
        } catch (e) {
            this.notification.add(_t("WhatsApp link error: ") + (e.message || e), { type: "danger" });
        }
    }
}

registry.category("actions").add("wu_hr_employee360.DashboardClientAction", DashboardClientAction);
