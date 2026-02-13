# -*- coding: utf-8 -*-
import logging
import json
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

class ShopifyAnalytics(models.Model):
    _name = 'shopify.analytics'
    _description = 'Shopify Analytics Dashboard'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Analytics Name', required=True, tracking=True)
    instance_id = fields.Many2one('shopify.instance', string='Shopify Instance', required=True, ondelete='cascade')
    
    # Time Period
    date_from = fields.Date('From Date', required=True, tracking=True)
    date_to = fields.Date('To Date', required=True, tracking=True)
    period_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], string='Period Type', default='monthly', tracking=True)
    
    # Sales Analytics
    total_sales = fields.Monetary('Total Sales', currency_field='currency_id', compute='_compute_sales_analytics')
    total_orders = fields.Integer('Total Orders', compute='_compute_sales_analytics')
    average_order_value = fields.Monetary('Average Order Value', currency_field='currency_id', compute='_compute_sales_analytics')
    conversion_rate = fields.Float('Conversion Rate (%)', compute='_compute_sales_analytics')
    revenue_growth = fields.Float('Revenue Growth (%)', compute='_compute_sales_analytics')
    
    # Customer Analytics
    total_customers = fields.Integer('Total Customers', compute='_compute_customer_analytics')
    new_customers = fields.Integer('New Customers', compute='_compute_customer_analytics')
    returning_customers = fields.Integer('Returning Customers', compute='_compute_customer_analytics')
    customer_acquisition_cost = fields.Monetary('Customer Acquisition Cost', currency_field='currency_id', compute='_compute_customer_analytics')
    customer_lifetime_value = fields.Monetary('Customer Lifetime Value', currency_field='currency_id', compute='_compute_customer_analytics')
    
    # Product Analytics
    total_products = fields.Integer('Total Products', compute='_compute_product_analytics')
    top_selling_products = fields.Text('Top Selling Products', compute='_compute_product_analytics')
    low_stock_products = fields.Text('Low Stock Products', compute='_compute_product_analytics')
    product_performance_score = fields.Float('Product Performance Score', compute='_compute_product_analytics')
    
    # Inventory Analytics
    total_inventory_value = fields.Monetary('Total Inventory Value', currency_field='currency_id', compute='_compute_inventory_analytics')
    inventory_turnover_rate = fields.Float('Inventory Turnover Rate', compute='_compute_inventory_analytics')
    stockout_incidents = fields.Integer('Stockout Incidents', compute='_compute_inventory_analytics')
    reorder_recommendations = fields.Text('Reorder Recommendations', compute='_compute_inventory_analytics')
    
    # Financial Analytics
    gross_profit_margin = fields.Float('Gross Profit Margin (%)', compute='_compute_financial_analytics')
    net_profit_margin = fields.Float('Net Profit Margin (%)', compute='_compute_financial_analytics')
    operating_expenses = fields.Monetary('Operating Expenses', currency_field='currency_id', compute='_compute_financial_analytics')
    cash_flow = fields.Monetary('Cash Flow', currency_field='currency_id', compute='_compute_financial_analytics')
    
    # Performance Metrics
    order_fulfillment_rate = fields.Float('Order Fulfillment Rate (%)', compute='_compute_performance_analytics')
    average_processing_time = fields.Float('Average Processing Time (Hours)', compute='_compute_performance_analytics')
    customer_satisfaction_score = fields.Float('Customer Satisfaction Score', compute='_compute_performance_analytics')
    return_rate = fields.Float('Return Rate (%)', compute='_compute_performance_analytics')
    
    # AI Insights
    ai_insights = fields.Text('AI Insights', compute='_compute_ai_insights')
    risk_alerts = fields.Text('Risk Alerts', compute='_compute_ai_insights')
    optimization_recommendations = fields.Text('Optimization Recommendations', compute='_compute_ai_insights')
    
    # Chart Data
    sales_chart_data = fields.Json('Sales Chart Data', compute='_compute_chart_data')
    customer_chart_data = fields.Json('Customer Chart Data', compute='_compute_chart_data')
    product_chart_data = fields.Json('Product Chart Data', compute='_compute_chart_data')
    inventory_chart_data = fields.Json('Inventory Chart Data', compute='_compute_chart_data')
    
    # Configuration
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                 default=lambda self: self.env.company.currency_id)
    base_currency_id = fields.Many2one('res.currency', string='Base Currency', 
                                      default=lambda self: self.env.company.currency_id)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ], string='Status', default='draft', tracking=True)
    
    # Audit
    last_updated = fields.Datetime('Last Updated', default=fields.Datetime.now, readonly=True)
    generated_by = fields.Many2one('res.users', string='Generated By', default=lambda self: self.env.user)
    
    note = fields.Text('Notes')

    @api.depends('date_from', 'date_to', 'instance_id')
    def _compute_sales_analytics(self):
        for record in self:
            orders = self._get_orders_in_period(record)
            
            record.total_sales = sum(orders.mapped('amount_total'))
            record.total_orders = len(orders)
            record.average_order_value = record.total_sales / record.total_orders if record.total_orders > 0 else 0
            
            # Calculate conversion rate (orders / visitors)
            visitors = self._get_visitors_in_period(record)
            record.conversion_rate = (record.total_orders / visitors * 100) if visitors > 0 else 0
            
            # Calculate revenue growth
            previous_period_sales = self._get_previous_period_sales(record)
            record.revenue_growth = ((record.total_sales - previous_period_sales) / previous_period_sales * 100) if previous_period_sales > 0 else 0

    @api.depends('date_from', 'date_to', 'instance_id')
    def _compute_customer_analytics(self):
        for record in self:
            customers = self._get_customers_in_period(record)
            
            record.total_customers = len(customers)
            record.new_customers = len(customers.filtered(lambda c: c.create_date >= record.date_from))
            record.returning_customers = record.total_customers - record.new_customers
            
            # Calculate customer acquisition cost
            marketing_costs = self._get_marketing_costs_in_period(record)
            record.customer_acquisition_cost = marketing_costs / record.new_customers if record.new_customers > 0 else 0
            
            # Calculate customer lifetime value
            record.customer_lifetime_value = record.total_sales / record.total_customers if record.total_customers > 0 else 0

    @api.depends('date_from', 'date_to', 'instance_id')
    def _compute_product_analytics(self):
        for record in self:
            products = self._get_products_in_period(record)
            
            record.total_products = len(products)
            
            # Get top selling products
            top_products = self._get_top_selling_products(record)
            record.top_selling_products = json.dumps(top_products)
            
            # Get low stock products
            low_stock_products = self._get_low_stock_products(record)
            record.low_stock_products = json.dumps(low_stock_products)
            
            # Calculate product performance score
            record.product_performance_score = self._calculate_product_performance_score(record)

    @api.depends('date_from', 'date_to', 'instance_id')
    def _compute_inventory_analytics(self):
        for record in self:
            # Calculate total inventory value
            products = self._get_products_in_period(record)
            record.total_inventory_value = sum(products.mapped(lambda p: p.qty_available * p.standard_price))
            
            # Calculate inventory turnover rate
            record.inventory_turnover_rate = self._calculate_inventory_turnover_rate(record)
            
            # Count stockout incidents
            record.stockout_incidents = self._count_stockout_incidents(record)
            
            # Generate reorder recommendations
            reorder_recs = self._generate_reorder_recommendations(record)
            record.reorder_recommendations = json.dumps(reorder_recs)

    @api.depends('date_from', 'date_to', 'instance_id')
    def _compute_financial_analytics(self):
        for record in self:
            # Calculate gross profit margin
            total_cost = self._get_total_cost_in_period(record)
            record.gross_profit_margin = ((record.total_sales - total_cost) / record.total_sales * 100) if record.total_sales > 0 else 0
            
            # Calculate net profit margin
            operating_expenses = self._get_operating_expenses_in_period(record)
            record.operating_expenses = operating_expenses
            record.net_profit_margin = ((record.total_sales - total_cost - operating_expenses) / record.total_sales * 100) if record.total_sales > 0 else 0
            
            # Calculate cash flow
            record.cash_flow = record.total_sales - total_cost - operating_expenses

    @api.depends('date_from', 'date_to', 'instance_id')
    def _compute_performance_analytics(self):
        for record in self:
            # Calculate order fulfillment rate
            fulfilled_orders = self._get_fulfilled_orders_in_period(record)
            record.order_fulfillment_rate = (len(fulfilled_orders) / record.total_orders * 100) if record.total_orders > 0 else 0
            
            # Calculate average processing time
            record.average_processing_time = self._calculate_average_processing_time(record)
            
            # Calculate customer satisfaction score
            record.customer_satisfaction_score = self._calculate_customer_satisfaction_score(record)
            
            # Calculate return rate
            returned_orders = self._get_returned_orders_in_period(record)
            record.return_rate = (len(returned_orders) / record.total_orders * 100) if record.total_orders > 0 else 0

    @api.depends('date_from', 'date_to', 'instance_id')
    def _compute_ai_insights(self):
        for record in self:
            # Generate AI insights
            insights = self._generate_ai_insights(record)
            record.ai_insights = json.dumps(insights)
            
            # Generate risk alerts
            risks = self._generate_risk_alerts(record)
            record.risk_alerts = json.dumps(risks)
            
            # Generate optimization recommendations
            recommendations = self._generate_optimization_recommendations(record)
            record.optimization_recommendations = json.dumps(recommendations)

    @api.depends('date_from', 'date_to', 'instance_id')
    def _compute_chart_data(self):
        for record in self:
            # Generate sales chart data
            record.sales_chart_data = self._generate_sales_chart_data(record)
            
            # Generate customer chart data
            record.customer_chart_data = self._generate_customer_chart_data(record)
            
            # Generate product chart data
            record.product_chart_data = self._generate_product_chart_data(record)
            
            # Generate inventory chart data
            record.inventory_chart_data = self._generate_inventory_chart_data(record)

    def _get_orders_in_period(self, record):
        """Get orders within the specified period"""
        shopify_orders = self.env['shopify.order'].search([
            ('instance_id', '=', record.instance_id.id),
            ('odoo_order_id.date_order', '>=', record.date_from),
            ('odoo_order_id.date_order', '<=', record.date_to),
            ('odoo_order_id.state', 'in', ['sale', 'done'])
        ])
        return shopify_orders.mapped('odoo_order_id')

    def _get_customers_in_period(self, record):
        """Get customers within the specified period"""
        # Get customers from Shopify orders in the period
        shopify_orders = self.env['shopify.order'].search([
            ('instance_id', '=', record.instance_id.id),
            ('odoo_order_id.date_order', '>=', record.date_from),
            ('odoo_order_id.date_order', '<=', record.date_to)
        ])
        return shopify_orders.mapped('odoo_order_id.partner_id')

    def _get_products_in_period(self, record):
        """Get products within the specified period"""
        shopify_products = self.env['shopify.product'].search([
            ('instance_id', '=', record.instance_id.id)
        ])
        return shopify_products.mapped('odoo_product_id')

    def _get_visitors_in_period(self, record):
        """Get visitors within the specified period (placeholder)"""
        # This would integrate with analytics platforms like Google Analytics
        return 1000  # Placeholder

    def _get_previous_period_sales(self, record):
        """Get sales from previous period for growth calculation"""
        period_days = (record.date_to - record.date_from).days
        previous_date_from = record.date_from - timedelta(days=period_days)
        previous_date_to = record.date_from - timedelta(days=1)
        
        previous_shopify_orders = self.env['shopify.order'].search([
            ('instance_id', '=', record.instance_id.id),
            ('odoo_order_id.date_order', '>=', previous_date_from),
            ('odoo_order_id.date_order', '<=', previous_date_to),
            ('odoo_order_id.state', 'in', ['sale', 'done'])
        ])
        
        return sum(previous_shopify_orders.mapped('odoo_order_id.amount_total'))

    def _get_marketing_costs_in_period(self, record):
        """Get marketing costs within the specified period"""
        # This would integrate with marketing platforms
        return 5000  # Placeholder

    def _get_top_selling_products(self, record):
        """Get top selling products"""
        orders = self._get_orders_in_period(record)
        product_sales = {}
        
        for order in orders:
            for line in order.order_line:
                product_id = line.product_id.id
                if product_id not in product_sales:
                    product_sales[product_id] = 0
                product_sales[product_id] += line.product_uom_qty
        
        # Sort by sales quantity
        sorted_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)
        
        top_products = []
        for product_id, qty in sorted_products[:10]:
            product = self.env['product.product'].browse(product_id)
            top_products.append({
                'name': product.name,
                'quantity': qty,
                'revenue': qty * product.list_price
            })
        
        return top_products

    def _get_low_stock_products(self, record):
        """Get products with low stock"""
        products = self._get_products_in_period(record)
        low_stock_products = []
        
        for product in products:
            # Use a default reorder point of 10 if not set
            reorder_point = getattr(product, 'reorder_min_qty', 10)
            if product.qty_available <= reorder_point:
                low_stock_products.append({
                    'name': product.name,
                    'current_stock': product.qty_available,
                    'reorder_point': reorder_point,
                    'recommended_order': reorder_point - product.qty_available
                })
        
        return low_stock_products

    def _calculate_product_performance_score(self, record):
        """Calculate product performance score"""
        products = self._get_products_in_period(record)
        if not products:
            return 0
        
        total_score = 0
        for product in products:
            # Calculate score based on available metrics
            # Use safe defaults for fields that might not exist
            sales_count = getattr(product, 'sales_count', 0)
            gross_profit_margin = getattr(product, 'gross_profit_margin', 0)
            inventory_turnover_rate = getattr(product, 'inventory_turnover_rate', 0)
            
            sales_score = min(sales_count / 100, 1) * 40  # Max 40 points
            profit_score = min(gross_profit_margin / 50, 1) * 30  # Max 30 points
            turnover_score = min(inventory_turnover_rate / 10, 1) * 30  # Max 30 points
            
            total_score += sales_score + profit_score + turnover_score
        
        return total_score / len(products)

    def _calculate_inventory_turnover_rate(self, record):
        """Calculate inventory turnover rate"""
        # This is a simplified calculation
        products = self._get_products_in_period(record)
        if not products:
            return 0
        
        total_cost_of_goods_sold = sum(products.mapped(lambda p: getattr(p, 'sales_count', 0) * p.standard_price))
        average_inventory = sum(products.mapped('qty_available')) / len(products)
        
        return total_cost_of_goods_sold / average_inventory if average_inventory > 0 else 0

    def _count_stockout_incidents(self, record):
        """Count stockout incidents"""
        # This would integrate with inventory management system
        return 5  # Placeholder

    def _generate_reorder_recommendations(self, record):
        """Generate reorder recommendations"""
        products = self._get_products_in_period(record)
        recommendations = []
        
        for product in products:
            reorder_min_qty = getattr(product, 'reorder_min_qty', 10)
            reorder_max_qty = getattr(product, 'reorder_max_qty', 50)
            
            if product.qty_available <= reorder_min_qty:
                recommended_qty = reorder_max_qty - product.qty_available
                recommendations.append({
                    'product_name': product.name,
                    'current_stock': product.qty_available,
                    'recommended_order': recommended_qty,
                    'urgency': 'high' if product.qty_available == 0 else 'medium'
                })
        
        return recommendations

    def _get_total_cost_in_period(self, record):
        """Get total cost of goods sold in period"""
        orders = self._get_orders_in_period(record)
        total_cost = 0
        
        for order in orders:
            for line in order.order_line:
                total_cost += line.product_uom_qty * line.product_id.standard_price
        
        return total_cost

    def _get_operating_expenses_in_period(self, record):
        """Get operating expenses in period"""
        # This would integrate with accounting system
        return 10000  # Placeholder

    def _get_fulfilled_orders_in_period(self, record):
        """Get fulfilled orders in period"""
        shopify_orders = self.env['shopify.order'].search([
            ('instance_id', '=', record.instance_id.id),
            ('odoo_order_id.date_order', '>=', record.date_from),
            ('odoo_order_id.date_order', '<=', record.date_to),
            ('odoo_order_id.state', '=', 'done')
        ])
        return shopify_orders.mapped('odoo_order_id')

    def _calculate_average_processing_time(self, record):
        """Calculate average order processing time"""
        orders = self._get_orders_in_period(record)
        if not orders:
            return 0
        
        total_time = 0
        count = 0
        
        for order in orders:
            if order.effective_date and order.date_order:
                processing_time = (order.effective_date - order.date_order).total_seconds() / 3600
                total_time += processing_time
                count += 1
        
        return total_time / count if count > 0 else 0

    def _calculate_customer_satisfaction_score(self, record):
        """Calculate customer satisfaction score"""
        # This would integrate with customer feedback systems
        return 4.2  # Placeholder

    def _get_returned_orders_in_period(self, record):
        """Get returned orders in period"""
        # This would integrate with returns management system
        shopify_orders = self.env['shopify.order'].search([
            ('instance_id', '=', record.instance_id.id),
            ('odoo_order_id.date_order', '>=', record.date_from),
            ('odoo_order_id.date_order', '<=', record.date_to),
            ('odoo_order_id.state', '=', 'cancel')
        ])
        return shopify_orders.mapped('odoo_order_id')

    def _generate_ai_insights(self, record):
        """Generate AI-powered insights"""
        insights = []
        
        # Sales insights
        if record.revenue_growth > 20:
            insights.append("Strong revenue growth detected - consider expanding inventory")
        elif record.revenue_growth < -10:
            insights.append("Revenue decline detected - review pricing and marketing strategy")
        
        # Customer insights
        if record.customer_acquisition_cost > record.customer_lifetime_value:
            insights.append("Customer acquisition cost exceeds lifetime value - optimize marketing spend")
        
        # Inventory insights
        if record.inventory_turnover_rate < 2:
            insights.append("Low inventory turnover - consider promotions or price adjustments")
        
        return insights

    def _generate_risk_alerts(self, record):
        """Generate risk alerts"""
        risks = []
        
        # Stockout risks
        if record.stockout_incidents > 10:
            risks.append("High stockout incidents - review inventory management")
        
        # Customer satisfaction risks
        if record.customer_satisfaction_score < 3.5:
            risks.append("Low customer satisfaction - investigate service issues")
        
        # Financial risks
        if record.net_profit_margin < 5:
            risks.append("Low profit margin - review pricing and costs")
        
        return risks

    def _generate_optimization_recommendations(self, record):
        """Generate optimization recommendations"""
        recommendations = []
        
        # Sales optimization
        if record.conversion_rate < 2:
            recommendations.append("Low conversion rate - optimize website and checkout process")
        
        # Inventory optimization
        if record.inventory_turnover_rate < 3:
            recommendations.append("Improve inventory turnover with better demand forecasting")
        
        # Customer optimization
        if record.customer_lifetime_value < record.customer_acquisition_cost * 3:
            recommendations.append("Focus on customer retention and upselling strategies")
        
        return recommendations

    def _generate_sales_chart_data(self, record):
        """Generate sales chart data"""
        orders = self._get_orders_in_period(record)
        
        # Group by date
        sales_by_date = {}
        for order in orders:
            date_str = order.date_order.strftime('%Y-%m-%d')
            if date_str not in sales_by_date:
                sales_by_date[date_str] = 0
            sales_by_date[date_str] += order.amount_total
        
        return {
            'labels': list(sales_by_date.keys()),
            'values': list(sales_by_date.values()),
            'type': 'line'
        }

    def _generate_customer_chart_data(self, record):
        """Generate customer chart data"""
        customers = self._get_customers_in_period(record)
        
        # Group by date
        customers_by_date = {}
        for customer in customers:
            date_str = customer.create_date.strftime('%Y-%m-%d')
            if date_str not in customers_by_date:
                customers_by_date[date_str] = 0
            customers_by_date[date_str] += 1
        
        return {
            'labels': list(customers_by_date.keys()),
            'values': list(customers_by_date.values()),
            'type': 'bar'
        }

    def _generate_product_chart_data(self, record):
        """Generate product chart data"""
        top_products = json.loads(record.top_selling_products or '[]')
        
        return {
            'labels': [p['name'] for p in top_products],
            'values': [p['quantity'] for p in top_products],
            'type': 'pie'
        }

    def _generate_inventory_chart_data(self, record):
        """Generate inventory chart data"""
        products = self._get_products_in_period(record)
        
        # Group by stock level
        stock_levels = {
            'In Stock': len(products.filtered(lambda p: p.qty_available > getattr(p, 'reorder_min_qty', 10))),
            'Low Stock': len(products.filtered(lambda p: 0 < p.qty_available <= getattr(p, 'reorder_min_qty', 10))),
            'Out of Stock': len(products.filtered(lambda p: p.qty_available == 0))
        }
        
        return {
            'labels': list(stock_levels.keys()),
            'values': list(stock_levels.values()),
            'type': 'doughnut'
        }

    def action_generate_analytics(self):
        """Generate analytics for the specified period"""
        for record in self:
            record.state = 'processing'
            try:
                # Trigger all computed fields
                record._compute_sales_analytics()
                record._compute_customer_analytics()
                record._compute_product_analytics()
                record._compute_inventory_analytics()
                record._compute_financial_analytics()
                record._compute_performance_analytics()
                record._compute_ai_insights()
                record._compute_chart_data()
                
                record.state = 'completed'
                record.last_updated = fields.Datetime.now()
                record.message_post(body=_('Analytics generated successfully'))
            except Exception as e:
                record.state = 'error'
                record.message_post(body=_('Failed to generate analytics: %s') % str(e))
                raise UserError(_('Failed to generate analytics: %s') % str(e))

    def action_export_report(self):
        """Export analytics report"""
        for record in self:
            # Generate report data
            report_data = {
                'analytics_name': record.name,
                'period': f"{record.date_from} to {record.date_to}",
                'sales_summary': {
                    'total_sales': record.total_sales,
                    'total_orders': record.total_orders,
                    'average_order_value': record.average_order_value,
                    'revenue_growth': record.revenue_growth,
                },
                'customer_summary': {
                    'total_customers': record.total_customers,
                    'new_customers': record.new_customers,
                    'customer_lifetime_value': record.customer_lifetime_value,
                },
                'ai_insights': json.loads(record.ai_insights or '[]'),
                'risk_alerts': json.loads(record.risk_alerts or '[]'),
                'recommendations': json.loads(record.optimization_recommendations or '[]'),
            }
            
            # Return report data (could be used for PDF generation, Excel export, etc.)
            return report_data

    @api.model
    def create(self, vals):
        """Override create to set default values"""
        if not vals.get('date_from'):
            vals['date_from'] = (datetime.now() - timedelta(days=30)).date()
        if not vals.get('date_to'):
            vals['date_to'] = datetime.now().date()
        
        return super().create(vals)

    def write(self, vals):
        """Override write to trigger analytics generation"""
        result = super().write(vals)
        
        # If period changed, regenerate analytics
        if 'date_from' in vals or 'date_to' in vals:
            for record in self:
                if record.state == 'completed':
                    record.action_generate_analytics()
        
        return result 