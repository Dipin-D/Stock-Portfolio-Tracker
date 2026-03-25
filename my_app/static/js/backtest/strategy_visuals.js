(function () {
    const VISUALS = {
        golden_cross: {
            slug: 'golden_cross',
            name: 'Golden Cross',
            shortLabel: 'GC',
            color: '#d97706',
            borderColor: '#f59e0b',
            softColor: 'rgba(217, 119, 6, 0.12)',
            textColor: '#92400e',
            markerEntryLabel: 'GC Buy',
            markerExitLabel: 'GC Exit',
        },
        momentum_12m: {
            slug: 'momentum_12m',
            name: 'Momentum 12M',
            shortLabel: 'M12',
            color: '#0f766e',
            borderColor: '#14b8a6',
            softColor: 'rgba(15, 118, 110, 0.12)',
            textColor: '#115e59',
            markerEntryLabel: 'M12 Buy',
            markerExitLabel: 'M12 Exit',
        },
        golden_cross_bollinger_squeeze: {
            slug: 'golden_cross_bollinger_squeeze',
            name: 'Golden Cross + Bollinger Squeeze',
            shortLabel: 'GC+BS',
            color: '#2563eb',
            borderColor: '#38bdf8',
            softColor: 'rgba(37, 99, 235, 0.12)',
            textColor: '#1d4ed8',
            markerEntryLabel: 'GC+BS Buy',
            markerExitLabel: 'GC+BS Exit',
        },
        golden_cross_bollinger_breakout_confirm: {
            slug: 'golden_cross_bollinger_breakout_confirm',
            name: 'Golden Cross + Bollinger Breakout Confirm',
            shortLabel: 'GC+BBC',
            color: '#7c3aed',
            borderColor: '#a855f7',
            softColor: 'rgba(124, 58, 237, 0.12)',
            textColor: '#6d28d9',
            markerEntryLabel: 'GC+BBC Buy',
            markerExitLabel: 'GC+BBC Exit',
        },
    };

    const FALLBACK_VISUAL = {
        slug: 'strategy',
        name: 'Strategy',
        shortLabel: 'STR',
        color: '#475569',
        borderColor: '#94a3b8',
        softColor: 'rgba(71, 85, 105, 0.12)',
        textColor: '#334155',
        markerEntryLabel: 'Entry',
        markerExitLabel: 'Exit',
    };

    function normalizeSlug(slug) {
        return String(slug || '')
            .trim()
            .toLowerCase();
    }

    function getStrategyVisual(slug) {
        const normalized = normalizeSlug(slug);
        return Object.assign({}, FALLBACK_VISUAL, VISUALS[normalized] || {}, {
            slug: normalized || FALLBACK_VISUAL.slug,
        });
    }

    window.BacktestStrategyVisuals = {
        getStrategyVisual,
        all() {
            return Object.keys(VISUALS).map((slug) => getStrategyVisual(slug));
        },
    };
})();
