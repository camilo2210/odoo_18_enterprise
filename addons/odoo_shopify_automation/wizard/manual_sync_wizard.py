from odoo import models, fields, api
from odoo.exceptions import UserError

class ShopifyManualSyncWizard(models.TransientModel):
    _name = 'shopify.manual.sync.wizard'
    _description = 'Shopify Manual Sync Wizard'

    instance_id = fields.Many2one('shopify.instance', string='Shopify Instance', required=True)
    sync_type = fields.Selection([
        ('import_product', 'Import Products'),
        ('import_order', 'Import Orders'),
        ('import_customer', 'Import Customers'),
        ('export_product', 'Export Products'),
        ('export_order', 'Export Orders'),
        ('export_customer', 'Export Customers'),
    ], string='Sync Type', required=True)

    def action_manual_sync(self):
        if not self.instance_id or not self.sync_type:
            raise UserError('Please select an instance and sync type.')
        if self.sync_type == 'import_product':
            self.env['shopify.product'].import_products_from_shopify(self.instance_id)
        elif self.sync_type == 'import_order':
            self.env['shopify.order'].import_orders_from_shopify(self.instance_id)
        elif self.sync_type == 'import_customer':
            self.env['shopify.customer'].import_customers_from_shopify(self.instance_id)
        elif self.sync_type == 'export_product':
            products = self.env['shopify.product'].search([('instance_id', '=', self.instance_id.id)])
            self.env['shopify.product'].export_products_to_shopify(self.instance_id, products)
        elif self.sync_type == 'export_order':
            orders = self.env['shopify.order'].search([('instance_id', '=', self.instance_id.id)])
            self.env['shopify.order'].export_orders_to_shopify(self.instance_id, orders)
        elif self.sync_type == 'export_customer':
            customers = self.env['shopify.customer'].search([('instance_id', '=', self.instance_id.id)])
            self.env['shopify.customer'].export_customers_to_shopify(self.instance_id, customers)
        return {'type': 'ir.actions.act_window_close'} 