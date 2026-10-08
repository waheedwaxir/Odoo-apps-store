/** @odoo-module **/

import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";

const cogMenuRegistry = registry.category("cogMenu");

/**
 * "Import from Employees" entry in the gear / cog menu of the salon.staff
 * list & kanban views, next to "Import records" / "Export All" / "Spreadsheet".
 * Opens the salon.staff.import.wizard.
 */
export class SalonStaffImportCogMenu extends Component {
    static template = "salon_spa_scheduler.SalonStaffImportCogMenu";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.action = useService("action");
    }

    openImportWizard() {
        this.action.doAction("salon_spa_scheduler.action_salon_staff_import_wizard", {
            additionalContext: this.env.searchModel.context,
        });
    }
}

export const salonStaffImportCogMenuItem = {
    Component: SalonStaffImportCogMenu,
    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
    isDisplayed: ({ config, searchModel }) =>
        searchModel.resModel === "salon.staff" &&
        config.actionType === "ir.actions.act_window" &&
        ["list", "kanban"].includes(config.viewType),
};

cogMenuRegistry.add("salon-staff-import-menu", salonStaffImportCogMenuItem, { sequence: 2 });
