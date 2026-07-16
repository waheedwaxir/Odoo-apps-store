/** @odoo-module **/
import { Component, onMounted, onWillUpdateProps, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class ChartManager extends Component {
    static template = "wu_hr_employee360.ChartPanel";
    static props = {
        title: { type: String, required: true },
        type: { type: String, required: true }, // 'bar', 'donut', 'line', 'pie'
        data: { type: Object, required: true },
        onSliceClick: { type: Function, optional: true },
    };

    setup() {
        this.chartRef = useRef("chartContainer");
        this.chartInstance = null;

        onMounted(() => {
            this.renderChart();
        });

        onWillUpdateProps((nextProps) => {
            if (JSON.stringify(nextProps.data) !== JSON.stringify(this.props.data)) {
                setTimeout(() => this.renderChart(), 50);
            }
        });
    }

    renderChart() {
        if (!this.chartRef.el) return;
        if (this.chartInstance && typeof this.chartInstance.destroy === 'function') {
            this.chartInstance.destroy();
        }

        const labels = Object.keys(this.props.data || {});
        const seriesData = Object.values(this.props.data || {});

        // Use native window.ApexCharts if loaded or fallback HTML canvas render
        if (window.ApexCharts) {
            const options = {
                chart: {
                    type: this.props.type === 'donut' ? 'donut' : 'bar',
                    height: 280,
                    toolbar: { show: false },
                    events: {
                        dataPointSelection: (event, chartContext, config) => {
                            const selectedLabel = labels[config.dataPointIndex];
                            if (this.props.onSliceClick && selectedLabel) {
                                this.props.onSliceClick(selectedLabel);
                            }
                        }
                    }
                },
                series: this.props.type === 'donut' ? seriesData : [{ name: 'Headcount', data: seriesData }],
                labels: labels,
                xaxis: { categories: labels },
                colors: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#64748b', '#ef4444'],
                plotOptions: {
                    bar: { borderRadius: 6, horizontal: false, columnWidth: '55%' }
                },
                dataLabels: { enabled: false },
                legend: { position: 'bottom', fontSize: '12px' }
            };
            this.chartInstance = new window.ApexCharts(this.chartRef.el, options);
            this.chartInstance.render();
        } else {
            // Fallback simple visual bar renderer if ApexCharts CDN is not yet injected
            this.chartRef.el.innerHTML = "";
            const wrapper = document.createElement("div");
            wrapper.className = "d-flex flex-column gap-2 py-2";
            const maxVal = Math.max(...seriesData, 1);
            labels.forEach((label, i) => {
                const val = seriesData[i];
                const pct = Math.round((val / maxVal) * 100);
                wrapper.innerHTML += `
                    <div class="d-flex align-items-center justify-content-between text-muted fs-7" style="cursor: pointer;" data-slice="${label}">
                        <span class="text-truncate" style="max-width: 130px;" title="${label}">${label}</span>
                        <div class="flex-grow-1 mx-2 bg-light rounded" style="height: 10px;">
                            <div class="bg-primary rounded" style="width: ${pct}%; height: 100%;"></div>
                        </div>
                        <span class="fw-bold text-dark">${val}</span>
                    </div>
                `;
            });
            wrapper.querySelectorAll("[data-slice]").forEach(el => {
                el.addEventListener("click", () => {
                    if (this.props.onSliceClick) this.props.onSliceClick(el.getAttribute("data-slice"));
                });
            });
            this.chartRef.el.appendChild(wrapper);
        }
    }
}
