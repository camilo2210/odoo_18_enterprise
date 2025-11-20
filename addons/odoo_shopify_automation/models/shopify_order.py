from odoo import models, fields, api
import requests
from odoo.exceptions import UserError
from odoo.tools.translate import _
from datetime import datetime


class ShopifyOrder(models.Model):
    _name = 'shopify.order'
    _description = 'Shopify Order Mapping'
    _rec_name = 'shopify_order_id'


    shopify_order_id = fields.Char('Shopify Order ID', required=True)
    odoo_order_id = fields.Many2one('sale.order', string='Odoo Sale Order', required=True)
    instance_id = fields.Many2one('shopify.instance', string='Shopify Instance', required=True)
    sync_status = fields.Selection([
        ('synced', 'Synced'),
        ('pending', 'Pending'),
        ('error', 'Error'),
    ], string='Sync Status', default='pending')
    last_sync = fields.Datetime('Last Sync')
    active = fields.Boolean('Active', default=True)
    note = fields.Text('Notes')


    _sql_constraints = [
        ('uniq_shopify_order_instance', 'unique(shopify_order_id, instance_id)', 'This Shopify order is already mapped for this instance!'),
    ]


    def _convert_shopify_datetime(self, shopify_date_str):
        """
        Convert Shopify datetime (ISO 8601) to Odoo datetime format.
        Shopify returns dates like: '2025-11-12T20:42:45-05:00'
        Odoo expects: '%Y-%m-%d %H:%M:%S' in UTC
        """
        if not shopify_date_str:
            return fields.Datetime.now()
        
        try:
            # Parse ISO 8601 format with timezone
            dt_object = datetime.fromisoformat(shopify_date_str)
            # Convert to UTC and remove timezone info (Odoo stores in UTC)
            if dt_object.tzinfo is not None:
                dt_utc = dt_object.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            else:
                dt_utc = dt_object
            return dt_utc
        except (ValueError, AttributeError) as e:
            # Fallback to current time if parsing fails
            return fields.Datetime.now()


    def import_orders_from_shopify(self, instance):
        """
        Import orders from Shopify for the given instance.
        Creates queue jobs and logs results.
        """
        if not instance:
            raise UserError(_('No Shopify instance provided.'))
        url = f"{instance.shop_url}/admin/api/2024-01/orders.json"
        try:
            response = requests.get(url, auth=(instance.api_key, instance.password), timeout=20)
            if response.status_code == 200:
                orders = response.json().get('orders', [])
                job = self.env['shopify.queue.job'].create({
                    'name': f'Import Orders ({instance.name})',
                    'job_type': 'import_order',
                    'instance_id': instance.id,
                    'status': 'in_progress',
                })
                self.env['shopify.log'].create({
                    'name': 'Order Import Started',
                    'log_type': 'info',
                    'job_id': job.id,
                    'message': f'Starting import of {len(orders)} orders from Shopify instance {instance.name}',
                })
                
                # Process each order
                created_count = 0
                updated_count = 0
                error_count = 0
                
                for shopify_order in orders:
                    try:
                        # Check if order already exists
                        existing_mapping = self.search([
                            ('shopify_order_id', '=', str(shopify_order['id'])),
                            ('instance_id', '=', instance.id)
                        ])
                        
                        if existing_mapping:
                            # Update existing order
                            odoo_order = existing_mapping.odoo_order_id
                            updated_count += 1
                        else:
                            # Create new Odoo sale order
                            # Get or create customer
                            customer_email = shopify_order.get('email', '')
                            customer = self.env['res.partner'].search([('email', '=', customer_email)], limit=1)
                            if not customer and customer_email:
                                customer = self.env['res.partner'].create({
                                    'name': f"{shopify_order.get('customer', {}).get('first_name', '')} {shopify_order.get('customer', {}).get('last_name', '')}".strip(),
                                    'email': customer_email,
                                    'is_company': False,
                                })
                            
                            # Create sale order
                            order_vals = {
                                'partner_id': customer.id if customer else self.env.ref('base.partner_admin').id,
                                'date_order': self._convert_shopify_datetime(shopify_order.get('created_at')),  # <- CAMBIO AQUÍ
                                'client_order_ref': f"Shopify-{shopify_order['id']}",
                                'note': f"Imported from Shopify Order #{shopify_order['id']}",
                            }
                            odoo_order = self.env['sale.order'].create(order_vals)
                            
                            # Add order lines
                            line_items = shopify_order.get('line_items', [])
                            for item in line_items:
                                # Find product by Shopify product ID
                                product_mapping = self.env['shopify.product'].search([
                                    ('shopify_product_id', '=', str(item.get('product_id'))),
                                    ('instance_id', '=', instance.id)
                                ], limit=1)
                                
                                if product_mapping:
                                    product = product_mapping.odoo_product_id
                                else:
                                    # Create placeholder product if not found
                                    product = self.env['product.product'].create({
                                        'name': item.get('name', 'Unknown Product'),
                                        'default_code': item.get('sku', ''),
                                        'list_price': float(item.get('price', 0)),
                                        'type': 'product',
                                        'categ_id': self.env.ref('product.product_category_all').id,
                                    })
                                
                                # Create order line
                                self.env['sale.order.line'].create({
                                    'order_id': odoo_order.id,
                                    'product_id': product.id,
                                    'name': item.get('name', ''),
                                    'product_uom_qty': item.get('quantity', 1),
                                    'price_unit': float(item.get('price', 0)),
                                })
                            
                            created_count += 1
                        
                        # Create or update mapping
                        mapping_vals = {
                            'shopify_order_id': str(shopify_order['id']),
                            'odoo_order_id': odoo_order.id,
                            'instance_id': instance.id,
                            'sync_status': 'synced',
                            'last_sync': fields.Datetime.now(),
                        }
                        
                        if existing_mapping:
                            existing_mapping.write(mapping_vals)
                        else:
                            self.create(mapping_vals)
                        
                    except Exception as e:
                        error_count += 1
                        self.env['shopify.log'].create({
                            'name': 'Order Import Error',
                            'log_type': 'error',
                            'job_id': job.id,
                            'message': f'Error importing order {shopify_order.get("id", "Unknown")}: {str(e)}',
                        })
                
                # Update job status
                job.write({'status': 'done'})
                self.env['shopify.log'].create({
                    'name': 'Order Import Completed',
                    'log_type': 'info',
                    'job_id': job.id,
                    'message': f'Import completed: {created_count} created, {updated_count} updated, {error_count} errors',
                })
                
                return orders
            else:
                job = self.env['shopify.queue.job'].create({
                    'name': f'Import Orders ({instance.name})',
                    'job_type': 'import_order',
                    'instance_id': instance.id,
                    'status': 'failed',
                    'error_message': response.text,
                })
                self.env['shopify.log'].create({
                    'name': 'Order Import Error',
                    'log_type': 'error',
                    'job_id': job.id,
                    'message': f'Failed to import orders: {response.text}',
                })
                raise UserError(_(f'Failed to import orders: {response.text}'))
        except Exception as e:
            job = self.env['shopify.queue.job'].create({
                'name': f'Import Orders ({instance.name})',
                'job_type': 'import_order',
                'instance_id': instance.id,
                'status': 'failed',
                'error_message': str(e),
            })
            self.env['shopify.log'].create({
                'name': 'Order Import Exception',
                'log_type': 'error',
                'job_id': job.id,
                'message': str(e),
            })
            raise UserError(_(f'Exception during order import: {str(e)}'))


    def export_orders_to_shopify(self, instance, orders):
        """
        Export orders to Shopify for the given instance.
        Creates queue jobs and logs results.
        """
        if not instance:
            raise UserError(_('No Shopify instance provided.'))
        job = self.env['shopify.queue.job'].create({
            'name': f'Export Orders ({instance.name})',
            'job_type': 'export_order',
            'instance_id': instance.id,
            'status': 'done',
        })
        self.env['shopify.log'].create({
            'name': 'Order Export',
            'log_type': 'info',
            'job_id': job.id,
            'message': f'Exported {len(orders)} orders to Shopify instance {instance.name}',
        })
        # (Scaffold) Actual export logic to be implemented
        return True


    @api.model
    def _run_order_import_cron(self):
        """
        Cron job method to automatically import orders from all active Shopify instances.
        """
        instances = self.env['shopify.instance'].search([('active', '=', True), ('state', '=', 'connected')])
        for instance in instances:
            try:
                self.import_orders_from_shopify(instance)
            except Exception as e:
                self.env['shopify.log'].create({
                    'name': 'Cron Order Import Error',
                    'log_type': 'error',
                    'message': f'Error importing orders for instance {instance.name}: {str(e)}',
                })
