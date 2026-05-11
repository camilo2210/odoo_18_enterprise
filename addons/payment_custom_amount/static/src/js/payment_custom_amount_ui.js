'use strict';

document.addEventListener('DOMContentLoaded', function () {

    const tabContainer = document.getElementById('paymentAmountTabs');
    if (!tabContainer) return;

    const customInput  = document.getElementById('custom_payment_amount_input');
    const feedbackEl   = document.getElementById('custom_amount_feedback');

    // El form nativo de /my/invoices usa o_payment_form o similar
    const payForm = document.querySelector('form[name="o_payment_checkout"]')
                 || document.querySelector('form.o_payment_form')
                 || document.querySelector('#payment_form')
                 || document.querySelector('form[action*="transaction"]');

    // ── Utilidades ────────────────────────────────────────────────────────
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
        feedbackEl.classList.remove('d-block');
        if (customInput) {
            customInput.classList.remove('is-invalid');
            customInput.classList.add('is-valid');
        }
    }

    function formatCOP(val) {
        return new Intl.NumberFormat('es-CO', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2,
        }).format(val);
    }

    // ── Inyectar/actualizar campo oculto en el form nativo ───────────────
    function setHiddenField(name, value) {
        if (!payForm) return;
        let el = payForm.querySelector('input[name="' + name + '"]');
        if (!el) {
            el = document.createElement('input');
            el.type = 'hidden';
            el.name = name;
            payForm.appendChild(el);
        }
        el.value = value;
    }

    function setPaymentType(type) {
        setHiddenField('custom_payment_type', type);
    }

    function setCustomAmount(amount) {
        setHiddenField('custom_payment_amount', amount);
    }

    // Inicializar con tipo 'full' — no interferir si el cliente no toca nada
    setPaymentType('full');
    setCustomAmount('');

    // ── Cambio de pestañas ────────────────────────────────────────────────
    tabContainer.querySelectorAll('[data-bs-toggle="tab"]').forEach(function (btn) {
        btn.addEventListener('shown.bs.tab', function (e) {
            const type  = e.target.dataset.paymentType;
            const value = e.target.dataset.amountValue;

            if (type === 'full') {
                setPaymentType('full');
                setCustomAmount('');
                clearError();
            } else if (type === 'partial') {
                setPaymentType('partial');
                setCustomAmount('');
                clearError();
            } else if (type === 'custom') {
                setPaymentType('custom');
                setCustomAmount('');
                if (customInput) customInput.focus();
            }
        });
    });

    // ── Validación AJAX del input ─────────────────────────────────────────
    if (customInput) {
        const minAmount = parseFloat(customInput.dataset.min || 1500);
        const maxAmount = parseFloat(customInput.dataset.max || 0);
        const invoiceId = document.querySelector('input[name="invoice_id"]')?.value
                       || window.location.pathname.match(/\/(\d+)/)?.[1]
                       || null;
        let debounceTimer;

        customInput.addEventListener('input', function () {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function () {
                validateAndSet(customInput.value, minAmount, maxAmount, invoiceId);
            }, 400);
        });

        customInput.addEventListener('blur', function () {
            clearTimeout(debounceTimer);
            validateAndSet(customInput.value, minAmount, maxAmount, invoiceId);
        });
    }

    function validateAndSet(value, minAmount, maxAmount, invoiceId) {
        const amount = parseFloat(value);

        if (!value || isNaN(amount)) {
            showError('Por favor ingresa un monto válido.');
            setCustomAmount('');
            return;
        }
        if (amount < minAmount) {
            showError('Monto mínimo: ' + formatCOP(minAmount) + ' COP.');
            setCustomAmount('');
            return;
        }
        if (maxAmount > 0 && amount > maxAmount) {
            showError('No puede superar ' + formatCOP(maxAmount) + '.');
            setCustomAmount('');
            return;
        }

        fetch('/payment/custom/validate_amount', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jsonrpc: '2.0', method: 'call', id: Date.now(),
                params: { amount: amount, invoice_id: invoiceId },
            }),
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            const result = data.result || {};
            if (result.valid) {
                clearError();
                // Guardar el monto en el campo oculto — viajará con el POST
                setCustomAmount(amount);
                console.log('[CustomAmount] Monto ' + amount + ' listo en campo oculto');
            } else {
                showError(result.message || 'Monto no válido.');
                setCustomAmount('');
            }
        })
        .catch(function () {
            clearError();
            setCustomAmount(amount);
        });
    }

    // ── Validación final en submit ────────────────────────────────────────
    if (payForm) {
        payForm.addEventListener('submit', function (e) {
            const typeInput   = payForm.querySelector('input[name="custom_payment_type"]');
            const amountInput = payForm.querySelector('input[name="custom_payment_amount"]');
            const currentType = typeInput ? typeInput.value : 'full';

            if (currentType !== 'custom') return; // no interferir

            const amount    = parseFloat(amountInput?.value || 0);
            const minAmount = parseFloat(customInput?.dataset.min || 1500);
            const maxAmount = parseFloat(customInput?.dataset.max || 0);

            if (!amount || isNaN(amount) || amount < minAmount) {
                e.preventDefault();
                showError('Ingresa un monto válido (mínimo ' + formatCOP(minAmount) + ' COP).');
                customInput && customInput.focus();
                return;
            }
            if (maxAmount > 0 && amount > maxAmount) {
                e.preventDefault();
                showError('No puede superar ' + formatCOP(maxAmount) + '.');
                customInput && customInput.focus();
                return;
            }

            console.log('[CustomAmount] Submit con monto personalizado: ' + amount);
        });
    }

});