/** @odoo-module **/
import { Component, onMounted, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class AttendanceMap extends Component {
    static template = "wu_hr_employee360.AttendanceMap";
    static props = {
        points: { type: Array, required: true },
    };

    setup() {
        this.mapRef = useRef("mapContainer");

        onMounted(() => {
            this.initLeafletMap();
        });
    }

    initLeafletMap() {
        if (!this.mapRef.el) return;
        if (window.L && this.props.points && this.props.points.length > 0) {
            this.mapRef.el.innerHTML = "";
            const branch = this.props.points.find(p => p.type === 'branch') || { lat: 25.276987, lng: 55.296249 };
            const map = window.L.map(this.mapRef.el).setView([branch.lat, branch.lng], 14);

            window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);

            // Draw Geofence Radius Circle (500m)
            window.L.circle([branch.lat, branch.lng], {
                color: '#3b82f6',
                fillColor: '#3b82f6',
                fillOpacity: 0.15,
                radius: branch.radius || 500
            }).addTo(map).bindPopup("<b>HQ Office Geofence Boundary</b><br>Radius: 500 Meters");

            // Add Employee Check-In Pins
            this.props.points.forEach(pt => {
                if (pt.type === 'branch') return;
                const pinColor = pt.is_breach ? 'red' : 'green';
                const marker = window.L.circleMarker([pt.lat, pt.lng], {
                    color: pt.is_breach ? '#ef4444' : '#10b981',
                    fillColor: pt.is_breach ? '#ef4444' : '#10b981',
                    fillOpacity: 0.8,
                    radius: 8
                }).addTo(map);

                marker.bindPopup(`
                    <div style="font-size:12px;">
                        <b>${pt.name}</b><br>
                        Time: ${pt.time}<br>
                        Status: <b style="color:${pt.is_breach ? 'red' : 'green'}">${pt.is_breach ? 'GEOFENCE BREACH ALERT' : 'Verified Within Boundary'}</b>
                        ${pt.is_breach ? `<br><small class="text-danger">${pt.breach_msg || ''}</small>` : ''}
                    </div>
                `);
            });
        }
    }
}
