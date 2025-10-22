import { useState } from 'react';
import { useMutation, useQuery } from '@tantml:query';
import { processingAPI } from '../api/client';
import { Upload, Film, Play } from 'lucide-react';

export default function MediaProcessing() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [s3Uri, setS3Uri] = useState('');

  const uploadMutation = useMutation({
    mutationFn: (file: File) => processingAPI.uploadVideo(file),
  });

  const processMutation = useMutation({
    mutationFn: (data: { video_s3_uri: string }) => processingAPI.processVideo(data),
  });

  const { data: jobs } = useQuery({
    queryKey: ['processing-jobs'],
    queryFn: async () => {
      const response = await processingAPI.listJobs();
      return response.data;
    },
    refetchInterval: 5000, // Poll every 5 seconds
  });

  const handleFileUpload = async () => {
    if (!selectedFile) return;
    const result = await uploadMutation.mutateAsync(selectedFile);
    if (result.data.success) {
      setS3Uri(result.data.s3_uri);
    }
  };

  const handleProcess = () => {
    if (!s3Uri) return;
    processMutation.mutate({ video_s3_uri: s3Uri });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Media Processing</h1>
        <p className="mt-2 text-sm text-gray-600">
          Upload and process videos with TwelveLabs Marengo
        </p>
      </div>

      {/* Upload Section */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Upload Video</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Choose video file</label>
            <input
              type="file"
              accept="video/*"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              className="mt-1 block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-md file:border-0
                file:text-sm file:font-semibold
                file:bg-indigo-50 file:text-indigo-700
                hover:file:bg-indigo-100"
            />
          </div>
          <button
            onClick={handleFileUpload}
            disabled={!selectedFile || uploadMutation.isPending}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            <Upload className="-ml-1 mr-2 h-5 w-5" />
            Upload
          </button>
        </div>
      </div>

      {/* S3 URI Section */}
      {s3Uri && (
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Process Video</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">S3 URI</label>
              <input
                type="text"
                value={s3Uri}
                readOnly
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm bg-gray-50 sm:text-sm"
              />
            </div>
            <button
              onClick={handleProcess}
              disabled={processMutation.isPending}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              <Play className="-ml-1 mr-2 h-5 w-5" />
              Process Video
            </button>
          </div>
        </div>
      )}

      {/* Processing Jobs */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Processing Jobs</h3>
        <div className="space-y-3">
          {jobs?.jobs?.length > 0 ? (
            jobs.jobs.map((job: any) => (
              <div key={job.job_id} className="border border-gray-200 rounded-md p-4">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="text-sm font-medium text-gray-900">Job ID: {job.job_id}</p>
                    <p className="text-sm text-gray-500">Status: {job.status}</p>
                  </div>
                  <div className="text-sm text-gray-500">
                    {job.progress !== undefined && `${job.progress}%`}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-gray-500">No processing jobs</p>
          )}
        </div>
      </div>
    </div>
  );
}

