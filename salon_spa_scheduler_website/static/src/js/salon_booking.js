/** @odoo-module **/

// Plain JS (no OWL) step-by-step booking for the public booking page:
// 1. services (and branch, when there is more than one), 2. beautician - or
// anyone available, 3. a free time, 4. the customer's details.
// It stays one form posted to /salon/booking/submit; the steps only decide
// which part of it is shown.
//
// The free times come live from the scheduler (/salon/booking/availability):
// only beauticians with a Planning shift that day, and only times nothing on
// their column covers. They are read again whenever the times step opens,
// every minute while it is open and when the customer comes back to the tab,
// so a time reception has just filled disappears.

// Local calendar date, not toISOString(): that is UTC, which in Qatar
// (UTC+3) still says yesterday until 3 in the morning.
function dateToISO(d) {
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function shiftISO(iso, days) {
    const d = new Date(iso + "T00:00:00");
    d.setDate(d.getDate() + days);
    return dateToISO(d);
}

function formatDay(iso) {
    return new Date(iso + "T00:00:00").toLocaleDateString(undefined, {
        weekday: "short", year: "numeric", month: "short", day: "numeric",
    });
}

const LAST_STEP = 4;
const REFRESH_MS = 60000;

function setupBookingPage() {
    const form = document.getElementById("salon_booking_form");
    const stepper = document.getElementById("salon_stepper");
    const dateLabel = document.getElementById("salon_date_label");
    const prevBtn = document.getElementById("salon_prev_day");
    const nextDayBtn = document.getElementById("salon_next_day");
    const todayBtn = document.getElementById("salon_today_btn");
    const nextFreeBtn = document.getElementById("salon_next_free_btn");
    const hint = document.getElementById("salon_slots_hint");
    const container = document.getElementById("salon_slots_container");
    const dateInput = document.getElementById("salon_booking_date");
    const timeInput = document.getElementById("salon_booking_time");
    const staffInput = document.getElementById("salon_staff_id");
    const backBtn = document.getElementById("salon_back_btn");
    const nextBtn = document.getElementById("salon_next_btn");
    const submitBtn = document.getElementById("salon_submit_btn");
    const warning = document.getElementById("salon_step_warning");
    const summary = document.getElementById("salon_summary");
    const servicesTotal = document.getElementById("salon_services_total");
    if (!form || !stepper || !dateLabel || !container || !nextBtn || !staffInput) {
        return;
    }

    const state = {
        step: 1,
        today: dateToISO(new Date()),
        date: dateToISO(new Date()),
        staffName: "",
        request: 0,
        timer: null,
    };

    // ------------------------------------------------------------------
    // Selection helpers
    // ------------------------------------------------------------------
    function checked(name) {
        return form.querySelector(`input[name="${name}"]:checked`);
    }

    function selectedServices() {
        return Array.from(form.querySelectorAll('input[name="service_ids"]:checked'));
    }

    function servicesInfo() {
        const inputs = selectedServices();
        return {
            ids: inputs.map((el) => el.value),
            names: inputs.map((el) => el.dataset.name),
            price: inputs.reduce((sum, el) => sum + (parseFloat(el.dataset.price) || 0), 0),
            hours: inputs.reduce((sum, el) => sum + (parseFloat(el.dataset.duration) || 0), 0),
        };
    }

    function formatHours(hours) {
        const minutes = Math.round(hours * 60);
        const h = Math.floor(minutes / 60);
        const m = minutes % 60;
        return [h ? `${h} h` : "", m ? `${m} min` : ""].filter(Boolean).join(" ") || "-";
    }

    function renderServicesTotal() {
        const info = servicesInfo();
        servicesTotal.textContent = info.names.length
            ? `${info.names.length} selected - ${formatHours(info.hours)} - QAR ${info.price.toFixed(2)}`
            : "";
    }

    // Beauticians who do every picked service; the rest are hidden.
    function filterStaff() {
        const ids = servicesInfo().ids;
        form.querySelectorAll(".salon-staff-col").forEach((col) => {
            const does = col.dataset.services === "all"
                || ids.every((id) => col.dataset.services.split(",").includes(id));
            col.classList.toggle("d-none", !does);
            const radio = col.querySelector("input");
            if (!does && radio.checked) {
                radio.checked = false;
            }
        });
    }

    function clearPick() {
        dateInput.value = "";
        timeInput.value = "";
        staffInput.value = "";
        state.staffName = "";
    }

    // ------------------------------------------------------------------
    // Steps
    // ------------------------------------------------------------------
    function showWarning(message) {
        warning.textContent = message || "";
        warning.classList.toggle("d-none", !message);
    }

    function validate(step) {
        if (step === 1) {
            if (!checked("branch_id")) {
                return "Please select a branch.";
            }
            if (!selectedServices().length) {
                return "Please select at least one service.";
            }
        } else if (step === 2) {
            if (!checked("staff_choice")) {
                return "Please select a beautician, or Any available.";
            }
        } else if (step === 3) {
            if (!timeInput.value || !staffInput.value) {
                return "Please select an available time.";
            }
        } else if (step === 4) {
            if (!form.customer_name.value.trim()) {
                return "Please enter your name.";
            }
            if (!form.phone.value.trim()) {
                return "Please enter your phone number.";
            }
            if (form.email.value.trim() && !form.email.checkValidity()) {
                return "Please enter a valid email address, or leave it empty.";
            }
        }
        return "";
    }

    function renderSummary() {
        const info = servicesInfo();
        const branch = checked("branch_id");
        const rows = [];
        if (branch && branch.dataset.name) {
            rows.push(["Branch", branch.dataset.name]);
        }
        rows.push(["Services", info.names.join(", ")]);
        rows.push(["Beautician", state.staffName || "-"]);
        rows.push(["When", dateInput.value ? `${formatDay(dateInput.value)}, ${timeInput.value}` : "-"]);
        rows.push(["Duration", formatHours(info.hours)]);
        rows.push(["Total", `QAR ${info.price.toFixed(2)}`]);
        summary.innerHTML = "";
        rows.forEach(([label, value]) => {
            const dt = document.createElement("dt");
            dt.textContent = label;
            const dd = document.createElement("dd");
            dd.textContent = value;
            summary.append(dt, dd);
        });
    }

    function goTo(step, scroll = true) {
        state.step = step;
        showWarning("");
        form.querySelectorAll(".salon-step").forEach((el) => {
            el.classList.toggle("d-none", Number(el.dataset.step) !== step);
        });
        stepper.querySelectorAll("li").forEach((li) => {
            const n = Number(li.dataset.step);
            li.classList.toggle("active", n === step);
            li.classList.toggle("done", n < step);
        });
        backBtn.classList.toggle("invisible", step === 1);
        nextBtn.classList.toggle("d-none", step === LAST_STEP);
        submitBtn.classList.toggle("d-none", step !== LAST_STEP);
        clearInterval(state.timer);
        state.timer = null;
        if (step === 2) {
            filterStaff();
        } else if (step === 3) {
            fetchSlots();
            state.timer = setInterval(() => fetchSlots(true), REFRESH_MS);
        } else if (step === LAST_STEP) {
            renderSummary();
        }
        if (scroll) {
            stepper.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }

    nextBtn.addEventListener("click", () => {
        const problem = validate(state.step);
        if (problem) {
            showWarning(problem);
            return;
        }
        goTo(state.step + 1);
    });

    backBtn.addEventListener("click", () => {
        if (state.step > 1) {
            goTo(state.step - 1);
        }
    });

    // A finished step can be reopened from the indicator.
    stepper.querySelectorAll("li").forEach((li) => {
        li.addEventListener("click", () => {
            const n = Number(li.dataset.step);
            if (n < state.step) {
                goTo(n);
            }
        });
    });

    // Enter in a text field would post the form from any step.
    form.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" && ev.target.tagName === "INPUT" && state.step !== LAST_STEP) {
            ev.preventDefault();
            nextBtn.click();
        }
    });

    form.addEventListener("submit", (ev) => {
        for (let step = 1; step <= LAST_STEP; step++) {
            const problem = validate(step);
            if (problem) {
                ev.preventDefault();
                if (step !== state.step) {
                    goTo(step);
                }
                showWarning(problem);
                return;
            }
        }
    });

    // Picking a beautician is the choice itself: move on to the times.
    form.querySelectorAll('input[name="staff_choice"]').forEach((el) => {
        el.addEventListener("change", () => {
            clearPick();
            if (state.step === 2) {
                goTo(3);
            }
        });
    });
    form.querySelectorAll('input[name="service_ids"]').forEach((el) => {
        el.addEventListener("change", () => {
            renderServicesTotal();
            clearPick();
        });
    });

    // Back on the tab after a while: what was free may not be any more.
    document.addEventListener("visibilitychange", () => {
        if (!document.hidden && state.step === 3) {
            fetchSlots(true);
        }
    });

    // ------------------------------------------------------------------
    // Free times
    // ------------------------------------------------------------------
    function renderDateLabel() {
        dateLabel.textContent = formatDay(state.date);
        prevBtn.disabled = state.date <= state.today;
    }

    function slotButton(staff, slot) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-outline-secondary salon-slot-btn rounded-pill px-3";
        btn.textContent = slot;
        btn.dataset.staffId = staff.id;
        btn.dataset.time = slot;
        if (staffInput.value === String(staff.id) && timeInput.value === slot
                && dateInput.value === state.date) {
            btn.classList.add("selected");
        }
        btn.addEventListener("click", () => {
            container.querySelectorAll("button.salon-slot-btn.selected").forEach((b) => {
                b.classList.remove("selected");
            });
            btn.classList.add("selected");
            dateInput.value = state.date;
            timeInput.value = slot;
            staffInput.value = staff.id;
            state.staffName = staff.name;
            showWarning("");
        });
        return btn;
    }

    function renderSlots(data) {
        container.innerHTML = "";
        nextFreeBtn.classList.add("d-none");
        if (!data.staff.length) {
            hint.textContent = data.message || "No free times on this day.";
            hint.classList.remove("d-none");
            if (data.next_date) {
                nextFreeBtn.textContent = `Next free day: ${formatDay(data.next_date)}`;
                nextFreeBtn.dataset.date = data.next_date;
                nextFreeBtn.classList.remove("d-none");
            }
            return;
        }
        hint.classList.add("d-none");
        data.staff.forEach((staff) => {
            const box = document.createElement("div");
            box.className = "salon-staff-slots";
            const head = document.createElement("div");
            head.className = "d-flex justify-content-between align-items-baseline mb-2";
            const name = document.createElement("span");
            name.className = "fw-bold text-dark";
            name.textContent = staff.name;
            const shift = document.createElement("small");
            shift.className = "text-muted";
            shift.textContent = staff.shift_hint ? `At work ${staff.shift_hint}` : "";
            head.append(name, shift);
            const slots = document.createElement("div");
            slots.className = "d-flex flex-wrap";
            slots.style.gap = "0.5rem";
            staff.slots.forEach((slot) => slots.appendChild(slotButton(staff, slot)));
            box.append(head, slots);
            container.appendChild(box);
        });
    }

    // quiet: a background refresh - keep what is on screen until the answer
    // is in, and only speak up when the customer's pick has been taken.
    async function fetchSlots(quiet = false) {
        renderDateLabel();
        const choice = checked("staff_choice");
        const info = servicesInfo();
        if (!choice || !info.ids.length) {
            container.innerHTML = "";
            hint.textContent = "Please select your services and a beautician first.";
            hint.classList.remove("d-none");
            return;
        }
        if (!quiet) {
            container.innerHTML = "";
            nextFreeBtn.classList.add("d-none");
            hint.textContent = "Loading availability...";
            hint.classList.remove("d-none");
        }
        const request = ++state.request;
        try {
            const params = new URLSearchParams({
                date: state.date,
                service_ids: info.ids.join(","),
            });
            if (choice.value !== "any") {
                params.set("staff_id", choice.value);
            }
            const response = await fetch("/salon/booking/availability?" + params.toString());
            const data = await response.json();
            if (request !== state.request) {
                return; // a newer request (another day) is on its way
            }
            if (data.error) {
                container.innerHTML = "";
                hint.textContent = data.error;
                hint.classList.remove("d-none");
                return;
            }
            if (data.today) {
                state.today = data.today;
            }
            // Is the time the customer picked still free?
            if (timeInput.value && dateInput.value === state.date) {
                const still = data.staff.some((s) => String(s.id) === staffInput.value
                    && s.slots.includes(timeInput.value));
                if (!still) {
                    clearPick();
                    showWarning("The time you picked has just been taken. Please choose another.");
                }
            }
            renderSlots(data);
        } catch {
            if (!quiet) {
                hint.textContent = "Could not load availability. Please try again.";
                hint.classList.remove("d-none");
            }
        }
    }

    function changeDay(iso) {
        if (iso < state.today) {
            return;
        }
        state.date = iso;
        fetchSlots();
    }

    prevBtn.addEventListener("click", () => changeDay(shiftISO(state.date, -1)));
    nextDayBtn.addEventListener("click", () => changeDay(shiftISO(state.date, 1)));
    todayBtn.addEventListener("click", () => changeDay(state.today));
    nextFreeBtn.addEventListener("click", () => changeDay(nextFreeBtn.dataset.date));

    renderDateLabel();
    renderServicesTotal();
    goTo(1, false);
}

// Odoo 19 loads this with the lazy frontend bundle, after DOMContentLoaded
// has already fired - a listener alone would never run.
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupBookingPage);
} else {
    setupBookingPage();
}
