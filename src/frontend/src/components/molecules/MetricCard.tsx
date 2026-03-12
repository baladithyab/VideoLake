/**
 * MetricCard - Displays a metric with title, value, and optional trend
 */

import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';

export interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  iconColor?: string;
  trend?: {
    value: number;
    label: string;
    direction: 'up' | 'down' | 'neutral';
  };
  onClick?: () => void;
  loading?: boolean;
  className?: string;
}

const trendColors = {
  up: 'text-green-600',
  down: 'text-red-600',
  neutral: 'text-gray-600',
};

const trendBackgrounds = {
  up: 'bg-green-50',
  down: 'bg-red-50',
  neutral: 'bg-gray-50',
};

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  iconColor = 'text-indigo-600',
  trend,
  onClick,
  loading = false,
  className,
}: MetricCardProps) {
  return (
    <Card
      className={cn(
        'relative overflow-hidden transition-all',
        onClick && 'cursor-pointer hover:shadow-md',
        className
      )}
      onClick={onClick}
    >
      <div className="p-6">
        {/* Header with icon */}
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          {Icon && (
            <div className={cn('p-2 rounded-lg bg-gray-50', iconColor)}>
              <Icon className="w-5 h-5" />
            </div>
          )}
        </div>

        {/* Value */}
        {loading ? (
          <div className="h-8 w-24 bg-gray-200 animate-pulse rounded" />
        ) : (
          <div className="mb-2">
            <p className="text-3xl font-bold text-gray-900">{value}</p>
            {subtitle && (
              <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
            )}
          </div>
        )}

        {/* Trend indicator */}
        {trend && !loading && (
          <div
            className={cn(
              'inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium',
              trendBackgrounds[trend.direction],
              trendColors[trend.direction]
            )}
          >
            {trend.direction === 'up' && '↑'}
            {trend.direction === 'down' && '↓'}
            {trend.direction === 'neutral' && '→'}
            <span>{trend.value > 0 ? '+' : ''}{trend.value}%</span>
            <span className="opacity-75">{trend.label}</span>
          </div>
        )}
      </div>

      {/* Accent line at bottom */}
      <div className="h-1 bg-gradient-to-r from-indigo-500 to-purple-500" />
    </Card>
  );
}

/**
 * Compact metric card for dashboards
 */
export function CompactMetricCard({
  label,
  value,
  icon: Icon,
  color = 'indigo',
  className,
}: {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  color?: 'indigo' | 'green' | 'red' | 'yellow' | 'blue';
  className?: string;
}) {
  const colorClasses = {
    indigo: 'text-indigo-600 bg-indigo-50',
    green: 'text-green-600 bg-green-50',
    red: 'text-red-600 bg-red-50',
    yellow: 'text-yellow-600 bg-yellow-50',
    blue: 'text-blue-600 bg-blue-50',
  };

  return (
    <div className={cn('flex items-center gap-3 p-3 rounded-lg bg-white border', className)}>
      {Icon && (
        <div className={cn('p-2 rounded-lg', colorClasses[color])}>
          <Icon className="w-4 h-4" />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-500 truncate">{label}</p>
        <p className="text-lg font-semibold text-gray-900">{value}</p>
      </div>
    </div>
  );
}
