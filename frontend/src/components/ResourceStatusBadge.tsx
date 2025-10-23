import { Loader2, CheckCircle, XCircle, AlertCircle, Clock } from 'lucide-react';
import { ResourceState } from '../types/resources';

interface ResourceStatusBadgeProps {
  state: ResourceState;
  progress?: number;
  estimatedTime?: number;
}

export default function ResourceStatusBadge({ state, progress, estimatedTime }: ResourceStatusBadgeProps) {
  const getStateConfig = (state: ResourceState) => {
    switch (state) {
      case 'ACTIVE':
      case 'AVAILABLE':
        return {
          color: 'text-green-700 bg-green-100',
          icon: <CheckCircle className="w-4 h-4" />,
          label: state,
        };
      case 'CREATING':
        return {
          color: 'text-blue-700 bg-blue-100',
          icon: <Loader2 className="w-4 h-4 animate-spin" />,
          label: 'Creating',
        };
      case 'DELETING':
        return {
          color: 'text-orange-700 bg-orange-100',
          icon: <Loader2 className="w-4 h-4 animate-spin" />,
          label: 'Deleting',
        };
      case 'FAILED':
        return {
          color: 'text-red-700 bg-red-100',
          icon: <XCircle className="w-4 h-4" />,
          label: 'Failed',
        };
      case 'DELETED':
      case 'NOT_FOUND':
        return {
          color: 'text-gray-700 bg-gray-100',
          icon: <AlertCircle className="w-4 h-4" />,
          label: state === 'DELETED' ? 'Deleted' : 'Not Found',
        };
      default:
        return {
          color: 'text-gray-700 bg-gray-100',
          icon: <AlertCircle className="w-4 h-4" />,
          label: state,
        };
    }
  };

  const config = getStateConfig(state);

  return (
    <div className="flex items-center gap-2">
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.color}`}>
        {config.icon}
        {config.label}
      </span>
      
      {(state === 'CREATING' || state === 'DELETING') && progress !== undefined && (
        <div className="flex items-center gap-2">
          <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-600 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="text-xs text-gray-600">{progress}%</span>
        </div>
      )}
      
      {estimatedTime !== undefined && estimatedTime > 0 && (
        <span className="inline-flex items-center gap-1 text-xs text-gray-600">
          <Clock className="w-3 h-3" />
          ~{Math.ceil(estimatedTime / 60)}m
        </span>
      )}
    </div>
  );
}

