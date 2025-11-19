import axios from 'axios';

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
}

export interface ProcessVideoRequest {
  s3_key: string;
  model_id?: string;
  bucket_name?: string;
}

export const api = {
  // Config
  getConfig: () => apiClient.get('/config'),
  switchBackend: (config: BackendConfig) => apiClient.post('/config/backend', config),

  // Search
  search: (request: SearchRequest) => apiClient.post('/search', request),

  // Ingest
  uploadVideo: (file: File, bucketName?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (bucketName) {
      formData.append('bucket_name', bucketName);
    }
    return apiClient.post('/ingest/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  processVideo: (request: ProcessVideoRequest) => apiClient.post('/ingest/process', request),
};
