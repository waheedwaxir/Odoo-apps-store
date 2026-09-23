# Technical Design Specification & Developer Guide

**Module Name:** `wu_pos_categories`  
**Display Name:** POS Single Line Categories  
**Odoo Version:** 19.0  
**License:** LGPL-3  
**Price:** Free (0.00 EUR)  
**Author:** Engr Waheed  

---

## 1. Overview & Purpose

In default Odoo 19 Point of Sale, product categories are displayed as a multi-line vertical grid (`.category-list.d-grid`) that consumes substantial vertical screen real estate on POS terminals, pushing the product catalog down.

This module replaces the multi-line grid with a **sleek, single-line horizontal scrollable category bar**:
- Displays categories in a single horizontal row with auto-overflow scrolling.
- Provides smooth navigation buttons (Left `<` and Right `>`) when items overflow.
- Enables mouse drag-to-scroll, touch swipe, and mouse wheel horizontal scrolling.
- Includes a responsive overflow dropdown menu (`⋮`) for instant category jump with color indicators.
- Provides a clean backend toggle in **Settings > Point of Sale** under PoS configuration.
- 100% Free and Open-Source ready for Odoo App Store submission.

---

## 2. File & Directory Structure

```text
wu_pos_categories/
├── __init__.py                          # Python package root
├── __manifest__.py                      # Module metadata, App Store configuration & assets
├── DESIGN_SPEC.md                       # Developer design specification & changelog
├── models/
│   ├── __init__.py                      # Models package initializer
│   ├── pos_config.py                    # Extends pos.config with setting field
│   └── res_config_settings.py           # Extends res.config.settings for backend UI
├── views/
│   └── res_config_settings_views.xml    # Inherits POS settings form view
├── static/
│   ├── description/
│   │   ├── icon.png                     # Odoo App Store & Apps dashboard icon (128x128)
│   │   ├── index.html                   # Rich Bootstrap 5 presentation page for App Store
│   │   ├── banner_cat.png               # Main promotional banner
│   │   ├── pos_main_screen.png          # Screenshot of POS single-line carousel in action
│   │   ├── default_odoo.png             # Screenshot of default Odoo multi-line grid (Before)
│   │   ├── setting_pos.png              # Screenshot of POS Configuration toggle
│   │   └── thumbnails.png               # Showcase thumbnail
│   └── src/
│       └── app/
│           └── components/
│               └── category_selector/
│                   ├── category_selector.js   # OWL Component patch (scrolling, state, events)
│                   ├── category_selector.xml  # OWL Template (precompiled, CSP compliant)
│                   └── category_selector.scss # Styling: pills, scrollbar, colors, animations
```

---

## 3. Architecture & Technical Details

### 3.1 Backend Configuration (`models/` & `views/`)

* **`models/pos_config.py`**:
  - Adds `iface_single_line_categories = fields.Boolean(string="Single-Line Categories", default=True)` to `pos.config`.
  - **Important**: In Odoo 19, `pos.config` inherits `pos.load.mixin` where the base `_load_pos_data_fields` returns `[]`, which triggers Odoo ORM `records.read([], load=False)` to load **all** fields of `pos.config` into the POS frontend state (`this.pos.config`). Do NOT override `_load_pos_data_fields` on `pos.config` to return partial fields, as that would truncate default fields like `currency_id`, `company_id`, etc.

* **`models/res_config_settings.py`**:
  - Exposes `pos_iface_single_line_categories = fields.Boolean(related='pos_config_id.iface_single_line_categories', readonly=False)`.

* **`views/res_config_settings_views.xml`**:
  - Uses XPath targeting `//field[@name='pos_iface_group_by_categ']/ancestor::setting` to insert the setting card into the Point of Sale configuration section.

### 3.2 Frontend OWL Integration (`static/src/app/components/category_selector/`)

* **Component Architecture (`category_selector.js`)**:
  - Assigns `CategorySelector.template = "wu_pos_categories.CategorySelector"` directly to use the precompiled asset template and avoid runtime eval / CSP blockers.
  - Patches `@point_of_sale/app/components/category_selector/category_selector`.
  - **State Management**:
    - `state.canScrollLeft`: Boolean flag updated on scroll/resize.
    - `state.canScrollRight`: Boolean flag updated on scroll/resize.
    - `state.isOverflowOpen`: Controls dropdown menu visibility.
    - **Note on State Updates**: State changes are strictly guarded to prevent re-rendering when values haven't changed, and never mutated inside `onPatched` to avoid infinite render cycles in Owl.
  - **Interactivity**:
    - `scrollCarousel(direction)`: Performs smooth programmatic scrolling by ~60% of viewport width.
    - `onTrackWheel(ev)`: Converts vertical wheel delta (`deltaY`) to horizontal scroll (`scrollLeft`).
    - `onMouseDown / onMouseMove / onMouseUp`: Enables desktop click-and-drag panning.
    - `scrollToSelectedCategory()`: Smoothly scrolls the active category into the center of the viewport.
    - `selectCategory(catId)`: Calls `this.pos.setSelectedCategory(catId)` and handles menu close / centering.

* **Template Structure (`category_selector.xml`)**:
  - Defined cleanly as `<t t-name="wu_pos_categories.CategorySelector">` ensuring full static asset precompilation.
  - All template expressions strictly use `this.` scope prefixes (e.g. `this.state.canScrollLeft`, `this.onTrackScroll`, `this.ui.isSmall`).
  - Uses deterministic category ID hashing `(category.id % 12) + 1` for consistent pastel palette assignment without relying on non-standard template loop index variables.
  - Uses `this.getCategoriesAndSub()` for both the carousel buttons and the overflow dropdown list.
  - Uses conditional `<t t-if="this.pos.config.iface_single_line_categories">`:
    - Renders `.pos-category-carousel-container` with prev/next buttons, horizontal scroll track, category pills, and overflow dropdown.
  - `<t t-else>`: Gracefully renders default Odoo POS grid layout.

* **Styling System (`category_selector.scss`)**:
  - Custom scrollbar styling for webkit and Firefox (`scrollbar-width: thin`).
  - 12 soft pastel color combinations (`wu_pos_categ_color_1` through `wu_pos_categ_color_12`) assigned dynamically or falling back to category record colors.
  - Active button state `.is-selected` with elevated border and subtle shadow.

---

## 4. Developer Instructions: How to Add Changes

When modifying or adding new features to this module:

1. **Adding New Configuration Fields**:
   - Add field to `pos.config`.
   - Add related field to `res.config.settings`.
   - Update `res_config_settings_views.xml`.

2. **Modifying Carousel Behavior / Gestures**:
   - Update `category_selector.js` inside `patch(CategorySelector.prototype, { ... })`.
   - Ensure event listeners are properly cleaned up in `onWillUnmount`.

3. **Modifying SCSS & Layout**:
   - Edit `category_selector.scss`.
   - Keep breakpoints consistent with Bootstrap 5 breakpoints (`ui.isSmall`).

4. **Documenting Changes**:
   - Always add a new entry to the **Change Log** table below with version, author, date, and description.

---

## 5. Change Log & Revision History

| Version | Date (YYYY-MM-DD) | Author | Description of Changes |
| :--- | :--- | :--- | :--- |
| **19.0.1.0.0** | 2026-09-23 | Engr Waheed | **Official Free Release & App Store Polish**: Added `icon.png`, comprehensive `index.html` with screenshots, before/after comparison, free manifest metadata (`price: 0.0`, `currency: 'EUR'`), LGPL-3 licensing, and complete App Store readiness. |
| **19.0.1.0.0-rc7** | 2026-09-23 | Engr Waheed | Direct template binding (`CategorySelector.template = "wu_pos_categories.CategorySelector"`) to bypass runtime XPath AST re-compilation and fully comply with strict CSP policies. |
| **19.0.1.0.0-rc6** | 2026-09-23 | Engr Waheed | Explicitly declare `t-name="wu_pos_categories.CategorySelector"` on extension template to ensure QWeb compiler generates a named template without triggering CSP eval fallback. |
| **19.0.1.0.0-rc5** | 2026-09-23 | Engr Waheed | Prevent infinite render loop: eliminated `onPatched` reactive state mutation, added value change guards to `updateScrollButtons`, unified dropdown dataSource with `getCategoriesAndSub()`. |
| **19.0.1.0.0-rc4** | 2026-09-23 | Engr Waheed | Clean up Owl template scope: removed undeclared loop index references (`cat_index`, `category_index`), migrated to `this.state`, and added deterministic ID-based pastel palette color indexing. |
| **19.0.1.0.0-rc3** | 2026-09-23 | Engr Waheed | Fix Owl template scope bindings (ensure `this.` prefix on all component methods and state properties) and bound event listeners in setup. |
| **19.0.1.0.0-rc2** | 2026-09-23 | Engr Waheed | Fix XML template xpath to use `hasclass('d-grid')` conforming to Odoo 19 QWeb xpath parser rules. |
| **19.0.1.0.0-rc1** | 2026-09-23 | Engr Waheed | Fix pos.config data loading by removing `_load_pos_data_fields` override to prevent truncating core `pos.config` fields (`currency_id`, `company_id`, etc.). |
| **19.0.1.0.0-base** | 2026-09-23 | Engr Waheed | Initial implementation: Single-line category bar, horizontal smooth scroll, touch swipe, drag-to-scroll, responsive overflow menu, backend settings toggle, and 12-color pastel styling system. |
