(function () {
    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function formatPercent(value, digits = 1) {
        return `${(Number(value || 0) * 100).toFixed(digits)}%`;
    }

    function summarizeParams(slug, params) {
        if (slug === 'golden_cross') {
            return [
                `Fast SMA ${params.fast_sma}`,
                `Slow SMA ${params.slow_sma}`,
                `Order ${Number(params.order_percentage || 0).toFixed(0)}%`,
                `Cash $${Number(params.starting_cash || 0).toLocaleString()}`,
            ];
        }

        if (slug === 'momentum_12m') {
            return [
                `Lookback ${params.lookback}d`,
                `Buy ${formatPercent(params.buy_threshold, 1)}`,
                `Exit ${formatPercent(params.exit_threshold, 1)}`,
                `Cash $${Number(params.starting_cash || 0).toLocaleString()}`,
            ];
        }

        return Object.entries(params || {}).map(([key, value]) => `${key}: ${value}`);
    }

    function buildStrategyPanelMarkup(config, status) {
        const summary = summarizeParams(config.slug, config.params)
            .map((line) => `<li>${escapeHtml(line)}</li>`)
            .join('');

        return `
            <article class="strategy-panel" data-strategy-slug="${escapeHtml(config.slug)}">
                <div class="indicator-card-header">
                    <div>
                        <p class="indicator-card-title">${escapeHtml(config.name)}</p>
                        <p class="indicator-card-status">${escapeHtml(status.badge)}</p>
                    </div>
                    <div class="strategy-step-badge">Step ${config.sequenceIndex}</div>
                </div>
                <ul class="strategy-parameter-list">${summary}</ul>
                <p class="strategy-panel-note">${escapeHtml(status.note)}</p>
                <div class="indicator-card-actions">
                    <button type="button" class="indicator-card-btn" data-action="edit">Edit</button>
                    <button type="button" class="indicator-card-btn indicator-card-btn-danger" data-action="delete">Delete</button>
                </div>
            </article>
        `;
    }

    window.BacktestStrategyPanelHelpers = {
        buildStrategyPanelMarkup,
        summarizeParams,
    };
})();
