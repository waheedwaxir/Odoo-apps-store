# Salon & Spa — Online Website Booking Add-On

Companion module — no separate price.

## Short Description
Website online booking add-on for the **Salon & Spa Management** app (`salon_spa_scheduler`) on Odoo 19. Adds a customer-facing 24/7 self-service appointment page at `/salon/booking` that syncs instantly with the front-desk timeline scheduler, with full multi-company awareness. Auto-installs the moment the Odoo **Website** app is present; the core module itself has **no dependency on Website**.

## Main Features
- Public 24/7 online booking page at `/salon/booking` plus a "Book Online" website menu
- 3-step reservation flow: personal info → branch → services & specialist → date/time
- Existing customers matched automatically by phone or email; new visitors get a contact record
- Bookings land straight on the receptionist's timeline scheduler, honouring the same overlap / double-booking checks as backend appointments
- Staff timezone-aware start time conversion
- **Multi-company aware** – the page only shows the branches, services and beauticians of the website's company (plus shared records); the created appointment is stamped with that company, and submitted selections are re-validated against it before saving
- **Spam protection** – Google reCAPTCHA v3 on the booking form (activates automatically once reCAPTCHA keys are set in *Settings → Website*), plus a honeypot field; web bookings are created in **Draft** so staff confirm before any customer email is sent
- Confirmation reference returned to the customer; confirmation email is queued (never blocks the page)

## Package Contents
Part of a three-module product so the Website app is never a forced dependency:

| Module | Install | Purpose |
| --- | --- | --- |
| `salon_spa_scheduler` | You install it | Core application (scheduler, POS, tips, memberships, commissions, reports, multi-company). **No dependency on Website.** |
| `salon_spa_scheduler_website` | Auto-installs **only when the Website app is present** | **This module.** Customer-facing online booking page (`/salon/booking`) and the "Book Online" website menu. Uninstall it to remove the public page while leaving the core app intact. |
| `salon_spa_scheduler_data` | Optional | Clean, ready-to-use sample data (branches, chairs, staff, services, packages, memberships, customers, appointments, reviews) plus *Import Sample Data* / *Remove Sample Data* menu actions. |

## Requirements
- `salon_spa_scheduler` (core module)
- Odoo **Website** app
- `google_recaptcha` (standard Odoo module; the form still works if reCAPTCHA keys are left unset)

## Suggested App Store Title
Salon & Spa Online Website Booking | Website Add-On | Multi Company | Odoo 19

## Author & Support
- **Author**: Engr Waheed, Techman Solutions
- **Website**: https://www.techmansolutions.com
- **LinkedIn**: https://www.linkedin.com/in/waheed-ullah-810082151/
- **WhatsApp**: +974 3064 3395
