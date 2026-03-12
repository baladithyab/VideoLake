/**
 * UI Context - Manages global UI state (sidebar, modals, toasts, theme)
 */

import React, { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import toast from 'react-hot-toast';

export type ThemeMode = 'light' | 'dark' | 'system';
export type ViewMode = 'grid' | 'list' | 'table';

interface Modal {
  id: string;
  component: React.ComponentType<Record<string, unknown>>;
  props?: Record<string, unknown>;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  closeable?: boolean;
}

interface UIState {
  // Sidebar
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;

  // Navigation
  currentPath: string;

  // Modals
  modals: Modal[];

  // View preferences
  viewMode: ViewMode;
  theme: ThemeMode;

  // Loading states
  globalLoading: boolean;
  loadingMessage: string | null;
}

interface UIContextValue extends UIState {
  // Sidebar actions
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebarCollapse: () => void;

  // Navigation
  setCurrentPath: (path: string) => void;

  // Modal actions
  openModal: (component: React.ComponentType<Record<string, unknown>>, props?: Record<string, unknown>, options?: Partial<Modal>) => string;
  closeModal: (id: string) => void;
  closeAllModals: () => void;

  // View preferences
  setViewMode: (mode: ViewMode) => void;
  setTheme: (theme: ThemeMode) => void;

  // Loading
  setGlobalLoading: (loading: boolean, message?: string) => void;

  // Toast notifications
  notify: {
    success: (message: string) => void;
    error: (message: string) => void;
    info: (message: string) => void;
    warning: (message: string) => void;
  };
}

const UIContext = createContext<UIContextValue | undefined>(undefined);

interface UIProviderProps {
  children: ReactNode;
}

export function UIProvider({ children }: UIProviderProps) {
  const [state, setState] = useState<UIState>({
    sidebarOpen: true,
    sidebarCollapsed: false,
    currentPath: '/',
    modals: [],
    viewMode: 'grid',
    theme: 'system',
    globalLoading: false,
    loadingMessage: null,
  });

  // Sidebar actions
  const toggleSidebar = useCallback(() => {
    setState(prev => ({ ...prev, sidebarOpen: !prev.sidebarOpen }));
  }, []);

  const setSidebarOpen = useCallback((open: boolean) => {
    setState(prev => ({ ...prev, sidebarOpen: open }));
  }, []);

  const toggleSidebarCollapse = useCallback(() => {
    setState(prev => ({ ...prev, sidebarCollapsed: !prev.sidebarCollapsed }));
  }, []);

  // Navigation
  const setCurrentPath = useCallback((path: string) => {
    setState(prev => ({ ...prev, currentPath: path }));
  }, []);

  // Modal actions
  const openModal = useCallback(
    (
      component: React.ComponentType<Record<string, unknown>>,
      props?: Record<string, unknown>,
      options?: Partial<Modal>
    ): string => {
      const id = `modal-${Date.now()}`;
      const modal: Modal = {
        id,
        component,
        props,
        size: options?.size || 'md',
        closeable: options?.closeable !== false,
      };

      setState(prev => ({
        ...prev,
        modals: [...prev.modals, modal],
      }));

      return id;
    },
    []
  );

  const closeModal = useCallback((id: string) => {
    setState(prev => ({
      ...prev,
      modals: prev.modals.filter(modal => modal.id !== id),
    }));
  }, []);

  const closeAllModals = useCallback(() => {
    setState(prev => ({
      ...prev,
      modals: [],
    }));
  }, []);

  // View preferences
  const setViewMode = useCallback((mode: ViewMode) => {
    setState(prev => ({ ...prev, viewMode: mode }));
    localStorage.setItem('viewMode', mode);
  }, []);

  const setTheme = useCallback((theme: ThemeMode) => {
    setState(prev => ({ ...prev, theme }));
    localStorage.setItem('theme', theme);

    // Apply theme to document
    if (theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, []);

  // Loading
  const setGlobalLoading = useCallback((loading: boolean, message?: string) => {
    setState(prev => ({
      ...prev,
      globalLoading: loading,
      loadingMessage: message || null,
    }));
  }, []);

  // Toast notifications
  const notify = React.useMemo(
    () => ({
      success: (message: string) => toast.success(message),
      error: (message: string) => toast.error(message),
      info: (message: string) => toast(message, { icon: 'ℹ️' }),
      warning: (message: string) => toast(message, { icon: '⚠️' }),
    }),
    []
  );

  // Initialize theme from localStorage
  React.useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as ThemeMode | null;
    const savedViewMode = localStorage.getItem('viewMode') as ViewMode | null;

    if (savedTheme) {
      setTheme(savedTheme);
    }

    if (savedViewMode) {
      setViewMode(savedViewMode);
    }
  }, [setTheme, setViewMode]);

  const value: UIContextValue = {
    ...state,
    toggleSidebar,
    setSidebarOpen,
    toggleSidebarCollapse,
    setCurrentPath,
    openModal,
    closeModal,
    closeAllModals,
    setViewMode,
    setTheme,
    setGlobalLoading,
    notify,
  };

  return (
    <UIContext.Provider value={value}>
      {children}
    </UIContext.Provider>
  );
}

/**
 * Hook to access UI context
 */
export function useUI() {
  const context = useContext(UIContext);
  if (context === undefined) {
    throw new Error('useUI must be used within UIProvider');
  }
  return context;
}
