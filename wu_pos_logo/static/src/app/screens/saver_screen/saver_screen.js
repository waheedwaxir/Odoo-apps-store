/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { SaverScreen } from "@point_of_sale/app/screens/saver_screen/saver_screen";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

patch(SaverScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },
    get wuScreenSaverStyle() {
        if (this.pos && this.pos.config.enable_screen_saver_bg && this.pos.config.pos_screen_saver_image) {
            const url = `/web/image?model=pos.config&id=${this.pos.config.id}&field=pos_screen_saver_image`;
            return `background-image: url('${url}') !important; background-size: cover !important; background-position: center !important;`;
        }
        return "";
    },
    get wuTimerColorStyle() {
        if (this.pos && this.pos.config.enable_screen_saver_bg && this.pos.config.pos_timer_color) {
            return `color: ${this.pos.config.pos_timer_color} !important;`;
        }
        return "";
    },
    get wuShowPosLogo() {
        if (!this.pos || !this.pos.config.enable_pos_logo) {
            return !this.pos.config.enable_screen_saver_bg;
        }
        return this.pos.config.pos_logo_option !== 'no_logo';
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
