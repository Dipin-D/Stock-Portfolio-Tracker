/**
 * runGoldenCrossStrategySim
 *
 * This function simulates the Golden Cross strategy for a given stock's raw data.
 * It computes the fast and slow SMAs (using computeSMA from indicator.js), then runs through the data,
 * entering a BUY signal when the fast SMA crosses above the slow SMA and a SELL signal when it crosses below.
 *
 * If the simulation ends with an open BUY position (i.e. no subsequent SELL occurred),
 * that last BUY trade is disregarded (and the cash is rolled back).
 *
 * @param {Array} data - Array of stock data objects.
 * @param {number} fastPeriod - Fast SMA period (e.g., 50).
 * @param {number} slowPeriod - Slow SMA period (e.g., 200).
 * @param {number} orderPerc - Order percentage (e.g., 100 for 100%).
 * @param {number} startingCash - Starting cash available.
 * @param {string|number} overrideShares - (Optional) If provided, the strategy uses this share quantity instead of calculating.
 *
 * @returns {Object} An object with:
 *   - signals: Array of trade signals (each with date, action, price, shares, and the SMA values used).
 *   - finalCash: Final cash balance (only closed trades count).
 */


function runGoldenCrossStrategySim(data, fastPeriod, slowPeriod, orderPerc, startingCash, overrideShares) {
  // Compute moving averages (must be available from indicator.js)
  const fastSMA = computeSMA(data, fastPeriod);
  const slowSMA = computeSMA(data, slowPeriod);
  
  let signals = [];
  let cash = startingCash;
  let position = 0; // 0 = not in a trade; 1 = currently in a trade.
  let shares = overrideShares ? parseInt(overrideShares, 10) : 0;
  
  // Save cash before a BUY to roll back if needed.
  let lastCashBeforeBuy = cash;
  
  // Define separate offsets for fast and slow SMAs.
  const fastOffset = fastPeriod - 1;   // For example: 50 - 1 = 49.
  const slowOffset = slowPeriod - 1;     // For example: 200 - 1 = 199.
  
  // Determine starting index where both SMAs have values.
  const startIndex = Math.max(fastOffset, slowOffset) + 1;
  
  for (let i = startIndex; i < data.length; i++) {
      // Ensure we have valid SMA values for current and previous days.
      if (
          !fastSMA[i - fastOffset] || !slowSMA[i - slowOffset] ||
          !fastSMA[i - fastOffset - 1] || !slowSMA[i - slowOffset - 1]
      ) {
          continue;
      }
      
      let prevFast = fastSMA[i - fastOffset - 1].value;
      let prevSlow = slowSMA[i - slowOffset - 1].value;
      let currentFast = fastSMA[i - fastOffset].value;
      let currentSlow = slowSMA[i - slowOffset].value;
      
      let formattedDate = new Date(data[i].Date * 1000).toISOString().slice(0,10);
      let price = data[i].Close;
      
      // Upward crossover: BUY signal.
      if (position === 0 && prevFast < prevSlow && currentFast >= currentSlow) {
          // Save cash before buying.
          lastCashBeforeBuy = cash;
          
          let investAmt = (orderPerc / 100) * cash;
          if (!overrideShares) {
              shares = Math.floor(investAmt / price);
          }
          if (shares > 0) {
              position = 1;
              cash -= shares * price;
              signals.push({
                  date: formattedDate,
                  action: "BUY",
                  price: price,
                  shares: shares,
                  prevFast: prevFast,
                  currentFast: currentFast,
                  prevSlow: prevSlow,
                  currentSlow: currentSlow
              });
              console.log(`Buy ${shares} shares at $${price} on ${formattedDate}`);
          }
      }
      
      // Downward crossover: SELL signal.
      if (position === 1 && prevFast > prevSlow && currentFast <= currentSlow) {
          cash += shares * price;
          signals.push({
              date: formattedDate,
              action: "SELL",
              price: price,
              shares: shares,
              prevFast: prevFast,
              currentFast: currentFast,
              prevSlow: prevSlow,
              currentSlow: currentSlow
          });
          console.log(`Sell ${shares} shares at $${price} on ${formattedDate}`);
          position = 0;
          shares = 0;
      }
  }
  
  // If the strategy ends with an open position (BUY not closed), disregard it.
  if (position === 1) {
      console.log("Open position detected at end of simulation, disregarding last BUY trade.");
      if (signals.length > 0 && signals[signals.length - 1].action === "BUY") {
          signals.pop();
      }
      cash = lastCashBeforeBuy;
      position = 0;
      shares = 0;
  }
  
  console.log("Final cash balance:", cash);
  return { signals: signals, finalCash: cash };
};

// Expose the function globally for reuse.
window.runGoldenCrossStrategySim = runGoldenCrossStrategySim;



/**
 * summarizeTradeLog
 *  Derives win/loss counts, win-rate, dollar gains & losses, and total return %
 *  from the BUY/SELL signal pairs produced by runGoldenCrossStrategySim
 *
 * @param {Array} signals       – Array of BUY/SELL objects (already paired)
 * @param {number} startCash    – Cash you began with (same one you passed in)
 * @param {number} finalCash    – Cash returned by the simulator
 *
 * @returns {Object} {
 *    wins, losses, winRate, dollarGains, dollarLosses, totalReturnPct
 * }
 */

function summarizeTradeLog(signals, startCash, finalCash) {
  let wins = 0, losses = 0;
  let dollarGains = 0, dollarLosses = 0;

  // Walk through signals two at a time (BUY then SELL)
  for (let i = 0; i < signals.length; i += 2) {
    const buy = signals[i];
    const sell = signals[i + 1];
    if (!buy || !sell) continue;                      // safety guard

    const pnl = (sell.price - buy.price) * buy.shares;
    if (pnl >= 0) {
      wins += 1;
      dollarGains += pnl;
    } else {
      losses += 1;
      dollarLosses += Math.abs(pnl);
    }
  }

  const totalTrades   = wins + losses;
  const winRate       = totalTrades ? (wins / totalTrades) * 100 : 0;
  const totalReturnPct = ((finalCash - startCash) / startCash) * 100;

  return {
    wins,
    losses,
    winRate: winRate.toFixed(2),
    dollarGains: dollarGains.toFixed(2),
    dollarLosses: dollarLosses.toFixed(2),
    totalReturnPct: totalReturnPct.toFixed(2)
  };
};

window.summarizeTradeLog = summarizeTradeLog;
