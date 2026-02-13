from odoo import api, fields, models, tools

from .access_studio import MODELS


class ModelAccess(models.Model):
    _name = "model.access"
    _inherit = "access.studio.cache.mixin"
    _description = "Model Access Control"

    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        domain=[("model", "not in", MODELS)],
        help="Target model for access control restrictions.",
    )
    model = fields.Char(
        string="Model Name",
        related="model_id.model",
        store=True,
        help="Technical name of the target model.",
    )
    access_studio_id = fields.Many2one(
        "access.studio",
        string="Access Rule Set",
        ondelete="cascade",
        help="Parent access control rule set.",
    )

    hide_report_ids = fields.Many2many(
        "action.data",
        "model_access_hide_report_rel",
        "model_access_id",
        "report_id",
        string="Hide Reports",
        help="Hiding reports ensures that sensitive or non-essential business "
             "data is not exposed to users who do not need it, helping maintain "
             "confidentiality and simplify the interface for daily operations.",
    )

    hide_action_ids = fields.Many2many(
        "action.data",
        "model_access_hide_action_rel",
        "model_access_id",
        "action_id",
        string="Hide Actions",
        help="By hiding actions from the drop-down menu, businesses can prevent "
             "users from performing operations that may not be relevant to their "
             "role, reducing errors and enforcing process discipline.",
    )

    hide_view_type_ids = fields.Many2many(
        "ir.ui.view.type",
        "model_access_hide_view_type_rel",
        "model_access_id",
        "view_type_id",
        string="Hide Views",
        help="Hiding specific views allows the organization to control which "
             "layouts and information a user can see, ensuring employees focus "
             "only on the data necessary for their responsibilities.",
    )

    hide_read = fields.Boolean(
        string="Hide Read",
        help="Hide read access ensures users cannot access records outside "
             "their responsibility, helping maintain data privacy, compliance, and "
             "reducing accidental exposure of sensitive business information.",
    )

    hide_create = fields.Boolean(
        string="Hide Create",
        help="Hide create access controls which users can add new records, "
             "preventing unnecessary or unauthorized data entries that could affect "
             "business processes or reporting accuracy.",
    )

    hide_edit = fields.Boolean(
        string="Hide Edit",
        help="Hide edit permissions prevents users from modifying critical "
             "records, preserving data integrity and ensuring that changes are made "
             "only by authorized personnel.",
    )

    hide_unlink = fields.Boolean(
        string="Hide Delete",
        help="Hide delete access safeguards important business records from "
             "being removed accidentally or intentionally, protecting historical "
             "data and compliance requirements.",
    )

    hide_duplicate = fields.Boolean(
        string="Hide Duplicate",
        help="Hiding the duplicate option ensures users follow proper data entry "
             "procedures, preventing accidental duplication of records that could "
             "lead to reporting inconsistencies or operational confusion.",
    )

    hide_archive = fields.Boolean(
        string="Hide Archive",
        help="Hiding archive buttons controls which users can move records to "
             "inactive status, ensuring that only authorized personnel can manage "
             "the lifecycle of business records.",
    )

    hide_unarchive = fields.Boolean(
        string="Hide Unarchive",
        help="Hiding unarchive functionality ensures that archived records remain "
             "inactive unless specifically restored by authorized users, preserving "
             "process consistency.",
    )

    hide_import = fields.Boolean(
        string="Hide Import Records",
        help="Hiding the import functionality restricts users from uploading bulk "
             "data that could bypass validation rules, ensuring data quality and "
             "process compliance.",
    )

    hide_export = fields.Boolean(
        string="Hide Export All",
        help="Hiding export capabilities prevents unauthorized extraction of "
             "business data, protecting sensitive information and maintaining "
             "compliance with internal or regulatory policies.",
    )

    hide_add_property = fields.Boolean(
        string="Hide Add Property",
        help="Hiding the ability to add custom properties ensures that users do "
             "not create additional fields that may complicate data models or "
             "reporting, maintaining standardization and clarity.",
    )

    _sql_constraints = [
        (
            "unique_model_access",
            "unique(model_id, access_studio_id)",
            "A model can have only one access control rule per simplified access control.",
        )
    ]

    @api.model
    @tools.ormcache('self.env.uid', 'model_name', 'self.env.company')
    def get_cached_model_access(self, model_name):
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
        rules = self.env["model.access"].sudo().search(domain)

        global_access = self.env["access.studio"].get_global_access_studio_rules()

        hide_create = global_access.get("hide_create") or any(rules.mapped("hide_create"))
        hide_edit = global_access.get("hide_edit") or any(rules.mapped("hide_edit"))
        hide_unlink = global_access.get("hide_unlink") or any(rules.mapped("hide_unlink"))
        hide_read = global_access.get("hide_read") or any(rules.mapped("hide_read"))
        hide_duplicate = hide_create or global_access.get("hide_duplicate") or any(rules.mapped("hide_duplicate"))
        hide_archive = hide_edit or global_access.get("hide_archive") or any(rules.mapped("hide_archive"))
        hide_unarchive = hide_edit or global_access.get("hide_unarchive") or any(rules.mapped("hide_unarchive"))
        hide_import = hide_create or hide_edit or global_access.get("hide_import") or any(rules.mapped("hide_import"))
        hide_export = hide_read or global_access.get("hide_export") or any(rules.mapped("hide_export"))
        hide_add_property = global_access.get("hide_add_property") or any(rules.mapped("hide_add_property"))

        return {
            'restricted_actions_ids': rules.mapped("hide_action_ids.action_id").ids,
            'restricted_reports_ids': rules.mapped("hide_report_ids.action_id").ids,
            'restricted_views_technames': rules.mapped("hide_view_type_ids").mapped("techname"),
            'hide_read': hide_read,
            'hide_edit': hide_edit,
            'hide_create': hide_create,
            'hide_unlink': hide_unlink,
            'hide_duplicate': hide_duplicate,
            'hide_archive': hide_archive,
            'hide_unarchive': hide_unarchive,
            'hide_import': hide_import,
            'hide_export': hide_export,
            'hide_add_property': hide_add_property,
        }