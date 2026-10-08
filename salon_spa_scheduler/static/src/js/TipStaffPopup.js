import { Component, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";

export class TipStaffPopup extends Component {
    static template = "salon_spa_scheduler.TipStaffPopup";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        getPayload: { type: Function, optional: true },
        close: { type: Function, optional: true },
    };
    static defaultProps = {
        title: _t("Tip Staff"),
    };

    setup() {
        this.pos = usePos();
        this.state = useState({
            staffList: [],
            selectedStaffId: null,
            tipAmount: 0.0,
        });

        onWillStart(async () => {
            // The beauticians loaded in the POS, so the tip line gets a real
            // salon.staff record that is saved with the order.
            this.state.staffList = (this.pos.models["salon.staff"]?.getAll() || [])
                .slice()
                .sort((a, b) => (a.name || "").localeCompare(b.name || ""));
            if (this.state.staffList.length > 0) {
                this.state.selectedStaffId = this.state.staffList[0].id;
            }
        });
    }

    getPayload() {
        return {
            staff_id: parseInt(this.state.selectedStaffId),
            amount: parseFloat(this.state.tipAmount),
        };
    }

    confirm() {
        if (this.props.getPayload) {
            this.props.getPayload(this.getPayload());
        }
        if (this.props.close) {
            this.props.close();
        }
    }

    cancel() {
        if (this.props.close) {
            this.props.close();
        }
    }
}
