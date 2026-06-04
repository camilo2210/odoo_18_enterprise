# -*- coding: utf-8 -*-
import logging
import re
import unicodedata

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FIELD_TYPE_SELECTION = [
    ('char', 'Text (Short)'),
    ('text', 'Text (Long)'),
    ('html', 'Rich Text (HTML)'),
    ('integer', 'Integer'),
    ('float', 'Decimal'),
    ('monetary', 'Monetary'),
    ('boolean', 'Checkbox (Yes/No)'),
    ('date', 'Date'),
    ('datetime', 'Date & Time'),
    ('binary', 'File / Attachment'),
    ('selection', 'Dropdown (Selection)'),
    ('many2one', 'Link to another model (Many2one)'),
]

TECHNICAL_NAME_PREFIX = 'x_pgm_'


class ExtendedFieldCreator(models.Model):
    """UI-driven dynamic field creator for functional consultants.

    Creates ``ir.model.fields`` records at runtime and auto-injects
    the new field into the target model's primary form view.
    """

    _name = 'extended.field.creator'
    _description = 'Extended Field Creator'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    # ------------------------------------------------------------------
    # Field Definitions
    # ------------------------------------------------------------------
    active = fields.Boolean(
        default=True,
        help="Uncheck to archive this record without deleting it.",
    )

    name = fields.Char(
        string="Field Label",
        required=True,
        tracking=True,
        help="Human-readable label displayed in the UI (e.g. 'Customer Score').",
    )

    technical_name = fields.Char(
        string="Technical Name",
        compute='_compute_technical_name',
        store=True,
        readonly=True,
        tracking=True,
        help="Auto-generated Odoo-compatible technical name (x_pgm_…).",
    )

    field_type = fields.Selection(
        selection=FIELD_TYPE_SELECTION,
        string="Field Type",
        required=True,
        tracking=True,
        help="Select the data type for the new field.",
    )

    model_id = fields.Many2one(
        comodel_name='ir.model',
        string="Target Model",
        required=True,
        ondelete='cascade',
        tracking=True,
        index=True,
        domain="[('transient', '=', False)]",
        help="The Odoo model where the field will be created.",
    )

    model_name = fields.Char(
        string="Model Technical Name",
        related='model_id.model',
        store=True,
        readonly=True,
    )

    help_text = fields.Text(
        string="Help Message",
        help="Tooltip shown when the user hovers over the field in a form.",
    )

    notes = fields.Text(
        string="Internal Notes",
        help="Private notes about this field (not visible to end users).",
    )

    # --- Selection-specific ---
    selection_options = fields.Text(
        string="Selection Options",
        help=(
            "Define key:Label pairs, one per line.\n"
            "Example:\n"
            "  draft:Draft\n"
            "  confirmed:Confirmed\n"
            "  done:Done"
        ),
    )

    # --- Many2one-specific ---
    relation_model_id = fields.Many2one(
        comodel_name='ir.model',
        string="Related Model",
        ondelete='set null',
        domain="[('transient', '=', False)]",
        help="For Many2one fields: the model this field will point to.",
    )

    # --- Optional attributes ---
    required_field = fields.Boolean(
        string="Required",
        default=False,
        help="If checked, users must fill in this field before saving.",
    )

    copied_field = fields.Boolean(
        string="Copy on Duplicate",
        default=True,
        help="If checked, the field value is copied when the record is duplicated.",
    )

    # --- Workflow ---
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('done', 'Created'),
            ('removed', 'Removed'),
        ],
        string="Status",
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )

    # --- References to created artefacts ---
    created_field_id = fields.Many2one(
        comodel_name='ir.model.fields',
        string="Created Field",
        readonly=True,
        ondelete='set null',
        copy=False,
        help="Reference to the ir.model.fields record that was created.",
    )

    created_view_id = fields.Many2one(
        comodel_name='ir.ui.view',
        string="Created View Extension",
        readonly=True,
        ondelete='set null',
        copy=False,
        help="Reference to the inheriting ir.ui.view record that injects the field.",
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        default=lambda self: self.env.company,
        index=True,
    )

    # ------------------------------------------------------------------
    # SQL Constraints
    # ------------------------------------------------------------------
    _sql_constraints = [
        (
            'unique_technical_name_model',
            'UNIQUE(technical_name, model_id)',
            'A field with this technical name already exists for the selected model.',
        ),
    ]

    # ------------------------------------------------------------------
    # Computed Fields
    # ------------------------------------------------------------------
    @api.depends('name')
    def _compute_technical_name(self):
        """Auto-generate ``x_pgm_<sanitized_label>`` from the field label."""
        for rec in self:
            if not rec.name:
                rec.technical_name = False
                continue
            # Normalize unicode → strip accents → lowercase
            normalized = unicodedata.normalize('NFKD', rec.name)
            ascii_name = normalized.encode('ascii', 'ignore').decode('ascii')
            lower_name = ascii_name.lower().strip()
            # Replace anything non-alphanumeric with underscores
            clean_name = re.sub(r'[^a-z0-9]+', '_', lower_name)
            clean_name = clean_name.strip('_')
            if clean_name:
                rec.technical_name = f'{TECHNICAL_NAME_PREFIX}{clean_name}'
            else:
                rec.technical_name = False

    # ------------------------------------------------------------------
    # Onchange / Validation
    # ------------------------------------------------------------------
    @api.constrains('field_type', 'selection_options')
    def _check_selection_options(self):
        for rec in self:
            if rec.field_type == 'selection' and not rec.selection_options:
                raise ValidationError(
                    _("Selection Options are required when the field type is 'Dropdown (Selection)'.\n"
                      "Please provide key:Label pairs, one per line.")
                )

    @api.constrains('field_type', 'relation_model_id')
    def _check_relation_model(self):
        for rec in self:
            if rec.field_type == 'many2one' and not rec.relation_model_id:
                raise ValidationError(
                    _("A Related Model is required when the field type is 'Link to another model (Many2one)'.")
                )

    @api.constrains('technical_name')
    def _check_technical_name_valid(self):
        for rec in self:
            if rec.technical_name and not re.match(r'^x_pgm_[a-z0-9_]+$', rec.technical_name):
                raise ValidationError(
                    _("The technical name '%(name)s' is invalid. "
                      "It must only contain lowercase letters, digits, and underscores.",
                      name=rec.technical_name)
                )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_confirm(self):
        """Create the field in ``ir.model.fields`` and inject into the form view."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Only records in 'Draft' status can be confirmed."))
        if not self.technical_name:
            raise UserError(_("Cannot confirm: the technical name could not be generated. "
                              "Please enter a valid Field Label."))

        # --- Check for duplicate field on target model ---
        existing_field = self.env['ir.model.fields'].sudo().search([
            ('model_id', '=', self.model_id.id),
            ('name', '=', self.technical_name),
        ], limit=1)
        if existing_field:
            raise UserError(
                _("A field with technical name '%(tech)s' already exists on model '%(model)s'.",
                  tech=self.technical_name,
                  model=self.model_id.name)
            )

        _logger.info(
            "Creating field '%s' (%s) on model '%s' ...",
            self.technical_name, self.field_type, self.model_id.model,
        )

        try:
            created_field = self._create_ir_model_field()
            _logger.info(
                "Field '%s' (id=%s) created successfully on '%s'.",
                self.technical_name, created_field.id, self.model_id.model,
            )
        except Exception:
            _logger.exception(
                "Failed to create ir.model.fields for '%s' on '%s'.",
                self.technical_name, self.model_id.model,
            )
            raise

        # --- Auto-inject into form view ---
        created_view = False
        try:
            created_view = self._inject_into_form_view()
            if created_view:
                _logger.info(
                    "View extension (id=%s) created to inject '%s' into '%s' form.",
                    created_view.id, self.technical_name, self.model_id.model,
                )
            else:
                _logger.warning(
                    "No form view found for model '%s'. "
                    "Field '%s' was created but not injected into any view.",
                    self.model_id.model, self.technical_name,
                )
        except Exception:
            _logger.exception(
                "Failed to inject '%s' into form view of '%s'. "
                "The field was created but is not visible in any view.",
                self.technical_name, self.model_id.model,
            )

        self.write({
            'state': 'done',
            'created_field_id': created_field.id,
            'created_view_id': created_view.id if created_view else False,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Field Created Successfully"),
                'message': _(
                    "The field '%(label)s' (%(tech)s) has been created on %(model)s.",
                    label=self.name,
                    tech=self.technical_name,
                    model=self.model_id.name,
                ),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def action_remove_field(self):
        """Remove the created field and its view extension from the database."""
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_("Only records in 'Created' status can be removed."))

        _logger.info(
            "Removing field '%s' from model '%s' ...",
            self.technical_name, self.model_id.model,
        )

        errors = []

        # --- Remove view extension first ---
        if self.created_view_id:
            try:
                view_id = self.created_view_id.id
                self.created_view_id.sudo().unlink()
                _logger.info("Removed view extension (id=%s).", view_id)
            except Exception:
                _logger.exception("Failed to remove view extension (id=%s).", self.created_view_id.id)
                errors.append(_("Could not remove the view extension."))

        # --- Remove the field ---
        if self.created_field_id:
            try:
                field_id = self.created_field_id.id
                self.created_field_id.sudo().unlink()
                _logger.info("Removed ir.model.fields (id=%s).", field_id)
            except Exception:
                _logger.exception("Failed to remove ir.model.fields (id=%s).", self.created_field_id.id)
                errors.append(_("Could not remove the field from the model."))

        if errors:
            raise UserError('\n'.join(errors))

        self.write({
            'state': 'removed',
            'created_field_id': False,
            'created_view_id': False,
        })

        _logger.info("Field '%s' removed successfully.", self.technical_name)

    def action_reset_to_draft(self):
        """Reset a removed record back to draft so it can be re-created."""
        self.ensure_one()
        if self.state != 'removed':
            raise UserError(_("Only records in 'Removed' status can be reset to draft."))
        self.write({'state': 'draft'})
        _logger.info("Record '%s' reset to draft.", self.technical_name)

    # ------------------------------------------------------------------
    # CRUD Overrides
    # ------------------------------------------------------------------
    def unlink(self):
        """Clean up created fields and views when the creator record is deleted."""
        for rec in self:
            if rec.state == 'done':
                raise UserError(
                    _("Cannot delete a record in 'Created' status. "
                      "Please remove the field first (use the 'Remove Field' button), "
                      "then delete this record.")
                )
        return super().unlink()

    def copy(self, default=None):
        """Append '(Copy)' to the name on duplicate."""
        default = dict(default or {})
        default.setdefault('name', _("%s (Copy)", self.name))
        return super().copy(default)

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------
    def _create_ir_model_field(self):
        """Create an ``ir.model.fields`` record for the configured field.

        Returns:
            ir.model.fields recordset (singleton)
        """
        self.ensure_one()
        vals = {
            'name': self.technical_name,
            'field_description': self.name,
            'model_id': self.model_id.id,
            'ttype': self.field_type,
            'help': self.help_text or False,
            'required': self.required_field,
            'copied': self.copied_field,
        }

        # --- Selection options ---
        if self.field_type == 'selection':
            parsed_options = self._parse_selection_options()
            vals['selection_ids'] = [
                (0, 0, {
                    'value': key,
                    'name': label,
                    'sequence': idx * 10,
                })
                for idx, (key, label) in enumerate(parsed_options)
            ]

        # --- Many2one relation ---
        if self.field_type == 'many2one':
            vals['relation'] = self.relation_model_id.model
            vals['on_delete'] = 'set null'

        return self.env['ir.model.fields'].sudo().create(vals)

    def _inject_into_form_view(self):
        """Create an inheriting ``ir.ui.view`` that adds the field to the
        target model's primary form view.

        Returns:
            ir.ui.view recordset (singleton) or False if no form view found.
        """
        self.ensure_one()

        # Find the primary (non-inherited) form view for the model
        form_view = self.env['ir.ui.view'].sudo().search([
            ('model', '=', self.model_id.model),
            ('type', '=', 'form'),
            ('inherit_id', '=', False),
        ], limit=1, order='priority ASC, id ASC')

        if not form_view:
            return False

        # Build a small arch that injects the field inside the sheet
        field_widget = self._get_widget_for_type()
        field_attrs = f'name="{self.technical_name}"'
        if field_widget:
            field_attrs += f' widget="{field_widget}"'

        arch = (
            '<data>\n'
            '    <xpath expr="//sheet" position="inside">\n'
            '        <group string="Custom Fields (Extended)" name="extended_custom_fields">\n'
            f'            <field {field_attrs}/>\n'
            '        </group>\n'
            '    </xpath>\n'
            '</data>'
        )

        view_vals = {
            'name': f'extended.field.creator.inject.{self.technical_name}',
            'model': self.model_id.model,
            'inherit_id': form_view.id,
            'arch': arch,
            'priority': 999,
        }

        return self.env['ir.ui.view'].sudo().create(view_vals)

    def _parse_selection_options(self):
        """Parse the ``selection_options`` text field into a list of (key, label) tuples.

        Expected format (one pair per line)::

            draft:Draft
            confirmed:Confirmed
            done:Done

        Returns:
            list[tuple[str, str]]

        Raises:
            ValidationError: if the format is invalid.
        """
        self.ensure_one()
        if not self.selection_options:
            return []

        result = []
        for line_num, raw_line in enumerate(self.selection_options.strip().splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            if ':' not in line:
                raise ValidationError(
                    _("Invalid selection option on line %(line)s: '%(text)s'.\n"
                      "Expected format: key:Label (e.g. 'draft:Draft').",
                      line=line_num, text=line)
                )
            key, label = line.split(':', 1)
            key = key.strip()
            label = label.strip()
            if not key or not label:
                raise ValidationError(
                    _("Empty key or label on line %(line)s: '%(text)s'.\n"
                      "Both key and label are required.",
                      line=line_num, text=line)
                )
            # Validate key is a valid Python identifier-style string
            if not re.match(r'^[a-z0-9_]+$', key):
                raise ValidationError(
                    _("Invalid key '%(key)s' on line %(line)s.\n"
                      "Keys must contain only lowercase letters, digits, and underscores.",
                      key=key, line=line_num)
                )
            result.append((key, label))

        if not result:
            raise ValidationError(
                _("No valid selection options found. "
                  "Please provide key:Label pairs, one per line.")
            )
        return result

    @staticmethod
    def _get_widget_for_type():
        """Return a recommended widget name for the field type, or False."""
        # Most types use the default widget — only override where it helps.
        return False
