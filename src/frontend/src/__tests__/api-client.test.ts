/**
 * API client tests.
 *
 * Tests for the API client module:
 * - Request formatting
 * - Response handling
 * - Error handling
 * - Endpoint structure
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'
import { api, apiClient } from '../api/client'

// Mock axios
vi.mock('axios')

describe('API Client Configuration', () => {
  it('creates axios instance with correct base URL', () => {
    expect(apiClient.defaults.baseURL).toBeDefined()
    // Default should be localhost:8000 or from env var
    expect(apiClient.defaults.baseURL).toMatch(/http/)
  })

  it('sets correct default headers', () => {
    expect(apiClient.defaults.headers['Content-Type']).toBe('application/json')
  })
})

describe('API Client Methods', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Infrastructure endpoints', () => {
    it('getInfrastructureStatus calls correct endpoint', async () => {
      const mockData = { vector_stores: {} }
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockData })

      await api.getInfrastructureStatus()

      expect(apiClient.get).toHaveBeenCalledWith('/api/infrastructure/status')
    })

    it('deployInfrastructure sends correct request', async () => {
      const mockRequest = {
        vector_stores: ['s3_vector', 'opensearch'],
        wait_for_completion: false,
      }

      vi.mocked(apiClient.post).mockResolvedValue({ data: { message: 'Deployment started' } })

      await api.deployInfrastructure(mockRequest)

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/infrastructure/deploy',
        mockRequest
      )
    })

    it('destroyInfrastructure sends correct request', async () => {
      const mockRequest = {
        vector_stores: ['opensearch'],
        confirm: true,
      }

      vi.mocked(apiClient.delete).mockResolvedValue({ data: { message: 'Destruction started' } })

      await api.destroyInfrastructure(mockRequest)

      expect(apiClient.delete).toHaveBeenCalledWith(
        '/api/infrastructure/destroy',
        { data: mockRequest }
      )
    })

    it('deploySingleStore calls correct endpoint', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { message: 'Deployed' } })

      await api.deploySingleStore('lancedb')

      expect(apiClient.post).toHaveBeenCalledWith('/api/infrastructure/deploy/lancedb')
    })

    it('destroySingleStore calls correct endpoint with params', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({ data: { message: 'Destroyed' } })

      await api.destroySingleStore('lancedb', true)

      expect(apiClient.delete).toHaveBeenCalledWith(
        '/api/infrastructure/destroy/lancedb',
        { params: { confirm: true } }
      )
    })
  })

  describe('Search endpoints', () => {
    it('search calls correct endpoint with vector', async () => {
      const mockRequest = {
        query_vector: [0.1, 0.2, 0.3],
        top_k: 10,
        backend: 's3_vector',
      }

      vi.mocked(apiClient.post).mockResolvedValue({ data: { results: [] } })

      await api.search(mockRequest)

      expect(apiClient.post).toHaveBeenCalledWith('/api/search', mockRequest)
    })

    it('searchQuery calls correct endpoint with text', async () => {
      const mockRequest = {
        query_text: 'test query',
        top_k: 5,
        backend: 'opensearch',
      }

      vi.mocked(apiClient.post).mockResolvedValue({ data: { results: [] } })

      await api.searchQuery(mockRequest)

      expect(apiClient.post).toHaveBeenCalledWith('/api/search/query', mockRequest)
    })
  })

  describe('Ingestion endpoints', () => {
    it('uploadVideo sends multipart form data', async () => {
      const mockFile = new File(['test'], 'test.mp4', { type: 'video/mp4' })

      vi.mocked(apiClient.post).mockResolvedValue({ data: { s3_key: 'uploads/test.mp4' } })

      await api.uploadVideo(mockFile, 'my-bucket')

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/ingest/upload',
        expect.any(FormData),
        expect.objectContaining({
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })
      )
    })

    it('startIngestion calls correct endpoint', async () => {
      const mockRequest = {
        video_path: 's3://bucket/video.mp4',
        model_type: 'titan',
        backend_types: ['s3_vector', 'opensearch'],
      }

      vi.mocked(apiClient.post).mockResolvedValue({
        data: {
          message: 'Ingestion started',
          execution_arn: 'arn:aws:states:us-east-1:123456789012:execution:test',
        },
      })

      await api.startIngestion(mockRequest)

      expect(apiClient.post).toHaveBeenCalledWith('/ingestion/start', mockRequest)
    })

    it('getIngestionStatus calls correct endpoint with ARN', async () => {
      const executionArn = 'arn:aws:states:us-east-1:123456789012:execution:test'

      vi.mocked(apiClient.get).mockResolvedValue({
        data: {
          status: 'RUNNING',
          execution_arn: executionArn,
        },
      })

      await api.getIngestionStatus(executionArn)

      expect(apiClient.get).toHaveBeenCalledWith(`/ingestion/status/${executionArn}`)
    })

    it('listDatasets calls correct endpoint', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: [
          { name: 'MSR-VTT', source: 'huggingface' },
        ],
      })

      await api.listDatasets()

      expect(apiClient.get).toHaveBeenCalledWith('/ingestion/datasets')
    })
  })

  describe('Benchmark endpoints', () => {
    it('startBenchmark calls correct endpoint', async () => {
      const mockRequest = {
        name: 'Test Benchmark',
        vector_stores: ['s3_vector'],
        dataset: 'MSR-VTT',
        query_count: 100,
      }

      vi.mocked(apiClient.post).mockResolvedValue({
        data: {
          benchmark_id: 'bench-123',
          status: 'running',
        },
      })

      await api.startBenchmark(mockRequest as any)

      expect(apiClient.post).toHaveBeenCalledWith('/api/benchmark/start', mockRequest)
    })

    it('getBenchmarkResults calls correct endpoint', async () => {
      const benchmarkId = 'bench-123'

      vi.mocked(apiClient.get).mockResolvedValue({
        data: {
          id: benchmarkId,
          status: 'completed',
          metrics: {},
        },
      })

      await api.getBenchmarkResults(benchmarkId)

      expect(apiClient.get).toHaveBeenCalledWith(`/api/benchmark/results/${benchmarkId}`)
    })

    it('getBenchmarkProgress calls correct endpoint', async () => {
      const benchmarkId = 'bench-123'

      vi.mocked(apiClient.get).mockResolvedValue({
        data: {
          benchmark_id: benchmarkId,
          progress: 0.5,
          current_step: 'Running queries',
        },
      })

      await api.getBenchmarkProgress(benchmarkId)

      expect(apiClient.get).toHaveBeenCalledWith(`/api/benchmark/progress/${benchmarkId}`)
    })

    it('listBenchmarks calls correct endpoint', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: [],
      })

      await api.listBenchmarks()

      expect(apiClient.get).toHaveBeenCalledWith('/api/benchmark/list')
    })
  })
})
