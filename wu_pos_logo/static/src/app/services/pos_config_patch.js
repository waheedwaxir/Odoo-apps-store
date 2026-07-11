/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosConfig } from "@point_of_sale/app/models/pos_config";

patch(PosConfig.prototype, {
    get receiptCompanyLogoUrl() {
        if (this.enable_receipt_logo) {
            if (this.receipt_logo_option === 'no_logo') {
                return null;
            }
            if (this.receipt_logo_option === 'custom_image' && this.receipt_custom_logo) {
                return `/web/image?model=pos.config&id=${this.id}&field=receipt_custom_logo`;
            }
        }
        return super.receiptCompanyLogoUrl;
    },
    get receiptLogoUrl() {
        if (this.enable_receipt_logo && this.receipt_logo_option === 'no_logo') {
            return null;
        }
        return super.receiptLogoUrl;
    },
    async cacheReceiptLogo() {
        if (this.enable_receipt_logo && this.receipt_logo_option === 'no_logo') {
            this.uiState.receiptLogoDataUrl = null;
            return;
        }
        return super.cacheReceiptLogo();
    }
});
