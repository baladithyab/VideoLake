/**
 * CostBadge - Displays cost with trend indicator
 */

import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { formatCost } from '@/utils/cost';
import { cn } from '@/lib/utils';

export type CostPeriod = 'hour' | 'day' | 'month' | 'query' | 'operation';
export type CostTrend = 'up' | 'down' | 'stable';

interface CostBadgeProps {
  amount: number;
  period?: CostPeriod;
  trend?: CostTrend;
  tooltip?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const periodLabels: Record<CostPeriod, string> = {
  hour: '/hr',
  day: '/day',
  month: '/mo',
  query: '/query',
  operation: '/op',
};

const trendColors: Record<CostTrend, string> = {
  up: 'text-red-600',
  down: 'text-green-600',
  stable: 'text-gray-500',
};

const trendIcons: Record<CostTrend, React.ComponentType<{ className?: string }>> = {
  up: TrendingUp,
  down: TrendingDown,
  stable: Minus,
};

const sizeClasses = {
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-2.5 py-1',
  lg: 'text-base px-3 py-1.5',
};

export function CostBadge({
  amount,
  period = 'month',
  trend,
  tooltip,
  size = 'md',
  className,
}: CostBadgeProps) {
  const TrendIcon = trend ? trendIcons[trend] : null;
  const formattedAmount = formatCost(amount);

  // Determine badge color based on amount
  const getBadgeColor = () => {
    if (amount === 0) return 'bg-gray-100 text-gray-700 border-gray-200';
    if (amount < 50) return 'bg-blue-50 text-blue-700 border-blue-200';
    if (amount < 200) return 'bg-yellow-50 text-yellow-700 border-yellow-200';
    if (amount < 1000) return 'bg-orange-50 text-orange-700 border-orange-200';
    return 'bg-red-50 text-red-700 border-red-200';
  };

  const badge = (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-md border font-medium',
        sizeClasses[size],
        getBadgeColor(),
        className
      )}
    >
      <span className="font-semibold">{formattedAmount}</span>
      <span className="text-xs opacity-80">{periodLabels[period]}</span>
      {TrendIcon && (
        <TrendIcon
          className={cn('w-3 h-3', trendColors[trend!])}
          aria-label={`Trend ${trend}`}
        />
      )}
    </span>
  );

  if (tooltip) {
    return (
      <span title={tooltip} className="inline-block">
        {badge}
      </span>
    );
  }

  return badge;
}
