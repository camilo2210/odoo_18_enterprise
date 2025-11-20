from odoo import _, api, models
from odoo.exceptions import AccessError


class IrModelAccess(models.Model):
    _inherit = "ir.model.access"

    @api.model
    def check(self, model, mode="read", raise_exception=True):
        # Superuser always allowed
        if self.env.su:
            return super().check(model, mode, raise_exception)

        # Only enforce when registry is ready and model is known
        if not getattr(self.pool, "ready", False):
            return super().check(model, mode, raise_exception)
        if model not in self.env:
            return super().check(model, mode, raise_exception)

        # Read cached rules
        cached = {}
        if mode in ("read", "write", "create", "unlink"):
            cached = self.env["model.access"].sudo().get_cached_model_access(model)

        # Map modes to flags
        deny = (
            (mode == "create" and cached.get("hide_create"))
            or (mode == "write" and cached.get("hide_edit"))
            or (mode == "unlink" and cached.get("hide_unlink"))
            or (mode == "read" and cached.get("hide_read"))
        )

        if deny:
            if raise_exception:
                msg = _(
                    "You do not have permission to %(op)s records of model "
                    "%(model)s (Simplified Access Control)."
                ) % {"op": mode, "model": model}
                raise AccessError(msg)
            return False

        # Fallback to standard ACLs
        return super().check(model, mode, raise_exception)