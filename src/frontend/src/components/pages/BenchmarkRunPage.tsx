import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Trophy, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { api } from '../../api/client';
import { toast } from 'react-hot-toast';
import type { BenchmarkResult, BenchmarkProgress } from '../../types/benchmark';

interface LiveMetricData {
  queryNumber: number;
  [backend: string]: number;
}

export const BenchmarkRunPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [benchmark, setBenchmark] = useState<BenchmarkResult | null>(null);
  const [progress, setProgress] = useState<BenchmarkProgress | null>(null);
  const [liveChartData, setLiveChartData] = useState<LiveMetricData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [startTime, setStartTime] = useState<Date>(new Date());

  useEffect(() => {
    if (!id) {
      navigate('/benchmark');
      return;
    }

    loadBenchmark();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (!benchmark || benchmark.status === 'completed' || benchmark.status === 'failed') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        // Fetch progress
        const progressResponse = await api.getBenchmarkProgress(id!);
        setProgress(progressResponse.data);

        // Fetch full results
        const resultsResponse = await api.getBenchmarkResults(id!);
        setBenchmark(resultsResponse.data);

        // Update live chart data
        if (resultsResponse.data.metrics && resultsResponse.data.metrics.length > 0) {
          updateLiveChartData(resultsResponse.data);
        }

        // Check if completed
        if (resultsResponse.data.status === 'completed') {
          toast.success('Benchmark completed!');
          setTimeout(() => {
            navigate(`/benchmark/results/${id}`);
          }, 2000);
        } else if (resultsResponse.data.status === 'failed') {
          toast.error('Benchmark failed');
        }
      } catch (error) {
        console.error('Failed to fetch progress:', error);
      }
    }, 2000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [benchmark, id, navigate]);

  const loadBenchmark = async () => {
    try {
      const response = await api.getBenchmarkResults(id!);
      setBenchmark(response.data);
      setStartTime(new Date(response.data.started_at));
    } catch (error) {
      console.error('Failed to load benchmark:', error);
      toast.error('Failed to load benchmark');
      navigate('/benchmark');
    } finally {
      setIsLoading(false);
    }
  };

  const updateLiveChartData = (benchmarkData: BenchmarkResult) => {
    // Simulate live chart updates based on completed queries
    const dataPoint: LiveMetricData = {
      queryNumber: progress?.completed_queries || 0,
    };

    benchmarkData.metrics.forEach(metric => {
      dataPoint[metric.backend] = metric.avg_latency;
    });

    setLiveChartData(prev => {
      const updated = [...prev, dataPoint];
      return updated.slice(-20); // Keep last 20 data points
    });
  };

  const getElapsedTime = () => {
    const elapsed = Math.floor((Date.now() - startTime.getTime()) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const getEstimatedRemaining = () => {
    if (!progress || progress.progress_percentage === 0) return '~calculating...';

    const elapsed = (Date.now() - startTime.getTime()) / 1000;
    const estimatedTotal = (elapsed / progress.progress_percentage) * 100;
    const remaining = Math.max(0, estimatedTotal - elapsed);

    const minutes = Math.floor(remaining / 60);
    const seconds = Math.floor(remaining % 60);

    if (minutes === 0) {
      return `~${seconds}s`;
    }
    return `~${minutes}m ${seconds}s`;
  };

  const getLeader = () => {
    if (!benchmark?.metrics || benchmark.metrics.length === 0) return null;

    return benchmark.metrics.reduce((best, current) => {
      const completedBest = (best.total_queries - best.failed_queries);
      const completedCurrent = (current.total_queries - current.failed_queries);

      if (completedCurrent === 0) return best;
      if (completedBest === 0) return current;

      return current.avg_latency < best.avg_latency ? current : best;
    });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading benchmark...</p>
        </div>
      </div>
    );
  }

  if (!benchmark) {
    return null;
  }

  const isRunning = benchmark.status === 'running' || benchmark.status === 'pending';
  const leader = getLeader();

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8">
      <div className="max-w-6xl mx-auto space-y-6">
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

          {benchmark.status === 'completed' && (
            <Button onClick={() => navigate(`/benchmark/results/${id}`)}>
              View Full Results
            </Button>
          )}
        </div>

        {/* Status Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-2xl">
                  {isRunning ? 'Running Benchmark' : benchmark.status === 'completed' ? 'Benchmark Completed' : 'Benchmark Failed'}
                </CardTitle>
                <CardDescription>
                  {benchmark.config.backends.join(' vs ')} • {benchmark.config.num_queries} queries
                </CardDescription>
              </div>
              <Badge variant={isRunning ? 'default' : benchmark.status === 'completed' ? 'default' : 'destructive'}>
                {benchmark.status}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-8 text-sm">
              <div>
                <span className="text-gray-600">Elapsed:</span>{' '}
                <span className="font-semibold">{getElapsedTime()}</span>
              </div>
              {isRunning && (
                <div>
                  <span className="text-gray-600">Est. remaining:</span>{' '}
                  <span className="font-semibold">{getEstimatedRemaining()}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Overall Progress */}
        {progress && isRunning && (
          <Card>
            <CardHeader>
              <CardTitle>Overall Progress</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">
                    {progress.message || 'Running benchmark...'}
                  </span>
                  <span className="text-sm font-bold text-gray-900">
                    {progress.progress_percentage.toFixed(0)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4">
                  <div
                    className="bg-gradient-to-r from-indigo-600 to-purple-600 h-4 rounded-full transition-all duration-300"
                    style={{ width: `${progress.progress_percentage}%` }}
                  />
                </div>
                <p className="text-sm text-gray-600 mt-2">
                  {progress.completed_queries} / {progress.total_queries} queries completed
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Backend Status */}
        {benchmark.metrics && benchmark.metrics.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Backend Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {benchmark.metrics.map((metric) => {
                  const completedQueries = metric.total_queries - metric.failed_queries;
                  const progressPercent = (completedQueries / (progress?.total_queries || benchmark.config.num_queries)) * 100;
                  const isLeader = leader?.backend === metric.backend;

                  return (
                    <div key={metric.backend} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-gray-900">{metric.backend}</span>
                          {isLeader && (
                            <Trophy className="h-4 w-4 text-yellow-500" />
                          )}
                        </div>
                        <span className="text-sm font-medium text-gray-700">
                          {progressPercent.toFixed(0)}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all duration-300 ${
                            isLeader ? 'bg-yellow-500' : 'bg-indigo-600'
                          }`}
                          style={{ width: `${progressPercent}%` }}
                        />
                      </div>
                      <div className="flex items-center gap-4 text-xs text-gray-600">
                        <span>{completedQueries}/{metric.total_queries} queries</span>
                        {completedQueries > 0 && (
                          <>
                            <span>•</span>
                            <span>Avg: {metric.avg_latency.toFixed(2)}ms</span>
                            <span>•</span>
                            <span className="flex items-center gap-1">
                              Success: {(metric.success_rate * 100).toFixed(1)}%
                              {metric.success_rate === 1 ? (
                                <CheckCircle className="h-3 w-3 text-green-600" />
                              ) : metric.success_rate < 0.8 ? (
                                <XCircle className="h-3 w-3 text-red-600" />
                              ) : (
                                <AlertCircle className="h-3 w-3 text-yellow-600" />
                              )}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Live Metrics Chart */}
        {liveChartData.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Live Latency Comparison</CardTitle>
              <CardDescription>
                Average latency updated in real-time
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={liveChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="queryNumber"
                    label={{ value: 'Queries Completed', position: 'insideBottom', offset: -5 }}
                  />
                  <YAxis
                    label={{ value: 'Latency (ms)', angle: -90, position: 'insideLeft' }}
                  />
                  <Tooltip />
                  <Legend />
                  {benchmark.config.backends.map((backend, index) => {
                    const colors = ['#8884d8', '#82ca9d', '#ffc658', '#ff7c7c'];
                    return (
                      <Line
                        key={backend}
                        type="monotone"
                        dataKey={backend}
                        stroke={colors[index % colors.length]}
                        strokeWidth={2}
                        dot={{ r: 3 }}
                        activeDot={{ r: 5 }}
                      />
                    );
                  })}
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* Info Alert */}
        {isRunning && (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Don't close this window - results are being saved automatically
            </AlertDescription>
          </Alert>
        )}
      </div>
    </div>
  );
};
