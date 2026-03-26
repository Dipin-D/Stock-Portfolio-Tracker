(function () {
    const FALLBACK_DEFINITIONS = {
        golden_cross: {
            slug: 'golden_cross',
            name: 'Golden Cross',
            category: 'Trend',
            default_params: {
                fast_sma: 50,
                slow_sma: 200,
                order_percentage: 100,
                starting_cash: 100000,
                override_shares: null,
            },
        },
        momentum_12m: {
            slug: 'momentum_12m',
            name: 'Momentum 12M',
            category: 'Trend',
            default_params: {
                lookback: 252,
                buy_threshold: 0.0,
                exit_threshold: -0.02,
                order_percentage: 100,
                starting_cash: 100000,
                override_shares: null,
            },
        },
        golden_cross_bollinger_squeeze: {
            slug: 'golden_cross_bollinger_squeeze',
            name: 'Golden Cross + Bollinger Squeeze',
            category: 'Trend',
            default_params: {
                fast_sma: 50,
                slow_sma: 200,
                bb_period: 20,
                bb_std_dev: 2,
                squeeze_lookback: 20,
                squeeze_quantile: 0.35,
                order_percentage: 100,
                starting_cash: 100000,
                override_shares: null,
            },
        },
        golden_cross_bollinger_breakout_confirm: {
            slug: 'golden_cross_bollinger_breakout_confirm',
            name: 'Golden Cross + Bollinger Breakout Confirm',
            category: 'Trend',
            default_params: {
                fast_sma: 50,
                slow_sma: 200,
                bb_period: 20,
                bb_std_dev: 2,
                squeeze_lookback: 20,
                squeeze_quantile: 0.35,
                order_percentage: 100,
                starting_cash: 100000,
                override_shares: null,
            },
        },
    };

    const EARNINGS_MODE_BY_OPTION = {
        'Nothing Special': 'nothing_special',
        'Never Trade Earnings': 'never_trade',
        'Only Trade Earnings': 'only_trade',
        'Custom Earnings': 'custom',
    };

    function getCookie(name) {
        const cookieValue = document.cookie
            .split(';')
            .map((cookie) => cookie.trim())
            .find((cookie) => cookie.startsWith(`${name}=`));
        return cookieValue ? decodeURIComponent(cookieValue.split('=').slice(1).join('=')) : '';
    }

    function setModalVisibility(modal, visible) {
        if (!modal) {
            return;
        }
        modal.style.display = visible ? 'flex' : 'none';
        modal.setAttribute('aria-hidden', visible ? 'false' : 'true');
    }

    function normalizeDefinitions(definitions) {
        const normalized = {};
        Object.values(FALLBACK_DEFINITIONS).forEach((definition) => {
            normalized[definition.slug] = definition;
        });
        (definitions || []).forEach((definition) => {
            normalized[definition.slug] = definition;
        });
        return normalized;
    }

    document.addEventListener('DOMContentLoaded', function () {
        const page = document.querySelector('.backtest-page');
        const strategyPanels = document.getElementById('strategy-panels');
        const posteriorPanel = document.getElementById('posterior-panel');
        const evidencePanel = document.getElementById('evidence-panel');
        const tradeLog = document.getElementById('trade-log-golden-cross');
        const analysisPanel = document.getElementById('analysis-golden-cross');
        const chainPanel = document.getElementById('bayes-chain-panel');
        const runButton = document.getElementById('run-bayes-button');
        const modeSelect = document.getElementById('analysis-mode');
        const priorModeSelect = document.getElementById('prior-mode');
        const benchmarkInput = document.getElementById('benchmark-input');
        const workflowMessage = document.getElementById('analysis-mode-help');
        const statusPill = document.getElementById('bayes-run-status');
        const tickerInput = document.getElementById('ticker-input');
        const startDateInput = document.getElementById('start-date');
        const endDateInput = document.getElementById('end-date');

        if (!strategyPanels || !runButton || !modeSelect || !priorModeSelect || !window.BayesBacktestUI) {
            return;
        }

        const gcModal = document.getElementById('golden-cross-modal');
        const gcForm = document.getElementById('golden-cross-form');
        const gcCancel = document.getElementById('gc-cancel');
        const momentumModal = document.getElementById('momentum-modal');
        const momentumForm = document.getElementById('momentum-form');
        const momentumCancel = document.getElementById('mom-cancel');
        const gcBollingerSqueezeModal = document.getElementById('golden-cross-bollinger-squeeze-modal');
        const gcBollingerSqueezeForm = document.getElementById('golden-cross-bollinger-squeeze-form');
        const gcBollingerSqueezeCancel = document.getElementById('gcbs-cancel');
        const gcBollingerBreakoutModal = document.getElementById('golden-cross-bollinger-breakout-confirm-modal');
        const gcBollingerBreakoutForm = document.getElementById('golden-cross-bollinger-breakout-confirm-form');
        const gcBollingerBreakoutCancel = document.getElementById('gcbc-cancel');

        const targets = { posteriorPanel, evidencePanel, tradeLog, analysisPanel, chainPanel, statusPill };
        window.BayesBacktestUI.resetResults(targets);

        const state = {
            definitionsBySlug: normalizeDefinitions([]),
            strategies: [],
            lastResult: null,
            editingIndex: null,
        };

        const initialAnalysisMode = page?.dataset.initialAnalysisMode || '';
        const initialPriorMode = page?.dataset.initialPriorMode || '';
        const initialPrefillStrategy = page?.dataset.initialPrefillStrategy || '';
        const initialHorizonDays = Number(page?.dataset.initialHorizonDays || 126) || 126;

        if (initialAnalysisMode && modeSelect.querySelector(`option[value="${initialAnalysisMode}"]`)) {
            modeSelect.value = initialAnalysisMode;
        }

        if (initialPriorMode && priorModeSelect.querySelector(`option[value="${initialPriorMode}"]`)) {
            priorModeSelect.value = initialPriorMode;
        }

        function dispatchBayesRunEvent(result, reason = '') {
            window.dispatchEvent(new CustomEvent('backtest:bayes-run-complete', {
                detail: {
                    result: result || null,
                    reason,
                },
            }));
        }

        function setRunButtonLabel() {
            if (!runButton) {
                return;
            }

            const configuredCount = state.strategies.length;
            if (modeSelect.value === 'single') {
                runButton.textContent = configuredCount ? 'Run Single Strategy' : 'Run Single Strategy';
                return;
            }

            const completedSteps = state.lastResult?.strategies?.length || 0;
            runButton.textContent = completedSteps && configuredCount > completedSteps
                ? 'Extend Bayesian Chain'
                : 'Run Bayesian Chain';
        }

        function activeDefinitionsCount() {
            return Object.keys(state.definitionsBySlug).length;
        }

        function resetRunState(message) {
            state.lastResult = null;
            statusPill.textContent = message || 'Waiting for posterior';
            window.BayesBacktestUI.resetResults(targets);
            dispatchBayesRunEvent(null, message || 'Waiting for posterior');
            renderStrategyPanels();
            updateWorkflowMessage();
            setRunButtonLabel();
        }

        function syncStrategyButtons() {
            document.querySelectorAll('.btn-clickable[data-strategy-slug]').forEach((button) => {
                const configured = state.strategies.some((strategy) => strategy.slug === button.dataset.strategySlug);
                button.classList.toggle('btn-clickable-active', configured);
            });
        }

        function updateWorkflowMessage() {
            const mode = modeSelect.value;
            if (mode === 'multi') {
                workflowMessage.textContent = state.lastResult
                    ? 'Multi-strategy mode: the current posterior is locked in. Add the next strategy and rerun to extend the chain.'
                    : 'Multi-strategy mode: run one strategy first to establish a posterior before adding another.';
            } else {
                workflowMessage.textContent = 'Single strategy mode: run one evidence source at a time and inspect its prior-to-posterior move.';
            }
        }

        function strategyStatus(index) {
            const completedSteps = state.lastResult?.strategies?.length || 0;
            if (index < completedSteps) {
                return {
                    badge: `Posterior captured at step ${index + 1}`,
                    note: 'This configuration is already reflected in the most recent posterior result.',
                };
            }
            if (modeSelect.value === 'multi' && index > completedSteps) {
                return {
                    badge: 'Locked',
                    note: 'Run the previous step first to unlock this strategy in the Bayesian chain.',
                };
            }
            if (modeSelect.value === 'multi' && completedSteps === index) {
                return {
                    badge: 'Ready to extend posterior',
                    note: 'This is the next strategy that will be folded into the posterior on the next run.',
                };
            }
            return {
                badge: 'Ready to run',
                note: 'This strategy will be included in the next Bayesian analysis run.',
            };
        }

        function renderStrategyPanels() {
            if (!state.strategies.length) {
                strategyPanels.innerHTML = '<p class="backtest-empty-state">Configure Golden Cross, a Bollinger-confirmed Golden Cross variant, or Momentum to create the Bayesian strategy chain.</p>';
                syncStrategyButtons();
                return;
            }

            strategyPanels.innerHTML = state.strategies.map((strategy, index) => {
                const definition = state.definitionsBySlug[strategy.slug] || FALLBACK_DEFINITIONS[strategy.slug];
                return window.BacktestStrategyPanelHelpers.buildStrategyPanelMarkup({
                    slug: strategy.slug,
                    name: definition.name,
                    params: strategy.params,
                    sequenceIndex: index + 1,
                }, strategyStatus(index));
            }).join('');

            strategyPanels.querySelectorAll('[data-action="edit"]').forEach((button, index) => {
                button.addEventListener('click', function () {
                    openStrategyEditor(index);
                });
            });

            strategyPanels.querySelectorAll('[data-action="delete"]').forEach((button, index) => {
                button.addEventListener('click', function () {
                    state.strategies.splice(index, 1);
                    resetRunState('Posterior invalidated by strategy change');
                });
            });

            syncStrategyButtons();
        }

        function canAddAnotherStrategy(slug) {
            if (!state.definitionsBySlug[slug]) {
                return { valid: false, reason: 'This Backtest build only supports the currently exposed Bayesian strategies.' };
            }

            if (state.editingIndex !== null) {
                return { valid: true };
            }

            if (modeSelect.value === 'single' && state.strategies.length >= 1) {
                return { valid: false, reason: 'Single Strategy Analysis only allows one configured strategy. Edit or remove the existing one first.' };
            }

            if (state.strategies.some((strategy) => strategy.slug === slug)) {
                return { valid: false, reason: 'That strategy is already configured. Use Edit on the existing panel.' };
            }

            if (modeSelect.value === 'multi' && state.strategies.length >= activeDefinitionsCount()) {
                return { valid: false, reason: 'All available Bayesian v1 strategies are already in the chain.' };
            }

            if (modeSelect.value === 'multi' && state.strategies.length >= 1) {
                const completedSteps = state.lastResult?.strategies?.length || 0;
                if (!state.lastResult || completedSteps < state.strategies.length) {
                    return { valid: false, reason: 'Run the current strategy chain first. Multi-strategy mode only unlocks the next strategy after a posterior result exists.' };
                }
            }

            return { valid: true };
        }

        function fillGoldenCrossForm(params) {
            document.getElementById('fast-sma').value = params.fast_sma;
            document.getElementById('slow-sma').value = params.slow_sma;
            document.getElementById('order-percentage').value = params.order_percentage;
            document.getElementById('starting-cash').value = params.starting_cash;
            document.getElementById('override-shares').value = params.override_shares ?? '';
        }

        function fillMomentumForm(params) {
            document.getElementById('mom-lookback').value = params.lookback;
            document.getElementById('mom-threshold').value = Number(params.buy_threshold || 0) * 100;
            document.getElementById('mom-exit').value = Number(params.exit_threshold || 0) * 100;
            document.getElementById('mom-order-pct').value = params.order_percentage;
            document.getElementById('mom-cash').value = params.starting_cash;
            document.getElementById('mom-override').value = params.override_shares ?? '';
        }

        function fillGoldenCrossBollingerSqueezeForm(params) {
            document.getElementById('gcbs-fast-sma').value = params.fast_sma;
            document.getElementById('gcbs-slow-sma').value = params.slow_sma;
            document.getElementById('gcbs-bb-period').value = params.bb_period;
            document.getElementById('gcbs-bb-std-dev').value = params.bb_std_dev;
            document.getElementById('gcbs-squeeze-lookback').value = params.squeeze_lookback;
            document.getElementById('gcbs-squeeze-quantile').value = params.squeeze_quantile;
            document.getElementById('gcbs-order-percentage').value = params.order_percentage;
            document.getElementById('gcbs-starting-cash').value = params.starting_cash;
            document.getElementById('gcbs-override-shares').value = params.override_shares ?? '';
        }

        function fillGoldenCrossBollingerBreakoutForm(params) {
            document.getElementById('gcbc-fast-sma').value = params.fast_sma;
            document.getElementById('gcbc-slow-sma').value = params.slow_sma;
            document.getElementById('gcbc-bb-period').value = params.bb_period;
            document.getElementById('gcbc-bb-std-dev').value = params.bb_std_dev;
            document.getElementById('gcbc-squeeze-lookback').value = params.squeeze_lookback;
            document.getElementById('gcbc-squeeze-quantile').value = params.squeeze_quantile;
            document.getElementById('gcbc-order-percentage').value = params.order_percentage;
            document.getElementById('gcbc-starting-cash').value = params.starting_cash;
            document.getElementById('gcbc-override-shares').value = params.override_shares ?? '';
        }

        function openStrategyEditor(indexOrSlug) {
            let slug = indexOrSlug;
            state.editingIndex = null;

            if (typeof indexOrSlug === 'number') {
                const existing = state.strategies[indexOrSlug];
                if (!existing) {
                    return;
                }
                slug = existing.slug;
                state.editingIndex = indexOrSlug;
            }

            const permission = canAddAnotherStrategy(slug);
            if (!permission.valid && state.editingIndex === null) {
                alert(permission.reason);
                return;
            }

            const existingParams = state.editingIndex === null
                ? (state.definitionsBySlug[slug] || FALLBACK_DEFINITIONS[slug]).default_params
                : state.strategies[state.editingIndex].params;

            if (slug === 'golden_cross') {
                fillGoldenCrossForm(existingParams);
                setModalVisibility(gcModal, true);
                return;
            }

            if (slug === 'momentum_12m') {
                fillMomentumForm(existingParams);
                setModalVisibility(momentumModal, true);
                return;
            }

            if (slug === 'golden_cross_bollinger_squeeze') {
                fillGoldenCrossBollingerSqueezeForm(existingParams);
                setModalVisibility(gcBollingerSqueezeModal, true);
                return;
            }

            if (slug === 'golden_cross_bollinger_breakout_confirm') {
                fillGoldenCrossBollingerBreakoutForm(existingParams);
                setModalVisibility(gcBollingerBreakoutModal, true);
                return;
            }
        }

        function closeModals() {
            state.editingIndex = null;
            setModalVisibility(gcModal, false);
            setModalVisibility(momentumModal, false);
            setModalVisibility(gcBollingerSqueezeModal, false);
            setModalVisibility(gcBollingerBreakoutModal, false);
        }

        function upsertStrategy(slug, params) {
            const definition = state.definitionsBySlug[slug] || FALLBACK_DEFINITIONS[slug];
            if (state.editingIndex !== null) {
                state.strategies[state.editingIndex] = { slug, params };
            } else {
                state.strategies.push({ slug, params });
            }
            closeModals();
            resetRunState(`Strategy chain updated: ${definition.name}`);
        }

        async function loadDefinitions() {
            try {
                const response = await fetch('/api/strategies/definitions/');
                const payload = await response.json();
                if (response.ok && payload.valid) {
                    state.definitionsBySlug = normalizeDefinitions(payload.strategies);
                    prefillStrategyFromQuery();
                    renderStrategyPanels();
                    updateWorkflowMessage();
                    setRunButtonLabel();
                    return;
                }
            } catch (error) {
                // Ignore and fall back to local defaults.
            }

            state.definitionsBySlug = normalizeDefinitions([]);
            prefillStrategyFromQuery();
            renderStrategyPanels();
            updateWorkflowMessage();
            setRunButtonLabel();
        }

        function prefillStrategyFromQuery() {
            if (!initialPrefillStrategy || state.strategies.length || state.lastResult) {
                return;
            }

            const definition = state.definitionsBySlug[initialPrefillStrategy] || FALLBACK_DEFINITIONS[initialPrefillStrategy];
            if (!definition) {
                return;
            }

            state.strategies = [{
                slug: definition.slug,
                params: { ...definition.default_params },
            }];
            statusPill.textContent = 'Research handoff ready';
        }

        async function ensureChartLoaded() {
            if (typeof window.fetchBacktestChartData !== 'function') {
                return true;
            }
            return window.fetchBacktestChartData();
        }

        function currentStrategyChain() {
            return state.strategies.map((strategy) => ({
                slug: strategy.slug,
                params: strategy.params,
            }));
        }

        function selectedEarningsMode() {
            const activeButton = document.querySelector('#earnings-handling .btn-clickable-active[data-option]');
            if (!activeButton) {
                return 'nothing_special';
            }
            return EARNINGS_MODE_BY_OPTION[activeButton.dataset.option] || 'nothing_special';
        }

        function buildEarningsPayload() {
            return {
                mode: selectedEarningsMode(),
                earnings_dates: [],
                blackout_before_days: 3,
                blackout_after_days: 2,
            };
        }

        function buildPayload() {
            return {
                ticker: tickerInput.value.trim().toUpperCase(),
                start_date: startDateInput.value,
                end_date: endDateInput.value,
                analysis_mode: modeSelect.value,
                prior_mode: priorModeSelect.value,
                horizon_days: initialHorizonDays,
                benchmark: benchmarkInput.value.trim().toUpperCase() || 'SPY',
                strategy_chain: currentStrategyChain(),
                earnings: buildEarningsPayload(),
            };
        }

        async function runBayesianAnalysis() {
            if (!state.strategies.length) {
                alert('Configure at least one strategy before running Bayesian analysis.');
                return;
            }

            const chartLoaded = await ensureChartLoaded();
            if (!chartLoaded && (!Array.isArray(window.rawChartData) || !window.rawChartData.length)) {
                statusPill.textContent = 'Chart load failed';
                return;
            }

            runButton.disabled = true;
            const previousLabel = runButton.textContent;
            runButton.textContent = 'Running...';
            statusPill.textContent = 'Computing posterior...';

            try {
                const response = await fetch('/api/backtest/run/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                    body: JSON.stringify(buildPayload()),
                });
                let payload;

                try {
                    payload = await response.json();
                } catch (error) {
                    if (response.status === 403) {
                        throw new Error('Run request was blocked by CSRF protection. Refresh the page and try again.');
                    }
                    throw new Error('Backtest run endpoint returned an invalid response.');
                }

                if (!response.ok || !payload.valid) {
                    throw new Error(payload.error || 'Unable to run Bayesian analysis.');
                }

                state.lastResult = payload;
                window.BayesBacktestUI.renderRunResult(targets, payload);
                dispatchBayesRunEvent(payload, 'Run completed');
                renderStrategyPanels();
                updateWorkflowMessage();
                setRunButtonLabel();
            } catch (error) {
                statusPill.textContent = 'Run failed';
                alert(error.message || 'Unable to run Bayesian analysis.');
            } finally {
                runButton.disabled = false;
                runButton.textContent = previousLabel;
            }
        }

        document.querySelectorAll('.btn-clickable[data-strategy-slug]').forEach((button) => {
            button.addEventListener('click', function () {
                openStrategyEditor(button.dataset.strategySlug);
            });
        });

        document.querySelectorAll('.btn-clickable[data-coming-soon="1"]').forEach((button) => {
            button.addEventListener('click', function () {
                alert('This Backtest build currently supports Golden Cross, the two Bollinger-confirmed Golden Cross variants, and Momentum 12M. Additional strategies come later.');
            });
        });

        modeSelect.addEventListener('change', function () {
            if (modeSelect.value === 'single' && state.strategies.length > 1) {
                state.strategies = state.strategies.slice(0, 1);
            }
            resetRunState('Analysis mode updated');
        });

        priorModeSelect.addEventListener('change', function () {
            resetRunState('Prior mode updated');
        });

        document.querySelectorAll('#earnings-handling .btn-clickable[data-option]').forEach((button) => {
            button.addEventListener('click', function () {
                resetRunState('Earnings handling updated');
            });
        });

        runButton.addEventListener('click', runBayesianAnalysis);

        if (gcCancel) {
            gcCancel.addEventListener('click', closeModals);
        }
        if (momentumCancel) {
            momentumCancel.addEventListener('click', closeModals);
        }
        if (gcBollingerSqueezeCancel) {
            gcBollingerSqueezeCancel.addEventListener('click', closeModals);
        }
        if (gcBollingerBreakoutCancel) {
            gcBollingerBreakoutCancel.addEventListener('click', closeModals);
        }

        if (gcModal) {
            gcModal.addEventListener('click', function (event) {
                if (event.target === gcModal) {
                    closeModals();
                }
            });
        }

        if (momentumModal) {
            momentumModal.addEventListener('click', function (event) {
                if (event.target === momentumModal) {
                    closeModals();
                }
            });
        }
        if (gcBollingerSqueezeModal) {
            gcBollingerSqueezeModal.addEventListener('click', function (event) {
                if (event.target === gcBollingerSqueezeModal) {
                    closeModals();
                }
            });
        }
        if (gcBollingerBreakoutModal) {
            gcBollingerBreakoutModal.addEventListener('click', function (event) {
                if (event.target === gcBollingerBreakoutModal) {
                    closeModals();
                }
            });
        }

        if (gcForm) {
            gcForm.addEventListener('submit', function (event) {
                event.preventDefault();
                upsertStrategy('golden_cross', {
                    fast_sma: Number(document.getElementById('fast-sma').value),
                    slow_sma: Number(document.getElementById('slow-sma').value),
                    order_percentage: Number(document.getElementById('order-percentage').value),
                    starting_cash: Number(document.getElementById('starting-cash').value),
                    override_shares: document.getElementById('override-shares').value || null,
                });
            });
        }

        if (momentumForm) {
            momentumForm.addEventListener('submit', function (event) {
                event.preventDefault();
                upsertStrategy('momentum_12m', {
                    lookback: Number(document.getElementById('mom-lookback').value),
                    buy_threshold: Number(document.getElementById('mom-threshold').value) / 100,
                    exit_threshold: Number(document.getElementById('mom-exit').value) / 100,
                    order_percentage: Number(document.getElementById('mom-order-pct').value),
                    starting_cash: Number(document.getElementById('mom-cash').value),
                    override_shares: document.getElementById('mom-override').value || null,
                });
            });
        }

        if (gcBollingerSqueezeForm) {
            gcBollingerSqueezeForm.addEventListener('submit', function (event) {
                event.preventDefault();
                upsertStrategy('golden_cross_bollinger_squeeze', {
                    fast_sma: Number(document.getElementById('gcbs-fast-sma').value),
                    slow_sma: Number(document.getElementById('gcbs-slow-sma').value),
                    bb_period: Number(document.getElementById('gcbs-bb-period').value),
                    bb_std_dev: Number(document.getElementById('gcbs-bb-std-dev').value),
                    squeeze_lookback: Number(document.getElementById('gcbs-squeeze-lookback').value),
                    squeeze_quantile: Number(document.getElementById('gcbs-squeeze-quantile').value),
                    order_percentage: Number(document.getElementById('gcbs-order-percentage').value),
                    starting_cash: Number(document.getElementById('gcbs-starting-cash').value),
                    override_shares: document.getElementById('gcbs-override-shares').value || null,
                });
            });
        }

        if (gcBollingerBreakoutForm) {
            gcBollingerBreakoutForm.addEventListener('submit', function (event) {
                event.preventDefault();
                upsertStrategy('golden_cross_bollinger_breakout_confirm', {
                    fast_sma: Number(document.getElementById('gcbc-fast-sma').value),
                    slow_sma: Number(document.getElementById('gcbc-slow-sma').value),
                    bb_period: Number(document.getElementById('gcbc-bb-period').value),
                    bb_std_dev: Number(document.getElementById('gcbc-bb-std-dev').value),
                    squeeze_lookback: Number(document.getElementById('gcbc-squeeze-lookback').value),
                    squeeze_quantile: Number(document.getElementById('gcbc-squeeze-quantile').value),
                    order_percentage: Number(document.getElementById('gcbc-order-percentage').value),
                    starting_cash: Number(document.getElementById('gcbc-starting-cash').value),
                    override_shares: document.getElementById('gcbc-override-shares').value || null,
                });
            });
        }

        window.addEventListener('backtest:chart-error', function (event) {
            if (event.detail?.error) {
                statusPill.textContent = 'Chart data unavailable';
            }
        });

        renderStrategyPanels();
        updateWorkflowMessage();
        setRunButtonLabel();
        loadDefinitions();
    });
})();
