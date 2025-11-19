import React from 'react';
import { Play, Clock } from 'lucide-react';

export interface SearchResult {
  id: string;
  score: number;
  metadata: {
    s3_uri?: string;
    start_time?: number;
    end_time?: number;
    thumbnail_url?: string;
    text?: string;
    [key: string]: any;
  };
}

interface ResultsGridProps {
  results: SearchResult[];
  onPlaySegment: (result: SearchResult) => void;
}

export const ResultsGrid: React.FC<ResultsGridProps> = ({ results, onPlaySegment }) => {
  if (!results || results.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        No results found. Try a different search query.
      </div>
    );
  }

  const formatTime = (seconds?: number) => {
    if (seconds === undefined) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 p-4">
      {results.map((result, index) => (
        <div key={result.id || index} className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow">
          <div className="relative aspect-video bg-gray-200">
            {result.metadata.thumbnail_url ? (
              <img 
                src={result.metadata.thumbnail_url} 
                alt={`Result ${index + 1}`} 
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400">
                <Play size={48} />
              </div>
            )}
            <div className="absolute bottom-2 right-2 bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded">
              {formatTime(result.metadata.start_time)} - {formatTime(result.metadata.end_time)}
            </div>
          </div>
          
          <div className="p-4">
            <div className="flex justify-between items-start mb-2">
              <h3 className="text-lg font-medium text-gray-900 truncate" title={result.metadata.s3_uri}>
                {result.metadata.s3_uri?.split('/').pop() || 'Unknown Video'}
              </h3>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                {(result.score * 100).toFixed(1)}%
              </span>
            </div>
            
            {result.metadata.text && (
              <p className="text-sm text-gray-500 mb-4 line-clamp-2">
                {result.metadata.text}
              </p>
            )}
            
            <button
              onClick={() => onPlaySegment(result)}
              className="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              <Play className="mr-2 h-4 w-4" />
              Play Segment
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};