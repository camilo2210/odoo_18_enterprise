from odoo import http
from odoo.http import request, route
import logging

_logger = logging.getLogger(__name__)

class ShopifyWebhookController(http.Controller):
    @route(['/shopify/webhook/product'], type='json', auth='public', csrf=False, methods=['POST'])
    def shopify_webhook_product(self, **post):
        _logger.info('Received Shopify Product Webhook: %s', post)
        job = request.env['shopify.queue.job'].sudo().create({
            'name': 'Webhook Product Import',
            'job_type': 'import_product',
            'instance_id': None,  # To be set by matching shop URL or header
            'status': 'pending',
        })
        request.env['shopify.log'].sudo().create({
            'name': 'Product Webhook',
            'log_type': 'info',
            'job_id': job.id,
            'message': str(post),
        })
        # (Scaffold) Add logic to process and map product data
        return {'status': 'ok'}

    @route(['/shopify/webhook/order'], type='json', auth='public', csrf=False, methods=['POST'])
    def shopify_webhook_order(self, **post):
        _logger.info('Received Shopify Order Webhook: %s', post)
        job = request.env['shopify.queue.job'].sudo().create({
            'name': 'Webhook Order Import',
            'job_type': 'import_order',
            'instance_id': None,  # To be set by matching shop URL or header
            'status': 'pending',
        })
        request.env['shopify.log'].sudo().create({
            'name': 'Order Webhook',
            'log_type': 'info',
            'job_id': job.id,
            'message': str(post),
        })
        # (Scaffold) Add logic to process and map order data
        return {'status': 'ok'}

    @route(['/shopify/webhook/customer'], type='json', auth='public', csrf=False, methods=['POST'])
    def shopify_webhook_customer(self, **post):
        _logger.info('Received Shopify Customer Webhook: %s', post)
        job = request.env['shopify.queue.job'].sudo().create({
            'name': 'Webhook Customer Import',
            'job_type': 'import_customer',
            'instance_id': None,  # To be set by matching shop URL or header
            'status': 'pending',
        })
        request.env['shopify.log'].sudo().create({
            'name': 'Customer Webhook',
            'log_type': 'info',
            'job_id': job.id,
            'message': str(post),
        })
        # (Scaffold) Add logic to process and map customer data
        return {'status': 'ok'} 