import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { searchAPI } from '../api/client';
import { Search, Play } from 'lucide-react';

export default function QuerySearch() {
  const navigate = useNavigate();
  const [queryText, setQueryText] = useState('');
  const [vectorTypes, setVectorTypes] = useState(['visual-text', 'visual-image', 'audio']);
  const [results, setResults] = useState<any>(null);

  const searchMutation = useMutation({
    mutationFn: (data: { query_text: string; vector_types: string[]; top_k: number }) =>
      searchAPI.multiVector(data),
    onSuccess: (response) => {
      setResults(response.data);
      // Store results in localStorage for ResultsPlayback page
      localStorage.setItem('searchResults', JSON.stringify(response.data));
    },
  });

  const handleSearch = () => {
    if (!queryText) return;
    searchMutation.mutate({ query_text: queryText, vector_types: vectorTypes, top_k: 10 });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Query & Search</h1>
        <p className="mt-2 text-sm text-gray-600">
          Multi-modal search with Marengo 2.7
        </p>
      </div>

      {/* Search Input */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Search Query</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Query Text</label>
            <textarea
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              rows={3}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="Enter your search query..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Vector Types</label>
            <div className="space-y-2">
              {['visual-text', 'visual-image', 'audio'].map((type) => (
                <label key={type} className="inline-flex items-center mr-4">
                  <input
                    type="checkbox"
                    checked={vectorTypes.includes(type)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setVectorTypes([...vectorTypes, type]);
                      } else {
                        setVectorTypes(vectorTypes.filter((t) => t !== type));
                      }
                    }}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">{type}</span>
                </label>
              ))}
            </div>
          </div>

          <button
            onClick={handleSearch}
            disabled={!queryText || searchMutation.isPending}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            <Search className="-ml-1 mr-2 h-5 w-5" />
            Search
          </button>
        </div>
      </div>

      {/* Results */}
      {results && (
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">Search Results</h3>
            <button
              onClick={() => navigate('/results')}
              className="inline-flex items-center px-3 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              <Play className="-ml-1 mr-2 h-4 w-4" />
              View in Player
            </button>
          </div>
          <div className="space-y-3">
            {results.results?.map((result: any, index: number) => (
              <div key={index} className="border border-gray-200 rounded-md p-4 hover:border-indigo-300 transition-colors">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">Result {index + 1}</p>
                    <p className="text-sm text-gray-500 mt-1">Score: {result.score?.toFixed(4)}</p>
                    <p className="text-sm text-gray-500">Type: {result.vector_type}</p>
                    {result.metadata && (
                      <div className="mt-2 text-xs text-gray-400">
                        <pre className="whitespace-pre-wrap">{JSON.stringify(result.metadata, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex justify-between items-center">
            <div className="text-sm text-gray-500">
              Query time: {results.query_time_ms}ms | Total results: {results.total_results}
            </div>
            <button
              onClick={() => navigate('/results')}
              className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
            >
              Open in Video Player →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

