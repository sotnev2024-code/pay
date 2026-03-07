/**
 * UI component renderers for the Mini App.
 */
const Components = (() => {

    function renderUserCard(profile) {
        const user = profile.user;
        const sub  = profile.subscription;

        document.getElementById('user-name').textContent = user?.first_name || 'Пользователь';

        const badge   = document.getElementById('sub-badge');
        const details = document.getElementById('sub-details');

        if (sub && sub.status === 'active') {
            badge.textContent = 'Активна';
            badge.className   = 'badge active';
            details.classList.remove('hidden');

            document.getElementById('sub-tariff-name').textContent = sub.tariff_name;

            if (sub.days_left !== null && sub.duration_days) {
                const pct = Math.max(0, Math.min(100, (sub.days_left / sub.duration_days) * 100));
                document.getElementById('sub-progress').style.width = pct + '%';
                document.getElementById('sub-days-left').textContent = sub.days_left + ' дн.';
            } else {
                document.getElementById('sub-progress').style.width = '100%';
                document.getElementById('sub-days-left').textContent = '∞';
            }

            if (sub.expires_at) {
                const d = new Date(sub.expires_at);
                document.getElementById('sub-expires').textContent =
                    'Истекает: ' + d.toLocaleDateString('ru-RU');
            } else {
                document.getElementById('sub-expires').textContent = 'Бессрочная подписка';
            }

            const channelBtn = document.getElementById('btn-goto-channel');
            if (sub.invite_link) {
                channelBtn.classList.remove('hidden');
                channelBtn.onclick = () => window.open(sub.invite_link, '_blank');
            } else {
                channelBtn.classList.add('hidden');
            }
        } else {
            badge.textContent = 'Нет подписки';
            badge.className   = 'badge';
            details.classList.add('hidden');
        }
    }

    function renderTariffGrid(tariffs, onSelect) {
        const grid = document.getElementById('tariff-grid');
        grid.innerHTML = '';

        const popular = tariffs.length > 1 ? tariffs[1] : null;

        tariffs.forEach(t => {
            const card = document.createElement('div');
            card.className = 'tariff-card' + (t === popular ? ' popular' : '');

            let featuresHtml = '';
            if (t.features && Array.isArray(t.features)) {
                featuresHtml = '<ul class="tariff-features">' +
                    t.features.map(f => `<li>${f}</li>`).join('') +
                    '</ul>';
            }

            card.innerHTML = `
                ${t === popular ? '<div class="popular-badge">Популярное</div>' : ''}
                <h3>${t.name}</h3>
                <p class="tariff-desc">${t.description}</p>
                ${featuresHtml}
                <div class="tariff-price-row">
                    <span class="tariff-price-main">⭐ ${t.price_stars}</span>
                    <span class="tariff-price-alt">${t.price_rub}₽</span>
                    <span class="tariff-price-alt">$${t.price_usd}</span>
                </div>
                <p class="tariff-duration">${t.duration_days ? t.duration_days + ' дней' : 'Разовый доступ'}</p>
            `;

            card.addEventListener('click', () => onSelect(t));
            grid.appendChild(card);
        });
    }

    function renderProviderList(providers, onSelect) {
        const list = document.getElementById('provider-list');
        list.innerHTML = '';

        providers.forEach(p => {
            const item = document.createElement('div');
            item.className = 'provider-item';
            item.dataset.provider = p.name;
            item.innerHTML = `
                <span class="provider-icon">${p.icon}</span>
                <span class="provider-label">${p.label}</span>
            `;
            item.addEventListener('click', () => {
                list.querySelectorAll('.provider-item').forEach(el => el.classList.remove('selected'));
                item.classList.add('selected');
                onSelect(p);
            });
            list.appendChild(item);
        });
    }

    function renderSelectedTariff(tariff) {
        const el = document.getElementById('selected-tariff-info');
        el.innerHTML = `
            <h3>${tariff.name}</h3>
            <p class="tariff-desc">${tariff.description}</p>
        `;
    }

    function updateTotalPrice(amount, currencySymbol) {
        document.getElementById('total-price').textContent = `${amount} ${currencySymbol}`;
    }

    function showPromoResult(message, isSuccess) {
        const el = document.getElementById('promo-result');
        el.textContent = message;
        el.className = 'promo-result ' + (isSuccess ? 'success' : 'error');
        el.classList.remove('hidden');
    }

    function hidePromoResult() {
        document.getElementById('promo-result').classList.add('hidden');
    }

    function showSuccessModal(tariffName, inviteLink) {
        document.getElementById('success-tariff-name').textContent = tariffName + ' активирован!';
        const linkEl = document.getElementById('success-channel-link');
        if (inviteLink) {
            linkEl.href = inviteLink;
            linkEl.classList.remove('hidden');
        } else {
            linkEl.classList.add('hidden');
        }
        document.getElementById('modal-success').classList.remove('hidden');
    }

    function hideSuccessModal() {
        document.getElementById('modal-success').classList.add('hidden');
    }

    return {
        renderUserCard,
        renderTariffGrid,
        renderProviderList,
        renderSelectedTariff,
        updateTotalPrice,
        showPromoResult,
        hidePromoResult,
        showSuccessModal,
        hideSuccessModal,
    };
})();
