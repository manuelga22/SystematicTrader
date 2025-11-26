'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Slider } from '@/components/ui/slider';
import { NumberInput } from '@/components/ui/number-input';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface BacktestConfigProps {
  startDate: string;
  endDate: string;
  initialCapital: number;
  onStartDateChange: (date: string) => void;
  onEndDateChange: (date: string) => void;
  onInitialCapitalChange: (capital: number) => void;
}

// Date picker component
function DatePicker({
  value,
  onChange,
  label,
  id,
}: {
  value: string;
  onChange: (date: string) => void;
  label: string;
  id: string;
}) {
  const presets = [
    { label: '1M', months: 1 },
    { label: '3M', months: 3 },
    { label: '6M', months: 6 },
    { label: '1Y', months: 12 },
  ];

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      {id === 'startDate' && (
        <div className="flex gap-1">
          {presets.map((preset) => (
            <Button
              key={preset.label}
              variant="ghost"
              size="sm"
              className="text-xs h-7 px-2"
              onClick={() => {
                const start = new Date();
                start.setMonth(start.getMonth() - preset.months);
                onChange(start.toISOString().split('T')[0]);
              }}
            >
              {preset.label} ago
            </Button>
          ))}
        </div>
      )}
      {id === 'endDate' && (
        <div className="flex gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="text-xs h-7 px-2"
            onClick={() => {
              onChange(new Date().toISOString().split('T')[0]);
            }}
          >
            Today
          </Button>
        </div>
      )}
    </div>
  );
}

export default function BacktestConfig({
  startDate,
  endDate,
  initialCapital,
  onStartDateChange,
  onEndDateChange,
  onInitialCapitalChange,
}: BacktestConfigProps) {
  const formatCurrency = (value: number) => {
    return value.toLocaleString('en-US');
  };

  const parseCurrency = (value: string) => {
    return parseInt(value.replace(/,/g, '')) || 0;
  };

  const capitalPresets = [10000, 25000, 50000, 100000, 250000, 500000];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Backtest Configuration</CardTitle>
        <CardDescription>Set the time period and starting capital for your backtest</CardDescription>
      </CardHeader>
      <Separator />
      <CardContent className="pt-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <DatePicker
            id="startDate"
            label="Start Date"
            value={startDate}
            onChange={onStartDateChange}
          />
          <DatePicker
            id="endDate"
            label="End Date"
            value={endDate}
            onChange={onEndDateChange}
          />
        </div>

        <Separator />

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Label htmlFor="initialCapital">Initial Capital</Label>
            <span className="text-2xl font-bold">${formatCurrency(initialCapital)}</span>
          </div>

          <Slider
            value={[initialCapital]}
            onValueChange={([value]) => onInitialCapitalChange(value)}
            min={1000}
            max={1000000}
            step={1000}
            className="py-4"
          />

          <div className="flex items-center gap-2">
            <NumberInput
              id="initialCapital"
              value={initialCapital}
              onChange={onInitialCapitalChange}
              min={1000}
              max={10000000}
              step={1000}
              formatValue={formatCurrency}
              parseValue={parseCurrency}
              className="flex-1"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {capitalPresets.map((preset) => (
              <Button
                key={preset}
                variant={initialCapital === preset ? 'default' : 'outline'}
                size="sm"
                onClick={() => onInitialCapitalChange(preset)}
              >
                ${formatCurrency(preset)}
              </Button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
