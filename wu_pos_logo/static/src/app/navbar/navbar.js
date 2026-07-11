/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";

patch(Navbar.prototype, {
    get wuShowPosLogo() {
        if (!this.pos || !this.pos.config.enable_pos_logo) {
            return !this.pos.getOrder();
        }
        if (this.pos.config.pos_logo_option === 'no_logo') {
            return false;
        }
        return true;
    },
    get wuLogoUrl() {
        if (!this.pos || !this.pos.config.enable_pos_logo) {
            return null;
        }
        if (this.pos.config.pos_logo_option === 'company') {
            return `/web/image?model=res.company&id=${this.pos.company.id}&field=logo`;
        }
        if (this.pos.config.pos_logo_option === 'custom_image' && this.pos.config.pos_custom_logo) {
            return `/web/image?model=pos.config&id=${this.pos.config.id}&field=pos_custom_logo`;
        }
        return null;
    }
});
