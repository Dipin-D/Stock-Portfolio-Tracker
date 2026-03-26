(function () {
    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function formatPercent(value, digits = 2) {
        return `${(Number(value || 0) * 100).toFixed(digits)}%`;
    }

    function formatSignedPercent(value, digits = 2) {
        const numeric = Number(value || 0) * 100;
        return `${numeric >= 0 ? '+' : ''}${numeric.toFixed(digits)}%`;
    }

    function formatDecimal(value, digits = 3) {
        return Number(value || 0).toFixed(digits);
    }

    function formatCurrency(value) {
        return Number(value || 0).toLocaleString(undefined, {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function buildMathUrl(result) {
        if (!result || !result.run_id) {
            return '';
        }
        return `/theMath/?run_id=${encodeURIComponent(result.run_id)}&section=bayesian#bayesian`;
    }

    function getStrategyVisual(slug) {
        return window.BacktestStrategyVisuals?.getStrategyVisual(slug) || {
            slug: String(slug || ''),
            name: String(slug || 'Strategy'),
            shortLabel: 'STR',
            color: '#475569',
            borderColor: '#94a3b8',
            softColor: 'rgba(71, 85, 105, 0.12)',
            textColor: '#334155',
        };
    }

    function strategyStyleAttr(slug) {
        const visual = getStrategyVisual(slug);
        return `style="--strategy-accent:${escapeHtml(visual.color)};--strategy-accent-soft:${escapeHtml(visual.softColor)};--strategy-accent-border:${escapeHtml(visual.borderColor)};--strategy-accent-text:${escapeHtml(visual.textColor)};"`;
    }

    function strategyDisplayName(slug, fallbackName = '') {
        return escapeHtml(fallbackName || getStrategyVisual(slug).name);
    }

    function renderStrategyBadge(slug, fallbackName = '') {
        const visual = getStrategyVisual(slug);
        return `
            <span class="strategy-badge" ${strategyStyleAttr(slug)}>
                <span class="strategy-badge-swatch"></span>
                <span class="strategy-badge-text">${strategyDisplayName(slug, fallbackName)}</span>
            </span>
        `;
    }

    function renderMathLink(href, label, extraClass = '') {
        if (!href) {
            return `<span class="bayes-text-link bayes-text-link-disabled ${extraClass}">Run required</span>`;
        }

        return `<a class="bayes-text-link ${extraClass}" href="${href}">${escapeHtml(label)}</a>`;
    }

    function renderMetricCard(label, value, href, accentClass = '') {
        const tagName = href ? 'a' : 'div';
        const hrefAttr = href ? ` href="${href}"` : '';
        const interactiveClass = href ? ' is-clickable' : '';
        const cta = href
            ? '<span class="bayes-metric-cta">Open Math</span>'
            : '<span class="bayes-metric-cta bayes-metric-cta-muted">Run required</span>';

        return `
            <${tagName} class="bayes-metric-card${interactiveClass}${accentClass ? ` ${accentClass}` : ''}"${hrefAttr}>
                <div class="bayes-metric-card-copy">
                    <span class="bayes-metric-label">${label}</span>
                    <strong>${value}</strong>
                </div>
                ${cta}
            </${tagName}>
        `;
    }

    function earningsModeLabel(mode) {
        switch (String(mode || '').toLowerCase()) {
            case 'never_trade':
                return 'Never Trade Earnings';
            case 'only_trade':
                return 'Only Trade Earnings';
            case 'custom':
                return 'Custom Earnings';
            default:
                return 'Nothing Special';
        }
    }

    function buildEarningsSummary(result) {
        const earnings = result?.earnings || {};
        const mode = earningsModeLabel(earnings.mode);
        const datesCount = Number(earnings.dates_count || 0);
        const blocked = Number(earnings.blocked_entry_signals_total || 0);
        return {
            mode,
            datesCount,
            blocked,
            text: `${mode} · ${datesCount} dates · ${blocked} entries blocked`,
        };
    }

    function renderPosteriorPanel(result) {
        const lift = Number(result.posterior_probability || 0) - Number(result.prior_probability || 0);
        const mathUrl = buildMathUrl(result);

        return `
            <div class="bayes-summary-shell">
                <div class="bayes-panel-header">
                    <div>
                        <p class="bayes-summary-eyebrow">Probability ladder</p>
                        <h4 class="indicator-card-title">Current Bayesian read</h4>
                    </div>
                    ${mathUrl
                        ? `<a class="bayes-math-link" href="${mathUrl}">View Bayesian Math</a>`
                        : '<span class="bayes-math-link bayes-math-link-disabled">Run required</span>'}
                </div>
                <div class="bayes-metric-grid bayes-metric-grid-wide">
                    ${renderMetricCard('Prior Probability', formatPercent(result.prior_probability), mathUrl)}
                    ${renderMetricCard('Posterior Probability', formatPercent(result.posterior_probability), mathUrl, 'bayes-metric-card-emphasis')}
                    ${renderMetricCard('Bayesian Lift', formatSignedPercent(lift), mathUrl)}
                    ${renderMetricCard('Confidence', escapeHtml(result.confidence_label || 'Unknown'), mathUrl)}
                </div>
                <div class="bayes-summary-footer">
                    <p class="bayes-workflow-footnote">Click any probability card to inspect the exact prior, LR, weighted log-LR, and posterior math for this run.</p>
                    ${renderMathLink(mathUrl, 'Open the full run derivation')}
                </div>
            </div>
        `;
    }

    function renderEvidenceDetailMarkup(strategy) {
        return `
            <div class="bayes-evidence-detail-header">
                <div class="bayes-evidence-detail-title">
                    ${renderStrategyBadge(strategy.slug, strategy.name)}
                    <strong>Step ${strategy.sequence_index} contribution</strong>
                </div>
                <span class="strategy-signal-pill ${strategy.active ? 'strategy-signal-pill-active' : 'strategy-signal-pill-inactive'}">
                    ${strategy.active ? 'Active' : 'Inactive'}
                </span>
            </div>
            <p class="bayes-evidence-detail-meta">
                Inspect how this strategy changed the posterior after the prior and earlier steps were already taken into account.
            </p>
            <div class="bayes-evidence-detail-grid">
                <div class="bayes-evidence-detail-metric">
                    <span>Strength</span>
                    <strong>${formatDecimal(strategy.strength, 2)}</strong>
                </div>
                <div class="bayes-evidence-detail-metric">
                    <span>Likelihood Ratio</span>
                    <strong>${formatDecimal(strategy.likelihood_ratio, 2)}</strong>
                </div>
                <div class="bayes-evidence-detail-metric">
                    <span>Weighted Log-LR</span>
                    <strong>${formatDecimal(strategy.weighted_log_lr, 3)}</strong>
                </div>
                <div class="bayes-evidence-detail-metric">
                    <span>Posterior After</span>
                    <strong>${formatPercent(strategy.posterior_after || 0)}</strong>
                </div>
            </div>
        `;
    }

    function renderEvidenceMobileCard(strategy) {
        return `
            <article class="bayes-evidence-mobile-card" data-evidence-mobile-card>
                <div class="bayes-evidence-mobile-summary">
                    <div class="bayes-evidence-detail-title">
                        ${renderStrategyBadge(strategy.slug, strategy.name)}
                        <span class="bayes-evidence-detail-meta">Step ${strategy.sequence_index}</span>
                    </div>
                    <span class="bayes-evidence-mobile-step">#${strategy.sequence_index}</span>
                </div>
                <div class="bayes-evidence-mobile-core">
                    <div class="bayes-evidence-mobile-core-item">
                        <span>Signal</span>
                        <strong>${strategy.active ? 'Active' : 'Inactive'}</strong>
                    </div>
                    <div class="bayes-evidence-mobile-core-item">
                        <span>Strength</span>
                        <strong>${formatDecimal(strategy.strength, 2)}</strong>
                    </div>
                    <div class="bayes-evidence-mobile-core-item">
                        <span>Posterior After</span>
                        <strong>${formatPercent(strategy.posterior_after || 0)}</strong>
                    </div>
                    <div class="bayes-evidence-mobile-core-item">
                        <span>LR</span>
                        <strong>${formatDecimal(strategy.likelihood_ratio, 2)}</strong>
                    </div>
                </div>
                <button type="button" class="indicator-card-btn bayes-evidence-mobile-toggle" aria-expanded="false">Show details</button>
                <div class="bayes-evidence-mobile-detail">
                    <div class="bayes-evidence-mobile-detail-item">
                        <span>Weighted Log-LR</span>
                        <strong>${formatDecimal(strategy.weighted_log_lr, 3)}</strong>
                    </div>
                    <div class="bayes-evidence-mobile-detail-item">
                        <span>Signal State</span>
                        <strong>${strategy.active ? 'Active' : 'Inactive'}</strong>
                    </div>
                </div>
            </article>
        `;
    }

    function renderEvidencePanel(result) {
        const strategies = Array.isArray(result.strategies) ? result.strategies : [];
        const rows = strategies.map((strategy, index) => `
            <tr class="bayes-evidence-row" data-evidence-index="${index}" tabindex="0" ${strategyStyleAttr(strategy.slug)}>
                <td>${strategy.sequence_index}</td>
                <td>${renderStrategyBadge(strategy.slug, strategy.name)}</td>
                <td>
                    <span class="strategy-signal-pill ${strategy.active ? 'strategy-signal-pill-active' : 'strategy-signal-pill-inactive'}">
                        ${strategy.active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td>${formatDecimal(strategy.strength, 2)}</td>
                <td>${formatDecimal(strategy.likelihood_ratio, 2)}</td>
                <td>${formatDecimal(strategy.weighted_log_lr, 3)}</td>
                <td>${formatPercent(strategy.posterior_after || 0)}</td>
            </tr>
        `).join('');

        if (!rows) {
            return '<p class="backtest-empty-state">Evidence contributions will appear here after the first run.</p>';
        }

        const mathUrl = buildMathUrl(result);

        return `
            <div class="bayes-evidence-shell">
                <div class="bayes-panel-header">
                    <div>
                        <p class="bayes-summary-eyebrow">Evidence chain</p>
                        <h4 class="indicator-card-title">Step-by-step contribution breakdown</h4>
                    </div>
                    ${renderMathLink(mathUrl, 'Open full derivation')}
                </div>
                <div class="bayes-evidence-desktop">
                    <div class="bayes-table-wrap">
                        <table class="zebra-table bayes-data-table min-w-full text-sm text-gray-700 border border-gray-300">
                            <thead class="bg-gray-200 text-xs font-semibold">
                                <tr>
                                    <th class="px-3 py-2 text-left">Step</th>
                                    <th class="px-3 py-2 text-left">Strategy</th>
                                    <th class="px-3 py-2 text-left">Signal</th>
                                    <th class="px-3 py-2 text-left">Strength</th>
                                    <th class="px-3 py-2 text-left">LR</th>
                                    <th class="px-3 py-2 text-left">Weighted Log-LR</th>
                                    <th class="px-3 py-2 text-left">Posterior After</th>
                                </tr>
                            </thead>
                            <tbody>${rows}</tbody>
                        </table>
                    </div>
                    <div class="bayes-evidence-detail" data-evidence-detail-panel>
                        ${renderEvidenceDetailMarkup(strategies[0])}
                    </div>
                </div>
                <div class="bayes-evidence-mobile-list">
                    ${strategies.map(renderEvidenceMobileCard).join('')}
                </div>
            </div>
        `;
    }

    function activateEvidenceRow(panel, strategies, index) {
        const strategy = strategies[index];
        const detailPanel = panel.querySelector('[data-evidence-detail-panel]');
        if (!strategy || !detailPanel) {
            return;
        }

        detailPanel.innerHTML = renderEvidenceDetailMarkup(strategy);
        panel.querySelectorAll('.bayes-evidence-row').forEach((row) => {
            row.classList.toggle('is-active', Number(row.dataset.evidenceIndex) === index);
        });
    }

    function bindEvidencePanelInteractions(panel, result) {
        const strategies = Array.isArray(result?.strategies) ? result.strategies : [];
        if (!panel || !strategies.length) {
            return;
        }

        panel.querySelectorAll('.bayes-evidence-row').forEach((row) => {
            const index = Number(row.dataset.evidenceIndex || 0);
            const activate = function () {
                activateEvidenceRow(panel, strategies, index);
            };
            row.addEventListener('mouseenter', activate);
            row.addEventListener('focus', activate);
            row.addEventListener('click', activate);
        });

        panel.querySelectorAll('.bayes-evidence-mobile-toggle').forEach((button) => {
            button.addEventListener('click', function () {
                const card = button.closest('[data-evidence-mobile-card]');
                if (!card) {
                    return;
                }
                const isOpen = card.classList.toggle('is-open');
                button.textContent = isOpen ? 'Hide details' : 'Show details';
                button.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            });
        });

        activateEvidenceRow(panel, strategies, 0);
    }

    function summarizeTradesByStrategy(trades) {
        const grouped = new Map();

        trades.forEach((trade) => {
            const slug = String(trade.strategy_slug || '').trim() || 'strategy';
            const current = grouped.get(slug) || {
                count: 0,
                wins: 0,
                totalPnl: 0,
            };

            current.count += 1;
            current.totalPnl += Number(trade.pnl || 0);
            if (Number(trade.pnl || 0) >= 0) {
                current.wins += 1;
            }

            grouped.set(slug, current);
        });

        return Array.from(grouped.entries());
    }

    function renderTradeLog(result) {
        const trades = Array.isArray(result.trade_log) ? result.trade_log : [];

        if (!trades.length) {
            return `
                <div class="trade-log-shell">
                    <div class="trade-log-summary trade-log-summary-empty">
                        <div class="trade-log-kpi">
                            <span class="trade-log-kpi-label">Trade count</span>
                            <strong>0</strong>
                        </div>
                        <div class="trade-log-kpi">
                            <span class="trade-log-kpi-label">Win rate</span>
                            <strong>0.00%</strong>
                        </div>
                    </div>
                    <p class="backtest-empty-state">No closed trades were generated for the current run.</p>
                </div>
            `;
        }

        const wins = trades.filter((trade) => (trade.pnl || 0) >= 0).length;
        const losses = trades.length - wins;
        const totalPnl = trades.reduce((sum, trade) => sum + Number(trade.pnl || 0), 0);
        const averageReturn = trades.reduce((sum, trade) => sum + Number(trade.return_pct || 0), 0) / trades.length;
        const strategyBreakdown = summarizeTradesByStrategy(trades);

        const breakoutMarkup = strategyBreakdown.map(([slug, stats]) => `
            <div class="trade-strategy-kpi" ${strategyStyleAttr(slug)}>
                ${renderStrategyBadge(slug)}
                <div class="trade-strategy-kpi-stats">
                    <strong>${stats.count} trades</strong>
                    <span>${stats.wins} wins · ${formatCurrency(stats.totalPnl)}</span>
                </div>
            </div>
        `).join('');

        const rows = trades.map((trade) => {
            const pnl = Number(trade.pnl || 0);
            const returnPct = Number(trade.return_pct || 0);
            const outcomeClass = pnl >= 0 ? 'trade-outcome-win' : 'trade-outcome-loss';
            const pnlClass = pnl >= 0 ? 'trade-log-positive' : 'trade-log-negative';
            return `
                <tr class="trade-log-row" ${strategyStyleAttr(trade.strategy_slug)}>
                    <td class="px-3 py-2 trade-strategy-cell">
                        <span class="trade-row-accent"></span>
                        ${renderStrategyBadge(trade.strategy_slug)}
                    </td>
                    <td class="px-3 py-2">${escapeHtml(trade.entry_date)}</td>
                    <td class="px-3 py-2">${escapeHtml(trade.exit_date || '-')}</td>
                    <td class="px-3 py-2">${formatCurrency(trade.entry_price)}</td>
                    <td class="px-3 py-2">${trade.exit_price == null ? '-' : formatCurrency(trade.exit_price)}</td>
                    <td class="px-3 py-2">${Number(trade.shares || 0).toFixed(0)}</td>
                    <td class="px-3 py-2 ${pnlClass}">${formatPercent(returnPct)}</td>
                    <td class="px-3 py-2 ${pnlClass}">${formatCurrency(pnl)}</td>
                    <td class="px-3 py-2"><span class="trade-outcome-pill ${outcomeClass}">${pnl >= 0 ? 'Win' : 'Loss'}</span></td>
                </tr>
            `;
        }).join('');

        return `
            <div class="trade-log-shell">
                <div class="trade-log-summary">
                    <div class="trade-log-kpi">
                        <span class="trade-log-kpi-label">Trade count</span>
                        <strong>${trades.length}</strong>
                    </div>
                    <div class="trade-log-kpi">
                        <span class="trade-log-kpi-label">Wins / Losses</span>
                        <strong>${wins} / ${losses}</strong>
                    </div>
                    <div class="trade-log-kpi">
                        <span class="trade-log-kpi-label">Average return</span>
                        <strong>${formatSignedPercent(averageReturn)}</strong>
                    </div>
                    <div class="trade-log-kpi">
                        <span class="trade-log-kpi-label">Total PnL</span>
                        <strong class="${totalPnl >= 0 ? 'trade-log-positive' : 'trade-log-negative'}">${formatCurrency(totalPnl)}</strong>
                    </div>
                </div>
                <div class="trade-log-breakdown">${breakoutMarkup}</div>
                <div class="trade-log-table-wrap">
                    <table class="zebra-table bayes-data-table min-w-full text-sm text-gray-700 border border-gray-300" data-responsive-table data-responsive-title-col="0" data-responsive-subtitle-col="1">
                        <thead class="bg-gray-200 text-xs font-semibold">
                            <tr>
                                <th class="px-3 py-2 text-left">Strategy</th>
                                <th class="px-3 py-2 text-left">Entry</th>
                                <th class="px-3 py-2 text-left">Exit</th>
                                <th class="px-3 py-2 text-left">Entry Price</th>
                                <th class="px-3 py-2 text-left">Exit Price</th>
                                <th class="px-3 py-2 text-left">Shares</th>
                                <th class="px-3 py-2 text-left">Return</th>
                                <th class="px-3 py-2 text-left">PnL</th>
                                <th class="px-3 py-2 text-left">Outcome</th>
                            </tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
            </div>
        `;
    }

    function renderAnalysis(result) {
        const mathUrl = buildMathUrl(result);
        const cards = (result.strategies || []).map((strategy) => `
            <div class="bayes-strategy-performance-card" ${strategyStyleAttr(strategy.slug)}>
                <div class="bayes-strategy-performance-header">
                    ${renderStrategyBadge(strategy.slug, strategy.name)}
                    ${mathUrl ? `<a class="bayes-inline-link" href="${mathUrl}">Open Math</a>` : ''}
                </div>
                <strong>${formatPercent(strategy.metrics?.win_rate || 0)}</strong>
                <span class="bayes-metric-subtext">Win rate</span>
                <div class="bayes-performance-stat-row">
                    <span>${Number(strategy.metrics?.trade_count || 0)} trades</span>
                    <span>${formatSignedPercent(strategy.metrics?.total_return_pct || 0)} total return</span>
                </div>
            </div>
        `).join('');

        return `
            <div class="bayes-performance-shell">
                <div class="bayes-panel-header">
                    <div>
                        <p class="bayes-summary-eyebrow">Performance notes</p>
                        <h4 class="indicator-card-title">Strategy metrics</h4>
                    </div>
                    ${renderMathLink(mathUrl, 'View math context')}
                </div>
                <div class="bayes-performance-grid">${cards || '<p class="backtest-empty-state">No strategy metrics available yet.</p>'}</div>
            </div>
        `;
    }

    function renderChainPanel(result) {
        const mathUrl = buildMathUrl(result);
        const earningsSummary = buildEarningsSummary(result);
        const notes = ((result.explanation || {}).notes || [])
            .map((note) => `<li>${escapeHtml(note)}</li>`)
            .join('');

        const strategies = (result.strategies || []).map((strategy) => `
            <li class="bayes-chain-item">
                ${renderStrategyBadge(strategy.slug, strategy.name)}
                <span class="bayes-chain-item-copy">
                    ${strategy.used_as_prior ? 'Used as prior' : 'Posterior after step'} · ${formatPercent(strategy.posterior_after || 0)}
                </span>
            </li>
        `).join('');

        return `
            <div class="bayes-note-stack">
                <div class="bayes-note-card">
                    <div class="bayes-panel-header">
                        <div>
                            <p class="bayes-summary-eyebrow">Chain status</p>
                            <h4 class="indicator-card-title">Posterior progression</h4>
                        </div>
                        ${renderMathLink(mathUrl, 'Open run math')}
                    </div>
                    <p class="strategy-panel-note">${escapeHtml(result.ui?.workflow_note || 'Run a strategy to establish a posterior.')}</p>
                    <p class="strategy-panel-note">${escapeHtml(`Earnings filter: ${earningsSummary.text}`)}</p>
                    <ul class="strategy-parameter-list bayes-chain-list">${strategies || '<li>No strategy chain has been executed yet.</li>'}</ul>
                </div>
                <div class="bayes-note-card">
                    <div class="bayes-panel-header">
                        <div>
                            <p class="bayes-summary-eyebrow">Posterior notes</p>
                            <h4 class="indicator-card-title">Interpretation cues</h4>
                        </div>
                    </div>
                    <ul class="strategy-parameter-list">${notes || '<li>No explanation notes returned.</li>'}</ul>
                </div>
            </div>
        `;
    }

    function renderAnalysisEmpty() {
        return `
            <div class="bayes-performance-shell">
                <div class="bayes-panel-header">
                    <div>
                        <p class="bayes-summary-eyebrow">Performance notes</p>
                        <h4 class="indicator-card-title">Strategy metrics</h4>
                    </div>
                    <span class="bayes-text-link bayes-text-link-disabled">Run required</span>
                </div>
                <div class="bayes-note-card">
                    <p class="backtest-empty-state">Strategy metrics will appear here after the first run.</p>
                </div>
            </div>
        `;
    }

    function renderChainEmpty() {
        return `
            <div class="bayes-note-stack">
                <div class="bayes-note-card">
                    <div class="bayes-panel-header">
                        <div>
                            <p class="bayes-summary-eyebrow">Chain status</p>
                            <h4 class="indicator-card-title">Posterior progression</h4>
                        </div>
                    </div>
                    <p class="backtest-empty-state">Posterior notes and chain status will appear here after the first run.</p>
                </div>
                <div class="bayes-note-card">
                    <div class="bayes-panel-header">
                        <div>
                            <p class="bayes-summary-eyebrow">Posterior notes</p>
                            <h4 class="indicator-card-title">Interpretation cues</h4>
                        </div>
                    </div>
                    <p class="backtest-empty-state">Run a strategy chain to unlock the written interpretation layer.</p>
                </div>
            </div>
        `;
    }

    function resetResults(targets) {
        if (targets.posteriorPanel) {
            targets.posteriorPanel.innerHTML = '<p class="backtest-empty-state">Prior and posterior probabilities will appear here after the first run.</p>';
        }
        if (targets.evidencePanel) {
            targets.evidencePanel.innerHTML = '<p class="backtest-empty-state">Evidence contributions will appear here after the first run.</p>';
        }
        if (targets.tradeLog) {
            targets.tradeLog.innerHTML = '<p class="backtest-empty-state">Trade log output will appear here after the first run.</p>';
        }
        if (targets.analysisPanel) {
            targets.analysisPanel.innerHTML = renderAnalysisEmpty();
        }
        if (targets.chainPanel) {
            targets.chainPanel.innerHTML = renderChainEmpty();
        }

        window.TradingProResponsive?.refreshResponsiveTables();
    }

    function renderRunResult(targets, result) {
        if (targets.posteriorPanel) {
            targets.posteriorPanel.innerHTML = renderPosteriorPanel(result);
        }
        if (targets.evidencePanel) {
            targets.evidencePanel.innerHTML = renderEvidencePanel(result);
            bindEvidencePanelInteractions(targets.evidencePanel, result);
        }
        if (targets.tradeLog) {
            targets.tradeLog.innerHTML = renderTradeLog(result);
        }
        if (targets.analysisPanel) {
            targets.analysisPanel.innerHTML = renderAnalysis(result);
        }
        if (targets.chainPanel) {
            targets.chainPanel.innerHTML = renderChainPanel(result);
        }
        if (targets.statusPill) {
            const earningsSummary = buildEarningsSummary(result);
            targets.statusPill.textContent = `${result.confidence_label || 'Posterior'} · ${formatPercent(result.posterior_probability)} · ${earningsSummary.mode}`;
        }

        window.TradingProResponsive?.refreshResponsiveTables();
    }

    window.BayesBacktestUI = {
        resetResults,
        renderRunResult,
        buildMathUrl,
    };
})();
