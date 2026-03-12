/**
 * App - Main application component with routing and context providers
 */

import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { UIProvider } from '@/contexts/UIContext';
import { InfrastructureProvider } from '@/contexts/InfrastructureContext';
import { BenchmarkProvider } from '@/contexts/BenchmarkContext';
import { SearchProvider } from '@/contexts/SearchContext';
import { MainLayout } from '@/components/templates/MainLayout';
import { WelcomePage } from '@/components/pages/WelcomePage';
import { NotFoundPage } from '@/components/pages/NotFoundPage';

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
      <UIProvider>
        <InfrastructureProvider>
          <BenchmarkProvider>
            <SearchProvider>
              <Routes>
                {/* Routes with MainLayout */}
                <Route element={<MainLayout><div /></MainLayout>}>
                  <Route path="/" element={<MainLayout><WelcomePage /></MainLayout>} />

                  {/* Deployment wizard routes */}
                  <Route path="/deployment/configure" element={<MainLayout><DeploymentConfigurePage /></MainLayout>} />
                  <Route path="/deployment/review" element={<MainLayout><DeploymentReviewPage /></MainLayout>} />
                  <Route path="/deployment/progress" element={<MainLayout><DeploymentProgressPage /></MainLayout>} />

                  {/* Benchmark workflow routes */}
                  <Route path="/benchmark" element={<MainLayout><BenchmarkHubPage /></MainLayout>} />
                  <Route path="/benchmark/configure" element={<MainLayout><BenchmarkConfigurePage /></MainLayout>} />
                  <Route path="/benchmark/run/:id" element={<MainLayout><BenchmarkRunPage /></MainLayout>} />
                  <Route path="/benchmark/results/:id" element={<MainLayout><BenchmarkResultsPage /></MainLayout>} />
                  <Route path="/benchmark/history" element={<MainLayout><BenchmarkHistoryPage /></MainLayout>} />

                  {/* Demo routes */}
                  <Route path="/demo/search" element={<MainLayout><DemoSearchPage /></MainLayout>} />
                  <Route path="/demo/video/:id" element={<MainLayout><VideoDetailPage /></MainLayout>} />

                  {/* Infrastructure page */}
                  <Route path="/infrastructure" element={<MainLayout><InfrastructurePage /></MainLayout>} />

                  {/* Settings placeholder */}
                  <Route path="/settings" element={<MainLayout><SettingsPage /></MainLayout>} />
                </Route>

                {/* 404 page (no layout) */}
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </SearchProvider>
          </BenchmarkProvider>
        </InfrastructureProvider>
      </UIProvider>
    </BrowserRouter>
  );
}

export default App;
