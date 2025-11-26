export type TimeframeOption = '1Min' | '5Min' | '15Min' | '30Min' | '1H' | '4H' | '1D' | '1W';

export type ChangeType = 'price_increase' | 'price_decrease' | 'volume_increase' | 'volume_decrease';

export type Decision = 'BUY' | 'SELL';

export type RuleType = 'early_profit_taker' | 'early_loss_taker' | 'mean_reversal' | 'loss_profit_taker' | 'custom';

// Python trading rule types (maps to trading_rules module)
export type PythonRuleType = 'mean_reversal' | 'early_profit_taker' | 'early_loss_taker' | 'loss_profit_taker' | null;

// Parameters for Python trading rules
export interface RuleParams {
  shortWindow?: number;  // For mean reversal
  longWindow?: number;   // For mean reversal
  profitThreshold?: number;  // For profit taker (decimal, e.g., 0.02 = 2%)
  lossThreshold?: number;    // For loss taker (decimal, e.g., 0.02 = 2%)
}

export interface TradingRule {
  id: string;
  name: string;
  ruleType: RuleType;
  timeframe: TimeframeOption;
  changeType?: ChangeType;  // Optional for Python rules
  changePercent?: number;   // Optional for Python rules
  decision: Decision;
  quantity: number;
  enabled: boolean;
  // New fields for Python trading rules
  pythonRuleType?: PythonRuleType;
  params?: RuleParams;
}

export interface BacktestConfig {
  stocks: string[];
  startDate: string;
  endDate: string;
  initialCapital: number;
  rules: TradingRule[];
}

export interface Trade {
  id: string;
  timestamp: string;
  stock: string;
  decision: Decision;
  price: number;
  quantity: number;
  ruleTriggered: string;
  pnl?: number;
}

export interface BacktestResult {
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  totalPnL: number;
  percentReturn: number;
  maxDrawdown: number;
  trades: Trade[];
  portfolioValue: number[];
  timestamps: string[];
}

export const TIMEFRAME_OPTIONS: { value: TimeframeOption; label: string }[] = [
  { value: '1Min', label: '1 Minute' },
  { value: '5Min', label: '5 Minutes' },
  { value: '15Min', label: '15 Minutes' },
  { value: '30Min', label: '30 Minutes' },
  { value: '1H', label: '1 Hour' },
  { value: '4H', label: '4 Hours' },
  { value: '1D', label: '1 Day' },
  { value: '1W', label: '1 Week' },
];

export const CHANGE_TYPE_OPTIONS: { value: ChangeType; label: string }[] = [
  { value: 'price_increase', label: 'Price Increase' },
  { value: 'price_decrease', label: 'Price Decrease' },
  { value: 'volume_increase', label: 'Volume Increase' },
  { value: 'volume_decrease', label: 'Volume Decrease' },
];

export const RULE_TYPE_OPTIONS: { value: RuleType; label: string; description: string }[] = [
  { value: 'early_profit_taker', label: 'Early Profit Taker', description: 'Sell when profit threshold is reached' },
  { value: 'early_loss_taker', label: 'Early Loss Taker', description: 'Sell when loss threshold is exceeded' },
  { value: 'mean_reversal', label: 'Mean Reversal', description: 'Buy when price is below moving average' },
  { value: 'loss_profit_taker', label: 'Loss/Profit Taker', description: 'Combined stop-loss and take-profit' },
  { value: 'custom', label: 'Custom Rule', description: 'Create your own rule with custom parameters' },
];

export const POPULAR_STOCKS = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'NFLX', 'TSLA', 'META', 'NVDA'];
