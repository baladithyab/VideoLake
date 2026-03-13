import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Trophy, Download, Share2 } from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { useBenchmark } from '../../contexts/BenchmarkContext';
import { toast } from 'react-hot-toast';
import type { BenchmarkResult } from '../../types/benchmark';

export const BenchmarkResultsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { getBenchmark } = useBenchmark();
  const [benchmark, setBenchmark] = useState<BenchmarkResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!id) {
      navigate('/benchmark');
      return;
    }

    const loadBenchmark = async () => {
      try {
        const result = await getBenchmark(id);
        setBenchmark(result);

        if (result.status !== 'completed') {
          // Redirect to run page if still running
          navigate(`/benchmark/run/${id}`);
        }
      } catch (error) {
        console.error('Failed to load benchmark:', error);
        toast.error('Failed to load benchmark results');
        navigate('/benchmark');
      } finally {
        setIsLoading(false);
      }
    };

    loadBenchmark();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const getWinner = () => {
    if (!benchmark?.metrics || benchmark.metrics.length === 0) return null;

    return benchmark.metrics.reduce((best, current) =>
      current.avg_latency < best.avg_latency ? current : best
    );
  };

  const getSpeedImprovement = () => {
    if (!benchmark?.metrics || benchmark.metrics.length < 2) return null;

    const sorted = [...benchmark.metrics].sort((a, b) => a.avg_latency - b.avg_latency);
    const fastest = sorted[0];
    const slowest = sorted[sorted.length - 1];

    return ((slowest.avg_latency - fastest.avg_latency) / slowest.avg_latency) * 100;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    }).format(date);
  };

  const getRuntime = () => {
    if (!benchmark?.started_at || !benchmark?.completed_at) return 'N/A';

    const start = new Date(benchmark.started_at).getTime();
    const end = new Date(benchmark.completed_at).getTime();
    const seconds = Math.floor((end - start) / 1000);

    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;

    return `${minutes}m ${remainingSeconds}s`;
  };

  const handleExport = () => {
    if (!benchmark) return;

    const dataStr = JSON.stringify(benchmark, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
    const exportFileDefaultName = `benchmark-${benchmark.id}-results.json`;

    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();

    toast.success('Results exported successfully');
  };

  const handleShare = () => {
    const url = window.location.href;
    navigator.clipboard.writeText(url);
    toast.success('Link copied to clipboard');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading results...</p>
        </div>
      </div>
    );
  }

  if (!benchmark) {
    return null;
  }

  const winner = getWinner();
  const improvement = getSpeedImprovement();

  // Prepare chart data
  const latencyChartData = benchmark.metrics.map(m => ({
    backend: m.backend,
    'Avg Latency': m.avg_latency,
    'P95 Latency': m.p95_latency,
    'P99 Latency': m.p99_latency,
  }));

  const throughputChartData = benchmark.metrics.map(m => ({
    backend: m.backend,
    'Throughput (q/s)': m.throughput,
  }));

  const percentileData = benchmark.metrics.map(m => ({
    backend: m.backend,
    P50: m.avg_latency,
    P95: m.p95_latency,
    P99: m.p99_latency,
  }));

  return (
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

          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleShare}>
              <Share2 className="h-4 w-4 mr-2" />
              Share
            </Button>
            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </div>

        {/* Hero Section */}
        <Card className="border-2">
          <CardHeader>
            <div className="space-y-2">
              <CardTitle className="text-3xl">
                Benchmark Results
              </CardTitle>
              <CardDescription className="text-base">
                {formatDate(benchmark.started_at)} • Runtime: {getRuntime()}
              </CardDescription>
              <div className="flex items-center gap-2 pt-2">
                {benchmark.config.backends.map(backend => (
                  <Badge key={backend} variant="outline">{backend}</Badge>
                ))}
                <Badge variant="secondary">{benchmark.config.num_queries} queries</Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {winner && (
              <div className="bg-gradient-to-r from-yellow-50 to-orange-50 border-2 border-yellow-500 rounded-lg p-6">
                <div className="flex items-center gap-3 mb-2">
                  <Trophy className="h-8 w-8 text-yellow-600" />
                  <div>
                    <div className="text-2xl font-bold text-gray-900">
                      Winner: {winner.backend}
                    </div>
                    {improvement && (
                      <div className="text-lg text-gray-700">
                        {improvement.toFixed(0)}% faster average latency
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-6 mt-4 text-sm text-gray-700">
                  <div>
                    <span className="font-semibold">{winner.avg_latency.toFixed(2)}ms</span> avg latency
                  </div>
                  <div>
                    <span className="font-semibold">{winner.throughput.toFixed(2)} q/s</span> throughput
                  </div>
                  <div>
                    <span className="font-semibold">{(winner.success_rate * 100).toFixed(1)}%</span> success rate
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Key Metrics Grid */}
        <div className="grid md:grid-cols-3 gap-6">
          {benchmark.metrics.map((metric) => (
            <Card key={metric.backend}>
              <CardHeader>
                <CardTitle className="text-lg">{metric.backend}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="text-3xl font-bold text-indigo-600">
                    {metric.avg_latency.toFixed(2)}ms
                  </div>
                  <div className="text-sm text-gray-600">Average Latency</div>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="font-semibold">{metric.throughput.toFixed(2)} q/s</div>
                    <div className="text-gray-600">Throughput</div>
                  </div>
                  <div>
                    <div className="font-semibold">{(metric.success_rate * 100).toFixed(1)}%</div>
                    <div className="text-gray-600">Success Rate</div>
                  </div>
                  <div>
                    <div className="font-semibold">{metric.p95_latency.toFixed(2)}ms</div>
                    <div className="text-gray-600">P95</div>
                  </div>
                  <div>
                    <div className="font-semibold">{metric.p99_latency.toFixed(2)}ms</div>
                    <div className="text-gray-600">P99</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Detailed Visualizations */}
        <Tabs defaultValue="latency" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="latency">Latency Analysis</TabsTrigger>
            <TabsTrigger value="throughput">Throughput</TabsTrigger>
            <TabsTrigger value="percentiles">Percentiles</TabsTrigger>
          </TabsList>

          <TabsContent value="latency" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Latency Comparison</CardTitle>
                <CardDescription>
                  Average, P95, and P99 latency across backends
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={latencyChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="backend" />
                    <YAxis label={{ value: 'Latency (ms)', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="Avg Latency" fill="#8884d8" />
                    <Bar dataKey="P95 Latency" fill="#82ca9d" />
                    <Bar dataKey="P99 Latency" fill="#ffc658" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="throughput" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Throughput Comparison</CardTitle>
                <CardDescription>
                  Queries per second for each backend
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={throughputChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="backend" />
                    <YAxis label={{ value: 'Queries/sec', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="Throughput (q/s)" fill="#10b981" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="percentiles" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Percentile Analysis</CardTitle>
                <CardDescription>
                  Latency distribution showing P50, P95, and P99 percentiles
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart data={percentileData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="backend" />
                    <YAxis label={{ value: 'Latency (ms)', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="P50" stroke="#8884d8" strokeWidth={2} />
                    <Line type="monotone" dataKey="P95" stroke="#82ca9d" strokeWidth={2} />
                    <Line type="monotone" dataKey="P99" stroke="#ffc658" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Detailed Metrics Table */}
        <Card>
          <CardHeader>
            <CardTitle>Detailed Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Backend
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Avg Latency
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      P95
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      P99
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Throughput
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Success Rate
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Failed
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {benchmark.metrics.map((metric) => (
                    <tr key={metric.backend} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {metric.backend}
                        {winner?.backend === metric.backend && (
                          <Trophy className="inline h-4 w-4 ml-2 text-yellow-500" />
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {metric.avg_latency.toFixed(2)} ms
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {metric.p95_latency.toFixed(2)} ms
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {metric.p99_latency.toFixed(2)} ms
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {metric.throughput.toFixed(2)} q/s
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <Badge
                          variant={metric.success_rate >= 0.95 ? 'default' : 'destructive'}
                        >
                          {(metric.success_rate * 100).toFixed(1)}%
                        </Badge>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {metric.failed_queries} / {metric.total_queries}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
  );
};
