/**
 * payment_custom_amount.js
 * Gestiona la interacción de las pestañas de monto en el portal de pago.
 * Odoo 18 · Bootstrap 5 · Vanilla JS (sin dependencias OWL en portal)
 */

'use strict';

document.addEventListener('DOMContentLoaded', function () {

    const tabContainer     = document.getElementById('paymentAmountTabs');
    const customInput      = document.getElementById('custom_payment_amount_input');
    const selectedAmountEl = document.getElementById('payment_selected_amount');
    const selectedTypeEl   = document.getElementById('payment_selected_type');
    const feedbackEl       = document.getElementById('custom_amount_feedback');
    const payForm          = document.querySelector('form[name="o_payment_checkout"]')
                          || document.querySelector('form.o_payment_form');

    // Si no hay pestañas, el módulo no aplica para este link
    if (!tabContainer) return;

    // ── Utilidades ────────────────────────────────────────────────────────────

    function showError(msg) {
        if (!feedbackEl) return;
        feedbackEl.textContent = msg;
        feedbackEl.classList.remove('d-none');
        feedbackEl.classList.add('d-block', 'text-danger');
        if (customInput) customInput.classList.add('is-invalid');
    }

    function clearError() {
        if (!feedbackEl) return;
        feedbackEl.textContent = '';
        feedbackEl.classList.add('d-none');
        feedbackEl.classList.remove('d-block', 'text-danger');
        if (customInput) {
            customInput.classList.remove('is-invalid');
            customInput.classList.add('is-valid');
        }
    }

    function setSelectedAmount(amount, type) {
        if (selectedAmountEl) selectedAmountEl.value = amount;
        if (selectedTypeEl)   selectedTypeEl.value   = type;
        // Actualizar el input nativo de Odoo para que el proveedor reciba el monto correcto
        const odooInput = document.querySelector(
            'input[name="amount"], input[name="payment_amount"]'
        );
        if (odooInput) {
            odooInput.value = amount;
            odooInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    function formatCurrency(value) {
        return new Intl.NumberFormat('es-CO', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2,
        }).format(value);
    }

    // ── Cambio de pestañas ────────────────────────────────────────────────────

    tabContainer.querySelectorAll('[data-bs-toggle="tab"]').forEach(function (btn) {
        btn.addEventListener('shown.bs.tab', function (e) {
            const type        = e.target.dataset.paymentType;
            const amountValue = e.target.dataset.amountValue;

            if (type === 'full') {
                const fullEl  = document.querySelector('.o_payment_full_amount');
                const fullAmt = fullEl
                    ? parseFloat(fullEl.textContent.replace(/[^\d.]/g, ''))
                    : parseFloat(amountValue || 0);
                setSelectedAmount(fullAmt, 'full');
                clearError();

            } else if (type === 'partial') {
                setSelectedAmount(parseFloat(amountValue || 0), 'partial');
                clearError();

            } else if (type === 'custom') {
                setSelectedAmount(0, 'custom');
                if (customInput) customInput.focus();
            }
        });
    });

    // ── Validación del input personalizado ────────────────────────────────────

    if (customInput) {
        const minAmount = parseFloat(customInput.dataset.min || 1500);
        const maxAmount = parseFloat(customInput.dataset.max || 0);
        const invoiceId = document.querySelector('input[name="invoice_id"]')?.value || null;

        let debounceTimer;

        customInput.addEventListener('input', function () {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function () {
                validateCustomAmount(customInput.value, minAmount, maxAmount, invoiceId);
            }, 400);
        });

        customInput.addEventListener('blur', function () {
            clearTimeout(debounceTimer);
            validateCustomAmount(customInput.value, minAmount, maxAmount, invoiceId);
        });
    }

    function validateCustomAmount(value, minAmount, maxAmount, invoiceId) {
        const amount = parseFloat(value);

        if (!value || isNaN(amount)) {
            showError('Por favor ingresa un monto válido.');
            setSelectedAmount(0, 'custom');
            return;
        }
        if (amount < minAmount) {
            showError('El monto mínimo permitido es ' + formatCurrency(minAmount) + ' COP.');
            setSelectedAmount(0, 'custom');
            return;
        }
        if (maxAmount > 0 && amount > maxAmount) {
            showError('El monto no puede superar ' + formatCurrency(maxAmount) + ' (total factura).');
            setSelectedAmount(0, 'custom');
            return;
        }

        // Validación remota AJAX
        fetch('/payment/custom/validate_amount', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: { amount: amount, invoice_id: invoiceId },
            }),
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            const result = data.result || {};
            if (result.valid) {
                clearError();
                setSelectedAmount(amount, 'custom');
            } else {
                showError(result.message || 'Monto no válido.');
                setSelectedAmount(0, 'custom');
            }
        })
        .catch(function () {
            // Fallback local si el servidor no responde
            clearError();
            setSelectedAmount(amount, 'custom');
        });
    }

    // ── Interceptar submit del formulario ────────────────────────────────────

    if (payForm) {
        payForm.addEventListener('submit', function (e) {
            const currentType = selectedTypeEl ? selectedTypeEl.value : 'full';

            if (currentType === 'custom') {
                const customAmount = parseFloat(customInput?.value || 0);
                const minAmount    = parseFloat(customInput?.dataset.min || 1500);
                const maxAmount    = parseFloat(customInput?.dataset.max || 0);

                if (!customAmount || isNaN(customAmount) || customAmount < minAmount) {
                    e.preventDefault();
                    showError(
                        'Debes ingresar un monto válido (mínimo ' +
                        formatCurrency(minAmount) + ' COP).'
                    );
                    customInput && customInput.focus();
                    return false;
                }
                if (maxAmount > 0 && customAmount > maxAmount) {
                    e.preventDefault();
                    showError(
                        'El monto no puede superar ' + formatCurrency(maxAmount) + '.'
                    );
                    customInput && customInput.focus();
                    return false;
                }
                setSelectedAmount(customAmount, 'custom');
            }
        });
    }

});