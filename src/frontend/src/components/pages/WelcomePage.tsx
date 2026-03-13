/**
 * WelcomePage - Landing page with quick start guide and feature overview
 */

import React from 'react';
import { Link } from 'react-router-dom';
import {
  Rocket,
  BarChart3,
  Search,
  Database,
  Zap,
  Shield,
  ArrowRight,
  Play,
  BookOpen,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useInfrastructure } from '@/contexts/InfrastructureContext';
import { StatusIndicator } from '@/components/molecules/StatusIndicator';

interface FeatureCardProps {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  link: string;
  linkLabel: string;
}

function FeatureCard({ icon: Icon, title, description, link, linkLabel }: FeatureCardProps) {
  return (
    <Card className="p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-start gap-4">
        <div className="p-3 bg-indigo-50 rounded-lg">
          <Icon className="w-6 h-6 text-indigo-600" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
          <p className="text-gray-600 mb-4">{description}</p>
          <Link to={link}>
            <Button variant="ghost" size="sm" className="group">
              {linkLabel}
              <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
            </Button>
          </Link>
        </div>
      </div>
    </Card>
  );
}

export function WelcomePage() {
  const { getDeployedStores } = useInfrastructure();
  const deployedStores = getDeployedStores();
  const hasDeployments = deployedStores.length > 0;

  return (
    <div className="max-w-7xl mx-auto space-y-12">
      {/* Hero section */}
      <div className="text-center space-y-6">
        <div className="inline-flex items-center gap-3 px-4 py-2 bg-indigo-50 rounded-full">
          <Database className="w-5 h-5 text-indigo-600" />
          <span className="text-sm font-medium text-indigo-700">
            Multi-Modal Vector Search Platform
          </span>
        </div>

        <h1 className="text-5xl font-bold text-gray-900 tracking-tight">
          Welcome to <span className="text-indigo-600">S3Vector</span>
        </h1>

        <p className="text-xl text-gray-600 max-w-3xl mx-auto">
          Deploy, benchmark, and explore vector stores for multi-modal search.
          Compare performance across S3 Vector, LanceDB, Qdrant, and OpenSearch.
        </p>

        {/* CTA buttons */}
        <div className="flex items-center justify-center gap-4 pt-4">
          <Link to="/deployment">
            <Button size="lg" className="group">
              <Rocket className="w-5 h-5 mr-2" />
              Get Started
              <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
            </Button>
          </Link>
          <Link to="/demo">
            <Button size="lg" variant="outline">
              <Play className="w-5 h-5 mr-2" />
              Try Demo
            </Button>
          </Link>
        </div>
      </div>

      {/* Infrastructure status */}
      {hasDeployments && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <div className="flex items-start gap-4">
            <Shield className="w-6 h-6 text-green-600 mt-1" />
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-green-900 mb-2">
                Infrastructure Active
              </h3>
              <p className="text-green-700 mb-3">
                You have {deployedStores.length} vector {deployedStores.length === 1 ? 'store' : 'stores'} deployed and ready to use.
              </p>
              <div className="flex flex-wrap gap-2">
                {deployedStores.map((store) => (
                  <StatusIndicator
                    key={store}
                    status="deployed"
                    label={store === 's3vector' ? 'S3 Vector' : store}
                    size="sm"
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quick start guide */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Quick Start Guide</h2>
        <div className="grid md:grid-cols-3 gap-6">
          <div className="relative">
            <div className="absolute -left-1 top-0 w-8 h-8 bg-indigo-600 text-white rounded-full flex items-center justify-center font-bold">
              1
            </div>
            <Card className="ml-6 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Deploy Infrastructure
              </h3>
              <p className="text-gray-600 mb-4">
                Choose vector stores and embedding models. Get cost estimates before deploying.
              </p>
              <Link to="/deployment">
                <Button variant="outline" size="sm">
                  Start Deployment
                </Button>
              </Link>
            </Card>
          </div>

          <div className="relative">
            <div className="absolute -left-1 top-0 w-8 h-8 bg-indigo-600 text-white rounded-full flex items-center justify-center font-bold">
              2
            </div>
            <Card className="ml-6 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Run Benchmarks
              </h3>
              <p className="text-gray-600 mb-4">
                Compare performance, latency, and cost across different vector stores.
              </p>
              <Link to="/benchmark">
                <Button variant="outline" size="sm">
                  Configure Benchmark
                </Button>
              </Link>
            </Card>
          </div>

          <div className="relative">
            <div className="absolute -left-1 top-0 w-8 h-8 bg-indigo-600 text-white rounded-full flex items-center justify-center font-bold">
              3
            </div>
            <Card className="ml-6 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Search & Explore
              </h3>
              <p className="text-gray-600 mb-4">
                Test multi-modal search with text, images, and video content.
              </p>
              <Link to="/demo">
                <Button variant="outline" size="sm">
                  Try Search Demo
                </Button>
              </Link>
            </Card>
          </div>
        </div>
      </div>

      {/* Features */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Platform Features</h2>
        <div className="grid md:grid-cols-2 gap-6">
          <FeatureCard
            icon={Rocket}
            title="One-Click Deployment"
            description="Deploy vector stores with Terraform automation. Infrastructure as code with automatic provisioning."
            link="/deployment"
            linkLabel="Deploy Now"
          />

          <FeatureCard
            icon={BarChart3}
            title="Performance Benchmarks"
            description="Compare latency, throughput, and cost. Make data-driven decisions about your infrastructure."
            link="/benchmark"
            linkLabel="Run Benchmarks"
          />

          <FeatureCard
            icon={Search}
            title="Multi-Modal Search"
            description="Search across text, images, audio, and video. Unified embedding space for all modalities."
            link="/demo"
            linkLabel="Try Demo"
          />

          <FeatureCard
            icon={Zap}
            title="Real-Time Monitoring"
            description="Track deployment progress, benchmark execution, and search performance in real-time."
            link="/benchmark/history"
            linkLabel="View History"
          />
        </div>
      </div>

      {/* Documentation */}
      <div className="bg-gray-100 rounded-lg p-8 text-center">
        <BookOpen className="w-12 h-12 text-gray-600 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-gray-900 mb-2">
          Need Help?
        </h3>
        <p className="text-gray-600 mb-4 max-w-2xl mx-auto">
          Check out our documentation for detailed guides, API references, and best practices.
        </p>
        <div className="flex items-center justify-center gap-4">
          <a
            href="https://github.com/yourusername/s3vector"
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button variant="outline">
              View Documentation
            </Button>
          </a>
          <a
            href="https://github.com/yourusername/s3vector/issues"
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button variant="ghost">
              Report Issue
            </Button>
          </a>
        </div>
      </div>
    </div>
  );
}
