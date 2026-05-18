/** @odoo-module **/
'use strict';

import publicWidget from "@web/legacy/js/public/public_widget";
import { patch } from "@web/core/utils/patch";

const PaymentForm = publicWidget.registry.PaymentForm;

patch(PaymentForm.prototype, {

    /**
     * Override _prepareTransactionRouteParams to inject the custom amount
     * into the JSON-RPC params sent to the transaction controller.
     *
     * This is the correct hook: the returned object is sent as the body of the
     * RPC call to the transaction route (e.g. /invoice/transaction/<id>).
     * When `amount` is overridden here, _create_transaction() creates the
     * payment.transaction record with the custom amount, so self.amount in the
     * DB is already correct when Mercado Pago (or any provider) reads it.
     */
    _prepareTransactionRouteParams() {
        const params = super._prepareTransactionRouteParams(...arguments);

        // Detect if the "Otro Monto" (custom amount) pane is active
        const activeCustomPane = document.querySelector(
            '#o_payment_custom.tab-pane.show.active, ' +
            '#o_payment_custom_simple.tab-pane.show.active'
        );

        if (activeCustomPane) {
            const customInput = activeCustomPane.querySelector('.o_custom_amount_input');

            if (customInput && customInput.value) {
                const customAmount = parseFloat(customInput.value);
                const minAmount    = parseFloat(customInput.dataset.min || 0);
                const maxAmount    = parseFloat(customInput.dataset.max || 0);

                if (!isNaN(customAmount) && customAmount > 0) {
                    // Client-side validation (server also validates)
                    if (minAmount > 0 && customAmount < minAmount) {
                        console.warn(
                            `[CustomAmount] Amount ${customAmount} below minimum ${minAmount}`
                        );
                        return params;  // Don't override, let server-side validation handle it
                    }
                    if (maxAmount > 0 && customAmount > maxAmount) {
                        console.warn(
                            `[CustomAmount] Amount ${customAmount} exceeds maximum ${maxAmount}`
                        );
                        return params;
                    }

                    console.log(
                        `[CustomAmount] ✅ Overriding amount: ${params.amount} → ${customAmount}`
                    );
                    params.amount = customAmount;
                }
            }
        }

        return params;
    },

    /**
     * Override _submitForm to add client-side validation before submitting.
     * Shows user-facing error messages if the custom amount is invalid.
     */
    async _submitForm(ev) {
        // Check if custom pane is active and validate before submitting
        const activeCustomPane = document.querySelector(
            '#o_payment_custom.tab-pane.show.active, ' +
            '#o_payment_custom_simple.tab-pane.show.active'
        );

        if (activeCustomPane) {
            const customInput = activeCustomPane.querySelector('.o_custom_amount_input');

            if (customInput) {
                const value      = customInput.value;
                const amount     = parseFloat(value);
                const minAmount  = parseFloat(customInput.dataset.min || 0);
                const maxAmount  = parseFloat(customInput.dataset.max || 0);

                if (!value || isNaN(amount) || amount <= 0) {
                    this._showCustomError("Ingresa un monto válido.");
                    return;
                }
                if (minAmount > 0 && amount < minAmount) {
                    this._showCustomError(`Monto mínimo: ${minAmount}`);
                    return;
                }
                if (maxAmount > 0 && amount > maxAmount) {
                    this._showCustomError(`No puede superar ${maxAmount}`);
                    return;
                }

                // Clear any previous error
                this._clearCustomError();
            }
        }

        return super._submitForm(ev);
    },

    // ── Helper: show error in the custom amount feedback area ──────────
    _showCustomError(message) {
        const feedback = document.querySelector(
            '#custom_amount_feedback, #custom_amount_feedback_simple'
        );
        if (feedback) {
            feedback.textContent = message;
            feedback.classList.add('d-block', 'text-danger');
            feedback.classList.remove('d-none');
        }
        const input = document.querySelector('.o_custom_amount_input');
        if (input) input.classList.add('is-invalid');
    },

    // ── Helper: clear error in the custom amount feedback area ─────────
    _clearCustomError() {
        const feedback = document.querySelector(
            '#custom_amount_feedback, #custom_amount_feedback_simple'
        );
        if (feedback) {
            feedback.textContent = '';
            feedback.classList.remove('d-block', 'text-danger');
            feedback.classList.add('d-none');
        }
        const input = document.querySelector('.o_custom_amount_input');
        if (input) input.classList.remove('is-invalid');
    },
});