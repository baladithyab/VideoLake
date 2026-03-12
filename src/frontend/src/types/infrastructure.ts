/**
 * Infrastructure types for deployment, management, and monitoring
 */

export type VectorStoreType = 's3vector' | 'lancedb' | 'qdrant' | 'opensearch';
export type EmbeddingProviderType = 'bedrock_titan' | 'bedrock_cohere' | 'sagemaker' | 'jumpstart' | 'external';

export interface VectorStoreConfig {
  type: VectorStoreType;
  name: string;
  displayName: string;
  description: string;
  cost: {
    storage: number; // $/GB/month
    requests: number; // $/1K requests
    compute?: number; // $/hour (for managed services)
  };
  features: {
    multiModal: boolean;
    filtering: boolean;
    hybridSearch: boolean;
    managedService: boolean;
  };
}

export interface EmbeddingProviderConfig {
  type: EmbeddingProviderType;
  name: string;
  displayName: string;
  modelId: string;
  supportedModalities: ('text' | 'image' | 'audio' | 'video')[];
  dimensions: number;
  cost: {
    perToken?: number; // For text
    perImage?: number; // For vision
    perSecond?: number; // For audio
  };
}

export interface DeploymentConfig {
  vectorStores: VectorStoreType[];
  embeddingProviders: EmbeddingProviderType[];
  datasets: string[];
  estimatedDataSize: number; // GB
  estimatedQueries: number; // per month
}

export interface CostEstimate {
  monthly: {
    storage: number;
    compute: number;
    requests: number;
    embeddings: number;
    total: number;
  };
  breakdown: {
    [key: string]: number;
  };
}

export type InfrastructureStatus = 'not_deployed' | 'deploying' | 'deployed' | 'destroying' | 'failed' | 'partial';

export interface VectorStoreDeployment {
  type: VectorStoreType;
  status: InfrastructureStatus;
  endpoint?: string;
  region?: string;
  createdAt?: string;
  updatedAt?: string;
  error?: string;
  terraform?: {
    state: 'planned' | 'applying' | 'applied' | 'destroying' | 'destroyed' | 'error';
    operations: TerraformOperation[];
  };
}

export interface TerraformOperation {
  id: string;
  action: 'plan' | 'apply' | 'destroy';
  status: 'pending' | 'running' | 'completed' | 'failed';
  startedAt: string;
  completedAt?: string;
  logs: string[];
  error?: string;
  resources?: {
    created: number;
    updated: number;
    destroyed: number;
  };
}

export interface InfrastructureState {
  deployments: Record<VectorStoreType, VectorStoreDeployment>;
  lastSync: string;
  operationInProgress: boolean;
  currentOperation?: {
    type: 'deploy' | 'destroy';
    stores: VectorStoreType[];
    startedAt: string;
  };
}

export interface DeploymentWizardStep {
  id: string;
  title: string;
  description: string;
  completed: boolean;
  current: boolean;
  data?: Record<string, unknown>;
}

export interface DatasetInfo {
  id: string;
  name: string;
  source: 'huggingface' | 's3' | 'local';
  size: number; // GB
  videoCount: number;
  duration: number; // total hours
  modalities: ('text' | 'image' | 'audio' | 'video')[];
  hfDatasetId?: string;
}
