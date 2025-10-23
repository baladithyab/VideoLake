import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { resourcesAPI } from '../api/client';
import { RefreshCw, Plus, Trash2, Database, HardDrive, Server, Loader2, CheckSquare, Square } from 'lucide-react';
import ResourceStatusBadge from '../components/ResourceStatusBadge';
import ConfirmDialog from '../components/ConfirmDialog';

type ResourceState = 'CREATING' | 'ACTIVE' | 'AVAILABLE' | 'DELETING' | 'DELETED' | 'FAILED' | 'NOT_FOUND';

interface ResourceStatus {
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

export default function ResourceManagement() {
  const queryClient = useQueryClient();

  // Create dialogs
  const [showCreateMediaBucket, setShowCreateMediaBucket] = useState(false);
  const [showCreateVectorBucket, setShowCreateVectorBucket] = useState(false);
  const [showCreateOpenSearch, setShowCreateOpenSearch] = useState(false);

  // Stack creation dialog
  const [showCreateStack, setShowCreateStack] = useState(false);

  // Batch create dialogs
  const [showBatchCreateMedia, setShowBatchCreateMedia] = useState(false);
  const [showBatchCreateVector, setShowBatchCreateVector] = useState(false);
  const [showBatchCreateOpenSearch, setShowBatchCreateOpenSearch] = useState(false);

  // Delete confirmation
  const [deleteConfirm, setDeleteConfirm] = useState<{type: 'media' | 'vector' | 'opensearch'; name: string;} | null>(null);
  const [batchDeleteConfirm, setBatchDeleteConfirm] = useState<{type: 'media' | 'vector' | 'opensearch'; names: string[];} | null>(null);

  // Form inputs
  const [mediaBucketName, setMediaBucketName] = useState('');
  const [vectorBucketName, setVectorBucketName] = useState('');
  const [openSearchDomainName, setOpenSearchDomainName] = useState('');
  const [batchMediaNames, setBatchMediaNames] = useState('');
  const [batchVectorNames, setBatchVectorNames] = useState('');
  const [batchOpenSearchNames, setBatchOpenSearchNames] = useState('');

  // Stack creation form
  const [stackProjectName, setStackProjectName] = useState('');
  const [stackCreateVector, setStackCreateVector] = useState(true);
  const [stackCreateMedia, setStackCreateMedia] = useState(true);
  const [stackCreateOpenSearch, setStackCreateOpenSearch] = useState(true);

  // Checkbox selections for deletion
  const [selectedMediaBuckets, setSelectedMediaBuckets] = useState<Set<string>>(new Set());
  const [selectedVectorBuckets, setSelectedVectorBuckets] = useState<Set<string>>(new Set());
  const [selectedOpenSearchDomains, setSelectedOpenSearchDomains] = useState<Set<string>>(new Set());

  const { data: registry, isLoading: registryLoading, refetch: refetchRegistry } = useQuery({
    queryKey: ['resource-registry'],
    queryFn: async () => {
      const response = await resourcesAPI.getRegistry();
      return response.data;
    },
    refetchInterval: 3000, // Auto-refresh every 3 seconds to catch deletions
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

  // Batch create mutations
  const batchCreateMediaMutation = useMutation({
    mutationFn: (data: { bucket_names: string[] }) => resourcesAPI.batchCreateMediaBuckets(data),
    onSuccess: (response) => {
      setShowBatchCreateMedia(false);
      setBatchMediaNames('');
      toast.success(`Created ${response.data.successful}/${response.data.total} media buckets`);
      refetchRegistry();
    },
  });

  const batchCreateVectorMutation = useMutation({
    mutationFn: (data: { bucket_names: string[] }) => resourcesAPI.batchCreateVectorBuckets(data),
    onSuccess: (response) => {
      setShowBatchCreateVector(false);
      setBatchVectorNames('');
      toast.success(`Created ${response.data.successful}/${response.data.total} vector buckets`);
      refetchRegistry();
    },
  });

  const batchCreateOpenSearchMutation = useMutation({
    mutationFn: (data: { domain_names: string[] }) => resourcesAPI.batchCreateOpenSearchDomains(data),
    onSuccess: (response) => {
      setShowBatchCreateOpenSearch(false);
      setBatchOpenSearchNames('');
      toast.success(`Started creation of ${response.data.successful}/${response.data.total} OpenSearch domains`);
      refetchRegistry();
    },
  });

  // Batch delete mutation
  const batchDeleteMutation = useMutation({
    mutationFn: (data: { resource_type: string; resource_names: string[]; force?: boolean }) =>
      resourcesAPI.batchDelete(data),
    onSuccess: (response) => {
      setBatchDeleteConfirm(null);
      setSelectedMediaBuckets(new Set());
      setSelectedVectorBuckets(new Set());
      setSelectedOpenSearchDomains(new Set());
      toast.success(`Deleted ${response.data.successful}/${response.data.total} resources`);
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

  const handleBatchDelete = () => {
    if (!batchDeleteConfirm) return;
    batchDeleteMutation.mutate({
      resource_type: batchDeleteConfirm.type,
      resource_names: batchDeleteConfirm.names,
      force: false
    });
  };

  const createStackMutation = useMutation({
    mutationFn: (data: {
      project_name: string;
      create_vector_bucket?: boolean;
      create_media_bucket?: boolean;
      create_opensearch_domain?: boolean;
    }) => resourcesAPI.createStack(data),
    onSuccess: (response) => {
      setShowCreateStack(false);
      setStackProjectName('');
      setStackCreateVector(true);
      setStackCreateMedia(true);
      setStackCreateOpenSearch(true);
      const data = response.data;
      toast.success(`Created ${data.created_count} resource(s) for project "${data.project_name}"`);
      if (data.failed_count > 0) {
        toast.error(`Failed to create ${data.failed_count} resource(s)`);
      }
      refetchRegistry();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create stack');
    },
  });

  // Checkbox toggle helpers
  const toggleMediaBucket = (name: string) => {
    const newSet = new Set(selectedMediaBuckets);
    if (newSet.has(name)) {
      newSet.delete(name);
    } else {
      newSet.add(name);
    }
    setSelectedMediaBuckets(newSet);
  };

  const toggleVectorBucket = (name: string) => {
    const newSet = new Set(selectedVectorBuckets);
    if (newSet.has(name)) {
      newSet.delete(name);
    } else {
      newSet.add(name);
    }
    setSelectedVectorBuckets(newSet);
  };

  const toggleOpenSearchDomain = (name: string) => {
    const newSet = new Set(selectedOpenSearchDomains);
    if (newSet.has(name)) {
      newSet.delete(name);
    } else {
      newSet.add(name);
    }
    setSelectedOpenSearchDomains(newSet);
  };

  const toggleAllMedia = () => {
    if (selectedMediaBuckets.size === mediaBuckets.length) {
      setSelectedMediaBuckets(new Set());
    } else {
      setSelectedMediaBuckets(new Set(mediaBuckets.map((b: any) => b.name)));
    }
  };

  const toggleAllVector = () => {
    if (selectedVectorBuckets.size === vectorBuckets.length) {
      setSelectedVectorBuckets(new Set());
    } else {
      setSelectedVectorBuckets(new Set(vectorBuckets.map((b: any) => b.name)));
    }
  };

  const toggleAllOpenSearch = () => {
    if (selectedOpenSearchDomains.size === openSearchDomains.length) {
      setSelectedOpenSearchDomains(new Set());
    } else {
      setSelectedOpenSearchDomains(new Set(openSearchDomains.map((d: any) => d.name)));
    }
  };

  // Template selection helpers
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
        <button
          onClick={() => setShowCreateStack(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-md hover:from-indigo-700 hover:to-purple-700 shadow-md"
        >
          <Plus className="w-5 h-5" />Create Complete Stack
        </button>
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
                {selectedMediaBuckets.size > 0 && (
                  <span className="text-sm text-indigo-600 font-medium">
                    {selectedMediaBuckets.size} selected
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                {selectedMediaBuckets.size > 0 && (
                  <button
                    onClick={() => setBatchDeleteConfirm({ type: 'media', names: Array.from(selectedMediaBuckets) })}
                    className="inline-flex items-center gap-2 px-3 py-1.5 bg-red-600 text-white text-sm rounded-md hover:bg-red-700"
                  >
                    <Trash2 className="w-4 h-4" />Delete Selected ({selectedMediaBuckets.size})
                  </button>
                )}
                <button onClick={() => setShowBatchCreateMedia(true)} className="inline-flex items-center gap-2 px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700">
                  <Plus className="w-4 h-4" />Batch Create
                </button>
                <button onClick={() => setShowCreateMediaBucket(true)} className="inline-flex items-center gap-2 px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700">
                  <Plus className="w-4 h-4" />Create
                </button>
              </div>
            </div>
            <div className="p-6">
              {mediaBuckets.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No media buckets created yet</p>
              ) : (
                <div className="space-y-3">
                  {mediaBuckets.length > 0 && (
                    <div className="flex items-center gap-2 pb-2 border-b">
                      <button onClick={toggleAllMedia} className="p-1 hover:bg-gray-100 rounded">
                        {selectedMediaBuckets.size === mediaBuckets.length ? (
                          <CheckSquare className="w-5 h-5 text-indigo-600" />
                        ) : (
                          <Square className="w-5 h-5 text-gray-400" />
                        )}
                      </button>
                      <span className="text-sm text-gray-600">Select All</span>
                    </div>
                  )}
                  {mediaBuckets.map((bucket: any) => (
                    <div key={bucket.name} className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50">
                      <button onClick={() => toggleMediaBucket(bucket.name)} className="p-1">
                        {selectedMediaBuckets.has(bucket.name) ? (
                          <CheckSquare className="w-5 h-5 text-indigo-600" />
                        ) : (
                          <Square className="w-5 h-5 text-gray-400" />
                        )}
                      </button>
                      <div className="flex-1">
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
                {selectedVectorBuckets.size > 0 && (
                  <span className="text-sm text-indigo-600 font-medium">
                    {selectedVectorBuckets.size} selected
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                {selectedVectorBuckets.size > 0 && (
                  <button
                    onClick={() => setBatchDeleteConfirm({ type: 'vector', names: Array.from(selectedVectorBuckets) })}
                    className="inline-flex items-center gap-2 px-3 py-1.5 bg-red-600 text-white text-sm rounded-md hover:bg-red-700"
                  >
                    <Trash2 className="w-4 h-4" />Delete Selected ({selectedVectorBuckets.size})
                  </button>
                )}
                <button onClick={() => setShowBatchCreateVector(true)} className="inline-flex items-center gap-2 px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700">
                  <Plus className="w-4 h-4" />Batch Create
                </button>
                <button onClick={() => setShowCreateVectorBucket(true)} className="inline-flex items-center gap-2 px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700">
                  <Plus className="w-4 h-4" />Create
                </button>
              </div>
            </div>
            <div className="p-6">
              {vectorBuckets.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No vector buckets created yet</p>
              ) : (
                <div className="space-y-3">
                  {vectorBuckets.length > 0 && (
                    <div className="flex items-center gap-2 pb-2 border-b">
                      <button onClick={toggleAllVector} className="p-1 hover:bg-gray-100 rounded">
                        {selectedVectorBuckets.size === vectorBuckets.length ? (
                          <CheckSquare className="w-5 h-5 text-indigo-600" />
                        ) : (
                          <Square className="w-5 h-5 text-gray-400" />
                        )}
                      </button>
                      <span className="text-sm text-gray-600">Select All</span>
                    </div>
                  )}
                  {vectorBuckets.map((bucket: any) => (
                    <div key={bucket.name} className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50">
                      <button onClick={() => toggleVectorBucket(bucket.name)} className="p-1">
                        {selectedVectorBuckets.has(bucket.name) ? (
                          <CheckSquare className="w-5 h-5 text-indigo-600" />
                        ) : (
                          <Square className="w-5 h-5 text-gray-400" />
                        )}
                      </button>
                      <div className="flex-1">
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
                {selectedOpenSearchDomains.size > 0 && (
                  <span className="text-sm text-indigo-600 font-medium">
                    {selectedOpenSearchDomains.size} selected
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                {selectedOpenSearchDomains.size > 0 && (
                  <button
                    onClick={() => setBatchDeleteConfirm({ type: 'opensearch', names: Array.from(selectedOpenSearchDomains) })}
                    className="inline-flex items-center gap-2 px-3 py-1.5 bg-red-600 text-white text-sm rounded-md hover:bg-red-700"
                  >
                    <Trash2 className="w-4 h-4" />Delete Selected ({selectedOpenSearchDomains.size})
                  </button>
                )}
                <button onClick={() => setShowBatchCreateOpenSearch(true)} className="inline-flex items-center gap-2 px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700">
                  <Plus className="w-4 h-4" />Batch Create
                </button>
                <button onClick={() => setShowCreateOpenSearch(true)} className="inline-flex items-center gap-2 px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700">
                  <Plus className="w-4 h-4" />Create
                </button>
              </div>
            </div>
            <div className="p-6">
              {openSearchDomains.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No OpenSearch domains created yet</p>
              ) : (
                <div className="space-y-3">
                  {openSearchDomains.length > 0 && (
                    <div className="flex items-center gap-2 pb-2 border-b">
                      <button onClick={toggleAllOpenSearch} className="p-1 hover:bg-gray-100 rounded">
                        {selectedOpenSearchDomains.size === openSearchDomains.length ? (
                          <CheckSquare className="w-5 h-5 text-indigo-600" />
                        ) : (
                          <Square className="w-5 h-5 text-gray-400" />
                        )}
                      </button>
                      <span className="text-sm text-gray-600">Select All</span>
                    </div>
                  )}
                  {openSearchDomains.map((domain: any) => (
                    <div key={domain.name} className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50">
                      <button onClick={() => toggleOpenSearchDomain(domain.name)} className="p-1">
                        {selectedOpenSearchDomains.has(domain.name) ? (
                          <CheckSquare className="w-5 h-5 text-indigo-600" />
                        ) : (
                          <Square className="w-5 h-5 text-gray-400" />
                        )}
                      </button>
                      <div className="flex-1">
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

      {/* Create Complete Stack Dialog */}
      {showCreateStack && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4 bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
              Create Complete S3Vector Stack
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Create a coordinated set of resources with consistent naming for your project.
            </p>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Project Name
              </label>
              <input
                type="text"
                value={stackProjectName}
                onChange={(e) => setStackProjectName(e.target.value)}
                placeholder="my-project"
                className="w-full px-3 py-2 border rounded-md"
              />
              <p className="text-xs text-gray-500 mt-1">
                Resources will be named: {stackProjectName || 'project-name'}-vector-bucket, {stackProjectName || 'project-name'}-media-bucket, {stackProjectName || 'project-name'}-os
              </p>
              {stackProjectName && stackProjectName.length > 25 && (
                <p className="text-xs text-red-600 mt-1">
                  ⚠️ Project name too long ({stackProjectName.length} chars). Must be ≤25 characters for OpenSearch domain (AWS limit: 28 chars total).
                </p>
              )}
            </div>

            <div className="mb-4 space-y-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Components to Create
              </label>

              <div className="flex items-center gap-3 p-3 border rounded-lg hover:bg-gray-50 cursor-pointer" onClick={() => setStackCreateVector(!stackCreateVector)}>
                <button className="mt-0.5">
                  {stackCreateVector ? (
                    <CheckSquare className="w-5 h-5 text-indigo-600" />
                  ) : (
                    <Square className="w-5 h-5 text-gray-400" />
                  )}
                </button>
                <div className="flex-1">
                  <p className="font-medium text-sm">S3 Vector Bucket</p>
                  <p className="text-xs text-gray-500">Store vector embeddings with S3 Vectors</p>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 border rounded-lg hover:bg-gray-50 cursor-pointer" onClick={() => setStackCreateMedia(!stackCreateMedia)}>
                <button className="mt-0.5">
                  {stackCreateMedia ? (
                    <CheckSquare className="w-5 h-5 text-indigo-600" />
                  ) : (
                    <Square className="w-5 h-5 text-gray-400" />
                  )}
                </button>
                <div className="flex-1">
                  <p className="font-medium text-sm">S3 Media Bucket</p>
                  <p className="text-xs text-gray-500">Store media files and data</p>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 border rounded-lg hover:bg-gray-50 cursor-pointer" onClick={() => setStackCreateOpenSearch(!stackCreateOpenSearch)}>
                <button className="mt-0.5">
                  {stackCreateOpenSearch ? (
                    <CheckSquare className="w-5 h-5 text-indigo-600" />
                  ) : (
                    <Square className="w-5 h-5 text-gray-400" />
                  )}
                </button>
                <div className="flex-1">
                  <p className="font-medium text-sm">OpenSearch Domain</p>
                  <p className="text-xs text-gray-500">Hybrid search with OpenSearch (takes 5-10 min)</p>
                </div>
              </div>
            </div>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowCreateStack(false);
                  setStackProjectName('');
                  setStackCreateVector(true);
                  setStackCreateMedia(true);
                  setStackCreateOpenSearch(true);
                }}
                className="px-4 py-2 border rounded-md"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (stackProjectName.trim()) {
                    createStackMutation.mutate({
                      project_name: stackProjectName.trim(),
                      create_vector_bucket: stackCreateVector,
                      create_media_bucket: stackCreateMedia,
                      create_opensearch_domain: stackCreateOpenSearch,
                    });
                  }
                }}
                disabled={
                  !stackProjectName.trim() ||
                  (!stackCreateVector && !stackCreateMedia && !stackCreateOpenSearch) ||
                  (stackCreateOpenSearch && stackProjectName.length > 25) ||
                  createStackMutation.isPending
                }
                className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-md disabled:opacity-50"
                title={
                  stackCreateOpenSearch && stackProjectName.length > 25
                    ? 'Project name too long for OpenSearch domain (max 25 chars)'
                    : ''
                }
              >
                {createStackMutation.isPending ? 'Creating...' : 'Create Stack'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Batch Create Media Buckets Dialog */}
      {showBatchCreateMedia && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Batch Create Media Buckets</h3>
            <textarea
              value={batchMediaNames}
              onChange={(e) => setBatchMediaNames(e.target.value)}
              placeholder="Enter bucket names (one per line)"
              className="w-full px-3 py-2 border rounded-md mb-2 h-32 font-mono text-sm"
            />
            <p className="text-xs text-gray-500 mb-4">Enter one bucket name per line</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowBatchCreateMedia(false)} className="px-4 py-2 border rounded-md">Cancel</button>
              <button
                onClick={() => {
                  const names = batchMediaNames.split('\n').map(n => n.trim()).filter(n => n);
                  if (names.length > 0) {
                    batchCreateMediaMutation.mutate({ bucket_names: names });
                  }
                }}
                disabled={!batchMediaNames.trim() || batchCreateMediaMutation.isPending}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md disabled:opacity-50"
              >
                {batchCreateMediaMutation.isPending ? 'Creating...' : `Create ${batchMediaNames.split('\n').filter(n => n.trim()).length} Buckets`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Batch Create Vector Buckets Dialog */}
      {showBatchCreateVector && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Batch Create Vector Buckets</h3>
            <textarea
              value={batchVectorNames}
              onChange={(e) => setBatchVectorNames(e.target.value)}
              placeholder="Enter bucket names (one per line)"
              className="w-full px-3 py-2 border rounded-md mb-2 h-32 font-mono text-sm"
            />
            <p className="text-xs text-gray-500 mb-4">Enter one bucket name per line</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowBatchCreateVector(false)} className="px-4 py-2 border rounded-md">Cancel</button>
              <button
                onClick={() => {
                  const names = batchVectorNames.split('\n').map(n => n.trim()).filter(n => n);
                  if (names.length > 0) {
                    batchCreateVectorMutation.mutate({ bucket_names: names });
                  }
                }}
                disabled={!batchVectorNames.trim() || batchCreateVectorMutation.isPending}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md disabled:opacity-50"
              >
                {batchCreateVectorMutation.isPending ? 'Creating...' : `Create ${batchVectorNames.split('\n').filter(n => n.trim()).length} Buckets`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Batch Create OpenSearch Domains Dialog */}
      {showBatchCreateOpenSearch && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Batch Create OpenSearch Domains</h3>
            <textarea
              value={batchOpenSearchNames}
              onChange={(e) => setBatchOpenSearchNames(e.target.value)}
              placeholder="Enter domain names (one per line)"
              className="w-full px-3 py-2 border rounded-md mb-2 h-32 font-mono text-sm"
            />
            <p className="text-xs text-gray-500 mb-2">Enter one domain name per line</p>
            <p className="text-sm text-gray-600 mb-4">Note: Each domain takes 5-10 minutes to create</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowBatchCreateOpenSearch(false)} className="px-4 py-2 border rounded-md">Cancel</button>
              <button
                onClick={() => {
                  const names = batchOpenSearchNames.split('\n').map(n => n.trim()).filter(n => n);
                  if (names.length > 0) {
                    batchCreateOpenSearchMutation.mutate({ domain_names: names });
                  }
                }}
                disabled={!batchOpenSearchNames.trim() || batchCreateOpenSearchMutation.isPending}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md disabled:opacity-50"
              >
                {batchCreateOpenSearchMutation.isPending ? 'Creating...' : `Create ${batchOpenSearchNames.split('\n').filter(n => n.trim()).length} Domains`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Single Delete Confirmation */}
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

      {/* Batch Delete Confirmation */}
      <ConfirmDialog
        isOpen={batchDeleteConfirm !== null}
        onClose={() => setBatchDeleteConfirm(null)}
        onConfirm={handleBatchDelete}
        title="Delete Multiple Resources"
        message={`Are you sure you want to delete ${batchDeleteConfirm?.names.length} ${batchDeleteConfirm?.type} resource(s)? This action cannot be undone.`}
        confirmText={`Delete ${batchDeleteConfirm?.names.length || 0} Resources`}
        isDestructive={true}
        isLoading={batchDeleteMutation.isPending}
      />
    </div>
  );
}
