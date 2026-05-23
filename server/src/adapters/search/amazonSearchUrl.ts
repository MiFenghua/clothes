import { config } from "../../config.js";

export function buildAmazonSearchUrl(query: string) {
  if (config.amazonSearchUrlTemplate) {
    return config.amazonSearchUrlTemplate
      .replaceAll("{query}", encodeURIComponent(query))
      .replaceAll("{rawQuery}", query);
  }

  const searchUrl = new URL("/s", config.amazonMarketplaceBaseUrl);
  searchUrl.searchParams.set("k", query);
  return searchUrl.toString();
}

export function getAmazonMarketplaceOrigin() {
  return new URL(config.amazonMarketplaceBaseUrl).origin;
}
