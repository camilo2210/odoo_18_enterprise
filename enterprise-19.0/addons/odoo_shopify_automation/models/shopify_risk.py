# -*- coding: utf-8 -*-
import logging
import json
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

class ShopifyRisk(models.Model):
    _name = 'shopify.risk'
    _description = 'Shopify Risk Management'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Risk Assessment', required=True, tracking=True)
    instance_id = fields.Many2one('shopify.instance', string='Shopify Instance', required=True, ondelete='cascade')
    
    # Risk Assessment
    risk_type = fields.Selection([
        ('fraud', 'Fraud Risk'),
        ('payment', 'Payment Risk'),
        ('shipping', 'Shipping Risk'),
        ('inventory', 'Inventory Risk'),
        ('customer', 'Customer Risk'),
        ('financial', 'Financial Risk'),
        ('operational', 'Operational Risk'),
    ], string='Risk Type', required=True, tracking=True)
    
    risk_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Risk Level', default='low', tracking=True)
    
    risk_score = fields.Float('Risk Score (0-100)', default=0.0, tracking=True)
    confidence_score = fields.Float('Confidence Score (0-100)', default=0.0, tracking=True)
    
    # Related Records
    order_id = fields.Many2one('shopify.order', string='Related Order', tracking=True)
    customer_id = fields.Many2one('shopify.customer', string='Related Customer', tracking=True)
    product_id = fields.Many2one('shopify.product', string='Related Product', tracking=True)
    
    # Risk Factors
    risk_factors = fields.Text('Risk Factors', tracking=True)
    risk_indicators = fields.Json('Risk Indicators', default=dict, tracking=True)
    
    # AI Analysis
    ai_analysis = fields.Text('AI Analysis', tracking=True)
    ai_recommendations = fields.Text('AI Recommendations', tracking=True)
    ai_confidence = fields.Float('AI Confidence', default=0.0, tracking=True)
    
    # Manual Assessment
    manual_assessment = fields.Text('Manual Assessment', tracking=True)
    manual_risk_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Manual Risk Level', tracking=True)
    
    # Actions
    action_taken = fields.Selection([
        ('none', 'No Action'),
        ('review', 'Under Review'),
        ('hold', 'Order on Hold'),
        ('cancel', 'Cancel Order'),
        ('approve', 'Approve Order'),
        ('flag', 'Flag for Manual Review'),
        ('block', 'Block Customer'),
        ('investigate', 'Investigate Further'),
    ], string='Action Taken', default='none', tracking=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('analyzing', 'Analyzing'),
        ('assessed', 'Assessed'),
        ('actioned', 'Actioned'),
        ('resolved', 'Resolved'),
        ('false_positive', 'False Positive'),
    ], string='Status', default='draft', tracking=True)
    
    # Timestamps
    detected_at = fields.Datetime('Detected At', default=fields.Datetime.now, tracking=True)
    assessed_at = fields.Datetime('Assessed At', tracking=True)
    resolved_at = fields.Datetime('Resolved At', tracking=True)
    
    # User tracking
    detected_by = fields.Many2one('res.users', string='Detected By', default=lambda self: self.env.user, tracking=True)
    assessed_by = fields.Many2one('res.users', string='Assessed By', tracking=True)
    resolved_by = fields.Many2one('res.users', string='Resolved By', tracking=True)
    
    # Configuration
    auto_assess = fields.Boolean('Auto Assess', default=True, tracking=True)
    auto_action = fields.Boolean('Auto Action', default=False, tracking=True)
    notify_users = fields.Boolean('Notify Users', default=True, tracking=True)
    
    note = fields.Text('Notes')

    @api.model
    def create(self, vals):
        """Override create to auto-assess risk if enabled"""
        risk = super().create(vals)
        if risk.auto_assess:
            risk.action_assess_risk()
        return risk

    def action_assess_risk(self):
        """Assess risk using AI and rule-based analysis"""
        for record in self:
            record.state = 'analyzing'
            
            try:
                # Perform AI analysis
                ai_result = record._perform_ai_analysis()
                
                # Perform rule-based analysis
                rule_result = record._perform_rule_analysis()
                
                # Combine results
                combined_result = record._combine_analysis_results(ai_result, rule_result)
                
                # Update record
                record.write({
                    'risk_score': combined_result['risk_score'],
                    'risk_level': combined_result['risk_level'],
                    'confidence_score': combined_result['confidence_score'],
                    'ai_analysis': combined_result['ai_analysis'],
                    'ai_recommendations': combined_result['ai_recommendations'],
                    'ai_confidence': combined_result['ai_confidence'],
                    'risk_factors': combined_result['risk_factors'],
                    'risk_indicators': combined_result['risk_indicators'],
                    'state': 'assessed',
                    'assessed_at': fields.Datetime.now(),
                    'assessed_by': self.env.user.id,
                })
                
                # Take auto action if enabled
                if record.auto_action:
                    record._take_auto_action()
                
                # Send notifications
                if record.notify_users:
                    record._send_risk_notifications()
                
                record.message_post(body=_('Risk assessment completed. Risk Level: %s, Score: %.2f') % 
                                  (record.risk_level, record.risk_score))
                
            except Exception as e:
                record.state = 'draft'
                record.message_post(body=_('Risk assessment failed: %s') % str(e))
                raise UserError(_('Risk assessment failed: %s') % str(e))

    def action_manual_assessment(self):
        """Perform manual risk assessment"""
        for record in self:
            if not record.manual_risk_level:
                raise UserError(_('Please set manual risk level before proceeding'))
            
            record.write({
                'state': 'assessed',
                'assessed_at': fields.Datetime.now(),
                'assessed_by': self.env.user.id,
            })
            
            record.message_post(body=_('Manual assessment completed. Risk Level: %s') % record.manual_risk_level)

    def action_take_action(self):
        """Take action based on risk assessment"""
        for record in self:
            if record.action_taken == 'none':
                raise UserError(_('Please select an action to take'))
            
            record._execute_action()
            record.write({
                'state': 'actioned',
                'resolved_at': fields.Datetime.now(),
                'resolved_by': self.env.user.id,
            })
            
            record.message_post(body=_('Action taken: %s') % record.action_taken)

    def action_resolve(self):
        """Mark risk as resolved"""
        for record in self:
            record.write({
                'state': 'resolved',
                'resolved_at': fields.Datetime.now(),
                'resolved_by': self.env.user.id,
            })
            
            record.message_post(body=_('Risk marked as resolved'))

    def action_false_positive(self):
        """Mark as false positive"""
        for record in self:
            record.write({
                'state': 'false_positive',
                'resolved_at': fields.Datetime.now(),
                'resolved_by': self.env.user.id,
            })
            
            record.message_post(body=_('Risk marked as false positive'))

    def _perform_ai_analysis(self):
        """Perform AI-powered risk analysis"""
        # This would integrate with AI/ML services
        # For now, using rule-based scoring
        
        risk_factors = []
        risk_score = 0.0
        confidence_score = 0.0
        
        if self.order_id:
            # Analyze order patterns
            order_analysis = self._analyze_order_patterns()
            risk_factors.extend(order_analysis['factors'])
            risk_score += order_analysis['score']
            confidence_score += order_analysis['confidence']
        
        if self.customer_id:
            # Analyze customer behavior
            customer_analysis = self._analyze_customer_behavior()
            risk_factors.extend(customer_analysis['factors'])
            risk_score += customer_analysis['score']
            confidence_score += customer_analysis['confidence']
        
        if self.product_id:
            # Analyze product risk
            product_analysis = self._analyze_product_risk()
            risk_factors.extend(product_analysis['factors'])
            risk_score += product_analysis['score']
            confidence_score += product_analysis['confidence']
        
        # Normalize scores
        risk_score = min(risk_score, 100.0)
        confidence_score = min(confidence_score / 3, 100.0)  # Average confidence
        
        return {
            'risk_score': risk_score,
            'confidence_score': confidence_score,
            'analysis': 'AI analysis completed based on multiple risk factors',
            'recommendations': self._generate_ai_recommendations(risk_score),
            'factors': risk_factors,
        }

    def _perform_rule_analysis(self):
        """Perform rule-based risk analysis"""
        rules = self._get_risk_rules()
        triggered_rules = []
        rule_score = 0.0
        
        for rule in rules:
            if self._evaluate_rule(rule):
                triggered_rules.append(rule)
                rule_score += rule.get('score', 0)
        
        return {
            'triggered_rules': triggered_rules,
            'rule_score': rule_score,
            'analysis': f'Rule-based analysis triggered {len(triggered_rules)} rules',
        }

    def _combine_analysis_results(self, ai_result, rule_result):
        """Combine AI and rule-based analysis results"""
        # Weighted combination (70% AI, 30% rules)
        combined_score = (ai_result['risk_score'] * 0.7) + (rule_result['rule_score'] * 0.3)
        
        # Determine risk level
        if combined_score >= 80:
            risk_level = 'critical'
        elif combined_score >= 60:
            risk_level = 'high'
        elif combined_score >= 30:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        # Combine risk factors
        all_factors = ai_result.get('factors', []) + rule_result.get('triggered_rules', [])
        
        return {
            'risk_score': combined_score,
            'risk_level': risk_level,
            'confidence_score': ai_result['confidence_score'],
            'ai_analysis': ai_result['analysis'],
            'ai_recommendations': ai_result['recommendations'],
            'ai_confidence': ai_result['confidence_score'],
            'risk_factors': '\n'.join(all_factors),
            'risk_indicators': {
                'ai_score': ai_result['risk_score'],
                'rule_score': rule_result['rule_score'],
                'combined_score': combined_score,
                'triggered_rules': len(rule_result['triggered_rules']),
            }
        }

    def _analyze_order_patterns(self):
        """Analyze order patterns for risk indicators"""
        order = self.order_id
        factors = []
        score = 0.0
        confidence = 0.0
        
        if order:
            # Check order amount
            if order.total_price > 1000:
                factors.append('High order value')
                score += 20
                confidence += 30
            
            # Check order frequency
            recent_orders = self.env['shopify.order'].search([
                ('customer_id', '=', order.customer_id.id),
                ('create_date', '>=', fields.Datetime.now() - timedelta(hours=24))
            ])
            
            if len(recent_orders) > 5:
                factors.append('High order frequency')
                score += 25
                confidence += 25
            
            # Check shipping address mismatch
            if order.shipping_address_id != order.billing_address_id:
                factors.append('Shipping/billing address mismatch')
                score += 15
                confidence += 20
            
            # Check payment method
            if order.payment_method == 'credit_card':
                factors.append('Credit card payment')
                score += 10
                confidence += 15
        
        return {
            'factors': factors,
            'score': score,
            'confidence': confidence,
        }

    def _analyze_customer_behavior(self):
        """Analyze customer behavior for risk indicators"""
        customer = self.customer_id
        factors = []
        score = 0.0
        confidence = 0.0
        
        if customer:
            # Check customer age
            if customer.create_date:
                customer_age = (fields.Datetime.now() - customer.create_date).days
                if customer_age < 1:
                    factors.append('New customer')
                    score += 15
                    confidence += 20
            
            # Check order history
            total_orders = len(customer.order_ids)
            if total_orders == 0:
                factors.append('First-time customer')
                score += 20
                confidence += 25
            elif total_orders > 20:
                factors.append('High-volume customer')
                score -= 10  # Reduce risk for loyal customers
                confidence += 30
            
            # Check return history
            returned_orders = customer.order_ids.filtered(lambda o: o.state == 'cancel')
            if len(returned_orders) > 3:
                factors.append('High return rate')
                score += 30
                confidence += 25
        
        return {
            'factors': factors,
            'score': score,
            'confidence': confidence,
        }

    def _analyze_product_risk(self):
        """Analyze product-specific risk factors"""
        product = self.product_id
        factors = []
        score = 0.0
        confidence = 0.0
        
        if product:
            # Check product category
            if product.category_id.name in ['Electronics', 'Jewelry', 'Gift Cards']:
                factors.append('High-risk product category')
                score += 20
                confidence += 25
            
            # Check product value
            if product.list_price > 500:
                factors.append('High-value product')
                score += 15
                confidence += 20
            
            # Check stock availability
            if product.qty_available == 0:
                factors.append('Out of stock product')
                score += 10
                confidence += 15
        
        return {
            'factors': factors,
            'score': score,
            'confidence': confidence,
        }

    def _get_risk_rules(self):
        """Get risk assessment rules"""
        return [
            {
                'name': 'High Value Order',
                'condition': 'order.total_price > 1000',
                'score': 20,
                'description': 'Orders over $1000'
            },
            {
                'name': 'New Customer',
                'condition': 'customer.create_date > (now - 24h)',
                'score': 15,
                'description': 'Customers created in last 24 hours'
            },
            {
                'name': 'Address Mismatch',
                'condition': 'order.shipping_address != order.billing_address',
                'score': 15,
                'description': 'Shipping and billing addresses differ'
            },
            {
                'name': 'High Frequency',
                'condition': 'customer.order_count_24h > 5',
                'score': 25,
                'description': 'More than 5 orders in 24 hours'
            },
            {
                'name': 'International Order',
                'condition': 'order.shipping_country != company.country',
                'score': 10,
                'description': 'International shipping'
            },
        ]

    def _evaluate_rule(self, rule):
        """Evaluate if a rule is triggered"""
        try:
            condition = rule['condition']
            
            if 'order.total_price > 1000' in condition and self.order_id:
                return self.order_id.total_price > 1000
            
            elif 'customer.create_date > (now - 24h)' in condition and self.customer_id:
                return self.customer_id.create_date > (fields.Datetime.now() - timedelta(hours=24))
            
            elif 'order.shipping_address != order.billing_address' in condition and self.order_id:
                return self.order_id.shipping_address_id != self.order_id.billing_address_id
            
            elif 'customer.order_count_24h > 5' in condition and self.customer_id:
                recent_orders = self.env['shopify.order'].search([
                    ('customer_id', '=', self.customer_id.id),
                    ('create_date', '>=', fields.Datetime.now() - timedelta(hours=24))
                ])
                return len(recent_orders) > 5
            
            elif 'order.shipping_country != company.country' in condition and self.order_id:
                company_country = self.env.company.country_id
                return self.order_id.shipping_address_id.country_id != company_country
            
            return False
            
        except Exception as e:
            _logger.error('Error evaluating rule %s: %s', rule['name'], str(e))
            return False

    def _generate_ai_recommendations(self, risk_score):
        """Generate AI recommendations based on risk score"""
        if risk_score >= 80:
            return "Critical risk detected. Recommend immediate order hold and manual review."
        elif risk_score >= 60:
            return "High risk detected. Recommend order review and additional verification."
        elif risk_score >= 30:
            return "Medium risk detected. Recommend enhanced monitoring."
        else:
            return "Low risk detected. Standard processing recommended."

    def _take_auto_action(self):
        """Take automatic action based on risk level"""
        if self.risk_level == 'critical':
            self.action_taken = 'hold'
            if self.order_id:
                self.order_id.write({'state': 'hold'})
        elif self.risk_level == 'high':
            self.action_taken = 'flag'
        elif self.risk_level == 'medium':
            self.action_taken = 'review'
        else:
            self.action_taken = 'approve'

    def _execute_action(self):
        """Execute the selected action"""
        if self.action_taken == 'hold' and self.order_id:
            self.order_id.write({'state': 'hold'})
        elif self.action_taken == 'cancel' and self.order_id:
            self.order_id.write({'state': 'cancel'})
        elif self.action_taken == 'approve' and self.order_id:
            self.order_id.write({'state': 'confirmed'})
        elif self.action_taken == 'block' and self.customer_id:
            self.customer_id.write({'active': False})

    def _send_risk_notifications(self):
        """Send notifications about risk detection"""
        if self.risk_level in ['high', 'critical']:
            # Send email notification
            self._send_email_notification()
            
            # Create activity
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                note=_('Risk assessment required for %s (Risk Level: %s)') % (self.name, self.risk_level),
                user_id=self.env.ref('base.group_user').users[0].id if self.env.ref('base.group_user').users else False
            )

    def _send_email_notification(self):
        """Send email notification about risk"""
        template = self.env.ref('odoo_shopify_automation.email_template_risk_alert', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    @api.model
    def auto_detect_risks(self):
        """Automatically detect risks for new orders"""
        # Find orders without risk assessment
        orders = self.env['shopify.order'].search([
            ('risk_ids', '=', False),
            ('state', 'in', ['draft', 'confirmed'])
        ])
        
        for order in orders:
            # Create risk assessment
            self.create({
                'name': f'Risk Assessment for Order {order.order_number}',
                'instance_id': order.instance_id.id,
                'order_id': order.id,
                'customer_id': order.customer_id.id,
                'risk_type': 'fraud',
                'auto_assess': True,
            })

    def get_risk_summary(self):
        """Get risk summary for reporting"""
        return {
            'total_risks': len(self),
            'critical_risks': len(self.filtered(lambda r: r.risk_level == 'critical')),
            'high_risks': len(self.filtered(lambda r: r.risk_level == 'high')),
            'medium_risks': len(self.filtered(lambda r: r.risk_level == 'medium')),
            'low_risks': len(self.filtered(lambda r: r.risk_level == 'low')),
            'resolved_risks': len(self.filtered(lambda r: r.state == 'resolved')),
            'false_positives': len(self.filtered(lambda r: r.state == 'false_positive')),
        }

    @api.model
    def create(self, vals):
        """Override create to set default values"""
        if not vals.get('name'):
            vals['name'] = f'Risk Assessment {fields.Datetime.now().strftime("%Y-%m-%d %H:%M")}'
        
        return super().create(vals) 