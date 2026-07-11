/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    get idleTimeout() {
        if (this.config && this.config.enable_screen_saver_bg) {
            const timerMinutes = this.config.pos_screen_timer > 0 ? this.config.pos_screen_timer : 1;
            const timeoutMs = timerMinutes * 60 * 1000;
            return [
                {
                    timeout: timeoutMs,
                    action: () =>
                        this.router.state.current !== "PaymentScreen" && this.navigate("SaverScreen"),
                },
            ];
        }
        return super.idleTimeout;
    }
});
