import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { embeddingsAPI } from '../api/client';
import Plot from 'react-plotly.js';
import { RefreshCw, Download } from 'lucide-react';

type VisualizationMethod = 'pca' | 'tsne' | 'umap';

export default function EmbeddingVisualization() {
  const [method, setMethod] = useState<VisualizationMethod>('pca');
  const [dimensions, setDimensions] = useState<2 | 3>(2);
  const [vectorType, setVectorType] = useState('visual-text');
  const [visualizationData, setVisualizationData] = useState<any>(null);

  // Get available visualization methods
  const { data: methods } = useQuery({
    queryKey: ['visualization-methods'],
    queryFn: async () => {
      const response = await embeddingsAPI.getMethods();
      return response.data;
    },
  });

  // Visualize embeddings mutation
  const visualizeMutation = useMutation({
    mutationFn: (data: any) => embeddingsAPI.visualize(data),
    onSuccess: (response) => {
      setVisualizationData(response.data);
    },
  });

  // Analyze embeddings mutation
  const analyzeMutation = useMutation({
    mutationFn: (data: any) => embeddingsAPI.analyze(data),
  });

  const handleVisualize = () => {
    visualizeMutation.mutate({
      method,
      dimensions,
      vector_type: vectorType,
      limit: 1000,
    });
  };

  const handleAnalyze = () => {
    analyzeMutation.mutate({ vector_type: vectorType });
  };

  const downloadData = () => {
    if (!visualizationData) return;
    const dataStr = JSON.stringify(visualizationData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `embeddings_${method}_${dimensions}d.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Prepare Plotly data
  const getPlotlyData = () => {
    if (!visualizationData?.coordinates) return [];

    const coords = visualizationData.coordinates;
    const labels = visualizationData.labels || [];
    const colors = visualizationData.colors || [];

    if (dimensions === 2) {
      return [
        {
          x: coords.map((c: number[]) => c[0]),
          y: coords.map((c: number[]) => c[1]),
          mode: 'markers',
          type: 'scatter',
          marker: {
            size: 8,
            color: colors.length > 0 ? colors : '#4F46E5',
            opacity: 0.7,
            line: {
              color: 'white',
              width: 1,
            },
          },
          text: labels,
          hovertemplate: '<b>%{text}</b><br>X: %{x:.3f}<br>Y: %{y:.3f}<extra></extra>',
        },
      ];
    } else {
      return [
        {
          x: coords.map((c: number[]) => c[0]),
          y: coords.map((c: number[]) => c[1]),
          z: coords.map((c: number[]) => c[2]),
          mode: 'markers',
          type: 'scatter3d',
          marker: {
            size: 5,
            color: colors.length > 0 ? colors : '#4F46E5',
            opacity: 0.7,
            line: {
              color: 'white',
              width: 0.5,
            },
          },
          text: labels,
          hovertemplate: '<b>%{text}</b><br>X: %{x:.3f}<br>Y: %{y:.3f}<br>Z: %{z:.3f}<extra></extra>',
        },
      ];
    }
  };

  const plotLayout = {
    title: `${method.toUpperCase()} Visualization (${dimensions}D)`,
    autosize: true,
    height: 600,
    hovermode: 'closest',
    paper_bgcolor: '#ffffff',
    plot_bgcolor: '#f9fafb',
    ...(dimensions === 2
      ? {
          xaxis: { title: 'Component 1', gridcolor: '#e5e7eb' },
          yaxis: { title: 'Component 2', gridcolor: '#e5e7eb' },
        }
      : {
          scene: {
            xaxis: { title: 'Component 1', gridcolor: '#e5e7eb' },
            yaxis: { title: 'Component 2', gridcolor: '#e5e7eb' },
            zaxis: { title: 'Component 3', gridcolor: '#e5e7eb' },
          },
        }),
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Embedding Visualization</h1>
        <p className="mt-2 text-sm text-gray-600">
          Explore embedding space with PCA, t-SNE, and UMAP
        </p>
      </div>

      {/* Controls */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Visualization Settings</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Method</label>
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value as VisualizationMethod)}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            >
              <option value="pca">PCA</option>
              <option value="tsne">t-SNE</option>
              <option value="umap">UMAP</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Dimensions</label>
            <select
              value={dimensions}
              onChange={(e) => setDimensions(parseInt(e.target.value) as 2 | 3)}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            >
              <option value="2">2D</option>
              <option value="3">3D</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Vector Type</label>
            <select
              value={vectorType}
              onChange={(e) => setVectorType(e.target.value)}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            >
              <option value="visual-text">Visual-Text</option>
              <option value="visual-image">Visual-Image</option>
              <option value="audio">Audio</option>
            </select>
          </div>

          <div className="flex items-end space-x-2">
            <button
              onClick={handleVisualize}
              disabled={visualizeMutation.isPending}
              className="flex-1 inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              <RefreshCw
                className={`-ml-1 mr-2 h-4 w-4 ${visualizeMutation.isPending ? 'animate-spin' : ''}`}
              />
              Visualize
            </button>
          </div>
        </div>

        <div className="mt-4 flex space-x-2">
          <button
            onClick={handleAnalyze}
            disabled={analyzeMutation.isPending}
            className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            Analyze Embeddings
          </button>
          {visualizationData && (
            <button
              onClick={downloadData}
              className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              <Download className="-ml-1 mr-2 h-4 w-4" />
              Download Data
            </button>
          )}
        </div>
      </div>

      {/* Visualization */}
      {visualizationData && (
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">
              {method.toUpperCase()} Projection
            </h3>
            <div className="text-sm text-gray-500">
              {visualizationData.coordinates?.length || 0} points
            </div>
          </div>
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <Plot
              data={getPlotlyData()}
              layout={plotLayout}
              config={{
                responsive: true,
                displayModeBar: true,
                displaylogo: false,
                modeBarButtonsToRemove: ['lasso2d', 'select2d'],
              }}
              style={{ width: '100%', height: '600px' }}
            />
          </div>
          {visualizationData.explained_variance && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700">
                Explained Variance: {(visualizationData.explained_variance * 100).toFixed(2)}%
              </p>
            </div>
          )}
        </div>
      )}

      {/* Analysis Results */}
      {analyzeMutation.data && (
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Embedding Analysis</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Total Embeddings</p>
              <p className="text-2xl font-semibold text-gray-900 mt-1">
                {analyzeMutation.data.data.analysis?.total_embeddings || 0}
              </p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Dimension</p>
              <p className="text-2xl font-semibold text-gray-900 mt-1">
                {analyzeMutation.data.data.analysis?.dimension || 0}
              </p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Avg Norm</p>
              <p className="text-2xl font-semibold text-gray-900 mt-1">
                {analyzeMutation.data.data.analysis?.avg_norm?.toFixed(3) || 0}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Info Panel */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="text-sm font-medium text-blue-900 mb-2">About Dimensionality Reduction</h4>
        <div className="text-sm text-blue-700 space-y-1">
          <p>
            <strong>PCA:</strong> Fast linear method, preserves global structure
          </p>
          <p>
            <strong>t-SNE:</strong> Non-linear method, preserves local structure, good for clusters
          </p>
          <p>
            <strong>UMAP:</strong> Fast non-linear method, preserves both local and global structure
          </p>
        </div>
      </div>
    </div>
  );
}

