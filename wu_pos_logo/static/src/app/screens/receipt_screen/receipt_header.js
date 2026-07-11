/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";

patch(ReceiptHeader.prototype, {
    get wuShowReceiptLogo() {
        if (!this.order || !this.order.config || !this.order.config.enable_receipt_logo) {
            return Boolean(this.logoUrl);
        }
        return this.order.config.receipt_logo_option !== 'no_logo' && Boolean(this.logoUrl);
    }
});
