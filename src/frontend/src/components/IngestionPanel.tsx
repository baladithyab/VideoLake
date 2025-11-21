import React, { useState, useEffect } from 'react';
import { api, type Dataset } from '../api/client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { toast } from 'react-hot-toast';
import { Loader2, Upload, Database, FileVideo } from 'lucide-react';
import axios from 'axios';

export function IngestionPanel() {
  const [videoPath, setVideoPath] = useState('');
  const [modelType, setModelType] = useState('Amazon Nova');
  const [selectedBackends, setSelectedBackends] = useState<string[]>(['S3Vector']);
  const [isIngesting, setIsIngesting] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<string>('');
  const [activeTab, setActiveTab] = useState('s3');
  const [executionArn, setExecutionArn] = useState<string | null>(null);
  const [ingestionStatus, setIngestionStatus] = useState<string | null>(null);

  useEffect(() => {
    loadDatasets();
  }, []);

  useEffect(() => {
    let intervalId: any;

    if (executionArn && (ingestionStatus === 'RUNNING' || !ingestionStatus)) {
      intervalId = setInterval(async () => {
        try {
          const response = await api.getIngestionStatus(executionArn);
          const newStatus = response.data.status;
          setIngestionStatus(newStatus);
          
          if (newStatus === 'SUCCEEDED') {
             toast.success('Ingestion completed successfully!');
             setExecutionArn(null); // Stop polling
          } else if (newStatus === 'FAILED') {
             toast.error(`Ingestion failed: ${response.data.error || 'Unknown error'}`);
             setExecutionArn(null); // Stop polling
          }
        } catch (error) {
          console.error('Failed to poll status:', error);
        }
      }, 3000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [executionArn, ingestionStatus]);

  const loadDatasets = async () => {
    try {
      const response = await api.listDatasets();
      setDatasets(response.data);
    } catch (error) {
      console.error('Failed to load datasets:', error);
      toast.error('Failed to load available datasets');
    }
  };

  const handleBackendToggle = (backend: string) => {
    setSelectedBackends(prev =>
      prev.includes(backend)
        ? prev.filter(b => b !== backend)
        : [...prev, backend]
    );
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      // Get presigned URL
      const { data } = await api.getUploadUrl(file.name, file.type);
      
      // Upload to S3
      await axios.put(data.upload_url, file, {
        headers: {
          'Content-Type': file.type
        }
      });

      setVideoPath(data.s3_uri);
      toast.success('File uploaded successfully');
    } catch (error) {
      console.error('Upload failed:', error);
      toast.error('Failed to upload file');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDatasetSelect = (datasetName: string) => {
    setSelectedDataset(datasetName);
    // For datasets, we might want to trigger a different ingestion flow
    // For now, we'll just set a placeholder path or handle it in the backend
    // Assuming the backend knows how to handle dataset names if we pass them
    // But the current API expects video_path.
    // Let's assume for now we just select it and the user clicks start.
    // Ideally, we should update the startIngestion API to accept dataset_name too.
    // Or we can construct a special URI like dataset://msr-vtt
    setVideoPath(`dataset://${datasetName}`);
  };

  const handleIngestion = async () => {
    if (!videoPath) {
      toast.error('Please provide a video source');
      return;
    }
    if (selectedBackends.length === 0) {
      toast.error('Please select at least one backend');
      return;
    }

    setIsIngesting(true);
    setIngestionStatus(null);
    setExecutionArn(null);

    try {
      const response = await api.startIngestion({
        video_path: videoPath,
        model_type: modelType,
        backend_types: selectedBackends
      });
      
      setExecutionArn(response.data.execution_arn);
      setIngestionStatus('RUNNING');

      toast.success('Ingestion started successfully');
      if (!videoPath.startsWith('dataset://')) {
          setVideoPath('');
      }
    } catch (error) {
      console.error('Ingestion failed:', error);
      toast.error('Failed to start ingestion');
      setIngestionStatus(null);
    } finally {
      setIsIngesting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Video Ingestion</CardTitle>
        <CardDescription>
          Process videos and index them into vector stores
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="s3">S3 URI</TabsTrigger>
            <TabsTrigger value="upload">Upload Video</TabsTrigger>
            <TabsTrigger value="dataset">Select Dataset</TabsTrigger>
          </TabsList>

          <TabsContent value="s3" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="s3-uri">S3 URI</Label>
              <Input
                id="s3-uri"
                placeholder="s3://bucket/path/to/video.mp4"
                value={videoPath}
                onChange={(e) => setVideoPath(e.target.value)}
                disabled={activeTab !== 's3'}
              />
            </div>
          </TabsContent>

          <TabsContent value="upload" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Upload Video File</Label>
              <div className="flex items-center gap-4">
                <Input
                  type="file"
                  accept="video/*"
                  onChange={handleFileUpload}
                  disabled={isUploading}
                />
                {isUploading && <Loader2 className="h-4 w-4 animate-spin" />}
              </div>
              {videoPath && activeTab === 'upload' && (
                <p className="text-sm text-muted-foreground">
                  Uploaded to: {videoPath}
                </p>
              )}
            </div>
          </TabsContent>

          <TabsContent value="dataset" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Available Datasets</Label>
              <div className="grid gap-2">
                {datasets.map((dataset) => (
                  <div
                    key={dataset.name}
                    className={`p-3 border rounded-md cursor-pointer transition-colors ${
                      selectedDataset === dataset.name
                        ? 'bg-primary/10 border-primary'
                        : 'hover:bg-accent'
                    }`}
                    onClick={() => handleDatasetSelect(dataset.name)}
                  >
                    <div className="flex justify-between items-center">
                      <span className="font-medium">{dataset.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {dataset.estimated_videos} videos
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      Source: {dataset.source}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>
        </Tabs>

        <div className="space-y-2">
          <Label>Model Selection</Label>
          <select
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            value={modelType}
            onChange={(e) => setModelType(e.target.value)}
          >
            <option value="Amazon Nova">Amazon Nova</option>
            <option value="Bedrock Titan">Bedrock Titan</option>
          </select>
        </div>

        <div className="space-y-2">
          <Label>Target Backends</Label>
          <div className="flex gap-4">
            {['S3Vector', 'LanceDB', 'Qdrant'].map((backend) => (
              <label key={backend} className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  checked={selectedBackends.includes(backend)}
                  onChange={() => handleBackendToggle(backend)}
                />
                <span className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                  {backend}
                </span>
              </label>
            ))}
          </div>
        </div>

        <Button
          className="w-full"
          onClick={handleIngestion}
          disabled={isIngesting || (activeTab === 'upload' && isUploading) || !videoPath}
        >
          {isIngesting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Starting Ingestion...
            </>
          ) : (
            <>
              <Upload className="mr-2 h-4 w-4" />
              Start Ingestion
            </>
          )}
        </Button>

        {ingestionStatus && (
          <div className={`mt-4 p-4 rounded-md border ${
            ingestionStatus === 'SUCCEEDED' ? 'bg-green-50 border-green-200 text-green-700' :
            ingestionStatus === 'FAILED' ? 'bg-red-50 border-red-200 text-red-700' :
            'bg-blue-50 border-blue-200 text-blue-700'
          }`}>
            <div className="flex items-center">
              {ingestionStatus === 'RUNNING' && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              <span className="font-medium">Status: {ingestionStatus}</span>
            </div>
            {executionArn && (
                <p className="text-xs mt-1 opacity-75 break-all font-mono">Execution ARN: {executionArn}</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}