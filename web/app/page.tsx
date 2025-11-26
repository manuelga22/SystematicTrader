'use client';

import { useState } from 'react';
import RuleBuilder from './components/RuleBuilder';
import StockSelector from './components/StockSelector';
import BacktestConfig from './components/BacktestConfig';
import BacktestResults from './components/BacktestResults';
import { TradingRule, BacktestResult } from './types/trading';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';

export default function Home() {
  const [rules, setRules] = useState<TradingRule[]>([]);
  const [selectedStocks, setSelectedStocks] = useState<string[]>(['AAPL']);
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState('2024-12-01');
  const [initialCapital, setInitialCapital] = useState(100000);
  const [results, setResults] = useState<BacktestResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('configure');

  const handleAddRule = (rule: TradingRule) => {
    setRules(prevRules => [...prevRules, rule]);
  };

  const handleRemoveRule = (id: string) => {
    setRules(prevRules => prevRules.filter((r) => r.id !== id));
  };

  const handleToggleRule = (id: string) => {
    setRules(prevRules =>
      prevRules.map((r) =>
        r.id === id ? { ...r, enabled: !r.enabled } : r
      )
    );
  };

  const runBacktest = async () => {
    if (selectedStocks.length === 0) {
      setError('Please select at least one stock');
      return;
    }

    if (rules.length === 0) {
      setError('Please add at least one trading rule');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResults(null);

    try {
      // Debug: Log rules being sent
      console.log('[Backtest] Sending rules:', rules.map(r => ({
        name: r.name,
        decision: r.decision,
        quantity: r.quantity
      })));

      const response = await fetch('/api/backtest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          stocks: selectedStocks,
          startDate,
          endDate,
          initialCapital,
          rules,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Backtest failed');
      }

      const data: BacktestResult = await response.json();
      setResults(data);
      setActiveTab('results');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const enabledRules = rules.filter(r => r.enabled);
  const hasBuyRule = enabledRules.some(r => r.decision === 'BUY');
  const hasSellRule = enabledRules.some(r => r.decision === 'SELL');
  const canRunBacktest = selectedStocks.length > 0 && rules.length > 0 && hasBuyRule && hasSellRule;

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto py-8 px-4 max-w-5xl">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold tracking-tight mb-2">
            Strategy Backtester
          </h1>
          <p className="text-muted-foreground text-lg">
            Create cookie-cutter trading rules and backtest them against historical data
          </p>
        </header>

        <Separator className="mb-8" />

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="configure">Configure Strategy</TabsTrigger>
            <TabsTrigger value="results">
              Results
              {results && (
                <span className="ml-2 text-xs bg-primary/20 px-2 py-0.5 rounded-full">
                  {results.totalTrades}
                </span>
              )}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="configure" className="space-y-6">
            <StockSelector
              selectedStocks={selectedStocks}
              onStocksChange={setSelectedStocks}
            />

            <BacktestConfig
              startDate={startDate}
              endDate={endDate}
              initialCapital={initialCapital}
              onStartDateChange={setStartDate}
              onEndDateChange={setEndDate}
              onInitialCapitalChange={setInitialCapital}
            />

            <RuleBuilder
              onAddRule={handleAddRule}
              existingRules={rules}
              onRemoveRule={handleRemoveRule}
              onToggleRule={handleToggleRule}
            />

            {error && (
              <Alert variant="destructive">
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <Separator />

            <div className="space-y-3">
              <Button
                onClick={runBacktest}
                disabled={isLoading || !canRunBacktest}
                size="lg"
                className="w-full"
              >
                {isLoading ? 'Running Backtest...' : 'Run Backtest'}
              </Button>

              {!canRunBacktest && rules.length > 0 && (
                <Alert variant="default" className="border-muted">
                  <AlertDescription className="text-muted-foreground text-center">
                    {!hasBuyRule && !hasSellRule && 'Add both BUY and SELL rules to run backtest'}
                    {hasBuyRule && !hasSellRule && 'Add a SELL rule to run backtest'}
                    {!hasBuyRule && hasSellRule && 'Add a BUY rule to run backtest'}
                  </AlertDescription>
                </Alert>
              )}

              {rules.length === 0 && (
                <Alert variant="default" className="border-muted">
                  <AlertDescription className="text-muted-foreground text-center">
                    Add trading rules using the Quick Start strategies or create custom rules above
                  </AlertDescription>
                </Alert>
              )}
            </div>
          </TabsContent>

          <TabsContent value="results" className="space-y-6">
            <BacktestResults results={results} isLoading={isLoading} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
