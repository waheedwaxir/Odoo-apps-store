/** @odoo-module **/
import { Component, useState } from "@odoo/owl";

/**
 * FilterPanel — collapsible 10-field advanced filter bar.
 * Emits onApply(filters) when HR clicks Apply.
 * Emits onReset() when HR resets all filters.
 */
export class FilterPanel extends Component {
    static template = "wu_hr_employee360.FilterPanel";
    static props = {
        isVisible:    { type: Boolean },
        activeFilters: { type: Object },
        onApply:      { type: Function },
        onReset:      { type: Function },
        onToggle:     { type: Function },
    };

    setup() {
        this.state = useState({
            // Mirror of active filters, editable in the panel
            department_id:     this.props.activeFilters.department_id     || "",
            job_id:            this.props.activeFilters.job_id            || "",
            employment_status: this.props.activeFilters.employment_status || "",
            employment_type:   this.props.activeFilters.employment_type   || "",
            gender:            this.props.activeFilters.gender            || "",
            nationality:       this.props.activeFilters.nationality       || "",
            hire_date_from:    this.props.activeFilters.hire_date_from    || "",
            hire_date_to:      this.props.activeFilters.hire_date_to      || "",
            employee_search:   this.props.activeFilters.employee_search   || "",
            company_id:        this.props.activeFilters.company_id        || "",
        });
    }

    get activeCount() {
        return Object.values(this.state).filter(v => v && v !== "").length;
    }

    applyFilters() {
        const filters = {};
        for (const [k, v] of Object.entries(this.state)) {
            if (v !== "" && v !== null && v !== undefined) {
                filters[k] = v;
            }
        }
        this.props.onApply(filters);
    }

    resetFilters() {
        for (const key of Object.keys(this.state)) {
            this.state[key] = "";
        }
        this.props.onReset();
    }

    updateField(field, value) {
        this.state[field] = value;
    }
}
