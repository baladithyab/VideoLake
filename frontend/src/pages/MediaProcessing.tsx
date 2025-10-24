import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { processingAPI } from '../api/client';
import { Upload, Film, Play, Video, CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react';
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
  embeddingModel: 'bedrock-titan' | 'twelvelabs-marengo';
  vectorTypes: string[];
  segmentDuration: number;
  quality: 'standard' | 'high' | 'maximum';
  batchProcessing: boolean;
  storeInS3Vectors: boolean;
  storeInOpenSearch: boolean;
}

export default function MediaProcessing() {
  const [activeTab, setActiveTab] = useState<'samples' | 'upload' | 's3uri'>('samples');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [s3Uri, setS3Uri] = useState('');
  const [selectedSampleVideos, setSelectedSampleVideos] = useState<Set<string>>(new Set());

  const [settings, setSettings] = useState<ProcessingSettings>({
    embeddingModel: 'twelvelabs-marengo',
    vectorTypes: ['visual-text', 'visual-image', 'audio'],
    segmentDuration: 5,
    quality: 'standard',
    batchProcessing: false,
    storeInS3Vectors: true,
    storeInOpenSearch: true,
  });

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

  const handleFileUpload = async () => {
    if (!selectedFile) return;
    await uploadMutation.mutateAsync(selectedFile);
  };

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

    for (const video of selectedVideos) {
      try {
        await processMutation.mutateAsync({
          video_s3_uri: video.sources[0],
          embedding_options: settings.vectorTypes,
        });
      } catch (error) {
        console.error(`Failed to process ${video.title}:`, error);
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

  const sampleVideos = sampleVideosData?.categories[0]?.videos || [];

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
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => setSettings({ ...settings, embeddingModel: 'twelvelabs-marengo' })}
                className={`p-4 border-2 rounded-lg text-left transition-all ${
                  settings.embeddingModel === 'twelvelabs-marengo'
                    ? 'border-indigo-500 bg-indigo-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <h4 className="font-medium text-gray-900">TwelveLabs Marengo 2.7</h4>
                <p className="text-xs text-gray-500 mt-1">Multi-vector model (visual, audio, text)</p>
              </button>
              <button
                onClick={() => setSettings({ ...settings, embeddingModel: 'bedrock-titan' })}
                className={`p-4 border-2 rounded-lg text-left transition-all ${
                  settings.embeddingModel === 'bedrock-titan'
                    ? 'border-indigo-500 bg-indigo-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <h4 className="font-medium text-gray-900">Amazon Bedrock Titan</h4>
                <p className="text-xs text-gray-500 mt-1">Text embeddings (1536 dimensions)</p>
              </button>
            </div>
          </div>

          {/* Vector Types (for TwelveLabs) */}
          {settings.embeddingModel === 'twelvelabs-marengo' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Vector Types</label>
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
                      {type.replace('-', ' ')}
                    </span>
                  </label>
                ))}
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
        <h3 className="text-lg font-medium text-gray-900 mb-4">4. Storage Backend</h3>

        <div className="space-y-3">
          <label className="flex items-start">
            <input
              type="checkbox"
              checked={settings.storeInS3Vectors}
              onChange={(e) => setSettings({ ...settings, storeInS3Vectors: e.target.checked })}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded mt-1"
            />
            <div className="ml-3">
              <span className="text-sm font-medium text-gray-700">S3 Vectors (Direct)</span>
              <p className="text-xs text-gray-500">
                Store embeddings directly in S3 Vector buckets. Cost-effective, limited to 10 metadata tags.
              </p>
            </div>
          </label>

          <label className="flex items-start">
            <input
              type="checkbox"
              checked={settings.storeInOpenSearch}
              onChange={(e) => setSettings({ ...settings, storeInOpenSearch: e.target.checked })}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded mt-1"
            />
            <div className="ml-3">
              <span className="text-sm font-medium text-gray-700">OpenSearch (with S3 Vector Backend)</span>
              <p className="text-xs text-gray-500">
                Store in OpenSearch with S3 Vectors as storage engine. Unlimited metadata, hybrid search capability.
              </p>
            </div>
          </label>

          {!settings.storeInS3Vectors && !settings.storeInOpenSearch && (
            <p className="text-sm text-amber-600 bg-amber-50 p-3 rounded">
              ⚠️ Please select at least one storage backend
            </p>
          )}
        </div>
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
              const statusIcon = {
                processing: <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />,
                completed: <CheckCircle className="w-5 h-5 text-green-500" />,
                failed: <XCircle className="w-5 h-5 text-red-500" />,
                pending: <Clock className="w-5 h-5 text-yellow-500" />,
              }[job.status] || <Clock className="w-5 h-5 text-gray-500" />;

              const statusColor = {
                processing: 'bg-blue-50 border-blue-200',
                completed: 'bg-green-50 border-green-200',
                failed: 'bg-red-50 border-red-200',
                pending: 'bg-yellow-50 border-yellow-200',
              }[job.status] || 'bg-gray-50 border-gray-200';

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
                {[settings.storeInS3Vectors, settings.storeInOpenSearch].filter(Boolean).length}
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
