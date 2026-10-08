import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";

/**
 * Membership discount for the POS.
 *
 * A customer with an active membership plan gets the plan's discount on the
 * *services* of an order (products whose Product Type is "Service") once those
 * services reach the plan's minimum spend. The discount is one separate line
 * named after the plan (product "Membership Discount"), kept in the Services
 * section and recomputed whenever the order changes.
 */
const DISCOUNT_CODE = "TS_MEMBER_DISC";
const MODEL = "ts.membership";
const METHOD = "get_pos_member_discount";

// Id of the "Membership Discount" product, learned at POS start-up.
let discountProductId = null;
let posStore = null;
const applying = new WeakSet();
const pending = new WeakSet();

function isMemberDiscountLine(line) {
    const product = line.product_id;
    return (
        !!product &&
        (product.default_code === DISCOUNT_CODE ||
            (discountProductId && product.id === discountProductId))
    );
}

function isServiceLine(line) {
    if (isMemberDiscountLine(line) || line.isDiscountLine) {
        return false;
    }
    const tipId = line.config?.tip_product_id?.id;
    if (tipId && line.product_id?.id === tipId) {
        return false;
    }
    return line.product_id?.product_tmpl_id?.type === "service";
}

patch(PosStore.prototype, {
    async afterProcessServerData() {
        await super.afterProcessServerData(...arguments);
        posStore = this;
        try {
            const info = await this.data.call(MODEL, METHOD, [false, this.company.id]);
            discountProductId = info?.discount_product_id || null;
        } catch (e) {
            console.warn("Membership discount product lookup failed", e);
        }
        // POS renames loaded lines; re-sync the discount line (name/amount).
        for (const order of this.data.models["pos.order"].filter((o) => !o.finalized)) {
            this.applyMembershipDiscount(order);
        }
    },
    async applyMembershipDiscount(order) {
        if (!order || order.finalized) {
            return;
        }
        if (applying.has(order)) {
            pending.add(order);
            return;
        }
        applying.add(order);
        try {
            do {
                pending.delete(order);
                await this._syncMembershipDiscountLine(order);
            } while (pending.has(order));
        } catch (e) {
            console.warn("Membership discount failed", e);
        } finally {
            applying.delete(order);
            pending.delete(order);
        }
    },
    async _syncMembershipDiscountLine(order) {
        const partner = order.getPartner();
        const offer = await this.data.call(MODEL, METHOD, [
            partner ? partner.id : false,
            this.company.id,
        ]);
        if (!offer || !offer.discount_product_id) {
            return;
        }
        discountProductId = offer.discount_product_id;
        const discountLines = order.lines.filter(isMemberDiscountLine);
        const serviceLines = order.lines.filter(isServiceLine);
        const spend = serviceLines.reduce(
            (sum, l) => sum + l.price_unit * l.getQuantity() * (1 - (l.getDiscount() || 0) / 100),
            0
        );
        const qualifies = offer.discount > 0 && spend > 0 && spend >= (offer.min_spend || 0);
        const amount = qualifies ? Math.round(spend * offer.discount) / 100 : 0;

        const current = discountLines.length === 1 ? discountLines[0] : null;
        if (amount === 0 && !discountLines.length) {
            return;
        }
        if (
            current &&
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
        if (!applying.has(order)) {
            await this.applyMembershipDiscount(order);
        }
        return line;
    },
    setPartnerToCurrentOrder(partner) {
        super.setPartnerToCurrentOrder(...arguments);
        this.applyMembershipDiscount(this.getOrder());
    },
});

patch(PosOrder.prototype, {
    removeOrderline(line) {
        const res = super.removeOrderline(...arguments);
        posStore?.applyMembershipDiscount(this);
        return res;
    },
});

patch(PosOrderline.prototype, {
    // The membership discount line is named after the plan, not the product.
    get isTsMemberDiscount() {
        return isMemberDiscountLine(this);
    },
    // The global Discount button only discounts services (per POS setting);
    // the membership discount line is never re-discounted.
    isGlobalDiscountApplicable() {
        if (!super.isGlobalDiscountApplicable(...arguments)) {
            return false;
        }
        if (isMemberDiscountLine(this)) {
            return false;
        }
        if (this.config?.ts_discount_services_only) {
            return isServiceLine(this);
        }
        return true;
    },
    setFullProductName() {
        const keep = isMemberDiscountLine(this) ? this.full_product_name : null;
        super.setFullProductName(...arguments);
        if (keep) {
            this.full_product_name = keep;
        }
    },
    get orderDisplayProductName() {
        if (isMemberDiscountLine(this) && this.full_product_name) {
            return { name: this.full_product_name, attributeString: "" };
        }
        return super.orderDisplayProductName;
    },
    setQuantity() {
        const res = super.setQuantity(...arguments);
        if (this.order_id) {
            posStore?.applyMembershipDiscount(this.order_id);
        }
        return res;
    },
});

// ---- Order sections -----------------------------------------------------------
// Services (with the membership discount line) / Products / Tips.
const SECTIONS = ["Services", "Services", "Products", "Tips", ""];

function sectionRank(line) {
    if (isMemberDiscountLine(line)) {
        return 1;
    }
    // Global Discount button line: closes the Services section when the button is
    // limited to services, otherwise it is the last line of the order.
    if (line.isDiscountLine) {
        return line.config?.ts_discount_services_only ? 1 : 4;
    }
    if (isServiceLine(line)) {
        return 0;
    }
    const tipId = line.config?.tip_product_id?.id;
    if (tipId && line.product_id?.id === tipId) {
        return 3;
    }
    return 2;
}

patch(OrderDisplay.prototype, {
    get comboSortedLines() {
        const lines = super.comboSortedLines;
        if (lines.some((l) => l.combo_line_ids?.length || l.combo_parent_id)) {
            return lines;
        }
        return lines
            .map((line, index) => ({ line, index, rank: sectionRank(line) }))
            .sort((a, b) => a.rank - b.rank || a.index - b.index)
            .map((entry) => entry.line);
    },
    membershipSectionTitle(line) {
        const lines = this.comboSortedLines;
        const titles = lines.map((l) => SECTIONS[sectionRank(l)]);
        if (new Set(titles.filter(Boolean)).size < 2) {
            return "";
        }
        const idx = lines.findIndex((l) => l.uuid === line.uuid);
        return idx === 0 || titles[idx] !== titles[idx - 1] ? titles[idx] : "";
    },
});
