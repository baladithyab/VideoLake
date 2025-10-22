import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// Resources API
export const resourcesAPI = {
  scan: () => apiClient.get('/api/resources/scan'),
  getRegistry: () => apiClient.get('/api/resources/registry'),
  createVectorBucket: (data: { bucket_name: string; encryption_type?: string }) =>
    apiClient.post('/api/resources/vector-bucket', data),
  createVectorIndex: (data: { bucket_name: string; index_name: string; dimension: number; similarity_function?: string }) =>
    apiClient.post('/api/resources/vector-index', data),
  createOpenSearchDomain: (data: { domain_name: string; instance_type?: string; instance_count?: number }) =>
    apiClient.post('/api/resources/opensearch-domain', data),
  cleanup: (resourceType?: string) => apiClient.delete('/api/resources/cleanup', { params: { resource_type: resourceType } }),
  getActive: () => apiClient.get('/api/resources/active'),
  setActive: (resourceType: string, resourceId: string) =>
    apiClient.post('/api/resources/active/set', null, { params: { resource_type: resourceType, resource_id: resourceId } }),
};

// Processing API
export const processingAPI = {
  uploadVideo: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('/api/processing/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  processVideo: (data: {
    video_s3_uri?: string;
    embedding_options?: string[];
    start_sec?: number;
    length_sec?: number;
    use_fixed_length_sec?: number;
  }) => apiClient.post('/api/processing/process', data),
  getJobStatus: (jobId: string) => apiClient.get(`/api/processing/job/${jobId}`),
  listJobs: () => apiClient.get('/api/processing/jobs'),
  storeEmbeddings: (jobId: string, indexArn: string) =>
    apiClient.post('/api/processing/store-embeddings', null, { params: { job_id: jobId, index_arn: indexArn } }),
  getSampleVideos: () => apiClient.get('/api/processing/sample-videos'),
  processSampleVideo: (videoId: string) => apiClient.post('/api/processing/process-sample', null, { params: { video_id: videoId } }),
};

// Search API
export const searchAPI = {
  query: (data: {
    query_text: string;
    vector_types?: string[];
    top_k?: number;
    index_arn?: string;
    use_opensearch?: boolean;
  }) => apiClient.post('/api/search/query', data),
  multiVector: (data: {
    query_text: string;
    vector_types?: string[];
    top_k?: number;
    enable_reranking?: boolean;
  }) => apiClient.post('/api/search/multi-vector', data),
  generateEmbedding: (text: string, modelId?: string) =>
    apiClient.post('/api/search/generate-embedding', null, { params: { text, model_id: modelId } }),
  getSupportedVectorTypes: () => apiClient.get('/api/search/supported-vector-types'),
  dualPattern: (data: {
    query_text: string;
    vector_types?: string[];
    top_k?: number;
    index_arn?: string;
  }) => apiClient.post('/api/search/dual-pattern', data),
};

// Embeddings API
export const embeddingsAPI = {
  visualize: (data: {
    index_arn: string;
    method?: string;
    n_components?: number;
    query_embedding?: number[];
    max_points?: number;
  }) => apiClient.post('/api/embeddings/visualize', data),
  analyze: (data: {
    embeddings: number[][];
    labels?: string[];
  }) => apiClient.post('/api/embeddings/analyze', data),
  getMethods: () => apiClient.get('/api/embeddings/methods'),
};

// Analytics API
export const analyticsAPI = {
  getPerformance: () => apiClient.get('/api/analytics/performance'),
  estimateCost: (data: {
    video_duration_minutes: number;
    embedding_options?: string[];
  }) => apiClient.post('/api/analytics/cost-estimate', data),
  getErrors: () => apiClient.get('/api/analytics/errors'),
  getSystemStatus: () => apiClient.get('/api/analytics/system-status'),
  getUsageStats: (days?: number) => apiClient.get('/api/analytics/usage-stats', { params: { days } }),
};

// Health check
export const healthCheck = () => apiClient.get('/api/health');

