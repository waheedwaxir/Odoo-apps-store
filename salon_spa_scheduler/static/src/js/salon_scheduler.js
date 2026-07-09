/** @odoo-module **/

import { Component, onWillStart, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

function dateToISO(d) { return d.toISOString().slice(0, 10); }

export class SalonScheduler extends Component {
    static template = "salon_spa_scheduler.Scheduler";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            date: dateToISO(new Date()),
            staff: [],
            services: [],
            appointments: [],
            slots: [],
            branches: [],
            selectedBranchId: 0,
            currentTimeTop: -1,
            searchQuery: "",
            searchResults: [],
            selectedCustomer: null,
            showCustomerModal: false,
            customerHistory: [],
        });
        onWillStart(() => this.loadData());

        let timeInterval;
        onMounted(() => {
            timeInterval = setInterval(() => {
                this.updateCurrentTimeLine();
            }, 60000);
        });
        onWillUnmount(() => {
            if (timeInterval) {
                clearInterval(timeInterval);
            }
        });
    }

    async onCustomerSearchInput(ev) {
        const val = ev.target.value;
        this.state.searchQuery = val;
        if (!val || val.length < 2) {
            this.state.searchResults = [];
            return;
        }
        try {
            const results = await this.orm.call(
                "res.partner",
                "search_read",
                [],
                {
                    domain: [
                        "|", "|", ["name", "ilike", val], ["phone", "ilike", val], ["email", "ilike", val]
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
    }

    closeCustomerModal() {
        this.state.showCustomerModal = false;
        this.state.selectedCustomer = null;
        this.state.customerHistory = [];
    }

    async saveCustomerProfile() {
        const cust = this.state.selectedCustomer;
        try {
            await this.orm.write("res.partner", [cust.id], {
                salon_allergies: cust.salon_allergies || "",
                salon_preferences: cust.salon_preferences || ""
            });
            this.notification.add("Customer notes updated successfully!", { type: "success" });
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
        this.state.startHour = data.start_hour || 8;
        this.state.endHour = data.end_hour || 22;
        this.state.slots = this.makeSlots(data.date, data.start_hour, data.end_hour, data.slot_minutes);
        this.updateCurrentTimeLine();
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

        const slotHeight = 40;
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
        return this.loadData();
    }

    nextDay() {
        const d = new Date(this.state.date + "T00:00:00");
        d.setDate(d.getDate() + 1);
        this.state.date = dateToISO(d);
        return this.loadData();
    }

    today() {
        this.state.date = dateToISO(new Date());
        return this.loadData();
    }

    formattedDate() {
        const options = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' };
        const d = new Date(this.state.date + "T00:00:00");
        return d.toLocaleDateString(undefined, options);
    }

    async onDateChange(ev) {
        this.state.date = ev.target.value;
        await this.loadData();
    }

    quickCreate(ev) {
        const cell = ev.currentTarget;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "salon.appointment",
            views: [[false, "form"]],
            target: "current",
            context: {
                default_staff_id: parseInt(cell.dataset.staffId),
                default_start_datetime: cell.dataset.start,
            }
        });
    }

    dragStart(ev) {
        ev.dataTransfer.setData("appointment_id", ev.currentTarget.dataset.id);
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
        const newHeight = Math.max(40, this.resizeStartHeight + deltaY);
        const apptBlock = document.querySelector(`.appt_block[data-id="${this.resizingAppt}"]`);
        if (apptBlock) {
            apptBlock.style.height = `${newHeight}px`;
        }
    }

    async endResize(ev) {
        document.removeEventListener('mousemove', this._onMouseMove);
        document.removeEventListener('mouseup', this._onMouseUp);
        
        if (!this.resizingAppt) return;
        const apptBlock = document.querySelector(`.appt_block[data-id="${this.resizingAppt}"]`);
        if (apptBlock) {
            // Calculate new duration based on height. 40px = 1 slot (15 mins)
            // Height = duration * 4 * 40 - 2 => duration = (Height + 2) / 160
            let newHeight = apptBlock.offsetHeight;
            let durationHours = (newHeight + 2) / 160.0;
            // Round to nearest 15 mins (0.25 hours)
            durationHours = Math.max(0.25, Math.round(durationHours * 4) / 4);
            
            try {
                await this.orm.call("salon.appointment", "scheduler_resize", [this.resizingAppt, durationHours]);
                await this.loadData();
            } catch (e) {
                this.notification.add(e.message || "Could not resize appointment", { type: "danger" });
                await this.loadData(); // Revert visual change
            }
        }
        this.resizingAppt = null;
    }

    async dropAppointment(ev) {
        const appointmentId = ev.dataTransfer.getData("appointment_id");
        if (!appointmentId) return;
        const cell = ev.currentTarget;
        try {
            await this.orm.call("salon.appointment", "scheduler_move", [appointmentId, cell.dataset.staffId, cell.dataset.start]);
            await this.loadData();
        } catch (e) {
            this.notification.add(e.message || "Could not move appointment", { type: "danger" });
        }
    }

    async markArrived(ev) {
        const appointmentId = ev.currentTarget.dataset.id;
        if (!appointmentId) return;
        try {
            await this.orm.call("salon.appointment", "scheduler_mark_arrived", [appointmentId]);
            await this.loadData();
        } catch (e) {
            this.notification.add(e.message || "Could not mark as arrived", { type: "danger" });
        }
    }

    openAppointment(ev) {
        const rawId = ev.currentTarget.dataset.id;
        const id = parseInt(rawId.split("_")[0]);
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
