from odoo import models, api, fields
from datetime import datetime, timedelta
import calendar
from dateutil.relativedelta import relativedelta

class StockValuationDashboard(models.AbstractModel):
    _name = 'stock.valuation.dashboard'
    _description = 'Stock Valuation Dashboard API'

    @api.model
    def get_filters_data(self):
        companies = self.env['res.company'].search_read([], ['id', 'name'])
        warehouses = self.env['stock.warehouse'].search_read([], ['id', 'name', 'company_id'])
        
        category_fields = ['id', 'name']
        if 'company_id' in self.env['product.category']._fields:
            category_fields.append('company_id')
        categories = self.env['product.category'].search_read([], category_fields)



        return {
            'companies': companies,
            'warehouses': warehouses,
            'categories': categories,
            'default_company_id': self.env.company.id,
        }

    @api.model
    def get_dashboard_data(self, timeframe='daily', company_id=None, warehouse_id=None, category_id=None, date_from=None, date_to=None):
        company = self.env['res.company'].browse(company_id) if company_id else self.env.company
        company_id = company.id
        currency_symbol = company.currency_id.symbol or '$'

        # Previous Period calculation
        prev_date_from = None
        prev_date_to = None
        
        if date_from and date_to:
            dt_from = datetime.strptime(date_from, '%Y-%m-%d')
            dt_to = datetime.strptime(date_to, '%Y-%m-%d')
            delta = (dt_to - dt_from).days
            prev_dt_to = dt_from - timedelta(days=1)
            prev_dt_from = prev_dt_to - timedelta(days=delta)
            prev_date_from = prev_dt_from.strftime('%Y-%m-%d')
            prev_date_to = prev_dt_to.strftime('%Y-%m-%d')
        else:
            # Default comparison if no dates given (All Time vs 30 days ago)
            prev_date_to = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')

        categ_ids = self.env['product.category'].search([('id', 'child_of', category_id)]).ids if category_id else []
        move_join = " JOIN product_product pp ON stock_move.product_id = pp.id JOIN product_template pt ON pp.product_tmpl_id = pt.id" if category_id else ""
        move_where_cat = " AND pt.categ_id IN %s" if category_id else ""
        
        domain_move = [('state', '=', 'done'), ('company_id', '=', company_id)]
        if category_id:
            domain_move.append(('product_id.categ_id', 'child_of', category_id))
            
        # 1. Total Inventory Value (Current valuation from stock.move)
        # We sum all moves up to date_to if provided
        query_move_val = f"""
            SELECT SUM(CASE WHEN is_out = TRUE THEN -value ELSE value END) 
            FROM stock_move {move_join}
            WHERE stock_move.state = 'done' AND (is_in = TRUE OR is_out = TRUE) AND stock_move.company_id = %s {move_where_cat}
        """
        params_move_val = [company_id]
        if category_id:
            params_move_val.append(tuple(categ_ids))
        if date_to:
            query_move_val += " AND DATE(stock_move.date) <= %s"
            params_move_val.append(date_to)
            
        self.env.cr.execute(query_move_val, tuple(params_move_val))
        total_value = self.env.cr.fetchone()[0] or 0.0

        # Previous total value
        query_prev_val = f"""
            SELECT SUM(CASE WHEN is_out = TRUE THEN -value ELSE value END) 
            FROM stock_move {move_join}
            WHERE stock_move.state = 'done' AND (is_in = TRUE OR is_out = TRUE) AND stock_move.company_id = %s {move_where_cat} AND DATE(stock_move.date) <= %s
        """
        params_prev_val = [company_id]
        if category_id:
            params_prev_val.append(tuple(categ_ids))
        params_prev_val.append(prev_date_to)
        self.env.cr.execute(query_prev_val, tuple(params_prev_val))
        prev_total_value = self.env.cr.fetchone()[0] or 0.0

        # 2. Total Stock Quantity (from stock.quant internal locations)
        query_quant = f"""
            SELECT SUM(sq.quantity) 
            FROM stock_quant sq
            JOIN stock_location sl ON sq.location_id = sl.id
            { "JOIN product_product pp ON sq.product_id = pp.id JOIN product_template pt ON pp.product_tmpl_id = pt.id" if category_id else "" }
            WHERE sl.usage = 'internal' AND sq.company_id = %s { "AND pt.categ_id IN %s" if category_id else "" }
        """
        params_quant = [company_id]
        if category_id:
            params_quant.append(tuple(categ_ids))
        if warehouse_id:
            query_quant += " AND sl.warehouse_id = %s"
            params_quant.append(warehouse_id)
            
        self.env.cr.execute(query_quant, tuple(params_quant))
        total_qty = self.env.cr.fetchone()[0] or 0.0

                # 3. Total Products & Low Stock
        domain_prod = ['|', ('type', '=', 'product'), ('is_storable', '=', True)]
        if category_id:
            domain_prod = ['&', ('categ_id', 'child_of', category_id), '|', ('type', '=', 'product'), ('is_storable', '=', True)]
        total_products = self.env['product.product'].search_count(domain_prod)
        
        domain_prod_prev = domain_prod.copy()
        if prev_date_to:
            domain_prod_prev.append(('create_date', '<=', prev_date_to))
        prev_total_products = self.env['product.product'].search_count(domain_prod_prev)
        
        query_low_stock = """
            SELECT COUNT(id) FROM (
                SELECT pp.id, SUM(sq.quantity) as qty
                FROM product_product pp
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN stock_quant sq ON sq.product_id = pp.id AND sq.company_id = %s
                LEFT JOIN stock_location sl ON sq.location_id = sl.id AND sl.usage = 'internal'
                WHERE (pt.is_storable = TRUE OR pt.type = 'product')
        """
        params_low_stock = [company_id]
        if warehouse_id:
            query_low_stock += " AND sl.warehouse_id = %s"
            params_low_stock.append(warehouse_id)
        if category_id:
            query_low_stock += " AND pt.categ_id IN %s"
            params_low_stock.append(tuple(categ_ids))
            
        query_low_stock += """
                GROUP BY pp.id
            ) as stock_grouped
            WHERE qty < 10 OR qty IS NULL
        """
        self.env.cr.execute(query_low_stock, tuple(params_low_stock))
        low_stock_count = self.env.cr.fetchone()[0] or 0

        # Exact historical low stock count
        query_prev_low = f'''
            SELECT COUNT(id) FROM (
                SELECT pp.id, SUM(CASE WHEN sm.is_in = TRUE THEN sm.product_uom_qty WHEN sm.is_out = TRUE THEN -sm.product_uom_qty ELSE 0 END) as qty
                FROM product_product pp
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN stock_move sm ON sm.product_id = pp.id AND sm.state = 'done' AND sm.company_id = %s AND DATE(sm.date) <= %s
                WHERE (pt.is_storable = TRUE OR pt.type = 'product') {move_where_cat}
                GROUP BY pp.id
            ) as stock_grouped
            WHERE qty < 10 OR qty IS NULL
        '''
        params_prev_low = [company_id, prev_date_to]
        if category_id:
            params_prev_low.append(tuple(categ_ids))
            
        self.env.cr.execute(query_prev_low, tuple(params_prev_low))
        prev_low_stock_count = self.env.cr.fetchone()[0] or 0

        # 4. Incoming, Outgoing, Internal & Returns Counts
        domain_in = [('picking_type_id.code', '=', 'incoming'), ('state', 'in', ['confirmed', 'assigned', 'partially_available']), ('company_id', '=', company_id)]
        domain_out = [('picking_type_id.code', '=', 'outgoing'), ('state', 'in', ['confirmed', 'assigned', 'partially_available']), ('company_id', '=', company_id)]
        domain_int = [('picking_type_id.code', '=', 'internal'), ('state', 'in', ['confirmed', 'assigned', 'partially_available']), ('company_id', '=', company_id)]
        domain_ret = [('origin_returned_move_id', '!=', False), ('state', 'in', ['confirmed', 'assigned', 'partially_available']), ('company_id', '=', company_id)]
        
        if category_id:
            domain_in.append(('product_id.categ_id', 'child_of', category_id))
            domain_out.append(('product_id.categ_id', 'child_of', category_id))
            domain_int.append(('product_id.categ_id', 'child_of', category_id))
            domain_ret.append(('product_id.categ_id', 'child_of', category_id))

        if warehouse_id:
            domain_in.append(('picking_type_id.warehouse_id', '=', warehouse_id))
            domain_out.append(('picking_type_id.warehouse_id', '=', warehouse_id))
            domain_int.append(('picking_type_id.warehouse_id', '=', warehouse_id))
            domain_ret.append(('picking_type_id.warehouse_id', '=', warehouse_id))
            
        if date_from:
            domain_in.append(('date', '>=', date_from))
            domain_out.append(('date', '>=', date_from))
            domain_int.append(('date', '>=', date_from))
            domain_ret.append(('date', '>=', date_from))
            
        if date_to:
            domain_in.append(('date', '<=', date_to))
            domain_out.append(('date', '<=', date_to))
            domain_int.append(('date', '<=', date_to))
            domain_ret.append(('date', '<=', date_to))
            
        incoming = self.env['stock.move'].search_count(domain_in)
        outgoing = self.env['stock.move'].search_count(domain_out)
        internal_transfers = self.env['stock.move'].search_count(domain_int)
        returns = self.env['stock.move'].search_count(domain_ret)

        # Previous counts
        domain_in_prev = [('picking_type_id.code', '=', 'incoming'), ('state', 'in', ['confirmed', 'assigned', 'partially_available']), ('company_id', '=', company_id)]
        domain_out_prev = [('picking_type_id.code', '=', 'outgoing'), ('state', 'in', ['confirmed', 'assigned', 'partially_available']), ('company_id', '=', company_id)]
        domain_int_prev = [('picking_type_id.code', '=', 'internal'), ('state', 'in', ['confirmed', 'assigned', 'partially_available']), ('company_id', '=', company_id)]
        domain_ret_prev = [('origin_returned_move_id', '!=', False), ('state', 'in', ['confirmed', 'assigned', 'partially_available']), ('company_id', '=', company_id)]
        
        if category_id:
            domain_in_prev.append(('product_id.categ_id', 'child_of', category_id))
            domain_out_prev.append(('product_id.categ_id', 'child_of', category_id))
            domain_int_prev.append(('product_id.categ_id', 'child_of', category_id))
            domain_ret_prev.append(('product_id.categ_id', 'child_of', category_id))

        if warehouse_id:
            domain_in_prev.append(('picking_type_id.warehouse_id', '=', warehouse_id))
            domain_out_prev.append(('picking_type_id.warehouse_id', '=', warehouse_id))
            domain_int_prev.append(('picking_type_id.warehouse_id', '=', warehouse_id))
            domain_ret_prev.append(('picking_type_id.warehouse_id', '=', warehouse_id))
            
        if prev_date_from:
            domain_in_prev.append(('date', '>=', prev_date_from))
            domain_out_prev.append(('date', '>=', prev_date_from))
            domain_int_prev.append(('date', '>=', prev_date_from))
            domain_ret_prev.append(('date', '>=', prev_date_from))
            
        if prev_date_to:
            domain_in_prev.append(('date', '<=', prev_date_to))
            domain_out_prev.append(('date', '<=', prev_date_to))
            domain_int_prev.append(('date', '<=', prev_date_to))
            domain_ret_prev.append(('date', '<=', prev_date_to))

        prev_incoming = self.env['stock.move'].search_count(domain_in_prev)
        prev_outgoing = self.env['stock.move'].search_count(domain_out_prev)
        prev_internal_transfers = self.env['stock.move'].search_count(domain_int_prev)
        prev_returns = self.env['stock.move'].search_count(domain_ret_prev)

        # 5. Stock Value by Category (Top 5)
        query_cat_val = """
            SELECT pc.name, SUM(CASE WHEN sm.is_out = TRUE THEN -sm.value ELSE sm.value END) as total_value
            FROM stock_move sm
            JOIN product_product pp ON sm.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            JOIN product_category pc ON pt.categ_id = pc.id
            WHERE sm.state = 'done' AND (sm.is_in = TRUE OR sm.is_out = TRUE) AND sm.company_id = %s
        """
        params_cat_val = [company_id]
        if category_id:
            query_cat_val += " AND pt.categ_id IN %s"
            params_cat_val.append(tuple(categ_ids))
        if date_to:
            query_cat_val += " AND DATE(sm.date) <= %s"
            params_cat_val.append(date_to)
            
        query_cat_val += " GROUP BY pc.name ORDER BY total_value DESC LIMIT 5"
        self.env.cr.execute(query_cat_val, tuple(params_cat_val))
        value_by_category = self.env.cr.fetchall()

        # 6. Warehouse Value, Product Table & Cost vs Sales
        query_quants_data = f"""
            SELECT sw.name as wh_name, sq.product_id, SUM(sq.quantity) as quantity
            FROM stock_quant sq
            JOIN stock_location sl ON sq.location_id = sl.id
            JOIN stock_warehouse sw ON sl.warehouse_id = sw.id
            { "JOIN product_product pp ON sq.product_id = pp.id JOIN product_template pt ON pp.product_tmpl_id = pt.id" if category_id else "" }
            WHERE sl.usage = 'internal' AND sq.company_id = %s { "AND pt.categ_id IN %s" if category_id else "" }
        """
        params_quants_data = [company_id]
        if category_id:
            params_quants_data.append(tuple(categ_ids))
        if warehouse_id:
            query_quants_data += " AND sw.id = %s"
            params_quants_data.append(warehouse_id)
            
        query_quants_data += " GROUP BY sw.name, sq.product_id"
        self.env.cr.execute(query_quants_data, tuple(params_quants_data))
        quants_data = self.env.cr.dictfetchall()
        
        product_ids = list(set(q['product_id'] for q in quants_data))
        products = self.env['product.product'].browse(product_ids)
        price_map = {p.id: p.standard_price for p in products}
        sales_map = {p.id: p.list_price for p in products}
        name_map = {p.id: p.display_name for p in products}
        method_map = {p.id: p.cost_method for p in products}
        valuation_map = {p.id: p.valuation for p in products}
        categ_map = {p.id: p.categ_id.name for p in products}
        
        # Fetch orderpoints for Over/Under stock calculation
        self.env.cr.execute("""
            SELECT product_id, SUM(product_min_qty) as min_qty, SUM(product_max_qty) as max_qty
            FROM stock_warehouse_orderpoint
            WHERE company_id = %s
            GROUP BY product_id
        """, (company_id,))
        orderpoints = {row['product_id']: row for row in self.env.cr.dictfetchall()}
        
        warehouse_values = {}
        total_sales_value = 0.0
        product_totals = {}
        cost_method_totals = {}
        automation_totals = {}
        
        for q in quants_data:
            pid = q['product_id']
            qty = q['quantity']
            wh_name = q['wh_name']
            cost = price_map.get(pid, 0.0)
            sales = sales_map.get(pid, 0.0)
            method = method_map.get(pid) or 'standard'
            automation = valuation_map.get(pid) or 'periodic'
            
            val = qty * cost
            warehouse_values[wh_name] = warehouse_values.get(wh_name, 0.0) + val
            cost_method_totals[method] = cost_method_totals.get(method, 0.0) + val
            automation_totals[automation] = automation_totals.get(automation, 0.0) + val
            
            if pid not in product_totals:
                product_totals[pid] = {'id': pid, 'name': name_map.get(pid, 'Unknown'), 'category': categ_map.get(pid, 'Unknown'), 'qty': 0.0, 'cost': cost, 'sales': sales, 'total_cost': 0.0, 'total_sales': 0.0}
            
            product_totals[pid]['qty'] += qty
            product_totals[pid]['total_cost'] += val
            product_totals[pid]['total_sales'] += (qty * sales)
            total_sales_value += (qty * sales)
            
        value_by_warehouse = [{'label': k, 'value': v} for k, v in warehouse_values.items()]
        value_by_warehouse.sort(key=lambda x: x['value'], reverse=True)
        value_by_warehouse = value_by_warehouse[:5]

        category_margins = {}
        negative_stock_count = 0
        overstock_count = 0
        understock_count = 0
        
        for pid, p_data in product_totals.items():
            qty = p_data['qty']
            val = p_data['total_cost']
            sales = p_data['total_sales']
            margin = sales - val
            
            categ = p_data['category']
            category_margins[categ] = category_margins.get(categ, 0.0) + margin
            
            if qty < 0:
                negative_stock_count += 1
            elif qty > 0:
                op = orderpoints.get(pid)
                if op:
                    if qty < op['min_qty']:
                        understock_count += 1
                    elif qty > op['max_qty']:
                        overstock_count += 1
                        
        profit_by_category = [{'label': k, 'value': v} for k, v in category_margins.items()]
        profit_by_category.sort(key=lambda x: x['value'], reverse=True)
        profit_by_category = profit_by_category[:5]
        
        total_margin = total_sales_value - total_value
        margin_percent = (total_margin / total_sales_value * 100) if total_sales_value > 0 else 0.0
        
        # COGS (Cost of Goods Sold) over the last 30 days
        thirty_days_ago = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
        self.env.cr.execute("""
            SELECT SUM(value) 
            FROM stock_move 
            WHERE state = 'done' AND is_out = TRUE AND DATE(date) >= %s AND company_id = %s
        """, (thirty_days_ago, company_id))
        cogs_30 = self.env.cr.fetchone()[0] or 0.0
        cogs_annual = cogs_30 * (365 / 30)
        
        turnover_ratio = cogs_annual / total_value if total_value > 0 else 0.0
        stock_days = 365 / turnover_ratio if turnover_ratio > 0 else 0.0

        product_valuations = list(product_totals.values())
        product_valuations.sort(key=lambda x: x['total_cost'], reverse=True)
        top_products = product_valuations[:10]

        cost_method_labels = {'standard': 'Standard Price', 'average': 'AVCO'}
        automation_labels = {'real_time': 'Automated (Perpetual)', 'periodic': 'Manual (Periodic)'}
        value_by_cost_method = [{'label': cost_method_labels.get(k, k.title()), 'value': v} for k, v in cost_method_totals.items() if k != 'fifo']
        value_by_automation = [{'label': automation_labels.get(k, k.title()), 'value': v} for k, v in automation_totals.items()]

        # 7. ABC Analysis
        total_inventory_cost = sum(p['total_cost'] for p in product_valuations)
        abc_totals = {'A': 0.0, 'B': 0.0, 'C': 0.0}
        cumulative_value = 0.0
        
        for p in product_valuations:
            cumulative_value += p['total_cost']
            percentage = cumulative_value / total_inventory_cost if total_inventory_cost else 0
            if percentage <= 0.80:
                abc_totals['A'] += p['total_cost']
            elif percentage <= 0.95:
                abc_totals['B'] += p['total_cost']
            else:
                abc_totals['C'] += p['total_cost']
                
        abc_analysis = [
            {'label': 'Class A (80%)', 'value': abc_totals['A']},
            {'label': 'Class B (15%)', 'value': abc_totals['B']},
            {'label': 'Class C (5%)', 'value': abc_totals['C']},
        ]

        # 8. Aging Analysis (FIFO)
        aging_buckets = {'0-30': 0.0, '31-60': 0.0, '61-90': 0.0, '90+': 0.0}
        active_products = [pid for pid, p in product_totals.items() if p['qty'] > 0]
        
        if active_products:
            self.env.cr.execute("""
                SELECT product_id, date, quantity
                FROM stock_move
                WHERE state = 'done' AND is_in = TRUE AND product_id IN %s AND company_id = %s
                ORDER BY product_id, date DESC
            """, (tuple(active_products), company_id))
            moves_in = self.env.cr.dictfetchall()
            
            moves_by_product = {}
            for m in moves_in:
                moves_by_product.setdefault(m['product_id'], []).append(m)
                
            today_dt = datetime.today()
            for pid in active_products:
                remaining_qty = product_totals[pid]['qty']
                cost = product_totals[pid]['cost']
                moves = moves_by_product.get(pid, [])
                
                for move in moves:
                    if remaining_qty <= 0:
                        break
                    
                    move_qty = move['quantity']
                    assigned_qty = min(remaining_qty, move_qty)
                    remaining_qty -= assigned_qty
                    
                    days_old = (today_dt.date() - move['date'].date()).days
                    val = assigned_qty * cost
                    
                    if days_old <= 30:
                        aging_buckets['0-30'] += val
                    elif days_old <= 60:
                        aging_buckets['31-60'] += val
                    elif days_old <= 90:
                        aging_buckets['61-90'] += val
                    else:
                        aging_buckets['90+'] += val
                        
                if remaining_qty > 0:
                    aging_buckets['90+'] += (remaining_qty * cost)
                    
        aging_analysis = [
            {'label': '0-30 days', 'value': aging_buckets['0-30']},
            {'label': '31-60 days', 'value': aging_buckets['31-60']},
            {'label': '61-90 days', 'value': aging_buckets['61-90']},
            {'label': '90+ days', 'value': aging_buckets['90+']},
        ]

        # 9. Trend Data (Valuation over time)
        trend = []
        today = datetime.today()
        if timeframe == 'yearly':
            for i in range(4, -1, -1):
                dt = today - relativedelta(years=i)
                date_str = f"{dt.year}-12-31"
                
                query_trend = f"SELECT SUM(CASE WHEN is_out = TRUE THEN -value ELSE value END) FROM stock_move {move_join} WHERE stock_move.state = 'done' AND (is_in = TRUE OR is_out = TRUE) AND stock_move.company_id = %s {move_where_cat} AND DATE(stock_move.date) <= %s"
                params_trend = [company_id]
                if category_id:
                    params_trend.append(tuple(categ_ids))
                params_trend.append(date_str)
                
                self.env.cr.execute(query_trend, tuple(params_trend))
                trend.append({'label': str(dt.year), 'value': self.env.cr.fetchone()[0] or 0.0})
        elif timeframe == 'monthly':
            for i in range(5, -1, -1):
                dt = today - relativedelta(months=i)
                _, last_day = calendar.monthrange(dt.year, dt.month)
                date_str = f"{dt.year}-{dt.month:02d}-{last_day}"
                
                query_trend = f"SELECT SUM(CASE WHEN is_out = TRUE THEN -value ELSE value END) FROM stock_move {move_join} WHERE stock_move.state = 'done' AND (is_in = TRUE OR is_out = TRUE) AND stock_move.company_id = %s {move_where_cat} AND DATE(stock_move.date) <= %s"
                params_trend = [company_id]
                if category_id:
                    params_trend.append(tuple(categ_ids))
                params_trend.append(date_str)
                
                self.env.cr.execute(query_trend, tuple(params_trend))
                trend.append({'label': dt.strftime('%b %Y'), 'value': self.env.cr.fetchone()[0] or 0.0})
        else: # daily
            for i in range(6, -1, -1):
                dt = today - timedelta(days=i)
                date_str = dt.strftime('%Y-%m-%d')
                
                query_trend = f"SELECT SUM(CASE WHEN is_out = TRUE THEN -value ELSE value END) FROM stock_move {move_join} WHERE stock_move.state = 'done' AND (is_in = TRUE OR is_out = TRUE) AND stock_move.company_id = %s {move_where_cat} AND DATE(stock_move.date) <= %s"
                params_trend = [company_id]
                if category_id:
                    params_trend.append(tuple(categ_ids))
                params_trend.append(date_str)
                
                self.env.cr.execute(query_trend, tuple(params_trend))
                trend.append({'label': dt.strftime('%a'), 'value': self.env.cr.fetchone()[0] or 0.0})

        # 10. Movement Analysis
        movements = []
        for i in range(6, -1, -1):
            dt = today - timedelta(days=i)
            date_str = dt.strftime('%Y-%m-%d')
            
            query_mov = f"""
                SELECT 
                    SUM(CASE WHEN is_in = TRUE THEN value ELSE 0 END) as inc,
                    SUM(CASE WHEN is_out = TRUE THEN value ELSE 0 END) as outg
                FROM stock_move {move_join}
                WHERE stock_move.state = 'done' AND DATE(stock_move.date) = %s AND stock_move.company_id = %s {move_where_cat}
            """
            params_mov = [date_str, company_id]
            if category_id:
                params_mov.append(tuple(categ_ids))
                
            self.env.cr.execute(query_mov, tuple(params_mov))
            res = self.env.cr.fetchone()
            movements.append({'label': dt.strftime('%a'), 'incoming': res[0] or 0.0, 'outgoing': res[1] or 0.0})

        # Notifications logic
        notifications = []
        if low_stock_count > 0:
            notifications.append({'title': 'Low Stock Products', 'desc': 'Immediate action required', 'value': low_stock_count, 'type': 'danger', 'icon': 'fa-exclamation-triangle'})
        if overstock_count > 0:
            notifications.append({'title': 'Overstock Products', 'desc': 'Review excess stock', 'value': overstock_count, 'type': 'warning', 'icon': 'fa-arrow-up'})
        # Just mock one for Negative Stock
        if negative_stock_count > 0:
            notifications.append({'title': 'Negative Stock', 'desc': 'Check stock adjustments', 'value': negative_stock_count, 'type': 'danger', 'icon': 'fa-minus-circle'})
        # Expiring / Dead stock (we have aging 90+)
        if aging_buckets['90+'] > 0:
            notifications.append({'title': 'Dead Stock', 'desc': 'No movement for 90+ days', 'value': int(aging_buckets['90+']/1000), 'type': 'danger', 'icon': 'fa-stop-circle'})

        # Top Insights logic
        insights = [
            {'title': f"Inventory value is {currency_symbol}{round(total_value, 2):,}", 'icon': 'fa-lightbulb-o', 'color': 'text-primary'},
            {'title': f"Top product is {top_products[0]['name'] if top_products else 'N/A'}", 'icon': 'fa-trophy', 'color': 'text-success'},
            {'title': f"Stock turnover ratio is {round(turnover_ratio, 1)}", 'icon': 'fa-refresh', 'color': 'text-info'},
            {'title': f"Aging stock (90+ days) is {round((aging_buckets['90+'] / total_value * 100) if total_value else 0, 1)}% of total inventory value.", 'icon': 'fa-clock-o', 'color': 'text-warning'}
        ]

        # Net quantity change since prev_date_to to approximate prev_total_qty
        query_net_qty = f"""
            SELECT SUM(CASE WHEN is_in = TRUE THEN product_uom_qty WHEN is_out = TRUE THEN -product_uom_qty ELSE 0 END)
            FROM stock_move {move_join}
            WHERE stock_move.state = 'done' AND (is_in = TRUE OR is_out = TRUE) AND stock_move.company_id = %s {move_where_cat} AND DATE(stock_move.date) > %s
        """
        params_net_qty = [company_id]
        if category_id:
            params_net_qty.append(tuple(categ_ids))
        params_net_qty.append(prev_date_to)
        
        self.env.cr.execute(query_net_qty, tuple(params_net_qty))
        net_qty_change = self.env.cr.fetchone()[0] or 0.0
        prev_total_qty = total_qty - net_qty_change

        # --- NEW FINANCIAL METRICS ---
        # Beginning Balance (Value up to prev_dt_to if date_from provided, else 0 or all time)
        beginning_balance = 0.0
        if date_from:
            prev_dt = datetime.strptime(date_from, '%Y-%m-%d') - timedelta(days=1)
            query_bb = f"SELECT SUM(CASE WHEN is_out = TRUE THEN -value ELSE value END) FROM stock_move {move_join} WHERE stock_move.state = 'done' AND (is_in = TRUE OR is_out = TRUE) AND stock_move.company_id = %s {move_where_cat} AND DATE(stock_move.date) <= %s"
            params_bb = [company_id]
            if category_id:
                params_bb.append(tuple(categ_ids))
            params_bb.append(prev_dt.strftime('%Y-%m-%d'))
            
            self.env.cr.execute(query_bb, tuple(params_bb))
            beginning_balance = self.env.cr.fetchone()[0] or 0.0

        ending_balance = total_value
        internal_balance = total_value
        
        # Inventory Adjustments in selected period
        query_adj = f"SELECT SUM(value) FROM stock_move {move_join} JOIN stock_location sl ON stock_move.location_id = sl.id JOIN stock_location sld ON stock_move.location_dest_id = sld.id WHERE stock_move.state = 'done' AND stock_move.company_id = %s {move_where_cat} AND (sl.usage = 'inventory' OR sld.usage = 'inventory')"
        params_adj = [company_id]
        if category_id:
            params_adj.append(tuple(categ_ids))
        if date_from:
            query_adj += " AND DATE(stock_move.date) >= %s"
            params_adj.append(date_from)
        if date_to:
            query_adj += " AND DATE(stock_move.date) <= %s"
            params_adj.append(date_to)
        self.env.cr.execute(query_adj, tuple(params_adj))
        inventory_adjustments = self.env.cr.fetchone()[0] or 0.0
        
        # Exact COGS in selected period (Customer shipments)
        query_cogs = f"SELECT SUM(value) FROM stock_move {move_join} JOIN stock_location sld ON stock_move.location_dest_id = sld.id WHERE stock_move.state = 'done' AND stock_move.company_id = %s {move_where_cat} AND sld.usage = 'customer'"
        params_cogs = [company_id]
        if category_id:
            params_cogs.append(tuple(categ_ids))
        if date_from:
            query_cogs += " AND DATE(stock_move.date) >= %s"
            params_cogs.append(date_from)
        if date_to:
            query_cogs += " AND DATE(stock_move.date) <= %s"
            params_cogs.append(date_to)
        self.env.cr.execute(query_cogs, tuple(params_cogs))
        exact_cogs = self.env.cr.fetchone()[0] or 0.0
        
        gross_profit = total_sales_value - exact_cogs

        return {
            'beginning_balance': round(beginning_balance, 2),
            'ending_balance': round(ending_balance, 2),
            'internal_balance': round(internal_balance, 2),
            'inventory_adjustments': round(inventory_adjustments, 2),
            'exact_cogs': round(exact_cogs, 2),
            'gross_profit': round(gross_profit, 2),
            'total_value': round(total_value, 2),
            'prev_total_value': round(prev_total_value, 2),
            'total_sales_value': round(total_sales_value, 2),
            'total_qty': round(total_qty, 2),
            'prev_total_qty': round(prev_total_qty, 2),
            'total_products': total_products,
            'prev_total_products': prev_total_products,
            'low_stock_count': low_stock_count,
            'prev_low_stock_count': prev_low_stock_count,
            'incoming': incoming,
            'prev_incoming': prev_incoming,
            'outgoing': outgoing,
            'prev_outgoing': prev_outgoing,
            'internal_transfers': internal_transfers,
            'prev_internal_transfers': prev_internal_transfers,
            'returns': returns,
            'prev_returns': prev_returns,
            'value_by_category': [{'label': row[0], 'value': row[1]} for row in value_by_category],
            'value_by_warehouse': value_by_warehouse,
            'value_by_cost_method': value_by_cost_method,
            'value_by_automation': value_by_automation,
            'abc_analysis': abc_analysis,
            'aging_analysis': aging_analysis,
            'top_products': top_products,
            'trend': trend,
            'movements': movements,
            'timeframe': timeframe,
            'currency_symbol': currency_symbol,
            'negative_stock_count': negative_stock_count,
            'overstock_count': overstock_count,
            'understock_count': understock_count,
            'total_margin': round(total_margin, 2),
            'margin_percent': round(margin_percent, 2),
            'profit_by_category': profit_by_category,
            'turnover_ratio': round(turnover_ratio, 2),
            'stock_days': round(stock_days, 1),
            'notifications': notifications,
            'insights': insights,
        }
