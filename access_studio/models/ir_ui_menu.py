# -*- coding: utf-8 -*-

import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def _filter_visible_menus(self):
        visible_menu_ids = super()._filter_visible_menus()
        hide_menu_ids = self.env["access.studio"].get_cached_menu_ids_to_restrict()
        visible_menu_ids -= hide_menu_ids
        return visible_menu_ids

    @api.model_create_multi
    def create(self, vals_list):
        menus = super().create(vals_list)
        menu_data_vals = []
        module_menu_ids = self.env["access.studio"]._get_access_studio_module_menus()
        for menu in menus:
            if menu.id not in module_menu_ids:
                menu_data_vals.append(
                    {
                        "menu_id": menu.id,
                        "name": menu.name,
                    }
                )
        if menu_data_vals:
            try:
                self.env["menu.data"].create(menu_data_vals)
                _logger.info(
                    "Created %d menu.data records for new menus",
                    len(menu_data_vals),
                )
            except Exception as e:
                _logger.error("Error creating menu.data records: %s", e)
        return menus

    def unlink(self):
        menu_ids = self.ids
        result = super().unlink()
        try:
            menu_data_records = self.env["menu.data"].search(
                [("menu_id", "in", menu_ids)]
            )
            if menu_data_records:
                menu_data_records.unlink()
                _logger.info(
                    "Removed %d menu.data records for deleted menus",
                    len(menu_data_records),
                )
        except Exception as e:
            _logger.error("Error removing menu.data records: %s", e)
        return result
