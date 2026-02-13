from odoo import models, fields, api
import requests
from odoo.exceptions import UserError
from odoo.tools.translate import _

class ShopifyProduct(models.Model):
    _name = 'shopify.product'
    _description = 'Shopify Product Mapping'
    _rec_name = 'name'

    name = fields.Char('Shopify Product Name')
    shopify_product_id = fields.Char('Shopify Product ID', required=True)
    shopify_variant_id = fields.Char('Shopify Variant ID')
    odoo_product_id = fields.Many2one('product.product', string='Odoo Product', required=True)
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
        ('uniq_shopify_variant_instance', 'unique(shopify_variant_id, instance_id)', 'This Shopify variant is already mapped for this instance!'),
    ]

    def import_products_from_shopify(self, instance):
        """
        Import products from Shopify for the given instance.
        Creates queue jobs and logs results.
        """
        if not instance:
            raise UserError(_('No Shopify instance provided.'))
        url = f"{instance.shop_url}/admin/api/2024-01/products.json"
        try:
            response = requests.get(url, auth=(instance.api_key, instance.password), timeout=20)
            if response.status_code == 200:
                products = response.json().get('products', [])
                job = self.env['shopify.queue.job'].create({
                    'name': f'Import Products ({instance.name})',
                    'job_type': 'import_product',
                    'instance_id': instance.id,
                    'status': 'in_progress',
                })
                self.env['shopify.log'].create({
                    'name': 'Product Import Started',
                    'log_type': 'info',
                    'job_id': job.id,
                    'message': f'Starting import of {len(products)} products from Shopify instance {instance.name}',
                })
                
                # Process each product
                created_count = 0
                updated_count = 0
                error_count = 0
                
                for shopify_product in products:
                    try:
                        # Check if product already exists
                        existing_mapping = self.search([
                            ('shopify_product_id', '=', str(shopify_product['id'])),
                            ('instance_id', '=', instance.id)
                        ])
                        
                        if existing_mapping:
                            # Update existing product
                            odoo_product = existing_mapping.odoo_product_id
                            updated_count += 1
                        else:
                            # Create new Odoo product
                            odoo_product = self.env['product.product'].create({
                                'name': shopify_product.get('title', 'Unknown Product'),
                                'default_code': shopify_product.get('sku', ''),
                                'list_price': float(shopify_product.get('variants', [{}])[0].get('price', 0)),
                                'type': 'product',
                                'categ_id': self.env.ref('product.product_category_all').id,
                            })
                            created_count += 1
                        
                        # Create or update mapping
                        mapping_vals = {
                            'name': shopify_product.get('title', 'Unknown Product'),
                            'shopify_product_id': str(shopify_product['id']),
                            'odoo_product_id': odoo_product.id,
                            'instance_id': instance.id,
                            'sync_status': 'synced',
                            'last_sync': fields.Datetime.now(),
                        }
                        
                        if existing_mapping:
                            existing_mapping.write(mapping_vals)
                        else:
                            self.create(mapping_vals)
                        
                        # Handle variants if any
                        variants = shopify_product.get('variants', [])
                        for variant in variants:
                            variant_mapping = self.search([
                                ('shopify_variant_id', '=', str(variant['id'])),
                                ('instance_id', '=', instance.id)
                            ])
                            
                            if not variant_mapping:
                                # Create variant mapping (using same Odoo product for now)
                                self.create({
                                    'name': f"{shopify_product.get('title', 'Unknown Product')} - {variant.get('title', 'Default')}",
                                    'shopify_product_id': str(shopify_product['id']),
                                    'shopify_variant_id': str(variant['id']),
                                    'odoo_product_id': odoo_product.id,
                                    'instance_id': instance.id,
                                    'sync_status': 'synced',
                                    'last_sync': fields.Datetime.now(),
                                })
                        
                    except Exception as e:
                        error_count += 1
                        self.env['shopify.log'].create({
                            'name': 'Product Import Error',
                            'log_type': 'error',
                            'job_id': job.id,
                            'message': f'Error importing product {shopify_product.get("title", "Unknown")}: {str(e)}',
                        })
                
                # Update job status
                job.write({'status': 'done'})
                self.env['shopify.log'].create({
                    'name': 'Product Import Completed',
                    'log_type': 'info',
                    'job_id': job.id,
                    'message': f'Import completed: {created_count} created, {updated_count} updated, {error_count} errors',
                })
                
                return products
            else:
                job = self.env['shopify.queue.job'].create({
                    'name': f'Import Products ({instance.name})',
                    'job_type': 'import_product',
                    'instance_id': instance.id,
                    'status': 'failed',
                    'error_message': response.text,
                })
                self.env['shopify.log'].create({
                    'name': 'Product Import Error',
                    'log_type': 'error',
                    'job_id': job.id,
                    'message': f'Failed to import products: {response.text}',
                })
                raise UserError(_(f'Failed to import products: {response.text}'))
        except Exception as e:
            job = self.env['shopify.queue.job'].create({
                'name': f'Import Products ({instance.name})',
                'job_type': 'import_product',
                'instance_id': instance.id,
                'status': 'failed',
                'error_message': str(e),
            })
            self.env['shopify.log'].create({
                'name': 'Product Import Exception',
                'log_type': 'error',
                'job_id': job.id,
                'message': str(e),
            })
            raise UserError(_(f'Exception during product import: {str(e)}'))

    def export_products_to_shopify(self, instance, products):
        """
        Export products to Shopify for the given instance.
        Creates queue jobs and logs results.
        """
        if not instance:
            raise UserError(_('No Shopify instance provided.'))
        
        job = self.env['shopify.queue.job'].create({
            'name': f'Export Products ({instance.name})',
            'job_type': 'export_product',
            'instance_id': instance.id,
            'status': 'in_progress',
        })
        
        self.env['shopify.log'].create({
            'name': 'Product Export Started',
            'log_type': 'info',
            'job_id': job.id,
            'message': f'Starting export of {len(products)} products to Shopify instance {instance.name}',
        })
        
        exported_count = 0
        error_count = 0
        
        for product_mapping in products:
            try:
                odoo_product = product_mapping.odoo_product_id
                
                # Prepare product data for Shopify
                product_data = {
                    'product': {
                        'title': odoo_product.name,
                        'body_html': odoo_product.description or '',
                        'vendor': 'Odoo',
                        'product_type': 'Default',
                        'tags': '',
                        'variants': [{
                            'price': str(odoo_product.list_price),
                            'sku': odoo_product.default_code or '',
                            'inventory_quantity': int(odoo_product.qty_available) if odoo_product.type == 'product' else 0,
                            'inventory_management': 'shopify' if odoo_product.type == 'product' else 'continue',
                        }]
                    }
                }
                
                # Check if product already exists in Shopify
                if product_mapping.shopify_product_id:
                    # Update existing product
                    url = f"{instance.shop_url}/admin/api/2024-01/products/{product_mapping.shopify_product_id}.json"
                    response = requests.put(url, auth=(instance.api_key, instance.password), json=product_data, timeout=20)
                else:
                    # Create new product
                    url = f"{instance.shop_url}/admin/api/2024-01/products.json"
                    response = requests.post(url, auth=(instance.api_key, instance.password), json=product_data, timeout=20)
                
                if response.status_code in [200, 201]:
                    response_data = response.json()
                    shopify_product = response_data.get('product', {})
                    
                    # Update mapping with Shopify product ID
                    product_mapping.write({
                        'shopify_product_id': str(shopify_product.get('id')),
                        'sync_status': 'synced',
                        'last_sync': fields.Datetime.now(),
                    })
                    
                    exported_count += 1
                else:
                    error_count += 1
                    self.env['shopify.log'].create({
                        'name': 'Product Export Error',
                        'log_type': 'error',
                        'job_id': job.id,
                        'message': f'Failed to export product {odoo_product.name}: {response.text}',
                    })
                    
            except Exception as e:
                error_count += 1
                self.env['shopify.log'].create({
                    'name': 'Product Export Exception',
                    'log_type': 'error',
                    'job_id': job.id,
                    'message': f'Exception exporting product {product_mapping.odoo_product_id.name}: {str(e)}',
                })
        
        # Update job status
        job.write({'status': 'done'})
        self.env['shopify.log'].create({
            'name': 'Product Export',
            'log_type': 'info',
            'job_id': job.id,
            'message': f'Export completed: {exported_count} exported, {error_count} errors',
        })
        
        return True 

    @api.model
    def _run_product_import_cron(self):
        """
        Cron job method to automatically import products from all active Shopify instances.
        """
        instances = self.env['shopify.instance'].search([('active', '=', True), ('state', '=', 'connected')])
        for instance in instances:
            try:
                self.import_products_from_shopify(instance)
            except Exception as e:
                self.env['shopify.log'].create({
                    'name': 'Cron Product Import Error',
                    'log_type': 'error',
                    'message': f'Error importing products for instance {instance.name}: {str(e)}',
                }) 