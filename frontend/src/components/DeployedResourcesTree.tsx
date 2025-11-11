import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { resourcesAPI } from '../api/client';
import {
  ChevronRight,
  ChevronDown,
  Database,
  Server,
  HardDrive,
  FolderTree,
  Loader2,
  RefreshCw,
  Globe,
  Box,
  Layers,
  Activity,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  MinusCircle,
  Clock
} from 'lucide-react';

interface TreeNode {
  type: string;
  name: string;
  status?: string;
  connectivity?: string;  // 'healthy', 'unhealthy', 'timeout', 'error', 'unavailable', 'degraded', 'not_deployed'
  children?: TreeNode[];
  arn?: string;
  region?: string;
  endpoint?: string;
  response_time_ms?: number;
  vector_count?: number;
  dimension?: number;
  metadata?: any;
  health_details?: any;
}

interface DeployedResourcesTreeData {
  shared_resources: TreeNode;
  vector_backends: TreeNode[];
}

const getConnectivityColor = (status: string): string => {
  switch (status?.toLowerCase()) {
    case 'healthy':
      return 'bg-green-50 text-green-700 border-green-200';
    case 'degraded':
      return 'bg-yellow-50 text-yellow-700 border-yellow-200';
    case 'unhealthy':
      return 'bg-red-50 text-red-700 border-red-200';
    case 'timeout':
      return 'bg-orange-50 text-orange-700 border-orange-200';
    case 'error':
      return 'bg-red-50 text-red-700 border-red-200';
    case 'unavailable':
    case 'not_deployed':
      return 'bg-gray-50 text-gray-600 border-gray-200';
    default:
      return 'bg-gray-50 text-gray-600 border-gray-200';
  }
};

const getConnectivityIcon = (status: string) => {
  switch (status?.toLowerCase()) {
    case 'healthy':
      return <CheckCircle2 className="w-3 h-3" />;
    case 'degraded':
      return <AlertTriangle className="w-3 h-3" />;
    case 'unhealthy':
    case 'error':
      return <XCircle className="w-3 h-3" />;
    case 'timeout':
      return <Clock className="w-3 h-3" />;
    case 'unavailable':
    case 'not_deployed':
      return <MinusCircle className="w-3 h-3" />;
    default:
      return null;
  }
};

const getResponseTimeColor = (ms: number): string => {
  if (ms < 200) return 'text-green-600';
  if (ms < 500) return 'text-yellow-600';
  return 'text-orange-600';
};

const getStatusColor = (status?: string) => {
  switch (status?.toLowerCase()) {
    case 'active':
    case 'healthy':
      return 'bg-green-100 text-green-800 border-green-200';
    case 'creating':
    case 'degraded':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case 'unhealthy':
    case 'error':
    case 'failed':
      return 'bg-red-100 text-red-800 border-red-200';
    case 'timeout':
    case 'unavailable':
    case 'not_deployed':
      return 'bg-gray-100 text-gray-800 border-gray-200';
    default:
      return 'bg-blue-100 text-blue-800 border-blue-200';
  }
};

const getIcon = (type: string) => {
  switch (type) {
    case 'shared':
      return <Globe className="w-4 h-4" />;
    case 's3_bucket':
      return <HardDrive className="w-4 h-4 text-blue-600" />;
    case 's3_vector':
      return <Database className="w-4 h-4 text-purple-600" />;
    case 'vector_bucket':
      return <Box className="w-4 h-4 text-purple-500" />;
    case 'vector_index':
      return <Layers className="w-4 h-4 text-purple-400" />;
    case 'opensearch':
      return <Server className="w-4 h-4 text-blue-600" />;
    case 'opensearch_domain':
      return <Server className="w-4 h-4 text-blue-500" />;
    case 'qdrant':
      return <Database className="w-4 h-4 text-green-600" />;
    case 'qdrant_collection':
      return <FolderTree className="w-4 h-4 text-green-500" />;
    case 'lancedb':
      return <Database className="w-4 h-4 text-orange-600" />;
    case 'lancedb_table':
      return <FolderTree className="w-4 h-4 text-orange-500" />;
    default:
      return <FolderTree className="w-4 h-4" />;
  }
};

interface TreeNodeItemProps {
  node: TreeNode;
  level: number;
}

const TreeNodeItem = ({ node, level }: TreeNodeItemProps) => {
  const [isExpanded, setIsExpanded] = useState(level < 2); // Auto-expand first 2 levels
  const [showHealthDetails, setShowHealthDetails] = useState(false);
  const hasChildren = node.children && node.children.length > 0;
  const indent = level * 20;
  const hasHealthDetails = node.health_details && Object.keys(node.health_details).length > 0;

  return (
    <div>
      <div
        className={`flex items-center gap-2 py-2 px-3 hover:bg-gray-50 rounded-md transition-colors ${hasChildren ? 'cursor-pointer' : ''}`}
        style={{ marginLeft: `${indent}px` }}
        onClick={() => hasChildren && setIsExpanded(!isExpanded)}
      >
        {/* Expand/Collapse Icon */}
        <div className="w-4 h-4 flex items-center justify-center">
          {hasChildren ? (
            isExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500" />
            )
          ) : (
            <div className="w-4" />
          )}
        </div>

        {/* Icon */}
        <div className="flex-shrink-0">
          {getIcon(node.type)}
        </div>

        {/* Name and Status */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-sm text-gray-900 truncate">
              {node.name}
            </span>
            
            {/* Connectivity Badge with Icon */}
            {node.connectivity && (
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${getConnectivityColor(node.connectivity)}`}>
                {getConnectivityIcon(node.connectivity)}
                {node.connectivity}
              </span>
            )}
            
            {/* Response Time */}
            {node.response_time_ms !== undefined && (
              <span className={`text-xs font-mono ${getResponseTimeColor(node.response_time_ms)}`}>
                ({node.response_time_ms.toFixed(0)}ms)
              </span>
            )}
            
            {/* Endpoint */}
            {node.endpoint && (
              <span className="text-xs text-gray-500 font-mono truncate max-w-xs" title={node.endpoint}>
                {node.endpoint}
              </span>
            )}
            
            {/* Status (if no connectivity) */}
            {node.status && !node.connectivity && (
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(node.status)}`}>
                {node.status}
              </span>
            )}
          </div>
          
          {/* Metadata */}
          <div className="flex items-center gap-3 mt-1 text-xs text-gray-500 flex-wrap">
            {node.region && (
              <span className="flex items-center gap-1">
                <Globe className="w-3 h-3" />
                {node.region}
              </span>
            )}
            {node.vector_count !== undefined && (
              <span>
                {node.vector_count.toLocaleString()} vectors
              </span>
            )}
            {node.dimension !== undefined && (
              <span>
                dim: {node.dimension}
              </span>
            )}
            {node.connectivity === 'not_deployed' && (
              <span className="text-gray-500 italic">
                Module not deployed (count=0 in Terraform)
              </span>
            )}
          </div>
          
          {/* Health Details Toggle */}
          {hasHealthDetails && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowHealthDetails(!showHealthDetails);
              }}
              className="mt-2 text-xs text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
            >
              {showHealthDetails ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              {showHealthDetails ? 'Hide' : 'Show'} health details
            </button>
          )}
          
          {/* Expandable Health Details */}
          {showHealthDetails && hasHealthDetails && (
            <div className="mt-2 p-3 bg-blue-50 rounded-md border border-blue-100">
              <div className="text-xs space-y-1">
                {Object.entries(node.health_details).map(([key, value]) => (
                  <div key={key} className="flex gap-2">
                    <span className="font-medium text-gray-700">{key}:</span>
                    <span className="text-gray-600">{JSON.stringify(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Children count badge */}
        {hasChildren && (
          <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-600">
            {node.children!.length}
          </span>
        )}
      </div>

      {/* Render children */}
      {hasChildren && isExpanded && (
        <div className="mt-1">
          {node.children!.map((child, index) => (
            <TreeNodeItem key={`${child.name}-${index}`} node={child} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  );
};

export default function DeployedResourcesTree() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['deployed-resources-tree'],
    queryFn: async () => {
      const response = await resourcesAPI.getDeployedResourcesTree();
      return response.data;
    },
    refetchInterval: 30000, // Auto-refresh every 30 seconds
  });

  const treeData: DeployedResourcesTreeData | null = data?.tree || null;

  // Calculate summary statistics
  const healthyCount = treeData?.vector_backends.filter(b => b.connectivity === 'healthy').length || 0;
  const unhealthyCount = treeData?.vector_backends.filter(b =>
    b.connectivity && !['healthy', 'not_deployed', 'unavailable'].includes(b.connectivity)
  ).length || 0;
  const notDeployedCount = treeData?.vector_backends.filter(b =>
    b.connectivity === 'not_deployed' || b.status === 'not_deployed'
  ).length || 0;
  const totalResources = (treeData?.shared_resources.children?.length || 0) +
    (treeData?.vector_backends.reduce((sum, b) => sum + (b.children?.length || 0), 0) || 0);

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FolderTree className="w-5 h-5 text-indigo-600" />
          <h2 className="text-lg font-semibold text-gray-900">Deployed Resources</h2>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div className="p-6">
        {isLoading ? (
          <div className="space-y-4">
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600 mx-auto mb-3" />
                <p className="text-sm text-gray-600">Checking connectivity and loading resources...</p>
              </div>
            </div>
          </div>
        ) : error ? (
          <div className="text-center py-12">
            <XCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
            <div className="text-red-600 mb-2 font-medium">Failed to load resources</div>
            <p className="text-sm text-gray-600 mb-4">
              {error instanceof Error ? error.message : 'Unable to fetch resource tree. Terraform state may be missing.'}
            </p>
            <button
              onClick={() => refetch()}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700"
            >
              <RefreshCw className="w-4 h-4" />
              Try again
            </button>
          </div>
        ) : !treeData || (treeData.vector_backends.length === 0 && !treeData.shared_resources.children?.length) ? (
          <div className="text-center py-12">
            <Database className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <div className="text-gray-900 font-medium mb-2">No vector backends deployed yet</div>
            <p className="text-sm text-gray-600 mb-4 max-w-md mx-auto">
              Deploy backends via the Infrastructure Dashboard or run:
            </p>
            <div className="bg-gray-100 rounded-md p-3 max-w-md mx-auto">
              <code className="text-sm text-gray-800">
                cd terraform && terraform apply -var="deploy_s3vector=true"
              </code>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Summary Statistics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold text-gray-900">{totalResources}</div>
                    <div className="text-sm text-gray-500 mt-1">Total Resources</div>
                  </div>
                  <Database className="w-8 h-8 text-gray-400" />
                </div>
              </div>
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold text-green-600">{healthyCount}</div>
                    <div className="text-sm text-gray-500 mt-1">Healthy Backends</div>
                  </div>
                  <CheckCircle2 className="w-8 h-8 text-green-500" />
                </div>
              </div>
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold text-red-600">{unhealthyCount}</div>
                    <div className="text-sm text-gray-500 mt-1">Unhealthy Backends</div>
                  </div>
                  <XCircle className="w-8 h-8 text-red-500" />
                </div>
              </div>
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold text-gray-600">{notDeployedCount}</div>
                    <div className="text-sm text-gray-500 mt-1">Not Deployed</div>
                  </div>
                  <MinusCircle className="w-8 h-8 text-gray-400" />
                </div>
              </div>
            </div>
            {/* Shared Resources */}
            <div className="bg-blue-50 rounded-lg p-4">
              <TreeNodeItem node={treeData.shared_resources} level={0} />
            </div>

            {/* Vector Backends */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3 px-3">
                Vector Store Backends
              </h3>
              <div className="space-y-2">
                {treeData.vector_backends.map((backend, index) => (
                  <div key={`${backend.name}-${index}`} className="bg-gray-50 rounded-lg p-3">
                    <TreeNodeItem node={backend} level={0} />
                  </div>
                ))}
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}