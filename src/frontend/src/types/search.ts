/**
 * Search types for multi-modal search functionality
 */

export type SearchModality = 'text' | 'image' | 'audio' | 'video' | 'multimodal';
export type VectorType = 'visual-text' | 'visual-image' | 'audio' | 'multimodal';

export interface SearchQuery {
  text?: string;
  imageFile?: File;
  imageUrl?: string;
  audioFile?: File;
  videoFile?: File;
  modality: SearchModality;
  filters?: SearchFilters;
}

export interface SearchFilters {
  timeRange?: {
    start: number;
    end: number;
  };
  videoIds?: string[];
  minScore?: number;
  metadata?: Record<string, unknown>;
}

export interface SearchRequest {
  query_text?: string;
  query_vector?: number[];
  top_k?: number;
  backend?: string;
  vector_types?: VectorType[];
  filters?: SearchFilters;
  collection?: string;
  index_arn?: string;
}

export interface SearchResult {
  id: string;
  score: number;
  metadata: SearchResultMetadata;
  embedding?: number[];
}

export interface SearchResultMetadata {
  video_id: string;
  s3_uri: string;
  presigned_url?: string;
  start_time: number;
  end_time: number;
  text?: string;
  frame_url?: string;
  audio_features?: Record<string, unknown>;
  vector_type: VectorType;
}

export interface SearchResponse {
  results: SearchResult[];
  query_time: number;
  backend: string;
  total_results: number;
}

export interface SearchHistory {
  id: string;
  query: SearchQuery;
  response: SearchResponse;
  timestamp: string;
  backend: string;
}

export interface SearchState {
  query: SearchQuery | null;
  results: SearchResult[];
  isLoading: boolean;
  error: string | null;
  history: SearchHistory[];
  selectedResult: SearchResult | null;
  backend: string;
}

export interface VideoSegment {
  id: string;
  videoId: string;
  s3Uri: string;
  presignedUrl?: string;
  startTime: number;
  endTime: number;
  thumbnailUrl?: string;
  transcript?: string;
}
