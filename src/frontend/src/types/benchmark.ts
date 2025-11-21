export interface BenchmarkConfig {
  backends: string[];
  num_queries: number;
  query_type: 'text' | 'image' | 'video';
  use_existing_embeddings: boolean;
  collection?: string;
}

export interface BenchmarkMetrics {
  backend: string;
  avg_latency: number;
  p95_latency: number;
  p99_latency: number;
  throughput: number;
  total_queries: number;
  failed_queries: number;
  success_rate: number;
}

export interface BenchmarkResult {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  config: BenchmarkConfig;
  metrics: BenchmarkMetrics[];
  started_at: string;
  completed_at?: string;
  error?: string;
}

export interface BenchmarkRequest {
  backends: string[];
  num_queries: number;
  query_type: 'text' | 'image' | 'video';
  use_existing_embeddings?: boolean;
  collection?: string;
}

export interface BenchmarkProgress {
  benchmark_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress_percentage: number;
  current_backend?: string;
  completed_queries: number;
  total_queries: number;
  message?: string;
}