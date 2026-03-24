(function () {
    function toNumber(value) {
        const num = Number(value);
        return Number.isFinite(num) ? num : null;
    }

    function getTime(item) {
        const rawTime = item.time ?? item.Time ?? item.date ?? item.Date;
        if (rawTime === undefined || rawTime === null || rawTime === '') {
            return null;
        }

        if (typeof rawTime === 'string' && /^\d{4}-\d{2}-\d{2}/.test(rawTime)) {
            return rawTime.slice(0, 10);
        }

        if (rawTime instanceof Date && !Number.isNaN(rawTime.getTime())) {
            return rawTime.toISOString().slice(0, 10);
        }

        const numericTime = Number(rawTime);
        if (!Number.isFinite(numericTime)) {
            return null;
        }

        const timestamp = numericTime > 100000000000 ? numericTime : numericTime * 1000;
        const parsed = new Date(timestamp);
        return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString().slice(0, 10);
    }

    function normalizeCandle(item) {
        return {
            time: getTime(item),
            open: toNumber(item.Open ?? item.open),
            high: toNumber(item.High ?? item.high),
            low: toNumber(item.Low ?? item.low),
            close: toNumber(item.Close ?? item.close),
            volume: toNumber(item.Volume ?? item.volume) || 0,
        };
    }

    function normalizeCandles(data) {
        if (!Array.isArray(data)) {
            return [];
        }

        return data
            .map(normalizeCandle)
            .filter((item) =>
                item.time &&
                item.open !== null &&
                item.high !== null &&
                item.low !== null &&
                item.close !== null
            );
    }

    function rollingMean(values, period) {
        if (period <= 0) {
            return [];
        }

        const result = new Array(values.length).fill(null);
        let sum = 0;

        for (let i = 0; i < values.length; i += 1) {
            const current = toNumber(values[i]);
            sum += current ?? 0;

            if (i >= period) {
                const outgoing = toNumber(values[i - period]);
                sum -= outgoing ?? 0;
            }

            if (i >= period - 1) {
                result[i] = sum / period;
            }
        }

        return result;
    }

    function lineFromValues(candles, values) {
        const line = [];
        for (let i = 0; i < candles.length; i += 1) {
            const value = toNumber(values[i]);
            if (candles[i] && candles[i].time && value !== null) {
                line.push({ time: candles[i].time, value });
            }
        }
        return line;
    }

    function constantLine(times, value) {
        return times
            .filter(Boolean)
            .map((time) => ({ time, value }));
    }

    function computeSMA(data, period) {
        const candles = normalizeCandles(data);
        const closes = candles.map((item) => item.close);
        return lineFromValues(candles, rollingMean(closes, period));
    }

    function computeEMA(data, period) {
        const candles = normalizeCandles(data);
        if (!candles.length || period <= 0 || candles.length < period) {
            return [];
        }

        const multiplier = 2 / (period + 1);
        const closes = candles.map((item) => item.close);
        const emaValues = new Array(closes.length).fill(null);

        const seed = closes.slice(0, period).reduce((sum, value) => sum + value, 0) / period;
        emaValues[period - 1] = seed;

        for (let i = period; i < closes.length; i += 1) {
            emaValues[i] = ((closes[i] - emaValues[i - 1]) * multiplier) + emaValues[i - 1];
        }

        return lineFromValues(candles, emaValues);
    }

    function computeRSI(data, period = 14) {
        const candles = normalizeCandles(data);
        if (candles.length <= period) {
            return [];
        }

        const closes = candles.map((item) => item.close);
        const gains = new Array(closes.length).fill(0);
        const losses = new Array(closes.length).fill(0);

        for (let i = 1; i < closes.length; i += 1) {
            const change = closes[i] - closes[i - 1];
            gains[i] = Math.max(change, 0);
            losses[i] = Math.max(-change, 0);
        }

        let avgGain = gains.slice(1, period + 1).reduce((sum, value) => sum + value, 0) / period;
        let avgLoss = losses.slice(1, period + 1).reduce((sum, value) => sum + value, 0) / period;
        const rsiValues = new Array(closes.length).fill(null);

        rsiValues[period] = avgLoss === 0 ? 100 : 100 - (100 / (1 + (avgGain / avgLoss)));

        for (let i = period + 1; i < closes.length; i += 1) {
            avgGain = ((avgGain * (period - 1)) + gains[i]) / period;
            avgLoss = ((avgLoss * (period - 1)) + losses[i]) / period;

            if (avgLoss === 0) {
                rsiValues[i] = 100;
            } else {
                const rs = avgGain / avgLoss;
                rsiValues[i] = 100 - (100 / (1 + rs));
            }
        }

        return lineFromValues(candles, rsiValues);
    }

    function computeBollingerBands(data, period = 20, stdDevMultiplier = 2) {
        const candles = normalizeCandles(data);
        if (candles.length < period) {
            return { middle: [], upper: [], lower: [] };
        }

        const closes = candles.map((item) => item.close);
        const middleValues = rollingMean(closes, period);
        const upperValues = new Array(closes.length).fill(null);
        const lowerValues = new Array(closes.length).fill(null);

        for (let i = period - 1; i < closes.length; i += 1) {
            const slice = closes.slice(i - period + 1, i + 1);
            const mean = middleValues[i];
            const variance = slice.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / period;
            const stdDev = Math.sqrt(variance);

            upperValues[i] = mean + (stdDevMultiplier * stdDev);
            lowerValues[i] = mean - (stdDevMultiplier * stdDev);
        }

        return {
            middle: lineFromValues(candles, middleValues),
            upper: lineFromValues(candles, upperValues),
            lower: lineFromValues(candles, lowerValues),
        };
    }

    function computeStochasticOscillator(data, kPeriod = 14, smoothK = 3, dPeriod = 3) {
        const candles = normalizeCandles(data);
        if (candles.length < kPeriod) {
            return { k: [], d: [] };
        }

        const rawK = new Array(candles.length).fill(null);

        for (let i = kPeriod - 1; i < candles.length; i += 1) {
            const window = candles.slice(i - kPeriod + 1, i + 1);
            const highestHigh = Math.max(...window.map((item) => item.high));
            const lowestLow = Math.min(...window.map((item) => item.low));
            const denominator = highestHigh - lowestLow;
            rawK[i] = denominator === 0 ? 50 : ((candles[i].close - lowestLow) / denominator) * 100;
        }

        const smoothKValues = rollingMean(rawK.map((value) => value ?? 0), smoothK);
        const adjustedSmoothK = smoothKValues.map((value, index) => (rawK[index] === null ? null : value));
        const dValues = rollingMean(adjustedSmoothK.map((value) => value ?? 0), dPeriod);
        const adjustedD = dValues.map((value, index) => (adjustedSmoothK[index] === null ? null : value));

        return {
            k: lineFromValues(candles, adjustedSmoothK),
            d: lineFromValues(candles, adjustedD),
        };
    }

    function computeADX(data, period = 14) {
        const candles = normalizeCandles(data);
        if (candles.length <= period * 2) {
            return { adx: [], plusDI: [], minusDI: [] };
        }

        const tr = new Array(candles.length).fill(null);
        const plusDM = new Array(candles.length).fill(0);
        const minusDM = new Array(candles.length).fill(0);

        for (let i = 1; i < candles.length; i += 1) {
            const current = candles[i];
            const previous = candles[i - 1];

            const highDiff = current.high - previous.high;
            const lowDiff = previous.low - current.low;

            plusDM[i] = highDiff > lowDiff && highDiff > 0 ? highDiff : 0;
            minusDM[i] = lowDiff > highDiff && lowDiff > 0 ? lowDiff : 0;

            tr[i] = Math.max(
                current.high - current.low,
                Math.abs(current.high - previous.close),
                Math.abs(current.low - previous.close)
            );
        }

        let atr = 0;
        let smoothPlusDM = 0;
        let smoothMinusDM = 0;

        for (let i = 1; i <= period; i += 1) {
            atr += tr[i] ?? 0;
            smoothPlusDM += plusDM[i];
            smoothMinusDM += minusDM[i];
        }

        let plusDI = ((smoothPlusDM / atr) * 100) || 0;
        let minusDI = ((smoothMinusDM / atr) * 100) || 0;
        const dxValues = new Array(candles.length).fill(null);
        dxValues[period] = ((Math.abs(plusDI - minusDI) / (plusDI + minusDI || 1)) * 100);

        for (let i = period + 1; i < candles.length; i += 1) {
            atr = atr - (atr / period) + (tr[i] ?? 0);
            smoothPlusDM = smoothPlusDM - (smoothPlusDM / period) + plusDM[i];
            smoothMinusDM = smoothMinusDM - (smoothMinusDM / period) + minusDM[i];

            plusDI = atr === 0 ? 0 : (smoothPlusDM / atr) * 100;
            minusDI = atr === 0 ? 0 : (smoothMinusDM / atr) * 100;

            dxValues[i] = ((Math.abs(plusDI - minusDI) / (plusDI + minusDI || 1)) * 100);
        }

        const adxValues = new Array(candles.length).fill(null);
        const firstAdxIndex = period * 2 - 1;
        const initialSlice = dxValues.slice(period, firstAdxIndex + 1).filter((value) => value !== null);

        if (!initialSlice.length) {
            return { adx: [], plusDI: [], minusDI: [] };
        }

        adxValues[firstAdxIndex] = initialSlice.reduce((sum, value) => sum + value, 0) / initialSlice.length;

        let currentPlus = plusDI;
        let currentMinus = minusDI;
        atr = 0;
        smoothPlusDM = 0;
        smoothMinusDM = 0;

        for (let i = 1; i <= period; i += 1) {
            atr += tr[i] ?? 0;
            smoothPlusDM += plusDM[i];
            smoothMinusDM += minusDM[i];
        }

        const plusValues = new Array(candles.length).fill(null);
        const minusValues = new Array(candles.length).fill(null);

        plusValues[period] = ((smoothPlusDM / atr) * 100) || 0;
        minusValues[period] = ((smoothMinusDM / atr) * 100) || 0;

        for (let i = period + 1; i < candles.length; i += 1) {
            atr = atr - (atr / period) + (tr[i] ?? 0);
            smoothPlusDM = smoothPlusDM - (smoothPlusDM / period) + plusDM[i];
            smoothMinusDM = smoothMinusDM - (smoothMinusDM / period) + minusDM[i];

            currentPlus = atr === 0 ? 0 : (smoothPlusDM / atr) * 100;
            currentMinus = atr === 0 ? 0 : (smoothMinusDM / atr) * 100;
            plusValues[i] = currentPlus;
            minusValues[i] = currentMinus;
        }

        for (let i = firstAdxIndex + 1; i < candles.length; i += 1) {
            adxValues[i] = (((adxValues[i - 1] ?? 0) * (period - 1)) + (dxValues[i] ?? 0)) / period;
        }

        return {
            adx: lineFromValues(candles, adxValues),
            plusDI: lineFromValues(candles, plusValues),
            minusDI: lineFromValues(candles, minusValues),
        };
    }

    function computeIchimokuCloud(data, conversionPeriod = 9, basePeriod = 26, spanBPeriod = 52, displacement = 26) {
        const candles = normalizeCandles(data);
        if (!candles.length) {
            return { conversion: [], base: [], spanA: [], spanB: [], lagging: [] };
        }

        const conversionValues = new Array(candles.length).fill(null);
        const baseValues = new Array(candles.length).fill(null);
        const spanAValues = new Array(candles.length).fill(null);
        const spanBValues = new Array(candles.length).fill(null);
        const laggingValues = new Array(candles.length).fill(null);

        function midpoint(index, period) {
            const start = index - period + 1;
            if (start < 0) {
                return null;
            }

            const window = candles.slice(start, index + 1);
            const highest = Math.max(...window.map((item) => item.high));
            const lowest = Math.min(...window.map((item) => item.low));
            return (highest + lowest) / 2;
        }

        for (let i = 0; i < candles.length; i += 1) {
            conversionValues[i] = midpoint(i, conversionPeriod);
            baseValues[i] = midpoint(i, basePeriod);

            if (conversionValues[i] !== null && baseValues[i] !== null && i + displacement < candles.length) {
                spanAValues[i + displacement] = (conversionValues[i] + baseValues[i]) / 2;
            }

            const spanB = midpoint(i, spanBPeriod);
            if (spanB !== null && i + displacement < candles.length) {
                spanBValues[i + displacement] = spanB;
            }

            if (i - displacement >= 0) {
                laggingValues[i - displacement] = candles[i].close;
            }
        }

        return {
            conversion: lineFromValues(candles, conversionValues),
            base: lineFromValues(candles, baseValues),
            spanA: lineFromValues(candles, spanAValues),
            spanB: lineFromValues(candles, spanBValues),
            lagging: lineFromValues(candles, laggingValues),
        };
    }

    function computeParabolicSAR(data, step = 0.02, maxStep = 0.2) {
        const candles = normalizeCandles(data);
        if (candles.length < 2) {
            return [];
        }

        const psar = new Array(candles.length).fill(null);
        let isUptrend = candles[1].close >= candles[0].close;
        let af = step;
        let ep = isUptrend ? Math.max(candles[0].high, candles[1].high) : Math.min(candles[0].low, candles[1].low);
        psar[1] = isUptrend ? Math.min(candles[0].low, candles[1].low) : Math.max(candles[0].high, candles[1].high);

        for (let i = 2; i < candles.length; i += 1) {
            let current = psar[i - 1] + af * (ep - psar[i - 1]);

            if (isUptrend) {
                current = Math.min(current, candles[i - 1].low, candles[i - 2].low);

                if (candles[i].low < current) {
                    isUptrend = false;
                    current = ep;
                    ep = candles[i].low;
                    af = step;
                } else if (candles[i].high > ep) {
                    ep = candles[i].high;
                    af = Math.min(af + step, maxStep);
                }
            } else {
                current = Math.max(current, candles[i - 1].high, candles[i - 2].high);

                if (candles[i].high > current) {
                    isUptrend = true;
                    current = ep;
                    ep = candles[i].high;
                    af = step;
                } else if (candles[i].low < ep) {
                    ep = candles[i].low;
                    af = Math.min(af + step, maxStep);
                }
            }

            psar[i] = current;
        }

        return lineFromValues(candles, psar);
    }

    function computeOBV(data, signalPeriod = 20) {
        const candles = normalizeCandles(data);
        if (!candles.length) {
            return { obv: [], signal: [] };
        }

        const obvValues = new Array(candles.length).fill(null);
        obvValues[0] = candles[0].volume;

        for (let i = 1; i < candles.length; i += 1) {
            if (candles[i].close > candles[i - 1].close) {
                obvValues[i] = (obvValues[i - 1] ?? 0) + candles[i].volume;
            } else if (candles[i].close < candles[i - 1].close) {
                obvValues[i] = (obvValues[i - 1] ?? 0) - candles[i].volume;
            } else {
                obvValues[i] = obvValues[i - 1] ?? 0;
            }
        }

        const obvLine = lineFromValues(candles, obvValues);

        if (!signalPeriod || signalPeriod < 2) {
            return { obv: obvLine, signal: [] };
        }

        const signalRaw = computeEMA(
            obvValues.map((value, index) => ({
                Date: data[index]?.Date,
                time: candles[index].time,
                Open: value,
                High: value,
                Low: value,
                Close: value,
                Volume: 0,
            })),
            signalPeriod
        );

        return {
            obv: obvLine,
            signal: signalRaw,
        };
    }

    window.normalizeCandles = normalizeCandles;
    window.constantLine = constantLine;
    window.computeSMA = computeSMA;
    window.computeEMA = computeEMA;
    window.computeRSI = computeRSI;
    window.computeBollingerBands = computeBollingerBands;
    window.computeStochasticOscillator = computeStochasticOscillator;
    window.computeADX = computeADX;
    window.computeIchimokuCloud = computeIchimokuCloud;
    window.computeParabolicSAR = computeParabolicSAR;
    window.computeOBV = computeOBV;
})();
