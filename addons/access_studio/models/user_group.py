import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class UserGroup(models.Model):
    """Custom user grouping for access control management."""

    _name = "user.group"
    _description = "User Group"

    name = fields.Char(
        string="Group Name",
        required=True,
        help="Name of the user group for identification.",
    )

    user_ids = fields.Many2many(
        "res.users",
        "user_group_user_rel",
        "user_group_id",
        "user_id",
        string="Users",
        help="Users assigned to this group.",
    )

    access_studio_ids = fields.Many2many(
        "access.studio",
        "access_studio_user_group_rel",
        "user_group_id",
        "access_studio_id",
        string="Simplified Access Control Rules",
        help="Access control rules applied to this user group.",
    )

    # SQL Constraints
    _sql_constraints = [
        (
            "unique_user_group_name",
            "unique(name)",
            "User group name must be unique. Please choose a different name.",
        ),
    ]

    @api.constrains("user_ids")
    def _check_user_uniqueness(self):
        """Ensure users are not assigned to multiple custom user groups."""
        for record in self:
            if record.user_ids:
                # Get all user IDs assigned to this group
                user_ids = record.user_ids.ids

                # Check if any of these users are already in other groups
                for user_id in user_ids:
                    # Find other groups that contain this user
                    other_groups = self.search([
                        ("user_ids", "in", user_id),
                        ("id", "!=", record.id)
                    ])

                    if other_groups:
                        user = self.env["res.users"].browse(user_id)
                        group_names = ", ".join(other_groups.mapped("name"))
                        raise ValidationError(_(
                            f"User '{user.name}' is already assigned to user group(s): {group_names}.\n"
                            "Each user can only belong to one custom user group.\n"
                            "Please remove the user from other groups first."
                        ))
