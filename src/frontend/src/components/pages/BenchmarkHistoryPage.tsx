import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Trophy, Clock, CheckSquare, Square } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { api } from '../../api/client';
import { toast } from 'react-hot-toast';
import type { BenchmarkResult } from '../../types/benchmark';

type SortField = 'date' | 'queries' | 'backends';
type SortOrder = 'asc' | 'desc';

export const BenchmarkHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [benchmarks, setBenchmarks] = useState<BenchmarkResult[]>([]);
  const [filteredBenchmarks, setFilteredBenchmarks] = useState<BenchmarkResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [selectedBenchmarks, setSelectedBenchmarks] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadBenchmarks();
  }, []);

  useEffect(() => {
    applyFiltersAndSort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [benchmarks, searchQuery, sortField, sortOrder]);

  const loadBenchmarks = async () => {
    try {
      const response = await api.listBenchmarks();
      const completed = response.data.filter(b => b.status === 'completed');
      setBenchmarks(completed);
    } catch (error) {
      console.error('Failed to load benchmarks:', error);
      toast.error('Failed to load benchmark history');
    } finally {
      setIsLoading(false);
    }
  };

  const applyFiltersAndSort = () => {
    let filtered = [...benchmarks];

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(b =>
        b.config.backends.some(backend => backend.toLowerCase().includes(query)) ||
        b.id.toLowerCase().includes(query)
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let comparison = 0;

      switch (sortField) {
        case 'date':
          comparison = new Date(a.started_at).getTime() - new Date(b.started_at).getTime();
          break;
        case 'queries':
          comparison = a.config.num_queries - b.config.num_queries;
          break;
        case 'backends':
          comparison = a.config.backends.length - b.config.backends.length;
          break;
      }

      return sortOrder === 'asc' ? comparison : -comparison;
    });

    setFilteredBenchmarks(filtered);
  };

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const toggleBenchmarkSelection = (id: string) => {
    const newSelection = new Set(selectedBenchmarks);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedBenchmarks(newSelection);
  };

  const selectAll = () => {
    if (selectedBenchmarks.size === filteredBenchmarks.length) {
      setSelectedBenchmarks(new Set());
    } else {
      setSelectedBenchmarks(new Set(filteredBenchmarks.map(b => b.id)));
    }
  };

  const handleCompare = () => {
    if (selectedBenchmarks.size < 2) {
      toast.error('Select at least 2 benchmarks to compare');
      return;
    }

    const ids = Array.from(selectedBenchmarks).join(',');
    navigate(`/history/compare?ids=${ids}`);
  };

  const getWinner = (benchmark: BenchmarkResult) => {
    if (!benchmark.metrics || benchmark.metrics.length === 0) return null;

    return benchmark.metrics.reduce((best, current) =>
      current.avg_latency < best.avg_latency ? current : best
    );
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    }).format(date);
  };

  const getRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return `${Math.floor(diffDays / 30)} months ago`;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading history...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
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

          {selectedBenchmarks.size > 0 && (
            <Button
              onClick={handleCompare}
              disabled={selectedBenchmarks.size < 2}
            >
              Compare Selected ({selectedBenchmarks.size})
            </Button>
          )}
        </div>

        {/* Header Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-3xl">Benchmark History</CardTitle>
            <CardDescription>
              Browse and compare past benchmark results
            </CardDescription>
          </CardHeader>
        </Card>

        {/* Filters and Search */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <Input
                  placeholder="Search by backend or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="max-w-md"
                />
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => toggleSort('date')}
                >
                  <Clock className="h-4 w-4 mr-2" />
                  Date {sortField === 'date' && (sortOrder === 'asc' ? '↑' : '↓')}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => toggleSort('queries')}
                >
                  Queries {sortField === 'queries' && (sortOrder === 'asc' ? '↑' : '↓')}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => toggleSort('backends')}
                >
                  Backends {sortField === 'backends' && (sortOrder === 'asc' ? '↑' : '↓')}
                </Button>
              </div>

              {filteredBenchmarks.length > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={selectAll}
                >
                  {selectedBenchmarks.size === filteredBenchmarks.length ? (
                    <CheckSquare className="h-4 w-4 mr-2" />
                  ) : (
                    <Square className="h-4 w-4 mr-2" />
                  )}
                  {selectedBenchmarks.size === filteredBenchmarks.length ? 'Deselect All' : 'Select All'}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Results Count */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-600">
            {filteredBenchmarks.length} {filteredBenchmarks.length === 1 ? 'benchmark' : 'benchmarks'} found
            {searchQuery && ` for "${searchQuery}"`}
          </p>
        </div>

        {/* Benchmark List */}
        {filteredBenchmarks.length === 0 ? (
          <Card>
            <CardContent className="py-12">
              <div className="text-center">
                <Clock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600 mb-2">
                  {searchQuery ? 'No benchmarks found' : 'No benchmarks yet'}
                </p>
                <p className="text-sm text-gray-500">
                  {searchQuery ? 'Try a different search query' : 'Start your first benchmark to see it here'}
                </p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {filteredBenchmarks.map((benchmark) => {
              const winner = getWinner(benchmark);
              const isSelected = selectedBenchmarks.has(benchmark.id);

              return (
                <Card
                  key={benchmark.id}
                  className={`hover:shadow-md transition-all cursor-pointer ${
                    isSelected ? 'ring-2 ring-indigo-500 bg-indigo-50' : ''
                  }`}
                >
                  <CardContent className="py-6">
                    <div className="flex items-start gap-4">
                      {/* Selection Checkbox */}
                      <div className="pt-1">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleBenchmarkSelection(benchmark.id)}
                          className="h-5 w-5 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded cursor-pointer"
                          onClick={(e) => e.stopPropagation()}
                        />
                      </div>

                      {/* Main Content */}
                      <div
                        className="flex-1"
                        onClick={() => navigate(`/benchmark/results/${benchmark.id}`)}
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="space-y-2">
                            <div className="flex items-center gap-3">
                              <span className="text-sm text-gray-500">
                                {formatDate(benchmark.started_at)}
                              </span>
                              <Badge variant="outline">
                                {getRelativeTime(benchmark.started_at)}
                              </Badge>
                            </div>

                            <div className="flex items-center gap-2">
                              {benchmark.config.backends.map(backend => (
                                <Badge key={backend} variant="secondary">
                                  {backend}
                                </Badge>
                              ))}
                              <span className="text-sm text-gray-600">
                                • {benchmark.config.num_queries} queries
                              </span>
                            </div>
                          </div>

                          <Button variant="ghost" size="sm">
                            View Details
                          </Button>
                        </div>

                        {winner && (
                          <div className="flex items-center gap-6 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                            <div className="flex items-center gap-2">
                              <Trophy className="h-5 w-5 text-yellow-600" />
                              <span className="font-semibold text-gray-900">
                                Winner: {winner.backend}
                              </span>
                            </div>
                            <div className="flex items-center gap-6 text-sm text-gray-700">
                              <div>
                                <span className="font-semibold">{winner.avg_latency.toFixed(2)}ms</span> avg latency
                              </div>
                              <div>
                                <span className="font-semibold">{winner.throughput.toFixed(2)} q/s</span> throughput
                              </div>
                              <div>
                                <span className="font-semibold">{(winner.success_rate * 100).toFixed(1)}%</span> success
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Action Bar */}
        {selectedBenchmarks.size > 0 && (
          <Card className="sticky bottom-4 border-2 border-indigo-500 shadow-lg">
            <CardContent className="py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckSquare className="h-5 w-5 text-indigo-600" />
                  <span className="font-semibold">
                    {selectedBenchmarks.size} benchmark{selectedBenchmarks.size > 1 ? 's' : ''} selected
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setSelectedBenchmarks(new Set())}
                  >
                    Clear Selection
                  </Button>
                  <Button
                    onClick={handleCompare}
                    disabled={selectedBenchmarks.size < 2}
                  >
                    Compare Benchmarks
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};
