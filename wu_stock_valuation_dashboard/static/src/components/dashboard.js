/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState, onMounted, useRef, onWillDestroy } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { DateTimeInput } from "@web/core/datetime/datetime_input";

export class StockValuationDashboard extends Component {
    static components = { DateTimeInput };
    
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            data: {
                total_value: 0,
                total_sales_value: 0,
                total_qty: 0,
                total_products: 0,
                low_stock_count: 0,
                incoming: 0,
                outgoing: 0,
                internal_transfers: 0,
                returns: 0,
                currency_symbol: '$',
                value_by_category: [],
                value_by_warehouse: [],
                value_by_cost_method: [],
                value_by_automation: [],
                abc_analysis: [],
                aging_analysis: [],
                profit_by_category: [],
                top_products: [],
                trend: [],
                movements: [],
                timeframe: 'daily',
                notifications: [],
                insights: []
            },
            filters: {
                companies: [],
                warehouses: [],
                categories: []
            },
            selectedCompanyId: false,
            selectedWarehouseId: false,
            selectedCategoryId: false,
            dateFrom: '',
            dateTo: '',
            dateRangeMode: 'all',
            timeframe: 'daily',
            isLoading: true,
            autoRefreshEnabled: false
        });

        this.categoryChartRef = useRef("categoryChart");
        this.warehouseChartRef = useRef("warehouseChart");
        this.movementChartRef = useRef("movementChart");
        this.trendChartRef = useRef("trendChart");
        this.abcChartRef = useRef("abcChart");
        this.agingChartRef = useRef("agingChart");
        this.profitChartRef = useRef("profitChart");
        this.costSalesChartRef = useRef("costSalesChart");
        this.costMethodChartRef = useRef("costMethodChart");
        
        this.refreshInterval = null;

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            const filters = await this.orm.call("stock.valuation.dashboard", "get_filters_data", []);
            if (filters) {
                this.state.filters = filters;
                this.state.selectedCompanyId = filters.default_company_id;
            }
            await this.fetchData();
        });

        onMounted(() => {
            this.renderCharts();
        });

        onWillDestroy(() => {
            if (this.refreshInterval) clearInterval(this.refreshInterval);
        });
    }

    async fetchData() {
        this.state.isLoading = true;
        const data = await this.orm.call(
            "stock.valuation.dashboard", 
            "get_dashboard_data", 
            [], 
            {
                timeframe: this.state.timeframe,
                company_id: this.state.selectedCompanyId || false,
                warehouse_id: this.state.selectedWarehouseId || false,
                category_id: this.state.selectedCategoryId || false,
                date_from: this.state.dateFrom || false,
                date_to: this.state.dateTo || false
            }
        );
        if (data) {
            this.state.data = data;
        }
        this.state.isLoading = false;
    }

    async refreshDashboard() {
        await this.fetchData();
        // Wait for Owl to patch the DOM after isLoading becomes false
        setTimeout(() => {
            this.renderCharts();
        }, 50);
    }
    
    async onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value;
        this.state.dateRangeMode = 'custom';
        await this.refreshDashboard();
    }

    async onDateToChange(ev) {
        this.state.dateTo = ev.target.value;
        this.state.dateRangeMode = 'custom';
        await this.refreshDashboard();
    }

    get dateFromObj() {
        return this.state.dateFrom ? luxon.DateTime.fromISO(this.state.dateFrom) : false;
    }

    get dateToObj() {
        return this.state.dateTo ? luxon.DateTime.fromISO(this.state.dateTo) : false;
    }

    async onDateFromChangeObj(d) {
        this.state.dateFrom = d ? d.toISODate() : '';
        this.state.dateRangeMode = 'custom';
        await this.refreshDashboard();
    }

    async onDateToChangeObj(d) {
        this.state.dateTo = d ? d.toISODate() : '';
        this.state.dateRangeMode = 'custom';
        await this.refreshDashboard();
    }

    async onDateRangeChange(ev) {
        const mode = ev.target.value;
        this.state.dateRangeMode = mode;
        
        const today = new Date();
        const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
        
        if (mode === 'all') {
            this.state.dateFrom = '';
            this.state.dateTo = '';
        } else if (mode === 'today') {
            this.state.dateFrom = this.formatDate(startOfToday);
            this.state.dateTo = this.formatDate(startOfToday);
        } else if (mode === 'this_week') {
            const first = today.getDate() - today.getDay(); 
            const firstDay = new Date(today.setDate(first));
            this.state.dateFrom = this.formatDate(firstDay);
            this.state.dateTo = this.formatDate(new Date());
        } else if (mode === 'this_month') {
            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
            this.state.dateFrom = this.formatDate(firstDay);
            this.state.dateTo = this.formatDate(new Date());
        } else if (mode === 'last_month') {
            const firstDay = new Date(today.getFullYear(), today.getMonth() - 1, 1);
            const lastDay = new Date(today.getFullYear(), today.getMonth(), 0);
            this.state.dateFrom = this.formatDate(firstDay);
            this.state.dateTo = this.formatDate(lastDay);
        } else if (mode === 'this_year') {
            const firstDay = new Date(today.getFullYear(), 0, 1);
            this.state.dateFrom = this.formatDate(firstDay);
            this.state.dateTo = this.formatDate(new Date());
        }
        
        if (mode !== 'custom') {
            await this.refreshDashboard();
        }
    }

    formatDate(date) {
        const d = new Date(date);
        let month = '' + (d.getMonth() + 1);
        let day = '' + d.getDate();
        const year = d.getFullYear();

        if (month.length < 2) month = '0' + month;
        if (day.length < 2) day = '0' + day;

        return [year, month, day].join('-');
    }

    getPercentChange(current, previous) {
        if (!previous && current) return 100;
        if (!previous && !current) return 0;
        return (((current - previous) / Math.abs(previous)) * 100).toFixed(1);
    }

    async onCompanyChange(ev) {
        this.state.selectedCompanyId = parseInt(ev.target.value) || false;
        this.state.selectedWarehouseId = false;
        this.state.selectedCategoryId = false;
        await this.refreshDashboard();
    }

    async onWarehouseChange(ev) {
        this.state.selectedWarehouseId = parseInt(ev.target.value) || false;
        await this.refreshDashboard();
    }

    async onCategoryChange(ev) {
        this.state.selectedCategoryId = parseInt(ev.target.value) || false;
        await this.refreshDashboard();
    }

    async onFilterChange() {
        await this.refreshDashboard();
    }

    async changeTimeframe(tf) {
        if (this.state.timeframe === tf) return;
        this.state.timeframe = tf;
        await this.refreshDashboard();
    }


    openProduct(productId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: _t('Product'),
            res_model: 'product.product',
            res_id: productId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openInventory(type) {
        let domain = [];
        let model = "";
        let name = "";
        
        // Base domain filters based on active dashboard selections
        const companyId = this.state.selectedCompanyId;
        const categoryId = this.state.selectedCategoryId;
        const warehouseId = this.state.selectedWarehouseId;

        if (type === 'products') {
            model = 'product.product';
            name = 'Products';
            domain = [['is_storable', '=', true]];
            if (companyId) domain.push(['company_id', 'in', [companyId, false]]);
            if (categoryId) domain.push(['categ_id', 'child_of', categoryId]);
        } else if (type === 'low_stock') {
            model = 'product.product';
            name = 'Low Stock Products';
            domain = [['is_storable', '=', true], ['qty_available', '<', 10]];
            if (companyId) domain.push(['company_id', 'in', [companyId, false]]);
            if (categoryId) domain.push(['categ_id', 'child_of', categoryId]);
        } else if (type === 'valuation') {
            model = 'stock.move';
            name = 'Inventory Valuation';
            domain = [];
            if (companyId) domain.push(['company_id', '=', companyId]);
            if (categoryId) domain.push(['product_id.categ_id', 'child_of', categoryId]);
        } else if (type === 'quantity') {
            model = 'stock.quant';
            name = 'Stock Quantities';
            domain = [['location_id.usage', '=', 'internal']];
            if (companyId) domain.push(['company_id', '=', companyId]);
            if (categoryId) domain.push(['product_id.categ_id', 'child_of', categoryId]);
            if (warehouseId) domain.push(['location_id.warehouse_id', '=', warehouseId]);
        } else if (type === 'incoming') {
            model = 'stock.move';
            name = 'Incoming Moves';
            domain = [['picking_type_id.code', '=', 'incoming'], ['state', 'in', ['confirmed', 'assigned', 'partially_available']]];
            if (companyId) domain.push(['company_id', '=', companyId]);
            if (categoryId) domain.push(['product_id.categ_id', 'child_of', categoryId]);
            if (warehouseId) domain.push(['picking_type_id.warehouse_id', '=', warehouseId]);
        } else if (type === 'outgoing') {
            model = 'stock.move';
            name = 'Outgoing Moves';
            domain = [['picking_type_id.code', '=', 'outgoing'], ['state', 'in', ['confirmed', 'assigned', 'partially_available']]];
            if (companyId) domain.push(['company_id', '=', companyId]);
            if (categoryId) domain.push(['product_id.categ_id', 'child_of', categoryId]);
            if (warehouseId) domain.push(['picking_type_id.warehouse_id', '=', warehouseId]);
        } else if (type === 'internal') {
            model = 'stock.move';
            name = 'Internal Transfers';
            domain = [['picking_type_id.code', '=', 'internal'], ['state', 'in', ['confirmed', 'assigned', 'partially_available']]];
            if (companyId) domain.push(['company_id', '=', companyId]);
            if (categoryId) domain.push(['product_id.categ_id', 'child_of', categoryId]);
            if (warehouseId) domain.push(['picking_type_id.warehouse_id', '=', warehouseId]);
                } else if (type === 'adjustments') {
            model = 'stock.move';
            name = _t('Inventory Adjustments');
            domain = [['state', '=', 'done'], '|', ['location_id.usage', '=', 'inventory'], ['location_dest_id.usage', '=', 'inventory']];
            if (companyId) domain.push(['company_id', '=', companyId]);
            if (categoryId) domain.push(['product_id.categ_id', 'child_of', categoryId]);
        } else if (type === 'cogs') {
            model = 'stock.move';
            name = _t('Exact COGS (Shipped)');
            domain = [['state', '=', 'done'], ['location_dest_id.usage', '=', 'customer']];
            if (companyId) domain.push(['company_id', '=', companyId]);
            if (categoryId) domain.push(['product_id.categ_id', 'child_of', categoryId]);
        } else if (type === 'returns') {
            model = 'stock.move';
            name = 'Returns';
            domain = [['origin_returned_move_id', '!=', false], ['state', 'in', ['confirmed', 'assigned', 'partially_available']]];
            if (companyId) domain.push(['company_id', '=', companyId]);
            if (categoryId) domain.push(['product_id.categ_id', 'child_of', categoryId]);
            if (warehouseId) domain.push(['picking_type_id.warehouse_id', '=', warehouseId]);
        }

        if (model) {
            this.action.doAction({
                type: 'ir.actions.act_window',
                name: name,
                res_model: model,
                views: [[false, 'list'], [false, 'form']],
                domain: domain,
                target: 'current',
            });
        }
    }

    renderCharts() {
        if (this.state.isLoading) return;

        const pastelColors = ['#5b8ff9', '#5ad8a6', '#5d7092', '#f6bd16', '#e8684a', '#6dc8ec', '#9270CA', '#ff9d4d', '#269a99', '#ff99c3'];

        // 1. Category Chart (Doughnut)
        if (this.categoryChartRef.el) {
            if (this.categoryChart) this.categoryChart.destroy();
            this.categoryChart = new Chart(this.categoryChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: this.state.data.value_by_category.map(d => d.label),
                    datasets: [{
                        data: this.state.data.value_by_category.map(d => d.value),
                        backgroundColor: pastelColors,
                        borderWidth: 0,
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, legend: { display: false }, cutoutPercentage: 70 }
            });
        }

        // 2. Warehouse Chart (Bar)
        if (this.warehouseChartRef.el) {
            if (this.warehouseChart) this.warehouseChart.destroy();
            this.warehouseChart = new Chart(this.warehouseChartRef.el, {
                type: 'bar',
                data: {
                    labels: this.state.data.value_by_warehouse.map(d => d.label),
                    datasets: [{
                        data: this.state.data.value_by_warehouse.map(d => d.value),
                        backgroundColor: ['#5b8ff9', '#5ad8a6', '#6dc8ec', '#e8684a', '#5d7092'],
                        borderRadius: 4,
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, legend: { display: false }, scales: { x: { gridLines: { display: false } }, y: { beginAtZero: true, gridLines: { borderDash: [2, 4] } } } }
            });
        }

        // 3. Movement Chart (Line with dots)
        if (this.movementChartRef.el) {
            if (this.movementChart) this.movementChart.destroy();
            this.movementChart = new Chart(this.movementChartRef.el, {
                type: 'line',
                data: {
                    labels: this.state.data.movements.map(d => d.label),
                    datasets: [
                        { label: _t('Incoming'), data: this.state.data.movements.map(d => d.incoming), borderColor: '#5ad8a6', backgroundColor: '#5ad8a6', fill: false, pointRadius: 4 },
                        { label: _t('Outgoing'), data: this.state.data.movements.map(d => d.outgoing), borderColor: '#e8684a', backgroundColor: '#e8684a', fill: false, pointRadius: 4 }
                    ]
                },
                options: { responsive: true, maintainAspectRatio: false, legend: { position: 'top', align: 'end' }, scales: { x: { gridLines: { display: false } }, y: { gridLines: { borderDash: [2, 4] } } } }
            });
        }

        // 4. Trend Chart (Line filled)
        if (this.trendChartRef.el) {
            if (this.trendChart) this.trendChart.destroy();
            this.trendChart = new Chart(this.trendChartRef.el, {
                type: 'line',
                data: {
                    labels: this.state.data.trend.map(d => d.label),
                    datasets: [{
                        label: _t('Inventory Value'),
                        data: this.state.data.trend.map(d => d.value),
                        borderColor: '#9270CA',
                        backgroundColor: 'rgba(146, 112, 202, 0.2)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 3
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, legend: { display: false }, scales: { x: { gridLines: { display: false } }, y: { gridLines: { borderDash: [2, 4] } } } }
            });
        }
        
        // 5. ABC Analysis Chart (Pyramid / Doughnut as fallback)
        if (this.abcChartRef.el) {
            if (this.abcChart) this.abcChart.destroy();
            this.abcChart = new Chart(this.abcChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: this.state.data.abc_analysis.map(d => d.label),
                    datasets: [{
                        data: this.state.data.abc_analysis.map(d => d.value),
                        backgroundColor: ['#28c76f', '#ff9f43', '#ea5455'],
                        borderWidth: 0,
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, legend: { display: false } }
            });
        }

        // 6. Aging Analysis Chart (Doughnut)
        if (this.agingChartRef.el) {
            if (this.agingChart) this.agingChart.destroy();
            this.agingChart = new Chart(this.agingChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: this.state.data.aging_analysis.map(d => d.label),
                    datasets: [{
                        data: this.state.data.aging_analysis.map(d => d.value),
                        backgroundColor: ['#5b8ff9', '#5ad8a6', '#f6bd16', '#e8684a'],
                        borderWidth: 0,
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, legend: { display: false }, cutoutPercentage: 60 }
            });
        }
        
        // 7. Cost vs Sales (Bar)
        if (this.costSalesChartRef.el) {
            if (this.costSalesChart) this.costSalesChart.destroy();
            this.costSalesChart = new Chart(this.costSalesChartRef.el, {
                type: 'bar',
                data: {
                    labels: this.state.data.top_products.slice(0, 5).map(d => d.name.substring(0, 10)),
                    datasets: [
                        { label: _t('Cost Value'), data: this.state.data.top_products.slice(0, 5).map(d => d.total_cost), backgroundColor: '#5b8ff9' },
                        { label: _t('Sales Value'), data: this.state.data.top_products.slice(0, 5).map(d => d.total_sales), backgroundColor: '#9270CA' }
                    ]
                },
                options: { responsive: true, maintainAspectRatio: false, legend: { position: 'top' }, scales: { x: { gridLines: { display: false } }, y: { beginAtZero: true, gridLines: { borderDash: [2, 4] } } } }
            });
        }

        // 8. Profitability Chart
        if (this.profitChartRef.el) {
            if (this.profitChart) this.profitChart.destroy();
            this.profitChart = new Chart(this.profitChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: this.state.data.profit_by_category.map(d => d.label),
                    datasets: [{
                        data: this.state.data.profit_by_category.map(d => d.value),
                        backgroundColor: pastelColors,
                        borderWidth: 0,
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, legend: { display: false }, cutoutPercentage: 60 }
            });
        }

        // 9. Cost Method Breakdown (Doughnut)
        if (this.costMethodChartRef.el) {
            if (this.costMethodChart) this.costMethodChart.destroy();
            this.costMethodChart = new Chart(this.costMethodChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: this.state.data.value_by_cost_method.map(d => d.label),
                    datasets: [{
                        data: this.state.data.value_by_cost_method.map(d => d.value),
                        backgroundColor: ['#29b8c2', '#a05bf2', '#f6bd16'],
                        borderWidth: 0,
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, legend: { display: false }, cutoutPercentage: 70 }
            });
        }
    }
}

StockValuationDashboard.template = "wu_stock_valuation_dashboard.Dashboard";
registry.category("actions").add("wu_stock_valuation_dashboard.dashboard", StockValuationDashboard);
