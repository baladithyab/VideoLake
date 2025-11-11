import { useState, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { processingAPI, resourcesAPI } from '../api/client';
import { Upload, Film, Play, Video, CheckCircle, XCircle, Clock, Loader2, Database } from 'lucide-react';
import toast from 'react-hot-toast';

interface SampleVideo {
  id: string;
  title: string;
  description: string;
  sources: string[];
  subtitle: string;
  thumb: string;
}

interface ProcessingSettings {
  embeddingModel: 'bedrock-titan' | 'twelvelabs-marengo' | 'amazon-nova';
  vectorTypes: string[];  // For Marengo: which embeddings to generate
  novaDimension?: 1024 | 3072 | 384 | 256;  // For Nova: embedding dimension
  novaMode?: 'AUDIO_VIDEO_COMBINED' | 'AUDIO_ONLY' | 'VIDEO_ONLY';  // For Nova
  segmentDuration: number;
  quality: 'standard' | 'high' | 'maximum';
  batchProcessing: boolean;
  storeInS3Vectors: boolean;
  storeInOpenSearch: boolean;
  storeInQdrant: boolean;
  storeInLanceDB: boolean;
  lancedbBackend?: 's3' | 'efs' | 'ebs';  // LanceDB backend choice
}

export default function MediaProcessing() {
  const [activeTab, setActiveTab] = useState<'samples' | 'upload' | 's3uri'>('samples');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [s3Uri, setS3Uri] = useState('');
  const [selectedSampleVideos, setSelectedSampleVideos] = useState<Set<string>>(new Set());

  const [settings, setSettings] = useState<ProcessingSettings>({
    embeddingModel: 'twelvelabs-marengo',
    vectorTypes: ['visual-text', 'visual-image', 'audio'],
    novaDimension: 1024,
    novaMode: 'AUDIO_VIDEO_COMBINED',
    segmentDuration: 5,
    quality: 'standard',
    batchProcessing: false,
    storeInS3Vectors: true,
    storeInOpenSearch: true,
    storeInQdrant: false,
    storeInLanceDB: false,
    lancedbBackend: 's3',
  });

  // State for embedding storage
  const [selectedBucket, setSelectedBucket] = useState<string>('');
  const [selectedIndexArn, setSelectedIndexArn] = useState<string>('');
  const [selectedBackends, setSelectedBackends] = useState<string[]>(['s3_vector']);
  const [storageResults, setStorageResults] = useState<Record<string, any> | null>(null);
  const [completedJobId, setCompletedJobId] = useState<string | null>(null);

  // Fetch sample videos
  const { data: sampleVideosData } = useQuery({
    queryKey: ['sample-videos'],
    queryFn: async () => {
      const response = await processingAPI.getSampleVideos();
      return response.data;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => processingAPI.uploadVideo(file),
    onSuccess: (result) => {
      if (result.data.success) {
        setS3Uri(result.data.s3_uri);
        toast.success(`Uploaded: ${result.data.filename}`);
      }
    },
    onError: (error: any) => {
      toast.error(`Upload failed: ${error.message}`);
    },
  });

  const processMutation = useMutation({
    mutationFn: (data: { video_s3_uri: string; embedding_options?: string[] }) =>
      processingAPI.processVideo(data),
    onSuccess: () => {
      toast.success('Processing started!');
    },
    onError: (error: any) => {
      toast.error(`Processing failed: ${error.message}`);
    },
  });

  const { data: jobs, refetch: refetchJobs } = useQuery({
    queryKey: ['processing-jobs'],
    queryFn: async () => {
      const response = await processingAPI.listJobs();
      return response.data;
    },
    refetchInterval: 3000, // Poll every 3 seconds
  });

  // Fetch vector buckets for index selection
  const { data: registry } = useQuery({
    queryKey: ['resource-registry'],
    queryFn: async () => {
      const response = await resourcesAPI.getRegistry();
      return response.data;
    },
  });

  // Fetch indexes for selected bucket
  const { data: indexesData, refetch: refetchIndexes } = useQuery({
    queryKey: ['vector-indexes', selectedBucket],
    queryFn: async () => {
      if (!selectedBucket) return null;
      const response = await resourcesAPI.listVectorIndexes(selectedBucket);
      return response.data;
    },
    enabled: !!selectedBucket,
  });

  // Watch for completed jobs and auto-select first vector bucket
  useEffect(() => {
    if (jobs?.jobs) {
      const completedJob = jobs.jobs.find((j: any) => j.status === 'completed');
      if (completedJob && completedJob.job_id !== completedJobId) {
        setCompletedJobId(completedJob.job_id);
        setStorageResults(null); // Reset storage results for new job
        
        // Auto-select first vector bucket if available
        const buckets = registry?.registry?.vector_buckets || [];
        if (buckets.length > 0 && !selectedBucket) {
          setSelectedBucket(buckets[0].name);
        }
      }
    }
  }, [jobs, registry, completedJobId, selectedBucket]);

  const handleMultipleFileUpload = async () => {
    if (selectedFiles.length === 0) return;

    for (const file of selectedFiles) {
      try {
        await uploadMutation.mutateAsync(file);
      } catch (error) {
        console.error(`Failed to upload ${file.name}:`, error);
      }
    }
  };

  const handleProcess = () => {
    if (!s3Uri) return;
    processMutation.mutate({
      video_s3_uri: s3Uri,
      embedding_options: settings.vectorTypes,
    });
  };

  const handleProcessSampleVideos = async () => {
    if (selectedSampleVideos.size === 0) {
      toast.error('Please select at least one video');
      return;
    }

    const videos = sampleVideosData?.categories[0]?.videos || [];
    const selectedVideos = videos.filter((v: SampleVideo) => selectedSampleVideos.has(v.id));

    toast.success(`Starting processing for ${selectedVideos.length} video(s)...`);

    for (let i = 0; i < selectedVideos.length; i++) {
      const video = selectedVideos[i];
      try {
        await processMutation.mutateAsync({
          video_s3_uri: video.sources[0],
          embedding_options: settings.vectorTypes,
        });

        // Add delay between requests to avoid throttling (except for last video)
        if (i < selectedVideos.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 2000)); // 2 second delay
        }
      } catch (error: any) {
        console.error(`Failed to process ${video.title}:`, error);
        toast.error(`Failed to process ${video.title}: ${error.message || 'Unknown error'}`);
      }
    }
  };

  const toggleSampleVideo = (videoId: string) => {
    const newSelected = new Set(selectedSampleVideos);
    if (newSelected.has(videoId)) {
      newSelected.delete(videoId);
    } else {
      newSelected.add(videoId);
    }
    setSelectedSampleVideos(newSelected);
  };

  const toggleVectorType = (vectorType: string) => {
    const newTypes = settings.vectorTypes.includes(vectorType)
      ? settings.vectorTypes.filter(t => t !== vectorType)
      : [...settings.vectorTypes, vectorType];
    setSettings({ ...settings, vectorTypes: newTypes });
  };

  const toggleBackend = (backend: string) => {
    setSelectedBackends(prev =>
      prev.includes(backend)
        ? prev.filter(b => b !== backend)
        : [...prev, backend]
    );
  };

  const storeEmbeddingsMutation = useMutation({
    mutationFn: async (data: { job_id: string; index_arn: string; backend: string }) =>
      resourcesAPI.storeEmbeddingsToIndex(data),
  });

  const handleStoreEmbeddings = async () => {
    if (!completedJobId || !selectedIndexArn || selectedBackends.length === 0) {
      toast.error('Please select an index and at least one backend');
      return;
    }

    const results: Record<string, any> = {};
    
    for (const backend of selectedBackends) {
      try {
        toast.loading(`Storing to ${backend}...`, { id: backend });
        const response = await storeEmbeddingsMutation.mutateAsync({
          job_id: completedJobId,
          index_arn: selectedIndexArn,
          backend: backend,
        });
        
        results[backend] = {
          success: true,
          vectors_stored: response.data.stored_count || 0,
          message: response.data.message,
        };
        toast.success(`Stored to ${backend}!`, { id: backend });
      } catch (error: any) {
        results[backend] = {
          success: false,
          error: error.response?.data?.detail || error.message,
        };
        toast.error(`Failed to store to ${backend}: ${error.response?.data?.detail || error.message}`, { id: backend });
      }
    }

    setStorageResults(results);
  };

  const sampleVideos = sampleVideosData?.categories[0]?.videos || [];
  const vectorBuckets = registry?.registry?.vector_buckets || [];
  const availableIndexes = indexesData?.indexes || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">🎬 Media Processing</h1>
        <p className="mt-2 text-sm text-gray-600">
          Upload and process videos with multi-vector embeddings using TwelveLabs Marengo or Amazon Bedrock
        </p>
      </div>

      {/* Video Source Selection */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">1. Select Video Source</h3>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-4">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('samples')}
              className={`${
                activeTab === 'samples'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              <Film className="inline-block w-5 h-5 mr-2" />
              Creative Commons Collections
            </button>
            <button
              onClick={() => setActiveTab('upload')}
              className={`${
                activeTab === 'upload'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              <Upload className="inline-block w-5 h-5 mr-2" />
              Custom Upload
            </button>
            <button
              onClick={() => setActiveTab('s3uri')}
              className={`${
                activeTab === 's3uri'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              <Video className="inline-block w-5 h-5 mr-2" />
              S3 URI
            </button>
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'samples' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Select from Creative Commons licensed videos from Google and Blender Foundation
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-96 overflow-y-auto">
              {sampleVideos.map((video: SampleVideo) => (
                <div
                  key={video.id}
                  onClick={() => toggleSampleVideo(video.id)}
                  className={`cursor-pointer border-2 rounded-lg p-3 transition-all ${
                    selectedSampleVideos.has(video.id)
                      ? 'border-indigo-500 bg-indigo-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <img
                    src={video.thumb}
                    alt={video.title}
                    className="w-full h-32 object-cover rounded mb-2"
                  />
                  <h4 className="font-medium text-sm text-gray-900">{video.title}</h4>
                  <p className="text-xs text-gray-500 mt-1">{video.subtitle}</p>
                  {selectedSampleVideos.has(video.id) && (
                    <CheckCircle className="absolute top-2 right-2 w-6 h-6 text-indigo-600" />
                  )}
                </div>
              ))}
            </div>
            <div className="flex justify-between items-center pt-4 border-t">
              <p className="text-sm text-gray-600">
                {selectedSampleVideos.size} video{selectedSampleVideos.size !== 1 ? 's' : ''} selected
              </p>
              <button
                onClick={handleProcessSampleVideos}
                disabled={selectedSampleVideos.size === 0 || processMutation.isPending}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
              >
                <Play className="-ml-1 mr-2 h-5 w-5" />
                Process Selected Videos
              </button>
            </div>
          </div>
        )}

        {activeTab === 'upload' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Upload video files (mp4, avi, mov, mkv, webm)
              </label>
              <input
                type="file"
                accept="video/*"
                multiple
                onChange={(e) => setSelectedFiles(Array.from(e.target.files || []))}
                className="block w-full text-sm text-gray-500
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-md file:border-0
                  file:text-sm file:font-semibold
                  file:bg-indigo-50 file:text-indigo-700
                  hover:file:bg-indigo-100"
              />
            </div>
            {selectedFiles.length > 0 && (
              <div className="bg-gray-50 rounded p-3">
                <p className="text-sm font-medium text-gray-700 mb-2">Selected files:</p>
                <ul className="text-sm text-gray-600 space-y-1">
                  {selectedFiles.map((file, idx) => (
                    <li key={idx}>• {file.name}</li>
                  ))}
                </ul>
              </div>
            )}
            <button
              onClick={handleMultipleFileUpload}
              disabled={selectedFiles.length === 0 || uploadMutation.isPending}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
            >
              {uploadMutation.isPending ? (
                <Loader2 className="-ml-1 mr-2 h-5 w-5 animate-spin" />
              ) : (
                <Upload className="-ml-1 mr-2 h-5 w-5" />
              )}
              Upload & Process
            </button>
          </div>
        )}

        {activeTab === 's3uri' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                S3 URI (e.g., s3://bucket-name/path/to/video.mp4)
              </label>
              <input
                type="text"
                value={s3Uri}
                onChange={(e) => setS3Uri(e.target.value)}
                placeholder="s3://your-bucket/video.mp4"
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              />
            </div>
            <button
              onClick={handleProcess}
              disabled={!s3Uri || processMutation.isPending}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
            >
              <Play className="-ml-1 mr-2 h-5 w-5" />
              Process Video
            </button>
          </div>
        )}
      </div>

      {/* Embedding Model Configuration */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">2. Configure Embedding Model</h3>

        <div className="space-y-4">
          {/* Model Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Embedding Model</label>
            <div className="grid grid-cols-3 gap-4">
              <button
                onClick={() => setSettings({ ...settings, embeddingModel: 'twelvelabs-marengo' })}
                className={`p-4 border-2 rounded-lg text-left transition-all ${
                  settings.embeddingModel === 'twelvelabs-marengo'
                    ? 'border-indigo-500 bg-indigo-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <h4 className="font-medium text-gray-900">Marengo 2.7</h4>
                <p className="text-xs text-gray-500 mt-1">Multi-vector (3 spaces)</p>
                <p className="text-xs text-indigo-600 mt-1">Choose vector types</p>
              </button>
              <button
                onClick={() => setSettings({ ...settings, embeddingModel: 'amazon-nova' })}
                className={`p-4 border-2 rounded-lg text-left transition-all ${
                  settings.embeddingModel === 'amazon-nova'
                    ? 'border-indigo-500 bg-indigo-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <h4 className="font-medium text-gray-900">Amazon Nova</h4>
                <p className="text-xs text-gray-500 mt-1">Single unified space</p>
                <p className="text-xs text-indigo-600 mt-1">Choose dimension</p>
              </button>
              <button
                onClick={() => setSettings({ ...settings, embeddingModel: 'bedrock-titan' })}
                className={`p-4 border-2 rounded-lg text-left transition-all ${
                  settings.embeddingModel === 'bedrock-titan'
                    ? 'border-indigo-500 bg-indigo-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <h4 className="font-medium text-gray-900">Titan Text</h4>
                <p className="text-xs text-gray-500 mt-1">Text-only (1536D)</p>
                <p className="text-xs text-gray-400 mt-1">Legacy option</p>
              </button>
            </div>
          </div>

          {/* Vector Types (for Marengo - Multi-Vector Approach) */}
          {settings.embeddingModel === 'twelvelabs-marengo' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Vector Types (Choose which embeddings to generate)
              </label>
              <div className="space-y-2">
                {['visual-text', 'visual-image', 'audio'].map((type) => (
                  <label key={type} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={settings.vectorTypes.includes(type)}
                      onChange={() => toggleVectorType(type)}
                      className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700 capitalize">
                      {type.replace('-', ' ')} (1024D)
                    </span>
                  </label>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Generates separate embeddings in different semantic spaces
              </p>
            </div>
          )}

          {/* Nova Configuration (Single-Vector Approach) */}
          {settings.embeddingModel === 'amazon-nova' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Embedding Dimension (Choose accuracy vs cost tradeoff)
                </label>
                <select
                  value={settings.novaDimension}
                  onChange={(e) => setSettings({ ...settings, novaDimension: parseInt(e.target.value) as any })}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                >
                  <option value="3072">3072D - Highest accuracy (premium cost)</option>
                  <option value="1024">1024D - Balanced (recommended)</option>
                  <option value="384">384D - Fast & affordable</option>
                  <option value="256">256D - Ultra-fast & low cost</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Embedding Mode (Choose which modalities to include)
                </label>
                <select
                  value={settings.novaMode}
                  onChange={(e) => setSettings({ ...settings, novaMode: e.target.value as any })}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                >
                  <option value="AUDIO_VIDEO_COMBINED">Audio + Video Combined (all modalities)</option>
                  <option value="VIDEO_ONLY">Video Only (visual content)</option>
                  <option value="AUDIO_ONLY">Audio Only (audio content)</option>
                </select>
              </div>

              <div className="bg-blue-50 p-3 rounded">
                <p className="text-xs text-blue-800">
                  <strong>Nova generates 1 unified embedding</strong> across all selected modalities.
                  This enables direct cross-modal search (e.g., text query finds relevant videos).
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Processing Settings */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">3. Processing Settings</h3>

        <div className="space-y-4">
          {/* Segment Duration */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Segment Duration: {settings.segmentDuration} seconds
            </label>
            <input
              type="range"
              min="2"
              max="10"
              step="1"
              value={settings.segmentDuration}
              onChange={(e) => setSettings({ ...settings, segmentDuration: parseInt(e.target.value) })}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>2s</span>
              <span>10s</span>
            </div>
          </div>

          {/* Quality Preset */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Quality Preset</label>
            <select
              value={settings.quality}
              onChange={(e) => setSettings({ ...settings, quality: e.target.value as any })}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            >
              <option value="standard">Standard (Faster, Lower Cost)</option>
              <option value="high">High (Balanced)</option>
              <option value="maximum">Maximum (Slower, Higher Quality)</option>
            </select>
          </div>

          {/* Batch Processing */}
          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={settings.batchProcessing}
                onChange={(e) => setSettings({ ...settings, batchProcessing: e.target.checked })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700">Enable batch processing</span>
            </label>
            <p className="text-xs text-gray-500 mt-1 ml-6">
              Process multiple videos in parallel for faster throughput
            </p>
          </div>
        </div>
      </div>

      {/* Storage Backend Selection */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">4. Storage Backends (Select Multiple for Comparison)</h3>

        <div className="grid grid-cols-2 gap-4">
          <label className="flex items-start p-3 border-2 rounded-lg hover:bg-gray-50 cursor-pointer transition-all"
                 style={{borderColor: settings.storeInS3Vectors ? '#4F46E5' : '#E5E7EB'}}>
            <input
              type="checkbox"
              checked={settings.storeInS3Vectors}
              onChange={(e) => setSettings({ ...settings, storeInS3Vectors: e.target.checked })}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded mt-1"
            />
            <div className="ml-3">
              <span className="text-sm font-medium text-gray-900">S3 Vectors (Direct)</span>
              <p className="text-xs text-gray-500 mt-1">
                Native AWS, serverless, $0.023/GB/month
              </p>
              <p className="text-xs text-indigo-600 mt-1">40-80ms latency</p>
            </div>
          </label>

          <label className="flex items-start p-3 border-2 rounded-lg hover:bg-gray-50 cursor-pointer transition-all"
                 style={{borderColor: settings.storeInOpenSearch ? '#4F46E5' : '#E5E7EB'}}>
            <input
              type="checkbox"
              checked={settings.storeInOpenSearch}
              onChange={(e) => setSettings({ ...settings, storeInOpenSearch: e.target.checked })}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded mt-1"
            />
            <div className="ml-3">
              <span className="text-sm font-medium text-gray-900">OpenSearch</span>
              <p className="text-xs text-gray-500 mt-1">
                S3Vector backend, hybrid search, unlimited metadata
              </p>
              <p className="text-xs text-indigo-600 mt-1">100-200ms latency</p>
            </div>
          </label>

          <label className="flex items-start p-3 border-2 rounded-lg hover:bg-gray-50 cursor-pointer transition-all"
                 style={{borderColor: settings.storeInQdrant ? '#4F46E5' : '#E5E7EB'}}>
            <input
              type="checkbox"
              checked={settings.storeInQdrant}
              onChange={(e) => setSettings({ ...settings, storeInQdrant: e.target.checked })}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded mt-1"
            />
            <div className="ml-3">
              <span className="text-sm font-medium text-gray-900">Qdrant</span>
              <p className="text-xs text-gray-500 mt-1">
                High-performance HNSW, managed cloud or self-hosted
              </p>
              <p className="text-xs text-green-600 mt-1">20-50ms latency (fastest)</p>
            </div>
          </label>

          <label className="flex items-start p-3 border-2 rounded-lg hover:bg-gray-50 cursor-pointer transition-all"
                 style={{borderColor: settings.storeInLanceDB ? '#4F46E5' : '#E5E7EB'}}>
            <input
              type="checkbox"
              checked={settings.storeInLanceDB}
              onChange={(e) => setSettings({ ...settings, storeInLanceDB: e.target.checked })}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded mt-1"
            />
            <div className="ml-3">
              <span className="text-sm font-medium text-gray-900">LanceDB</span>
              <p className="text-xs text-gray-500 mt-1">
                Embedded, flexible backends (S3/EFS/EBS)
              </p>
              <p className="text-xs text-indigo-600 mt-1">50-500ms (depends on backend)</p>
            </div>
          </label>
        </div>

        {/* LanceDB Backend Selection */}
        {settings.storeInLanceDB && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              LanceDB Backend
            </label>
            <div className="grid grid-cols-3 gap-2">
              <button
                onClick={() => setSettings({ ...settings, lancedbBackend: 's3' })}
                className={`p-2 text-sm border-2 rounded ${
                  settings.lancedbBackend === 's3'
                    ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                S3 (Serverless)
              </button>
              <button
                onClick={() => setSettings({ ...settings, lancedbBackend: 'efs' })}
                className={`p-2 text-sm border-2 rounded ${
                  settings.lancedbBackend === 'efs'
                    ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                EFS (Shared)
              </button>
              <button
                onClick={() => setSettings({ ...settings, lancedbBackend: 'ebs' })}
                className={`p-2 text-sm border-2 rounded ${
                  settings.lancedbBackend === 'ebs'
                    ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                EBS (Fast)
              </button>
            </div>
          </div>
        )}

        {!settings.storeInS3Vectors && !settings.storeInOpenSearch && !settings.storeInQdrant && !settings.storeInLanceDB && (
          <p className="text-sm text-amber-600 bg-amber-50 p-3 rounded mt-4">
            ⚠️ Please select at least one storage backend
          </p>
        )}
      </div>

      {/* Processing Jobs Dashboard */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium text-gray-900">Processing Jobs</h3>
          <button
            onClick={() => refetchJobs()}
            className="text-sm text-indigo-600 hover:text-indigo-700"
          >
            Refresh
          </button>
        </div>

        <div className="space-y-3">
          {jobs?.jobs && jobs.jobs.length > 0 ? (
            jobs.jobs.map((job: any) => {
              const statusIconMap: Record<string, React.ReactElement> = {
                processing: <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />,
                completed: <CheckCircle className="w-5 h-5 text-green-500" />,
                failed: <XCircle className="w-5 h-5 text-red-500" />,
                pending: <Clock className="w-5 h-5 text-yellow-500" />,
              };
              const statusIcon = statusIconMap[job.status] || <Clock className="w-5 h-5 text-gray-500" />;

              const statusColorMap: Record<string, string> = {
                processing: 'bg-blue-50 border-blue-200',
                completed: 'bg-green-50 border-green-200',
                failed: 'bg-red-50 border-red-200',
                pending: 'bg-yellow-50 border-yellow-200',
              };
              const statusColor = statusColorMap[job.status] || 'bg-gray-50 border-gray-200';

              return (
                <div
                  key={job.job_id}
                  className={`border-2 rounded-lg p-4 ${statusColor}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-3 flex-1">
                      {statusIcon}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          Job ID: {job.job_id}
                        </p>
                        <p className="text-sm text-gray-500 capitalize">
                          Status: {job.status}
                        </p>
                        {job.error && (
                          <p className="text-xs text-red-600 mt-1">
                            Error: {job.error}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="ml-4 flex-shrink-0">
                      {job.progress !== undefined && job.progress !== null && (
                        <div className="text-right">
                          <p className="text-sm font-medium text-gray-900">
                            {Math.round(job.progress)}%
                          </p>
                          <div className="w-24 bg-gray-200 rounded-full h-2 mt-1">
                            <div
                              className="bg-indigo-600 h-2 rounded-full transition-all"
                              style={{ width: `${job.progress}%` }}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Results Summary */}
                  {job.status === 'completed' && job.result && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <p className="text-xs text-gray-600">
                        <strong>Video ID:</strong> {job.result.video_id}
                      </p>
                      <p className="text-xs text-gray-600">
                        <strong>Segments:</strong> {job.result.segments?.length || 0}
                      </p>
                    </div>
                  )}

                  {/* Store to Index Section - Only show for completed jobs */}
                  {job.status === 'completed' && (
                    <div className="mt-4 pt-4 border-t border-gray-200">
                      <h4 className="text-sm font-semibold text-gray-900 mb-3">Store Embeddings to Index</h4>
                      
                      {/* Bucket Selector */}
                      <div className="space-y-3">
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1">
                            1. Select Vector Bucket
                          </label>
                          <select
                            value={selectedBucket}
                            onChange={(e) => {
                              setSelectedBucket(e.target.value);
                              setSelectedIndexArn('');
                              setStorageResults(null);
                            }}
                            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                          >
                            <option value="">Select vector bucket</option>
                            {vectorBuckets.map((bucket: any) => (
                              <option key={bucket.name} value={bucket.name}>
                                {bucket.name}
                              </option>
                            ))}
                          </select>
                        </div>

                        {/* Index Selector */}
                        {selectedBucket && (
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">
                              2. Select Vector Index
                            </label>
                            <select
                              value={selectedIndexArn}
                              onChange={(e) => {
                                setSelectedIndexArn(e.target.value);
                                setStorageResults(null);
                              }}
                              className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                            >
                              <option value="">Select vector index</option>
                              {availableIndexes.map((index: any) => (
                                <option key={index.index_arn} value={index.index_arn}>
                                  {index.index_name} ({index.dimension}D, {index.distance_metric})
                                </option>
                              ))}
                            </select>
                            {availableIndexes.length === 0 && (
                              <p className="text-xs text-amber-600 mt-1">
                                No indexes found. Create one in Resource Management.
                              </p>
                            )}
                          </div>
                        )}

                        {/* Backend Checkboxes */}
                        {selectedIndexArn && (
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-2">
                              3. Select Storage Backends
                            </label>
                            <div className="grid grid-cols-2 gap-2">
                              {['s3_vector', 'opensearch', 'qdrant', 'lancedb'].map(backend => (
                                <label key={backend} className="flex items-center gap-2 text-xs">
                                  <input
                                    type="checkbox"
                                    checked={selectedBackends.includes(backend)}
                                    onChange={() => toggleBackend(backend)}
                                    className="h-3 w-3 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                                  />
                                  <span className="text-gray-700 capitalize">
                                    {backend.replace('_', ' ')}
                                  </span>
                                </label>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Store Button */}
                        {selectedIndexArn && selectedBackends.length > 0 && (
                          <button
                            onClick={handleStoreEmbeddings}
                            disabled={storeEmbeddingsMutation.isPending}
                            className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {storeEmbeddingsMutation.isPending ? (
                              <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Storing...
                              </>
                            ) : (
                              <>
                                <Database className="w-4 h-4" />
                                Store to {selectedBackends.length} Backend(s)
                              </>
                            )}
                          </button>
                        )}

                        {/* Storage Results */}
                        {storageResults && (
                          <div className="mt-3 space-y-2">
                            <p className="text-xs font-medium text-gray-700">Storage Results:</p>
                            {Object.entries(storageResults).map(([backend, result]: [string, any]) => (
                              <div
                                key={backend}
                                className={`flex items-center justify-between p-2 rounded text-xs ${
                                  result.success
                                    ? 'bg-green-50 border border-green-200'
                                    : 'bg-red-50 border border-red-200'
                                }`}
                              >
                                <div className="flex items-center gap-2">
                                  {result.success ? (
                                    <CheckCircle className="w-4 h-4 text-green-600" />
                                  ) : (
                                    <XCircle className="w-4 h-4 text-red-600" />
                                  )}
                                  <span className="font-medium capitalize">
                                    {backend.replace('_', ' ')}
                                  </span>
                                </div>
                                <span className={result.success ? 'text-green-700' : 'text-red-700'}>
                                  {result.success
                                    ? `${result.vectors_stored} vectors stored`
                                    : 'Failed'}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          ) : (
            <div className="text-center py-8">
              <Video className="mx-auto h-12 w-12 text-gray-400" />
              <p className="mt-2 text-sm text-gray-500">No processing jobs yet</p>
              <p className="text-xs text-gray-400 mt-1">
                Select videos and start processing to see jobs here
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Cost Estimation */}
      {(selectedSampleVideos.size > 0 || selectedFiles.length > 0) && (
        <div className="bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-2">💰 Estimated Cost</h3>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-600">Videos</p>
              <p className="text-xl font-bold text-gray-900">
                {selectedSampleVideos.size + selectedFiles.length}
              </p>
            </div>
            <div>
              <p className="text-gray-600">Vector Types</p>
              <p className="text-xl font-bold text-gray-900">
                {settings.vectorTypes.length}
              </p>
            </div>
            <div>
              <p className="text-gray-600">Storage</p>
              <p className="text-xl font-bold text-gray-900">
                {[settings.storeInS3Vectors, settings.storeInOpenSearch, settings.storeInQdrant, settings.storeInLanceDB].filter(Boolean).length}
              </p>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-3">
            💡 Actual costs depend on video duration and processing quality. S3 Vectors offers the most cost-effective storage.
          </p>
        </div>
      )}
    </div>
  );
}
