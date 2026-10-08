import { Component } from "@odoo/owl";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { isSalonExtraProductId, isSalonServiceProductId } from "./pos_patch";
import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

/**
 * Who does a line. A salon service or a retail product tapped on the product
 * screen asks straight away; the Beautician button (in the "more" menu)
 * changes it on the selected line. For a product, "Default" leaves the sale
 * with the employee logged in at the till. The line shows the name
 * underneath, and once the order is paid the Sales History (and, for
 * services, the commissions) credit that beautician.
 */
export class BeauticianPopup extends Component {
    static template = "salon_spa_scheduler.BeauticianPopup";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        staff: Array,
        currentId: { optional: true },
        // Label of the "Default" choice (the cashier); none = no such choice.
        defaultLabel: { type: String, optional: true },
        getPayload: Function,
        close: Function,
    };

    pick(staff) {
        this.props.getPayload(staff);
        this.props.close();
    }

    pickDefault() {
        this.props.getPayload({ isDefault: true });
        this.props.close();
    }
}

// Beauticians who do this line's service: its category or an extra
// service of theirs covers it, or they have nothing picked (= every service).
// Anyone may sell a retail product.
function beauticiansFor(pos, line) {
    const all = (pos.models["salon.staff"]?.getAll() || [])
        .slice()
        .sort((a, b) => (a.name || "").localeCompare(b.name || ""));
    const productId = line.product_id?.id;
    if (!isSalonServiceProductId(productId)) {
        return all;
    }
    const productsOf = (staff) => (staff.pos_service_product_ids || []).map((p) => p?.id ?? p);
    const able = all.filter((staff) => {
        const products = productsOf(staff);
        return !products.length || products.includes(productId);
    });
    return able.length ? able : all;
}

async function pickBeautician(pos, dialog, line, { allowDefault = false } = {}) {
    const staff = beauticiansFor(pos, line);
    if (!staff.length) {
        dialog.add(AlertDialog, {
            title: _t("Beautician"),
            body: _t("No beauticians are set up for this branch."),
        });
        return;
    }
    const picked = await makeAwaitable(dialog, BeauticianPopup, {
        title: _t("Beautician for %s", line.getFullProductName?.() || line.product_id?.display_name || ""),
        staff,
        currentId: line.salon_beautician_id?.id || false,
        defaultLabel: allowDefault ? pos.getCashier?.()?.name || _t("Cashier") : undefined,
    });
    if (picked?.isDefault) {
        line.update({ salon_beautician_id: false, salon_beautician_name: false });
    } else if (picked) {
        line.update({
            salon_beautician_id: picked,
            salon_beautician_name: picked.name,
        });
    }
}

patch(ControlButtons.prototype, {
    async clickAssignBeautician() {
        const line = this.pos.getOrder()?.getSelectedOrderline();
        if (!line) {
            this.dialog.add(AlertDialog, {
                title: _t("Beautician"),
                body: _t("Select the line first, then pick who does it."),
            });
            return;
        }
        await pickBeautician(this.pos, this.dialog, line, { allowDefault: true });
    },
});

patch(ProductScreen.prototype, {
    // A salon service or a retail product tapped here asks who does / sells
    // it; a product may stay with the cashier ("Default").
    async addProductToOrder(product) {
        const order = this.pos.getOrder();
        const before = new Set((order?.lines || []).map((l) => l.uuid));
        const result = await super.addProductToOrder(...arguments);
        const line = this.pos.getOrder()?.getSelectedOrderline();
        const productId = line?.product_id?.id;
        if (
            line &&
            !before.has(line.uuid) &&
            !line.salon_beautician_id &&
            productId &&
            !isSalonExtraProductId(productId)
        ) {
            const isService = isSalonServiceProductId(productId);
            await pickBeautician(this.pos, this.dialog, line, { allowDefault: !isService });
        }
        return result;
    },
});

patch(PosOrderline.prototype, {
    // Each tap on a service is its own line, so the same service can be done
    // by two beauticians. Likewise each tip stays its own line, so a tip
    // split 10 + 10 between two beauticians keeps both of them.
    canBeMergedWith(orderline) {
        if (isSalonServiceProductId(this.product_id?.id) || this.staff_id || orderline?.staff_id) {
            return false;
        }
        return super.canBeMergedWith(...arguments);
    },
});
