/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class SmartSearchModal extends Component {
    static template = "wu_hr_employee360.SmartSearchModal";
    static props = {
        employees: { type: Array, required: true },
        onSelectEmployee: { type: Function, required: true },
        onClose: { type: Function, required: true },
    };

    setup() {
        this.notification = useService("notification");
        this.state = useState({
            searchQuery: "",
            barcodeInput: "",
            qrMode: false,
            results: this.props.employees.slice(0, 10),
        });
    }

    toggleQrMode() {
        this.state.qrMode = !this.state.qrMode;
    }

    onSearchInput(event) {
        const q = event.target.value.toLowerCase().trim();
        this.state.searchQuery = q;
        if (!q) {
            this.state.results = this.props.employees.slice(0, 10);
            return;
        }
        this.state.results = this.props.employees.filter(emp => {
            return (emp.name && emp.name.toLowerCase().includes(q)) ||
                   (emp.job_title && emp.job_title.toLowerCase().includes(q)) ||
                   (emp.department && emp.department.toLowerCase().includes(q)) ||
                   (String(emp.id).includes(q));
        }).slice(0, 15);
    }

    onBarcodeEnter(event) {
        if (event.key === "Enter") {
            this.onScanSubmit();
        }
    }

    onScanSubmit() {
        const code = this.state.barcodeInput.trim().toUpperCase();
        if (!code) return;
        const matched = this.props.employees.find(e => `EMP-${String(e.id).padStart(4, '0')}` === code || String(e.id) === code || (e.name && e.name.toUpperCase().includes(code)));
        if (matched) {
            this.notification.add(`Scanned verified employee badge: ${matched.name}`, { type: "success" });
            this.props.onSelectEmployee(matched.id);
            this.props.onClose();
        } else {
            this.notification.add(`No employee found matching badge ID: ${code}`, { type: "danger" });
        }
    }

    onSelectEmployee(empId) {
        this.props.onSelectEmployee(empId);
        this.props.onClose();
    }
}
