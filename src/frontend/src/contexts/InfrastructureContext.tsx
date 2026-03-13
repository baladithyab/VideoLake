/**
 * Infrastructure Context - Manages deployment state and operations
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import type { ReactNode } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type {
  VectorStoreType,
  VectorStoreDeployment,
  InfrastructureStatus,
} from '@/types/infrastructure';
import { usePollDeployment } from '@/hooks/usePollOperation';

interface InfrastructureContextValue {
  // State
  deployments: Record<string, VectorStoreDeployment>;
  isLoading: boolean;
  error: Error | null;
  operationInProgress: boolean;

  // Actions
  deployStore: (store: VectorStoreType) => Promise<void>;
  destroyStore: (store: VectorStoreType) => Promise<void>;
  deployMultiple: (stores: VectorStoreType[]) => Promise<void>;
  refreshStatus: () => Promise<void>;

  // Utilities
  getStoreStatus: (store: VectorStoreType) => InfrastructureStatus;
  isDeployed: (store: VectorStoreType) => boolean;
  getDeployedStores: () => VectorStoreType[];
}

const InfrastructureContext = createContext<InfrastructureContextValue | undefined>(undefined);

interface InfrastructureProviderProps {
  children: ReactNode;
}

export function InfrastructureProvider({ children }: InfrastructureProviderProps) {
  const queryClient = useQueryClient();
  const [operationInProgress, setOperationInProgress] = useState(false);
  const [currentOperationId, setCurrentOperationId] = useState<string | null>(null);

  // Fetch infrastructure status
  const {
    data: statusData,
    isLoading,
    error: queryError,
    refetch: refreshStatus,
  } = useQuery({
    queryKey: ['infrastructure', 'status'],
    queryFn: async () => {
      const response = await api.getInfrastructureStatus();
      return response.data;
    },
    refetchInterval: 30000, // Refetch every 30 seconds
    refetchOnWindowFocus: true,
  });

  // Poll for deployment operations
  const [pollState] = usePollDeployment(
    currentOperationId,
    async (_id: string) => {
      const response = await api.getInfrastructureStatus();
      return response.data;
    },
    {
      interval: 3000,
      maxInterval: 10000,
      autoStart: Boolean(currentOperationId),
    }
  );

  // Clear operation state when polling completes
  useEffect(() => {
    if (currentOperationId && !pollState.isPolling && pollState.data) {
      // Polling has completed, clear operation state
      setOperationInProgress(false);
      setCurrentOperationId(null);
    }
  }, [currentOperationId, pollState.isPolling, pollState.data]);

  // Parse deployments from API response
  const deployments = React.useMemo<Record<string, VectorStoreDeployment>>(() => {
    if (!statusData?.deployed_stores) {
      return {};
    }

    const result: Record<string, VectorStoreDeployment> = {};

    for (const store of statusData.deployed_stores) {
      const storeType = store.name.toLowerCase() as VectorStoreType;
      result[storeType] = {
        type: storeType,
        status: store.deployed ? 'deployed' : 'not_deployed',
        endpoint: store.endpoint || undefined,
        region: store.region || undefined,
        createdAt: store.created_at,
        updatedAt: store.updated_at,
      };
    }

    return result;
  }, [statusData]);

  // Deploy single store mutation
  const deployStoreMutation = useMutation({
    mutationFn: async (store: VectorStoreType) => {
      const response = await api.deploySingleStore(store);
      return response.data;
    },
    onMutate: () => {
      setOperationInProgress(true);
    },
    onSuccess: (data) => {
      if (data.operation_id) {
        setCurrentOperationId(data.operation_id);
      }
      queryClient.invalidateQueries({ queryKey: ['infrastructure', 'status'] });
    },
    onError: (error) => {
      console.error('Deploy failed:', error);
      setOperationInProgress(false);
      setCurrentOperationId(null);
    },
  });

  // Destroy single store mutation
  const destroyStoreMutation = useMutation({
    mutationFn: async (store: VectorStoreType) => {
      const response = await api.destroySingleStore(store, true);
      return response.data;
    },
    onMutate: () => {
      setOperationInProgress(true);
    },
    onSuccess: (data) => {
      if (data.operation_id) {
        setCurrentOperationId(data.operation_id);
      }
      queryClient.invalidateQueries({ queryKey: ['infrastructure', 'status'] });
    },
    onError: (error) => {
      console.error('Destroy failed:', error);
      setOperationInProgress(false);
      setCurrentOperationId(null);
    },
  });

  // Deploy multiple stores
  const deployMultipleMutation = useMutation({
    mutationFn: async (stores: VectorStoreType[]) => {
      const response = await api.deployInfrastructure({
        vector_stores: stores,
        wait_for_completion: false,
      });
      return response.data;
    },
    onMutate: () => {
      setOperationInProgress(true);
    },
    onSuccess: (data) => {
      if (data.operation_id) {
        setCurrentOperationId(data.operation_id);
      }
      queryClient.invalidateQueries({ queryKey: ['infrastructure', 'status'] });
    },
    onError: (error) => {
      console.error('Deploy multiple failed:', error);
      setOperationInProgress(false);
      setCurrentOperationId(null);
    },
  });

  // Action functions
  const deployStore = useCallback(
    async (store: VectorStoreType) => {
      await deployStoreMutation.mutateAsync(store);
    },
    [deployStoreMutation]
  );

  const destroyStore = useCallback(
    async (store: VectorStoreType) => {
      await destroyStoreMutation.mutateAsync(store);
    },
    [destroyStoreMutation]
  );

  const deployMultiple = useCallback(
    async (stores: VectorStoreType[]) => {
      await deployMultipleMutation.mutateAsync(stores);
    },
    [deployMultipleMutation]
  );

  // Utility functions
  const getStoreStatus = useCallback(
    (store: VectorStoreType): InfrastructureStatus => {
      return deployments[store]?.status || 'not_deployed';
    },
    [deployments]
  );

  const isDeployed = useCallback(
    (store: VectorStoreType): boolean => {
      return getStoreStatus(store) === 'deployed';
    },
    [getStoreStatus]
  );

  const getDeployedStores = useCallback((): VectorStoreType[] => {
    return Object.entries(deployments)
      .filter(([, deployment]) => deployment.status === 'deployed')
      .map(([type]) => type as VectorStoreType);
  }, [deployments]);

  const value: InfrastructureContextValue = {
    deployments,
    isLoading,
    error: queryError as Error | null,
    operationInProgress: operationInProgress || pollState.isPolling,
    deployStore,
    destroyStore,
    deployMultiple,
    refreshStatus: async () => {
      await refreshStatus();
    },
    getStoreStatus,
    isDeployed,
    getDeployedStores,
  };

  return (
    <InfrastructureContext.Provider value={value}>
      {children}
    </InfrastructureContext.Provider>
  );
}

/**
 * Hook to access infrastructure context
 */
export function useInfrastructure() {
  const context = useContext(InfrastructureContext);
  if (context === undefined) {
    throw new Error('useInfrastructure must be used within InfrastructureProvider');
  }
  return context;
}
