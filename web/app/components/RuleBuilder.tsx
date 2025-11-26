'use client';

import { useState, useEffect } from 'react';
import {
  TradingRule,
  TimeframeOption,
  ChangeType,
  Decision,
  RuleType,
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

interface RuleBuilderProps {
  onAddRule: (rule: TradingRule) => void;
  existingRules: TradingRule[];
  onRemoveRule: (id: string) => void;
  onToggleRule: (id: string) => void;
}

// Simplified rule types with clear descriptions
const SIMPLIFIED_RULE_TYPES = [
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
  {
    value: 'custom',
    label: 'Custom Rule',
    description: 'Full control over all parameters',
    decision: null,
    changeType: null,
    thresholdLabel: 'Threshold',
  },
];

type SimpleRuleType = 'buy_the_dip' | 'buy_momentum' | 'take_profit' | 'stop_loss' | 'custom';

export default function RuleBuilder({
  onAddRule,
  existingRules,
  onRemoveRule,
  onToggleRule,
}: RuleBuilderProps) {
  const [simpleRuleType, setSimpleRuleType] = useState<SimpleRuleType>('buy_the_dip');
  const [timeframe, setTimeframe] = useState<TimeframeOption>('1D');
  const [changeType, setChangeType] = useState<ChangeType>('price_decrease');
  const [changePercent, setChangePercent] = useState(3);
  const [decision, setDecision] = useState<Decision>('BUY');
  const [quantity, setQuantity] = useState(100);
  const [ruleName, setRuleName] = useState('');

  // Get current rule type config
  const currentRuleConfig = SIMPLIFIED_RULE_TYPES.find(r => r.value === simpleRuleType)!;
  const isCustom = simpleRuleType === 'custom';

  // Update decision and changeType when rule type changes
  useEffect(() => {
    if (!isCustom) {
      if (currentRuleConfig.decision) setDecision(currentRuleConfig.decision);
      if (currentRuleConfig.changeType) setChangeType(currentRuleConfig.changeType);
    }
  }, [simpleRuleType, isCustom, currentRuleConfig]);

  const handleAddRule = () => {
    const effectiveDecision = isCustom ? decision : currentRuleConfig.decision!;
    const effectiveChangeType = isCustom ? changeType : currentRuleConfig.changeType!;

    const newRule: TradingRule = {
      id: `rule-${Date.now()}`,
      name: ruleName || currentRuleConfig.label,
      ruleType: 'custom',
      timeframe,
      changeType: effectiveChangeType,
      changePercent,
      decision: effectiveDecision,
      quantity,
      enabled: true,
    };
    onAddRule(newRule);
    setRuleName('');
  };

  const addPresetStrategy = (preset: 'mean_reversion' | 'momentum' | 'conservative') => {
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
          <CardContent className="flex flex-wrap gap-2">
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
          </CardContent>
        </Card>

        {/* Rule Builder */}
        <Card>
          <CardHeader>
            <CardTitle>Create Rule</CardTitle>
            <CardDescription>{currentRuleConfig.description}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Rule Type Selection - Visual Cards */}
            <div className="space-y-2">
              <Label>What do you want to do?</Label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {SIMPLIFIED_RULE_TYPES.filter(r => r.value !== 'custom').map((ruleType) => (
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
                <Button
                  variant={simpleRuleType === 'custom' ? 'default' : 'outline'}
                  className="h-auto py-3 flex flex-col items-start text-left"
                  onClick={() => setSimpleRuleType('custom')}
                >
                  <span className="font-medium">Custom</span>
                  <span className="text-xs text-muted-foreground font-normal">Full control</span>
                </Button>
              </div>
            </div>

            <Separator />

            {/* Threshold Input - Clear Label */}
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="flex-1 space-y-2">
                  <Label htmlFor="changePercent">
                    {currentRuleConfig.thresholdLabel}
                  </Label>
                  <div className="flex items-center gap-2">
                    <NumberInput
                      id="changePercent"
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
              </div>

              {/* Quick Percent Buttons */}
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

            {/* Custom Rule Options - Only show for custom */}
            {isCustom && (
              <>
                <Separator />
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Action</Label>
                    <Select value={decision} onValueChange={(v) => setDecision(v as Decision)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="BUY">BUY (Entry)</SelectItem>
                        <SelectItem value="SELL">SELL (Exit)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Trigger Condition</Label>
                    <Select value={changeType} onValueChange={(v) => setChangeType(v as ChangeType)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {CHANGE_TYPE_OPTIONS.map((opt) => (
                          <SelectItem key={opt.value} value={opt.value}>
                            {opt.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </>
            )}

            <Separator />

            {/* Common Options */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="ruleName">Rule Name (optional)</Label>
                <Input
                  id="ruleName"
                  value={ruleName}
                  onChange={(e) => setRuleName(e.target.value)}
                  placeholder={currentRuleConfig.label}
                />
              </div>

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
                <Label htmlFor="quantity">Shares per Trade</Label>
                <NumberInput
                  id="quantity"
                  value={quantity}
                  onChange={setQuantity}
                  min={1}
                  max={10000}
                  step={10}
                />
              </div>
            </div>

            <Button onClick={handleAddRule} className="w-full" size="lg">
              <Badge variant={isCustom ? (decision === 'BUY' ? 'default' : 'destructive') : (currentRuleConfig.decision === 'BUY' ? 'default' : 'destructive')} className="mr-2">
                {isCustom ? decision : currentRuleConfig.decision}
              </Badge>
              Add {ruleName || currentRuleConfig.label} Rule
            </Button>
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
              {/* Warning if missing BUY or SELL rules */}
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
                          <span className="font-medium">{rule.name}</span>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          {rule.decision === 'BUY' ? 'Buy' : 'Sell'} when {rule.changeType === 'price_increase' ? 'up' : 'down'} {rule.changePercent}%
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
