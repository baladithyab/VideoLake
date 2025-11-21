import axios from 'axios';
import type { BenchmarkRequest, BenchmarkResult, BenchmarkProgress } from '../types/benchmark';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface BackendConfig {
  backend_type: string;
}

export interface SearchRequest {
  query_vector: number[];
  top_k?: number;
  collection?: string;
  backend?: string;
}

export interface TextSearchRequest {
  query_text: string;
  top_k?: number;
  backend?: string;
  vector_types?: string[];
  index_arn?: string;
}

export interface ProcessVideoRequest {
  s3_key: string;
  model_id?: string;
  bucket_name?: string;
}

export interface IngestionRequest {
  video_path: string;
  model_type: string;
  backend_types: string[];
}

export interface Dataset {
  name: string;
  source: string;
  hf_dataset_id?: string;
  streaming_supported: boolean;
  estimated_videos: number | string;
}

export interface UploadUrlResponse {
  upload_url: string;
  s3_uri: string;
  expires_in: number;
}

export interface DeployRequest {
  vector_stores: string[];
  wait_for_completion?: boolean;
}

export interface DestroyRequest {
  vector_stores: string[];
  confirm: boolean;
}

export const api = {
  // Config
  getConfig: () => apiClient.get('/config'),
  switchBackend: (config: BackendConfig) => apiClient.post('/config/backend', config),

  // Infrastructure
  getInfrastructureStatus: () => apiClient.get('/api/infrastructure/status'),
  deployInfrastructure: (request: DeployRequest) => apiClient.post('/api/infrastructure/deploy', request),
  destroyInfrastructure: (request: DestroyRequest) => apiClient.delete('/api/infrastructure/destroy', { data: request }),
  
  // Single Store Operations
  deploySingleStore: (store: string) => apiClient.post(`/api/infrastructure/deploy/${store}`),
  destroySingleStore: (store: string, confirm: boolean) => apiClient.delete(`/api/infrastructure/destroy/${store}`, { params: { confirm } }),

  // Search
  search: (request: SearchRequest) => apiClient.post('/api/search', request),
  searchQuery: (request: TextSearchRequest) => apiClient.post('/api/search/query', request),

  // Ingest
  uploadVideo: (file: File, bucketName?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (bucketName) {
      formData.append('bucket_name', bucketName);
    }
    return apiClient.post('/api/ingest/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  processVideo: (request: ProcessVideoRequest) => apiClient.post('/api/ingest/process', request),
  startIngestion: (request: IngestionRequest) => apiClient.post('/ingestion/start', request),
  listDatasets: () => apiClient.get<Dataset[]>('/ingestion/datasets'),
  getUploadUrl: (filename: string, contentType: string) => apiClient.post<UploadUrlResponse>('/ingestion/upload-url', { filename, content_type: contentType }),

  // Benchmark
  startBenchmark: (request: BenchmarkRequest) => apiClient.post<BenchmarkResult>('/api/benchmark/start', request),
  getBenchmarkResults: (benchmarkId: string) => apiClient.get<BenchmarkResult>(`/api/benchmark/results/${benchmarkId}`),
  getBenchmarkProgress: (benchmarkId: string) => apiClient.get<BenchmarkProgress>(`/api/benchmark/progress/${benchmarkId}`),
  listBenchmarks: () => apiClient.get<BenchmarkResult[]>('/api/benchmark/list'),
};
