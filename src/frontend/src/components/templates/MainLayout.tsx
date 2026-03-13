/**
 * MainLayout - Main application layout with header, sidebar, and content area
 */

import React from 'react';
import { Link, useLocation, Outlet } from 'react-router-dom';
import {
  Home,
  Rocket,
  BarChart3,
  Search,
  History,
  Settings,
  Menu,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useUI } from '@/contexts/UIContext';
import { useInfrastructure } from '@/contexts/InfrastructureContext';
import { StatusDot } from '@/components/molecules/StatusIndicator';

interface NavItem {
  path: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

const navigationItems: NavItem[] = [
  { path: '/', label: 'Welcome', icon: Home },
  { path: '/deployment', label: 'Deploy', icon: Rocket },
  { path: '/benchmark', label: 'Benchmark', icon: BarChart3 },
  { path: '/demo', label: 'Search Demo', icon: Search },
  { path: '/benchmark/history', label: 'History', icon: History },
];

export function MainLayout() {
  const location = useLocation();
  const { sidebarOpen, setSidebarOpen } = useUI();
  const { deployments, isDeployed } = useInfrastructure();

  // Count deployed stores for status indicator
  const deployedCount = Object.values(deployments).filter(
    d => d.status === 'deployed'
  ).length;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-gray-900/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-200 transform transition-transform duration-200 ease-in-out lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <Link to="/" className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">S3</span>
              </div>
              <span className="text-xl font-bold text-gray-900">S3Vector</span>
            </Link>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-2 text-gray-500 hover:text-gray-700"
              aria-label="Close sidebar"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
            {navigationItems.map((item) => {
              const Icon = item.icon;
              // Match exact path for home, or check if current path starts with nav path (for multi-page sections)
              const isActive = item.path === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.path);

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-gray-700 hover:bg-gray-100'
                  )}
                  onClick={() => {
                    // Close sidebar on mobile after navigation
                    if (window.innerWidth < 1024) {
                      setSidebarOpen(false);
                    }
                  }}
                >
                  <Icon className="w-5 h-5" />
                  <span className="flex-1">{item.label}</span>
                  {item.badge && (
                    <span className="px-2 py-0.5 text-xs font-semibold bg-indigo-100 text-indigo-700 rounded-full">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Infrastructure status */}
          <div className="px-4 py-4 border-t border-gray-200" aria-live="polite" aria-atomic="true">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Infrastructure
              </span>
              <StatusDot
                status={deployedCount > 0 ? 'deployed' : 'not_deployed'}
                size="sm"
              />
            </div>
            <div className="space-y-2">
              {(['s3vector', 'lancedb', 'qdrant', 'opensearch'] as const).map((store) => (
                <div key={store} className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 capitalize">
                    {store === 's3vector' ? 'S3 Vector' : store}
                  </span>
                  <StatusDot
                    status={isDeployed(store) ? 'success' : 'not_deployed'}
                    size="sm"
                    tooltip={isDeployed(store) ? 'Deployed' : 'Not deployed'}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Settings link */}
          <div className="px-4 py-4 border-t border-gray-200">
            <Link
              to="/settings"
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
            >
              <Settings className="w-5 h-5" />
              <span>Settings</span>
            </Link>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Header */}
        <header className="sticky top-0 z-30 bg-white border-b border-gray-200">
          <div className="flex items-center justify-between px-4 py-3 sm:px-6">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 text-gray-500 hover:text-gray-700 lg:hidden"
              aria-label="Open sidebar"
            >
              <Menu className="w-6 h-6" />
            </button>

            <div className="flex-1 lg:block hidden">
              <h1 className="text-xl font-semibold text-gray-900">
                {navigationItems.find(item => item.path === location.pathname)?.label || 'S3Vector'}
              </h1>
            </div>

            <div className="flex items-center gap-4">
              {/* Status badge */}
              {deployedCount > 0 && (
                <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-green-50 border border-green-200 rounded-lg" aria-live="polite">
                  <StatusDot status="success" size="sm" />
                  <span className="text-sm font-medium text-green-700">
                    {deployedCount} {deployedCount === 1 ? 'Store' : 'Stores'} Active
                  </span>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
