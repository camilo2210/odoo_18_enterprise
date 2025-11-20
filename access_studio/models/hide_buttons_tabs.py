import logging

from odoo import _, api, fields, models, tools

try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

from .access_studio import MODELS

_logger = logging.getLogger(__name__)


class HideButtonsTabs(models.Model):
    """UI element visibility control for buttons and tabs in form views."""

    _name = "hide.buttons.tabs"
    _description = "Manage Button & Tab Visibility"

    # Relationship Fields

    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        domain=[("model", "not in", MODELS)],
        help="Target model for button and tab visibility controls.",
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

    # UI Element Controls

    hidden_button_ids = fields.Many2many(
        "view.node.data",
        "hide_buttons_view_node_data_rel",
        "hide_buttons_tabs_id",
        "view_node_data_id",
        string="Hidden Buttons",
        domain=[("node_option", "=", "button")],
        help="Buttons to hide for this model.",
    )

    hidden_tab_ids = fields.Many2many(
        "view.node.data",
        "hide_tabs_view_node_data_rel",
        "hide_buttons_tabs_id",
        "view_node_data_id",
        string="Hidden Tabs",
        domain=[("node_option", "=", "page")],
        help="Tabs to hide for this model.",
    )

    # Links are not managed; only buttons and tabs are supported

    _sql_constraints = [
        (
            "unique_button_tabs_per_control",
            "unique(model_id, access_studio_id)",
            "A model can have only one button & tab visibility rule per simplified access control.",
        )
    ]

    @api.model
    def _store_node_data(
        self,
        model_id,
        node_option,
        attribute_name,
        attribute_string,
        button_type=None,
        is_smart_button=False,
        view_name=None,
    ):
        """Store discovered UI element data in the view.node.data model."""
        view_node_data_obj = self.env["view.node.data"]
        domain = [
            ("model_id", "=", model_id),
            ("node_option", "=", node_option),
        ]

        # Build domain based on node type
        if node_option == "page":
            # For pages, use string as primary identifier
            if attribute_string:
                domain.append(("attribute_string", "=", attribute_string))
            if attribute_name:
                domain.append(("attribute_name", "=", attribute_name))
        else:
            # For buttons, require both name and string
            domain.extend(
                [
                    ("attribute_name", "=", attribute_name),
                    ("attribute_string", "=", attribute_string),
                ]
            )

        # Add button-specific filters
        if button_type:
            domain.append(("button_type", "=", button_type))
        if is_smart_button:
            domain.append(("is_smart_button", "=", is_smart_button))
        if view_name:
            domain.append(("view_name", "=", view_name))

        try:
            # Check if node data already exists
            exists = view_node_data_obj.search(domain)
            if not exists:
                # Create new node data record
                vals = {
                    "model_id": model_id,
                    "node_option": node_option,
                    "attribute_name": attribute_name,
                    "attribute_string": attribute_string,
                    "button_type": button_type,
                    "is_smart_button": is_smart_button,
                }
                if view_name:
                    vals["view_name"] = view_name
                view_node_data_obj.create(vals)
        except Exception as e:
            _logger.warning("Error storing node data: %s", e)

    # Smart Button Processing Methods

    def _get_smart_button_string(self, btn):
        """Extract smart button attributes from complex button structures."""

        def _get_span_text(span_list):
            """Extract text content from a list of span elements."""
            text = ""
            for sp in span_list:
                if sp.text:
                    text = text + " " + sp.text
            return text.strip()

        # Try to get basic attributes first
        attribute_name = btn.get("name", "")
        attribute_string = btn.get("string", "")

        # Look for field elements that might contain the attributes
        field_list = btn.findall("field")
        if not attribute_name and field_list:
            attribute_name = field_list[0].get("name", "") or field_list[0].get(
                "string", ""
            )

        if not attribute_string and field_list:
            attribute_string = field_list[0].get("string", "") or field_list[0].get(
                "name", ""
            )

        # Try to extract string from span elements
        if not attribute_string:
            span_list = btn.findall("span")
            if span_list:
                attribute_string = _get_span_text(span_list)
            else:
                # Look for spans inside div elements
                div_list = btn.findall("div")
                if div_list:
                    span_list = div_list[0].findall("span")
                    if span_list:
                        attribute_string = _get_span_text(span_list)

        # Fallback to button text content
        if not attribute_string and btn.text and btn.text.strip():
            attribute_string = btn.text.strip()

        return attribute_name, attribute_string

    def _get_button_label(self, btn):
        """Robustly extract a label for non-smart header buttons."""
        label = btn.get("string") or ""
        if label:
            return label
        # Try spans
        spans = btn.findall(".//span")
        text = " ".join([s.text or "" for s in spans]).strip()
        if text:
            return text
        # Fallback to button text
        return (btn.text or "").strip()

    @api.model
    def _discover_form_elements(self, model_id, doc):
        """Discover buttons and tabs from form view XML."""
        # Discover regular header buttons (exclude smart button box)
        header_buttons = doc.xpath("//form//button[( @type='object' or @type='action') and not(ancestor::div[contains(@class,'oe_button_box')])]"
        )
        for btn in header_buttons:
            attribute_name = btn.get("name")
            if not attribute_name:
                continue
            attribute_string = self._get_button_label(btn) or attribute_name
            btype = btn.get("type")
            if btype in ("object", "action"):
                self._store_node_data(
                    model_id, "button", attribute_name, attribute_string, btype, False, "Form Header"
                )

        # Discover smart buttons in button box
        smart_button_div = doc.xpath("//div[@class='oe_button_box']")
        if smart_button_div:
            # Convert to string and back to XML for proper xpath handling
            smart_button_div = etree.tostring(smart_button_div[0])
            smart_button_div = etree.XML(smart_button_div)

            # Discover smart object buttons
            smart_object_buttons = smart_button_div.xpath("//button[@type='object']")
            for btn in smart_object_buttons:
                attribute_name, attribute_string = self._get_smart_button_string(btn)
                if attribute_name and attribute_string:
                    self._store_node_data(
                        model_id,
                        "button",
                        attribute_name,
                        attribute_string,
                        "object",
                        True,
                        "Form Smart",
                    )

            # Discover smart action buttons
            smart_action_buttons = smart_button_div.xpath("//button[@type='action']")
            for btn in smart_action_buttons:
                attribute_name, attribute_string = self._get_smart_button_string(btn)
                if attribute_name and attribute_string:
                    self._store_node_data(
                        model_id,
                        "button",
                        attribute_name,
                        attribute_string,
                        "action",
                        True,
                        "Form Smart",
                    )

        # Discover tabs/pages
        pages = doc.xpath("//page")
        for page in pages:
            attribute_name = page.get("name")
            attribute_string = page.get("string")
            if attribute_string:
                self._store_node_data(
                    model_id, "page", attribute_name, attribute_string, None, False, "Form"
                )

        # Discover links in form (rare in modern views, but supported)
        form_links = doc.xpath("//form//a[@type='action' or @type='object']")
        for a in form_links:
            name = a.get("name")
            label = a.get("string") or (a.text or "").strip()
            ltype = a.get("type")  # 'action' or 'object'
            if name and label:
                self._store_node_data(model_id, "link", name, label, ltype, False, "Form")

    @api.model
    def _discover_list_elements(self, model_id, doc):
        """Discover header and row buttons/links from list (tree) views."""
        # Header buttons under <list>/<tree><header>...</header>
        header_buttons = doc.xpath("//list/header//button | //tree/header//button")
        for btn in header_buttons:
            name = btn.get("name")
            label = btn.get("string")
            btype = btn.get("type")  # 'object' or 'action'
            if name and label and btype in ("object", "action"):
                self._store_node_data(model_id, "button", name, label, btype, False, "List Header")

        # Row-level buttons inside the list/tree, excluding header
        row_buttons = doc.xpath("(//list//button | //tree//button)[not(ancestor::header)]")
        for btn in row_buttons:
            name = btn.get("name")
            label = btn.get("string")
            btype = btn.get("type")
            if name and label and btype in ("object", "action"):
                self._store_node_data(model_id, "button", name, label, btype, False, "List Row")

        # Links not managed

    @api.onchange("model_id")
    def _discover_button_tabs_links(self):
        """Automatically discover buttons and tabs when model changes."""
        if not self.model_id or not self.model:
            return

        model_id = self.model_id.id

        # Find root, active form views for the selected model
        views = self.env["ir.ui.view"].sudo().search([
            ("model", "=", self.model),
            ("inherit_id", "=", False),
            ("active", "=", True),
            ("type", "=", "form"),
        ])

        for view in views:
            try:
                # Get the combined architecture including inherited views (fast, server-side)
                arch = view.get_combined_arch()
                doc = etree.fromstring(arch)
            except Exception as e:
                _logger.error("Error combining/parsing XML for model %s (view %s): %s", self.model, view.xml_id or view.id, e)
                continue

            # Discover form elements from this combined arch
            self._discover_form_elements(model_id, doc)

        # Also discover list view elements (header and row buttons/links)
        list_views = self.env["ir.ui.view"].sudo().search([
            ("model", "=", self.model),
            ("inherit_id", "=", False),
            ("active", "=", True),
            ("type", "=", "list"),
        ])
        for view in list_views:
            try:
                arch = view.get_combined_arch()
                doc = etree.fromstring(arch)
            except Exception as e:
                _logger.error("Error combining/parsing XML for model %s (list view %s): %s", self.model, view.xml_id or view.id, e)
                continue
            self._discover_list_elements(model_id, doc)


    @api.model
    @tools.ormcache('self.env.uid', 'model_name', 'self.env.company')
    def get_cached_hidden_nodes(self, model_name):
        domain = [
            ('model', '=', model_name),
            ('access_studio_id.active', '=', True),
            '|',
            ('access_studio_id.apply_without_companies', '=', True),
            ('access_studio_id.company_ids', 'in', [self.env.company.id]),
            ('access_studio_id.user_ids', 'in', [self.env.user.id]),
        ]
        rules = self.sudo().search(domain)

        result = {
            'form': {
                'buttons': {'object': set(), 'action': set()},
                'tabs': set(),
            },
            'list header': {
                'buttons': {'object': set(), 'action': set()},
            },
            'list row': {
                'buttons': {'object': set(), 'action': set()},
            },
        }

        def _vn(rec):
            return (rec.view_name or '').lower()

        # Buttons
        for r in rules.mapped('hidden_button_ids'):
            name = r.attribute_name
            if not name:
                continue
            vt = (r.button_type or '').lower()  # 'object' or 'action'
            if vt not in ('object', 'action'):
                continue
            vn = _vn(r)
            if 'form' in vn:
                result['form']['buttons'][vt].add(name)
            elif 'list' in vn:
                result[vn]['buttons'][vt].add(name)

        # Tabs (form only)
        for r in rules.mapped('hidden_tab_ids'):
            name = r.attribute_name or ''
            label = r.attribute_string or ''
            if not (name or label):
                continue
            if 'form' in _vn(r):
                if name:
                    result['form']['tabs'].add(name)
        return result
