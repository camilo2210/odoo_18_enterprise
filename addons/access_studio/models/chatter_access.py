import logging

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError

from .access_studio import MODELS

_logger = logging.getLogger(__name__)


class ChatterAccess(models.Model):
    """Model-specific chatter visibility control for models with chatter support."""

    _name = "chatter.access"
    _description = "Chatter Access"

    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        domain=[("model", "not in", MODELS)],
        help="Target model for chatter visibility controls.",
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

    hide_chatter = fields.Boolean(
        string="Hide Chatter", help="Hide the entire chatter section for this model."
    )

    hide_send_message = fields.Boolean(
        string="Hide Send Message", help="Hide the send message option in chatter."
    )
    hide_log_notes = fields.Boolean(
        string="Hide Log Notes", help="Hide the log notes option in chatter."
    )
    hide_schedule_activity = fields.Boolean(
        string="Hide Activities", help="Hide the schedule activity option in chatter."
    )

    hide_search_message_icon = fields.Boolean(
        string="Hide Search Message", help="Hide the search message icon in chatter."
    )

    hide_attachment_icon = fields.Boolean(
        string="Hide Attachment",
        help="Hide the attachment (paperclip) icon in chatter.",
    )

    hide_followers_icon = fields.Boolean(
        string="Hide Followers", help="Hide the followers (eye) icon in chatter."
    )

    hide_follow_unfollow = fields.Boolean(
        string="Hide Follow/Unfollow",
        help="Hide the follow/unfollow button in chatter.",
    )

    _sql_constraints = [
        (
            "unique_chatter_access_per_control",
            "unique(model_id, access_studio_id)",
            "Each model can have only one Chatter visibility rule per simplified access control.",
        )
    ]

    @api.constrains("model_id")
    def _check_chatter_support(self):
        """Ensure the selected model supports chatter functionality."""
        for rec in self:
            try:
                model = self.env[rec.model].sudo()
                if not hasattr(model, "_inherits") and not hasattr(model, "_name"):
                    raise ValidationError(
                        _("The selected model does not support chatter functionality.")
                    )
            except Exception as e:
                _logger.warning(
                    "Error checking chatter support for model %s: %s", rec.model, e
                )
                raise ValidationError(
                    _("The selected model does not support chatter functionality.")
                )

    @api.model
    @tools.ormcache('self.env.uid', 'model_name', 'self.env.company')
    def get_cached_chatter_access(self, model_name):
        """
        Get cached access control settings for the given model and company.
        """
        domain = [
            ("model", "=", model_name),
            ("access_studio_id.active", "=", True),
            "|",
            ("access_studio_id.apply_without_companies", "=", True),
            ("access_studio_id.company_ids", "in", [self.env.company.id]),
            ("access_studio_id.user_ids", "in", [self.env.user.id]),
        ]
        rules = self.env["chatter.access"].sudo().search(domain)

        global_access = self.env["access.studio"].get_global_access_studio_rules()

        hide_chatter = global_access.get("hide_chatter") or any(rules.mapped("hide_chatter"))
        hide_send_message = global_access.get("hide_send_message") or any(rules.mapped("hide_send_message"))
        hide_log_notes = global_access.get("hide_log_notes") or any(rules.mapped("hide_log_notes"))
        hide_schedule_activity = global_access.get("hide_schedule_activity") or any(rules.mapped("hide_schedule_activity"))
        hide_search_message_icon = global_access.get("hide_search_message_icon") or any(rules.mapped("hide_search_message_icon"))
        hide_attachment_icon = global_access.get("hide_attachment_icon") or any(rules.mapped("hide_attachment_icon"))
        hide_followers_icon = global_access.get("hide_followers_icon") or any(rules.mapped("hide_followers_icon"))
        hide_follow_unfollow = global_access.get("hide_follow_unfollow") or any(rules.mapped("hide_follow_unfollow"))

        return {
            'hide_chatter': hide_chatter,
            'hide_send_message': hide_send_message,
            'hide_log_notes': hide_log_notes,
            'hide_schedule_activity': hide_schedule_activity,
            'hide_search_message_icon': hide_search_message_icon,
            'hide_attachment_icon': hide_attachment_icon,
            'hide_followers_icon': hide_followers_icon,
            'hide_follow_unfollow': hide_follow_unfollow,
        }