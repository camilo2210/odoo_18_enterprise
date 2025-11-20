import logging

from odoo import api, fields, models, tools

try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

from .access_studio import MODELS

_logger = logging.getLogger(__name__)


class SearchPanelAccess(models.Model):
    """Search panel and filter visibility control for specific models."""

    _name = "search.panel.access"
    _inherit = "access.studio.cache.mixin"
    _description = "Manage Search Panel Access"

    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        domain=[("model", "not in", MODELS)],
        help="Target model for search panel access control.",
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

    hide_search_panel = fields.Boolean(
        string="Hide Search Panel", help="Hide the entire search panel for this model."
    )

    hidden_filter_ids = fields.Many2many(
        "view.node.data",
        "search_panel_access_view_node_data_rel",
        "search_panel_access_id",
        "view_node_data_id",
        string="Hide Filters",
        domain=[("node_option", "=", "filter")],
        help="Specific filters to hide for this model.",
    )

    hidden_groupby_ids = fields.Many2many(
        "view.node.data",
        "search_panel_access_view_node_data_rel",
        "search_panel_access_id",
        "view_node_data_id",
        string="Hide Groups",
        domain=[("node_option", "=", "groupby")],
        help="Specific group-by options to hide for this model.",
    )

    hide_custom_filter = fields.Boolean(
        string="Hide Custom Filter",
        help="Disable custom filter creation for this model.",
    )
    hide_custom_group = fields.Boolean(
        string="Hide Custom Group",
        help="Disable custom group-by creation for this model.",
    )

    hide_unlink_in_favorites = fields.Boolean(
        string="Hide Delete in Favorites",
        help="Hide delete button in favorites for this model.",
    )

    _sql_constraints = [
        (
            "unique_search_panel_access_per_control",
            "unique(model_id, access_studio_id)",
            "Each model can have only one search panel access rule per simplified access control.",
        )
    ]

    @api.model
    def _store_node_data(self, model_id, node_option, attribute_name, attribute_string):
        """Store discovered node data in the view.node.data model."""
        domain = [
            ("attribute_name", "=", attribute_name),
            ("model_id", "=", model_id),
            ("node_option", "=", node_option),
        ]

        try:
            # Check if node data already exists
            if not self.env["view.node.data"].search(domain):
                # Create new node data record
                self.env["view.node.data"].create(
                    {
                        "model_id": model_id,
                        "node_option": node_option,
                        "attribute_name": attribute_name,
                        "attribute_string": attribute_string,
                    }
                )
            else:
                _logger.info(
                    "Node data already exists for model %s: %s",
                    self.model,
                    attribute_name,
                )
        except Exception as e:
            _logger.error("Error storing node data for model %s: %s", self.model, e)

    @api.model
    def _discover_filter_elements(self, model_id, filter_list):
        """Discover and store filter elements from search view XML."""
        for filter in filter_list:
            attribute_name = filter.get("name")
            attribute_string = filter.get("string")
            invisible = filter.get("invisible")
            context = filter.get("context")

            # Only store valid, visible filters without context
            if (
                attribute_name
                and attribute_string
                and invisible not in ["1", "1.0", "True"]
                and not context
            ):
                self._store_node_data(
                    model_id, "filter", attribute_name, attribute_string
                )

    @api.model
    def _discover_groupby_elements(self, model_id, object_groups):
        """Discover and store group-by elements from search view XML."""
        for object_group in object_groups:
            for group in object_group:
                attribute_name = group.get("name")
                attribute_string = group.get("string")
                context = group.get("context")
                # Only store valid group-by options with context
                if attribute_name and attribute_string and context:
                    self._store_node_data(
                        model_id, "groupby", attribute_name, attribute_string
                    )

    @api.onchange("model_id")
    def _discover_filters_groups(self):
        """Automatically discover filters and group-by options when model changes."""
        if not self.model_id:
            return

        model_id = self.model_id.id

        # Find search views for the selected model
        views = self.env["ir.ui.view"].search(
            [("model", "=", self.model), ("type", "=", "search")]
        )

        for view in views:
            try:
                # Get the search view definition
                res = (
                    self.env[self.model]
                    .sudo()
                    .get_view(view_id=view.id, view_type="search")
                )
            except Exception as e:
                _logger.error(
                    "Error discovering filters/groups for model %s: %s", self.model, e
                )
                return

            try:
                # Parse the XML view definition
                doc = etree.XML(res["arch"])
            except Exception as e:
                _logger.error("Error parsing XML for model %s: %s", self.model, e)
                return

            try:
                # Discover filter elements
                filter_list = doc.xpath("//filter")
                self._discover_filter_elements(model_id, filter_list)
            except Exception as e:
                _logger.error(
                    "Error discovering filters for model %s: %s", self.model, e
                )

            try:
                # Discover group-by elements
                object_groups = doc.xpath("//group")
                self._discover_groupby_elements(model_id, object_groups)
            except Exception as e:
                _logger.error(
                    "Error discovering groupbys for model %s: %s", self.model, e
                )

    @api.model
    @tools.ormcache('self.env.uid', 'model_name', 'self.env.company')
    def get_cached_search_panel_access(self, model_name):
        """Get cached search panel access rules for a model."""
        domain = [
            ("model", "=", model_name),
            ("access_studio_id.active", "=", True),
            "|",
            ("access_studio_id.apply_without_companies", "=", True),
            ("access_studio_id.company_ids", "in", [self.env.company.id]),
            ("access_studio_id.user_ids", "in", [self.env.user.id]),
        ]
        rules = self.sudo().search(domain)

        # Precompute normalized technical names for client usage
        hidden_filter_names = [
            name for name in rules.mapped("hidden_filter_ids.attribute_name") if name
        ]
        hidden_groupby_names = [
            name for name in rules.mapped("hidden_groupby_ids.attribute_name") if name
        ]

        global_access = self.env["access.studio"].get_global_access_studio_rules()
        return {
            'hide_search_panel': global_access.get("hide_search_panel") or any(rules.mapped("hide_search_panel")),
            'hide_custom_filter': global_access.get("hide_custom_filter") or any(rules.mapped("hide_custom_filter")),
            'hide_custom_group': global_access.get("hide_custom_group") or any(rules.mapped("hide_custom_group")),
            'hide_unlink_in_favorites': global_access.get("hide_unlink_in_favorites") or any(rules.mapped("hide_unlink_in_favorites")),
            'hidden_filter_ids': rules.mapped("hidden_filter_ids"),
            'hidden_groupby_ids': rules.mapped("hidden_groupby_ids"),
            # Flattened, deduplicated technical names for high-performance OWL usage
            'hideFilters': list(dict.fromkeys(hidden_filter_names)),
            'hideGroups': list(dict.fromkeys(hidden_groupby_names)),
        }