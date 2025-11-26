'use client';

import { useState } from 'react';
import { POPULAR_STOCKS } from '../types/trading';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Label } from '@/components/ui/label';

interface StockSelectorProps {
  selectedStocks: string[];
  onStocksChange: (stocks: string[]) => void;
}

export default function StockSelector({
  selectedStocks,
  onStocksChange,
}: StockSelectorProps) {
  const [customStock, setCustomStock] = useState('');

  const toggleStock = (stock: string) => {
    if (selectedStocks.includes(stock)) {
      onStocksChange(selectedStocks.filter((s) => s !== stock));
    } else {
      onStocksChange([...selectedStocks, stock]);
    }
  };

  const addCustomStock = () => {
    const symbol = customStock.toUpperCase().trim();
    if (symbol && !selectedStocks.includes(symbol)) {
      onStocksChange([...selectedStocks, symbol]);
      setCustomStock('');
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Select Stocks</CardTitle>
        <CardDescription>Choose stocks to backtest your strategy against</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label className="text-sm text-muted-foreground mb-2 block">Popular Stocks</Label>
          <div className="flex flex-wrap gap-2">
            {POPULAR_STOCKS.map((stock) => (
              <Button
                key={stock}
                variant={selectedStocks.includes(stock) ? 'default' : 'outline'}
                size="sm"
                onClick={() => toggleStock(stock)}
              >
                {stock}
              </Button>
            ))}
          </div>
        </div>

        <Separator />

        <div className="space-y-2">
          <Label htmlFor="customStock">Add Custom Ticker</Label>
          <div className="flex gap-2">
            <Input
              id="customStock"
              value={customStock}
              onChange={(e) => setCustomStock(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && addCustomStock()}
              placeholder="Enter ticker symbol..."
              className="flex-1"
            />
            <Button variant="secondary" onClick={addCustomStock}>
              Add
            </Button>
          </div>
        </div>

        {selectedStocks.length > 0 && (
          <>
            <Separator />
            <div>
              <Label className="text-sm text-muted-foreground mb-2 block">
                Selected Stocks ({selectedStocks.length})
              </Label>
              <div className="flex flex-wrap gap-2">
                {selectedStocks.map((stock) => (
                  <Badge
                    key={stock}
                    variant="secondary"
                    className="cursor-pointer hover:bg-destructive/20 transition-colors"
                    onClick={() => toggleStock(stock)}
                  >
                    {stock}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-auto p-0 ml-1 text-muted-foreground hover:text-foreground hover:bg-transparent"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleStock(stock);
                      }}
                    >
                      &times;
                    </Button>
                  </Badge>
                ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
