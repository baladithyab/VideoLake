import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/Layout';
import InfrastructureDashboard from './pages/InfrastructureDashboard';
import ResourceManagement from './pages/ResourceManagement';
import MediaProcessing from './pages/MediaProcessing';
import QuerySearch from './pages/QuerySearch';
import ResultsPlayback from './pages/ResultsPlayback';
import EmbeddingVisualization from './pages/EmbeddingVisualization';
import AnalyticsManagement from './pages/AnalyticsManagement';
import './App.css';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<InfrastructureDashboard />} />
              <Route path="/infrastructure" element={<InfrastructureDashboard />} />
              <Route path="/resources" element={<ResourceManagement />} />
              <Route path="/processing" element={<MediaProcessing />} />
              <Route path="/search" element={<QuerySearch />} />
              <Route path="/results" element={<ResultsPlayback />} />
              <Route path="/visualization" element={<EmbeddingVisualization />} />
              <Route path="/analytics" element={<AnalyticsManagement />} />
            </Routes>
          </Layout>
        </Router>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
            },
            success: {
              duration: 3000,
              iconTheme: {
                primary: '#10B981',
                secondary: '#fff',
              },
            },
            error: {
              duration: 5000,
              iconTheme: {
                primary: '#EF4444',
                secondary: '#fff',
              },
            },
          }}
        />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
