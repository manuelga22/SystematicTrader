import { NextRequest, NextResponse } from 'next/server';
import { BacktestConfig, BacktestResult, Trade, TradingRule } from '../../types/trading';

// Seeded random number generator for consistent results
function seededRandom(seed: number): () => number {
  return function() {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    return seed / 0x7fffffff;
  };
}

// Generate consistent price data for a stock
function generatePriceData(
  stock: string,
  startDate: string,
  endDate: string,
  intervalMinutes: number
): { timestamp: string; price: number; volume: number }[] {
  const start = new Date(startDate);
  const end = new Date(endDate);
  const data: { timestamp: string; price: number; volume: number }[] = [];

  // Create a seed based on stock symbol for consistent data
  const seed = stock.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) * 12345;
  const random = seededRandom(seed);

  // Base price varies by stock
  const basePrice = (stock.charCodeAt(0) * stock.charCodeAt(1)) % 300 + 100;
  let price = basePrice;
  let prevVolume = 500000;

  const current = new Date(start);
  while (current <= end) {
    const day = current.getDay();
    const hour = current.getHours();

    // Skip weekends and non-trading hours for intraday
    if (day !== 0 && day !== 6) {
      if (intervalMinutes >= 1440 || (hour >= 9 && hour < 16)) {
        // More realistic price movements (can be -5% to +5%)
        const volatility = 0.03 + random() * 0.04; // 3-7% volatility
        const direction = random() > 0.48 ? 1 : -1; // slight upward bias
        const change = direction * random() * volatility;
        price = Math.max(1, price * (1 + change));

        // Volume with some correlation to price moves
        const volumeChange = (random() - 0.5) * 0.5;
        prevVolume = Math.max(100000, prevVolume * (1 + volumeChange));

        data.push({
          timestamp: current.toISOString(),
          price: parseFloat(price.toFixed(2)),
          volume: Math.floor(prevVolume),
        });
      }
    }

    current.setMinutes(current.getMinutes() + intervalMinutes);
  }

  return data;
}

function getIntervalMinutes(timeframe: string): number {
  const map: Record<string, number> = {
    '1Min': 1,
    '5Min': 5,
    '15Min': 15,
    '30Min': 30,
    '1H': 60,
    '4H': 240,
    '1D': 1440,
    '1W': 10080,
  };
  return map[timeframe] || 60;
}

interface Position {
  entryPrice: number;
  quantity: number;
  entryTimestamp: string;
}

export async function POST(request: NextRequest) {
  try {
    const config: BacktestConfig = await request.json();
    const { stocks, startDate, endDate, initialCapital, rules } = config;

    if (!stocks.length || !rules.length) {
      return NextResponse.json(
        { error: 'Please select at least one stock and add at least one rule' },
        { status: 400 }
      );
    }

    const enabledRules = rules.filter((r) => r.enabled);
    if (!enabledRules.length) {
      return NextResponse.json(
        { error: 'Please enable at least one rule' },
        { status: 400 }
      );
    }

    // Separate buy and sell rules
    const buyRules = enabledRules.filter((r) => r.decision === 'BUY');
    const sellRules = enabledRules.filter((r) => r.decision === 'SELL');

    const trades: Trade[] = [];
    let cash = initialCapital;
    const positions: Record<string, Position> = {};
    const portfolioValues: number[] = [initialCapital];
    const timestamps: string[] = [startDate];

    // Pre-generate all price data once
    const stockPriceData: Record<string, { timestamp: string; price: number; volume: number }[]> = {};
    const minInterval = Math.min(...enabledRules.map((r) => getIntervalMinutes(r.timeframe)), 60);

    for (const stock of stocks) {
      stockPriceData[stock] = generatePriceData(stock, startDate, endDate, minInterval);
    }

    // Find the maximum data length across all stocks
    const maxDataLength = Math.max(...Object.values(stockPriceData).map((d) => d.length));

    // Process each time step
    for (let i = 1; i < maxDataLength; i++) {
      for (const stock of stocks) {
        const priceData = stockPriceData[stock];
        if (i >= priceData.length) continue;

        const current = priceData[i];
        const previous = priceData[i - 1];

        // Calculate changes
        const priceChange = ((current.price - previous.price) / previous.price) * 100;
        const volumeChange = ((current.volume - previous.volume) / previous.volume) * 100;

        // Check position-based metrics if we have a position
        const position = positions[stock];
        let positionPnLPercent = 0;
        if (position) {
          positionPnLPercent = ((current.price - position.entryPrice) / position.entryPrice) * 100;
        }

        // Evaluate BUY rules (only if not holding)
        if (!position) {
          for (const rule of buyRules) {
            let triggered = false;

            switch (rule.changeType) {
              case 'price_increase':
                triggered = priceChange >= rule.changePercent;
                break;
              case 'price_decrease':
                triggered = priceChange <= -rule.changePercent;
                break;
              case 'volume_increase':
                triggered = volumeChange >= rule.changePercent;
                break;
              case 'volume_decrease':
                triggered = volumeChange <= -rule.changePercent;
                break;
            }

            if (triggered) {
              const cost = current.price * rule.quantity;
              if (cash >= cost) {
                cash -= cost;
                positions[stock] = {
                  entryPrice: current.price,
                  quantity: rule.quantity,
                  entryTimestamp: current.timestamp,
                };

                trades.push({
                  id: `trade-${i}-${stock}-buy`,
                  timestamp: current.timestamp,
                  stock,
                  decision: 'BUY',
                  price: current.price,
                  quantity: rule.quantity,
                  ruleTriggered: rule.name,
                });
                break; // Only execute one buy per stock per timestep
              }
            }
          }
        }

        // Evaluate SELL rules (only if holding)
        if (positions[stock]) {
          const pos = positions[stock];

          for (const rule of sellRules) {
            let triggered = false;

            // For sell rules, also consider position P&L
            switch (rule.changeType) {
              case 'price_increase':
                // Sell on profit - check if position is up by threshold
                triggered = positionPnLPercent >= rule.changePercent;
                break;
              case 'price_decrease':
                // Sell on loss - check if position is down by threshold
                triggered = positionPnLPercent <= -rule.changePercent;
                break;
              case 'volume_increase':
                triggered = volumeChange >= rule.changePercent;
                break;
              case 'volume_decrease':
                triggered = volumeChange <= -rule.changePercent;
                break;
            }

            if (triggered) {
              const revenue = current.price * pos.quantity;
              const pnl = (current.price - pos.entryPrice) * pos.quantity;

              cash += revenue;
              delete positions[stock];

              trades.push({
                id: `trade-${i}-${stock}-sell`,
                timestamp: current.timestamp,
                stock,
                decision: 'SELL',
                price: current.price,
                quantity: pos.quantity,
                ruleTriggered: rule.name,
                pnl,
              });
              break; // Only execute one sell per stock per timestep
            }
          }
        }
      }

      // Record portfolio value periodically
      if (i % Math.max(1, Math.floor(maxDataLength / 100)) === 0) {
        let portfolioValue = cash;
        for (const [stock, pos] of Object.entries(positions)) {
          const priceData = stockPriceData[stock];
          const currentPrice = priceData[Math.min(i, priceData.length - 1)]?.price || 0;
          portfolioValue += currentPrice * pos.quantity;
        }
        portfolioValues.push(portfolioValue);
        timestamps.push(stockPriceData[stocks[0]][Math.min(i, stockPriceData[stocks[0]].length - 1)]?.timestamp || endDate);
      }
    }

    // Close any remaining positions at end
    for (const [stock, position] of Object.entries(positions)) {
      const priceData = stockPriceData[stock];
      const finalPrice = priceData[priceData.length - 1]?.price || position.entryPrice;
      const pnl = (finalPrice - position.entryPrice) * position.quantity;
      cash += finalPrice * position.quantity;

      trades.push({
        id: `trade-final-${stock}`,
        timestamp: endDate,
        stock,
        decision: 'SELL',
        price: finalPrice,
        quantity: position.quantity,
        ruleTriggered: 'End of Backtest',
        pnl,
      });
    }

    // Calculate metrics
    const sellTrades = trades.filter((t) => t.decision === 'SELL' && t.pnl !== undefined);
    const winningTrades = sellTrades.filter((t) => (t.pnl || 0) > 0).length;
    const losingTrades = sellTrades.filter((t) => (t.pnl || 0) < 0).length;
    const totalPnL = sellTrades.reduce((sum, t) => sum + (t.pnl || 0), 0);
    const percentReturn = ((cash - initialCapital) / initialCapital) * 100;

    // Calculate max drawdown
    let peak = initialCapital;
    let maxDrawdown = 0;
    for (const value of portfolioValues) {
      if (value > peak) peak = value;
      const drawdown = ((peak - value) / peak) * 100;
      if (drawdown > maxDrawdown) maxDrawdown = drawdown;
    }

    portfolioValues.push(cash);
    timestamps.push(endDate);

    const result: BacktestResult = {
      totalTrades: trades.length,
      winningTrades,
      losingTrades,
      totalPnL: parseFloat(totalPnL.toFixed(2)),
      percentReturn: parseFloat(percentReturn.toFixed(2)),
      maxDrawdown: parseFloat(maxDrawdown.toFixed(2)),
      trades,
      portfolioValue: portfolioValues,
      timestamps,
    };

    return NextResponse.json(result);
  } catch (error) {
    console.error('Backtest error:', error);
    return NextResponse.json(
      { error: 'Failed to run backtest' },
      { status: 500 }
    );
  }
}
