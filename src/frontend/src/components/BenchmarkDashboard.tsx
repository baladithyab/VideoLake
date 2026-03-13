import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { Play, RefreshCw, Download, AlertCircle } from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { api } from '../api/client';
import type { BenchmarkConfig, BenchmarkResult, BenchmarkMetrics, BenchmarkProgress } from '../types/benchmark';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface BackendOption {
  value: string;
  label: string;
  deployed?: boolean;
}

interface BenchmarkDashboardProps {
  availableBackends: BackendOption[];
}

export const BenchmarkDashboard: React.FC<BenchmarkDashboardProps> = ({ availableBackends }) => {
  const [config, setConfig] = useState<BenchmarkConfig>({
    backends: [],
    num_queries: 50,
    query_type: 'text',
    use_existing_embeddings: true,
  });
  
  const [isRunning, setIsRunning] = useState(false);
  const [currentBenchmark, setCurrentBenchmark] = useState<BenchmarkResult | null>(null);
  const [progress, setProgress] = useState<BenchmarkProgress | null>(null);
  const [benchmarkHistory, setBenchmarkHistory] = useState<BenchmarkResult[]>([]);

  // Poll for progress when benchmark is running
  useEffect(() => {
    if (!currentBenchmark || currentBenchmark.status === 'completed' || currentBenchmark.status === 'failed') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const response = await api.getBenchmarkProgress(currentBenchmark.id);
        setProgress(response.data);

        // Refresh full results
        const resultsResponse = await api.getBenchmarkResults(currentBenchmark.id);
        setCurrentBenchmark(resultsResponse.data);

        if (resultsResponse.data.status === 'completed') {
          setIsRunning(false);
          toast.success('Benchmark completed!');
          loadBenchmarkHistory();
        } else if (resultsResponse.data.status === 'failed') {
          setIsRunning(false);
          toast.error(`Benchmark failed: ${resultsResponse.data.error}`);
        }
      } catch (error) {
        console.error('Failed to fetch progress:', error);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [currentBenchmark]);

  // Load benchmark history on mount
  useEffect(() => {
    loadBenchmarkHistory();
  }, []);

  const loadBenchmarkHistory = async () => {
    try {
      const response = await api.listBenchmarks();
      setBenchmarkHistory(response.data);
    } catch (error) {
      console.error('Failed to load benchmark history:', error);
    }
  };

  const handleBackendToggle = (backend: string) => {
    setConfig(prev => ({
      ...prev,
      backends: prev.backends.includes(backend)
        ? prev.backends.filter(b => b !== backend)
        : [...prev.backends, backend]
    }));
  };

  const handleStartBenchmark = async () => {
    if (config.backends.length === 0) {
      toast.error('Please select at least one backend');
      return;
    }

    setIsRunning(true);
    try {
      const response = await api.startBenchmark({
        backends: config.backends,
        config: {
          queries: config.num_queries,
          // query_type: config.query_type, // Not directly supported in backend config yet, maybe map to collection or operation?
          // use_existing_embeddings: config.use_existing_embeddings, // Not directly supported
          operation: 'search', // Default to search for now
          use_ecs: true // Default to ECS for now as per requirement
        }
      });

      setCurrentBenchmark(response.data);
      toast.success('Benchmark started!');
    } catch (error: any) {
      setIsRunning(false);
      const errorMessage = error.response?.data?.detail || 'Failed to start benchmark';
      toast.error(errorMessage);
    }
  };

  const exportResults = () => {
    if (!currentBenchmark) return;
    
    const dataStr = JSON.stringify(currentBenchmark, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
    const exportFileDefaultName = `benchmark-${currentBenchmark.id}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  // Prepare chart data
  const latencyChartData = currentBenchmark?.metrics.map(m => ({
    backend: m.backend,
    'Avg Latency (ms)': m.avg_latency,
    'P95 Latency (ms)': m.p95_latency,
    'P99 Latency (ms)': m.p99_latency,
  })) || [];

  const throughputChartData = currentBenchmark?.metrics.map(m => ({
    backend: m.backend,
    'Throughput (q/s)': m.throughput,
    'Success Rate (%)': m.success_rate * 100,
  })) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Performance Benchmarking</h2>
        <p className="text-gray-600">
          Compare search performance across different vector store backends
        </p>
      </div>

      {/* Configuration Panel */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Benchmark Configuration</h3>
        
        <div className="space-y-6">
          {/* Backend Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Backends to Benchmark
            </label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {availableBackends.map(backend => (
                <label
                  key={backend.value}
                  className={`relative flex items-center p-4 border rounded-lg cursor-pointer transition-colors ${
                    config.backends.includes(backend.value)
                      ? 'border-indigo-600 bg-indigo-50'
                      : 'border-gray-300 hover:border-gray-400'
                  } ${!backend.deployed ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <input
                    type="checkbox"
                    checked={config.backends.includes(backend.value)}
                    onChange={() => handleBackendToggle(backend.value)}
                    disabled={!backend.deployed || isRunning}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                  />
                  <span className="ml-3 text-sm font-medium text-gray-900">
                    {backend.label}
                  </span>
                  {!backend.deployed && (
                    <span className="absolute top-1 right-1 text-xs text-red-600">Not Deployed</span>
                  )}
                </label>
              ))}
            </div>
          </div>

          {/* Number of Queries */}
          <div>
            <Label htmlFor="num-queries" className="block text-sm font-medium text-gray-700 mb-2">
              Number of Queries
            </Label>
            <Input
              id="num-queries"
              type="number"
              min="1"
              max="1000"
              value={config.num_queries}
              onChange={(e) => setConfig({ ...config, num_queries: parseInt(e.target.value) })}
              disabled={isRunning}
              className="block w-full md:w-48"
            />
          </div>

          {/* Query Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Query Type
            </label>
            <div className="flex space-x-4">
              {(['text', 'image', 'video'] as const).map(type => (
                <label key={type} className="flex items-center">
                  <input
                    type="radio"
                    name="query-type"
                    value={type}
                    checked={config.query_type === type}
                    onChange={(e) => setConfig({ ...config, query_type: e.target.value as any })}
                    disabled={isRunning}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
                  />
                  <span className="ml-2 text-sm text-gray-900 capitalize">{type}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Use Existing Embeddings */}
          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={config.use_existing_embeddings}
                onChange={(e) => setConfig({ ...config, use_existing_embeddings: e.target.checked })}
                disabled={isRunning}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-900">
                Use existing embeddings (faster, recommended for quick comparisons)
              </span>
            </label>
          </div>

          {/* Start Button */}
          <div className="flex items-center space-x-4">
            <button
              onClick={handleStartBenchmark}
              disabled={isRunning || config.backends.length === 0}
              className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isRunning ? (
                <>
                  <RefreshCw className="animate-spin -ml-1 mr-2 h-5 w-5" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="-ml-1 mr-2 h-5 w-5" />
                  Start Benchmark
                </>
              )}
            </button>
            
            {currentBenchmark && (
              <button
                onClick={exportResults}
                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                <Download className="-ml-1 mr-2 h-4 w-4" />
                Export Results
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Progress Indicator */}
      {progress && isRunning && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center">
              <RefreshCw className="animate-spin h-5 w-5 text-blue-600 mr-2" />
              <span className="text-sm font-medium text-blue-900">
                {progress.message || 'Running benchmark...'}
              </span>
            </div>
            <span className="text-sm font-medium text-blue-900">
              {progress.progress_percentage.toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-blue-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress.progress_percentage}%` }}
            />
          </div>
          <div className="mt-2 text-xs text-blue-800">
            {progress.current_backend && `Testing ${progress.current_backend}`}
            {' • '}
            {progress.completed_queries} / {progress.total_queries} queries
          </div>
        </div>
      )}

      {/* Results Display */}
      {currentBenchmark?.metrics && currentBenchmark.metrics.length > 0 && (
        <div className="space-y-6">
          {/* Results Table */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Benchmark Results</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Backend
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Avg Latency (ms)
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      P95 (ms)
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      P99 (ms)
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Throughput (q/s)
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Success Rate
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {currentBenchmark.metrics.map((metric) => (
                    <tr key={metric.backend} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {metric.backend}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {metric.avg_latency.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {metric.p95_latency.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {metric.p99_latency.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {metric.throughput.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          metric.success_rate >= 0.95 
                            ? 'bg-green-100 text-green-800'
                            : metric.success_rate >= 0.80
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {(metric.success_rate * 100).toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Latency Chart */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Latency Comparison</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={latencyChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="backend" />
                <YAxis label={{ value: 'Latency (ms)', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="Avg Latency (ms)" fill="#8884d8" />
                <Bar dataKey="P95 Latency (ms)" fill="#82ca9d" />
                <Bar dataKey="P99 Latency (ms)" fill="#ffc658" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Throughput Chart */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Throughput & Success Rate</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={throughputChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="backend" />
                <YAxis 
                  yAxisId="left"
                  label={{ value: 'Throughput (q/s)', angle: -90, position: 'insideLeft' }} 
                />
                <YAxis 
                  yAxisId="right"
                  orientation="right"
                  label={{ value: 'Success Rate (%)', angle: 90, position: 'insideRight' }}
                  domain={[0, 100]}
                />
                <Tooltip />
                <Legend />
                <Line 
                  yAxisId="left"
                  type="monotone" 
                  dataKey="Throughput (q/s)" 
                  stroke="#8884d8" 
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
                <Line 
                  yAxisId="right"
                  type="monotone" 
                  dataKey="Success Rate (%)" 
                  stroke="#82ca9d" 
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* No Results Placeholder */}
      {!currentBenchmark && !isRunning && (
        <div className="bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No benchmark results</h3>
          <p className="mt-1 text-sm text-gray-500">
            Configure and start a benchmark to see performance comparisons
          </p>
        </div>
      )}

      {/* API Note */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex">
          <AlertCircle className="h-5 w-5 text-yellow-400" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-800">Backend API Required</h3>
            <div className="mt-2 text-sm text-yellow-700">
              <p>
                This dashboard requires backend benchmark API endpoints:
              </p>
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li><code className="text-xs bg-yellow-100 px-1 py-0.5 rounded">POST /api/benchmark/start</code> - Start a new benchmark</li>
                <li><code className="text-xs bg-yellow-100 px-1 py-0.5 rounded">GET /api/benchmark/results/:id</code> - Get benchmark results</li>
                <li><code className="text-xs bg-yellow-100 px-1 py-0.5 rounded">GET /api/benchmark/progress/:id</code> - Get benchmark progress</li>
                <li><code className="text-xs bg-yellow-100 px-1 py-0.5 rounded">GET /api/benchmark/list</code> - List all benchmarks</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};