/**
 * API client for Mini App backend communication.
 * All requests include Telegram initData for authentication.
 */
const API = (() => {
    const BASE = '/api';

    function _headers() {
        const h = { 'Content-Type': 'application/json' };
        if (window.Telegram?.WebApp?.initData) {
            h['X-Telegram-Init-Data'] = window.Telegram.WebApp.initData;
        }
        return h;
    }

    async function _request(method, path, body) {
        const opts = { method, headers: _headers() };
        if (body) opts.body = JSON.stringify(body);

        const res = await fetch(BASE + path, opts);
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }
        return res.json();
    }

    return {
        getTariffs:     ()              => _request('GET',  '/tariffs'),
        getProfile:     ()              => _request('GET',  '/profile'),
        getProviders:   ()              => _request('GET',  '/providers'),
        checkPayment:   (paymentId)     => _request('GET',  '/payment/check?payment_id=' + encodeURIComponent(paymentId)),
        validatePromo:  (code, tid)    => _request('POST', '/promo/validate', { code, tariff_id: tid }),
        createPayment:  (tariffId, provider, promoCode) =>
            _request('POST', '/payment/create', {
                tariff_id: tariffId,
                provider,
                promo_code: promoCode || null,
            }),
    };
})();
