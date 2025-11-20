from odoo import api, models


class IrModuleModule(models.Model):
    """Extended module model with simplified access control uninstall handling."""

    _inherit = "ir.module.module"

    def button_immediate_uninstall(self):
        """Override button_immediate_uninstall to handle module uninstallation."""
        config_parameter_obj = self.env["ir.config_parameter"].sudo()

        if self.name == "access_studio":
            # Set configuration parameter to mark uninstallation
            value = config_parameter_obj.search(
                [("key", "=", "uninstall_access_studio")], limit=1
            )
            if value:
                value.value = "True"
            else:
                config_parameter_obj.create(
                    {"key": "uninstall_access_studio", "value": "True"}
                )

            # Force commit to ensure parameter is saved
            self._cr.commit()

        # Call parent method to proceed with uninstallation
        res = super(IrModuleModule, self).button_immediate_uninstall()

        # Clean up the configuration parameter after uninstallation
        if self.name == "access_studio":
            config_parameter_obj.search(
                [("key", "=", "uninstall_access_studio")], limit=1
            ).unlink()

        return res
