# -*- coding: utf-8 -*-
from odoo import api, models


class AccessStudioCacheMixin(models.AbstractModel):
    _name = "access.studio.cache.mixin"
    _description = "Mixin: Simplified Access Control Cache Behavior"

    def clear_access_studio_cache(self):
        self.env.registry.clear_cache()
        self.env.registry.clear_cache('templates')

    @api.model_create_multi
    def create(self, vals_list):
        result = super().create(vals_list)
        self.clear_access_studio_cache()
        return result

    def write(self, vals):
        result = super().write(vals)
        self.clear_access_studio_cache()
        return result

    def unlink(self):
        result = super().unlink()
        self.clear_access_studio_cache()
        return result
