/** @odoo-module **/

import { SwitchCompanyMenu } from "@web/webclient/switch_company_menu/switch_company_menu";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { registry } from "@web/core/registry";

let allowMultiCompany = null;
let isCheckingPermission = false;

patch(SwitchCompanyMenu.prototype, {
    
    async logIntoCompany(companyId) {
        // Load permission if not loaded yet
        if (allowMultiCompany === null && !isCheckingPermission) {
            isCheckingPermission = true;
            try {
                const result = await this.orm.call(
                    "res.users",
                    "get_user_company_restriction",
                    []
                );
                allowMultiCompany = result.allow_multi_company;
            } catch (error) {
                console.error("Error checking company restriction:", error);
                allowMultiCompany = true; // Default to allow on error
            }
            isCheckingPermission = false;
        }

        // If user doesn't have multi-company permission
        if (allowMultiCompany === false) {
            const currentCompanies = this.companyService.activeCompanyIds;
            const isCompanyActive = currentCompanies.includes(companyId);
            
            // If trying to add a second company (company not active and already have one)
            if (!isCompanyActive && currentCompanies.length >= 1) {
                this.notification.add(
                    "Solo puedes seleccionar una empresa a la vez. Por favor, deselecciona la empresa actual primero.",
                    {
                        type: "warning",
                        title: "Restricción de Empresa Única",
                    }
                );
                return; // Block the action
            }
            
            // If trying to deselect the only company
            if (isCompanyActive && currentCompanies.length === 1) {
                this.notification.add(
                    "Debes tener al menos una empresa seleccionada.",
                    {
                        type: "warning",
                        title: "Empresa Requerida",
                    }
                );
                return; // Block the action
            }
        }

        // Proceed with normal behavior
        return super.logIntoCompany(companyId);
    },
});

