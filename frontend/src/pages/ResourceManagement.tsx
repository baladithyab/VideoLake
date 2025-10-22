import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { resourcesAPI } from '../api/client';
import { RefreshCw, Plus, Trash2, Database, HardDrive } from 'lucide-react';

export default function ResourceManagement() {
  const queryClient = useQueryClient();
  const [showCreateBucket, setShowCreateBucket] = useState(false);
  const [showCreateIndex, setShowCreateIndex] = useState(false);
  const [bucketName, setBucketName] = useState('');
  const [indexName, setIndexName] = useState('');
  const [dimension, setDimension] = useState(1024);

  // Queries
  const { data: registry, isLoading: registryLoading, refetch: refetchRegistry } = useQuery({
    queryKey: ['resource-registry'],
    queryFn: async () => {
      const response = await resourcesAPI.getRegistry();
      return response.data;
    },
  });

  const { data: activeResources } = useQuery({
    queryKey: ['active-resources'],
    queryFn: async () => {
      const response = await resourcesAPI.getActive();
      return response.data;
    },
  });

  // Mutations
  const createBucketMutation = useMutation({
    mutationFn: (data: { bucket_name: string }) => resourcesAPI.createVectorBucket(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resource-registry'] });
      setShowCreateBucket(false);
      setBucketName('');
    },
  });

  const createIndexMutation = useMutation({
    mutationFn: (data: { bucket_name: string; index_name: string; dimension: number }) =>
      resourcesAPI.createVectorIndex(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resource-registry'] });
      setShowCreateIndex(false);
      setIndexName('');
    },
  });

  const scanMutation = useMutation({
    mutationFn: () => resourcesAPI.scan(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resource-registry'] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Resource Management</h1>
          <p className="mt-2 text-sm text-gray-600">
            Manage AWS resources, create new resources, and monitor status
          </p>
        </div>
        <button
          onClick={() => scanMutation.mutate()}
          disabled={scanMutation.isPending}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
        >
          <RefreshCw className={`-ml-1 mr-2 h-5 w-5 ${scanMutation.isPending ? 'animate-spin' : ''}`} />
          Scan Resources
        </button>
      </div>

      {/* Resource Summary */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Database className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Vector Buckets</dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {registry?.summary?.vector_buckets || 0}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <HardDrive className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Vector Indexes</dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {registry?.summary?.indexes || 0}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Database className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">OpenSearch Domains</dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {registry?.summary?.opensearch_domains || 0}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <HardDrive className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">OpenSearch Collections</dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {registry?.summary?.opensearch_collections || 0}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Active Resources */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">Active Resources</h3>
          <div className="mt-4 space-y-3">
            {activeResources?.active_resources?.vector_bucket ? (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Vector Bucket:</span>
                <span className="text-sm font-medium text-green-600">
                  {activeResources.active_resources.vector_bucket}
                </span>
              </div>
            ) : (
              <div className="text-sm text-gray-500">No active vector bucket</div>
            )}
            {activeResources?.active_resources?.opensearch_domain ? (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">OpenSearch Domain:</span>
                <span className="text-sm font-medium text-green-600">
                  {activeResources.active_resources.opensearch_domain}
                </span>
              </div>
            ) : (
              <div className="text-sm text-gray-500">No active OpenSearch domain</div>
            )}
          </div>
        </div>
      </div>

      {/* Create Resources */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">Create Resources</h3>
          <div className="space-y-4">
            <div>
              <button
                onClick={() => setShowCreateBucket(!showCreateBucket)}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                <Plus className="-ml-1 mr-2 h-5 w-5" />
                Create Vector Bucket
              </button>
              {showCreateBucket && (
                <div className="mt-4 p-4 border border-gray-200 rounded-md">
                  <input
                    type="text"
                    value={bucketName}
                    onChange={(e) => setBucketName(e.target.value)}
                    placeholder="Bucket name"
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  />
                  <button
                    onClick={() => createBucketMutation.mutate({ bucket_name: bucketName })}
                    disabled={!bucketName || createBucketMutation.isPending}
                    className="mt-2 inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                  >
                    Create
                  </button>
                </div>
              )}
            </div>

            <div>
              <button
                onClick={() => setShowCreateIndex(!showCreateIndex)}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                <Plus className="-ml-1 mr-2 h-5 w-5" />
                Create Vector Index
              </button>
              {showCreateIndex && (
                <div className="mt-4 p-4 border border-gray-200 rounded-md space-y-3">
                  <input
                    type="text"
                    value={bucketName}
                    onChange={(e) => setBucketName(e.target.value)}
                    placeholder="Bucket name"
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  />
                  <input
                    type="text"
                    value={indexName}
                    onChange={(e) => setIndexName(e.target.value)}
                    placeholder="Index name"
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  />
                  <input
                    type="number"
                    value={dimension}
                    onChange={(e) => setDimension(parseInt(e.target.value))}
                    placeholder="Dimension"
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  />
                  <button
                    onClick={() =>
                      createIndexMutation.mutate({ bucket_name: bucketName, index_name: indexName, dimension })
                    }
                    disabled={!bucketName || !indexName || createIndexMutation.isPending}
                    className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                  >
                    Create
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

