/** @odoo-module **/

import { SwitchCompanyMenu } from "@web/webclient/switch_company_menu/switch_company_menu";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session"; // Para acceder al user_context si es necesario

patch(SwitchCompanyMenu.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.user = useService("user");
        this.orm = useService("orm");
    },

    async toggleCompany(companyId) {
        // 1. Verificar permiso. Idealmente esto debería venir en el session_info para evitar el await
        // Pero si lo mantenemos via ORM:
        const hasGroup = await this.user.hasGroup("restrict_single_company.group_multi_company_selection");

        if (!hasGroup) {
            // Lógica: Si el usuario NO tiene el grupo, forzamos SINGLE company.
            // En Odoo 17+, this.props.companyIds o similar contiene las activas.
            // Pero SwitchCompanyMenu usa el companyService.
            
            const activeCompanyIds = this.companyService.activeCompanyIds;
            const isSelected = activeCompanyIds.includes(companyId);

            // CASO A: Intenta seleccionar una segunda empresa
            if (!isSelected && activeCompanyIds.length >= 1) {
                 this.notification.add(
                    "No tienes permiso para seleccionar múltiples empresas. Se cambiará a la nueva empresa.",
                    { type: "info" }
                );
                // En Odoo 18, para forzar cambio único, usamos setCompanies con UN solo ID
                this.companyService.setCompanies([companyId], companyId);
                return; 
            }
            
            // CASO B: Intenta deseleccionar la única que tiene (Odoo suele bloquear esto por defecto, pero por si acaso)
            if (isSelected && activeCompanyIds.length === 1) {
                 this.notification.add("Debes tener al menos una empresa activa.", { type: "danger" });
                 return;
            }
        }

        // Si tiene permiso o es un toggle normal
        super.toggleCompany(companyId);
    }
});


