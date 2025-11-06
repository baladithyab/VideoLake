import { useEffect, useRef, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Loader2, CheckCircle2, XCircle, Terminal, X } from 'lucide-react';

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  status?: string;
  error?: string;
}

interface TerraformLogViewerProps {
  operationId: string;
  vectorStore: string;
  operationType: 'deploy' | 'destroy';
  onClose: () => void;
}

export default function TerraformLogViewer({
  operationId,
  vectorStore,
  operationType,
  onClose
}: TerraformLogViewerProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [status, setStatus] = useState<'running' | 'completed' | 'failed'>('running');
  const [error, setError] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // Connect to SSE endpoint
  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const eventSource = new EventSource(
      `${apiUrl}/api/infrastructure/logs/${operationId}`
    );

    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const logEntry: LogEntry = JSON.parse(event.data);

        // Check if this is a completion event
        if (logEntry.level === 'COMPLETE') {
          setStatus(logEntry.status as 'completed' | 'failed');
          if (logEntry.error) {
            setError(logEntry.error);
          }
          eventSource.close();
        } else {
          // Add log entry
          setLogs((prev) => [...prev, logEntry]);
        }
      } catch (err) {
        console.error('Failed to parse log entry:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE error:', err);
      setStatus('failed');
      setError('Connection to log stream lost');
      eventSource.close();
    };

    // Cleanup on unmount
    return () => {
      eventSource.close();
    };
  }, [operationId]);

  const getStatusBadge = () => {
    switch (status) {
      case 'running':
        return (
          <Badge variant="default" className="bg-blue-500">
            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
            Running
          </Badge>
        );
      case 'completed':
        return (
          <Badge variant="default" className="bg-green-500">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Completed
          </Badge>
        );
      case 'failed':
        return (
          <Badge variant="destructive">
            <XCircle className="h-3 w-3 mr-1" />
            Failed
          </Badge>
        );
    }
  };

  const getLogLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR':
        return 'text-red-500';
      case 'WARNING':
        return 'text-yellow-500';
      case 'INFO':
      default:
        return 'text-gray-300';
    }
  };

  return (
    <div className="w-full">
      {/* Header */}
      <div className="flex items-center justify-between p-6 pb-4">
        <div className="flex items-center gap-3">
          <Terminal className="h-5 w-5" />
          <div>
            <h2 className="text-lg font-semibold">
              {operationType === 'deploy' ? 'Deploying' : 'Destroying'} {vectorStore}
            </h2>
            <p className="text-sm text-muted-foreground">
              Real-time Terraform output
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {getStatusBadge()}
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            disabled={status === 'running'}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="px-6 pb-6">
        {/* Log output */}
        <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm h-96 overflow-y-auto">
          {logs.length === 0 && status === 'running' && (
            <div className="flex items-center gap-2 text-gray-400">
              <Loader2 className="h-4 w-4 animate-spin" />
              Connecting to log stream...
            </div>
          )}

          {logs.map((log, index) => (
            <div key={index} className="mb-1">
              <span className="text-gray-500">{log.timestamp}</span>
              {' '}
              <span className={getLogLevelColor(log.level)}>
                [{log.level}]
              </span>
              {' '}
              <span className="text-gray-200">{log.message}</span>
            </div>
          ))}

          {error && (
            <div className="mt-4 p-3 bg-red-900/20 border border-red-500 rounded text-red-400">
              <strong>Error:</strong> {error}
            </div>
          )}

          {/* Auto-scroll anchor */}
          <div ref={logsEndRef} />
        </div>

        {/* Status footer */}
        <div className="mt-4 flex items-center justify-between text-sm text-gray-500">
          <div>
            {logs.length} log {logs.length === 1 ? 'entry' : 'entries'}
          </div>
          {status === 'completed' && (
            <div className="text-green-600 font-medium">
              ✓ Operation completed successfully
            </div>
          )}
          {status === 'failed' && (
            <div className="text-red-600 font-medium">
              ✗ Operation failed
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

