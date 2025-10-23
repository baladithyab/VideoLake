import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { resourcesAPI } from '../api/client';
import { RefreshCw, Plus, Trash2, Database, HardDrive, Server, Loader2 } from 'lucide-react';
import ResourceStatusBadge from '../components/ResourceStatusBadge';
import ConfirmDialog from '../components/ConfirmDialog';
import { ResourceState, ResourceStatus } from '../types/resources';

export default function ResourceManagement() {
  const queryClient = useQueryClient();
  const [showCreateMediaBucket, setShowCreateMediaBucket] = useState(false);
  const [showCreateVectorBucket, setShowCreateVectorBucket] = useState(false);
  const [showCreateOpenSearch, setShowCreateOpenSearch] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{type: 'media' | 'vector' | 'opensearch'; name: string;} | null>(null);
  const [mediaBucketName, setMediaBucketName] = useState('');
  const [vectorBucketName, setVectorBucketName] = useState('');
  const [openSearchDomainName, setOpenSearchDomainName] = useState('');

  const { data: registry, isLoading: registryLoading, refetch: refetchRegistry } = useQuery({
    queryKey: ['resource-registry'],
    queryFn: async () => {
      const response = await resourcesAPI.getRegistry();
      return response.data;
    },
  });

  const createMediaBucketMutation = useMutation({
    mutationFn: (data: { bucket_name: string }) => resourcesAPI.createMediaBucket(data),
    onSuccess: () => {
      setShowCreateMediaBucket(false);
      setMediaBucketName('');
      toast.success('Media bucket created successfully');
      refetchRegistry();
    },
  });

  const createVectorBucketMutation = useMutation({
    mutationFn: (data: { bucket_name: string }) => resourcesAPI.createVectorBucket(data),
    onSuccess: () => {
      setShowCreateVectorBucket(false);
      setVectorBucketName('');
      toast.success('Vector bucket created successfully');
      refetchRegistry();
    },
  });

  const createOpenSearchMutation = useMutation({
    mutationFn: (data: { domain_name: string }) => resourcesAPI.createOpenSearchDomain(data),
    onSuccess: () => {
      setShowCreateOpenSearch(false);
      setOpenSearchDomainName('');
      toast.success('OpenSearch domain creation started (5-10 minutes)');
      refetchRegistry();
    },
  });

  const deleteMediaBucketMutation = useMutation({
    mutationFn: (bucketName: string) => resourcesAPI.deleteMediaBucket(bucketName, false),
    onSuccess: () => {
      setDeleteConfirm(null);
      toast.success('Media bucket deleted');
      refetchRegistry();
    },
  });

  const deleteVectorBucketMutation = useMutation({
    mutationFn: (bucketName: string) => resourcesAPI.deleteVectorBucket(bucketName),
    onSuccess: () => {
      setDeleteConfirm(null);
      toast.success('Vector bucket deleted');
      refetchRegistry();
    },
  });

  const deleteOpenSearchMutation = useMutation({
    mutationFn: (domainName: string) => resourcesAPI.deleteOpenSearchDomain(domainName),
    onSuccess: () => {
      setDeleteConfirm(null);
      toast.success('OpenSearch domain deletion started');
      refetchRegistry();
    },
  });

  const handleDeleteResource = () => {
    if (!deleteConfirm) return;
    switch (deleteConfirm.type) {
      case 'media': deleteMediaBucketMutation.mutate(deleteConfirm.name); break;
      case 'vector': deleteVectorBucketMutation.mutate(deleteConfirm.name); break;
      case 'opensearch': deleteOpenSearchMutation.mutate(deleteConfirm.name); break;
    }
  };

  const mediaBuckets = registry?.registry?.s3_buckets || [];
  const vectorBuckets = registry?.registry?.vector_buckets || [];
  const openSearchDomains = registry?.registry?.opensearch_domains || [];

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Resource Management</h1>
        <p className="mt-2 text-gray-600">Manage AWS resources with lifecycle tracking</p>
      </div>

      <div className="flex gap-3 mb-6">
        <button onClick={() => refetchRegistry()} className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-md hover:bg-gray-50">
          <RefreshCw className="w-4 h-4" />Refresh
        </button>
      </div>

      {registryLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Media Buckets */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <div className="flex items-center gap-3">
                <HardDrive className="w-5 h-5 text-gray-600" />
                <h2 className="text-lg font-semibold">Media Buckets (S3)</h2>
                <span className="text-sm text-gray-500">({mediaBuckets.length})</span>
              </div>
              <button onClick={() => setShowCreateMediaBucket(true)} className="inline-flex items-center gap-2 px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700">
                <Plus className="w-4 h-4" />Create
              </button>
            </div>
            <div className="p-6">
              {mediaBuckets.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No media buckets created yet</p>
              ) : (
                <div className="space-y-3">
                  {mediaBuckets.map((bucket: any) => (
                    <div key={bucket.name} className="flex items-center justify-between p-4 border rounded-lg">
                      <div>
                        <p className="font-medium">{bucket.name}</p>
                        <p className="text-sm text-gray-500">{bucket.region}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <ResourceStatusBadge state={bucket.status === 'created' ? 'ACTIVE' : 'FAILED'} />
                        <button onClick={() => setDeleteConfirm({ type: 'media', name: bucket.name })} className="p-2 text-red-600 hover:bg-red-50 rounded-md">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Vector Buckets */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Database className="w-5 h-5 text-gray-600" />
                <h2 className="text-lg font-semibold">Vector Buckets (S3 Vectors)</h2>
                <span className="text-sm text-gray-500">({vectorBuckets.length})</span>
              </div>
              <button onClick={() => setShowCreateVectorBucket(true)} className="inline-flex items-center gap-2 px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700">
                <Plus className="w-4 h-4" />Create
              </button>
            </div>
            <div className="p-6">
              {vectorBuckets.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No vector buckets created yet</p>
              ) : (
                <div className="space-y-3">
                  {vectorBuckets.map((bucket: any) => (
                    <div key={bucket.name} className="flex items-center justify-between p-4 border rounded-lg">
                      <div>
                        <p className="font-medium">{bucket.name}</p>
                        <p className="text-sm text-gray-500">{bucket.region}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <ResourceStatusBadge state={bucket.status === 'created' ? 'ACTIVE' : 'FAILED'} />
                        <button onClick={() => setDeleteConfirm({ type: 'vector', name: bucket.name })} className="p-2 text-red-600 hover:bg-red-50 rounded-md">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* OpenSearch Domains */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Server className="w-5 h-5 text-gray-600" />
                <h2 className="text-lg font-semibold">OpenSearch Domains</h2>
                <span className="text-sm text-gray-500">({openSearchDomains.length})</span>
              </div>
              <button onClick={() => setShowCreateOpenSearch(true)} className="inline-flex items-center gap-2 px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700">
                <Plus className="w-4 h-4" />Create
              </button>
            </div>
            <div className="p-6">
              {openSearchDomains.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No OpenSearch domains created yet</p>
              ) : (
                <div className="space-y-3">
                  {openSearchDomains.map((domain: any) => (
                    <div key={domain.name} className="flex items-center justify-between p-4 border rounded-lg">
                      <div>
                        <p className="font-medium">{domain.name}</p>
                        <p className="text-sm text-gray-500">{domain.region}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <ResourceStatusBadge state="ACTIVE" />
                        <button onClick={() => setDeleteConfirm({ type: 'opensearch', name: domain.name })} className="p-2 text-red-600 hover:bg-red-50 rounded-md">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Create Dialogs */}
      {showCreateMediaBucket && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Create Media Bucket</h3>
            <input type="text" value={mediaBucketName} onChange={(e) => setMediaBucketName(e.target.value)} placeholder="Bucket name" className="w-full px-3 py-2 border rounded-md mb-4" />
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowCreateMediaBucket(false)} className="px-4 py-2 border rounded-md">Cancel</button>
              <button onClick={() => createMediaBucketMutation.mutate({ bucket_name: mediaBucketName })} disabled={!mediaBucketName || createMediaBucketMutation.isPending} className="px-4 py-2 bg-indigo-600 text-white rounded-md disabled:opacity-50">
                {createMediaBucketMutation.isPending ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showCreateVectorBucket && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Create Vector Bucket</h3>
            <input type="text" value={vectorBucketName} onChange={(e) => setVectorBucketName(e.target.value)} placeholder="Bucket name" className="w-full px-3 py-2 border rounded-md mb-4" />
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowCreateVectorBucket(false)} className="px-4 py-2 border rounded-md">Cancel</button>
              <button onClick={() => createVectorBucketMutation.mutate({ bucket_name: vectorBucketName })} disabled={!vectorBucketName || createVectorBucketMutation.isPending} className="px-4 py-2 bg-indigo-600 text-white rounded-md disabled:opacity-50">
                {createVectorBucketMutation.isPending ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showCreateOpenSearch && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Create OpenSearch Domain</h3>
            <input type="text" value={openSearchDomainName} onChange={(e) => setOpenSearchDomainName(e.target.value)} placeholder="Domain name" className="w-full px-3 py-2 border rounded-md mb-4" />
            <p className="text-sm text-gray-600 mb-4">Note: Domain creation takes 5-10 minutes</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowCreateOpenSearch(false)} className="px-4 py-2 border rounded-md">Cancel</button>
              <button onClick={() => createOpenSearchMutation.mutate({ domain_name: openSearchDomainName })} disabled={!openSearchDomainName || createOpenSearchMutation.isPending} className="px-4 py-2 bg-indigo-600 text-white rounded-md disabled:opacity-50">
                {createOpenSearchMutation.isPending ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={deleteConfirm !== null}
        onClose={() => setDeleteConfirm(null)}
        onConfirm={handleDeleteResource}
        title="Delete Resource"
        message={`Are you sure you want to delete ${deleteConfirm?.name}? This action cannot be undone.`}
        confirmText="Delete"
        isDestructive={true}
        isLoading={deleteMediaBucketMutation.isPending || deleteVectorBucketMutation.isPending || deleteOpenSearchMutation.isPending}
      />
    </div>
  );
}
