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
        return Number.isFinite(value) ? `${value.toFixed(digits)}%` : '-';
    }

    function formatDecimal(value, digits = 2) {
        return Number.isFinite(value) ? value.toFixed(digits) : '-';
    }

    function numericValue(value) {
        if (typeof value === 'number' && Number.isFinite(value)) {
            return value;
        }

        const parsed = parseFloat(String(value || '').replace(/[,%$]/g, '').trim());
        return Number.isFinite(parsed) ? parsed : null;
    }

    function getCookie(name) {
        const cookieValue = document.cookie
            .split(';')
            .map((cookie) => cookie.trim())
            .find((cookie) => cookie.startsWith(`${name}=`));
        return cookieValue ? decodeURIComponent(cookieValue.split('=').slice(1).join('=')) : '';
    }

    function strategyContextSummary(config, context) {
        if (context.type === 'portfolio') {
            return `Portfolio context: <strong>${escapeHtml(context.label)}</strong><br>Dates ${escapeHtml(config.startDate)} → ${escapeHtml(config.endDate)}<br>Capital comes from stored portfolio weights and notional balance.`;
        }

        if (context.type === 'group') {
            return `Group: <strong>${escapeHtml(context.label)}</strong><br>Dates ${escapeHtml(config.startDate)} → ${escapeHtml(config.endDate)}<br>Order ${escapeHtml(String(config.orderPct))}% · Cash ${escapeHtml(config.startCashDisplay)}`;
        }

        return 'Choose a ticker group or portfolio, then run this card.';
    }

    function createStrategyCard(title) {
        const card = document.createElement('article');
        card.className = 'proscan-strategy-card';
        card.innerHTML = `
            <h4>${escapeHtml(title)}</h4>
            <p data-role="summary"></p>
            <div class="proscan-card-actions">
                <button type="button" class="proscan-btn proscan-btn-secondary" data-role="run">Run Scan</button>
                <button type="button" class="proscan-btn proscan-btn-warning" data-role="edit">Edit</button>
                <button type="button" class="proscan-btn proscan-btn-danger" data-role="delete">Delete</button>
            </div>
        `;
        return card;
    }

    document.addEventListener('DOMContentLoaded', function () {
        const page = document.querySelector('[data-pro-scan-page]');
        if (!page) {
            return;
        }

        const table = document.getElementById('proscan-table');
        const tableBody = table ? table.querySelector('tbody') : null;
        const resultsMeta = document.getElementById('proscan-results-meta');
        const resultsCopy = document.getElementById('proscan-results-copy');
        const currentScanModeValue = document.getElementById('current-scan-mode');
        const currentScopeValue = document.getElementById('current-scope-value');
        const currentGroupValue = document.getElementById('current-group-value');
        const currentStrategyValue = document.getElementById('current-strategy-value');
        const scanStatusValue = document.getElementById('scan-status-value');
        const strategyPanelContainer = document.getElementById('strategy-panel-container');
        const queryFilter = document.getElementById('proscan-filter-query');
        const performanceFilter = document.getElementById('proscan-filter-performance');
        const minTradesFilter = document.getElementById('proscan-filter-min-trades');
        const clearFiltersButton = document.getElementById('proscan-clear-filters');
        const sortHeaders = Array.from(document.querySelectorAll('#proscan-table th[data-sort-key]'));
        const groupButtons = Array.from(document.querySelectorAll('[data-group-name]'));
        const accordionButtons = Array.from(document.querySelectorAll('[data-portfolio-list-trigger]'));
        const presetPortfolioList = document.getElementById('proscan-preset-portfolio-list');
        const savedPortfolioList = document.getElementById('proscan-saved-portfolio-list');

        const gcModal = document.getElementById('proscan-gc-modal');
        const gcForm = document.getElementById('proscan-gc-form');
        const gcCancel = document.getElementById('ps-gc-cancel');
        const gcOpenButton = document.getElementById('golden-cross-btn');

        const momentumModal = document.getElementById('proscan-momentum-modal');
        const momentumForm = document.getElementById('proscan-momentum-form');
        const momentumCancel = document.getElementById('ps-mom-cancel');
        const momentumOpenButton = document.getElementById('momentum-btn');

        const COL = {
            name: 0,
            ticker: 1,
            gcQuality: 2,
            liveGc: 3,
            consensus: 4,
            wins: 5,
            losses: 6,
            winRate: 7,
            avgTradeReturn: 8,
            totalReturn: 9,
            trades: 10,
            math: 11,
        };

        function getGroupLabel(groupName) {
            const matchingButton = groupButtons.find((button) => button.dataset.groupName === groupName);
            if (matchingButton?.dataset.groupLabel) {
                return matchingButton.dataset.groupLabel;
            }
            return String(groupName || '').replace(/-/g, ' ').trim();
        }

        const initialGroupName = (page.dataset.initialGroupName || '').trim();

        const state = {
            context: {
                type: initialGroupName ? 'group' : 'none',
                label: initialGroupName ? getGroupLabel(initialGroupName) : '',
                groupName: initialGroupName || '',
                selectionType: '',
                selectionKey: '',
                option: null,
            },
            portfolioOptions: {
                preset: [],
                saved: [],
            },
            currentSort: { key: 'gcQuality', direction: 'desc' },
        };

        function syncBrowserLocation(context) {
            if (!window.history || typeof window.history.replaceState !== 'function') {
                return;
            }

            if (context.type === 'group' && context.groupName) {
                window.history.replaceState({}, '', `/stocks/${encodeURIComponent(context.groupName)}/`);
                return;
            }

            window.history.replaceState({}, '', '/pro_scan/');
        }

        function setAccordionState(button, expanded) {
            const panelId = button?.getAttribute('aria-controls');
            const panel = panelId ? document.getElementById(panelId) : null;
            if (!button || !panel) {
                return;
            }

            button.setAttribute('aria-expanded', expanded ? 'true' : 'false');
            panel.classList.toggle('hidden', !expanded);
        }

        function collapsePortfolioAccordions(exceptType = '') {
            accordionButtons.forEach((button) => {
                const kind = button.dataset.portfolioListTrigger || '';
                setAccordionState(button, kind === exceptType && exceptType !== '');
            });
        }

        const STRATEGIES = {
            golden_cross: {
                slug: 'golden_cross',
                label: 'Golden Cross',
                modal: gcModal,
                openButton: gcOpenButton,
                buildConfig() {
                    const startCash = parseFloat(document.getElementById('ps-gc-starting-cash').value);
                    return {
                        startDate: document.getElementById('ps-gc-start-date').value,
                        endDate: document.getElementById('ps-gc-end-date').value,
                        fastSma: parseInt(document.getElementById('ps-gc-fast-sma').value, 10),
                        slowSma: parseInt(document.getElementById('ps-gc-slow-sma').value, 10),
                        orderPct: parseFloat(document.getElementById('ps-gc-order-percentage').value),
                        startCash,
                        startCashDisplay: `$${Number.isFinite(startCash) ? startCash.toLocaleString() : '0'}`,
                        overrideShares: document.getElementById('ps-gc-override-shares').value,
                    };
                },
                groupParams(config) {
                    return {
                        fast_sma: config.fastSma,
                        slow_sma: config.slowSma,
                        order_percentage: config.orderPct,
                        starting_cash: config.startCash,
                        override_shares: config.overrideShares || null,
                    };
                },
                fillConfig(config) {
                    document.getElementById('ps-gc-start-date').value = config.startDate;
                    document.getElementById('ps-gc-end-date').value = config.endDate;
                    document.getElementById('ps-gc-fast-sma').value = config.fastSma;
                    document.getElementById('ps-gc-slow-sma').value = config.slowSma;
                    document.getElementById('ps-gc-order-percentage').value = config.orderPct;
                    document.getElementById('ps-gc-starting-cash').value = config.startCash;
                    document.getElementById('ps-gc-override-shares').value = config.overrideShares || '';
                },
                portfolioParams(config) {
                    return {
                        fast_sma: config.fastSma,
                        slow_sma: config.slowSma,
                        order_percentage: config.orderPct,
                    };
                },
                modalFields: ['ps-gc-starting-cash', 'ps-gc-override-shares'],
                modalContextTitle: 'Golden Cross',
            },
            momentum_12m: {
                slug: 'momentum_12m',
                label: 'Momentum',
                modal: momentumModal,
                openButton: momentumOpenButton,
                buildConfig() {
                    const startCash = parseFloat(document.getElementById('ps-mom-starting-cash').value);
                    return {
                        startDate: document.getElementById('ps-mom-start-date').value,
                        endDate: document.getElementById('ps-mom-end-date').value,
                        lookback: parseInt(document.getElementById('ps-mom-lookback').value, 10),
                        buyPct: parseFloat(document.getElementById('ps-mom-buy-threshold').value),
                        exitPct: parseFloat(document.getElementById('ps-mom-exit-threshold').value),
                        orderPct: parseFloat(document.getElementById('ps-mom-order-percentage').value),
                        startCash,
                        startCashDisplay: `$${Number.isFinite(startCash) ? startCash.toLocaleString() : '0'}`,
                        overrideShares: document.getElementById('ps-mom-override-shares').value,
                    };
                },
                groupParams(config) {
                    return {
                        lookback: config.lookback,
                        buy_threshold: Number(config.buyPct) / 100,
                        exit_threshold: Number(config.exitPct) / 100,
                        order_percentage: config.orderPct,
                        starting_cash: config.startCash,
                        override_shares: config.overrideShares || null,
                    };
                },
                fillConfig(config) {
                    document.getElementById('ps-mom-start-date').value = config.startDate;
                    document.getElementById('ps-mom-end-date').value = config.endDate;
                    document.getElementById('ps-mom-lookback').value = config.lookback;
                    document.getElementById('ps-mom-buy-threshold').value = config.buyPct;
                    document.getElementById('ps-mom-exit-threshold').value = config.exitPct;
                    document.getElementById('ps-mom-order-percentage').value = config.orderPct;
                    document.getElementById('ps-mom-starting-cash').value = config.startCash;
                    document.getElementById('ps-mom-override-shares').value = config.overrideShares || '';
                },
                portfolioParams(config) {
                    return {
                        lookback: config.lookback,
                        buy_threshold: Number(config.buyPct) / 100,
                        exit_threshold: Number(config.exitPct) / 100,
                        order_percentage: config.orderPct,
                    };
                },
                modalFields: ['ps-mom-starting-cash', 'ps-mom-override-shares'],
                modalContextTitle: 'Momentum',
            },
        };

        function getDataRows() {
            return Array.from(tableBody?.querySelectorAll('tr:not([data-placeholder="1"])') || []);
        }

        function refreshResponsiveTables() {
            window.TradingProResponsive?.refreshResponsiveTables(document);
        }

        function renderEmptyTable(message) {
            if (!tableBody) {
                return;
            }
            tableBody.innerHTML = `
                <tr data-placeholder="1">
                    <td colspan="12" style="padding: 1.1rem; text-align: center; color: #64748b;">${escapeHtml(message)}</td>
                </tr>
            `;
            if (resultsMeta) {
                resultsMeta.textContent = message;
            }
            refreshResponsiveTables();
        }

        function updateTickerLink(row) {
            const ticker = row.dataset.ticker || row.cells[COL.ticker].textContent.trim();
            const href = row.dataset.researchUrl || `/research/${ticker}/`;
            if (ticker && href && row.dataset.rowMode !== 'portfolio') {
                row.cells[COL.ticker].innerHTML = `<a class="proscan-ticker-link" href="${href}" target="_blank" rel="noopener noreferrer">${escapeHtml(ticker)}</a>`;
            } else {
                row.cells[COL.ticker].textContent = ticker || '-';
            }
        }

        function updateMathLink(row) {
            const mathUrl = row.dataset.mathUrl || '';
            row.cells[COL.math].innerHTML = mathUrl
                ? `<a class="proscan-ticker-link" href="${escapeHtml(mathUrl)}" target="_blank" rel="noopener noreferrer">Math</a>`
                : '-';
        }

        function updateSignalColumns(row, stock = {}) {
            const gcQuality = numericValue(stock.golden_cross_quality_score);
            const liveGc = numericValue(stock.golden_cross_live_score);
            const consensus = stock.golden_cross_consensus_label || '-';
            row.cells[COL.gcQuality].textContent = gcQuality !== null ? gcQuality.toFixed(2) : '-';
            row.cells[COL.liveGc].textContent = liveGc !== null ? liveGc.toFixed(2) : '-';
            row.cells[COL.consensus].textContent = consensus;
            row.dataset.gcQuality = gcQuality !== null ? gcQuality : '';
            row.dataset.liveGc = liveGc !== null ? liveGc : '';
            row.dataset.consensus = consensus;
            row.dataset.researchUrl = stock.research_url || row.dataset.researchUrl || '';
            row.dataset.mathUrl = stock.golden_cross_math_url || row.dataset.mathUrl || '';
            updateTickerLink(row);
            updateMathLink(row);
        }

        function updateRowDataset(row, stats = {}) {
            row.dataset.name = row.dataset.name || row.cells[COL.name].textContent.trim() || '-';
            row.dataset.ticker = row.dataset.ticker || row.cells[COL.ticker].textContent.trim() || '-';
            row.dataset.wins = stats.wins ?? numericValue(row.cells[COL.wins].textContent) ?? '';
            row.dataset.losses = stats.losses ?? numericValue(row.cells[COL.losses].textContent) ?? '';
            row.dataset.winRate = stats.winRatePct ?? numericValue(row.cells[COL.winRate].textContent) ?? '';
            row.dataset.avgTradeReturn = stats.avgTradeReturnPct ?? numericValue(row.cells[COL.avgTradeReturn].textContent) ?? '';
            row.dataset.totalReturn = stats.totalReturnPct ?? numericValue(row.cells[COL.totalReturn].textContent) ?? '';
            row.dataset.trades = stats.trades ?? numericValue(row.cells[COL.trades].textContent) ?? '';
            row.dataset.hasScanData = stats.hasScanData !== undefined
                ? String(Boolean(stats.hasScanData))
                : String(row.cells[COL.totalReturn].textContent.trim() !== '-' && row.cells[COL.totalReturn].textContent.trim() !== 'No data');
        }

        function setContextLabels() {
            if (!currentScanModeValue || !currentScopeValue || !currentGroupValue) {
                return;
            }

            if (state.context.type === 'portfolio') {
                currentScanModeValue.textContent = 'Portfolio';
                currentScopeValue.textContent = state.context.label || 'No portfolio selected';
                currentGroupValue.textContent = state.context.selectionType === 'saved' ? 'Saved portfolio' : 'Preset portfolio';
                if (resultsCopy) {
                    resultsCopy.textContent = 'Portfolio mode aggregates holding-level results into one portfolio row, with holding drilldown in the last column.';
                }
                return;
            }

            if (state.context.type === 'group') {
                currentScanModeValue.textContent = 'Ticker group';
                currentScopeValue.textContent = state.context.label || 'No group selected';
                currentGroupValue.textContent = 'Ticker group';
                if (resultsCopy) {
                    resultsCopy.textContent = 'Metrics update row by row when a strategy card is run against the selected ticker group.';
                }
                return;
            }

            currentScanModeValue.textContent = 'None';
            currentScopeValue.textContent = 'None selected';
            currentGroupValue.textContent = 'None selected';
            if (resultsCopy) {
                resultsCopy.textContent = 'Choose a ticker group or portfolio, then run a strategy card to populate results.';
            }
        }

        function setActiveContextButtons() {
            groupButtons.forEach((button) => {
                button.classList.toggle('active', state.context.type === 'group' && button.dataset.groupName === state.context.groupName);
            });

            accordionButtons.forEach((button) => {
                const isSelectedContext = state.context.type === 'portfolio'
                    && button.dataset.portfolioListTrigger === state.context.selectionType;
                button.classList.toggle('is-context-selected', isSelectedContext);
            });

            document.querySelectorAll('[data-portfolio-option]').forEach((button) => {
                const active = state.context.type === 'portfolio'
                    && button.dataset.selectionType === state.context.selectionType
                    && button.dataset.selectionKey === state.context.selectionKey;
                button.classList.toggle('active', active);
            });
        }

        function setContext(context) {
            state.context = Object.assign({
                type: 'none',
                label: '',
                groupName: '',
                selectionType: '',
                selectionKey: '',
                option: null,
            }, context || {});
            syncBrowserLocation(state.context);
            setContextLabels();
            setActiveContextButtons();
        }

        function matchesFilters(row) {
            const query = (queryFilter?.value || '').trim().toLowerCase();
            const performance = performanceFilter?.value || 'all';
            const minTrades = numericValue(minTradesFilter?.value) ?? 0;
            const name = (row.dataset.name || '').toLowerCase();
            const ticker = (row.dataset.ticker || '').toLowerCase();
            const totalReturn = numericValue(row.dataset.totalReturn);
            const trades = numericValue(row.dataset.trades) ?? 0;
            const hasScanData = row.dataset.hasScanData === 'true';

            if (query && !name.includes(query) && !ticker.includes(query)) {
                return false;
            }
            if (performance === 'positive' && !(hasScanData && totalReturn !== null && totalReturn >= 0)) {
                return false;
            }
            if (performance === 'negative' && !(hasScanData && totalReturn !== null && totalReturn < 0)) {
                return false;
            }
            if (performance === 'with-data' && !hasScanData) {
                return false;
            }
            if (trades < minTrades) {
                return false;
            }
            return true;
        }

        function compareRows(left, right) {
            const { key, direction } = state.currentSort;
            const type = sortHeaders.find((header) => header.dataset.sortKey === key)?.dataset.sortType || 'text';
            const directionFactor = direction === 'asc' ? 1 : -1;
            let comparison = 0;

            if (type === 'number') {
                const leftValue = numericValue(left.dataset[key]);
                const rightValue = numericValue(right.dataset[key]);
                if (leftValue === null && rightValue === null) {
                    comparison = 0;
                } else if (leftValue === null) {
                    comparison = 1;
                } else if (rightValue === null) {
                    comparison = -1;
                } else {
                    comparison = leftValue - rightValue;
                }
            } else {
                comparison = String(left.dataset[key] || '').localeCompare(String(right.dataset[key] || ''), undefined, {
                    sensitivity: 'base',
                });
            }

            if (comparison === 0) {
                comparison = String(left.dataset.ticker || '').localeCompare(String(right.dataset.ticker || ''), undefined, {
                    sensitivity: 'base',
                });
            }

            return comparison * directionFactor;
        }

        function renderTableState() {
            if (!tableBody) {
                return;
            }

            const rows = getDataRows();
            if (!rows.length) {
                refreshResponsiveTables();
                return;
            }

            const visibleRows = [];
            rows.sort(compareRows).forEach((row) => {
                const visible = matchesFilters(row);
                row.hidden = !visible;
                if (visible) {
                    visibleRows.push(row);
                }
                tableBody.appendChild(row);
            });

            sortHeaders.forEach((header) => {
                header.dataset.sortIndicator = header.dataset.sortKey === state.currentSort.key
                    ? (state.currentSort.direction === 'asc' ? '↑' : '↓')
                    : '';
            });

            if (resultsMeta) {
                resultsMeta.textContent = visibleRows.length
                    ? `Showing ${visibleRows.length} of ${rows.length} results`
                    : 'No results match the current filters';
            }

            refreshResponsiveTables();
        }

        function ensureModalContextNote(modal, text) {
            if (!modal) {
                return;
            }
            const header = modal.querySelector('.proscan-modal-header');
            if (!header) {
                return;
            }
            let note = header.querySelector('[data-proscan-context-note]');
            if (!note) {
                note = document.createElement('p');
                note.className = 'proscan-inline-note';
                note.style.marginTop = '0.85rem';
                note.dataset.proscanContextNote = '1';
                header.appendChild(note);
            }
            if (text) {
                note.textContent = text;
                note.hidden = false;
            } else {
                note.hidden = true;
            }
        }

        function syncStrategyModalContext(strategy) {
            const modal = strategy.modal;
            const isPortfolioMode = state.context.type === 'portfolio';
            const note = isPortfolioMode
                ? `${strategy.modalContextTitle} will use the selected portfolio’s notional balance and saved sleeve weights. Starting cash and override shares are ignored in portfolio mode.`
                : '';

            ensureModalContextNote(modal, note);
            strategy.modalFields.forEach((fieldId) => {
                const input = document.getElementById(fieldId);
                if (input) {
                    input.disabled = isPortfolioMode;
                }
            });
        }

        function openModal(modal) {
            if (!modal) {
                return;
            }
            modal.classList.remove('hidden');
            modal.setAttribute('aria-hidden', 'false');
        }

        function closeModal(modal) {
            if (!modal) {
                return;
            }
            modal.classList.add('hidden');
            modal.setAttribute('aria-hidden', 'true');
        }

        function buildHoldingDrilldownMarkup(holdings) {
            const holdingCards = (holdings || []).map((holding) => `
                <div class="proscan-holding-card">
                    <div class="proscan-holding-card-header">
                        <strong>${escapeHtml(holding.ticker || '-')}</strong>
                        <span>${escapeHtml(holding.allocated_cash_display || '-')}</span>
                    </div>
                    <div class="proscan-holding-grid">
                        <div class="proscan-holding-metric">
                            <span>Weight</span>
                            <strong>${escapeHtml(String(holding.weight_pct ?? '-'))}%</strong>
                        </div>
                        <div class="proscan-holding-metric">
                            <span>Trades</span>
                            <strong>${escapeHtml(String(holding.trade_count ?? 0))}</strong>
                        </div>
                        <div class="proscan-holding-metric">
                            <span>Win Rate</span>
                            <strong>${formatPercent(Number(holding.win_rate || 0) * 100, 1)}</strong>
                        </div>
                        <div class="proscan-holding-metric">
                            <span>Total Return</span>
                            <strong>${formatPercent(Number(holding.total_return_pct || 0) * 100, 2)}</strong>
                        </div>
                    </div>
                </div>
            `).join('');

            return `
                <details class="proscan-holdings-details">
                    <summary class="proscan-holdings-summary">Holdings drilldown</summary>
                    <div class="proscan-holdings-panel">${holdingCards || '<p class="proscan-muted">No holding results yet.</p>'}</div>
                </details>
            `;
        }

        function buildGroupRow(result) {
            const hasScanData = result.status === 'ok';
            const row = document.createElement('tr');
            row.dataset.rowMode = 'group';
            row.dataset.name = result.name || '-';
            row.dataset.ticker = result.symbol || '-';
            row.innerHTML = `
                <td>${escapeHtml(result.name || '-')}</td>
                <td>${escapeHtml(result.symbol || '-')}</td>
                <td>-</td>
                <td>-</td>
                <td>-</td>
                <td>${hasScanData ? escapeHtml(String(result.wins || 0)) : '-'}</td>
                <td>${hasScanData ? escapeHtml(String(result.losses || 0)) : '-'}</td>
                <td>${hasScanData ? formatPercent(Number(result.win_rate || 0) * 100, 1) : '-'}</td>
                <td>${hasScanData ? formatPercent(Number(result.avg_trade_return || 0) * 100, 2) : '-'}</td>
                <td>${hasScanData ? formatPercent(Number(result.total_return_pct || 0) * 100, 2) : 'No data'}</td>
                <td>${hasScanData ? escapeHtml(String(result.trade_count || 0)) : '-'}</td>
                <td>-</td>
            `;
            updateSignalColumns(row, result);
            updateRowDataset(row, {
                wins: Number(result.wins || 0),
                losses: Number(result.losses || 0),
                winRatePct: Number(result.win_rate || 0) * 100,
                avgTradeReturnPct: Number(result.avg_trade_return || 0) * 100,
                totalReturnPct: Number(result.total_return_pct || 0) * 100,
                trades: Number(result.trade_count || 0),
                hasScanData,
            });
            if (hasScanData) {
                row.classList.add(Number(result.total_return_pct || 0) >= 0 ? 'scan-positive' : 'scan-negative');
            }
            return row;
        }

        function buildPortfolioRow(result) {
            const row = document.createElement('tr');
            row.dataset.rowMode = 'portfolio';
            row.dataset.name = result.portfolio_name || '-';
            row.dataset.ticker = result.selection_type === 'preset' ? 'Preset Portfolio' : 'Saved Portfolio';
            row.innerHTML = `
                <td>${escapeHtml(result.portfolio_name || '-')} ${result.is_default ? '<span class="proscan-default-marker">Default</span>' : ''}</td>
                <td>${escapeHtml(result.selection_type === 'preset' ? 'Preset Portfolio' : 'Saved Portfolio')}</td>
                <td>-</td>
                <td>-</td>
                <td>${result.is_default ? 'Default' : '-'}</td>
                <td>${escapeHtml(String(result.wins || 0))}</td>
                <td>${escapeHtml(String(result.losses || 0))}</td>
                <td>${formatPercent(Number(result.win_rate || 0) * 100, 1)}</td>
                <td>${formatPercent(Number(result.avg_trade_return || 0) * 100, 2)}</td>
                <td>${formatPercent(Number(result.total_return_pct || 0) * 100, 2)}</td>
                <td>${escapeHtml(String(result.trade_count || 0))}</td>
                <td>${buildHoldingDrilldownMarkup(result.holdings || [])}</td>
            `;
            updateRowDataset(row, {
                wins: Number(result.wins || 0),
                losses: Number(result.losses || 0),
                winRatePct: Number(result.win_rate || 0) * 100,
                avgTradeReturnPct: Number(result.avg_trade_return || 0) * 100,
                totalReturnPct: Number(result.total_return_pct || 0) * 100,
                trades: Number(result.trade_count || 0),
                hasScanData: true,
            });
            row.dataset.gcQuality = '';
            row.dataset.liveGc = '';
            row.dataset.consensus = result.is_default ? 'Default' : '-';
            row.classList.add(Number(result.total_return_pct || 0) >= 0 ? 'scan-positive' : 'scan-negative');
            return row;
        }

        function syncStrategyCardSummary(card) {
            if (!card || !card._proscanStrategy) {
                return;
            }
            const descriptor = card._proscanStrategy;
            const summaryNode = card.querySelector('[data-role="summary"]');
            if (summaryNode) {
                summaryNode.innerHTML = strategyContextSummary(descriptor.config, state.context);
            }
        }

        function bindStrategyCard(card) {
            card.querySelector('[data-role="run"]').addEventListener('click', async function () {
                if (!card._proscanStrategy) {
                    return;
                }

                if (state.context.type === 'portfolio') {
                    await runPortfolioScan(card._proscanStrategy);
                    return;
                }

                await runScanForGroup(card._proscanStrategy);
            });

            card.querySelector('[data-role="edit"]').addEventListener('click', function () {
                if (!card._proscanStrategy) {
                    return;
                }
                const descriptor = STRATEGIES[card._proscanStrategy.slug];
                if (!descriptor) {
                    return;
                }
                descriptor.fillConfig(card._proscanStrategy.config);
                syncStrategyModalContext(descriptor);
                card.remove();
                openModal(descriptor.modal);
            });

            card.querySelector('[data-role="delete"]').addEventListener('click', function () {
                card.remove();
                currentStrategyValue.textContent = 'Strategy card removed';
            });
        }

        async function runScanForGroup(strategyDescriptor) {
            if (!state.context.groupName) {
                alert('Select a ticker group first.');
                return;
            }

            scanStatusValue.textContent = `Running ${strategyDescriptor.label}...`;
            currentStrategyValue.textContent = strategyDescriptor.label;

            try {
                const response = await fetch('/api/pro-scan/run-group/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                    body: JSON.stringify({
                        group_name: state.context.groupName,
                        strategy_slug: strategyDescriptor.slug,
                        start_date: strategyDescriptor.config.startDate,
                        end_date: strategyDescriptor.config.endDate,
                        strategy_params: strategyDescriptor.groupParams(strategyDescriptor.config),
                    }),
                });
                const data = await response.json().catch(function () {
                    return {
                        valid: false,
                        error: `Group scan returned HTTP ${response.status}.`,
                    };
                });

                if (!response.ok || !data.valid) {
                    throw new Error(data.error || 'Unable to load group data.');
                }

                tableBody.innerHTML = '';
                (data.results || []).forEach((result) => {
                    tableBody.appendChild(buildGroupRow(result));
                });

                if (!data.results || !data.results.length) {
                    renderEmptyTable(data.error || `${state.context.groupName} returned no stocks to scan.`);
                    return;
                }

                state.currentSort = {
                    key: strategyDescriptor.slug === 'golden_cross' ? 'gcQuality' : 'totalReturn',
                    direction: 'desc',
                };
                scanStatusValue.textContent = `${strategyDescriptor.label} finished successfully`;
                renderTableState();
            } catch (error) {
                console.error(error);
                scanStatusValue.textContent = `Scan failed: ${error.message}`;
                alert(error.message);
            }
        }

        async function runPortfolioScan(strategyDescriptor) {
            if (state.context.type !== 'portfolio' || !state.context.selectionType || !state.context.selectionKey) {
                alert('Choose a preset or saved portfolio first.');
                return;
            }

            scanStatusValue.textContent = `Running ${strategyDescriptor.label} in portfolio mode...`;
            currentStrategyValue.textContent = `${strategyDescriptor.label} (portfolio mode)`;

            try {
                const response = await fetch('/api/pro-scan/run-portfolio/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                    body: JSON.stringify({
                        selection_type: state.context.selectionType,
                        selection_key: state.context.selectionKey,
                        strategy_slug: strategyDescriptor.slug,
                        start_date: strategyDescriptor.config.startDate,
                        end_date: strategyDescriptor.config.endDate,
                        strategy_params: strategyDescriptor.portfolioParams(strategyDescriptor.config),
                    }),
                });
                const payload = await response.json();

                if (!response.ok || !payload.valid) {
                    throw new Error(payload.error || 'Portfolio scan failed.');
                }

                tableBody.innerHTML = '';
                (payload.results || []).forEach((result) => {
                    tableBody.appendChild(buildPortfolioRow(result));
                });

                if (!payload.results || !payload.results.length) {
                    renderEmptyTable('No portfolio results were returned for this strategy.');
                    return;
                }

                state.currentSort = { key: 'totalReturn', direction: 'desc' };
                scanStatusValue.textContent = `${strategyDescriptor.label} finished successfully`;
                renderTableState();
            } catch (error) {
                console.error(error);
                scanStatusValue.textContent = `Scan failed: ${error.message}`;
                alert(error.message);
            }
        }

        function createConfiguredStrategyCard(strategySlug, config) {
            const descriptor = STRATEGIES[strategySlug];
            if (!descriptor) {
                return;
            }
            const strategyPayload = {
                slug: descriptor.slug,
                label: descriptor.label,
                config,
                groupParams: descriptor.groupParams,
                portfolioParams: descriptor.portfolioParams,
            };
            const existingCard = strategyPanelContainer.querySelector(`[data-strategy-slug="${descriptor.slug}"]`);
            if (existingCard) {
                existingCard._proscanStrategy = strategyPayload;
                syncStrategyCardSummary(existingCard);
                currentStrategyValue.textContent = `${descriptor.label} updated`;
                return;
            }

            const card = createStrategyCard(descriptor.label);
            card.dataset.strategySlug = descriptor.slug;
            card._proscanStrategy = strategyPayload;
            syncStrategyCardSummary(card);
            bindStrategyCard(card);
            strategyPanelContainer.appendChild(card);
            currentStrategyValue.textContent = descriptor.label;
        }

        function renderPortfolioOptionButton(option) {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'proscan-option-item';
            button.dataset.portfolioOption = '1';
            button.dataset.selectionType = option.type;
            button.dataset.selectionKey = option.key;
            button.innerHTML = `
                <span class="proscan-option-item-copy">
                    <span>
                        <strong>${escapeHtml(option.name)}</strong>
                        <span>${escapeHtml(String(option.ticker_count || 0))} holdings</span>
                    </span>
                    ${option.is_default ? '<span class="proscan-default-marker">Default</span>' : ''}
                </span>
            `;
            button.addEventListener('click', function () {
                sessionStorage.removeItem('tickerGroup');
                setContext({
                    type: 'portfolio',
                    label: option.name,
                    selectionType: option.type,
                    selectionKey: option.key,
                    option,
                });
                collapsePortfolioAccordions(option.type);
                renderEmptyTable(`Portfolio mode ready for ${option.name}. Run a strategy card to generate aggregated portfolio results.`);
                Array.from(strategyPanelContainer.children).forEach(syncStrategyCardSummary);
            });
            return button;
        }

        function renderPortfolioOptions() {
            presetPortfolioList.innerHTML = '';
            savedPortfolioList.innerHTML = '';

            state.portfolioOptions.preset.forEach((option) => {
                presetPortfolioList.appendChild(renderPortfolioOptionButton(option));
            });

            state.portfolioOptions.saved.forEach((option) => {
                savedPortfolioList.appendChild(renderPortfolioOptionButton(option));
            });

            if (!state.portfolioOptions.preset.length) {
                presetPortfolioList.innerHTML = '<p class="proscan-muted">No preset portfolios available.</p>';
            }

            if (!state.portfolioOptions.saved.length) {
                savedPortfolioList.innerHTML = '<p class="proscan-muted">No saved portfolios yet.</p>';
            }

            setActiveContextButtons();
        }

        async function loadPortfolioOptions() {
            try {
                const response = await fetch('/api/pro-scan/portfolio-options/');
                const payload = await response.json();
                if (!response.ok || !payload.valid) {
                    throw new Error(payload.error || 'Unable to load portfolio options.');
                }

                state.portfolioOptions.preset = payload.preset_portfolios || [];
                state.portfolioOptions.saved = payload.saved_portfolios || [];
                renderPortfolioOptions();
            } catch (error) {
                console.error(error);
                presetPortfolioList.innerHTML = '<p class="proscan-inline-error">Unable to load preset portfolios right now.</p>';
                savedPortfolioList.innerHTML = '<p class="proscan-inline-error">Unable to load saved portfolios right now.</p>';
            }
        }

        groupButtons.forEach((button) => {
            button.addEventListener('click', function () {
                const groupName = button.dataset.groupName || '';
                sessionStorage.setItem('tickerGroup', groupName);
                collapsePortfolioAccordions();
                setContext({
                    type: 'group',
                    label: button.dataset.groupLabel || getGroupLabel(groupName),
                    groupName,
                });
                renderEmptyTable(`${groupName} selected. Run a strategy card to populate group results.`);
                Array.from(strategyPanelContainer.children).forEach(syncStrategyCardSummary);
            });
        });

        accordionButtons.forEach((button) => {
            button.addEventListener('click', function () {
                const expanded = button.getAttribute('aria-expanded') === 'true';
                collapsePortfolioAccordions();
                setAccordionState(button, !expanded);
            });
        });

        sortHeaders.forEach((header) => {
            header.addEventListener('click', function () {
                const nextKey = header.dataset.sortKey;
                state.currentSort = {
                    key: nextKey,
                    direction: state.currentSort.key === nextKey && state.currentSort.direction === 'asc' ? 'desc' : 'asc',
                };
                renderTableState();
            });
        });

        queryFilter?.addEventListener('input', renderTableState);
        performanceFilter?.addEventListener('change', renderTableState);
        minTradesFilter?.addEventListener('input', renderTableState);
        clearFiltersButton?.addEventListener('click', function () {
            queryFilter.value = '';
            performanceFilter.value = 'all';
            minTradesFilter.value = '';
            renderTableState();
        });

        gcOpenButton?.addEventListener('click', function () {
            syncStrategyModalContext(STRATEGIES.golden_cross);
            openModal(gcModal);
        });

        momentumOpenButton?.addEventListener('click', function () {
            syncStrategyModalContext(STRATEGIES.momentum_12m);
            openModal(momentumModal);
        });

        gcCancel?.addEventListener('click', function () { closeModal(gcModal); });
        momentumCancel?.addEventListener('click', function () { closeModal(momentumModal); });

        gcModal?.addEventListener('click', function (event) {
            if (event.target === gcModal) {
                closeModal(gcModal);
            }
        });

        momentumModal?.addEventListener('click', function (event) {
            if (event.target === momentumModal) {
                closeModal(momentumModal);
            }
        });

        gcForm?.addEventListener('submit', function (event) {
            event.preventDefault();
            closeModal(gcModal);
            createConfiguredStrategyCard('golden_cross', STRATEGIES.golden_cross.buildConfig());
        });

        momentumForm?.addEventListener('submit', function (event) {
            event.preventDefault();
            closeModal(momentumModal);
            createConfiguredStrategyCard('momentum_12m', STRATEGIES.momentum_12m.buildConfig());
        });

        Array.from(tableBody?.querySelectorAll('tr') || []).forEach((row) => {
            if (row.dataset.placeholder === '1') {
                return;
            }
            row.dataset.rowMode = 'group';
            updateRowDataset(row);
            updateTickerLink(row);
            updateMathLink(row);
        });

        setContext(state.context);
        if (!getDataRows().length) {
            renderEmptyTable('Choose a ticker group or portfolio, then run a strategy card to populate results.');
        } else {
            renderTableState();
        }
        loadPortfolioOptions();
    });
})();
