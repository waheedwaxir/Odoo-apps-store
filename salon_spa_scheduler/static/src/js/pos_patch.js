import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";

// Id of the "Membership Discount" product, learned at POS start-up.
let salonDiscountProductId = null;
// Product ids of the salon services and of the staff tip, for the order sections.
let salonServiceIds = new Set();
let salonTipProductId = null;

// Is this product.product id a salon service (linked to a salon.service)?
export function isSalonServiceProductId(productId) {
    return salonServiceIds.has(productId);
}

// The staff tip and the membership discount: lines nobody "sells".
export function isSalonExtraProductId(productId) {
    return Boolean(productId) && (productId === salonTipProductId || productId === salonDiscountProductId);
}

function salonLoadInfo(info) {
    if (!info) {
        return;
    }
    salonDiscountProductId = info.discount_product_id || salonDiscountProductId;
    salonTipProductId = info.tip_product_id || null;
    salonServiceIds = new Set(info.service_product_ids || []);
}

patch(PosStore.prototype, {
    async afterProcessServerData() {
        await super.afterProcessServerData();
        try {
            const info = await this.data.call("salon.membership.line", "get_pos_member_discount", [
                false,
                this.company.id,
            ]);
            salonLoadInfo(info);
        } catch (e) {
            console.warn("Salon membership discount product lookup failed", e);
        }
        if (!this.config.module_pos_restaurant && !this.router.state.params.orderUuid) {
            const openOrders = this.data.models["pos.order"].filter((order) => !order.finalized);
            const unsyncedOpenOrders = openOrders.filter((order) => !order.isSynced);
            this.selectedOrderUuid = unsyncedOpenOrders.length
                ? unsyncedOpenOrders[unsyncedOpenOrders.length - 1].uuid
                : this.getEmptyOrder().uuid;
        }
        // POS renames loaded lines; re-sync the membership discount line (name/amount).
        for (const order of this.data.models["pos.order"].filter((o) => !o.finalized)) {
            this.applySalonMembershipDiscount(order);
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

// ---- Membership discount --------------------------------------------------
// A customer with an active membership plan gets the plan's discount on the
// salon services of an order once those services reach the plan's minimum
// spend. The discount is one separate, last order line named after the plan
// (product "Membership Discount"); it is recomputed whenever the order changes.
let salonPosStore = null;
const salonApplying = new WeakSet();
const salonPending = new WeakSet();

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        salonPosStore = this;
    },
    async applySalonMembershipDiscount(order) {
        if (!order || order.finalized) {
            return;
        }
        if (salonApplying.has(order)) {
            salonPending.add(order);
            return;
        }
        salonApplying.add(order);
        try {
            do {
                salonPending.delete(order);
                await this._salonSyncDiscountLine(order);
            } while (salonPending.has(order));
        } catch (e) {
            console.warn("Salon membership discount failed", e);
        } finally {
            salonApplying.delete(order);
            salonPending.delete(order);
        }
    },
    async _salonSyncDiscountLine(order) {
        const partner = order.getPartner();
        const offer = await this.data.call("salon.membership.line", "get_pos_member_discount", [
            partner ? partner.id : false,
            this.company.id,
        ]);
        if (!offer || !offer.discount_product_id) {
            return;
        }
        salonLoadInfo(offer);
        const discountLines = order.lines.filter((l) => l.product_id?.id === offer.discount_product_id);
        const serviceIds = new Set(offer.service_product_ids);
        const serviceLines = order.lines.filter((l) => serviceIds.has(l.product_id?.id));
        const spend = serviceLines.reduce(
            (sum, l) => sum + l.price_unit * l.getQuantity() * (1 - (l.getDiscount() || 0) / 100),
            0
        );
        const qualifies = offer.discount > 0 && spend > 0 && spend >= (offer.min_spend || 0);
        const amount = qualifies ? Math.round(spend * offer.discount) / 100 : 0;

        const current = discountLines.length === 1 ? discountLines[0] : null;
        const isLast = current && order.lines[order.lines.length - 1] === current;
        if (amount === 0 && !discountLines.length) {
            return;
        }
        if (
            current &&
            isLast &&
            amount > 0 &&
            Math.abs(current.price_unit + amount) < 0.005 &&
            current.full_product_name === offer.name
        ) {
            return;
        }
        for (const line of discountLines) {
            line.delete();
        }
        if (amount <= 0) {
            return;
        }
        let product = this.models["product.product"].get(offer.discount_product_id);
        if (!product) {
            await this.loadNewProducts([["id", "=", offer.discount_product_tmpl_id]]);
            product = this.models["product.product"].get(offer.discount_product_id);
        }
        if (!product) {
            return;
        }
        const vals = {
            product_tmpl_id: product.product_tmpl_id,
            product_id: product,
            price_unit: -amount,
            qty: 1,
        };
        // Same taxes as the discounted services when they all share them.
        const taxKeys = new Set(serviceLines.map((l) => l.tax_ids.map((t) => t.id).sort().join(",")));
        if (taxKeys.size === 1 && serviceLines[0].tax_ids.length) {
            vals.tax_ids = [["link", ...serviceLines[0].tax_ids]];
        }
        const line = await this.addLineToOrder(vals, order, { merge: false }, false);
        if (line) {
            line.full_product_name = offer.name;
        }
    },
    async addLineToOrder(vals, order) {
        const line = await super.addLineToOrder(...arguments);
        if (!salonApplying.has(order)) {
            await this.applySalonMembershipDiscount(order);
        }
        return line;
    },
    setPartnerToCurrentOrder(partner) {
        super.setPartnerToCurrentOrder(...arguments);
        this.applySalonMembershipDiscount(this.getOrder());
    },
});

patch(PosOrder.prototype, {
    removeOrderline(line) {
        const res = super.removeOrderline(...arguments);
        salonPosStore?.applySalonMembershipDiscount(this);
        return res;
    },
});

const SALON_DISCOUNT_CODE = "SALON_MEMBER_DISC";

patch(PosOrderline.prototype, {
    // The global Discount button only discounts salon services (per POS setting);
    // the membership discount line is never re-discounted.
    isGlobalDiscountApplicable() {
        if (!super.isGlobalDiscountApplicable(...arguments)) {
            return false;
        }
        if (this.isSalonMemberDiscount) {
            return false;
        }
        if (this.config?.salon_discount_services_only && salonServiceIds.size) {
            return salonServiceIds.has(this.product_id?.id);
        }
        return true;
    },
    // The membership discount line is named after the plan, not the product.
    get isSalonMemberDiscount() {
        const product = this.product_id;
        return (
            !!product &&
            (product.default_code === SALON_DISCOUNT_CODE ||
                (salonDiscountProductId && product.id === salonDiscountProductId))
        );
    },
    setFullProductName() {
        const keep = this.isSalonMemberDiscount ? this.full_product_name : null;
        super.setFullProductName(...arguments);
        if (keep) {
            this.full_product_name = keep;
        }
    },
    get orderDisplayProductName() {
        if (this.isSalonMemberDiscount && this.full_product_name) {
            return { name: this.full_product_name, attributeString: "" };
        }
        return super.orderDisplayProductName;
    },
    setQuantity(quantity) {
        const res = super.setQuantity(...arguments);
        if (this.order_id) {
            salonPosStore?.applySalonMembershipDiscount(this.order_id);
        }
        return res;
    },
});

// ---- Order sections ---------------------------------------------------------
// Group the order lines into Services (with the membership discount line) and
// Products (and Tips), since members get no discount on products.
const SALON_SECTIONS = ["Services", "Services", "Products", "Tips", ""];
// Shown beside the English heading when the POS setting "Arabic Section
// Titles" is on - the receipt has to carry Arabic.
const SALON_SECTIONS_AR = {
    Services: "الخدمات",
    Products: "المنتجات",
    Tips: "البقشيش",
};

function salonSectionRank(line) {
    const id = line.product_id?.id;
    if (line.isSalonMemberDiscount) {
        return 1;
    }
    // Global Discount button line: closes the Services section when the button is
    // limited to services, otherwise it is the last line of the order.
    if (line.isDiscountLine) {
        return line.config?.salon_discount_services_only ? 1 : 4;
    }
    if (salonServiceIds.has(id)) {
        return 0;
    }
    if (salonTipProductId && id === salonTipProductId) {
        return 3;
    }
    return 2;
}

patch(OrderDisplay.prototype, {
    get comboSortedLines() {
        const lines = super.comboSortedLines;
        if (lines.some((l) => l.combo_line_ids?.length || l.combo_parent_id) || !salonServiceIds.size) {
            return lines;
        }
        return lines
            .map((line, index) => ({ line, index, rank: salonSectionRank(line) }))
            .sort((a, b) => a.rank - b.rank || a.index - b.index)
            .map((entry) => entry.line);
    },
    salonSectionTitle(line) {
        const lines = this.comboSortedLines;
        if (!salonServiceIds.size) {
            return "";
        }
        const titles = lines.map((l) => SALON_SECTIONS[salonSectionRank(l)]);
        if (new Set(titles.filter(Boolean)).size < 2) {
            return "";
        }
        const idx = lines.findIndex((l) => l.uuid === line.uuid);
        return idx === 0 || titles[idx] !== titles[idx - 1] ? titles[idx] : "";
    },
    salonSectionArabic(line) {
        const config = line.config || this.props.order?.config;
        if (!config?.salon_arabic_sections) {
            return "";
        }
        return SALON_SECTIONS_AR[this.salonSectionTitle(line)] || "";
    },
});
