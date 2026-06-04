from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError

class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    is_contract_expired = fields.Boolean(
        string="Expired Contract",
        compute="_compute_is_contract_expired",
        store=True,
    )
    # budget_amount = fields.Monetary(
    #     string="Presupuesto",
    #     currency_field="currency_id",
    #     help="Monto máximo presupuestado para este contrato.",
    #     default=0.0,
    # )

    # budget_spent = fields.Monetary(
    #     string="Presupuesto gastado",
    #     currency_field="currency_id",
    #     compute="_compute_budget_spent",
    #     help="Suma de los totales de las cotizaciones/órdenes asociadas (excepto canceladas).",
    #     store=False,  # dinámico para reflejar siempre el gasto real
    # )

    # @api.depends("state")  # disparador mínimo; el cálculo consulta purchase.order
    # def _compute_budget_spent(self):
    #     """Suma amount_total de las purchase.order enlazadas (state != cancel)."""
    #     PurchaseOrder = self.env["purchase.order"].sudo()
    #     for rec in self:
    #         if not rec.id:
    #             rec.budget_spent = 0.0
    #             continue
    #         total = 0.0
    #         # Trae todas las cotizaciones/órdenes del contrato, excepto canceladas
    #         orders = PurchaseOrder.search([
    #             ("requisition_id", "=", rec.id),
    #             ("state", "!=", "cancel"),
    #         ])
    #         # Sumamos amount_total (ya incluye impuestos)
    #         total = sum(o.amount_total for o in orders)
    #         rec.budget_spent = total
    #         # rec._check_budget_not_exceeded()

    # @api.constrains("budget_amount")
    # def _check_budget_not_exceeded(self):
    #     """Evita que el presupuesto quede por debajo del gasto acumulado."""
    #     for rec in self:
    #         # Recalcula en caliente
    #         # rec._compute_budget_spent()
    #         if rec.budget_amount and rec.budget_spent > rec.budget_amount:
    #             raise ValidationError(
    #                 _("El presupuesto (%(b).2f) no puede ser menor que el gastado (%(s).2f).")
    #                 % {"b": rec.budget_amount, "s": rec.budget_spent}
    #             )

    @api.depends("date_end")
    def _compute_is_contract_expired(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_contract_expired = bool(rec.date_end and rec.date_end < today)

    def action_open_requisition_orders_safe(self):
        self.ensure_one()
        action = self.env.ref("purchase_requisition.action_purchase_requisition_list").read()[0]

        raw_ctx = action.get("context")
        if isinstance(raw_ctx, str):
            try:
                ctx = safe_eval(raw_ctx) or {}
            except Exception:
                ctx = {}
        elif isinstance(raw_ctx, dict):
            ctx = dict(raw_ctx)
        else:
            ctx = {}

        ctx.update({
            "default_requisition_id": self.id,
            "default_currency_id": self.currency_id.id,
        })
        action["context"] = ctx

        raw_domain = action.get("domain")
        if isinstance(raw_domain, str):
            try:
                dom = safe_eval(raw_domain) or []
            except Exception:
                dom = []
        elif isinstance(raw_domain, (list, tuple)):
            dom = list(raw_domain)
        else:
            dom = []
        dom.append(("requisition_id", "=", self.id))
        action["domain"] = dom

        if self.is_contract_expired or self.state in ["done", "cancel"]:
            action["context"]["create"] = False

        return action