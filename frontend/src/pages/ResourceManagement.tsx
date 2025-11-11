import { useQuery } from '@tanstack/react-query';
import { resourcesAPI } from '../api/client';
import { RefreshCw } from 'lucide-react';
import DeployedResourcesTree from '../components/DeployedResourcesTree';

export default function ResourceManagement() {
  // ONLY keep the tree query
  const deployedResourcesQuery = useQuery({
    queryKey: ['deployed-resources-tree'],
    queryFn: async () => {
      const response = await resourcesAPI.getDeployedResourcesTree();
      return response.data;
    },
    refetchInterval: 30000,
  });

  return (
    <div className="container mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Deployed Resources</h1>
        <p className="mt-2 text-gray-600">
          View your Terraform-deployed infrastructure. To modify resources, use Terraform commands.
        </p>
      </div>

      {/* Info Banner */}
      <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-blue-800 mb-2">
          Resources are managed via Terraform. To deploy or modify infrastructure:
        </p>
        <code className="block bg-blue-100 p-2 rounded font-mono text-sm">
          cd terraform && terraform apply
        </code>
        <p className="mt-2 text-blue-800 text-sm">
          Or use the <a href="/infrastructure" className="underline hover:text-blue-900">Infrastructure Dashboard</a> for deployment.
        </p>
      </div>

      {/* Refresh Button */}
      <div className="flex gap-3 mb-6">
        <button
          onClick={() => deployedResourcesQuery.refetch()}
          disabled={deployedResourcesQuery.isRefetching}
          className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${deployedResourcesQuery.isRefetching ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Error State */}
      {deployedResourcesQuery.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">
            Error loading resources: {(deployedResourcesQuery.error as any).message || 'Unknown error'}
          </p>
        </div>
      )}

      {/* No Tfstate State */}
      {deployedResourcesQuery.data && !deployedResourcesQuery.data.success && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <p className="text-yellow-800">
            {deployedResourcesQuery.data.message || 'No Terraform state found'}
          </p>
          <p className="text-yellow-700 text-sm mt-2">
            Initialize and apply your Terraform configuration to deploy resources.
          </p>
        </div>
      )}

      {/* Loading State */}
      {deployedResourcesQuery.isLoading && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-gray-400 mx-auto mb-2" />
          <p className="text-gray-600">Loading deployed resources...</p>
        </div>
      )}

      {/* Deployed Resources Tree */}
      {!deployedResourcesQuery.isLoading && (
        <DeployedResourcesTree />
      )}
    </div>
  );
}
