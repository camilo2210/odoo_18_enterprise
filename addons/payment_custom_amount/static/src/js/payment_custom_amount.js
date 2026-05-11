/** @odoo-module **/
'use strict';

import { PaymentForm } from "@payment/js/payment_form";
import { patch } from "@web/core/utils/patch";

patch(PaymentForm.prototype, {

    // ── Interceptar el submit del formulario OWL de Odoo ─────────────────
    async _submitForm(params) {
        console.log("[CustomAmount] _submitForm llamado, params:", params);

        // Detectar si el pane de "Otro Monto" está activo
        const activeCustomPane = document.querySelector(
            '#o_payment_custom.tab-pane.show.active, ' +
            '#o_payment_custom_simple.tab-pane.show.active'
        );

        console.log("[CustomAmount] Pane personalizado activo:", !!activeCustomPane);

        if (activeCustomPane) {
            const customInput = activeCustomPane.querySelector('.o_custom_amount_input');
            console.log("[CustomAmount] Input encontrado:", customInput?.value);

            if (customInput && customInput.value) {
                const customAmount = parseFloat(customInput.value);
                const maxAmount    = parseFloat(customInput.dataset.max || 0);
                const minAmount    = parseFloat(customInput.dataset.min || 0);

                // Validar rango
                if (isNaN(customAmount) || customAmount <= 0) {
                    this._displayError("Ingresa un monto válido.");
                    return;
                }
                if (minAmount > 0 && customAmount < minAmount) {
                    this._displayError(`Monto mínimo: ${minAmount}`);
                    return;
                }
                if (maxAmount > 0 && customAmount > maxAmount) {
                    this._displayError(`No puede superar ${maxAmount}`);
                    return;
                }

                console.log(
                    "[CustomAmount] ✅ Reemplazando amount:", params.amount, "→", customAmount
                );
                // AQUÍ es donde se inyecta el monto al JSON que va al controller
                params = { ...params, amount: customAmount };
            }
        }

        return super._submitForm(params);
    },

    // ── Mostrar error en el feedback del pane activo ──────────────────────
    _displayError(message) {
        const feedback = document.querySelector(
            '#custom_amount_feedback:not(.d-none), ' +
            '#custom_amount_feedback_simple'
        );
        if (feedback) {
            feedback.textContent = message;
            feedback.classList.add('d-block', 'text-danger');
            feedback.classList.remove('d-none');
        }
        const input = document.querySelector('.o_custom_amount_input');
        if (input) input.classList.add('is-invalid');
    },
});