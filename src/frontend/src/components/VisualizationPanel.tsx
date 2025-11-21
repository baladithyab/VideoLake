import React, { useMemo } from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { SearchResult } from './ResultsGrid';

interface VisualizationPanelProps {
  results: SearchResult[];
  onPointClick: (result: SearchResult) => void;
}

export const VisualizationPanel: React.FC<VisualizationPanelProps> = ({ results, onPointClick }) => {
  // Generate pseudo-coordinates based on score and ID hash for visualization
  // In a real app, these would come from dimensionality reduction (t-SNE/PCA) on the backend
  const data = useMemo(() => {
    return results.map((result, index) => {
      // Simple pseudo-random projection based on string hash
      const hash = result.id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
      const x = (hash % 100) + (Math.random() * 10 - 5); // Add some jitter
      const y = result.score * 100; // Use score as Y axis to show relevance
      
      return {
        x,
        y,
        z: 1,
        result // Keep reference to original result
      };
    });
  }, [results]);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-2 border border-gray-200 shadow-lg rounded text-xs">
          <p className="font-semibold">{data.result.metadata.s3_uri?.split('/').pop()}</p>
          <p>Score: {(data.result.score * 100).toFixed(1)}%</p>
          <p>Time: {data.result.metadata.start_time?.toFixed(1)}s</p>
        </div>
      );
    }
    return null;
  };

  if (results.length === 0) {
    return null;
  }

  return (
    <div className="bg-white p-4 rounded-lg shadow-md">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Result Distribution</h3>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart
            margin={{
              top: 20,
              right: 20,
              bottom: 20,
              left: 20,
            }}
          >
            <CartesianGrid />
            <XAxis type="number" dataKey="x" name="Cluster" unit="" tick={false} />
            <YAxis type="number" dataKey="y" name="Relevance" unit="%" domain={[0, 100]} />
            <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
            <Scatter name="Results" data={data} fill="#8884d8" onClick={(data) => onPointClick(data.payload.result)}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.y > 80 ? '#4f46e5' : '#818cf8'} cursor="pointer" />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <p className="text-sm text-gray-500 mt-2 text-center">
        Click on a point to play the video segment. Y-axis represents relevance score.
      </p>
    </div>
  );
};