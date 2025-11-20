from odoo import api, models, fields, _
import logging
import json

from odoo import tools
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)

class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    # field access cache now provided by field.access.get_cached_field_access

    def _access_studio_update_modifiers(self, node, updates):
        """Force-update modifiers on a field node.

        updates: dict like {'invisible': True, 'readonly': True, 'required': True}
        """
        try:
            modifiers = json.loads(node.attrib.get('modifiers', '{}')) if node.attrib.get('modifiers') else {}
        except Exception:
            modifiers = {}
        for key, val in updates.items():
            if val:
                modifiers[key] = True
        if modifiers:
            node.attrib['modifiers'] = json.dumps(modifiers, separators=(',', ':'))

        # Also reflect basic attrs for robustness
        if updates.get('invisible'):
            node.attrib['invisible'] = '1'
            node.attrib['column_invisible'] = '1'
            node.attrib['class'] = node.attrib.get('class', '') + ' d-none'
        if updates.get('readonly'):
            node.attrib['readonly'] = '1'
        if updates.get('required'):
            node.attrib['required'] = '1'

    def _postprocess_tag_field(self, node, name_manager, node_info):
        res = super()._postprocess_tag_field(node, name_manager, node_info)
        if node.tag != 'field':
            return res
        model_name = name_manager.model._name
        field_name = node.attrib.get('name')
        if not field_name:
            return res

        # 1) Global field access rules (static flags and many2one options)
        access_map = self.env['field.access'].get_cached_field_access(model_name)
        field_rules = access_map.get(field_name)
        if field_rules:
            modifiers = {}

            if field_rules.get('invisible'):
                modifiers['invisible'] = True
            if field_rules.get('readonly'):
                modifiers['readonly'] = True
            if field_rules.get('required'):
                modifiers['required'] = True

            self._access_studio_update_modifiers(node, modifiers)

            field_def = name_manager.model._fields.get(field_name)
            if field_def and field_def.type == 'many2one':
                try:
                    options = json.loads(node.attrib.get('options', '{}')) if node.attrib.get('options') else {}
                except Exception:
                    options = {}

                if field_rules.get('remove_create_option'):
                    options['no_quick_create'] = True
                    options['no_create'] = True
                if field_rules.get('remove_edit_option'):
                    options['no_create_edit'] = True
                if field_rules.get('remove_internal_link'):
                    options['no_open'] = True

                if options:
                    node.attrib['options'] = json.dumps(options, separators=(',', ':'))

        # 2) Conditional rules (attrs via modifiers JSON, relational domain direct)
        cond = self.env['field.conditional.access'].get_cached_field_conditional_rules(model_name)
        attrs_slot = cond['attrs_map'].get(field_name)

        if attrs_slot:
            # Conditional simple expressions set directly on node (client evaluates)
            for key, expr in attrs_slot['expr'].items():
                if expr:
                    node.set(key, expr)

        dom_str = cond['domain_map'].get(field_name)
        if dom_str:
            node.set('domain', dom_str)
        return res

    def _postprocess_tag_label(self, node, name_manager, node_info):
        res = super()._postprocess_tag_label(node, name_manager, node_info)
        # Mirror-hide label when its target field is forced invisible by SAC
        target_field = node.get('for')
        if not target_field:
            return res
        model_name = name_manager.model._name
        access_map = self.env['field.access'].get_cached_field_access(model_name)
        rules = access_map.get(target_field)
        if rules and rules.get('invisible'):
            self._access_studio_update_modifiers(node, {'invisible': True})
        return res


    def _postprocess_tag_form(self, node, name_manager, node_info):
        super()._postprocess_tag_form(node, name_manager, node_info)
        hidden = self.env['hide.buttons.tabs'].get_cached_hidden_nodes(name_manager.model._name)
        chatter_rule = self.env['chatter.access'].get_cached_chatter_access(name_manager.model._name)

        def hide(xpath):
            for el in node.xpath(xpath):
                self._access_studio_update_modifiers(el, {'invisible': True})
        
        if chatter_rule.get('hide_chatter'):
            hide("//chatter")
            hide("//div[hasclass('o_attachment_preview')]")

        # Header buttons (exclude smart button box)
        for n in hidden.get('form', {}).get('buttons', {}).get('object', set()):
            hide(f".//button[@type='object' and @name='{n}' and not(ancestor::div[contains(@class,'oe_button_box')])]" )
        for n in hidden.get('form', {}).get('buttons', {}).get('action', set()):
            hide(f".//button[@type='action' and @name='{n}' and not(ancestor::div[contains(@class,'oe_button_box')])]" )

        # Smart buttons (inside oe_button_box)
        for n in hidden.get('form', {}).get('buttons', {}).get('object', set()):
            hide(f".//div[contains(@class,'oe_button_box')]//button[@type='object' and @name='{n}']")
        for n in hidden.get('form', {}).get('buttons', {}).get('action', set()):
            hide(f".//div[contains(@class,'oe_button_box')]//button[@type='action' and @name='{n}']")

        # Tabs
        for n in hidden.get('form', {}).get('tabs', set()):
            hide(f".//notebook//page[@name='{n}' or @string='{n}']")

    def _postprocess_tag_list(self, node, name_manager, node_info):
        super()._postprocess_tag_list(node, name_manager, node_info)
        hidden = self.env['hide.buttons.tabs'].get_cached_hidden_nodes(name_manager.model._name)

        def hide(xpath):
            for el in node.xpath(xpath):
                self._access_studio_update_modifiers(el, {'invisible': True})

        # Header buttons
        for n in hidden.get('list header', {}).get('buttons', {}).get('object', set()):
            hide(f"./header//button[@type='object' and @name='{n}']")
        for n in hidden.get('list header', {}).get('buttons', {}).get('action', set()):
            hide(f"./header//button[@type='action' and @name='{n}']")

        # Row buttons (exclude header)
        for n in hidden.get('list row', {}).get('buttons', {}).get('object', set()):
            hide(f".//button[@type='object' and @name='{n}' and not(ancestor::header)]")
        for n in hidden.get('list row', {}).get('buttons', {}).get('action', set()):
            hide(f".//button[@type='action' and @name='{n}' and not(ancestor::header)]")