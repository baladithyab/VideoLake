/**
 * Navigation - Reusable navigation component (standalone or embedded)
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Home, Rocket, BarChart3, Search, History, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavigationProps {
  variant?: 'sidebar' | 'header' | 'mobile';
  className?: string;
  onNavigate?: () => void;
}

interface NavItem {
  path: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navigationItems: NavItem[] = [
  { path: '/', label: 'Welcome', icon: Home },
  { path: '/deployment', label: 'Deploy', icon: Rocket },
  { path: '/benchmark', label: 'Benchmark', icon: BarChart3 },
  { path: '/demo', label: 'Search Demo', icon: Search },
  { path: '/history', label: 'History', icon: History },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export function Navigation({ variant = 'sidebar', className, onNavigate }: NavigationProps) {
  const location = useLocation();

  if (variant === 'header') {
    // Horizontal navigation for header
    return (
      <nav className={cn('flex items-center gap-1', className)}>
        {navigationItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;

          return (
            <Link
              key={item.path}
              to={item.path}
              onClick={onNavigate}
              className={cn(
                'flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-indigo-100 text-indigo-700'
                  : 'text-gray-700 hover:bg-gray-100'
              )}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden md:inline">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    );
  }

  if (variant === 'mobile') {
    // Mobile menu (full screen)
    return (
      <nav className={cn('space-y-1', className)}>
        {navigationItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;

          return (
            <Link
              key={item.path}
              to={item.path}
              onClick={onNavigate}
              className={cn(
                'flex items-center gap-3 px-4 py-3 rounded-lg text-base font-medium transition-colors',
                isActive
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-gray-700 hover:bg-gray-100'
              )}
            >
              <Icon className="w-6 h-6" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    );
  }

  // Default: Sidebar navigation (vertical)
  return (
    <nav className={cn('space-y-1', className)}>
      {navigationItems.map((item) => {
        const Icon = item.icon;
        const isActive = location.pathname === item.path;

        return (
          <Link
            key={item.path}
            to={item.path}
            onClick={onNavigate}
            className={cn(
              'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
              isActive
                ? 'bg-indigo-50 text-indigo-700'
                : 'text-gray-700 hover:bg-gray-100'
            )}
          >
            <Icon className="w-5 h-5" />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

/**
 * Breadcrumb navigation
 */
export function Breadcrumb({ items }: { items: Array<{ label: string; path?: string }> }) {
  return (
    <nav className="flex" aria-label="Breadcrumb">
      <ol className="flex items-center space-x-2">
        {items.map((item, index) => (
          <li key={index} className="flex items-center">
            {index > 0 && (
              <span className="mx-2 text-gray-400">/</span>
            )}
            {item.path ? (
              <Link
                to={item.path}
                className="text-sm font-medium text-gray-600 hover:text-gray-900"
              >
                {item.label}
              </Link>
            ) : (
              <span className="text-sm font-medium text-gray-900">
                {item.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
