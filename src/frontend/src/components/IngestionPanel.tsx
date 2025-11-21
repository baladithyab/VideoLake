import React, { useState } from 'react';
import { api } from '../api/client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { toast } from 'react-hot-toast';
import { Loader2, Upload } from 'lucide-react';

export function IngestionPanel() {
  const [videoPath, setVideoPath] = useState('');
  const [modelType, setModelType] = useState('Amazon Nova');
  const [selectedBackends, setSelectedBackends] = useState<string[]>(['S3Vector']);
  const [isIngesting, setIsIngesting] = useState(false);

  const handleBackendToggle = (backend: string) => {
    setSelectedBackends(prev => 
      prev.includes(backend) 
        ? prev.filter(b => b !== backend)
        : [...prev, backend]
    );
  };

  const handleIngestion = async () => {
    if (!videoPath) {
      toast.error('Please enter an S3 URI');
      return;
    }
    if (selectedBackends.length === 0) {
      toast.error('Please select at least one backend');
      return;
    }

    setIsIngesting(true);
    try {
      await api.startIngestion({
        video_path: videoPath,
        model_type: modelType,
        backend_types: selectedBackends
      });
      toast.success('Ingestion started successfully');
      setVideoPath('');
    } catch (error) {
      console.error('Ingestion failed:', error);
      toast.error('Failed to start ingestion');
    } finally {
      setIsIngesting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Video Ingestion</CardTitle>
        <CardDescription>
          Process videos from S3 and index them into vector stores
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <Label htmlFor="s3-uri">S3 URI</Label>
          <Input
            id="s3-uri"
            placeholder="s3://bucket/path/to/video.mp4"
            value={videoPath}
            onChange={(e) => setVideoPath(e.target.value)}
          />
        </div>

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
          disabled={isIngesting}
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
      </CardContent>
    </Card>
  );
}