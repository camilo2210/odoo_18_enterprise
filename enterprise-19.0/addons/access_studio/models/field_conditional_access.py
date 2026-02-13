import logging

from odoo import api, fields, models, tools
from odoo.tools.safe_eval import safe_eval

from .access_studio import MODELS

from ..utils.domain_utils import domain_to_expression

_logger = logging.getLogger(__name__)


class FieldConditionalAccess(models.Model):
    """Dynamic field restrictions based on record state or conditions."""

    _name = "field.conditional.access"
    _description = "Field Conditional Access Control"

    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        domain=[("model", "not in", MODELS)],
        help="Target model for conditional field access.",
    )
    model = fields.Char(
        string="Model Name",
        related="model_id.model",
        store=True,
        help="Technical name of the target model.",
    )
    access_studio_id = fields.Many2one(
        "access.studio",
        string="Access Rule Set",
        ondelete="cascade",
        help="Parent access control rule set.",
    )

    apply_attrs = fields.Boolean(
        string="Apply Attributes",
        default=False,
        help="Enable Attribute-based field restrictions.",
    )
    attrs_field_id = fields.Many2one(
        "ir.model.fields",
        string="Attribute on Field",
        domain="[('model_id', '=', model_id)]",
        ondelete="cascade",
        help="Field on which to apply Attribute access control.",
    )
    attrs_type = fields.Selection(
        [
            ("required", "Required"),
            ("readonly", "Readonly"),
            ("invisible", "Invisible"),
        ],
        string="Attribute Type",
        default="required",
        help="Type of Attribute restriction to apply.",
    )
    attrs_domain = fields.Char(
        string="Attribute Condition", help="Condition for applying the Attribute restriction."
    )

    apply_field_domain = fields.Boolean(
        string="Apply Condition", default=False, help="Enable Condition Field restrictions."
    )
    domain_on_field_id = fields.Many2one(
        "ir.model.fields",
        string="Condition on Field",
        domain="[('model_id', '=', model_id), ('ttype', 'in', ['many2one', 'many2many', 'one2many'])]",
        ondelete="cascade",
        help="Field to apply the Condition on.",
    )
    domain_field_relation = fields.Char(
        related="domain_on_field_id.relation",
        store=True,
    )
    field_domain = fields.Char(
        string="Condition",
        help="Condition for field access restriction on the field. (e.g. [('state', '=', 'draft')])",
    )

    @api.onchange("apply_field_domain")
    def _onchange_domain_on_field_id(self):
        if not self.apply_field_domain:
            self.domain_on_field_id = False
            self.field_domain = False

    @api.onchange("apply_attrs")
    def _onchange_attrs_field_id(self):
        if not self.apply_attrs:
            self.attrs_field_id = False
            self.attrs_type = False
            self.attrs_domain = False

    @api.model
    @tools.ormcache('self.env.uid', 'model_name', 'self.env.company')
    def get_cached_field_conditional_rules(self, model_name):
        domain = [
            ('model', '=', model_name),
            ('access_studio_id.active', '=', True),
            '|', ('access_studio_id.apply_without_companies', '=', True),
                 ('access_studio_id.company_ids', 'in', [self.env.company.id]),
            ('access_studio_id.user_ids', 'in', [self.env.user.id]),
        ]
        rules = self.sudo().search(domain)

        attrs_map = {}
        domain_map = {}

        # Attribute-based rules
        for r in rules.filtered(lambda x: x.apply_attrs and x.attrs_field_id and x.attrs_type):
            fname = r.attrs_field_id.name
            if not fname:
                continue
            slot = attrs_map.setdefault(fname, {'expr': {}})
            if r.attrs_domain:
                expr = domain_to_expression(r.attrs_domain)
                if expr:
                    prev = slot['expr'].get(r.attrs_type)
                    slot['expr'][r.attrs_type] = f"({prev}) and ({expr})" if prev else expr

        # Field domain rules (relational only)
        for r in rules.filtered(lambda x: x.apply_field_domain and x.domain_on_field_id and x.field_domain):
            fname = r.domain_on_field_id.name
            if not fname:
                continue
            # first rule wins for simplicity
            domain_map.setdefault(fname, r.field_domain.strip())

        return {'attrs_map': attrs_map, 'domain_map': domain_map}
