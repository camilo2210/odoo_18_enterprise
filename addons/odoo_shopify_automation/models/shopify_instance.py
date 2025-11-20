from odoo import models, fields, api
import requests
from odoo.exceptions import UserError
from odoo.tools.translate import _


class ShopifyInstance(models.Model):
    _name = 'shopify.instance'
    _description = 'Shopify Store Instance'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char('Instance Name', required=True, tracking=True)
    shop_url = fields.Char('Shopify Shop URL', required=True, help='e.g. https://yourstore.myshopify.com', tracking=True)
    api_key = fields.Char('API Key', required=True)
    password = fields.Char('API Password', required=True)
    shared_secret = fields.Char('Shared Secret', required=True)
    access_token = fields.Char('Access Token', help='OAuth Access Token (if using OAuth)')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, tracking=True)
    active = fields.Boolean('Active', default=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('connected', 'Connected'),
        ('error', 'Error'),
    ], string='Status', default='draft', tracking=True)
    last_sync = fields.Datetime('Last Sync', tracking=True)
    note = fields.Text('Notes')


    # Dashboard KPIs
    total_sales = fields.Monetary(string='Total Sales', currency_field='currency_id', compute='_compute_dashboard_kpis')
    product_count = fields.Integer(string='Products', compute='_compute_dashboard_kpis')
    order_count = fields.Integer(string='Orders', compute='_compute_dashboard_kpis')
    customer_count = fields.Integer(string='Customers', compute='_compute_dashboard_kpis')
    queue_job_count = fields.Integer(string='Queue Jobs', compute='_compute_dashboard_kpis')
    error_count = fields.Integer(string='Errors', compute='_compute_dashboard_kpis')
    sales_chart_data = fields.Json(string='Sales Chart Data', compute='_compute_dashboard_kpis')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)


    _sql_constraints = [
        ('shop_url_uniq', 'unique(shop_url, company_id)', 'A Shopify instance with this URL already exists for this company!'),
    ]


    def action_test_connection(self):
        self.ensure_one()
        url = f"{self.shop_url}/admin/api/2024-01/shop.json"
        try:
            response = requests.get(url, auth=(self.api_key, self.password), timeout=10)
            if response.status_code == 200:
                self.state = 'connected'
                self.message_post(body=_('Connection Test Succeeded!'))
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Shopify'),
                        'message': _('Connection Test Succeeded!'),
                        'type': 'success',
                        'sticky': False,
                    },
                }
            else:
                self.state = 'error'
                raise UserError(_(f"Connection failed! Status: {response.status_code}\n{response.text}"))
        except Exception as e:
            self.state = 'error'
            raise UserError(_(f"Connection error: {str(e)}"))


    def _compute_dashboard_kpis(self):
        for rec in self:
            rec.product_count = self.env['shopify.product'].search_count([('instance_id', '=', rec.id), ('active', '=', True)])
            rec.order_count = self.env['shopify.order'].search_count([('instance_id', '=', rec.id), ('active', '=', True)])
            rec.customer_count = self.env['shopify.customer'].search_count([('instance_id', '=', rec.id), ('active', '=', True)])
            rec.queue_job_count = self.env['shopify.queue.job'].search_count([('instance_id', '=', rec.id)])
            rec.error_count = self.env['shopify.log'].search_count([('job_id.instance_id', '=', rec.id), ('log_type', '=', 'error')])
            
            # Calculate total sales
            orders = self.env['shopify.order'].search([
                ('instance_id', '=', rec.id),
                ('active', '=', True),
                ('odoo_order_id', '!=', False)
            ])
            rec.total_sales = sum(orders.mapped('odoo_order_id.amount_total') or [0.0])
            # Sales chart: sales per month for last 12 months
            orders = self.env['shopify.order'].search([
                ('instance_id', '=', rec.id),
                ('active', '=', True),
                ('odoo_order_id', '!=', False)
            ])
            sales_by_month = {}
            for order in orders:
                if order.odoo_order_id and order.odoo_order_id.date_order:
                    month = order.odoo_order_id.date_order.strftime('%Y-%m')
                    sales_by_month.setdefault(month, 0)
                    sales_by_month[month] += order.odoo_order_id.amount_total or 0.0
            # Sort and keep last 12 months
            sorted_months = sorted(sales_by_month.keys())[-12:]
            rec.sales_chart_data = {
                'labels': sorted_months,
                'values': [round(sales_by_month[m], 2) for m in sorted_months]
            }
