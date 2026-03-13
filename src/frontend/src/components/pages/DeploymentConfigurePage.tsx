import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

// Types
interface EmbeddingModel {
  id: string;
  name: string;
  description: string;
  dimensions: number;
  useCase: string;
  cost: string;
  modality: string;
  recommended?: boolean;
}

interface VectorStore {
  id: string;
  name: string;
  description: string;
  cost: string;
  costDetails: string;
  features: string[];
  alwaysOn?: boolean;
  recommended?: boolean;
}

interface ComputeConfig {
  instanceType: string;
  vCPU: string;
  memory: string;
  cost: string;
}

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

// Data
// TODO: These should be fetched from the API instead of being hardcoded
// Consider adding API endpoints: GET /api/v1/models/embedding and GET /api/v1/infrastructure/stores/available
const EMBEDDING_MODELS: EmbeddingModel[] = [
  {
    id: 'clip',
    name: 'CLIP (ViT-B/32)',
    description: 'Multi-modal: Image + Text',
    dimensions: 512,
    useCase: 'General image-text search',
    cost: '~$0.50/1M vectors',
    modality: 'Image + Text',
    recommended: true,
  },
  {
    id: 'whisper',
    name: 'Whisper (Medium)',
    description: 'Audio transcription + embeddings',
    dimensions: 1024,
    useCase: 'Audio content search',
    cost: '~$0.006/minute',
    modality: 'Audio',
  },
  {
    id: 'bert',
    name: 'BERT (base-uncased)',
    description: 'Text-only embeddings',
    dimensions: 768,
    useCase: 'Text search and classification',
    cost: '~$0.10/1M vectors',
    modality: 'Text',
  },
];

const VECTOR_STORES: VectorStore[] = [
  {
    id: 's3vector',
    name: 'S3 Vector',
    description: 'Native S3-based vector storage',
    cost: '~$5/mo',
    costDetails: 'S3 storage',
    features: ['Serverless', 'Cost-effective', 'S3 native'],
    alwaysOn: true,
  },
  {
    id: 'lancedb',
    name: 'LanceDB',
    description: 'Columnar store with SIMD acceleration',
    cost: '~$28/mo',
    costDetails: 'ECS Fargate',
    features: ['Fast queries', 'Columnar format', 'SIMD optimized'],
    recommended: true,
  },
  {
    id: 'qdrant',
    name: 'Qdrant',
    description: 'Purpose-built for vector search',
    cost: '~$45/mo',
    costDetails: 'ECS + EC2',
    features: ['High performance', 'Rich filtering', 'Production-ready'],
  },
  {
    id: 'opensearch',
    name: 'OpenSearch',
    description: 'Full-featured with analytics',
    cost: '~$180/mo',
    costDetails: 'Managed ES',
    features: ['Analytics', 'Kibana dashboards', 'Full-text search'],
  },
];

const COMPUTE_CONFIGS: Record<string, ComputeConfig[]> = {
  lancedb: [
    { instanceType: 't3.small', vCPU: '0.5', memory: '1GB', cost: '~$15/mo' },
    { instanceType: 't3.medium', vCPU: '2', memory: '4GB', cost: '~$28/mo' },
    { instanceType: 't3.large', vCPU: '2', memory: '8GB', cost: '~$58/mo' },
  ],
  qdrant: [
    { instanceType: 't3.medium', vCPU: '2', memory: '4GB', cost: '~$45/mo' },
    { instanceType: 't3.large', vCPU: '2', memory: '8GB', cost: '~$75/mo' },
    { instanceType: 't3.xlarge', vCPU: '4', memory: '16GB', cost: '~$150/mo' },
  ],
};

export default function DeploymentConfigurePage() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [config, setConfig] = useState<DeploymentConfig>({
    embeddingModels: [],
    vectorStores: ['s3vector'], // S3 Vector always selected
    computeConfigs: {
      lancedb: { instanceType: 't3.medium', minTasks: 1, maxTasks: 4 },
      qdrant: { instanceType: 't3.medium', minTasks: 1, maxTasks: 4 },
    },
    storageClass: 'intelligent-tiering',
    estimatedDataSize: 10,
  });

  const totalSteps = 3;

  // Calculate estimated cost
  const calculateCost = (): number => {
    let cost = 5; // Base S3 Vector cost

    // Add vector store costs
    if (config.vectorStores.includes('lancedb')) {
      const lanceConfig = COMPUTE_CONFIGS.lancedb.find(
        c => c.instanceType === config.computeConfigs.lancedb.instanceType
      );
      cost += parseFloat(lanceConfig?.cost.replace(/[^0-9.]/g, '') || '28');
    }
    if (config.vectorStores.includes('qdrant')) {
      const qdrantConfig = COMPUTE_CONFIGS.qdrant.find(
        c => c.instanceType === config.computeConfigs.qdrant.instanceType
      );
      cost += parseFloat(qdrantConfig?.cost.replace(/[^0-9.]/g, '') || '45');
    }
    if (config.vectorStores.includes('opensearch')) {
      cost += 180;
    }

    // Storage cost
    cost += 2.3;

    return cost;
  };

  const handleNext = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    } else {
      // Save config and navigate to review
      localStorage.setItem('deploymentConfig', JSON.stringify(config));
      navigate('/deployment/review');
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    } else {
      navigate('/welcome');
    }
  };

  const toggleEmbeddingModel = (modelId: string) => {
    setConfig(prev => ({
      ...prev,
      embeddingModels: prev.embeddingModels.includes(modelId)
        ? prev.embeddingModels.filter(id => id !== modelId)
        : [...prev.embeddingModels, modelId],
    }));
  };

  const toggleVectorStore = (storeId: string) => {
    if (storeId === 's3vector') return; // Can't deselect S3 Vector

    setConfig(prev => ({
      ...prev,
      vectorStores: prev.vectorStores.includes(storeId)
        ? prev.vectorStores.filter(id => id !== storeId)
        : [...prev.vectorStores, storeId],
    }));
  };

  const canProceed = () => {
    if (currentStep === 1) return config.embeddingModels.length > 0;
    if (currentStep === 2) return config.vectorStores.length > 0;
    return true;
  };

  return (
    <div className="container mx-auto max-w-4xl py-8 px-4">
      {/* Progress Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-2xl font-bold">
            Step {currentStep} of {totalSteps}: {
              currentStep === 1 ? 'Select Embedding Models' :
              currentStep === 2 ? 'Select Vector Stores to Deploy' :
              'Compute Configuration'
            }
          </h1>
          {currentStep > 1 && (
            <div className="text-sm text-muted-foreground">
              Running cost estimate: <span className="font-semibold text-foreground">${calculateCost().toFixed(2)}/month</span>
            </div>
          )}
        </div>

        {/* Progress bar */}
        <div className="flex gap-2">
          {[1, 2, 3].map(step => (
            <div
              key={step}
              className={cn(
                "h-2 flex-1 rounded-full transition-colors",
                step <= currentStep ? "bg-primary" : "bg-muted"
              )}
            />
          ))}
        </div>
      </div>

      {/* Step Content */}
      <div className="space-y-6">
        {/* Step 1: Embedding Models */}
        {currentStep === 1 && (
          <>
            <p className="text-muted-foreground mb-6">
              Choose the embedding models for vector generation
            </p>
            <div className="space-y-4">
              {EMBEDDING_MODELS.map(model => (
                <Card
                  key={model.id}
                  className={cn(
                    "cursor-pointer transition-all hover:shadow-md",
                    config.embeddingModels.includes(model.id) && "ring-2 ring-primary"
                  )}
                  onClick={() => toggleEmbeddingModel(model.id)}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <input
                          type="checkbox"
                          checked={config.embeddingModels.includes(model.id)}
                          onChange={() => {}}
                          className="w-4 h-4 rounded border-gray-300"
                        />
                        <div>
                          <CardTitle className="flex items-center gap-2">
                            {model.name}
                            {model.recommended && (
                              <Badge variant="secondary">Recommended</Badge>
                            )}
                          </CardTitle>
                          <CardDescription className="mt-1">
                            {model.description}
                          </CardDescription>
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Modality:</span> {model.modality}
                      </div>
                      <div>
                        <span className="text-muted-foreground">Dimensions:</span> {model.dimensions}
                      </div>
                      <div>
                        <span className="text-muted-foreground">Use case:</span> {model.useCase}
                      </div>
                      <div>
                        <span className="text-muted-foreground">Cost:</span> {model.cost}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </>
        )}

        {/* Step 2: Vector Stores */}
        {currentStep === 2 && (
          <>
            <p className="text-muted-foreground mb-6">
              Select the vector stores you want to deploy for benchmarking and search
            </p>
            <div className="grid grid-cols-2 gap-4">
              {VECTOR_STORES.map(store => (
                <Card
                  key={store.id}
                  className={cn(
                    "cursor-pointer transition-all hover:shadow-md",
                    config.vectorStores.includes(store.id) && "ring-2 ring-primary",
                    store.alwaysOn && "opacity-100"
                  )}
                  onClick={() => !store.alwaysOn && toggleVectorStore(store.id)}
                >
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={config.vectorStores.includes(store.id)}
                        onChange={() => {}}
                        disabled={store.alwaysOn}
                        className="w-4 h-4 rounded border-gray-300 disabled:opacity-50"
                      />
                      <div className="flex-1">
                        <CardTitle className="flex items-center gap-2 text-base">
                          {store.name}
                          {store.alwaysOn && (
                            <Badge variant="secondary">Always On</Badge>
                          )}
                          {store.recommended && (
                            <Badge variant="secondary">Recommended</Badge>
                          )}
                        </CardTitle>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm text-muted-foreground">{store.description}</p>
                    <div className="space-y-1">
                      {store.features.map((feature, idx) => (
                        <div key={idx} className="text-xs text-muted-foreground">
                          • {feature}
                        </div>
                      ))}
                    </div>
                    <div className="pt-2 border-t">
                      <div className="font-semibold">{store.cost}</div>
                      <div className="text-xs text-muted-foreground">({store.costDetails})</div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </>
        )}

        {/* Step 3: Compute Configuration */}
        {currentStep === 3 && (
          <>
            <div className="mb-6">
              <p className="text-lg font-semibold">
                Estimated monthly cost: <span className="text-primary">${calculateCost().toFixed(2)}</span>
              </p>
            </div>

            <div className="space-y-6">
              {/* LanceDB Configuration */}
              {config.vectorStores.includes('lancedb') && (
                <Card>
                  <CardHeader>
                    <CardTitle>LanceDB Configuration</CardTitle>
                    <CardDescription>Configure compute resources for LanceDB</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <label className="text-sm font-medium mb-3 block">Instance Type</label>
                      <div className="space-y-2">
                        {COMPUTE_CONFIGS.lancedb.map(cfg => (
                          <label
                            key={cfg.instanceType}
                            className={cn(
                              "flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all",
                              config.computeConfigs.lancedb.instanceType === cfg.instanceType
                                ? "border-primary bg-primary/5"
                                : "border-border hover:border-primary/50"
                            )}
                          >
                            <input
                              type="radio"
                              name="lancedb-instance"
                              checked={config.computeConfigs.lancedb.instanceType === cfg.instanceType}
                              onChange={() => setConfig(prev => ({
                                ...prev,
                                computeConfigs: {
                                  ...prev.computeConfigs,
                                  lancedb: { ...prev.computeConfigs.lancedb, instanceType: cfg.instanceType }
                                }
                              }))}
                              className="w-4 h-4"
                            />
                            <div className="flex-1 flex items-center justify-between">
                              <span className="font-medium">
                                {cfg.instanceType} ({cfg.vCPU} vCPU, {cfg.memory})
                              </span>
                              <span className="text-muted-foreground">{cfg.cost}</span>
                            </div>
                          </label>
                        ))}
                      </div>
                    </div>

                    <div>
                      <Label className="text-sm font-medium mb-2 block">Auto-scaling</Label>
                      <div className="flex gap-4">
                        <div className="flex-1">
                          <Label className="text-xs text-muted-foreground">Min tasks</Label>
                          <Input
                            type="number"
                            min="1"
                            max="10"
                            value={config.computeConfigs.lancedb.minTasks}
                            onChange={e => setConfig(prev => ({
                              ...prev,
                              computeConfigs: {
                                ...prev.computeConfigs,
                                lancedb: { ...prev.computeConfigs.lancedb, minTasks: parseInt(e.target.value) }
                              }
                            }))}
                            className="mt-1"
                          />
                        </div>
                        <div className="flex-1">
                          <Label className="text-xs text-muted-foreground">Max tasks</Label>
                          <Input
                            type="number"
                            min="1"
                            max="10"
                            value={config.computeConfigs.lancedb.maxTasks}
                            onChange={e => setConfig(prev => ({
                              ...prev,
                              computeConfigs: {
                                ...prev.computeConfigs,
                                lancedb: { ...prev.computeConfigs.lancedb, maxTasks: parseInt(e.target.value) }
                              }
                            }))}
                            className="mt-1"
                          />
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Qdrant Configuration */}
              {config.vectorStores.includes('qdrant') ? (
                <Card>
                  <CardHeader>
                    <CardTitle>Qdrant Configuration</CardTitle>
                    <CardDescription>Configure compute resources for Qdrant</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <label className="text-sm font-medium mb-3 block">Instance Type</label>
                      <div className="space-y-2">
                        {COMPUTE_CONFIGS.qdrant.map(cfg => (
                          <label
                            key={cfg.instanceType}
                            className={cn(
                              "flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all",
                              config.computeConfigs.qdrant.instanceType === cfg.instanceType
                                ? "border-primary bg-primary/5"
                                : "border-border hover:border-primary/50"
                            )}
                          >
                            <input
                              type="radio"
                              name="qdrant-instance"
                              checked={config.computeConfigs.qdrant.instanceType === cfg.instanceType}
                              onChange={() => setConfig(prev => ({
                                ...prev,
                                computeConfigs: {
                                  ...prev.computeConfigs,
                                  qdrant: { ...prev.computeConfigs.qdrant, instanceType: cfg.instanceType }
                                }
                              }))}
                              className="w-4 h-4"
                            />
                            <div className="flex-1 flex items-center justify-between">
                              <span className="font-medium">
                                {cfg.instanceType} ({cfg.vCPU} vCPU, {cfg.memory})
                              </span>
                              <span className="text-muted-foreground">{cfg.cost}</span>
                            </div>
                          </label>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent className="py-8">
                    <p className="text-center text-muted-foreground">
                      NOT SELECTED<br />
                      <span className="text-sm">Enable Qdrant to configure compute</span>
                    </p>
                  </CardContent>
                </Card>
              )}

              {/* Storage Configuration */}
              <Card>
                <CardHeader>
                  <CardTitle>Storage Configuration</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">S3 Storage Class:</span>
                      <span className="font-medium">Intelligent-Tiering</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Estimated data size:</span>
                      <span className="font-medium">{config.estimatedDataSize}GB</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Monthly cost:</span>
                      <span className="font-medium">~$2.30</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </>
        )}

        {/* Validation Alert */}
        {!canProceed() && currentStep === 1 && (
          <Alert>
            <AlertDescription>
              Please select at least one embedding model to continue.
            </AlertDescription>
          </Alert>
        )}
      </div>

      {/* Navigation Buttons */}
      <div className="flex justify-between mt-8 pt-6 border-t">
        <Button variant="outline" onClick={handleBack}>
          ← Back
        </Button>
        <Button onClick={handleNext} disabled={!canProceed()}>
          {currentStep < totalSteps ? 'Continue →' : 'Review →'}
        </Button>
      </div>
    </div>
  );
}
