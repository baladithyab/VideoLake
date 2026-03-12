import React, { useState } from 'react';
import { Search, Filter, Image as ImageIcon, Mic, Video } from 'lucide-react';
import { SearchInterface } from '../SearchInterface';
import { ResultsGrid, type SearchResult } from '../ResultsGrid';
import { VideoPlayer } from '../VideoPlayer';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { api } from '../../api/client';
import { toast } from 'react-hot-toast';

type SearchMode = 'text' | 'image' | 'audio';

export const DemoSearchPage: React.FC = () => {
  const [searchMode, setSearchMode] = useState<SearchMode>('text');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);
  const [selectedBackend, setSelectedBackend] = useState('s3_vector');
  const [searchQuery, setSearchQuery] = useState('');
  const [scoreFilter, setScoreFilter] = useState<[number, number]>([0, 100]);
  const [showFilters, setShowFilters] = useState(false);

  const availableBackends = [
    { value: 's3_vector', label: 'S3 Vector', deployed: true },
    { value: 'lancedb', label: 'LanceDB', deployed: false },
    { value: 'qdrant', label: 'Qdrant', deployed: false },
    { value: 'opensearch', label: 'OpenSearch', deployed: false }
  ];

  const handleSearch = async (query: string, type: 'text' | 'image', backend: string) => {
    setIsLoading(true);
    setSearchQuery(query);

    try {
      const response = await api.searchQuery({
        query_text: query,
        backend: backend,
        top_k: 50
      });

      // Transform API response to SearchResult format
      const transformedResults: SearchResult[] = response.data.results?.map((result: { id?: string; score?: number; metadata?: Record<string, unknown> }, index: number) => ({
        id: result.id || `result-${index}`,
        score: result.score || 0,
        metadata: {
          s3_uri: result.metadata?.s3_uri,
          start_time: result.metadata?.start_time,
          end_time: result.metadata?.end_time,
          thumbnail_url: result.metadata?.thumbnail_url,
          text: result.metadata?.text,
          ...result.metadata
        }
      })) || [];

      setResults(transformedResults);

      if (transformedResults.length === 0) {
        toast.success('Search completed - no results found');
      } else {
        toast.success(`Found ${transformedResults.length} results`);
      }
    } catch (error) {
      console.error('Search failed:', error);
      toast.error('Search failed. Please try again.');
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePlaySegment = (result: SearchResult) => {
    setSelectedResult(result);
    // Scroll to player
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleClosePlayer = () => {
    setSelectedResult(null);
  };

  const filteredResults = results.filter(result => {
    const scorePercent = result.score * 100;
    return scorePercent >= scoreFilter[0] && scorePercent <= scoreFilter[1];
  });

  const exampleQueries = [
    "sunset over water",
    "people playing basketball",
    "car chase scene",
    "person running on beach",
    "cooking in kitchen",
    "mountain landscape"
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              VideoLake Search
            </h1>
            <p className="text-gray-600">
              Multi-modal video content discovery
            </p>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Video Player (when a result is selected) */}
        {selectedResult && (
          <Card className="mb-8">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Playing Matched Segment</CardTitle>
                <Button variant="outline" size="sm" onClick={handleClosePlayer}>
                  Close Player
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <VideoPlayer
                videoUrl={selectedResult.metadata.s3_uri || ''}
                startTime={selectedResult.metadata.start_time}
                endTime={selectedResult.metadata.end_time}
                autoPlay={true}
              />
              <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                <h3 className="font-medium text-gray-900 mb-2">Match Details</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">Score:</span>
                    <Badge variant="default" className="bg-green-500">
                      {(selectedResult.score * 100).toFixed(1)}%
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">Query:</span>
                    <span className="text-gray-900 font-medium">{searchQuery}</span>
                  </div>
                  {selectedResult.metadata.text && (
                    <div>
                      <span className="text-gray-600">Transcript:</span>
                      <p className="text-gray-900 mt-1 italic">"{selectedResult.metadata.text}"</p>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Search Panel */}
        <Card className="mb-8">
          <CardContent className="pt-6">
            {/* Search Mode Selector */}
            <div className="flex items-center justify-center space-x-4 mb-6">
              <span className="text-sm font-medium text-gray-700">Search Mode:</span>
              <div className="flex space-x-2">
                <Button
                  variant={searchMode === 'text' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSearchMode('text')}
                >
                  <Search className="h-4 w-4 mr-2" />
                  Text
                </Button>
                <Button
                  variant={searchMode === 'image' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSearchMode('image')}
                  disabled
                >
                  <ImageIcon className="h-4 w-4 mr-2" />
                  Image (Soon)
                </Button>
                <Button
                  variant={searchMode === 'audio' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSearchMode('audio')}
                  disabled
                >
                  <Mic className="h-4 w-4 mr-2" />
                  Audio (Soon)
                </Button>
              </div>
            </div>

            {/* Search Interface */}
            <SearchInterface
              onSearch={handleSearch}
              isLoading={isLoading}
              availableBackends={availableBackends}
              selectedBackend={selectedBackend}
              onBackendChange={setSelectedBackend}
            />

            {/* Example Queries */}
            {results.length === 0 && !isLoading && (
              <div className="mt-6 text-center">
                <p className="text-sm text-gray-600 mb-3">Try these example searches:</p>
                <div className="flex flex-wrap justify-center gap-2">
                  {exampleQueries.map((query) => (
                    <Button
                      key={query}
                      variant="outline"
                      size="sm"
                      onClick={() => handleSearch(query, 'text', selectedBackend)}
                      className="text-xs"
                    >
                      "{query}"
                    </Button>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Results Section */}
        {(results.length > 0 || isLoading) && (
          <div>
            {/* Results Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-4">
                <h2 className="text-xl font-semibold text-gray-900">
                  {isLoading ? (
                    'Searching...'
                  ) : (
                    <>
                      {filteredResults.length} result{filteredResults.length !== 1 ? 's' : ''} found
                      {results.length !== filteredResults.length && (
                        <span className="text-gray-500 text-sm ml-2">
                          ({results.length - filteredResults.length} filtered)
                        </span>
                      )}
                    </>
                  )}
                </h2>
                {!isLoading && (
                  <Badge variant="secondary" className="text-xs">
                    Backend: {availableBackends.find(b => b.value === selectedBackend)?.label}
                  </Badge>
                )}
              </div>

              {/* Filters Toggle */}
              {results.length > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowFilters(!showFilters)}
                >
                  <Filter className="h-4 w-4 mr-2" />
                  Filters
                </Button>
              )}
            </div>

            {/* Filter Panel */}
            {showFilters && (
              <Card className="mb-6">
                <CardContent className="pt-6">
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Minimum Score: {scoreFilter[0]}%
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={scoreFilter[0]}
                        onChange={(e) => setScoreFilter([parseInt(e.target.value), scoreFilter[1]])}
                        className="w-full"
                      />
                    </div>
                    <div className="flex items-center space-x-2 text-sm text-gray-600">
                      <Video className="h-4 w-4" />
                      <span>Showing video segments with {scoreFilter[0]}% - {scoreFilter[1]}% match</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Results Grid */}
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
              </div>
            ) : (
              <ResultsGrid results={filteredResults} onPlaySegment={handlePlaySegment} />
            )}
          </div>
        )}
      </div>
    </div>
  );
};
