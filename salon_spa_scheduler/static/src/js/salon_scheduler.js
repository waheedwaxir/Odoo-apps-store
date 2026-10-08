/** @odoo-module **/

import { Component, onWillStart, useState, onMounted, onWillUnmount, useRef, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";


const COLOR_FILTER_KEY = "salon_scheduler_color_filter";

function loadColorFilter() {
    try {
        const value = JSON.parse(window.localStorage.getItem(COLOR_FILTER_KEY) || "[]");
        return Array.isArray(value) ? value.filter((c) => Number.isInteger(c)) : [];
    } catch {
        return [];
    }
}

function saveColorFilter(colors) {
    try {
        window.localStorage.setItem(COLOR_FILTER_KEY, JSON.stringify(colors));
    } catch {
        // Private window or blocked storage: the filter just isn't remembered.
    }
}

// Local calendar date, not UTC: toISOString() would roll back to the previous
// day for any timezone ahead of UTC (e.g. midnight CEST is still 22:00 UTC the
// day before), which made the Next Day arrow a no-op and Previous Day skip two
// days instead of one.
function dateToISO(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}

const SLOT_HEIGHT = 24;

// Remember the last date the user navigated to, so returning from an
// appointment form (Save/Discard) or the customer booking flow lands back on
// that date instead of silently resetting to today.
const DATE_STORAGE_KEY = "salon_scheduler_date";

function getStoredDate() {
    try {
        return sessionStorage.getItem(DATE_STORAGE_KEY) || null;
    } catch {
        return null;
    }
}

function setStoredDate(date) {
    try {
        sessionStorage.setItem(DATE_STORAGE_KEY, date);
    } catch {
        // ignore (private browsing / storage disabled)
    }
}

export class SalonScheduler extends Component {
    static template = "salon_spa_scheduler.Scheduler";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.state = useState({
            date: getStoredDate() || dateToISO(new Date()),
            staff: [],
            services: [],
            appointments: [],
            slots: [],
            branches: [],
            selectedBranchId: 0,
            currentTimeTop: -1,
            slotHeight: SLOT_HEIGHT,
            headHeight: 70,
            searchQuery: "",
            searchResults: [],
            selectedCustomer: null,
            showCustomerModal: false,
            customerHistory: [],
            noteHistory: [],
            // Status colours picked in the legend; bookings of other
            // statuses fade. Empty = no filter. Remembered per browser.
            colorFilter: loadColorFilter(),
            // Booking note being written from the popup: {apptId, customer, text}.
            noteEdit: null,
            activeNoteAppt: null,
            showNoteModal: false,
            activeNote: "",
            activeNoteCustomer: "",
            activeNoteTitle: "Booking Notes",
            // Block clicked once on the grid: drives the info popup and the
            // highlighted time range in the time column.
            selectedApptId: null,
            userCanCheckout: false,
            blockTypes: [],
            // Empty slot right-clicked: {staffId, start} while the block
            // type chooser is open.
            slotChooser: null,
            // Length typed into the chooser; both empty = the type's default.
            blockHours: "",
            blockMins: "",
        });
        this.gridRef = useRef("grid");
        // Cursor straight into the hours field when the block chooser opens.
        this.blockHoursRef = useRef("blockHours");
        useEffect(
            (chooser) => {
                if (chooser && this.blockHoursRef.el) {
                    this.blockHoursRef.el.focus();
                }
            },
            () => [this.state.slotChooser]
        );
        onWillStart(() => this.loadData());

        let timeInterval;
        onMounted(() => {
            this._onResize = () => this.fitToViewport();
            window.addEventListener("resize", this._onResize);
            this.fitToViewport();
            timeInterval = setInterval(() => {
                this.updateCurrentTimeLine();
            }, 60000);
        });
        onWillUnmount(() => {
            if (timeInterval) {
                clearInterval(timeInterval);
            }
            window.removeEventListener("resize", this._onResize);
        });
    }

    // Rows keep a fixed, readable height (SLOT_HEIGHT) and the grid scrolls
    // vertically when the working day doesn't fit the viewport. Still re-measure
    // the sticky header's height on resize so the current-time line (positioned
    // as headHeight + offset) lines up under it.
    fitToViewport() {
        const table = this.gridRef.el;
        if (!table || !this.state.slots.length) {
            return;
        }
        const thead = table.querySelector("thead");
        const headHeight = thead ? thead.offsetHeight : 70;
        this.state.headHeight = headHeight;
        this.updateCurrentTimeLine();
    }

    async onCustomerSearchInput(ev) {
        const val = ev.target.value;
        this.state.searchQuery = val;
        if (!val || val.length < 2) {
            this.state.searchResults = [];
            return;
        }
        const phoneDigits = val.replace(/\D/g, "");
        try {
            const results = await this.orm.call(
                "res.partner",
                "search_read",
                [],
                {
                    domain: [
                        "|", "|", "|", "|",
                        ["name", "ilike", val], ["phone", "ilike", val], ["email", "ilike", val],
                        ["salon_other_phones", "ilike", val],
                        // Digits only, so "30236826" finds "+974 3023 6826" - but only
                        // once it looks like a number, or "Ai3" would match every "3".
                        ["salon_phone_search", "ilike", phoneDigits.length >= 5 ? phoneDigits : val],
                    ],
                    fields: ["id", "name", "phone", "email", "salon_allergies", "salon_preferences", "salon_favorite_staff_id"],
                    limit: 10
                }
            );
            this.state.searchResults = results;
        } catch (e) {
            console.error("Search failed:", e);
        }
    }

    async selectCustomer(customer) {
        this.state.selectedCustomer = customer;
        this.state.searchQuery = "";
        this.state.searchResults = [];
        this.state.showCustomerModal = true;
        try {
            const history = await this.orm.call(
                "salon.customer.history",
                "search_read",
                [],
                {
                    domain: [["partner_id", "=", customer.id]],
                    fields: ["id", "date", "service_name", "staff_name", "state", "notes", "price_unit", "origin"]
                }
            );
            this.state.customerHistory = history;
        } catch (e) {
            console.error("Loading history failed:", e);
        }
        await this.loadNoteHistory(customer.id);
    }

    async loadNoteHistory(partnerId) {
        try {
            this.state.noteHistory = await this.orm.call(
                "salon.customer.note",
                "search_read",
                [],
                {
                    domain: [["partner_id", "=", partnerId]],
                    fields: ["id", "date", "user_id", "allergies", "preferences"],
                }
            );
        } catch (e) {
            console.error("Loading note history failed:", e);
        }
    }

    closeCustomerModal() {
        this.state.showCustomerModal = false;
        this.state.selectedCustomer = null;
        this.state.customerHistory = [];
        this.state.noteHistory = [];
    }

    async saveCustomerProfile() {
        const cust = this.state.selectedCustomer;
        try {
            await this.orm.call("res.partner", "action_update_salon_notes", [
                [cust.id],
                cust.salon_allergies || "",
                cust.salon_preferences || "",
            ]);
            this.notification.add("Customer notes updated successfully!", { type: "success" });
            await this.loadNoteHistory(cust.id);
        } catch (e) {
            this.notification.add(e.message || "Could not update customer notes", { type: "danger" });
        }
    }

    bookForCustomer() {
        const customerId = this.state.selectedCustomer.id;
        this.closeCustomerModal();
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "salon.appointment",
            views: [[false, "form"]],
            target: "current",
            context: {
                default_partner_id: customerId,
            }
        });
    }

    async loadData() {
        const data = await this.orm.call("salon.appointment", "scheduler_data", [this.state.date]);
        this.state.staff = data.staff;
        this.state.services = data.services;
        this.state.appointments = data.appointments;
        this.state.branches = data.branches || [];
        this.state.userCanCheckout = !!data.user_can_checkout;
        this.state.blockTypes = data.block_types || [];
        this.state.startHour = data.start_hour || 8;
        this.state.endHour = data.end_hour || 22;
        this.state.slots = this.makeSlots(data.date, data.start_hour, data.end_hour, data.slot_minutes);
        this.updateCurrentTimeLine();
        // Re-fit after the new rows render (slot count may have changed).
        if (typeof requestAnimationFrame === "function") {
            requestAnimationFrame(() => this.fitToViewport());
        }
    }

    updateCurrentTimeLine() {
        const todayStr = dateToISO(new Date());
        if (this.state.date !== todayStr) {
            this.state.currentTimeTop = -1;
            return;
        }
        const now = new Date();
        const startHour = this.state.startHour || 8;
        const endHour = this.state.endHour || 22;
        const currentHour = now.getHours();
        const currentMinute = now.getMinutes();

        if (currentHour < startHour || currentHour >= endHour) {
            this.state.currentTimeTop = -1;
            return;
        }

        const slotHeight = this.state.slotHeight || SLOT_HEIGHT;
        const hoursDiff = currentHour - startHour;
        const minutesDiff = currentMinute;

        const topOffset = (hoursDiff * 4 + minutesDiff / 15) * slotHeight;
        this.state.currentTimeTop = topOffset;
    }

    onBranchChange(ev) {
        this.state.selectedBranchId = parseInt(ev.target.value);
    }

    makeSlots(date, startHour, endHour, step) {
        const slots = [];
        const start = new Date(`${date}T${String(startHour).padStart(2, "0")}:00:00`);
        const end = new Date(`${date}T${String(endHour).padStart(2, "0")}:00:00`);
        for (let d = start; d < end; d = new Date(d.getTime() + step * 60000)) {
            slots.push({
                key: d.toISOString(),
                datetime: d.toISOString().slice(0, 19).replace("T", " "),
                label: d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            });
        }
        return slots;
    }

    appointmentsFor(staffId, slotDatetime) {
        if (!slotDatetime || typeof slotDatetime !== "string") return [];
        const slotTime = new Date(slotDatetime.replace(" ", "T")).getTime();
        return (this.state.appointments || []).filter((a) => {
            if (!a || !a.start || typeof a.start !== "string") return false;
            const startDt = new Date(a.start.replace(" ", "T"));
            const minutes = startDt.getMinutes();
            const roundedMinutes = Math.floor(minutes / 15) * 15;
            startDt.setMinutes(roundedMinutes);
            startDt.setSeconds(0);
            startDt.setMilliseconds(0);
            const matchStaff = a.staff_id === staffId && startDt.getTime() === slotTime;
            if (!matchStaff) return false;
            if (this.state.selectedBranchId) {
                return a.branch_id === this.state.selectedBranchId;
            }
            return true;
        });
    }

    previousDay() {
        const d = new Date(this.state.date + "T00:00:00");
        d.setDate(d.getDate() - 1);
        this.state.date = dateToISO(d);
        setStoredDate(this.state.date);
        return this.loadData();
    }

    nextDay() {
        const d = new Date(this.state.date + "T00:00:00");
        d.setDate(d.getDate() + 1);
        this.state.date = dateToISO(d);
        setStoredDate(this.state.date);
        return this.loadData();
    }

    today() {
        this.state.date = dateToISO(new Date());
        setStoredDate(this.state.date);
        return this.loadData();
    }

    formattedDate() {
        const options = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' };
        const d = new Date(this.state.date + "T00:00:00");
        return d.toLocaleDateString(undefined, options);
    }

    async onDateChange(ev) {
        this.state.date = ev.target.value;
        setStoredDate(this.state.date);
        await this.loadData();
    }

    // A beautician linked to an employee can only be booked inside their
    // published Planning shifts for the day. `slotDatetime` is the naive-UTC
    // "YYYY-MM-DD HH:MM:SS" slot start, directly comparable to shift_ranges.
    slotOffShift(staff, slotDatetime) {
        if (!staff || !staff.planning_gated) return false;
        const ranges = staff.shift_ranges || [];
        if (!ranges.length) return true;
        if (!slotDatetime || typeof slotDatetime !== "string") return false;
        return !ranges.some(([a, b]) => slotDatetime >= a && slotDatetime < b);
    }

    _offShiftMessage(staff) {
        if (staff && staff.shift_hint) {
            return `${staff.name} is only scheduled ${staff.shift_hint} on this day (Planning shift).`;
        }
        return `${staff ? staff.name : "This beautician"} has no Planning shift on this day.`;
    }

    quickCreate(ev) {
        const cell = ev.currentTarget;
        const staffId = parseInt(cell.dataset.staffId);
        const staff = (this.state.staff || []).find((s) => s.id === staffId);
        if (this.slotOffShift(staff, cell.dataset.start)) {
            const blockHint = this.state.blockTypes.length
                ? " Right-click the slot to block the time instead."
                : "";
            this.notification.add(this._offShiftMessage(staff) + blockHint, {
                type: "warning",
                title: "Outside shift",
            });
            return;
        }
        this._newAppointmentAt(staffId, cell.dataset.start);
    }

    // Right-click on an empty slot: block the time. Allowed outside the shift -
    // duty at another branch is exactly that.
    openBlockChooser(ev) {
        // Right-click on a card sitting in the cell is not a click on free time.
        if (ev.target.closest(".appt_block")) return;
        if (!this.state.blockTypes.length) {
            this.notification.add("Create a block type under Configuration > Block Types first.", {
                type: "warning",
                title: "Time block",
            });
            return;
        }
        const cell = ev.currentTarget;
        this.state.blockHours = "";
        this.state.blockMins = "";
        this.state.slotChooser = {
            staffId: parseInt(cell.dataset.staffId),
            start: cell.dataset.start,
        };
    }

    closeSlotChooser() {
        this.state.slotChooser = null;
    }

    onBlockHoursInput(ev) {
        this.state.blockHours = ev.target.value;
    }

    onBlockMinsInput(ev) {
        this.state.blockMins = ev.target.value;
    }

    // Minutes typed into the chooser, or 0 when left empty (use the type's).
    get chooserMinutes() {
        const hours = Math.max(0, parseFloat(this.state.blockHours) || 0);
        const mins = Math.max(0, parseInt(this.state.blockMins) || 0);
        return Math.round(hours * 60) + mins;
    }

    async chooserCreateBlock(blockType) {
        const chooser = this.state.slotChooser;
        if (!chooser) return;
        this.state.slotChooser = null;
        try {
            await this.orm.call("salon.block", "scheduler_create", [{
                block_type_id: blockType.id,
                staff_id: chooser.staffId,
                start_datetime: chooser.start,
                duration_minutes: this.chooserMinutes || blockType.duration,
                branch_id: this._branchFor(chooser.staffId),
            }]);
        } catch (e) {
            this.notification.add(this._rpcErrorMessage(e, "Could not create the block."), {
                type: "danger",
                title: "Time block",
            });
        }
        await this.loadData();
    }

    // The branch new work on the board belongs to: the one picked in the
    // header, or - with all branches shown - the clicked beautician's own.
    _branchFor(staffId) {
        if (this.state.selectedBranchId) {
            return this.state.selectedBranchId;
        }
        const staff = (this.state.staff || []).find((s) => s.id === staffId);
        return (staff && staff.company_id) || false;
    }

    // Beautician columns: only the selected branch's, or everyone's.
    get visibleStaff() {
        const branchId = this.state.selectedBranchId;
        const staff = this.state.staff || [];
        return branchId ? staff.filter((s) => !s.company_id || s.company_id === branchId) : staff;
    }

    _newAppointmentAt(staffId, start) {
        const branchId = this._branchFor(staffId);
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "salon.appointment",
            views: [[false, "form"]],
            target: "current",
            context: {
                default_staff_ids: [staffId],
                default_staff_id: staffId,
                default_start_datetime: start,
                ...(branchId ? { default_company_id: branchId, default_branch_id: branchId } : {}),
                // Seed the first "Beautician & Service" row with the clicked beautician
                default_step_ids: [[0, 0, { staff_id: staffId, need_staff: true, duration_minutes: 30 }]],
            }
        });
    }

    // Pull the real Python message/traceback out of an Odoo RPC error. `e.message`
    // is usually the generic "Odoo Server Error"; the detail sits in `e.data`.
    _rpcErrorMessage(e, fallback) {
        const data = e && e.data;
        const detail = (data && (data.message || data.arguments?.[0])) || (e && e.message);
        if (data && data.debug) {
            console.error("[salon scheduler] server error:\n" + data.debug);
        } else {
            console.error("[salon scheduler] error:", e);
        }
        return detail || fallback;
    }

    dragStart(ev) {
        const block = ev.currentTarget;
        if (block.getAttribute("draggable") === "false") {
            ev.preventDefault();
            return;
        }
        ev.dataTransfer.setData("appointment_id", block.dataset.id);
        // Some browsers only start a drag once text/plain is present.
        ev.dataTransfer.setData("text/plain", block.dataset.id);
        ev.dataTransfer.effectAllowed = "move";
    }

    startResize(ev) {
        this.resizingAppt = ev.currentTarget.dataset.id;
        this.resizeStartY = ev.clientY;
        const apptBlock = ev.currentTarget.closest('.appt_block');
        this.resizeStartHeight = apptBlock.offsetHeight;
        
        this._onMouseMove = this.performResize.bind(this);
        this._onMouseUp = this.endResize.bind(this);
        document.addEventListener('mousemove', this._onMouseMove);
        document.addEventListener('mouseup', this._onMouseUp);
        
        // Prevent default drag and drop while resizing
        ev.preventDefault();
        ev.stopPropagation();
    }

    performResize(ev) {
        if (!this.resizingAppt) return;
        const deltaY = ev.clientY - this.resizeStartY;
        const newHeight = Math.max(this.state.slotHeight || SLOT_HEIGHT, this.resizeStartHeight + deltaY);
        const apptBlock = document.querySelector(`.appt_block[data-id="${this.resizingAppt}"]`);
        if (apptBlock) {
            apptBlock.style.height = `${newHeight}px`;
        }
    }

    async endResize(ev) {
        document.removeEventListener('mousemove', this._onMouseMove);
        document.removeEventListener('mouseup', this._onMouseUp);
        
        if (!this.resizingAppt) return;
        const resizedBlock = this.blockEntry(this.resizingAppt);
        const apptBlock = document.querySelector(`.appt_block[data-id="${this.resizingAppt}"]`);
        if (apptBlock) {
            // Calculate new duration based on height. slotHeight px = 1 slot (15 mins)
            // Height = duration * 4 * slotHeight - 2 => duration = (Height + 2) / (slotHeight * 4)
            const slotHeight = this.state.slotHeight || SLOT_HEIGHT;
            let newHeight = apptBlock.offsetHeight;
            let durationHours = (newHeight + 2) / (slotHeight * 4);
            // Round to nearest 15 mins (0.25 hours)
            durationHours = Math.max(0.25, Math.round(durationHours * 4) / 4);
            
            try {
                if (resizedBlock) {
                    // A block id ("b42") would not survive scheduler_resize.
                    await this.orm.call("salon.appointment", "scheduler_resize_block", [
                        resizedBlock.block_id,
                        durationHours,
                    ]);
                } else {
                    await this.orm.call("salon.appointment", "scheduler_resize", [this.resizingAppt, durationHours]);
                }
                await this.loadData();
            } catch (e) {
                this.notification.add(this._rpcErrorMessage(e, "Could not resize appointment"), {
                    type: "danger",
                    title: "Resize failed",
                    sticky: true,
                });
                await this.loadData(); // Revert visual change
            }
        }
        this.resizingAppt = null;
        // The mouseup that ends a resize is followed by a click on the block;
        // don't let it open the info popup.
        this._justResized = true;
        setTimeout(() => (this._justResized = false), 0);
    }

    async dropAppointment(ev) {
        ev.preventDefault();
        const appointmentId =
            ev.dataTransfer.getData("appointment_id") || ev.dataTransfer.getData("text/plain");
        if (!appointmentId) return;
        const cell = ev.currentTarget;
        const staffId = parseInt(cell.dataset.staffId);
        const draggedBlock = this.blockEntry(appointmentId);
        if (draggedBlock) {
            try {
                await this.orm.call("salon.appointment", "scheduler_move_block", [
                    draggedBlock.block_id,
                    staffId,
                    cell.dataset.start,
                ]);
                await this.loadData();
            } catch (e) {
                this.notification.add(
                    this._rpcErrorMessage(e, "Could not move this block."),
                    { type: "danger", title: "Time block" }
                );
            }
            return;
        }
        const staff = (this.state.staff || []).find((s) => s.id === staffId);
        // A Draft booking is still just a tentative hold - let it move anywhere,
        // regardless of how many steps/beauticians it has, same as the server no
        // longer enforces the Planning-shift limit until it's Confirmed.
        const draggedAppt = (this.state.appointments || []).find((a) => String(a.id) === String(appointmentId));
        const isDraft = draggedAppt && draggedAppt.state === 'draft';
        if (!isDraft && this.slotOffShift(staff, cell.dataset.start)) {
            this.notification.add(this._offShiftMessage(staff), {
                type: "warning",
                title: "Outside shift",
            });
            await this.loadData(); // snap the dragged block back to its stored slot
            return;
        }
        if (draggedAppt && draggedAppt.staff_required) {
            // Warn only: the customer asked for this beautician, but the move is still allowed.
            const proceed = await new Promise((resolve) => {
                this.dialog.add(ConfirmationDialog, {
                    title: "Requested beautician",
                    body: "This service was requested by the customer to be done by this specific person. Do you still want to move it?",
                    confirmLabel: "Move anyway",
                    confirm: () => resolve(true),
                    cancelLabel: "Cancel",
                    cancel: () => resolve(false),
                }, { onClose: () => resolve(false) });
            });
            if (!proceed) {
                await this.loadData();
                return;
            }
        }
        try {
            await this.orm.call("salon.appointment", "scheduler_move", [appointmentId, cell.dataset.staffId, cell.dataset.start]);
            await this.loadData();
        } catch (e) {
            this.notification.add(this._rpcErrorMessage(e, "Could not move appointment"), {
                type: "danger",
                title: "Move failed",
                sticky: true,
            });
            await this.loadData(); // revert the board to the stored state
        }
    }

    async markArrived(ev) {
        const appointmentId = ev.currentTarget.dataset.id;
        if (!appointmentId) return;
        try {
            await this.orm.call("salon.appointment", "scheduler_mark_arrived", [appointmentId]);
            await this.loadData();
        } catch (e) {
            this.notification.add(this._rpcErrorMessage(e, "Could not mark as arrived"), {
                type: "danger",
                sticky: true,
            });
        }
    }

    async rebook(ev) {
        const appointmentId = ev.currentTarget.dataset.id;
        if (!appointmentId) return;
        try {
            const action = await this.orm.call("salon.appointment", "scheduler_rebook", [appointmentId]);
            this.action.doAction(action);
        } catch (e) {
            this.notification.add(this._rpcErrorMessage(e, "Could not start a rebooking"), {
                type: "danger",
                sticky: true,
            });
        }
    }

    showNote(ev) {
        const id = ev.currentTarget.dataset.id;
        const appt = (this.state.appointments || []).find((a) => String(a.id) === String(id));
        if (!appt || !(appt.note || appt.step_note)) return;
        // On a beautician's block: their own line note first, then the
        // booking's note for the whole visit.
        const parts = [];
        if (appt.step_note) {
            parts.push(`${this.staffName(appt.staff_id)}:\n${appt.step_note}`);
        }
        if (appt.note) {
            parts.push(appt.step_note ? `Booking:\n${appt.note}` : appt.note);
        }
        this.state.activeNote = parts.join("\n\n");
        this.state.activeNoteCustomer = appt.customer || "";
        this.state.activeNoteTitle = "Booking Notes";
        // Lets the note window offer Edit Note for this booking.
        this.state.activeNoteAppt = this.noteEditable(appt) ? appt : null;
        this.state.showNoteModal = true;
    }

    showGeneralNotes(ev) {
        const id = ev.currentTarget.dataset.id;
        const appt = (this.state.appointments || []).find((a) => String(a.id) === String(id));
        if (!appt || !appt.general_notes) return;
        this.state.activeNote = appt.general_notes;
        this.state.activeNoteCustomer = appt.customer || "";
        this.state.activeNoteTitle = "General Notes";
        this.state.showNoteModal = true;
    }

    // ---- Status filter (legend) --------------------------------------------

    get legendItems() {
        return [
            { color: 2, label: "Booking" },
            { color: 4, label: "Confirmed" },
            { color: 3, label: "Not confirmed" },
            { color: 5, label: "Arrived" },
            { color: 6, label: "In Progress" },
            { color: 9, label: "Completed" },
            { color: 1, label: "Cancelled" },
        ];
    }

    toggleColorFilter(ev) {
        const color = parseInt(ev.currentTarget.dataset.color);
        const colors = this.state.colorFilter.includes(color)
            ? this.state.colorFilter.filter((c) => c !== color)
            : [...this.state.colorFilter, color];
        this.state.colorFilter = colors;
        saveColorFilter(colors);
    }

    // Faded, not hidden: the time stays visibly taken. Time blocks never fade.
    isFilteredOut(appt) {
        return !appt.is_block && this.state.colorFilter.length > 0
            && !this.state.colorFilter.includes(appt.color);
    }

    editActiveNote() {
        const appt = this.state.activeNoteAppt;
        if (!appt) return;
        this.closeNoteModal();
        this.openNoteEditor(appt);
    }

    closeNoteModal() {
        this.state.activeNoteAppt = null;
        this.state.showNoteModal = false;
        this.state.activeNote = "";
        this.state.activeNoteCustomer = "";
        this.state.activeNoteTitle = "Booking Notes";
    }

    openStaff(ev) {
        const id = parseInt(ev.currentTarget.dataset.id);
        if (!id) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "salon.staff",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // ---- Appointment info popup (single click) -----------------------------

    get selectedAppt() {
        const id = this.state.selectedApptId;
        if (!id) return null;
        return (this.state.appointments || []).find((a) => String(a.id) === String(id)) || null;
    }

    // ---- Time blocks ------------------------------------------------------
    // Blocks ride in `appointments` (see salon.appointment._scheduler_block_entries)
    // so the timeline renders them without a special case. They have no booking
    // behind them, so anything that would call salon.appointment with their id
    // has to peel off here first.

    /** The board entry behind a card id such as "b42", if it is a block. */
    blockEntry(id) {
        if (id === undefined || id === null) return null;
        const entry = (this.state.appointments || []).find(
            (a) => String(a.id) === String(id)
        );
        return entry && entry.is_block ? entry : null;
    }

    openBlockForm(blockId) {
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "salon.block",
                res_id: blockId,
                views: [[false, "form"]],
                target: "new",
            },
            { onClose: () => this.loadData() }
        );
    }

    popupEditBlock() {
        const block = this.selectedAppt;
        this.closeApptPopup();
        if (block && block.is_block) {
            this.openBlockForm(block.block_id);
        }
    }

    popupRemoveBlock() {
        const block = this.selectedAppt;
        if (!block || !block.is_block) return;
        // Close the popup first: it sits above Odoo's dialog layer and would
        // otherwise cover the confirmation.
        this.closeApptPopup();
        this.dialog.add(ConfirmationDialog, {
            title: "Remove time block",
            body: `Remove "${block.name}" for ${this.staffName(block.staff_id)} (${this.timeRange(block)})?`,
            confirmLabel: "Remove",
            confirm: async () => {
                try {
                    await this.orm.call("salon.appointment", "scheduler_cancel_block", [block.block_id]);
                } catch (e) {
                    this.notification.add(this._rpcErrorMessage(e, "Could not remove the block."), {
                        type: "danger",
                        title: "Time block",
                    });
                }
                await this.loadData();
            },
            cancel: () => {},
        });
    }

    selectAppointment(ev) {
        if (this._justResized) return;
        this.state.selectedApptId = ev.currentTarget.dataset.id;
    }

    closeApptPopup() {
        this.state.selectedApptId = null;
    }

    // Every block on the board that belongs to the selected booking (one per
    // step / beautician), in time order - listed as the booking's services.
    selectedApptLines() {
        const appt = this.selectedAppt;
        if (!appt) return [];
        return (this.state.appointments || [])
            .filter((a) => a.appointment_id === appt.appointment_id)
            .sort((a, b) => (a.start < b.start ? -1 : a.start > b.start ? 1 : 0));
    }

    // True when the time-column row starting at `slotDatetime` falls inside the
    // selected block. Both sides are naive-UTC "YYYY-MM-DD HH:MM:SS" strings,
    // so they compare lexically; the start is floored to the 15-min row it is
    // rendered in (same rounding as appointmentsFor).
    slotInSelection(slotDatetime) {
        const appt = this.selectedAppt;
        if (!appt || !appt.start || !appt.end || !slotDatetime) return false;
        const start = new Date(appt.start.replace(" ", "T") + "Z");
        start.setUTCMinutes(Math.floor(start.getUTCMinutes() / 15) * 15, 0, 0);
        const startStr = start.toISOString().slice(0, 19).replace("T", " ");
        return slotDatetime >= startStr && slotDatetime < appt.end;
    }

    staffName(staffId) {
        const staff = (this.state.staff || []).find((s) => s.id === staffId);
        return staff ? staff.name : "";
    }

    // "HH:MM AM - HH:MM PM" in the user's local time for a block.
    timeRange(appt) {
        const fmt = (str) =>
            new Date(str.replace(" ", "T") + "Z").toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        if (!appt || !appt.start) return "";
        return appt.end ? `${fmt(appt.start)} - ${fmt(appt.end)}` : fmt(appt.start);
    }

    formatAmount(value) {
        return (value || 0).toFixed(2);
    }

    stateLabel(state) {
        return {
            draft: "Draft",
            confirmed: "Confirmed",
            progress: "In Progress",
            done: "Done",
            cancel: "Cancelled",
        }[state] || state;
    }

    popupEditNote() {
        this.openNoteEditor(this.selectedAppt);
    }

    // A finished (Done) or cancelled booking's note is part of its record.
    noteEditable(appt) {
        return !!appt && !["done", "cancel"].includes(appt.state);
    }

    openNoteEditor(appt) {
        if (!this.noteEditable(appt)) return;
        this.state.noteEdit = {
            apptId: appt.appointment_id,
            customer: appt.customer || "",
            text: appt.note || "",
        };
    }

    // Note on one line of the booking - for that beautician only.
    openStepNoteEditor(line) {
        if (!line?.step_id || !this.noteEditable(line)) return;
        this.state.noteEdit = {
            stepId: line.step_id,
            title: `Note for ${this.staffName(line.staff_id)} (${line.service})`,
            customer: line.customer || "",
            text: line.step_note || "",
        };
    }

    closeNoteEdit() {
        this.state.noteEdit = null;
    }

    async saveNoteEdit() {
        const edit = this.state.noteEdit;
        if (!edit) return;
        try {
            if (edit.stepId) {
                await this.orm.call("salon.appointment", "scheduler_set_step_note", [edit.stepId, edit.text]);
            } else {
                await this.orm.call("salon.appointment", "scheduler_set_note", [edit.apptId, edit.text]);
            }
            this.state.noteEdit = null;
            await this.loadData();
        } catch (e) {
            this.notification.add(this._rpcErrorMessage(e, "Could not save the note"), {
                type: "danger",
                sticky: true,
            });
        }
    }

    // The one status shown at the top of the booking popup: the furthest the
    // booking has got.
    popupLastStatus(appt) {
        if (appt.state === "cancel") {
            return { key: "cancel", label: "Cancelled", icon: "" };
        }
        if (appt.payment_state === "paid") {
            return { key: "paid", label: "Paid", icon: "fa-check" };
        }
        if (appt.state === "done") {
            return { key: "done", label: "Done", icon: "fa-check-circle" };
        }
        if (appt.state === "progress") {
            return { key: "progress", label: "In Progress", icon: "fa-play-circle" };
        }
        if (appt.is_arrived) {
            return { key: "arrived", label: "Arrived", icon: "fa-check" };
        }
        return { key: appt.state, label: this.stateLabel(appt.state), icon: "" };
    }

    popupComplete() {
        const appt = this.selectedAppt;
        if (!appt) return;
        // Close the popup first: it sits above Odoo's dialog layer and would
        // otherwise cover the confirmation.
        this.closeApptPopup();
        this.dialog.add(ConfirmationDialog, {
            title: "Complete service",
            body: `Are you sure everything for ${appt.customer || "this customer"} was done as per the order list - the services and the beauticians who did them?`,
            confirmLabel: "Yes, completed",
            confirm: async () => {
                try {
                    await this.orm.call("salon.appointment", "scheduler_complete", [appt.appointment_id]);
                } catch (e) {
                    this.notification.add(this._rpcErrorMessage(e, "Could not mark the service completed"), {
                        type: "danger",
                        sticky: true,
                    });
                }
                await this.loadData();
            },
            cancelLabel: "No, go back",
            cancel: () => {},
        });
    }

    async popupStartService() {
        const appt = this.selectedAppt;
        if (!appt) return;
        try {
            await this.orm.call("salon.appointment", "scheduler_start_service", [appt.appointment_id]);
            await this.loadData();
        } catch (e) {
            this.notification.add(this._rpcErrorMessage(e, "Could not start the service"), {
                type: "danger",
                sticky: true,
            });
        }
    }

    async popupConfirm() {
        const appt = this.selectedAppt;
        if (!appt) return;
        try {
            await this.orm.call("salon.appointment", "scheduler_confirm", [appt.appointment_id]);
            await this.loadData();
        } catch (e) {
            this.notification.add(this._rpcErrorMessage(e, "Could not confirm the appointment"), {
                type: "danger",
                sticky: true,
            });
        }
    }

    async popupMarkArrived() {
        const appt = this.selectedAppt;
        if (!appt) return;
        try {
            await this.orm.call("salon.appointment", "scheduler_mark_arrived", [appt.appointment_id]);
            await this.loadData();
        } catch (e) {
            this.notification.add(this._rpcErrorMessage(e, "Could not mark as arrived"), {
                type: "danger",
                sticky: true,
            });
        }
    }

    async popupRebook() {
        const appt = this.selectedAppt;
        if (!appt) return;
        this.closeApptPopup();
        try {
            const action = await this.orm.call("salon.appointment", "scheduler_rebook", [appt.appointment_id]);
            this.action.doAction(action);
        } catch (e) {
            this.notification.add(this._rpcErrorMessage(e, "Could not start a rebooking"), {
                type: "danger",
                sticky: true,
            });
        }
    }

    // Send the booking to the Point of Sale and open it there (reopens the
    // booking's unpaid POS order if it already has one).
    async popupAddService() {
        const appt = this.selectedAppt;
        if (!appt) return;
        // Close first: the popup sits above Odoo's dialog layer.
        this.closeApptPopup();
        try {
            const action = await this.orm.call("salon.appointment", "scheduler_open_add_service", [
                appt.appointment_id,
            ]);
            await this.action.doAction(action, { onClose: () => this.loadData() });
        } catch (e) {
            this.notification.add(this._rpcErrorMessage(e, "Could not add a service."), {
                type: "danger",
                title: "Add Service",
            });
        }
    }

    async popupCheckout() {
        const appt = this.selectedAppt;
        if (!appt) return;
        try {
            const action = await this.orm.call("salon.appointment", "scheduler_checkout", [appt.appointment_id]);
            this.closeApptPopup();
            await this.action.doAction(action);
        } catch (e) {
            this.notification.add(this._rpcErrorMessage(e, "Could not check out the appointment"), {
                type: "danger",
                title: "Checkout failed",
                sticky: true,
            });
            await this.loadData();
        }
    }

    popupOpenAppointment() {
        const appt = this.selectedAppt;
        if (!appt) return;
        this.closeApptPopup();
        this._openAppointmentForm(appt.appointment_id);
    }

    // Double click still goes straight to the full appointment form.
    openAppointment(ev) {
        const rawId = ev.currentTarget.dataset.id;
        this.closeApptPopup();
        const block = this.blockEntry(rawId);
        if (block) {
            this.openBlockForm(block.block_id);
            return;
        }
        this._openAppointmentForm(parseInt(rawId.split("_")[0]));
    }

    _openAppointmentForm(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "salon.appointment",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openPOS() {
        this.action.doAction("point_of_sale.action_pos_config_kanban");
    }
}

registry.category("actions").add("salon_spa_scheduler.scheduler", SalonScheduler);
