import logging

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval
from odoo.osv import expression

from .access_studio import MODELS

_logger = logging.getLogger(__name__)


class DomainAccess(models.Model):
    """Domain-based record filtering and access restrictions."""

    _name = "domain.access"
    _description = "Domain-Based Access Control"

    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        domain=[("model", "not in", MODELS)],
        help="Target model for domain-based access restrictions.",
    )
    model = fields.Char(
        string="Model Name",
        related="model_id.model",
        store=True,
        help="Technical name of the target model.",
    )
    access_studio_id = fields.Many2one(
        "access.studio",
        string="Access Control Rule Set",
        ondelete="cascade",
        help="Parent access control rule set.",
    )

    domain = fields.Char(
        string="Domain",
        help="Domain filter to restrict record visibility and operations.",
    )
    soft_restrict = fields.Boolean(
        string="Restrict Softly",
        help="Apply restriction without completely blocking access.",
    )

    restrict_read = fields.Boolean(
        string="Restrict Read", help="Allow reading records matching the domain filter."
    )
    restrict_write = fields.Boolean(
        string="Restrict Write", help="Allow modifying records matching the domain filter."
    )
    restrict_create = fields.Boolean(
        string="Restrict Create", help="Allow creating new records within domain constraints."
    )
    restrict_unlink = fields.Boolean(
        string="Restrict Delete", help="Allow deleting records matching the domain filter."
    )

    _sql_constraints = [
        (
            "unique_model_access_studio",
            "unique(model_id, access_studio_id, domain)",
            "Each model can have only one unique domain access control rule per simplified access control.",
        )
    ]

    @api.constrains("domain")
    def _check_domain_syntax(self):
        """Validate domain syntax to prevent invalid filters."""
        for rec in self:
            if rec.domain:
                try:
                    # Validate domain syntax by attempting to safely evaluate it
                    # Support common variables similar to ir.rule contexts
                    safe_eval(
                        rec.domain,
                        {
                            "uid": self.env.uid,
                            "user": self.env.user,
                            "context": dict(self.env.context),
                        },
                    )
                except Exception as e:
                    raise ValidationError(_("Invalid domain syntax: %s") % str(e))

    @api.model
    @tools.ormcache('self.env.uid', 'model_name', 'op', 'self.env.company')
    def get_cached_deny_domain(self, model_name: str, op: str):
        """Return a single OR-ed domain of all deny rules for the op, or None.

        op in {'read','write','create','unlink'}
        """
        if op not in {'read', 'write', 'create', 'unlink'}:
            return None
        field_name = f'restrict_{op}'
        domain = [
            ('model', '=', model_name),
            ('access_studio_id.active', '=', True),
            '|',
            ('access_studio_id.apply_without_companies', '=', True),
            ('access_studio_id.company_ids', 'in', [self.env.company.id]),
            ('access_studio_id.user_ids', 'in', [self.env.user.id]),
            (field_name, '=', True),
        ]
        rules = self.sudo().search(domain)
        parts = []
        for r in rules:
            if not r.domain:
                continue
            try:
                parts.append(safe_eval(r.domain))
            except Exception:
                continue
        if not parts:
            return None
        # OR all parts
        combined = parts[0]
        for d in parts[1:]:
            combined = expression.OR([combined, d])
        return combined
