# -*- coding: utf-8 -*-
import logging
import os
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import odoo.modules

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

TECHNICAL_NAME_PREFIX = 'smm_'

FIELD_CLASS_MAP = {
    'char': 'Char',
    'text': 'Text',
    'html': 'Html',
    'integer': 'Integer',
    'float': 'Float',
    'monetary': 'Monetary',
    'boolean': 'Boolean',
    'date': 'Date',
    'datetime': 'Datetime',
    'binary': 'Binary',
    'selection': 'Selection',
    'many2one': 'Many2one',
}

TARGET_MODULE = 'extended_fields'


class ExtendedFieldCreator(models.Model):
    """UI-driven code generator for the ``extended_fields`` addon.

    When a field definition is confirmed, this model generates:
    - A Python field definition in ``extended_fields/models/<model>.py``
    - An XML view extension in ``extended_fields/views/<model>_views.xml``

    After generation, the ``extended_fields`` module must be upgraded
    for the new field to become active.
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
        required=True,
        tracking=True,
        help="Technical name used in Python code. Must start with 'smm_' "
             "and contain only lowercase letters, digits, and underscores.",
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

    # --- References to generated code files ---
    generated_model_file = fields.Char(
        string="Generated Model File",
        readonly=True,
        copy=False,
        help="Relative path to the Python model file where the field was generated.",
    )

    generated_view_file = fields.Char(
        string="Generated View File",
        readonly=True,
        copy=False,
        help="Relative path to the XML view file where the field was generated.",
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
    @api.onchange('technical_name')
    def _onchange_technical_name(self):
        """Auto-prepend ``smm_`` prefix if the user forgets it."""
        for rec in self:
            if rec.technical_name and not rec.technical_name.startswith(TECHNICAL_NAME_PREFIX):
                # Clean the input: lowercase, replace non-alnum with underscores
                cleaned = re.sub(r'[^a-z0-9_]+', '_', rec.technical_name.lower().strip())
                cleaned = cleaned.strip('_')
                if cleaned:
                    rec.technical_name = f'{TECHNICAL_NAME_PREFIX}{cleaned}'

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
            if rec.technical_name and not re.match(r'^smm_[a-z0-9_]+$', rec.technical_name):
                raise ValidationError(
                    _("The technical name '%(name)s' is invalid. "
                      "It must only contain lowercase letters, digits, and underscores.",
                      name=rec.technical_name)
                )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_confirm(self):
        """Generate Python and XML code in the ``extended_fields`` addon."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Only records in 'Draft' status can be confirmed."))
        if not self.technical_name:
            raise UserError(_("Cannot confirm: the technical name could not be generated. "
                              "Please enter a valid Field Label."))

        module_path = self._get_extended_fields_path()

        # --- Check for duplicate field in target model file ---
        model_filename = self._get_model_filename()
        model_filepath = os.path.join(module_path, 'models', model_filename)
        if os.path.isfile(model_filepath):
            content = self._read_file(model_filepath)
            # Match both active and commented-out definitions
            if re.search(rf'^\s+{re.escape(self.technical_name)}\s*=\s*fields\.', content, re.MULTILINE):
                raise UserError(
                    _("A field with technical name '%(tech)s' already exists in %(file)s.",
                      tech=self.technical_name,
                      file=model_filename)
                )

        _logger.info(
            "Generating code for field '%s' (%s) on model '%s' ...",
            self.technical_name, self.field_type, self.model_id.model,
        )

        # --- Generate Python model code ---
        try:
            model_file_rel = self._generate_model_code(module_path)
            _logger.info(
                "Python code generated in '%s' for field '%s'.",
                model_file_rel, self.technical_name,
            )
        except Exception:
            _logger.exception(
                "Failed to generate model code for '%s' on '%s'.",
                self.technical_name, self.model_id.model,
            )
            raise

        # --- Generate XML view code ---
        view_file_rel = False
        try:
            view_file_rel = self._generate_view_xml(module_path)
            if view_file_rel:
                _logger.info(
                    "XML view code generated in '%s' for field '%s'.",
                    view_file_rel, self.technical_name,
                )
            else:
                _logger.warning(
                    "No form view found for model '%s'. "
                    "Field '%s' code was generated but no view extension was created.",
                    self.model_id.model, self.technical_name,
                )
        except Exception:
            _logger.exception(
                "Failed to generate view XML for '%s' on '%s'. "
                "The Python code was generated but the field is not visible in any view.",
                self.technical_name, self.model_id.model,
            )

        self.write({
            'state': 'done',
            'generated_model_file': model_file_rel,
            'generated_view_file': view_file_rel or False,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Code Generated Successfully"),
                'message': _(
                    "The field '%(label)s' (%(tech)s) has been generated in the "
                    "extended_fields module.\n"
                    "Please upgrade the 'extended_fields' module to activate the field.",
                    label=self.name,
                    tech=self.technical_name,
                ),
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def action_remove_field(self):
        """Remove the generated field code from the ``extended_fields`` addon."""
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_("Only records in 'Created' status can be removed."))

        _logger.info(
            "Removing generated code for field '%s' from model '%s' ...",
            self.technical_name, self.model_id.model,
        )

        module_path = self._get_extended_fields_path()
        errors = []

        # --- Remove from XML view first ---
        if self.generated_view_file:
            try:
                self._remove_field_from_view(module_path)
                _logger.info("Removed field '%s' from view XML.", self.technical_name)
            except Exception:
                _logger.exception("Failed to remove field '%s' from view XML.", self.technical_name)
                errors.append(_("Could not remove the field from the view XML."))

        # --- Comment out from Python model ---
        if self.generated_model_file:
            try:
                self._remove_field_from_model(module_path)
                _logger.info("Commented out field '%s' in model code.", self.technical_name)
            except Exception:
                _logger.exception("Failed to comment out field '%s' in model code.", self.technical_name)
                errors.append(_("Could not comment out the field in the model code."))

        if errors:
            raise UserError('\n'.join(errors))

        self.write({
            'state': 'removed',
            'generated_model_file': False,
            'generated_view_file': False,
        })

        _logger.info("Field '%s' code removed successfully.", self.technical_name)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Field Code Removed"),
                'message': _(
                    "The code for field '%(label)s' (%(tech)s) has been removed.\n"
                    "Please upgrade the 'extended_fields' module to apply changes.",
                    label=self.name,
                    tech=self.technical_name,
                ),
                'type': 'warning',
                'sticky': True,
            },
        }

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
        """Prevent deletion of records whose code is already generated."""
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
    # Code Generation — Python Model
    # ------------------------------------------------------------------
    def _generate_model_code(self, module_path):
        """Generate or append a Python field definition in ``extended_fields``.

        Returns:
            str: Relative path to the generated model file (e.g. ``models/res_partner.py``).
        """
        self.ensure_one()
        model_filename = self._get_model_filename()
        model_filepath = os.path.join(module_path, 'models', model_filename)
        field_code = self._build_field_definition()

        if os.path.isfile(model_filepath):
            # Append field to existing file
            content = self._read_file(model_filepath)
            if not content.endswith('\n'):
                content += '\n'
            content += '\n' + field_code + '\n'
            self._write_file(model_filepath, content)
        else:
            # Create new model file
            class_name = self._get_class_name()
            content = (
                "# -*- coding: utf-8 -*-\n"
                "from odoo import fields, models\n"
                "\n"
                "\n"
                f"class {class_name}(models.Model):\n"
                f"    _inherit = '{self.model_id.model}'\n"
                "\n"
                f"{field_code}\n"
            )
            self._write_file(model_filepath, content)
            # Update models/__init__.py
            self._update_init_file(module_path, model_filename.replace('.py', ''))

        return f"models/{model_filename}"

    def _build_field_definition(self):
        """Build a Python field definition string.

        Returns:
            str: Multi-line field definition indented with 4 spaces.
        """
        self.ensure_one()
        field_class = FIELD_CLASS_MAP.get(self.field_type, 'Char')

        # Positional arguments (before keyword args)
        positional_args = []

        if self.field_type == 'many2one':
            positional_args.append(f"'{self.relation_model_id.model}'")

        if self.field_type == 'selection':
            options = self._parse_selection_options()
            sel_items = ', '.join(f"('{k}', '{l}')" for k, l in options)
            positional_args.append(f"[{sel_items}]")

        # Keyword arguments
        kwargs = []
        kwargs.append(f'string="{self.name}"')

        if self.help_text:
            escaped_help = self.help_text.replace('\\', '\\\\').replace('"', '\\"')
            kwargs.append(f'help="{escaped_help}"')

        if self.required_field:
            kwargs.append('required=True')

        if not self.copied_field:
            kwargs.append('copy=False')

        if self.field_type == 'many2one':
            kwargs.append("ondelete='set null'")

        # Combine all args
        all_args = positional_args + kwargs

        # Always use multi-line format for consistency with extended_fields style
        formatted_args = ',\n        '.join(all_args)
        return (
            f"    {self.technical_name} = fields.{field_class}(\n"
            f"        {formatted_args},\n"
            f"    )"
        )

    # ------------------------------------------------------------------
    # Code Generation — XML View
    # ------------------------------------------------------------------
    def _generate_view_xml(self, module_path):
        """Generate or append an XML view extension in ``extended_fields``.

        Returns:
            str or False: Relative path to the view file, or False if no form view found.
        """
        self.ensure_one()
        view_filename = self._get_view_filename(module_path)
        view_filepath = os.path.join(module_path, 'views', view_filename)

        # We need the base form view's external ID for the inherit_id ref
        base_view_xmlid = self._find_base_form_view_xmlid()
        if not base_view_xmlid:
            return False

        model_safe = self.model_id.model.replace('.', '_')
        record_id = f"view_{model_safe}_form_extended_custom_fields"
        field_line = f'                        <field name="{self.technical_name}"/>'

        if os.path.isfile(view_filepath):
            content = self._read_file(view_filepath)

            if f'id="{record_id}"' in content:
                # Record already exists — add field to the existing custom fields group
                marker = 'name="extended_custom_fields"'
                marker_idx = content.find(marker)
                if marker_idx != -1:
                    # Find the closing </group> tag after the marker
                    close_group_idx = content.find('</group>', marker_idx)
                    if close_group_idx != -1:
                        # Insert the field line before </group>
                        indent = '                    '
                        insert_text = field_line + '\n' + indent
                        content = (
                            content[:close_group_idx]
                            + insert_text
                            + content[close_group_idx:]
                        )
                        self._write_file(view_filepath, content)
            else:
                # Record doesn't exist yet — create a new one in this file
                new_record = self._build_view_record(record_id, base_view_xmlid)
                # Insert before the closing </odoo> or </data> tag
                for closing_tag in ['</data>', '</odoo>']:
                    close_idx = content.rfind(closing_tag)
                    if close_idx != -1:
                        content = (
                            content[:close_idx]
                            + '\n' + new_record + '\n\n    '
                            + content[close_idx:]
                        )
                        self._write_file(view_filepath, content)
                        break
        else:
            # Create a brand-new view file
            content = self._build_view_file(record_id, base_view_xmlid)
            # Ensure the views directory exists
            views_dir = os.path.join(module_path, 'views')
            os.makedirs(views_dir, exist_ok=True)
            self._write_file(view_filepath, content)
            # Update __manifest__.py
            self._update_manifest_file(module_path, view_filename)

        return f"views/{view_filename}"

    def _build_view_record(self, record_id, base_view_xmlid):
        """Build an XML ``<record>`` string for a custom fields view extension.

        Returns:
            str: XML record block.
        """
        self.ensure_one()
        model_name = self.model_id.model
        return (
            f'    <record id="{record_id}" model="ir.ui.view">\n'
            f'        <field name="name">{model_name}.form.extended.custom.fields</field>\n'
            f'        <field name="model">{model_name}</field>\n'
            f'        <field name="inherit_id" ref="{base_view_xmlid}"/>\n'
            f'        <field name="priority">999</field>\n'
            f'        <field name="arch" type="xml">\n'
            f'            <xpath expr="//sheet" position="inside">\n'
            f'                <group string="Custom Fields (Extended)" name="extended_custom_fields">\n'
            f'                    <field name="{self.technical_name}"/>\n'
            f'                </group>\n'
            f'            </xpath>\n'
            f'        </field>\n'
            f'    </record>'
        )

    def _build_view_file(self, record_id, base_view_xmlid):
        """Build a complete XML view file with one inherited view record.

        Returns:
            str: Full XML file content.
        """
        self.ensure_one()
        record_content = self._build_view_record(record_id, base_view_xmlid)
        return (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<odoo>\n'
            f'{record_content}\n'
            '</odoo>\n'
        )

    # ------------------------------------------------------------------
    # Code Removal
    # ------------------------------------------------------------------
    def _remove_field_from_model(self, module_path):
        """Comment out the field definition in the Python model file."""
        self.ensure_one()
        model_filename = self._get_model_filename()
        model_filepath = os.path.join(module_path, 'models', model_filename)

        if not os.path.isfile(model_filepath):
            _logger.warning("Model file '%s' not found; nothing to remove.", model_filepath)
            return

        content = self._read_file(model_filepath)
        lines = content.split('\n')

        field_pattern = re.compile(
            rf'^(\s+){re.escape(self.technical_name)}\s*=\s*fields\.'
        )

        field_start = None
        field_end = None

        for i, line in enumerate(lines):
            if field_pattern.match(line):
                field_start = i
                # Track parentheses to find the end of the field definition
                paren_depth = 0
                for j in range(i, len(lines)):
                    paren_depth += lines[j].count('(') - lines[j].count(')')
                    if paren_depth <= 0:
                        field_end = j
                        break
                if field_end is None:
                    field_end = i
                break

        if field_start is not None:
            for i in range(field_start, field_end + 1):
                lines[i] = '    # REMOVED: ' + lines[i].lstrip()
            self._write_file(model_filepath, '\n'.join(lines))
            _logger.info(
                "Commented out lines %d-%d in '%s'.",
                field_start + 1, field_end + 1, model_filepath,
            )
        else:
            _logger.warning(
                "Could not find field '%s' in '%s'; file was not modified.",
                self.technical_name, model_filepath,
            )

    def _remove_field_from_view(self, module_path):
        """Remove the field element from the XML view file."""
        self.ensure_one()
        view_filename = self._get_view_filename(module_path)
        view_filepath = os.path.join(module_path, 'views', view_filename)

        if not os.path.isfile(view_filepath):
            _logger.warning("View file '%s' not found; nothing to remove.", view_filepath)
            return

        content = self._read_file(view_filepath)

        # Remove lines containing <field name="technical_name"/>
        field_pattern = re.compile(
            rf'^\s*<field\s+name="{re.escape(self.technical_name)}"\s*/>\s*\n?',
            re.MULTILINE,
        )
        new_content = field_pattern.sub('', content)

        if new_content != content:
            self._write_file(view_filepath, new_content)
            _logger.info("Removed field '%s' from '%s'.", self.technical_name, view_filepath)
        else:
            _logger.warning(
                "Could not find field '%s' in view file '%s'.",
                self.technical_name, view_filepath,
            )

    # ------------------------------------------------------------------
    # Path & Naming Helpers
    # ------------------------------------------------------------------
    def _get_extended_fields_path(self):
        """Return the absolute filesystem path to the ``extended_fields`` addon.

        Raises:
            UserError: If the module cannot be found.
        """
        module_path = odoo.modules.get_module_path(TARGET_MODULE, display_warning=False)
        if not module_path:
            raise UserError(
                _("Cannot find the '%(module)s' module on the filesystem. "
                  "Please ensure it is installed and the addons path is configured correctly.",
                  module=TARGET_MODULE)
            )
        return module_path

    def _get_model_filename(self):
        """Return the Python filename for the target model (e.g. ``res_partner.py``).

        Returns:
            str
        """
        self.ensure_one()
        return self.model_id.model.replace('.', '_') + '.py'

    def _get_view_filename(self, module_path):
        """Return the XML view filename for the target model.

        Tries to find an existing file first (with or without ``_views`` suffix),
        falling back to ``{model}_views.xml`` for new files.

        Returns:
            str
        """
        self.ensure_one()
        model_safe = self.model_id.model.replace('.', '_')
        views_dir = os.path.join(module_path, 'views')

        # Check existing naming patterns
        candidate_views = f"{model_safe}_views.xml"
        candidate_plain = f"{model_safe}.xml"

        if os.path.isfile(os.path.join(views_dir, candidate_views)):
            return candidate_views
        if os.path.isfile(os.path.join(views_dir, candidate_plain)):
            return candidate_plain

        # Default for new files
        return candidate_views

    def _get_class_name(self):
        """Generate a Python class name from the model name.

        Example: ``account.move.line`` → ``AccountMoveLine``

        Returns:
            str
        """
        self.ensure_one()
        return ''.join(word.capitalize() for word in self.model_id.model.split('.'))

    def _find_base_form_view_xmlid(self):
        """Find the external XML ID of the primary form view for the target model.

        Returns:
            str or False: e.g. ``account.view_account_form``
        """
        self.ensure_one()
        form_view = self.env['ir.ui.view'].sudo().search([
            ('model', '=', self.model_id.model),
            ('type', '=', 'form'),
            ('inherit_id', '=', False),
        ], limit=1, order='priority ASC, id ASC')

        if not form_view:
            return False

        external_ids = form_view.get_external_id()
        xmlid = external_ids.get(form_view.id, '')
        return xmlid or False

    # ------------------------------------------------------------------
    # File Update Helpers
    # ------------------------------------------------------------------
    def _update_init_file(self, module_path, module_name):
        """Add an import line to ``models/__init__.py`` if not already present.

        Args:
            module_path: Absolute path to the ``extended_fields`` addon.
            module_name: Python module name (without ``.py``), e.g. ``res_partner``.
        """
        init_path = os.path.join(module_path, 'models', '__init__.py')
        import_line = f"from . import {module_name}"

        if os.path.isfile(init_path):
            content = self._read_file(init_path)
            if import_line in content:
                return  # Already present
            if not content.endswith('\n'):
                content += '\n'
            content += f"{import_line}\n"
            self._write_file(init_path, content)
        else:
            content = f"# -*- coding: utf-8 -*-\n{import_line}\n"
            self._write_file(init_path, content)

        _logger.info("Updated %s with import for '%s'.", init_path, module_name)

    def _update_manifest_file(self, module_path, view_filename):
        """Add a view file entry to ``__manifest__.py``'s ``data`` list.

        Args:
            module_path: Absolute path to the ``extended_fields`` addon.
            view_filename: Filename of the view XML file, e.g. ``crm_lead_views.xml``.
        """
        manifest_path = os.path.join(module_path, '__manifest__.py')
        view_entry = f"views/{view_filename}"

        content = self._read_file(manifest_path)
        if view_entry in content:
            return  # Already present

        # Find the 'data' list and insert before its closing bracket
        lines = content.split('\n')
        in_data = False
        insert_idx = None

        for i, line in enumerate(lines):
            stripped = line.strip()
            if "'data'" in line or '"data"' in line:
                in_data = True
            if in_data and (stripped.startswith('],') or stripped == ']'):
                insert_idx = i
                break

        if insert_idx is not None:
            # Determine indentation from surrounding lines
            indent = '        '
            new_line = f"{indent}'{view_entry}',"
            lines.insert(insert_idx, new_line)
            self._write_file(manifest_path, '\n'.join(lines))
            _logger.info("Updated %s with view file '%s'.", manifest_path, view_entry)
        else:
            _logger.warning(
                "Could not find 'data' list in %s. Please add '%s' manually.",
                manifest_path, view_entry,
            )

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------
    @staticmethod
    def _read_file(filepath):
        """Read a file and return its content as a string."""
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def _write_file(filepath, content):
        """Write content to a file, creating parent directories if needed."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    # ------------------------------------------------------------------
    # Selection Options Parser
    # ------------------------------------------------------------------
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
