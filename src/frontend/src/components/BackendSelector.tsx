import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { Database } from 'lucide-react';

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

  const handleBackendChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newBackend = e.target.value;
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
      <label htmlFor="backend-select" className="text-sm font-medium text-gray-700">
        Backend:
      </label>
      <select
        id="backend-select"
        value={activeBackend}
        onChange={handleBackendChange}
        disabled={loading}
        className="block w-full pl-3 pr-10 py-1 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
      >
        {backends.map((backend) => (
          <option key={backend} value={backend}>
            {backend}
          </option>
        ))}
      </select>
      {loading && <span className="text-xs text-gray-500">Switching...</span>}
    </div>
  );
};