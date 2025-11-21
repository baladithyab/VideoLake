import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { Server, Play, Trash2, RefreshCw, AlertTriangle } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import TerraformLogViewer from './TerraformLogsViewer';
import { toast } from 'react-hot-toast';

interface BackendStatus {
  name: string;
  deployed: boolean;
  endpoint: string | null;
  status: string;
  estimated_cost_monthly: number | null;
}

interface InfrastructureStatus {
  deployed_stores: BackendStatus[];
  total_deployed: number;
  total_cost_monthly: number;
}

export const InfrastructureManager: React.FC = () => {
  const [status, setStatus] = useState<InfrastructureStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [operationId, setOperationId] = useState<string | null>(null);
  const [operationType, setOperationType] = useState<'deploy' | 'destroy'>('deploy');
  const [activeStore, setActiveStore] = useState<string>('');

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const response = await api.getInfrastructureStatus();
      setStatus(response.data);
    } catch (error) {
      console.error('Failed to fetch infrastructure status:', error);
      toast.error('Failed to load infrastructure status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    // Poll status every 30 seconds
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleDeploy = async (storeName: string) => {
    try {
      const response = await api.deploySingleStore(storeName);
      
      setOperationId(response.data.operation_id);
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
      const response = await api.destroySingleStore(storeName, true);
      
      setOperationId(response.data.operation_id);
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
    fetchStatus(); // Refresh status after operation
  };

  if (operationId) {
    return (
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
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Infrastructure Management</h2>
        <Button variant="outline" size="sm" onClick={fetchStatus} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {status && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">Total Deployed</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{status.total_deployed}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">Monthly Cost (Est.)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${status.total_cost_monthly.toFixed(2)}</div>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4">
        {status?.deployed_stores.map((store) => (
          <Card key={store.name} className="overflow-hidden">
            <div className="p-6 flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className={`p-2 rounded-full ${store.deployed ? 'bg-green-100' : 'bg-gray-100'}`}>
                  <Server className={`h-6 w-6 ${store.deployed ? 'text-green-600' : 'text-gray-400'}`} />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900 capitalize">
                    {store.name.replace('_', ' ')}
                  </h3>
                  <div className="flex items-center space-x-2 mt-1">
                    <Badge variant={store.deployed ? 'default' : 'secondary'} className={store.deployed ? 'bg-green-500' : ''}>
                      {store.status}
                    </Badge>
                    {store.estimated_cost_monthly && (
                      <span className="text-sm text-gray-500">
                        ~${store.estimated_cost_monthly}/mo
                      </span>
                    )}
                  </div>
                  {store.endpoint && (
                    <p className="text-xs text-gray-400 mt-1 font-mono truncate max-w-md">
                      {store.endpoint}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex items-center space-x-2">
                {store.deployed ? (
                  <Button 
                    variant="destructive" 
                    size="sm"
                    onClick={() => handleDestroy(store.name)}
                    disabled={store.name === 's3vector' || store.name === 'data_bucket'} // Prevent destroying core infra
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Destroy
                  </Button>
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
          </Card>
        ))}
      </div>

      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mt-6">
        <div className="flex">
          <div className="flex-shrink-0">
            <AlertTriangle className="h-5 w-5 text-yellow-400" />
          </div>
          <div className="ml-3">
            <p className="text-sm text-yellow-700">
              <strong>Note:</strong> Deploying infrastructure (especially OpenSearch) can take 15-20 minutes. 
              Please do not close the browser tab while an operation is running.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};