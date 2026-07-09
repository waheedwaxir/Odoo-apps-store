import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { TipStaffPopup } from "./TipStaffPopup";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

patch(ControlButtons.prototype, {
    async clickTipStaff() {
        const payload = await makeAwaitable(this.dialog, TipStaffPopup, {
            title: _t("Tip Staff"),
        });

        if (payload && payload.amount > 0) {
            // Find the Tip Product
            const tipProducts = await this.env.services.orm.searchRead(
                "product.product",
                [["name", "=", "Staff Tip"], ["available_in_pos", "=", true]],
                ["id", "product_tmpl_id"],
                { limit: 1 }
            );

            if (tipProducts.length > 0) {
                let product = this.pos.models["product.product"].get(tipProducts[0].id);
                if (!product) {
                    const tmplId = Array.isArray(tipProducts[0].product_tmpl_id) 
                        ? tipProducts[0].product_tmpl_id[0] 
                        : tipProducts[0].product_tmpl_id;
                    await this.pos.loadNewProducts([["id", "=", tmplId]]);
                    product = this.pos.models["product.product"].get(tipProducts[0].id);
                }
                if (product) {
                    const staffRecord = this.pos.models["salon.staff"]?.get(payload.staff_id) || { id: payload.staff_id };
                    await this.pos.addLineToCurrentOrder({
                        product_tmpl_id: product.product_tmpl_id,
                        price_unit: payload.amount,
                        qty: 1,
                        extras: {
                            staff_id: staffRecord,
                        },
                    });
                } else {
                    this.dialog.add(AlertDialog, {
                        title: _t('Error'),
                        body: _t('Tip product not loaded in POS. Please refresh.'),
                    });
                }
            } else {
                this.dialog.add(AlertDialog, {
                    title: _t('Configuration Error'),
                    body: _t('Could not find the "Staff Tip" product. Please ensure it exists.'),
                });
            }
        }
    }
});
