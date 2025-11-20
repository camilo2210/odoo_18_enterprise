import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class StoreViewNodes(models.Model):
    """Store view node data for UI element management."""

    _name = "view.node.data"
    _description = "Store View Nodes"
    _rec_name = "attribute_string"

    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        help="Select the model for which the view node settings should be applied.",
    )

    model = fields.Char(
        string="Technical Model Name",
        related="model_id.model",
        store=True,
        help="The technical name of the selected model.",
    )

    node_option = fields.Selection(
        [
            ("button", "Button"),
            ("page", "Page"),
            ("filter", "Filter"),
            ("groupby", "Group By"),
        ],
        string="Node Type",
        required=True,
        help="Defines the type of view node, such as a button, a page, or a link.",
    )

    attribute_name = fields.Char(
        string="Attribute Name",
        help="The name of the XML attribute to modify in the selected node.",
    )

    attribute_string = fields.Char(
        string="Attribute Label",
        help="The label associated with the attribute, used for display purposes.",
    )

    lang_code = fields.Char(
        string="Language Code",
        help="Specify the language code for translations, if applicable.",
    )

    button_type = fields.Selection(
        [("object", "Object"), ("action", "Action")],
        string="Button Type",
        help="Defines whether the button triggers an object method or an action.",
    )

    is_smart_button = fields.Boolean(
        string="Smart Button",
        help="Indicates if the button is a smart button, typically linking to related records.",
    )

    view_name = fields.Char(
        string="View Name",
        help=(
            "Logical view bucket this node belongs to. Examples: 'form', 'list header', "
            "'list row', 'kanban'. Stored as text for flexibility across versions."
        ),
    )

    @api.depends("attribute_string", "attribute_name", "is_smart_button", "node_option", "button_type", "view_name")
    def _compute_display_name(self):
        for rec in self:
            # Humanize view bucket (e.g., 'list header' -> 'List Header')
            view_bucket = (rec.view_name or "").replace("_", " ").strip().title()

            # Determine kind label without action/object mention
            if rec.node_option == "page":
                kind = "Tab"
            # links removed from management
            elif rec.node_option == "button":
                kind = "Smart Button" if rec.is_smart_button else "Button"
            else:
                kind = (rec.node_option or "").title() or "Node"

            prefix = f"{view_bucket} {kind}" if view_bucket else kind

            # Main label and technical name
            label = rec.attribute_string or "Unnamed"
            tech = rec.attribute_name or ""
            if tech:
                label = f"{label} ({tech})"

            rec.display_name = f"{prefix} — {label}"
