/**
 * Cost estimation utilities for infrastructure and operations
 */

import type {
  DeploymentConfig,
  CostEstimate,
} from '@/types/infrastructure';

// AWS Pricing (approximate, region: us-east-1)
export const VECTOR_STORE_COSTS = {
  s3vector: {
    storage: 0.023, // S3 Standard $/GB/month
    requests: 0.0004, // S3 GET requests $/1K
    compute: 0, // Serverless (included in Lambda costs)
  },
  lancedb: {
    storage: 0.10, // EBS gp3 $/GB/month
    requests: 0.0008, // EC2 instance amortized $/1K
    compute: 0.0464, // t3.medium $/hour
  },
  qdrant: {
    storage: 0.10, // EBS gp3 $/GB/month
    requests: 0.001, // $/1K requests
    compute: 0.0928, // t3.large $/hour
  },
  opensearch: {
    storage: 0.135, // OpenSearch storage $/GB/month
    requests: 0.002, // $/1K requests
    compute: 0.138, // r6g.large.search $/hour
  },
} as const;

export const EMBEDDING_COSTS = {
  bedrock_titan: {
    perToken: 0.0001 / 1000, // Titan Embeddings V2 $/token
    perImage: 0.00006, // Titan Multimodal $/image
  },
  bedrock_cohere: {
    perToken: 0.0001 / 1000, // Cohere Embed $/token
  },
  sagemaker: {
    perToken: 0.00015 / 1000, // Custom endpoint amortized
    perImage: 0.0001,
    compute: 0.186, // ml.g4dn.xlarge $/hour
  },
  jumpstart: {
    perToken: 0.00012 / 1000,
    perImage: 0.00008,
    compute: 0.186,
  },
  external: {
    perToken: 0.0002 / 1000, // OpenAI ada-002 equivalent
    perImage: 0.0002,
  },
} as const;

export interface CostBreakdown {
  category: string;
  subcategory: string;
  quantity: number;
  unitCost: number;
  totalCost: number;
  unit: string;
}

/**
 * Calculate cost estimate for a deployment configuration
 */
export function calculateDeploymentCost(config: DeploymentConfig): CostEstimate {
  const breakdown: Record<string, number> = {};

  // Storage costs (monthly)
  let storageCost = 0;
  for (const store of config.vectorStores) {
    const storeCost = VECTOR_STORE_COSTS[store].storage * config.estimatedDataSize;
    breakdown[`${store}_storage`] = storeCost;
    storageCost += storeCost;
  }

  // Compute costs (monthly = hourly * 730 hours)
  let computeCost = 0;
  for (const store of config.vectorStores) {
    const hourlyCompute = VECTOR_STORE_COSTS[store].compute || 0;
    if (hourlyCompute > 0) {
      const monthlyCost = hourlyCompute * 730;
      breakdown[`${store}_compute`] = monthlyCost;
      computeCost += monthlyCost;
    }
  }

  // Request costs (monthly)
  let requestCost = 0;
  for (const store of config.vectorStores) {
    const cost = VECTOR_STORE_COSTS[store].requests * (config.estimatedQueries / 1000);
    breakdown[`${store}_requests`] = cost;
    requestCost += cost;
  }

  // Embedding costs
  let embeddingCost = 0;
  for (const provider of config.embeddingProviders) {
    const providerCosts = EMBEDDING_COSTS[provider];

    // Estimate: 1000 tokens per video + 10 frames per video
    const avgVideos = config.estimatedDataSize * 10; // Rough estimate: 10 videos/GB
    const tokenCost = (providerCosts.perToken || 0) * avgVideos * 1000;
    const imageCost = ('perImage' in providerCosts ? providerCosts.perImage || 0 : 0) * avgVideos * 10;

    const totalProviderCost = tokenCost + imageCost;
    breakdown[`${provider}_embeddings`] = totalProviderCost;
    embeddingCost += totalProviderCost;
  }

  const total = storageCost + computeCost + requestCost + embeddingCost;

  return {
    monthly: {
      storage: storageCost,
      compute: computeCost,
      requests: requestCost,
      embeddings: embeddingCost,
      total,
    },
    breakdown,
  };
}

/**
 * Get detailed cost breakdown for display
 */
export function getCostBreakdown(config: DeploymentConfig): CostBreakdown[] {
  const items: CostBreakdown[] = [];

  // Storage breakdown
  for (const store of config.vectorStores) {
    items.push({
      category: 'Storage',
      subcategory: store,
      quantity: config.estimatedDataSize,
      unitCost: VECTOR_STORE_COSTS[store].storage,
      totalCost: VECTOR_STORE_COSTS[store].storage * config.estimatedDataSize,
      unit: 'GB',
    });
  }

  // Compute breakdown
  for (const store of config.vectorStores) {
    const hourlyCompute = VECTOR_STORE_COSTS[store].compute;
    if (hourlyCompute && hourlyCompute > 0) {
      items.push({
        category: 'Compute',
        subcategory: store,
        quantity: 730,
        unitCost: hourlyCompute,
        totalCost: hourlyCompute * 730,
        unit: 'hours',
      });
    }
  }

  // Request breakdown
  for (const store of config.vectorStores) {
    items.push({
      category: 'Requests',
      subcategory: store,
      quantity: config.estimatedQueries / 1000,
      unitCost: VECTOR_STORE_COSTS[store].requests,
      totalCost: VECTOR_STORE_COSTS[store].requests * (config.estimatedQueries / 1000),
      unit: 'K requests',
    });
  }

  // Embedding breakdown
  for (const provider of config.embeddingProviders) {
    const providerCosts = EMBEDDING_COSTS[provider];
    const avgVideos = config.estimatedDataSize * 10;

    if (providerCosts.perToken) {
      items.push({
        category: 'Embeddings',
        subcategory: `${provider} (text)`,
        quantity: avgVideos * 1000,
        unitCost: providerCosts.perToken,
        totalCost: providerCosts.perToken * avgVideos * 1000,
        unit: 'tokens',
      });
    }

    if ('perImage' in providerCosts && providerCosts.perImage) {
      items.push({
        category: 'Embeddings',
        subcategory: `${provider} (images)`,
        quantity: avgVideos * 10,
        unitCost: providerCosts.perImage,
        totalCost: providerCosts.perImage * avgVideos * 10,
        unit: 'images',
      });
    }
  }

  return items;
}

/**
 * Format cost as currency
 */
export function formatCost(amount: number, decimals: number = 2): string {
  return `$${amount.toFixed(decimals)}`;
}

/**
 * Get cost tier and color for UI display
 */
export function getCostTier(monthlyCost: number): {
  tier: 'free' | 'low' | 'medium' | 'high' | 'enterprise';
  color: string;
  label: string;
} {
  if (monthlyCost === 0) {
    return { tier: 'free', color: 'green', label: 'Free Tier' };
  } else if (monthlyCost < 50) {
    return { tier: 'low', color: 'blue', label: 'Low Cost' };
  } else if (monthlyCost < 200) {
    return { tier: 'medium', color: 'yellow', label: 'Medium Cost' };
  } else if (monthlyCost < 1000) {
    return { tier: 'high', color: 'orange', label: 'High Cost' };
  } else {
    return { tier: 'enterprise', color: 'red', label: 'Enterprise Scale' };
  }
}
