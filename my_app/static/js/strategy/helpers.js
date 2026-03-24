(() => {
  // Guard the namespace (no conflicts).
  const root = window;
  root.Strat = root.Strat || {};
  const H = {};

  // --- Utils ---------------------------------------------------------------
  const num = (v, d = 0) => (Number.isFinite(+v) ? +v : d);
  const pct = (n) => (Number.isFinite(n) ? n : 0);

  // A "signal" can be an object or tuple:
  //   { date, action, type?, price, shares }
  // or [date, action, price, shares] etc.
  function readSignal(sig) {
    if (sig && typeof sig === 'object' && !Array.isArray(sig)) {
      return {
        date: sig.date ?? null,
        action: (sig.action ?? sig.type ?? '').toString().toUpperCase(),
        price: num(sig.price),
        shares: num(sig.shares)
      };
    }
    if (Array.isArray(sig)) {
      // best-effort: [date, action, price, shares]
      const [date, action, price, shares] = sig;
      return {
        date: date ?? null,
        action: (action ?? '').toString().toUpperCase(),
        price: num(price),
        shares: num(shares)
      };
    }
    return { date: null, action: '', price: 0, shares: 0 };
  }

  // Infer number of completed trades from signals (pairs of BUY/SELL).
  H.inferTradesFromSignals = function inferTradesFromSignals(signals) {
    if (!Array.isArray(signals) || !signals.length) return 0;
    let inPos = false, trades = 0;
    for (const s of signals) {
      const { action } = readSignal(s);
      if (!inPos && action.startsWith('BUY')) inPos = true;
      else if (inPos && action.startsWith('SELL')) {
        inPos = false;
        trades += 1;
      }
    }
    return trades;
  };

  // Summarize the trade log into wins/losses etc.
  // You can pass either:
  //  - a sim object { signals, finalCash } and also startCash as second arg
  //  - or (legacy) summarizeTradeLog(signals, startCash, finalCash)
  H.summarizeTradeLog = function summarizeTradeLog(a, b, c) {
    let signals, startCash, finalCash;
    if (Array.isArray(a)) {
      // legacy signature
      signals = a; startCash = num(b); finalCash = num(c, startCash);
    } else if (a && typeof a === 'object') {
      signals = a.signals || [];
      startCash = num(b);
      finalCash = num(a.finalCash, startCash);
    } else {
      signals = []; startCash = num(b); finalCash = num(c, startCash);
    }

    let wins = 0, losses = 0, dollarGains = 0, dollarLosses = 0;
    let inPos = false, entryPrice = 0, entryShares = 0;

    for (const raw of signals) {
      const { action, price, shares } = readSignal(raw);

      if (!inPos && action.startsWith('BUY')) {
        inPos = true;
        entryPrice = price;
        entryShares = shares || entryShares || 0; // carry if sim stores on SELL only
      } else if (inPos && action.startsWith('SELL')) {
        const exitPrice = price;
        const sh = entryShares || shares || 0;
        const pnl = (exitPrice - entryPrice) * sh;
        if (pnl >= 0) { wins += 1; dollarGains += pnl; }
        else { losses += 1; dollarLosses += Math.abs(pnl); }
        inPos = false;
        entryPrice = 0; entryShares = 0;
      }
    }

    const trades = wins + losses || H.inferTradesFromSignals(signals);
    const winRate = trades ? (wins / trades) * 100 : 0;

    // If the sim didn’t precompute average, estimate it from per-trade P/L %
    // (fallback; your sim may give avgTradeReturnPct directly).
    let avgTradeReturnPct = 0;
    if (trades) {
      // rough estimate: (total gains - total losses) / (trades * average entry value)
      // We don’t have entry notional; leave 0 and let caller overwrite if provided.
      avgTradeReturnPct = 0;
    }

    const totalReturnPct = startCash
      ? ((finalCash - startCash) / startCash) * 100
      : 0;

    return {
      wins, losses, trades,
      winRate: +winRate.toFixed(2),
      dollarGains: +dollarGains.toFixed(2),
      dollarLosses: +dollarLosses.toFixed(2),
      avgTradeReturnPct: +avgTradeReturnPct.toFixed(2),
      totalReturnPct: +totalReturnPct.toFixed(2),
    };
  };

  // Expose namespaced helpers
  root.Strat.Helpers = root.Strat.Helpers || H;

  // Back-compat plain globals (only if not already defined)
  if (typeof root.inferTradesFromSignals !== 'function') {
    root.inferTradesFromSignals = H.inferTradesFromSignals;
  }
  if (typeof root.summarizeTradeLog !== 'function') {
    root.summarizeTradeLog = H.summarizeTradeLog;
  }
})();

