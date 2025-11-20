from urllib.parse import urlencode

from odoo import http
from odoo.addons.web.controllers.home import Home, ensure_db
from odoo.http import request


class AccessStudioHome(Home):
    """Override Home controller to block debug mode when disable_debug rule applies."""

    # Re-declare routes to ensure our override is used
    @http.route(
        ["/web", "/odoo", "/odoo/<path:subpath>", "/scoped_app/<path:subpath>"],
        type="http",
        auth="none",
        readonly=Home._web_client_readonly,
    )
    def web_client(self, s_action=None, **kw):
        """Intercept debug query param and redirect if the user is not allowed."""
        ensure_db()

        # Skip debug check if no user is logged in
        if not request.session.uid:
            return super().web_client(s_action=s_action, **kw)

        # Restore environment with correct user
        request.update_env(user=request.session.uid)

        # Check if debug mode is requested
        debug_requested = "debug" in kw or "debug" in request.httprequest.args
        if debug_requested:
            user = request.env.user
            domain = [
                ("user_ids", "in", [user.id]),
                "|",
                ("apply_without_companies", "=", True),
                ("company_ids", "in", [user.company_id.id]),
                ("disable_debug", "=", True),
            ]
            rule = (
                request.env["access.studio"].sudo().search(domain, limit=1)
            )
            if rule:
                # Clear debug flag and redirect without debug parameter
                request.session.debug = ""
                args = dict(request.httprequest.args)
                args.pop("debug", None)
                url = request.httprequest.path
                if args:
                    url += "?" + urlencode(args)
                return request.redirect(url)

        # Delegate to standard behavior if debug is allowed
        return super().web_client(s_action=s_action, **kw)
