/**
 * Hook for polling long-running operations with exponential backoff
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export interface PollConfig {
  /** Initial polling interval in milliseconds */
  interval?: number;
  /** Maximum polling interval (for exponential backoff) */
  maxInterval?: number;
  /** Maximum number of poll attempts (0 = infinite) */
  maxAttempts?: number;
  /** Enable exponential backoff */
  exponentialBackoff?: boolean;
  /** Backoff multiplier */
  backoffMultiplier?: number;
  /** Auto-start polling on mount */
  autoStart?: boolean;
}

export interface PollState<T> {
  data: T | null;
  isPolling: boolean;
  error: Error | null;
  attemptCount: number;
}

export interface PollControls {
  start: () => void;
  stop: () => void;
  reset: () => void;
}

const DEFAULT_CONFIG: Required<PollConfig> = {
  interval: 2000,
  maxInterval: 30000,
  maxAttempts: 0,
  exponentialBackoff: true,
  backoffMultiplier: 1.5,
  autoStart: true,
};

/**
 * Custom hook for polling operations with automatic retry and backoff
 *
 * @param fetchFn - Async function to fetch data
 * @param shouldContinue - Function to determine if polling should continue based on data
 * @param config - Polling configuration
 * @returns [state, controls]
 */
export function usePollOperation<T>(
  fetchFn: () => Promise<T>,
  shouldContinue: (data: T) => boolean,
  config: PollConfig = {}
): [PollState<T>, PollControls] {
  const cfg = { ...DEFAULT_CONFIG, ...config };

  const [state, setState] = useState<PollState<T>>({
    data: null,
    isPolling: false,
    error: null,
    attemptCount: 0,
  });

  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const currentIntervalRef = useRef(cfg.interval);
  const isActiveRef = useRef(false);

  const clearCurrentTimeout = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const poll = useCallback(async () => {
    if (!isActiveRef.current) return;

    try {
      setState(prev => ({ ...prev, attemptCount: prev.attemptCount + 1 }));

      const data = await fetchFn();

      setState(prev => ({
        ...prev,
        data,
        error: null,
      }));

      // Check if we should continue polling
      if (!shouldContinue(data)) {
        isActiveRef.current = false;
        setState(prev => ({ ...prev, isPolling: false }));
        return;
      }

      // Check max attempts
      if (cfg.maxAttempts > 0 && state.attemptCount >= cfg.maxAttempts) {
        isActiveRef.current = false;
        setState(prev => ({
          ...prev,
          isPolling: false,
          error: new Error('Maximum poll attempts reached'),
        }));
        return;
      }

      // Schedule next poll with backoff
      if (cfg.exponentialBackoff) {
        currentIntervalRef.current = Math.min(
          currentIntervalRef.current * cfg.backoffMultiplier,
          cfg.maxInterval
        );
      }

      timeoutRef.current = setTimeout(poll, currentIntervalRef.current);

    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error : new Error('Unknown error'),
        isPolling: false,
      }));
      isActiveRef.current = false;
    }
  }, [fetchFn, shouldContinue, cfg, state.attemptCount]);

  const start = useCallback(() => {
    if (isActiveRef.current) return;

    isActiveRef.current = true;
    currentIntervalRef.current = cfg.interval;
    setState(prev => ({
      ...prev,
      isPolling: true,
      error: null,
      attemptCount: 0,
    }));

    poll();
  }, [poll, cfg.interval]);

  const stop = useCallback(() => {
    isActiveRef.current = false;
    clearCurrentTimeout();
    setState(prev => ({ ...prev, isPolling: false }));
  }, [clearCurrentTimeout]);

  const reset = useCallback(() => {
    stop();
    setState({
      data: null,
      isPolling: false,
      error: null,
      attemptCount: 0,
    });
    currentIntervalRef.current = cfg.interval;
  }, [stop, cfg.interval]);

  // Auto-start on mount if configured
  useEffect(() => {
    if (cfg.autoStart) {
      start();
    }

    return () => {
      clearCurrentTimeout();
      isActiveRef.current = false;
    };
  }, [cfg.autoStart, start, clearCurrentTimeout]);

  return [state, { start, stop, reset }];
}

/**
 * Specialized hook for polling infrastructure deployment status
 */
export function usePollDeployment(
  operationId: string | null,
  fetchStatus: (id: string) => Promise<{ status: string; [key: string]: unknown }>,
  config?: PollConfig
) {
  const fetchFn = useCallback(async () => {
    if (!operationId) throw new Error('No operation ID');
    return fetchStatus(operationId);
  }, [operationId, fetchStatus]);

  const shouldContinue = useCallback((data: { status: string }) => {
    const inProgressStates = ['pending', 'running', 'deploying', 'destroying', 'applying'];
    return inProgressStates.includes(data.status.toLowerCase());
  }, []);

  return usePollOperation(fetchFn, shouldContinue, {
    ...config,
    autoStart: Boolean(operationId),
  });
}

/**
 * Specialized hook for polling benchmark execution
 */
export function usePollBenchmark(
  benchmarkId: string | null,
  fetchProgress: (id: string) => Promise<{ status: string; progress_percentage?: number; [key: string]: unknown }>,
  config?: PollConfig
) {
  const fetchFn = useCallback(async () => {
    if (!benchmarkId) throw new Error('No benchmark ID');
    return fetchProgress(benchmarkId);
  }, [benchmarkId, fetchProgress]);

  const shouldContinue = useCallback((data: { status: string }) => {
    return ['pending', 'running'].includes(data.status.toLowerCase());
  }, []);

  return usePollOperation(fetchFn, shouldContinue, {
    ...config,
    autoStart: Boolean(benchmarkId),
  });
}
