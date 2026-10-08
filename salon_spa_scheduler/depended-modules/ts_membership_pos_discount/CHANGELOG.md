# Changelog - Membership Plans & POS Discount (ts_membership_pos_discount)

## [19.0.1.0.0] - 2026-09-21
### Added
- Membership plans (`ts.membership.plan`): tier, duration, price, discount %,
  **minimum spend per session**.
- Customer memberships (`ts.membership`) with start/end date (end date computed
  from the plan duration), Active / Expired / Cancelled state and a daily cron
  that expires ended memberships; Memberships tab on the customer; Members list.
- POS: when the customer has an active membership and the services of the order
  reach the plan's minimum spend, a separate discount line named after the plan
  is added (product "Membership Discount"), recomputed on every order change.
  Products are not discounted.
- POS order list grouped into Services / Products / Tips sections.
- POS setting "Discount Button on Services Only" for the global Discount
  button (`pos_discount`).
- A product counts as a service when its Product Type is "Service".
