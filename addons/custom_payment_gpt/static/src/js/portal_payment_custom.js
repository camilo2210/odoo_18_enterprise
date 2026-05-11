/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.PortalInvoicePaymentCustom = publicWidget.Widget.extend({
    selector: '.o_payment_portal_content', // Selector del contenedor en v18
    events: {
        'change #custom_amount_input': '_onAmountChange',
        'click button[name="o_payment_submit_button"]': '_onPaymentSubmit',
    },

    _onAmountChange: function (ev) {
        const customAmount = parseFloat(ev.currentTarget.value);
        const maxAmount = parseFloat(ev.currentTarget.getAttribute('max'));
        
        // Validación funcional: No permitir sobrepagos
        if (customAmount > maxAmount) {
            alert("El monto no puede superar el saldo pendiente.");
            ev.currentTarget.value = maxAmount;
        }
    },

    _onPaymentSubmit: function (ev) {
        const inputMonto = document.getElementById('custom_amount_input');
        if (inputMonto && inputMonto.value) {
            // Buscamos el input oculto que Odoo usa para el monto de la transacción
            const amountInput = this.$el.find('input[name="amount"]');
            if (amountInput.length) {
                amountInput.val(inputMonto.value); // Inyectamos el abono parcial
            }
        }
    },
});