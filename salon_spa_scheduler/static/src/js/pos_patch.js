import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosStore.prototype, {
    async afterProcessServerData() {
        await super.afterProcessServerData();
        if (!this.config.module_pos_restaurant && !this.router.state.params.orderUuid) {
            const openOrders = this.data.models["pos.order"].filter((order) => !order.finalized);
            const unsyncedOpenOrders = openOrders.filter((order) => !order.isSynced);
            this.selectedOrderUuid = unsyncedOpenOrders.length
                ? unsyncedOpenOrders[unsyncedOpenOrders.length - 1].uuid
                : this.getEmptyOrder().uuid;
        }
    }
});

patch(PosOrder.prototype, {
    getChange() {
        return this.change || 0;
    },
    get_change() {
        return this.change || 0;
    }
});

patch(PosOrderline.prototype, {
    setup(_defaultObj, options = {}) {
        super.setup(...arguments);
        if (!this.product_id) {
            return;
        }
        let staffVal = this.staff_id || this.raw?.staff_id || (options && options.extras && options.extras.staff_id) || false;
        if (Array.isArray(staffVal)) {
            this.staff_id = { id: staffVal[0] };
        } else if (typeof staffVal === 'number') {
            this.staff_id = { id: staffVal };
        } else {
            this.staff_id = staffVal;
        }
    },
    setOptions(options) {
        super.setOptions(...arguments);
        if (options && options.extras && options.extras.staff_id) {
            let staffId = options.extras.staff_id;
            this.staff_id = typeof staffId === 'number' ? { id: staffId } : staffId;
        }
    },
    serializeForORM() {
        const result = super.serializeForORM(...arguments);
        if (result) {
            result.staff_id = this.staff_id && this.staff_id.id ? this.staff_id.id : (this.staff_id || false);
        }
        return result;
    },
    serializeForIndexedDB() {
        const result = super.serializeForIndexedDB(...arguments);
        if (result) {
            result.staff_id = this.staff_id && this.staff_id.id ? this.staff_id.id : (this.staff_id || false);
        }
        return result;
    },
    get productProductPrice() {
        if (!this.product_id) {
            return 0;
        }
        return super.productProductPrice;
    },
    prepareBaseLineForTaxesComputationExtraValues(customValues = {}) {
        const product = customValues.product_id ?? this.product_id;
        if (!product) {
            return {
                id: this.uuid,
                price_unit: customValues.price_unit ?? this.getUnitPrice(),
                quantity: this.getQuantity(),
                discount: this.getDiscount(),
                tax_ids: this.tax_ids,
                product_id: product,
                rate: 1.0,
                is_refund: false,
                ...customValues,
            };
        }
        return super.prepareBaseLineForTaxesComputationExtraValues(...arguments);
    }
});
