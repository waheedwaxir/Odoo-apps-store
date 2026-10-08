# Changelog - Salon & Spa Management (salon_spa_scheduler)

## [19.0.1.79.0] - 2026-09-30
### Changed
- **General Notes popup shows once, when the booking is made.** With "Warn
  About General Notes" on, it pops up when the customer is picked on a
  booking, and no longer again every time that booking is opened - including
  right after it was created, when going back to it from the scheduler. On
  an existing booking the notes are on the General Notes tab and behind the
  red "i" on the scheduler.

## [19.0.1.78.0] - 2026-09-30
### Fixed
- **POS Sales Details report showed "0 discounts"** on a day with
  membership discounts: Odoo only counts a % taken off a line, and the
  membership discount is a line of its own. The Discounts section now lists
  each kind with how many and how much - each membership plan by name
  (e.g. "Gold Member 4 x 120.00"), the global discount (pos_discount) and
  "Discount on lines" (% off at the till) - and the total underneath. Same
  report from the POS (Daily Sales) and from Reporting.
### Added
- **Tips on the POS Sales Details report**: a Tips section after Discounts,
  one row per beautician - how many tips and how much - and the total.
### Changed
- **Dashboard cards: the icon is a small badge in the top-right corner**
  instead of a large block on the left, so the figures and their breakdown
  get the card's full width.

## [19.0.1.77.0] - 2026-09-29
### Changed
- **Dashboard money cards reorganised.** "Booked Financials" and "Payments
  Status" (which only added up to each other) became two cards:
  - **Collected** - what actually came in (Sales History, as the old
    "Paid"), split into Services, Products, Discounts (the membership
    discount line) and, when there is any, Other (misc items imported from
    Shortcuts). A click opens those Sales History lines.
  - **To Collect** - what is not paid yet (as the old "Unpaid"), split into
    **Done, not paid** (finished but nobody took the money - highlighted,
    to act on) and **Upcoming** (Confirmed / In Progress), each with its
    number of bookings and a click to open them; the old total
    (collected + to collect) is the "Expected total" line underneath.
- **Avg. Ticket Value moved into the first row**, after Booked Services.

## [19.0.1.76.0] - 2026-09-29
### Changed
- **Dashboard: "Ongoing Sessions" replaced by "Booked Services".** It counts
  the services in the period's bookings, not the bookings - a booking with
  four services counts four - the way the bookings charge them: every
  service, Additional Services, and a service done twice counted twice.
  Cancelled bookings don't count. Underneath: how many are done and how
  many still to do. In Progress bookings still show in the status
  breakdown further down.
- **"Completed Services" renamed "Completed Bookings"** - it always counted
  Done bookings, not services (those are on Booked Services now). Its
  completion rate leaves cancelled bookings out: Done out of the bookings
  that are not cancelled (e.g. 6 of 7 = 86%, not 6 of 8 = 75%).

## [19.0.1.75.0] - 2026-09-29
### Added
- **Members and Membership Plans in Point of Sale > Configuration**, under
  their own "Memberships" heading, as well as under Salon & Spa > Configuration >
  Memberships & Loyalty. Same lists, same access rights.

## [19.0.1.74.0] - 2026-09-29
### Added
- **Edit Bookings After Start** (Settings, off by default). The Beauticians
  & Services lines of a booking are now editable until it starts - Draft
  and Confirmed (they used to lock once Confirmed). With the setting on, a
  Salon manager can also edit them In Progress and Done, until the booking
  is paid: beautician, service, start time, duration, price, notes, add or
  remove lines. On a Done booking the booking follows its lines - Main
  Beauticians, and Services (a service swapped or removed in the table is
  no longer billed; Additional Services lines still bill on their own) - a
  beautician change is logged in the chatter, and the Sales History and
  commissions are rewritten. A booking imported from Shortcuts keeps its
  imported Sales History (what was really charged); only its rows move to
  the beautician now on the line. Without the setting, or once paid, a Done
  booking stays locked (form and scheduler).
- **Done bookings on the scheduler** follow the same rule: with the setting
  on, a manager can drag an unpaid Done booking to another time or
  beautician and resize it (e.g. finished early, to free the slot); its
  Sales History follows (date, beautician). Without the setting the board
  refuses the move with a message - before, a Done booking could be moved
  in time without the Sales History following.
- **Completed on the scheduler asks first**: "Are you sure everything was
  done as per the order list - the services and the beauticians who did
  them?". Only Yes marks the booking completed.

### Changed
- **Start Time of each Beauticians & Services line can be typed in
  directly.** It used to be editable only after switching the line's Timing
  to Manual Time by hand; changing it now switches the line to Manual Time
  itself, so it keeps the typed time.

## [19.0.1.73.0] - 2026-09-29
### Fixed
- **POS payment failed with `'bool' object has no attribute 'id'`** (since
  19.0.1.68.0) on any order with a line nobody sells - the membership
  discount line, or a tip with no beautician. Writing the Sales History,
  the staff fallback for those lines was `False` instead of an empty
  `salon.staff` recordset, so `.id` blew up and the order could not be paid.
- **Tips from the till never kept their beautician.** The Tip button passed
  the beautician under an `extras` key that Odoo 19 ignores, so every tip
  line was saved without one: no `salon.staff.tip` was created and the tip
  did not reach the beautician. The beautician now goes on the line itself,
  picked from the beauticians loaded in the POS. Tip lines also never merge
  with each other, so a tip split 10 + 10 stays two lines. In the Sales
  History a tip line now names the beautician it is for, not the cashier.
### Changed
- **A staff tip line at the till shows who it is for**, the beautician's
  name under the line, like a service shows its beautician.
- **Beautician form: "Unpaid Tips" became "Tips".** The button shows the
  total of every tip given to that beautician at the till and opens all of
  them, paid and unpaid; the Unpaid / Paid filters and a Date filter narrow
  the list. Selected tips can be marked Paid / Unpaid from the list.

## [19.0.1.72.0] - 2026-09-29
### Changed
- **Apps Store page (`static/description/index.html`) brought up to date**
  with the features added since the first release: new sections for the
  scheduler booking popup and visit flow, Time Blocks, Beautician Targets /
  Monthly Incentives / commissions, the salon POS extensions (beautician per
  line, membership discount line, sections, services written back) and the
  Sales History ledger with the customer tools; 20 more checklist items;
  new workflow bullets; a Salon & POS settings table; updated screenshot
  captions for the Reports and Configuration menus, the booking and the
  beautician forms.
### Fixed
- The page promised SMS reminders, loyalty reward points, recurring
  subscriptions and an "expired draft cleanup" job, none of which the module
  has. The scheduled actions are now listed as they are: the 30-minute email
  reminder (every 5 minutes) and the monthly beautician incentives.

## [19.0.1.71.0] - 2026-09-28
### Changed
- The Add Service window shows the picked service's **Price** (its list
  price, what the added service is charged at).

## [19.0.1.70.0] - 2026-09-28
### Changed
- **Add Service on a draft booking.** The scheduler popup offers Add Service
  on a Draft booking too, always; on a Confirmed or In Progress one as
  before, when "Add Services to Started Appointments" is on. Done and
  Cancelled bookings take no more services.

## [19.0.1.69.0] - 2026-09-28
### Added
- **A note per beautician on a booking.** Each Beauticians & Services line
  has its own **Note** (new column on the booking form). In the scheduler
  popup every line has a small note icon to add or edit that beautician's
  note, and the note shows under the line. The note icon on a beautician's
  block on the board opens their own note together with the booking's note.
  The booking's note stays for the whole visit. Notes of a Done or Cancelled
  booking cannot be changed from the scheduler.

## [19.0.1.68.0] - 2026-09-28
### Added
- **Retail sales per person in the POS.** Tapping a retail product (shampoo
  and so on) asks who sells it, like a service: any beautician, or
  **Default - <cashier>**, which leaves the sale with the employee logged in
  at the till. The Beautician button in the "more" menu offers Default too.
  The staff tip and the membership discount do not ask.
- The Sales History credits a retail line to the beautician picked for it,
  else to the cashier: named after the employee logged in at the till (POS
  employee login), and linked to them as beautician when that employee is
  one - so it counts in their Earned. Retail sold on a booking's order is no
  longer put on the booking's main beautician. Commissions stay services
  only.

## [19.0.1.67.0] - 2026-09-28
### Added
- **Beauticians / Staff has a search view**: search by name, position,
  service category or phone; filters **Archived** and **Active and
  Archived** (archived beauticians could not be found before); group by
  Branch or Position.

## [19.0.1.66.0] - 2026-09-28
### Changed
- The scheduler popup's "Mark Arrived" button reads just **Arrived**, with an
  empty checkbox to tick.

## [19.0.1.65.0] - 2026-09-28
### Changed
- **Membership Number is the customer's.** The number is the corporate ID a
  customer shows for a scheme discount (an employee number at Qatar Airways,
  Qatar University, Hamad Hospital...), so it lives on the customer:
  **Membership Number** (`res.partner.salon_membership_number`), shown with
  the other salon fields on the General Notes tab, carried over from
  Shortcuts by the import. A membership shows and edits it
  (`salon.membership.line.membership_number`, related, stored).
  - Members lists it, and it is searchable in Customers, Members and the
    customer memberships (new search view).
  - Replaces 19.0.1.64.0's per-membership "Membership No." (and its "unique
    within a plan" rule); numbers typed there are moved to the customer on
    upgrade.

## [19.0.1.64.0] - 2026-09-28
### Added
- **Membership number.** A customer's membership has a **Membership No.**
  (card or ID number), typed on the customer's Customer Membership tab or on
  the membership itself; unique within a plan. Members lists it next to the
  plan ("Hamad Hospital #12345"), and customers can be searched by it - in
  Members (the Member search looks there too) and in Customers ("Membership
  No."). Shortcuts exports carry no membership number, so imported
  memberships start without one.

## [19.0.1.63.0] - 2026-09-28
### Added
- **Services added at the till are written back into the booking.** When a
  booking's POS order is paid, every service charged on it that the booking
  did not have becomes an Additional Services line (at the price charged, for
  the beautician picked on the POS line) and a line at the end of
  Beauticians & Services, with a note in the booking's chatter. It works for
  a booking already Done (paid later) as well as one In Progress. The work
  is done and paid, so shift, block and overlap checks do not apply; if the
  write-back still fails, the payment goes through and the booking gets a
  note instead. Subtotal, Sales History and commissions include it.
  - On upgrade, bookings already paid get the services added at their till
    (and their Sales History / commissions rewritten).

## [19.0.1.62.0] - 2026-09-28
### Changed
- **What a beautician does is picked by service category.** On the
  beautician: **Service Categories** (every service in them) and **Extra
  Services** (single services besides); nothing picked means every service.
  The old Allowed Services are kept as the Extra Services. This replaces
  19.0.1.61.0's "reserved service" rule: it is all decided on the beautician
  again. Used by the POS beautician picker, the services offered on booking
  lines and for the Main Beauticians, and the automatic choice of beautician
  for a booked service; a service's Beauticians column counts categories too.

## [19.0.1.61.0] - 2026-09-28
### Changed
- **A service in a beautician's Allowed Services is reserved for them.**
  Before, a beautician with no Allowed Services could do everything, so
  giving Natasa "Nail Polish - Feet" did not keep the others from it. Now:
  - a beautician with Allowed Services does only those (as before);
  - a service that is in someone's Allowed Services is offered only for the
    beauticians who have it;
  - a beautician with none set does every service not reserved that way.
  It applies to the POS beautician picker, to the services offered on a
  Beauticians & Services / Additional Services line and for the booking's
  Main Beauticians, and to which beautician a booked service is given
  automatically. A service's form lists its beauticians (Beauticians).

## [19.0.1.60.0] - 2026-09-28
### Changed
- **POS beautician picker lists only who may do the service.** A beautician
  with Allowed Services set is offered only for those services; one with none
  set is offered for every service (as on the scheduler). If nobody is set up
  for a service, everyone is offered rather than nobody. The POS loads, per
  beautician, the POS products of their allowed services
  (`pos_service_product_ids`).

## [19.0.1.59.0] - 2026-09-28
### Changed
- **POS: tapping a service asks for the beautician.** Adding a salon service
  on the product screen opens the beautician picker straight away; each tap
  on a service is its own line (they no longer merge into quantity 2), so the
  same service can be done by two beauticians. Cancelling leaves the line
  without one.
- The **Beautician** button left the main button row, where it squeezed the
  customer's name; it stays in the "more" menu to change the beautician of
  the selected line.

## [19.0.1.58.0] - 2026-09-28
### Changed
- **In Progress has its own colour: purple.** Arrived and In Progress were
  both blue; blue is now Arrived (not started yet) only. The scheduler
  legend has an "In Progress" entry (it filters like the others), and the
  appointment kanban cards follow.

## [19.0.1.57.0] - 2026-09-28
### Added
- **Beautician button in the POS.** Select an order line - e.g. a service
  added at the till, whether the booking is in progress or already done -
  press **Beautician** (next to Tip Staff, and in the "more" menu) and pick
  who does it; the name shows under the line and prints on the receipt.
  Once paid, the Sales History and commissions credit that beautician, for
  a line added to a booking's order as well as for a sale without a booking.
  It is not a tip: no tip is created for it.
  - The POS now loads the branch's active beauticians (`salon.staff` joins
    the POS data), so the line keeps a real link to the beautician
    (`salon_beautician_id`), not only a name.
### Changed
- A Done booking that is not paid yet shows a red **Not Paid** badge next to
  Done at the top of the scheduler popup.
- Booking cards on the scheduler no longer show the status label (the card's
  colour is the status), Arrived or a Mark Arrived button (arrival is handled
  in the popup); they show **Paid**, or a red **Not Paid** on a Done booking
  still to be paid.

## [19.0.1.56.0] - 2026-09-28
### Added
- **Completed on the scheduler marks the booking Done.** The booking popup of
  an In Progress booking offers **Completed** (green): the work is finished,
  the booking goes to Done (Sales History and commissions are written, and
  rewritten from the till once paid). Checkout is offered from then on - now,
  or on a later visit when the client pays later. Flow: Confirm -> Mark
  Arrived -> Start -> Completed -> Checkout. A Done booking takes no more
  services (Add Service is only offered while Confirmed or In Progress).
  - Checkout is offered for Done, unpaid bookings only; the server refuses a
    board Checkout before Completed. The company's "Allow Done Without POS
    Payment" no longer gates the scheduler's Checkout.
  - Send to POS on the appointment form stays available while In Progress
    or Done and unpaid.
### Changed
- The top of the booking popup shows only the latest status: Draft,
  Confirmed, Arrived, In Progress, Done or Paid (or Cancelled).

## [19.0.1.55.0] - 2026-09-28
### Fixed
- **Send to POS disappeared from the appointment once it had a POS order**,
  even an unpaid one. It now stays until the order is paid: with an unpaid
  order it opens that order at the till, adding the services missing from it
  (as the scheduler's Checkout does); without one it creates the order as
  before.
- **A booking whose POS order was cancelled could not be checked out again.**
  Closing a POS session cancels its unpaid orders; the booking kept pointing
  at the cancelled order, which counted as settled, so Send to POS and the
  scheduler's Checkout were gone. A cancelled order is now unlinked from its
  booking, which can then be sent to the POS again (a new order). On upgrade
  bookings linked to a cancelled order are unlinked.

## [19.0.1.54.0] - 2026-09-28
### Fixed
- **A booking reset to Draft still showed as Arrived on the scheduler.**
  Reset to Draft changed the state but kept the Arrived mark, and the board
  colours an arrived booking blue whatever its state. Putting a booking back
  to Draft now clears Arrived too (arrival follows confirmation). On upgrade,
  draft bookings still marked Arrived are cleared.

## [19.0.1.53.0] - 2026-09-28
### Fixed
- **A service added only in the Beauticians & Services table was not
  charged.** Checkout billed the booking's Services and Additional Services
  lines; a further service typed into the table (e.g. Balayage for Helen), or
  the same service again for another beautician, never reached the POS, the
  subtotal or the Sales History. Charging now follows the table: every
  service in it is one POS line with its beautician - a service built from
  several steps once per run of its steps, not once per step - with nothing
  charged twice (Services and Additional Services lines count as the first
  runs; an Additional Services line keeps its own price).
  - Subtotal / Estimated Cost, checkout, the Sales History written from the
    paid order and the commissions from it all use the same list.
  - A service done twice is matched to its two beauticians in turn when the
    paid order is written to Sales History.
  - **Checkout of a booking whose POS order is already open** adds the
    services missing from that order (one line each, with the beautician and
    the membership discount redone); lines already on it, and anything the
    till added, stay.
  - On upgrade the subtotal of open bookings is recomputed; finished and
    imported bookings keep theirs.

## [19.0.1.52.0] - 2026-09-27
### Changed
- **Reports menu in sections, with the Dashboard inside it.** The Dashboard
  left the top bar: **Reports > Overview** has Dashboard and Sales History,
  **Reports > Printed Reports** has Client Report, Employee Performance
  Report and Sales & Appointments Report (alphabetical inside each).
### Fixed
- Odoo warned "Two fields (salon_staff_count, salon_staff_ids) of hr.job()
  have the same label: Beauticians" on every start. The count is now
  labelled "Number of Beauticians".

## [19.0.1.51.0] - 2026-09-27
### Added
- **Targets per Position.** Job Positions (`hr.job`, the same ones as in
  Employees) carry the monthly Target 1 / Target 1 % and Target 2 /
  Target 2 %. **Configuration > Positions** (managers) lists them with their
  targets, typed straight in, and how many beauticians hold each.
- A beautician has a **Position**, taken from their employee's Job Position
  (or picked on the beautician / in Beautician Targets). Their targets are
  filled from it; they can still be changed for that one beautician.
  Changing a Position's targets updates every beautician in it.
- Beauticians linked from Employees (Import from Employees) bring their
  employee's Job Position.
### Changed
- The free-text Job Title on the beautician is replaced by Position on the
  form and list. On upgrade a beautician whose employee has no Job Position
  but who had a Job Title text gets the Job Position of that name (created
  without targets when missing); their own targets are kept.
- The Employee Performance Report shows the Position as the role.
- The Configuration menu is grouped into sections, alphabetical inside each:
  Settings, then **Salon** (Block Types, Branches, Chairs, Time Block
  History), **Services** (Packages, Service Categories, Services), **Staff**
  (Beautician Targets, Beauticians / Staff, Positions, Shifts), **Commissions
  & Tips** (Commissions, Staff Tips), **Customers** (Duplicate Customers,
  Reviews), **Memberships & Loyalty** (Members, Membership Plans), and last
  Data Migration / Sample Data from their own modules.

## [19.0.1.50.0] - 2026-09-27
### Added
- **Monthly incentives go into Commissions.** On the 1st of every month a
  scheduled action ("Salon & Spa: Monthly Beautician Incentives") works out
  last month's incentive of every active beautician with a target, per branch
  in the branch's timezone, and records it in Commissions as a **Monthly
  Incentive** (Draft, dated the month's last day, with the month, the service
  sales and the % it was worked out on). Paid like any other commission.
  - Nothing is recorded for a beautician below Target 1.
  - **Create Last Month's Incentives** on Beautician Targets does the same
    on demand (for the selected beauticians, or all with a target). Running
    it again recalculates that month's draft incentives; paid ones are left
    alone.
  - Commissions has a Type (Service / Monthly Incentive), the incentive's
    Month, Service Sales and %, and a search view: Monthly Incentives /
    Service Commissions, Draft / Paid, group by Beautician, Type or Month.
  - Existing commissions are of type Service.

## [19.0.1.49.0] - 2026-09-27
### Added
- **Monthly targets per beautician.** Target 1 and Target 2 on the month's
  service sales, each with its incentive % (5 % and 10 % by default, as on
  the salon's incentive sheet): past Target 1 the beautician earns Target 1 %
  of the month's services, past Target 2 the Target 2 % instead.
  - **Configuration > Beautician Targets** (managers): every active
    beautician in one list, targets typed straight in, with this month's
    service sales, % of Target 1, the incentive % reached and the amount -
    totals at the bottom.
  - A **Targets** tab on the beautician with the same.
  - The month's sales come from Sales History (services, net of discounts,
    cancellations left out), credited per beautician as since 19.0.1.44.0.
    Target 2 cannot be below Target 1.

## [19.0.1.48.0] - 2026-09-27
### Added
- **Last Session on the beautician.** A smart button next to Earned Today with
  what the beautician's services brought in during the branch's latest POS
  session (the open one, if there is one); it opens those Sales History
  lines. Hidden while the branch has never had a POS session.
- The Earned Today smart button is labelled just "Earned" (still today's
  total; it opens on the Today filter).
- **POS Session on Sales History** (`pos_session_id`, stored): the till
  session a booking was paid in. Searchable, groupable ("POS Session") and
  an optional column. Filled for existing lines on upgrade.

## [19.0.1.47.0] - 2026-09-27
### Added
- **Earned Today on the beautician.** A smart button on the Staff form with
  what the beautician's services brought in today (Sales History, net of
  discounts, cancellations left out) - to check against the till at closing.
  It opens every Sales History line credited to them, filtered on Today;
  remove the filter to see all of them.
- **Today** filter in Sales History.

## [19.0.1.46.0] - 2026-09-27
### Changed
- In the scheduler's booking popup the "General Notes" label next to the
  customer's name is now a small red "!" icon, followed by a small yellow
  note icon when the booking has a booking note. Each opens its notes.
- The popup's Start Service button reads just "Start".
- Once a booking has a note, it is edited on the note itself in the popup
  (a yellow Edit button on Booking Notes, or a click on the note); the
  footer only offers Add Note while there is none.
- The booking note window (opened from the yellow note icon, on the popup or
  on a booking card) has an Edit Note button.
- A booking note can no longer be added or edited from the scheduler once the
  booking is Done or Cancelled (it stays readable); the server refuses it too.
- Add Note left the popup's button row: a booking without a note shows a
  faded yellow note icon with a small "+" next to the customer's name; click
  it to add one. With a note it is the full yellow icon, as before.
- All of a booking's statuses sit together at the top of the popup, left of
  the close X: its state (Draft, Confirmed, In Progress, Done, Cancelled),
  Arrived and Paid. They left the cost line and the button row, which now
  holds only the next step and the other buttons.

## [19.0.1.45.0] - 2026-09-27
### Changed
- **Checkout on the scheduler only once the service has started.** The
  booking popup now goes one step at a time: **Confirm** (draft) -> **Mark
  Arrived** -> **Start Service** (new, blue; puts the booking In Progress) ->
  **Checkout**. A confirmed booking no longer offers Checkout, even when the
  customer has arrived; the server refuses it too. Done-but-unpaid bookings
  keep Checkout when the company allows finishing unpaid, as before.
### Fixed
- The popup's Arrived / Mark Arrived had disappeared once Add Note was added
  (19.0.1.43.0); the steps above show again.

## [19.0.1.44.0] - 2026-09-27
### Fixed
- **Sales History and commissions credited the wrong beautician.** A
  booking's services were all put on its main beautician, whoever the
  Beauticians & Services table said did them - two beauticians on one
  booking, or a beautician changed only in the table, went to the first one.
  Each service is now credited to the beautician on its Beauticians &
  Services line (the main beautician when that line has none), in the Sales
  History written at checkout and in the commissions worked out from it.
  Additional Services lines keep their own beautician, as before.
### Added
- **Beautician on POS Lines** (POS settings, per POS, off by default). A
  booking checked out to that POS carries on each service line the
  beautician who does it, shown under the line on the POS screen and on the
  receipt; the Sales History then takes the beautician from the till.
  It is a new field on the POS line (`salon_beautician_id` /
  `salon_beautician_name`), apart from the staff field that marks a line as
  a tip, so no tip is created for it.

## [19.0.1.43.0] - 2026-09-26
### Added
- **Add Note in the scheduler's booking popup.** Opens a small editor for the
  booking's own note (the one behind the note icon on the card, and in
  Booking Notes); Edit Note when there is one already. Not offered on a
  cancelled booking. The button is yellow, like a sticky note.
- The popup's Confirm button is green, the colour of a confirmed booking.

## [19.0.1.42.0] - 2026-09-26
### Added
- **Status legend on the scheduler filters the board.** Click Booking,
  Confirmed, Not confirmed, Arrived, Completed or Cancelled to highlight
  those bookings; several can be on at once, click again to switch one off.
  Bookings of other statuses fade rather than disappear, so their time still
  shows as taken; time blocks never fade. The choice is remembered in that
  browser, across days. A status switched on keeps its size, so the legend
  stays on its line.

## [19.0.1.41.0] - 2026-09-26
### Changed
- The General Notes mark on a booking card on the scheduler is a red "i"
  instead of a blue "G", matching the red sign in the booking popup.

## [19.0.1.40.0] - 2026-09-26
### Changed
- **Comments about a customer instead of an editable note history.** The
  customer's General Notes tab (and the booking's) has a **Comments** list:
  date, who wrote it, type (Complaint, Rude / Behaviour, Did Not Pay, Other)
  and the comment - for what happened with the customer, not for allergies
  or preferences. A saved comment stays as written (managers can delete one).
  Adding a comment no longer changes Allergy Information / Customer
  Preferences, as 19.0.1.36.0 had it do.
- The General Notes popup and the scheduler's red sign now also count
  comments: they show allergies, preferences and the five latest comments
  (with a line saying how many older ones there are).
- Changes to Allergies / Preferences are still logged, but that log is no
  longer shown on the customer.
- The General Notes popup opens with "This customer has General Notes - see
  the General Notes tab." above the notes.

## [19.0.1.39.0] - 2026-09-26
### Changed
- **Red General Notes sign in the scheduler's booking popup.** Next to the
  customer's name, shown only when the customer has General Notes
  (allergies / preferences); clicking it opens them. It replaces the notes
  text that used to be printed inside the popup.

## [19.0.1.38.0] - 2026-09-26
### Changed
- **Checkout on the scheduler only once the customer has arrived.** A
  confirmed booking shows Checkout after Mark Arrived; an In Progress (or
  Done-unpaid) booking keeps it, since the customer is there. The server
  refuses a board checkout of a confirmed booking not marked Arrived.

## [19.0.1.37.0] - 2026-09-26
### Changed
- **Confirm before Arrived on the scheduler.** The booking popup of a draft
  booking shows **Confirm** instead of Mark Arrived; once confirmed it shows
  Mark Arrived. The booking card on the board no longer offers Mark Arrived on
  a draft booking, and the server refuses it with "Confirm ... before marking
  the customer as arrived."

## [19.0.1.36.0] - 2026-09-26
### Added
- **Add notes in the customer's Note History.** The list on the customer's
  General Notes tab has "Add a line": date, the user, allergies and/or
  preferences. What is filled in becomes the customer's current Allergy
  Information / Customer Preferences, so the booking tab and the General Notes
  popup show it. Saved entries stay as they were written (managers can still
  delete one).
### Fixed
- **Editing Allergy Information or Customer Preferences on the customer form
  left no history.** Only the scheduler logged changes. Every change is now
  logged, wherever it is made - customer form, scheduler or booking - and
  once only.
- Editing one of the two notes on a booking's General Notes tab could reset
  the other one; each is now saved on its own.

## [19.0.1.35.0] - 2026-09-26
### Added
- **General Notes tab on the appointment.** The customer's Allergies /
  Medical Notes and Preferences / Styling Notes, right on the booking and
  editable there. A change is saved on the customer and logged in their note
  history, the same way the scheduler saves them; the history is listed under
  the notes.
- **General Notes warning** (Settings > Salon & Spa, off by default, per
  company). When on and the customer has General Notes, they pop up:
  - when the customer is picked on a booking;
  - when an existing booking is opened (not again after saving a new one).

## [19.0.1.34.0] - 2026-09-26
### Fixed
- **Service column empty on Beauticians & Services.** A service built from
  steps (as every imported service is) put its lines on the booking with the
  step name but no service, so the Service column stayed blank. Every line now
  carries the service that was booked - on the form, on create/write and when
  a service is added to a started appointment. Two services for one
  beautician are two lines, one under the other.
  - A one-step service whose step has the service's own name is just "X",
    not "X - X".
  - The Price column shows a service's price on its first line only, so a
    service with several steps is not counted once per step in the total.
    (Still for information: checkout bills the Additional Services lines.)
  - Existing bookings are filled in on upgrade: the service is matched by the
    line's name among the booking's services, then among the branch's
    services. On the local copy: 31 lines filled, 20 "X - X" names shortened,
    none left empty.
### Changed
- Every column on Beauticians & Services can be switched on and off from the
  column picker (Beautician, Required, Service, Duration, Timing, Start and
  End Time, as well as Step Name, Price and Need Staff?). Shown by default:
  Beautician, Required, Service and Start Time; the rest are a click away.

## [19.0.1.33.0] - 2026-09-23
### Fixed
- **Two branches on one scheduler.** The branch picker only filtered the
  bookings: every branch's beauticians kept their columns, and a slot clicked
  under Branch 2 created the booking in the company the user happened to be
  logged into - refused as a company crossover as soon as a Branch 2
  beautician was on it.
  - The board shows only the selected branch's beauticians
    (`scheduler_data` now sends each beautician's company).
  - A booking or time block made from the board belongs to the selected
    branch, or - with all branches shown - to the clicked beautician's.
- **Branch and Company on an appointment can no longer drift apart.** Setting
  either one sets the other, on the form and on create/write. The scheduler
  filters on Branch while the company checks on staff, services and chairs use
  Company, so a mismatch made bookings vanish or fail.
### Checked
- On a copy with a second company: per-company booking numbers, bookings and
  time blocks in Branch 2, Sales History and commissions in Branch 2's
  company, scheduler and dashboard figures per selected branch, a Branch 1
  user unable to see Branch 2's bookings, services or staff, and a Branch 1
  beautician refused on a Branch 2 booking.

## [19.0.1.32.0] - 2026-09-23
### Added
- **Arabic section titles on the POS and the receipt.** New POS setting
  **Arabic Section Titles** (`pos.config.salon_arabic_sections`, off by
  default, under Point of Sale settings next to "Discount Button on Services
  Only"). When on, the order's section headings show English on the left and
  Arabic on the right: Services / الخدمات, Products / المنتجات,
  Tips / البقشيش. The headings are drawn by `OrderDisplay`, which the printed
  receipt uses too, so the receipt carries them as well.

## [19.0.1.31.0] - 2026-09-23
### Changed
- **Add Service after checkout.** An appointment already sent to the Point of
  Sale can still be extended while its POS order is unpaid: the service is
  added to the appointment as before and also put on that POS order, priced
  exactly as checkout prices it, and the membership discount line is
  recalculated for the new total of services. The chatter notes it, with a
  reminder to reopen the order at the till if it is already on screen there.
  Once the order is paid (or its session is closed) Add Service is refused
  with a clear message, as before.
- Checkout's POS line building is split into
  `_pos_service_line_commands` and `_pos_membership_line_command`, shared by
  checkout and Add Service. Checkout behaves as before.

## [19.0.1.30.0] - 2026-09-23
### Added
- **Configuration > Duplicate Customers** (Salon Managers). Groups customers
  that share a phone number - Phone or Other Phones, compared on the last
  eight digits so `+974 3023 6826` and `30236826` match - and opens them
  grouped for review. Nothing is merged automatically: a shared number can be
  two people (a sister booking for her sister). Tick the real duplicates and
  use Action > Merge. A shared name alone is not used - on the migrated data
  it is mostly different people. `res.partner.salon_duplicate_key` holds the
  grouping; `action_find_salon_duplicates` builds it.
- **Merging keeps every number.** `base.partner.merge.automatic.wizard` is
  extended so the numbers of the merged-away customers go to the survivor's
  Other Phones instead of being lost, and the duplicate marker is cleared.
- **Phone search ignores formatting.** New stored `salon_phone_search` (digits
  of Phone and Other Phones, trigram indexed). The scheduler's customer
  search, the customer field on forms (`name_search`) and the Contacts search
  ("Any Phone") use it, so typing `30236826` finds `+974 3023 6826`. The
  digits-only match kicks in from five digits, so a short name search is not
  flooded. The customer field on forms also searches Other Phones.

## [19.0.1.29.1] - 2026-09-23
### Fixed
- **Dashboard no longer slows down with every day of trading.**
  - The tips safety net ran `_create_staff_tips` over every paid POS order
    ever, on each opening. Tips are created when an order is paid; the safety
    net now only looks at the last 7 days and at orders with a tip line.
  - Revenue, beautician and service figures are summed in the database
    (`_read_group`) instead of loading every Sales History line; beautician
    counts, commissions and tips are gathered in one pass. On the migrated
    data "All Time" went from 1.4 s to 0.3 s, with identical figures.

## [19.0.1.29.0] - 2026-09-23
### Changed
- **Commissions follow the salon's rule**: earned on what was actually
  charged, per beautician, tips excluded. New
  `salon.appointment._sync_commissions()` builds them from the booking's Sales
  History instead of the price list:
  - every service line goes to the beautician on that line, so a booking done
    by several beauticians pays each one for their own work (it all went to
    the main beautician before), and services added with Add Service or as
    Additional Services now earn commission too;
  - percentage commissions are taken on the charged amount; the membership
    discount, booked by the till as one negative line for the whole order, is
    spread over the service lines in proportion to their price; fixed
    commissions stay a fixed amount per service line;
  - tips (Sundry lines) and retail products earn nothing;
  - one commission record per beautician per booking.
- Commissions are rebuilt when the POS order is paid, so an appointment closed
  before payment gets its commission corrected to what was really charged.
  Draft commissions are replaced; once any commission of a booking is marked
  Paid, that booking's commissions are left alone.

## [19.0.1.28.0] - 2026-09-23
### Fixed
- **Changing a price on an appointment rewrote the price list.** The price on
  an Additional Services line and on a Beauticians & Services step was a
  writable related field on the service's list price, so a special price for
  one customer became the new price for everyone.
  - `salon.appointment.line.price_unit` is now the line's own stored value,
    filled from the price list when the service is picked and free to change
    for that booking. A later price-list change does not rewrite existing
    bookings. Existing lines are filled from the current price list on
    upgrade.
  - Checkout bills the line's price. It used to take the price-list price, so
    a price changed on the line was never charged anyway.
  - The step price (`salon.appointment.step.price_unit`) is shown read-only:
    it is for information and is not what checkout bills.

## [19.0.1.27.2] - 2026-09-23
### Changed
- Dashboard period buttons run from the shortest to the longest: Today, This
  Week, This Month, Last 6 Months, Last Year, All Time. The dashboard opens on
  Today.

## [19.0.1.27.1] - 2026-09-23
### Fixed
- The dashboard would not open ("IndexError: list index out of range" in
  `call_kw`): 19.0.1.27.0 left `get_dashboard_data` without its `@api.model`
  decorator, so the call from the dashboard, which passes no record ids, was
  refused.

## [19.0.1.27.0] - 2026-09-23
### Fixed
- **Dashboard money now comes from Sales History**, i.e. what was actually
  charged, instead of list prices summed over appointments. On the migrated
  data the old figure was 1,509,575 against 912,178 really taken.
  - **Paid** = collected in the period (ledger, tips excluded). A booking
    finished without payment is not counted here.
  - **Unpaid** = confirmed / in-progress / done appointments whose money is
    not in yet. Appointments brought over from the previous system count as
    settled - previously every one of them (7,311) showed as unpaid.
  - **Total** = Paid + Unpaid ("Collected + still to be paid").
  - **Average value** = collected / completed appointments (it used to divide
    by every appointment, cancelled ones included).
  - **Beauticians**: revenue per line to whoever did the work (not all to the
    booking's main beautician); an appointment counts for every beautician on
    it.
  - **Top services**: count and revenue from the lines actually sold.
  - **Customer Ratings**: shows "No reviews yet" instead of 5.0 stars when
    there are none.
- Today / this week / this month now start at local midnight (user's time
  zone, Asia/Qatar by default) instead of UTC midnight.

## [19.0.1.26.0] - 2026-09-23
### Added
- **Other Phones on customers** (`res.partner.salon_other_phones`, trigram
  indexed). Odoo 19 has a single Phone per contact, so a customer's further
  numbers - home, work, a second mobile - go here. It sits under Phone on the
  contact form, and both the scheduler's customer search and the Contacts
  search look in it, so a customer is found by any of their numbers. The
  Contacts search field is anchored on Email, because `phone_validation`
  replaces the Phone field in that view.

## [19.0.1.25.0] - 2026-09-23
### Fixed
- **Duplicates left by an old copy of `salon_shortcuts_import`.** A database
  that loaded an out-of-date copy of the import module (19.0.1.0.2, from a
  folder earlier in the addons path) re-created the views, actions, menus and
  access rules that had moved here - Sales History and Service Categories
  appeared twice - and re-registered its external ids for the moved fields.
  The pre-migration (`migrations/19.0.1.25.0/pre-migrate.py`) deletes the
  import module's duplicate records, releases its external ids on the shared
  models, fields and selection values, and removes its old inherited views on
  the service form. A database without the old copy is left untouched.

## [19.0.1.24.3] - 2026-09-23
### Changed
- **Scheduler appointment popup footer tidied up.** Button labels no longer
  wrap onto two lines at uneven heights. The less frequent actions (Mark
  Arrived, Add Service, Rebook) sit on the left as smaller buttons; Checkout
  and Open Appointment sit on the right at a common height. When space runs
  out, whole buttons move to the next row. The popup is a little wider
  (640px) and the footer has its own light background. The block popup
  footer follows the same layout.

## [19.0.1.24.2] - 2026-09-23
### Fixed
- **Add Service** in the scheduler popup failed with "Cannot read properties
  of undefined (reading 'map')". `action_open_add_service` returned only
  `view_mode`; a form button gets `views` filled in by the server, but the
  scheduler passes the action straight to `doAction`, which needs `views`.
  The action now spells out `views`.

## [19.0.1.24.1] - 2026-09-23
### Fixed
- `salon.block.type`: the unique name-per-company rule used `_sql_constraints`,
  which Odoo 19 ignores ("Model attribute '_sql_constraints' is no longer
  supported") - the constraint was never created. It is now a
  `models.Constraint`, so duplicate block type names are refused again.

## [19.0.1.24.0] - 2026-09-23
### Added
- **Add a service to an appointment that has already started.** New setting
  **Add Services to Started Appointments** (Salon settings,
  `res.company.salon_allow_extend_started`, off by default). With it on, a
  confirmed or in-progress appointment gets an **Add Service** button on its
  form and in the scheduler popup.
  - A small dialog (`salon.appointment.add.service`) asks for the service,
    the beautician, the length, and whether it runs after the last service
    (the booking gets longer) or at the same time (a second beautician).
  - The extra service is added as an **Additional Services** line, so
    checkout charges it, and as new steps at the end of the step list, so the
    scheduler shows the longer booking. Existing steps are not touched. A
    service with its own step template keeps its steps, scaled to the length
    entered.
  - The usual overlap, shift and time block checks decide whether the
    beautician is free; a fixed Duration on the appointment is cleared so the
    new step is not squeezed into the old end time. The chatter records what
    was added and the new end time.
  - Not offered once the appointment has been sent to the Point of Sale: the
    service then has to be added on the POS order so it is charged.
  - Server methods `_add_extra_service`, `action_open_add_service`,
    `scheduler_open_add_service`; scheduler cards carry `can_add_service`.

## [19.0.1.23.1] - 2026-09-23
### Fixed
- **Customers menu opens again.** Sales History sat under Customers, and a
  menu with children in Odoo is only a dropdown - the Customers list could no
  longer be reached from it. Sales History is now under **Reports > Sales
  History**, and Customers opens the customer list directly as before.

## [19.0.1.23.0] - 2026-09-23
### Added
- **Import guards on two constraints.** `_check_overlap` returns straight
  away under `skip_salon_overlap_check`, and `_check_cancellation_limit`
  under `skip_salon_cancellation_limit`. Two years of real history contain
  149 genuine technician overlaps and customers over the cancellation limit;
  live booking still validates as normal. Nothing else in either method
  changed.
- `res.partner.salon_first_visit_date` ("First Visit", carried over from the
  previous system), shown on the customer's **General Notes** tab next to the
  other salon fields.
### Changed
- Both guards and the field used to be added by `salon_shortcuts_import`
  (the guards as method overrides). The pre-migration
  (`migrations/19.0.1.23.0/pre-migrate.py`) hands the field's external ids
  over, so imported first-visit dates are kept.

## [19.0.1.22.0] - 2026-09-23
### Changed
- **Appointments paid through the POS write Sales History from the till.**
  New `salon.appointment._log_sale_history()`: when the appointment's POS order
  is paid, there is one history row per POS line instead of one per service at
  list price.
  - `price_unit` is what was actually charged (line total with tax).
  - A service line keeps its service and beautician; its gross is the price
    the checkout put on it, so a % discount shows as Discount and a price typed
    over at the till shows as Price Override.
  - The membership discount line becomes its own row (item type Other, the
    plan as Discount Reason), and retail added at the till is recorded against
    the appointment as Retail Product.
  - Not paid through the POS: one row per service at list price, as before.
- An appointment marked done **before** its POS order was paid now has its
  history rewritten from the POS lines once the order is paid.
- `_pos_line_vals` takes gross as the line's unit price x quantity with
  taxes (same result, no division by the discount).
- `_populate_history_if_empty` uses `_log_sale_history` for done appointments.

## [19.0.1.21.0] - 2026-09-23
### Changed
- **Live sales now fill the ledger fields too**, not just imported history.
  Every place that writes `salon.customer.history` goes through shared
  builders on the model (`_appointment_service_vals`, `_pos_line_vals`,
  `_payment_vals`, `_log_pos_order`), so the text columns and the ledger
  columns are always written together:
  - **Appointment done:** `service_id`, `staff_id`, `appointment_id`,
    `item_type` = service, quantity, gross = the price used, and from the
    linked POS order the sale reference and payment (Paid With, sale total,
    split payment).
  - **Appointment cancelled:** links to the appointment, beautician and (when
    there is one) the service; quantity and money stay 0.
  - **POS sale without an appointment:** product, service (when the product
    belongs to a salon service), item type (service / retail / tip as
    sundry / membership discount as other), quantity, gross before the line's
    % discount, discount amount, % and reason, cost of goods, tip beneficiary
    as `staff_id`, and payment details.
  - `_populate_history_if_empty` uses the same builders.
  Existing column meanings are unchanged: `price_unit` is still the amount
  used before (list price for appointment services, line total with tax for
  POS lines).
### Fixed
- History rows from POS orders created directly in the paid state had no
  company set explicitly; they now take the order's company.

## [19.0.1.20.0] - 2026-09-23
### Added
- **Sales History is a real ledger.** `salon.customer.history` stored names as
  text only - enough to show a customer what they had last time, useless for
  "how much did we take on Gel Polish in March and what did it cost us".
  Existing fields are unchanged: `service_name` and `staff_name` are still
  filled, and `price_unit` is still the NET amount actually charged.
  - Links: `service_id`, `category_id` (related, stored), `product_id`,
    `staff_id`, `appointment_id`; `item_type` (service / retail product /
    sundry-tip / package / other).
  - Money: `quantity`, `price_gross`, `discount_amount`, `discount_percent`,
    `discount_reason`, `cost_amount`, `block`, `sale_ref`.
  - Payment: `payment_method`, `payment_amount` (whole sale), `is_split_payment`.
  - Stored computes: `margin` = net - cost; `reduction_total` = gross - net;
    `price_override` = (gross - net) - discount, i.e. what was given away by
    typing a different price at the till.
  - List view with Net / Discount / Price Override totals (quantity, gross,
    cost and margin optional), search view with Services / Retail / Discounted
    / Price Overridden / Refunds filters, date filter and group-bys, and the
    menu **Customers > Sales History**.
### Changed
- All of the above moved here from `salon_shortcuts_import`. The
  pre-migration (`migrations/19.0.1.20.0/pre-migrate.py`) hands the external
  ids over, so the imported ledger is kept as it is.

## [19.0.1.19.0] - 2026-09-23
### Added
- **Processing breaks in multi-step services.** Dead time in the middle of a
  treatment - colour developing, a mask setting - where the chair is taken but
  the beautician is not. A break is an ordinary step with `need_staff = False`,
  flagged as such, so `_compute_step_times` is untouched and the service's
  total duration comes out right.
  - `salon.service.step.is_processing_break` ("Processing Time"); `create()`
    forces `need_staff = False` whenever it is set.
  - `salon.appointment.step.is_processing_break`.
  - **Processing** toggle in the service form's step list, before Need Staff.
### Changed
- Both fields and the toggle moved here from `salon_shortcuts_import`. The
  pre-migration (`migrations/19.0.1.19.0/pre-migrate.py`) hands the field
  external ids over, so imported flags are kept, and removes the import
  module's inherited service-form view.

## [19.0.1.18.0] - 2026-09-23
### Added
- **Service categories.** New model `salon.service.category` (name, code,
  sequence, parent/children, colour, active, service count via `_read_group`,
  `action_view_services`), so reports can group turnover by treatment type -
  Nails - Mani/Pedi, Hair Color, Waxing, Massage, Eyelash and so on.
  - `salon.service.category_id` (tracked, indexed, `ondelete='set null'`).
  - Editable category list with sequence handle and active toggle; form with a
    Services smart button, archived ribbon and colour picker.
  - Category shown on the service list (after the name, optional), form and
    search view, with a **Group By > Category** filter.
  - Menu **Configuration > Service Categories**.
### Changed
- The model, its views, menu, access rules and `salon.service.category_id`
  moved here from `salon_shortcuts_import`. The pre-migration
  (`migrations/19.0.1.18.0/pre-migrate.py`) hands their external ids over to
  this module, so existing categories and service links are kept, and removes
  the import module's three inherited views that used to show the field.

## [19.0.1.17.3] - 2026-09-23
### Fixed
- **Remove Block** opened its confirmation underneath the block popup, so the
  two overlapped and the confirmation could not be used. The popup now closes
  first and the confirmation shows on its own.

## [19.0.1.17.2] - 2026-09-23
### Changed
- **Type the block's length.** The block chooser (right-click on an empty slot)
  now has free **h** and **min** fields instead of a fixed list of durations.
  The cursor is already in the hours field when it opens, so you type the
  length and click the type. Leave both empty for the type's usual length.

## [19.0.1.17.1] - 2026-09-23
### Changed
- **Right-click makes a block.** A left click on an empty slot opens a new
  appointment straight away again, as before 19.0.1.17.0. Right-clicking an
  empty slot opens the block type chooser (with the duration picker). It works
  outside the shift too, and the "Outside shift" warning now says so.
  Right-clicking an existing card does nothing.

## [19.0.1.17.0] - 2026-09-23
### Changed
- **Time blocks live on the scheduler.** There is no separate calendar any more.
  - Clicking an empty slot opens a small chooser: **New Appointment**, or one
    click on a block type to block that time for that beautician (duration
    defaults to the type, or pick 15 min - 8 h). Outside a beautician's shift
    only a block can be placed; duty at another branch is exactly that case.
  - Block cards have their own look (hatched, dashed border) and show the
    title, time range and note - no customer, badges or Mark Arrived.
  - A click on a block opens a block popup (type, time, beautician, Working At,
    notes) with **Edit Block** and **Remove Block**; the board refreshes when
    the edit dialog closes.
  - Blocks can be resized by dragging the bottom edge
    (`salon.appointment.scheduler_resize_block`) and removed from the popup
    (`scheduler_cancel_block`), besides being dragged as before.
  - A block created while a branch is selected on the board belongs to that
    branch; a type with a Works At Branch fills it in.
- The block calendar view and the top-level **Time Blocks** menu are removed.
  The list stays as **Configuration > Time Block History**; the Blocks smart
  buttons open list and form only.

## [19.0.1.16.1] - 2026-09-23
### Fixed
- Upgrade failed with `Field "works_at_branch_id" does not exist in model
  "salon.block.type"`. The Block Type list and form views now use the type's own
  field, `target_branch_id` (`works_at_branch_id` belongs to `salon.block`).

## [19.0.1.16.0] - 2026-09-23
### Added
- **Time Blocks.** Not every hour of a beautician's day is a customer:
  training, a staff meeting, a photoshoot, a day on duty at another branch, a
  stretch marked "do not book". None of it could be recorded before, because a
  booking requires both a customer and a service.
  - New model `salon.block.type` - the policy behind a block: colour, usual
    length, category (block / duty / training / meeting / break / absence),
    whether it prevents booking, whether it publishes a Planning shift, whether
    it raises Time Off, and which branch the beautician is working at when the
    block means duty elsewhere. Seven sensible types ship with the module.
  - New model `salon.block` - the blocks themselves, against a beautician and a
    time range. Calendar, list and form views under **Salon > Time Blocks**,
    configuration under **Salon > Configuration > Block Types**, and a Blocks
    smart button on the beautician form.
  - **Scheduler integration.** Blocks appear on the timeline beside bookings.
    Clicking or opening one opens the block; dragging one moves it through
    `salon.appointment.scheduler_move_block`; resizing is handled on the block
    form, since block lengths do not go through `scheduler_resize`.
  - **Booking protection.** A confirmed block whose type prevents booking now
    refuses an overlapping appointment (`_check_salon_block_clash`), with the
    same `skip_salon_overlap_check` escape hatch used by data migration.
  - **Planning bridge.** A block can publish itself as a `planning.slot`, so the
    shift gate already enforced in `_check_overlap` and drawn on the scheduler
    sees it without any further wiring.
  - **Time Off bridge.** An absence-type block raises an `hr.leave` against the
    linked employee. Allocation limits stay HR's business: if the request is
    refused the block is still recorded and the reason is posted to its chatter.
- New server methods `salon.appointment._scheduler_block_entries` and
  `salon.appointment.scheduler_move_block`; `scheduler_data` now also returns
  `block_types`, and its `appointments` list carries block cards flagged
  `is_block`.
- New dependency: `hr_holidays`.

## [19.0.1.15.0] - 2026-09-23
### Added
- **Checkout button in the scheduler's appointment popup.** Sends the booking
  to the Point of Sale (same lines, taxes and membership discount as the
  form's Send to POS) and opens the order in the POS screen. A Confirmed
  booking is moved to In Progress first, so paying the POS order marks it
  Done. If the booking already has an unpaid POS order, Checkout reopens
  that order instead of creating a second one.
  Shown only to users with "Create Payment" (or Manager) rights, for bookings
  that are Confirmed / In Progress (or Done when "Allow Done without payment"
  is on) and not yet paid. Needs an open POS session.
- New server method `salon.appointment.scheduler_checkout`; `scheduler_data`
  now returns `user_can_checkout` and a per-block `can_checkout` flag.

## [19.0.1.14.0] - 2026-09-23
### Added
- **Appointment info popup on the scheduler.** A single click on a booking
  now opens a small popup instead of the full form: customer name and phone,
  alert/general notes (allergies, preferences), booking notes, every service
  of the booking with its time and beautician (REQ when requested), estimated
  cost, status/paid, and Mark Arrived / Rebook / Open Appointment buttons.
  Click the name or Open Appointment (or double-click the block) to go to the
  full form; click outside or x to close.
- **Selected booking's time range is highlighted in the time column.** While
  a booking is selected, its rows in the left time column are marked, and the
  block itself gets an outline.
- `scheduler_data` now also returns each block's `amount` (appointment
  subtotal) for the popup.

## [19.0.1.13.4] - 2026-09-22
### Fixed
- **Scheduler grid could not be scrolled to the working day's last couple of
  rows** (e.g. hours set to 10:00-22:00 but 21:30/21:45 were unreachable).
  `.o_salon_scheduler` used `height: 100vh`, which ignores the Odoo top app
  bar above it, so the component's bottom edge sat below the visible
  viewport with nothing able to scroll to it. Changed to `height: 100%` (of
  the app bar-aware `.o_content` area). Same fix applied to the Dashboard
  (`salon_dashboard.scss`), which had the identical pattern.

## [19.0.1.13.3] - 2026-09-22
### Fixed
- **Scheduler jumped back to today after booking a future date.** Clicking a
  cell to book, then Save (or Discard) on the appointment form navigates away
  from and back to the scheduler client action, which recreated the component
  and reset its date to today. The last date navigated to (Previous/Next Day,
  date picker, Today) is now remembered in `sessionStorage` and restored on
  return, so the board stays on the date you booked for.

## [19.0.1.13.2] - 2026-09-22
### Fixed
- **Appointment Notes could only be edited while the appointment was still a
  Draft.** After Confirm (or later), the Notes tab became read-only. The
  `note` field is now always editable, at any appointment status.

## [19.0.1.13.1] - 2026-09-21
### Changed
- The POS **Discount button line** is now shown at the end of the **Services**
  section when "Discount Button on Services Only" is on; when it is off (discount
  on everything) it stays the last line of the order.

## [19.0.1.13.0] - 2026-09-21
### Added
- **POS setting "Discount Button on Services Only"** (Settings > Point of Sale,
  under Global Discounts; new field `pos.config.salon_discount_services_only`,
  default on). When on, the POS Discount button (`pos_discount`) discounts only
  salon services and leaves products untouched; untick it to discount services
  and products as before. The membership discount line is never re-discounted.
  The module now depends on `pos_discount` (installed automatically). Run
  `-u salon_spa_scheduler`.

## [19.0.1.12.2] - 2026-09-21
### Fixed
- **Retail products were treated as services** by the POS membership discount
  and the new Services/Products sections, so the discount also covered goods
  (e.g. "ANS Gel Polish") and no sections appeared. `is_a_salon` is set on
  almost every POS product, so services are now only the products linked to a
  Salon Service (`POS Products`).

## [19.0.1.12.1] - 2026-09-21
### Added
- **POS order lines are grouped into sections**: **Services** (salon service
  products, followed by the membership discount line), **Products**, and
  **Tips**. Section headers show only when the order mixes sections, in the
  order list, receipt and order history. Members get no discount on products,
  so this makes it clear what the discount covers.
  (`static/src/xml/salon_pos_sections.xml`, `pos_patch.js`)
- `get_pos_member_discount` now always returns `service_product_ids` and
  `tip_product_id`.

## [19.0.1.12.0] - 2026-09-21
### Changed
- **Membership discount is now a separate last order line**, named after the
  customer's membership plan (e.g. "Qatar Airways"), instead of a % on every
  service line. It is a negative line of the new product **Membership
  Discount** (`data/membership_discount_data.xml`), recomputed whenever the
  POS order changes and always kept last. Taxes follow the discounted services
  when they all share the same taxes. The line shows the plan name in the POS
  order list and on the receipt (product code `SALON_MEMBER_DISC`).
- **Send to POS from an appointment** now adds the same discount line when the
  customer has an active membership and the services reach the plan's minimum
  spend (`action_create_pos_order`).
- `get_pos_member_discount` always returns the discount product; `discount` is
  0 when there is no active membership. Run `-u salon_spa_scheduler`.

## [19.0.1.11.3] - 2026-09-21
### Changed
- POS membership discount logs a `[salon membership]` line to the browser
  console (partner, matched service lines, spend, qualifies) to make it easy
  to diagnose why a discount did or did not apply.

## [19.0.1.11.2] - 2026-09-21
### Fixed
- Membership discount still did not apply in the POS: the spend calculation
  called `getUnitPrice()`, which does not exist on Odoo 19 order lines, so it
  threw before the discount was set. It now uses `price_unit`.

## [19.0.1.11.1] - 2026-09-21
### Fixed
- **Membership discount never applied in the POS.** Services were detected only
  via the `is_a_salon` flag, which is off for the POS products linked to Salon
  Services. `get_pos_member_discount` now returns `service_product_ids` (products
  of all Salon Services + `is_a_salon` products) and the POS matches lines
  against that list. Lookup errors are logged to the browser console.

## [19.0.1.11.0] - 2026-09-21
### Added
- **Membership spend threshold.** New field `min_spend` ("Minimum Spend per
  Session") on Membership Plans. In the POS, when the customer has an active
  membership and the salon services (`is_a_salon` products) of the order reach
  `min_spend`, the plan's `discount_percentage` is applied to those service
  lines (e.g. 300 QAR -> discount). Products are not discounted; manual line
  discounts are never overwritten; the discount is removed again if the order
  drops below the threshold. `min_spend = 0` means no minimum.
  New `salon.membership.line.get_pos_member_discount`; `is_a_salon` is now
  loaded into the POS. Run `-u salon_spa_scheduler`.

## [19.0.1.10.4] - 2026-09-21
### Changed
- Scheduler cards: the red **REQ** badge (customer requested this beautician)
  is now a compact **R**, still red.
- Dragging a card whose service was requested by the customer now shows a
  warning popup ("Move anyway" / "Cancel"). The move is still allowed.
  (`static/src/js/salon_scheduler.js`, `static/src/xml/salon_scheduler.xml`)

## [19.0.1.10.1] - 2026-09-19
### Added
- **Dark mode for the scheduler.** `static/src/scss/salon_scheduler.dark.scss`
  (loaded via `web.assets_web_dark`) re-colours the grid, header, sidebar,
  search and customer modal when Odoo runs in dark mode. Appointment cards
  keep their status colours.

## [19.0.1.10.0] - 2026-09-19
### Added
- New setting **Cancelled Appointments** (Settings > Salon & Spa): when on,
  Salon Managers get a **Reset to Draft** button on cancelled appointments.
  `action_reset_draft` also enforces this server-side (manager group + setting).
  Adds `res.company.salon_allow_reset_cancelled` - run `-u salon_spa_scheduler`.

## [19.0.1.9.3] - 2026-09-19
### Fixed
- **Dashboard showed every amount in `$`** regardless of company currency:
  `formatMonetary` (`static/src/js/salon_dashboard.js`) hardcoded USD.
  `get_dashboard_data` now returns the current company's currency (symbol,
  position, decimals) and the dashboard formats amounts with it.

## [19.0.1.9.2] - 2026-09-18
### Fixed
- **Dragging one service step of a multi-step appointment moved every step
  together**, even when that step's Timing was set to Manual. `scheduler_move`
  (`models/salon_appointment.py`) always shifted the whole appointment's
  `start_datetime` by the drag delta - since every non-manual step's time is
  computed relative to that same anchor, they all slid along with it
  regardless of the dragged step's own Timing setting.
- Now only dragging the **first** step (which anchors the appointment) shifts
  the whole block, matching Timing's own "ignored for the first step"
  behavior. Dragging any other step pins that step exactly where it's
  dropped and switches it to **Manual Time** automatically - no need to set
  Manual by hand first. Each service can now be dragged independently to a
  different beautician and/or time by default; steps still chained
  sequentially after it re-anchor to its new position.

## [19.0.1.9.1] - 2026-09-18
### Changed
- **"Customers" menu now opens with the "Individuals" filter applied by
  default** - salon customers are (almost) never companies. New
  `action_salon_customers` (`views/menu_views.xml`), a copy of
  `contacts.action_contacts` with `search_default_type_person: 1` added to
  its context, replaces the shared Contacts action on `menu_salon_customers`
  so the real Contacts app menu/action is untouched.

## [19.0.1.9.0] - 2026-09-17
### Added
- **Dated history log for Allergies/Preferences notes**, so an older note
  isn't lost the next time someone overwrites the Allergies/Preferences
  textareas. New `salon.customer.note` model (`partner_id`, `date`,
  `user_id`, `allergies`, `preferences`), one entry per `Save Notes` click
  that actually changed something (`res.partner.action_update_salon_notes`,
  `models/res_partner.py`) - a no-op save doesn't spam the log.
- New `res.partner.salon_note_ids` One2many, shown as a read-only "Note
  History" list under Allergies & Preferences in the scheduler's Customer
  Profile modal (`static/src/js/salon_scheduler.js`,
  `static/src/xml/salon_scheduler.xml`) and under a new "Note History"
  separator on the Contacts "General Notes" tab
  (`views/res_partner_views.xml`).
- Allergies/Preferences themselves are unchanged - still a single editable
  "current state" textarea each; only the history is new.

## [19.0.1.8.13] - 2026-09-17
### Changed
- **Draft bookings can now overlap any other booking's chair too, not just
  staff/time.** `_check_overlap` (`models/salon_appointment.py`) already
  treated Draft as a tentative hold for the staff-overlap and step-overlap
  checks (a Draft can double-book a beautician until it's Confirmed), but
  the Room/Chair overlap check right below it had no such exception and
  still blocked two overlapping bookings from sharing a chair while both
  were Draft. It now skips that check the same way while `state == 'draft'`,
  so you can stack multiple draft bookings on the same beautician/chair/time
  to pencil in options before confirming one.

## [19.0.1.8.12] - 2026-09-17
### Fixed
- **Very short appointment blocks (e.g. a 15-minute service) showed only
  the phone number, hiding the customer name and the note/general-notes
  icons.** `.appt_content` (`static/src/scss/salon_scheduler.scss`) laid
  its rows out with `justify-content: space-between` on a column flex, which
  pins the *last* row (the phone/footer) to the bottom of the block and
  pushes the *first* row (name + REQ/note/"G" icons) above the visible area
  once the block is too short for all three rows - the opposite of what you
  want to see at a glance. Switched to `flex-start` (with `.appt_title` now
  `flex: none` so it can't get squeezed) so the name and its icons are
  always the row that stays visible; service/phone are what gets clipped on
  the shortest blocks instead.

## [19.0.1.8.11] - 2026-09-17
### Added
- **"G" badge on scheduler appointment cards** when the customer has General
  Notes on file (`res.partner.salon_allergies` / `salon_preferences` -
  the same "Allergies & Preferences" fields shown in the Customer Profile
  modal and the Contacts "General Notes" tab). `scheduler_data()`
  (`models/salon_appointment.py`) now sends `has_general_notes` and a
  combined `general_notes` text per appointment block. Clicking the badge
  (`showGeneralNotes()`, `static/src/js/salon_scheduler.js`) reuses the
  existing Booking Notes popup - its header now reads "General Notes" or
  "Booking Notes" depending on which icon was clicked, instead of a second
  dedicated modal.

## [19.0.1.8.10] - 2026-09-17
### Fixed
- **Appointments booked outside the branch's business hours silently
  vanished from the Scheduler board**, even though they were valid records
  visible in the plain Appointments list (e.g. two Draft bookings at 08:15
  and 21:00-00:00 local time, with the branch configured for 09:00-21:00).
  `scheduler_data()` (`models/salon_appointment.py`) queried appointments
  with `('start_datetime', '<', end), ('end_datetime', '>', start)` where
  `start`/`end` were the *business-hours* window for the day, not the full
  calendar day - anything starting before opening or ending at/after closing
  fell outside that window and was dropped from the query entirely (staff
  header appointment-count badges silently read 0 for them too). The search
  domain now uses the full local calendar day (`day_start`/`day_end`,
  already computed for Planning-shift lookups) instead, and `start_hour`/
  `end_hour` returned to the client are widened to cover any appointment
  that falls before/after the configured business hours (capped to the
  0-23 grid the JS side can render), so the board's visible time range
  grows to include it instead of clipping it off.

## [19.0.1.8.9] - 2026-09-16
### Fixed
- **Modal close buttons showed the literal text `&times;` instead of a ×
  symbol.** The Customer Profile & History modal and the Booking Notes modal
  (`static/src/xml/salon_scheduler.xml`) wrote the close button's label as
  the HTML-entity escape `&amp;times;`; OWL templates don't decode HTML
  entities in text nodes, so it rendered as the raw string `&times;` rather
  than `×`. Both buttons now use the literal `×` character directly.

## [19.0.1.8.8] - 2026-09-14
### Changed
- **Draft bookings can be dragged freely, no matter how many steps they
  have.** `_check_overlap`'s Planning-shift/working-hours availability check
  (`views/../models/salon_appointment.py`) used to run for `state in
  ('draft', 'confirmed')` and, for a multi-step booking, checked *every*
  step's beautician/time - so the more steps a draft had, the more chances
  one of them landed outside that beautician's published shift and blocked
  the drag. It now only runs once `state == 'confirmed'`, matching the
  staff/room double-booking checks just below it which already treat Draft
  as a tentative hold. The scheduler board's client-side "Outside shift"
  guard in `dropAppointment` (`static/src/js/salon_scheduler.js`) is relaxed
  the same way for a Draft-state drag. Chair/room double-booking still
  blocks a Draft move; the shift limit still applies as soon as the booking
  is Confirmed.

## [19.0.1.8.7] - 2026-09-14
### Removed
- **`salon_general_notes` field**, added in 19.0.1.8.4/.5 and removed again
  at the user's request. The "General Notes" customer-form tab (renamed in
  19.0.1.8.6) now just holds Allergies / Medical Notes and Preferences /
  Styling Notes, same as the scheduler's "Allergies & Preferences" modal
  card. `res_partner.salon_general_notes` dropped from the model, both
  views, the scheduler JS, and the `res_partner` DB column.

## [19.0.1.8.6] - 2026-09-14
### Changed
- Renamed the customer form tab from "Salon Notes" to **"General Notes"**
  (still holds `salon_general_notes`, `salon_allergies`,
  `salon_preferences` and `salon_favorite_staff_id`).

## [19.0.1.8.5] - 2026-09-14
### Fixed
- **`salon_general_notes` (and Allergies/Preferences/Favorite Beautician)
  were only reachable from the scheduler's customer search modal** - the
  standard Contacts app `res.partner` form had no field for them at all, so
  a note saved in the scheduler was invisible when opening that same
  customer from Contacts. Added a new "Salon Notes" tab to
  `base.view_partner_form` (`views/res_partner_views.xml`) showing
  `salon_general_notes`, `salon_allergies`, `salon_preferences` and
  `salon_favorite_staff_id` directly on the customer form, right before the
  existing "Service History" tab.

## [19.0.1.8.4] - 2026-09-14
### Added
- **"General Notes" on the customer profile card.** New
  `res.partner.salon_general_notes` field, editable in the scheduler's
  customer search modal (the same "Direct Edit" card as Allergies /
  Preferences). Unlike `salon.appointment.note`, which is scoped to one
  booking and reset per visit, this note lives on the customer record itself
  so it shows every time that customer is opened, regardless of which
  appointment brought you there.

## [19.0.1.8.3] - 2026-09-14
### Added
- **Settings > Salon & Spa > "Allow Done Without POS Payment"** (new
  `res.company.salon_allow_done_without_payment`, off by default). By default
  behaviour is unchanged: the "Done" button still requires
  `payment_state == 'paid'`, same as before. When a manager enables the
  setting, "Done" only requires `state == 'progress'` - for clients who pay
  at a later visit instead of at checkout - and `action_done()` was already
  payment-agnostic (commission/history creation doesn't check
  `payment_state`). Marking an order paid in POS still auto-completes the
  appointment as always via `PosOrder.write()`/`_process_saved_order()`.
- With the setting on, **"Send to POS" stays available on a `done`,
  not-yet-invoiced appointment** (new `salon.appointment.allow_done_without_payment`
  related field drives the button's `invisible` condition) so staff can still
  send it to POS once the client actually pays; it still hides as soon as
  `pos_order_id` is set. With the setting off this extra case can't occur,
  since `done` still implies paid.

## [19.0.1.8.1] - 2026-09-13
### Added
- **"POS" menu item in the Salon & Spa main menu**, next to Scheduler. New
  `pos.session.action_open_salon_pos()` finds the current company's open POS
  session (current user's own session first, else the first open one - same
  lookup `salon.appointment.action_create_pos_order()` / "Send to POS" already
  uses) and redirects straight into it (`/pos/ui/<config_id>/`, `act_url`)
  instead of the POS app's config-picker kanban. Raises a `UserError` if no
  session is open, same message as "Send to POS".

## [19.0.1.8.0] - 2026-09-13
### Added
- **"Salon & Spa" button in the POS navbar.** A new button next to
  Register/Orders (icon-only on small screens) takes the cashier straight
  back to the Salon & Spa app's Scheduler, using the same
  `window.location = "/odoo/action-<xmlid>"` redirect `PosStore.redirectToBackend()`
  already uses for the "Backend" menu item - no confirmation/close-register
  flow needed since it doesn't leave the POS session.

## [19.0.1.7.3] - 2026-09-13
### Fixed
- **"This Week" appointment filter crashed with `Function.prototype.apply was
  called on undefined`.** The search view domain called `context_today().weekday()`
  - the client-side domain evaluator doesn't expose a `weekday()` method on
  its date object, so the call resolved to `undefined` and crashed as soon as
  the filter was applied. `Today` / `Tomorrow` / `This Week` now use Odoo 19's
  relative-date domain literals (`'today'`, `'today +1d'`, `'=week_start'`,
  `'=week_start +1w'`, matching core modules like `planning`) instead of
  hand-rolled `context_today()`/`relativedelta()` expressions.

## [19.0.1.7.2] - 2026-09-13
### Changed
- Scheduler row height (`SLOT_HEIGHT`) halved from 48px to 24px, per feedback
  that the previous fix's rows were bit too large.

## [19.0.1.7.1] - 2026-09-13
### Fixed
- **Scheduler grid unreadable on small screens.** The scheduler's auto-fit
  logic used to shrink the 15-minute row height (down to 12px) so the whole
  working day fit the viewport with no vertical scroll - on short screens the
  time labels became too small to read or overlapped, and the grid body's
  `overflow-y: hidden` clipped rows outright below the fold. Rows now use a
  fixed, readable height (48px) and the grid body scrolls vertically again
  when the day doesn't fit, so the time column stays legible at any screen
  height.

## [19.0.1.7.0] - 2026-09-12
### Added
- **Parallel appointment steps.** `salon.service.step` (service templates) and
  `salon.appointment.step` (booked steps) gain a **Run In Parallel** toggle. A
  step flagged this way starts at the same time as the current block (the
  previous non-parallel step) instead of chaining after it finishes - e.g. a
  manicure and a pedicure run at once by two different beauticians on the same
  customer. `_compute_step_times` and the appointment's `_compute_end_datetime`
  (now sharing one `_assign_step_times` helper) both honor the flag, and the
  appointment's overall end time is the *latest* step to finish rather than the
  sum of all step durations.
- **Same-staff parallel conflict guard.** `_check_overlap` now also checks
  steps *within the same appointment*: if two overlapping steps end up with
  the same beautician (e.g. Run In Parallel was checked without reassigning
  staff), it's rejected with a clear error instead of silently double-booking
  that person.
- **Step count on Services.** `salon.service` gains stored `step_count` /
  `has_steps` fields. The Services list shows a **Steps** column (dimmed when
  0, highlighted when a service has steps), and a new search view adds **Has
  Steps** / **No Steps** filters plus **Group By > Has Steps** / **Number of
  Steps**, so multi-step services are easy to spot at a glance.

- **Manual step timing, for booking into a gap.** `salon.appointment.step`'s
  `run_parallel` boolean is replaced by a `timing_mode` selection: **After
  Previous Step** (default, the old sequential chaining), **Same Time As
  Previous Step** (the old parallel behaviour), and new **Manual Time** -
  the step keeps whatever `start_datetime` you type into it instead of being
  chained, and every recompute (`_compute_step_times` /
  `_assign_step_times`) preserves that value rather than overwriting it. A
  sequential step after a manual one resumes chaining from the manual step's
  end, so e.g. a 15-minute first step can fill a small gap between two
  existing bookings while the remaining steps are manually placed after
  whatever appointment comes next for that beautician. The step list
  (`salon_appointment_views.xml`) now shows a **Timing** dropdown and Start
  Time becomes editable only when a step is set to Manual Time.

- **Per-service beautician delegation with multiple Main Beauticians.**
  Previously, every generated step's beautician defaulted to the Primary
  Beautician, even when a service was outside that person's Allowed Services
  and another selected beautician could actually perform it. A new
  `_pick_staff_for_service(staff_pool, service, fallback_staff_id)` helper
  now assigns each step to whichever of the selected `staff_ids` has that
  step's service in their Allowed Services, falling back to an unrestricted
  beautician (no Allowed Services set) and finally to the primary. Applied
  everywhere steps get generated from services: the `service_ids` onchange,
  `create()`, and `write()`.

- **Auto-parallel default for multi-employee, multi-service bookings.**
  When auto-generating steps from `service_ids`, a step now defaults its
  `timing_mode` to **Same Time As Previous Step** if `_pick_staff_for_service`
  assigned it to a *different* beautician than the previous step (e.g.
  Manicure -> Staff A, Haircut -> Staff B now run at once instead of Haircut
  waiting for Manicure to finish); it stays **After Previous Step** when the
  same beautician is doing both (they can't do two things at once). New
  `_default_timing_mode(prev_staff, assigned_staff)` helper, applied in the
  `service_ids` onchange, `create()`, and `write()`. A template step's own
  Run In Parallel setting still always wins over this guess. Still just a
  default - any step's Timing can be changed by hand afterwards.
  Fixed along the way: `_pick_staff_for_service` and this new helper now
  compare `salon.staff` **records**, not `.id` values - during an onchange,
  ids are Odoo `NewId` objects whose `__bool__` is always `False`, which
  silently broke the truthiness/equality checks the parallel-vs-sequential
  decision (and the delegation fallback) depended on.

### Changed
- **Draft bookings no longer hard-block on staff double-booking.** A booking
  in the `Draft` state is a tentative hold, so `_check_overlap` now skips the
  cross-appointment "beautician already has an appointment" checks (both the
  step-based and the no-steps fallback path) while `state == 'draft'`. You can
  stack a new draft on top of an existing appointment for the same
  beautician/time. The hard block still applies the moment the booking is
  Confirmed (or later) - `_check_overlap` re-runs on every state change, so
  confirming a genuinely conflicting draft still raises the error. Per-step
  "same beautician, two overlapping parallel steps" and room/chair overlap
  checks are unaffected and still always enforced.

## [19.0.1.6.0] - 2026-09-10
### Added
- **Scheduler columns follow the Planning shift schedule.** For the shown day,
  `scheduler_data` looks up each beautician's **published** `planning.slot`
  records (Enterprise *Planning* app) overlapping that day. A beautician linked
  to an employee shows their shift hours (`HH:MM-HH:MM`, multiple ranges joined)
  under the name; a beautician with no shift that day keeps their column but the
  header dims with an **OFF** badge. Beauticians with no linked `hr.employee` are
  unrestricted.
- **Bookings are limited to the beautician's Planning shift.** Only the slots
  inside a published shift are bookable - e.g. a 09:00-18:00 shift in a salon
  open 10:00-22:00 leaves 10:00-18:00 open and 18:00-22:00 greyed with a hatch
  and a `not-allowed` cursor. On the board, clicking or dropping onto an
  off-shift slot is refused with an "Outside shift" toast (the dragged block
  snaps back). Server-side, `_check_overlap` raises `ValidationError` unless the
  booking (and each service step) falls inside one of that beautician's shifts -
  enforced on the form and on scheduler drag/resize alike (a Planning shift is a
  hard limit, unlike the resource-calendar roster which a drag can still
  override). Only checked while the booking is *Draft* / *Confirmed*, so
  in-progress and completed bookings are never retro-invalidated if the roster
  changes. Beauticians with no linked employee keep the previous
  resource-calendar behaviour.

- **Configuration > Shifts menu.** A new *Shifts* item under *Salon & Spa >
  Configuration* opens the Planning app's "Schedule" gantt
  (`planning.planning_action_schedule_by_resource`) so beautician shifts can be
  created and published without leaving the Salon menu. Visible to users with
  Planning access (Planning / User or Administrator).

### Dependencies
- Adds **`planning`** to `depends`. Upgrading the module installs the Planning
  app if it is not already present.

### Upgrade note
- Existing *Confirmed* bookings that sit outside the beautician's Planning shifts
  are left as-is, but the next edit to their time / beautician / status will be
  blocked until they fit a shift (or the shift is added in Planning).

## [19.0.1.5.0] - 2026-09-10
### Added
- **Reschedule a confirmed booking.** `start_datetime` (and `duration_selection`,
  which drives `end_datetime`) on the appointment form are now editable while the
  booking is *Confirmed*, not only *Draft* - so a manager can move a confirmed
  appointment without resetting it to draft first. The existing double-booking,
  chair-clash and working-hours `@api.constrains` re-run on the change, and
  `end_datetime` / step times recompute from the new start.
- **Rebook from an appointment card / form.** The appointment kanban card now
  shows a **Rebook** button on *Completed* and *Cancelled* bookings, and the
  appointment form gains a matching **Rebook** header button in the same states.
  Both call the new `salon.appointment.action_rebook`, which opens a fresh
  appointment form pre-filled from the original (customer, services, main
  beauticians, primary beautician, branch, chair, notes) - the manager just
  picks the new time; nothing is written until they save. The scheduler
  timeline's existing `scheduler_rebook` now delegates to `action_rebook`
  (shared logic; it still accepts the board's `<appt>_s<staff>` block ids).

### Fixed
- **Dragging a booking to a new time on the scheduler had no effect for
  appointments with service steps.** `scheduler_move` routed every step-block
  drag through the "reassign this step's beautician" path (added in 19.0.1.4.0),
  which never touched the timeline - so dropping the block at a different time in
  the same beautician column did nothing and the board snapped back. The step
  branch now distinguishes the two axes of a drop: a column change still only
  reassigns that step's beautician, but a time change shifts the whole
  appointment so the dragged block lands on the drop target (`end_datetime` and
  the other steps follow via `_compute_end_datetime`); both re-run the
  double-booking / chair-clash checks.
- **Dragging a booking to another beautician now moves it instead of adding a
  second beautician.** `scheduler_move` previously appended the drop-target
  beautician to *Main Beauticians* (`(4, id)`), leaving the original in place.
  It now re-derives *Main Beauticians* from the step assignments after the drag,
  so a single-beautician booking swaps cleanly and a beautician still running
  another step of the same appointment is kept.
- Two fields on `salon.client.report` (`appointment_count`, `appointment_ids`)
  shared the label *Appointments*; `appointment_count` is now *Appointment
  Count* (shown as *Total* under the report's Appointments group), clearing the
  `ir.model` duplicate-label warning.
- Decorative Font Awesome icons on the appointment kanban card
  (`fa-scissors` / `fa-user-md` / `fa-clock-o`) gained `title` / `aria-label`,
  clearing the `ir.ui.view` "must have title" accessibility warnings.

## [19.0.1.4.0] - 2026-09-07
### Added
- **"REQ" tag on scheduler cards.** When an appointment has the *Required*
  checkbox ticked (`salon.appointment.staff_required` - the customer specifically
  requested this beautician), the timeline card now shows a red **REQ** badge next
  to the customer name. `scheduler_data` exposes the new `staff_required` flag in
  the appointment payload; styled via `.appt_req_badge`.
- **Notes indicator on scheduler cards.** When a booking has anything in its
  *Notes* tab (`salon.appointment.note`), the timeline card shows a sticky-note
  icon next to the customer name; clicking it opens a read-only popup with the
  full note text (customer comments left at booking time). `scheduler_data` now
  returns `note` per appointment; new `showNote`/`closeNoteModal` handlers and
  `.appt_note_icon` / `.appt_note_text` styles.
- **Clickable beautician headers + daily count.** Each staff column header in the
  scheduler is now clickable and opens that beautician's profile
  (`salon.staff` form). A small count badge overlaid on the top-right of the
  avatar (next to the status dot, so the header row keeps its height) shows how
  many distinct (non-cancelled) appointments that beautician has on the shown
  day. `scheduler_data` returns `appt_count` per staff; new `openStaff` handler
  and `.staff_appt_count` style.
- **Rebook from a scheduler card.** Cards whose status is *Completed* (`done`) or
  *Cancelled* (`cancel`) show a **Rebook** button. It calls `scheduler_rebook`,
  which opens a fresh appointment form pre-filled from the original (customer,
  services, beauticians, branch, chair, notes) - the manager just picks the new
  time; nothing is written until they save.
- **"Bookings" smart button on the beautician form.** `salon.staff` gains an
  `appointment_count` stat button (`action_view_appointments`) opening the full
  booking history for that beautician - every `salon.appointment` where they are
  the primary beautician, one of the Main Beauticians, or assigned to a service
  step (list / form / calendar).
- **Build service steps from existing services.** Configuration > Services >
  *Service Steps* gains a **From Service** column (`salon.service.step.
  source_service_id`): pick an already-defined service and the step name +
  duration are filled in from it (step name still overridable). Lets you compose
  package/combo services out of existing ones. When such a service is added to an
  appointment, the generated appointment step is linked to the source service so
  its price flows through.

### Changed
- **Scheduler drag/resize no longer hard-blocked by roster hours.** Moving or
  resizing a booking on the timeline is an explicit manager action, so it now
  runs with `skip_working_hours_check` - the "X is only available from ..."
  `ValidationError` is bypassed for board moves (double-booking and chair-clash
  checks still apply; the appointment form still enforces working hours). The
  working-hours message also de-duplicates identical shift ranges (was showing
  "07:45 AM to 04:15 PM or 07:45 AM to 04:15 PM"); the check is refactored into a
  shared `_working_hours_check` helper.
- **Dragging a single step now only reassigns its beautician.** Previously
  dropping a step block also shoved the whole appointment's start time. Now a
  step drag just moves that step to the drop-target column - each of an
  appointment's steps can be run by a different beautician, and the timeline
  (step start/end, chained to the appointment start) is left untouched. The
  step's beautician is added to *Main Beauticians* and the double-booking /
  working-hours checks are re-run on the move. On a rejected move the board
  reloads to its stored state.

### Fixed
- **Scheduler errors now show the real message.** Move / resize / mark-arrived
  failures showed only the generic "Odoo Server Error". The handlers now read the
  Python exception text out of the RPC error (`e.data.message`), show it in a
  sticky danger notification, and log the full server traceback (`e.data.debug`)
  to the browser console. `scheduler_move` also no longer crashes with a
  `TypeError` when the dragged appointment has no start/end datetime (falls back
  to its `duration`) and raises a clear `UserError` if the drop-target time can't
  be parsed.
- **Drag & drop on the scheduler did nothing.** The appointment card used
  `t-att-draggable="appt.state != 'cancel'"`; OWL renders a boolean `true`
  attribute as `draggable=""`, which the browser treats as `auto` (not
  draggable), so a drag never started. Now emits the literal string
  `"true"`/`"false"`. `dragStart` also sets `text/plain` data + `effectAllowed`,
  and `dropAppointment` calls `preventDefault()` and falls back to the
  `text/plain` payload.

## [19.0.1.3.0] - 2026-09-03
### Added
- **Client Report** (Reports > Client Report). New `salon.client.report` transient
  model + full-page form: pick a client and see a live mini-dashboard - appointment
  count and a breakdown by status (draft / confirmed / in progress / completed /
  cancelled), no-show/missed count, marked-arrived count, cancellation rate; total
  value, paid, unpaid and average ticket; first/last visit, most-booked beautician
  and service, average review score, memberships; and the client's full
  appointment list. Optional From/To period filter. "Open Appointments" /
  "Open Client" buttons. ACLs for `group_salon_manager` and `base.group_user`.
  `_compute_display_name` gives the page a readable breadcrumb
  ("Client Report - <client>") instead of the raw `model,id`.
- **Status-driven scheduler colours.** `salon.appointment._compute_color` now
  derives the timeline block colour from status instead of the record id
  (`@api.depends('state', 'is_arrived', 'confirmation_sent')`):
  - orange - booking (draft)
  - green - default (confirmed, confirmation e-mail sent)
  - yellow - not confirmed (confirmed, confirmation e-mail not sent yet)
  - blue - arrived / in progress
  - grey - completed / checked out (done)
  - red - cancelled
- **Colour legend** in the scheduler header (six labelled swatches), sharing one
  palette map with the kanban dots/stripes.
- **Status colours on the appointment kanban cards** - a round status dot on the
  card title plus a coloured left accent stripe (`o_salon_status_dot`,
  `o_salon_appt_card`), driven by the same `color` value.
- **Colours in the appointment list view** - row text + a `badge`-widget state
  cell coloured via `decoration-*`; new toggle-able **Arrived** column;
  `confirmation_sent` pulled in hidden for the decoration expressions.
- **Service link on appointment steps.** `salon.appointment.step` gained
  `service_id` (domain-filtered to the row beautician's `service_ids` via a new
  `allowed_service_ids`), a related editable `price_unit`, and an
  `_onchange_service_id` that fills the step name and `duration_minutes` from the
  service. Auto-generated steps now carry `service_id` for single-service steps.
  `name` is no longer required (filled from the service on create).
- **"Beauticians & Services" tab** - the old "Service Steps" page renamed,
  promoted to the first notebook tab, with a Beautician -> Service (filtered) ->
  Duration -> Price grid, editable while in draft.
- **Scheduler quick-create** seeds the first Beautician & Service row with the
  clicked beautician (`default_step_ids` / `default_staff_ids` context).
- **Multiple Main Beauticians.** New `staff_ids` many2many
  (`salon_appointment_staff_rel`) on `salon.appointment`, labelled
  "Main Beauticians", required and tracked. The timeline renders the appointment
  block under every assigned beautician; the booking-overlap constraint is
  checked per beautician; list, kanban and search views updated to the
  many2many. A non-stored `staff_multi` helper flag drives the form modifier
  that reveals the read-only Primary Beautician field only when more than one
  beautician is selected (Odoo view expressions cannot call `len()`).

### Changed
- **Navigation.** The Salon & Spa app now opens straight to the Scheduler
  (`menu_salon_root` carries `action_salon_scheduler_client`). Left-menu order:
  Scheduler (first), Appointments, Customers, Products, Configuration, then
  Dashboard and Reports grouped together at the bottom.
- **Cancellations are logged to Customer History.** `action_cancel` now writes a
  `salon.customer.history` row (`state = 'Cancelled'`, price 0, dated on the
  appointment's scheduled day, note "Cancelled on <when> by <user>"); it is
  removed again on `action_reset_draft`, and `action_done` still overwrites the
  origin's rows. `_populate_history_if_empty` seeds cancelled appointments too on
  fresh installs. Customer-history lists (contact form, appointment form) gained
  `decoration-success` / `decoration-info` / `decoration-danger` for
  Completed / Paid / Cancelled; the scheduler customer-history modal shows a red
  `status_cancelled` badge.
- **Cancelled appointments now stay on the scheduler.** `scheduler_data` no
  longer filters out `state = 'cancel'`, so a cancelled booking keeps its slot
  in the timeline, rendered red and dimmed with a struck-through label
  (`.appt_block.state_cancel`). Cancelled blocks are not draggable and hide the
  "Mark Arrived" button. They still do not block new bookings (the overlap
  constraint keeps excluding cancelled).
- `salon.appointment.staff_id` is now a **stored, editable computed** field
  ("Primary Beautician" = first of `staff_ids`). All downstream logic
  (service-step seeding, commissions, tips, POS order, reports, confirmation
  e-mails) continues to key off this primary, unchanged. `create` back-fills
  `staff_ids` from a lone `staff_id`, so single-staff callers - the
  `salon_spa_scheduler_website` booking controller, `scheduler_quick_create`,
  tests - keep working without changes.
- `_compute_staff_service_ids` now returns the union of every selected
  beautician's services.
- `scheduler_move` / `scheduler_resize` composite-id parsing hardened for the new
  `<appt>_s<staff>` block ids; dragging one block of a multi-beautician
  appointment reassigns the whole appointment to the drop-target beautician and
  time.
- Scheduler `color_3` swatch changed from amber `#f59e0b` to a clearer yellow
  `#eab308` with dark text, so "booking" (orange) and "not confirmed" (yellow)
  are distinguishable.
- Scheduler header switched from a fixed `height: 50px` to
  `min-height: 50px` + `flex-wrap`, so the legend wraps instead of being clipped.
- **Scheduler fits the viewport with no vertical scroll.** The 15-minute row
  height is now dynamic: `fitToViewport()` measures the available height on mount,
  on window resize and after each reload, and shrinks the rows
  (`--salon-slot-h`, 40px down to 12px) so the whole working day is visible at
  once. Appointment-block heights, the current-time line offset and the
  resize-to-duration maths all follow the live row height; the grid wrapper no
  longer scrolls vertically (horizontal scroll for many beauticians is kept).

### Migration
- `migrations/19.0.1.3.0/post-migrate.py` backfills `salon_appointment_staff_rel`
  from each appointment's existing `staff_id`.

### Notes / known limitations
- Odoo list/badge `decoration-*` has no yellow, so in the **list view** "booking"
  and "not confirmed" both render amber; the scheduler and kanban keep the full
  six-colour distinction.
- Staff working-hours / shift validation in `_check_overlap` still covers the
  **primary** beautician only.
- The "Additional Services" tab (`line_ids`) still exists alongside the
  "Beauticians & Services" step grid; `line_ids` feeds the subtotal / POS while
  `step_ids` feeds the timeline.
