import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { Database } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export const BackendSelector: React.FC = () => {
  const [backends, setBackends] = useState<string[]>([]);
  const [activeBackend, setActiveBackend] = useState<string>('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await api.getConfig();
      setBackends(response.data.available_backends);
      setActiveBackend(response.data.active_backend);
    } catch (error) {
      console.error('Failed to fetch config:', error);
    }
  };

  const handleBackendChange = async (newBackend: string) => {
    setLoading(true);
    try {
      await api.switchBackend({ backend_type: newBackend });
      setActiveBackend(newBackend);
    } catch (error) {
      console.error('Failed to switch backend:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center space-x-2 bg-white p-2 rounded-md shadow-sm border border-gray-200">
      <Database className="h-4 w-4 text-gray-500" />
      <label className="text-sm font-medium text-gray-700">
        Backend:
      </label>
      <Select
        value={activeBackend}
        onValueChange={handleBackendChange}
        disabled={loading}
      >
        <SelectTrigger className="w-full">
          <SelectValue placeholder="Select backend" />
        </SelectTrigger>
        <SelectContent>
          {backends.map((backend) => (
            <SelectItem key={backend} value={backend}>
              {backend}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {loading && <span className="text-xs text-gray-500">Switching...</span>}
    </div>
  );
};