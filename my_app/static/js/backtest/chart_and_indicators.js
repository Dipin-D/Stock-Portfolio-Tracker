(function () {
    const OSCILLATOR_MARGINS = { top: 0.72, bottom: 0.04 };
    const DEFAULT_PRICE_MARGINS = { top: 0.05, bottom: 0.08 };
    const COMPRESSED_PRICE_MARGINS = { top: 0.05, bottom: 0.34 };
    const MAX_INDICATORS = 12;

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
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
            markerEntryLabel: 'Entry',
            markerExitLabel: 'Exit',
        };
    }

    const INDICATOR_DEFS = {
        ma: {
            label: 'Moving Average',
            pane: 'overlay',
            fields: [
                { name: 'maType', label: 'Average Type', type: 'select', default: 'sma', options: [
                    { value: 'sma', label: 'Simple (SMA)' },
                    { value: 'ema', label: 'Exponential (EMA)' },
                ]},
                { name: 'period', label: 'Period', type: 'number', default: 50, min: 1, step: 1 },
                { name: 'color', label: 'Color', type: 'color', default: '#2563eb' },
            ],
            summary(config) {
                return `${config.maType.toUpperCase()} · ${config.period}-day average`;
            },
            legendItems(config) {
                return [{
                    label: `${config.maType.toUpperCase()} ${config.period}-day line`,
                    color: config.color,
                }];
            },
            createSeries(config, rawData) {
                const data = config.maType === 'ema'
                    ? window.computeEMA(rawData, config.period)
                    : window.computeSMA(rawData, config.period);

                return [{
                    type: 'line',
                    data,
                    options: {
                        color: config.color,
                        lineWidth: 2,
                        lastValueVisible: false,
                        priceLineVisible: false,
                    },
                }];
            },
        },
        rsi: {
            label: 'Relative Strength Index',
            pane: 'oscillator',
            fields: [
                { name: 'period', label: 'Period', type: 'number', default: 14, min: 2, step: 1 },
                { name: 'overbought', label: 'Overbought Level', type: 'number', default: 70, min: 1, max: 100, step: 1 },
                { name: 'oversold', label: 'Oversold Level', type: 'number', default: 30, min: 0, max: 99, step: 1 },
                { name: 'color', label: 'RSI Color', type: 'color', default: '#7c3aed' },
            ],
            summary(config) {
                return `${config.period}-period · ${config.oversold}/${config.overbought} levels`;
            },
            legendItems(config) {
                return [
                    { label: 'RSI line', color: config.color },
                    { label: `Overbought ${config.overbought}`, color: '#ef4444' },
                    { label: `Oversold ${config.oversold}`, color: '#10b981' },
                ];
            },
            createSeries(config, rawData, indicatorId) {
                const rsi = window.computeRSI(rawData, config.period);
                const times = rsi.map((point) => point.time);
                const scaleId = `osc-rsi-${indicatorId}`;

                return [
                    oscillatorLine(rsi, config.color, scaleId),
                    oscillatorLine(window.constantLine(times, config.overbought), '#ef4444', scaleId, { lineStyle: 2, lineWidth: 1 }),
                    oscillatorLine(window.constantLine(times, config.oversold), '#10b981', scaleId, { lineStyle: 2, lineWidth: 1 }),
                ];
            },
        },
        bbands: {
            label: 'Bollinger Bands',
            pane: 'overlay',
            fields: [
                { name: 'period', label: 'Period', type: 'number', default: 20, min: 2, step: 1 },
                { name: 'stdDev', label: 'Standard Deviation', type: 'number', default: 2, min: 0.1, step: 0.1 },
                { name: 'upperColor', label: 'Upper Band Color', type: 'color', default: '#ec4899' },
                { name: 'middleColor', label: 'Middle Band Color', type: 'color', default: '#2563eb' },
                { name: 'lowerColor', label: 'Lower Band Color', type: 'color', default: '#14b8a6' },
            ],
            summary(config) {
                return `${config.period}-period · ${config.stdDev}σ`;
            },
            legendItems(config) {
                return [
                    { label: 'Upper band', color: config.upperColor },
                    { label: 'Middle band', color: config.middleColor },
                    { label: 'Lower band', color: config.lowerColor },
                ];
            },
            createSeries(config, rawData) {
                const bands = window.computeBollingerBands(rawData, config.period, config.stdDev);
                return [
                    overlayLine(bands.upper, config.upperColor),
                    overlayLine(bands.middle, config.middleColor, { lineStyle: 2 }),
                    overlayLine(bands.lower, config.lowerColor),
                ];
            },
        },
        stoch: {
            label: 'Stochastic Oscillator',
            pane: 'oscillator',
            fields: [
                { name: 'kPeriod', label: '%K Period', type: 'number', default: 14, min: 2, step: 1 },
                { name: 'smoothK', label: 'Smooth %K', type: 'number', default: 3, min: 1, step: 1 },
                { name: 'dPeriod', label: '%D Period', type: 'number', default: 3, min: 1, step: 1 },
                { name: 'upperLevel', label: 'Upper Level', type: 'number', default: 80, min: 0, max: 100, step: 1 },
                { name: 'lowerLevel', label: 'Lower Level', type: 'number', default: 20, min: 0, max: 100, step: 1 },
                { name: 'kColor', label: '%K Color', type: 'color', default: '#f59e0b' },
                { name: 'dColor', label: '%D Color', type: 'color', default: '#2563eb' },
            ],
            summary(config) {
                return `%K ${config.kPeriod} · smooth ${config.smoothK} · %D ${config.dPeriod}`;
            },
            legendItems(config) {
                return [
                    { label: '%K line', color: config.kColor },
                    { label: '%D line', color: config.dColor },
                    { label: `Upper level ${config.upperLevel}`, color: '#ef4444' },
                    { label: `Lower level ${config.lowerLevel}`, color: '#10b981' },
                ];
            },
            createSeries(config, rawData, indicatorId) {
                const stoch = window.computeStochasticOscillator(rawData, config.kPeriod, config.smoothK, config.dPeriod);
                const times = stoch.k.map((point) => point.time);
                const scaleId = `osc-stoch-${indicatorId}`;

                return [
                    oscillatorLine(stoch.k, config.kColor, scaleId),
                    oscillatorLine(stoch.d, config.dColor, scaleId),
                    oscillatorLine(window.constantLine(times, config.upperLevel), '#ef4444', scaleId, { lineStyle: 2, lineWidth: 1 }),
                    oscillatorLine(window.constantLine(times, config.lowerLevel), '#10b981', scaleId, { lineStyle: 2, lineWidth: 1 }),
                ];
            },
        },
        adx: {
            label: 'Average Directional Index',
            pane: 'oscillator',
            fields: [
                { name: 'period', label: 'Period', type: 'number', default: 14, min: 2, step: 1 },
                { name: 'threshold', label: 'Trend Threshold', type: 'number', default: 25, min: 1, step: 1 },
                { name: 'adxColor', label: 'ADX Color', type: 'color', default: '#111827' },
                { name: 'plusColor', label: '+DI Color', type: 'color', default: '#16a34a' },
                { name: 'minusColor', label: '-DI Color', type: 'color', default: '#dc2626' },
            ],
            summary(config) {
                return `${config.period}-period · threshold ${config.threshold}`;
            },
            legendItems(config) {
                return [
                    { label: 'ADX line', color: config.adxColor },
                    { label: '+DI line', color: config.plusColor },
                    { label: '-DI line', color: config.minusColor },
                    { label: `Trend threshold ${config.threshold}`, color: '#f59e0b' },
                ];
            },
            createSeries(config, rawData, indicatorId) {
                const adx = window.computeADX(rawData, config.period);
                const times = adx.adx.map((point) => point.time);
                const scaleId = `osc-adx-${indicatorId}`;

                return [
                    oscillatorLine(adx.adx, config.adxColor, scaleId),
                    oscillatorLine(adx.plusDI, config.plusColor, scaleId),
                    oscillatorLine(adx.minusDI, config.minusColor, scaleId),
                    oscillatorLine(window.constantLine(times, config.threshold), '#f59e0b', scaleId, { lineStyle: 2, lineWidth: 1 }),
                ];
            },
        },
        ichimoku: {
            label: 'Ichimoku Cloud',
            pane: 'overlay',
            fields: [
                { name: 'conversionPeriod', label: 'Conversion Period', type: 'number', default: 9, min: 2, step: 1 },
                { name: 'basePeriod', label: 'Base Period', type: 'number', default: 26, min: 2, step: 1 },
                { name: 'spanBPeriod', label: 'Span B Period', type: 'number', default: 52, min: 2, step: 1 },
                { name: 'displacement', label: 'Displacement', type: 'number', default: 26, min: 1, step: 1 },
                { name: 'conversionColor', label: 'Conversion Color', type: 'color', default: '#2563eb' },
                { name: 'baseColor', label: 'Base Color', type: 'color', default: '#f97316' },
                { name: 'spanAColor', label: 'Span A Color', type: 'color', default: '#16a34a' },
                { name: 'spanBColor', label: 'Span B Color', type: 'color', default: '#dc2626' },
                { name: 'laggingColor', label: 'Lagging Span Color', type: 'color', default: '#7c3aed' },
            ],
            summary(config) {
                return `${config.conversionPeriod}/${config.basePeriod}/${config.spanBPeriod} · shift ${config.displacement}`;
            },
            legendItems(config) {
                return [
                    { label: 'Conversion line', color: config.conversionColor },
                    { label: 'Base line', color: config.baseColor },
                    { label: 'Span A', color: config.spanAColor },
                    { label: 'Span B', color: config.spanBColor },
                    { label: 'Lagging span', color: config.laggingColor },
                ];
            },
            createSeries(config, rawData) {
                const cloud = window.computeIchimokuCloud(
                    rawData,
                    config.conversionPeriod,
                    config.basePeriod,
                    config.spanBPeriod,
                    config.displacement
                );

                return [
                    overlayLine(cloud.conversion, config.conversionColor),
                    overlayLine(cloud.base, config.baseColor),
                    overlayLine(cloud.spanA, config.spanAColor, { lineStyle: 2 }),
                    overlayLine(cloud.spanB, config.spanBColor, { lineStyle: 2 }),
                    overlayLine(cloud.lagging, config.laggingColor, { lineStyle: 3 }),
                ];
            },
        },
        psar: {
            label: 'Parabolic SAR',
            pane: 'overlay',
            fields: [
                { name: 'step', label: 'Acceleration Step', type: 'number', default: 0.02, min: 0.001, step: 0.001 },
                { name: 'maxStep', label: 'Maximum Step', type: 'number', default: 0.2, min: 0.01, step: 0.01 },
                { name: 'color', label: 'SAR Color', type: 'color', default: '#0f172a' },
            ],
            summary(config) {
                return `step ${config.step} · max ${config.maxStep}`;
            },
            legendItems(config) {
                return [
                    { label: 'SAR dots', color: config.color },
                ];
            },
            createSeries(config, rawData) {
                const psar = window.computeParabolicSAR(rawData, config.step, config.maxStep);
                return [overlayLine(psar, config.color, { lineStyle: 3, lineWidth: 1 })];
            },
        },
        obv: {
            label: 'On-Balance Volume',
            pane: 'oscillator',
            fields: [
                { name: 'signalPeriod', label: 'Signal Period', type: 'number', default: 20, min: 1, step: 1 },
                { name: 'color', label: 'OBV Color', type: 'color', default: '#0f172a' },
                { name: 'signalColor', label: 'Signal Color', type: 'color', default: '#2563eb' },
            ],
            summary(config) {
                return `signal ${config.signalPeriod}`;
            },
            legendItems(config) {
                return [
                    { label: 'OBV line', color: config.color },
                    { label: 'Signal line', color: config.signalColor },
                ];
            },
            createSeries(config, rawData, indicatorId) {
                const obv = window.computeOBV(rawData, config.signalPeriod);
                const scaleId = `osc-obv-${indicatorId}`;

                return [
                    oscillatorLine(obv.obv, config.color, scaleId),
                    oscillatorLine(obv.signal, config.signalColor, scaleId, { lineStyle: 2 }),
                ];
            },
        },
    };

    function overlayLine(data, color, extraOptions = {}) {
        return {
            type: 'line',
            data,
            options: Object.assign({
                color,
                lineWidth: 2,
                lastValueVisible: false,
                priceLineVisible: false,
            }, extraOptions),
        };
    }

    function oscillatorLine(data, color, priceScaleId, extraOptions = {}) {
        return {
            type: 'line',
            data,
            options: Object.assign({
                color,
                lineWidth: 2,
                lastValueVisible: false,
                priceLineVisible: false,
                priceScaleId,
            }, extraOptions),
            scaleMargins: OSCILLATOR_MARGINS,
        };
    }

    function collectDefaultConfig(definition) {
        return definition.fields.reduce((accumulator, field) => {
            accumulator[field.name] = field.default;
            return accumulator;
        }, {});
    }

    function coerceFieldValue(field, value) {
        if (field.type === 'number') {
            return Number(value);
        }
        return value;
    }

    function buildFieldMarkup(field, value) {
        if (field.type === 'select') {
            const optionsMarkup = field.options
                .map((option) => {
                    const selected = option.value === value ? 'selected' : '';
                    return `<option value="${option.value}" ${selected}>${option.label}</option>`;
                })
                .join('');

            return `
                <label class="indicator-field">
                    <span>${field.label}</span>
                    <select name="${field.name}" class="indicator-input indicator-select-input">
                        ${optionsMarkup}
                    </select>
                </label>
            `;
        }

        if (field.type === 'color') {
            return `
                <label class="indicator-field">
                    <span>${field.label}</span>
                    <input type="color" name="${field.name}" value="${value}" class="indicator-input indicator-color-input">
                </label>
            `;
        }

        const min = field.min !== undefined ? `min="${field.min}"` : '';
        const max = field.max !== undefined ? `max="${field.max}"` : '';
        const step = field.step !== undefined ? `step="${field.step}"` : '';

        return `
            <label class="indicator-field">
                <span>${field.label}</span>
                <input type="number" name="${field.name}" value="${value}" ${min} ${max} ${step} class="indicator-input">
            </label>
        `;
    }

    document.addEventListener('DOMContentLoaded', function () {
        const pageChart = document.getElementById('chart');
        const indicatorPanels = document.getElementById('indicator-panels');
        const indicatorToggle = document.getElementById('indicator-toggle');
        const indicatorOptions = document.getElementById('indicator-options');
        const indicatorModal = document.getElementById('indicator-config-modal');
        const indicatorModalTitle = document.getElementById('indicator-modal-title');
        const indicatorFields = document.getElementById('indicator-modal-fields');
        const indicatorCancel = document.getElementById('indicator-cancel');
        const indicatorForm = document.getElementById('indicator-config-form');
        const indicatorSaveLabel = document.getElementById('indicator-save-label');
        const indicatorLibraryPayload = document.getElementById('indicator-encyclopedia-data');

        if (!pageChart || !indicatorPanels || !indicatorModal || !indicatorForm) {
            return;
        }

        let chart;
        let candlestickSeries;
        let nextIndicatorId = 1;
        let editingIndicatorId = null;
        let activeIndicatorKey = null;
        let indicatorModalReturnFocus = null;
        const indicatorState = new Map();
        const tickerInput = document.getElementById('ticker-input');
        const startDateInput = document.getElementById('start-date');
        const endDateInput = document.getElementById('end-date');
        const renderGraphButton = document.getElementById('render-graph-button');
        const placeholder = document.getElementById('chart-placeholder');
        const errorDiv = document.getElementById('graph-error');
        const chartLegend = document.getElementById('chart-legend');
        const pageRoot = pageChart.closest('.backtest-page');
        const defaultRenderButtonLabel = renderGraphButton ? renderGraphButton.textContent : 'Start Backtest';

        window.rawChartData = [];
        window.currentTicker = '';
        window.backtestStartDate = '';
        window.backtestEndDate = '';
        let latestBayesResult = null;
        let indicatorInfoBySlug = {};

        if (indicatorLibraryPayload?.textContent) {
            try {
                const parsed = JSON.parse(indicatorLibraryPayload.textContent);
                if (Array.isArray(parsed)) {
                    indicatorInfoBySlug = parsed.reduce((accumulator, item) => {
                        if (item?.slug) {
                            accumulator[item.slug] = item;
                        }
                        return accumulator;
                    }, {});
                }
            } catch (error) {
                console.warn('Indicator encyclopedia payload could not be parsed.', error);
            }
        }

        function isPhoneLayout() {
            return window.matchMedia('(max-width: 768px)').matches;
        }

        function formatCandles(rawData) {
            return window.normalizeCandles(rawData).map((item) => ({
                time: item.time,
                open: item.open,
                high: item.high,
                low: item.low,
                close: item.close,
            }));
        }

        function createChartSeries(descriptor) {
            let series;

            if (descriptor.type === 'histogram') {
                series = chart.addHistogramSeries(descriptor.options || {});
            } else if (descriptor.type === 'area') {
                series = chart.addAreaSeries(descriptor.options || {});
            } else {
                series = chart.addLineSeries(descriptor.options || {});
            }

            series.setData(descriptor.data || []);

            if (descriptor.scaleMargins) {
                series.priceScale().applyOptions({
                    visible: false,
                    borderVisible: false,
                    scaleMargins: descriptor.scaleMargins,
                });
            }

            return series;
        }

        function removeIndicatorSeries(indicator) {
            indicator.seriesObjects.forEach((series) => {
                try {
                    chart.removeSeries(series);
                } catch (error) {
                    series.setData([]);
                }
            });
            indicator.seriesObjects = [];
        }

        function hasActiveOscillator() {
            return Array.from(indicatorState.values()).some((indicator) => indicator.applied && INDICATOR_DEFS[indicator.key].pane === 'oscillator');
        }

        function updatePriceScaleLayout() {
            if (!candlestickSeries) {
                return;
            }

            const margins = hasActiveOscillator() ? COMPRESSED_PRICE_MARGINS : DEFAULT_PRICE_MARGINS;
            candlestickSeries.priceScale().applyOptions({ scaleMargins: margins });
        }

        function buildIndicatorLegendMarkup(definition, config) {
            const items = typeof definition.legendItems === 'function' ? definition.legendItems(config) : [];

            if (!items.length) {
                return '';
            }

            return `
                <div class="indicator-color-legend">
                    ${items.map((item) => `
                        <span class="indicator-color-chip">
                            <span class="indicator-color-swatch" style="background:${escapeHtml(item.color)}"></span>
                            <span>${escapeHtml(item.label)}</span>
                        </span>
                    `).join('')}
                </div>
            `;
        }

        function buildIndicatorPreviewMarkup(indicatorKey) {
            const info = indicatorInfoBySlug[indicatorKey];
            if (!info) {
                return `
                    <a class="indicator-info-preview-card" href="/indicators/">
                        <strong>Indicator encyclopedia</strong>
                        <p>Open the standalone indicator reference page for the full math, history, significance, and strategy pairing notes.</p>
                        <span class="indicator-info-preview-link">Open encyclopedia ↗</span>
                    </a>
                `;
            }

            const firstLink = Array.isArray(info.external_links) && info.external_links.length ? info.external_links[0] : null;
            const externalPreview = firstLink ? `
                <div class="indicator-info-preview-external">
                    <strong>${escapeHtml(firstLink.title)}</strong>
                    <p>${escapeHtml(firstLink.preview)}</p>
                </div>
            ` : '';

            return `
                <a class="indicator-info-preview-card" href="/indicators/#${encodeURIComponent(info.slug)}">
                    <strong>${escapeHtml(info.name)}</strong>
                    <p>${escapeHtml(info.preview || info.what_it_measures || '')}</p>
                    ${externalPreview}
                    <span class="indicator-info-preview-link">Open full indicator page ↗</span>
                </a>
            `;
        }

        function updatePanel(indicator) {
            const definition = INDICATOR_DEFS[indicator.key];
            const status = indicator.element.querySelector('[data-role="indicator-status"]');
            const summary = indicator.element.querySelector('[data-role="indicator-summary"]');
            const legend = indicator.element.querySelector('[data-role="indicator-legend"]');
            const applyButton = indicator.element.querySelector('[data-role="indicator-apply"]');
            const preview = indicator.element.querySelector('[data-role="indicator-preview"]');

            status.textContent = indicator.applied ? 'Applied to chart' : 'Ready to apply';
            summary.textContent = definition.summary(indicator.config);
            if (legend) {
                legend.innerHTML = buildIndicatorLegendMarkup(definition, indicator.config);
            }
            if (preview) {
                preview.innerHTML = buildIndicatorPreviewMarkup(indicator.key);
            }
            applyButton.textContent = indicator.applied ? 'Reapply' : 'Apply';
        }

        function renderIndicatorOnChart(indicator) {
            removeIndicatorSeries(indicator);

            const definition = INDICATOR_DEFS[indicator.key];
            const descriptors = definition.createSeries(indicator.config, window.rawChartData, indicator.id);
            const hasData = descriptors.some((descriptor) => Array.isArray(descriptor.data) && descriptor.data.length);

            if (!hasData) {
                indicator.applied = false;
                updatePanel(indicator);
                updatePriceScaleLayout();
                renderChartLegend();
                alert(`Not enough chart data to compute ${definition.label}.`);
                return;
            }

            indicator.seriesObjects = descriptors.map(createChartSeries);
            indicator.applied = true;
            updatePanel(indicator);
            updatePriceScaleLayout();
            renderChartLegend();
        }

        function rerenderAppliedIndicators() {
            indicatorState.forEach((indicator) => {
                if (indicator.applied) {
                    renderIndicatorOnChart(indicator);
                }
            });
        }

        function resultMatchesCurrentChart(result) {
            if (!result) {
                return false;
            }

            return String(result.ticker || '').trim().toUpperCase() === window.currentTicker
                && String(result.start_date || '') === String(window.backtestStartDate || '')
                && String(result.end_date || '') === String(window.backtestEndDate || '')
                && Array.isArray(window.rawChartData)
                && window.rawChartData.length > 0;
        }

        function clearTradeMarkers() {
            if (candlestickSeries && typeof candlestickSeries.setMarkers === 'function') {
                candlestickSeries.setMarkers([]);
            }
        }

        function buildTradeMarkers(result) {
            const trades = Array.isArray(result?.trade_log) ? result.trade_log : [];
            const knownTimes = new Set(window.normalizeCandles(window.rawChartData).map((item) => item.time));
            const groupedMarkers = new Map();

            function pushMarker(dateValue, kind, trade) {
                if (!dateValue || !knownTimes.has(dateValue)) {
                    return;
                }

                const key = `${dateValue}|${kind}`;
                const markerGroup = groupedMarkers.get(key) || {
                    time: dateValue,
                    kind,
                    visuals: new Map(),
                };
                const visual = getStrategyVisual(trade.strategy_slug);
                markerGroup.visuals.set(visual.shortLabel, visual);
                groupedMarkers.set(key, markerGroup);
            }

            trades.forEach((trade) => {
                pushMarker(trade.entry_date, 'entry', trade);
                pushMarker(trade.exit_date, 'exit', trade);
            });

            return Array.from(groupedMarkers.values())
                .sort((left, right) => left.time.localeCompare(right.time) || left.kind.localeCompare(right.kind))
                .map((group) => {
                    const visuals = Array.from(group.visuals.values());
                    const grouped = visuals.length > 1;
                    const label = visuals.map((item) => item.shortLabel).join('+');

                    return {
                        time: group.time,
                        position: group.kind === 'entry' ? 'belowBar' : 'aboveBar',
                        shape: group.kind === 'entry' ? 'arrowUp' : 'arrowDown',
                        color: grouped ? '#334155' : visuals[0].color,
                        text: `${label} ${group.kind === 'entry' ? 'Buy' : 'Exit'}`,
                    };
                });
        }

        function renderChartLegend() {
            if (!chartLegend) {
                return;
            }

            const movingAverageItems = Array.from(indicatorState.values())
                .filter((indicator) => indicator.applied && indicator.key === 'ma')
                .sort((left, right) => Number(left.config.period) - Number(right.config.period))
                .map((indicator) => ({
                    label: `${indicator.config.maType.toUpperCase()} ${indicator.config.period}-day`,
                    color: indicator.config.color,
                    type: 'line',
                }));

            const strategyItems = resultMatchesCurrentChart(latestBayesResult)
                ? Array.from(new Map(
                    (latestBayesResult.trade_log || []).map((trade) => [trade.strategy_slug, getStrategyVisual(trade.strategy_slug)])
                ).values()).map((visual) => ({
                    label: `${visual.name} trades`,
                    color: visual.color,
                    type: 'strategy',
                }))
                : [];

            const markerItems = strategyItems.length
                ? [
                    { label: 'Entry marker', type: 'entry' },
                    { label: 'Exit marker', type: 'exit' },
                ]
                : [];

            const items = [...movingAverageItems, ...strategyItems, ...markerItems];

            if (!items.length) {
                chartLegend.innerHTML = '<span class="chart-legend-empty">Apply moving averages or run a strategy to populate the chart legend.</span>';
                return;
            }

            chartLegend.innerHTML = items.map((item) => {
                if (item.type === 'entry') {
                    return `
                        <span class="chart-legend-chip chart-legend-chip-marker">
                            <span class="chart-legend-icon chart-legend-icon-entry">↑</span>
                            <span>${escapeHtml(item.label)}</span>
                        </span>
                    `;
                }

                if (item.type === 'exit') {
                    return `
                        <span class="chart-legend-chip chart-legend-chip-marker">
                            <span class="chart-legend-icon chart-legend-icon-exit">↓</span>
                            <span>${escapeHtml(item.label)}</span>
                        </span>
                    `;
                }

                return `
                    <span class="chart-legend-chip">
                        <span class="chart-legend-swatch" style="background:${escapeHtml(item.color)}"></span>
                        <span>${escapeHtml(item.label)}</span>
                    </span>
                `;
            }).join('');
        }

        function applyTradeMarkers(result) {
            if (!candlestickSeries || typeof candlestickSeries.setMarkers !== 'function') {
                return;
            }

            if (!resultMatchesCurrentChart(result)) {
                clearTradeMarkers();
                renderChartLegend();
                return;
            }

            candlestickSeries.setMarkers(buildTradeMarkers(result));
            renderChartLegend();
        }

        function createIndicatorPanel(indicatorKey, config, existingIndicator) {
            const definition = INDICATOR_DEFS[indicatorKey];
            const indicator = existingIndicator || {
                id: nextIndicatorId,
                key: indicatorKey,
                config,
                applied: false,
                seriesObjects: [],
                element: null,
            };

            if (!existingIndicator) {
                nextIndicatorId += 1;
            }

            if (!indicator.element) {
                const panel = document.createElement('article');
                panel.className = 'indicator-card';
                panel.innerHTML = `
                    <div class="indicator-card-header">
                        <div>
                            <p class="indicator-card-title">${definition.label}</p>
                            <p class="indicator-card-status" data-role="indicator-status">Ready to apply</p>
                        </div>
                        <div class="indicator-card-actions">
                            <div class="indicator-info-wrapper">
                                <button type="button" class="indicator-card-btn indicator-card-btn-info" data-role="indicator-info" aria-expanded="false" aria-label="Indicator information">i</button>
                                <div class="indicator-info-preview" data-role="indicator-preview"></div>
                            </div>
                            <button type="button" class="indicator-card-btn indicator-card-btn-primary" data-role="indicator-apply">Apply</button>
                            <button type="button" class="indicator-card-btn" data-role="indicator-edit">Edit</button>
                            <button type="button" class="indicator-card-btn indicator-card-btn-danger" data-role="indicator-delete">Delete</button>
                        </div>
                    </div>
                    <p class="indicator-card-summary" data-role="indicator-summary"></p>
                    <div class="indicator-card-legend" data-role="indicator-legend"></div>
                `;

                panel.querySelector('[data-role="indicator-apply"]').addEventListener('click', function () {
                    if (!window.rawChartData.length) {
                        alert('Load a ticker and date range before applying indicators.');
                        return;
                    }
                    renderIndicatorOnChart(indicator);
                });

                panel.querySelector('[data-role="indicator-edit"]').addEventListener('click', function () {
                    openIndicatorModal(indicator.key, indicator);
                });

                panel.querySelector('[data-role="indicator-delete"]').addEventListener('click', function () {
                    removeIndicatorSeries(indicator);
                    indicatorState.delete(indicator.id);
                    indicator.element.remove();
                    updatePriceScaleLayout();
                    renderChartLegend();
                });

                const infoWrapper = panel.querySelector('.indicator-info-wrapper');
                const infoButton = panel.querySelector('[data-role="indicator-info"]');
                const preview = panel.querySelector('[data-role="indicator-preview"]');

                function setPreviewVisible(visible) {
                    preview.classList.toggle('is-visible', visible);
                    infoButton.setAttribute('aria-expanded', visible ? 'true' : 'false');
                }

                if (infoWrapper && infoButton && preview) {
                    const openPreview = function () {
                        setPreviewVisible(true);
                    };
                    const closePreview = function () {
                        setPreviewVisible(false);
                    };

                    infoWrapper.addEventListener('mouseenter', function () {
                        if (!isPhoneLayout()) {
                            openPreview();
                        }
                    });

                    infoWrapper.addEventListener('mouseleave', function () {
                        if (!isPhoneLayout()) {
                            closePreview();
                        }
                    });

                    infoButton.addEventListener('focus', openPreview);
                    infoButton.addEventListener('click', function (event) {
                        if (isPhoneLayout()) {
                            event.preventDefault();
                            setPreviewVisible(!preview.classList.contains('is-visible'));
                            return;
                        }
                        openPreview();
                    });

                    document.addEventListener('click', function (event) {
                        if (!infoWrapper.contains(event.target)) {
                            closePreview();
                        }
                    });
                }

                indicator.element = panel;
                indicatorPanels.appendChild(panel);
            }

            indicator.key = indicatorKey;
            indicator.config = config;
            indicator.element.querySelector('.indicator-card-title').textContent = definition.label;
            updatePanel(indicator);
            indicatorState.set(indicator.id, indicator);

            if (indicator.applied && window.rawChartData.length) {
                renderIndicatorOnChart(indicator);
            }
        }

        function closeIndicatorModal() {
            const returnFocusTarget = indicatorModal.contains(document.activeElement)
                ? (indicatorModalReturnFocus || indicatorToggle)
                : null;
            indicatorModal.classList.add('hidden');
            indicatorModal.setAttribute('aria-hidden', 'true');
            indicatorModal.setAttribute('inert', '');
            editingIndicatorId = null;
            activeIndicatorKey = null;
            if (returnFocusTarget && typeof returnFocusTarget.focus === 'function') {
                window.requestAnimationFrame(() => returnFocusTarget.focus());
            }
        }

        function openIndicatorModal(indicatorKey, existingIndicator = null) {
            const definition = INDICATOR_DEFS[indicatorKey];
            const config = existingIndicator ? existingIndicator.config : collectDefaultConfig(definition);

            indicatorModalReturnFocus = document.activeElement instanceof HTMLElement
                ? document.activeElement
                : indicatorToggle;
            activeIndicatorKey = indicatorKey;
            editingIndicatorId = existingIndicator ? existingIndicator.id : null;
            indicatorModalTitle.textContent = existingIndicator
                ? `Edit ${definition.label}`
                : `Add ${definition.label}`;
            indicatorSaveLabel.textContent = existingIndicator ? 'Save Changes' : 'Create Panel';
            indicatorFields.innerHTML = definition.fields
                .map((field) => buildFieldMarkup(field, config[field.name]))
                .join('');

            indicatorModal.classList.remove('hidden');
            indicatorModal.removeAttribute('inert');
            indicatorModal.setAttribute('aria-hidden', 'false');
            window.requestAnimationFrame(() => {
                indicatorFields.querySelector('input, select')?.focus();
            });
        }

        function collectConfigFromModal(indicatorKey) {
            const definition = INDICATOR_DEFS[indicatorKey];
            const formData = new FormData(indicatorForm);

            return definition.fields.reduce((accumulator, field) => {
                accumulator[field.name] = coerceFieldValue(field, formData.get(field.name));
                return accumulator;
            }, {});
        }

        function clearError() {
            errorDiv.textContent = '';
            errorDiv.style.display = 'none';
            errorDiv.classList.add('hidden');
        }

        function showPlaceholder(message) {
            placeholder.textContent = message;
            placeholder.style.display = 'flex';
        }

        function hidePlaceholder() {
            placeholder.style.display = 'none';
        }

        function setRenderButtonState(isLoading) {
            if (!renderGraphButton) {
                return;
            }

            renderGraphButton.disabled = isLoading;
            renderGraphButton.textContent = isLoading ? 'Loading...' : defaultRenderButtonLabel;
        }

        function showError(message) {
            errorDiv.textContent = message;
            errorDiv.classList.remove('hidden');
            errorDiv.style.display = 'flex';
        }

        function syncBacktestUrl(ticker, startDate, endDate, autoload = true) {
            const params = new URLSearchParams(window.location.search);

            if (ticker) {
                params.set('ticker', ticker);
            } else {
                params.delete('ticker');
            }

            if (startDate) {
                params.set('start_date', startDate);
            } else {
                params.delete('start_date');
            }

            if (endDate) {
                params.set('end_date', endDate);
            } else {
                params.delete('end_date');
            }

            if (autoload) {
                params.set('autoload', '1');
            } else {
                params.delete('autoload');
            }

            const query = params.toString();
            const nextUrl = query ? `${window.location.pathname}?${query}` : window.location.pathname;
            window.history.replaceState({}, '', nextUrl);
        }

        function prefillFromQuery() {
            const params = new URLSearchParams(window.location.search);
            const ticker = (pageRoot?.dataset.initialTicker || params.get('ticker') || '').trim().toUpperCase();
            const startDate = pageRoot?.dataset.initialStartDate || params.get('start_date') || '';
            const endDate = pageRoot?.dataset.initialEndDate || params.get('end_date') || '';
            const autoload = ['1', 'true', 'yes'].includes(
                (pageRoot?.dataset.initialAutoload || params.get('autoload') || '').toLowerCase()
            );

            if (ticker) {
                tickerInput.value = ticker;
            }

            if (startDate) {
                startDateInput.value = startDate;
            }

            if (endDate) {
                endDateInput.value = endDate;
            }

            return {
                shouldAutoload: autoload && ticker && startDate && endDate,
            };
        }

        async function fetchData() {
            const ticker = tickerInput.value.trim().toUpperCase();
            const startDate = startDateInput.value;
            const endDate = endDateInput.value;

            clearError();
            tickerInput.value = ticker;

            if (!ticker || !startDate || !endDate) {
                syncBacktestUrl(ticker, startDate, endDate, false);
                window.rawChartData = [];
                window.currentTicker = ticker;
                window.backtestStartDate = startDate;
                window.backtestEndDate = endDate;
                candlestickSeries.setData([]);
                clearTradeMarkers();
                renderChartLegend();
                showPlaceholder('Enter ticker and date range to display chart');
                window.dispatchEvent(new CustomEvent('backtest:chart-error', {
                    detail: { ticker, startDate, endDate, error: 'Ticker and date range are required.' },
                }));
                return false;
            }

            try {
                setRenderButtonState(true);
                showPlaceholder(`Loading ${ticker} chart data...`);
                candlestickSeries.setData([]);
                clearTradeMarkers();
                window.rawChartData = [];
                window.currentTicker = ticker;
                window.backtestStartDate = startDate;
                window.backtestEndDate = endDate;
                syncBacktestUrl(ticker, startDate, endDate, true);
                const response = await fetch(`/fetch_stock_data/?ticker=${ticker}&start_date=${startDate}&end_date=${endDate}`);
                let data;

                try {
                    data = await response.json();
                } catch (error) {
                    throw new Error('Backtest data endpoint returned an invalid response.');
                }

                if (!response.ok || !data.valid) {
                    throw new Error(data.error || 'Unable to load data.');
                }

                const rawData = Array.isArray(data.data) ? data.data : [];
                if (!rawData.length) {
                    throw new Error(`No price rows returned for ${ticker} in that date range.`);
                }

                const candleData = formatCandles(rawData);
                if (!candleData.length) {
                    throw new Error(`Price data for ${ticker} loaded, but it could not be rendered on the chart.`);
                }

                window.rawChartData = rawData;
                window.currentTicker = ticker;
                window.backtestStartDate = startDate;
                window.backtestEndDate = endDate;
                candlestickSeries.setData(candleData);
                hidePlaceholder();
                chart.timeScale().fitContent();
                rerenderAppliedIndicators();
                applyTradeMarkers(latestBayesResult);
                chart.resize(pageChart.clientWidth, pageChart.clientHeight);
                window.dispatchEvent(new CustomEvent('backtest:chart-loaded', {
                    detail: {
                        ticker,
                        startDate,
                        endDate,
                        rows: rawData.length,
                    },
                }));
                return true;
            } catch (error) {
                window.rawChartData = [];
                window.currentTicker = ticker;
                window.backtestStartDate = startDate;
                window.backtestEndDate = endDate;
                candlestickSeries.setData([]);
                clearTradeMarkers();
                showPlaceholder('Enter ticker and date range to display chart');
                showError(error.message || 'Unable to load chart data.');
                renderChartLegend();
                window.dispatchEvent(new CustomEvent('backtest:chart-error', {
                    detail: {
                        ticker,
                        startDate,
                        endDate,
                        error: error.message || 'Unable to load chart data.',
                    },
                }));
                return false;
            } finally {
                setRenderButtonState(false);
            }
        }

        function debounce(callback, delay = 500) {
            let timeoutId;
            return function (...args) {
                clearTimeout(timeoutId);
                timeoutId = setTimeout(() => callback.apply(this, args), delay);
            };
        }

        function setIndicatorOptionsOpen(isOpen) {
            indicatorOptions.classList.toggle('hidden', !isOpen);
            indicatorOptions.setAttribute('aria-hidden', isOpen ? 'false' : 'true');
            indicatorToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        }

        if (!window.LightweightCharts) {
            showError('Chart library failed to load.');
            return;
        }

        chart = LightweightCharts.createChart(pageChart, {
            width: pageChart.clientWidth,
            height: pageChart.clientHeight,
            layout: { background: { color: '#ffffff' }, textColor: '#0f172a' },
            grid: { vertLines: { color: '#e2e8f0' }, horzLines: { color: '#e2e8f0' } },
        });

        candlestickSeries = chart.addCandlestickSeries();
        updatePriceScaleLayout();
        showPlaceholder('Enter ticker and date range to display chart');
        renderChartLegend();
        setIndicatorOptionsOpen(false);

        indicatorToggle.addEventListener('click', function (event) {
            event.stopPropagation();
            setIndicatorOptionsOpen(indicatorOptions.classList.contains('hidden'));
        });

        document.addEventListener('click', function (event) {
            if (!event.target.closest('#indicator-options') && !event.target.closest('#indicator-toggle')) {
                setIndicatorOptionsOpen(false);
            }
        });

        indicatorOptions.querySelectorAll('[data-indicator]').forEach((button) => {
            button.addEventListener('click', function () {
                if (indicatorState.size >= MAX_INDICATORS) {
                    alert(`You can only keep ${MAX_INDICATORS} indicator panels open at once.`);
                    return;
                }

                setIndicatorOptionsOpen(false);
                openIndicatorModal(button.dataset.indicator);
            });
        });

        indicatorCancel.addEventListener('click', closeIndicatorModal);
        indicatorModal.addEventListener('click', function (event) {
            if (event.target === indicatorModal) {
                closeIndicatorModal();
            }
        });

        indicatorForm.addEventListener('submit', function (event) {
            event.preventDefault();

            if (!activeIndicatorKey) {
                return;
            }

            const config = collectConfigFromModal(activeIndicatorKey);
            const existingIndicator = editingIndicatorId ? indicatorState.get(editingIndicatorId) : null;
            createIndicatorPanel(activeIndicatorKey, config, existingIndicator || null);
            closeIndicatorModal();
        });

        tickerInput.addEventListener('input', debounce(function (event) {
            if (event.target.value.trim().length >= 3) {
                fetchData();
            }
        }));

        startDateInput.addEventListener('change', fetchData);
        endDateInput.addEventListener('change', fetchData);
        renderGraphButton.addEventListener('click', fetchData);
        window.fetchBacktestChartData = fetchData;

        const queryState = prefillFromQuery();
        if (queryState.shouldAutoload) {
            fetchData();
        }

        window.addEventListener('backtest:bayes-run-complete', function (event) {
            latestBayesResult = event.detail?.result || null;
            applyTradeMarkers(latestBayesResult);
        });

        window.addEventListener('backtest:chart-loaded', function () {
            applyTradeMarkers(latestBayesResult);
        });

        window.addEventListener('backtest:chart-error', function () {
            clearTradeMarkers();
            renderChartLegend();
        });

        window.addEventListener('resize', function () {
            chart.resize(pageChart.clientWidth, pageChart.clientHeight);
        });
    });
})();
