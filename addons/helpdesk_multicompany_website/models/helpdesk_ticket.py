# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    @api.constrains('team_id', 'company_id')
    def _check_company_team_consistency(self):
        """Ensure ticket company matches its team's company.

        This is a critical safety net: tickets must NEVER be created
        in a company different from the team's company. This prevents
        cross-company data leakage in multi-company environments.
        """
        for ticket in self:
            if not ticket.team_id or not ticket.company_id:
                continue
            if not ticket.team_id.company_id:
                continue
            if ticket.company_id != ticket.team_id.company_id:
                _logger.error(
                    'Cross-company ticket rejected: ticket "%s" (company=%s) '
                    'vs team "%s" (company=%s)',
                    ticket.name or _('Nuevo'),
                    ticket.company_id.name,
                    ticket.team_id.name,
                    ticket.team_id.company_id.name,
                )
                raise ValidationError(_(
                    'El ticket "%(ticket)s" no puede pertenecer a la compañía '
                    '"%(ticket_company)s" porque el equipo "%(team)s" pertenece '
                    'a la compañía "%(team_company)s".\n\n'
                    'Los tickets deben crearse en la misma compañía que su '
                    'equipo de mesa de ayuda.',
                    ticket=ticket.name or _('Nuevo'),
                    ticket_company=ticket.company_id.name,
                    team=ticket.team_id.name,
                    team_company=ticket.team_id.company_id.name,
                ))
