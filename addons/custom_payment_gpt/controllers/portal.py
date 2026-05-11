from odoo import http
from odoo.http import request


class PortalCustomPaymentController(http.Controller):

    @http.route(
        ["/my/invoices/<int:invoice_id>/custom_pay"],
        type="http",
        auth="public",
        website=True,
        csrf=True,
    )
    def portal_custom_pay(self, invoice_id, custom_amount=None, **kwargs):

        invoice = request.env["account.move"].sudo().browse(invoice_id)

        if not invoice.exists():
            return request.not_found()

        if invoice.move_type != "out_invoice":
            return request.redirect("/my")

        if invoice.state != "posted":
            return request.redirect(invoice.get_portal_url())

        if invoice.payment_state == "paid":
            return request.redirect(invoice.get_portal_url())

        try:
            amount = float(custom_amount or 0)
        except Exception:
            amount = 0

        if amount <= 0:
            return request.redirect(invoice.get_portal_url())

        if amount > invoice.amount_residual:
            amount = invoice.amount_residual

        request.session["custom_payment_amount"] = amount

        return request.redirect(
            "/payment/pay"
            "?reference=%s"
            "&amount=%s"
            "&invoice_id=%s"
            % (
                invoice.name,
                amount,
                invoice.id,
            )
        )