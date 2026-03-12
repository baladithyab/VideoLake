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

// Placeholder pages (to be implemented by other agents)
function DeploymentPage() {
  return (
    <div className="text-center py-12">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">Deployment Wizard</h2>
      <p className="text-gray-600">Coming soon...</p>
    </div>
  );
}

function BenchmarkPage() {
  return (
    <div className="text-center py-12">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">Benchmark Dashboard</h2>
      <p className="text-gray-600">Coming soon...</p>
    </div>
  );
}

function DemoPage() {
  return (
    <div className="text-center py-12">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">Search Demo</h2>
      <p className="text-gray-600">Coming soon...</p>
    </div>
  );
}

function HistoryPage() {
  return (
    <div className="text-center py-12">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">History</h2>
      <p className="text-gray-600">Coming soon...</p>
    </div>
  );
}

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
                  <Route path="/deployment" element={<MainLayout><DeploymentPage /></MainLayout>} />
                  <Route path="/benchmark" element={<MainLayout><BenchmarkPage /></MainLayout>} />
                  <Route path="/demo" element={<MainLayout><DemoPage /></MainLayout>} />
                  <Route path="/history" element={<MainLayout><HistoryPage /></MainLayout>} />
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
