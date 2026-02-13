from odoo import _, http
from odoo.addons.web.controllers.action import Action
from odoo.exceptions import UserError
from odoo.http import request


class AccessStudioAction(Action):
    """Override Action controller to enforce view type restrictions."""

    @http.route("/web/action/load", type="json", auth="user")
    def load(self, action_id, context=None):
        """Override action load to filter restricted view types."""
        res = super(AccessStudioAction, self).load(
            action_id, context=context
        )

        user = request.env.user

        # Get current company IDs from cookies or user's company
        cids = request.httprequest.cookies.get("cids")
        if cids:
            cids = list(map(int, cids.split("-")))
        else:
            cids = [user.company_id.id]

        rules = request.env["model.access"].sudo().get_cached_model_access(res.get("res_model"))
        restricted_views_technames = rules['restricted_views_technames']

        if restricted_views_technames:
            # Filter out restricted view types
            original_views = res.get("views", [])
            filtered_views = []

            for view_id, view_type in original_views:
                if view_type not in restricted_views_technames:
                    filtered_views.append([view_id, view_type])

            res["views"] = filtered_views

            # Raise error if no views are available after filtering
            if not filtered_views:
                raise UserError(
                    _(
                        "You don't have permission to access any views for this model. Please contact your administrator."
                    )
                )

        return res
