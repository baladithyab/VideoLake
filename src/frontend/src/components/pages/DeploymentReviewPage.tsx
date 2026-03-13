import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { useInfrastructure } from '@/contexts/InfrastructureContext';
import type { VectorStoreType } from '@/types/infrastructure';

interface DeploymentConfig {
  embeddingModels: string[];
  vectorStores: string[];
  computeConfigs: Record<string, {
    instanceType: string;
    minTasks: number;
    maxTasks: number;
  }>;
  storageClass: string;
  estimatedDataSize: number;
}

// Model and store display names
const MODEL_NAMES: Record<string, string> = {
  clip: 'CLIP (ViT-B/32)',
  whisper: 'Whisper (Medium)',
  bert: 'BERT (base-uncased)',
};

const STORE_NAMES: Record<string, string> = {
  s3vector: 'S3 Vector',
  lancedb: 'LanceDB',
  qdrant: 'Qdrant',
  opensearch: 'OpenSearch',
};

const STORE_COSTS: Record<string, number> = {
  s3vector: 5.0,
  lancedb: 28.0,
  qdrant: 45.0,
  opensearch: 180.0,
};

export default function DeploymentReviewPage() {
  const navigate = useNavigate();
  const { deployMultiple, operationInProgress, error: contextError } = useInfrastructure();
  const [config, setConfig] = useState<DeploymentConfig | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use context operation state for deploying
  const deploying = operationInProgress;

  useEffect(() => {
    // Load config from localStorage
    const savedConfig = localStorage.getItem('deploymentConfig');
    if (savedConfig) {
      try {
        setConfig(JSON.parse(savedConfig));
      } catch {
        setError('Failed to load configuration. Please restart the wizard.');
      }
    } else {
      setError('No configuration found. Please complete the wizard first.');
    }
  }, []);

  const calculateTotalCost = (): number => {
    if (!config) return 0;

    let total = 0;
    config.vectorStores.forEach(store => {
      total += STORE_COSTS[store] || 0;
    });
    // Add storage cost
    total += 2.3;
    return total;
  };

  const handleDeploy = async () => {
    if (!config) return;

    setError(null);

    try {
      // Filter out s3vector as it's always deployed
      const storesToDeploy = config.vectorStores
        .filter(s => s !== 's3vector')
        .map(s => s as VectorStoreType);

      // Start deployment using context
      await deployMultiple(storesToDeploy);

      // Store deployment metadata for progress tracking
      localStorage.setItem('deploymentInProgress', 'true');
      localStorage.setItem('deploymentStartTime', new Date().toISOString());

      // Navigate to progress page
      navigate('/deployment/progress');
    } catch (err) {
      console.error('Deployment error:', err);
      const errorMessage = err && typeof err === 'object' && 'response' in err
        ? (err.response as { data?: { detail?: string } })?.data?.detail
        : undefined;
      setError(errorMessage || 'Failed to start deployment. Please try again.');
    }
  };

  const handleEdit = (step: number) => {
    navigate(`/deployment/configure?step=${step}`);
  };

  if (error && !config) {
    return (
      <div className="container mx-auto max-w-4xl py-8 px-4">
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <div className="mt-4">
          <Button onClick={() => navigate('/deployment/configure')}>
            Start Configuration Wizard
          </Button>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="container mx-auto max-w-4xl py-8 px-4">
        <p>Loading configuration...</p>
      </div>
    );
  }

  const totalCost = calculateTotalCost();
  const estimatedTime = '15-20 minutes';

  return (
    <div className="container mx-auto max-w-4xl py-8 px-4">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Review Configuration</h1>
        <p className="text-muted-foreground">
          Review your deployment settings before proceeding
        </p>
      </div>

      {/* Cost Summary */}
      <Card className="mb-6 border-primary/50 bg-primary/5">
        <CardContent className="py-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-bold">
                Total Estimated Monthly Cost: ${totalCost.toFixed(2)}
              </div>
              <div className="text-sm text-muted-foreground mt-1">
                Deployment Time: ~{estimatedTime}
              </div>
            </div>
            <Badge variant="secondary" className="text-lg px-4 py-2">
              {config.vectorStores.length} {config.vectorStores.length === 1 ? 'Store' : 'Stores'}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Configuration Details */}
      <div className="space-y-4">
        {/* Embedding Models */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Embedding Models</CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleEdit(1)}
                disabled={deploying}
              >
                Edit
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {config.embeddingModels.map(modelId => (
                <li key={modelId} className="flex items-center gap-2">
                  <span className="text-primary">•</span>
                  <span>{MODEL_NAMES[modelId] || modelId}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        {/* Vector Stores */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Vector Stores</CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleEdit(2)}
                disabled={deploying}
              >
                Edit
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {config.vectorStores.map(storeId => (
                <div key={storeId} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-primary">•</span>
                    <span className="font-medium">{STORE_NAMES[storeId] || storeId}</span>
                    {storeId === 's3vector' && (
                      <Badge variant="secondary" className="text-xs">Always Active</Badge>
                    )}
                    {storeId === 'lancedb' && config.computeConfigs.lancedb && (
                      <span className="text-sm text-muted-foreground">
                        ({config.computeConfigs.lancedb.instanceType})
                      </span>
                    )}
                  </div>
                  <span className="text-sm font-semibold">
                    ${STORE_COSTS[storeId].toFixed(2)}/mo
                  </span>
                </div>
              ))}
              {config.vectorStores.includes('lancedb') && config.computeConfigs.lancedb && (
                <div className="ml-6 text-sm text-muted-foreground">
                  Min {config.computeConfigs.lancedb.minTasks}, Max {config.computeConfigs.lancedb.maxTasks} tasks
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Storage */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Storage</CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleEdit(3)}
                disabled={deploying}
              >
                Edit
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-primary">•</span>
                  <span>S3 {config.storageClass}</span>
                </div>
                <span className="text-sm font-semibold">$2.30/mo</span>
              </div>
              <div className="ml-6 text-sm text-muted-foreground">
                Estimated {config.estimatedDataSize}GB data
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Infrastructure Details */}
        <Card>
          <CardHeader>
            <CardTitle>Infrastructure Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-primary">•</span>
                <span className="text-muted-foreground">Region:</span>
                <span className="font-medium">us-east-1</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-primary">•</span>
                <span className="text-muted-foreground">VPC:</span>
                <span className="font-medium">New dedicated VPC</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-primary">•</span>
                <span className="text-muted-foreground">Monitoring:</span>
                <span className="font-medium">CloudWatch (included)</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Deployment Notice */}
        <Alert>
          <AlertDescription>
            <div className="font-semibold mb-2">⚠️ Deployment Notice</div>
            <ul className="space-y-1 text-sm ml-4">
              <li>• Infrastructure will be created via Terraform</li>
              <li>• Do not close browser during deployment</li>
              <li>• You can monitor progress in real-time</li>
              <li>• Partial deployments can be resumed</li>
            </ul>
          </AlertDescription>
        </Alert>

        {/* Confirmation Checkbox */}
        <Card>
          <CardContent className="py-4">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={e => setConfirmed(e.target.checked)}
                className="w-5 h-5 mt-0.5 rounded border-gray-300"
                disabled={deploying}
              />
              <span className="text-sm">
                I understand the costs and deployment process. I authorize the creation of AWS resources
                that will incur charges as outlined above.
              </span>
            </label>
          </CardContent>
        </Card>

        {/* Error Display */}
        {(error || contextError) && (
          <Alert variant="destructive">
            <AlertDescription>
              {error || contextError?.message || 'An error occurred'}
            </AlertDescription>
          </Alert>
        )}
      </div>

      {/* Navigation Buttons */}
      <div className="flex justify-between mt-8 pt-6 border-t">
        <Button
          variant="outline"
          onClick={() => navigate('/deployment/configure')}
          disabled={deploying}
        >
          ← Back
        </Button>
        <Button
          onClick={handleDeploy}
          disabled={!confirmed || deploying}
          className="min-w-[200px]"
        >
          {deploying ? 'Starting Deployment...' : 'Deploy Infrastructure'}
        </Button>
      </div>
    </div>
  );
}
