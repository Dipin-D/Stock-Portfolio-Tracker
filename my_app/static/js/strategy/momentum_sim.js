/* momentum_sim.js
   N-day momentum rule:
   momentum_t = (Close_t / Close_{t-Lookback}) - 1
   Buy when momentum crosses ABOVE buyThreshold% (e.g., 2%), hold while >= exitThreshold (e.g., 0%),
   Sell when momentum falls BELOW exitThreshold.
*/

function computeMomentum(raw, lookback) {
  const out = [];
  for (let i = 0; i < raw.length; i++) {
    if (i < lookback) { out.push({ date: raw[i].time || raw[i].Date, m: null }); continue; }
    const prevClose = raw[i - lookback].Close;
    const m = prevClose > 0 ? (raw[i].Close / prevClose) - 1 : null;
    out.push({ date: raw[i].time || raw[i].Date, m });
  }
  return out;
}

function runMomentumStrategySim(raw, lookback=60, buyThresholdPct=2, exitThresholdPct=0, orderPct=100, startingCash=100000, overrideShares=null) {
  const buyTh = buyThresholdPct / 100.0;
  const exitTh = exitThresholdPct / 100.0;
  const mom = computeMomentum(raw, lookback);

  let cash = startingCash;
  let position = 0;
  const signals = [];

  const buyShares = (price) => {
    let shares = overrideShares ? Number(overrideShares) : Math.floor((cash * (orderPct/100)) / price);
    if (shares <= 0) return 0;
    cash -= shares * price;
    position += shares;
    return shares;
  };

  const sellAll = (price) => {
    if (position <= 0) return 0;
    const proceeds = position * price;
    cash += proceeds;
    const sold = position;
    position = 0;
    return sold;
  };

  for (let i = 1; i < raw.length; i++) {
    const price = raw[i].Close;
    const prevM = mom[i-1].m;
    const curM  = mom[i].m;
    if (curM == null || prevM == null) continue;

    // Cross above buy threshold → BUY
    if (prevM <= buyTh && curM > buyTh && position === 0) {
      const sh = buyShares(price);
      if (sh > 0) { signals.push({ date: mom[i].date, action: 'BUY', price, shares: sh, m: curM }); }
    }
    // Cross below exit threshold → SELL
    if (prevM >= exitTh && curM < exitTh && position > 0) {
      const sh = sellAll(price);
      if (sh > 0) { signals.push({ date: mom[i].date, action: 'SELL', price, shares: sh, m: curM }); }
    }
  }

  // Liquidate at end
  if (position > 0) {
    const price = raw[raw.length - 1].Close;
    const sh = sellAll(price);
    if (sh > 0) { signals.push({ date: mom[mom.length - 1].date, action: 'SELL', price, shares: sh, m: mom[mom.length-1].m }); }
  }

  return { finalCash: cash, signals };
}

function summarizeMomentumLog(signals, startCash, finalCash) {
  let wins=0, losses=0, dollarGains=0, dollarLosses=0;
  const stack = [];
  for (const s of signals) {
    if (s.action === 'BUY') stack.push(s);
    if (s.action === 'SELL' && stack.length) {
      const b = stack.pop();
      const pnl = (s.price - b.price) * b.shares;
      if (pnl >= 0) { wins++; dollarGains += pnl; }
      else { losses++; dollarLosses += -pnl; }
    }
  }
  const totalReturnPct = ((finalCash - startCash) / startCash * 100).toFixed(2);
  const winRate = (wins + losses) ? (wins * 100 / (wins + losses)).toFixed(1) : "0.0";
  return { wins, losses, dollarGains, dollarLosses, totalReturnPct, winRate };
}
