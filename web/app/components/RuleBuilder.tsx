'use client';

import { useState, useEffect } from 'react';
import {
  TradingRule,
  TimeframeOption,
  ChangeType,
  Decision,
  PythonRuleType,
  RuleParams,
  TIMEFRAME_OPTIONS,
  CHANGE_TYPE_OPTIONS,
} from '../types/trading';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import { NumberInput } from '@/components/ui/number-input';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface RuleBuilderProps {
  onAddRule: (rule: TradingRule) => void;
  existingRules: TradingRule[];
  onRemoveRule: (id: string) => void;
  onToggleRule: (id: string) => void;
}

// Simple rule types (percentage-based triggers)
const SIMPLE_RULE_TYPES = [
  {
    value: 'buy_the_dip',
    label: 'Buy the Dip',
    description: 'Buy when price drops by a certain %',
    decision: 'BUY' as Decision,
    changeType: 'price_decrease' as ChangeType,
    thresholdLabel: 'Buy when price drops',
  },
  {
    value: 'buy_momentum',
    label: 'Buy on Momentum',
    description: 'Buy when price rises by a certain %',
    decision: 'BUY' as Decision,
    changeType: 'price_increase' as ChangeType,
    thresholdLabel: 'Buy when price rises',
  },
  {
    value: 'take_profit',
    label: 'Take Profit',
    description: 'Sell when your position is up by a certain %',
    decision: 'SELL' as Decision,
    changeType: 'price_increase' as ChangeType,
    thresholdLabel: 'Sell when up',
  },
  {
    value: 'stop_loss',
    label: 'Stop Loss',
    description: 'Sell when your position is down by a certain %',
    decision: 'SELL' as Decision,
    changeType: 'price_decrease' as ChangeType,
    thresholdLabel: 'Sell when down',
  },
];

// Python trading rules (from trading_rules module)
const PYTHON_RULE_TYPES = [
  {
    value: 'mean_reversal' as PythonRuleType,
    label: 'Mean Reversal',
    description: 'Buy when short-term average < long-term average (price below trend)',
    decision: 'BUY' as Decision,
    hasShortWindow: true,
    hasLongWindow: true,
  },
  {
    value: 'early_profit_taker' as PythonRuleType,
    label: 'Early Profit Taker',
    description: 'Sell when position profit exceeds threshold',
    decision: 'SELL' as Decision,
    hasProfitThreshold: true,
  },
  {
    value: 'early_loss_taker' as PythonRuleType,
    label: 'Early Loss Taker',
    description: 'Sell when position loss exceeds threshold (stop loss)',
    decision: 'SELL' as Decision,
    hasLossThreshold: true,
  },
  {
    value: 'loss_profit_taker' as PythonRuleType,
    label: 'Loss/Profit Taker',
    description: 'Sell on either profit or loss threshold (combines both)',
    decision: 'SELL' as Decision,
    hasProfitThreshold: true,
    hasLossThreshold: true,
  },
];

type SimpleRuleType = 'buy_the_dip' | 'buy_momentum' | 'take_profit' | 'stop_loss';

export default function RuleBuilder({
  onAddRule,
  existingRules,
  onRemoveRule,
  onToggleRule,
}: RuleBuilderProps) {
  // Simple rule state
  const [simpleRuleType, setSimpleRuleType] = useState<SimpleRuleType>('buy_the_dip');
  const [changePercent, setChangePercent] = useState(3);

  // Python rule state
  const [pythonRuleType, setPythonRuleType] = useState<PythonRuleType>('mean_reversal');
  const [shortWindow, setShortWindow] = useState(5);
  const [longWindow, setLongWindow] = useState(20);
  const [profitThreshold, setProfitThreshold] = useState(2);
  const [lossThreshold, setLossThreshold] = useState(2);

  // Common state
  const [timeframe, setTimeframe] = useState<TimeframeOption>('1D');
  const [quantity, setQuantity] = useState(100);
  const [ruleName, setRuleName] = useState('');

  const currentSimpleConfig = SIMPLE_RULE_TYPES.find(r => r.value === simpleRuleType)!;
  const currentPythonConfig = PYTHON_RULE_TYPES.find(r => r.value === pythonRuleType);

  // Add simple rule
  const handleAddSimpleRule = () => {
    const newRule: TradingRule = {
      id: `rule-${Date.now()}`,
      name: ruleName || currentSimpleConfig.label,
      ruleType: 'custom',
      timeframe,
      changeType: currentSimpleConfig.changeType,
      changePercent,
      decision: currentSimpleConfig.decision,
      quantity,
      enabled: true,
    };
    onAddRule(newRule);
    setRuleName('');
  };

  // Add Python rule
  const handleAddPythonRule = () => {
    if (!currentPythonConfig) return;

    const params: RuleParams = {};
    if (currentPythonConfig.hasShortWindow) params.shortWindow = shortWindow;
    if (currentPythonConfig.hasLongWindow) params.longWindow = longWindow;
    if (currentPythonConfig.hasProfitThreshold) params.profitThreshold = profitThreshold / 100;
    if (currentPythonConfig.hasLossThreshold) params.lossThreshold = lossThreshold / 100;

    const newRule: TradingRule = {
      id: `rule-${Date.now()}`,
      name: ruleName || currentPythonConfig.label,
      ruleType: pythonRuleType as any,
      timeframe,
      decision: currentPythonConfig.decision,
      quantity,
      enabled: true,
      pythonRuleType,
      params,
    };
    onAddRule(newRule);
    setRuleName('');
  };

  // Preset strategies using Python rules
  const addPresetStrategy = (preset: 'mean_reversion_python' | 'mean_reversion' | 'momentum' | 'conservative') => {
    if (preset === 'mean_reversion_python') {
      // Uses actual Python trading rules
      const rules = [
        {
          name: 'Mean Reversal Entry',
          decision: 'BUY' as Decision,
          pythonRuleType: 'mean_reversal' as PythonRuleType,
          params: { shortWindow: 5, longWindow: 20 },
        },
        {
          name: 'Loss/Profit Exit',
          decision: 'SELL' as Decision,
          pythonRuleType: 'loss_profit_taker' as PythonRuleType,
          params: { profitThreshold: 0.03, lossThreshold: 0.02 },
        },
      ];
      rules.forEach((rule, index) => {
        setTimeout(() => {
          onAddRule({
            id: `rule-${Date.now()}-${index}`,
            name: rule.name,
            ruleType: rule.pythonRuleType as any,
            timeframe: '1D',
            decision: rule.decision,
            quantity: 100,
            enabled: true,
            pythonRuleType: rule.pythonRuleType,
            params: rule.params,
          });
        }, index * 10);
      });
      return;
    }

    // Simple percentage-based presets
    const presets = {
      mean_reversion: [
        { name: 'Buy the Dip (3%)', decision: 'BUY' as Decision, changeType: 'price_decrease' as ChangeType, changePercent: 3 },
        { name: 'Take Profit (2%)', decision: 'SELL' as Decision, changeType: 'price_increase' as ChangeType, changePercent: 2 },
      ],
      momentum: [
        { name: 'Buy Momentum (2%)', decision: 'BUY' as Decision, changeType: 'price_increase' as ChangeType, changePercent: 2 },
        { name: 'Take Profit (3%)', decision: 'SELL' as Decision, changeType: 'price_increase' as ChangeType, changePercent: 3 },
        { name: 'Stop Loss (2%)', decision: 'SELL' as Decision, changeType: 'price_decrease' as ChangeType, changePercent: 2 },
      ],
      conservative: [
        { name: 'Buy Dip (2%)', decision: 'BUY' as Decision, changeType: 'price_decrease' as ChangeType, changePercent: 2 },
        { name: 'Take Profit (5%)', decision: 'SELL' as Decision, changeType: 'price_increase' as ChangeType, changePercent: 5 },
        { name: 'Stop Loss (3%)', decision: 'SELL' as Decision, changeType: 'price_decrease' as ChangeType, changePercent: 3 },
      ],
    };

    presets[preset].forEach((rule, index) => {
      setTimeout(() => {
        onAddRule({
          id: `rule-${Date.now()}-${index}`,
          name: rule.name,
          ruleType: 'custom',
          timeframe: '1D',
          changeType: rule.changeType,
          changePercent: rule.changePercent,
          decision: rule.decision,
          quantity: 100,
          enabled: true,
        });
      }, index * 10);
    });
  };

  const enabledRules = existingRules.filter(r => r.enabled);
  const hasBuyRule = enabledRules.some(r => r.decision === 'BUY');
  const hasSellRule = enabledRules.some(r => r.decision === 'SELL');

  return (
    <TooltipProvider>
      <div className="space-y-6">
        {/* Quick Start Presets */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Start Strategies</CardTitle>
            <CardDescription>Add a complete buy + sell strategy with one click</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    onClick={() => addPresetStrategy('mean_reversion_python')}
                    className="border-yellow-500/50 text-yellow-400 hover:bg-yellow-500/10"
                  >
                    ⚡ Mean Reversal (Python)
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Uses actual Python trading rules: Mean Reversal entry + Loss/Profit exit</p>
                </TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    onClick={() => addPresetStrategy('mean_reversion')}
                    className="border-purple-500/50 text-purple-400 hover:bg-purple-500/10"
                  >
                    Mean Reversion
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Buy on 3% dip, sell on 2% recovery</p>
                </TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    onClick={() => addPresetStrategy('momentum')}
                    className="border-blue-500/50 text-blue-400 hover:bg-blue-500/10"
                  >
                    Momentum
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Buy on 2% rise, sell on 3% profit or 2% loss</p>
                </TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    onClick={() => addPresetStrategy('conservative')}
                    className="border-green-500/50 text-green-400 hover:bg-green-500/10"
                  >
                    Conservative
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Buy on 2% dip, take profit at 5%, stop loss at 3%</p>
                </TooltipContent>
              </Tooltip>
            </div>
          </CardContent>
        </Card>

        {/* Rule Builder with Tabs */}
        <Card>
          <CardHeader>
            <CardTitle>Create Rule</CardTitle>
            <CardDescription>Build custom trading rules</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="simple" className="space-y-4">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="simple">Simple Rules</TabsTrigger>
                <TabsTrigger value="python">Python Rules</TabsTrigger>
              </TabsList>

              {/* Simple Rules Tab */}
              <TabsContent value="simple" className="space-y-4">
                <div className="space-y-2">
                  <Label>Rule Type</Label>
                  <div className="grid grid-cols-2 gap-2">
                    {SIMPLE_RULE_TYPES.map((ruleType) => (
                      <Button
                        key={ruleType.value}
                        variant={simpleRuleType === ruleType.value ? 'default' : 'outline'}
                        className={`h-auto py-3 flex flex-col items-start text-left ${
                          simpleRuleType === ruleType.value
                            ? ''
                            : ruleType.decision === 'BUY'
                              ? 'border-green-500/30 hover:border-green-500/50'
                              : 'border-red-500/30 hover:border-red-500/50'
                        }`}
                        onClick={() => setSimpleRuleType(ruleType.value as SimpleRuleType)}
                      >
                        <span className="font-medium">{ruleType.label}</span>
                        <span className="text-xs text-muted-foreground font-normal">
                          {ruleType.decision === 'BUY' ? 'Entry rule' : 'Exit rule'}
                        </span>
                      </Button>
                    ))}
                  </div>
                </div>

                <Separator />

                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>{currentSimpleConfig.thresholdLabel}</Label>
                    <div className="flex items-center gap-2">
                      <NumberInput
                        value={changePercent}
                        onChange={setChangePercent}
                        min={0.1}
                        max={100}
                        step={0.5}
                        formatValue={(v) => v.toFixed(1)}
                        parseValue={(v) => parseFloat(v) || 0}
                      />
                      <span className="text-2xl font-bold text-muted-foreground">%</span>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {[1, 2, 3, 5, 10].map((pct) => (
                      <Button
                        key={pct}
                        variant={changePercent === pct ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setChangePercent(pct)}
                      >
                        {pct}%
                      </Button>
                    ))}
                  </div>
                </div>

                <Separator />

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Timeframe</Label>
                    <Select value={timeframe} onValueChange={(v) => setTimeframe(v as TimeframeOption)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {TIMEFRAME_OPTIONS.map((opt) => (
                          <SelectItem key={opt.value} value={opt.value}>
                            {opt.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Shares per Trade</Label>
                    <NumberInput
                      value={quantity}
                      onChange={setQuantity}
                      min={1}
                      max={10000}
                      step={10}
                    />
                  </div>
                </div>

                <Button onClick={handleAddSimpleRule} className="w-full" size="lg">
                  <Badge variant={currentSimpleConfig.decision === 'BUY' ? 'default' : 'destructive'} className="mr-2">
                    {currentSimpleConfig.decision}
                  </Badge>
                  Add {currentSimpleConfig.label} Rule
                </Button>
              </TabsContent>

              {/* Python Rules Tab */}
              <TabsContent value="python" className="space-y-4">
                <Alert className="border-yellow-500/50 bg-yellow-500/10">
                  <AlertDescription className="text-yellow-500">
                    These rules use the actual Python trading_rules module for signal generation.
                  </AlertDescription>
                </Alert>

                <div className="space-y-2">
                  <Label>Python Rule Type</Label>
                  <div className="grid grid-cols-2 gap-2">
                    {PYTHON_RULE_TYPES.map((ruleType) => (
                      <Button
                        key={ruleType.value}
                        variant={pythonRuleType === ruleType.value ? 'default' : 'outline'}
                        className={`h-auto py-3 flex flex-col items-start text-left ${
                          pythonRuleType === ruleType.value
                            ? ''
                            : ruleType.decision === 'BUY'
                              ? 'border-green-500/30 hover:border-green-500/50'
                              : 'border-red-500/30 hover:border-red-500/50'
                        }`}
                        onClick={() => setPythonRuleType(ruleType.value)}
                      >
                        <span className="font-medium">{ruleType.label}</span>
                        <span className="text-xs text-muted-foreground font-normal">
                          {ruleType.decision === 'BUY' ? 'Entry rule' : 'Exit rule'}
                        </span>
                      </Button>
                    ))}
                  </div>
                </div>

                {currentPythonConfig && (
                  <p className="text-sm text-muted-foreground">{currentPythonConfig.description}</p>
                )}

                <Separator />

                {/* Mean Reversal Parameters */}
                {currentPythonConfig?.hasShortWindow && (
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Short Window (periods)</Label>
                      <NumberInput
                        value={shortWindow}
                        onChange={setShortWindow}
                        min={2}
                        max={50}
                        step={1}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Long Window (periods)</Label>
                      <NumberInput
                        value={longWindow}
                        onChange={setLongWindow}
                        min={5}
                        max={200}
                        step={1}
                      />
                    </div>
                  </div>
                )}

                {/* Profit Threshold */}
                {currentPythonConfig?.hasProfitThreshold && (
                  <div className="space-y-2">
                    <Label>Profit Threshold</Label>
                    <div className="flex items-center gap-2">
                      <NumberInput
                        value={profitThreshold}
                        onChange={setProfitThreshold}
                        min={0.1}
                        max={100}
                        step={0.5}
                        formatValue={(v) => v.toFixed(1)}
                        parseValue={(v) => parseFloat(v) || 0}
                      />
                      <span className="text-2xl font-bold text-muted-foreground">%</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {[1, 2, 3, 5, 10].map((pct) => (
                        <Button
                          key={pct}
                          variant={profitThreshold === pct ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => setProfitThreshold(pct)}
                        >
                          {pct}%
                        </Button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Loss Threshold */}
                {currentPythonConfig?.hasLossThreshold && (
                  <div className="space-y-2">
                    <Label>Loss Threshold</Label>
                    <div className="flex items-center gap-2">
                      <NumberInput
                        value={lossThreshold}
                        onChange={setLossThreshold}
                        min={0.1}
                        max={100}
                        step={0.5}
                        formatValue={(v) => v.toFixed(1)}
                        parseValue={(v) => parseFloat(v) || 0}
                      />
                      <span className="text-2xl font-bold text-muted-foreground">%</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {[1, 2, 3, 5, 10].map((pct) => (
                        <Button
                          key={pct}
                          variant={lossThreshold === pct ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => setLossThreshold(pct)}
                        >
                          {pct}%
                        </Button>
                      ))}
                    </div>
                  </div>
                )}

                <Separator />

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Timeframe</Label>
                    <Select value={timeframe} onValueChange={(v) => setTimeframe(v as TimeframeOption)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {TIMEFRAME_OPTIONS.map((opt) => (
                          <SelectItem key={opt.value} value={opt.value}>
                            {opt.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Shares per Trade</Label>
                    <NumberInput
                      value={quantity}
                      onChange={setQuantity}
                      min={1}
                      max={10000}
                      step={10}
                    />
                  </div>
                </div>

                <Button onClick={handleAddPythonRule} className="w-full" size="lg">
                  <Badge variant={currentPythonConfig?.decision === 'BUY' ? 'default' : 'destructive'} className="mr-2">
                    {currentPythonConfig?.decision}
                  </Badge>
                  Add {currentPythonConfig?.label} Rule
                </Button>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Active Rules */}
        {existingRules.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Active Rules</CardTitle>
              <CardDescription>
                {existingRules.length} rule{existingRules.length !== 1 ? 's' : ''} configured
                {hasBuyRule && hasSellRule && ' - Ready to backtest!'}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {existingRules.length > 0 && (!hasBuyRule || !hasSellRule) && (
                <Alert variant="default" className="border-yellow-500/50 bg-yellow-500/10">
                  <AlertDescription className="text-yellow-500">
                    {!hasBuyRule && !hasSellRule && 'Add both entry (BUY) and exit (SELL) rules to complete trades.'}
                    {hasBuyRule && !hasSellRule && 'Add an exit rule (Take Profit or Stop Loss) to close positions.'}
                    {!hasBuyRule && hasSellRule && 'Add an entry rule (Buy the Dip or Buy Momentum) to open positions.'}
                  </AlertDescription>
                </Alert>
              )}

              <div className="space-y-3">
                {existingRules.map((rule) => (
                  <Card key={rule.id} className={`transition-opacity ${!rule.enabled ? 'opacity-50' : ''}`}>
                    <CardContent className="flex items-center justify-between p-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <Badge variant={rule.decision === 'BUY' ? 'default' : 'destructive'}>
                            {rule.decision === 'BUY' ? 'ENTRY' : 'EXIT'}
                          </Badge>
                          {rule.pythonRuleType && (
                            <Badge variant="outline" className="border-yellow-500/50 text-yellow-500">
                              Python
                            </Badge>
                          )}
                          <span className="font-medium">{rule.name}</span>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          {rule.pythonRuleType ? (
                            <>
                              {rule.pythonRuleType === 'mean_reversal' &&
                                `Short: ${rule.params?.shortWindow}, Long: ${rule.params?.longWindow}`}
                              {rule.pythonRuleType === 'early_profit_taker' &&
                                `Profit threshold: ${((rule.params?.profitThreshold || 0) * 100).toFixed(1)}%`}
                              {rule.pythonRuleType === 'early_loss_taker' &&
                                `Loss threshold: ${((rule.params?.lossThreshold || 0) * 100).toFixed(1)}%`}
                              {rule.pythonRuleType === 'loss_profit_taker' &&
                                `Profit: ${((rule.params?.profitThreshold || 0) * 100).toFixed(1)}%, Loss: ${((rule.params?.lossThreshold || 0) * 100).toFixed(1)}%`}
                            </>
                          ) : (
                            <>
                              {rule.decision === 'BUY' ? 'Buy' : 'Sell'} when {rule.changeType === 'price_increase' ? 'up' : 'down'} {rule.changePercent}%
                            </>
                          )}
                          {' · '}{TIMEFRAME_OPTIONS.find((t) => t.value === rule.timeframe)?.label}
                          {' · '}{rule.quantity} shares
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                          <Label htmlFor={`toggle-${rule.id}`} className="text-xs text-muted-foreground">
                            {rule.enabled ? 'On' : 'Off'}
                          </Label>
                          <Switch
                            id={`toggle-${rule.id}`}
                            checked={rule.enabled}
                            onCheckedChange={() => onToggleRule(rule.id)}
                          />
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onRemoveRule(rule.id)}
                          className="text-destructive hover:text-destructive hover:bg-destructive/10"
                        >
                          Remove
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </TooltipProvider>
  );
}
