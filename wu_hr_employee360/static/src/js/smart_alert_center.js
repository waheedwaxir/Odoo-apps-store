/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/**
 * SmartAlertCenter — standalone OWL component embedded in the main dashboard.
 * Displays critical / warning / info alerts with dismiss and employee drill-down.
 */
export class SmartAlertCenter extends Component {
    static template = "wu_hr_employee360.SmartAlertCenter";
    static props = {
        smartAlerts: { type: Object },              // { critical:[], warning:[], info:[], total, unread }
        onOpen360Drawer: { type: Function },        // (employeeId) => void
        onRefresh: { type: Function },              // async () => void — triggers fetchData
    };

    setup() {
        this.orm          = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            activeSection: "critical",   // 'critical' | 'warning' | 'info' | 'all'
            dismissing: null,            // alert id being dismissed
        });
    }

    // ---------------------------------------------------------------- //
    //  Computed helpers                                                  //
    // ---------------------------------------------------------------- //
    get displayedAlerts() {
        const sa = this.props.smartAlerts || {};
        if (this.state.activeSection === "all") {
            return [
                ...(sa.critical || []),
                ...(sa.warning  || []),
                ...(sa.info     || []),
            ];
        }
        return sa[this.state.activeSection] || [];
    }

    severityBadgeClass(severity) {
        return severity === "critical" ? "badge-alert-critical"
             : severity === "warning"  ? "badge-alert-warning"
             :                           "badge-alert-info";
    }

    severityIcon(severity) {
        return severity === "critical" ? "fa-exclamation-circle"
             : severity === "warning"  ? "fa-exclamation-triangle"
             :                           "fa-info-circle";
    }

    alertTypeIcon(alertType) {
        const iconMap = {
            document_expiry:        "fa-file-text-o",
            contract_renewal:       "fa-file-contract",
            probation_end:          "fa-hourglass-end",
            birthday:               "fa-birthday-cake",
            anniversary:            "fa-star",
            appraisal_due:          "fa-line-chart",
            training_due:           "fa-graduation-cap",
            leave_balance_critical: "fa-plane",
            attendance_anomaly:     "fa-clock-o",
            disciplinary_followup:  "fa-gavel",
        };
        return iconMap[alertType] || "fa-bell";
    }

    formatAlertType(alertType) {
        return (alertType || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }


    daysLeftLabel(daysLeft) {
        if (daysLeft < 0)  return _t("%sd overdue").replace("%s", Math.abs(daysLeft));
        if (daysLeft === 0) return _t("Today");
        if (daysLeft === 1) return _t("Tomorrow");
        return _t("%sd remaining").replace("%s", daysLeft);
    }

    daysLeftClass(daysLeft, severity) {
        if (severity === "critical") return "text-danger fw-bold";
        if (severity === "warning")  return "text-warning fw-bold";
        return "text-muted";
    }

    setSection(section) {
        this.state.activeSection = section;
    }

    // ---------------------------------------------------------------- //
    //  Actions                                                           //
    // ---------------------------------------------------------------- //
    async dismissAlert(alertId) {
        this.state.dismissing = alertId;
        try {
            const res = await this.orm.call("hr.smart.alert", "dismiss_alert", [alertId]);
            if (res.success) {
                this.notification.add(_t("Alert acknowledged & dismissed."), { type: "success" });
                await this.props.onRefresh();
            } else {
                this.notification.add(res.message || _t("Could not dismiss alert."), { type: "warning" });
            }
        } catch (e) {
            this.notification.add(_t("Error dismissing alert."), { type: "danger" });
        } finally {
            this.state.dismissing = null;
        }
    }

    openEmployeeDrawer(employeeId) {
        if (employeeId) {
            this.props.onOpen360Drawer(employeeId);
        }
    }
}
