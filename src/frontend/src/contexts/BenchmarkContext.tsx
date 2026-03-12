/**
 * Benchmark Context - Manages benchmark execution and results
 */

import React, { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type {
  BenchmarkResult,
  BenchmarkProgress,
  BenchmarkRequest,
} from '@/types/benchmark';
import { usePollBenchmark } from '@/hooks/usePollOperation';

interface BenchmarkContextValue {
  // State
  benchmarks: BenchmarkResult[];
  currentBenchmark: BenchmarkResult | null;
  progress: BenchmarkProgress | null;
  isLoading: boolean;
  error: Error | null;

  // Actions
  startBenchmark: (config: BenchmarkRequest) => Promise<string>;
  getBenchmark: (id: string) => Promise<BenchmarkResult>;
  listBenchmarks: () => Promise<void>;
  stopPolling: () => void;

  // Utilities
  isRunning: boolean;
  hasResults: boolean;
}

const BenchmarkContext = createContext<BenchmarkContextValue | undefined>(undefined);

interface BenchmarkProviderProps {
  children: ReactNode;
}

export function BenchmarkProvider({ children }: BenchmarkProviderProps) {
  const queryClient = useQueryClient();
  const [currentBenchmarkId, setCurrentBenchmarkId] = useState<string | null>(null);
  const [currentBenchmark, setCurrentBenchmark] = useState<BenchmarkResult | null>(null);

  // List all benchmarks
  const {
    data: benchmarks = [],
    isLoading: listLoading,
    error: listError,
    refetch: refetchList,
  } = useQuery({
    queryKey: ['benchmarks', 'list'],
    queryFn: async () => {
      const response = await api.listBenchmarks();
      return response.data;
    },
    refetchInterval: 30000,
  });

  // Poll current benchmark progress
  const [pollState, pollControls] = usePollBenchmark(
    currentBenchmarkId,
    async (id: string) => {
      const response = await api.getBenchmarkProgress(id);
      return response.data;
    },
    {
      interval: 2000,
      maxInterval: 5000,
      autoStart: Boolean(currentBenchmarkId),
    }
  );

  const progress = pollState.data as BenchmarkProgress | null;

  // Fetch benchmark results when polling completes
  React.useEffect(() => {
    if (progress && ['completed', 'failed'].includes(progress.status)) {
      if (currentBenchmarkId) {
        api.getBenchmarkResults(currentBenchmarkId)
          .then(response => {
            setCurrentBenchmark(response.data);
            queryClient.invalidateQueries({ queryKey: ['benchmarks', 'list'] });
          })
          .catch(console.error);
      }
      pollControls.stop();
    }
  }, [progress, currentBenchmarkId, queryClient, pollControls]);

  // Start benchmark mutation
  const startBenchmarkMutation = useMutation({
    mutationFn: async (request: BenchmarkRequest) => {
      const response = await api.startBenchmark(request);
      return response.data;
    },
    onSuccess: (data) => {
      setCurrentBenchmarkId(data.id);
      setCurrentBenchmark(data);
      queryClient.invalidateQueries({ queryKey: ['benchmarks', 'list'] });
    },
    onError: (error) => {
      console.error('Benchmark start failed:', error);
    },
  });

  // Get benchmark results
  const getBenchmarkMutation = useMutation({
    mutationFn: async (id: string) => {
      const response = await api.getBenchmarkResults(id);
      return response.data;
    },
    onSuccess: (data) => {
      setCurrentBenchmark(data);
    },
  });

  // Action functions
  const startBenchmark = useCallback(
    async (config: BenchmarkRequest): Promise<string> => {
      const result = await startBenchmarkMutation.mutateAsync(config);
      return result.id;
    },
    [startBenchmarkMutation]
  );

  const getBenchmark = useCallback(
    async (id: string): Promise<BenchmarkResult> => {
      return await getBenchmarkMutation.mutateAsync(id);
    },
    [getBenchmarkMutation]
  );

  const listBenchmarksAction = useCallback(async () => {
    await refetchList();
  }, [refetchList]);

  const stopPolling = useCallback(() => {
    pollControls.stop();
    setCurrentBenchmarkId(null);
  }, [pollControls]);

  // Computed values
  const isRunning = pollState.isPolling || progress?.status === 'running';
  const hasResults = Boolean(currentBenchmark?.metrics && currentBenchmark.metrics.length > 0);

  const value: BenchmarkContextValue = {
    benchmarks,
    currentBenchmark,
    progress,
    isLoading: listLoading || startBenchmarkMutation.isPending,
    error: (listError || startBenchmarkMutation.error || pollState.error) as Error | null,
    startBenchmark,
    getBenchmark,
    listBenchmarks: listBenchmarksAction,
    stopPolling,
    isRunning,
    hasResults,
  };

  return (
    <BenchmarkContext.Provider value={value}>
      {children}
    </BenchmarkContext.Provider>
  );
}

/**
 * Hook to access benchmark context
 */
export function useBenchmark() {
  const context = useContext(BenchmarkContext);
  if (context === undefined) {
    throw new Error('useBenchmark must be used within BenchmarkProvider');
  }
  return context;
}
