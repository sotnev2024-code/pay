/**
 * Main Mini App controller — state management and navigation.
 */
(async function () {
    const tg = window.Telegram?.WebApp;
    if (tg) {
        tg.ready();
        tg.expand();
    } else {
        var notice = document.getElementById('browser-notice');
        if (notice) notice.classList.remove('hidden');
    }

    const state = {
        profile: null,
        tariffs: [],
        providers: [],
        selectedTariff: null,
        selectedProvider: null,
        promoCode: null,
        promoDiscount: null,
    };

    const currencySymbols = { RUB: '₽' };

    // ── Navigation ────────────────────────────────────────────

    function showScreen(id) {
        document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
        const screen = document.getElementById('screen-' + id);
        if (screen) screen.classList.add('active');
    }

    // ── Data Loading ──────────────────────────────────────────

    function getFallbackUser() {
        const u = tg && tg.initDataUnsafe && tg.initDataUnsafe.user;
        return u ? { first_name: u.first_name || 'Пользователь', photo_url: u.photo_url } : { first_name: 'Пользователь', photo_url: null };
    }

    async function loadData() {
        let profile = null;
        let tariffs = [];
        let providers = [];

        try {
            profile = await API.getProfile();
        } catch (e) {
            console.warn('Profile load failed:', e);
            profile = { user: getFallbackUser(), subscription: null };
        }
        if (!profile || !profile.user) {
            profile = { user: getFallbackUser(), subscription: null };
        }

        try {
            tariffs = await API.getTariffs();
        } catch (e) {
            console.warn('Tariffs load failed:', e);
        }
        if (!Array.isArray(tariffs)) tariffs = [];

        try {
            providers = await API.getProviders();
        } catch (e) {
            console.warn('Providers load failed:', e);
        }
        if (!Array.isArray(providers)) providers = [];

        state.profile   = profile;
        state.tariffs   = tariffs;
        state.providers = providers;

        Components.renderUserCard(profile, tg ? tg.initDataUnsafe : null);
        Components.renderTariffGrid(tariffs, onTariffSelect);
        Components.renderProviderList(providers, onProviderSelect);

        showScreen('profile');

        // Загрузка правил согласия для модального окна
        try {
            const consent = await API.getConsent();
            const box = document.getElementById('consent-text');
            if (box && consent && consent.text_html) {
                box.innerHTML = consent.text_html;
            }
        } catch (e) {
            console.warn('Consent load failed:', e);
        }

        // Если вернулись после оплаты (return_url с status=success&pid=...) — проверить платёж и обновить профиль
        var params = new URLSearchParams(window.location.search);
        var pid = params.get('pid') || params.get('payment_id');
        if (params.get('status') === 'success' && pid) {
            if (window.history && window.history.replaceState) {
                window.history.replaceState({}, '', window.location.pathname);
            }
            try {
                await API.checkPayment(pid);
                await loadData();
            } catch (e) {
                console.warn('Payment check failed:', e);
            }
        }
    }

    // ── Tariff Selection ──────────────────────────────────────

    function onTariffSelect(tariff) {
        state.selectedTariff  = tariff;
        state.selectedProvider = null;
        state.promoCode = null;
        state.promoDiscount = null;

        Components.renderSelectedTariff(tariff);
        Components.hidePromoResult();

        document.querySelectorAll('.provider-item').forEach(el => el.classList.remove('selected'));
        document.getElementById('promo-input').value = '';
        updatePayButton();
        updatePrice();

        showScreen('payment');
    }

    // ── Provider Selection ────────────────────────────────────

    function onProviderSelect(provider) {
        state.selectedProvider = provider;
        updatePrice();
        updatePayButton();
    }

    function getAmountForProvider(tariff, providerName) {
        // Сейчас используем только ЮKassa, сумма = цена в рублях
        return tariff.price_rub;
    }

    function getCurrencyForProvider(providerName) {
        return 'RUB';
    }

    function updatePrice() {
        if (!state.selectedTariff || !state.selectedProvider) {
            Components.updateTotalPrice('—', '');
            return;
        }

        let amount = getAmountForProvider(state.selectedTariff, state.selectedProvider.name);
        const currency = getCurrencyForProvider(state.selectedProvider.name);
        const sym = currencySymbols[currency] || currency;

        if (state.promoDiscount) {
            if (state.promoDiscount.discount_percent) {
                amount = amount * (100 - state.promoDiscount.discount_percent) / 100;
            } else if (state.promoDiscount.discount_amount) {
                amount = Math.max(amount - state.promoDiscount.discount_amount, 1);
            }
        }

        amount = Math.round(amount * 100) / 100;
        Components.updateTotalPrice(amount, sym);
    }

    // ── Pay Button State ──────────────────────────────────────

    function updatePayButton() {
        const btn = document.getElementById('btn-pay');
        const agreed = document.getElementById('agree-checkbox').checked;
        btn.disabled = !(state.selectedTariff && state.selectedProvider && agreed);
    }

    // ── Promo Code ────────────────────────────────────────────

    async function applyPromo() {
        const code = document.getElementById('promo-input').value.trim();
        if (!code) return;

        try {
            const result = await API.validatePromo(
                code,
                state.selectedTariff?.id || null,
            );
            state.promoCode = code;
            state.promoDiscount = result;
            const desc = result.discount_percent
                ? `-${result.discount_percent}%`
                : `-${result.discount_amount}`;
            Components.showPromoResult(`Промокод применён: ${desc}`, true);
            updatePrice();
        } catch (e) {
            state.promoCode = null;
            state.promoDiscount = null;
            Components.showPromoResult(e.message || 'Промокод недействителен', false);
            updatePrice();
        }
    }

    // ── Payment ───────────────────────────────────────────────

    async function handlePay() {
        const btn = document.getElementById('btn-pay');
        btn.disabled = true;
        btn.textContent = '⏳ Создание платежа...';

        try {
            const result = await API.createPayment(
                state.selectedTariff.id,
                state.selectedProvider.name,
                state.promoCode,
            );

            if (result.pay_url) {
                window.open(result.pay_url, '_blank');
                setTimeout(async () => {
                    const profile = await API.getProfile();
                    if (profile.subscription?.status === 'active') {
                        Components.showSuccessModal(
                            state.selectedTariff.name,
                            profile.subscription.invite_link,
                        );
                    }
                }, 5000);
            }
        } catch (e) {
            alert('Ошибка: ' + (e.message || 'Не удалось создать платёж'));
        } finally {
            btn.disabled = false;
            btn.textContent = '💳 Оплатить';
            updatePayButton();
        }
    }

    // ── Event Listeners ───────────────────────────────────────

    document.getElementById('btn-goto-tariffs').addEventListener('click', () => showScreen('tariffs'));
    document.getElementById('btn-back-profile').addEventListener('click', () => showScreen('profile'));
    document.getElementById('btn-back-tariffs').addEventListener('click', () => showScreen('tariffs'));
    document.getElementById('btn-apply-promo').addEventListener('click', applyPromo);
    document.getElementById('btn-pay').addEventListener('click', handlePay);
    document.getElementById('agree-checkbox').addEventListener('change', updatePayButton);
    document.getElementById('btn-open-consent').addEventListener('click', () => {
        document.getElementById('modal-consent').classList.remove('hidden');
    });
    document.getElementById('btn-close-consent').addEventListener('click', () => {
        document.getElementById('modal-consent').classList.add('hidden');
    });
    document.getElementById('btn-close-modal').addEventListener('click', () => {
        Components.hideSuccessModal();
        showScreen('profile');
        loadData();
    });

    document.getElementById('promo-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') applyPromo();
    });

    // ── Init ──────────────────────────────────────────────────

    await loadData();
})();
