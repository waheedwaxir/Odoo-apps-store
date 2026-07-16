/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class OrgNode extends Component {
    static template = "wu_hr_employee360.OrgNode";
    static components = { OrgNode };
    static props = {
        node: { type: Object, required: true },
        onNodeClick: { type: Function, required: true },
        onNodeDblClick: { type: Function, required: true },
    };
}

export class OrgChartTree extends Component {
    static template = "wu_hr_employee360.OrgChartTree";
    static components = { OrgNode };
    static props = {
        employees: { type: Array, required: true },
        onOpenProfile: { type: Function, required: true },
    };

    setup() {
        this.state = useState({
            treeData: null,
        });

        onWillStart(() => {
            this.buildTree();
        });
    }

    buildTree() {
        if (!this.props.employees || this.props.employees.length === 0) return;
        
        // Find top-level manager or CEO (employee without manager or highest level)
        const emps = this.props.employees;
        const ceo = emps.find(e => !e.manager || e.manager === '-' || e.job_title.toLowerCase().includes('ceo') || e.job_title.toLowerCase().includes('director')) || emps[0];

        const buildNode = (emp, depth = 0) => {
            const children = emps.filter(e => e.manager === emp.name && e.id !== emp.id).map(c => buildNode(c, depth + 1));
            return {
                id: emp.id,
                name: emp.name,
                job_title: emp.job_title,
                photo_url: emp.photo_url,
                is_ceo: depth === 0,
                expanded: depth < 2, // Auto-expand up to level 2
                children: children
            };
        };

        this.state.treeData = buildNode(ceo);
    }

    onNodeClick(node) {
        if (node.children && node.children.length > 0) {
            node.expanded = !node.expanded;
        }
    }

    onNodeDblClick(empId) {
        if (this.props.onOpenProfile && empId) {
            this.props.onOpenProfile(empId);
        }
    }

    expandAll() {
        const toggle = (node, state) => {
            node.expanded = state;
            if (node.children) node.children.forEach(c => toggle(c, state));
        };
        if (this.state.treeData) toggle(this.state.treeData, true);
    }

    collapseAll() {
        const toggle = (node, state) => {
            node.expanded = state;
            if (node.children) node.children.forEach(c => toggle(c, state));
        };
        if (this.state.treeData) toggle(this.state.treeData, false);
    }
}
