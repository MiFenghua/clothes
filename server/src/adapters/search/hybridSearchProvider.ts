import type { Budget, OutfitStrategy } from "../../domain/types.js";
import type { SearchProvider, SearchProviderIssue } from "./searchProvider.js";

export class HybridSearchProvider implements SearchProvider {
  private lastSearchIssue: SearchProviderIssue | null = null;

  constructor(
    private readonly primary: SearchProvider,
    private readonly fallback: SearchProvider
  ) {}

  async search(input: { strategy: OutfitStrategy; budget: Budget; limitPerQuery: number }) {
    this.lastSearchIssue = null;
    const primaryProducts = await this.primary.search(input);
    this.lastSearchIssue = this.readIssue(this.primary);
    if (primaryProducts.length >= 10) {
      return primaryProducts;
    }

    const fallbackProducts = await this.fallback.search(input);
    this.lastSearchIssue = this.lastSearchIssue ?? this.readIssue(this.fallback);
    const seen = new Set(primaryProducts.map((product) => product.productId));
    return [
      ...primaryProducts,
      ...fallbackProducts.filter((product) => !seen.has(product.productId))
    ].slice(0, input.limitPerQuery);
  }

  getLastSearchIssue() {
    return this.lastSearchIssue ?? this.readIssue(this.primary) ?? this.readIssue(this.fallback);
  }

  private readIssue(provider: SearchProvider) {
    return provider.getLastSearchIssue?.() ?? null;
  }
}
