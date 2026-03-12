/**
 * ProgressTracker - Step-by-step progress indicator for wizards and multi-step processes
 */

import React from 'react';
import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ProgressStep {
  id: string;
  title: string;
  description?: string;
  completed: boolean;
  current: boolean;
  optional?: boolean;
}

interface ProgressTrackerProps {
  steps: ProgressStep[];
  orientation?: 'horizontal' | 'vertical';
  onStepClick?: (step: ProgressStep, index: number) => void;
  className?: string;
}

export function ProgressTracker({
  steps,
  orientation = 'horizontal',
  onStepClick,
  className,
}: ProgressTrackerProps) {
  if (orientation === 'vertical') {
    return (
      <nav aria-label="Progress" className={cn('space-y-4', className)}>
        {steps.map((step, index) => (
          <div key={step.id} className="relative">
            {/* Connector line */}
            {index < steps.length - 1 && (
              <div
                className={cn(
                  'absolute left-5 top-12 h-full w-0.5',
                  step.completed ? 'bg-indigo-600' : 'bg-gray-200'
                )}
                aria-hidden="true"
              />
            )}

            {/* Step */}
            <div
              className={cn(
                'group relative flex items-start',
                onStepClick && 'cursor-pointer'
              )}
              onClick={() => onStepClick?.(step, index)}
            >
              {/* Icon */}
              <div className="relative flex items-center justify-center">
                {step.completed ? (
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-600">
                    <Check className="h-5 w-5 text-white" />
                  </div>
                ) : step.current ? (
                  <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-indigo-600 bg-white">
                    <div className="h-3 w-3 rounded-full bg-indigo-600" />
                  </div>
                ) : (
                  <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-gray-300 bg-white">
                    <div className="h-3 w-3 rounded-full bg-gray-300" />
                  </div>
                )}
              </div>

              {/* Content */}
              <div className="ml-4 min-w-0 flex-1">
                <p
                  className={cn(
                    'text-sm font-medium',
                    step.completed || step.current
                      ? 'text-gray-900'
                      : 'text-gray-500'
                  )}
                >
                  {step.title}
                  {step.optional && (
                    <span className="ml-2 text-xs text-gray-400">(Optional)</span>
                  )}
                </p>
                {step.description && (
                  <p className="mt-1 text-sm text-gray-500">{step.description}</p>
                )}
              </div>
            </div>
          </div>
        ))}
      </nav>
    );
  }

  // Horizontal orientation
  return (
    <nav aria-label="Progress" className={className}>
      <ol className="flex items-center">
        {steps.map((step, index) => (
          <li
            key={step.id}
            className={cn(
              'relative',
              index < steps.length - 1 ? 'flex-1' : 'flex-initial'
            )}
          >
            <div
              className={cn(
                'group flex items-center',
                onStepClick && 'cursor-pointer'
              )}
              onClick={() => onStepClick?.(step, index)}
            >
              {/* Step indicator */}
              <div className="relative flex items-center justify-center">
                {step.completed ? (
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-600 transition-colors group-hover:bg-indigo-700">
                    <Check className="h-5 w-5 text-white" />
                  </div>
                ) : step.current ? (
                  <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-indigo-600 bg-white">
                    <div className="h-3 w-3 rounded-full bg-indigo-600 animate-pulse" />
                  </div>
                ) : (
                  <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-gray-300 bg-white group-hover:border-gray-400">
                    <span className="text-sm font-medium text-gray-500">
                      {index + 1}
                    </span>
                  </div>
                )}
              </div>

              {/* Label */}
              <div className="ml-4 hidden sm:block">
                <p
                  className={cn(
                    'text-sm font-medium',
                    step.completed || step.current
                      ? 'text-gray-900'
                      : 'text-gray-500'
                  )}
                >
                  {step.title}
                </p>
              </div>

              {/* Connector line */}
              {index < steps.length - 1 && (
                <div className="ml-4 flex-1 hidden sm:flex items-center">
                  <div
                    className={cn(
                      'h-0.5 w-full transition-colors',
                      step.completed ? 'bg-indigo-600' : 'bg-gray-200'
                    )}
                    aria-hidden="true"
                  />
                </div>
              )}
            </div>
          </li>
        ))}
      </ol>

      {/* Mobile: Show current step details */}
      <div className="mt-4 sm:hidden">
        {steps.find(s => s.current) && (
          <div className="text-center">
            <p className="text-sm font-medium text-gray-900">
              {steps.find(s => s.current)?.title}
            </p>
            {steps.find(s => s.current)?.description && (
              <p className="mt-1 text-sm text-gray-500">
                {steps.find(s => s.current)?.description}
              </p>
            )}
          </div>
        )}
      </div>
    </nav>
  );
}

/**
 * Simple progress bar for percentage-based progress
 */
export function ProgressBar({
  percentage,
  label,
  showPercentage = true,
  size = 'md',
  color = 'indigo',
  className,
}: {
  percentage: number;
  label?: string;
  showPercentage?: boolean;
  size?: 'sm' | 'md' | 'lg';
  color?: 'indigo' | 'green' | 'blue' | 'red';
  className?: string;
}) {
  const heightClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3',
  };

  const colorClasses = {
    indigo: 'bg-indigo-600',
    green: 'bg-green-600',
    blue: 'bg-blue-600',
    red: 'bg-red-600',
  };

  const clampedPercentage = Math.max(0, Math.min(100, percentage));

  return (
    <div className={className}>
      {(label || showPercentage) && (
        <div className="flex items-center justify-between mb-2">
          {label && <span className="text-sm font-medium text-gray-700">{label}</span>}
          {showPercentage && (
            <span className="text-sm font-medium text-gray-600">
              {clampedPercentage.toFixed(0)}%
            </span>
          )}
        </div>
      )}
      <div className={cn('w-full bg-gray-200 rounded-full overflow-hidden', heightClasses[size])}>
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500 ease-out',
            colorClasses[color]
          )}
          style={{ width: `${clampedPercentage}%` }}
          role="progressbar"
          aria-valuenow={clampedPercentage}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  );
}
