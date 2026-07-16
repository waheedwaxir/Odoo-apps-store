/** @odoo-module **/

/**
 * ExcelExporter — pure browser-side multi-sheet Excel (.xlsx) export.
 * Uses SheetJS (xlsx) bundled locally as a vendor script.
 *
 * Usage:
 *   import { ExcelExporter } from "./excel_exporter";
 *   ExcelExporter.exportToExcel(dashboardData, activeFilters);
 */
export class ExcelExporter {

    // ---------------------------------------------------------------- //
    //  Public entry point                                               //
    // ---------------------------------------------------------------- //
    static exportToExcel(data, filters = {}) {
        if (typeof XLSX === "undefined") {
            alert("SheetJS library not loaded. Please check your module assets.");
            return;
        }

        const wb = XLSX.utils.book_new();
        const today = new Date().toISOString().slice(0, 10);

        // ── Sheet 1: Employee Directory ──────────────────────────────
        ExcelExporter._addSheet(wb, "Employee Directory",
            ExcelExporter._buildDirectorySheet(data));

        // ── Sheet 2: Attendance Summary ──────────────────────────────
        ExcelExporter._addSheet(wb, "Attendance Summary",
            ExcelExporter._buildAttendanceSheet(data));

        // ── Sheet 3: Leave Summary ───────────────────────────────────
        ExcelExporter._addSheet(wb, "Leave Summary",
            ExcelExporter._buildLeaveSheet(data));

        // ── Sheet 4: Smart Alerts ────────────────────────────────────
        ExcelExporter._addSheet(wb, "Smart Alerts",
            ExcelExporter._buildAlertsSheet(data));

        // ── Sheet 5: Filter Applied ──────────────────────────────────
        ExcelExporter._addSheet(wb, "Export Info",
            ExcelExporter._buildInfoSheet(filters, today));

        const filename = `HR_360_Dashboard_${today}.xlsx`;
        XLSX.writeFile(wb, filename);
    }

    // ---------------------------------------------------------------- //
    //  Sheet Builders                                                  //
    // ---------------------------------------------------------------- //
    static _buildDirectorySheet(data) {
        const rows = [
            ["#", "Full Name", "Department", "Job Position", "Gender",
             "Nationality", "Contract Type", "Join Date", "Manager",
             "Work Email", "Mobile", "Status"],
        ];
        const employees = data.employee_list || [];
        employees.forEach((emp, i) => {
            rows.push([
                i + 1,
                emp.name || "",
                emp.department || "",
                emp.job || "",
                emp.gender || "",
                emp.nationality || "",
                emp.employment_type || "",
                emp.join_date || "",
                emp.manager || "",
                emp.work_email || "",
                emp.mobile || "",
                emp.status || "Confirmed",
            ]);
        });
        return rows;
    }

    static _buildAttendanceSheet(data) {
        const att = data.attendance_dashboard || {};
        const rows = [
            ["Attendance Summary", "", "", "", ""],
            ["Metric", "Count / Value", "", "", ""],
            ["Present Today", att.present_today || 0],
            ["Absent Today", att.absent_today || 0],
            ["Attendance Rate %", att.attendance_rate || 0],
            ["Absent Rate %", att.absent_rate || 0],
            ["Work From Home", att.wfh_today || 0],
            ["Late Arrivals", att.late_today || 0],
            ["", ""],
            ["Employee Name", "Check-In Status"],
        ];
        (att.present_emp_ids || []).forEach(id => {
            rows.push([`Employee ID: ${id}`, "Present"]);
        });
        (att.missing_checkout_emp_ids || []).forEach(id => {
            rows.push([`Employee ID: ${id}`, "Missing Checkout"]);
        });
        return rows;
    }

    static _buildLeaveSheet(data) {
        const lv = data.leave_dashboard || {};
        const rows = [
            ["Leave Summary", "", "", ""],
            ["Type", "Count", "", ""],
            ["Approved Leaves", lv.approved_leave || 0],
            ["Annual Leave", lv.annual_leave || 0],
            ["Sick Leave", lv.sick_leave || 0],
            ["Unpaid Leave", lv.unpaid_leave || 0],
            ["Pending Approvals", lv.pending_leave || 0],
            ["", ""],
            ["Leave Records", "", "", ""],
            ["Employee", "Leave Type", "From", "To", "Days", "Status"],
        ];
        (lv.leave_records || []).forEach(r => {
            rows.push([
                r.employee || "",
                r.leave_type || "",
                r.date_from || "",
                r.date_to || "",
                r.days || "",
                r.state || "",
            ]);
        });
        return rows;
    }

    static _buildAlertsSheet(data) {
        const sa = data.smart_alerts || {};
        const rows = [
            ["Smart HR Alerts Export", "", "", "", ""],
            ["Total Alerts", sa.total || 0, "", "", ""],
            ["Unread", sa.unread || 0, "", "", ""],
            ["", ""],
            ["Severity", "Alert Type", "Employee", "Department", "Message", "Due Date", "Days Left"],
        ];
        const allAlerts = [
            ...(sa.critical || []).map(a => ({...a, _sev: "🔴 Critical"})),
            ...(sa.warning  || []).map(a => ({...a, _sev: "🟡 Warning"})),
            ...(sa.info     || []).map(a => ({...a, _sev: "🔵 Info"})),
        ];
        allAlerts.forEach(a => {
            rows.push([
                a._sev,
                (a.alert_type || "").replace(/_/g, " "),
                a.employee_name || "",
                a.department || "",
                a.message || "",
                a.due_date || "",
                a.days_left || 0,
            ]);
        });
        return rows;
    }

    static _buildInfoSheet(filters, exportDate) {
        const rows = [
            ["HR 360 Dashboard Export", "", ""],
            ["", ""],
            ["Export Date", exportDate],
            ["Generated By", "HR Employee 360° Dashboard Pro"],
            ["", ""],
            ["Active Filters Applied", "", ""],
            ["Filter", "Value", ""],
        ];
        const filterLabels = {
            employee_search:   "Employee Search",
            department_id:     "Department",
            job_id:            "Job Position",
            employment_status: "Employment Status",
            employment_type:   "Contract Type",
            gender:            "Gender",
            nationality:       "Nationality",
            hire_date_from:    "Hired From",
            hire_date_to:      "Hired To",
            company_id:        "Company",
        };
        let hasFilter = false;
        for (const [key, label] of Object.entries(filterLabels)) {
            if (filters[key]) {
                rows.push([label, filters[key], ""]);
                hasFilter = true;
            }
        }
        if (!hasFilter) {
            rows.push(["(No filters applied — full dataset)", "", ""]);
        }
        return rows;
    }

    // ---------------------------------------------------------------- //
    //  Helpers                                                          //
    // ---------------------------------------------------------------- //
    static _addSheet(wb, sheetName, rows) {
        const ws = XLSX.utils.aoa_to_sheet(rows);

        // Style header row (bold simulation via column widths)
        const colWidths = rows[0]
            ? rows[0].map((_, ci) => ({
                wch: Math.max(
                    16,
                    ...rows.map(r => String(r[ci] ?? "").length + 2)
                )
              }))
            : [];
        ws["!cols"] = colWidths;

        XLSX.utils.book_append_sheet(wb, ws, sheetName);
    }
}
