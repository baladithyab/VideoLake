/**
 * NotFoundPage - 404 error page
 */

import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Home, ArrowLeft, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="max-w-2xl w-full text-center space-y-8">
        {/* 404 illustration */}
        <div className="relative">
          <h1 className="text-9xl font-bold text-gray-200">404</h1>
          <div className="absolute inset-0 flex items-center justify-center">
            <Search className="w-24 h-24 text-gray-400" />
          </div>
        </div>

        {/* Error message */}
        <div className="space-y-4">
          <h2 className="text-3xl font-bold text-gray-900">
            Page Not Found
          </h2>
          <p className="text-lg text-gray-600 max-w-md mx-auto">
            Sorry, we couldn't find the page you're looking for.
            It might have been moved or doesn't exist.
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex items-center justify-center gap-4 pt-4">
          <Button
            onClick={() => navigate(-1)}
            variant="outline"
            size="lg"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            Go Back
          </Button>

          <Link to="/">
            <Button size="lg">
              <Home className="w-5 h-5 mr-2" />
              Home Page
            </Button>
          </Link>
        </div>

        {/* Helpful links */}
        <div className="pt-8 border-t border-gray-200">
          <p className="text-sm text-gray-600 mb-4">
            You might find these pages helpful:
          </p>
          <div className="flex items-center justify-center gap-6 text-sm">
            <Link
              to="/deployment"
              className="text-indigo-600 hover:text-indigo-700 font-medium"
            >
              Deploy Infrastructure
            </Link>
            <span className="text-gray-300">•</span>
            <Link
              to="/benchmark"
              className="text-indigo-600 hover:text-indigo-700 font-medium"
            >
              Run Benchmarks
            </Link>
            <span className="text-gray-300">•</span>
            <Link
              to="/demo"
              className="text-indigo-600 hover:text-indigo-700 font-medium"
            >
              Search Demo
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
