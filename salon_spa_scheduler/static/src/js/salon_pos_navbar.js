import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    // Same redirect mechanism as PosStore.redirectToBackend() (pos_store.js),
    // just pointing at the Salon & Spa app's root action instead of the POS
    // backend menu, so cashiers can jump straight back to the scheduler.
    goToSalonApp() {
        window.location = "/odoo/action-salon_spa_scheduler.action_salon_scheduler_client";
    },
});
