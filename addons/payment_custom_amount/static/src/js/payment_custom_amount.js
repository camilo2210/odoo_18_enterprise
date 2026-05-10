// ── Guardar en sesión antes del submit ────────────────────────────────────

function saveCustomAmountToSession(amount, callback) {
    fetch('/payment/custom/save_session_amount', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            jsonrpc: '2.0',
            method: 'call',
            params: { amount: amount },
        }),
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        const result = data.result || {};
        if (result.success) {
            console.log('[CustomAmount] Monto %.2f guardado en sesión', amount);
            if (callback) callback(true);
        } else {
            console.warn('[CustomAmount] Error guardando en sesión:', result.message);
            if (callback) callback(false, result.message);
        }
    })
    .catch(function(e) {
        console.warn('[CustomAmount] Fallo de red guardando sesión:', e);
        // En caso de fallo de red, continuar igual (el submit procederá)
        if (callback) callback(true);
    });
}

// ── Interceptar submit ANTES de que Odoo lo envíe ────────────────────────

if (payForm) {
    payForm.addEventListener('submit', function (e) {
        const currentType = selectedTypeEl ? selectedTypeEl.value : 'full';

        if (currentType !== 'custom') return; // No interceptar pagos totales/parciales

        e.preventDefault(); // Detener submit hasta guardar en sesión

        const customAmount = parseFloat(customInput?.value || 0);
        const minAmount    = parseFloat(customInput?.dataset.min || 1500);
        const maxAmount    = parseFloat(customInput?.dataset.max || 0);

        if (!customAmount || isNaN(customAmount) || customAmount < minAmount) {
            showError('Debes ingresar un monto válido (mínimo ' + formatCurrency(minAmount) + ' COP).');
            customInput && customInput.focus();
            return;
        }
        if (maxAmount > 0 && customAmount > maxAmount) {
            showError('El monto no puede superar ' + formatCurrency(maxAmount) + '.');
            customInput && customInput.focus();
            return;
        }

        // 1. Guardar en sesión del servidor
        saveCustomAmountToSession(customAmount, function(success, errorMsg) {
            if (!success && errorMsg) {
                showError(errorMsg);
                return;
            }

            // 2. Sobreescribir inputs del formulario como respaldo adicional
            const amountSelectors = [
                'input[name="amount"]',
                'input[name="payment_amount"]',
            ];
            amountSelectors.forEach(function(sel) {
                const el = payForm.querySelector(sel);
                if (el) {
                    el.value = customAmount.toFixed(2);
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });

            // 3. Añadir hidden como respaldo
            let hidden = payForm.querySelector('input[name="custom_amount"]');
            if (!hidden) {
                hidden = document.createElement('input');
                hidden.type  = 'hidden';
                hidden.name  = 'custom_amount';
                payForm.appendChild(hidden);
            }
            hidden.value = customAmount.toFixed(2);

            // 4. Hacer submit real ahora que la sesión está guardada
            payForm.submit();
        });

    }, false);
}