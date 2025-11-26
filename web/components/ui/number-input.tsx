'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

interface NumberInputProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  formatValue?: (value: number) => string;
  parseValue?: (value: string) => number;
  className?: string;
  id?: string;
}

export function NumberInput({
  value,
  onChange,
  min = 0,
  max = Infinity,
  step = 1,
  formatValue = (v) => v.toString(),
  parseValue = (v) => parseFloat(v) || 0,
  className,
  id,
}: NumberInputProps) {
  const [inputValue, setInputValue] = React.useState(formatValue(value));

  React.useEffect(() => {
    setInputValue(formatValue(value));
  }, [value, formatValue]);

  const increment = () => {
    const newValue = Math.min(max, value + step);
    onChange(newValue);
  };

  const decrement = () => {
    const newValue = Math.max(min, value - step);
    onChange(newValue);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  const handleInputBlur = () => {
    const parsed = parseValue(inputValue);
    const clamped = Math.max(min, Math.min(max, parsed));
    onChange(clamped);
    setInputValue(formatValue(clamped));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleInputBlur();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      increment();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      decrement();
    }
  };

  return (
    <div className={cn('flex items-center gap-1', className)}>
      <Button
        type="button"
        variant="outline"
        size="icon"
        className="h-9 w-7 shrink-0"
        onClick={decrement}
        disabled={value <= min}
      >
        <span className="text-sm font-medium">−</span>
      </Button>
      <Input
        id={id}
        type="text"
        inputMode="numeric"
        value={inputValue}
        onChange={handleInputChange}
        onBlur={handleInputBlur}
        onKeyDown={handleKeyDown}
        className="text-center"
      />
      <Button
        type="button"
        variant="outline"
        size="icon"
        className="h-9 w-7 shrink-0"
        onClick={increment}
        disabled={value >= max}
      >
        <span className="text-sm font-medium">+</span>
      </Button>
    </div>
  );
}
