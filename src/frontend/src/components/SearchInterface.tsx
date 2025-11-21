import React, { useState } from 'react';
import { Search, Image as ImageIcon, Database } from 'lucide-react';
import { Badge } from './ui/badge';

interface BackendOption {
  value: string;
  label: string;
  deployed?: boolean;
  disabled?: boolean;
}

interface SearchInterfaceProps {
  onSearch: (query: string, type: 'text' | 'image', backend: string) => void;
  isLoading?: boolean;
  availableBackends?: BackendOption[];
  selectedBackend?: string;
  onBackendChange?: (backend: string) => void;
}

export const SearchInterface: React.FC<SearchInterfaceProps> = ({
  onSearch,
  isLoading = false,
  availableBackends = [
    { value: 's3_vector', label: 'S3 Vector', deployed: true },
    { value: 'lancedb', label: 'LanceDB', deployed: false },
    { value: 'qdrant', label: 'Qdrant', deployed: false },
    { value: 'opensearch', label: 'OpenSearch', deployed: false }
  ],
  selectedBackend = 's3_vector',
  onBackendChange
}) => {
  const [query, setQuery] = useState('');
  const [localBackend, setLocalBackend] = useState(selectedBackend);

  const handleBackendChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newBackend = e.target.value;
    setLocalBackend(newBackend);
    if (onBackendChange) {
      onBackendChange(newBackend);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query, 'text', localBackend);
    }
  };

  const currentBackend = availableBackends.find(b => b.value === localBackend);

  return (
    <div className="w-full max-w-4xl mx-auto p-4 space-y-3">
      {/* Backend Selector */}
      <div className="flex items-center justify-center space-x-3">
        <Database className="h-5 w-5 text-gray-500" />
        <label htmlFor="backend-select" className="text-sm font-medium text-gray-700">
          Vector Store:
        </label>
        <select
          id="backend-select"
          value={localBackend}
          onChange={handleBackendChange}
          className="block w-48 pl-3 pr-10 py-2 text-sm border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 rounded-md"
        >
          {availableBackends.map((backend) => (
            <option
              key={backend.value}
              value={backend.value}
              disabled={backend.disabled}
            >
              {backend.label} {backend.deployed ? '✓' : '(not deployed)'}
            </option>
          ))}
        </select>
        {currentBackend?.deployed && (
          <Badge variant="default" className="bg-green-500">
            Active
          </Badge>
        )}
        {currentBackend && !currentBackend.deployed && (
          <Badge variant="secondary">
            Not Deployed
          </Badge>
        )}
      </div>

      {/* Search Form */}
      <form onSubmit={handleSubmit} className="relative flex items-center">
        <div className="relative flex-grow">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-l-lg leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            placeholder="Search videos (e.g., 'person running on beach')"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <button
          type="button"
          className="inline-flex items-center px-4 py-3 border border-l-0 border-gray-300 bg-gray-50 text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
          title="Search by Image (Coming Soon)"
        >
          <ImageIcon className="h-5 w-5" />
        </button>
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-r-lg text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Searching...' : 'Search'}
        </button>
      </form>
    </div>
  );
};