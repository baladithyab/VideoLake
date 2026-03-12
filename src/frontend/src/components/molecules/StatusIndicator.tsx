/**
 * StatusIndicator - Visual status indicator with pulse animation and labels
 */

import React from 'react';
import { CheckCircle2, XCircle, AlertCircle, Clock, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatStatus } from '@/utils/format';

export type StatusType =
  | 'success'
  | 'error'
  | 'warning'
  | 'info'
  | 'pending'
  | 'running'
  | 'deployed'
  | 'not_deployed'
  | 'deploying'
  | 'destroying'
  | 'failed';

interface StatusConfig {
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor: string;
  borderColor: string;
  pulse: boolean;
}

const statusConfigs: Record<StatusType, StatusConfig> = {
  success: {
    icon: CheckCircle2,
    color: 'text-green-700',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    pulse: false,
  },
  deployed: {
    icon: CheckCircle2,
    color: 'text-green-700',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    pulse: false,
  },
  error: {
    icon: XCircle,
    color: 'text-red-700',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    pulse: false,
  },
  failed: {
    icon: XCircle,
    color: 'text-red-700',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    pulse: false,
  },
  warning: {
    icon: AlertCircle,
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    pulse: false,
  },
  info: {
    icon: AlertCircle,
    color: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    pulse: false,
  },
  pending: {
    icon: Clock,
    color: 'text-gray-700',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
    pulse: true,
  },
  running: {
    icon: Loader2,
    color: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    pulse: true,
  },
  deploying: {
    icon: Loader2,
    color: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    pulse: true,
  },
  destroying: {
    icon: Loader2,
    color: 'text-orange-700',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    pulse: true,
  },
  not_deployed: {
    icon: AlertCircle,
    color: 'text-gray-500',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
    pulse: false,
  },
};

interface StatusIndicatorProps {
  status: StatusType | string;
  label?: string;
  showIcon?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeClasses = {
  sm: {
    container: 'px-2 py-1 text-xs',
    icon: 'w-3 h-3',
    dot: 'w-2 h-2',
  },
  md: {
    container: 'px-3 py-1.5 text-sm',
    icon: 'w-4 h-4',
    dot: 'w-2.5 h-2.5',
  },
  lg: {
    container: 'px-4 py-2 text-base',
    icon: 'w-5 h-5',
    dot: 'w-3 h-3',
  },
};

export function StatusIndicator({
  status,
  label,
  showIcon = true,
  size = 'md',
  className,
}: StatusIndicatorProps) {
  const statusKey = status as StatusType;
  const config = statusConfigs[statusKey] || statusConfigs.info;
  const Icon = config.icon;
  const displayLabel = label || formatStatus(status);

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md border font-medium',
        sizeClasses[size].container,
        config.color,
        config.bgColor,
        config.borderColor,
        className
      )}
    >
      {showIcon && (
        <Icon
          className={cn(
            sizeClasses[size].icon,
            config.pulse && 'animate-spin'
          )}
        />
      )}
      <span>{displayLabel}</span>
      {config.pulse && (
        <span className="relative flex">
          <span
            className={cn(
              'absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping',
              config.bgColor
            )}
          />
          <span
            className={cn(
              'relative inline-flex rounded-full',
              sizeClasses[size].dot,
              config.color === 'text-blue-700' ? 'bg-blue-500' : 'bg-current'
            )}
          />
        </span>
      )}
    </span>
  );
}

/**
 * Simple dot indicator without label
 */
export function StatusDot({
  status,
  size = 'md',
  className,
  tooltip,
}: {
  status: StatusType | string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  tooltip?: string;
}) {
  const statusKey = status as StatusType;
  const config = statusConfigs[statusKey] || statusConfigs.info;

  const dotSizes = {
    sm: 'w-2 h-2',
    md: 'w-3 h-3',
    lg: 'w-4 h-4',
  };

  return (
    <span
      className={cn('relative inline-flex', className)}
      title={tooltip || formatStatus(status)}
    >
      {config.pulse && (
        <span
          className={cn(
            'absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping',
            config.bgColor
          )}
        />
      )}
      <span
        className={cn(
          'relative inline-flex rounded-full',
          dotSizes[size],
          config.color === 'text-green-700' ? 'bg-green-500' :
          config.color === 'text-red-700' ? 'bg-red-500' :
          config.color === 'text-blue-700' ? 'bg-blue-500' :
          config.color === 'text-yellow-700' ? 'bg-yellow-500' :
          config.color === 'text-orange-700' ? 'bg-orange-500' :
          'bg-gray-500'
        )}
      />
    </span>
  );
}
