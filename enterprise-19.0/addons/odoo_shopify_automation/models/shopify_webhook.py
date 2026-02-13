# -*- coding: utf-8 -*-
import logging
import json
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import config

_logger = logging.getLogger(__name__)

class ShopifyWebhook(models.Model):
    _name = 'shopify.webhook'
    _description = 'Shopify Webhook Configuration'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Webhook Name', required=True, tracking=True)
    instance_id = fields.Many2one('shopify.instance', string='Shopify Instance', required=True, ondelete='cascade')
    webhook_action = fields.Selection([
        ('products/create', 'Product Created'),
        ('products/update', 'Product Updated'),
        ('products/delete', 'Product Deleted'),
        ('orders/create', 'Order Created'),
        ('orders/updated', 'Order Updated'),
        ('orders/fulfilled', 'Order Fulfilled'),
        ('orders/cancelled', 'Order Cancelled'),
        ('customers/create', 'Customer Created'),
        ('customers/update', 'Customer Updated'),
        ('customers/delete', 'Customer Deleted'),
        ('inventory/update', 'Inventory Updated'),
        ('fulfillments/create', 'Fulfillment Created'),
        ('fulfillments/update', 'Fulfillment Updated'),
        ('refunds/create', 'Refund Created'),
        ('app/uninstalled', 'App Uninstalled'),
        ('shop/update', 'Shop Updated'),
        ('themes/publish', 'Theme Published'),
        ('carts/create', 'Cart Created'),
        ('carts/update', 'Cart Updated'),
        ('checkouts/create', 'Checkout Created'),
        ('checkouts/update', 'Checkout Updated'),
        ('collection_publications/create', 'Collection Publication Created'),
        ('collection_publications/delete', 'Collection Publication Deleted'),
        ('collection_publications/update', 'Collection Publication Updated'),
        ('collections/create', 'Collection Created'),
        ('collections/delete', 'Collection Deleted'),
        ('collections/update', 'Collection Updated'),
        ('customer_groups/create', 'Customer Group Created'),
        ('customer_groups/delete', 'Customer Group Deleted'),
        ('customer_groups/update', 'Customer Group Updated'),
        ('disputes/create', 'Dispute Created'),
        ('disputes/update', 'Dispute Updated'),
        ('domains/create', 'Domain Created'),
        ('domains/destroy', 'Domain Destroyed'),
        ('domains/update', 'Domain Updated'),
        ('inventory_items/create', 'Inventory Item Created'),
        ('inventory_items/delete', 'Inventory Item Deleted'),
        ('inventory_items/update', 'Inventory Item Updated'),
        ('inventory_levels/connect', 'Inventory Level Connected'),
        ('inventory_levels/disconnect', 'Inventory Level Disconnected'),
        ('inventory_levels/update', 'Inventory Level Updated'),
        ('locations/create', 'Location Created'),
        ('locations/delete', 'Location Deleted'),
        ('locations/update', 'Location Updated'),
        ('tender_transactions/create', 'Tender Transaction Created'),
        ('tender_transactions/update', 'Tender Transaction Updated'),
        ('themes/create', 'Theme Created'),
        ('themes/delete', 'Theme Deleted'),
        ('themes/update', 'Theme Updated'),
        ('variants/create', 'Variant Created'),
        ('variants/update', 'Variant Updated'),
        ('variants/delete', 'Variant Deleted'),
    ], string='Webhook Action', required=True, tracking=True)
    
    webhook_id = fields.Char('Shopify Webhook ID', readonly=True, tracking=True)
    delivery_url = fields.Text('Delivery URL', readonly=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('error', 'Error'),
    ], string='Status', default='draft', tracking=True)
    
    # Advanced Configuration
    format = fields.Selection([
        ('json', 'JSON'),
        ('xml', 'XML'),
    ], string='Format', default='json', required=True)
    
    api_version = fields.Char('API Version', default='2024-01', required=True)
    include_fields = fields.Text('Include Fields', help='Comma-separated list of fields to include')
    exclude_fields = fields.Text('Exclude Fields', help='Comma-separated list of fields to exclude')
    
    # Performance & Reliability
    retry_count = fields.Integer('Retry Count', default=3)
    timeout = fields.Integer('Timeout (seconds)', default=30)
    batch_size = fields.Integer('Batch Size', default=100)
    
    # Monitoring
    last_triggered = fields.Datetime('Last Triggered', readonly=True)
    success_count = fields.Integer('Success Count', default=0)
    error_count = fields.Integer('Error Count', default=0)
    average_response_time = fields.Float('Average Response Time (ms)', default=0.0)
    
    # Security
    signature_verification = fields.Boolean('Verify Signature', default=True)
    secret_key = fields.Char('Secret Key', help='HMAC secret for signature verification')
    
    # Advanced Features
    custom_headers = fields.Text('Custom Headers', help='JSON format: {"header": "value"}')
    custom_payload = fields.Text('Custom Payload Template', help='Jinja2 template for custom payload')
    conditional_logic = fields.Text('Conditional Logic', help='Python expression for conditional processing')
    
    # Integration
    auto_process = fields.Boolean('Auto Process', default=True)
    create_odoo_record = fields.Boolean('Create Odoo Record', default=True)
    update_odoo_record = fields.Boolean('Update Odoo Record', default=True)
    delete_odoo_record = fields.Boolean('Delete Odoo Record', default=False)
    
    # Logging
    log_level = fields.Selection([
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ], string='Log Level', default='info')
    
    note = fields.Text('Notes')
    
    _sql_constraints = [
        ('unique_webhook_action_instance', 'unique(webhook_action, instance_id)', 
         'A webhook with this action already exists for this instance!'),
    ]

    @api.constrains('delivery_url')
    def _check_delivery_url(self):
        for record in self:
            if record.delivery_url and not record.delivery_url.startswith('https://'):
                raise ValidationError(_('Delivery URL must use HTTPS protocol for security.'))

    def action_create_webhook(self):
        """Create webhook in Shopify"""
        for record in self:
            try:
                record._create_shopify_webhook()
                record.state = 'active'
                record.message_post(body=_('Webhook created successfully in Shopify'))
            except Exception as e:
                record.state = 'error'
                record.message_post(body=_('Failed to create webhook: %s') % str(e))
                raise UserError(_('Failed to create webhook: %s') % str(e))

    def action_delete_webhook(self):
        """Delete webhook from Shopify"""
        for record in self:
            try:
                record._delete_shopify_webhook()
                record.state = 'inactive'
                record.message_post(body=_('Webhook deleted successfully from Shopify'))
            except Exception as e:
                record.message_post(body=_('Failed to delete webhook: %s') % str(e))
                raise UserError(_('Failed to delete webhook: %s') % str(e))

    def action_test_webhook(self):
        """Test webhook delivery"""
        for record in self:
            try:
                result = record._test_webhook_delivery()
                record.message_post(body=_('Webhook test successful: %s') % result)
            except Exception as e:
                record.message_post(body=_('Webhook test failed: %s') % str(e))
                raise UserError(_('Webhook test failed: %s') % str(e))

    def _create_shopify_webhook(self):
        """Create webhook in Shopify store"""
        instance = self.instance_id
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        # Generate delivery URL
        route = self._get_webhook_route()
        delivery_url = f"{base_url}{route}"
        
        # Prepare webhook data
        webhook_data = {
            'topic': self.webhook_action,
            'address': delivery_url,
            'format': self.format,
            'api_version': self.api_version,
        }
        
        # Add custom headers if specified
        if self.custom_headers:
            try:
                headers = json.loads(self.custom_headers)
                webhook_data['fields'] = list(headers.keys())
            except json.JSONDecodeError:
                _logger.warning('Invalid custom headers JSON for webhook %s', self.name)
        
        # Create webhook via Shopify API
        headers = {
            'X-Shopify-Access-Token': instance.access_token or instance.password,
            'Content-Type': 'application/json',
        }
        
        url = f"{instance.shop_url}/admin/api/{self.api_version}/webhooks.json"
        response = requests.post(url, headers=headers, json={'webhook': webhook_data}, timeout=self.timeout)
        
        if response.status_code == 201:
            webhook_response = response.json()
            self.write({
                'webhook_id': str(webhook_response['webhook']['id']),
                'delivery_url': delivery_url,
                'state': 'active',
            })
            _logger.info('Webhook %s created successfully in Shopify', self.name)
        else:
            raise UserError(_('Failed to create webhook. Status: %s, Response: %s') % 
                          (response.status_code, response.text))

    def _delete_shopify_webhook(self):
        """Delete webhook from Shopify store"""
        if not self.webhook_id:
            return
            
        instance = self.instance_id
        headers = {
            'X-Shopify-Access-Token': instance.access_token or instance.password,
        }
        
        url = f"{instance.shop_url}/admin/api/{self.api_version}/webhooks/{self.webhook_id}.json"
        response = requests.delete(url, headers=headers, timeout=self.timeout)
        
        if response.status_code == 200:
            self.write({
                'webhook_id': False,
                'delivery_url': False,
                'state': 'inactive',
            })
            _logger.info('Webhook %s deleted successfully from Shopify', self.name)
        else:
            raise UserError(_('Failed to delete webhook. Status: %s, Response: %s') % 
                          (response.status_code, response.text))

    def _test_webhook_delivery(self):
        """Test webhook delivery with sample data"""
        # Generate sample payload based on webhook action
        sample_payload = self._generate_sample_payload()
        
        # Send test request to delivery URL
        headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Topic': self.webhook_action,
            'X-Shopify-Hmac-Sha256': self._generate_hmac_signature(sample_payload),
            'X-Shopify-Shop-Domain': self.instance_id.shop_url,
        }
        
        response = requests.post(
            self.delivery_url, 
            headers=headers, 
            json=sample_payload, 
            timeout=self.timeout
        )
        
        if response.status_code == 200:
            return 'Test payload delivered successfully'
        else:
            raise UserError(_('Test delivery failed. Status: %s, Response: %s') % 
                          (response.status_code, response.text))

    def _get_webhook_route(self):
        """Get webhook route based on action"""
        action_routes = {
            'products/create': '/shopify/webhook/product/create',
            'products/update': '/shopify/webhook/product/update',
            'products/delete': '/shopify/webhook/product/delete',
            'orders/create': '/shopify/webhook/order/create',
            'orders/updated': '/shopify/webhook/order/update',
            'orders/fulfilled': '/shopify/webhook/order/fulfilled',
            'orders/cancelled': '/shopify/webhook/order/cancelled',
            'customers/create': '/shopify/webhook/customer/create',
            'customers/update': '/shopify/webhook/customer/update',
            'customers/delete': '/shopify/webhook/customer/delete',
            'inventory/update': '/shopify/webhook/inventory/update',
            'fulfillments/create': '/shopify/webhook/fulfillment/create',
            'fulfillments/update': '/shopify/webhook/fulfillment/update',
            'refunds/create': '/shopify/webhook/refund/create',
        }
        return action_routes.get(self.webhook_action, '/shopify/webhook/generic')

    def _generate_sample_payload(self):
        """Generate sample payload for testing"""
        if 'product' in self.webhook_action:
            return {
                'id': 123456789,
                'title': 'Sample Product',
                'body_html': '<p>Sample product description</p>',
                'vendor': 'Sample Vendor',
                'product_type': 'Sample Type',
                'created_at': '2024-01-01T00:00:00-05:00',
                'updated_at': '2024-01-01T00:00:00-05:00',
                'published_at': '2024-01-01T00:00:00-05:00',
                'template_suffix': None,
                'status': 'active',
                'published_scope': 'web',
                'tags': 'sample, test',
                'admin_graphql_api_id': 'gid://shopify/Product/123456789',
                'variants': [],
                'options': [],
                'images': [],
                'image': None,
            }
        elif 'order' in self.webhook_action:
            return {
                'id': 123456789,
                'email': 'test@example.com',
                'closed_at': None,
                'created_at': '2024-01-01T00:00:00-05:00',
                'updated_at': '2024-01-01T00:00:00-05:00',
                'number': 1,
                'note': None,
                'token': 'sample_token',
                'gateway': 'manual',
                'test': False,
                'total_price': '10.00',
                'subtotal_price': '10.00',
                'total_weight': 0,
                'total_tax': '0.00',
                'taxes_included': False,
                'currency': 'USD',
                'financial_status': 'paid',
                'confirmed': True,
                'total_discounts': '0.00',
                'total_line_items_price': '10.00',
                'cart_token': 'sample_cart_token',
                'buyer_accepts_marketing': False,
                'name': '#1001',
                'referring_site': None,
                'landing_site': None,
                'cancelled_at': None,
                'cancel_reason': None,
                'total_price_usd': '10.00',
                'checkout_token': 'sample_checkout_token',
                'reference': None,
                'user_id': None,
                'location_id': None,
                'source_identifier': None,
                'source_url': None,
                'processed_at': '2024-01-01T00:00:00-05:00',
                'device_id': None,
                'phone': None,
                'customer_locale': 'en',
                'app_id': None,
                'browser_ip': None,
                'landing_site_ref': None,
                'order_number': 1001,
                'discount_applications': [],
                'discount_codes': [],
                'note_attributes': [],
                'payment_gateway_names': ['manual'],
                'processing_method': 'manual',
                'checkout_id': None,
                'source_name': 'web',
                'fulfillment_status': None,
                'tax_lines': [],
                'tags': '',
                'contact_email': 'test@example.com',
                'order_status_url': 'https://sample.myshopify.com/orders/sample_token/authenticate?key=sample_key',
                'presentment_currency': 'USD',
                'total_line_items_price_set': {'shop_money': {'amount': '10.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '10.00', 'currency_code': 'USD'}},
                'total_discounts_set': {'shop_money': {'amount': '0.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '0.00', 'currency_code': 'USD'}},
                'total_shipping_price_set': {'shop_money': {'amount': '0.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '0.00', 'currency_code': 'USD'}},
                'subtotal_price_set': {'shop_money': {'amount': '10.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '10.00', 'currency_code': 'USD'}},
                'total_price_set': {'shop_money': {'amount': '10.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '10.00', 'currency_code': 'USD'}},
                'total_tax_set': {'shop_money': {'amount': '0.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '0.00', 'currency_code': 'USD'}},
                'line_items': [],
                'shipping_lines': [],
                'billing_address': None,
                'shipping_address': None,
                'fulfillments': [],
                'client_details': None,
                'refunds': [],
                'customer': None,
            }
        elif 'customer' in self.webhook_action:
            return {
                'id': 123456789,
                'email': 'test@example.com',
                'accepts_marketing': False,
                'created_at': '2024-01-01T00:00:00-05:00',
                'updated_at': '2024-01-01T00:00:00-05:00',
                'first_name': 'John',
                'last_name': 'Doe',
                'orders_count': 0,
                'state': 'disabled',
                'total_spent': '0.00',
                'last_order_id': None,
                'note': None,
                'verified_email': True,
                'multipass_identifier': None,
                'tax_exempt': False,
                'phone': None,
                'tags': '',
                'last_order_name': None,
                'currency': 'USD',
                'addresses': [],
                'accepts_marketing_updated_at': '2024-01-01T00:00:00-05:00',
                'marketing_opt_in_level': None,
                'tax_exemptions': [],
                'admin_graphql_api_id': 'gid://shopify/Customer/123456789',
                'default_address': None,
            }
        else:
            return {'id': 123456789, 'test': True}

    def _generate_hmac_signature(self, payload):
        """Generate HMAC signature for webhook verification"""
        if not self.secret_key:
            return ''
        
        import hmac
        import hashlib
        
        payload_str = json.dumps(payload, separators=(',', ':'))
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature

    @api.model
    def process_webhook_payload(self, webhook_action, payload, headers):
        """Process incoming webhook payload"""
        webhook = self.search([
            ('webhook_action', '=', webhook_action),
            ('state', '=', 'active')
        ], limit=1)
        
        if not webhook:
            _logger.warning('No active webhook found for action: %s', webhook_action)
            return False
        
        # Verify signature if enabled
        if webhook.signature_verification and webhook.secret_key:
            if not webhook._verify_webhook_signature(payload, headers):
                _logger.error('Webhook signature verification failed for action: %s', webhook_action)
                return False
        
        # Update webhook statistics
        webhook.write({
            'last_triggered': fields.Datetime.now(),
            'success_count': webhook.success_count + 1,
        })
        
        # Process payload based on action
        try:
            if 'product' in webhook_action:
                webhook._process_product_webhook(payload)
            elif 'order' in webhook_action:
                webhook._process_order_webhook(payload)
            elif 'customer' in webhook_action:
                webhook._process_customer_webhook(payload)
            elif 'inventory' in webhook_action:
                webhook._process_inventory_webhook(payload)
            else:
                webhook._process_generic_webhook(payload)
                
            return True
        except Exception as e:
            webhook.write({'error_count': webhook.error_count + 1})
            webhook.message_post(body=_('Webhook processing error: %s') % str(e))
            _logger.error('Webhook processing error for action %s: %s', webhook_action, str(e))
            return False

    def _verify_webhook_signature(self, payload, headers):
        """Verify webhook signature"""
        if not self.secret_key:
            return True
            
        hmac_header = headers.get('X-Shopify-Hmac-Sha256', '')
        if not hmac_header:
            return False
            
        expected_signature = self._generate_hmac_signature(payload)
        return hmac.compare_digest(hmac_header, expected_signature)

    def _process_product_webhook(self, payload):
        """Process product webhook payload"""
        product_data = payload
        shopify_product = self.env['shopify.product'].search([
            ('shopify_product_id', '=', str(product_data.get('id'))),
            ('instance_id', '=', self.instance_id.id)
        ], limit=1)
        
        if self.webhook_action == 'products/create':
            if not shopify_product:
                self.env['shopify.product'].create({
                    'instance_id': self.instance_id.id,
                    'shopify_product_id': str(product_data.get('id')),
                    'name': product_data.get('title'),
                    'description': product_data.get('body_html'),
                    'vendor': product_data.get('vendor'),
                    'product_type': product_data.get('product_type'),
                    'status': product_data.get('status'),
                    'tags': product_data.get('tags'),
                })
        elif self.webhook_action == 'products/update':
            if shopify_product:
                shopify_product.write({
                    'name': product_data.get('title'),
                    'description': product_data.get('body_html'),
                    'vendor': product_data.get('vendor'),
                    'product_type': product_data.get('product_type'),
                    'status': product_data.get('status'),
                    'tags': product_data.get('tags'),
                })
        elif self.webhook_action == 'products/delete':
            if shopify_product:
                shopify_product.write({'active': False})

    def _process_order_webhook(self, payload):
        """Process order webhook payload"""
        order_data = payload
        shopify_order = self.env['shopify.order'].search([
            ('shopify_order_id', '=', str(order_data.get('id'))),
            ('instance_id', '=', self.instance_id.id)
        ], limit=1)
        
        if self.webhook_action in ['orders/create', 'orders/updated']:
            if not shopify_order:
                self.env['shopify.order'].create({
                    'instance_id': self.instance_id.id,
                    'shopify_order_id': str(order_data.get('id')),
                    'order_number': order_data.get('order_number'),
                    'email': order_data.get('email'),
                    'total_price': float(order_data.get('total_price', 0)),
                    'currency': order_data.get('currency'),
                    'financial_status': order_data.get('financial_status'),
                    'fulfillment_status': order_data.get('fulfillment_status'),
                    'created_at': order_data.get('created_at'),
                })
            else:
                shopify_order.write({
                    'total_price': float(order_data.get('total_price', 0)),
                    'financial_status': order_data.get('financial_status'),
                    'fulfillment_status': order_data.get('fulfillment_status'),
                })

    def _process_customer_webhook(self, payload):
        """Process customer webhook payload"""
        customer_data = payload
        shopify_customer = self.env['shopify.customer'].search([
            ('shopify_customer_id', '=', str(customer_data.get('id'))),
            ('instance_id', '=', self.instance_id.id)
        ], limit=1)
        
        if self.webhook_action in ['customers/create', 'customers/update']:
            if not shopify_customer:
                self.env['shopify.customer'].create({
                    'instance_id': self.instance_id.id,
                    'shopify_customer_id': str(customer_data.get('id')),
                    'email': customer_data.get('email'),
                    'first_name': customer_data.get('first_name'),
                    'last_name': customer_data.get('last_name'),
                    'phone': customer_data.get('phone'),
                    'total_spent': float(customer_data.get('total_spent', 0)),
                    'orders_count': customer_data.get('orders_count', 0),
                })
            else:
                shopify_customer.write({
                    'email': customer_data.get('email'),
                    'first_name': customer_data.get('first_name'),
                    'last_name': customer_data.get('last_name'),
                    'phone': customer_data.get('phone'),
                    'total_spent': float(customer_data.get('total_spent', 0)),
                    'orders_count': customer_data.get('orders_count', 0),
                })

    def _process_inventory_webhook(self, payload):
        """Process inventory webhook payload"""
        # Handle inventory updates
        pass

    def _process_generic_webhook(self, payload):
        """Process generic webhook payload"""
        # Log generic webhook for debugging
        _logger.info('Generic webhook received: %s', payload)

    @api.model
    def create(self, vals):
        """Override create to auto-create webhook in Shopify if needed"""
        webhook = super().create(vals)
        if webhook.auto_process and webhook.state == 'draft':
            webhook.action_create_webhook()
        return webhook

    def unlink(self):
        """Override unlink to delete webhook from Shopify"""
        for record in self:
            if record.webhook_id:
                record.action_delete_webhook()
        return super().unlink() 