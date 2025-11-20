# -*- coding: utf-8 -*-
import logging
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class ShopifyCarrier(models.Model):
    _name = 'shopify.carrier'
    _description = 'Shopify Delivery Carrier'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Carrier Name', required=True, tracking=True)
    code = fields.Char('Carrier Code', required=True, tracking=True)
    active = fields.Boolean('Active', default=True, tracking=True)
    
    # Shopify Integration
    shopify_code = fields.Char('Shopify Code', tracking=True)
    shopify_source = fields.Char('Shopify Source', tracking=True)
    shopify_tracking_company = fields.Selection([
        # Major International Carriers
        ('DHL Express', 'DHL Express'),
        ('DHL eCommerce', 'DHL eCommerce'),
        ('DHL Parcel', 'DHL Parcel'),
        ('FedEx', 'FedEx'),
        ('UPS', 'UPS'),
        ('USPS', 'USPS'),
        ('Canada Post CA', 'Canada Post CA'),
        ('Royal Mail', 'Royal Mail'),
        ('Australia Post', 'Australia Post'),
        ('New Zealand Post', 'New Zealand Post'),
        ('Japan Post', 'Japan Post'),
        ('China Post', 'China Post'),
        ('Singapore Post SG', 'Singapore Post SG'),
        ('Hong Kong Post', 'Hong Kong Post'),
        ('Korea Post', 'Korea Post'),
        ('India Post IN', 'India Post IN'),
        ('Brazil Post', 'Brazil Post'),
        ('Correios', 'Correios'),
        ('Mexico Post', 'Mexico Post'),
        ('Canada Post MX', 'Canada Post MX'),
        
        # European Carriers
        ('Deutsche Post', 'Deutsche Post'),
        ('La Poste', 'La Poste'),
        ('PostNL', 'PostNL'),
        ('PostNord', 'PostNord'),
        ('GLS', 'GLS'),
        ('DPD', 'DPD'),
        ('TNT', 'TNT'),
        ('Colissimo', 'Colissimo'),
        ('Chronopost', 'Chronopost'),
        ('Mondial Relay', 'Mondial Relay'),
        ('BPost', 'BPost'),
        ('CTT', 'CTT'),
        ('Correos', 'Correos'),
        ('Swiss Post', 'Swiss Post'),
        ('Österreichische Post', 'Österreichische Post'),
        ('Poste Italiane', 'Poste Italiane'),
        ('Hellenic Post', 'Hellenic Post'),
        ('Poczta Polska', 'Poczta Polska'),
        ('Magyar Posta', 'Magyar Posta'),
        ('Česká pošta', 'Česká pošta'),
        ('Slovenská pošta', 'Slovenská pošta'),
        ('Slovenian Post', 'Slovenian Post'),
        ('Croatian Post', 'Croatian Post'),
        ('Bulgarian Post', 'Bulgarian Post'),
        ('Romanian Post', 'Romanian Post'),
        ('Estonian Post', 'Estonian Post'),
        ('Latvia Post', 'Latvia Post'),
        ('Lietuvos Paštas', 'Lietuvos Paštas'),
        ('Iceland Post', 'Iceland Post'),
        ('Norway Post', 'Norway Post'),
        ('Finland Post', 'Finland Post'),
        ('Sweden Post', 'Sweden Post'),
        ('Denmark Post', 'Denmark Post'),
        
        # Asian Carriers
        ('SF Express', 'SF Express'),
        ('YTO Express', 'YTO Express'),
        ('ZTO Express', 'ZTO Express'),
        ('STO Express', 'STO Express'),
        ('Yunda Express', 'Yunda Express'),
        ('Best Express', 'Best Express'),
        ('JD Logistics', 'JD Logistics'),
        ('Cainiao', 'Cainiao'),
        ('Yamato', 'Yamato'),
        ('Sagawa', 'Sagawa'),
        ('Nippon Express', 'Nippon Express'),
        ('Korea Express', 'Korea Express'),
        ('CJ Logistics', 'CJ Logistics'),
        ('Lotte Express', 'Lotte Express'),
        ('Singapore Post MY', 'Singapore Post MY'),
        ('NinjaVan', 'NinjaVan'),
        ('J&T Express', 'J&T Express'),
        ('Lazada Express', 'Lazada Express'),
        ('GrabExpress', 'GrabExpress'),
        ('Flash Express', 'Flash Express'),
        ('Kerry Express', 'Kerry Express'),
        ('Thailand Post', 'Thailand Post'),
        ('Vietnam Post', 'Vietnam Post'),
        ('Philippines Post', 'Philippines Post'),
        ('Indonesia Post', 'Indonesia Post'),
        ('Malaysia Post', 'Malaysia Post'),
        ('India Post PH', 'India Post PH'),
        ('DTDC IN', 'DTDC IN'),
        ('Blue Dart', 'Blue Dart'),
        ('Gati', 'Gati'),
        ('Professional Couriers IN', 'Professional Couriers IN'),
        ('XpressBees IN', 'XpressBees IN'),
        ('Ecom Express IN', 'Ecom Express IN'),
        ('Ekart IN', 'Ekart IN'),
        ('Shadowfax IN', 'Shadowfax IN'),
        ('Delhivery', 'Delhivery'),
        
        # Middle East & Africa
        ('Aramex', 'Aramex'),
        ('Saudi Post', 'Saudi Post'),
        ('Emirates Post', 'Emirates Post'),
        ('Qatar Post', 'Qatar Post'),
        ('Kuwait Post', 'Kuwait Post'),
        ('Bahrain Post', 'Bahrain Post'),
        ('Oman Post', 'Oman Post'),
        ('Egypt Post', 'Egypt Post'),
        ('South Africa Post', 'South Africa Post'),
        ('Nigeria Post', 'Nigeria Post'),
        ('Kenya Post', 'Kenya Post'),
        ('Ghana Post', 'Ghana Post'),
        ('Morocco Post', 'Morocco Post'),
        ('Tunisia Post', 'Tunisia Post'),
        ('Algeria Post', 'Algeria Post'),
        
        # Specialized Carriers
        ('Amazon Logistics', 'Amazon Logistics'),
        ('Amazon Logistics UK', 'Amazon Logistics UK'),
        ('Amazon Logistics US', 'Amazon Logistics US'),
        ('eBay Global Shipping', 'eBay Global Shipping'),
        ('Walmart Fulfillment', 'Walmart Fulfillment'),
        ('Shopify Shipping', 'Shopify Shipping'),
        ('ShipBob', 'ShipBob'),
        ('ShipMonk', 'ShipMonk'),
        ('ShipHero', 'ShipHero'),
        ('ShipStation', 'ShipStation'),
        ('EasyPost', 'EasyPost'),
        ('Shippo', 'Shippo'),
        ('Parcel2Go', 'Parcel2Go'),
        ('ParcelForce', 'ParcelForce'),
        ('Yodel', 'Yodel'),
        ('Hermes', 'Hermes'),
        ('Evri', 'Evri'),
        ('DPD Local', 'DPD Local'),
        ('DPD UK', 'DPD UK'),
        ('DPD Ireland', 'DPD Ireland'),
        ('GLS Italy', 'GLS Italy'),
        ('GLS (US)', 'GLS (US)'),
        ('Bring NO', 'Bring NO'),
        ('PostNord DK', 'PostNord DK'),
        ('PostNord NO', 'PostNord NO'),
        ('PostNord SE', 'PostNord SE'),
        ('Inpost PL', 'Inpost PL'),
        ('Packeta', 'Packeta'),
        ('Zásilkovna', 'Zásilkovna'),
        ('Venipak', 'Venipak'),
        ('Omniva', 'Omniva'),
        ('Itella', 'Itella'),
        ('Matkahuolto', 'Matkahuolto'),
        ('Bring SE', 'Bring SE'),
        ('Posten Norge', 'Posten Norge'),
        ('Bring DK', 'Bring DK'),
        ('Swiss Post CH', 'Swiss Post CH'),
        ('Österreichische Post AT', 'Österreichische Post AT'),
        ('Deutsche Post (DE)', 'Deutsche Post (DE)'),
        ('Deutsche Post (EN)', 'Deutsche Post (EN)'),
        ('DHL', 'DHL'),
        ('Swiship', 'Swiship'),
        ('Hermes DE', 'Hermes DE'),
        ('SEUR', 'SEUR'),
        ('Colissimo ES', 'Colissimo ES'),
        ('Mondial Relay ES', 'Mondial Relay ES'),
        ('Colis Privé', 'Colis Privé'),
        ('Evri DE', 'Evri DE'),
        ('Parcelforce UK', 'Parcelforce UK'),
        ('Yodel IE', 'Yodel IE'),
        ('DHL Parcel DE', 'DHL Parcel DE'),
        ('Tuffnells', 'Tuffnells'),
        ('ACS Courier', 'ACS Courier'),
        ('Fastway IE', 'Fastway IE'),
        ('DPD Ireland IE', 'DPD Ireland IE'),
        ('DTDC UK', 'DTDC UK'),
        ('India Post UK', 'India Post UK'),
        ('Gati KWE', 'Gati KWE'),
        ('Professional Couriers UK', 'Professional Couriers UK'),
        ('XpressBees UK', 'XpressBees UK'),
        ('Ecom Express UK', 'Ecom Express UK'),
        ('Ekart UK', 'Ekart UK'),
        ('Shadowfax UK', 'Shadowfax UK'),
        ('BRT', 'BRT'),
        ('GLS Italy UK', 'GLS Italy UK'),
        ('DHL Parcel UK', 'DHL Parcel UK'),
        ('Bring IT', 'Bring IT'),
        ('Inpost UK', 'Inpost UK'),
        ('PTT', 'PTT'),
        ('Yurtiçi Kargo', 'Yurtiçi Kargo'),
        ('Aras Kargo', 'Aras Kargo'),
        ('Sürat Kargo', 'Sürat Kargo'),
        ('Alliance Air Freight', 'Alliance Air Freight'),
        ('Pilot Freight', 'Pilot Freight'),
        ('LSO', 'LSO'),
        ('Old Dominion', 'Old Dominion'),
        ('R+L Carriers', 'R+L Carriers'),
        ('Southwest Air Cargo', 'Southwest Air Cargo'),
        ('Fastway UK', 'Fastway UK'),
        ('Skynet', 'Skynet'),
        ('Italy BTR', 'Italy BTR'),
    ], string='Shopify Tracking Company', tracking=True)
    
    # Odoo Integration
    delivery_carrier_id = fields.Many2one('delivery.carrier', string='Odoo Delivery Carrier', tracking=True)
    product_id = fields.Many2one('product.product', string='Carrier Product', tracking=True)
    
    # Service Configuration
    service_type = fields.Selection([
        ('domestic', 'Domestic'),
        ('international', 'International'),
        ('express', 'Express'),
        ('economy', 'Economy'),
        ('same_day', 'Same Day'),
        ('next_day', 'Next Day'),
        ('ground', 'Ground'),
        ('air', 'Air'),
        ('sea', 'Sea'),
        ('rail', 'Rail'),
    ], string='Service Type', default='domestic', tracking=True)
    
    # Coverage
    supported_countries = fields.Many2many('res.country', string='Supported Countries')
    supported_regions = fields.Text('Supported Regions', help='Comma-separated list of regions/states')
    excluded_countries = fields.Many2many('res.country', 'shopify_carrier_excluded_countries_rel', 
                                        'carrier_id', 'country_id', string='Excluded Countries')
    
    # Pricing & Performance
    base_price = fields.Float('Base Price', default=0.0, tracking=True)
    price_per_kg = fields.Float('Price per KG', default=0.0, tracking=True)
    max_weight = fields.Float('Max Weight (KG)', tracking=True)
    min_weight = fields.Float('Min Weight (KG)', default=0.0, tracking=True)
    max_dimensions = fields.Char('Max Dimensions (LxWxH cm)', tracking=True)
    
    # Delivery Times
    estimated_delivery_days = fields.Integer('Estimated Delivery Days', tracking=True)
    max_delivery_days = fields.Integer('Max Delivery Days', tracking=True)
    same_day_cutoff_time = fields.Float('Same Day Cutoff Time (24h)', tracking=True)
    
    # Tracking & API
    tracking_url_template = fields.Text('Tracking URL Template', 
                                       help='Use {tracking_number} as placeholder', tracking=True)
    api_endpoint = fields.Char('API Endpoint', tracking=True)
    api_key = fields.Char('API Key', tracking=True)
    api_secret = fields.Char('API Secret', tracking=True)
    
    # Advanced Features
    real_time_tracking = fields.Boolean('Real-time Tracking', default=True, tracking=True)
    signature_required = fields.Boolean('Signature Required', default=False, tracking=True)
    insurance_available = fields.Boolean('Insurance Available', default=False, tracking=True)
    insurance_rate = fields.Float('Insurance Rate (%)', default=0.0, tracking=True)
    
    # Performance Metrics
    delivery_success_rate = fields.Float('Delivery Success Rate (%)', default=100.0, tracking=True)
    average_delivery_time = fields.Float('Average Delivery Time (Days)', tracking=True)
    customer_satisfaction = fields.Float('Customer Satisfaction (1-5)', tracking=True)
    
    # Configuration
    auto_create_shipment = fields.Boolean('Auto Create Shipment', default=True, tracking=True)
    auto_generate_label = fields.Boolean('Auto Generate Label', default=True, tracking=True)
    auto_send_tracking = fields.Boolean('Auto Send Tracking', default=True, tracking=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('testing', 'Testing'),
    ], string='Status', default='draft', tracking=True)
    
    # Analytics
    total_shipments = fields.Integer('Total Shipments', compute='_compute_analytics')
    successful_deliveries = fields.Integer('Successful Deliveries', compute='_compute_analytics')
    failed_deliveries = fields.Integer('Failed Deliveries', compute='_compute_analytics')
    total_revenue = fields.Monetary('Total Revenue', currency_field='currency_id', compute='_compute_analytics')
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                 default=lambda self: self.env.company.currency_id)
    
    note = fields.Text('Notes')
    
    _sql_constraints = [
        ('unique_carrier_code', 'unique(code)', 'Carrier code must be unique!'),
    ]

    @api.depends('delivery_carrier_id')
    def _compute_analytics(self):
        for record in self:
            # Get shipments for this carrier
            shipments = self.env['stock.picking'].search([
                ('carrier_id', '=', record.delivery_carrier_id.id),
                ('state', 'in', ['done', 'cancel'])
            ])
            
            record.total_shipments = len(shipments)
            record.successful_deliveries = len(shipments.filtered(lambda s: s.state == 'done'))
            record.failed_deliveries = len(shipments.filtered(lambda s: s.state == 'cancel'))
            
            # Calculate revenue from successful deliveries
            successful_shipments = shipments.filtered(lambda s: s.state == 'done')
            record.total_revenue = sum(successful_shipments.mapped('sale_id.amount_total'))

    def action_activate(self):
        """Activate carrier"""
        for record in self:
            record.state = 'active'
            record.message_post(body=_('Carrier activated successfully'))

    def action_deactivate(self):
        """Deactivate carrier"""
        for record in self:
            record.state = 'inactive'
            record.message_post(body=_('Carrier deactivated successfully'))

    def action_test_connection(self):
        """Test API connection"""
        for record in self:
            try:
                result = record._test_api_connection()
                record.message_post(body=_('API connection test successful: %s') % result)
            except Exception as e:
                record.message_post(body=_('API connection test failed: %s') % str(e))
                raise UserError(_('API connection test failed: %s') % str(e))

    def action_generate_shipping_label(self, picking):
        """Generate shipping label for picking"""
        for record in self:
            try:
                label_data = record._generate_shipping_label(picking)
                return label_data
            except Exception as e:
                record.message_post(body=_('Failed to generate shipping label: %s') % str(e))
                raise UserError(_('Failed to generate shipping label: %s') % str(e))

    def action_track_shipment(self, tracking_number):
        """Track shipment with real-time updates"""
        for record in self:
            try:
                tracking_data = record._track_shipment(tracking_number)
                return tracking_data
            except Exception as e:
                record.message_post(body=_('Failed to track shipment: %s') % str(e))
                raise UserError(_('Failed to track shipment: %s') % str(e))

    def _test_api_connection(self):
        """Test API connection to carrier"""
        if not self.api_endpoint or not self.api_key:
            raise UserError(_('API endpoint and key are required for testing'))
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        
        # Test endpoint (varies by carrier)
        test_url = f"{self.api_endpoint}/test"
        response = requests.get(test_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return 'Connection successful'
        else:
            raise UserError(_('Connection failed. Status: %s') % response.status_code)

    def _generate_shipping_label(self, picking):
        """Generate shipping label for picking"""
        # This is a generic implementation - each carrier would have specific logic
        label_data = {
            'tracking_number': self._generate_tracking_number(),
            'label_url': f"https://example.com/labels/{picking.name}",
            'carrier': self.name,
            'service_type': self.service_type,
            'estimated_delivery': self._calculate_estimated_delivery(),
        }
        
        # Update picking with tracking info
        picking.write({
            'carrier_tracking_ref': label_data['tracking_number'],
            'carrier_id': self.delivery_carrier_id.id,
        })
        
        return label_data

    def _track_shipment(self, tracking_number):
        """Track shipment with real-time updates"""
        if not self.tracking_url_template:
            raise UserError(_('Tracking URL template not configured'))
        
        tracking_url = self.tracking_url_template.replace('{tracking_number}', tracking_number)
        
        # Make API call to get tracking info
        headers = {}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        response = requests.get(tracking_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            tracking_data = response.json()
            return self._parse_tracking_data(tracking_data)
        else:
            raise UserError(_('Failed to get tracking info. Status: %s') % response.status_code)

    def _parse_tracking_data(self, tracking_data):
        """Parse tracking data from carrier API"""
        # Generic parsing - each carrier would have specific format
        return {
            'status': tracking_data.get('status', 'unknown'),
            'location': tracking_data.get('location', ''),
            'timestamp': tracking_data.get('timestamp', ''),
            'estimated_delivery': tracking_data.get('estimated_delivery', ''),
            'events': tracking_data.get('events', []),
        }

    def _generate_tracking_number(self):
        """Generate unique tracking number"""
        import uuid
        return f"{self.code.upper()}{uuid.uuid4().hex[:8].upper()}"

    def _calculate_estimated_delivery(self):
        """Calculate estimated delivery date"""
        from datetime import datetime, timedelta
        base_date = datetime.now()
        
        if self.service_type == 'same_day':
            return base_date.date()
        elif self.service_type == 'next_day':
            return (base_date + timedelta(days=1)).date()
        elif self.service_type == 'express':
            return (base_date + timedelta(days=2)).date()
        else:
            return (base_date + timedelta(days=self.estimated_delivery_days or 5)).date()

    def get_shipping_cost(self, weight, dimensions=None, destination_country=None):
        """Calculate shipping cost"""
        cost = self.base_price
        
        if self.price_per_kg and weight:
            cost += weight * self.price_per_kg
        
        # Add insurance if available
        if self.insurance_available and self.insurance_rate > 0:
            cost += cost * (self.insurance_rate / 100)
        
        return cost

    def is_supported_for_country(self, country):
        """Check if carrier supports shipping to country"""
        if not self.supported_countries:
            return True  # If no countries specified, assume global
        
        if country in self.excluded_countries:
            return False
        
        return country in self.supported_countries

    @api.model
    def create(self, vals):
        """Override create to set default values"""
        if not vals.get('code'):
            vals['code'] = vals.get('name', '').upper().replace(' ', '_')
        
        return super().create(vals)

    def write(self, vals):
        """Override write to update related records"""
        result = super().write(vals)
        
        # Update delivery carrier if needed
        if 'shopify_tracking_company' in vals and self.delivery_carrier_id:
            self.delivery_carrier_id.write({
                'shopify_tracking_company': vals['shopify_tracking_company']
            })
        
        return result

    def unlink(self):
        """Override unlink to clean up related records"""
        for record in self:
            if record.delivery_carrier_id:
                record.delivery_carrier_id.unlink()
        return super().unlink()


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    shopify_carrier_id = fields.Many2one('shopify.carrier', string='Shopify Carrier')
    shopify_tracking_company = fields.Selection(related='shopify_carrier_id.shopify_tracking_company', 
                                               string='Shopify Tracking Company', store=True)
    
    # Advanced Shopify Integration
    shopify_service_code = fields.Char('Shopify Service Code')
    shopify_rate_id = fields.Char('Shopify Rate ID')
    shopify_zone_id = fields.Char('Shopify Zone ID')
    
    # Performance Tracking
    delivery_success_rate = fields.Float('Delivery Success Rate (%)', default=100.0)
    average_delivery_time = fields.Float('Average Delivery Time (Days)')
    customer_rating = fields.Float('Customer Rating (1-5)')
    
    # Analytics
    total_orders = fields.Integer('Total Orders', compute='_compute_analytics')
    total_revenue = fields.Monetary('Total Revenue', currency_field='currency_id', compute='_compute_analytics')
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                 default=lambda self: self.env.company.currency_id)

    @api.depends('name', 'shopify_carrier_id')
    def _compute_analytics(self):
        for record in self:
            # Get orders that use this carrier
            orders = self.env['sale.order'].search([
                ('carrier_id', '=', record.id),
                ('state', 'in', ['sale', 'done'])
            ])
            record.total_orders = len(orders)
            record.total_revenue = sum(orders.mapped('amount_total'))

    def shopify_search_create_delivery_carrier(self, line, instance):
        """Search and create delivery carrier based on Shopify order line"""
        carrier_code = line.get('carrier_identifier', '')
        if not carrier_code:
            return False
        
        # Search for existing carrier
        carrier = self.search([
            ('shopify_carrier_id.code', '=', carrier_code),
            ('company_id', '=', instance.company_id.id)
        ], limit=1)
        
        if not carrier:
            # Create new carrier
            shopify_carrier = self.env['shopify.carrier'].search([
                ('code', '=', carrier_code)
            ], limit=1)
            
            if shopify_carrier:
                carrier = self.create({
                    'name': shopify_carrier.name,
                    'shopify_carrier_id': shopify_carrier.id,
                    'company_id': instance.company_id.id,
                    'delivery_type': 'fixed',
                    'fixed_price': 0.0,
                })
        
        return carrier

    def shopify_get_tracking_url(self, picking):
        """Get tracking URL for picking"""
        if self.shopify_carrier_id and self.shopify_carrier_id.tracking_url_template:
            tracking_number = picking.carrier_tracking_ref
            if tracking_number:
                return self.shopify_carrier_id.tracking_url_template.replace(
                    '{tracking_number}', tracking_number
                )
        return False 