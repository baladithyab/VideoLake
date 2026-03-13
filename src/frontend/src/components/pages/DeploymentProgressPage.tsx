import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { api } from '@/api/client';
import { CheckCircle2, Circle, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DeploymentStep {
  id: string;
  title: string;
  description?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  duration?: number;
  error?: string;
}

interface InfrastructureStatus {
  overall_status: string;
  vector_stores: Record<string, {
    status: string;
    endpoint?: string;
    error?: string;
  }>;
}

export default function DeploymentProgressPage() {
  const navigate = useNavigate();
  const [steps, setSteps] = useState<DeploymentStep[]>([
    { id: 'vpc', title: 'VPC and networking', status: 'in_progress' },
    { id: 'security', title: 'Security groups and IAM roles', status: 'pending' },
    { id: 's3', title: 'S3 buckets and policies', status: 'pending' },
    { id: 'ecs', title: 'ECS cluster and task definitions', status: 'pending' },
    { id: 'containers', title: 'Container deployment', status: 'pending' },
    { id: 'health', title: 'Health checks and verification', status: 'pending' },
  ]);
  const [deploymentComplete, setDeploymentComplete] = useState(false);
  const [deploymentFailed, setDeploymentFailed] = useState(false);
  const [infrastructureStatus, setInfrastructureStatus] = useState<InfrastructureStatus | null>(null);
  const [startTime, setStartTime] = useState<Date>(new Date());
  const [elapsedTime, setElapsedTime] = useState(0);
  const [showLogs, setShowLogs] = useState(false);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Calculate elapsed time
  useEffect(() => {
    const deploymentStartTimeStr = localStorage.getItem('deploymentStartTime');
    if (deploymentStartTimeStr) {
      setStartTime(new Date(deploymentStartTimeStr));
    }

    const timer = setInterval(() => {
      const now = new Date();
      const elapsed = Math.floor((now.getTime() - startTime.getTime()) / 1000);
      setElapsedTime(elapsed);
    }, 1000);

    return () => clearInterval(timer);
  }, [startTime]);

  // Poll infrastructure status
  useEffect(() => {
    const updateStepsFromStatus = (status: InfrastructureStatus, currentElapsedTime: number) => {
    // Simulate step progression based on overall status
    // In a real implementation, this would be based on actual Terraform events

    const hasError = status.overall_status === 'error';
    const isComplete = status.overall_status === 'healthy';

    setSteps(prev => {
      const newSteps = [...prev];

      if (hasError) {
        // Mark current step as failed
        const inProgressIndex = newSteps.findIndex(s => s.status === 'in_progress');
        if (inProgressIndex !== -1) {
          newSteps[inProgressIndex].status = 'failed';
          newSteps[inProgressIndex].error = 'Deployment failed. Check logs for details.';
        }
      } else if (isComplete) {
        // Mark all as completed
        newSteps.forEach(step => {
          if (step.status !== 'completed') {
            step.status = 'completed';
          }
        });
      } else {
        // Progress through steps
        const completedCount = Math.min(
          Math.floor(currentElapsedTime / 120), // ~2 minutes per step
          newSteps.length - 1
        );

        newSteps.forEach((step, index) => {
          if (index < completedCount) {
            step.status = 'completed';
            step.duration = 120; // Mock duration
          } else if (index === completedCount) {
            step.status = 'in_progress';
          }
        });
      }

      return newSteps;
    });
    };

    const pollStatus = async () => {
      try {
        const response = await api.getInfrastructureStatus();
        const status = response.data as InfrastructureStatus;
        setInfrastructureStatus(status);

        // Calculate current elapsed time for step progression
        const now = new Date();
        const currentElapsedTime = Math.floor((now.getTime() - startTime.getTime()) / 1000);

        // Update steps based on infrastructure status
        updateStepsFromStatus(status, currentElapsedTime);

        // Check if deployment is complete
        if (status.overall_status === 'healthy') {
          setDeploymentComplete(true);
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
          }
          localStorage.removeItem('deploymentInProgress');
        } else if (status.overall_status === 'error') {
          setDeploymentFailed(true);
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
          }
        }
      } catch (error) {
        console.error('Failed to poll infrastructure status:', error);
      }
    };

    // Initial poll
    pollStatus();

    // Poll every 5 seconds
    pollingIntervalRef.current = setInterval(pollStatus, 5000);

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [startTime]);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs.toString().padStart(2, '0')}s`;
  };

  const estimatedRemaining = (): string => {
    const totalEstimated = 1200; // 20 minutes
    const remaining = Math.max(0, totalEstimated - elapsedTime);
    const mins = Math.floor(remaining / 60);
    return mins > 0 ? `${mins}-${mins + 6} minutes` : 'Almost done';
  };

  const getStepIcon = (status: DeploymentStep['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case 'in_progress':
        return <Loader2 className="w-5 h-5 text-primary animate-spin" />;
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-destructive" />;
      default:
        return <Circle className="w-5 h-5 text-muted-foreground" />;
    }
  };

  if (deploymentComplete) {
    const deployedStores = infrastructureStatus?.vector_stores || {};

    return (
      <div className="container mx-auto max-w-4xl py-8 px-4">
        <Card className="border-green-500/50 bg-green-500/5">
          <CardContent className="py-8">
            <div className="text-center space-y-4">
              <div className="flex justify-center">
                <CheckCircle2 className="w-16 h-16 text-green-500" />
              </div>
              <h1 className="text-3xl font-bold">✅ Deployment Complete!</h1>
              <p className="text-muted-foreground">
                Total time: {formatTime(elapsedTime)}
              </p>
            </div>
          </CardContent>
        </Card>

        <div className="mt-8 space-y-6">
          <div>
            <h2 className="text-xl font-semibold mb-4">Your infrastructure is ready:</h2>
            <div className="space-y-3">
              {Object.entries(deployedStores).map(([store, details]) => (
                <Card key={store}>
                  <CardContent className="py-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <CheckCircle2 className="w-5 h-5 text-green-500" />
                        <div>
                          <div className="font-semibold">{store} - Active</div>
                          {details.endpoint && (
                            <div className="text-sm text-muted-foreground">
                              Endpoint: {details.endpoint}
                            </div>
                          )}
                        </div>
                      </div>
                      <Badge variant="secondary">Ready</Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          <div>
            <h3 className="font-semibold mb-4">Next Steps:</h3>
            <div className="grid grid-cols-2 gap-4">
              <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate('/benchmark')}>
                <CardContent className="py-6">
                  <h4 className="font-semibold mb-2">Run Benchmark</h4>
                  <p className="text-sm text-muted-foreground">
                    Compare vector store performance
                  </p>
                </CardContent>
              </Card>
              <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate('/demo')}>
                <CardContent className="py-6">
                  <h4 className="font-semibold mb-2">Try Demo</h4>
                  <p className="text-sm text-muted-foreground">
                    Search videos with multi-modal queries
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>

          <div className="flex justify-center pt-6">
            <Button size="lg" onClick={() => navigate('/infrastructure')}>
              View Infrastructure Dashboard
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (deploymentFailed) {
    return (
      <div className="container mx-auto max-w-4xl py-8 px-4">
        <Alert variant="destructive">
          <AlertDescription>
            <div className="font-semibold mb-2">Deployment Failed</div>
            <p>The deployment encountered errors. Please check the logs below for details.</p>
          </AlertDescription>
        </Alert>

        <div className="mt-6 space-y-4">
          {steps.filter(s => s.status === 'failed').map(step => (
            <Card key={step.id} className="border-destructive">
              <CardContent className="py-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-destructive mt-0.5" />
                  <div>
                    <div className="font-semibold">{step.title}</div>
                    {step.error && (
                      <div className="text-sm text-muted-foreground mt-1">{step.error}</div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="flex gap-4 mt-8">
          <Button variant="outline" onClick={() => navigate('/deployment/configure')}>
            Back to Configuration
          </Button>
          <Button onClick={() => navigate('/infrastructure')}>
            View Infrastructure Status
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-4xl py-8 px-4">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Deploying Infrastructure...</h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>Elapsed: {formatTime(elapsedTime)}</span>
          <span>•</span>
          <span>Est. remaining: {estimatedRemaining()}</span>
        </div>
      </div>

      {/* Progress Steps */}
      <Card className="mb-6">
        <CardContent className="py-6">
          <div className="space-y-4">
            {steps.map((step, index) => (
              <div key={step.id} className="flex items-start gap-4">
                <div className="flex-shrink-0 mt-0.5">
                  {getStepIcon(step.status)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className={cn(
                        "font-medium",
                        step.status === 'in_progress' && "text-primary",
                        step.status === 'completed' && "text-green-600",
                        step.status === 'failed' && "text-destructive"
                      )}>
                        {step.title}
                      </div>
                      {step.description && (
                        <div className="text-sm text-muted-foreground mt-0.5">
                          {step.description}
                        </div>
                      )}
                      {step.status === 'in_progress' && (
                        <div className="text-sm text-muted-foreground mt-1">
                          {index === 3 && '• Creating ECS services...'}
                          {index === 3 && <div className="ml-2">• Waiting for tasks to stabilize...</div>}
                        </div>
                      )}
                      {step.error && (
                        <div className="text-sm text-destructive mt-1">{step.error}</div>
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground flex-shrink-0">
                      {step.status === 'completed' && step.duration && formatTime(step.duration)}
                      {step.status === 'in_progress' && 'In Progress'}
                      {step.status === 'pending' && 'Pending'}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Terraform Logs */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold">Live Terraform Output</h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowLogs(!showLogs)}
            >
              {showLogs ? 'Collapse' : 'Expand'}
            </Button>
          </div>
          {showLogs && (
            <div className="bg-black text-green-400 p-4 rounded-md font-mono text-sm max-h-[400px] overflow-y-auto">
              <div className="mt-2 text-gray-500">
                module.lancedb.aws_ecs_service.main: Creating...
                <br />
                module.lancedb.aws_ecs_service.main: Still creating... [30s elapsed]
                <br />
                module.lancedb.aws_ecs_service.main: Still creating... [1m0s elapsed]
                <br />
                module.lancedb.aws_ecs_service.main: Creation complete after 1m15s [id=s3vec-lancedb]
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Warning */}
      <Alert className="mt-6">
        <AlertDescription>
          ⚠️ Please keep this window open during deployment
        </AlertDescription>
      </Alert>

      {/* View Full Logs Button */}
      <div className="flex justify-center mt-6">
        <Button variant="outline" onClick={() => setShowLogs(true)}>
          View Full Logs
        </Button>
      </div>
    </div>
  );
}
