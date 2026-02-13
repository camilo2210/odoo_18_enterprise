# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class ShopifyWorkflow(models.Model):
    _name = 'shopify.workflow'
    _description = 'Shopify Order Workflow Configuration'
    _order = 'sequence, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Workflow Name', required=True, tracking=True)
    instance_id = fields.Many2one('shopify.instance', string='Shopify Instance', required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10, tracking=True)
    active = fields.Boolean('Active', default=True, tracking=True)
    
    # Workflow Configuration
    workflow_type = fields.Selection([
        ('order_processing', 'Order Processing'),
        ('inventory_management', 'Inventory Management'),
        ('shipping_fulfillment', 'Shipping & Fulfillment'),
        ('customer_service', 'Customer Service'),
        ('financial_processing', 'Financial Processing'),
        ('returns_processing', 'Returns Processing'),
    ], string='Workflow Type', required=True, tracking=True)
    
    # Status Mapping
    shopify_status = fields.Char('Shopify Status', required=True, tracking=True)
    odoo_status = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ('hold', 'On Hold'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('refunded', 'Refunded'),
    ], string='Odoo Status', required=True, tracking=True)
    
    # Workflow Steps
    step_ids = fields.One2many('shopify.workflow.step', 'workflow_id', string='Workflow Steps')
    
    # Automation Rules
    auto_process = fields.Boolean('Auto Process', default=True, tracking=True)
    auto_notify = fields.Boolean('Auto Notify', default=True, tracking=True)
    auto_invoice = fields.Boolean('Auto Create Invoice', default=False, tracking=True)
    auto_ship = fields.Boolean('Auto Create Shipment', default=False, tracking=True)
    
    # Conditions
    condition_ids = fields.One2many('shopify.workflow.condition', 'workflow_id', string='Conditions')
    
    # Actions
    action_ids = fields.One2many('shopify.workflow.action', 'workflow_id', string='Actions')
    
    # Timing
    processing_delay = fields.Integer('Processing Delay (minutes)', default=0, tracking=True)
    timeout_hours = fields.Integer('Timeout (hours)', default=24, tracking=True)
    
    # Notifications
    notify_users = fields.Many2many('res.users', string='Notify Users', tracking=True)
    notify_customer = fields.Boolean('Notify Customer', default=False, tracking=True)
    email_template_id = fields.Many2one('mail.template', string='Email Template', tracking=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('testing', 'Testing'),
    ], string='Status', default='draft', tracking=True)
    
    # Statistics
    total_executions = fields.Integer('Total Executions', default=0, tracking=True)
    success_count = fields.Integer('Success Count', default=0, tracking=True)
    failure_count = fields.Integer('Failure Count', default=0, tracking=True)
    average_execution_time = fields.Float('Average Execution Time (seconds)', default=0.0, tracking=True)
    
    note = fields.Text('Notes')
    
    _sql_constraints = [
        ('unique_workflow_status', 'unique(instance_id, shopify_status, workflow_type)', 
         'A workflow with this status already exists for this instance and type!'),
    ]

    @api.constrains('shopify_status', 'odoo_status')
    def _check_status_mapping(self):
        for record in self:
            if record.shopify_status == record.odoo_status:
                raise ValidationError(_('Shopify status and Odoo status cannot be the same'))

    def action_activate(self):
        """Activate workflow"""
        for record in self:
            record.state = 'active'
            record.message_post(body=_('Workflow activated successfully'))

    def action_deactivate(self):
        """Deactivate workflow"""
        for record in self:
            record.state = 'inactive'
            record.message_post(body=_('Workflow deactivated successfully'))

    def action_test_workflow(self):
        """Test workflow with sample data"""
        for record in self:
            try:
                result = record._test_workflow_execution()
                record.message_post(body=_('Workflow test successful: %s') % result)
            except Exception as e:
                record.message_post(body=_('Workflow test failed: %s') % str(e))
                raise UserError(_('Workflow test failed: %s') % str(e))

    def action_execute_workflow(self, order):
        """Execute workflow for a specific order"""
        for record in self:
            if record.state != 'active':
                continue
                
            try:
                start_time = fields.Datetime.now()
                
                # Check conditions
                if not record._check_conditions(order):
                    _logger.info('Workflow conditions not met for order %s', order.name)
                    continue
                
                # Execute steps
                for step in record.step_ids.sorted('sequence'):
                    step._execute_step(order)
                
                # Execute actions
                for action in record.action_ids.sorted('sequence'):
                    action._execute_action(order)
                
                # Update statistics
                execution_time = (fields.Datetime.now() - start_time).total_seconds()
                record._update_statistics(True, execution_time)
                
                # Send notifications
                if record.auto_notify:
                    record._send_notifications(order)
                
                record.message_post(body=_('Workflow executed successfully for order %s') % order.name)
                
            except Exception as e:
                record._update_statistics(False, 0)
                record.message_post(body=_('Workflow execution failed for order %s: %s') % (order.name, str(e)))
                raise UserError(_('Workflow execution failed: %s') % str(e))

    def _check_conditions(self, order):
        """Check if all conditions are met"""
        for condition in self.condition_ids:
            if not condition._evaluate_condition(order):
                return False
        return True

    def _test_workflow_execution(self):
        """Test workflow execution with sample data"""
        # Create sample order for testing
        sample_order = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_1').id,
            'date_order': fields.Datetime.now(),
        })
        
        try:
            self.action_execute_workflow(sample_order)
            return 'Test completed successfully'
        finally:
            # Clean up test data
            sample_order.unlink()

    def _update_statistics(self, success, execution_time):
        """Update workflow statistics"""
        self.total_executions += 1
        
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        
        # Update average execution time
        if self.total_executions > 1:
            self.average_execution_time = (
                (self.average_execution_time * (self.total_executions - 1) + execution_time) / 
                self.total_executions
            )
        else:
            self.average_execution_time = execution_time

    def _send_notifications(self, order):
        """Send notifications based on workflow configuration"""
        # Send user notifications
        if self.notify_users:
            for user in self.notify_users:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    note=_('Workflow "%s" executed for order %s') % (self.name, order.name),
                    user_id=user.id
                )
        
        # Send customer notification
        if self.notify_customer and self.email_template_id:
            self.email_template_id.send_mail(order.id, force_send=True)

    @api.model
    def process_order_status_change(self, order, new_status):
        """Process order status change through workflows"""
        workflows = self.search([
            ('instance_id', '=', order.shopify_instance_id.id),
            ('shopify_status', '=', new_status),
            ('workflow_type', '=', 'order_processing'),
            ('state', '=', 'active')
        ])
        
        for workflow in workflows:
            workflow.action_execute_workflow(order)


class ShopifyWorkflowStep(models.Model):
    _name = 'shopify.workflow.step'
    _description = 'Shopify Workflow Step'
    _order = 'sequence, id'

    name = fields.Char('Step Name', required=True)
    workflow_id = fields.Many2one('shopify.workflow', string='Workflow', required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)
    
    step_type = fields.Selection([
        ('status_update', 'Status Update'),
        ('field_update', 'Field Update'),
        ('validation', 'Validation'),
        ('notification', 'Notification'),
        ('integration', 'Integration'),
        ('custom', 'Custom Action'),
    ], string='Step Type', required=True)
    
    # Step Configuration
    action = fields.Selection([
        ('update_status', 'Update Order Status'),
        ('update_field', 'Update Field'),
        ('send_email', 'Send Email'),
        ('create_invoice', 'Create Invoice'),
        ('create_shipment', 'Create Shipment'),
        ('validate_stock', 'Validate Stock'),
        ('check_payment', 'Check Payment'),
        ('custom_python', 'Custom Python Code'),
    ], string='Action', required=True)
    
    # Action Parameters
    field_name = fields.Char('Field Name')
    field_value = fields.Char('Field Value')
    status_value = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ('hold', 'On Hold'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('refunded', 'Refunded'),
    ], string='Status Value')
    
    # Custom Code
    python_code = fields.Text('Python Code', help='Custom Python code to execute')
    
    # Conditions
    condition_field = fields.Char('Condition Field')
    condition_operator = fields.Selection([
        ('=', 'Equal'),
        ('!=', 'Not Equal'),
        ('>', 'Greater Than'),
        ('<', 'Less Than'),
        ('>=', 'Greater or Equal'),
        ('<=', 'Less or Equal'),
        ('in', 'In'),
        ('not in', 'Not In'),
    ], string='Condition Operator')
    condition_value = fields.Char('Condition Value')
    
    # Status
    active = fields.Boolean('Active', default=True)
    error_handling = fields.Selection([
        ('stop', 'Stop on Error'),
        ('continue', 'Continue on Error'),
        ('retry', 'Retry on Error'),
    ], string='Error Handling', default='stop')
    
    # Statistics
    execution_count = fields.Integer('Execution Count', default=0)
    success_count = fields.Integer('Success Count', default=0)
    error_count = fields.Integer('Error Count', default=0)
    
    note = fields.Text('Notes')

    def _execute_step(self, order):
        """Execute workflow step"""
        self.execution_count += 1
        
        try:
            # Check condition
            if not self._check_condition(order):
                _logger.info('Step condition not met for order %s', order.name)
                return
            
            # Execute action
            if self.action == 'update_status':
                self._update_order_status(order)
            elif self.action == 'update_field':
                self._update_field(order)
            elif self.action == 'send_email':
                self._send_email(order)
            elif self.action == 'create_invoice':
                self._create_invoice(order)
            elif self.action == 'create_shipment':
                self._create_shipment(order)
            elif self.action == 'validate_stock':
                self._validate_stock(order)
            elif self.action == 'check_payment':
                self._check_payment(order)
            elif self.action == 'custom_python':
                self._execute_custom_code(order)
            
            self.success_count += 1
            
        except Exception as e:
            self.error_count += 1
            _logger.error('Step execution failed: %s', str(e))
            
            if self.error_handling == 'stop':
                raise e
            elif self.error_handling == 'retry':
                # Implement retry logic
                pass

    def _check_condition(self, order):
        """Check if step condition is met"""
        if not self.condition_field:
            return True
        
        try:
            field_value = getattr(order, self.condition_field, None)
            
            if self.condition_operator == '=':
                return field_value == self.condition_value
            elif self.condition_operator == '!=':
                return field_value != self.condition_value
            elif self.condition_operator == '>':
                return field_value > float(self.condition_value)
            elif self.condition_operator == '<':
                return field_value < float(self.condition_value)
            elif self.condition_operator == '>=':
                return field_value >= float(self.condition_value)
            elif self.condition_operator == '<=':
                return field_value <= float(self.condition_value)
            elif self.condition_operator == 'in':
                return field_value in self.condition_value.split(',')
            elif self.condition_operator == 'not in':
                return field_value not in self.condition_value.split(',')
            
            return True
            
        except Exception as e:
            _logger.error('Error checking condition: %s', str(e))
            return False

    def _update_order_status(self, order):
        """Update order status"""
        if self.status_value:
            order.write({'state': self.status_value})

    def _update_field(self, order):
        """Update order field"""
        if self.field_name and self.field_value:
            order.write({self.field_name: self.field_value})

    def _send_email(self, order):
        """Send email notification"""
        template = self.workflow_id.email_template_id
        if template:
            template.send_mail(order.id, force_send=True)

    def _create_invoice(self, order):
        """Create invoice for order"""
        if order.state in ['sale', 'done']:
            order._create_invoices()

    def _create_shipment(self, order):
        """Create shipment for order"""
        if order.state in ['sale', 'done']:
            order._create_delivery()

    def _validate_stock(self, order):
        """Validate stock availability"""
        for line in order.order_line:
            if line.product_id.qty_available < line.product_uom_qty:
                raise UserError(_('Insufficient stock for product %s') % line.product_id.name)

    def _check_payment(self, order):
        """Check payment status"""
        if order.amount_total > 0 and not order.invoice_ids.filtered(lambda inv: inv.state == 'paid'):
            raise UserError(_('Payment not received for order %s') % order.name)

    def _execute_custom_code(self, order):
        """Execute custom Python code"""
        if self.python_code:
            # Create safe execution environment
            local_vars = {
                'order': order,
                'self': self,
                'env': self.env,
                'fields': fields,
                'UserError': UserError,
            }
            
            exec(self.python_code, {}, local_vars)


class ShopifyWorkflowCondition(models.Model):
    _name = 'shopify.workflow.condition'
    _description = 'Shopify Workflow Condition'
    _order = 'sequence, id'

    name = fields.Char('Condition Name', required=True)
    workflow_id = fields.Many2one('shopify.workflow', string='Workflow', required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)
    
    condition_type = fields.Selection([
        ('field', 'Field Condition'),
        ('expression', 'Python Expression'),
        ('custom', 'Custom Function'),
    ], string='Condition Type', required=True)
    
    # Field Condition
    field_name = fields.Char('Field Name')
    operator = fields.Selection([
        ('=', 'Equal'),
        ('!=', 'Not Equal'),
        ('>', 'Greater Than'),
        ('<', 'Less Than'),
        ('>=', 'Greater or Equal'),
        ('<=', 'Less or Equal'),
        ('in', 'In'),
        ('not in', 'Not In'),
        ('contains', 'Contains'),
        ('not contains', 'Not Contains'),
    ], string='Operator')
    value = fields.Char('Value')
    
    # Expression Condition
    python_expression = fields.Text('Python Expression')
    
    # Custom Function
    function_name = fields.Char('Function Name')
    
    # Logic
    logical_operator = fields.Selection([
        ('and', 'AND'),
        ('or', 'OR'),
    ], string='Logical Operator', default='and')
    
    active = fields.Boolean('Active', default=True)
    note = fields.Text('Notes')

    def _evaluate_condition(self, order):
        """Evaluate condition for order"""
        if not self.active:
            return True
        
        try:
            if self.condition_type == 'field':
                return self._evaluate_field_condition(order)
            elif self.condition_type == 'expression':
                return self._evaluate_expression(order)
            elif self.condition_type == 'custom':
                return self._evaluate_custom_function(order)
            
            return True
            
        except Exception as e:
            _logger.error('Error evaluating condition %s: %s', self.name, str(e))
            return False

    def _evaluate_field_condition(self, order):
        """Evaluate field-based condition"""
        if not self.field_name:
            return True
        
        field_value = getattr(order, self.field_name, None)
        
        if self.operator == '=':
            return field_value == self.value
        elif self.operator == '!=':
            return field_value != self.value
        elif self.operator == '>':
            return field_value > float(self.value)
        elif self.operator == '<':
            return field_value < float(self.value)
        elif self.operator == '>=':
            return field_value >= float(self.value)
        elif self.operator == '<=':
            return field_value <= float(self.value)
        elif self.operator == 'in':
            return field_value in self.value.split(',')
        elif self.operator == 'not in':
            return field_value not in self.value.split(',')
        elif self.operator == 'contains':
            return self.value in str(field_value)
        elif self.operator == 'not contains':
            return self.value not in str(field_value)
        
        return True

    def _evaluate_expression(self, order):
        """Evaluate Python expression"""
        if not self.python_expression:
            return True
        
        local_vars = {
            'order': order,
            'self': self,
            'env': self.env,
            'fields': fields,
        }
        
        return eval(self.python_expression, {}, local_vars)

    def _evaluate_custom_function(self, order):
        """Evaluate custom function"""
        if not self.function_name:
            return True
        
        # This would call a custom function defined elsewhere
        return True


class ShopifyWorkflowAction(models.Model):
    _name = 'shopify.workflow.action'
    _description = 'Shopify Workflow Action'
    _order = 'sequence, id'

    name = fields.Char('Action Name', required=True)
    workflow_id = fields.Many2one('shopify.workflow', string='Workflow', required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)
    
    action_type = fields.Selection([
        ('system', 'System Action'),
        ('integration', 'Integration Action'),
        ('notification', 'Notification Action'),
        ('custom', 'Custom Action'),
    ], string='Action Type', required=True)
    
    # System Actions
    system_action = fields.Selection([
        ('create_invoice', 'Create Invoice'),
        ('create_shipment', 'Create Shipment'),
        ('update_status', 'Update Status'),
        ('send_email', 'Send Email'),
        ('create_activity', 'Create Activity'),
        ('log_event', 'Log Event'),
    ], string='System Action')
    
    # Integration Actions
    integration_action = fields.Selection([
        ('shopify_update', 'Update Shopify'),
        ('erp_update', 'Update ERP'),
        ('api_call', 'API Call'),
        ('webhook_trigger', 'Trigger Webhook'),
    ], string='Integration Action')
    
    # Action Parameters
    parameters = fields.Json('Parameters', default=dict)
    
    # Custom Code
    custom_code = fields.Text('Custom Code')
    
    # Timing
    delay_minutes = fields.Integer('Delay (minutes)', default=0)
    retry_count = fields.Integer('Retry Count', default=0)
    retry_delay = fields.Integer('Retry Delay (minutes)', default=5)
    
    # Status
    active = fields.Boolean('Active', default=True)
    error_handling = fields.Selection([
        ('stop', 'Stop on Error'),
        ('continue', 'Continue on Error'),
        ('retry', 'Retry on Error'),
    ], string='Error Handling', default='stop')
    
    # Statistics
    execution_count = fields.Integer('Execution Count', default=0)
    success_count = fields.Integer('Success Count', default=0)
    error_count = fields.Integer('Error Count', default=0)
    
    note = fields.Text('Notes')

    def _execute_action(self, order):
        """Execute workflow action"""
        self.execution_count += 1
        
        try:
            if self.action_type == 'system':
                self._execute_system_action(order)
            elif self.action_type == 'integration':
                self._execute_integration_action(order)
            elif self.action_type == 'notification':
                self._execute_notification_action(order)
            elif self.action_type == 'custom':
                self._execute_custom_action(order)
            
            self.success_count += 1
            
        except Exception as e:
            self.error_count += 1
            _logger.error('Action execution failed: %s', str(e))
            
            if self.error_handling == 'stop':
                raise e
            elif self.error_handling == 'retry' and self.retry_count > 0:
                # Implement retry logic
                pass

    def _execute_system_action(self, order):
        """Execute system action"""
        if self.system_action == 'create_invoice':
            order._create_invoices()
        elif self.system_action == 'create_shipment':
            order._create_delivery()
        elif self.system_action == 'update_status':
            status = self.parameters.get('status')
            if status:
                order.write({'state': status})
        elif self.system_action == 'send_email':
            template_id = self.parameters.get('template_id')
            if template_id:
                template = self.env['mail.template'].browse(template_id)
                template.send_mail(order.id, force_send=True)
        elif self.system_action == 'create_activity':
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                note=self.parameters.get('note', 'Workflow action executed'),
                user_id=self.parameters.get('user_id', self.env.user.id)
            )
        elif self.system_action == 'log_event':
            self.env['shopify.log'].create({
                'job_id': order.id,
                'log_type': 'info',
                'message': self.parameters.get('message', 'Workflow action executed'),
            })

    def _execute_integration_action(self, order):
        """Execute integration action"""
        if self.integration_action == 'shopify_update':
            # Update Shopify via API
            pass
        elif self.integration_action == 'erp_update':
            # Update ERP system
            pass
        elif self.integration_action == 'api_call':
            # Make API call
            pass
        elif self.integration_action == 'webhook_trigger':
            # Trigger webhook
            pass

    def _execute_notification_action(self, order):
        """Execute notification action"""
        # Send notifications based on parameters
        pass

    def _execute_custom_action(self, order):
        """Execute custom action"""
        if self.custom_code:
            local_vars = {
                'order': order,
                'self': self,
                'env': self.env,
                'fields': fields,
                'UserError': UserError,
            }
            
            exec(self.custom_code, {}, local_vars) 