// Resource state types
export type ResourceState = 'CREATING' | 'ACTIVE' | 'AVAILABLE' | 'DELETING' | 'DELETED' | 'FAILED' | 'NOT_FOUND';

export interface ResourceStatus {
  resource_id: string;
  resource_type: string;
  state: ResourceState;
  arn?: string;
  region?: string;
  progress_percentage: number;
  estimated_time_remaining?: number;
  error_message?: string;
  metadata?: any;
}

