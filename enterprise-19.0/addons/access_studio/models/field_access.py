import logging

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError

from .access_studio import MODELS

_logger = logging.getLogger(__name__)


class FieldAccess(models.Model):
    """Granular field-level access control for specific models and fields."""

    _name = "field.access"
    _inherit = "access.studio.cache.mixin"
    _description = "Field Access Settings"

    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        domain=[("model", "not in", MODELS)],
        help="Target model for field access restrictions.",
    )
    model = fields.Char(
        string="Model Name",
        related="model_id.model",
        store=True,
        help="Technical name of the target model.",
    )
    access_studio_id = fields.Many2one(
        "access.studio",
        string="Simplified Access Control",
        ondelete="cascade",
        help="Parent Simplified Access Control configuration.",
    )

    field_ids = fields.Many2many(
        "ir.model.fields",
        "field_access_rel",
        "access_id",
        "field_id",
        string="Fields",
        help="Fields to apply access restrictions to.",
    )

    invisible = fields.Boolean(
        string="Invisible", help="Hide selected fields in the UI."
    )

    readonly = fields.Boolean(
        string="Read-Only", help="Make selected fields read-only."
    )

    required = fields.Boolean(string="Required", help="Make selected fields mandatory.")

    remove_create_option = fields.Boolean(
        string="Remove Create Option",
        help="Disable creation of related records for Many2one fields.",
    )

    remove_edit_option = fields.Boolean(
        string="Remove Edit Option",
        help="Disable editing of related records for Many2one fields.",
    )

    remove_internal_link = fields.Boolean(
        string="Remove Internal Link",
        help="Hide internal link icon for Many2one fields.",
    )

    @api.constrains("field_ids", "model_id")
    def _check_field_model_consistency(self):
        """Ensure selected fields belong to the selected model."""
        for rec in self:
            invalid_fields = rec.field_ids.filtered(
                lambda f: f.model_id.id != rec.model_id.id
            )
            if invalid_fields:
                field_names = ", ".join(invalid_fields.mapped("name"))
                raise ValidationError(
                    _("Some selected fields do not belong to the chosen model: %s")
                    % field_names
                )

    @api.model
    @tools.ormcache('self.env.uid', 'self.env.company', 'model_name')
    def get_cached_field_access(self, model_name):
        """
        Return a mapping of field technical names to enforcement flags for the
        given model, considering active rules for the current user/company.
        """
        domain = [
            ('model', '=', model_name),
            ('access_studio_id.active', '=', True),
            '|',
            ('access_studio_id.apply_without_companies', '=', True),
            ('access_studio_id.company_ids', 'in', [self.env.company.id]),
            ('access_studio_id.user_ids', 'in', [self.env.user.id]),
        ]
        rules = self.sudo().search(domain)

        access_map = {}
        for rule in rules:
            flags = {
                'invisible': bool(rule.invisible),
                'readonly': bool(rule.readonly),
                'required': bool(rule.required),
                'remove_create_option': bool(rule.remove_create_option),
                'remove_edit_option': bool(rule.remove_edit_option),
                'remove_internal_link': bool(rule.remove_internal_link),
            }
            for fld in rule.field_ids:
                cur = access_map.setdefault(fld.name, {
                    'invisible': False,
                    'readonly': False,
                    'required': False,
                    'remove_create_option': False,
                    'remove_edit_option': False,
                    'remove_internal_link': False,
                })
                for key, val in flags.items():
                    if val:
                        cur[key] = True
        return access_map
