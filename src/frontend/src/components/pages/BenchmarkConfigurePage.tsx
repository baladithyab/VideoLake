import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, CheckCircle, Info } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Alert, AlertDescription } from '../ui/alert';
import { api } from '../../api/client';
import { toast } from 'react-hot-toast';
import type { BenchmarkConfig } from '../../types/benchmark';

interface BackendOption {
  value: string;
  label: string;
  deployed: boolean;
}

type WizardStep = 'backends' | 'parameters';

export const BenchmarkConfigurePage: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<WizardStep>('backends');
  const [availableBackends, setAvailableBackends] = useState<BackendOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);

  const [config, setConfig] = useState<BenchmarkConfig>({
    backends: [],
    num_queries: 50,
    query_type: 'text',
    use_existing_embeddings: true,
  });

  useEffect(() => {
    loadAvailableBackends();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadAvailableBackends = async () => {
    try {
      const response = await api.getInfrastructureStatus();
      const stores = response.data.stores || {};

      const backends: BackendOption[] = Object.entries(stores).map(([key, value]) => ({
        value: key,
        label: formatBackendName(key),
        deployed: (value as { status?: string }).status === 'deployed',
      }));

      setAvailableBackends(backends);
    } catch (error) {
      console.error('Failed to load backends:', error);
      toast.error('Failed to load available backends');
    } finally {
      setIsLoading(false);
    }
  };

  const formatBackendName = (backend: string): string => {
    const nameMap: Record<string, string> = {
      's3vector': 'S3 Vector',
      'lancedb': 'LanceDB',
      'qdrant': 'Qdrant',
      'opensearch': 'OpenSearch',
    };
    return nameMap[backend] || backend.charAt(0).toUpperCase() + backend.slice(1);
  };

  const handleBackendToggle = (backend: string) => {
    setConfig(prev => ({
      ...prev,
      backends: prev.backends.includes(backend)
        ? prev.backends.filter(b => b !== backend)
        : [...prev.backends, backend],
    }));
  };

  const canProceedFromBackends = () => {
    return config.backends.length >= 2;
  };

  const estimatedRuntime = () => {
    const queriesPerBackend = config.num_queries;
    const numBackends = config.backends.length;
    const avgTimePerQuery = config.use_existing_embeddings ? 0.1 : 0.5; // seconds
    const totalSeconds = (queriesPerBackend * numBackends * avgTimePerQuery) + 10; // +10s overhead

    const minutes = Math.floor(totalSeconds / 60);
    const seconds = Math.floor(totalSeconds % 60);

    if (minutes === 0) {
      return `~${seconds}s`;
    }
    return `~${minutes}m ${seconds}s`;
  };

  const handleStartBenchmark = async () => {
    setIsStarting(true);
    try {
      const response = await api.startBenchmark({
        backends: config.backends,
        config: {
          queries: config.num_queries,
          operation: 'search',
          use_ecs: true,
        },
      });

      toast.success('Benchmark started!');
      navigate(`/benchmark/run/${response.data.id}`);
    } catch (error) {
      const errorMessage = (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to start benchmark';
      toast.error(errorMessage);
      setIsStarting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading configuration...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/benchmark')}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Hub
          </Button>
        </div>

        {/* Progress Steps */}
        <Card>
          <CardContent className="py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className={`h-8 w-8 rounded-full flex items-center justify-center ${
                  currentStep === 'backends' ? 'bg-indigo-600 text-white' : 'bg-green-600 text-white'
                }`}>
                  {currentStep === 'parameters' ? <CheckCircle className="h-5 w-5" /> : '1'}
                </div>
                <span className={`font-medium ${currentStep === 'backends' ? 'text-gray-900' : 'text-gray-600'}`}>
                  Select Backends
                </span>
              </div>

              <div className="flex-1 h-0.5 bg-gray-300 mx-4" />

              <div className="flex items-center gap-2">
                <div className={`h-8 w-8 rounded-full flex items-center justify-center ${
                  currentStep === 'parameters' ? 'bg-indigo-600 text-white' : 'bg-gray-300 text-gray-600'
                }`}>
                  2
                </div>
                <span className={`font-medium ${currentStep === 'parameters' ? 'text-gray-900' : 'text-gray-600'}`}>
                  Configure Parameters
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Step 1: Backend Selection */}
        {currentStep === 'backends' && (
          <Card>
            <CardHeader>
              <CardTitle>Select Backends to Benchmark</CardTitle>
              <CardDescription>
                Choose which vector stores to compare. At least 2 backends are required.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid md:grid-cols-2 gap-4">
                {availableBackends.map((backend) => (
                  <label
                    key={backend.value}
                    className={`relative flex flex-col p-4 border-2 rounded-lg cursor-pointer transition-all ${
                      config.backends.includes(backend.value)
                        ? 'border-indigo-600 bg-indigo-50'
                        : 'border-gray-300 hover:border-gray-400'
                    } ${!backend.deployed ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <input
                        type="checkbox"
                        checked={config.backends.includes(backend.value)}
                        onChange={() => handleBackendToggle(backend.value)}
                        disabled={!backend.deployed}
                        className="h-5 w-5 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                      />
                      {backend.deployed ? (
                        <Badge variant="default" className="bg-green-500">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Deployed
                        </Badge>
                      ) : (
                        <Badge variant="destructive">
                          Not Deployed
                        </Badge>
                      )}
                    </div>
                    <span className="text-lg font-semibold text-gray-900 mt-2">
                      {backend.label}
                    </span>
                  </label>
                ))}
              </div>

              {!canProceedFromBackends() && (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    At least 2 backends required for comparison
                  </AlertDescription>
                </Alert>
              )}

              <div className="flex justify-end">
                <Button
                  onClick={() => setCurrentStep('parameters')}
                  disabled={!canProceedFromBackends()}
                  size="lg"
                >
                  Continue
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 2: Parameters */}
        {currentStep === 'parameters' && (
          <Card>
            <CardHeader>
              <CardTitle>Configure Benchmark Parameters</CardTitle>
              <CardDescription>
                Set up query configuration and performance options
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-8">
              {/* Query Configuration */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900">Query Configuration</h3>

                <div className="space-y-2">
                  <Label htmlFor="num-queries">
                    Number of queries
                  </Label>
                  <div className="flex items-center gap-4">
                    <Input
                      id="num-queries"
                      type="range"
                      min="1"
                      max="1000"
                      value={config.num_queries}
                      onChange={(e) => setConfig({ ...config, num_queries: parseInt(e.target.value) })}
                      className="flex-1"
                    />
                    <Input
                      type="number"
                      min="1"
                      max="1000"
                      value={config.num_queries}
                      onChange={(e) => setConfig({ ...config, num_queries: parseInt(e.target.value) })}
                      className="w-24"
                    />
                  </div>
                  <p className="text-sm text-gray-500">Recommended: 50-200 queries for balanced results</p>
                </div>

                <div className="space-y-2">
                  <Label>Query type</Label>
                  <div className="flex flex-col space-y-2">
                    {[
                      { value: 'text', label: 'Text queries (natural language)' },
                      { value: 'image', label: 'Image queries (visual similarity)' },
                      { value: 'video', label: 'Mixed (50/50 text and image)' },
                    ].map((type) => (
                      <label key={type.value} className="flex items-center">
                        <input
                          type="radio"
                          name="query-type"
                          value={type.value}
                          checked={config.query_type === type.value}
                          onChange={(e) => setConfig({ ...config, query_type: e.target.value as 'text' | 'image' | 'video' })}
                          className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
                        />
                        <span className="ml-2 text-sm text-gray-900">{type.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              {/* Performance Configuration */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900">Performance Configuration</h3>

                <div className="space-y-3">
                  <label className="flex items-start">
                    <input
                      type="checkbox"
                      checked={config.use_existing_embeddings}
                      onChange={(e) => setConfig({ ...config, use_existing_embeddings: e.target.checked })}
                      className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded mt-0.5"
                    />
                    <div className="ml-2">
                      <span className="text-sm font-medium text-gray-900">
                        Use existing embeddings (faster)
                      </span>
                      <p className="text-xs text-gray-500">
                        Recommended for quick comparisons
                      </p>
                    </div>
                  </label>
                </div>
              </div>

              {/* Estimated Runtime */}
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  <strong>Estimated runtime:</strong> {estimatedRuntime()} for {config.backends.length} backends
                </AlertDescription>
              </Alert>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-4">
                <Button
                  variant="outline"
                  onClick={() => setCurrentStep('backends')}
                >
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back
                </Button>

                <Button
                  onClick={handleStartBenchmark}
                  disabled={isStarting}
                  size="lg"
                  className="min-w-[180px]"
                >
                  {isStarting ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                      Starting...
                    </>
                  ) : (
                    'Start Benchmark'
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};
