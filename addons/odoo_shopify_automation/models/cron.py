from odoo import models, fields, api
from datetime import datetime

class ShopifyCron(models.Model):
    _name = 'shopify.cron'
    _description = 'Shopify Scheduled Sync Cron'

    name = fields.Char('Cron Name', required=True)
    cron_type = fields.Selection([
        ('import_product', 'Import Products'),
        ('import_order', 'Import Orders'),
        ('import_customer', 'Import Customers'),
        ('export_product', 'Export Products'),
        ('export_order', 'Export Orders'),
        ('export_customer', 'Export Customers'),
    ], string='Cron Type', required=True)
    instance_id = fields.Many2one('shopify.instance', string='Shopify Instance', required=True)
    active = fields.Boolean('Active', default=True)
    last_run = fields.Datetime('Last Run')
    note = fields.Text('Notes')

    def run_cron(self):
        for cron in self:
            try:
                if cron.cron_type == 'import_product':
                    self.env['shopify.product'].import_products_from_shopify(cron.instance_id)
                elif cron.cron_type == 'import_order':
                    self.env['shopify.order'].import_orders_from_shopify(cron.instance_id)
                elif cron.cron_type == 'import_customer':
                    self.env['shopify.customer'].import_customers_from_shopify(cron.instance_id)
                elif cron.cron_type == 'export_product':
                    # Example: export all mapped products for this instance
                    products = self.env['shopify.product'].search([('instance_id', '=', cron.instance_id.id)])
                    self.env['shopify.product'].export_products_to_shopify(cron.instance_id, products)
                elif cron.cron_type == 'export_order':
                    orders = self.env['shopify.order'].search([('instance_id', '=', cron.instance_id.id)])
                    self.env['shopify.order'].export_orders_to_shopify(cron.instance_id, orders)
                elif cron.cron_type == 'export_customer':
                    customers = self.env['shopify.customer'].search([('instance_id', '=', cron.instance_id.id)])
                    self.env['shopify.customer'].export_customers_to_shopify(cron.instance_id, customers)
                self.env['shopify.log'].create({
                    'name': f'Cron {cron.cron_type} completed',
                    'log_type': 'info',
                    'message': f'Cron job {cron.cron_type} completed for instance {cron.instance_id.name}',
                })
            except Exception as e:
                self.env['shopify.log'].create({
                    'name': f'Cron {cron.cron_type} error',
                    'log_type': 'error',
                    'message': f'Error in cron job {cron.cron_type} for instance {cron.instance_id.name}: {str(e)}',
                })
            cron.last_run = fields.Datetime.now() 