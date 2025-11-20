# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class KpiProvider(models.AbstractModel):
    _inherit = 'kpi.provider'

    @api.model
    def get_documents_kpi_summary(self):
        inbox_tag = self.env.ref('documents.documents_tag_inbox', raise_if_not_found=False)
        if not inbox_tag:
            return []

        return [{
            'id': 'documents.inbox',
            'name': _('Inbox'),
            'type': 'integer',
            'value': self.env['documents.document'].search_count([
                ('tag_ids', 'in', inbox_tag.ids),
            ]),
        }]

    @api.model
    def get_kpi_summary(self):
        result = super().get_kpi_summary()
        result.extend(self.get_documents_kpi_summary())
        return result
