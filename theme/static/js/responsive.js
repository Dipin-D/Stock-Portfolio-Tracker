(function () {
    const phoneMedia = window.matchMedia('(max-width: 768px)');
    let tableCounter = 0;

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function parseIndex(value, fallback) {
        const parsed = Number.parseInt(value, 10);
        return Number.isFinite(parsed) ? parsed : fallback;
    }

    function stripHtml(value) {
        return String(value ?? '').replace(/<[^>]*>/g, '').trim();
    }

    function applyCollapsibleState(trigger, panel, expanded) {
        if (!phoneMedia.matches) {
            panel.hidden = false;
            panel.classList.add('is-open');
            trigger.setAttribute('aria-expanded', 'true');
            trigger.classList.add('is-expanded');
            return;
        }

        panel.hidden = !expanded;
        panel.classList.toggle('is-open', expanded);
        trigger.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        trigger.classList.toggle('is-expanded', expanded);
    }

    function initCollapsibles() {
        document.querySelectorAll('[data-collapsible-trigger]').forEach((trigger) => {
            const panelId = trigger.getAttribute('aria-controls');
            const panel = panelId ? document.getElementById(panelId) : null;

            if (!panel) {
                return;
            }

            if (!trigger.dataset.currentExpanded) {
                trigger.dataset.currentExpanded = trigger.dataset.defaultState === 'open' ? 'true' : 'false';
            }

            if (!trigger.dataset.collapsibleBound) {
                trigger.dataset.collapsibleBound = '1';
                trigger.addEventListener('click', function () {
                    if (!phoneMedia.matches) {
                        return;
                    }

                    const nextExpanded = trigger.dataset.currentExpanded !== 'true';
                    trigger.dataset.currentExpanded = nextExpanded ? 'true' : 'false';
                    applyCollapsibleState(trigger, panel, nextExpanded);
                });
            }

            applyCollapsibleState(trigger, panel, trigger.dataset.currentExpanded === 'true');
        });
    }

    function getTableShell(table) {
        const wrapper = table.closest('[data-responsive-table-shell]')
            || table.parentElement;

        let cardsHost = wrapper.querySelector(':scope > .responsive-table-cards');
        if (!cardsHost) {
            cardsHost = document.createElement('div');
            cardsHost.className = 'responsive-table-cards';
            wrapper.insertBefore(cardsHost, table);
        }

        return { wrapper, cardsHost };
    }

    function buildRowCard(headers, cells, titleIndex, subtitleIndex) {
        const title = cells[titleIndex] || 'Row';
        const subtitle = subtitleIndex >= 0 ? cells[subtitleIndex] : '';
        const subtitleIsBadge = subtitle && /^\d+$/.test(stripHtml(subtitle));
        const items = cells
            .map((value, index) => ({ label: headers[index] || `Column ${index + 1}`, value, index }))
            .filter((item) => item.index !== titleIndex && item.index !== subtitleIndex)
            .filter((item) => item.value && item.value !== '—')
            .map((item) => `
                <div class="responsive-table-card-item">
                    <span class="responsive-table-card-label">${escapeHtml(item.label)}</span>
                    <div class="responsive-table-card-value">${item.value}</div>
                </div>
            `)
            .join('');

        return `
            <article class="responsive-table-card">
                <div class="responsive-table-card-header">
                    <h3 class="responsive-table-card-title">${title}</h3>
                    ${subtitle ? `<span class="responsive-table-card-subtitle${subtitleIsBadge ? ' is-badge' : ''}">${subtitle}</span>` : ''}
                </div>
                <div class="responsive-table-card-grid">${items}</div>
            </article>
        `;
    }

    function refreshResponsiveTable(table) {
        if (!table || !table.matches('[data-responsive-table]')) {
            return;
        }

        if (!table.id) {
            tableCounter += 1;
            table.id = `responsive-table-${tableCounter}`;
        }

        const { cardsHost } = getTableShell(table);
        const headers = Array.from(table.querySelectorAll('thead th')).map((cell) => cell.textContent.trim());
        const rows = Array.from(table.querySelectorAll('tbody tr'));
        const dataRows = rows.filter((row) => !row.querySelector('td[colspan]'));
        const titleIndex = parseIndex(table.dataset.responsiveTitleCol, 0);
        const subtitleIndex = table.dataset.responsiveSubtitleCol === undefined
            ? -1
            : parseIndex(table.dataset.responsiveSubtitleCol, -1);

        if (!dataRows.length) {
            const emptyRow = rows.find((row) => row.querySelector('td[colspan]'));
            const emptyText = emptyRow ? emptyRow.textContent.trim() : 'No rows available.';
            cardsHost.innerHTML = `<div class="responsive-table-empty">${escapeHtml(emptyText)}</div>`;
            return;
        }

        cardsHost.innerHTML = dataRows.map((row) => {
            const cells = Array.from(row.children).map((cell) => cell.innerHTML.trim() || '—');
            return buildRowCard(headers, cells, titleIndex, subtitleIndex);
        }).join('');
    }

    function observeResponsiveTable(table) {
        const body = table.tBodies && table.tBodies[0];
        if (!body || body.dataset.responsiveObserved) {
            return;
        }

        body.dataset.responsiveObserved = '1';
        const observer = new MutationObserver(function () {
            refreshResponsiveTable(table);
        });
        observer.observe(body, {
            childList: true,
            subtree: true,
            characterData: true,
        });
    }

    function refreshResponsiveTables(root = document) {
        root.querySelectorAll('[data-responsive-table]').forEach((table) => {
            refreshResponsiveTable(table);
            observeResponsiveTable(table);
        });
    }

    function initResponsive() {
        initCollapsibles();
        refreshResponsiveTables();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initResponsive);
    } else {
        initResponsive();
    }

    const mediaHandler = function () {
        initCollapsibles();
        refreshResponsiveTables();
    };

    if (typeof phoneMedia.addEventListener === 'function') {
        phoneMedia.addEventListener('change', mediaHandler);
    } else if (typeof phoneMedia.addListener === 'function') {
        phoneMedia.addListener(mediaHandler);
    }

    window.addEventListener('resize', function () {
        initCollapsibles();
    });

    window.TradingProResponsive = {
        refreshResponsiveTables,
        initCollapsibles,
    };
})();
