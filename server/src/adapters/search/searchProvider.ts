import type { Budget, OutfitStrategy, Product } from "../../domain/types.js";

export type SearchProviderIssueCode =
  | "AMAZON_VERIFICATION_REQUIRED"
  | "AMAZON_BROWSER_UNAVAILABLE"
  | "AMAZON_TIMEOUT"
  | "TAOBAO_LOGIN_REQUIRED"
  | "TAOBAO_VERIFICATION_REQUIRED"
  | "TAOBAO_BROWSER_UNAVAILABLE"
  | "TAOBAO_TIMEOUT";

export interface SearchProviderIssue {
  code: SearchProviderIssueCode;
  message: string;
  provider: string;
}

export interface SearchProvider {
  search(input: {
    strategy: OutfitStrategy;
    budget: Budget;
    limitPerQuery: number;
  }): Promise<Product[]>;
  getLastSearchIssue?(): SearchProviderIssue | null;
}

export function getLastSearchIssue(provider: SearchProvider) {
  return provider.getLastSearchIssue?.() ?? null;
}
