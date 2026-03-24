(function () {
    function formatPercent(value, digits = 2) {
        return Number.isFinite(value) ? `${value.toFixed(digits)}%` : '-';
    }

    function summarizeSignals(signals, startCash, finalCash) {
        let wins = 0;
        let losses = 0;
        let totalTradeReturnPct = 0;
        let trades = 0;
        let openTrade = null;

        (signals || []).forEach((signal) => {
            if (!openTrade && signal.action === 'BUY') {
                openTrade = signal;
                return;
            }

            if (openTrade && signal.action === 'SELL') {
                const pnl = (signal.price - openTrade.price) * openTrade.shares;
                const tradeReturnPct = openTrade.price ? ((signal.price - openTrade.price) / openTrade.price) * 100 : 0;

                if (pnl >= 0) {
                    wins += 1;
                } else {
                    losses += 1;
                }

                totalTradeReturnPct += tradeReturnPct;
                trades += 1;
                openTrade = null;
            }
        });

        return {
            wins,
            losses,
            trades,
            winRatePct: trades ? (wins / trades) * 100 : 0,
            avgTradeReturnPct: trades ? totalTradeReturnPct / trades : 0,
            totalReturnPct: startCash ? ((finalCash - startCash) / startCash) * 100 : 0,
        };
    }

    function createStrategyCard(title, summaryHtml) {
        const card = document.createElement('article');
        card.className = 'proscan-strategy-card';
        card.innerHTML = `
            <h4>${title}</h4>
            <p>${summaryHtml}</p>
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

        const currentGroupValue = document.getElementById('current-group-value');
        const currentStrategyValue = document.getElementById('current-strategy-value');
        const scanStatusValue = document.getElementById('scan-status-value');
        const strategyPanelContainer = document.getElementById('strategy-panel-container');
        const groupButtons = Array.from(document.querySelectorAll('[data-group-name][data-group-url]'));
        const optionButtons = Array.from(document.querySelectorAll('.btn-option'));
        const table = document.getElementById('proscan-table');
        const tableBody = table ? table.querySelector('tbody') : null;
        const resultsMeta = document.getElementById('proscan-results-meta');
        const queryFilter = document.getElementById('proscan-filter-query');
        const performanceFilter = document.getElementById('proscan-filter-performance');
        const minTradesFilter = document.getElementById('proscan-filter-min-trades');
        const clearFiltersButton = document.getElementById('proscan-clear-filters');
        const sortHeaders = Array.from(document.querySelectorAll('#proscan-table th[data-sort-key]'));

        const gcModal = document.getElementById('proscan-gc-modal');
        const gcForm = document.getElementById('proscan-gc-form');
        const gcCancel = document.getElementById('ps-gc-cancel');
        const gcOpenButton = document.getElementById('golden-cross-btn');

        const momentumModal = document.getElementById('proscan-momentum-modal');
        const momentumForm = document.getElementById('proscan-momentum-form');
        const momentumCancel = document.getElementById('ps-mom-cancel');
        const momentumOpenButton = document.getElementById('momentum-btn');

        let currentTickerGroup = sessionStorage.getItem('tickerGroup') || '';
        let lastScanContext = null;
        let currentSort = { key: 'ticker', direction: 'asc' };
        if (!currentTickerGroup) {
            const matchingButton = groupButtons.find((button) => {
                try {
                    return new URL(button.dataset.groupUrl, window.location.origin).pathname === window.location.pathname;
                } catch (error) {
                    return false;
                }
            });

            if (matchingButton) {
                currentTickerGroup = matchingButton.dataset.groupName;
                sessionStorage.setItem('tickerGroup', currentTickerGroup);
            }
        }

        function numericValue(value) {
            if (typeof value === 'number' && Number.isFinite(value)) {
                return value;
            }

            const parsed = parseFloat(String(value || '').replace(/[,%$]/g, '').trim());
            return Number.isFinite(parsed) ? parsed : null;
        }

        function updateTickerLink(row) {
            const ticker = row.dataset.ticker || row.cells[1].textContent.trim();
            const params = new URLSearchParams();

            if (ticker) {
                params.set('ticker', ticker);
            }

            if (lastScanContext && lastScanContext.startDate && lastScanContext.endDate) {
                params.set('start_date', lastScanContext.startDate);
                params.set('end_date', lastScanContext.endDate);
                params.set('autoload', '1');
            }

            const href = `/backtest/${params.toString() ? `?${params.toString()}` : ''}`;
            row.cells[1].innerHTML = `<a class="proscan-ticker-link" href="${href}" target="_blank" rel="noopener noreferrer">${ticker || '-'}</a>`;
        }

        function updateRowDataset(row, stats = {}) {
            const name = row.dataset.name || row.cells[0].textContent.trim() || '-';
            const ticker = row.dataset.ticker || row.cells[1].textContent.trim() || '-';

            row.dataset.name = name;
            row.dataset.ticker = ticker;
            row.dataset.wins = stats.wins ?? numericValue(row.cells[2].textContent) ?? '';
            row.dataset.losses = stats.losses ?? numericValue(row.cells[3].textContent) ?? '';
            row.dataset.winRate = stats.winRatePct ?? numericValue(row.cells[4].textContent) ?? '';
            row.dataset.avgTradeReturn = stats.avgTradeReturnPct ?? numericValue(row.cells[5].textContent) ?? '';
            row.dataset.totalReturn = stats.totalReturnPct ?? numericValue(row.cells[6].textContent) ?? '';
            row.dataset.trades = stats.trades ?? numericValue(row.cells[7].textContent) ?? '';
            row.dataset.hasScanData = stats.hasScanData !== undefined
                ? String(Boolean(stats.hasScanData))
                : String(row.cells[6].textContent.trim() !== '-' && row.cells[6].textContent.trim() !== 'No data');
        }

        function matchesFilters(row) {
            const query = (queryFilter.value || '').trim().toLowerCase();
            const performance = performanceFilter.value;
            const minTrades = numericValue(minTradesFilter.value) ?? 0;
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
            const { key, direction } = currentSort;
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

            const rows = Array.from(tableBody.querySelectorAll('tr'));
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
                header.dataset.sortIndicator = header.dataset.sortKey === currentSort.key
                    ? (currentSort.direction === 'asc' ? '↑' : '↓')
                    : '';
            });

            if (resultsMeta) {
                resultsMeta.textContent = `Showing ${visibleRows.length} of ${rows.length} results`;
            }
        }

        function updateContext(strategyLabel) {
            currentGroupValue.textContent = currentTickerGroup || 'None selected';
            if (strategyLabel) {
                currentStrategyValue.textContent = strategyLabel;
            }
        }

        function setActiveButton(button) {
            const group = button.closest('[data-option-group]');
            if (!group) {
                return;
            }

            group.querySelectorAll('.btn-option').forEach((item) => item.classList.remove('active'));
            button.classList.add('active');
        }

        function openModal(modal) {
            modal.classList.remove('hidden');
            modal.setAttribute('aria-hidden', 'false');
        }

        function closeModal(modal) {
            modal.classList.add('hidden');
            modal.setAttribute('aria-hidden', 'true');
        }

        function updateRow(row, stats) {
            row.classList.remove('scan-positive', 'scan-negative');
            row.cells[2].textContent = stats.wins;
            row.cells[3].textContent = stats.losses;
            row.cells[4].textContent = formatPercent(stats.winRatePct, 1);
            row.cells[5].textContent = formatPercent(stats.avgTradeReturnPct, 2);
            row.cells[6].textContent = formatPercent(stats.totalReturnPct, 2);
            row.cells[7].textContent = stats.trades || '-';
            row.classList.add(stats.totalReturnPct >= 0 ? 'scan-positive' : 'scan-negative');
            updateRowDataset(row, Object.assign({}, stats, { hasScanData: true }));
            updateTickerLink(row);
        }

        async function runScanForGroup(strategyLabel, config, runner) {
            if (!currentTickerGroup) {
                alert('Select a ticker group first.');
                return;
            }

            scanStatusValue.textContent = `Running ${strategyLabel}...`;
            currentStrategyValue.textContent = strategyLabel;
            lastScanContext = {
                strategyLabel,
                startDate: config.startDate,
                endDate: config.endDate,
            };

            try {
                const response = await fetch(
                    `/fetch_group_data/?ticker_group=${encodeURIComponent(currentTickerGroup)}&start_date=${config.startDate}&end_date=${config.endDate}`
                );
                const data = await response.json();

                if (!data.valid) {
                    throw new Error(data.error || 'Unable to load group data.');
                }

                (data.data || []).forEach((stock) => {
                    const row = document.querySelector(`tr[data-ticker="${stock.symbol}"]`);
                    if (!row) {
                        return;
                    }

                    row.classList.remove('scan-positive', 'scan-negative');

                    if (!Array.isArray(stock.chartData) || !stock.chartData.length) {
                        row.cells[2].textContent = '-';
                        row.cells[3].textContent = '-';
                        row.cells[4].textContent = '-';
                        row.cells[5].textContent = '-';
                        row.cells[6].textContent = 'No data';
                        row.cells[7].textContent = '-';
                        updateRowDataset(row, {
                            wins: null,
                            losses: null,
                            winRatePct: null,
                            avgTradeReturnPct: null,
                            totalReturnPct: null,
                            trades: null,
                            hasScanData: false,
                        });
                        updateTickerLink(row);
                        return;
                    }

                    const simResult = runner(stock.chartData, config);
                    const stats = summarizeSignals(simResult.signals, config.startCash, simResult.finalCash);
                    updateRow(row, stats);
                });

                scanStatusValue.textContent = `${strategyLabel} finished successfully`;
                renderTableState();
            } catch (error) {
                console.error(error);
                scanStatusValue.textContent = `Scan failed: ${error.message}`;
                alert(error.message);
            }
        }

        function bindStrategyCard(card, onRun, onEdit) {
            card.querySelector('[data-role="run"]').addEventListener('click', onRun);
            card.querySelector('[data-role="edit"]').addEventListener('click', onEdit);
            card.querySelector('[data-role="delete"]').addEventListener('click', function () {
                card.remove();
                currentStrategyValue.textContent = 'Strategy card removed';
            });
        }

        optionButtons.forEach((button) => {
            if (!button.dataset.groupName) {
                button.addEventListener('click', function () {
                    setActiveButton(button);
                });
            }
        });

        groupButtons.forEach((button) => {
            if (button.dataset.groupName === currentTickerGroup) {
                button.classList.add('active');
            }

            button.addEventListener('click', function () {
                sessionStorage.setItem('tickerGroup', button.dataset.groupName);
                window.location.href = button.dataset.groupUrl;
            });
        });

        if (tableBody) {
            Array.from(tableBody.querySelectorAll('tr')).forEach((row) => {
                updateRowDataset(row);
                updateTickerLink(row);
            });
        }

        sortHeaders.forEach((header) => {
            header.addEventListener('click', function () {
                const nextKey = header.dataset.sortKey;
                currentSort = {
                    key: nextKey,
                    direction: currentSort.key === nextKey && currentSort.direction === 'asc' ? 'desc' : 'asc',
                };
                renderTableState();
            });
        });

        queryFilter.addEventListener('input', renderTableState);
        performanceFilter.addEventListener('change', renderTableState);
        minTradesFilter.addEventListener('input', renderTableState);
        clearFiltersButton.addEventListener('click', function () {
            queryFilter.value = '';
            performanceFilter.value = 'all';
            minTradesFilter.value = '';
            renderTableState();
        });

        updateContext();
        renderTableState();


        gcOpenButton.addEventListener('click', function () {
            setActiveButton(gcOpenButton);
            openModal(gcModal);
        });

        gcCancel.addEventListener('click', function () {
            closeModal(gcModal);
        });

        gcModal.addEventListener('click', function (event) {
            if (event.target === gcModal) {
                closeModal(gcModal);
            }
        });

        gcForm.addEventListener('submit', function (event) {
            event.preventDefault();

            const config = {
                startDate: document.getElementById('ps-gc-start-date').value,
                endDate: document.getElementById('ps-gc-end-date').value,
                fastSma: parseInt(document.getElementById('ps-gc-fast-sma').value, 10),
                slowSma: parseInt(document.getElementById('ps-gc-slow-sma').value, 10),
                orderPct: parseFloat(document.getElementById('ps-gc-order-percentage').value),
                startCash: parseFloat(document.getElementById('ps-gc-starting-cash').value),
                overrideShares: document.getElementById('ps-gc-override-shares').value,
            };

            if (!currentTickerGroup) {
                alert('Select a ticker group first.');
                return;
            }

            closeModal(gcModal);

            const card = createStrategyCard(
                'Golden Cross',
                `Group: <strong>${currentTickerGroup}</strong><br>Fast SMA ${config.fastSma} · Slow SMA ${config.slowSma}<br>Order ${config.orderPct}% · Cash $${config.startCash.toLocaleString()}`
            );

            bindStrategyCard(
                card,
                function () {
                    runScanForGroup('Golden Cross', config, function (chartData, cfg) {
                        return window.runGoldenCrossStrategySim(
                            chartData,
                            cfg.fastSma,
                            cfg.slowSma,
                            cfg.orderPct,
                            cfg.startCash,
                            cfg.overrideShares
                        );
                    });
                },
                function () {
                    document.getElementById('ps-gc-start-date').value = config.startDate;
                    document.getElementById('ps-gc-end-date').value = config.endDate;
                    document.getElementById('ps-gc-fast-sma').value = config.fastSma;
                    document.getElementById('ps-gc-slow-sma').value = config.slowSma;
                    document.getElementById('ps-gc-order-percentage').value = config.orderPct;
                    document.getElementById('ps-gc-starting-cash').value = config.startCash;
                    document.getElementById('ps-gc-override-shares').value = config.overrideShares || '';
                    card.remove();
                    openModal(gcModal);
                }
            );

            strategyPanelContainer.appendChild(card);
            updateContext('Golden Cross');
        });

        momentumOpenButton.addEventListener('click', function () {
            setActiveButton(momentumOpenButton);
            openModal(momentumModal);
        });

        momentumCancel.addEventListener('click', function () {
            closeModal(momentumModal);
        });

        momentumModal.addEventListener('click', function (event) {
            if (event.target === momentumModal) {
                closeModal(momentumModal);
            }
        });

        momentumForm.addEventListener('submit', function (event) {
            event.preventDefault();

            const config = {
                startDate: document.getElementById('ps-mom-start-date').value,
                endDate: document.getElementById('ps-mom-end-date').value,
                lookback: parseInt(document.getElementById('ps-mom-lookback').value, 10),
                buyPct: parseFloat(document.getElementById('ps-mom-buy-threshold').value),
                exitPct: parseFloat(document.getElementById('ps-mom-exit-threshold').value),
                orderPct: parseFloat(document.getElementById('ps-mom-order-percentage').value),
                startCash: parseFloat(document.getElementById('ps-mom-starting-cash').value),
                overrideShares: document.getElementById('ps-mom-override-shares').value,
            };

            if (!currentTickerGroup) {
                alert('Select a ticker group first.');
                return;
            }

            closeModal(momentumModal);

            const card = createStrategyCard(
                'Momentum',
                `Group: <strong>${currentTickerGroup}</strong><br>Lookback ${config.lookback} · Buy ≥ ${config.buyPct}% · Exit &lt; ${config.exitPct}%<br>Order ${config.orderPct}% · Cash $${config.startCash.toLocaleString()}`
            );

            bindStrategyCard(
                card,
                function () {
                    runScanForGroup('Momentum', config, function (chartData, cfg) {
                        return window.runMomentumStrategySim(
                            chartData,
                            cfg.lookback,
                            cfg.buyPct,
                            cfg.exitPct,
                            cfg.orderPct,
                            cfg.startCash,
                            cfg.overrideShares
                        );
                    });
                },
                function () {
                    document.getElementById('ps-mom-start-date').value = config.startDate;
                    document.getElementById('ps-mom-end-date').value = config.endDate;
                    document.getElementById('ps-mom-lookback').value = config.lookback;
                    document.getElementById('ps-mom-buy-threshold').value = config.buyPct;
                    document.getElementById('ps-mom-exit-threshold').value = config.exitPct;
                    document.getElementById('ps-mom-order-percentage').value = config.orderPct;
                    document.getElementById('ps-mom-starting-cash').value = config.startCash;
                    document.getElementById('ps-mom-override-shares').value = config.overrideShares || '';
                    card.remove();
                    openModal(momentumModal);
                }
            );

            strategyPanelContainer.appendChild(card);
            updateContext('Momentum');
        });
    });
})();
