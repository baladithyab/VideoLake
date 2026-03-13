/**
 * App - Main application component with routing and context providers
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { UIProvider } from '@/contexts/UIContext';
import { InfrastructureProvider } from '@/contexts/InfrastructureContext';
import { BenchmarkProvider } from '@/contexts/BenchmarkContext';
import { SearchProvider } from '@/contexts/SearchContext';
import { MainLayout } from '@/components/templates/MainLayout';
import { WelcomePage } from '@/components/pages/WelcomePage';
import { NotFoundPage } from '@/components/pages/NotFoundPage';
import { ErrorBoundary } from '@/components/ErrorBoundary';

// Deployment wizard pages (default exports)
import DeploymentConfigurePage from '@/components/pages/DeploymentConfigurePage';
import DeploymentReviewPage from '@/components/pages/DeploymentReviewPage';
import DeploymentProgressPage from '@/components/pages/DeploymentProgressPage';

// Benchmark workflow pages (named exports)
import { BenchmarkHubPage } from '@/components/pages/BenchmarkHubPage';
import { BenchmarkConfigurePage } from '@/components/pages/BenchmarkConfigurePage';
import { BenchmarkRunPage } from '@/components/pages/BenchmarkRunPage';
import { BenchmarkResultsPage } from '@/components/pages/BenchmarkResultsPage';
import { BenchmarkHistoryPage } from '@/components/pages/BenchmarkHistoryPage';

// Demo pages (named exports)
import { DemoSearchPage } from '@/components/pages/DemoSearchPage';
import { VideoDetailPage } from '@/components/pages/VideoDetailPage';

// Infrastructure page (named export)
import { InfrastructurePage } from '@/components/pages/InfrastructurePage';

function SettingsPage() {
  return (
    <div className="text-center py-12">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">Settings</h2>
      <p className="text-gray-600">Coming soon...</p>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <UIProvider>
          <InfrastructureProvider>
            <BenchmarkProvider>
              <SearchProvider>
                <Routes>
                  {/* Routes with MainLayout */}
                  <Route element={<MainLayout />}>
                    <Route path="/" element={<WelcomePage />} />

                  {/* Deployment wizard routes with isolated error boundary */}
                  <Route path="/deployment" element={<Navigate to="/deployment/configure" replace />} />
                  <Route
                    path="/deployment/configure"
                    element={
                      <ErrorBoundary level="page">
                        <DeploymentConfigurePage />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/deployment/review"
                    element={
                      <ErrorBoundary level="page">
                        <DeploymentReviewPage />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/deployment/progress"
                    element={
                      <ErrorBoundary level="page">
                        <DeploymentProgressPage />
                      </ErrorBoundary>
                    }
                  />

                  {/* Benchmark workflow routes with isolated error boundary */}
                  <Route
                    path="/benchmark"
                    element={
                      <ErrorBoundary level="page">
                        <BenchmarkHubPage />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/benchmark/configure"
                    element={
                      <ErrorBoundary level="page">
                        <BenchmarkConfigurePage />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/benchmark/run/:id"
                    element={
                      <ErrorBoundary level="page">
                        <BenchmarkRunPage />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/benchmark/results/:id"
                    element={
                      <ErrorBoundary level="page">
                        <BenchmarkResultsPage />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/benchmark/history"
                    element={
                      <ErrorBoundary level="page">
                        <BenchmarkHistoryPage />
                      </ErrorBoundary>
                    }
                  />

                  {/* Demo routes with isolated error boundary */}
                  <Route path="/demo" element={<Navigate to="/demo/search" replace />} />
                  <Route
                    path="/demo/search"
                    element={
                      <ErrorBoundary level="page">
                        <DemoSearchPage />
                      </ErrorBoundary>
                    }
                  />
                  <Route
                    path="/demo/video/:id"
                    element={
                      <ErrorBoundary level="page">
                        <VideoDetailPage />
                      </ErrorBoundary>
                    }
                  />

                  {/* Infrastructure page with isolated error boundary */}
                  <Route
                    path="/infrastructure"
                    element={
                      <ErrorBoundary level="page">
                        <InfrastructurePage />
                      </ErrorBoundary>
                    }
                  />

                  {/* Settings placeholder with isolated error boundary */}
                  <Route
                    path="/settings"
                    element={
                      <ErrorBoundary level="page">
                        <SettingsPage />
                      </ErrorBoundary>
                    }
                  />
                </Route>

                  {/* 404 page (no layout) */}
                  <Route path="*" element={<NotFoundPage />} />
                </Routes>
              </SearchProvider>
            </BenchmarkProvider>
          </InfrastructureProvider>
        </UIProvider>
      </ErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
