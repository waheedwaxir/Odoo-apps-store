# Changelog - Salon & Spa Management - Online Booking (salon_spa_scheduler_website)

## [19.0.1.3.0] - 2026-09-30
### Changed
- **Online booking goes step by step.** `/salon/booking` is no longer one
  long form. A step indicator leads the customer through:
  1. **Services** - with the branch above them when there is more than one
     (a single branch is selected on its own); the number of services, the
     total time and price show under the list.
  2. **Beautician** - only those who do every picked service, plus **Any
     available**. Picking one moves straight on to the times.
  3. **Date & Time** - the free times of each beautician at work that day,
     one box per beautician with their shift hours (only the chosen one, if
     one was chosen). Previous / today / next day; a day with nothing free
     offers a button to the next day that has room (up to 30 days ahead).
  4. **Your Details** - name, phone, optional email, next to a summary of
     the booking (branch, services, beautician, when, duration, total).
  - Next checks the step before moving on; Back, or a finished step in the
    indicator, goes back without losing what was chosen.
- **The free times follow the scheduler** (new `/salon/booking/availability`,
  replacing `/salon/booking/slots`), with the board's own rules:
  - At work = a published **Planning shift** that day. Beauticians with no
    shift that day are not offered; the old page used the working-hours
    calendar, which is not what the board goes by.
  - Busy = anything on the beautician's column: bookings (draft too - an
    online request holds its time until reception deals with it), each step
    of a multi-step booking under its own beautician, and time blocks
    (break, leave, training, duty at the other branch...). The old page
    missed steps and blocks.
  - Bookings are placed the way the board draws them: a step with no end
    saved (or no start) runs from the end of the previous step for its
    duration. Reading only the saved step times missed those, and offered
    e.g. a 1-hour treatment in a 45-minute gap the board shows as taken.
  - A time is offered when the whole treatment fits in one shift. Times are
    every 15 minutes, like the scheduler's grid (the old page offered only
    :00 and :30), in the salon's timezone (company), and past times
    of today are left out.
  - Only beauticians linked to an employee are offered online (on the board
    those are the ones under Planning).
- **Kept in sync while the page is open**: the times are read again each
  time the step opens, every minute while it is open and when the customer
  returns to the tab. If the picked time has gone, it is cleared with a
  message.
- **Checked again when the booking is sent**: the time must still be free
  by the same rules, or the customer is sent back to pick another. Two
  requests for the same beautician are handled one after the other, so the
  second sees the first.
### Fixed
- The page's script never ran: Odoo 19 loads it after the page has
  finished loading, and it waited for an event that had already passed -
  so the old time picker did not work either.
- The day picker used the UTC date, so between midnight and 3 AM in Qatar
  "Today" showed the day before.
- The picked time was hard to see (the theme's primary colour); it is now
  filled teal.
