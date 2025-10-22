import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
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
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/resources" replace />} />
            <Route path="/resources" element={<ResourceManagement />} />
            <Route path="/processing" element={<MediaProcessing />} />
            <Route path="/search" element={<QuerySearch />} />
            <Route path="/results" element={<ResultsPlayback />} />
            <Route path="/visualization" element={<EmbeddingVisualization />} />
            <Route path="/analytics" element={<AnalyticsManagement />} />
          </Routes>
        </Layout>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
