import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, History, Clock, Trophy, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { api } from '../../api/client';
import type { BenchmarkResult } from '../../types/benchmark';

export const BenchmarkHubPage: React.FC = () => {
  const navigate = useNavigate();
  const [recentBenchmarks, setRecentBenchmarks] = useState<BenchmarkResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadRecentBenchmarks();
  }, []);

  const loadRecentBenchmarks = async () => {
    try {
      const response = await api.listBenchmarks();
      // Get the 3 most recent completed benchmarks
      const completed = response.data
        .filter(b => b.status === 'completed')
        .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())
        .slice(0, 3);
      setRecentBenchmarks(completed);
    } catch (error) {
      console.error('Failed to load benchmark history:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getWinner = (benchmark: BenchmarkResult) => {
    if (!benchmark.metrics || benchmark.metrics.length === 0) return null;

    return benchmark.metrics.reduce((best, current) =>
      current.avg_latency < best.avg_latency ? current : best
    );
  };

  const getSpeedImprovement = (benchmark: BenchmarkResult) => {
    if (!benchmark.metrics || benchmark.metrics.length < 2) return null;

    const sorted = [...benchmark.metrics].sort((a, b) => a.avg_latency - b.avg_latency);
    const fastest = sorted[0];
    const slowest = sorted[sorted.length - 1];

    const improvement = ((slowest.avg_latency - fastest.avg_latency) / slowest.avg_latency) * 100;
    return Math.round(improvement);
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

  const totalBenchmarks = recentBenchmarks.length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Performance Benchmarking
          </h1>
          <p className="text-lg text-gray-600">
            Compare search performance across different vector store backends
          </p>
        </div>

        {/* Action Cards */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* New Benchmark Card */}
          <Card className="hover:shadow-lg transition-shadow cursor-pointer border-2 border-transparent hover:border-indigo-500">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="h-12 w-12 rounded-lg bg-indigo-100 flex items-center justify-center">
                  <Play className="h-6 w-6 text-indigo-600" />
                </div>
                <ArrowRight className="h-5 w-5 text-gray-400" />
              </div>
              <CardTitle className="mt-4">New Benchmark</CardTitle>
              <CardDescription>
                Configure and run a new performance test
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                onClick={() => navigate('/benchmark/configure')}
                className="w-full"
                size="lg"
              >
                Start Benchmark
              </Button>
            </CardContent>
          </Card>

          {/* View History Card */}
          <Card className="hover:shadow-lg transition-shadow cursor-pointer border-2 border-transparent hover:border-emerald-500">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="h-12 w-12 rounded-lg bg-emerald-100 flex items-center justify-center">
                  <History className="h-6 w-6 text-emerald-600" />
                </div>
                <ArrowRight className="h-5 w-5 text-gray-400" />
              </div>
              <CardTitle className="mt-4">View History</CardTitle>
              <CardDescription>
                {isLoading ? 'Loading...' : `${totalBenchmarks} completed benchmarks`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                onClick={() => navigate('/history')}
                variant="outline"
                className="w-full"
                size="lg"
              >
                Browse History
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Recent Benchmarks */}
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Recent Benchmarks</h2>

          {isLoading ? (
            <Card>
              <CardContent className="py-12">
                <div className="text-center text-gray-500">
                  Loading recent benchmarks...
                </div>
              </CardContent>
            </Card>
          ) : recentBenchmarks.length === 0 ? (
            <Card>
              <CardContent className="py-12">
                <div className="text-center">
                  <Clock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600 mb-2">No benchmarks yet</p>
                  <p className="text-sm text-gray-500">
                    Start your first benchmark to see results here
                  </p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {recentBenchmarks.map((benchmark) => {
                const winner = getWinner(benchmark);
                const improvement = getSpeedImprovement(benchmark);

                return (
                  <Card
                    key={benchmark.id}
                    className="hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => navigate(`/benchmark/results/${benchmark.id}`)}
                  >
                    <CardContent className="py-6">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <span className="text-sm text-gray-500">
                              {formatDate(benchmark.started_at)}
                            </span>
                            <Badge variant="outline">
                              {benchmark.config.backends.join(' vs ')}
                            </Badge>
                            <Badge variant="secondary">
                              {benchmark.config.num_queries} queries
                            </Badge>
                          </div>

                          {winner && (
                            <div className="flex items-center gap-2 mt-2">
                              <Trophy className="h-4 w-4 text-yellow-600" />
                              <span className="font-medium text-gray-900">
                                Winner: {winner.backend}
                              </span>
                              {improvement && (
                                <span className="text-sm text-gray-600">
                                  ({improvement}% faster)
                                </span>
                              )}
                            </div>
                          )}
                        </div>

                        <Button variant="ghost" size="sm">
                          View Results
                          <ArrowRight className="ml-2 h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
