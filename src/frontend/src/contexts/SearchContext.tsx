/**
 * Search Context - Manages multi-modal search state and history
 */

import React, { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import { useMutation } from '@tanstack/react-query';
import { api } from '@/api/client';
import type {
  SearchQuery,
  SearchResult,
  SearchResponse,
  SearchHistory,
  SearchState,
  SearchRequest,
} from '@/types/search';

interface SearchContextValue extends SearchState {
  // Actions
  executeSearch: (query: SearchQuery, backend: string) => Promise<void>;
  clearResults: () => void;
  selectResult: (result: SearchResult | null) => void;
  setBackend: (backend: string) => void;
  clearHistory: () => void;
  removeHistoryItem: (id: string) => void;

  // Utilities
  getHistoryItem: (id: string) => SearchHistory | undefined;
  canSearch: boolean;
}

const SearchContext = createContext<SearchContextValue | undefined>(undefined);

interface SearchProviderProps {
  children: ReactNode;
}

export function SearchProvider({ children }: SearchProviderProps) {
  const [state, setState] = useState<SearchState>({
    query: null,
    results: [],
    isLoading: false,
    error: null,
    history: [],
    selectedResult: null,
    backend: 's3vector',
  });

  // Search mutation
  const searchMutation = useMutation({
    mutationFn: async ({ query, backend }: { query: SearchQuery; backend: string }) => {
      // Build search request based on modality
      const request: SearchRequest = {
        top_k: 12,
        backend,
      };

      if (query.text) {
        request.query_text = query.text;
      }

      if (query.filters) {
        request.filters = query.filters;
      }

      // For now, we use text search. Image/audio/video search will be added later
      if (query.modality === 'text' && query.text) {
        const response = await api.searchQuery({
          query_text: query.text,
          top_k: request.top_k,
          backend,
          vector_types: ['visual-text', 'visual-image', 'audio'],
        });
        return response.data as SearchResponse;
      }

      // Fallback - return empty results
      return {
        results: [],
        query_time: 0,
        backend,
        total_results: 0,
      };
    },
    onMutate: ({ query }) => {
      setState(prev => ({
        ...prev,
        query,
        isLoading: true,
        error: null,
      }));
    },
    onSuccess: (data, { query, backend }) => {
      // Add to history
      const historyItem: SearchHistory = {
        id: `search-${Date.now()}`,
        query,
        response: data,
        timestamp: new Date().toISOString(),
        backend,
      };

      setState(prev => ({
        ...prev,
        results: data.results || [],
        isLoading: false,
        error: null,
        history: [historyItem, ...prev.history.slice(0, 49)], // Keep last 50 searches
      }));
    },
    onError: (error: Error) => {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error.message || 'Search failed',
        results: [],
      }));
    },
  });

  // Action functions
  const executeSearch = useCallback(
    async (query: SearchQuery, backend: string) => {
      await searchMutation.mutateAsync({ query, backend });
    },
    [searchMutation]
  );

  const clearResults = useCallback(() => {
    setState(prev => ({
      ...prev,
      results: [],
      error: null,
      selectedResult: null,
    }));
  }, []);

  const selectResult = useCallback((result: SearchResult | null) => {
    setState(prev => ({
      ...prev,
      selectedResult: result,
    }));
  }, []);

  const setBackend = useCallback((backend: string) => {
    setState(prev => ({
      ...prev,
      backend,
    }));
  }, []);

  const clearHistory = useCallback(() => {
    setState(prev => ({
      ...prev,
      history: [],
    }));
  }, []);

  const removeHistoryItem = useCallback((id: string) => {
    setState(prev => ({
      ...prev,
      history: prev.history.filter(item => item.id !== id),
    }));
  }, []);

  // Utility functions
  const getHistoryItem = useCallback(
    (id: string): SearchHistory | undefined => {
      return state.history.find(item => item.id === id);
    },
    [state.history]
  );

  const canSearch = Boolean(state.query?.text || state.query?.imageFile);

  const value: SearchContextValue = {
    ...state,
    executeSearch,
    clearResults,
    selectResult,
    setBackend,
    clearHistory,
    removeHistoryItem,
    getHistoryItem,
    canSearch,
  };

  return (
    <SearchContext.Provider value={value}>
      {children}
    </SearchContext.Provider>
  );
}

/**
 * Hook to access search context
 */
export function useSearch() {
  const context = useContext(SearchContext);
  if (context === undefined) {
    throw new Error('useSearch must be used within SearchProvider');
  }
  return context;
}
