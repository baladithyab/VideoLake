import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { infrastructureAPI } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Server,
  Database,
  Cloud,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Rocket,
  Trash2,
  RefreshCw,
  DollarSign,
  Settings
} from 'lucide-react';
import toast from 'react-hot-toast';
import TerraformLogViewer from '@/components/TerraformLogViewer';

interface VectorStore {
  name: string;
  deployed: boolean;
  endpoint: string | null;
  status: string;
  estimated_cost_monthly: number | null;
}

interface InfrastructureStatus {
  deployed_stores: VectorStore[];
  total_deployed: number;
  total_cost_monthly: number;
}

// Vector store configuration
const VECTOR_STORES = [
  {
    id: 's3_vector',
    name: 'S3 Vector Direct',
    description: 'AWS-native vector storage with S3 Metadata integration',
    icon: Database,
    color: 'bg-blue-500',
  },
  {
    id: 'opensearch',
    name: 'OpenSearch',
    description: 'OpenSearch domain with S3 Vector engine',
    icon: Server,
    color: 'bg-purple-500',
  },
  {
    id: 'qdrant',
    name: 'Qdrant (ECS)',
    description: 'Qdrant vector database on ECS Fargate',
    icon: Cloud,
    color: 'bg-green-500',
  },
  {
    id: 'lancedb_s3',
    name: 'LanceDB (S3)',
    description: 'LanceDB with serverless S3 backend (most cost-effective)',
    icon: Database,
    color: 'bg-orange-500',
  },
  {
    id: 'lancedb_efs',
    name: 'LanceDB (EFS)',
    description: 'LanceDB with shared EFS storage (multi-AZ)',
    icon: Database,
    color: 'bg-yellow-500',
  },
  {
    id: 'lancedb_ebs',
    name: 'LanceDB (EBS)',
    description: 'LanceDB with fast EBS local storage (single-AZ)',
    icon: Database,
    color: 'bg-pink-500',
  },
];

export default function InfrastructureDashboard() {
  const queryClient = useQueryClient();
  const [selectedStores, setSelectedStores] = useState<string[]>([]);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [pendingStore, setPendingStore] = useState<string | null>(null);

  // Configuration state with defaults
  const [config, setConfig] = useState({
    opensearch_password: 'MediaLake-Demo-2024!',
    project_name: 'media-lake-demo',
    aws_region: 'us-east-1',
  });

  // Log viewer state
  const [activeOperation, setActiveOperation] = useState<{
    operationId: string;
    vectorStore: string;
    operationType: 'deploy' | 'destroy';
  } | null>(null);

  // Query infrastructure status
  const { data: statusData, isLoading: statusLoading, error: statusError } = useQuery<InfrastructureStatus>({
    queryKey: ['infrastructure-status'],
    queryFn: async () => {
      const response = await infrastructureAPI.getStatus();
      return response.data;
    },
    refetchInterval: 5000, // Poll every 5 seconds
  });

  // Initialize Terraform mutation
  const initMutation = useMutation({
    mutationFn: () => infrastructureAPI.init(),
    onSuccess: () => {
      toast.success('Terraform initialized successfully');
      queryClient.invalidateQueries({ queryKey: ['infrastructure-status'] });
    },
    onError: (error: any) => {
      toast.error(`Initialization failed: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Deploy mutation
  const deployMutation = useMutation({
    mutationFn: (stores: string[]) =>
      infrastructureAPI.deploy({
        vector_stores: stores,
        wait_for_completion: false
      }),
    onSuccess: (_, stores) => {
      toast.success(`Deploying ${stores.length} vector store(s) in background`);
      queryClient.invalidateQueries({ queryKey: ['infrastructure-status'] });
      setSelectedStores([]);
    },
    onError: (error: any) => {
      toast.error(`Deployment failed: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Deploy single store mutation
  const deploySingleMutation = useMutation({
    mutationFn: (store: string) => infrastructureAPI.deploySingle(store),
    onSuccess: (response, store) => {
      // Show log viewer if operation_id is returned
      if (response.data.operation_id) {
        setActiveOperation({
          operationId: response.data.operation_id,
          vectorStore: store,
          operationType: 'deploy'
        });
      }

      if (response.data.success) {
        toast.success(`${store} deployed successfully`);
      } else {
        toast.error(`${store} deployment failed`);
      }

      queryClient.invalidateQueries({ queryKey: ['infrastructure-status'] });
    },
    onError: (error: any) => {
      toast.error(`Deployment failed: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Destroy mutation (for future batch destroy feature)
  // const destroyMutation = useMutation({
  //   mutationFn: (stores: string[]) =>
  //     infrastructureAPI.destroy({
  //       vector_stores: stores,
  //       confirm: true
  //     }),
  //   onSuccess: (_, stores) => {
  //     toast.success(`Destroyed ${stores.length} vector store(s)`);
  //     queryClient.invalidateQueries({ queryKey: ['infrastructure-status'] });
  //   },
  //   onError: (error: any) => {
  //     toast.error(`Destruction failed: ${error.response?.data?.detail || error.message}`);
  //   },
  // });

  // Destroy single store mutation
  const destroySingleMutation = useMutation({
    mutationFn: (store: string) => infrastructureAPI.destroySingle(store, true),
    onSuccess: (response, store) => {
      // Show log viewer if operation_id is returned
      if (response.data.operation_id) {
        setActiveOperation({
          operationId: response.data.operation_id,
          vectorStore: store,
          operationType: 'destroy'
        });
      }

      if (response.data.success) {
        toast.success(`${store} destroyed successfully`);
      } else {
        toast.error(`${store} destruction failed`);
      }

      queryClient.invalidateQueries({ queryKey: ['infrastructure-status'] });
    },
    onError: (error: any) => {
      toast.error(`Destruction failed: ${error.response?.data?.detail || error.message}`);
    },
  });

  const handleDeploy = (storeId: string) => {
    // Open configuration dialog instead of immediately deploying
    setPendingStore(storeId);
    setConfigDialogOpen(true);
  };

  const handleDestroy = (storeId: string) => {
    if (window.confirm(`⚠️ Destroy ${storeId}? This will DELETE all data and resources.`)) {
      destroySingleMutation.mutate(storeId);
    }
  };

  const handleBatchDeploy = () => {
    if (selectedStores.length === 0) {
      toast.error('Please select at least one vector store');
      return;
    }
    // Open configuration dialog for batch deployment
    setConfigDialogOpen(true);
  };

  const getStoreStatus = (storeId: string): VectorStore | undefined => {
    return statusData?.deployed_stores.find(s => s.name === storeId);
  };

  const isStoreDeployed = (storeId: string): boolean => {
    const store = getStoreStatus(storeId);
    return store?.deployed || false;
  };

  const getStatusBadge = (storeId: string) => {
    const store = getStoreStatus(storeId);
    if (!store || !store.deployed) {
      return <Badge variant="outline" className="gap-1"><XCircle className="h-3 w-3" /> Not Deployed</Badge>;
    }
    if (store.status === 'active' || store.status === 'running') {
      return <Badge variant="default" className="gap-1 bg-green-500"><CheckCircle2 className="h-3 w-3" /> Active</Badge>;
    }
    if (store.status === 'deploying' || store.status === 'creating') {
      return <Badge variant="secondary" className="gap-1"><Loader2 className="h-3 w-3 animate-spin" /> Deploying</Badge>;
    }
    return <Badge variant="secondary">{store.status}</Badge>;
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Infrastructure Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Deploy and manage vector stores with Terraform
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => {
              setPendingStore(null); // Clear pending store for general config
              setConfigDialogOpen(true);
            }}
          >
            <Settings className="h-4 w-4 mr-2" />
            Configure
          </Button>
          <Button
            variant="outline"
            onClick={() => queryClient.invalidateQueries({ queryKey: ['infrastructure-status'] })}
            disabled={statusLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${statusLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            variant="secondary"
            onClick={() => initMutation.mutate()}
            disabled={initMutation.isPending}
          >
            {initMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Initialize Terraform
          </Button>
        </div>
      </div>

      {/* Status Summary */}
      {statusData && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Deployed</CardDescription>
              <CardTitle className="text-3xl">{statusData.total_deployed}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                {VECTOR_STORES.length - statusData.total_deployed} available to deploy
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Monthly Cost Estimate</CardDescription>
              <CardTitle className="text-3xl flex items-center gap-1">
                <DollarSign className="h-6 w-6" />
                {statusData.total_cost_monthly.toFixed(2)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Across all deployed resources
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>System Status</CardDescription>
              <CardTitle className="flex items-center gap-2">
                {statusData.total_deployed > 0 ? (
                  <>
                    <CheckCircle2 className="h-6 w-6 text-green-500" />
                    Operational
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-6 w-6 text-orange-500" />
                    No Deployments
                  </>
                )}
              </CardTitle>
            </CardHeader>
          </Card>
        </div>
      )}

      {/* Error Alert */}
      {statusError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load infrastructure status. Please try refreshing.
          </AlertDescription>
        </Alert>
      )}

      {/* Vector Store Cards */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Vector Stores</h2>
          {selectedStores.length > 0 && (
            <Button onClick={handleBatchDeploy} disabled={deployMutation.isPending}>
              {deployMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              <Rocket className="h-4 w-4 mr-2" />
              Deploy Selected ({selectedStores.length})
            </Button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {VECTOR_STORES.map((store) => {
            const StoreIcon = store.icon;
            const deployed = isStoreDeployed(store.id);
            const storeStatus = getStoreStatus(store.id);

            return (
              <Card key={store.id} className={`relative ${deployed ? 'border-green-500' : ''}`}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${store.color}`}>
                        <StoreIcon className="h-6 w-6 text-white" />
                      </div>
                      <div>
                        <CardTitle>{store.name}</CardTitle>
                        <CardDescription className="mt-1">{store.description}</CardDescription>
                      </div>
                    </div>
                    {getStatusBadge(store.id)}
                  </div>
                </CardHeader>

                <CardContent className="space-y-2">
                  {deployed && storeStatus && (
                    <>
                      {storeStatus.endpoint && (
                        <div className="text-sm">
                          <span className="font-medium">Endpoint: </span>
                          <span className="text-muted-foreground font-mono text-xs break-all">
                            {storeStatus.endpoint}
                          </span>
                        </div>
                      )}
                      {storeStatus.estimated_cost_monthly && (
                        <div className="text-sm">
                          <span className="font-medium">Cost: </span>
                          <span className="text-muted-foreground">
                            ${storeStatus.estimated_cost_monthly.toFixed(2)}/month
                          </span>
                        </div>
                      )}
                    </>
                  )}

                  {!deployed && (
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id={`select-${store.id}`}
                        checked={selectedStores.includes(store.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedStores([...selectedStores, store.id]);
                          } else {
                            setSelectedStores(selectedStores.filter(s => s !== store.id));
                          }
                        }}
                        className="h-4 w-4"
                      />
                      <label htmlFor={`select-${store.id}`} className="text-sm text-muted-foreground">
                        Select for batch deployment
                      </label>
                    </div>
                  )}
                </CardContent>

                <CardFooter className="flex gap-2">
                  {!deployed ? (
                    <Button
                      className="flex-1"
                      onClick={() => handleDeploy(store.id)}
                      disabled={deploySingleMutation.isPending}
                    >
                      {deploySingleMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                      <Rocket className="h-4 w-4 mr-2" />
                      Deploy
                    </Button>
                  ) : (
                    <Button
                      className="flex-1"
                      variant="destructive"
                      onClick={() => handleDestroy(store.id)}
                      disabled={destroySingleMutation.isPending}
                    >
                      {destroySingleMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                      <Trash2 className="h-4 w-4 mr-2" />
                      Destroy
                    </Button>
                  )}
                </CardFooter>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Quick Deploy Templates */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Quick Deploy Templates</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">S3 Vector Only</CardTitle>
              <CardDescription>
                Lightweight setup for AWS-native vector storage
              </CardDescription>
            </CardHeader>
            <CardFooter>
              <Button
                className="w-full"
                onClick={() => {
                  if (window.confirm('Deploy S3 Vector Direct storage?')) {
                    deploySingleMutation.mutate('s3_vector');
                  }
                }}
                disabled={isStoreDeployed('s3_vector')}
              >
                <Rocket className="h-4 w-4 mr-2" />
                {isStoreDeployed('s3_vector') ? 'Already Deployed' : 'Deploy'}
              </Button>
            </CardFooter>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">OpenSearch Stack</CardTitle>
              <CardDescription>
                OpenSearch with S3 Vector engine for hybrid search
              </CardDescription>
            </CardHeader>
            <CardFooter>
              <Button
                className="w-full"
                onClick={() => {
                  if (window.confirm('Deploy OpenSearch domain?')) {
                    deploySingleMutation.mutate('opensearch');
                  }
                }}
                disabled={isStoreDeployed('opensearch')}
              >
                <Rocket className="h-4 w-4 mr-2" />
                {isStoreDeployed('opensearch') ? 'Already Deployed' : 'Deploy'}
              </Button>
            </CardFooter>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Full Comparison</CardTitle>
              <CardDescription>
                Deploy all backends for comprehensive comparison
              </CardDescription>
            </CardHeader>
            <CardFooter>
              <Button
                className="w-full"
                onClick={() => {
                  const allStores = VECTOR_STORES.map(s => s.id);
                  if (window.confirm('Deploy all vector stores? This may take 10-15 minutes.')) {
                    deployMutation.mutate(allStores);
                  }
                }}
                disabled={statusData?.total_deployed === VECTOR_STORES.length}
              >
                <Rocket className="h-4 w-4 mr-2" />
                {statusData?.total_deployed === VECTOR_STORES.length ? 'All Deployed' : 'Deploy All'}
              </Button>
            </CardFooter>
          </Card>
        </div>
      </div>

      {/* Configuration Dialog */}
      <Dialog open={configDialogOpen} onOpenChange={setConfigDialogOpen}>
        <DialogContent className="sm:max-w-[525px]">
          <DialogHeader>
            <DialogTitle>Deployment Configuration</DialogTitle>
            <DialogDescription>
              Configure deployment settings. These will be used as Terraform variables.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="project_name">Project Name</Label>
              <Input
                id="project_name"
                value={config.project_name}
                onChange={(e) => setConfig({ ...config, project_name: e.target.value })}
                placeholder="media-lake-demo"
              />
              <p className="text-xs text-muted-foreground">
                Used as prefix for all AWS resources
              </p>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="aws_region">AWS Region</Label>
              <Input
                id="aws_region"
                value={config.aws_region}
                onChange={(e) => setConfig({ ...config, aws_region: e.target.value })}
                placeholder="us-east-1"
              />
              <p className="text-xs text-muted-foreground">
                AWS region for deployment
              </p>
            </div>
            {(pendingStore === 'opensearch' || selectedStores.includes('opensearch')) && (
              <div className="grid gap-2">
                <Label htmlFor="opensearch_password">OpenSearch Master Password</Label>
                <Input
                  id="opensearch_password"
                  type="password"
                  value={config.opensearch_password}
                  onChange={(e) => setConfig({ ...config, opensearch_password: e.target.value })}
                  placeholder="Min 8 chars, include upper, lower, number, special char"
                />
                <p className="text-xs text-muted-foreground">
                  Must be at least 8 characters with uppercase, lowercase, number, and special character
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfigDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => {
              setConfigDialogOpen(false);
              if (pendingStore) {
                deploySingleMutation.mutate(pendingStore);
                setPendingStore(null);
              } else if (selectedStores.length > 0) {
                deployMutation.mutate(selectedStores);
              }
            }}>
              <Rocket className="h-4 w-4 mr-2" />
              Deploy
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Terraform Log Viewer Dialog */}
      {activeOperation && (
        <Dialog open={true} onOpenChange={() => setActiveOperation(null)}>
          <DialogContent className="max-w-5xl">
            <TerraformLogViewer
              operationId={activeOperation.operationId}
              vectorStore={activeOperation.vectorStore}
              operationType={activeOperation.operationType}
              onClose={() => {
                setActiveOperation(null);
                queryClient.invalidateQueries({ queryKey: ['infrastructure-status'] });
              }}
            />
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
