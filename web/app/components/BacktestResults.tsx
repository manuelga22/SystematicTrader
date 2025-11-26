'use client';

import { BacktestResult, Trade } from '../types/trading';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';

interface BacktestResultsProps {
  results: BacktestResult | null;
  isLoading: boolean;
}

function StatCard({
  title,
  value,
  variant = 'default',
}: {
  title: string;
  value: string;
  variant?: 'default' | 'success' | 'destructive';
}) {
  const valueClasses = {
    default: 'text-foreground',
    success: 'text-green-500',
    destructive: 'text-red-500',
  };

  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-sm text-muted-foreground">{title}</p>
        <p className={`text-2xl font-bold ${valueClasses[variant]}`}>{value}</p>
      </CardContent>
    </Card>
  );
}

function LoadingSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-4 w-60" />
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <Skeleton className="h-4 w-20 mb-2" />
                <Skeleton className="h-8 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default function BacktestResults({ results, isLoading }: BacktestResultsProps) {
  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (!results) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16">
          <p className="text-muted-foreground text-center">
            Configure your rules and run a backtest to see results
          </p>
        </CardContent>
      </Card>
    );
  }

  const winRate = results.totalTrades > 0
    ? ((results.winningTrades / results.totalTrades) * 100).toFixed(1)
    : '0';

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Backtest Results</CardTitle>
          <CardDescription>Performance summary of your trading strategy</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              title="Total P&L"
              value={`$${results.totalPnL.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
              variant={results.totalPnL >= 0 ? 'success' : 'destructive'}
            />
            <StatCard
              title="Return"
              value={`${results.percentReturn >= 0 ? '+' : ''}${results.percentReturn.toFixed(2)}%`}
              variant={results.percentReturn >= 0 ? 'success' : 'destructive'}
            />
            <StatCard title="Total Trades" value={results.totalTrades.toString()} />
            <StatCard title="Win Rate" value={`${winRate}%`} />
            <StatCard
              title="Winning Trades"
              value={results.winningTrades.toString()}
              variant="success"
            />
            <StatCard
              title="Losing Trades"
              value={results.losingTrades.toString()}
              variant="destructive"
            />
            <StatCard
              title="Max Drawdown"
              value={`-${results.maxDrawdown.toFixed(2)}%`}
              variant="destructive"
            />
            <StatCard
              title="Final Portfolio"
              value={`$${results.portfolioValue[results.portfolioValue.length - 1]?.toLocaleString('en-US', { minimumFractionDigits: 2 }) || '0.00'}`}
            />
          </div>
        </CardContent>
      </Card>

      {results.trades.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Trade History</CardTitle>
            <CardDescription>
              Showing {Math.min(50, results.trades.length)} of {results.trades.length} trades
            </CardDescription>
          </CardHeader>
          <Separator />
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Stock</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead className="text-right">Price</TableHead>
                  <TableHead className="text-right">Qty</TableHead>
                  <TableHead className="text-right">P&L</TableHead>
                  <TableHead>Rule</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {results.trades.slice(0, 50).map((trade: Trade) => (
                  <TableRow key={trade.id}>
                    <TableCell className="text-muted-foreground">
                      {new Date(trade.timestamp).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="font-medium">{trade.stock}</TableCell>
                    <TableCell>
                      <Badge variant={trade.decision === 'BUY' ? 'default' : 'destructive'}>
                        {trade.decision}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">${trade.price.toFixed(2)}</TableCell>
                    <TableCell className="text-right">{trade.quantity}</TableCell>
                    <TableCell
                      className={`text-right font-medium ${
                        (trade.pnl ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'
                      }`}
                    >
                      {trade.pnl != null
                        ? `${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)}`
                        : '-'}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-xs max-w-[150px] truncate">
                      {trade.ruleTriggered}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
