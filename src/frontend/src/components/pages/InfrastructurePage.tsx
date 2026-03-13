import React, { useEffect, useState } from 'react';
import {
  Server,
  RefreshCw,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Clock,
  DollarSign,
  Activity,
  Settings,
  Play,
  Trash2,
  Zap
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { useInfrastructure } from '../../contexts/InfrastructureContext';
import TerraformLogViewer from '../TerraformLogsViewer';
import { toast } from 'react-hot-toast';
import type { VectorStoreType } from '../../types/infrastructure';

interface BackendStatus {
  name: string;
  deployed: boolean;
  endpoint: string | null;
  status: string;
  estimated_cost_monthly: number | null;
  queries_24h?: number;
  avg_latency_ms?: number;
  uptime_percent?: number;
}

interface InfrastructureStatus {
  deployed_stores: BackendStatus[];
  total_deployed: number;
  total_cost_monthly: number;
  overall_status: 'healthy' | 'degraded' | 'down';
  uptime_percent: number;
}

interface ActivityLog {
  id: string;
  timestamp: string;
  message: string;
  type: 'info' | 'warning' | 'success';
}

export const InfrastructurePage: React.FC = () => {
  const { deployments, isLoading, deployStore, destroyStore, refreshStatus, operationInProgress } = useInfrastructure();
  const [operationId, setOperationId] = useState<string | null>(null);
  const [operationType, setOperationType] = useState<'deploy' | 'destroy'>('deploy');
  const [activeStore, setActiveStore] = useState<string>('');
  const [activityLogs, setActivityLogs] = useState<ActivityLog[]>([]);

  // Transform context deployments to page format
  const status: InfrastructureStatus | null = React.useMemo(() => {
    const deployed_stores: BackendStatus[] = Object.entries(deployments).map(([name, deployment]) => ({
      name,
      deployed: deployment.status === 'deployed',
      endpoint: deployment.endpoint || null,
      status: deployment.status,
      // TODO: Replace with actual cost data from API - api.getInfrastructureCosts()
      estimated_cost_monthly: deployment.status === 'deployed' ? 50 : null,
      // TODO: Replace with actual metrics from API - api.getStoreMetrics(name)
      // Expected metrics: queries_24h, avg_latency_ms, uptime_percent
      queries_24h: Math.floor(Math.random() * 5000),
      avg_latency_ms: Math.floor(Math.random() * 200) + 20,
      uptime_percent: 99.5 + Math.random() * 0.5
    }));

    const total_deployed = deployed_stores.filter(s => s.deployed).length;

    return {
      deployed_stores,
      total_deployed,
      total_cost_monthly: total_deployed * 50,
      overall_status: total_deployed > 0 ? 'healthy' : 'down',
      uptime_percent: 99.8
    };
  }, [deployments]);

  useEffect(() => {
    // TODO: Replace with actual activity logs from API - api.getActivityLogs()
    // Expected format: { id, timestamp, message, type: 'info' | 'warning' | 'success' }
    const mockLogs: ActivityLog[] = [
      {
        id: '1',
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        message: 'LanceDB auto-scaled to 3 tasks',
        type: 'info'
      },
      {
        id: '2',
        timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
        message: 'Benchmark #BMK-1234 completed',
        type: 'success'
      },
      {
        id: '3',
        timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
        message: 'S3 Vector index rebuilt',
        type: 'info'
      }
    ];
    setActivityLogs(mockLogs);
  }, []);

  const handleDeploy = async (storeName: string) => {
    try {
      await deployStore(storeName as VectorStoreType);
      setOperationType('deploy');
      setActiveStore(storeName);
      toast.success(`Deployment started for ${storeName}`);
    } catch (error) {
      console.error('Deployment failed:', error);
      toast.error(`Failed to start deployment for ${storeName}`);
    }
  };

  const handleDestroy = async (storeName: string) => {
    if (!confirm(`Are you sure you want to destroy ${storeName}? This action cannot be undone.`)) {
      return;
    }

    try {
      await destroyStore(storeName as VectorStoreType);
      setOperationType('destroy');
      setActiveStore(storeName);
      toast.success(`Destruction started for ${storeName}`);
    } catch (error) {
      console.error('Destruction failed:', error);
      toast.error(`Failed to start destruction for ${storeName}`);
    }
  };

  const handleOperationClose = () => {
    setOperationId(null);
    refreshStatus();
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    if (diffHours > 0) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    return 'Just now';
  };

  if (operationId) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Card className="w-full">
          <CardContent className="p-0">
            <TerraformLogViewer
              operationId={operationId}
              vectorStore={activeStore}
              operationType={operationType}
              onClose={handleOperationClose}
            />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Infrastructure Overview</h1>
              <p className="mt-2 text-sm text-gray-600">
                Manage and monitor your vector store infrastructure
              </p>
            </div>
            <Button variant="outline" onClick={refreshStatus} disabled={isLoading || operationInProgress}>
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Status Overview Cards */}
        {status && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            {/* Overall Status */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-gray-500 flex items-center">
                  <Activity className="h-4 w-4 mr-2" />
                  Status
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center space-x-2">
                  {status.overall_status === 'healthy' ? (
                    <>
                      <CheckCircle className="h-5 w-5 text-green-500" />
                      <span className="text-lg font-semibold text-green-600">All Systems Operational</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="h-5 w-5 text-red-500" />
                      <span className="text-lg font-semibold text-red-600">Issues Detected</span>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Deployed Stores */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-gray-500 flex items-center">
                  <Server className="h-4 w-4 mr-2" />
                  Deployed Stores
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-gray-900">{status.total_deployed}</div>
                <p className="text-xs text-gray-500 mt-1">Active vector stores</p>
              </CardContent>
            </Card>

            {/* Monthly Cost */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-gray-500 flex items-center">
                  <DollarSign className="h-4 w-4 mr-2" />
                  Monthly Cost
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-gray-900">
                  ${status.total_cost_monthly.toFixed(2)}
                </div>
                <p className="text-xs text-gray-500 mt-1">Estimated</p>
              </CardContent>
            </Card>

            {/* Uptime */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-gray-500 flex items-center">
                  <TrendingUp className="h-4 w-4 mr-2" />
                  Uptime
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-gray-900">{status.uptime_percent.toFixed(1)}%</div>
                <p className="text-xs text-gray-500 mt-1">Last 30 days</p>
              </CardContent>
            </Card>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Vector Stores List */}
          <div className="lg:col-span-2 space-y-4">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Vector Stores</h2>

            {status?.deployed_stores.map((store) => (
              <Card key={store.name} className="overflow-hidden">
                <div className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-4 flex-1">
                      <div className={`p-3 rounded-full ${store.deployed ? 'bg-green-100' : 'bg-gray-100'}`}>
                        <Server className={`h-6 w-6 ${store.deployed ? 'text-green-600' : 'text-gray-400'}`} />
                      </div>

                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <h3 className="text-lg font-semibold text-gray-900 capitalize">
                            {store.name.replace('_', ' ')}
                          </h3>
                          <Badge
                            variant={store.deployed ? 'default' : 'secondary'}
                            className={store.deployed ? 'bg-green-500' : ''}
                          >
                            {store.status}
                          </Badge>
                        </div>

                        {store.endpoint && (
                          <p className="text-xs text-gray-500 font-mono mb-3 truncate">
                            {store.endpoint}
                          </p>
                        )}

                        {store.deployed && (
                          <div className="grid grid-cols-3 gap-4 mt-4">
                            <div>
                              <p className="text-xs text-gray-500">Queries (24h)</p>
                              <p className="text-lg font-semibold text-gray-900">
                                {store.queries_24h?.toLocaleString() || 'N/A'}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-gray-500">Avg Latency</p>
                              <p className="text-lg font-semibold text-gray-900">
                                {store.avg_latency_ms || 'N/A'}ms
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-gray-500">Uptime</p>
                              <p className="text-lg font-semibold text-gray-900">
                                {store.uptime_percent?.toFixed(1) || 'N/A'}%
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-col items-end space-y-2 ml-4">
                      {store.estimated_cost_monthly && (
                        <div className="text-right mb-2">
                          <p className="text-xs text-gray-500">Cost</p>
                          <p className="text-lg font-bold text-gray-900">
                            ${store.estimated_cost_monthly.toFixed(2)}/mo
                          </p>
                        </div>
                      )}

                      <div className="flex space-x-2">
                        {store.deployed ? (
                          <>
                            <Button
                              variant="outline"
                              size="sm"
                              disabled
                            >
                              <Settings className="h-4 w-4 mr-2" />
                              Configure
                            </Button>
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => handleDestroy(store.name)}
                              disabled={store.name === 's3vector' || store.name === 'data_bucket'}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </>
                        ) : (
                          <Button
                            variant="default"
                            size="sm"
                            onClick={() => handleDeploy(store.name)}
                          >
                            <Play className="h-4 w-4 mr-2" />
                            Deploy
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            ))}

            {/* Quick Actions */}
            <Card className="mt-6">
              <CardHeader>
                <CardTitle className="text-lg">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-3">
                  <Button variant="outline" disabled>
                    <Zap className="h-4 w-4 mr-2" />
                    Run Health Check
                  </Button>
                  <Button variant="outline" disabled>
                    <Settings className="h-4 w-4 mr-2" />
                    Configure Auto-Scaling
                  </Button>
                  <Button variant="outline" disabled>
                    <TrendingUp className="h-4 w-4 mr-2" />
                    View Metrics
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar - Activity & Alerts */}
          <div className="space-y-6">
            {/* Recent Activity */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center">
                  <Clock className="h-5 w-5 mr-2" />
                  Recent Activity
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {activityLogs.map((log) => (
                    <div key={log.id} className="flex items-start space-x-3 text-sm">
                      <div className={`mt-0.5 ${
                        log.type === 'success' ? 'text-green-500' :
                        log.type === 'warning' ? 'text-yellow-500' :
                        'text-blue-500'
                      }`}>
                        {log.type === 'success' && <CheckCircle className="h-4 w-4" />}
                        {log.type === 'warning' && <AlertCircle className="h-4 w-4" />}
                        {log.type === 'info' && <Activity className="h-4 w-4" />}
                      </div>
                      <div className="flex-1">
                        <p className="text-gray-900">{log.message}</p>
                        <p className="text-xs text-gray-500 mt-1">{formatTimestamp(log.timestamp)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Cost Breakdown */}
            {status && status.total_cost_monthly > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center">
                    <DollarSign className="h-5 w-5 mr-2" />
                    Cost Breakdown
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {status.deployed_stores
                      .filter(store => store.deployed && store.estimated_cost_monthly)
                      .map((store) => (
                        <div key={store.name} className="flex items-center justify-between text-sm">
                          <span className="text-gray-600 capitalize">{store.name.replace('_', ' ')}</span>
                          <span className="font-medium text-gray-900">
                            ${store.estimated_cost_monthly?.toFixed(2)}
                          </span>
                        </div>
                      ))}
                    <div className="pt-3 border-t border-gray-200 flex items-center justify-between font-semibold">
                      <span className="text-gray-900">Total</span>
                      <span className="text-gray-900">${status.total_cost_monthly.toFixed(2)}/mo</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Info Banner */}
            <Card className="bg-yellow-50 border-yellow-200">
              <CardContent className="pt-6">
                <div className="flex">
                  <AlertCircle className="h-5 w-5 text-yellow-600 mr-3 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm text-yellow-800 font-medium mb-1">Deployment Notice</p>
                    <p className="text-xs text-yellow-700">
                      Infrastructure deployment can take 15-20 minutes. Monitor progress in the operation logs.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};
