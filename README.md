# Systematic Trader

A trading strategy backtester with a React/Next.js frontend and Python FastAPI backend.

## Prerequisites

- **Python 3.9+**
- **Node.js 18+**
- **npm**

## Quick Start

### 1. Install Python Dependencies

```bash
cd data_api
pip3 install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd web
npm install
```

### 3. Start the Python API (Terminal 1)

```bash
cd data_api
python3 -m uvicorn data_api.main:app --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

### 4. Start the Frontend (Terminal 2)

```bash
cd web
npm run dev
```

The frontend will be available at http://localhost:3000

## Usage

1. Open http://localhost:3000 in your browser
2. Select stocks to backtest (e.g., AAPL, GOOGL)
3. Set the date range and initial capital
4. Add trading rules:
   - **Simple Rules**: Percentage-based triggers (Buy the Dip, Take Profit, etc.)
   - **Python Rules**: Uses actual trading_rules module (Mean Reversal, Loss/Profit Taker)
5. Click "Run Backtest" to see results

## Project Structure

```
SystematicTrader/
├── data_api/           # Python FastAPI backend
│   ├── data_api/
│   │   ├── main.py           # API endpoints
│   │   ├── backtest_service.py   # Backtesting logic
│   │   └── indicators.py     # Technical indicators
│   └── requirements.txt
├── trading_rules/      # Python trading rule implementations
│   ├── mean_reversal.py
│   ├── early_profit_taker.py
│   ├── early_loss_taker.py
│   └── loss_profit_taker.py
└── web/               # Next.js frontend
    ├── app/
    │   ├── page.tsx
    │   ├── components/
    │   └── api/backtest/
    └── package.json
```

## Available Trading Rules

### Simple Rules (Percentage-based)
- **Buy the Dip** - Buy when price drops by X%
- **Buy on Momentum** - Buy when price rises by X%
- **Take Profit** - Sell when position is up by X%
- **Stop Loss** - Sell when position is down by X%

### Python Rules (from trading_rules module)
- **Mean Reversal** - Buy when short-term average < long-term average
- **Early Profit Taker** - Sell when profit threshold is reached
- **Early Loss Taker** - Sell when loss threshold is exceeded
- **Loss/Profit Taker** - Combined stop-loss and take-profit
