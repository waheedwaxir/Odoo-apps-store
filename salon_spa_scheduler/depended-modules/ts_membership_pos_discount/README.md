# Membership Plans & POS Discount (`ts_membership_pos_discount`)

Reusable Odoo 19 module: membership plans with a spend threshold and an automatic
POS discount line for members.

## How it works
1. **Point of Sale > Memberships > Membership Plans**: create a plan with a
   *Discount (%)* and a *Minimum Spend per Session* (e.g. 300).
2. **Members / Customer Memberships** (or the *Memberships* tab on the customer):
   enrol a customer in a plan. The end date is computed from the plan duration;
   a daily cron marks ended memberships as Expired.
3. In the **POS**, once the order's *services* (products with Product Type
   "Service") reach the minimum spend, a separate last line of the Services
   section named after the plan (e.g. "Gold") is added with the discount. It is
   recomputed when lines, quantities or the customer change. Products are never
   discounted by it.
4. The order list is grouped into **Services / Products / Tips**.
5. **Settings > Point of Sale > Global Discounts**: *Discount Button on Services
   Only* limits the POS Discount button (`pos_discount`) to services.

## Notes
- Depends on `point_of_sale` and `pos_discount`.
- The discount product is `Membership Discount` (code `TS_MEMBER_DISC`, created on install).
- Do not install it next to `salon_spa_scheduler` on the same POS: that module
  ships its own copy of this feature (different models) and both would add a discount line.
