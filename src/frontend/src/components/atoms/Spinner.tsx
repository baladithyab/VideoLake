/**
 * Spinner - Animated loading spinner
 */

import React from 'react';
import { cn } from '@/lib/utils';

export type SpinnerSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

interface SpinnerProps {
  size?: SpinnerSize;
  className?: string;
  label?: string;
}

const sizeClasses: Record<SpinnerSize, string> = {
  xs: 'w-3 h-3',
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
  xl: 'w-12 h-12',
};

const borderSizes: Record<SpinnerSize, string> = {
  xs: 'border',
  sm: 'border-2',
  md: 'border-2',
  lg: 'border-3',
  xl: 'border-4',
};

export function Spinner({ size = 'md', className, label }: SpinnerProps) {
  return (
    <div className={cn('inline-flex items-center gap-2', className)} role="status">
      <div
        className={cn(
          'animate-spin rounded-full border-gray-300 border-t-indigo-600',
          sizeClasses[size],
          borderSizes[size]
        )}
        aria-hidden="true"
      />
      {label && (
        <span className="text-sm text-gray-600">{label}</span>
      )}
      <span className="sr-only">Loading...</span>
    </div>
  );
}

/**
 * Full-page loading spinner overlay
 */
export function SpinnerOverlay({ message }: { message?: string }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-4 rounded-lg bg-white p-8 shadow-xl">
        <Spinner size="xl" />
        {message && (
          <p className="text-lg font-medium text-gray-900">{message}</p>
        )}
      </div>
    </div>
  );
}

/**
 * Inline loading state for buttons
 */
export function ButtonSpinner({ className }: { className?: string }) {
  return <Spinner size="sm" className={cn('mr-2', className)} />;
}
