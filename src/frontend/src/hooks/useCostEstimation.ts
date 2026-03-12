/**
 * Hook for real-time cost estimation based on deployment configuration
 */

import { useMemo } from 'react';
import type { DeploymentConfig, CostEstimate } from '@/types/infrastructure';
import { calculateDeploymentCost, getCostBreakdown, getCostTier } from '@/utils/cost';
import type { CostBreakdown } from '@/utils/cost';

export interface CostEstimationResult {
  estimate: CostEstimate;
  breakdown: CostBreakdown[];
  tier: ReturnType<typeof getCostTier>;
  isValid: boolean;
  warnings: string[];
}

/**
 * Custom hook for calculating cost estimates from deployment configuration
 *
 * @param config - Deployment configuration
 * @returns Cost estimation result with breakdown and warnings
 */
export function useCostEstimation(config: DeploymentConfig | null): CostEstimationResult {
  return useMemo(() => {
    // Default empty result
    if (!config) {
      return {
        estimate: {
          monthly: { storage: 0, compute: 0, requests: 0, embeddings: 0, total: 0 },
          breakdown: {},
        },
        breakdown: [],
        tier: getCostTier(0),
        isValid: false,
        warnings: ['No configuration provided'],
      };
    }

    const warnings: string[] = [];

    // Validation
    if (!config.vectorStores || config.vectorStores.length === 0) {
      warnings.push('No vector stores selected');
    }

    if (!config.embeddingProviders || config.embeddingProviders.length === 0) {
      warnings.push('No embedding providers selected');
    }

    if (config.estimatedDataSize <= 0) {
      warnings.push('Invalid data size (must be > 0)');
    }

    if (config.estimatedQueries < 0) {
      warnings.push('Invalid query count (must be >= 0)');
    }

    // Calculate costs even if some warnings exist
    const estimate = calculateDeploymentCost(config);
    const breakdown = getCostBreakdown(config);
    const tier = getCostTier(estimate.monthly.total);

    // Add tier-specific warnings
    if (tier.tier === 'high') {
      warnings.push('High monthly costs - consider optimization');
    } else if (tier.tier === 'enterprise') {
      warnings.push('Enterprise-scale costs - review architecture carefully');
    }

    // Multiple vector store warning
    if (config.vectorStores.length > 2) {
      warnings.push(`Deploying ${config.vectorStores.length} vector stores increases costs significantly`);
    }

    // High query volume warning
    if (config.estimatedQueries > 1000000) {
      warnings.push('High query volume detected - ensure proper caching strategy');
    }

    const isValid = warnings.length === 0 || !warnings.some(w =>
      w.includes('No vector stores') || w.includes('No embedding providers') || w.includes('Invalid')
    );

    return {
      estimate,
      breakdown,
      tier,
      isValid,
      warnings,
    };
  }, [config]);
}

/**
 * Hook for comparing costs between different configurations
 *
 * @param configs - Array of deployment configurations to compare
 * @returns Array of cost estimation results
 */
export function useCompareCosts(
  configs: (DeploymentConfig | null)[]
): CostEstimationResult[] {
  return useMemo(() => {
    return configs.map(config => {
      if (!config) {
        return {
          estimate: {
            monthly: { storage: 0, compute: 0, requests: 0, embeddings: 0, total: 0 },
            breakdown: {},
          },
          breakdown: [],
          tier: getCostTier(0),
          isValid: false,
          warnings: ['No configuration'],
        };
      }

      const estimate = calculateDeploymentCost(config);
      const breakdown = getCostBreakdown(config);
      const tier = getCostTier(estimate.monthly.total);

      return {
        estimate,
        breakdown,
        tier,
        isValid: true,
        warnings: [],
      };
    });
  }, [configs]);
}

/**
 * Calculate cost savings between two configurations
 */
export function useCostSavings(
  baseConfig: DeploymentConfig | null,
  optimizedConfig: DeploymentConfig | null
): {
  monthlySavings: number;
  percentSaved: number;
  savingsBreakdown: Record<string, number>;
} {
  return useMemo(() => {
    if (!baseConfig || !optimizedConfig) {
      return {
        monthlySavings: 0,
        percentSaved: 0,
        savingsBreakdown: {},
      };
    }

    const baseCost = calculateDeploymentCost(baseConfig);
    const optimizedCost = calculateDeploymentCost(optimizedConfig);

    const monthlySavings = baseCost.monthly.total - optimizedCost.monthly.total;
    const percentSaved = baseCost.monthly.total > 0
      ? (monthlySavings / baseCost.monthly.total) * 100
      : 0;

    const savingsBreakdown: Record<string, number> = {
      storage: baseCost.monthly.storage - optimizedCost.monthly.storage,
      compute: baseCost.monthly.compute - optimizedCost.monthly.compute,
      requests: baseCost.monthly.requests - optimizedCost.monthly.requests,
      embeddings: baseCost.monthly.embeddings - optimizedCost.monthly.embeddings,
    };

    return {
      monthlySavings,
      percentSaved,
      savingsBreakdown,
    };
  }, [baseConfig, optimizedConfig]);
}
