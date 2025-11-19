import React, { useState } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { BackendSelector } from './components/BackendSelector';
import { SearchInterface } from './components/SearchInterface';
import { ResultsGrid, type SearchResult } from './components/ResultsGrid';
import { VideoPlayer } from './components/VideoPlayer';
import { VisualizationPanel } from './components/VisualizationPanel';
import { api } from './api/client';

// Helper to generate a dummy vector for testing since backend requires vector
const generateDummyVector = (dim: number = 1024): number[] => {
  return Array.from({ length: dim }, () => Math.random());
};

function App() {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [showPlayer, setShowPlayer] = useState(false);

  const handleSearch = async (query: string, type: 'text' | 'image') => {
    setIsSearching(true);
    try {
      // In a real application, we would call an embedding service here
      // to convert the text/image query into a vector.
      // For now, we generate a dummy vector to satisfy the backend contract.
      console.log(`Searching for "${query}" (${type})`);
      const dummyVector = generateDummyVector(1024);
      
      const response = await api.search({
        query_vector: dummyVector,
        top_k: 12
      });
      
      if (response.data && response.data.results) {
        setResults(response.data.results);
        toast.success(`Found ${response.data.results.length} results`);
      } else {
        setResults([]);
        toast('No results found', { icon: 'ℹ️' });
      }
    } catch (error) {
      console.error('Search failed:', error);
      toast.error('Search failed. Please try again.');
    } finally {
      setIsSearching(false);
    }
  };

  const handlePlaySegment = (result: SearchResult) => {
    setSelectedResult(result);
    setShowPlayer(true);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Toaster position="top-right" />
      
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-indigo-600">VideoLake</h1>
              <span className="ml-2 text-sm text-gray-500 hidden sm:inline-block">
                Multi-modal Video Search
              </span>
            </div>
            <BackendSelector />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Search Section */}
        <section className="text-center space-y-4">
          <h2 className="text-3xl font-extrabold text-gray-900 sm:text-4xl">
            Find moments in your videos
          </h2>
          <p className="max-w-2xl mx-auto text-xl text-gray-500">
            Search using natural language or images to find exact timestamps.
          </p>
          <SearchInterface onSearch={handleSearch} isLoading={isSearching} />
        </section>

        {/* Visualization Section */}
        <section>
          <VisualizationPanel />
        </section>

        {/* Results Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">Search Results</h3>
            <span className="text-sm text-gray-500">
              {results.length > 0 ? `${results.length} results found` : ''}
            </span>
          </div>
          <ResultsGrid results={results} onPlaySegment={handlePlaySegment} />
        </section>
      </main>

      {/* Video Player Modal */}
      {showPlayer && selectedResult && (
        <div className="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true" onClick={() => setShowPlayer(false)}></div>

            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                    <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4" id="modal-title">
                      {selectedResult.metadata.s3_uri?.split('/').pop() || 'Video Playback'}
                    </h3>
                    <VideoPlayer 
                      videoUrl={selectedResult.metadata.s3_uri || ''} // Note: In real app, this needs to be a signed URL
                      startTime={selectedResult.metadata.start_time}
                      endTime={selectedResult.metadata.end_time}
                      autoPlay={true}
                    />
                    <div className="mt-4 text-sm text-gray-500">
                      <p>Score: {(selectedResult.score * 100).toFixed(2)}%</p>
                      <p>Time: {selectedResult.metadata.start_time?.toFixed(2)}s - {selectedResult.metadata.end_time?.toFixed(2)}s</p>
                      {selectedResult.metadata.text && <p className="mt-2 italic">"{selectedResult.metadata.text}"</p>}
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button 
                  type="button" 
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                  onClick={() => setShowPlayer(false)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
