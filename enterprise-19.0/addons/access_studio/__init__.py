import logging
from . import models, controllers

_logger = logging.getLogger(__name__)

def post_install_action_hook(env):
    action_data_obj = env["action.data"]
    for action in env["ir.actions.actions"].search([]):
        try:
            action_data_obj.create({"name": action.name, "action_id": action.id})
        except Exception as e:
            _logger.error("Error creating action.data record: %s", e)

    menu_data_obj = env["menu.data"]
    try:
        module_menu_ids = env["access.studio"]._get_access_studio_module_menus()
    except Exception as e:
        _logger.error("Error getting simplified access module menus: %s", e)
        module_menu_ids = []

    for menu in env["ir.ui.menu"].search([]):
        if menu.id not in module_menu_ids:
            try:
                menu_data_obj.create({"name": menu.name, "menu_id": menu.id})
            except Exception as e:
                _logger.error("Error creating menu.data record: %s", e)
