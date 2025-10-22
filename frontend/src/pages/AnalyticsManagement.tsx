import { useQuery } from '@tanstack/react-query';
import { analyticsAPI } from '../api/client';

export default function AnalyticsManagement() {
  const { data: performance } = useQuery({
    queryKey: ['performance'],
    queryFn: async () => {
      const response = await analyticsAPI.getPerformance();
      return response.data;
    },
  });

  const { data: systemStatus } = useQuery({
    queryKey: ['system-status'],
    queryFn: async () => {
      const response = await analyticsAPI.getSystemStatus();
      return response.data;
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Analytics & Management</h1>
        <p className="mt-2 text-sm text-gray-600">
          Performance monitoring, cost tracking, and system management
        </p>
      </div>

      {/* Performance Metrics */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Performance Metrics</h3>
        {performance?.metrics && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">Avg Query Latency</p>
              <p className="text-2xl font-semibold text-gray-900">
                {performance.metrics.avg_query_latency_ms}ms
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Queries</p>
              <p className="text-2xl font-semibold text-gray-900">
                {performance.metrics.total_queries}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Videos Processed</p>
              <p className="text-2xl font-semibold text-gray-900">
                {performance.metrics.total_videos_processed}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Cache Hit Rate</p>
              <p className="text-2xl font-semibold text-gray-900">
                {(performance.metrics.cache_hit_rate * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        )}
      </div>

      {/* System Status */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">System Status</h3>
        {systemStatus?.status && (
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Overall Status</span>
              <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                systemStatus.status.overall === 'healthy' 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-red-100 text-red-800'
              }`}>
                {systemStatus.status.overall}
              </span>
            </div>
            {Object.entries(systemStatus.status.services).map(([service, status]: [string, any]) => (
              <div key={service} className="flex justify-between items-center">
                <span className="text-sm text-gray-600">{service}</span>
                <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                  status === 'healthy' 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  {status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

