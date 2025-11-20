from odoo import models
from odoo.osv import expression


class IrRule(models.Model):
    _inherit = 'ir.rule'

    def _compute_domain(self, model_name, mode="read"):
        base = super()._compute_domain(model_name, mode=mode)
        if self.env.su or self._context.get('bypass_domain_access'):
            return base

        # Append NOT(deny) from Access Studio domain.access rules
        deny = self.env['domain.access'].get_cached_deny_domain(model_name, mode)
        if not deny:
            return base

        # Normalize and distribute NOT to avoid invalid leaf shapes
        deny_norm = expression.normalize_domain(deny)
        not_deny_flat = expression.distribute_not(['!'] + deny_norm)
        if base:
            return expression.AND([base, not_deny_flat])
        return not_deny_flat


