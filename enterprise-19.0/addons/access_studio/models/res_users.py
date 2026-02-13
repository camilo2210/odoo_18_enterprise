from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import AccessDenied


class Users(models.Model):
    """Extended user model with simplified access control integration."""

    _inherit = "res.users"

    # Simplified Access Control Linkage
    access_studio_ids = fields.Many2many(
        "access.studio",
        "access_studio_users_rel",
        "user_id",
        "access_studio_id",
        string="Simplified Access Control Rules",
        help="Simplified Access Control rule sets that are assigned directly to this user.",
    )

    # Auto-link Default Access Control Rules to New Users
    @api.model_create_multi
    def create(self, vals_list):
        """Attach default Simplified Access Control rule sets to newly created users."""
        users = super().create(vals_list)
        access_studio_model = self.env["access.studio"].sudo()

        for user in users:
            # Determine user category (portal vs internal)
            is_portal = user.has_group("base.group_portal") or user.share

            # Build domain for matching access control rules
            domain = [("active", "=", True)]
            if is_portal:
                domain.append(("default_portal_user", "=", True))
            else:
                domain.append(("default_internal_user", "=", True))

            rules = access_studio_model.search(domain)
            if rules:
                # Link rules to user without replacing existing ones
                user.access_studio_ids = [(4, r.id) for r in rules]

        return users

    # Login Guard - Block Login if Disabled via Access Control
    def _check_credentials(self, credential, env):
        """Check credentials and block login if disabled by access control."""
        # Fetch user record by login if needed
        user = self
        if not self.id and credential.get("login"):
            user = self.sudo().search([("login", "=", credential["login"])], limit=1)

        # Only apply restrictions to non-superuser
        if user and user.id != SUPERUSER_ID:
            rules_domain = [
                ("active", "=", True),
                ("user_ids", "in", user.id),
                ("disable_login", "=", True),
                "|",
                ("apply_without_companies", "=", True),
                ("company_ids", "in", user.company_id.id if user.company_id else False),
            ]
            if self.env["access.studio"].sudo().search(rules_domain):
                raise AccessDenied(
                    _("Your login has been disabled by the administrator.")
                )

        return super()._check_credentials(credential, env)
