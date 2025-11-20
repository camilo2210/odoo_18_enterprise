import logging

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

MODELS = [
    "access.studio",
    "domain.access",
    "field.access",
    "field.conditional.access",
    "hide.buttons.tabs",
    "chatter.access",
    "action.data",
    "menu.data",
    "model.access",
    "user.group",
    "ir.ui.view.type",
    "view.node.data",
    "search.panel.access",
]
MENUS = [
    "access_studio.menu_access_studio_root",
    "access_studio.menu_user_group",
]


class AccessStudio(models.Model):
    """Central model for managing comprehensive user access controls and restrictions."""

    _name = "access.studio"
    _inherit = "access.studio.cache.mixin"
    _description = "Simplified Access Control"


    @api.model
    def _get_access_studio_module_menus(self):
        menu_ids = []
        for menu in MENUS:
            menu_id = self.env.ref(menu, raise_if_not_found=False)
            if menu_id:
                menu_ids.append(menu_id.id)
        return menu_ids

    # Basic Information Fields

    name = fields.Char(
        string="Rule Name",
        required=True,
        index=True,
        help="Unique identifier for this access rule configuration.",
    )
    active = fields.Boolean(
        string="Active", default=True, help="Enable/disable this access rule."
    )

    # User & Group Assignment

    apply_by_user_groups = fields.Boolean(
        string="Apply by User Groups",
        help="Apply rules based on user groups instead of individual users.",
    )
    user_group_ids = fields.Many2many(
        "user.group",
        "access_studio_user_group_rel",
        "access_studio_id",
        "user_group_id",
        string="User Groups",
        help="User groups affected by this access rule.",
    )
    user_ids = fields.Many2many(
        "res.users",
        "access_studio_users_rel",
        "access_studio_id",
        "user_id",
        string="Users",
        help="Individual users affected by this access rule.",
    )
    default_internal_user = fields.Boolean(
        string="Default for Internal User",
        help="Auto-apply this rule to new internal users.",
    )
    default_portal_user = fields.Boolean(
        string="Default for Portal User",
        help="Auto-apply this rule to new portal users.",
    )

    # Company & Multi-Company Settings

    apply_without_companies = fields.Boolean(
        string="Apply Without Companies",
        help="Apply rule regardless of user's company context.",
    )
    company_ids = fields.Many2many(
        "res.company",
        "access_studio_company_rel",
        "access_studio_id",
        "company_id",
        string="Companies",
        help="Companies where this access rule applies.",
    )

    # System-Level Controls

    readonly = fields.Boolean(
        string="Readonly Mode", help="Prevent users from editing any records."
    )
    disable_debug = fields.Boolean(
        string="Disable Debug Mode",
        help="Prevent access to debug mode and developer tools.",
    )
    disable_login = fields.Boolean(
        string="Disable User Login",
        help="Block affected users from logging into the system.",
    )

    # Menu & Navigation Controls

    hide_menu_ids = fields.Many2many(
        "menu.data",
        "access_studio_hide_menu_rel",
        "access_studio_id",
        "menu_data_id",
        string="Menus to Hide",
        help="Menus to hide from affected users.",
    )

    # Chatter Controls

    hide_chatter = fields.Boolean(
        string="Hide Chatter", help="Hide chatter section across all records."
    )
    hide_send_message = fields.Boolean(
        string="Hide 'Send Message'", help="Hide send message option in chatter."
    )
    hide_log_notes = fields.Boolean(
        string="Hide 'Log Note'", help="Hide log note option in chatter."
    )
    hide_schedule_activity = fields.Boolean(
        string="Hide 'Activities'", help="Hide schedule activity option in chatter."
    )
    hide_search_message_icon = fields.Boolean(
        string="Hide Search Message Icon", help="Hide search icon in chatter."
    )
    hide_attachment_icon = fields.Boolean(
        string="Hide Attachment Icon",
        help="Hide attachment (paperclip) icon in chatter.",
    )
    hide_followers_icon = fields.Boolean(
        string="Hide Followers Icon", help="Hide followers (user) icon in chatter."
    )
    hide_follow_unfollow = fields.Boolean(
        string="Hide Follow/Unfollow Button",
        help="Hide follow/unfollow button in chatter.",
    )

    # Import & Export Controls
    hide_import = fields.Boolean(
        string="Hide Import Records",
        help="Hiding the import functionality restricts users from uploading bulk data that could bypass validation rules, ensuring data quality and process compliance.",
    )

    hide_export = fields.Boolean(
        string="Hide Export All",
        help="Hiding export capabilities prevents unauthorized extraction of business data, protecting sensitive information and maintaining compliance with internal or regulatory policies.",
    )

    # Search & Filter Controls
    hide_search_panel = fields.Boolean(
        string="Hide Search Panel", help="Hide search panel completely."
    )
    hide_custom_filter = fields.Boolean(
        string="Hide Custom Filter", help="Prevent creation of custom filters."
    )
    hide_custom_group = fields.Boolean(
        string="Hide Custom Group", help="Prevent custom grouping of records."
    )
    hide_unlink_in_favorites = fields.Boolean(
        string="Hide Delete in Favorites", help="Hide delete button in favorites."
    )

    # Record Operation Controls
    hide_create = fields.Boolean(
        string="Hide Create",
        help="Hide create access controls which users can add new records, preventing unnecessary or unauthorized data entries that could affect business processes or reporting accuracy.",
    )

    hide_edit = fields.Boolean(
        string="Hide Edit",
        help="Hide edit permissions prevents users from modifying critical records, preserving data integrity and ensuring that changes are made only by authorized personnel.",
    )

    hide_unlink = fields.Boolean(
        string="Hide Delete",
        help="Hide delete access safeguards important business records from being removed accidentally or intentionally, protecting historical data and compliance requirements.",
    )

    hide_duplicate = fields.Boolean(
        string="Hide Duplicate",
        help="Hiding the duplicate option ensures users follow proper data entry procedures, preventing accidental duplication of records that could lead to reporting inconsistencies or operational confusion.",
    )

    hide_archive = fields.Boolean(
        string="Hide Archive",
        help="Hiding archive buttons controls which users can move records to inactive status, ensuring that only authorized personnel can manage the lifecycle of business records.",
    )

    hide_unarchive = fields.Boolean(
        string="Hide Unarchive",
        help="Hiding unarchive functionality ensures that archived records remain inactive unless specifically restored by authorized users, preserving process consistency.",
    )

    # Advanced Feature Controls
    hide_add_property = fields.Boolean(
        string="Hide Add Property",
        help="Hiding the ability to add custom properties ensures that users do not create additional fields that may complicate data models or reporting, maintaining standardization and clarity.",
    )

    # Related Models - Granular Access Control

    model_access_ids = fields.One2many(
        "model.access",
        "access_studio_id",
        string="Model Access Rules",
        help="Model-specific access restrictions.",
    )

    field_access_ids = fields.One2many(
        "field.access",
        "access_studio_id",
        string="Field Access Rules",
        help="Field-level access control rules.",
    )

    field_conditional_access_ids = fields.One2many(
        "field.conditional.access",
        "access_studio_id",
        string="Field Conditional Access",
        help="Conditional field access based on record state.",
    )

    domain_access_ids = fields.One2many(
        "domain.access",
        "access_studio_id",
        string="Domain Access Rules",
        help="Domain-based record filtering rules.",
    )

    hide_buttons_tabs_ids = fields.One2many(
        "hide.buttons.tabs",
        "access_studio_id",
        string="Hide Buttons & Tabs",
        help="Specific buttons or tabs to hide.",
    )

    search_panel_access_ids = fields.One2many(
        "search.panel.access",
        "access_studio_id",
        string="Search Panel Access",
        help="Search panel filter and grouping restrictions.",
    )

    chatter_access_ids = fields.One2many(
        "chatter.access",
        "access_studio_id",
        string="Model-Specific Chatter Settings",
        help="Model-specific chatter visibility controls.",
    )

    # Constraints
    @api.constrains("user_ids")
    def _check_superuser_odoobot_restrictions(self):
        """Prevent restrictive access controls on Superuser or OdooBot for business continuity."""
        OdooBot = self.env.ref("base.user_root", raise_if_not_found=False)
        superuser = self.env.ref("base.user_admin", raise_if_not_found=False)

        for rec in self:
            user_ids = rec.user_ids.ids
            if not user_ids:
                continue

            if superuser.id in user_ids or OdooBot.id in user_ids:
                raise ValidationError(
                    _(
                        "You cannot apply restrictive access controls to the Superuser or OdooBot accounts. "
                        "These users are essential for system administration and automated operations, "
                        "and must always retain unrestricted access to ensure business continuity."
                    )
                )

    # Onchange Methods

    @api.onchange("apply_without_companies")
    def _onchange_apply_without_company(self):
        """Handle company assignment based on 'Apply Without Company' setting."""
        if not self.apply_without_companies:
            # Assign current company when not applying without company
            self.company_ids = [(6, 0, [self.env.company.id])]
        else:
            # Clear companies when applying without company
            self.company_ids = [(6, 0, [])]

    @api.onchange("apply_by_user_groups", "user_group_ids")
    def _onchange_user_group_ids(self):
        """Synchronize user assignments based on user group selection."""
        if self.apply_by_user_groups:
            # Get all users from selected groups
            user_ids = self.user_group_ids.mapped("user_ids").ids
            self.user_ids = [(6, 0, user_ids)]
        else:
            # Clear users when not using group-based access
            self.user_ids = [(6, 0, [])]

    @api.model
    @tools.ormcache('self.env.uid', 'self.env.company')
    def get_cached_menu_ids_to_restrict(self):
        """
        Get cached access control settings for the given company.
        """
        domain = [
            ("active", "=", True),
            "|",
            ("apply_without_companies", "=", True),
            ("company_ids", "in", [self.env.company.id]),
            ("user_ids", "in", [self.env.user.id]),
        ]
        rules = self.env["access.studio"].sudo().search(domain)
        return rules.mapped("hide_menu_ids.menu_id")
    
    @api.model
    @tools.ormcache('self.env.uid', 'self.env.company')
    def get_global_access_studio_rules(self):

        domain = [
            ("active", "=", True),
            ("user_ids", "in", [self.env.user.id]),
            "|",
            ("apply_without_companies", "=", True),
            ("company_ids", "in", [self.env.company.id]),
        ]
        rules = self.env["access.studio"].sudo().search(domain)
        readonly = any(rules.mapped("readonly"))

        # combined CRUD rules
        hide_create = readonly or any(rules.mapped("hide_create"))
        hide_edit = readonly or any(rules.mapped("hide_edit"))
        hide_unlink = readonly or any(rules.mapped("hide_unlink"))
        hide_duplicate = hide_create or any(rules.mapped("hide_duplicate"))
        hide_import = hide_create or hide_edit or any(rules.mapped("hide_import"))
        hide_export = any(rules.mapped("hide_export"))
        hide_archive = hide_edit or any(rules.mapped("hide_archive"))
        hide_unarchive = hide_edit or any(rules.mapped("hide_unarchive"))
        hide_add_property = any(rules.mapped("hide_add_property"))

        return {
            # model.access
            'hide_create': hide_create,
            'hide_edit': hide_edit,
            'hide_unlink': hide_unlink,
            'hide_duplicate': hide_duplicate,
            'hide_import': hide_import,
            'hide_export': hide_export,
            'hide_archive': hide_archive,
            'hide_unarchive': hide_unarchive,
            'hide_add_property': hide_add_property,
            # chatter.access
            'hide_chatter': any(rules.mapped("hide_chatter")),
            'hide_send_message': any(rules.mapped("hide_send_message")),
            'hide_log_notes': any(rules.mapped("hide_log_notes")),
            'hide_schedule_activity': any(rules.mapped("hide_schedule_activity")),
            'hide_search_message_icon': any(rules.mapped("hide_search_message_icon")),
            'hide_attachment_icon': any(rules.mapped("hide_attachment_icon")),
            'hide_followers_icon': any(rules.mapped("hide_followers_icon")),
            'hide_follow_unfollow': any(rules.mapped("hide_follow_unfollow")),
            # search.panel.access
            'hide_search_panel': any(rules.mapped("hide_search_panel")),
            'hide_custom_filter': any(rules.mapped("hide_custom_filter")),
            'hide_custom_group': any(rules.mapped("hide_custom_group")),
            'hide_unlink_in_favorites': any(rules.mapped("hide_unlink_in_favorites")),
            # access.studio
            'hide_menu_ids': any(rules.mapped("hide_menu_ids.menu_id")),
            'readonly': any(rules.mapped("readonly")),
            'disable_debug': any(rules.mapped("disable_debug")),
            'disable_login': any(rules.mapped("disable_login")),
            'default_internal_user': any(rules.mapped("default_internal_user")),
            'default_portal_user': any(rules.mapped("default_portal_user")),
        }