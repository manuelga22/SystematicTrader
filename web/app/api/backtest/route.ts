import { NextRequest, NextResponse } from 'next/server';
import { BacktestConfig, BacktestResult } from '../../types/trading';

// Python backend URL
const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://localhost:8000';

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

    // Call the Python backend
    const response = await fetch(`${PYTHON_API_URL}/backtest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        stocks,
        startDate,
        endDate,
        initialCapital,
        rules,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = errorData.detail || 'Backtest failed on Python backend';
      return NextResponse.json(
        { error: errorMessage },
        { status: response.status }
      );
    }

    const result: BacktestResult = await response.json();
    return NextResponse.json(result);
  } catch (error) {
    console.error('Backtest error:', error);

    // Check if it's a connection error (Python backend not running)
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return NextResponse.json(
        { error: 'Cannot connect to Python backend. Make sure the Python API server is running on port 8000.' },
        { status: 503 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to run backtest. Check if the Python API is running.' },
      { status: 500 }
    );
  }
}
